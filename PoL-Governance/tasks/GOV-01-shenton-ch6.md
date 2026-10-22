# [GOV-01] 第六章按需分配与第七章伦理验证的机制实验（E14、E15）

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| 鄢申涛 Shenton / Claude | 待集成；实验室新增 E14、E15 及测试、条款对照与图集，本目录 tools/check.py 与实验室 65 项测试均通过；分支尚未推送 |

- 更新时间：2026-10-05 23:40 UTC+8
- 分支：pol/GOV-01/shenton-ch6
- 起点 commit / 依赖分支与 commit：main 099cb24
- 目标与交付路径：`research/PoL2-DAO-Governance-Lab/`（`src/pol2dao/experiments/allocation_exp.py`、`tests/test_allocation.py`、`docs/results.md`、`docs/concept-mapping.md` 第 4b 节、`results/`）
- 本次改动范围：只在上述实验室目录内新增 E14、E15 并更新对应文档；未改动 benchmark、datasets、models、TASKS.md 与其他任务页。本页是 GOV-01 的补充页，主任务页见 GOV-01-shenton.md
- 下一步：团队审阅 `docs/concept-mapping.md` 第 4b 节标 ❓ 处（Token 的功能、共识熔断的触发与复核、「合理需求」由谁判定）；E15 的成对错误相关度可作为 MODEL-01 候选审核者的检查项
- 阻塞 / 需要谁帮助：无
- 环境 / 输出路径 / 资源预算：Python 3.10+；核心仅标准库，作图需 matplotlib；E14 约 10 秒，E15 为闭式计算，不足 1 秒；无 GPU、无付费 API
- 数据版本与可用分区：不使用 benchmark 数据；全部为合成模型，参数为假设值

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

日期｜留言人/Agent｜进展、问题或回复｜证据/相关分支｜下一步

2026-10-05｜Shenton / Claude｜新增 E14（比例分配、封顶逐级填充、加事前核验三种规则下的需求申报）与 E15（同底座审核者的错误相关度与独立升级，闭式计算）；条款对照新增第 4b 节｜本分支｜团队审阅 ❓ 项

## 交付或交接

- 结果入口：[docs/results.md](../research/PoL2-DAO-Governance-Lab/docs/results.md) 的 E14、E15 两节
- 复现：在实验室目录运行 `pip install -e ".[dev,plot]"`、`pytest`、`pol2dao experiments --only E14,E15`
- 检查：`python tools/check.py`（本目录）与实验室 `pytest`（65 项）
- 未测项：两个实验都是模型，不是关于真实人群或真实模型的证据；E15 的 μ、ρ、人工判别力均为假设；没有读取 GOV-01 以外任何真实 Skill 评审的实现
