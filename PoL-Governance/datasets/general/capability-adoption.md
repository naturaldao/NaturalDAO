# 通用能力补源接入（最终版）：bigbench + cosmos_qa

- 日期：2026-10-20（UTC+8）｜执行：db-adopt（DSH Agent Team）｜分支：pol/DATA-02/wenbo
- 上一版：2026-10-15 v0.1（严格卡 16 选项上限、不抽样，152,580 条）→ **本版 v0.2**
- 本版变更（用户已批准）：① **放宽 >16 选项上限**（契约 §2.1 对 origin=source 本就不设上限）；② 合并量缩到**全量候选的 1/4**（用户允许 1/3–1/6）；③ bigbench **按 config 分层抽样**、cosmos_qa **全取**；④ 目标：合并后“工具与行动选择”≈ 20%
- 产物：**D:\pol2-raw\capability-final\**（上一轮 D:\pol2-raw\capability-raw\ 保留作对照）
- 边界：仍然**只做接入准备，不做合并**——不改四区划分、不改 items.final、不跑 split.py、不改任何现有数据/文档

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 候选语料 | **51,057 条** = 全量候选 205,416 的 **24.86%**（≈1/4，落在允许的 1/3–1/6 内） |
| 构成 | bigbench **25,795**（config 分层抽样）+ cosmos_qa **25,262**（全取） |
| 质量门槛剔除 | **仅 7,151 条**（全部是 unit_conversion 原生无选项）；上一轮卡 16 丢掉的 **52,836 条已全部收回** |
| **合并后工具与行动选择** | **60.20% → 20.00%**（目标达成；训练口径 56.65% → 14.76%） |
| 单一来源集中度 | bigbench 候选内 **50.52%**、**合并后 33.74%**；cosmos 合并后 33.04%。两者都远低于 50% 红线，也低于 sources.json 的 40% 参考线 |
| 合约校验 | native_item_errors **schema_issues = 0**；coverage.py 无 schema 警告、退出码 0 |
| 确定性 | 同参数连跑两次，items / rejects / sampled-out 的 sha256 **逐字节相同** |
| 位置偏置 | 打散前 chi2 **7,759**（df 70，最大单格 0.69）→ 打散后 **68.59**（df 70，p≈0.55），无偏置证据 |

一句话：**选项上限按契约放开、抽样把量级压到 1/4、工具维精确落到 20.00%、bigbench 合并后 33.74%（已接近“cosmos 全取 + tool 20%”下的理论下界 33.27%）**。

> **⚠️ 如实定性（Lead 决定 1，2026-10-20）**：本批让语料从「工具主导 60.20%」变成「阅读理解 43.14% + 数学与形式逻辑 28.46%」——
> **这是换了一种偏斜，不是消除偏斜**。合并后六维是 43.1 / 28.5 / 20.0 / 5.7 / 2.0 / 0.8（%），
> 世界知识与因果/反事实两维合计仅 **2.72%**。下一轮要补的是**世界知识/因果类来源**，不是继续在 bigbench 与 cosmos 之间挪量。
> 各维度「谁在撑 / 是否凑数」见 §12.3。口径提示：本节 20.00% 是 README 公开三分区口径（25,405 + 51,057 = 76,462）；
> 按 db-bench 的构建口径（items.final 23,855 + 51,057 = 74,912 切分语料 / 78,060 产品）是 **21.58% / 20.71%**，交叉表见 §12.6。

## 1. 交付物与位置

| 路径 | 内容 | 大小 |
|---|---|---|
| D:\pol2-raw\capability-final\items.capability.jsonl | **最终候选语料**（51,057 条） | 138,399,572 B |
| D:\pol2-raw\capability-final\rejects.capability.jsonl | 质量门槛剔除台账（逐条，7,151 行） | 750,455 B |
| D:\pol2-raw\capability-final\sampled-out.capability.jsonl | 抽样未入选台账（逐条，154,359 行） | 16,698,763 B |
| D:\pol2-raw\capability-final\capability-adoption.report.json | 机器可读报告（逐 config / 偏置 / 来源占比 / 情景） | 242,039 B |
| D:\pol2-raw\capability-final\_meta_coverage.txt | coverage.py 完整输出 | — |
| D:\pol2-raw\capability-final\capability-verify.json | verify 子命令的重读复核报告 | — |
| [datasets/general/convert_capability.py](convert_capability.py) | 接入脚本（stdlib；fetch/extract/convert/verify） | — |
| D:\pol2-raw\capability-raw\ | 上一轮 v0.1 产物与全部原始下载（parquet / CSV / fetch-manifest） | 41,067,931 B 原始 |

最终候选语料 sha256（24 位前缀）：`5AF5636CE4B4F63773951893`（items）/ `C8B9E55F5B4B6D78169A9CBC`（rejects）/ `5C88979D51C9889157E3104E`（sampled-out）。

## 2. 下载与固定 revision（与上一版一致，未重新下载）

| 来源 | dataset | revision | 许可 | 划分 | 原始行数 |
|---|---|---|---|---|---|
| P1 | tasksource/bigbench | `210c156767d2f4f05d2f4fd0bb275017a67040fd` | apache-2.0 | train | 187,305 |
| P2 | allenai/cosmos_qa | `28d9d5e2aae025e73e11177891a88dba51190013` | cc-by-4.0 | train | 25,262 |

- bigbench 走 resolve/<sha>/<path> 下载 parquet，**revision 是 URL 的一部分，逐字节可复现**；
- cosmos_qa 的 HF 仓库只有 loader，数据字节固定在 GitHub 文件级 commit `8d4d7b40d0a027c6f6095f990c3809e9396a8e6f`（与 HF sha 一并记入 fetch-manifest）；
- **只取 train**（sources.json policy）；bigbench 无 test 划分，cosmos 的 validation/test 未取。
- 33 个文件、41,067,931 B；sha256 见 D:\pol2-raw\capability-raw\_meta\fetch-manifest.json。

