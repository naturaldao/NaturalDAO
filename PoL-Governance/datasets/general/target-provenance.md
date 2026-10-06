# target 溯源报告：probs 到底是怎么产生的

**范围**：冻结语料 `D:\pol2-raw\general-private\data\items.final.jsonl.gz`（23,855 条 / 31,786 个 target，sha256 `ba615c96c0dc13cbc4caa8b0f83ac1326abc13700bde98579f2ebb9f38bdaece`，见 [items.final.report.json](data/items.final.report.json)）。
**本轮只读**：不改数据、不动划分、不做任何 git 写操作。
**产出**：本报告 + §6 的 `target_type` 回填提案（可被脚本直接执行）。

数据指纹与本报告所有计数由附录 B 的只读过程从冻结文件现算，不引用任何二手统计。

---

## 0. 一页结论

### 0.1 一句话

同一个 `probs` 字段里装的是**至少 5 种不同的量**：教师模型的预测分布、按规则算出来的参考标签、并列选项的均分占位、我们自己用 `point_mass` 造出来的单点分布、以及**整条子流恒定的常量**。其中**只有 432 个 target（占全部 31,786 的 1.4%）在文档上被明确写成「由状态精确算出的概率」**，这才是「校准参照」意义上的那一个量；其余所谓「真分布」都是**教师信念**，只能当**软蒸馏目标**，不能当校准基准。

### 0.2 全量形态（实测，与任务书给的数字有一处 1,730 的错位）

| target 形态 | 条数 | 占比 |
|---|---:|---:|
| 伪 one-hot（含我们造的和来源自带的） | 14,119 | 44.4% |
| 只有 answer、无 probs | 8,417 | 26.5% |
| 真·非退化分布（soft） | 7,520 | 23.7% |
| 全候选等值（uniform） | 1,730 | 5.4% |
| **合计** | **31,786** | 100% |

任务书写的是「真分布 9,250（29%）/ 伪 one-hot 14,119 / 均匀 1,730 / 只有 answer 6,687」。9,250 = 7,520 + 1,730，说明那份口径把 uniform 并进了「真分布」，同时又把 1,730 从 answer_only 里减掉了（8,417 − 1,730 = 6,687）——同一个 1,730 被移动了两次，四类全加仍是 31,786，所以总数对、分类错位。**本报告一律以实测 7,520 / 1,730 / 8,417 为准**；「29%」在本文中始终指 7,520 + 1,730 = 9,250 这个并集。

### 0.3 那 29% 里有多少能当校准参照

| 29% 的构成 | 条数 | 语义 | 能当校准参照？ |
|---|---:|---|---|
| procedural 精确后验 / 精确 k–n | **432** | `rule_counter` | ✅ **能**（限定在该合成任务内） |
| jev-distill-v3 `yuri_v3` 教师软标签 | 5,364 | `model_logits` | ❌ 只能当软蒸馏目标 |
| system-one-270m 教师 logprob 集合均值 | 1,492 | `model_logits` | ❌ 只能当软蒸馏目标 |
| open-jev「并列均分」 | 201 | `rule_counter` | ❌ |
| jev-distill-v3 `openjev_v2`（Open-Jev 转出） | 31 | `rule_counter` | ❌ |
| uniform 全桶（其中 1,621 是**整条子流恒定 0.5**） | 1,730 | 无信息 | ❌ |
| **合计** | **9,250** | | **432，即 4.7%** |

一句话：**「29% 真分布」里只有 432 条（全语料的 1.4%）可以直接拿来做概率校准参照；另外 6,856 条是教师分布，能当软目标但拿它测校准等于在测「和教师像不像」；剩下 1,962 条（uniform + 并列均分）根本不携带方向信息，必须先从校准口径里剔除。**

### 0.4 三条最容易踩的坑（本次实测新增）

1. **`jev-distill-v3` 这一个 slug 里混了三种语义**：教师蒸馏（`yuri_v3`）、整条恒定 0.5 的退化流（`yuri_v1`）、以及 Open-Jev 规则标签的转出（`openjev_v2`）。按 slug 分组统计是错的，必须下钻到 `meta.native_source`。
2. **`yuri_v1` 子流：1,661 行原始行、1,621 行入语料，target 只有一个取值 `[0.5, 0.5]`。** 这不是「真不确定」，是**常量**——一条只教模型输出 0.5 的流。
3. **「伪 one-hot」里只有 5,488 条真是「来源只给硬标签、我们替它写成单点」**；另外 8,631 条是**来源自己就给了一组 one-hot 权重**（Open-Jev 控制规则 4,221、procedural 3,696、jev-distill 的 openjev_v2 714）。这两类的处置不同：前者是「我们造的形态」，后者是「来源的真实取值恰好退化」。

---

## 1. 证据等级与判定规则

每条结论都标来源与置信度。记号：

| 标记 | 含义 |
|---|---|
| **【文档】** | 上游卡面 / 上游代码 / 上游仓库内 provenance 文件**明说**；附可点击 URL + 固定 revision |
| **【代码】** | 从 [convert.py](convert.py)（或仓外 `D:\pol2-raw\zh-final\build_zh.py`）读出的映射事实；附函数名与行号 |
| **【实测】** | 从冻结语料 / 原始 `rows.jsonl` 现算的取值事实；附口径 |
| **【推断】** | 上面三类都不足以直接支持、由我合并推断；**一律同时给出备选解释** |

置信度：**高**（文档原文直接支持）/ **中**（文档只支持一部分，其余靠代码或数据闭合）/ **低**（只有间接证据）。

**判定纪律**（对应任务硬要求 2）：数值形态（熵、最大概率、小数位数、是否 one-hot）**只允许出现在「回填候选」和「旁证」两处**，不允许单独作为 `distribution_semantics` 的判定依据。本报告每一次用形态，都标注了它是「旁证」还是「唯一的依据」。

---

## 2. 全量实测计数

### 2.1 按来源（`source.slug`）

| slug | 条数 | target 数 | answer_only | 伪 one-hot | uniform | soft |
|---|---:|---:|---:|---:|---:|---:|
| deepexi-fcs-v3（中文） | 7,872 | 7,872 | 7,872 | – | – | – |
| jev-distill-v3 | 7,756 | 7,756 | – | 714 | 1,647 | 5,395 |
| jev-decisions-general-50k | 3,802 | 3,802 | – | 3,802 | – | – |
| procedural-typed-decisions | 1,500 | 4,691 | 545 | 3,696 | 18 | 432 |
| systemone-lite-general | 1,479 | 1,479 | – | 1,479 | – | – |
| open-jev | 792 | 4,479 | – | 4,221 | 57 | 201 |
| system-one-270m | 447 | 1,500 | – | – | 8 | 1,492 |
| jev-decisions-strata | 207 | 207 | – | 207 | – | – |
| **合计** | **23,855** | **31,786** | **8,417** | **14,119** | **1,730** | **7,520** |

全部 31,786 个 target 都带 `answer`；8,417 个没有 `probs` 键。

### 2.2 下钻到 `meta.native_source`：slug 内部的语义并不单一

| slug | `meta.native_source` | target 数 | soft | uniform | 伪 one-hot |
|---|---|---:|---:|---:|---:|
| jev-distill-v3 | yuri_v3 | 5,378 | 5,364 | 14 | 0 |
| jev-distill-v3 | **yuri_v1** | **1,621** | 0 | **1,621** | 0 |
| jev-distill-v3 | openjev_v2 | 757 | 31 | 12 | 714 |
| open-jev | customer-control-v1 | 4,206 | 201 | 57 | 3,948 |
| open-jev | vizdoom-basic-v1 | 273 | 0 | 0 | 273 |

