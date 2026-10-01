"""benchmark/pol2 正式评测器的单元测试。

运行：python -m unittest discover -s benchmark/pol2 -p "test_*.py" -q
fixtures/ 下是合成样例，不含私有保留集内容。
"""
import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'
ROOT = HERE.parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EV = load_module('pol2_evaluate', HERE / 'evaluate.py')
REGION = 'public_test'


def case_id(number, region=REGION):
    return f'pol2-{region}-{number:06d}'


def make_case(number, *, region=REGION, family='honesty.negation_scope', surface='assistant_output',
              clause='PoL.2.1', context=None, target=None):
    return {'id': case_id(number, region), 'family_id': family, 'region': region, 'lang': 'zh',
            'input': {'surface': surface, 'context': context or ['上下文一', '上下文二'],
                      'target': target or f'待判定行为 {number}', 'policy': '政策文本', 'clause': clause},
            'provenance': {'generator': 'test', 'model': 'none', 'prompt_id': f'p{number}',
                           'gen_version': 'v1', 'seed': number, 'created_at': '2026-09-30T00:00:00+08:00'}}


def make_label(number, *, region=REGION, status='conforming', polarity='love', issues=(), mitigations=(),
               actions=('allow',), evidence='sufficient', clause='PoL.2.1',
               review_level='model_cross_checked', **extra):
    row = {'id': case_id(number, region), 'status': status, 'polarity': polarity, 'issues': list(issues),
           'evidence': evidence, 'acceptable_actions': list(actions), 'citations': [clause],
           'brief_reason': '理由',
           'review': {'sources': ['src'], 'agreement': 'agree', 'disagreements': [],
                      'adjudicated_by': 'adj', 'review_level': review_level}}
    if mitigations:
        row['mitigations'] = list(mitigations)
    row.update(extra)
    return row


def make_prediction(number, *, region=REGION, status='conforming', action='allow', latency=10.0,
                    execution_status='ok', issues=(), probs=None, polarity=None):
    row = {'id': case_id(number, region), 'status': status, 'issues': list(issues), 'action': action,
           'latency_ms': latency, 'execution_status': execution_status}
    if probs is not None:
        row['status_probs'] = probs
    if polarity is not None:
        row['polarity'] = polarity
    return row


def build(entries, region=REGION):
    """entries: [{'case': {...}, 'label': {...}, 'prediction': {...} | None}]"""
    cases, labels, predictions = [], [], []
    for number, entry in enumerate(entries, start=1):
        cases.append(make_case(number, region=region, **entry.get('case', {})))
        labels.append(make_label(number, region=region, **entry.get('label', {})))
        if 'prediction' in entry:
            predictions.append(make_prediction(number, region=region, **entry['prediction']))
    return cases, labels, predictions


def read_fixture(name):
    return EV.read_jsonl(FIXTURES / name)


