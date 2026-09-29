# PoL2 × Jev 类型化决策模型：文献综述

> **性质**：本文是爱2证明（PoL2）理论的参考文献整理，不是 PoL2 正文，也不代表协作者的共同立场。凡标 ★ 的判断，属于需要团队讨论确认的建议。
>
> **检索截止**：2026-09-29（香港时间）。Jev 于 2026-09-15 发布，本文收录的研究全部出现在发布后的两周之内，绝大多数是未经同行评审的预印本。
>
> **整理者**：鄢申涛 Shenton（在 Claude 协助下完成检索、归类与初稿）。

---

## 0. 为什么 PoL2 需要关注 Jev

PoL2 的工程策略（正文第 3.4.1 节）要求在大模型之内建立一个"内置的共识治理层"，其中包括两个部件：

- **智慧导航仪**：依据伦理对齐协议（EAP）扬爱抑恨的要求，决定爱恨智慧的调拨；
- **安全阀**：对输入和输出进行"严格的动态审计与拦截"，使恨语在必要时从输入端被阻断、从输出端被抑止。

第七章《人类公共福利的治理协议》进一步要求 NaturalDAO 做到：异常检测与风险预警（第七条）、提供"可验证的决策链路，包括数据源、推理步骤、伦理依据"（第五条）、对人类的质询"提供可理解的解释和依据"（第九条），以及由 AI 做"事实分析与伦理评估"来裁决争议（第十条）。

这些要求有一个共同点：**需要在每一次输入、输出、决策上都做一次快速、结构化、可被代码直接执行的判断。** 用生成式大模型逐条做这种判断，又慢又贵，而且它输出的是文字，不是可以直接接入治理流程的结论。

Jev 是 TypeSafe AI 发布的、官方称为第一个的"System One 决策模型"：它不生成文字，只对调用方给定的问题返回三种类型化答案——选择（Choice）、分级评分（Score）、是非概率（Noul），并声称这些概率经过校准（RLCD，Reinforcement Learning for Calibrated Decisions）[T1][T2][T4]。官方称单次判断 70–500 毫秒，每百万输入 token 0.042 美元 [T2]。从形态上看，它几乎就是为"安全阀"这类部件量身定做的。

**但这正是需要文献把关的地方。** 下面的研究共同表明：Jev 在一些判断上又快又便宜，但它的"类型安全"不等于"判断正确"，它的"校准"不等于"可以直接当阈值用"，它对注入攻击也并非免疫。对一个要求公开透明（第七章第四条）、要求 PAI 做认知校准与行为自省（5.3.3.1）的治理框架来说，这些限制比它的优点更需要被看清楚。

---

## 1. 对照框架：PoL2 条款 × 工程问题 × 文献

| 编号 | PoL2 正文依据 | 要回答的工程问题 | 主要文献 |
|---|---|---|---|
| **G1** | 3.4.1 安全阀：输入输出的动态审计与拦截 | 决策模型能否可靠地发现 AI 的对齐失效和越界行为？ | [P-29429] [P-34862] [P-23959] [P-22664] [P-28940] |
| **G2** | 3.4.1 安全阀；5.3.3.1 恨语截断 | 安全阀自己会不会被注入、被语境带偏？ | [P-28613] [P-30243] [G-CheckPoint] |
| **G3** | 5.3.1 平等联结；5.3.2 扬爱抑恨；第五章"语义识别和情绪识别相结合"一节 | 决策模型的语义判断是否公平、是否被选项措辞或语言左右？ | [P-26758] [P-24574] [P-35293] [G-Simmons] [G-ZhBench] |
| **G4** | 5.3.3.1 PAI 自我对齐：认知校准、行为自省 | 模型报出的概率是否诚实？它会不会说"我不知道"？ | [P-35342] [P-33209] [P-24052] [P-24881] [A-RAG] [G-Molas] [G-Bernoulli] |
| **G5** | 第七章第四、五、九条：公开透明、可验证决策链路、解释义务 | 只给数字、不给理由的判断，如何满足可审计与可解释？ | [P-24965] [P-27678] [P-32160] [G-Willison] |
| **G6** | 第七章第九、十条：人类质询与监督、争议裁决 | "高置信自动执行、低置信交给更强的模型或人"这种分层是否真的可靠？ | [P-26550] [P-29769] [P-26532] [P-27607] |
| **G7** | 第七章：公共福利治理；3.6 公共决策的评估维度 | 在公共事务规模上用决策模型做判断或模拟，需要什么样的诚实条款？ | [P-27535] [P-24052] [P-28919] [P-30216] |

文献编号规则：`P-xxxxx` 为 arXiv 论文（2609.xxxxx），`A-` 为仅发表在 alphaXiv 的论文，`G-` 为灰色文献（博客、技术报告、开源仓库，未经同行评审），`T` 为 TypeSafe 官方资料。完整目录见第 5 节和 [`data/papers.csv`](../data/papers.csv)。

---

## 2. 按治理条款梳理

### G1 安全阀能否发现问题：对齐失效与越界行为检测

**最直接相关的一篇是 *Just Ask Jev* [P-29429]。** 作者构建了 RLCDAlignBench，覆盖十类对齐失效：谄媚、越狱、欺骗、提示注入、幻觉、隐私侵犯、社会偏见、奖励投机、隐瞒不确定性、权力寻求，共 44 个基准、5 个目标模型。只用一个通用问题、不做任何训练，Jev 的 AUROC 中位数就达到 0.886，在多数基准上超过有监督基线，成本约为 LLM 评判器的 1/63。

这十类里至少有四类可以直接对应 PoL2 的恨语概念：谄媚与欺骗（虚假的爱的表达）、隐瞒不确定性（对 PoL2 诚实原则的违反）、权力寻求（与"平等联结"相悖的控制意图）。

但这篇论文有三个结论对 PoL2 尤其重要：

1. **问法影响小，给模型看什么影响大。** 很多失效是"关系性"的，只有对照参照物（用户原本的信念、被注入的指令）才能判断，单看回应本身看不出来；作者也注明，上下文的作用主要来自那些本身就编码了标签的字段 [P-29429]。对安全阀的含义是：审计时必须把上下文一起交给判断模型，只审输出是不够的。
2. **排序好不等于阈值好。** 独立复现者 jkf87 用 1,155 条数据重跑了论文的五个子实验，结果与原文的差异中位数只有 0.0036；但同时复现出一个关键现象——在 TensorTrust 劫持检测上，按默认阈值 0.5 判断的 F1 只有 0.158，改用校准后的阈值 0.35 才升到 0.947，五个子实验拟合出的最佳阈值没有一个是 0.5 [G-Replication]。
3. 论文还发现它能暴露现有基准自身的标注错误 [P-29429]。

