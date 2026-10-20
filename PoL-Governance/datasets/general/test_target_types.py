"""target_types.py / filter_targets.py 自检：旁挂文件只覆盖公开分区、逐行与规则表自洽、路由可复算、且不指认 benchmark 成员。

放在 datasets/general/ 根目录（与其余 test_*.py 一致），tools/check.py 的 unittest discovery 能收进来。
旁挂文件优先读明文 data/target-types.jsonl；明文被 .gitignore 第 13 行挡住（属派生大文件，只提交 .gz），
所以干净检出上退到 data/target-types.jsonl.gz。

两条纪律：

1. **期望值一律推导，不写死。** 总数来自公开分区（train/test/validation）的 target 键减去中文补充；
   分布与逐规则计数来自 target_types.RULES 与旁挂文件自身。旁挂件只含公开分区（v5：全量 82,843
   → 落盘 74,853），将来重切数字还会变——该红的是语义断了，不是数字变了。
2. **护栏盯内容级。** 旁挂文件不含答案，但它的 item_id 列等于一份成员名单：指认「谁属于内部
   benchmark」配上仍在 git 历史里可达的语料，就能精确还原保留集。所以除了 test_split.py 的公开面
   文本扫描，这里再从数据层断言 item_id 与 benchmark 成员零交集（两层，见 BenchmarkIsolationTest）。
"""

import gzip
import json
import os
import sys
import tempfile
import unittest
from collections import Counter
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import filter_targets as ft  # noqa: E402
import target_types as tt  # noqa: E402

DATA = HERE / "data"
SIDECAR_PLAIN = DATA / "target-types.jsonl"
SIDECAR_GZ = DATA / "target-types.jsonl.gz"
CORPUS = DATA / "items.final.jsonl"
SPLITS = DATA / "splits"
SUPPLEMENT = DATA / "zh-supplement" / "items.jsonl"

#: 公开分区（落盘口径）。benchmark 是内部保留集：只在护栏层 2 里被读，且从不落盘。
PUBLIC_SPLITS = ("train", "test", "validation")
BENCHMARK_SPLIT = "benchmark"

#: 注入演练用：把旁挂文件指向一份**副本**（默认读仓内真件）。只在手工演练里设置，check.py 不设。
SIDECAR_ENV = "POL_TARGET_TYPES_SIDECAR"

#: 报告 §6.2 的字段值域。是字段规格，不是总数——总数一律推导。
FIELD_DOMAINS = {
    "target_type": {"hard_label", "soft_distribution", "uninformative_uniform", "answer_only"},
    "distribution_semantics": {"vote_share", "model_logits", "temperature_softmax",
                               "self_confidence", "rule_counter", "human_annotation", "unknown", "none"},
    "target_type_basis": {"source", "shape"},
    "semantics_confidence": {"high", "medium", "low", "unknown"},
    "calibration_role": {"reference_probability", "soft_target_only", "label_only"},
    "label_trust": {"rule_exact", "teacher_argmax", "behavioral", "unknown", "native_gold"},
    "shape_class": {"answer_only", "onehot_fabricated", "onehot_native", "soft",
                    "uniform_all_candidates", "tie_subset"},
    "training_route": {"drop", "classification", "distillation"},
}
REQUIRED_FIELDS = tuple(FIELD_DOMAINS) + ("provenance_ref", "mechanism_unknown", "rule_id",
                                          "shape_override", "item_id", "question_key")


def local_file(path):
    """明文优先，干净检出退到同名 .jsonl.gz；都没有返回 None。"""
    plain = Path(path)
    if plain.is_file():
        return plain
    packed = plain.with_suffix(".jsonl.gz")
    return packed if packed.is_file() else None


def read_jsonl(path):
    opener = gzip.open if Path(path).suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_text(path):
    opener = gzip.open if Path(path).suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return handle.read()


def sidecar_file():
    """旁挂文件路径：演练覆盖优先，否则仓内真件（明文优先，退到 .gz）。"""
    override = os.environ.get(SIDECAR_ENV)
    if override:
        return Path(override)
    if SIDECAR_PLAIN.is_file():
        return SIDECAR_PLAIN
    return SIDECAR_GZ if SIDECAR_GZ.is_file() else None


