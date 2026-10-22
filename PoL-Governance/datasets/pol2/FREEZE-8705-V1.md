# POL2-accepted-8705-v1 专用数据卡（POL2 freeze / DATA-02）

> 一句话：协作者标注项目 `pol2-label-team-v1` 的冻结集 **8,705 units / 75 families / 4,888 cases**，
> 本目录把它物化为四区切分与 HF 导出结构。状态 **`FROZEN_READ_ONLY_NOT_TRAINING_APPROVED`**：
> **未批准训练、非专家金标**，训练/上传前须由数据所有者书面确认。

## 1. 来源与可复算锚点

| 项 | 值 |
|---|---|
| 数据包 | `datasets/pol2/pack-1022.tar.gz`（本机，gitignore，不入库） |
| pack 大小 / sha256 | 119,500,628 bytes / `9b9ae1cbc3ed1788a0f4e5ccd998fe4dc713ccd121af88077f68c8f56241001e` |
| freeze 文件 | `accepted-units.jsonl`（41,048,954 bytes，8,705 行） |
| freeze sha256 | `773a3d236b48edb576bb2cf9a4cc9798b77447a808dfe7e151e9db246ab51ec1`（与 pack manifest 的 frozen_files 一致） |
| freeze manifest | `manifest.json`（17,534 bytes，sha256 `a4391ab02044b6caf295aa4d8e77d6c1003011b2037f3e0715e259e718e5d2f8`） |
| 生成时间 | 2026-10-20T02:29:08Z（freeze manifest `created_at`） |
| 汇总范围 | 26 个 source_run（FULL200-0001 … FULL200-0026） |
| 标注团队 | 5 角色：`standard-guardian` / `annotator-a` / `annotator-b` / `auditor` / `coordinator` |
| 标注模型 | `deepseek-flash`（standard-guardian、annotator-a、auditor）+ `deepseek-v4-pro`（annotator-b、coordinator） |
| 判定手册 | `handbook.md` v0.8（sha256 `d32d56222adcc11c6421dce3ccddfd703a77c7c7edef96459b1125ad61c35a5b`） |
| 问项政策 | `question-policy.json` POL2-question-policy-v0.8.1（18 条模板，sha256 `2d9f0ef40288bc4ce45b0a9e553dd82c48ec61cc481159e47f0481774e6609cc`） |
| 状态标志 | `training_approved=false`、`expert_gold=false`；gates：`training_enabled=false`、`test_only=true` |

数据实体（解压包、freeze 副本、切分、HF 导出）全部在 gitignore 的 `datasets/pol2/data/`；
仓库只提交本卡、[SPLIT-MANIFEST.json](freeze-8705-v1/SPLIT-MANIFEST.json)、
[prepare_freeze.py](prepare_freeze.py) 与 [test_prepare_freeze.py](test_prepare_freeze.py)。

## 2. 四区计数（以冻结提案为准，未重新切分）

冻结 manifest 的 `split_proposal_counts` 就是四区来源；本目录用
`split_proposal` 字段原样物化，**没有重新切分、没有引入新盐、没有改标签**。
行序统一为 `unit_id` 升序（当前 id 全为 ASCII，等价字节序）；每行都是冻结文件对应行的逐字节副本。

| 冻结区 | 项目区（provisional） | units | families | cases | choice | score | audit pass | 切分文件 sha256 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| train | train | 5,900 | 52 | 3,383 | 5,361 | 539 | 1,175 | `f4a4b827e858f8ad04685b950ab47761689e52fac481c9bd62a1b5a34dc07f23` |
| validation | public_test | 1,110 | 9 | 584 | 1,086 | 24 | 206 | `e48c046ab7c616f20aa807eb238fafc7f266418ba149ee93a32b7534d622cf45` |
| calibration | validation | 1,008 | 9 | 548 | 884 | 124 | 190 | `b1615723247639e7c977d9a1a7878e49e0c8f47c17c81dc91e28aa83d7310a05` |
| blind_test | private_holdout | 687 | 5 | 373 | 579 | 108 | 132 | `6c562c48b71410121f096aa9f8348d6903618b1ffdb121339c299c5cc2905eb2` |
| **合计** | — | **8,705** | **75** | **4,888** | **7,910** | **795** | **1,703** | — |

族级一致性：75 个 `family_id` 各自只属于一个冻结区（0 冲突）；4,888 个 `case_id`
也不跨区。每族都至少有一条 unit，没有空区。

### 2.1 为什么是这个映射（provisional，待 owner 签字）

