# [DATA-03] 通用决策底座：覆盖全面问题集与 Jev 就绪作答 harness

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Wenbo / DSH Agent Team | 完成；**v5 已交付并经 PR #43 并入 main**（公开三区 71,519 条 / 78,001 问题；保留集 6,541 条库外）；正在做 Hugging Face 托管与仓库整理 |

- 更新时间：2026-10-23 UTC+8
- 分支：pol/DATA-02/wenbo（阶段一收尾 PR 之后，模型适配线另开 pol/MODEL-02/wenbo）
- 起点 commit / 依赖分支与 commit：main 68105b1（PR #43 合并 v5 之后）；依赖 DATA-02 的契约与来源审计
- 目标与交付路径：`datasets/general/`；数据实体在 `datasets/general/data/`（gitignore）；仓库只留数据卡、清单与校验脚本，实体托管 Hugging Face
- 本次改动范围：datasets/general/ 文档、清单、HF 导出脚本与 tests；不改动他人已有文件
- 下一步：① 数据实体 Hugging Face 托管（公开三区与私有保留集分离） ② 大文件 git 离仓 ③ 进入第二阶段 model adaptation（MODEL-02） ④ P8 补世界知识与因果·反事实
- 阻塞 / 需要谁帮助：HF 上传需要用户操作或 token（本机无 token）；保留集只能由独立评测者统一评测
- 环境 / 输出路径 / 资源预算：Python 3.12 + uv，仅标准库；HF 走 datasets-server 分页接口；原始下载在仓库外
- 数据版本与可用分区：general v5；四区 train 48,728 / test 15,194 / validation 7,597 / benchmark 6,541；`Praveenrajus/jev-bench` 只有 test 划分，仅作外部评测、不进训练

状态：待领取 / 进行中 / 阻塞 / 暂停 / 待集成 / 完成。左格写负责的人与实际执行 Agent（换 Agent 时更新）；右格以状态开头，接一句当前事实，不用虚构百分比。保留表头，单元格内不用竖线，以便看板读取。

## 进展与交流

2026-09-30 19:15｜Wenbo / DSH Agent Team｜用户指示：PoL2 专项数据集改由协作者制备约 1k 条，我方搁置；重心转为按 research/Wenbo/data.md 制备**通用决策底座**，重点是覆盖全面的问题集与顺畅的作答流程
2026-09-30 19:18｜Wenbo / DSH Agent Team｜冻结契约 e01984d：条目 = state + 正交问题 + targets，兼容 Jev 的 noul/choice/score 三原语；六个覆盖域各设 1200 条下限、总量下限 10000、单一来源不超过 40%
2026-09-30 19:20｜Wenbo / DSH Agent Team｜重要纠偏：data.md 把 `Praveenrajus/jev-bench` 列为"校准价值极高"，但 DATA-02 的来源审计发现它**22 个 config 全部只有 test 划分**，本身是排行榜基准。判定为：只能当外部评测与校准参考，不得进训练；其上游数据集（GoEmotions、Civil Comments、ChaosNLI 等）的 train 划分另取

2026-10-22 16:10｜Wenbo / DSH Agent Team｜**v5 定稿并开 PR #43**。语料 74,912 条 / 82,843 target（基座 23,855 + 能力补源 51,057）；产品 78,001；四区 train 48,728 / test 15,194 / validation 7,597 / benchmark 6,541。可用软分布 7.61% → 62.74%（mercury 补全；**是一致子集、有选择偏差**）。验收：check.py pass（769 tests / 478 links）、公开面审计 exit 0（348 文件全量、id 6,541 + 正文 5,773 零命中）、保留集包 verify.py exit 0、切分两跑逐字节一致。**注意**：本任务与 DATA-02 共用一个工作分支 `pol/DATA-02/wenbo`，未按规范拆出 `pol/DATA-03/wenbo`，合并前需说明。
2026-10-22｜Wenbo / DSH Agent Team｜**PR #43 已合并**（main 68105b1），v5 进入主线；本任务转为交付后整理
2026-10-23｜Wenbo / DSH Agent Team｜**阶段一收尾**：① 数据实体迁 Hugging Face 托管，仓库改留数据集清单 MANIFEST.json + HF.md 操作手册 + 校验脚本；② 公开三区导出与私有保留集导出物理分离，保留集只上传私有仓库；③ 大文件 git 离仓；④ 更新 registry 与数据卡中的托管状态
2026-10-23｜Wenbo / DSH Agent Team｜**本任务交付完成**（待 HF 上传）：export_hf.py 两次 build 逐字节一致；公开面断言 benchmark 6,541 成员 id × 公开导出 71,519 条目交集 0；私有包 verify.py exit 0；readme_stats 复算 71,519 / 78,001；公开面审计 exit 0。6 个大文件已 git rm --cached（本机保留），HF 状态 READY / NOT UPLOADED。下一步交接 MODEL-02 模型适配

## 交付或交接

- 已交付并合入 main：`datasets/general/` v5（数据集卡、契约、来源、训练路由、切分报告、target 溯源、目录索引）；概率旁挂件 jev-probs（44,740 行）与 target-types（74,853 行），两者与保留集交集均为 0
- 托管整理中：数据实体 → Hugging Face（公开三区公开仓库；保留集私有仓库），仓库留 `data/MANIFEST.json` 与 [HF.md](../datasets/general/HF.md)；状态 READY / NOT UPLOADED
- 库外保留：保留集包 v0.5（6,541 条）在 `datasets/general/data/splits/benchmark-dataset/`（gitignore），由用户/维护者上传私有仓库，独立评测者统一评测
- 复现与检查：`uv run --no-project --offline python tools/check.py`；`split.py --audit-public-surface`；`benchmark-dataset/verify.py`；`readme_stats.py --check`
- 未完成：HF 上传（需用户操作）；P8 补源；模板命题线退役；第二阶段模型适配另立 MODEL-02 任务页
