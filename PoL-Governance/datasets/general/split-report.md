# 最终切分报告（6:2:1:1，按请求分组）

本报告只含聚合统计，**不含任何样本内容**；内部 benchmark 的条目只存在于 data/splits/benchmark.jsonl(.gz) 与 data/splits/benchmark-dataset/，请勿提交到公开仓库，请上传 Hugging Face 并设为 private。

- 随机种子：20261005
- 切分比例：train=0.6, test=0.2, validation=0.1, benchmark=0.1
- 输入文件：1 个
  - datasets/general/data/items.final.jsonl：23855 条
- 条目总数：23855；请求组 21376 个
- 保密：本次运行使用 仓外私盐（盐值不记录、不派生进任何公开产物）
- benchmark 语言白名单：en（白名单外的语言只进 train/test/validation）

## 1. 切分算法

1. **分组**（并查集）：显式分组键（item.group_id / source.group_id / meta.group_id / source.request_id / meta.request_id）与**归一化 state**（去空白、压缩空白、大小写折叠）各自连边；同一分量的所有条目整组进同一分区，绝不按行切。
   - 显式分组键 8664 条；无显式键（靠 state 或 id 兜底）15191 条
   - 组数 21376；多条目组 2479 个；最大组 2 条；跨多个 state 的组 0 个；含多个显式分组 id 的组 0 个
   - 无 state 的条目 0 条；state 分组：开启
   - 中文侧分组 id 门禁（zh）：已通过
2. **分层**：按 (domain, lang) 分层；层内组按种子洗牌，benchmark 先按 10% 预留，其余组按 6:2:1 用「目标条数 - 已分配条数」最大缺口贪心分配。
3. **benchmark 保底**：对每个 lang x kind、每个 domain、每个 lang 设下限，不足时从其余组整组补足；该类总量不足下限时取全部并在下表标「是」。
4. **确定性**：随机数来自 random.Random("公开种子|盐token|阶段|domain|lang")；分区内条目按 id 排序；gzip 以 mtime=0 写入 → 同一输入 + 同一私盐重跑逐字节一致。
5. **保密**：盐token = 仓外私盐文件内容的 sha256 前 16 位；盐值与盐的哈希都不写入任何公开产物。只用公开脚本 + 公开种子（--public-demo）得到的是**另一套**分配，见第 10 节。

## 2. 分区规模

| 分区 | 条目 | 占比 | 目标占比 | 请求组 |
|---|---:|---:|---:|---:|
| train | 17984 | 66.6% | 60% | 15801 |
| test | 4946 | 18.3% | 20% | 4946 |
| validation | 2473 | 9.2% | 10% | 2473 |
| benchmark | 1600 | 5.9% | 10% | 1600 |

> **三处刻意的偏离，别当成 bug**：
> 1. **train 高于 60%（66.6%）**：切分完成后按裁定只向 train 追加了 3,148 条中文降级补充
>    （origin=taxonomy、benchmark_eligible=false，仅 train）；合计条目 23,855 → 27,003。
> 2. **benchmark 只有 1,600 条（5.9% 而非 10%）**：本次只允许**英文**进 benchmark（中文侧见第 10 节），
>    1,600 ≈ 英文侧（15,983）的 10%。
> 3. **benchmark 全是英文**，因此第 4.4 节 benchmark 一行的分层漂移必然偏大（zh 全在公开三区）。

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
- **中文侧不进内部 benchmark**（本轮裁定）：中文答案曾以 (group_id → 正确工具) 索引进入公开版本库，
  换盐、换种子、重切都挡不住——该映射对任何从同批请求生成的题都有效。恢复条件见第 10.3 节。
- 可选补强路径：中文 noul/score 目前没有原生来源；task-14 的中文分类衍生池（42,436 条，单标签 + documented 映射，**非原生四元组**）可作补强，属成色降级，需用户确认后另行引入——**本轮未引入**。

## 4. 分布（每区内部占比）

### 4.1 lang

| lang | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| en | 9588 (65%) | 3197 (65%) | 1598 (65%) | 1600 (100%) |
| zh | 5248 (35%) | 1749 (35%) | 875 (35%) | 0 (0%) |

### 4.2 domain

| domain | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| decision_mechanics | 12203 (82%) | 4068 (82%) | 2034 (82%) | 1160 (72%) |
| knowledge_reasoning | 2633 (18%) | 878 (18%) | 439 (18%) | 440 (28%) |

### 4.3 kind

| kind | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| choice | 11187 (75%) | 3763 (76%) | 1868 (76%) | 997 (62%) |
| noul | 4019 (27%) | 1324 (27%) | 672 (27%) | 652 (41%) |
| score | 2222 (15%) | 757 (15%) | 349 (14%) | 397 (25%) |

