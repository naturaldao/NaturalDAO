# 训练侧过滤与路由（general v0.1）

> **一句话**：`probs` 字段里装着**至少 5 种不同的量**——教师预测分布、规则算出的参考标签、并列选项的均分占位、
> 我们自己用 `point_mass` 造的单点、以及整条子流恒定的常量。训练与评测必须按**语义**分开走，
> 本页给出可直接复跑的过滤清单、分区剩余数与参考实现。
>
> 依据：[target 溯源报告](target-provenance.md) §6 的 R1–R15 规则表；机器可读路由见
> `target-types.jsonl.gz`（**74,853 行**，每条 target 一行；**只含公开分区**，见 §1.1；
> 文件托管在 HF，见 [HF.md](HF.md)）。
> **本页不修改任何语料、不动任何划分。**

---

## 0. 一页结论

> 本节与 §3 的数字是 **v3 语料口径**（31,786 target，含内部保留集），只作历史对照——v4 起
> 分布由生成器从输入语料现算、不再写死。**落盘件只含公开分区**（v5：74,853 行），见 §1.1。

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
| `target-types.jsonl.gz`（HF 托管，见 [HF.md](HF.md)） | 旁挂路由，**74,853 行**，每条 target 一行，**只含公开分区**（§1.1）；明文 `data/target-types.jsonl` 由脚本生成（明文不入库） |
| [target_types.py](target_types.py) | 生成器：实现 R1–R15；自检只断言可推导 / 内部一致的结论（v3 的 §6.3 基线不再当断言） |
| [filter_targets.py](filter_targets.py) | 过滤与路由的参考实现：只读，打印各分区过滤前后条数 |
| [test_target_types.py](test_target_types.py) | 不变量测试（`tools/check.py` 的 unittest discovery 会收进来） |
| 本页 | 过滤与路由规格 |

不变量（由 `target_types.py --verify` 与测试共同保证；**数字一律从输入语料与规则表现算，不写死**）：

1. 连接键 `(item_id, question_key)` 全局唯一；全量扫描 `classified + unregistered == scanned`，
   且未登记来源必须为 0（否则旁挂件会静默缺行，见 §1.1）；
2. 每行的 `target_type` / 语义 / 角色 / 可信度 / 置信度 / 机制未知 / 证据集 == `RULES` 的静态载荷，
   `training_route == _training_route()` 复算，覆盖规则只可能是 R12/R13；
3. `hard_label` ⇔ 转换器旗标 `hard_label_to_point_mass`；
4. **原语料字节不变**：旁挂文件只读语料，不写回；
5. **落盘件只含公开分区**，且**恰好**覆盖「公开分区 ∩ 语料」的每个 target（v5：74,853 条，一条不多、
   一条不少）；白名单外的 target 一条都不出现（§1.1）。

### 1.1 旁挂文件只覆盖公开分区（内部保留集不入库）

旁挂件按 `data/splits/{train,test,validation}` 的 item id **白名单**过滤，只写公开分区的 target。
v5 分区（语料 v4：74,912 条 / 82,843 target）实测：全量扫描 82,843 → 落盘 **74,853**，**7,990 个 target
属于内部保留集、未落盘**（v5 轮换后 benchmark 6,541 条 / 7,990 target；v4 的 8,394 已随轮换作废）。

**口径恒等式（v5）**：旁挂 **74,853** + 中文补充 **3,148** = 公开三分区 target 总数 **78,001**。
中文补充（`db-zhtax-*`，只追加进 train 尾部、不参与切分）不在冻结语料里，因此**不写进旁挂件**——
这是**口径决定**（两类来源不同，硬塞进同一个旁挂件会把 provenance 搅浑），**不是遗漏**；它们全部
`answer_only`，由 `filter_targets.py` 的 `route_of_uncovered` 按形态兜底走 `classification`。