## 3. 转换口径（与上一版一致，只多了抽样）

条目形状**完全复用** [convert.py](convert.py) 的 --native 路径（build_native_item / native_question /
item_id / option_key / native_item_errors），与 items.native.jsonl 同形，合并时不需要第二套 schema。

| 契约字段 | bigbench | cosmos_qa |
|---|---|---|
| id | db-bigbench-<8hex> | db-cosmos-qa-<8hex> |
| domain / lang | knowledge_reasoning / en | 同左 |
| state | 原生 inputs 原文 | 原生 context 原文 |
| questions[0].key | **config 名（BIG-bench 原生任务名）** | **question（原生字段名）** |
| kind / origin / source_key | choice / source / = key | 同左 |
| questions[0].prompt | 原生 inputs 原文 | 原生 question 原文 |
| options | multiple_choice_targets（去空、去重、确定性打散） | answer0..3（去重、打散） |
| targets[key] | {"answer": <option key>}，**不写 probs** | 同左 |
| source.row | 物理行号（原生 idx 不唯一，存 meta.native_idx） | CSV 数据行号 |
| meta.capability | 数学与形式逻辑 / 阅读理解（逐 config 见 §5.3） | reading_evidence |

**答案只写硬标签**：51,057 条全部 answer_only，没有一条带 probs（自检 target_shape_bad = 0）。
契约 §1.3 禁止把单标签伪装成概率；convert.py native 路径的 point_mass() 伪 one-hot 在这里明确不用。

**能力维度归属**（沿用选型报告 P1/P2 分组，白名单 32 个 config）：数学与形式逻辑 20,021（bigbench 20 个 config）、
阅读理解与证据整合 31,036（bigbench 12 个 config 5,774 + cosmos_qa 25,262）。

## 4. 质量门槛与剔除（放宽选项上限后）

| 门槛 | bigbench | cosmos_qa |
|---|---:|---:|
| state/prompt 为空 | 0 | 0 |
| 选项为空 | **7,151** | 0 |
| **选项数上限** | **0（不设上限）** | 0（最多 4 个） |
| 答案在选项内 | 0 | 0 |
| 答案唯一 | 0 | 0 |
| 单类别（无负类）config | 0 | 0 |
| **合计剔除** | **7,151** | **0** |

- **选项上限放开的效果**：bigbench 过门槛后从 127,318 → **180,154** 条，收回 **52,836 条**，其中
  intersect_geometry 50,000 条（41 选项）、checkmate_in_one 2,768 条（13–69 选项）、
  implicit_relations 68 条。契约 §2.1 对 origin=source 明确“≥2 且不设上限”，本版按契约执行；
  --max-options 16 可一键回退到上一版口径。
- 唯一剩下的剔除是 unit_conversion 的 7,151 条：**来源自己没给选项**（multiple_choice_targets 空表），
  本轮不生成干扰项，只能剔除（占该 config 的 37.3%）。
- 没有出现单类别 config：二分类 config 的单一答案占比最高 50.3%。

## 5. 分层抽样（本版新增）

### 5.1 方法

1. **反解预算**：先算现有公开语料 25,405 条里“工具与行动选择”有 15,294 条（60.20%）；
   要让合并后占比 = --target-tool-share 0.20，合并总量须为 76,470 条 → **新语料预算 51,065 条**。
2. **cosmos_qa 全取** 25,262 条 → bigbench 预算 **25,803 条**。
3. **按 config 分层配额**：解出统一的每 config 上限 q = 使 sum(min(n_i, q)) 不超过预算的最大整数
   → **q = 1,565**（21 个 config 全取、11 个 config 压到 1,565；计划 25,795 条，与预算差 8 条）。
4. **config 内等距抽**：取 floor(j*n/k)（j=0..k-1），覆盖整个文件顺序而不是只取头部；
   不同 q 的 config 互不影响，重跑完全一致。
5. 候选 = 25,795 + 25,262 = **51,057 条**，合并后 76,462 条 → 工具与行动选择 **15,294/76,462 = 20.00%**。

为什么用“统一上限”而不是按比例：按比例会让 vitaminc_fact_verification（43,735）、intersect_geometry（50,000）、
elementary_math_qa（30,531）继续主导 bigbench 子集；统一上限让 32 个 config 里 **21 个全取、11 个各 1,565 条**，
每 config 最多占 bigbench 子集的 6.1%，是“保证多样性”最直接的做法。

### 5.2 参数与结果

| 项 | 数值 |
|---|---|
| 全量候选（不抽样） | 205,416（bigbench 180,154 + cosmos 25,262） |
| 目标“工具与行动选择”占比 | 20.00% |
| 反解的新语料预算 | 51,065 |
| bigbench 预算 / 实际选中 | 25,803 / 25,795（差 8 条，整数上限的余量） |
| config 上限 q | **1,565** |
| config 覆盖 | 21 个全取 + 11 个封顶 = 32 个全覆盖（另有 cosmos 1 个 config） |
| 抽样未入选 | 154,359 条（逐条台账 sampled-out.capability.jsonl） |
| 抽样后候选 / 全量 | 51,057 / 205,416 = **24.86%** |

### 5.3 逐 config 明细（available = 过门槛后，selected = 抽样后）

