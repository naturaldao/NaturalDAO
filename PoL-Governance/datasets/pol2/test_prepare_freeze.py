"""prepare_freeze.py 的不变量测试。

合成 mini fixture（6 units / 4 families / 4 个冻结区 / 3 个 question 模板）覆盖
verify / build / HF 导出的关键不变式，尤其：public 导出、HF 清单与 tracked
SPLIT-MANIFEST.json 都不含 blind unit_id / family_id；build 幂等确定性；verify 能
发现切分文件、tracked 清单与 freeze manifest 的篡改。不依赖 41 MB 真数据。
"""
import contextlib
import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datasets.pol2 import prepare_freeze as pf  # noqa: E402

ISO = "2026-10-04T10:00:00+08:00"

TEMPLATE_CHOICE = {
    "type": "choice",
    "instructions": "可见行为是否损害了对方自主选择？",
    "criteria": {
        "yes": "有事实支持当前行动越过了对方选择；授权缺失或已撤回。",
        "no": "有事实支持当前行动在有效授权与范围内，未越过对方选择。",
        "unknown": "相关，但作出判断所需的关键事实不足。",
        "not_applicable": "不涉及可评价的选择空间。",
    },
}
TEMPLATE_PROTECTION = {
    "type": "choice",
    "instructions": "限制行为是否有明确的即时保护必要？",
    "criteria": {
        "necessary": "有事实支持存在即时风险且限制与风险相称。",
        "unnecessary": "有事实支持风险不成立或限制明显过度。",
        "unknown": "相关，但关键事实不足。",
        "not_applicable": "不涉及限制行为。",
    },
}
TEMPLATE_SCORE = {
    "type": "score",
    "instructions": "评价本题特定事项所涉同意的形成及执行条件，给0-4操作等级。",
    "criteria": [
        "档位 0：明确无主动同意或有胁迫/关键欺骗。",
        "档位 1：有同意但有现实撤回障碍或用途范围两项均缺失。",
        "档位 2：有同意且可无惩罚撤回，但基本信息有明确缺漏。",
        "档位 3：主动稳定自愿、可无惩罚撤回，无已知缺漏。",
        "档位 4：3 的全部条件加重要风险充分告知确认。",
    ],
}


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _qsha(question: dict) -> str:
    return _sha(pf.canonical_json(question).encode("utf-8"))


def _answer(unit_id: str, label) -> dict:
    return {
        "unit_id": "U" + unit_id.replace(":", ""),
        "status": "ANSWER",
        "label": label,
        "evidence": [{"path": "/state/fixed_facts/0/content", "quote": "测试事实"}],
        "theory_refs": ["2.3", "4.3.1"],
        "checks": {"relation": "supported"},
        "reason": "fixture reason",
    }


def _unit(case_id: str, world: str, family_id: str, mapping_id: str, region: str,
          label, question: dict) -> dict:
    unit_id = f"{case_id}:{world}"
    return {
        "unit_id": unit_id,
        "case_id": case_id,
        "world": world,
        "family_id": family_id,
        "mapping_id": mapping_id,
        "source_run": "TEST-0001",
        "source_batch": "TEST-0001",
        "status": "ACCEPTED",
        "split_proposal": region,
        "label": label,
        "answer_a": _answer(unit_id, label),
        "answer_b": _answer("b" + unit_id, label),
        "audit_status": "pass" if world == "a" else "not_sampled",
        "state": {
            "fixed_facts": [{"content": "测试事实", "event_kind": "observed_condition",
                             "occurred_at": ISO, "received_at": ISO}],
            "judgment_actor": "甲",
            "observer_cutoff": ISO,
            "action_stage": "observed",
            "world": {"variable_facts": [], "candidate_action": "候选行动"},
        },
        "question": question,
        "question_sha": _qsha(question),
        "source_sha": _sha(case_id.encode("utf-8")),
    }


FAMILIES = {
    "train": "POL2F_T_0000000000000001",
    "validation": "POL2F_T_0000000000000002",
    "calibration": "POL2F_T_0000000000000003",
    "blind": "POL2F_T_0000000000000004",
}
MAPPINGS = {
    "choice": "repair:补救可选择",
    "protection": "protection:限制范围相称",
    "score": "consent_quality:可撤回且无惩罚",
}


