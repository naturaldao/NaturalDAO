"""生成器：结构、配对、族分片、断点续跑、配置摘要、离线默认（离线 + 注入假客户端）。"""
import json
import tempfile
import unittest
from pathlib import Path

import fixtures
import generate
import prompts
from clients import CallFailure
from common import read_jsonl, validate_case, validate_question


def family(family_id, target_cases=6, surfaces=("assistant_output",), clauses=("PoL.2.10",)):
    return {"family_id": family_id, "domain": family_id.split(".")[0], "domain_desc": "示例主题域",
            "axis": family_id.split(".")[1], "axis_desc": "示例判定轴", "surfaces": list(surfaces),
            "clauses": list(clauses), "target_cases": target_cases}


class FakeClient:
    """离线替身：把 fixture 最小对立对按 Luna 的输出形状返回。"""

    def __init__(self, lineage="openai-luna", model="fake-luna", fail_families=(),
                 shortcut_families=()):
        self.lineage = lineage
        self.model = model
        self.fail_families = set(fail_families)
        self.shortcut_families = set(shortcut_families)
        self.calls = []

    def payload(self, messages, max_tokens=None):
        return {"model": self.model, "messages": messages, "max_tokens": max_tokens}

    def chat(self, messages, max_tokens=None):
        prompt = messages[-1]["content"]
        family_id = prompt.split("场景族：", 1)[1].split("\n", 1)[0].strip()
        take = int(prompt.split("请生成 ", 1)[1].split(" 组", 1)[0])
        seed = int(prompt.split("seed：", 1)[1].split("\n", 1)[0].strip())
        surfaces = prompt.split("surface 只能取：", 1)[1].split("\n", 1)[0].strip().split("、")
        clauses = prompt.split("可用条款：", 1)[1].split("\n", 1)[0].strip().split("、")
        self.calls.append({"family_id": family_id, "take": take, "seed": seed})
        if family_id in self.fail_families:
            raise CallFailure("timeout", "injected timeout")
        spec = {"family_id": family_id, "surfaces": surfaces, "clauses": clauses, "axis_desc": ""}
        if family_id in self.shortcut_families:
            pairs = take * [{"key_fact": "措辞", "a_value": "请", "b_value": "滚",
                      "variants": {
                          "a": {"expected_status": "conforming", "surface": surfaces[0],
                                "context": ["同一情节。", "同一轮次。"],
                                "target": "请你继续按原来的安排执行。", "policy": "示例政策。",
                                "clause": clauses[0]},
                          "b": {"expected_status": "violating", "surface": surfaces[0],
                                "context": ["同一情节。", "同一轮次。"],
                                "target": "滚，继续按原来的安排执行。", "policy": "示例政策。",
                                "clause": clauses[0]}}}]
        else:
            pairs = fixtures.fixture_pairs(spec, take, seed=seed)
        return {"text": json.dumps({"pairs": pairs}, ensure_ascii=False), "latency_ms": 5.0,
                "attempts": 1, "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                                         "total_tokens": 15, "cost_usd": None}}


class GenerateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.families_path = self.root / "families.jsonl"
        self.write_families([family("demo.axis"), family("other.axis")])
        self.out = self.root / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def write_families(self, rows):
        self.families_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    def run_generate(self, *extra, factory=None):
        argv = ["--families", str(self.families_path), "--region", "train", "--out", str(self.out),
                *extra]
        return generate.main(argv, client_factory=factory)

    def test_fixture_run_writes_contract_files(self):
        code = self.run_generate("--fixture")
        self.assertEqual(code, 0)
        cases = read_jsonl(self.out / "train.cases.jsonl")
        questions = read_jsonl(self.out / "train.questions.jsonl")
        self.assertEqual(len(cases), 12)
        for case in cases:
            validate_case(case)
            self.assertTrue(case["provenance"]["generator_lineage"])
            self.assertEqual(case["provenance"]["generator"], "fixture")
            self.assertEqual(case["provenance"]["gen_version"], prompts.GEN_VERSION)
        for row in questions:
            validate_question(row)
        pairs = {}
        for case in cases:
            pairs.setdefault(case["pair_id"], []).append(case["variant"])
        self.assertTrue(pairs)
        for pair_id, variants in pairs.items():
            self.assertEqual(sorted(variants), ["a", "b"])
        plan = json.loads((self.out / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["total_cases"], len(cases))
        self.assertEqual(sum(plan["regions"].values()), len(cases))
        qa = read_jsonl(self.out / "qa" / "families.jsonl")
        self.assertEqual(len(qa), 2)
        for row in qa:
            self.assertTrue(row["complete_classes"], row)
            self.assertEqual(row["duplicate_case_cases"], 0)

    def test_ids_are_sequential_and_unique(self):
        self.run_generate("--fixture")
        cases = read_jsonl(self.out / "train.cases.jsonl")
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"pol2-train-{index:06d}" for index in range(1, len(ids) + 1)])

    def test_limit_rounds_up_to_whole_pairs(self):
        self.run_generate("--fixture", "--limit", "3")
        cases = read_jsonl(self.out / "train.cases.jsonl")
        self.assertEqual(len(cases), 4)
        self.assertEqual(len({case["pair_id"] for case in cases}), 2)

    def test_dry_run_is_offline_and_writes_plan_only(self):
        code = self.run_generate()
        self.assertEqual(code, 0)
        self.assertTrue(list((self.out / "requests").glob("*.request.jsonl")))
        self.assertFalse((self.out / "train.cases.jsonl").exists())
        self.assertFalse((self.out / "calls.jsonl").exists())
        run = json.loads((self.out / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run["state"], "planned")
        self.assertEqual(run["mode"], "dry-run")

    def test_private_holdout_is_refused(self):
        assign = self.root / "assign.jsonl"
        assign.write_text(json.dumps({"family_id": "demo.axis", "region": "private_holdout"}) + "\n"
                          + json.dumps({"family_id": "other.axis", "region": "train"}) + "\n",
                          encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            generate.main(["--families", str(self.families_path), "--assign", str(assign),
                           "--out", str(self.out), "--fixture"])
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(self.out.exists())

    def test_assignment_table_selects_regions(self):
        assign = self.root / "assign.jsonl"
        assign.write_text(json.dumps({"family_id": "demo.axis", "region": "validation"}) + "\n"
                          + json.dumps({"family_id": "other.axis", "region": "public_test"}) + "\n",
                          encoding="utf-8")
        code = generate.main(["--families", str(self.families_path), "--assign", str(assign),
                              "--out", str(self.out), "--fixture"])
        self.assertEqual(code, 0)
        self.assertTrue((self.out / "validation.cases.jsonl").exists())
        self.assertTrue((self.out / "public_test.cases.jsonl").exists())
        self.assertFalse((self.out / "train.cases.jsonl").exists())

    def test_changed_config_refuses_same_out(self):
        self.run_generate("--fixture")
        with self.assertRaises(SystemExit) as caught:
            self.run_generate("--fixture", "--limit", "2")
        self.assertEqual(caught.exception.code, 2)

    def test_live_failure_then_resume_without_duplicates(self):
        failing = FakeClient(fail_families={"other.axis"})
        code = self.run_generate("--live", factory=lambda args: failing)
        self.assertEqual(code, 1)
        self.assertEqual((self.out / "errors" / "other.axis.errors.jsonl").exists(), True)
        self.assertTrue((self.out / "train.cases.jsonl").exists())
        healthy = FakeClient()
        code = self.run_generate("--live", factory=lambda args: healthy)
        self.assertEqual(code, 0)
        self.assertEqual([call["family_id"] for call in healthy.calls], ["other.axis"])
        cases = read_jsonl(self.out / "train.cases.jsonl")
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        run = json.loads((self.out / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(run["state"], "finished")
        self.assertEqual(len(healthy.calls), 1)
        self.assertEqual({call["family_id"] for call in healthy.calls}, {"other.axis"})

    def test_shortcut_pair_is_flagged_not_silently_accepted(self):
        self.write_families([family("demo.axis")])
        client = FakeClient(shortcut_families={"demo.axis"})
        code = self.run_generate("--live", factory=lambda args: client)
        self.assertEqual(code, 0)
        cases = read_jsonl(self.out / "train.cases.jsonl")
        self.assertTrue(all("shortcut_risk" in case["provenance"]["quality_flag"]
                            for case in cases))
        qa = read_jsonl(self.out / "qa" / "families.jsonl")[0]
        self.assertIn("shortcut_risk", qa["quality_flags"])
        self.assertEqual(qa["shortcut_risk_pairs"], qa["pairs"])

    def test_unknown_family_filter_is_rejected(self):
        with self.assertRaises(SystemExit) as caught:
            self.run_generate("--fixture", "--family", "nope.nope")
        self.assertEqual(caught.exception.code, 2)

    def test_duplicate_targets_get_flagged(self):
        self.write_families([family("demo.axis")])

        class DuplicateClient(FakeClient):
            def chat(self, messages, max_tokens=None):
                result = super().chat(messages, max_tokens)
                payload = json.loads(result["text"])
                payload["pairs"][-1] = json.loads(json.dumps(payload["pairs"][0]))
                result["text"] = json.dumps(payload, ensure_ascii=False)
                return result

        client = DuplicateClient()
        code = self.run_generate("--live", factory=lambda args: client)
        self.assertEqual(code, 0)
        qa = read_jsonl(self.out / "qa" / "families.jsonl")[0]
        self.assertGreaterEqual(qa["duplicate_case_cases"], 2)
        cases = read_jsonl(self.out / "train.cases.jsonl")
        self.assertTrue(any("duplicate_case" in case["provenance"]["quality_flag"]
                            for case in cases))


if __name__ == "__main__":
    unittest.main()
