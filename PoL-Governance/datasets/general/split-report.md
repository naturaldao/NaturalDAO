# 最终切分报告（v3：6:2:1:1，按请求分组，benchmark 来源均衡）

本报告只含聚合统计，**不含任何样本内容**；内部 benchmark 的条目只存在于 data/splits/benchmark.jsonl(.gz) 与 data/splits/benchmark-dataset/，请勿提交到公开仓库，请上传 Hugging Face 并设为 private。

- 随机种子：20261005
- 切分比例：train=0.6, test=0.2, validation=0.1, benchmark=0.1
- 输入文件：1 个
  - datasets/general/data/items.final.jsonl：23855 条
- 切分语料条目总数：23855；请求组 21376 个
- train-only 降级补充：3148 条（datasets/general/data/zh-supplement/items.jsonl 3148 条）；只追加 train，不进 test/validation/benchmark
- 产物条目总数（含补充）：27003 条
- 保密：本次运行使用 仓外私盐（盐值不记录、不派生进任何公开产物）
- benchmark 语言白名单：en（白名单外的语言只进 train/test/validation，且必须显式排除并写明理由）

## 1. 切分算法

1. **分组**（并查集）：显式分组键（item.group_id / source.group_id / meta.group_id / source.request_id / meta.request_id）与**归一化 state**（去空白、压缩空白、大小写折叠）各自连边；同一分量的所有条目整组进同一分区，绝不按行切。
   - 显式分组键 8664 条；无显式键（靠 state 或 id 兜底）15191 条
   - 组数 21376；多条目组 2479 个；最大组 2 条；跨多个 state 的组 0 个；含多个显式分组 id 的组 0 个
   - 无 state 的条目 0 条；state 分组：开启
   - 中文侧分组 id 门禁（zh）：已通过
2. **分层**：按 (domain, lang) 分层；层内组按种子洗牌，其余组按 6:2:1 用「目标条数 - 已分配条数」最大缺口贪心分配；benchmark 的来源配额在**每个来源内部**再按 (domain, lang) 分层取，保证每个来源的切片仍是它自己的自然分布。
3. **benchmark 来源均衡（本轮新增，硬约束）**：先按比例算目标条数，再用水位法给每个来源分配配额——任一来源占比 ≤ max_source_share（默认 25%），每个来源 ≥ min_source_share（默认 5%，「各个来源都收集一点」）；选择时逐组复核硬上限，组粒度最多差一条组。上限不可行（来源数太少）时放宽到可行界 1/来源数并如实标注。
4. **benchmark 保底**：对每个 lang x kind、每个 domain、每个 lang 设下限，不足时从其余组整组补足；该类总量不足下限、或被来源上限挡住时在下表标「是」。
   - 本次配额：目标 1598 条；上限折算 399 条（政策上限）；下限 79 条；可进 benchmark 的来源 6 个
5. **确定性**：随机数全部来自 random.Random("公开种子|盐token|阶段|…")（无盐时 token 为固定标记 public-demo）；分区内条目按 id 排序，补充集按文件顺序追加在 train 末尾；gzip 以 mtime=0 写入 → 同一输入 + 同一私盐重跑逐字节一致。
6. **默认值防误伤**：--out/--report 没显式给出而目标位置已有交付件时直接拒绝（退出 3），想覆盖必须显式给路径或加 --force；裸跑不会把已交付的四区或公开报告换掉。

## 2. 分区规模

| 分区 | 切分语料条目 | 占比 | 目标占比 | 请求组 | 产物条目（含补充） |
|---|---:|---:|---:|---:|---:|
| train | 14838 | 62.2% | 60% | 14838 | 17986 |
| test | 4946 | 20.7% | 20% | 4946 | 4946 |
| validation | 2473 | 10.4% | 10% | 2473 | 2473 |
| benchmark | 1598 | 6.7% | 10% | 1598 | 1598 |

> **三处刻意的偏离，别当成 bug**：
> 1. **train 高于 60%**：按裁定只向 train 追加了降级补充集（3148 条，origin != source，仅 train）；切分语料 23855 条 → 产物 27003 条。
> 2. **benchmark 低于 10%**：本轮只允许 en 进 benchmark（排除的语言见第 10 节），目标条数是**可进 benchmark 那部分语料**的 10%。
> 3. **benchmark 的语言构成与公开三区不同**，因此第 4.4 节 benchmark 一行的分层漂移必然偏大；这是刻意的覆盖取舍，不是分层失效。