### 2.3 任务书那张「平均熵」表复现（口径 = 只统计 soft 子集，单位 nats）

| slug | soft n | 平均熵 | 平均最大概率 |
|---|---:|---:|---:|
| jev-distill-v3 | 5,395 | 0.755 | 0.666 |
| open-jev | 201 | 0.693 | 0.500 |
| procedural-typed-decisions | 432 | 0.347 | 0.853 |
| system-one-270m | 1,492 | 0.122 | 0.942 |

复现完全吻合，说明任务书那张表就是「soft 子集 + nats」。需要点明：**open-jev 的 0.693 = ln 2、平均最大概率恰好 0.500，不是「平均的软」，而是「软的那 201 条全是并列均分」**（§3.2）。四个数字差 6 倍不是「同一个量的不同尺度」，而是**四个不同的量**——本报告逐条给出它们各自是什么。

---

## 3. 逐来源溯源卡片

### 3.1 jev-distill-v3（SargeDev/jev-distill-corpus-v3，apache-2.0）

**revision**：`fc99c6357a9f89f7512c4a987314352addead049`；config `default`，split `train`，row_limit 8000（head）。

**① probs 来自哪个字段（【代码】）**

| 项 | 值 |
|---|---|
| 原始字段 | `target`：与 `options` 等长的 float 数组；`kind` ∈ {noul, choice, score} |
| 映射 | [convert.py](convert.py) `native_jev_typed`（L1112–1155）→ `prob_map`（L942–947）→ `normalize_probs`（L137–147） |
| 具体动作 | 权重向量**原样**绑到候选 key 上；`/total` 归一；`round(value, 6)`；`answer` 取 `argmax_key` |
| 旗标 | 源和目标不等长 → `options_target_misaligned` 跳过；sum≠1 → `probs_normalized`（本语料 16 条）；全等值 → `uniform_target` |

**② 上游怎么产生该字段（【文档】，高）**

卡面（固定 revision 的 README）逐字：

