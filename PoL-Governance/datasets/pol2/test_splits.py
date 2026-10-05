"""splits.py 的分区不变量测试。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datasets.pol2 import splits  # noqa: E402


def families(n=40, target=10):
    """Unique family ids: the axis index carries i, so no two rows can collide."""
    return [{"family_id": f"dom{i % 5}.axis{i}", "target_cases": target}
            for i in range(n)]


class AssignTest(unittest.TestCase):
    def test_is_deterministic_for_same_salt(self):
        rows = families()
        self.assertEqual(splits.assign(rows, "salt-a"), splits.assign(rows, "salt-a"))

    def test_different_salt_changes_private_holdout(self):
        rows = families()
        a = {r["family_id"] for r in splits.assign(rows, "salt-a") if r["region"] == "private_holdout"}
        b = {r["family_id"] for r in splits.assign(rows, "salt-b") if r["region"] == "private_holdout"}
        self.assertNotEqual(a, b)

    def test_every_family_assigned_once(self):
        rows = families()
        assigned = splits.assign(rows, "salt")
        self.assertEqual(len(assigned), len(rows))
        self.assertEqual(len({r["family_id"] for r in assigned}), len(rows))

    def test_shares_hit_targets(self):
        stats = splits.check_assignment(splits.assign(families(200), "salt"), families(200))
        for region, row in stats["regions"].items():
            self.assertLess(abs(row["case_share"] - row["target_share"]), 0.03, region)

    def test_verify_rejects_missing_and_duplicate(self):
        rows = families()
        good = splits.assign(rows, "salt")
        with self.assertRaises(ValueError):
            splits.check_assignment(good[:-1], rows)
        with self.assertRaises(ValueError):
            splits.check_assignment(good + [good[0]], rows)
        with self.assertRaises(ValueError):
            splits.check_assignment(good + [{"family_id": "nope", "region": "train",
                                             "target_cases": 1}], rows)

    def test_empty_salt_rejected(self):
        with self.assertRaises(ValueError):
            splits.assign(families(), "")


class CliGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.fam = self.dir / "families.jsonl"
        splits.write_jsonl(self.fam, families())

    def tearDown(self):
        self.tmp.cleanup()

    def test_assign_refuses_to_write_inside_repository(self):
        salt = self.dir / "salt"
        salt.write_text("secret", encoding="utf-8")
        target = splits.MODULE_ROOT / "datasets" / "pol2" / "_should_not_exist.jsonl"
        with self.assertRaises(SystemExit):
            splits.main(["assign", "--families", str(self.fam), "--salt-file", str(salt),
                         "--out", str(target)])
        self.assertFalse(target.exists())

    def test_subset_refuses_private_holdout(self):
        salt = self.dir / "salt"
        salt.write_text("secret", encoding="utf-8")
        out = self.dir / "assign.jsonl"
        splits.main(["assign", "--families", str(self.fam), "--salt-file", str(salt),
                     "--out", str(out)])
        with self.assertRaises(SystemExit):
            splits.main(["subset", "--assign", str(out), "--families", str(self.fam),
                         "--regions", "train,private_holdout",
                         "--out", str(self.dir / "pub.jsonl")])

    def test_subset_contains_only_public_families(self):
        salt = self.dir / "salt"
        salt.write_text("secret", encoding="utf-8")
        out = self.dir / "assign.jsonl"
        splits.main(["assign", "--families", str(self.fam), "--salt-file", str(salt),
                     "--out", str(out)])
        pub = self.dir / "pub.jsonl"
        splits.main(["subset", "--assign", str(out), "--families", str(self.fam),
                     "--out", str(pub)])
        keep = {json.loads(line)["family_id"] for line in pub.read_text(encoding="utf-8").splitlines()}
        held = {json.loads(line)["family_id"] for line in out.read_text(encoding="utf-8").splitlines()
                if json.loads(line)["region"] == "private_holdout"}
        self.assertFalse(keep & held)
        self.assertTrue(keep)


if __name__ == "__main__":
    unittest.main()
