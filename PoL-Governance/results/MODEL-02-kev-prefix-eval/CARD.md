# 结果卡：Kev 前后对照（原版 Kev-4B vs POL2 score-v2 M10）+ JevBench coherence

> 最终单页报告（唯一版本）：[2026-10-28-kev-prefix-eval.html](../../docs/reports/2026-10-28-kev-prefix-eval.html)（单文件自包含，内嵌 22 张图，无外部依赖）。

- 任务 / 分支 / 领取人 / Agent：Session B 独立评测（`.agent/prompts/SESSION-B-final-eval.md`）/ `pol/MODEL-02/wenbo` / lead（独立评测 Agent，未参与训练）
- 日期 / 执行方式：2026-10-28；私有保留集**方式 2（本机隔离执行）**；只回传聚合，评测后删除临时副本
- 模型与底座 revision / 方法：见 §2；**不训练、不改模型/数据、不为保留集调 prompt/阈值**
- 数据版本 / 划分 / 校准方法：general v5 私有保留视图（6,541 items / 7,990 questions）；共同支持上下文（state 384 / branch 1024 / packed 2048 tokens）主口径；温度**不重拟合**，served 与 raw T=1 并报
- 对照组 / 硬件 / 精度 / 预算：RX 7900 XT 20GB（WSL2 ROCm 7.2.1）/ bf16 / 单卡串行；GPU 静默时段外（15:30 起）
- 可复现命令 / 配置：`benchmark/kev_prefix/README.md`、`run-config.json`、`versions.json`；聚合文件见本目录
- 结论边界：只描述本冻结视图/转换/配置下的观察性配对比较；seed43 属**事后选择**的探索性比较；JevBench 为第三方 coherence，不是 accuracy

> 一句话：在共同有效上下文与 bf16/GPU 配置下，**seed43 的决策准确率略高（+0.95 pt，95% CI [+0.30,+1.65]）但概率校准显著变差**（ECE10 0.0247→0.2081，Brier/NLL 更大，5% 错误预算下可自动处置份额更低）；seed17 仅 +0.60 pt（CI 跨 0）、seed29 持平。JevBench coherence 上 seed43 **+8.7 分**（第三方、coherence≠accuracy）。没有证据支持「M10 整体更好」；准确率的微小增益属事后选择的探索性结果，部署级自动处置没有改善。

## 1. 数据覆盖表（只发布聚合）

| 项 | 数值 | 说明 |
|---|---:|---|
| 私有保留集 items / questions | 6,541 / 7,990 | en-only；choice 5,501 / noul 1,446 / score 1,043（问题级） |
| 可映射（转换失败=0） | 6,541 / 7,990 | 无 target/答案越界/noul 歧义均 0 |
| overlong（>4,000 chars，view 规则标记） | 53 题 | 不删记录，仅在 sidecar 标记；主表排除 |
| 组装 suite 记录（含变体） | 9,070 | clean 6,541 + permuted 600 + isolation 1,929 |
| 本机不可评测（row > 2,048 tokens） | 5 clean records / 14 题 + 13 isolation | 20GB 卡 + exact eager 路径放不下 L×L attention（首轮实测 HIP OOM，见 §9）；**单列，不做静默截断** |
| 评测 suite（screened） | 9,052 记录（clean 6,536 / permuted 600 / isolation 1,916） | suite manifest sha256 `4f0e56c1…`（本次重跑；manifest 含构建时间戳，故每次重建的哈希不同） |
| **主口径：共同支持上下文** | **6,299 records / 7,347 questions** | 原版训练 384/1024/2048；M10 训练 max_state=4096；共同范围取 384/1024/2048（= Kev 官方 suite CONTEXT） |
| ├ 整条拒绝 | 242 records / 643 questions | state 228 / branch 14；按 strict encode 整条拒绝（不是逐题裁剪） |
| └ overlong（主口径内） | 43 题 | view 规则排除 |
| serving 敏感性 | 7,933 题（排除 overlong）/ 7,976 题（全量） | 只作敏感性；不改变主表 |
| 长度分布（主口径 state tokens） | p50 74 / p90 165 / p99 329 / max 383 | 全部 ≤384 |
| 长度分布（serving 全量） | p50 87 / p90 354 / p99 1,113 / max 5,712 | |
| 共同配对 n / cluster 数 | 7,347 / 6,299 | cluster = record（declared group 合并），配对 (id, question) |
| 数据重叠审计（vs M10 训练数据） | **精确 state/question/id 重叠 0** | mixed kev-m10 6,827 行、MRI replay m10/validation/guard；模糊/语义重叠未审计 |
| 运行失败 | 首轮 full-suite 1 次 HIP OOM（见 §9）；重跑 0 失败 | 4 个 checkpoint × 9,052 记录，全部 rejected_records=0 |

