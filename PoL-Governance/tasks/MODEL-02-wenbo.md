# [MODEL-02] 决策模型适配：封闭原语微调与防遗忘评估

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 进行中（GPU 暂停）；Track A 基线完成：validation 0.5127→0.7883、test 0.5047→0.7785；lm-eval base 完成（均值 0.5342）、adapter 侧被 10-23 崩溃中断待重跑；PoL2 未批准训练前零梯度 |

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
2026-10-23｜Wenbo / DSH Agent Team｜按 owner 指示切换到 **RX 7900 XT（WSL2 + ROCm 7.2.1 + PyTorch 2.9.1+rocm7.2.1，`~/src/polgov`）** 为主训练卡（T10 仅备用；GPU 静默时段 00:30–09:30 与 12:30–15:30）。同时给训练脚本加两个优化：`--no-grad-ckpt` 开关与**末位 token 轻量损失**（只对答案位置过 lm_head，避免 [B,L,vocab] 全量 logits）。
2026-10-23｜Wenbo / DSH Agent Team｜**发现并修复轻量损失的标签泄漏**：首版取「标签自身位置的 hidden」预测该 token（teacher forcing 复制，loss 可降到 0.003）；改为取**前一位置** hidden 的 logits（因果 LM 正确口径）后 loss 恢复真实水平。修复后冒烟（4,000 行 / 40 步 / batch 8×grad 4 / seq 1024）：约 6.8s/步、峰值 6.3GB；validation 前 200 行准确率 **0.5100 → 0.6250**（40 步，仅管线验证）。正式 1 epoch 在 RX 7900 XT 上重跑（`~/src/polgov/runs/track-a-e1-rocm`，约 3h）。

2026-10-23｜Wenbo / DSH Agent Team｜**Track B（主路线）代码就绪**：`finetune/decision_scorer.py`（marker 定位 + pointer head + masked softmax/CE/KL）、`train_decision_scorer.py`（LoRA+head、fp16、软标签 λ 混合）、`test_decision_scorer.py`（19 个 CPU 单测全过，tiny 模型）+ dry-run 在真实 validation 视图跑通（marker 位置、padding mask、混合损失形状校验）。GPU 训练待 Track A 完整基线跑完后排期。

2026-10-23｜Wenbo / DSH Agent Team｜**Track A 完整 1 epoch 基线完成**（RX 7900 XT / WSL2 ROCm 7.2.1 / PyTorch 2.9.1）：batch 8×grad-accum 4（有效 32）、seq 1024、lr 1e-4 cosine、seed 20261023；1,564 步、**9,135 s（2.54 h）**、峰值显存 **6,286 MB**。周期评测（validation 500 行）：step400 0.668 / step800 0.758 / step1200 0.792。
2026-10-23｜Wenbo / DSH Agent Team｜**validation 全量评测（7,887 行）**：0-shot **0.5127** → adapter **0.7883（+27.6pt）**；en 0.4589→0.7621；zh 0.9440→0.9977（天花板/位置先验，不能当能力证据）；choice/noul/score：0.5392→0.7869 / 0.3909→0.8499 / 0.2634→0.7299；选项数 2/3-4/5-8/9-26：0.4843→0.8511 / 0.6147→0.8618 / 0.2940→0.6021 / 0.1516→0.3287。
2026-10-23｜Wenbo / DSH Agent Team｜**test 评测（15,573 行）**：adapter **0.7785**；en 0.7514 / zh 0.9931；choice 0.7780 / noul 0.8450 / score 0.7069。跳过 >26 选项 656 行与超长 prompt 77 行；**base 0-shot 对照未跑**。
2026-10-23｜Wenbo / DSH Agent Team｜**GPU 实验按用户要求暂停**，等待设备调整后继续。代码/视图/结果卡/报告已提交到 `pol/MODEL-02/wenbo`；恢复后顺序：test base 对照 → lm-eval → Track B 全量 → 校准 → 多 seed。结果卡：`results/MODEL-02-qwen3-1.7b-track-a-full/CARD.md`；阶段报告：`docs/reports/2026-10-23-phase2-track-a.md`。

## 交付或交接

- 待交付：训练视图生成脚本、Track A/B 训练入口与配置、结果卡（模型版本/数据 fingerprint/硬件/预算/指标区间）、失败与限制记录
- 复现与检查：`uv run --no-project --offline python tools/check.py`；训练与评测命令写入任务页与结果卡
- 纪律：不使用 test 调参；不把 PoL2 冻结集用于训练/教师造数/tokenizer 拟合/阈值选择，直到获得训练批准；通用能力下降只陈述所选代理上的非劣效区间，不宣称"通用智力不降"

2026-10-26｜Wenbo / DSH Agent Team｜**合并协作者更新（main 前进 45 提交）**：新增 EVAL-02 具身推理先导、EVAL-03 完整理论内在化先导、POL2 score-v2 数据与 Kev-4B pointer-head 模型（研究预发布）。本项目 Track A 线（Qwen3-1.7B 字母 SFT）与其数据/规模/口径不同，**不混表比较**；摘要见 `docs/reports/2026-10-26-collaborator-update.md`。

