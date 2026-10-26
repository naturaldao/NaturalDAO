# PoL2 score-v2 决策数据

- ID / 版本：`pol2-score-v2` / `v1.0.0-rc1`
- 来源 / 许可：POL2 原创内容遵循 PoL-Governance 当前许可；MRI 通用回放遵循 MIT
- 内容位置：GitHub Release `pol2-score-v2-v1.0.0`
- 语言：中文
- 任务原语：`choice` / `noul` / `score`
- 生成方法：POL2 场景生成、白名单过滤、双模型独立答案、分歧隔离和结构去重
- 人工审阅：未达到 human expert gold；不得写成专家金标

## 范围

这是 Laya/Kev score 0–4 微调实验所使用的数据快照，包含：

- POL2 专项训练、validation、calibration 和已使用的 score-development；
- 875 个新增 score 单元；
- MRI-derived 通用决策回放 M10/M25/M40；
- 可直接训练的 M10 混合导出。

完整数据不在 Git 历史中，下载地址和 SHA-256 见
[`manifests/full-release.json`](manifests/full-release.json)。

## 数据边界

1. Laya/Kev 文件是训练适配器导出，不是本目录 canonical `case/questions/answers/labels` 四层数据的替代。
2. 旧 300 条 score 数据已用于多轮开发，只能作为 development；
3. sealed/fresh blind 不进入本目录；
4. validation 和 calibration 不跨族混用；
5. AI 辅助答案不是 human expert gold；
6. 场景是合成的，但包含胁迫、歧视、隐私冲突、伤害等敏感内容。

## 行数

| 文件 | 行数 |
|---|---:|
| `train-m0`，Laya/Kev 各一份 | 6,166 |
| validation，Laya/Kev 各一份 | 1,162 |
| calibration，Laya/Kev 各一份 | 1,051 |
| score-development，Laya/Kev 各一份 | 354 |
| score-v2 new units，Laya/Kev 各一份 | 875 |
| general replay M10 / M25 / M40 | 661 / 1,971 / 3,942 |
| general validation / guard | 288 / 244 |
| mixed M10，Laya/Kev 各一份 | 6,827 |

同一案例出现在 Laya 和 Kev 两份文件中时只算一个案例。

## 样例

`samples/` 包含 20 条专项和 20 条通用样例，Laya/Kev 成对提供：

- `specialist-laya.jsonl` / `specialist-kev.jsonl`
- `general-replay-laya.jsonl` / `general-replay-kev.jsonl`

这些样例含问题和正确答案，可用于检查 loader 与 target 格式。

## 校验

完整 Release 包内含：

```text
CHECKSUMS.sha256
scripts/validate_public_release.py
```

下载后运行：

```bash
sha256sum -c CHECKSUMS.sha256
python3 scripts/validate_public_release.py
```

训练结果随 `pol/MODEL-02/kev-pol2-m10` 分支提交到 `results/MODEL-02-kev-pol2-score-v2-20261026/`。

## 已知限制

- 专项标签由模型辅助交叉核验，不是多人人工共识；
- 本轮数据比例面向模型实验，不等于正式 benchmark 的 70/20/5/5；
- fresh blind 已一次性使用，不能继续冒充未见测试；
- 通用回放不能代表所有中文决策任务；
- 不得用单点 one-hot 冒充真实标注分布。
