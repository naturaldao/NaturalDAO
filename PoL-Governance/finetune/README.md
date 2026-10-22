# PoL-Governance Track A: 决策模型单 token 字母微调 (SFT)

本项目为 PoL-Governance 第二阶段模型适配中 **Track A 字母微调基线** 的完整实现方案，包含训练脚本、评测脚本、通用工具模块与纯 CPU 离线单测。

---

## 1. 架构与设计说明

第二阶段的核心目标是培养仅做封闭选择（`noul`、`choice`、`score`）的小决策模型。
- **Track A 路线**：将题面候选选项格式化渲染为 `A. {label}\nB. {label}...\n\n【答案】\n`，模型在输出位置预测唯一的单字母 token（`A`..`Z`）。
- **训练目标**：采用 **Completion-only SFT**，提示词上下文部分全部填充 `-100` 屏蔽损失，仅在答案字母位置计算交叉熵。
- **依赖栈约束**：仅依赖纯 Python + `torch` + `transformers` + `peft`。不依赖 LLaMA-Factory、Axolotl、DeepSpeed、Unsloth 等第三方训练框架，确保轻量、透明、易调试。
- **代码文件布局**：
  - `finetune/train_decision_sft.py`：核心训练脚本。
  - `finetune/eval_decision.py`：分层决策准确率评测脚本（支持 0-shot 基线与 LoRA adapter 评测）。
  - `finetune/decision_common.py`：公共数据格式化、字母映射、截断、分层指标与安全护栏。
  - `finetune/test_train_decision_sft.py`：纯 CPU 离线单元测试集（< 1s 完成）。

---

## 2. 数据准备

训练视图数据由 `datasets/general/build_training_view.py` 生成。数据文件必须保存在仓库外部（例如 `D:/pol2-train/data/`）：

```powershell
# 生成通用决策数据集统一训练视图
python datasets/general/build_training_view.py --split train --out D:/pol2-train/data/general-train-view.jsonl
python datasets/general/build_training_view.py --split validation --out D:/pol2-train/data/general-validation-view.jsonl
python datasets/general/build_training_view.py --split test --out D:/pol2-train/data/general-test-view.jsonl
```

每行数据 Schema 包含：
- `rid`: `"<item_id>#<question_key>"` 全局唯一键
- `kind`: `"choice"` | `"noul"` | `"score"`
- `prompt`: 渲染后的完整题面（情境 + 问题 + A/B/C... 候选选项）
- `options`: 选项原始键/档位列表
- `option_labels`: 选项展示文本
- `answer_idx`: 正确选项下标 (int)
- `route`: `"classification"` | `"distillation"`

---

## 3. 运行环境与硬件约束

- **硬件配置**：
  - 单张 **NVIDIA Tesla T10 16GB**（Turing 架构，Compute Capability 7.5）
  - 特性约束：支持 **fp16**，**不支持 bf16**，不支持 FlashAttention-2。本脚本默认采用 PyTorch 原生 **SDPA** (`attn_implementation="sdpa"`)。
  - 宿主机配置：Windows 11 x64, AMD Ryzen 7 5700X, 80GB RAM。
- **虚拟环境**：
  - 训练依赖环境由 Lead 统一安装在 `D:/pol2-train/.venv`（包含 torch cu124、transformers、peft）。
- **安全护栏 (Guard)**：
  - `train_decision_sft.py` 与 `eval_decision.py` 均内建路径检测护栏。
  - 若 `--output-dir` 或 `--predictions` 指向本 git 仓库内部路径，程序将直接中止并退出（退出码 **2**），杜绝训练副产物意外污染仓库。

---

## 4. Track A 命令执行流

在 PowerShell 中激活训练虚拟环境：
```powershell
& D:/pol2-train/.venv/Scripts/Activate.ps1
```

### 步骤 1：Dry-Run 校验（0 显存、不加载模型权重）
检查输入数据、统计选项过滤情况、验证 batch 构建与前 3 条样本形状：
```powershell
python finetune/train_decision_sft.py `
  --train-view D:/pol2-train/data/general-train-view.jsonl `
  --output-dir D:/pol2-train/runs/track-a-qwen1.7b `
  --dry-run
```

### 步骤 2：小样本冒烟测试 (Smoke Test)
使用前 100 条样本跑 1 轮微调，验证前向传播、梯度反向传播与周期评测链路：
```powershell
python finetune/train_decision_sft.py `
  --train-view D:/pol2-train/data/general-train-view.jsonl `
  --eval-view D:/pol2-train/data/general-validation-view.jsonl `
  --model Qwen/Qwen3-1.7B `
  --output-dir D:/pol2-train/runs/track-a-smoke `
  --limit 100 `
  --eval-limit 50 `
  --epochs 1 `
  --batch-size 4 `
  --grad-accum 2 `
  --eval-every 25
```

### 步骤 3：完整训练 (Full Training)
对全量过滤后训练数据（约 5.1 万条）执行完整 SFT 训练：
```powershell
python finetune/train_decision_sft.py `
  --train-view D:/pol2-train/data/general-train-view.jsonl `
  --eval-view D:/pol2-train/data/general-validation-view.jsonl `
  --model Qwen/Qwen3-1.7B `
  --output-dir D:/pol2-train/runs/track-a-qwen1.7b-r16 `
  --epochs 2 `
  --batch-size 4 `
  --grad-accum 8 `
  --lr 1e-4 `
  --seq-len 1536 `
  --lora-r 16 `
  --lora-alpha 32 `
  --lora-dropout 0.05 `
  --eval-limit 500 `
  --eval-every 200 `
  --seed 20261023
```

