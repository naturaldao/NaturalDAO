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

- **首选硬件：Radeon RX 7900 XT 20GB（gfx1100）**，Windows 11 + WSL2 Ubuntu 24.04 + ROCm 7.2.1 + PyTorch 2.9.1+rocm7.2.1。
  - 项目环境：WSL 内 `~/src/polgov/.venv`（uv）；数据/模型建议放 WSL ext4（`~/src/polgov/{data,models}`），代码可直接从 `/mnt/c` 仓库运行。
  - 平台资料与验证：`C:/Projects/ROCM`（README / INSTALLED_STATE / TROUBLESHOOTING）。
  - ROCm 上 `torch.cuda` API 为 HIP 别名，本脚本的 fp16 AMP、SDPA、grad checkpointing 均可直接工作。
- **备用硬件：NVIDIA Tesla T10 16GB**（Turing CC 7.5；fp16，无 bf16，不支持 FA2；SDPA）。
- **GPU 静默时段（owner 要求）**：00:30–09:30 与 12:30–15:30 不启动 GPU（已经开始且即将跑完的允许跑完）。
- **训练数据视图生成**：Windows 侧 `D:/pol2-train/.venv`（torch cu124）或任意 Python 3.12 均可（生成器只用标准库）。
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

> 2026-10-23 实测（RX 7900 XT 20GB，WSL2 ROCm 7.2.1 + torch 2.9.1）：
> batch 8 / grad-accum 4 / seq 1024 / grad ckpt + **末位 token 轻量损失**（只对答案位置过 lm_head，
> 不再生成 [B,L,vocab] 全量 logits）：**约 5.8 s/优化步**（有效 batch 32，约 5.5 samples/s），
> 峰值显存约 **6.3 GB**；51k 行 1 epoch（1,563 步）预计 **2.4–2.6 h**。
> T10 对照：batch 4 / grad-accum 2 / seq 1024（有效 batch 8）约 2.1 s/步、峰值 7.9 GB。


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
---

# Track B：候选评分头（主路线，masked CE + 软蒸馏）

## 9. 架构与设计

- **输出形态**：候选评分读出（pointer/scorer head）。每个选项位置出一个 scalar，题内 masked softmax（padding 选项位填 -1e4）；原生支持变长候选（2..26 选项），不依赖字母 token，也不需要为每题换固定分类头。
- **模块结构**（finetune/decision_scorer.py）：
  - DecisionScorer(nn.Module) = AutoModel 底座（transformer 部分，无 lm_head，前向省掉 vocab 投影）+ pointer_head = Linear(hidden→1)（全参训练）；
  - forward(input_ids, attention_mask, marker_positions) -> logits[B, max_opts]，批量 padding 选项位已填 -1e4；
  - 纯函数 masked_softmax / masked_ce（硬标签题内 CE）/ masked_kl（软标签 KL，带温度）/ masked_mixed_loss（(1-λ)·CE + λ·KL，仅 soft 行启用 KL）；
  - save_scorer_head / load_scorer_head 保存/恢复 head state_dict 与配置（scorer_head.pt）。
- **训练器**（finetune/train_decision_scorer.py，CLI 与 Track A 对齐）：LoRA(all-linear) + head 全参（head lr 可 --head-lr-mult 倍率，默认 x5）；AdamW + cosine warmup（3%）；fp16 AMP + GradScaler（Turing 无 bf16）；gradient checkpointing + enable_input_require_grads（PEFT 组合必需，另有 forward hook 兜底）；周期评测（题内 argmax accuracy 按 kind/lang/option_bucket/route 分层 + mean NLL）；保存 adapter/、scorer_head.pt、tokenizer/、train-manifest.json（配置、数据 sha256、行数、指标、显存峰值、时长、seed、模板版本）。
- **损失路由**：classification 行 -> masked CE；distillation 行（soft 有效）-> (1-λ)·CE + λ·KL(T)，--lambda-soft 默认 0.3、--soft-temperature 默认 2.0。温度按标准 KD 处理：学生 logits / T；target 视为教师 logits = log p，故按 p**(1/T) 重整化。soft 无效的 distillation 行回退硬标签并计数（soft_invalid_fallback_hard）。
- **护栏**：--output-dir 必须在仓库外（复用 Track A guard，exit 2）；训练/评测视图文件名含 benchmark/holdout/private 时拒绝（exit 2，保留集不进训练器）。

