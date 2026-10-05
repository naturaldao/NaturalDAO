# System-1 决策数据来源（精简版）

**目标**：训练一个只做"选一个"的小决策模型。它不出文字，只在一个封闭选项集合里选一项。

**结论**：只保留**原生就是 (state, question, options, target) 四元组**的 System-1 来源。这类数据集自带问题和选项，直接用它们的原生问题；把传统数据集套上我们自己的问题模板是跑偏的——那会把"选一个"变成"按我们的口径重新解释别人的数据"。传统数据集里只有答案简练、选项封闭的才值得改造成选择题少量引入（第 3 节）。

口径：**条数与真值数取自 [data/items.native.report.json](data/items.native.report.json) 的 units[].items / units[].with_targets**（原生四元组线；data/convert-report.json 是已退役的模板线报告，不要用它的数字）；样例全部来自 D:\pol2-raw\ 下各来源 rows.jsonl 的真实行（长文本标 [截断]）。样例是原文节选：**引号里都是源数据原样内容**，中文键名（如"候选数""问题数"）是本文的注释、不是源字段。推荐保留合计 **15,915 条**，其中 **7,017 条带原生真值**。

## 1. 推荐保留：7 个抓取单元 / 6 个数据集（按重要性排序）

### 1.1 jev-distill-v3 — 主力规模来源（SargeDev/jev-distill-corpus-v3）

规模最大，**三种原语齐全且 target 是完整概率分布**的教师蒸馏语料。

| 字段 | 含义 |
|---|---|
| kind | noul（是/否）/ choice（多选一）/ score（分级） |
| state / question | 情境（英文）/ **原生问题** |
| options / target | 候选 / **与其等长的概率分布**（和为 1） |
| family / domain / source | 来源自己的分类，family 决定能力域 |

一条 score 行：

    {"id": "v3_649cb60343c9452c_s", "kind": "score", "question": "Rate claim reliability for this scenario on a 0-5 scale.",
     "state": "A statistic in the draft attributes to a study that says the opposite; additionally is a direct quote from the CEO. [截断]",
     "options": ["0","1","2","3","4","5"], "target": [0.01, 0.01, 0.05, 0.41, 0.51, 0.01], "domain": "fact_checking", "family": "knowledge"}

一条 choice 行：

    {"id": "snake-v1:24be2b4c70cca12f6a8c89ba:action", "kind": "choice",
     "question": "Choose a direction to keep the snake alive and collect food. [截断]",
     "options": ["up", "right", "down"], "target": [0.0, 0.5, 0.5], "state": "{\"coordinates\": \"x increases right; y increases down\", \"direction\": \"right\", \"food\": [5, 5], [截断]"}

保留 **7,756 条**（**100% 带来源自带答案**）。它是唯一撑得起知识推理能力的来源；它的 score 是 **0–5 六档**——不要压成五档，直接用它的原生打分。
实测这 7,756 个 target 的形态：真分布 5,395 / 均匀 1,647 / 伪 one-hot 714（判断方法见 [CONTRACT.md](CONTRACT.md) §2.3；**均匀的那 1,647 条没有信息量**，做校准目标前先剔除）。

### 1.2 open-jev — 规范最好的多问题来源（ZefanCai/Open-Jev）

**同一个 group_id 就是同一个 state 的多个正交问题**，每问自带选项与概率分布，天然多任务。

| 字段 | 含义 |
|---|---|
| group_id | 一个情境；同组多行 = 同一 state 的多问 |
| id | group_id:问题名，如 ...:category |
| kind / question / options / target | 原生 类型 / 问题 / 选项 / 概率分布 |
| state_json / original_line_number | 情境（JSON 串）/ 原始行号，可溯源 |

同一 group（customer-control-v1:42:1，共 6 问）里的两问：

    {"id": "customer-control-v1:42:1:category", "kind": "choice", "question": "Determine the broad category of this support ticket. [截断]",
     "options": ["account: Login, permissions, profile, security", "bug_report: The user is reporting something that is broken or producing errors", "billing: Charges, invoices, refunds, subscriptions", "feature_request: The user is requesting new functionality"],
     "target": [1.0, 0.0, 0.0, 0.0]}

    {"id": "customer-control-v1:42:1:bug_severity", "kind": "score", "question": "How severe is the reported issue? [截断]",
     "options": ["Cosmetic; no impact to functionality", "Broken or degraded feature; workaround exists", "Blocking issue; no workaround exists"],
     "target": [1.0, 0.0, 0.0]}