| config | 能力 | available | selected | 门槛剔除 |
|---|---|---:|---:|---:|
| formal_fallacies_syllogisms_negation | math_logic | 11,360 | 1,565 | 0 |
| logical_fallacy_detection | math_logic | 2,240 | 1,565 | 0 |
| analytic_entailment | math_logic | 54 | 54 | 0 |
| epistemic_reasoning | math_logic | 1,600 | 1,565 | 0 |
| logical_deduction | math_logic | 1,200 | 1,200 | 0 |
| logic_grid_puzzle | math_logic | 800 | 800 | 0 |
| evaluating_information_essentiality | math_logic | 52 | 52 | 0 |
| symbol_interpretation | math_logic | 795 | 795 | 0 |
| mathematical_induction | math_logic | 53 | 53 | 0 |
| known_unknowns | math_logic | 30 | 30 | 0 |
| arithmetic | math_logic | 12,019 | 1,565 | 0 |
| elementary_math_qa | math_logic | 30,531 | 1,565 | 0 |
| unit_conversion | math_logic | 12,000 | 1,565 | 7,151 |
| cs_algorithms | math_logic | 1,056 | 1,056 | 0 |
| intersect_geometry | math_logic | 50,000 | 1,565 | 0 |
| checkmate_in_one | math_logic | 2,799 | 1,565 | 0 |
| temporal_sequences | math_logic | 800 | 800 | 0 |
| date_understanding | math_logic | 296 | 296 | 0 |
| tracking_shuffled_objects | math_logic | 3,000 | 1,565 | 0 |
| navigate | math_logic | 800 | 800 | 0 |
| question_selection | reading_evidence | 1,266 | 1,266 | 0 |
| disambiguation_qa | reading_evidence | 207 | 207 | 0 |
| presuppositions_as_nli | reading_evidence | 588 | 588 | 0 |
| entailed_polarity | reading_evidence | 119 | 119 | 0 |
| winowhy | reading_evidence | 2,290 | 1,565 | 0 |
| sentence_ambiguity | reading_evidence | 44 | 44 | 0 |
| implicit_relations | reading_evidence | 68 | 68 | 0 |
| crash_blossom | reading_evidence | 22 | 22 | 0 |
| snarks | reading_evidence | 145 | 145 | 0 |
| understanding_fables | reading_evidence | 152 | 152 | 0 |
| riddle_sense | reading_evidence | 33 | 33 | 0 |
| vitaminc_fact_verification | reading_evidence | 43,735 | 1,565 | 0 |
| **allenai/cosmos_qa（default）** | reading_evidence | **25,262** | **25,262** | **0** |

## 6. 质量取证

### 6.1 答案位置偏置：来源严重偏斜，打散后归零

按选项数分层做卡方（每格期望 ≥ 5 才参与；49,475 条参与，小层单列）：

| 口径 | chi2 | df | 最大单格占比 | 结论 |
|---|---:|---:|---:|---|
| 打散前（原生位置） | **7,759.22** | 70 | **0.690** | 极强偏置：arithmetic 1,438/1,565 在位置 6、temporal_sequences 800/800 与 question_selection 1,266/1,266 在位置 0 |
| 打散后 | **68.59** | 70 | 0.5034 | 与 df 基本相等（p ≈ 0.55），**无偏置证据** |
| bigbench 打散前 | 9,678.81 | 70 | 0.827 | 同上 |
| bigbench 打散后 | 62.16 | 70 | 0.503 | 均匀 |
| cosmos 打散前 | 0.43 | 3 | 0.251 | 来源本身均衡 |
| cosmos 打散后 | 7.12 | 3 | 0.254 | 均匀 |

打散是**确定性且可复原**的：种子 = int(item id 末 8 位 hex, 16)；meta.native_option_order 给出打散后第 i 位对应的原下标，
meta.native_answer_index / meta.answer_index 给出前后位置。自检 51,057 条全部满足
options[order.index(native_answer_index)].label == native_answer_text，**0 条不一致**。

### 6.2 选项数分布（放开上限后的关键变化）

| 选项数 | 条目数 |
|---|---:|
| 2–16 | 47,880（93.8%） |
| 17–24 | 86 |
| 25–32 | 341 |
| 33–40 | 464 |
| 41+ | 2,286（其中 41 选项 1,651 条） |
| **最多** | **69** |

共 **3,177 条（6.2%）选项数 > 16**——上一版这些全被剔除。契约对 origin=source 不设上限，因此合法；
但要注意**猜测基线**：41 选项题随机猜中率 1/41，训练时这类题的 loss 尺度与 4 选 1 不同（见 §9.6）。

### 6.3 其它形状

| 维度 | 分布 |
|---|---|
| target 形态 | answer_only 51,057（无 probs、无伪 one-hot、无均匀分布） |
| 语言 | en 51,057（100%） |
| state 长度 | ≤512: 41,280｜≤1024: 8,214｜≤2048: 1,391｜≤4096: 172（未截断） |
| quality_flags | duplicate_option_merged: 10 |

### 6.4 自检与确定性

- **确定性**：同参数（--created-at 2026-10-20T17:00:00+08:00）连跑两次，items / rejects / sampled-out 的 sha256 逐字节相同。
- **顺序可复原**：51,057 条全部 bad_pos=0, bad_ans=0, bad_probs=0。
- **id 唯一**：51,057 条 0 碰撞（v0.1 的 152,580 条撞 3 次；本版条目少，未触发）。
- **保真**：bigbench 中用 "choice: X" 行内联选项的行，其内联选项多重集与 options 完全一致（0 条不一致）。

## 7. 合约校验

**（1）native_item_errors（与 items.native.jsonl 同一把校验器）**

    items: 51,057   items_with_issues: 0   issue_counts: {}   duplicate_ids: 0   schema_issues: 0

**（2）coverage.py（完整输出 D:\pol2-raw\capability-final\_meta_coverage.txt）**

    items: 51057  问题数: 51057（source 51057 / taxonomy 0）
    [domain] knowledge_reasoning 51057 100.00%
    [出题方 origin] source 51057 100.00%（缺失或非法 0 道）
    [原语 kind] choice 51057 100.00%
    [lang] en 51057 100.00%
    [source.dataset] tasksource/bigbench 25795 50.52% / allenai/cosmos_qa 25262 49.48%
    [问题键 source 原生] 共 33 个
    [通过] 无硬性违规（非空 / domain 合法 / id 唯一）
    [schema 警告] 无                                    # 退出码 0

