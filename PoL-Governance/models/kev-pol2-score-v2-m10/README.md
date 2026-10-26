# Kev-4B POL2 Score-v2 M10

- ID：`kev-4b-pol2-score-v2-m10`
- 状态：**研究候选（release review）**，不是生产认证
- 底座：`Qwen/Qwen3.5-4B-Base`，revision `1001bb4d826a52d1f399e183466143f4da7b741b`
- 起点：Kev-4B adapter/pointer head
- 适配方式：LoRA + pointer head
- 训练数据：`pol2-score-v2`（随 `pol/DATA-02/score-v2` 分支提交）
- 权重：GitHub Release `pol2-score-v2-v1.0.0`
- 结果：[结果卡](../../results/MODEL-02-kev-pol2-score-v2-20261026/README.md)

## 交付内容

Release 包含同一配方的三个随机种子：

| Seed | Development | Fresh blind | 用途 |
|---|---|---|---|
| 17 | FAIL | PASS | 研究变体 |
| 29 | PASS | FAIL | 研究变体 |
| 43 | PASS | PASS | 默认推荐候选 |

seed43 是看到全部结果后选出的唯一双门通过版本，必须保留这一披露。三个 seed 不是三个运行组件；运行时选择其中一个 adapter 和对应 head。

## 训练配置

- 1 epoch；
- bf16 backbone，fp32 head；
- LoRA rank 16 / alpha 32，targets 覆盖 Qwen/Kev 主干模块；
- pointer-head hidden width 256；
- batch 1，gradient accumulation 4；
- learning rate `2e-5`；
- max state 4096；
- M10 训练 6,827 个决策单元；
- 硬件 NVIDIA GB10；
- 每个 seed 训练约 61 分钟，含完整评测约 2.5 小时。

## 安装

模型权重不进入 Git 历史。下载：

```text
https://github.com/naturaldao/NaturalDAO/releases/download/pol2-score-v2-v1.0.0/kev-pol2-score-v2-m10-all-seeds.tar.gz
```

校验和解压：

```bash
sha256sum kev-pol2-score-v2-m10-all-seeds.tar.gz
# 28a8d407573c1cc26ce16e421c0bb825c8792ebf4a9fc8a759de656885821b4b
tar -xzf kev-pol2-score-v2-m10-all-seeds.tar.gz
cd kev-pol2-score-v2-m10
sha256sum -c SHA256SUMS
```

还需要按上游 revision 准备 Qwen3.5-4B-Base 与 Kev 运行依赖。底座不属于本 Release。

## 推理

```bash
python infer.py \
  --run ./seed-43 \
  --input cases.jsonl \
  --output predictions.jsonl
```

输入为 Kev typed-decision JSONL，包含 `state` 和 `questions`，不要求含答案。输出为每个问题的概率和 argmax。

## 公平比较

- 不把 seed17/29 删掉后再宣称配方稳定；
- 不把 development 当 blind；
- 不把 268 条 blind 当完整生产分布；
- 不把三个 seed 平均结果说成 ensemble；
- 不把模型输出直接当高风险事务批准。

## 许可

- 本仓库代码和文档遵循 PoL-Governance 当前许可；
- Qwen 底座、Kev 代码/权重和训练数据分别保留各自许可；
- MRI-derived replay 保留 MIT；
- 权重发布前需完成模型卡、许可和数据卡联合审核。
