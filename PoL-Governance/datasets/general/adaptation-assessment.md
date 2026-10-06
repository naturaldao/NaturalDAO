# 适配评估：target 形态会不会卡住后续微调

**问题**（用户原话）：我们的软分布和 One-Hot 会不会影响到之后的微调适配阶段？还能不能用常用的方式（比如 RLCD 等）进行训练，还是说完全没办法跟后面适配？

**范围**：只回答"形态能不能被训练方法消费"，不改数据、不动划分、不做 git 写操作。所有对语料的计数都是本轮对冻结语料现算的只读过程（见 §8），与 [target-provenance.md](target-provenance.md) 的数字一致。

---

## 0. 一页结论

**判断：不会卡住，属于"直接可用，但要按形态路由 + 换一个输出头"，不是"完全没法适配"。**

| 训练方法 | 我们 31,786 个 target 支不支持 | 依据 |
|---|---|---|
| SFT / 交叉熵（硬标签） | ✅ 支持。22,536 个 target 直接可用（14,119 one-hot + 8,417 只有 answer） | §3 |
| 软目标蒸馏（log score / KD） | ✅ 支持。7,520 个真分布可直接当软目标 | §4 |
| RLCD（TypeSafe 义：Reinforcement Learning for Calibrated Decisions） | ✅ 支持：它的 reward 是"严格 proper scoring rule + 目标分布"，我们有 7,520 个目标分布；硬标签行也能跑，但退化成"教模型说 1.0" | §5 |
| RLCD（学界义：Reinforcement Learning from Contrastive Distillation, ICLR 2024） | ❌ 不支持：它需要模型自己生成文本、构造偏好对、再训奖励模型；我们是非生成语料，没有生成物、没有偏好对 | §5 |
| DPO / 偏好优化 | ⚠️ 不直接支持：没有 chosen/rejected 对，只能人工构造（正确项 vs 干扰项）；构造出来的对通常太容易被区分，信号弱 | §6 |
| RLHF / RLAIF | ⚠️ 需要额外数据：没有偏好标注、没有 AI 偏好标签；可以把软分布当 reward/judge 监督，但不是 RLHF 本身 | §6 |
| RLVR（可验证奖励） | ❌ 不支持：语料里没有环境、没有可执行验证器，只有静态 (state, question, options, target) | §6 |
| 校准感知损失（label smoothing / Brier / RPS / 温度缩放） | ✅ 部分支持：训练侧都能上；**验证侧缺"真概率参照"**（冻结语料里只有 432 个规则精确概率能当参照，占 1.4%） | §4.4、§6 |
| 防遗忘（replay / 混合通用数据） | ✅ 支持：硬标签 CE 就够；本语料可直接当 replay 数据 | §6.8 |

**必须做的三件事**（都是训练侧工程，不是数据返工）：

1. **输出头必须是"候选打分头"**，不能是固定类别分类头。因为 (slug, question key) 有 3,730 种、选项数 2–57、score 档位 3–11 档。Jev 类模型的开源实现（Laya / Kev / Intern-Decision / system-one-270m）全部是这个头，做法有公开代码。
2. **损失按 target 形态路由**：真分布行 → log score（序数题再加 RPS）；one-hot / 只有 answer 行 → 交叉熵；无信息均匀行 → 先剔除（已决）。
3. **软分布只能当"蒸馏目标"，不能当"校准参照"**。要用它测 ECE/Brier，测出来的是"和教师像不像"，不是"概率准不准"。

**唯一值得考虑补的数据**：一个带**真概率参照**的小校准集（人投票比例 / 多标注者分布）。冻结语料里没有任何一个是人类投票分布（[target-provenance.md](target-provenance.md) §4.1：`vote_share` = 0、`human_annotation` = 0）。没有它，校准声明只能靠"跟教师一致度"和"温度缩放后的 ECE"间接支撑。

**中文侧的限制**：7,872 条中文只有硬标签、没有分布。中文只能做 CE / 准确率路线，做不了校准训练，除非另配一个多语言教师生成软目标。

---

## 1. 证据等级（先说清楚哪些是查到的、哪些是我推的）

| 标记 | 含义 |
|---|---|
| **【文档】** | 上游论文 / 模型卡 / 官方文档 / 公开代码里**明说**；给可点击 URL |
| **【实测】** | 本轮从冻结语料 `datasets/general/data/items.final.jsonl` 现算（过程见 §8，可复算） |
| **【推断】** | 上面两类不足以直接支持，由我合并推断；**同时给备选解释** |
| **【查不到】** | 公开材料里找不到，明确写"查不到"，不猜 |

**跨环境注意**：本轮 `web_fetch` 在本机被 DNS 策略拦掉（所有域名解析到非公网地址），网页内容是用本机 `Invoke-WebRequest` 取的，取到的正文我已核对过是原页面文本。论文摘要取自 arXiv abs 页。

---

## 2. Q1：System-One / Jev 这类模型实际是怎么训练的？

### 2.1 共同形状：非自回归 + 候选打分 + 约束输出空间