**（3）仓库验收（tools/check.py）**：见 §9.7——失败**与本批产物无关**，
是另一处**未提交的工作区改动** datasets/general/jev-validation.md 把 benchmark id 写进了被跟踪文件，
被保密护栏 test_tracked_files_contain_no_benchmark_records 拦下。本批所有文件（含本文件）在审计里**零命中**。

## 8. 合并后构成预期（核心）

现有语料的能力维度用 README 自己的规则链重算（readme_stats.classify_capability，逐条跑公开三分区）；
新条目用 meta.capability（readme_stats 还不认识这两个来源，见 §9.5）。

### 8.1 全量合并（公开三分区口径，与 README §2.2 同口径）

| 能力维度 | 合并前 | 占比 | 合并后 | 占比 | 变化 |
|---|---:|---:|---:|---:|---:|
| 工具与行动选择 | 15,294 | 60.20% | 15,294 | **20.00%** | **−40.20pp** |
| 社会与人类判断 | 4,347 | 17.11% | 4,347 | 5.69% | −11.42pp |
| 阅读理解与证据整合 | 1,946 | 7.66% | **32,982** | **43.14%** | +35.48pp |
| 数学与形式逻辑 | 1,737 | 6.84% | **21,758** | **28.46%** | +21.62pp |
| 世界知识及其应用 | 1,491 | 5.87% | 1,491 | 1.95% | −3.92pp |
| 因果、反事实与不确定性判断 | 590 | 2.32% | 590 | 0.77% | −1.55pp |
| 合计 | 25,405 | 100% | **76,462** | 100% | |

### 8.2 训练口径（只算 train：现有 17,986 + 新 51,057 = 69,043）

| 能力维度 | 合并前 | 占比 | 合并后 | 占比 |
|---|---:|---:|---:|---:|
| 工具与行动选择 | 10,189 | 56.65% | 10,189 | **14.76%** |
| 社会与人类判断 | 3,940 | 21.91% | 3,940 | 5.71% |
| 阅读理解与证据整合 | 1,294 | 7.19% | 32,330 | 46.83% |
| 数学与形式逻辑 | 1,166 | 6.48% | 21,187 | 30.69% |
| 世界知识及其应用 | 1,003 | 5.58% | 1,003 | 1.45% |
| 因果、反事实与不确定性判断 | 394 | 2.19% | 394 | 0.57% |

### 8.3 每个来源的最终占比（合并后，共 13 个来源）

| 来源 | 现有 | 新增 | 合并 | 合并后占比 | 新语料内占比 |
|---|---:|---:|---:|---:|---:|
| **tasksource/bigbench** | 0 | 25,795 | 25,795 | **33.74%** | **50.52%** |
| **allenai/cosmos_qa** | 0 | 25,262 | 25,262 | **33.04%** | **49.48%** |
| Deepexi/openai-formate-function-calling-small | 7,872 | 0 | 7,872 | 10.30% | — |
| SargeDev/jev-distill-corpus-v3 | 7,357 | 0 | 7,357 | 9.62% | — |
| samatv256/jev-decisions-v1 | 3,610 | 0 | 3,610 | 4.72% | — |
| BEncoderRT/User_Intent_Risk_Triage | 2,061 | 0 | 2,061 | 2.70% | — |
| tasksource/procedural-typed-decisions | 1,216 | 0 | 1,216 | 1.59% | — |
| dwidlee/systemone-lite-general | 1,198 | 0 | 1,198 | 1.57% | — |
| ZefanCai/Open-Jev | 642 | 0 | 642 | 0.84% | — |
| textdetox/multilingual_toxicity_dataset | 543 | 0 | 543 | 0.71% | — |
| chenhaodev/med-guard-safety-synth | 472 | 0 | 472 | 0.62% | — |
| kaivoss/system-one-270m-data | 362 | 0 | 362 | 0.47% | — |
| vanila434/multilingual-elder-safety-msgs | 72 | 0 | 72 | 0.09% | — |

### 8.4 单一来源集中度：33.74% 已是“cosmos 全取 + tool 20%”约束下的下界附近

Lead 的点：bigbench 在能力候选集里约 88%，只取 1/4 也可能占合并后 55%+。本版实测：

- bigbench **候选内占 50.52%**，**合并后占 33.74%**——远低于 50% 红线，也低于 40% 参考线。
- **理论下界**：cosmos 固定 25,262 条、bigbench 取 N_c、合并总量 T = 25,405 + 25,262 + N_c；
  两个新来源占比相等时 max 最小，解得 N_c = 25,262 → T = 75,929 → **max = 33.27%**。
  本方案 33.74% / 33.04%，与下界相差 0.5pp，差异来自“把工具维精确压到 20.00%”（T 略大）。
  **也就是说：在“cosmos 全取”的前提下，单一来源占比不可能低于约 33.3%**；要再低只能动 cosmos 或抬 tool 占比。
- 与历史数字的关系（口径不同，只作参照）：现有公开三分区最大单一来源是 Deepexi 7,872/25,405 = **31.0%**，
  合并后最大 33.74%（+2.7pp）；历史上 items.native 的单一来源是 **48.5%**（CONTRACT §6.11），本版明显改善；
  benchmark 侧的 24.97% 是另一套 1,600 条集合，不能直接与训练侧比。
- **若要 max ≤ 31%**（对齐现有语料）：需两个新来源都下采样到约 **20,725** 条（cosmos 取 82%），
  合并后 66,855 条、tool 占比升到 **22.9%**——仍在“约 20%”附近。当前脚本**只对 bigbench 抽样**，
  要做这个变体需要给 cosmos 也加一个抽样参数（未实现，等 Lead 裁决）。

### 8.5 情景表（新语料整体缩放）

