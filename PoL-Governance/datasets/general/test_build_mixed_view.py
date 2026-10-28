"""build_mixed_view.py 的纯 CPU 单元测试（标准库）。"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from datasets.general import build_mixed_view as mixer


def make_row(index: int, *, group: str = "base", src: str = "general-v5") -> dict:
    return {
        "rid": f"{group}-{index:05d}#q",
        "src": src,
        "kind": "choice",
        "lang": "en",
        "route": "classification",
        "prompt": f"prompt {index}",
        "options": ["A", "B"],
        "option_labels": ["A", "B"],
        "answer_idx": 0,
        "soft": None,
    }


def write_rows(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class MixedViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.base = self.dir / "base.jsonl"
        self.extra = self.dir / "extra.jsonl"
        self.out = self.dir / "mixed" / "view.jsonl"
        self.out.parent.mkdir(parents=True, exist_ok=True)

    def run_cli(self, *args):
        return mixer.main(list(map(str, args)))

    def test_extra_count_for(self):
        self.assertEqual(mixer.extra_count_for(900, 0.1), 100)
        self.assertEqual(mixer.extra_count_for(800, 0.2), 200)
        self.assertEqual(mixer.extra_count_for(10, 0.5), 10)
        with self.assertRaises(mixer.MixError):
            mixer.extra_count_for(100, 0.0)
        with self.assertRaises(mixer.MixError):
            mixer.extra_count_for(100, 1.0)
        with self.assertRaises(mixer.MixError):
            mixer.extra_count_for(0, 0.1)

    def test_interleave_positions(self):
        positions = mixer.interleave_positions(9, 1)
        self.assertEqual(len(positions), 10)
        self.assertEqual(sum(positions), 1)
        self.assertEqual(positions, mixer.interleave_positions(9, 1))
        positions = mixer.interleave_positions(80, 20)
        self.assertEqual(len(positions), 100)
        self.assertEqual(sum(positions), 20)
        # 前几个位置不应全是 extra
        self.assertFalse(all(positions[:5]))

    def test_mix_rows_counts_groups(self):
        base_rows = [make_row(i) for i in range(100)]
        extra_rows = [make_row(i, group="extra", src="pol2-freeze-8705-v1") for i in range(10)]
        mixed, stats = mixer.mix_rows(base_rows, extra_rows, 0.1)
        # 100 * 0.1 / 0.9 = 11.11 -> round 11
        self.assertEqual(len(mixed), 111)
        self.assertEqual(stats["extra_rows_used"], 11)
        self.assertAlmostEqual(stats["ratio_realized"], 11 / 111, places=4)
        self.assertEqual(sum(1 for row in mixed if row["mix_group"] == "extra"), 11)
        self.assertEqual(sum(1 for row in mixed if row["mix_group"] == "base"), 100)

    def test_extra_rows_cycle_when_short(self):
        base_rows = [make_row(i) for i in range(100)]
        extra_rows = [make_row(i, group="extra") for i in range(3)]
        mixed, stats = mixer.mix_rows(base_rows, extra_rows, 0.1)
        self.assertEqual(stats["extra_rows_used"], 11)
        self.assertTrue(stats["base_cycled"])
        extra_rids = [row["rid"] for row in mixed if row["mix_group"] == "extra"]
        self.assertEqual(len(extra_rids), 11)
        self.assertEqual(set(extra_rids), {row["rid"] for row in extra_rows})

    def test_cli_deterministic_and_manifest(self):
        write_rows(self.base, [make_row(i) for i in range(50)])
        write_rows(self.extra, [make_row(i, group="extra") for i in range(5)])
        out1 = self.dir / "mixed1.jsonl"
        out2 = self.dir / "mixed2.jsonl"
        for out in (out1, out2):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = self.run_cli("--base", self.base, "--extra", self.extra,
                                    "--ratio", "0.1", "--out", out, "--json")
            self.assertEqual(code, 0)
        self.assertEqual(out1.read_bytes(), out2.read_bytes())
        manifest = json.loads(Path(str(out1) + ".manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["template_version"], "mix-1")
        self.assertEqual(manifest["base_rows"], 50)
        self.assertEqual(manifest["extra_rows_used"], 6)
        self.assertEqual(manifest["total_rows"], 56)
        self.assertEqual(manifest["output_sha256"], mixer.sha256_file(out1))
        self.assertEqual(len(manifest["base_sha256"]), 64)

    def test_cli_pol2_requires_flag(self):
        write_rows(self.base, [make_row(i) for i in range(10)])
        write_rows(self.extra, [make_row(i, group="extra", src="pol2-freeze-8705-v1") for i in range(2)])
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = self.run_cli("--base", self.base, "--extra", self.extra,
                                "--ratio", "0.1", "--out", self.out)
        self.assertEqual(code, 2)
        self.assertIn("--allow-pol2", buffer.getvalue())
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = self.run_cli("--base", self.base, "--extra", self.extra, "--ratio", "0.1",
                                "--allow-pol2", "--out", self.out)
        self.assertEqual(code, 0)

    def test_cli_out_inside_repo_rejected(self):
        write_rows(self.base, [make_row(i) for i in range(10)])
        write_rows(self.extra, [make_row(i, group="extra") for i in range(2)])
        repo_out = mixer.repo_root() / "datasets" / "general" / "should-not-exist.jsonl"
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = self.run_cli("--base", self.base, "--extra", self.extra,
                                "--ratio", "0.1", "--out", repo_out)
        self.assertEqual(code, 2)
        self.assertIn("仓库", buffer.getvalue())
        self.assertFalse(repo_out.exists())

    def test_cli_missing_field_rejected(self):
        write_rows(self.base, [make_row(i) for i in range(10)])
        bad = make_row(0, group="extra")
        bad.pop("prompt")
        write_rows(self.extra, [bad])
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = self.run_cli("--base", self.base, "--extra", self.extra,
                                "--ratio", "0.1", "--out", self.out)
        self.assertEqual(code, 2)
        self.assertIn("prompt", buffer.getvalue())

    def test_cli_overwrite_guard(self):
        write_rows(self.base, [make_row(i) for i in range(10)])
        write_rows(self.extra, [make_row(i, group="extra") for i in range(2)])
        self.out.write_text("existing\n", encoding="utf-8")
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = self.run_cli("--base", self.base, "--extra", self.extra,
                                "--ratio", "0.1", "--out", self.out)
        self.assertEqual(code, 2)
        self.assertIn("--overwrite", buffer.getvalue())
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = self.run_cli("--base", self.base, "--extra", self.extra, "--ratio", "0.1",
                                "--out", self.out, "--overwrite")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
