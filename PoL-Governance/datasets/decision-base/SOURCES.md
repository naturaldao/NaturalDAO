# 通用决策底座：数据来源说明（v0.1）

面向决策者的取材说明。读完这份不用看代码，就能回答三个问题：**数据从哪来、为什么有的有真值、为什么英文情境配中文问题。**

数字口径：条目与真值数字来自 [data/convert-report.json](data/convert-report.json)（表下标注字段名）；来源属性来自 [sources.json](sources.json)；配额与问题键分布来自 [coverage.py](coverage.py) 的报告（命令见文末）。契约与字段定义见 [README.md](README.md)，问题键定义见 [taxonomy.py](taxonomy.py)。

## 1. 一句话结论

从 **13 个 Hugging Face 仓库**（18 个 config/split 抓取单元）取了 **43,400 行**原始记录，转成 **37,124 条**决策条目，其中 **16,717 条带真值（45.03%）**，其余 20,407 条是"只有情境、等外部答案源作答"的问题集。

| 指标 | 数值 | 字段 |
|---|---:|---|
| 抓取单元 / HF 仓库 | 18 / 13 | sources.json **sources[].dataset** 去重 |
| 原始行数 | 43,400 | convert-report **units[].rows_read** 求和 |
| 条目数 | 37,124 | **items** |
| 带真值条目 | 16,717（45.03%） | **items_with_targets** / **native_target_rate** |
| 待外部作答 | 20,407 | **pending_external_answers** |
| 问题总数 | 121,389（平均 3.27 问/条） | coverage 报告 **questions** |
| 用到的 taxonomy 键 | 17 / 75 个 | coverage 报告 **distributions.question_key** |
| 语言 | 100% en（state） | coverage 报告 **distributions.lang** |
| 最大单一来源占比 | 20.89%（jev-distill-v3） | coverage 报告 **quotas.source_shares** |

覆盖域（**by_domain_detail**，括号内为真值率）：

| 覆盖域 | 条目 | 真值率 | 主要由谁提供 |
|---|---:|---:|---|
| decision_mechanics | 11,557 | 60.7% | jev-distill 的 agent/technical 等 family、Open-Jev、Jev Decisions、System-One 系列 |
| social_moral | 11,352 | 26.4% | ProsocialDialog、ETHICS、Moral Stories |
| human_judgment | 5,491 | 54.5% | Civil Comments、HelpSteer2 |
| risk_harm | 4,366 | 85.0% | Aegis 1.0 / 2.0 |
| knowledge_reasoning | 4,358 | 0% | jev-distill 的 knowledge/medical/物理化学等 family |
| pol2_axis | 0 | — | **不由本底座承担**（见 [sources.json](sources.json) 的 quotas.domain_min_reason，留给 PoL2 语料） |

## 2. 逐源说明

"数据怎么产生"一列是判断可信度的关键：**教师蒸馏出来的概率是教师信念，不是现实真值**；真人标注才是人类判断。

### 2.1 决策机制类（decision_mechanics，11,557 条）