## 10. 输入模板与 marker 方案（tv-1b）

- 模板版本 tv-1b；与 tv-1 共享固定说明与【情境】【问题】段（字节一致），仅选项段渲染不同：
  1. 取 row.prompt，按最后一个 【选项】 切出情境/问题段（rpartition，防正文自身含该字样）；
  2. 丢弃 tv-1 的字母选项段（不依赖字母列表）；
  3. 追加 【选项】+ 换行 + 每选项一行 'OP: <label>'（label 取 option_labels，缺失回退 options 键）；答案不进输入。
- **marker 定位（分段 tokenize）**：head 段与每个选项行各为独立 segment，encode(segment, add_special_tokens=False) 后拼接成 input_ids；每选项的评分锚点 = 该选项行（'OP: <label>'）的最后一个 token。
- **为什么锚点在行末而不是 'OP:' marker 自身**：因果 decoder 的 hidden state 只能看到该位置之前的内容；若把锚点放在选项文字之前的 marker token 上，评分时看不到该选项自身的文字，题内 softmax 会退化为位置先验（laya 的 marker 前置可行是因为它是双向编码器）。Qwen3 是因果模型，锚点必须落在选项文字之后。
- marker 文本 OP 是普通文本 token（Qwen tokenizer 下 'OP:' -> ['OP', ':']），不依赖任何特有 token id；tiny Llama 随机模型 + stub tokenizer 可完整测试。
- **左侧截断**：总长超过 --seq-len 时从最左侧截断（先裁固定说明/情境），保留完整选项 marker 区间（第一个选项行的全部 token 必须留下）；连选项区都放不下时该行跳过并计数（skipped_seq_len_too_short_for_options）。选项数 >26 与 Track A 一致跳过。
- 可选 --shuffle-options：每 epoch 打乱每题选项顺序（options/labels/answer_idx/soft 同步置换）以消融位置偏置；代价是每 epoch 重新 tokenize，默认关闭。

## 11. Track B 命令执行流

同样先激活训练虚拟环境（D:/pol2-train/.venv/Scripts/Activate.ps1）；模型用本地快照 D:/pol2-train/models/Qwen3-1.7B。命令为单行形式（可直接复制）。

### 步骤 1：Dry-Run 校验（0 显存、不加载模型权重；前向形状校验用随机 tiny 模型）

    python finetune/train_decision_scorer.py --train-view D:/pol2-train/data/general-validation-view.jsonl --model D:/pol2-train/models/Qwen3-1.7B --output-dir D:/pol2-train/runs/track-b-1.7b --dry-run

### 步骤 2：小样本冒烟测试（smoke，对齐 Track A 冒烟口径便于对照）

    python finetune/train_decision_scorer.py --train-view D:/pol2-train/data/general-train-view.jsonl --eval-view D:/pol2-train/data/general-validation-view.jsonl --model D:/pol2-train/models/Qwen3-1.7B --output-dir D:/pol2-train/runs/track-b-smoke --limit 4000 --max-steps 40 --epochs 1 --batch-size 2 --grad-accum 4 --seq-len 1024 --eval-limit 300 --eval-every 20 --seed 20261023

### 步骤 3：完整训练（full）

    python finetune/train_decision_scorer.py --train-view D:/pol2-train/data/general-train-view.jsonl --eval-view D:/pol2-train/data/general-validation-view.jsonl --model D:/pol2-train/models/Qwen3-1.7B --output-dir D:/pol2-train/runs/track-b-qwen1.7b-r16 --epochs 2 --batch-size 4 --grad-accum 8 --lr 1e-4 --seq-len 1536 --lora-r 16 --lora-alpha 32 --lora-dropout 0.05 --lambda-soft 0.3 --soft-temperature 2.0 --head-lr-mult 5 --eval-limit 500 --eval-every 200 --seed 20261023

