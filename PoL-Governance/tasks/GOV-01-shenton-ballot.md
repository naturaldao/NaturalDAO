# [GOV-01] Agent 密封投票：用投票决定事件推进（IVXV 结构）

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| 鄢申涛 Shenton / Claude | 待集成；协议、三组实验与 32 项测试完成，本目录 tools/check.py 通过 |

- 更新时间：2026-10-18 23:00 UTC+8
- 分支：pol/GOV-01/shenton-ballot
- 起点 commit / 依赖分支与 commit：main ad64542；内容来自 https://github.com/shentonyan/pol2-agent-ballot （commit ae61b8b，v0.4.0）。与 pol/GOV-01/shenton 的治理实验室互补，不依赖其未合并改动
- 目标与交付路径：`research/PoL2-Agent-Ballot/`
- 本次改动范围：新增上述目录与本任务页。未改动 TASKS、benchmark、datasets、models 与任何现有文件。原仓库的网页演示与 CI 未复制，在线演示见 https://shentonyan.github.io/pol2-agent-ballot/
- 下一步：请 PoL2 编辑确定事件推进采用多数决还是共识（见下方「需要决定的问题」）；用更易从众的模型或更模糊的证据重跑实验三
- 阻塞 / 需要谁帮助：需要 PoL2 编辑对决策规则给出意见
- 环境 / 输出路径 / 资源预算：Python 3.10+，依赖 PyNaCl；作图需 matplotlib。实验一、二在本机数分钟内完成，无 GPU。实验三调用一个 OpenAI 兼容接口（首轮用 Claude Haiku 5.5，560 次调用）
- 数据版本与可用分区：未使用 PoL-Governance 的 datasets 或 benchmark。实验一、二为脚本 Agent 的合成仿真；实验三使用自动生成的发布审核提案（已知正确答案），模型原始回复随结果公开

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 做了什么

当多个 Agent 共同决定一个事件能否进入下一阶段时，本模块给出一个可审计的投票流程，结构参照爱沙尼亚国家在线投票系统 IVXV：组织者签名的资格名单、双信封（密封 + Ed25519 签名）、哈希链账本与签名回执、改票以最后一票为准、Shamir 2-of-3 托管选举私钥，以及只凭导出记录复算全过程的独立审计。选票「开票前保密、开票后公开」，对应 PoL2 第七章对可验证决策链路的要求。另有多轮密封投票的协商共识模式。

| 实验 | 设置 | 结果 |
|---|---|---|
| 一：密封与公开顺序投票 | 9 个脚本 Agent，证据正确率 0.7，各 30,000 次 | 集体正确率 0.903 与 0.843；公开条件下 22.6% 的票违背自身证据，与精确理论值一致 |
| 二：多轮密封投票达成共识 | 0–4 个固执 Agent，各 3,000 次 | 达成共识比例 1.00 / 0.71 / 0.50 / 0.35 / 0.23；未达成时事件停在原阶段 |
| 三：语言模型 Agent | Claude Haiku 5.5，7 个 Agent，40 个提案，配对比较 | 密封与公开均 37/40，等于证据上限；违背自身证据 0/280 与 2/280，仅在落后 5–6 票时出现；未观察到信息级联 |

详见 [README](../research/PoL2-Agent-Ballot/README.zh-CN.md)。

## 需要决定的问题

PoL2 第七章写明 NaturalDAO 的自治无需人类投票。本模块中的投票者是 Agent，人类保留建议权与质询权（`Event.add_query` / `Event.answer_query`）。事件推进应采用多数决（>1/2 或 ≥2/3）还是一致同意的共识，留待 PoL2 编辑确定；实验二给出了两者的代价对照。

## 进展与交流

2026-10-18｜Shenton / Claude｜完成 v0.4.0：协议、审计、共识模式、三组实验、网页演示｜shentonyan/pol2-agent-ballot｜迁入协作目录，登记于 GOV-01

## 交付或交接

- 结果入口：[research/PoL2-Agent-Ballot/README.md](../research/PoL2-Agent-Ballot/README.md)；实验三方案与日志在 `experiments/llm_herding_protocol.md` 与 `experiments/results/llm_herding/`
- 复现：在该目录运行 `pip install -e ".[dev,experiments]"`、`pytest`、`python experiments/sealed_vs_open.py`、`python experiments/consensus_rounds.py`
- 检查：`uv run --no-project --offline python tools/check.py`（本目录）通过；模块 `pytest` 32 项通过
- 与其他任务的关系：可作为 GOV-01 治理实验室「投票」环节的 Agent 版本；`KeywordEAP` 只是占位，可换成 EVAL-01 / MODEL-02 产出的判定器
- 未测项：实验三只有一个模型、一类任务、40 个提案，区间较宽；组织者是单把签名密钥；任意 2 个托管人合谋可提前解密；未接入链上注册表；协议保证决策可验证，不保证 Agent 判断质量
