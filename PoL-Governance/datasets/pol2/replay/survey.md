# HuggingFace 通用决策数据审计（PoL2 回放池候选）

- 审计日期：2026-09-30（UTC+8）
- 审计人 / Agent：pol2-replay（DSH Agent Team），共享任务 task-4
- 上游依据：[SPEC.md](../../../SPEC.md)「准备数据」「教师生成与质量检查」、[datasets/README.md](../../README.md)、
  [datasets/pol2/README.md](../README.md)、[research/Chun/实施路径说明.md](../../../research/Chun/实施路径说明.md) 第六节
- 机器可读结果：[candidates.json](candidates.json)（人工判读表）、[audit-2026-09-30.json](audit-2026-09-30.json)（HF API 实时元数据快照 + 校验结果）
- 池规则与配比：[replay_pool.md](replay_pool.md)；改写与重判：[rewrite.py](rewrite.py)

## 0. 结论摘要

| 结论 | 数量 |
|---|---:|
| 落表候选（逐条给出许可、来源、形态、规模、分区、证据等级） | 68 |
| **准入**（只取 train，可进通用回放池） | **15** |
| 观察（许可/来源/去重/血缘缺证据，暂不入池） | 16 |
| 剔除 | 37（其中评测集/对抗考卷本体 **22**） |
| 检索覆盖 | 16 个搜索词，合并去重 728 个 dataset id；名称或标签落在 jev / typed-decision / system-one 命名法上的 146 个 |

**合格候选够用，不需要降低门槛。** 15 个准入数据集的 train 分区合计远超 9:1 与 8:2 两种配比的需要
（单 `ZefanCai/Open-Jev` 的 train 就有 266,793 行决策，`HIT-TMG/JevEmbed-Data` train 1,601,157 条判定）。
审计同时发现 3 类必须挡在训练之外的东西：**评测集本体的多语言衍生译本**、**train 分区内混入公开评测基准的
“训练混合包”**、**无真值/标签已知反向的数据集**。

## 1. 方法与证据

- **只用 HF 官方 API，固定 revision**。本环境 `web_fetch` 访问 huggingface.co 被拦（解析到非公网 IP），
  改用 PowerShell `Invoke-WebRequest` 直连 `https://huggingface.co/api/...`；随后固化成 [audit.py](audit.py)
  的 `fetch` 子命令（标准库 urllib，产物见 [audit-2026-09-30.json](audit-2026-09-30.json)）。
- **元数据**：`GET /api/datasets?search=<词>&limit=100`、`GET /api/datasets/{id}`（取 `sha`、`cardData.license`、
  `tags`、`language`、`lastModified`、`downloads`、`siblings`）、`GET /api/datasets/{id}/tree/main?recursive=true`（取文件与字节数）。
- **卡面**：按固定 revision 取 `/datasets/{id}/raw/{sha}/README.md`，51 份里读到 47 份（2 份在该 revision 上 404、
  2 份 TLS 失败；`SargeDev/jev-distill-corpus*` 即因 TLS 失败只能停在观察外的“未深审”状态）。失败项按「未知」记录，不猜。
- **小样本取证**：只用 HTTP Range 或 <1MB 的小文件，落在系统临时目录，**不下载大文件、不把第三方数据写进仓库**。
  本轮实际取证包括 `raw/citation-control-v1/train.jsonl.gz`（105,707 B → 解压 2,520 行，确认字段名）、
  `raw/mailroom-control-v1/validation.jsonl.gz`（仅核对字段，不入池）、`LICENSE-DATA`、`THIRD_PARTY_NOTICES.md`、
  `provenance/benchmark-overlap-screen.json`、`clearance.json`、以及 INSTRUCT_JEV/najd/fastino/rlcd/helmo/jevlite 的行级样例。
- **证据等级**：A＝读过卡面**并且**看过原始记录/许可文件/文件清单；B＝读过卡面字段与来源说明；
  C＝只看过元数据与卡面摘要；D＝只有搜索元数据（名称/标签）。**准入只接受 A/B。**
- **硬规则**（[audit.py](audit.py) 的 `verify` 强制，任何人改表都会被拦）：
  1. 评测集/对抗 benchmark 本体一律 `exclude`，不得 `admit`；
  2. `license_status` 为 unclear/none 的一律不得 `admit`；
  3. `admit` 必须 `train_only=true`、绑定 40 位 commit sha、证据 A/B；
  4. `admit` 要求 `license_training=yes` 且 `license_derivative ∈ {yes, yes_with_conditions}`；
  5. HF 元数据被启发式标记 benchmark/eval 时，除非写入 `benchmark_flag_review`（结论＋证据），否则不得 `admit`。

