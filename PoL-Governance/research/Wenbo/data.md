## 1) 结论

**结论：有，而且这两周刚好出现了一批非常贴近 Jev / System One 的公开数据集。置信度：高。**

截至 **2026-09-30**，我认为你们已经不需要从零构造一个“大型通用决策数据集”。更合理的是建立一个分层的 **PoL Decision Base**：

**System-One 原生决策数据 → 真人判断/概率校准数据 → 通用伦理与安全数据 → PoL/EAP 专门数据。**

其中最值得认真看的四个是：

| 数据集 | 规模 | 数据性质 | 我对 PoL 的判断 |
|---|---:|---|---|
| **Jev Decisions v1** | 11.98M | Agent 决策/工具选择/Value | 最大的底座，但不能裸吃 |
| **Jev Distill Corpus v3** | 740,957 | `noul/choice/score` 概率分布 | **目前最贴近你们需求** |
| **Open-Jev** | 113,568+ | 可复现、受控、System-One 原生 | **质量/工程规范最好之一** |
| **jev-bench** | 166,054 | 真人标注，部分有多人概率分布 | **校准价值极高，尤其重要** |

与此同时，用 ETHICS、HelpSteer2、ProsocialDialog、Social Chemistry、Moral Stories 等补足“人类判断与伦理语义空间”。

我不建议把 12M Jev Decisions 直接当最终训练集。它看起来壮观，但 **78.22% 的数据来自 Open-SWE，全部 Value supervision 也来自 Open-SWE**，模型很容易被训练成一个异常热爱软件工程的决策官僚。:chatgpt-content-reference{index="0"}

---

## 2) First principles

Jev 本质上不是“更小的聊天 LLM”，而是：

> `state + typed questions → probabilities / decisions`

TypeSafe 在 2026 年 9 月 15 日发布 Jev，把输出分成类似 `Noul / Choice / Score` 的有界决策，并强调 **calibrated probabilities**。也就是说真正需要学习的不是“写漂亮答案”，而是 **在给定状态和候选决策时，形成可靠、可校准的概率判断**。:chatgpt-content-reference{index="1"}

这和你们 PoL 工程事实上相当契合。项目文档本身已经把治理层定义成一种“智慧导航仪/安全阀”，需要识别输入输出中的不同性质，然后进行治理决策；EAP 也明确要求 PAI 同时识别爱与恨，而不是简单生成一段“看起来有爱”的文字。:chatgpt-content-reference{index="2"} :chatgpt-content-reference{index="3"}

所以你们真正缺的不是传统 instruction corpus，而是：

**state → 判断维度 → 候选 → 概率 → 行动/结果**

这种数据。

---

## 3) 调研结果

### A. Jev Distill Corpus v3：目前最值得直接拿来做实验

这是我这一轮调研里最接近“你说的高质量通用 Jev 数据底座”的东西。

**740,957 条，Apache-2.0**，统一成 TypeSafe System One 的：

`noul / choice / score`

三种 primitive，而且 target 不是单纯 hard label，而是**完整概率分布**。:chatgpt-content-reference{index="4"}

组成非常有意思：

- `yuri_v3`：498,010
  - 53 个领域
  - business、technical、agent、knowledge、medical、biology、physics、chemistry 等
  - Noul / Choice / Score 全都有
  - 用 **Jev 1.13** 做 teacher distillation
- `yuri_v1`：148,154
  - 18 个开放 QA 数据源
  - 主要训练 memory relevance / 判断相关性
- `openjev_v2`：94,801
  - 来自 Open-Jev

它还做了：

- 概率 normalization
- exact duplicate 去重
- 极端 degenerate teacher label 过滤
- privacy / secret pattern scanning

