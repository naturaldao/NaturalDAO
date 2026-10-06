# 训练侧过滤与路由（general v0.1）

> **一句话**：`probs` 字段里装着**至少 5 种不同的量**——教师预测分布、规则算出的参考标签、并列选项的均分占位、
> 我们自己用 `point_mass` 造的单点、以及整条子流恒定的常量。训练与评测必须按**语义**分开走，
> 本页给出可直接复跑的过滤清单、分区剩余数与参考实现。
>
> 依据：[target 溯源报告](target-provenance.md) §6 的 R1–R13 规则表；机器可读路由见
> [target-types.jsonl.gz](data/target-types.jsonl.gz)（31,786 行，每条 target 一行）。
> **本页不修改任何语料、不动任何划分。**

---

## 0. 一页结论

| | 条数 | 训练怎么办 | 能不能当校准参照 |
|---|---:|---|---|
| 我们伪造的 one-hot（`point_mass`） | 5,488 | 硬标签，分类损失 | ❌（不是分布） |
| 来源自带的退化 one-hot | 8,631 | 硬标签，分类损失 | ❌（不是分布） |
| 只有 `answer`、没有 `probs` | 8,417 | 硬标签，分类损失 | ❌（没有概率目标） |
| 真·非退化 soft 分布 | 7,288 | **软蒸馏目标** | ❌ 只有其中 432 条是 |
| 无信息：全候选等值 | 1,730 | **剔除** | ❌ |
| 无信息：并列均分占位 | 232 | **剔除**（见 §4.4 的另一口径） | ❌ |
| **合计** | **31,786** | | **432** |

三条路由（训练视图）：

| 路由 | 条数 | 含义 |
|---|---:|---|
| `drop` | **1,962** | 剔除：无信息均匀 1,730（含 `yuri_v1` 常量 1,621）+ 并列均分占位 232 |
| `classification` | **22,536** | 分类损失（硬标签）：5,488 伪造 one-hot + 8,631 来源自带 one-hot + 8,417 answer_only |
| `distillation` | **7,288** | 软蒸馏目标，**不用于校准** |

**全语料 31,786 个 target 里，只有 432 条（1.4%）可以当概率校准的参照**——procedural 的 7 个
documented 精确概率键上的非退化取值（报告 §3.6 / §5）。其余 6,856 条教师分布是**信念**不是**世界概率**，
拿它测校准等于在测「学生和教师像不像」。

---

## 1. 交付物与不变量

| 交付物 | 说明 |
|---|---|
| [target-types.jsonl.gz](data/target-types.jsonl.gz) | 旁挂路由，31,786 行，每条 target 一行；明文 `data/target-types.jsonl` 由脚本生成（见 §8 的 .gitignore 说明） |
| [target_types.py](target_types.py) | 生成器：实现 R1–R13，自带自检（对不上报告 §6.3 就非零退出） |
| [filter_targets.py](filter_targets.py) | 过滤与路由的参考实现：只读，打印各分区过滤前后条数 |
| [test_target_types.py](test_target_types.py) | 不变量测试（`tools/check.py` 的 unittest discovery 会收进来） |
| 本页 | 过滤与路由规格 |

不变量（由 `target_types.py --verify` 与测试共同保证）：

1. **合计 = 31,786**，连接键 `(item_id, question_key)` 全局唯一；
2. `target_type` 四类分布 = 报告 §6.3 的 15,919 / 8,417 / 5,488 / 1,962；
3. 逐规则命中数与报告 §6.3 完全一致；
4. `hard_label` ⇔ 转换器旗标 `hard_label_to_point_mass`（5,488 条）；
5. **原语料字节不变**：旁挂文件只读语料，不写回（语料 sha256 见报告抬头）。

---

## 2. 旁挂文件字段

报告 §6.2 的 9 个字段 + 本任务新增的 3 个旁挂字段。**新增字段都是审计用的派生量，可整体忽略**。

