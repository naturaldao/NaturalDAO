# [GOV-01] PoL2 × DAO 治理机制实验室（模拟、反事实与基线筛查评测）

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| 鄢申涛 Shenton / Claude | 待集成；实验室 0.3.0 迁入 research/，本目录 tools/check.py 与实验室 54 项测试均通过 |

- 更新时间：2026-09-30 18:00 UTC+8
- 分支：pol/GOV-01/shenton
- 起点 commit / 依赖分支与 commit：main bf2636c；内容来自 https://github.com/shentonyan/pol2-dao-governance （commit f6c017b）
- 目标与交付路径：`research/PoL2-DAO-Governance-Lab/`
- 本次改动范围：新增上述目录与本任务页；TASKS.md 增加 GOV-01 一行；README.md 增加实验室入口。未改动 benchmark、datasets、models 与任何现有文件的内容
- 下一步：团队审阅 PoL2 条款的工程解读（`docs/concept-mapping.md`，标 ❓ 处）；E9 的试例评测结果可作为 EVAL-01 的对照基线
- 阻塞 / 需要谁帮助：无
- 环境 / 输出路径 / 资源预算：Python 3.10+；核心仅标准库，作图需 matplotlib；无 GPU、无付费 API；全部实验约 3 分钟
- 数据版本与可用分区：使用 benchmark/pilot.jsonl 的 20 条公开试例（副本，取自 commit 30f1ad6，内容与当前 main 相同）仅作接口与失败模式演示，不用于训练或选阈值；另用 Sharma et al. (2026) 公布的汇总数字

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-09-29｜Shenton / Claude｜把 PoL2 条款（平等联结、扬爱抑恨、非爱非恨、质询权与解释义务、可验证决策链路）落到 Sharma et al. (2026) 的 DAO 投票实验上，完成可运行实验室与 14 个实验｜shentonyan/pol2-dao-governance｜迁入协作目录
2026-09-30｜Shenton / Claude｜统一制图规范；PoLEn 章节号跟随当日调整（EAP 改为第 4 章）；按 PoL-Governance 约定迁入 research/，登记 GOV-01｜本分支｜开 PR 纳入公共基线

## 交付或交接

- 结果入口：[research/PoL2-DAO-Governance-Lab/README.md](../research/PoL2-DAO-Governance-Lab/README.md)；实验图集 [docs/results.md](../research/PoL2-DAO-Governance-Lab/docs/results.md)；条款对照 [docs/concept-mapping.md](../research/PoL2-DAO-Governance-Lab/docs/concept-mapping.md)
- 复现：在该目录运行 `pip install -e ".[dev]"`、`pytest`、`pol2dao experiments --reps 1000`
- 检查：`python tools/check.py`（本目录）通过；实验室 `pytest` 54 项通过
- 与 PoL-Governance 其他任务的关系：E9 用关键词基线跑了 20 条公开试例（盲测版召回 0 %，看过试例后的 v1 为 22 %，不是盲测），说明 PoL 违规远宽于恨语，可作 EVAL-01 的最低对照；E4、E5 用合成判定器量化了「阈值与对异见的偏见」对少数派的影响，可作 MODEL-01 选型时的检查项
- 未测项：E0–E8 是模型模拟，不是关于真实人群的证据；关键词判定器是占位基线；未接入任何真实模型；OSF 原始选票未随附，逐票重放需自行下载
