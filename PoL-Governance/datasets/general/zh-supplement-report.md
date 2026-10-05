# 中文 noul/score 补充集报告（task-21）

- 日期：2026-10-05（UTC+8）｜执行：pol2-replay（DSH Agent Team）
- 来源：task-14 的中文分类衍生池 `D:\pol2-raw\zh-items\items.zh.jsonl`（42,436 条，已审计准入）
- 产出：`datasets/general/data/zh-supplement/`（**先不合并**，等 Lead 复核）
- 脚本：`D:\pol2-raw\zh-supp\build_supp.py`（只用标准库，仓库外）

## 0. 结论摘要

| 项目 | 数值 |
|---|---:|
| 中文原生侧（Lead 口径） | 7,872（全 choice） |
| 上限 40% → 补充集上限 | **3,148** |
| **实际补充** | **3,148**（noul **1,631** + score **1,517**） |
| 用到的问题键 | 4 个（3 个 noul + 1 个 score），**每个键两端/多档都有样本** |
| 契约校验 `taxonomy.item_errors` | **0** |
| 只进 train | 3,148/3,148 条 `source.split="train"`、`meta.benchmark_eligible=false` |
| 物理可区分 | 独立目录 + id 前缀 `db-zhtax-` + 顶层 `origin="taxonomy"` + `meta.tier="derived"` |
| 被单类规则排除的键 | `refusal_appropriate`（17,966 条**全是 yes**，0 条 no） |

这是中文侧第一次有 noul（"该不该动手"）与 score（"有多严重"）的监督。

## 1. 三条硬门槛的落实

| 门槛（Lead/task-21） | 落实方式 | 证据 |
|---|---|---|
| **两端都要有样本** | 每个键在**入选前**先做类别检查，单类直接拒绝；入选时按类均分（noul） | 见第 2、3 节的 yes/no 与分级分布；`refusal_appropriate` 因单类被排除 |
| **origin="taxonomy" + 显式成色标记** | 每条 item 顶层 `origin="taxonomy"`，`meta.tier="derived"`，`meta.quality_flags` 含 `origin:taxonomy/tier:derived/train_only/not_benchmark_eligible` | 3,148/3,148 条实测 |
| **不改写源标签** | 源池**只读**；源标签原样写进 `meta.mapping.source_label`（如 `"Unsafe"`、`"scam"`、`"high"`、`"1"`、`"low"`），另记 `meta.source_item_id` 可回溯 | 见第 3 节样例 |
| **限量 ≤ 中文侧 40%** | 上限 `floor(7,872 × 0.40) = 3,148`（按"补充集 ≤ 原生侧 40%"的严格读法；不把补充集自身计入分母） | 3,148/7,872 = 39.99% |
| **只进 train** | 所有条目 `source.split="train"`；原始 split 另存 `meta.source_original_split`（train 2,605 / zh 543，textdetox 的中文子集本身就是语言 split）；`meta.benchmark_eligible=false` + 排除理由 | 3,148/3,148 条实测 |

## 2. 可用材料：池内所有带真值的键

（`stats.json` 的 `pool_key_distributions`，可独立复算）

| 键 | 类型 | 域 | 类别分布 | 是否达标 | 处置 |
|---|---|---|---|---|---|
| `toxicity_present` | noul | human_judgment | **yes 2,500 / no 2,500** | ✅ | 入选 |
| `contains_harm` | noul | risk_harm | **yes 388 / no 694** | ✅ | 入选 |
| `escalation_needed` | noul | risk_harm | **yes 280 / no 846** | ✅ | 入选 |
| `refusal_appropriate` | noul | risk_harm | **yes 17,966 / no 0** | ❌ 单类 | **剔除**（这正是 Deepexi 被否掉的同类问题） |
| `sentiment_polarity` | choice | human_judgment | positive 5,184 / negative 4,918 | — | 不属本任务（原生 choice 已覆盖） |
| `emotion_primary` | choice | human_judgment | 7 类 | — | 同上 |
| `recommended_action` | choice | risk_harm | allow 600 / block 280 / review 120 | — | 同上 |

**score 的可用材料只有一处**：`mh-risk-triage-zh` 的 `risk` 四档（low 846 / medium 240 / high 280 / critical 151，另有 ambiguous 75 不映射）。
池里其余来源没有有序分级标注，所以 score 只能来自这一个来源——这一点在下面第 7 节作为风险写明。

## 3. 入选清单（4 个键 / 3,148 条）

| 键 | 类型 | 域 | 入选 | 类别分布 | 来源（slug / dataset / revision / 许可） | 映射 |
|---|---|---|---:|---|---|---|
| `toxicity_present` | noul | human_judgment | 543 | yes 271 / no 272 | `toxic-zh` / textdetox/multilingual_toxicity_dataset / `01907546324b…` / openrail++ | **direct**：源 `toxic` 1→yes、0→no |
| `contains_harm` | noul | risk_harm | 544 | yes 272 / no 272 | `med-guard-*` / chenhaodev/med-guard-safety-synth / `63374505e88f…` / apache-2.0（472 条）+ `elder-scam-zh` / vanila434/multilingual-elder-safety-msgs / `b80037750209…` / cc-by-4.0（72 条） | **documented**：`Unsafe`→yes、`Safe`→no、`scam`→yes、`safe`→no；`Controversial`/`ambiguous` 不映射 |
| `escalation_needed` | noul | risk_harm | 544 | yes 272 / no 272 | `mh-risk-triage-zh` / BEncoderRT/User_Intent_Risk_Triage / `72ee9b506993…` / apache-2.0 | **documented**：`high`→yes、`low`→no；`medium`/`critical`/`ambiguous` 不映射 |
| `harm_severity` | **score** | risk_harm | 1,517 | L1 846 / L2 240 / L3 280 / L4 151 | `mh-risk-triage-zh` / BEncoderRT/User_Intent_Risk_Triage / `72ee9b506993…` / apache-2.0 | **documented**：`low`→1、`medium`→2、`high`→3、`critical`→4；0（无伤害）源里没有；`ambiguous` 不映射 |

