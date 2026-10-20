import sys, json, collections
sys.path.insert(0, 'datasets/general')
import jev_fill as J

plan = J.read_jsonl('datasets/general/data/jev/validation-plan.jsonl')
prow = {r['qid']: r for r in plan[1:]}
qids = set()
shapes = collections.Counter()
aokind = collections.Counter()
noulshape = collections.Counter()
nouln = 0
total = 0
for it, k, q, t in J.iter_targets('datasets/general/data/items.final.jsonl'):
    qid = '%s.%s' % (it['id'], k)
    qids.add(qid)
    total += 1
    s = J.target_shape(t)
    shapes[s] += 1
    if s == 'answer_only':
        aokind[q['kind']] += 1
    if q['kind'] == 'noul':
        pos, neg = J.noul_option_keys(q)
        if pos and neg and str(t.get('answer')) in (pos, neg):
            nouln += 1
            noulshape[s] += 1
print('corpus targets', total, 'shapes', dict(shapes))
print('answer_only by kind', dict(aokind))
print('noul', nouln, 'shapes', dict(noulshape))
missing = [q for q in prow if q not in qids]
print('phase-1 plan qids missing in new corpus:', len(missing), 'of', len(prow))
for name in ('fill-calls-dist.jsonl', 'mercury-noul-fill.jsonl'):
    rows = J.read_jsonl('datasets/general/data/jev/' + name)
    jq = {r.get('qid') for r in rows if r.get('status') == 'ok'}
    miss = sum(1 for q in jq if q not in qids)
    print(name, 'ok qids', len(jq), 'missing in new corpus', miss)