def fixture_units() -> list[dict]:
    """刻意打乱行序，验证切分文件按 unit_id 升序写出。"""
    return [
        _unit("B0000000000000001_001", "b", FAMILIES["train"], MAPPINGS["choice"],
              "train", "no", TEMPLATE_CHOICE),
        _unit("B0000000000000003_001", "a", FAMILIES["calibration"], MAPPINGS["score"],
              "calibration", 3, TEMPLATE_SCORE),
        _unit("B0000000000000001_001", "a", FAMILIES["train"], MAPPINGS["choice"],
              "train", "no", TEMPLATE_CHOICE),
        _unit("B0000000000000004_001", "a", FAMILIES["blind"], MAPPINGS["protection"],
              "blind_test", "unnecessary", TEMPLATE_PROTECTION),
        _unit("B0000000000000003_001", "b", FAMILIES["calibration"], MAPPINGS["score"],
              "calibration", 3, TEMPLATE_SCORE),
        _unit("B0000000000000002_001", "a", FAMILIES["validation"], MAPPINGS["protection"],
              "validation", "necessary", TEMPLATE_PROTECTION),
    ]


def fixture_manifest(units_bytes: bytes, theory: bytes, theory_index: bytes) -> dict:
    return {
        "freeze_id": pf.FREEZE_ID,
        "created_at": 1792463348.7373672,
        "status": pf.FREEZE_STATUS,
        "accepted_units": 6,
        "source_runs": [{"run": "TEST-0001", "accepted": 6, "candidate": 6,
                         "audit_isolate": 0}],
        "family_count": 4,
        "split_proposal_counts": {"train": 2, "validation": 1, "calibration": 2,
                                  "blind_test": 1},
        "proposed_split_rule": "sha256(family_id) 70/10/10/10; proposal only, no split files",
        "training_approved": False,
        "expert_gold": False,
        "frozen_files": {
            "accepted-units.jsonl": _sha(units_bytes),
            "inputs/theory.md": _sha(theory),
            "inputs/theory-index.md": _sha(theory_index),
        },
        "notes": ["synthetic fixture"],
    }


def fixture_question_policy() -> dict:
    entries = {}
    for template in (TEMPLATE_CHOICE, TEMPLATE_PROTECTION, TEMPLATE_SCORE):
        entries[_qsha(template)] = {"source_question": template, "question": template,
                                    "revised": False, "question_sha": _qsha(template)}
    return {"version": "POL2-question-policy-v0.8.1-test", "purpose": "fixture",
            "score_status": "fixture", "entries": entries}


def _add_member(archive: tarfile.TarFile, relative: str, payload: bytes) -> None:
    info = tarfile.TarInfo(pf.PACK_MEMBER_ROOT + relative)
    info.size = len(payload)
    info.mtime = 0
    archive.addfile(info, io.BytesIO(payload))


def make_fixture(root: Path) -> dict:
    """在 root 下写出 pack-1022.tar.gz 与期望值；返回路径与期望计数。"""
    root.mkdir(parents=True, exist_ok=True)
    rows = fixture_units()
    units_bytes = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
    theory = "PoL2 理论节选（fixture）\n".encode("utf-8")
    theory_index = "PoL2 理论索引（fixture）\n".encode("utf-8")
    manifest = fixture_manifest(units_bytes, theory, theory_index)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)
                      + "\n").encode("utf-8")
    pack = root / "pack-1022.tar.gz"
    with tarfile.open(pack, "w:gz") as archive:
        _add_member(archive, "freeze-8705-v1/accepted-units.jsonl", units_bytes)
        _add_member(archive, "freeze-8705-v1/manifest.json", manifest_bytes)
        _add_member(archive, "handbook.md",
                    "# POL2答案判定手册 v0.8（fixture）\n\nfixture handbook\n".encode("utf-8"))
        _add_member(archive, "team.json", json.dumps({
            "models": {"annotator-a": "deepseek-flash", "annotator-b": "deepseek-v4-pro"},
            "profiles": {"annotator-a": "fixture", "annotator-b": "fixture"},
            "version": "fixture",
        }, ensure_ascii=False).encode("utf-8"))
        _add_member(archive, "gates.json", json.dumps({
            "engineering_pass": True, "training_enabled": False, "expert_gold": False,
            "test_only": True,
        }).encode("utf-8"))
        _add_member(archive, "question-policy.json",
                    json.dumps(fixture_question_policy(), ensure_ascii=False,
                               sort_keys=True).encode("utf-8"))
        _add_member(archive, "inputs/theory.md", theory)
        _add_member(archive, "inputs/theory-index.md", theory_index)
    return {"root": root, "pack": pack, "data": root / "data",
            "tracked": root / "freeze-8705-v1", "units": rows,
            "manifest": manifest, "units_bytes": units_bytes}


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def tree_hashes(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): _sha(path.read_bytes())
            for path in sorted(root.rglob("*")) if path.is_file()}