| 字段 | 取值域 | 来源 |
|---|---|---|
| `item_id` / `question_key` | string | 连接键，与语料 `(item_id, target key)` 一一对应 |
| `target_type` | `hard_label` \| `soft_distribution` \| `uninformative_uniform` \| `answer_only` | §6.2 |
| `distribution_semantics` | `vote_share` \| `model_logits` \| `temperature_softmax` \| `self_confidence` \| `rule_counter` \| `human_annotation` \| `unknown` \| `none` | §6.2 |
| `target_type_basis` | `source` \| `shape` | §6.2。`shape` 只有 341 行（R12+R13） |
| `semantics_confidence` | `high` \| `medium` \| `low` \| `unknown` | §6.2 |
| `calibration_role` | `reference_probability` \| `soft_target_only` \| `label_only` | §6.2 |
| `label_trust` | `rule_exact` \| `teacher_argmax` \| `behavioral` \| `unknown` | §6.2 |
| `mechanism_unknown` | bool | §6.2。只有 6,999 条（R9+R10，报告 §7 U1） |
| `provenance_ref` | string[] | §6.2，对应报告 §6.4 的 E1–E13 |
| `shape_note` | string \| null | §6.2，**仅旁证**，消费者可忽略 |
| `rule_id` | `R1`–`R11` | **新增**：命中的**来源证据**规则号，与 §6.3 逐行对账 |
| `shape_override` | `R12` \| `R13` \| null | **新增**：是否被形态兜底覆盖（只降 `target_type`，不改语义） |
| `shape_class` | 6 个形态桶 | **新增**：`answer_only` / `onehot_fabricated` / `onehot_native` / `soft` / `uniform_all_candidates` / `tie_subset` |
| `training_route` | `drop` \| `classification` \| `distillation` | **新增**：训练侧路由（本页 §4） |

> **为什么把 `rule_id` 与 `shape_override` 分开**：报告 §6.3 的逐规则计数（R5 = 432、R7 = 4,479 …）是
> **源规则命中数**，而 R12/R13 是**覆盖规则**——它们把 341 行的 `target_type` 从 `soft_distribution`
> 降级成 `uninformative_uniform`，同时**继承**源规则的 `distribution_semantics` / `calibration_role` /
> `label_trust`。§6.3 那张表里会产出 soft 的六条规则（R5/R6/R7/R8/R9/R11）相加是 16,260
> （R10 的 1,621 本来就是 `uninformative_uniform`），而 soft 总数写 15,919，差额正是 341。
> 两个字段并置后，两种口径都能逐行对上（见 §3）。

---

## 3. 全量分布（与报告 §6.3 对账）

### 3.1 `target_type` 四类

| `target_type` | 条数 | 构成 |
|---|---:|---|
| `soft_distribution` | 15,919 | 含来源自带的 8,631 条退化 one-hot（语义上是分布，只是取值退化） |
| `answer_only` | 8,417 | deepexi 7,872 + procedural 545 |
| `hard_label` | 5,488 | 我们造的 `point_mass` 单点 |
| `uninformative_uniform` | 1,962 | `yuri_v1` 常量 1,621 + 全候选等值 109 + 并列均分 232 |
| **合计** | **31,786** | |

### 3.2 逐规则命中数（报告 §6.3 逐行一致）

| # | 命中条件（来源证据） | 命中 | 最终 `target_type` |
|---|---|---:|---|
| R1 | `jev-decisions-general-50k` / `jev-decisions-strata` | 4,009 | `hard_label` |
| R2 | `systemone-lite-general` | 1,479 | `hard_label` |
| R3 | `deepexi-fcs-v3`（无 `probs`） | 7,872 | `answer_only` |
| R4 | `procedural` 无 `probs` | 545 | `answer_only` |
| R5 | `procedural` 的 7 个 documented 精确概率键（**非退化**） | **432** | `soft_distribution` |
| R6 | `procedural` 其余（含 7 键上的退化取值） | 3,714 | 3,696 soft + 18 降级 |
| R7 | `open-jev` | 4,479 | 4,221 soft + 258 降级 |
| R8 | `jev-distill-v3` / `openjev_v2` | 757 | 714 soft + 43 降级 |
| R9 | `jev-distill-v3` / `yuri_v3` | 5,378 | 5,364 soft + 14 降级 |
| R10 | `jev-distill-v3` / `yuri_v1`（整条子流常量 0.5） | 1,621 | `uninformative_uniform` |
| R11 | `system-one-270m` | 1,500 | 1,492 soft + 8 降级 |
| R12 | 形态兜底：全候选等值（**覆盖**） | 109 | `uninformative_uniform` |
| R13 | 形态兜底：并列均分，且来源是「并列均分」构造（**覆盖**） | 232 | `uninformative_uniform` |

