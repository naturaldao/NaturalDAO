#!/usr/bin/env python3
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'


def tokenize(text):
    text = text.lower()
    words = re.findall(r'[a-z0-9_]{2,}', text)
    han = re.findall(r'[\u3400-\u9fff]+', text)
    tokens = list(words)
    for sequence in han:
        tokens.extend(sequence[i:i + 2] for i in range(max(0, len(sequence) - 1)))
        tokens.extend(sequence[i:i + 3] for i in range(max(0, len(sequence) - 2)))
    return tokens


def search(query, limit=8):
    records = [json.loads(line) for line in (PACKAGE / 'search-records.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    index = json.loads((PACKAGE / 'retrieval-index.json').read_text(encoding='utf-8'))
    counts = Counter(tokenize(query))
    scores = Counter()
    k1, b = 1.5, 0.75
    for token in counts:
        entries = index['postings'].get(token, [])
        idf = index['idf'].get(token, 1.0)
        for doc_index, frequency in entries:
            length = index['lengths'][doc_index]
            denom = frequency + k1 * (1 - b + b * length / index['average_length'])
            scores[doc_index] += idf * frequency * (k1 + 1) / denom
    result = []
    for doc_index, score in scores.most_common(limit):
        record = records[doc_index]
        result.append({'score': round(score, 4), 'record_id': record['record_id'], 'record_type': record['record_type'],
                       'title': record['title'], 'rule_ids': record['rule_ids'], 'text': record['text'][:420]})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('query')
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(search(args.query, args.limit), ensure_ascii=False, indent=2))