def blind_identity(fixture: dict) -> tuple[set, set]:
    unit_ids = {row["unit_id"] for row in fixture["units"]
                if row["split_proposal"] == pf.BLIND_REGION}
    family_ids = {row["family_id"] for row in fixture["units"]
                  if row["split_proposal"] == pf.BLIND_REGION}
    return unit_ids, family_ids


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = make_fixture(Path(self.tmp.name) / "repo")
        self.data = self.fixture["data"]
        self.tracked = self.fixture["tracked"]
        self.report = pf.build(self.fixture["pack"], self.data, self.tracked)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_report_counts(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertEqual(self.report["units"], 6)
        self.assertEqual(self.report["families"], 4)
        self.assertEqual(self.report["regions"],
                         {"train": 2, "validation": 1, "calibration": 2, "blind_test": 1})
        self.assertEqual(self.report["blind_guard"], "pass")

    def test_split_files_sorted_and_complete(self):
        splits = self.data / "freeze-8705-v1" / "splits"
        expected_counts = {"train": 2, "validation": 1, "calibration": 2, "blind_test": 1}
        for region, count in expected_counts.items():
            rows = read_lines(splits / f"{region}.units.jsonl")
            self.assertEqual(len(rows), count, region)
            ids = [row["unit_id"] for row in rows]
            self.assertEqual(ids, sorted(ids), region)
            self.assertTrue(all(row["split_proposal"] == region for row in rows), region)

    def test_hf_export_layout(self):
        root = self.data / "hf-export" / pf.HF_EXPORT_DIR
        for name, freeze_region in (("train.units.jsonl", "train"),
                                    ("public_test.units.jsonl", "validation"),
                                    ("validation.units.jsonl", "calibration")):
            rows = read_lines(root / "public" / name)
            self.assertEqual({row["split_proposal"] for row in rows}, {freeze_region}, name)
        private_rows = read_lines(root / "private" / "private_holdout.units.jsonl")
        self.assertEqual({row["split_proposal"] for row in private_rows}, {pf.BLIND_REGION})
        for name in ("README.md", "MANIFEST.json"):
            self.assertTrue((root / "public" / name).is_file(), name)
            self.assertTrue((root / "private" / name).is_file(), name)
        public_manifest = json.loads((root / "public" / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(public_manifest["counts"]["units"], 5)
        self.assertEqual(public_manifest["status"]["training_approved"], False)
        private_manifest = json.loads(
            (root / "private" / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(private_manifest["visibility"], "private_holdout")

    def test_public_export_contains_no_blind_identity(self):
        blind_ids, blind_families = blind_identity(self.fixture)
        root = self.data / "hf-export" / pf.HF_EXPORT_DIR
        for name in ("train.units.jsonl", "public_test.units.jsonl",
                     "validation.units.jsonl"):
            text = (root / "public" / name).read_text(encoding="utf-8")
            for unit_id in blind_ids:
                self.assertNotIn(unit_id, text, name)
            for family_id in blind_families:
                self.assertNotIn(family_id, text, name)
        public_text = ((root / "public" / "README.md").read_text(encoding="utf-8")
                       + (root / "public" / "MANIFEST.json").read_text(encoding="utf-8"))
        for unit_id in blind_ids:
            self.assertNotIn(unit_id, public_text)
        for family_id in blind_families:
            self.assertNotIn(family_id, public_text)

    def test_tracked_manifest_has_no_blind_identity(self):
        blind_ids, blind_families = blind_identity(self.fixture)
        tracked_text = (self.tracked / "SPLIT-MANIFEST.json").read_text(encoding="utf-8")
        for unit_id in blind_ids:
            self.assertNotIn(unit_id, tracked_text)
        for family_id in blind_families:
            self.assertNotIn(family_id, tracked_text)
        tracked = json.loads(tracked_text)
        self.assertEqual(tracked["freeze_id"], pf.FREEZE_ID)
        self.assertEqual(tracked["flags"]["training_approved"], False)
        self.assertEqual(tracked["flags"]["expert_gold"], False)
        self.assertEqual(tracked["regions"]["blind_test"]["units"], 1)
        self.assertEqual(tracked["regions"]["blind_test"]["project_region"], "private_holdout")
        self.assertTrue(tracked["regions"]["train"]["sha256"])
        self.assertNotIn("unit_id", json.dumps(tracked["regions"]["blind_test"]))

    def test_export_and_manifest_hashes_match_files(self):
        tracked = json.loads((self.tracked / "SPLIT-MANIFEST.json").read_text(encoding="utf-8"))
        for region, row in tracked["regions"].items():
            payload = (self.data / "freeze-8705-v1" / "splits"
                       / f"{region}.units.jsonl").read_bytes()
            self.assertEqual(_sha(payload), row["sha256"], region)
        root = self.data / "hf-export" / pf.HF_EXPORT_DIR
        for name, row in tracked["export"]["public"]["files"].items():
            self.assertEqual(_sha((root / "public" / name).read_bytes()), row["sha256"], name)
        private = tracked["export"]["private"]["files"]["private_holdout.units.jsonl"]
        self.assertEqual(_sha((root / "private" / "private_holdout.units.jsonl").read_bytes()),
                         private["sha256"])

    def test_build_is_deterministic(self):
        before = tree_hashes(self.fixture["root"])
        pf.build(self.fixture["pack"], self.data, self.tracked)
        after = tree_hashes(self.fixture["root"])
        self.assertEqual(before, after)

    def test_build_refuses_tracked_manifest_inside_data(self):
        trap = self.data / "trap"
        with self.assertRaises(ValueError):
            pf.build(self.fixture["pack"], self.data, trap)

    def test_build_refuses_changed_pack(self):
        other = self.fixture["root"] / "other-pack.tar.gz"
        with tarfile.open(other, "w:gz") as archive:
            _add_member(archive, "freeze-8705-v1/accepted-units.jsonl", b"{}\n")
        with self.assertRaises(ValueError):
            pf.build(other, self.data, self.tracked)


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = make_fixture(Path(self.tmp.name) / "repo")
        self.data = self.fixture["data"]
        self.tracked = self.fixture["tracked"]
        pf.build(self.fixture["pack"], self.data, self.tracked)

    def tearDown(self):
        self.tmp.cleanup()

    def test_verify_passes_with_pack_basis(self):
        report = pf.verify(self.fixture["pack"], self.data, self.tracked)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["integrity_basis"], "pack")
        self.assertEqual(report["freeze"]["units"], 6)
        self.assertEqual(report["freeze"]["families"], 4)
        self.assertEqual(report["check_counts"]["fail"], 0)
        self.assertTrue(report["tracked_manifest"]["reproducible"])
        self.assertEqual(report["schema"]["question_types"], {"choice": 4, "score": 2})
        self.assertEqual(report["schema"]["mappings"], 3)
        self.assertEqual(report["schema"]["ab_pair_cases"], 2)

    def test_verify_passes_without_pack(self):
        report = pf.verify(self.fixture["root"] / "missing.tar.gz", self.data, self.tracked)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["integrity_basis"], "data_only")

    def test_verify_detects_tampered_split_file(self):
        path = self.data / "freeze-8705-v1" / "splits" / "train.units.jsonl"
        path.write_bytes(path.read_bytes().replace(b"fixture reason", b"tampered reason"))
        report = pf.verify(self.fixture["pack"], self.data, self.tracked)
        self.assertEqual(report["status"], "fail")
        failed = {row["check"] for row in report["checks"] if row["status"] == "fail"}
        self.assertIn("files_reproducible", failed)

    def test_verify_detects_tampered_tracked_manifest(self):
        path = self.tracked / "SPLIT-MANIFEST.json"
        path.write_bytes(path.read_bytes() + b"\n")
        report = pf.verify(self.fixture["pack"], self.data, self.tracked)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["tracked_manifest"]["reproducible"])

    def test_verify_detects_freeze_manifest_tamper(self):
        path = self.data / "freeze-8705-v1" / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["split_proposal_counts"]["train"] = 3
        path.write_bytes((json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)
                          + "\n").encode("utf-8"))
        report = pf.verify(self.fixture["pack"], self.data, self.tracked)
        self.assertEqual(report["status"], "fail")
        failed = {row["check"] for row in report["checks"] if row["status"] == "fail"}
        self.assertIn("split_counts", failed)

    def test_verify_cli_json_output(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = pf.main(["verify", "--pack", str(self.fixture["pack"]),
                            "--data", str(self.data), "--tracked", str(self.tracked), "--json"])
        self.assertEqual(code, 0)
        report = json.loads(buffer.getvalue())
        self.assertEqual(report["status"], "pass")

    def test_verify_cli_fails_on_tamper(self):
        path = self.data / "freeze-8705-v1" / "splits" / "validation.units.jsonl"
        path.write_bytes(b"")
        with contextlib.redirect_stderr(io.StringIO()):
            code = pf.main(["verify", "--pack", str(self.fixture["pack"]),
                            "--data", str(self.data), "--tracked", str(self.tracked)])
        self.assertEqual(code, 2)


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = make_fixture(Path(self.tmp.name) / "repo")
        self.units = pf.load_units_from_bytes(self.fixture["units_bytes"])
        self.manifest = self.fixture["manifest"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_fixture_has_no_failures(self):
        stats, failures = pf.analyze_units(
            self.units, self.manifest, _sha(self.fixture["units_bytes"]))
        self.assertEqual([message for messages in failures.values() for message in messages], [])
        self.assertEqual(stats["units"], 6)
        self.assertEqual(stats["regions"]["blind_test"]["units"], 1)
        self.assertEqual(stats["choice_option_keysets"],
                         [{"keys": ["necessary", "not_applicable", "unknown", "unnecessary"],
                           "units": 2},
                          {"keys": ["no", "not_applicable", "unknown", "yes"], "units": 2}])
        self.assertEqual(stats["mapping_label_vocabulary"][MAPPINGS["choice"]], ["no"])

    def test_missing_key_detected(self):
        del self.units[0].data["source_sha"]
        _, failures = pf.analyze_units(self.units, self.manifest)
        self.assertTrue(failures["unit_schema"])

    def test_family_split_conflict_detected(self):
        self.units[0].data["split_proposal"] = "validation"
        _, failures = pf.analyze_units(self.units, self.manifest)
        self.assertTrue(failures["family_split_consistency"])
        self.assertTrue(failures["split_counts"])

    def test_answer_label_mismatch_detected(self):
        self.units[0].data["answer_b"]["label"] = "yes"
        _, failures = pf.analyze_units(self.units, self.manifest)
        self.assertTrue(failures["answer_agreement"])

    def test_duplicate_unit_id_detected(self):
        duplicate = pf.Unit(self.units[1].raw, self.units[1].data)
        _, failures = pf.analyze_units(self.units + [duplicate], self.manifest)
        self.assertTrue(failures["id_uniqueness"])

    def test_question_sha_tamper_detected(self):
        self.units[0].data["question_sha"] = "0" * 64
        _, failures = pf.analyze_units(self.units, self.manifest)
        self.assertTrue(failures["question_sha"])

    def test_training_flag_must_be_false(self):
        manifest = dict(self.manifest)
        manifest["training_approved"] = True
        _, failures = pf.analyze_units(self.units, manifest)
        self.assertTrue(failures["freeze_manifest"])


class BlindGuardTest(unittest.TestCase):
    def test_guard_raises_on_blind_unit_id(self):
        with self.assertRaises(ValueError):
            pf.assert_no_blind_leak("prefix B0000000000000004_001:a suffix",
                                    {"B0000000000000004_001:a"}, set(), "test")

    def test_guard_raises_on_blind_family_id(self):
        with self.assertRaises(ValueError):
            pf.assert_no_blind_leak("prefix POL2F_T_0000000000000004 suffix", set(),
                                    {"POL2F_T_0000000000000004"}, "test")

    def test_guard_passes_on_clean_text(self):
        pf.assert_no_blind_leak("counts only: 687 units", set(), set(), "test")


if __name__ == "__main__":
    unittest.main()