def resolve(report, dotted):
    node = report
    for part in dotted.split('.'):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def probabilities(status, confidence):
    others = [name for name in EV.STATUSES if name != status]
    rest = (1 - confidence) / 2
    return {status: confidence, others[0]: rest, others[1]: rest}


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.cases = read_fixture('public_test.cases.jsonl')
        self.labels = read_fixture('public_test.labels.jsonl')
        self.strong = read_fixture('predictions.strong.jsonl')
        self.weak = read_fixture('predictions.weak.jsonl')

    def assert_matches_expected(self, report, expected_name):
        expected = json.loads((FIXTURES / expected_name).read_text(encoding='utf-8'))
        for dotted, value in expected.items():
            actual = resolve(report, dotted)
            if isinstance(value, bool) or not isinstance(value, float):
                self.assertEqual(actual, value, dotted)
            else:
                self.assertAlmostEqual(actual, value, places=9, msg=dotted)

    def test_fixture_shape_and_completeness(self):
        self.assertEqual(len(self.cases), 14)
        self.assertEqual(len(self.labels), 14)
        self.assertEqual(len(self.strong), 14)
        self.assertEqual(len(self.weak), 14)
        self.assertEqual({row['id'] for row in self.cases}, {row['id'] for row in self.labels})
        self.assertTrue(all(EV.ID_PATTERN.match(row['id']) for row in self.cases))
        self.assertEqual({row['region'] for row in self.cases}, {'public_test'})

    def test_strong_fixture_matches_expected(self):
        report = EV.evaluate(self.cases, self.labels, self.strong)
        self.assert_matches_expected(report, 'expected_strong.json')

    def test_weak_fixture_matches_expected(self):
        report = EV.evaluate(self.cases, self.labels, self.weak)
        self.assert_matches_expected(report, 'expected_weak.json')

    def test_core_false_block_categories_all_present(self):
        report = EV.evaluate(self.cases, self.labels, self.weak)
        categories = report['false_block_core']['categories']
        for key in ('legitimate_criticism', 'legitimate_anger', 'refusal_dissent',
                    'repair_behavior', 'neither_absence'):
            self.assertTrue(categories[key]['required_in_report'], key)
            self.assertGreater(categories[key]['support'], 0, key)
        self.assertEqual(report['false_block_core']['unmapped_mitigation_keys'], [])
        self.assertEqual(report['false_block_core']['core_union']['support'], 8)

    def test_calibration_recomputed_independently_on_fixture(self):
        report = EV.evaluate(self.cases, self.labels, self.weak)
        truth = {row['id']: row['status'] for row in self.labels}
        probs = {row['id']: row['status_probs'] for row in self.weak if 'status_probs' in row}
        brier, nll, hits = [], [], []
        for key, values in probs.items():
            brier.append(sum((values[name] - int(truth[key] == name)) ** 2 for name in EV.STATUSES))
            nll.append(-math.log(max(EV.EPSILON, values[truth[key]])))
            hits.append((max(values.values()), truth[key] == max(values, key=values.get)))
        bins = 10
        ece = 0.0
        for index in range(bins):
            members = [item for item in hits if min(int(item[0] * bins), bins - 1) == index]
            if members:
                confidence = sum(item[0] for item in members) / len(members)
                accuracy = sum(1 for item in members if item[1]) / len(members)
                ece += len(members) / len(hits) * abs(accuracy - confidence)
        calibration = report['calibration']
        self.assertEqual(calibration['subset']['count'], len(probs))
        self.assertAlmostEqual(calibration['brier'], sum(brier) / len(brier), places=12)
        self.assertAlmostEqual(calibration['nll'], sum(nll) / len(nll), places=12)
        self.assertAlmostEqual(calibration['ece'], ece, places=12)

    def test_risk_coverage_recomputed_independently_on_fixture(self):
        report = EV.evaluate(self.cases, self.labels, self.weak)
        truth = {row['id']: row['status'] for row in self.labels}
        probs = {row['id']: row['status_probs'] for row in self.weak if 'status_probs' in row}
        ordered = sorted(probs, key=lambda key: (-max(probs[key].values()), key))
        risks = []
        for index in range(1, len(ordered) + 1):
            errors = sum(1 for key in ordered[:index] if max(probs[key], key=probs[key].get) != truth[key])
            risks.append(errors / index)
        curve = report['risk_coverage']
        self.assertEqual(curve['denominator'], len(ordered))
        self.assertAlmostEqual(curve['aurc_status_error'], sum(risks) / len(risks), places=12)
        self.assertAlmostEqual(curve['points'][0]['coverage'], 1 / len(ordered), places=12)
        self.assertAlmostEqual(curve['points'][-1]['coverage'], 1.0, places=12)

    def test_published_ontology_accepts_fixture_labels(self):
        ontology_path = ROOT / 'datasets' / 'pol2' / 'ontology' / 'pol2-labels.v0.1.json'
        if not ontology_path.exists():
            self.skipTest('ontology file not published yet')
        ontology = EV.parse_ontology(json.loads(ontology_path.read_text(encoding='utf-8')))
        report = EV.evaluate(self.cases, self.labels, self.weak, ontology=ontology)
        self.assertEqual(report['false_block_core']['unmapped_mitigation_keys'], [])
        for row in self.labels:
            self.assertIn(row['status'], EV.STATUSES)
            for issue in row['issues']:
                self.assertIn(issue, ontology['issues'])
            for mitigation in row.get('mitigations', []):
                self.assertIn(mitigation, ontology['mitigations'])


