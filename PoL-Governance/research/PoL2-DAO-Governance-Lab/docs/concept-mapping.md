# PoL2 条款 ↔ 机制 ↔ 代码 ↔ 测试

本文件逐条说明：PoL2 正文里的哪一句话，被翻译成了什么机制，写在哪段代码里，由哪个测试检查。条款编号采用 NaturalDAO 仓库 `PoLEn/` 英译版 2026-09-30 调整后的章节号：伦理对齐协议（EAP）为第 4 章，静观公理为第 3 章，AI 与人类文明的治理为第 5 章。中文原文 PoL/ 与英译版 PoLEn/ 已在同日统一为这套编号，两者分歧以中文原文为准。

> 这是一个**工程解读**，不代表 NaturalDAO 协作者的共同立场。标 ❓ 的地方是解读有分歧空间、需要团队讨论的。

## 1. 平等联结（EAP 4.3.1）

> 「平等对待每一个人和平等对待每一个人的行为，不能等同！」——原则平等适用于所有人，而不是不加区别地适用于一个人的所有行为。

| 解读 | 机制 | 代码 | 测试 |
|---|---|---|---|
| 人的权利平等 → 每人同样的投票预算 | `power="equal"`：每人 100 代币；对照组 `20/80` 让 20 % 的人持有 80 % 的代币 | `voting.budgets` | `test_twenty_eighty_budgets` |
| 行为可以被区别对待，但**不给人贴标签** | 判定接口 `judge(text)` 只接收文本，没有发言者参数；不存在任何「按人汇总」的分数 | `eap.LexiconJudge.judge` | `test_judge_sees_text_only` |
| 被标记后人的权利不变 | 被标记的人下一轮照常发言、照常投票 | `deliberation.Deliberation.post` | `test_flagged_speaker_keeps_turns` |
| 「平等获取资源」→ 反事实 | 保持每人的分配比例，把预算拉平，看结果是否变化 | `voting.equalize`, `replay` | `test_equal_power_can_flip_outcome`, `test_published_counterfactual` |

## 2. PAI 实现平等联结的核心要求（EAP 4.3.3）

| 条款原文 | 机制 | 代码 | 测试 |
|---|---|---|---|
| 平等发言权保障：严格轮流发言，不垄断对话 | `moderation="round_robin"`，抢话抛出 `TurnError`；允许主动跳过 | `deliberation` | `test_round_robin_enforced` |
| 决策共识辅助 | 质询期：决定前所有质询都必须得到解释 | `protocol.question/explain/finalize` | `test_unanswered_question_escalates` |
| 透明的边界记录 | 所有发言、筛查结果、修复提示都进入决策链 | `protocol.say` → `ledger` | `test_demo_chain_verifies_and_detects_tampering` |
| 平等获取资源 | 平等代币预算 | `voting` | 同上 |
| 发言平等度可度量 | 按消息数与字符数计算基尼系数、最大份额、沉默人数 | `Deliberation.voice_report` | `test_round_robin_keeps_minority_voice_under_hostility` |

## 3. 扬爱抑恨（EAP 4.3.2）

| 条款原文 | 机制 | 代码 | 测试 |
|---|---|---|---|
| 爱与恨不直接等同于好与坏、褒与贬 | 输出是「爱 / 恨 / 不在场」概率，不是「好 / 坏」分数 | `eap.Verdict` | — |
| 批评、愤怒、反对不能当作违规（亦见 PoL-Governance 模型调研提示） | 批评标记只记录为 `note:criticism-is-not-hate`，**不计入恨** | `eap.CRITICISM_MARKERS` | `test_criticism_and_anger_pass` |
| PAI 须守住人类伦理边界：不得制造虚假亲密（「叫我爸爸」） | `false_intimacy` 类别 | `eap.HATE_MARKERS` | `test_hate_patterns_are_flagged` |
| 「你怕不怕小狗？」——制造恐惧以获取控制 | `fear_control` 类别 | 同上 | 同上 |
| 「非爱非恨」的不在场状态 | 无任何标记 → `absence = 1.0` | `LexiconJudge` | `test_neutral_text_is_absence` |
| PAI 无需检测人的情绪状态 | 基线只匹配行为标记，不做情绪识别 | `eap` 模块说明 | — |
| 处理方式是修复，而不是清除 | 被标记 → 附修复提示，原文保留在链上；消息失去说服权重（模拟中） | `eap.repair_prompt` | `test_repair_prompt_names_category` |

## 4. 人类公共福利治理协议（第七章）

| 条款 | 机制 | 代码 | 测试 |
|---|---|---|---|
| 第 4 条 公开透明、可追溯可审计 | 追加式 JSONL 决策链，每条记录含上一条的 SHA-256 | `ledger.DecisionChain` | `test_demo_chain_verifies_and_detects_tampering` |
| 第 5.5 条 可验证决策链路：数据来源、推理步骤、伦理依据 | `decision` 记录包含 `data_sources`（选票和发言在链上的序号）、`reasoning_steps`、`ethical_foundations`、`ethical_checks` | `protocol.finalize` | 同上 |
| 第 9 条 质询权、解释义务 | 质询从不被拦截（筛查只记录）；每个质询需要 `explain` | `protocol.question/explain` | `test_unanswered_question_escalates` |
| 第 10 条 争议裁决过程公开，接受人类监督 | 不能定案时状态为 `escalated`，并写明原因 | `protocol.finalize` | `test_flagged_winning_option_escalates` |
| 第 11.5 条 所有修订版本永久存档 | 链只追加不可改；修订 = 新的会话记录，引用旧链头 | `ledger` | — ❓ 尚未实现专门的修订流程 |

