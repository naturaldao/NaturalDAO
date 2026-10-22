import sys, json, time, random, urllib.request, urllib.error
sys.path.insert(0, 'datasets/general')
import jev_fill as J

cfg = J.load_jev_config()
url = J.DEFAULT_DECISIONS_URL
plan = J.read_jsonl('datasets/general/data/jev/fill-plan-dist-zh-choice.jsonl')
old_zh = {row['qid'] for row in plan[1:]}

items = []
for it, k, q, t in J.iter_targets('datasets/general/data/items.final.jsonl'):
    if J.target_shape(t) != 'answer_only' or q['kind'] != 'choice':
        continue
    qid = '%s.%s' % (it['id'], k)
    if qid in old_zh:
        continue
    src = (it.get('source') or {}).get('dataset') or '?'
    items.append({'qid': qid, 'id': it['id'], 'key': k, 'question': q, 'answer': str(t.get('answer')),
                  'state': str(it.get('state') or ''), 'src': src})
    if len(items) >= 3000:
        break

by_src = {}
for row in items:
    by_src.setdefault(row['src'], []).append(row)
rng = random.Random(20261020)
templates = {
    'T1': lambda label: 'the correct answer is %s' % label,
    'T2': lambda label: 'choosing %s is correct' % label,
    'T3': lambda label: '%s is the right choice' % label,
}
results = {}
for src, rows in by_src.items():
    sample = rows[:6]
    for name, fn in templates.items():
        ok = 0
        parsed = 0
        cost = 0.0
        detail = []
        for row in sample:
            q = row['question']
            options = [str(o.get('key')) for o in q['options']]
            labels = [str(o.get('label') or o.get('key')) for o in q['options']]
            criteria = {}
            for key, label in zip(options, labels):
                criteria[key] = fn(label)[:300]
            body = {'model': J.MERCURY_MODEL, 'state': row['state'][:6000],
                    'questions': {'q': {'type': 'choice',
                                        'instructions': str(q.get('prompt') or '')[:2000],
                                        'criteria': criteria}}}
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json',
                                                  'Accept': 'application/json',
                                                  'Authorization': 'Bearer ' + cfg['apikey'],
                                                  'User-Agent': J.USER_AGENT}, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read(4000).decode('utf-8'))
                ans = (data.get('answers') or {}).get('q') or {}
                cost += float((data.get('usage') or {}).get('cost') or 0)
                probs = ans.get('probabilities')
                if isinstance(probs, dict) and probs:
                    parsed += 1
                    top = max(probs, key=lambda kk: probs[kk])
                    if top == row['answer']:
                        ok += 1
                detail.append({'answer': row['answer'], 'choice': ans.get('choice'),
                               'probs': {kk: round(vv, 3) for kk, vv in (probs or {}).items()}})
            except urllib.error.HTTPError as e:
                detail.append({'error': e.code, 'body': e.read(200).decode('utf-8', 'replace')})
            time.sleep(0.3)
        results[(src, name)] = {'n': len(sample), 'parsed': parsed, 'argmax_ok': ok,
                                'cost': round(cost, 6), 'detail': detail
                                if name == 'T1' else None}
for key, value in results.items():
    print(key, 'n=%d parsed=%d argmax_ok=%d cost=$%.6f' % (value['n'], value['parsed'],
                                                           value['argmax_ok'], value['cost']))
print()
for key, value in results.items():
    if value['detail']:
        print('===', key)
        for d in value['detail'][:3]:
            print('  ', json.dumps(d, ensure_ascii=False)[:300])
