"""通用回放池：HF 候选审计的离线测试（不联网，只用 fixtures/audit 快照）。

    uv run --no-project --offline python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q
"""
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "audit"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import audit  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def base_record(**overrides):
    record = {
        "id": "owner/name", "revision": "a" * 40, "license": "cc0-1.0", "license_status": "clear",
        "license_training": "yes", "license_derivative": "yes",
        "task_forms": ["choice"], "languages": ["en"], "splits": ["train"], "train_only": True,
        "is_benchmark": False, "generation": "synthetic", "source_basis": "unit test",
        "row_count": 10, "tier": "admit", "decision_reason": "unit test", "evidence_level": "A",
        "checked_at": "2026-09-30T00:00:00Z", "hf": {"benchmark_flag": False, "card_license": "cc0-1.0"},
    }
    record.update(overrides)
    return record


class ValidateRecordTests(unittest.TestCase):
    def test_valid_admit_record(self):
        self.assertEqual(audit.validate_record(base_record()), [])

    def test_missing_field_is_reported(self):
        record = base_record()
        del record["source_basis"]
        problems = audit.validate_record(record)
        self.assertTrue(any("source_basis" in problem for problem in problems))

    def test_benchmark_cannot_be_admitted(self):
        record = base_record(is_benchmark=True)
        problems = audit.validate_record(record)
        self.assertTrue(any("benchmark" in problem for problem in problems))

    def test_benchmark_tier_must_be_exclude(self):
        record = base_record(is_benchmark=True, tier="observe")
        problems = audit.validate_record(record)
        self.assertTrue(any("exclude" in problem for problem in problems))

    def test_unclear_license_cannot_be_admitted(self):
        record = base_record(license_status="unclear", license="unknown")
        problems = audit.validate_record(record)
        self.assertTrue(any("观察项" in problem for problem in problems))

    def test_admit_requires_license_allowing_training_and_derivatives(self):
        problems = audit.validate_record(base_record(license_training="no"))
        self.assertTrue(any("license_training" in problem for problem in problems))
        problems = audit.validate_record(base_record(license_derivative="unknown"))
        self.assertTrue(any("license_derivative" in problem for problem in problems))
        self.assertEqual(audit.validate_record(base_record(license_derivative="yes_with_conditions")), [])

    def test_admit_requires_train_only(self):
        problems = audit.validate_record(base_record(train_only=False))
        self.assertTrue(any("train_only" in problem for problem in problems))

    def test_admit_requires_strong_evidence(self):
        problems = audit.validate_record(base_record(evidence_level="D"))
        self.assertTrue(any("A/B" in problem for problem in problems))

    def test_admit_requires_pinned_revision(self):
        problems = audit.validate_record(base_record(revision="unpinned"))
        self.assertTrue(any("40 位" in problem for problem in problems))

    def test_hf_benchmark_flag_blocks_admit(self):
        record = base_record(hf={"benchmark_flag": True, "card_license": "cc0-1.0"})
        problems = audit.validate_record(record)
        self.assertTrue(any("benchmark/eval" in problem for problem in problems))

    def test_benchmark_flag_can_be_overridden_only_with_recorded_review(self):
        flagged = {"benchmark_flag": True, "card_license": "cc0-1.0"}
        problems = audit.validate_record(base_record(hf=flagged))
        self.assertTrue(any("benchmark_flag_review" in problem for problem in problems))
        reviewed = base_record(hf=flagged, benchmark_flag_review={
            "conclusion": "not_a_benchmark", "evidence": "标签指向被剔除的评测包", "reviewed_at": "2026-09-30"})
        self.assertEqual(audit.validate_record(reviewed), [])
        empty = base_record(hf=flagged, benchmark_flag_review={
            "conclusion": "not_a_benchmark", "evidence": "  "})
        self.assertTrue(any("benchmark_flag_review" in problem
                            for problem in audit.validate_record(empty)))

    def test_license_mismatch_with_card(self):
        record = base_record(license="mit", hf={"benchmark_flag": False, "card_license": "apache-2.0"})
        problems = audit.validate_record(record)
        self.assertTrue(any("不一致" in problem for problem in problems))

    def test_null_row_count_is_allowed_but_unknown_numbers_are_not_guessed(self):
        self.assertEqual(audit.validate_record(base_record(row_count=None)), [])
        problems = audit.validate_record(base_record(row_count="many"))
        self.assertTrue(any("row_count" in problem for problem in problems))