其他几篇从"执行前闸门"的角度提供了补充：

- **Agent 轨迹安全评判** [P-34862]：在四个基准共 5,219 条工具调用轨迹上，用同一套风险标准做事后分类。Jev 的正类 F1 平均为 77.8，高于最强生成式评判器 GLM-5.2 的 74.1，有效结果覆盖率 95.5%；但各数据集互有胜负。每次有效判断的估算成本约 0.000195 美元。作者的定位是"经济的筛查信号"，在精确率与召回率之间有取舍。
- **诈骗电话筛查** [P-23959]：用开源的 JevLite（Qwen3-4B 微调）在每一轮对话后给出诈骗概率，AUROC 0.974、校准误差 0.052，对正常来电零误报，且在相同挂断规则下比 LLM 评判器早 1.14 轮做出判断。这是"安全阀需要在对话进行中实时判断"的一个可操作样例。
- **自主渗透测试的保障框架** [P-22664] [P-28940]：作者认为这类 Agent 只按"能力"评测是不够的，还必须回答三个保障问题——发现的漏洞是否真实、Agent 是否停留在授权范围内、操作者能否审计它做了什么，并据此提出五项保障属性；在一个开源实现上直接执行授权与审计验收测试，发现了真实的授权执行缺口 [P-22664]。同一作者的后续论文对比了有无 Jev 判断层的各一次运行，作者明确说明这是探索性案例，不构成统计显著的结论 [P-28940]。这里的"授权范围"与 PoL2 第七章"人类保留监督权"的边界意识是同一类问题。

> **对 PoL2 的含义**：决策模型作为安全阀的"探测器"是有证据支持的，尤其在速度和成本上足以做到对每一次输入输出都审计。但阈值必须按任务、按数据单独拟合，不能沿用默认值。★ 建议 NaturalDAO 为每一类恨语审计单独建立带人工标注的校准集。

### G2 安全阀本身会不会被攻破：注入与语境翻转

这是目前证据最一致、也最值得警惕的一组。

- **Decision Hijacking** [P-28613]：在 510 个重构的 InjecAgent 攻击案例上，恶意内容会改变 Jev 的动作概率，但很少能让它真正选中攻击者想要的目标；利用分数反馈的自适应攻击，把新样本上的成功率从 1.8% 提到 3.5%。作者的结论是：**schema 约束的输出改变了注入风险的形态，但没有消除它。**
- **JevOut** [P-30243]：作者借助模型自身的选项概率反馈，优化出读起来毫不违和的背景短句。在正确答案不变的前提下，这些短句把 508 个原本答对的决策中的 312 个（61.4%）翻转到指定的错误选项；其中 229 个案例里，Jev 给错误选项的概率不低于 0.7。另外三个决策系统的翻转率在 64.9%–73.2% 之间。**看似平常的语境，就能把正确判断变成高置信的错误判断。**
- **Check Point 的多轮攻击实验** [G-CheckPoint]：用一个会多轮自适应的攻击 Agent，九种"攻击者 × 难度"组合全部至少攻破一次；最强的攻击者在 27 次中攻破 25 次，平均第 4 轮得手，每次成功的成本约 0.5 美元。把文档标为"不可信"、加入反注入指令，几乎没有效果。对照的生成式模型打开推理设置后，攻破成本从 0.54 美元升到 4.39 美元，而 Jev 没有这个设置。该报告自己强调这是单一应用的方向性研究，不是基准。
- TypeSafe 官方文档也承认"对抗性内容"是 jev-1.13 已知的失效模式之一 [T3]。

> **对 PoL2 的含义**：PoL2 正文把安全阀设计成"从输入端阻断恨语"。上面的证据说明，如果安全阀本身就是一个会被输入内容影响的模型，那么**恨语恰恰可能通过它要审计的那段输入来操纵它**。★ 建议：安全阀不应是单一模型的单点判断；关键的阻断决策至少需要两个独立来源（不同模型，或模型加规则）一致，并保留人工复核通道。

### G3 语义判断是否公平：平等联结与扬爱抑恨

PoL2 的平等联结原则要求 PAI"平等对待每一个人"（5.3.1），扬爱抑恨则依赖对爱语与恨语的准确语义识别（5.3.2，以及第五章"语义识别和情绪识别相结合"一节）。这组文献检验的正是决策模型在语义判断上的偏差。

- **Type-Safe Is Not Error-Free** [P-26758]：**这是本综述中最重要的一个负面结果。** 作者只做了一件事——把两个选项的名字从 `0/1` 换成 `no/yes`，其他完全不变。在两个开源权重的 Jev 类模型上，每 100 个答案里多出 70.4 个发生改变（95% 置信区间 67.6–73.1），AUC 从 0.94 翻转到 0.23，是系统性的反转而不是随机波动；选项越多，效应越强。闭源的 Jev 也表现出同样的行为：AUC 从 0.81 降到 0.58，翻转次数是其重复测试噪声的 24 倍。而在所有条件下，类型错误率始终为 0%——**输出格式永远合法，判断却可以整体颠倒**。标题概括得很准确：**模型跟随的是选项的名字，而不是绑定在选项上的定义。**
  对 PoL2 来说，这意味着"爱语 / 恨语"这些选项本身的措辞，可能比我们写给它的判断标准更能左右结果。PoL2 协作中一向重视术语的审定，这篇论文从工程上说明了术语为什么重要。
