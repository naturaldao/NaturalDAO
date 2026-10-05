# 中文侧构建报告：Deepexi 去重、统计筛选与变体利用（task-18）

- 日期：2026-10-05（UTC+8）｜执行：pol2-replay（DSH Agent Team）
- 口径：**按唯一请求计**；允许用变体增强；中文 30–40% 均可，**质量优先**（Lead task-18 与后续硬要求）
- 来源：`Deepexi/openai-formate-function-calling-small`（主）与 `Deepexi/function-calling-small`（对照）
- 产物：仓库内 `data/zh/zh-group-index.jsonl`（分组索引）与 `data/zh/zh-items.sample.jsonl`（200 条样例）；
  全量条目在仓库外 `D:\pol2-raw\zh-final\items.zh.jsonl`（**最终合并不由本任务做**）

## 0. 结论摘要

| 项目 | 数值 |
|---|---:|
| 原始行数（v3） | 24,608 |
| 筛选后保留行数 = 条目数 | **22,372**（剔除 2,236 行，**9.09%**） |
| **唯一请求数 = 组数** | **5,454** |
| 变体总数（可训练条目） | 22,372 |
| 平均变体/请求 | 4.10（4 套占 97.71%） |
| 契约校验 `taxonomy.item_errors` | **0** |
| v2/v3 一致性 | 24,608/24,608 行 (request,target) **完全相同** |
| 位置偏置（筛选后，打散前） | 合并 χ²=6,669（df=4，p≈0）；**最后一位几乎从不是答案**（3 候选时仅 5/5,605） |
| 打散后位置检验 | 分层 χ²=16.58（df=15，**p=0.345**）→ 位置均匀 |
| 捷径检测 | 706 个函数中 **0 个**满足 P(被选中\|出现在菜单)≥0.9；最高仅 0.495 |
| 目标函数分布 | 706 个，熵 9.34 bit，Top-10 占 4.0%，无单例函数 |
| 请求长度 | 最短 8，中位 23，p90 41，最长 319 字 |
| 中文占比（英文侧 15,915） | 每请求取 1 套 = 25.5%；取 2 套 = 40.7%；全取 22,372 = 58.4% |

## 1. 数据与 manifest

固定 revision 直接 `resolve` 下载，字节数与 HF tree 完全一致（可复算）：

| 文件 | dataset | revision | bytes | sha256 |
|---|---|---|---:|---|
| `D:\pol2-raw\deepexi\v3.csv`（主） | `Deepexi/openai-formate-function-calling-small` | `6d1dc02a2549104cc9cd2828c4b8647e9f994341` | 120,038,302 | `4865ac94e27e02e67a3578f04ced85586fc41df0145cdc517b664275931946a0` |
| `D:\pol2-raw\deepexi\v2.csv`（对照） | `Deepexi/function-calling-small` | `8fba7ee941523e7da69f4ff882b52e5566d24288` | 111,809,738 | `36f45fc4abd8cf29637eec7d1fc0f4083913d207f76a62633d6a526ce1d411ac` |

**v2 与 v3 是同一批数据的两种函数 schema**（legacy `arguments` vs OpenAI `parameters`）：
24,608 行的 (request, target) 逐行比对 **完全相同**（same_ratio = 1.000000），异常行数也相同
（不可解析 416、答案不在候选 191）。因此**只按一个来源计**；本轮以 v3（apache-2.0）为准，
v2（cc-by-4.0）作为等价性证据保留。

许可链说明（与 task-17 报告一致）：Deepexi 声明 apache-2.0 / cc-by-4.0；内容取材自阿里云公开 OpenAPI 中文文档，
入库需保留 Deepexi 署名并注明来源，阿里云条款另行核对。

## 2. 按请求分组重建

- 分组键：归一化后的 `userPrompt`（压缩空白、去首尾引号）→ `group_id = zhgrp-<sha256(request)[:12]>`。
- **同一请求的 4 套候选集共享同一 group_id**（见第 8 节的切分说明）。
- 组内去重：同一菜单只留一行（实测 0 行）；同一菜单不同答案记矛盾（实测 0 行）。
- 变体数分布：

