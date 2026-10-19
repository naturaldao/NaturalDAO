# 通用能力补源接入（准备）：bigbench + cosmos_qa

- 日期：2026-10-15（UTC+8）｜执行：db-adopt（DSH Agent Team）｜分支：pol/DATA-02/wenbo
- 上游依据：选型报告 [capability-sources.md](capability-sources.md)（P1 [tasksource/bigbench](https://huggingface.co/datasets/tasksource/bigbench)、P2 [allenai/cosmos_qa](https://huggingface.co/datasets/allenai/cosmos_qa)）
- 契约：[CONTRACT.md](CONTRACT.md)（字段与形状）｜分布口径：[README.md](README.md) 第 2 节（六维能力口径）
- **本轮只做接入准备，不做合并**：不改四区划分、不改 items.final、不跑 split.py、不改任何现有数据与文档。
- 产物全部落仓库外 D:\pol2-raw\capability-raw\；仓库内**新增且只新增**本文件与 [convert_capability.py](convert_capability.py)。

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 转出候选语料 | **152,580 条**（bigbench 127,318 + cosmos_qa 25,262） |
| 剔除 | **59,987 条**，全部来自 bigbench，只有两类理由：选项数 > 16（52,836）、原生无选项（7,151） |
| 合约校验 | native_item_errors：schema_issues = **0**；coverage.py：无 schema 警告、退出码 0；tools/check.py：退出码 0 |
| 能力维度（候选内） | 数学与形式逻辑 78,717 / 阅读理解与证据整合 73,863 |
| **合并后 60.20% 会降到** | **8.59%**（公开三分区口径，合并后 177,985 条）；训练口径 56.65% → 5.97% |
| ⚠️ 同时必须看到的 | 候选语料是现有语料的 **6.0 倍**。全量合并不是"再平衡"而是"翻盘"：数学+阅读合计 87.8%，bigbench 单一来源占 **71.5%**（sources.json 参考上限 40%）。第 7 节给了 6 个缩放情景，回落到 30.09% 需要把新语料缩到 1/6 |

一句话：**两个来源都接得上、质量门槛全过、契约零违规**；但"全量合并"会让天平从"工具主导"直接翻成"数学+阅读主导"，
所以真正要裁决的不是"接不接"，而是**"接多少"**（第 7、8 节）。

## 1. 交付物与位置

| 路径 | 内容 | 大小 |
|---|---|---|
| D:\pol2-raw\capability-raw\items.capability.jsonl | **候选语料**（152,580 条，可直接合并的 items） | 389,755,783 B |
| D:\pol2-raw\capability-raw\rejects.capability.jsonl | 剔除台账（逐条：dataset/config/row/reason） | 7,809,752 B |
| D:\pol2-raw\capability-raw\capability-adoption.report.json | 机器可读报告（逐 config、位置偏置、合并情景） | 60,699 B |
| D:\pol2-raw\capability-raw\capability-verify.json | verify 子命令的重读复核报告 | 17,303 B |
| D:\pol2-raw\capability-raw\_meta\fetch-manifest.json | 33 个原始文件的 url + sha256 + bytes | — |
| D:\pol2-raw\capability-raw\bigbench\<config>\train-*.parquet / train.jsonl | 原始 parquet 与抽出的行 | 24,407,482 B |
| D:\pol2-raw\capability-raw\cosmos-qa\train.csv | 原始 CSV | 16,660,449 B |
| D:\pol2-raw\capability-raw\_meta\coverage-candidate.txt | coverage.py 完整输出 | — |
| [datasets/general/convert_capability.py](convert_capability.py) | 接入脚本（stdlib；fetch/extract/convert/verify） | — |

候选语料 sha256（16 位前缀）`0ed4be7db90925e7`（items）/ `1f00bf10ca760d5e`（rejects）。

## 2. 下载与固定 revision

| 来源 | dataset | revision | 许可 | 划分 | 原始行数 |
|---|---|---|---|---|---|
| P1 | tasksource/bigbench | `210c156767d2f4f05d2f4fd0bb275017a67040fd` | apache-2.0 | train | 187,305 |
| P2 | allenai/cosmos_qa | `28d9d5e2aae025e73e11177891a88dba51190013` | cc-by-4.0 | train | 25,262 |

两点与 CONTRACT §6.1 直接相关，必须写清：

1. **bigbench 走 `resolve/<sha>/<path>` 下载 parquet**，revision 是 URL 的一部分，**逐字节可复现**，不是 datasets-server 的
   "不遵守 revision"链路。32 个 config 各一个 `train-00000-of-00001.parquet`（实测无多分片）。
2. **cosmos_qa 的 HF 仓库里没有数据文件**（只有 `cosmos_qa.py`），该 loader 在固定 sha 下指向
   `https://github.com/wilburOne/cosmosqa/raw/master/data/`。因此记**两个 revision**：
   HF 侧 `28d9d5e2aae025e73e11177891a88dba51190013`（loader 出处，写进 `source.revision`）、
   GitHub 文件级 commit `8d4d7b40d0a027c6f6095f990c3809e9396a8e6f`（实际数据字节，写进
   `meta.native_source_file` 与 fetch-manifest）。只固定前者而放开后者等于没固定数据。

**划分收口**：两个来源都**只取 train**（sources.json policy："只取 train；validation/calibration 用于选模型与校准，
test/ood/leaderboard 一律不参与训练"）。bigbench 本身没有 test 划分；cosmos_qa 的 validation 2,985 / test 6,963 未取。
因此本候选语料 152,580 条**全部是 train**，`source.split` 一律 `"train"`。

下载总量：33 个文件、41,067,931 B（其中 bigbench parquet 24,407,482 B、cosmos train.csv 16,660,449 B，
与选型报告实测的 16,660,449 B 一致）。

## 3. 转换口径

### 3.1 字段映射

条目形状**完全复用** [convert.py](convert.py) 的 `--native` 路径
（`build_native_item` / `native_question` / `item_id` / `option_key` / `native_item_errors`），
所以产物与 `items.native.jsonl` 同形，合并时不需要第二套 schema。

| 契约字段 | bigbench | cosmos_qa |
|---|---|---|
| id | `db-bigbench-<8hex>` | `db-cosmos-qa-<8hex>` |
| domain | `knowledge_reasoning` | `knowledge_reasoning` |
| lang | `en`（保留源语言） | `en` |
| state | 原生 `inputs` 原文 | 原生 `context` 原文 |
| questions[0].key | **config 名（BIG-bench 原生任务名）** | **`question`（原生字段名）** |
| questions[0].kind | `choice` | `choice` |
| questions[0].origin | `source` | `source` |
| questions[0].source_key | = key | = key |
| questions[0].prompt | 原生 `inputs` 原文 | 原生 `question` 原文 |
| questions[0].options | `multiple_choice_targets`（去空、去重、确定性打散后） | `answer0..3`（去重、打散后） |
| targets[key].answer | 正确选项的 option key（**硬标签**） | 同左 |
| targets[key].probs | **不写** | **不写** |
| source.row | 抽取产物里的**物理行号**（原生 `idx` 不唯一，见 §8.3） | CSV 数据行号（不含表头） |
| source.{dataset,revision,config,split,license,url} | 见 §2 | 见 §2 |
| meta.capability | 数学与形式逻辑 / 阅读理解（§3.3 逐 config） | `reading_evidence` |

`key` 的口径说明：契约 §2.1 要求 `origin=source` 的 key 用**来源的原生问题名**。bigbench 的原生问题名就是
**任务名（=config）**，cosmos_qa 的题目存在原生字段 `question` 里——两处都用 `key_source="native-name"`，
`prompt` 放原生题面原文，没有任何改写、翻译或档位压缩。

**state 与 prompt 的关系**：bigbench 的 `inputs` 本身就是完整题面，没有独立的情境字段，
所以 `state == prompt`（`meta.state_equals_prompt=true`）；cosmos_qa 有独立的 `context`（state）与 `question`（prompt）。
这是本批条目体积偏大（152,580 条 379 MB，约 2.5 KB/条）的原因之一。

### 3.2 答案形态：只写硬标签，不写概率

`targets[<key>] = {"answer": "<option key>"}`，**全批 152,580 条都是 answer_only，没有一条带 probs**
（自检：`target_shape_bad = 0`）。

这一点与 convert.py 既有 native 路径**故意不同**：那条路径对硬标签调 `point_mass()` 造"选中 1.0、其余 0.0"的
单点分布（旗标 `hard_label_to_point_mass`），正是 CONTRACT §2.3 点名与 §1.3 冲突的**伪 one-hot**（历史产物 14,119 个问题）。
本候选语料不制造新的伪 one-hot；合并后若确有分布类损失需要概率，应当走契约建议的
`targets[key].provenance` 方案，而不是回到单点分布。

### 3.3 能力维度归属（按选型报告 P1/P2 分组）

| 能力维度 | 条目 | bigbench config |
|---|---:|---|
| 数学与形式逻辑 | 78,717 | formal_fallacies_syllogisms_negation / logical_fallacy_detection / analytic_entailment / epistemic_reasoning / logical_deduction / logic_grid_puzzle / evaluating_information_essentiality / symbol_interpretation / mathematical_induction / known_unknowns / arithmetic / elementary_math_qa / unit_conversion / cs_algorithms / intersect_geometry / checkmate_in_one / temporal_sequences / date_understanding / tracking_shuffled_objects / navigate（20 个） |
| 阅读理解与证据整合 | 73,863 | question_selection / disambiguation_qa / presuppositions_as_nli / entailed_polarity / winowhy / sentence_ambiguity / implicit_relations / crash_blossom / snarks / understanding_fables / riddle_sense / vitaminc_fact_verification（12 个）+ cosmos_qa 全部 25,262 |

白名单 = 选型报告 §2 P1-1 表里标为"原生带选项 + 不需要生成（L0）"的 **P1+P2 共 32 个 config**。
P3（general_knowledge / periodic_elements / physics / physical_intuition / anachronisms / misconceptions /
human_organs_senses / movie_recommendation / sports_understanding）与 P5（moral_permissibility /
simple_ethical_questions）**本轮按范围未取**，不是质量不达标——它们按选型报告的实测规模合计约 2,700 条 train，
若要扩面可以直接加进 `BIGBENCH_CONFIGS` 再跑一次，成本很低。

## 4. 质量门槛与剔除

门槛全部落成 convert 阶段的断言，不达标即剔除并逐条计数（台账见 rejects.capability.jsonl）。

| 门槛 | 实现 | bigbench | cosmos_qa |
|---|---|---:|---:|
| state/prompt 为空 | `state.strip()` / `prompt.strip()` 判空 | 0 | 0 |
| 选项为空 | `multiple_choice_targets` 为空 / 4 个候选全空 | **7,151** | 0 |
| 选项数 2–16 | 去重后再判 | **52,836** | 0 |
| 答案在选项内 | 折叠空白的规范化文本比对 | 0 | 0 |
| 答案唯一 | 去重后仍被源标为正确的**不同**文本只能有 1 个 | 0 | 0 |
| 单类别（无负类）config | 整份 config 的答案文本只有 1 个取值则整份剔除 | 0 | 0 |
| 只取 train | 抓取阶段 | — | — |
| **合计剔除** | | **59,987** | **0** |

**最大的单项损失是选项数上限**：`intersect_geometry`（50,000 条，41 个选项）整份被剔、`checkmate_in_one`
剔 2,768/2,799（13–52 个选项）、`implicit_relations` 整份 68 条被剔。这不是数据质量问题，而是**接入口径与契约不一致**，
详见 §8.1。

`unit_conversion` 的 7,151 条（占该 config 的 37.3%）在源里 `multiple_choice_targets` 就是空表——
来源自己没给选项，我们没有生成干扰项（本轮不引入任何生成选项），因此只能剔除，详见 §8.6。

### 4.1 逐 config 明细

| config | 能力 | 转出 | 剔除 | 剔除理由 | 答案类别数 | 原生答案位置 top2 |
|---|---|---:|---:|---|---:|---|
| formal_fallacies_syllogisms_negation | math_logic | 11,360 | 0 | — | 2 | pos0=5707, pos1=5653 |
| logical_fallacy_detection | math_logic | 2,240 | 0 | — | 2 | pos1=1182, pos0=1058 |
| analytic_entailment | math_logic | 54 | 0 | — | 2 | pos1=32, pos0=22 |
| epistemic_reasoning | math_logic | 1,600 | 0 | — | 2 | pos1=1006, pos0=594 |
| logical_deduction | math_logic | 1,200 | 0 | — | 323 | pos1=240, pos2=238 |
| logic_grid_puzzle | math_logic | 800 | 0 | — | 5 | pos1=258, pos0=244 |
| evaluating_information_essentiality | math_logic | 52 | 0 | — | 6 | pos3=14, pos4=11 |
| symbol_interpretation | math_logic | 795 | 0 | — | 441 | pos4=185, pos1=175 |
| mathematical_induction | math_logic | 53 | 0 | — | 2 | pos0=28, pos1=25 |
| known_unknowns | math_logic | 30 | 0 | — | 16 | pos1=15, pos0=15 |
| arithmetic | math_logic | 12,019 | 0 | — | 7,616 | **pos6=11110**, pos5=795 |
| elementary_math_qa | math_logic | 30,531 | 0 | — | 2,304 | pos2=6711, pos1=6461 |
| unit_conversion | math_logic | 12,000 | 7,151 | empty_options=7151 | 10,931 | pos2=2723, pos0=2698 |
| cs_algorithms | math_logic | 1,056 | 0 | — | 12 | pos1=478, pos0=370 |
| intersect_geometry | math_logic | **0** | **50,000** | options_gt16=50000 | 0 | — |
| checkmate_in_one | math_logic | 31 | 2,768 | options_gt16=2768 | 26 | pos0=7, pos9=4 |
| temporal_sequences | math_logic | 800 | 0 | — | 111 | **pos0=800** |
| date_understanding | math_logic | 296 | 0 | — | 267 | pos0=291, pos1=3 |
| tracking_shuffled_objects | math_logic | 3,000 | 0 | — | 47 | pos0=607, pos2=603 |
| navigate | math_logic | 800 | 0 | — | 2 | pos0=404, pos1=396 |
| question_selection | reading_evidence | 1,266 | 0 | — | 1,263 | **pos0=1266** |
| disambiguation_qa | reading_evidence | 207 | 0 | — | 61 | pos1=79, pos2=65 |
| presuppositions_as_nli | reading_evidence | 588 | 0 | — | 3 | pos1=250, pos0=232 |
| entailed_polarity | reading_evidence | 119 | 0 | — | 2 | pos1=117, pos0=2 |
| winowhy | reading_evidence | 2,290 | 0 | — | 2 | pos1=1279, pos0=1011 |
| sentence_ambiguity | reading_evidence | 44 | 0 | — | 2 | pos1=23, pos0=21 |
| implicit_relations | reading_evidence | **0** | **68** | options_gt16=68 | 0 | — |
| crash_blossom | reading_evidence | 22 | 0 | — | 3 | pos2=12, pos0=7 |
| snarks | reading_evidence | 145 | 0 | — | 2 | pos1=77, pos0=68 |
| understanding_fables | reading_evidence | 152 | 0 | — | 150 | pos2=38, pos4=37 |
| riddle_sense | reading_evidence | 33 | 0 | — | 31 | pos3=10, pos0=8 |
| vitaminc_fact_verification | reading_evidence | 43,735 | 0 | — | 3 | pos0=21854, pos1=16083 |
| **allenai/cosmos_qa（default）** | reading_evidence | **25,262** | **0** | — | 23,084 | pos0=6344, pos1=6319（原 label 分布，无偏斜） |

**没有出现单类别 config**：二分类 config 的单一答案占比最高 50.3%（formal_fallacies 5707/11360），
其余二分类都在 50% 上下，说明每个 config 都同时带正负类。唯一的例外性观察是
`known_unknowns`（30 条，其中 15 条答案是 `Unknown`）——它是 BIG-bench 的"不可判定"任务，两类都在，未剔除。

## 5. 质量取证

### 5.1 答案位置偏置：来源严重偏斜，打散后归零

按选项数分层做卡方（每格期望 ≥ 5 才参与；152,515 条参与，65 条落在小层里单列）：

| 口径 | chi2 | df | 最大单格占比 | 结论 |
|---|---:|---:|---:|---|
| 打散前（原生位置） | **67,385.79** | 37 | **0.865** | 极强位置偏置：`arithmetic` 11,110/12,019 全部落在第 7 个位置 |
| 打散后 | **36.53** | 37 | 0.500（小层） | 与 df 基本相等（p ≈ 0.49），**无偏置证据** |
| cosmos_qa 原生 | 0.43 | 3 | 0.251 | 来源本身均衡（与选型报告 valid 划分实测一致） |
| cosmos_qa 打散后 | 7.12 | 3 | — | 均匀 |

来源侧的极端偏斜（这是必须打散的直接证据）：`temporal_sequences` 800/800 在位置 0、
`question_selection` 1,266/1,266 在位置 0、`arithmetic` 11,110/12,019 在位置 6（最后一个）、
`date_understanding` 291/296 在位置 0、`entailed_polarity` 117/119 在位置 1。
若直接入库，模型学到的是"位置"而不是能力。

**打散是确定性的、可复原的**：种子 = `int(item id 末 8 位 hex, 16)`；`meta.native_option_order` 给出
"打散后第 i 位对应的原下标"，`meta.native_answer_index` / `meta.answer_index` 给出打散前后的答案位置。
自检：152,580 条全部满足 `options[order.index(native_answer_index)].label == native_answer_text`，
`order.index(native_answer_index) == answer_index`，**0 条不一致**。

### 5.2 其它形状分布

| 维度 | 分布 |
|---|---|
| 选项数（契约口径） | 2: 20,476｜3: 48,267｜4: 26,784｜5: 42,225｜6: 1,242｜7: 13,172｜8: 63｜9: 41｜10: 286｜11–16: 24 |
| target 形态 | answer_only 152,580（**无 probs、无伪 one-hot、无均匀分布**） |
| 语言 | en 152,580（100%） |
| state 长度 | ≤512: 116,683｜≤1024: 34,263｜≤2048: 1,462｜≤4096: 172（最长 < 4096，**未做任何截断**） |
| quality_flags | `duplicate_option_merged`: 10｜`id_collision_resolved`: 3 |

`duplicate_option_merged` 只有 10 条：选型报告点名的 `geometric_shapes`、`reasoning_about_colored_objects`
**不在本批 P1/P2 白名单里**，所以那两处已知的标签重复没有进入候选语料。这 10 条是白名单内的重复选项，
去重后答案文本仍唯一（若两个**不同**文本同时被判为正确，走的是 `answer_not_unique` 剔除，本批 0 条）。

### 5.3 结论：可复现、可复原、可校验

- **确定性**：同一 `--created-at` 连跑两次，items 与 rejects 的 sha256 **逐字节相同**。
- **可复原**：打散顺序、原生答案位置、原生行号（`meta.native_idx`）、原生选项数（`native_option_count_before_dedupe`）都在 meta 里。
- **保真**：bigbench 里用 "choice: X" 行内联选项的 16,154 条，其内联选项多重集与我们的 `options` **完全一致（0 条不一致）**；
  另外注意内联顺序与 `multiple_choice_targets` 的顺序**在来源里就不一致**（如 arithmetic 首行题面顺序 [1,5,house,6,banana,612]、
  选项数组顺序 [1,5,612,banana,house,6]），答案按**文本**对齐而不是按位置对齐，这一点在合并后的训练里也应保持。

## 6. 合约校验

**（1）native_item_errors（与 items.native.jsonl 同一把校验器）**

    items: 152,580   items_with_issues: 0   issue_counts: {}   duplicate_ids: 0   schema_issues: 0

**（2）coverage.py（外部检查，完整输出见 _meta\coverage-candidate.txt）**

    uv run --no-project --offline python datasets/general/coverage.py --items D:\pol2-raw\capability-raw\items.capability.jsonl
    items: 152580  问题数: 152580（source 152580 / taxonomy 0）
    [domain] knowledge_reasoning 152580 100.00%
    [出题方 origin] 缺失或非法 origin 0 道；source 152580 100.00%
    [原语 kind] choice 152580 100.00%
    [lang] en 152580 100.00%
    [source.dataset] tasksource/bigbench 127318 83.44% / allenai/cosmos_qa 25262 16.56%
    [问题键 source 原生] 共 31 个（30 个 bigbench config + cosmos_qa 的 question）
    [通过] 无硬性违规（非空 / domain 合法 / id 唯一）
    [schema 警告] 无                                    # 退出码 0

**（3）仓库验收**：`uv run --no-project --offline python tools/check.py` → 退出码 **0**；
`git status` 只有本文件与 convert_capability.py 两个新增，未触碰任何现有数据/文档。

## 7. 合并后构成预期（核心）

现有语料的能力维度**用 README 自己的规则链重算**（`readme_stats.classify_capability`，逐条跑公开三个分区），
新条目的维度取 `meta.capability`（因为 readme_stats 目前不认识这两个来源，见 §8.5）。

### 7.1 全量合并（公开三分区口径，与 README §2.2 同口径）

| 能力维度 | 合并前 | 占比 | 合并后 | 占比 |
|---|---:|---:|---:|---:|
| 工具与行动选择 | 15,294 | 60.20% | 15,294 | **8.59%** |
| 社会与人类判断 | 4,347 | 17.11% | 4,347 | 2.44% |
| 阅读理解与证据整合 | 1,946 | 7.66% | 75,809 | 42.59% |
| 数学与形式逻辑 | 1,737 | 6.84% | 80,454 | 45.20% |
| 世界知识及其应用 | 1,491 | 5.87% | 1,491 | 0.84% |
| 因果、反事实与不确定性判断 | 590 | 2.32% | 590 | 0.33% |
| **合计** | **25,405** | 100% | **177,985** | 100% |

### 7.2 训练口径（只算 train 分区：现有 17,986 + 新 152,580）

| 能力维度 | 合并前 | 占比 | 合并后 | 占比 |
|---|---:|---:|---:|---:|
| 工具与行动选择 | 10,189 | 56.65% | 10,189 | **5.97%** |
| 社会与人类判断 | 3,940 | 21.91% | 3,940 | 2.31% |
| 阅读理解与证据整合 | 1,294 | 7.19% | 75,157 | 44.06% |
| 数学与形式逻辑 | 1,166 | 6.48% | 79,883 | 46.83% |
| 世界知识及其应用 | 1,003 | 5.58% | 1,003 | 0.59% |
| 因果、反事实与不确定性判断 | 394 | 2.19% | 394 | 0.23% |
| **合计** | **17,986** | 100% | **170,566** | 100% |

### 7.3 情景表：真正要裁决的是"接多少"

全量合并之所以把 60.20% 压到 8.59%，唯一原因是**新语料体量**（152,580 ≈ 现有 25,405 的 6.0 倍），
不是"两个来源特别强"。按整体缩放新语料（口径同上，公开三分区）：

| 情景 | 新语料 | 合并总量 | 工具与行动选择 | 数学与形式逻辑 | 阅读理解与证据整合 |
|---|---:|---:|---:|---:|---:|
| full_both（本候选全量） | 152,580 | 177,985 | **8.59%** | 45.20% | 42.59% |
| bigbench_only | 127,318 | 152,723 | 10.01% | 52.68% | 33.10% |
| cosmos_only | 25,262 | 50,667 | 30.19% | 3.43% | 53.70% |
| both_half（1/2） | 76,290 | 101,695 | 15.04% | 40.41% | 38.23% |
| both_third（1/3） | 50,860 | 76,265 | 20.05% | 36.68% | 34.84% |
| both_sixth（1/6） | 25,430 | 50,835 | **30.09%** | 29.23% | 28.04% |

**单一来源占比**（sources.json 参考上限 40%，当前不判定、只作参考）：全量合并后
tasksource/bigbench 占 **71.5%**（127,318/177,985）；要让 bigbench 回到 40% 以内，
新语料需缩到约 **1/6.5 以下**（≈ 23,500 条），届时工具与行动选择约 31%。

**读法**：如果目标是"把 60.20% 降到不再一家独大"，1/6 缩放（30.09% / 29.23% / 28.04%，前三维基本三分天下）
比全量合并（8.59% / 45.2% / 42.6%）更接近"通用底盘"；如果目标是"把数学与形式逻辑从 6.84% 补到与工具维相当"，
全量或 1/2 都可以。**这个取舍需要 Lead 定，本文件只给数字。** 缩放实现上只需在 convert 阶段按 config 分层下采样，
不必改口径（`--limit` 目前只用于冒烟，未实现分层采样）。

## 8. 契约不匹配与需要裁决的点

### 8.1 【最重要】选项数上限：口径与契约不一致，代价 52,836 条

- **契约**：CONTRACT §2.1 明确 `origin=source` 的 choice **≥2 且不设上限**（实测原生最多 57 个选项）；
  上限 16 只对 `origin=taxonomy` 成立。
- **本轮口径**：task 要求按 2–16 卡，我照做了——严格卡 16 之后剔掉 52,836 条，
  其中 `intersect_geometry` 50,000 条（41 选项）与 `checkmate_in_one` 2,768 条（13–52 选项）**整份丢失**。
- **两条路**：① 维持 16 上限（本候选现状，最保守）；② 按契约放宽到"≥2 不设上限"，可再多接约 **52.8k 条**
  （几何/棋类是纯形式推理，能力价值高，但选项空间大、猜测基线低，混进训练会改变 loss 的尺度）。
  **我没有替 Lead 决定**，脚本里 `MAX_OPTIONS` 一个常量即可切换，切换后需要重跑并重新出数。

### 8.2 伪 one-hot：本候选不造，但与既有 native 路径不一致

convert.py 的 native 路径对硬标签写 `point_mass()`（选中 1.0 / 其余 0.0），与 CONTRACT §1.3、§2.3 冲突。
本候选语料 152,580 条**全部只写 answer**。合并后如果既有语料仍保留伪 one-hot，同一份训练集里会同时存在
两种真值形态；建议合并时统一按 §2.3 的判别方法过滤，或加 `targets[key].provenance`。

### 8.3 `source.row` 不能用原生 `idx`

原生 `idx` **在多个 config 里不唯一**（实测 `unit_conversion` 19,151 行只有 2,400 个 idx、
`arithmetic` 12,019 行只有 800 个、`elementary_math_qa` 30,531 行只有 6,151 个、`intersect_geometry` 50,000 行 30,473 个）。
第一版用它当 row，直接导致 **11,166 个重复 id**（同时让打散种子重复、位置分布失真）。
现在 row = 抽取产物的物理行号，原生 idx 存在 `meta.native_idx`。**任何后续接入 tasksource 系数据集的人都该知道这一点。**

### 8.4 8 位 hex 的生日碰撞

id 是 `db-<slug>-<8hex>`（32 位）。152,580 条时实测撞了 **3 次**（期望 ≈ 2.7 次）。已按固定遍历顺序
挂 `v1/v2…` variant 解决（`meta.quality_flags` 记 `id_collision_resolved:v1`），重复 id = 0。
若后续语料继续扩大（>50 万条），建议契约层考虑把 hex 位宽提到 10–12 位，而不是继续靠 variant 兜。

### 8.5 `readme_stats.classify_capability` 必须先加规则

该函数按 `source.dataset` 分派，目前不认识 `tasksource/bigbench` 与 `allenai/cosmos_qa`，**会把这 152,580 条
全部归到 `other`**。本报告的合并预期是用 `meta.capability` 注入算的；真正合并前需要在
[readme_stats.py](readme_stats.py) 里加两条规则（建议 C9/C10：bigbench 按 `meta.native_task` 查 §3.3 的表，
cosmos_qa 整份 `reading_evidence`），否则 README 的分布审计会失真。该文件属 db-schema，不在本轮写范围。

### 8.6 来源侧的形状缺口（不是我们的门槛问题）

- `unit_conversion` 19,151 条 train 里 **7,151 条（37.3%）原生 `multiple_choice_targets` 为空**，只能剔除。
- `intersect_geometry`/`implicit_relations` 整份超选项上限（§8.1）。
- 选型报告点名的 `geometric_shapes`/`reasoning_about_colored_objects` 标签重复**不在本白名单内**，未进入候选。

### 8.7 其它需要知道的事实

- **语言 100% 英文**：本批对中国语料零贡献。选型报告 §4.5 的"中文世界知识无规模化可训练来源"这一空洞**没有被本批填补**。
- **state 与 prompt 重复**（bigbench 无独立情境字段），条目体积约 2.5 KB/条，全批 379 MB。若要压体积，
  可在合并时对 `state_equals_prompt=true` 的条目做字段级压缩，但那属于合并期决策。
- **能力维度是"来源标签经固定映射"**，不是独立人工标注（与 README §2.5 的自述限制一致）：
  `evaluating_information_essentiality`（数据充分性）、`known_unknowns`（不可判定）两处按选型报告归入
  数学与形式逻辑，若按 README 的"瓶颈能力"约定也可以归入因果/反事实与不确定性判断——这会影响 82 条的归属，
  数量很小但口径要一致。
- **许可**：apache-2.0 / cc-by-4.0，均无 NC/ND 限制；逐条 `source.license` 与 `source.url` 已写入。
  cosmos_qa 的许可依据是卡面原文"As reported via email by Yejin Choi, the dataset is licensed under CC BY 4.0"。

## 9. 复算命令

    # 0) 仓外 venv（只为读 parquet；仓库继续保持 stdlib-only）
    uv venv D:\pol2-raw\capability-raw\.venv
    uv pip install --python D:\pol2-raw\capability-raw\.venv\Scripts\python.exe pyarrow

    # 1) 下载 33 个原始文件（固定 revision；sha256 写入 _meta\fetch-manifest.json）
    uv run --no-project --offline python datasets/general/convert_capability.py fetch

    # 2) parquet -> rows.jsonl（187,305 行）
    D:\pol2-raw\capability-raw\.venv\Scripts\python.exe datasets/general/convert_capability.py extract

    # 3) 转换 + 报告（--created-at 固定后逐字节可复现）
    uv run --no-project --offline python datasets/general/convert_capability.py convert --created-at 2026-10-15T15:00:00+08:00

    # 4) 重读产物复核（schema + 位置偏置 + 合并预期）
    uv run --no-project --offline python datasets/general/convert_capability.py verify

    # 5) 契约校验（外部）
    uv run --no-project --offline python datasets/general/coverage.py --items D:\pol2-raw\capability-raw\items.capability.jsonl

    # 6) 仓库验收
    uv run --no-project --offline python tools/check.py

## 10. 本轮明确未做

- 未合并、未改四区划分、未改 items.final、未跑 split.py、未改任何现有文档与数据（`git status` 只有两个新增文件）。
- 未做语义近重复/同族检测（与 CONTRACT §6.5 一致），也未与现有 25,405 条做跨来源去重。
- 未做分层下采样（§7.3 的 six/half/third 情景只是按比例缩放算出来的预期，不是已经生成的文件）。
- 未取 validation/test 划分，未取 P3/P5 的 11 个 config（§3.3）。
- 未做训练实验：本文件只能说"补进了多少条什么能力的监督信号"，**不能**说明"训练后模型智力不退化"——
  那需要具体模型、训练配置与独立评测（与 README §2.5 的口径一致）。
