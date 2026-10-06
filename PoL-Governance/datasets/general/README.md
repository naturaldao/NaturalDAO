# 通用决策数据集 general（v0.1）

给**只做"选一个"的小决策模型**用的中英双语语料，按请求分组切成 train / test / validation / benchmark 四个分区。

| 规模 | 数值 |
|---|---:|
| 切分输入语料（items.final） | **23,855 条**（英文 15,983 + 中文 7,872） |
| 中文补充（只追加进 train） | **3,148 条** |
| **四个分区合计** | **27,003 条**（英文 15,983 + 中文 11,020） |
| 带真值 | **100%**（每条都有来源自带的答案） |

新人从这一页开始看就够；字段与格式细节在 **[CONTRACT.md](CONTRACT.md)**。

| 我想知道 | 看这里 |
|---|---|
| 字段怎么定义、三种原语什么形状 | [CONTRACT.md](CONTRACT.md) |
| 英文侧每个来源是什么、为什么选它 | [SOURCES.md](SOURCES.md) |
| 最终语料怎么合出来的、中文占比怎么定的 | [merge-report.md](merge-report.md) |
| 四个分区各有多少条、怎么切的、泄漏检查 | [split-report.md](split-report.md) |
| 每条记录省了多少字段（manifest + 紧凑引用） | [slim-report.md](slim-report.md) |
| 目录里每个脚本干什么、哪些已过时 | [ARCHIVE.md](ARCHIVE.md) |

> **对外发布面（2026-10-05 定）**：仓库内**只发布三个分区** train / test / validation 及其报告与清单；
> **完整语料与内部 benchmark 都不对外**（七件语料已移出版本控制，仓外留存 D:\pol2-raw\general-private\）。
> benchmark 现在必须用**仓外私盐**才能重建，见 §3.1。

## 1. 我们用了什么思路

### 1.1 目标模型只做"选一个"，不生成文字

它要能快速在**封闭候选集**里选一项，而不是像 LLM 那样逐字生成。这决定了数据必须尽量是原生的
**(state, question, options, target) 四元组**：情境、问题、候选、答案都现成。

### 1.2 为什么优先用来源原生的问题

把别人的分类数据套上我们自己的中文问题模板，会把"选择"变成"**按我们的口径重新解释别人的数据**"：
模型学到的将是我们的解释，而不是数据本身。所以：

- 来源自带候选与答案的（System-1 系）：**直接用它的 state / options / target**，键名就用来源的原生问题名，
  不改写、不翻译、不压档位（例如来源是 0–5 六档就保留六档）。
- 来源确实没有候选集的：才由本地 taxonomy 出题与补选项（次选，origin=taxonomy，见 [CONTRACT.md](CONTRACT.md) §2.1）。

### 1.3 三种原语

| 原语 | 含义 | 答案形态 | 例 |
|---|---|---|---|
| **choice** | 多选一，选项 2 个以上（实测最多 57 个） | 概率分布或硬标签 | 选哪个工具 / 哪个类别 |
| **noul** | 是 / 否（选项键可能是 false/true 或 no/yes） | 概率分布或硬标签 | 这条记录是否相关 |
| **score** | 整数分级，**各来源档位不同**（实测 3 档 / 6 档 / 10 档 / **11 档**都有） | 概率分布 | 严重程度打分 |

只用这三种，是因为它们正好覆盖"选一个"的全部形态；**不发明第四种**。

⚠️ **score 的取值口径有个坑**：score 题的 scale.labels 是**给人看的档位文字**，而 target 的键是
**数字下标**（"0".."max"）。照 labels 去建输出词表会静默对不上。实测 6,752 道 score 题里，
**4,661 道**的 labels 是描述文字（如 "Cosmetic; no impact to functionality"），只有 2,091 道是 "0".."max"。

### 1.4 构成：33% 是合并目标，补充集把中文推到 40.8%

