# Track B 预注册方案（候选评分头，2026-10-23）

> 状态：代码就绪（19 个 CPU 单测 + dry-run 通过），GPU 训练待 owner 开启。
> 本文件在第一次 Track B GPU run 之前冻结；改配置必须先改本文件并说明原因（预注册）。

## 1. 方法

- 底座：Qwen3-1.7B（与 Track A 同底座，便于对照）+ PEFT LoRA（r16 / alpha32 / dropout 0.05 / all-linear）+ 新 pointer head（Linear(hidden→1)，全参）。
- 输入模板 tv-1b：`row.prompt` 按最后一个「【选项】」切出情境/问题段（与 tv-1 字节一致），丢弃字母选项段，追加每选项一行 `OP: <label>`；评分锚点 = 每个选项行的**最后一个 token**（因果 LM 在该位置的 hidden 已看到完整选项文字）。
- 输出：题内 logits[B, max_opts] → masked softmax（padding −1e4）→ 交叉熵；distillation 行加 KL（T=2，λ=0.3）混合。
- 跳行：>26 选项行与超长截断行跳过并计数（与 Track A / 视图口径一致）。

## 2. 运行配置（预注册）

| 参数 | smoke | full |
|---|---|---|
| train 行数 | 前 4,000 | 全量（>26 选项跳过，约 50k） |
| epochs | 1（--max-steps 40） | 1 |
| batch × grad-accum | 8 × 4（有效 32） | 8 × 4（有效 32） |
| seq len | 1024 | 1024 |
| lr（head 为 5×） | 1e-4 | 1e-4 |
| λ_soft / T | 0.3 / 2.0 | 0.3 / 2.0 |
| eval | 200 行 / step 20 | 500 行 / step 400 |
| seed | 20261023 | 20261023 |

显存/时长（估算，先以 smoke 实测为准）：1.7B LoRA + pointer head fp16 约 **7–9 GB**；全量 1 epoch 约 **2.5–3.5 h**（RX 7900 XT / ROCm）。

## 3. 成功判据（先声明）

在 **validation（7,887 行同口径）** 上，与同底座 0-shot、Track A 对照：

1. **主指标**：整体 letter accuracy **≥ Track A（0.7883）**；若 <，记录为负结果，不挑子集硬讲；
2. **校准**：calibrated ECE ≤ Track A 的 calibrated ECE，且 NLL 更低（温度在 calibration 半区拟合，同 Track A 流程）；
3. **通用能力**：lm-eval（ceval-valid/mmlu/agieval，limit 100）降幅不差于 Track A（平均下降 ≤2pt 为警戒线，≥5pt 判失败）；
4. **失败也交付**：无论结果如何，写结果卡（配置、数据 sha、指标、显存/时长、失败情况），不隐藏负结果。

test 分区只做回归，不参与选型；private benchmark 不触碰。

## 4. 评测流程（与 EVAL-PROTOCOL 一致）

1. Track B smoke（4,000 行 / 40 步）→ 看 loss/显存/吞吐，确认无 OOM；
2. Track B full（1 epoch）→ 保存 adapter + scorer_head.pt + train-manifest.json；
3. validation 全量评测：`finetune/eval_decision_scorer.py`（与 Track A 同口径 JSON；`--predictions` 导出 candidate_probs）→ 与 Track A、0-shot 同表；
4. 温度校准（calibrate.py，半 B 拟合 / 半 A 复算）；
5. lm-eval base/adapter；
6. 结果卡：`results/MODEL-02-qwen3-1.7b-track-b/CARD.md`。

## 5. 已知风险

- 位置/顺序偏置：选项顺序固定；Track B 增加 `--shuffle-options` 消融（每 epoch 重 tokenize，代价高），首轮先不开启；
- score 题按类别处理，未建模档位距离；
- 软标签来自一致子集（jev-probs），只作行为先验，不当校准参照；
- 选项 >26 未覆盖（占 choice 4.5%），长选项题仍是弱点。

## 6. 命令入口

~~~bash
# 在 WSL 项目环境（~/src/polgov/.venv）
python finetune/train_decision_scorer.py --train-view "$HOME/src/polgov/data/general-train-view.jsonl" \
  --eval-view "$HOME/src/polgov/data/general-validation-view.jsonl" \
  --model "$HOME/src/polgov/models/Qwen3-1.7B" \
  --output-dir "$HOME/src/polgov/runs/track-b-smoke" --limit 4000 --max-steps 40 \
  --batch-size 8 --grad-accum 4 --seq-len 1024
# 或用规划器生成整套脚本（含 restore 后顺序）
python finetune/run_plan.py --stages track-b-smoke,track-b-full --out /tmp/trackb.sh
~~~
