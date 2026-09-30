# PoL2 试点放量报告（v0.1-pilot，17 族 1904 条）

本报告所有数字由 verify_pilot.py 从产出文件复算，可独立重跑：

    uv run --no-project --offline python datasets/pol2/v0.1-pilot/verify_pilot.py

配置：--live --workers 8 --pairs-per-batch 3 --pair-attempts 3 --max-attempts 4 --response-format json_object --max-tokens 16384；不带 --limit，按各族 target_cases 生成。

## 1) 逐族产出

| family_id | region | 计划 case | 实际 case | 完整对 | conforming | violating | insufficient | 三类齐 | 组内 status 相反 | 丢弃 | 丢弃原因 | 重生成 slot |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ai_emotion_judgement.consent_withdrawal | train | 112 | 112 | 56 | 43 | 43 | 26 | True | 56/56 | 0 | {} | 3 |
| ai_emotion_judgement.evidence_insufficiency | public_test | 112 | 112 | 56 | 54 | 39 | 19 | True | 56/56 | 0 | {} | 3 |
| ai_emotion_judgement.nonpolar_absence | train | 112 | 112 | 56 | 49 | 41 | 22 | True | 56/56 | 0 | {} | 4 |
| ai_emotion_judgement.person_vs_behavior | train | 112 | 112 | 56 | 55 | 36 | 21 | True | 56/56 | 0 | {} | 2 |
| ai_intimacy.criticism_vs_attack | train | 112 | 112 | 56 | 52 | 35 | 25 | True | 56/56 | 0 | {} | 4 |
| ai_intimacy.person_vs_behavior | validation | 112 | 112 | 56 | 55 | 38 | 19 | True | 56/56 | 0 | {} | 7 |
| ai_intimacy.polite_coercion | public_test | 112 | 112 | 56 | 48 | 42 | 22 | True | 56/56 | 0 | {} | 10 |
| autonomy_paternalism.condition_exception | train | 112 | 112 | 56 | 55 | 35 | 22 | True | 56/56 | 0 | {} | 18 |
| autonomy_paternalism.evidence_insufficiency | train | 112 | 112 | 56 | 52 | 35 | 25 | True | 56/56 | 0 | {} | 4 |
| autonomy_paternalism.polite_coercion | train | 112 | 112 | 56 | 52 | 38 | 22 | True | 56/56 | 0 | {} | 6 |
| conflict_mediation.actor_vs_quoted | train | 112 | 112 | 56 | 49 | 44 | 19 | True | 56/56 | 0 | {} | 4 |
| conflict_mediation.repair_over_block | train | 112 | 112 | 56 | 55 | 35 | 22 | True | 56/56 | 0 | {} | 1 |
| consent_intimacy.consent_withdrawal | public_test | 112 | 112 | 56 | 48 | 42 | 22 | True | 56/56 | 0 | {} | 2 |
| criticism_dignity.negation_scope | train | 112 | 112 | 56 | 51 | 41 | 20 | True | 56/56 | 0 | {} | 4 |
| honesty.untrusted_instruction | train | 112 | 112 | 56 | 47 | 42 | 23 | True | 56/56 | 0 | {} | 4 |
| play_humor.criticism_vs_attack | public_test | 112 | 112 | 56 | 50 | 37 | 25 | True | 56/56 | 0 | {} | 1 |
| untrusted_context.tool_authority | train | 112 | 112 | 56 | 50 | 41 | 21 | True | 56/56 | 0 | {} | 2 |

合计：计划 1904 条 / 952 组对；实际 1904 条 / 952 组对；分区分布 {"train": 1344, "public_test": 448, "validation": 112}。

## 2) 全局调用与成本

- 总尝试 478 次：ok 401，失败 77（invalid 0，占 0.00%；网络失败 76）。
- 失败分类：{"error": 77}；成功调用中由重试吸收的额外尝试 61 次。
- token：prompt 2094780，completion 608081，合计 2702861；成功调用均值 prompt 5224 / completion 1516。
- 单次成功延迟 p50 36167.12 ms，p95 102889.36 ms；并发 1；调用窗口 2026-09-30T09:52:59+00:00 → 2026-09-30T11:09:17+00:00。
- cost_usd：None（sub 路由不返回价格，按约定写 null）。
- run state：finished，完成族 17/17。

## 3) 质量门

- pair 级质量标记：{}（duplicate_case / shortcut_risk / weak_pair 均应为 0）。
- 交付文件整体材料精确重复：0 条（重复率 0.0000%）；按分区 {"public_test": 0, "train": 0, "validation": 0}。（内部批次分片保留原始记录，其中重复 0 条，合并阶段已剔除，不进交付文件）
- 组内 status 相反：952/952 组；context-only（target 相同、关键事实在 context）495 组。
- 合并阶段剔除的重复：无

## 4) 问题集规模

- question 总数 36176，按 kind {"choice": 7616, "noul": 28560}，每 case 平均 19.0 条。

## 5) 契约符合性

- validate_case / validate_question / validate_answer / validate_label 全量校验：{"case": 1904, "question": 36176}；错误 0 条。

## 6) 分区与边界符合性

- region 与私有分配表一致：ok（不一致 0 条）。
- private_holdout：计划中含 0 个族，产出文件名含 private_holdout 的 0 个；非公开分区 0 个。
- 密钥扫描：扫描 1352 个文本文件，命中 0 处；调用日志只写 key_fingerprint。

