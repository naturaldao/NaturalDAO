# 阶段二评测协议（预注册 v1，2026-10-23）

> 运行任何 GPU 评测前先冻结本协议；报告只按本协议的口径与阈值解释。
> 目标：让「微调是否让决策更准、是否伤通用能力、概率是否可校准」有可复现、不可事后挑选的判据。

## 1. 范围与主张边界

阶段二只回答三件事（SPEC 第 2–3 阶段的对齐）：

1. **决策能力**：在同一数据分布上，微调后是否比同底座 0-shot 基线更准、误拦更少；
2. **通用能力保持**：在预选代理上是否没有明显下降（只写「非劣」区间，不写「智力不降」）；
3. **概率可用性**：候选概率经温度缩放后是否可校准，能否支撑有限自动处置/风险-覆盖。


### 1.1 默认评测范围（2026-10-27 确认）

默认评测只做**我们自己的 general v5** 上的 pre/post 对比，**不包含任何专有或协作者专项数据**：

1. **主对比**：同底座、同 prompt、同评测代码、同数据视图 sha，base 0-shot vs 微调后 adapter；
   - public test 视图（16,306 行）只做回归；validation 视图（8,177 行）做选型/校准；
   - 私有 benchmark（6,541 条，库外）做定版后的独立评测；
2. **通用能力保持**：lm-eval 四任务 base vs adapter（阈值见 §4；只写「在所选代理上」）；
3. **校准**：temperature 只在 validation 半 B 拟合、半 A 复核；test 与保留集只 apply。

**不在默认范围**：POL2 冻结集、POL2 score-v2、EVAL-02/EVAL-03 的具身/理论数据、其他协作者专有数据。
这些只在 owner/协作者书面授权后作为**单独预注册实验**，结果不得与本协议的表混排。

### 1.2 与协作者数据/结果的关系

- 协作者使用的通用数据集与我们的 v5 不完全相同（版本/来源/划分不同）——这是**预期情况**，不影响我们在自己数据上的标准化对比；
- 我们只在自己的 v5 上做「同一模型微调前后」的对比；协作者数据上的数字只作**外部参照**，引用时注明其数据版本/revision/协议差异；
- **后续模型选型与迭代一律来自我们自己的 v5 训练视图**；外部数据不参与我们的选择。

---
不能声称：现实伤害减少、自动伦理裁决、跨语言/跨人群普适、模型「理解」爱恨、无限泛化——这些需要阶段四端到端对照或独立保留集。

## 2. 数据与划分

| 数据 | 用途 | 硬约束 |
|---|---|---|
| general v5 train 视图（51,947 行） | 训练 | 只用 train；drop 路由剔除 |
| general v5 validation 视图（8,177 行） | 选模型 + 校准拟合 | 与 test 不混用；同一结果不重复挑选 |
| general v5 test 视图（16,306 行） | **只做回归** | 不用于梯度、教师生成、阈值选择；反复依据 test 改方案必须披露 |
| private benchmark（6,541 条，库外） | 定版后独立评测 | 不进任何分支/日志/训练上下文 |
| PoL2 冻结集 | **暂停** | training_approved=false 前零梯度；blind 内容不进入公开路径 |

视图口径：train 51,947 / validation 8,177 / test 16,306（问题行 − drop）；**>26 选项行**与**超长 prompt**（>4,000 字符）在训练/评测中跳过并计入 skipped，分母不含它们。视图 sha256 记录在各自 manifest，评测结果卡必须带视图 sha。

### 2.1 validation 的两半用法

评测前用 **sha256(rid) 的奇偶** 把 validation 固定切成互斥两半（不随机、不再变）：

- A 半（selection，约 50%）：选模型/超参/温度范围之外的决策（只看指标，不拟合）；
- B 半（calibration，约 50%）：**只**用于拟合温度缩放参数（标签分布与 A 不混用）；
- 阈值/自动动作的风险上限在 A 半预注册，B 半复核。

校验命令：两次切分应得到同一组 rid（脚本测试覆盖）；切分结果写进结果卡。

## 3. 指标

### 3.1 决策能力（主指标）

- 整体 letter accuracy（Track A 用 `eval_decision.py`；Track B 用 `eval_decision_scorer.py`，两者输出同键名 JSON + 逐行 predictions）；
- 分层：kind（choice/noul/score）、lang（en/zh）、选项数桶（2 / 3-4 / 5-8 / 9-26）、route（classification/distillation）；
- 缺失/失败行计入分母（不补齐、不推断），与 benchmark/pol2 评测器口径一致；
- 同时报告 0-shot 基线（同底座、同 prompt、同子集）与差值。

### 3.2 校准（概率）

- 温度缩放：p_T = softmax(log p / T)，T 只在 calibration 半拟合；
- 指标：NLL、Brier（多类平方误差和均值）、ECE（等宽 15 箱、按样本量加权）、MCE；
- 报告 raw（T=1）与 calibrated 两套；校准前后 accuracy 必须不变（单调变换，仅作 sanity check）；
- 风险-覆盖（可选）：按最大类概率降序的 coverage-error 曲线与 AURC；
- **不得**用 jev-probs 软标签当校准参照（一致子集偏差，见 TRAINING.md §4.6）。

### 3.3 通用能力（防遗忘代理）

- 工具：lm-evaluation-harness 0.4.x（WSL 评测环境：lm-eval 0.4.13 + **datasets 3.6.0**（cmmlu 脚本需要）+ `--trust_remote_code`；torch/transformers/peft 见 README §3）；
- 任务：ceval-valid、cmmlu、mmlu、agieval，**每任务 limit 100**（先跑小样本保时间，结论只写「在所选代理上」）；
- 若某任务因数据集/依赖版本不可运行（如 cmmlu 需要 datasets<4 与 `--trust_remote_code`），必须在结果卡**显式注明**并用剩余任务均值，不得静默省略或替换成更容易的任务；
- 对照：同底座 0-shot vs adapter，同 prompt 模板（base 模式生成，不用决策头）；
- 指标：各任务 accuracy 与 4 任务平均；报告原始值与差值。

