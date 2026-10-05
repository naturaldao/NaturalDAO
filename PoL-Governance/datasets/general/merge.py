#!/usr/bin/env python3
r"""合并最终语料：英文原生四元组 + 中文侧（按变体规则抽样）。

规格（Lead 2026-10-05 裁定）
---------------------------
- 英文侧：data/items.native.jsonl 全量（15,983 条）
- 中文侧：D:\pol2-raw\zh-final\items.zh.jsonl（22,372 条 / 5,454 个唯一请求）
    1. 每个 group 先取 variant_index == 0 的那一条；
    2. 不足目标条数时，按 sha256(seed + group_id) 升序，为 group 追加 variant_index == 1 的那一条；
    3. seed 固定并写进报告，保证可复算。
- 目标中文占比 33%（不是 40%）：Deepexi 是唯一中文来源，中文占比 = 该来源占比；取到 40% 会正好
  顶满"单一来源 ≤40%"而没有余量，而多取的变体来自同一批请求、信息量递减，33% 留出后续第二个
  中文来源的头寸。

两条硬要求
----------
1. 中文侧显式 group_id（顶层 + source + meta 三处，另有 request_id）**不得重写或丢弃**——切分器
   靠它把同一请求的变体整组分配，丢了就静默泄漏。
2. 中文侧候选顺序**已被确定性打散**（修正了"最后一位几乎从不是答案"的位置偏置）。本脚本只做
   "挑哪几行"，**逐行原样复制**（不做 json 往返序列化），因此不可能把顺序或任何字段改回去。

用法
----
    uv run --no-project --offline python datasets/general/merge.py \
        --en datasets/general/data/items.native.jsonl \
        --zh D:\pol2-raw\zh-final\items.zh.jsonl \
        --out datasets/general/data/items.final.jsonl \
        --report datasets/general/data/items.final.report.json \
        --report-md datasets/general/merge-report.md --share 0.33 --gzip
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import shutil
import sys
from pathlib import Path

DEFAULT_SEED = "general-merge-v1"
DEFAULT_SHARE = 0.33


def read_lines(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield line.rstrip("\n")


def variant_index(item) -> int:
    meta = item.get("meta") or {}
    if "variant_index" in meta:
        return int(meta["variant_index"])
    return 0


def group_key(item, fallback: str) -> str:
    for candidate in (item.get("group_id"), (item.get("meta") or {}).get("group_id"),
                      (item.get("source") or {}).get("group_id")):
        if candidate:
            return str(candidate)
    return fallback


def order_key(seed: str, group: str) -> str:
    return hashlib.sha256(f"{seed}|{group}".encode("utf-8")).hexdigest()


def write_lines(path: Path, lines) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    count, digest = 0, hashlib.sha256()
    with path.open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
            count += 1
    return {"path": str(path), "records": count, "bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def write_gzip(source: Path, target: Path) -> dict:
    with source.open("rb") as fin, gzip.GzipFile(target, "wb", compresslevel=9, mtime=0) as fout:
        shutil.copyfileobj(fin, fout)
    return {"path": str(target), "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def select_zh(lines, target: int, seed: str):
    """按规格挑中文行：先每个 group 的 variant 0，再按 sha256(seed+group) 升序补 variant 1。"""
    by_group = {}
    order = []
    for line in lines:
        item = json.loads(line)
        group = group_key(item, f"line:{len(order)}")
        if group not in by_group:
            by_group[group] = {"lines": {}, "order": len(order)}
            order.append(group)
        by_group[group]["lines"][variant_index(item)] = line

    chosen = []
    for group in order:
        entry = by_group[group]["lines"].get(0)
        if entry is not None:
            chosen.append((group, 0, entry))
    if len(chosen) < target:
        ranked = sorted((group for group in order if 1 in by_group[group]["lines"]),
                        key=lambda group: order_key(seed, group))
        for group in ranked:
            if len(chosen) >= target:
                break
            chosen.append((group, 1, by_group[group]["lines"][1]))
    stats = {
        "zh_available_items": sum(len(entry["lines"]) for entry in by_group.values()),
        "zh_total_groups": len(order),
        "zh_groups_with_variant_1": sum(1 for group in order if 1 in by_group[group]["lines"]),
        "zh_taken_variant_0": sum(1 for _, variant, _ in chosen if variant == 0),
        "zh_taken_variant_1": sum(1 for _, variant, _ in chosen if variant == 1),
        "zh_unique_groups_taken": len({group for group, _, _ in chosen}),
    }
    return chosen, stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="合并英文原生四元组与中文侧（变体抽样）")
    parser.add_argument("--en", type=Path, required=True)
    parser.add_argument("--zh", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--report-md", type=Path)
    parser.add_argument("--share", type=float, default=DEFAULT_SHARE, help="目标中文占比（默认 0.33）")
    parser.add_argument("--seed", default=DEFAULT_SEED, help="变体抽取种子（固定后才可复算）")
    parser.add_argument("--gzip", action="store_true")
    args = parser.parse_args(argv)

    en_lines = list(read_lines(args.en))
    zh_lines = list(read_lines(args.zh))
    if not en_lines or not zh_lines:
        print("错误：英文或中文侧为空", file=sys.stderr)
        return 1
    target_zh = round(len(en_lines) * args.share / (1.0 - args.share))
    chosen, zh_stats = select_zh(zh_lines, target_zh, args.seed)

    en_ids = {json.loads(line)["id"] for line in en_lines}
    zh_ids = {json.loads(line)["id"] for _, _, line in chosen}
    collisions = sorted(en_ids & zh_ids)

    def profile(pairs):
        domains, langs, with_targets, groups, ids = collections.Counter(), collections.Counter(), 0, set(), set()
        for line in pairs:
            item = json.loads(line)
            domains[item.get("domain")] += 1
            langs[item.get("lang")] += 1
            if item.get("targets"):
                with_targets += 1
            ids.add(item["id"])
            for candidate in (item.get("group_id"), (item.get("meta") or {}).get("group_id")):
                if candidate:
                    groups.add(str(candidate))
                    break
        return {"items": len(pairs), "domains": dict(domains), "langs": dict(langs),
                "with_targets": with_targets,
                "target_rate": round(with_targets / len(pairs), 4) if pairs else 0.0,
                "groups": len(groups), "unique_ids": len(ids)}

    zh_chosen_lines = [line for _, _, line in chosen]
    ordered = en_lines + zh_chosen_lines
    written = write_lines(args.out, ordered)
    result = {
        "en": profile(en_lines), "zh": profile(zh_chosen_lines), "final": profile(ordered),
        "zh_share": round(len(zh_chosen_lines) / len(ordered), 4),
        "target_zh": target_zh, "seed": args.seed, "requested_share": args.share,
        "id_collisions": collisions[:20], "zh_selection": zh_stats,
        "zh_source_share_note": "Deepexi 是唯一中文来源，因此中文占比即该来源占比；"
                                "取 33% 而非 40%，是给'单一来源 ≤40%'留余量，"
                                "且多取的变体来自同一批请求、边际信息量递减。",
    }
    if args.gzip:
        result["gzip"] = write_gzip(args.out, args.out.with_suffix(args.out.suffix + ".gz"))
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report_md:
        args.report_md.write_text(markdown_report(result), encoding="utf-8")
    print(json.dumps({"items": len(ordered), "en": len(en_lines), "zh": len(zh_chosen_lines),
                      "zh_share": result["zh_share"], "target_zh": target_zh,
                      "collisions": len(collisions)}, ensure_ascii=False))
    return 0 if not collisions else 2


def markdown_report(result: dict) -> str:
    en, zh, final = result["en"], result["zh"], result["final"]
    lines = [
        "# 最终语料合并报告（items.final）",
        "",
        f"- 英文侧：data/items.native.jsonl 全量 **{en['items']:,} 条**",
        f"- 中文侧：D:\\pol2-raw\\zh-final\\items.zh.jsonl 按变体规则抽取 **{zh['items']:,} 条**",
        f"- 合计 **{final['items']:,} 条**，**中文占比 {result['zh_share'] * 100:.2f}%**"
        f"（目标 {result['requested_share'] * 100:.0f}%，目标条数 {result['target_zh']:,}）",
        f"- 抽取种子：**{result['seed']}**（按 sha256(seed + group_id) 升序补 variant 1，可复算）",
        f"- id 冲突：{len(result['id_collisions'])}",
        "",
        "## 中文侧怎么取的",
        "",
        "| 步骤 | 规则 | 条数 |",
        "|---|---|---:|",
        f"| 1 | 每个 group 取 variant_index = 0 | {result['zh_selection']['zh_taken_variant_0']:,} |",
        f"| 2 | 不足目标时按 sha256(seed + group_id) 升序补 variant_index = 1 | "
        f"{result['zh_selection']['zh_taken_variant_1']:,} |",
        f"| 合计 | 覆盖 {result['zh_selection']['zh_unique_groups_taken']:,} 个唯一请求"
        f"（共 {result['zh_selection']['zh_total_groups']:,} 个） | {zh['items']:,} |",
        "",
        "## 为什么取 33% 而不是 40%",
        "",
        result["zh_source_share_note"],
        "",
        "## 分布",
        "",
        "| | 英文 | 中文 | 合计 |",
        "|---|---:|---:|---:|",
        f"| 条数 | {en['items']:,} | {zh['items']:,} | {final['items']:,} |",
        f"| 带真值 | {en['with_targets']:,}（{en['target_rate'] * 100:.1f}%） | "
        f"{zh['with_targets']:,}（{zh['target_rate'] * 100:.1f}%） | "
        f"{final['with_targets']:,}（{final['target_rate'] * 100:.1f}%） |",
        f"| 语言 | {en['langs']} | {zh['langs']} | — |",
        f"| 显式 group 数 | {en['groups']:,} | {zh['groups']:,} | — |",
        "",
        "域分布（合计）：",
        "",
        "| domain | 条数 |",
        "|---|---:|",
    ]
    for domain, count in sorted(final["domains"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {domain} | {count:,} |")
    lines += [
        "",
        "## 两条硬要求怎么保证的",
        "",
        "1. **group_id 原样保留**：合并脚本只做「挑哪几行」，逐行原样复制，不做 JSON 往返序列化；"
        "中文侧顶层 group_id / request_id、source.group_id、meta.group_id 全部原封不动。",
        "2. **候选顺序不被改回**：同样因为逐行复制，中文侧已确定性打散的候选顺序（含 "
        "meta.target_position 与 meta.original_target_position 的差异）原样保留。",
        "",
        "## 复算",
        "",
        "    uv run --no-project --offline python datasets/general/merge.py " + "\\",
        "        --en datasets/general/data/items.native.jsonl " + "\\",
        "        --zh D:\\pol2-raw\\zh-final\\items.zh.jsonl " + "\\",
        "        --out datasets/general/data/items.final.jsonl --share 0.33 --seed " + result["seed"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
