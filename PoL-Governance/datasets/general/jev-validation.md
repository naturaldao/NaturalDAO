# Jev 分层校验与 probs 补全报告

> 本报告含两部分：**第一阶段**（与语料真值的分层一致性校验，第 1–7 节）与**第二阶段**（旁挂 probs 的补全/升级，第 8 节；两条线分开统计）。

> 生成时间：2026-10-20T13:19:11+00:00 ｜ 生成脚本：jev-v0.1（[jev_fill.py](jev_fill.py)）
> 语料：`datasets/general/data/items.final.jsonl`（明文不入库，见 .gitignore；只读，未改动）
>
> ⚠️ **语料版本说明**：第一阶段抽样基于 plan 记录的语料版本（sha256 前缀 `21f11fe3dc39edd9`）；**会话期间语料被其他任务重建**，当前版本 sha256 前缀 `47df533ec00bc94d`、target 数 82,843（旧版 31,786）。已核对：**旧版 target 0 缺失**（第一阶段 300 条抽样、jev-router 1,883 条、mercury 7,907 条全部仍能对上冻结语料），因此第一阶段的结论不受影响；但 8.4 的形态构成表按**当前版本**统计。
> 凭据配置为仓外/本机的 `datasets/jev.yaml`（未提交到仓库）；model=typesafe/jev-router，endpoint 主机 openrouter.ai；密钥只记录指纹。

## 0. 结论摘要

| 指标 | 值 |
|---|---|
| 计划抽样条数（按 lang x domain x kind 分层） | 300 |
| 本次报告覆盖的请求数 | 300 |
| 成功取得响应 | 218 |
| 未跑完（计划 - 成功；预算上限 + 余额耗尽） | 0 |
| HTTP 200 有效响应 | 218/300 |
| 可解析率（占有效响应） | 205/218 = 94.0% [95%CI 90.1%–96.5%] |
| 与语料真值一致率（占可解析） | 151/205 = 73.7% [95%CI 67.2%–79.2%] |
| 随机基线期望一致率（同一批可解析题） | 29.2% |
| 一致率 / 基线 | 2.52x |
| 成本合计（成功响应，脚本口径） | $0.18661 |
| 其中 API 实测 / 兜底估计 | $0.18661 / $0.00000 |
| 账户侧权威口径（GET /key 的 usage） | $0.19585 |
| 单次成功调用成本（账户侧口径） | $0.000616 |
| 上游模型数（异构教师） | 9 |

- **一致率是否高于随机**：是，明显高于随机基线（一致率 73.7%，基线 29.2%）。
- **可解析率**：205/218 = 94.0% [95%CI 90.1%–96.5%]；不可解析的原因分布见第 4 节。
- **最弱的三层**（3.8 节逐层给了解读与保留）：`en|decision_mechanics|choice` 显著高于随机、`en|knowledge_reasoning|noul` 与随机不可区分、`uniform` 与随机不可区分；后两层经 Wilson CI 判定**与随机不可区分**，因此它们既不支持“我们错”也不支持“Jev 错”。
- **第二阶段两条线的产出**（详见 8.3/8.4）：mercury-decide 升级 noul 的**原生校准概率**，以及 jev-router 已经付费的 zh-choice 分布；两者在旁挂文件里按 `distribution_semantics` 分开标记，**不合并计数**。
- **诚实说明**：本阶段的“一致”只是 **Jev 的答案 == 语料已有的 answer**。语料里大量 target 的 answer 本身来自教师模型或伪 one-hot（见 3.5 按 shape 分列），因此**一致率低不等于语料错**，一致率高也不等于语料对；能下判断的是“与随机基线的差距”“真实分布子集上的一致率”和“同题重复的自洽率”。

### 0.1 为什么停在 218/300：先是撞预算上限，后是 OpenRouter 余额不足（HTTP 402）

**第一轮（上限 $0.05）**：派发前按「命令行给的单次估计」（$0.0001/次）预留预算，但 `typesafe/jev-router` 每次路由到不同上游模型，单次成本实测跨 **3 个数量级**（本阶段整体：中位数 $0.000071、均值 $0.000587、最高 $0.007370）。估计值比实际低约 4–5 倍，跑到 $0.05 上限时**该轮**已花掉 $0.0584，**超出上限 16.8%**；该轮对应 journal 的**前 163 行**（journal 是只追加的，界址可复算）。已按“超限即停”停止，未继续追加调用。

预算预留已改成**自适应**（预留额 = max(命令行估计, 已观测均值 x 2)）；Lead 随后把上限放到 $0.12，于是补跑了第二轮：又拿到若干响应后，**80 条请求返回 HTTP 402 “Insufficient credits”**，账户余额耗尽，整批停止（402 不计费，已完成的调用全部保留在 journal）。脚本已把 402 识别为**致命错误**：一旦出现就停止整批派发，避免第二阶段白刷 8,000 次。

**余额证据（2026-10-15T05:44Z 实测，可直接复算）**：

```sh
curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $JEV_API_KEY"
# -> {"data":{"total_credits":5,"total_usage":5.210495714}}   # 账户额度已用尽
curl -s https://openrouter.ai/api/v1/key     -H "Authorization: Bearer $JEV_API_KEY"
# -> limit_usd=1, usage=0.195851448, limit_remaining=0.804148552   # 这把 key 另有 $1 硬上限
```

**这两条对第二阶段都是硬约束**：账户要有余额（按实测均值，8,417 次约 $4.94）；同时这把 key 自身的 $1 上限只剩 $0.80，**即使账户充值，跑满 8,417 条也会先撞 key 上限**——需要换一把额度更高的 key，或先把 key limit 调大。

未跑完的 0 条本身只需约 $0.000（中位数口径）到 $0.000（均值口径）。

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
| 成功响应（HTTP 200） | 318 |
| HTTP 非 200 响应（402 等，不计费） | 82 |
| 未收到响应（网络/超时） | 3 |
| 因预算上限未发出（跳过） | 7 |
| prompt tokens | 73234 |
| completion tokens | 91052 |
| 成本合计（成功响应） | $0.18661 |
| 其中 API 回传 cost 的实测部分 | $0.18661 |
| 其中 API 未回传 cost、按兜底估计的部分 | $0.00000 |
| 单次成功调用成本（实测+估计） | $0.000587 |
| 单次成本中位数 / 最高 | $0.000071 / $0.007370 |
| 成功响应中 cost 来自 API 实测的条数 | 318 |

**口径说明（重要）**：脚本逐条累加的是 OpenRouter 响应里的 `usage.cost`，本阶段合计 $0.18661；而账户侧 `GET /key` 的 `usage` 是 $0.19585，**高 $0.00925（+5%）**。差额来源未查明（可能是 router 加价/计费口径不同，也可能这把 key 在别处也被用过），因此本报告的分列成本只作相对比较，**做预算一律用账户侧口径**：单次 $0.000616。若按脚本口径 ($0.000587/次) 规划，会低估一半。

