"""Check portable collaboration links, registries and tests; optionally compare a mirror."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def files(root):
    skip = {'__pycache__', '.git', '.venv', '.cache'}
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and not (set(p.relative_to(root).parts) & skip)
            and p.suffix not in ('.pyc', '.pyo')}


def local_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f'Missing/outside file: {value}')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mirror', type=Path)
    args = parser.parse_args()
    links = 0
    try:
        for path in ROOT.rglob('*.md'):
            if set(path.relative_to(ROOT).parts) & {'__pycache__', '.git', '.venv', '.cache'}:
                continue
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):
                    continue
                target = (path.parent / unquote(link.split('#')[0])).resolve()
                if not target.is_relative_to(ROOT) or not target.exists():
                    raise ValueError(f'Broken/nonportable link: {path.relative_to(ROOT)} -> {link}')
                links += 1
        for name in ('datasets', 'models'):
            rows = json.loads(local_path(f'{name}/registry.json').read_text(encoding='utf-8'))
            ids = [row['id'] for row in rows]
            if len(ids) != len(set(ids)):
                raise ValueError(f'Duplicate ids in {name}')
            for row in rows:
                local_path(row['card'])
                if 'data' in row:
                    local_path(row['data'])
        for suite in ('benchmark', 'tools'):
            subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', suite,
                            '-p', 'test_*.py', '-q'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, 'benchmark/validate_pilot.py'], cwd=ROOT, check=True)
        report = {'status': 'pass', 'local_links': links, 'models_run': False}
        if args.mirror:
            mirror = args.mirror.resolve()
            if not mirror.is_dir() or files(ROOT) != files(mirror):
                raise ValueError('Mirror differs (paths or file bytes)')
            report['mirror'] = 'identical'
            report['files'] = len(files(ROOT))
        print(json.dumps(report, ensure_ascii=False))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Check failed: {error}\n')


if __name__ == '__main__':
    main()
