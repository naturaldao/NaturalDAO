# [DATA-02] 正式 PoL2 中文决策数据集与配套 benchmark

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 完成；通用 v5 已并入 main；专用冻结数据 POL2-accepted-8705-v1（8,705 单元 / 75 场景族）已完成解压、校验、四区切分、数据卡与 HF 导出（NOT UPLOADED，待 owner 授权） |

- 更新时间：2026-10-23 UTC+8
- 分支：pol/DATA-02/wenbo（阶段一收尾 PR 之后，模型适配线另开 pol/MODEL-02/wenbo）
- 起点 commit / 依赖分支与 commit：main 68105b1（PR #43 合并 v5 之后）；依赖协作者交付的 pack-1022 冻结包
- 目标与交付路径：`datasets/pol2/`（本体、生成与真值流水线、冻结数据卡、切分清单、可复算脚本与测试、Hugging Face 导出）；配套评测入口见 benchmark/pol2
- 本次改动范围：datasets/pol2/ 与其测试；不改动他人已有文件
- 下一步：① POL2-accepted-8705-v1 校验与四区物化（train / validation / calibration / blind_test） ② 数据卡与 SPLIT-MANIFEST ③ Hugging Face 导出与托管 ④ 训练批准后再按 9:1 或 8:2 与通用数据混合
- 阻塞 / 需要谁帮助：`training_approved=false`（LLM 标注、非专家金标），训练前需人工复核批准；HF 上传需要用户操作或 token
- 环境 / 输出路径 / 资源预算：Python 3.12 + uv，仅标准库；数据实体在 datasets/pol2/data/（gitignore），仓库只留数据卡、清单与校验脚本
- 数据版本与可用分区：POL2-accepted-8705-v1，四区 5,900 / 1,110 / 1,008 / 687；到项目区域的映射见数据卡（provisional，待 owner 签字）

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-09-30 16:56｜Wenbo / DSH Agent Team｜领取本任务并开分支。已通读 PoL2 第 0-8 章、工程策略、SPEC、AGENTS、benchmark/PROTOCOL 与两位协作者调研报告；确认三处硬约束：本机 16GB 单卡无法微调 GLM-5.3 系列、官方 Jev 只做外部基线与答案源、保留集必须库外保管｜main bf2636c｜先小样本跑通生成器再放量
2026-09-30 17:10｜Wenbo / DSH Agent Team｜落库并推送 8e3f5d0：数据契约（case/question/answer/label 四层 JSONL，pilot schema 超集）、20 主题域 x 15 判定轴 = 96 场景族共 10752 条目标、族级加盐确定性分区（实测 69.8/19.8/5.2/5.2）、splits.py 拒绝把分配表与保留族写进仓库。tools/check.py 增加 datasets 测试发现；全仓 50 项测试与 127 条链接检查通过｜分支 pol/DATA-02/wenbo
2026-09-30 17:12｜Wenbo / DSH Agent Team｜实测打通全部模型路由并交底给流水线：Luna 一次调用 3 组对用 4706/576 tokens 耗时 28s；gpt-6.1-sol、grok-4.7、mimo-v2.6-pro、deepseek-v4.1-flash、glm-5.3 均 200。发现 opencode-go 需 x-opencode-session 头、mimo 与 glm 低 max_tokens 时 content 为空，已要求判为 invalid。用户定稿：本轮只做数据与 benchmark，先跑 17 族 1904 条试点
2026-09-30 17:12｜Wenbo / DSH Agent Team｜三路 Agent 并行：pol2-ontology（本体与测试项矩阵）、pol2-pipeline（生成与真值）、pol2-benchmark（正式评测器）；共享任务 task-1/2/3 均已领取。真值判定加了硬约束：生成方血缘必须从真值池剔除，≥2 个不同血缘逐题一致才出 label
2026-09-30 17:25｜Wenbo / DSH Agent Team｜task-1 本体完成并合入 0c26fcb：57 条标签、34 条注册条款、18 判定轴 / 25 组成对样例，每条标签带 clause 回溯；另有 12 条 pending_review 留给人工裁定（含"沉默是否构成同意撤回"，原文无规定，工程不替原文补规则）
2026-09-30 17:26｜Wenbo / DSH Agent Team｜task-2 流水线与 task-3 正式评测器完成并合入 bb9f6b2：流水线 100 项离线测试、评测器 60 项，tools/check.py 全绿（171 条链接）。评测器把"正当批评/正当愤怒/拒绝异议/修复/不在场"五类误拦单列，不混进总分。Luna 真实冒烟 1 次调用 4820+1547 tokens、53s、6 条 case 三类齐备
2026-09-30 17:28｜Wenbo / DSH Agent Team｜用户补充：HuggingFace 若有高质量决策数据集可降低制备难度，但 PoL2 专项仍须自制。据此新开 task-4（datasets/pol2/replay/）做通用决策回放池审计与中文改写重判，由 pol2-replay 领取；这一路对应 SPEC 的 通用:PoL = 9:1 或 8:2，且只有 PoL 的 train 分区参与混合

