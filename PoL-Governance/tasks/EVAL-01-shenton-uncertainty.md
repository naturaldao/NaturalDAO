# [EVAL-01] 评测的不确定性：族级置信区间、成对比较与最小可检出差

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| 鄢申涛 Shenton / Claude | 待集成；uncertainty.py 与 10 个单元测试、模拟脚本与说明已完成，tools/check.py 通过 |

- 更新时间：2026-10-05 23:50 UTC+8
- 分支：pol/EVAL-01/shenton-uncertainty
- 起点 commit / 依赖分支与 commit：main 3d278a9
- 目标与交付路径：`benchmark/pol2/uncertainty.py`、`benchmark/pol2/test_uncertainty.py`、`research/PoL2-Eval-Uncertainty/`
- 本次改动范围：**只新增文件**，不修改 `benchmark/pol2/evaluate.py`、README、数据或任何他人的文件。本任务只认领 EVAL-01 中"不确定性与功效"这一块；DATA-02 任务页提到正式拆分时会另开 `pol/EVAL-01/wenbo`，其余评测工作（指标、通用能力与主流安全对照）不在本页范围，欢迎在任务页留言协商文件归属或合并
- 下一步：团队审阅；用真实的公开测试报告估计族间差异；视协商并入 EVAL-01 的评测入口。
- 阻塞 / 需要谁帮助：无
- 环境 / 输出路径 / 资源预算：Python 3.10+，`uncertainty.py` 只用标准库；`research/` 下的模拟脚本需要 numpy，约 10 秒；无 GPU、无付费 API
- 数据版本与可用分区：不使用任何真实标签或保留集；仅用 `benchmark/pol2/fixtures/` 的合成样例与模型模拟

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

日期｜留言人/Agent｜进展、问题或回复｜证据/相关分支｜下一步

2026-10-05｜Shenton / Claude｜领取。起因：`evaluate.py` 只报点估计，而 SPEC 第 3 节、PROTOCOL 与 results/README 都要求报不确定性；`splits.py` 的分区是 5 族保留集、5 族校验集、19 族公开测试，案例在族内相关｜本分支｜实现 uncertainty.py 与测试，补模拟与说明
2026-10-05｜Shenton / Claude｜交付：族级区间、成对比较、最小可检出差、非劣效判定；在 fixtures 的真实评测报告上端到端跑通；模拟与说明在 research/PoL2-Eval-Uncertainty/｜本分支｜团队审阅；用真实的公开测试报告估计族间差异

## 交付或交接

- 结果入口：`research/PoL2-Eval-Uncertainty/README.md`
- 复现：`python -m unittest discover -s benchmark/pol2 -p "test_uncertainty.py" -q`；`python research/PoL2-Eval-Uncertainty/split_power_sim.py`
- 检查：`python tools/check.py` 通过
- 未测项：没有用真实的公开测试结果估计族间差异；模拟的 σ、ρ、错误率为假设值；未与 EVAL-01 的其他认领人协商合并
- 建议团队考虑：保留集建成更多小族（至少 30 个）；把最小可检出差写进结果卡模板；规定"低于最小可检出差的差值不排名"
