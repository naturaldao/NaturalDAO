import sys, json, collections
sys.path.insert(0, 'datasets/general')
import jev_fill as J

old_zh = set()
plan = J.read_jsonl('datasets/general/data/jev/fill-plan-dist-zh-choice.jsonl')
for row in plan[1:]:
    old_zh.add(row['qid'])

kinds = collections.Counter()
langs = collections.Counter()
options = collections.Counter()
sources = collections.Counter()
new = 0
old_remaining = 0
examples = {}
for it, k, q, t in J.iter_targets('datasets/general/data/items.final.jsonl'):
    if J.target_shape(t) != 'answer_only':
        continue
    qid = '%s.%s' % (it['id'], k)
    if qid in old_zh:
        old_remaining += 1
        continue
    new += 1
    kinds[q['kind']] += 1
    langs[it.get('lang')] += 1
    nopt = len(J.option_space(q))
    options[nopt] += 1
    src = (it.get('source') or {}).get('dataset') or '?'
    sources[src] += 1
    if q['kind'] not in examples:
        examples[q['kind']] = (qid, q, t, it.get('state', ''))
print('new answer-only targets:', new)
print('old-zh-choice already planned:', old_remaining)
print('kinds', dict(kinds))
print('langs', dict(langs))
print('option counts (top)', dict(list(sorted(options.items()))[:10]))
print('sources', dict(list(sources.items())[:10]))
for kind, (qid, q, t, st) in examples.items():
    print('---', kind, qid[:40])
    print('  prompt:', str(q.get('prompt'))[:160])
    print('  options:', json.dumps(q.get('options'), ensure_ascii=False)[:300])
    print('  answer:', json.dumps(t.get('answer'), ensure_ascii=False)[:120])
    print('  state:', str(st)[:160])