R12 的 109 来自：procedural 18 + `yuri_v3` 14 + `openjev_v2` 12 + open-jev 57 + system-one-270m 8。
R13 的 232 来自：open-jev 201 + `openjev_v2` 31。

### 3.3 形态桶（旁证，报告 §0.2 的同一套事实）

| `shape_class` | 条数 | 说明 |
|---|---:|---|
| `answer_only` | 8,417 | 没有 `probs` |
| `onehot_fabricated` | 5,488 | 旗标 `hard_label_to_point_mass` |
| `onehot_native` | 8,631 | 来源自带的退化取值（4,221 open-jev + 3,696 procedural + 714 `openjev_v2`） |
| `soft` | 7,286 | 真·非退化 |
| `uniform_all_candidates` | 1,730 | 全候选等值 |
| `tie_subset` | 234 | 正权重子集并列（232 是占位符 + 2 是真实取值，见 §7 冲突 3） |
| **合计** | **31,786** | |

---

## 4. 训练侧路由规格

### 4.1 三条路由

| 路由 | 判据 | 损失 | 条数 |
|---|---|---|---:|
| `drop` | `target_type = uninformative_uniform` | 不参与任何损失 | 1,962 |
| `classification` | `target_type ∈ {hard_label, answer_only}`，或 `soft_distribution ∧ shape_class = onehot_native` | 交叉熵（答案即标签） | 22,536 |
| `distillation` | `soft_distribution` 且非退化 | 对 `probs` 的软目标（KL / soft CE） | 7,288 |

用户批准的三条决定与实现的对应：

1. **剔除无信息流** → `drop`。任务书写的「1,730 条无信息均匀 + 1,621 条 `yuri_v1` 常量」是**包含关系**
   （1,621 ⊂ 1,730），不是相加；报告 §5 结论 3 建议把并列均分的 232 条一并剔除，故 `drop` = 1,962。
   两种口径都提供，见 §4.4。
2. **5,488 条我们伪造的 one-hot → 硬标签（分类损失）** → `classification`（`target_type = hard_label`）。
3. **8,631 条来源自带的 one-hot → 标 hard_label** → `classification`。注意轴上区别：旁挂文件的
   `target_type` 仍按报告 §6.3 记为 `soft_distribution`（**来源语义**确实是退化分布），
   训练路由在 `training_route = classification`（**损失按硬标签算**）。
4. **7,520 条教师软分布 → 保留作蒸馏目标、不用于校准** → 其中 232 条并列占位按报告 §5 剔除，
   蒸馏集 = 7,288；**没有任何一条教师分布进入 `calibration_role = reference_probability`**。

### 4.2 各分区过滤前后（冻结语料 23,855 条 / 31,786 target）

| 分区 | items | target 合计 | 剔除 `drop` | 分类 `classification` | 蒸馏 `distillation` | 过滤后保留 |
|---|---:|---:|---:|---:|---:|---:|
| train | 14,836 | 19,551 | 1,170 | 13,986 | 4,395 | **18,381** |
| test | 4,946 | 6,604 | 394 | 4,728 | 1,482 | **6,210** |
| validation | 2,473 | 3,232 | 196 | 2,347 | 689 | **3,036** |
| benchmark | 1,600 | 2,399 | 202 | 1,475 | 722 | **2,197** |
| **合计** | **23,855** | **31,786** | **1,962** | **22,536** | **7,288** | **29,824** |

**train 分区还有一个尾巴**：[split-manifest.json](data/splits/split-manifest.json) 记的**中文补充**
3,148 条（`db-zhtax-*`，taxonomy 派生，只追加进 train、不参与切分）不在冻结语料里，因此不在旁挂文件里；
它们**全部是 `answer_only`**（没有 `probs`），按同一规则走 `classification`：

| 实际文件 | target 合计 | 剔除 | 分类 | 蒸馏 | 过滤后保留 |
|---|---:|---:|---:|---:|---:|
| `train.jsonl`（冻结 19,551 + 补充 3,148） | 22,699 | 1,170 | 17,134 | 4,395 | **21,529** |

