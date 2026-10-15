"""打包内部 benchmark：dataset card + 使用说明 + 可复算 manifest（不含任何样本内容）。

split.py 负责切分与写 benchmark.jsonl(.gz)，本模块负责把它变成可直接上传私有托管的整包：

    benchmark-dataset/
      benchmark.jsonl / benchmark.jsonl.gz   数据（split.py 写、本模块只读来算哈希）
      README.md                              dataset card（聚合统计）
      USAGE.md                               使用与指标口径
      manifest.json                          schema=pol-internal-benchmark-package/0.1
      verify.py                              包内副本，逐字节复制自 verify_benchmark_package.py

三条纪律：

1. **只写聚合统计**：卡片、说明、manifest 都不含任何样本正文、id、state。
   （datasets/general/test_benchmark_package.py 每次运行都会断言。）
2. **可复算**：verifiable_counts 用 verify_benchmark_package.compute_counts 生成——与 verify.py
   校验时用的是同一个函数，生成口径与校验口径不可能漂移。
3. **确定性**：所有文本只由入参决定，不含时间戳；同一输入重跑逐字节一致（split.py 的复跑校验覆盖）。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import verify_benchmark_package as vbp

SCHEMA = "pol-internal-benchmark-package/0.1"
VERIFY_NAME = "verify.py"
VERIFY_TEMPLATE = Path(__file__).resolve().with_name("verify_benchmark_package.py")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """临时文件 + os.replace：并发读者要么看到旧版要么看到新版，不会读到半截文件。"""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def atomic_copy(source: Path, target: Path) -> None:
    """逐字节复制（verify.py 由模板复制而来），同样原子替换。"""
    target = Path(target)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_bytes(Path(source).read_bytes())
    os.replace(temporary, target)


def _table(rows, header) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def render_card(counts: dict, *, version: str, seed: int, ratios: dict, policy: dict,
                generation: dict, known_limitations) -> str:
    """dataset card：只有聚合统计。"""
    total = counts["items"] or 1
    ratio_text = ", ".join(f"{key}={value:g}" for key, value in ratios.items())
    lang_rows = [(lang, n, f"{n / total:.1%}") for lang, n in sorted(counts["by_lang"].items(),
                                                                    key=lambda kv: -kv[1])]
    domain_rows = [(domain, n, f"{n / total:.1%}")
                   for domain, n in sorted(counts["by_domain"].items(), key=lambda kv: -kv[1])]
    kind_rows = []
    for kind, n in sorted(counts["by_kind"].items(), key=lambda kv: -kv[1]):
        questions = counts["questions_by_kind"].get(kind, 0)
        kind_rows.append((kind, n, f"{n / total:.1%}", questions))
    source_rows = []
    for row in policy.get("rows", []):
        source_rows.append((row["dataset"], row["items"], f"{row['share']:.1%}",
                            row["pool"], f"{row['take_rate']:.1%}"))
    cap = policy.get("policy", {}).get("cap_items", 0)
    floor = policy.get("policy", {}).get("floor_items", 0)
    cap_policy = policy.get("policy", {}).get("cap_policy", "-")
    max_row = max(policy.get("rows", []), key=lambda row: row["items"], default=None)
    lang_rows_text = _table(lang_rows, ("语言", "条目", "占本包"))
    domain_rows_text = _table(domain_rows, ("域", "条目", "占本包"))
    kind_rows_text = _table(kind_rows, ("原语", "条目（含该原语的条目）", "占本包", "该原语问题数"))
    source_rows_text = _table(source_rows, ("来源 dataset", "条目", "占本包", "该来源池子", "取用率"))
    limitation_text = "\n".join(f"- {item}" for item in known_limitations)
    exclusions = generation.get("benchmark_lang_policy", {}).get("exclusions", {})
    exclusion_text = ("\n".join(f"- `{lang}`：{reason}" for lang, reason in exclusions.items())
                      if exclusions else "- 无（语料里每种语言都可进 benchmark）")
    return f"""---
license: other
pretty_name: PoL 通用决策底座 · 内部 benchmark
private: true
---

# PoL 通用决策底座 · 内部 benchmark（private）

**用途**：内部模型比较与回归；不作为公开测试集，不进入训练、蒸馏或教师造数。
**请勿公开**：本目录由用户上传私有托管（Hugging Face 设为 private）；不得进入公开仓库、
公开日志、测试夹具或提交信息。红线与加载方式见 USAGE.md。

## 版本与生成

- 版本：{version}（切分比例 {ratio_text}；随机种子 {seed}）
- 生成脚本：`{generation.get('generator', '-')}`
- 保密：{generation.get('salt_note', '-')}
- 语料：{generation.get('input', {}).get('path', '-')}（{generation.get('input', {}).get('items', '-')} 条，
  全量语料不进公开仓库）