- **尊重协作者冻结设计**：pack manifest 明确写了 `proposed_split_rule = "sha256(family_id) 70/10/10/10; proposal only, no split files"`；
  重新切分会让本仓库的区与协作者交付物不可对齐，也浪费其已内嵌的族级 hash 设计。
- **75 个族做精确 70/20/5/5 太粗**：每族平均约 116 units，5% 档只有 3-4 个族，抖动过大。
- **校准需要足够样本**：把冻结的 `calibration`（1,008 units / 9 族）落到项目 `validation`，
  比在 75 族上重新分 5% 更稳。
- **私有保留必须物理隔离**：冻结的 `blind_test` 落到项目 `private_holdout`，内容不进入公开路径。
- 状态：`PROVISIONAL_FAMILY_LEVEL_PROPOSAL_MATERIALIZED`。owner 签字后可改状态，但**不应**在未重跑全部派生件的情况下改区。

> 这与 [README](README.md) §5 的 `splits.py` 体系**不冲突**：`splits.py` 管通用族清单的仓外私盐切分；
> 本冻结集自带族级提案，不使用 `splits.py`、不重切。两套体系互不引用。

## 3. Schema（17 键 unit）

一行一个 unit（JSONL / UTF-8 / 无 BOM）。键集合固定，未使用 `extra` 扩展。

| 键 | 类型 | 说明 |
|---|---|---|
| `unit_id` | string | `<case_id>:<world>`，8,705 个唯一 |
| `case_id` | string | 场景 id；同一 case 可有 world `a` / `b` 两个反事实世界 |
| `world` | string | `a` / `b`；全套 a=4,268、b=4,437 |
| `family_id` | string | 场景族（`POL2F_O_…` 等），75 个 |
| `mapping_id` | string | 主题名，64 种（如 `repair:补救可选择`） |
| `source_run` / `source_batch` | string | 26 个 run；两者当前相同 |
| `status` | string | 恒为 `ACCEPTED` |
| `split_proposal` | string | 冻结提案区：`train` / `validation` / `calibration` / `blind_test` |
| `label` | string 或 int | 异质：choice 为选项键字符串，score 为 0-4 整数 |
| `answer_a` / `answer_b` | object | 两次独立作答：`unit_id` / `status` / `label` / `evidence` / `theory_refs` / `reason`；部分带 `checks` / `check_evidence` 及归一化记录字段 |
| `audit_status` | string | `pass`（1,703）或 `not_sampled`（7,002） |
| `state` | object | `fixed_facts`（非空，含 content/event_kind/occurred_at/received_at）、`judgment_actor`、`observer_cutoff`、`action_stage`、`world{variable_facts, candidate_action}` |
| `question` | object | `instructions`（题面）、`type`（`choice` / `score`）、`criteria`（见下） |
| `question_sha` | string | `sha256(canonical_json(question))`，18 个模板；verify 逐条复算 |
| `source_sha` | string | 每 case 唯一（4,888 个），同一 case 的 a/b 共享 |

### 3.1 输出空间（adapter 必读）

| question.type | units | 输出空间 |
|---|---:|---|
| choice | 7,910 | 3 种选项键集：`{yes,no,unknown,not_applicable}`（6,693）、`{necessary,unnecessary,unknown,not_applicable}`（598）、`{hate2,love2,mixed,neither,unknown}`（619） |
| score | 795 | 整数 0-4（`question.criteria` 是 5 条档位定义，下标即等级） |

- **没有独立的选项列表**：choice 的选项就是 `question.criteria` 的**键**，其值是判定条件长文本；
  不存在短 option label。adapter 应按 `mapping_id` 选输出头（同一 mapping 只对应一个 question 模板，verify 已校验）。
- 标签词表全局 15 种取值（choice 10 种 + score 0-4）：yes 3,343 / no 2,809 / necessary 387 / unknown 454 /
  not_applicable 87 / neither 74 / hate2 233 / love2 234 / mixed 78 / unnecessary 211；score 3:387 / 0:129 / 1:107 / 2:154 / 4:18。
- 建议上下文拼装：`state.judgment_actor` + `state.fixed_facts[*].content` + `state.world.variable_facts[*].content`
  + `state.world.candidate_action`，再附 `state.observer_cutoff` / `state.action_stage` 与 `question.instructions`；
  `answer_*` 的 `evidence[*].path` 形如 `/state/fixed_facts/0/content`，可反查。

### 3.2 answer 字段的异质性（不要当稳定机器 schema）

