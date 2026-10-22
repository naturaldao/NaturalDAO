# 通用能力补源调研：数学与形式逻辑 / 阅读理解与证据整合 / 广泛世界知识

- 日期：2026-10-15（UTC+8）｜执行：db-capability（DSH Agent Team）｜共享任务：task-4
- 上游依据：评审对当前构成的判断（decision_mechanics 19,465 / 27,003 = 72%，`origin=source` 线几乎只有工具与决策类）、
  [CONTRACT.md](../CONTRACT.md)（三条原语：choice / noul / score）、[SOURCES.md](../SOURCES.md)（来源与许可登记）、
  [coverage-gaps.md](2026-10-06-coverage-gaps.md)（六域缺口）、[TRAINING.md](../TRAINING.md)（训练口径）
- 边界：**本文件只做调研与取证**，不动数据、不动划分、不改其它文档、不写 git。
- 本轮准入口径（2026-10-15 Lead 转述用户放宽后）：**有问题 + 有答案（简练、可判定）即可**，
  不再要求原生带选项；答案可作为其中一个选项，**其余选项可由模型/规则生成**。
  仍然排除：需要**人工重标**的、只有单一类别（无负类）的、答案自由文本或开放式到无法枚举选项的。

## 0. 取证方法与证据等级

| 等级 | 含义 |
|---|---|
| **A** | 读过卡面 + **实际拉过行数据/下载过原始文件**（行数、字段、取值、标签分布为实测） |
| **B** | 读过卡面 + datasets-server 的 size / info / rows 快照（未下载原始文件） |
| **C** | 只有 HF API 元数据（sha / license / downloads），行结构**未实测** |

本轮实际用到的接口（可复算，见 §8）：`huggingface.co/api/datasets/{id}`（sha / license / gated）、
`datasets-server.huggingface.co/info|size|rows`（划分规模、前 20–100 行）、
`huggingface.co/datasets/{id}/raw/{sha}/README.md`（卡面许可原文）、`api.github.com/repos/{owner}/{repo}`（上游许可）。
**行数一律指"源行数"（源数据一行 = 我们的一个条目），取自 datasets-server 的 num_examples**，不是转换后条数。

**已知口径限制**：CONTRACT §6.1 已记录 datasets-server 不遵守 revision 参数，所以本文的行级实测是
**抓取时 HEAD** 的内容；fixed revision 是 2026-10-15 通过 HF API 解析出的 sha（可点开核对）。
真正逐字节复现需走 `resolve/<sha>/<path>` 下载文件。

## 1. 结论速览

| 优先级 | 候选（按"接入成本 / 能力价值"排序） | train 可用行数 | 语言 | 原生选项 | 选项生成 | 许可 | 证据 |
|---|---|---:|---|---|---|---|---|
| P1 数学与形式逻辑 | **tasksource/bigbench** | 191,961（本表列出的 45 个 config 合计） | en（少数多语任务） | ✓ | 不需要 | apache-2.0 | A |
| P1 | **deepmind/aqua_rat** | 97,467 | en | ✓（5 选 1） | 不需要 | apache-2.0 | A |
| P1 | **allenai/math_qa** | 29,837 | en | ✓（5 选 1） | 不需要 | apache-2.0 | A |
| P1 | **tasksource/proofwriter**（+ ruletaker） | 585,552（+480,152） | en | 3 值标签 | 不需要 | 未查到（ruletaker: apache-2.0） | A |
| P2 阅读理解与证据整合 | **allenai/cosmos_qa** | 25,262 | en | ✓（4 选 1） | 不需要 | cc-by-4.0 | A |
| P2 | **aps/super_glue（multirc）** | 27,243 | en | 逐候选 yes/no | 不需要 | other（未明确） | A |
| P2 | **rajpurkar/squad_v2** | 130,319（33.8% 不可回答） | en | noul（固定 yes/no） | 不需要 | cc-by-sa-4.0 | A |
| P2 | **clue/clue（c3）** | 11,869 | zh | ✓（3–4 选 1） | 不需要 | 未查到 | A |
| P3 广泛世界知识 | **cais/mmlu** | 99,842（auxiliary_train；本体 test 不进梯度） | en | ✓（4 选 1） | 不需要 | mit | A |
| P3 | **mandarjoshi/trivia_qa** | 138,384 | en | ✗ | 需生成（实体名） | 卡面 unknown / 上游 apache-2.0 | A |
| P3 | **google-research-datasets/nq_open** | 87,925 | en | ✗ | 需生成（实体名） | cc-by-sa-3.0 | A |
| P3 | 原生选项知识小集（commonsense_qa / qasc / openbookqa / ai2_arc / sciq） | 9,741 / 8,134 / 4,957 / 3,370 / 11,679 | en | ✓ | 不需要 | mit / cc-by-4.0 / 卡面 unknown / cc-by-sa-4.0 / cc-by-nc-3.0 | A |

**一句话**：三条线里 P1、P2 都能找到**零生成成本**的干净来源（BIG-bench 的原生选项、Cosmos QA、MultiRC、SQuAD2.0 的不可回答子集、CLUE 的 c3）；
**P3 是唯一必须依赖"生成干扰项"的线**（MMLU 本体按本仓数据边界不能进梯度，只留下混合来源的 auxiliary_train）。
**没有找到任何天然 `score`（分级）形态的通用能力来源**——这条原语在这三个维度上没有现成供给，属负面结果。

## 2. 优先级 1：数学与形式逻辑

### P1-1 tasksource/bigbench —— 形式逻辑 / 算术 / 约束满足（首选）

- 链接（fixed revision）：https://huggingface.co/datasets/tasksource/bigbench/tree/210c156767d2f4f05d2f4fd0bb275017a67040fd
- revision：`210c156767d2f4f05d2f4fd0bb275017a67040fd`｜许可：**apache-2.0**（HF 卡面 `license: apache-2.0`；上游 BIG-bench 同为 Apache-2.0）
- 规模：167 个 config，**train 640,167 / validation 201,172**（/info 实测）；本文挑出**原生带选项的 45 个 config = 191,961 条 train**
- 语言：en 为主（另有 cryobiology_spanish / medical_questions_russian 等少数多语任务，本文未采用）
- 是否原生 (question, options, target)：**是**（对带多选的 config）。字段 `inputs`（题面，含问题原文）+
  `multiple_choice_targets`（选项列表）+ `multiple_choice_scores`（唯一 1.0 的独热）+ `targets`（正确项文本）
- 答案是否封闭且简练：**是**。实测 12 个 config 各抽 60 行：`targets[0] ∈ multiple_choice_targets` **60/60**、
  `multiple_choice_scores` 恰一个 1.0 **60/60**（唯二例外见下）
