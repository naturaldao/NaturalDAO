# 训练视图（general v5 → 决策模型微调）

本文件定义**统一训练视图**：把通用决策数据集 v5 的公开分区转换成「一行 = 一个问题」的 JSONL，
供第二阶段决策模型微调（Track A 字母 SFT / Track B 候选评分头）直接消费。生成器是
[build_training_view.py](build_training_view.py)，只用标准库、离线、确定性。

依据：[SPEC](../../SPEC.md)、[CONTRACT.md](CONTRACT.md)、[TRAINING.md](TRAINING.md)。

## 1. 生成与复算

先确认输入文件在本机（数据实体不入库，从 HF 或本机缓存获取；见 [HF.md](HF.md)）：

```powershell
# 生成通用决策数据集统一训练视图
python datasets/general/build_training_view.py --split train --out D:/pol2-train/data/general-train-view.jsonl
python datasets/general/build_training_view.py --split validation --out D:/pol2-train/data/general-validation-view.jsonl
python datasets/general/build_training_view.py --split test --out D:/pol2-train/data/general-test-view.jsonl
```

- 默认输入：`data/splits/<split>.jsonl.gz` + `data/target-types.jsonl.gz`（训练路由旁挂件）。
- CLI 可选参数：
  - `--items <path>`：指定分区文件路径（默认为 `data/splits/<split>.jsonl.gz`）；
  - `--target-types <path>`：指定旁挂路由文件（默认为 `data/target-types.jsonl.gz`）；
  - `--split {train,validation,test}`：指定分区；
  - `--out <path>`：输出 JSONL 文件路径；
  - `--manifest <path>`：清单 JSON 路径（默认 `<out>.manifest.json`）；
  - `--limit N`：仅处理前 N 行（用于快速冒烟）；
  - `--json`：向 stdout 打印 manifest JSON 摘要；
  - `--strict-route`：严格禁止无旁挂 target 兜底，未覆盖 target 全部跳过（计入 `skipped.no_route`）。
- 退出码：0 为正常完成；2 为安全护栏触发或数据校验失败。

## 2. 行 schema（冻结，template_version = tv-1）

一行一个 JSON 对象（JSONL，UTF-8，无 BOM，按 `(item_id, question_key)` 升序排列，逐字节确定性）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `rid` | string | `<item_id>#<question_key>`，全局唯一，冲突时报错 |
| `src` | string | 固定 `"general-v5"` |
| `split` | string | `"train"` | `"validation"` | `"test"` |
| `lang` | string | 原始语言，如 `"en"`、`"zh"` |
| `domain` | string | 覆盖域，如 `"knowledge_reasoning"`、`"risk_harm"` |
| `kind` | string | `"choice"` | `"noul"` | `"score"` |
| `prompt` | string | 渲染后的完整题面（见下文模板） |
| `options` | string[] | 选项 key 列表（score 为 `"min".."max"` 字符串列表） |
| `option_labels` | string[] | 展示文字（choice/noul 取来源 label，缺省用 key；score 用数字字符串） |
| `answer_idx` | int | 正确选项硬标签下标（对应 options 索引，0-based） |
| `soft` | float[] | null | 软分布（仅 distillation 路由且 probs 非退化时，已归一并与 options 对齐；否则 null） |
| `soft_conf` | string | null | 软标签置信度：`"high"` | `"medium"` | `"low"` | null（来自 target-types 的置信度标记） |
| `scale` | object | null | score 量程 `{"min": int, "max": int}`，choice/noul 为 null |
| `route` | string | 训练路由：`"classification"`（分类交叉熵）| `"distillation"`（软目标蒸馏） |
| `source_slug` | string | 来源标识，取 `meta.native_source` 或 `source.slug`（供能力维重加权） |
| `template_version` | string | 当前固定为 `"tv-1"`；**改模板必须升版本并重生成全部视图** |

## 3. 渲染模板（冻结常量 tv-1）

模板文本：

```text
你是只做封闭选择的决策模型：给定情境、问题与候选选项，只选择一个最合适的选项，不解释、不输出其他文字。

【情境】
{state}

【问题】
{prompt}

【选项】
A. {option_labels[0]}
B. {option_labels[1]}
...
```

- **选项字母标号**：采用双射进位字母编码（0→`A`、25→`Z`、26→`AA`、27→`AB`…），全量保留全部选项（2–69 档）。
- **与训练脚本的职责分离**：
  - **训练视图**完整保留所有合法样本（包含选项数 >26 的长列表样本），供支持变长评分头的模型（Track B）使用；
  - **Track A 单字母微调器**（[finetune/](../../finetune/)）：在样本加载器构造输入时跳过选项 >26 的样本并计数（[decision_common.py](../../finetune/decision_common.py) 的 `options_gt_26` 护栏）。

## 4. 过滤与路由规则

