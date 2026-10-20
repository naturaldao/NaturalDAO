# 最终切分报告（v4：6:2:1:1，按请求分组，benchmark 来源均衡）

本报告只含聚合统计，**不含任何样本内容**；内部 benchmark 的条目只存在于 data/splits/benchmark.jsonl(.gz) 与 data/splits/benchmark-dataset/，请勿提交到公开仓库，请上传 Hugging Face 并设为 private。

- 随机种子：20261005
- 切分比例：train=0.6, test=0.2, validation=0.1, benchmark=0.1
- 输入文件：1 个
  - datasets/general/data/items.final.jsonl：74912 条
- 切分语料条目总数：74912；请求组 60711 个
- 语料来源：本轮输入是**合并后的主语料**；合并台账（各增量来源、id 前缀、sha256）由 data/splits/build_corpus.py 生成并保管在仓外（本报告 §3 只有来源构成聚合）
- train-only 降级补充：3148 条（datasets/general/data/zh-supplement/items.jsonl 3148 条）；只追加 train，不进 test/validation/benchmark
- 产物条目总数（含补充）：78060 条
- **口径注记（与立项数字的差异）**：立项时写的「25,405 + 51,057 = 76,462」把**公开三区产物**（含 3,148 中文补充、不含 benchmark 1,598）当成了切分语料。正确口径：切分语料 = 23,855 + 51,057 = **74,912**，产物 = 74,912 + 3,148 = **78,060**（差 1,550 = 3,148 − 1,598）。本报告一律按**切分语料**口径统计，产物条数单列。
- 保密：本次运行使用 仓外私盐（盐值不记录、不派生进任何公开产物）
- benchmark 语言白名单：en（白名单外的语言只进 train/test/validation，且必须显式排除并写明理由）

## 1. 切分算法

1. **分组**（并查集）：显式分组键（item.group_id / source.group_id / meta.group_id / source.request_id / meta.request_id）与**归一化 state**（去空白、压缩空白、大小写折叠）各自连边；同一分量的所有条目整组进同一分区，绝不按行切。
   - 显式分组键 8664 条；无显式键（靠 state 或 id 兜底）66248 条
   - 组数 60711；多条目组 9710 个；最大组 10 条；跨多个 state 的组 0 个；含多个显式分组 id 的组 0 个
   - 无 state 的条目 0 条；state 分组：开启
   - 中文侧分组 id 门禁（zh）：已通过
2. **分层**：按 (domain, lang) 分层；层内组按种子洗牌，其余组按 6:2:1 用「目标条数 - 已分配条数」最大缺口贪心分配；benchmark 的来源配额在**每个来源内部**再按 (domain, lang) 分层取，保证每个来源的切片仍是它自己的自然分布。
3. **benchmark 来源均衡（硬约束）**：先按比例算目标条数，再用水位法给每个来源分配配额——任一来源占比 ≤ max_source_share（硬上限，交付用 25%），每个来源 ≥ max(min_source_share, min_source_items)（占比下限与**绝对条数下限**取大：语料变大后 5% 会变成几百条，足以把小来源抽干，所以下限用绝对条数）；选择时逐组复核硬上限，组粒度最多差一条组。上限不可行（来源数太少）时放宽到可行界 1/来源数并如实标注。
4. **benchmark 保底**：对每个 lang x kind、每个 domain、每个 lang 设下限，不足时从其余组整组补足；该类总量不足下限、或被来源上限挡住时在下表标「是」。
   - 本次配额：目标 6703 条；上限折算 1675 条（政策上限）；下限 100 条；可进 benchmark 的来源 8 个
5. **确定性**：随机数全部来自 random.Random("公开种子|盐token|阶段|…")（无盐时 token 为固定标记 public-demo）；分区内条目按 id 排序，补充集按文件顺序追加在 train 末尾；gzip 以 mtime=0 写入 → 同一输入 + 同一私盐重跑逐字节一致。
6. **默认值防误伤**：--out/--report 没显式给出而目标位置已有交付件时直接拒绝（退出 3），想覆盖必须显式给路径或加 --force；裸跑不会把已交付的四区或公开报告换掉。
7. **公开引用排除（--exclude-public-items）**：扫描被 git 跟踪的**手写公开文件**（301 个），把其中引用过的条目 id 对应条目整组排除出 benchmark 候选——本轮排除 8 条（5 组）。「被公开引用过的条目永不进盲测集」由机器保证，不靠人工维护文档。派生产物（分区、target-types 侧挂文件）不在扫描范围内，它们切分后会被重新生成。

## 2. 分区规模

