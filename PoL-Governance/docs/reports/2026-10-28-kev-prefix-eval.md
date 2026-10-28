# Kev 前后对照评测（Session B，2026-10-28）

> 状态：**已完成（2026-10-28）**。最终结果卡见 [results/MODEL-02-kev-prefix-eval/CARD.md](../../results/MODEL-02-kev-prefix-eval/CARD.md)；可视化单页见 [HTML 报告](2026-10-28-kev-prefix-eval.html)。
> 边界：本报告只描述冻结视图、指定 checkpoint 与配置下的观察性配对比较；不训练、不调参、不为保留集调 prompt/阈值；私有保留集只在仓库外隔离执行、只回传聚合。

## 0. 一句话结论

在共同有效上下文（384/1024/2048，7,347 题）与 bf16/GPU 配置下：**seed43 的配对准确率 +0.95 pt（95% CI [+0.30,+1.65]，事后选择的探索性）**，但**概率校准显著更差**（ECE10 0.0247→0.2081，Brier +0.073、NLL +0.70、5% 错误预算下可自动处置份额 0.1805→0.1424）；seed17 +0.60 pt（CI 跨 0）、seed29 持平。JevBench（第三方 coherence）上 seed43 80.9 vs 原版 72.2（+8.7），但 coherence≠accuracy、且本表无 accuracy。没有证据支持「M10 整体更好」。

## 1. 背景与范围

- 任务书：`.agent/prompts/SESSION-B-final-eval.md`（所有者 2026-10-27/28 授权：评测可用 GPU、守静默时段 00:30–09:30/12:30–15:30；私有保留集方式 2 本机隔离）。
- 对象：原版 Kev-4B（`jaredpalmer/kev-4b@v1.0`，Hub sha `6cfce5c2fa4b`）vs POL2 score-v2 M10（GitHub Release `pol2-score-v2-v1.0.0` 的 seed-43/17/29；研究预发布，非生产认证）。
- 评测集：general v5 私有保留集（6,541 items / 7,990 questions，en-only；choice 5,501 / noul 1,446 / score 1,043）。与 M10 训练数据（mixed kev-m10 6,827 行）**精确 state/question/id 重叠审计为 0**；模糊语义重叠未审计（限制）。
- Kev 表与我们的 Qwen3-1.7B 线**分表**，不混排；JevBench coherence 与 accuracy 分表。

## 2. 方法（预注册口径）

### 2.1 数据转换与 suite

- 逐题映射：state/instructions 原文；choice 选项 key 中立化为 `opt_<i>`（保留顺序与 label 文本）、label=选项 key；noul label=bool（false/true、no/yes、yes_/no_ 前缀唯一判定，1,446 题全部可判）；score criteria=scale.labels、label=answer−min（1,043 题全部可判）。映射失败 0；53 题按 view 规则（>4,000 chars）标 overlong，主表排除、全量敏感性另计。
- 组装 Kev 冻结 suite（官方 `kev.benchmark --suite`）：manifest 记录 context 与文件 sha；suite 内另有 **permuted 600**（确定性 sha256 抽样，criteria 顺序打乱）与 **isolation 1,929**（多问题 item 的每题单独成记录）两个变体。记录 id 用中性 `holdout/<n>`；join/sidecar 含 item id，仅在仓库外临时使用。
- **主口径（共同支持上下文）**：原版 Kev-4B 以 384/1024/2048 训练（= Kev 官方 suite `CONTEXT`）；M10 训练 `max_state=4096`（branch 4,736 / packed 5,760）；共同有证据范围 = 384/1024/2048。实测 6,299 records / 7,347 questions 可入（整条拒绝 242/643：state 228、branch 14），admitted 全部非 overlong。**serving context 全量（7,937 / 7,990 题）只作敏感性**。
- 长度分布：主口径 state tokens p50 74 / p90 165 / p99 329 / max 383；全量 p50 87 / p90 354 / p99 1,113 / max 5,712。

### 2.2 模型加载与运行