## 3. 数据成色与已知缺口（用户决策必读）

| 语言 | 条目 | 覆盖的 kind | 来源数 | 最大来源占比 |
|---|---:|---|---:|---:|
| en | 15983 | choice, noul, score | 6 | 49% |
| zh | 7872 | choice | 1 | 100% |

| kind | 出现在哪些语言 |
|---|---|
| choice | en, zh |
| noul | en |
| score | en |

- **noul 只来自 en**，zh 侧没有 noul 形态的原生数据。
- **score 只来自 en**，zh 侧没有 score 形态的原生数据。
- **zh 侧只有单一来源** Deepexi/openai-formate-function-calling-small（7872 条，占全语料 33%）——低于契约 40% 上限，但**没有第二来源兜底**，跨来源去偏能力有限，训练决策请按单一来源对待。
- 可选补强路径：中文 noul/score 目前没有原生来源；task-14 的中文分类衍生池（42,436 条，单标签 + documented 映射，**非原生四元组**）可作补强，属成色降级，需用户确认后另行引入——**本轮未引入**。

## 4. 分布（每区内部占比）

### 4.1 lang

| lang | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| en | 9590 (65%) | 3197 (65%) | 1598 (65%) | 1598 (100%) |
| zh | 5248 (35%) | 1749 (35%) | 875 (35%) | 0 (0%) |

### 4.2 domain

| domain | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| decision_mechanics | 12064 (81%) | 4021 (81%) | 2011 (81%) | 1369 (86%) |
| knowledge_reasoning | 2774 (19%) | 925 (19%) | 462 (19%) | 229 (14%) |

### 4.3 kind

| kind | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| choice | 11053 (74%) | 3657 (74%) | 1850 (75%) | 1255 (79%) |
| noul | 3982 (27%) | 1329 (27%) | 661 (27%) | 695 (43%) |
| score | 2163 (15%) | 747 (15%) | 357 (14%) | 458 (29%) |

### 4.4 分层漂移（各区内 (domain, lang) 占比 vs 全局占比）

| 分区 | 最大占比差 | 该层 |
|---|---:|---|
| train | 2.7% | decision_mechanics/en |
| test | 2.7% | decision_mechanics/en |
| validation | 2.7% | decision_mechanics/en |
| benchmark | 37.1% | decision_mechanics/en |

## 5. benchmark 保底配额

| 单元 | 下限 | 实际 | 该类不足（取全部） |
|---|---:|---:|---|
| domain=decision_mechanics | 100 | 1369 | 否 |
| domain=knowledge_reasoning | 100 | 229 | 否 |
| lang=en | 100 | 1598 | 否 |
| lang=en,kind=choice | 100 | 1255 | 否 |
| lang=en,kind=noul | 100 | 695 | 否 |
| lang=en,kind=score | 100 | 458 | 否 |

## 6. 泄漏检查（必须为空）

- 跨分区的组：0
- 跨分区的同一 state：0
- 跨分区的 id：0
- 复核范围：21376 组 / 21376 个不同 state
- 结论：**空**（按组切分 + state 合并后无任何跨区）。

## 7. benchmark 来源均衡（本轮硬约束）

- 上限：任一来源占 benchmark ≤ **25%**（本次折算 399 条；策略=政策上限，可行界 267 条）
- 下限：每个来源 ≥ **5%**（本次折算 79 条；来源池不足时取全部）
- 实际：最大来源 samatv256/jev-decisions-v1 占 25.0%；硬上限满足：是

**为什么把上限定在 25%**：英文侧有 6 个来源，25% 意味着至少 4 个来源共同撑起benchmark，任一来源都无法单独决定总分；再收紧（如 15%）会把只占池子 2.8% 的小来源放大 5 倍以上，让 benchmark 偏离真实训练分布，而 benchmark 的用途正是估计「在这份语料上表现如何」；25% 同时 ≤ 契约 40% 上限，且与第二大来源的自然占比（25.1%）同量级——原先 47.1% 的最大来源不再比第二名占便宜。下限 5% 对应「各个来源都收集一点」：每个来源都拿到一个可单独报数的切片。

