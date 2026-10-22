#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from service.embeddings import OpenAIEmbeddingClient
from service.store_postgres import PostgresStore

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=24)
    args = parser.parse_args()
    required = ['POL2_DATABASE_URL', 'POL2_EMBEDDING_BASE_URL', 'POL2_EMBEDDING_MODEL']
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit('missing configuration: ' + ', '.join(missing))
    records = [json.loads(line) for line in (PACKAGE / 'search-records.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    client = OpenAIEmbeddingClient(
        os.environ['POL2_EMBEDDING_BASE_URL'], os.environ['POL2_EMBEDDING_MODEL'],
        os.getenv('POL2_EMBEDDING_API_KEY', ''), int(os.getenv('POL2_EMBEDDING_TIMEOUT', '120')))
    store = PostgresStore(os.environ['POL2_DATABASE_URL'], int(os.getenv('POL2_EMBEDDING_DIM', '4096')))
    rows = []
    for start in range(0, len(records), args.batch_size):
        batch = records[start:start + args.batch_size]
        texts = [record['text'][:8000] for record in batch]
        vectors = client.embed(texts)
        if len(vectors) != len(batch):
            raise RuntimeError('embedding count mismatch')
        rows.extend((record['record_id'], record['record_type'], vector)
                    for record, vector in zip(batch, vectors))
        print(json.dumps({'embedded': len(rows), 'total': len(records)}), flush=True)
    store.replace_embeddings(rows, os.environ['POL2_EMBEDDING_MODEL'])
    print(json.dumps({'status': 'ok', 'records': len(rows), 'model': os.environ['POL2_EMBEDDING_MODEL']}))


if __name__ == '__main__':
    main()