**成本结论（唯一口径）**：以**账户侧**为准，单次 **$0.000616**；据此跑满第二阶段 8,417 条 ≈ **$5.18**。脚本逐条累加的口径（$0.000587/次 → $4.94）会低估约一半，不要用它做预算。

预算：本阶段硬上限 **$0.05**（`--budget`），超限即停并保留已完成的调用。

### 上游模型分布（异构教师）

| 上游模型 | 调用数 | 占比 | 成本 | 单次均价 | completion tokens |
|---|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | 84 | 21.0% | $0.06285 | $0.000748 | 54760 |
| x-ai/grok-4.7 | 10 | 2.5% | $0.04605 | $0.004605 | 5505 |
| meta/muse-spark-1.2 | 6 | 1.5% | $0.03218 | $0.005363 | 7393 |
| google/gemini-3.8-flash | 10 | 2.5% | $0.02193 | $0.002193 | 5614 |
| openai/gpt-6-luna | 117 | 29.2% | $0.00588 | $0.000050 | 8346 |
| stepfun/step-5-preview | 1 | 0.2% | $0.00551 | $0.005510 | 2000 |
| z-ai/glm-5.3-flash | 74 | 18.5% | $0.00486 | $0.000066 | 3833 |
| deepseek/deepseek-v4.1-flash-1017 | 10 | 2.5% | $0.00467 | $0.000467 | 3268 |
| z-ai/glm-5.3 | 6 | 1.5% | $0.00267 | $0.000445 | 333 |

`typesafe/jev-router` 每次可能路由到不同上游模型，因此 Jev 产出的是**异构教师**的判断，不是单一模型的稳定输出。

## 附录 A. 附加探针：distribution 变体（另采样）

同一批 qid 再跑一遍，只把提示词换成“给出各选项概率（JSON 序号→概率）”。本探针回答四个问题：**(1)** 分布提示词的可解析率；**(2)** 产出的分布是否非退化（不是 one-hot、也不是均匀）；**(3)** argmax 是否等于语料 answer（契约硬约束）；**(4)** 同一题两套提示词的 argmax 是否一致。

| 指标 | 值 |
|---|---|
| 抽样条数 | 100 |
| 有效响应 | 100 |
| 拿到合法分布（可解析） | 100/100 = 100.0% [95%CI 96.3%–100.0%] |
| argmax 与真值一致 | 68/100 = 68.0% [95%CI 58.3%–76.3%] |
| 随机基线 | 30.6% |
| 本探针成本 | $0.05825 |

**(2) 分布是否非退化**（分母 = 拿到合法分布的 100 条）：

| 指标 | 值 |
|---|---|
| 非退化（既非 one-hot 也非均匀） | 53/100 = 53.0% [95%CI 43.3%–62.5%] |
| 退化：恰好一个选项非零（one-hot） | 42/100 = 42.0% [95%CI 32.8%–51.8%] |
| 退化：各选项相等（均匀） | 5/100 = 5.0% [95%CI 2.2%–11.2%] |
| 支撑集 = 全部选项 | 51/100 = 51.0% [95%CI 41.3%–60.6%] |
| 非零选项数中位数 | 2 |
| 最大概率中位数 | 0.944 |
| 最大概率均值 | 0.871 |

**配对比较**（两套提示词跑在**同一批 qid** 上，可直接比）：

| 指标 | answer 变体（单选项） | distribution 变体（给分布） |
|---|---|---|
| 可解析 | 70/100 | 100/100 |
| 与真值一致（按全部配对算，未解析计为不一致） | 47/100 = 47.0% [95%CI 37.5%–56.7%] | 68/100 = 68.0% [95%CI 58.3%–76.3%] |
| 与真值一致（**仅两套都解析的 70 条**，公平口径） | 47/70 = 67.1% [95%CI 55.5%–77.0%] | 46/70 = 65.7% [95%CI 54.0%–75.8%] |
| 成本 | $0.04621 | $0.05825 |
| 都能解析的条数 | 70 | 70 |
| 两套提示词给出同一个选项 | 62/70 = 88.6% [95%CI 79.0%–94.1%] | — |

## 附录 B. mercury-decide 决策端点与 noul 验证（2026-10-20）

官方 Jev 路由端的成本/限流问题解决后，改用**决策专用端点**（不是 chat/completions）：

```text
POST https://openrouter.ai/api/alpha/decisions     # 注意是 /api/alpha/，不是 /api/v1/
Content-Type: application/json

{"model": "inception/mercury-decide",
 "state": "<item.state 原文>",
 "questions": {"next_step_candidate": {"type": "noul",
                                        "instructions": "<question.prompt>"}}}

# 返回
{"model": "inception/mercury-decide-20260930",
 "answers": {"next_step_candidate": {"type": "noul", "noul": 0.8519...}},
 "usage": {"input_tokens": 65, "output_tokens": 1, "cost": 0.0000013}}
```

要点：

1. `type` 的合法值就是 `noul` / `choice` / `score` / `box`，与本数据集三种原语对应；`noul` 直接返回 **P(yes)**，不用解析文本。
2. 我们把这一个数转成两个选项上的分布：`{正类key: p, 负类key: 1-p}`；写入门禁仍是 **argmax == 语料已有 answer**。
3. 语料里 489 条 noul 的选项 key 是整句判据（如 `yes_escalation_is_warran` / `no_escalation_is_not_war`），解析器按 `yes_/no_` 前缀判极性后才覆盖到全部 7,907 条。
4. **`:free` 变体不可用**：账户 free 配额还剩 988/1000，但请求持续 HTTP 429 （上游 `rate_limit_exceeded`），间隔 6 秒重试 3 次仍 429——是 free 通道本身限流，不是配额。改用同款付费 id `inception/mercury-decide`（返回同一模型 `inception/mercury-decide-20260930`），单次 $0.0000013，跑满 7,907 条约 $0.01，把可靠性买了回来。

| 指标 | 值 |
|---|---|
| 验证条数（两批各 20，累积） | 40 |
| 可解析 | 40/40 = 100.0% [95%CI 91.2%–100.0%] |
| argmax(P) == 语料 answer | 35/40 = 87.5% [95%CI 73.9%–94.5%] |
| 正类（true/yes）命中 | 13/13 = 100.0% [95%CI 77.2%–100.0%] |
| 负类（false/no）命中 | 22/27 = 81.5% [95%CI 63.3%–91.8%] |
| **平衡准确率**（正负类精度的均值） | 90.7% |
| “全猜 no”平凡基线 | 67.5% |
| 模型判正率 vs 语料正例占比 | 45.0% vs 45.0% |
| 成本（40 次） | $0.000238 |
| 单次成本 | $0.00000595 |
| 延迟中位数 | 900.2 ms |

