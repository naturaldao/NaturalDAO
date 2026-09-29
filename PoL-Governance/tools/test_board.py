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
        result = fields('- 领取人：agent-a\n- 状态：阻塞\n')
        self.assertEqual(result['owner'], 'agent-a')
        self.assertEqual(result['status'], '阻塞')
        self.assertEqual(result['agent'], '')

    def test_task_table_and_handoff(self):
        result = fields('| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |\n'
                        '|---|---|\n| Alice / reviewer-a (Sol) | 阻塞；等待标注 |\n'
                        '- 更新时间：2026-09-29 12:00 +08:00\n'
                        '- 下一步：检查分歧\n- 阻塞 / 需要谁帮助：Bob\n')
        self.assertEqual(result['owner'], 'Alice')
        self.assertEqual(result['agent'], 'reviewer-a (Sol)')
        self.assertEqual(result['status'], '阻塞；等待标注')
        self.assertEqual(result['updated_at'], '2026-09-29 12:00 +08:00')
        self.assertEqual(result['next'], '检查分歧')
        self.assertEqual(result['blocker'], 'Bob')

    def test_empty_table_cells(self):
        result = fields('| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |\n|---|---|\n| | |\n')
        self.assertEqual((result['owner'], result['agent'], result['status']), ('', '', ''))

    def test_blank_owner_does_not_consume_next_line(self):
        self.assertEqual(fields('- 领取人：\n- 状态：进行中\n')['owner'], '')


if __name__ == '__main__':
    unittest.main()
