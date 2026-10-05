# 目录说明与脚本归档（datasets/general）

这份文档回答两个问题：**这个目录里每个文件是干什么的**，以及**哪些文件已经过时可以清理**。

## 1. 这个目录是什么

通用决策数据集（原 datasets/decision-base，2026-10-05 更名为 datasets/general，与 datasets/pol2 并列）。
目标模型只做"选一个"：给一个情境和一组候选，输出选哪个。

里面有**两条线**，一定不要混：

| 线 | 产物 | 状态 |
|---|---|---|
| **原生四元组线（主）** | data/items.native.jsonl（15,983 条，100% 带来源自带真值） | **训练首选**；来源本来就自带 (state, question, options, target)，我们只是搬运 |
| 模板命题线（对照） | data/items.jsonl（37,124 条，45% 真值、20,407 条待作答） | 已降为对照；它用本地 taxonomy.py 的中文模板去"替数据出题"，与上述立论相反 |

主流程（英文侧）：

    fetch.py            从 HF datasets-server 抓原始行      → D:\pol2-raw\<slug>\rows.jsonl (+manifest)
    convert.py --native 用来源原生四元组生成条目           → data/items.native.jsonl (+report)
    slim.py build       字段精简成 manifest + 紧凑引用      → data/items.native.slim.jsonl (+manifest)
    merge.py            合并中文侧（按变体抽到 33%）        → data/items.final.jsonl (+merge-report.md)
    ask.py plan/run     给没有真值的条目批量取外部答案（原生线已 100% 有真值，暂不需要）
    split 任务（db-schema）按 group 切分 train/dev/calibration/test

## 1.1 命名沿革（留痕，别删）

本目录在 v0.1 期间曾用名 **datasets/decision-base**，2026-10-05 更名为 **datasets/general**
（与 datasets/pol2 并列）。随更名一起改掉的**机器可读标识**：

| 位置 | 旧 | 新 |
|---|---|---|
| coverage.py 报告 schema | decision-base-coverage/0.1 | general-coverage/0.1 |
| taxonomy.py schema | decision-base-taxonomy/0.1 | general-taxonomy/0.1 |
| ask.py 的 TOOL | decision-base-ask | general-ask |
| fetch.py / luna_gen.py 的 User-Agent | pol-decision-base/0.1、PoL-decision-base/0.1 | pol-general/0.1、PoL-general/0.1 |
| 目录名与全部路径引用 | datasets/decision-base/… | datasets/general/… |

更名时这些标识**尚无外部消费者**，所以现在改代价最小。旧字符串只保留在两处历史记录里：
本段说明，以及仓库根的 baseline-old.json（旧覆盖基线，里面存着旧 schema 字符串）。
拿着更名前生成的报告对照上表即可。

## 2. 脚本清单

| 文件 | 作用 | 输入 → 输出 | 状态 |
|---|---|---|---|
| fetch.py | 用 datasets-server 分页抓 HF 原始行，带退避与断点续跑 | sources.json → D:\pol2-raw\<slug>\{rows.jsonl,manifest.json} | **在用**（英文侧原始数据全靠它） |
| convert.py | 条目生成。两种模式：默认=taxonomy 模板（对照）；--native=原生四元组 | 原始行 → data/items*.jsonl + 报告 | **在用**（--native 是主路径） |
| slim.py | 字段精简：逐条恒定/可整批复述的字段抽到数据集级 manifest | items.native.jsonl → items.native.slim.jsonl + manifest | **在用**（新，本次新增） |
| merge.py | 合并最终语料：英文全量 + 中文侧按变体规则抽到 33% | items.native.jsonl + zh-final/items.zh.jsonl → items.final.jsonl + 报告 | **在用**（新，本次新增） |
| coverage.py | 覆盖域、问题键、配额与 schema 报告 | items*.jsonl + sources.json → 文本/JSON 报告 | **在用**（db-schema） |
| taxonomy.py | 覆盖域与问题键定义（模板线的"题面"来源） | — | 在用但**只服务模板线**；原生线已不依赖 |
| ask.py | 批量作答 harness：把条目变成请求、调外部答案源（Jev）、校验答案 | items.jsonl → answers.<source>.jsonl | **在用**（db-ask） |
| luna_clean.py | 把 Luna（自回归教师）输出清洗成契约条目 | Luna 原始输出 → items | 在用（db-luna） |
| luna_gen.py | 按覆盖域与问题键让 Luna 生成 decision 条目（默认 dry-run） | 计划 → 生成请求 | 在用（db-luna） |
| convert_zh.py | 中文来源抓取 + 转换 + 合并（中英双语线） | sources.zh.json → items.zh.jsonl 等 | **在用**（pol2-replay） |

测试（全部离线）：

| 文件 | 覆盖 |
|---|---|
| test_fetch.py | 分页计划、退避、manifest、断点续跑、revision 漂移 |
| test_convert_native.py | 原生四元组模式：原生键名、等长对齐、0-5 不压档、group 聚合、硬标签可复原 |
| test_convert.py | 模板模式（对照线）的映射规则与契约校验 |
| test_slim.py | 精简/还原：round-trip 逐字段一致、提升规则、被删键有文档 |
| test_taxonomy.py / test_coverage.py / test_ask.py / test_luna_clean.py / test_luna_gen.py / test_convert_zh.py / test_split.py | 各脚本自检（分属 db-schema / db-ask / db-luna / pol2-replay） |

    uv run --no-project --offline python -m unittest discover -s datasets/general -p "test_*.py" -q

