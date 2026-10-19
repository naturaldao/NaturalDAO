#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""候选接入准备（只接入、不合并）：tasksource/bigbench + allenai/cosmos_qa → general 契约候选语料。

定位
----
本脚本**不参与**现有四区划分、不改 items.final、不跑 split.py。它只做一件事：
把选型报告 datasets/general/capability-sources.md 推荐的 P1/P2 两个来源，按
datasets/general/CONTRACT.md 的字段契约转成**可直接合并的候选语料**，落在仓库外
D:\pol2-raw\capability-raw\，并给出质量门槛的逐条剔除计数与合并后构成预期。

- tasksource/bigbench（P1 数学与形式逻辑）：原生 multiple_choice_targets + multiple_choice_scores，
  apache-2.0，revision 210c156767d2f4f05d2f4fd0bb275017a67040fd，只取 train。
- allenai/cosmos_qa（P2 阅读理解与证据整合）：原生 4 选 1（answer0..3 + label），cc-by-4.0，
  HF revision 28d9d5e2aae025e73e11177891a88dba51190013（该 sha 的 loader 指向 GitHub 外链），
  实际数据字节固定到 GitHub 文件级 commit 8d4d7b40d0a027c6f6095f990c3809e9396a8e6f，只取 train。

与 convert.py 的关系
--------------------
条目形状**完全复用** convert.py 的 --native 路径（build_native_item / native_question /
item_id / option_key / native_item_errors），产物与 items.native.jsonl 同形，
合并时不需要第二套 schema。只有来源专属的解析、质量门槛与统计写在本文件里。

质量门槛（不达标即剔除并计数，见 --report）
------------------------------------------
1. state/prompt 为空、选项为空、选项数不在 [2, 16] → 剔除；
2. 答案必须在选项内：按折叠空白的规范化文本比对；
3. **答案唯一**：按规范化文本对选项去重后，仍被源标为正确的**不同**选项只能有一个。
   选项文本重复（bigbench geometric_shapes / reasoning_about_colored_objects 已知）
   在"重复项都不是答案"或"重复项就是同一个答案文本"时去重即可解决，去重计数进 quality_flags；
   只有当两个**不同**文本同时被判为正确时才剔除（answer_not_unique）。
4. 答案位置不得有系统偏置：按 item id 派生的确定性种子打散选项顺序，
   原位置与打散后位置都写进 meta，报告里给出打散前后的位置分布。
5. 只保留 train 划分（sources.json policy: 只取 train）。
6. 答案只写硬标签：targets[k] = {"answer": <option key>}，**不写 probs**。
   契约 1.3 禁止把单标签伪装成概率；convert.py 的 point_mass() 造的伪 one-hot 在这里明确不用。

用法
----
    # 1) 下载（stdlib urllib，固定 revision，写 sha256 到 _meta/fetch-manifest.json）
    uv run --no-project --offline python datasets/general/convert_capability.py fetch

    # 2) parquet -> rows.jsonl（需要 pyarrow；用仓外 venv 跑，仓库不引入第三方依赖）
    D:\pol2-raw\capability-raw\.venv\Scripts\python.exe datasets/general/convert_capability.py extract

    # 3) 转换 + 报告（stdlib）
    uv run --no-project --offline python datasets/general/convert_capability.py convert

    # 4) 合约校验（native_item_errors）与合并后构成预期
    uv run --no-project --offline python datasets/general/convert_capability.py verify
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import random
import sys
import urllib.request
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RAW_ROOT = Path(r"D:\pol2-raw\capability-raw")
DEFAULT_ITEMS = RAW_ROOT / "items.capability.jsonl"
DEFAULT_REPORT = RAW_ROOT / "capability-adoption.report.json"
DEFAULT_REJECTS = RAW_ROOT / "rejects.capability.jsonl"
FETCH_MANIFEST = RAW_ROOT / "_meta" / "fetch-manifest.json"

CONVERTER_NAME = "convert_capability.py"
CONVERTER_VERSION = "0.1"

#: 契约上限：taxonomy 模式是 16；原生模式契约为不设上限（实测最多 57），
#: 本轮按接入口径统一卡 2-16（超限只剔除、不改题，剔除量在报告里单列）。
MAX_OPTIONS = 16
MIN_OPTIONS = 2

#: 拆分收口：只取 train（sources.json policy.splits）
SPLIT = "train"

#: 空白的统一写法（避免源码里出现单反斜杠 u 转义）
LINE_BREAKS = (0x2028, 0x2029, 0x85)

# ------------------------------------------------------------------ 来源定义

BIGBENCH = {
    "slug": "bigbench",
    "dataset": "tasksource/bigbench",
    "revision": "210c156767d2f4f05d2f4fd0bb275017a67040fd",
    "license": "apache-2.0",
    "split": SPLIT,
    "url": "https://huggingface.co/datasets/tasksource/bigbench",
    "file_url": ("https://huggingface.co/datasets/tasksource/bigbench/resolve/"
                 "210c156767d2f4f05d2f4fd0bb275017a67040fd/{config}/train-00000-of-00001.parquet"),
    "key_source": "native-name",
    "key_note": "key=config 名（BIG-bench 原生任务名），prompt=原生 inputs 原文",
}

COSMOS = {
    "slug": "cosmos-qa",
    "dataset": "allenai/cosmos_qa",
    "revision": "28d9d5e2aae025e73e11177891a88dba51190013",
    "data_revision": "8d4d7b40d0a027c6f6095f990c3809e9396a8e6f",
    "license": "cc-by-4.0",
    "split": SPLIT,
    "config": "default",
    "url": "https://huggingface.co/datasets/allenai/cosmos_qa",
    "file_url": ("https://raw.githubusercontent.com/wilburOne/cosmosqa/"
                 "8d4d7b40d0a027c6f6095f990c3809e9396a8e6f/data/train.csv"),
    "key_source": "native-name",
    "key": "question",
    "key_note": "key=原生字段名 question，prompt=原生 question 原文",
}

