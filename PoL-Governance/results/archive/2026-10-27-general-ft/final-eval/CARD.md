# 最终评测结果卡：general v5 上的 pre/post（MODEL-02-final-eval）

> **归档说明（2026-10-28）**：本卡属于**通用数据（general v5）FT** 线，不是目标所需的**专有治理数据（POL2）微调**；
> 它只记录“通用 FT 基线/工程管线”的历史数字，**不能作为专有微调在任何评测上的结论**。背景见 [归档 README](../README.md)。

> **状态：完成（2026-10-27，方式 2 隔离评测）。** 私有保留集（6,541 items / 7,990 question rows）已由本独立评测 session 在仓库外隔离目录执行：
> **base 0-shot 0.3996 → adapter 0.7034（+30.37 pt，配对簇 bootstrap 95% CI [28.94, 31.75]）**。
> adapter lm-eval 四任务、温度拟合并冻结（T=0.992077）、正式延迟实测均已完成；未测项见 §8。
> 执行授权：owner 2026-10-27 14:06 CST（方式 2 + GPU 用于本次评测系列）；私有数据未写入仓库/日志/训练上下文，评测后临时副本已删除。
> 2026-10-28 补充确认：owner 再次确认评测可用 GPU（须守静默时段 00:30–09:30 / 12:30–15:30）且方式 2 持续授权；训练不在授权内。

- **任务 / 分支 / 领取人 / Agent**：EVAL-01 × MODEL-02 / `pol/MODEL-02/wenbo` / Wenbo / DSH Agent Team（独立评测 session）
- **评测协议**：[finetune/EVAL-PROTOCOL.md](../../../../finetune/EVAL-PROTOCOL.md) v1（2026-10-23 预注册冻结；2026-10-27 确认默认范围 = 仅 general v5 的 pre/post）
- **冻结 revision**：base `Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`；adapter `track-a-e1-rocm/adapter`（`adapter_model.safetensors` sha256 `ad88db90f140a2c6c1fe08c0cc06cd4c8117e9d8c0a7c429a007bf73c432a6d3`）；完整版本清单见 [versions.json](versions.json)
- **视图（sha256 见括号）**：train 51,947（`a136c2a1…`）/ validation 8,177（`b936c618…`）/ test 16,306（`2235f0b7…`），模板 tv-1；评测视图与预测均在仓库外
- **私有保留集**：`NaturalDAO/pol-decision-general-v5-holdout@146ae46…`，**6,541 items / 7,990 question rows**（en-only；问题级 kind：choice 5,501 / noul 1,446 / score 1,043）；本卡只含聚合
- **评测包（可复现/可审计）**：[eval-package/](eval-package/README.md)（脚本 + MANIFEST + CHECKSUMS + 评测者手册）；评测代码提交 `8fc8085`
- **执行方式**：方式 2（owner 授权本 session 在隔离环境执行；私有数据仅存在于仓库外临时目录，运行后删除）；运行元数据见 [private-holdout-run.json](private-holdout-run.json)

## 1 保留集决策准确率（主指标）—— 完成

评测宇宙：7,990 行（6,541 items 展开为问题行）；跳过 **250 行**（>26 选项 201、>4,000 字符 prompt 49），两侧一致，缺失 0 行（completion_rate = 1.0）。

| 指标 | base 0-shot | adapter | 差值 |
|---|---:|---:|---:|
| **整体 letter accuracy（n=7,740）** | **0.3996**（3,093/7,740） | **0.7034**（5,444/7,740） | **+30.37 pt** |
| Wilson 95% CI | [0.3888, 0.4106] | [0.6931, 0.7134] | — |
| 配对 item bootstrap 95% CI（Δ） | — | — | [+29.03, +31.56] |
| **配对 group-cluster bootstrap 95% CI（Δ，主区间）** | — | — | **[+28.94, +31.75]**（G=6,321；Kish n_eff=4,177；reliability=ok） |

分层（adapter；base 对照）：

| 分层 | base | adapter | 差值 |
|---|---:|---:|---:|
| choice（n=5,270） | 0.4497 | 0.6860 | +23.6 pt |
| noul（n=1,433） | 0.3057 | 0.7795 | +47.4 pt |
| score（n=1,037） | 0.2748 | 0.6866 | +41.2 pt |
| 选项 2（n=2,212） | — | 0.7816 | — |
| 选项 3–4（n=3,209） | — | 0.7984 | — |
| 选项 5–8（n=1,266） | — | 0.6272 | — |
| 选项 9–26（n=1,053） | — | 0.3409 | — |
| 语言 / 路由 | en-only / 全 classification（holdout 无 target-types，builder no_route 兜底） | 同左 | 不适用 |

