# Jev 分层校验报告（第一阶段）

> 生成时间：2026-10-15T05:52:30+00:00 ｜ 生成脚本：jev-v0.1（[jev_fill.py](jev_fill.py)）
> 语料：[items.final.jsonl](data/items.final.jsonl) sha256 前缀 21f11fe3dc39edd9（只读，未改动）
> 凭据：[datasets/jev.yaml](../jev.yaml)（model=typesafe/jev-router，endpoint 主机 openrouter.ai）；密钥只记录指纹。

## 0. 结论摘要

| 指标 | 值 |
|---|---|
| 计划抽样条数（按 lang x domain x kind 分层） | 300 |
| 本次报告覆盖的请求数 | 300 |
| 成功取得响应 | 218 |
| 未跑完（计划 - 成功；预算上限 + 余额耗尽） | 82 |
| HTTP 200 有效响应 | 218/300 |
| 可解析率（占有效响应） | 205/218 = 94.0% [95%CI 90.1%–96.5%] |
| 与语料真值一致率（占可解析） | 151/205 = 73.7% [95%CI 67.2%–79.2%] |
| 随机基线期望一致率（同一批可解析题） | 29.2% |
| 一致率 / 基线 | 2.52x |
| 成本合计（成功响应，脚本口径） | $0.12836 |
| 其中 API 实测 / 兜底估计 | $0.12836 / $0.00000 |
| 账户侧权威口径（GET /key 的 usage） | $0.19585 |
| 单次成功调用成本（账户侧口径） | $0.000898 |
| 上游模型数（异构教师） | 5 |

- **一致率是否高于随机**：是，明显高于随机基线（一致率 73.7%，基线 29.2%）。
- **可解析率**：205/218 = 94.0% [95%CI 90.1%–96.5%]；不可解析的原因分布见第 4 节。
- **最弱的三层**（3.8 节逐层给了解读与保留）：`en|decision_mechanics|choice` 显著高于随机、`en|knowledge_reasoning|noul` 与随机不可区分、`uniform` 与随机不可区分；后两层经 Wilson CI 判定**与随机不可区分**，因此它们既不支持“我们错”也不支持“Jev 错”。
- **诚实说明**：本阶段的“一致”只是 **Jev 的答案 == 语料已有的 answer**。语料里大量 target 的 answer 本身来自教师模型或伪 one-hot（见 3.5 按 shape 分列），因此**一致率低不等于语料错**，一致率高也不等于语料对；能下判断的是“与随机基线的差距”“真实分布子集上的一致率”和“同题重复的自洽率”。

### 0.1 为什么停在 218/300：先是撞预算上限，后是 OpenRouter 余额不足（HTTP 402）

**第一轮（上限 $0.05）**：派发前按「命令行给的单次估计」（$0.0001/次）预留预算，但 `typesafe/jev-router` 每次路由到不同上游模型，单次成本实测跨 **3 个数量级**（本阶段整体：中位数 $0.000071、均值 $0.000589、最高 $0.007370）。估计值比实际低约 4–5 倍，跑到 $0.05 上限时**该轮**已花掉 $0.0584，**超出上限 16.8%**；该轮对应 journal 的**前 163 行**（journal 是只追加的，界址可复算）。已按“超限即停”停止，未继续追加调用。

预算预留已改成**自适应**（预留额 = max(命令行估计, 已观测均值 x 2)）；Lead 随后把上限放到 $0.12，于是补跑了第二轮：又拿到若干响应后，**80 条请求返回 HTTP 402 “Insufficient credits”**，账户余额耗尽，整批停止（402 不计费，已完成的调用全部保留在 journal）。脚本已把 402 识别为**致命错误**：一旦出现就停止整批派发，避免第二阶段白刷 8,000 次。

**余额证据（2026-10-15T05:44Z 实测，可直接复算）**：

```sh
curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $JEV_API_KEY"
# -> {"data":{"total_credits":5,"total_usage":5.210495714}}   # 账户额度已用尽
curl -s https://openrouter.ai/api/v1/key     -H "Authorization: Bearer $JEV_API_KEY"
# -> limit_usd=1, usage=0.195851448, limit_remaining=0.804148552   # 这把 key 另有 $1 硬上限
```

**这两条对第二阶段都是硬约束**：账户要有余额（按实测均值，8,417 次约 $4.96）；同时这把 key 自身的 $1 上限只剩 $0.80，**即使账户充值，跑满 8,417 条也会先撞 key 上限**——需要换一把额度更高的 key，或先把 key limit 调大。

未跑完的 82 条本身只需约 $0.006（中位数口径）到 $0.048（均值口径）。

因余额耗尽，原计划的**同题重复调用（自洽率）**与 **distribution 变体配对探针**（100 次）本轮**未能执行**（见第 8 节 / 附录 A），它们同样卡在余额上。

## 1. 方法与可复算命令

抽样单元是 **target**（`<item id>.<question key>`），不是 item。
分层键 = `lang|domain|kind`，按各层总体规模**比例分配**（最大余数法），层内用种子洗牌后取值。
提示词模板（answer 变体，Lead 实测可解析）：

```text
{question.prompt}

{state}

Options: {opt1} | {opt2} | ...
Reply with exactly one option from the list, nothing else.
```

- 选项文本 = 该题 `options[].label`（label 以 key 开头时直接用 label，例如中文侧的 `ListMessages：按…`）；score 题用数字档位，label 是文字时写成 `0 (描述)`。
- 请求参数：`temperature=0`、`max_tokens>=2000`、必须带 `user-agent`；`usage.include=true` 以取回真实成本。
- 重试：HTTP 408/409/425/429/5xx 与超时/网络错误指数退避，最多 4 次；每次尝试单独落一行 journal。
- 续跑：journal 里已有 `status=ok` 的 qid 直接跳过，重跑不重复花钱。

