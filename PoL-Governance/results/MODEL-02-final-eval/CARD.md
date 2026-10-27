# 最终评测结果卡：general v5 上的 pre/post（MODEL-02-final-eval）

> **状态：部分完成（2026-10-27）——诚实版。** 公开 test 回归、validation、lm-eval base 已入卡；
> **私有保留集评测未执行、adapter 侧 lm-eval 未测、温度校准未拟合、正式延迟基准未测**。
> 执行链（评测包 + 聚合 + 导出闸门 + 延迟脚本）已交付并通过 CPU 端到端冒烟；每一项未测都写进 [§8 未测与门禁](#8-未测失败与门禁)，不填 0、不省略。

- **任务 / 分支 / 领取人 / Agent**：EVAL-01 × MODEL-02 / `pol/MODEL-02/wenbo` / Wenbo / DSH Agent Team
- **评测协议**：[finetune/EVAL-PROTOCOL.md](../../finetune/EVAL-PROTOCOL.md) v1（2026-10-23 预注册冻结；2026-10-27 确认默认范围 = 仅 general v5 的 pre/post）
- **冻结 revision**：base `Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`；adapter `track-a-e1-rocm/adapter`（`adapter_model.safetensors` sha256 `ad88db90f140a2c6c1fe08c0cc06cd4c8117e9d8c0a7c429a007bf73c432a6d3`）；完整版本清单见 [versions.json](versions.json)
- **视图（sha256 见括号）**：train 51,947（`a136c2a1…`）/ validation 8,177（`b936c618…`）/ test 16,306（`2235f0b7…`），模板 tv-1；视图文件在仓库外
- **私有保留集**：`NaturalDAO/pol-decision-general-v5-holdout@146ae460…`，6,541 条，库外独立保管；**本卡不含任何保留集内容/逐例结果**
- **评测包（可交给独立评测者执行）**：[eval-package/](eval-package/README.md)（脚本 + MANIFEST + CHECKSUMS + 运行手册）；代码提交 `8fc8085`（MANIFEST.git_commit 同值），本卡随 `2057d1e` 落库

## 1 保留集决策准确率（主指标）—— 未测

| 指标 | base 0-shot | adapter | 差值 |
|---|---:|---:|---:|
| 整体 letter accuracy（6,541 条，待评测） | 未测 | 未测 | 未测 |
| 分层 kind / lang / 选项数桶 / route | 未测 | 未测 | 未测 |
| 缺失/失败行（计入分母） | 未测 | 未测 | 未测 |

**门禁**：①owner 决定执行方式（方式 1 独立评测者 / 方式 2 授权我们在隔离环境执行；任务书 §5，内部文档 `.agent/prompts/SESSION-B-final-eval.md`）；②GPU 恢复后补 adapter lm-eval 与温度拟合；③按 [eval-package/README.md](eval-package/README.md) 运行并只带回 `aggregate.json`（先过 `check_aggregate_export`）。
**在门禁通过前，任何「保留集提升 X pt」的表述都不成立。**

**统计口径（已按独立咨询预置）**：
- 主区间 = **配对 group-cluster bootstrap**（簇 = rid 的 `#` 前缀；10,000 次重采样；Δ 按行加权；同时报簇数 G 与 reliability 分级）；item-level bootstrap 只作近似，**不得**用更窄的 item 区间替代；
- 预注册判据仍是「两独立 95% CI 不重叠」，**不得事后**换成「配对 Δ CI 不含 0」并宣称通过；若配对显著但预注册门槛未满足，只能写「配对分析显示正向差异；预注册门槛未满足」；
- 缺失/失败行：主口径为固定分母（失败记错误），同时披露各模型完成率与失败类型；双方均完成子集只作敏感性分析。

## 2 校准（概率可用性）—— 未拟合

温度缩放按协议 §2.1：validation 按 `sha256(rid)` 奇偶固定切半（B 半拟合、A 半复核），test 与保留集**只 apply**。

| 指标 | raw（T=1） | calibrated（T 待拟合） |
|---|---:|---:|
| NLL / Brier / ECE / MCE（validation） | 未测 | 未测 |
| NLL / Brier / ECE / MCE（保留集） | 未测 | 未测 |

**门禁**：需要 adapter 的**逐行预测**（含 `candidate_probs`）——`finetune/eval_decision.py --predictions`（GPU，约 5–10 分钟）。得到后：`calibrate.py fit`（B 半）→ `temperature.json` 冻结进本轮评测包 → 保留集只 `apply`。

**结论边界（预置）**：calibrated ECE ≤0.05 只能写「本评测集、该 15 箱定义下观测到校准误差低于阈值」，**不能**据此授权自动处置；15 箱 ECE 有有限样本偏差，单箱 <20 或分层 <200 例时标「样本不足」、不作该层阈值结论。报告须含每箱 n、（校准前后）置信度/准确率、Brier/NLL 及其簇 bootstrap CI，不得挑指标。

## 3 公开 test 回归（口径 sanity check）—— 完成

16,306 行视图，评测 15,573 行（跳过 >26 选项 656 行、超长 prompt 77 行，base 与 adapter 同口径）；**只做回归，不用于选型**。

| 分层 | 0-shot 基线 | LoRA adapter | 差值 |
|---|---:|---:|---:|
| **整体准确率** | **0.5047**（7,859/15,573） | **0.7785**（12,124/15,573） | **+27.4 pt** |
| choice | 0.5283（13,548） | 0.7780 | +25.0 pt |
| noul | 0.4075（1,097） | 0.8450 | +43.8 pt |
| score | 0.2748（928） | 0.7069 | +43.2 pt |
| en | 0.4490（13,824） | 0.7514 | +30.2 pt |
| zh | 0.9445（1,749） | 0.9931 | +4.9 pt（天花板/位置先验，不作能力证据） |
| 选项 2 | 0.4866（3,163） | 0.8277 | +34.1 pt |
| 选项 3–4 | 0.6027（9,157） | 0.8484 | +24.6 pt |
| 选项 5–8 | 0.2888（2,282） | 0.6100 | +32.1 pt |
| 选项 9–26 | 0.1462（971） | 0.3553 | +20.9 pt |
| classification | 0.5080（14,294） | 0.7858 | +27.8 pt |
| distillation | 0.4676（1,279） | 0.6974 | +23.0 pt |

与历史结果（Track A 结果卡 0.7785）**逐位一致**——口径 sanity check 通过。

> 口径说明：本表数字来自**已落盘的评测结果 JSON**（仓库外 `~/src/polgov/evals/{base,track-a}-test.json`，2026-10-22/23）；[§10](#10-可复算) 给的是**从视图重跑**的命令（同模型、同视图、同口径，期望复现同一数字）——两者是「同一结果的两种入口」，不是两套口径。

validation（8,177 行视图，评测 7,887 行，跳过 290 行 >26 选项）同口径：0-shot **0.5127** → adapter **0.7883**（+27.6 pt）；分 kind：choice 0.5392→0.7869、noul 0.3909→0.8499、score 0.2634→0.7299；en 0.4589→0.7621、zh 0.9440→0.9977。

## 4 通用能力代理（防遗忘）—— base 完成 / adapter 未测

lm-eval 0.4.13 + datasets 3.6.0，ceval-valid / cmmlu / mmlu / agieval，`--limit 100`，`--trust_remote_code`，201 个子任务 + 4 组聚合（结果 JSON 共 205 键）；同底座、同 prompt 模板、base 模式生成。组内均值即 lm-eval 的 group 聚合，未二次加工。

| 任务组 | base acc | adapter acc | 差值 |
|---|---:|---:|---:|
| ceval-valid | 0.5847 | 未测 | 未测 |
| cmmlu | 0.5624 | 未测 | 未测 |
| mmlu | 0.5765 | 未测 | 未测 |
| agieval | 0.4133 | 未测 | 未测 |
| **均值** | **0.5342** | 未测 | 未测 |

**门禁**：adapter 侧在 2026-10-23 17:27 系统崩溃时中断（约 25%，未落盘）；GPU 恢复后重跑 ~30–60 分钟（`.agent/RESUME-GPU.md` §2）。预注册阈值：均值降 ≥2pt 警戒、≥5pt 判失败。

## 5 成本与延迟 —— 部分（历史墙钟，非正式基准）

| 项 | 数值 | 口径 |
|---|---|---|
| 训练 | 1 epoch / 1,564 步 / **9,135 s（2.54 h）** / 峰值显存 **6,286 MB** | RX 7900 XT，fp16+SDPA+grad ckpt，batch 8×grad-accum 4 |
| test 评测（15,573 行） | base **433.8 s（35.9 行/s）** / adapter **561.1 s（27.8 行/s）** | batch 32，fp16，含数据加载与 tokenize |
| 单题 p50/p95、tokens/s、batch=1/16 峰值显存 | 未测 | 需 `finetune/bench_latency.py`（GPU，~10 分钟）；包内已提供 |

> 历史墙钟不是正式延迟基准：不含 batch=1、未分离 tokenize/推理、未做 warmup；不用于跨硬件排名。

## 6 统计（CI / 显著性）—— 待输入

- 现只有聚合 JSON，**没有逐行预测**，因此配对 bootstrap 无法计算；test 的 +27.4 pt 只有点估计，**无 CI**。
- 已预置的统计方案（聚合脚本自动产出）：
  - **主区间**：配对 group-cluster bootstrap，簇 = rid 的 `#` 前缀，10,000 次重采样，Δ 按行加权，报告 G / 簇大小中位数 / Kish n_eff / reliability（G≥50 ok、30–49 cautious、<30 low）；
  - item-level paired bootstrap 1000 次（seed 20261023）只作近似，不得用它替代主区间；
  - 缺失行主口径固定分母（失败记错误），另给双方完成子集敏感性分析。
- **最小可检测效应（MDE，α=0.05、power=0.8、N=6,541，双比例保守上界）**：p≈0.50 时约 **2.45 pt**、p≈0.65 约 **2.34 pt**、p≈0.78 约 **2.03 pt**；配对正相关通常更低，但组相关会抬高实际值——**不能把 6,541 当独立样本保证检出 +5 pt**。
- **预注册判据不事后更改**：仍按「两独立 95% CI 不重叠」判定「有意义提升」；若日后配对 Δ 的 CI 不含 0 但独立 CI 重叠，只能报告「配对分析显示正向差异；预注册门槛未满足」。
- 单 seed / 单轮不能证明跨 seed 稳定、因果泛化、部署安全或群体公平。


## 7 数据/口径边界（不混表声明）

| 材料 | 是否本卡数字 | 说明 |
|---|---|---|
| general v5 public test / validation（本文 §3） | ✅ 本研究评测 | 同底座、同 prompt、同代码、同视图 sha |
| lm-eval 四任务（§4） | ✅ 本研究评测 | 只作「在所选代理上」的防遗忘证据 |
| 私有保留集（§1） | ⏳ 未测 | 只发布聚合；内容不进仓库/日志/训练上下文 |
| POL2 冻结集 / POL2 score-v2 / EVAL-02 具身 / EVAL-03 理论 / Kev-4B | ❌ 不在本卡 | 专项或协作者数据，需 owner/协作者授权后单独预注册；**不与本表混排** |
| 协作者通用数据（版本/来源/划分不同） | ❌ 不在本卡 | 只作外部参照，引用必须注明差异 |

## 8 未测、失败与门禁

| # | 项 | 状态 | 门禁 / 需要什么 | 影响 |
|---|---|---|---|---|
| 1 | 私有保留集 base vs adapter | 未测 | owner 定执行方式；独立评测者按包运行 | 主结论（唯一能回答「是否真的更好」） |
| 2 | 温度校准（validation 拟合 → 保留集 apply） | 未拟合 | 逐行预测（GPU） | 不能讨论自动处置/风险-覆盖 |
| 3 | adapter lm-eval 四任务 | 未测（2026-10-23 崩溃中断） | GPU 恢复 + 硬件确认 | 防遗忘结论只有 base 侧 |
| 4 | 成对 bootstrap CI / 多 seed | 未测 | 逐行预测 + 预注册 seed 20261024/25 重训 | +27.4 pt 无区间；单 seed 不能声称泛化 |
| 5 | 批次延迟 p50/p95、tokens/s、峰值显存 | 未测 | GPU；`bench_latency.py` | 成本结论只有历史墙钟 |
| 6 | 保留集分层（kind/lang/桶/route） | 未测 | 聚合脚本已支持，随 #1 产出 | 无法判断提升集中在哪类题 |
| 7 | PoL2 专项 / 外部安全基准（XSTest 误拦） | 不在范围 | owner/协作者授权 | 本卡不涉及 |
| 8 | >26 选项题 | 未训练、未评测 | 设计上跳过（训练/评测一致） | 该子集能力未知 |

**已知的区间口径限制（必须随结果一起读）**：聚合脚本当前没有 `--view` 模式（ITT 全量配对；设计已写进内部规格 v3，本轮不做）。因此：主区间（`paired.cluster`）在**双方都完成的 rid 交集**上计算，而 `accuracy_with_missing` 是**固定分母**的点估计；如果保留集评测出现「两侧缺失集合不同」，这两个量的样本集不一致。默认 fail-closed 要求完整预测，就是为了让两者一致；一旦用了 `--allow-missing`，结果卡必须同时给出两侧完成率，并注明配对 CI 的作用域是完成交集。

**已知失败/事故记录**：2026-10-23 17:27 内核 bugcheck（0x3B）中断 lm-eval adapter 侧（约 25% 已完成、未落盘）；T10 已物理移除；GPU 恢复前需 owner 确认 PSU/内存。详见 `.agent/notes/2026-10-23-crash-investigation-polgov.md`。

## 9 验收清单（对应任务书 §7）

- [x] 模型 revision / 适配器 sha / 视图 sha 全部记录（[versions.json](versions.json)，可脚本复算）
- [x] 保留集相关表述**没有**任何 id/原文/逐例输出（本卡未运行保留集）
- [ ] 温度在 validation 拟合、保留集只 apply —— **未拟合**（门禁 §8#2）
- [ ] 分层指标 + CI + 校准 + 通用能力 + 延迟成本齐全 —— 分层（test/validation）✅；CI/校准/延迟 ❌；通用能力 base ✅ / adapter ❌
- [x] 与历史结果（test 0.7785）口径一致（逐位一致）
- [x] 失败/未测项如实列出（§8）
- [x] 评测包自校验通过（`prepare_eval_package.py --check` pass；`sha256sum -c CHECKSUMS.sha256` 13/13 OK）
- [x] 独立审计 6 条发现已处理：修复**导出闸门双舍入假拒**（合法 delta 与两 accuracy 相差 1e-6 被误拒；已加回归测试）、收紧 `coverage.skipped` 键/模型标签/seed 范围、清理交付脚本中的本机路径、修正复算路径与示例数字
- [x] **CPU 端到端冒烟通过**（公开 validation 前 48 行 + 9.8M 随机 tiny 模型与其 LoRA：推理 35 行/侧 → 聚合 fit 路径 → 导出检查器 pass → 延迟基准产出 `pol-latency-bench-v1`；导出文件不含任何 rid/prompt 片段）。冒烟只证明**链路可执行**，不产生任何真实结论数字。

## 10 可复算

**公开 test 回归（需要 GPU + WSL 环境）**：
```bash
# base 0-shot / adapter，同口径（batch 32，跳过 >26 选项与 >4,000 字符 prompt）
python -u finetune/eval_decision.py --eval-view ~/src/polgov/data/general-test-view.jsonl \
  --model ~/src/polgov/models/Qwen3-1.7B --batch-size 32 --json            # 期望 0.5047
python -u finetune/eval_decision.py --eval-view ~/src/polgov/data/general-test-view.jsonl \
  --model ~/src/polgov/models/Qwen3-1.7B --adapter ~/src/polgov/runs/track-a-e1-rocm/adapter \
  --batch-size 32 --json                                                    # 期望 0.7785
```

**保留集最终评测（交给独立评测者 / owner 授权后执行）**：见 [eval-package/README.md](eval-package/README.md)；产出只有 `aggregate.json`，且必须通过 `finetune/check_aggregate_export.py` 才能带出隔离环境。

**版本校验与包漂移检查（在仓库根）**：
```bash
python finetune/prepare_eval_package.py --versions results/MODEL-02-final-eval/versions.json \
  --out results/MODEL-02-final-eval/eval-package --check      # 期望 {"status":"pass","files":12}
cd results/MODEL-02-final-eval/eval-package && sha256sum -c CHECKSUMS.sha256
```

**CPU 端到端冒烟（可复算，无需 GPU/私有数据）**：把公开 validation 前 48 行写成中性文件名 → `python -m finetune.eval_decision`（tiny 模型 + tiny LoRA）→ `python -m finetune.final_eval_aggregate --fit-preds ... --cluster-rounds 1000` → `python -m finetune.check_aggregate_export` → `python -m finetune.bench_latency`；结果：两侧各 35 行有效、聚合/检查/延迟全部 exit 0，导出文件无 rid/prompt 泄漏。脚本见内部 `.agent/scratch/final-eval-package-smoke.sh`（内部工作区，不进公开仓库）。

> 公开 test 是否影响过模型/提示/阈值选择：**没有**。public test 只做回归；模型选择只用 validation（A 半）与预注册配置。
> 独立评测者：**未指定**（待 owner）。定版 revision：本轮冻结为 base@70d244cc + adapter@ad88db90；任何改动都必须视为新一轮。
