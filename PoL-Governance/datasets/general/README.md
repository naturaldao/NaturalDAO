# 通用决策数据集 general（v0.1）

给**只做"选一个"的小决策模型**用的中英双语语料：**23,855 条，100% 带真值**，已按请求分组切成
train / test / validation / benchmark 四个分区。

新人从这一页开始看就够；字段与格式细节在 **[CONTRACT.md](CONTRACT.md)**。

| 我想知道 | 看这里 |
|---|---|
| 字段怎么定义、三种原语什么形状 | [CONTRACT.md](CONTRACT.md) |
| 英文侧每个来源是什么、为什么选它 | [SOURCES.md](SOURCES.md) |
| 最终语料怎么合出来的、中文占比为什么是 33% | [merge-report.md](merge-report.md) |
| 四个分区各有多少条、怎么切的、泄漏检查 | [split-report.md](split-report.md) |
| 每条记录省了多少字段（manifest + 紧凑引用） | [slim-report.md](slim-report.md) |
| 目录里每个脚本干什么、哪些已过时 | [ARCHIVE.md](ARCHIVE.md) |

## 1. 我们用了什么思路

### 1.1 目标模型只做"选一个"，不生成文字

它要能快速在**封闭候选集**里选一项，而不是像 LLM 那样逐字生成。这决定了数据必须尽量是原生的
**(state, question, options, target) 四元组**：情境、问题、候选、答案都现成。

### 1.2 为什么优先用来源原生的问题

把别人的分类数据套上我们自己的中文问题模板，会把"选择"变成"**按我们的口径重新解释别人的数据**"：
模型学到的将是我们的解释，而不是数据本身。所以：

- 来源自带问题的（System-1 系）：**直接用它的 state / question / options / target**，键名就用来源的原生问题名，
  不改写、不翻译、不压档位（例如来源是 0–5 六档就保留六档）。
- 来源确实没有问题的：才由本地 taxonomy 出题（这是次选，origin=taxonomy）。

### 1.3 三种原语

| 原语 | 含义 | 答案形态 | 例 |
|---|---|---|---|
| **choice** | 多选一，选项 2 个以上（实测最多 57 个） | 概率分布或硬标签 | 选哪个工具 / 哪个类别 |
| **noul** | 是 / 否 | 概率分布或硬标签 | 这条记录是否相关 |
| **score** | 整数分级（各来源档位不同，0–2 / 0–5 / 0–9 都有） | 概率分布 | 严重程度打分 |

只用这三种，是因为它们正好覆盖"选一个"的全部形态；**不发明第四种**。

### 1.4 中英构成与 33% 的取舍

| | 条数 | 占比 | 来源数 | 覆盖原语 |
|---|---:|---:|---:|---|
| 英文 en | 15,983 | 67% | 6 个 HF 仓库（7 个抓取单元） | choice / noul / score |
| 中文 zh | 7,872 | 33% | 1 个（Deepexi） | choice |

**为什么中文取 33% 而不是上限 40%**：Deepexi 是唯一中文来源，中文占比就等于该来源占比。
取到 40% 会正好顶满契约"单一来源 ≤ 40%"的线、没有余量；而多取的是**同一批请求的变体**，
边际信息量递减。33% 既落在 30–40% 区间里，又给以后第二个中文来源留出头寸。
（详见 [merge-report.md](merge-report.md)；抽取种子 general-merge-v1，可复算。）

### 1.5 成色分层（做训练决策必读）

| 层级 | 是什么 | 条数 | 真值形态 | 进 benchmark？ |
|---|---|---:|---|---|
| **A. 原生四元组** | 来源自带 state/question/options/target，我们只搬运 | **23,855（100%）** | 来源的概率分布，或来源自己的硬标签 | **是（只有这一层）** |
| B. 单标签转换的补充 | 数据只有"这条属于 X 类"，我们把 X 当正确选项、再从**同一标签集**取其余选项凑成 choice | 暂未引入（中文 noul/score 补充，task-21） | 硬标签 + documented 映射 | **否** |

**怎么用**：A 层可以直接进训练与 benchmark；B 层是**成色降级**的补充，**只进 train**，
不进 validation / test / benchmark，训练时也要与 A 层分开报告。内部 benchmark **只含 A 层**。

