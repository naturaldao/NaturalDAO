# ROADMAP

**目标**：交付可插拔的 PoL 运行时治理层，并让它真正可训练、可评测、可部署。
当前主线是**决策模型**：只做封闭选择（noul 是/否、choice 从候选选一个、score 序数打分）的小模型，要求**不拖累通用智力**，同时更准、更少误拦、可校准、成本可接受。

> 判据是「不拖累」，不是「样样都强」。任何「越大越好 / 越全越好」的表述都是方向错误。

## 总体阶段（对齐 [SPEC](SPEC.md)）

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 | 准备数据：通用底座 + PoL 专项 + 独立标注 + 共享划分 | **完成**（数据收尾 + HF 托管 2026-10-27；集成方式待 owner 决定） |
| 2 | 模型适配：可复现配方、首个基线、控制遗忘 | **进行中**：Track A 基线完成（test base/adapter 同口径）；lm-eval base 完成、adapter 待重跑；评测/校准/混合视图就绪；GPU 暂停（2026-10-23 崩溃后硬件待确认） |
| 3 | 校准盲测：同口径评测、效果与成本、保留集统一评测 | **进行中**：评测包（聚合/导出检查/延迟基准/版本清单）与结果卡就绪，可交独立评测者；公开 test 回归完成；**保留集评测待 owner 定执行方式、adapter lm-eval 待 GPU** |
| 4 | 插件与验证：接入 DSH、试运行、端到端 | 未开始 |

## 第一阶段：数据（收尾）

- [x] P1 语料重建：来源原生四元组、溯源、格式标准化
- [x] P2 切分与保留集：按组切分、私盐、来源均衡
- [x] P3 文档：数据卡、契约、来源登记
- [x] P4 安全：公开面内容级审计 + 注入验证
- [x] P5 概率补全：mercury-decide 原生概率（44,740 行旁挂件）
- [x] P6 能力拓宽：bigbench + cosmos_qa（语料 23,855 → 74,912）
- [x] P7 上线：v5 经 PR #43 并入 main；公开三区 71,519 条 / 78,001 问题，私有保留集 6,541 条库外
- [x] P7b-1 数据集 Hugging Face 导出就绪：公开三区与私有保留集物理分离，清单（MANIFEST）、数据卡、上传手册与下载校验齐备；大文件已从 git 离仓（见 [datasets/general/HF.md](datasets/general/HF.md)）；离线 `verify` 复检通过（公开 7 文件 / 私有包 6 文件 / 包自校验 exit 0）
- [x] P7b-2 实际执行 HF 上传：公开仓库 `NaturalDAO/pol-decision-general-v5`（revision `52bfdca…`）+ 私有保留集仓库（revision `146ae46…`）；远程校验与下载回验通过
- [x] P7c 专用数据落位：POL2-accepted-8705-v1 解压、校验（pack/族级切分/回答一致）、四区物化、数据卡与可复算脚本（见 [datasets/pol2/FREEZE-8705-V1.md](datasets/pol2/FREEZE-8705-V1.md)）；**未批准训练前只做整理与评测准备**；训练前置清单见 [APPROVAL-CHECKLIST](datasets/pol2/APPROVAL-CHECKLIST.md)
- [x] P7d 文档与仓库整理：过时文档归档、内部 Agent 工作区分隔（`.agent/` 不进公开仓库）、大文件离仓、公开文档精简
- [ ] P8 下一轮补源：世界知识 + 因果·反事实（见下）
- [ ] P9 模板命题线退役（见 [目录索引 §7](datasets/general/INDEX.md)）

### P8 规划（补能力偏斜）

**依据**：v5 的能力构成是「换了一种偏斜」——阅读 + 数学合计 71.34%，世界知识 1.74% / 因果 0.83% **比旧来源子集内部更薄**。

| 子项 | 内容 | 验收 |
|---|---|---|
| P8-1 | 筛世界知识类原生决策来源（封闭选项、自带真值、非排行榜基准） | 至少 3 个来源通过，世界知识 → ≥5% |
| P8-2 | 筛因果/反事实类来源 | 因果·反事实 → ≥2% |
| P8-3 | 重跑 build_corpus → split（同一份盐） | 保留集重切需再轮换；派生链全部重生成 |
| P8-4 | 重算数据卡 / 训练路由 / 切分报告 | readme_stats.py --check 0 例外 |