- 负类：每个多选题目自带 1–40 个错误选项，非单一类别
- **选项可否自动生成：不需要生成（L0 原生选项）**——干扰项由 BIG-bench 原始构造给出，同类型同粒度，
  这正是"干扰项质量"最省心的一档
- 能力维度：P1（形式逻辑、约束满足、算术、几何、状态跟踪、时序）

推荐子集（实测 train 行数 / 选项数来自 60 行抽样）：

| config | train | 选项数 | 维度 | 备注 |
|---|---:|---:|---|---|
| formal_fallacies_syllogisms_negation | 11,360 | 2 | 论证有效性 | valid / invalid，两类均出现 |
| logical_fallacy_detection | 2,240 | 2 | 逻辑谬误 | valid / invalid |
| analytic_entailment / epistemic_reasoning | 54 / 1,600 | 2 | 形式蕴含 | entailment / non-entailment |
| logical_deduction | 1,200 | 5 | 约束满足（排序） | |
| logic_grid_puzzle | 800 | 2–5 | 约束满足（网格） | |
| evaluating_information_essentiality | 52 | 5 | **数据充分性** | "哪条信息足以作答"，天然对应证据不足类 |
| symbol_interpretation | 795 | 5 | 形式化语义一致性 | |
| mathematical_induction | 53 | 2 | 数学归纳 | |
| known_unknowns | 30 | 2 | **不可判定**（选项含 Unknown） | 规模极小 |
| arithmetic | 12,019 | 5–7 | 多步算术 | |
| elementary_math_qa | 30,531 | 5–6 | 数学应用题 | |
| unit_conversion | 19,151 | 5 | 单位换算 | |
| cs_algorithms | 1,056 | 10 | 算法/计数 | |
| intersect_geometry | 50,000 | 41 | 几何 | 规模最大 |
| checkmate_in_one | 2,799 | 13–52 | 棋类搜索 | 选项空间大 |
| temporal_sequences / date_understanding / tracking_shuffled_objects / navigate | 800 / 296 / 3,000 / 800 | 4 / 6 / 5 / 2 | 时序、状态跟踪、空间 | |
| question_selection / disambiguation_qa / presuppositions_as_nli / entailed_polarity / winowhy / sentence_ambiguity / implicit_relations / crash_blossom / snarks / understanding_fables / riddle_sense | 1,266 / 207 / 588 / 119 / 2,290 / 44 / 68 / 22 / 145 / 152 / 33 | 2–25 | P2 阅读与证据 | 见 §3.3 |
| vitaminc_fact_verification | 43,735 | 3 | P2/P3 证据核验 | True / False / **Neither**（含"信息不足"负类） |
| general_knowledge / periodic_elements / physics / physical_intuition / anachronisms / misconceptions / human_organs_senses / movie_recommendation / sports_understanding | 54 / 524 / 184 / 65 / 184 / 176 / 26 / 400 / 789 | 2–118 | P3 世界知识 | 见 §4.4 |
| moral_permissibility / simple_ethical_questions | 274 / 92 | 2 / 4 | P5 社会判断 | 优先级最低 |

- 已知限制：
  1. **不是所有 config 都能用**：`modified_arithmetic`、`object_counting`、`simple_arithmetic_json`、`qa_wikidata` 实测
     `multiple_choice_targets` 为空（自由数值/文本答案），需另生成选项；`list_functions`、`repeat_copy_logic`、
     `operators`、`dyck_languages`、`word_sorting` 答案是自由文本 → **不适合**生成选项。
  2. **标签重复**：`geometric_shapes` 恰一个 1.0 只有 **47/60**、`reasoning_about_colored_objects` **39/60**（选项里有等价表述）→
     入库前要按文本去重，否则"唯一正确项"不成立。
  3. `strategyqa` 虽有 2 个选项，但 `targets[0] ∉ multiple_choice_targets`（实测 0/60）→ 必须按 target 文本重建选项。
  4. 单个 config 普遍偏小（22–800 行的有十几个），**能力价值密度高但规模靠多 config 拼**。
  5. 训练集/验证集是 BIG-bench 官方划分；**无 test 划分**，所以不存在"公开测试集进梯度"的边界问题。

### P1-2 deepmind/aqua_rat —— 多步数学应用题（原生 5 选 1）

- 链接：https://huggingface.co/datasets/deepmind/aqua_rat/tree/33301c6a050c96af81f63cad5562cb5363e88971
- revision：`33301c6a050c96af81f63cad5562cb5363e88971`｜许可：**apache-2.0**（卡面原文 "Licensed under the Apache License, Version 2.0"）
- 规模：`raw` 配置 **train 97,467 / validation 254 / test 254**（另一 config `tokenized` 是同一批数据的另一种编码，勿重复计入）
- 语言：en｜字段：`question`、`options`（列表，5 项，形如 `"A)21"`…）、`rationale`、`correct`（字母）
- 是否原生 (question, options, target)：**是**，且自带 rationale（可做 CoT 辅助信号）
- 答案是否封闭且简练：**是**（A–E 字母 + 数字选项）
- 负类：每题 4 个错误选项。实测 300 行正确答案位置分布 A/B/C/D/E = 72/72/65/55/36，**位置无明显偏斜**，无重复选项（0/300）
- **选项可否自动生成：不需要生成（L0）**；干扰项由原作者用错误解法生成，同粒度
- 能力维度：P1（代数/行程/百分比类多步计算）
- 已知限制：
  1. 单一子技能（算术应用题），且选项文本格式不统一（`A)21` 与 `A) 21` 混用）→ 需规范化；
  2. rationale 是自动生成/众包的，个别与答案不一致（已知争议），**不要把 rationale 当作真值监督**；
  3. test 只有 254 条 → 只能做小回归。

### P1-3 allenai/math_qa —— 多步数学（原生 5 选 1 + 公式标注）

- 链接：https://huggingface.co/datasets/allenai/math_qa/tree/c4f1cc784c04c4957b50c97858f23893b633eea6
- revision：`c4f1cc784c04c4957b50c97858f23893b633eea6`｜许可：**apache-2.0**（卡面原文 "The dataset is licensed under the Apache License, Version 2.0"）
- 规模：**train 29,837 / validation 4,475 / test 2,985**（HF dataset_info 实测；另有 challenge_test.json 未在 HF 上）
- 语言：en｜字段：`Problem`、`Rationale`、`options`（"a ) 38 , b ) 27.675 , …"）、`correct`、`annotated_formula`、`linear_formula`、`category`
- 是否原生 (question, options, target)：**是**（选项与答案字母都在源里）
- 答案是否封闭且简练：**是**。实测 29,837 条 train：正确答案位置 a/b/c/d/e = 6,010 / 6,308 / 6,653 / 6,085 / 4,781（**无位置偏斜**）
- 负类：每题 4 个错误选项｜**选项可否自动生成：不需要生成（L0）**
- 能力维度：P1（多步数学；实测类别分布 general 13,273 / physics 7,063 / gain 5,120 / geometry 2,117 / other 1,814 / probability 450）
- 已知限制：
  1. **HF 仓库里没有数据文件**（只有 `math_qa.py` + README），datasets-server 返回 501；
     真实数据在仓外 `https://math-qa.github.io/math-QA/data/MathQA.zip`（7,302,821 B，本文已实际下载并逐行统计）；
  2. **4.9% 的行（1,471/29,837）选项里含 "none of these" / "data inadequate"** → 这类"兜底项"会让"选一个"退化成排除法，建议过滤或标注；
  3. 选项文本用逗号+千分位分隔，朴素切分会把 483 行误判成 10 个选项 → 解析要按 `a ) … , b ) …` 模式，不能按逗号 split。

