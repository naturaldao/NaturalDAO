# 中英双语决策底座（general bilingual v0.1）

- 生成日期：2026-10-02（UTC+8）
- 执行：pol2-replay（DSH Agent Team），共享任务 task-14
- 契约：[README.md](CONTRACT.md)；问题键：[taxonomy.py](taxonomy.py)；中文来源：[sources.zh.json](sources.zh.json) + [zh-survey.md](zh-survey.md)
- 英文来源：[sources.json](sources.json) + [data/convert-report.json](data/convert-report.json)；抓取/转换：[convert_zh.py](convert_zh.py)
- 产物：**`data/items.bilingual.jsonl`**（明文，已 gitignore）与 **`data/items.bilingual.jsonl.gz`**（入库）；
  机器可读报告 `data/items.bilingual.report.json`

## 0. 结论摘要

| 项目 | 数值 |
|---|---:|
| 合并后条目总数 | **54,594** |
| 英文 `lang="en"` | 37,124（**68.00%**，原样未改，顺序未变） |
| 中文 `lang="zh"` | 17,470（**32.00%**） |
| 中文占比目标 | ≥30%（本轮取 32%：30% 底线 + 2 个点余量，防止后续筛选把比例压到线下） |
| 中文全量池 | 42,436 条（12 个来源全量转换，0 错误）；入库抽样 17,470 条，其余留在仓库外池中 |
| id 跨语言碰撞 | 0（合并时硬校验；id 规则 `db-<slug>-<8hex>` 两侧一致） |
| 条目 schema 错误（`taxonomy.item_errors`） | **0** |
| 真值率（native target rate） | 英文 45.03% / 中文 **86.38%** |
| coverage.py 配额结论 | **通过**（0 个 violation，0 条 schema 警告） |
| 最大单一来源占比 | 14.21%（`SargeDev/jev-distill-corpus-v3`），上限 40% |
| 明文 / gz 体积 | 131,385,656 B / 16,287,199 B |
| 明文 sha256 | `ac24d42fdcf89102bf1adccad0fb985f87e77480e01f96fa53da42d594f70b68` |

**一句话：中英双语底座已生成，中文 32% 达标；但中文侧在 `decision_mechanics` 与
`knowledge_reasoning` 两个域是 0 条（第 7 节），这是真实缺口，不因整体占比达标而消失。**

## 1. 产物与复算

| 文件 | 说明 |
|---|---|
| `data/items.bilingual.jsonl` | 54,594 行；前 37,124 行是英文条目（原文件顺序、逐字节内容未改），其后是抽样后的中文条目（按 id 排序） |
| `data/items.bilingual.jsonl.gz` | 同一内容的 gzip（入库件）；明文由根目录 .gitignore 的 `*.items.jsonl` 与 `data/.gitignore` 双重忽略 |
| `data/items.bilingual.report.json` | 机器可读：语言/域分布、逐来源保留数、抽样参数、sha256 |

复算（不改任何数据，只读）：

```powershell
# 1) 全量抓取（12 个中文来源；HF 免费下载，无付费调用；已抓完则自动跳过，未完成的加 --resume）
uv run --no-project --offline python datasets/general/convert_zh.py fetch --all --raw-root D:\pol2-raw\zh

# 2) 转换（0 错误；产物在仓库外）
uv run --no-project --offline python datasets/general/convert_zh.py convert --all \
    --raw-root D:\pol2-raw\zh --out D:\pol2-raw\zh-items\items.zh.jsonl

# 3) 合并（英文原样 + 中文按域分层抽样；确定性，seed 固定）
uv run --no-project --offline python datasets/general/convert_zh.py merge \
    --zh D:\pol2-raw\zh-items\items.zh.jsonl --out datasets/general/data/items.bilingual.jsonl

# 4) 覆盖校验
uv run --no-project --offline python datasets/general/coverage.py \
    --items datasets/general/data/items.bilingual.jsonl --json-out <临时目录>\coverage.json
```

抓取阶段遇到过 datasets-server 的 HTTP 429 限流：12 个来源里有 3 个（`chinese-emotion-dialogue`、
`baidu-review-sentiment`、`toxic-zh`）中断过一次，用 `--resume` 从 manifest 游标续跑补齐，没有丢行、没有重复行。