这一族模型（Jev、Laya、Kev、Intern-Decision、system-one-270m，以及 JevK5 / NanoJev / vllm2jev / localjev 等复现）公开的做法高度一致：

1. **不生成文字**。state 与"类型化问题"一起进模型，问题自带候选集（choice 的选项、score 的档位、noul 的是/否）。
2. **一次前向算出整个候选集上的分布**（不是逐 token 生成）。不同实现读分布的位置不同：
   - Laya（ModernBERT 编码器）：每个选项写进输入、各带自己的 `[MASK]` token，在各自的 `[MASK]` 位打 softmax —— 【文档】<https://huggingface.co/convaiinnovations/laya>
   - Kev（Qwen3.5 解码器 + pointer head）：两个投影把每个选项的收尾 token 与问题的末位 token 打分，softmax 得到概率 —— 【文档】<https://huggingface.co/jaredpalmer/kev-4b>
   - Intern-Decision（Qwen3.5）：把选项映射成单 token 符号 `A`…`Z`、`a`…`z`、`0`…`9`，在 `<decision>` 占位符前一位读 logits，只在该字段合法符号上 softmax —— 【文档】<https://huggingface.co/internlm/Intern-Decision-0.8B>
   - system-one-270m（Gemma-3-270m）：选项渲染成字母，取 `A`…`Z` 这些**单 token** 的 logits，mask 掉其余，softmax —— 【文档/代码】<https://github.com/Akicou/system-one-270m>（`train.py`）
3. **损失 = 在该候选集上的交叉熵 / log score**。Kev 的写法最直白："The loss is cross-entropy over each question's options."；Intern-Decision 训练时"cross-entropy uses the full vocabulary"，推理时才把 logits 限制到合法符号。
4. **序数题另加序数损失**。system-one-270m 的 `train.py` 里 `RPS_WEIGHT = 0.5`，对 score 题在 log score 之外加 ranked probability score（"一格错"比"四格错"便宜）—— 【文档/代码】。
5. **校准靠后验温度缩放**。Kev 存了一个 `T=2.41`（在 held-out 上按 NLL 拟合）；Intern-Decision"Fit one positive scalar per checkpoint by NLL on calibration data only"；system-one-270m 同时报 ECE 与 ECE(temp-scaled)，并明说"只在校准后才准的模型不是学会了校准，是被补上的"。

**关键点：这一族模型需要的是"每个问题在候选集上的一个标签或一个分布"，而不是"一段文字"。我们的 target 恰好就是这个形状。**

### 2.2 Jev 本身：方法名公开，机制没公开

- **RLCD = Reinforcement Learning for Calibrated Decisions**，TypeSafe 自己的第三种后训练路线（对 RLHF / RLVR）—— 【文档】官方文档 <https://docs.typesafe.ai/introduction/machine-learning-primer>、官方发布文 <https://typesafe.ai/blog/introducing-system-one-models-and-jev>。
- 输出契约：**每个答案都带 calibrated probabilities 与 confidence**；"Jev outputs all probabilities in parallel instead of autoregressively generating by token" —— 同上【文档】。
- **机制（损失、奖励、数据）没有公开**。官方只说目标：概率要"epistemically honest"，0.2 的预测应在大约 20% 的情况发生。TypeSafe 不提供客户微调 / LoRA（[CATALOG.md](../../models/CATALOG.md) 已记）。
- 第三方对"Jev 用 RLCD 训练"的引用见 <https://arxiv.org/abs/2609.29429>（*Just Ask Jev*，2026-09-24）与 <https://arxiv.org/abs/2609.28940>（渗透测试 harness 一文，逐条比较 RLHF / RLAIF / RLCD / RLHV）。

### 2.3 有公开训练代码 / 论文的同类实现（可直接引用的证据）

| 实现 | 头 / 损失 | 训练数据形态 | 与 Jev 的可比成绩 |
|---|---|---|---|
| **Laya**（Apache-2.0，ModernBERT-large 421M / mmBERT 322M） | `[MASK]` 位打分 + 选项集 softmax；**RLCD**：奖励 = 严格 proper scoring rule（log + spherical，序数题加 RPS），REINFORCE + group-mean baseline（GRPO 式） | 决策数据；`laya-train --data tickets.csv` 支持**普通带标签 CSV** 微调 | typed-decisions 0.766 acc / Brier 0.062；Jev 0.727 |
| **Kev-4B**（Apache-2.0） | 冻结骨干 + LoRA r16 + **pointer head**；**交叉熵 over options**；外挂一个温度 T=2.41 | **硬标签**：十个公开分类数据集的原始标签、代码算出的规则标签——"No output of Jev was used" | 新来源 0.838 acc / Brier 0.242（Jev 0.857 / 0.211），27B 版 0.889 / 0.156 |
| **Intern-Decision-0.8B/2B/4B**（Apache-2.0） | `autoregressive masked language modeling` + 决策位 CE；推理限制到合法符号 + 拟合温度 | 硬标签（答案符号只在 label 里，不在输入里） | 七套件均值 90.02%（Jev 88.74%）；另在 96 条校准试点上报 Brier 0.550 / ECE 0.089（Jev 0.595 / 0.130） |
| **system-one-270m**（开源复现，MIT 代码） | 单 token 字母位打分；**log score（严格 proper）+ 序数 RPS**；温度网格搜索 | 教师 `top_logprobs` 经置换集成得到的**软目标**（并明确说语料歧义太少限制了校准） | 无 Jev 对比；Brier 0.718→0.411，ECE 0.304→0.131 |

