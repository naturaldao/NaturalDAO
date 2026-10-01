"""锚点迁移：映射正确性、幂等、dry-run 不落盘、退役前缀清零、policy 待裁定清单。"""
import gzip
import json
import tempfile
import unittest
from pathlib import Path

import migrate_anchors as ma

GUARD_PATH = "datasets/pol2/ontology/check_ontology.py"


def jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def case(case_id, clause, policy):
    return {"id": case_id, "family_id": "demo.axis", "region": "train", "lang": "zh",
            "input": {"surface": "assistant_output", "context": ["甲说现在不想继续。"],
                      "target": "助手继续原来的安排。", "policy": policy, "clause": clause},
            "provenance": {"generator": "luna", "model": "gpt-6-luna",
                           "prompt_id": "pol2.gen.v0.1.demo.axis", "gen_version": "pol2-gen-v0.1",
                           "seed": 1, "created_at": "2026-10-02T00:00:00+00:00",
                           "generator_lineage": "openai-luna", "quality_flag": []}}


class MigrationTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        rows = [case("pol2-train-000001", "EAP.5.3.2", "依据 EAP.5.3.2：不得虚构亲密。"),
                case("pol2-train-000002", "PoL.1.3", "野蛮2 造成伤害。"),
                case("pol2-train-000003", "PoL.2.10", "身体接触需要持续同意。")]
        (self.root / "train.cases.jsonl").write_text(jsonl(rows), encoding="utf-8")
        (self.root / "notes.md").write_text(
            "见 EAP.5.3.1 与 PoL.3.4.1；第 5 章与 3.4 节是自然语言，不该被替换；PoL.2.10 不变。\n",
            encoding="utf-8")
        (self.root / "code.py").write_text('ANCHOR = "ENG.6.1"\n', encoding="utf-8")
        packed_plain = self.root / "x.jsonl"
        packed_plain.write_text('{"clause": "EAP.5.3.2"}\n', encoding="utf-8")
        with open(self.root / "x.jsonl.gz", "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                stream.write(packed_plain.read_bytes())
        guard = self.root / GUARD_PATH
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text('RETIRED = ("EAP.5.", "PoL.3.4", "PoL.3.6", "ENG.6.")\n',
                         encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, relative):
        return (self.root / relative).read_text(encoding="utf-8")


class MappingTests(unittest.TestCase):
    def test_identifier_rewrites(self):
        cases = {"EAP.5.3.2": "EAP.4.3.2", "EAP.5.1": "EAP.4.1", "PoL.3.4.1": "PoL.5.4.1",
                 "PoL.3.4": "PoL.5.4", "PoL.3.6": "PoL.5.6", "PoL.3.1": "PoL.5.1",
                 "ENG.6.1": "ENG.1"}
        for old, new in cases.items():
            migrated, hits = ma.migrate_text(old)
            self.assertEqual(migrated, new, old)
            self.assertEqual(hits, 0 if old == new else 1, old)

    def test_untouched_text(self):
        for text in ("PoL.1.4", "PoL.2.10", "第 5 章", "3.4 节", "PoL.13.4", "XPoL.3.4"):
            migrated, _hits = ma.migrate_text(f"前缀{text}后缀")
            self.assertEqual(migrated, f"前缀{text}后缀", text)

    def test_bare_chapter_references_follow_the_same_rule(self):
        # anchor_audit.renumbering 就是章级映射：EAP.5→EAP.4、PoL.3→PoL.5、ENG.6→ENG.1
        for old, new in (("EAP.5", "EAP.4"), ("PoL.3", "PoL.5"), ("ENG.6", "ENG.1")):
            migrated, _hits = ma.migrate_text(f"参见 {old} 章")
            self.assertEqual(migrated, f"参见 {new} 章")

    def test_retired_counter(self):
        self.assertEqual(ma.count_hits("EAP.5.3.2 与 PoL.3.4.1 与 ENG.6.1"), 3)
        self.assertEqual(ma.count_hits("PoL.2.10 与 第 5 章"), 0)


class RunTests(MigrationTree):
    def test_dry_run_writes_nothing(self):
        before = {path: self.read(path) for path in
                  ("train.cases.jsonl", "notes.md", "code.py", "x.jsonl", GUARD_PATH)}
        report = ma.run(self.root, apply=False)
        self.assertEqual(report["mode"], "dry-run")
        self.assertGreater(report["changed_file_count"], 0)
        self.assertGreater(report["hits_before"], 0)
        for path, text in before.items():
            self.assertEqual(self.read(path), text, path)

    def test_apply_is_idempotent_and_clears_retired_prefixes(self):
        first = ma.run(self.root, apply=True)
        self.assertEqual(first["hits_after_outside_allowlist"], 0)
        self.assertIn("EAP.4.3.2", self.read("train.cases.jsonl"))
        self.assertIn("PoL.5.4.1", self.read("notes.md"))
        self.assertIn("ENG.1", self.read("code.py"))
        self.assertNotIn("EAP.5.3.2", self.read("train.cases.jsonl"))
        self.assertIn("第 5 章与 3.4 节是自然语言", self.read("notes.md"))
        second = ma.run(self.root, apply=True)
        self.assertEqual(second["changed_file_count"], 0)
        self.assertEqual(second["changed_hits"], 0)
        self.assertEqual(second["hits_after_outside_allowlist"], 0)
        self.assertEqual(second["hits_before"], second["hits_after"])

    def test_allowlisted_guard_keeps_retired_prefixes(self):
        ma.run(self.root, apply=True)
        guard = self.read(GUARD_PATH)
        self.assertIn("EAP.5.", guard)
        self.assertIn("ENG.6.", guard)
        report = ma.run(self.root, apply=True)
        self.assertEqual(report["allowlisted_residual"],
                         [{"path": GUARD_PATH, "hits": 4, "allowed": True}])

    def test_gz_sibling_is_rebuilt(self):
        ma.run(self.root, apply=True)
        with gzip.open(self.root / "x.jsonl.gz", "rt", encoding="utf-8") as stream:
            packed = stream.read()
        self.assertEqual(packed, self.read("x.jsonl"))
        self.assertIn("EAP.4.3.2", packed)

    def test_policy_review_lists_changed_clauses_only(self):
        report = ma.run(self.root, apply=False)
        review = report["policy_review"]
        self.assertEqual(review["changed_clauses"],
                         ["PoL.1.1", "PoL.1.2", "PoL.1.3", "PoL.1.4", "PoL.1.5", "EAP.4.3.2"])
        entries = review["entries"]
        self.assertEqual([entry["id"] for entry in entries],
                         ["pol2-train-000001", "pol2-train-000002"])
        self.assertEqual(review["count"], 2)
        self.assertEqual(review["by_clause"], {"EAP.4.3.2": 1, "PoL.1.3": 1})
        by_id = {entry["id"]: entry for entry in entries}
        self.assertEqual(by_id["pol2-train-000001"]["clause_new"], "EAP.4.3.2")
        self.assertTrue(by_id["pol2-train-000001"]["policy_mentions_anchor"])
        self.assertFalse(by_id["pol2-train-000002"]["policy_mentions_anchor"])
        self.assertEqual(review["policy_mentions_anchor"], 1)

    def test_main_exit_codes_and_report_files(self):
        report_path = self.root / "out" / "report.json"
        dry = ma.main(["--root", str(self.root), "--report", str(report_path)])
        self.assertEqual(dry, 1)  # 仍有未迁移命中
        self.assertTrue(report_path.is_file())
        self.assertTrue((report_path.parent / "policy-review.jsonl").is_file())
        applied = ma.main(["--root", str(self.root), "--apply", "--report", str(report_path)])
        self.assertEqual(applied, 0)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["hits_after_outside_allowlist"], 0)
        self.assertEqual(payload["mode"], "apply")


