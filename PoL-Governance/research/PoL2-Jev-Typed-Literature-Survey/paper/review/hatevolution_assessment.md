# 评估：*Hatevolution: What Static Benchmarks Don't Tell Us*（arXiv:2506.12148）

- 作者：Chiara Di Bonaventura, Barbara McGillivray, Yulan He, Albert Meroño-Peñuela（King's College London；第一作者另属 Imperial College London）
- 版本：arXiv v1，2025-06-13 提交，主类 cs.CL；DOI 10.48550/arXiv.2506.12148。arXiv 摘要页**没有** journal-ref 字段，正式发表的会议或期刊未核实（DBLP 查询失败），因此下文按预印本引用。
- 全文：13 页 PDF，已用 pymupdf 抽取并保存到 scratchpad 下的 `hatevolution.txt`（58,463 字符，含附录 A–E）。
- 说明：以下内容只报告论文本身写了什么，数字原样照抄。标 **【推断】** 的是本评估自己的判断或计算，原文没有这样写。

---

## 1. 研究设计摘要

### 1.1 研究问题
原文的研究问题是 “how does static hate speech benchmarking correlate with evolving language?”。作者的论点是：静态基准“grounded to the specific timestamp”，因此可能高估模型的安全性。

### 1.2 数据集（Table 2）
| 数据集 | 规模 | 时间信息 | 用途 |
|---|---|---|---|
| Singapore Online Attacks（Haber et al. 2023，英文版） | 3000 | 2017–2022 | 实验 1 |
| NeoBench（Zheng et al. 2024）中的 Reddit 样本，作者扩展为仇恨检测任务 | 682（341 对） | 2020–2023 | 实验 2 |
| HateXplain | 1924 | 无 | 静态基准 |
| Implicit Hate Corpus | 2149 | 无 | 静态基准 |
| HateCheck | 3729 | 无 | 静态基准 |
| Dynabench | 4120 | 无 | 静态基准 |

- 静态基准都用测试集（App. A）。
- 四个静态基准的选择理由：HateXplain 对应 offensiveness，Implicit Hate 对应 expressiveness，HateCheck 与实验 2 的“只换一个词”的配对结构相似，Dynabench 是“唯一的动态（多轮对抗）基准”。
- 所有数据只有英文。

### 1.3 实验 1：Time-Sensitive Shifts（时间敏感漂移）
- **操作化方式**：不是训练集和测试集的时间切分。所有模型都是 zero-shot，直接在带时间戳的 Reddit 帖子上，**按年份分组评估**。原数据覆盖 2011–2022，但 2017 年以前数据不足，所以只分析 2017–2022 六个年份。
- 实验 1 研究的是语义、话题和极性变化交织在一起的总体效应。原文举的例子：“gammon” 从“火腿”变成政治侮辱语；部分针对亚裔的词在新冠期间变得更具冒犯性；被夺回使用的蔑称（reclaimed slurs）。作者明确说**不拆分**这几类变化（“we do not attempt to do so”）。
- **指标**：time-sensitive macro F1 = (1/T) Σ_{t=1..T} F1_t，其中 F1_t 是第 t 年的 macro-F1。Table 3 分别给出每年 hateful 和 non-hateful 两个标签的 F1，最后一列是 Mean。附录 Table A1 给出两个标签 F1 在各年之间的标准差。
- **没有**新出现蔑称的检测，也**没有**反事实测试集；这两类内容在实验 2。

### 1.4 实验 2：Vocabulary Expansion（新词）
- **数据来源**：NeoBench 的句对 (s1, s2)。s2 是把 s1 中的一个目标词替换成新词，并保持词性和含义不变。新词收集于 2020–2023，分三类：lexical（如 “long covid”）、morphological（如 “doomscrolling”）、semantic（如 “ice” 指燃油车）。
- **标注**：三位作者（AI 研究者）把 NeoBench 的 Reddit 样本标为 hateful 或 non-hateful，取多数票作为金标；平均 Cohen's κ = 0.67。结果是 341 个 s1 配 341 个反事实 s2。原文没有明确说是否对 s2 单独标注【推断：反事实设计的前提是 s2 的标签与 s1 相同】。
- **操作化方式**：反事实不变性（counterfactual invariance，Veitch et al. 2021），拆成两个指标：
  - label flip = (1/N) Σ 1(ŷ_i(s1) ≠ ŷ_i(s2))
  - hallucination = (1/N) Σ 1(v(s2,i)=1 ∧ v(s1,i)=0)，v(·)=1 表示模型没有按指令作答
  
  另外也报告 macro F1。