- 泄漏检查：跨区组 {generation.get('leak_checks', {}).get('groups_multi_split', '-')} /
  跨区 state {generation.get('leak_checks', {}).get('states_multi_split', '-')} /
  跨区 id {generation.get('leak_checks', {}).get('ids_multi_split', '-')}

## 规模

- 条目数：{counts['items']}；请求组：{counts['declared_groups']}（有显式分组 id 的条目
  {counts['items_with_declared_group_id']}）
- 问题数：{counts['questions']}；带 answer 的问题：{counts['questions_with_answer']}；
  带 probs 的问题：{counts['questions_with_probs']}

### 语言

{lang_rows_text}

### 域

{domain_rows_text}

### 原语

{kind_rows_text}

## 来源均衡（硬约束）

- 上限：任一来源占本包 **≤ {policy.get('policy', {}).get('max_source_share', 0):.0%}**
  （本次上限折算 {cap} 条，策略 {cap_policy}）；实际最大来源
  {max_row['dataset'] if max_row else '-'} 占 {policy.get('max_share', 0):.1%}。
- 下限：每个来源 **≥ {policy.get('policy', {}).get('min_source_share', 0):.0%}**
  （{floor} 条；池子不够时取全部），确保"各个来源都收集一点"。
- 为什么是 25%：英文侧 6 个来源，25% 保证至少 4 个来源共同支撑总分；再收紧会把只占池子
  2.8% 的小来源放大 5 倍以上，让 benchmark 偏离真实分布；25% 同时 ≤ 契约 40% 上限。

{source_rows_text}

## 语言政策

- 允许进 benchmark：{', '.join(policy.get('benchmark_langs', []) or generation.get('benchmark_lang_policy', {}).get('benchmark_langs', []) or ['(不限)'])}
- 显式排除：
{exclusion_text}

## 字段

每条记录沿用数据集契约的 items 形状：id / domain / lang / state / questions[] / targets / source / meta。
questions[] 是本条目自带的问题；targets 是逐问题的真值（answer 与/或 probs）。

## 已知限制

{limitation_text}

## 校验

    python verify.py        # 退出码 0=全部通过

本卡片、USAGE.md 与 manifest.json 只包含聚合统计，不含任何 benchmark 样本内容。
"""


def render_usage(counts: dict, *, version: str) -> str:
    """使用说明：load/预测格式/指标口径/与其它评测器的关系/校验/再分发。"""
    langs = ", ".join(sorted(counts["by_lang"])) or "-"
    return f"""# 使用说明（内部 benchmark，private）

本包是**内部盲测集**（{version}）：只用于模型定版后的版本对比与回归，**不得公开、不得进入训练、
不得据其调参**（红线与已知限制见 README.md）。本说明不依赖仓库其它文件。

## 1. 加载

JSONL，一行一条；两种等价文件：benchmark.jsonl（明文）与 benchmark.jsonl.gz（同内容、gzip mtime=0）。

    import json, gzip
    rows = [json.loads(line) for line in gzip.open("benchmark.jsonl.gz", "rt", encoding="utf-8") if line.strip()]

用 Hugging Face datasets：

    from datasets import load_dataset
    ds = load_dataset("json", data_files="benchmark.jsonl", split="train")

## 2. 预测格式

评测按**问题**计分，不按条目：一条 state 上有多个问题（noul / choice / score），每题单独作答。
提交 JSONL，每行一个问题：

    {{"qid": "<item id>.<question key>", "id": "<item id>", "key": "<question key>",
     "kind": "noul|choice|score", "answer": "yes|<option key>|3", "probs": {{"yes": 0.7, "no": 0.3}},
     "execution_status": "ok|timeout|error|invalid", "latency_ms": 12.3}}

约定（沿用仓库 benchmark/PROTOCOL.md 的机器接口精神）：

- answer 取选项 key（noul 的 yes/no、choice 的某个 option key）或 score 的整数分级；
- probs 可选，但给了就必须归一到 1，键必须是该题的选项 key（score 则是分级值）；
- 失败不要编答案：execution_status != ok 时 answer/probs 写 null，并计入分母（不补齐、不推断）；
- 缺失的 qid 计入分母，按错误处理。

## 3. 指标口径（建议，按 kind 分开报）

| 原语 | 主指标 | 有 probs 时附加 |
|---|---|---|
| noul | 准确率（正类 = yes） | Brier、AUROC |
| choice | 准确率、macro-F1 | top-1 准确率、Brier |
| score | MAE、二次加权 kappa（QWK） | 期望值 MAE、Brier |
| 全包 | 按 lang x kind x domain x **source** 分层报告 | 校准：ECE（等宽 10 箱，只算 ok 行） |

报告要求：

- 本包语言：{langs}。按原语、域与来源分层报告；**来源分层是本包的硬约束**（见 README.md
  「来源均衡」），目的是让总分不被单一来源主导，不是为了给来源排名；