## 2. 检索覆盖

16 个搜索词（13 个进入 `audit.py fetch` 的默认值，另有 `probability+estimation`/`insufficiency`/`preference+judgement` 三个 0 命中）：
`jev`、`open-jev`、`typed-decision`、`typed_decision`、`system-one`、`system_one`、`decision`、`nli`、
`rlcd`、`judgement`、`judgment`、`entailment`、`risk-assessment`…
命中数（每词上限 100）：jev 100、open-jev 14、typed-decision 18、typed_decision 18、system-one 20、
system_one 20、decision 100、nli 100、rlcd 12、judgement 100、judgment 100、entailment 94、risk-assessment 100。

去重后 728 个 id，其中 146 个属于本任务关心的命名法。绝大多数命中是**同名噪声**（`jevonmao/*`、`jevtor/*`、
`aleksandar-jevtic-robco/*`、`Jevanleeuwen/*` 等个人账号或无关项目），未逐条落表；短名单 91 条 → 87 条有元数据
（4 条 401/不存在，含我误猜的 id），最终逐条落表 68 条。

## 3. 准入清单（15）

| 数据集 | 固定 revision | 许可（训练 / 衍生发布） | 任务形态 | 语言 | train 行数 | 生成方式 | 证据 |
|---|---|---|---|---|---|---|---|
| `ZefanCai/Open-Jev` | `c67699e13d0a` | cc0-1.0（训练✓ 衍生✓） | choice/noul/score | en/zh/tr | 266,793 | synthetic | A |
| `tasksource/procedural-typed-decisions` | `609513a3fadd` | apache-2.0（训练✓ 衍生✓） | choice/noul/score | en | 未知 | synthetic | A |
| `tasksource/tasksource-jev-typed-decisions` | `8173a06c7bb6` | other（逐行 license/license_use）（训练✓ 衍生需条件） | choice/noul/score | en/multilingual | 2,500,000 | mixed | B |
| `dwidlee/systemone-lite-general` | `c14eb7f7518f` | mit（训练✓ 衍生✓） | choice/noul/score | en | 32,400 | synthetic | A |
| `dwidlee/systemone-lite-phase2` | `3e283cb7d32f` | apache-2.0（训练✓ 衍生✓） | choice/noul/score | en | 240,800 | synthetic | B |
| `kaivoss/system-one-270m-data` | `f31d5a3f3da8` | apache-2.0（训练✓ 衍生✓） | choice/noul/score | en | 25,002 | teacher-distill | A |
| `soyrsoyr/jev-playground-rlcd-v0` | `3a7c53a49b70` | mit（训练✓ 衍生✓） | choice/noul/score | en | 25,000 | synthetic | A |
| `HIT-TMG/JevEmbed-Data` | `fc7f44305315` | apache-2.0\|cc0-1.0\|cc-by-4.0（逐行 license）（训练✓ 衍生需条件） | choice/noul/score | en | 1,601,157 | mixed | B |
| `najdresearch/system-one` | `788bc10036f4` | other（逐 pack，clearance.json）（训练✓ 衍生需条件） | choice/noul/score | en/ar | 3,284 | synthetic | A |
| `helmo/synthetic-typed-decisions` | `1827dc0d7f5a` | mit（训练✓ 衍生✓） | choice/noul/score | en | 未知 | synthetic | B |
| `n4ze3m/typed-decisions-synth` | `5ece89a225b2` | mit（训练✓ 衍生✓） | choice/noul/score | en | 未知 | synthetic | B |
| `DavidHatley/system-one-mini-data` | `319c9329b417` | apache-2.0（训练✓ 衍生✓） | score | en | 20,000 | synthetic | A |
| `fastino/fast-decisions` | `1a33070cabf9` | apache-2.0（训练✓ 衍生✓） | classification | en | 1,700 | unknown | B |
| `samatv256/jev-decisions-v1` | `c12aadf1f01c` | cc-by-4.0（训练✓ 衍生需条件） | choice | en | 12,000,000 | mixed | B |
| `shreyanbr/system-one-training-pairs` | `813f34c0fe71` | apache-2.0（训练✓ 衍生✓） | nli/choice | en | 未知 | teacher-distill | B |