[Jev Distill Corpus v3](https://huggingface.co/datasets/SargeDev/jev-distill-corpus-v3)

**优点：**

它可以几乎原样变成你们模型的第一阶段训练集。如果最后模型就是 encoder / 小 Qwen + decision heads，这个 schema 非常舒服。

**最大问题：teacher contamination。**

498k 核心数据其实是在学 **“Jev 1.13 怎么判断”**，不是直接学习“现实世界正确概率”。

这两者不能混为一谈。

所以我会把它称为：

> excellent behavior prior，not ground truth.

如果将来 PoL 与 Jev teacher 在伦理上产生冲突，你们必须允许 PoL 数据覆盖 teacher，而不是反过来。

---

### B. Open-Jev：规模没那么变态，但工程质量很高

`ZefanCai/Open-Jev`

它明确说自己与 TypeSafe 无关，而且不是 TypeSafe/Jev 官方训练数据。这个诚实程度在今天的数据集生态里已经算稀有物种了。

其核心：

`release-v2-redistributable`

大约：

**113,568 条**

其中 train：

**79,116**

并且专门设计了：

- train
- calibration
- validation
- test
- OOD :chatgpt-content-reference{index="6"}


此外它还有 browser/drone、citation、entity alignment、amount extraction、email selection、phone extraction、context retention 等决策任务。

最重要的是它对：

- provenance
- hash
- dataset reconstruction
- license
- split leakage

处理得非常认真。

比如 Wikispeedia 的 2,253 条，因为无法确认原始数据的再分发许可，作者干脆从 redistributable 版本里排除了，而不是“互联网有的东西当然都属于我”。:chatgpt-content-reference{index="7"}

[Open-Jev 数据集](https://huggingface.co/datasets/ZefanCai/Open-Jev)

我的判断：

**它非常适合成为 PoL 数据 schema 和评测体系的参考模板。**

不一定靠它撑规模，但应该借鉴它的：

`group_id + OOD + calibration split + provenance + target distribution`

---

### C. Jev Decisions v1：12M，真正的大型底料

这个就是你们所谓“较大的数据集作为基底”里最夸张的一个。

规模：

**11,978,080 usable records**

其中：

- Choice supervised：6,214,185
- Value supervised：9,369,747
- Completion：48,293
- Score：**0**
- unique trajectories/tasks：1,066,352

而且用了 group-aware 94/3/3 split，trajectory 之间没有 train/test overlap。:chatgpt-content-reference{index="9"}

来源是 NVIDIA 的：

- Nemotron-SFT-Agentic-v2
- Nemotron RL Conversational Tool Use
- Nemotron RL Function Calling
- Open-SWE-Traces

统一成：

`state + candidates → target / outcome / eligibility`

[Jev Decisions v1](https://huggingface.co/datasets/samatv256/jev-decisions-v1)

但这里有一个非常关键的问题：

**Open-SWE 占 usable records 的 78.22%。**

Choice 中：

- Open-SWE：58.03%
- Nemotron-SFT：40.84%
- Pivot：1.13%

而所有 Value supervision 都来自 Open-SWE。:chatgpt-content-reference{index="11"}

所以：

**不能全量 uniform training。**

否则对 PoL 而言，你不是训练“通用治理模型”，而是在用 1200 万行数据强行给模型灌输：

> 世界最重要的事情是修 GitHub issue 和选择下一条工具调用。

这对 Agent 层很好，对 EAP 决策层明显不够。

我会从这里**分层抽样 50 万到 200 万条**，作为 decision mechanics / agent control 底料，而不是吃完整 12M。

---

### D. jev-bench：我反而认为它是最有研究价值的一个

`Praveenrajus/jev-bench`

规模：

**166,054 rows**

22 个 config。

关键区别是：

> **Real human-labeled data**

而不是纯 synthetic teacher labels。

其中四个 config 甚至保存了**人类标注者的完整 vote distribution**：

- GoEmotions
- Measuring Hate Speech
- Civil Comments
- ChaosNLI :chatgpt-content-reference{index="12"}


这是极其重要的。

比如：

如果 100 个标注者中：

- 63% 认为 A
- 37% 认为 B

正确监督信号不应该被压扁成：

`A = 1`

更应该是：

`P(A)=0.63, P(B)=0.37`

这才是真正适合 System-One / calibrated decision model 的监督。

[jev-bench](https://huggingface.co/datasets/Praveenrajus/jev-bench)

但是要注意：

**test 必须锁死。**

不要因为它很好就全部拿去训练，然后一个月之后高兴地发现 benchmark 99.8%。这种成就通常被称为数据泄漏。

---

## 4) 第二层：通用“人类判断”数据

仅靠 Jev 社区数据还是不够。因为 PoL 的治理模型不是一个 ticket router。

我认为下面这些应该进入转换池。

**ETHICS**

134,417 条，MIT，包含：

- commonsense
- deontology
- justice
- utilitarianism
- virtue

它是非常标准的伦理分类数据。:chatgpt-content-reference{index="14"}

[Hendrycks ETHICS](https://huggingface.co/datasets/hendrycks/ethics)

非常适合转成：

`state → 哪种行为更符合某原则？`

但不要把 ETHICS 的标签视为 PoL 真理，它只是人类既有伦理判断样本。

---

**Social Chemistry 101**

大约：

**356k annotations / 104k situations**

包含：

- action moral judgment
- care/harm
- fairness/cheating
- loyalty/betrayal
- authority/subversion
- legality
- social pressure

其中大部分只有 1 个 annotator，但有大约 20k 行拥有 50 人共识标注。:chatgpt-content-reference{index="16"}

这部分 50-person subset 对 calibration 很有价值。

但文化偏差也很明显，因为大量数据来自 Reddit 和 ROCStories。

因此不要让模型学成：

> “Reddit 美国网友 = 普遍人类伦理。”

人类已经在这类事情上踩过足够多的坑。

---

**Moral Stories**

底层其实只有约 **12k structured stories**，只是不同任务配置展开之后 HF 显示会达到几十万行，所以不要被 720k 这个数字欺骗。:chatgpt-content-reference{index="17"}

每条包含：

`situation → intention → normative action → consequence`

以及：

`divergent action → consequence`

这一结构反而特别适合 PoL。

因为 PoL 不是单纯判断一句话“善/恶”，而是涉及：

**动机 → 行为 → 对他人/关系造成的结果。**

---

**ProsocialDialog**

这是一个非常值得你们关注的数据集：

- 58k dialogues
- 331k utterances
- 160k unique social rules
- 497k safety labels
- HF 当前 165,681 records
- CC-BY-4.0

目的就是让模型面对 problematic / toxic / unethical content 时，给出 prosocial response。:chatgpt-content-reference{index="18"}

[ProsocialDialog](https://huggingface.co/datasets/allenai/prosocial-dialog)

这和你们 EAP 里“识别恨 → 转化/调控 → 给出建设性行动”非常接近。EAP 本身也明确提出恨语识别、实时矫正和冲突转化。:chatgpt-content-reference{index="20"}

---

**HelpSteer2**

只有 **21,362**，但质量不错。

每个回答有人类打的 0–4 分：

- helpfulness
- correctness
- coherence
- complexity
- verbosity

还有单独的 preference annotation。CC-BY-4.0。:chatgpt-content-reference{index="21"}

这很适合直接转成 Score primitive。

例如：

```text
state = prompt + response

helpfulness: score 0..4
correctness: score 0..4
coherence: score 0..4
```

这就是天然 System-One 数据。

---

### 安全数据

还有三个可以作为“恨/伤害识别能力”的补充。

**BeaverTails**：约 330k QA safety classification，14 类危害，人类标注；但是 **CC-BY-NC-4.0**，非商业限制是个实际问题。:chatgpt-content-reference{index="22"}

**PKU-SafeRLHF**：83.4k preference，helpfulness 和 harmlessness 分开标注，19 harm categories。也是很好的 preference/reward 数据。:chatgpt-content-reference{index="23"}

**WildGuardMix**：86,759 train，其中大约 87% synthetic、11% in-the-wild，包含 benign / harmful / adversarial/jailbreak。需要接受 AI2 Responsible Use 条件。:chatgpt-content-reference{index="24"}

这些非常适合做 **risk / harm / escalation heads**，但不应该成为整个 PoL 模型的价值中枢。

---

## 5) 我会怎么构建你们的数据底座

我现在会把它设计成：

```text
PoL-Decision-Base
│
├── 1. Decision Mechanics
│   ├── Jev Decisions
│   ├── Open-Jev
│   └── Jev Distill
│
├── 2. Human Judgment / Calibration
│   ├── jev-bench
│   ├── HelpSteer2
│   ├── ETHICS
│   └── human-vote distributions
│
├── 3. Social / Ethical Dynamics
│   ├── ProsocialDialog
│   ├── Moral Stories
│   └── Social Chemistry
│
├── 4. Risk / Hate / Harm
│   ├── WildGuard
│   ├── BeaverTails
│   └── PKU-SafeRLHF
│
└── 5. PoL / EAP
    ├── Love2 / Hate2
    ├── equality
    ├── love-language
    ├── harm / barbarism
    ├── love-hate-neutral
    ├── intervention decision
    └── action policy
```

你们自己的工程策略实际上已经明确提出：不要试图把原 LLM 全部重训掉，而是利用既有智慧，抽取/构造适合 NaturalDAO 的知识、Agent 和 Skill。:chatgpt-content-reference{index="25"}

这与上面这个设计是高度一致的。

---

## 6) 一个更重要的判断：不要把这些数据全部转换成 DPO

这是我认为整个项目接下来最容易走歪的一点。

如果最终目标是一个 Jev-like governance model，那么：

```text
chosen / rejected
```

只是其中一种数据。

更理想的统一 schema 应该是：

```json
{
  "state": "...",

  "questions": {
    "contains_harm": {
      "type": "noul"
    },

    "interaction_type": {
      "type": "choice",
      "options": [
        "love",
        "hate",
        "neutral",
        "uncertain"
      ]
    },

    "harm_severity": {
      "type": "score",
      "levels": [0,1,2,3,4]
    },

    "recommended_action": {
      "type": "choice",
      "options": [
        "allow",
        "respond_prosocially",
        "deescalate",
        "warn",
        "escalate"
      ]
    }
  },

  "targets": {
    ...
  }
}
```

真正宝贵的是：

**一个 state 同时产生多个相互正交的 decision heads。**

比如同一句话：

```text
“我恨他，但我不会伤害他，我只是想离开。”
```

不能简单：

`hate = true → block`

而应该同时输出：

```text
negative emotion      = 0.94
violent intent        = 0.04
harm to other         = 0.08
need intervention     = 0.11
boundary assertion    = 0.87
prosocial response    = 0.91
```

这才真正符合你们 EAP 所强调的：“爱恨不直接等同于好坏”，以及平等对待人不等于无差别评价行为。:chatgpt-content-reference{index="26"}

---

## 7) 反方观点：为什么不直接用 12M Jev Decisions？

这是一个很合理的反驳：

> 既然有 1200 万条，直接预训练，再拿 PoL 数据微调不就行了？

**在 Agent/action selector 场景下，这可能成立。**

例如你们以后训练：

- 是否调用某个 Skill
- 选择哪个 API
- 下一步执行什么动作
- 是否结束 trajectory

那么 Jev Decisions v1 很强。

但是对于：

- 人际关系
- 爱/恨
- 冲突
- 公平
- 公共利益
- 社会治理
- 危害
- 伦理权衡

它的分布差得太远。

所以如果全量 12M 预训练，后面只有 5 万 PoL 数据，可能发生的不是“PoL 赋予通用模型价值观”，而是：

**12M 旧任务先定义 representation，5 万 PoL 只是在表面修一下 decision boundary。**

特别是小模型更明显。

因此我的建议恰好相反：

> **不是以样本量决定权重，而是以 information value 决定 sampling weight。**

---

## 8) 一个实际可执行的第一版配方

如果现在让我做 `PoL-Decision-Base-v0.1`，我不会追求 2000 万条。

我会先控制在 **约 150 万～300 万 decision records**。

训练初期 sampling weight 大致：

| 数据类型 | 初始权重 |
|---|---:|
| 通用 System-One / decision mechanics | 40–45% |
| 真人 judgement + calibration | 20–25% |
| social / moral / prosocial | 15–20% |
| harm / safety / adversarial | 10–15% |
| PoL/EAP 专门数据 | 初期 10%，后期提高到 30–50% |

注意这不是“原始行数比例”。

比如 Jev Decisions 即使有 1200 万，我可能也只采 50～100 万。

而你们自己最终只有 10 万条高质量 PoL 数据，我反而会**过采样很多次**。

---

## 9) SFT 和 RL 应该分开考虑

如果你们下一步是 **SFT / adapter**：

最重要的：

- Open-Jev
- Jev Distill
- jev-bench train
- ETHICS / HelpSteer2 / Prosocial 转换集
- PoL

用：

- KL / soft cross entropy
- ordinal loss
- Brier-style calibration objective

而不是传统 next-token loss 为主。

如果下一步做 **RL / RLCD-like**：

Jev Decisions v1 的价值明显上升，因为它包含 trajectory/outcome/value 类 supervision。

但 ETHICS、Social Chemistry 这种静态数据并不能凭空变成真正 RL 环境。

它们更适合作为：

```text
reward / judge / critic supervision
```

然后真正的 RL 再跑：

```text
scenario
→ decision
→ environment outcome
→ reward
→ policy update
```

---

## 10) 最大的不确定性

这里现在最大的问题不是“数据够不够”。

**数据已经够多了。**

最大问题是：

### 谁的概率是真实概率？

Jev Distill：

> Jev teacher 的概率。

它代表 teacher belief。

Social Chemistry：

> annotator judgment。

代表特定文化样本人群。

ETHICS：

> dataset-defined norm。

代表特定伦理框架。

PoL：

> 你们定义的 EAP。

代表另一套明确的治理框架。

它们不是同一个东西。

所以千万不要简单：

```python
concat(all_datasets)
shuffle()
train()
```

然后期待“集体智慧自然涌现”。

通常涌现出来的是统计平均意义上的浆糊。

---

## 下一步

我认为现在可以直接进入数据工程阶段。

第一步不是先造 PoL 数据，而是先制定一个统一的 **`PoL Decision Schema v0.1`**，兼容 Jev 的 `noul / choice / score`，然后把：

**Jev Distill + Open-Jev + Jev Decisions + jev-bench + ETHICS + ProsocialDialog + HelpSteer2**

转换成同一种格式。

其中我会暂时把 **Jev Distill Corpus v3 + Open-Jev + jev-bench** 作为核心三件套：

**Distill 提供规模，Open-Jev 提供规范，jev-bench 提供真人校准。**

然后再把你们自己的 PoL/EAP 数据作为真正的“价值方向层”，而不是让它承担从零教会模型“什么叫决策”的苦力。这种分工会干净得多，也更容易分别做 SFT、reward model、DPO 和后续 RL。