> | `yuri_v3` | 498,010 | Synthetic operational scenarios across 53 domains (...), 3 primitives per domain. **Labels distilled from Jev 1.13 (TypeSafe) via OpenRouter.** |
> | `yuri_v1` | 148,154 | Memory-relevance `noul` pairs **distilled from a 32B teacher** over 18 open-domain QA datasets (...). |
> | `openjev_v2` | 94,801 | **Rows from ZefanCai/Open-Jev** `release-v2-redistributable` (CC0), reschema'd to the unified format. |
> - Teacher: **Jev 1.13 via the OpenRouter Decisions API, full distributions per question**
> - Degenerate labels (max-prob >= 0.999 with confidence >= 0.95): **filtered (1.5%)**
> - noul calibration: mean 0.45, stdev 0.28 — the teacher discriminates rather than rubber-stamps
> All targets are normalized probability distributions (sum to 1).
> `score`: distribution over ordered levels `0..5` (labels distilled from Jev's expected-score distribution)

URL：https://huggingface.co/datasets/SargeDev/jev-distill-corpus-v3/blob/fc99c6357a9f89f7512c4a987314352addead049/README.md

教师侧（Jev）自己怎么说（【文档】，厂商自述）——TypeSafe 官方博客：

> Possible outputs and structure are defined in advance. The model never makes type errors.
> **All answers are accompanied with calibrated probabilities and confidence scores.**
> **Jev outputs all probabilities in parallel instead of autoregressively generating by token.**

URL：https://typesafe.ai/blog/introducing-system-one-models-and-jev

【推断，中】综合两句：Jev 是**非自回归**、在预先定义的封闭结构上**并行输出概率**的模型，所以 `target` 是**模型自己的预测分布**，而不是「把文字答案再解析出来」，也不是逐 token logprob 的拼装。它属于 `model_logits` 一类。**但「API 那一串数字具体怎么读出来」（并行 head 的 softmax？先算分再归一？2 位小数是 API 还是导出时舍入？）没有任何文档**——这一点标为 `mechanism_unknown`（见 §7）。另外「calibrated」是厂商自我宣称，本项目没有复核。

**③ 语义分类**

| 子流 | n | 判定 | 依据 |
|---|---:|---|---|
| `yuri_v3` | 5,378 | **`model_logits`**（教师 Jev 1.13 的预测分布） | 【文档】"Labels distilled from Jev 1.13"；置信度高（类别）、中（具体机制） |
| `yuri_v1` | 1,621 | 语义仍是 `model_logits`，但**取值退化为常量**，形态上按无信息处理 | 【实测】1,661 行原始数据只有 1 个不同取值 `[0.5, 0.5]`；置信度高 |
| `openjev_v2` | 757 | **`rule_counter`**（Open-Jev 的规则参考标签，见 §3.2） | 【文档】卡面明说是 Open-Jev 转出；置信度高 |

**旁证（不是依据）**：`yuri_v3` 的 5,378 个 target 里**没有一个**是 one-hot —— 与卡面「max-prob ≥ 0.999 的退化标签已过滤掉 1.5%」自洽；反过来 `openjev_v2` 有 714 个 one-hot，说明那条过滤只作用于教师蒸馏流，没有作用于转出流。另外 `yuri_v3` 的取值被**上游**量化到 2 位小数（原始 `rows.jsonl` 里就是 `0.01, 0.41, 0.51`），4 选项时出现 `0.101 / 0.1616 / 0.0505 / 0.6869` 这种「同量子 1/99」的形态 —— 即上游先四舍五入到 2 位、再由我们归一（16 条 `probs_normalized`）。**这是上游的舍入，不要读成我们的加工。**

**④ 是否可比**

- **跨子流不可比**：同一个 slug 里三种语义，直接按 slug 混训等于把「教师信念」「常量 0.5」「并列均分」平均在一起。
- **与 system-one-270m 不可比**：两者都是「模型分布」，但一个是 Jev 一次并行输出的分布，另一个是 gpt-oss-20b **多次排列读取的均值**（度量的是采样/排列方差）。同一个 0.6 含义不同。
- **与 procedural / open-jev 不可比**：后者是**由状态算出的世界概率**，前者是**信念**。

**⑤ 能否作为校准基准**

**不能**（`yuri_v3` 只能当**软蒸馏目标**；`yuri_v1` 必须先剔除）。理由：校准要求「参照量是结果发生的概率」。教师分布是**教师认为**的分布，教师会错；拿它测学生的 ECE，测到的是「学生和教师像不像」，不是「学生的概率是否诚实」。`yuri_v1` 的 1,621 条是常量，信息量为 0，作为目标只会把学生往 0.5 拉。

---

### 3.2 open-jev（ZefanCai/Open-Jev，cc0-1.0）

**revision**：`c67699e13d0ae25e35b77165a4b6b079bedc8aba`；config `release-v2-redistributable`，split `train`，row_limit 6000（head）。

**① probs 来自哪个字段（【代码】）**

| 项 | 值 |
|---|---|
| 原始字段 | `target`（float64 数组）+ `metadata_json`（含 `target_basis`、`provenance.annotation_status`） |
| 映射 | [convert.py](convert.py) `native_open_jev`（L1158–1210）→ 同样的 `prob_map` 归一 + `argmax_key` |
| 聚合 | 按 `group_id` 把同一 state 的多问聚成一条多问题条目；键名取 `id` 末段（`...:category`） |

**② 上游怎么产生该字段（【文档】，高）**

根卡面（固定 revision）：

> | `target` | Original numeric reference targets, represented as a float64 list. **These are labels, not measured model confidence.** |
> These are controlled, mostly synthetic tasks and reference labels. They are **not official TypeSafe/Jev training data, model predictions**, or evidence of general capability.
> Distribution, binary, multilabel and ordinal targets have different semantics; do not reduce every row to a single-class accuracy calculation.

URL：https://huggingface.co/datasets/ZefanCai/Open-Jev/blob/c67699e13d0ae25e35b77165a4b6b079bedc8aba/README.md

仓库内 `provenance/component-artifacts/` 的审计文件给到**逐族**的依据（【文档】，高）：

- `case-customer/target-statistics.json`：`"definition": "Hard: one-hot PMF. total_target_mass sums probability mass over hard and soft records..."`。其中 customer-control-v1：choice 1000 条 = **hard 900 / soft 100**；noul 2000 条 = **hard 2000 / soft 0**；score 3000 条 = **hard 2725 / soft 275**。
- `case-customer/manifest.json`：`"source_status": "Five official-public-docs forms plus a local churn rubric; ... all labels are synthetic controls."`
- `doom-basic-v1/manifest.json`：`"expert": "momentum_tracking_weak_script_v1"`；行内 `"expert_optimality_claim": false`
- `cards/ir-control-v1.md`：
  > **Choice targets are uniform over equally best passages; they do not supervise a full ranking or represent measured model uncertainty.**

URL 基址：https://huggingface.co/datasets/ZefanCai/Open-Jev/tree/c67699e13d0ae25e35b77165a4b6b079bedc8aba/provenance

**③ 语义分类（【实测】闭合【文档】）**

本语料 4,479 个 target 里，**全部取值只有 4 个不同的数：0.0 / 1.0 / 0.5 / 0.333333**。按行内 `target_basis` 分组后完全对得上文档：

| `target_basis` | n | 实测形态 | 语义 |
|---|---:|---|---|
| `explicit_control_rule` | 3,948 | 100% one-hot | 控制规则的确定答案 |
| `weak_script_expert_v1` | 1,794（本语料 273） | 100% one-hot | 弱脚本专家的答案 |
| `defined_uniform_latent_worlds` | 258（本语料 201 + 57） | 100% **精确均分**（对全候选，或对「与观测一致的候选子集」） | 并列/潜在世界均分 |

判定：**`rule_counter`**（规则/控制参考标签，含并列均分），依据是卡面 "labels, not measured model confidence" + `target_basis` 逐行元数据。置信度**高**。

用户看到的 `{"0":0.0,"1":0.5,"2":0.5}` 与「平均最大概率恰好 0.500」由此解释：**不是「真不确定」，是「这几个选项并列最优，所以均分」**——文档明说它 "do not represent measured model uncertainty"。

**④ 是否可比**：**不可比**。它是「参考标签」，不是概率；把 0.5 当概率目标会教出「有并列就报 50%」的行为。

**⑤ 能否作为校准基准**：**不能**。它的 0.5 与 0.3333 表示并列，不表示结果发生的概率；不过它的 one-hot 行（4,221 条）作为**硬标签**是可用的（见 §5）。

---

### 3.3 jev-decisions（samatv256/jev-decisions-v1，cc-by-4.0）——两个抓取单元

**revision**：`c12aadf1f01c72616bfab0b02480e21806397669`；单元 A `general-clean-50k`（3,802 条）/ 单元 B `default` 浅窗口（207 条）。

**① probs 来自哪个字段（【代码】）**

| 配置 | 答案字段 | 映射 |
|---|---|---|
| `general-clean-50k` | `target_index`（整数下标）+ `answer_options[{type,label,description,schema_json}]` | `native_jev_decisions`（L1213–1267） |
| `default` | `candidates[{id,name,description}]` + `target{candidate_id,action_name}` | 同上，按 `candidate_id` 定位下标 |

两种形态最终都走 `point_mass`（L950–953）：`{选中:1.0, 其余:0.0}`，并打旗标 **`hard_label_to_point_mass`**。**来源侧没有任何概率字段。**

**② 上游怎么产生该字段（【文档】+【实测】，高）**

卡面：

> Jev Decisions v1 is a **derived, decision-oriented corpus built from public agent trajectory datasets**.
> | `target` | ... | **Single target action** and its arguments/label where represented. |
> Eligibility flags are authoritative: ... In particular, **do not train Choice on failed or unresolved trajectory actions.**
> general-clean-50k：Selection required supported Choice training labels, at least two distinct options, **one unambiguous target within the option set** ...
> The five Parquet shards contain the state, a fixed Choice question, finite answer options, and **the correct option index**.

URL：https://huggingface.co/datasets/samatv256/jev-decisions-v1/blob/c12aadf1f01c72616bfab0b02480e21806397669/README.md

我们抽到的 400 行 `default` 记录里，`training.supervision_evidence` 只有两个取值（【实测】）：

- `verified_demonstration`（128 条，来源 `nvidia/Nemotron-SFT-Agentic-v2`）——轨迹里**实际执行**的动作；
- `explicit_expected_action`（79 条，来源 `nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1`）——来源**显式给出**的期望动作。

上游 Nemotron Pivot 卡面（【文档】）：

> **Labeling Method** * [Synthetic] * Using `openai/gpt-oss-120b`, `Qwen/Qwen3-235B-A22B-Instruct-2507`
> 11 top-level fields per record: trajectory_id, responses_create_params, **expected_action**, ...

URL：https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1

**③ 语义分类**

**不是分布**。`distribution_semantics = none`；`probs` 里的 one-hot 是**我们**用 `point_mass` 造出来的（旗标 `hard_label_to_point_mass` 可机器判定）。标签本身的语义是**行为标签**：`verified_demonstration` = agent 当时真这么做了；`explicit_expected_action` = 上游 LLM 标注的期望动作。置信度高。

**④ 是否可比**：与任何来源的 `probs` 都不可比（它不是概率）；作为**分类标签**与其他硬标签同构。

**⑤ 能否作为校准基准**：作为**硬标签**可以（ECE/Brier 对着 realized label 算），但必须先承认标签的性质：**「当时做了什么」不等于「正确答案」**，而且上游卡面自己提醒 "do not train Choice on failed or unresolved trajectory actions"。所以是 **conditional 可用**：只有当评测口径定义成「预测上游标注的那个动作」时才成立。

---

### 3.4 systemone-lite-general（dwidlee/systemone-lite-general，mit）

**revision**：`c14eb7f7518f1d15cfcc27ac300c070a145d506a`；config `default`，split `train`，row_limit 1500。

**① probs 来自哪个字段（【代码】）**

| 项 | 值 |
|---|---|
| 原始字段 | `criteria_keys` / `criteria_values` / `label_alias` / `label_key`；**无任何概率字段**（实测首行 keys：task, state, instructions, criteria_keys, criteria_values, label_alias, label_key, meta） |
| 映射 | [convert.py](convert.py) `native_systemone_lite`（L1270–1297）：`label_alias` 在 `criteria_keys` 里的下标 → `point_mass` → 旗标 `hard_label_to_point_mass` |

**② 上游怎么产生该字段（【文档】，高）**

> Synthetic typed-decision rows for `systemone-lite` (letter-alias `choice` labels for causal LM SFT).
> Not affiliated with TypeSafe AI / Jev. **Labels are rule-based, not human prefs.**

URL：https://huggingface.co/datasets/dwidlee/systemone-lite-general/blob/c14eb7f7518f1d15cfcc27ac300c070a145d506a/README.md

【实测】行内 `meta` 是 JSON 串，形如 `{"gym":"debate_judge","pro_ev":0,"con_ev":2,"schema":"choice","hard":false,"n_options":2}`。生成器把判定用的证据量（pro_ev / con_ev / urgency …）直接放在 meta 里，说明标签是这些量的**确定性规则函数**。

**③ 语义分类**：`distribution_semantics = none`（硬标签，规则派生）。置信度高。若一定要给硬标签的**来源**分类，最接近 `rule_counter`；但本报告不为硬标签编造分布语义。

**④ 是否可比**：与概率目标不可比；作为硬标签可用。

**⑤ 能否作为校准基准**：**conditional**。理由：卡面只说 "rule-based"，**没有公布具体规则**，也**没有说标签是「无噪声」的**；行内 `meta.hard` 的含义未文档化（标为 unknown）。同族的 procedural（§3.6）在卡面上明确写了「labels are noise-free」，这个更强，所以如果要在规则标签里挑校准基准，优先用 procedural。

---

### 3.5 system-one-270m（kaivoss/system-one-270m-data，apache-2.0）

**revision**：`f31d5a3f3da828021c792edf5ab4b93cf60fe01b`；config `default`，split `train`，row_limit 1500（head）。

**① probs 来自哪个字段（【代码】）**

| 项 | 值 |
|---|---|
| 原始字段 | `target`（与 `letters` 对齐的 float 数组）；另有 `label` / `qtype` / `letters` / `entropy` / `score` / `ambiguity` / `ambiguity_requested` / `state_id` |
| 映射 | [convert.py](convert.py) `native_system_one_270m`（L1300–1361）：从 `prompt` 里正则抽 `<state>`、从 `Question:` / `Options:` 之间抽题干、用 `parse_lettered_options`（L828）解出候选文本；`target` 走 `prob_map` |
| 旗标 | `probs_normalized` 命中 **242 条条目**（源 target 之和 ≠ 1，被我们归一）；`uniform_target` 8 |

【实测】把 `entropy` 字段与 `target` 复算比对：**它是 target 的 Shannon 熵（以 2 为底，bits）**，误差在小数位舍入内。`score` 字段 = target 的**序号期望**（对 `score` 型问题是 0-based 档位期望，例：`[0.0001,0.0001,0.0001,0.9996,0.0001]` → 2.9995）。两者都是**由 target 派生的**，可当交叉校验。

**② 上游怎么产生该字段（【文档】+【上游代码】，高）**

卡面（固定 revision）：

> **Label** — an ensemble of permuted reads. Each read shuffles the option order and asks for a single letter, so the answer is one token and **`top_logprobs` returns a distribution**. Reads stop early at 3 when unanimous.
> The ensemble exists because gpt-oss reasons before answering and **cannot be told not to** — a post-reasoning distribution is effectively one-hot (measured: top option at `-0.0` with no competitor in the top 8). **The uncertainty lives in the variance across reads**, and shuffling also cancels letter-position bias.
> | Labels from logprobs | ~100% (6 rows fell back to hard voting) |
> **Labels are gpt-oss-20b's judgement, not human.** ... **No human validation.**

URL：https://huggingface.co/datasets/kaivoss/system-one-270m-data/blob/f31d5a3f3da828021c792edf5ab4b93cf60fe01b/README.md
（卡面给出代码仓库：https://github.com/Akicou/system-one-270m ）

上游生成脚本 `generate.py`（【文档】，高；核对的是 `main` 分支）：

- `_read_letter_logprobs`：`mass[letter] = mass.get(letter, 0.0) + math.exp(alt.logprob)`，然后 `dist = [mass.get(LETTERS[i], 0.0) + UNSEEN_FLOOR for i in range(n_options)]`，再 `/total`；
- **`UNSEEN_FLOOR = 1e-4`**（脚本 L63，注释：「Small but non-zero so a proper scoring rule stays finite」）；
- `_one_read`：`temperature=1.0`，`logprobs=True`，`top_logprobs=min(20, max(n, 2))`，并按排列把分布还原到原始候选顺序；
- `teacher_distribution`（docstring 原文）：
  > So **the ensemble mean is the target**, and shuffling doubles as the correction for letter-position bias.
  自适应：`min_votes=3`，`--votes` 默认 8，前 3 次一致就提前停；
- 落盘：`"target": json.dumps([round(p, 6) for p in dist])`。

URL：https://github.com/Akicou/system-one-270m/blob/main/generate.py

**③ 语义分类**

**`model_logits`**，依据：卡面 "top_logprobs returns a distribution" + 代码 `math.exp(alt.logprob)`；`temperature=1.0`，没有任何事后温度缩放，**因此不是 `temperature_softmax`**；也不是 `self_confidence`（不是模型口头自报，是词表 logprob）。置信度**高**。

但必须同时写清它到底是**哪个**模型分布的什么量（这正是用户怀疑的地方）：

- 单次读取的 logprob 分布**几乎必然是一 hot**（卡面：top option 在 `-0.0`）；
- 发布的 `target` 是 **3–8 次「打乱候选顺序重读」的均值**；
- 所以它实际度量的是「**换一种选项排列，教师会不会改主意**」——**自洽性/采样方差**，**不是**「教师 99.98% 有把握」。用户的直觉（"像被温度压到极端的分数，不是 99.98% 把握"）方向正确，但更精确的说法是：**极端值来自单次读取的一 hot 化（推理后分布），而 0.0001 那一档是构造伪影**。

**旁证（不是依据）**：实测 target 取值里 **0.0001 出现 2,825 次**，而 `UNSEEN_FLOOR = 1e-4` —— **这个数不是测出来的概率，是构造函数加的底**。因此「0.0001 表示 0.01% 把握」在这批数据上是错的。

**④ 是否可比**：与 procedural / open-jev 不可比（信念 vs 世界概率）；与 jev-distill `yuri_v3` 也不可比（一次并行输出 vs 多次排列读取的均值）。它自己内部可比（同一生成器、同一 teacher、同一温度）。

**⑤ 能否作为校准基准**：**不能**，只能当**软蒸馏目标**。理由：（a）卡面自认 "Labels are gpt-oss-20b's judgement"、"No human validation"；（b）它度量的是排列方差而不是正确概率；（c）0.0001 底与 6 位舍入是构造伪影。另外它还有 242 条**源 target 和不为 1**、需要归一的条目 —— 直接当概率用会引入 1e-6 量级的系统性偏差。

---

### 3.6 procedural-typed-decisions（tasksource/procedural-typed-decisions，apache-2.0）

**revision**：`609513a3faddf729123266efe9861456fe748f95`；config `all`，split `train`，row_limit 1500。

**① probs 来自哪个字段（【代码】）** —— 这段最关键，容易看错

`questions` 与 `answers` 是两个 JSON map（字符串），逐问对应。[convert.py](convert.py) `native_procedural`（L1364–1459）：

| question type | probs 的真正来源 | 代码位置 |
|---|---|---|
| `score` | `answer.probabilities[档位文本]`，按 `spec.criteria` 的档位顺序取 | L1395–1401 |
| `choice` | `answer.probabilities[criterion]` | L1420–1426 |
| `noul` | **不用 probabilities**（noul 行根本没有这个键），用标量 `answer.noul` → `[v, 1-v]` | L1427–1434 |

- 若 `probabilities` 全为 0（和为 0）→ `normalize_probs` 返回 None → **probs 被丢弃**，打旗标 `probs_dropped_zero_mass`，该 target 只剩 `answer`。本语料受影响 1,753 条条目。
- `answer.confidence` = 该分布的最大值（实测：`confidence: 0.6086956521739131` 对应 `{0.608696, 0.391304}`），可当一致性交叉校验。

**② 上游怎么产生该字段（【文档】，高）**

卡面（固定 revision）：

> **Procedurally generated decision problems.** Each row is one structured state ... with several typed questions over that same state ...
> **Every answer is computed exactly from the state by rules that the state itself spells out, so the labels are noise-free.**
> This is an independent dataset. It is **not an official TypeSafe Jev dataset** ...
> | `arithmetic` | ... `random_line_bulk`, `random_is_deposit`, `random_is_long` (**noul, exact probability k/n**) |
> | `partial_observation_calibration` | `incident_real` (**noul, exact Bayesian posterior**); 1 to 6 sensors |
> | `policy_under_uncertainty` | `access_allowed` (noul), `governing_policy` (choice), `requester_role` (choice); **exact posteriors** over a role known through history counts and reports of stated reliability |

URL：https://huggingface.co/datasets/tasksource/procedural-typed-decisions/blob/609513a3faddf729123266efe9861456fe748f95/README.md

**③ 语义分类：`rule_counter`，但请读成「规则精确算出的概率」，不是「数了数」**

这是**全语料唯一**一个「数字本身就是 P(结果 | 状态)」的来源。文档与实测**逐键闭合**：

| 问题键 | 出现在哪个 task | 文档说法 | 本语料 soft 条数 |
|---|---|---|---:|
| `incident_real` | partial_observation_calibration | exact Bayesian posterior | 109 |
| `access_allowed` | policy_under_uncertainty | exact posteriors | 78 |
| `governing_policy` | policy_under_uncertainty | exact posteriors | 85 |
| `requester_role` | policy_under_uncertainty | exact posteriors | 115 |
| `random_line_bulk` | arithmetic | exact probability k/n | 21 |
| `random_is_long` | arithmetic | exact probability k/n | 13 |
| `random_is_deposit` | arithmetic | exact probability k/n | 11 |
| **合计** | | | **432** |

**本语料里 procedural 的非退化 probs 只出现在这 7 个键上，且恰好 432 个** —— 与卡面「哪些问题是精确概率」完全一一对应。置信度**高**。这条对应关系是本报告能做「证据而非形态」判定的关键：判定依据是 `meta.native_task` + 问题键，不是 probs 的取值样子。

**旁证（不是依据）**：这 432 个值的小数确实是**有理数**——`0.666667 = 2/3`（分母 3）、`0.428571 = 3/7`、`0.272727 = 3/11`、`0.076923 = 1/13`、`0.287129/0.712871 = 29/101, 72/101`、`0.134328/0.865672 = 9/67, 58/67`……分母是 3/7/11/13/23/67/89/101/139 这类**组合计数**才会出现的数。**这印证了「算出来的」，但它不是判定依据**——用户从 `0.666667` 猜「像算出来的」是对的，依据在上面的卡面，不在小数本身。

**④ 是否可比**：**在 procedural 内部可比**（同一生成器、同一「状态决定答案」语义），**与所有教师/API 分布不可比**（世界概率 vs 信念）。与它的 one-hot 行也可比（那些是概率为 0/1 的确定性情形）。

**⑤ 能否作为校准基准：能（需限定条件）——这是全语料唯一的一个「能」。**

条件：

1. **只限这 432 条**（7 个 documented 精确概率键），其余 procedural target 是确定性 0/1，只能当硬标签；
2. **只在合成世界内**成立：概率是「这个世界发生了 A」的概率，不是「人类会怎么判」的概率；
3. 模型必须看到与生成器相同的 state（`state` 字段是完整 JSON/表格）；
4. 逐 task 分别报告，不要把 12 个 config 揉成一个 ECE（卡面的 kappa 表显示各 config 难度差极大）；
5. 卡面自称 noise-free，但**我们无法独立验证生成器实现**——这是「文档声明」而非「我们复核过」，置信度中高。

---

### 3.7 deepexi-fcs-v3（中文侧，Deepexi/openai-formate-function-calling-small，apache-2.0）

**revision**：`6d1dc02a2549104cc9cd2828c4b8647e9f994341`（来自 `D:\pol2-raw\zh-final\manifest.json`；v3.csv sha256 `4865ac94…1946a0`，24,608 行）。转换脚本在仓外：`D:\pol2-raw\zh-final\build_zh.py`（不走 convert.py）。

**① probs 来自哪个字段（【代码】）**

| 项 | 值 |
|---|---|
| 原始字段 | `systemPrompt` / `userPrompt` / `assistantResponse`（JSON 串） |
| 答案 | `build_zh.py::parse_response`（L107–115）：`json.loads(assistantResponse)["function"]` |
| target | `build_zh.py::to_item`（L514–561）：`"targets": {"next_step_candidate": {"answer": row["target"]}}` |
| probs | **没有。一个字都没有。** 7,872 个 target 全是 answer_only |

`meta.quality_flags` 里的 `target_from_source` 只表示「答案来自来源」，**不代表来源给了概率**——读报告时别被这个名字骗到。

**② 上游怎么产生该字段（【文档】= 没写，低）**

卡面只说字段与用途：

> 包含700+个阿里云OpenAPI的信息 ... **Functions信息与OpenAI functions calling 能力中，functions信息传入的格式保持一致**
> 字段：`systemPrompt`: 指令 / `userPrompt`: 用户输入 / `assistantResponse`: 输出
> 数据集用途 - 函数调用理解 ...

URL：https://huggingface.co/datasets/Deepexi/openai-formate-function-calling-small

**卡面完全没有说明 `assistantResponse` 是谁产生的**（模型生成？人工？脚本？哪个模型？），也没有说明答案是否经过校验。→ **`unknown`**，不猜。

**③ 语义分类**：`distribution_semantics = unknown`（不存在分布；且**答案的生成方式未知**）。置信度：对「没有分布」这件事是**高**（代码 + 实测），对「答案怎么来的」是 **unknown**。

**④ 是否可比**：无分布，不存在可比性问题。

**⑤ 能否作为校准基准**：**不能**。没有概率目标；答案生成过程无文档；`build_zh.py` 还专门过滤过「答案出现在输入里」的行（`target_name_in_state`），说明来源本身质量参差。作为**硬标签**训练可用（这是它现在的作用），但不要拿它做校准参照。

---

## 4. 横向：语义分类总表 + 可比性

### 4.1 语义分类总表（只统计**有 probs** 的 23,369 个）

| `distribution_semantics` | 条数 | 构成 | 证据等级 |
|---|---:|---|---|
| `model_logits` | 8,499 | jev-distill `yuri_v3` 5,378 + `yuri_v1` 1,621 + system-one-270m 1,500 | 高（类别）/ 中（Jev 的具体读数机制） |
| `rule_counter` | 9,382 | open-jev 4,479 + jev-distill `openjev_v2` 757 + procedural 4,146 | 高 |
| `none`（我们造的单点） | 5,488 | jev-decisions 4,009 + systemone-lite 1,479 | 高（旗标 `hard_label_to_point_mass`） |
| **`vote_share`** | **0** | — | — |
| **`human_annotation`** | **0** | — | — |
| **`self_confidence`** | **0** | — | — |
| **`temperature_softmax`** | **0** | — | — |
| **`unknown`** | **0**（有 probs 的）/ **7,872**（无分布且答案来源未知，见 §7） | deepexi-fcs-v3 | — |

**冻结语料里没有任何一个是人类投票比例、也没有任何一个是人工标注分布。** 全部 8 个抓取单元都是合成/派生。（唯一带真人 vote 的两个来源 `civil_comments`、`aegis1` **不在这份冻结语料里**，见附录 A。）

### 4.2 可比性矩阵（能否当同一个概率目标混训）

| 来源 | vs jev-distill `yuri_v3` | vs system-one-270m | vs procedural | vs open-jev | vs 硬标签源 |
|---|---|---|---|---|---|
| jev-distill `yuri_v3`（教师分布） | ✅ 同源 | ⚠️ 同类不同量 | ❌ 信念 vs 世界概率 | ❌ | ❌ |
| jev-distill `yuri_v1`（常量 0.5） | ❌ 常量 | ❌ | ❌ | ❌ | ❌ |
| jev-distill `openjev_v2`（规则标签） | ❌ | ❌ | ⚠️ 同为规则但生成器不同 | ✅ 同源 | ⚠️ 它是 one-hot |
| system-one-270m（logprob 集合均值） | ⚠️ | ✅ 同源 | ❌ | ❌ | ❌ |
| procedural（精确后验） | ❌ | ❌ | ✅ 同源 | ⚠️ | ⚠️ |
| open-jev（并列均分/控制规则） | ❌ | ❌ | ⚠️ | ✅ 同源 | ⚠️ |
| jev-decisions / systemone-lite（硬标签） | ❌ | ❌ | ❌ | ❌ | ✅（同为单点） |

读法：**只有「✅ 同源」的格子能直接当同一个目标混训**。任何跨列混训，模型学到的都是**混合平均**，而这个平均值不对应任何真实量——这是本报告支持用户判断的核心结论。

**特别提醒**：`jev-distill-v3` 一个 slug 内部就横跨 ✅ 与 ❌ 两类格子。按 slug 做 data mixing / 配比 / 分组统计都会出错，**必须下钻到 `meta.native_source`**。

---

## 5. 校准可用性判定（全语料，不只 29%）

先把「校准」拆成两件不同的事，否则结论会打架：

- **A. 分布校准（distributional calibration）**：参照量是一个**概率**，可以算 NLL / Brier / reliability diagram。要求参照量是「结果发生的概率」。
- **B. 置信度校准（confidence calibration / ECE）**：参照量只需要一个**正确答案**，把模型置信度分箱对比准确率即可。硬标签就够用。

| 来源 | 桶 | n | A：分布校准 | B：ECE 用硬标签 | 条件 |
|---|---|---:|---|---|---|
| procedural | 精确后验/k–n（7 键） | 432 | ✅ **能** | ✅ | 仅合成世界内；逐 task 报告 |
| procedural | 其余（0/1 确定性） | 4,259 | ❌（是 0/1，无梯度） | ✅ | 答案由规则精确算出 |
| system-one-270m | soft | 1,492 | ❌ | ✅（argmax 为标签） | 标签是 gpt-oss-20b 判断 |
| jev-distill `yuri_v3` | soft | 5,364 | ❌ | ✅ | 标签是 Jev 1.13 的 argmax |
| jev-distill `openjev_v2` | 全部 | 757 | ❌ | ✅ | 规则标签 |
| open-jev | 全部 | 4,479 | ❌ | ⚠️ one-hot 行可用；并列均分行不能当唯一答案 | 卡面："labels, not measured confidence" |
| jev-decisions | 全部 | 4,009 | ❌ | ⚠️ 行为标签，非「正确答案」 | `verified_demonstration` / `expected_action` |
| systemone-lite | 全部 | 1,479 | ❌ | ✅ | 规则标签，规则未公开 |
| jev-distill `yuri_v1` | 全部 | 1,621 | ❌ | ❌（常量） | **建议直接从任何目标里剔除** |
| deepexi-fcs-v3 | 全部 | 7,872 | ❌ | ⚠️ 答案来源未知 | **unknown** |

**结论**：

1. **能被当作「概率参照」的只有 432 条**（procedural 的 7 个 documented 键），占全语料 1.4%、占「29%」的 4.7%。
2. 其余 6,856 条教师分布（`model_logits`）= **软蒸馏目标**，不是校准参照。用它们测校准，测的是「学生与教师的一致性」。
3. 1,962 条（uniform 1,730 + 并列均分 232）**信息量为 0 或仅表示并列**，任何训练/评测口径都应先剔除。
4. 若只需要 ECE，硬标签路线可用面大得多（约 2.4 万条），但**必须逐来源标注标签的可信度**（规则精确算出 / 教师 argmax / 行为标签 / 来源未知），否则 ECE 的分子分母里混着四种不同的「正确」。

---

## 6. `target_type` 回填提案（可被脚本直接执行）

### 6.1 设计原则

1. **判定依据是来源证据**：`source.slug` + `meta.native_source` + `meta.native_task` + 问题键 + 转换器写入的 `meta.quality_flags`。这些都是**转换时由代码按来源字段写的**，不是概率形状。
2. **数值形态只允许出现在两处**：(a) 作为 `target_type` 的**降级候选**（把一个向量判为「无信息」，绝不判为某个语义）；(b) 作为证据里的**旁证字段**，单独存放、可被消费者忽略。凡是用到形态的判定，`target_type_basis` 必须写成 `shape` 而不是 `source`。
3. **不改数据**：落盘为**旁挂文件**（sidecar），与原语料按 `(item_id, question_key)` 连接。
4. 一个来源可以被多条规则命中，**priority 数字大的覆盖小的**。

### 6.2 字段定义

| 字段 | 类型 / 取值域 | 说明 |
|---|---|---|
| `target_type` | `hard_label` \| `soft_distribution` \| `uninformative_uniform` \| `answer_only` | 四选一，每条 target 必填 |
| `distribution_semantics` | `vote_share` \| `model_logits` \| `temperature_softmax` \| `self_confidence` \| `rule_counter` \| `human_annotation` \| `unknown` \| `none` | **`none` 是本提案对给定取值域的显式扩展**：没有 probs 的 target 不存在分布语义，用 `unknown` 会与「有分布但查不清」混淆 |
| `target_type_basis` | `source` \| `shape` | 该判定是「来源证据」还是「形态候选」 |
| `semantics_confidence` | `high` \| `medium` \| `low` \| `unknown` | 语义判定的置信度 |
| `calibration_role` | `reference_probability` \| `soft_target_only` \| `label_only` | 见 §5 |
| `label_trust` | `rule_exact` \| `teacher_argmax` \| `behavioral` \| `unknown` | 答案本身可信度，用于 ECE 分层 |
| `mechanism_unknown` | bool | 语义类别有文档、但**具体数值读数机制**无文档（目前只有 jev-distill `yuri_v3` / `yuri_v1` 为 true） |
| `provenance_ref` | string[] | 命中的证据条目 id（对应 6.4 的证据表） |
| `shape_note` | string \| null | **仅旁证**，例如「源向量全等值」「整条子流只有一个取值」。消费者可忽略 |

### 6.3 规则表（按 source 证据判定，可直接翻译成代码）

| # | 命中条件（全部是来源/代码证据） | `target_type` | `distribution_semantics` | `calibration_role` | `label_trust` | 条数 | 依据 |
|---|---|---|---:|---:|---|---:|---|
| R1 | `source.slug ∈ {jev-decisions-general-50k, jev-decisions-strata}`（旗标 `hard_label_to_point_mass`） | `hard_label` | `none` | `label_only` | `behavioral` | 4,009 | E1, E2 |
| R2 | `source.slug = systemone-lite-general`（旗标 `hard_label_to_point_mass`） | `hard_label` | `none` | `label_only` | `rule_exact` | 1,479 | E3 |
| R3 | `source.slug = deepexi-fcs-v3`（无 probs） | `answer_only` | `unknown` | `label_only` | `unknown` | 7,872 | E4 |
| R4 | `source.slug = procedural-typed-decisions` 且无 probs（旗标 `probs_dropped_zero_mass`） | `answer_only` | `none` | `label_only` | `rule_exact` | 545 | E5 |
| R5 | `source.slug = procedural-typed-decisions` 且 `(meta.native_task, question.key)` ∈ 7 个 documented 精确概率键 | `soft_distribution` | `rule_counter` | `reference_probability` | `rule_exact` | **432** | E5 |
| R6 | `source.slug = procedural-typed-decisions` 其余 | `soft_distribution` | `rule_counter` | `label_only` | `rule_exact` | 3,714 | E5 |
| R7 | `source.slug = open-jev` | `soft_distribution` | `rule_counter` | `label_only` | `rule_exact` | 4,479 | E6, E7, E8 |
| R8 | `source.slug = jev-distill-v3` 且 `meta.native_source = openjev_v2` | `soft_distribution` | `rule_counter` | `label_only` | `rule_exact` | 757 | E9 |
| R9 | `source.slug = jev-distill-v3` 且 `meta.native_source = yuri_v3` | `soft_distribution` | `model_logits` | `soft_target_only` | `teacher_argmax` | 5,378 | E9, E10 |
| **R10** | `source.slug = jev-distill-v3` 且 `meta.native_source = yuri_v1` | **`uninformative_uniform`** | `model_logits` | `soft_target_only` | `teacher_argmax` | **1,621** | E9 + E11 |
| R11 | `source.slug = system-one-270m` | `soft_distribution` | `model_logits` | `soft_target_only` | `teacher_argmax` | 1,500 | E12, E13 |
| R12 | 兜底：全候选等值（`max(probs) - min(probs) < 1e-9`）且未被 R10/R13 命中 | `uninformative_uniform` | 继承上一行语义 | `label_only` | 继承 | 109 | **形态候选**，`target_type_basis = shape` |
| R13 | 兜底：非负权重在**正权重子集**上等值（并列均分） | `uninformative_uniform` | 继承 | `label_only` | 继承 | 232 | **形态候选**，`target_type_basis = shape`（open-jev 与 `openjev_v2` 的并列行） |

**合计自检**：`answer_only` 8,417（R3+R4）；`hard_label` 5,488（R1+R2）；`uninformative_uniform` 1,962（R10 1,621 + R12 109 + R13 232）；`soft_distribution` 15,919；总计 **31,786** ✅。

### 6.4 证据条目（规则表引用）

| id | 证据 |
|---|---|
| **E1** | jev-decisions 卡面：`target` = "Single target action"；"derived ... from public agent trajectory datasets"；"do not train Choice on failed or unresolved trajectory actions"。URL：https://huggingface.co/datasets/samatv256/jev-decisions-v1/blob/c12aadf1f01c72616bfab0b02480e21806397669/README.md |
| **E2** | 行内 `training.supervision_evidence` ∈ {`verified_demonstration`, `explicit_expected_action`}；Nemotron Pivot 卡面 `expected_action` 字段 + "Labeling Method [Synthetic]"。URL：https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1 |
| **E3** | systemone-lite 卡面："Labels are rule-based, not human prefs."；字段表无概率列（实测原始行 keys 已核对）。URL：https://huggingface.co/datasets/dwidlee/systemone-lite-general/blob/c14eb7f7518f1d15cfcc27ac300c070a145d506a/README.md |
| **E4** | Deepexi 卡面只描述三字段，未说明 `assistantResponse` 的产生方式；`build_zh.py::to_item` 只写 `answer`。URL：https://huggingface.co/datasets/Deepexi/openai-formate-function-calling-small |
| **E5** | procedural 卡面："Every answer is computed exactly from the state by rules ... noise-free"；7 个 documented 精确概率键（exact Bayesian posterior / exact posteriors / exact probability k/n）。URL：https://huggingface.co/datasets/tasksource/procedural-typed-decisions/blob/609513a3faddf729123266efe9861456fe748f95/README.md |
| **E6** | open-jev 卡面："These are labels, not measured model confidence."；"not official TypeSafe/Jev training data, model predictions"。URL：https://huggingface.co/datasets/ZefanCai/Open-Jev/blob/c67699e13d0ae25e35b77165a4b6b079bedc8aba/README.md |
| **E7** | `provenance/component-artifacts/case-customer/target-statistics.json`：`"definition": "Hard: one-hot PMF..."`（choice 900 hard/100 soft …）。URL：https://huggingface.co/datasets/ZefanCai/Open-Jev/tree/c67699e13d0ae25e35b77165a4b6b079bedc8aba/provenance |
| **E8** | `cards/ir-control-v1.md`："Choice targets are uniform over equally best passages; they do not ... represent measured model uncertainty."；`doom-basic-v1/manifest.json` `"expert": "momentum_tracking_weak_script_v1"`。URL：https://huggingface.co/datasets/ZefanCai/Open-Jev/tree/c67699e13d0ae25e35b77165a4b6b079bedc8aba/cards |
| **E9** | jev-distill-v3 卡面三条流的 origin 表（yuri_v3 = Jev 1.13 蒸馏；yuri_v1 = 32B teacher；openjev_v2 = Open-Jev 转出）。URL：https://huggingface.co/datasets/SargeDev/jev-distill-corpus-v3/blob/fc99c6357a9f89f7512c4a987314352addead049/README.md |
| **E10** | TypeSafe 博客："All answers are accompanied with calibrated probabilities"；"Jev outputs all probabilities in parallel"。URL：https://typesafe.ai/blog/introducing-system-one-models-and-jev |
| **E11** | 实测（**旁证**）：`yuri_v1` 原始 1,661 行 target 只有 1 个取值 `[0.5, 0.5]`。**常量向量不可能携带方向信息**，故判为无信息；"为什么是常量"本身仍未知。 |
| **E12** | system-one-270m 卡面："top_logprobs returns a distribution"；"the ensemble mean is the target"；"Labels are gpt-oss-20b's judgement"；"Labels from logprobs ~100%"。URL：https://huggingface.co/datasets/kaivoss/system-one-270m-data/blob/f31d5a3f3da828021c792edf5ab4b93cf60fe01b/README.md |
| **E13** | 上游代码 `generate.py`：`math.exp(alt.logprob)`、`UNSEEN_FLOOR = 1e-4`、`temperature=1.0`、`min_votes=3`、`round(p, 6)`。URL：https://github.com/Akicou/system-one-270m/blob/main/generate.py |

### 6.5 落盘形态（旁挂，不动数据）

建议后续任务写 `datasets/general/data/target-types.jsonl`（**本任务不创建**，避免本轮改数据），每行一条 target 标注：

```json
{"item_id":"db-jev-distill-v3-1a2b3c4d","question_key":"Rate claim reliability for this scenario on a 0-5 scale.",
 "target_type":"soft_distribution","distribution_semantics":"model_logits",
 "target_type_basis":"source","semantics_confidence":"medium","mechanism_unknown":true,
 "calibration_role":"soft_target_only","label_trust":"teacher_argmax",
 "provenance_ref":["E9","E10"],"shape_note":null}
```

生成器骨架（关键点：**先判 slug/子流，再判问题键，形态只在最后兜底**）：

```python
RULES = [  # (priority, predicate, payload)
    (10, lambda it, q: it["source"]["slug"] in {"jev-decisions-general-50k", "jev-decisions-strata"},
     dict(target_type="hard_label", distribution_semantics="none",
          calibration_role="label_only", label_trust="behavioral", refs=["E1", "E2"])),
    (10, lambda it, q: it["source"]["slug"] == "systemone-lite-general",
     dict(target_type="hard_label", distribution_semantics="none",
          calibration_role="label_only", label_trust="rule_exact", refs=["E3"])),
    (10, lambda it, q: it["source"]["slug"] == "deepexi-fcs-v3",
     dict(target_type="answer_only", distribution_semantics="unknown",
          calibration_role="label_only", label_trust="unknown", refs=["E4"])),
    (20, lambda it, q: it["source"]["slug"] == "procedural-typed-decisions"
        and q["key"] in EXACT_PROB_KEYS and q["task"] in EXACT_PROB_TASKS,
     dict(target_type="soft_distribution", distribution_semantics="rule_counter",
          calibration_role="reference_probability", label_trust="rule_exact", refs=["E5"])),
    (15, lambda it, q: it["source"]["slug"] == "procedural-typed-decisions",
     dict(target_type="soft_distribution", distribution_semantics="rule_counter",
          calibration_role="label_only", label_trust="rule_exact", refs=["E5"])),
    (10, lambda it, q: it["source"]["slug"] == "open-jev",
     dict(target_type="soft_distribution", distribution_semantics="rule_counter",
          calibration_role="label_only", label_trust="rule_exact", refs=["E6", "E7", "E8"])),
    (20, lambda it, q: it["source"]["slug"] == "jev-distill-v3"
        and it["meta"].get("native_source") == "yuri_v1",
     dict(target_type="uninformative_uniform", distribution_semantics="model_logits",
          calibration_role="soft_target_only", label_trust="teacher_argmax", refs=["E9", "E11"])),
    (10, lambda it, q: it["source"]["slug"] == "jev-distill-v3"
        and it["meta"].get("native_source") == "openjev_v2",
     dict(target_type="soft_distribution", distribution_semantics="rule_counter",
          calibration_role="label_only", label_trust="rule_exact", refs=["E9"])),
    (10, lambda it, q: it["source"]["slug"] == "jev-distill-v3"
        and it["meta"].get("native_source") == "yuri_v3",
     dict(target_type="soft_distribution", distribution_semantics="model_logits",
          calibration_role="soft_target_only", label_trust="teacher_argmax",
          mechanism_unknown=True, refs=["E9", "E10"])),
    (10, lambda it, q: it["source"]["slug"] == "system-one-270m",
     dict(target_type="soft_distribution", distribution_semantics="model_logits",
          calibration_role="soft_target_only", label_trust="teacher_argmax", refs=["E12", "E13"])),
]
# 形态只在最后兜底；命中时 target_type_basis="shape"，且只允许把 target_type 改成
# uninformative_uniform，不允许改 distribution_semantics。
SHAPE_FALLBACK = dict(target_type="uninformative_uniform", target_type_basis="shape")
```

**未命中任何规则的 target 一律写 `unknown` 并在报告里计数**——本提案的规则表覆盖全部 31,786 条（自检见 §6.3），所以实际未命中数应为 0；若脚本跑出非 0，说明映射已经变了，应停下来重查而不是猜。

---

## 7. unknown 清单（不许猜的地方）

| # | unknown | 涉及 target | 为什么查不清 | 对使用的影响 |
|---|---|---:|---|---|
| U1 | **Jev 1.13 那串分布的具体读数机制**（并行 head 的 softmax？还是先算分再归一？2 位小数是 API 还是导出时舍入？） | 6,999（jev-distill `yuri_v3` 5,378 + `yuri_v1` 1,621 的**类**已知、**机制**未知） | 卡面只说 "full distributions per question"；TypeSafe 博客只说"并行输出概率"，没有 API 输出文档 | 语义按 `model_logits` 用没问题；但**不能声称它是 logits**（可能是校准头输出），`mechanism_unknown=true` |
| U2 | **`yuri_v1` 为什么整条流恒定 `[0.5, 0.5]`**（教师真的每次都 50/50？还是蒸馏管线写死了默认值？） | 1,621 | 上游卡面没有说明；上游没有发布生成脚本 | 无论如何**无信息**，应剔除；但「是教师退化还是管线 bug」未知 |
| U3 | **deepexi `assistantResponse` 是谁产生的** | 7,872 | 卡面完全没提；没有生成脚本 | 只能当硬标签训练，不能当校准参照 |
| U4 | **systemone-lite 的具体判定规则**（`meta.hard` 是什么？标签是否无噪声？） | 1,479 | 卡面只说 rule-based，未公开规则 | ECE 用它时要标注 `label_trust=rule_exact` 但置信度只能算中 |
| U5 | **open-jev 的 `defined_uniform_latent_worlds` 具体如何枚举潜在世界** | 258（本语料 201 + 57） | 仓库里有 `target_basis` 标注，但没有该 basis 的算法文档 | 「并列均分」这个**语义**是明确的，不影响判定 |
| U6 | **`jev-decisions` 的 `labels.source_pass_rate` 等量与新目标的关系** | 4,009（本语料 target 侧未使用） | 卡面只说 "These quantities are not interchangeable" | 本语料没有用这些列，不影响；但若要扩样需重查 |

**标为 `distribution_semantics = unknown` 的 target 数：7,872（deepexi-fcs-v3，全部）。**
**标为 `mechanism_unknown = true` 的：6,999（`yuri_v3` + `yuri_v1`）。**
其余来源的语义分类均有可点击的上游证据，无 unknown。

---

## 附录 A：退役模板线（**不在冻结语料内**，仅供对照）

[SOURCES.md](SOURCES.md) §2 说明 `items.jsonl`（37,124 条 / 19,717 target）是**已退役的模板线**，不在 `items.final.jsonl.gz` 里。但它包含**整个项目里唯二的人类群体标注分布**，对「校准参照稀缺」这件事有参考价值，所以列在这里：

| slug | target 数 | 形态 | probs 来源（[convert.py](convert.py)） | 语义 |
|---|---:|---|---|---|
| civil-comments | 2,991 | soft 599 / one-hot 2,355 / uniform 37 | `convert_civil_comments` L546–582：`toxicity` 标注者比例 → `{yes: p, no: 1-p}`，旗标 `probs_from_annotator_fraction` | **`vote_share`（真人多标注者比例）** |
| aegis1 | 1,477 | soft 109 / one-hot 1,367 / uniform 1 | `convert_aegis` L584–656：`labels_0..labels_4` 非空标注计票 → 归一，旗标 `probs_from_annotator_votes` | **`vote_share`（真人多标注者投票）** |
| moral-stories / aegis2 / jev-decisions / systemone-lite | 6,000 / 2,232 / 2,041 / 1,479 | 全 answer_only | 硬标签不伪装成概率（旗标 `target_is_hard_label:no_probs`） | `none` |

这 4,468 个 `vote_share` target **不属于本轮结论范围**（不在冻结语料里，也没有进任何训练/评测划分）。若后续要补「人类投票比例」这一档校准参照，它们是仓内唯一现成的候选；但需要先解决许可与「标注口径与我们无关」的问题（见 [SOURCES.md](SOURCES.md) §3 对传统数据集的处理原则）。

---

## 附录 B：复算方式（只读）

本报告所有计数都可由下面的只读过程复现（不写任何仓内文件）：

1. **全量形态**：读 `D:\pol2-raw\general-private\data\items.final.jsonl.gz`，对每个 `targets[key]` 判：无 `probs` → answer_only；全等值 → uniform；恰一个非零且 =1 → 伪 one-hot；否则 soft。按 `source.slug` 与 `meta.native_source` 双键分组。
2. **语义闭合**：把每个 slug 的 `meta.quality_flags`（`hard_label_to_point_mass` / `probs_normalized` / `probs_dropped_zero_mass` / `uniform_target`）与规则表 §6.3 对照。
3. **上游复核**：用固定 revision 的 resolve 直链下载（**不要用 datasets-server，它不遵守 revision 参数**）：`https://huggingface.co/datasets/<id>/resolve/<sha>/README.md`。本报告引用的 6 份卡面均以该方式在固定 sha 上核对。
4. **上游代码**：`raw.githubusercontent.com/Akicou/system-one-270m/main/generate.py`（`UNSEEN_FLOOR=1e-4`、`math.exp(alt.logprob)`、`temperature=1.0`、ensemble 均值）。

验收命令（仓根执行）：

```sh
uv run --no-project --offline python tools/check.py
```

---

## 附：修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-06 | 首版。覆盖冻结语料全部 8 个抓取单元；给出 31,786 个 target 的逐来源溯源、语义判定、可比性与校准可用性；附 `target_type` 回填提案（覆盖 100%）。 |
