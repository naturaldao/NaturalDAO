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
| train | 17458 | 64.7% | 60% | 15419 |
| test | 4771 | 17.7% | 20% | 4771 |
| validation | 2385 | 8.8% | 10% | 2385 |
| benchmark | 2389 | 8.8% | 10% | 2389 |

> **train 高于 60% 是刻意安排**：切分完成后按裁定**只向 train 追加**了 3,148 条中文降级补充
> （origin=taxonomy、benchmark_eligible=false，仅 train），未触碰其它分区。合计条目由 23,855 变为 27,003。
> 追加前后的哈希与 origin 构成见第 10 节。

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
- 可选补强路径：中文 noul/score 目前没有原生来源；task-14 的中文分类衍生池（42,436 条，单标签 + documented 映射，**非原生四元组**）可作补强，属成色降级，需用户确认后另行引入——**本轮未引入**。train 里现有 3,148 条同类降级补充（仅 train、benchmark_eligible=false），见第 10 节。
- 出题方：英文原生与中文原生的 questions 均已带 origin=source；中文侧在 2026-10-05 修复后 source_key 也逐问齐全。

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

- data/splits/train.jsonl（+.gz）：17458 条（含 3,148 条降级补充，仅 train；见第 10 节）
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
- 产物树哈希（sha256 over 文件名+文件哈希）：618826416149312e023cbb719c3944b868276a6c84f697e0fbb3b6a63230101c
- 比对范围：train.jsonl、train.jsonl.gz、test.jsonl、test.jsonl.gz、validation.jsonl、validation.jsonl.gz、benchmark.jsonl、benchmark.jsonl.gz、benchmark-dataset/README.md、benchmark-dataset/benchmark.jsonl、benchmark-dataset/benchmark.jsonl.gz、benchmark-dataset/manifest.json
- 上述复跑校验与外部两遍比对（13 个文件含报告）均在**追加补充集之前**完成；追加只改 train 的两个文件（见第 10 节）。

## 10. 中文 origin 修复后的整体重跑 + train 追加降级补充（task-21）

背景：契约规定「questions[].origin 缺省即视为 taxonomy」，而中文原生（Deepexi）条目此前未标 origin，
会被读成降级数据（方向反了）。pol2-replay 修复后（每问补 origin=source + source_key），
按裁定**整条链重跑**：重合并 items.final → 重切分四区（种子 20261005）→ 只向 train 追加 3,148 条降级补充。

### 10.1 重跑后的四区哈希

| 分区 | sha256（明文） | sha256（.gz） |
|---|---|---|
| train（追加前） | 29870a4eacca2aa440cfb2ff96d2fb30f2aa43881d9c2a93b8902418f1e94dad | 1d42925502b72eeeac39d2877c2534ae388dbf7593900be1aecab3c7e863fbda |
| train（**追加后**） | **52ed2ff6c2987002092dc9fbdb4ad0e59b4db3608f1de68802e8065a71264894** | **dbf6c00b01ab607f2df0a64b46f80fa23372f23f18eae5b7b12d0bc594047382** |
| test | 308d58028c43680a17f7908438ff6c27dab01b33dbb07018c856809048aaee49 | 0182019c397a5fa306e76e0681387c466ff5fb4d64bca8c72a5fc3f554435138 |
| validation | 24c2addec2f8b4ba8869bb69715705b517e62cace0c0c1530778a8b874734b6d | 99d88f3762b0fca1a984952f7cf53a9ae564bae0ffb5f89b293faf7490ff1cb5 |
| benchmark | 43937e09a6fdde62c7290bd6f5217d6928f4fd7809f1f2f1a4808f43c495b3d9 | 4a7f75bc1f799127bceccfb71ada826305686273b4c4adf2882c046ad7cc03b3 |

输入语料 items.final.jsonl：23,855 条（en 15,983 + zh 7,872），sha256 21f11fe3dc39edd9d82680b7461b45883bb73d15a1d9611f3b2e80f4bd7e9f9f。

### 10.2 口径一致性交叉验证（重跑前 vs 重跑后）

按"算法与种子不变、只多 origin/source_key 字段"的论断，重跑后各分区的 **id 集合**应与重跑前一致：

| 分区 | 重跑前基线 | 重跑后 | 结论 |
|---|---:|---:|---|
| test | 4,771 | 4,771 | id 集合**完全一致** |
| validation | 2,385 | 2,385 | id 集合**完全一致** |
| benchmark | 2,389 | 2,389 | id 集合**完全一致** |
| train | 14,310（盘上 17,458 − 3,148 补充） | 14,310 | id 集合**完全一致**（对称差 0） |

即：本次重跑只带来字段新增，没有任何条目换区。泄漏检查仍为 **0/0/0**。

### 10.3 追加后 train 的 origin 构成（三类）

| origin | 条目 | 占 train | 说明 |
|---|---:|---:|---|
| source（英文原生） | 9,588 | 54.9% | 英文原生四元组，questions[].origin=source |
| source（中文原生） | 4,722 | 27.1% | 中文原生（Deepexi）四元组；修复后 questions[].origin=source 且 source_key 齐全 |
| taxonomy（**降级补充**） | **3,148** | **18.0%** | 中文分类数据 + documented 映射生成；meta.tier=derived、benchmark_eligible=false、**仅 train** |
| 未标 | **0** | 0.0% | 重跑后已无缺 origin 的条目 |

- train 合计 **17,458**：其中 **3,148 条（18.0%）是降级补充**，与原生条目混在同一分区，
  训练配比与损失权重请据此调整，不要把它们当作原生四元组。
- 降级补充 kind：noul 1,631 + score 1,517；来源 4 个（BEncoderRT/User_Intent_Risk_Triage 2,061、
  textdetox/multilingual_toxicity_dataset 543、chenhaodev/med-guard-safety-synth 472、
  vanila434/multilingual-elder-safety-msgs 72）；来源文件 sha256 f2d87c3893d2e138b1443140a67d30c545cd47bebb05c5d9d629fed4f7422c8a。
- train 追加后：请求组 15,419；kind（条目集合）choice 10,706 / noul 5,608 / score 3,753；语言 en 9,588 / zh 7,870。
- **降级补充不得进入 test / validation / benchmark**：三区保持纯原生，本次追加未触碰。

### 10.4 注意

- 本节是一次性补丁：若以后重跑 datasets/general/data/splits/split.py，四个分区会由纯原生语料重新生成，
  本次追加需重新执行。
- 第 5 节保底表的"实际"按**组**计（同一请求组内条目一并计入），因此会比该 kind 的真实条目数略高
  （例如 en/noul 显示 682，而按条目复算是 680）；真实条目数以 benchmark 包 manifest 的 verifiable_counts 为准。
  这是报表口径问题，不影响分区成员。

