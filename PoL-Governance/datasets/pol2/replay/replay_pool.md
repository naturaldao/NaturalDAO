# PoL2 通用决策回放池 数据卡（pol2-replay-v0.1）

- ID / 版本：`pol2-replay-v0.1`（起草于 2026-09-30，尚未取数）
- 来源 / 许可：15 个 HuggingFace 数据集的 train 分区，逐条许可与固定 revision 见 [survey.md](survey.md) 第 3 节与 [candidates.json](candidates.json)
- 内容位置：**本仓库不放数据本体**。每条来源用 `数据集 id + 固定 commit sha` 登记；
  取数与改写产物写在仓库外的池目录（建议 `<仓库外>/pol2-replay/<version>/`），仓库只保存流程、审计表与汇总计数
- 语言 / 场景：来源为英文（`najdresearch/system-one` 含阿语）；**入池前一律经英译中改写 + 教师重判**，
  池内以中文为主，保留英文原件作对照
- 生成方法 / 教师版本 / 人工审阅状态：来源以合成与既有数据集规范化为主（详见下表）；
  5 个来源含教师蒸馏（其中 `shreyanbr/system-one-training-pairs` 为闭源 Claude Haiku 4.5，必须点名）；
  **回放池不做人工逐例审阅**，其标签不作为 PoL 真值，只用于「别把通用判断力练丢」
- 数量：**train-only**，无 public_test / validation-dev / validation-calibration / private_holdout；
  另从准入 train 行中按 group 预留 2% 作 `replay-dev`（只用于通用能力回归，不进训练）
- 去重与跨分区检查：见第 4 节（内容哈希 + group 级 + 跨来源 + 语义近重复四道）
- 保留集保管与统一评测方式：回放池**不设私有保留集**；PoL 的 5% 保留集由独立评测者在库外保管，
  回放池不接触、不采样、不用于调阈值
- 已知偏差 / 未解决争议：来源以英文与合成任务为主，业务域偏 IT/客服/工单；`tasksource` 与
  `HIT-TMG/JevEmbed-Data` 的许可为逐行/逐子集，必须按行过滤；卡面声明（「已排除评测基准」「0% 重叠」）
  尚未抽检
- 复现命令：见第 8 节

## 1. 池的定位

回放池**不是**第二个 PoL 数据集，也不产生 PoL 标签。它的唯一作用写在
[SPEC.md](../../../SPEC.md) 与 [datasets/pol2/README.md](../README.md) 里：让模型在学 PoL 判据的同时，
继续复习「信息是否充分、规则是否适用、是否命中例外、普通业务风险多大、哪条证据更相关」这些基本功，
防止把中性内容道德化、防止丢掉 `insufficient` 这一档。

因此：

- 回放样本**不引用 PoL2 条款**，不进 `input.policy/clause`，不参与 PoL 真值裁决；
- 回放池的标签只来自**改写后的中文重判**，绝不来自英文原标签；
- 回放池的产物与 `datasets/pol2/` 下的四类记录（case/question/answer/label）**物理分开放**，
  文件名、目录、划分都不共用。

## 2. 准入与禁用清单

**准入（15）**：`ZefanCai/Open-Jev`、`tasksource/procedural-typed-decisions`、
`tasksource/tasksource-jev-typed-decisions`、`dwidlee/systemone-lite-general`、`dwidlee/systemone-lite-phase2`、
`kaivoss/system-one-270m-data`、`soyrsoyr/jev-playground-rlcd-v0`、`HIT-TMG/JevEmbed-Data`、
`najdresearch/system-one`、`helmo/synthetic-typed-decisions`、`n4ze3m/typed-decisions-synth`、
`DavidHatley/system-one-mini-data`、`fastino/fast-decisions`、`samatv256/jev-decisions-v1`、
`shreyanbr/system-one-training-pairs`。逐条条件见 [survey.md](survey.md) 第 3 节。

**禁用（任何情况下不进训练池）**：

1. **评测集 / 对抗考卷本体及其衍生**（22 条，含 `LocalLLaMA/typed-decisions` 与它的日/葡/俄译本、
   `Praveenrajus/jev-bench`、`AirsideLabs/notam-typed-decisions`、`s1lv3rj1nx/openjev-heldout`、
   `Nebulaw1/jev-legal-judgment-tests` 等）。[audit.py](audit.py) 的 `verify` 会让「评测集被 admit」直接失败。
2. **train 分区内含公开评测基准的混合包**（`s1lv3rj1nx/openjev-mixture` 的 train 里有 92 个公开评测任务）。
3. **无真值 / 标签已知错误**（`com-kotobalabs/typed-decisions-repo-governance`、`pngwn/typed-decisions` v1）。
4. **许可不明**（卡面无 license 字段）或 **NC**（非商业）来源。
5. **任何 test / validation / OOD / holdout / leaderboard 分区**，无论来源多干净。
6. 任何 PoL 的 `public_test`、`validation`、`private_holdout` 内容（也不允许用它们造回放样本）。