`checks` / `check_evidence` 的值类型不统一：字符串 `supported/refuted/unknown`、对象
`{"value":…,"status":…,"evidence":…}`、数组、布尔都出现过。另有归一化记录：
`original_label`+`label_adapter`（answer_a 580 / answer_b 434 条，均为 score 数字的字符串→整数表示）、
`check_evidence_adapter`（1）、`rubric_assessment`（2）、`unresolved_kind`（a18 / b10，值均为 null）、
`turns`（9）、`missing_conditions`（a7 / b1）。训练侧若需要 `checks`，先做类型正规化。

### 3.3 a/b 反事实对

4,888 个 case：**3,817 个有 a/b 两条**（world 事实变量不同、label 一致），**1,071 个单条**。
`answer_a` 与 `answer_b` 的 label 与 unit label **全部一致**（8,705/8,705，verify 断言）；
但 evidence / reason / checks 不同（两个答案独立作答），不能当成同一答案的两个副本。

## 4. 切分与 HF 导出布局

### 4.1 仓库内落位（gitignored）

```
datasets/pol2/data/
  pack-1022/                      # 从 tar 选择性解压的 14 个成员 + EXTRACT-MANIFEST.json
  freeze-8705-v1/
    accepted-units.jsonl          # 8,705 行冻结副本
    manifest.json
    splits/{train,validation,calibration,blind_test}.units.jsonl
  hf-export/pol2-freeze-8705-v1/
    public/  {train,public_test,validation}.units.jsonl + README.md + MANIFEST.json
    private/ private_holdout.units.jsonl + README.md + MANIFEST.json
```

public 与 private **物理分开**：public 目录只有公开三区；`blind_test` 只在 private 目录。
两个目录各自带 README（HF 数据卡）与 MANIFEST（sha256/bytes/lines/计数/映射）。

| 导出文件 | 冻结区 | 项目区 | lines | bytes | sha256 |
|---|---|---|---:|---:|---|
| public/train.units.jsonl | train | train | 5,900 | 27,989,777 | `f4a4b827…dc07f23` |
| public/public_test.units.jsonl | validation | public_test | 1,110 | 4,828,677 | `e48c046a…622cf45` |
| public/validation.units.jsonl | calibration | validation | 1,008 | 5,004,403 | `b1615723…d7310a05` |
| private/private_holdout.units.jsonl | blind_test | private_holdout | 687 | 3,226,097 | `6c562c48…c2905eb2` |

公开合计 **8,018 units / 70 families / 4,515 cases**（choice 7,331 · score 687）；私有 **687 units / 5 families / 373 cases**。
公开导出覆盖全部 18 个 question 模板与 60/64 个 `mapping_id`（其余 4 个 mapping 只出现在私有保留集）。
完整 sha256 与导出 README/MANIFEST 哈希见 [SPLIT-MANIFEST.json](freeze-8705-v1/SPLIT-MANIFEST.json)。

### 4.2 上传状态与建议

- 状态：**NOT_UPLOADED**。本任务不调用网络、不含 HF token；导出目录已就绪，等 owner 授权。
- 建议公开仓库名 `<HF_ORG>/pol2-freeze-8705-v1`，私有保留 `<HF_ORG>/pol2-freeze-8705-v1-holdout`（org 由上传者配置）。
- 上传前必须同时满足：① owner 书面确认训练用途；② 许可确认（源包未声明许可）；③ 私有仓库访问控制就位。
- 上传后用仓库脚本重算 sha256 对照本卡的清单；并把 HF revision 固定到 commit sha。

## 5. 复现命令

前置：`datasets/pol2/pack-1022.tar.gz` 在本机（gitignore，不入库）。

```
# 物化：解压 → 四区切分 → HF public/private → tracked SPLIT-MANIFEST.json（幂等、确定性）
uv run --no-project --offline python datasets/pol2/prepare_freeze.py build

# 只读复核：pack/freeze sha256、unit 数、schema、族级切分、answer 一致、mapping 标签词表、
# id 唯一、question type 统计，并逐字节复算全部分片/导出/manifest
uv run --no-project --offline python datasets/pol2/prepare_freeze.py verify
uv run --no-project --offline python datasets/pol2/prepare_freeze.py verify --json

# 不变量测试（合成 6-unit fixture，不依赖 41 MB 真数据）
uv run --no-project --offline python -m unittest datasets.pol2.test_prepare_freeze -v
```

`verify` 的期望结果（本机实测，2026-10-22）：
`status=pass`，`integrity_basis=pack`，17 项检查通过（0 fail / 0 skip），
`tracked manifest reproducible=true`。关键计数：units 8,705 / families 75 / cases 4,888；
partition 5,900 · 1,110 · 1,008 · 687；audit pass 1,703；label agreement 8,705/8,705；
question templates 18；mappings 64；a/b pairs 3,817。两次 build 逐字节一致（测试覆盖）。