2026-10-26｜Wenbo / DSH Agent Team｜test base 0-shot 与 lm-eval base 侧结果已在 10-23 崩溃前落盘（test 0.5047→0.7785；lm-eval base 均值 0.5342），adapter 侧被崩溃中断待重跑；详见结果卡与 `docs/reports/2026-10-23-phase2-track-a.md` §7。
2026-10-27｜Wenbo / DSH Agent Team｜**最终评测执行链（阶段三准备）交付**：新增 `finetune/final_eval_aggregate.py`（隔离环境内聚合：整体/分层准确率 + Wilson CI、配对 item 与 **group-cluster bootstrap**（簇 = rid # 前缀，10,000 次）、校准 raw/calibrated + 15 箱分箱与样本不足标记、覆盖率/缺失口径）、`finetune/check_aggregate_export.py`（导出前唯一闸门：结构白名单/禁键/数值自洽/体积与文本扫描）、`finetune/bench_latency.py`（batch=1/16 延迟与峰值显存）、`finetune/prepare_eval_package.py`（可复现打包 + `--check` 漂移门禁），均带纯 CPU 单测。产出 `results/MODEL-02-final-eval/`：CARD（公开 test 回归 0.5047→0.7785 逐位一致；保留集/校准/adapter lm-eval/延迟逐项标「未测 + 门禁」）、versions.json（base@70d244cc、adapter 6 文件 sha256、三视图 sha 复算一致、holdout revision）、eval-package/（脚本 + MANIFEST + CHECKSUMS + 评测者手册）。阶段报告：docs/reports/2026-10-27-final-eval-package.md。
2026-10-27｜Wenbo / DSH Agent Team｜**未执行项与门禁**：私有保留集评测（需 owner 定方式 1 独立评测者 / 方式 2 授权隔离执行）；温度拟合（需 adapter 逐行预测，GPU）；adapter lm-eval（GPU 恢复后 ~30–60 分钟）；正式延迟实测（GPU）。**GPU 仍暂停，本轮只做 CPU 工作，未触碰私有数据。**
2026-10-27｜Wenbo / DSH Agent Team｜**独立审计与修复**：对抗性审计 6 条发现全部处理——导出闸门「delta 双舍入假拒」（合法的 7859/12124/15573 聚合被唯一出口误拒）已修并加回归测试；`coverage.skipped` 键改为 15 个已知原因枚举（堵住把 rid 伪装成跳过原因带出）、模型标签强制 `[A-Za-z0-9._-]{1,24}`、`paired.seed` 加范围、交付脚本本机路径清理。审计记录：`.agent/notes/2026-10-27-final-eval-audit.md`（内部）。

2026-10-27｜Wenbo / DSH Agent Team｜**最终评测完成（方式 2）**：owner 授权后本 session 作为独立评测者在仓库外隔离目录执行私有保留集（6,541 items / 7,990 问题行，en-only；跳过 250、缺失 0）。**base 0-shot 0.3996 → adapter 0.7034（+30.37 pt）**；配对 group-cluster bootstrap 95% CI **[+28.94, +31.75]**（G=6,321，reliability ok）；分层：choice 0.6860 / noul 0.7795 / score 0.6866。只导出聚合（检查器 1,004 项 pass），临时副本已删除。
2026-10-27｜Wenbo / DSH Agent Team｜**校准与防遗忘、成本**：温度 T=0.992077（validation calibration 半区拟合，保留集只 apply）；raw ECE 0.0221 / calibrated 0.0225、NLL 0.75009→0.75050 → 预注册「NLL 下降」未满足（原始概率已校准良好）。adapter lm-eval：ceval 0.6189 / cmmlu 0.5922 / mmlu 0.5911 / agieval 0.3057，均值 **0.5270（-0.7pt）**；**agieval -10.8pt 触发单任务警戒**，处置留 owner。延迟实测：batch=1 p50 44.9/65.0 ms、峰值 4.0/4.1GB；batch=16 更差且 14.6GB → 部署建议 batch=1。
2026-10-27｜Wenbo / DSH Agent Team｜**工程记录**：WSL/ROCm 必须 `HSA_ENABLE_DXG_DETECTION=1`；test 逐行预测 batch 32 触发 dxg ENOMEM（~19.4GB）抖动，改 batch 8 完成。余项：多 seed（20261024/25）、Track B、agieval 警戒处置。
2026-10-27 17:04｜Wenbo / DSH Agent Team｜owner 决定**停止额外重训**（多 seed 20261024/25 与 agieval rank-8 处置实验在 16:14–17:04 进行过一部分，随后终止、半成品删除）。最终交付按**单 seed**：保留集 +30.37 pt（簇 CI [28.94,31.75]）、校准 T=0.992（NLL 未降）、lm-eval 均值 −0.7pt 且 agieval 触发单任务警戒、batch=1 延迟 45–65ms。完整报告见 docs/reports/2026-10-27-final-eval-package.md 与 CARD。