- **数据污染检查**：按新词出现年份分别计算 label flip 和 hallucination（Table A2/A3）。结果各年大体稳定，作者据此说 “no evidence” 存在污染，但同时承认污染无法完全排除。

### 1.5 模型（共 20 个，另加 1 个基线；Table 1、App. A）
- **20 个模型**：
  - FLAN-Alpaca base / large / xl（3 个）
  - FLAN-T5 small / base / large / xl（4 个）
  - mT0 small / base / large / xl（4 个）
  - RoBERTa-dyna-r1/r2/r3/r4（4 个，在 Dynabench 连续四轮上微调）
  - GPT-3.5-turbo、GPT-4o、OpenAI Moderation API（text-moderation-latest）、Perspective API、DeepSeek LLM-7b（5 个）
- **基线**：TimeLMs 最新几个版本经仇恨检测微调后的平均分，不计入 20 个模型。
- **设置**：全部 zero-shot，使用默认参数。提示词沿用 Plaza-del-arco et al. (2023)：“Classify the input text as ‘respectful’ or ‘toxic’.”。xl 规模的模型用 8-bit 量化加载。
- **非预期输出的处理**：不按指令作答的输出在计算 macro F1 时**直接剔除**。
- **两个 API 的二值化**：原文**没有说明** Moderation API 和 Perspective API 用什么阈值把分数转成二值标签。

### 1.6 “静态与时间敏感评估错位”如何度量
- **统计量**：Spearman 秩相关 ρ，比较的是**模型排名**。对每一对“静态基准 × 时间敏感实验”（4 × 2 = 8 对）分别计算。
- **数据来源**：静态排名来自 Table A7–A10 的 macro F1；时间敏感排名来自 Table 3 和 Table 4。实验 2 的 Table 4 有 label flip、hallucination、macro F1 三个指标，原文**没有说明用哪一个**来排名。
- **置信区间**：用 Fisher z 变换，α = 0.10（90% CI），n = 20。
- **静态基准之间的对照**：静态基准两两之间也算了 Spearman 相关（Table A11）作为对照。

### 1.7 主要定量结果（原文数字）

**实验 1**
- 原文说各模型逐年 F1 变化“significant”，但没有给出显著性检验。
- 长期趋势：多数模型对 hateful 的检测随年份变差，对 non-hateful 的检测变好。例：mT0-large 2017 年 hateful F1 为 .5045、non-hateful 为 .5455；2022 年为 .3811 和 .6290。
- GPT-4o 的均值最高，为 .7083；其 hateful F1 从 2017 年的 .7619 降到 2022 年的 .6032。
- TimeLMs 基线各年更稳定，但均值只有 .3722，与小型 LLM 和 DeepSeek（.3740）相近。
- 动态对抗训练没有带来帮助：RoBERTa-dyna-r1 均值 .5976，高于 r2 的 .5526、r3 的 .5638、r4 的 .5922。
- 对非对抗训练的模型，规模越大，均值越高。
- 作者的解释（属于作者推测）：仇恨分类器存在词汇过拟合，依赖旧的词义联想，例如把 “gammon” 理解为火腿。

**实验 2**
- 20 个模型中有 6 个的 label flip 超过 10%：FLAN-Alpaca-xl 14.14%、FLAN-T5-base 11.24%、FLAN-T5-large 15.96%、FLAN-T5-xl 13.99%、mT0-large 14.12%、GPT-3.5-turbo 14.93%。GPT-4o 为 9.44%，比 RoBERTa-dyna-r2/3/4（5.88%、5.00%、6.47%）差。
- label flip 为 0 的几个模型（FLAN-T5-small、mT0-small、Moderation API、DeepSeek）对所有文本输出同一个标签，或者几乎不按指令作答。排除这些模型后，Perspective API 最好：label flip 2.94%，macro F1 .7067。
- 模型越大，hallucination 越低，但 label flip 不一定改善。例：FLAN-Alpaca-xl 的 hallucination 为 0%，large 为 10.88%；但 xl 的 label flip 为 14.14%，large 为 3.98%。
- 按新词类型的平均值：
  - label flip：morphological 6.54%、lexical 6.40%、semantic 5.34%
  - hallucination：lexical 2.12%、morphological 1.58%、semantic 1.82%
