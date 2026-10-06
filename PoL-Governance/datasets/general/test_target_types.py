"""target_types.py / filter_targets.py 自检：旁挂文件覆盖全量、分布与报告 §6.3 一致、路由可复算。

放在 datasets/general/ 根目录（与其余 test_*.py 一致），tools/check.py 的 unittest discovery 能收进来。
旁挂文件优先读明文 data/target-types.jsonl；明文被 .gitignore 第 13 行挡住（属派生大文件，只提交 .gz），
所以干净检出上退到 data/target-types.jsonl.gz。
"""

import gzip
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import filter_targets as ft  # noqa: E402
import target_types as tt  # noqa: E402

SIDECAR_PLAIN = HERE / "data" / "target-types.jsonl"
SIDECAR_GZ = HERE / "data" / "target-types.jsonl.gz"
CORPUS = HERE / "data" / "items.final.jsonl"

#: 报告 §6.3 的四个 target_type 基准
EXPECTED_TARGET_TYPE = {"soft_distribution": 15_919, "answer_only": 8_417,
                        "hard_label": 5_488, "uninformative_uniform": 1_962}
#: 报告 §6.3 的逐规则基准（R12/R13 是覆盖规则，单独计）
EXPECTED_RULE_HITS = {"R1": 4_009, "R2": 1_479, "R3": 7_872, "R4": 545, "R5": 432,
                      "R6": 3_714, "R7": 4_479, "R8": 757, "R9": 5_378, "R10": 1_621,
                      "R11": 1_500}
EXPECTED_SHAPE_OVERRIDE = {"R12": 109, "R13": 232}
#: 报告 §0.2 的形态桶
EXPECTED_SHAPE = {"answer_only": 8_417, "onehot_fabricated": 5_488, "onehot_native": 8_631,
                  "soft": 7_286, "uniform_all_candidates": 1_730, "tie_subset": 234}
#: 分布语义全量分布。none = 5,488（我们造的单点，报告 §4.1）+ 545（procedural 的 answer_only，R4：
#: 答案由规则精确算出，语义就是 none 而不是 unknown）。unknown 只有 deepexi 的 7,872。
EXPECTED_SEMANTICS = {"none": 6_033, "unknown": 7_872, "model_logits": 8_499, "rule_counter": 9_382}
#: 报告 §6.2 的字段值域
FIELD_DOMAINS = {
    "target_type": {"hard_label", "soft_distribution", "uninformative_uniform", "answer_only"},
    "distribution_semantics": {"vote_share", "model_logits", "temperature_softmax",
                               "self_confidence", "rule_counter", "human_annotation", "unknown", "none"},
    "target_type_basis": {"source", "shape"},
    "semantics_confidence": {"high", "medium", "low", "unknown"},
    "calibration_role": {"reference_probability", "soft_target_only", "label_only"},
    "label_trust": {"rule_exact", "teacher_argmax", "behavioral", "unknown"},
    "shape_class": {"answer_only", "onehot_fabricated", "onehot_native", "soft",
                    "uniform_all_candidates", "tie_subset"},
    "training_route": {"drop", "classification", "distillation"},
}
REQUIRED_FIELDS = tuple(FIELD_DOMAINS) + ("provenance_ref", "mechanism_unknown", "rule_id",
                                          "shape_override", "item_id", "question_key")