**解读（必须一起读）**：

- 87.5% 的总体命中率**不能单独看**：noul 里大多数答案是 no，“全猜 no”就有 67.5%。有意义的是**平衡准确率 90.7%**（正类 13/13、负类 22/27）。
- 不平衡方向要说清：**模型偏向判“是”**（负类漏判 5 条），所以这条链路更适合当“召回优先的软标签”，不要当成无偏裁判。
- **P(yes) 是双峰的**（下面直方图）：多数落在 <0.01 或 >0.99，说明它是**原生校准概率**，不是我们诊断出的那类伪 one-hot。

| P(yes) 区间 | [0.00, 0.01) | [0.01, 0.05) | [0.05, 0.20) | [0.20, 0.50) | [0.50, 0.80) | [0.80, 0.99) | [0.99, 1.00) |
|---|---|---|---|---|---|---|---|
| 条数 | 17 | 4 | 1 | 0 | 4 | 3 | 11 |

## 6. 分歧样例（逐条）

共 54 条分歧（占可解析 26.3%）。state 摘要为单行截断，完整 state 见语料。

| 样本（匿名） | lang | domain | kind | shape | 选项数 | 语料 answer | Jev 答案 | 上游模型 | state 摘要 |
|---|---|---|---|---|---|---|---|---|---|
| 样本 #075（id 从略） | en | decision_mechanics | choice | one_hot | 20 | get_participant_status | report_adverse_event | deepseek/deepseek-v4.1-flash | Hi, I’m calling as a participant in the Phase II respiratory trial (ID: PT-44556). I’m experiencing severe wheezing that started around 8:00 PM on Aug… |
| 样本 #076（id 从略） | en | decision_mechanics | choice | one_hot | 20 | get_appointment_details | authenticate_user | openai/gpt-6-luna | Hello, I need to cancel my car wash appointment. My license plate is ABC123, and the appointment ID is SH789. It’s scheduled for a Premium Shine at 9 … |
| 样本 #077（id 从略） | en | decision_mechanics | choice | one_hot | 13 | get_package_details | transfer_to_human_coordi | deepseek/deepseek-v4.1-flash | Hello, my name is [Customer Name], and I'm reaching out to request a transfer of my career coaching session credits to my spouse's account. My User ID… |
| 样本 #078（id 从略） | en | decision_mechanics | choice | one_hot | 18 | get_booking_details | schedule_vendor_call | openai/gpt-6-luna | Hi, my name is [Groom's Name], and I’m calling about my wedding photography booking. My booking ID is BKG-556677, and my email is <REDACTED_EMAIL>. I’… |
| 样本 #079（id 从略） | en | decision_mechanics | choice | one_hot | 14 | transfer_to_human_agent | authenticate_user | deepseek/deepseek-v4.1-flash | Hello, I'm calling regarding a temperature deviation for a vaccine shipment with tracking number 9400100000000000000030. Our records show the temperat… |
| 样本 #080（id 从略） | en | decision_mechanics | choice | one_hot | 17 | transfer_to_human_agent | authenticate_applicant | openai/gpt-6-luna | Hello, my name is [Student Name], and I'm calling to update my graduation timeline. My application ID is GRAD-DATE-22, and I was born on March 30, 200… |
| 样本 #081（id 从略） | en | decision_mechanics | choice | one_hot | 15 | get_wedding_profile | authenticate_client | deepseek/deepseek-v4.1-flash | Hello, I’m calling about unexpected overtime charges from my photographer for the wedding on October 25, 2025 at the Vineyard venue. My client ID is B… |
| 样本 #082（id 从略） | en | decision_mechanics | choice | one_hot | 19 | transfer_to_human_agent | generate_troubleshooting | openai/gpt-6-luna | Hi, I'm having trouble with the practice videos buffering on my iPad Pro even though my internet speed is 150 Mbps. My student ID is MM-7799. Can you … |
| 样本 #083（id 从略） | en | decision_mechanics | choice | one_hot | 14 | get_customer_profile | modify_order | openai/gpt-6-luna | Hello, I'm reaching out regarding our recent order #COMFC4433 under government contract #GOVX2287, which has already been validated for FOB terms. We … |
| 样本 #084（id 从略） | en | decision_mechanics | choice | one_hot | 17 | get_user_profile | get_order_details | openai/gpt-6-luna | Hello, I recently purchased a video game through your store, but I think there might be an issue with the regional version. I bought the EU edition wh… |
| 样本 #086（id 从略） | en | decision_mechanics | choice | one_hot | 21 | get_user_profile | get_pricing_tiers | openai/gpt-6-luna | Hello, I'm calling about a parking charge I received. I parked at 6:50 AM and left at 7:05 AM, but I was charged $5 for the hour starting at 6:50. Why… |
| 样本 #087（id 从略） | en | decision_mechanics | choice | one_hot | 17 | access_recording | get_recording_processing | deepseek/deepseek-v4.1-flash | Hello, I'm Dr. Emily Carter, a VIP healthcare professional with access to your platform. I'm calling regarding a session recording issue for Event ID … |
| 样本 #089（id 从略） | en | decision_mechanics | choice | one_hot | 17 | get_child_profile | add_pickup_contact | openai/gpt-6-luna | Hello, I need to urgently add a new contact for my child INF-44. There’s been a family emergency, and I can only provide 24 hours’ notice instead of t… |
| 样本 #090（id 从略） | en | decision_mechanics | choice | one_hot | 18 | transfer_to_specialist | resolve_invoice | openai/gpt-6-luna | Hello, I'm reaching out to request a consolidated billing statement for multiple invoices under my client's account. Could you please generate a combi… |
| 样本 #093（id 从略） | en | decision_mechanics | choice | one_hot | 17 | transfer_to_human_agent | verify_compliance | deepseek/deepseek-v4.1-flash | Hello, I'm calling from the National Park Service regarding Project ID MON-2025-444 (Organization ID: NPS-2025). I need to verify compliance with site… |
| 样本 #094（id 从略） | en | decision_mechanics | choice | one_hot | 19 | get_customer_profile | request_service_change | openai/gpt-6-luna | Hello, I'm calling to update my utility service for account #990044. My current ZIP is 90039, and I'm moving to unit 5B in the same building. Can you … |
| 样本 #095（id 从略） | en | decision_mechanics | choice | one_hot | 16 | record_verbal_confirmati | adjust_billing | deepseek/deepseek-v4.1-flash | Hi, I'm calling regarding an unusually high energy bill. My account is linked to meter ID SMART-1010, and my current bill is 210% higher than last mon… |
| 样本 #096（id 从略） | en | decision_mechanics | choice | one_hot | 16 | transfer_to_human_agent | notify_coast_guard | openai/gpt-6-luna | I'm calling to report an illegal oil discharge I observed from a commercial vessel yesterday near the coastal conservation area. My name is associated… |
| 样本 #097（id 从略） | en | decision_mechanics | choice | one_hot | 17 | get_application_status | authenticate_applicant | openai/gpt-6-luna | Hi, I'm a domestic undergraduate applicant with Application ID U246823 and a birthdate of July 8, 2005. I recently changed my phone number and need to… |
| 样本 #098（id 从略） | en | decision_mechanics | choice | one_hot | 22 | rotate_access_key | check_resource_state | openai/gpt-6-luna | Hello, I'm a security specialist with a media company, and I need to confirm compliance with our mandatory 90-day access key rotation policy. Could yo… |
| 样本 #100（id 从略） | en | decision_mechanics | choice | one_hot | 16 | create_dock_reservation | verify_identity | openai/gpt-6-luna | Hello, I'm a member with Member ID CY-8901 and vessel registration ending in 0123. I'm calling about the slip size requirement for my 48-foot boat. I … |
| 样本 #101（id 从略） | en | decision_mechanics | choice | one_hot | 20 | get_program_schedule | get_tuition_details | deepseek/deepseek-v4.1-flash | Hi, I'm calling about my child C373. We need to switch from full-time (5 days/week) to part-time (3 days/week) starting November 1st due to scheduling… |
| 样本 #102（id 从略） | en | decision_mechanics | choice | one_hot | 22 | transfer_to_care_coordin | get_program_details | openai/gpt-6-luna | Hi, I’m calling about the childcare enrollment platform. As a parent, I’m concerned about ensuring all children feel included in playgroup activities,… |
| 样本 #103（id 从略） | en | decision_mechanics | choice | one_hot | 13 | transfer_to_human_agent | create_service_ticket | deepseek/deepseek-v4.1-flash | Hello, I’m calling about significant water damage at my home located at 404 Water St. The drywall in my living room collapsed after a 2-hour leak, and… |
| 样本 #104（id 从略） | en | decision_mechanics | choice | one_hot | 13 | get_item_availability | get_membership_benefits | openai/gpt-6-luna | Hello, I’m calling about a 7-day rental for SKU SUT-6666. As a Bronze member, I’d like to calculate the total cost including the damage waiver. Could … |
| 样本 #106（id 从略） | en | decision_mechanics | choice | one_hot | 15 | get_regional_pest_alerts | transfer_to_agronomist | deepseek/deepseek-v4.1-flash | Hello, I'm a citrus grower in the Florida lowlands with Farmer ID F1013. I need to request an experimental fungicide that isn't listed in your product… |
| 样本 #107（id 从略） | en | decision_mechanics | choice | one_hot | 14 | issue_compensation | report_incident | openai/gpt-6-luna | Hello, I’m calling regarding a temperature issue in our climate-controlled storage unit CL-889 (reservation R54321). On July 15th, the temperature in … |
| 样本 #109（id 从略） | en | decision_mechanics | choice | one_hot | 17 | get_reservation_details | transfer_to_human_agent | openai/gpt-6-luna | Hello, my name is Stewart and I have a booking reference OV789012 for a cruise departing on June 10, 2024. I'm reaching out to inquire if there are pa… |
| 样本 #111（id 从略） | en | decision_mechanics | choice | one_hot | 11 | transfer_to_human_agent | manage_gate_appointment | deepseek/deepseek-v4.1-flash | Hello, I need to verify the arrival timestamp for a truck with plate AUDIT-EXP-25 under appointment ID EXP-20251014-0730. Could you please confirm if … |
| 样本 #112（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | deepseek/deepseek-v4.1-flash | Although Helicobacter pylori eradication is effective in treating low-grade gastric mucosa-associated lymphoid tissue (MALT) lymphoma, the condition i… |
| 样本 #115（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | C. Halifax Town 4-0 2-0 2-1 0-0 1-1 2-1 2-0 1-0 3-3 4-0 1-1 4-0 1-1 5-1 2-0 2-1 2-2 5-1 1-0 2-0 3-0 3-4 3-2 Forest Green Rovers 3-1 3-1 1-2 0-2 3-2 3-… |
| 样本 #116（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | deepseek/deepseek-v4.1-flash | Malpas, Cheshire Malpas is a large village that used to be a market town. It is also a civil parish in the unitary authority of Cheshire West and Ches… |
| 样本 #120（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | )Chumacero 62' Report (FIFA)Report (CONMEBOL) Rodríguez 10'Bacca 41'Cardona 90+2' 24 March 2016 (2016-03-24)16:00 UTC 5 Ecuador 2-2 Paraguay Estadio O… |
| 样本 #130（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | The regatta was organized by Sailing Academy of St. Petersburg Yacht Club. According to the idea of the organizers, this winter event will be held on … |
| 样本 #131（id 从略） | en | decision_mechanics | score | real | 6 | 4 | 5 | deepseek/deepseek-v4.1-flash | An autonomous vehicle passes an active school zone at dismissal; additionally requires an unpaved segment for 8km. Context: in low-visibility conditio… |
| 样本 #132（id 从略） | en | knowledge_reasoning | score | real | 6 | 1 | 5 | deepseek/deepseek-v4.1-flash | A collaboration archive has versioned metadata and checksums; additionally is stored with a 3-2-1 backup strategy. Context: before the personnel depar… |
| 样本 #134（id 从略） | en | decision_mechanics | choice | real | 4 | issue_warning | maintain | deepseek/deepseek-v4.1-flash | A regional warehouse shows a count variance of 2.3%; additionally flags 340 units damaged in transit. Context: SKU AX-330, under reduced staffing. Rep… |
| 样本 #135（id 从略） | en | decision_mechanics | score | real | 6 | 3 | 4 | deepseek/deepseek-v4.1-flash | A distribution center detects expiration risk on 1,200 units; additionally shows a count variance of 2.3%. Context: a bonded SKU, following a recent a… |
| 样本 #138（id 从略） | en | knowledge_reasoning | noul | real | 2 | true | false | deepseek/deepseek-v4.1-flash | A course suggestion was returned by this user 2 months ago; additionally was explicitly filtered out by preference settings. Context: in the seasonal … |
| 样本 #140（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | F.C. Fylde 42 22 9 11 76 53 +23 75 4 Harrogate Town 42 21 9 12 73 46 +27 72 5 Boston United 42 22 5 15 73 60 +13 71 6 Nuneaton Town 42 20 13 9 71 46 +… |
| 样本 #141（id 从略） | en | knowledge_reasoning | score | real | 6 | 3 | 5 | meta/muse-spark-1.2 | A 40-page incident report is already a summary of a summary; additionally has 2 material contradictions. Context: for the 1-page brief, during an exte… |
| 样本 #143（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | Cheese - Lotsa Pasta , Louisville's Gourmet Grocery Lotsa Pasta,Louisville,pasta,fresh pasta,international grocery store,imported food,homemade food .… |
| 样本 #144（id 从略） | en | knowledge_reasoning | score | real | 6 | 4 | 3 | google/gemini-3.8-flash | An autoclave cycle was performed outside the certified cabinet; additionally deviated from the approved protocol with supervisor sign-off. Context: du… |
| 样本 #146（id 从略） | en | decision_mechanics | score | real | 6 | 3 | 4 | deepseek/deepseek-v4.1-flash | The release candidate shows a 9% regression in the p95 benchmark; additionally was rebased after a security patch. Context: in the payments repo, foll… |
| 样本 #147（id 从略） | en | knowledge_reasoning | score | real | 6 | 3 | 1 | meta/muse-spark-1.2 | A merchandising slot was explicitly filtered out by preference settings; additionally is the only available option. Context: for this user profile, sh… |
| 样本 #148（id 从略） | en | decision_mechanics | score | real | 6 | 3 | 0 | deepseek/deepseek-v4.1-flash | Service catalog-sync shows clock skew of 800ms across replicas; additionally reports cardinality explosion in the metrics store. Context: over the las… |
| 样本 #156（id 从略） | en | decision_mechanics | choice | real | 4 | vendor | compliance | deepseek/deepseek-v4.1-flash | The renewal deadline needs a document that takes 15 days to obtain; additionally depends on a vendor response with a 5-day SLA. Context: under the con… |
| 样本 #165（id 从略） | en | decision_mechanics | score | real | 6 | 4 | 0 | deepseek/deepseek-v4.1-flash | The log shipper reports empty scrape targets after the network change; additionally matches last Tuesday's incident signature. Context: during the bat… |
| 样本 #173（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | deepseek/deepseek-v4.1-flash | To assess the occurrence of cardiac events in patients diagnosed with left main coronary artery disease on diagnostic cardiac catheterization and wait… |
| 样本 #174（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | Sansevieria Sansevieria is a genus of about 70 species of flowering plants, native to Africa, Madagascar and southern Asia. Common names include mothe… |
| 样本 #177（id 从略） | en | knowledge_reasoning | noul | uniform | 2 | false | true | openai/gpt-6-luna | National Professional Basketball League was a pro basketball league in the USA in (1950-51). The league played just one season, with no championship f… |
| 样本 #180（id 从略） | en | knowledge_reasoning | score | real | 6 | 3 | 5 | deepseek/deepseek-v4.1-flash | A 40-page incident report contains the guidance revision in minute 34; additionally has the dissenting opinion in a footnote. Context: for the executi… |
| 样本 #206（id 从略） | en | decision_mechanics | score | one_hot | 3 | 0 | 1 | deepseek/deepseek-v4.1-flash | Conversation with account holder Harbor-e059e62989. Customer message: My card was charged twice for the same monthly invoice. That is the request I wa… |
| 样本 #216（id 从略） | en | decision_mechanics | score | one_hot | 3 | 0 | 1 | deepseek/deepseek-v4.1-flash | Conversation with account holder Harbor-b61817726d. Customer message: My card was charged twice for the same monthly invoice. That is the request I wa… |