## 2. 模型版本表

| 角色 | 权重 / revision | 温度 | 头/适配器 sha256 | 备注 |
|---|---|---|---:|---|
| 原版 Kev | `jaredpalmer/kev-4b@v1.0`，Hub commit `6cfce5c2fa4b` | 2.406（Kev 自家 dev 拟合） | head `dd633435…` / adapter `90e817356…` | 与 M10 训练 init_source 的 head/weights sha 完全一致 |
| 微调（主） | seed-43，GitHub Release `pol2-score-v2-v1.0.0` | 1.0（未拟合） | 固定底座后 head `42cd433a…` / adapter `c05a982e…` | head.pt 的 base_revision 由 null 固定为 `1001bb4d…`（断言张量不变；前后 sha 记于 versions.json） |
| 微调（变体） | seed-17 | 1.0 | head `bdcd9943…` / adapter `d43511fc…` | 同上 |
| 微调（变体） | seed-29 | 1.0 | head `1d51f95f…` / adapter `93ab8136…` | 同上 |
| 共同底座 | `Qwen/Qwen3.5-4B-Base@1001bb4d826a52d1f399e183466143f4da7b741b` | — | — | 原版 head.pt 自带同一 revision；seed 由 null 固定 |
| Kev 代码 | commit `2074cc44` | — | — | 无 flash-linear-attention / causal-conv1d（参考实现） |

- 训练侧（协作者提供，不在本 session 执行）：Qwen3.5-4B-Base + LoRA r=16/α=32 + pointer head（hidden 256），1 epoch，bf16 backbone / fp32 head，batch 1 / accum 4，lr 2e-5，max_state 4096，训练数据 6,827 units（POL2 score-v2 专家规则数据 6,166 + MRI general replay 661，MIT），硬件 NVIDIA GB10。
- **选择后披露**：seed43 是在查看 seed17/29/43 全部既有结果后选作默认推荐版本；其在本卡的结果属**选择后探索性估计**，CI 不含训练 seed 变异，不作方法级确认性证据。seed17/29 同口径完整呈现；三 seed **不是 ensemble**。

## 3. 主决策表（served，主口径 n=7,347，cluster=6,299）

| run | acc [95% CI] | brier | nll | ece_10 | ece_15 | coverage@5%err [95% CI] | aurc |
|---|---:|---:|---:|---:|---:|---:|---:|
| kev-original | **0.6414** [0.6298, 0.6527] | **0.4773** | **0.9945** | **0.0247** | **0.0227** | **0.1805** [0.1543, 0.2113] | 0.1694 |
| seed43 | **0.6509** [0.6404, 0.6615] | 0.5500 | 1.6971 | 0.2081 | 0.2094 | 0.1424 [0.1069, 0.1854] | 0.1743 |
| seed17 | 0.6473 [0.6367, 0.6583] | 0.5500 | 1.6572 | 0.2153 | 0.2168 | 0.1725 [0.1026, 0.1935] | 0.1699 |
| seed29 | 0.6411 [0.6303, 0.6521] | 0.5558 | 1.6465 | 0.2115 | 0.2116 | 0.1460 [0.1167, 0.1762] | 0.1762 |