### 步骤 4：断点续跑（resume）

    python finetune/train_decision_scorer.py --train-view D:/pol2-train/data/general-train-view.jsonl --eval-view D:/pol2-train/data/general-validation-view.jsonl --model D:/pol2-train/models/Qwen3-1.7B --output-dir D:/pol2-train/runs/track-b-qwen1.7b-r16 --resume

产物目录：adapter/（LoRA）、scorer_head.pt（head state_dict + 配置）、tokenizer/、train-manifest.json。

## 12. 显存与耗时估算（标注为估算）

| 组成部分 | Qwen3-1.7B (LoRA fp16 + head) | 估算说明 |
|---|---:|---|
| 基座权重（AutoModel，仅 transformer 部分） | ~3.4 GB | fp16；无 lm_head 前向（Qwen3-1.7B 词表与 embedding 绑定） |
| LoRA 参数 + AdamW 状态 + head | ~0.2-0.3 GB | r16 all-linear + head（hidden->1，约 2k 参数） |
| 激活显存 (bs=4, seq=1536) | ~1.8-2.2 GB | gradient checkpointing + SDPA；marker gather 开销可忽略 |
| CUDA context 与碎片 | ~1.2 GB | 已设 expandable_segments:True |
| **预估总显存** | **~6.7-7.3 GB** | 16GB T10 宽裕（Track A 同口径实测峰值 7,965 MB 可交叉参照） |

- **耗时**：与 Track A 同量级（同一 forward 主干，只多 [B, max_opts, H] gather + 一个 Linear，无自回归生成）。按 Track A 冒烟实测（bs2、seq1024，40 step / 4,000 样本 163 s）折算，全量 50,033 行 × 2 epoch 约 **2.8-3.5 小时**（估算；正式数字以 train-manifest.json 为准）。
- 蒸馏行额外开销可忽略（soft 只是把 one-hot 换成分布，KL 与 CE 同一次前向）。

## 13. 与 Track A 对比

| 维度 | Track A（单字母 SFT） | Track B（候选评分头） |
|---|---|---|
| 输出形态 | 末位生成一个字母 token | 每选项 scalar + 题内 softmax |
| 变长候选 | 2-26（A..Z 上限） | 2-26（同样按视图规则跳过 >26） |
| 字母/位置先验 | 有（字母频率 + 位置偏置） | 无字母先验；顺序偏置可用 --shuffle-options 消融 |
| 软标签蒸馏 | 不支持（one-hot） | 原生支持（KL(T) + λ 混合） |
| 概率读出 | 需从字母 token 分布提取 | 直接题内 softmax，便于温度校准 / ECE / Brier |
| score 序数语义 | 丢失（无序类别） | 仍为无序类别 CE（CORAL/CORN 序数留 v1.1 消融） |
| tokenizer 要求 | 字母必须单 token | 无特殊要求（marker 为普通文本，分段 tokenize 定位） |

## 14. 已知限制

1. **>26 选项仍跳过**（与 Track A / 训练视图一致；视图统计 choice 的 4.5% 行 >26 选项，另行处理）。
2. **位置（选项顺序）偏置**：默认按视图原顺序；--shuffle-options 开启后每 epoch 重 tokenize（时间代价见 §10）。
3. **score 题仍是平的类别 CE**，不建模档位距离（序数回归留待 v1.1）。
4. **蒸馏 soft 的选择偏差**：jev-probs 是"教师判定与语料答案一致"的一致子集，只作行为先验，绝不用于校准参照（校准参照仅 calibration 分区的 reference_probability）。
5. --soft-temperature 是**蒸馏**温度；温度校准链路（validation 派生校准子集拟合 T、报告 ECE/Brier）属后续任务，不在本模块。
6. fp16 + GradScaler（Turing 无 bf16）；本轮只做 CPU 单测 + dry-run + CPU 微型训练验证，真实 GPU 训练由 Lead 执行。
7. transformers 5.20.2 下 meta-device 前向不可用（masking_utils 对 meta 张量调用 .item()），因此 dry-run 的前向形状校验使用随机初始化 tiny 模型而非真实架构 meta 实例。

## 15. Track B 离线单元测试

