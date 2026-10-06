"""target 语义回填（旁挂）：按 target-provenance.md §6 的 R1-R13 给每个 target 标注语义与训练用途。

用法::

    uv run --no-project --offline python datasets/general/target_types.py             # 生成 + 自检
    uv run --no-project --offline python datasets/general/target_types.py --verify    # 只校验：重算结果与已落盘逐行一致
    uv run --no-project --offline python datasets/general/target_types.py \
        --input "D:/pol2-raw/general-private/data/items.final.jsonl.gz"               # 直接读冻结语料

输入（只读，不改）：默认 datasets/general/data/items.final.jsonl。它就是冻结语料
D:/pol2-raw/general-private/data/items.final.jsonl.gz（sha256 ba615c96...daece）的解压同名文件：
23,855 条 / 31,786 个 target，逐条 JSON 规范化后 sha256 完全一致。
输出：datasets/general/data/target-types.jsonl —— 每条 target 一行，旁挂文件，原语料一个字节都不动。

判定纪律（报告 §6.1）：

1. 先判来源证据：source.slug -> meta.native_source -> meta.native_task + 问题键 ->
   meta.quality_flags。这些都是转换时由代码按来源字段写下的。
2. 数值形态只出现在两处：(a) 作为 target_type 的降级候选（最多降成 uninformative_uniform，
   绝不把向量判成某个语义）；(b) shape_note 旁证字段，消费者可忽略。凡用到形态的判定，
   target_type_basis 写 shape 而不是 source。
3. 不猜：规则表覆盖全部 target，未命中即报错退出。

字段：报告 §6.2 的 9 个字段 + 本任务新增的 3 个旁挂字段（见 TRAINING.md §2）：

- rule_id        命中的**来源证据**规则号 R1-R11，便于与报告 §6.3 逐行对账
- shape_override 形态覆盖规则号 R12 / R13 / null（覆盖只降级 target_type，不改语义）
- shape_class    target 的形态桶（旁证）：answer_only / onehot_fabricated / onehot_native /
                 soft / uniform_all_candidates / tie_subset
- training_route 训练侧路由：drop / classification / distillation

自检（不通过就非零退出）：合计 31,786；四类分布与报告 §6.3 一致；
逐规则计数与 §6.3 一致；hard_label 与旗标 hard_label_to_point_mass 等价。
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

#: 冻结语料指纹（仅在文档里引用；明文与 .gz 逐条一致，允许在仓内明文上复算）。
FROZEN_GZ_SHA256 = "ba615c96c0dc13cbc4caa8b0f83ac1326abc13700bde98579f2ebb9f38bdaece"
EXPECTED_TARGETS = 31_786

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

#: 报告 §6.3 的自检基准：target_type 四类。
EXPECTED_TARGET_TYPE = {
    "hard_label": 5_488,
    "soft_distribution": 15_919,
    "uninformative_uniform": 1_962,
    "answer_only": 8_417,
}

#: 报告 §6.3 的自检基准：逐规则命中数（R1-R11，全部是来源证据规则）。
#: R12/R13 是**覆盖规则**，单独计：它们不改 distribution_semantics / calibration_role /
#: label_trust（全部继承源规则），只把 target_type 降级成 uninformative_uniform。
#: 因此「源规则计数 + 覆盖计数」才等于 §6.3 那张表。
EXPECTED_RULE_HITS = {
    "R1": 4_009, "R2": 1_479, "R3": 7_872, "R4": 545, "R5": 432, "R6": 3_714,
    "R7": 4_479, "R8": 757, "R9": 5_378, "R10": 1_621, "R11": 1_500,
}

#: 报告 §6.3 的自检基准：形态覆盖规则命中数。
EXPECTED_SHAPE_OVERRIDE = {"R12": 109, "R13": 232}

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
}


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
    """给一个 target 产出旁挂行。"""
    slug = item["source"]["slug"]
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


def build_rows(path):
    """遍历语料，产出全部旁挂行；顺带做结构自检。"""
    seen = set()
    rows = []
    for lineno, item in iter_items(path):
        targets = item.get("targets") or {}
        for question in item.get("questions") or []:
            key = question.get("key")
            target = targets.get(key)
            if target is None:
                continue
            row = classify_target(item, question, target)
            ident = (row["item_id"], row["question_key"])
            if ident in seen:
                raise BackfillError(f"{path}:{lineno} 连接键 (item_id, question_key) 重复：{ident}")
            seen.add(ident)
            rows.append(row)
    return rows


# ------------------------------------------------------------------ 落盘与统计

def dump_row(row):
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))


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


def self_check(rows):
    """自检。返回问题列表（空 = 通过）。"""
    problems = []
    if len(rows) != EXPECTED_TARGETS:
        problems.append(f"target 合计 {len(rows)} != {EXPECTED_TARGETS}")
    counts = Counter(row["target_type"] for row in rows)
    for name, want in EXPECTED_TARGET_TYPE.items():
        if counts.get(name, 0) != want:
            problems.append(f"target_type {name} = {counts.get(name, 0)} != 报告 §6.3 的 {want}")
    hits = Counter(row["rule_id"] for row in rows)
    for rid, want in EXPECTED_RULE_HITS.items():
        if hits.get(rid, 0) != want:
            problems.append(f"规则 {rid} 命中 {hits.get(rid, 0)} != 报告 §6.3 的 {want}")
    overrides = Counter(row["shape_override"] for row in rows if row["shape_override"])
    for rid, want in EXPECTED_SHAPE_OVERRIDE.items():
        if overrides.get(rid, 0) != want:
            problems.append(f"覆盖规则 {rid} 命中 {overrides.get(rid, 0)} != 报告 §6.3 的 {want}")
    fabricated = sum(1 for row in rows if row["shape_class"] == "onehot_fabricated")
    if counts.get("hard_label", 0) != fabricated:
        problems.append(f"hard_label {counts.get('hard_label', 0)} != point_mass 伪造 one-hot {fabricated}")
    if sum(overrides.values()) != 341:
        problems.append(f"R12+R13 = {sum(overrides.values())} != 341")
    shapes = Counter(row["shape_class"] for row in rows)
    if sum(shapes.values()) != EXPECTED_TARGETS:
        problems.append("形态桶合计不等于 target 总数")
    if shapes.get("onehot_fabricated", 0) + shapes.get("onehot_native", 0) != 14_119:
        problems.append("伪 one-hot 合计 != 14,119")
    refs_unknown = [row for row in rows if not row["provenance_ref"]]
    if refs_unknown:
        problems.append(f"{len(refs_unknown)} 行没有 provenance_ref")
    return problems


# ------------------------------------------------------------------ CLI

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="语料 JSONL（默认仓内 items.final.jsonl）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="旁挂文件输出路径")
    parser.add_argument("--verify", action="store_true", help="只校验：重算结果与已落盘文件逐行一致，不写盘")
    args = parser.parse_args()

    try:
        rows = build_rows(args.input)
        problems = self_check(rows)
        if problems:
            for problem in problems:
                print(f"自检失败：{problem}", file=sys.stderr)
            return 2
        summary = summarize(rows)
        if args.verify:
            actual, path = read_sidecar(args.out)
            if actual != render(rows):
                print(f"自检失败：{path} 与重算结果不一致（语料或规则变了）", file=sys.stderr)
                return 2
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"# OK：{path} 与重算逐行一致（{len(rows)} 行）")
            return 0
        digest = write_sidecar(rows, args.out)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"# 落盘 {args.out}")
        print(f"# 明文 sha256 {digest}")
        return 0
    except BackfillError as error:
        print(f"回填失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