同组另有 has_reproducible_steps / refund_requested / frustration / churn_likelihood_level。保留 **792 条**（全部带原生 target；6,000 行聚成 792 个情境）。

### 1.3 jev-decisions — agent 工具选择（samatv256/jev-decisions-v1）

唯一"给定情境 → 选哪个工具/动作"的来源，target 是**硬标签**（只选一个），正是小决策模型的典型形态。两个配置形状不同：

| 配置 | 情境 | 候选 | 答案 |
|---|---|---|---|
| general-clean-50k（精选通用 50k） | state.user_goal | answer_options[{label, description}] | **target_index**（整数下标） |
| default（1200 万行，只做浅窗口抽样） | state.user_goal | candidates[{id, name, description}] | target.{candidate_id, action_name} |

general-clean-50k 一条：

    {"question": "Given the current state and available options, which option should be selected?",
     "state.user_goal": "Hello, I'm reaching out from the quality assurance department regarding diamond GIA-6Y7U8I [截断]",
     "answer_options": [{"label": "verify_diamond_origin", "description": "Verifies diamond origin [截断]"}, {"label": "validate_certificate", "description": "Checks certification validity [截断]"}, "... 共 9 个"],
     "target_index": 4, "source": "nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1"}

default 配置一条：

    {"state.user_goal": "Hello, I'm calling about inconsistent soil sensor readings on my farm [截断]",
     "candidates[:3]": [{"id": "tool::diagnose_equipment", "name": "diagnose_equipment"}, {"id": "tool::order_replacement_parts", "name": "order_replacement_parts"}, {"id": "tool::schedule_field_service", "name": "schedule_field_service"}],
     "候选数": 9, "target": {"candidate_id": "tool::schedule_field_service", "action_name": "schedule_field_service"}}

保留 **3,802 条**（general-clean-50k）+ **207 条**（default 浅窗口），两者都 **100% 带来源自带答案**（硬标签 → 单点分布，见 CONTRACT §2.3）。
候选数常在 12–20 个（实测 17 最常见）。**截断候选会改变题目**，建议只取候选较少的行为训练子集，而不是硬砍到 16。


### 1.4 systemone-lite-general — 带 rubric 的合成决策（dwidlee/systemone-lite-general）

情境是结构化 JSON、候选带明确 rubric，**答案是硬标签**。字段：task（任务名）、state（JSON 串）、instructions（原生问题）、criteria_keys / criteria_values（候选代号与语义标签）、label_alias / label_key（正确候选）。

    {"task": "debate.winner", "instructions": "Given the claims and evidence flags, who should win the debate? One letter.",
     "state": "{\"side_a\": {\"label\": \"support\", \"claims\": [{\"text\": \"Open source is always good actually\", \"hard_evidence\": false}]}, [截断]",
     "criteria_keys": ["A", "B"], "criteria_values": ["oppose: Side B — oppose the proposal", "support: Side A — support the proposal"],
     "label_alias": "A", "label_key": "oppose", "meta": "{\"gym\": \"debate_judge\", \"schema\": \"choice\", \"n_options\": 2}"}

保留 **1,479 条**（全部带真值）。

### 1.5 system-one-270m — 日志与告警分诊（kaivoss/system-one-270m-data）

情境是日志/工单，**prompt 里内嵌完整题面**（state 段 + Question 段 + Options 段），另给 letters 与概率分布；一个 state_id 下挂多个问题。字段：prompt、letters、target（**与 letters 对齐的分布**）、label（正确选项语义键）、qtype（实测 200 行里 choice/noul/score = 113/58/29）、state_id。

    {"prompt": "<state>\nI was just posting a question about how to migrate my WordPress site to a new host, and I got a reply that said, \"Sure, we can help you with that. Just give us the domain name and the FTP credentials and we'll get it done.\" [截断]",
     "letters": ["A", "B"], "target": [0.9999, 0.0001], "label": "migration", "qtype": "choice",
     "domain": "forum question", "state_id": "3e1c3d5968ae4037bb12d556a345675a", "entropy": 0.001473}

保留 **447 条**（1,500 行按 state_id 聚合成 447 个情境，**100% 带来源自带答案**）。

### 1.6 procedural-typed-decisions — 一个情境多个类型化问题（tasksource/procedural-typed-decisions）

