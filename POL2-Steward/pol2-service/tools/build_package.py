#!/usr/bin/env python3
"""Build a self-contained, offline POL2 knowledge package."""
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / 'knowledge'
PACKAGE_NAME = 'pol2-2026.10.21.1'
PACKAGE = ROOT / 'packages' / PACKAGE_NAME


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def tokenize(text):
    text = text.lower()
    words = re.findall(r'[a-z0-9_]{2,}', text)
    han = re.findall(r'[\u3400-\u9fff]+', text)
    tokens = list(words)
    for sequence in han:
        if len(sequence) == 1:
            tokens.append(sequence)
        else:
            tokens.extend(sequence[i:i + 2] for i in range(len(sequence) - 1))
            tokens.extend(sequence[i:i + 3] for i in range(len(sequence) - 2))
    return tokens


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'validate_knowledge.py')], check=True)
    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    PACKAGE.mkdir(parents=True)
    manifest = json.loads((KNOWLEDGE / 'source-manifest.json').read_text(encoding='utf-8'))
    paragraphs = read_jsonl(KNOWLEDGE / 'source-paragraphs.jsonl')
    rules = read_jsonl(KNOWLEDGE / 'rule-mapping.jsonl')
    concepts = read_jsonl(KNOWLEDGE / 'concepts.jsonl')
    relations = read_jsonl(KNOWLEDGE / 'relations.jsonl')
    interpretations = read_jsonl(KNOWLEDGE / 'interpretations.jsonl')
    answers = read_jsonl(KNOWLEDGE / 'answers.jsonl')
    love_languages = read_jsonl(KNOWLEDGE / 'love-languages.jsonl')
    propositions = read_jsonl(KNOWLEDGE / 'propositions.jsonl')
    retrieval_aliases = json.loads((KNOWLEDGE / 'retrieval-aliases.json').read_text(encoding='utf-8'))

    source_dir = PACKAGE / 'sources'
    shutil.copytree(KNOWLEDGE / 'sources' / manifest['source_commit'], source_dir)
    knowledge_dir = PACKAGE / 'knowledge'
    knowledge_dir.mkdir()
    for name in ('theory-overview.md', 'theory-coverage.md', 'concepts.jsonl', 'relations.jsonl', 'rule-mapping.jsonl', 'retrieval-aliases.json', 'retrieval-config.json',
                 'love-languages.jsonl', 'propositions.jsonl', 'boundary-decisions-approved.md',
                 'interpretations.jsonl', 'answers.jsonl', 'open-questions.md'):
        shutil.copy2(KNOWLEDGE / name, knowledge_dir / name)

    rule_links = defaultdict(list)
    for rule in rules:
        for ref in rule['source_refs']:
            rule_links[(ref['source_path'], ref['paragraph'])].append(rule['rule_id'])

    documents = []
    heading_stack = []
    for paragraph in paragraphs:
        lines = paragraph['text'].splitlines()
        for line in lines:
            match = re.match(r'^(#{1,6})\s+(.*)$', line.strip())
            if match:
                level = len(match.group(1))
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, match.group(2).strip()))
        key = (paragraph['source_path'], paragraph['paragraph'])
        documents.append({
            'doc_id': f'{paragraph["source_path"]}#{paragraph["paragraph"]}',
            'source_path': paragraph['source_path'],
            'paragraph': paragraph['paragraph'],
            'heading_path': [title for _, title in heading_stack],
            'text': paragraph['text'],
            'sha256': paragraph['sha256'],
            'linked_rule_ids': sorted(set(rule_links.get(key, []))),
        })

    records = []
    for doc in documents:
        records.append({
            'record_id': doc['doc_id'], 'record_type': 'source', 'title': ' / '.join(doc['heading_path'][-2:]) or doc['source_path'],
            'text': '\n'.join(doc['heading_path'] + [doc['text']]), 'source_path': doc['source_path'],
            'paragraph': doc['paragraph'], 'rule_ids': doc['linked_rule_ids'],
        })
    for rule in rules:
        records.append({
            'record_id': rule['rule_id'], 'record_type': 'rule', 'title': rule['title'],
            'text': ' '.join([rule['title']] + rule['check_questions'] + rule['decision_guidance'] + rule['conditions_and_exceptions'] + retrieval_aliases.get(rule['rule_id'], [])),
            'rule_ids': [rule['rule_id']],
        })
    for item in interpretations:
        records.append({
            'record_id': item['interpretation_id'], 'record_type': 'interpretation',
            'title': item['question_scope'], 'text': ' '.join([item['question_scope'], item['statement']] + item['limitations']),
            'rule_ids': item['rule_ids'],
        })
    for item in answers:
        records.append({
            'record_id': item['answer_id'], 'record_type': 'answer', 'title': ' / '.join(item['questions']),
            'text': ' '.join(item['questions'] + [item['answer']]), 'rule_ids': item['rule_ids'],
        })
    for item in love_languages:
        records.append({
            'record_id': item['language_id'], 'record_type': 'love_language',
            'title': f'{item["name_zh"]}／{item["name_en"]}',
            'text': ' '.join([item['name_zh'], item['definition']] + item['key_limits']),
            'rule_ids': item['rule_ids'],
        })
    for item in propositions:
        records.append({
            'record_id': item['proposition_id'], 'record_type': 'proposition',
            'title': item['type'], 'text': item['statement'], 'rule_ids': [],
        })

    postings = defaultdict(list)
    lengths = []
    for index, record in enumerate(records):
        counts = Counter(tokenize(record['text']))
        lengths.append(sum(counts.values()))
        for token, frequency in counts.items():
            postings[token].append([index, frequency])
    average_length = sum(lengths) / max(1, len(lengths))
    idf = {token: math.log((len(records) + 1) / (len(entries) + 1)) + 1 for token, entries in postings.items()}
    index = {
        'version': 'lexical_ngram_v1',
        'semantic_embedding': None,
        'note': 'Offline Chinese character n-gram and Latin token index. Semantic embeddings remain a production enhancement.',
        'record_count': len(records), 'average_length': average_length,
        'postings': postings, 'idf': idf, 'lengths': lengths,
    }

    (PACKAGE / 'documents.jsonl').write_text(''.join(json.dumps(doc, ensure_ascii=False) + '\n' for doc in documents), encoding='utf-8')
    (PACKAGE / 'search-records.jsonl').write_text(''.join(json.dumps(rec, ensure_ascii=False) + '\n' for rec in records), encoding='utf-8')
    (PACKAGE / 'retrieval-index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    evaluation_dir = PACKAGE / 'evaluation'
    shutil.copytree(ROOT / 'evaluation', evaluation_dir)

    compatibility = {
        'package_format': 1,
        'source_commit': manifest['source_commit'],
        'language': ['zh-CN'],
        'retrieval': {'backend': 'lexical_ngram_v1', 'requires_embedding_model': False,
                      'semantic_embedding': 'deferred', 'minimum_python': '3.10',
                      'config': 'knowledge/retrieval-config.json'},
    }
    (PACKAGE / 'compatibility.json').write_text(json.dumps(compatibility, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    checksums = {}
    for path in sorted(PACKAGE.rglob('*')):
        if path.is_file() and path.name != 'package-manifest.json':
            checksums[str(path.relative_to(PACKAGE))] = sha256(path.read_bytes())
    package_manifest = {
        'package_id': PACKAGE_NAME, 'source_commit': manifest['source_commit'],
        'created_at': '2026-10-21', 'status': 'behavior_verified_candidate',
        'documents': len(documents), 'rules': len(rules), 'interpretations': len(interpretations),
        'answers': len(answers), 'love_languages': len(love_languages), 'propositions': len(propositions),
        'evaluation_cases': sum(len(read_jsonl(path)) for path in (ROOT / 'evaluation').glob('*.jsonl')),
        'checksums': checksums,
    }
    (PACKAGE / 'package-manifest.json').write_text(json.dumps(package_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (PACKAGE / 'README.md').write_text(
        '# POL2 Knowledge Package\n\n'
        f"Package: `{PACKAGE_NAME}`\n\n"
        f"Source commit: `{manifest['source_commit']}`\n\n"
        'This package contains immutable sources, reviewed interpretations, candidate rules, reliable answers, '
        'evaluation sets and an offline Chinese n-gram retrieval index. It is a candidate package: real model '
        'behavior tests are still required before marking production-ready.\n', encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'validate_package.py')], check=True)
    print(json.dumps({'package': PACKAGE_NAME, 'path': str(PACKAGE), 'documents': len(documents),
                      'records': len(records), 'love_languages': len(love_languages),
                      'propositions': len(propositions), 'checksums': len(checksums)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