- **强迫选择下的群体偏见** [G-Simmons]：允许拒答时，Jev 对"X 群体比 Y 群体更 [美丽 / 有领导力 / 文明 / 有道德]"这类陈述，只有约 3% 的情况回答"是"。但一旦强迫它二选一，在美丽、领导力、文明、道德这几项上，"白人"占了 51% 的首选；性别测试中，本应互补的两个概率加起来只有 0.11，连一个一致的排序都构不成。这是一篇个人博客，方法未经同行评审，但它指向的问题正是平等联结要防止的：**当接口强迫模型在人群之间做选择时，偏见会以"类型安全"的形式被输出。**
- **计算社会科学的文本标注** [P-24574]：在 18 个标注任务（7,977 条）中的 15 个评测任务上，决策模型有 14 个落后于表现最好的大模型，宏 F1 中位数低 11.6 个点，但成本低 44 倍。它的置信度比 19 个大模型中 16 个的"口头置信度"更校准，但仍不如三个前沿模型。**与 PoL2 最相关的一个细节**：在"同伴支持对话中的共情"这一任务上，模型报告高置信度，实际表现却接近随机。作者的建议是把决策模型作为标注流程的第一步，低置信的条目交给大模型，可以用四分之一到一半的成本达到或超过只用大模型的效果。
- **中文场景** [G-ZhBench]：中文实测 ZH-Decision-Bench 发现，决策模型的过度自信在中文上是系统性的（重新拟合的温度系数全部大于 1，在 1.33 到 5.70 之间）；被测的开源决策模型（据追踪库记录为 Laya 多语种 322M 版本）在选项顺序调换后有 28% 的答案翻转，简繁体切换有 12.8% 翻转（对照的 Qwen3.5-2B logit 读出分别为 0% 和 2.2%）。TypeSafe 官方也说明英文是主要语言，中日韩文字"能处理但效果不等同" [T2]。PoL2 的正文以中文写成、面向全人类，**语言上的不平等本身就是平等联结需要面对的问题**。
- **细粒度情感分析** [P-35293]：把 SemEval-2026 维度情感分析的三个子任务全部拆成类型化问题，不生成文本、不微调骨干，只在 CPU 上拟合 488 个系数，就在六种语言、十个语料的效价-唤醒度回归上取得参赛系统中最低的总误差。作者也指出，有监督的校准把原始回归误差降低了约一半——**不经本地校准的原始分数并不可直接使用**。

> **对 PoL2 的含义与一处需要团队讨论的张力** ★：
> 伦理对齐协议 5.3 节明确写道，PAI"可以通过判断人类的行为模式提供帮助和必要的友好的管理，但毫无必要让 PAI 检测一个人的情感状态"，因为情感状态转瞬即逝、因人因境而异，"甚至这还涉及到人类的尊严"。而正文另外两处又有不同的表述：5.3.3.1 要求 PAI"需要理解人类情绪状态和过程，但不需要模拟人类的情感体验"；第五章中标为"3.3.3"的"语义识别和情绪识别相结合"一节（编号疑为笔误）则把情绪识别列为技能开发的方向。决策模型让"对每一句话打一个情绪分"变得极其便宜，会放大这一张力。建议团队明确"理解情绪"与"检测个人情绪状态"的边界，例如：**对人，只判断行为与语义，不检测个人情绪状态**；情绪识别只用于 PAI 审计自身输出。另外，[P-24574] 发现决策模型恰恰在"共情"判断上高置信而接近随机，这也提示情绪类判断目前最不可靠。

### G4 模型是否诚实：校准与"我不知道"

PoL2 对 PAI 自我对齐的要求包括"认知校准"和"行为自省"（5.3.3.1）。在决策模型上，这对应一个可以检验的问题：**它报出的概率是否如实反映了它有多大把握？** TypeSafe 用 RLCD 训练的正是这一点，但官方只公开了目标，没有公开方法和数据 [T1]。

支持的证据：
- 在 WiC 语义判断的 3,066 对样本上，Jev 的期望校准误差 ECE 为 0.027，几乎每个区间都在抽样误差范围内 [G-Grazian]。
- 在警方车祸叙述转码任务上，作者用 2,416 条盲审人工判断审计了 Jev 的概率，结论是校准因模型而异、每个模型都必须单独审计；用同一批标签重新校准后，校准误差降到原来的 1/3.3 [P-24052]。

反对或限定的证据：
- **"Jev 在想'我不知道'，但没有说出来"** [P-35342]：作者构造了一个真值概率已知的是非题数据集 Sys1Cal-v1，用三种原语分别提问。作者观察到一种特殊行为，并提出一个解释性假设：Jev 在 Choice 答案里把 P(A) 和 P(非 A) 表现得好像二者之和等于 1，实际上却缺了一项 P(U)——一个被压下去的**第三个真值："不知道"**。按这一假设把该项找回来，Choice 答案的软准确率中位数从 0.771 升到 0.978。
  如果这一假设成立，它与 PoL2 伦理对齐协议 5.3.2 中"理解和接受不在场的'非爱非恨'状态"惊人地相合：二元的爱 / 恨判断之外，必须为"不在场"留出位置。**如果问题只给"是 / 否"两个选项，模型的"不知道"就会被强行分摊到两边。**
- **概率是否遵守概率公理** [P-33209]：不需要标签，只检验逻辑相关的问题之间概率是否自洽。在 480 对"标签是 X / 标签不是 X"的问题上，Jev 两个概率之和平均偏离 1 达 0.064（95% 置信区间 0.055–0.072），好于开源 Qwen3.8-27B 的 0.293（首 token 读出）；但它的违背幅度约为自身重复噪声的五倍，而且会过度认可单一标签——三个互斥标签的概率加起来平均是 1.14。它的不一致集中在自己不确定的地方。
  官方文档自己就给出过一个例子：对同一张工单分别用两个 Noul 问"是退款请求"和"不是退款请求"，概率为 0.72 和 0.47，加起来是 1.19 [T3]。
- **RAG 冲突分类** [A-RAG]：在 453 条留出样本上，最好的提示把五分类准确率提到 65.3%，但**错误答案的平均置信度始终在 0.56–0.58**，偶尔高达 0.99–1.00；提示改进能提高正确答案的置信度，却从没让模型在答错时变得不确定。作者的结论是：置信度只是一个"有损的错误过滤器"。
- **作为外部校准器** [P-24881]：这篇论文提出的是一个专门估计黑盒大模型回答是否正确的方法 Pinocchio（AUROC 0.862）；据追踪库对其附录的摘录，把 Jev 1.13 当作现成工具做同一件事，在 1,718 条回答上 AUROC 只有 0.666，而 Pinocchio 在相同样本上为 0.868。
- **校准依赖数据分布** [G-Molas]：一个统计学上的论证——模型在 TypeSafe 的数据分布上校准，不代表在你的分布上也校准，因此应当把 Jev 的输出当作"分数"而不是"概率"。
- **置信度公式本身的问题** [G-Bernoulli]：在 76,807 个二选一答案上反推出官方的置信度公式后，作者发现：往选项列表里加零概率的空选项，就能把置信度从 0.20 抬到 0.58；完全相同的请求重复十次，置信度在 0.84 到 0.88 之间浮动，平坦问题上连胜出的标签都会以 7:2 的比例翻转。
- 在车祸叙述任务上，用同一批人工标签重新校准后，校准误差下降到原来的 1/3.3；作者强调**校准因模型而异，每个模型都必须单独审计** [P-24052]。