- 隔离副本固定底座 revision：`pin_checkpoints.py` 把 seed-43/17/29 的 `head.pt` 中 `base_revision`（null）固定为 `1001bb4d826a52d1f399e183466143f4da7b741b`（Qwen3.5-4B-Base 训练时 revision = 当前 HF main）；原版本身已记录同一 revision。断言 head 张量不变并记录前后 sha。
- 运行：Kev commit `2074cc4`；`torch 2.9.1+rocm7.2.1`（超出 Kev 声明 `torch<2.9`，披露）、`transformers 5.20.2`、`peft 0.21.2`；device=cuda（ROCm）、dtype=bf16、backend=torch、merge=1、attn=eager、cuda_graphs=0、fused=0；`HSA_ENABLE_DXG_DETECTION=1`。未安装 flash-linear-attention/causal-conv1d → 参考实现（正确性优先，非性能最优）。
- 温度：**不重拟合**（任务书）。served = checkpoint 自带温度（原版 2.406，Kev 自家 dev 拟合；M10=1.0 未拟合）；raw_t1 = 由记录 logits 还原 raw logits 后的 T=1。

### 2.3 指标与统计

- 决策指标：accuracy（overall + kind/lang/domain/option bucket/state 长度层）、Brier、NLL、ECE（10-bin = Kev 口径；15-bin = EVAL-PROTOCOL 口径，并列）、coverage@5% error budget（Kev 定义；附 accepted n 与接受集错误率）、AURC；score 题 MAE/RPS。
- 配对比较：同一 (id, question) 配对；按 record 簇（declared group 合并，其余 item 自成簇）做 1,000 次 cluster percentile bootstrap，95% CI，seed=0；三个 seed 分别与 original 比较，不做多重比较校正（逐比较 CI，注明）。单模型 CI：additive 指标 1,000 次、ECE/coverage 200 次。
- 变体：permuted 报 mean/max max-prob delta、flip rate、accuracy_unchanged_rate 与 cluster CI；isolation 报 packed vs separate 的 delta/flip。
- 独立交叉核对：`verify_metrics.py` 在同一 rows.json 上比较 aggregate 与 `kev.metrics`，acc/brier/nll/ece 差值 ≤1e-9（实测 ~1e-16）。

## 3. 结果

以 [结果卡](../../results/MODEL-02-kev-prefix-eval/CARD.md) 为准，摘要：

- **主口径 n=7,347（cluster=6,299）**：acc original 0.6414 vs seed43 **0.6509**（Δ **+0.95 pt**，95% CI [+0.30,+1.65]）/ seed17 0.6473（+0.60 pt，CI [−0.11,+1.31]）/ seed29 0.6411（−0.03 pt，CI [−0.77,+0.65]）。
- **校准**（served）：original ECE10 0.0247 / Brier 0.4773 / NLL 0.9945；seed43 0.2081 / 0.5500 / 1.6971；raw T=1 下 seed43 仍更差（Brier 0.5500 vs 0.5238，NLL 1.6971 vs 1.3313）。
- **automation share @5% 错误预算**：original 0.1805 [0.1543,0.2113] vs seed43 0.1424 [0.1069,0.1854]；confident-error-rate 0.0069 vs 0.1371。
- **分层**：seed43 在 choice（0.6583 vs 0.6259）与 knowledge_reasoning（0.7015 vs 0.6765）更好；original 在 noul（0.7707 vs 0.7174）、score（0.5579 vs 0.5225）、decision_mechanics（0.5972 vs 0.5874）更好。选项 3–4 桶 seed43 更好，其余桶原版更好。
- **serving 敏感性**：extended（7,933）/ full（7,976）同向，seed43 Δacc +1.05 pt [+0.38,+1.77]。
- **变体**：M10 的选项顺序敏感度略高（permuted mean_max_delta 0.093–0.103 vs 原版 0.061；flip 10.7–11.3% vs 10.2%）；isolation 几乎无差（≤0.0035）。
- **延迟**（GPU bf16）：median 80–83 ms / p95 362–388 ms；四个 checkpoint 各约 16–17 min。

## 4. JevBench coherence（第三方，第二主表）

