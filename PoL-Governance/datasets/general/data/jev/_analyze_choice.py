import sys, json, collections, statistics
sys.path.insert(0, 'datasets/general')
import jev_fill as J

rows = J.read_jsonl('datasets/general/data/jev/mercury-choice-probs.jsonl')
print('choice written rows:', len(rows))
maxes = []
supports = []
for row in rows:
    values = list(row['probs'].values())
    maxes.append(max(values))
    supports.append(sum(1 for v in values if v > 0))
print('max prob: median %.3f mean %.3f min %.3f' % (statistics.median(maxes), sum(maxes)/len(maxes), min(maxes)))
print('support: median %d  dist %s' % (statistics.median(supports), dict(sorted(collections.Counter(supports).items()))))
print('very peaked (max>0.99): %d (%.1f%%)' % (sum(1 for v in maxes if v > 0.99), 100*sum(1 for v in maxes if v>0.99)/len(maxes)))
print('confident (max>0.9): %d (%.1f%%)' % (sum(1 for v in maxes if v > 0.9), 100*sum(1 for v in maxes if v>0.9)/len(maxes)))

# 按 bigbench 子任务拆 mismatch（用 journal + 语料）
journal = J.read_jsonl('datasets/general/data/jev/mercury-choice-fill.jsonl')
ok = {}
for row in journal:
    if row.get('status') == 'ok':
        ok[row['qid']] = row
qids = set(ok)
info = {}
for it, k, q, t in J.iter_targets('datasets/general/data/items.final.jsonl'):
    qid = '%s.%s' % (it['id'], k)
    if qid in qids:
        info[qid] = (str(t.get('answer')), q, (it.get('source') or {}).get('dataset'))
per = collections.Counter()
tot = collections.Counter()
for qid, row in ok.items():
    if qid not in info:
        continue
    try:
        payload = json.loads(row.get('content') or '')
    except Exception:
        continue
    probs = payload.get('probs') or {}
    if not probs:
        continue
    top = max(probs, key=lambda kk: probs[kk])
    answer, question, src = info[qid]
    key = (src, str(question.get('key'))[:40])
    tot[key] += 1
    if top == answer:
        per[key] += 1
print()
print('by (source, key): agree/total')
for key in sorted(tot):
    print('  %-70s %d/%d = %.1f%%' % (str(key), per[key], tot[key], 100*per[key]/tot[key]))
