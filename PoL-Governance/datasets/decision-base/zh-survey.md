# 中文决策数据调研与准入（decision-base 中文来源）

- 调研日期：2026-10-02（UTC+8）
- 执行：pol2-replay（DSH Agent Team），共享任务 task-11
- 上游依据：[datasets/decision-base/README.md](README.md)（契约）、[taxonomy.py](taxonomy.py)（问题键）、
  [sources.json](sources.json)（英文来源清单）、[../../SPEC.md](../../SPEC.md)、[../../research/Wenbo/data.md](../../research/Wenbo/data.md)
- 方法沿用 [datasets/pol2/replay/survey.md](../pol2/replay/survey.md)：固定 revision、逐条许可判读、剔除评测集、标注证据等级
- 机器可读准入清单：[sources.zh.json](sources.zh.json)；抓取+转换：[convert_zh.py](convert_zh.py)；离线测试：[test_convert_zh.py](test_convert_zh.py)

## 0. 结论摘要

| 结论 | 数量 / 说明 |
|---|---|
| 检索覆盖 | 95 次 HF 检索（含 `filter=language:zh`），去重 **1,906** 个 dataset id |
| 逐条核对 | 49 份 HF 元数据（固定 revision）、20 份卡面、25 份 datasets-server 字段快照、14 份文件清单、8 组行抽样 |
| **准入** | **9 个数据集 / 12 个来源配置**（train-only），row_limit 合计 **45,608** 条 |
| 覆盖域 | human_judgment / risk_harm / social_moral **三个域** |
| 机器翻译（不优先，单独列出） | 8 个数据集（见第 3 节）；**没有**把机翻英文数据当中文来源 |
| 评测集 / 对抗考卷（不进训练） | 6 个数据集（第 4 节）+ 2 个 TC260 镜像 |
| 许可不明 / NC | 6 个数据集（第 4 节） |
| --limit 200 试点 | 12 个来源全部打通：**2,154 条中文条目，item_errors=0**，native_target_rate **90.6%** |

**结论：中文来源足够。** 现有 37,124 条英文若原样保留，中文要占 ≥30% 需要 ≈15,911 条；
本次准入来源按 pilot 的实测产出率外推可得 **≈4.4 万条**中文条目（第 7 节），缺口不是数量而是
「更多中文原生、可判定的来源」——因此没有降低门槛：许可不明、NC、机翻、评测集一律不进准入。

## 1. 方法与证据

- **只用 HF 官方接口**：`GET /api/datasets?search=...&filter=language:zh`（枚举）、`GET /api/datasets/{id}`（sha 与卡面许可）、
  `/tree/main?recursive=true`（文件与字节数）、`/raw/{sha}/README.md`（按 revision 取卡面）。
  本环境 `web_fetch` 访问 huggingface.co 被拦，统一用 pwsh `Invoke-WebRequest`。
- **行级证据走 datasets-server**：`/splits`、`/first-rows`、`/rows`（`length ≤ 100`、深 offset 不可用、config 名需转义——
  这些坑见 [fetch.py](fetch.py) 头部说明，抓取直接复用该实现）。
- **小样本取证**：只取 HTTP Range 或小文件，落系统临时目录，不入仓库；本轮读了 THU Safety-Prompts 的两个 JSON 头部、
  TC260 的 schema.json/DATA_STATEMENT.md、Nemotron zh/train.jsonl 头部等。
- **许可链核实**：对二次上传的来源，回溯上游许可。例：`Skepsun/cvalues_rlhf` 声明 apache-2.0，
  本轮实测 `raw.githubusercontent.com/X-PLUG/CValues/main/LICENSE` = Apache-2.0（Copyright 2023 Alibaba X-PLUG Team），
  授权链成立，因此准入。
- **证据等级**：A＝读过卡面 + 实际行数据或原始许可文件；B＝读过卡面 + 行抽样（含标注语义核对）；
  C＝只有元数据与摘要；D＝只有检索元数据。**准入只接受 A/B。**
- **两条用户硬约束的落实**：
  1. **优先现成中文来源，不做翻译**：准入的 12 个来源全部是原生中文内容，targets 直接来自来源标注或卡面口径；
     本任务没有做任何英译中改写。
  2. **机翻英文数据不算中文来源**：所有由英文数据集翻译/文化适配而来的来源（PolyGuardMix、Nemotron-Safety-Guard、
     DirectLLM/Chinese_Preference、hh_rlhf-chinese-zhtw、OpenOrca-Traditional-Chinese、BRIGHTER、zzhdbw 繁→简 等）
     一律写进 `excluded`（第 3 节），标注机翻理由，不进准入。

