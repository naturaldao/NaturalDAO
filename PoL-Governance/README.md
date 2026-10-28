# PoL 治理层协作

用 PoL 改善 AI 运行时治理：少伤害、少误拦，保留帮助能力，成本可接受。

## 当前进度（2026-10-28 方向修正）

> **方向修正（owner 2026-10-28）**：此前 Track A 是**通用数据（general v5）的普通 FT**，用于打通工程管线；它**不是**目标所需的**专有治理数据（POL2）微调**。该线与最终评测已归档（[results/archive/2026-10-27-general-ft](results/archive/2026-10-27-general-ft/README.md)），数字只作“通用 FT 基线”记录，**不能回答专有微调后在治理+通用上的表现**。
> 项目目标不变：**用专有治理数据微调后，在专有治理评测与通用智力评测上都取得良好成绩**；POL2 训练仍需 owner 授权（`training_approved=false`）。

- **第一阶段 · 数据（完成，2026-10-27）**：通用决策数据集 **v5** 已由 PR #43 并入 main（公开三区 71,519 条 / 78,001 问题，私有保留集 6,541 条库外）；协作者交付的**专用 PoL2 冻结数据** POL2-accepted-8705-v1（8,705 单元 / 75 场景族）已完成校验、四区切分与数据卡，**尚未批准训练**。阶段一改动在 `pol/DATA-02/wenbo` 分支（PR #44 已关闭，集成方式待维护者确认）。
- **HF 托管（完成，2026-10-27）**：公开三区与私有保留集已上传到 Hugging Face（公开 revision `52bfdca…`、私有 `146ae46…`），远程校验与下载回验通过；仓库只保留数据卡、清单与校验脚本，流程见 [datasets/general/HF.md](datasets/general/HF.md)。
- **第二阶段 · 通用 FT 基线（历史，已归档）**：Qwen3-1.7B + LoRA 在 general v5 上训练（validation 0.5127→0.7883；test 0.5047→0.7785）。**这是通用 FT 基线，不是专有微调**；结果卡与代码保留在归档目录供工程参考。
- **第三阶段 · 通用 FT 最终评测（历史，已归档）**：按 owner 授权以方式 2 在隔离环境完成私有保留集评测（base 0.3996→adapter 0.7034，+30.37pt；校准 T≈0.992；lm-eval 均值 -0.7pt 且 agieval 触发警戒；batch=1 p50 45–65ms）。归档：[results/archive/2026-10-27-general-ft/final-eval](results/archive/2026-10-27-general-ft/final-eval/CARD.md)、阶段报告 [已归档](docs/reports/archive/2026-10-27-final-eval.md)。
- **当前主线（2026-10-28）**：① **专有微调待启动**——等 PoL2 训练授权后，用 POL2 专有数据微调，并同时评专有治理与通用智力；② 评测 session 正在做 **Kev 原版 vs Kev 微调版** 的对照与 Jev 类基准调研（外部参考线，不混表）。
- **协作线合并（2026-10-26）**：main 前进 45 个提交，新增 **EVAL-02 具身推理先导**（16 案例三条件筛查、Kev+VirtualHome 符号闭环、MuJoCo 单任务 n=1）、**EVAL-03 完整理论内在化先导**（严格质量门 0/6，按规则停止训练）、**POL2 score-v2 数据**（外部 Release）与 **Kev-4B pointer-head 模型**（3 seed 研究预发布，作者明确不能宣称平均提升）。我们的分支已合并 main；摘要见 [阶段报告](docs/reports/2026-10-26-collaborator-update.md)。两条模型线口径不同，**不能混表比较**。

**Agent 从这里开始：**读 [SPEC](SPEC.md) → 在 [任务表](TASKS.md) 选任务 → 推送任务分支认领 → 在任务页更新进度。日常协作不需要 PR 或 fork，具体见 [AGENTS.md](AGENTS.md)。

| 你要做什么 | 去哪里 |
|---|---|
| 领任务、看谁在做 | [TASKS](TASKS.md)；以远端 pol/* 分支中的任务页为实时状态 |
| 通用决策数据集 v5 | [datasets/general](datasets/general/README.md) · [HF 托管](datasets/general/HF.md) |
| 专用 PoL2 决策数据 | [datasets/pol2](datasets/pol2/README.md) · [冻结版数据卡](datasets/pol2/FREEZE-8705-V1.md) |
| 找模型、贡献调研或适配 | [models](models/README.md) · [模型清单](models/CATALOG.md) |
| 运行公共评估 | [benchmark](benchmark/README.md) |
| 看具身推理先导（EVAL-02，协作） | [benchmark/embodied_reasoning](benchmark/embodied_reasoning/README.md) |
| 看完整理论内在化先导（EVAL-03，协作） | [benchmark/pol2](benchmark/pol2/README.md) |
| POL2 score-v2 数据（外部 Release，协作） | [datasets/pol2/score-v2](datasets/pol2/score-v2/README.md) |
| 提交训练与评估结果 | [results](results/README.md) |
| 深入调研模型 | [Research Agent Prompt](research/model-research-example.md) |
| 查 Jev 类模型的研究证据 | [文献综述](research/PoL2-Jev-Typed-Literature-Survey/README.md)（37 篇论文，对照 PoL2 条款） |
| 看 PoL2 条款如何落到 DAO 投票与审议 | [治理机制实验室](research/PoL2-DAO-Governance-Lab/README.md)（14 个实验，含公开试例评测） |

**已有**：20 条公开合成试例、盲输入导出、双人标注/分歧工具、诊断评估器、Kev 本地适配器、通用决策数据集 v5、PoL2 生成与真值流水线、909 项自动化测试。
**进行中**：第二阶段 GPU 实验（owner 暂停中；2026-10-23 系统崩溃后硬件待确认）、PR 集成方式确认（#44/#45 已关闭）。
**待完成**：lm-eval adapter 侧对照、校准报告、Track B 全量训练、多 seed；插件接入。现有建议标签不是金标准。

在本目录运行：

```powershell
uv run --no-project --offline python tools/check.py
```

数据边界（必须遵守）：训练只用 train；validation 只用于选模型与校准；公开测试只做回归；私有保留集不进任何分支、日志或训练环境，由独立评测者库外保管。详见 [datasets/README.md](datasets/README.md)。

本目录可完整复制到其他仓库独立使用，无需安装模型。原创代码与文档的当前许可声明遵循随附 [Proof of Love2](LICENSE)；此前版本已授予的 CC0 或其他许可不因本次更新而撤销。外部数据、模型及引用保留各自许可。

主分支尚未包含本目录时，可从提供本目录的初始化分支开任务分支，或将整个目录复制到自己的仓库；不必等待初始化 PR 合并。