| 来源 slug | 取了什么 | 行 → 条 | 真值率 | 数据怎么产生 | 为什么选它 |
|---|---|---:|---:|---|---|
| jev-distill-v3 | state / question / options / target 概率分布 / family / domain | 8,000 → 3,398 | 13.6% | 教师蒸馏（Jev 1.13 生成 noul/choice/score 三原语 + 完整概率分布），**是行为先验不是真值** | 规模最大、概率分布最完整；同时是唯一提供 knowledge_reasoning 的来源（另 4,358 条） |
| open-jev | group_id 内 6 个源问题及其分布、original_line_number | 6,000 → 792 | 100% | 合成受控任务（作者自建生成器，卡面自述与 TypeSafe 无关、非官方训练数据） | 工程规范最好：group 内 6 个正交问题聚成一条、可逐行溯源、许可最干净（CC0） |
| jev-decisions-general-50k | state(user_goal) / answer_options / target_index | 4,000 → 3,802 | 52.1% | 混合：NVIDIA Nemotron 轨迹 + Open-SWE，作者按 group 划分并给出通用精选 50k | 唯一提供 **agent 工具选择**（下一步调哪个工具）的来源，这正是"决策机制"的核心能力 |
| jev-decisions-strata | 同上（default 配置） | 400 → 139 | 43.9% | 同上 | 只为对照 default 与 general-clean-50k 的分布差异，**不是训练用规模来源** |
| systemone-lite-general | state(JSON) / instructions / criteria / label_alias | 1,500 → 1,479 | 100% | 合成 gym（辩论裁决、工单紧急度等工作流，带 rubric） | 候选来自条目本身、带明确 rubric，是真值干净的决策样本 |
| system-one-270m | prompt 内嵌 state/选项 + letters/target 分布 | 1,500 → 447 | 84.3% | 教师蒸馏 | 日志与告警分诊场景，与上者同构但规模最小 |
| procedural-typed-decisions | questions / answers 两个 JSON 字段（多问题 + 概率） | 1,500 → 1,500 | 85.0% | tasksource 对既有数据集的规范化（**不是教师产物**） | 唯一提供**多问题程序性推理**（算术、排程、信念追踪）并带分布的来源 |

### 2.2 真人判断类（human_judgment，5,491 条）

| 来源 slug | 取了什么 | 行 → 条 | 真值率 | 数据怎么产生 | 为什么选它 |
|---|---|---:|---:|---|---|
| civil-comments | text + toxicity 等 7 列标注者比例 | 3,000 → 2,991 | 100% | 真人众包标注：每条由多位标注者独立判定，字段值是**判为 toxic 的标注者比例（0–1）** | 唯一提供**真实多人 vote 分布**的来源，正是"概率优先于硬标签"最想要的监督信号 |
| helpsteer2 | prompt + response + 5 个人类 0–4 分 | 2,500 → 2,500 | 0% | 真人评分（helpfulness/correctness/coherence/complexity/verbosity） | 真人质量判断样本；但我们的问题键表里没有对应键，故只作情境（见第 3 节） |

### 2.3 社会道德类（social_moral，11,352 条）

| 来源 slug | 取了什么 | 行 → 条 | 真值率 | 数据怎么产生 | 为什么选它 |
|---|---|---:|---:|---|---|
| prosocial-dialog | context 作 state；response/rots/safety_label/三人标注进 meta | 4,000 → 3,998 | 0% | GPT-3 生成"可能不合适的言论" + 众包工作者标注（3 人）+ 众包亲社会回应 | 唯一提供**亲社会回应**语料（识别问题言论 → 建设性回应），对应 EAP 的"识别恨 → 转化" |
| ethics（5 个 config） | input/scenario/baseline 作 state，label 进 meta | 5,000 → 4,354 | 0% | 众包/作者标注，单标签二分类 | 经典伦理判断语料；但各 config 的 label 语义卡面未逐项说明，本轮不映射真值 |
| moral-stories | situation + intention + 正反两个行动与其后果 | 1,500 → 3,000 | 100% | 众包结构化叙事（作者校验） | 唯一提供**动机 → 行为 → 后果**结构，一行展开正反两条，天然适合"同一情境两个行为"的对照 |

### 2.4 风险与伤害类（risk_harm，4,366 条）

| 来源 slug | 取了什么 | 行 → 条 | 真值率 | 数据怎么产生 | 为什么选它 |
|---|---|---:|---:|---|---|
| aegis2 | prompt/response + safe/unsafe 标签 + 标注来源 + violated_categories | 3,000 → 2,889 | 77.3% | prompt 取自 Anthropic HH-RLHF / DAN 等；**对话整体安全标签是人类标注，response 标签可能由 3 个 LLM 集成生成**（卡面明写） | 唯一把 prompt 与 response 分开标注、且**逐行声明标注来源**的安全数据，可精确只取人类标签 |
| aegis1 | text + labels_0..4（多位标注者的类别串） | 1,500 → 1,477 | 100% | 12 人标注团队 + 2 名 QA，一条由 3–5 人独立打类别 | 唯一提供**安全类别的多标注者投票比例**（Safe → 无害，其余 → 有害） |