def load_sidecar(path=None):
    """读旁挂文件。path 省略时读仓内真件（或演练覆盖）；不存在则跳过相关测试。"""
    path = Path(path) if path is not None else sidecar_file()
    if path is None or not path.is_file():
        raise unittest.SkipTest(f"旁挂文件不存在：{SIDECAR_PLAIN}（也没有 {SIDECAR_GZ.name}）")
    return read_jsonl(path)


def target_keys(items):
    """(item_id, question_key)：只算真的挂了 target 的问题键——旁挂文件一行对一个 target。"""
    return {(item["id"], q["key"]) for item in items
            for q in item.get("questions") or []
            if (item.get("targets") or {}).get(q.get("key")) is not None}


@lru_cache(maxsize=1)
def public_split_items():
    """公开三分区的条目。分区是入库的 .gz，干净检出上不该缺；缺了就当测试环境不完整。"""
    items = []
    for name in PUBLIC_SPLITS:
        path = local_file(SPLITS / f"{name}.jsonl")
        if path is None:
            raise unittest.SkipTest(f"公开分区不在本机：{name}.jsonl(.gz)")
        items.extend(read_jsonl(path))
    return tuple(items)


def public_keys():
    return target_keys(public_split_items())


def public_item_ids():
    return {item["id"] for item in public_split_items()}


def supplement_keys():
    """中文补充（db-zhtax-*，只追加进 train 尾、不在冻结语料里）：由 filter_targets 兜底路由。"""
    path = local_file(SUPPLEMENT)
    return target_keys(read_jsonl(path)) if path else set()


def benchmark_ids():
    """内部保留集的 id 集合；不在本机返回 None（.gitignore 第 15 行：单独交付，不入公开仓）。"""
    path = local_file(SPLITS / f"{BENCHMARK_SPLIT}.jsonl")
    return {item["id"] for item in read_jsonl(path)} if path else None


def benchmark_membership(rows, members):
    """护栏核心：旁挂行的 item_id 与 benchmark 成员的**交集**（排序、去重）。空 = 通过。"""
    return sorted({row["item_id"] for row in rows} & set(members))