> 使用边界（AGENTS.md 数据边界）：`train` 用于梯度；`validation` 用于选模型；
> `test` 只做回归、不用于梯度/教师生成/蒸馏/选阈值；`benchmark` 是内部保留集，
> 只做回归，本页给出它的数字仅为口径完整，**不得**据此调参。反复依据测试改方案要披露。

### 4.3 剔除理由计数（全语料 1,962）

| 理由 | 条数 |
|---|---:|
| R10：`yuri_v1` 整条子流常量 `[0.5, 0.5]`（报告 §7 U2，无信息） | **1,621** |
| R13：并列均分占位（open-jev 201 + `openjev_v2` 31，文档明说 "do not represent measured model uncertainty"） | **232** |
| R12：全候选等值（procedural 18 + `yuri_v3` 14 + `openjev_v2` 12 + open-jev 57 + system-one-270m 8） | **109** |
| **合计** | **1,962** |

### 4.4 并列均分的两种口径（一个开关）

任务书按**形态**四分类把 234 条并列算在「7,520 条教师软分布」里；报告 §5 结论 3 则明确建议
「1,962 条（uniform 1,730 + 并列均分 232）任何训练/评测口径都应先剔除」。两者只差这 232 条：

| 口径 | 命令 | 剔除 | 蒸馏 | 过滤后保留（全语料） |
|---|---|---:|---:|---:|
| **drop（默认，按报告 §5）** | `filter_targets.py` | 1,962 | 7,288 | 29,824 |
| `distill`（按任务书字面） | `filter_targets.py --ties distill` | 1,730 | 7,520 | 30,056 |

`--ties distill` 下各分区：train 1,038 / test 340 / validation 179 / benchmark 173 被剔除。

**建议默认 `drop`**：那 232 条的 0.5 / 0.3333 表示「这几个选项并列」，不表示结果发生的概率
（E8 原文：`do not represent measured model uncertainty`）。当蒸馏目标会教出「一有并列就报 50%」的行为。
若只想要「不丢数据、不碰语义」的保守口径，用 `--ties distill` 并把那 232 行单独打标。

### 4.5 参考实现（可直接跑）

    # 默认口径（报告 §5）：剔除 1,962，蒸馏 7,288
    uv run --no-project --offline python datasets/general/filter_targets.py

    # 任务书字面口径：只剔除 1,730，蒸馏 7,520
    uv run --no-project --offline python datasets/general/filter_targets.py --ties distill

    # 机器可读：--json 打印，--emit 写聚合计数（只含计数，不含样本、不含 id 清单）
    uv run --no-project --offline python datasets/general/filter_targets.py --json

训练时在 DataLoader 层按连接键过滤，**不重写语料**：

    import gzip, json

    ROUTES = gzip.open("datasets/general/data/target-types.jsonl.gz", "rt", encoding="utf-8")
    route_of = {}
    for line in ROUTES:
        row = json.loads(line)
        route_of[(row["item_id"], row["question_key"])] = row["training_route"]

    def keep(item, question, wanted=("classification", "distillation")):
        return route_of.get((item["id"], question["key"])) in wanted

    # 分类损失：wanted=("classification",)；蒸馏：wanted=("distillation",)
    # 校准：只用 calibration_role == "reference_probability" 的 432 条

### 4.6 校准口径

`calibration_role = reference_probability` 的 **432** 条，分布：

| 分区 | 条数 |
|---|---:|
| train | 267 |
| test | 84 |
| validation | 37 |
| benchmark | 44 |

按 `meta.native_task`：`partial_observation_calibration` 109 / `policy_under_uncertainty` 278 /
`arithmetic` 45（合计 432）。

报告 §3.6 的 5 个条件仍然适用：只限这 432 条；只在合成世界内成立（是「这个世界发生了 A」的概率，
不是「人类会怎么判」）；模型必须看到与生成器相同的 `state`；**逐 task 分别报告**，不要揉成一个 ECE；
「noise-free」是卡面声明而非我们复核过。

若只需要 ECE（置信度校准）而不需要分布校准，硬标签路线可用面大得多（22,536 条），
但必须用 `label_trust` 分层报告，否则 ECE 的分子分母里混着四类不同的「正确」：