1. **连接 target-types 旁挂件**：以 `(item_id, question_key)` 为键 join `target-types.jsonl.gz`。
2. **未被旁挂件覆盖的 target**：
   - 依据 [TRAINING.md](TRAINING.md) §1.1，中文补充集（`db-zhtax-*`，3,148 条，仅追加于 train 尾部）不在冻结语料内，因此未写进旁挂件；
   - 默认模式：按其自身形态兜底为 `classification` 硬标签，计入 `fallbacks.classification_without_route`（共 3,148 条）；
   - 若开启 `--strict-route`：不进行兜底，未覆盖行全部计入 `skipped.no_route`。
3. **剔除规则**：
   - `training_route == "drop"`：剔除无信息均匀流与并列占位（计入 `skipped.drop`）；
   - 软分布退化：distillation 路由下 probs 缺失、全 0 或各分量完全相等时剔除（计入 `skipped.degenerate_soft`）；
   - 选项不匹配：答案未出现在 options 与 option_labels 中（计入 `skipped.answer_not_in_options`）；
   - 量程越界：score 答案非整数或超出 scale 量程（计入 `skipped.answer_out_of_range`）；
   - 目标缺失：既无 answer 且无可用 probs（计入 `skipped.no_target`）。
4. **确定性与排序**：所有 rows 按 `(item_id, question_key)` 升序排序输出，两次运行逐字节完全一致。
5. **安全护栏**：`--items` 输入路径文件名包含 `benchmark`、`holdout` 或 `private`，或 `--split benchmark` 时，生成器**拒绝运行**（exit 2），杜绝内部保留集泄漏风险。

## 5. 本次生成结果（v5，2026-10-22）

生成文件位于仓库外 `D:/pol2-train/data/`：

| 分区 | 行数 (rows) | choice | noul | score | classification | distillation | skipped (drop) | fallbacks (zh-supp) | 输出 SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **train** | **51,947** | 42,694 | 5,082 | 4,171 | 48,054 | 3,893 | 1,052 | 3,148 | `a136c2a1f731bbff0565f5e6e0bb7dc62689745c8ff9e550ce433274a581c0dd` |
| **validation** | **8,177** | 7,156 | 573 | 448 | 7,598 | 579 | 184 | 0 | `b936c61812ab41337462b528fbbeeecd7bf63e2b7951db8f362c3b6437f4ee81` |
| **test** | **16,306** | 14,266 | 1,107 | 933 | 15,018 | 1,288 | 335 | 0 | `2235f0b74444194ab427a5536e5e89e4afc3e63d89a2bc23412d60beb80ec661` |
| **合计** | **76,430** | 64,116 | 6,762 | 5,552 | 70,670 | 5,760 | 1,571 | 3,148 | — |

### 口径对账说明

1. **train 分区**：问题总数 52,999 − 剔除 `drop` 1,052 = **51,947**。其中包含 3,148 条中文安全补充集（`db-zhtax-*`），按 [TRAINING.md](TRAINING.md) §1.1 / §4.2 走 `classification`；若开启 `--strict-route` 排除该补充集，则为 **48,799** 行（48,799 + 3,148 = 51,947，恒等式严格闭合）。
2. **validation 分区**：问题总数 8,361 − 剔除 `drop` 184 = **8,177**（与 [TRAINING.md](TRAINING.md) §4.2 逐条一致）。
3. **test 分区**：问题总数 16,641 − 剔除 `drop` 335 = **16,306**（与 [TRAINING.md](TRAINING.md) §4.2 逐条一致）。
4. **剔除分布**：公开三分区剔除合计 1,571 条（train 1,052 + val 184 + test 335），全部由 `training_route == "drop"` 触发，无因格式错误、标签解析失败等异常跳过。

## 6. 测试与验收

离线单元测试集覆盖全部规范与护栏，不依赖真实大文件：

```powershell
python -m unittest datasets.general.test_build_training_view -v
```

测试通过项：
- `test_classification_and_noul`：choice 键/展示文本匹配、score 量程下标转换、noul 选项解析；
- `test_distillation_soft_alignment_and_normalization`：缺失键补 0、软分布归一化、argmax/gold 标签判定与置信度；
- `test_skip_counts_and_fallbacks`：drop、no_route、answer_not_in_options、answer_out_of_range、degenerate_soft 跳过计数；
- `test_prompt_rendering_and_bijective_letters`：提示词模板渲染及 27+ 选项时的 A..Z, AA 双射字母进位；
- `test_deterministic`：两次独立构建 SHA-256 逐字节一致；
- `test_benchmark_guard_exit_2`：输入路径包含 benchmark/holdout 时拒绝执行（exit 2）；
- `test_rid_conflict_and_invalid_options`：重复 rid、非法选项数（<2）或非法 scale 边界报错；
- `test_strict_route_flag`：`--strict-route` 开关对未覆盖行的精确过滤。