- 第三方：JevBench（Chen Feng, QUB；非 TypeSafe）；`jevbench==0.1.0`（Apache-2.0，数据随包可离线），suite `jevbench-mini` v1（240 cases/50 relations/1,248 requests），2026-10-28 运行；服务 `kev.serve`（GPU bf16、merge=1、eager），每模型全新缓存目录 + serve POST 计数复核（各 1,442）。
- 结果（×100 对齐榜单）：**kev-original 72.19 [70.16,74.17]**（REP 74.7 / BAT 100 / MEA 30.4 / LOG 68.3 / CHO 87.5）；**seed43 80.91 [78.66,83.15]**（REP 80.8 / BAT 100 / MEA 56.6 / LOG 87.9 / CHO 79.2）；Δ overall **+8.72**（MEA +26.2、LOG +19.6、CHO −8.3）。
- 外部参照：官方 leaderboard（2026-10-28 读取）Kev-4B overall 71.9 / acc 87.9% / 名次区间 9–15；我们复现原版 72.19（bf16 vs 官方 fp32）。**未提交榜单**（无公开提交入口），对外称 reproduced locally, not listed。
- **coherence ≠ accuracy**：该基准可被均匀回答刷到 89.4（accuracy 39.8%）；本 session 无 JevBench accuracy（需第三方 gold，未取）。+8.7 只说明第三方一致性指标更好，须与 §3 的 general v5 结果并读（那里 seed43 校准更差）。

## 5. 失败、未测与限制

- GPU 依赖版本偏离 Kev 声明（torch 2.9.1 vs <2.9）；bf16 与官方 fp32 exact path 不同源（两模型同口径，但绝对值不可与官方榜直接比较）。
- 原版温度由 Kev 自家 dev 拟合、M10 未拟合 → served 校准/automation 对比为「随权重交付配置」，非公平校准因果估计。
- seed43 事后选择（看完全部结果后选为默认推荐）→ 探索性；seed17/29 完整同表；非 ensemble。
- M10 训练数据为 POL2 score-v2（专家规则数据）+ MRI replay；与本保留集精确重叠 0，但模糊/语义重叠未审计，不声称独立泛化。
- 未测：显存峰值（WSL 无 amdgpu 模块）；GPU 温度；JevBench accuracy（需第三方 gold，本 session 未取）；Kev 官方套件复现（breadth-v1 需私有镜像）。
- **首轮 full-suite OOM**：eager attention 在 row=4,733 tokens 记录处 HIP OOM（尝试分配 4.01 GiB）；`screen_suite.py` 剔除 5 条 clean（14 题，row 2,132–5,828）与 13 条 isolation 变体后重跑成功（rejected=0），不可测项单列。
- **JevBench 缓存陷阱**：jevbench 0.1.0 请求缓存不区分 serve checkpoint，单独 `--no-cache` 仍复用旧响应（两模型分数逐位相同、serve 仅 1 次 POST）；改为每模型全新 `--cache-dir` + POST 计数断言（1,442 次/模型）后重跑，本报告为修正后结果。
- 所有失败/拒绝计数见 CARD 覆盖表；不填 0、不省略负面结果。

## 6. 复现

```bash
# CPU/网络：准备仓库外评测文件 + 固定底座副本 + 重叠审计
bash benchmark/kev_prefix/prepare_eval.sh
python benchmark/kev_prefix/pin_checkpoints.py --src-root <weights> --out-root <仓库外>/ckpt --seeds 43 17 29 --kev-hub jaredpalmer/kev-4b@v1.0
python benchmark/kev_prefix/overlap_audit.py --holdout-items <仓库外>/items.jsonl --candidate <release>/data/mixed-training/kev-m10.jsonl --out <仓库外>/overlap-audit.json
# GPU（静默时段外）：4 checkpoint 顺序评测 + 三次聚合
bash benchmark/kev_prefix/run_models.sh
bash benchmark/kev_prefix/analyze.sh
# JevBench（第三方）：serve + mini + 汇总
bash benchmark/kev_prefix/run_jevbench.sh kev-original seed43
python benchmark/kev_prefix/jevbench_summary.py --report kev-original=<...> --report seed43=<...> --reference kev-original --out <仓库外>/jev-summary.json
# 收尾：check.py；删除私有临时副本
python tools/check.py
bash benchmark/kev_prefix/cleanup_private.sh --yes
```

最终 `python tools/check.py`：**pass（exit 0；831 tests OK + 29 tests OK/skip 3，2026-10-28）**；私有保留集临时副本已删除，仓库内只保留聚合 JSON。

## 7. 结论边界

- 最多结论：在冻结的数据视图、转换、Kev commit、底座/权重 revision、长度口径、精度与温度配置下，各指定 checkpoint 的配对指标与不确定性。
- 不能声称：模型方法总体优劣、通用能力非劣、生产安全、减少现实伤害、跨群体泛化、JevBench 准确率、保留集阈值已验证。
- 措辞按 `.agent/notes/2026-10-28-card-outline.md` 的三类模板；seed43 选择后披露按专家模板。