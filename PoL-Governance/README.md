# PoL 治理层协作

用 PoL 改善 AI 运行时治理：少伤害、少误拦，保留帮助能力，成本可接受。

**Agent 从这里开始：**读 [SPEC](SPEC.md) → 在 [任务表](TASKS.md) 选任务 → 推送任务分支认领 → 在任务页更新进度。日常协作不需要 PR 或 fork，具体见 [AGENTS.md](AGENTS.md)。

| 你要做什么 | 去哪里 |
|---|---|
| 领任务、看谁在做 | [TASKS](TASKS.md)；以远端 `pol/*` 分支中的任务页为实时状态 |
| 生成、标注、共享数据 | [datasets](datasets/README.md) |
| 找模型、贡献调研或适配 | [models](models/README.md) · [模型清单](models/CATALOG.md) |
| 运行公共评估 | [benchmark](benchmark/README.md) |
| 提交训练与评估结果 | [results](results/README.md) |
| 深入调研模型 | [Research Agent Prompt](prompts/model-research.md) |

**已有**：20 条公开合成试例、盲输入导出、双人标注/分歧工具、诊断评估器、Kev 本地适配器、41 项自动化测试（benchmark 34 + board 7）。
**待完成**：独立标注、正式数据、真实训练与模型评测、插件。现有建议标签不是金标准。

在本目录运行：

```powershell
uv run --no-project --offline python tools/check.py
```

本目录可完整复制到其他仓库独立使用，无需安装模型。原创代码与文档采用随附 [CC0](LICENSE)；外部数据、模型及引用保留各自许可，不随本目录变更。

主分支尚未包含本目录时，可从提供本目录的初始化分支开任务分支，或将整个目录复制到自己的仓库；不必等待初始化 PR 合并。
