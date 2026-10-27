# Track A 决策模型保留测试集独立评测指南 (Evaluation Package)

> **面向读者**：本指南面向**独立第三方评测者**或**获得正式授权在隔离环境中执行评测的工作人员**。
> 本文档假设读者不具备 PoL-Governance 项目的先验开发背景，旨在提供一份自包含、可复现、严防数据泄露的规范操作手册。

---

## 目录
- [1. 评测包定位与数据边界](#1-评测包定位与数据边界)
- [2. 目录结构与模块说明](#2-目录结构与模块说明)
- [3. 环境要求与完整性校验](#3-环境要求与完整性校验)
- [4. 逐步运行手册](#4-逐步运行手册)
  - [4.1 数据准备与中性命名规范](#41-数据准备与中性命名规范)
  - [4.2 构造统一评测视图](#42-构造统一评测视图)
  - [4.3 模型推理评测 (Base 与 Adapter)](#43-模型推理评测-base-与-adapter)
  - [4.4 概率校准温度设定 (两条路径)](#44-概率校准温度设定-两条路径)
  - [4.5 隔离环境内聚合计算](#45-隔离环境内聚合计算)
  - [4.6 导出前合规检查 (唯一出口关卡)](#46-导出前合规检查-唯一出口关卡)
  - [4.7 环境清理与执行结果回报](#47-环境清理与执行结果回报)
- [5. 行为准则：严禁与允许清单](#5-行为准则严禁与允许清单)
- [6. 验收清单与评测范围界定](#6-验收清单与评测范围界定)
- [7. 版本清单与审计元数据](#7-版本清单与审计元数据)

---

## 1. 评测包定位与数据边界

### 1.1 本评测包是什么
本评测包是 PoL-Governance 项目（权力分离与大模型治理架构）针对 **Track A 决策模型**（基于 `Qwen/Qwen3-1.7B` 架构）制作的标准化独立评测工具套件。评测包将数据转换、模型推理、指标分层统计、校准检验与合规检查等核心脚本打包为一个自包含分发单元。

### 1.2 评测什么
评测的核心目标是衡量**在冻结协议下，微调是否在未见的私有保留测试集上带来具有统计显著性的决策能力提升，且输出概率是否具备良好的校准可用性**：
1. **决策准确率 (Letter Accuracy)**：对比未经微调的基线模型（0-shot 基线）与微调后的 LoRA 适配器（Track A Adapter）在多选封闭决策任务上的选择准确率；
2. **多维度分层表现**：按照题目类型 (`kind`: choice / noul / score)、语言 (`lang`: en / zh)、选项数量区间 (`option_bucket`: 2 / 3-4 / 5-8 / 9-26) 以及治理路由 (`route`: classification / distillation) 分解表现；
3. **统计显著性与配对比较**：计算单模型准确率的 Wilson 95% 置信区间，以及基于逐题配对重采样的配对 Bootstrap 95% 置信区间 ($Delta = \text{tuned} - \text{base}$)；
4. **概率校准 (Probability Calibration)**：检验经温度缩放 (Temperature Scaling) 后的候选概率质量，评估负对数似然 (NLL)、Brier 分数、期望校准误差 (ECE, 15 等宽箱) 与最大校准误差 (MCE)。

### 1.3 只发布聚合数字
本评测协议实施极其严格的数据输出隔离：**只导出、只传输、只发布聚合统计数字（Aggregated Metrics JSON）**。
- 输出文件仅包含样本规模、正确数、比率、置信区间与分层聚合值；
- 严禁导出逐例样本 ID (`rid`)、问题文本、选项内容、模型逐行预测结果 (`pred_letter`) 或真实金标 (`gold_letter`)。

### 1.4 为什么必须严格物理隔离
私有保留测试集（Private Holdout / Benchmark，共 6,541 条）是评估治理模型泛化能力的最高权威依据：
1. **防止训练污染**：彻底避免私有案例流入后续模型训练集、微调语料或上下文示例中；
2. **防过拟合与针对性调优**：杜绝开发人员“依据保留集错误样例反向改写 Prompt、调整损失权重或超参数”等数据过拟合行为；
3. **第三方可信度**：评测由独立第三方评测者在其自主掌控的离线受控环境中闭环执行，确保评测结论不可篡改、真实可复核。

---

## 2. 目录结构与模块说明

评测包内的脚本严格沿用主仓库的相对目录布局，确保 Python 模块导入体系无缝一致：

```text
eval-package/
├── README.md                      # [本文件] 独立评测操作指南与执行规范
├── MANIFEST.json                  # 全包版本权威记录 (模型 Revision、文件哈希、Git Commit)
├── CHECKSUMS.sha256               # 包内所有文件 (除自身外) 的 SHA-256 校验和列表
├── finetune/                      # 评测与统计核心模块
│   ├── __init__.py                # 模块初始化
│   ├── decision_common.py         # 选项映射、分层指标计算、Prompt 渲染与路径安全护栏
│   ├── eval_decision.py           # 逐 Token 概率推理与单模型评测执行器
│   ├── calibrate.py               # 概率校准算法 (温度缩放拟合与 NLL/Brier/ECE 计算)
│   ├── final_eval_aggregate.py    # 隔离环境内多模型聚合脚本 (生成无逐例信息的 aggregate.json)
│   ├── check_aggregate_export.py  # 导出前合规检查器 (带出隔离环境的唯一审计闸门)
│   └── bench_latency.py           # 延迟与吞吐基准测试脚本 (可选参考工具)
└── datasets/
    └── general/
        ├── __init__.py            # 模块初始化
        └── build_training_view.py # 评测视图构建脚本 (将原始私有数据转换为统一决策视图)
```

各关键核心组件的职责定位：
- `MANIFEST.json`：静态版本权威文件。评测前必须查验其中记录的 Base Revision、Adapter 权重各文件哈希与评测协议版本；
- `CHECKSUMS.sha256`：完整性校验文件，包含除自身外所有文件的 SHA-256 签名，供评测者从零核对；
- `build_training_view.py`：数据隔离预处理工具，将库外原始数据格式化为模型可接受的统一封闭选择题视图；
- `eval_decision.py`：执行单模型推理，生成逐行预测缓存（保留在本地隔离区）；
- `final_eval_aggregate.py`：消费两个模型的预测缓存，执行配对 Bootstrap 与校准分析，产出聚合 JSON；
- `check_aggregate_export.py`：静态与动态审计聚合 JSON，确认零逐例泄漏且数值严格自洽。

---

## 3. 环境要求与完整性校验

### 3.1 运行环境要求
- **操作系统**：Linux (Ubuntu 22.04 LTS / 24.04 LTS 推荐) 或 macOS / Windows WSL2。
- **Python 版本**：Python 3.12 (开发验证基线：Python 3.12.13)。
- **深度学习核心依赖**（参考 `MANIFEST.json` 中所列测试环境版本）：
  - `torch >= 2.6.0`（测试环境基线：2.9.1+rocm7.2.1 或对应 CUDA / CPU 版本）
  - `transformers >= 5.0.0`（测试环境基线：5.20.2）
  - `peft >= 0.20.0`（测试环境基线：0.21.2）
- **标准库优先原则**：
  - `build_training_view.py`、`final_eval_aggregate.py` 与 `check_aggregate_export.py` **全部仅使用 Python 3.12 标准库**，完全不依赖 GPU 或 torch。
  - 只有在运行 `eval_decision.py` 执行模型推理时才需要导入 `torch`、`transformers` 与 `peft`。
- **硬件支持**：
  - 推理支持 GPU 加速（NVIDIA CUDA 或 AMD ROCm）或纯 CPU 推理（适合资源受限但要求高确定性的环境）。

### 3.2 离线与网络隔离要求 (Air-gapped)
- 执行环境必须处于**物理或虚拟网络隔离状态（断开公网连接）**；
- 评测脚本全程禁止任何外部网络通信、API 调用或遥测回传。

### 3.3 从零开始校验步骤
在开始执行任何评测前，评测者必须完成两步完整性与版本审计：

1. **解压与哈希完整性校验**：
   ```bash
   # 进入评测包解压目录
   cd eval-package

   # 执行 SHA-256 校验和检验 (必须全部输出 OK)
   sha256sum -c CHECKSUMS.sha256
   ```
   若任何文件报告 `FAILED`，说明评测包在分发过程中受损或被篡改，必须立即停止，拒绝运行。

2. **审验 MANIFEST.json 版本权威清单**：
   查验 `MANIFEST.json` 中声明的元数据（字段位于 `MANIFEST.json → versions` 之下）：
   - `versions.base_model.id` 与 `versions.base_model.revision`；
   - `versions.adapter.files_sha256`（与评测者本地持有的 LoRA 权重文件哈希逐一核对）；
   - `versions.protocol.version` 与 `versions.protocol.scope`；
   - `git_commit`（评测代码所属 commit）与 `package_sha256`（整个包的规范摘要，见 §7.1）。
     注：`prepare_eval_package.py --check` 默认只校验逐文件 sha256（不比对 commit；生成 manifest 之后仓库还会有新提交），需要钉住 commit 时显式传 `--git-commit`。

---

## 4. 逐步运行手册

本手册支持两种执行方式（两种方式底层步骤与命令完全相同，区别仅在执行者与临时文件归属）：
- **方式 1（推荐：独立评测者执行）**：独立第三方评测者在自己的离线隔离机器上准备数据、执行推理并聚合，最终仅回传 `aggregate.json`。
- **方式 2（项目方经授权隔离执行）**：在获得数据所有者正式书面授权后，由我们在受控隔离节点上按照完全相同的流程执行，完成后销毁所有中间文件。

以下步骤均以通用的中性临时目录 `/tmp/priv-eval/` 为例说明。

### 4.1 数据准备与中性命名规范

1. **数据目录隔离**：
   创建独立的库外临时目录，禁止在代码仓库目录内部解压或存放私有测试数据：
   ```bash
   mkdir -p /tmp/priv-eval
   ```

2. **中性文件名要求**：
   将原始保留测试集题目复制到该临时目录，**必须使用中性文件名**：
   - 题目文件命名为：`/tmp/priv-eval/items.jsonl`
   - 若附带路由旁挂标注文件，命名为：`/tmp/priv-eval/target-types.jsonl`

3. **为什么使用中性文件名（协议硬性要求）**：
   `build_training_view.py` 内置了严格的路径安全检查机制（`SKIP_BENCHMARK_TOKENS`）。如果文件名或 split 参数中包含 `benchmark`、`holdout` 或 `private`，脚本将**主动拒绝读取并强制退出（exit code 2）**。
   这一设计是用于防止开发阶段误将私有集当作公开训练集直接构建。因此，将私有文件重命名为 `items.jsonl` 是**标准评测协议的规范调用流程**，受审计流程保护，并非绕过审计。

### 4.2 构造统一评测视图

使用统一视图构建脚本，将原始选择题格式化为标准决策视图（`tv-1` 提示词模板）：

```bash
python datasets/general/build_training_view.py --split test \
  --items /tmp/priv-eval/items.jsonl \
  --target-types /tmp/priv-eval/target-types.jsonl \
  --out /tmp/priv-eval/private-eval-view.jsonl
```

**关于路由真值与数据对齐的说明**：
- 若私有集未提供 `target-types.jsonl` 文件，`build_training_view.py` 的 `no_route` 兜底机制会自动将路由标记为 `classification` 处理，保证流程畅通；
- 若私有数据源的字段命名（如问题、选项或答案标签）与通用数据集规范不一致，评测者必须提供明确的格式对齐说明，严禁在脚本中编写臆造或推断答案的逻辑。

记录视图生成的实际有效行数（后续聚合命令的分母依据）：
```bash
VIEW_ROWS=$(wc -l < /tmp/priv-eval/private-eval-view.jsonl)
echo "Generated view rows: $VIEW_ROWS"
```

> 口径提醒：私有包声明 "6,541 条" 是 **items** 数；builder 一行 = 一个问题，本包 6,541 items 展开为 **7,990 个问题行**（本项目 2026-10-27 方式 2 实测构建结果，en-only、无 dropped 行）。**聚合分母用视图行数（问题行），不是 items 数**；若私有包版本不同，以 `wc -l` 实测为准。
> 该 holdout 未随包提供 target-types，builder 走 no_route 兜底 → 全部行的 route 记为 `classification`（route 分层因此不含 distillation；letter accuracy 不受影响）。

### 4.3 模型推理评测 (Base 与 Adapter)

分别对基线模型与微调模型执行推理评测。每次推理必须通过 `--predictions` 指定逐行预测保存路径（该文件仅留存在本地隔离环境，严禁外发）。

1. **基线模型 (Base 0-shot) 推理**：
   ```bash
   python -m finetune.eval_decision --eval-view /tmp/priv-eval/private-eval-view.jsonl \
     --model /path/to/models/Qwen3-1.7B --batch-size 32 \
     --predictions /tmp/priv-eval/base-preds.jsonl --json > /tmp/priv-eval/base-metrics.json
   ```

2. **微调模型 (Track A LoRA Adapter) 推理**：
   ```bash
   python -m finetune.eval_decision --eval-view /tmp/priv-eval/private-eval-view.jsonl \
     --model /path/to/models/Qwen3-1.7B --adapter /path/to/adapter --batch-size 32 \
     --predictions /tmp/priv-eval/tuned-preds.jsonl --json > /tmp/priv-eval/tuned-metrics.json
   ```

   > 评测器默认跳过 **>26 个选项** 与 **>4,000 字符 prompt** 的行（与训练同口径），跳过的原因与计数写在 `*-metrics.json` 的 `skipped_stats` 中；聚合时需要它（见 4.5）。

*提示*：若在纯 CPU 环境下运行，脚本将自动选择 CPU 执行，建议适当调小 `--batch-size 16`。

### 4.4 概率校准温度设定 (两条路径)

评测协议要求对微调模型的输出概率进行温度缩放（$p_T = \text{softmax}(\log p / T)$）。
**核心红线：保留测试集上绝对严禁重新拟合温度！必须使用预冻结的温度值执行 apply。**

评测者根据自身环境在以下两条路径中选择其一（推荐路径 A）：

- **路径 A（推荐：直接传入已冻结的温度值）**：
  温度由研发团队在**公开 validation 集**的 `calibration` 半区（`sha256(rid)` 为奇）拟合并冻结，文件为：
  `results/MODEL-02-final-eval/temperature.json`（字段 `temperature`；本次冻结值 = 1.xxxx，见该文件，不在本文硬编码）。
  在聚合阶段直接传入：`--temperature "$FROZEN_TEMP"`。
  **若冻结值缺失，请不要自行在保留集上拟合**：改用路径 B，或在聚合时省略温度（输出会标 `calibration.status = pending_temperature`，不得报告校准结论）。

- **路径 B（评测者独立拟合验证集温度）**：
  若评测者同时复跑了公开 `validation` 集的模型预测（例如生成了 `/tmp/priv-eval/val-preds.jsonl`），则可以在聚合命令中指定：
  `--fit-preds /tmp/priv-eval/val-preds.jsonl --fit-half calibration`
  聚合脚本将严格根据 `sha256(rid)` 奇偶切分规则，仅在 `calibration` 半区拟合最优温度 $T$，并将该拟合温度应用于保留测试集。

### 4.5 隔离环境内聚合计算

运行 `final_eval_aggregate.py`，将两个模型的逐行预测聚合为最终的汇总统计文件 `aggregate.json`：

先把推理阶段跳过的行数导出成 `skipped.json`（用两个模型各自 metrics 的并集应一致；不同就说明两次推理视图不一致，必须重跑）：

```bash
python - <<'PY' > /tmp/priv-eval/skipped.json
import json
base = json.load(open("/tmp/priv-eval/base-metrics.json", encoding="utf-8"))["skipped_stats"]
tuned = json.load(open("/tmp/priv-eval/tuned-metrics.json", encoding="utf-8"))["skipped_stats"]
assert {k: v for k, v in base.items()} == {k: v for k, v in tuned.items()}, (base, tuned)
print(json.dumps({k: int(v) for k, v in tuned.items() if v}, ensure_ascii=False))
PY
```

然后聚合（温度二选一：路径 A 给 `--temperature`，路径 B 给 `--fit-preds`；两者都不给则 calibration 标 `pending_temperature`）：

```bash
python -m finetune.final_eval_aggregate \
  --preds base=/tmp/priv-eval/base-preds.jsonl \
  --preds tuned=/tmp/priv-eval/tuned-preds.jsonl \
  --view-rows "$VIEW_ROWS" --skipped /tmp/priv-eval/skipped.json \
  --temperature "$FROZEN_TEMP" \
  --bootstrap-rounds 1000 --cluster-rounds 10000 --seed 20261023 \
  --out /tmp/priv-eval/aggregate.json
```

**口径说明**：
- 预期评测行数：`expected_evaluated = view_rows - skipped_total`；
- **配对区间以 group-cluster bootstrap 为主**（簇 = `rid` 的 `#` 前缀，10,000 次重采样，Δ 按行加权），item-level bootstrap 只作近似；输出含 `paired.cluster`（簇数 / 簇大小中位数 / Kish n_eff / reliability）。**report 里不得用更窄的 item 区间替代主区间**；
- **预注册判据不事后更改**：仍看「base 与 tuned 两独立 95% CI 是否不重叠」；配对 Δ CI 不含 0 但独立 CI 重叠时，只能写「配对分析显示正向差异；预注册门槛未满足」；
- **Fail-closed 保护**：默认任何行在预测中缺失（`missing > 0`）→ exit code 2，防止静默丢行夸大准确率；
- **缺失行口径**：`--allow-missing` 时缺失行按错误计入固定分母（`accuracy_with_missing` 为主口径），同时保留完成子集准确率（`accuracy`）与 `completed_only` 敏感性分析；**首选做法仍是重跑到完整覆盖**，不要靠 `--allow-missing` 交付。

### 4.6 导出前合规检查 (唯一出口关卡)

在把 `aggregate.json` 传出隔离环境之前，**必须**运行导出检查器进行自动化审查：

```bash
python -m finetune.check_aggregate_export --in /tmp/priv-eval/aggregate.json --json
```

**检查器检验内容（全部不通过即报违规）：**
1. **Schema 白名单**：只允许协议预注册的字段键名；
2. **禁止词扫描**：严禁出现任何匹配 `rid`、`id`、`prompt`、`text`、`question`、`answer`、`gold`、`pred` 等可能承载逐例样本的键；
3. **枚举值校验**：所有字符串必须命中预定义的白名单枚举；
4. **数值自洽性**：各分层样本数之和必须等于总样本数；正确数不得超过总数；Wilson CI 与 Bootstrap CI 必须包含点估计；校准前后准确率必须保持单调不变；
5. **体积与编码安全**：文件大小必须 $\le 256\text{KB}$，不含超长字符串、换行转义符或未受控字符。

**判定标准**：
- 输出格式形如：`{"status": "pass", "checks": 573, "bytes": 4820}` 且退出码为 `0`（`checks` 是实际执行的检查项计数，随内容略有变化）。
- **只有且仅有通过检查的 `aggregate.json` 允许带出隔离区！**
- 若检查未通过（exit code 2），严禁强行导出，评测者必须在隔离环境内排查原因。

### 4.7 环境清理与执行结果回报

1. **环境彻底清理**：
   在导出聚合文件后，立即安全删除本地临时目录内的全部逐例预测、中间视图与私有原始数据：
   ```bash
   rm -f /tmp/priv-eval/*-preds.jsonl
   rm -f /tmp/priv-eval/*-view.jsonl
   rm -f /tmp/priv-eval/items.jsonl
   rm -f /tmp/priv-eval/target-types.jsonl
   rm -f /tmp/priv-eval/*-metrics.json
   ```

2. **结果回报内容**：
   向项目维护团队仅回报以下两项内容：
   - 经过检查器验证通过的 `aggregate.json` 产物文件；
   - 一份运行环境简要摘要文本（参见下文第 7 节的提交报告模板）。

---

## 5. 行为准则：严禁与允许清单

| 类别 | 详细条款 | 违规后果与说明 |
|---|---|---|
| **严禁行为 (Prohibited)** | **禁止反馈调优 (No Feedback Loop)**<br>严禁依据保留集的整体得分、分层缺陷或错误案例，反向调整提示词、微调超参数、模型结构或判决阈值。 | 保留测试集彻底作废，该轮评测视为无效。 |
| **严禁行为 (Prohibited)** | **禁止导出逐例预测 (No Per-Item Export)**<br>严禁将带有 `rid`、选项明细、预测结果的 `*-preds.jsonl` 文件或中间视图移出隔离区。 | 严重违反数据隔离协议，视同私有数据泄漏。 |
| **严禁行为 (Prohibited)** | **禁止截图或留存日志 (No Logs / Screenshots)**<br>严禁在外部终端截取、复制或保存任何含有保留集具体题目文字的日志。 | 造成题目样本意外公开流传。 |
| **严禁行为 (Prohibited)** | **禁止在保留集上重拟合温度 (No Temperature Re-fitting)**<br>严禁在保留测试集上重新优化搜索温度参数 $T$。 | 打破预注册承诺，造成概率校准过拟合。 |
| **严禁行为 (Prohibited)** | **禁止挑选结果 (No Cherry-picking)**<br>一轮评测严格对应一个预注册且冻结的模型 Revision，不得多次尝试后只挑最高分报告。 | 破坏统计严肃性。 |
| **允许行为 (Permitted)** | **允许代码审计与哈希核验**<br>评测者有权对本包内所有 Python 脚本进行完整的离线代码静态审计。 | 确保执行逻辑透明受信。 |
| **允许行为 (Permitted)** | **允许更换硬件进行吞吐/精度复核**<br>允许在不同的 CPU 或 GPU 架构（如 NVIDIA / AMD / Intel）上交叉验证推理数值一致性。 | 验证模型跨硬件平台的数值稳定性。 |
| **允许行为 (Permitted)** | **允许如实报告异常与跳过行**<br>若评测过程中因长文本超限或格式不符跳过行，应当在聚合参数中如实反映并披露。 | 保证覆盖率完全透明。 |

---

## 6. 验收清单与评测范围界定

### 6.1 评测执行验收清单 (Checklist)
独立评测者在交付评测结果前，请逐项核对并确认：
- [ ] **完整性核查**：运行 `sha256sum -c CHECKSUMS.sha256` 全部返回 `OK`；
- [ ] **物理离线**：执行机器处于物理隔离或完全断网状态；
- [ ] **中性命名**：原始私有数据使用中性名称 `items.jsonl` 存放于库外临时目录；
- [ ] **视图对齐**：评测视图生成行数与声明的保留集规模一致（6,541 行）；
- [ ] **无静默丢失**：Base 与 Tuned 推理预测覆盖率符合口径，无意外静默跳行；
- [ ] **温度合规**：校准温度来自预先冻结设定，未在保留集上执行重拟合；
- [ ] **聚合生成**：成功运行 `final_eval_aggregate.py` 生成规范 `aggregate.json`；
- [ ] **检查器通过**：运行 `check_aggregate_export.py` 退出码为 0，且通过所有审计项；
- [ ] **现场清理**：已彻底删除隔离机上的所有 `*-preds.jsonl`、视图及原始数据副本；
- [ ] **唯一导出**：仅将合规通过的 `aggregate.json` 与环境元数据带出隔离环境；
- [ ] **披露异常**：若有未测项、跳过项或失败行，已如实记录在交付报告中。

### 6.2 评测范围界定 (包外与包内划分)
为避免独立评测者承担非必要的工作负担，本项目对评测任务进行了清晰的边界划分：
1. **本评测包覆盖范围**：
   - 保留测试集上的封闭选择决策能力（Overall 及分层 Accuracy）；
   - 配对 Bootstrap 统计置信区间；
   - 概率校准指标（NLL、Brier、ECE、MCE）。
2. **包外由研发团队（Session A）完成的基准测试（不属于本包范围，当前状态如实标注）**：
   - **通用能力防遗忘评测 (lm-evaluation-harness)**：`ceval-valid`/`cmmlu`/`mmlu`/`agieval`（limit 100）。base 侧已完成（均值 0.5342），**adapter 侧未测**（2026-10-23 系统崩溃中断），待 GPU 恢复后补跑；
   - **吞吐与延迟基准评测 (`bench_latency.py`)**：脚本已随包提供，**正式 p50/p95、tokens/s 与峰值显存尚未测量**（GPU 暂停），公开 test 的历史墙钟（batch 32）不是正式延迟基准。

---

## 7. 版本清单与审计元数据

### 7.1 版本信息对照表 (参见 MANIFEST.json)
独立评测者请对照 `MANIFEST.json` 核实以下关键对象的版本与哈希一致性：

| 实体对象 | 标识符 / 来源 | 冻结 Revision 或 SHA-256 依据 |
|---|---|---|
| **Base Model** | `Qwen/Qwen3-1.7B`（`MANIFEST.json → versions.base_model`） | Git Commit Revision: `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` |
| **Adapter (Track A)** | `track-a-e1-rocm/adapter`（`MANIFEST.json → versions.adapter`） | 6 个关键文件哈希记录在 `versions.adapter.files_sha256` 中：`adapter_model.safetensors`=`ad88db90…`、`adapter_config.json`=`16cea619…`、`chat_template.jinja`=`a55ee1b1…`、`tokenizer.json`=`be756060…`、`tokenizer_config.json`=`2e3bd3cb…`、`README.md`=`07282f39…`（完整 sha256 见 MANIFEST） |
| **评测协议** | `finetune/EVAL-PROTOCOL.md` | 预注册协议版本：`v1`（冻结于 2026-10-23） |
| **保留测试集** | 私有 Benchmark (6,541 条) | HuggingFace 托管对应：`NaturalDAO/pol-decision-general-v5-holdout@146ae4604e67c93805f6bf468449b45c205ca7da` |

### 7.2 评测执行提交报告模板
评测完成后，请独立评测者填写如下 Markdown 摘要，连同合规的 `aggregate.json` 一同交付：

```markdown
### Track A 决策模型保留测试集独立评测执行回执

- **评测执行人 / 机构**：[例如：Independent Auditor Team X]
- **执行方式**：[方式 1 独立评测者 / 方式 2 授权隔离执行]
- **执行日期**：YYYY-MM-DD
- **物理环境**：[完全离线禁网物理机 / 隔离虚拟环境]
- **硬件环境**：
  - 计算芯片：[例如：AMD Radeon RX 7900 XT 20GB / NVIDIA RTX 4090 24GB / CPU Only]
  - 操作系统：[例如：Ubuntu 24.04 LTS x86_64]
- **软件版本**：
  - Python: 3.12.x
  - PyTorch: 2.x.x
  - Transformers: 5.x.x
  - PEFT: 0.x.x
- **执行耗时**：
  - Base Model 推理耗时：XXX.X 秒
  - Adapter Model 推理耗时：XXX.X 秒
- **数据与行数核验**：
  - 视图总行数 (view_rows)：6541
  - Base 有效评测数：6541（缺失：0，跳过：0）
  - Tuned 有效评测数：6541（缺失：0，跳过：0）
- **校准温度应用路径**：[路径 A 直接指定冻结值 <FROZEN_TEMP> / 路径 B 在 validation calibration 半区拟合并冻结]
- **导出检查结果**：
  - check_aggregate_export 执行退出码：0 (PASS)
  - 聚合文件大小：XXXX 字节 (<= 256KB)
- **异常与失败项声明**：
  - [若全流程正常，填写“无异常；全部分层与配对统计均已正常计算完成”]
```