> **对 PoL2 的含义**：PoL2 把诚实放在核心位置，而上述研究说明，"经过校准训练"不等于"在你的问题上诚实"。**模型不会主动说"我不知道"，需要治理层替它说。** ★ 建议：NaturalDAO 的任何自动执行都以本地校准集上的实测为准，而不是以模型自报的置信度为准；并把"模型拒绝判断 / 证据不足"作为一个显式选项写进每一个问题。

### G5 可验证决策链路与解释义务

第七章第五条要求 NaturalDAO 提供"可验证的决策链路，包括数据源、推理步骤、伦理依据"；第九条要求对人类的质询"提供可理解的解释和依据"。决策模型在这一点上有结构性的不足。

- **只有数字，没有理由** [G-Willison]：Simon Willison 的评论切中要害——大模型本来就是黑箱，但至少可以要求它说明理由；Jev 只返回一个浮点数，是什么信号促成了一个"垃圾信息"的判定，完全不可见。他因此认为偏见问题应当被放在首位，并希望没有人用它给求职者排序。
- **最终结论对了，不代表中间判断对了** [P-24965]：在 10 个科学案例、20 个语义选择上，Jev 与另外五种配置都做到了语义选择全对；但三个对照模型的 7 次错误中间选择改变了下游计数，却没有改变最终结论标签。这篇论文的价值不在于 Jev 犯了错，而在于它说明了：**只看最终准确率会掩盖中间错误**，审计必须检查链路上每一个被复用的判断与数量。
- **分数相同，决策不同** [P-27678]：在合同推理任务上，按平均准确率排名和按"逐条、多次重复都答对"排名，结果在每种条件下都不一样；而且"多次答得一致"本身也不够——模型可能每次都一致地答错。
- **早期证据审计与评估清单** [P-32160]：对 9 月 19–24 日的 28 篇论文做了系统审计，结论是：在这批早期文献中，**类型化读出本身并未显示出比同类"标签概率读出"更高的独立准确率优势**；Jev 最清楚的优势是延迟与成本，较难任务上仍有准确率差距；实际部署中置信度常被用来决定何时交给更强的模型或人。作者据此提出一份 14 项的评估清单，并强调这只是发布后九天的"早期证据地图"。

> **对 PoL2 的含义**：决策模型能提供的"链路"，是"哪个问题、看了哪些字段、给出什么概率"，这对审计是有用的（每个判断都可以被逐条记录、回放）；但它不能提供"推理步骤"和"伦理依据"。★ 建议：在 NaturalDAO 中，决策模型只作为链路上的一个**可记录的节点**；需要向人类解释的决定，其依据必须由另一层（规则、引用的 EAP 条款，或生成式模型的说明）给出，并与决策模型的输出一起上链存档。

### G6 人类监督与争议裁决：分层升级是否可靠

第七章把争议裁决交给 AI（第十条），同时保留人类的质询与监督权（第九条）。工程上最常见的做法是分层：**高置信的判断自动执行，低置信的交给更强的模型或人。**

- **支持的证据** [P-26550]：与 16 个生成式和奖励模型评判器比较，并有盲审的人工裁决。凡是结论能直接从文本读出的判断，Jev 与 GPT-6 相差不超过 3 个百分点，费用是后者的 0.36%，中位延迟 0.15 秒；凡是结论需要推导的（数学、代码、逻辑），Jev 明显落后——而它的置信度恰好标出了这条边界。用事先冻结的阈值，"自信就采纳、不确定就升级"比单用 GPT-6 高 0.9 个百分点，费用为其 41%；在两个新任务的预先设定实测中，级联准确率与 GPT-6 完全持平。但在风格对抗样本和无参考答案的文本上，置信度分流会变弱。（本文依据 arXiv v2 摘要；v1 的表述是"保留 99% 的强模型准确率"。）
- **反对的证据** [P-29769]：在 7 个基准、9 组评测上，Jev 的置信度确实能给自己的错误排序，这本应让分层很有效。但**三个 flash 档 LLM 评判器几乎重复了 Jev 所有最自信的错误**——错误是相关的，不是随机的。按记录下来的判决重放级联，只比最好的单一评判器高出 1.5 个百分点，即使用事后最优阈值也只有 2.0 个百分点。
- **Agent 中的分层控制** [P-26532]：在 100 个冻结任务上成功率 95%，强模型调用减少 72.7%；但可靠性取决于动作集的大小，以及"授权边界附近是否存在几乎合法的选项"。在外部基准上，如果普通的廉价生成式分层已经路由得很准，Jev 的额外收益有限。
- **临床报告评判** [P-27607]：与专家错误计数的 Kendall 一致性为 0.573 和 0.398。

> **对 PoL2 的含义**：[P-26550] 与 [P-29769] 看似矛盾，其实回答的是不同问题，而且比较的对象不同：前者升级给推理型的 GPT-6，并说明"低置信"能标出需要推导的那部分判断；后者升级给同档的 flash 模型，说明"升级给另一个 AI"未必能纠正错误，因为不同 AI 往往在同一处犯错。**这对 PoL2 的争议裁决设计很关键**：如果争议最终只在 AI 之间升级，相关错误会被系统性地保留下来。★ 建议：升级链的末端必须有人类，且人类复核的样本应当包含一部分**高置信**判决的随机抽检，而不只是低置信的那些。

### G7 公共事务规模的判断与模拟

