# [DATA-02] 正式 PoL2 中文决策数据集与配套 benchmark

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 进行中；契约、本体、流水线、正式评测器、通用回放池审计五件已落库；PoL2 生成器在修解析失败率与去重，尚未放量 |

- 更新时间：2026-09-30 16:56 UTC+8
- 分支：pol/DATA-02/wenbo
- 起点 commit / 依赖分支与 commit：main bf2636c（本目录与 research、benchmark 工具齐备）
- 目标与交付路径：`datasets/pol2/`（本体、生成与真值流水线、数据卡、公开样例、registry 条目）；配套正式 benchmark 见 `benchmark/pol2/`，与本任务同分支推进，正式拆分时另开 `pol/EVAL-01/wenbo`
- 本次改动范围：新增本任务页；后续新增 datasets/pol2、benchmark/pol2 及其测试，不改动他人已有文件
- 下一步：本体与流水线合并后跑 17 族 1904 条试点；抽查最小对立对质量；确认后放量到 96 族 10752 条
- 阻塞 / 需要谁帮助：官方 Jev 答案源待接入（Wenbo 提供）。用户已定：本轮只做数据与 benchmark，不做微调；真值教师为 gpt-6.1-sol（主）、grok-4.7 与 mimo-v2.6-pro（备），加官方 Jev
- 环境 / 输出路径 / 资源预算：Python 3.12 + uv；生成走 sub/gpt-6-luna（备 opencode-go/deepseek-v4.1-flash），真值走 sub/gpt-6.1-sol、sub-grok/grok-4.7、opencode-go/mimo-v2.6-pro 三血缘交叉加官方 Jev；私有分配表与盐值放 C:\Projects\DAism\pol2-private（仓库之外），仓库只登记版本与规模
- 数据版本与可用分区：pol2-v0.1 起草中，按场景族预分 70/20/5/5；train 与 public_test 之外的族不对生成/训练 Agent 暴露

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

## 交付或交接

- 待交付：`datasets/pol2/` 本体与数据卡、生成脚本、公开样例、`datasets/registry.json` 条目；`benchmark/pol2/` 评估入口与测试
- 复现与检查：交付时在本目录运行 `uv run --no-project --offline python tools/check.py`
- 未测项：尚未产生任何真实数据；本轮不下载大权重、不占用他人输出目录
