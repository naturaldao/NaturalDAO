# [GOV-01] 优先等级误判与申诉复核（E17）

| 领取人 / Agent | 状态 / 最近进展（Agent 更新）|
|---|---|
| Codex / OpenAI Codex | 待集成；E17 模拟已完成，比较分类误差、虚报比例和有限申诉复核容量 |

- 更新时间：2026-11-01 11:10 Asia/Hong_Kong
- 分支：pol/GOV-01/appeal-robustness
- 起点 commit / 依赖分支与 commit：`main` / `630c0ec4204380a9a03bc7ab7bfe40c2fc471fcc`
- 目标与交付路径：`research/PoL2-DAO-Governance-Lab/` 的 E17 代码、图表、CSV、设计与结果说明
- 本次改动范围：新增等级误分类与申诉复核模拟；更新实验注册、测试、README、实验设计和结果图集；把已集成 E16 任务标为完成
- 下一步：评审复核假设、优先等级的共同制定方式以及申诉程序的延误与成本；待集成后再与 PPA 动态公平配给基线比较
- 阻塞 / 需要谁帮助：无
- 环境 / 输出路径 / 资源预算：Python 3.12；纯合成模型，matplotlib 出图；无 GPU 与外部 API
- 数据版本与可用分区：120 主体、24 轮；分类误差 10%/25%，虚报 0%/15%/30%，每格 200 次重复

## 进展与交流

日期｜留言人/Agent｜进展、问题或回复｜证据/相关分支｜下一步

2026-11-01｜Codex / OpenAI Codex｜新增 E17：比较无申诉与 10%/25% 复核容量；分类误差、虚假紧急申报和复核误批同时进入模型；75 项实验室测试通过，每格完成 200 次模拟｜本分支，结果见实验室 `docs/results.md` 和 `results/tables/e17_priority_appeals.csv`｜上传分支并开待集成 PR

## 交付或交接

- 结果入口：实验室 `docs/results.md` 的 E17；`results/figures/e17_priority_appeals.png`；`results/tables/e17_priority_appeals.csv`
- 复现：实验室目录 `python -m pol2dao.cli experiments --only E17 --reps 500`
- 检查：`python -m pytest --basetemp .pytest-tmp`，75 passed；总仓库检查受非本任务数据附件缺失影响
- 未测项：审核等待、真实审核成本、申诉理由质量、公开参与制定等级、隐私和基于社区的监测均未实现；所有审核参数为假设值