**硬约束**：单一来源 ≤ 25%（折算后）；保留集 en-only；排行榜基准只能当外部评测、不得进训练；任何补源都会触发「重切 → 保留集轮换 → 派生件重生成 → 审计重跑 → 数字重算」。

## 第二阶段：模型适配（当前重点）

| 子项 | 内容 | 验收 |
|---|---|---|
| M2-1 | 模型选型：0.3B–8B、中文、封闭原语、许可清晰、有成熟微调案例 | **完成**：选型报告（内部）；推荐 Qwen3-1.7B 起步 / Qwen3-4B 主力 + LoRA + 候选评分头，文本单 token SFT 作最简基线；Laya 322M 作超廉价层 |
| M2-2 | 训练数据适配：通用决策数据 + POL2 冻结数据 → 统一训练样本；软标签与 a/b 反事实对的用法 | **完成（general 部分）**：`build_training_view.py` 生成 train 50,033 / validation 7,887 / test 15,650 行统一视图（模板 tv-1，可复算）；PoL2 未批准训练前只做 schema，不进梯度：**pv-1 适配器已就绪**（`datasets/pol2/build_pol2_training_view.py` + `POL2-VIEW.md`），当前唯一允许 `--schema-preview`，写盘 build 在 `training_approved=false` 下 exit 2；preview 实测 train 5,900 行（choice 5,361 / score 539、skipped=0） |
| M2-3 | 首个基线：LoRA/QLoRA 小模型 + 通用:PoL = 9:1 或 8:2 | **Track A 完成**：Qwen3-1.7B + LoRA 1 epoch（2.54h / 6.29GB）；validation 0-shot 0.5127 → **0.7883**；test 同口径 **0.5047 → 0.7785（+27.4pt）**；**Track B 训练+独立评测代码就绪**（19+31 个 CPU 单测），待 GPU 训练；**混合视图 mix-1** 与 `pol2-mix` 一键链就绪（9:1/8:2）；GPU 实验暂停待 owner 开启 |
| M2-4 | 防遗忘：replay 比例、通用智力代理评测、灾难性遗忘阈值 | **base 侧完成**：lm-eval 四任务（ceval/cmmlu/mmlu/agieval，limit 100，205 子任务）base 结果为 0.5847 / 0.5624 / 0.5765 / 0.4133（均值 **0.5342**）；**adapter 侧在 2026-10-23 17:27 系统崩溃时中断（约 25%）未落盘，待重跑**；恢复前需 owner 确认硬件（见下） |
| M2-5 | 校准：温度缩放、ECE/Brier、软标签一致子集偏差的降权 | **工具与协议就绪**：`calibrate.py`（半 B 拟合/半 A 复算，NLL/Brier/ECE/MCE，7 个 CPU 测试）；待 GPU 生成 adapter 概率后出报告 |
| M2-6 | 评测 harness：internal / external / 保留集统一口径 | **基本就绪**：Track A / Track B 同键名 JSON 评测、`collect_results.py` 汇总（分层/配对 bootstrap/多 seed CI/lm-eval 目录）、预注册协议 [EVAL-PROTOCOL](finetune/EVAL-PROTOCOL.md)；正式数字待 GPU |

硬件约束：**主卡 Radeon RX 7900 XT 20GB**（WSL2 Ubuntu 24.04 + ROCm 7.2.1 + PyTorch 2.9.1+rocm7.2.1；GPU 静默时段 00:30–09:30 / 12:30–15:30）；Tesla T10 16GB 仅作备用（Turing，fp16，无 bf16）。首选 LoRA/QLoRA + PEFT；全参与更大模型需要另议算力。

> **2026-10-23 系统崩溃事故**：14:40 启动的 GPU 队列在 17:27 发生内核 bugcheck（0x3B），随后系统反复重启；拆下 T10 后恢复。证据指向「双 GPU 供电/瞬态」与「内存混插（疑似单通道）」两类风险（详见内部取证笔记）。**恢复长时间 GPU 训练前需 owner 确认 PSU/内存/插槽配置**；恢复后先做单卡短任务（≤25 分钟）验证，监测 Kernel-Power 41 / BugCheck 1001 / WHEA；T10 不再与 7900 XT 同时满载。

## 协作工作线（2026-10-26 合并 main；与主线并行，**不混表比较**）

