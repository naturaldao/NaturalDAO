# Kev POL2 score-v2 M10 结果卡

- 任务 / 分支 / 领取人：MODEL-02 / `main` / w609641894 + Codex
- 模型：`kev-4b-pol2-score-v2-m10`
- 底座：`Qwen/Qwen3.5-4B-Base@1001bb4d826a52d1f399e183466143f4da7b741b`
- 方法：Kev LoRA + pointer head，1 epoch
- 数据：`pol2-score-v2` M0/M10，seeds 17/29/43
- 硬件：NVIDIA GB10；bf16；每 seed 完整训练+评测约 2.5 小时

## 对照

| Seed | M0 specialist macro-F1 | M10 specialist macro-F1 | Development | Fresh blind |
|---|---:|---:|---|---|
| 17 | 0.740944 | 0.729701 | FAIL | PASS（56.72% → 61.19%） |
| 29 | 0.738924 | 0.732926 | PASS | FAIL（61.19% → 55.97%） |
| 43 | 0.733785 | 0.736192 | PASS | PASS（58.21% → 58.96%） |

Development 判决：`APPROVE_FOR_FREEZE`（2/3）。  
冻结后一次性 fresh blind：`APPROVE_FOR_RELEASE_REVIEW`（2/3）。

## 关键限制

- 三 seed blind 平均准确率都是 58.71%，因此不能宣称平均提升；
- seed29 的两个 fresh family 分别下降 12.5pp 和 17.24pp；
- seed43 是唯一同时通过 development 与 blind 的 seed，但为事后选择；
- 本轮 fresh blind 已消费，不能再用作未见测试；
- `training_approved=false`、`expert_gold=false`；
- 本结果是研究/发布评审证据，不是生产安全认证。

逐项汇总在 [`metrics.json`](metrics.json)，环境和训练参数在 [`run.json`](run.json)。
