# [MODEL-02] 决策模型适配：封闭原语微调与防遗忘评估

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 进行中；训练视图已生成、环境已就绪；Qwen3-1.7B + LoRA 冒烟管线通过（40 step），完整 1 epoch 基线运行中；PoL2 未批准训练前零梯度 |

- 更新时间：2026-10-23 UTC+8
- 分支：pol/MODEL-02/wenbo（阶段一数据收尾 PR 后另开）
- 起点 commit / 依赖分支与 commit：main 68105b1（PR #43 合并 v5 之后）；依赖 DATA-03 的通用决策数据集 v5（含 target-types 训练路由与 jev-probs 旁挂件）
- 目标与交付路径：`models/`（训练入口、配置、适配说明）与 `results/`（版本/数据/硬件/预算/结果卡）；训练工作区与权重放仓库外（D 盘），大权重登记 Hugging Face revision
- 本轮改动范围：新增本任务页；后续新增 models/ 下训练入口与 results/ 结果卡；不改动他人已有文件
- 下一步：① 生成训练视图（general train 按 training_route 过滤 + 选项渲染，约 51,947 行） ② Track A 单 token SFT 冒烟（Qwen3-1.7B LoRA，fp16，T10 16GB） ③ Track B 候选评分头 masked CE ④ 通用能力前后对照（lm-eval 中文/英文代理）与校准链路 ⑤ 报告真实结果（含失败）
- 阻塞 / 需要谁帮助：需要用户拍板 PoL2 训练授权（当前冻结集 `training_approved=false`）、底座档位、评测阈值预注册；GPU 只有单张 T10 16GB（Turing，无 bf16），全参与 8B 以上另议
- 环境 / 输出路径 / 资源预算：Windows + uv；训练工作区仓库外 D 盘，`HF_HOME` 指到 D 盘；fp16 + SDPA（Turing 不支持 FA2）；LoRA 路线 1.7B/4B 可在 16GB 内跑
- 数据版本与可用分区：general v5 训练路由：classification 67,522 / distillation 5,760 / drop 1,571（公开分区口径）；只消费 train；test/validation 只做回归与选型；PoL2 冻结集未批准前零梯度

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-10-22｜Wenbo / DSH Agent Team｜第一阶段数据收尾启动（DATA-02/DATA-03），同时规划第二阶段模型适配。完成微调方案调研（内部报告）：推荐 decoder LM（Qwen3 系列）+ LoRA + 候选评分头 masked CE；文本单 token SFT 作最简基线；PoL2 未批准训练前零梯度；通用:PoL 按行 9:1 恰为各一遍 epoch；评测含通用智力代理 + 决策三区 + 校准（ECE/Brier/温度缩放）+ 外部安全基准；阈值预注册（通用代理降 ≥2pt 警戒、≥5pt 明显下降；blind_test 687 只足以判 ≥5pt 差异）
2026-10-23｜Wenbo / DSH Agent Team｜方案定稿并写入内部报告：主路线 Qwen3-4B（或 4B-Instruct-2507）+ LoRA r16 + 候选评分头 masked CE（选项 2–69 可变，固定分类头不可行）；1.7B 先跑通；Laya 322M 作超廉价层；T10 16GB 下 4B LoRA fp16 约 10.5–11.5GB、8B 仅 QLoRA。数据实测：general train 52,999 问题行（drop 后 51,947），choice 选项中位 4 / p90 11 / max 69。下一步：写训练视图 → Track A 冒烟 → Track B → 评测链路
2026-10-23｜Wenbo / DSH Agent Team｜论文与理论对齐（内部两份报告）：论文（163 研究 / 7 灰文，κ=.59）结论只支持「有记录、三值、本地校准的检测器 + 人终结后果性决定」，不支持单独作 judge；中文 PoL2 构念尚无研究测量。阶段二主张必须限定在指定数据/模型/分布上的判定、误拦漏判、校准、覆盖、通用代理非劣与成本；现实伤害/帮助效果留到阶段四

2026-10-23｜Wenbo / DSH Agent Team｜**训练视图（M2-2）完成**：`datasets/general/build_training_view.py`（离线/确定性/仅标准库）+ 6 个离线测试 + [TRAINING-VIEW.md](../datasets/general/TRAINING-VIEW.md)。真实数据：train 50,033 / validation 7,887 / test 15,650 行（= 问题行 52,999 − drop 1,052 − 选项>26 1,914；其中中文补充 3,148 行走 no_route 兜底 classification）；模板 tv-1，视图 sha256 记录在各自 manifest。
2026-10-23｜Wenbo / DSH Agent Team｜**Track A 管线打通**：环境 `D:/pol2-train/.venv`（torch 2.6.0+cu124、transformers 5.20.2、peft 0.21.2，T10 fp16/SDPA）；训练脚本 `finetune/train_decision_sft.py` + 评测 `finetune/eval_decision.py` + 6 个 CPU 单测。冒烟：4,000 行 / 40 step / 峰值显存 7,965MB / 163s，validation 前 300 行 0-shot 0.3833 → adapter 0.4933（+11.0pt，单 seed，仅管线验证）。结果卡见 [results/MODEL-02-qwen3-1.7b-track-a-smoke](../results/MODEL-02-qwen3-1.7b-track-a-smoke/CARD.md)。
2026-10-23｜Wenbo / DSH Agent Team｜**完整 1 epoch 基线启动**（50,033 行、batch 4×grad-accum 8、seq 1024、lr 1e-4、eval-every 400、eval-limit 500）：训练日志与 adapter 在仓库外 `D:/pol2-train/runs/track-a-e1-1.7b`；完成后补结果卡并做 0-shot 同子集对照。

## 交付或交接

- 待交付：训练视图生成脚本、Track A/B 训练入口与配置、结果卡（模型版本/数据 fingerprint/硬件/预算/指标区间）、失败与限制记录
- 复现与检查：`uv run --no-project --offline python tools/check.py`；训练与评测命令写入任务页与结果卡
- 纪律：不使用 test 调参；不把 PoL2 冻结集用于训练/教师造数/tokenizer 拟合/阈值选择，直到获得训练批准；通用能力下降只陈述所选代理上的非劣效区间，不宣称"通用智力不降"