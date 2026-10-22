# 中文译稿术语表（所有译者必须统一使用）

## 总体定位
本文的中心是 **PoL（爱2证明）的治理**：研究问题是 PoL2 规范所要求的自动化治理判断（安全阀、恨语截断、NaturalDAO 的异常检测与争议裁决等）能否以及在何种条件下由类型化决策模型承担，以及这对 PoL2 条款的写法与实现意味着什么。翻译时：
- 内容忠实于英文原文，不增删论断、数字、引用和限定语（"在附加条件下""多数""低确定性"等限定词必须保留）。
- 英文原文中泛指的 "AI governance" 在涉及本文研究对象时译为"AI 治理"；凡指 PoL2 的部分，使用 PoL2 自身的中文术语（见下）。
- 学术书面语，句式简洁准确；避免口语化、避免"的的"连用；数字、单位、统计量保持原样（如 ECE 0.063、AUROC 0.744、κ = 0.72、95% CI）。
- 中文标点用全角（，。；：“”（）），但数学公式、引用命令、LaTeX 命令内部保持原样。
- 引号：中文正文用 “ ”（直接写 Unicode 弯引号），不要用 LaTeX 的 `` ''。
- 不翻译：论文标题（参考文献、附录 C 中的英文标题）、模型名（Jev、Laya、Qwen3 等）、数据集名、法规条款编号。

## PoL2 自身术语（以 PoL2 中文原文为准）
| English | 中文 |
|---|---|
| Proof of Love2 (PoL2) | 爱2证明（PoL2） |
| Love2 / Hate2 | 爱2 / 恨2 |
| Love Language | 爱语 |
| hate language | 恨语 |
| state of absence ("neither love nor hate") | "非爱非恨"的不在场状态 / 不在场状态 |
| Ethical Alignment Protocol (EAP) | 伦理对齐协议（EAP） |
| Public AI (PAI) | 公共 AI（PAI） |
| equal connection | 平等联结 |
| promoting love and restraining hate | 扬爱抑恨 |
| love's alignment | 爱的对齐 |
| self alignment / collaborative alignment | 自我对齐 / 协同对齐 |
| awareness of emotional experience | 情感体验的觉察 |
| cognitive calibration | 认知校准 |
| behavioural self-reflection | 行为自省 |
| hate-language truncation | 恨语截断 |
| real-time correction support | 实时矫正支持 |
| transparent boundary records | 边界透明记录 |
| reciprocal repair supervision | 修复对等监督 |
| Combining Semantic Recognition and Emotion Recognition | 语义识别和情绪识别相结合 |
| inner governance layer | 内置的共识治理层（简称"治理层"） |
| wisdom navigator | 智慧导航仪 |
| safety valve | 安全阀 |
| application layer (plug-and-play) | （"即插即用"的）应用层 |
| covenant of publicization | 公共化之约 |
| hate attack on humanity's core ethic | 对人类核心伦理的仇恨攻击 |
| Contemplative Axioms (Chapter 3) | 冥想智慧公理 |
| public-welfare governance protocol (Chapter 7) | 人类公共福利的治理协议 |
| complete autonomy | 完全自治 |
| verifiable decision chain | 可验证的决策链路 |
| right of suggestion / obligation to discuss | 建议权 / 讨论义务 |
| supervision / questioning | 监督 / 质询 |
| obligation to explain | 解释义务 |
| unimpeded access | 无阻碍访问 |
| non-intervention principle | 非干预原则 |
| anomaly detection / risk warning | 异常检测 / 风险预警 |
| ethical verification | 伦理验证 |
| universal questioning period | 全民质询期 |
| NaturalDAO | NaturalDAO（不译） |
| clause §5.4.1 | 第 5.4.1 节（正文可保留 `\clause{5.4.1}` 宏，宏会输出 §5.4.1） |
| Art. 9(7) | 第 9 条第（7）项（正文保留 `\art{9}(7)` 宏即可） |