| `label_trust` | 条数 | 含义 |
|---|---:|---|
| `rule_exact` | 11,406 | 规则精确算出（procedural / open-jev / systemone-lite） |
| `teacher_argmax` | 8,499 | 教师分布的 argmax（belief，不是正确答案） |
| `unknown` | 7,872 | deepexi 答案来源无文档（报告 §7 U3） |
| `behavioral` | 4,009 | 轨迹里「当时做了什么」，不是「正确答案」（报告 §3.3） |

---

## 5. 关键设计决定：过滤不做在语料上

**决定**：过滤以「旁挂路由 + 训练视图」交付，**原语料一个字节都不改**，也不动任何划分。

理由：

1. **可复算**。原语料 sha256 不变，任何人拿同一份语料 + `target_types.py` 都能重算出同一份过滤清单
   （`--verify` 逐行比对）。若把剔除直接做进语料，就再也无法回答「被剔掉的到底是什么」。
2. **划分已冻结且 benchmark 用仓外私盐加固**（[split-report.md](split-report.md)），重切会破坏可复现性，
   也会让已发布的 split-manifest 摘要对不上。
3. **规则还会迭代**。本任务执行过程中就发现报告 §6.3 的 R5/R13 有两处口径需要收紧（§7 冲突 2、3），
   旁挂文件可以随时重建；改语料不可逆。
4. **留出反事实**。`--ties drop|distill` 让「剔除 232 条并列」这个判断可以一键回滚做消融，
   而破坏性过滤做不到。

代价与对策：训练代码必须**显式**按路由过滤（一行 `route_of.get(...)`，见 §4.5），
不能直接 `cat train.jsonl` 开训——这是「可复算」换来的成本。若确实需要一份物理过滤后的文件，
用 `filter_targets.py` 的清单在训练前流式过滤即可，不需要落盘第二份语料。

---

## 6. 更正：按 `meta.native_source` 统计，不要按 `source.slug`

### 6.1 问题

`jev-distill-v3` 这**一个 slug 里混了三种语义**（报告 §0.4 第 1 条）：

| `meta.native_source` | target 数 | `distribution_semantics` | `target_type` | 能不能当校准参照 |
|---|---:|---|---|---|
| `yuri_v3` | 5,378 | `model_logits` | 5,364 soft + 14 uniform | ❌ 软蒸馏目标 |
| `yuri_v1` | 1,621 | `model_logits`（**取值恒定**） | 1,621 uniform | ❌ **必须剔除** |
| `openjev_v2` | 757 | `rule_counter` | 714 soft + 43 uniform | ❌ 规则参考标签 |

同一个 slug 下：一个是教师信念、一个是常量、一个是 Open-Jev 规则标签的转出。
**任何按 `source.slug` 的统计（数据配比、平均熵、校准分层、ECE 报告）都是错的。**

另外两个 slug 内部也不单一：

- `open-jev`：`customer-control-v1` 4,206 + `vizdoom-basic-v1` 273（后者 100% one-hot，273 条规则确定答案）；
- `jev-decisions-strata`：`nvidia/Nemotron-SFT-Agentic-v2` 128（`verified_demonstration`）+
  `nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1` 79（`explicit_expected_action`）。

### 6.2 正确口径与数字（全量 12 个 `(slug, native_source)` 组）

| `source.slug` | `meta.native_source` | items | targets | 语义 | 校准角色 |
|---|---|---:|---:|---|---|
| `deepexi-fcs-v3` | `None`（中文侧） | 7,872 | 7,872 | `unknown` | `label_only` |
| `jev-distill-v3` | `yuri_v3` | 5,378 | 5,378 | `model_logits` | `soft_target_only` |
| `jev-distill-v3` | `yuri_v1` | 1,621 | 1,621 | `model_logits`（常量） | `soft_target_only`（**剔除**） |
| `jev-distill-v3` | `openjev_v2` | 757 | 757 | `rule_counter` | `label_only` |
| `open-jev` | `customer-control-v1` | 701 | 4,206 | `rule_counter` | `label_only` |
| `open-jev` | `vizdoom-basic-v1` | 91 | 273 | `rule_counter` | `label_only` |
| `procedural-typed-decisions` | `None` | 1,500 | 4,691 | `rule_counter` / `none` | 432 条 `reference_probability` |
| `system-one-270m` | `None` | 447 | 1,500 | `model_logits` | `soft_target_only` |
| `systemone-lite-general` | `None` | 1,479 | 1,479 | `none` | `label_only` |
| `jev-decisions-general-50k` | `…Nemotron…Tool-Use-Pivot-v1` | 3,802 | 3,802 | `none` | `label_only` |
| `jev-decisions-strata` | `…Nemotron-SFT-Agentic-v2` | 128 | 128 | `none` | `label_only` |
| `jev-decisions-strata` | `…Nemotron…Tool-Use-Pivot-v1` | 79 | 79 | `none` | `label_only` |
| **合计** | | **23,855** | **31,786** | | |

