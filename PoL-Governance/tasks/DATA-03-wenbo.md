# [DATA-03] 通用决策底座：覆盖全面问题集与 Jev 就绪作答 harness

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 进行中；契约与覆盖域已冻结，抓取转换、作答 harness、Luna 清洗三路并行开发中 |

- 更新时间：2026-09-30 19:20 UTC+8
- 分支：pol/DATA-02/wenbo（本任务与 DATA-02 共用一个工作分支：五个 Agent 共享同一 checkout，切换分支会打断在写的文件。待两条线稳定后再按规范拆出 pol/DATA-03/wenbo，届时本页随分支迁移）
- 起点 commit / 依赖分支与 commit：main bf2636c；依赖 DATA-02 的契约与来源审计（datasets/pol2/replay/survey.md）
- 目标与交付路径：`datasets/general/`；构建产物 `datasets/general/data/items.jsonl`；原始下载放仓库外 `D:\pol2-raw\`
- 本次改动范围：新增 datasets/general 与本任务页；TASKS.md 增一行。不改动他人已有文件
- 下一步：db-schema 先定稿 taxonomy；db-hf 用 --limit 200 打通 3 个来源；db-ask 交付可续跑的 Jev 作答 harness；db-luna 打通清洗路径。之后由 Lead 汇总 10k+ 条目并跑覆盖校验
- 阻塞 / 需要谁帮助：官方 Jev 的 endpoint、版本与密钥待 Wenbo 提供（接口骨架已就绪，缺参即退出码 2，不静默降级）
- 环境 / 输出路径 / 资源预算：Python 3.12 + uv，仅标准库；HF 走 datasets-server 分页接口；生成走 sub/gpt-6-luna；磁盘 C 盘剩约 35GB、D 盘剩约 823GB，原始数据落 D 盘
- 数据版本与可用分区：general v0.1；只做通用底座，不掺入 PoL 专项数据；`Praveenrajus/jev-bench` 全部划分为 test，仅作外部评测，不进训练

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-09-30 19:15｜Wenbo / DSH Agent Team｜用户指示：PoL2 专项数据集改由协作者制备约 1k 条，我方搁置；重心转为按 research/Wenbo/data.md 制备**通用决策底座**，重点是覆盖全面的问题集与顺畅的作答流程
2026-09-30 19:18｜Wenbo / DSH Agent Team｜冻结契约 e01984d：条目 = state + 正交问题 + targets，兼容 Jev 的 noul/choice/score 三原语；六个覆盖域各设 1200 条下限、总量下限 10000、单一来源不超过 40%
2026-09-30 19:20｜Wenbo / DSH Agent Team｜重要纠偏：data.md 把 `Praveenrajus/jev-bench` 列为"校准价值极高"，但 DATA-02 的来源审计发现它**22 个 config 全部只有 test 划分**，本身是排行榜基准。判定为：只能当外部评测与校准参考，不得进训练；其上游数据集（GoEmotions、Civil Comments、ChaosNLI 等）的 train 划分另取

## 交付或交接

- 待交付：`datasets/general/` 的 taxonomy、fetch/convert、ask harness、Luna 清洗，以及构建后的 items.jsonl 与覆盖报告
- 复现与检查：`uv run --no-project --offline python tools/check.py` 与 `python datasets/general/coverage.py --items ...`
- 未测项：尚未产生任何真实条目；Jev 未接入；覆盖配额未实测
