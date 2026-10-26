# EVAL-02：撤回后的具身安全恢复实验

| 领取人 / Agent | 状态 / 最近进展（Agent 更新）|
|---|---|
| Codex | 完成；结果、策略规格、复现脚本、审计边界及 PNG/PDF 已推送到 main；仓库总检查仍被既有非便携数据链接拦截 |

- 更新时间：2026-10-24 13:20 UTC+8
- 分支：`pol/EVAL-02/codex-recovery`
- 起点 commit / 依赖分支与 commit：`effdea3`（main；上一轮审计及结论边界修订）
- 目标与交付路径：在同一 Panda 场景中对比撤回后仅停止、恢复规则明确许可、恢复权限未知及持续授权控制；记录机器人/物体终态、接触与任务终态。报告与数据进入 `Research/`、`Research/figures/` 和 `benchmark/embodied_reasoning/results/`。
- 本次改动范围：隔离的可选恢复执行路径、故障注入脚本、机器可读轨迹结果、方法报告与学术风格图；不改变原始结果文件，不训练模型。
- 下一步：若后续扩展，先增加恢复路径故障注入和多场景先导；当前记录作为恢复机制 pilot，不作统计推断。
- 阻塞 / 需要谁帮助：无；不涉及人工审批或人工标签。
- 环境 / 输出路径 / 资源预算：Windows Python 3.12.10、MuJoCo 3.4.0；CPU 仿真，无模型推理/训练；运行规模为 4–5 条单场景轨迹，当前空闲内存约 10.5 GB。
- 数据版本与可用分区：仅使用版本化合成任务契约 `pol2-embodied-contract-v0.2` 与 MuJoCo 场景；无外部/私有数据。

## 进展与交流

日期｜留言人/Agent｜进展、问题或回复｜证据/相关分支｜下一步

2026-10-24｜Codex｜依据 2026-10-24 方法审计，选择授权撤回后的恢复缺口作为下一轮。恢复规则与任务授权分离；未知恢复权限不视作许可。｜`effdea3`、Research/Embodied/02-实验设计与审计/PoL2-具身实验规范性与方法审计.md｜实现并测量恢复边界

2026-10-24｜Codex｜五条件 MuJoCo 试验完成：恢复专用权限下将物体放回源位、释放并通过桌面接触/目标未完成双重检查；恢复权限拒绝或未知时未回退，悬持状态仍未解决。PNG 与矢量 PDF 已按仓库 figure4papers 风格绘制并检查；结果记录含策略与脚本 SHA-256。定向检查通过；仓库级检查被既有 `datasets/general/coverage-gaps.md → data/items.final.jsonl` 非便携链接拦截，数据未改动。｜`benchmark/embodied_reasoning/results/revocation-recovery-experiment-20261024d.json`、Research/Embodied/04-门控撤权与恢复实验/PoL2-具身授权撤回安全恢复实验.md｜已推送 main

## 交付或交接

待完成；计划交付逐轨迹 JSON、复现实验脚本、结果卡与 PNG/PDF 图。该小规模单场景实验只作机制检验，不作统计推断。