| 分区 | 切分语料条目 | 占比 | 目标占比 | 请求组 | 产物条目（含补充） |
|---|---:|---:|---:|---:|---:|
| train | 45472 | 60.7% | 60% | 45472 | 48620 |
| test | 15157 | 20.2% | 20% | 15157 | 15157 |
| validation | 7579 | 10.1% | 10% | 7579 | 7579 |
| benchmark | 6704 | 8.9% | 10% | 6704 | 6704 |

> **三处刻意的偏离，别当成 bug**：
> 1. **train 高于 60%**：按裁定只向 train 追加了降级补充集（3148 条，origin != source，仅 train）；切分语料 74912 条 → 产物 78060 条。
> 2. **benchmark 低于 10%**：本轮只允许 en 进 benchmark（排除的语言见第 10 节），目标条数是**可进 benchmark 那部分语料**的 10%。
> 3. **benchmark 的语言构成与公开三区不同**，因此第 4.4 节 benchmark 一行的分层漂移必然偏大；这是刻意的覆盖取舍，不是分层失效。

## 3. 数据成色与已知缺口（用户决策必读）

| 语言 | 条目 | 覆盖的 kind | 来源数 | 最大来源占比 |
|---|---:|---|---:|---:|
| en | 67040 | choice, noul, score | 8 | 38% |
| zh | 7872 | choice | 1 | 100% |

### 3.1 语料来源构成（合并后，聚合）

| 来源 dataset | 条目 | 占语料 | 进 benchmark | 占 benchmark |
|---|---:|---:|---:|---:|
| tasksource/bigbench | 25795 | 34.4% | 1675 | 25.0% |
| allenai/cosmos_qa | 25262 | 33.7% | 1675 | 25.0% |
| Deepexi/openai-formate-function-calling-small | 7872 | 10.5% | 0 | 0.0% |
| SargeDev/jev-distill-corpus-v3 | 7756 | 10.4% | 1626 | 24.3% |
| samatv256/jev-decisions-v1 | 4009 | 5.4% | 838 | 12.5% |
| tasksource/procedural-typed-decisions | 1500 | 2.0% | 314 | 4.7% |
| dwidlee/systemone-lite-general | 1479 | 2.0% | 310 | 4.6% |
| ZefanCai/Open-Jev | 792 | 1.1% | 166 | 2.5% |
| kaivoss/system-one-270m-data | 447 | 0.6% | 100 | 1.5% |

| kind | 出现在哪些语言 |
|---|---|
| choice | en, zh |
| noul | en |
| score | en |

- **noul 只来自 en**，zh 侧没有 noul 形态的原生数据。
- **score 只来自 en**，zh 侧没有 score 形态的原生数据。
- **zh 侧只有单一来源** Deepexi/openai-formate-function-calling-small（7872 条，占全语料 11%）——低于契约 40% 上限，但**没有第二来源兜底**，跨来源去偏能力有限，训练决策请按单一来源对待。
- 可选补强路径：中文 noul/score 目前没有原生来源；task-14 的中文分类衍生池（42,436 条，单标签 + documented 映射，**非原生四元组**）可作补强，属成色降级，需用户确认后另行引入——**本轮未引入**。

## 4. 分布（每区内部占比）

> 本节占比按**切分语料**算：train 列不含追加的 3,148 条降级补充（补充的语言/原语/origin 构成见第 11 节）。
### 4.1 lang

| lang | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| en | 40224 (88%) | 13408 (88%) | 6704 (88%) | 6704 (100%) |
| zh | 5248 (12%) | 1749 (12%) | 875 (12%) | 0 (0%) |

### 4.2 domain

| domain | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| decision_mechanics | 11352 (25%) | 3784 (25%) | 1892 (25%) | 2437 (36%) |
| knowledge_reasoning | 34120 (75%) | 11373 (75%) | 5687 (75%) | 4267 (64%) |

### 4.3 kind

| kind | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| choice | 42352 (93%) | 14070 (93%) | 7025 (93%) | 5425 (81%) |
| noul | 3443 (8%) | 1226 (8%) | 609 (8%) | 1389 (21%) |
| score | 1897 (4%) | 678 (4%) | 340 (4%) | 810 (12%) |

### 4.4 分层漂移（各区内 (domain, lang) 占比 vs 全局占比）

| 分区 | 最大占比差 | 该层 |
|---|---:|---|
| train | 2.1% | decision_mechanics/en |
| test | 2.0% | decision_mechanics/en |
| validation | 2.1% | decision_mechanics/en |
| benchmark | 20.9% | decision_mechanics/en |

