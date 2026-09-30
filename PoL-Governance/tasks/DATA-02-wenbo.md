# [DATA-02] 正式 PoL2 中文决策数据集与配套 benchmark

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 进行中；已冻结理论依据与标签本体 v0.1 草案，生成与真值流水线在搭建中 |

- 更新时间：2026-09-30 16:56 UTC+8
- 分支：pol/DATA-02/wenbo
- 起点 commit / 依赖分支与 commit：main bf2636c（本目录与 research、benchmark 工具齐备）
- 目标与交付路径：`datasets/pol2/`（本体、生成与真值流水线、数据卡、公开样例、registry 条目）；配套正式 benchmark 见 `benchmark/pol2/`，与本任务同分支推进，正式拆分时另开 `pol/EVAL-01/wenbo`
- 本次改动范围：新增本任务页；后续新增 datasets/pol2、benchmark/pol2 及其测试，不改动他人已有文件
- 下一步：冻结标签本体与 JSONL schema；用 Luna 小样本试跑生成器；确认规模与预算后放量到上万条；GLM-5.3 制备真值并交叉验证
- 阻塞 / 需要谁帮助：官方 Jev 答案源待接入（Wenbo 提供）；微调算力与底座待确认（本机仅 Tesla T10 16GB，无法本地微调 GLM-5.3 569B 或 GLM-5.3-Flash 320B-A18B）
- 环境 / 输出路径 / 资源预算：Python 3.12 + uv；生成与真值走已配置 API（Luna: gpt-6-luna；教师: GLM-5.3）；私有保留集写入仓库之外，仅登记版本与规模
- 数据版本与可用分区：pol2-v0.1 起草中，按场景族预分 70/20/5/5；train 与 public_test 之外的族不对生成/训练 Agent 暴露

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-09-30 16:56｜Wenbo / DSH Agent Team｜领取本任务并开分支。已通读 PoL2 第 0-8 章、工程策略、SPEC、AGENTS、benchmark/PROTOCOL 与两位协作者调研报告；确认三处硬约束：本机 16GB 单卡无法微调 GLM-5.3 系列、官方 Jev 只做外部基线与答案源、保留集必须库外保管｜main bf2636c｜先小样本跑通生成器再放量

## 交付或交接

- 待交付：`datasets/pol2/` 本体与数据卡、生成脚本、公开样例、`datasets/registry.json` 条目；`benchmark/pol2/` 评估入口与测试
- 复现与检查：交付时在本目录运行 `uv run --no-project --offline python tools/check.py`
- 未测项：尚未产生任何真实数据；本轮不下载大权重、不占用他人输出目录