#: 白名单 = 选型报告 第2节 P1-1 表里标为"原生带选项 + 不需要生成"的 P1/P2 config。
#: 能力维度取 README.md 2.1 的六维口径；归属沿用选型报告的 P1/P2 分组。
BIGBENCH_CONFIGS = OrderedDict([
    # ---- P1 数学与形式逻辑 ----
    ("formal_fallacies_syllogisms_negation", ("math_logic", "形式论证有效性")),
    ("logical_fallacy_detection", ("math_logic", "逻辑谬误识别")),
    ("analytic_entailment", ("math_logic", "形式蕴含")),
    ("epistemic_reasoning", ("math_logic", "形式蕴含（知识模态）")),
    ("logical_deduction", ("math_logic", "约束满足·排序")),
    ("logic_grid_puzzle", ("math_logic", "约束满足·网格")),
    ("evaluating_information_essentiality", ("math_logic", "数据充分性")),
    ("symbol_interpretation", ("math_logic", "形式化语义一致性")),
    ("mathematical_induction", ("math_logic", "数学归纳")),
    ("known_unknowns", ("math_logic", "不可判定")),
    ("arithmetic", ("math_logic", "多步算术")),
    ("elementary_math_qa", ("math_logic", "数学应用题")),
    ("unit_conversion", ("math_logic", "单位换算")),
    ("cs_algorithms", ("math_logic", "算法与计数")),
    ("intersect_geometry", ("math_logic", "几何（选项数超上限）")),
    ("checkmate_in_one", ("math_logic", "棋类搜索（选项数超上限）")),
    ("temporal_sequences", ("math_logic", "时序推理")),
    ("date_understanding", ("math_logic", "日期推算")),
    ("tracking_shuffled_objects", ("math_logic", "状态跟踪")),
    ("navigate", ("math_logic", "空间推理")),
    # ---- P2 阅读理解与证据整合 ----
    ("question_selection", ("reading_evidence", "问题选择")),
    ("disambiguation_qa", ("reading_evidence", "歧义消解")),
    ("presuppositions_as_nli", ("reading_evidence", "预设与蕴含")),
    ("entailed_polarity", ("reading_evidence", "极性蕴含")),
    ("winowhy", ("reading_evidence", "因果解释合理性")),
    ("sentence_ambiguity", ("reading_evidence", "句法歧义")),
    ("implicit_relations", ("reading_evidence", "隐式关系")),
    ("crash_blossom", ("reading_evidence", "常识事件链")),
    ("snarks", ("reading_evidence", "讽刺识别")),
    ("understanding_fables", ("reading_evidence", "寓言寓意")),
    ("riddle_sense", ("reading_evidence", "谜语常识")),
    ("vitaminc_fact_verification", ("reading_evidence", "证据核验")),
])

CAPABILITY_LABELS = OrderedDict([
    ("tool_action", "工具与行动选择"),
    ("social_judgment", "社会与人类判断"),
    ("reading_evidence", "阅读理解与证据整合"),
    ("math_logic", "数学与形式逻辑"),
    ("world_knowledge", "世界知识及其应用"),
    ("causal_uncertainty", "因果、反事实与不确定性判断"),
    ("other", "未命中"),
])

DOMAIN = "knowledge_reasoning"


# ------------------------------------------------------------------ 通用小工具

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def utc_now():
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm_text(text):
    """选项/答案比较用的规范化文本：折叠全部空白、去首尾。不做大小写或语义归并。"""
    return " ".join(str(text if text is not None else "").split())


def jsonl_line(payload):
    """与 convert.py 的 jsonl_line 同口径：转义 U+2028/U+2029/U+0085，按行读不会断裂。"""
    text = json.dumps(payload, ensure_ascii=False)
    for code in LINE_BREAKS:
        text = text.replace(chr(code), "\\u%04x" % code)
    return text + "\n"


def jsonl_write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(jsonl_line(row))