### 步骤 4：断点续跑 (Resume)
如遇意外中断，添加 `--resume` 即可从 `output-dir/adapter` 继续微调：
```powershell
python finetune/train_decision_sft.py `
  --train-view D:/pol2-train/data/general-train-view.jsonl `
  --output-dir D:/pol2-train/runs/track-a-qwen1.7b-r16 `
  --resume
```

---

## 5. 显存与耗时预期（标为估算）

> 注：以下指标均为基于理论参数与 Turing 架构特性的工程估算值，供资源排期参考。

### 显存开销估算 (VRAM Estimates)
| 组成部分 | Qwen3-1.7B (LoRA fp16) | Qwen3-4B (LoRA fp16) | 估算说明 |
|---|---|---|---|
| 基座模型权重 | ~3.4 GB | ~8.0 GB | fp16 存储 (2 bytes/param) |
| LoRA 参数与 AdamW 状态 | ~0.2 GB | ~0.5 GB | r=16, alpha=32, target_modules=all-linear |
| 激活显存 (bs=4, seq=1536) | ~1.8 GB | ~2.4 GB | 开启 `gradient_checkpointing` + SDPA |
| CUDA Context 与内存碎片 | ~1.2 GB | ~1.2 GB | PyTorch 运行时预留 |
| **预估总显存需求** | **~6.6 GB** | **~12.1 GB** | **在 16GB Tesla T10 上均完全可容纳** |

### 训练耗时估算 (Duration Estimates)
- **数据集规模**：全量训练集 ~51,947 样本。
- **有效批次大小**：`batch_size (4) * grad_accum (8) = 32`。
- **每轮更新步数**：`51,947 / 32 ≈ 1,623 steps/epoch`。
- **Tesla T10 吞吐速率**：
  - Qwen3-1.7B：约 9 ~ 12 样本/秒（约 0.28 ~ 0.38 step/秒）。
  - 单轮耗时：`51,947 / 10 ≈ 5,200 秒 ≈ 1.4 小时`。
  - **2 轮完整训练总耗时：约 2.8 ~ 3.5 小时**。

---

## 6. 决策评测命令 (Evaluation)

`eval_decision.py` 支持批量读取测试视图，前向推理末位 token 处的字母 logits（A..Z 候选范围），并计算各细分维度的准确率。

### 0-Shot 基线评测
```powershell
python finetune/eval_decision.py `
  --eval-view D:/pol2-train/data/general-test-view.jsonl `
  --model Qwen/Qwen3-1.7B `
  --batch-size 8 `
  --predictions D:/pol2-train/runs/eval_0shot_preds.jsonl
```

### LoRA 微调模型评测
```powershell
python finetune/eval_decision.py `
  --eval-view D:/pol2-train/data/general-test-view.jsonl `
  --model Qwen/Qwen3-1.7B `
  --adapter D:/pol2-train/runs/track-a-qwen1.7b-r16/adapter `
  --batch-size 8 `
  --predictions D:/pol2-train/runs/eval_lora_preds.jsonl `
  --json
```

评测报告自动输出整体 accuracy 以及 4 个维度的分层统计：
1. **题型 (by_kind)**：`choice`（多选一）、`noul`（二元是非）、`score`（序数打分）
2. **语言 (by_lang)**：`zh`、`en` 等
3. **选项数 (by_option_bucket)**：`2`、`3-4`、`5-8`、`9-26`
4. **路由 (by_route)**：`classification`、`distillation`

---

## 7. 已知限制与演进路线 (Limitations & Next Steps)

1. **>26 选项截断**：
   - 字母单 token 方案受限于 26 个英文字母。通用训练集中有 1,914 条 choice 题目选项数 >26（最大达 69 个选项，占 choice 的 4.5%）。这些题目在 Track A 中被计数并跳过。
2. **位置偏置 (Position Bias)**：
   - 自回归模型在选择字母 A/B/C 时天然存在字母出现频率与位置先验偏置。
3. **序数语义丢失**：
   - 对于 `score` 题型（例如 0~4 档风险打分），字母 SFT 将其退化为 5 个无序的类别标签（A~E），无法衡量"预测 3 分但实际 4 分"（小错）与"预测 0 分但实际 4 分"（大错）的区别。
4. **主路线 (Track B)**：
   - 针对上述退化，项目规划的 **Track B（候选评分头 pointer/scorer head + masked CE）** 为主路线。在每个候选选项前放置可学习 marker token，通过动态 Linear 评分头输出标量并在选项间做题内 Softmax，原生支持任意变长候选、软概率 KL 蒸馏与温度校准。

---

## 8. 离线单元测试

在无需 GPU、无需下载大模型权重的环境下验证全部核心逻辑：
```powershell
python -m unittest finetune.test_train_decision_sft -v
```

静态语法校验：
```powershell
python -m py_compile finetune/decision_common.py finetune/train_decision_sft.py finetune/eval_decision.py finetune/test_train_decision_sft.py
```