| dataset | revision | license | 条目 | 占 benchmark | 该来源池子 | 取用率 |
|---|---|---|---:|---:|---:|---:|
| SargeDev/jev-distill-corpus-v3 | fc99c6357a9f | apache-2.0 | 399 | 25.0% | 7756 | 5.1% |
| samatv256/jev-decisions-v1 | c12aadf1f01c | cc-by-4.0 | 399 | 25.0% | 4009 | 10.0% |
| tasksource/procedural-typed-decisions | 609513a3fadd | apache-2.0 | 284 | 17.8% | 1500 | 18.9% |
| dwidlee/systemone-lite-general | c14eb7f7518f | mit | 281 | 17.6% | 1479 | 19.0% |
| ZefanCai/Open-Jev | c67699e13d0a | cc0-1.0 | 150 | 9.4% | 792 | 18.9% |
| kaivoss/system-one-270m-data | f31d5a3f3da8 | apache-2.0 | 85 | 5.3% | 447 | 19.0% |

> 取用率 = 该来源进 benchmark 的条数 / 它的全部可用条数。小来源的取用率天然更高（均衡的代价），训练侧少掉的那部分在表里可直接核对。

- **结构性冲突（必须知道）**：knowledge_reasoning 在语料里有 4390 条，其中 4358 条（99%）来自 SargeDev/jev-distill-corpus-v3；把该来源压到 上限以内之后，benchmark 的 knowledge_reasoning 只拿到 229 条（14.3%）。**该域几乎只有一个来源时，「来源均衡」与「该域保持自然占比」在数学上不可兼得**：要来源均衡就接受该域欠采样，要该域自然占比就得放开单一来源上限。请按用途二选一。

## 8. 产物

- data/splits/train.jsonl（+.gz）：17986 条（含补充 3148 条）
- data/splits/test.jsonl（+.gz）：4946 条
- data/splits/validation.jsonl（+.gz）：2473 条
- data/splits/benchmark.jsonl（+.gz）：1598 条（**内部，勿公开**）
- data/splits/benchmark-dataset/：可直接上传私有托管的内部 benchmark（README.md 数据卡 + USAGE.md + benchmark.jsonl(.gz) + manifest.json + verify.py）
- data/splits/split-manifest.json：各产物 sha256 与复跑校验结果（机器可读）

## 9. 可复现性（两次运行逐字节一致）

- 随机种子：20261005；同一输入 + 同一种子 + 同一私盐 → 同一分组、同一分配、同一顺序。
- 本次命令（输出路径与盐路径用占位符，实际路径见第 8 节）：`uv run --no-project --offline python datasets/general/data/splits/split.py --out <OUT_DIR> --report <REPORT_PATH> --seed 20261005 --salt-file <仓外私盐> --benchmark-lang en --benchmark-exclude-lang "zh=中文答案以 (group_id → 正确工具) 索引形式仍在公开 git 历史里可达（实测覆盖 5454/5454 组 = 100%），换盐/换种子都挡不住，zh 分项分数不具盲测意义；恢复条件：接入全新中文来源，或由维护者协调重写仓库历史清除该索引" --train-supplement datasets/general/data/zh-supplement/items.jsonl`
- 分区内条目按 id 排序；gzip 以 mtime=0 写入（gzip 头不含时间戳，否则两次压缩不会逐字节相同）。
- 输出把裸 U+2028 / U+2029 / U+0085 统一写成 \uXXXX 转义（无损）：它们在 JSON 里合法，但用 str.splitlines() 读会被当成换行、把记录劈开。
- 本次运行额外完整复跑一遍（重新读文件、重新分组、重新分配、重新打包）并写到独立临时目录，比对 14 个产物文件：**逐字节一致**。
- 产物树哈希（sha256 over 文件名+文件哈希）：8c1fc88961a8c1b1b58f3d4dd71e3c17b4fbb8d65dc3b4f195539c99f6cbe339
- 比对范围：train.jsonl、train.jsonl.gz、test.jsonl、test.jsonl.gz、validation.jsonl、validation.jsonl.gz、benchmark.jsonl、benchmark.jsonl.gz、benchmark-dataset/README.md、benchmark-dataset/USAGE.md、benchmark-dataset/benchmark.jsonl、benchmark-dataset/benchmark.jsonl.gz、benchmark-dataset/manifest.json、benchmark-dataset/verify.py

## 10. 保密：私盐 + 语言政策 + 版本

### 10.1 私盐（不可用公开信息重建）