- 更宽口径的 hallucination（s1 或 s2 任一句不按指令作答，Table A6）：14 个生成式模型中有 5 个超过 10%；DeepSeek LLM-7b 高达 98.82%。

**错位（Table 5，Spearman ρ 及 90% CI）**

| 静态基准 | 与实验 1 | 与实验 2 |
|---|---|---|
| HateCheck | −0.2662（−0.586, 0.126） | −0.0707（−0.438, 0.317） |
| Dynabench | −0.1549（−0.504, 0.238） | −0.3053（−0.613, 0.083） |
| HateXplain | −0.2541（−0.578, 0.138） | −0.1865（−0.528, 0.207） |
| Implicit Hate | −0.2812（−0.597, 0.110） | 0.1909（−0.203, 0.532） |

- 静态基准两两之间的平均 ρ = 0.36，即 (0.3865+0.2361+0.3203+0.8647+0.2421+0.0917)/6。最高是 Dynabench–HateXplain 的 0.8647（CI 0.722, 0.937），最低是 HateXplain–Implicit Hate 的 0.0917。
- 原文结论：“clear misalignment”，与实验 1 “overall… negative correlation”，与实验 2 “on average negative or close to zero”。
- 【推断，本评估计算】实验 1 列四个 ρ 的平均约为 −0.239，实验 2 列约为 −0.093。**全部 8 个 90% CI 都包含 0**。静态基准之间的 6 个 CI 只有 2 个不含 0（HateCheck–Dynabench 0.009–0.668，Dynabench–HateXplain 0.722–0.937）。所以，说“没有正相关的证据”是站得住的；说“显著负相关”则不成立。附录 E 自己也只写到 “negative or negligible… skewed tendency toward negative”，并承认样本量会影响估计。

### 1.8 作者自述的局限（§6 及 App. E）
1. 只用英文；多语言留待以后。
2. 仇恨数据集本身带有标注主观性造成的偏差和噪声。
3. 没有拆分极性、话题等漂移子类。
4. 社交媒体数据难以持续采集，会妨碍以后重复实验 1；实验 2 可以改用 OED、Wiktionary、Urban Dictionary 等词典资源。
5. 附录 E 补充：n = 20 时估计不够精确，更大的样本才能给出更精确的评估。

---

## 2. 方法可借鉴性

### (a) 作为本文的论据点（背景文献，不属于 corpus）
这篇论文早于 Jev，也没有测试任何 typed 模型，所以只能放进 `background.bib`，不计入编码统计。建议放在三处：

1. **§4 G4 “Calibration is local.” 段末尾或 “Relation to prior work”。** 现有句子是 “This is the general pattern of calibration under shift~\cite{ovadia2019trust}”。可以加半句，说明对仇恨语言而言，漂移不只是理论风险，静态基准上的排名不能预测随时间变化的表现。它支持的论点是：risk-controlled thresholds 依赖的可交换性（exchangeability）在仇恨语言上会因语言演化而被破坏。§4 G6 “Relation to prior work” 和 §6 “Trade-offs” 中 “bound error under benign drift” 一句也可以用它作为 drift 的具体证据。
2. **§4 G1 “Relation to prior work”。** 现有句子是 “good ranking, poorly transferable thresholds and failures concentrated in sub-types~\cite{rottger2021hatecheck}”。可以补一句：静态基准上的高分不能转移到随时间演化的仇恨语言上。
3. **§7 Open problems 中 “A PoL2 benchmark” 一条。** 可以加上要求：这个基准需要带时间戳，并定期刷新，因为静态的仇恨语言基准会随语言演化而失效。

### (b) 作为 tab:checklist 的验收项
建议**新增第 16 项**（标 $^\circ$，表示不来自 arx32160）。也可以把它并入第 3 项和第 8 项，但单列更清楚。