## 2. 准入清单（9 个数据集 / 12 个来源）

| slug | HF dataset | 固定 revision | 许可 | config/split | 域 | 转换器 | row_limit | 证据 |
|---|---|---|---|---|---|---|---|---|
| `cvalues-rlhf` | `Skepsun/cvalues_rlhf` | `130d6cc61440` | apache-2.0 | default/train | risk_harm | cvalues | 18000 | B |
| `zhihu-preference` | `liyucheng/zhihu_rlhf_3k` | `97c801e01626` | cc-by-2.0 | default/train | social_moral | zhihu_pref | 3460 | B |
| `chinese-emotion-dialogue` | `Johnson8187/Chinese_Multi-Emotion_Dialogue_Dataset` | `f3854f948907` | mit | default/train | human_judgment | emotion_zh | 4159 | A |
| `chinese-logic-sentiment` | `YiMeng-SYSU/chinese-logic-sentiment-dataset` | `09cb1ba399dd` | apache-2.0 | default/train | human_judgment | sentiment_zh | 2176 | A |
| `baidu-review-sentiment` | `left0ver/sentiment-classification` | `2f78a31b0c7d` | mit | default/train | human_judgment | sentiment_binary_zh | 9146 | B |
| `toxic-zh` | `textdetox/multilingual_toxicity_dataset` | `01907546324b` | openrail++ | default/zh | human_judgment | toxicity_zh | 5000 | B |
| `elder-scam-zh` | `vanila434/multilingual-elder-safety-msgs` | `b80037750209` | cc-by-4.0 | default/train | risk_harm | elder_scam | 1029 | B |
| `med-guard-unsafe` | `chenhaodev/med-guard-safety-synth` | `63374505e88f` | apache-2.0 | unsafe/train | risk_harm | med_guard | 320 | A |
| `med-guard-controversial` | `chenhaodev/med-guard-safety-synth` | `63374505e88f` | apache-2.0 | controversial/train | risk_harm | med_guard | 120 | A |
| `med-guard-benign-r1r5` | `chenhaodev/med-guard-safety-synth` | `63374505e88f` | apache-2.0 | benign_r1_r5/train | risk_harm | med_guard | 300 | A |
| `med-guard-benign-r6r11` | `chenhaodev/med-guard-safety-synth` | `63374505e88f` | apache-2.0 | benign_r6_r11/train | risk_harm | med_guard | 300 | A |
| `mh-risk-triage-zh` | `BEncoderRT/User_Intent_Risk_Triage` | `72ee9b506993` | apache-2.0 | default/train | risk_harm | mh_triage | 1598 | B |

合计 row_limit **45,608**，单一来源最大占比 39.5%（cvalues-rlhf 18,000）≤ 40% 上限。

准入的共性条件（逐条写在 [sources.zh.json](sources.zh.json) 的 `notes` 里）：

- **只取 train**（唯一例外是 `textdetox` 的中文子集：它的中文是一个语言 split，来源清单里单独注明）。
- **targets 分两类映射**：`direct`（源字段就是答案，如 `textdetox.toxic → toxicity_present`）与
  `documented`（按卡面或抽样证据做的一次有据可查的映射，如 CValues 的 `pos_type=拒绝为主 → refusal_appropriate=yes`）。
  `--mappings direct` 可只保留 direct；两类都写进 `meta.quality_flags`。
- **不硬塞**：映射不上的源字段（知乎的 chosen/rejected 与票数、med-guard 的 categories、mh-triage 的 strategy 词表）
  原文进 `meta.source_record`，targets 留空等外部答案源。
- **许可判读**：apache-2.0 / mit / cc-by-2.0 / cc-by-4.0 → 允许训练与衍生（署名）；
  openrail++ → 允许训练与衍生，但衍生物须沿用同一使用限制。

### 逐条要点

- **cvalues-rlhf**（Skepsun/cvalues_rlhf，18,000）：CValues-Comparison 的中文价值观对齐数据，
  `pos_type` 是人工标注「妥当回应」的类型，`拒绝为主`/`拒绝&正向建议` 都表明【拒绝】是妥当回应，
  映射 `refusal_appropriate=yes`（documented）；风险回复/纯拒绝原文进 meta。这是本批唯一的大体量中文来源，
  也是唯一触及「该不该拒绝」的中文监督。