```sh
# 1) 抽样（离线，不花钱）
uv run --no-project --offline python datasets/general/jev_fill.py sample --n 300 --seed 20261015

# 2) 先小样本试跑，确认可解析率与单次成本
uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation --limit 5

# 3) 全量跑（预算硬上限 $0.05；跑满或超限即停，可反复重跑续跑）
uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation --budget 0.05 --workers 4

# 4) 生成本报告
uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation
```

## 2. 抽样设计与实际完成

| 分层 lang|domain|kind | 总体 target 数 | 计划抽样 | 实际发出 / 计划 | 可解析 |
|---|---|---|---|---|
| en|decision_mechanics|choice | 9861 | 93 | 92 / 93 | 49 |
| en|decision_mechanics|noul | 5300 | 50 | 49 / 50 | 22 |
| en|decision_mechanics|score | 4288 | 40 | 40 / 40 | 21 |
| en|knowledge_reasoning|choice | 911 | 9 | 9 / 9 | 7 |
| en|knowledge_reasoning|noul | 2607 | 25 | 25 / 25 | 24 |
| en|knowledge_reasoning|score | 947 | 9 | 9 / 9 | 8 |
| zh|decision_mechanics|choice | 7872 | 74 | 74 / 74 | 74 |
| 合计 | 31786 | 300 | 298 / 300 | 205 |

完成情况：计划抽 300 条，实际发出 298 条（有效响应 218 条），可解析 205 条。

## 3. 一致率

### 3.1 总体

| 指标 | 值 |
|---|---|
| 可解析 | 205/218 = 94.0% [95%CI 90.1%–96.5%] |
| 与真值一致 | 151/205 = 73.7% [95%CI 67.2%–79.2%] |
| 随机基线 | 29.2% |

### 3.2 按 lang

| 分组 | 抽样 | 有效响应 | 可解析率 | 一致率 | 随机基线 |
|---|---|---|---|---|---|
| en | 226 | 144 | 131/144 = 91.0% [95%CI 85.2%–94.6%] | 77/131 = 58.8% [95%CI 50.2%–66.8%] | 28.4% |
| zh | 74 | 74 | 74/74 = 100.0% [95%CI 95.1%–100.0%] | 74/74 = 100.0% [95%CI 95.1%–100.0%] | 30.7% |

### 3.3 按 domain

| 分组 | 抽样 | 有效响应 | 可解析率 | 一致率 | 随机基线 |
|---|---|---|---|---|---|
| decision_mechanics | 257 | 175 | 166/175 = 94.9% [95%CI 90.5%–97.3%] | 128/166 = 77.1% [95%CI 70.1%–82.8%] | 27.0% |
| knowledge_reasoning | 43 | 43 | 39/43 = 90.7% [95%CI 78.4%–96.3%] | 23/39 = 59.0% [95%CI 43.4%–72.9%] | 38.7% |

### 3.4 按 kind

| 分组 | 抽样 | 有效响应 | 可解析率 | 一致率 | 随机基线 |
|---|---|---|---|---|---|
| choice | 176 | 139 | 130/139 = 93.5% [95%CI 88.2%–96.6%] | 99/130 = 76.2% [95%CI 68.1%–82.7%] | 23.0% |
| noul | 75 | 47 | 46/47 = 97.9% [95%CI 88.9%–99.6%] | 35/46 = 76.1% [95%CI 62.1%–86.1%] | 50.0% |
| score | 49 | 32 | 29/32 = 90.6% [95%CI 75.8%–96.8%] | 17/29 = 58.6% [95%CI 40.7%–74.5%] | 24.4% |

### 3.5 按 target 形态（probs 形态）

| 分组 | 抽样 | 有效响应 | 可解析率 | 一致率 | 随机基线 |
|---|---|---|---|---|---|
| answer_only | 81 | 74 | 74/74 = 100.0% [95%CI 95.1%–100.0%] | 74/74 = 100.0% [95%CI 95.1%–100.0%] | 30.7% |
| one_hot | 130 | 81 | 73/81 = 90.1% [95%CI 81.7%–94.9%] | 42/73 = 57.5% [95%CI 46.1%–68.2%] | 22.3% |
| real | 72 | 47 | 42/47 = 89.4% [95%CI 77.4%–95.4%] | 29/42 = 69.0% [95%CI 54.0%–80.9%] | 30.8% |
| uniform | 17 | 16 | 16/16 = 100.0% [95%CI 80.6%–100.0%] | 6/16 = 37.5% [95%CI 18.5%–61.4%] | 50.0% |

### 3.6 分层交叉表（lang|domain|kind）

| 分层 | 抽样 | 有效响应 | 可解析 | 一致 | 一致率 | 随机基线 |
|---|---|---|---|---|---|---|
| en|decision_mechanics|choice | 93 | 56 | 49 | 18 | 36.7% | 10.9% |
| en|decision_mechanics|noul | 50 | 22 | 22 | 22 | 100.0% | 50.0% |
| en|decision_mechanics|score | 40 | 23 | 21 | 14 | 66.7% | 27.3% |
| en|knowledge_reasoning|choice | 9 | 9 | 7 | 7 | 100.0% | 25.0% |
| en|knowledge_reasoning|noul | 25 | 25 | 24 | 13 | 54.2% | 50.0% |
| en|knowledge_reasoning|score | 9 | 9 | 8 | 3 | 37.5% | 16.7% |
| zh|decision_mechanics|choice | 74 | 74 | 74 | 74 | 100.0% | 30.7% |

### 3.7 answer-only 子集 vs 已有 probs 子集

| 子集 | 抽样 | 有效响应 | 可解析 | 一致 | 一致率 | 随机基线 |
|---|---|---|---|---|---|---|
| answer_only（第二阶段目标人群） | 81 | 74 | 74 | 74 | 100.0% | 30.7% |
| 已有 probs | 219 | 144 | 131 | 77 | 58.8% | 28.4% |