### 1.6 一条数据里的语言分工

| 内容 | 来自哪 | 语言 |
|---|---|---|
| state（情境） | 来源原文 | 英文条目的 state 是英文，中文条目的 state 是中文 |
| questions 的 key / prompt | 来源原生问题名与原文（英文侧）；中文侧候选来自来源、题面由 taxonomy 出 | 英文侧英文；中文侧中文 |
| options | 来源原文（含中文侧已被确定性打散顺序的候选菜单） | 随来源 |
| targets | 来源自带答案；有分布存分布，只有硬标签就只写 answer | 语言无关 |

## 2. 开源来源清单 + 真实例子

### 2.1 英文侧：6 个 HF 仓库 / 7 个抓取单元，15,983 条

| 来源 | HF 链接 | 许可 | 固定 revision | 一句话 | 条数 |
|---|---|---|---|---:|
| jev-distill-corpus-v3 | [SargeDev/jev-distill-corpus-v3](https://huggingface.co/datasets/SargeDev/jev-distill-corpus-v3) | apache-2.0 | fc99c6357a9f | 教师蒸馏的三原语语料，**带完整概率分布**，规模主力 | 7,756 |
| jev-decisions-v1 | [samatv256/jev-decisions-v1](https://huggingface.co/datasets/samatv256/jev-decisions-v1) | cc-by-4.0 | c12aadf1f01c | agent **工具选择**（通用精选配置），硬标签 | 3,802 |
| procedural-typed-decisions | [tasksource/procedural-typed-decisions](https://huggingface.co/datasets/tasksource/procedural-typed-decisions) | apache-2.0 | 609513a3fadd | **一个情境挂多个类型化问题**，带概率 | 1,500 |
| systemone-lite-general | [dwidlee/systemone-lite-general](https://huggingface.co/datasets/dwidlee/systemone-lite-general) | mit | c14eb7f7518f | 合成 gym（辩论裁决、工单紧急度），硬标签 | 1,479 |
| Open-Jev | [ZefanCai/Open-Jev](https://huggingface.co/datasets/ZefanCai/Open-Jev) | cc0-1.0 | c67699e13d0a | 同一请求下**多个正交问题**，规范最好、可逐行溯源 | 792 |
| system-one-270m-data | [kaivoss/system-one-270m-data](https://huggingface.co/datasets/kaivoss/system-one-270m-data) | apache-2.0 | f31d5a3f3da8 | 日志与告警分诊，带概率 | 447 |
| jev-decisions-v1（default 配置） | 同上 | cc-by-4.0 | c12aadf1f01c | 1200 万行里做的浅窗口抽样，仅作分布对照 | 207 |

逐来源的取材理由与陷阱见 [SOURCES.md](SOURCES.md)；来源清单机器可读版见 [sources.json](sources.json)。

### 2.2 中文侧：1 个来源，7,872 条

| 来源 | HF 链接 | 许可 | 固定 revision | 说明 | 条数 |
|---|---|---|---|---:|
| Deepexi 函数调用 | [Deepexi/openai-formate-function-calling-small](https://huggingface.co/datasets/Deepexi/openai-formate-function-calling-small) | apache-2.0 | 6d1dc02a2549 | 中文用户请求 + 候选工具菜单 + 正确工具；从 5,454 个唯一请求按变体抽到 33% 占比 | 7,872 |

中文侧调研与准入见 [zh-survey.md](zh-survey.md)、构建说明见 [zh-build-report.md](zh-build-report.md)、
清单见 [sources.zh.json](sources.zh.json)。

### 2.3 真实例子（取自最终语料，长文本标 [截断]）

**例 1 · 英文 choice：从候选菜单里选正确的一个（Open-Jev，同一请求下共 6 个问题）**

    state: "Conversation with account holder Harbor-65673ba098.
            Customer message: I need access restored after changing the email address [截断]"
    questions[0]: key="category"  kind=choice   ← 键名就是来源自己的问题名
      options: [{"key":"account_login_permission","label":"account: Login, permissions, profile, security"},
                {"key":"bug_report_the_user_is_r","label":"bug_report: The user is reporting something broken"},
                {"key":"billing_charges_invoices","label":"billing: Charges, invoices, refunds, subscriptions"},
                {"key":"feature_request_the_user","label":"feature_request: The user is requesting new functionality"}]
    targets["category"]: {"answer":"account_login_permission",
                          "probs":{"account_login_permission":1.0,"bug_report_the_user_is_r":0.0, ...}}   ← 来源给的是分布

**例 2 · 英文 choice：来源只有硬标签，就只写 answer + 单点分布（systemone-lite-general）**

    state: "{\"ticket\": {\"subject\": \"Production outage: checkout broken\", \"tier\": \"enterprise\", ...}}"
    questions[0]: key="ticket.urgency"  kind=choice
      options: [{"key":"1_medium_same_day","label":"1: medium — same day"},
                {"key":"0_low_can_wait","label":"0: low — can wait"},
                {"key":"2_high_immediate","label":"2: high — immediate"}]
    targets["ticket.urgency"]: {"answer":"2_high_immediate",
                                "probs":{"1_medium_same_day":0.0,"0_low_can_wait":0.0,"2_high_immediate":1.0}}

**例 3 · 英文 noul 与 score：保留来源自己的档位（jev-distill-corpus-v3）**

    noul:  state "The log shipper shows a 22% drop in request rate with no deploys [截断]"
           key "Is this scenario one where: this can wait until morning?"  kind=noul
           options [{"key":"false","label":"false"},{"key":"true","label":"true"}]     ← 原样，不改成 yes/no
           target  {"answer":"false","probs":{"false":0.87,"true":0.13}}

    score: state "A statistic in the draft attributes to a study that says the opposite [截断]"
           key "Rate claim reliability for this scenario on a 0-5 scale."  kind=score
           scale {"min":0,"max":5,"labels":["0","1","2","3","4","5"]}                  ← 六档原样保留，不压成 0-4
           target {"answer":"4","probs":{"0":0.01,"1":0.01,"2":0.05,"3":0.41,"4":0.51,"5":0.01}}

**例 4 · 英文：一条条目挂多个问题（procedural-typed-decisions，一次覆盖三种原语）**

    state: "Order lines (prices in €):
            item,unit_price,quantity
            drill,2,1 / vase,20,2 / tent,15,2
            Rule: Orders of €50 or more get €5 off; smaller orders pay €6 shipping."
    questions: largest_line     kind=choice  "Which line costs the most in total?"          options [drill, vase, tent]
               lines_above      kind=score   "Count the lines whose total exceeds €30."      scale 0..9
               random_line_bulk kind=noul    "If one line is picked at random, P(quantity>=2)?" options [yes, no]
               within_budget    kind=noul    "Does the order fit within a budget of €62?"
    targets: largest_line {"answer":"vase","probs":{"drill":0.0,"vase":1.0,"tent":0.0}}
             lines_above  {"answer":"1","probs":{"0":0.0,"1":1.0,"2":0.0, ...}}
             random_line_bulk {"answer":"yes","probs":{"yes":0.666667,"no":0.333333}}      ← 真概率，不是凑的

**例 5 · 中文 choice：候选菜单来自来源（顺序已确定性打散），答案是硬标签（Deepexi）**

    state: "20210101的短信发送状态如何？"
    group_id: "zhgrp-104f0514ee19"        ← 同一请求的多个变体共用一个 group_id（切分按组，不拆开）
    questions[0]: key="next_step_candidate"  kind=choice
      options: [{"key":"ListMessages","label":"ListMessages：按指定过滤条件获取指定日期的短信发送状态。"},
                {"key":"UpdateDISyncTask","label":"UpdateDISyncTask：更新数据集成同步任务。"},
                {"key":"GenerateDISyncTaskConfigForCreating","label":"GenerateDISyncTaskConfigForCreating：异步生成同时任务的JSON。"}]
    targets["next_step_candidate"]: {"answer":"ListMessages"}    ← 来源只给了硬标签，就不编概率

（中文侧的 **noul / score 例子**要等中文补充数据 task-21 交付后补上，见下一节。）

### 2.4 补充数据（中文 noul / score）：只进 train

中文侧目前只有 choice（Deepexi 一个来源）。为补 noul / score，正在做**单标签转换**的补充集
（中文分类数据 + documented 映射，属于第 1.5 节的 **B 层**）：

- **只进 train**，不进 validation / test / **benchmark**；
- 训练时必须与 A 层（原生四元组）分开报告，便于消融；
- 本轮 README 先写约定，数字等交付后补。

## 3. 划分信息

四分区按**请求分组**切分（不是按行），种子 **20261005**，两次运行逐字节一致。

| 分区 | 条目 | 占比 | 请求组 | 英文 | 中文 |
|---|---:|---:|---:|---:|---:|
| train | 14,310 | 60.0% | 14,310 | 9,588 (67%) | 4,722 (33%) |
| test | 4,771 | 20.0% | 4,771 | 3,197 (67%) | 1,574 (33%) |
| validation | 2,385 | 10.0% | 2,385 | 1,598 (67%) | 787 (33%) |
| benchmark | 2,389 | 10.0% | 2,389 | 1,600 (67%) | 789 (33%) |
| 合计 | 23,855 | 100% | 21,376 | 15,983 | 7,872 |

域与原语分布（各区内部占比）：

| 维度 | train | test | validation | benchmark |
|---|---|---|---|---|
| decision_mechanics | 11,677 (82%) | 3,893 (82%) | 1,946 (82%) | 1,949 (82%) |
| knowledge_reasoning | 2,633 (18%) | 878 (18%) | 439 (18%) | 440 (18%) |
| choice | 10,706 (75%) | 3,545 (74%) | 1,780 (75%) | 1,784 (75%) |
| noul | 3,977 (28%) | 1,342 (28%) | 668 (28%) | 680 (28%) |
| score | 2,236 (16%) | 742 (16%) | 367 (15%) | 380 (16%) |

（同一条目可挂多个问题，所以 kind 占比之和超过 100%。）

**为什么必须整组切**：中文侧的多个变体来自**同一个请求**、state 逐字相同，只是候选顺序不同。
按行随机切会把同一请求的变体分到 train 和 test 两侧，**静默泄漏**——测试分数会虚高。
切分器的做法是并查集合并：显式分组键（group_id / request_id，中英两侧都读）与**归一化 state**
各自连边，同一连通分量的条目整组进同一分区。实测：显式分组键 8,664 条，靠 state 或 id 兜底的 15,191 条，
共 21,376 组；多条目组 2,479 个（最大 2 条）。

**泄漏检查（必须为空，实测为空）**：跨分区的组 0、跨分区的同一 state 0、跨分区的 id 0；
复核范围 21,376 组 / 21,376 个不同 state。

**复现**：

    uv run --no-project --offline python datasets/general/data/splits/split.py \
        --items datasets/general/data/items.final.jsonl --out datasets/general/data/splits --seed 20261005

产物与哈希见 [data/splits/split-manifest.json](data/splits/split-manifest.json)；
产物树哈希 2c3fa92c323edbf38147325dd6605220ed9a7b1a64cc0d935201f514533c62f4。
完整报告见 [split-report.md](split-report.md)。

### 3.1 内部 benchmark 的隐私约定

- **不得进公开仓库**：benchmark 分区（2,389 条）与可上传目录 data/splits/benchmark-dataset/ 已在 .gitignore 里；
- **上传时设为 private**，不要放到任何公开分支、fork、PR、日志或截图里；
- **其他人不要引用其内容**：看过逐例答案就不能再自称在它上面是盲测；
- 它只含 A 层（原生四元组），**不含**第 1.5 节 B 层的补充数据。

## 4. 文件在哪

| 文件 | 内容 |
|---|---|
| [data/items.final.jsonl.gz](data/items.final.jsonl.gz) | **最终语料** 23,855 条（明文同名去 .gz，体积大不入库） |
| [data/items.native.jsonl.gz](data/items.native.jsonl.gz) | 英文侧主产物 15,983 条 |
| data/splits/train.jsonl(.gz) 等四份 | 切分产物（benchmark 那份勿公开） |
| data/items.jsonl(.gz) / items.bilingual.jsonl(.gz) | 早期"模板命题"版（37,124 条），**留作对照，不再是训练首选** |

原始下载在仓库外（D:\pol2-raw\）。检查：

    uv run --no-project --offline python tools/check.py
