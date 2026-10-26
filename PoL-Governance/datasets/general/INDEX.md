# 目录索引（datasets/general）

> 这份文件回答三件事：**每个文件是干什么的**、**按目的该读哪一份**、**哪些可以退役**。
> 数据集本身长什么样、怎么用，读 [README](README.md)。

## 1. 这是什么

通用决策数据集（v0.1 期间叫 `datasets/decision-base`，2026-10-05 更名）。目标模型只做「选一个」：
给一个情境和一组候选，输出选哪个或选/不选。三条原语（`noul` / `choice` / `score`，见 [CONTRACT](CONTRACT.md)）。

当前版本 **v5**：公开三区 **71,519 条 / 78,001 问题**；内部保留集 **6,541 条**在仓库与训练环境之外。

## 2. 按目的找文档

| 你想知道 | 读 |
|---|---|
| 数据集长什么样、怎么用、分布如何 | [README.md](README.md) |
| 字段定义、三层结构（item/question/answer/label）、原语 | [CONTRACT.md](CONTRACT.md) |
| 数据从哪来、什么许可、固定在哪个 revision | [SOURCES.md](SOURCES.md) |
| 训练时怎么过滤、路由（classification/distillation/drop）、怎么降权 | [TRAINING.md](TRAINING.md) |
| 切分怎么做的、保留集为什么轮换、护栏缺口 | [split-report.md](split-report.md) |
| 概率（probs）到底是怎么产生的 | [target-provenance.md](target-provenance.md) |
| 概率补全做了多少、拒了多少、置信度分层 | [jev-validation.md](jev-validation.md) |
| 能不能接 RLCD / LoRA / SFT，软分布会不会卡住后续适配 | [adaptation-assessment.md](adaptation-assessment.md) |
| 为什么 v5 的能力分布长这样、bigbench/cosmos 怎么选的 | [capability-adoption.md](capability-adoption.md) |
| 怎么给条目批量取外部答案（Jev） | [ask.md](ask.md) |
| 数据实体托管在哪、怎么下载/上传/校验 | [HF.md](HF.md) |
| 每个数据文件的 sha256、字节数、行数、可见性 | [data/MANIFEST.json](data/MANIFEST.json) |

## 3. 流水线