按 target 形态理解：`real` = 来源真的给了分布（可当概率用）；`one_hot` = 硬标签造的单点分布；`uniform` = 无信息均匀分布；`answer_only` = 只有硬标签。
若分歧集中在 one_hot / uniform / answer_only，说明不一致主要发生在**弱监督标签**上，而不是来源的真实分布上。

### 3.8 三个最弱分层：解读与保留

判定规则（**代码算，不靠目测**）：把该层一致率的 Wilson 95% CI 与随机基线比——CI 完全高于基线 = 显著高于随机；CI 覆盖基线 = 与随机不可区分；CI 完全低于基线 = 显著低于随机。上一节 3.6/3.5 的表里已经能看出这三层最弱，这里单独说清楚**证据能支持到哪一步、不能支持什么**。

| 分层 | 抽样 | 可解析 | 一致率 [95%CI] | 随机基线 | 与随机比 |
|---|---|---|---|---|---|
| en|decision_mechanics|choice | 93 | 49 | 36.7% [24.7%–50.7%] | 10.9% | 显著高于随机 |
| en|knowledge_reasoning|noul | 25 | 24 | 54.2% [35.1%–72.1%] | 50.0% | 与随机不可区分 |
| uniform（按 target 形态） | 17 | 16 | 37.5% [18.5%–61.4%] | 50.0% | 与随机不可区分 |

**（a）en|decision_mechanics|choice** = 18/49 = 36.7%，随机基线 10.9%（CI 24.7%–50.7%）——判定：**显著高于随机**。

这一层是 13–57 个候选的“下一步该选哪个”多选，语料答案来自**硬标签**（形态 `one_hot`，没有真分布），来源 jev-decisions-general-50k / Open-Jev。**证据能支持**：Jev 在这层明显高于随机（差 3 倍以上），说明它在读 state 而不是乱选；但它是全表最低的 choice 层，说明这层任务本身歧义大（候选多、场景意图不唯一）。**证据不能支持**：不能推出“我们 63% 的标签是错的”，也不能推出“Jev 63% 是错的”——这层没有可对照的真分布，两边都是教师在猜。第 6 节的分歧样例里两边答案往往都讲得通：例如“严重喘息”的场景，我们记 `get_participant_status`、Jev 答 `report_adverse_event`；“取消洗车预约”我们记 `get_appointment_details`、Jev 答 `authenticate_user`（先认证 vs 直接查详情，取决于该业务的流程约定，题面没给）。**保留**：这一层只能当硬标签用，**不能当分布**；训练时应标为高分歧子集，要定真值只能靠外部判别（人工复核或场景规则），现有证据不足以判谁对。

**（b）en|knowledge_reasoning|noul** = 13/24 = 54.2%，随机基线 50.0%（CI 35.1%–72.1%）——判定：**与随机不可区分**。

二值判断题，**随机基线就是 50%**。**证据能支持**：这层的数字几乎不含信息，既不能说“我们和 Jev 判据一致”，也不能说“不一致”。题面是场景专属谓词（jev-distill-v3 的 noul，如“这段 memory 对回答该 query 是否相关”），来源本身是教师模型产出的硬标签，没有第二意见可对照。**证据不能支持**：不能说“我们一半错”——n 太小，CI 同时装得下“完全随机”和“轻微一致”。要判定必须专门加样本（例如 200 条）或换人工复核。**保留**：先当噪声区，不用于任何强度结论。

**（c）uniform（均匀分布 target）** = 6/16 = 37.5%，随机基线 50.0%（CI 18.5%–61.4%）——判定：**与随机不可区分**。

契约 2.3 已经写明：均匀分布 target **本身无信息**（多来自教师低置信样本），本不该进监督。**证据能支持**：这层的 37.5% 不构成“Jev 反着答”的证据——n=16，CI 覆盖 50%，与随机不可区分。**证据不能支持**：不能据此说 Jev 在无信息题上系统性反向。**保留**：按契约建议，报分与训练都应**排除 uniform target** 后再看；本表保留它只作为分布事实。

## 4. 无法解析与未响应的原因分类

### 4.1 有响应但无法解析：13/218 = 6.0%

| 原因码 | 含义 | 条数 |
|---|---|---|
| length | 被 max_tokens 截断（finish_reason=length） | 13 |

`length` = 模型把 max_tokens=2000 全用在思维链上，正文为空或被截断（与 Lead 实测同一现象：13 条，占有效响应 6.0%；而且这几次是最贵的一档，因为 completion 被吃满）。第二阶段建议开 `--retry-truncated`（对 length 的条目用 2 倍预算重试一次），或把 max_tokens 提到 4000。`empty_content` = 返回空；`not_in_options` = 输出无法落回任何选项；`ambiguous_match` = 同时命中多个选项。

### 4.2 未取得 HTTP 200 的请求：82/300

| 原因码 | 含义 | 条数 |
|---|---|---|
| insufficient_credits | HTTP 402：账户/密钥余额不足（致命，立即停止整批） | 80 |
| network_error | 网络/其他错误 | 2 |

## 5. 成本

| 项 | 值 |
|---|---|
| 成功响应（HTTP 200） | 218 |
| HTTP 非 200 响应（402 等，不计费） | 82 |
| 未收到响应（网络/超时） | 3 |
| 因预算上限未发出（跳过） | 7 |
| prompt tokens | 34462 |
| completion tokens | 78113 |
| 成本合计（成功响应） | $0.12836 |
| 其中 API 回传 cost 的实测部分 | $0.12836 |
| 其中 API 未回传 cost、按兜底估计的部分 | $0.00000 |
| 单次成功调用成本（实测+估计） | $0.000589 |
| 单次成本中位数 / 最高 | $0.000071 / $0.007370 |
| 成功响应中 cost 来自 API 实测的条数 | 218 |