许可与固定版本：全部 18 个单元都固定在 40 位 commit sha 上，许可是 apache-2.0 / mit / cc0-1.0 / cc-by-4.0（无 NC、无 SA）——逐条见 [sources.json](sources.json) 的 sources[].license 与 sources[].revision。证据等级 A/B 见 sources[].evidence。

## 3. 为什么有的条目有真值、有的没有

真值的唯一判据是：**源数据是否真的给出了某个 taxonomy 问题的答案**。分三层（**mapping_classes**）：

| 层级 | 说明 | 映射数 | 谁属于这一层 |
|---|---|---:|---|
| direct | 源字段**本身就是**该问题的答案 | 13,008 | civil-comments（标注者比例 → toxicity_present 的 yes/no 概率）、moral-stories（卡面写明 label 0=不道德 / 1=道德 → moral_judgment）、jev 系列的候选选择（→ next_step_candidate）、jev-decisions（硬标签，**只有 answer 不给 probs**） |
| documented | 需要一次**有卡面证据**的标签映射 | 6,709 | aegis2 的 human safe/unsafe → contains_harm；aegis1 的多标注者票 → contains_harm；moral-stories 的后果字段配对 → expected_consequence |
| 无 | 对不上任何键，只保留情境 | 20,407 条条目 | Open-Jev 的 6 个源问题、ProsocialDialog 的三值安全票、HelpSteer2 的 5 个质量分、ETHICS 的 label |

注：moral-stories 的 3,000 条同时带 direct 与 documented 两类映射，所以带真值条目 = 13,008 + 6,709 − 3,000 = **16,717**。

三条硬规则（[sources.json](sources.json) 的 policy.truth）：

1. **单标签不得伪装成概率**——jev-decisions 的正确答案只有一个，条目里就只写 answer，不编 probs；只有源数据真的给了分布（jev-distill 的教师分布、civil-comments 的标注者比例、aegis1 的投票）才写 probs。
2. **不硬压档位**——jev-distill 的 score 是 0–5 六档，taxonomy 的分级键是 0–4 五档，两者不重合时宁可不要真值，也不做换算。
3. **映射不上的答案不丢**——原始问答/选项/分布原样存进 meta.source_record（单字段超 4KB 会截断并留 sha256 与原始长度），targets 留空等外部答案源；这一步由 [ask.py](ask.py) 的 harness 接手。

为什么对不上，无非三种情况：

- **键名不在词表**：Open-Jev 的 category / bug_severity / has_reproducible_steps 是它自己的任务键；ProsocialDialog 的 casual / needs caution / needs intervention 是它自己的安全阶梯。把它们硬塞进 taxonomy 会造出同义标签，跨来源就没法比较（[../../research/Wenbo/data.md](../../research/Wenbo/data.md) 第 10 节把这种"合在一起训"的后果称为统计平均意义上的浆糊）。
- **档位不同**：见上。
- **语义未核实**：ETHICS 五个 config 的 label 哪一侧是 1，卡面没有逐 config 说明。**没核实就不映射**，label 原样进 meta，条目仍以 state 形式入库。

## 4. state 是 HF 的英文原文，question/options 是本地 taxonomy 生成的

这是最容易被误读的一点：**3 万多条英文不是"数据的语言"，而是"情境的语言"；问题是我们自己出的。**

### 4.1 谁生成、什么语言