### P1-4 tasksource/proofwriter（+ tasksource/ruletaker）—— 条件推理与"不可判定"

- 链接：https://huggingface.co/datasets/tasksource/proofwriter/tree/ee4d22d49b8486786cbc01c0b6f6f6266e56f3bd ；
  https://huggingface.co/datasets/tasksource/ruletaker/tree/a3e0880baeb6ec3d478f4c4d85afe04b21b6cf7f
- revision：proofwriter `ee4d22d49b8486786cbc01c0b6f6f6266e56f3bd`｜ruletaker `a3e0880baeb6ec3d478f4c4d85afe04b21b6cf7f`
- 许可：proofwriter **未查到**（HF 卡面无许可字段；allenai/ProofWriter 仓库 404）；ruletaker **apache-2.0**（卡面）
- 规模：proofwriter **train 585,552 / validation 85,468 / test 174,476**；ruletaker **train 480,152 / dev 75,872 / test 151,911**（/info 实测）
- 语言：en｜proofwriter 字段：`theory`（前提集合）、`question`（假设）、`answer ∈ {True, False, Unknown}`、
  `maxD`/`NFact`/`NRule`/`QDep`（深度与规模）；ruletaker 字段：`context`、`question`、`label ∈ {entailment, not entailment}`
- 是否原生 (question, options, target)：**问题与答案原生，选项隐含**（3 值/2 值闭合标签集）→ 转 `choice`（3 项）或 `noul`（2 项），
  **不需要任何人工重标**
- 答案是否封闭且简练：**是**（单个词）｜负类：**有**，且带第三类"Unknown"（实测 20 行 True/False/Unknown = 7/7/6）
- **选项可否自动生成：不需要生成（选项就是源标签集本身，L0/L1）**
- 能力维度：P1（条件推理、规则演绎）+ 兼补"证据不足/不可判定"（优先级 4）
- 已知限制：
  1. **合成数据**，模板化、词汇封闭（人名+属性），与真实文本分布差距大 → 适合作为"形式推理基本功"，不能代表阅读理解；
  2. 规模巨大但**高度同质**（同一模板的 D0–D5 深度变体），直接全量入库会淹没其它来源 → 建议按 depth/config 分层下采样；
  3. proofwriter 许可未查到（上游 Allen AI 页面存在，GitHub 仓库 404）→ 需标注风险；
  4. 答案为三分类，若走 `choice` 需固定选项顺序，避免位置偏置。

### P1 次级候选（同样可接，成本或价值次一档）

