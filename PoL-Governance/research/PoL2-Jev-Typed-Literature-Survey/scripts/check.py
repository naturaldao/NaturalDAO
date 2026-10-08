"""Check that the survey directory is self-consistent and portable.

  - every relative Markdown link resolves inside this directory;
  - every PDF in papers/ is listed in data/papers.csv with a Creative Commons licence;
  - every row marked pdf_in_repo=yes has its PDF;
  - no PDF under an arXiv default (non-redistributable) licence is tracked in papers/;
  - every PoL2 axis used in the data is defined in data/pol2_axes.json.

Run from anywhere:  python scripts/check.py
"""
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '_local', '__pycache__'}


def main():
    errors = []
    links = 0
    for md in ROOT.rglob('*.md'):
        if set(md.relative_to(ROOT).parts) & SKIP:
            continue
        for link in re.findall(r'\]\(([^)\s]+)\)', md.read_text(encoding='utf-8')):
            if '://' in link or link.startswith(('#', 'mailto:')):
                continue
            target = (md.parent / unquote(link.split('#')[0])).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f'broken or non-portable link: {md.relative_to(ROOT)} -> {link}')
            links += 1

    rows = list(csv.DictReader((ROOT / 'data' / 'papers.csv').open(encoding='utf-8')))
    by_id = {r['arxiv_id']: r for r in rows if r['arxiv_id']}
    for pdf in (ROOT / 'papers').glob('*.pdf'):
        r = by_id.get(pdf.stem)
        if r is None:
            errors.append(f'papers/{pdf.name} is not listed in data/papers.csv')
        elif 'creativecommons.org' not in r['license_url']:
            errors.append(f'papers/{pdf.name} has a non-redistributable licence: {r["license"]}')
    for r in rows:
        if r['pdf_in_repo'] == 'yes' and not (ROOT / 'papers' / f"{r['arxiv_id']}.pdf").is_file():
            errors.append(f"{r['id']} is marked pdf_in_repo=yes but papers/{r['arxiv_id']}.pdf is missing")

    axes = set(json.loads((ROOT / 'data' / 'pol2_axes.json').read_text(encoding='utf-8'))['axes'])
    used = {a for f in ('papers.csv', 'grey_literature.csv')
            for r in csv.DictReader((ROOT / 'data' / f).open(encoding='utf-8'))
            for a in r['pol_axes'].split()}
    errors += [f'axis {a} is used but not defined in data/pol2_axes.json' for a in sorted(used - axes)]

    report = {'status': 'fail' if errors else 'pass', 'local_links': links, 'papers': len(rows),
              'pdf_in_repo': sum(r['pdf_in_repo'] == 'yes' for r in rows)}
    print(json.dumps(report, ensure_ascii=False))
    for e in errors:
        print('  -', e)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