| 内容 | 谁生成 | 语言 | 例子（取自真实条目） |
|---|---|---|---|
| **state**（情境） | HF 来源原文，未经改写 | **英文**（coverage 报告：lang 分布 en 100%） | "Conversation with account holder Harbor-65673ba098. Customer message: I need access restored…" |
| **questions[].prompt** | 本地 [taxonomy.py](taxonomy.py) | **中文**（convert-report 的 question_lang = zh） | "在这个情境下，下一步最合适的动作是什么？" |
| **options 的 key** | 本地 taxonomy | 英文小写枚举（语言无关的标签空间） | direct_answer / use_tool / ask_clarification |
| **options 的 label** | 本地 taxonomy | **中文** | "直接作答" / "调用工具" / "先澄清" |
| **next_step_candidate 的候选**（7,017 条） | HF 来源原文（候选来自条目本身） | **英文** | "account: Login, permissions, profile, security" |
| **targets 的 answer / probs 键** | 本地 taxonomy 的选项 key | 英文枚举 | answer 取 acceptable / wrong；probs 取 yes 与 no |
| source / meta | [fetch.py](fetch.py) / [convert.py](convert.py) | 结构化 | dataset / revision / config / split / row / license / url |

所以"为什么问题和选项跟那 3 万多条英文不同语言、不同来源"的答案是：**情境取自别人（英文），问题是我们自己出的（中文）**。只有 7,017 条 next_step_candidate 的候选文本是从来源里原样带过来的，而它的问题提示词仍是中文。

### 4.2 为什么这么设计

- **状态与问题分离**是契约的第一条原则（[README.md](README.md) 第 1 节）：state 是"待判断的东西"，question 是"我们要问的东西"。
- **来源自带的问题不可复用**：每家一套键名和档位（第 3 节）。如果照搬，"有没有伤害倾向""要不要介入"这类问题在 13 个仓库里会变成十几种写法，无法汇总、无法算覆盖。
- **只有共享键表才能形成底座**：37,124 条来自 13 个仓库的 state 之所以能落进同一个标签空间、能算出五域覆盖，就是因为问题由本地键表统一生成。
- **state 不做静默翻译**：契约要求保留源语言（lang 字段），翻译质量与语义漂移不可控，中文改写必须是**独立、可审计**的后续步骤。

### 4.3 对"中英双语"意味着什么

| 你的目标 | 现在这份产物 | 需要做什么 |
|---|---|---|
| 英文情境 + 中文问题 | 就是现状（question_lang=zh） | 直接可用 |
| 英文情境 + 英文问题 | 一个开关 | 重跑转换并加 --question-lang en，state 与 targets 不变，只有 prompt 与 option label 变英文（约 2–3 分钟，可离线，命令见文末） |
| 中文情境 + 中文问题 | 中文条目 0 条 | 必须走"改写 + 重判"流水线（[../pol2/replay/rewrite.py](../pol2/replay/rewrite.py) 有同构做法），**不能只翻译问题**——情境的语言决定模型看到什么 |
| 中英混训同一批标签 | 设计上支持 | 选项 key 与语言无关，中英两版 targets 的取值集合完全一致，可直接对齐 |

一句话：**这份底座提供的是"英文情境 + 统一问题空间"，中文能力需要另一条线补；而问题空间本身已经语言中立（key 不随语言变），所以补中文情境不会推翻已有标注。**

## 5. 精简建议：18 个来源里哪些可以砍

判断依据三条：**真值率**（有没有监督信号）、**独特性**（砍掉后有没有别的来源顶上）、**规模贡献**。不建议只按条数砍。

### 5.1 建议移出训练集（保守方案：−6,440 条，37,124 → 30,684）

| 来源 | 条数 | 真值率 | 独特性 | 建议 | 理由 |
|---|---:|---:|---|---|---|
| ethics-deontology | 359 | 0% | 低 | 移出 | 与其余 ETHICS config 同构（短伦理情境 + 无真值）；且 1,000 行里 641 行因去重被丢 |
| ethics-justice | 1,000 | 0% | 低 | 移出 | 同上 |
| ethics-utilitarianism | 997 | 0% | 低 | 移出 | 两两比较、源数据本身没有 label |
| ethics-virtue | 998 | 0% | 低 | 移出 | 同上 |
| helpsteer2 | 2,500 | 0% | 低 | 移出 | state 是"提问 + 整段回答"的长文本，衡量的是回答质量而非决策轴；问题键表里没有对应键，暂时只能当情境 |
| jev-decisions-strata | 139 | 43.9% | 低 | 移出 | 与 general-50k 同源同结构，只为分布对照；建议只留报告记录，不进训练集 |
| system-one-270m | 447 | 84.3% | 中 | 移出 | 与 systemone-lite 同为"单问候选选择"；它是三个 System-One 来源里条数最少的（447） |