**口径说明（重要）**：脚本逐条累加的是 OpenRouter 响应里的 `usage.cost`，本阶段合计 $0.12836；而账户侧 `GET /key` 的 `usage` 是 $0.19585，**高 $0.06750（+53%）**。差额来源未查明（可能是 router 加价/计费口径不同，也可能这把 key 在别处也被用过），因此本报告的分列成本只作相对比较，**做预算一律用账户侧口径**：单次 $0.000898。若按脚本口径 ($0.000589/次) 规划，会低估一半。

**成本结论（唯一口径）**：以**账户侧**为准，单次 **$0.000898**；据此跑满第二阶段 8,417 条 ≈ **$7.56**。脚本逐条累加的口径（$0.000589/次 → $4.96）会低估约一半，不要用它做预算。

预算：本阶段硬上限 **$0.05**（`--budget`），超限即停并保留已完成的调用。

### 上游模型分布（异构教师）

| 上游模型 | 调用数 | 占比 | 成本 | 单次均价 | completion tokens |
|---|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | 84 | 28.0% | $0.06285 | $0.000748 | 54760 |
| meta/muse-spark-1.2 | 6 | 2.0% | $0.03218 | $0.005363 | 7393 |
| google/gemini-3.8-flash | 10 | 3.3% | $0.02193 | $0.002193 | 5614 |
| openai/gpt-6-luna | 117 | 39.0% | $0.00588 | $0.000050 | 8346 |
| stepfun/step-5-preview | 1 | 0.3% | $0.00551 | $0.005510 | 2000 |

`typesafe/jev-router` 每次可能路由到不同上游模型，因此 Jev 产出的是**异构教师**的判断，不是单一模型的稳定输出。

## 6. 分歧样例（逐条）

共 54 条分歧（占可解析 26.3%）。state 摘要为单行截断，完整 state 见语料。