class SidecarTest(unittest.TestCase):
    """旁挂文件本身的自洽性（不需要 82MB 语料，干净检出也能跑）。"""

    @classmethod
    def setUpClass(cls):
        cls.rows = load_sidecar()

    def test_covers_every_public_target_once(self):
        """覆盖：公开分区里挂在冻结语料上的 target 恰好一行，一条不多、一条不少。

        期望值推导 = 公开三分区的 target 键 − 中文补充的 target 键。补充只追加进 train 尾、
        不在冻结语料里（由 filter_targets.route_of_uncovered 兜底路由），因此不在旁挂文件里。
        只断包含关系查不出「少了一行」，所以两边都断。
        """
        keys = [(row["item_id"], row["question_key"]) for row in self.rows]
        self.assertEqual(len(set(keys)), len(keys), "连接键 (item_id, question_key) 必须唯一")
        expected = public_keys() - supplement_keys()
        self.assertEqual(set(keys), expected)
        self.assertEqual(len(self.rows), len(expected))

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

    def test_rows_follow_the_rule_table(self):
        """逐行与 target_types.RULES 的静态载荷一致：旁挂件是规则算出来的，不是手抄的。

        这条占的是原来「与报告 §6.3 对账」的位置——全量基准对已过滤的落盘件不再可比，
        而「行 ⇔ 规则表」不依赖任何总数，重切也不会失效。
        """
        for row in self.rows:
            ident = f"{row['item_id']}/{row['question_key']}"
            self.assertIn(row["rule_id"], tt.RULES, f"{ident} 的规则号不在规则表里")
            self.assertNotIn(row["rule_id"], ("R12", "R13"),
                             f"{ident}：覆盖规则号只应出现在 shape_override")
            payload = tt.RULES[row["rule_id"]]
            self.assertEqual(row["distribution_semantics"],
                             payload.get("distribution_semantics", "none"), ident)
            self.assertEqual(row["calibration_role"], payload["calibration_role"], ident)
            self.assertEqual(row["label_trust"], payload["label_trust"], ident)
            self.assertEqual(row["semantics_confidence"], payload["semantics_confidence"], ident)
            self.assertEqual(row["mechanism_unknown"], payload["mechanism_unknown"], ident)
            self.assertEqual(row["provenance_ref"], list(payload["refs"]), ident)
            if row["shape_override"] is None:
                self.assertEqual(row["target_type"], payload["target_type"], ident)
                self.assertEqual(row["target_type_basis"], "source", ident)
            else:
                self.assertEqual(row["target_type"], "uninformative_uniform", ident)
                self.assertEqual(row["target_type_basis"], "shape", ident)

    def test_distribution_is_self_consistent(self):
        """分布自洽：每类计数都能从「规则表 + 形态覆盖」复算，且跨字段互相钳制。

        不再与报告 §6.3 的全量基准比（那份含非公开分区，与落盘件不可比）；换成不依赖任何总数的
        推导：少一行、规则断一路、覆盖规则失灵都会红。
        """
        counts = Counter(row["target_type"] for row in self.rows)
        shapes = Counter(row["shape_class"] for row in self.rows)
        routes = Counter(row["training_route"] for row in self.rows)
        semantics = Counter(row["distribution_semantics"] for row in self.rows)
        overrides = Counter(row["shape_override"] for row in self.rows if row["shape_override"])

        for label, counter, domain in (("target_type", counts, FIELD_DOMAINS["target_type"]),
                                       ("shape_class", shapes, FIELD_DOMAINS["shape_class"]),
                                       ("training_route", routes, FIELD_DOMAINS["training_route"]),
                                       ("distribution_semantics", semantics,
                                        FIELD_DOMAINS["distribution_semantics"])):
            self.assertEqual(sum(counter.values()), len(self.rows), f"{label} 计数合计 != 行数")
            self.assertLessEqual(set(counter), domain, f"{label} 出现越界取值")

        # 每个 target_type 都能从规则表的静态 target_type + 形态覆盖复算
        for name in FIELD_DOMAINS["target_type"]:
            expected = sum(1 for row in self.rows
                           if (name == "uninformative_uniform" and row["shape_override"] is not None)
                           or (row["shape_override"] is None
                               and tt.RULES[row["rule_id"]]["target_type"] == name))
            self.assertEqual(counts.get(name, 0), expected, f"{name} 计数与规则表不符")

        # 形态桶与 target_type 一一对得上（原 test_baseline_invariants 的意图）
        self.assertEqual(counts["hard_label"], shapes["onehot_fabricated"])
        self.assertEqual(counts["answer_only"], shapes["answer_only"])
        # 非「并列均分构造」的 tie_subset 保留源语义 soft_distribution（v4 起出现），要一并算进来
        soft_ties = sum(1 for row in self.rows
                        if row["shape_class"] == "tie_subset" and row["shape_override"] is None)
        self.assertEqual(counts["soft_distribution"],
                         shapes["soft"] + shapes["onehot_native"] + soft_ties)
        # 无信息均匀有两个来源，且不重叠：来源规则自己就判它的（yuri_v1 常量流）+ 被形态覆盖降级的
        by_source = sum(1 for row in self.rows
                        if row["shape_override"] is None
                        and tt.RULES[row["rule_id"]]["target_type"] == "uninformative_uniform")
        self.assertEqual(counts["uninformative_uniform"], by_source + sum(overrides.values()))
        # 形态覆盖只可能来自 R12/R13，且只吃对应形态桶（R13 只吃并列子集的一部分，其余是真实取值）
        self.assertLessEqual(set(overrides), {"R12", "R13"})
        self.assertLessEqual(overrides["R12"], shapes["uniform_all_candidates"])
        self.assertLessEqual(overrides["R13"], shapes["tie_subset"])
        # 覆盖只降级 target_type，不改语义 / 角色 / 可信度；全候选等值一律降级（覆盖或来源规则）
        for row in self.rows:
            if row["shape_override"]:
                self.assertEqual(row["target_type"], "uninformative_uniform")
                self.assertEqual(row["target_type_basis"], "shape")
            if row["shape_class"] == "uniform_all_candidates":
                self.assertEqual(row["target_type"], "uninformative_uniform",
                                 f"{row['item_id']}：全候选等值必须降级成无信息均匀")

        # 这三列的特殊取值只能由规则表里声明了它们的规则产出（不写死具体规则号）
        for field, want in (("distribution_semantics", "unknown"),
                            ("calibration_role", "reference_probability"),
                            ("mechanism_unknown", True)):
            allowed = {rid for rid, payload in tt.RULES.items() if payload.get(field) == want}
            self.assertTrue(allowed, f"规则表里没有声明 {field}={want!r} 的规则")
            got = {row["rule_id"] for row in self.rows if row[field] == want}
            self.assertEqual(got, allowed, f"{field}={want!r} 只能来自 {sorted(allowed)}")

    def test_training_route_is_consistent(self):
        counts = Counter(row["target_type"] for row in self.rows)
        routes = Counter(row["training_route"] for row in self.rows)
        for row in self.rows:
            self.assertEqual(row["training_route"],
                             tt._training_route(row["target_type"], row["shape_class"]),
                             f"{row['item_id']}/{row['question_key']}")
        # drop ⇔ 无信息均匀
        self.assertEqual(routes["drop"], counts["uninformative_uniform"])
        for row in self.rows:
            if row["shape_class"] == "onehot_native":
                # 来源自带的 one-hot 走分类损失（用户批准口径），不是蒸馏
                self.assertEqual(row["training_route"], "classification")
            if row["shape_class"] == "uniform_all_candidates":
                self.assertEqual(row["training_route"], "drop")
        # 蒸馏目标 = 真·软分布 + 保留源语义的并列子集（两者都必须是 soft_distribution）
        self.assertLessEqual({row["shape_class"] for row in self.rows
                              if row["training_route"] == "distillation"}, {"soft", "tie_subset"})
        self.assertEqual({row["target_type"] for row in self.rows
                          if row["training_route"] == "distillation"}, {"soft_distribution"})