## 3. 配比：通用:PoL = 9:1 或 8:2（按**决策数**，只有 PoL train 参与）

SPEC 的起点是 `通用:PoL = 9:1 或 8:2`，并要求「按训练决策数记录，同时报 token 数与损失权重」。
PoL2 的规模是 **96 族 × 112 案例 = 10,752 案例**，其中 **70% train ≈ 7,526 案例**
（pilot：17 族 × 112 = 1,904 案例）。每个 case 派生的决策数 `k` 取决于跑到哪些 key：
基础 4 个 choice（`status/action/polarity/evidence`）+ 15 个 `issue.*` noul + 可选 1 个 `severity` score，
即 `k ∈ [4, 20]`。

| PoL train 决策数 | 9:1 需要的回放决策数 | 8:2 需要的回放决策数 |
|---|---:|---:|
| 7,526 × 4 = 30,104 | 270,936 | 120,416 |
| 7,526 × 19 = 142,994 | 1,286,946 | 571,976 |
| 7,526 × 20 = 150,520 | 1,354,680 | 602,080 |

准入池的已知容量（train 行/判定数，未计入未知规模的 4 个来源）：`HIT-TMG/JevEmbed-Data` 1,601,157、
`tasksource/tasksource-jev-typed-decisions` 2,500,000、`ZefanCai/Open-Jev` 266,793、
`dwidlee/systemone-lite-phase2` 240,800、`samatv256/jev-decisions-v1`（clean50k）50,000、
`dwidlee/systemone-lite-general` 32,400、`kaivoss` 25,002、`soyrsoyr` 25,000、`DavidHatley` 20,000、
`najdresearch` 3,284、`fastino` 1,700 —— 合计 **> 470 万**，两种配比都够，不需要降低准入门槛。

混合硬约束：

- **只有 PoL 的 train 分区参与混合**；`public_test` / `validation` / `private_holdout` 一律不掺入，
  也不用于教师造数与改写。
- 回放池自身**只用各来源的 train 分区**；`ZefanCai/Open-Jev` 这类来源另有 calibration/validation/OOD，
  同样不取（避免与外部评测口径混淆）。
- 比例按**同一训练轮里实际使用的决策数**计算；同时登记 token 数（写明 tokenizer 与版本）与损失权重，
  并在结果卡披露。比例可以实验，但起点必须是 9:1 或 8:2 之一。
- **单一来源不得超过回放池的 30%**，避免某一个制造者的偏差成为池子的主旋律。

## 4. 去重策略

| 层级 | 规则 | 实现 |
|---|---|---|
| L1 内容哈希 | 改写后的中文 `state + question + options` 经 NFKC 与空白归一后取 sha256，作为 `dedup_key`；同键只保留一条 | [rewrite.py](rewrite.py) 的 `dedup_key()` / `verify_records()`（改写后**重算**，不是照抄英文的键） |
| L2 group 级 | 同一 `group_id`（同 state 的多个问题、同族的反事实）整体进同一边，禁止跨 train / replay-dev | 取数脚本按 `group_id` 分组切分；来源自带 split 的（`kaivoss` 的 `state_id`、`najdresearch` 的 case、`soyrsoyr` 的 state）沿用来源分组 |
| L3 跨来源 | 同一批数据的多个再发布要去重：`ZefanCai/Open-Jev`、`TypeSafeAI/Open-Jev`、`OpenAGILab/Jev-dataset`（236 文件、README 逐字节相同）；两个 `tasksource` 数据集含相同行；评测集译本已整库剔除 | 按文件 sha256 / 行内容哈希比对后再入池 |
| L4 语义近重复 | 同情节的翻译与改写视为同一条（SPEC「同情节、翻译和改写不得跨区」）。用教师对 `state+question` 做近重复判定，阈值与 PoL 专项一致并记录 | 取数批次内一次性完成（与改写重判同批，避免重复付费） |

与 PoL 的对撞筛查：可以用 PoL 的 `public_test` 与 `validation` 的 question 文本做词面/语义比对
（这两区对生成 Agent 可见），但 **`private_holdout` 内容不可见，因此回放池不承诺与保留集零重合**；
保留集由独立评测者在库外统一跑，回放池不参与调阈值，这个限制必须在结果卡写明。

## 5. 质量门（每条回放记录都要过）