准入的共性条件（每条都写进了 [candidates.json](candidates.json) 的 `decision_reason`）：

- **只取 train 分区**；test / validation / OOD / holdout / leaderboard 一律不参与训练与教师造数。
- **保留逐行溯源**：`dataset + revision + line_number + license`（外加 `group_id`）。
- **域外判别**：`samatv256/jev-decisions-v1`、`HIT-TMG/JevEmbed-Data`、`tasksource/tasksource-jev-typed-decisions`
  的许可是逐行/逐子集给出的，入库时必须按行过滤，不能按卡面的单一 SPDX 处理。
- **拆分必须按 group 而不是按行**：`kaivoss/system-one-270m-data`（按 `state_id`）、`najdresearch/system-one`
  （按 case）、`helmo/synthetic-typed-decisions`（按题组），否则同一 state 会跨区泄漏。
- **闭源教师必须点名**：`shreyanbr/system-one-training-pairs`（Claude Haiku 4.5）在池内标注
  `teacher=claude-haiku-4-5, closed`，其答案只作对照、绝不作为真值。

## 4. 观察清单（16，缺什么写什么）

| 数据集 | 固定 revision | 许可 | 来源与生成 | 为什么只观察 | 证据 |
|---|---|---|---|---|---|
| `TypeSafeAI/Open-Jev` | `538ce45e3e88` | cc0-1.0（训练✓ 衍生✓） | 与 ZefanCai/Open-Jev 同为 236 个文件、README 结构相同，仅项目 URL 与 load_dataset id 不同 | 疑似镜像/再发布；须按文件 sha256 逐字节比对后只保留一份，避免重复计数 | A |
| `OpenAGILab/Jev-dataset` | `4427393a93cc` | cc0-1.0（训练✓ 衍生✓） | README 与 ZefanCai/Open-Jev 逐字节一致（本轮已比对），文件清单同为 236 个 | README 逐字节相同的第三方再发布；按内容哈希去重后与 ZefanCai/Open-Jev 择一 | A |
| `ZefanCai/Open-Jev-v1.1` | `10ad6888333f` | other（CC0-1.0 原创 + WANLI CC BY 4.0）（训练✓ 衍生需条件） | community-hard-mix-v2 可再发布投影；101,207 条 WANLI 派生 NLI + 51,200 条原创受控行；附 benchmark-overlap-screen.json | 污染筛查与逐行来源说明质量最好，但许可分区混合（WANLI 需 CC BY 署名）且与 v1 的 replay 行大量重叠；补逐 source 过滤与跨库去重后可升为准入 | A |
| `vagmi/jevlite_dataset` | `b1c29cfe506a` | cc-by-sa-4.0（训练✓ 衍生需条件） | 教师给出完整概率分布（teacher_entropy 在行内）；卡面只写 a teacher model 未点名 | 许可为 SA（衍生发布需同许可）且教师血缘未点名，不满足「来源清楚」；补齐后可再议 | A |
| `pngwn/typed-decisions-v2` | `74a8ed2d0d28` | cc-by-sa-4.0（训练✓ 衍生需条件） | 修正版合成票据分流语料，labels 由生成器概率给出；raw jsonl 与 npz 双份 | 许可 SA 且主格式为绑定 tokenizer 的 npz（REPRESENTATION.md），转换成本与许可义务都高；若采用必须用 v2（v1 标签反向） | A |
| `pngwn/typed-decisions-v2-system-one` | `4af44cdb3cb6` | unknown（卡面无 license 字段）（训练? 衍生?） | 卡面无许可与来源说明，仅 README 与 parquet | 许可不明，按硬规则不得入池 | A |
| `pngwn/typed-decisions-causal-experiment` | `0529c3ba0f60` | unknown（卡面无 license，README 404）（训练? 衍生?） | 研究仓库，含 eval/ 脚本与 REPORT.md；README 在固定 revision 上 404 | 许可与用途不明且含评测脚本；补齐文档前不入池 | A |
| `hotchpotch/bekko-system-one-dataset-v0` | `5f67e4e2fd25` | unknown（卡面无 license 字段）（训练? 衍生?） | 用于训练 bekko-system-one-v0；有 training-manifest.json 与 quarantine-manifest.json，卡面声明 quarantine 配置不得进入评测 | 工程化程度高（成员清单/隔离清单）但卡面无许可；补许可声明后可优先复核 | B |
| `com-kotobalabs/typed-decisions-code-holes` | `d099aa2096b5` | apache-2.0（训练✓ 衍生✓） | 64 个公开仓库 git 历史的单 token 替换，gold 为提交实际写入的 token；来源片段带各自仓库许可 | gold 来自真实提交但任务形态是代码补全而非判断力回放，且上游代码许可逐仓库不同；价值与成本不匹配 | A |
| `shibing624/nli-zh-all` | `d9034b79da1d` | cc-by-4.0（训练✓ 衍生需条件） | 聚合 820 万条中文匹配/推理/摘要/问答数据（含 SimCLUE 等），卡面以 cc-by-4.0 发布 | 中文且体量大，但聚合多个上游数据集，上游许可与内容边界不透明；需逐项核实后再谈 | B |
| `MoritzLaurer/multilingual-NLI-26lang-2mil7` | `510a233972a0` | unknown（卡面无 license 字段）（训练? 衍生?） | 5 个英文 NLI 数据集的机器翻译（opus-mt/m2m100） | 许可不明；且为机翻产物，中文样本应按我们自己的改写+重判流水线生产，不照搬翻译标签 | B |
| `tasksource/defeasible-nli` | `7c4a57df9d8d` | apache-2.0（训练✓ 衍生✓） | DEFEASIBLE-NLI（Rudinger et al. 2020）：前提+更新+假设的可废止推理，正是「命中例外条件」 | 许可与主题都合适，但形态是 NLI 三元组；需改造为 choice/noul 并由教师重判后才能入池 | B |
| `tasksource/logical-entailment` | `5275a96cea76` | apache-2.0（训练✓ 衍生✓） | FOLIO 等逻辑蕴含语料（tasksource 规范化） | 同上：许可可以但形态为 NLI，需要改造与重判 | B |
| `AlexWortega/openjev-data` | `98ddc2bba169` | other（训练? 衍生?） | 多个 jsonl.gz 面板（distill/hardfmt/faith/longdoc 等）与 panel_manifest.json | 许可 other 且未逐项说明，面板命名无法判断是否含评测数据；本轮未深审 | C |
| `Mikhail/mini-jev-runs` | `8f84bb1a789b` | mit（训练✓ 衍生✓） | 小规模对照实验记录（成本/长度/选项扰动） | 是实验产物而非决策语料，规模与形态均不匹配 | C |
| `reachjalil/jev-tree-choice-cap` | `6f7a325a3010` | mit（训练✓ 衍生✓） | 分层/截断选项的实验对比数据（n<1K） | 实验数据、量级过小 | C |

