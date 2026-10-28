# Kev 前后对照评测（Session B，benchmark/kev_prefix）

本目录实现「原版 Kev-4B vs POL2 score-v2 M10（seed-43/17/29）」在我们评测集上的规范对照，
以及第二主表 JevBench coherence 的运行入口。**只做推理/评测**：不训练、不改模型、不为保留集调阈值/提示。

## 1. 对象与版本

| 角色 | 权重 | 版本 | 自带温度 |
|---|---|---|---|
| 原版 Kev | `jaredpalmer/kev-4b@v1.0` | Hub sha `6cfce5c2fa4b`（tag v1.0 = `591dcb5bd6d0`） | 2.41（Kev 在自家 dev 拟合） |
| 微调版（主） | `seed-43`（本地产权 `~/src/polgov/pol2-release/v1.0.0/weights/seed-43`） | Release `pol2-score-v2-v1.0.0`；init_from Kev-4B | 1.0（head.pt 记录，未拟合） |
| 微调版（变体） | `seed-17` / `seed-29` | 同上 | 1.0 |

- 底座：`Qwen/Qwen3.5-4B-Base@1001bb4d826a52d1f399e183466143f4da7b741b`（与项目 pin 一致；seed-43 head.pt 的 base_revision 为 null，评测前由 HF snapshot 固定）。
- seed-43 是「看到全部结果后选出的唯一双门通过版本」，**必须披露**；三个 seed 不是 ensemble。
- 与我们的 Qwen3-1.7B 线（base vs Track A）**分表**，不混排（EVAL-PROTOCOL §1.1/§1.2）。

## 2. 评测集与转换（convert.py）

- 评测集：general v5 私有保留集（6,541 items / 7,990 questions，en-only；choice 5,501 / noul 1,446 / score 1,043；137 items 有 declared group）。私有数据只在仓库外隔离目录，只回传聚合，评测后删除临时副本。
- 每题一条 Kev Question，state/instructions 用原文；choice 选项 key 换成中性 `opt_<i>`（原始 key 多为截断文字，直接渲染会重复/失真），label 用 option key；noul label 为 bool（false/true、no/yes、yes_/no_ 三类 key 规则唯一判定）；score criteria 用 `scale.labels`，label = answer − min。
- **映射失败 0**：无 target / 答案不在选项内 / score 越界 / noul 歧义均为 0（实测）。任何无法映射的问题按 `SkipQuestion` 跳过并计数，绝不猜标签。
- **超长**：`len(state)+len(instructions)+Σ选项渲染 > 4000 chars`（沿用 general v5 view 规则）标记为 overlong，**保留记录但不进主表分母**，另出全量敏感性；两个模型同口径。
- 不做 >26 选项跳过：Kev pointer head 支持至 255 选项（Kev 与 letter-SFT 的能力边界不同，因此 Kev 表的口径以 Kev 侧为准，并在结果卡披露与 Track A 分母差异）。

## 3. Kev suite（build_suite.py）

- 把转换结果组装成 Kev 冻结 suite（`kev.benchmark --suite`）。manifest 的 context 使用 Kev serving 上限（max_state 65,536 / max_branch 73,728 / max_packed 139,264，truncate=false），使全部 9,070 条记录可编码；**但主分析不取全量**：
  - **主口径（共同支持上下文，专家裁决 P0）**：原版 Kev-4B 以 384/1024/2048 训练（= Kev 官方 suite 的 `CONTEXT`），M10 训练 `max_state=4096`（branch 4,736 / packed 5,760）；两者共同有证据的范围 = **384/1024/2048**。实测该子集 = **6,299 records / 7,347 questions**（整条拒绝 242 records / 643 questions：state 228、branch 14），admitted 全部非 overlong。主表只用该子集，所有模型同分母。
  - **扩展/敏感性**：serving context 全量（排除 overlong 后 7,937 题；含 overlong 全量 7,990）作为敏感性表，并报 overflow/拒绝数与长度分布。
  - 长度分层：state token p50/p90/p99 = 74/165/329（主口径）与 87/354/1,113（全量），全量表见结果卡；字符桶仅作 view 对照。