### 6.1 一致样例抽样（用于判断 Jev 是否真的在做题）

| 样本（匿名） | kind | 答案（两边一致） | 上游模型 | state 摘要 |
|---|---|---|---|---|
| 样本 #001（id 从略） | choice | RenamePartition | openai/gpt-6-luna | 如何更新数据湖元数据表的分区名称？ |
| 样本 #002（id 从略） | choice | StartMigrationJob | openai/gpt-6-luna | 我想启动一个数据迁移任务，实例ID是"123456"。 |
| 样本 #003（id 从略） | choice | CheckPermissions | openai/gpt-6-luna | 如何对用户的权限进行校验？ |
| 样本 #004（id 从略） | choice | ListNodesByOutput | deepseek/deepseek-v4.1-flash | 根据输出结果为"failed"的节点精确查询目标节点。 |
| 样本 #005（id 从略） | choice | ResetSynchronizationJob | openai/gpt-6-luna | 如何清空数据同步作业配置？ |
| 样本 #006（id 从略） | choice | GenerateResourcePlanWithFlinkConfAsync | openai/gpt-6-luna | 我想提交一个异步工单来生成resource plan，工作空间ID是123，项目空间名称是abc，deploymentId是456。 |
| 样本 #007（id 从略） | choice | DescribeDataCheckReportUrl | openai/gpt-6-luna | 我想获取数据检查报告的URL链接。 |
| 样本 #008（id 从略） | choice | ListUsers | openai/gpt-6-luna | 我想查看第三页的用户列表。 |
| 样本 #009（id 从略） | choice | UpdateTableTheme | openai/gpt-6-luna | 我想更新主题的名称。 |
| 样本 #010（id 从略） | choice | ListByUserGroupId | openai/gpt-6-luna | 用户组ID为"123,456,789"的用户组信息是什么？ |