**成绩口径提醒**：表里 Kev / Jev 的数字来自 Kev 自己的模型卡，其中 Jev 只在两套件的 **development** 划分上跑过，Kev 用 test、`Jev has only been run on the development sets`，作者自己写明`this isn't a controlled comparison of the two architectures`。所以这张表用于说明**路线可行**，不用于排强弱。Intern-Decision 的 Brier / ECE 来自它自己的 96 条校准试点，不是与上表同一套件。

**读这张表要得到的结论**：这一族里两个成绩最好的开源实现（Kev、Intern-Decision）**主力都是硬标签 + 交叉熵**，软目标是可选项而不是必需项；而"校准"这一步，四个实现全部落在**后验温度缩放**上。

---

## 3. Q2：one-hot 目标能用吗？

### 3.1 能用，这就是标准硬标签

**结论：成立，且有公开实证。** one-hot 在交叉熵 / 分类损失下就是标准硬标签，不存在"格式不合法"的问题：

- Kev：主力配方用十个公开数据集的**原始硬标签**，损失就是"cross-entropy over each question's options"，在 held-out 新来源上做到 0.838（4B）/ 0.889（27B），Brier 0.242 / 0.156，与 Jev（0.857 / 0.211）同一档 —— 【文档】<https://github.com/jaredpalmer/kev>。
- Intern-Decision：训练用普通 causal next-token CE（全词表），硬标签，七套件均值 90.02% 超过 Jev 的 88.74% —— 【文档】<https://github.com/InternLM/Intern-Decision>。
- 我们自己的 [CONTRACT.md](CONTRACT.md) §2.3 也是这个立场：one-hot"是硬标签的单点分布"，只是**不能当校准目标**。

### 3.2 我们语料里有多少 one-hot、能不能直接喂

- 【实测】14,119 个 one-hot + 8,417 个"只有 answer" = **22,536 个 target 可以走硬标签 CE**，占 71%。
- 【实测】one-hot 行里**恰好一个 1.0、其余 0.0，且这个 1.0 就落在 `answer` 上，14,119/14,119 全部一致**（§8.2）。
- 【实测】没有重复选项键、答案全部落在该题自己的选项 / 档位空间内、probs 全部和 = 1.0（§8.3）。

也就是说：**one-hot 这一档不需要任何转换，就是训练标签。**

### 3.3 什么场景下 one-hot 反而有害（要记住的四条）

1. **你要校准概率的时候。** CE 配 one-hot 会一路把正确类的概率往 1 推；现代神经网络在 CE 下本来就偏过度自信（Guo et al., ICML 2017，<https://arxiv.org/abs/1706.04599>），而 label smoothing 之所以有效，一部分原因正是"prevent the network from becoming over-confident"（Müller et al., NeurIPS 2019，<https://arxiv.org/abs/1906.02629>）。Kev 的"confident errors（错答案且概率 ≥ 0.9）8.2% → 温度缩放后 2.4%"就是这个病的直接测量。
2. **序数题（我们的 score）**。把 0–5 档当无序类做 CE，等于告诉模型"差一格"和"差五格"一样错。Jev 类实现的修法是加序数项（system-one-270m 的 RPS，Laya 的"ranked probability score for ordinal questions"）。我们语料有 5,235 个 score 题。
3. **本来就歧义的样本。** 一条 60/40 的样本被写成 one-hot，就是在教模型"这里要确定"。system-one-270m 的设计文档直说：*"A corpus of one-hot labels from a single teacher trains argmax accuracy and destroys calibration"*，并且"把语料过滤成教师有把握的样本，是最可能交付一个'自信地错'的模型的方式" —— 【文档】<https://github.com/Akicou/system-one-270m/blob/main/docs/jev-system-one.md>。我们 22,536 条硬标签 vs 7,520 条软目标，比例是 3:1，**在"练校准"这个目标上是偏硬的一侧**。
4. **规则标签在边界样本上系统性错。** 8,631 条"来源自带 one-hot"里，4,221 条来自 Open-Jev 控制规则、3,696 条来自 procedural 规则；它们的可信度是"规则说它对"，不是"世界就是这样"（[target-provenance.md](target-provenance.md) §5 的 `label_trust`）。

**但注意第 3 条的边界**：Kev 明确用 **uniform 目标**表示"**证据被抽掉、无法判断**"（"255 cases with the deciding sentence removed and a uniform target"）。所以"均匀"不是天然有害：**状态里真的没有信息时，均匀是正确答案；整条子流不分状态恒定 0.5 时，才是噪声**（对应 [target-provenance.md](target-provenance.md) §0.4 的 `yuri_v1`）。这条区分决定了我们那 1,730 条该"整批剔"还是"分流处理"。