- manifest 记录 context 与文件 sha256/records；**suite_sha256 = manifest digest**，同一次评测两次运行相同，可用于 `kev.compare`。
- 变体（同一 suite 内）：
  - `permuted` 600 题：按 sha256 确定性抽取 choice 题（不看标签/模型），criteria 顺序打乱，parent_id 指向 clean 记录 → option-order 稳健性（Kev summarize 自动算 mean_max_delta / flip_rate）。
  - `isolation` 1,929 题：多问题 item 的每题单独成记录 → packed（一次请求多题）vs separate（逐题）的「问题隔离」对比。
- 个人可复现：`prepare_eval.sh` 生成 `records.jsonl / sidecar.jsonl / suite / join.jsonl`（均在仓库外）并打印聚合计数。

## 4. 指标与统计（aggregate.py）

- 主指标：accuracy（overall + by kind/lang/domain/option bucket/state-chars bucket）、Brier、NLL、ECE（10 箱 = Kev 口径；15 箱 = EVAL-PROTOCOL 口径）、automation share（`coverage_at_5pct_error`，Kev 定义）、AURC、score 题 MAE/RPS；GPU 延迟 p50/p95 取自 `report.json`；CPU 延迟用 `cpu_latency.py` 在**公开** validation 子集上测。
- 校准：**不在保留集重拟合温度**。报告两套：`served`（checkpoint 自带 T）与 `raw_t1`（由记录 logits 还原 raw logits 后的 T=1）。原版 T 由 Kev 自家 dev 拟合、M10 未拟合，须在结果卡披露这是「随权重交付的校准」而非同源拟合。
- 配对比较：同一 (id, question) 上，按 join 的 `group_id`（declared group；无 group 的 item 自成簇）做 1,000 次 cluster bootstrap，95% 百分位 CI；固定 seed。三个 seed 各自与 original 比较，**不做多重比较校正**（逐比较 CI，并注明）。
- 变体：permuted 报 mean/max max-prob delta、flip rate、accuracy_unchanged_rate；isolation 同口径（与同 run 的 clean 记录配对）。
- 出口检查：聚合 JSON 若出现 item id / rid / group id 字符串即失败（`export_check`）；所有逐例产物（rows.json/predictions.jsonl/join.jsonl）只在仓库外临时目录。

## 5. 运行步骤（WSL）

```bash
# 0) 依赖：Kev 源码 ~/src/kev（commit 2074cc4），项目 venv ~/src/polgov/.venv
#    一次性：下载 Qwen3.5-4B-Base@1001bb4d… 与 jaredpalmer/kev-4b@v1.0 缓存；跑 pin_checkpoints.py 生成固定底座副本
#    不把 kev 安装进项目 venv：PYTHONPATH=~/src/kev 即可（依赖 pydantic/fastapi/uvicorn 已补装到 venv）
# 1) CPU/网络：准备评测端文件（仓库外），并打印聚合计数
bash benchmark/kev_prefix/prepare_eval.sh
# 1b) 固定底座 revision 的隔离副本（需 CPU torch；只需一次）
python benchmark/kev_prefix/pin_checkpoints.py --src-root <weights> --out-root <仓库外>/ckpt --seeds 43 17 29 --kev-hub jaredpalmer/kev-4b@v1.0
# 1c) 数据重叠审计（只输出计数）
python benchmark/kev_prefix/overlap_audit.py --holdout-items <仓库外>/items.jsonl --candidate <release>/data/mixed-training/kev-m10.jsonl --out <仓库外>/overlap-audit.json
# 2) GPU（仅在静默时段外、单卡、按 GPU 纪律）：
bash benchmark/kev_prefix/run_models.sh            # 或指定模型名
# 3) 聚合（run_models.sh 末尾已自动执行）：
python benchmark/kev_prefix/aggregate.py --join <仓库外>/join.jsonl \
  --run kev-original=<仓库外>/runs/kev-original --run seed43=<仓库外>/runs/seed43 \
  --reference kev-original --out <仓库外>/aggregate.json
# 4) 敏感性：Kev 训练上下文可入子集
python benchmark/kev_prefix/fit_training_context.py --join <仓库外>/join.jsonl \
  --out-rids <仓库外>/rids-training-context.txt --out-json <仓库外>/training-context-stats.json
# 5) CPU 延迟（公开 validation 子集，非私有）：
python benchmark/kev_prefix/cpu_latency.py --run jaredpalmer/kev-4b@v1.0 \
  --data <仓库外>/public-smoke.jsonl --out <仓库外>/cpu-latency-kev-original.json
# 6) 收尾：只保留聚合 JSON，删除私有临时副本
bash benchmark/kev_prefix/cleanup_private.sh --yes
```

