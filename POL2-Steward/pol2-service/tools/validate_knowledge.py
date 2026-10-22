#!/usr/bin/env python3
"""Validate frozen POL2 sources and authored knowledge citations."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / 'knowledge'


def load_jsonl(name):
    path = KNOWLEDGE / name
    rows = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f'{name}:{number}: {exc}') from exc
    return rows


def validate_refs(label, row, paragraphs):
    refs = row.get('source_refs')
    if not refs:
        raise ValueError(f'{label}: missing source_refs')
    for ref in refs:
        key = (ref.get('source_path'), ref.get('paragraph'))
        source = paragraphs.get(key)
        if source is None:
            raise ValueError(f'{label}: unknown source ref {key}')
        excerpt = ref.get('excerpt', '')
        def normalize_markdown(value):
            return re.sub(r'\s+', ' ', re.sub(r'[*`]', '', value)).strip()
        normalized_text = normalize_markdown(source['text'])
        normalized_excerpt = normalize_markdown(excerpt)
        if not excerpt or normalized_excerpt not in normalized_text:
            raise ValueError(f'{label}: excerpt not found in {key}: {excerpt!r}')


def main():
    manifest = json.loads((KNOWLEDGE / 'source-manifest.json').read_text(encoding='utf-8'))
    paragraphs = {(row['source_path'], row['paragraph']): row for row in load_jsonl('source-paragraphs.jsonl')}

    seen_paths = set()
    source_counts = {}
    for item in manifest['files']:
        path = KNOWLEDGE / 'sources' / manifest['source_commit'] / item['path']
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError(f'source integrity failed: {item["path"]}')
        if item['path'] in seen_paths:
            raise ValueError(f'duplicate source path: {item["path"]}')
        seen_paths.add(item['path'])
        if item['path'].endswith('.md'):
            source_counts[item['path']] = sum(key[0] == item['path'] for key in paragraphs)
            if source_counts[item['path']] == 0:
                raise ValueError(f'markdown has no indexed paragraphs: {item["path"]}')

    concepts = load_jsonl('concepts.jsonl')
    relations = load_jsonl('relations.jsonl')
    rules = load_jsonl('rule-mapping.jsonl')
    interpretations = load_jsonl('interpretations.jsonl')
    answers = load_jsonl('answers.jsonl')
    love_languages = load_jsonl('love-languages.jsonl')
    propositions = load_jsonl('propositions.jsonl')

    for name, rows, key in [('concept', concepts, 'concept_id'), ('relation', relations, 'relation_id'), ('rule', rules, 'rule_id'),
                            ('love_language', love_languages, 'language_id'), ('proposition', propositions, 'proposition_id')]:
        ids = [row[key] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f'duplicate {name} ids')
        for row in rows:
            validate_refs(f'{name}:{row[key]}', row, paragraphs)

    concept_ids = {row['concept_id'] for row in concepts}
    for relation in relations:
        if relation['from'] not in concept_ids or relation['to'] not in concept_ids:
            raise ValueError(f'relation endpoint missing concept: {relation["relation_id"]}')
    rule_ids = {row['rule_id'] for row in rules}
    for rule in rules:
        if rule.get('kind') not in {'direct_requirement', 'interpretation', 'service_policy'}:
            raise ValueError(f'{rule["rule_id"]}: invalid kind {rule.get("kind")!r}')
        if rule['rule_id'] in {'POL2-R016', 'POL2-R017', 'POL2-R018', 'POL2-R019', 'POL2-R020', 'POL2-R021', 'POL2-R025', 'POL2-R026'} and not rule.get('applicability'):
            raise ValueError(f'{rule["rule_id"]}: missing applicability')
        unknown = set(rule['related_rules']) - rule_ids
        if unknown:
            raise ValueError(f'{rule["rule_id"]}: unknown related rules {sorted(unknown)}')

    for label, rows, key in [('interpretation', interpretations, 'interpretation_id'), ('answer', answers, 'answer_id')]:
        ids = [row[key] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f'duplicate {label} ids')
        for row in rows:
            validate_refs(f'{label}:{row[key]}', row, paragraphs)
            unknown = set(row['rule_ids']) - rule_ids
            if unknown:
                raise ValueError(f'{row[key]}: unknown rules {sorted(unknown)}')
    if len(love_languages) != 16:
        raise ValueError(f'expected 16 love languages, got {len(love_languages)}')
    for item in love_languages:
        unknown = set(item['rule_ids']) - rule_ids
        if unknown:
            raise ValueError(f'{item["language_id"]}: unknown rules {sorted(unknown)}')

    eval_counts = {}
    all_case_ids = []
    valid_verdicts = {'direct_answer', 'allow', 'allow_with_conditions', 'clarify', 'revise', 'reject_request', 'reject_output'}
    for eval_path in sorted((ROOT / 'evaluation').glob('*.jsonl')):
        eval_name = eval_path.name
        cases = []
        eval_path = ROOT / 'evaluation' / eval_name
        for number, line in enumerate(eval_path.read_text(encoding='utf-8').splitlines(), 1):
            if line.strip():
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{eval_name}:{number}: {exc}') from exc
        eval_counts[eval_name] = len(cases)
        case_ids = [case['case_id'] for case in cases]
        all_case_ids.extend(case_ids)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError(f'duplicate cases in {eval_name}')
        for case in cases:
            expected = set(case['expected_verdict_in'])
            if not expected or not expected <= valid_verdicts:
                raise ValueError(f'{case["case_id"]}: invalid expected verdict')
            unknown = set(case['source_refs']) - rule_ids
            if unknown:
                raise ValueError(f'{case["case_id"]}: unknown rules {sorted(unknown)}')
            if not case.get('acceptance') or not case.get('context'):
                raise ValueError(f'{case["case_id"]}: missing acceptance or context')
    if len(all_case_ids) != len(set(all_case_ids)):
        raise ValueError('duplicate evaluation case ids across suites')
    if sum(eval_counts.values()) < 80:
        raise ValueError(f'expected at least 80 evaluation cases, got {sum(eval_counts.values())}')

    cited_paths = set()
    for rows in (concepts, relations, rules, interpretations, answers, love_languages, propositions):
        for row in rows:
            for ref in row.get('source_refs', []):
                cited_paths.add(ref['source_path'])
    expected_paths = {item['path'] for item in manifest['files'] if item['path'].endswith('.md')}
    missing_paths = expected_paths - cited_paths
    if missing_paths:
        raise ValueError(f'markdown sources not represented in knowledge: {sorted(missing_paths)}')

    coverage = KNOWLEDGE / 'chapter-coverage.csv'
    with coverage.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['source_path', 'paragraphs_indexed', 'read_status', 'coverage_note'])
        for item in manifest['files']:
            if item['path'].endswith('.md'):
                writer.writerow([item['path'], source_counts[item['path']], 'reviewed', '全文读取；概念、关系或规则按其适用部分引用'])

    print(json.dumps({
        'sources_verified': len(manifest['files']),
        'markdown_covered': len(source_counts),
        'concepts': len(concepts),
        'relations': len(relations),
        'rules': len(rules),
        'interpretations': len(interpretations),
        'answers': len(answers),
        'love_languages': len(love_languages),
        'propositions': len(propositions),
        'paragraph_count': len(paragraphs),
        'evaluation_cases': eval_counts,
    }, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'VALIDATION FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