---

## 4. Q3：软分布目标能用吗？语义不统一有什么实际影响？

### 4.1 能用，而且是成熟做法

- 软目标是知识蒸馏的原始设定（Hinton et al., 2015，<https://arxiv.org/abs/1503.02531>）。
- 在 Jev 这一族里，软目标还有更强的身份：**严格 proper scoring rule 的 reward 必须对着一个分布才有意义**。Laya 的 RLCD 描述就是"奖励 = 严格 proper scoring rule（log + spherical，序数题加 RPS）"，学生报分布、探索给 logits 加零均值高斯噪声、REINFORCE 更新 —— 【文档】<https://huggingface.co/convaiinnovations/laya>。
- 我们的 7,520 条真分布**就是**这种目标：每条是某个候选集上的合法分布（和 = 1.0【实测】），可以直接进 log score / Brier / spherical。

### 4.2 语义不统一：训练层面不致命，解释层面会致命

先把两件事分开：

**(A) 梯度/损失层面——不影响。** proper scoring rule 对**任何**合法分布都有定义，它不需要知道这个分布"是教师的信念"还是"规则算出的后验"。多个不同教师的软目标混训，就是标准的 multi-teacher distillation，不产生数学错误。

**(B) 解释与使用层面——影响很大，有四条：**

1. **不能当同一个量做统计。** 同一个 `probs` 字段里装着教师预测分布、规则参考标签、并列占位、我们造的单点分布、常量（[target-provenance.md](target-provenance.md) §0.1）。跨源求"平均熵 / 平均最大概率"会得到没有意义的数：四个来源的"平均熵"差 6 倍（0.122 / 0.347 / 0.693 / 0.755），它们不是同一个量的不同尺度，是四个不同的量【文档/实测，provenance §2.3】。
2. **不能把蒸馏目标当校准参照。** 用它测 ECE/Brier，测的是"学生和教师像不像"。全语料真正能当"概率参照"的只有 432 条规则精确概率（1.4%）【文档，provenance §5】。
3. **教师自身的偏差会被学进去。** 我们的软目标来自 Jev 1.13 的蒸馏（5,364 条）、gpt-oss-20b 的 `top_logprobs` 集成均值（1,492 条）、合成任务的精确后验（432 条）、并列均分（232 条）【文档/实测】。在教师不擅长的域，软目标就是把它的弱学过来；*Just Ask Jev* 那篇也报告了 Jev 的概率"排序好、但当阈值不好用"（同文复现：F1@0.5 = 0.158，拟合阈值后 0.947，5 个拟合阈值里没有一个接近 0.5）—— 【文档/实测复现】<https://github.com/jkf87/jev-rlcd-replication>。
4. **别承诺"蒸馏能带来校准"。** Stanton et al.（NeurIPS 2021，<https://arxiv.org/abs/2106.05945>）的结论是：学生通常**匹配不上**教师的预测分布，即使容量够；而且"更像教师"并不总等于"泛化更好"。**【推断】** 所以我们的软目标能被消费，但不应指望学生复现教师的校准。

### 4.3 三种"看起来是分布、其实不是"的行，要分别处理

| 形态 | 我们有多少 | 训练上怎么处理 | 依据 |
|---|---:|---|---|
| 退化常量（整条子流恒 `[0.5,0.5]`，`yuri_v1`） | 1,621 | **剔除**（已决）。任何目标都不该是"永远 0.5" | [target-provenance.md](target-provenance.md) §0.4 |
| 无信息均匀（无正权重差异，且与状态无关） | 1,730（含上面 1,621） | **剔除**（已决） | 同上 §5 |
| 并列均分（非零权重在**正权重子集**上相等，open-jev 201 + openjev_v2 31 条） | 232 | **可保留**：`0` 放在未并列项、`1/k` 放在并列项，就是一个合法的"这些都对"的目标 —— 【推断】，上游卡面只写了"Choice targets are uniform over equally best passages"，没写这层训练含义；备选解释是 provenance 的处置（当 `label_only` 的硬标签） | provenance §6.3 R13 |
| 教师软分布（`model_logits`） | 6,856（5,364 + 1,492） | 走 log score；**只当蒸馏目标** | provenance §4.1 |
| 规则精确概率（procedural 7 键） | 432 | 同上，且是唯一可当"概率参照"的一档 | provenance §5 |

> **口径提醒**：任务书里"常量退化 1,621"是 1,730 条 uniform 的子集，**不要减两次**。剔掉 uniform 后剩 30,056 个 target。

### 4.4 一个必须点明的落差：软目标和硬标签是"同向"的

【实测】全部 21,639 条有意义的 probs（7,520 soft + 14,119 one-hot）里，`argmax(probs) == answer` **100% 成立**（uniform 的 1,730 条此项无意义，因为最大项并列）。这意味着：**同一行内部，软目标和硬标签从不冲突**，训练时可任选其一，或按行路由，不需要仲裁逻辑。冲突只存在于"行与行之间"（不同教师/规则对相似输入的判断不同）——这在多教师训练里是常态。**【推断】** 其后果是模型置信度会被拉向中间值；备选解释：教师本身就偏向 1.0 主导（我们的 soft 子集平均最大概率 0.666–0.942，本就不算软）。

