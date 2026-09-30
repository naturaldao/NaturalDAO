=== 交付侧 ===
run state=finished, complete_families=2/2, cases=224/224, pairs=112
pair flags={}
run: accepted_pairs=112 dropped_pairs=0 drop_reasons={} regenerated_slots=4 duplicate_case_cases=0 class_coverage_complete=True missing=[]
  ai_emotion_judgement.consent_withdrawal: cases=112 conforming=46 violating=41 insufficient=25 三类齐全=True
  autonomy_paternalism.condition_exception: cases=112 conforming=53 violating=36 insufficient=23 三类齐全=True
组内 status 相反: 112/112；contrast={'conforming_vs_violating': 64, 'conforming_vs_insufficient': 35, 'insufficient_vs_violating': 13}
精确重复 case: 0/224 = 0.0000%
跨族精确重复: 0

=== 调用侧（全部历史尝试） ===
calls=107 ok=91 failed=16 失败率=15.0%
prompt=437737 completion=112844
失败分类: {"SSL": 13, "524": 2, "other": 1}

=== json_object + 大预算时代（含重试后的口径） ===
calls=49 ok=43 failed=6 失败率=12.2%
失败分类: {"SSL": 5, "524": 1}
prompt=206938 completion=55309

=== 每千条 case 预算 ===
每批 3 组对 = 6 条 case；成功调用均值 prompt 4813 / completion 1286
观察到的尝试失败率 12.2%（全部为网络瞬断，invalid=0）
折合每千条 case：约 190 次调用，prompt 约 914004 tokens，completion 约 244289 tokens，合计约 1158293 tokens
10,904 条（96 族全量）预算：约 2071 次调用，约 10.0M prompt + 2.7M completion tokens
单次成功调用延迟 p50 25.3s / max 111.5s；并发 8 时 10,904 条约需 1.8 小时
按 13% 尝试失败率，全量预计约 254 次失败尝试会被重试或丢弃（invalid 0，均为网络瞬断）
cost_usd: 0（sub 路由不返回价格，按约定写 null 而不是编造）