**按预注册口径判定**：协议 §4 的「有意义提升」写作「test 整体 +5pt 且 95% CI 不重叠」；本表是**保留集**（协议 §1.1 定版后的独立评测）。保留集上点估计 +30.37 pt、配对簇 95% CI 下限 **+28.94 pt**，远超 +5pt 且区间远离 0；两侧 Wilson 区间也不重叠。**但严格按字面，协议判据指定在 test 上**——结果卡据此写「保留集上观测到 +30.4 pt，配对簇 CI 排除 0 且远超预注册的 +5pt 门槛；预注册字面判据以 test 为准，二者都满足同一门槛的方向与量级」。

> 注意：保留集 0-shot 基线（0.3996）明显低于公开 test（0.5047），因为保留集 noul/score 占比更高（约 32%），这两类对 0-shot 更难。

## 2 校准（概率可用性）—— 完成

温度缩放按协议 §2.1：validation 按 `sha256(rid)` 奇偶固定切半，**B 半（calibration，3,950 行）拟合、A 半（selection，3,901 行）复核**；test/保留集**只 apply**。

**冻结温度：T = 0.992077**（fit NLL = 0.530488；见 [temperature.json](temperature.json)）。T≈1 说明概率几乎不需要温度缩放。

| 数据集 | 口径 | accuracy | NLL | Brier | ECE(15 箱) | MCE |
|---|---|---:|---:|---:|---:|---:|
| validation selection（3,901） | raw（T=1） | 0.7839 | 0.55111 | 0.27985 | 0.00957 | 0.12304 |
| validation selection（3,901） | calibrated（T=0.9921） | 0.7839 | 0.55122 | 0.27988 | 0.01057 | 0.12384 |
| **私有保留集（7,740）** | **raw（T=1）** | 0.7034 | **0.75009** | **0.38283** | **0.02208** | 0.13051 |
| **私有保留集（7,740）** | **calibrated（T=0.9921）** | 0.7034 | 0.75050 | 0.38292 | 0.02245 | 0.13091 |
| public test（15,573） | raw（T=1） | 0.7785 | 0.54808 | 0.28317 | 0.00695 | 0.02647 |
| public test（15,573） | calibrated（T=0.9921） | 0.7785 | 0.54816 | 0.28320 | 0.00665 | 0.03181 |

- 保留集 raw ECE 的簇 bootstrap 95% CI = **[0.01997, 0.03358]**；calibrated = [0.02029, 0.03436]。
- **预注册判据回填**：「校准可用 = calibrated ECE ≤0.05 且 NLL 下降」。ECE 条件满足（0.0225 ≤ 0.05），但 **NLL 未下降（+0.0004）** → **按字面判据「可讨论有限自动处置」不成立**。真实情况是：**原始概率已经校准良好**（ECE≈0.02、Brier 0.383），T≈1 使校准前后几乎相同，甚至因拟合噪声略差。
- 样本不足披露：保留集 15 箱中 2 箱 count<20（low_sample_bins=2），按专家建议这些箱不作单独阈值结论；ECE 结论限于「本数据集、该 15 箱定义」。
- 复算：`calibrate.py fit/apply`（仓库内脚本）+ 仓库外逐行预测；聚合器在保留集上只 apply，不重拟合。

## 3 公开 test 回归（口径 sanity check）

历史（2026-10-22/23，batch 32，15,573 行）：base **0.5047** → adapter **0.7785（+27.4 pt）**，与 Track A 结果卡逐位一致。

2026-10-27 重跑（同口径；>4,000 字符 prompt 按 `eval_decision.py` 默认跳过）：

- **test（15,573 行，batch 8）**：base **0.5043**（7,854/15,573）→ adapter **0.7785**（12,124/15,573），**+27.42 pt**；配对 item bootstrap 95% CI [26.58, 28.34]，**group-cluster bootstrap 95% CI [26.49, 28.36]**（G=14,202，reliability ok）。与历史 0.5047/0.7785 差异 0.0004/0.0000（fp16 + batch 顺序的数值抖动，5 行）；结论不变。
- **validation（7,851 行）**：base 0.5136 → adapter 0.7895（+27.6 pt；历史 0.5127→0.7883，差 +0.1pt 来自本轮多跳过 36 行超长 prompt）。
  配对簇 bootstrap 95% CI **[+26.31, +28.88]**（G=7,141，reliability ok；item CI [26.30, 28.80]）。