| # | Requirement | Provisional pass criterion | Basis |
|---|---|---|---|
| 16$^\circ$ | Temporal re-validation: re-evaluate on a time-stamped hold-out of recent items and on paired items in which a target word is replaced by a newly emerged term of the same meaning | Per-period recall of hate language, and flip rate on neologism pairs, within a set margin of the certification period and of the repeat-noise floor; thresholds re-certified when either is exceeded | \cite{dibonaventura2025hatevolution} |

设计说明：
- 用 recall（漏检）而不用 macro-F1，原因是实验 1 显示的长期趋势恰好是 hateful 类变差、non-hateful 类变好，平均指标会把这种恶化掩盖掉。这一点与第 8 项（分子类报告）的精神一致。
- 新词替换翻转率用与第 4 项相同的“repeat-noise floor 倍数”结构。原文 label flip 的数量级（6/20 模型 >10%，最好的非退化模型 2.94%）可以作为设定阈值的参考，但**原文没有提出任何通过阈值**；具体数值仍按本表惯例由部署方设定。
- 一个可选的更简短的英文写法：“Flip rate on neologism-substitution pairs at most twice the repeat-noise floor; per-period hate recall not below the certification-period value minus a set margin.”
- 可以顺带在 §6 第 4 条（Calibrate locally）末尾加一句：“and re-certified on a schedule and whenever a temporal re-validation fails.”

### (c) 对未来 PoL2 中文恨语基准的启示

**可以沿用的**
1. **双轨设计**：一条是带时间戳的自然语料，按时期分层评估（对应实验 1）；另一条是受控的反事实配对（对应实验 2）。后者不依赖持续抓取平台数据，作者也说实验 2 可以用词典资源重复，这一点对中文尤其重要，因为中文平台数据难以长期合规采集【推断】。
2. **指标拆分**：把 label flip（判决翻转）和 hallucination（不按格式作答）分开统计，正好对应 typed 模型的 G4 问题。typed 模型输出受约束，hallucination 不适用；但三值构念中 “insufficient / state of absence” 的选择率可以替代 hallucination 的位置【推断】。
3. **报告排名一致性**：对多个候选检测器，同时报告其在 PoL2 基准与通用中文毒性基准（如 COLD、ToxiCN）上的 Spearman 排名相关和 CI，用来检验通用中文基准能否替代 PoL2 自己的构念。
4. **按年份做污染检查**的思路。

**需要改造的**
1. **新词类型**：中文需要另建分类，例如谐音、拼音缩写、缩略语、错别字和拆字规避、表情或符号替代、旧词新义（“semantic”）。英文的 lexical / morphological / semantic 三分法不能直接套用，中文缺少 blending/splintering 那样的形态派生【推断】。
2. **标签体系**：原文是二值的 hateful / non-hateful，PoL2 是 love / hate / state of absence 三值。反事实不变性在三值下的定义需要扩展：替换后从 hate 变成 absence，应当算作“翻转”还是“降级”？需要预先定义【推断】。
3. **标注**：原文只有三位作者标注，κ = 0.67。PoL2 基准需要独立的、对分歧敏感的标注（§7 已经引用 davani2022dealing）。

**无法直接迁移的**
1. **PoL2 的个案适用规则**（扬爱抑恨，§4.3.2）：小说和游戏中的“制造的仇恨”分级管理、安全机器人的紧急警告不算仇恨攻击、伪造亲密感算情感操纵。这些都需要**语境标签**（体裁、场景、说话者角色）。原文只评估孤立的句子，没有语境维度。
2. **“爱”极和“情感操纵”**：原文完全没有涉及。
3. **反事实前提**：原文要求 s2 与 s1 “same meaning”，所以标签不变。PoL2 的语境例外需要的恰恰相反：同一句话换一个语境后，正确标签**应当改变**（例如小说中的台词）。这需要“应变的反事实”，而不只是“应不变的反事实”，这种设计原文没有【推断】。

---

## 3. 局限与不可迁移之处（本评估的判断）

