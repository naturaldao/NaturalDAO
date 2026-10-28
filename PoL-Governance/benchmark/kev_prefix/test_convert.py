"""benchmark/kev_prefix/convert.py 的单元测试（纯合成样例，不含任何私有保留集内容）。

运行：python -m unittest discover -s benchmark/kev_prefix -p "test_*.py" -q
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "convert.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conv = load_module("kev_prefix_convert", MODULE_PATH)


def item(item_id="syn-0001", state="The sky is blue on a clear day.", questions=None, targets=None,
         lang="en", domain="knowledge_reasoning", meta=None):
    return {"id": item_id, "lang": lang, "domain": domain, "state": state,
            "questions": questions or [], "targets": targets or {}, "meta": meta or {},
            "source": {}}


def choice_q(key="weather", prompt="Which statement is true?", labels=("The sky is blue", "The sky is green", "The sky is red")):
    return {"key": key, "kind": "choice", "prompt": prompt,
            "origin": "source", "source_key": key,
            "options": [{"key": f"k{i}", "label": label} for i, label in enumerate(labels)]}


def noul_q(key, labels, option_keys, prompt="Is the claim supported?"):
    return {"key": key, "kind": "noul", "prompt": prompt, "origin": "source", "source_key": key,
            "options": [{"key": k, "label": l} for k, l in zip(option_keys, labels)]}


def score_q(key="severity", labels=("none", "mild", "severe"), min_=0, max_=2, prompt="How severe is it?"):
    return {"key": key, "kind": "score", "prompt": prompt, "origin": "source", "source_key": key,
            "scale": {"min": min_, "max": max_, "labels": list(labels)}}


class ChoiceMappingTest(unittest.TestCase):
    def test_choice_neutral_keys_order_and_label(self):
        it = item(questions=[choice_q()], targets={"weather": {"answer": "k1"}})
        records, sidecar, stats = conv.convert_items([it])
        self.assertEqual(len(records), 1)
        q = records[0]["questions"]["q0"]
        self.assertEqual(q["type"], "choice")
        self.assertEqual(q["src"], "choice")
        self.assertEqual(list(q["criteria"]), ["opt_1", "opt_2", "opt_3"])
        self.assertEqual(q["criteria"]["opt_2"], "The sky is green")
        self.assertEqual(q["label"], "opt_2")
        side = sidecar[0]["questions"][0]
        self.assertEqual(side["kind"], "choice")
        self.assertEqual(side["num_options"], 3)
        self.assertFalse(side["overlong"])
        self.assertEqual(side["rid"], "syn-0001#q0")
        self.assertEqual(stats["questions_primary"], 1)

    def test_choice_answer_by_label_text(self):
        it = item(questions=[choice_q()], targets={"weather": {"answer": "The sky is red"}})
        records, _, _ = conv.convert_items([it])
        self.assertEqual(records[0]["questions"]["q0"]["label"], "opt_3")

    def test_choice_answer_missing_skips(self):
        it = item(questions=[choice_q()], targets={"weather": {"answer": "not an option"}})
        records, sidecar, stats = conv.convert_items([it])
        self.assertEqual(records, [])
        self.assertEqual(sidecar, [])
        self.assertEqual(stats["skipped"]["record_no_questions"], 1)
        self.assertEqual(stats["skipped_by_kind"]["choice:answer_not_in_options"], 1)


class NoulMappingTest(unittest.TestCase):
    def _convert(self, labels, keys, answer):
        it = item(questions=[noul_q("claim", labels, keys)], targets={"claim": {"answer": answer}})
        return conv.convert_items([it])

    def test_false_true_keys(self):
        records, sidecar, _ = self._convert(["No", "Yes"], ["false", "true"], "true")
        q = records[0]["questions"]["q0"]
        self.assertEqual(q["src"], "noul")
        self.assertIs(q["label"], True)
        self.assertEqual(q["criteria"], {"false": "No", "true": "Yes"})
        self.assertEqual(sidecar[0]["questions"][0]["num_options"], 2)

    def test_false_true_keys_reversed_order(self):
        records, _, _ = self._convert(["Yes", "No"], ["true", "false"], "false")
        q = records[0]["questions"]["q0"]
        self.assertIs(q["label"], False)
        self.assertEqual(q["criteria"], {"false": "No", "true": "Yes"})

    def test_no_yes_keys(self):
        records, _, _ = self._convert(["No", "Yes"], ["no", "yes"], "yes")
        self.assertIs(records[0]["questions"]["q0"]["label"], True)

    def test_long_prefix_keys(self):
        labels = ["no_the_post_is_allowed", "yes_the_post_is_disallowed"]
        records, _, _ = self._convert(labels, list(labels), "yes_the_post_is_disallowed")
        q = records[0]["questions"]["q0"]
        self.assertIs(q["label"], True)
        self.assertEqual(q["criteria"]["true"], "yes_the_post_is_disallowed")

    def test_ambiguous_true_side_skips(self):
        records, _, stats = self._convert(["alpha", "beta"], ["alpha", "beta"], "beta")
        self.assertEqual(records, [])
        self.assertEqual(stats["skipped_by_kind"]["noul:noul_ambiguous"], 1)


class ScoreMappingTest(unittest.TestCase):
    def test_score_labels_and_offset(self):
        it = item(questions=[score_q(labels=("low", "medium", "high"))],
                  targets={"severity": {"answer": "2"}})
        records, sidecar, _ = conv.convert_items([it])
        q = records[0]["questions"]["q0"]
        self.assertEqual(q["type"], "score")
        self.assertEqual(q["src"], "score")
        self.assertEqual(q["criteria"], ["low", "medium", "high"])
        self.assertEqual(q["label"], 2)
        self.assertEqual(sidecar[0]["questions"][0]["num_options"], 3)

    def test_score_nonzero_min(self):
        it = item(questions=[score_q(labels=("one", "two", "three"), min_=1, max_=3)],
                  targets={"severity": {"answer": "1"}})
        records, _, _ = conv.convert_items([it])
        self.assertEqual(records[0]["questions"]["q0"]["label"], 0)

    def test_score_missing_labels_fallback(self):
        q = score_q()
        q["scale"] = {"min": 0, "max": 2}
        it = item(questions=[q], targets={"severity": {"answer": "1"}})
        records, _, stats = conv.convert_items([it])
        self.assertEqual(records[0]["questions"]["q0"]["criteria"], ["0", "1", "2"])
        self.assertEqual(stats["score_labels_fallback"], 1)

    def test_score_out_of_range_skips(self):
        it = item(questions=[score_q()], targets={"severity": {"answer": "9"}})
        records, _, stats = conv.convert_items([it])
        self.assertEqual(records, [])
        self.assertEqual(stats["skipped_by_kind"]["score:answer_out_of_range"], 1)


class FlagAndRecordTest(unittest.TestCase):
    def test_overlong_is_flagged_not_dropped(self):
        it = item(state="x" * 4000, questions=[choice_q()], targets={"weather": {"answer": "k0"}})
        records, sidecar, stats = conv.convert_items([it], max_chars=4000)
        self.assertEqual(len(records), 1)
        self.assertTrue(sidecar[0]["questions"][0]["overlong"])
        self.assertEqual(stats["questions_overlong_flagged"], 1)
        self.assertEqual(stats["questions_primary"], 0)

    def test_partial_skip_keeps_other_questions(self):
        it = item(questions=[choice_q("weather"), choice_q("weather2")],
                  targets={"weather": {"answer": "k0"}, "weather2": {"answer": "nope"}})
        records, sidecar, stats = conv.convert_items([it])
        self.assertEqual(len(records), 1)
        self.assertEqual(list(records[0]["questions"]), ["q0"])
        self.assertEqual(sidecar[0]["questions"][0]["qid"], "q0")
        self.assertEqual(stats["questions_in"], 2)
        self.assertEqual(stats["questions_out"], 1)

    def test_record_index_and_group_id(self):
        items = [item("a", questions=[choice_q()], targets={"weather": {"answer": "k0"}}, meta={"group_id": "g1"}),
                 item("b", questions=[choice_q()], targets={"weather": {"answer": "k0"}})]
        records, sidecar, _ = conv.convert_items(items)
        self.assertEqual([r["record"] for r in sidecar], [0, 1])
        self.assertEqual(sidecar[0]["item_id"], "a")
        self.assertEqual(sidecar[0]["group_id"], "g1")
        self.assertIsNone(sidecar[1]["group_id"])
        self.assertNotIn("state", sidecar[0])
        self.assertNotIn("prompt", json.dumps(sidecar))

    def test_limit(self):
        items = [item(f"it{i}", questions=[choice_q()], targets={"weather": {"answer": "k0"}}) for i in range(5)]
        records, _, stats = conv.convert_items(items, limit=3)
        self.assertEqual(len(records), 3)
        self.assertEqual(stats["records_out"], 3)


class GuardTest(unittest.TestCase):
    def test_refuses_inside_repo(self):
        with self.assertRaises(SystemExit):
            conv.assert_outside_repo(conv.ROOT / "benchmark" / "kev_prefix" / "x.jsonl", False, "--out-records")

    def test_allows_outside_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            conv.assert_outside_repo(Path(tmp) / "x.jsonl", False, "--out-records")


class CliTest(unittest.TestCase):
    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "items.jsonl"
            it = item(questions=[choice_q(), score_q()],
                      targets={"weather": {"answer": "k0"}, "severity": {"answer": "1"}})
            src.write_text(json.dumps(it) + "\n", encoding="utf-8")
            records = tmp / "records.jsonl"
            sidecar = tmp / "sidecar.jsonl"
            manifest = tmp / "manifest.json"
            code = conv.main(["--items", str(src), "--out-records", str(records),
                              "--sidecar", str(sidecar), "--manifest", str(manifest)])
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in records.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(set(rows[0]["questions"]), {"q0", "q1"})
            meta = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(meta["questions_out"], 2)
            self.assertEqual(meta["questions_primary"], 2)
            self.assertEqual(meta["records_out"], 1)


if __name__ == "__main__":
    unittest.main()