class SnapshotTests(unittest.TestCase):
    def test_snapshot_reads_card_license_and_tags(self):
        payload = load(FIXTURES / "datasets" / "ZefanCai__Open-Jev.json")
        snap = audit.snapshot(payload)
        self.assertEqual(snap["card_license"], "cc0-1.0")
        self.assertEqual(snap["sha"], "c67699e13d0ae25e35b77165a4b6b079bedc8aba")
        self.assertEqual(snap["files"], 3)

    def test_license_falls_back_to_tags(self):
        payload = load(FIXTURES / "datasets" / "mystery__decisions.json")
        self.assertIsNone(audit.license_of(payload))

    def test_benchmark_flag_from_tags_and_name(self):
        bench = load(FIXTURES / "datasets" / "Praveenrajus__jev-bench.json")
        self.assertTrue(audit.benchmark_flag("Praveenrajus/jev-bench", bench["tags"]))
        plain = load(FIXTURES / "datasets" / "ZefanCai__Open-Jev.json")
        self.assertFalse(audit.benchmark_flag("ZefanCai/Open-Jev", plain["tags"]))
        self.assertTrue(audit.benchmark_flag("someone/decision-holdout", []))


class BuildAndVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.candidates = FIXTURES / "candidates.json"
        self.out = self.root / "audit.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_from_fixtures(self):
        code = audit.main(["build", "--candidates", str(self.candidates),
                           "--fixtures", str(FIXTURES), "--out", str(self.out)])
        self.assertEqual(code, 0)
        report = load(self.out)
        self.assertEqual(report["mode"], "fixtures")
        self.assertEqual([record["tier"] for record in report["records"]],
                         ["admit", "exclude", "observe"])
        self.assertEqual(report["summary"]["admit"], 1)
        self.assertEqual(report["search_hits"], {"jev": 2})
        self.assertEqual(report["problems"], [])

    def test_verify_accepts_built_audit(self):
        audit.main(["build", "--candidates", str(self.candidates), "--fixtures", str(FIXTURES),
                    "--out", str(self.out)])
        self.assertEqual(audit.main(["verify", "--audit", str(self.out)]), 0)

    def test_verify_rejects_admitted_benchmark(self):
        audit.main(["build", "--candidates", str(self.candidates), "--fixtures", str(FIXTURES),
                    "--out", str(self.out), "--keep-going"])
        report = load(self.out)
        report["records"][1]["tier"] = "admit"          # jev-bench 被偷偷放进池
        report["records"][1]["train_only"] = True
        report["records"][1]["hf"] = {"benchmark_flag": True}
        self.out.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(audit.main(["verify", "--audit", str(self.out)]), 1)

    def test_revision_drift_is_reported(self):
        candidates = load(self.candidates)
        candidates["candidates"][0]["revision"] = "b" * 40
        path = self.root / "candidates.json"
        path.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
        code = audit.main(["build", "--candidates", str(path), "--fixtures", str(FIXTURES),
                           "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_missing_snapshot_is_reported(self):
        candidates = load(self.candidates)
        candidates["candidates"].append(dict(candidates["candidates"][0], id="ghost/missing"))
        path = self.root / "candidates.json"
        path.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
        code = audit.main(["build", "--candidates", str(path), "--fixtures", str(FIXTURES),
                           "--out", str(self.out)])
        self.assertEqual(code, 1)

    def test_duplicate_candidate_ids_rejected(self):
        candidates = load(self.candidates)
        candidates["candidates"].append(dict(candidates["candidates"][0]))
        path = self.root / "candidates.json"
        path.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            audit.main(["build", "--candidates", str(path), "--fixtures", str(FIXTURES),
                        "--out", str(self.out)])

    def test_fetch_failure_is_loud(self):
        with mock.patch.object(audit, "hf_get", side_effect=RuntimeError("offline")):
            with self.assertRaises(SystemExit):
                audit.main(["fetch", "--candidates", str(self.candidates), "--out",
                            str(self.out), "--search", "jev"])

    def test_real_candidates_file_parses_and_covers_benchmarks(self):
        real = HERE / "candidates.json"
        payload = load(real)
        candidates = payload["candidates"]
        self.assertGreaterEqual(len(candidates), 50)
        benchmarks = [row for row in candidates if row["is_benchmark"]]
        self.assertTrue(benchmarks)
        for row in benchmarks:
            self.assertEqual(row["tier"], "exclude")
        for row in candidates:
            self.assertRegex(row["revision"], r"^[0-9a-f]{40}$")
            self.assertIn(row["tier"], audit.TIERS)
            self.assertIn(row["evidence_level"], audit.EVIDENCE_LEVELS)
            self.assertIn(row["license_training"], audit.LICENSE_USE)
            self.assertIn(row["license_derivative"], audit.LICENSE_USE)
            if row["tier"] == "admit":
                self.assertEqual(row["license_training"], "yes")
            self.assertTrue(row["decision_reason"].strip())

    def test_real_candidates_only_admit_train(self):
        for row in load(HERE / "candidates.json")["candidates"]:
            if row["tier"] == "admit":
                self.assertTrue(row["train_only"])
                self.assertFalse(row["is_benchmark"])
                self.assertIn(row["license_status"], ("clear", "composite"))


if __name__ == "__main__":
    unittest.main()