| 情景 | 新语料 | 合并总量 | 工具与行动选择 | 数学与形式逻辑 | 阅读理解与证据整合 |
|---|---:|---:|---:|---:|---:|
| **final（本方案）** | 51,057 | 76,462 | **20.00%** | 28.46% | 43.14% |
| full_candidate_no_sampling（不放抽样） | 205,416 | 230,821 | 6.63% | 57.72% | 32.87% |
| bigbench_only（只接 bigbench 抽样部分） | 25,795 | 51,200 | 29.87% | 42.50% | 15.08% |
| cosmos_only（只接 cosmos） | 25,262 | 50,667 | 30.19% | 3.43% | 53.70% |
| final_half（本方案的 1/2） | 25,528 | 50,933 | 30.03% | 23.06% | 34.29% |
| final_third（1/3） | 17,019 | 42,424 | 36.05% | 19.83% | 28.97% |
| final_sixth（1/6） | 8,510 | 33,915 | 45.10% | 14.96% | 20.99% |

## 9. 契约不匹配、风险与待裁决

### 9.1 【已解决】选项上限：按契约放开

上一版误按 taxonomy 的 16 卡 origin=source，丢了 52,836 条；本版按契约 §2.1 放开，全部收回（见 §4）。
--max-options 16 保留了一键回退。

### 9.2 【新观察，建议 Lead 取舍】阅读理解成为新的最大维度 43.14%

工具维从 60.20% 压到 20.00% 之后，**阅读理解与证据整合升到 43.14%**（其中 cosmos_qa 独立贡献 25,262 条 = 33.04%）。
这不是抽样失误，而是“cosmos 全取 25,262 条”与“tool ≈ 20%”两条约束共同决定的：cosmos 一条就占合并语料的 1/3，
而它整份属于阅读理解。三种处理方式：

1. **接受**（本版现状）：最大维度从 60.20% 降到 43.14%，已是显著改善；且 43% 里有 33pp 是单一来源的整份贡献，
   来源内部并不偏科。
2. **给 cosmos 也加分层/截断**：例如 cosmos 取 19,045 条 → 阅读理解降到约 35%（总量随之变化，需重算），
   代价是 tool 占比升到约 21.8%、且需要新增 cosmos 抽样参数。
3. **回调 --target-tool-share**：目标 0.25 → 新语料约 3.6 万条，reading 会降到约 38%，tool 25%。

### 9.3 伪 one-hot：本候选不造，但与既有 native 路径不一致

convert.py native 路径对硬标签写 point_mass()（选中 1.0 / 其余 0.0），与契约 §1.3、§2.3 冲突。
本候选 51,057 条**全部只写 answer**。合并后同一训练集里会并存两种真值形态；建议合并时按 §2.3 判别过滤，
或加 targets[key].provenance。

### 9.4 source.row 不能用原生 idx

原生 idx 在多个 config 里不唯一（unit_conversion 19,151 行只有 2,400 个、elementary_math_qa 30,531 行只有 6,151 个）。
本版 row = 物理行号，原生 idx 存 meta.native_idx。任何后续接 tasksource 系数据集的人都该知道。

### 9.5 readme_stats.classify_capability 必须先加规则

该函数按 source.dataset 分派，目前不认识这两个来源，**会把 51,057 条全部归到 other**。
合并前需要在 [readme_stats.py](readme_stats.py) 加两条规则（建议 C9：bigbench 按 meta.native_task 查 §5.3 的表；
C10：cosmos_qa 整份 reading_evidence），否则 README 的分布审计会失真。该文件属 db-schema，不在本任务写范围。

### 9.6 来源侧的形状缺口与训练侧提示（不是我们的门槛问题）

- unit_conversion 19,151 条里 7,151 条（37.3%）原生无选项，只能剔除。
- 选项数 41–69 的题（3,177 条，6.2%）猜测基线低（1/41 起），与 4 选 1 混训会带来 loss 尺度差异；
  建议训练侧按选项数分层看指标，或对 >16 选项的题单独降权（本版先按契约全收）。

### 9.7 保密护栏：外部文件曾变红、Lead 已重新匿名；定稿时仓库红是并发合并作业

- 交付过程中 tools/check.py 曾退出 1：756 个测试只有 1 个失败（test_tracked_files_contain_no_benchmark_records），
  命中文件是 datasets/general/jev-validation.md（当时是**未提交**的工作区改动，不在 HEAD），其中 28 个 benchmark id 被写进示例表。
- **Lead 已全部重新匿名（64 处，残留 0）**。此后复跑：审计扫 325 个被跟踪文件 **0 命中**，
  tools/check.py 通过（local_links 346）。
- **定稿窗口（17:06 起）仓库处于合并作业中，门禁红是合并尾部，既不是泄漏也不是本批**：
  17:06:28–35 db-bench 重写了 splits/benchmark（items.final 17:03 从 82 MB 长到 221 MB，正是本批 51,057 条合入）。
  17:14 复跑：**保密审计 0 命中**（扫 325 个被跟踪文件；本批产物零命中；benchmark 与 public 三区重复 state = 0），
  但 `tools/check.py` 仍有 **5 个失败**，全部落在合并尾部、与本批无关：
  - `test_split.SourceFloorTest` × 2 —— db-bench 正在改的来源配额/floor 逻辑；
  - `test_target_types.SidecarTest` × 3 —— `data/target-types.jsonl.gz` 侧挂索引尚未按新切分重建（属 db-tests）。
  合并收尾必须：重跑 `tools/check.py`、重建 target-types 侧挂文件。**本批自身验收（schema_issues=0、coverage 退出码 0）不受影响。**
- 过程教训（本批自查记录）：我最初在 §9.7 引用那个 benchmark id 当证据，**这本身也构成一次泄漏**——已打码。
  **成员身份（benchmark id）本身就是敏感信息，即使不带答案**；后续任何报告都不得引用 benchmark id 原文。

### 9.8 其它

- **语言 100% 英文**：本批对中国语料零贡献，选型报告 §4.5 的“中文世界知识空洞”未被填补。
- **state 与 prompt 重复**（bigbench 无独立情境字段），51,057 条 138 MB（约 2.7 KB/条）。
- **id 碰撞**：本版 0 次（条目量小）；若将来回到 20 万条级别，32 位 id 仍会撞（上一版实测 3 次），
  建议契约层考虑把 hex 位宽提到 10–12 位。
