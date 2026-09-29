import copy
import unittest
from annotations import compare, worksheet
from test_evaluate import case

class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.cases = [case('a', 'violating', ['block']), case('b', 'conforming', ['allow'])]
        self.left = worksheet(self.cases, 'reviewer-a')
        self.right = worksheet(self.cases, 'reviewer-b')

    def finish(self, row, status='conforming', actions=None):
        row.update(completion='complete', status=status, acceptable_actions=actions or ['allow'],
                   brief_reason='Observable reason', policy_dispute=False)

    def test_pending_not_agreement(self):
        report = compare(self.cases, self.left, self.right)
        self.assertEqual(report['coverage'], 0)
        self.assertIsNone(report['status_exact_agreement']['rate'])
        self.assertFalse(report['gold_created'])

    def test_partial_coverage_and_missing_rows(self):
        self.finish(self.left[0])
        self.finish(self.right[0])
        report = compare(self.cases, self.left, self.right[:1])
        self.assertEqual(report['coverage'], 0.5)
        self.assertEqual(report['status_exact_agreement']['rate'], 1)
        self.assertEqual(report['missing_ids']['reviewer-b'], ['b'])

    def test_disagreement_and_intersection_are_different(self):
        self.finish(self.left[0], 'insufficient', ['clarify', 'review'])
        self.finish(self.right[0], 'violating', ['review'])
        report = compare(self.cases, self.left, self.right)
        self.assertEqual(report['status_exact_agreement']['rate'], 0)
        self.assertEqual(report['action_set_exact_agreement']['rate'], 0)
        self.assertEqual(report['action_intersection_nonempty']['rate'], 1)
        self.assertEqual(report['disagreements'][0]['flags'], ['status', 'action_set'])

    def test_policy_dispute_even_when_labels_agree(self):
        self.finish(self.left[0])
        self.finish(self.right[0])
        self.left[0]['policy_dispute'] = True
        report = compare(self.cases, self.left, self.right)
        self.assertEqual(report['policy_dispute_cases'], ['a'])
        self.assertEqual(report['disagreements'][0]['flags'], ['policy_interpretation'])

    def test_same_reviewer_refused(self):
        with self.assertRaises(ValueError):
            compare(self.cases, self.left, self.left)

    def test_modified_input_refused(self):
        self.left[0]['input']['policy'] = 'new policy'
        with self.assertRaises(ValueError):
            compare(self.cases, self.left, self.right)

    def test_completed_missing_reason_refused(self):
        self.finish(self.left[0])
        self.left[0]['brief_reason'] = ' '
        with self.assertRaises(ValueError):
            compare(self.cases, self.left, self.right)

    def test_duplicate_unknown_and_mixed_reviewer_refused(self):
        variants = [self.left + [copy.deepcopy(self.left[0])], copy.deepcopy(self.left), copy.deepcopy(self.left)]
        variants[1][0]['id'] = 'unknown'
        variants[2][0]['annotator_id'] = 'different'
        for rows in variants:
            with self.assertRaises(ValueError):
                compare(self.cases, rows, self.right)

    def test_template_contains_no_labels(self):
        row = self.left[0]
        self.assertNotIn('proposal', row)
        self.assertNotIn('family_id', row)
        self.assertIsNone(row['status'])
        self.assertEqual(row['acceptable_actions'], [])

if __name__ == '__main__':
    unittest.main()