2026-09-30 17:40｜Wenbo / DSH Agent Team｜task-4 完成：审计 728 个候选 id、87 条元数据，准入 15 / 观察 16 / 剔除 37（评测集本体 22 条）。重要防坑：同一 Open-Jev 有 3 个再发布须按内容哈希去重；s1lv3rj1nx/openjev-mixture 的 train 混入 92 个公开评测任务；LocalLLaMA/typed-decisions 本体就是 benchmark；pngwn v1 的 escalate 标签 100% 反向。准入池 train 容量 >470 万决策，够 9:1 与 8:2 两种配比，未降门槛
2026-09-30 17:42｜Wenbo / DSH Agent Team｜Lead 独立复核 2 族试点产出（未只看 Agent 报告）：83 组对、组内 target 相似度 mean=0.972 min=0.593，对纪律合格；但 47 次调用失败 12 次（26%，多为 JSON 解析失败，1 次 Cloudflare 524），duplicate_case=12、shortcut_risk=14。已下放量门槛：invalid 率 <5%、重复 <1%、shortcut 清零、每族三类齐备且组内 status 相反，达标才批 17 族

2026-09-30 17:55｜Wenbo / DSH Agent Team｜两族试点达标并合入 1e132a1。Lead 独立复算（不用 Agent 报告数字）：224 条 case、112 组完整对、精确重复 0、shortcut_risk 0、107 次调用 invalid 尝试 0、派生问题 4256 条（choice 896 / noul 3360，每 case 19 题）。根因修复三件：sub 路由支持 response_format=json_object；推理吃光 8192 completion 预算导致截断，改 max_tokens 16384；不合格对回灌原因重生成、仍不合格则丢弃并计数。历史前后对比与每千条预算写进 pipeline/README.md
2026-09-30 17:57｜Wenbo / DSH Agent Team｜批准放量（task-5）：跑满 datasets/pol2/families.pilot.jsonl 的 17 族 1904 条，输出 datasets/pol2/v0.1-pilot/，预算约 2000 次调用、约 10M prompt + 2.7M completion tokens、并发 8 约 1.5-2 小时。本次仍不跑教师真值，真值需另行批准

2026-10-22｜Wenbo / DSH Agent Team｜**PR #43 合并**（main 68105b1），通用决策数据集 v5 进入 main；本任务的专项数据改由协作者制备，本轮转做数据接收与整理
2026-10-22｜Wenbo / DSH Agent Team｜收到协作者数据包 pack-1022.tar.gz（119.5 MB，已 gitignore）。核心产物为 POL2-accepted-8705-v1：8,705 accepted units / 75 场景族 / 26 个 run / 4,888 case（其中 3,817 个带 a/b 反事实对）；状态 FROZEN_READ_ONLY_NOT_TRAINING_APPROVED，training_approved=false，expert_gold=false；提案切分 5,900 / 1,110 / 1,008 / 687（提案，原包无切分文件）
2026-10-23｜Wenbo / DSH Agent Team｜**阶段一收尾启动**：解压落位 datasets/pol2/data/；校验 8,705 units 与 75 族切分一致性；物化四区切分；产出数据卡、SPLIT-MANIFEST、可复算 prepare/verify 脚本与离线测试；构建 public/private 分离的 Hugging Face 导出。另有本次仓库整理：大文件离仓（转 HF）、内部 Agent 工作区分隔、公开文档精简
2026-10-23｜Wenbo / DSH Agent Team｜**本任务交付完成**（待 HF 上传）：数据卡 `datasets/pol2/FREEZE-8705-V1.md`、清单 `datasets/pol2/freeze-8705-v1/SPLIT-MANIFEST.json`、脚本 `prepare_freeze.py`、测试 `test_prepare_freeze.py`。验证：prepare_freeze verify pass（17 checks，tracked manifest 可复现）、26 个离线测试 OK、全 datasets discovery 795 tests OK、blind 内容在 tracked 文件 grep 0 命中。剩余动作：owner 训练授权 + 许可确认 → HF 上传（public/private 分离）

## 交付或交接

- 已交付：`datasets/pol2/` 本体、生成与真值流水线、本体标签与测试项矩阵、回放池审计；冻结数据卡 [FREEZE-8705-V1.md](../datasets/pol2/FREEZE-8705-V1.md) 与切分清单
- 数据实体：`datasets/pol2/data/`（gitignore，含 blind_test，绝不入库）；Hugging Face 导出在 `datasets/pol2/data/hf-export/`，public / private 分离，尚未上传
- 复现与检查：`uv run --no-project --offline python datasets/pol2/prepare_freeze.py verify`；`uv run --no-project --offline python tools/check.py`
- 未完成：训练批准（需人工复核非专家金标数据）；HF 上传；与通用数据的 9:1 / 8:2 混合属第二阶段（MODEL-02）
