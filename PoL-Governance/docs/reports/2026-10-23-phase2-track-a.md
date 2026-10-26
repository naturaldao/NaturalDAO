# 阶段报告：第二阶段启动与 Track A 基线（2026-10-23）

## 一句话

第二阶段（模型适配）启动：完成通用决策数据的**统一训练视图**、**环境与训练管线**，并跑出**首个完整基线**——
Qwen3-1.7B + LoRA 单字母 SFT 在 validation 上把封闭选择准确率从 **0.5127（0-shot）提到 0.7883**。
GPU 实验按 owner 要求暂停，等待设备调整后继续。

## 1. 训练视图（M2-2）

`datasets/general/build_training_view.py` 把 general v5 公开分区转成「一行 = 一个问题」的 JSONL（模板 tv-1，离线、仅标准库、确定性）：

| 分区 | 行数 | choice | noul | score | 说明 |
|---|---:|---:|---:|---:|---|
| train | 51,947 | 42,694 | 5,082 | 4,171 | 问题行 52,999 − drop 1,052 |
| validation | 8,177 | 7,156 | 573 | 448 | − drop 184 |
| test | 16,306 | 14,266 | 1,107 | 933 | − drop 335 |

口径与 [TRAINING](../../datasets/general/TRAINING.md) 对齐；中文补充集 3,148 行按兜底规则进 classification；>26 选项保留在视图中（训练/评测按字母集跳过并计数）。
文档：[TRAINING-VIEW.md](../../datasets/general/TRAINING-VIEW.md)。

## 2. 训练与评测管线

- 代码：`finetune/`（Train A 字母 SFT、Track B 候选评分头、评测脚本、CPU 单测）。
- 训练优化：**末位 token 轻量损失**（只对答案位置过 lm_head，避免全量 logits）；评测只算末位 logits 并按长度排序组 batch。
- 期间发现并修复一个**标签泄漏 bug**（首版轻量损失取了标签自身位置的 hidden，等价抄答案）；修复后 loss 回到真实水平。

## 3. Track A 完整基线（1 epoch）

- 数据：train 视图有效 50,033 行（跳过 1,914 行 >26 选项）；LoRA r16/alpha32/all-linear，fp16 + SDPA + grad ckpt；
  batch 8 × grad-accum 4（有效 32）、seq 1024、lr 1e-4 cosine、seed 20261023、1 epoch（1,564 步）。
- 训练：**2.54 h**，峰值显存 **6.29 GB**（RX 7900 XT 20GB / WSL2 ROCm 7.2.1 / PyTorch 2.9.1）。
- 周期评测（validation 500 行）：step 400 → 0.668，step 800 → 0.758，step 1200 → 0.792。

### validation 结果（7,887 行，0-shot 与 adapter 同子集）

| 分层 | 0-shot | LoRA | 差值 |
|---|---:|---:|---:|
| **整体** | **0.5127** | **0.7883** | **+27.6 pt** |
| choice | 0.5392 | 0.7869 | +24.8 pt |
| noul | 0.3909 | 0.8499 | +45.9 pt |
| score | 0.2634 | 0.7299 | +46.7 pt |
| en | 0.4589 | 0.7621 | +30.3 pt |
| zh | 0.9440 | 0.9977 | +5.4 pt（天花板，见限制） |
| 选项数 2 | 0.4843 | 0.8511 | +36.7 pt |
| 选项数 3–4 | 0.6147 | 0.8618 | +24.7 pt |
| 选项数 5–8 | 0.2940 | 0.6021 | +30.8 pt |
| 选项数 9–26 | 0.1516 | 0.3287 | +17.7 pt |

### test 结果（15,573 行，adapter）

整体 **0.7785**；choice 0.7780 / noul 0.8450 / score 0.7069；en 0.7514 / zh 0.9931；
选项数 2/3–4/5–8/9–26：0.8277 / 0.8484 / 0.6100 / 0.3553。
（>26 选项 656 行与超长 prompt 77 行按口径跳过；基座 0-shot 的 test 对照已在 2026-10-23 崩溃前补跑，见 §7。）

## 4. 已知限制（引用时不要弱化）

- **单 seed、单配置**：无显著性检验，不能声称泛化提升；需要 2–3 seed 复现与置信区间。
- **中文子集不能当能力证据**：zh 行 0-shot 已达 0.944、adapter 0.998，说明该子集可被位置/标签先验猜中；主指标应按 en 与选项数分层看。
- **>26 选项题暂未训练**（1,914 行 train / 656 行 test 跳过）；长选项题仍是弱点（9–26 选项仅 0.33）。
- **未测**：通用智力代理（lm-eval）、校准（ECE/Brier/温度缩放）、PoL2 专项（数据未批准）、外部安全基准、test 的 0-shot 对照。
- **未使用 PoL2 冻结数据**：`training_approved=false`，批准前零梯度。

## 5. 状态与下一步

- **GPU 实验已暂停**（用户要求设备调整后再继续）；代码、数据视图、结果卡与文档已提交到 `pol/MODEL-02/wenbo` 分支（已合入最新 main）。**PR #44/#45 已由维护者关闭**，集成方式待确认；main 同时新增同仓库项目 `POL2-Steward`（治理服务，阶段四可对接）。
- 恢复后顺序：test 0-shot 对照 → 通用能力代理（lm-eval）→ Track B 候选评分头（主路线）→ 校准 → 多 seed。
- 需要拍板：阶段一数据集成方式、HF 上传、PoL2 训练授权、底座档位（1.7B→4B）、评测阈值预注册。

## 6. 暂停期补充（2026-10-23，CPU-only）

GPU 实验按 owner 要求暂停（设备调整，等待手动开启）。暂停期完成 CPU 工作：

- **预注册评测协议** [EVAL-PROTOCOL.md](../../finetune/EVAL-PROTOCOL.md)：决策/校准/通用能力代理/统计口径与阈值先声明（test 只回归、validation 固定切半、≥2–3 seed、报告 CI）。
- **温度校准工具** `finetune/calibrate.py` + 7 个纯 CPU 测试：在 validation 的 calibration 半区拟合温度、selection 半区复算，输出 NLL/Brier/ECE/MCE。
- **GPU 恢复清单**（内部）：恢复后先跑 test 的 base 0-shot 对照 → lm-eval → Track B → 校准 → 多 seed。

## 7. 更新（2026-10-23 崩溃前落盘：test base 与 lm-eval base）

在 2026-10-23 的 GPU 队列中（当日 17:27 系统崩溃之前）完成并落盘了两项此前缺失的对照：

- **test 分区 base 0-shot 同口径**：整体 **0.5047**（7,859/15,573）vs adapter **0.7785**，差值 **+27.4pt**；
  分层：choice 0.5283→0.7780、noul 0.4075→0.8450、score 0.2748→0.7069、en 0.4490→0.7514、zh 0.9445→0.9931；
  base 与 adapter 跳过口径相同（>26 选项 656 行、超长 prompt 77 行）。
- **lm-eval 通用能力代理 base 侧**（四任务组，limit 100，205 个子任务）：
  ceval-valid **0.5847** / cmmlu **0.5624** / mmlu **0.5765** / agieval **0.4133**，均值 **0.5342**。
- **adapter 侧 lm-eval 在 17:27 系统崩溃时被中断**（约 25%，未落盘），待环境稳定后重跑；崩溃后 T10 已移除，
  owner 需先确认 PSU/内存/插槽配置，再恢复长时间 GPU 训练（单卡短任务优先）。

结果卡已同步：results/MODEL-02-qwen3-1.7b-track-a-full/CARD.md。