## 5. benchmark 保底配额

| 单元 | 下限 | 实际 | 该类不足（取全部） |
|---|---:|---:|---|
| domain=decision_mechanics | 100 | 2437 | 否 |
| domain=knowledge_reasoning | 100 | 4267 | 否 |
| lang=en | 100 | 6704 | 否 |
| lang=en,kind=choice | 100 | 5429 | 否 |
| lang=en,kind=noul | 100 | 1389 | 否 |
| lang=en,kind=score | 100 | 814 | 否 |

## 6. 泄漏检查（必须为空）

- 跨分区的组：0
- 跨分区的同一 state：0
- 跨分区的 id：0
- 复核范围：60711 组 / 60711 个不同 state
- 结论：**空**（按组切分 + state 合并后无任何跨区）。

## 7. benchmark 来源均衡（硬约束）

- 上限：任一来源占 benchmark ≤ **25%**（本次折算 1675 条；策略=政策上限，可行界 838 条）
- 下限：每个来源 ≥ **占比下限 1% 与绝对下限 100 条取大** = 100 条（来源池不足时取全部）
- 实际：8 个来源可进 benchmark；最大来源 tasksource/bigbench 占 25.0%；最小来源 100 条；硬上限满足：是

**为什么把上限定在 25%**：本次有 8 个来源可进 benchmark。25% 上限意味着单一来源最多 1675 条、且数学上至少 4 个来源才能凑满 100%——任一来源都无法单独决定总分，这是「不被单一来源绑架」的下限保证；同时它还留出约 15 个百分点的余量给政策调整（契约参考线 40%）。下限用「绝对条数」而不是固定占比：语料从 2.4 万涨到 7.5 万后，5% 会从 80 条变成 300+ 条，足以把小来源抽干；用绝对条数（本次 100 条）才能同时满足「每个来源都有切片」和「不把小来源抽干」。

**来源覆盖 vs 占比失真（必读）**：语料里最大的两个来源合计占可进benchmark 语料的 76.2%，但受 25% 上限约束，它们在 benchmark 里合计只占 50.0%；其余 6 个来源占语料 23.8%，却在 benchmark 里占 50.0%（放大约 2.1 倍）。这是「必须覆盖原语料来源」的直接代价：若按自然比例，新涌入的能力语料会把benchmark 的大头占掉。因此 benchmark 的**总分不能当语料自然分布的无偏估计**，必须按来源分层报；要更接近自然比例就放宽 --benchmark-max-source-share。

- **内容重叠剔除**：1 个保留组的 state 正文被公开侧某个条目的 state 完整包含（检查 6705 个保留条目的 state，含 293 个常见词兜底扫描），已整组移出 benchmark——正文已公开的条目不能当盲测成员。典型来源：bigbench question_selection 把 cosmos 的整段 context 嵌进 state，而旧 Jev 语料里有条目的 state 恰好就是那段 context。

| dataset | revision | license | 条目 | 占 benchmark | 占语料 | 该来源池子 | 取用率 |
|---|---|---|---:|---:|---:|---:|---:|
| allenai/cosmos_qa | 28d9d5e2aae0 | cc-by-4.0 | 1675 | 25.0% | 37.7% | 25262 | 6.6% |
| tasksource/bigbench | 210c156767d2 | apache-2.0 | 1675 | 25.0% | 38.5% | 25795 | 6.5% |
| SargeDev/jev-distill-corpus-v3 | fc99c6357a9f | apache-2.0 | 1626 | 24.3% | 11.6% | 7755 | 21.0% |
| samatv256/jev-decisions-v1 | c12aadf1f01c | cc-by-4.0 | 838 | 12.5% | 6.0% | 4003 | 20.9% |
| tasksource/procedural-typed-decisions | 609513a3fadd | apache-2.0 | 314 | 4.7% | 2.2% | 1499 | 20.9% |
| dwidlee/systemone-lite-general | c14eb7f7518f | mit | 310 | 4.6% | 2.2% | 1479 | 21.0% |
| ZefanCai/Open-Jev | c67699e13d0a | cc0-1.0 | 166 | 2.5% | 1.2% | 792 | 21.0% |
| kaivoss/system-one-270m-data | f31d5a3f3da8 | apache-2.0 | 100 | 1.5% | 0.7% | 447 | 22.4% |

> 取用率 = 该来源进 benchmark 的条数 / 它在这个语言白名单下的全部可用条数。「占语料」= 该来源在可进 benchmark 语料里的占比。两者对比可以看出谁被放大、谁被压制。


## 8. 产物

