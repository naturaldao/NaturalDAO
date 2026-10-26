# 实验结果：Track A 冒烟基线（Qwen3-1.7B + LoRA 字母 SFT）

> **历史冒烟卡（2026-10-22，T10）**：仅管线验证；完整 1 epoch 基线见 [MODEL-02-qwen3-1.7b-track-a-full](../MODEL-02-qwen3-1.7b-track-a-full/CARD.md)。

- **任务 / 分支 / 领取人 / Agent**：MODEL-02 / `pol/MODEL-02/wenbo` / Wenbo / DSH Agent Team
- **模型与底座 revision / 方法**：Qwen/Qwen3-1.7B（本地快照，2026-10-22 下载） + PEFT LoRA r16 / alpha32 / dropout 0.05 / all-linear；completion-only 单字母 SFT（A..Z 对应选项下标）
- **数据版本 / 划分 / 校准方法**：general v5 训练视图（`datasets/general/build_training_view.py`，template tv-1）；
  训练视图 train sha256 `a136c2a1…`（51,947 行，本次仅用前 4,000 行），validation 视图 sha256 `b936c618…`（8,177 行，本次评测前 300 行）；未做温度校准
- **对照组 / 硬件 / 精度 / 预算**：同底座 0-shot（无 adapter）；Tesla T10 16GB（Turing，fp16 + SDPA + gradient checkpointing）；Windows 11；训练 40 step / 4,000 样本，峰值显存约 8.0 GB，训练 150 s + 两次验证评测
- **可复现命令 / 配置 / 公开预测链接**：见 `finetune/README.md`；本次配置 `--limit 4000 --max-steps 40 --batch-size 2 --grad-accum 4 --seq-len 1024 --epochs 1 --lr 1e-4 --seed 20261023`；预测文件不提交（逐例内容不入库）

| 比较项 | 0-shot 基线 | 微调后（40 step） | 差值 |
|---|---|---|---|
| 决策字母准确率（validation 前 300 行） | **0.3833**（115/300） | **0.5000**（150/300） | **+11.7 pt** |
| 其中 choice（同一子集） | 0.3833 | 0.5000 | +11.7 pt |
| 选项数 2 | — | 0.5702（69/121） | — |
| 选项数 3–4 | — | 0.4844（31/64） | — |
| 选项数 5–8 | — | 0.4486（48/107） | — |
| 选项数 9–26 | — | 0.2500（2/8） | 样本过少 |
| PoL 判定与误拦 | 未测（本数据集不是 PoL2 专项） | 未测 | — |
| 通用能力保持 | 未测（本轮未跑 lm-eval 代理） | 未测 | — |
| 主流安全测试 | 未测 | 未测 | — |
| 延迟与成本 | 评测 300 条 18.5 s（16.2 条/s，单卡） | 评测 300 条 25.3 s（含 adapter 加载） | 未做生产延迟协议 |

**结论与限制**：

- 这是一次**冒烟基线**：只训练 40 step / 4,000 样本，用来验证「训练视图 → LoRA SFT → adapter 评测」整条管线可跑、可存档、可复评；**不是**完整基线结论。
- 观察到微调后同一验证子集准确率 +11.7 pt，说明字母格式与决策任务可学；但样本少、单 seed、未做显著性检验，不能据此声称泛化提升。
- 未测：通用智力保持（ceval/cmmlu/mmlu/agieval）、校准（ECE/Brier/温度缩放）、PoL2 专项（数据未批准）、外部安全基准、完整 validation/test 评测、多 seed 与置信区间。
- 位置偏置与字母先验未量化；score 题被当作离散字母类，未体现等级距离。
- 训练数据只含 general train；**未使用 PoL2 冻结数据**（`training_approved=false`）。

**说明测试是公开回归还是独立保留集**：公开 validation 子集（回归用），非独立保留集；私有 benchmark 未触碰。

- **公开测试是否影响模型、提示或阈值选择**：未使用 public test；validation 仅用于本卡评估与后续选型。
- **独立保留集评测者 / 定版模型 revision**：尚未定版；私有保留集由独立评测者统一评测，本轮未运行。

## 下一步

1. 完整 1 epoch（51,947 行）基线 + 0-shot/微调同子集对照（进行中）。
2. 通用能力代理（lm-eval：ceval/cmmlu/mmlu/agieval，各 limit≥500）前后对照。
3. Track B 候选评分头（masked CE，支持变长选项与软标签）作主路线。
4. 校准链路：温度缩放在 validation 派生校准子集拟合，报告 ECE/Brier。
