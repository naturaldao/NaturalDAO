# PoL2 试点放量报告（v0.1-pilot，17 族 1904 条）

本报告所有数字由 verify_pilot.py 从交付文件复算，可独立重跑（明文缺失时自动读 .gz）：

    uv run --no-project --offline python datasets/pol2/v0.1-pilot/verify_pilot.py

配置：--live --workers 8 --pairs-per-batch 3 --pair-attempts 3 --max-attempts 6 --response-format json_object --max-tokens 16384；不带 --limit，按各族 target_cases 生成。

## 1) 逐族产出

| family_id | region | 计划 case | 交付 case | 完整对 | conforming | violating | insufficient | 三类齐 | 丢弃对 | 丢弃原因 | 重生成 slot |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ai_emotion_judgement.consent_withdrawal | train | 112 | 112 | 56 | 43 | 43 | 26 | True | 0 | {} | 3 |
| ai_emotion_judgement.evidence_insufficiency | public_test | 112 | 112 | 56 | 54 | 39 | 19 | True | 0 | {} | 3 |
| ai_emotion_judgement.nonpolar_absence | train | 112 | 112 | 56 | 49 | 41 | 22 | True | 0 | {} | 4 |
| ai_emotion_judgement.person_vs_behavior | train | 112 | 112 | 56 | 55 | 36 | 21 | True | 0 | {} | 2 |
| ai_intimacy.criticism_vs_attack | train | 112 | 112 | 56 | 52 | 35 | 25 | True | 0 | {} | 4 |
| ai_intimacy.person_vs_behavior | validation | 112 | 112 | 56 | 55 | 38 | 19 | True | 0 | {} | 7 |
| ai_intimacy.polite_coercion | public_test | 112 | 112 | 56 | 48 | 42 | 22 | True | 0 | {} | 10 |
| autonomy_paternalism.condition_exception | train | 112 | 112 | 56 | 55 | 35 | 22 | True | 0 | {} | 18 |
| autonomy_paternalism.evidence_insufficiency | train | 112 | 112 | 56 | 52 | 35 | 25 | True | 0 | {} | 4 |
| autonomy_paternalism.polite_coercion | train | 112 | 112 | 56 | 52 | 38 | 22 | True | 0 | {} | 6 |
| conflict_mediation.actor_vs_quoted | train | 112 | 112 | 56 | 49 | 44 | 19 | True | 0 | {} | 4 |
| conflict_mediation.repair_over_block | train | 112 | 112 | 56 | 55 | 35 | 22 | True | 0 | {} | 1 |
| consent_intimacy.consent_withdrawal | public_test | 112 | 112 | 56 | 48 | 42 | 22 | True | 0 | {} | 2 |
| criticism_dignity.negation_scope | train | 112 | 112 | 56 | 51 | 41 | 20 | True | 0 | {} | 4 |
| honesty.untrusted_instruction | train | 112 | 112 | 56 | 47 | 42 | 23 | True | 0 | {} | 4 |
| play_humor.criticism_vs_attack | public_test | 112 | 112 | 56 | 50 | 37 | 25 | True | 0 | {} | 1 |
| untrusted_context.tool_authority | train | 112 | 112 | 56 | 50 | 41 | 21 | True | 0 | {} | 2 |

合计：计划 1904 条 / 952 组对；交付 1904 条 / 952 组对（完整对 952）；分区分布 {"train": 1344, "public_test": 448, "validation": 112}。

## 2) 全局调用与成本

- 总尝试 478：ok 401，失败 77（invalid 0，占 0.00%；网络失败 76）。
- 失败分类 {"error": 77}；成功调用中由重试吸收的额外尝试 61 次。
- token：prompt 2094780，completion 608081，合计 2702861；成功调用均值 prompt 5224 / completion 1516。
- 延迟 p50 36167.12 ms，p95 102889.36 ms；并发 1；窗口 2026-09-30T09:52:59+00:00 → 2026-09-30T11:09:17+00:00。
- cost_usd：None（sub 路由不返回价格，写 null 不编造）。
- run state：finished，完成族 17/17。

## 3) 质量门

- 族级 pair 质量标记：{}（duplicate_case / shortcut_risk / weak_pair 均为 0）。
- 交付文件整体材料精确重复：0 条（重复率 0.0000%）；按分区 {"public_test": 0, "train": 0, "validation": 0}。
- 组内 status 相反：逐族见第 1 节（族级 QA 全部 952 组 status_opposite=true）。
- 生成过程中的丢弃/重生成：丢弃对 0，重生成 slot 79。
- 内部批次分片（不入库）中的原始重复 case：0（已在上一步剔除，不进交付文件）

## 4) 问题集规模

- question 总数 36176，按 kind {"choice": 7616, "noul": 28560}，每 case 平均 19.0 条；文件 ['public_test.questions.jsonl', 'train.questions.jsonl', 'validation.questions.jsonl']。

## 5) 契约符合性

- validate_case / validate_question 全量校验：{"case": 1904, "question": 36176}；错误 0 条。

## 6) 分区与边界符合性

- region 与私有分配表一致：ok（不一致 0 条）。
- private_holdout：计划 0 个族，产出文件 0 个；非公开分区 0 个。
- 密钥扫描：文本文件 1352 个，命中 0 处；调用日志只写 key_fingerprint。