配对差（模型 − 原版；cluster percentile bootstrap，1,000 次，seed=0）：

| comparison | Δacc [95% CI] | Δnll | Δbrier | Δece_10 |
|---|---|---:|---:|---:|
| seed43 − original | **+0.0095** [+0.0030, +0.0165] | +0.7026 | +0.0728 | +0.1835 |
| seed17 − original | +0.0060 [−0.0011, +0.0131] | +0.6627 | +0.0727 | +0.1907 |
| seed29 − original | −0.0003 [−0.0077, +0.0065] | +0.6519 | +0.0785 | +0.1868 |

分层（served，节选；完整表见 aggregate-primary.json 的 by_* 字段）：

| 层 | n | original acc | seed43 acc | original ece_15 | seed43 ece_15 |
|---|---:|---:|---:|---:|---:|
| choice | 5,194 | 0.6259 | **0.6583** | 0.0185 | 0.2092 |
| noul | 1,221 | **0.7707** | 0.7174 | 0.0790 | 0.1907 |
| score | 932 | **0.5579** | 0.5225 | 0.0849 | 0.2505 |
| decision_mechanics | 3,257 | **0.5972** | 0.5874 | 0.0375 | 0.2772 |
| knowledge_reasoning | 4,090 | 0.6765 | **0.7015** | 0.0382 | 0.1565 |
| 选项 2 | 1,982 | **0.7694** | 0.7407 | 0.0522 | 0.1812 |
| 选项 3–4 | 3,085 | 0.7037 | **0.7455** | 0.0251 | 0.1553 |
| 选项 5–8 | 1,152 | **0.5868** | 0.5694 | 0.0996 | 0.1714 |
| 选项 9–26 | 967 | 0.3020 | 0.3113 | 0.1836 | 0.5281 |
| 选项 >26 | 161 | 0.2981 | 0.3540 | 0.2311 | 0.1035 |

serving 敏感性（不改变主结论）：extended n=7,933：acc original 0.6453 / seed43 0.6557（Δ **+0.0105** [+0.0038,+0.0177]）/ seed17 0.6523（+0.0071）/ seed29 0.6460（+0.0008）；full n=7,976 同向（+0.0105 / +0.0074 / +0.0011）。

## 4. 校准 / 风险表

| run | mode | n | mean_conf | confident_error_rate (p≥0.9 且错) | coverage@5% | ece_10 | ece_15 |
|---|---|---:|---:|---:|---:|---:|---:|
| kev-original | served (T=2.406) | 7,347 | 0.6288 | **0.0069** | 0.1805 | **0.0247** | **0.0227** |
| kev-original | raw_t1 | 7,347 | 0.7913 | 0.0859 | 0.1809 | 0.1542 | 0.1553 |
| seed43 | served (T=1.0) | 7,347 | 0.8589 | **0.1371** | 0.1424 | 0.2081 | 0.2094 |
| seed17 | served | 7,347 | 0.8623 | 0.1338 | 0.1725 | 0.2153 | 0.2168 |
| seed29 | served | 7,347 | 0.8522 | 0.1341 | 0.1460 | 0.2115 | 0.2116 |

- raw_t1 下（两模型都还原到 T=1）：original brier 0.5238 / nll 1.3313；seed43 brier 0.5500 / nll 1.6971 → **即使统一到 T=1，seed43 的概率仍更差**（不是说它的「校准温度缺失」造成了全部差距）。
- 温度来源不对称：original 的 2.406 是 Kev 在自家 dev 上拟合并随权重发布；M10 head.pt 记录 T=1.0（未拟合）。按任务书**不在保留集重拟合**；served 对比是「随权重交付配置」，不是公平的校准能力因果估计。
- coverage@5% 是**本样本上的经验风险-覆盖**（含接受集 n 与错误率），不是真实部署错误上界；温度来源不对称，不能据此宣称安全自动处置。
- score 题：original MAE 0.6932 / RPS 0.1450；seed43 0.7625 / 0.1732（raw_t1 同值）。