| qid | lang | domain | kind | shape | 选项数 | 语料 answer | Jev 答案 | 上游模型 | state 摘要 |
|---|---|---|---|---|---|---|---|---|---|
| `db-jev-decisions-general-50k-0d21843b.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 20 | get_participant_status | report_adverse_event | deepseek/deepseek-v4.1-flash | Hi, I’m calling as a participant in the Phase II respiratory trial (ID: PT-44556). I’m experiencing severe wheezing that started around 8:00 PM on Aug… |
| `db-jev-decisions-general-50k-14e8153c.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 20 | get_appointment_details | authenticate_user | openai/gpt-6-luna | Hello, I need to cancel my car wash appointment. My license plate is ABC123, and the appointment ID is SH789. It’s scheduled for a Premium Shine at 9 … |
| `db-jev-decisions-general-50k-19962720.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 13 | get_package_details | transfer_to_human_coordi | deepseek/deepseek-v4.1-flash | Hello, my name is [Customer Name], and I'm reaching out to request a transfer of my career coaching session credits to my spouse's account. My User ID… |
| `db-jev-decisions-general-50k-19eec6a0.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 18 | get_booking_details | schedule_vendor_call | openai/gpt-6-luna | Hi, my name is [Groom's Name], and I’m calling about my wedding photography booking. My booking ID is BKG-556677, and my email is <REDACTED_EMAIL>. I’… |
| `db-jev-decisions-general-50k-1cf413e3.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 14 | transfer_to_human_agent | authenticate_user | deepseek/deepseek-v4.1-flash | Hello, I'm calling regarding a temperature deviation for a vaccine shipment with tracking number 9400100000000000000030. Our records show the temperat… |
| `db-jev-decisions-general-50k-202fa8a7.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | transfer_to_human_agent | authenticate_applicant | openai/gpt-6-luna | Hello, my name is [Student Name], and I'm calling to update my graduation timeline. My application ID is GRAD-DATE-22, and I was born on March 30, 200… |
| `db-jev-decisions-general-50k-20929d5a.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 15 | get_wedding_profile | authenticate_client | deepseek/deepseek-v4.1-flash | Hello, I’m calling about unexpected overtime charges from my photographer for the wedding on October 25, 2025 at the Vineyard venue. My client ID is B… |
| `db-jev-decisions-general-50k-2779db83.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 19 | transfer_to_human_agent | generate_troubleshooting | openai/gpt-6-luna | Hi, I'm having trouble with the practice videos buffering on my iPad Pro even though my internet speed is 150 Mbps. My student ID is MM-7799. Can you … |
| `db-jev-decisions-general-50k-2b1c8db7.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 14 | get_customer_profile | modify_order | openai/gpt-6-luna | Hello, I'm reaching out regarding our recent order #COMFC4433 under government contract #GOVX2287, which has already been validated for FOB terms. We … |
| `db-jev-decisions-general-50k-36ce80ce.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | get_user_profile | get_order_details | openai/gpt-6-luna | Hello, I recently purchased a video game through your store, but I think there might be an issue with the regional version. I bought the EU edition wh… |
| `db-jev-decisions-general-50k-485504f7.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 21 | get_user_profile | get_pricing_tiers | openai/gpt-6-luna | Hello, I'm calling about a parking charge I received. I parked at 6:50 AM and left at 7:05 AM, but I was charged $5 for the hour starting at 6:50. Why… |
| `db-jev-decisions-general-50k-4f001e84.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | access_recording | get_recording_processing | deepseek/deepseek-v4.1-flash | Hello, I'm Dr. Emily Carter, a VIP healthcare professional with access to your platform. I'm calling regarding a session recording issue for Event ID … |
| `db-jev-decisions-general-50k-557e600e.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | get_child_profile | add_pickup_contact | openai/gpt-6-luna | Hello, I need to urgently add a new contact for my child INF-44. There’s been a family emergency, and I can only provide 24 hours’ notice instead of t… |
| `db-jev-decisions-general-50k-61641ecb.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 18 | transfer_to_specialist | resolve_invoice | openai/gpt-6-luna | Hello, I'm reaching out to request a consolidated billing statement for multiple invoices under my client's account. Could you please generate a combi… |
| `db-jev-decisions-general-50k-6adf6e13.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | transfer_to_human_agent | verify_compliance | deepseek/deepseek-v4.1-flash | Hello, I'm calling from the National Park Service regarding Project ID MON-2025-444 (Organization ID: NPS-2025). I need to verify compliance with site… |
| `db-jev-decisions-general-50k-6b36a4f7.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 19 | get_customer_profile | request_service_change | openai/gpt-6-luna | Hello, I'm calling to update my utility service for account #990044. My current ZIP is 90039, and I'm moving to unit 5B in the same building. Can you … |
| `db-jev-decisions-general-50k-6d40cc19.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 16 | record_verbal_confirmati | adjust_billing | deepseek/deepseek-v4.1-flash | Hi, I'm calling regarding an unusually high energy bill. My account is linked to meter ID SMART-1010, and my current bill is 210% higher than last mon… |
| `db-jev-decisions-general-50k-8acad603.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 16 | transfer_to_human_agent | notify_coast_guard | openai/gpt-6-luna | I'm calling to report an illegal oil discharge I observed from a commercial vessel yesterday near the coastal conservation area. My name is associated… |
| `db-jev-decisions-general-50k-977f6115.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | get_application_status | authenticate_applicant | openai/gpt-6-luna | Hi, I'm a domestic undergraduate applicant with Application ID U246823 and a birthdate of July 8, 2005. I recently changed my phone number and need to… |
| `db-jev-decisions-general-50k-9b9253fa.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 22 | rotate_access_key | check_resource_state | openai/gpt-6-luna | Hello, I'm a security specialist with a media company, and I need to confirm compliance with our mandatory 90-day access key rotation policy. Could yo… |
| `db-jev-decisions-general-50k-9e127662.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 16 | create_dock_reservation | verify_identity | openai/gpt-6-luna | Hello, I'm a member with Member ID CY-8901 and vessel registration ending in 0123. I'm calling about the slip size requirement for my 48-foot boat. I … |
| `db-jev-decisions-general-50k-a164eb41.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 20 | get_program_schedule | get_tuition_details | deepseek/deepseek-v4.1-flash | Hi, I'm calling about my child C373. We need to switch from full-time (5 days/week) to part-time (3 days/week) starting November 1st due to scheduling… |
| `db-jev-decisions-general-50k-aa5ba78f.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 22 | transfer_to_care_coordin | get_program_details | openai/gpt-6-luna | Hi, I’m calling about the childcare enrollment platform. As a parent, I’m concerned about ensuring all children feel included in playgroup activities,… |
| `db-jev-decisions-general-50k-c05235ad.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 13 | transfer_to_human_agent | create_service_ticket | deepseek/deepseek-v4.1-flash | Hello, I’m calling about significant water damage at my home located at 404 Water St. The drywall in my living room collapsed after a 2-hour leak, and… |
| `db-jev-decisions-general-50k-daf2c3ea.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 13 | get_item_availability | get_membership_benefits | openai/gpt-6-luna | Hello, I’m calling about a 7-day rental for SKU SUT-6666. As a Bronze member, I’d like to calculate the total cost including the damage waiver. Could … |
| `db-jev-decisions-general-50k-e0100603.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 15 | get_regional_pest_alerts | transfer_to_agronomist | deepseek/deepseek-v4.1-flash | Hello, I'm a citrus grower in the Florida lowlands with Farmer ID F1013. I need to request an experimental fungicide that isn't listed in your product… |
| `db-jev-decisions-general-50k-ebf40831.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 14 | issue_compensation | report_incident | openai/gpt-6-luna | Hello, I’m calling regarding a temperature issue in our climate-controlled storage unit CL-889 (reservation R54321). On July 15th, the temperature in … |
| `db-jev-decisions-general-50k-feaf334e.Given the current state and available options, which…` | en | decision_mechanics | choice | one_hot | 17 | get_reservation_details | transfer_to_human_agent | openai/gpt-6-luna | Hello, my name is Stewart and I have a booking reference OV789012 for a cruise departing on June 10, 2024. I'm reaching out to inquire if there are pa… |
| `db-jev-decisions-strata-40e32041.tool_choice` | en | decision_mechanics | choice | one_hot | 11 | transfer_to_human_agent | manage_gate_appointment | deepseek/deepseek-v4.1-flash | Hello, I need to verify the arrival timestamp for a truck with plate AUDIT-EXP-25 under appointment ID EXP-20251014-0730. Could you please confirm if … |
| `db-jev-distill-v3-0451ff9e.Is this memory relevant for answering the query? Query: Immunol…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | deepseek/deepseek-v4.1-flash | Although Helicobacter pylori eradication is effective in treating low-grade gastric mucosa-associated lymphoid tissue (MALT) lymphoma, the condition i… |
| `db-jev-distill-v3-0a6d8e14.Is this memory relevant for answering the query? Query: What ar…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | C. Halifax Town 4-0 2-0 2-1 0-0 1-1 2-1 2-0 1-0 3-3 4-0 1-1 4-0 1-1 5-1 2-0 2-1 2-2 5-1 1-0 2-0 3-0 3-4 3-2 Forest Green Rovers 3-1 3-1 1-2 0-2 3-2 3-… |
| `db-jev-distill-v3-0b6d019a.Is this memory relevant for answering the query? Query: Chorley…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | deepseek/deepseek-v4.1-flash | Malpas, Cheshire Malpas is a large village that used to be a market town. It is also a civil parish in the unitary authority of Cheshire West and Ches… |
| `db-jev-distill-v3-13c98ace.Is this memory relevant for answering the query? Query: What wa…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | )Chumacero 62' Report (FIFA)Report (CONMEBOL) Rodríguez 10'Bacca 41'Cardona 90+2' 24 March 2016 (2016-03-24)16:00 UTC 5 Ecuador 2-2 Paraguay Estadio O… |
| `db-jev-distill-v3-4e745037.Is this memory relevant for answering the query? Query: Which y…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | The regatta was organized by Sailing Academy of St. Petersburg Yacht Club. According to the idea of the organizers, this winter event will be held on … |
| `db-jev-distill-v3-4e7e5a4a.Rate arrival risk for this scenario on a 0-5 scale.` | en | decision_mechanics | score | real | 6 | 4 | 5 | deepseek/deepseek-v4.1-flash | An autonomous vehicle passes an active school zone at dismissal; additionally requires an unpaved segment for 8km. Context: in low-visibility conditio… |
| `db-jev-distill-v3-50e8812d.Rate reusability for this scenario on a 0-5 scale.` | en | knowledge_reasoning | score | real | 6 | 1 | 5 | deepseek/deepseek-v4.1-flash | A collaboration archive has versioned metadata and checksums; additionally is stored with a 3-2-1 backup strategy. Context: before the personnel depar… |
| `db-jev-distill-v3-5984f9a2.Supplier response for this scenario.` | en | decision_mechanics | choice | real | 4 | issue_warning | maintain | deepseek/deepseek-v4.1-flash | A regional warehouse shows a count variance of 2.3%; additionally flags 340 units damaged in transit. Context: SKU AX-330, under reduced staffing. Rep… |
| `db-jev-distill-v3-631fa1aa.Rate stockout risk for this scenario on a 0-5 scale.` | en | decision_mechanics | score | real | 6 | 3 | 4 | deepseek/deepseek-v4.1-flash | A distribution center detects expiration risk on 1,200 units; additionally shows a count variance of 2.3%. Context: a bonded SKU, following a recent a… |
| `db-jev-distill-v3-6d743ea0.Is this scenario one where: the ranking is justified?` | en | knowledge_reasoning | noul | real | 2 | true | false | deepseek/deepseek-v4.1-flash | A course suggestion was returned by this user 2 months ago; additionally was explicitly filtered out by preference settings. Context: in the seasonal … |
| `db-jev-distill-v3-6ff4c5f9.Is this memory relevant for answering the query? Query: How man…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | F.C. Fylde 42 22 9 11 76 53 +23 75 4 Harrogate Town 42 21 9 12 73 46 +27 72 5 Boston United 42 22 5 15 73 60 +13 71 6 Nuneaton Town 42 20 13 9 71 46 +… |
| `db-jev-distill-v3-70c032e6.Rate fidelity risk for this scenario on a 0-5 scale.` | en | knowledge_reasoning | score | real | 6 | 3 | 5 | meta/muse-spark-1.2 | A 40-page incident report is already a summary of a summary; additionally has 2 material contradictions. Context: for the 1-page brief, during an exte… |
| `db-jev-distill-v3-7c84a411.Is this memory relevant for answering the query? Query: What ty…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | Cheese - Lotsa Pasta , Louisville's Gourmet Grocery Lotsa Pasta,Louisville,pasta,fresh pasta,international grocery store,imported food,homemade food .… |
| `db-jev-distill-v3-7ce2966f.Rate protocol severity for this scenario on a 0-5 scale.` | en | knowledge_reasoning | score | real | 6 | 4 | 3 | google/gemini-3.8-flash | An autoclave cycle was performed outside the certified cabinet; additionally deviated from the approved protocol with supervisor sign-off. Context: du… |
| `db-jev-distill-v3-82271c45.Rate regression risk for this scenario on a 0-5 scale.` | en | decision_mechanics | score | real | 6 | 3 | 4 | deepseek/deepseek-v4.1-flash | The release candidate shows a 9% regression in the p95 benchmark; additionally was rebased after a security patch. Context: in the payments repo, foll… |
| `db-jev-distill-v3-844daf61.Rate business value for this scenario on a 0-5 scale.` | en | knowledge_reasoning | score | real | 6 | 3 | 1 | meta/muse-spark-1.2 | A merchandising slot was explicitly filtered out by preference settings; additionally is the only available option. Context: for this user profile, sh… |
| `db-jev-distill-v3-87f125da.Rate user-visible impact for this scenario on a 0-5 scale.` | en | decision_mechanics | score | real | 6 | 3 | 0 | deepseek/deepseek-v4.1-flash | Service catalog-sync shows clock skew of 800ms across replicas; additionally reports cardinality explosion in the metrics store. Context: over the las… |
| `db-jev-distill-v3-98bf7123.Critical path for this scenario.` | en | decision_mechanics | choice | real | 4 | vendor | compliance | deepseek/deepseek-v4.1-flash | The renewal deadline needs a document that takes 15 days to obtain; additionally depends on a vendor response with a 5-day SLA. Context: under the con… |
| `db-jev-distill-v3-bf2923a0.Rate user-visible impact for this scenario on a 0-5 scale.` | en | decision_mechanics | score | real | 6 | 4 | 0 | deepseek/deepseek-v4.1-flash | The log shipper reports empty scrape targets after the network change; additionally matches last Tuesday's incident signature. Context: during the bat… |
| `db-jev-distill-v3-d9aeb58d.Is this memory relevant for answering the query? Query: Can pat…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | deepseek/deepseek-v4.1-flash | To assess the occurrence of cardiac events in patients diagnosed with left main coronary artery disease on diagnostic cardiac catheterization and wait… |
| `db-jev-distill-v3-e2fc2ee2.Is this memory relevant for answering the query? Query: Both Ac…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | Sansevieria Sansevieria is a genus of about 70 species of flowering plants, native to Africa, Madagascar and southern Asia. Common names include mothe… |
| `db-jev-distill-v3-f16a74fa.Is this memory relevant for answering the query? Query: When wa…` | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | National Professional Basketball League was a pro basketball league in the USA in (1950-51). The league played just one season, with no championship f… |
| `db-jev-distill-v3-fec50b58.Rate compression difficulty for this scenario on a 0-5 scale.` | en | knowledge_reasoning | score | real | 6 | 3 | 5 | deepseek/deepseek-v4.1-flash | A 40-page incident report contains the guidance revision in minute 34; additionally has the dissenting opinion in a footnote. Context: for the executi… |
| `db-open-jev-b69608fa.bug_severity` | en | decision_mechanics | score | one_hot | 3 | 0 | 1 | deepseek/deepseek-v4.1-flash | Conversation with account holder Harbor-e059e62989. Customer message: My card was charged twice for the same monthly invoice. That is the request I wa… |
| `db-open-jev-effce146.bug_severity` | en | decision_mechanics | score | one_hot | 3 | 0 | 1 | deepseek/deepseek-v4.1-flash | Conversation with account holder Harbor-b61817726d. Customer message: My card was charged twice for the same monthly invoice. That is the request I wa… |

### 6.1 一致样例抽样（用于判断 Jev 是否真的在做题）

| qid | kind | 答案（两边一致） | 上游模型 | state 摘要 |
|---|---|---|---|---|
| `db-deepexi-fcs-v3-00161a77.next_step_candidate` | choice | RenamePartition | openai/gpt-6-luna | 如何更新数据湖元数据表的分区名称？ |
| `db-deepexi-fcs-v3-004897fd.next_step_candidate` | choice | StartMigrationJob | openai/gpt-6-luna | 我想启动一个数据迁移任务，实例ID是"123456"。 |
| `db-deepexi-fcs-v3-0801b674.next_step_candidate` | choice | CheckPermissions | openai/gpt-6-luna | 如何对用户的权限进行校验？ |
| `db-deepexi-fcs-v3-0972eb85.next_step_candidate` | choice | ListNodesByOutput | deepseek/deepseek-v4.1-flash | 根据输出结果为"failed"的节点精确查询目标节点。 |
| `db-deepexi-fcs-v3-0e4f56c3.next_step_candidate` | choice | ResetSynchronizationJob | openai/gpt-6-luna | 如何清空数据同步作业配置？ |
| `db-deepexi-fcs-v3-222e76bb.next_step_candidate` | choice | GenerateResourcePlanWithFlinkConfAsync | openai/gpt-6-luna | 我想提交一个异步工单来生成resource plan，工作空间ID是123，项目空间名称是abc，deploymentId是456。 |
| `db-deepexi-fcs-v3-24926bf6.next_step_candidate` | choice | DescribeDataCheckReportUrl | openai/gpt-6-luna | 我想获取数据检查报告的URL链接。 |
| `db-deepexi-fcs-v3-286b7fe5.next_step_candidate` | choice | ListUsers | openai/gpt-6-luna | 我想查看第三页的用户列表。 |
| `db-deepexi-fcs-v3-2ce13416.next_step_candidate` | choice | UpdateTableTheme | openai/gpt-6-luna | 我想更新主题的名称。 |
| `db-deepexi-fcs-v3-330e3f65.next_step_candidate` | choice | ListByUserGroupId | openai/gpt-6-luna | 用户组ID为"123,456,789"的用户组信息是什么？ |

## 7. 如实解读

1. **一致 = Jev 的答案与我们已有的 answer 相同**，这是两个答案源的比较，不是与客观真值的比较。
2. 语料真值的强度分层见 3.5：`real` 是来源给出的真实分布，`one_hot`/`uniform`/`answer_only` 多来自教师模型或硬标签，谈不上标准答案。
3. 判断谁更可能错，可用证据：(a) 一致率与随机基线的差距；(b) 真实分布子集上的一致率；(c) 同题重复调用的自洽率（模型自己都不稳定时，它的“分歧”多半是噪声）；(d) 逐条分歧样例的 state 与两边答案（第 6 节）。
4. 上游模型每次不同（第 5 节），一致率因此混合了“模型能力差异”和“路由随机性”。
5. **补不补概率这件事本身也有诚实口径**：探针若显示分布提示词可解析率低、或产出的分布普遍退化，就不做补全——**保持 answer_only 不丢人，塞假概率才丢人**（Lead 定，见 8.2）。

## 8. 第二阶段（补全 probs）现状

冻结语料中 answer-only 的 target 共 **8417** 个（`score` 545 / `choice` 7872）。
写入旁挂文件 `data/jev-probs.jsonl` 的**全部**条件：

1. Jev 返回可解析，且恰好命中一个选项；
2. 命中的选项 == 语料已有的 `answer`（保证 `argmax(probs) == answer`）；
3. 概率归一（和为 1）。

任一条不满足则该 target 保持 answer_only 不变，并计入本报告。**冻结语料在任何情况下都不修改。**

**当前状态**：Lead 已否掉方案 A（one-hot 的信息量等于 answer 本身，等于把问题原地搬一遍），决定先跑 **100 条配对探针**验证方案 B（分布提示词）。**探针未执行：账户余额耗尽（HTTP 402）**——需先给 OpenRouter 账户充值；另外这把 key 自身还有 $1 上限（剩 $0.80），跑满 8,417 条会先撞 key 上限，需要一并放宽。

```sh
uv run --no-project --offline python datasets/general/jev_fill.py fill-plan
uv run --no-project --offline python datasets/general/jev_fill.py run --phase fill --budget 5
uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation
uv run --no-project --offline python datasets/general/jev_fill.py verify --phase fill
```

### 8.1 由第一阶段推出的第二阶段预期（等确认）

第一阶段里 **answer-only 子集（正是第二阶段要补的人群）一致率 = 74/74 = 100.0% [95%CI 95.1%–100.0%]**。但该子集的 74 条**全部是 `zh|decision_mechanics|choice`**，第二阶段剩下的 545 条 `en|score` 在本次抽样里没有落进 answer-only 子集，只能用同 kind 的 score 实测值外推。分块外推如下：

| 第二阶段子集 | 条数 | 第一阶段实测一致率 | 预计可写入（95%CI 外推） |
|---|---|---|---|
| zh|decision_mechanics|choice | 7,872 | 74/74 = 100.0% [95%CI 95.1%–100.0%] | 7,484–7,872 |
| en score（两个 domain 合计） | 545 | 17/29 = 58.6% [95%CI 40.7%–74.5%] | 222–406 |
| 合计 | 8,417 | — | 7,706–8,278 |

结论：`zh choice` 这一块几乎肯定能写满；`en score` 的 545 条证据很弱（score 只有 17/29 = 58.6% [95%CI 40.7%–74.5%]），可能大量保持 answer_only。

成本外推（**两个口径都要看**）：账户侧口径单次 $0.000898 → 跑满 8,417 条约 **$7.56，超过第二阶段的 $5 上限**；脚本逐条口径单次 $0.000589 → 约 $4.96，恰好贴线。所以第二阶段要么把上限提到 $8 左右，要么接受在 $5 处提前停止（按均值口径约能跑 5,565 条 ≈ 全部 zh choice）。最坏情况（全部路由到最贵的上游，均价 $0.005510/次）约 $46.4，因此必须按 0.1 节的**自适应预算**执行：超限即停、已完成调用不丢、可续跑。

**方案选择（Lead 已定）**：

- ~~方案 A~~（answer 变体 → 命中项 one-hot）**否掉**：probs 的信息量等于 answer 本身，属契约 2.3 的“伪 one-hot”，拿它去“补全”等于把 8,417 条 answer_only 变成 8,417 条伪 one-hot。
- **方案 B**（distribution 变体 → 各选项概率，门禁 argmax == answer）：先跑 100 条配对探针验证协议，再决定是否跑满。

探针要量四件事（脚本已实现，journal 与统计都在 `report` 的附录 A 自动产出）：

1. 分布提示词的**可解析率**；
2. 产出的分布是否**非退化**（不是 one-hot、也不是均匀）；
3. **argmax 是否等于语料 answer**（契约硬约束）；
4. **同一题两套提示词的 argmax 是否一致**（配对自洽性）。

若可解析率低、或分布普遍退化，**就不做补全**：保持 answer_only 不丢人，塞假概率才丢人。

命令（同一批 100 个 qid，是第一阶段 300 条样本的**真子集**，可直接配对）：

```sh
uv run --no-project --offline python datasets/general/jev_fill.py sample --n 100 --seed 20261015 --variant distribution
uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation \
    --plan datasets/general/data/jev/validation-plan-distribution.jsonl \
    --journal datasets/general/data/jev/probe-dist-calls.jsonl --budget 0.06
uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation   # 附录 A
```

### 8.2 要跑完第二阶段，需要同时满足的条件（清单）

下面 5 条**全部**满足才开跑；任何一条不满足，第二阶段就只停留在「已就绪、未执行」，并如实写进本报告。

| # | 条件 | 现状（2026-10-15） | 怎么确认 |
|---|---|---|---|
| 1 | OpenRouter 账户有余额 | **已耗尽**：`total_credits=5, total_usage=5.21` | `jev_fill.py credits` |
| 2 | 这把 key 的额度上限调大 | **是瓶颈**：key limit $1，已用 $0.196，剩 $0.804 | `jev_fill.py credits` |
| 3 | 第二阶段预算上限提到 $8 | 任务书写的是 $5；账户侧口径跑满需 $7.56 | Lead 改口径/批准 |
| 4 | 配对探针四项达标 | **未跑**（卡在 1、2） | `jev_fill.py probe` |
| 5 | probs 形态定为方案 B | 方案 A 已否；B 待探针 | 报告附录 A |

口径（Lead 定）：**保持 answer_only 不丢人，塞假概率才丢人。** 若探针显示分布提示词可解析率低、或产出的分布普遍退化，结论就是「这份数据只有硬标签」，照实写进报告，**不做补全**——而不是退回方案 A 硬塞一份 one-hot。

探针就绪、一条命令即可启动（不依赖人工判断）：

```sh
# 条件 1/2 满足后：跑探针 -> 自动重生成报告（附录 A 出四张表）
uv run --no-project --offline python datasets/general/jev_fill.py probe --budget 0.06

# 先看余额
uv run --no-project --offline python datasets/general/jev_fill.py credits

# 探针四项过关后，再跑满（自适应预算，超限即停、可续跑）
uv run --no-project --offline python datasets/general/jev_fill.py run --phase fill --budget 8 \
    --retry-truncated --workers 6
uv run --no-project --offline python datasets/general/jev_fill.py verify --phase fill
uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation
```

## 9. 产物

| 路径 | 内容 |
|---|---|
| `datasets/general/jev_fill.py` | 本报告的生成脚本（抽样/调用/解析/报告/校验） |
| `datasets/general/jev-validation.md` | 本文件 |
| `datasets/general/data/jev/validation-plan.jsonl` | 抽样清单（manifest + 300 条，含分层与真值） |
| `datasets/general/data/jev/validation-calls.jsonl` | 逐次尝试的原始响应与成本（可续跑） |
| `datasets/general/data/jev/fill-plan.jsonl` | 第二阶段请求清单（8,417 条 answer-only target） |
| `datasets/general/data/jev/fill-calls.jsonl` | 第二阶段的原始响应与成本（尚未生成） |
| `datasets/general/data/jev-probs.jsonl` | 第二阶段的旁挂概率（answer-only 补全结果） |

冻结语料只读：`items.final.jsonl` 与 `data/splits/` 四区文件在本任务中未被写入。

