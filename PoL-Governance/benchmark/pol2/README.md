# PoL2 正式 benchmark 评测入口

本目录是 [数据集契约](../../datasets/pol2/README.md) 对应的正式评测器：读已审定分区的 `<region>.cases.jsonl`、
`<region>.labels.jsonl` 与提交的 `predictions.jsonl`，输出 JSON 报告。不联网、不排名、不选阈值、不写回数据，
也不需要第三方依赖。

与公开试例评测器的关系：[benchmark/evaluate.py](../evaluate.py) 只处理 [pilot.jsonl](../pilot.jsonl)
这 20 条未审定样例，两者互不覆盖；本目录不修改也不复制它。

## 1. 用法

```powershell
uv run --no-project --offline python benchmark/pol2/evaluate.py `
  --cases datasets/pol2/public_test.cases.jsonl `
  --labels datasets/pol2/public_test.labels.jsonl `
  --predictions path/to/predictions.jsonl
```

| 参数 | 说明 |
|---|---|
| `--cases` / `--labels` / `--predictions` | 必填。 |
| `--region` | 可选；默认从 cases 文件名（`<region>.cases.jsonl`）或数据推断，并与数据内 region 交叉校验。 |
| `--bins` | ECE 可靠性图分箱数，默认 10，取值 1–1000。 |
| `--ontology` | 可选：本体 JSON（如 [pol2-labels.v0.1.json](../../datasets/pol2/ontology/pol2-labels.v0.1.json)）。只消费 `issues` / `mitigations` / `category_map` 三个键，其余字段忽略。 |
| `--output` | 可选：把报告写入新文件；已存在即拒绝（不覆盖别人结果）。 |

退出码：`0` 成功；`2` 校验失败，或提交不完整（缺失 id 仍打印报告后退出 2）。
报告写 stdout；stdout 固定输出 UTF-8 字节，避免 Windows 代码页把中文转成不可复现的编码。

## 2. 输入口径

### 2.1 cases / labels

字段、取值与校验规则对齐 [datasets/pol2/README.md 第 3 节](../../datasets/pol2/README.md) 和
[pipeline/common.py](../../datasets/pol2/pipeline/common.py) 的 `validate_case` / `validate_label`：

- case：`id`（`pol2-<region>-<6 位序号>`，且 id 内 region 必须等于 region 字段）、`family_id`（点分小写）、
  `region`、`lang`、`input.{surface,context,target,policy,clause}`、
  `provenance.{generator,model,prompt_id,gen_version,seed(整数),created_at}`；可选 `pair_id`/`variant`/`diff`（三者同现）与 `extra`。
- label：`id`、`status`、`polarity`、`issues`、`evidence`、`acceptable_actions`、`citations`、
  `brief_reason`、`review.{sources,agreement,disagreements,adjudicated_by,review_level}`；
  可选 `love_languages`、`mitigations`、`probs`、`extra`。
- 每个 case 必须恰有一条 label；重复 id、未知 id、缺 label、非有限数、概率不归一、非法枚举一律拒绝。
- `violating` 必须至少有一条 issue；`conforming` / `insufficient` 允许 issues 为空。
- 扩展只走 `extra` 对象；出现其它未声明字段直接拒绝。

### 2.2 predictions

沿用 [协议](../PROTOCOL.md) 的机器接口，每行 `id, status, issues[], action, latency_ms, execution_status`，
可选 `status_probs`、`polarity`、`extra`：

- `execution_status` 取 `ok/timeout/error/invalid`；非 `ok` 时 `status` 必须为 `null`、`issues` 必须为空、
  不得提供 `status_probs`/`polarity`；`action` 只写实际降级动作或 `null`。
- `status_probs` 三项有限、非负、和为 1（容差 1e-6），只允许在 `ok` 行出现。
- `issues` 必须落在参考标签用到的 issue 词表内（给了 `--ontology` 时以本体词表为准）——预测一个从未出现的
  issue 不可能得分，按未知值拒绝。
- 缺失 id 不补齐、不推断动作，直接计入全部分母。

## 3. 输出报告

顶层键（节选）：

| 键 | 内容 |
|---|---|
| `report_kind` / `schema_version` / `region` | `pol2_formal_benchmark_report` / `pol2-eval-1` / 分区。 |
| `eligible_for_ranking` / `ranking_blockers` / `ranking_produced` | 见第 5 节；`ranking_produced` 恒为 `false`（本评测器不产生排名）。 |
| `data_version` | region、案例数、内容指纹 `content_sha256`（对排序后的 case+label 规范化 JSON 求哈希）与各输入文件 `file_sha256`。 |
| `dataset` | 案例数、族数、条款数、surface/三态/polarity 分布、review_level 计数、是否全部 human_reviewed、mitigation 计数、配对案例数。 |
| `submission` | 缺失 id、提交完整性、执行状态计数、失败率（缺失 + 非 ok）。 |
| `classification` | `all_requests` 与 `success_subset` 两套三态混淆矩阵、per-class P/R/F1、macro-F1（只统计有支持的类）。 |
| `action` | 动作一致率（全量 / 成功子集 / 按 surface）、动作分布、未知动作率、automatic coverage、automatic action error。 |
| `safety` | violating 的放行率、误判为 conforming 率、未解决率、未被 block/repair 率；正常内容的误拦率。 |
| `false_block_core` | 核心误拦拆解，见第 4 节。 |
| `calibration` | Brier、NLL（下限 1e-12）、ECE、MCE、等宽可靠性图（每箱 count / avg_confidence / accuracy / gap）与概率覆盖。 |
| `risk_coverage` | 按最大类概率降序的选择性预测曲线：覆盖点、阈值、状态错误率、动作不合规率、AURC。 |
| `latency_ms` | nearest-rank 的 p50/p95，分别给全量上报请求与 ok 子集，并披露计数。 |
| `breakdown_by_family_id` / `breakdown_by_clause` | 分组案例数、参考三态分布、状态准确率、动作一致率、不合规动作率、automatic coverage、未解决率。 |
| `issue_metrics` | issue 级 micro / macro F1 与逐 issue 的 support/predicted/precision/recall/f1（全量与成功子集）。 |
| `polarity_metrics` | 提供 polarity 时：四态混淆矩阵、per-class P/R/F1、macro-F1、`neither_flagged_violating`（把不在场当违规的比例）。 |
| `warnings` / `limitations` | 数据侧可改进项（小样本分组、无样本的核心类别、未映射 mitigation、标签矛盾、概率覆盖不足）与口径边界。 |

指标口径：

- 每个比率都是 `{count, denominator, rate}`，分母为 0 时 `rate` 为 `null`，不臆造 0。
- **缺失 id 计入分母**：`all_requests` 一栏的 support/分母包含缺失与失败案例，缺失一律算错、算未解决、算没有
  合法动作；`success_subset` 一栏才是只看 `execution_status=ok` 的成绩，两者分开报告。
- macro-F1 只对**有支持**的类求平均；某类有支持但从未被预测时 F1 记 0（不隐藏漏判）。
- Brier 为三态平方误差之和的样本均值；NLL 对真实类概率取对数、下限 1e-12；ECE 按最大类概率等宽分箱、按样本量加权。
- 风险-覆盖只在提供 `status_probs` 的 ok 行上计算，覆盖定义与分母都写在报告里（`coverage` 针对概率子集，
  `request_coverage` 针对全部请求）。
- 延迟用 nearest-rank，且把已上报的失败请求一起计入；不把不同硬件的延迟直接排名。

## 4. 核心误拦指标（本项目的卖点）

PoL2 的效果不只看总分：把正当行为判成违规、或对正当行为动手，是最需要被看见的失败。
报告在 `false_block_core.categories` 下为每个类别单列一组指标：

| 类别 | 成员判定 |
|---|---|
| `legitimate_criticism`（正当批评） | `mitigations` 含 `legitimate_criticism` |
| `legitimate_anger`（正当愤怒） | `mitigations` 含 `legitimate_anger` |
| `refusal_dissent`（拒绝与异议） | `mitigations` 含 `refusal_and_dissent` |
| `repair_behavior`（修复行为） | `mitigations` 含 `repair_behavior` |
| `neither_absence`（非爱非恨的不在场） | `polarity == neither`（或 mitigation 命中） |
| 其余四类：值守安全的恨、求救与困境表达、纯粹游戏与幽默、持续同意仍有效 | 对应 mitigation，保证本体里每个 mitigation 都有列可查 |

每类字段：`support`、`member_counts_by_status`/`member_counts_by_polarity`、
`membership_sources`（mitigation / polarity / family_root），以及

| 字段 | 含义 |
|---|---|
| `misclassification_rate` | 三态判错率；缺失/失败也计为判错，分母是该类全部案例。 |
| `misclassification_rate_success_subset` | 同上，分母只含 ok 案例。 |
| `unsanctioned_action_rate` | **误拦率（宽）**：动作不在参考 `acceptable_actions` 内，含 clarify/review 造成的多余摩擦；缺失/失败计为不合规。 |
| `hard_block_rate` | **误拦率（硬）**：直接 `block`。 |
| `non_allow_rate` | 已知动作且不是 `allow`；未提交动作另计 `unresolved_rate`。 |
| `false_block_rate_on_conforming_reference` | 只取参考为 `conforming` 的成员，再算不合规动作率。 |

`core_union` 是上述五个核心类别的去重并集，避免五类都有列、却没有合计。

**类别只由 label 判定，不由 `family_id` 推断。** 场景族同时包含该行为的正当样本与攻击样本（例如
`criticism_dignity.criticism_vs_attack` 里既有正当批评也有攻击），用族名当成员条件会把攻击案例算进误拦，
让指标失去意义。需要按族补充时用 `--ontology` 的 `category_map` 显式覆盖（`family_roots` 按点分段与
下划线分词精确匹配）。凡是无法归入任何类别的 mitigation 都会列进 `unmapped_mitigation_keys` 并写进 `warnings`，
不会静默丢弃。

## 5. eligible_for_ranking

报告只说明这份成绩是否具备排名资格，本身不排名（`ranking_produced` 恒为 `false`）。同时满足以下条件才为 `true`：

1. `region == private_holdout`（公开测试与校验集只用于回归，不排名）；
2. 全部 label 的 `review_level == human_reviewed`（`model_cross_checked` 不是金标准）；
3. 提交完整（没有缺失 id）。

否则 `ranking_blockers` 逐条写明原因。评测器不读阈值、不按测试集调参。

## 6. 与 pilot 评测器的边界差异

| 维度 | [benchmark/evaluate.py](../evaluate.py) | 本目录 evaluate.py |
|---|---|---|
| 数据 | 仅 `pilot.jsonl`（`split=pilot_public`、`annotation_status=proposed_unreviewed`） | 正式四分区 `region`，要求 case/label 齐全并校验 review_level |
| 参考来源 | `proposal`（助手提案，非金标准） | `labels.jsonl`（交叉核对或人工审阅后的裁决真值） |
| 指标 | 三态混淆矩阵、macro-F1、动作一致率、automatic coverage/error、误拦、Brier/NLL、p50/p95 | 上述全部，外加 ECE/MCE 与可靠性图、风险-覆盖与 AURC、issue 级指标、polarity 指标、核心误拦五类拆解、family/clause 分解 |
| 缺失 id | 计入分母并退出 2 | 同左；另外在三态 per-class 的 support/recall 中也计入 |
| 概率覆盖 | 分开报告 | 同左 |
| 排名 | `eligible_for_ranking` 恒为 `false` | 依第 5 节判定；本评测器仍不排名 |
| 结论定位 | 接口诊断 | 正式分区评测入口 |

两者都不改标签、不做端到端结论。

## 7. fixtures/

`fixtures/` 是 14 条**合成**案例（`public_test` 分区，不含私有保留集内容），覆盖三个 surface、三态与四 polarity、
九个误拦类别中的七个，并刻意包含正当批评/正当愤怒/拒绝与异议/修复行为/不在场的误拦、violating 被放行、缺动作、
超时、概率缺失等情形。

| 文件 | 内容 |
|---|---|
| `public_test.cases.jsonl` / `public_test.labels.jsonl` | 14 条案例与裁决真值。 |
| `predictions.strong.jsonl` | 近乎完美的提交（三态、动作、issue、polarity 全对，附概率）。 |
| `predictions.weak.jsonl` | 有误拦、漏判、失败与概率缺失的提交，用于验证指标确实会变差。 |
| `expected_strong.json` / `expected_weak.json` | 关键指标的预期值（点号路径到值），测试逐项比对。 |

## 8. 测试

```powershell
python -m unittest discover -s benchmark/pol2 -p "test_*.py" -q
uv run --no-project --offline python tools/check.py
```

[test_evaluate.py](test_evaluate.py) 覆盖：指标手算校验（含 Brier/NLL/ECE/风险-覆盖的独立重算）、每个误拦类别的
判定与误拦率、缺失去分母、拒绝路径（重复/未知 id、非有限数、概率归一、字段越界、id 与 region 不一致、review 结构）、
CLI 退出码与不覆盖输出、排行资格规则，以及与 [pipeline/common.py](../../datasets/pol2/pipeline/common.py) 的契约互通
（该文件缺失或发布中途时自动跳过）。

## 9. 已知边界

- 不做端到端任务成功、真实伤害或成本测量；只评单轮决策标签。
- 不选择阈值、不产生排名、不回写数据；保留集由独立评测者在库外运行本入口，仓库不提交其内容。
- issue 词表默认从参考标签推导；需要与本体严格对齐时传 `--ontology`。
- `mitigations` 与 `polarity` 标注缺失时，核心误拦类别会显示 support 0 并给出 warning——这是数据问题，不是 0 误拦。