- **KITE：用决策模型扩展群体实验** [P-27535]：对每个唯一状态只调用一次决策模型，再用查表模拟任意规模的人群；昂贵的前沿模型只用于少量锚点来估计干预效应，并**把"人与模型之间的差异"作为共享误差传播到每一个结论里**。在 9,070 名参与者的实验上，覆盖 1.7% 状态的锚点把效应误差降低了 41%。这与 PoL2 协作中的一条工作原则（非正文条款）高度一致：**所有模拟输出都必须带有诚实条款，防止过度推广到真实人群。**
- **公共安全数据** [P-24052]：把警方车祸叙述转成带概率的结构化变量，并用"带门槛的类型化决策"来回答"人工到底需要复核多少"这一此前没有规则可循的问题；作者发现，与已有编码字段的一致性会把真实保真度低估 0.26 kappa（中位数）。
- **企业 Agent 控制平面** [P-28919]：用 Jev 按企业自定的请求分类给每个提示打标签并据此路由；在按真实会话模拟的 10,000 席企业中，回收了 13%–21% 的模型开支。论文还梳理了 21 种 Agent 运行框架的风险，以及对单一供应商的依赖成本——后者与 PoL2"任何大语言模型都可以纳入治理"的去中心化主张直接相关。
- **生态实证** [P-30216]：截至 2026-09-22，GitHub 上有 2,170 个把 Jev 用于具体任务的公开项目；安全与治理类（审核审批、安全合规）共 175 个，关注度远低于路由与自动化类。

---

## 3. 负面结果汇总

PoL2 协作中的一条工作原则（非正文条款）认为，负面结果比确认性结果更有证据价值。以下是本综述中最应当被记住的负面结果：

| 发现 | 来源 | 对应 PoL2 条款 |
|---|---|---|
| 把选项名从 0/1 改成 no/yes：开源 Jev 类模型 AUC 从 0.94 翻转到 0.23，Jev 从 0.81 降到 0.58；类型错误率始终为 0% | [P-26758] | 5.3.2 扬爱抑恨的语义识别 |
| 强迫二选一时，在"美丽 / 领导力 / 文明 / 道德"上"白人"占首选的 51% | [G-Simmons] | 5.3.1 平等联结 |
| 错误答案的平均置信度保持在 0.56–0.58，提示改进不能让模型在答错时变得不确定 | [A-RAG] | 5.3.3.1 认知校准 |
| 三个 flash 档 LLM 评判器几乎重复 Jev 所有最自信的错误，级联最多提升 1.5 个百分点 | [P-29769] | 第十条 争议裁决 |
| 自适应多轮攻击 27 次攻破 25 次；标注"不可信"几乎无效 | [G-CheckPoint] | 3.4.1 安全阀 |
| 默认阈值 0.5 下 F1 只有 0.158，校准阈值下为 0.947 | [G-Replication] | 3.4.1 安全阀 |
| 经概率反馈优化、读来自然的语境短句，翻转 61.4% 原本正确的决策 | [P-30243] | 3.4.1 安全阀 |
| 二元问题中"不知道"疑被压成"是 / 否"；"是 X"与"不是 X"之和偏离 1 | [P-35342] [P-33209] | 5.3.2 非爱非恨的不在场；5.3.3.1 认知校准 |
| 类型化读出尚无独立的准确率优势，优势主要在延迟与成本 | [P-32160] | 整体定位 |
| 中文上过度自信是系统性的；选项顺序调换 28% 翻转 | [G-ZhBench] | 5.3.1 平等联结 |
| 最终标签正确，中间语义选择却是错的（出现在对照模型上，说明只看最终准确率不足以审计） | [P-24965] | 第五条 可验证决策链路 |

---

## 4. 对 NaturalDAO 工程的建议（草案 ★）

以下建议均为供团队讨论的草案：

1. **把决策模型定位为安全阀的"探测器"，而不是"裁判"。** 它负责快速、廉价地标记，最终的阻断或放行由规则、多模型一致或人工复核决定（G1、G2）。
2. **选项措辞与判断标准一同纳入术语审定流程。** 爱语、恨语等选项名本身会左右模型判断，应当像正文术语一样由团队确认，并做"换名测试"（G3）。
3. **对人只判断行为与语义，不检测情绪状态**，与伦理对齐协议 5.3 节保持一致；PAI 对人类情绪的"理解"（5.3.3.1）如何在不检测个人情绪状态的前提下实现，需要团队界定（G3）。
4. **本地校准优先于自报置信度，并为"不在场"留出位置。** 每类判断都建立带人工标注的校准集，阈值按任务拟合；爱 / 恨类问题一律使用三选项（爱语 / 恨语 / 非爱非恨·不在场），而不是二元 Noul（G4）。
5. **决策链路上链存档，但解释由另一层给出。** 记录问题、输入字段、概率与模型版本；向人类解释的依据引用 EAP 条款（G5）。
6. **升级链的末端是人，并对高置信判决随机抽检**（G6）。
7. **优先考虑可自托管的开源决策模型。** Jev 是闭源 API：TypeSafe 未发布模型权重（其官方 GitHub 与 Hugging Face 均无权重，整理者核查于 2026-09-29），RLCD 的方法与数据也只公开了目标层面的描述 [T1]。这与第七章第四条"所有NaturalDAO技术的运行逻辑、决策过程和输出结果必须完全公开透明"存在张力；社区已有多种开源复现可以作为替代或对照（见 [G-Tracker]）。
8. **任何模拟结论都附带诚实条款**，参考 KITE 把人机差异作为共享误差传播的做法（G7）。
9. **用中文做独立评测。** 现有公开评测几乎全是英文（G3）。

---

## 5. 论文目录

完整元数据（作者、日期、摘要、许可证、PDF 状态）见 [`data/papers.csv`](../data/papers.csv)。**PDF 一栏说明**：
- `✅ PDF` 表示该论文采用 Creative Commons 许可，允许转载，PDF 已收入 [`papers/`](../papers/) 文件夹；
- `🔗 仅链接` 表示该论文采用 arXiv 默认许可（arXiv.org perpetual non-exclusive license），只授权 arXiv 分发，第三方不得转载，因此只提供链接。需要本地全文时，运行 [`scripts/fetch_papers.ps1`](../scripts/fetch_papers.ps1) 即可一次下载到被 git 忽略的 `papers/_local/` 文件夹。

<!-- CATALOG:START -->
### 核心（15 篇）：直接对应 PoL2 治理条款

