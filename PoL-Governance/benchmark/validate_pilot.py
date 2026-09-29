"""Validate the public annotation pilot; never claims semantic validation."""
import json
from collections import Counter
from pathlib import Path

path = Path(__file__).with_name('pilot.jsonl')
rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
assert rows, 'Empty pilot'
ids = set()
statuses = {'conforming', 'violating', 'insufficient'}
actions = {'allow', 'repair', 'block', 'clarify', 'review'}
issues = {'dishonesty', 'consent_boundary', 'coercion_manipulation', 'dignity_equality', 'fabricated_intimacy', 'harm_facilitation', 'unnecessary_restriction'}
for row in rows:
    assert row['id'] not in ids, f"Duplicate: {row['id']}"
    ids.add(row['id'])
    assert row['split'] == 'pilot_public'
    assert row['annotation_status'] == 'proposed_unreviewed'
    assert isinstance(row['family_id'], str) and row['family_id']
    inp, proposal = row['input'], row['proposal']
    assert set(inp) == {'surface', 'context', 'target', 'policy'}
    assert inp['surface'] in {'user_input', 'assistant_output', 'tool_action'}
    assert isinstance(inp['context'], list) and inp['context']
    assert all(isinstance(x, str) and x.strip() for x in inp['context'])
    assert all(isinstance(inp[k], str) and inp[k].strip() for k in ('target', 'policy'))
    assert proposal['status'] in statuses
    assert isinstance(proposal['issues'], list) and set(proposal['issues']) <= issues
    assert isinstance(proposal['acceptable_actions'], list) and proposal['acceptable_actions']
    assert set(proposal['acceptable_actions']) <= actions
    assert isinstance(proposal['brief_reason'], str) and proposal['brief_reason'].strip()
families = Counter(r['family_id'] for r in rows)
print(json.dumps({'structural_check': 'pass', 'cases': len(rows), 'families': len(families),
                  'status_counts': dict(Counter(r['proposal']['status'] for r in rows)),
                  'semantic_review': 'pending', 'model_evaluation': 'not_run'}, ensure_ascii=False, indent=2))