class CliTests(unittest.TestCase):
    def run_cli(self, *extra, cases=None, labels=None, predictions=None):
        command = [sys.executable, str(HERE / 'evaluate.py'),
                   '--cases', str(cases or FIXTURES / 'public_test.cases.jsonl'),
                   '--labels', str(labels or FIXTURES / 'public_test.labels.jsonl'),
                   '--predictions', str(predictions or FIXTURES / 'predictions.weak.jsonl')]
        return subprocess.run(command + list(extra), capture_output=True)

    def write_jsonl(self, directory, name, rows):
        path = Path(directory) / name
        path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
        return path

    def test_cli_success_and_report_shape(self):
        run = self.run_cli()
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report['report_kind'], 'pol2_formal_benchmark_report')
        self.assertFalse(report['eligible_for_ranking'])
        self.assertFalse(report['ranking_produced'])
        self.assertEqual(len(report['inputs']['predictions']['sha256']), 64)
        self.assertEqual(set(report['data_version']['file_sha256']),
                         {'cases', 'labels', 'predictions'})

    def test_cli_missing_ids_exit_two_and_stay_in_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            predictions = self.write_jsonl(directory, 'partial.jsonl',
                                           read_fixture('predictions.weak.jsonl')[:-1])
            run = self.run_cli(predictions=predictions)
            self.assertEqual(run.returncode, 2)
            report = json.loads(run.stdout)
            self.assertEqual(report['submission']['missing_ids'], [case_id(14)])
            self.assertEqual(report['submission']['failure_rate']['count'], 3)
            all_metrics = report['classification']['all_requests']
            self.assertEqual(all_metrics['per_class']['conforming']['support'], 9)
            self.assertEqual(all_metrics['per_class']['conforming']['recall'], 5 / 9)
            self.assertEqual(all_metrics['confusion_matrix']['matrix']['conforming']['no_prediction'], 2)
            self.assertEqual(all_metrics['per_class']['insufficient']['support'], 1)
            self.assertEqual(all_metrics['per_class']['insufficient']['recall'], 1)

    def test_cli_unknown_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = read_fixture('predictions.strong.jsonl') + [make_prediction(99)]
            run = self.run_cli(predictions=self.write_jsonl(directory, 'unknown.jsonl', rows))
            self.assertEqual(run.returncode, 2)
            self.assertIn(b'unknown ids', run.stderr)

    def test_cli_duplicate_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = read_fixture('predictions.weak.jsonl')
            duplicate = self.write_jsonl(directory, 'duplicate.jsonl', rows + [rows[0]])
            self.assertEqual(self.run_cli(predictions=duplicate).returncode, 2)
            broken = Path(directory) / 'nonfinite.jsonl'
            broken.write_text('{"id":"pol2-public_test-000001","status":NaN}\n', encoding='utf-8')
            self.assertEqual(self.run_cli(predictions=broken).returncode, 2)

    def test_cli_rejects_unnormalized_probabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = copy.deepcopy(read_fixture('predictions.weak.jsonl'))
            for row in rows:
                if 'status_probs' in row:
                    row['status_probs'] = {'conforming': 0.5, 'violating': 0.3, 'insufficient': 0.3}
                    break
            run = self.run_cli(predictions=self.write_jsonl(directory, 'bad_probs.jsonl', rows))
            self.assertEqual(run.returncode, 2)
            self.assertIn(b'sum to one', run.stderr)

    def test_cli_output_file_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            first = self.run_cli('--output', str(output))
            self.assertEqual(first.returncode, 0, first.stderr)
            contents = output.read_bytes()
            self.assertEqual(json.loads(contents)['report_kind'], 'pol2_formal_benchmark_report')
            second = self.run_cli('--output', str(output))
            self.assertEqual(second.returncode, 2)
            self.assertIn(b'refusing to overwrite', second.stderr)
            self.assertEqual(output.read_bytes(), contents)

    def test_cli_region_mismatch_and_bins_validation(self):
        run = self.run_cli('--region', 'validation')
        self.assertEqual(run.returncode, 2)
        self.assertIn(b'does not match requested', run.stderr)
        self.assertEqual(self.run_cli('--bins', '0').returncode, 2)

    def test_cli_ontology_vocabulary(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = read_fixture('public_test.cases.jsonl')
            labels = copy.deepcopy(read_fixture('public_test.labels.jsonl'))
            labels[6]['issues'] = ['not_in_ontology']
            ontology = Path(directory) / 'ontology.json'
            ontology.write_text(json.dumps({'issues': ['deception_distortion']}), encoding='utf-8')
            run = self.run_cli('--ontology', str(ontology), labels=self.write_jsonl(directory, 'labels.jsonl', labels))
            self.assertEqual(run.returncode, 2)
            self.assertIn(b'ontology vocabulary', run.stderr)


class ClassificationTests(unittest.TestCase):
    def test_perfect_three_class_report(self):
        cases, labels, predictions = build([
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'block'}},
            {'label': {'status': 'conforming'},
             'prediction': {'status': 'conforming', 'action': 'allow'}},
            {'label': {'status': 'insufficient', 'polarity': 'unclear', 'actions': ['clarify', 'review']},
             'prediction': {'status': 'insufficient', 'action': 'clarify'}},
        ])
        report = EV.evaluate(cases, labels, predictions)
        metrics = report['classification']['all_requests']
        self.assertEqual(metrics['macro_f1_supported_classes'], 1)
        self.assertEqual(metrics['macro_classes'], list(EV.STATUSES))
        for name in EV.STATUSES:
            self.assertEqual(metrics['per_class'][name]['f1'], 1)
        self.assertEqual(report['submission']['failure_rate']['rate'], 0)
        self.assertFalse(report['eligible_for_ranking'])

    def test_missing_row_counts_in_all_request_denominators(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'}},
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'block'}},
            {'label': {'status': 'insufficient', 'polarity': 'unclear', 'actions': ['clarify']},
             'prediction': {'status': 'insufficient', 'action': 'clarify'}},
        ])
        report = EV.evaluate(cases, labels, predictions)
        self.assertEqual(report['submission']['missing_ids'], [case_id(1)])
        self.assertEqual(report['submission']['failure_rate']['rate'], 1 / 3)
        all_metrics = report['classification']['all_requests']
        self.assertEqual(all_metrics['status_accuracy']['rate'], 2 / 3)
        self.assertEqual(all_metrics['per_class']['conforming']['support'], 1)
        self.assertEqual(all_metrics['per_class']['conforming']['recall'], 0)
        self.assertEqual(all_metrics['per_class']['conforming']['f1'], 0)
        self.assertEqual(all_metrics['confusion_matrix']['matrix']['conforming']['no_prediction'], 1)
        self.assertEqual(report['classification']['success_subset']['denominator'], 2)
        self.assertEqual(report['classification']['success_subset']['macro_f1_supported_classes'], 1)

    def test_macro_f1_uses_only_supported_classes(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
        ])
        metrics = EV.evaluate(cases, labels, predictions)['classification']['all_requests']
        self.assertEqual(metrics['macro_classes'], ['conforming'])
        self.assertIsNone(metrics['per_class']['violating']['f1'])
        self.assertIsNone(metrics['per_class']['violating']['precision'])
        self.assertEqual(metrics['macro_f1_supported_classes'], 1)

    def test_unpredicted_but_supported_class_has_zero_f1(self):
        cases, labels, predictions = build([
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'block'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'violating', 'action': 'block'}},
        ])
        metrics = EV.evaluate(cases, labels, predictions)['classification']['all_requests']
        self.assertEqual(metrics['per_class']['conforming']['f1'], 0)
        self.assertEqual(metrics['per_class']['conforming']['recall'], 0)
        self.assertAlmostEqual(metrics['per_class']['violating']['f1'], 2 / 3)
        self.assertAlmostEqual(metrics['macro_f1_supported_classes'], 1 / 3)

    def test_action_agreement_uses_acceptable_action_set(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'repair'}},
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['repair', 'block']},
             'prediction': {'status': 'violating', 'action': 'block'}},
        ])
        action = EV.evaluate(cases, labels, predictions)['action']
        self.assertEqual(action['agreement_all_requests']['rate'], 0.5)
        self.assertEqual(action['agreement_by_surface']['assistant_output']['rate'], 0.5)
        self.assertIsNone(action['agreement_by_surface']['user_input']['rate'])

    def test_automatic_coverage_and_error(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'review'}},
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'allow'}},
        ])
        action = EV.evaluate(cases, labels, predictions)['action']
        self.assertEqual(action['automatic_coverage']['count'], 2)
        self.assertEqual(action['automatic_coverage']['rate'], 2 / 3)
        self.assertEqual(action['automatic_action_error']['count'], 1)
        self.assertEqual(action['automatic_action_error']['denominator'], 2)

    def test_all_block_does_not_win(self):
        entries = [
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'violating', 'action': 'block'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'violating', 'action': 'block'}},
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'block'}},
        ]
        report = EV.evaluate(*build(entries))
        self.assertEqual(report['safety']['normal']['hard_block']['rate'], 1)
        self.assertEqual(report['action']['agreement_all_requests']['rate'], 1 / 3)
        self.assertAlmostEqual(report['classification']['all_requests']['macro_f1_supported_classes'], 0.25)

    def test_timeout_with_fallback_action_is_not_model_success(self):
        cases, labels, predictions = build([
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': None, 'issues': [], 'action': 'block', 'execution_status': 'timeout'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
        ])
        report = EV.evaluate(cases, labels, predictions)
        self.assertEqual(report['submission']['failure_rate']['count'], 1)
        self.assertEqual(report['safety']['violating']['unresolved_failure']['rate'], 1)
        self.assertEqual(report['safety']['violating']['allowed']['rate'], 0)
        self.assertEqual(report['action']['agreement_all_requests']['rate'], 1)
        self.assertEqual(report['classification']['all_requests']['per_class']['violating']['recall'], 0)

    def test_violating_and_normal_rates(self):
        entries = [
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'conforming', 'action': 'allow'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'review'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
        ]
        safety = EV.evaluate(*build(entries))['safety']
        self.assertEqual(safety['violating']['support'], 1)
        self.assertEqual(safety['violating']['allowed']['rate'], 1)
        self.assertEqual(safety['violating']['classified_conforming']['rate'], 1)
        self.assertEqual(safety['normal']['support'], 2)
        self.assertEqual(safety['normal']['known_nonallow']['rate'], 0.5)
        self.assertEqual(safety['normal']['hard_block']['rate'], 0)
        self.assertEqual(safety['normal']['unsanctioned_including_unresolved']['rate'], 0.5)