---

## 5. Q4：RLCD 是什么，我们的数据支不支持？

### 5.1 这个词在此语境下有两种完全不同的展开（都真实存在，必须分开）

| 展开 | 出处 | 是什么 | 我们的数据 |
|---|---|---|---|
| **Reinforcement Learning for Calibrated Decisions** | TypeSafe 官方文档与发布文【文档】：<https://docs.typesafe.ai/introduction/machine-learning-primer>、<https://typesafe.ai/blog/introducing-system-one-models-and-jev> | 后训练目标对准"决策 + 校准概率"，而不是人类偏好或可验证答案。官方**没有公开机制**（损失、奖励、数据都没说） | ✅ 见 §5.2 |
| **Reinforcement Learning from Contrastive Distillation** | ICLR 2024，K. Yang et al.，<https://arxiv.org/abs/2307.12950> | 用一个"正面提示"和一个"负面提示"让模型生成两份输出凑成偏好对，训偏好模型，再 RL 对齐。**不需要人类反馈，但需要模型生成** | ❌ 见 §5.3 |

**在本项目（Jev / System-One 语境）里，RLCD 指的是第一个。** 佐证不止官方两处：同行论文也这么用 —— *Just Ask Jev*（<https://arxiv.org/abs/2609.29429>）写 "Jev, a model trained with reinforcement learning for calibrated decisions (RLCD)"；渗透测试那篇（<https://arxiv.org/abs/2609.28940>）把 RLCD 与 RLHF / RLAIF / RLHV 并列，并写明 RLCD "trains against strictly proper scoring rules … where the unique optimal prediction is the true probability distribution"，且"Laya documents training against the Brier score explicitly"。

缩写还有其它可能的展开（我没找到把它们用在 Jev/TypeSafe 语境里的证据，列出以免混淆）：Reinforcement Learning with Calibrated Decisions、Reinforcement Learning from Critique/Deliberation（部分 RLHF 变体里用 RLCD 指 critique 训练）。**这三条属于【查不到确切所指】，不作为判断依据。**

### 5.2 TypeSafe 义的 RLCD：我们的数据**支持**（有前提）

TypeSafe 没公开机制，但**有一个公开的开源复现把机制写出来了**（Laya 模型卡，Apache-2.0）：

> 策略输出一个分布；探索在 logits 上加零均值高斯噪声；奖励是严格 proper scoring rule（log + spherical，序数题加 ranked probability score）；更新是 REINFORCE + group-mean baseline（GRPO 式）。
> —— <https://huggingface.co/convaiinnovations/laya>

按这个读法，RLCD 需要的最小数据是：**（state + 问题 + 候选集 + 一个目标分布）**。我们的语料：

- 7,520 条**有目标分布**（合法、和 = 1.0【实测】）→ 可以直接当 reward 参照，**这就是 RLCD 的原生形状**。
- 22,536 条只有硬标签 → 也能算 proper score（对 one-hot 目标），但严格 proper scoring rule 的性质是`最优预测就是目标分布本身`，对 one-hot 目标即`输出 1.0`，**退化成普通 CE，拿不到校准收益**（这是 proper scoring rule 的定义性质，不是经验观察）。
- 另外还需要一个能在候选集上输出 logits 的头（§0 第 1 条），否则没有可探索的分布。
- 不需要：偏好对、奖励模型、环境、人类标注。

**【推断】** 用 7,520 条软目标跑 RLCD 是这套数据最"对齐"的用法；备选解释是直接在软目标上做 log score 的 SFT（等价于把奖励梯度换成教师强制），在只有 7.5k 软样本时更稳。两者都需要先解决"软目标语义不统一"的解释问题（§4.2），但不影响能不能练。

### 5.3 学界义的 RLCD（对比蒸馏）：**不支持**，且不必绕

它要求：模型能**生成**两份对照输出（需要正面/负面提示）→ 用生成物构造偏好对 → 训偏好模型 → RL。我们的语料是静态四元组 (state, question, options, target)，**没有生成物、没有偏好对、没有可对齐的原则提示**。要支持它，等于先引入一个生成模型和一套提示工程，产出的偏好标签再喂给一个小决策模型——这是另一条技术路线，不是"我们的数据卡住了它"。

**明确说**：这不构成适配障碍。对"只做选择、不生成文字"的模型，RLCD(对比蒸馏) 是错的工具，不是缺的数据。

---

## 6. Q5：其它常用适配方法逐个判断

