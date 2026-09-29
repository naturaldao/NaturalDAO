# [LIT-01] Jev 类型化决策模型文献综述（对照 PoL2 治理条款）

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| 鄢申涛 Shenton / Claude | 待集成；综述 0.1.1 已完成，迁入 research/ 并通过两项检查 |

- 更新时间：2026-09-30 00:40 UTC+8
- 分支：pol/LIT-01/shenton
- 起点 commit / 依赖分支与 commit：main 813d89e；内容来自原 PR #17（lit/pol2-jev-typed-literature-survey，210ec5e）
- 目标与交付路径：`research/PoL2-Jev-Typed-Literature-Survey/`
- 本次改动范围：新增上述目录与本任务页；TASKS.md 增加 LIT-01 一行；README.md 增加文献综述入口；README.md 与 models/CATALOG.md 中已失效的 `prompts/model-research.md` 链接改指 `research/model-research-example.md`
- 下一步：团队审阅第 4 节 ★ 建议；把 G3/G4 的负面结果转为 MODEL-01 的淘汰检查项、EVAL-01 的评估条目
- 阻塞 / 需要谁帮助：无
- 环境 / 输出路径 / 资源预算：Python 3.10+ 标准库；PowerShell 5.1 抓取脚本；无 GPU、无付费 API
- 数据版本与可用分区：不使用 PoL 数据；文献检索截止 2026-09-29

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-09-29｜Shenton / Claude｜完成 37 篇论文（36 arXiv + 1 alphaXiv）与 11 条灰色文献的检索、归类与综述；独立 Agent 核对数字与 PoL2 引文后修正 20 处｜原 PR #17｜迁入协作目录
2026-09-30｜Shenton / Claude｜按 PoL-Governance 约定迁入 research/，登记 LIT-01｜本分支｜开 PR 纳入公共基线

## 交付或交接

- 结果入口：[research/PoL2-Jev-Typed-Literature-Survey/README.md](../research/PoL2-Jev-Typed-Literature-Survey/README.md)；综述正文 [docs/survey.zh.md](../research/PoL2-Jev-Typed-Literature-Survey/docs/survey.zh.md)
- 复现：在该目录运行 `python scripts/build_catalog.py`、`python scripts/check.py`；抓取元数据与 PDF 用 `scripts/fetch_papers.ps1`
- 检查：`python tools/check.py`（本目录）与上述 `scripts/check.py` 均通过
- 未测项：综述对论文的概括主要依据摘要，未逐篇精读全文；条款对应为整理者解读