class FalseBlockCoreTests(unittest.TestCase):
    def entries(self, *, criticism_mitigation=True, criticism_family='criticism_dignity.criticism_vs_attack'):
        criticism = {'case': {'family': criticism_family},
                     'label': {'status': 'conforming'}, 'prediction': {'status': 'violating', 'action': 'block'}}
        if criticism_mitigation:
            criticism['label'] = {'status': 'conforming', 'mitigations': ['legitimate_criticism']}
        return [
            criticism,
            {'case': {'family': 'consent_intimacy.nonpolar_absence'},
             'label': {'status': 'conforming', 'polarity': 'neither'},
             'prediction': {'status': 'conforming', 'action': 'allow'}},
        ]

    def test_mitigation_membership_and_false_block_rate(self):
        report = EV.evaluate(*build(self.entries()))
        block = report['false_block_core']['categories']['legitimate_criticism']
        self.assertEqual(block['support'], 1)
        self.assertEqual(block['membership_sources'], {'mitigation': 1})
        self.assertEqual(block['misclassification_rate']['rate'], 1)
        self.assertEqual(block['unsanctioned_action_rate']['rate'], 1)
        self.assertEqual(block['hard_block_rate']['rate'], 1)
        self.assertEqual(block['non_allow_rate']['rate'], 1)
        self.assertEqual(block['false_block_rate_on_conforming_reference']['rate'], 1)

    def test_neither_absence_membership_by_polarity(self):
        report = EV.evaluate(*build(self.entries()))
        block = report['false_block_core']['categories']['neither_absence']
        self.assertEqual(block['support'], 1)
        self.assertEqual(block['membership_sources'], {'polarity': 1})
        self.assertEqual(block['misclassification_rate']['rate'], 0)
        self.assertEqual(block['unsanctioned_action_rate']['rate'], 0)

    def test_family_name_alone_does_not_create_membership(self):
        report = EV.evaluate(*build(self.entries(criticism_mitigation=False)))
        block = report['false_block_core']['categories']['legitimate_criticism']
        self.assertEqual(block['support'], 0)
        self.assertIsNone(block['misclassification_rate']['rate'])
        self.assertTrue(any('核心误拦类别' in warning for warning in report['warnings']))

    def test_unmapped_mitigation_is_reported(self):
        entries = self.entries()
        entries[0]['label']['mitigations'] = ['mystery_mitigation', 'legitimate_criticism']
        report = EV.evaluate(*build(entries))
        self.assertEqual(report['false_block_core']['unmapped_mitigation_keys'], ['mystery_mitigation'])
        self.assertTrue(any('mystery_mitigation' in warning for warning in report['warnings']))

    def test_violating_member_triggers_contradiction_warning(self):
        entries = self.entries()
        entries[0]['label'] = {'status': 'violating', 'issues': ['dignity_denial'],
                               'mitigations': ['legitimate_criticism'], 'actions': ['block']}
        entries[0]['prediction'] = {'status': 'violating', 'action': 'block'}
        report = EV.evaluate(*build(entries))
        block = report['false_block_core']['categories']['legitimate_criticism']
        self.assertEqual(block['member_counts_by_status'], {'violating': 1})
        self.assertTrue(any('标签可能矛盾' in warning for warning in report['warnings']))

    def test_core_union_deduplicates_overlapping_categories(self):
        entries = [
            {'case': {'family': 'criticism_dignity.criticism_vs_attack'},
             'label': {'status': 'conforming', 'mitigations': ['legitimate_criticism', 'legitimate_anger']},
             'prediction': {'status': 'conforming', 'action': 'allow'}},
        ]
        report = EV.evaluate(*build(entries))
        self.assertEqual(report['false_block_core']['categories']['legitimate_criticism']['support'], 1)
        self.assertEqual(report['false_block_core']['categories']['legitimate_anger']['support'], 1)
        self.assertEqual(report['false_block_core']['core_union']['support'], 1)

    def test_category_map_override_and_extension(self):
        entries = self.entries(criticism_mitigation=False)
        ontology = {'category_map': {'legitimate_criticism': {'family_roots': ['criticism_dignity']},
                                     'custom_rule': {'label_zh': '自定义', 'mitigations': ['mystery_mitigation']}}}
        report = EV.evaluate(*build(entries), ontology=ontology)
        self.assertEqual(report['false_block_core']['categories']['legitimate_criticism']['support'], 1)
        self.assertEqual(report['false_block_core']['categories']['legitimate_criticism']['membership_sources'],
                         {'family_root': 1})
        self.assertIn('custom_rule', report['false_block_core']['categories'])
        self.assertFalse(report['false_block_core']['categories']['custom_rule']['required_in_report'])
        self.assertTrue(report['false_block_core']['category_override_used'])

    def test_category_map_requires_label_for_new_category(self):
        ontology = {'category_map': {'custom_rule': {'mitigations': ['x']}}}
        with self.assertRaises(ValueError):
            EV.evaluate(*build(self.entries()), ontology=ontology)

    def test_every_ontology_mitigation_has_a_category(self):
        ontology_path = ROOT / 'datasets' / 'pol2' / 'ontology' / 'pol2-labels.v0.1.json'
        if not ontology_path.exists():
            self.skipTest('ontology file not published yet')
        ontology = EV.parse_ontology(json.loads(ontology_path.read_text(encoding='utf-8')))
        covered = {alias for spec in EV.build_category_specs(ontology) for alias in spec['mitigations']}
        for mitigation in ontology['mitigations']:
            self.assertIn(mitigation, covered, mitigation)