**为什么**：旁挂文件本身不含答案，但它的 `item_id` 列等于一份**成员名单**。v3 的 31,786 行版本里有
3,119 个 id 属于内部 benchmark——配上仍在 git 历史里可达的语料，两者一拼即可精确还原保留集。
换个说法：**成员身份本身就是敏感信息**，说得出「谁在保留集里」就等于交出了保留集。这与
[AGENTS.md](../../AGENTS.md) 的数据边界一致：保留集不进入任何公开分支、fork、PR、日志、截图或
训练 Agent 上下文。

**保留集的路由怎么办**：**不入库，在仓外维护**。仓内生成器只认公开白名单，`--out` 也不改变这一点
（连「读 benchmark 才能排除它」都避免——那等于把成员清单从旁挂文件搬到源码里）；需要保留集路由时，
在仓外按同一套 R1–R15 规则复算，输出不要提交。

**怎么防回流**（三条都盯**内容级**，不是「文件有没有被 git 跟踪」）：

1. [target_types.py](target_types.py) 只认公开分区白名单，分区缺失即报错退出（fail closed），
   绝不退回「全量落盘」；
2. [test_target_types.py](test_target_types.py) 的 `BenchmarkIsolationTest` 分两层断言：层 1
   `item_id ⊆ 公开分区`（需要本地已按 [HF.md](HF.md) 下载并解压的公开分区 `.gz`），层 2 与
   `data/splits/benchmark.jsonl` 的 id 集合**交集为空**（保留集不在本机时跳过）；并用
   「注入必红、未注入必绿」的副本演练自证护栏真的会拦；
3. [filter_targets.py](filter_targets.py) 扫到保留集分区时**不做兜底路由估算**，只要求旁挂文件
   覆盖 0 条——不估算才不会有「看起来合理的错数字」。

§0 / §3 / §4.2 / §4.6 / §7 里出现的全量与保留集数字是 **v3 口径**（保留集路由按本节约定不再入库）。
v4 起条数一律现算；这些表留给后续文档刷新任务统一清理。

**v4 新增来源**：bigbench（25,795 条）与 cosmos_qa（25,262 条）已按 **R14 / R15** 登记（证据 E14 / E15，
见 [target-provenance.md](target-provenance.md) §6.3/§6.4）：两者 `targets` 只有原生金答案、**没有 probs**，
故 `target_type = answer_only`、`training_route = classification`；落盘件里 R14 24,161 条 / R15 23,628 条
（其余在保留集）。

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
| `label_trust` | `rule_exact` \| `teacher_argmax` \| `behavioral` \| `unknown` \| `native_gold` | §6.2。**`native_gold` 是 v4 新增**：上游数据集原生金标签（bigbench / cosmos_qa），不是本仓库规则算出 |
| `mechanism_unknown` | bool | §6.2。只有 6,999 条（R9+R10，报告 §7 U1） |
| `provenance_ref` | string[] | §6.2，对应报告 §6.4 的 E1–E15 |
| `shape_note` | string \| null | §6.2，**仅旁证**，消费者可忽略 |
| `rule_id` | `R1`–`R11` \| `R14` \| `R15` | **新增**：命中的**来源证据**规则号，与 §6.3 逐行对账 |
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

> **口径**：本节是 **v3 全量语料**（31,786 target，含内部保留集）的分布，只作历史对照——v4 起
> 生成器不再对 §6.3 基线做断言，分布一律从输入语料现算。**不等于**已落盘的旁挂件
> （v5 只含公开分区 74,853 行，见 §1.1）。

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

### 4.2 各分区过滤前后（v5 分区；语料 v4 74,912 条 / 82,843 target；+ 中文补充 3,148 = 产品 78,060 条）