- 不给排行榜、不做显著性包装；样本 {counts['items']} 条，小差异不可解读；
- 阈值与校准参数**不得**在本包上选（那会让它失去盲测意义）。

## 4. 与仓库其它评测器的关系

**不复用**。仓库里的 benchmark/pol2/evaluate.py 面向 PoL2 的治理判定数据
（cases/labels 是 status / issues / action / evidence 那一套），本包是来源原生的 typed decision
（noul / choice / score + answer / probs），两者输入 schema 不同，不能直接喂给它，也不要为了喂进去而改写标签。

复用的只是**约定**：不联网、不排名、不写回数据、stdout 固定 UTF-8、退出码 0=成功 / 2=校验失败、
ECE 等宽 10 箱。若以后要统一评测口径，建议单独写一个 decision 评测器，而不是改本包或改 pol2 评测器。

## 5. 完整性校验

在本目录内运行（标准库，不联网）：

    python verify.py

校验四件事并在最后打印结论：

1. 包内每个文件 sha256 与 manifest.json 一致；
2. 从 benchmark.jsonl 复算的条数、语言/域/原语分布、问题数、真值覆盖、来源分布与 manifest 一致；
3. 明文与解压后的数据**不含裸 U+2028 / U+2029 / U+0085**（这些字符会被 str.splitlines() 当换行）；
4. 文件**不在 git 跟踪列表里**（git ls-files 为空；顺带打印 .gitignore 命中规则作为旁证）。

退出码：0 全部通过；1 校验失败；2 环境不可用（缺文件、缺 manifest 字段、缺 git 且未加 --skip-git）。

## 6. 再分发与署名

- 本包**不得公开**；上传私有托管时设为 private。
- 若在受控范围内再分发，请保留每条记录的 source.dataset / source.revision / source.row 与本目录
  的 README.md、manifest.json。
- 逐来源许可见 manifest.json 的 sources 字段（有的来源要求署名，如 cc-by-4.0）。
"""


def write_package(directory: Path, items, *, version: str, seed: int, ratios: dict,
                  policy: dict, generation: dict, sources, known_limitations) -> dict:
    """写 README.md / USAGE.md / manifest.json，并复制包内 verify.py。

    调用方（split.py）已写好 benchmark.jsonl 与 benchmark.jsonl.gz；本函数只读它们来算哈希。
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_copy(VERIFY_TEMPLATE, directory / VERIFY_NAME)
    counts = vbp.compute_counts(items)
    card = render_card(counts, version=version, seed=seed, ratios=ratios, policy=policy,
                       generation=generation, known_limitations=known_limitations)
    usage = render_usage(counts, version=version)
    atomic_write_text(directory / "README.md", card)
    atomic_write_text(directory / "USAGE.md", usage)

    files = []
    for name, item_count in (("benchmark.jsonl", counts["items"]),
                             ("benchmark.jsonl.gz", counts["items"]),
                             ("README.md", None), ("USAGE.md", None), (VERIFY_NAME, None)):
        path = directory / name
        entry = {"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if item_count is not None:
            entry["items"] = item_count
        files.append(entry)

    manifest = {
        "schema": SCHEMA,
        "name": "pol-general-decision-base-internal-benchmark",
        "version": version,
        "private": True,
        "purpose": "模型定版后的内部盲测与版本对比。不得公开、不得进入训练或教师造数、不得据其调参。",
        "generation": generation,
        "items": counts["items"],
        "files": files,
        "verifiable_counts": counts,
        "sources": {row["dataset"]: {"revision": row["revision"], "license": row["license"],
                                     "items": row["items"]} for row in sources},
        "source_balance": policy,
        "traceability": {
            "per_record_fields": ["id", "source.dataset", "source.revision", "source.config",
                                  "source.split", "source.row", "source.license", "source.url",
                                  "meta.converter", "meta.converter_version"],
            "note": "每条记录的 source.* 指向原始数据集与行号；manifest 只含聚合。",
        },
        "known_limitations": list(known_limitations),
        "privacy": {
            "git_ignored": True,
            "red_lines": ["不得公开（上传私有托管时设为 private）",
                          "不得进入训练 / 蒸馏 / 教师造数",
                          "不得依据本包调阈值或选超参",
                          "不得把内容写入公开文件、公开日志、测试夹具或提交信息"],
            "tracked_scan": "所有被 git 跟踪的文件对 benchmark 的 id 与正文零命中"
                            "（test_split.SecrecyTest 每次运行都验）",
        },
    }
    atomic_write_text(directory / "manifest.json",
                      json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    return {"directory": directory.as_posix(), "items": counts["items"], "card": "README.md",
            "usage": "USAGE.md", "manifest": "manifest.json", "verify": VERIFY_NAME}