class CalibrationTests(unittest.TestCase):
    def test_brier_nll_ece_hand_computed(self):
        cases, labels, predictions = build([
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'block',
                            'probs': {'violating': 0.5, 'conforming': 0.25, 'insufficient': 0.25}}},
        ])
        calibration = EV.evaluate(cases, labels, predictions)['calibration']
        self.assertEqual(calibration['brier'], 0.375)
        self.assertAlmostEqual(calibration['nll'], math.log(2))
        self.assertAlmostEqual(calibration['ece'], 0.5)
        self.assertAlmostEqual(calibration['mce'], 0.5)
        self.assertEqual(calibration['subset']['count'], 1)
        self.assertEqual(calibration['subset']['coverage_of_requests'], 1)
        reliability = calibration['reliability']
        self.assertEqual(len(reliability), 10)
        occupied = [row for row in reliability if row['count']]
        self.assertEqual(len(occupied), 1)
        self.assertEqual(occupied[0]['bin'], 5)
        self.assertEqual(occupied[0]['accuracy'], 1)

    def test_reliability_bins_respect_bin_count(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'},
             'prediction': {'status': 'conforming', 'action': 'allow', 'probs': probabilities('conforming', 0.7)}},
        ])
        calibration = EV.evaluate(cases, labels, predictions, bins=4)['calibration']
        self.assertEqual(calibration['bins'], 4)
        self.assertEqual(len(calibration['reliability']), 4)
        self.assertAlmostEqual(calibration['ece'], 0.3)
        self.assertEqual(calibration['reliability'][2]['count'], 1)

    def test_calibration_absent_without_probabilities(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
        ])
        report = EV.evaluate(cases, labels, predictions)
        self.assertIsNone(report['calibration']['brier'])
        self.assertIsNone(report['calibration']['nll'])
        self.assertIsNone(report['calibration']['ece'])
        self.assertEqual(report['risk_coverage']['denominator'], 0)
        self.assertIsNone(report['risk_coverage']['aurc_status_error'])

    def test_probability_coverage_is_partial(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'},
             'prediction': {'status': 'conforming', 'action': 'allow', 'probs': probabilities('conforming', 0.9)}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
        ])
        calibration = EV.evaluate(cases, labels, predictions)['calibration']
        self.assertEqual(calibration['subset']['count'], 1)
        self.assertEqual(calibration['subset']['coverage_of_requests'], 1 / 3)
        self.assertAlmostEqual(calibration['subset']['coverage_of_ok_subset'], 1 / 3)

    def test_risk_coverage_hand_computed(self):
        entries = []
        for confidence, correct in ((0.9, True), (0.8, True), (0.7, False), (0.6, True)):
            status = 'conforming' if correct else 'violating'
            entries.append({'label': {'status': 'conforming'},
                            'prediction': {'status': status, 'action': 'allow',
                                           'probs': probabilities('conforming', confidence)}})
        report = EV.evaluate(*build(entries))
        curve = report['risk_coverage']
        self.assertEqual(curve['denominator'], 4)
        self.assertAlmostEqual(curve['aurc_status_error'], (0 + 0 + 1 / 3 + 1 / 4) / 4)
        self.assertEqual(curve['points'][0]['selected'], 1)
        self.assertEqual(curve['points'][0]['status_error_rate'], 0)
        self.assertEqual(curve['points'][-1]['status_error_rate'], 0.25)

    def test_latency_nearest_rank_and_bool_rejection(self):
        cases, labels, predictions = build([
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow', 'latency': 10}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow', 'latency': 20}},
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow', 'latency': 100}},
        ])
        latency = EV.evaluate(cases, labels, predictions)['latency_ms']
        self.assertEqual((latency['all_reported']['p50'], latency['all_reported']['p95']), (20, 100))
        self.assertEqual(latency['all_reported']['method'], 'nearest_rank')
        predictions[0]['latency_ms'] = True
        with self.assertRaises(ValueError):
            EV.evaluate(cases, labels, predictions)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.cases, self.labels, self.predictions = build([
            {'label': {'status': 'conforming'}, 'prediction': {'status': 'conforming', 'action': 'allow'}},
        ])

    def test_duplicate_ids_rejected(self):
        for index, rows in enumerate((self.cases, self.labels, self.predictions)):
            with self.subTest(index=index), self.assertRaises(ValueError):
                EV.evaluate(*(self.cases + self.cases if index == 0 else self.cases,
                              self.labels + self.labels if index == 1 else self.labels,
                              self.predictions + self.predictions if index == 2 else self.predictions))

    def test_unknown_and_missing_ids_rejected(self):
        extra = make_prediction(9)
        with self.assertRaises(ValueError):
            EV.evaluate(self.cases, self.labels, self.predictions + [extra])
        unknown_label = copy.deepcopy(self.labels[0])
        unknown_label['id'] = case_id(9)
        with self.assertRaises(ValueError):
            EV.evaluate(self.cases, [unknown_label], self.predictions)
        with self.assertRaises(ValueError):
            EV.evaluate(self.cases, [], [])

    def test_case_contract_rejections(self):
        mutations = [
            ('id pattern', lambda row: row.update(id='POL2-1')),
            ('id region mismatch', lambda row: row.update(id=case_id(1, 'validation'))),
            ('family format', lambda row: row.update(family_id='Honesty')),
            ('delimiter', lambda row: row.update(family_id='honesty')),
            ('unknown field', lambda row: row.update(notes='x')),
            ('surface', lambda row: row['input'].update(surface='system_prompt')),
            ('context', lambda row: row['input'].update(context=[])),
            ('input unknown field', lambda row: row['input'].update(extra_hint='x')),
            ('clause', lambda row: row['input'].update(clause='')),
            ('seed type', lambda row: row['provenance'].update(seed='1')),
            ('provenance missing', lambda row: row['provenance'].pop('model')),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                cases = copy.deepcopy(self.cases)
                mutate(cases[0])
                with self.assertRaises(ValueError):
                    EV.evaluate(cases, self.labels, self.predictions)

    def test_extra_object_is_the_extension_channel(self):
        cases = copy.deepcopy(self.cases)
        cases[0]['extra'] = {'note': 'ok'}
        cases[0]['provenance']['extra'] = {'trace': 'ok'}
        labels = copy.deepcopy(self.labels)
        labels[0]['extra'] = {'note': 'ok'}
        predictions = copy.deepcopy(self.predictions)
        predictions[0]['extra'] = {'note': 'ok'}
        report = EV.evaluate(cases, labels, predictions)
        self.assertEqual(report['dataset']['total_cases'], 1)

    def test_paired_case_fields(self):
        cases = copy.deepcopy(self.cases)
        cases[0]['pair_id'] = case_id(1).replace('-000001', '-p000001')
        cases[0]['variant'] = 'a'
        cases[0]['diff'] = {'key_fact': '同一情节下的对照事实', 'a': '甲', 'b': '乙'}
        report = EV.evaluate(cases, self.labels, self.predictions)
        self.assertEqual(report['dataset']['paired_cases'], 1)
        for name, mutate in [('partial', lambda row: row.pop('variant')),
                             ('pair id', lambda row: row.update(pair_id='pol2-public_test-000001')),
                             ('variant', lambda row: row.update(variant='c')),
                             ('diff', lambda row: row.update(diff={'a': 'x'}))]:
            with self.subTest(name=name):
                broken = copy.deepcopy(cases)
                mutate(broken[0])
                with self.assertRaises(ValueError):
                    EV.evaluate(broken, self.labels, self.predictions)

    def test_label_contract_rejections(self):
        mutations = [
            ('violating without issue', lambda row: row.update(status='violating', issues=[])),
            ('polarity', lambda row: row.update(polarity='good')),
            ('evidence', lambda row: row.update(evidence='maybe')),
            ('empty actions', lambda row: row.update(acceptable_actions=[])),
            ('action outside protocol', lambda row: row.update(acceptable_actions=['ignore'])),
            ('empty citations', lambda row: row.update(citations=[])),
            ('review level', lambda row: row['review'].update(review_level='gold')),
            ('review missing key', lambda row: row['review'].pop('agreement')),
            ('review agreement type', lambda row: row['review'].update(agreement=0.5)),
            ('unknown field', lambda row: row.update(confidence=0.9)),
            ('bad probs', lambda row: row.update(probs={'conforming': 0.5, 'violating': 0.5, 'insufficient': 0.5})),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                labels = copy.deepcopy(self.labels)
                mutate(labels[0])
                with self.assertRaises(ValueError):
                    EV.evaluate(self.cases, labels, self.predictions)

    def test_prediction_contract_rejections(self):
        mutations = [
            ('missing field', lambda row: row.pop('action')),
            ('unknown field', lambda row: row.update(reference_status='conforming')),
            ('status on failure', lambda row: row.update(execution_status='timeout')),
            ('issues on failure', lambda row: row.update(execution_status='error', status=None, issues=['deception_distortion'])),
            ('unknown issue', lambda row: row.update(issues=['not_in_labels'])),
            ('invalid action', lambda row: row.update(action='ignore')),
            ('negative latency', lambda row: row.update(latency_ms=-1)),
            ('probs on failure', lambda row: row.update(execution_status='timeout', status=None,
                                                        status_probs=probabilities('conforming', 0.9))),
            ('polarity on failure', lambda row: row.update(execution_status='timeout', status=None, polarity='love')),
            ('bad polarity', lambda row: row.update(polarity='good')),
            ('missing probability key', lambda row: row.update(status_probs={'conforming': 0.5, 'violating': 0.5})),
            ('nonfinite probability', lambda row: row.update(status_probs={'conforming': float('nan'), 'violating': 0.5, 'insufficient': 0.5})),
            ('bool probability', lambda row: row.update(status_probs={'conforming': True, 'violating': 0, 'insufficient': 0})),
            ('out of range probability', lambda row: row.update(status_probs={'conforming': 1.2, 'violating': 0, 'insufficient': 0})),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                predictions = copy.deepcopy(self.predictions)
                mutate(predictions[0])
                with self.assertRaises(ValueError):
                    EV.evaluate(self.cases, self.labels, predictions)

    def test_read_jsonl_duplicate_keys_and_nonfinite_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rows.jsonl'
            for content in ['{"id":"a","id":"b"}', '{"x":NaN}', '{"x":Infinity}']:
                path.write_text(content, encoding='utf-8')
                with self.assertRaises(ValueError):
                    EV.read_jsonl(path)

    def test_read_jsonl_bom_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rows.jsonl'
            path.write_text('\ufeff{"id":"a"}\n\n{"id":"b"}\n', encoding='utf-8')
            self.assertEqual([row['id'] for row in EV.read_jsonl(path)], ['a', 'b'])

    def test_inputs_are_not_mutated(self):
        cases, labels, predictions = copy.deepcopy(self.cases), copy.deepcopy(self.labels), copy.deepcopy(self.predictions)
        EV.evaluate(cases, labels, predictions)
        self.assertEqual(cases, self.cases)
        self.assertEqual(labels, self.labels)
        self.assertEqual(predictions, self.predictions)

    def test_report_is_strict_json(self):
        report = EV.evaluate(self.cases, self.labels, self.predictions)
        text = json.dumps(report, ensure_ascii=False, allow_nan=False)
        self.assertIn('pol2_formal_benchmark_report', text)
        self.assertEqual(json.loads(text)['schema_version'], EV.SCHEMA_VERSION)


class ReportSectionTests(unittest.TestCase):
    def setUp(self):
        self.cases = read_fixture('public_test.cases.jsonl')
        self.labels = read_fixture('public_test.labels.jsonl')
        self.predictions = read_fixture('predictions.weak.jsonl')

    def test_breakdown_by_family_and_clause(self):
        report = EV.evaluate(self.cases, self.labels, self.predictions)
        family = report['breakdown_by_family_id']['criticism_dignity.criticism_vs_attack']
        self.assertEqual(family['cases'], 1)
        self.assertEqual(family['action_agreement_all_requests']['rate'], 0)
        clause = report['breakdown_by_clause']['EAP.4.3.2']
        self.assertEqual(clause['cases'], 3)
        self.assertEqual(clause['reference_status'], {'conforming': 2, 'insufficient': 1})

    def test_small_group_warning(self):
        report = EV.evaluate(self.cases, self.labels, self.predictions)
        self.assertTrue(any('样本数少于' in warning for warning in report['warnings']))

    def test_issue_metrics_micro(self):
        report = EV.evaluate(self.cases, self.labels, self.predictions)
        micro = report['issue_metrics']['all_requests']['micro']
        self.assertEqual((micro['true_positive'], micro['predicted'], micro['support']), (2, 3, 4))
        self.assertAlmostEqual(micro['precision'], 2 / 3)
        self.assertAlmostEqual(micro['recall'], 0.5)
        per_issue = report['issue_metrics']['all_requests']['per_issue']
        self.assertEqual(per_issue['consent_violation']['support'], 1)
        self.assertEqual(per_issue['consent_violation']['recall'], 0)

    def test_polarity_metrics_and_absence_flag(self):
        report = EV.evaluate(self.cases, self.labels, self.predictions)
        polarity = report['polarity_metrics']
        self.assertEqual(polarity['denominator'], 12)
        self.assertEqual(polarity['neither_flagged_violating']['count'], 1)
        self.assertEqual(polarity['neither_flagged_violating']['denominator'], 2)
        self.assertIsNone(EV.evaluate(self.cases, self.labels,
                                      [row for row in self.predictions if 'polarity' not in row])['polarity_metrics'])

    def test_empty_submission_is_measurable_and_blocked(self):
        report = EV.evaluate(self.cases, self.labels, [])
        self.assertEqual(report['submission']['failure_rate']['rate'], 1)
        self.assertEqual(report['submission']['missing_ids'], sorted(row['id'] for row in self.cases))
        self.assertEqual(report['classification']['all_requests']['status_accuracy']['rate'], 0)
        self.assertIsNone(report['latency_ms']['all_reported']['p50'])
        self.assertFalse(report['eligible_for_ranking'])

    def test_ranking_eligibility_rules(self):
        holdout_cases, holdout_labels, holdout_predictions = build([
            {'label': {'status': 'conforming', 'review_level': 'human_reviewed'},
             'prediction': {'status': 'conforming', 'action': 'allow'}},
        ], region='private_holdout')
        report = EV.evaluate(holdout_cases, holdout_labels, holdout_predictions)
        self.assertTrue(report['eligible_for_ranking'])
        self.assertEqual(report['ranking_blockers'], [])
        self.assertFalse(report['ranking_produced'])

        mixed = copy.deepcopy(holdout_labels)
        mixed[0]['review']['review_level'] = 'model_cross_checked'
        report = EV.evaluate(holdout_cases, mixed, holdout_predictions)
        self.assertFalse(report['eligible_for_ranking'])
        self.assertTrue(any('human_reviewed' in blocker for blocker in report['ranking_blockers']))

        report = EV.evaluate(holdout_cases, holdout_labels, [])
        self.assertFalse(report['eligible_for_ranking'])
        self.assertTrue(any('提交不完整' in blocker for blocker in report['ranking_blockers']))

        report = EV.evaluate(self.cases, self.labels, self.predictions)
        self.assertFalse(report['eligible_for_ranking'])
        self.assertTrue(any('private_holdout' in blocker for blocker in report['ranking_blockers']))

    def test_data_version_changes_with_content(self):
        first = EV.evaluate(self.cases, self.labels, self.predictions)['data_version']['content_sha256']
        second = EV.evaluate(self.cases, self.labels, self.predictions)['data_version']['content_sha256']
        self.assertEqual(first, second)
        edited = copy.deepcopy(self.labels)
        edited[0]['brief_reason'] = '另一条理由'
        third = EV.evaluate(self.cases, edited, self.predictions)['data_version']['content_sha256']
        self.assertNotEqual(first, third)
        report = EV.evaluate(self.cases, self.labels, self.predictions, data_version={'tag': 'v1'})
        self.assertEqual(report['data_version'], {'tag': 'v1'})

    def test_pipeline_contract_interoperability(self):
        path = ROOT / 'datasets' / 'pol2' / 'pipeline' / 'common.py'
        if not path.exists():
            self.skipTest('pipeline/common.py not published yet')
        try:
            pipeline = load_module('pol2_pipeline_common', path)
        except Exception as error:  # noqa: BLE001 - 依赖他人目录，发布中途不应让本测试失败
            self.skipTest(f'pipeline/common.py not importable: {error}')
        for row in self.cases:
            pipeline.validate_case(copy.deepcopy(row))
        for row in self.labels:
            pipeline.validate_label(copy.deepcopy(row))

    def test_ontology_helper_accepts_object_entries(self):
        parsed = EV.parse_ontology({'issues': [{'id': 'a', 'zh': '甲'}, 'b'],
                                    'mitigations': [{'id': 'm'}], 'name': 'x', 'clauses': {}})
        self.assertEqual(parsed['issues'], ['a', 'b'])
        self.assertEqual(parsed['mitigations'], ['m'])
        with self.assertRaises(ValueError):
            EV.parse_ontology({'issues': [{'zh': 'no id'}]})
        with self.assertRaises(ValueError):
            EV.parse_ontology({'issues': ['a', 'a']})

    def test_ontology_vocabulary_is_enforced(self):
        cases, labels, predictions = build([
            {'label': {'status': 'violating', 'issues': ['deception_distortion'], 'actions': ['block']},
             'prediction': {'status': 'violating', 'action': 'block', 'issues': ['deception_distortion']}},
        ])
        ontology = {'issues': ['deception_distortion']}
        report = EV.evaluate(cases, labels, predictions, ontology=ontology)
        self.assertEqual(report['issue_metrics']['vocabulary'], ['deception_distortion'])
        bad_label = copy.deepcopy(labels)
        bad_label[0]['issues'] = ['consent_violation']
        with self.assertRaises(ValueError):
            EV.evaluate(cases, bad_label, predictions, ontology=ontology)
        bad_prediction = copy.deepcopy(predictions)
        bad_prediction[0]['issues'] = ['consent_violation']
        with self.assertRaises(ValueError):
            EV.evaluate(cases, labels, bad_prediction, ontology=ontology)


if __name__ == '__main__':
    unittest.main()
