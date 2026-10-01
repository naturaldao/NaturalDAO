import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from board import configure_stdio, fields, task_location


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


class StdioTests(unittest.TestCase):
    """The report must not depend on the host console code page."""

    def test_configure_stdio_switches_to_utf8(self):
        stream = io.TextIOWrapper(io.BytesIO(), encoding='gbk')
        original = sys.stdout
        try:
            sys.stdout = stream
            configure_stdio()
            self.assertEqual(stream.encoding, 'utf-8')
        finally:
            sys.stdout = original

    def test_stream_without_reconfigure_is_ignored(self):
        class Bare:
            pass

        original = sys.stdout
        try:
            sys.stdout = Bare()
            configure_stdio()
        finally:
            sys.stdout = original


class CliEncodingTests(unittest.TestCase):
    def test_report_survives_a_code_page_that_cannot_encode_task_text(self):
        repo = Path(__file__).resolve().parents[1]
        refs = subprocess.run(
            ['git', '-C', str(repo), 'for-each-ref', '--format=%(refname:short)',
             'refs/remotes/origin/pol/'],
            capture_output=True, text=True)
        if refs.returncode != 0 or not refs.stdout.strip():
            self.skipTest('no fetched origin/pol/* refs to report on')
        env = dict(os.environ, PYTHONIOENCODING='gbk')
        result = subprocess.run([sys.executable, str(repo / 'tools' / 'board.py')],
                                capture_output=True, env=env, cwd=repo)
        self.assertEqual(result.returncode, 0,
                         result.stderr.decode('utf-8', 'replace'))
        report = json.loads(result.stdout.decode('utf-8'))
        self.assertIn('tasks', report)
        self.assertTrue(report['tasks'])


if __name__ == '__main__':
    unittest.main()