- **zhihu-preference**（liyucheng/zhihu_rlhf_3k，3,460）：知乎真实问答的人类偏好（高赞 vs 低赞回答 + 票数）。
  taxonomy 没有「哪个回答更好」的键，因此**不硬塞偏好标签**，只作 state（域归 social_moral：生活/价值/人际情境）。
- **chinese-emotion-dialogue**（Johnson8187，4,159）：繁体中文口语/影视对白 8 类情绪，人工标注。
  `emotion → emotion_primary` 为 documented 映射，未在表内的标签打 `unmapped_emotion` 旗标留空。
- **chinese-logic-sentiment**（YiMeng-SYSU，2,176）：豆包生成 + 人工清洗的中文逻辑情感（反讽/双重否定/转折），
  卡面明确 label 0=负面 1=正面。
- **baidu-review-sentiment**（left0ver，9,146）：百度飞桨公开的中文商品/酒店评论情感数据；卡面没写 label 极性，
  本次用 30 条抽样核对（正面=1、负面=0）后才做 documented 映射，抽检结论写进 `quality_flags`。
- **toxic-zh**（textdetox，5,000）：PAN TextDetox 的中文毒性二分类子集，`text/toxic` 直接是 toxicity_present 的答案。
  **注意**：卡面列了各语言原始来源但没单列中文来源，属来源说明不完整 → 证据 B，只当 state+硬标签，不外推。
- **elder-scam-zh**（vanila434，1,029）：手写中文/粤语长者防诈骗场景，label ∈ {safe, scam, ambiguous}；
  只收 `language ∈ {mandarin, cantonese, code_mixed_*}` 的行（实测 200 行里 29 行是英文/其它语，被跳过）。
- **med-guard-***（chenhaodev，4 个配置共 1,040）：中文健康/康养护栏数据，针对真实生产系统的 11 类误报根因。
  `safety → contains_harm`、`action → recommended_action`（放行=allow、观察=review、拦截=block）都是 documented 映射；
  benign 两档正是「过度限制/误拦」的负样本（contains_harm=no + allow）。
- **mh-risk-triage-zh**（BEncoderRT，1,598）：中文心理危机风险分级，`risk high → escalation_needed=yes`、
  `low → no`（documented）；medium/ambiguous 留空；strategy 词表与 `response_style` 不是等义枚举，只进 meta。

## 3. 机器翻译 / 文化适配来源（明确不优先，逐条记录理由）

用户硬约束：**不要把机器翻译出来的英文数据集当成中文数据集**。以下来源都是「中文文本 + 英文血统」，
单独列出、进 `excluded`，不作为中文来源使用：

| dataset | 规模 | 为什么是机翻/文化适配 |
|---|---:|---|
| `nvidia/Nemotron-Safety-Guard-Dataset-v3` | 45 万（12 语） | 卡面：CultureGuard 管线「culturally adapts and translates content from the English Aegis 2.0」 |
| `ToxicityPrompts/PolyGuardMix` | 191 万（17 语） | 卡面：自然多语交互 + WildGuardMix 的**人验机翻**混合；`metadata.source=wildguardmix_translated_*` |
| `DirectLLM/Chinese_Preference_Safe_and_Helpful` | 100 万+ | 英文 HH-RLHF/SHP 的中文译本（目录 SHP/、hh_rlhf_harmful/；抽样有明显机翻痕迹） |
| `erhwenkuo/hh_rlhf-chinese-zhtw` | 10 万+ | HH-RLHF 繁中译本 |
| `lchakkei/OpenOrca-Traditional-Chinese` | 1000 万+ | OpenOrca 繁中译本 |
| `brighter-dataset/BRIGHTER-emotion-categories` | 20+ 语 | GoEmotions 的多语机翻扩展（含 `chn` 配置） |
| `zzhdbw/Simplified_Chinese_Multi-Emotion_Dialogue_Dataset` | 4,159 | 卡面：用 Qwen2.5-32B 把 Johnson8187 繁中数据**机器转写**为简体（与原始来源同内容，去重后只用原始来源） |
| `TIX007/chinese-sentiment` | 20,000 | 卡面自述由英文 `dair-ai/emotion` **模板扩增**生成（annotations_creators=machine-generated），多样性低 |
| `shibing624/DPO-En-Zh-20k-Preference` | 20,000 | zh 配置中 10k 来自 wenbopan/Chinese-dpo-pairs，另 10k 是英文 DPO 数据；原生/翻译成分未逐条可辨 |