## 7. 如实解读

1. **一致 = Jev 的答案与我们已有的 answer 相同**，这是两个答案源的比较，不是与客观真值的比较。
2. 语料真值的强度分层见 3.5：`real` 是来源给出的真实分布，`one_hot`/`uniform`/`answer_only` 多来自教师模型或硬标签，谈不上标准答案。
3. 判断谁更可能错，可用证据：(a) 一致率与随机基线的差距；(b) 真实分布子集上的一致率；(c) 同题重复调用的自洽率（模型自己都不稳定时，它的“分歧”多半是噪声）；(d) 逐条分歧样例的 state 与两边答案（第 6 节）。
4. 上游模型每次不同（第 5 节），一致率因此混合了“模型能力差异”和“路由随机性”。
5. **补不补概率这件事本身也有诚实口径**：探针若显示分布提示词可解析率低、或产出的分布普遍退化，就不做补全——**保持 answer_only 不丢人，塞假概率才丢人**（Lead 定，见 8.2）。

## 8. 第二阶段（补全/升级 probs）

第二阶段有**三条线**，目标人群不同（详见 8.3）：

- **A. mercury-decide 升级 noul（7,907 条）**：这些 target 原本有 probs，但 3,668 条是伪 one-hot、1,656 条是均匀分布（无信息）——用决策端点的原生 P(yes) 换成真分布。
- **B. mercury-decide 补 answer-only choice**：新增的 51,057 条没有 probs 的 choice target，用 choice 端点补（返回完整概率分布，见附录 B）。
- **C. jev-router 补 zh choice**：旧方案，已付费的 841 条保留（语义标记 `jev_router`）。

三条线写入旁挂文件 `data/jev-probs.jsonl` 的**共同**硬条件：