| 线 | 内容 | 状态 / 边界 |
|---|---|---|
| EVAL-02 | 具身推理先导：16 案例 / 8 族文本配对（qwen2.5:7b、llama3.1:8b）；generic/中性/PoL2 三条件长度匹配（中性 vs PoL2 动作净变化 0）；Kev-0.8B + VirtualHome 符号闭环；MuJoCo 单任务 n=1 | 探索性；无统计效能、无相机感知/真机、非 AGIBOT 复现 |
| EVAL-03 | 完整理论内在化先导：114 个来源条目；love2 单条目严格质量门 **0/6** → 按规则停止训练 | 仅可行性先导，**无内在化结论** |
| DATA-02 score-v2 | POL2 score-v2 v1.0.0-rc1：Laya/Kev 训练导出（train-M0 各 6,166）+ MRI 回放 M10/M25/M40；完整数据在 GitHub Release | 非专家金标；sealed blind 不在包内；完整数据不入 Git |
| MODEL-02 Kev-4B | kev-4b-pol2-score-v2-m10（Qwen3.5-4B-Base@1001bb4d + LoRA + pointer head），3 个 seed（17/29/43） | 研究预发布；三 seed blind 平均均 58.71% → **不能宣称平均提升**；seed43 为事后选择的唯一双门版本 |

- 本项目主线（Qwen3-1.7B + 字母 SFT）与协作 Kev-4B pointer-head 线在数据、规模、评测口径上都不同，**禁止混表比较**；
- 协作材料位置：benchmark/embodied_reasoning、benchmark/pol2、datasets/pol2/score-v2、models/kev-pol2-score-v2-m10、results/MODEL-02-kev-pol2-score-v2-20261026；
- 合并摘要见 [阶段报告](docs/reports/2026-10-26-collaborator-update.md)。

## 第三阶段：校准盲测（进行中）

统一输入、标签含义与测试版本；阈值与校准只用预留校验数据；私有保留集由独立评测者统一运行。比较项：PoL benchmark（更准、误拦更少）、通用能力（不明显下降）、主流安全 benchmark（有证据的提升），同时报告延迟与成本。

| 子项 | 内容 | 状态 / 验收 |
|---|---|---|
| E3-1 | 最终评测包（可交第三方执行） | **完成**：`results/MODEL-02-final-eval/eval-package/`（聚合脚本 + 导出检查器 + 延迟基准 + MANIFEST/CHECKSUMS + 评测者手册）；`--check` 与 CPU 端到端冒烟通过 |
| E3-2 | 公开 test 回归 + validation 口径 | **完成**：test 0.5047→0.7785（15,573 行同口径）；validation 0.5127→0.7883；版本 sha 复算一致 |
| E3-3 | 私有保留集 base vs adapter（6,541 条，只出聚合） | **待执行**：需 owner 决定方式 1（独立评测者）/方式 2（授权隔离执行）；聚合脚本支持配对 group-cluster bootstrap（簇=rid 前缀） |
| E3-4 | 温度校准（validation 拟合 → test/保留集只 apply） | **未拟合**：需 adapter 逐行预测（GPU）；拟合后冻结进评测包 |
| E3-5 | 通用能力保持（lm-eval base vs adapter） | base 完成（均值 0.5342）；**adapter 待 GPU 重跑** |
| E3-6 | 成本/延迟（p50/p95、tokens/s、峰值显存） | 工具就绪（`finetune/bench_latency.py`）；**实测待 GPU** |
| E3-7 | 统计（配对 CI、多 seed） | 簇 bootstrap 已内建；多 seed 需 GPU 重训（预注册 20261024/25） |

结果卡：[results/MODEL-02-final-eval/CARD.md](results/MODEL-02-final-eval/CARD.md)；阶段报告见 [docs/reports](docs/reports/2026-10-27-final-eval-package.md)。

## 第四阶段：插件与验证

接入 DSH 等宿主的模型调用与工具执行环节；先影子记录，再有限启用；比较有无治理层时的安全性、任务完成率、延迟与成本。

## 不变式（不要破坏）

1. **绝不按行切分** —— 必须按组（group_id / request_id / family_id + 规范化 state 并查集）
2. **保留集不进任何分支、fork、PR、日志、截图、训练上下文**，由独立评测者库外保管
3. **交付件先按公开三区过滤再生成**，生成后跑 --audit-public-surface 才允许提交
4. **数据卡里的数字由脚本生成**，不手写；报告不得含保留集成员 id
5. **软标签的一致子集要标出来**，不能当随机样本或无偏概率
6. **未批准训练的数据只做整理与评测准备**，不进入训练集