## 5. 剔除清单

### 5.1 评测集 / 对抗考卷本体（22，硬规则整库剔除）

| 数据集 | 它是什么 | 剔除理由 | 证据 |
|---|---|---|---|
| `LocalLLaMA/typed-decisions` | 自称 benchmark：400 案/2000 判定的 test 分区 + 排行榜；gold 为约 4B 教师三样本均值 | 本体即评测集（标题 A benchmark for typed probabilistic decisions，含 leaderboard 与 test 分区）。按 SPEC 公开测试集与对抗考卷不得进训练，整库剔除；train 分区同属该 benchmark 题池，也不使用 | A |
| `s1lv3rj1nx/openjev-heldout` | 七个任务的泛化评测套件（clinc_oos/banking77/massive/sst5/helpsteer/ag_news/civil_comments） | 评测套件本体，硬规则剔除 | A |
| `Praveenrajus/jev-bench` | 166,054 行 / 22,773 条 test 记录、43 个模型排行榜 | 卡面即 benchmark，含 test 与 leaderboard；按硬规则整库剔除，不得进训练池 | A |
| `Luni/laya-jev-benchmark` | Laya vs Jev 对比评测 | 标签含 benchmark/evaluation；按硬规则整库剔除，不得进训练池 | A |
| `AirsideLabs/notam-typed-decisions` | 三个 4,241 行 DEEL test 套件 + 8,000 行多问题套件 | 卡面标签含 benchmark/evaluation，全部是 frozen test suites；按硬规则整库剔除，不得进训练池 | A |
| `blazeofchi/system-one-eval` | 60 个任务 / 70 个问题，自述 diagnostic set | 名称与卡面即 eval，且答案公开；按硬规则整库剔除，不得进训练池 | A |
| `dylantom2012/open-system-one-bench` | 10,000 条决策的逐项预测 | 卡面标签含 benchmark；按硬规则整库剔除，不得进训练池 | A |
| `apus-ailab/APUS-OpenJev-Eval-Frozen80` | 冻结 80 题评测 | 名称即 eval；卡面无许可；按硬规则整库剔除，不得进训练池 | A |
| `pngwn/open-jev-laya-bench` | OpenJev/Laya 对比评测 | 名称即 bench；卡面无许可；按硬规则整库剔除，不得进训练池 | A |
| `kishida/jev-bench` | 日语 jev 基准 | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `hayriyigit/jev-bench-tr` | 土耳其语 jev 基准 | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `atmaneayoub/jev-ar-bench` | 阿拉伯语 jev 基准 | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `earino/ecbs5200-jev-benchmark` | 课程基准 | 名称即 benchmark；按硬规则整库剔除，不得进训练池 | A |
| `lisonallen/jev-ai-benchmark` | jev AI 基准 | 名称即 benchmark；按硬规则整库剔除，不得进训练池 | A |
| `Leanmcp/jevbench` | 797 文件的 jevbench | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `SamuelChien821/typed-decision-bench` | 115 文件的 typed-decision bench | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `akhilaaa3/decision-bench` | 决策基准 | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `Hanno-Labs/decision-bench` | 决策基准 | 名称即 bench；按硬规则整库剔除，不得进训练池 | A |
| `reachjalil/jevlogs-log-triage-benchmark` | 日志分诊基准 | 名称即 benchmark；按硬规则整库剔除，不得进训练池 | A |
| `Nebulaw1/jev-legal-judgment-tests` | 中文法律判断测试集 | 名称即 tests；中文评测集尤其不得入池；按硬规则整库剔除，不得进训练池 | A |
| `morrenhale/decision-benchmark-jev-laya-julia` | 跨模型对比基准 | 名称即 benchmark；按硬规则整库剔除，不得进训练池 | A |
| `marcmagn1/jev-alt-systemone-eval` | 备选 System One 评测 | 名称即 eval；README 在固定 revision 上 404；按硬规则整库剔除，不得进训练池 | A |

