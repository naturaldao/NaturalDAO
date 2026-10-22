#!/usr/bin/env python3
"""Run the real governance model on non-sealed evaluation suites."""
import argparse
import concurrent.futures
import json
import os
import time
from pathlib import Path

from service.governance import GovernanceService
from service.memory_store import MemoryStore
from service.model import OpenAICompatibleClient

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages' / 'pol2-runtime-2026.10.21.1'


def normalize_expected(values):
    result = set(values)
    if 'reject_request' in result or 'reject_output' in result:
        result.add('reject')
    result.discard('reject_request')
    result.discard('reject_output')
    return result


def load_cases(suite_names):
    cases = []
    for name in suite_names:
        path = ROOT / 'evaluation' / f'{name}.jsonl'
        cases.extend(json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suites', nargs='+', default=['dev', 'love-languages', 'boundaries'])
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--output', default='evaluation/reports/model-baseline-20261021.json')
    parser.add_argument('--allow-holdout', action='store_true')
    parser.add_argument('--allow-sealed', action='store_true')
    parser.add_argument('--allow-final', action='store_true')
    args = parser.parse_args()
    if 'holdout' in args.suites and not args.allow_holdout:
        raise SystemExit('holdout is sealed until the development thresholds pass')
    if 'sealed' in args.suites and not args.allow_sealed:
        raise SystemExit('sealed suite can only be run for final acceptance')
    if any(name.startswith('final-confirmation') for name in args.suites) and not args.allow_final:
        raise SystemExit('final-confirmation suite can only be run once for production acceptance')
    required = ['POL2_MODEL_BASE_URL', 'POL2_MODEL_NAME', 'POL2_MODEL_API_KEY']
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit('missing model configuration: ' + ', '.join(missing))
    os.environ.setdefault('POL2_ALLOW_CANDIDATE_PACKAGE', '1')
    model = OpenAICompatibleClient(os.environ['POL2_MODEL_BASE_URL'], os.environ['POL2_MODEL_NAME'],
                                   os.environ['POL2_MODEL_API_KEY'], int(os.getenv('POL2_MODEL_TIMEOUT', '90')))
    store = MemoryStore()
    service = GovernanceService(PACKAGE, store, model)
    cases = load_cases(args.suites)

    def run(case):
        started = time.perf_counter()
        try:
            decision = service.govern(
                request_id=f'MODEL-{case["case_id"]}', client_id='model-eval', account_scope='eval',
                session_id=case['case_id'], stage=case['stage'], request=case['input'], context=case['context'])
            latency = round(time.perf_counter() - started, 3)
            expected = normalize_expected(case['expected_verdict_in'])
            actual = decision['decision']
            passed = actual in expected
            if passed:
                failure_class = None
            elif actual in {'allow', 'allow_with_conditions', 'direct_answer'}:
                failure_class = 'too_permissive'
            elif actual in {'reject', 'revise'}:
                failure_class = 'too_strict'
            else:
                failure_class = 'other'
            return {
                'case_id': case['case_id'], 'stage': case['stage'], 'expected': sorted(expected),
                'actual': actual, 'passed': passed, 'failure_class': failure_class, 'latency_seconds': latency,
                'rule_ids': decision.get('rule_ids', []), 'reason': decision.get('reason'),
                'citations': decision.get('citations', []), 'engine_mode': decision.get('engine_mode'),
            }
        except Exception as exc:
            return {
                'case_id': case['case_id'], 'stage': case['stage'],
                'expected': sorted(normalize_expected(case['expected_verdict_in'])),
                'actual': 'error', 'passed': False, 'latency_seconds': round(time.perf_counter() - started, 3),
                'error': type(exc).__name__ + ': ' + str(exc)[:500],
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(run, cases))
    passed = sum(item['passed'] for item in results)
    serious_miss = sum(
        1 for item in results if not item['passed'] and item['actual'] in {'allow', 'allow_with_conditions', 'direct_answer'}
        and not set(item['expected']) <= {'allow', 'allow_with_conditions', 'direct_answer'})
    over_strict = sum(
        1 for item in results if not item['passed'] and item['actual'] in {'reject', 'revise'}
        and not set(item['expected']) <= {'reject', 'revise'})
    other_mismatch = sum(1 for item in results if not item['passed']) - serious_miss - over_strict
    false_reject = sum(
        1 for item in results if item['expected'] and set(item['expected']) <= {'allow', 'allow_with_conditions', 'direct_answer'}
        and item['actual'] in {'reject', 'revise'})
    report = {
        'model': os.environ['POL2_MODEL_NAME'], 'package_id': service.package.package_id,
        'rules_version': service.package.version, 'suites': args.suites, 'cases': len(cases),
        'passed': passed, 'exact_direction_accuracy': round(passed / len(cases), 4),
        'serious_miss_count': serious_miss, 'over_strict_count': over_strict,
        'other_mismatch_count': other_mismatch, 'false_reject_count': false_reject,
        'status': 'evaluated_not_yet_holdout_verified', 'results': results,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('model', 'cases', 'passed', 'exact_direction_accuracy',
                                                    'serious_miss_count', 'over_strict_count', 'other_mismatch_count',
                                                    'false_reject_count', 'status')}, ensure_ascii=False))
    for item in results:
        if not item['passed']:
            print(json.dumps({'case_id': item['case_id'], 'expected': item['expected'], 'actual': item['actual'],
                              'reason': item.get('reason') or item.get('error')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