| 阶段 | 英文 | 中文 | 中文占比 | 说明 |
|---|---:|---:|---:|---|
| 合并（items.final） | 15,983 | 7,872 | **33.00%** | 中文按 33% 抽（先取每请求 1 套，再按 sha256(seed+group_id) 补第 2 套） |
| + 中文补充（只进 train） | — | +3,148 | — | 单标签转换，成色降级（见 §1.5） |
| **合计** | **15,983** | **11,020** | **40.8%** | 但**单一来源** Deepexi 只占 29.2%，未触 40% 上限 |

**为什么合并时取 33% 而不是上限 40%**：Deepexi 是唯一中文来源，中文占比就等于该来源占比。
取到 40% 会正好顶满契约"单一来源 ≤ 40%"、没有余量；而多取的是**同一批请求的变体**，边际信息量递减。
33% 落在 30–40% 区间内，又给第二个中文来源留出头寸。（详见 [merge-report.md](merge-report.md)。）

### 1.5 成色分层（做训练决策必读）

| 层级 | 是什么 | 条数 | 真值形态 | 进 benchmark？ |
|---|---|---:|---|---|
| **A. 原生四元组** | 来源自带 state/候选/答案，我们只搬运 | **23,855** | 来源的概率分布，或来源自己的硬标签 | **是（只有这一层）** |
| B. 单标签转换的补充 | 数据只有"这条属于 X 类"，把 X 当正确选项、再从**同一标签集**取其余选项凑成 choice | **3,148**（中文 noul 1,631 / score 1,517） | 硬标签 + documented 映射，origin=taxonomy | **否** |

**怎么用**：A 层可以直接进训练与 benchmark；B 层是**成色降级**的补充，**只进 train**，
不进 validation / test / benchmark，训练时也要与 A 层分开报告。**benchmark 只含 A 层**（实测 2,389 条全部 origin=source）。

### 1.6 真值形态：别把"伪概率"当真分布（会改变训练结果）

每条问题下 target 可能是三类之一，字段层面**长得一样**，必须先判形态再用：

| 形态 | 怎么识别 | 全语料 | train | test | validation | benchmark |
|---|---|---:|---:|---:|---:|---:|
| **真分布** | probs 有多个不同取值 | 7,520 | 4,527 | 1,536 | 706 | 751 |
| **伪 one-hot** | probs 恰好一个 1.0、其余 0.0（由硬标签造出来） | **14,119** | 8,397 | 2,883 | 1,425 | **1,414** |
| **均匀分布** | probs 各项相等（如 0.5/0.5）→ **无信息** | 1,730 | 1,038 | 340 | 179 | 173 |
| 只有 answer | 没有 probs 字段 | 11,565 | 8,737 | 1,845 | 922 | 61 |

（形态是**语料级**属性：v1/v2 只是把同一批 27,003 条重新分配，形态统计不变；上表的 benchmark 列已按 v2 的 1,600 条重算。）

- 伪 one-hot 与 [CONTRACT.md](CONTRACT.md) 的"不允许把单标签伪装成概率"是**已知冲突**：
  判别方法与建议的 provenance 字段见 CONTRACT §2.3；训练时若要按真分布做 KL / 校准目标，**请先按上表过滤**。
- 均匀分布 target 没有信息量（多出现在教师模型的低置信样本），用它做监督等于教模型"别确定"；
  报告指标时建议同时给"排除均匀目标"的子集分数。

### 1.7 一条数据里的语言分工

| 内容 | 来自哪 | 语言 |
|---|---|---|
| state（情境） | 来源原文 | 英文条目英文，中文条目中文 |
| questions 的 key / prompt | **候选集与答案来自来源**；题面措辞英文侧用来源原文，**中文侧由我们编写** | 随来源 / 中文侧中文 |
| options | 来源原文（中文侧候选顺序已被确定性打散） | 随来源 |
| targets | 来源自带答案；有分布存分布，只有硬标签就只写 answer（或单点分布） | 语言无关 |

## 2. 开源来源清单 + 真实例子

### 2.1 英文侧：6 个 HF 仓库 / 7 个抓取单元，15,983 条（100% 带真值）

