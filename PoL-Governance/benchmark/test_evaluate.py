import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evaluate import evaluate, read_jsonl
from export_inputs import input_view

HERE = Path(__file__).parent

def case(key, status, actions):
    return {'id': key, 'family_id': key, 'split': 'pilot_public',
            'annotation_status': 'proposed_unreviewed',
            'input': {'surface': 'assistant_output', 'context': ['context'],
                      'target': 'target', 'policy': 'policy'},
            'proposal': {'status': status, 'issues': [], 'acceptable_actions': actions}}

def prediction(key, status, action, **extra):
    return {'id': key, 'status': status, 'issues': [], 'action': action,
            'latency_ms': 10, 'execution_status': 'ok', **extra}

class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.cases = [case('v', 'violating', ['block']),
                      case('c', 'conforming', ['allow']),
                      case('i', 'insufficient', ['clarify', 'review'])]
        self.predictions = [prediction('v', 'violating', 'block'),
                            prediction('c', 'conforming', 'allow'),
                            prediction('i', 'insufficient', 'clarify')]

    def test_perfect_diagnostic_not_ranking(self):
        result = evaluate(self.cases, self.predictions)
        self.assertFalse(result['eligible_for_ranking'])
        self.assertEqual(result['classification_success_subset']['macro_f1_supported_classes'], 1)
        self.assertEqual(result['automatic_coverage']['rate'], 2 / 3)
        self.assertIsNone(result['calibration_available_subset']['brier'])

    def test_missing_stays_in_denominator(self):
        result = evaluate(self.cases, self.predictions[1:])
        self.assertEqual(result['missing_ids'], ['v'])
        self.assertEqual(result['failure_rate']['rate'], 1 / 3)
        self.assertEqual(result['all_request_status_correct']['rate'], 2 / 3)
        self.assertEqual(result['violating_unresolved_failure']['rate'], 1)
        self.assertEqual(result['unknown_action_rate']['count'], 1)

    def test_timeout_explicit_fallback_is_not_model_success(self):
        self.predictions[0] = prediction('v', None, 'block', execution_status='timeout')
        result = evaluate(self.cases, self.predictions)
        self.assertEqual(result['action_agreement_all_including_explicit_fallback']['rate'], 1)
        self.assertEqual(result['failure_rate']['count'], 1)
        self.assertEqual(result['automatic_coverage']['count'], 1)

    def test_all_refusal_does_not_win(self):
        for row in self.predictions:
            row['action'] = 'block'
            row['status'] = 'violating'
        result = evaluate(self.cases, self.predictions)
        self.assertEqual(result['normal_known_nonallow']['rate'], 1)
        self.assertEqual(result['action_agreement_all_including_explicit_fallback']['rate'], 1 / 3)
        self.assertAlmostEqual(result['classification_success_subset']['macro_f1_supported_classes'], 1 / 6)

    def test_all_review_has_zero_automatic_coverage(self):
        for row in self.predictions:
            row['action'] = 'review'
        result = evaluate(self.cases, self.predictions)
        self.assertEqual(result['automatic_coverage']['rate'], 0)
        self.assertIsNone(result['automatic_action_error']['rate'])
        self.assertEqual(result['normal_known_nonallow']['rate'], 1)

    def test_calibration_hand_computed(self):
        self.predictions[0]['status_probs'] = {'violating': 0.5, 'conforming': 0.25, 'insufficient': 0.25}
        metric = evaluate(self.cases, self.predictions)['calibration_available_subset']
        self.assertEqual(metric['brier'], 0.375)
        self.assertAlmostEqual(metric['nll'], math.log(2))
        self.assertEqual(metric['coverage'], 1 / 3)

    def test_invalid_probabilities_rejected(self):
        for value in [float('nan'), float('inf'), True, -0.1, 1.2]:
            with self.subTest(value=value):
                self.predictions[0]['status_probs'] = {'violating': value, 'conforming': 0, 'insufficient': 0}
                with self.assertRaises(ValueError):
                    evaluate(self.cases, self.predictions)

    def test_probability_sum_rejected(self):
        self.predictions[0]['status_probs'] = dict.fromkeys(('violating', 'conforming', 'insufficient'), 0.2)
        with self.assertRaises(ValueError):
            evaluate(self.cases, self.predictions)

    def test_duplicate_and_unknown_id_rejected(self):
        for extra in [self.predictions[0], prediction('unknown', 'conforming', 'allow')]:
            with self.assertRaises(ValueError):
                evaluate(self.cases, self.predictions + [extra])

    def test_empty_predictions_and_absent_support(self):
        result = evaluate(self.cases, [])
        self.assertEqual(result['failure_rate']['rate'], 1)
        self.assertIsNone(result['classification_success_subset']['macro_f1_supported_classes'])
        result = evaluate(self.cases[:1], self.predictions[:1])
        self.assertIsNone(result['classification_success_subset']['per_class']['conforming']['f1'])

    def test_latency_nearest_rank_and_bool_rejection(self):
        for p, latency in zip(self.predictions, [10, 20, 100]):
            p['latency_ms'] = latency
        metrics = evaluate(self.cases, self.predictions)['latency_observed_ms']
        self.assertEqual((metrics['p50'], metrics['p95']), (20, 100))
        self.predictions[0]['latency_ms'] = True
        with self.assertRaises(ValueError):
            evaluate(self.cases, self.predictions)

    def test_unparsed_output_is_failure(self):
        self.predictions[0] = prediction('v', None, None, execution_status='invalid')
        result = evaluate(self.cases, self.predictions)
        self.assertEqual(result['failure_rate']['count'], 1)
        self.assertEqual(result['unknown_action_rate']['count'], 1)

    def test_no_reference_leakage_even_extra_input_fields(self):
        source = copy.deepcopy(self.cases)
        source[0]['input']['answer'] = 'SECRET'
        view = input_view(source)
        self.assertEqual(set(view[0]), {'id', 'input'})
        self.assertEqual(set(view[0]['input']), {'surface', 'context', 'target', 'policy'})
        self.assertNotIn('SECRET', json.dumps(view))
        self.assertNotIn('proposal', json.dumps(view))

    def test_gold_or_test_data_refused(self):
        self.cases[0]['split'] = 'test'
        with self.assertRaises(ValueError):
            evaluate(self.cases, self.predictions)

    def test_json_duplicate_keys_and_nonfinite_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rows.jsonl'
            for content in ['{"id":"a","id":"b"}', '{"x":NaN}']:
                path.write_text(content, encoding='utf-8')
                with self.assertRaises(ValueError):
                    read_jsonl(path)

    def test_cli_export_no_overwrite_and_missing_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'inputs.jsonl'
            command = [sys.executable, str(HERE / 'export_inputs.py'), '--output', str(output)]
            run = subprocess.run(command, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            contents = output.read_bytes()
            self.assertEqual(len(read_jsonl(output)), 20)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), contents)
            predictions = Path(directory) / 'empty.jsonl'
            predictions.write_text('', encoding='utf-8')
            run = subprocess.run([sys.executable, str(HERE / 'evaluate.py'), '--predictions', str(predictions)], capture_output=True)
            self.assertEqual(run.returncode, 2)
            report = json.loads(run.stdout)
            self.assertEqual(report['failure_rate']['count'], 20)
            self.assertFalse(report['eligible_for_ranking'])

if __name__ == '__main__':
    unittest.main()