`run_models.sh` 的 GPU 环境固定为：`KEV_DTYPE=bf16 KEV_BACKEND=torch KEV_MERGE=1 KEV_ATTN=eager KEV_CUDA_GRAPHS=0 KEV_FUSED=0`，并导出 `HSA_ENABLE_DXG_DETECTION=1`、`PYTORCH_ROCM_ARCH=gfx1100`。Kev 官方报告用 fp32 exact path；本机 20GB 卡用 bf16（须在结果卡注明，且两个模型同口径）。

## 6. JevBench 第二主表

- 第三方 JevBench（coherence，无 gold）用 `jevbench==0.1.0`（Apache-2.0，数据随包，可离线）对同一批 Kev 模型跑 `check` + `eval --suite jevbench-mini`，Kev 以 `kev.serve` 提供 `POST /v1/systemone`。
- **coherence ≠ accuracy**：coherence 可被「均匀回答」刷到 89.4（accuracy 39.8%），必须与 accuracy/校准并列读；本表只作外部一致性参照，不当作决策能力提升证据。
- 榜单/许可/提交要求与其它 Jev 类榜单见 [docs/reports/2026-10-27-jev-benchmarks.md](../../docs/reports/2026-10-27-jev-benchmarks.md)；不下载/不提交题目到仓库或数据集。

## 7. 文件与测试

| 文件 | 用途 |
|---|---|
| `convert.py` | items → Kev labelled requests；sidecar（rid/kind/num_options/overlong）|
| `build_suite.py` | 组装 suite + join；可选 permuted/isolation 变体 |
| `aggregate.py` | 聚合、分层、served/raw 校准、配对 cluster bootstrap、变体分析、出口检查 |
| `prepare_eval.sh` / `run_models.sh` / `cleanup_private.sh` | 评测端驱动（仓库外数据） |
| `fit_training_context.py` | 共同上下文（384/1024/2048）可入子集 + 长度分布（主口径） |
| `pin_checkpoints.py` | 隔离副本并把 base_revision 固定到训练 revision；记录前后 head/adapter sha |
| `overlap_audit.py` | 与 M10 训练/回放数据的精确重叠审计（只输出计数） |
| `verify_metrics.py` | 在同一 rows.json 上交叉核对 aggregate 与 kev.metrics 的指标差值 |
| `run_jevbench.sh` | JevBench（第三方 coherence）mini 跑分（kev.serve + jevbench） |
| `report_tables.py` | aggregate JSON → 结果卡 Markdown 表格（缺失显示 —） |
| `cpu_latency.py` | CPU 延迟（公开子集） |
| `test_*.py` | 纯合成样例单测（不含私有内容）；`python -m unittest discover -s benchmark/kev_prefix -p "test_*.py"` |

## 8. 已知限制

1. 本机 torch 2.9.1+rocm7.2.1 超出 Kev 声明范围（<2.9），仅实测 import/CPU 路径；GPU 路径以实际运行为准，失败则记录并降级/放弃，不静默替换。
2. bf16（GPU 服务/评测）与 Kev 官方 fp32 exact path 不同源；两模型同口径，但绝对值不可与官方榜直接比较。
3. M10 自带温度未拟合；`served` 校准对比受此影响，结果卡须同时给 `raw_t1` 并披露。
4. seed-43 为事后选择；seed17/29 保留全部结果，不删失败 seed。
5. Kev 表与我们 Qwen 线、JevBench coherence 与 accuracy 均分表。
6. 每次结果必须记录：Kev commit、base revision、checkpoint/release sha、suite manifest sha、环境（dtype/backend/device）、覆盖与拒绝计数、未测项。