**规则**：凡是分组统计，键一律用 `(source.slug, meta.native_source)` 双键；
语义与校准可用性只在 `meta.native_source` 这一层定义。

### 6.3 错在哪：一个具体数字

报告 §2.3 那张表里 `jev-distill-v3` 的「soft n = 5,395，平均熵 0.755 nats，平均最大概率 0.666」，
按 `meta.native_source` 拆开后是**两个不同的量**：

| 口径 | n | 平均熵 | 平均最大概率 | 是什么 |
|---|---:|---:|---:|---|
| `jev-distill-v3`（**按 slug，错**） | 5,395 | 0.755 | 0.666 | 教师分布与规则占位符的混合平均 |
| `yuri_v3` | 5,364 | **0.755** | **0.667** | 教师 Jev 1.13 的预测分布（信念） |
| `openjev_v2` | 31 | **0.768** | **0.470** | Open-Jev 并列均分占位（规则，且**全部要剔除**） |

按 slug 看，这 5,395 条像是同一锅「软标签」；拆开后才发现其中 31 条平均最大概率只有 0.470
（不是教师觉得不确定，是并列占位），而且**一条都不该进蒸馏集**。同理 `open-jev` 的
「0.693 = ln 2、平均最大概率恰好 0.500」根本不是「平均的软」，那 201 条**全是并列均分**。

其它同源数字（拆分后可核对）：`system-one-270m` n = 1,492，平均熵 0.122；
`procedural` 的非退化 n = 432，平均熵 0.347。

---

## 7. 未决项与规则冲突（本次执行发现）

**冲突 1｜§6.3 的两种计数口径混在一张表里。** R5/R6/R7/R8/R9/R11 相加 = 16,260（R10 的 1,621 条
本来就是 `uninformative_uniform`，不参与这次降级），但同表的 soft 总数写 15,919，
差 341 = R12(109) + R13(232)。这不是错，而是「源规则命中数」与「最终 `target_type`」两个口径：
R12/R13 是**覆盖规则**且继承语义。落盘时用 `rule_id`（R1–R11）+ `shape_override`（R12/R13/null）
两个字段分开记，两个口径都能逐行对上；测试同时断言两者。