def jsonl_read(path):
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def fetch_url(url, timeout=300):
    request = urllib.request.Request(
        url, headers={"User-Agent": "pol-governance-db-adopt/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def bucket_of(value, edges):
    """返回落在哪个长度分桶（用于报告 state 长度分布）。"""
    for edge in edges:
        if value <= edge:
            return "<=" + str(edge)
    return ">" + str(edges[-1])


# ------------------------------------------------------------------ fetch

def cmd_fetch(args):
    """下载原始文件到仓库外；逐个记 sha256，保证"这次到底下了什么"可复核。"""
    records = []
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for config in BIGBENCH_CONFIGS:
        target = RAW_ROOT / "bigbench" / config / "train-00000-of-00001.parquet"
        url = BIGBENCH["file_url"].format(config=config)
        if target.is_file() and target.stat().st_size > 0 and not args.force:
            print("skip bigbench/" + config + " (exists, " + str(target.stat().st_size) + " B)")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(fetch_url(url))
            print("ok   bigbench/" + config + " " + str(target.stat().st_size) + " B")
        records.append({"dataset": BIGBENCH["dataset"], "revision": BIGBENCH["revision"],
                        "split": BIGBENCH["split"], "config": config,
                        "path": str(target.relative_to(RAW_ROOT)), "url": url,
                        "sha256": sha256_file(target), "bytes": target.stat().st_size})
    target = RAW_ROOT / "cosmos-qa" / "train.csv"
    if target.is_file() and target.stat().st_size > 0 and not args.force:
        print("skip cosmos-qa/train.csv (exists, " + str(target.stat().st_size) + " B)")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fetch_url(COSMOS["file_url"]))
        print("ok   cosmos-qa/train.csv " + str(target.stat().st_size) + " B")
    records.append({"dataset": COSMOS["dataset"], "revision": COSMOS["revision"],
                    "data_revision": COSMOS["data_revision"], "split": COSMOS["split"],
                    "config": COSMOS["config"], "path": str(target.relative_to(RAW_ROOT)),
                    "url": COSMOS["file_url"], "sha256": sha256_file(target),
                    "bytes": target.stat().st_size})
    FETCH_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    FETCH_MANIFEST.write_text(json.dumps(
        {"fetched_at": utc_now(), "raw_root": str(RAW_ROOT),
         "revision_enforced": True,
         "revision_note": "bigbench 走 resolve/<sha>/<path>，revision 是 URL 的一部分，逐字节可复现；"
                          "cosmos_qa 的 HF 仓库只有 loader，数据字节固定在 GitHub 文件级 commit。",
         "files": records,
         "totals": {"files": len(records), "bytes": sum(r["bytes"] for r in records)}},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifest -> " + str(FETCH_MANIFEST) + " (" + str(len(records)) + " files, "
          + str(sum(r["bytes"] for r in records)) + " B)")
    return 0


# ------------------------------------------------------------------ extract

def cmd_extract(args):
    """parquet -> rows.jsonl。需要 pyarrow，用仓外 venv 跑（仓库保持 stdlib-only）。"""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("需要 pyarrow：请用仓外 venv 运行，例如 "
              r"D:\pol2-raw\capability-raw\.venv\Scripts\python.exe", file=sys.stderr)
        return 2
    total = 0
    for config in BIGBENCH_CONFIGS:
        src = RAW_ROOT / "bigbench" / config / "train-00000-of-00001.parquet"
        dst = RAW_ROOT / "bigbench" / config / "train.jsonl"
        if not src.is_file():
            print("MISSING " + str(src), file=sys.stderr)
            return 2
        if dst.is_file() and not args.force:
            print("skip bigbench/" + config + " (" + str(dst.stat().st_size) + " B)")
            continue
        rows = pq.read_table(src).to_pylist()
        jsonl_write(dst, rows)
        total += len(rows)
        print("ok   bigbench/" + config + " rows=" + str(len(rows)))
    print("extracted rows=" + str(total))
    return 0

# ------------------------------------------------------------------ 质量门槛

def select_options(labels, scores, answer_text):
    """质量门槛 + 选项去重。

    返回 (kept_labels, answer_index, flags, reject_reason)；reject_reason 非空表示剔除。
    顺序：先去空选项，再按折叠空白的规范化文本去重，再定位答案，再卡选项数。
    """
    flags = []
    if not norm_text(answer_text):
        return None, None, flags, "empty_answer"
    entries = []
    for index, label in enumerate(labels):
        if not norm_text(label):
            flags.append("empty_option_dropped")
            continue
        marked = bool(scores) and index < len(scores) and float(scores[index]) == 1.0
        entries.append([index, str(label), marked])
    if not entries:
        return None, None, flags, "empty_options"
    seen = {}
    kept = []
    for record in entries:
        key = norm_text(record[1])
        if key in seen:
            seen[key][2] = seen[key][2] or record[2]
            flags.append("duplicate_option_merged")
            continue
        seen[key] = record
        kept.append(record)
    target_key = norm_text(answer_text)
    matched = [i for i, record in enumerate(kept) if norm_text(record[1]) == target_key]
    if not matched:
        return None, None, flags, "answer_not_in_options"
    answer_index = matched[0]
    correct = [i for i, record in enumerate(kept) if record[2]]
    if len(correct) > 1:
        return None, None, flags, "answer_not_unique"
    if correct and correct[0] != answer_index:
        flags.append("score_target_mismatch")
    if not correct:
        flags.append("answer_from_target_text")
    if len(kept) < MIN_OPTIONS:
        return None, None, flags, "options_lt2"
    if len(kept) > MAX_OPTIONS:
        return None, None, flags, "options_gt16"
    return [record[1] for record in kept], answer_index, flags, None


def stamp_converter(item, errors):
    """条目出自本脚本，不是 convert.py 本体：把 meta.converter 改回真实转换器。

    build_native_item 会把 CONVERTER_NAME 写死成 convert.py；照抄会让溯源指向错误的脚本。
    这里保留复用关系（native 形状由 convert.py 的构建器产出），但署名给本脚本。
    """
    item["meta"]["converter"] = CONVERTER_NAME
    item["meta"]["converter_version"] = CONVERTER_VERSION
    item["meta"]["converter_chain"] = ("convert_capability.py "
                                       + CONVERTER_VERSION + " -> convert.py native builders")
    if errors:
        # 只在真有问题时写：全批 152,580 条都通过校验，逐条写空数组纯属 13 MB 噪声
        item["meta"]["schema_errors"] = errors
    return item


def resolve_id(convert, ctx, slug, dataset, revision, config, split, row):
    """分配 id，并把 32 位哈希的生日碰撞按确定性 variant 解决。

    id 是 db-<slug>-<8hex>（32 位），本批 152,580 条实测撞了 3 次（期望 ~2.7 次）。
    同一 (config, row) 只会走到同一个 base id，因此冲突只可能来自不同行；
    这里按**固定的遍历顺序**给后来者依次挂 v1、v2…，顺序固定所以结果可复现。
    变体会一起决定打散种子，所以必须在打散之前定下来。
    """
    variant = ""
    step = 0
    while True:
        candidate = convert.item_id(slug, dataset, revision, config, split, row, variant)
        if candidate not in ctx["used_ids"]:
            ctx["used_ids"].add(candidate)
            if variant:
                ctx["id_collisions"] += 1
            return candidate, variant
        step += 1
        variant = "v" + str(step)


def shuffle_options(labels, answer_index, seed):
    """确定性打散：种子由 item id 派生，同一行重复转换得到同一顺序。

    返回 (shuffled_labels, new_answer_index, native_order)。
    native_order 是打散后每个位置对应的原下标，用来完整复原来源顺序。
    """
    order = list(range(len(labels)))
    random.Random(seed).shuffle(order)
    shuffled = [labels[index] for index in order]
    return shuffled, order.index(answer_index), order


def position_bias(counter_by_size, min_expected=5.0):
    """位置偏置检验：按选项数分层做卡方，避免不同选项数混在一起比。

    只在"每格期望 >= min_expected"的层里算卡方与最大占比：格子太小的层（如 size=16 只有 12 条）
    每格期望远小于 1，卡方近似失效，会把统计量抬到没有意义的量级，单独列进 small_groups。

    counter_by_size: {options_count: Counter(position -> count)}
    返回 {items, tested_items, chi2, df, max_share, max_share_position, max_share_size,
          per_size, small_groups, min_expected}
    """
    chi2 = 0.0
    df = 0
    items = 0
    tested = 0
    worst = (0.0, None, None)
    per_size = {}
    small = {}
    for size in sorted(counter_by_size):
        counter = counter_by_size[size]
        total = sum(counter.values())
        if total == 0:
            continue
        items += total
        expected = total / float(size)
        counts = [counter.get(position, 0) for position in range(size)]
        if expected < min_expected:
            small[str(size)] = {"items": total, "expected_per_cell": round(expected, 3),
                                "counts": counts}
            continue
        tested += total
        size_chi2 = sum((observed - expected) ** 2 / expected for observed in counts)
        chi2 += size_chi2
        df += size - 1
        peak = max(counts)
        share = peak / float(total)
        if share > worst[0]:
            worst = (share, counts.index(peak), size)
        per_size[size] = {"items": total, "chi2": round(size_chi2, 2), "counts": counts}
    return {"items": items, "tested_items": tested, "chi2": round(chi2, 2), "df": df,
            "max_share": round(worst[0], 4), "max_share_position": worst[1],
            "max_share_size": worst[2], "min_expected": min_expected,
            "per_size": per_size, "small_groups": small}


# ------------------------------------------------------------------ bigbench -> items

def convert_bigbench(ctx):
    """tasksource/bigbench：inputs + multiple_choice_targets + multiple_choice_scores -> choice。"""
    convert = ctx["convert"]
    out = []
    rejects = []
    per_config = OrderedDict()
    raw_total = 0
    for config, (capability, subtype) in BIGBENCH_CONFIGS.items():
        path = RAW_ROOT / "bigbench" / config / "train.jsonl"
        if not path.is_file():
            raise SystemExit("缺 extract 产物：" + str(path) + "（先跑 extract）")
        config_items = []
        config_rejects = Counter()
        config_answers = Counter()
        config_positions = Counter()
        for line_no, payload in enumerate(jsonl_read(path)):
            raw_total += 1
            #: 原生 idx 在多个 config 里**不唯一**（实测 unit_conversion 19,151 行只有 2,400 个 idx、
            #: arithmetic 12,019 行只有 800 个、elementary_math_qa 30,531 行只有 6,151 个），
            #: 拿它当 source.row 会让 id 大面积撞车（顺带让打散种子重复、位置分布失真）。
            #: 因此 row 用**物理行号**，原生 idx 原样留在 meta.native_idx 供溯源。
            native_idx = payload.get("idx")
            row = line_no
            state = str(payload.get("inputs") or "")
            labels = list(payload.get("multiple_choice_targets") or [])
            scores = list(payload.get("multiple_choice_scores") or [])
            targets = list(payload.get("targets") or [])
            if not state.strip():
                config_rejects["empty_state"] += 1
                rejects.append({"dataset": BIGBENCH["dataset"], "config": config, "row": row,
                                "reason": "empty_state"})
                continue
            if not labels:
                config_rejects["empty_options"] += 1
                rejects.append({"dataset": BIGBENCH["dataset"], "config": config, "row": row,
                                "reason": "empty_options"})
                continue
            if len(targets) != 1:
                reason = "multi_target:" + str(len(targets))
                config_rejects[reason] += 1
                rejects.append({"dataset": BIGBENCH["dataset"], "config": config, "row": row,
                                "reason": reason})
                continue
            kept, answer_index, flags, reject = select_options(labels, scores, targets[0])
            if reject:
                config_rejects[reject] += 1
                rejects.append({"dataset": BIGBENCH["dataset"], "config": config, "row": row,
                                "reason": reject, "native_option_count": len(labels)})
                continue
            item_id, id_variant = resolve_id(convert, ctx, BIGBENCH["slug"],
                                             BIGBENCH["dataset"], BIGBENCH["revision"],
                                             config, BIGBENCH["split"], row)
            if id_variant:
                flags = list(flags) + ["id_collision_resolved:" + id_variant]
            seed = int(item_id.rsplit("-", 1)[1], 16)
            shuffled, new_index, native_order = shuffle_options(kept, answer_index, seed)
            used = set()
            pairs = [{"key": convert.option_key(label, index, used), "label": label}
                     for index, label in enumerate(shuffled)]
            question = convert.native_question(config, "choice", state, options=pairs)
            manifest = {"dataset": BIGBENCH["dataset"], "revision": BIGBENCH["revision"],
                        "config": config, "split": BIGBENCH["split"],
                        "license": BIGBENCH["license"], "source_url": BIGBENCH["url"],
                        "_created_at": ctx["created_at"]}
            item, errors = convert.build_native_item(
                None, slug=BIGBENCH["slug"], manifest=manifest, row=row, domain=DOMAIN,
                domain_rule="capability:bigbench:" + config, state=state, questions=[question],
                targets={config: {"answer": pairs[new_index]["key"]}}, flags=flags,
                variant=id_variant, key_source=BIGBENCH["key_source"],
                meta_extra={
                    "capability": capability,
                    "capability_label": CAPABILITY_LABELS[capability],
                    "capability_subtype": subtype,
                    "capability_rule": "capability-sources.md P1-1 config -> " + capability,
                    "native_task": config,
                    "native_idx": native_idx,
                    "native_option_count": len(kept),
                    "native_option_count_before_dedupe": len(labels),
                    "native_answer_index": answer_index,
                    "answer_index": new_index,
                    "shuffle_seed": seed,
                    "native_option_order": native_order,
                    "native_answer_text": kept[answer_index],
                    "native_split": "train",
                    "native_source_file": BIGBENCH["file_url"].format(config=config),
                    "state_length": len(state),
                    "state_equals_prompt": True,
                })
            stamp_converter(item, errors)
            config_items.append(item)
            config_answers[norm_text(kept[answer_index])] += 1
            config_positions[answer_index] += 1
        # 单一类别（无负类）的 config 整份剔除：答案文本只有一个取值
        if config_items and len(config_answers) == 1:
            only = next(iter(config_answers))
            for item in config_items:
                rejects.append({"dataset": BIGBENCH["dataset"], "config": config,
                                "row": item["source"]["row"],
                                "reason": "single_class_config", "answer": only})
            config_rejects["single_class_config"] += len(config_items)
            config_items = []
        out.extend(config_items)
        per_config[config] = {
            "capability": capability, "capability_label": CAPABILITY_LABELS[capability],
            "subtype": subtype, "converted": len(config_items),
            "rejected": sum(config_rejects.values()),
            "rejects": dict(sorted(config_rejects.items())),
            "distinct_answer_texts": len(config_answers),
            "answer_top": config_answers.most_common(5),
            "native_answer_position_top": config_positions.most_common(3),
        }
    return out, rejects, per_config, raw_total


# ------------------------------------------------------------------ cosmos_qa -> items

COSMOS_ANSWER_FIELDS = ["answer0", "answer1", "answer2", "answer3"]


def convert_cosmos(ctx):
    """allenai/cosmos_qa：context + question + answer0..3 + label -> choice（原生 4 选 1）。"""
    convert = ctx["convert"]
    path = RAW_ROOT / "cosmos-qa" / "train.csv"
    if not path.is_file():
        raise SystemExit("缺下载产物：" + str(path) + "（先跑 fetch）")
    out = []
    rejects = []
    counts = Counter()
    answers = Counter()
    raw_total = 0
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for line_no, payload in enumerate(reader):
            raw_total += 1
            row = line_no
            state = str(payload.get("context") or "")
            prompt = str(payload.get("question") or "")
            labels = [payload.get(field) for field in COSMOS_ANSWER_FIELDS]
            if not state.strip():
                counts["empty_state"] += 1
                rejects.append({"dataset": COSMOS["dataset"], "config": COSMOS["config"],
                                "row": row, "reason": "empty_state"})
                continue
            if not prompt.strip():
                counts["empty_prompt"] += 1
                rejects.append({"dataset": COSMOS["dataset"], "config": COSMOS["config"],
                                "row": row, "reason": "empty_prompt"})
                continue
            if not any(norm_text(label) for label in labels):
                counts["empty_options"] += 1
                rejects.append({"dataset": COSMOS["dataset"], "config": COSMOS["config"],
                                "row": row, "reason": "empty_options"})
                continue
            try:
                native_index = int(str(payload.get("label")).strip())
            except (TypeError, ValueError):
                native_index = -1
            if not 0 <= native_index < len(labels):
                counts["bad_label"] += 1
                rejects.append({"dataset": COSMOS["dataset"], "config": COSMOS["config"],
                                "row": row, "reason": "bad_label",
                                "label": payload.get("label")})
                continue
            scores = [1.0 if index == native_index else 0.0 for index in range(len(labels))]
            kept, answer_index, flags, reject = select_options(labels, scores, labels[native_index])
            if reject:
                counts[reject] += 1
                rejects.append({"dataset": COSMOS["dataset"], "config": COSMOS["config"],
                                "row": row, "reason": reject, "native_option_count": len(labels)})
                continue
            item_id, id_variant = resolve_id(convert, ctx, COSMOS["slug"], COSMOS["dataset"],
                                             COSMOS["revision"], COSMOS["config"],
                                             COSMOS["split"], row)
            if id_variant:
                flags = list(flags) + ["id_collision_resolved:" + id_variant]
            seed = int(item_id.rsplit("-", 1)[1], 16)
            shuffled, new_index, native_order = shuffle_options(kept, answer_index, seed)
            used = set()
            pairs = [{"key": convert.option_key(label, index, used), "label": label}
                     for index, label in enumerate(shuffled)]
            question = convert.native_question(COSMOS["key"], "choice", prompt, options=pairs)
            manifest = {"dataset": COSMOS["dataset"], "revision": COSMOS["revision"],
                        "config": COSMOS["config"], "split": COSMOS["split"],
                        "license": COSMOS["license"], "source_url": COSMOS["url"],
                        "_created_at": ctx["created_at"]}
            item, errors = convert.build_native_item(
                None, slug=COSMOS["slug"], manifest=manifest, row=row, domain=DOMAIN,
                domain_rule="capability:cosmos_qa:reading_evidence", state=state,
                questions=[question],
                targets={COSMOS["key"]: {"answer": pairs[new_index]["key"]}}, flags=flags,
                variant=id_variant, key_source=COSMOS["key_source"],
                meta_extra={
                    "capability": "reading_evidence",
                    "capability_label": CAPABILITY_LABELS["reading_evidence"],
                    "capability_subtype": "多句情境下的因果/意图推理",
                    "capability_rule": "capability-sources.md P2-1 -> reading_evidence",
                    "native_id": payload.get("id"),
                    "native_field": COSMOS["key"],
                    "native_option_count": len(kept),
                    "native_option_count_before_dedupe": len(labels),
                    "native_answer_index": answer_index,
                    "answer_index": new_index,
                    "shuffle_seed": seed,
                    "native_option_order": native_order,
                    "native_answer_text": kept[answer_index],
                    "native_label": native_index,
                    "native_split": "train",
                    "native_source_file": COSMOS["file_url"],
                    "state_length": len(state),
                    "state_equals_prompt": False,
                })
            stamp_converter(item, errors)
            out.append(item)
            answers[norm_text(kept[answer_index])] += 1
    if out and len(answers) == 1:
        only = next(iter(answers))
        for item in out:
            rejects.append({"dataset": COSMOS["dataset"], "config": COSMOS["config"],
                            "row": item["source"]["row"], "reason": "single_class_config",
                            "answer": only})
        counts["single_class_config"] += len(out)
        out = []
    per_config = {COSMOS["config"]: {
        "capability": "reading_evidence",
        "capability_label": CAPABILITY_LABELS["reading_evidence"],
        "subtype": "多句情境下的因果/意图推理",
        "converted": len(out), "rejected": sum(counts.values()),
        "rejects": dict(sorted(counts.items())),
        "distinct_answer_texts": len(answers), "answer_top": answers.most_common(5)}}
    return out, rejects, per_config, raw_total

# ------------------------------------------------------------------ 统计与报告

def dist_text(counter, limit=None):
    total = sum(counter.values())
    rows = counter.most_common(limit) if limit else sorted(counter.items())
    return [{"value": str(value), "items": count,
             "share": round(count / float(total), 6) if total else 0.0}
            for value, count in rows]


def corpus_stats(items):
    """候选语料的形状统计：能力维度、语言、选项数、位置偏置、state 长度、quality_flags。"""
    capability = Counter()
    lang = Counter()
    option_count = Counter()
    flags = Counter()
    target_shape = Counter()
    state_len = Counter()
    raw_by_size = {}
    shuffled_by_size = {}
    per_config = Counter()
    for item in items:
        meta = item.get("meta") or {}
        capability[meta.get("capability") or "other"] += 1
        lang[item.get("lang") or "?"] += 1
        questions = item.get("questions") or []
        question = questions[0] if questions else {}
        options = question.get("options") or []
        size = len(options)
        option_count[size] += 1
        targets = item.get("targets") or {}
        value = list(targets.values())[0] if targets else {}
        if value.get("probs"):
            shape = "with_probs"
        elif value.get("answer") is not None:
            shape = "answer_only"
        else:
            shape = "empty"
        target_shape[shape] += 1
        native_index = meta.get("native_answer_index")
        shuffled_index = meta.get("answer_index")
        if isinstance(native_index, int):
            raw_by_size.setdefault(size, Counter())[native_index] += 1
        if isinstance(shuffled_index, int):
            shuffled_by_size.setdefault(size, Counter())[shuffled_index] += 1
        for flag in meta.get("quality_flags") or []:
            base = flag.split(":", 1)[0]
            flags[base] += 1
        length = meta.get("state_length")
        if isinstance(length, int):
            state_len[bucket_of(length, (512, 1024, 2048, 4096, 8192))] += 1
        per_config[meta.get("native_task") or meta.get("native_field") or "?"] += 1
    return {
        "items": len(items),
        "capability": dict(capability),
        "lang": dict(lang),
        "option_count": {str(k): v for k, v in sorted(option_count.items())},
        "target_shape": dict(target_shape),
        "quality_flags": dict(flags),
        "state_length_buckets": dict(state_len),
        "answer_position_native": position_bias(raw_by_size),
        "answer_position_shuffled": position_bias(shuffled_by_size),
        "per_config": dict(per_config),
    }


def validate_items(convert, items):
    """用 convert.py 的 native_item_errors 逐条校验（与 items.native.jsonl 同一把尺子）。"""
    issues = Counter()
    samples = []
    bad_items = 0
    seen_ids = Counter()
    for item in items:
        errors = convert.native_item_errors(item)
        if not isinstance(item, dict) or item.get("domain") != DOMAIN:
            errors = list(errors) + ["domain_not_knowledge_reasoning"]
        if errors:
            bad_items += 1
            for error in errors:
                issues[error.split(":")[0].split(" ")[0]] += 1
            if len(samples) < 5:
                samples.append({"id": (item or {}).get("id"), "errors": errors[:4]})
        seen_ids[item.get("id")] += 1
    duplicates = {key: value for key, value in seen_ids.items() if value > 1}
    if duplicates:
        # 重复 id 是 coverage.py 的硬违规（退出码 1），必须计进 schema_issues
        issues["duplicate_id"] = sum(value - 1 for value in duplicates.values())
    return {"items": len(items), "items_with_issues": bad_items + len(duplicates),
            "issue_counts": dict(issues), "samples": samples,
            "duplicate_ids": len(duplicates),
            "schema_issues": sum(issues.values())}


def merge_preview(items_path, splits_dir, by_source=None):
    """与现有语料合并后的构成预期。

    现有语料的能力维度**用 README 自己的规则链**（readme_stats.classify_capability）重算，
    新条目用 meta.capability（readme_stats 目前不认识这两个来源，合并时需要在
    classify_capability 里加两条规则，见 capability-adoption.md）。
    """
    stats = load_module("general_readme_stats", HERE / "readme_stats.py")
    splits = OrderedDict([("train", Path(splits_dir) / "train.jsonl"),
                          ("test", Path(splits_dir) / "test.jsonl"),
                          ("validation", Path(splits_dir) / "validation.jsonl")])
    before_all = Counter()
    before_train = Counter()
    rules = Counter()
    present = []
    for split, path in splits.items():
        if not path.is_file():
            continue
        present.append(split)
        for item in jsonl_read(path):
            capability, rule = stats.classify_capability(item)
            before_all[capability] += 1
            rules[rule] += 1
            if split == "train":
                before_train[capability] += 1
    new = Counter()
    for item in jsonl_read(items_path):
        new[(item.get("meta") or {}).get("capability") or "other"] += 1
    after_all = Counter(before_all)
    after_all.update(new)
    after_train = Counter(before_train)
    after_train.update(new)

    def table(before, after):
        rows = []
        for key in list(CAPABILITY_LABELS):
            if key == "other" and not before.get(key) and not after.get(key):
                continue
            rows.append({
                "capability": key, "label": CAPABILITY_LABELS[key],
                "before": before.get(key, 0), "after": after.get(key, 0),
                "before_share": round(before.get(key, 0) / float(sum(before.values())), 6),
                "after_share": round(after.get(key, 0) / float(sum(after.values())), 6)})
        return rows

    def scenario(name, new_counter):
        after = Counter(before_all)
        after.update(new_counter)
        total = sum(after.values())
        return {
            "name": name, "new_items": sum(new_counter.values()), "merged_total": total,
            "shares": {key: round(after.get(key, 0) / float(total), 6)
                       for key in ("tool_action", "social_judgment", "reading_evidence",
                                   "math_logic", "world_knowledge", "causal_uncertainty")},
            "counts": {key: after.get(key, 0) for key in CAPABILITY_LABELS if after.get(key)},
        }

    scenarios = [scenario("full_both", new)]
    for dataset, label in ((BIGBENCH["dataset"], "bigbench_only"),
                           (COSMOS["dataset"], "cosmos_only")):
        if by_source and by_source.get(dataset):
            scenarios.append(scenario(label, by_source[dataset]))
    for factor, label in ((0.5, "both_half"), (1 / 3, "both_third"), (1 / 6, "both_sixth")):
        scenarios.append(scenario(label, {key: int(round(count * factor))
                                          for key, count in new.items()}))

    return {
        "scenarios": scenarios,
        "existing_files": [str(splits[split]) for split in present],
        "existing_all_splits": sum(before_all.values()),
        "existing_train_only": sum(before_train.values()),
        "existing_rules": dict(rules),
        "new_items": sum(new.values()),
        "new_by_capability": dict(new),
        "merged_all_splits_total": sum(after_all.values()),
        "merged_train_only_total": sum(after_train.values()),
        "table_all_splits": table(before_all, after_all),
        "table_train_only": table(before_train, after_train),
    }


def write_report(args, payload):
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("report -> " + str(args.report))


def print_summary(payload):
    print("")
    print("== 候选语料 ==")
    for name, source in payload["sources"].items():
        print("  " + name + ": raw=" + str(source["raw_rows"])
              + " converted=" + str(source["converted"])
              + " rejected=" + str(source["rejected_total"]))
    print("  total converted=" + str(payload["totals"]["items"]))
    print("")
    print("== 剔除理由（逐条计数）==")
    for reason, count in sorted(payload["totals"].get("rejects", {}).items(),
                                key=lambda pair: -pair[1]):
        print("  " + reason + ": " + str(count))
    print("")
    print("== 能力维度分布（候选）==")
    for capability, count in payload["stats"]["capability"].items():
        print("  " + capability + ": " + str(count))
    print("")
    print("== 答案位置偏置 ==")
    for key in ("answer_position_native", "answer_position_shuffled"):
        bias = payload["stats"][key]
        print("  " + key + ": chi2=" + str(bias["chi2"]) + " df=" + str(bias["df"])
              + " max_share=" + str(bias["max_share"]))
    print("")
    print("== 合并后构成预期（公开三分区口径）==")
    for row in payload["merge"]["table_all_splits"]:
        print("  " + row["label"] + ": " + str(row["before"]) + " ("
              + str(round(row["before_share"] * 100, 2)) + "%) -> "
              + str(row["after"]) + " (" + str(round(row["after_share"] * 100, 2)) + "%)")
    print("")
    print("== 合并情景（新语料整体缩放到不同体量）==")
    for row in payload["merge"].get("scenarios", []):
        shares = row["shares"]
        print("  " + row["name"] + ": new=" + str(row["new_items"])
              + " total=" + str(row["merged_total"])
              + " tool=" + str(round(shares["tool_action"] * 100, 2)) + "%"
              + " math=" + str(round(shares["math_logic"] * 100, 2)) + "%"
              + " reading=" + str(round(shares["reading_evidence"] * 100, 2)) + "%")
    print("")
    print("schema_issues=" + str(payload["schema"]["schema_issues"])
          + " (items_with_issues=" + str(payload["schema"]["items_with_issues"]) + ")")


def cmd_convert(args):
    convert = load_module("general_convert", HERE / "convert.py")
    ctx = {"convert": convert, "created_at": args.created_at or utc_now(),
           "used_ids": set(), "id_collisions": 0}
    bigbench_items, bb_rejects, bb_configs, bb_raw = convert_bigbench(ctx)
    cosmos_items, cs_rejects, cs_configs, cs_raw = convert_cosmos(ctx)
    if args.limit:
        bigbench_items = bigbench_items[:args.limit]
        cosmos_items = cosmos_items[:args.limit]
    items = bigbench_items + cosmos_items
    jsonl_write(args.out, items)
    jsonl_write(args.rejects, bb_rejects + cs_rejects)

    schema = validate_items(convert, items)
    stats = corpus_stats(items)
    reject_counts = Counter(row["reason"] for row in bb_rejects + cs_rejects)
    by_source = {
        BIGBENCH["dataset"]: Counter((item["meta"].get("capability") or "other")
                                     for item in bigbench_items),
        COSMOS["dataset"]: Counter((item["meta"].get("capability") or "other")
                                   for item in cosmos_items),
    }
    merge = merge_preview(args.out, args.splits_dir, by_source)

    def source_block(spec, items_list, rejects_list, configs, raw_total):
        counts = Counter(row["reason"] for row in rejects_list)
        block = {
            "dataset": spec["dataset"], "revision": spec["revision"],
            "license": spec["license"], "url": spec["url"],
            "source_file_url": spec["file_url"],
            "split": spec["split"], "raw_rows": raw_total,
            "converted": len(items_list), "rejected_total": sum(counts.values()),
            "rejects": dict(sorted(counts.items(), key=lambda pair: -pair[1])),
            "configs": configs,
        }
        if spec is COSMOS:
            block["data_revision"] = spec["data_revision"]
        subset = [item for item in items_list]
        if subset:
            positions_native = {}
            positions_shuffled = {}
            for item in subset:
                meta = item["meta"]
                size = meta["native_option_count"]
                positions_native.setdefault(size, Counter())[meta["native_answer_index"]] += 1
                positions_shuffled.setdefault(size, Counter())[meta["answer_index"]] += 1
            block["answer_position_native"] = position_bias(positions_native)
            block["answer_position_shuffled"] = position_bias(positions_shuffled)
        return block

    payload = {
        "schema": "capability-adoption/0.1",
        "generated_at": utc_now(),
        "converter": {"name": CONVERTER_NAME, "version": CONVERTER_VERSION,
                      "created_at": ctx["created_at"],
                      "reuses": "datasets/general/convert.py --native 路径"
                                "（build_native_item/native_question/item_id/option_key/"
                                "native_item_errors）"},
        "scope": {
            "domain": DOMAIN,
            "kind": "choice",
            "origin": "source",
            "splits_used": [SPLIT],
            "splits_excluded": "validation/test 未取（sources.json policy: 只取 train）",
            "option_count_gate": [MIN_OPTIONS, MAX_OPTIONS],
            "option_count_gate_note": "契约对 origin=source 不设选项上限（实测最多 57）；"
                                      "本轮按接入口径卡 16，超限只剔除不改题。",
            "answer_form": "targets[key].answer 硬标签，不写 probs（契约 1.3 禁止伪造概率）",
            "shuffle": "种子 = int(item id 末 8 位 hex, 16)；原顺序见 meta.native_option_order",
            "id_collisions_resolved": ctx["id_collisions"],
            "id_derivation": "row = 抽取产物里的物理行号（原生 idx 不唯一，见 meta.native_idx）；"
                             "8hex 生日碰撞按固定遍历顺序挂 v1/v2 变体解决",
        },
        "sources": {
            BIGBENCH["dataset"]: source_block(BIGBENCH, bigbench_items, bb_rejects,
                                              bb_configs, bb_raw),
            COSMOS["dataset"]: source_block(COSMOS, cosmos_items, cs_rejects,
                                            cs_configs, cs_raw),
        },
        "totals": {
            "items": len(items),
            "raw_rows": bb_raw + cs_raw,
            "rejected": len(bb_rejects) + len(cs_rejects),
            "rejects": dict(sorted(reject_counts.items(), key=lambda pair: -pair[1])),
            "by_capability": stats["capability"],
        },
        "stats": stats,
        "schema": schema,
        "merge": merge,
        "artifacts": {"items": str(args.out), "rejects": str(args.rejects),
                      "raw_root": str(RAW_ROOT)},
    }
    write_report(args, payload)
    print_summary(payload)
    return 0 if schema["schema_issues"] == 0 else 1


def cmd_verify(args):
    convert = load_module("general_convert", HERE / "convert.py")
    items = list(jsonl_read(args.out))
    schema = validate_items(convert, items)
    stats = corpus_stats(items)
    merge = merge_preview(args.out, args.splits_dir)
    payload = {"schema": "capability-adoption/0.1", "generated_at": utc_now(),
               "converter": {"name": CONVERTER_NAME, "version": CONVERTER_VERSION},
               "sources": {}, "totals": {"items": len(items),
                                         "by_capability": stats["capability"]},
               "stats": stats, "schema": schema, "merge": merge,
               "artifacts": {"items": str(args.out)}}
    write_report(args, payload)
    print_summary(payload)
    return 0 if schema["schema_issues"] == 0 else 1


# ------------------------------------------------------------------ CLI

def build_parser():
    parser = argparse.ArgumentParser(
        description="候选接入准备：tasksource/bigbench + allenai/cosmos_qa -> general 契约候选语料",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="下载原始文件（固定 revision，记 sha256）")
    fetch.add_argument("--force", action="store_true", help="已存在也重新下载")
    fetch.set_defaults(func=cmd_fetch)

    extract = sub.add_parser("extract", help="parquet -> rows.jsonl（需要 pyarrow）")
    extract.add_argument("--force", action="store_true")
    extract.set_defaults(func=cmd_extract)

    convert = sub.add_parser("convert", help="转换 + 报告（stdlib）")
    convert.add_argument("--out", type=Path, default=DEFAULT_ITEMS)
    convert.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    convert.add_argument("--rejects", type=Path, default=DEFAULT_REJECTS)
    convert.add_argument("--splits-dir", type=Path,
                         default=HERE / "data" / "splits")
    convert.add_argument("--created-at", default=None,
                         help="固定 meta.created_at，便于逐字节复现")
    convert.add_argument("--limit", type=int, default=0, help="每个来源只留前 N 条（冒烟用）")
    convert.set_defaults(func=cmd_convert)

    verify = sub.add_parser("verify", help="重读候选语料，跑 native_item_errors + 合并预期")
    verify.add_argument("--out", type=Path, default=DEFAULT_ITEMS)
    verify.add_argument("--report", type=Path, default=RAW_ROOT / "capability-verify.json")
    verify.add_argument("--splits-dir", type=Path,
                        default=HERE / "data" / "splits")
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
