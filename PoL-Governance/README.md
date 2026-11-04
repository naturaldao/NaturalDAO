# PoL 治理层协作

用 PoL 改善 AI 运行时治理：少伤害、少误拦，保留帮助能力，成本可接受。

## 从这里开始

阅读 [SPEC](SPEC.md) 了解研究目标，按 [AGENTS.md](AGENTS.md) 的流程从 [任务表](TASKS.md) 选择工作，并用任务页记录进度。
[路线图](ROADMAP.md) 记录阶段安排，[结果索引](results/README.md) 汇总模型评估与归档结果。

专用 PoL2 训练遵循 [训练审批清单](datasets/pol2/APPROVAL-CHECKLIST.md)。通用数据微调基线与 Kev 对照结果分别从结果索引进入，按各自的数据版本和实验口径解读。

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
| 开发宿主适配器并验证接入 | [插件与试运行](integrations/README.md) |
| 深入调研模型 | [Research Agent Prompt](research/model-research-example.md) |
| 查 Jev 类模型的研究证据 | [文献综述](research/PoL2-Jev-Typed-Literature-Survey/README.md)（对照 PoL2 条款） |
| 看 PoL2 条款如何落到 DAO 投票与审议 | [治理机制实验室](research/PoL2-DAO-Governance-Lab/README.md)（含模拟与公开试例评测） |

在本目录运行：

```powershell
uv run --no-project --offline python tools/check.py
```

数据边界（必须遵守）：训练只用 train；validation 只用于选模型与校准；公开测试只做回归；私有保留集不进任何分支、日志或训练环境，由独立评测者库外保管。详见 [datasets/README.md](datasets/README.md)。

本目录可完整复制到其他仓库独立使用，无需安装模型。原创代码与文档的当前许可声明遵循随附 [Proof of Love2](LICENSE)；此前版本已授予的 CC0 或其他许可不因本次更新而撤销。外部数据、模型及引用保留各自许可。