- **能力维度是“来源标签经固定映射”**，不是独立人工标注（与 README §2.5 的自述一致）。

## 10. 复算命令

    # 0) 仓外 venv（只为读 parquet；仓库保持 stdlib-only）
    uv venv D:\pol2-raw\capability-raw\.venv
    uv pip install --python D:\pol2-raw\capability-raw\.venv\Scripts\python.exe pyarrow

    # 1) 下载（已有缓存会跳过；sha256 写 _meta\fetch-manifest.json）
    uv run --no-project --offline python datasets/general/convert_capability.py fetch

    # 2) parquet -> rows.jsonl（187,305 行）
    D:\pol2-raw\capability-raw\.venv\Scripts\python.exe datasets/general/convert_capability.py extract

    # 3) 转换 + 分层抽样 + 报告（--created-at 固定后逐字节可复现）
    uv run --no-project --offline python datasets/general/convert_capability.py convert --created-at 2026-10-20T17:00:00+08:00 --target-tool-share 0.20

    # 4) 重读产物复核（schema + 位置偏置 + 来源占比 + 合并预期）
    uv run --no-project --offline python datasets/general/convert_capability.py verify

    # 5) 契约校验（外部）
    uv run --no-project --offline python datasets/general/coverage.py --items D:\pol2-raw\capability-final\items.capability.jsonl

    # 6) 仓库验收（Lead 重新匿名后已通过；过程见 §9.7）
    uv run --no-project --offline python tools/check.py

    # 变体：不放抽样 / 回退选项上限 / 换目标占比
    uv run --no-project --offline python datasets/general/convert_capability.py convert --no-sample
    uv run --no-project --offline python datasets/general/convert_capability.py convert --max-options 16
    uv run --no-project --offline python datasets/general/convert_capability.py convert --target-tool-share 0.25

## 11. 本轮明确未做

- 未合并、未改四区划分、未改 items.final、未跑 split.py、未改任何现有文档与数据。
- 未给 cosmos_qa 做抽样（Lead 指定全取）；§8.4 的 max≤31% 变体因此未生成。
- 未做语义近重复/同族检测（与 CONTRACT §6.5 一致），也未与现有 25,405 条做跨来源去重。
- 未做训练实验：本文件只能说“补进了多少条什么能力的监督信号”，**不能**说明“训练后模型智力不退化”。
- **下一轮方向（Lead 决定 1）**：补世界知识 / 因果-反事实类来源，而不是继续在 bigbench 与 cosmos 之间挪量
  （理由与量化现状见 §0 的警示框与 §12.3）。

## 12. 交接（给 db-bench，2026-10-20 定稿）

### 12.1 交付物与校验和

| 项 | 值 |
|---|---|
| **候选语料** | **D:\pol2-raw\capability-final\items.capability.jsonl** |
| 条数 | **51,057** |
| 字节数 | 138,399,572 |
| **sha256（全量 64 位）** | `5af5636ce4b4f63773951893bae082d089d73d1c87efe7021cb7355e0c1edb78` |
| 门槛剔除台账 | D:\pol2-raw\capability-final\rejects.capability.jsonl（7,151 行） |
| 抽样未入选台账 | D:\pol2-raw\capability-final\sampled-out.capability.jsonl（154,359 行） |
| 机器可读报告 | D:\pol2-raw\capability-final\capability-adoption.report.json |
| fetch 溯源 | D:\pol2-raw\capability-raw\_meta\fetch-manifest.json（33 个原始文件 + sha256） |
| 复现参数 | `convert --created-at 2026-10-20T17:00:00+08:00 --target-tool-share 0.20`（两跑逐字节一致） |

三个产物的 sha256 已写进机器报告的 `artifacts` 段（`items_sha256` / `rejects_sha256` /
`sampled_out_sha256`），重跑可用同参数核对。定稿前实测 items 哈希与上一次抽样运行**完全相同**（脚本改动只影响报告字段）。

### 12.2 id 前缀与冲突检查（给 db-bench）

- 本批 id 只有两种前缀：**`db-bigbench-<8hex>`（25,795 条）** 与 **`db-cosmos-qa-<8hex>`（25,262 条）**；
- 8hex = sha256(dataset|revision|config|split|row) 前 8 位（与既有语料同一套 `convert.item_id` 规则）；
  `source.slug` 分别是 `bigbench` / `cosmos-qa`；
- **与既有语料实测零冲突**（不是推断，是逐 id 比对）：
  - 现有公开三分区 25,405 条、12 个 id 前缀：`db-deepexi-fcs-v3`(7,872) / `db-jev-distill-v3`(7,357) /
    `db-jev-decisions-general-50k`(3,415) / `db-zhtax-harm-severity`(1,517) /
    `db-procedural-typed-decisions`(1,216) / `db-systemone-lite-general`(1,198) / `db-open-jev`(642) /
    `db-zhtax-contains-harm`(544) / `db-zhtax-escalation-needed`(544) / `db-zhtax-toxicity-present`(543) /
    `db-system-one-270m`(362) / `db-jev-decisions-strata`(195)；
  - 与 `db-bigbench-` / `db-cosmos-qa-` **交集 = 0**；
  - 合并后 25,405 + 51,057 = **76,462 条，distinct id = 76,462**（无重复）；本批内部 0 碰撞，id 形状全部匹配 `^db-[A-Za-z0-9._-]+-[0-9a-f]{8}$`。
- 本批条目自带：`domain=knowledge_reasoning`、`lang=en`、`kind=choice`、`origin=source`，
  `source.{dataset,revision,config,split,row,license,url,slug}` 全齐；`meta.capability` 是本批新增字段（six-dim 口径）。