**为什么不直接收**：改写/重译成本高且会语义漂移（用户约束 1），而机翻数据的「中文语感」与标注语义都是二手的：
用它训练等于把英文标注体系经翻译器引入中文侧。宁可少而真：本批准入的中文来源虽然量小，
但每一条的标签都是来源自己面向中文标注的。

## 4. 评测集、许可不明与不可达来源（不进训练）

| dataset | 类别 | 处理 |
|---|---|---|
| `thu-coai/Safety-Prompts`（100K 中文安全提示） | 对抗/安全评测语料（THU CoAI 安全榜单用），无 train/test 划分 | 登记为**外部评测**，不进训练 |
| `BBBBBBBBBBBQ/TC260-Chinese-Safety-Prompts` + `MuYi23/…`（同一份，4,997 条合成对抗提示） | 卡面自述「安全评测数据集」，含 public/validation/test，且 `review_status=pending` 的 silver 数据 | 登记为**外部评测**（两份互为镜像，只登记一次） |
| `thu-coai/SafetyBench`、`SUSTech/ChineseSafe`、`zjunlp/ChineseHarm-bench`、`OpenStellarTeam/Chinese-SafetyQA`、`Paul/hatecheck-mandarin` | 中文安全/毒性评测集（部分同时是 NC 许可） | 剔除，不进训练 |
| `clue/clue` + `suolyer/ocnli` + `suolyer/cmnli` | CLUE 官方卡面 license=unknown；二次上传自述 apache-2.0 不构成授权链（且 CMNLI 本身是 MNLI 的中文翻译版） | 观察（补上游许可后可复核） |
| `m-a-p/COIG-CQIA`（NONE）、`BAAI/COIG-PC`（unknown）、`hasankursun/multilingual-safety-classification-dataset`（NC-SA） | 许可不明 / NC | 剔除 |
| `qundao/data-zh-legal-judgements`、`morinoppp/ethics`、`LookingJuicy/Chinese-Emotional-Intelligence`、`NNaiyi/divorce-judge-questions` | HF API 401/500，本轮不可达 | 观察（不是"没有"，是"没查到"） |

## 5. 中文原生但本轮未入选（宁缺毋滥，不是没有中文）

| dataset | 为什么没进准入 |
|---|---|
| `BAAI/COIG`（97,739 条 NoTranslate 配置，apache-2.0） | 中文原生、许可清楚，但形态是**通用指令/多轮问答**，不是「待判断的情境」；用作决策 item 会把状态与问题错配。可另作通用能力回归语料评估。 |
| `BAAI/Infinity-Preference`（59,338 条，apache-2.0） | 抽样 100 条里仅 ≈7% 是中文 prompt；中文部分的来源与是否翻译未逐条说明。 |
| `david9dragon9/cvalues-chinese`（477MB） | 与 Skepsun/cvalues_rlhf 同源，但上传者**随机重切** train/val/test 且单文件 477MB；去重后只取 Skepsun 版本。 |
| `shibing624/nli_zh`、`shibing624/nli-zh-all` | 前者仓库只有 README 与脚本（无数据）；后者聚合多个上游数据集，上游许可不透明。 |
| `i-Lang/ilang-judge-observations`、`valuesimplex-ai-lab/FinCPRG`、`MiniMaxAI/SynLogic`、`sojuL/RubricHub_v1` | 分别是不含 state 的判日志、检索语料+qrels、实际为英文的逻辑题、英文 rubric 数据。 |

## 6. `--limit 200` 试点实测（12 个来源全部打通）

命令（原始数据落 `D:\pol2-raw\<slug>\`，条目落 `D:\pol2-raw\zh-items\items.zh.jsonl`，**都不进仓库**）：

```powershell
uv run --no-project --offline python datasets/decision-base/convert_zh.py run --all --limit 200 \
    --out D:\pol2-raw\zh-items\items.zh.jsonl
