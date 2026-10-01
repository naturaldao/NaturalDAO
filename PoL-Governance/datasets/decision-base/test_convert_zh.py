"""convert_zh.py 的离线测试：来源清单校验 + 中文来源转换 + 不硬塞原则。

完全离线：不联网、不读 D:\pol2-raw，测试数据全部内联在本文件里。

    uv run --no-project --offline python -m unittest discover -s datasets/decision-base -p "test_*.py" -q
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import convert as convert_mod          # noqa: E402
import convert_zh                      # noqa: E402
import taxonomy as taxonomy_mod        # noqa: E402

CREATED_AT = "2026-10-02T00:00:00+08:00"
MANIFEST = {
    "dataset": "unit/test-zh", "revision": "a" * 40, "config": "default", "split": "train",
    "license": "apache-2.0", "source_url": "https://huggingface.co/datasets/unit/test-zh",
    "_created_at": CREATED_AT, "_domain_rule": "unit_test", "lang": "zh",
}


def convert_rows(converter, rows, *, slug="unit-zh", mappings="all"):
    """把内联行喂给某个转换器，返回 (unit, items)。走的是 convert.py 同一条组装路径。"""
    taxonomy = convert_zh.load_taxonomy()
    ctx = convert_mod.Context(taxonomy, mappings=mappings, question_lang="zh",
                              created_at=CREATED_AT, log=lambda *_: None)
    manifest = dict(MANIFEST)
    unit = convert_mod.Unit(slug, manifest, [(index, row) for index, row in enumerate(rows)],
                            ctx, limit=None, stratum_cap=1.0)
    unit.rows_read = len(rows)
    convert_zh.CONVERTERS[converter](ctx, unit)
    return unit, unit.emitted


class SourceListTests(unittest.TestCase):
    def setUp(self):
        self.payload = convert_zh.load_sources(convert_zh.DEFAULT_SOURCES)
        self.sources = self.payload["sources"]
        self.excluded = {row["dataset"] for row in self.payload["excluded"]}

    def test_quota_floor_and_domain_coverage(self):
        total = sum(source["row_limit"] for source in self.sources)
        self.assertGreaterEqual(total, 11000)
        domains = {source["domain"] for source in self.sources}
        self.assertGreaterEqual(len(domains), 3, f"域覆盖不足：{domains}")
        self.assertIn("human_judgment", domains)
        self.assertIn("risk_harm", domains)

    def test_every_source_is_chinese_train_only_and_pinned(self):
        self.assertGreaterEqual(len(self.sources), 3)
        slugs = set()
        for source in self.sources:
            self.assertEqual(source["lang"], "zh")
            self.assertIn(source["split"], ("train", "zh"))
            self.assertRegex(source["revision"], r"^[0-9a-f]{40}$")
            self.assertIn(str(source["license"]).lower(), convert_zh.ALLOWED_LICENSES)
            self.assertNotIn(source["slug"], slugs)
            slugs.add(source["slug"])
            self.assertNotIn(source["dataset"], self.excluded)
            self.assertIn(source["converter"], convert_zh.CONVERTERS)

    def test_machine_translated_sources_are_excluded_not_admitted(self):
        """用户硬约束：机器翻译出来的英文数据集不算中文来源。"""
        for dataset in ("ToxicityPrompts/PolyGuardMix", "nvidia/Nemotron-Safety-Guard-Dataset-v3",
                        "DirectLLM/Chinese_Preference_Safe_and_Helpful",
                        "erhwenkuo/hh_rlhf-chinese-zhtw", "lchakkei/OpenOrca-Traditional-Chinese",
                        "brighter-dataset/BRIGHTER-emotion-categories",
                        "zzhdbw/Simplified_Chinese_Multi-Emotion_Dialogue_Dataset"):
            self.assertIn(dataset, self.excluded)
            self.assertNotIn(dataset, {source["dataset"] for source in self.sources})

    def test_benchmark_and_adversarial_corpora_are_excluded(self):
        for dataset in ("thu-coai/Safety-Prompts", "BBBBBBBBBBBQ/TC260-Chinese-Safety-Prompts",
                        "thu-coai/SafetyBench", "SUSTech/ChineseSafe", "Paul/hatecheck-mandarin"):
            self.assertIn(dataset, self.excluded)

    def test_unclear_license_sources_are_excluded(self):
        for dataset in ("clue/clue", "m-a-p/COIG-CQIA", "BAAI/COIG-PC"):
            self.assertIn(dataset, self.excluded)

    def test_share_cap_is_respected_by_row_limits(self):
        total = sum(source["row_limit"] for source in self.sources)
        for source in self.sources:
            self.assertLessEqual(source["row_limit"] / total, 0.4, source["slug"])

    def test_load_sources_rejects_bad_rows(self):
        cases = [
            ("split", "test", "只取 train"),
            ("license", "cc-by-nc-4.0", "不在白名单"),
            ("revision", "deadbeef", "40 位"),
            ("lang", "en", "lang=zh"),
            ("converter", "nope", "未知转换器"),
            ("domain", "not_a_domain", "未知覆盖域"),
        ]
        for field, value, _ in cases:
            with self.subTest(field=field):
                payload = json.loads(json.dumps(self.payload))
                payload["sources"] = [dict(payload["sources"][0], **{field: value})]
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "sources.zh.json"
                    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                    with self.assertRaises(SystemExit):
                        convert_zh.load_sources(path)

    def test_source_cannot_be_admitted_and_excluded_at_once(self):
        payload = json.loads(json.dumps(self.payload))
        payload["sources"] = [dict(payload["sources"][0],
                                   dataset=payload["excluded"][0]["dataset"])]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.zh.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(SystemExit):
                convert_zh.load_sources(path)


class ItemShapeTests(unittest.TestCase):
    def assert_valid(self, items):
        taxonomy = convert_zh.load_taxonomy()
        for item in items:
            self.assertEqual(item["lang"], "zh")
            self.assertTrue(taxonomy_mod.id_is_canonical(item["id"]), item["id"])
            self.assertEqual(taxonomy.item_errors(item), [])
            for field in ("dataset", "revision", "config", "split", "row", "license", "url"):
                self.assertIn(field, item["source"])
            self.assertEqual(item["meta"]["converter"], "convert_zh.py")

    def test_cvalues_maps_refusal_and_keeps_raw(self):
        rows = [{"prompt": "如何操纵他人的思维和行为？", "pos_resp": "我不能提供。",
                 "neg_resp": "可以这样做……", "pos_type": "拒绝为主", "neg_type": "风险回复"},
                {"prompt": "普通问题", "pos_resp": "答案", "neg_resp": "另一个答案",
                 "pos_type": "未知类型", "neg_type": ""}]
        unit, items = convert_rows("cvalues", rows)
        self.assertEqual(len(items), 2)
        self.assert_valid(items)
        first = items[0]
        self.assertEqual(first["domain"], "risk_harm")
        self.assertEqual(first["targets"]["refusal_appropriate"]["answer"], "yes")
        self.assertIn("mapping:documented:refusal_appropriate", first["meta"]["quality_flags"])
        self.assertIn("可以这样做", first["meta"]["source_record"]["neg_resp"])
        second = items[1]
        self.assertNotIn("targets", second)
        self.assertIn("source_target_unmapped:pos_type=未知类型", second["meta"]["quality_flags"])

    def test_zhihu_preference_is_state_only(self):
        rows = [{"question_id": 1, "upvotes_chosen": 1291, "upvotes_rejected": 91,
                 "prompt": "艺术的本质是什么？", "chosen": "好答案", "rejected": "差答案"}]
        unit, items = convert_rows("zhihu_pref", rows)
        self.assertEqual(items[0]["domain"], "social_moral")
        self.assertNotIn("targets", items[0])
        self.assertEqual(items[0]["meta"]["upvotes_chosen"], 1291)
        self.assertEqual(items[0]["meta"]["source_record"]["chosen"], "好答案")
        self.assert_valid(items)

    def test_emotion_mapping_and_unknown_label(self):
        rows = [{"text": "誒誒誒！我甄選上了！", "emotion": "開心語調"},
                {"text": "这是一句话", "emotion": "某种新情绪"}]
        unit, items = convert_rows("emotion_zh", rows)
        self.assertEqual(items[0]["targets"]["emotion_primary"]["answer"], "joy")
        self.assertNotIn("targets", items[1])
        self.assertIn("unmapped_emotion:某种新情绪", items[1]["meta"]["quality_flags"])
        self.assert_valid(items)

    def test_binary_sentiment_labels(self):
        rows = [{"text": "非常满意", "label": 1, "type": "简单句"},
                {"text": "差得要命", "label": 0},
                {"text": "无法判断", "label": ""}]
        unit, items = convert_rows("sentiment_zh", rows)
        self.assertEqual(items[0]["targets"]["sentiment_polarity"]["answer"], "positive")
        self.assertEqual(items[1]["targets"]["sentiment_polarity"]["answer"], "negative")
        self.assertNotIn("targets", items[2])
        self.assertIn("label_polarity:card", items[0]["meta"]["quality_flags"])
        self.assert_valid(items)

    def test_toxicity_is_direct_mapping(self):
        rows = [{"text": "抓虫大战，人人有责", "toxic": 1}, {"text": "今天天气不错", "toxic": 0}]
        unit, items = convert_rows("toxicity_zh", rows)
        self.assertEqual(items[0]["targets"]["toxicity_present"]["answer"], "yes")
        self.assertEqual(items[1]["targets"]["toxicity_present"]["answer"], "no")
        self.assertIn("mapping:direct:toxicity_present", items[0]["meta"]["quality_flags"])
        self.assert_valid(items)

    def test_elder_scam_filters_non_chinese_rows(self):
        rows = [{"text": "嫲嫲你下個禮拜幾方便？", "label": "safe", "language": "cantonese"},
                {"text": "Fake Alipay message", "label": "scam", "language": "english"},
                {"text": "你嘅账户被冻结", "label": "scam", "language": "mandarin"}]
        unit, items = convert_rows("elder_scam", rows)
        self.assertEqual(len(items), 2)
        self.assertEqual(unit.skipped.get("not_chinese_row"), 1)
        self.assertEqual(items[0]["targets"]["contains_harm"]["answer"], "no")
        self.assertEqual(items[1]["targets"]["contains_harm"]["answer"], "yes")
        self.assert_valid(items)

    def test_med_guard_maps_safety_and_action(self):
        rows = [{"text": "我要推翻现在的政权", "safety": "Unsafe", "action": "拦截",
                 "channel": "input", "root_cause": "unsafe", "categories": ["涉政"]},
                {"text": "白带像豆腐渣一样", "safety": "Safe", "action": "放行",
                 "channel": "input", "root_cause": "R1", "categories": ["None"]},
                {"text": "海洛因", "safety": "Controversial", "action": "观察",
                 "channel": "input", "root_cause": "controversial", "categories": ["违禁"]}]
        unit, items = convert_rows("med_guard", rows)
        self.assertEqual(items[0]["targets"]["contains_harm"]["answer"], "yes")
        self.assertEqual(items[0]["targets"]["recommended_action"]["answer"], "block")
        self.assertEqual(items[1]["targets"]["contains_harm"]["answer"], "no")
        self.assertEqual(items[1]["targets"]["recommended_action"]["answer"], "allow")
        self.assertNotIn("contains_harm", items[2]["targets"])
        self.assertEqual(items[2]["targets"]["recommended_action"]["answer"], "review")
        self.assert_valid(items)

    def test_mh_triage_reads_json_output_and_multiturn_fallback(self):
        rows = [{"instruction": "分析", "input": "我觉得活着没意思",
                 "output": {"conversation": None,
                            "response": {"intent": ["suicide_ideation"], "risk": "high",
                                         "strategy": ["escalate"], "uncertainty": "low"}}},
                {"instruction": "分析", "input": "",
                 "output": {"conversation": [{"role": "user", "content": "最近压力很大"},
                                             {"role": "assistant", "content": "我在听"}],
                            "response": {"intent": ["mild_distress"], "risk": "low",
                                         "strategy": ["empathize"], "uncertainty": "medium"}}}]
        unit, items = convert_rows("mh_triage", rows)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["targets"]["escalation_needed"]["answer"], "yes")
        self.assertEqual(items[1]["targets"]["escalation_needed"]["answer"], "no")
        self.assertIn("user: 最近压力很大", items[1]["state"])
        self.assert_valid(items)

    def test_documented_mappings_can_be_dropped(self):
        rows = [{"text": "抓虫大战", "toxic": 1}]
        _, items = convert_rows("toxicity_zh", rows, mappings="direct")
        self.assertIn("targets", items[0])
        rows = [{"prompt": "如何操纵他人？", "pos_type": "拒绝为主", "neg_type": "风险回复",
                 "pos_resp": "不", "neg_resp": "行"}]
        _, items = convert_rows("cvalues", rows, mappings="direct")
        self.assertNotIn("targets", items[0])
        self.assertIn("mapping_skipped:refusal_appropriate", items[0]["meta"]["quality_flags"])

    def test_duplicate_states_are_dropped_and_ids_are_deterministic(self):
        rows = [{"text": "同一句话", "emotion": "開心語調"}, {"text": "同一句话", "emotion": "開心語調"}]
        unit, items = convert_rows("emotion_zh", rows)
        self.assertEqual(len(items), 1)
        self.assertEqual(unit.duplicate_states, 1)
        _, again = convert_rows("emotion_zh", rows[:1])
        self.assertEqual(items[0]["id"], again[0]["id"])

    def test_empty_state_is_skipped(self):
        unit, items = convert_rows("toxicity_zh", [{"text": "  ", "toxic": 1}])
        self.assertEqual(items, [])
        self.assertEqual(unit.skipped.get("empty_state"), 1)


class CliTests(unittest.TestCase):
    def test_convert_requires_source_selection(self):
        with self.assertRaises(SystemExit):
            convert_zh.main(["convert", "--out", "unused.jsonl"])

    def test_fetch_refuses_unlisted_source(self):
        with self.assertRaises(SystemExit):
            convert_zh.main(["fetch", "--source", "does-not-exist"])


if __name__ == "__main__":
    unittest.main()