| 编号 | 标题 | 第一作者 | 日期 | 轴 | 要点 | 许可 | PDF |
|---|---|---|---|---|---|---|---|
| P-29429 | [Just Ask Jev: Reinforcement Learning for Calibrated Decisions as a Zero-Shot Detector of AI Alignment Failures](https://arxiv.org/abs/2609.29429) | Ruoqi Guo 等 | 2026-09-24 | G1 | 零样本检测十类对齐失效，AUROC 中位数 0.886 | CC BY 4.0 | [✅ PDF](../papers/2609.29429.pdf) |
| P-34862 | [JEV as a Judge for Agent Trace Security: An Empirical Comparison with Generative LLM Judges](https://arxiv.org/abs/2609.34862) | Zhiqiang Wang 等 | 2026-09-28 | G1 | Agent 轨迹安全评判：5,219 条轨迹上 F1 77.8，高于最强生成式评判器的 74.1 | arXiv 默认许可 | 🔗 仅链接 |
| P-28613 | [Decision Hijacking: Prompt Injection Attacks on Jev's Typed Probabilistic Decisions](https://arxiv.org/abs/2609.28613) | Tiantong Wu 等 | 2026-09-23 | G2 | 提示注入改变动作概率但很少劫持目标；schema 不能消除注入风险 | CC BY 4.0 | [✅ PDF](../papers/2609.28613.pdf) |
| P-30243 | [JevOut: Natural Context Can Flip Decision Models](https://arxiv.org/abs/2609.30243) | Zixiang Xu | 2026-09-24 | G2 | 经概率反馈优化的自然语境短句，可翻转 61.4% 原本正确的决策 | arXiv 默认许可 | 🔗 仅链接 |
| P-26758 | [Type-Safe Is Not Error-Free: A Constrained Decision Head Follows the Option Name, Not the Rubric Bound to It](https://arxiv.org/abs/2609.26758) | Yu Sun 等 | 2026-09-22 | G3 | 选项名 0/1 改 no/yes：开源模型 AUC 0.94→0.23，Jev 0.81→0.58；类型错误率始终 0% | CC BY 4.0 | [✅ PDF](../papers/2609.26758.pdf) |
| P-24574 | [Evaluating Decision Models for Text Annotation in Computational Social Science](https://arxiv.org/abs/2609.24574) | Hazem Ibrahim 等 | 2026-09-21 | G3 G4 | 15 个评测任务中 14 个落后最佳大模型，成本低 44 倍；"共情"任务高置信而近随机 | CC BY 4.0 | [✅ PDF](../papers/2609.24574.pdf) |
| A-RAG | [Can JEV Be Used as a Confident Classifier? A Calibration Study on Conflict-Type Classification in RAG](https://www.alphaxiv.org/abs/2609.can-jev-be-used-as-a-confident-classifier-a-calibration-study-on-conflict-type-classification-in-rag) | Prajapati Harishkumar Kishorkumar | 2026-09-22 | G4 | 错误答案的平均置信度保持在 0.56–0.58（仅发表于 alphaXiv） | 未标注 | 🔗 仅链接 |
| P-33209 | [Beyond Calibration: Do a Typed-Decision Model's Probabilities Obey the Probability Axioms?](https://arxiv.org/abs/2609.33209) | Keyi Li 等 | 2026-09-27 | G4 | "是 X"与"不是 X"的概率之和平均偏离 1 达 0.064；三个单标签概率之和为 1.14 | CC BY 4.0 | [✅ PDF](../papers/2609.33209.pdf) |
| P-35342 | [Jev thinks "I don't know'', but doesn't say it: Introducing Sys1Cal-v1 Dataset for Probability Calibration](https://arxiv.org/abs/2609.35342) | Riccardo Porcedda | 2026-09-28 | G4 | 假设 Jev 隐去了"不知道"这第三个真值；按此补回，软准确率 0.771→0.978 | CC BY 4.0 | [✅ PDF](../papers/2609.35342.pdf) |
| P-24052 | [Calibrated Decisions at Scale: Converting Police Crash Narratives into Probabilistic Crash Variables with a System One Model (Jev)](https://arxiv.org/abs/2609.24052) | Amir Rafe 等 | 2026-09-21 | G4 G7 | 车祸叙述转码：校准因模型而异，须逐一审计；重新校准后误差降至 1/3.3 | arXiv 默认许可 | 🔗 仅链接 |
| P-24965 | [Jev for Scientific Decisions: Evaluating Semantic Choices and Their Consequences](https://arxiv.org/abs/2609.24965) | Boyuan Deng 等 | 2026-09-21 | G5 | Jev 语义全对，但对照模型出现"最终标签正确、中间选择错误" | CC BY-NC-ND 4.0 | [✅ PDF](../papers/2609.24965.pdf) |
| P-27678 | [Same Scores, Different Decisions: Evaluating JEV and Language Models for Legal Document Understanding](https://arxiv.org/abs/2609.27678) | Fan Zhang 等 | 2026-09-23 | G5 | 合同推理：平均准确率与逐条一致正确的排名不同 | CC BY 4.0 | [✅ PDF](../papers/2609.27678.pdf) |
| P-32160 | [Typed Decision Models: An Early Evidence Audit and Evaluation Checklist](https://arxiv.org/abs/2609.32160) | Lijuan Tang 等 | 2026-09-26 | G5 | 28 篇早期论文的证据审计：类型化读出尚无独立的准确率优势；14 项评估清单 | CC BY 4.0 | [✅ PDF](../papers/2609.32160.pdf) |
| P-26550 | [JEV-as-a-Judge: Accept When Confident, Escalate When Unsure](https://arxiv.org/abs/2609.26550) | Yubo Li 等 | 2026-09-22 | G6 | 可直接读出的判断与 GPT-6 相差 ≤3 点、费用 0.36%；冻结阈值级联比 GPT-6 高 0.9 点、费用 41% | CC BY 4.0 | [✅ PDF](../papers/2609.26550.pdf) |
| P-29769 | [JEV vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places](https://arxiv.org/abs/2609.29769) | Delip Rao 等 | 2026-09-24 | G6 | 三个 flash 档 LLM 评判器重复 Jev 最自信的错误；级联最多 +1.5 点 | arXiv 默认许可 | 🔗 仅链接 |

### 相关（10 篇）：提供补充证据

| 编号 | 标题 | 第一作者 | 日期 | 轴 | 要点 | 许可 | PDF |
|---|---|---|---|---|---|---|---|
| P-22664 | [From Capability to Assurance in Autonomous Penetration-Testing Harnesses: A Framework and Reference Implementation](https://arxiv.org/abs/2609.22664) | Joas Antonio dos Santos Barbosa | 2026-09-19 | G1 | 自主渗透测试的五项保障属性；实测发现真实的授权执行缺口 | CC BY 4.0 | [✅ PDF](../papers/2609.22664.pdf) |
| P-23959 | [Open-Jev Judgments on CallScreenBench: Calibrated One-Pass Scam Screening with a Small Language Model](https://arxiv.org/abs/2609.23959) | Simiao Ren 等 | 2026-09-21 | G1 | 诈骗电话逐轮筛查，AUROC 0.974，零误报 | CC BY-NC-SA 4.0 | [✅ PDF](../papers/2609.23959.pdf) |
| P-28940 | [Calibrated Decision Models for Autonomous Penetration-Testing Harnesses: JEV and Laya as System One Decision Layers for LLM-Driven Pentest Agents](https://arxiv.org/abs/2609.28940) | Joas Antonio dos Santos Barbosa | 2026-09-24 | G1 | 渗透测试 Agent 的判断层：有无 Jev 各一次运行的探索性案例 | CC BY 4.0 | [✅ PDF](../papers/2609.28940.pdf) |
| P-35293 | [Decide, Don't Generate: Competitive Dimensional ABSA with Jev's Typed Decisions](https://arxiv.org/abs/2609.35293) | Yiqun Zhang 等 | 2026-09-28 | G3 | 六种语言的维度情感分析：不生成文本也达到 SemEval-2026 最低误差 | arXiv 默认许可 | 🔗 仅链接 |
| P-24881 | [Pinocchio: Fast Uncertainty Estimates for Black-Box Language Models](https://arxiv.org/abs/2609.24881) | Kevin David Hayes 等 | 2026-09-21 | G4 | Pinocchio 黑盒不确定性估计（AUROC 0.862）；附录中 Jev 作校准器仅 0.666 | CC BY 4.0 | [✅ PDF](../papers/2609.24881.pdf) |
| P-26532 | [REFLEX with Jev for Efficient Selective Control in LLM Agents](https://arxiv.org/abs/2609.26532) | Tiantong Wu 等 | 2026-09-22 | G6 | Agent 分层控制：强模型调用减少 72.7%；授权边界附近易错 | CC BY 4.0 | [✅ PDF](../papers/2609.26532.pdf) |
| P-27607 | [Can Jev Judge Radiology Reports? Evaluating a System One Model for Clinical Factuality](https://arxiv.org/abs/2609.27607) | Jiaju Huang 等 | 2026-09-23 | G6 | 临床报告事实性评判 | arXiv 默认许可 | 🔗 仅链接 |
| P-27535 | [KITE: Scaling Jev Population Experiments with Sparse Flagship Calibration](https://arxiv.org/abs/2609.27535) | Hengyu Li | 2026-09-23 | G7 | 群体实验：把人机差异作为共享误差传播 | CC BY-NC-SA 4.0 | [✅ PDF](../papers/2609.27535.pdf) |
| P-28919 | [Harness Tokenomics: A Router for the Enterprise Agentic Control Plane](https://arxiv.org/abs/2609.28919) | Ted Kwartler 等 | 2026-09-24 | G7 | 企业 Agent 控制平面：用 Jev 路由，回收 13%–21% 模型开支 | CC BY-NC-SA 4.0 | [✅ PDF](../papers/2609.28919.pdf) |
| P-30216 | [Jev in the Wild: A Data-Driven Analysis of the Jev Model's Functionality, Applications and Ecosystem](https://arxiv.org/abs/2609.30216) | Guoming Ling 等 | 2026-09-24 | G7 | 2,170 个公开 Jev 项目的生态实证 | arXiv 默认许可 | 🔗 仅链接 |

### 背景（12 篇）：工程与其他领域，供参考

| 编号 | 标题 | 第一作者 | 日期 | 轴 | 要点 | 许可 | PDF |
|---|---|---|---|---|---|---|---|
| P-22753 | [Replacing Large Language Models with Jev Decision Models for Low-Latency Edge Service Orchestration](https://arxiv.org/abs/2609.22753) | Delong Li 等 | 2026-09-19 |  | 以 Jev 替代大模型做边缘服务编排 | arXiv 默认许可 | 🔗 仅链接 |
| P-23136 | [Fast Intent-Driven Service Orchestration with Jev for 6G Edge Networks](https://arxiv.org/abs/2609.23136) | Delong Li 等 | 2026-09-19 |  | 6G 边缘网络的意图驱动服务编排 | arXiv 默认许可 | 🔗 仅链接 |
| P-23886 | [this-that-model-1.0: A typed decision model that decides in 30 ms, for a millionth of a cent](https://arxiv.org/abs/2609.23886) | Zehua Cheng 等 | 2026-09-20 |  | this-that-model-1.0：2B 开源类型化决策模型 | arXiv 默认许可 | 🔗 仅链接 |
| P-23986 | [Jev-Mem: System-One-Controlled Agentic Memory for Efficient AI Agents](https://arxiv.org/abs/2609.23986) | Dongming Jiang 等 | 2026-09-21 |  | Jev-Mem：System One 控制的 Agent 记忆 | CC BY 4.0 | [✅ PDF](../papers/2609.23986.pdf) |
| P-24395 | [JEVQA - Video Quality from Metadata, Bitstream, and Pixel Features with a General-Purpose Decision Model](https://arxiv.org/abs/2609.24395) | Werner Robitza | 2026-09-21 |  | JEVQA：视频质量评估 | arXiv 默认许可 | 🔗 仅链接 |
| P-25498 | [Universal Fractal Natural Language Decision Map: Real-Time Edge Triage Across Heterogeneous Domains](https://arxiv.org/abs/2609.25498) | Volkan Dağlı 等 | 2026-09-21 |  | 分形自然语言决策图（主张较强，证据有限） | arXiv 默认许可 | 🔗 仅链接 |
| P-25845 | [Visual Jev: Accurate and Efficient Decisions from Shared Visual Context](https://arxiv.org/abs/2609.25845) | Guanxu Yu 等 | 2026-09-22 |  | Visual Jev：共享视觉上下文的多问题判断 | CC BY-NC-ND 4.0 | [✅ PDF](../papers/2609.25845.pdf) |
| P-27331 | [JEV-Star: Fast, Low-Cost StarCraft II Control with Language-Model Planning](https://arxiv.org/abs/2609.27331) | Weiyu Ma 等 | 2026-09-23 |  | JEV-Star：星际争霸 II 控制 | CC BY 4.0 | [✅ PDF](../papers/2609.27331.pdf) |
| P-28587 | [NumericJev: Jev-like LLM Numerical Decoding with Multiway Decision Trees](https://arxiv.org/abs/2609.28587) | Weiwei Ye 等 | 2026-09-23 |  | NumericJev：数值输出的多路决策树解码 | CC BY-NC-SA 4.0 | [✅ PDF](../papers/2609.28587.pdf) |
| P-29283 | [From Text Decisions to Pixels: An Study of Jev-Style Visual Choice Model](https://arxiv.org/abs/2609.29283) | Xunlan Zhou 等 | 2026-09-24 |  | PixelJev：图像输入的选择模型 | CC BY 4.0 | [✅ PDF](../papers/2609.29283.pdf) |
| P-30186 | [Jev-Mobile: Jev as an Executor for Mobile GUI Agents](https://arxiv.org/abs/2609.30186) | Linghua Zhang | 2026-09-24 |  | Jev-Mobile：移动端 GUI Agent 执行器 | CC0 1.0 | [✅ PDF](../papers/2609.30186.pdf) |
| P-34180 | [Decision Readouts for Text-Mediated Video Anomaly Detection: An Exploratory Evaluation of Jev and Qwen](https://arxiv.org/abs/2609.34180) | Xukui Qin 等 | 2026-09-28 |  | 文本中介的视频异常检测（探索性） | arXiv 默认许可 | 🔗 仅链接 |

<!-- CATALOG:END -->

---

## 6. 灰色文献（非论文，未经同行评审）

以下材料的摘要取自 hanxiao.io 的 Jev 生态追踪库 [G-Tracker]（2026-09-27 扫描），整理者未逐一核对原文，引用时请回到原链接。

| 编号 | 标题 / 作者 | 链接 | 与 PoL2 的关联 |
|---|---|---|---|
| G-CheckPoint | *Jev is not a language model, but it breaks like one* — Check Point Research | [链接](https://blog.checkpoint.com/ai-security/jev-is-not-a-language-model-but-it-breaks-like-one-prompt-injection-against-a-typed-decision-model/) | G2 安全阀可被攻破 |
| G-Simmons | *It refused, then I made it choose* — Josh C. Simmons | [链接](https://www.drjoshcsimmons.com/writing/it-refused-then-i-made-it-choose) | G3 平等联结 |
| G-ZhBench | ZH-Decision-Bench v0.1：中文决策模型校准评测 — CodyQin | [链接](https://github.com/CodyQin/zh-decision-bench) | G3 语言平等 |
| G-Replication | Jev RLCD Replication（*Just Ask Jev* 的独立复现）— jkf87 | [链接](https://github.com/jkf87/jev-rlcd-replication) | G1 阈值 |
| G-Molas | *Jev can't be calibrated* — Alex Molas | [链接](https://www.alexmolas.com/2026/09/23/jev-cant-be-calibrated.html) | G4 校准 |
| G-Grazian | *Is Jev calibrated? Tests on real data* — Leonard Grazian | [链接](https://leonardgrazian.com/blog/jev-calibration/) | G4 校准（支持） |
| G-Bernoulli | *Is Jev confident?* — Stanislav Yurin | [链接](https://bernoulli.app/articles/is-jev-confident) | G4 置信度公式 |
| G-Willison | *Jev introduces a new shape of LLM* — Simon Willison | [链接](https://simonwillison.net/2026/Sep/21/jev/) | G5 可解释性、偏见 |
| G-Sev | RLCD 逆向分析（LakoreAI/sev） | [链接](https://github.com/LakoreAI/sev) | G4：分析 Laya 的 RL 训练项，推导出其中的噪声平滑会使分布偏向过度自信 |
| G-Tracker | *All about Jev* 生态追踪库（2,073 条，2026-09-27 扫描）— Han Xiao | [链接](https://hanxiao.io/all-about-jev/) | 检索来源 |
| G-ASOM | *Awesome System One Models*（213 篇相关论文，截至 2026-09-24）— Amir Rafe, Subasish Das | [链接](https://github.com/pozapas/awesome-system-one-models) | 检索来源；含 27 项研究的偏倚风险评估 |

**TypeSafe 官方资料**

- [T1] AI primer（RLHF / RLVR / RLCD）：https://docs.typesafe.ai/introduction/machine-learning-primer
- [T2] Models（价格、上下文、语言支持）：https://docs.typesafe.ai/models
- [T3] Jev 1.13 jaggedness（已知失效模式）：https://docs.typesafe.ai/model-jaggedness/jev-1.13
- [T4] Introduction（"the first System One model"）：https://docs.typesafe.ai/introduction

---

## 7. 方法与局限

**检索来源**：
1. hanxiao.io 的 Jev 生态追踪库 `all-methods.jsonl`（2,073 条记录，其中 52 条标为论文，2026-09-27 扫描）[G-Tracker]；
2. pozapas/awesome-system-one-models 的 `papers.csv`（213 篇）与 `studies.csv`（27 项研究），截至 2026-09-24 [G-ASOM]；
3. 2026-09-28 至 09-29 的网络检索，补充追踪库截止日期之后的 arXiv 论文；
4. alphaXiv 上仅在该平台发表的一篇论文 [A-RAG]。

**纳入标准**：以 Jev 或 Jev 类 System One 决策模型为研究对象、实验组件或直接对照的研究。Jev 发布之前的背景文献（如校准、拒答选项、LLM 评判器的经典工作）不在本目录中，可参考 [G-ASOM] 的完整谱系。

**局限**：
- 绝大多数文献是发布两周内的预印本，样本量小，许多是单一作者的快速研究；[G-ASOM] 对其中 27 项研究的偏倚风险评估中，没有一项被评为"低风险"。
- 第 2 节对每篇论文的概括，主要依据论文摘要与追踪库的结果摘录，并未逐篇精读全文；数字引用时请回到原文核对。
- 与 PoL2 条款的对应关系是整理者的解读，不是原作者的主张。
- 本综述的结论只适用于 2026 年 9 月的 jev-1.13 及同期开源复现；模型版本变化后可能不再成立。

---

## 许可说明

整理者撰写的文字、数据与脚本以 CC0-1.0 发布（见 [`LICENSE`](../LICENSE)）。**[`papers/`](../papers/) 文件夹中的论文不适用 CC0**，各自保留原作者的 Creative Commons 许可，详见 [`papers/LICENSES.md`](../papers/LICENSES.md)。