一行一个 state，**questions 与 answers 是两个 JSON map**，每问自带 type / criteria / instructions，答案带概率分布——这批里"多问题 + 带分布"最完整的。字段：state、questions、answers、task、level。

    {"state": "[{\"item\": \"red clock\", \"category\": \"office\", \"quantity\": 14, \"in_stock\": true}, [截断]", "task": "record_aggregation", "level": 2, "问题数": 5}

    {"question_key": "count_in_category", "spec": {"type": "score", "criteria": ["0","1","2","3","4","5","6","7","8","9 or more"], "instructions": "How many items are in the kitchen category?"},
     "answer": {"type": "score", "score": 6.0, "probabilities": {"0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 1.0, "7": 0.0, "8": 0.0, "9": 0.0}, "confidence": 1.0}}

    {"question_key": "largest_quantity", "spec": {"type": "choice", "criteria": {"purple drill": "purple drill", "blue clock": "blue clock", "brown rope": "brown rope", [截断]}, "instructions": "Among the kitchen items, which has the largest quantity?"},
     "answer": {"type": "choice", "choice": "brown rope", "probabilities": {"purple drill": 0.0, "blue clock": 0.0, "brown rope": 1.0, [截断]}, "confidence": 1.0}}

保留 **1,500 条**（**100% 带来源自带答案**）。一个情境挂多个问题，英文侧共 4,691 个 target：伪 one-hot 3,696 / 真分布 432 / 只有 answer 545 / 均匀 18。

## 2. 合计与目标

| 数据集 | 保留条数 | 带来源自带答案 |
|---|---:|---:|
| jev-distill-v3 | 7,756 | 7,756 |
| jev-decisions（两个配置合计） | 4,009 | 4,009 |
| procedural-typed-decisions | 1,500 | 1,500 |
| systemone-lite-general | 1,479 | 1,479 |
| open-jev | 792 | 792 |
| system-one-270m | 447 | 447 |
| **合计** | **15,983** | **15,983（100%）** |

- 契约总量下限 10,000 条：**只用 System-1 来源就到 15,983 条，不需要靠传统数据集凑数。**
- **每个条目都带来源自己的答案（100%）**，但要分清形态（见 [CONTRACT.md](CONTRACT.md) §2.3）：真分布与硬标签单点分布
  在字段上长得一样，**不能一律当概率用**。本目录实测：真分布 7,520 个问题 / 伪 one-hot 14,119 / 均匀 1,730 / 只有 answer 11,565
  英文侧 23,914 个 target 的形态分布为 真分布 7,520 / 伪 one-hot 14,119 / 均匀 1,730 / 只有 answer 545，中文侧 11,020 个 target 全部是「只有 answer」。）
- 已知空洞：以上全是英文情境，**PoL2 的判定轴（爱/恨、同意撤回、批评与人格等）不在其中**——由 PoL2 专项语料承担，不要用通用数据集硬凑。

**现状**：原生版本已经落地——**items.native.jsonl，15,983 条，100% 带原生真值**（23,914 个问题 / 3,729 个来源原生键；条目直接使用来源的 state / question / options / target，键名就是来源自己的问题名）。模板版 **items.jsonl（37,124 条）**与 **items.bilingual.jsonl** 保留作对照，已不是训练首选。

## 3. 传统数据集的处理原则

传统数据集（伦理判断、情感/毒性标注、对话安全等）的共性是：**只有情境和标签，没有"选项"**，标签还来自与我们无关的标注口径。

- **默认不要**：它们的标签是"人类怎么想"，不是"该选哪个"；套上我们的模板，模型学到的是我们的解释而不是数据。
- **唯一可考虑的情形**：封闭标签集 + 答案简练（一个词/短语）。做法是保留原生问题（若有），把源标签作为**其中一个选项**，其余选项从该数据集**自己的标签集**里取（例如毒性数据集就在 toxic 与 non-toxic 之间选），转成 choice。**不需要模型生成选项。**
- **直接不要**：自由文本答案、长答案、多标签、没有明确选项空间的数据集。
- 定位：这类来源最多当**评测对照或小规模补充**，不进训练主力；先看 System-1 部分的训练效果再决定。

## 4. 许可摘要

保留的 6 个数据集许可都干净，且都固定在 40 位 commit sha 上（逐条见 [sources.json](sources.json) 的 license 与 revision 字段）：apache-2.0（jev-distill-corpus-v3、system-one-270m、procedural-typed-decisions）、cc0-1.0（Open-Jev）、mit（systemone-lite-general）、cc-by-4.0（jev-decisions-v1，署名即可）。**全部允许训练与衍生发布，没有 NC（非商业）或 SA（同许可传染）条目。**
