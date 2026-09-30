"""通用回放池：英译中改写 + 重判流水线的离线测试（不联网、不花钱）。

    uv run --no-project --offline python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "rewrite"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import rewrite  # noqa: E402


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


class RewriteFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = FIXTURES / "en-source.jsonl"
        self.candidates = FIXTURES / "candidates.json"
        self.out = self.root / "run"
        self.rows = read_jsonl(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def write_source(self, rows, name="source.jsonl"):
        path = self.root / name
        path.write_text(jsonl(rows), encoding="utf-8")
        return path

    # ---------- prepare ----------
    def test_prepare_writes_plan_without_targets(self):
        code = rewrite.main(["prepare", "--source", str(self.source), "--candidates",
                             str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 0)
        plan = read_jsonl(self.out / "rewrite-plan.jsonl")
        self.assertEqual(len(plan), 3)
        manifest = json.loads((self.out / "plan.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["target_visible_to_teachers"])
        for row in plan:
            prompt = rewrite.render_rewrite_prompt(row)
            self.assertNotIn("target", json.dumps(row["en"], ensure_ascii=False))
            for label in ("Book the requested fare", "Not fully supported", "High risk"):
                self.assertNotIn(label, prompt.split("【选项】")[0])  # 选项之外不得出现答案线索
            self.assertRegex(row["source"]["revision"], r"^[0-9a-f]{40}$")
            self.assertEqual(row["source"]["split"], "train")
            self.assertEqual(row["source"]["license"], "cc0-1.0")

    def test_prepare_rejects_non_train_split(self):
        rows = [dict(self.rows[0], split="test")]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_non_commercial_license(self):
        rows = [dict(self.rows[0], license="cc-by-nc-4.0")]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_benchmark_candidate(self):
        rows = [dict(self.rows[0], dataset="fixture/bench-like")]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_observe_candidate(self):
        rows = [dict(self.rows[0], dataset="fixture/unclear-license")]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_unknown_dataset(self):
        rows = [dict(self.rows[0], dataset="stranger/data")]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_revision_mismatch(self):
        rows = [dict(self.rows[0], revision="f" * 40)]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_missing_line_number(self):
        row = dict(self.rows[0])
        row.pop("line_number")
        code = rewrite.main(["prepare", "--source", str(self.write_source([row])),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_prepare_rejects_chinese_source(self):
        rows = [dict(self.rows[0], source_language="zh")]
        code = rewrite.main(["prepare", "--source", str(self.write_source(rows)),
                             "--candidates", str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 1)

    # ---------- run ----------
    def prepare(self):
        code = rewrite.main(["prepare", "--source", str(self.source), "--candidates",
                             str(self.candidates), "--out", str(self.out)])
        self.assertEqual(code, 0)

    def test_fixture_run_and_verify(self):
        self.prepare()
        code = rewrite.main(["run", "--out", str(self.out), "--fixture"])
        self.assertEqual(code, 0)
        records = read_jsonl(self.out / "zh.records.jsonl")
        self.assertEqual(len(records), 3)
        for record in records:
            self.assertTrue(record["fixture"])
            self.assertFalse(record["usable_for_training"])
            self.assertEqual(record["label_source"], "judge")
            self.assertIn("fixture 伪改写", record["zh"]["state"])
            self.assertTrue(record["judge"]["answered_without_original_target"])
        code = rewrite.main(["verify", "--records", str(self.out / "zh.records.jsonl")])
        self.assertEqual(code, 0)

    def test_verify_reports_agreement_with_english_label_without_copying_it(self):
        """重判与英文标签一致是统计量，不是照搬：一致计数不产生问题。"""
        self.prepare()
        rewrite.main(["run", "--out", str(self.out), "--fixture"])
        records = read_jsonl(self.out / "zh.records.jsonl")
        problems, stats = rewrite.verify_records(records)
        self.assertEqual(problems, [])
        self.assertEqual(stats["records"], 3)
        self.assertGreaterEqual(stats["agree_with_english_target"], 0)

    def test_live_requires_lead_approval(self):
        self.prepare()
        code = rewrite.main(["run", "--out", str(self.out), "--endpoint", "https://example.invalid/v1",
                             "--rewrite-model", "m1", "--judge-model", "m2"])
        self.assertEqual(code, 2)
        self.assertFalse((self.out / "zh.records.jsonl").exists())

    def test_live_requires_distinct_lineages(self):
        self.prepare()
        code = rewrite.main(["run", "--out", str(self.out), "--endpoint", "https://example.invalid/v1",
                             "--rewrite-model", "m1", "--judge-model", "m2",
                             "--rewrite-lineage", "same", "--judge-lineage", "same",
                             "--approved-by-lead"])
        self.assertEqual(code, 2)

    def test_run_without_prepare_refuses(self):
        self.assertEqual(rewrite.main(["run", "--out", str(self.out), "--fixture"]), 2)


class RewriteVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "run"
        rewrite.main(["prepare", "--source", str(FIXTURES / "en-source.jsonl"), "--candidates",
                      str(FIXTURES / "candidates.json"), "--out", str(self.out)])
        rewrite.main(["run", "--out", str(self.out), "--fixture"])
        self.records = read_jsonl(self.out / "zh.records.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self, records):
        path = self.root / "records.jsonl"
        path.write_text(jsonl(records), encoding="utf-8")
        return rewrite.main(["verify", "--records", str(path)])

    def test_rejects_english_label_as_truth(self):
        records = [dict(record) for record in self.records]
        records[0] = dict(records[0], label_source="original")
        self.assertEqual(self.verify(records), 1)

    def test_rejects_same_model_for_rewrite_and_judge(self):
        records = [dict(record) for record in self.records]
        records[0] = dict(records[0], judge=dict(records[0]["judge"],
                                                 model=records[0]["rewrite"]["model"]))
        self.assertEqual(self.verify(records), 1)

    def test_rejects_same_lineage(self):
        records = [dict(record) for record in self.records]
        records[0] = dict(records[0], judge=dict(records[0]["judge"],
                                                 lineage=records[0]["rewrite"]["lineage"]))
        self.assertEqual(self.verify(records), 1)

    def test_rejects_untranslated_state(self):
        records = [dict(record) for record in self.records]
        zh = dict(records[0]["zh"], state=records[0]["original"]["state"])
        key = rewrite.dedup_key(zh["state"], zh["question"], zh["options"])
        records[0] = dict(records[0], zh=zh, dedup_key=key)
        self.assertEqual(self.verify(records), 1)

    def test_rejects_stale_dedup_key(self):
        records = [dict(record) for record in self.records]
        records[0] = dict(records[0], dedup_key="0" * 64)
        self.assertEqual(self.verify(records), 1)

    def test_rejects_duplicate_chinese_content(self):
        records = [dict(record) for record in self.records]
        records[2] = dict(records[2], zh=dict(records[0]["zh"]), dedup_key=records[0]["dedup_key"])
        self.assertEqual(self.verify(records), 1)

    def test_rejects_non_train_provenance(self):
        records = [dict(record) for record in self.records]
        source = dict(records[0]["source"], split="validation")
        records[0] = dict(records[0], source=source)
        self.assertEqual(self.verify(records), 1)

    def test_rejects_missing_provenance_field(self):
        records = [dict(record) for record in self.records]
        source = dict(records[0]["source"])
        source.pop("line_number")
        records[0] = dict(records[0], source=source)
        self.assertEqual(self.verify(records), 1)

    def test_rejects_disallowed_license(self):
        records = [dict(record) for record in self.records]
        source = dict(records[0]["source"], license="cc-by-nc-4.0")
        records[0] = dict(records[0], source=source)
        self.assertEqual(self.verify(records), 1)

    def test_rejects_judge_that_saw_english_label(self):
        records = [dict(record) for record in self.records]
        judge = dict(records[0]["judge"], answered_without_original_target=False)
        records[0] = dict(records[0], judge=judge)
        self.assertEqual(self.verify(records), 1)

    def test_fixture_records_must_not_be_trainable(self):
        records = [dict(record) for record in self.records]
        records[0] = dict(records[0], usable_for_training=True)
        self.assertEqual(self.verify(records), 1)


class NormalizationTests(unittest.TestCase):
    def test_option_keys_are_preserved(self):
        pairs = rewrite.normalize_options([{"key": "handoff", "label": " 给人工 "}, "其它"])
        self.assertEqual(pairs, [("handoff", "给人工"), ("B", "其它")])

    def test_dedup_key_is_stable_under_whitespace_and_width(self):
        first = rewrite.dedup_key("Ａ  B", "问  题", ["选项一", "选项二"])
        second = rewrite.dedup_key("A B", "问 题", ["选项一", "选项二"])
        self.assertEqual(first, second)

    def test_dedup_key_changes_with_options(self):
        first = rewrite.dedup_key("state", "question", ["a", "b"])
        second = rewrite.dedup_key("state", "question", ["a", "c"])
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