1. 解析成功，且**恰好命中一个选项**（argmax 明确）；
2. **argmax == 语料已有的 answer**（契约硬约束，违反一律不写）；
3. 概率归一（和为 1）；
4. **非退化**：伪 one-hot 与均匀分布都不写（宁可少补也不塞假概率）。

任一条不满足则该 target 不写入旁挂文件、并计入 8.3 的拒绝统计。**冻结语料在任何情况下都不修改。**

**方案选择**：方案 A（单选项提示词 → one-hot）已被否掉——one-hot 的信息量等于 answer 本身，属契约 2.3 的“伪 one-hot”；改为**方案 B（分布提示词）**，100 条配对探针结果见**附录 A**，它同时暴露了 42%% 输出仍是退化 one-hot，因此最终改用 **mercury 决策端点**（原生概率，见附录 B）。

### 8.1 旧方案的收益/成本外推（jev-router，已被 mercury 方案取代）

第一阶段里 **answer-only 子集（正是第二阶段要补的人群）一致率 = 74/74 = 100.0% [95%CI 95.1%–100.0%]**。但该子集的 74 条**全部是 `zh|decision_mechanics|choice`**，第二阶段剩下的 545 条 `en|score` 在本次抽样里没有落进 answer-only 子集，只能用同 kind 的 score 实测值外推。分块外推如下：

| 第二阶段子集 | 条数 | 第一阶段实测一致率 | 预计可写入（95%CI 外推） |
|---|---|---|---|
| zh|decision_mechanics|choice | 7,872 | 74/74 = 100.0% [95%CI 95.1%–100.0%] | 7,484–7,872 |
| en score（两个 domain 合计） | 545 | 17/29 = 58.6% [95%CI 40.7%–74.5%] | 222–406 |
| 合计 | 8,417 | — | 7,706–8,278 |

结论：`zh choice` 这一块几乎肯定能写满；`en score` 的 545 条证据很弱（score 只有 17/29 = 58.6% [95%CI 40.7%–74.5%]），可能大量保持 answer_only。

成本外推（**两个口径都要看**）：账户侧口径单次 $0.000616 → 跑满 8,417 条约 **$5.18，超过第二阶段的 $5 上限**；脚本逐条口径单次 $0.000587 → 约 $4.94，恰好贴线。所以第二阶段要么把上限提到 $8 左右，要么接受在 $5 处提前停止（按均值口径约能跑 8,118 条 ≈ 全部 zh choice）。最坏情况（全部路由到最贵的上游，均价 $0.005510/次）约 $46.4，因此必须按 0.1 节的**自适应预算**执行：超限即停、已完成调用不丢、可续跑。

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

### 8.2 旧方案（jev-router）曾需要的条件（清单，已大部分作废）

> **备注**：下面这张清单是为 jev-router 方案写的。该方案已被 mercury-decide 取代（决策专用端点、原生概率、成本约 $0.01/7,907 条），因此 1–3 条不再构成阻塞；保留此表是为了记录当时的判断依据与 gate 状态。

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

落到交付文件的完整命令（可复算）：

```sh
# 1) mercury-decide 全量补 noul（限速 2.5/s，可断点续跑；跑完自动导出）
uv run --no-project --offline python datasets/general/jev_fill.py noul-fill --rate 2.5 --workers 4

# 2) 合并两条线 -> 交付文件（按 distribution_semantics 区分）
uv run --no-project --offline python datasets/general/jev_fill.py probs-assemble \
    --source datasets/general/data/jev/jev-router-partial-probs.jsonl \
    --source datasets/general/data/jev/mercury-noul-probs.jsonl \
    --out datasets/general/data/jev-probs.jsonl

# 3) 校验（不给 --plan 时直接对冻结语料：argmax/归一/非退化/语义标记/corpus_shape）
uv run --no-project --offline python datasets/general/jev_fill.py verify --out datasets/general/data/jev-probs.jsonl
```

### 8.3 第二阶段执行结果（三个来源，分开报）

第二阶段实际有**三条线**，语义/人群都不同，**绝不合并成一个“补了 N 条”的数字**：

- **A. mercury-decide 升级 noul（7,907 条）**：这些 target 原本就有 probs 但多数不可用——伪 one-hot 3,668 条、均匀分布（无信息）1,656 条、来源真分布（real）2,583 条。用 mercury 的原生 P(yes) 换成真分布；旁挂行带 `corpus_shape` 字段，消费方对 real 的条目可以选择保留来源分布。
- **B. mercury-decide 补 answer-only choice（51,057 条）**：语料里没有 probs 的 choice target；用 choice 端点补（返回完整概率分布），**尚未跑完**，见 8.3 覆盖范围。
- **C. jev-router 补 zh choice（answer-only）**：旧方案，被 mercury 取代；**已付费的 841 条保留**，语义标记 `jev_router`。

| 来源 | distribution_semantics | 目标数 | 成功响应 | 写入旁挂 | 被门禁拒绝（主因） | 成本 |
|---|---|---|---|---|---|---|
| A. mercury-decide noul | `mercury_decide_native` | 7,907 | 7,907 | **6,524** | `answer_mismatch 1,323、degenerate:uniform 60` | $0.0472 |
| C. jev-router zh choice | `jev_router` | 7,872 | 1,883 | **841** | `not_called_or_failed 5,989、degenerate:one_hot 1,026、answer_mismatch 16` | $0.5843 |
| B. mercury-decide choice | `mercury_decide_native` | 51,057 | 51,057 | **41,138** | `answer_mismatch 9,862、degenerate:uniform 57` | $0.3538 |

**护栏在起作用，这不是失败**：被门禁拒绝的条目**宁可少补也不塞假概率**。jev-router 那条线里 1,026 条因为输出是退化 one-hot（伪概率）被拒——这正是契约 2.3 诊断出的问题，被门禁拦下来而不是写进旁挂文件；另有 16 条 argmax 与语料 answer 不一致被拒（硬约束，绝不写）。

**覆盖范围提醒**：当前语料 answer-only 共 59,474 条（choice 58,929 / score 545）。
- **已尝试** 52,940 条（mercury choice 51,057 + jev-router 1,883）→ 写入 41,979 条，其余 10,961 条因 argmax 与语料不一致 / 输出退化被拒、**保持硬标签**；
- **未尝试** 6,534 条：旧语料 zh choice 约 5,989 条（jev-router 线中断后，mercury 线按设计只跑新增的 51,057 条）+ score 545 条（criteria 格式不同，本轮未补）。

mercury choice 线本身**已跑完全部 51,057 条**，不再受额度限制。

旁挂交付文件：`datasets/general/data/jev-probs.jsonl`；每行都带 `distribution_semantics` / `upstream_model` / `created_at` / `corpus_shape`（mercury 线）与 `answer`（门禁依据）。**冻结语料未修改。**