| 分区 | items | target 合计 | 剔除 `drop` | 分类 `classification` | 蒸馏 `distillation` | 过滤后保留 |
|---|---:|---:|---:|---:|---:|---:|
| train（语料内） | 45,580 | 49,851 | 1,052 | 44,906 | 3,893 | **48,799** |
| test | 15,194 | 16,641 | 335 | 15,018 | 1,288 | **16,306** |
| validation | 7,597 | 8,361 | 184 | 7,598 | 579 | **8,177** |
| benchmark | 6,541 | 7,990 | 391 | 6,071 | 1,528 | **7,599** |
| **合计** | **74,912** | **82,843** | **1,962** | **73,593** | **7,288** | **80,881** |

**train 分区还有一个尾巴**：[split-manifest.json](data/splits/split-manifest.json) 记的**中文补充**
3,148 条（`db-zhtax-*`，taxonomy 派生，只追加进 train、不参与切分）不在冻结语料里，因此不在旁挂文件里；
它们**全部是 `answer_only`**（没有 `probs`），按同一规则走 `classification`：

| 实际文件 | target 合计 | 剔除 | 分类 | 蒸馏 | 过滤后保留 |
|---|---:|---:|---:|---:|---:|
| `train.jsonl`（语料 train 49,851 + 补充 3,148） | 52,999 | 1,052 | 48,054 | 3,893 | **51,947** |

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

| 口径 | 命令 | 剔除 | 蒸馏 | 过滤后保留（v4 全量） |
|---|---|---:|---:|---:|
| **drop（默认，按报告 §5）** | `filter_targets.py` | 1,962 | 7,288 | 80,881 |
| `distill`（按任务书字面） | `filter_targets.py --ties distill` | 1,730 | 7,520 | 81,113 |

`--ties distill` 下各分区：train 936 / test 294 / validation 156 / benchmark 344 被剔除。

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

`calibration_role = reference_probability` 的 **432** 条（全量；语料 v4 未变，故与 v3 一样仍是 432），分布随 v5 分区：

| 分区 | 条数 |
|---|---:|
| train | 243 |
| test | 71 |
| validation | 43 |
| benchmark | 75 |

按 `meta.native_task`：`partial_observation_calibration` 109 / `policy_under_uncertainty` 278 /
`arithmetic` 45（合计 432）。

报告 §3.6 的 5 个条件仍然适用：只限这 432 条；只在合成世界内成立（是「这个世界发生了 A」的概率，
不是「人类会怎么判」）；模型必须看到与生成器相同的 `state`；**逐 task 分别报告**，不要揉成一个 ECE；
「noise-free」是卡面声明而非我们复核过。

若只需要 ECE（置信度校准）而不需要分布校准，硬标签路线可用面大得多（v4 **全量** classification 73,593 条；
落盘件 67,522；v3 为 22,536 条），但必须用 `label_trust` 分层报告，否则 ECE 的分子分母里混着几类不同来源的「正确」：

| `label_trust` | 条数（v4 全量） | 落盘件（公开分区） | 含义 |
|---|---:|---:|---|
| `rule_exact` | 11,406 | 9,335 | 规则精确算出（procedural / open-jev / systemone-lite） |
| `native_gold` | 51,057 | 47,789 | **v4 新增**：上游数据集的原生金标签（bigbench / cosmos_qa），不是本仓库规则算出 |
| `teacher_argmax` | 8,499 | 6,724 | 教师分布的 argmax（belief，不是正确答案） |
| `unknown` | 7,872 | 7,872 | deepexi 答案来源无文档（报告 §7 U3） |
| `behavioral` | 4,009 | 3,133 | 轨迹里「当时做了什么」，不是「正确答案」（报告 §3.3） |

> 条数一律现算（以 `target_types.py` / `filter_targets.py` 的输出为准）；全量含内部保留集，落盘件只含公开分区。

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

### 6.2 正确口径与数字（v4 全量 14 个 `(slug, native_source)` 组）

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
| `bigbench` | `None` | 25,795 | 25,795 | `none` | `label_only` |
| `cosmos-qa` | `None` | 25,262 | 25,262 | `none` | `label_only` |
| **合计** | | **74,912** | **82,843** | | |

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