## 本文方法与论证术语
| English | 中文 |
|---|---|
| typed decision model | 类型化决策模型 |
| System One model | "System One"模型（系统一模型） |
| generative (language) model | 生成式（语言）模型 |
| LLM evaluator | LLM 评估器 |
| low-cost generative evaluator | 低成本生成式评估器 |
| frontier model | 前沿模型 |
| open / open-weight model | 开源 / 开放权重模型 |
| hosted model | 托管模型 |
| safeguard | 保障机制 |
| detector | 检测器 |
| judge | 裁决者 |
| automatic allow | 自动放行 |
| block / false block | 阻断 / 误阻断 |
| miss rate | 漏检率 |
| requirement G1–G7 | 要求 G1–G7 |
| evidence assessment | 证据评估 |
| answer in brief (box title) | 简要回答 |
| code S / Q / N | S（支持）/ Q（有条件或结果不一）/ N（不支持），正文保留字母 |
| comparator (better/similar/worse/mixed/none) | 对照比较（更好 / 相近 / 更差 / 不一 / 无） |
| added condition | 附加条件 |
| certainty (very low/low/moderate) | 确定性（极低 / 低 / 中等） |
| design rating (stronger/moderate/weaker) | 设计评级（较强 / 中等 / 较弱） |
| preregistered | 预注册 |
| held-out | 留出（数据） |
| grey literature | 灰色文献 |
| corpus | 语料库（文献集） |
| coder / double-coded blind | 编码者 / 盲法双重编码 |
| vote counting (SWiM) | 计票（SWiM） |
| calibration / calibrated | 校准 / 经过校准的 |
| expected calibration error (ECE) | 期望校准误差（ECE） |
| threshold | 阈值 |
| deferral / selective prediction | 暂缓判定 / 选择性预测 |
| abstention | 弃权 |
| risk–coverage curve | 风险–覆盖率曲线 |
| escalation / cascade | 升级 / 级联 |
| confident error | 高置信错误 |
| option names | 选项名称 |
| prompt injection | 提示注入 |
| opinion attack / inserted opinion | 观点攻击 / 插入的观点 |
| three-valued | 三值 |
| tension (T1–T5) | 张力（T1–T5） |
| reference design | 参考设计 |
| acceptance criteria / pass criteria | 验收标准 / 通过标准 |
| checklist | 核查清单 |
| positionality | 立场声明 |
| competing interests | 利益冲突 |
| emotion recognition | 情绪识别 |
| per-person scoring | 逐人评分 |
| content moderation | 内容审核 |
| EU AI Act / GDPR / DSA | 欧盟《人工智能法》/《通用数据保护条例》（GDPR）/《数字服务法》（DSA） |
| Santa Clara Principles | 《圣克拉拉原则》 |

## Terms added on 2026-10-08 (update search and certainty ratings)
| English | 中文 |
|---|---|
| update search | 更新检索 |
| main window | 主窗口 |
| post-window / late-indexed / re-screened (set) | 窗口后 / 迟索引 / 重新筛选（集合） |
| census (of all pairs) | 全量（对全部配对） |
| adjudication / adjudicator | 裁定 / 裁定者 |
| contested | 有争议（表中标记 c） |
| opposing study / supporting study | 相反研究 / 支持研究 |
| corroborate (open-model evidence) | 佐证（开源模型证据） |
| counted per system arm | 按系统组计数 |
| hosted arm / open arm | 托管组 / 开源组 |
| replication / reproduction | 重复研究（独立复现） / 再现（重跑原代码） |
| protocol deviation | 方案偏离 |
| primary result | 主要结果 |
| principal studies | 主要研究 |
| temporal re-validation | 时间再验证 |
| neologism-substitution pairs | 新词替换句对 |
| as given on 4 October | 10 月 4 日给定的评级 |
| recomputed | 重新计算 |
| oracle (queryable black box, e.g. "oracle for attackers") | 判定接口（oracle）（不用“预言机”） |
| headline study | 重点研究 |
| escalate to a stronger reasoner | 升级至更强的推理模型 |
| error target | 错误目标 |

## Terms added on 2026-10-09 (§2.3 governance paradigms, §7.1 verdict)
| English | 中文 |
|---|---|
| governance paradigm | 治理范式 |
| risk-based regulation | 基于风险的监管 |
| platform content governance | 平台内容治理 |
| training-time alignment / constitution / spec | 训练期对齐 / 宪法 / 规范（spec） |
| inference-time guardrails | 推理期护栏 |
| decentralised / polycentric governance | 去中心化 / 多中心治理 |
| intercept (layer) | 拦截（层） |
| model-agnostic | 与具体模型无关 |
| Interim Measures for the Management of Generative AI Services (CAC, 2023) | 《生成式人工智能服务管理暂行办法》（网信办，2023） |
| high-risk system / Annex III | 高风险系统 / 附件三 |
| alternative dispute resolution | 替代性争议解决 |
| by analogy | 类比适用 / 以类比方式 |
| verdict NS / DC / NT | 证据不支持（NS）/ 仅作有条件的检测器（DC）/ 未经测试（NT） |
| precautionary | 审慎原则 |
| What transfers | 可借鉴之处 |
| queryable oracle | 可查询的判定接口（oracle） |
| data minimisation | 数据最小化 |
| surrogate extraction | 替身模型提取 |