| 来源 | HF 链接 | 许可 | 固定 revision | 一句话 | 条数 |
|---|---|---|---|---:|
| jev-distill-corpus-v3 | [SargeDev/jev-distill-corpus-v3](https://huggingface.co/datasets/SargeDev/jev-distill-corpus-v3) | apache-2.0 | fc99c6357a9f | 教师蒸馏的三原语语料，**带完整概率分布**，规模主力 | 7,756 |
| jev-decisions-v1 | [samatv256/jev-decisions-v1](https://huggingface.co/datasets/samatv256/jev-decisions-v1) | cc-by-4.0 | c12aadf1f01c | agent **工具选择**（通用精选配置），硬标签 | 3,802 |
| procedural-typed-decisions | [tasksource/procedural-typed-decisions](https://huggingface.co/datasets/tasksource/procedural-typed-decisions) | apache-2.0 | 609513a3fadd | **一个情境挂多个类型化问题**，带概率 | 1,500 |
| systemone-lite-general | [dwidlee/systemone-lite-general](https://huggingface.co/datasets/dwidlee/systemone-lite-general) | mit | c14eb7f7518f | 合成 gym（辩论裁决、工单紧急度），硬标签 | 1,479 |
| Open-Jev | [ZefanCai/Open-Jev](https://huggingface.co/datasets/ZefanCai/Open-Jev) | cc0-1.0 | c67699e13d0a | 同一请求下**多个正交问题**，规范最好、可逐行溯源 | 792 |
| system-one-270m-data | [kaivoss/system-one-270m-data](https://huggingface.co/datasets/kaivoss/system-one-270m-data) | apache-2.0 | f31d5a3f3da8 | 日志与告警分诊，带概率 | 447 |
| jev-decisions-v1（default 配置） | 同上 | cc-by-4.0 | c12aadf1f01c | 1200 万行里做的浅窗口抽样，仅作分布对照 | 207 |

逐来源的取材理由与陷阱见 [SOURCES.md](SOURCES.md)；机器可读清单见 [sources.json](sources.json)。

### 2.2 中文侧：1 个原生来源 + 4 个补充来源

| 来源 | 链接 | 许可 | 固定 revision | 说明 | 条数 |
|---|---|---|---|---:|
| Deepexi 函数调用（**A 层**） | [Deepexi/openai-formate-function-calling-small](https://huggingface.co/datasets/Deepexi/openai-formate-function-calling-small) | apache-2.0 | 6d1dc02a2549 | 中文用户请求 + 候选工具菜单 + 正确工具；从 5,454 个唯一请求按变体抽到 33% | 7,872 |
| BEncoderRT/User_Intent_Risk_Triage（**B 层**） | [BEncoderRT/User_Intent_Risk_Triage](https://huggingface.co/datasets/BEncoderRT/User_Intent_Risk_Triage) | 见 sources.zh.json | 见 sources.zh.json | 中文意图/风险分类 → 补充 noul / score，**只进 train** | 2,061 |
| textdetox/multilingual_toxicity_dataset（**B 层**） | [textdetox/multilingual_toxicity_dataset](https://huggingface.co/datasets/textdetox/multilingual_toxicity_dataset) | 同上 | 同上 | 同上 | 543 |
| chenhaodev/med-guard-safety-synth（**B 层**） | [chenhaodev/med-guard-safety-synth](https://huggingface.co/datasets/chenhaodev/med-guard-safety-synth) | 同上 | 同上 | 同上 | 472 |
| vanila434/multilingual-elder-safety-msgs（**B 层**） | [vanila434/multilingual-elder-safety-msgs](https://huggingface.co/datasets/vanila434/multilingual-elder-safety-msgs) | 同上 | 同上 | 同上 | 72 |

中文侧的调研与准入见 [zh-survey.md](zh-survey.md)、构建见 [zh-build-report.md](zh-build-report.md)、
清单（含逐条许可与 revision）见 [sources.zh.json](sources.zh.json)。

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

**例 2 · 英文 choice（硬标签 → 单点分布，属 §1.6 的"伪 one-hot"）：systemone-lite-general**

    state: "{\"ticket\": {\"subject\": \"Production outage: checkout broken\", \"tier\": \"enterprise\", ...}}"
    questions[0]: key="ticket.urgency"  kind=choice
      options: [{"key":"1_medium_same_day","label":"1: medium — same day"},
                {"key":"0_low_can_wait","label":"0: low — can wait"},
                {"key":"2_high_immediate","label":"2: high — immediate"}]
    targets["ticket.urgency"]: {"answer":"2_high_immediate",
                                "probs":{"1_medium_same_day":0.0,"0_low_can_wait":0.0,"2_high_immediate":1.0}}
    ← 来源只有硬标签，这个 probs 是单点分布、不是真概率；任何分布类损失都要先过滤（见 §1.6）

**例 3 · 英文 noul 与 score：保留来源自己的档位（jev-distill-corpus-v3）**

    noul:  state "The log shipper shows a 22% drop in request rate with no deploys [截断]"
           key "Is this scenario one where: this can wait until morning?"  kind=noul
           options [{"key":"false","label":"false"},{"key":"true","label":"true"}]     ← 原样，不改成 yes/no
           target  {"answer":"false","probs":{"false":0.87,"true":0.13}}

    score: state "A statistic in the draft attributes to a study that says the opposite [截断]"
           key "Rate claim reliability for this scenario on a 0-5 scale."  kind=score
           scale {"min":0,"max":5,"labels":["0","1","2","3","4","5"]}                  ← 六档原样，不压成 0-4
           target {"answer":"4","probs":{"0":0.01,"1":0.01,"2":0.05,"3":0.41,"4":0.51,"5":0.01}}

    对比 · score 的 labels 是描述文字时（Open-Jev 的 bug_severity，3 档）：
           scale {"min":0,"max":2,"labels":["Cosmetic; no impact to functionality",
                                            "Broken or degraded feature; workaround exists",
                                            "Blocking issue; no workaround exists"]}
           target {"answer":"0","probs":{"0":1.0,"1":0.0,"2":0.0}}                     ← 键是数字下标，不是 labels 文字

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
             random_line_bulk {"answer":"yes","probs":{"yes":0.666667,"no":0.333333}}      ← 真概率

**例 5 · 中文 choice：候选集与答案来自来源，题面由我们编写（Deepexi，A 层）**

    state: "20210101的短信发送状态如何？"
    group_id: "zhgrp-104f0514ee19"        ← 同一请求的多个变体共用一个 group_id（切分按组，不拆开）
    questions[0]: key="next_step_candidate"  kind=choice
      prompt: "以下候选中，哪一个是正确的下一步？"     ← 中文侧题面是我们写的；候选与答案来自来源
      options: [{"key":"ListMessages","label":"ListMessages：按指定过滤条件获取指定日期的短信发送状态。"},
                {"key":"UpdateDISyncTask","label":"UpdateDISyncTask：更新数据集成同步任务。"},
                {"key":"GenerateDISyncTaskConfigForCreating","label":"GenerateDISyncTaskConfigForCreating：异步生成同时任务的JSON。"}]
    targets["next_step_candidate"]: {"answer":"ListMessages"}    ← 来源只给了硬标签，就不编概率

**例 6 · 中文补充（B 层，只进 train）：单标签 + 同一标签集凑选项**

    state（中文分类数据的原文）→ 由 taxonomy 命题成 noul / score，从该数据集**自己的标签集**取选项；
    origin=taxonomy、tier=derived，**不进 validation / test / benchmark**（实测 benchmark 内 origin=taxonomy 为 0 条）。

## 3. 划分信息

四分区按**请求分组**切分，种子 **20261005**。

**v2（加盐重切，2026-10-05）**。三处刻意的偏离，别当 bug：

1. **train 高于 60%（66.6%）**：切分后按裁定只向 train 追加了 3,148 条中文降级补充；
2. **benchmark 只有 5.9%**：本轮**只允许英文进 benchmark**（中文侧见 §3.1），1,600 ≈ 英文侧 15,983 的 10%；
3. **benchmark 全英文**，所以它的 (domain, lang) 分层占比天然与公开三区不同。

| 分区 | 条目 | 占比 | 英文 | 中文 | 其中降级补充（B 层） |
|---|---:|---:|---:|---:|---:|
| train | 17,984 | 66.6% | 9,588 | 8,396 | 3,148 |
| test | 4,946 | 18.3% | 3,197 | 1,749 | 0 |
| validation | 2,473 | 9.2% | 1,598 | 875 | 0 |
| benchmark | 1,600 | 5.9% | 1,600 | 0 | 0 |
| **合计** | **27,003** | 100% | 15,983 | 11,020 | 3,148 |

**train 的 origin 构成（条目级，决定"哪些是真原生"）**：

| origin | 条目 | 占 train | 说明 |
|---|---:|---:|---|
| source（英文原生） | 9,588 | 53.3% | 6 个英文来源，原生四元组 |
| source（中文原生） | 5,248 | 29.2% | Deepexi 请求 + 候选菜单 + 正确工具 |
| taxonomy（**降级补充**） | 3,148 | 17.5% | 单标签转换，仅 train |
| 未标 | 0 | 0.0% | — |

**域分布（这一节必须看，否则会做出错误结论）**：

| domain | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| decision_mechanics | 12,203 | 4,068 | 2,034 | 1,160 |
| knowledge_reasoning | 2,633 | 878 | 439 | 440 |
| risk_harm | 2,605 | **0** | **0** | **0** |
| human_judgment | 543 | **0** | **0** | **0** |

> 🔴 **risk_harm 与 human_judgment 只存在于 train**（它们全部来自中文补充集 B 层）。
> 因此 **train 与 test / validation / benchmark 的域分布不可比**：
> 任何"某域在训练里如何、在测试里如何"的对比都会被这个结构差异污染。
> 需要域间对比时，请在 train 内部再切一个与评测区同构的子集（只用 A 层），或只比较两区共有的两个域。

**原语分布（条目级：一条条目至少含一个该原语）**：

| kind | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| choice | 11,187 | 3,763 | 1,868 | 997 |
| noul | 5,650 | 1,324 | 672 | 652 |
| score | 3,739 | 757 | 349 | 397 |

（同一条目可挂多个问题，所以一行内多列不互斥、也不等于条目数。）

**为什么必须整组切**：中文侧的多个变体来自**同一个请求**、state 逐字相同，只是候选顺序不同。
按行随机切会把同一请求的变体分到 train 和 test 两侧，**静默泄漏**。切分器的做法是并查集合并：
显式分组键（group_id / request_id）与**归一化 state** 各自连边，同一连通分量的条目整组进同一分区。

**泄漏检查（我在四个分区文件上复算，全部为 0）**：

| 组合 | id 重叠 | 组重叠 | 归一化 state 重叠 |
|---|---:|---:|---:|
| train ∩ test | 0 | 0 | 0 |
| train ∩ validation | 0 | 0 | 0 |
| train ∩ benchmark | 0 | 0 | 0 |
| test ∩ validation、test ∩ benchmark、validation ∩ benchmark | 0 | 0 | 0 |

复核范围：27,003 条 / 21,376 组（切分器口径）/ 23,980 个不同归一化 state（我按 state 归一化后复算）。
切分产物树哈希 **7635cfbbd01b1f73**…（v2 私盐版），种子 20261005；详见 [split-report.md](split-report.md) 与
[data/splits/split-manifest.json](data/splits/split-manifest.json)。

> **v1 四区已作废**：v1（benchmark 2,389 条、sha256 43937e09…）是公开种子**无盐**跑出来的，
> 用仓库里公开的脚本 + 语料 + 种子就能逐字节重建，已确认不可保密。**v1 与 v2 不可拼接使用。**

**复现（三个坑）**：

    # 1) 旗标是 --input（不是 --items）
    # 2) 默认 --out/--report 指向交付目录：不加参数直接跑会【覆盖 train（含追加的 3,148 条补充）】
    #    并覆盖 split-report.md，必须显式指到仓库外
    # 3) 【必须带 --salt-file，且盐文件必须在仓库外】：无盐直接退出 3（"交付件必须用仓外私盐"）
    uv run --no-project --offline python datasets/general/data/splits/split.py \
        --input datasets/general/data/items.final.jsonl \
        --out <仓库外目录> --report <仓库外目录>/split-report.md \
        --salt-file <仓库外盐文件> --seed 20261005

    # 只看流程：--dry-run（无盐可跑、不写盘）
    # 跑"公开可复现的演示"：--public-demo，且 --out 必须在仓库外；结果与交付件不同，不是交付件
    # 盐文件放在仓库内、或短于 16 字节 → 同样退出 3

实测：照抄旧命令里的 --items 报 unrecognized arguments（退出码 2）；不带 --salt-file 退出码 3。

### 3.1 内部 benchmark（v2，私盐版）

| | v1（作废） | **v2（现行）** |
|---|---|---|
| benchmark 条数 | 2,389（含中文 789） | **1,600（全英文）** |
| 语言 | en + zh | **仅 en** |
| 重建方式 | 公开脚本 + 公开种子即可 | 必须**仓外私盐**（盐的 sha256 前 16 位折进所有随机种子） |
| sha256（明文） | 43937e09a6fdde62… | f5ae670811c33200… |
| 状态 | **作废**，与 v2 不可拼接 | 现行交付件 |

- **不得进公开仓库**：benchmark 分区与 data/splits/benchmark-dataset/ 已在 .gitignore；
- **上传时设为 private**；不要放进公开分支、fork、PR、日志或截图；
- **其他人不要引用其内容**：看过逐例答案就不能再自称在它上面是盲测；
- **只含 A 层**（原生四元组；实测 1,600 条全部 origin=source，且全部英文）；
- **中文侧不进 benchmark（本轮裁定）**：中文答案曾以 (group_id → 正确工具) 索引的形式进过公开版本库，
  **换盐、换种子、重切都挡不住**——该映射对任何从同批请求生成的题都有效。
  恢复条件：接入一个**全新的中文来源**，或在确认无外部副本后由维护者**协调重写仓库历史**清除该索引。
- 保密现在是**机器可验证**的（test_split.py 的 SecrecyTest）：两个不同盐 → benchmark 不同；同盐两次 → 完全一致；
  非白名单语言不得进 benchmark；无盐 public-demo 结果与交付件不同；**被 git 跟踪的文件对 benchmark 记录零命中**；
  盐文件在仓库内 / 无盐且非 public-demo / public-demo 写到仓库内 → 均非零退出。

## 4. 文件在哪（对外只发三区 + 报告）

**对外发布（仓库内）**：只有三个公开分区 + 报告与清单。

| 文件 | 内容 | 对外 |
|---|---|---|
| data/splits/train.jsonl(.gz) | 17,984 条（含 3,148 条降级补充） | ✅ |
| data/splits/test.jsonl(.gz) | 4,946 条 | ✅ |
| data/splits/validation.jsonl(.gz) | 2,473 条 | ✅ |
| data/splits/split-manifest.json、split-report.md | 哈希与聚合报告（不含样本） | ✅ |
| data/splits/benchmark.jsonl(.gz)、benchmark-dataset/ | 内部 benchmark 1,600 条 | ❌ private 托管 |
| data/items.final.jsonl、items.native.jsonl、items.native.slim.jsonl、items.bilingual.jsonl、items.jsonl | 完整语料（明文，本机保留；items.final 是切分输入 23,855 条） | ❌ **已移出版本控制** |
| 上述五件的 .gz、data/zh/zh-group-index.jsonl、data/zh/zh-items.sample.jsonl | 含 benchmark 正文或中文答案索引 | ❌ **已移出版本控制**，仓外留存 D:\pol2-raw\general-private\ |

- **七件语料已移出版本控制**（原因：含 benchmark 正文或中文答案索引），清单见 [split-report.md](split-report.md) §10.4；
- data/zh-supplement/items.jsonl(.gz)（3,148 条补充）仍在仓库内。

检查（注意：6 域配额是按**已退役**的混合语料定的，对当前语料会报 NG）：

    uv run --no-project --offline python tools/check.py
    # 实测：items.final 在 human_judgment / social_moral / risk_harm 三域为 0 → 3 项不通过；
    # items.native 另有单一来源 jev-distill 占 48.5% > 40% → 4 项不通过。配额口径需随语料重定。
    uv run --no-project --offline python datasets/general/coverage.py --items datasets/general/data/items.final.jsonl