其中三条是**中文相关**的，值得单独点名：`Nebulaw1/jev-legal-judgment-tests`（中文法律判断测试集）、
`GeneLab/typed-decisions-ja` 与 `telepatia-ai/typed-decisions-pt-es`（把 `LocalLLaMA/typed-decisions`
这一 benchmark 翻成日/葡/西语，训练它们等于同时污染原 benchmark 与译本）。

### 5.2 其他剔除（15）

| 数据集 | 许可 | 剔除理由 | 证据 |
|---|---|---|---|
| `s1lv3rj1nx/openjev-mixture` | apache-2.0（组装）（训练✓ 衍生需条件） | train 分区直接包含 MMLU/BIG-bench/ARC/GLUE 等公开评测基准；作者只与自有 heldout 去重，未排除通用评测基准。硬规则剔除 | A |
| `shenjunhao/OpenJevData-140k` | mit（仅原创部分）（训练✓ 衍生需条件） | 上游混合多个公开评测基准家族，且 MIT 只覆盖原创贡献、逐行许可未解决；无法保证不把评测数据带入训练 | B |
| `pngwn/typed-decisions` | cc-by-sa-4.0（训练✓ 衍生需条件） | 已知缺陷：escalate 标签在 100% 行上与其定义的后验互补（v2 已修正）。缺陷版本不得入池 | A |
| `pngwn/system-one-decisions` | cc-by-nc-4.0（训练✗ 衍生✗） | NC 许可与非商业限制，与本项目公开发布及后续商用不确定性冲突 | B |
| `yipyany/ted-translation-decisions-en-zh` | cc-by-nc-4.0（训练✗ 衍生✗） | NC 许可；任务形态是翻译决策（语境/语用），不是 typed decision 判断力回放 | B |
| `ctaxnagomi/INSTRUCT_JEV` | mit（训练✓ 衍生✓） | 抽样取证显示绝大多数行是文档问答（output 为文档正文），不是可判定决策样本；剔除 | A |
| `com-kotobalabs/typed-decisions-repo-governance` | apache-2.0（训练✓ 衍生✓） | 无真值：卡面明写 gold 全为 null、prediction 不得当真值，不满足真值须独立裁决 | A |
| `GeneLab/typed-decisions-ja` | apache-2.0（训练✓ 衍生✓） | 评测集译本：训练会同时污染原 benchmark 与其译本 | A |
| `yyhlm/typed-decisions-ru` | apache-2.0（训练✓ 衍生✓） | 评测集衍生译本 | B |
| `telepatia-ai/typed-decisions-pt-es` | apache-2.0（训练✓ 衍生✓） | 评测集衍生译本；没有理由只取其 train 而为该 benchmark 增污染 | A |
| `ai-simonsk13/id-typed-decisions` | apache-2.0（训练✓ 衍生✓） | 无任何来源/生成/许可说明，无法核实；且没有可补的证据线索 | A |
| `shibing624/nli_zh` | cc-by-4.0（训练✓ 衍生需条件） | 无数据本体（脚本仓库），无可入池内容 | A |
| `clduab11/jev-calibration-statistics` | mit（训练✓ 衍生✓） | 是统计结果而非决策样本，无可训练内容 | B |
| `egetheengineer/jevcraft` | cc-by-sa-4.0（训练✓ 衍生需条件） | 形态为视频录制，与文本 typed decision 不同构 | D |
| `FaroukMoc2/jev-stage2-image-beans-pilot` | mit（训练✓ 衍生✓） | 多模态图像任务，与文本判断力回放不同构 | D |