## 5. 鲁棒性表（变体，探索性）

| run | variant | n_pairs | mean_max_delta [95% CI] | max_max_delta | flip_rate [95% CI] | accuracy_unchanged_rate |
|---|---|---:|---:|---:|---:|---:|
| kev-original | permuted | 600 | **0.0606** [0.0560, 0.0655] | 0.4223 | **0.1017** [0.0769, 0.1250] | 0.4950 |
| seed43 | permuted | 600 | 0.1025 | 0.8984 | 0.1133 | 0.4817 |
| seed17 | permuted | 600 | 0.0996 | 0.9059 | 0.1117 | 0.4667 |
| seed29 | permuted | 600 | 0.0927 | 0.9381 | 0.1067 | 0.4650 |
| kev-original | isolation | 1,916 | 0.0025 | 0.0527 | 0.0021 | 0.9984 |
| seed43 | isolation | 1,916 | 0.0030 | 0.1519 | 0.0052 | 0.9958 |
| seed17 | isolation | 1,916 | 0.0035 | 0.1448 | 0.0031 | 0.9969 |
| seed29 | isolation | 1,916 | 0.0032 | 0.1457 | 0.0037 | 0.9963 |

- permuted：按 sha256 确定性抽取 600 道 choice 题（不看标签/结果），选项顺序打乱。**M10 三个 seed 的选项顺序敏感度略高于原版**（mean_max_delta 0.093–0.103 vs 0.061；flip 10.7–11.3% vs 10.2%），accuracy_unchanged 略低。
- isolation：packed（一次请求多题）vs 单独提问，所有模型几乎无差（mean delta ≤0.0035，flip ≤0.6%）；问题隔离本身不是退化的来源。

## 6. 运行成本表

| 项 | 值 |
|---|---|
| GPU | AMD Radeon RX 7900 XT 20GB（WSL2 Ubuntu-24.04，ROCm 7.2.1） |
| 软件 | torch 2.9.1+rocm7.2.1（**超出 Kev 声明 `torch<2.9`，披露**）、transformers 5.20.2、peft 0.21.2、triton 3.5.1+rocm；无 FLA / causal-conv1d |
| 精度 / 后端 | bf16、backend=torch、merge=1、attn=eager、cuda_graphs=0、fused=0；`HSA_ENABLE_DXG_DETECTION=1` |
| GPU 单记录延迟（median / p95，9,052 记录） | original 83.8 / 361.8 ms；seed43 77.7 / 360.1 ms；seed17 82.6 / 343.0 ms；seed29 78.6 / 353.9 ms（同配置重跑；延迟随系统负载波动，±5 ms 内不具区分意义） |
| 每 checkpoint 总时长 | 约 16–17 min（9,052 记录；含加载与评测） |
| CPU 旁表（公开 validation smoke 43 条，Ryzen 5700X，fp32） | original p50 6,627 ms / p95 20,933 ms / ~41 tokens/s；seed43 p50 5,722 ms / p95 18,904 ms / ~46 tokens/s（**仅 smoke，不作部署基准**） |
| 显存峰值 | **未测**（WSL 无 amdgpu 模块；仅据 OOM 行为推断 attention 缓冲约为限制因素） |

## 7. JevBench（第三方 coherence，独立表）