## 3. 文档与配置

| 文件 | 说明 |
|---|---|
| README.md | **面向协作者的总览**：思路、来源与例子、划分信息（db-hf） |
| CONTRACT.md | **契约**（Lead 所有）：字段定义、覆盖域、配额。字段名不得改 |
| SOURCES.md | 英文侧来源说明：推荐保留的 6 个 System-1 数据集、结构、真实样例、精简建议 |
| ask.md | 作答 harness 的用法与答案契约（db-ask） |
| BILINGUAL.md / zh-survey.md / zh-typed-survey.md | 中文侧调研、准入与合并说明（pol2-replay） |
| slim-report.md | 字段精简报告：逐字段字节占比与前后对比（由 slim.py 自动生成） |
| merge-report.md | 最终语料合并报告：中英条数、组数、域分布、真值率、中文占比、抽取种子与 33% 取舍理由（由 merge.py 自动生成） |
| ARCHIVE.md | 本文件 |
| sources.json | 英文侧来源清单 + 许可 + 配额（db-hf） |
| sources.zh.json | 中文侧来源清单（pol2-replay） |

## 4. 数据产物（不要删）

| 文件 | 内容 |
|---|---|
| data/items.final.jsonl(.gz) | **最终语料**：英文 15,983 + 中文 7,872 = 23,855 条，中文占 33.00%，100% 带真值；中文侧带显式 group_id（切分按组分配） |
| data/items.native.jsonl(.gz) | 英文主产物：15,983 条原生四元组，100% 带真值 |
| data/items.native.slim.jsonl(.gz) + items.native.manifest.json | 精简存储版（省 34.5% 字节，可无损还原） |
| data/items.jsonl(.gz) | 模板版对照产物（37,124 条） |
| data/items.bilingual.jsonl(.gz) | 中英双语版（基于模板版；中文侧裁决后处理） |
| data/*.report.json / convert-report.json | 各步骤的可复算报告 |
| data/splits/ | 最终切分（db-schema，task-20）；benchmark* 已在 .gitignore 里，**不得进公开仓库** |

## 5. 清理提案（本次**没有删除任何文件**）

用户已确认"模板脚本可以清理"，但实测依赖关系表明**现在还不能删**。逐项证据：

| 候选 | 看起来为什么可清 | 实测仍被谁依赖 | 结论 |
|---|---|---|---|
| taxonomy.py | 它是模板命题线的题面来源，原生线不需要 | coverage.py、ask.py、luna_clean.py、luna_gen.py、convert_zh.py、convert.py（模板模式）与 6 个测试文件 import 它（共 10 个模块） | **暂不删** |
| convert.py 的模板转换器（CONVERTERS 段） | 已被 NATIVE_CONVERTERS 取代 | data/items.jsonl 仍作为对照产物存在，需要能复现 | **暂不删**（已在代码里标注"对照/待归档"） |
| test_convert.py | 只测模板模式 | 同上 | **暂不删** |
| data/items.jsonl(.gz) | 已降对照 | 契约与文档引用它；删除属于"删数据产物" | **不删**（任务约束） |
| baseline-old.json（仓库根） | 名字就叫 old，是模板版的覆盖基线 | 在仓库根、不在本目录；是记录不是脚本 | 移交 Lead 处置 |

**可以整套退役的前置条件**（满足后可一次性删除：taxonomy.py、convert.py 的 CONVERTERS 段、
test_convert.py、items.jsonl、items.bilingual.jsonl、baseline-old.json）：

1. Lead 正式宣布模板版对照产物退役，并由 db-schema 把 coverage.py / db-ask 把 ask.py /
   db-luna 把 luna_*.py 的 taxonomy 依赖摘掉（或它们一并退役）；
2. pol2-replay 的中文侧不再依赖 taxonomy 键；
3. 删除后 tools/check.py 仍 pass。

## 6. 常用命令

    # 抓取（英文侧，原始数据落仓库外）
    uv run --no-project --offline python datasets/general/fetch.py --all --resume

    # 生成主产物（原生四元组）
    uv run --no-project --offline python datasets/general/convert.py --native --raw-root D:\pol2-raw

    # 字段精简 + 自校验报告
    uv run --no-project --offline python datasets/general/slim.py build \
        --items datasets/general/data/items.native.jsonl \
        --out datasets/general/data/items.native.slim.jsonl \
        --manifest datasets/general/data/items.native.manifest.json \
        --report-md datasets/general/slim-report.md --gzip

    # 精简是否无损（与原件逐字段比对）
    uv run --no-project --offline python datasets/general/slim.py expand \
        --manifest datasets/general/data/items.native.manifest.json \
        --slim datasets/general/data/items.native.slim.jsonl \
        --out D:\pol2-raw\_check\expanded.jsonl --expect datasets/general/data/items.native.jsonl

    # 覆盖与配额
    uv run --no-project --offline python datasets/general/coverage.py \
        --items datasets/general/data/items.native.jsonl

    # 全仓检查（链接、registry、测试）
    uv run --no-project --offline python tools/check.py