## 6. 关键发现（审计的价值所在）

1. **同一个 Open-Jev 数据集有 3 个再发布**（`ZefanCai/Open-Jev`、`TypeSafeAI/Open-Jev`、`OpenAGILab/Jev-dataset`，
   都是 236 个文件；`OpenAGILab` 的 README 与 `ZefanCai` 逐字节相同，`TypeSafeAI` 只改了项目 URL 与
   `load_dataset` 的 id）。不按内容哈希去重就会把同一批 26.7 万行训练数据算成三份。
2. **“训练混合包”里可能藏着公开评测基准**：`s1lv3rj1nx/openjev-mixture` 的 train 目录里有 92 个公开评测任务
   （52 个 `bigbench_*`、12 个 `mmlu_*`、`ai2_arc`、`hellaswag`、`glue/super_glue`、`truthful_qa`、`winogrande`、
   `race`、`openbookqa`、`piqa`、`math_qa` 等）。作者只做了与自有 heldout 套件的去重，没有排除通用评测基准。
   这类包一旦进池，我们所有外部 benchmark 数字都不可信。
3. **评测集的译本是最容易被误收的一类**：`GeneLab/typed-decisions-ja`、`telepatia-ai/typed-decisions-pt-es`、
   `yyhlm/typed-decisions-ru` 都自带 Apache-2.0 卡面、结构干净，但本体是别家的 benchmark。
4. **标签已知反向的版本必须点名禁用**：`pngwn/typed-decisions` v1 的 `escalate` 标签与它自己定义的后验互补
   （100% 行），v2 才修好。收数据不能只看名字新不新。
5. **“文档语料”和“决策数据”长得一样**：`ctaxnagomi/INSTRUCT_JEV` 卡面写 choice/noul/score 三件套，
   实际 119 行里只有 7 行带答案、24 行有 question block，其余是 TypeSafe 文档正文问答（抽样见附录）。剔除。
6. **没有真值的数据集不能靠“模型输出”补**：`com-kotobalabs/typed-decisions-repo-governance` 的
   `questions[].gold` 全是 `null`，只有 Jev 预测；卡面自己写明 prediction 不得当真值。
7. **污染筛查可以是证据**：`ZefanCai/Open-Jev-v1.1` 附 `provenance/benchmark-overlap-screen.json`
   （531 条 benchmark 请求、0 命中、并列出「词面筛查查不出改写、也不覆盖预训练暴露」等限制）。
   这种自曝边界的卡面比“我保证干净”可信得多；它没进准入只是因为许可分区混合（WANLI 需 CC BY 署名）
   且与 v1 的 replay 行大量重叠，补上逐 source 过滤与去重后可升为准入。