- 第三方基准：JevBench（Chen Feng, ML Lab, Queen's University Belfast；非 TypeSafe）。`jevbench==0.1.0`（Apache-2.0，数据随包，可离线），suite `jevbench-mini` v1（240 cases / 50 relations / 1,200 tests / 1,248 requests），运行日期 2026-10-28。
- 服务配置：`kev.serve` + `POST /v1/systemone`，GPU bf16、merge=1、eager；每模型全新 `--cache-dir` 并用 serve 日志 POST 计数复核（各 1,442 次 POST，确认真实打到对应模型）。
- 结果（overall 为 0–1 分数，×100 与榜单对齐）：

| model | overall [95% CI] | REP | BAT | MEA | LOG | CHO | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| kev-original | **72.19** [70.16, 74.17] | 0.7472 | 1.0000 | 0.3039 | 0.6833 | **0.8750** | —（第三方 0.1.0 不含 accuracy；官方榜 Kev-4B acc 87.9%） |
| seed43 | **80.91** [78.66, 83.15] | 0.8083 | 1.0000 | 0.5662 | 0.8792 | 0.7917 | — |
| Δ (seed43 − original) | **+0.0872** | +0.0611 | 0.0000 | +0.2623 | +0.1958 | −0.0833 | — |

- 外部参照：官方 leaderboard（读取于 2026-10-28）Kev-4B overall **71.9**、acc 87.9%、名次区间 9–15；我们复现原版 72.19（差 0.3 分，配置差异：bf16 vs 官方 fp32、ROCm/不同服务实现）。
- **coherence ≠ accuracy**：JevBench 可被「均匀回答」刷到 89.4（accuracy 39.8%）；本表**没有** accuracy 列（需第三方 gold，本 session 未取），不能据此说模型更准。seed43 的 +8.7 只说明该第三方一致性指标上更好，需与 §3 的 general v5 结果并读（那里 seed43 校准更差）。
- 未提交 leaderboard（无公开提交入口；需作者邮件 + 公开权重/复现脚本）。对外表述：reproduced locally, not listed。

## 8. 榜单调研

见 [docs/reports/2026-10-27-jev-benchmarks.md](../../docs/reports/2026-10-27-jev-benchmarks.md)：JevBench（coherence，唯一明确榜单）、同名 leanmcp JevBench（accuracy 型，不可混）、Kev suites / Decision Index、TypeSafe Jev、OpenJev、Laya、OpenDecider、System One Bench；含许可/访问/可收集性。本 session 未下载/入库任何题目数据。

## 9. 失败、未测与限制

**运行失败（如实记录）**

1. **首轮 full-suite 在 `holdout/6056` 处 HIP OOM**：`torch.OutOfMemoryError: HIP out of memory. Tried to allocate 4.01 GiB`（eager attention 的 L×L 缓冲；该记录 row=4,733 tokens）。处置：`screen_suite.py` 按本机可执行性筛掉 5 条 clean（14 题，row 2,132–5,828）与 13 条 isolation 变体（**单列、不静默裁剪**），重跑 4 个 checkpoint 全成功、rejected=0。Kev 官方行为（exact eager path）不变。
2. **JevBench 请求缓存陷阱**：jevbench 0.1.0 的请求缓存按 URL+请求内容做键，不区分 serve 的 checkpoint；单独 `--no-cache` 实测仍复用旧响应（两次重跑 seed43 与 original 分数逐位相同，serve 日志仅 1 次 POST）。处置：每模型全新 `--cache-dir` + serve 日志 POST 计数断言（各 1,442）后重跑；本卡为修正后的结果。

**未测 / 不可测**

- GPU 显存峰值、GPU 温度（WSL 无 amdgpu 模块）；JevBench accuracy（需第三方 gold）；Kev 官方 suite（breadth-v1 等）复现（部分分区在私有镜像）。
- 超出共同上下文的长文档：主表按预注册规则排除（242 records/643 questions + view 规则 43 题），serving 敏感性覆盖到 row≤2,048；更长的 5 条 clean 记录本机不可评测。
- 模糊/语义层面的训练数据重叠：只做了精确 state/question/id 审计（结果 0），未做 n-gram/嵌入层面的污染审计。