## 4b. 生产公共化协议（第六章）与第七章第六条

| 条款 | 解读 | 代码 | 测试 |
|---|---|---|---|
| 第六章第五条 Token 不可交易、不可跨域转移、不与货币挂钩 | 与「人工货币」机制相容；❓ Token 只是记账单位，还是每人一份的个人预算，协议未定 | — | — |
| 第六章第六条 按需分配，AI 实时监测公共需求 | 需求来自申报时，规则必须封顶并核验：比较比例分配、封顶逐级填充、加事前核验 | `experiments.allocation_exp.needs_once`, `water_fill` | `test_proportional_rule_shifts_harm_to_honest_agents`, `test_water_fill_conserves_supply_and_caps` |
| 第六章第十条 私有事务触发共识熔断 | ❓ 熔断由「系统自动」触发并剥夺调用权，触发判定者、复核与恢复程序未写明 | — | — |
| 第六章第十一条 3 按「合理需求」无偿享有 | ❓ 「合理」由谁判定未写明；与第六条的需求信号问题同源 | — | — |
| 第七章第六条 3 伦理验证由 EAP 自动完成 | 若由同底座的多个审核者承担，冗余价值取决于错误相关度；独立复核的价值更大 | `allocation_exp.fa_mean`, `fa_any`, `escalation_frontier` | `test_more_reviewers_help_less_when_errors_are_correlated`, `test_escalation_frontier_is_monotone_and_respects_false_rejection` |

## 5. 来自 PoL2-Jev 文献综述的工程约束

NaturalDAO/PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey 的五条主要发现，在这里对应为：

| 发现 | 本仓库的做法 |
|---|---|
| 零样本检测可用，但默认阈值 0.5 下 F1 可能很低，阈值必须本地拟合 | `fit_threshold(scores, labels)`；`ScreeningPolicy` 的两个阈值都是参数 |
| 安全阀本身会被输入内容操纵 | 筛查结果只影响**路由**，不能单方面删除内容或剥夺权利；最终落到人 |
| 选项名改变会翻转结果（类型安全 ≠ 判断正确） | 判定值用显式枚举 `Verdict`；`CallableJudge` 要求返回命名概率 |
| 二元问题把「不知道」压成是/否 | 三值输出，含 `absence` |
| 升级给另一个 AI 未必能纠错，升级链末端必须有人 | `Route.ESCALATE` 表示「人类复核」，不是「再问一个模型」 |

## 6. 实验对应（E0–E15）

| PoL2 条款 / 问题 | 实验 | 结论（模型内） |
|---|---|---|
| 4.3.1 平等联结 · 平等获取资源 | E0、E3、E11 | 平等权力是基础；真实数据中一格结果翻转 |
| 4.3.3 平等发言权保障 | E0、E1、E8 | 敌意存在时，轮流发言是最有效的机制 |
| 4.3.2 扬爱抑恨 · 批评不是恨 | E4、E5、E9、E10 | 筛查只有在判定器准确且不偏向压制异见时才有净收益 |
| 4.3.1 人人平等 → 一人一身份 | E6 | 一人多号能击穿二次方投票，需要人格证明 |
| 第七章第 2 条 自主决策 | E7 | 依赖诚实报告；有人夸大时不优于二次方投票 |
| 第七章第 4、5 条 可验证决策链路 | E12 | 成本可忽略；篡改被精确定位 |
| 文献综述 G1–G7 | E13 | 每条轴线对应的模块 |
| 第六章第六条 按需分配 | E14 | 比例分配把夸大的代价转给诚实者，且不表现为浪费；封顶加核验可缓解 |
| 第七章第六条 3 伦理验证 | E15 | 同底座审核者错误高度相关时，加人不加保护；给不确定区间配独立复核更有效 |

## 尚未解决的问题

1. ❓ **自主决策 vs 人类投票。** PoLEn 第七章第 2 条：「自主意味着不需要人类投票或额外的决策机制」，人类保留建议权和监督权。DAO 实验恰恰是人类投票。本仓库把人类投票当作 PAI 决策的**输入**，把质询期当作监督权的实现。另一种读法「PAI 直接决定，人类只能质询」已在 `autonomy.py` 中实现，并在 E7 中比较：PAI 的决策质量取决于人们是否如实报告偏好。
2. ❓ **透明 vs 隐私。** 第 4 条要求完全透明；但公开记名选票会带来压力与报复风险（这本身可能是一种「恨」的机制）。目前使用化名。
3. ❓ **谁来定义恨语标记？** 基线词表由本仓库作者拟定，没有经过协作者共识。按 PoL2 的精神，这份词表本身也应该走一次本仓库的治理流程。
4. ❓ **筛查的代价由谁承担。** 模拟显示误报恰好落在少数派的批评上（见 [experiment-design.md](experiment-design.md)）。是否应该对少数派的发言使用更高的标记阈值？这会与「平等对待行为」冲突吗？
5. ❓ **身份。** 平等联结要求「一人一份」，而 E6 显示一人多号可以击穿二次方投票。人格证明本身又会带来隐私与排斥风险（没有证件的人怎么办？），这与 PoL2 的平等原则存在张力。