### 8.4 补全后语料的真值形态构成（给训练方）

| 形态 | 语料原本 | 采用旁挂 probs 后 |
|---|---|---|
| 原生软分布（来源自己给的） | 7,520 | 5,421 |
| 伪 one-hot（硬标签单点分布） | 14,119 | 10,658 |
| 均匀分布（无信息） | 1,730 | 766 |
| 仅硬标签：**还没尝试补全** | 59,474 | 6,534 |
| 仅硬标签：**尝试过但与我们不一致**（被门禁拒绝、保持原样） | 0 | 10,961 |
| 新补：mercury noul 原生概率（升级伪 one-hot / 均匀） | 0 | 6,524 |
| 新补：mercury choice + jev-router 分布（**只在一致时写入，有选择偏差**） | 0 | 41,979 |
| 合计 | 82,843 | 82,843 |

读法：`采用旁挂后` 列假设消费方**优先使用旁挂 probs、没有旁挂的沿用语料**；所有条目在旁挂文件里按 `distribution_semantics` + `corpus_shape` 可区分。

**两个「仅硬标签」不要混为一谈**：前者是**还没尝试补**，后者是**补了但 mercury 与我们分歧、按门禁不写**——训练价值不同，所以单列。

**交付面（保密约束）**：发布的旁挂件只保留**公开面** 44,740 条（本地全量 48,503 条，剔除 3,763 条 benchmark / 私有保留集成员）。原因：sidecar 的 `id` 列等于一份**成员名单**，含 benchmark 成员的入库件会踩保密护栏（`test_split.SecrecyTest.test_tracked_files_contain_no_benchmark_records`）。本地全量保留在 `data/jev/jev-probs.full.jsonl`（gitignore），供内部审计。

**换个口径看训练价值**（README §4.4 口径：分母 = 公开件 74,853 + 补充集 3,148 = 78,001；「真概率分布」= shape_class ∈ {soft, tie_subset}）：

- 补全前：**5,945 条 = 7.62%**（v4 语料时为 7.61%；这里按 v5 公开面重算）
- 采用旁挂 probs 后：**48,941 条 = 62.74%**（**+55.12 pp**）
- 新增可用软分布 42,996 条（jev_router 841；mercury_decide_native 42,155）；1,744 条本来就是来源真分布（不重复计）。

### 8.5 一致性偏差与分歧分层（训练方必读）

#### 8.5.1 选择偏差：软分布子集是「一致子集」，不是随机子集

写入门禁要求 `argmax == 语料 answer`，因此**写进旁挂的 answer-only 样本 = mercury 与语料一致的子集**。实测：

| 来源 | 已调用 | 写入 | 写入率 | 被拒（不一致/退化） |
|---|---|---|---|---|
| mercury choice | 51,057 | 41,138 | 80.6% | 9,919 |
| jev-router zh choice | 1,883 | 841 | 44.7% | 1,042 |
| 合计 | 52,940 | 41,979 | 79.3% | 10,961 |

**后果（训练方必须知道）**：这 41,979 条软分布系统性偏向**双方共识题/简单题**；分歧的 10,961 条恰恰可能是边界样本、有争议样本。**不要把它当随机子集**，也不要因为“有了软分布”就认为该人群质量更高——它只是“双方意见一致”的那部分。

#### 8.5.2 criteria 模板会不会泄漏答案？对照实验：**不泄漏**

| 变体 | criteria 模板 | argmax == 语料 answer | 平均最大概率 |
|---|---|---|---|
| T1_current | `the correct answer is %s` | 24/30 = 80.0% | 0.910 |
| N1_neutral | `the state supports %s` | 25/30 = 83.3% | 0.897 |
| N2_neutral | `%s follows from the provided information` | 24/30 = 80.0% | 0.893 |
| N3_neutral | `%s is consistent with the state` | 25/30 = 83.3% | 0.909 |

同一批 30 个 qid、四种模板的 argmax 一致性（相对当前模板 T1）：N1_neutral 28/30 = 93.3%；N2_neutral 30/30 = 100.0%；N3_neutral 29/30 = 96.7%。

**结论**：换成中性判据后一致率**没有下降**（反而略升），argmax 跨模板一致性 93–100%，平均最大概率基本不变——说明判断由 state/instructions 驱动，**不是被 criteria 措辞带偏**；模板不构成答案泄漏，已写入的 41,138 条统计没有被这个模板抬高。

#### 8.5.3 分歧分层：哪些 config 的不一致高

下表按一致率升序（只统计已调用的 choice 条目）。**一致率低于 70% 的 config 值得单独复核标签**；高于 95% 的可视为双方相互印证。

| source question key | 已调用 | 一致 | 一致率 | label_confidence |
|---|---|---|---|---|
| `intersect_geometry` | 1565 | 315 | 20.1% | `low_consensus` |
| `tracking_shuffled_objects` | 1565 | 760 | 48.6% | `low_consensus` |
| `mathematical_induction` | 53 | 34 | 64.2% | `low_consensus` |
| `presuppositions_as_nli` | 588 | 379 | 64.5% | `low_consensus` |
| `symbol_interpretation` | 795 | 539 | 67.8% | `low_consensus` |
| `logic_grid_puzzle` | 800 | 560 | 70.0% | `medium_consensus` |
| `winowhy` | 1565 | 1132 | 72.3% | `medium_consensus` |
| `crash_blossom` | 22 | 16 | 72.7% | `medium_consensus` |
| `elementary_math_qa` | 1565 | 1179 | 75.3% | `medium_consensus` |
| `riddle_sense` | 33 | 25 | 75.8% | `medium_consensus` |
| `disambiguation_qa` | 207 | 164 | 79.2% | `medium_consensus` |
| `implicit_relations` | 68 | 54 | 79.4% | `medium_consensus` |
| `analytic_entailment` | 54 | 43 | 79.6% | `medium_consensus` |
| `cs_algorithms` | 1056 | 850 | 80.5% | `medium_consensus` |
| `question` | 25262 | 20494 | 81.1% | `medium_consensus` |
| `evaluating_information_essentiality` | 52 | 44 | 84.6% | `medium_consensus` |
| `epistemic_reasoning` | 1565 | 1330 | 85.0% | `medium_consensus` |
| `navigate` | 800 | 697 | 87.1% | `medium_consensus` |
| `date_understanding` | 296 | 259 | 87.5% | `medium_consensus` |
| `snarks` | 145 | 127 | 87.6% | `medium_consensus` |
| `formal_fallacies_syllogisms_negation` | 1565 | 1373 | 87.7% | `medium_consensus` |
| `logical_deduction` | 1200 | 1056 | 88.0% | `medium_consensus` |
| `sentence_ambiguity` | 44 | 39 | 88.6% | `medium_consensus` |
| `vitaminc_fact_verification` | 1565 | 1405 | 89.8% | `medium_consensus` |
| `unit_conversion` | 1565 | 1435 | 91.7% | `medium_consensus` |
| `understanding_fables` | 152 | 140 | 92.1% | `medium_consensus` |
| `checkmate_in_one` | 1565 | 1468 | 93.8% | `medium_consensus` |
| `entailed_polarity` | 119 | 114 | 95.8% | `high_consensus` |
| `known_unknowns` | 30 | 29 | 96.7% | `high_consensus` |
| `logical_fallacy_detection` | 1565 | 1534 | 98.0% | `high_consensus` |
| `arithmetic` | 1565 | 1536 | 98.1% | `high_consensus` |
| `question_selection` | 1266 | 1243 | 98.2% | `high_consensus` |
| `temporal_sequences` | 800 | 798 | 99.8% | `high_consensus` |