**这四条不建议砍**（砍掉就会出现能力空洞）：

- **jev-distill-v3**（7,756 条，真值率仅 13.6%）：真值率低是因为它多数的行是 noul/score，档位对不上；但它同时是**唯一**的 knowledge_reasoning 来源（4,358 条），砍掉该域直接归零。
- **prosocial-dialog**（3,998 条，0% 真值）：唯一亲社会回应语料。
- **civil-comments**（2,991 条，100% 真值）：唯一真实多人 vote 分布。
- **aegis1**（1,477 条，100% 真值）：唯一提供安全类别的多标注者投票比例；aegis2 的 human 行是单一标签，替代不了它。

### 5.2 精简后的域覆盖（推算值）

按 [data/convert-report.json](data/convert-report.json) 的 units[].by_domain 相减推算，**不是实测**：

| 覆盖域 | 精简前 | 精简后 | 下限 |
|---|---:|---:|---:|
| decision_mechanics | 11,557 | 10,971 | 1,200 通过 |
| social_moral | 11,352 | 7,998 | 1,200 通过 |
| human_judgment | 5,491 | 2,991 | 1,200 通过 |
| risk_harm | 4,366 | 4,366 | 1,200 通过 |
| knowledge_reasoning | 4,358 | 4,358 | 1,200 通过 |
| 合计 | 37,124 | 30,684 | 10,000 通过 |

执行方式：从 [sources.json](sources.json) 删掉对应条目后重跑 [convert.py](convert.py)（约 2–3 分钟，原始数据已在库外，不需重新下载），再跑 coverage.py 复核。若只想先看效果，可先重跑并加 --source 列出要保留的 slug。

### 5.3 更激进的一档（−2,477，合计 28,207）

再砍 ethics-commonsense（1,000 条，0% 真值）与 aegis1（1,477 条）。**不推荐**：前者是 ETHICS 里字段最规整的 config（将来若核实了 label 语义，它是最容易升级成有真值的一批），后者是唯一的投票分布来源。省下 2,477 条换不来什么，却让风险域失去一种监督形态。

## 6. 已知污染与陷阱

### 6.1 明确排除的来源（[sources.json](sources.json) 的 excluded，共 9 条）

| 来源 | 排除理由 | 类别 |
|---|---|---|
| Praveenrajus/jev-bench | 全部 config 都是 test 划分的排行榜基准，只能作外部评测，**不得进训练集** | 评测集本体 |
| PKU-Alignment/PKU-SafeRLHF | 许可 CC-BY-NC-4.0，非商业限制与公开发布冲突 | 许可 |
| HIT-TMG/JevEmbed-Data | 许可逐行给出（apache/cc0/cc-by 混合），按行过滤未完成前不进池 | 许可（逐行） |
| tasksource/tasksource-jev-typed-decisions | 卡面 license=other，逐行条款未判读完成 | 许可（待判读） |
| allenai/wildguardmix | 匿名抓取返回 401；且 wildguardtest 是公开测试集 | 可达性 + 评测集 |
| allenai/social_chem_101 | HF API 401（id 不存在或受限） | 可达性 |
| google/goemotions | HF API 401 | 可达性 |
| nyu-mll/chaosNLI | HF API 401 | 可达性 |
| soyrsoyr/jev-playground-rlcd-v0 | datasets-server 返回 500（No supported data files） | 可达性 |

### 6.2 审计发现、必须知道的坑（来自 [../pol2/replay/survey.md](../pol2/replay/survey.md)）

