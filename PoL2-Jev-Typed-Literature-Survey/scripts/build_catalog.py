"""Build data/papers.csv, data/papers.json, papers/LICENSES.md and the survey catalog.

Inputs (all inside this directory):
  data/sources/arxiv_meta.csv   arXiv metadata written by scripts/fetch_papers.ps1
  data/pol2_mapping.csv         human-edited: tier, PoL2 axes and a one-line note per paper

Run from anywhere:  python scripts/build_catalog.py
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'data' / 'sources' / 'arxiv_meta.csv'
MAPPING = ROOT / 'data' / 'pol2_mapping.csv'
SURVEY = ROOT / 'docs' / 'survey.zh.md'
TIERS = ['核心', '相关', '背景']
TIER_LABEL = {'核心': '直接对应 PoL2 治理条款', '相关': '提供补充证据', '背景': '工程与其他领域，供参考'}

# Papers that are not on arXiv; kept here so the catalog stays one generated table.
EXTRA = [{
    'id': 'A-RAG', 'arxiv_id': '', 'tier': '核心', 'pol_axes': 'G4',
    'title': 'Can JEV Be Used as a Confident Classifier? A Calibration Study on Conflict-Type Classification in RAG',
    'authors': 'Prajapati Harishkumar Kishorkumar', 'published': '2026-09-22', 'version': '',
    'primary_category': '', 'license': '未标注', 'license_url': '', 'pdf_in_repo': 'no',
    'url': 'https://www.alphaxiv.org/abs/2609.can-jev-be-used-as-a-confident-classifier-a-calibration-study-on-conflict-type-classification-in-rag',
    'note_zh': '错误答案的平均置信度保持在 0.56–0.58（仅发表于 alphaXiv）', 'abstract': '',
}]


def license_name(url):
    m = re.search(r'creativecommons\.org/licenses/([a-z-]+)/([\d.]+)', url or '')
    if m:
        return f'CC {m.group(1).upper()} {m.group(2)}'
    if 'publicdomain/zero' in (url or ''):
        return 'CC0 1.0'
    if 'nonexclusive-distrib' in (url or ''):
        return 'arXiv 默认许可'
    return url or '未知'


def is_cc(url):
    return bool(re.search(r'creativecommons\.org/(licenses|publicdomain)/', url or ''))


def build():
    meta = {r['arxiv_id']: r for r in csv.DictReader(META.open(encoding='utf-8-sig'))}
    rows = []
    for m in csv.DictReader(MAPPING.open(encoding='utf-8')):
        aid = m['arxiv_id']
        r = meta.get(aid)
        if r is None:
            raise SystemExit(f'{aid} is in pol2_mapping.csv but not in arxiv_meta.csv; run fetch_papers.ps1 first')
        pdf = ROOT / 'papers' / f'{aid}.pdf'
        rows.append({
            'id': 'P-' + aid.split('.')[1], 'arxiv_id': aid, 'tier': m['tier'], 'pol_axes': m['pol_axes'],
            'title': r['title'], 'authors': r['authors'], 'published': r['published'],
            'version': r['version'], 'primary_category': r['primary_category'],
            'license': license_name(r['license_url']), 'license_url': r['license_url'],
            'pdf_in_repo': 'yes' if is_cc(r['license_url']) and pdf.is_file() else 'no',
            'url': f'https://arxiv.org/abs/{aid}', 'note_zh': m['note_zh'], 'abstract': r['abstract'],
        })
    rows += EXTRA
    rows.sort(key=lambda x: (TIERS.index(x['tier']), x['pol_axes'] or 'Z', x['id']))

    with (ROOT / 'data' / 'papers.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (ROOT / 'data' / 'papers.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    esc = lambda s: s.replace('|', '\\|')
    lines = []
    for tier in TIERS:
        sub = [x for x in rows if x['tier'] == tier]
        lines += [f'### {tier}（{len(sub)} 篇）：{TIER_LABEL[tier]}', '',
                  '| 编号 | 标题 | 第一作者 | 日期 | 轴 | 要点 | 许可 | PDF |',
                  '|---|---|---|---|---|---|---|---|']
        for x in sub:
            names = x['authors'].split('; ')
            first = names[0] + (' 等' if len(names) > 1 else '')
            pdf = f"[✅ PDF](../papers/{x['arxiv_id']}.pdf)" if x['pdf_in_repo'] == 'yes' else '🔗 仅链接'
            lines.append(f"| {x['id']} | [{esc(x['title'])}]({x['url']}) | {esc(first)} | {x['published']} "
                         f"| {x['pol_axes']} | {x['note_zh']} | {x['license']} | {pdf} |")
        lines.append('')
    catalog = '\n'.join(lines)
    text = SURVEY.read_text(encoding='utf-8')
    text = re.sub(r'(<!-- CATALOG:START -->\n).*?(<!-- CATALOG:END -->)',
                  lambda m: m.group(1) + catalog + '\n' + m.group(2), text, flags=re.S)
    SURVEY.write_text(text, encoding='utf-8')

    lic = ['# papers/ 的许可说明', '',
           '本文件夹中的论文 **不适用** 本目录的 CC0-1.0 许可。每篇论文保留作者在 arXiv 上选择的 Creative Commons 许可；'
           '转载或再利用时请遵守对应条款并注明原作者。NC（非商业）与 ND（禁止演绎）版本只可原样用于非商业用途。', '',
           '由 `scripts/build_catalog.py` 生成，请勿手工编辑。', '',
           '| 文件 | 标题 | 作者 | 许可 | arXiv 版本 |', '|---|---|---|---|---|']
    for x in rows:
        if x['pdf_in_repo'] == 'yes':
            lic.append(f"| [{x['arxiv_id']}.pdf]({x['arxiv_id']}.pdf) | {esc(x['title'])} | {esc(x['authors'])} "
                       f"| [{x['license']}]({x['license_url']}) | [{x['version']}](https://arxiv.org/abs/{x['version']}) |")
    (ROOT / 'papers' / 'LICENSES.md').write_text('\n'.join(lic) + '\n', encoding='utf-8')

    n_pdf = sum(x['pdf_in_repo'] == 'yes' for x in rows)
    print(json.dumps({'papers': len(rows), 'pdf_in_repo': n_pdf,
                      'by_tier': {t: sum(x['tier'] == t for x in rows) for t in TIERS}}, ensure_ascii=False))


if __name__ == '__main__':
    build()
