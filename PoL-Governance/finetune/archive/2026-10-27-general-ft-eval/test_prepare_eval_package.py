"""最终评测包打包器的单元测试（纯标准库、纯 CPU、只读公开 fixture）。

测试全部在临时目录里自建最小仓库结构（finetune/ + datasets/ + versions.json + README.md），
不联网、不读真实数据、不访问 results/MODEL-02-final-eval/ 真实目录。
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, Optional

from finetune import prepare_eval_package

GIT_COMMIT = "a" * 40

# 规格 §4 的白名单（顺序与规格一致）；单独写死，防止实现里悄悄增删文件。
WHITELIST_SPEC = (
    "finetune/__init__.py",
    "finetune/decision_common.py",
    "finetune/eval_decision.py",
    "finetune/calibrate.py",
    "finetune/collect_results.py",
    "finetune/final_eval_aggregate.py",
    "finetune/check_aggregate_export.py",
    "finetune/bench_latency.py",
    "datasets/__init__.py",
    "datasets/general/__init__.py",
    "datasets/general/build_training_view.py",
)


def write_bytes(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def build_fixture(root: Path, readme: bool = True, versions: Optional[Dict[str, object]] = None) -> None:
    """在 root 里造一个最小仓库：白名单脚本 + versions.json + README.md + 白名单外文件。"""
    for index, rel_path in enumerate(sorted(WHITELIST_SPEC)):
        write_bytes(root / rel_path, f"# fixture copy of {rel_path}\nVALUE = {index}\n")
    payload = versions if versions is not None else {
        "schema": "fixture-versions",
        "base": "fixture/base-1.7b",
        "adapter": "fixture/adapter-m10",
        "records": 3,
    }
    write_bytes(root / "versions.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    if readme:
        write_bytes(root / "README.md", "# fixture eval package readme\n\n人工撰写的说明。\n")
    # 白名单外的文件：package 里绝不能出现。
    write_bytes(root / "finetune" / "notes.txt", "outside whitelist\n")
    write_bytes(root / "finetune" / "eval_decision.py.bak", "# backup\n")


class PackageTestBase(unittest.TestCase):
    """每个测试一个临时仓库 + 一个 package 输出目录（与真实布局一致，位于仓库内）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.out = self.repo / "results" / "MODEL-02-final-eval" / "eval-package"
        self.versions = self.repo / "versions.json"
        build_fixture(self.repo)

    # -- helpers ---------------------------------------------------------

    def cli(self, *extra: str, out: Optional[Path] = None,
            versions: Optional[Path] = None) -> "tuple[int, str, str]":
        argv = [
            "--versions", str(versions if versions is not None else self.versions),
            "--repo-root", str(self.repo),
            "--out", str(out if out is not None else self.out),
            *extra,
        ]
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = prepare_eval_package.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def generate(self, force: bool = False) -> "tuple[int, str, str]":
        extra = ["--git-commit", GIT_COMMIT]
        if force:
            extra.append("--force")
        return self.cli(*extra)

    def check(self) -> "tuple[int, str, str]":
        return self.cli("--check", "--git-commit", GIT_COMMIT)

    def snapshot(self) -> Dict[str, bytes]:
        return {rel_path: (self.out / rel_path).read_bytes()
                for rel_path in prepare_eval_package.iter_package_files(self.out)}

    def read_manifest(self) -> Dict[str, object]:
        return json.loads((self.out / "MANIFEST.json").read_text(encoding="utf-8"))


class WhitelistTest(unittest.TestCase):
    def test_whitelist_matches_spec(self) -> None:
        self.assertEqual(tuple(prepare_eval_package.WHITELIST), WHITELIST_SPEC)
        self.assertEqual(set(prepare_eval_package.WHITELIST), set(WHITELIST_SPEC))