### 4.4 分层漂移（各区内 (domain, lang) 占比 vs 全局占比）

| 分区 | 最大占比差 | 该层 |
|---|---:|---|
| train | 2.4% | decision_mechanics/zh |
| test | 2.4% | decision_mechanics/zh |
| validation | 2.4% | decision_mechanics/zh |
| benchmark | 33.0% | decision_mechanics/zh |

## 5. benchmark 保底配额

| 单元 | 下限 | 实际 | 该类不足（取全部） |
|---|---:|---:|---|
| domain=decision_mechanics | 100 | 1160 | 否 |
| domain=knowledge_reasoning | 100 | 440 | 否 |
| lang=en | 100 | 1600 | 否 |
| lang=en,kind=choice | 100 | 998 | 否 |
| lang=en,kind=noul | 100 | 652 | 否 |
| lang=en,kind=score | 100 | 398 | 否 |

## 6. 泄漏检查（必须为空）

- 跨分区的组：0
- 跨分区的同一 state：0
- 跨分区的 id：0
- 复核范围：21376 组 / 21376 个不同 state
- 结论：**空**（按组切分 + state 合并后无任何跨区）。

## 7. 来源汇总（benchmark 分区，聚合）

| dataset | revision | license | 条目 |
|---|---|---|---:|
| SargeDev/jev-distill-corpus-v3 | fc99c6357a9f | apache-2.0 | 753 |
| samatv256/jev-decisions-v1 | c12aadf1f01c | cc-by-4.0 | 438 |
| tasksource/procedural-typed-decisions | 609513a3fadd | apache-2.0 | 144 |
| dwidlee/systemone-lite-general | c14eb7f7518f | mit | 135 |
| ZefanCai/Open-Jev | c67699e13d0a | cc0-1.0 | 80 |
| kaivoss/system-one-270m-data | f31d5a3f3da8 | apache-2.0 | 50 |

## 8. 产物

- data/splits/train.jsonl（+.gz）：17984 条（含 3,148 条降级补充，仅 train；见第 10 节）
- data/splits/test.jsonl（+.gz）：4946 条
- data/splits/validation.jsonl（+.gz）：2473 条
- data/splits/benchmark.jsonl（+.gz）：1600 条（**内部，勿公开**；全部英文，v2）
- data/splits/benchmark-dataset/：可直接上传 HF 的 private benchmark（dataset card + benchmark.jsonl(.gz) + manifest.json）
- data/splits/split-manifest.json：各产物 sha256 与复跑校验结果（机器可读）

## 9. 可复现性（两次运行逐字节一致）

- 随机种子：20261005；同一输入 + 同一种子 → 同一分组、同一分配、同一顺序。
- 分区内条目按 id 排序；gzip 以 mtime=0 写入（gzip 头不含时间戳，否则两次压缩不会逐字节相同）。
- 输出把裸 U+2028 / U+2029 / U+0085 统一写成 \uXXXX 转义（无损）：它们在 JSON 里合法，但用 str.splitlines() 读会被当成换行、把记录劈开。
- 本次运行额外完整复跑一遍并写到独立临时目录，比对 12 个产物文件：**逐字节一致**。
- 另起一次同条件 CLI（同样带盐、同样未追加补充）到第三个目录：**13 个文件（含报告）0 处不一致**。
- 产物树哈希（sha256 over 文件名+文件哈希）：7635cfbbd01b1f7310808d6aedaa79fb55334bdfbcd56681dde65ca88d6cbfb1
- 注意：带盐后**旧四区（未加盐那版）与本次四区是两套**，旧版全部作废（见第 10.1 节）。

## 10. benchmark 保密修复（task-24）：加盐重切 + 移出泄漏文件 + v1 作废

### 10.1 新旧是两套，v1 作废

| 版本 | 内容 | 状态 |
|---|---|---|
| v1（本报告早些时候的四区） | 公开种子 20261005、无盐；benchmark 2,389 条（含中文 789） | **作废**：可用仓库公开的脚本 + 语料 + 种子逐字节重建（benchmark.jsonl sha256 43937e09a6fdde62…） |
| **v2（本次）** | **仓外私盐** + 只允许英文进 benchmark；benchmark 1,600 条 | 现行交付件；四区哈希见 10.5 |

**v1 与 v2 不可拼接、不可混用计分**；v1 的 benchmark 与 test/validation 均已作废。

### 10.2 三条泄漏路径与对应修复