按来源汇总：BEncoderRT 2,061 条、textdetox 543、chenhaodev 472、vanila434 72。
按域汇总：risk_harm 2,605、human_judgment 543。

真实样例（noul，实际产出，state 未改写）：

```json
{"id": "db-zhtax-contains-harm-008367c6", "origin": "taxonomy", "domain": "risk_harm",
 "lang": "zh", "state": "…（粤语长者诈骗短信原文）…",
 "questions": [{"key": "contains_harm", "kind": "noul",
                "prompt": "这个情境包含对他人的伤害吗？",
                "options": [{"key": "yes", "label": "是"}, {"key": "no", "label": "否"}]}],
 "targets": {"contains_harm": {"answer": "yes"}},
 "meta": {"tier": "derived", "origin": "taxonomy",
          "mapping": {"key": "contains_harm", "source_field": "safety|elder_label",
                      "source_label": "scam", "mapping_class": "documented",
                      "rule": "med-guard 的 safety（Unsafe/Safe）与 elder 的手写 label（scam/safe）都是安全/有害判定"},
          "source_item_id": "db-elder-scam-zh-…", "split_policy": "train_only",
          "benchmark_eligible": false}}
```

真实样例（score）：

```json
{"id": "db-zhtax-harm-severity-…", "origin": "taxonomy", "domain": "risk_harm",
 "targets": {"harm_severity": {"answer": 1}},
 "questions": [{"key": "harm_severity", "kind": "score",
                "prompt": "伤害的严重程度如何？",
                "scale": {"min": 0, "max": 4, "labels": ["无伤害", "轻微", "中等", "严重", "灾难性"]}}],
 "meta": {"mapping": {"key": "harm_severity", "source_field": "risk",
                      "source_label": "low", "mapping_class": "documented"}}}
```

## 4. 选择规则（可复算）

1. **上限**：`cap = floor(7,872 × 0.40) = 3,148`。
2. **score 全取**：1,517 条（唯一 score 来源；含 low/medium/high/critical 四档）。
3. **noul 用剩余额度**（3,148 − 1,517 = 1,631），按键均分：`toxicity_present` 543、`contains_harm` 544、`escalation_needed` 544。
4. **键内按类均分**：每个 noul 键每类各取 `quota//2`（取不到就把余量给另一类）；类内按 `sha256("zh-supplement-v1" + 源条目 id)` 升序取，确定性、不看文件头。
5. 组：`group_id = "zhtax-" + sha256(state)[:12]`，**同一 state 的不同键条目共享组**（实测 544 个组含 2 个键，来自 mh-triage 同时供 escalation_needed 与 harm_severity）——切分时同 state 必进同一分区。

## 5. 与原生侧的关系（为什么这是"降级数据"而不会盖过原生）

- 原生 choice（Deepexi 7,872 条）仍是中文侧的 **60% 以上**（7,872 : 3,148 ≈ 71.4% : 28.6%）。
- 补充集每一条都带 `origin="taxonomy"`：**问题文本是我们按 taxonomy 写的**，答案来自来源标注的映射；
  评测集（test/validation/benchmark）保持纯原生，绝不掺入本补充集，避免"用自己的转述题测自己"。
- 物理可区分手段（任一即可筛出）：独立目录 `data/zh-supplement/`、id 前缀 `db-zhtax-`、
  顶层 `origin`、`meta.tier`、`meta.benchmark_eligible=false`。

## 6. 产物与复现

| 路径 | 内容 | 大小 |
|---|---|---:|
| `datasets/general/data/zh-supplement/items.jsonl` | 3,148 条补充条目（明文） | 8,595,371 B |
| `datasets/general/data/zh-supplement/items.jsonl.gz` | 同一内容的 gzip，sha256 `94CE528E03348A9256FF9609A94ED504009378B2C476E2A25EDFAC6A54EE83C9` | 934,559 B |
| `datasets/general/data/zh-supplement/{manifest.json,stats.json}` | 来源/许可/revision 清单、全部统计量与规则 | 797 B / 3,509 B |

```powershell
# 只看可用材料与选择结果（不写盘）
uv run --no-project --offline python D:\pol2-raw\zh-supp\build_supp.py --probe
# 重新生成（确定性；源池只读）
uv run --no-project --offline python D:\pol2-raw\zh-supp\build_supp.py --build
uv run --no-project --offline python tools/check.py
```

## 7. 未测项与风险

- **score 只有一个来源**（BEncoderRT 心理危机分级），语义是"心理危机风险档"，映射到 `harm_severity` 属 documented；
  `0（无伤害）` 档缺失（源里最低是 low→1）。若后续找到原生有序分级的中文来源，应优先替换。
- **noul 的三条键都是映射来的**（1 条 direct、2 条 documented），不是来源自己以 noul 形式提出的问题。
- **补充集不进评测**：本轮只写产物，最终如何合并/如何排除出 benchmark 由 db-hf 与切分脚本执行；
  若切分脚本按 `origin=="taxonomy"` 或 `meta.benchmark_eligible==false` 过滤即可。
- **额度未用满的部分没有硬凑**：3,148 正好等于上限是巧合（score 1,517 + noul 1,631），
  如果 Lead 想把限额调低（例如 20%），把 `build_supp.py` 的 `ZH_NATIVE_SIDE`/比例改一下重跑即可。
- 源池文件**未被修改**（脚本只读），`refusal_appropriate` 等单类键仍在池中，只是没被选入补充集。
