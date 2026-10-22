"""Fetch the fixed POL2 source files and rebuild derived artifacts."""
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / 'knowledge'
COMMIT = 'c70227fbc13b64f189c54efe2d45f2d77bc3babf'
REPO = 'https://github.com/naturaldao/NaturalDAO'
RAW = 'https://raw.githubusercontent.com/naturaldao/NaturalDAO'


def fetch_file(path, expected):
    url = f'{RAW}/{COMMIT}/{quote(path, safe="/")}'
    last_error = None
    for attempt in range(5):
        try:
            response = requests.get(url, timeout=(10, 60))
            response.raise_for_status()
            content = response.content
            if len(content) != expected['bytes']:
                raise ValueError(f'byte size mismatch for {path}')
            if hashlib.sha256(content).hexdigest() != expected['sha256']:
                raise ValueError(f'sha256 mismatch for {path}')
            return content
        except Exception as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(2 ** attempt)
    raise RuntimeError(f'failed to fetch {path}: {last_error}')


def main():
    manifest_path = KNOWLEDGE / 'source-manifest.json'
    if not manifest_path.exists():
        raise RuntimeError('knowledge/source-manifest.json is required to reproduce sources')
    original = json.loads(manifest_path.read_text(encoding='utf-8'))
    if original.get('source_commit') != COMMIT:
        raise RuntimeError('source manifest commit does not match the pinned import commit')

    records = []
    sections = []
    for expected in sorted(original['files'], key=lambda item: item['path']):
        rel = expected['path']
        content = fetch_file(rel, expected)
        path = KNOWLEDGE / 'sources' / COMMIT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        records.append({
            'path': rel, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
            'source_url': f'{REPO}/blob/{COMMIT}/{quote(rel, safe="/")}',
            'role': 'theory' if rel.endswith('.md') else 'attachment',
        })
        if rel.endswith('.md'):
            text = content.decode('utf-8-sig').replace('\r\n', '\n')
            normalized = KNOWLEDGE / 'normalized' / rel
            normalized.parent.mkdir(parents=True, exist_ok=True)
            normalized.write_text(text, encoding='utf-8')
            for number, paragraph in enumerate(re.split(r'\n\s*\n', text), 1):
                if paragraph.strip():
                    sections.append({
                        'source_path': rel, 'paragraph': number, 'text': paragraph,
                        'sha256': hashlib.sha256(paragraph.encode()).hexdigest(),
                        'source_commit': COMMIT,
                    })

    manifest = {
        'repository': REPO, 'source_commit': COMMIT,
        'normalization': 'UTF-8 BOM removed and CRLF converted to LF; originals unchanged',
        'files': records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (KNOWLEDGE / 'source-paragraphs.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in sections), encoding='utf-8')
    (KNOWLEDGE / 'source-inventory.md').write_text(
        '# POL2 原文基线\n\n'
        f'固定提交：`{COMMIT}`\n\n'
        '| 文件 | 字节数 | SHA-256 |\n| --- | --- | --- |\n'
        + ''.join(f'| {row["path"]} | {row["bytes"]} | `{row["sha256"]}` |\n' for row in records)
        + '\n标准化仅处理 BOM 与换行；原始副本保留不变。外链仅登记，不自动导入为治理规则。\n',
        encoding='utf-8')
    print(json.dumps({'commit': COMMIT, 'files': len(records), 'paragraphs': len(sections)}))


if __name__ == '__main__':
    main()