| 路径 | 证据 | 修复 |
|---|---|---|
| 算法路：公开脚本 + 公开语料 + 公开种子 → 重建 benchmark | v1 可逐字节重建 | **仓外私盐**折进所有 RNG 种子；无盐只能 public-demo（写仓库外），产出的是另一套 |
| 内容路：被跟踪的语料里直接含 benchmark 正文 | items.final.jsonl.gz 含全 2,389 条且逐字段相同；items.native.jsonl.gz 含全 1,600 条英文条目 | 七件含 benchmark 或答案索引的文件**移出版本控制**（清单见 10.4），公开侧不再有完整语料 |
| 减法路：公开语料 − 公开三区 = benchmark | 语料在仓库里时成立 | 同上（公开侧没有完整语料）；对外只发布 train/test/validation |

### 10.3 中文侧为什么不进 benchmark（本轮裁定）

- 泄漏的不是"哪几条"，而是 **(group_id → 正确工具) 的映射**（zh-group-index.jsonl，5,454 行，覆盖中文全部组），
  它对**任何**从同批请求生成的题都有效——换盐、换种子、重切都挡不住。
- 未选择"重写 git 历史"：这是共享仓库、已有协作者分支，无法确认没有外部 clone 或已推送副本，历史重写不可逆。
- 未选择"保留但标注已泄漏"：一个已知不可信的 benchmark 比一个小而干净的更糟，会给出看似可信的分数。
- **恢复条件**：接入一个全新的中文来源；或在确认无外部副本后，由维护者协调重写仓库历史清除该索引。

### 10.4 移出版本控制的文件（仓库外 D:/pol2-raw/general-private/）

| 文件 | 原因 |
|---|---|
| data/items.final.jsonl.gz | 含 benchmark 全部 2,389 条且逐字段相同（完整语料） |
| data/items.native.jsonl.gz | 含英文侧 benchmark 全部 1,600 条且逐字段相同 |
| data/items.native.slim.jsonl.gz | 字段精简版，正文仍在（同 1,600 条） |
| data/items.bilingual.jsonl.gz | 旧 schema，同一批 state/答案（减法路原料） |
| data/items.jsonl.gz | 旧 taxonomy 版，同一批 state/答案 |
| data/zh/zh-group-index.jsonl | 5,454 行答案索引（group_id → 正确工具） |
| data/zh/zh-items.sample.jsonl | 200 行中含 9 行与 benchmark 逐字段相同 |

从版本库删除跟踪记录（git rm --cached）与提交由 Lead 执行；我这边只做"移出 + 清单 + 验证"。
护栏测试会逐个扫描**被 git 跟踪**的文件，要求对 benchmark 的 id 与正文**零命中**。

### 10.5 本次（v2）四个分区的哈希

| 分区 | 条目 | sha256（明文） |
|---|---:|---|
| train（追加补充后） | 17,984 | 0d04c0445ea0a64ee9aefbcea87686abfd4de48ce3fb0a98e8030d3a85b706e2 |
| test | 4,946 | 95e6633914f08ad6…（完整值见 split-manifest.json） |
| validation | 2,473 | 55c11de812d3177c… |
| benchmark | 1,600 | f5ae670811c33200…（v2，私盐版） |

### 10.6 追加后 train 的 origin 构成

| origin | 条目 | 占 train |
|---|---:|---:|
| source（英文原生） | 9,588 | 53.3% |
| source（中文原生） | 5,248 | 29.2% |
| taxonomy（**降级补充**，仅 train） | 3,148 | 17.5% |
| 未标 | 0 | 0.0% |

train 其他聚合：请求组 15,801；语言 en 9,588 / zh 8,396；kind（条目集合）choice 11,187 / noul 5,650 / score 3,739；
域 decision_mechanics 12,203 / knowledge_reasoning 2,633 / risk_harm 2,605 / human_judgment 543。
**risk_harm 与 human_judgment 只出现在 train**，因此 train 与 test/validation/benchmark 的域分布不可比。

### 10.7 机器可验证的保密性（test_split.py 的 SecrecyTest）

1. 同一语料 + 两个不同盐 → benchmark 集合不同；
2. 同盐两次 → 完全一致（可复现）；
3. 语言白名单：非白名单语言不得进 benchmark；
4. **无盐 public-demo 跑法与交付件不同**（集成测试，语料存在时执行）；
5. **所有被 git 跟踪的文件对 benchmark 记录零命中**（护栏）；
6. 拒绝性：盐文件在仓库内 / 无盐且非 public-demo / public-demo 写到仓库内 → 均非零退出。

- 比对范围：train.jsonl、train.jsonl.gz、test.jsonl、test.jsonl.gz、validation.jsonl、validation.jsonl.gz、benchmark.jsonl、benchmark.jsonl.gz、benchmark-dataset/README.md、benchmark-dataset/benchmark.jsonl、benchmark-dataset/benchmark.jsonl.gz、benchmark-dataset/manifest.json