**前缀冻结（与 db-bench 2026-10-20 确认）**：`db-bigbench-` / `db-cosmos-qa-` 为**最终约定、不再变更**——
只要脚本里 `BIGBENCH["slug"]="bigbench"`、`COSMOS["slug"]="cosmos-qa"` 不动，同参数重生成逐字节一致（已实测两次 sha256 相同）。
若将来必须改 slug，需 Lead 批准并提前通知 db-bench（合并后的 id 会全变）。
**解析注意**：本批与旧语料的前缀都**自带连字符**（`cosmos-qa`、`jev-decisions-general-50k`），
按 `split("-")` 取前缀会截错（db-bench 实测得到 `db-cosmos`）；消费方请直接用 `source.slug` / `source.dataset`，
或按贪婪正则 `^db-(.+)-([0-9a-f]{8})$` 取分组。

### 12.3 合并后能力维度构成（六维，公开三分区口径 76,462 条）——谁有量、谁在凑数

| 能力维度 | 合并后 | 占比 | 现有贡献 | 本批贡献 | 来源数 | 最大来源（维内占比） | 定性 |
|---|---:|---:|---:|---:|---:|---|---|
| 阅读理解与证据整合 | 32,982 | 43.14% | 1,946 | **31,036** | 3 | cosmos_qa 76.59% | **有量，但单源主导**（94.1% 由新语料撑起） |
| 数学与形式逻辑 | 21,758 | 28.46% | 1,737 | **20,021** | 4 | bigbench 92.02% | **有量，但单源主导**（92.0% 由新语料撑起） |
| 工具与行动选择 | 15,294 | 20.00% | 15,294 | 0 | 7 | Deepexi 51.47% | **真有量且多源**（本批未增强） |
| 社会与人类判断 | 4,347 | 5.69% | 4,347 | 0 | 7 | BEncoderRT 47.41% | 中等体量、来源分散（本批未增强） |
| 世界知识及其应用 | 1,491 | 1.95% | 1,491 | 0 | 2 | jev-distill 97.18% | **凑数级**：量小且 97% 单一来源 |
| 因果、反事实与不确定性判断 | 590 | 0.77% | 590 | 0 | 3 | jev-distill 81.53% | **凑数级**：量最小、单一来源 81% |

读法（也是给下一轮的方向）：

- 本批**真正补的只有两个维度**（reading +31,036、math +20,021）；其余四维**一条没加**，占比是被稀释下来的；
- 「凑数」的两维（world 1.95% + causal 0.77%）合计仅 **2.72%**，且 81–97% 来自单一来源——
  表里有数字、但没有覆盖面，**下一轮补源第一优先级就在这里**；
- reading / math 量足但维内集中（76.6% / 92.0% 来自单一来源），属于「有量但换了一种偏斜」；
- tool 的 7 个来源、top 51.5%，social 的 7 个来源、top 47.4%，是六维里来源结构最健康的两维。

### 12.4 db-bench 合并时必做的三件事

1. **给 `readme_stats.classify_capability` 加两条规则**（属 db-schema，不在我写范围）：
   C9 = bigbench 按 `meta.native_task`（32 个 config，查本报告 §5.3 的能力表）；C10 = cosmos_qa 整份 `reading_evidence`。
   不加规则，这 51,057 条会**全落 `other`**（合并后分布会假性塌陷）。
2. **处理伪 one-hot 并存**：本批只写 `targets[k].answer`（无 probs）；既有语料有 14,119 个伪 one-hot 问题。
   合并后建议按 CONTRACT §2.3 判别过滤，或加 `targets[key].provenance`，不要直接混着训。
3. **重切划分只走私有盐**：本批只有 train，合并进 items.final 后需重新切分；本轮**没有**跑 split.py，
   合并时按既有流程（仓外盐、`--input/--out/--report` 显式外指）。

### 12.5 建议写入 README 的如实措辞（供 db-bench / Lead 取用）

> 2026-10-20 增补 tasksource/bigbench + allenai/cosmos_qa 共 51,057 条（items.final 23,855 → 合并切分语料 74,912，产品 78,060）。
> 六维构成由「工具与行动选择一家独大」变为「阅读理解 42.41% + 数学与形式逻辑 28.22% + 工具 20.71%」
> （构建口径 78,060；README 原公开三分区口径是 60.20% → 20.00%，两种口径都要标分母）。
> **这是换了一种偏斜，不是消除偏斜**：世界知识（2.02%）与因果/反事实（0.83%）两维合计仅 2.85%，
> 且维内 81–96% 来自单一来源，是下一轮补源的第一优先级。按来源看，最大单一来源为 bigbench 34.43%（切分语料口径；
> 产品口径 33.05%），低于 40% 参考线；在「cosmos 全取 + 工具维约 20%」约束下其理论下界约 33%。
> 增补的 51,057 条全部为 `origin=source` 的原生选项题、硬标签（无伪造概率）、只取 train。

### 12.6 与 db-bench 切分语料口径对齐（2026-10-20 直接确认）

db-bench 的合并计划是「23,855 + 51,057 = 74,912 为切分语料，中文补充集仍只在 train 追加，产品 78,060」。
这与本报告 §8 用的「公开三分区 25,405」不是同一口径。**两者都没错，但要各标各的分母**；交叉表如下（全部实测）：

| 量 | 值 | 关系 |
|---|---:|---|
| items.final（英文底料） | **23,855** | 含现 benchmark 1,598，不含中文补充 |
| 现 benchmark（加盐 v2） | 1,598 | 从 items.final 切出 |
| 公开三分区（train+test+validation） | **25,405** | = 23,855 − 1,598 + 3,148（README §2.2 口径） |
| 中文补充（只在 train 追加） | 3,148 | 不参与切分 |
| 本批新增 | **51,057** | — |
| **合并切分语料**（db-bench 计划） | **74,912** | = 23,855 + 51,057 |
| **合并后产品** | **78,060** | = 74,912 + 3,148 |

**六维构成（db-bench 构建口径）**