| 候选 | revision / 许可 | train 行数 | 语言 | 原生选项 | 选项生成 | 维度与限制 |
|---|---|---|---|---|---|---|
| [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k/tree/740312add88f781978c0658806c59bc2815b9866) | `740312add88f781978c0658806c59bc2815b9866` / mit（卡面；上游 openai/grade-school-math 无 LICENSE 文件） | 7,473（test 1,319 为公开测试，仅回归） | en | ✗ | **L1 可确定性构造**：答案形如 `… #### 72`，取 `####` 后数值；干扰项用数值扰动（±1 位、错位小数点、常见中间结果），同粒度可控 | 小学多步算术。**限制**：需解析答案尾部；数值区间跨 0–10^5，干扰项要按数量级分层，否则一眼可排除 |
| [Azure99/math23k-reborn](https://huggingface.co/datasets/Azure99/math23k-reborn/tree/8476e15c99e329150c3c5c662eb2d150f7501f40) | `8476e15c99e329150c3c5c662eb2d150f7501f40` / **apache-2.0** | 22,329（仅 train） | **zh** | ✗ | **L1/L2**：`metadata.reference` 是数值/百分数（实测 20/180/32/39.76/10%），可规则扰动；也可由模型生成错误解法得干扰项 | **中文数学**的主要供给。限制：同一模板答案唯一、无负类需生成；上游 Math23K 的原始许可未查到，此镜像标 apache-2.0 |
| [lucasmccabe/logiqa](https://huggingface.co/datasets/lucasmccabe/logiqa/tree/3c19b0488d794d30c36f73d132d8a22e64f42f2e) | `3c19b0488d794d30c36f73d132d8a22e64f42f2e` / **未查到**（卡面无许可，GitHub 仓库 404） | 7,376 | en（中文原题的英译） | ✓（`context`/`query`/`options` 4 项/`correct_option` 整数下标） | 不需要 | 公务员考试逻辑题。**限制**：许可未查到；机翻痕迹；单一来源 |
| [hails/agieval-logiqa-zh](https://huggingface.co/datasets/hails/agieval-logiqa-zh/tree/e85baf7de058eba84623ebb2b6266cf77691df62) | `e85baf7de058eba84623ebb2b6266cf77691df62` / 卡面无许可（上游 AGIEval **MIT**） | 0（只有 test 651） | **zh** | ✓ | 不需要 | **中文逻辑原件**，但 **test-only → 只能做回归，不能进梯度**（本仓数据边界） |
| [tasksource/folio](https://huggingface.co/datasets/tasksource/folio/tree/295b95fb4fe9be4ff3f933b73142d142cf6b2c97) | `295b95fb4fe9be4ff3f933b73142d142cf6b2c97` / 卡面 `license: cc`（**具体版本未查到**；上游 Yale-LILY/FOLIO 为 CC-BY-SA-4.0，HF 原仓库 yale-nlp/FOLIO 卡面写 mit 且 `gated=auto`） | 1,001 | en | 3 值标签（True / False / Uncertain，实测 10/4/6） | 不需要 | 一阶逻辑前提+结论，价值高但**规模太小**、许可表述互相矛盾 |

## 3. 优先级 2：阅读理解与证据整合

### P2-1 allenai/cosmos_qa —— 原生 4 选 1 的英文阅读理解（首选）

- 链接：https://huggingface.co/datasets/allenai/cosmos_qa/tree/28d9d5e2aae025e73e11177891a88dba51190013
- revision：`28d9d5e2aae025e73e11177891a88dba51190013`｜许可：**cc-by-4.0**（卡面："As reported via email by Yejin Choi, the dataset is licensed under CC BY 4.0"）
- 规模：**train 25,262 / validation 2,985 / test 6,963**（HF dataset_info 实测；本文另下载 valid.csv 逐行核对，2,985 行）
- 语言：en｜字段（实测 valid.csv 表头）：`id, context, question, answer0, answer1, answer2, answer3, label`
- 是否原生 (question, options, target)：**是**——问题是原生自然语言，4 个候选是原生文本，label 是 0–3 下标
- 答案是否封闭且简练：**是**（选项是一句话，答案是指标）
- 负类：每题 3 个错误项；实测 valid 划分 label 分布 0/1/2/3 = 744 / 729 / 761 / 751（**均衡**）
- **选项可否自动生成：不需要生成（L0）**
- 能力维度：P2（多句情境下的因果/意图/指代与事件推理；题目设计本就是"机器阅读理解需要常识推断"）
- 已知限制：
  1. **HF 仓库无数据文件**（只有 `cosmos_qa.py`，datasets-server 501）；数据在
     `https://github.com/wilburOne/cosmosqa/raw/master/data/`（`valid.csv` 2,128,345 B 已实测下载；`train.csv` 16,660,449 B）；
  2. 相当一部分题目**本身就是常识推断**，标注者之间可能存在分歧（原论文自述部分题"无法唯一确定"）→ 入库时建议保留源标签，不做再标注；
  3. 英文；context 长度实测中位 ~50 词（短，不是长上下文）。

### P2-2 aps/super_glue（config multirc）—— 逐候选 yes/no，天然含负类

- 链接：https://huggingface.co/datasets/aps/super_glue/tree/3de24cf8022e94f4ee4b9d55a6f539891524d646
- revision：`3de24cf8022e94f4ee4b9d55a6f539891524d646`（`super_glue` 与 `aps/super_glue` 同 sha）
- 许可：卡面 **other**（"The primary SuperGLUE tasks are built on and derived from existing datasets. We refer users to the original licenses accompanying each dataset…"）；
  上游 MultiRC 仓库（CogComp/multirc）GitHub license = **NOASSERTION（未明确）** → **标注风险**
- 规模：**multirc train 27,243 / validation 4,848 / test 9,693**（/info 实测）｜语言：en
- 字段（实测）：`paragraph`、`question`、`answer`（候选句）、`idx`（paragraph/question/answer 三层下标）、`label`(0/1)
- 是否原生 (question, options, target)：**问题原生 + 候选原生 + 标签原生**；形态不是"多选一"，而是"**某个候选句是否正确**"
  → 直接映射 **`noul`**（选项固定 yes/no，零生成成本；题面措辞可由我们写："该候选是否为该问题的正确答案？"，属 `origin=taxonomy`）
- 答案是否封闭且简练：**是**（0/1）｜负类：**有**，实测 20 行 0/1 = 11/9
- **选项可否自动生成：不需要生成（yes/no 固定）**
- 能力维度：P2（多段材料 + 证据整合；MultiRC 的设计就是"一个问题需要多个证据句"）
- 已知限制：
  1. **一个问题可有多个正确候选**（多标签）→ 拆成"每个候选一条 noul"是正确用法，但同一 question 的多个正例会造成条目重复感，需按 (paragraph, question) 分组管理；
  2. 许可未明确（SuperGLUE 汇总页 + 上游 NOASSERTION）→ 需标注风险；
  3. test 无公开标签（官方评测），只能做 train/validation。

### P2-3 rajpurkar/squad_v2 —— 130k 条"能不能回答"的 noul 信号

- 链接：https://huggingface.co/datasets/rajpurkar/squad_v2/tree/3ffb306f725f7d2ce8394bc1873b24868140c412
- revision：`3ffb306f725f7d2ce8394bc1873b24868140c412`｜许可：**cc-by-sa-4.0**（卡面）
- 规模：**train 130,319 / validation 11,873**（test 未在 HF 上发布）
- 语言：en｜字段（实测）：`id, title, context, question, answers{text[], answer_start[]}`
- 是否原生 (question, options, target)：问题与材料原生，**答案原本是抽取式跨度**（非封闭选项）；
  但 `answers.text` 为空 ⇒ 不可回答，这是一个**由源字段确定性派生**的二值标签
- 答案是否封闭且简练：**转成 noul 后是**（yes/no）｜负类：**有**——实测 5 个窗口共 500 行，**不可回答 169/500 = 33.8%**
- **选项可否自动生成：noul 部分不需要生成（固定 yes/no，L0）**；
  若要利用"可回答"的那 66% 做 choice，则需从**同一段落**抽取同类型跨度作干扰项（L1，质量可控：同段落、同实体类型、长度相近）——
  这是本项目里**质量最高的一类自动干扰项**，因为干扰项天然"看着像答案"
- 能力维度：P2（证据定位）+ 兼补"证据不足/不可判定"（优先级 4）
- 已知限制：
  1. noul 的**问句措辞是我们写的**（`origin=taxonomy`，与契约 §2.1 的 B 层一致）——但标签**完全来自源**，无需人工重标；
  2. 若做 choice，必须保证干扰跨度**不出现在同段落的任何答案里**，否则会出现多个正确答案；
  3. 材料是维基百科段落，域偏窄（体育/历史/人物）。

### P2-4 clue/clue（config c3）—— 中文原生 3–4 选 1 阅读理解

- 链接：https://huggingface.co/datasets/clue/clue/tree/28178267a609dd08bdc703dd6c931dfc2c2f4431
- revision：`28178267a609dd08bdc703dd6c931dfc2c2f4431`｜许可：**未查到**（CLUE 卡面 `license: unknown`；上游 CLUEbenchmark/CLUE 仓库无 LICENSE；
  C3 原始仓库 nlpdata/c3 license = NOASSERTION；另一镜像 dataset-org/c3 卡面写 "Dataset provided for research purposes only"）→ **标注风险**
- 规模：c3 配置 **train 11,869 / validation 3,816 / test 1,625**（/info 实测；整个 CLUE 12 个 config 合计 train 696,947）
- 语言：**zh**｜字段（实测）：`id, context`（多轮对话/短文列表）、`question`、`choice`（列表）、`answer`（字符串）
- 是否原生 (question, options, target)：**是**（原生四元组）｜答案是否封闭：**是**——实测 100/100 行 gold ∈ choice，选项数 4 个（79 行）/ 3 个（21 行）
- 负类：每题 2–3 个错误项
- **选项可否自动生成：不需要生成（L0）**
- 能力维度：P2（中文短对话与短文的细节/推断）
- 已知限制：
  1. **许可未查到**（三层镜像的许可表述互相不一致）→ 需 Lead 裁决风险；
  2. 材料以短对话为主（实测样例行均为 2–3 轮对话），**不是长上下文**；
  3. 同一 bundle 里其它 config 形状不同（`chid` 多标签、`cmnli`/`ocnli` 无原生问句），接入时要按 config 白名单。

### P2 次级候选与负面案例

| 候选 | revision / 许可 | train 行数 | 语言 | 原生选项 | 选项生成 | 结论 |
|---|---|---|---|---|---|---|
| [hotpotqa/hotpot_qa](https://huggingface.co/datasets/hotpotqa/hotpot_qa/tree/1908d6afbbead072334abe2965f91bd2709910ab) | `1908d6afbbead072334abe2965f91bd2709910ab` / cc-by-sa-4.0 | 90,447（distractor 与 fullwiki 同规模） | en | ✗（答案自由文本） | **comparison 子集答案就是 Yes/No → 零生成 noul**（实测 200 行 comparison 19% ≈ 1.7 万条）；bridge 子集答案是短实体 → L1/L2 生成 | **推荐作为 P2 的补充**：多跳、跨段落；限制是 bridge 部分需生成干扰项，且答案有表面形式差异 |
| [dirtycomputer/dureader_yesno-data](https://huggingface.co/datasets/dirtycomputer/dureader_yesno-data/tree/52659cc967cbceecad521f39f43930336197eb9e) | `52659cc967cbceecad521f39f43930336197eb9e` / **未查到**（无卡面许可；上游 baidu/DuReader 仓库无 LICENSE） | 75,391（仅 train） | **zh** | noul（`yesno_answer ∈ {Yes,No}`） | 不需要 | 中文真实网络问答 + 多段材料 + noul，**形态极佳**；但**许可与血缘均未查到**（镜像来源不明）→ 高风险 |
| [hfl/cmrc2018](https://huggingface.co/datasets/hfl/cmrc2018/tree/137f2c45a24275fb68f6961c4d357f46288886aa) | `137f2c45a24275fb68f6961c4d357f46288886aa` / cc-by-sa-4.0 | 10,142 | zh | ✗（抽取式跨度） | **L1**：从同段落抽同类型跨度做干扰项 | 中文抽取式阅读理解，可作 c3 的补充；需自建干扰项 |
| [ucinlp/drop](https://huggingface.co/datasets/ucinlp/drop/tree/95cda593fae71b60b5b19f82de3fcf3298c1239c) | `95cda593fae71b60b5b19f82de3fcf3298c1239c` / cc-by-sa-4.0 | 77,400 | en | ✗ | **L1/L2**：答案是数字/日期/跨度（实测 `answers_spans.types`），数值型可扰动，跨度型需从段落抽 | 需要离散推理（加减/排序/计数）的阅读理解；**限制**：答案可能是多跨度，且类型混杂 |
| [clue/clue（chid）](https://huggingface.co/datasets/clue/clue/tree/28178267a609dd08bdc703dd6c931dfc2c2f4431) | 同 CLUE / 单 config `thu-coai/chid` 为 apache-2.0 | 84,709 | zh | ✓（10 成语候选） | 不需要 | **不推荐**：实测每行平均 **6.9/10** 个候选被标为"可接受"（min 3 / max 10），等于干扰项里混着正解 → 单选信号噪声过大 |
| [ehovy/race](https://huggingface.co/datasets/ehovy/race/tree/2fec9fd81f1dc971569a9b729c43f2f0e6436637) | `2fec9fd81f1dc971569a9b729c43f2f0e6436637` / other（卡面明示 **non-commercial research purpose only**） | 87,866 | en | ✓（4 选 1） | 不需要 | 形态很好（原生 4 选 1、规模大），但**非商用** → 记录风险后由 Lead 决策 |
| [sagnikrayc/mctest](https://huggingface.co/datasets/sagnikrayc/mctest/tree/00355bee8104a40d80665be0e4570f4a8b2c96f7) | `00355bee8104a40d80665be0e4570f4a8b2c96f7` / other（卡面：**Microsoft Research License Agreement**） | 1,480 | en | ✓（4 选 1） | 不需要 | 规模小 + 许可限制明确 → 不推荐 |
| [clue/clue（cluewsc2020）](https://huggingface.co/datasets/clue/clue/tree/28178267a609dd08bdc703dd6c931dfc2c2f4431) | 同 CLUE | 1,244 | zh | 2 个跨度（`span1_text`/`span2_text`） | 不需要 | **指代消解**专用，选项来自源标注的两个跨度；规模小，可作点缀 |

## 4. 优先级 3：广泛世界知识及其应用

### P3-1 cais/mmlu —— 57 学科原生 4 选 1（评测价值高，训练价值受本仓边界限制）

- 链接：https://huggingface.co/datasets/cais/mmlu/tree/c30699e8356da336a370243923dbaf21066bb9fe
- revision：`c30699e8356da336a370243923dbaf21066bb9fe`｜许可：**mit**（卡面 / tags `license:mit`）
- 规模（config `all` 实测）：**test 14,042 / validation 1,531 / dev 285 / auxiliary_train 99,842**；57 个学科各自成 config
- 语言：en｜字段：`question`、`subject`、`choices`（4 项）、`answer`（ClassLabel 下标）
- 是否原生 (question, options, target)：**是**｜答案封闭简练：**是**｜负类：每题 3 个错误项
- **选项可否自动生成：不需要生成（L0）**
- 能力维度：P3（人文/社科/自然科学/医学/工程入门级知识）+ P1（数学相关学科 test 合计 1,552 条）
- **必须写清的边界（否则会踩本仓数据红线）**：按 AGENTS.md"公开测试用于回归，不用于梯度"，
  MMLU 的 **test 14,042 只能做回归基准**；validation 1,531 按"dev 用于选模型"处理；
  **真正能进梯度的只有 `auxiliary_train` 99,842**——而它实测 `subject` 字段为空、内容是从 ARC/RACE/AQuA 等
  混进来的辅助训练数据（首行是一条法律责任题），**不是 MMLU 本体的知识题**。
- 已知限制：
  1. 上述划分边界：**MMLU 作为"通用知识训练源"的实际增量很有限**，它的强项是评测回归；
  2. 若 Lead 裁决放宽（MMLU test 并非本仓评测集），则 14,042 条是成本最低的知识源——**该裁决需显式记录**；
  3. 学科间规模极不均衡（几十到几百条/学科），且部分题目有已知标注错误（社区长期讨论）。

### P3-2 mandarjoshi/trivia_qa —— 13.8 万条百科事实问答（需生成选项）

- 链接：https://huggingface.co/datasets/mandarjoshi/trivia_qa/tree/0f7faf33a3908546c6fd5b73a660e0f8ff173c2f
- revision：`0f7faf33a3908546c6fd5b73a660e0f8ff173c2f`
- 许可：**卡面未查到**（`license: unknown`；卡面原文："The University of Washington does not own the copyright of the questions and documents included in TriviaQA."）；
  **上游仓库 mandarjoshi90/triviaqa = Apache-2.0** → 记录风险，非零歧义
- 规模：`rc.nocontext` 配置 **train 138,384 / validation 17,944 / test 17,210**（8 个 config 合计 728,780 train）
- 语言：en｜字段（实测）：`question`、`answer{value, aliases[], normalized_aliases[], …}`、`question_id`、`entity_pages`、`search_results`
- 是否原生 (question, options, target)：问题与答案原生，**无选项**
- 答案是否封闭且简练：**是**（实体名，且自带 aliases 别名集 → 自动判等友好）
- **选项可否自动生成：L2（需模型生成，或 L1 用实体池构造）**。干扰项质量评估：
  - 答案类型 = 实体名（人/地/作品/组织/日期）
  - 构造方式：先从问题里判定期望实体类型 → 从**同类型实体池**（可用其它问题的答案，或 Wikidata/维基标题表）抽取 3–4 个同粒度实体 → 用模型做最后一道"是否一眼可排除"的筛
  - 风险：**类型判断错就会露馅**（把国家名和作家名混在一起）；同类型里若混入"也对"的实体（同一问题的别名/变体）会造成多解 → 必须先用 aliases 去重
  - 结论：**可行，但需要一条固定流水线 + 一个质检门（见 §5）**，不能裸奔式生成
- 能力维度：P3（百科式世界知识，覆盖面最广）
- 已知限制：
  1. 许可记录不完整（卡面 unknown + 版权声明）；若要求许可零歧义，**等价替换为 NQ-Open**（见 P3-3）；
  2. 答案开放（同一问多答案）→ 生成选项时要固定一个规范答案文本，其余走别名判等；
  3. 问题来自 trivia 网站，风格口语化、含年代词（知识时效性随时间衰减）。

### P3-3 google-research-datasets/nq_open —— 8.8 万条短答案事实问答（许可最干净）

- 链接：https://huggingface.co/datasets/google-research-datasets/nq_open/tree/5dd9790a83002ad084ddeb7c420dc716852c6f28
- revision：`5dd9790a83002ad084ddeb7c420dc716852c6f28`｜许可：**cc-by-sa-3.0**（卡面）
- 规模：**train 87,925 / validation 3,610**（无 test）
- 语言：en｜字段（实测）：`question`、`answer`（列表，1–5 个可接受短答案）
- 是否原生 (question, options, target)：无选项｜答案封闭简练：**是**（短实体/短语）
- **选项可否自动生成：L2/L1**（同 TriviaQA 的实体池路线）。评估：答案更短更规范（多为专名/数字/年份），
  干扰项可比 TriviaQA 更容易保持同粒度；风险同样在"类型判定"与"多答案去重"
- 能力维度：P3（事实知识）
- 已知限制：
  1. 问题短、常为检索式（"where did they film hot tub time machine"），**题面质量低于 TriviaQA**；
  2. 答案是列表（多可接受答案），入库前要决定"规范答案 + 别名表"的存法（建议存 `answer` 主文本，别名进 `meta`）；
  3. cc-by-sa-**3.0**（比常见的 4.0 更老，仍要求署名+相同方式共享）。

### P3-4 原生选项的知识类小集（零生成成本，规模是短板）

| 候选 | revision / 许可 | train / validation | 语言 | 选项 | 选项生成 | 维度与限制 |
|---|---|---|---|---|---|---|
| [tau/commonsense_qa](https://huggingface.co/datasets/tau/commonsense_qa/tree/94630fe30dad47192a8546eb75f094926d47e155) | `94630fe30dad47192a8546eb75f094926d47e155` / **mit**（卡面） | 9,741 / 1,221（test 1,140 无公开标签） | en | 5 选 1（`choices.label/text` + `answerKey`） | 不需要 | **日常物理与社会常识**，最贴近"通用智力"；限制：规模小、部分题需世界知识以外的语用推断 |
| [allenai/qasc](https://huggingface.co/datasets/allenai/qasc/tree/a34ba204eb9a33b919c10cc08f4f1c8dae5ec070) | `a34ba204eb9a33b919c10cc08f4f1c8dae5ec070` / **cc-by-4.0**（卡面） | 8,134 / 926 | en | **8 选 1** + 两条支撑事实 | 不需要 | 自然科学多跳（两事实组合）；限制：8 选 1 干扰项多但语义相近，规模小 |
| [allenai/openbookqa](https://huggingface.co/datasets/allenai/openbookqa/tree/388097ea7776314e93a529163e0fea805b8a6454) | `388097ea7776314e93a529163e0fea805b8a6454` / **卡面 unknown**（上游 allenai/OpenBookQA GitHub = **Apache-2.0**） | 4,957 / 500（main 与 additional 各 4,957 train，注意去重） | en | 4 选 1 | 不需要 | 科学常识 + 核心事实；限制：规模小、许可需引用上游 |
| [allenai/ai2_arc](https://huggingface.co/datasets/allenai/ai2_arc/tree/210d026faf9955653af8916fad021475a3f00453) | `210d026faf9955653af8916fad021475a3f00453` / **cc-by-sa-4.0**（卡面） | 3,370（Easy 2,251 + Challenge 1,119）/ 869 | en | 3–5 选 1（`choices` + `answerKey`，实测含 `answerKey="2"` 的异常行） | 不需要 | 小学科学；限制：**train 只有 3,370**，本体是测试基准 |
| [allenai/sciq](https://huggingface.co/datasets/allenai/sciq/tree/2c94ad3e1aafab77146f384e23536f97a4849815) | `2c94ad3e1aafab77146f384e23536f97a4849815` / **cc-by-nc-3.0**（卡面明示 NonCommercial） | 11,679 / 1,000 | en | 4 选 1（`correct_answer` + 3 个 distractor 字段）+ 支撑段落 | 不需要 | 科学 QA；限制：**非商用**、distractor 为源自带（本文未逐条核验其质量） |

### P3-5 中文世界知识的现实：可训练量极小

| 候选 | revision / 许可 | 划分 | 语言 | 选项 | 选项生成 | 结论 |
|---|---|---|---|---|---|---|
| [ceval/ceval-exam](https://huggingface.co/datasets/ceval/ceval-exam/tree/617524a00b307ff6f9933702f724131fe12ca7ce) | `617524a00b307ff6f9933702f724131fe12ca7ce` / **cc-by-nc-sa-4.0**（卡面） | **test 12,342 / val 1,346 / dev 260**，52 学科 | zh | ✓ 4 选 1（`A–D` + `answer`） | 不需要 | 形态与规模都好，但 **test 是公开测试集 → 不能进梯度**；可训练量只有 val 1,346 / dev 260（选模型用） |
| [haonan-li/cmmlu](https://huggingface.co/datasets/haonan-li/cmmlu/tree/efcc940752ea4a1ea94d2727f11f83858d64fc8e) | `efcc940752ea4a1ea94d2727f11f83858d64fc8e` / **cc-by-nc-4.0**（卡面 tags；README 正文写 CC BY-NC-**SA** 4.0，两者不一致） | 卡面自述："development and test dataset for each of 67 subjects, **5 questions in development**, 100+ in test" → **可训练 ≈ 335 条** | zh | ✓ 4 选 1 | 不需要 | 训练增量几乎为零（dev 按"选模型"用），只能做评测 |
| [openai/MMMLU](https://huggingface.co/datasets/openai/MMMLU/tree/325a01dc3e173cac1578df94120499aaca2e2504) | `325a01dc3e173cac1578df94120499aaca2e2504` / **mit** | 14 个语言配置（各 14,042）+ 合并配置 `default`（196,588），**全部 test** | 多语（含 zh） | ✓ 4 选 1 | 不需要 | 职业翻译的多语 MMLU，**只能做多语回归基准** |
| [chiayewken/m3exam](https://huggingface.co/datasets/chiayewken/m3exam/tree/c219dfc50d989a903052f19190a12b4d9866aacb) | `c219dfc50d989a903052f19190a12b4d9866aacb` / 卡面无许可（**未查到**；上游 DAMO-NLP-SG/M3Exam `gated`/401 未取到） | chinese 711（dev+test），全 9 语言 dev 194 / test 9,307 | zh 等 | ✓ 4 选 1 | 不需要 | 多语考试基准，**只有 dev+test → 评测用** |

**结论**：中文世界知识这条线上**没有找到能进梯度的规模化来源**（C-Eval/CMMLU 的可训练部分合计约 1.7 千条）。
这是三条线里最大的空洞，需要 Lead 显式决策：要么放宽"公开测试集不进梯度"的边界，要么接受"中文知识靠模型生成题干"的合成路线。

## 5. 干扰项生成可行性（按答案类型的统一评估）

Lead 明确的成败关键。下面把候选按**答案类型**归并，给出构造方式与质量结论；**本项目已有的转换口径是
"保留提问 + 把源标签作为一个选项"（CONTRACT §2.1 的 `origin=source`），本轮放宽后新增
"源问题 + 源答案 + 生成干扰项"（属 `origin=taxonomy`，题面保留源问句、选项由我们补齐）**。

| 级别 | 含义 | 代表来源 |
|---|---|---|
| **L0** | 选项原生，零生成 | bigbench、aqua_rat、math_qa、mmlu、commonsense_qa、qasc、openbookqa、ai2_arc、sciq、cosmos_qa、clue/c3、logiqa、proofwriter（标签集）、squad_v2 noul、multirc noul、hotpotqa comparison |
| **L1** | **确定性构造**（规则 + 源内池），可离线复算、无需模型 | GSM8K/math23k-reborn 的数值扰动；SQuAD2.0/CMRC2018 的**同段落同类型跨度**；DROP 的数字型答案 |
| **L2** | 需模型生成（或生成后必须过质检门） | TriviaQA / NQ-Open 的实体名；HotpotQA bridge 实体；DROP 的跨度型答案 |
| **L3** | **不适合**生成选项（自由文本/多值/开放式） | `list_functions`、`repeat_copy_logic`、`operators`、`dyck_languages`、`word_sorting`、`qa_wikidata`（无 MC 的任务）、CHID（多值）、MATH 类 LaTeX 表达式答案 |

**L1/L2 的干扰项质量门槛（建议直接落成 convert 阶段的断言）**：
1. **同类同粒度**：数值型必须同数量级；实体型必须同实体类别；跨度型必须同段落同类型；
2. **不可一眼排除**：干扰项长度/形态与正确项相近（数值位数、实体词数差 ≤1）；
3. **不与任何源标注答案重合**：实体名要用 aliases 全集查重；跨度要排除段落内其它被标注的答案；
4. **无重复选项**：去重后仍须 ≥2 项；
5. **位置随机化**：AQuA-RAT 无位置偏斜，但自造选项必须打乱，否则模型学位置；

**风险提示**：L2 是唯一会把"通用智力"训坏的环节——如果干扰项太弱，模型学到的是"排除法"而不是知识；
建议 L2 来源**只作为 P3 的补充量**，不要让它们主导语料；同时保留 `meta.option_origin=generated` 以便后续消融。

## 6. 未采纳清单（负面结果与风险登记）

| 项 | 结论 | 理由（实测/卡面） |
|---|---|---|
| [clue/clue chid](https://huggingface.co/datasets/clue/clue/tree/28178267a609dd08bdc703dd6c931dfc2c2f4431) / [thu-coai/chid](https://huggingface.co/datasets/thu-coai/chid/tree/47ad8022d369233bea2f4a8112268f9a9a039a43) | **不用**（单选） | 实测 100 行：每行平均 6.9 个候选被标"可接受"（min 3 / max 10），干扰项中混正解 |
| [ehovy/race](https://huggingface.co/datasets/ehovy/race/tree/2fec9fd81f1dc971569a9b729c43f2f0e6436637) | 记录风险 | 卡面明示 non-commercial research only |
| [sagnikrayc/mctest](https://huggingface.co/datasets/sagnikrayc/mctest/tree/00355bee8104a40d80665be0e4570f4a8b2c96f7) | 不用 | 卡面 Microsoft Research License Agreement + 规模仅 1,480 |
| [allenai/sciq](https://huggingface.co/datasets/allenai/sciq/tree/2c94ad3e1aafab77146f384e23536f97a4849815) / [ceval](https://huggingface.co/datasets/ceval/ceval-exam/tree/617524a00b307ff6f9933702f724131fe12ca7ce) / [cmmlu](https://huggingface.co/datasets/haonan-li/cmmlu/tree/efcc940752ea4a1ea94d2727f11f83858d64fc8e) | 可用但标注 | 非商用（NC / NC-SA）→ 只作信息登记，由 Lead 判断 |
| [yale-nlp/FOLIO](https://huggingface.co/datasets/yale-nlp/FOLIO/tree/4c1f14bf39ca6a6de242bd8f75ef313b4b436818) | 用镜像替代 | `gated=auto`（需登录接受条款），datasets-server 401；改用 tasksource/folio（1,001 条） |
| [DAMO-NLP-SG/M3Exam](https://huggingface.co/datasets/DAMO-NLP-SG/M3Exam) | 未取到 | HF API 401（受限/不存在），仅 chiayewken/m3exam 镜像可读且只有 dev+test |
| `lighteval/MATH`、`hendrycks/competition_math` | 不用 | 401 未取到；且答案是 LaTeX 表达式（长度/等价形式不唯一）→ 选项生成不适合 |
| `tasksource/multirc`、`allenai/multirc`、`tasksource/mctest`、`hfl/c3`、`hfl/chid`、`tasksource/snli`、`tasksource/bigbench-hard` | **不存在** | HF API 401 / 404（本轮实测），规范 id 分别是 super_glue、sagnikrayc/mctest、clue/clue、thu-coai/chid |
| [SUSTech/math23k](https://huggingface.co/datasets/SUSTech/math23k/tree/687c1c322a1e420507238e6d483c231d732bc789) | 用镜像替代 | datasets-server 501、卡面无许可；改用 Azure99/math23k-reborn（apache-2.0，train 22,329） |
| `score` 形态来源 | **未找到** | 三条维度上没有任何"天然分级 + 闭合量程"的公开来源；契约的第三种原语在本轮补源里没有供给 |
| 许可**未查到**（需标注风险） | tasksource/folio（"cc" 具体版本）、tasksource/proofwriter、lucasmccabe/logiqa、SUSTech/math23k、dirtycomputer/dureader_yesno-data、clue/clue（CLUE 与 C3 各层表述不一）、allenai/openbookqa（HF 卡面 unknown，上游 Apache-2.0）、mandarjoshi/trivia_qa（卡面 unknown，上游 Apache-2.0）、hails/agieval-logiqa-zh（卡面无，上游 MIT）、chiayewken/m3exam | 全部按"信息登记 + 风险标注"处理，不作准入否决 |

## 7. 若只能接 3 个：接哪三个

**推荐：① tasksource/bigbench ② allenai/cosmos_qa ③ mandarjoshi/trivia_qa**

理由（按"每条线各取一个 + 成本/风险最低"）：

1. **tasksource/bigbench（P1）**：唯一一个**同时**满足"原生选项、独热标签实测 100% 干净、规模 19 万、
   许可 apache-2.0 明确、覆盖形式逻辑+算术+约束满足+不可判定"的来源；L0 零生成成本，
   等于把 P1 的干扰项质量问题一次性消掉。它的短板（单 config 小、部分任务要排除）都是**白名单式的施工问题**，不是数据质量问题。
2. **allenai/cosmos_qa（P2）**：原生 4 选 1、25,262 条 train、**标签分布实测均衡**、许可 cc-by-4.0 干净、
   题目本身就是"需要整合多句信息 + 常识推断"的阅读理解。代价只是"HF 仓库无数据文件，需按 loader 的外链下载 CSV"。
   若更看重"证据是否充分"这一维度，**等价替换为 rajpurkar/squad_v2**（130,319 条 train、33.8% 不可回答 → noul，
   零生成成本、许可 cc-by-sa-4.0），代价是题面措辞由我们写（`origin=taxonomy`）。
3. **mandarjoshi/trivia_qa（P3）**：P3 里唯一有真实体量（138,384 条 train）、答案简练（实体名 + 别名集）的来源；
   它是三条线里**唯一必须生成干扰项**的一环，且干扰项质量可控（同类型实体池 + 质检门，§5）。
   - **许可零歧义替代**：`google-research-datasets/nq_open`（cc-by-sa-3.0，87,925 条），代价是题面更短更检索式；
   - **不做生成、只做评测**：`cais/mmlu`（mit，test 14,042 做回归、auxiliary_train 99,842 可进梯度但来源混杂）+
     `tau/commonsense_qa`（mit，9,741 条原生 5 选 1）——但这两者加起来只有约 1 万条**干净的原生知识题**，撑不起 P3 的体量。

**明确不选**：CLUE c3 / dureader-yesno（许可未查到，作为第 4 顺位备选）、chid（多值噪声）、RACE / MCTest（许可限制）、
C-Eval / CMMLU（test-only，训练增量 ≈ 1.7 千条）。

## 8. 复算与取证方式

本文所有数字都可用下面几条命令/接口独立复核（本轮实际执行过；注意 datasets-server 有速率限制，需串行 + 退避）：

    # 1) 固定 revision / 许可 / 是否 gated（信息登记）
    https://huggingface.co/api/datasets/<id>
    # 2) 划分规模（行数）
    https://datasets-server.huggingface.co/info?dataset=<id>      # 逐 config/split 的 num_examples
    https://datasets-server.huggingface.co/size?dataset=<id>      # 同上（splits 端点现返回 null，要用 size/info）
    # 3) 行结构与标签分布（length ≤ 100，超出返回 422）
    https://datasets-server.huggingface.co/rows?dataset=<id>&config=<cfg>&split=<split>&offset=0&length=100
    # 4) 卡面许可原文
    https://huggingface.co/datasets/<id>/raw/<sha>/README.md
    # 5) 上游许可
    https://api.github.com/repos/<owner>/<repo>
    # 6) 仓外原始文件（HF 仓库只有 loading script 的：math_qa / cosmos_qa）
    https://math-qa.github.io/math-QA/data/MathQA.zip                       # 7,302,821 B，29,837/4,475/2,985
    https://github.com/wilburOne/cosmosqa/raw/master/data/valid.csv         # 2,128,345 B，2,985 行

**局限复述**：datasets-server 不遵守 revision（CONTRACT §6.1），所以"实测"是 2026-10-15 的 HEAD；
固定 sha 用于将来 `resolve/<sha>/<path>` 的逐字节复现；本轮未做逐字节下载校验（除 math_qa/cosmos_qa 外）。

## 9. 待 Lead 裁决 / 未查到

1. **中文世界知识的可训练来源**（C-Eval/CMMLU 只有 val/dev 能进梯度）→ 放宽边界，还是走合成？
2. **MMLU test 的使用**：按现行边界只能回归；若裁决可进梯度，P3 成本立刻降低。
3. **TriviaQA / TriviaQA 型生成选项**是否接受"卡面许可 unknown + 上游 Apache-2.0"这一风险等级。
4. CLUE c3 与 dureader-yesno：**许可均未查到**（三层镜像表述不一致 / 镜像无血缘）→ 是否接受。
5. **未查到**：tasksource/folio 的 "cc" 具体版本；tasksource/proofwriter 的许可；lucasmccabe/logiqa 的许可；
   SUSTech/math23k 的许可；thu-coai/chid 之外 CHID 的官方许可；dirtycomputer/dureader_yesno-data 的血缘。
6. **未实测**：allenai/math_qa 在 HF 上的字段级结构（datasets-server 501，本文改用官方 zip 实测，字段与行数已核对）；
   allenai/cosmos_qa 的 train.csv 标签分布（本文只逐行核对了 valid.csv 2,985 行）。