def load_sidecar():
    """读旁挂文件：优先明文，干净检出上退到 .gz。"""
    path = SIDECAR_PLAIN if SIDECAR_PLAIN.is_file() else SIDECAR_GZ
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class SidecarTest(unittest.TestCase):
    """旁挂文件本身的自洽性（不需要 82MB 语料，干净检出也能跑）。"""

    @classmethod
    def setUpClass(cls):
        if not (SIDECAR_PLAIN.is_file() or SIDECAR_GZ.is_file()):
            raise unittest.SkipTest("旁挂文件不存在：先跑 target_types.py")
        cls.rows = load_sidecar()

    def test_covers_every_target_once(self):
        self.assertEqual(len(self.rows), tt.EXPECTED_TARGETS)
        keys = [(row["item_id"], row["question_key"]) for row in self.rows]
        self.assertEqual(len(set(keys)), len(keys), "连接键 (item_id, question_key) 必须唯一")

    def test_required_fields_and_domains(self):
        for row in self.rows:
            for field in REQUIRED_FIELDS:
                self.assertIn(field, row, f"{row['item_id']} 缺字段 {field}")
            for field, domain in FIELD_DOMAINS.items():
                self.assertIn(row[field], domain, f"{row['item_id']} 的 {field}={row[field]!r} 越界")
            self.assertIsInstance(row["mechanism_unknown"], bool)
            self.assertIsInstance(row["provenance_ref"], list)
            self.assertTrue(row["provenance_ref"], "每行都必须有来源证据")
            self.assertIn(row["shape_override"], (None, "R12", "R13"))
            self.assertTrue(row["rule_id"].startswith("R"))

    def test_distribution_matches_provenance_report(self):
        counts = Counter(row["target_type"] for row in self.rows)
        self.assertEqual(dict(counts), EXPECTED_TARGET_TYPE)
        semantics = Counter(row["distribution_semantics"] for row in self.rows)
        self.assertEqual(dict(semantics), EXPECTED_SEMANTICS)
        shapes = Counter(row["shape_class"] for row in self.rows)
        self.assertEqual(dict(shapes), EXPECTED_SHAPE)

    def test_rule_hits_match_provenance_report(self):
        hits = Counter(row["rule_id"] for row in self.rows)
        self.assertEqual({rid: hits.get(rid, 0) for rid in EXPECTED_RULE_HITS}, EXPECTED_RULE_HITS)
        overrides = Counter(row["shape_override"] for row in self.rows if row["shape_override"])
        self.assertEqual(dict(overrides), EXPECTED_SHAPE_OVERRIDE)
        self.assertEqual(sum(overrides.values()), 341)

    def test_baseline_invariants(self):
        counts = Counter(row["target_type"] for row in self.rows)
        shapes = Counter(row["shape_class"] for row in self.rows)
        # hard_label 与「我们伪造的 one-hot」一一对应（对应转换器旗标 hard_label_to_point_mass）
        self.assertEqual(counts["hard_label"], shapes["onehot_fabricated"])
        # 伪 one-hot 合计 = 报告 §0.4 的 5,488 + 8,631
        self.assertEqual(shapes["onehot_fabricated"] + shapes["onehot_native"], 14_119)
        # 唯一可当校准参照的 432 条
        roles = Counter(row["calibration_role"] for row in self.rows)
        self.assertEqual(roles["reference_probability"], 432)
        # 机制未知只有 jev-distill 的 yuri_v3 + yuri_v1（报告 §7 U1）
        self.assertEqual(sum(1 for row in self.rows if row["mechanism_unknown"]), 6_999)
        self.assertEqual({row["rule_id"] for row in self.rows if row["mechanism_unknown"]},
                         {"R9", "R10"})
        # 形态兜底只降级 target_type，不改 distribution_semantics
        for row in self.rows:
            if row["shape_override"]:
                self.assertEqual(row["target_type"], "uninformative_uniform")
                self.assertEqual(row["target_type_basis"], "shape")
        self.assertEqual(sum(1 for row in self.rows if row["target_type_basis"] == "shape"), 341)

    def test_training_route_is_consistent(self):
        routes = Counter(row["training_route"] for row in self.rows)
        self.assertEqual(dict(routes), {"classification": 22_536, "distillation": 7_288, "drop": 1_962})
        for row in self.rows:
            expected = tt._training_route(row["target_type"], row["shape_class"])
            self.assertEqual(row["training_route"], expected)
        # 来源自带的 one-hot 走分类损失（用户批准口径），教师软分布才走蒸馏
        for row in self.rows:
            if row["shape_class"] == "onehot_native":
                self.assertEqual(row["training_route"], "classification")
        self.assertEqual(Counter(row["rule_id"] for row in self.rows
                                 if row["training_route"] == "distillation"),
                         Counter({"R9": 5_364, "R11": 1_492, "R5": 432}))


class RegenerationTest(unittest.TestCase):
    """有语料时：重算必须与已落盘逐行一致（规则或语料一变就红）。"""

    @unittest.skipUnless(CORPUS.is_file(), "仓内语料不存在（大文件不入库）：跳过重算比对")
    def test_regeneration_is_byte_identical(self):
        rows = tt.build_rows(CORPUS)
        self.assertEqual(tt.self_check(rows), [])
        self.assertEqual(tt.render(rows), "".join(json.dumps(row, ensure_ascii=False,
                                                              separators=(",", ":")) + "\n"
                                                  for row in load_sidecar()))


class RouteTest(unittest.TestCase):
    """过滤口径：--ties 只影响 R13 的 232 条。"""

    def test_ties_switch_only_moves_r13(self):
        row_r13 = {"shape_override": "R13", "training_route": "drop"}
        row_r12 = {"shape_override": "R12", "training_route": "drop"}
        row_soft = {"shape_override": None, "training_route": "distillation"}
        self.assertEqual(ft.route_of(row_r13, "distill"), "distillation")
        self.assertEqual(ft.route_of(row_r13, "drop"), "drop")
        self.assertEqual(ft.route_of(row_r12, "distill"), "drop")
        self.assertEqual(ft.route_of(row_soft, "distill"), "distillation")

    def test_uncovered_targets_route_by_shape(self):
        classify = ft.route_of_uncovered
        self.assertEqual(classify({}, {}, {"answer": "yes"}), "classification")
        self.assertEqual(classify({}, {}, {"probs": {"a": 0.5, "b": 0.5}}), "drop")
        self.assertEqual(classify({}, {}, {"probs": {"a": 0.7, "b": 0.3}}), "distillation")


if __name__ == "__main__":
    unittest.main()