英文侧（原始数据落仓库外 `D:\pol2-raw\`）：

    fetch.py                HF datasets-server 分页抓原始行        → D:\pol2-raw\<slug>\{rows.jsonl,manifest.json}
    convert.py --native     用来源原生四元组生成条目               → data/items.native.jsonl
    slim.py build           字段精简成 manifest + 紧凑引用          → data/items.native.slim.jsonl
    merge.py                合并中文侧                             → data/items.final.jsonl

能力拓宽（v4 起）：

    convert_capability.py   把 bigbench / cosmos_qa 转成同构条目     → data/items.capability.jsonl
    build_corpus.py         合并基座 + 能力源（greedy 正则按来源归属） → data/corpus.jsonl

切分与交付：

    split.py                分组切分 + 盐 + 公开面排除 + 审计         → data/splits/{train,test,validation,benchmark}.jsonl*
    package_benchmark.py    打包私有 benchmark（gitignore）           → data/splits/benchmark-dataset/
    verify_benchmark_package.py  复核包完整性与口径                   → exit 0/非 0

数据托管与交付（v5）：

    export_hf.py            确定性 HF 导出 + 仓库清单 + 全量校验      → data/hf-export/ 与 data/MANIFEST.json
    HF.md                   托管方案与上传/校验手册                    → HF 公共/私有仓库（状态 UPLOADED）

概率补全与旁挂件：

    jev_fill.py             唯一交付导出入口 `probs-public`（写盘前硬断言） → data/jev-probs.jsonl.gz
    target_types.py         每个 target 的形态与来源                  → data/target-types.jsonl.gz
    filter_targets.py       按分区筛 target                          → 保留集/公开面
    report_corpus.py        确定性语料报告                            → （stdout / json）
    readme_stats.py         README 全部数字的唯一来源，保证可复算      → （stdout）

## 4. 脚本与测试

| 文件 | 作用 | 状态 |
|---|---|---|
| fetch.py | 抓 HF 原始行，带退避与断点续跑 | 在用 |
| convert.py | 条目生成。`--native`=原生四元组（主）；默认=模板命题线（对照） | 在用（原生为主） |
| convert_capability.py | 能力补源转换（bigbench / cosmos_qa） | 在用（v4 起） |
| convert_zh.py | 中文来源抓取 + 转换 + 合并 | 在用 |
| slim.py | 字段精简 / 无损还原 | 在用 |
| merge.py | 英文全量 + 中文侧合并 | 在用 |
| build_corpus.py | 语料合并（基座 + 能力源） | 在用（v4 起） |
| split.py | 分组切分、盐、公开面排除、`--audit-public-surface` | 在用（核心） |
| jev_fill.py | 概率补全（mercury / jev-router）+ 交付导出 + 自检 | 在用（核心） |
| target_types.py | target 形态分类与溯源 | 在用（核心） |
| filter_targets.py | 按分区筛选 target | 在用 |
| report_corpus.py | 确定性语料报告 | 在用 |
| readme_stats.py | README 数字生成（可复算，口径唯一来源） | 在用 |
| export_hf.py | HF 公开/私有导出 + 仓库清单 `data/MANIFEST.json`（离线、确定性） | 在用（v5 交付） |
| coverage.py | 覆盖域 / 问题键 / 配额报告 | 在用 |
| ask.py | 批量作答 harness（Jev） | 在用 |
| taxonomy.py | 覆盖域与问题键定义 | 在用，但**只服务模板线** |
| luna_clean.py / luna_gen.py | Luna（自回归教师）清洗与生成 | 在用（非主路径） |
| package_benchmark.py / verify_benchmark_package.py | 私有 benchmark 打包与复核 | 在用 |

测试全部离线：

    uv run --no-project --offline python -m unittest discover -s datasets/general -p "test_*.py" -q

## 5. 数据产物

| 路径 | 内容 | 进 git |
|---|---|---|
| data/items.final.jsonl | 冻结语料 v4：74,912 条 / 82,843 target | 否（大文件，本机保留） |
| data/corpus.jsonl | 合并后语料（基座 + 能力源） | 否 |
| data/splits/{train,test,validation}.jsonl(.gz) | 公开三区 | 否（.gz 托管 HF 公开仓库） |
| data/splits/benchmark.jsonl(.gz) | 内部保留集 6,541 条 | **否，且不得进任何分支** |
| data/splits/benchmark-dataset/ | 私有 benchmark 包（v0.5，README/USAGE/manifest/verify.py） | 否，上传 HF 私有仓库 |
| data/splits/split-manifest.json | 切分清单、盐指纹、轮换名单 sha256 | 是 |
| data/MANIFEST.json | 全部数据文件的 sha256 / bytes / 行数 / 可见性 / HF 路径 | 是（v5 新增） |
| data/jev-probs.jsonl.gz、data/target-types.jsonl.gz | 概率 / target 形态旁挂件（公开面） | 否（托管 HF 公开仓库） |
| data/zh-supplement/items.jsonl | 中文补充明文（8.7 MB） | 否 |
| data/zh-supplement/items.jsonl.gz | 中文补充 gzip（936 KB） | 是（小体积复算锚点；HF 有同字节副本） |
| data/hf-export/ | HF 导出（public / private-holdout） | 否（gitignored，见 HF.md §7.3） |
| data/jev/*.json | 补全统计、置信度分层 | 是 |
| data/zh/、data/zh-supplement/ | 中文侧中间产物 | 部分 |

## 6. 历史报告（archive/）

以下报告是当时的过程记录，**数字已过时，不要据此引用**；要引用请用 README / TRAINING / split-report 的 v5 数字。

| 文件 | 内容 | 归档原因 |
|---|---|---|
| archive/2026-10-02-bilingual.md | 中英双语底座 v0.1 设计 | 被 v4 双语语料取代 |
| archive/2026-10-02-zh-survey.md | 中文决策数据调研与准入 | 准入结论已固化进 SOURCES.md |
| archive/2026-10-05-zh-typed-survey.md | 中文原生 typed decision 补搜 | 同上 |
| archive/2026-10-05-zh-build-report.md | 中文侧构建报告（Deepexi 去重等） | 构建记录，v3 口径 |
| archive/2026-10-05-zh-supplement-report.md | 中文 noul/score 补充集 | 补充集已并入语料 |
| archive/2026-10-05-merge-report.md | 最终语料合并报告（v3：23,855 条） | 自动生成、v3 口径 |
| archive/2026-10-05-slim-report.md | 字段精简报告（v3） | 自动生成、v3 口径 |
| archive/2026-10-06-coverage-gaps.md | 六域缺口分析 | 被 v5 能力构成取代 |
| archive/2026-10-15-capability-sources.md | 能力补源候选调研（P1/P2 选型） | 选型结论已固化进 capability-adoption.md |
| archive/coverage-baseline-old.json | 更名前（decision-base）的覆盖基线 | 仅留痕 |

## 7. 可退役候选（**本次没有删除任何文件**）

用户已同意「模板脚本可以清理」，但实测依赖关系表明现在还不能删。逐项：

| 候选 | 仍被谁依赖 | 结论 |
|---|---|---|
| taxonomy.py | coverage.py、ask.py、luna_clean.py、luna_gen.py、convert_zh.py、convert.py（模板模式）与 6 个测试 import 它 | 暂不删 |
| convert.py 的 CONVERTERS 段 | data/items.jsonl 作为对照产物仍存在，需可复现 | 暂不删（代码里已标注「对照/待归档」） |
| test_convert.py | 只测模板模式 | 暂不删 |
| data/items.jsonl / items.bilingual.jsonl | 模板版对照产物 | 明文不删 |

**整套退役的前置条件**：① 正式宣布模板版对照产物退役，并把 coverage.py / ask.py / luna_*.py 的 taxonomy 依赖摘掉；② 中文侧不再依赖 taxonomy 键；③ 删除后 `tools/check.py` 仍 pass。

## 8. 常用命令

    # 抓取（英文侧，原始数据落仓库外）
    uv run --no-project --offline python datasets/general/fetch.py --all --resume

    # 生成主产物（原生四元组）
    uv run --no-project --offline python datasets/general/convert.py --native --raw-root D:\pol2-raw

    # 语料合并（基座 + 能力源）
    uv run --no-project --offline python datasets/general/data/splits/build_corpus.py --help

    # 切分（盐在仓库外）
    uv run --no-project --offline python datasets/general/data/splits/split.py --help

    # 公开面内容审计（提交前必须 exit 0）
    uv run --no-project --offline python datasets/general/data/splits/split.py --audit-public-surface

    # 概率旁挂件导出（写盘前硬断言保留集不命中）
    uv run --no-project --offline python datasets/general/jev_fill.py probs-public --help

    # README 数字复算
    uv run --no-project --offline python datasets/general/readme_stats.py --help

    # HF 导出 + 仓库清单 + 全量 sha256 校验（离线、确定性）
    uv run --no-project --offline python datasets/general/export_hf.py all

    # 全仓检查（链接、registry、测试、保密护栏）
    uv run --no-project --offline python tools/check.py