## 6. 诚实限制（引用时不要弱化）

1. **未批准训练**：`FROZEN_READ_ONLY_NOT_TRAINING_APPROVED`、`training_approved=false`。
   training_approved=true（owner 书面签字）前不得用于梯度、蒸馏、教师生成或选阈值。
2. **非专家金标**：`expert_gold=false`。标注是 Agent 团队（deepseek-flash + deepseek-v4-pro）产出，
   人工审计只做抽检，没有独立人工复核。
3. **审计覆盖仅 19.6%**：pass 1,703 / 8,705；`not_sampled` 不等于无问题。
4. **标签异质**：15 种 label 取值、3 种 choice 选项键集 + score 0-4；且 choice 没有短 option label。
   adapter 必须按 `mapping_id` 建输出头，不能压成一个分类空间。
5. **answer 字段不是稳定机器 schema**：`checks` / `check_evidence` 类型混杂；
   580/434 条带 `original_label` 归一化痕迹。
6. **只有中文**：没有翻译或英文对照；跨语言迁移要另做。
7. **原文没有 public_test 区**：`validation→public_test`、`calibration→validation` 是项目侧 provisional 安排。
8. **a/b 对不独立**：3,817 个 case 的反事实对共享事实模板；按 unit 计样本量会高估独立性。
9. **切分是提案**：族级 sha256(70/10/10/10) 由协作者给出，仅审阅前有效；未做语义近重复/跨族重叠检测。
10. **question 模板有修订史**：question-policy v0.8.1 的 18 条以 `sha256(source_question)` 为键，
    其中 7 条已修订；unit 使用修订后的 question 文本（3,258 units），policy 顶层键仍是旧版 hash。
11. **许可未声明**：仓库 LICENSE 只有 `Proof of Love2` 一行，pack 也没有许可文件；
    公开再分发前必须由数据所有者确认许可。
12. **审计布尔 gates 只是流程状态**：`engineering_pass=true` / `handbook_frozen=true` 是标注流程闸门，
    不构成数据质量或训练授权。

## 7. 训练门禁与使用纪律

- 训练只用 `train`；`validation`（冻结 calibration）用于选模型/校准；
  `public_test`（冻结 validation）只做回归，若据此改方案须在结果卡披露，不再称盲测。
- `private_holdout`（冻结 blind_test）只在模型定版后的受控评测使用：隔离、禁网、只导出汇总；
  内容/unit_id/family_id 不得进入公开仓库、fork、PR、日志、截图或训练 Agent 上下文。
- 任何使用都要先过 `training_approved` 闸门；本卡不构成授权。

## 8. 保密边界（tracked vs 数据实体）

- tracked 文件（本卡、[SPLIT-MANIFEST.json](freeze-8705-v1/SPLIT-MANIFEST.json)、脚本、测试、README）
  **只出现计数与 sha256**；blind_test 的 unit_id / family_id / 内容一律不出现（随机抽真实 id 在 tracked 文件
  grep 0 命中；脚本写盘前还有硬断言）。
- 数据实体全部在 gitignore 的 `datasets/pol2/data/` 与显式忽略的 pack tar 内。
- 本卡刻意不写具体 blind unit_id / family_id；如需核验，用数据实体 + verify 脚本，而不是把 id 写进文档。

## 9. 文件索引

| 路径 | 角色 |
|---|---|
| [README.md](README.md) | 本目录数据契约（§5 分区、§6 目录已指向本卡） |
| [prepare_freeze.py](prepare_freeze.py) | tracked 脚本：`verify` / `build`（仅标准库） |
| [test_prepare_freeze.py](test_prepare_freeze.py) | tracked 测试：合成 fixture 覆盖关键不变式 |
| [SPLIT-MANIFEST.json](freeze-8705-v1/SPLIT-MANIFEST.json) | tracked 清单：区计数、全部分片/导出 sha256、schema 摘要、限制 |
| `datasets/pol2/data/…` | gitignored 数据实体（pack 解压、freeze、切分、HF 导出） |
| 上游 packs | `datasets/pol2/pack-1022.tar.gz`（gitignore；owner 保管） |

维护：DATA-02 数据集 Agent（T2）。pack 更新时**必须全量重建所有派生件**（切分、导出、README/MANIFEST、
SPLIT-MANIFEST），否则旧派生件会与新 pack 不一致；verify 会以 pack sha256 拒绝对不上的重建。
