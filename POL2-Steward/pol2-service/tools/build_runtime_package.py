#!/usr/bin/env python3
"""Build the runtime-only knowledge package bundled with releases."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'packages' / 'pol2-2026.10.21.1'
TARGET = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'
RUNTIME_KNOWLEDGE = (
    'theory-overview.md', 'rule-mapping.jsonl', 'answers.jsonl', 'concepts.jsonl',
    'relations.jsonl', 'love-languages.jsonl', 'propositions.jsonl',
    'retrieval-aliases.json', 'retrieval-config.json', 'boundary-decisions-approved.md',
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not (SOURCE / 'package-manifest.json').exists():
        raise SystemExit('run tools/build_package.py first')
    if TARGET.exists():
        shutil.rmtree(TARGET)
    (TARGET / 'knowledge').mkdir(parents=True)
    for name in ('documents.jsonl', 'search-records.jsonl', 'retrieval-index.json', 'compatibility.json'):
        shutil.copy2(SOURCE / name, TARGET / name)
    for name in RUNTIME_KNOWLEDGE:
        shutil.copy2(SOURCE / 'knowledge' / name, TARGET / 'knowledge' / name)

    source_manifest = json.loads((SOURCE / 'package-manifest.json').read_text(encoding='utf-8'))
    checksums = {}
    for path in sorted(TARGET.rglob('*')):
        if path.is_file() and path.name != 'package-manifest.json':
            checksums[str(path.relative_to(TARGET))] = sha256(path)
    manifest = {
        'package_id': TARGET.name, 'source_commit': source_manifest['source_commit'],
        'created_at': source_manifest['created_at'], 'status': source_manifest['status'],
        'runtime_package': True, 'documents': source_manifest['documents'],
        'rules': source_manifest['rules'], 'interpretations': source_manifest['interpretations'],
        'answers': source_manifest['answers'], 'love_languages': source_manifest['love_languages'],
        'propositions': source_manifest['propositions'], 'checksums': checksums,
        'note': 'Runtime bundle only. Raw theory sources and evaluation reports are distributed through the pinned upstream source workflow.',
    }
    (TARGET / 'package-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (TARGET / 'README.md').write_text(
        '# POL2 Runtime Knowledge Package\n\n'
        f"Package: `{TARGET.name}`\n\n"
        f"Source commit: `{source_manifest['source_commit']}`\n\n"
        'This bundle contains the runtime documents, structured rules, reliable answers and lexical retrieval index. '
        'Raw source files and evaluation reports are not included.\n', encoding='utf-8')
    print(json.dumps({'package': TARGET.name, 'files': len(checksums),
                      'documents': manifest['documents'], 'rules': manifest['rules']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