| 变体/请求 | 组数 | 占比 |
|---:|---:|---:|
| 4 | 5,329 | 97.71% |
| 8 | 114 | 2.09% |
| 12 | 9 | 0.165% |
| 16 | 1 | 0.018% |
| 20 | 1 | 0.018% |
| **合计** | **5,454** | 100% |

真实样例（同一请求、4 套候选集；state 逐字相同，答案都是 `ListMessages`）：

```json
{"group_id": "zhgrp-104f0514ee19", "state": "20210101的钉钉发送状态如何？",
 "variants": [
   {"row": 15830, "menu": ["ListMessages", "UpdateDISyncTask", "GenerateDISyncTaskConfigForCreating"], "target": "ListMessages"},
   {"row": 15831, "menu": ["CreateMetaCategory", "ListDataServiceApis", "ConfigureDtsJob", "ListMessages"], "target": "ListMessages"},
   {"row": 15832, "menu": ["RevokeTablePermission", "ListMessages", "GetSchedule", "UpdateDeployment", "ListFunctions"], "target": "ListMessages"},
   {"row": 15833, "menu": ["UpdateMetaCollection", "CreateProjectMember", "DeleteQuotaPlan", "UpdateUserTagValue", "GetTrustedProjects", "ListMessages"], "target": "ListMessages"}]}
```

（上例中答案在原始菜单里的位置分别是 0、3、1、5 —— 这正是下面第 4 节要处理的偏置。）

## 3. 统计筛选：规则、数量、理由

| 规则 | 剔除行数 | 占比 | 理由 |
|---|---:|---:|---|
| `target_name_in_state` | **1,509** | 6.13% | 答案函数名直接出现在请求文本里（如 state 以 `BatchGetTables` 开头）→ 输入即答案的捷径 |
| `unparsable_response` | 416 | 1.69% | CSV 内嵌换行把 JSON 拆断；按既定口径「解析失败即丢弃」，不猜 |
| `target_not_in_candidates` | 191 | 0.78% | 选中函数不在该行候选集里（已核对：不是解析丢失，是原始数据如此） |
| `request_too_short` | 100 | 0.41% | 请求 < 8 字（多为 `"xxx"` 这类退化片段） |
| `request_concat_artifact` | 20 | 0.08% | 两行请求被拼进同一条（含 `"} {"`），语义不完整 |
| **合计** | **2,236** | **9.09%** | 24,608 → **22,372** |

组级：**没有整组被剔除**（每个请求至少 1 套可用候选集），但请求数从 5,849（仅行级清洗时）
降到 **5,454**，即 **395 个请求的 4 套变体全部命中上面的规则**（主要是整组答案泄漏）。

被剔掉的一类真实样例（answer-in-state）：

```json
{"state": "BatchGetTables我想查询某个数据库和元数据表的详细信息", "target": "BatchGetTables", "menu_size": 3}
```

**这是本轮最重要的一条质量结论**：如果只做「解析失败 + 答案不在候选」两项清洗，会有 6.13% 的样本
把答案写在输入里，模型学到的是"照着念"而不是"从候选里选"。

## 4. 位置偏置检测（含打散处理）

筛选后的 22,372 行，正确答案在候选集中的位置分布：

| 菜单大小 | 位置 0 | 1 | 2 | 3 | 4 | 5 | 卡方 |
|---:|---:|---:|---:|---:|---:|---:|---|
| 3（5,605 行） | 2,794 | 2,806 | **5** | — | — | — | χ²=2,787.6, df=2, p≈0 |
| 4（5,601 行） | 1,883 | 1,888 | 1,823 | **7** | — | — | χ²=1,850.2, df=3, p≈0 |
| 5（5,594 行） | 1,476 | 1,320 | 1,424 | 1,371 | **3** | — | χ²=1,403.1, df=4, p≈0 |
| 6（5,551 行） | 1,086 | 1,107 | 1,092 | 1,155 | 1,111 | **0** | χ²=1,113.4, df=5, p≈0 |
| 合并 | 7,258 | 7,123 | 4,344 | 2,533 | 1,114 | — | χ²=6,669.5, df=4, p≈0 |