## 2. 中文侧：全量池 → 分层抽样

中文全量转换结果（`convert_zh.py convert --all`，42,436 条、0 错误）：

| slug | 抓取行 | 条目 | 真值率 | 域 | 跳过 |
|---|---:|---:|---:|---|---|
| cvalues-rlhf | 18,000 | 17,966 | 1.00 | risk_harm | duplicate_state 34 |
| zhihu-preference | 3,460 | 2,420 | 0.00 | social_moral | duplicate_state 1,040 |
| chinese-emotion-dialogue | 4,159 | 4,154 | 0.87 | human_judgment | duplicate_state 5 |
| chinese-logic-sentiment | 2,176 | 2,176 | 1.00 | human_judgment | — |
| baidu-review-sentiment | 9,146 | 7,926 | 1.00 | human_judgment | duplicate_state 1,220 |
| toxic-zh | 5,000 | 5,000 | 1.00 | human_judgment | — |
| elder-scam-zh | 1,029 | **167** | 0.97 | risk_harm | not_chinese_row 166、duplicate_state 696 |
| med-guard（4 配置） | 1,040 | 1,040 | 1.00 | risk_harm | — |
| mh-risk-triage-zh | 1,598 | 1,587 | 0.71 | risk_harm | duplicate_state 11 |
| **合计** | **45,608** | **42,436** | **0.92** | 3 域 | — |

两个需要点名的损耗（都会影响后续配比，写在这里以免被当成"抓到了就有"）：

- `elder-scam-zh`：1,029 行里 166 行不是中文/粤语行，696 行与已保留行 state 相同（同一场景的多语言与多变体），
  **净得 167 条**，是本批最小的来源。
- `zhihu-preference`：3,460 行对应 2,420 个不同问题（同一问题下多组回答对，契约只保留每个 state 一条），
  保留的那条把 chosen/rejected 与票数放在 `meta.source_record`。

入库抽样规则（`merge` 子命令，确定性、可复算）：

1. 目标中文占比 0.32 → 目标条数 `round(37124 × 0.32/0.68) = 17,470`；
2. 单一来源上限 = 中文样本的 **40%**（6,988 条），与契约 §4 的 40% 同口径；
3. 每域下限 **1,200** 条；先给下限，剩余预算按各域剩余容量比例分配（最大余数法）；
4. 域内按各来源容量比例分配；来源内按 `sha256(seed + id)` 排序取前 N，**不是简单截断头部**；
5. seed = `pol2-bilingual-v1`，所有参数写进 `data/items.bilingual.report.json`。

抽样结果（域预算 human_judgment 10,020 / risk_harm 5,622 / social_moral 1,828 = 17,470）：

| slug | 域 | 可用 | 入库 |
|---|---|---:|---:|
| baidu-review-sentiment | human_judgment | 7,926 | 3,823 |
| toxic-zh | human_judgment | 5,000 | 2,735 |
| chinese-emotion-dialogue | human_judgment | 4,154 | 2,272 |
| chinese-logic-sentiment | human_judgment | 2,176 | 1,190 |
| cvalues-rlhf | risk_harm | 17,966 | 4,016 |
| mh-risk-triage-zh | risk_harm | 1,587 | 912 |
| med-guard-unsafe | risk_harm | 320 | 184 |
| med-guard-benign-r1r5 | risk_harm | 300 | 173 |
| med-guard-benign-r6r11 | risk_harm | 300 | 172 |
| elder-scam-zh | risk_harm | 167 | 96 |
| med-guard-controversial | risk_harm | 120 | 69 |
| zhihu-preference | social_moral | 2,420 | 1,828 |
| **合计** | | **42,436** | **17,470** |

**未入库的 24,966 条中文条目没有被删除**，仍在 `D:\pol2-raw\zh-items\items.zh.jsonl`，
想提高中文占比时重跑第 3 步并改 `--zh-share` 即可（例：`--zh-share 0.5` → 中文 37,124 条，
池子也够）。这也意味着当前 32% 是一个**可调的产品决定**，不是数据上限。

## 3. 分域分布（条目级，中英并列）