**限制**

- bf16 评测与 Kev 官方 fp32 exact path 不同源；两模型同口径，但绝对值不可与官方榜直接比较。
- 原版温度由 Kev 自家 dev 拟合、M10 温度未拟合 → served 校准/automation 对比不对称（raw_t1 已并报）。
- seed43 事后选择（探索性）；三 seed 非 ensemble；CI 不含训练随机性。
- 本机依赖版本越界（torch 2.9.1 vs `<2.9`），已记录 environment；GPU 路径实测可用。
- M10 训练数据（POL2 score-v2 + MRI replay）与本保留视图精确重叠 0，但不能由此声称独立泛化或方法有效。

## 10. 验收与边界

- [x] 原版与三个 seed 在同一 suite（同一 manifest sha）、同一转换、同一 Kev commit、同一环境配置下跑通（rejected=0）
- [x] seed17/29 完整保留；seed43 事后选择已披露；per-seed 不称 ensemble
- [x] 私有保留集只出现聚合数字（本目录 JSON 均为聚合；无 id/原文/逐例；逐例 rows/predictions 仅在仓库外临时目录，评测后删除）
- [x] accuracy/Brier/ECE(10+15)/automation/option-order/isolation 齐全；配对 cluster CI 与样本量齐备
- [x] JevBench 注明第三方、coherence≠accuracy，与 leaderboard 对比注明配置差异
- [x] 榜单表含规模/许可/访问/能否收集；本 session 未擅自下载题目入仓
- [x] 失败/未测项如实列出（OOM 与缓存陷阱）
- [x] 公开 test 未影响模型/prompt/阈值选择（本 session 未使用公开 test 做任何选择）
- [x] `python tools/check.py`：**pass（exit 0；831 tests OK + 29 tests OK/skip 3，2026-10-28）**


**允许的结论**：在本次冻结的 general v5 专项评测、共同有效上下文（384/1024/2048）与 bf16/GPU 配置下，seed43 的配对准确率差 +0.95 pt（95% CI [+0.30,+1.65]），但其 Brier/NLL/ECE 显著更差、5% 错误预算下可自动处置份额更低；seed43 属事后选择，结果为探索性。原版在这份切片上校准显著更好。
**禁止的结论**：M10 方法普遍更好/更聪明；微调已证明有效或无效（无等效/确认性设计）；安全自动裁决；减少现实伤害；跨人群泛化；JevBench 准确率；保留集阈值已验证。

## 11. 复现

见 [benchmark/kev_prefix/README.md](../../benchmark/kev_prefix/README.md)；摘要：

```bash
bash benchmark/kev_prefix/prepare_eval.sh                          # 转换 + suite（仓库外）
python benchmark/kev_prefix/pin_checkpoints.py ...                # 固定底座 revision 的隔离副本
python benchmark/kev_prefix/overlap_audit.py ...                  # 数据重叠审计（只出计数）
python benchmark/kev_prefix/screen_suite.py ... --max-row-tokens 2048   # 20GB 卡可执行性筛查
bash benchmark/kev_prefix/run_models.sh                           # GPU：4 checkpoint + 3 次聚合
bash benchmark/kev_prefix/analyze.sh                              # 交叉核对 + 表 + summary
bash benchmark/kev_prefix/run_jevbench.sh kev-original seed43      # JevBench（GPU serve）
python benchmark/kev_prefix/jevbench_summary.py ...               # 第三方表
python tools/check.py
bash benchmark/kev_prefix/cleanup_private.sh --yes                # 删除私有临时副本
```

文件：`aggregate-primary.json`（主口径）、`aggregate-extended.json` / `aggregate-full.json`（serving 敏感性）、`screening-report.json`、`training-context-stats.json`、`versions.json`、`run-config.json`、`jev-summary.json`、`cpu-latency-*.json`、`overlap-audit.json`。