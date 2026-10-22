#!/usr/bin/env python3
"""Exercise the pipeline with the reference heuristic; not a model-quality claim."""
import json
import os
from pathlib import Path

from service.governance import GovernanceService
from service.memory_store import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'
os.environ.setdefault('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
os.environ.setdefault('POL2_ALLOW_REFERENCE_JUDGE', '1')


def normalize(expected):
    values = set(expected)
    if 'reject_request' in values or 'reject_output' in values:
        values.add('reject')
    values.discard('reject_request')
    values.discard('reject_output')
    return values


def main():
    cases = [json.loads(line) for line in (ROOT / 'evaluation' / 'dev.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    service = GovernanceService(PACKAGE, MemoryStore())
    results = []
    passed = 0
    for index, case in enumerate(cases, 1):
        result = service.govern(
            request_id=f'REF-{index:03d}', client_id='reference', account_scope='evaluation',
            session_id='dev', stage=case['stage'], request=case['input'], context=case['context'])
        expected = normalize(case['expected_verdict_in'])
        ok = result['decision'] in expected
        passed += int(ok)
        results.append({'case_id': case['case_id'], 'expected': sorted(expected), 'actual': result['decision'],
                        'passed': ok, 'reason': result.get('reason')})
    report = {'engine_mode': 'reference_heuristic_v1', 'dev_cases': len(cases),
              'decision_direction_accuracy': round(passed / len(cases), 4),
              'status': 'pipeline_only_not_model_evaluation', 'results': results}
    output = ROOT / 'evaluation' / 'reports' / 'reference-heuristic-dev.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('engine_mode', 'dev_cases', 'decision_direction_accuracy', 'status')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
