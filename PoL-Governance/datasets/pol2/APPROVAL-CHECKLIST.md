# PoL2 冻结集训练授权前置清单（APPROVAL CHECKLIST）

> 用途：把「owner 书面授权 → 解禁训练 → 训练前验收 → 训练后报告」固化成一份可勾选的操作清单。
> 背景与诚实限制见 [数据卡 §6/§7](FREEZE-8705-V1.md)；冻结状态：FROZEN_READ_ONLY_NOT_TRAINING_APPROVED。
> 本清单不是授权本身；没有 owner 的书面批准，任何一步解禁都不得执行。

## 0. 当前门禁状态（每项为 false 时禁止任何梯度）

| 标志 | 当前位置 | 含义 |
|---|---|---|
| freeze_id | POL2-accepted-8705-v1 | 8,705 units / 75 families / 4,888 cases / 26 runs |
| training_approved | **false** | owner 书面签字前：不得用于梯度、蒸馏、教师生成、阈值选择 |
| expert_gold | **false** | 标注为 Agent 团队产出（deepseek-flash + deepseek-v4-pro），非专家金标 |
| audit coverage | 1,703 / 8,705 = 19.6% | not_sampled ≠ 无问题 |
| license | **未声明** | 源包无许可文件；公开再分发前必须确认 |
| gates | training_enabled=false / test_only=true | 流程闸门，不构成授权 |

## A. owner 必须书面确认的事项（缺一不可）

| # | 确认项 | 记录到 |
|---|---|---|
| A1 | 训练用途与范围：仅 train 区用于梯度？validation（冻结 calibration）用于选型/校准？public_test 只回归？ | 本文件 §F 记录 + 数据卡状态行 |
| A2 | 许可：源包的训练/再分发条款（至少内部训练许可；公开再分发另议） | 本文件 §F + README 许可注记 |
| A3 | 标签权威性：接受 LLM 标注作为行为先验，不声称专家金标；审计覆盖 19.6% | 结果卡限制节 |
| A4 | 冻结不可变性：不重切、不引新盐、按 SPLIT-MANIFEST sha 使用；provisional 映射接受 | 本文件 §F |
| A5 | 盲测边界：private_holdout（冻结 blind_test）只做定版后受控评测；内容不进公开仓库/日志/训练上下文 | 结果卡评测章节 |
| A6 | 报告限制：按数据卡 §6 的限制逐条披露；不得声称专家金标、不得外推跨语言 | 结果卡 |
| A7 | 撤回机制：owner 可随时书面撤回；撤回后停止训练并废弃派生视图 | 本文件 §F |

## B. 解禁步骤（A 全部确认后由维护者执行）

~~~text
1) 在 §F 填写批准记录（批准人 / 日期 / 范围 / 许可引用 / 限制 / 撤回条件）
2) 更新冻结数据实体内 manifest.json 的 training_approved=true（gitignored 数据，记录批准引用）
3) 更新数据卡 FREEZE-8705-V1.md 的状态行（FROZEN_READ_ONLY... -> TRAINING_APPROVED）
4) 重跑 prepare_freeze.py verify，确认除状态标志外一切不变（0 fail）
5) 生成 pv-1 视图（仓库外）：
   python datasets/pol2/build_pol2_training_view.py \
     --freeze datasets/pol2/data/freeze-8705-v1/splits/train.units.jsonl \
     --region train --out <仓库外>/pol2-train-view.jsonl
6) 记录视图 sha256 与行数（本文件 §C）
7) 用 build_mixed_view.py 生成混合视图（9:1 或 8:2，--allow-pol2），记录 manifest
~~~

## C. 训练前验收清单（每项勾选后才可启动 GPU 训练）

- [ ] C1 混合视图 sha256/行数/实际比例已记录（路径与 manifest 在仓库外）
- [ ] C2 训练配置冻结：模型/底座 revision、LoRA 参数、seq len、batch、lr、epoch、seed 写入训练命令与结果卡
- [ ] C3 训练脚本 dry-run 通过（Track A / Track B 对应脚本的 --dry-run）
- [ ] C4 GPU 静默时段与温度检查通过（00:30–09:30 / 12:30–15:30 不启动）
- [ ] C5 多 seed 计划已预注册（20261023 / 20261024 / 20261025）
- [ ] C6 结果卡路径与必填字段已确定（results/<任务ID>-<模型>-<短名>/CARD.md）
- [ ] C7 训练数据只含 train 区 + 通用 train 视图；public_test/validation 不在训练混合中
- [ ] C8 私有/盲测内容未进入任何文件、日志、提示词或 warmup 样本

## D. 训练后报告要求（写进结果卡）

1. 数据版本：冻结 id、pv-1 视图 sha、混合 manifest sha、实际比例；
2. 指标：整体 + 分 kind / lang / 选项数桶 / route；与通用 0-shot、纯通用 LoRA（同配置）对照；
3. 限制：LLM 标注（非专家金标）、审计 19.6%、provisional 映射、仅中文、a/b 对不独立、>26 选项未覆盖；
4. 结论边界：只写「在本数据与配置下的差值」；不写专家金标、不写通用智能提升、不外推跨语言；
5. 失败与未测项如实列出（不填 0、不省略负面结果）。

## E. 撤销与回滚

- owner 撤回授权：立即停止训练；删除仓库外派生视图（pol2 view / mixed view）；保留 manifest 与日志用于审计；
- 本文件 §F 记录「批准已撤回（日期）」；数据卡状态行改回 NOT_TRAINING_APPROVED；
- 已训练权重不得再分发或用于后续评测；结果卡如已公开须补撤回声明。

## F. 批准记录（owner 填写）

| 项 | 内容 |
|---|---|
| 批准人 / 身份 |  |
| 日期（ISO） |  |
| 训练范围 | train 区 + 通用 train 视图；9:1 或 8:2（写明） |
| 许可引用 | 源包许可声明或内部授权文件位置 |
| 限制 | 不公开分发数据 / 不声称专家金标 / 其他 |
| 撤回条件 | 默认：owner 书面撤回即生效 |
| 备注 |  |

> 本文件与冻结数据卡、SPLIT-MANIFEST 一起构成训练授权链；任何不一致以 owner 书面批准为准。
