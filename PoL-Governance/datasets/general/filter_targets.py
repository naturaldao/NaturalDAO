"""训练侧过滤与路由：把 target-types.jsonl 的路由落成可复跑的过滤清单与分区统计。

用法::

    uv run --no-project --offline python datasets/general/filter_targets.py
    uv run --no-project --offline python datasets/general/filter_targets.py --ties distill
    uv run --no-project --offline python datasets/general/filter_targets.py --json

读：datasets/general/data/target-types.jsonl（旁挂路由）+ data/splits/*.jsonl + 中文补充（只读）。
写：默认只打印统计（stdout）；--emit 时才写一个聚合 JSON（**只含计数，不含样本、不含 id 清单**）。

旁挂文件只含**公开分区**（train/test/validation）：内部保留集 benchmark 的成员身份本身就是敏感信息，
它的路由在仓外维护。本工具按同一条线分开算：

- 公开分区：covered（旁挂文件给了路由）+ uncovered（旁挂没覆盖、按形态兜底——中文补充就是这一类）。
  covered 合计必须恰好等于旁挂文件行数（少 = 有 target 没路由，多 = 路由指认了不存在的 target）。
- 内部保留集：**不做兜底估算**。把它当「中文补充」那样估，会给出一个看起来合理的错数字，
  而且是静默的；这里只回答「旁挂文件有没有覆盖到它」，答案必须是 0，不为 0 直接报错。

三条路由：

- drop           剔除：uninformative_uniform（无信息均匀 / yuri_v1 常量 / 并列均分占位）
- classification 分类损失（硬标签）：我们伪造的 one-hot、来源自带的退化 one-hot、answer_only
- distillation   软蒸馏目标（**不用于校准**）：真·非退化 soft 分布

--ties 决定那 232 条「并列均分」怎么走（报告 §5 结论 3 建议一并剔除；用户任务书按形态四分类
把它们算在 7,520 里）：

- drop     默认，按报告 §5
- distill  按用户任务书字面，并入蒸馏目标

**不写盘、不改语料**：过滤以「旁挂路由 + 训练视图」交付，原语料字节不变、划分不动。
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "datasets/general/data"
DEFAULT_SIDECAR = DATA / "target-types.jsonl"
DEFAULT_SPLITS = DATA / "splits"
DEFAULT_SUPPLEMENT = DATA / "zh-supplement/items.jsonl"
#: 公开分区：旁挂文件只覆盖它们，兜底路由也只在这里估。
PUBLIC_SCANS = ("train", "test", "validation")
#: 内部保留集：单独算，不参与兜底估算。文件被 .gitignore 第 15 行挡在仓外（单独交付）。
SEALED_SPLIT = "benchmark"
ROUTES = ("drop", "classification", "distillation")


class FilterError(Exception):
    """输入或口径不可用。"""


def iter_items(path):
    """逐行读 JSONL（支持 .gz）。"""
    source = Path(path)
    if not source.is_file():
        raise FilterError(f"输入不存在：{source}")
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def resolve_sidecar(path):
    """明文优先；干净检出上没有明文（.gitignore 挡住大体积派生文件），退到同名 .gz。"""
    plain = Path(path)
    if plain.is_file():
        return plain
    packed = plain.with_suffix(".jsonl.gz")
    return packed if packed.is_file() else plain


def load_sidecar(path):
    """读旁挂路由：(item_id, question_key) -> 行。"""
    rows = {}
    for row in iter_items(path):
        key = (row["item_id"], row["question_key"])
        if key in rows:
            raise FilterError(f"旁挂文件连接键重复：{key}")
        rows[key] = row
    return rows


def route_of(row, ties):
    """按 --ties 口径取路由。"""
    if ties == "distill" and row.get("shape_override") == "R13":
        return "distillation"
    return row["training_route"]


def route_of_uncovered(item, question, target):
    """旁挂文件没覆盖的 target（中文补充只在 train 尾追加，不在冻结语料里）：按其自身形态路由。"""
    probs = target.get("probs")
    if probs is None:
        return "classification"
    values = [float(v) for v in probs.values()]
    if values and max(values) - min(values) < 1e-9:
        return "drop"
    return "distillation"


def resolve_split(split_dir, split):
    """分区文件：明文优先，干净检出退到同名 .gz（明文被 .gitignore 第 17 行挡住）；都没有返回 None。"""
    plain = Path(split_dir) / f"{split}.jsonl"
    if plain.is_file():
        return plain
    packed = plain.with_suffix(".jsonl.gz")
    return packed if packed.is_file() else None


def scan_split(split_dir, split, sidecar, ties):
    """扫一个**公开**分区，分开统计「旁挂文件给了路由的 target」与「旁挂未覆盖、按形态兜底的 target」。"""
    frozen, uncovered = Counter(), Counter()
    per_type, per_rule = Counter(), Counter()
    path = resolve_split(split_dir, split)
    if path is None:
        raise FilterError(f"分区文件不存在：{Path(split_dir) / (split + '.jsonl')}（也没有 .gz）")
    for item in iter_items(path):
        targets = item.get("targets") or {}
        for question in item.get("questions") or []:
            target = targets.get(question.get("key"))
            if target is None:
                continue
            row = sidecar.get((item["id"], question["key"]))
            if row is None:
                uncovered[route_of_uncovered(item, question, target)] += 1
            else:
                frozen[route_of(row, ties)] += 1
                per_type[row["target_type"]] += 1
                per_rule[row["rule_id"]] += 1
    return frozen, uncovered, per_type, per_rule


def count_sealed(split_dir, split, sidecar):
    """内部保留集：只回答「旁挂文件有没有覆盖到它」，**不**按形态兜底估算路由。

    兜底估算在公开分区是对的（中文补充确实没进旁挂文件），用在保留集上却是**静默错误**：
    它会把保留集的 target 报成一份看起来合理的路由分布，谁也发现不了不对。
    返回 None = 保留集不在本机（.gitignore 第 15 行：单独交付，不入公开仓）。
    """
    path = resolve_split(split_dir, split)
    if path is None:
        return None
    targets = covered = 0
    for item in iter_items(path):
        item_targets = item.get("targets") or {}
        for question in item.get("questions") or []:
            if item_targets.get(question.get("key")) is None:
                continue
            targets += 1
            covered += (item["id"], question["key"]) in sidecar
    return {"file": path.name, "targets": targets, "covered": covered}


def _row(label, counts, width=12):
    total = sum(counts.values())
    drop = counts.get("drop", 0)
    return (f"{label:<{width}}{total:>12,}{drop:>10,}{counts.get('classification', 0):>10,}"
            f"{counts.get('distillation', 0):>10,}{total - drop:>12,}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    parser.add_argument("--splits", type=Path, default=DEFAULT_SPLITS)
    parser.add_argument("--supplement", type=Path, default=DEFAULT_SUPPLEMENT)
    parser.add_argument("--ties", choices=("drop", "distill"), default="drop",
                        help="232 条并列均分怎么走：drop（默认，报告 §5）/ distill（用户任务书字面）")
    parser.add_argument("--json", action="store_true", help="同时打印机器可读 JSON")
    parser.add_argument("--emit", type=Path, help="把聚合计数写成 JSON（只含计数）")
    args = parser.parse_args()

    try:
        sidecar = load_sidecar(resolve_sidecar(args.sidecar))
        print(f"# 训练视图（--ties {args.ties}）：旁挂 {len(sidecar):,} 条路由；只读，不改语料、不动划分")
        print()
        header = f"{'分区':<12}{'target 合计':>12}{'剔除':>10}{'分类损失':>10}{'蒸馏目标':>10}{'过滤后保留':>12}"
        rule = "-" * 66
        report = {"schema": "pol-training-view/0.1", "ties": args.ties,
                  "sidecar_rows": len(sidecar), "splits": {}}
        frozen_total = Counter()
        print(f"# A. 公开分区（{'/'.join(PUBLIC_SCANS)}）：旁挂文件 {len(sidecar):,} 行，覆盖公开 target 100%"
              f"；内部保留集见 D，其路由在仓外维护（TRAINING.md §1.1）")
        print(header)
        print(rule)
        for split in PUBLIC_SCANS:
            frozen, uncovered, per_type, per_rule = scan_split(args.splits, split, sidecar, args.ties)
            frozen_total.update(frozen)
            report["splits"][split] = {
                "targets": sum(frozen.values()),
                "drop": frozen.get("drop", 0),
                "classification": frozen.get("classification", 0),
                "distillation": frozen.get("distillation", 0),
                "keep": sum(frozen.values()) - frozen.get("drop", 0),
                "uncovered_targets": sum(uncovered.values()),
                "target_type": dict(per_type.most_common()),
                "rule_id": dict(sorted(per_rule.items())),
            }
            print(_row(split, frozen))
        print(rule)
        print(_row("公开合计", frozen_total))
        print()
        # 覆盖关系推导，不写死总数：旁挂文件的每一行都必须落在公开分区里，且一条不漏
        if sum(frozen_total.values()) != len(sidecar):
            raise FilterError(
                f"公开分区只扫到 {sum(frozen_total.values()):,} 条旁挂路由，旁挂文件却有 {len(sidecar):,} 行："
                "覆盖关系断了（少 = 有 target 没路由；多 = 有路由指认了不存在的 target）")

        # 中文补充：只追加进 train 尾部，不在冻结语料 / 旁挂文件里。
        supplement_items = 0
        supplement = Counter()
        if Path(args.supplement).is_file():
            for item in iter_items(args.supplement):
                supplement_items += 1
                for question in item.get("questions") or []:
                    target = (item.get("targets") or {}).get(question.get("key"))
                    if target is not None:
                        supplement[route_of_uncovered(item, question, target)] += 1
        supplement_total = sum(supplement.values())
        report["supplement"] = {"items": supplement_items, "targets": supplement_total,
                                "routes": dict(supplement.most_common())}
        print(f"# B. 中文补充（split-manifest 记的 train-only 追加）：{supplement_items:,} 条 / "
              f"{supplement_total:,} target，全部 answer_only -> classification")
        print()

        train = report["splits"]["train"]
        combined = Counter(frozen_total)
        combined.clear()
        for route in ROUTES:
            combined[route] = train.get(route, 0) + supplement.get(route, 0)
        report["train_jsonl_actual"] = {
            "targets": sum(combined.values()),
            "drop": combined.get("drop", 0),
            "classification": combined.get("classification", 0),
            "distillation": combined.get("distillation", 0),
            "keep": sum(combined.values()) - combined.get("drop", 0),
        }
        print(f"# C. train.jsonl 实际内容 = 公开 train {train.get('targets', 0):,} + 补充 "
              f"{supplement_total:,} = {sum(combined.values()):,} target")
        print(header)
        print(rule)
        print(_row("train 实际", combined))
        print()

        sealed = count_sealed(args.splits, SEALED_SPLIT, sidecar)
        if sealed is None:
            print(f"# D. 内部保留集（{SEALED_SPLIT}.jsonl）不在本机（.gitignore 第 15 行）：跳过覆盖检查")
        else:
            report["sealed"] = sealed
            print(f"# D. 内部保留集（{sealed['file']}）：{sealed['targets']:,} target，旁挂文件覆盖 "
                  f"{sealed['covered']} 条——必须为 0；保留集不做兜底路由估算")
            if sealed["covered"]:
                raise FilterError(f"旁挂文件覆盖了内部保留集 {sealed['covered']} 条 target："
                                  "旁挂件只许含公开分区")
        print()

        reasons = Counter()
        for row in sidecar.values():
            if route_of(row, args.ties) != "drop":
                continue
            if row["shape_override"] == "R12":
                reasons["R12 全候选等值（无信息均匀）"] += 1
            elif row["shape_override"] == "R13":
                reasons["R13 并列均分占位（open-jev / openjev_v2）"] += 1
            else:
                reasons[f"{row['rule_id']} yuri_v1 整条子流常量 [0.5, 0.5]"] += 1
        report["drop_reasons"] = dict(reasons.most_common())
        print("# 剔除理由计数（旁挂文件 = 公开分区）：")
        for reason, count in reasons.most_common():
            print(f"#   {reason}: {count:,}")
        print(f"#   合计: {sum(reasons.values()):,}")
        print()

        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.emit:
            Path(args.emit).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"# 已写聚合视图 {args.emit}（只含计数）")
        return 0
    except FilterError as error:
        print(f"过滤失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
