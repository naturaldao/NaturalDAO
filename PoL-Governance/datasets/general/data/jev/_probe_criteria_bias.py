import sys, json, time, random, urllib.request, urllib.error
sys.path.insert(0, 'datasets/general')
import jev_fill as J

cfg = J.load_jev_config()
url = J.DEFAULT_DECISIONS_URL
journal = J.read_jsonl('datasets/general/data/jev/mercury-choice-fill.jsonl')
ok = {}
for row in journal:
    if row.get('status') == 'ok':
        ok[row['qid']] = row
qids = sorted(ok)
rng = random.Random(20261020)
sample = rng.sample(qids, min(30, len(qids)))
sample_set = set(sample)

# 语料信息
info = {}
for it, k, q, t in J.iter_targets('datasets/general/data/items.final.jsonl'):
    qid = '%s.%s' % (it['id'], k)
    if qid in sample_set:
        info[qid] = {'answer': str(t.get('answer')), 'question': q, 'state': str(it.get('state') or '')}

VARIANTS = {
    'T1_current': lambda label: 'the correct answer is %s' % label,
    'N1_neutral': lambda label: 'the state supports %s' % label,
    'N2_neutral': lambda label: '%s follows from the provided information' % label,
    'N3_neutral': lambda label: '%s is consistent with the state' % label,
}


def ask(qid, template):
    row = info[qid]
    q = row['question']
    criteria = {}
    for option in q['options']:
        key = str(option.get('key'))
        label = str(option.get('label') or key).strip()[:300]
        criteria[key] = template(label)
    body = {'model': J.MERCURY_MODEL, 'state': row['state'][:12000],
            'questions': {'q': {'type': 'choice',
                                'instructions': str(q.get('prompt') or '')[:4000],
                                'criteria': criteria}}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                          'Authorization': 'Bearer ' + cfg['apikey'],
                                          'User-Agent': J.USER_AGENT}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read(4000).decode('utf-8'))
        ans = (data.get('answers') or {}).get('q') or {}
        return {'probs': ans.get('probabilities'),
                'cost': float((data.get('usage') or {}).get('cost') or 0)}
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'body': e.read(200).decode('utf-8', 'replace')}


results = {}
total_cost = 0.0
for name, template in VARIANTS.items():
    agree = 0
    parsed = 0
    maxes = []
    picks = {}
    for qid in sample:
        if name == 'T1_current':
            try:
                payload = json.loads(ok[qid].get('content') or '')
                probs = payload.get('probs')
            except Exception:
                probs = None
            cost = 0.0
        else:
            out = ask(qid, template)
            total_cost += out.get('cost') or 0
            probs = out.get('probs')
            time.sleep(0.12)
        if not isinstance(probs, dict) or not probs:
            continue
        parsed += 1
        top = max(probs, key=lambda kk: probs[kk])
        picks[qid] = top
        maxes.append(max(probs.values()))
        if top == info[qid]['answer']:
            agree += 1
    results[name] = {'parsed': parsed, 'agree': agree,
                     'rate': (agree / parsed) if parsed else None,
                     'mean_max': (sum(maxes) / len(maxes)) if maxes else None,
                     'picks': picks}

print('n per variant =', len(sample), ' total cost = $%.6f' % total_cost)
for name, value in results.items():
    print('%-12s parsed=%d agree=%d rate=%s mean_max=%.3f'
          % (name, value['parsed'], value['agree'],
             ('%.1f%%' % (100 * value['rate'])) if value['rate'] is not None else 'n/a',
             value['mean_max'] or 0))

print()
print('argmax 一致性（相对 T1，同 qid 配对）：')
base_picks = results['T1_current']['picks']
for name in ('N1_neutral', 'N2_neutral', 'N3_neutral'):
    picks = results[name]['picks']
    common = [qid for qid in base_picks if qid in picks]
    same = sum(1 for qid in common if picks[qid] == base_picks[qid])
    print('  T1 vs %-11s %d/%d = %.1f%%' % (name, same, len(common), 100 * same / len(common) if common else 0))

print()
print('逐条对照（T1 命中 vs 中性模板命中）：')
for qid in sample[:12]:
    row = [qid[:18], 'ans=' + info[qid]['answer']]
    for name in results:
        row.append('%s=%s' % (name.split('_')[0], results[name]['picks'].get(qid, '-')))
    print('  ', ' '.join(row))
