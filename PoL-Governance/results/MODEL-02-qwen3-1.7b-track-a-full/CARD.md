# 实验结果：Track A 完整基线（Qwen3-1.7B + LoRA 字母 SFT，1 epoch）

- **任务 / 分支 / 领取人 / Agent**：MODEL-02 / `pol/MODEL-02/wenbo` / Wenbo / DSH Agent Team
- **模型与方法**：Qwen/Qwen3-1.7B + PEFT LoRA（r16 / alpha32 / dropout 0.05 / all-linear）；completion-only 单字母 SFT（A..Z ↔ 选项下标，>26 选项跳过）；**只训练答案位**（末位 token 轻量损失，只对该位置过 lm_head）
- **数据版本 / 划分**：general v5 训练视图（`build_training_view.py`，模板 tv-1）；train 视图 sha256 `a136c2a1…`（51,947 行，有效 50,033 行；1,914 行 >26 选项被训练脚本跳过）；validation 视图 sha256 `b936c618…`（8,177 行，评测 7,887 行，跳过 290 行 >26 选项）。**未使用 PoL2 冻结数据**（`training_approved=false`）。
- **硬件 / 精度 / 预算**：RX 7900 XT 20GB（gfx1100），WSL2 Ubuntu 24.04 + ROCm 7.2.1 + PyTorch 2.9.1+rocm7.2.1；fp16 + SDPA + gradient checkpointing；1 epoch、1,564 步、batch 8 × grad-accum 4（有效 32）、seq len 1024、lr 1e-4 cosine + 3% warmup、seed 20261023；**训练 9,135 s（2.54 h），峰值显存 6,286 MB**。
- **可复现命令**：见 `finetune/README.md` §4/§11；配置与数据 sha256 见输出目录 `train-manifest.json`；adapter 与日志在仓库外 `~/src/polgov/runs/track-a-e1-rocm/`。

## 验证集结果（7,887 行；0-shot 与 adapter 同一子集）

| 分层 | 0-shot 基线 | LoRA 微调 | 差值 |
|---|---:|---:|---:|
| **整体准确率** | **0.5127**（4,044/7,887） | **0.7883**（6,217/7,887） | **+27.6 pt** |
| choice | 0.5392 | 0.7869 | +24.8 pt |
| noul | 0.3909 | 0.8499 | +45.9 pt |
| score | 0.2634 | 0.7299 | +46.7 pt |
| 英文（en） | 0.4589（7,012） | 0.7621 | +30.3 pt |
| 中文（zh） | 0.9440（875） | 0.9977 | +5.4 pt（**天花板/位置先验，见限制**） |
| 选项数 2 | 0.4843 | 0.8511 | +36.7 pt |
| 选项数 3–4 | 0.6147 | 0.8618 | +24.7 pt |
| 选项数 5–8 | 0.2940 | 0.6021 | +30.8 pt |
| 选项数 9–26 | 0.1516 | 0.3287 | +17.7 pt |
| classification 路由 | 0.5164 | 0.7949 | +27.9 pt |
| distillation 路由 | 0.4663 | 0.7047 | +23.8 pt |

### 训练过程（500 行周期评测）

| step | 准确率 |
|---:|---:|
| 400 | 0.668 |
| 800 | 0.758 |
| 1200 | 0.792 |


## 测试集结果（15,573 行；adapter；0-shot 同口径评测未跑，按用户要求暂停 GPU）

| 分层 | adapter 准确率 |
|---|---:|
| **整体** | **0.7785**（12,124/15,573） |
| choice | 0.7780（13,548） |
| noul | 0.8450（1,097） |
| score | 0.7069（928） |
| en | 0.7514（13,824） |
| zh | 0.9931（1,749；与 validation 相同的天花板/位置先验问题） |
| 选项数 2 | 0.8277（3,163） |
| 选项数 3–4 | 0.8484（9,157） |
| 选项数 5–8 | 0.6100（2,282） |
| 选项数 9–26 | 0.3553（971） |
| classification 路由 | 0.7858（14,294） |
| distillation 路由 | 0.6974（1,279） |

跳过：>26 选项 656 行、超长 prompt（>4,000 字符）77 行；与 validation 分母口径一致处见 `skipped_stats`。
评测耗时 561 s（27.75 行/s，含 adapter 加载）。**基座 0-shot 在 test 上的同口径评测尚未跑**（调度原因），因此 test 上暂不报告差值；validation 上的 base vs adapter 差值见上表。

## 结论与限制

- **这是首个完整决策基线**：在同一 validation 子集上，1 epoch LoRA 把封闭选择准确率从 0.5127 提到 0.7883；提升集中在 noul/score 与 5–8 选项题，说明字母格式与决策读出的迁移有效。
- **中文子集不可当能力证据**：0-shot 基座在中文 validation 子集已有 0.9440（adapter 0.9977），说明该子集结构上可被位置/标签先验猜中（中文补充集只进 train，但 validation 中文行来自其他来源，存在固定答案位置倾向）。引用时必须注明。
- **未测**：test 的 base 0-shot 对照、通用智力代理（lm-eval）、校准（ECE/Brier/温度缩放）、PoL2 专项（数据未批准）、外部安全基准、多 seed/置信区间、>26 选项题。
- **单 seed、单配置**：没有显著性检验，不能据此声称泛化提升；需要至少 2–3 seed 与 0-shot 同 prompt 对照重复。
- **位置偏置未量化**：字母 SFT 存在字母/位置先验；Track B 候选评分头 + 选项顺序消融是后续主路线。
- **score 题被当作离散字母类**：未建模档位距离（序数回归留待 v1.1）。

## 下一步

1. test 分区基座 0-shot 同口径评测 → 补全差值（GPU 已按用户要求暂停）。
2. 通用能力代理（lm-eval：ceval/cmmlu/mmlu/agieval，limit 100–500）base vs adapter。
3. Track B 候选评分头训练（主路线；变长选项、软标签蒸馏、温度校准）。
4. 校准链路与多 seed 复现。

> 公开测试是否影响模型/提示/阈值选择：未用 public test 调参；validation 仅用于评估与后续选型。独立保留集由独立评测者统一评测，本轮未运行。