**冲突 2｜R5 的「432」与字面谓词的「529」。** §6.3 的 R5 谓词只写「`(native_task, key) ∈ 7 键」，
按此命中 **529**；但 §3.6 的表头是「本语料 **soft** 条数」合计 **432**，§0.3 / §5 也都以 432 为
「唯一可校准参照」。差额 97 = 79 条 one-hot + 18 条全等值——即这些键上取值恰好落到 0 或 1 的
**确定性**情形（例如 k = 0 或 k = n 的 k/n 概率）。本实现把 R5 限定在**非退化**取值，退化者归 R6，
得到 432，与 §3.6 逐键计数完全一致：`incident_real` 109 / `access_allowed` 78 /
`governing_policy` 85 / `requester_role` 115 / `random_line_bulk` 21 / `random_is_long` 13 /
`random_is_deposit` 11。**若按字面谓词实现，R5 = 529、R6 = 3,617，与报告表对不上。**

**冲突 3｜R13 的「232」与字面形态的「234」。** 按「非负权重在正权重子集上等值」字面量，
全语料有 **234** 条。多出的 2 条是**真实取值**而不是占位符：

- `db-jev-distill-v3-6c8e967e`（`yuri_v3`）：`{no_issue 0, minor_deviation .5, reportable .5, emergency 0}`
  ——教师真的把质量放在两个选项上（排除了另两个），是信念不是构造伪影；
- `db-procedural-typed-decisions-de59753c`（`policy_under_uncertainty / governing_policy`）：
  `{p1 .5, p2 0, none_default_deny .5}` ——规则精确算出的后验并列，本身就是「概率」。

报告 §6.3 R13 的括注写的是「open-jev 与 openjev_v2 的并列行」= 201 + 31 = **232**。本实现据此把 R13
限定在**文档明说「并列均分」是构造**的两个来源（E7/E8/E9），另 2 条保留源语义并在 `shape_note`
注明「来源非『并列均分』构造，未降级」，这样四类分布与 §6.3 完全一致。
**若判定应放宽**（只要正权重子集并列就无信息），把 `target_types.py` 的 `_is_tie_construct` 改成
恒真即可：uniform 变 1,964、soft 变 15,917，其余不变，代价是丢掉 2 条真实信息。此判断已登记，等确认。

**冲突 4｜任务书的剔除范围与报告 §5 差 232 条。** 见 §4.4。默认按报告 §5（`drop` = 1,962），
另给 `--ties distill` 一键切回任务书字面口径（`drop` = 1,730）。**需要用户确认默认值。**

**冲突 5｜8,631 条来源自带 one-hot 的 `target_type`。** 任务书要求「标 hard_label」，
报告 §6.3 把它们留在 `soft_distribution`。两者是不同轴：`target_type` 记来源语义，
`training_route` 记损失怎么算。本交付两个都落，训练按硬标签走；若要求 `target_type` 也改成
`hard_label`，四类分布会变成 `hard_label` 14,119 / `soft_distribution` 7,288 / `answer_only` 8,417 /
`uninformative_uniform` 1,962（合计仍是 31,786）——即**会与报告 §6.3 的验收基准（soft 15,919）冲突**，
因此未改，请确认以哪份为准。

**冲突 6｜R1 内部可分得更细。** §6.3 把两个 jev-decisions 单元一起判 `label_trust = behavioral`，
但下钻 `meta.native_source` 后是两个不同东西：128 条 `verified_demonstration`（轨迹里**实际执行**的
动作）与 79 条 `explicit_expected_action`（上游 LLM 标注的**期望**动作）。做 ECE 分层时两者的
「正确」含义不同，建议后续拆成 R1a/R1b。本实现按 §6.3 不拆（保持与报告一致），仅登记。

**其它观察：**

- `benchmark` 里 `answer_only` 只有 61 条（train 5,589 / test 1,845 / validation 922），
  `label_trust = unknown` 在 benchmark 中为 0 条；benchmark 的 `drop` 率 8.4%（202/2,399）高于
  train 的 6.0%（1,170/19,551），做分区间对比时要注意这个偏差。
- `semantics_confidence` 报告 §6.3 没给列，本实现按 §3 各来源的置信度填：
  R9/R10 = `medium`（类别高、**机制未知**，§7 U1；与 §6.5 的示例一致），R3 = `unknown`，其余 `high`。
- `None` 出现在 `meta.native_source` 上（6 个抓取单元没有这个概念），统计时用 `None` 或 `"(native)"` 占位，
  不要与空串混用。

---

## 8. 复算命令

    # 1. 重算旁挂文件并与已落盘逐行比对（语料或规则一变就报错）
    uv run --no-project --offline python datasets/general/target_types.py --verify

    # 2. 分区过滤前后 + 剔除理由计数（两种并列口径）
    uv run --no-project --offline python datasets/general/filter_targets.py
    uv run --no-project --offline python datasets/general/filter_targets.py --ties distill

    # 3. 不变量测试
    uv run --no-project --offline python -m unittest discover -s datasets -p 'test_target_types.py' -q

    # 4. 仓库总验收
    uv run --no-project --offline python tools/check.py

**入库形态**：`datasets/general/data/*.jsonl` 被 `.gitignore` 第 13 行挡住（明文属可复算的大体积派生文件），
所以明文 `data/target-types.jsonl` 本机保留、**压缩版 [target-types.jsonl.gz](data/target-types.jsonl.gz)
入库**——与 `data/splits/*.jsonl(.gz)` 同一套规矩。两版内容逐字节同源（gzip mtime = 0，可复现）。
旁挂文件 31,786 行、明文 15.9 MB、压缩后约 514 KB。

---

## 附：修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-06 | 首版。实现报告 §6 的 R1–R13，落盘 31,786 行旁挂路由；给出三条路由与四分区过滤前后条数；更正 slug 统计口径；登记 6 处规则冲突。 |