```

| slug | 抓取行 | 条目 | 带真值 | 真值率 | 跳过 |
|---|---:|---:|---:|---:|---|
| cvalues-rlhf | 200 | 200 | 200 | 1.00 | — |
| zhihu-preference | 200 | 149 | 0 | 0.00 | duplicate_state 51 |
| chinese-emotion-dialogue | 200 | 200 | 200 | 1.00 | — |
| chinese-logic-sentiment | 200 | 200 | 200 | 1.00 | — |
| baidu-review-sentiment | 200 | 199 | 199 | 1.00 | duplicate_state 1 |
| toxic-zh | 200 | 200 | 200 | 1.00 | — |
| elder-scam-zh | 200 | 86 | 82 | 0.95 | not_chinese_row 29、duplicate_state 85 |
| med-guard-unsafe | 200 | 200 | 200 | 1.00 | — |
| med-guard-controversial | 120 | 120 | 120 | 1.00 | — |
| med-guard-benign-r1r5 | 200 | 200 | 200 | 1.00 | — |
| med-guard-benign-r6r11 | 200 | 200 | 200 | 1.00 | — |
| mh-risk-triage-zh | 200 | 200 | 150 | 0.75 | — |
| **合计** | **2,320** | **2,154** | **1,951** | **0.906** | duplicate_state 137、not_chinese_row 29 |

- **`taxonomy.item_errors()`：2,154 条全部通过，0 个错误**（`item_errors: 0`）。
- 域分布：risk_harm 1,206 / human_judgment 799 / social_moral 149。
- `lang` 全部为 `zh`；id 形状 `db-<slug>-<8hex>`，与英文条目同规则，可直接并入同一份 items.jsonl。
- `duplicate_state` 是契约既有行为（同一 state 只留一条）：zhihu 是同一问题下不同回答对（保留第一条，两条回答都在 meta），
  elder 是同一场景的多语言/多变体行（已核对**无标签冲突**）。
- 真实抽样核对：CValues 的 `refusal_appropriate=yes`、med-guard 的 allow/review/block、mh-triage 的 escalation 都已逐条看过。

## 7. 放量预估与 30% 目标核算

按 pilot 的实测产出率（条目/抓取行）外推到 row_limit：

| slug | row_limit | pilot 产出率 | 预估条目 |
|---|---:|---:|---:|
| cvalues-rlhf | 18,000 | 1.00 | 18,000 |
| zhihu-preference | 3,460 | 0.745 | 2,578 |
| chinese-emotion-dialogue | 4,159 | 1.00 | 4,159 |
| chinese-logic-sentiment | 2,176 | 1.00 | 2,176 |
| baidu-review-sentiment | 9,146 | 0.995 | 9,100 |
| toxic-zh | 5,000 | 1.00 | 5,000 |
| elder-scam-zh | 1,029 | 0.43 | 443 |
| med-guard（4 配置） | 1,040 | 1.00 | 1,040 |
| mh-risk-triage-zh | 1,598 | 1.00 | 1,598 |
| **合计** | **45,608** | — | **≈44,094** |

- 现有英文 37,124 条不变时，中文要占 **≥30%** 需要 **≈15,911** 条 → 本清单的 ≈4.4 万条**远超**该门槛；
  如果按 30% 精确配比训练，只需从池中抽 ≈15,911 条中文（建议按域分层抽，保证三个域都有）。
- 若要把中文占比做到 50%，需要 ≈37,124 条中文，仍然够（≈4.4 万）。
- **单一来源占比**：cvalues-rlhf 18,000 / 45,608 = 39.5% ≤ 40%；实际入库后需按真实条数复核一遍。

## 8. 风险与未测项

- **未放量**：本轮只跑了每源 200 行（合计 2,320 行）的试点；全量抓取（≈45,608 行、约 460 次分页请求）未执行，
  等 Lead 批准后再跑。放大后的真实产出率可能与 pilot 不同（尤其 zhihu 与 elder 的去重损耗）。
- **来源说明不完整**：`textdetox` 的中文子集没有单列原始来源；`left0ver` 的 label 极性来自 30 条抽样而非卡面。
  两者都按 B 级证据准入，并在数据卡标注，不做外推。
- **二次上传的授权链**：`Skepsun/cvalues_rlhf` 依赖上游 X-PLUG/CValues 的 Apache-2.0（本轮已实测该 LICENSE），
  但 ModelScope 上 `iic/CValues-Comparison` 的条目条款未逐字核对。
- **合成/教师成分**：med-guard（subagent 合成）、logic-sentiment（豆包生成 + 人工清洗）、
  TC260（已剔除）等含模型生成内容；池内已用 `meta.quality_flags` 标注，但**没有**做人工逐例审阅。
- **语义近重复未工具化**：现有去重是 state 哈希（精确），同情节改写/翻译的近重复没有检测工具
  （与英文侧同一状态，见 README 第 6 节第 5 条）。
- **中文覆盖的偏科**：本批中文来源集中在「情绪/毒性/风险拒绝」三类，
  `decision_mechanics`（工具选择、计划、权限）与 `knowledge_reasoning`（常识与知识判断）
  仍**没有**合格的中文原生来源——这是真实缺口，不拿机翻或通用指令语料填。

## 9. 复现命令

```powershell
# 来源清单校验 + 全离线测试（decision-base 共 347 项，含本任务新增的 21 项）
uv run --no-project --offline python -m unittest discover -s datasets/decision-base -p "test_*.py" -q