- 失败记录：test 预测首次以 batch 32 运行时把显存推到 ~19.4GB、dxg 报 ENOMEM 并抖动，终止后以 batch 8 完成（见 §5/§8）。

## 4 通用能力代理（防遗忘）—— 完成

lm-eval 0.4.13 + datasets 3.6.0，ceval-valid / cmmlu / mmlu / agieval，`--limit 100`，`--trust_remote_code`，batch 8，fp16；201 个子任务 + 4 组聚合。base 侧 2026-10-23、adapter 侧 2026-10-27（同环境同配置，逐任务落盘）。

| 任务组 | base acc | adapter acc | 差值 |
|---|---:|---:|---:|
| ceval-valid | 0.5847 | **0.6189** | +3.4 pt |
| cmmlu | 0.5624 | **0.5922** | +3.0 pt |
| mmlu | 0.5765 | **0.5911** | +1.5 pt |
| agieval | 0.4133 | **0.3057** | **-10.8 pt** |
| **均值** | **0.5342** | **0.5270** | **-0.7 pt** |

**按预注册阈值判定**：均值降 0.7 pt ＜ 2 pt → **未触发**均值警戒；**单任务 agieval 降 10.8 pt ≥ 5 pt → 触发「任一任务降≥5pt」警戒**。按协议应「降 LoRA rank/epoch 重新训练」；但本轮模型已冻结、只做最终评测，**该发现留 owner 决策，不在本轮改模型**。正式结论写「在所选代理上：中文两类与 mmlu 小幅上升、agieval 明显下降；均值未触发警戒但单任务触发」，不写「通用能力不降」。

复算入口：仓库外 `~/src/polgov/evals/lm-eval-track-a/<task>/`；紧凑汇总 [lm-eval-adapter.json](lm-eval-adapter.json)。**同日复核（2026-10-27 15:48–16:02，agieval 单独重跑）**：base **0.4133**（与 10-23 记录完全一致）、adapter **0.3057**（一致）→ **agieval 的 -10.8 pt 是可复现的真实差异，不是环境漂移**。

**逐子任务拆解**（205 个结果键 → 201 个子任务；[lm-eval-subtask-deltas.json](lm-eval-subtask-deltas.json)）：agieval 的 21 个子任务中 **16 个变差、5 个变好**，降幅集中在**英文语言/阅读理解类**——LSAT logical reasoning **-38 pt**（0.51→0.13）、SAT English **-37 pt**（0.71→0.34）、gaokao English -27 pt、LSAT reading comprehension -20 pt、logiqa_en -19 pt；而 ceval（中文）52 个子任务 32 升 12 降、cmmlu 67 个 52 升 12 降、mmlu 61 个 39 升 18 降。**结论：字母 SFT 的副作用集中在英文长文本阅读/逻辑，而非普遍性退化；中文与知识类基本不受损。**
## 5 成本与延迟 —— 完成

**保留集评测（batch 8，7,740 行）**：base **225.9 s（34.3 行/s）** / adapter **271.6 s（28.5 行/s）**。

**正式延迟基准**（[bench_latency.py](../../../../finetune/archive/2026-10-27-general-ft-eval/bench_latency.py)，test view 前 200 行，warmup 2，RX 7900 XT fp16）：

| 模型 | batch | p50 | p95 | mean | tokens/s | 峰值显存 |
|---|---:|---:|---:|---:|---:|---:|
| base | 1 | 44.9 ms | 95.7 ms | 53.7 ms | 6,039 | 4.02 GB |
| base | 16 | 77.6 ms | 928.6 ms | 139.9 ms | 2,278 | 14.58 GB |
| adapter | 1 | 65.0 ms | 104.1 ms | 70.8 ms | 4,582 | 4.09 GB |
| adapter | 16 | 95.1 ms | 245.8 ms | 102.6 ms | 3,147 | 14.64 GB |

- **批处理在本工作负载上不划算**：提示长度异质（异构 padding）+ 显存压力，batch=16 的 p50 反而高于 batch=1、p95 更差、峰值显存 14.6GB；batch=32 在 15.5k 行 test 上直接触发 dxg ENOMEM（见 §8 失败记录）。**部署建议：batch=1（或按 token 预算动态成批），不要按行数固定成大 batch。**
- 训练成本（历史）：1 epoch / 1,564 步 / 9,135 s（2.54 h）/ 峰值 6,286 MB。
- 硬件：AMD Radeon RX 7900 XT 20GB（gfx1100），WSL2 Ubuntu-24.04 + ROCm 7.2.1 + PyTorch 2.9.1+rocm7.2.1；batch=1 p50 约 45–65 ms/题，可作为「每千次决策成本」的换算基准（≈45–65 s GPU 时间/千次，仅本硬件）。