纯 CPU、离线、不下载权重（tiny Llama 随机模型：hidden 32 / 2 层 / 2 头 / intermediate 64 / vocab 128）：

    python -m unittest finetune.test_decision_scorer -v

静态语法校验：

    python -m py_compile finetune/decision_scorer.py finetune/train_decision_scorer.py finetune/test_decision_scorer.py

覆盖：marker 定位/option_count、左截断与确定性、padding mask、masked softmax/CE/KL 手算对照（含温度）、DecisionScorer 前向形状与梯度回传、LoRA 挂载、head 保存/加载、仓库内 output-dir 与保留集文件名护栏、--dry-run 合成数据全路径。

## 16. 校准与预注册评测协议

- 评测口径、阈值与统计规则见 [EVAL-PROTOCOL.md](EVAL-PROTOCOL.md)（阶段二预注册 v1）。
- 温度缩放工具：`finetune/calibrate.py`（纯标准库）

~~~bash
# 1) 导出逐行预测（含 candidate_probs）
python finetune/eval_decision.py --eval-view <validation-view.jsonl> --adapter <adapter> \
  --batch-size 32 --predictions <evals>/val-preds.jsonl
# 2) 在 validation 的 calibration 半区拟合温度
python finetune/calibrate.py fit --predictions <evals>/val-preds.jsonl --out <evals>/temperature.json
# 3) 在 selection 半区复算指标，并在 test 预测上复核（不重拟合）
python finetune/calibrate.py apply --predictions <evals>/val-preds.jsonl --temperature <T> --half selection --json
~~~

校准切分是确定性的：`sha256(rid)` 奇偶分到 calibration / selection 两半，测试覆盖；不使用软标签（jev-probs）作为校准参照。

## 17. 暂停期新增工具（CPU-only）

- [EVAL-PROTOCOL.md](EVAL-PROTOCOL.md)：阶段二预注册评测协议（划分/指标/阈值/统计/报告规则）。
- [TRACK-B-PLAN.md](TRACK-B-PLAN.md)：Track B 候选评分头的预注册配置与成功判据。
- `calibrate.py`：温度缩放（半 B 拟合 / 半 A 复算，NLL/Brier/ECE/MCE）。
- `collect_results.py`：把决策评测 JSON + lm-eval JSON + 逐行预测汇总成结果卡表格（含配对 bootstrap 95% CI）。
- `run_plan.py`：为 GPU 恢复生成分阶段 bash 脚本（env-check / base-test / lm-eval / calibrate / track-b-smoke / track-b-full / seeds）。
- `eval_decision_scorer.py`：Track B（adapter + scorer_head）独立评测；与 Track A 评测同口径输出 JSON，并可导出逐行概率供校准。
- `collect_results.py --seed-eval`：多 seed 汇总（均值 ± 95% CI，t 分布）。
- `datasets/general/build_mixed_view.py`：通用视图与专用视图按比例混合（mix-1，输出仓库外 + manifest）。
- `run_plan.py --stages pol2-mix --pol2-ratio 0.1`：PoL2 混合训练一键链（builder 自带 training_approved 门禁；未批准会第一步失败）。


~~~bash
# GPU 恢复后：生成整套脚本并执行
python finetune/run_plan.py --stages all --out /tmp/resume.sh
# 汇总结果卡表格
python finetune/collect_results.py --eval-json base=... --eval-json tuned=... \
  --lm-eval-json base=... --lm-eval-json tuned=... --preds base=... --preds tuned=... --out summary.md
# 多 seed 汇总（同 LABEL 重复给多个 seed 的评测 JSON；输出均值 ± 95% CI）
python finetune/collect_results.py --seed-eval track-a=seed20261023.json \
  --seed-eval track-a=seed20261024.json --seed-eval track-a=seed20261025.json --out seeds.md
~~~