class GenerateTest(PackageTestBase):
    def test_generate_writes_manifest_and_checksums(self) -> None:
        code, stdout, stderr = self.generate()
        self.assertEqual(code, 0, stderr)
        summary = json.loads(stdout)
        self.assertEqual(summary["status"], "written")
        self.assertEqual(summary["files"], len(WHITELIST_SPEC) + 1)

        self.assertTrue((self.out / "MANIFEST.json").is_file())
        self.assertTrue((self.out / "CHECKSUMS.sha256").is_file())
        manifest = self.read_manifest()
        self.assertEqual(manifest["schema"], "pol-final-eval-package-v1")
        self.assertEqual(manifest["git_commit"], GIT_COMMIT)
        self.assertEqual(manifest["versions"],
                         json.loads(self.versions.read_text(encoding="utf-8")))

        paths = [entry["path"] for entry in manifest["files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(set(paths), set(WHITELIST_SPEC) | {"README.md"})
        self.assertNotIn("MANIFEST.json", paths)
        self.assertNotIn("CHECKSUMS.sha256", paths)
        for entry in manifest["files"]:
            data = (self.out / entry["path"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(entry["bytes"], len(data))

        # package_sha256 = 去掉该字段后的规范 JSON 的 sha256
        payload = {key: value for key, value in manifest.items() if key != "package_sha256"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode("utf-8")
        self.assertEqual(manifest["package_sha256"], hashlib.sha256(canonical).hexdigest())

        # CHECKSUMS 覆盖除自身外全部文件（含 README/MANIFEST），按 path 排序，两个空格
        lines = (self.out / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
        recorded = {}
        for line in lines:
            digest, rel_path = line.split("  ", 1)
            recorded[rel_path] = digest
        self.assertEqual(set(recorded),
                         set(WHITELIST_SPEC) | {"README.md", "MANIFEST.json"})
        self.assertEqual([line.split("  ", 1)[1] for line in lines],
                         sorted(recorded))
        for rel_path, digest in recorded.items():
            data = (self.out / rel_path).read_bytes()
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_generate_is_idempotent(self) -> None:
        first = self.generate()
        self.assertEqual(first[0], 0, first[2])
        before = self.snapshot()
        second = self.generate()
        self.assertEqual(second[0], 0, second[2])
        self.assertEqual(json.loads(second[1])["status"], "unchanged")
        self.assertEqual(before, self.snapshot())

    def test_only_whitelist_files_are_copied(self) -> None:
        code, _, stderr = self.generate()
        self.assertEqual(code, 0, stderr)
        for rel_path in set(WHITELIST_SPEC) | {"README.md"}:
            self.assertTrue((self.out / rel_path).is_file(), rel_path)
        self.assertFalse((self.out / "finetune" / "notes.txt").exists())
        self.assertFalse((self.out / "finetune" / "eval_decision.py.bak").exists())
        self.assertFalse((self.out / "versions.json").exists())
        # 复制的字节与源文件逐字节相同（不做换行转换）
        source = (self.repo / "finetune" / "calibrate.py").read_bytes()
        self.assertEqual((self.out / "finetune" / "calibrate.py").read_bytes(), source)

    def test_output_is_lf_utf8_without_timestamps(self) -> None:
        code, _, stderr = self.generate()
        self.assertEqual(code, 0, stderr)
        for name in ("MANIFEST.json", "CHECKSUMS.sha256"):
            data = (self.out / name).read_bytes()
            self.assertNotIn(b"\r", data)
            self.assertTrue(data.endswith(b"\n"))
            data.decode("utf-8")
        manifest_text = (self.out / "MANIFEST.json").read_text(encoding="utf-8").lower()
        self.assertNotIn("timestamp", manifest_text)
        self.assertNotIn("generated_at", manifest_text)

    def test_generate_requires_force_to_overwrite(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        target = self.out / "finetune" / "calibrate.py"
        before = target.read_bytes()
        write_bytes(self.repo / "finetune" / "calibrate.py", "# 改过的源文件\n")

        code, _, stderr = self.generate()
        self.assertEqual(code, 2)
        self.assertIn("--force", stderr)
        self.assertIn("finetune/calibrate.py", stderr)
        self.assertEqual(target.read_bytes(), before)

        code, _, stderr = self.generate(force=True)
        self.assertEqual(code, 0, stderr)
        self.assertNotEqual(target.read_bytes(), before)
        self.assertEqual(self.check()[0], 0)

    def test_generate_refuses_outside_file_in_package(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        write_bytes(self.out / "extra.txt", "extra\n")
        code, _, stderr = self.generate(force=True)
        self.assertEqual(code, 2)
        self.assertIn("extra.txt", stderr)
        self.assertIn("白名单外", stderr)

    def test_generate_does_not_accept_repo_root_as_out(self) -> None:
        code, _, stderr = self.cli("--git-commit", GIT_COMMIT, out=self.repo)
        self.assertEqual(code, 2)
        self.assertIn("--out", stderr)
        self.assertFalse((self.repo / "MANIFEST.json").exists())


class MissingInputTest(PackageTestBase):
    def test_missing_whitelist_source_reports_error(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        (self.repo / "finetune" / "bench_latency.py").unlink()

        code, _, stderr = self.generate(force=True)
        self.assertEqual(code, 2)
        self.assertIn("缺少白名单源文件", stderr)
        self.assertIn("bench_latency.py", stderr)

        code, _, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("bench_latency.py", stderr)

    def test_missing_readme_reports_error(self) -> None:
        (self.repo / "README.md").unlink()
        code, _, stderr = self.generate()
        self.assertEqual(code, 2)
        self.assertIn("README.md", stderr)
        self.assertIn("人工撰写", stderr)
        self.assertFalse((self.out / "MANIFEST.json").exists())

    def test_package_readme_is_used_when_repo_readme_missing(self) -> None:
        (self.repo / "README.md").unlink()
        self.out.mkdir(parents=True)
        write_bytes(self.out / "README.md", "# 人工撰写的 package 说明\n")
        code, _, stderr = self.generate()
        self.assertEqual(code, 0, stderr)
        self.assertEqual((self.out / "README.md").read_bytes(),
                         "# 人工撰写的 package 说明\n".encode("utf-8"))
        self.assertEqual(self.check()[0], 0)

    def test_check_requires_existing_package_dir(self) -> None:
        code, _, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("不存在", stderr)


class CheckTest(PackageTestBase):
    def test_check_passes_after_generate(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        code, stdout, stderr = self.check()
        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["files"], len(WHITELIST_SPEC) + 1)

    def test_check_does_not_write_files(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        before = self.snapshot()
        self.assertEqual(self.check()[0], 0)
        self.assertEqual(before, self.snapshot())

    def test_check_detects_source_change(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        write_bytes(self.repo / "finetune" / "calibrate.py", "# 漂移的源文件\n")
        code, stdout, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("VIOLATION", stderr)
        self.assertIn("finetune/calibrate.py", stderr)
        self.assertEqual(json.loads(stdout)["status"], "fail")

    def test_check_detects_tampered_package_file(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        target = self.out / "finetune" / "calibrate.py"
        target.write_bytes(target.read_bytes() + b"# tampered\n")
        code, _, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("finetune/calibrate.py", stderr)
        self.assertTrue(("篡改" in stderr) or ("漂移" in stderr) or ("不一致" in stderr))

    def test_check_detects_unexpected_package_file(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        write_bytes(self.out / "extra.txt", "extra\n")
        code, _, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("extra.txt", stderr)
        self.assertIn("白名单外", stderr)

    def test_check_detects_missing_manifest(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        (self.out / "MANIFEST.json").unlink()
        code, _, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("MANIFEST.json", stderr)

    def test_check_detects_missing_checksums(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        (self.out / "CHECKSUMS.sha256").unlink()
        code, _, stderr = self.check()
        self.assertEqual(code, 2)
        self.assertIn("CHECKSUMS.sha256", stderr)

    def test_check_detects_git_commit_drift(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        self.assertEqual(self.read_manifest()["git_commit"], GIT_COMMIT)
        code, _, stderr = self.cli("--check", "--git-commit", "b" * 40)
        self.assertEqual(code, 2)
        self.assertIn("git_commit", stderr)


class ReadmeTest(PackageTestBase):
    def test_authored_package_readme_is_preserved(self) -> None:
        self.assertEqual(self.generate()[0], 0)
        authored = "# 人工撰写的评测包说明\n\n不要被生成器覆盖。\n"
        write_bytes(self.out / "README.md", authored)

        # README 变了但 MANIFEST/CHECKSUMS 还是旧的 → 需要 --force 重算
        self.assertEqual(self.generate()[0], 2)
        code, _, stderr = self.generate(force=True)
        self.assertEqual(code, 0, stderr)
        self.assertEqual((self.out / "README.md").read_bytes(), authored.encode("utf-8"))

        manifest = self.read_manifest()
        readme_entries = [entry for entry in manifest["files"] if entry["path"] == "README.md"]
        self.assertEqual(len(readme_entries), 1)
        self.assertEqual(readme_entries[0]["sha256"],
                         hashlib.sha256(authored.encode("utf-8")).hexdigest())
        self.assertEqual(self.check()[0], 0)


class VersionsTest(PackageTestBase):
    def test_versions_are_embedded_verbatim(self) -> None:
        payload = {"schema": "fixture-versions", "model": "中文名", "records": 7,
                   "notes": ["a", "b"]}
        build_fixture(self.repo, versions=payload)
        code, _, stderr = self.generate()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.read_manifest()["versions"], payload)

    def test_versions_relative_path_falls_back_to_repo_root(self) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as other:
            os.chdir(other)
            try:
                code, _, stderr = self.cli("--git-commit", GIT_COMMIT,
                                           versions=Path("versions.json"))
            finally:
                os.chdir(previous)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.read_manifest()["versions"],
                         json.loads(self.versions.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