**结论：存在明确的结构性偏置——最后一位几乎从不是答案**（3/4/5/6 候选时分别是 5、7、3、0 次）。
前 n−1 位则大致均匀。若按行直接进训练，模型可以靠"不选最后一个"白拿一部分正确率，
并且会把这个伪影带到真实场景（真实场景里最后一位一样可能是对的）。

**处理：确定性打散候选顺序**（`shuffle_options`，seed=`deepexi-zh-option-shuffle-v1`，
顺序 = `sha256(seed + item_id + 函数名)`；**只改顺序，不改答案**——答案按函数名匹配）。
打散后按菜单大小分层的卡方检验：

| 菜单大小 | 打散后位置分布 | 卡方 |
|---:|---|---|
| 3 | 1,918 / 1,806 / 1,881 | χ²=6.06, df=2 |
| 4 | 1,406 / 1,391 / 1,385 / 1,419 | χ²=0.52, df=3 |
| 5 | 1,151 / 1,078 / 1,160 / 1,126 / 1,079 | χ²=4.14, df=4 |
| 6 | 922 / 938 / 899 / 897 / 905 / 990 | χ²=5.86, df=5 |
| **分层合并** | — | **χ²=16.58, df=15, p=0.345** |

p=0.345 → 位置分布与均匀分布无显著差异，伪影消除。原始位置记在每条 item 的
`meta.original_target_position`，打散标记 `meta.option_order="shuffled_v1"`，可复算、可回退。

## 5. 目标函数的区分度（有没有"菜单里一出现就是答案"的函数）

对 706 个出现 ≥50 次的函数，计算 P(被选中 | 出现在候选集)：

- 分布：0.0–0.1 桶 114 个、0.1–0.2 桶 320 个、0.2–0.3 桶 265 个、0.3–0.4 桶 4 个、0.4–0.5 桶 3 个、0.5+ 桶 3 个
- **最大 0.4952，最小 0.0290，没有任何函数的选择率 ≥0.9**（`functions_with_rate_ge_0.9 = 0`），
  `rows_with_high_prior_function = 0`
- 解读：**没有"捷径函数"**。答案不能靠"菜单里出现了 X"来猜，必须读请求——这是这份数据最值钱的统计性质，
  也说明它适合做 decision_mechanics 的监督，而不是当"候选集模式匹配"训练。

## 6. 多样性与长尾

- 请求：5,454 条唯一请求；按"数字/引号内容掩码"后的骨架计 5,411 条 → **多样性强，不是同一句话换参数**。
  仅 18 个骨架承载 ≥10 条请求，最大 32 条（退化骨架 `{"X"}`，已被 `request_too_short` 规则清掉大部分）。
- 请求长度：中位 23 字、p90 41 字 —— 短请求居多，符合"函数选择"的形态。
- 目标函数：706 个，熵 9.34 bit（最大 log2(706)=9.46），Top-10 只占 4.0%，**没有长尾塌陷**（无单例函数）。
- 菜单大小分布几乎均匀（3/4/5/6 各约 5,600 行，2 个候选仅 21 行）→ 每个请求的 4 套变体覆盖了不同规模，
  本身就是"难度增强"。

## 7. 变体利用与中文占比（给 Lead 的算数）

英文侧按 15,915 条计：30% 门槛需要 **6,822** 条中文；40% 上限需要 **10,610** 条；超过 40% 就撞 README §4 的
"单一来源 ≤40%"（本数据只有这一个来源）。

| 取法 | 中文条目 | 合并后中文占比 |
|---|---:|---:|
| 每请求 1 套 | 5,454 | **25.5%**（低于 30% 门槛） |
| 每请求 2 套 | 10,908 | **40.7%**（略超 40%） |
| 全部 22,372 条 | 22,372 | **58.4%**（超 40% 上限，不建议） |
| 建议：取到 30–40% 区间 | **6,822 – 10,610** | 30% – 40% |