**lm-eval 环境注记（2026-10-23 实测）**：WSL 评测环境使用 lm-eval 0.4.13；cmmlu 数据集脚本要求 `datasets>=3.6,<4` 并传 `--trust_remote_code`（当前 pin 3.6.0）。已验证：四任务家族（ceval-valid / cmmlu / mmlu / agieval）在 CPU 上以真实 Qwen3-1.7B 各 limit=1 端到端跑通；真实 adapter + PEFT 加载亦通过。**注意**：若曾用 datasets 5.x 预取过任务数据，HF datasets 缓存会写入新版 feature 编码（`List`），datasets 3.6 读取会报 `Feature type 'List' not found`；需清空 `~/.cache/huggingface/datasets` 下对应缓存（可重新下载）。其余任务若因版本不可用，按 EVAL-PROTOCOL §3.3 规则在结果卡显式注明。

**Track B 评测（训练完成后）**：

~~~bash
python finetune/eval_decision_scorer.py --eval-view <validation/test-view.jsonl> \
  --model <底座> --adapter-dir <run>/adapter --head-path <run>/scorer_head.pt \
  --batch-size 16 --device cuda --json --predictions <仓库外>/track-b-preds.jsonl
~~~

## 18. 最终评测包（阶段三，2026-10-27；**历史，已归档 2026-10-28**）

> **归档说明**：该评测链服务于 **general v5 通用 FT** 线（非目标所需的 POL2 专有微调），已随该线归档；脚本移到 `finetune/archive/2026-10-27-general-ft-eval/`，结果在 `results/archive/2026-10-27-general-ft/`。以下内容仅作工程参考，不再作为当前主线维护。

retained-holdout 最终评测的执行链全部是纯标准库脚本，GPU 只用于模型推理：

- `final_eval_aggregate.py`：吃 base/tuned 两个逐行预测 JSONL（`eval_decision.py --predictions` 的输出），产出**只含聚合数字**的 `aggregate.json`（schema `pol-final-eval-aggregate-v1`）：整体/分层准确率 + Wilson CI、配对 bootstrap（item 与 **group-cluster** 两种，簇 = rid 的 `#` 前缀）、校准（raw / calibrated 的 NLL/Brier/ECE/MCE + 15 箱分箱与样本不足标记）、覆盖率与缺失行口径；
- `check_aggregate_export.py`：隔离环境的**唯一出口闸门**——对聚合 JSON 做结构白名单 / 禁键 / 枚举 / 数值自洽 / 体积与文本扫描，未通过不得带出；
- `bench_latency.py`：batch=1/16 的单题 p50/p95、tokens/s、峰值显存（CPU 可跑，GPU 实测待 owner 开启）；
- `prepare_eval_package.py`（已归档）：把评测所需脚本按原目录布局复制到 `results/archive/2026-10-27-general-ft/final-eval/eval-package/`，生成 `MANIFEST.json` + `CHECKSUMS.sha256`；`--check` 可用于集成前漂移检查。

~~~bash
# 1) 包生成 / 漂移检查（在仓库根执行）
python finetune/archive/2026-10-27-general-ft-eval/prepare_eval_package.py --versions results/archive/2026-10-27-general-ft/final-eval/versions.json \
  --out results/archive/2026-10-27-general-ft/final-eval/eval-package --force     # 生成
python finetune/prepare_eval_package.py --versions results/MODEL-02-final-eval/versions.json \
  --out results/MODEL-02-final-eval/eval-package --check     # 集成门禁：pass 才允许提交
# 2) 隔离环境内聚合（评测者在库外执行；输出只有聚合数字）
python -m finetune.archive.2026-10-27-general-ft-eval.final_eval_aggregate --preds base=/tmp/priv-eval/base-preds.jsonl \
  --preds tuned=/tmp/priv-eval/tuned-preds.jsonl --view-rows <视图行数> \
  --fit-preds /tmp/priv-eval/val-preds.jsonl --fit-half calibration \
  --cluster-rounds 10000 --out /tmp/priv-eval/aggregate.json
# 3) 导出前检查（唯一允许带出隔离环境的文件）
python -m finetune.archive.2026-10-27-general-ft-eval.check_aggregate_export --in /tmp/priv-eval/aggregate.json --json
~~~

评测口径、执行方式与验收清单见 [归档评测包 README](../results/archive/2026-10-27-general-ft/final-eval/eval-package/README.md)；数据边界见 [datasets/README.md](../datasets/README.md)。**保留集内容不进仓库、日志或训练上下文；温度只在 validation 拟合，保留集只 apply。**