8. **许可问题集中在三处**：NC（`pngwn/system-one-decisions`、`yipyany/ted-translation-decisions-en-zh`）、
   SA（`vagmi/jevlite_dataset`、`pngwn/typed-decisions*`）、以及“卡面根本没写许可”
   （`hotchpotch/bekko-system-one-dataset-v0`、`MoritzLaurer/multilingual-NLI-26lang-2mil7`、
   `pngwn/typed-decisions-v2-system-one`、`pngwn/typed-decisions-causal-experiment`、`AlexWortega/openjev-data`）。
   后两类一律停在观察项，即使内容看起来很好。

## 7. 与 SPEC / 数据契约的对应

| SPEC 要求 | 本审计的落实 |
|---|---|
| 通用:PoL = 9:1 或 8:2，**只有 PoL 的 70% train 分区**参与混合 | [replay_pool.md](replay_pool.md) 给出按**决策数**（不是 case 数）计算的配比表；回放池自身 100% train-only，不设独立 dev/calibration/holdout 分区 |
| 不把公开测试集和对抗考卷放进训练 | 22 个评测集本体整库剔除；`audit.py verify` 使「评测集被 admit」直接失败 |
| 只使用许可与来源清楚的分区 | 15 个准入条目全部有固定 revision + 训练/衍生发布判读；许可不明进观察项 |
| 先改写成自然的中文语境，改写后重新判断，不能照搬英文标签 | [rewrite.py](rewrite.py)：prepare 不把英文标签放进提示，改写与重判必须不同血缘，`verify` 拒绝 `label_source != judge`、拒绝未改写的中文、拒绝重算前的去重键 |
| 保留原始来源、版本、行号和许可证记录 | 每条回放记录携带 `source.{dataset,revision,line_number,license,split,group_id}` |
| 记录来源与许可；不把同源教师一致当真值 | 准入清单里闭源教师（Claude Haiku 4.5）明确标注；`tasksource` 明确「不是教师模型产物，是既有数据集的规范化」 |

## 8. 未测项与限制

- **没有下载任何数据集正文**（>50MB 的一律只登记链接与字节数）。除 2 个 raw 分片与 10 个小样本外，
  字段与规模信息来自卡面与文件清单，未逐行复核。
- **镜像等价性未做字节级校验**：`ZefanCai/Open-Jev` / `TypeSafeAI/Open-Jev` / `OpenAGILab/Jev-dataset`
  只核对了文件清单（236 个）与 README（其中 OpenAGILab 逐字节相同）；入库前须按文件 sha256 逐字节比对。
- **卡面声明未抽检**：`tasksource/tasksource-jev-typed-decisions` 声称“已排除评测基准”、
  `dwidlee/systemone-lite-phase2` 的“0.00% train∩test 重叠”、`HIT-TMG/JevEmbed-Data` 的
  `docs/PROCESSING_REPORT.md`，本轮都只当作**声明**（证据等级因此给 B，不是 A）。
- **未做真实改写**：`rewrite.py` 只跑了离线 fixture；真实英译中改写与教师重判需要 Lead 批准后才会调用，且会花钱。
- **跨语言/跨来源的语义近重复**没有工具化：目前只有内容哈希去重键；语义近重复（同情节的翻译与改写）
  必须在上池时用教师比对，否则 PoL 专项合同里「同情节、翻译和改写不得跨区」的约束无法延伸到回放池。
- **未核对私有保留集**：`private_holdout` 内容不在仓库，也无法与之比对；回放池只承诺不掺入任何 PoL 的
  public_test/validation，且不做任何 PoL 分区采样。
- **许可结论不是法律意见**：`license_training`/`license_derivative` 是按卡面与 LICENSE 文本的工程判读。

## 9. 复现命令

```powershell
# 1) 联网复核：拉取 HF 元数据并按固定 revision 与准入规则校验（缓存落在系统临时目录）
uv run --no-project --offline python datasets/pol2/replay/audit.py fetch --out datasets/pol2/replay/audit-2026-09-30.json

# 2) 离线校验已有审计快照（CI/断网可用）
uv run --no-project --offline python datasets/pol2/replay/audit.py verify --audit datasets/pol2/replay/audit-2026-09-30.json

# 3) 离线跑通改写 + 重判链路（fixture 伪改写，不是翻译也不是真值）
uv run --no-project --offline python datasets/pol2/replay/rewrite.py prepare \
    --source datasets/pol2/replay/fixtures/rewrite/en-source.jsonl \
    --candidates datasets/pol2/replay/fixtures/rewrite/candidates.json --out <临时目录>
uv run --no-project --offline python datasets/pol2/replay/rewrite.py run --out <临时目录> --fixture
uv run --no-project --offline python datasets/pol2/replay/rewrite.py verify --records <临时目录>/zh.records.jsonl

# 4) 本目录测试（全离线）
uv run --no-project --offline python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q
```