| 域 | 英文 | 中文 | 合计 | 中文域内占比 |
|---|---:|---:|---:|---:|
| human_judgment | 5,491 | 10,020 | 15,511 | 64.6% |
| social_moral | 11,352 | 1,828 | 13,180 | 13.9% |
| decision_mechanics | 11,557 | **0** | 11,557 | 0% |
| risk_harm | 4,366 | 5,622 | 9,988 | 56.3% |
| knowledge_reasoning | 4,358 | **0** | 4,358 | 0% |
| pol2_axis | 0 | 0 | 0 | — |
| **合计** | **37,124** | **17,470** | **54,594** | 32.0% |

中文侧三个域都有覆盖（human_judgment / risk_harm / social_moral），且每个域都远高于 1,200 条的域下限；
但两个域是空的 —— 见第 7 节。

## 4. 分语言真值率（native target rate）

| 域 × 语言 | 条目 | 自带真值 | 真值率 |
|---|---:|---:|---:|
| human_judgment · zh | 10,020 | 9,729 | **97.10%** |
| risk_harm · zh | 5,622 | 5,361 | **95.36%** |
| social_moral · zh | 1,828 | 0 | 0.00%（知乎偏好无等义键，按契约不硬塞） |
| decision_mechanics · zh | 0 | 0 | — |
| knowledge_reasoning · zh | 0 | 0 | — |
| **中文合计** | **17,470** | **15,090** | **86.38%** |
| decision_mechanics · en | 11,557 | 7,017 | 60.72% |
| risk_harm · en | 4,366 | 3,709 | 84.95% |
| human_judgment · en | 5,491 | 2,991 | 54.47% |
| social_moral · en | 11,352 | 3,000 | 26.43% |
| knowledge_reasoning · en | 4,358 | 0 | 0.00% |
| **英文合计** | **37,124** | **16,717** | **45.03%** |

中文真值率高于英文是正常的：中文来源以「带标注的分类/分级数据」为主（毒性、情绪、情感、安全三级判定、
风险分级），而英文侧有 20,407 条是**故意留空**等外部答案源的（契约允许：来源没给答案就不编）。
**不要**把 86% 理解成中文数据质量更高——它只说明中文这批来源更"顺带带了标签"，
覆盖面（尤其是机制与推理两类）反而更窄。

## 5. coverage.py 覆盖校验

`coverage.py --items data/items.bilingual.jsonl`（配额取自 [sources.json](sources.json)，`pol2_axis=0` 是 Lead 既有裁决）：

- **结论：通过**（`ok: true`，0 个 violation）
- 六域：human_judgment 15,511 / social_moral 13,180 / decision_mechanics 11,557 / risk_harm 9,988 /
  knowledge_reasoning 4,358 / pol2_axis 0 —— 五个域都 ≥1,200
- 总量 54,594 ≥ 10,000；`max_source_share` 实测 0.1421 ≤ 0.40
- **schema 警告：0 条**
- 1 条提示性 warning：15 个 PoL2 判定轴（`issue_*`）没有任何条目提问 —— 这是**设计如此**
  （`pol2_axis` 下限为 0，专项语料在 [datasets/pol2](../pol2/README.md)，不在此处凑数）

## 6. 已知不对称（训练决策必须知道的一条）

### 6.1 事实

**中文侧在 `decision_mechanics` 与 `knowledge_reasoning` 两个域是 0 条。**

- `decision_mechanics`（工具选择、下一步动作、计划可行性、资格/权限）：
  英文 11,557 条，中文 **0** 条。
- `knowledge_reasoning`（陈述是否有据、证据充分性、常识合理性、推理有效性）：
  英文 4,358 条，中文 **0** 条。
- 合计 15,915 条这两类样本，**全部是英文**，占合并语料的 29.2%。

### 6.2 影响（说白）

1. 这两类能力在训练时**只有英文 token 提供梯度**。中文语境下模型要么靠跨语言迁移，
   要么靠其它域的间接泛化——**没有任何中文监督信号直接教它**「该不该调工具」「这个计划能不能执行」
   「现有信息够不够做决定」「这个说法有没有依据」。
2. 尤其危险的是与中文业务耦合的判断：中文工具/服务命名、中文权限与审批习惯、
   中文文档里的条件与例外表述，这些在英文样本里天然缺失，迁移过来容易只学到"格式"而不是"惯例"。
