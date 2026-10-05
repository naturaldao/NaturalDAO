#!/usr/bin/env python3
"""slim.py 的离线测试：字段精简必须无损，能逐字段还原。

覆盖：src/row 溯源、meta 三档提升（全库恒定 / 来源内恒定 / 逐条）、可复原键整批删且留文档、
questions 的 origin/source_key/prompt 省略规则、flags 提升规则、空 quality_flags 省略、
build 自带的自校验，以及 compare 能抓到人为改动。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


slim = load_module("general_slim", HERE / "slim.py")


def question(key, kind="choice", options=None, scale=None, prompt=None):
    spec = {"key": key, "kind": kind, "origin": "source", "source_key": key,
            "prompt": prompt if prompt is not None else key}
    if kind == "score":
        spec["scale"] = scale or {"min": 0, "max": 2, "labels": ["a", "b", "c"]}
    else:
        spec["options"] = options or [{"key": "x", "label": "x"}, {"key": "y", "label": "y"}]
    return spec


def item(idx, slug="jev-distill-v3", row=None, domain="decision_mechanics", flags=None, meta_extra=None):
    payload = {
        "id": f"db-{slug}-{idx:08x}",
        "domain": domain,
        "lang": "en",
        "state": f"scenario {idx}",
        "questions": [question(f"q{idx}")],
        "targets": {f"q{idx}": {"answer": "x", "probs": {"x": 1.0, "y": 0.0}}},
        "source": {"dataset": "Example/data", "revision": "f" * 40, "config": "default",
                   "split": "train", "row": row if row is not None else idx,
                   "license": "apache-2.0", "url": "https://huggingface.co/datasets/Example/data",
                   "slug": slug},
        "meta": {"converter": "convert.py", "converter_version": "0.1",
                 "created_at": "2026-10-05T04:00:00+00:00", "native": True,
                 "question_origin": "source", "key_source": "native-text",
                 "quality_flags": list(flags or [])},
    }
    payload["meta"].update(meta_extra or {})
    return payload


def build(items):
    with tempfile.TemporaryDirectory() as tmp:
        records, manifest, stats = slim.build_slim(items, Path(tmp))
    return records, manifest, stats


class SlimTests(unittest.TestCase):
    def setUp(self):
        self.items = [item(0), item(1), item(2)]

    def test_source_object_becomes_src_index_and_row_is_kept(self):
        records, manifest, _ = build(self.items)
        for record in records:
            self.assertIsInstance(record["src"], int)
            self.assertIn("row", record)
            self.assertNotIn("source", record)
        entry = manifest["sources"][0]
        self.assertEqual(entry["slug"], "jev-distill-v3")
        self.assertEqual(entry["dataset"], "Example/data")
        self.assertEqual(entry["license"], "apache-2.0")
        self.assertEqual(entry["revision"], "f" * 40)
        self.assertEqual(entry["row_range"], [0, 2])
        self.assertEqual(entry["items"], 3)

    def test_global_constants_go_to_defaults(self):
        _records, manifest, _ = build(self.items)
        defaults = manifest["defaults"]
        self.assertEqual(defaults["converter"], "convert.py")
        self.assertEqual(defaults["created_at"], "2026-10-05T04:00:00+00:00")
        self.assertEqual(defaults["lang"], "en")

    def test_per_source_meta_is_hoisted_to_the_source(self):
        # 两个来源的 key_source 不同 → 不能进全局默认，只能按来源提升
        items = [item(0, slug="jev-distill-v3"), item(1, slug="open-jev")]
        items[1]["meta"]["key_source"] = "native-name"
        _records, manifest, _ = build(items)
        entries = {entry["slug"]: entry for entry in manifest["sources"]}
        self.assertEqual(entries["jev-distill-v3"]["meta"]["key_source"], "native-text")
        self.assertEqual(entries["open-jev"]["meta"]["key_source"], "native-name")
        self.assertNotIn("key_source", manifest["defaults"])

    def test_single_source_constant_becomes_global_default(self):
        # 只有一个来源时，"全库恒定"与"来源内恒定"等价 → 提升到 defaults 更省
        _records, manifest, _ = build(self.items)
        self.assertEqual(manifest["defaults"]["key_source"], "native-text")
        self.assertNotIn("meta", manifest["sources"][0])

    def test_recoverable_meta_is_dropped_and_documented(self):
        items = [item(index, meta_extra={"native_id": f"src-{index}", "domain_rule": "family:x"})
                 for index in range(3)]
        records, manifest, _ = build(items)
        for record in records:
            self.assertNotIn("m", record)
        documented = manifest["dropped_meta_keys"]
        self.assertEqual(documented["native_id"]["records"], 3)
        self.assertIn("how_to_recover", documented["native_id"])

    def test_per_record_meta_stays_in_compact_m(self):
        items = [item(index, meta_extra={"weird_key": f"value-{index}"}) for index in range(3)]
        records, _manifest, _ = build(items)
        self.assertEqual(records[0]["m"], {"weird_key": "value-0"})
        self.assertEqual(records[2]["m"], {"weird_key": "value-2"})

    def test_question_origin_and_source_key_are_omitted(self):
        records, _manifest, _ = build(self.items)
        for record in records:
            for spec in record["questions"]:
                self.assertNotIn("origin", spec)
                self.assertNotIn("source_key", spec)
                self.assertNotIn("prompt", spec)      # prompt == key 时省略

    def test_prompt_is_kept_when_it_differs_from_key(self):
        items = [item(0)]
        items[0]["questions"][0]["prompt"] = "Which option is correct?"
        records, _manifest, _ = build(items)
        self.assertEqual(records[0]["questions"][0]["prompt"], "Which option is correct?")

    def test_uniform_flags_are_hoisted(self):
        items = [item(index, flags=["hard_label_to_point_mass"]) for index in range(3)]
        records, manifest, _ = build(items)
        self.assertEqual(manifest["sources"][0]["flags"], ["hard_label_to_point_mass"])
        for record in records:
            self.assertNotIn("flags", record)

    def test_non_uniform_flags_stay_per_record_in_order(self):
        items = [item(0, flags=["a", "b"]), item(1, flags=["b", "a"]), item(2, flags=["a"])]
        records, manifest, _ = build(items)
        self.assertNotIn("flags", manifest["sources"][0])
        self.assertEqual(records[0]["flags"], ["a", "b"])
        self.assertEqual(records[1]["flags"], ["b", "a"])
        self.assertEqual(records[2]["flags"], ["a"])

    def test_empty_quality_flags_are_omitted(self):
        records, _manifest, _ = build([item(0)])
        self.assertNotIn("flags", records[0])

    def test_field_profile_counts_every_record(self):
        profile = slim.field_profile(self.items)
        self.assertEqual(profile["records"], 3)
        self.assertGreater(profile["bytes"], 0)
        fields = {row["field"] for row in profile["top_level"]}
        self.assertTrue({"state", "questions", "targets", "source.dataset"} <= fields)


class RoundTripTests(unittest.TestCase):
    def test_slim_can_be_expanded_back_to_equal_items(self):
        items = [item(index, flags=["hard_label_to_point_mass"] if index == 0 else None,
                      meta_extra={"native_id": f"src-{index}"}) for index in range(4)]
        records, manifest, _ = build(items)
        expanded = list(slim.expand_records(manifest, records))
        result = slim.compare(items, expanded, set(manifest["dropped_meta_keys"]))
        self.assertEqual(result["mismatches"], {}, result["examples"])
        self.assertEqual(result["compared"], 4)

    def test_compare_catches_a_tampered_field(self):
        items = [item(0), item(1)]
        records, manifest, _ = build(items)
        expanded = list(slim.expand_records(manifest, records))
        expanded[1]["state"] = "tampered"
        result = slim.compare(items, expanded, set())
        self.assertEqual(result["mismatches"].get("state"), 1)

    def test_expanded_item_has_the_contract_shape(self):
        records, manifest, _ = build([item(0)])
        expanded = list(slim.expand_records(manifest, records))[0]
        for field in ("id", "domain", "lang", "state", "questions", "targets", "source", "meta"):
            self.assertIn(field, expanded)
        for field in ("dataset", "revision", "config", "split", "row", "license", "url"):
            self.assertIn(field, expanded["source"])
        spec = expanded["questions"][0]
        self.assertEqual(spec["origin"], "source")
        self.assertEqual(spec["source_key"], spec["key"])
        self.assertEqual(spec["prompt"], spec["key"])


class CliTests(unittest.TestCase):
    def test_build_writes_slim_manifest_and_self_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "items.jsonl"
            source.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n"
                                      for entry in [item(0), item(1, slug="open-jev")]),
                              encoding="utf-8")
            out = root / "items.slim.jsonl"
            manifest_path = root / "items.manifest.json"
            report_path = root / "report.json"
            md_path = root / "report.md"
            code = slim.main(["build", "--items", str(source), "--out", str(out),
                              "--manifest", str(manifest_path), "--report", str(report_path),
                              "--report-md", str(md_path), "--raw-root", str(root / "raw")])
            self.assertEqual(code, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["verification"]["mismatches"], {})
            self.assertEqual(report["before"]["records"], 2)
            self.assertLess(report["after"]["bytes"], report["before"]["bytes"])
            self.assertIn("字段精简报告", md_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["sources"]), 2)

    def test_fields_subcommand_reports_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "items.jsonl"
            source.write_text(json.dumps(item(0), ensure_ascii=False) + "\n", encoding="utf-8")
            code = slim.main(["fields", "--items", str(source)])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