| 方法 | 我们支不支持 | 需要什么额外数据 | 依据 / 备注 |
|---|---|---|---|
| **SFT / CE（硬标签）** | ✅ 直接支持，22,536 条 | 无 | Kev、Intern-Decision 主力配方【文档】 |
| **软目标蒸馏（log score / KL）** | ✅ 7,520 条 | 无。若要"软硬同权"，需按行路由损失 | Hinton 2015；Laya RLCD |
| **RLCD（TypeSafe 义）** | ✅ 7,520 条软目标最合适；硬标签行退化 | 候选打分头（代码，不是数据） | Laya 卡面【文档】 |
| **RLCD（ICLR'24 对比蒸馏）** | ❌ | 生成模型 + 对照提示 + 偏好对 | arXiv 2307.12950【文档】 |
| **DPO / 偏好优化** | ⚠️ 只能构造 | 需要 (prompt, chosen, rejected)。我们每题只有一个正确答案：可把"正确项 vs 随机干扰项"凑成对；但这类对太容易区分，DPO 收益通常有限 —— 【推断】，无我们语料上的实验证据。Kev 的"minimal pairs（加/去 'none of the above' 各一次）"是同类构造的先例，但它是配 CE 用的，不是 DPO【文档】<https://github.com/jaredpalmer/kev> | DPO 原文 <https://arxiv.org/abs/2305.18290> |
| **RLHF** | ❌ | 人类偏好标注（我们没有；冻结语料里 `vote_share` = 0） | provenance §4.1 |
| **RLAIF** | ⚠️ 可自造 | 用 LLM 给候选打偏好；成本低但会继承打分模型的偏差（渗透测试那篇明确把 RLAIF 列为不适合安全关键决策的**唯一**信号） | <https://arxiv.org/abs/2609.28940>【文档】 |
| **RLHV（Human Verification）** | ⚠️ 可自造 | 每次预测后要有人/下游系统的验证结果回流；我们目前没有任何 (prediction, outcome) 日志 | 同上【文档】 |
| **RLVR** | ❌ | 需要可程序化验证的结果与环境；语料是静态判断，没有环境 | — |
| **校准感知损失**（label smoothing / Brier / spherical / RPS / focal / 温度缩放 / Dirichlet 校准） | ✅ 训练侧都能上；**验证侧缺参照** | 若要**验证**校准：需要带真概率的保留集。冻结语料里只有 432 条（1.4%）能当参照，且限于合成世界 | provenance §5；Guo 2017；Müller 2019 |
| **防遗忘（replay / 通用数据混合 / LoRA）** | ✅ 支持，硬标签 CE 即可 | 无 | 见 §6.8 |

### 6.8 关于真实目的："微调 PoL2 时不降低通用智力"

这一条**和 target 形态无关**：无论 one-hot 还是软分布，只要目标落在候选集上、能算出一个标量损失，就能当 replay 数据用。三点提醒：

1. 持续微调确实会遗忘，规模越大越明显，而**通用指令数据的混合能缓解后续微调中的遗忘**（Luo et al., <https://arxiv.org/abs/2308.08747> 摘要原话："general instruction tuning can help alleviate the forgetting phenomenon in LLMs during subsequent fine-tuning"）。这正是本语料的定位。
2. **我们的软目标是"别的教师"的分布（Jev 1.13 / gpt-oss-20b / 规则），不是"我们底座自己"的分布。** 所以它们**不能**当"KL 锚定底座、防止漂移"的锚点。若真实目标里包含"尽量不改变底座行为"，需要**另外**从底座自身采样目标（self-distillation）或显式加 KL 项到冻结底座 —— 这是额外数据/算力，不在本语料里。【推断】

---

## 7. Q6：结论、必须做的 X、最小补救

### 7.1 判断

**"直接可用"（但要按形态路由 + 换输出头），不是"完全没法适配"，也不需要返工数据。**

理由按重要性排序：

1. **形状对得上**：Jev 类模型要的是"在候选集上的标签或分布"，我们的 4 种形态全部落在候选集上，且【实测】答案、probs 键、选项空间三者零违规、probs 全部归一、无重复键。
2. **两条主力路线都有公开实证**：硬标签 CE（Kev、Intern-Decision）与软目标 + proper scoring（Laya、system-one-270m）都能训到与 Jev 同档，而我们的两类数据量都够（22,536 硬 / 7,520 软）。
3. **RLCD 在本语境的含义已确认**（TypeSafe 义），且其公开复现的机制与我们的软目标格式直接对应。
4. **真正的限制不在"能不能训"，在"能不能验证校准"**：语料里没有人类概率参照；这一条不卡训练，卡的是任何"我们的概率是准的"的声明。

### 7.2 必须做的 X（按优先级）

1. **补 target 级 provenance 到训练代码的读取路径**：按 `target_type` 路由损失（软 → log score [+RPS]；硬 → CE；无信息 → 丢弃）。task-1 正在落盘这套字段；训练侧要**真的读**它，而不是按 slug 猜。
2. **候选打分头**：把每个问题的候选集渲染进输入，取候选符号/占位位的 logits，在该题候选集上 softmax。四个开源实现都有可抄的写法。**不要**建全局分类头（3,730 种 (slug,key)、选项 2–57）。
3. **序数题走序数损失**（RPS 或分桶 CDF 损失），否则 5,235 个 score 题的档位信息白给。
4. **剔除 uniform（1,730，含常量 1,621）**，除非某条能证明"状态本身缺证据"（Kev 的做法）。
5. **中文侧明确定位**：只做 CE/准确率路线；若要中文校准，需另找多语言教师生成软目标（额外数据）。
6. **后验温度缩放 + 独立校准集**：Kev/Intern-Decision/Laya 都这么做。注意不要把测试集当校准集。