## 10. 证据附录（命令与输出摘要）

| 证据 | 命令 | 输出摘要 |
|---|---|---|
| HF API 可达 | `Invoke-WebRequest 'https://huggingface.co/api/datasets?search=jev&limit=20'` | HTTP 200，21,518 字节，首条 `ZefanCai/Open-Jev` |
| 命名法搜索 | 13 个默认搜索词 | `search_hits`：jev 100 / open-jev 14 / typed-decision 18 / system-one 20 / decision 100 / nli 100 / rlcd 12 / entailment 94 / risk-assessment 100… |
| 固定 revision 与许可 | `/api/datasets/{id}`（短名单 87 条） | 落表的 68 条全部绑定 40 位 sha；`audit.py fetch` 实时复核 `problems: 0`，summary：admit 15 / observe 16 / exclude 37 |
| 字节数 | `/tree/main?recursive=true`（20 个仓库的递归清单） | `samatv256/jev-decisions-v1` 22.22GB（12 个分片 >50MB）、`tasksource/tasksource-jev-typed-decisions` 1.52GB（13 个 >50MB）、`HIT-TMG/JevEmbed-Data` 388.7MB（3 个 >50MB）、`ZefanCai/Open-Jev` 86.8MB（无单文件 >50MB） |
| 逐行溯源字段 | 解压 `raw/citation-control-v1/train.jsonl.gz` | 105,707 B → 2,520 行；字段 `group_id,id,kind,metadata,options,question,source,split,state,target`；`metadata.provenance.license=CC0-1.0`、`generator_version=citation-control-v1`、`seed=42` |
| 许可文本 | `LICENSE-DATA`、`THIRD_PARTY_NOTICES.md`（按 revision 取） | 原创记录 CC0-1.0；Wikispeedia 行因无法核实图路径许可被剔除；未验证许可的 TypeSafe 文档措辞不随包再许可 |
| 污染筛查 | `provenance/benchmark-overlap-screen.json`（Open-Jev v1.1） | `status=no_detected_overlap`，531 条请求、`matched_rows=0`，并列出“词面筛查查不出改写、不覆盖预训练暴露” |
| 评测集混入证据 | `/tree/main?recursive=true`（openjev-mixture） | 281 个任务目录中 92 个是公开评测任务（`mmlu_*` 12、`bigbench_*` 52、`ai2_arc`、`glue_*`、`hellaswag`、`truthful_qa`…） |
| 文档语料冒充决策数据 | `metadata.json` + `choice.jsonl` 抽样（INSTRUCT_JEV） | `rows: 119`、`per_function_type: {choice 47, noul 51, score 21}`、`rows_with_answers: 7`、`rows_with_question_block: 24`；第二行为文档正文 |
| 无真值 | 卡面（repo-governance） | 每个 `questions[].gold` 为 `null`，只有 `prediction`，卡面写明不得当真值 |
| 反向标签 | 卡面（pngwn/typed-decisions-v2） | `escalate` 在 v1 中 100% 行与其定义互补，v2 修正 |
| 逐包许可 | `clearance.json`（najdresearch/system-one） | 逐 pack license（CC-BY-4.0 / CC-BY-SA-4.0 / MIT / Apache-2.0），`controlled-reserved_evaluation` 为作者保留评测包 |
| 本目录测试 | `python -m unittest discover -s datasets/pol2/replay -p "test_*.py" -q` | 53 项全绿（审计规则、镜像/许可/漂移校验、改写门禁与去重门） |

## 11. 交接建议

1. Lead 复核本表后，把准入的 15 条写进 `datasets/registry.json`（本任务边界在本目录内，未改该文件）。
2. 首次真正取数时先做两件事：按文件 sha256 合并三个 Open-Jev 再发布；对两个 `tasksource` 数据集
   与 `HIT-TMG/JevEmbed-Data` 做逐行许可过滤抽检（各 200 行即可）。
3. 语义近重复筛查（同情节翻译/改写）与中文改写重判同一个批次做，避免同一情节重复付两次费。