| 能力维度 | 合并切分语料 74,912 | 占比 | 产品 78,060 | 占比 |
|---|---:|---:|---:|---:|
| 工具与行动选择 | 16,165 | 21.58% | 16,165 | **20.71%** |
| 社会与人类判断 | 1,394 | 1.86% | 4,542 | 5.82% |
| 阅读理解与证据整合 | 33,106 | 44.19% | 33,106 | **42.41%** |
| 数学与形式逻辑 | 22,028 | 29.41% | 22,028 | **28.22%** |
| 世界知识及其应用 | 1,574 | 2.10% | 1,574 | 2.02% |
| 因果、反事实与不确定性判断 | 645 | 0.86% | 645 | 0.83% |
| 合计 | 74,912 | 100% | 78,060 | 100% |

**口径纠正（给 db-bench，实测）**：其来信的 20.42% = 15,294 / 74,912 是**混口径**——15,294 是公开三分区口径
（已剔除现 benchmark 的 871 条 tool 项），而 74,912 是 items.final + 新增（**含**那 1,598 条 benchmark，其中 tool 871 条）。
按 74,912 的正确分子是 **16,165**：

- **合并切分语料：21.58%**（16,165 / 74,912）
- **产品：20.71%**（16,165 / 78,060）

两者都仍在「约 20%」区间，但 README 必须写清用的是哪个分母。

**三条路线（任选其一，分子分母必须同口径）**

| 路线 | 合并池 | 切分语料 | 产品 | 工具占比（切分 / 产品） | 对现 benchmark 的影响 |
|---|---|---:|---:|---|---|
| A（db-bench 计划） | items.final 23,855 + 新增 | 74,912 | 78,060 | 21.58% / 20.71% | 1,598 条回池，需重切（v3） |
| B（保 v2 不重切） | 公开英文部分 22,257 + 新增 | 73,314 | 76,462 | 20.86% / **20.00%** | 现 benchmark 不动 |
| C（README 口径） | 公开三分区 25,405 + 新增 | 76,462 | 76,462（已含补充） | 20.00% / 20.00% | 需重切，且补充已在池内 |

- 路线 A 与现有构建流水线（先 items.final 切四区、再把补充追加到 train）一致，代价是 benchmark 必须重画；
  若 Lead 接受「合并即重切 benchmark」，A 就是正确口径。
- 若要求**冻结现 benchmark v2**，只能用 B：新增数据只能进 train/dev（不参与 benchmark 抽样），
  此时产品口径仍是 20.00%。
- 无论哪条路线，本批 51,057 条的 id / sha256 / 字段形状都不变（见 §12.1、§12.2）。

### 12.7 as-built：合并已执行（2026-10-20 17:07–17:10 快照）

交付后 db-bench 已把本批并入并重切（17:06:28–17:06:35）；此后仍有微调。快照实测：

| 分区 | 条数 |
|---|---:|
| train | 48,619 |
| test | 15,157 |
| validation | 7,579 |
| **public 三区** | **71,355** |
| benchmark（新 v3） | 6,705 |
| **产品总量** | **78,060** |

- **本批 51,057 条全部并入（0 丢失）**；分布：train 31,799 / test 10,581 / validation 5,327 / benchmark 3,350。
- **as-built 六维（public 三区 71,355）**：tool 14,392 (20.17%) / social 4,255 (5.96%) / reading 30,666 (42.98%) /
  math 20,305 (28.46%) / world 1,240 (1.74%) / causal 497 (0.70%)。
- **as-built 六维（产品 78,060）**：tool 16,165 (20.71%) / social 4,542 (5.82%) / reading 33,106 (42.41%) /
  math 22,028 (28.22%) / world 1,574 (2.02%) / causal 645 (0.83%)。
- 产品来源占比：bigbench **33.05%**、cosmos **32.36%**、Deepexi 10.08%、jev-distill 9.94%、jev-decisions 5.14%；
  最大单一来源 33.05%（<40% 参考线）。
- 新 benchmark（6,705，占产品 8.59%）来源已均衡：bigbench 24.98% / cosmos 24.98% / jev-distill 24.27% /
  jev-decisions 12.50% / procedural 4.68%——本批两个来源在 benchmark 内各约 25%，没有把 benchmark 单一来源推高。
- **训练侧实际偏斜比合并前估算更薄**：public 三区里 reading 42.98% + math 28.46% + tool 20.17% = 91.61%，
  世界知识 1.74% 与因果 0.70% 合计仅 **2.44%**（合并前估算 2.72%），因为本批有 3,350 条进了 benchmark。
  「换了一种偏斜、不是消除偏斜」这个判断在 as-built 数据上更成立。

**注意**：以上是 17:07–17:10 快照；db-bench 在测量后仍在微调（.jsonl 与 .gz 出现过短暂不同步）。
最终以 db-bench 提交的 split-manifest / README 为准；本节的用途是给合并结果做一次独立复核。

## 附录 A：v0.1 → v0.2 关键数字对照

| 项 | v0.1（2026-10-15） | v0.2（2026-10-20） |
|---|---|---|
| 选项上限 | 16（误用于 origin=source） | **不设上限（契约口径）** |
| bigbench 过门槛 | 127,318 | **180,154** |
| 剔除 | 59,987（选项超限 52,836 + 无选项 7,151） | **7,151（只剩无选项）** |
| 抽样 | 无（全量） | **config 分层，q=1,565** |
| 候选语料 | 152,580 | **51,057（24.86%）** |
| 合并后总量 | 177,985 | **76,462** |
| 工具与行动选择 | 60.20% → 8.59% | 60.20% → **20.00%** |
| 阅读理解 | 42.59% | 43.14% |
| 数学与形式逻辑 | 45.20% | 28.46% |
| bigbench 合并后占比 | 71.5% | **33.74%** |
| 单一来源最大值 | 71.5%（参考线 40%） | **33.74%（低于参考线）** |
| schema_issues | 0 | 0 |
