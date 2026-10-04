# 任务表

领取方法见 [AGENTS](AGENTS.md)。下表是任务目录，实时领取状态在远端 `pol/*` 分支的任务页；`git fetch origin` 后运行 `python tools/board.py` 查看。分支尚未合并也能协作。认领可能同时发生，发现撞单就通过任务页协商拆分，不把分支当全局锁。

| ID | 做什么 | 交付入口 |
|---|---|---|
| DATA-01 | 独立试标注与分歧整理 | datasets/；benchmark 标注工具 |
| DATA-02 | 生成正式 PoL 数据与 70/20/5/5 划分 | datasets/ |
| MODEL-01 | 深入调研并更新候选清单 | models/CATALOG.md |
| MODEL-02 | 自选模型适配与控制遗忘（可多队） | models/；results/ |
| EVAL-01 | 正式 benchmark、通用及主流安全对照 | benchmark/；results/ |
| APP-01 | 插件接入、试运行与端到端验证 | integrations/ |
| LIT-01 | Jev 类型化决策模型文献综述，对照 PoL2 治理条款 | research/PoL2-Jev-Typed-Literature-Survey/ |
| GOV-01 | PoL2 × DAO 治理机制实验室：条款落地、模拟、反事实与基线筛查评测 | research/PoL2-DAO-Governance-Lab/ |

DATA-01 可由两名独立标注者分别领取后缀 A/B，完成前不互看标签。MODEL-02 用模型名后缀区分实验。模型调研、数据准备、接口开发可并行；不同数据版本的结果分开比较。

新任务直接加一行。暂停/转交/完成更新任务分支里的任务页；本表仅在增加/调整任务范围时修改。日常进度不用等合并。