3. 更隐蔽的一点：中文的其它三个域（情绪/毒性/风险拒绝）都偏向"判断一段文本的性质"，
   而机制与推理偏向"决定下一步做什么"。中文侧缺的正是**行动类判断**，
   所以模型在中文下可能表现为：情绪/风险判得很准，但一到"接下来怎么做"就退化或过度澄清。
4. **这是数据组成的既成事实，不是实测的能力结论。** 本轮没有训练、没有评测，
   因此不能声称"中文决策能力一定下降 X%"；能声称的是"该能力没有中文监督"。

### 6.3 为什么没有用别的东西填上

- **机翻来源**：`Nemotron-Safety-Guard-v3`（45 万）、`PolyGuardMix`（191 万）、
  `DirectLLM/Chinese_Preference` 等 9 个数据集**量足够大、卡面也就缺口这一块**，
  但它们是英文数据集的翻译/文化适配产物，用户已明确"机器翻译出来的英文数据集不算中文数据集"，因此整批剔除
  （逐条证据见 [zh-survey.md](zh-survey.md) 第 3 节）。
- **`BAAI/COIG`**（97,739 条中文原生指令）：许可清楚、中文原生，但形态是通用指令/多轮问答，
  不是"待判断的情境"。把它当 decision 样本只能靠硬套 CORE 键，属于**凑数**，因此不进池。
- 结论：**缺口是真的，不是没找够。** 不降门槛是这个项目更重要的资产。

### 6.4 给训练决策的选项（按代价从低到高）

| 选项 | 做什么 | 代价 / 副作用 |
|---|---|---|
| A. 先测再定 | 在 PoL2 中文 benchmark 里补一小片 `decision_mechanics`/`knowledge_reasoning` 的中文题，先量出差距再决定要不要补数据 | 需要 benchmark 侧配合（EVAL/本体）；不解决训练缺口本身 |
| B. 中文生成（非翻译） | 用现有生成流水线**直接用中文出题**（场景族 + 最小对立对），教师交叉判定真值 | 花钱、要人工审；但这是唯一不改口径的正路 |
| C. 有监督地复用 COIG | 明确按"通用问答降级为 state"处理，只保留 `information_sufficient`/`question_well_formed` 等少数键 | 会引入"state 与问题语义不相干"的样本，需要人工抽查，属于降门槛的边界操作 |
| D. 提高中文占比 | `merge --zh-share 0.5`（中文 37,124 条，池子够） | **不解决缺口**：多的仍然只在那三个域，只会让语料更偏向情绪/毒性/拒绝类判断 |
| E. 直接接受 | 承认中文机制/推理靠迁移，训练后在中文语料上专项评测 | 风险自担；至少要在结果卡里披露 |

**推荐 A + B 并行：先用 A 把差距量出来，再用 B 补数据。D 单独做没有任何意义**（这是本报告最想让人看到的一句）。

## 7. 未测项与风险

- **未训练、未评测**：本报告只描述数据组成，不含任何模型效果结论。
- **语义近重复未工具化**：去重仍是 state 精确哈希（契约既有行为），跨来源的同情节改写/翻译未检测。
- **中文侧覆盖偏窄**：三域中 human_judgment 占 57%、risk_harm 占 32%、social_moral 占 10%；
  中文样本内部也偏向"文本性质判断"，行动类判断为零。
- **两个来源的证据等级是 B**：`textdetox` 的中文子集未列原始来源；`left0ver` 的 label 极性由 30 条抽样核对。
- **抽样是确定性的但也是单一的**：只跑了一组参数（32% / cap 0.4 / floor 1200 / seed pol2-bilingual-v1）；
  换参数会得到不同的 17,470 条（池子里的 42,436 条都在，可复算）。
- **未入库的中文池没有备份**：`D:\pol2-raw\zh-items\items.zh.jsonl` 是本机文件；需要长期保留应另行归档。

## 8. 交接

1. Lead 复核 `data/items.bilingual.report.json` 与本节数字后提交 `.gz`（明文已被忽略）。
2. 训练侧若按 30% 精确配比，可直接用本文件（32%）；若要更高中文占比，重跑 `merge --zh-share`。
3. 第 6.4 节的 A/B 两项建议进入下一轮任务；**在那之前不要用"中文占比达标"当作双语能力达标的证据**。