| 门 | 规则 | 不通过时 |
|---|---|---|
| G1 许可门 | 来源必须在 `candidates.json` 中 `tier=admit`，行级许可在 `{cc0-1.0, cc-by-4.0, cc-by-sa-4.0, mit, apache-2.0, bsd-2/3-clause}` 内 | 拒收该行并计数 |
| G2 分区门 | `split == train`；出现 test/validation/ood/holdout 直接拒 | 拒收整批 |
| G3 溯源门 | 每行必须有 `dataset/revision/line_number/license/group_id`，revision 为 40 位 sha | 拒收 |
| G4 去重门 | 通过第 4 节 L1–L4 | 保留最早一条并记录 |
| G5 捷径门 | 标签不能从输入直接读出（例如问题里带答案、只靠礼貌/情绪词就能判对）；抽样检查标签捷径 | 整族标记复核 |
| G6 重判门 | 改写后必须由**另一血缘**教师独立作答；`label_source == "judge"`；教师看不到英文标签 | 拒收；[rewrite.py](rewrite.py) `verify` 强制 |
| G7 血缘门 | 回放池的生成/重判血缘记录在案，且不得与 PoL 真值教师同源充当交叉验证；闭源教师必须点名 | 记录并披露 |
| G8 比例门 | 混合后按决策数核算通用:PoL；记录 token 数与损失权重 | 阻断训练配置 |
| G9 披露门 | 若某个来源的 benchmark 开发分区被用过（如 `fastino/fast-decisions`），必须在该 benchmark 相关结果卡披露 | 结果卡必须写明 |

## 6. 能力覆盖映射（为什么这 15 个来源够用）

| SPEC 要求的复习项 | 对应来源 |
|---|---|
| 信息是否充分 | `tasksource/procedural-typed-decisions`（`evidence_sufficiency` 的 `claim_supported`/`has_conflict`）、`dwidlee/systemone-lite-general`（`debate.enough_evidence`）、`kaivoss`（`ambiguity` 三档）、`soyrsoyr`（contradictory 档） |
| 某项规则是否适用 | `tasksource/procedural-typed-decisions`（`policy_applicability`、`policy_under_uncertainty`）、`najdresearch/system-one`（政策前置条件与澄清） |
| 是否命中例外条件 | `tasksource/procedural-typed-decisions`（`state_perturbation` 的 `material_change`、`risk_direction`）、`najdresearch`（`incomplete` 计数） |
| 文本表达的普通意图 | `fastino/fast-decisions`（17 域业务路由）、`dwidlee`（`ticket.route`）、`tasksource`（分类/多选） |
| 低/中/高风险 | `dwidlee`（`ticket.urgency`）、`DavidHatley`（五档标签）、`najdresearch`（score 题）、`fastino`（升级判断） |
| 哪个候选更符合证据 | `ZefanCai/Open-Jev`（citation 的 supported/contradicted/insufficient）、`tasksource`（`strongest_support_origin`）、`samatv256`（Choice 选择） |

## 7. 与 PoL 专项数据的关系

- **不混放**：回放池产物（`*.zh.records.jsonl`）与 PoL 的 `<region>.cases/questions/answers/labels.jsonl`
  不在同一目录、不同文件名、不同 schema，禁止写进 `datasets/pol2/` 的分区文件。
- **不参与造数与真值**：回放池的样本与标签不进入 PoL 的教师池、不参与裁决、不影响 `review_level`。
- **只在训练阶段汇合**：训练脚本分别读入 PoL train 与回放池 train，按第 3 节的决策数配比混合；
  其余分区不参与。
- **独立回归**：`replay-dev`（准入 train 行的 2%，按 group 切）只用于「通用能力是否下降」的回归，
  不用于选 PoL 阈值。

## 8. 复现命令

```powershell
# 审计（联网）与校验（离线）
uv run --no-project --offline python datasets/pol2/replay/audit.py fetch --out datasets/pol2/replay/audit-2026-09-30.json
uv run --no-project --offline python datasets/pol2/replay/audit.py verify --audit datasets/pol2/replay/audit-2026-09-30.json

# 离线跑通改写 + 重判链路（fixture：不是翻译，也不是真值）
uv run --no-project --offline python datasets/pol2/replay/rewrite.py prepare \
    --source datasets/pol2/replay/fixtures/rewrite/en-source.jsonl \
    --candidates datasets/pol2/replay/fixtures/rewrite/candidates.json --out <临时目录>
uv run --no-project --offline python datasets/pol2/replay/rewrite.py run --out <临时目录> --fixture
uv run --no-project --offline python datasets/pol2/replay/rewrite.py verify --records <临时目录>/zh.records.jsonl

# 真实改写 + 重判（需要 Lead 批准，会调用付费 API；缺参数直接退出码 2）
# uv run --no-project --offline python datasets/pol2/replay/rewrite.py run --out <池目录> \
#     --endpoint <base-url> --rewrite-model <A> --judge-model <B> \
#     --rewrite-lineage <血缘A> --judge-lineage <血缘B> --approved-by-lead

# 本目录测试
uv run --no-project --offline python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q
```
