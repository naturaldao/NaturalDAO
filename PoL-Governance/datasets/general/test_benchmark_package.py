"""内部 benchmark 包的守卫测试：跑包内 verify.py，并验证"篡改必须被发现"。

benchmark 包被 .gitignore 排除（不进公开仓库），所以在没有产物的检出里整个测试类自动跳过。
测试本身不含任何 benchmark 样本内容：只调用脚本、看退出码，并用数据里的字符串做"未泄漏"断言。
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / "data" / "splits" / "benchmark-dataset"
VERIFY = PACKAGE / "verify.py"


def run_verify(package: Path):
    return subprocess.run([sys.executable, str(package / "verify.py")],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


@unittest.skipUnless(VERIFY.is_file(), "benchmark 包不在本检出（已 gitignore，属正常）")
class BenchmarkPackageTest(unittest.TestCase):
    def test_package_passes_integrity_check(self):
        completed = run_verify(PACKAGE)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("全部通过", completed.stdout)

    def test_package_files_are_not_git_tracked(self):
        repo = subprocess.run(["git", "-C", str(PACKAGE), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if repo.returncode != 0:
            self.skipTest("不在 git 仓库内")
        root = Path(repo.stdout.strip())
        relative = PACKAGE.resolve().relative_to(root).as_posix()
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--", relative + "/"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(tracked.stdout.strip(), "", "benchmark 包不得被 git 跟踪")
        ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-v", "--",
                                  f"{relative}/benchmark.jsonl"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertIn("benchmark", ignored.stdout)

    def test_tampered_data_is_detected(self):
        with tempfile.TemporaryDirectory() as workspace:
            copy = Path(workspace) / "package"
            shutil.copytree(PACKAGE, copy)
            data = copy / "benchmark.jsonl"
            text = data.read_text(encoding="utf-8")
            first, rest = text.split("\n", 1)
            data.write_text(first + " \n" + rest, encoding="utf-8", newline="\n")  # 只多一个空格
            completed = run_verify(copy)
            self.assertEqual(completed.returncode, 1, completed.stdout)
            self.assertIn("sha256 不一致", completed.stdout)

    def test_docs_contain_no_sample_content(self):
        rows = [json.loads(line) for line in
                (PACKAGE / "benchmark.jsonl").read_text(encoding="utf-8").split("\n") if line.strip()]
        needle = str(rows[0]["state"])[:40]
        self.assertTrue(needle)
        for name in ("README.md", "USAGE.md", "manifest.json"):
            text = (PACKAGE / name).read_text(encoding="utf-8")
            self.assertNotIn(needle, text, f"{name} 泄漏了 benchmark 样本内容")


if __name__ == "__main__":
    unittest.main()
