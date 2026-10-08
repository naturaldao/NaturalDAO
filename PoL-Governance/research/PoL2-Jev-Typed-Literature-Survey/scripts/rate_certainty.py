#!/usr/bin/env python3
"""Compute the certainty ratings of tab:keyfindings from data/certainty_evidence.csv.

Rules (paper §3, sec:appraisal), applied mechanically:

* Rank of a study: design rating (stronger > moderate > weaker, from
  data/quality_appraisal*.csv); within a rating, preregistered (design ==
  preregistered) or independently replicated (non-empty ``replicated_by``,
  which must already satisfy D1) ranks above the rest.
* Per-arm counting (D3'): a finding scoped ``hosted`` or ``both`` is rated on
  hosted-arm rows only; a finding scoped ``open`` on open-arm rows only.  Rows
  marked ``corroborate`` or ``out-of-scope`` never enter the rating.
* Studies sharing an author (same ``author_group``) count as one study.
* very low: a single study, or no stronger-design study (or no in-scope
  evidence at all); low: >= 2 studies agree and >= 1 is stronger;
  moderate: >= 3 independent stronger studies agree and >= 1 of them is
  preregistered or replicated.
* Any in-scope opposing study marks the finding contested; if the strongest
  opposing study ranks at least as high as the strongest supporting one the
  rating falls one level (not below very low).
* A finding with clauses (ids such as 8a, 8b, 8c) takes its lowest clause.
* Finding 15 is a descriptive tally rated by judgement (JUDGEMENT below).

Columns printed: given 4 Oct (as given that day), 4 Oct recomputed (main
window, rows with cited_4oct == yes, current rule), main only (all main-window
rows), now (main + update).

``--check`` parses tab:keyfindings (paper/sections/04_evidence.tex) and
tab:certchanges (paper/sections/D_corrections.tex) and exits non-zero if any
rating cell disagrees, or if tab:certchanges does not list exactly the
findings whose rating as given on 4 October differs from now or that are now
contested.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
SECTIONS = os.path.join(ROOT, 'paper', 'sections')

LEVELS = ['very low', 'low', 'moderate']
QUALITY = {'weaker': 1, 'moderate': 2, 'stronger': 3}
JUDGEMENT = {'15': 'low'}          # descriptive tally (§3): rated low by judgement


def load_quality():
    q = {}
    for f in ['quality_appraisal.csv', 'quality_appraisal_update_2026-10-08.csv']:
        with open(os.path.join(DATA, f), encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                q[r['doc']] = (r['quality'], r['design'] == 'preregistered')
    return q


def load_evidence():
    with open(os.path.join(DATA, 'certainty_evidence.csv'), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def base_id(fid):
    return re.match(r'\d+', fid).group(0)


def rate_clause(rows, quality, scope):
    arm = 'open' if scope == 'open' else 'hosted'
    sup, opp = [], []
    for r in rows:
        if r['arm'] != arm or r['direction'] not in ('support', 'oppose'):
            continue
        qual, prereg = quality[r['doc']]
        star = prereg or bool(r['replicated_by'].strip())
        rank = (QUALITY[qual], 1 if star else 0)
        (sup if r['direction'] == 'support' else opp).append((r, qual, star, rank))
    groups = {}
    for r, qual, star, rank in sup:
        groups.setdefault(r['author_group'], []).append((qual, star))
    n_groups = len(groups)
    strong_groups = [g for g, v in groups.items() if any(q == 'stronger' for q, s in v)]
    strong_star = any(q == 'stronger' and s for v in groups.values() for q, s in v)
    if n_groups < 2 or not strong_groups:
        level = 0
    elif len(strong_groups) >= 3 and strong_star:
        level = 2
    else:
        level = 1
    contested = bool(opp)
    fell = False
    if opp:
        top_opp = max(x[3] for x in opp)
        top_sup = max((x[3] for x in sup), default=(0, 0))
        if top_opp >= top_sup and level > 0:
            level -= 1
            fell = True
    if VERBOSE is not None:
        tag = lambda x: '%s[%s%s]' % (x[0]['doc'], {'stronger': 'S', 'moderate': 'M', 'weaker': 'W'}[x[1]], '*' if x[2] else '')
        VERBOSE.append('support %d group(s), %d stronger, S* %s: %s | oppose: %s%s' % (
            n_groups, len(strong_groups), 'yes' if strong_star else 'no',
            ', '.join(tag(x) for x in sup) or '-', ', '.join(tag(x) for x in opp) or '-',
            ' | falls one level' if fell else ''))
    return level, contested


VERBOSE = None


def rate_all(evidence, quality):
    by_finding = {}
    for r in evidence:
        by_finding.setdefault(base_id(r['finding_id']), []).append(r)
    out = []
    for fid in sorted(by_finding, key=int):
        rows = by_finding[fid]
        scope = rows[0]['scope']
        given = rows[0]['given_4oct']
        text = rows[0]['finding'].split(' | clause:')[0]
        for r in rows:
            assert r['scope'] == scope and r['given_4oct'] == given, (fid, r['doc'])
            assert r['arm'] in ('hosted', 'open'), r
            assert r['window'] in ('main', 'update'), r
            assert r['direction'] in ('support', 'oppose', 'corroborate', 'out-of-scope', 'descriptive'), r
            if r['arm'] == 'open' and scope != 'open':
                assert r['direction'] in ('corroborate', 'out-of-scope'), \
                    'open arm cannot support/oppose a %s finding: %s %s' % (scope, fid, r['doc'])
        clause_ids = sorted({r['finding_id'] for r in rows if r['finding_id'] != fid})
        for r in rows:
            if r['finding_id'] == fid and clause_ids:
                assert r['direction'] in ('out-of-scope', 'corroborate'), \
                    'finding %s has clauses; counted row %s must name a clause' % (fid, r['doc'])
        res = {'id': fid, 'text': text, 'scope': scope, 'given': given}
        if fid in JUDGEMENT:
            for k in ('oct', 'main', 'now'):
                res[k] = (JUDGEMENT[fid], False)
            res['judgement'] = True
            out.append(res)
            continue
        res['judgement'] = False
        sets = {
            'oct': lambda r: r['window'] == 'main' and r['cited_4oct'] == 'yes',
            'main': lambda r: r['window'] == 'main',
            'now': lambda r: True,
        }
        for k, keep in sets.items():
            levels, cont = [], False
            for c in (clause_ids or [fid]):
                n0 = len(VERBOSE) if VERBOSE is not None else 0
                lv, ct = rate_clause([r for r in rows if r['finding_id'] == c and keep(r)], quality, scope)
                if VERBOSE is not None:
                    VERBOSE[n0] = '%-4s %-5s -> %-9s %s' % (c, k, LEVELS[lv] + (' c' if ct else ''), VERBOSE[n0])
                levels.append(lv)
                cont = cont or ct
            res[k] = (LEVELS[min(levels)], cont)
        out.append(res)
    return out


def fmt(rating, contested, judgement=False):
    return rating + (' c' if contested else '') + (' j' if judgement else '')


def print_table(results):
    print('%-3s %-7s %-10s %-14s %-14s %-14s  %s' % ('#', 'scope', 'given 4Oct', '4Oct recomp.', 'main only', 'now', 'finding'))
    for r in results:
        j = r['judgement']
        print('%-3s %-7s %-10s %-14s %-14s %-14s  %s' % (
            r['id'], r['scope'], r['given'], fmt(*r['oct'], j), fmt(*r['main'], j), fmt(*r['now'], j), r['text'][:70]))
    now = [r['now'][0] for r in results]
    print('\nNow: %d moderate, %d low, %d very low; contested: %s' % (
        now.count('moderate'), now.count('low'), now.count('very low'),
        ', '.join(r['id'] for r in results if r['now'][1]) or 'none'))
    mo = [r['main'][0] for r in results]
    print('Main only: %d moderate, %d low, %d very low; contested: %s' % (
        mo.count('moderate'), mo.count('low'), mo.count('very low'),
        ', '.join(r['id'] for r in results if r['main'][1]) or 'none'))
    g = [r['given'] for r in results]
    print('Given 4 Oct: %d moderate, %d low, %d very low' % (g.count('moderate'), g.count('low'), g.count('very low')))
    oc = [r['oct'][0] for r in results]
    print('4 Oct recomputed (current rule, studies cited that day): %d moderate, %d low, %d very low; differs from given: %s' % (
        oc.count('moderate'), oc.count('low'), oc.count('very low'),
        ', '.join(r['id'] for r in results if r['oct'][0] != r['given']) or 'none'))
    print('Changed vs given 4 Oct (rating differs or now contested): %s' % ', '.join(
        r['id'] for r in results if changed(r)))


def changed(r):
    return r['given'] != r['now'][0] or r['now'][1]


# --------------------------------------------------------------------- check
def strip_tex(s):
    s = re.sub(r'\$\^\{?([a-z])\}?\$', r'^\1', s)
    s = s.replace('\\', '').replace('{', '').replace('}', '')
    return re.sub(r'\s+', ' ', s).strip()


def split_row(line):
    cells, depth, cur = [], 0, ''
    for ch in line:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        if ch == '&' and depth == 0 and not cur.endswith('\\'):
            cells.append(cur)
            cur = ''
        else:
            cur += ch
    cells.append(cur)
    return [c.strip() for c in cells]


def table_rows(path, label):
    txt = open(path, encoding='utf-8').read()
    i = txt.index('\\label{%s}' % label)
    body = txt[txt.index('\\midrule', i) + len('\\midrule'):txt.index('\\bottomrule', i)]
    rows = [l.strip() for l in body.split('\\\\') if l.strip()]
    return [split_row(r) for r in rows]


def parse_cell(cell):
    """'very low$^{c}$' / 'very low, contested' / 'moderate$^{a}$' -> (rating, contested, marks)."""
    s = strip_tex(cell)
    marks = set(re.findall(r'\^([a-z])', s))
    s = re.sub(r'\^[a-z]', '', s)
    contested = 'contested' in s or 'c' in marks
    s = s.replace(', contested', '').replace('contested', '').strip(' ,')
    return s, contested, marks


def check(results):
    errors = []
    byid = {r['id']: r for r in results}
    kf = table_rows(os.path.join(SECTIONS, '04_evidence.tex'), 'tab:keyfindings')
    texts = {}
    for n, cells in enumerate(kf, 1):
        fid = str(n)
        if fid not in byid:
            if strip_tex(cells[-1]) != '--':
                errors.append('tab:keyfindings row %s has a rating but no evidence rows' % fid)
            continue
        r = byid[fid]
        texts[fid] = strip_tex(cells[0])
        oct_r, oct_c, oct_m = parse_cell(cells[-2])
        now_r, now_c, now_m = parse_cell(cells[-1])
        if oct_r != r['given'] or oct_c:
            errors.append('row %s 4 Oct cell %r != given %r' % (fid, cells[-2], r['given']))
        exp_r, exp_c = r['now']
        if now_r != exp_r or now_c != exp_c or (('j' in now_m) != r['judgement']):
            errors.append('row %s Now cell %r != computed %s' % (fid, cells[-1], fmt(exp_r, exp_c, r['judgement'])))
    expected = {r['id'] for r in results if changed(r)}
    cc = table_rows(os.path.join(SECTIONS, 'D_corrections.tex'), 'tab:certchanges')
    listed = set()
    for cells in cc:
        name = strip_tex(cells[0])
        match = [fid for fid, t in texts.items() if t.startswith(name)]
        if len(match) != 1:
            errors.append('tab:certchanges row %r matches %d keyfindings rows' % (name, len(match)))
            continue
        fid = match[0]
        listed.add(fid)
        r = byid[fid]
        o = parse_cell(cells[1])
        m = parse_cell(cells[2])
        n = parse_cell(cells[3])
        if o[0] != r['given'] or o[1]:
            errors.append('certchanges %s 4 Oct %r != given %r' % (fid, cells[1], r['given']))
        if (m[0], m[1]) != r['main']:
            errors.append('certchanges %s Main only %r != computed %s' % (fid, cells[2], fmt(*r['main'])))
        if (n[0], n[1]) != r['now']:
            errors.append('certchanges %s Now %r != computed %s' % (fid, cells[3], fmt(*r['now'])))
    if listed != expected:
        errors.append('tab:certchanges lists %s; expected %s' % (sorted(listed, key=int), sorted(expected, key=int)))
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='assert that the .tex rating cells match')
    ap.add_argument('--verbose', action='store_true', help='print the counted studies for every clause')
    a = ap.parse_args()
    global VERBOSE
    if a.verbose:
        VERBOSE = []
    results = rate_all(load_evidence(), load_quality())
    if a.verbose:
        print('\n'.join(VERBOSE) + '\n')
    print_table(results)
    if a.check:
        errs = check(results)
        if errs:
            print('\nCHECK FAILED:')
            for e in errs:
                print('  ' + e)
            sys.exit(1)
        print('\nCHECK PASSED: tab:keyfindings and tab:certchanges agree with the computed ratings.')


if __name__ == '__main__':
    main()
