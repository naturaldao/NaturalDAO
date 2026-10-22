# AI 执行治理的先例、边界与制度含义

## AI 治理概念与现有先例分别覆盖什么？

### Takeaway
“AI 执行治理”是比 AI 治理（governance of AI）更窄、更适合 PoL2-EG 的运行时概念：它表示 AI 参与或执行治理决策，但不能据此推断 AI 有权决定规范来源、修改最终价值基准或自行证明其治理权正当。现有工作分别覆盖给定原则下的 AI 反馈、算法嵌入治理流程、多智能体运行时政策拦截和模拟治理决策；本次检索未找到同时实现规范自定、具身行动授权、事故纠错及规范演化的真实高影响全 AI 治理系统。

### Cited Findings
- Farrell 将 AI 与治理的关系分成两个分析视角：AI 作为治理技术，改变分类、市场、官僚制、民主等既有治理机制；AI 也可被看作有自身表征与协调机制的一种治理形式。这种区分有助于避免把“用 AI 管理 AI”与“AI 成为治理主体”混为一谈。[Farrell, “AI as Governance,” *Annual Review of Political Science* (2025)](https://doi.org/10.1146/annurev-polisci-040723-013245)
- Kleiner 将治理 AI（外部规则、监管和监督）与由 AI 治理（AI 嵌入决策程序，输出影响或决定行政决定）区分，并提出两者通过部署和反馈相互耦合；其文意聚焦公共行政，不直接定义具身系统或无人机治理。[Kleiner, “Governance of AI and by AI,” *Global Policy* (2026)](https://doi.org/10.1111/1758-5899.70177)
- Gritsenko 与 Wood 以交通超速、虚假信息和共享平台三个案例说明算法如何把权力前置到协议与“选择架构”中、降低治理者逐项裁量空间；他们明确将“algorithmic governance”作为分析工具，并不声称已经存在一套独立、统一的全算法治理模式。[Gritsenko & Wood, “Algorithmic governance: A modes of governance approach,” *Regulation & Governance* (2022)](https://doi.org/10.1111/rego.12367)
- Constitutional AI 让模型依据**外部给定**原则批评、修订输出，并使用 AI 反馈训练；它减少逐条人工危害标签需求，但论文并未让 AI 产生或取得更改宪法原则的权力。[Bai et al., “Constitutional AI: Harmlessness from AI Feedback” (2022)](https://arxiv.org/abs/2212.08073)
- Collective Constitutional AI 将公众提出的原则用于训练模型。作者报告约 1,000 名美国公众参与，形成 1,127 条意见和 38,252 次投票；论文认为过程可以影响模型行为，同时明确承认样本范围、流程设计和外部适用性限制，也不把公众输入等同于系统治理权移交给 AI。[Huang et al., “Collective Constitutional AI,” FAccT 2024](https://facctconference.org/static/papers24/facct24-94.pdf)；[项目说明](https://www.anthropic.com/research/collective-constitutional-ai-aligning-a-language-model-with-public-input)
- Governance-as-a-Service 将声明式规则、运行时动作拦截和信任评分分离成治理层，并在多个模拟任务中评估；作者自述的实验是仿真，不是现实政策制度或具身机器人部署。[Gaurav et al., “Governance-as-a-Service: A Multi-Agent Framework for AI System Compliance and Policy Enforcement” (2025 preprint)](https://arxiv.org/abs/2508.18765)
- DAO-AI 探索代理阅读提案与历史信息后进行治理投票，并在基于区块链数据的仿真环境比较决策；它测试的是代理治理信号，不证明 DAO 制度已由 AI 完全接管，也没有覆盖真实具身动作或外部救济。[“DAO-AI: Evaluating Collective Decision-Making through Agentic AI in Decentralized Governance” (2025 preprint)](https://arxiv.org/abs/2510.21117)
- “Toward a Science of AI Agent Societies”将具备不同目标、规则/治理、自主性和规模复杂度的 Agent 社会视为新研究对象，并指出当时的多 Agent 系统只实现其提出特征的部分子集；该工作是议程和研究框架，不是已部署 AI 社会的治理证据。[Lee et al., KDD 2026](https://doi.org/10.1145/3770855.3818651)
- 关于公共部门 Agent 的访谈与文献研究发现，Agent 会放大持续监督、治理与运行集成、跨部门协调等既有困难；研究建议的是改造机构监督能力，而非由 Agent 取代制度责任。[Schmitz et al., “Oversight Structures for Agentic AI in Public-Sector Organizations,” REALM 2025](https://aclanthology.org/2025.realm-1.21/)
- 多 Agent 争论的 2026 年过程评估研究发现，只看最终答案、共识或多数票可能漏掉谄媚、支配、过早收敛等过程故障，并提出对交互过程本身进行测量；这意味着“多个 AI 同意”不能独立充当授权证据。[Pitre et al., ICML 2026, PMLR 306](https://proceedings.mlr.press/v306/pitre26a.html)

### Inferences
- 为 PoL2-EG 建立一套清晰分类，可采用五级谱系：自动化规则执行；AI 辅助治理；在既定授权下由 AI 代行具体决策；治理职能由 AI 组件执行的运行时自治；AI 修改规范、价值权重或自己的评估标准的自我制宪。PoL2-EG 当前定义主要落在第 4 级，V2 的“理论不断演化”若包含自动改写规范，才触及第 5 级。
- 对外主张应写成：“该框架提出一种无人工运行时决策节点的治理配置；规范依据、工具权限和评测规则是版本化输入；完整系统尚未完成端到端验证。”这比“AI 能够自主治理”更精确。
- 最强的技术先例是“外置运行时策略执行层拦截 Agent 产生的动作”；最弱的证据跨越是“从 AI 代理投票或 AI 自我批评，推断系统能自行制定规范并合法治理现实世界”。各组件先例不能仅靠拼接升格为系统级验证。
- 多代理“制衡”必须用独立数据、不同失效域、工具权限隔离、盲测/封存测试与共享错误评估证明；在同模型家族中变换角色提示不等于统计独立或规范独立。[Pitre et al., ICML 2026](https://proceedings.mlr.press/v306/pitre26a.html)

### Gaps
- 本次是基于针对性关键词的聚焦检索，不是预注册的系统性综述；“未发现端到端先例”应写明为本次检索边界内未发现，不应宣称穷尽所有学科。
- 治理研究中的算法决策、DAO 投票、LLM 代理和具身机器人使用不同“治理”定义，暂缺可直接横向比较的统一证据等级或 benchmark。
- 需要进一步检查 GaaS、DAO-AI 和 ARDE 的同行评审状态、完整方法、样本/仿真设置和复现材料；不应只引用摘要报告的结果。

## 无人工治理节点的技术价值与正当性难题是什么？

### Takeaway
反对每次动作都由人复核，有充分的工程理由：人工监督可能成为延迟、形式化签字或自动化偏差的来源，而持续运行的机器策略门更适合高速、重复、可契约化的动作。但“没有有效人工复核”不推出“治理不需要问责、权力授权或受影响者救济”；应将运行时无人工节点与初始化规范、责任归属、制度授权和事后挑战分开讨论。

### Cited Findings
- Green 对 41 项要求政府算法接受人工监督的政策进行综述，指出许多政策把人工有效监督当作未经验证的前提；其替代建议是机构层面的正当性论证、经验验证和民主审查，而非简单取消监督。[Green, “The Flaws of Policies Requiring Human Oversight of Government Algorithms,” *Computer Law & Security Review* (2022)](https://doi.org/10.1016/j.clsr.2022.105681)
- 算法治理研究显示，规则可以通过协议和选择架构在事前嵌入系统，减少逐项人工裁量；这种方式提升可重复执行能力，却把影响力转移给设计协议、选择指标和维护系统的主体。[Gritsenko & Wood (2022)](https://doi.org/10.1111/rego.12367)
- Stone 与 Mittelstadt 指出，自动决策的合法性问题是“控制系统的人为何有权作出这些决定”，不能简单等同于准确率、公平性、专业能力或公众接受度；他们分析同意、公共理性和民主授权等合法性路径，并指出不同路径有局限。[Stone & Mittelstadt, “Legitimate Power, Illegitimate Automation,” *ACM Journal on Responsible Computing* (2026)](https://doi.org/10.1145/3725858)
- Waldman 与 Martin 的因子情境调查发现，在其公共政策决策情境中，受试者认为 human-in-the-loop 提高算法决策的感知合法性，即使决定可能存在显著错误；这是公众感知实验，不等于证明任何特定人审查机制在实践中有效，也不等于规范上的最终结论。[Waldman & Martin, *Big Data & Society* (2022)](https://doi.org/10.1177/20539517221100449)
- accountability 研究把问责定义为一种要求回答的关系，包含权威认可、质询和限制权力的条件，并区分合规、报告、监督和执行目标；只留下日志或解释，但没有能限制权力或处理错误的论坛/后果，不能自动构成完整问责。[Santoni de Sio et al., “Accountability in artificial intelligence: what it is and how it works,” *AI & Society* (2023)](https://doi.org/10.1007/s00146-023-01635-y)
- NIST AI RMF 1.0 是自愿风险管理框架，其 Govern 功能强调组织领导层制定目标、价值与风险容忍度、明确责任、生命周期监测、测试事件以及收集外部相关方反馈；它把 AI 风险治理放在组织结构内，而不是授权模型对自身风险做最终判断。[NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- 欧盟 AI Act 第 14 条对法定高风险系统规定自然人监督设计要求，包括能理解限制、监测异常、识别自动化偏差，并适时覆盖、逆转或停止系统；是否适用于 PoL2 无人机 Demo，须按用途、风险分类、运营者和市场适用范围作法律分析，不应泛化为对所有 AI 项目的通则。[Regulation (EU) 2024/1689, Article 14](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng)
- 运行时 AI 再审与人类/外部救济并非同一机制。问责框架需要指定谁有权质询、依据什么标准、谁能限制或停止权力，以及错误造成的后果；模型内部复核可以改正记录或策略，但不自动补偿既成物理损害。[Santoni de Sio et al. (2023)](https://doi.org/10.1007/s00146-023-01635-y)；[Green (2022)](https://doi.org/10.1016/j.clsr.2022.105681)

### Inferences
- 应将用户的立场最强地解释为：“治理环路中的每次运行判断、逐案批准、规则更新和事故技术复核不依赖人工操作。”这是一项可定义、可测试的系统性质。它不等同于“没有人类来源/影响”，也不等同于系统取得自己的规范权威。
- “AI 内部复核”可以作为技术纠错机制，但如无独立审查方、可执行权限限制和受影响方挑战渠道，应称为机器复算/再审，不要称为法律意义的申诉、程序正义或外部问责。
- 可钢人化无人工参与的工程论证：明确策略门能消除人工审批的吞吐瓶颈和个体裁量波动；可重复、可记录的机器契约比值班人员逐次阅读复杂轨迹更适合高频动作；对机器人实时控制，人类无法及时在闭环内干预。由 Green 的综述看，形式化人工审批本身并非充分安全措施。[Green (2022)](https://doi.org/10.1016/j.clsr.2022.105681)
- 但应将“人工是否参与动作判定”与“谁设定系统目标/界限并承担责任”分层。即使 runtime 不存在人类决策节点，系统仍依赖初始化条款、动作类型、任务授权来源、风险阈值、训练/检索数据、封存测试与设备固件；这些构成治理边界，不能用“纯 AI”抹去。
- 具身系统造成的影响可能落在非发起任务的人身上。即使委托者接受 AI 自治，也不能由委托者单独证明第三方影响有正当授权；这一问题属于公共权力/社会合法性，不是分类模型性能。
- 报告可以明确采纳“运行时全 AI”的设计目标，同时把制度合法性当作外层条件与未解决问题，不以作者偏好删除风险论证，也不把当前法定人工监督要求说成工程上的最好实践。

### Gaps
- 不同国家/行业对 autonomous UAV 的操作者责任、远程驾驶员、事故报告、法律责任和保险规定不同；需要具体 demo 地点、用途、机型类别及测试性质后，才能判断人类节点的法定要求。
- 公共合法性文献主要研究行政政策或公共服务，不能直接等同用户自行控制的私人机器人；但非同意的第三方风险又使“私有系统”论证不能自动免除制度问题。
- 需实证测试人工审批与机器策略门在特定任务中的延迟、错误、误停、可解释性和责任归属差异；现有理念文献不能替 PoL2 给出量化结论。
- 对“初始 PoL2 理论由人类提出”这一边界，研究者应将其视为框架引导条件并明确记录，而不把它偷偷转化为运行时人工节点；若理论后续可演化，尚须定义演化的权力来源和失败回退机制。

## RSI、受约束规则更新与 PoL2-EG 命名应如何界定？

### Takeaway
RSI 的主要语义是 AI 递归改进自身能力，不是一个把“规则解释、任务授权、机器执行、审计和问责”整合起来的治理框架名称。对 PoL2-EG，更准确的技术议题是受约束的策略演化；关键工程边界是哪些对象可由 AI 更新、哪些安全不变量和评测准则在一个版本周期内不可由被评估系统改写。

### Cited Findings
- Stanford HAI 将 RSI 定义为 AI 系统改进自身代码、架构、训练、推理或工具使用能力，并以改进后的能力继续推进后续改进；这一语义聚焦能力提升。[Stanford HAI, “What is Recursive Self-Improvement?”](https://hai.stanford.edu/what-is-recursive-self-improvement)
- 一篇 2026 年预印本对 2024–2026 自我改进论文建立了分类框架，区分行为优化、policy/训练改进、评估器改进和自动科研，并将闭环程度从 human-in-the-loop 到 fully closed 划分；这是预印本综述，且“RSI”边界仍存在术语分歧，适合用作检索地图，不宜当作稳定共识。[Chen et al., “Recursive Self-Improvement in AI: From Bounded Self-Refinement to Autonomous Research Loops” (2026 preprint)](https://arxiv.org/abs/2607.07663)
- Collective Constitutional AI 通过公众输入调整训练原则，并在讨论部分强调模型行为与公共输入只能覆盖 AI 生命周期的一部分，研究者明确警告不可把方法误述为充分的组织治理或民主授权。[Huang et al., FAccT 2024](https://facctconference.org/static/papers24/facct24-94.pdf)
- NIST AI RMF 将风险管理定义为整个生命周期中的持续过程，要求组织明确责任、监控、定期回顾、测试、事件发现、停用流程及第三方风险；这些要求可用于工程化治理变更流程，但 NIST 并未验证“AI 自行改变其规范并自证合格”。[NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- Accountability 框架认为限制权力是问责关系的必要条件之一，因而审计代理、建议代理或规则生成代理不应同时成为唯一的验收标准制定者、候选判定者和上线发布者。[Santoni de Sio et al. (2023)](https://doi.org/10.1007/s00146-023-01635-y)

### Inferences
- PoL2-EG 可按对象定义三个版本域：理论版本（Proof of Love2 条款及原则）；应用策略版本（规则到动作谓词、作用对象、权限范围、证据要求、冲突优先级的映射）；单次授权版本（具体 Agent、任务、状态、时限和命令白名单）。MVP 中冻结理论版本，只测试“规则如何编译为任务策略”，避免把理论更新与飞控接入同时引入。
- 受约束策略演化可实现为：AI 提候选 → 独立实现对候选作类型/权限检查 → 封存数据回放和对抗测试 → 展示新旧策略动作差异 → 影子/金丝雀部署 → 机器监控和回滚。目标值、测试集、策略编译器和回滚条件须独立于候选补丁，且不能由同一 Agent 在当前周期改写；这是建议的可验证设计，不是已有全治理先例。
- 若团队仍希望 AI 能更新理论文本，可将更新权限限制在明确的版本操作集合（例如条文释义、执行映射或添加候选条款），分别定义哪些操作自动生效、哪些必须进入实验分支。机器“测试通过”只能支持实现满足固定形式性质，不证明新的价值优先级正当。
- PoL2-EG 名称既保留理论来源和具身领域，又不声称 autonomous self-improvement 已达成。若学术论文要精确定义，可把“AI-executed runtime governance”作为框架属性，把“bounded policy evolution”作为子机制，把 RSI 作为可能相关的能力研究问题。
- 如果框架完全取消人工节点，仍可以用标准、形式性质、合成测试、失败注入、版本差异和外部机器可验证日志证明技术契约的合规性；但这些验证只回答“系统是否遵守指定规范”，不回答“指定规范本身是否正当”。

### Gaps
- 文献缺少公认的 AI 自治治理成熟度模型，需 PoL2-EG 自己定义可重复的能力分级与证据门槛；例如设计提案、单组件基准、沙箱端到端、SITL/HITL、真实环境运行，不应以无来源的“成熟度级别”包装。
- 目前没有统一 benchmark 能判断治理理论更新后是否忠实于其原有规范意图；需要 PoL2 的理论不变量、规则冲突集、越权攻击集、非预期动作差异测试与独立评估。
- 需进一步区别模型自我修正、策略参数更新、可编辑政策树、改变规则优先级和修改规范本体等不同变化；它们风险与权限要求不同，不能统一叫“自我演化”。