- 一条 `yuri_v3` 条目（id 从略，避免暴露内部基准成员）：`{no_issue 0, minor_deviation .5, reportable .5, emergency 0}`
  ——教师真的把质量放在两个选项上（排除了另两个），是信念不是构造伪影；
- 一条 `procedural-typed-decisions` 的 `policy_under_uncertainty / governing_policy` 条目（id 从略）：
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

- `benchmark` 里 `answer_only` 3,364 条（旧来源 96 + 新来源 R14/R15 共 3,268），
  公开三区为 train 37,384 / test 12,480 / validation 6,246（v5 分区口径）；`label_trust = unknown` 在
  benchmark 中为 0 条（benchmark 只收 en，而 unknown 全部来自中文 deepexi）；benchmark 的 `drop` 率
  4.9%（391/7,990）高于 train 的 2.1%（1,052/49,851），做分区间对比时要注意这个偏差。
- `semantics_confidence` 报告 §6.3 没给列，本实现按 §3 各来源的置信度填：
  R9/R10 = `medium`（类别高、**机制未知**，§7 U1；与 §6.5 的示例一致），R3 = `unknown`，其余 `high`。
- `None` 出现在 `meta.native_source` 上（6 个抓取单元没有这个概念），统计时用 `None` 或 `"(native)"` 占位，
  不要与空串混用。

---

## 8. 复算命令

    # 0. 重新生成明文 + HF 发布的 .gz（只有改了规则 / 语料 / 分区才需要跑）
    uv run --no-project --offline python datasets/general/target_types.py \
        --out datasets/general/data/target-types.jsonl \
        --gz-out datasets/general/data/target-types.jsonl.gz

    # 1. 重算旁挂文件并与已落盘逐字节比对（语料、规则或公开分区一变就报错；
    #    自检只断言可推导/内部一致的结论，不再对 §6.3 的硬编码数字）
    uv run --no-project --offline python datasets/general/target_types.py --verify

    # 2. 公开分区过滤前后 + 中文补充 + 剔除理由（§4.3 / §4.4 的数字）
    uv run --no-project --offline python datasets/general/filter_targets.py
    uv run --no-project --offline python datasets/general/filter_targets.py --ties distill

    # 3. 全量分区路由 / 校准 / label_trust 分层 + 全量形态与逐规则计数
    #    （§4.2 的 benchmark 行、§4.6；也覆盖 target-provenance.md §0.2 / §6.3）
    uv run --no-project --offline python datasets/general/target_types.py --by-split --verify

    # 4. 语料构成报告（items.final.report.json 的全部数字）
    uv run --no-project --offline python datasets/general/report_corpus.py

    # 5. 不变量测试
    uv run --no-project --offline python -m unittest discover -s datasets -p 'test_target_types.py' -q

    # 6. 仓库总验收
    uv run --no-project --offline python tools/check.py

**数字来源**：§0 / §3 是 v3 口径（表上已标注，历史对照）；§4 / §6 / §7 由上面 2 / 3 / 4 组命令现算。
`target-provenance.md` §0.2 的全量形态与 §6.3 的逐规则计数，看第 3 组命令输出里
`partitions["全量（含保留集）"]` 的 `shape_class` / `rule_id` 两栏。

**落盘与托管形态**：`datasets/general/data/*.jsonl` 与 `*.jsonl.gz` 都不入仓库（明文属可复算的
大体积派生文件；压缩版由 [export_hf.py](export_hf.py) 发布到 HF 公开仓库，见 [HF.md](HF.md)）。
所以明文 `data/target-types.jsonl` 与 `data/target-types.jsonl.gz` 都在本机保留、由 HF 托管；
两版内容逐字节同源（gzip mtime = 0，可复现）。
旁挂文件 **74,853 行**（只含公开分区，§1.1）、明文 35,419,424 字节（sha256 `87cfa670…`）、
gzip 834,743 字节（sha256 `19f63155…`）；每行是 canonical JSON（键序排序、默认分隔符），
所以 `--verify` 能与本机旁挂件**逐字节**比对。

