"""verify_hf_remote.py 的纯 CPU 单元测试（不联网）。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from datasets.general import verify_hf_remote as verify


def write_manifest(path: Path, files) -> None:
    path.write_text(json.dumps({"files": files}, ensure_ascii=False), encoding="utf-8")


class VerifyHfRemoteTest(unittest.TestCase):
    def test_load_manifest_public_and_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            write_manifest(path, [
                {"path": "README.md", "bytes": 10, "sha256": "a" * 64},
                {"path": "train.jsonl.gz", "bytes": 100, "sha256": "b" * 64},
            ])
            files = verify.load_manifest(path)
            self.assertEqual([item["path"] for item in files], ["README.md", "train.jsonl.gz"])
            self.assertEqual(files[1]["bytes"], 100)

    def test_load_manifest_rejects_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            path.write_text(json.dumps({"files": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify.load_manifest(path)

    def test_parse_next_link(self):
        header = '<https://huggingface.co/api/datasets/x/tree/main?recursive=true&cursor=abc>; rel="next"'
        self.assertIn("cursor=abc", verify.parse_next_link(header) or "")
        self.assertIsNone(verify.parse_next_link(None))
        self.assertIsNone(verify.parse_next_link('<https://x>; rel="prev"'))

    def test_compare_lfs_match_and_mismatch(self):
        manifest = [
            {"path": "train.jsonl.gz", "bytes": 100, "sha256": "a" * 64},
            {"path": "test.jsonl.gz", "bytes": 50, "sha256": "b" * 64},
        ]
        tree = [
            {"type": "file", "path": "train.jsonl.gz", "size": 100, "lfs": {"oid": "a" * 64}},
            {"type": "file", "path": "test.jsonl.gz", "size": 50, "lfs": {"oid": "c" * 64}},
        ]
        results, counts = verify.compare(manifest, tree)
        by_path = {item["path"]: item for item in results}
        self.assertEqual(by_path["train.jsonl.gz"]["status"], verify.STATUS_MATCH)
        self.assertEqual(by_path["test.jsonl.gz"]["status"], verify.STATUS_SHA_MISMATCH)
        self.assertEqual(counts[verify.STATUS_MATCH], 1)
        self.assertEqual(counts[verify.STATUS_SHA_MISMATCH], 1)

    def test_compare_size_mismatch_and_missing(self):
        manifest = [
            {"path": "train.jsonl.gz", "bytes": 100, "sha256": "a" * 64},
            {"path": "validation.jsonl.gz", "bytes": 20, "sha256": "d" * 64},
        ]
        tree = [
            {"type": "file", "path": "train.jsonl.gz", "size": 99, "lfs": {"oid": "a" * 64}},
        ]
        results, counts = verify.compare(manifest, tree)
        by_path = {item["path"]: item for item in results}
        self.assertEqual(by_path["train.jsonl.gz"]["status"], verify.STATUS_SIZE_MISMATCH)
        self.assertEqual(by_path["validation.jsonl.gz"]["status"], verify.STATUS_MISSING)
        self.assertEqual(counts[verify.STATUS_SIZE_MISMATCH], 1)
        self.assertEqual(counts[verify.STATUS_MISSING], 1)

    def test_compare_downloads_small_plain_file(self):
        import hashlib
        payload = b"hello dataset card"
        manifest = [{"path": "README.md", "bytes": len(payload),
                     "sha256": hashlib.sha256(payload).hexdigest()}]
        tree = [{"type": "file", "path": "README.md", "size": len(payload)}]
        results, counts = verify.compare(manifest, tree, raw_fetcher=lambda path: payload)
        self.assertEqual(results[0]["status"], verify.STATUS_MATCH)
        self.assertEqual(results[0]["via"], "download")
        bad = [{"type": "file", "path": "README.md", "size": len(payload)}]
        results, counts = verify.compare(manifest, bad, raw_fetcher=lambda path: b"tampered")
        self.assertEqual(results[0]["status"], verify.STATUS_SIZE_MISMATCH)

    def test_compare_skips_large_non_lfs(self):
        manifest = [{"path": "big.bin", "bytes": 20, "sha256": "e" * 64}]
        tree = [{"type": "file", "path": "big.bin", "size": 20}]
        results, counts = verify.compare(manifest, tree, raw_fetcher=lambda path: b"x" * 20,
                                         max_download_bytes=10)
        self.assertEqual(results[0]["status"], verify.STATUS_SKIPPED)
        self.assertEqual(counts[verify.STATUS_SKIPPED], 1)

    def test_extra_remote_files_counted(self):
        manifest = [{"path": "a.txt", "bytes": 1, "sha256": "a" * 64}]
        tree = [
            {"type": "file", "path": "a.txt", "size": 1, "lfs": {"oid": "a" * 64}},
            {"type": "file", "path": "extra.txt", "size": 2},
            {"type": "directory", "path": "subdir"},
        ]
        _, counts = verify.compare(manifest, tree)
        self.assertEqual(counts[verify.STATUS_EXTRA], 1)

    def test_summarize_status(self):
        pass_counts = {verify.STATUS_MATCH: 3, verify.STATUS_SIZE_ONLY: 1}
        summary = verify.summarize(pass_counts)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["unverified"], 1)
        fail_counts = {verify.STATUS_MATCH: 2, verify.STATUS_SHA_MISMATCH: 1}
        self.assertEqual(verify.summarize(fail_counts)["status"], "fail")

    def test_token_file_inside_repo_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            token = root / "token.txt"
            token.write_text("hf_secret", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify.load_token(token, root)


if __name__ == "__main__":
    unittest.main()