**一致率 < 70% 且样本 ≥ 10 的 config（标 `low_consensus`）**：`intersect_geometry` 315/1565 = 20.1%；`tracking_shuffled_objects` 760/1565 = 48.6%；`mathematical_induction` 34/53 = 64.2%；`presuppositions_as_nli` 379/588 = 64.5%；`symbol_interpretation` 539/795 = 67.8%。这些是**关于该来源标签质量的信号**：要么 mercury 不擅长这类题（几何/多步追踪），要么语料标签本身有噪声——现有证据不足以区分，但**该子集的标签未经双方互证**。

**label_confidence 标记方案（已写进旁挂）**：

- `high_consensus`：双方一致率 ≥ 95%；`medium_consensus`：70%–95%；`low_consensus`：< 70%（n ≥ 10）；`insufficient_sample`：n < 10 不下结论。
- 每条 choice 旁挂行都带 `label_confidence` / `consensus_agree` / `consensus_n`；机器可读总表在 `data/jev/label-confidence.json`。
- 旁挂 choice 行按标记的分布：`high_consensus` 7,587；`low_consensus` 2,026；`medium_consensus` 38,890。

**语义**：`label_confidence` 衡量「我们与该子集的 mercury 判断是否互相印证」，**不是「标签对错」**。`low_consensus` = 该子集标签未经双方互证，训练时应降权或标记复核，**不要和 high_consensus 同等对待**。（这是给训练方的路由信号，不是把标签判死。）

#### 8.5.4 另一条线的互证率：noul 按来源 dataset

| source dataset | 已调用 | 一致 | 一致率 | label_confidence |
|---|---|---|---|---|
| `SargeDev/jev-distill-corpus-v3` | 4053 | 2943 | 72.6% | `medium_consensus` |
| `kaivoss/system-one-270m-data` | 489 | 436 | 89.2% | `medium_consensus` |
| `tasksource/procedural-typed-decisions` | 1872 | 1692 | 90.4% | `medium_consensus` |
| `ZefanCai/Open-Jev` | 1493 | 1492 | 99.9% | `high_consensus` |

noul 线没有 `low_consensus` 子集：最差的来源仍高于 70% 门槛。注意 noul 的互证率整体低于 choice 的头部 config——这与第一阶段 noul 在部分分层「等于随机」的发现一致，训练时应结合 `label_confidence` 一起看。

**jev-router 线（Deepexi/openai-formate-function-calling-small）**：argmax 与语料一致率 **99.2%**（1867/1883）→ `high_consensus`。**重要区分**：它的写入率只有 44.7%，但被拒的 1,026 条里绝大多数是**输出退化成伪 one-hot**（判断其实与语料一致）——所以这条线的问题在**分布质量**，**不在标注一致性**。`label_confidence` 衡量的是后者，故它是 high；选分布做训练时仍要按 8.3 的写入门禁走。

## 9. 产物

| 路径 | 内容 |
|---|---|
| `datasets/general/jev_fill.py` | 本报告的生成脚本（抽样/调用/解析/报告/校验） |
| `datasets/general/jev-validation.md` | 本文件 |
| `datasets/general/data/jev/validation-plan.jsonl` | 抽样清单（manifest + 300 条，含分层与真值） |
| `datasets/general/data/jev/validation-calls.jsonl` | 逐次尝试的原始响应与成本（可续跑） |
| `datasets/general/data/jev/mercury-noul-fill.jsonl` | mercury-decide noul 逐次调用 journal（可续跑） |
| `datasets/general/data/jev/mercury-noul-probs.jsonl` | mercury 线写出的 noul 原生概率 |
| `datasets/general/data/jev/jev-router-partial-probs.jsonl` | jev-router 线已付费的 zh choice 分布 |
| `datasets/general/data/jev/mercury-choice-fill.jsonl` | mercury choice 线逐次调用 journal（可续跑） |
| `datasets/general/data/jev/mercury-choice-probs.jsonl` | mercury choice 线写出的 answer-only 分布 |
| `datasets/general/data/jev/fill-plan-dist-zh-choice.jsonl` | jev-router 线请求清单（7,872 条 zh choice） |
| `datasets/general/data/jev/fill-calls-dist.jsonl` | jev-router 线逐次调用 journal |
| `datasets/general/data/jev-probs.jsonl` | **交付文件**：三位一体合并后的旁挂概率（按 distribution_semantics 区分） |
| `datasets/general/data/jev-probs.jsonl.gz` | **公开面**交付件的确定性压缩版（44,740 行；HF 公开仓库托管，见 [HF.md](HF.md)；明文不入库） |
| `datasets/general/data/jev/jev-probs.full.jsonl` | 本地全量旁挂件（48,503 行，含 benchmark/保留集成员，gitignore、不入库） |
| `datasets/general/data/jev/label-confidence.json` | 两条线合并的 label_confidence 总表（按 source/ config） |

冻结语料只读：`items.final.jsonl` 与 `data/splits/` 四区文件在本任务中未被写入。


## 附. 保密经验（写报告必须遵守）

本报告**不含任何完整 item id**：所有条目一律用「样本 #N（id 从略）」匿名索引；生成脚本在写盘前会拿语料里的全部 item id 做全文断言，**命中任一 id 就直接失败退出、不生成文件**。

为什么：**成员身份本身是敏感信息**。只要指出哪些 id 属于 benchmark，配合仍在 git 历史里的语料就能精确还原评测集，因此报告/日志/测试夹具里永远不写完整 item id。

踩坑记录（团队内第三次同类问题）：

1. 本报告第一版在分歧样例表里写了完整 qid；
2. Lead 手工匿名后，我重跑了一次报告生成器，**id 又被带回来了**——教训是**匿名化必须做在生成器里，不能只手改产物**；
3. db-adopt 也在报告里引用过 benchmark id，自查后打码。

现在的做法：匿名映射写进 `report` 子命令（`anon_labels()`），并加 `assert_no_item_ids()` 作为写盘前的硬门禁。