**分区白名单**：`target_types.py` 默认从 `data/splits` 取 `train/test/validation` 的 item id 作白名单
（`--splits` 可换目录）。任一公开分区缺失即报错退出，**不会**退回全量落盘；因此重算要求分区在位——
先从 HF 公开仓库下载三个分区的 `.jsonl.gz` 并解压到 `data/splits/`（见 [HF.md](HF.md)）。

**覆盖自检**（不写盘前就报错，不能用 `--skip-self-check` 绕过）：落盘件的连接键集合必须**恰好**等于
「公开分区 target 键 ∩ 语料 target 键」——少一条说明有 target 没有路由（训练会静默落到兜底路由），
多一条说明路由指认了不在公开分区的 target（泄漏风险）。

---

## 附：`label_confidence`（mercury 补全线的标签互证标记）

> 本节由 Jev 补全线（2026-10-20）加入，只新增这一节 + 一行修订记录，不改本页其他内容。

旁挂文件 `datasets/general/data/jev-probs.jsonl`（明文不入库；压缩版 `jev-probs.jsonl.gz` 由 HF 公开仓库托管，见 [HF.md](HF.md)，
**公开三区 44,740 行**（v5）；本地全量 48,503 行，剔除了 3,763 条 benchmark / 私有保留集成员——原因同 §1.1：
sidecar 的 `id` 列等于成员名单）里，**两条 mercury 线**（noul 升级线 + answer-only choice 补全线）的条目都额外带三个字段：

| 字段 | 含义 |
|---|---|
| `label_confidence` | `high_consensus` / `medium_consensus` / `low_consensus` / `insufficient_sample` |
| `consensus_agree` / `consensus_n` | 该 config 上「mercury 判断 == 语料 answer」的条数 / 已调用条数 |

判定：双方一致率 ≥95% → `high_consensus`；70–95% → `medium_consensus`；<70%（且 n≥10）→ `low_consensus`；
n<10 → `insufficient_sample`。机器可读总表：[label-confidence.json](data/jev/label-confidence.json)
（noul 线按 **source dataset** 分组、choice 线按 **question key** 分组；两线分开统计）。

**用法**（公开三区交付件：`low_consensus` **1,880** / `medium_consensus` **35,869** / `high_consensus` **6,991**；
全量含保留集时为 2,026 / 38,890 / 7,587）：
- `low_consensus`（交付件 1,880 条）：该子集标签**未经双方互证**，训练时应降权或标记复核。
  **它是「未互证」，不是「标签错了」**——不要据此直接删除。
- `high_consensus`（交付件 6,991 条）：双方互证，可正常使用。
- 典型：`intersect_geometry`（一致率 **20.1%**）与 `tracking_shuffled_objects`（48.6%）整批标 `low_consensus`，
  建议优先人工抽查——这同时是**关于来源标签质量**的信号。

**三条线的互证率**：
- **noul**（按 source dataset）：Open-Jev 99.9%、procedural 90.4%、system-one 89.2%、jev-distill 72.6%；
  **全部 ≥ 70%，无 `low_consensus`**。
- **choice**（按 question key，33 个 config）：多数 70–95%；5 个 config < 70%（见上）。
- **jev-router zh choice**（旧方案）：argmax 一致率 **99.15%**（1,867/1,883）→ `high_consensus`。
  **注意**：它的写入率只有 44.7%，但被拒的 1,026 条绝大多数是**输出退化成伪 one-hot**（判断其实与语料一致）——
  这条线的问题是**分布质量**、不是标注一致性；选分布做训练时仍要按写入门禁来。

**补全对「可用软分布」的贡献**（README §4.4 口径，分母 = 公开件 74,853 + 补充集 3,148 = 78,001）：
采用旁挂 probs 后，可用软分布从 **5,945（7.62%）** 升到 **48,941（62.74%）**，其中 42,996 条是本轮新补的
（v4 语料时为 5,905（7.61%）→ 48,715（62.78%）；v5 轮换后口径同步更新）。
**注意**：新补的是「双方一致」子集（选择偏差），不是随机抽样。