class ArtifactAllowlistTests(MigrationTree):
    """迁移自身的记录型产物必须 allowlist，否则再跑一次会把迁移依据改掉。"""

    def seed_artifacts(self):
        readme = self.root / "datasets/pol2/pipeline/README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text("映射：EAP.5.3.2 → EAP.4.3.2；PoL.3.4.1 → PoL.5.4.1。\n",
                          encoding="utf-8")
        report = self.root / "datasets/pol2/pipeline/smoke/anchor-migration-report.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"rules": [{"pattern": "EAP\\.5\\.", "replacement": "EAP.4."}],
                                      "changed": "ENG.6.1 → ENG.1"}, ensure_ascii=False),
                          encoding="utf-8")
        return readme, report

    def test_record_artifacts_are_allowlisted_and_never_rewritten(self):
        readme, report = self.seed_artifacts()
        before = (readme.read_text(encoding="utf-8"), report.read_text(encoding="utf-8"))
        result = ma.run(self.root, apply=False)
        allowed = {row["path"] for row in result["allowlisted_residual"]}
        self.assertIn("datasets/pol2/pipeline/README.md", allowed)
        self.assertIn("datasets/pol2/pipeline/smoke/anchor-migration-report.json", allowed)
        ma.run(self.root, apply=True)
        self.assertEqual(readme.read_text(encoding="utf-8"), before[0])
        self.assertEqual(report.read_text(encoding="utf-8"), before[1])

    def test_default_dry_run_is_clean_with_artifacts_present(self):
        self.seed_artifacts()
        ma.run(self.root, apply=True)
        result = ma.run(self.root, apply=False)
        self.assertEqual(result["changed_file_count"], 0)
        self.assertEqual(result["hits_after_outside_allowlist"], 0)


class RepositoryStateTests(unittest.TestCase):
    def test_repository_default_dry_run_is_idempotent(self):
        """仓库当前状态必须是"已迁移"：默认预演 changed_file_count=0、allowlist 外 0。

        这条直接锁死幂等性：将来任何人新增一份字面包含旧前缀的产物（报告/说明/清单）
        却没有加进 allowlist，这个测试立刻失败。
        """
        result = ma.run(ma.ROOT_DEFAULT, apply=False)
        self.assertEqual(result["changed_file_count"], 0, result["changed_files"][:5])
        self.assertEqual(result["hits_after_outside_allowlist"], 0,
                         result["unexpected_files_after"])
        self.assertEqual(result["unexpected_files_after"], [])


if __name__ == "__main__":
    unittest.main()
