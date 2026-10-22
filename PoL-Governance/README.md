# PoL 治理层协作

用 PoL 改善 AI 运行时治理：少伤害、少误拦，保留帮助能力，成本可接受。

## 当前进度（2026-10-23）

- **第一阶段 · 数据（收尾完成，PR #44 待合并）**：通用决策数据集 **v5** 已由 PR #43 并入 main（公开三区 71,519 条 / 78,001 问题，私有保留集 6,541 条库外）；协作者交付的**专用 PoL2 冻结数据** POL2-accepted-8705-v1（8,705 单元 / 75 场景族）已完成校验、四区切分与数据卡，**尚未批准训练**。
- **大文件离仓**：数据集实体改由 Hugging Face 托管，仓库只保留数据卡、清单（MANIFEST）与校验脚本；托管状态见 [datasets/general/HF.md](datasets/general/HF.md)。
- **第二阶段 · 模型适配（进行中）**：训练视图完成；**Track A 基线**（Qwen3-1.7B + LoRA 字母 SFT，1 epoch）在 validation 上把封闭选择准确率从 **0.5127（0-shot）提到 0.7883**，test adapter 准确率 **0.7785**；Track B（候选评分头）代码就绪。阶段报告见 [docs/reports](docs/reports/2026-10-23-phase2-track-a.md)，计划见 [ROADMAP](ROADMAP.md)。

**Agent 从这里开始：**读 [SPEC](SPEC.md) → 在 [任务表](TASKS.md) 选任务 → 推送任务分支认领 → 在任务页更新进度。日常协作不需要 PR 或 fork，具体见 [AGENTS.md](AGENTS.md)。

| 你要做什么 | 去哪里 |
|---|---|
| 领任务、看谁在做 | [TASKS](TASKS.md)；以远端 pol/* 分支中的任务页为实时状态 |
| 通用决策数据集 v5 | [datasets/general](datasets/general/README.md) · [HF 托管](datasets/general/HF.md) |
| 专用 PoL2 决策数据 | [datasets/pol2](datasets/pol2/README.md) · [冻结版数据卡](datasets/pol2/FREEZE-8705-V1.md) |
| 找模型、贡献调研或适配 | [models](models/README.md) · [模型清单](models/CATALOG.md) |
| 运行公共评估 | [benchmark](benchmark/README.md) |
| 提交训练与评估结果 | [results](results/README.md) |
| 深入调研模型 | [Research Agent Prompt](research/model-research-example.md) |
| 查 Jev 类模型的研究证据 | [文献综述](research/PoL2-Jev-Typed-Literature-Survey/README.md)（37 篇论文，对照 PoL2 条款） |
| 看 PoL2 条款如何落到 DAO 投票与审议 | [治理机制实验室](research/PoL2-DAO-Governance-Lab/README.md)（14 个实验，含公开试例评测） |

**已有**：20 条公开合成试例、盲输入导出、双人标注/分歧工具、诊断评估器、Kev 本地适配器、通用决策数据集 v5、PoL2 生成与真值流水线、909 项自动化测试。
**进行中**：专用数据切分与数据卡、数据集 Hugging Face 托管、决策模型选型与首个微调基线。
**待完成**：真实训练与统一口径评测、插件接入。现有建议标签不是金标准。

在本目录运行：

```powershell
uv run --no-project --offline python tools/check.py
```

数据边界（必须遵守）：训练只用 train；validation 只用于选模型与校准；公开测试只做回归；私有保留集不进任何分支、日志或训练环境，由独立评测者库外保管。详见 [datasets/README.md](datasets/README.md)。

本目录可完整复制到其他仓库独立使用，无需安装模型。原创代码与文档的当前许可声明遵循随附 [Proof of Love2](LICENSE)；此前版本已授予的 CC0 或其他许可不因本次更新而撤销。外部数据、模型及引用保留各自许可。

主分支尚未包含本目录时，可从提供本目录的初始化分支开任务分支，或将整个目录复制到自己的仓库；不必等待初始化 PR 合并。