1. **统计证据比标题和摘要弱。** 8 个 ρ 的 90% CI 全部跨过 0，n = 20，CI 用的是 Pearson 型 Fisher z 公式（标准误 1/√(n−3)），没有针对 Spearman 做修正。所以只能说“静态排名不能预测时间敏感排名”，不能说“两者负相关”。引用时应当写成 “negative or near-zero, with intervals including zero”。
2. **实验 1 的年份效应与样本构成混在一起。** 原文没有报告每年的样本量和类别比例，也没有给逐年的 CI，所以逐年波动有多少是抽样噪声、有多少是语言演化，无法区分。此外，Singapore Online Attacks 来自新加坡相关的 Reddit 内容，年份差异可能反映的是话题或事件的变化，而不只是“语言”的变化【推断】。
3. **剔除非预期输出会抬高 F1。** DeepSeek 在 HateCheck 上只有 0.54% 的输出符合预期，仍然有 F1 .3750，并参与排名。退化模型（例如 FLAN-T5-small 的 hateful F1 全部为 .0）也参与 Spearman 排名，可能放大排名噪声【推断】。
4. **实验 2 的 Spearman 用哪个指标排名没有说明**（Table 4 有三个指标），排名相关的含义因此不明确。
5. **两个 API 的阈值没有报告。** 对本文 G6（阈值不可迁移）来说，这是一个无法利用的空白。
6. **没有涉及 typed 模型或校准。** 所有结论都是关于标签和排名的，没有概率、ECE 或阈值分析，所以不能直接支持 G4 的校准主张，只能支持“分布会漂移”这个前提。
7. **没有中文。** DeepSeek 是中英双语模型，但只在英文上测试，而且 Table A6 中它几乎不按指令作答（98.82%），无法从中推断任何中文表现。
8. **规模小，标注者是作者本人**（341 对，κ = 0.67）。
9. **二值标签**，与 PoL2 的三值构念和“爱不等于善、恨不等于恶”（§1.5）的结构性定义不同。原文的 “toxic / respectful” 提示词恰恰是 PoL2 明确反对的道德化标签【推断】。

---

## 4. BibTeX 与候选句子

字段已对照 arXiv 摘要页的 citation_* meta 和 PDF 首页核对。没有核实到正式发表的会议或期刊。

```bibtex
@misc{dibonaventura2025hatevolution,
  author        = {Di Bonaventura, Chiara and McGillivray, Barbara and He, Yulan and Mero{\~n}o-Pe{\~n}uela, Albert},
  title         = {{Hatevolution}: What Static Benchmarks Don't Tell Us},
  year          = {2025},
  eprint        = {2506.12148},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  doi           = {10.48550/arXiv.2506.12148},
  url           = {https://arxiv.org/abs/2506.12148}
}
```

**候选句 1**（用于 G4 “Calibration is local.” 段末，或 §6 Trade-offs 中 drift 一句）：

> For hate speech the shift is not hypothetical: across 20 language models, rankings on four static English hate-speech benchmarks did not predict rankings on time-stamped or neologism-substituted data (Spearman's $\rho$ between $-0.31$ and $0.19$, all 90\% intervals including zero), whereas the static benchmarks agreed with each other (mean $\rho = 0.36$)~\cite{dibonaventura2025hatevolution}.

依据：Table 5 中 ρ 的范围是 −0.3053 到 0.1909，并且 CI 全部含 0；Table A11 的均值是 0.36。

**候选句 2**（用于 G1 “Relation to prior work”）：

> Static scores also age: in English, replacing one word with a recently coined term of the same meaning flipped the hate-speech label of more than 10\% of sentence pairs for 6 of 20 zero-shot models, and most models detected hateful posts less well in later years~\cite{dibonaventura2025hatevolution}.

依据：Table 4 的 6/20 和 §3 原文 “most language models exhibit a decreasing performance in detecting hateful instances”。

**候选句 3**（用于 §7 Open problems 中 “A PoL2 benchmark”）：

> Because static hate-speech benchmarks lose predictive value as language changes~\cite{dibonaventura2025hatevolution}, such a benchmark should be time-stamped and periodically refreshed, including paired items with newly emerged terms.

依据：原文结论 “call for time-sensitive linguistic benchmarks”。这句的建议部分是本文自己的推论，原文本身没有针对 PoL2 或中文。