class BenchmarkIsolationTest(unittest.TestCase):
    """内容级护栏（本任务核心）：旁挂文件不得指认任何 benchmark 成员。

    为什么盯内容级：上一次泄漏的根因是只查了「文件有没有被 git 跟踪」，没查「内容里有没有
    benchmark 成员」。文件级检查对旁挂件永远通过——它是入库的派生 .gz，看着人畜无害——但它的
    item_id 列等于一份成员名单，配上仍在 git 历史里可达的语料即可精确还原保留集。

    分两层，因为 benchmark.jsonl 被 .gitignore 第 15 行挡在仓外（干净检出上没有）：
    层 1 用**公开分区白名单**（入库的 train/test/validation .gz 推得出，CI 也生效）；
    层 2 在本机有保留集时再断言与 benchmark id 的**交集为空**（任务书字面要求）。
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = load_sidecar()

    def assert_only_public_members(self, rows, label="旁挂文件"):
        """层 1：每个 item_id 都必须落在公开分区里——benchmark 的 id 一个都不在其中。"""
        stray = sorted({row["item_id"] for row in rows} - public_item_ids())
        self.assertEqual(stray, [],
                         f"{label} 含 {len(stray)} 个不属于公开分区的 item_id（疑似保留集成员）："
                         f"{stray[:5]}")

    def assert_no_benchmark_member(self, rows, members, label="旁挂文件"):
        """层 2：与 benchmark 成员零交集。"""
        leaks = benchmark_membership(rows, members)
        self.assertEqual(leaks, [],
                         f"{label} 指认了 {len(leaks)} 个 benchmark 成员：{leaks[:5]}")

    def test_sidecar_ids_stay_inside_public_partitions(self):
        self.assert_only_public_members(self.rows)

    def test_sidecar_has_no_benchmark_member(self):
        members = benchmark_ids()
        if members is None:
            self.skipTest("benchmark.jsonl 不在本机（.gitignore 第 15 行：保留集单独交付）；"
                          "层 1（公开分区白名单）仍在跑")
        self.assertTrue(members, "benchmark 为空等于护栏失效")
        self.assert_no_benchmark_member(self.rows, members)

    def test_guard_fires_on_poisoned_copies(self):
        """护栏自证：同一段断言在**注入了外来 id 的副本**上必须报红，在未注入副本上必须通过。

        只写不验等于没写——这条把「临时手工注入实验」固化成可复跑的回归。明文与 .gz 两种形态都试
        （入库的是 .gz）。注入的 id 取一个真 benchmark 成员（有保留集时）加一个任何分区都没有的
        合成 id（没有保留集时也能自证）。
        """
        members = benchmark_ids()
        # (注入的 id, 期望层 2 是否也该报红)：合成 id 不属于任何分区，但也不是 benchmark 成员，
        # 层 2 不该动——这正是「不误报」的一半证据；真成员两个层都必须报红。
        cases = [("db-injected-not-in-any-split-0000", False)]
        if members:
            cases.append((sorted(members)[0], True))
        for poison, is_member in cases:
            rows = [dict(self.rows[0], item_id=poison)] + self.rows[1:]
            with tempfile.TemporaryDirectory() as workspace:
                for name in ("target-types.jsonl", "target-types.jsonl.gz"):
                    copy = Path(workspace) / name
                    payload = tt.render(rows).encode("utf-8")
                    if name.endswith(".gz"):
                        with gzip.open(copy, "wb") as handle:
                            handle.write(payload)
                    else:
                        copy.write_bytes(payload)
                    loaded = load_sidecar(copy)
                    with self.assertRaises(AssertionError) as caught:
                        self.assert_only_public_members(loaded, f"注入副本 {name}")
                    self.assertIn(poison, str(caught.exception), "护栏报错必须点名注入的 id")
                    if not members:
                        continue
                    if is_member:
                        with self.assertRaises(AssertionError) as caught:
                            self.assert_no_benchmark_member(loaded, members, f"注入副本 {name}")
                        self.assertIn(poison, str(caught.exception))
                    else:
                        # 层 2 不是「逢查必响」：非成员不得被判成泄漏
                        self.assert_no_benchmark_member(loaded, members, f"注入副本 {name}")
        # 未注入的副本必须通过：防止写出「逢查必响」的假护栏
        with tempfile.TemporaryDirectory() as workspace:
            clean = Path(workspace) / "target-types.jsonl"
            clean.write_bytes(tt.render(self.rows).encode("utf-8"))
            loaded = load_sidecar(clean)
            self.assert_only_public_members(loaded, "未注入副本")
            if members:
                self.assert_no_benchmark_member(loaded, members, "未注入副本")


class RegenerationTest(unittest.TestCase):
    """有语料时：重算（全量扫描 → 只留公开分区）必须与已落盘逐字节一致。"""

    @unittest.skipUnless(CORPUS.is_file(), "仓内语料不存在（大文件不入库）：跳过重算比对")
    def test_regeneration_is_byte_identical(self):
        """语料、规则或公开分区一变就红；顺带证明落盘件里一条非公开成员都没有。

        白名单取不到就抛错（fail closed），不允许退回「全量落盘」——那等于把泄漏放回去。
        """
        all_rows, scan_stats = tt.build_all_rows(CORPUS)
        self.assertEqual(tt.self_check(all_rows, scan_stats), [])
        rows = tt.public_rows(all_rows, tt.load_public_ids(SPLITS))
        self.assertTrue(rows, "公开分区过滤后一行都不剩，白名单大概率取错了")
        path = sidecar_file()
        self.assertIsNotNone(path, "旁挂文件不存在")
        self.assertEqual(read_text(path), tt.render(rows), f"{path} 与重算结果不一致")
        self.assertEqual(sorted({row["item_id"] for row in rows} - public_item_ids()), [])


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
