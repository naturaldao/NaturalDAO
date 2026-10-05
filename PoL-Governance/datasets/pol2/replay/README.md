# 通用决策回放池（DATA-02 / task-4）

防止只训练 PoL 专项数据导致模型“偏科”（把中性内容道德化、丢掉「信息不足 / 规则例外 / 普通业务风险」的判断力）。
本目录只做**审计、协议与流水线**，不存放任何第三方数据本体。

| 文件 | 内容 |
|---|---|
| [survey.md](survey.md) | HuggingFace 候选审计表：68 条候选的许可、固定 revision、来源与生成方式、形态、规模、分区、污染与剔除理由 |
| [candidates.json](candidates.json) | 审计表的机器可读形式（准入 15 / 观察 16 / 剔除 37） |
| [audit-2026-09-30.json](audit-2026-09-30.json) | 2026-09-30 由 HF API 拉取的元数据快照与校验结果（`problems: 0`） |
| [audit.py](audit.py) | 可复跑审计脚本：`fetch`（联网拉元数据）/ `build`（离线 fixtures）/ `verify`（必填字段与准入硬规则） |
| [rewrite.py](rewrite.py) | 英译中改写 + 教师重判流水线（默认离线；真实调用需 Lead 批准） |
| [replay_pool.md](replay_pool.md) | 回放池数据卡：准入/禁用、配比（9:1 或 8:2，按决策数）、去重策略、质量门 |
| [fixtures/](fixtures) | 离线测试用快照与自写样例（不是真实数据） |
| [test_audit.py](test_audit.py) / [test_rewrite.py](test_rewrite.py) | 全离线 unittest |

```powershell
uv run --no-project --offline python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q
uv run --no-project --offline python datasets/pol2/replay/audit.py verify --audit datasets/pol2/replay/audit-2026-09-30.json
```

边界：本目录的产物与 [datasets/pol2/](../README.md) 的四类 PoL 记录物理分开；回放池 100% train-only，
不接触 PoL 的 public_test / validation / private_holdout。上游依据见 [SPEC.md](../../../SPEC.md) 与
[datasets/README.md](../../README.md)。