即"每请求取 1.25 – 1.95 套"是达标的取数区间。取法建议：**组内按 `variant_index` 升序取前 k 套**
（k=1 或 2），确定性、可复算；**同一请求被取中的变体必须整组进同一分区**。
本轮不做最终配比（合并由 db-hf 的任务做），只给出可选项与算数。

## 8. 契约映射与切分接口

> **修订（task-21 复核后）**：新增 `questions[].origin="source"` 与 `source_key="function"`（见下），
> 并要求用 `--created-at` 构建以保证逐字节可复现。当前全量文件
> `D:\pol2-raw\zh-final\items.zh.jsonl`：22,372 条、139,611,239 B、
> sha256 `44c9084be08a3453929a0c97ae947b90e619494f46b7d07e7e3ae1a8c133a21d`，
> 构建命令 `python build_zh.py --build --created-at 2026-10-05T19:10:00+08:00`（同参数重跑两次哈希一致）。

每条 item 的形状（`taxonomy.item_errors` = 0，22,372/22,372）：

- `domain = "decision_mechanics"`，`lang = "zh"`（同组同域同语言，满足切分方的分层要求）
- `state` = **用户请求文本本身**（不含候选集，不写结论）；实测 **5,454/5,454 组的 state 逐字相同**
- `questions[0]` = `next_step_candidate`（choice，`options_from_state=True`），
  `options` = 该行的候选函数（`{key: 函数名, label: "函数名：中文描述(≤120字)"}`），2–6 个，已打散
- **`questions[0].origin = "source"`**（契约 [CONTRACT.md](CONTRACT.md) §2.1 的位置，**必须显式写**：
  缺省即视为 `taxonomy`，会把这批原生四元组误读成我们出题的降级数据）+ `questions[0].source_key = "function"`
  （来源自身的答案字段名）；条目顶层 `origin="source"` 与 `meta.origin/question_origin/source_question_key` 同时保留。
  实测 `questions[].origin` = **source 22,372 / taxonomy 0 / None 0**
- `targets.next_step_candidate.answer` = 被选中的函数名（与 options 的 key 对应）
- `meta.source_record.candidates` = 完整函数定义（name/description/raw，raw 截断 2,000 字）
- 函数参数（arguments/parameters）本契约无对应键，按"不硬塞"只进 meta

**切分接口（回应 db-schema / task-20）**：每条 item 在 **四个位置**都写了分组键，任一优先级都能命中：

```json
{"id": "db-deepexi-fcs-v3-xxxxxxxx", "group_id": "zhgrp-xxxxxxxxxxxx", "request_id": "zhgrp-xxxxxxxxxxxx",
 "source": {"...": "...", "group_id": "zhgrp-xxxxxxxxxxxx"},
 "meta": {"group_id": "zhgrp-xxxxxxxxxxxx", "request_id": "zhgrp-xxxxxxxxxxxx", "variant_index": 0, "n_variants": 4}}
```

- 同组变体共享 group_id；**state 也逐字相同**（双保险：即使分组键解析失败，按归一化 state 合并也不会拆散）。
- 预期切分方报告：多条目组数 = **5,454**、最大组条数 = **20**。若多条目组数为 0，说明分组键没被读到。

### 8.1 原生程度披露：哪些是来源原文、哪些是我们写的

这批 **`origin="source"`**，但它是**混合来源**的，必须按字段拆开说清楚，读者才不会被"source"这个词误导：

| 字段 | 谁写的 | 说明 |
|---|---|---|
| `state` | **来源原文** | Deepexi 的 `userPrompt`，一字未改（只做空白归一化用于分组） |
| `questions[0].options` | **来源原文** | 候选函数集来自该行 `systemPrompt` 的函数定义，键即函数名，标签只做了"函数名：中文描述(≤120字)"的截断 |
| `targets.next_step_candidate.answer` | **来源原文** | 该行 `assistantResponse` 里被选中的函数名 |
| `questions[0].prompt` | **我们写的** | "以下候选中，哪一个是正确的下一步？"——taxonomy 的固定句式 |
| `questions[0].key` | **我们写的** | 规范键名 `next_step_candidate` |
| `questions[0].source_key` | 记录来源事实 | `"function"`，即来源自身答案字段名 |

