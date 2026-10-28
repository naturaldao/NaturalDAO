# ROADMAP

**目标**：交付可插拔的 PoL 运行时治理层，并让它真正可训练、可评测、可部署。
当前主线是**决策模型**：只做封闭选择（noul 是/否、choice 从候选选一个、score 序数打分）的小模型，要求**不拖累通用智力**，同时更准、更少误拦、可校准、成本可接受。

> 判据是「不拖累」，不是「样样都强」。任何「越大越好 / 越全越好」的表述都是方向错误。
> **方向修正（2026-10-28，owner）**：真正的目标是**用专有治理数据（POL2）微调，并在专有治理评测 + 通用智力评测上都取得良好成绩**。此前的 Track A 是**通用数据（general v5）的普通 FT**，只用于打通工程管线，**不等于目标微调**；该线与第三阶段评测已归档（见下方各节标注）。专有微调尚未执行（POL2 `training_approved=false`，需授权 + APPROVAL-CHECKLIST）。

## 总体阶段（对齐 [SPEC](SPEC.md)）

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 | 准备数据：通用底座 + PoL 专项 + 独立标注 + 共享划分 | **完成**（数据收尾 + HF 托管 2026-10-27；集成方式待 owner 决定） |
| 2 | 模型适配：可复现配方、首个基线、控制遗忘 | **历史（通用 FT 基线，已归档）**：Track A 为 general v5 普通 FT（test 0.5047→0.7785），仅证明工程管线可用；**不是专有微调**，结果卡归档到 `results/archive/2026-10-27-general-ft/` |
| 3 | 校准盲测：同口径评测、效果与成本、保留集统一评测 | **历史（通用 FT 评测，已归档）**：保留集 0.3996→0.7034（+30.37pt，CI [28.94,31.75]），T=0.992，lm-eval -0.7pt（agieval 警戒），延迟完成；**只适用于 general v5 通用 FT**。专有微调双评测尚未开始（需 POL2 授权） |
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

## 第二阶段：模型适配（通用 FT 基线；历史，已归档 2026-10-28）

> **归档说明**：本阶段 Track A 使用 **general v5** 数据，是通用 FT 基线，**不是目标所需的 POL2 专有微调**；数字保留作工程参考，不再作为当前主线。

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

## 评测线（Session B，2026-10-28；独立评测，不训练）

| 子项 | 内容 | 状态 / 验收 |
|---|---|---|
| EB-1 | **Kev 前后对照**：原版 `jaredpalmer/kev-4b@v1.0` vs POL2 score-v2 M10（seed43 主 / seed17/29 变体）在 general v5 私有保留视图上的规范配对评测（共同上下文 384/1024/2048 主口径；serving 全量为敏感性） | **完成**：主口径 6,299 records / 7,347 questions；配对 cluster bootstrap（G=6,299）CI；accuracy/Brier/NLL/ECE/automation/分层/变体/延迟齐全；结果卡 [results/MODEL-02-kev-prefix-eval/CARD.md](results/MODEL-02-kev-prefix-eval/CARD.md) |
| EB-2 | **JevBench coherence**（第三方，无 gold）对照 | **完成**：kev-original 72.19 [70.16,74.17] vs seed43 80.91 [78.66,83.15]（mini v1）；注明第三方、coherence≠accuracy、不能与 accuracy 榜混读 |
| EB-3 | **Jev 类榜单/基准调研** | **完成**：[docs/reports/2026-10-27-jev-benchmarks.md](docs/reports/2026-10-27-jev-benchmarks.md)（JevBench / Kev suites / Decision Index / TypeSafe / OpenJev / Laya / OpenDecider / System One Bench；许可与可收集性） |
| EB-4 | **评测工程与复现** | **完成**：`benchmark/kev_prefix/`（转换/套件/筛查/聚合/独立核对/表生成/驱动脚本，85+ 单测）；数据重叠审计 0 精确重叠；底座 revision 固定；私有保留集只回传聚合、执行后删除临时副本 |

边界：本线**不训练**、不改模型/数据、不为保留集调 prompt/阈值；Kev 表与 Qwen3-1.7B 线分表；seed43 属事后选择的探索性比较；结论仅限该冻结视图/配置。

## 第三阶段：校准盲测（通用 FT 评测；历史，已归档 2026-10-28）

> **归档说明**：本节数字均来自 general v5 通用 FT 的评测，**不能推断专有微调后的治理/通用表现**；专有微调双评测待 POL2 授权后另行预注册。

统一输入、标签含义与测试版本；阈值与校准只用预留校验数据；私有保留集由独立评测者统一运行。比较项：PoL benchmark（更准、误拦更少）、通用能力（不明显下降）、主流安全 benchmark（有证据的提升），同时报告延迟与成本。