### 7.3 若诊断要"校准可验证"，最小补救

- **补一个小规模真概率参照集**（几百条即可）：同一 state 多标注者的投票比例，或"同一问题在多个独立教师上的分布"。
- 仓内最接近的现成候选是**已退役模板线**里的 `civil-comments`（2,990 条标注者比例）与 `aegis1`（标注者投票）—— 但按 [target-provenance.md](target-provenance.md) 附录 A，它们**不在冻结语料内**，且需先解决许可与"标注口径与我们无关"的问题。
- 不做这一步的后果：可以训练、可以报 ECE（在硬标签上），但**不能声称概率经过校准**。这不影响"微调适配"，只影响"能不能对外宣称校准"。

---

## 8. 本次实测过程（只读，可复算）

口径：读 `datasets/general/data/items.final.jsonl`（23,855 item / 31,786 target），逐个 `targets[key]` 判定。**不改任何文件。**

### 8.1 形态与语言（与 [target-provenance.md](target-provenance.md) §2.1 一致）

| 形态 | en | zh | 合计 |
|---|---:|---:|---:|
| 软分布（真·非退化） | 7,520 | 0 | 7,520 |
| 伪 one-hot | 14,119 | 0 | 14,119 |
| 全候选等值 uniform | 1,730 | 0 | 1,730 |
| 只有 answer | 545 | 7,872 | 8,417 |
| **合计** | **23,914** | **7,872** | **31,786** |

问题类型：choice 18,644 / noul 7,907 / score 5,235。每题 target 数：1 题 21,227、3 题 1,202、6 题 701、4 题 380、5 题 179、2 题 166。

### 8.2 软 / 硬标签一致性

- `argmax(probs) == answer`：soft 7,520/7,520、one-hot 14,119/14,119 **全部成立**；uniform 1,730 条此项无意义（并列）。
- 结论：软目标与硬标签在行内不冲突。

### 8.3 目标与候选空间的对齐（0 违规）

对每个 target，按其问题的 `options[].key`（choice/noul）或 `range(scale.min, scale.max+1)`（score）构造候选空间，检查：

- `target` 没有找不到对应问题的：0
- `answer` 落在候选空间外：0
- `probs` 键落在候选空间外：0
- `probs` 键数与候选数不一致：0
- `probs` 和 ≠ 1.0：0（23,369 条全部恰好 1.0）

### 8.4 头设计的实测约束

- (slug, question key) 组合数：**3,730** → 固定分类头不现实。
- 选项数分布（2–57）：2 项 8,830、3 项 6,427、4 项 5,385、5 项 734…**>16 项的共 2,087 题**，最大 57。
- score 档位：`(0,2)` 2,677、`(0,5)` 1,814、`(0,9)` 381、`(0,4)` 269，另有 `(0,1)`、`(0,3)`、`(0,6)`…`(0,10)`。
- score 题的 `scale.labels`：**3,144 题的 labels 是描述文字、2,091 题是数字** → 建词表必须用 `range(min, max+1)`，不能照 labels 建（[CONTRACT.md](CONTRACT.md) §2.1 已警告，本次实测复现）。

### 8.5 一个真实存在的措辞风险（不是形态问题，但会影响适配）

- **7,418 个 noul 题的选项键就是布尔词**（`true`/`false` 4,053 对、`yes`/`no` 3,365 对）。
- Laya 的模型卡明确警告："**Avoid boolean-word labels in choice questions.** Choice keys are rendered verbatim, and the current checkpoints can follow labels such as `true`/`false` or `yes`/`no` instead of the option descriptions. Use semantic labels or opaque labels such as `A`/`B`" —— 【文档】<https://github.com/NandhaKishorM/laya>。
- 本仓文献综述也记录了同类现象（只把选项名从 0/1 改成 no/yes，开源 Jev 类模型 AUC 从 0.94 翻到 0.23，Jev 从 0.81 降到 0.58，而类型错误率始终 0%）—— [survey.zh.md](../../research/PoL2-Jev-Typed-Literature-Survey/docs/survey.zh.md) 主要发现第 3 条。
- **处置建议**：训练时不要把选项键当语义用（渲染成 `A`/`B` 或把 `criteria` 描述放进题面），并在评估里做一次"选项换名"对照。这不需要改数据 —— 是**渲染层**的选择。

---

## 9. 不确定清单（不许猜的地方）