- data/splits/train.jsonl（+.gz）：48620 条（含补充 3148 条）
- data/splits/test.jsonl（+.gz）：15157 条
- data/splits/validation.jsonl（+.gz）：7579 条
- data/splits/benchmark.jsonl（+.gz）：6704 条（**内部，勿公开**）
- data/splits/benchmark-dataset/：可直接上传私有托管的内部 benchmark（README.md 数据卡 + USAGE.md + benchmark.jsonl(.gz) + manifest.json + verify.py）
- data/splits/split-manifest.json：各产物 sha256 与复跑校验结果（机器可读）

## 9. 可复现性（两次运行逐字节一致）

- 随机种子：20261005；同一输入 + 同一种子 + 同一私盐 + **同一份公开面** → 同一分组、同一分配、同一顺序。
- 注意：启用 --exclude-public-items 时，「可进 benchmark 的条目集合」还取决于**当前被 git 跟踪的手写公开文件**——若在切分之后有人新增/修改了引用条目 id 的文档，重跑出来的 benchmark 会随之变化。这是「被公开引用过的条目永不进盲测集」的代价，也是每次重切必须重跑公开面审计的原因。
- 本次命令（输出路径与盐路径用占位符，实际路径见第 8 节）：`uv run --no-project --offline python datasets/general/data/splits/split.py --out <OUT_DIR> --report <REPORT_PATH> --seed 20261005 --salt-file <仓外私盐> --benchmark-lang en --benchmark-exclude-lang "zh=中文答案以 (group_id → 正确工具) 索引形式仍在公开 git 历史里可达（实测覆盖 5454/5454 组 = 100%），换盐/换种子都挡不住，zh 分项分数不具盲测意义；恢复条件：接入全新中文来源，或由维护者协调重写仓库历史清除该索引" --benchmark-min-source-share 0.01 --benchmark-min-source-items 100 --exclude-public-items --derived-skip datasets/general/data/target-types.jsonl.gz --train-supplement datasets/general/data/zh-supplement/items.jsonl`
- 分区内条目按 id 排序；gzip 以 mtime=0 写入（gzip 头不含时间戳，否则两次压缩不会逐字节相同）。
- 输出把裸 U+2028 / U+2029 / U+0085 统一写成 \uXXXX 转义（无损）：它们在 JSON 里合法，但用 str.splitlines() 读会被当成换行、把记录劈开。
- 本次运行额外完整复跑一遍（重新读文件、重新分组、重新分配、重新打包）并写到独立临时目录，比对 14 个产物文件：**逐字节一致**。
- 产物树哈希（sha256 over 文件名+文件哈希）：d087d29a7fb82d4ff13bc0a7a33c56e4abf80311df6c519f8be993ef2e70607f
- 比对范围：train.jsonl、train.jsonl.gz、test.jsonl、test.jsonl.gz、validation.jsonl、validation.jsonl.gz、benchmark.jsonl、benchmark.jsonl.gz、benchmark-dataset/README.md、benchmark-dataset/USAGE.md、benchmark-dataset/benchmark.jsonl、benchmark-dataset/benchmark.jsonl.gz、benchmark-dataset/manifest.json、benchmark-dataset/verify.py

## 10. 保密：私盐 + 语言政策 + 版本

### 10.1 私盐挡什么、不挡什么（如实披露）

- 交付件的所有随机种子都折进**仓外私盐**文件的 sha256 前 16 位；盐值与盐的哈希都不写进任何产物。
- **私盐挡的是**：用公开脚本 + 公开语料 + 公开种子**直接重跑切分**来复现 benchmark——无盐（--public-demo）跑出来的是**另一套**分配。
- **私盐不挡的是**：重建语料后做减法。公开三区（train/test/validation）是**全量发布**的，而本语料 68% 来自公开 HF 数据集 + 公开转换脚本；任何人若能按公开脚本重建出同一份语料，就可以用「语料 − 公开三区 = benchmark」直接算出成员身份，**不需要盐、也不需要重跑切分**。这条路径在旧语料上就存在，新能力语料（公开来源占比更高、转换参数公开）让它更强。
- 因此本 benchmark 的定位是「**防止随手复现**」，**不是**「对决心攻击者保密」。若要用于真正的盲测/对抗性评测，评测方应另行持有**未公开的额外留出集**（不复用本 benchmark），或先把公开三区改成只发抽样/校验和。
- 护栏（test_split.py 的 SecrecyTest 每次运行都验）：两个不同盐 → benchmark 不同；同盐两次 → 完全一致；无盐 public-demo 与交付件不同；盐文件在仓库内 / 无盐且非 demo / demo 写到仓库内 → 均拒绝（非零退出）。这些护栏保证的是「没有私盐就分不出交付件」，不保证「有语料就能守住成员身份」——见上面第 3 条。