### 3.4 成本与延迟

- 固定硬件：RX 7900 XT 20GB（WSL2 + ROCm 7.2.1 + PyTorch 2.9.1+rocm7.2.1）；
- 报 p50/p95 单题延迟（batch=1 与 batch=16 各一次）、tokens/s、峰值显存、每千次决策成本（GPU 时长折算）。

## 4. 预注册阈值（先声明，后看结果）

| 判定 | 阈值 | 处理 |
|---|---|---|
| 决策提升「有意义」 | test 整体 +5pt 且 95% CI 不重叠（与 0-shot） | 记为有效提升 |
| 通用能力「警戒」 | 4 任务平均降 ≥2pt 或任一任务降 ≥5pt | 降 LoRA rank/epoch，重新训练 |
| 通用能力「明显下降」 | 4 任务平均降 ≥5pt | 判失败，回滚配置 |
| 校准可用 | calibrated ECE ≤0.05 且 NLL 下降 | 可讨论有限自动处置 |
| 误拦（PoL2 批准后） | XSTest 过拒率相对基线 +5pt 以上 | 判回退 |

盲测/保留集评测只发布汇总；单次比较必须带 CI 与样本量。

## 5. 统计协议

- 至少 **2–3 个 seed**（种子集合预注册：20261023 / 20261024 / 20261025）；
- 报告均值 ± 95% CI（Wilson 区间用于比例；配对 bootstrap 1000 次用于 base-vs-adapter 差值；跨 seed 聚合用 `collect_results.py --seed-eval`，t 分布 CI，n=1 不给 CI）；
- 分族相关：general v5 按组切分，视图行同族/同 state 存在相关性；item-level bootstrap 会低估 CI，结果卡必须注明「近似 CI，未做 group-cluster bootstrap」；
- 不做事后挑选（不能先看 test 再决定报告哪个 seed/任务/阈值）。

## 6. 执行顺序（评测可在授权时段使用 GPU；训练需 owner 重开）

~~~powershell
# 0) 确认评测授权（已获）与静默时段/温度；训练不在本协议授权内
# 1) test 的 base 0-shot（同口径）
wsl -d Ubuntu-24.04 -- bash <仓库>/.agent/scratch/run_eval.sh "" <数据>/general-test-view.jsonl <输出>/base-test.json
# 2) adapter 的 test（若尚未跑）
wsl -d Ubuntu-24.04 -- bash <仓库>/.agent/scratch/run_eval.sh <adapter> <数据>/general-test-view.jsonl <输出>/track-a-test.json
# 3) lm-eval base 与 adapter（limit 100）
lm_eval --model hf --model_args pretrained=<模型>,dtype=float16 --tasks ceval-valid,cmmlu,mmlu,agieval --limit 100 --batch_size 8 --trust_remote_code --output_path <输出>/lm-eval-base
lm_eval --model hf --model_args pretrained=<模型>,peft=<adapter>,dtype=float16 --tasks ceval-valid,cmmlu,mmlu,agieval --limit 100 --batch_size 8 --trust_remote_code --output_path <输出>/lm-eval-track-a
# 4) 校准：导出 predictions（--predictions），在半 B 拟合温度，半 A 复核
# 5) 多 seed 重训（Track A / Track B 各 2–3 seed）
~~~

### 6.1 执行授权与 GPU 时间窗（2026-10-27/28）

- **私有保留集**：已授权**方式 2（本机隔离执行）**（owner 2026-10-27 14:06；2026-10-28 再次确认持续有效）。私有数据只在仓库外，只回传聚合 JSON，执行后删除临时副本；不进入仓库/日志/截图/训练上下文。
- **GPU 评测**：owner 授权可用于评测（adapter lm-eval、validation 逐行预测/校准、延迟、保留集推理）。约束：北京时间 **00:30–09:30 与 12:30–15:30 不启动 GPU**；单卡、一次一个任务；每次 run 前后检查温度与 Kernel-Power 41 / BugCheck 1001 / WHEA；T10 已物理移除，不开双卡。
- **训练不在授权内**：2026-10-27 起本阶段训练线收尾；多 seed 重训与 rank-8 处置实验已由 owner 停止（单 seed 交付）。Track B 未训练；agieval 单任务警戒（adapter -10.8pt，已复现）为已知限制，待 owner 决定处置。
- 最终评测执行与数字见 [results/MODEL-02-final-eval/CARD.md](../results/MODEL-02-final-eval/CARD.md)。

## 7. 报告模板（结果卡必须包含）

1. 数据版本、视图 sha256、有效行数与 skipped 分布；
2. 模型/底座 revision、LoRA 配置、训练步数/时长/峰值显存、seed；
3. base vs tuned 的决策指标（含分层）与差值 CI；
4. 校准（raw/calibrated 的 NLL/Brier/ECE）；
5. 通用能力代理（4 任务 + 均值）；
6. 成本/延迟；
7. 失败与未测项（不填 0、不省略负面结果）；
8. 公开测试是否影响过模型/提示/阈值选择；独立保留集评测者与定版 revision。

## 8. 版本与变更

- 本协议 v1（2026-10-23）在 Track A 全量评测后、test base 对照/lm-eval/Track B 之前冻结；
- 任何阈值或口径变更必须在变更前写入任务页与结果卡，并说明原因；旧结果不追溯改口径。
