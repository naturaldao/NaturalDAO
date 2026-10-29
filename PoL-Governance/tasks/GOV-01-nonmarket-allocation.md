# [GOV-01] 公共资源不竞价分配的动态模拟（E16）

| 领取人 / Agent | 状态 / 最近进展（Agent 更新）|
|---|---|
| Codex / OpenAI Codex | 待集成；E16 三种规则已推送并提交 PR #54，300 次重复/格，70 项测试通过 |

- 更新时间：2026-10-30 21:00 Asia/Hong_Kong
- 分支：pol/GOV-01/nonmarket-allocation
- 起点 commit / 依赖分支与 commit：`main` / `d2e492f3ea84c8d5cc707e9a22488ea20ca376c6`
- 目标与交付路径：`research/PoL2-DAO-Governance-Lab/` 中 E16 非竞价资源分配实验
- 本次改动范围：实验算法与注册、单元测试、实验设计和结果说明、E16 PNG/PDF 图及 CSV；不改其他治理实验
- 下一步：请维护者审阅 PR #54 中的参数假设与优先等级的公共制定、申诉和复核边界
- 阻塞 / 需要谁帮助：无
- 环境 / 输出路径 / 资源预算：Python 3.12；标准库模拟、matplotlib 输出；无需 GPU 或外部 API
- 数据版本与可用分区：纯合成数据；每格 300 次、120 个主体、24 轮

## 进展与交流

日期｜留言人/Agent｜进展、问题或回复｜证据/相关分支｜下一步

2026-10-30｜Codex / OpenAI Codex｜实现 E16：人人同优先轮转、紧急等级优先、可行时先给人人一单位再按紧急等级分配三种规则；加入需求翻倍申报、每 6 轮一次的严重供给冲击；70 项测试全部通过，E16 每格完成 300 次模拟｜本分支，提交 `d0cec07`；结果见实验室 `docs/results.md`、`results/tables/e16_nonmarket_allocation.csv`｜PR #54 已开，等待审阅

## 交付或交接

- 结果入口：PR #54；实验室 `docs/results.md` 的 E16；`results/figures/e16_nonmarket_allocation.png`；`results/tables/e16_nonmarket_allocation.csv`
- 复现：实验室目录运行 `python -m pol2dao.cli experiments --only E16 --reps 500`
- 检查：`python -m pytest --basetemp .pytest-tmp`，70 passed；治理仓库 `tools/check.py` 因现有数据附件缺失而失败：`datasets/general/HF.md` → `data/jev-probs.jsonl.gz`
- 未测项：真实需求等级误判、申诉、隐私、共谋、多种公共资源及基础保障分层尚未纳入；模型不是现实公平性的证明
