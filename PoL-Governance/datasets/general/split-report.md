# 最终切分报告（6:2:1:1，按请求分组）

本报告只含聚合统计，**不含任何样本内容**；内部 benchmark 的条目只存在于 data/splits/benchmark.jsonl(.gz) 与 data/splits/benchmark-dataset/，请勿提交到公开仓库，请上传 Hugging Face 并设为 private。

- 随机种子：20261005
- 切分比例：train=0.6, test=0.2, validation=0.1, benchmark=0.1
- 输入文件：1 个
  - datasets/general/data/items.final.jsonl：23855 条
- 条目总数：23855；请求组 21376 个

## 1. 切分算法

1. **分组**（并查集）：显式分组键（item.group_id / source.group_id / meta.group_id / source.request_id / meta.request_id）与**归一化 state**（去空白、压缩空白、大小写折叠）各自连边；同一分量的所有条目整组进同一分区，绝不按行切。
   - 显式分组键 8664 条；无显式键（靠 state 或 id 兜底）15191 条
   - 组数 21376；多条目组 2479 个；最大组 2 条；跨多个 state 的组 0 个；含多个显式分组 id 的组 0 个
   - 无 state 的条目 0 条；state 分组：开启
   - 中文侧分组 id 门禁（zh）：已通过
2. **分层**：按 (domain, lang) 分层；层内组按种子洗牌，benchmark 先按 10% 预留，其余组按 6:2:1 用「目标条数 - 已分配条数」最大缺口贪心分配。
3. **benchmark 保底**：对每个 lang x kind、每个 domain、每个 lang 设下限，不足时从其余组整组补足；该类总量不足下限时取全部并在下表标「是」。
4. **确定性**：随机数来自 random.Random("seed|阶段|domain|lang")；分区内条目按 id 排序；gzip 以 mtime=0 写入 → 同一输入重跑逐字节一致。

## 2. 分区规模

| 分区 | 条目 | 占比 | 目标占比 | 请求组 |
|---|---:|---:|---:|---:|
| train | 14310 | 60.0% | 60% | 14310 |
| test | 4771 | 20.0% | 20% | 4771 |
| validation | 2385 | 10.0% | 10% | 2385 |
| benchmark | 2389 | 10.0% | 10% | 2389 |

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
| en | 9588 (67%) | 3197 (67%) | 1598 (67%) | 1600 (67%) |
| zh | 4722 (33%) | 1574 (33%) | 787 (33%) | 789 (33%) |

### 4.2 domain

| domain | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| decision_mechanics | 11677 (82%) | 3893 (82%) | 1946 (82%) | 1949 (82%) |
| knowledge_reasoning | 2633 (18%) | 878 (18%) | 439 (18%) | 440 (18%) |

### 4.3 kind

| kind | train | test | validation | benchmark |
|---|---:|---:|---:|---:|
| choice | 10706 (75%) | 3545 (74%) | 1780 (75%) | 1784 (75%) |
| noul | 3977 (28%) | 1342 (28%) | 668 (28%) | 680 (28%) |
| score | 2236 (16%) | 742 (16%) | 367 (15%) | 380 (16%) |

### 4.4 分层漂移（各区内 (domain, lang) 占比 vs 全局占比）

| 分区 | 最大占比差 | 该层 |
|---|---:|---|
| train | 0.0% | decision_mechanics/en |
| test | 0.0% | decision_mechanics/en |
| validation | 0.0% | knowledge_reasoning/en |
| benchmark | 0.0% | decision_mechanics/en |

## 5. benchmark 保底配额

| 单元 | 下限 | 实际 | 该类不足（取全部） |
|---|---:|---:|---|
| domain=decision_mechanics | 100 | 1949 | 否 |
| domain=knowledge_reasoning | 100 | 440 | 否 |
| lang=en | 100 | 1600 | 否 |
| lang=zh | 100 | 789 | 否 |
| lang=en,kind=choice | 100 | 995 | 否 |
| lang=en,kind=noul | 100 | 682 | 否 |
| lang=en,kind=score | 100 | 382 | 否 |
| lang=zh,kind=choice | 100 | 789 | 否 |

## 6. 泄漏检查（必须为空）

- 跨分区的组：0
- 跨分区的同一 state：0
- 跨分区的 id：0
- 复核范围：21376 组 / 21376 个不同 state
- 结论：**空**（按组切分 + state 合并后无任何跨区）。

## 7. 来源汇总（benchmark 分区，聚合）

| dataset | revision | license | 条目 |
|---|---|---|---:|
| Deepexi/openai-formate-function-calling-small | 6d1dc02a2549 | apache-2.0 | 789 |
| SargeDev/jev-distill-corpus-v3 | fc99c6357a9f | apache-2.0 | 781 |
| samatv256/jev-decisions-v1 | c12aadf1f01c | cc-by-4.0 | 391 |
| tasksource/procedural-typed-decisions | 609513a3fadd | apache-2.0 | 159 |
| dwidlee/systemone-lite-general | c14eb7f7518f | mit | 143 |
| ZefanCai/Open-Jev | c67699e13d0a | cc0-1.0 | 76 |
| kaivoss/system-one-270m-data | f31d5a3f3da8 | apache-2.0 | 50 |

## 8. 产物

- data/splits/train.jsonl（+.gz）：14310 条
- data/splits/test.jsonl（+.gz）：4771 条
- data/splits/validation.jsonl（+.gz）：2385 条
- data/splits/benchmark.jsonl（+.gz）：2389 条（**内部，勿公开**）
- data/splits/benchmark-dataset/：可直接上传 HF 的 private benchmark（dataset card + benchmark.jsonl(.gz) + manifest.json）
- data/splits/split-manifest.json：各产物 sha256 与复跑校验结果（机器可读）

## 9. 可复现性（两次运行逐字节一致）

- 随机种子：20261005；同一输入 + 同一种子 → 同一分组、同一分配、同一顺序。
- 分区内条目按 id 排序；gzip 以 mtime=0 写入（gzip 头不含时间戳，否则两次压缩不会逐字节相同）。
- 输出把裸 U+2028 / U+2029 / U+0085 统一写成 \uXXXX 转义（无损）：它们在 JSON 里合法，但用 str.splitlines() 读会被当成换行、把记录劈开。
- 本次运行额外完整复跑一遍并写到独立临时目录，比对 12 个产物文件：**逐字节一致**。
- 产物树哈希（sha256 over 文件名+文件哈希）：2c3fa92c323edbf38147325dd6605220ed9a7b1a64cc0d935201f514533c62f4
- 比对范围：train.jsonl、train.jsonl.gz、test.jsonl、test.jsonl.gz、validation.jsonl、validation.jsonl.gz、benchmark.jsonl、benchmark.jsonl.gz、benchmark-dataset/README.md、benchmark-dataset/benchmark.jsonl、benchmark-dataset/benchmark.jsonl.gz、benchmark-dataset/manifest.json