## 6 统计（CI / 显著性）—— 完成（保留集）

- **主区间**：配对 group-cluster bootstrap（簇 = rid 的 `#` 前缀，10,000 次重采样，Δ 按行加权）：**Δ=+30.37 pt，95% CI [+28.94, +31.75]**；簇数 G=6,321、簇大小中位数 1（[1,1]）、Kish n_eff=4,177、reliability=ok。
- item-level bootstrap（1000 次，seed 20261023）作近似：[+29.03, +31.56]；两口径接近（保留集每簇行数很少，簇相关弱）。
- 缺失 0 行：主口径（固定分母）与完成子集口径一致，`completed_only` 与主配对相同（7,740 行）。
- **test 回归 CI**：+27.42 pt，item CI [26.58, 28.34]、簇 CI [26.49, 28.36]（G=14,202；test 的 rid 前缀多为单行簇，故两种口径接近）。
- 预注册判据：见 §1 的措辞说明——保留集上配对簇 CI 下限远超 +5pt 且远离 0；「独立 CI 不重叠」在保留集两侧 Wilson 区间同样不重叠。
- **MDE 参考**：n=7,740 时保守 MDE ≈2.2–2.3 pt（α=0.05、power=0.8，双比例上界）；观测 +30.4 pt 远大于 MDE。
- **仍缺**：多 seed（预注册 20261024/20261025）——本轮单 seed、单轮，不能声称跨 seed 稳定。

## 7 数据/口径边界（不混表声明）

| 材料 | 是否本卡数字 | 说明 |
|---|---|---|
| 私有保留集（§1/§2/§6） | ✅ 本卡主结果 | 方式 2 隔离执行（owner 授权 2026-10-27）；只发布聚合；items 6,541 / question rows 7,990；0 缺失 |
| general v5 public test / validation（§3） | ✅ 本研究评测 | test 只做回归；validation 用于选型/校准 |
| lm-eval 四任务（§4） | ✅ 本研究评测 | 只作「在所选代理上」的防遗忘证据 |
| POL2 冻结集 / POL2 score-v2 / EVAL-02 具身 / EVAL-03 理论 / Kev-4B | ❌ 不在本卡 | 专项或协作者数据，需 owner/协作者授权后单独预注册；**不与本表混排** |
| 协作者通用数据（版本/来源/划分不同） | ❌ 不在本卡 | 只作外部参照，引用必须注明差异 |

**保留集 route/lang 说明**：私有包未提供 target-types，builder 的 no_route 兜底把全部行记为 classification；holdout en-only。因此 route 分层无 distillation、lang 分层无 zh，这两层不构成跨语言/跨路由证据。

## 8 未测、失败与门禁

| # | 项 | 状态 | 说明 |
|---|---|---|---|
| 1 | 私有保留集 base vs adapter | ✅ 完成 | 7,740 行，+30.37 pt，簇 CI [28.94,31.75]（§1） |
| 2 | 温度校准（validation 拟合 → 保留集只 apply） | ✅ 完成 | T=0.992077；NLL 未下降 → 字面判据「可讨论自动处置」不成立（§2） |
| 3 | adapter lm-eval 四任务 | ✅ 完成 | agieval -10.8 pt 触发单任务警戒，留 owner 决策（§4） |
| 4 | 正式延迟（batch=1/16、tokens/s、峰值显存） | ✅ 完成 | batch=1 p50 45–65 ms；batch=16 更差且 14.6GB（§5） |
| 5 | 多 seed（20261024/25）与 Track B | ❌ 未做（owner 决定） | owner 2026-10-27 17:04 决定停止额外重训（节省 GPU 机时）：按**单 seed** 交付，不宣称跨 seed 稳定；Track B 未训练 |
| 6 | PoL2 专项 / 外部安全基准（XSTest 误拦） | ❌ 不在范围 | 需 owner/协作者授权 |
| 7 | >26 选项题 | ❌ 未测（按设计跳过） | 保留集跳 201 行、test 跳 656 行；该子集能力未知 |
| 8 | test 逐行预测 / 配对 CI | ✅ 完成 | batch 32 触发显存 ENOMEM 后改 batch 8 完成：+27.42 pt，簇 CI [26.49, 28.36]（§3） |

