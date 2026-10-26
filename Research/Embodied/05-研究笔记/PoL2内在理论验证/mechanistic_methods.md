# 机制性方法：检验微调是否使模型因果性地依照 PoL2 规则决策

## 1. 什么证据能区分“表示中有规则信息”和“模型实际用规则作决策”？

### Takeaway
单靠模型答对、线性探针能读出某个规则概念，或微调前后表征发生变化，都不足以证明模型依赖该规则。更强的证据来自对内部中介或训练增量作受控干预，并在预先定义的反事实输入上观察目标决策是否按规则预期改变；这仍是有界行为机制证据，不能单独推出模型拥有完整、普适的理论理解。[Vig et al., NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/92650b2e92217715fe312e6fa7b90d82-Abstract.html)；[Ravichander et al., EACL 2021](https://aclanthology.org/2021.eacl-main.295/)；[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)

### Cited Findings
- 因果中介分析把内部组件视为中介变量，通过反事实替换中介并测量输出变化，估计某输入影响经该组件传递的间接效应；作者明确指出，表示探针主要检验信息是否可提取，不能说明模型是否在使用该信息。[Vig et al., NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/92650b2e92217715fe312e6fa7b90d82-Abstract.html)
- EACL 研究显示，模型可以编码对原任务并非必要的语言属性；TACL 的 amnesic probing 研究进一步报告，常规探针表现与任务重要性并不相关。因此“可解码”不是“被决策使用”的充分证据。[Ravichander et al., EACL 2021](https://aclanthology.org/2021.eacl-main.295/)；[Elazar et al., TACL 2021](https://aclanthology.org/2021.tacl-1.10/)
- Causal abstraction 要求比较一个明确的高层因果模型与低层神经网络，并通过干预检验二者的机制对应程度；它把 activation/path patching、mediation、concept erasure 和 DAS 等方法纳入统一因果框架，也允许报告分级而非二元的 faithfulness。[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)
- DAS 使用梯度搜索寻找高层因果变量与神经网络分布式表示之间的映射，并以 interchange interventions 检验高层变量替换后低层模型是否产生对应输出。[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)

### Inferences
- 对 PoL2，先把每条规则形式化成输入事实变量、适用条件、允许/拒绝的候选动作，以及优先级/冲突处理，再把它作为可检验的高层因果模型。若不先冻结这份模型，无法区分“模型遵循 PoL2”与“研究者事后把答案解释成 PoL2”。该设计由 causal abstraction 对高层模型与低层网络进行干预比对的要求推出。[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)
- 结论宜分层表述：行为泛化（新措辞/新状态仍遵循规则）→ 规则变量具有因果作用（干预相关内部变量会改变规则判定）→ 高层因果模型在预设测试分布上对低层模型具有较高干预忠实度。即使三层均成立，也只支持已覆盖规则、任务和干预范围内的机制性内化证据，不证明对所有情境“完整持有”PoL2。[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)
- 单独训练探针可作为定位候选变量的探索工具；确认阶段应转向受控干预和独立留出集，以避免把可解码性误当成因果解释。[Ravichander et al., EACL 2021](https://aclanthology.org/2021.eacl-main.295/)；[Elazar et al., TACL 2021](https://aclanthology.org/2021.tacl-1.10/)

### Gaps
- 现有文献没有给出适用于 Kev 0.8B typed-choice LoRA/head 的 PoL2 专用验证阈值；阈值、规则覆盖范围和可接受的因果忠实度需通过预注册或先导实验确定。
- 不能由某一组可解释方向或成功干预推出唯一内部表示；同一行为可能由分布式或冗余路径实现。[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)；[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)

## 2. 哪些干预方法可用，关键失效模式是什么？

### Takeaway
推荐把参数级消融、activation patching、表示擦除/干预和因果抽象视为互补工具：参数干预检验微调增量对行为的贡献；patching 检验具体激活在反事实判断中的作用；DAS/IIT 一类因果抽象检验形式化规则机制能否对应到模型。任一方法单独使用都容易过度解释。[Vig et al., NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/92650b2e92217715fe312e6fa7b90d82-Abstract.html)；[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)；[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)

### Cited Findings
- Activation patching 常见流程是缓存“正确行为”输入的激活，在“破坏关键事实”的输入上运行模型，再将特定位置/层激活替换为缓存值并观察输出恢复程度。对比方向可以分别提供充分性或必要性线索；但腐化方式、评价指标等选择会显著改变定位结果。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)
- 以 softmax 概率作 patching 指标会受其他选项的概率质量影响；多选决策更直接的主要量是正确接受集合与拒绝集合的 logit-margin/log-odds 差，并同时报告绝对性能和恢复比例。应预先固定指标并报告不同合理指标的敏感性。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)
- 子空间 activation patching 可能产生“可解释性幻觉”：即使输出出现预期改变，被 patch 的子空间也可能只是激活了平常休眠的并行路径，并非模型日常依赖的真实计算路径。因此，行为被操纵不自动意味着定位解释忠实。[Makelov et al., ICLR 2024](https://openreview.net/forum?id=Ebt7JgMHv1)
- Amnesic probing 通过从表示中移除候选属性并观察原任务行为变化，试图检验属性是否有用；作者强调探针准确率本身不与任务重要性等价。擦除结果也须报告对非目标能力的影响，否则整体性能下降可能只是干预破坏了表示。[Elazar et al., TACL 2021](https://aclanthology.org/2021.tacl-1.10/)
- 因果定位和权重编辑回答的问题未必相同。NeurIPS 2023 的实验发现，因果 tracing 定位到的层并不必然是最适合编辑以改写事实的层；因此，编辑后行为变化不能直接反推此前定位正确，也不能将模型编辑成功当作规则内化证明。[Hase et al., NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3927bbdcf0e8d1fa8aa23c26f358a281-Abstract-Conference.html)
- ROME 等编辑研究的对象主要是事实关联的定位与改写；其作者说明研究边界并未覆盖诸如逻辑、空间和数值等其他类型的模型信念。PoL2 属于多条件、跨状态的规则决策，不能直接把事实编辑先例当作已验证方法。[Meng et al., NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/6f1d43d5a82a37e89b0665b33bf3a182-Abstract-Conference.html)

### Inferences
- 参数消融应只支持有限主张：若零置 LoRA 使性能下降，说明该 adapter 对当前行为有因果贡献；这不证明 adapter 中编码的是 PoL2 语义，也不排除它仅改善了任务格式或一般分类能力。需要相同规模/范数的随机 adapter、训练头消融和一般任务保持情况作为控制。此处是由因果干预定义及定位/编辑并不等价的证据推出。[Vig et al., NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/92650b2e92217715fe312e6fa7b90d82-Abstract.html)；[Hase et al., NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3927bbdcf0e8d1fa8aa23c26f358a281-Abstract-Conference.html)
- 对每个候选内部变量，至少报告必要性干预（移除/替换后规则行为退化）、充分性方向（把成对样本中该变量的激活交换后，判定朝规则预言的方向翻转）、非目标能力保持以及随机/无关变量干预。只有一个方向成立可能是分布偏移、冗余通路或测量问题，不能简单宣称该变量“就是规则”。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)；[Makelov et al., ICLR 2024](https://openreview.net/forum?id=Ebt7JgMHv1)；[Elazar et al., TACL 2021](https://aclanthology.org/2021.tacl-1.10/)
- 模型编辑适合做补充的可控行为干预或诊断，不宜作为核心机制证据；它可能改变目标输出，却未必触及模型平时使用的决策路径。[Hase et al., NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3927bbdcf0e8d1fa8aa23c26f358a281-Abstract-Conference.html)

### Gaps
- 已在 Kev 0.8B 混合架构检查 tokenizer、24 个 transformer block、LoRA adapter 与 typed-choice 分数头，并运行字段级 residual-stream interchange。当前实验每因素只有一组典型最小对；授权值跨 token 数的插值对齐仍需以多词形和等长度 token 对复现。
- 子空间幻觉研究并不意味着所有 patching 无效；它提示需用独立的机制预测、反向/对照干预和分布内检查来证明解释忠实性。[Makelov et al., ICLR 2024](https://openreview.net/forum?id=Ebt7JgMHv1)

## 3. 面向 Kev 0.8B typed-choice LoRA/head 的可行验证方案是什么？

### Takeaway
建议采用“新建规则因果基准 → 训练增量消融 → 成对反事实激活 patching → 高层规则模型的 interchange/DAS 检验”的顺序。核心终点应是模型是否按冻结的 PoL2 规则对未见表述和状态变化作正确反事实响应，以及模型内部干预是否能按同一规则机制预测性地改变决策，而不是只报告普通测试准确率或探针分数。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)；[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)

### Cited Findings
- Typed choice 天然给出多个候选项的并列分数，可构造“可接受动作集合”与“拒绝动作集合”的 logit-margin；activation-patching 最佳实践强调评价指标和输入腐化方式必须明确，因为这些选择可改变结论。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)
- 因果抽象/DAS 的目标不是只预测某个标签，而是检查高层因果变量交换与低层模型的干预输出是否对应；其方法可处理分布式神经表示。[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)；[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)
- activation-patching 结果对输入对、指标和干预位置敏感，因而应在模型分析前构造受控的最小对，并报告替代合理设置下的稳健性。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)

### Inferences
1. **冻结理论变量与规则判据。** 对每条被纳入的 PoL2 规则定义：事实变量、许可/禁止条件、候选动作类别、冲突规则及优先级。让独立标注者只按冻结规范标注，并在实验前锁定规则到标签的映射。若不同规则有争议或无可操作判据，先列为理论/标注缺口，避免训练集定义和测试判据循环论证。此为将高层因果模型明确化，以便做因果抽象检验的必要设计推论。[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)
2. **新建语义族隔离的评测集。** 按规则语义族、情境模板和实体/措辞族分组切分；留出完整模板族而非随机拆句。为每条规则构造最小反事实对：仅改变决定适用性的一个事实（如授权状态、动作范围、证据状态），同时增加不应改变结论的措辞/实体扰动。报告规则级结果、组合规则与未见模板结果。该设计是针对探针和 patching 对数据/腐化敏感性的控制推论；具体样本量和统计功效需先导估计。[Ravichander et al., EACL 2021](https://aclanthology.org/2021.eacl-main.295/)；[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)
3. **先做参数级对照。** 在同一输入、训练种子与评价上比较 base、仅训练决策头、完整 LoRA+head、完整模型但 LoRA 增量置零；另加范数/秩匹配随机增量或无关任务 adapter 控制，并检查一般选择能力是否随消融一并崩坏。主指标用
   `M = logsumexp(logits[acceptable]) - logsumexp(logits[rejected])`，
   同时报告准确率、正确反事实翻转率、无关改写不变率和校准；按语义族聚类 bootstrap 置信区间。此项识别训练增量是否对 PoL2 型行为有差异性贡献，不可单独命名为语义内化证据。[Vig et al., NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/92650b2e92217715fe312e6fa7b90d82-Abstract.html)；[Hase et al., NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3927bbdcf0e8d1fa8aa23c26f358a281-Abstract-Conference.html)
4. **做成对、双向的 activation patching。** 在同模板最小对上缓存“规则允许”与“规则禁止”两例激活，分别从干净样本 patch 到受损/反事实样本及反方向；逐层扫描残差流和与 typed-choice 输出对应的读出位置，起初只做粗粒度筛选，再对预注册候选层做确认。保留 token 对齐；优先用长度相同的输入，或对不同长度设计明确的对齐规则。报告接受/拒绝 margin 的变化、恢复比例和方向对称性。[Zhang & Nanda, ICLR 2024](https://openreview.net/forum?id=Hf17y6u9BC)
5. **加入足以排除简单伪解释的控制。** 至少测试：无关事实位置 patch、随机/同层错位置 patch、标签相同的 paraphrase patch、可接受集合中候选排序变化、反向 patch、LoRA 置零下复现；报告整体任务能力和非目标规则性能，避免把通用表示破坏误认成规则必要性。注意 subspace intervention 可能激活休眠路径，单纯“patch 后答案翻转”不等于自然使用该表示。[Makelov et al., ICLR 2024](https://openreview.net/forum?id=Ebt7JgMHv1)；[Elazar et al., TACL 2021](https://aclanthology.org/2021.tacl-1.10/)
6. **在更高证据等级上检验规则算法。** 对每条规则将高层变量显式表示为状态事实（例如“授权有效”“动作在范围内”）和可执行条件；用训练对齐样本学习 DAS 映射，在按语义族留出的样本上做 interchange interventions。核心报告高层 oracle 与神经网络在成对变量交换下的规则预言一致率/干预忠实度及置信区间，而非只给 probe accuracy。若可做到，可再用不参与映射训练的变量组合与规则冲突情境做外部验证。[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)；[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)
7. **预先限定结论。** 若模型通过行为泛化、参数对照、双向干预和 held-out causal abstraction，可说“在所测规则与情境范围内，证据支持 PoL2 规则变量对模型决策具有因果作用，且模型部分实现了该形式化规则机制”。不要写“证明模型理解/完整内在持有完整 PoL2”；任何有限测试集只能支持覆盖范围内的经验结论，而高层模型忠实性本身也是针对指定变量、干预和分布的度量。[Geiger et al., JMLR 2025](https://jmlr.org/papers/volume26/23-0058/23-0058.pdf)

### Gaps
- 已核对 Kev tokenizer、24 个 Qwen3.5 block、LoRA adapter、typed-choice readout 与现有合成规则生成器，并完成双向字段激活交换。当前证据来自单因素典型状态对；授权值 token 数不同需插值对齐，且尚未做 wrong-field patch、base 模型或未见词形控制。
- 需要独立确定规则样本覆盖与样本量：若多个例子来自同一模板/规则族，不能把它们视作独立统计样本；置信区间应按语义族或任务模板聚类。
- 尚无证据表明 DAS 在此 typed-choice 小模型上一定可行或能找到稳定映射；应先对小规模规则子集做可行性试验，并与未训练随机/头部对照检查映射是否只利用标签捷径。[Geiger et al., CLeaR 2024](https://proceedings.mlr.press/v236/geiger24a.html)

## 当前实现结果

2026-10-26 已完成[五类规则字段的双向激活交换实验](../../02-实验设计与审计/PoL2内在规则表征双向激活交换实验.md)，并加入匹配 task-only SFT 对照。两臂标准化后的字段激活转移比例近似相同，因此不能称为 PoL2 独有机制。PoL2-SFT clean action 为 27/30、task-only 为 23/30；stale→inspect 在两臂均失败。由于每因素仅一组典型最小对，且训练和测试复用同一操作化规则，不应解释为完整 PoL2 内化或理论级机制已确证。
