"""JSONL IO：明文与 .gz 双读、缺失回退、错误处理。"""
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from common import read_jsonl, read_jsonl_any, resolve_jsonl


def write_plain(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")


def write_gz(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


class JsonlIoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rows = [{"qid": "pol2-train-000001.status", "kind": "choice"},
                     {"qid": "pol2-train-000001.issue.x", "kind": "noul"}]

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_plain_and_gzip_identically(self):
        plain = self.root / "a.jsonl"
        packed = self.root / "b.jsonl.gz"
        write_plain(plain, self.rows)
        write_gz(packed, self.rows)
        self.assertEqual(read_jsonl(plain), self.rows)
        self.assertEqual(read_jsonl(packed), self.rows)
        self.assertEqual(read_jsonl_any(plain), self.rows)
        self.assertEqual(read_jsonl_any(packed), self.rows)
        self.assertEqual(read_jsonl_any(plain), read_jsonl_any(packed))

    def test_missing_plain_falls_back_to_gz(self):
        packed = self.root / "c.jsonl.gz"
        write_gz(packed, self.rows)
        wanted = self.root / "c.jsonl"
        self.assertFalse(wanted.exists())
        self.assertEqual(read_jsonl_any(wanted), self.rows)
        self.assertEqual(resolve_jsonl(wanted), packed)
        self.assertEqual(resolve_jsonl(packed), packed)

    def test_missing_both_is_an_error(self):
        with self.assertRaises(ValueError):
            read_jsonl_any(self.root / "nope.jsonl")
        with self.assertRaises(ValueError):
            resolve_jsonl(self.root / "nope.jsonl")

    def test_gzip_file_still_enforces_row_rules(self):
        bad = self.root / "bad.jsonl.gz"
        write_gz(bad, self.rows)
        with gzip.open(bad, "at", encoding="utf-8") as stream:
            stream.write("[1, 2, 3]\n")
        with self.assertRaises(ValueError):
            read_jsonl(bad)


if __name__ == "__main__":
    unittest.main()