| # | 不确定的东西 | 影响 | 为什么不猜 |
|---|---|---|---|
| U1 | **TypeSafe RLCD 的真实机制**（损失、奖励、数据配比） | 只影响"要不要照抄 Jev"，不影响我们能不能训 | 官方只公开目标；唯一机制描述来自 Laya 对自己实现的说明，不能等同于 Jev |
| U2 | **我们 5,364 条 Jev 1.13 蒸馏软目标的读数机制**（并行 head softmax？校准头？2 位小数是 API 还是导出舍入） | 影响"能不能声称它们是 logits" | [target-provenance.md](target-provenance.md) §7 U1 已定 `mechanism_unknown=true`；按 `model_logits` 语义用没问题，不能声称是 logits |
| U3 | **中文 7,872 条答案的产生者**（Deepexi 卡面未说明） | 中文硬标签的可信度只能标"unknown" | provenance §7 U3 |
| U4 | **"常量 0.5"是教师退化还是管线 bug** | 只影响复现，不影响处置（无信息，剔除） | provenance §7 U2 |
| U5 | **混训软/硬目标对校准的实际影响**，在我们语料上没有实验证据 | 决定"要不要为软目标单独配比" | 目前只有理论（proper scoring）与别家经验，**没有我们自己的 ablation** |
| U6 | **DPO 在我们这种"构造偏好对"上的收益** | 决定值不值得做 | 没找到与本题同构的公开实验；只能给"通常有限"的推断 |

---

## 10. 来源

**TypeSafe / Jev（一手）**
- TypeSafe 官方 AI primer（RLCD 定义、三种后训练路线）：<https://docs.typesafe.ai/introduction/machine-learning-primer>
- TypeSafe 发布文 *Introducing System One Models & Jev*（并行采样、每答案带校准概率、RLCD）：<https://typesafe.ai/blog/introducing-system-one-models-and-jev>

**Jev 类模型的开源实现（一手：模型卡 / 代码）**
- Laya（RLCD 机制、`[MASK]` 打分头、指标、布尔标签警告）：<https://huggingface.co/convaiinnovations/laya> · 代码与 `laya-train`：<https://github.com/NandhaKishorM/laya>
- Kev-4B（pointer head、CE over options、硬标签、缺证据用 uniform 目标、温度 T=2.41）：<https://huggingface.co/jaredpalmer/kev-4b> · <https://github.com/jaredpalmer/kev>
- Intern-Decision（autoregressive masked LM 目标、全词表 CE、推理受限符号 + 拟合温度）：<https://huggingface.co/internlm/Intern-Decision-0.8B> · <https://github.com/InternLM/Intern-Decision>
- system-one-270m（单 token 字母位打分、log score + RPS、温度网格）：<https://github.com/Akicou/system-one-270m>（`train.py`、`docs/jev-system-one.md`）
- 候选 token logprob 路线的适配器（说明"任何 LLM + 约束候选集"也能做 Jev 形状）：<https://github.com/quaeast/vllm2jev> · <https://github.com/githubnext/localjev>

**论文**
- *Just Ask Jev*（Jev = RLCD 训练的零样本失效检测器；阈值需本地拟合）：<https://arxiv.org/abs/2609.29429>
- *Calibrated Decision Models for Autonomous Penetration-Testing Harnesses*（RLHF / RLAIF / RLCD / RLHV 逐条比较；RLCD 用严格 proper scoring rule）：<https://arxiv.org/abs/2609.28940>
- RLCD = Reinforcement Learning from Contrastive Distillation（ICLR 2024，**另一个** RLCD）：<https://arxiv.org/abs/2307.12950>
- Hinton et al., *Distilling the Knowledge in a Neural Network*（软目标）：<https://arxiv.org/abs/1503.02531>
- Müller et al., *When Does Label Smoothing Help?*（硬标签 → 过度自信；平滑改善校准）：<https://arxiv.org/abs/1906.02629>
- Guo et al., *On Calibration of Modern Neural Networks*（CE 训练偏过度自信；温度缩放）：<https://arxiv.org/abs/1706.04599>
- Stanton et al., *Does Knowledge Distillation Really Work?*（学生匹配不上教师分布）：<https://arxiv.org/abs/2106.05945>
- Rafailov et al., *Direct Preference Optimization*：<https://arxiv.org/abs/2305.18290>
- Luo et al., *An Empirical Study of Catastrophic Forgetting in LLMs During Continual Fine-tuning*（通用指令数据可缓解后续遗忘）：<https://arxiv.org/abs/2308.08747>

**独立复现（第三方，非官方）**
- Jev RLCD 独立复现（F1@0.5 = 0.158 vs 拟合阈值 0.947）：<https://github.com/jkf87/jev-rlcd-replication>

**仓内**
- [target-provenance.md](target-provenance.md)（每个 target 的语义溯源、可比性矩阵、校准可用性、`target_type` 回填提案）
- [CONTRACT.md](CONTRACT.md)（字段契约、真值形态判别、score 键口径陷阱）
- [survey.zh.md](../../research/PoL2-Jev-Typed-Literature-Survey/docs/survey.zh.md)（Jev 类文献综述与负面结果）
- [CATALOG.md](../../models/CATALOG.md)（候选模型与训练路线）

---

## 附：修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-06 | 首版。回答 6 个问题；给出形态路由、候选打分头、RLCD 两义辨析、最小补救；附本轮只读实测（一致性 / 对齐 / 基数 / 措辞风险）。未改动任何数据文件。 |
