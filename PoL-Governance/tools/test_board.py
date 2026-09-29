import unittest
from board import fields, task_location


class BoardTests(unittest.TestCase):
    def test_nested_module(self):
        self.assertEqual(task_location('origin/pol/DATA-01/alice', 'origin', 'PoL-Governance'),
                         ('DATA-01', 'PoL-Governance/tasks/DATA-01-alice.md'))

    def test_standalone_module(self):
        self.assertEqual(task_location('origin/pol/MODEL-02/kev', 'origin', ''),
                         ('MODEL-02', 'tasks/MODEL-02-kev.md'))

    def test_invalid_or_other_remote(self):
        for ref in ['origin/pol/../name', 'upstream/pol/DATA-01/a', 'origin/main', 'origin/pol/DATA-01/a/b']:
            self.assertIsNone(task_location(ref, 'origin', ''))

    def test_status_and_owner(self):
        self.assertEqual(fields('- 领取人：agent-a\n- 状态：阻塞\n'), {'owner': 'agent-a', 'status': '阻塞'})

    def test_blank_owner_does_not_consume_next_line(self):
        self.assertEqual(fields('- 领取人：\n- 状态：进行中\n')['owner'], '')


if __name__ == '__main__':
    unittest.main()
