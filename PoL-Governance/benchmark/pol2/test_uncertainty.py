"""benchmark/pol2/uncertainty.py 的单元测试。

运行：python -m unittest discover -s benchmark/pol2 -p "test_*.py" -q
"""
import importlib.util
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


u = load_module('pol2_uncertainty', HERE / 'uncertainty.py')
METRIC = 'status_accuracy_all_requests'


def report(counts, den=10):
    return {'breakdown_by_family_id': {
        f'f{i}': {METRIC: {'count': c, 'denominator': den}} for i, c in enumerate(counts)}}


def run_evaluate(predictions):
    out = subprocess.run(
        [sys.executable, str(HERE / 'evaluate.py'),
         '--cases', str(FIXTURES / 'public_test.cases.jsonl'),
         '--labels', str(FIXTURES / 'public_test.labels.jsonl'),
         '--predictions', str(FIXTURES / predictions)],
        capture_output=True, check=True)
    return json.loads(out.stdout.decode('utf-8'))


class TQuantileTest(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(u.t95(4), 2.776)
        self.assertAlmostEqual(u.t95(18), 2.101, places=9)
        self.assertEqual(u.t95(500), 1.960)
        self.assertTrue(2.0 < u.t95(50) < 2.021)
        self.assertEqual(u.t80(4), 0.941)


class RatioCiTest(unittest.TestCase):
    def test_matches_hand_computation(self):
        x, n = [8, 6, 9, 7, 10], [10] * 5
        d = u.ratio_ci(x, n)
        se = math.sqrt(5 / 4 * sum((xi - 0.8 * 10) ** 2 for xi in x)) / 50
        self.assertAlmostEqual(d['estimate'], 0.8, places=12)
        self.assertAlmostEqual(d['se'], se, places=12)
        self.assertAlmostEqual(d['hi'] - d['lo'], 2 * 2.776 * se, places=9)

    def test_unequal_family_sizes_use_ratio_estimator(self):
        d = u.ratio_ci([9, 4, 5, 2], [10, 5, 10, 5])
        self.assertAlmostEqual(d['estimate'], 20 / 30, places=12)

    def test_refuses_too_few_families(self):
        with self.assertRaises(SystemExit):
            u.ratio_ci([1, 2, 3], [4, 4, 4])

    def test_zero_variance_is_flagged(self):
        text = u.fmt(u.ratio_ci([10, 10, 10, 10], [10] * 4))
        self.assertIn('degenerate', text)


class PairedTest(unittest.TestCase):
    def test_verdicts(self):
        a, b = report([9, 8, 9, 10, 9, 8]), report([5, 6, 5, 6, 5, 7])
        d = u.paired(a, b, METRIC, margin=0.02)
        self.assertEqual(d['verdict'], 'A better')
        self.assertGreater(d['estimate'], 0)
        self.assertEqual(u.paired(b, a, METRIC, margin=0.02)['verdict'], 'A worse')

    def test_lower_is_better_metric_flips_direction(self):
        mk = lambda xs: {'breakdown_by_family_id': {
            f'f{i}': {'unsanctioned_action_rate': {'count': c, 'denominator': 10}} for i, c in enumerate(xs)}}
        d = u.paired(mk([1, 0, 1, 0, 1, 1]), mk([5, 6, 5, 6, 5, 7]), 'unsanctioned_action_rate', margin=0.02)
        self.assertEqual(d['verdict'], 'A better')

    def test_rejects_mismatched_data(self):
        with self.assertRaises(SystemExit):
            u.paired(report([1, 2, 3, 4]), report([1, 2, 3, 4], den=12), METRIC)
        with self.assertRaises(SystemExit):
            u.paired(report([1, 2, 3, 4]), report([1, 2, 3, 4, 5]), METRIC)

    def test_inconclusive_when_interval_straddles_zero(self):
        a, b = report([5, 6, 4, 7, 5, 6]), report([6, 5, 5, 6, 6, 5])
        self.assertEqual(u.paired(a, b, METRIC, margin=0.0)['verdict'], 'inconclusive')


class FixtureIntegrationTest(unittest.TestCase):
    def test_runs_on_real_evaluator_reports(self):
        strong, weak = run_evaluate('predictions.strong.jsonl'), run_evaluate('predictions.weak.jsonl')
        d = u.paired(strong, weak, METRIC, margin=0.02)
        self.assertEqual(d['families'], 14)
        self.assertEqual(d['verdict'], 'A better')
        self.assertTrue(0 <= u.single(weak, METRIC)['lo'] <= u.single(weak, METRIC)['hi'] <= 1.0001)


if __name__ == '__main__':
    unittest.main()
