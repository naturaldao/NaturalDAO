"""target 语义回填（旁挂）：按 target-provenance.md §6 的 R1-R15 给每个 target 标注语义与训练用途。

用法::

    uv run --no-project --offline python datasets/general/target_types.py             # 生成 + 自检
    uv run --no-project --offline python datasets/general/target_types.py --verify    # 只校验：重算结果与已落盘逐行一致
    uv run --no-project --offline python datasets/general/target_types.py \
        --input "D:/pol2-raw/general-private/data/items.final.jsonl.gz"               # 直接读冻结语料

输入（只读，不改）：默认 datasets/general/data/items.final.jsonl（v4：74,912 条 / 82,843 target；
v3 的 23,855 / 31,786 是它的子集，逐条未变）。语料每次合并都会变，本脚本**不做任何
"总数 = 某常数"的断言**——所有期望值从输入现算。
输出：datasets/general/data/target-types.jsonl —— 每条 target 一行，旁挂文件，原语料一个字节都不动。
落盘格式：每行 canonical JSON（键序排序、默认分隔符），与已交付的 .gz 逐字节可复算。
**只写公开分区**：按 data/splits/{train,test,validation} 的 item id 白名单过滤（--splits 可换目录），
非公开分区（内部 benchmark）的 target 只参与内存里的全量自检、**不落盘**——成员身份本身就是敏感信息，
配上仍在 git 历史里的语料即可精确还原保留集；这些 target 的路由信息在仓外维护（TRAINING.md §1.1）。
白名单取不到就报错退出（fail closed），绝不退回「全量落盘」。

判定纪律（报告 §6.1）：

1. 先判来源证据：source.slug -> meta.native_source -> meta.native_task + 问题键 ->
   meta.quality_flags。这些都是转换时由代码按来源字段写下的。
2. 数值形态只出现在两处：(a) 作为 target_type 的降级候选（最多降成 uninformative_uniform，
   绝不把向量判成某个语义）；(b) shape_note 旁证字段，消费者可忽略。凡用到形态的判定，
   target_type_basis 写 shape 而不是 source。
3. 不猜：规则表覆盖全部 target，未命中即报错退出。

字段：报告 §6.2 的 9 个字段 + 本任务新增的 3 个旁挂字段（见 TRAINING.md §2）：

- rule_id        命中的**来源证据**规则号（R1-R11、R14、R15），便于与报告 §6.3 逐行对账
- shape_override 形态覆盖规则号 R12 / R13 / null（覆盖只降级 target_type，不改语义）
- shape_class    target 的形态桶（旁证）：answer_only / onehot_fabricated / onehot_native /
                 soft / uniform_all_candidates / tie_subset
- training_route 训练侧路由：drop / classification / distillation
- label_trust    v4 新增取值 native_gold：上游数据集的原生金标签（bigbench / cosmos_qa），
                 不是本仓库规则算出。用 rule_exact 会系统性低估它的可信度，故单列。

自检（不通过就非零退出）只断言**可从数据推导或内部一致**的结论：
① 全量扫描 classified + unregistered == scanned，且未登记来源必须为 0（否则旁挂件会静默缺行）；
② 每行的 target_type / 语义 / 角色 / 可信度 / 置信度 / 机制未知 / 证据集 == RULES 的静态载荷，
   route == _training_route 复算，覆盖规则只可能是 R12/R13，全候选等值必须降级；
③ 落盘件**恰好**覆盖「公开分区 ∩ 语料」的每个 target——名单外一条不写、名单内一条不漏。
v3 报告 §6.3 的分布 / 逐规则命中数不再断言：那是上一份报告的结论，不是可推导事实（见 RULES 上方）。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "datasets/general/data/items.final.jsonl"
DEFAULT_OUT = REPO_ROOT / "datasets/general/data/target-types.jsonl"
DEFAULT_SPLITS = REPO_ROOT / "datasets/general/data/splits"

#: 公开分区：只有这三个分区里的 target 允许落盘。benchmark 不在其中，且**永远不会被读**——
#: 用白名单而不是黑名单，连它的 id 都不需要知道。
PUBLIC_SPLITS = ("train", "test", "validation")

#: v3 冻结语料指纹（仅在文档里引用；v4 语料是在它上面合入 bigbench / cosmos_qa）。
#: 不要在这里加「总数 / 分布 / 逐规则命中」常量：它们每换一次语料就碎一次（同类问题已出现三次）。
#: v3 的历史数字在 target-provenance.md §6.3 与 TRAINING.md §3，仅供文档对照。
FROZEN_GZ_SHA256 = "ba615c96c0dc13cbc4caa8b0f83ac1326abc13700bde98579f2ebb9f38bdaece"

#: 已登记来源规则链的 slug 白名单。表里没有的来源**不猜测 provenance**：不写进旁挂文件，
#: 只在汇总里报 unregistered_*，并由 self_check 报错（静默缺行比报错危险）——补规则与证据
#: （target-provenance.md §6.3/§6.4）后再登记。v4 并入的 bigbench / cosmos_qa 已按 E14/E15 登记。
REGISTERED_SLUGS = (
    "jev-decisions-general-50k", "jev-decisions-strata", "systemone-lite-general",
    "deepexi-fcs-v3", "procedural-typed-decisions", "open-jev", "jev-distill-v3",
    "system-one-270m", "bigbench", "cosmos-qa",
)

#: 形态比较容差。语料里的概率已由转换器 round(..., 6)，1e-9 远小于最小量子 1e-6。
SHAPE_EPS = 1e-9

#: §3.6 的 7 个 documented「精确概率」键：只有这些 (task, question key) 上的非退化取值
#: 才是「由状态精确算出的 P(结果|状态)」，即全语料唯一可当校准参照的 432 条。
EXACT_PROBABILITY_KEYS = frozenset({
    ("partial_observation_calibration", "incident_real"),
    ("policy_under_uncertainty", "access_allowed"),
    ("policy_under_uncertainty", "governing_policy"),
    ("policy_under_uncertainty", "requester_role"),
    ("arithmetic", "random_line_bulk"),
    ("arithmetic", "random_is_long"),
    ("arithmetic", "random_is_deposit"),
})

#: 形态桶（旁证）。与报告 §0.2 的四分类是同一套事实、更细的切分。
SHAPE_CLASSES = (
    "answer_only", "onehot_fabricated", "onehot_native",
    "soft", "uniform_all_candidates", "tie_subset",
)

#: 每个规则的静态载荷（报告 §6.3）。priority 大的覆盖小的（§6.1 第 4 条）。
RULES = {
    "R1": dict(priority=10, source="jev-decisions 两个抓取单元",
               target_type="hard_label", distribution_semantics="none",
               calibration_role="label_only", label_trust="behavioral",
               semantics_confidence="high", mechanism_unknown=False, refs=["E1", "E2"]),
    "R2": dict(priority=10, source="systemone-lite-general",
               target_type="hard_label", distribution_semantics="none",
               calibration_role="label_only", label_trust="rule_exact",
               semantics_confidence="high", mechanism_unknown=False, refs=["E3"]),
    "R3": dict(priority=10, source="deepexi-fcs-v3（无 probs）",
               target_type="answer_only", distribution_semantics="unknown",
               calibration_role="label_only", label_trust="unknown",
               semantics_confidence="unknown", mechanism_unknown=False, refs=["E4"]),
    "R4": dict(priority=30, source="procedural 无 probs（probs_dropped_zero_mass）",
               target_type="answer_only", distribution_semantics="none",
               calibration_role="label_only", label_trust="rule_exact",
               semantics_confidence="high", mechanism_unknown=False, refs=["E5"]),
    "R5": dict(priority=40, source="procedural 的 7 个 documented 精确概率键（非退化取值）",
               target_type="soft_distribution", distribution_semantics="rule_counter",
               calibration_role="reference_probability", label_trust="rule_exact",
               semantics_confidence="high", mechanism_unknown=False, refs=["E5"]),
    "R6": dict(priority=20, source="procedural 其余（含 7 键上的退化取值）",
               target_type="soft_distribution", distribution_semantics="rule_counter",
               calibration_role="label_only", label_trust="rule_exact",
               semantics_confidence="high", mechanism_unknown=False, refs=["E5"]),
    "R7": dict(priority=10, source="open-jev",
               target_type="soft_distribution", distribution_semantics="rule_counter",
               calibration_role="label_only", label_trust="rule_exact",
               semantics_confidence="high", mechanism_unknown=False, refs=["E6", "E7", "E8"]),
    "R8": dict(priority=30, source="jev-distill-v3 / openjev_v2",
               target_type="soft_distribution", distribution_semantics="rule_counter",
               calibration_role="label_only", label_trust="rule_exact",
               semantics_confidence="high", mechanism_unknown=False, refs=["E9"]),
    "R9": dict(priority=30, source="jev-distill-v3 / yuri_v3（教师 Jev 1.13 蒸馏）",
               target_type="soft_distribution", distribution_semantics="model_logits",
               calibration_role="soft_target_only", label_trust="teacher_argmax",
               semantics_confidence="medium", mechanism_unknown=True, refs=["E9", "E10"]),
    "R10": dict(priority=30, source="jev-distill-v3 / yuri_v1（整条子流常量 0.5）",
                target_type="uninformative_uniform", distribution_semantics="model_logits",
                calibration_role="soft_target_only", label_trust="teacher_argmax",
                semantics_confidence="medium", mechanism_unknown=True, refs=["E9", "E11"]),
    "R11": dict(priority=10, source="system-one-270m（logprob 集合均值）",
                target_type="soft_distribution", distribution_semantics="model_logits",
                calibration_role="soft_target_only", label_trust="teacher_argmax",
                semantics_confidence="high", mechanism_unknown=False, refs=["E12", "E13"]),
    # 形态兜底（覆盖规则）：不改 distribution_semantics / calibration_role / label_trust，
    # 只把 target_type 降级成 uninformative_uniform，并把 target_type_basis 标成 shape。
    "R12": dict(priority=5, source="形态兜底：全候选等值",
                target_type="uninformative_uniform", refs=[]),
    "R13": dict(priority=5, source="形态兜底：正权重子集等值，且来源是「并列均分」构造",
                target_type="uninformative_uniform", refs=[]),
    # v4 并入的两个能力补源：targets 只有 answer、没有 probs（转换器 convert_capability.py 0.2
    # 只写原生金标签，不保留分数/概率）。与 R3/R4 的区别：标签来源有文档（E14/E15），既不是教师
    # 推断也不是本仓库规则算出。label_trust 用 v4 新增的 native_gold：这是**上游数据集的金标签**，
    # 用 rule_exact 会系统性低估它的可信度（rule_exact 指「本仓库规则精确算出」）。标注质量未独立
    # 复核（属后续审计），但字段语义必须准确。
    "R14": dict(priority=10, source="tasksource/bigbench（上游金标签，无 probs）",
                target_type="answer_only", distribution_semantics="none",
                calibration_role="label_only", label_trust="native_gold",
                semantics_confidence="high", mechanism_unknown=False, refs=["E14"]),
    "R15": dict(priority=10, source="allenai/cosmos_qa（上游金标签，无 probs）",
                target_type="answer_only", distribution_semantics="none",
                calibration_role="label_only", label_trust="native_gold",
                semantics_confidence="high", mechanism_unknown=False, refs=["E15"]),
}

#: 形态覆盖规则号：只出现在 shape_override，永远不会是某行的 rule_id。
OVERRIDE_RULES = ("R12", "R13")


class BackfillError(Exception):
    """输入、规则或自检不通过。"""


# ------------------------------------------------------------------ 读取

def iter_items(path):
    """逐行读 JSONL（支持 .gz）。"""
    source = Path(path)
    if not source.is_file():
        raise BackfillError(f"输入不存在：{source}")
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield lineno, json.loads(line)
            except json.JSONDecodeError as exc:
                raise BackfillError(f"{source}:{lineno} JSON 解析失败：{exc}") from exc


# ------------------------------------------------------------------ 形态（只作旁证 / 降级候选）

def measure_shape(probs, flags):
    """量出 target 的形态桶。只作旁证：调用方不得据此推断语义。返回 (shape_class, shape_note)。"""
    if probs is None:
        return "answer_only", None
    values = [float(v) for v in probs.values()]
    if not values:
        return "answer_only", "probs 为空对象"
    highest, lowest = max(values), min(values)
    positive = [v for v in values if v > 0.0]
    if highest - lowest < SHAPE_EPS:
        return "uniform_all_candidates", f"源向量对全部 {len(values)} 个候选等值（{lowest:.6g}）"
    if len(positive) == 1 and highest >= 1.0 - SHAPE_EPS:
        if "hard_label_to_point_mass" in flags:
            return "onehot_fabricated", "我们按 point_mass 造的单点（旗标 hard_label_to_point_mass）"
        return "onehot_native", "来源自带的退化取值：恰一个候选非零且为 1"
    if len(positive) >= 2 and max(positive) - min(positive) < SHAPE_EPS:
        return "tie_subset", f"正权重子集等值：{len(positive)}/{len(values)} 个候选并列"
    return "soft", None


def _is_tie_construct(slug, native_source):
    """该来源的「并列」是不是构造（文档明说「并列均分」），而非真实取值。

    只有这两处：open-jev 的 defined_uniform_latent_worlds（E8：uniform over equally best
    passages），以及 jev-distill 里转出的同一 Open-Jev 流（E9）。其余来源上的并列是真实取值——
    教师真的 0.5/0.5、规则后验真的并列——保留源语义，不降级。
    """
    return slug == "open-jev" or (slug == "jev-distill-v3" and native_source == "openjev_v2")


# ------------------------------------------------------------------ 规则

def match_source_rule(item, question, shape, has_probs):
    """按来源证据选规则。形态只用于把 R5 限定在非退化取值上。

    R5 的「非退化」不是语义判定，而是可当校准参照的前提：0/1 取值没有概率可校准。
    7 个精确概率键上的 97 条退化取值由 R6 接住（报告 §6.3 R6 = 3,714 正是 4,146 - 432）。
    """
    slug = item["source"]["slug"]
    meta = item.get("meta") or {}
    native_source = meta.get("native_source")

    if slug in ("jev-decisions-general-50k", "jev-decisions-strata"):
        return "R1"
    if slug == "systemone-lite-general":
        return "R2"
    if slug == "deepexi-fcs-v3":
        return "R3"
    if slug == "procedural-typed-decisions":
        if not has_probs:
            return "R4"
        key = (meta.get("native_task"), question["key"])
        degenerate = shape in ("uniform_all_candidates", "onehot_native", "onehot_fabricated")
        if key in EXACT_PROBABILITY_KEYS and not degenerate:
            return "R5"
        return "R6"
    if slug == "open-jev":
        return "R7"
    if slug == "jev-distill-v3":
        if native_source == "openjev_v2":
            return "R8"
        if native_source == "yuri_v1":
            return "R10"
        if native_source == "yuri_v3":
            return "R9"
        raise BackfillError(f"jev-distill-v3 出现未知 meta.native_source={native_source!r}：映射变了，停下来重查")
    if slug == "system-one-270m":
        return "R11"
    if slug in ("bigbench", "cosmos-qa"):
        # v4 能力补源：targets 只有 answer、没有 probs（转换器只写原生金标签）
        if has_probs:
            raise BackfillError(f"{slug} 的 target 突然带 probs：映射变了，停下来重查")
        return "R14" if slug == "bigbench" else "R15"
    raise BackfillError(f"未知 source.slug={slug!r}：映射变了，停下来重查")


def _training_route(target_type, shape):
    """训练侧路由（用户在任务书里批准的口径，详见 TRAINING.md §4）。"""
    if target_type == "uninformative_uniform":
        return "drop"
    if target_type in ("hard_label", "answer_only"):
        return "classification"
    # soft_distribution：来源自带的 one-hot 按硬标签走分类损失，其余才是蒸馏目标。
    return "classification" if shape == "onehot_native" else "distillation"


def classify_target(item, question, target):
    """给一个 target 产出旁挂行；**未登记来源返回 None**（不猜 provenance，等补规则）。"""
    slug = item["source"]["slug"]
    if slug not in REGISTERED_SLUGS:
        return None
    meta = item.get("meta") or {}
    flags = set(meta.get("quality_flags") or [])
    has_probs = target.get("probs") is not None
    shape, shape_note = measure_shape(target.get("probs"), flags)

    rule_id = match_source_rule(item, question, shape, has_probs)
    payload = RULES[rule_id]
    target_type, basis, note = payload["target_type"], "source", shape_note
    refs = list(payload.get("refs", []))
    override = None

    # 形态兜底：只降级 target_type，语义/角色/可信度全部继承源规则。
    if rule_id == "R10":
        note = "整条子流只有一个取值 [0.5, 0.5]（旁证 E11）"
    elif shape == "uniform_all_candidates":
        override, target_type, basis = "R12", "uninformative_uniform", "shape"
    elif shape == "tie_subset":
        if _is_tie_construct(slug, meta.get("native_source")):
            override, target_type, basis = "R13", "uninformative_uniform", "shape"
        else:
            note = (note or "") + "；来源非「并列均分」构造，未降级"

    return {
        "item_id": item["id"],
        "question_key": question["key"],
        "target_type": target_type,
        "distribution_semantics": payload.get("distribution_semantics", "none"),
        "target_type_basis": basis,
        "semantics_confidence": payload.get("semantics_confidence"),
        "mechanism_unknown": payload.get("mechanism_unknown", False),
        "calibration_role": payload.get("calibration_role"),
        "label_trust": payload.get("label_trust"),
        "provenance_ref": refs,
        "shape_note": note,
        "rule_id": rule_id,
        "shape_override": override,
        "shape_class": shape,
        "training_route": _training_route(target_type, shape),
    }


def build_all_rows(path):
    """遍历语料，产出全部旁挂行（**含非公开分区**，只在内存里）；顺带做结构自检。

    返回 (rows, stats)。未登记来源（slug 不在 REGISTERED_SLUGS）的 target **不落盘**：
    在 stats["unregistered_targets"] / stats["unregistered_sources"] 里如实计数，
    等 target-provenance.md 补规则与证据后再纳入。
    """
    seen = set()
    rows = []
    stats = {"scanned_targets": 0, "unregistered_targets": 0,
             "unregistered_sources": Counter(), "unregistered_items": set()}
    for lineno, item in iter_items(path):
        targets = item.get("targets") or {}
        for question in item.get("questions") or []:
            key = question.get("key")
            target = targets.get(key)
            if target is None:
                continue
            stats["scanned_targets"] += 1
            row = classify_target(item, question, target)
            if row is None:
                stats["unregistered_targets"] += 1
                slug = str((item.get("source") or {}).get("slug"))
                stats["unregistered_sources"][slug] += 1
                stats["unregistered_items"].add(item["id"])
                continue
            ident = (row["item_id"], row["question_key"])
            if ident in seen:
                raise BackfillError(f"{path}:{lineno} 连接键 (item_id, question_key) 重复：{ident}")
            seen.add(ident)
            rows.append(row)
    stats["unregistered_items"] = len(stats["unregistered_items"])
    return rows, stats


def load_public_partitions(splits_dir, splits=PUBLIC_SPLITS):
    """公开分区的 (item id 集合, target 键集合)。明文优先，干净检出退到同名 .gz。

    白名单而不是黑名单：不需要读 benchmark.jsonl，也就不必把成员清单搬进源码。
    任何分区缺失都报错退出——静默退回「全量落盘」等于把泄漏放回去（fail closed）。
    """
    ids, keys, missing = set(), set(), []
    for name in splits:
        plain = Path(splits_dir) / f"{name}.jsonl"
        packed = plain.with_suffix(".jsonl.gz")
        path = plain if plain.is_file() else packed
        if not path.is_file():
            missing.append(f"{plain}（也没有 {packed.name}）")
            continue
        for _, item in iter_items(path):
            ids.add(item["id"])
            targets = item.get("targets") or {}
            for question in item.get("questions") or []:
                if targets.get(question.get("key")) is not None:
                    keys.add((item["id"], question.get("key")))
    if missing:
        raise BackfillError("公开分区缺失，拒绝生成旁挂文件（否则会重新包含非公开成员）："
                            + "；".join(missing))
    if not ids:
        raise BackfillError("公开分区为空，拒绝生成旁挂文件")
    return ids, keys


def load_public_ids(splits_dir, splits=PUBLIC_SPLITS):
    """只要 item id 白名单（调用方 / 测试用）。"""
    return load_public_partitions(splits_dir, splits)[0]


def check_coverage(rows, all_rows, public_keys):
    """落盘件必须**恰好**覆盖「公开分区 ∩ 语料」里的每个 target。

    少一条 = 有 target 没有路由，训练侧会静默落到兜底路由；多一条 = 路由指认了不在公开分区的
    target（泄漏风险）。两者都直接报错、不写盘——这是交付件的基本正确性，不能用 --skip-self-check 绕过。
    """
    corpus_keys = {(row["item_id"], row["question_key"]) for row in all_rows}
    expected = set(public_keys) & corpus_keys
    written = {(row["item_id"], row["question_key"]) for row in rows}
    if written != expected:
        missing = sorted(expected - written)[:3]
        extra = sorted(written - expected)[:3]
        raise BackfillError(
            f"旁挂件覆盖不完整：缺 {len(expected - written)} 条（公开分区有、旁挂没有；示例 {missing}），"
            f"多 {len(written - expected)} 条（旁挂有、公开分区没有；示例 {extra}）")


def public_rows(rows, public_ids):
    """只留公开分区的行；行序不变（= 语料顺序，确定性可复算）。"""
    return [row for row in rows if row["item_id"] in public_ids]


def split_partition_ids(splits_dir, splits=PUBLIC_SPLITS + ("benchmark",)):
    """各分区的 item id 集合（公开三区 + 内部保留集）。

    保留集不在本机（.gitignore 第 15 行）时值为 None——只是不报这一行，不算错。
    """
    result = {}
    for name in splits:
        plain = Path(splits_dir) / f"{name}.jsonl"
        packed = plain.with_suffix(".jsonl.gz")
        path = plain if plain.is_file() else packed
        if not path.is_file():
            result[name] = None
            continue
        result[name] = {item["id"] for _, item in iter_items(path)}
    return result


def partition_summary(all_rows, splits_dir):
    """按分区统计**全量**路由（TRAINING.md §4.2 / §4.6 的可复算来源）。

    分区 id 来自 data/splits；中文补充不在语料里、不参与；落盘件只含公开三区（§1.1）。
    不写盘、不读 sidecar——直接对全量行分组。
    """
    result = {}
    for name, ids in split_partition_ids(splits_dir).items():
        if ids is None:
            result[name] = None
            continue
        subset = [row for row in all_rows if row["item_id"] in ids]
        routes = Counter(row["training_route"] for row in subset)
        result[name] = {
            "corpus_items": len({row["item_id"] for row in subset}),
            "targets": len(subset),
            "drop": routes.get("drop", 0),
            "classification": routes.get("classification", 0),
            "distillation": routes.get("distillation", 0),
            "keep": len(subset) - routes.get("drop", 0),
            "calibration_reference": sum(1 for row in subset
                                         if row["calibration_role"] == "reference_probability"),
            "label_trust": dict(Counter(row["label_trust"] for row in subset).most_common()),
            "target_type": dict(Counter(row["target_type"] for row in subset).most_common()),
        }
    # 全量（含保留集）总览：§0.2 的形态四分类与 §6.3 的逐规则计数由这里的 shape_class / rule_id 复算
    result["全量（含保留集）"] = summarize(all_rows)
    return result


# ------------------------------------------------------------------ 落盘与统计

def dump_row(row):
    """一行的规范序列化。

    键序排序（sort_keys）：已交付的 .gz 就是这个形态，重算才可能**逐字节**一致；
    顺带让 sha256 不依赖字段的书写顺序。分隔符用默认值（`", "` / `": "`）——同上，
    与交付件一致优先于省几百 KB（gzip 后差异可忽略）。
    """
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def render(rows):
    """渲染成明文（行序 = 语料顺序，确定性可复算）。"""
    return "".join(dump_row(row) + "\n" for row in rows)


def read_sidecar(path):
    """读旁挂文件明文。明文被 .gitignore 第 13 行挡住（派生大文件只提交 .gz），
    所以干净检出上退到同目录同名 .gz。返回 (文本, 实际路径)。"""
    plain = Path(path)
    if plain.is_file():
        return plain.read_text(encoding="utf-8"), plain
    packed = plain.with_suffix(".jsonl.gz")
    if packed.is_file():
        with gzip.open(packed, "rt", encoding="utf-8") as handle:
            return handle.read(), packed
    raise BackfillError(f"旁挂文件不存在：{plain}（也没有 {packed}）")


def write_sidecar(rows, path):
    """写旁挂文件，返回明文 sha256。"""
    payload = render(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def summarize(rows):
    """统计：target_type / rule / 覆盖 / shape / route / 角色 / 可信度 / 证据集。"""
    return {
        "targets": len(rows),
        "target_type": dict(Counter(row["target_type"] for row in rows).most_common()),
        "rule_id": {rid: sum(1 for row in rows if row["rule_id"] == rid) for rid in RULES},
        "shape_override": dict(Counter(row["shape_override"] for row in rows if row["shape_override"]).most_common()),
        "shape_class": {s: sum(1 for row in rows if row["shape_class"] == s) for s in SHAPE_CLASSES},
        "training_route": dict(Counter(row["training_route"] for row in rows).most_common()),
        "target_type_basis": dict(Counter(row["target_type_basis"] for row in rows).most_common()),
        "calibration_role": dict(Counter(row["calibration_role"] for row in rows).most_common()),
        "label_trust": dict(Counter(row["label_trust"] for row in rows).most_common()),
        "mechanism_unknown": sum(1 for row in rows if row["mechanism_unknown"]),
        "provenance_ref_sets": dict(Counter("+".join(row["provenance_ref"]) for row in rows).most_common()),
    }


def self_check(rows, scan=None):
    """自检（**全量口径**）。只断言**可从数据推导或内部一致**的结论。

    为什么不再断言 v3 报告 §6.3 的数字：那是「上一份报告的结论」，不是能从数据独立推导的事实。
    硬编码它们会让每次换语料都失败（v4 合并后原值全体失效），和「测试里写死总数」是同一类脆弱点。

    - **断言（换语料仍然成立）**：classified + unregistered == scanned；未登记来源 == 0；
      每行字段 == RULES 的静态载荷（target_type 还要按 R12/R13 覆盖改判）；
      route == _training_route 复算；hard_label ⇔ 伪造 one-hot；全候选等值必须降级；
      rule_id / shape_class / shape_override 合法；每行有 provenance_ref。
    - **只报不判**（推导不出、需要人去 target-provenance.md 刷新）：§6.3 的分布基线、
      R12/R13 的具体条数。它们在 summarize() 里照常输出，供文档对照。
    """
    problems = []
    scan = scan or {}
    classified = len(rows)
    scanned = scan.get("scanned_targets")
    unregistered = scan.get("unregistered_targets", 0)
    if scanned is not None and classified + unregistered != scanned:
        problems.append(f"classified {classified} + unregistered {unregistered} != scanned {scanned}")
    if unregistered:
        detail = ", ".join(f"{slug}×{count}" for slug, count
                           in (scan.get("unregistered_sources") or {}).most_common(5))
        problems.append(f"{unregistered} 个 target 属于未登记来源（{detail}）：先在 RULES 里补规则、"
                        "在 target-provenance.md 补证据，否则旁挂件会静默缺行")

    shapes = Counter(row["shape_class"] for row in rows)
    counts = Counter(row["target_type"] for row in rows)
    if sum(shapes.values()) != classified:
        problems.append("形态桶合计不等于 target 总数")
    if counts.get("hard_label", 0) != shapes.get("onehot_fabricated", 0):
        problems.append(f"hard_label {counts.get('hard_label', 0)} != point_mass 伪造 one-hot "
                        f"{shapes.get('onehot_fabricated', 0)}")

    bad = Counter()
    source_uniform = overrides = 0
    for row in rows:
        payload = RULES.get(row["rule_id"])
        if payload is None or row["rule_id"] in OVERRIDE_RULES:
            bad["rule_id 不是来源规则表里的规则号"] += 1
            continue
        if row["shape_class"] not in SHAPE_CLASSES:
            bad["shape_class 越界"] += 1
        if row["shape_override"] not in (None,) + OVERRIDE_RULES:
            bad["shape_override 不是 R12/R13/null"] += 1
        expected_type = "uninformative_uniform" if row["shape_override"] else payload["target_type"]
        if row["target_type"] != expected_type:
            bad["target_type 与规则表/形态覆盖不符"] += 1
        if row["target_type_basis"] != ("shape" if row["shape_override"] else "source"):
            bad["target_type_basis 与覆盖状态不符"] += 1
        for field, want in (("distribution_semantics", payload.get("distribution_semantics", "none")),
                            ("calibration_role", payload.get("calibration_role")),
                            ("label_trust", payload.get("label_trust")),
                            ("semantics_confidence", payload.get("semantics_confidence")),
                            ("mechanism_unknown", payload.get("mechanism_unknown", False))):
            if row[field] != want:
                bad[f"{field} 与规则表载荷不符"] += 1
        if row["provenance_ref"] != list(payload.get("refs", [])):
            bad["provenance_ref 与规则表证据不符"] += 1
        if not row["provenance_ref"]:
            bad["缺少 provenance_ref"] += 1
        if row["training_route"] != _training_route(row["target_type"], row["shape_class"]):
            bad["training_route 与 _training_route 复算不符"] += 1
        if row["shape_class"] == "uniform_all_candidates" and row["target_type"] != "uninformative_uniform":
            bad["全候选等值没有降级成 uninformative_uniform"] += 1
        overrides += 1 if row["shape_override"] else 0
        if not row["shape_override"] and payload["target_type"] == "uninformative_uniform":
            source_uniform += 1

    if counts.get("uninformative_uniform", 0) != source_uniform + overrides:
        problems.append(f"uninformative_uniform {counts.get('uninformative_uniform', 0)} != "
                        f"来源规则直接判的 {source_uniform} + 形态覆盖 {overrides}")
    for what, count in bad.most_common(10):
        problems.append(f"{count} 行：{what}")
    return problems


# ------------------------------------------------------------------ CLI

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="语料 JSONL（默认仓内 items.final.jsonl）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="旁挂文件输出路径")
    parser.add_argument("--splits", type=Path, default=DEFAULT_SPLITS,
                        help="分区目录：只落盘 train/test/validation 里的 target（默认 data/splits）")
    parser.add_argument("--verify", action="store_true", help="只校验：重算结果与已落盘文件逐字节一致，不写盘")
    parser.add_argument("--skip-self-check", action="store_true",
                        help="跳过全量自检（自检只保留可推导断言；逃生口用于语料结构大改时先落盘再排查）")
    parser.add_argument("--gz-out", type=Path, default=None,
                        help="同时写一份 gzip（mtime=0，逐字节可复现；交付件 data/target-types.jsonl.gz）")
    parser.add_argument("--by-split", action="store_true",
                        help="额外输出各分区的全量路由 / 校准 / label_trust 分层"
                             "（TRAINING.md §4.2 / §4.6 的复算来源；不写盘）")
    args = parser.parse_args()

    try:
        # 先取白名单：分区不在就立刻退出，不白扫一遍语料
        public_ids, public_keys = load_public_partitions(args.splits)
        all_rows, scan_stats = build_all_rows(args.input)
        problems = [] if args.skip_self_check else self_check(all_rows, scan_stats)
        if problems:
            for problem in problems:
                print(f"自检失败：{problem}", file=sys.stderr)
            return 2
        rows = public_rows(all_rows, public_ids)
        check_coverage(rows, all_rows, public_keys)   # 名单内一条不漏、名单外一条不写
        withheld = len(all_rows) - len(rows)
        summary = summarize(rows)
        summary["scanned_targets"] = scan_stats["scanned_targets"]
        summary["classified_targets"] = len(all_rows)
        summary["unregistered_targets"] = scan_stats["unregistered_targets"]
        summary["unregistered_items"] = scan_stats["unregistered_items"]
        summary["unregistered_sources"] = dict(scan_stats["unregistered_sources"].most_common())
        summary["public_targets"] = len(rows)
        summary["non_public_targets_not_written"] = withheld
        if args.by_split:
            summary["partitions"] = partition_summary(all_rows, args.splits)
            summary["partitions_note"] = ("按 data/splits 分区统计**全量**路由；中文补充不在语料里、"
                                          "不参与；落盘件只含公开三区（TRAINING.md §1.1）")
        if args.verify:
            actual, path = read_sidecar(args.out)
            if actual != render(rows):
                print(f"自检失败：{path} 与重算结果不一致（语料、规则或公开分区变了）", file=sys.stderr)
                return 2
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"# OK：{path} 与重算逐行一致（扫描 {len(all_rows):,} / 落盘 {len(rows):,}；"
                  f"非公开分区 {withheld:,} 条未落盘）")
            return 0
        digest = write_sidecar(rows, args.out)
        if args.gz_out is not None:
            payload = render(rows)
            args.gz_out.parent.mkdir(parents=True, exist_ok=True)
            with open(args.gz_out, "wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
                    handle.write(payload.encode("utf-8"))
            print(f"# 同时写 gzip：{args.gz_out}（mtime=0，逐字节可复现）")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"# 落盘 {args.out}：公开分区 {len(rows):,} 行；非公开分区 {withheld:,} 行未落盘，"
              f"其路由信息仓外维护（TRAINING.md §1.1）")
        print(f"# 明文 sha256 {digest}")
        return 0
    except BackfillError as error:
        print(f"回填失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