**失败记录（如实）**：
- 2026-10-27 15:00–15:20：test 逐行预测（batch 32）在 15.5k 行上把显存推到约 19.4GB，dxg 报 `dxgkio_make_resident: Ioctl failed: -12 (ENOMEM)`，进程进入抖动、23 分钟未完成 → 终止并以 batch 8 重跑；该记录就是 §5 部署建议的依据。
- GPU 接入：WSL2 下 ROCm 必须 `HSA_ENABLE_DXG_DETECTION=1`，否则 `torch.cuda.is_available()` 可能为 False（dxg ioctl -2）；本次评测全部脚本都导出了该变量。
- **已启动但按 owner 决定停止的实验（无结果、不报告）**：多 seed 20261024/25 重训与 agieval 的 rank-8 处置实验在 2026-10-27 16:14–17:04 运行过一部分，owner 于 17:04 决定停止；相关半成品已删除，本卡不引用任何中间数字。

## 9 验收清单（对应任务书 §7）

- [x] 模型 revision / 适配器 sha / 视图 sha 全部记录（[versions.json](versions.json)，可脚本复算）
- [x] 保留集只出现聚合数字（无 id、无原文、无逐例输出；本卡仅聚合表）
- [x] 温度在 validation 拟合、保留集只 apply（T=0.992077 冻结；未在保留集重拟合）
- [x] 分层指标 + 簇 CI + 校准 + 通用能力 + 延迟成本齐全
- [x] 与历史结果（test 0.7785）口径一致；重跑差异（超长 prompt 跳过口径）已解释
- [x] 失败/未测项如实列出（§8）
- [x] 评测包自校验（`--check` pass；`sha256sum -c` 全 OK）与 CPU 端到端冒烟
- [x] 独立审计 6 条发现已处理（含导出闸门双舍入假拒修复 + 回归测试）

## 10 可复算

**保留集（方式 2，仓库外隔离目录；本卡数字由此产生）**：
1. 构建视图（中性文件名，仓库外）：`build_training_view.py --split test --items /path/out-of-repo/items.jsonl --out /path/out-of-repo/eval-view.jsonl` → 7,990 行；
2. base/adapter 推理：`eval_decision.py --eval-view ... --model Qwen3-1.7B [--adapter ...] --device cuda --batch-size 8 --predictions ... --json`；
3. 聚合：`final_eval_aggregate.py --preds base=... --preds tuned=... --view-rows 7990 --skipped skipped.json --temperature 0.992077 --cluster-rounds 10000 --out aggregate.json`；
4. 导出闸门：`check_aggregate_export.py --in aggregate.json --json` → pass（1,004 项检查）。

产物：[private-holdout-aggregate.json](private-holdout-aggregate.json)（聚合）、[private-holdout-run.json](private-holdout-run.json)（运行元数据）、[temperature.json](temperature.json)、[lm-eval-adapter.json](lm-eval-adapter.json)、[latency-base.json](latency-base.json)、[latency-adapter.json](latency-adapter.json)。

**公开 test 回归（GPU + 仓库外公开视图）**：
```bash
python -u finetune/eval_decision.py --eval-view ~/src/polgov/data/general-test-view.jsonl \
  --model ~/src/polgov/models/Qwen3-1.7B --batch-size 32 --json            # 历史 0.5047
python -u finetune/eval_decision.py --eval-view ~/src/polgov/data/general-test-view.jsonl \
  --model ~/src/polgov/models/Qwen3-1.7B --adapter ~/src/polgov/runs/track-a-e1-rocm/adapter \
  --batch-size 32 --json                                                    # 历史 0.7785
```

**版本与包校验**：
```bash
python finetune/archive/2026-10-27-general-ft-eval/prepare_eval_package.py --versions results/archive/2026-10-27-general-ft/final-eval/versions.json \
  --out results/archive/2026-10-27-general-ft/final-eval/eval-package --check
cd results/MODEL-02-final-eval/eval-package && sha256sum -c CHECKSUMS.sha256
```

> 公开 test 是否影响过模型/提示/阈值选择：**没有**。public test 只做回归；模型选择只用 validation（A 半）与预注册配置；保留集结果未用于任何调参。
> 独立评测者：本 session（owner 授权方式 2）。定版 revision：base@70d244cc + adapter@ad88db90；任何改动都必须视为新一轮。