### 10.2 语言政策：每种语言都必须显式声明

- 切分语料里出现的语言：en, zh
- 允许进 benchmark：en
- **显式排除**（--benchmark-exclude-lang）：
  - zh：中文答案以 (group_id → 正确工具) 索引形式仍在公开 git 历史里可达（实测覆盖 5454/5454 组 = 100%），换盐/换种子都挡不住，zh 分项分数不具盲测意义；恢复条件：接入全新中文来源，或由维护者协调重写仓库历史清除该索引
- 机制：run() 要求语料里每种语言要么在 --benchmark-lang 里，要么在--benchmark-exclude-lang 里带非空理由；漏一种直接拒绝切分（退出 3）。所以「benchmark 少了一整种语言」永远是**会报错的显式状态**，不是沉默的事实——恢复条件一满足，去掉排除项即可翻回来。

### 10.3 版本：v1 作废，v2 / v3 / v4 不可拼接

| 版本 | 内容 | 状态 |
|---|---|---|
| v1 | 公开种子、**无盐**；benchmark 2,389 条（含 zh 789） | **作废**：可用公开脚本 + 语料 + 种子逐字节重建（benchmark sha256 43937e09a6fdde62…） |
| v2 | 私盐 + 只允许 en 进 benchmark；benchmark 1,600 条，单一来源占 47.1% | 已被 v3 取代（benchmark sha256 f5ae670811c33200…） |
| v3 | 私盐 + en-only + 来源均衡（≤25% 上限 / 5% 下限）；语料 23,855 条；benchmark 1,598 条 | 已被 v4 取代 |
| **v4（本次）** | 语料合并 51,057 条能力语料（23,855 + 51,057 = 74,912）+ 私盐 + en-only + 来源均衡（≤25%，8 个来源，绝对下限 100 条）+ 公开引用排除 + train 回灌降级补充 | 现行交付件；benchmark 6704 条，哈希见第 9 节与 split-manifest.json |

**v1 / v2 / v3 / v4 的 benchmark 是四套不同的条目集合，分数不可拼接、不可混用。**

### 10.4 公开面零命中

- 护栏：SecrecyTest 逐个扫描**所有被 git 跟踪的文件**（`.gz` 解压后），对 benchmark 的**条目 id** 与**正文**（条目级唯一的 state 原文；完整条目行必然含 id，由 id 口径覆盖）两种口径都要求零命中；benchmark 分区与 benchmark-dataset/ 都在 .gitignore（benchmark*）。
  - 本次运行的公开面审计：对全部被跟踪文件（.gz 解压后）扫描，指纹 6704 条 id / 5949 条正文 → 零命中；可用 --audit-public-surface 单独复跑（命中则退出 1，并打印文件名）。（不记录文件个数：仓库增删文件会让它变化，而重跑一致性要求产物只由输入与盐决定。）
  - 为什么要两种口径：文件级检查（有没有被 git 跟踪）挡不住**内容级**泄漏——曾经有派生索引文件把 benchmark 的全部 id 列在里面（本身不含答案，但能精确指认成员）；压缩流里的泄漏也只有解压后才看得见。
- 语料、中文答案索引等含 benchmark 正文/答案的文件已移出版本控制（仓外留存）；但**删除不改变 git 历史**——zh 的 (group_id → 正确工具) 索引仍在历史里可达，这正是 zh 不进 benchmark 的原因（见 10.2 的排除理由）。
- 本报告、数据卡、manifest 都只含聚合统计；test_split.py 与 test_benchmark_package.py 有对应断言，benchmark 包 verify.py 另有独立校验。

## 11. origin 构成（原生 vs 降级）

| 分区 | origin=source（原生） | origin=taxonomy 等（降级） | 其它/未标 |
|---|---:|---:|---:|
| train | 45472 | 3148 | 0 |
| test | 15157 | 0 | 0 |
| validation | 7579 | 0 | 0 |
| benchmark | 6704 | 0 | 0 |

| 语言 | origin | 条目 | 落在哪些分区 |
|---|---|---:|---|
| en | source | 67040 | benchmark 6704, test 13408, train 40224, validation 6704 |
| zh | source | 7872 | test 1749, train 5248, validation 875 |
| zh | taxonomy | 3148 | train 3148 |

- origin=source 是来源原生四元组（A 层，可进 benchmark）；taxonomy 等是降级派生（B 层，只进 train）。benchmark 只含 A 层。
