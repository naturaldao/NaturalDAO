# 最终语料合并报告（items.final）

- 英文侧：data/items.native.jsonl 全量 **15,983 条**
- 中文侧：D:\pol2-raw\zh-final\items.zh.jsonl 按变体规则抽取 **7,872 条**
- 合计 **23,855 条**，**中文占比 33.00%**（目标 33%，目标条数 7,872）
- 抽取种子：**general-merge-v1**（按 sha256(seed + group_id) 升序补 variant 1，可复算）
- id 冲突：0

## 中文侧怎么取的

| 步骤 | 规则 | 条数 |
|---|---|---:|
| 1 | 每个 group 取 variant_index = 0 | 5,454 |
| 2 | 不足目标时按 sha256(seed + group_id) 升序补 variant_index = 1 | 2,418 |
| 合计 | 覆盖 5,454 个唯一请求（共 5,454 个） | 7,872 |

## 为什么取 33% 而不是 40%

Deepexi 是唯一中文来源，因此中文占比即该来源占比；取 33% 而非 40%，是给'单一来源 ≤40%'留余量，且多取的变体来自同一批请求、边际信息量递减。

## 分布

| | 英文 | 中文 | 合计 |
|---|---:|---:|---:|
| 条数 | 15,983 | 7,872 | 23,855 |
| 带真值 | 15,983（100.0%） | 7,872（100.0%） | 23,855（100.0%） |
| 语言 | {'en': 15983} | {'zh': 7872} | — |
| 显式 group 数 | 792 | 5,454 | — |

域分布（合计）：

| domain | 条数 |
|---|---:|
| decision_mechanics | 19,465 |
| knowledge_reasoning | 4,390 |

## 两条硬要求怎么保证的

1. **group_id 原样保留**：合并脚本只做「挑哪几行」，逐行原样复制，不做 JSON 往返序列化；中文侧顶层 group_id / request_id、source.group_id、meta.group_id 全部原封不动。
2. **候选顺序不被改回**：同样因为逐行复制，中文侧已确定性打散的候选顺序（含 meta.target_position 与 meta.original_target_position 的差异）原样保留。

## 复算

    uv run --no-project --offline python datasets/general/merge.py \
        --en datasets/general/data/items.native.jsonl \
        --zh D:\pol2-raw\zh-final\items.zh.jsonl \
        --out datasets/general/data/items.final.jsonl --share 0.33 --seed general-merge-v1