# 小样本打通：抓取 + 转换（200 行/来源，写仓库外）
uv run --no-project --offline python datasets/decision-base/convert_zh.py run --all --limit 200 \
    --out D:\pol2-raw\zh-items\items.zh.jsonl

# 只跑某几个来源 / 断点续跑 / 只保留 direct 映射
uv run --no-project --offline python datasets/decision-base/convert_zh.py fetch --source cvalues-rlhf --limit 200
uv run --no-project --offline python datasets/decision-base/convert_zh.py convert --all --mappings direct \
    --created-at 2026-10-02T00:00:00+08:00 --out D:\pol2-raw\zh-items\items.zh.jsonl
```

## 10. 证据附录（命令与输出摘要）

| 证据 | 命令 | 输出摘要 |
|---|---|---|
| 检索覆盖 | 95 次 `/api/datasets?search=...&filter=language:zh` | 去重 1,906 个 dataset id |
| 固定 revision 与许可 | `/api/datasets/{id}` × 49 | 每条来源拿到 40 位 sha 与 cardData.license |
| 行数与字段 | datasets-server `/splits` `/first-rows` `/rows` | 例：CValues train 77,693；zhihu 3,460；emotion 4,159；toxic-zh 5,000；med-guard 320+120+300+300；mh-triage 1,598 |
| CValues 授权链 | `Invoke-WebRequest https://raw.githubusercontent.com/X-PLUG/CValues/main/LICENSE` | Apache License 2.0，Copyright 2023 Alibaba X-PLUG Team（11,407 字节） |
| 机翻证据（Nemotron） | `zh/train.jsonl` 头 2.5KB | 中文 prompt + `language: zh-CN`，卡面写明从英文 Aegis 2.0 文化适配/翻译 |
| 机翻证据（PolyGuardMix） | `/first-rows` | `metadata={language, source}`，如 `wildguardmix_translated_tower` |
| 评测集证据（TC260） | 卡面 + `DATA_STATEMENT.md` + `schema.json` | 「合成安全测试提示」、public/validation/test、`review_status=pending`、`synthetic: const true` |
| 评测集证据（THU） | Range 读两个 JSON 头部 | `typical_safety_scenarios.json`/`instruction_attack_scenarios.json`，字段 prompt/response/type |
| 试点结果 | `convert_zh.py run --all --limit 200` | 2,154 条，item_errors=0，native_target_rate=0.906，域分布 risk_harm 1,206 / human_judgment 799 / social_moral 149 |
| 本目录测试 | `python -m unittest discover -s datasets/decision-base -p "test_*.py" -q` | decision-base 共 347 项全绿；其中 test_convert_zh.py 21 项（来源清单校验、9 个转换器、去重、direct/document 映射开关、CLI 拒绝未授权来源） |

## 11. 交接建议

1. Lead 复核后，把 `sources.zh.json` 的 12 个来源并入英文侧流程；放量时先跑
   `fetch --all`（≈460 次分页请求）再 `convert --all`，产物仍写仓库外，合并进 items.jsonl 的时机由 Lead 定。
2. 放量后回填**实际**产出率与域分布到本文件第 7 节，并按真实条数复核单一来源 40% 上限。
3. 若要把中文占比提到 30% 以上，建议按域分层抽样，优先保证 `decision_mechanics` 与
   `knowledge_reasoning` 的缺口有其它来源补位（这两个域目前没有中文来源，宁缺毋滥）。