**注意（选择偏差）**：这批软分布**只在双方一致时写入**，因此是「一致子集」而非随机子集；
详见 [jev-validation.md](jev-validation.md) §8.5。

---

## 附：修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-06 | 首版。实现报告 §6 的 R1–R13，落盘 31,786 行旁挂路由；给出三条路由与四分区过滤前后条数；更正 slug 统计口径；登记 6 处规则冲突。 |
| 2026-10-15 | 旁挂文件切到**只含公开分区**（31,786 → 28,667；3,119 个内部保留集 target 不再落盘，见 §1.1）：生成器改公开分区白名单 + fail closed + canonical JSON；测试改为推导式期望并加内容级护栏（两层 + 注入演练）；`filter_targets.py` 不再对保留集做兜底路由估算；`--ties` 计数随之更新为 1,809 / 6,648 / 20,210。 |
| 2026-10-20 | **v4 语料**（74,912 条 / 82,843 target；并入 bigbench 25,795 + cosmos_qa 25,262）重算旁挂件：**74,449 行**（公开三分区），保留集 8,394 条未落盘。新增 **R14 / R15**（上游金标签、无 probs → `answer_only` / `classification`，证据 E14 / E15）；`label_trust` 新增 **`native_gold`**（字段语义准确性优先：上游金标签不是本仓库规则算出，用 `rule_exact` 会系统性低估；R14/R15 共 47,707 行）。写明**口径恒等式 74,449 + 3,148 = 77,597**（补充集不进旁挂件是口径决定、不是遗漏，见 §1.1）。自检删掉全部硬编码基线、改为推导式断言 + 覆盖断言；`--gz-out` 一次写明文与入库 .gz；公开面审计（`split.py --audit-public-surface`）id/正文零命中。 |
| 2026-10-20 | **文档按 v4 语料重算（task-10）**：§4.2 / §4.4 / §4.6 / §6.2 / §7 全部换成 v4 实测（分区表 74,912 条 / 82,843 target；ties 口径 80,881 / 81,113；校准分区 218 / 89 / 34 / 91；label_trust 全量与落盘件两列；14 个 `(slug, native_source)` 组）。`items.final.report.json` 改由新脚本 [report_corpus.py](report_corpus.py) 现算重生成；生成器加 `--by-split`，使每个分区数字都有对应复算命令（§8）。|
| 2026-10-20 | 新增「`label_confidence`（mercury 补全线的标签互证标记）」一节：说明旁挂 `data/jev-probs.jsonl` 里 choice 条目的 `label_confidence` / `consensus_agree` / `consensus_n` 字段与判定阈值，指向 [label-confidence.json](data/jev/label-confidence.json)。本节由 Jev 补全线加入，不改其他内容。 |
| 2026-10-20 | **v5 分区轮换**（jev-probs 事故：1,621 个 benchmark id 写入仓外永久排除名单、v4 benchmark 作废；四区改为 train 48,728 / test 15,194 / validation 7,597 / benchmark 6,541）：按 v5 公开三区重生成旁挂件 → **74,853 行**，保留集 **7,990** 条未落盘（v4 的 8,394 作废）；口径恒等式 **74,853 + 3,148 = 78,001**。§4.2 分区表 / §4.4 ties / §4.6 校准分区 / label_trust 落盘件列 / §7 benchmark 行随 v5 更新；§8 指纹改为明文 `87cfa670…` / gz `19f63155…`。旧 v4 旁挂件曾与 v5 benchmark 相交 4,205 个 id，重生成后交集为 0。 |
| 2026-10-22 | 大文件离仓：分区与旁挂件的 `.gz` 改由 Hugging Face 托管（[HF.md](HF.md)），本页指向本地文件的链接改为指向 [HF.md](HF.md) / 清单；数字未变。 |