**`key` 与 `source_key` 不同是有意为之，不是遗漏**：`key` 用规范名是为了保住"这是同一类决策（从封闭候选里选一个）"的归一性，
使中文函数选择与其它 choice 键在同一张词表下可统计；`source_key="function"` 负责溯源到来源的原生字段。
（Lead 裁定：契约的 `origin` 回答的是"这道题在**决定什么**"，而不是"这句话谁写的"——候选与答案完全来自来源、
句式只是把来源本来就有的结构读出来、无编辑裁量，故维持 `origin="source"`。）

**因此这批的原生程度低于英文侧**：英文 6 个来源自带 `question` 字段（问题本身就是数据的一部分），
中文 Deepexi 只有"候选集 + 答案"这个结构，提问句式由我们补齐。做"只用 100% 原生四元组"的分析时，
应按 `questions[].source_key` 是否存在、或按数据卡声明来区分，而不是只看 `origin`。

（对应的契约补充由 Lead 在 [CONTRACT.md](CONTRACT.md) 落地：`origin=source` 时 `key` 可用规范名，
但 `source_key` 必须记录来源原生字段名，且问题措辞由谁写要在数据卡里声明。）

## 9. 产物清单与复现

仓库内（本任务写入）：

| 路径 | 内容 |
|---|---|
| `datasets/general/zh-build-report.md` | 本报告 |
| `datasets/general/data/zh/zh-group-index.jsonl` | 5,454 行分组索引：group_id / request / n_variants / targets / rows（1.36 MB） |
| `datasets/general/data/zh/zh-items.sample.jsonl` | 前 200 条条目样例，供切分方与 Lead 核对形状（1.24 MB） |

仓库外（全量，未提交）：

| 路径 | 内容 |
|---|---|
| `D:\pol2-raw\deepexi\v3.csv` / `v2.csv` | 原始下载（固定 revision，sha256 见 manifest） |
| `D:\pol2-raw\zh-final\items.zh.jsonl` | **全量 22,372 条条目**（契约形状，0 错误） |
| `D:\pol2-raw\zh-final\groups.jsonl` | 5,454 个组级结构（请求、菜单、答案、变体行号） |
| `D:\pol2-raw\zh-final\{manifest,stats,compare}.json` | 下载 manifest、全部统计量、v2/v3 对照 |
| `D:\pol2-raw\zh-final\build_zh.py` | 构建脚本（只用标准库） |

```powershell
# 全量重建（只读 HF，不调用付费 API；约 2 分钟）
uv run --no-project --offline python D:\pol2-raw\zh-final\build_zh.py --build
# 只看解析与异常计数
uv run --no-project --offline python D:\pol2-raw\zh-final\build_zh.py --probe
uv run --no-project --offline python tools/check.py
```

## 10. 未测项与风险

- **未做最终配比与合并**：本轮只产出中文侧条目与可选取数区间，合并/切分由 db-hf / db-schema 的任务完成。
- **许可链**：阿里云 OpenAPI 文档条款未逐条核对（Deepexi 声明 apache-2.0/cc-by-4.0）。
- **打散是按 item 独立做的**：同一组的 4 个变体顺序各自不同，符合"不同决策样本"的定位；
  若切分方需要组内顺序一致，可改用 group_id 作 seed（一行代码），本轮按 item 处理并在 meta 记了原位置。
- **答案泄漏只查了"函数名出现在 state"**：其它候选名或函数描述片段出现在 state 的情况未做硬过滤
  （属干扰项而非答案泄漏），如果训练后发现异常可再加规则。
- **3 个组跨变体出现 2 个不同答案**（占 0.055%）：菜单不同导致的最优选择不同，属正常，
  已通过 `groups.jsonl` 的 `n_distinct_targets` 暴露，未做处理。
