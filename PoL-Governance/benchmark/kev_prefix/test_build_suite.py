"""benchmark/kev_prefix/build_suite.py 的单元测试（纯合成样例）。"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "build_suite.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bs = load_module("kev_prefix_build_suite", MODULE_PATH)


def q(kind, label, n=3):
    if kind == "choice":
        criteria = {f"opt_{i}": f"option {i}" for i in range(1, n + 1)}
        return {"type": "choice", "instructions": "pick", "criteria": criteria, "label": label, "src": "choice"}
    if kind == "noul":
        return {"type": "noul", "instructions": "yes?", "criteria": {"false": "no", "true": "yes"},
                "label": label, "src": "noul"}
    return {"type": "score", "instructions": "rate", "criteria": ["a", "b", "c"], "label": label, "src": "score"}


def records_and_sidecar():
    records = [
        {"state": "state one", "questions": {"q0": q("choice", "opt_2")}},
        {"state": "state two", "questions": {"q0": q("noul", True), "q1": q("score", 1)}},
    ]
    sidecar = [
        {"record": 0, "item_id": "item-a", "domain": "d1", "lang": "en", "group_id": None,
         "questions": [{"qid": "q0", "rid": "item-a#weather", "kind": "choice", "num_options": 3, "overlong": False}]},
        {"record": 1, "item_id": "item-b", "domain": "d2", "lang": "en", "group_id": "fam-1",
         "questions": [{"qid": "q0", "rid": "item-b#claim", "kind": "noul", "num_options": 2, "overlong": False},
                       {"qid": "q1", "rid": "item-b#severity", "kind": "score", "num_options": 3, "overlong": False}]},
    ]
    return records, sidecar


class AssignCleanTest(unittest.TestCase):
    def test_meta(self):
        records, sidecar = records_and_sidecar()
        clean, join = bs.assign_clean(records, sidecar)
        self.assertEqual(clean[0]["_meta"]["id"], "holdout/0")
        self.assertEqual(clean[0]["_meta"]["group_id"], "holdout/0")
        self.assertEqual(clean[1]["_meta"]["group_id"], "fam-1")
        self.assertEqual(clean[0]["_meta"]["variant"], "clean")
        self.assertEqual([len(r["questions"]) for r in join], [1, 2])
        self.assertEqual(join[1]["state_chars"], len("state two"))

    def test_no_private_content_in_meta(self):
        records, sidecar = records_and_sidecar()
        clean, join = bs.assign_clean(records, sidecar)
        meta_text = json.dumps([r["_meta"] for r in clean])
        self.assertNotIn("state one", meta_text)
        self.assertNotIn("item-a", meta_text.replace("holdout/0", ""))


class VariantsTest(unittest.TestCase):
    def test_permuted_deterministic_and_valid(self):
        records, sidecar = records_and_sidecar()
        clean, join = bs.assign_clean(records, sidecar)
        first = bs.build_permuted(clean, join, 1, seed="s")
        second = bs.build_permuted(clean, join, 1, seed="s")
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(len(first), 1)
        variant = first[0]
        self.assertEqual(variant["_meta"]["variant"], "permuted")
        self.assertEqual(variant["_meta"]["parent_id"], "holdout/0")
        self.assertEqual(variant["_meta"]["id"], "holdout/0/q0/permuted")
        original = clean[0]["questions"]["q0"]
        shuffled = variant["questions"]["q0"]
        self.assertEqual(set(shuffled["criteria"]), set(original["criteria"]))
        self.assertEqual(shuffled["label"], original["label"])

    def test_permuted_only_choice(self):
        records, sidecar = records_and_sidecar()
        clean, join = bs.assign_clean(records, sidecar)
        variants = bs.build_permuted(clean, join, 99, seed="s")
        self.assertEqual(len(variants), 1)  # 只有一道 choice

    def test_isolation_only_multi_question(self):
        records, sidecar = records_and_sidecar()
        clean, join = bs.assign_clean(records, sidecar)
        variants = bs.build_isolation(clean, join)
        self.assertEqual(len(variants), 2)
        self.assertEqual({v["_meta"]["id"] for v in variants},
                         {"holdout/1/q0/isolation", "holdout/1/q1/isolation"})
        for variant in variants:
            self.assertEqual(len(variant["questions"]), 1)
            self.assertEqual(variant["_meta"]["parent_id"], "holdout/1")

    def test_variant_join_carries_parent_metadata(self):
        records, sidecar = records_and_sidecar()
        clean, join = bs.assign_clean(records, sidecar)
        variants = bs.build_isolation(clean, join)
        rows = bs.variant_join(variants, join, kind="isolation")
        self.assertEqual(rows[0]["variant"], "isolation")
        self.assertEqual(rows[0]["item_id"], "item-b")
        self.assertEqual(rows[0]["group_id"], "fam-1")
        self.assertEqual(rows[0]["questions"][0]["kind"], "noul")


class CliTest(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            records, sidecar = records_and_sidecar()
            records_path = tmp / "records.jsonl"
            sidecar_path = tmp / "sidecar.jsonl"
            records_path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
            sidecar_path.write_text("".join(json.dumps(r) + "\n" for r in sidecar), encoding="utf-8")
            suite = tmp / "suite"
            join = tmp / "join.jsonl"
            code = bs.main(["--records", str(records_path), "--sidecar", str(sidecar_path),
                            "--out-suite", str(suite), "--out-join", str(join),
                            "--permuted-sample", "1", "--isolation"])
            self.assertEqual(code, 0)
            manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
            lines = (suite / "development.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), manifest["files"]["development.jsonl"]["records"])
            self.assertEqual(manifest["counts"]["clean_records"], 2)
            self.assertEqual(manifest["counts"]["permuted_records"], 1)
            self.assertEqual(manifest["counts"]["isolation_records"], 2)
            self.assertEqual(manifest["context"]["max_state"], 65536)
            self.assertEqual(manifest["holdout_sources"], [])
            self.assertTrue(manifest["eval_only"])
            join_lines = join.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(join_lines), len(lines))


if __name__ == "__main__":
    unittest.main()