- 交付件的所有随机种子都折进**仓外私盐**文件的 sha256 前 16 位；盐值与盐的哈希都不写进任何产物。只凭公开脚本 + 公开种子（--public-demo）跑出来的是**另一套**分配。
- 护栏（test_split.py 的 SecrecyTest 每次运行都验）：两个不同盐 → benchmark 不同；同盐两次 → 完全一致；无盐 public-demo 与交付件不同；盐文件在仓库内 / 无盐且非 demo / demo 写到仓库内 → 均拒绝（非零退出）。

### 10.2 语言政策：每种语言都必须显式声明

- 切分语料里出现的语言：en, zh
- 允许进 benchmark：en
- **显式排除**（--benchmark-exclude-lang）：
  - zh：中文答案以 (group_id → 正确工具) 索引形式仍在公开 git 历史里可达（实测覆盖 5454/5454 组 = 100%），换盐/换种子都挡不住，zh 分项分数不具盲测意义；恢复条件：接入全新中文来源，或由维护者协调重写仓库历史清除该索引
- 机制：run() 要求语料里每种语言要么在 --benchmark-lang 里，要么在--benchmark-exclude-lang 里带非空理由；漏一种直接拒绝切分（退出 3）。所以「benchmark 少了一整种语言」永远是**会报错的显式状态**，不是沉默的事实——恢复条件一满足，去掉排除项即可翻回来。

### 10.3 版本：v1 作废，v2 与 v3 不可拼接

| 版本 | 内容 | 状态 |
|---|---|---|
| v1 | 公开种子、**无盐**；benchmark 2,389 条（含 zh 789） | **作废**：可用公开脚本 + 语料 + 种子逐字节重建（benchmark sha256 43937e09a6fdde62…） |
| v2 | 私盐 + 只允许 en 进 benchmark；benchmark 1,600 条，单一来源占 47.1% | 已被 v3 取代（benchmark sha256 f5ae670811c33200…） |
| **v3（本次）** | 私盐 + en-only + **来源均衡（≤25% 上限 / ≥5% 下限）** + train 回灌降级补充 | 现行交付件；哈希见第 9 节与 split-manifest.json |

**v1 / v2 / v3 的 benchmark 是三套不同的条目集合，分数不可拼接、不可混用。**

### 10.4 公开面零命中

- 护栏：SecrecyTest 逐个扫描**所有被 git 跟踪的文件**（`.gz` 解压后），对 benchmark 的**条目 id** 与**正文**（state / 整行 JSON）两种口径都要求零命中；benchmark 分区与 benchmark-dataset/ 都在 .gitignore（benchmark*）。
  - 本次运行的公开面审计：对全部被跟踪文件（.gz 解压后）扫描，指纹 1598 条 id / 1598 条正文 → 零命中；可用 --audit-public-surface 单独复跑（命中则退出 1，并打印文件名）。（不记录文件个数：仓库增删文件会让它变化，而重跑一致性要求产物只由输入与盐决定。）
  - 为什么要两种口径：文件级检查（有没有被 git 跟踪）挡不住**内容级**泄漏——曾经有派生索引文件把 benchmark 的全部 id 列在里面（本身不含答案，但能精确指认成员）；压缩流里的泄漏也只有解压后才看得见。
- 语料、中文答案索引等含 benchmark 正文/答案的文件已移出版本控制（仓外留存）；但**删除不改变 git 历史**——zh 的 (group_id → 正确工具) 索引仍在历史里可达，这正是 zh 不进 benchmark 的原因（见 10.2 的排除理由）。
- 本报告、数据卡、manifest 都只含聚合统计；test_split.py 与 test_benchmark_package.py 有对应断言，benchmark 包 verify.py 另有独立校验。

## 11. origin 构成（原生 vs 降级）

| 分区 | origin=source（原生） | origin=taxonomy 等（降级） | 其它/未标 |
|---|---:|---:|---:|
| train | 14838 | 3148 | 0 |
| test | 4946 | 0 | 0 |
| validation | 2473 | 0 | 0 |
| benchmark | 1598 | 0 | 0 |

| 语言 | origin | 条目 | 落在哪些分区 |
|---|---|---:|---|
| en | source | 15983 | benchmark 1598, test 3197, train 9590, validation 1598 |
| zh | source | 7872 | test 1749, train 5248, validation 875 |
| zh | taxonomy | 3148 | train 3148 |

- origin=source 是来源原生四元组（A 层，可进 benchmark）；taxonomy 等是降级派生（B 层，只进 train）。benchmark 只含 A 层。
