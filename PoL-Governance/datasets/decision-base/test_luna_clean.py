# -*- coding: utf-8 -*-
"""test_luna_clean.py —— luna_clean 的离线测试（不联网、不读密钥）。

覆盖：脏输出、markdown 围栏、嵌套 JSON、截断、截断抢救、非法选项/量程、
targets 丢弃与严格模式、重生成路径、幂等 id、账本不静默丢弃、CLI 落盘与退出码。
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import luna_clean as lc  # noqa: E402

FIXED_TIME = "2026-09-30T12:00:00+00:00"
REVISION = "luna-gen-v0.1+gpt-6-luna"


def make_options(**overrides):
    options = lc.Options(revision=REVISION, created_at=FIXED_TIME)
    for key, value in overrides.items():
        setattr(options, key, value)
    return options


def structural_cleaner(**overrides):
    """结构模式：显式给域、不带 taxonomy，避免测试被 taxonomy.py 的演进带偏。"""
    return lc.Cleaner(options=make_options(**overrides), domains=lc.FALLBACK_DOMAINS)


def run_rows(rows, cleaner=None):
    cleaner = cleaner or structural_cleaner()
    return cleaner.clean_rows([(index + 1, record) for index, record in enumerate(rows)])


def noul(key="contains_harm", prompt="这个情境包含伤害吗？"):
    return {"key": key, "kind": "noul", "prompt": prompt}


def choice(key="interaction_type", options=("love", "hate"), prompt="极性是什么？"):
    return {"key": key, "kind": "choice", "prompt": prompt,
            "options": [{"key": option, "label": option.upper()} for option in options]}


def score(key="harm_severity", low=0, high=4, labels=None, prompt="伤害有多严重？"):
    return {"key": key, "kind": "score", "prompt": prompt,
            "scale": {"min": low, "max": high,
                      "labels": labels if labels is not None else [str(i) for i in range(low, high + 1)]}}


def item_payload(state="同事在会上反复打断你，你准备指出这一点。", questions=None, targets=None,
                 **extra):
    payload = {"state": state, "lang": "zh",
               "questions": questions if questions is not None else [noul()]}
    if targets is not None:
        payload["targets"] = targets
    payload.update(extra)
    return payload


def response(payload, wrapper="items", **extra):
    body = {wrapper: payload} if wrapper else payload
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def record(text, rid="luna-test-0000", domain="pol2_axis", **extra):
    payload = {"id": rid, "domain": domain, "response": text}
    payload.update(extra)
    return payload


class ExtractionTests(unittest.TestCase):
    def test_prose_and_fence_are_tolerated(self):
        fence = chr(96) * 3
        text = ("好的，下面是结果：" + fence + "json" + chr(10) + response([item_payload()]) +
                chr(10) + fence + chr(10) + "希望有帮助。")
        result = run_rows([record(text)])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]["state"], "同事在会上反复打断你，你准备指出这一点。")

    def test_first_balanced_fragment_wins(self):
        first = response([item_payload(state="第一个情境，足够长可以入库。")])
        second = response([item_payload(state="第二个情境，应该被忽略掉。")])
        result = run_rows([record(first + chr(10) + "说明" + chr(10) + second)])
        self.assertEqual(len(result.items), 1)
        self.assertIn("第一个情境", result.items[0]["state"])

    def test_nested_json_inside_strings_and_braces(self):
        state = '他发来 {"a": [1, 2, {"b": "}"}], "c": "\"引号\""} 这段配置，让你判断风险。'
        payload = item_payload(state=state, targets={"contains_harm": {"answer": False}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]["state"], state)

    def test_array_envelope(self):
        result = run_rows([record(json.dumps([item_payload()], ensure_ascii=False),
                                  domain="risk_harm")])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]["domain"], "risk_harm")

    def test_single_key_wrapper_is_unwrapped(self):
        text = json.dumps({"item": item_payload()}, ensure_ascii=False)
        result = run_rows([record(text)])
        self.assertEqual(len(result.items), 1)

    def test_bare_item_is_accepted(self):
        result = run_rows([record(json.dumps(item_payload(), ensure_ascii=False))])
        self.assertEqual(len(result.items), 1)

    def test_no_json_found(self):
        result = run_rows([record("我觉得这个问题需要再看一下，没有 JSON。")])
        self.assertEqual(result.items, [])
        self.assertEqual(result.rejects[0]["reason_code"], "no_json_found")
        self.assertEqual(result.stats["rows_without_output"], 0)

    def test_bad_json_body(self):
        result = run_rows([record('前言 {"state": 未加引号} 后记')])
        self.assertEqual(result.rejects[0]["reason_code"], "bad_json")

    def test_unbalanced_brackets(self):
        result = run_rows([record('{"items": [{"state": "x"}]')])
        self.assertIn(result.rejects[0]["reason_code"], ("unterminated_json", "unbalanced_json"))


class TruncationTests(unittest.TestCase):
    @staticmethod
    def truncated_text():
        full = response([item_payload(questions=[noul()],
                                      targets={"contains_harm": {"answer": True}})])
        return full[:len(full) - 12]

    def test_truncated_is_rejected_with_reason(self):
        result = run_rows([record(self.truncated_text(), finish_reason="length")])
        self.assertEqual(result.items, [])
        self.assertEqual(result.rejects[0]["reason_code"], "unterminated_json")
        self.assertIn("finish_reason=length", result.rejects[0]["reason"])
        self.assertTrue(result.rejects[0]["response_excerpt"])

    def test_truncated_without_finish_reason_still_rejected(self):
        result = run_rows([record(self.truncated_text())])
        self.assertEqual(result.rejects[0]["reason_code"], "unterminated_json")

    def test_salvage_recovers_complete_items(self):
        result = run_rows([record(self.truncated_text(), finish_reason="length")],
                          structural_cleaner(salvage_truncated=True))
        self.assertEqual(len(result.items), 1)
        self.assertIn("salvaged_truncated", result.items[0]["meta"]["quality_flags"])
        self.assertEqual(result.stats["salvaged_items"], 1)

    def test_salvage_truncated_inside_string(self):
        text = ('{"items": [{"state": "楼道堆物影响通行，你打算先沟通", "lang": "zh", "questions": ['
                '{"key": "contains_harm", "kind": "noul", "prompt": "有伤害吗"}, {"key": "harm')
        result = run_rows([record(text)], structural_cleaner(salvage_truncated=True))
        self.assertEqual(len(result.items), 1)
        self.assertEqual([q["key"] for q in result.items[0]["questions"]], ["contains_harm"])


class QuestionValidationTests(unittest.TestCase):
    def test_noul_options_defaulted(self):
        question = {"key": "contains_harm", "kind": "noul", "prompt": "有伤害吗"}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual([option["key"] for option in result.items[0]["questions"][0]["options"]],
                         ["yes", "no"])
        self.assertIn("noul_options_defaulted", result.items[0]["meta"]["quality_flags"])

    def test_noul_options_wrong_keys_rejected(self):
        question = {"key": "contains_harm", "kind": "noul", "prompt": "有伤害吗",
                    "options": [{"key": "true", "label": "是"}, {"key": "false", "label": "否"}]}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual(result.items, [])
        self.assertEqual(result.rejects[0]["reason_code"], "noul_options_invalid")

    def test_noul_options_reordered_normalized(self):
        question = {"key": "contains_harm", "kind": "noul", "prompt": "有伤害吗",
                    "options": [{"key": "no", "label": "否"}, {"key": "yes", "label": "是"}]}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual([option["key"] for option in result.items[0]["questions"][0]["options"]],
                         ["yes", "no"])
        self.assertIn("noul_options_reordered", result.items[0]["meta"]["quality_flags"])

    def test_choice_too_few_options(self):
        result = run_rows([record(response([item_payload(questions=[choice(options=("a",))])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "choice_options_count")

    def test_choice_too_many_options(self):
        options = tuple("o%d" % index for index in range(17))
        result = run_rows([record(response([item_payload(questions=[choice(options=options)])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "choice_options_count")

    def test_choice_duplicate_keys(self):
        question = choice()
        question["options"][1]["key"] = "love"
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "choice_option_key_duplicate")

    def test_choice_string_options_normalized(self):
        question = {"key": "interaction_type", "kind": "choice", "prompt": "极性？",
                    "options": ["love", "hate", "neutral"]}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual([option["key"] for option in result.items[0]["questions"][0]["options"]],
                         ["love", "hate", "neutral"])
        self.assertIn("choice_options_normalized", result.items[0]["meta"]["quality_flags"])

    def test_score_bounds_invalid(self):
        result = run_rows([record(response([item_payload(questions=[score(low=3, high=1)])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "score_bounds_invalid")

    def test_score_labels_mismatch(self):
        result = run_rows([record(response([item_payload(questions=[score(labels=["低", "高"])])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "score_labels_mismatch")

    def test_score_labels_defaulted(self):
        question = {"key": "harm_severity", "kind": "score", "prompt": "严重度",
                    "scale": {"min": 0, "max": 2}}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual(result.items[0]["questions"][0]["scale"]["labels"], ["0", "1", "2"])
        self.assertIn("scale_labels_defaulted", result.items[0]["meta"]["quality_flags"])

    def test_score_scale_from_list(self):
        question = {"key": "harm_severity", "kind": "score", "prompt": "严重度",
                    "scale": [0, 1, 2]}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual(result.items[0]["questions"][0]["scale"]["min"], 0)
        self.assertIn("scale_normalized", result.items[0]["meta"]["quality_flags"])

    def test_kind_invalid(self):
        question = {"key": "contains_harm", "kind": "yesno", "prompt": "有伤害吗"}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "kind_invalid")

    def test_duplicate_question_keys(self):
        questions = [noul("contains_harm"), noul("contains_harm", prompt="再问一次")]
        result = run_rows([record(response([item_payload(questions=questions)]))])
        self.assertEqual(result.rejects[0]["reason_code"], "question_key_duplicate")

    def test_questions_missing_and_too_many(self):
        result = run_rows([record(response([item_payload(questions=[])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "questions_missing")
        many = [noul("k%d" % index) for index in range(13)]
        result = run_rows([record(response([item_payload(questions=many)]))])
        self.assertEqual(result.rejects[0]["reason_code"], "questions_too_many")

    def test_prompt_missing(self):
        question = {"key": "contains_harm", "kind": "noul", "prompt": "  "}
        result = run_rows([record(response([item_payload(questions=[question])]))])
        self.assertEqual(result.rejects[0]["reason_code"], "prompt_missing")


class TargetTests(unittest.TestCase):
    def test_bool_answer_normalized(self):
        payload = item_payload(targets={"contains_harm": {"answer": False}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.items[0]["targets"]["contains_harm"]["answer"], "no")
        self.assertIn("answer_bool_normalized", result.items[0]["meta"]["quality_flags"])

    def test_answer_by_label(self):
        payload = item_payload(questions=[choice()],
                               targets={"interaction_type": {"answer": "LOVE"}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.items[0]["targets"]["interaction_type"]["answer"], "love")

    def test_score_answer_string_to_int(self):
        payload = item_payload(questions=[score()], targets={"harm_severity": {"answer": "3"}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.items[0]["targets"]["harm_severity"]["answer"], 3)
        self.assertIn("answer_int_normalized", result.items[0]["meta"]["quality_flags"])

    def test_answer_from_probs_when_missing(self):
        payload = item_payload(targets={"contains_harm": {"probs": {"yes": 0.2, "no": 0.8}}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.items[0]["targets"]["contains_harm"]["answer"], "no")
        self.assertIn("answer_from_probs", result.items[0]["meta"]["quality_flags"])

    def test_probs_renormalized(self):
        payload = item_payload(targets={"contains_harm": {"probs": {"yes": 0.5, "no": 0.49}}})
        result = run_rows([record(response([payload]))])
        probs = result.items[0]["targets"]["contains_harm"]["probs"]
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=9)
        self.assertIn("probs_renormalized", result.items[0]["meta"]["quality_flags"])

    def test_probs_far_from_one_dropped_but_answer_kept(self):
        payload = item_payload(targets={"contains_harm": {"answer": "no",
                                                          "probs": {"yes": 0.2, "no": 0.2}}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]["targets"]["contains_harm"]["answer"], "no")
        self.assertNotIn("probs", result.items[0]["targets"]["contains_harm"])
        self.assertIn("probs_dropped_probs_sum_invalid", result.items[0]["meta"]["quality_flags"])

    def test_unknown_target_key_is_warning_not_reject(self):
        payload = item_payload(targets={"not_a_key": {"answer": "yes"},
                                        "contains_harm": {"answer": "no"}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(list(result.items[0]["targets"]), ["contains_harm"])
        warning = [row for row in result.rejects if row["severity"] == "warning"]
        self.assertEqual(len(warning), 1)
        self.assertEqual(warning[0]["reason_code"], "target_unknown_key")
        self.assertTrue(warning[0]["item_kept"])
        self.assertEqual(result.stats["warnings"], 1)

    def test_invalid_answer_dropped_with_warning(self):
        payload = item_payload(targets={"contains_harm": {"answer": "maybe"}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(len(result.items), 1)
        self.assertNotIn("targets", result.items[0])
        self.assertEqual(result.stats["warnings_by_code"]["target_dropped_answer_invalid"], 1)

    def test_strict_targets_rejects_whole_item(self):
        payload = item_payload(targets={"contains_harm": {"answer": "maybe"}})
        result = run_rows([record(response([payload]))], structural_cleaner(strict_targets=True))
        self.assertEqual(result.items, [])
        self.assertEqual(result.rejects[0]["reason_code"], "answer_invalid")

    def test_score_answer_out_of_range_dropped(self):
        payload = item_payload(questions=[score()], targets={"harm_severity": {"answer": 9}})
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.stats["warnings_by_code"]["target_dropped_answer_invalid"], 1)

    def test_targets_as_list(self):
        payload = item_payload(targets=[{"key": "contains_harm", "answer": "yes"}])
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.items[0]["targets"]["contains_harm"]["answer"], "yes")

    def test_scalar_target_normalized(self):
        payload = item_payload(targets={"contains_harm": "yes"})
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.items[0]["targets"]["contains_harm"]["answer"], "yes")
        self.assertIn("target_scalar_normalized", result.items[0]["meta"]["quality_flags"])

    def test_no_targets_flag_drops_targets(self):
        payload = item_payload(targets={"contains_harm": {"answer": "no"}})
        result = run_rows([record(response([payload]))], structural_cleaner(allow_targets=False))
        self.assertNotIn("targets", result.items[0])


class ItemLevelTests(unittest.TestCase):
    def test_missing_state(self):
        payload = item_payload()
        del payload["state"]
        result = run_rows([record(response([payload]))])
        self.assertEqual(result.rejects[0]["reason_code"], "state_missing")

    def test_state_from_request_wins(self):
        payload = item_payload(state="模型编的情境")
        result = run_rows([record(response([payload]), state="请求里固定的情境，足够长了。")])
        self.assertEqual(result.items[0]["state"], "请求里固定的情境，足够长了。")
        self.assertIn("state_from_request", result.items[0]["meta"]["quality_flags"])

    def test_unknown_domain(self):
        result = run_rows([record(response([item_payload()]), domain="unknown_domain")])
        self.assertEqual(result.rejects[0]["reason_code"], "domain_unknown")

    def test_default_domain_used_when_missing(self):
        row = {"id": "luna-x", "response": response([item_payload()])}
        result = run_rows([row], structural_cleaner(default_domain="risk_harm"))
        self.assertEqual(result.items[0]["domain"], "risk_harm")

    def test_domain_missing_without_default(self):
        row = {"id": "luna-x", "response": response([item_payload()])}
        result = run_rows([row])
        self.assertEqual(result.rejects[0]["reason_code"], "domain_missing")

    def test_invalid_lang(self):
        result = run_rows([record(response([item_payload()]), lang="zh CN!")])
        self.assertEqual(result.rejects[0]["reason_code"], "lang_invalid")

    def test_source_and_meta_complete(self):
        result = run_rows([record(response([item_payload()]), domain="risk_harm")])
        item = result.items[0]
        for key in lc.SOURCE_KEYS:
            self.assertTrue(item["source"].get(key), key)
        for key in ("converter", "converter_version", "created_at", "quality_flags"):
            self.assertIn(key, item["meta"])
        self.assertEqual(item["meta"]["created_at"], FIXED_TIME)
        for flag in ("synthetic", "closed_teacher", "not_ground_truth", "license_unverified"):
            self.assertIn(flag, item["meta"]["quality_flags"])

    def test_id_is_deterministic_and_well_formed(self):
        text = response([item_payload()])
        first = run_rows([record(text)]).items[0]["id"]
        second = run_rows([record(text)]).items[0]["id"]
        self.assertEqual(first, second)
        self.assertRegex(first, "^db-luna-[0-9a-f]{8}$")

    def test_different_rows_get_different_ids(self):
        text = response([item_payload()])
        result = run_rows([record(text, rid="luna-a"), record(text, rid="luna-b")])
        self.assertEqual(len(result.items), 2)
        self.assertNotEqual(result.items[0]["id"], result.items[1]["id"])

    def test_duplicate_input_row_is_rejected(self):
        text = response([item_payload()])
        result = run_rows([record(text, rid="luna-a"), record(text, rid="luna-a")])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.rejects[0]["reason_code"], "duplicate_item_id")

    def test_multi_item_envelope_partial_failure(self):
        good = item_payload()
        bad = item_payload(questions=[{"key": "contains_harm", "kind": "noul", "prompt": ""}])
        result = run_rows([record(response([good, bad]))])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(len(result.rejects), 1)
        self.assertEqual(result.stats["multi_item_rows"], 1)
        self.assertNotEqual(result.items[0]["id"], result.rejects[0]["id"])

    def test_item_cap_is_not_silent(self):
        payloads = [item_payload(state="情境编号 %d，长度足够可以进入数据集。" % index)
                    for index in range(9)]
        result = run_rows([record(response(payloads))])
        self.assertEqual(len(result.items), lc.MAX_ITEMS_PER_RESPONSE)
        self.assertEqual(result.rejects[0]["reason_code"], "items_truncated")

    def test_missing_response_with_prompt_only(self):
        result = run_rows([{"id": "luna-x", "domain": "pol2_axis", "prompt": "生成一个情境"}])
        self.assertEqual(result.rejects[0]["reason_code"], "missing_response")

    def test_input_json_invalid_is_rejected_not_crashed(self):
        result = run_rows([{"__parse_error__": "Expecting value"}])
        self.assertEqual(result.rejects[0]["reason_code"], "input_json_invalid")

    def test_accounting_invariant(self):
        rows = [record(response([item_payload()]), rid="luna-%d" % index,
                       domain="pol2_axis" if index % 2 else "risk_harm")
                for index in range(4)]
        rows.append(record("没有 JSON 的一段话", rid="luna-bad"))
        result = run_rows(rows)
        self.assertEqual(result.stats["rows_without_output"], 0)
        self.assertEqual(result.stats["rows_read"], 5)
        hard = [row for row in result.rejects if row["severity"] == "reject"]
        self.assertEqual(len(result.items) + len(hard), 5)


class RepairTests(unittest.TestCase):
    def test_repair_success_marks_item(self):
        calls = []

        def regenerate(rec, attempt, problems):
            calls.append((attempt, [problem.code for problem in problems]))
            return response([item_payload(targets={"contains_harm": {"answer": "no"}})])

        cleaner = structural_cleaner(max_repairs=1)
        cleaner.regenerate = regenerate
        broken = response([item_payload(questions=[{"key": "contains_harm", "kind": "noul",
                                                    "prompt": ""}])])
        result = run_rows([record(broken)], cleaner)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(calls[0][1], ["prompt_missing"])
        self.assertEqual(result.stats["repairs_used"], 1)
        self.assertEqual(result.stats["repaired_items"], 1)
        self.assertIn("repaired_1x", result.items[0]["meta"]["quality_flags"])

    def test_repair_exhausted_then_reject(self):
        calls = []

        def regenerate(rec, attempt, problems):
            calls.append(attempt)
            return response([item_payload(questions=[{"key": "contains_harm", "kind": "noul",
                                                      "prompt": ""}])])

        cleaner = structural_cleaner(max_repairs=2)
        cleaner.regenerate = regenerate
        broken = response([item_payload(questions=[{"key": "contains_harm", "kind": "noul",
                                                    "prompt": ""}])])
        result = run_rows([record(broken)], cleaner)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(result.items, [])
        self.assertEqual(result.rejects[0]["repairs_attempted"], 2)

    def test_repair_absent_falls_back_to_single_attempt(self):
        broken = response([item_payload(questions=[{"key": "contains_harm", "kind": "noul",
                                                    "prompt": ""}])])
        result = run_rows([record(broken)])
        self.assertEqual(result.rejects[0]["reason_code"], "prompt_missing")

    def test_repair_failure_does_not_crash(self):
        def regenerate(rec, attempt, problems):
            raise RuntimeError("boom")

        cleaner = structural_cleaner(max_repairs=1)
        cleaner.regenerate = regenerate
        broken = response([item_payload(questions=[{"key": "contains_harm", "kind": "noul",
                                                    "prompt": ""}])])
        result = run_rows([record(broken)], cleaner)
        self.assertEqual(len(result.rejects), 1)
        self.assertIn("repair_call_failed", result.rejects[0]["codes"])


class TaxonomyAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.domains, cls.source = lc.open_taxonomy()

    def setUp(self):
        if self.module is None:
            self.skipTest("taxonomy.py 不可用")

    def test_taxonomy_fields_and_validators_exist(self):
        gap = {"item_errors", "validate_target", "resolve_key", "key_spec", "build_question",
               "DOMAINS", "QUESTION_KEYS", "QUESTION_KEY_ALIASES"} - set(dir(self.module))
        self.assertEqual(gap, set(), "taxonomy.py 缺少：%s" % sorted(gap))

    def test_alias_key_resolved_and_options_canonical(self):
        payload = item_payload(
            questions=[{"key": "interaction_type", "kind": "choice", "prompt": "极性？",
                        "options": [{"key": "love", "label": "爱"}]}],
            targets={"interaction_type": {"answer": "neutral",
                                          "probs": {"love": 0.2, "hate": 0.1,
                                                    "neither": 0.6, "unclear": 0.1}}})
        row = {"id": "luna-pol2_axis-0000", "domain": "pol2_axis", "lang": "zh",
               "response": response([payload])}
        result = run_rows([row], lc.Cleaner(options=make_options()))
        self.assertEqual(len(result.items), 1, result.rejects)
        item = result.items[0]
        self.assertEqual(item["questions"][0]["key"], "interaction_polarity")
        self.assertEqual({option["key"] for option in item["questions"][0]["options"]},
                         {"love", "hate", "neither", "unclear"})
        self.assertEqual(item["targets"]["interaction_polarity"]["answer"], "neither")
        self.assertEqual(self.module.item_errors(item), [])

    def test_unknown_key_rejected_when_taxonomy_present(self):
        row = {"id": "luna-risk_harm-0000", "domain": "risk_harm",
               "response": response([item_payload(questions=[noul("made_up_key")])])}
        result = run_rows([row], lc.Cleaner(options=make_options()))
        self.assertEqual(result.items, [])
        self.assertEqual(result.rejects[0]["reason_code"], "question_key_unknown")

    def test_kind_mismatch_rejected(self):
        question = {"key": "contains_harm", "kind": "choice", "prompt": "有伤害吗",
                    "options": [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}]}
        row = {"id": "luna-risk_harm-0000", "domain": "risk_harm",
               "response": response([item_payload(questions=[question])])}
        result = run_rows([row], lc.Cleaner(options=make_options()))
        self.assertEqual(result.items, [])
        self.assertIn(result.rejects[0]["reason_code"],
                      ("taxonomy_question_invalid", "kind_invalid", "kind_mismatch"))

    def test_taxonomy_gate_can_be_disabled(self):
        row = {"id": "luna-risk_harm-0000", "domain": "risk_harm",
               "response": response([item_payload(questions=[noul("made_up_key")])])}
        cleaner = lc.Cleaner(options=make_options(taxonomy_check=False))
        result = run_rows([row], cleaner)
        self.assertEqual(len(result.items), 1)
        self.assertFalse(result.stats["taxonomy_check"])

    def test_generated_item_passes_taxonomy_item_errors(self):
        payload = item_payload(questions=self.module.build_questions("risk_harm"),
                               targets={"contains_harm": {"answer": False,
                                                          "probs": {"yes": 0.1, "no": 0.9}}})
        row = {"id": "luna-risk_harm-0000", "domain": "risk_harm", "lang": "zh",
               "response": response([payload])}
        result = run_rows([row], lc.Cleaner(options=make_options()))
        self.assertEqual(len(result.items), 1, result.rejects)
        self.assertEqual(self.module.item_errors(result.items[0]), [])
        self.assertTrue(self.module.id_is_canonical(result.items[0]["id"]))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.input = self.dir / "raw.jsonl"
        self.items = self.dir / "items.jsonl"
        self.rejects = self.dir / "rejects.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def write_input(self, rows):
        text = chr(10).join(json.dumps(row, ensure_ascii=False) for row in rows) + chr(10)
        self.input.write_text(text, encoding="utf-8")

    def run_cli(self, extra=()):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = lc.main(["--input", str(self.input), "--items", str(self.items),
                            "--rejects", str(self.rejects), "--created-at", FIXED_TIME,
                            "--revision", REVISION, *extra])
        return code, buffer.getvalue()

    @staticmethod
    def read_jsonl(path):
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def test_cli_writes_outputs_and_summary(self):
        self.write_input([record(response([item_payload()]), rid="luna-a", domain="risk_harm")])
        code, out = self.run_cli(["--domain", "risk_harm"])
        self.assertEqual(code, 0)
        summary = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(summary["items"], 1)
        self.assertEqual(summary["rows_without_output"], 0)
        self.assertEqual(len(self.read_jsonl(self.items)), 1)
        self.assertEqual(self.read_jsonl(self.rejects), [])

    def test_cli_fail_on_reject(self):
        self.write_input([record("没有 JSON", rid="luna-a", domain="risk_harm")])
        code, _ = self.run_cli(["--domain", "risk_harm"])
        self.assertEqual(code, 0)
        code, _ = self.run_cli(["--domain", "risk_harm", "--fail-on-reject"])
        self.assertEqual(code, 1)
        self.assertEqual(self.read_jsonl(self.rejects)[0]["reason_code"], "no_json_found")

    def test_cli_limit(self):
        self.write_input([record(response([item_payload()]), rid="luna-%d" % index,
                                 domain="risk_harm") for index in range(3)])
        code, out = self.run_cli(["--domain", "risk_harm", "--limit", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.strip().splitlines()[-1])["rows_read"], 1)

    def test_cli_repair_needs_source(self):
        self.write_input([record(response([item_payload()]), domain="risk_harm")])
        with self.assertRaises(SystemExit) as caught:
            self.run_cli(["--repair", "1"])
        self.assertEqual(caught.exception.code, 2)

    def test_cli_repair_with_fixture(self):
        broken = response([item_payload(questions=[{"key": "contains_harm", "kind": "noul",
                                                    "prompt": ""}])])
        self.write_input([{"id": "luna-a", "domain": "risk_harm", "response": broken}])
        repairs = self.dir / "repairs.jsonl"
        repairs.write_text(json.dumps({"id": "luna-a", "attempt": 1,
                                       "response": response([item_payload()])},
                                      ensure_ascii=False) + chr(10), encoding="utf-8")
        code, out = self.run_cli(["--repair", "1", "--repair-fixture", str(repairs)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.strip().splitlines()[-1])["repaired_items"], 1)

    def test_cli_bad_line_and_no_targets(self):
        self.input.write_text("这不是 JSON" + chr(10), encoding="utf-8")
        code, out = self.run_cli(["--domain", "risk_harm", "--no-targets"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.strip().splitlines()[-1])["rejects_by_code"],
                         {"input_json_invalid": 1})


class FallbackTests(unittest.TestCase):
    def test_missing_taxonomy_falls_back_to_readme_domains(self):
        module, domains, source = lc.open_taxonomy(Path("does-not-exist") / "taxonomy.py")
        self.assertIsNone(module)
        self.assertEqual(tuple(domains), lc.FALLBACK_DOMAINS)
        self.assertIn("readme-fallback", source)

    def test_close_open_helpers(self):
        self.assertEqual(lc._close_open('{"a": [1, 2'), '{"a": [1, 2]}')
        self.assertEqual(lc._close_open('{"a": "x'), '{"a": "x"}')
        self.assertEqual(lc.salvage_json('{"a": }'), (None, None))

    def test_derive_id_matches_contract_shape(self):
        item_id = lc.derive_id("rev", "row-1")
        self.assertRegex(item_id, "^db-luna-[0-9a-f]{8}$")
        self.assertEqual(item_id, lc.derive_id("rev", "row-1"))
        self.assertNotEqual(item_id, lc.derive_id("rev", "row-2"))


if __name__ == "__main__":
    unittest.main()