> **收尾说明（2026-10-27，owner 决定）**：本仓库的本地训练/评测线到此结束，之后不再在本地独立训练外部模型。本阶段以**单 seed** 交付；多 seed 与 Track B 未做，agieval 单任务警戒作为已知限制记录（已同日复现，处置需改模型重训）。结果与评测包保持可复现。

| 子项 | 内容 | 状态 / 验收 |
|---|---|---|
| E3-1 | 最终评测包（可交第三方执行） | **完成**：`results/archive/2026-10-27-general-ft/final-eval/eval-package/`（聚合脚本 + 导出检查器 + 延迟基准 + MANIFEST/CHECKSUMS + 评测者手册）；`--check` 与 CPU 端到端冒烟通过 |
| E3-2 | 公开 test 回归 + validation 口径 | **完成**：test 0.5047→0.7785（15,573 行同口径）；validation 0.5127→0.7883；版本 sha 复算一致 |
| E3-3 | 私有保留集 base vs adapter（6,541 items / 7,990 问题行，只出聚合） | **完成（2026-10-27，方式 2）**：base 0.3996 → adapter **0.7034（+30.37 pt）**，配对 group-cluster bootstrap 95% CI **[+28.94, +31.75]**（G=6,321，reliability ok）；7,740 行有效、0 缺失；只导出聚合（检查器 1,004 项 pass） |
| E3-4 | 温度校准（validation 拟合 → test/保留集只 apply） | **完成**：T=**0.992077**（validation calibration 半区 3,950 行拟合）冻结后保留集只 apply；raw/calibrated ECE 0.0221/0.0225、NLL 0.75009/0.75050 → **预注册「NLL 下降」未满足**（原始概率已校准良好；T≈1 无需缩放） |
| E3-5 | 通用能力保持（lm-eval base vs adapter） | **完成（含警戒）**：adapter ceval 0.6189 / cmmlu 0.5922 / mmlu 0.5911 / agieval 0.3057，均值 **0.5270**（-0.7 pt）；**agieval -10.8 pt 触发「任一任务降≥5pt」警戒**，处置（降 rank/epoch 重训）留 owner 决策 |
| E3-6 | 成本/延迟（p50/p95、tokens/s、峰值显存） | **完成**：batch=1 p50 44.9/65.0 ms（base/adapter）、tokens/s 6,039/4,582、峰值 4.0/4.1 GB；batch=16 更差（p50 77.6/95.1 ms，峰值 14.6 GB）→ **部署建议 batch=1**；保留集推理 base 225.9 s / adapter 271.6 s（7,740 行） |
| E3-7 | 统计（配对 CI、多 seed） | **CI 完成**（簇 bootstrap 见 E3-3；item bootstrap 近似 [+29.03,+31.56]）；**多 seed 未做**：owner 2026-10-27 决定停止额外重训（GPU 机时），本轮按单 seed 交付、不宣称跨 seed 稳定；Track B 未训练 |

结果卡：[results/archive/2026-10-27-general-ft/final-eval/CARD.md](results/archive/2026-10-27-general-ft/final-eval/CARD.md)；阶段报告已归档：[docs/reports/archive/2026-10-27-final-eval.md](docs/reports/archive/2026-10-27-final-eval.md)。

## 修正后的目标路径（2026-10-28）

1. **等待授权**：POL2 训练授权 + 许可（APPROVAL-CHECKLIST A1–A7）；`training_approved=false` 前零梯度；
2. **专有微调**：用 POL2 专有治理数据（必要时与 general 做小比例 replay）微调，记录数据版本/混合比例/授权；这是目标模型，不是通用 FT；
3. **双评测**：
   - **专有治理评测**：POL2 冻结集/专项评测协议（预注册、只聚合）；
   - **通用智力评测**：lm-eval 等代理（防遗忘阈值预注册），不得用 test/保留集调参；
4. **达标判据**：只有“治理专项提升 + 通用智力非劣（预注册阈值内）”同时成立，才作为目标达成证据；任一不达标如实报告；
5. **外部参考线**（Kev/Jev 类）可作对照与榜单调研，但与本项目专有微调结果分表、不混表。

## 第四阶段：插件与验证

接入 DSH 等宿主的模型调用与工具执行环节；先影子记录，再有限启用；比较有无治理层时的安全性、任务完成率、延迟与成本。

## 不变式（不要破坏）

1. **绝不按行切分** —— 必须按组（group_id / request_id / family_id + 规范化 state 并查集）
2. **保留集不进任何分支、fork、PR、日志、截图、训练上下文**，由独立评测者库外保管
3. **交付件先按公开三区过滤再生成**，生成后跑 --audit-public-surface 才允许提交
4. **数据卡里的数字由脚本生成**，不手写；报告不得含保留集成员 id
5. **软标签的一致子集要标出来**，不能当随机样本或无偏概率
6. **未批准训练的数据只做整理与评测准备**，不进入训练集