- **同一份 Open-Jev 有 3 个再发布**（ZefanCai / TypeSafeAI / OpenAGILab，都是 236 个文件，其中两家的 README 逐字节相同）。不按内容哈希去重，会把同一批 26.7 万行算成三份——本底座只取 ZefanCai 一份。
- **"训练混合包"里可能藏着公开评测基准**：s1lv3rj1nx/openjev-mixture 的 train 目录含 92 个公开评测任务（52 个 bigbench、12 个 mmlu、arc、hellaswag、glue 等），一旦进池，外部 benchmark 数字全部失效。
- **评测集的译本最容易误收**：GeneLab/typed-decisions-ja、telepatia-ai/typed-decisions-pt-es、yyhlm/typed-decisions-ru 自带 Apache-2.0 卡面、结构干净，本体却是别家的 benchmark。
- **标签已知反向的版本要点名禁用**：pngwn/typed-decisions v1 的 escalate 标签 100% 与其定义互补，v2 才修好。
- **"文档语料"长得像决策数据**：ctaxnagomi/INSTRUCT_JEV 卡面写 choice/noul/score，实际 119 行里只有 7 行带答案。
- **没有真值的数据不能靠模型输出补**：com-kotobalabs/typed-decisions-repo-governance 的 gold 全是 null，卡面自己写明 prediction 不得当真值。

### 6.3 抓取与格式上的坑（我们自己在流水线里踩过并已处理）

- **datasets-server 不遵守 revision 参数**：伪造 sha、别的数据集的 sha、不传 revision，返回的首行完全相同。所以 manifest 写 revision_enforced=false，改由"抓取前后用 HF API 解析 sha 并比对 + 抓取结束复查"来保证（[fetch.py](fetch.py)）。真正逐字节复现需走 resolve 加 sha 加路径的直取方式。
- **深 offset 不可用**：1200 万行数据集上 offset=3,000,000 的一次请求要 109 秒，offset=6,000,000 直接断连。因此大表不做全域均匀抽样。
- **配置名里的加号必须转义**（否则被解析成空格，404）；length 上限 100。
- **U+2028 会劈断 JSONL**：曾出现 22 处，任何用 str.splitlines() 的消费者都会把记录读断。convert.py 现已统一转义。
- **一行产出多条会撞 id**：moral-stories 一行给正反两条，id 派生加了 variant（source.row 仍是原行号）。
- **Aegis2 的 response 标签可能是 LLM 集成生成**：只有逐行标注来源为 human 的行才给真值。


## 7. 核查与复现

以下命令都在仓库根目录执行；重新转换不需要联网（原始数据已在仓库外的 D:\pol2-raw）。

    # 覆盖与配额报告（本文所有配额与问题键数字的来源；--json-out 写到仓库外，避免污染 data/）
    uv run --no-project --offline python datasets/decision-base/coverage.py --items datasets/decision-base/data/items.jsonl --json-out D:\pol2-raw\coverage-report.json

    # 重新转换：英文情境 + 英文问题版本
    uv run --no-project --offline python datasets/decision-base/convert.py --raw-root D:\pol2-raw --question-lang en --out D:\pol2-raw\items.en.jsonl

    # 只要部分来源（先看精简效果）
    uv run --no-project --offline python datasets/decision-base/convert.py --raw-root D:\pol2-raw --source jev-distill-v3 --source open-jev

    # 离线测试：27 + 53 项
    uv run --no-project --offline python -m unittest discover -s datasets/decision-base -p "test_fetch.py" -q
    uv run --no-project --offline python -m unittest discover -s datasets/decision-base -p "test_convert.py" -q

产物：data/items.jsonl.gz（压缩后提交；同一目录下的明文 items.jsonl 供本机工具使用，不进库）。同一命令重建两次，items.jsonl 逐字节一致（sha256 5A64912AB599228B6F4C359B9D9643BA9A6DE54FFA7CECFFB55464844C09EBAF），可复算。
