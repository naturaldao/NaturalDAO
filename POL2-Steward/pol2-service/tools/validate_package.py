#!/usr/bin/env python3
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL_PACKAGE = ROOT / 'packages' / 'pol2-2026.10.21.1'
RUNTIME_PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'
PACKAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    FULL_PACKAGE if (FULL_PACKAGE / 'package-manifest.json').exists() else RUNTIME_PACKAGE)


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def tokenize(text):
    text = text.lower()
    tokens = re.findall(r'[a-z0-9_]{2,}', text)
    for sequence in re.findall(r'[\u3400-\u9fff]+', text):
        tokens.extend(sequence[i:i + 2] for i in range(max(0, len(sequence) - 1)))
        tokens.extend(sequence[i:i + 3] for i in range(max(0, len(sequence) - 2)))
    return tokens


def load_index():
    return load_jsonl(PACKAGE / 'search-records.jsonl'), json.loads((PACKAGE / 'retrieval-index.json').read_text(encoding='utf-8'))


def search(query, records, index, limit=20):
    counts = Counter(tokenize(query))
    scores = Counter()
    k1, b = 1.5, 0.75
    for token in counts:
        idf = index['idf'].get(token, 1.0)
        for doc_index, frequency in index['postings'].get(token, []):
            length = index['lengths'][doc_index]
            denom = frequency + k1 * (1 - b + b * length / index['average_length'])
            scores[doc_index] += idf * frequency * (k1 + 1) / denom
    return [records[i] for i, _ in scores.most_common(limit)]


def main():
    manifest = json.loads((PACKAGE / 'package-manifest.json').read_text(encoding='utf-8'))
    for relative, expected in manifest['checksums'].items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'checksum mismatch: {relative}')
    records, index = load_index()
    retrieval_config = json.loads((PACKAGE / 'knowledge' / 'retrieval-config.json').read_text(encoding='utf-8'))
    core_rules = set(retrieval_config['always_loaded_rules'])
    if index['record_count'] != len(records):
        raise ValueError('index record count mismatch')
    if any('{{' in record['text'] or 'TODO' in record['text'] for record in records):
        raise ValueError('placeholder found in package records')

    report = {'package': PACKAGE.name, 'checksums': len(manifest['checksums']),
              'documents': manifest['documents'], 'records': len(records)}
    evaluation_paths = sorted((PACKAGE / 'evaluation').glob('*.jsonl')) if (PACKAGE / 'evaluation').exists() else []
    for eval_path in evaluation_paths:
        split = eval_path.stem
        cases = load_jsonl(eval_path)
        hits = 0
        missing = []
        for case in cases:
            expanded = set(core_rules)
            for result in search(case['input'] + ' ' + case['context'], records, index, retrieval_config['top_k']):
                expanded.update(result.get('rule_ids', []))
            expected = set(case['source_refs'])
            found = expected <= expanded
            hits += int(found)
            if not found:
                missing.append({'case_id': case['case_id'], 'missing_rules': sorted(expected - expanded)})
        report[split] = {'cases': len(cases), 'expected_rule_recall': round(hits / len(cases), 4), 'missing': missing}
    if evaluation_paths:
        (ROOT / 'evaluation' / 'reports').mkdir(parents=True, exist_ok=True)
        (ROOT / 'evaluation' / 'reports' / 'retrieval-validation.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for split, metrics in report.items():
        if isinstance(metrics, dict) and 'expected_rule_recall' in metrics and metrics['expected_rule_recall'] < 1.0:
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
