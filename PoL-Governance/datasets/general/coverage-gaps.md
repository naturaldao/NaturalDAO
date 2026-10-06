# general 覆盖缺口分析：六域 × 四分区，以及对 social_moral / human_judgment 的补源建议

- 日期：2026-10-06（UTC+8）｜执行：db-coverage（DSH Agent Team）｜共享任务：task-2
- 上游依据：[taxonomy.py](taxonomy.py)（6 个覆盖域，第 48 行）、[coverage.py](coverage.py)（硬阈值）、
  [README.md](README.md) §1.5/§3（成色分层与四分区）、[CONTRACT.md](CONTRACT.md)、[sources.json](sources.json)（配额与已排除来源）
- 边界：**本报告只做测算与调研**，不动数据、不动划分、不改 sources.json；所有条数均可用仓内工具复算。

## 0. 结论摘要

| 问题 | 结论 |
|---|---|
| 全语料 6 域现状 | decision_mechanics 19,465 / knowledge_reasoning 4,390 / risk_harm 2,605 / human_judgment 543 / **social_moral 0** / **pol2_axis 0** |
| 达标情况 | 3 域达标；**human_judgment 缺 657**、**social_moral 缺 1,200**；pol2_axis 缺 400（协作方另做，见 §4.3） |
| 结构性问题 | risk_harm 与 human_judgment **只存在于 train**（全部来自中文 B 层补充集）；test / validation / benchmark 只有 2 个域，train 与评测区的域分布**不可比** |
| 次生问题 | benchmark 的单一来源 SargeDev 占 **47.1%**，超过 40% 上限 |
| 补源结论 | social_moral 有 **1 个原生四元组来源**（Social IQa）+ 1 个"封闭标签集 + 3 人 vote"主力（ProsocialDialog）；human_judgment **没找到许可干净的原生四元组来源**，只能以 B 层补 train（最优三个：go_emotions / measuring-hate-speech / civil_comments） |
| 若只补 2–3 个 | 见 §7：优先 ProsocialDialog + Social IQa，第三个按"要不要补毒性严重度与对象"决定选 measuring-hate-speech |

## 1. 复算口径

**冻结语料**：`D:\pol2-raw\general-private\data\items.final.jsonl.gz`（仓外，23,855 条），
解压后 sha256 = `21f11fe3dc39edd9d82680b7461b45883bb73d15a1d9611f3b2e80f4bd7e9f9f`，
与本仓 [data/items.final.jsonl](data/items.final.jsonl) **逐字节相同**（同 sha256，同为 82,605,456 B）。
四分区来自 [data/splits/](data/splits/split-manifest.json)（train 17,984 / test 4,946 / validation 2,473 / benchmark 1,600）。

```powershell
# 0) 校验冻结语料与仓内明文一致
python -c "import gzip,hashlib; print(hashlib.sha256(gzip.open(r'D:\pol2-raw\general-private\data\items.final.jsonl.gz','rb').read()).hexdigest())"

# 1) 全语料（23,855 + 中文补充 3,148 = 27,003）：拼到仓外临时文件，再用官方工具跑
python -c "import gzip; o=open(r'D:\tmp\all.jsonl','wb'); o.write(gzip.open(r'D:\pol2-raw\general-private\data\items.final.jsonl.gz','rb').read()); o.write(open(r'datasets/general/data/zh-supplement/items.jsonl','rb').read()); o.close()"
uv run --no-project --offline python datasets/general/coverage.py --items D:\tmp\all.jsonl --no-sources --json-out D:\tmp\all.readme.json
#    --no-sources 用 README 默认配额：总量 ≥10,000、每域 ≥1,200、pol2_axis ≥400、单一来源 ≤40%

# 2) 各分区分别跑（分区下限不是硬要求，仅作诊断，见 §3）
foreach ($p in 'train','validation','test','benchmark') {
  uv run --no-project --offline python datasets/general/coverage.py --items "datasets/general/data/splits/$p.jsonl" --json-out "D:\tmp\$p.json"
}

# 3) 只跑冻结语料（不含中文补充集）作对照
uv run --no-project --offline python datasets/general/coverage.py --items datasets/general/data/items.final.jsonl --json-out D:\tmp\base.json
```

复算结果摘要：全语料 27,003 条，`ok=false`，`gaps.domains = {human_judgment: 657, social_moral: 1200, pol2_axis: 400}`，
`gaps.total_shortfall=0`、`gaps.sources_over_share={}`、`schema_issues=0`。
**每个分区的数字与 §2、§3 表格逐格一致**；口径为条目级 `domain` 字段（一条条目只算一个域）。

## 2. 覆盖现状表（六域 × 四分区 × 全语料）

| 覆盖域（taxonomy.py:48） | 全语料 27,003 | train 17,984 | test 4,946 | validation 2,473 | benchmark 1,600 |
|---|---:|---:|---:|---:|---:|
| decision_mechanics | 19,465 | 12,203 | 4,068 | 2,034 | 1,160 |
| human_judgment | 543 | 543 | **0** | **0** | **0** |
| social_moral | **0** | **0** | **0** | **0** | **0** |
| risk_harm | 2,605 | 2,605 | **0** | **0** | **0** |
| knowledge_reasoning | 4,390 | 2,633 | 878 | 439 | 440 |
| pol2_axis | **0** | **0** | **0** | **0** | **0** |
| **合计** | **27,003** | **17,984** | **4,946** | **2,473** | **1,600** |

语言（同一批文件）：全语料 en 15,983 / zh 11,020；train en 9,588 / zh 8,396；test en 3,197 / zh 1,749；
validation en 1,598 / zh 875；benchmark **全 en**（1600）。

冻结语料（不含中文补充集）对照：23,855 条里只有 decision_mechanics 19,465 + knowledge_reasoning 4,390 两域。

## 3. 缺口表

下限口径：总量 ≥10,000、每域 ≥1,200（[coverage.py](coverage.py) 常量），pol2_axis 例外 ≥400。

| 覆盖域 | 下限 | 全语料实测 | 缺口 | 缺口来源 |
|---|---:|---:|---:|---|
| decision_mechanics | 1,200 | 19,465 | **0** | — |
| human_judgment | 1,200 | 543 | **657** | 全部来自中文 B 层补充集（textdetox 543 条） |
| social_moral | 1,200 | 0 | **1,200** | 无任何来源 |
| risk_harm | 1,200 | 2,605 | **0** | 达标，但只在 train |
| knowledge_reasoning | 1,200 | 4,390 | **0** | — |
| pol2_axis | 400 | 0 | **400** | 通用底座不背此配额，见 §4.3 |
| **合计** | — | 27,003 | **1,857**（不含 pol2_axis）/ 2,257（含） | — |

**各分区单独跑 coverage.py 会报的项**（诊断用，不是硬要求——配额定义在全语料上）：

| 分区 | 报错项 |
|---|---|
| train | human_judgment 缺 657、social_moral 缺 1,200 |
| test | 总量 4,946 < 10,000；human_judgment / social_moral / risk_harm 各缺 1,200；knowledge_reasoning 缺 322 |
| validation | 总量 2,473 < 10,000；human_judgment / social_moral / risk_harm 各缺 1,200；knowledge_reasoning 缺 761 |
| benchmark | 总量 1,600 < 10,000；decision_mechanics 缺 40、knowledge_reasoning 缺 760、human_judgment / social_moral / risk_harm 各缺 1,200；**单一来源 47.1% > 40%** |

## 4. 四个结构性发现（比缺口数字更重要）

### 4.1 train 与评测区的域分布不可比（已知，此处给出可复算证据）

risk_harm 2,605 与 human_judgment 543 **100% 落在 train**，来源是中文补充集
（[zh-supplement-report.md](zh-supplement-report.md)：BEncoderRT 2,061 / textdetox 543 / chenhaodev 472 / vanila434 72，
全部 `meta.benchmark_eligible=false`、只进 train）。
所以 test / validation / benchmark 里 **只有 decision_mechanics 与 knowledge_reasoning 两域**。
任何"某域在训练里如何、在测试里如何"的对比都会被这个结构差异污染；
**补源时不能只看全语料下限**——要让评测区也含这些域，补进来的条目必须能进评测区（即 A 层原生四元组，见 §5.1）。

### 4.2 benchmark 的单一来源已超限

benchmark 1,600 条里 SargeDev/jev-distill-corpus-v3 占 **47.1%**（753 条；上限 40% 即 640 条）。
公开三区未超限（train 26.0% / test 31.1% / validation 31.8%；全语料最高 Deepexi 29.15%）。
评测分区通常不套训练期配额，但这条数字值得 Lead 知晓。

### 4.3 pol2_axis 的两套口径

[sources.json](sources.json) 的 `quotas.domain_min.pol2_axis = 0`（2026-09-30 Lead 裁决：通用底座不背 PoL2 专项配额），
而 README 默认是 **400**。同一份语料因此有两种结论：
`--no-sources` 报 3 项不通过（含 pol2_axis 缺 400），默认读 sources.json 只报 2 项。
任务书用的是 400 口径，本报告两处都写明。

### 4.4 单一来源还有余量

全语料最大来源 Deepexi/openai-formate-function-calling-small = 7,872 条 = **29.15%**。
新增 N 条后上限变为 `0.40 × (27,003 + N)`：例如 N=6,000 → 上限 13,201，Deepexi 占比降到 23.9%。
**补源不会撞 40% 上限**；但 §5 的候选来源全部是英文，会稀释中文占比（11,020 / 33,003 = 33.4%，仍在 33% 目标附近）。

## 5. 候选来源

证据等级：**A** = 读过卡面 + 实际行数据/实际下载；**B** = 读过卡面 + datasets-server 的 splits/size/first-rows/statistics 快照；
**C** = 只有 HF API 元数据。本轮 HF API 对**不存在的 repo 返回 401**（实测 `definitely/not-a-real-dataset-xyz` 也是 401），
所以"401"不等于受限；凡 401 的 id 都用 search API 找规范 id 后复核（例：`facebook/prosocial-dialog` → `allenai/prosocial-dialog`）。

### 5.1 先说一件影响选型的事：A 层 / B 层

按 [README.md](README.md) §1.5：**只有 A 层（来源原生四元组）能进 validation / test / benchmark**，B 层（我们出题、来源标签当答案）只进 train。

- social_moral：**有 A 层来源**（Social IQa，原生 context/question/answerA-C/label）→ 可以让评测区也长出一个域。
- human_judgment：**本轮没找到许可干净、且原生 (question, options, target) 的来源**。
  NLI 类（SNLI / MultiNLI）有封闭 3 值标签但无原生题面，且许可为 SA / 混杂；情绪类（go_emotions 等）只有标签没有候选与题面。
  → 结论：human_judgment 只能以 B 层补 train，**评测区的该域缺失应作为已知限制记录**（或后续由 Lead 裁决是否放宽）。
  这是本次调研最重要的负结果。

### 5.2 social_moral 候选（按推荐度排序）

| # | 来源（HF，固定 revision） | 许可 | 行数 | 原生四元组 | 可映射到 | 证据 |
|---|---|---|---|---:|---|---|
| S1 | [allenai/prosocial-dialog](https://huggingface.co/datasets/allenai/prosocial-dialog/tree/d77d7ad3c624c51030f2f32c83e892b3d620b3d4) | cc-by-4.0（卡面） | 165,681 | ✗（有原生封闭标签集 + 3 人原始标注） | `norm_violation`、`prosocial_response_warranted`、`toxicity_present`、`response_style`；vote 分布给 `probs` | A |
| S2 | [allenai/social_i_qa](https://huggingface.co/datasets/allenai/social_i_qa/tree/8835ceb9141d7896d9d968634a9b21ae440e3ec5) | CC-BY-4.0（卡面 Licensing Information） | train 33,410 + dev 1,954 | **✓ 原生** context/question/answerA-C/label | 动机→行为→后果类问题（键名用来源原生 question）；按题面可分流到 social_moral / decision_mechanics | A |
| S3 | [tasksource/scruples](https://huggingface.co/datasets/tasksource/scruples/tree/121b03f7820133d4ec4b42b776158968b787e3fd) | apache-2.0（卡面；上游 [allenai/scruples](https://github.com/allenai/scruples) GitHub license=Apache-2.0） | 32,766 | ✗（二值标签 + pro/contra 票分） | `norm_violation` / `moral_judgment`，`label_scores` 归一出真分布 | A |
| S4 | [hendrycks/ethics](https://huggingface.co/datasets/hendrycks/ethics/tree/b8b47c589f8bee77175b8648e5497278b68da48a) | mit（卡面；上游 [LICENSE](https://raw.githubusercontent.com/hendrycks/ethics/master/LICENSE) 实测 MIT） | commonsense train 13,910（+val 3,885 / test 3,964）等 5 个子集，合计 134,417 | ✗（单句 + 二值标签） | `moral_judgment` / `norm_violation` | B |
| S5 | [demelin/moral_stories](https://huggingface.co/datasets/demelin/moral_stories/tree/b830cf56eb00bc4edd1860dd544a192216eb3587) | mit（卡面 Licensing Information；上游 [demelin/moral_stories](https://github.com/demelin/moral_stories) GitHub license=MIT） | 30 个派生配置 × 24,000 = 720,000 | ✗（norm + 两结局 + 0/1 标签） | `norm_violation`、`intent_motive`、`expected_consequence` | B |
| S6 | [ninoscherrer/moralchoice](https://huggingface.co/datasets/ninoscherrer/moralchoice/tree/89c0fe7b158b5ade5d10e0644c1aa20ab4c78cbe) | cc-by-4.0（卡面） | 1,367 场景（680 high + 687 low ambiguity，实测下载计数） | ✗（A/B 成对比较 + 每动作规则违反标签） | `moral_judgment`（选 A 或 B）+ 各规则违规 | A |
| S7 | [tasksource/social-chemestry-101](https://huggingface.co/datasets/tasksource/social-chemestry-101/tree/a329cc50d3ae66b7f221415df3b1c4cb26f71c61) | **未查到**（镜像无卡面 404；另一镜像 [wassname/social_chemistry_101](https://huggingface.co/datasets/wassname/social_chemistry_101/tree/a7869978d5d441d89327067d8ff543d6dcc3fc32) 声明 cc-by-sa-4.0 = SA） | 355,922 | ✗（RoT 级标注） | `moral_foundation`（`rot-moral-foundations` 给出 care/harm、loyalty/betrayal 一类道德基础标签，**目前唯一原生匹配该键的来源**）、`moral_judgment`（rot-judgment 封闭值） | B |

**已知限制（逐条）**

- **S1 ProsocialDialog**：①首句由 GPT-3 生成、种子来自 SBIC / Social Chemistry / ETHICS（卡面 `language_creators: crowdsourced, machine-generated`），
  属合成+众包混合；②一条对话多行（`dialogue_id`/`response_id`），**必须按 dialogue_id 整组切**，否则同一情境跨区泄漏；
  ③`safety_label` 是 5 值（`__casual__` / `__possibly_needs_caution__` / `__probably_needs_caution__` / `__needs_caution__` / `__needs_intervention__`），
  而 3 名工人的原始标注 `safety_annotations` 只有 3 值（casual / needs caution / needs intervention）→ **vote 分布只能建在 3 值上**，
  5 值 verdict 需 documented 映射；④用到的 response 是生成文本，本任务不拿它当 target；⑤英文。
- **S2 Social IQa**：①**硬标签**、每题仅 1 个正确项，没有多人分布；②test 划分不公开，可用的只有 train 33,410 + dev 1,954；
  ③HF 仓库里只有加载脚本，数据要从 `https://storage.googleapis.com/ai2-mosaic/public/socialiqa/socialiqa-train-dev.zip`
  取（本轮实测 2,198,056 B 可下，train.jsonl/dev.jsonl 条数已核对）；④内容是**社会常识推理**而非道德判断，
  问题类型混杂（"如何感受 / 需要先做什么 / 接下来做什么"），部分更贴 decision_mechanics；⑤情境只有一句话。
- **S3 Scruples**：①只有 anecdotes 32,766 条；②`label` 与 `binarized_label` 的 0/1 语义**本轮未查到逐字段说明**
  （上游 readme 只说明是"社区 vs 众包对 32,000 条轶事的伦理判断"）→ 采用前必须核对；③票来自 r/AmITheAsshole 社区，
  不是受控标注；④同一 `post_id` 可能多行，需去重/整组切；⑤英文长文本。
- **S4 ETHICS**：①**label 语义卡面未写明**（"Dataset Summary"只有一句），本轮未查到权威表述 → 采用前需查 ICLR 2021 论文/上游代码；
  ②commonsense 子集是**单句、无情境**；③`utilitarianism` 配置**没有 label**（只有 baseline / less_pleasant 两段文本），不可用作监督；
  ④它是知名评测基准，只能取 train 划分，test 绝不取，且需在训练报告中披露。
- **S5 Moral Stories**：①卡面 `annotations_creators: no-annotation`——moral/immoral 动作是写作者**构造**的，不是"判断"标注；
  ②24,000 × 30 是作者派生的对照实例（lexical_bias / minimal_pairs / norm_distance 等变体），**同一故事会出现多份**，
  只能选一种配置；③label 含义随任务变（action 类 0=divergent、1=normative；consequence 类不同），卡面有写明；
  ④本轮未核到基础故事语料的原始条数（只核到 30 个配置各 24,000 行）。
- **S6 MoralChoice**：①规模小（1,367 场景），单独补不满 1,200 缺口；②作者自述局限：场景与模板多样性有限、仅英文；
  ③是成对比较而非四元组；④规则违反标签由 SurgeAI 采集，语义需按论文核对。
- **S7 Social Chemistry 101**：①**许可未证实**是硬伤——上游 GitHub 仓库已 404，唯一有卡面的镜像声明 cc-by-sa-4.0（SA，与 [SOURCES.md](SOURCES.md) §4"没有 NC 或 SA 条目"冲突）；
  ②行是 RoT 级（355,922 条 RoT 覆盖约 10.4 万个 situation），不是情境级；③`rot-judgment` 等字段的取值需要先做取值普查。**不建议在许可澄清前采用。**

### 5.3 human_judgment 候选（按推荐度排序）

| # | 来源（HF，固定 revision） | 许可 | 行数 | 原生四元组 | 可映射到 | 证据 |
|---|---|---|---|---:|---|---|
| H1 | [google-research-datasets/go_emotions](https://huggingface.co/datasets/google-research-datasets/go_emotions/tree/add492243ff905527e67aeb8b80c082af02207c3) | apache-2.0（卡面 + 上游 google-research LICENSE） | raw 211,225 行（rater 级）/ simplified 54,263 评论 | ✗（28 类封闭标签；raw 每行=1 名 rater 的 one-hot） | `emotion_primary`（28 类）+ 每情绪一个 noul；票比例即真 `probs` | A |
| H2 | [ucberkeley-dlab/measuring-hate-speech](https://huggingface.co/datasets/ucberkeley-dlab/measuring-hate-speech/tree/5468f6e118396646b02a2f691e771f6b6d9502ea) | cc-by-4.0（卡面） | 135,556 行 = 39,565 评论 × 7,912 标注者（卡面） | ✗（标注者×评论 行级 + 封闭标签） | `toxicity_present`（票比例）、`toxicity_severity`（`hatespeech` 实测 0–2 三档）、`toxicity_target`（`target_*` 组） | B |
| H3 | [google/civil_comments](https://huggingface.co/datasets/google/civil_comments/tree/f2970eb3a55777454c94069077cc8d9b5866312d) | **cc0-1.0**（卡面 Licensing Information） | 1,999,514（1,804,874/97,320/97,320） | ✗（文本 + 7 个比例） | `toxicity_present` noul，`probs={yes: toxicity, no: 1-toxicity}`；另 6 个维度可做同类键 | A |
| H4 | [allenai/real-toxicity-prompts](https://huggingface.co/datasets/allenai/real-toxicity-prompts/tree/f21629712ffd6a3d13a54fd2807ccd521c55ef74) | apache-2.0（卡面） | 99,442 | ✗ | `toxicity_present`（弱） | B |
| H5 | [google/jigsaw_toxicity_pred](https://huggingface.co/datasets/google/jigsaw_toxicity_pred/tree/9fca5f507ac11049ff34bb13c8546b01afcedbbd) | cc0-1.0（卡面） | **未查到**（viewer 501） | 未查到 | 未查到 | C |

**已知限制（逐条）**

- **H1 go_emotions**：①**多标签**（一条评价可同时给多个情绪）→ 直接做单选 `emotion_primary` 需要先定义聚合规则（属确定性再加工，不是人工重标）；
  更"原生化"的用法是**每情绪一个 noul**（键名即来源标签名），target 用该评论上 rater 的 positive 比例——这是**真分布**；
  ②Reddit 单句、无上下文；③含 `author` 用户名（隐私字段，建议丢弃）；④卡面写明由 **3 名印度英语众包工人**标注（文化偏差）；
  ⑤raw 与 simplified 二选一，避免同评论重复计数。
- **H2 measuring-hate-speech**：①**行级不是条目级**（每行=1 名标注者×1 条评论），要按 `comment_id` 聚合，且每条评论的标注者数不等；
  ②`hatespeech` 实测只有 **0 / 1 / 2 三档**（datasets-server statistics：min 0、max 2，直方图 80,624 / 8,911 / 46,021），
  不是部分资料写的 0–4 —— 做 score 键时按 3 档；③另有连续 `hate_speech_score`（−8.34..6.3）可做软标签；
  ④标注者取自美国众包、平台有限，卡面带大量 `annotator_*` 人口学字段（**只取文本+标签，别把人口学带进语料**）；
  ⑤仇恨言论 ≠ 一般毒性。
- **H3 civil_comments**：①HF 版**只有聚合比例，没有人头分布与人数**——比例分母不同（实测 0.1667=1/6、0.4576=27/59、0.3611=13/36），
  跨条目只是近似可比；②没有严重度序数（`severe_toxicity` / `identity_attack` / `threat` / `insult` / `obscene` / `sexual_explicit` 同样是比例）；
  ③2017 年新闻站评论，含 PII 风险；④英文；⑤优点：**CC0**，体量 200 万，是唯一零授权的来源。
- **H4 real-toxicity-prompts**：7 个分值是连续小数（如 0.40394926），形态上是**分类器打分而非人工票**，与本域"多人 vote 分布"的定位不符；
  且文本是随机窗口（`begin`/`end` 截断），不是自洽情境。**不建议作为 human_judgment 主来源。**
- **H5 jigsaw_toxicity_pred**：卡面 cc0-1.0，但 datasets-server `/splits` 与 `/size` 均返回 501（需跑 arbitrary Python 的加载脚本），
  **行数与字段本轮未查到**；与 H3 同源系（Jigsaw），若 H3 可用则 H5 边际价值有限。

### 5.4 已排查但不推荐（含理由与链接）

| 来源 | 许可 | 不推荐的理由 |
|---|---|---|
| [stanfordnlp/snli](https://huggingface.co/datasets/stanfordnlp/snli/tree/cdb5c3d5eed6ead6e5a341c8e56e669bb666725b) | cc-by-sa-4.0 | **SA**，与"不含 NC/SA"政策冲突；HF 版只有多数标签，拿不到 5 人分布 |
| [nyu-mll/multi_nli](https://huggingface.co/datasets/nyu-mll/multi_nli/tree/da70db2af9d09693783c3320c4249840212ee221) | cc-by-3.0 / cc-by-sa-3.0 / mit / other 四者并列 | 授权链不明确；HF 版无标注者分布 |
| [facebook/anli](https://huggingface.co/datasets/facebook/anli/tree/8e4813d81f46d313dac7892e1c28076917cfcdf9) | cc-by-nc-4.0 | **NC** |
| [dair-ai/emotion](https://huggingface.co/datasets/dair-ai/emotion/tree/cab853a1dbdf4c42c2b3ef2173804746df8825fe) | other（卡面：**仅限教育与研究用途**） | 使用范围受限 |
| [cardiffnlp/tweet_eval](https://huggingface.co/datasets/cardiffnlp/tweet_eval/tree/b3a375baf0f409c77e6bc7aa35102b7b3534f8be) | unknown | 许可不明，直接排除 |
| [fancyzhx/amazon_polarity](https://huggingface.co/datasets/fancyzhx/amazon_polarity/tree/9d9c45c18f8c3cf1b23a3c27917b60cbf28f3289) | apache-2.0（上传者声明） | 二次上传、上游许可链未核实；且与现有情感来源重叠（行数本轮未核） |
| [wassname/social_chemistry_101](https://huggingface.co/datasets/wassname/social_chemistry_101/tree/a7869978d5d441d89327067d8ff543d6dcc3fc32) | cc-by-sa-4.0（声明） | **SA** + 上游已 404，授权链不成立（对应 S7） |

> 注：`allenai/social-chem-101`、`allenai/scruples`、`facebook/prosocial-dialog`、`google/go_emotions` 这些 id 在 HF 上**不存在**
> （API 返回 401 "Invalid username or password"）。规范 id 分别是 `tasksource/social-chemestry-101`、`tasksource/scruples`、
> `allenai/prosocial-dialog`、`google-research-datasets/go_emotions`。[sources.json](sources.json) `excluded` 里
> 把 `allenai/social_chem_101` 与 `google/goemotions` 记为"401 不可达"，按本轮复核，那是**旧 id 不存在**，不是受限。

## 6. 候选来源的合并成本速览

| 来源 | 抽取单位 | 需要做的再加工 | 预估可入库量 |
|---|---|---:|---:|
| ProsocialDialog | 一行 = 一问一答 | 按 dialogue_id 聚合、3 值 vote → probs、B 层命题 | 3,000–5,000（自 16.5 万行分层抽） |
| Social IQa | 一行 = 一个原生四元组 | **几乎为零**（直接搬运 state/question/options/label） | 最多 35,364 |
| Scruples | 一行 = 一条轶事 | 二值标签语义核对、post_id 去重、label_scores 归一 | 2,000–3,000 |
| ETHICS commonsense | 一行 = 一句 | label 语义核对、B 层命题 | 2,000–3,000（train 13,910 中取） |
| Moral Stories | 一行 = 一个对照实例 | 选一种派生配置、去重同故事 | 3,000–5,000 |
| go_emotions raw | 一行 = 一名 rater 的一次评价 | 按评论聚合票比例（确定性） | 3,000–5,000 评论 |
| measuring-hate-speech | 一行 = 一名标注者×一条评论 | 按 comment_id 聚合、0–2 → score 键 | 2,000–4,000 评论 |
| civil_comments | 一行 = 一条评论 | 无（比例直接当 probs） | 不限（建议 ≤5,000，避免英语毒性单一化） |

## 7. 优先级建议（若只能补 2–3 个来源）

**第 1 顺位：ProsocialDialog（S1）** — 唯一同时满足"封闭标签集 + 多人原始标注"的 social_moral 来源，许可干净（cc-by-4.0）。
一条来源可同时补两个缺口：social_moral 深度（norm_violation / prosocial_response_warranted / response_style）
与 human_judgment 的 vote 分布形态。缺点是 B 层、只进 train，且首句有 GPT-3 合成成分。
**第 2 顺位：Social IQa（S2）** — 六域里 social_moral 的**唯一原生四元组**来源，CC-BY-4.0，几乎零加工，
而且是本次唯一能让 **social_moral 也出现在评测区**的来源（A 层）。缺点是硬标签、test 不公开、内容偏社会常识。
**第 3 顺位（二选一）**：
- 若目标是补 human_judgment 的**缺键**（`toxicity_severity` 与 `toxicity_target` 目前完全没有任何来源）→ 选 **measuring-hate-speech（H2）**：
  cc-by-4.0、7,912 名标注者、0–2 序数 + 目标群体标签 + 真票分布。
- 若目标是补**情绪轴的分布形态** → 选 **go_emotions（H1）**：apache-2.0、raw 的 rater 级 one-hot 直接给真分布，28 类封闭集。
**第 4 顺位（可选）**：**civil_comments（H3）**，CC0 零授权、200 万行，是最便宜的兜底；代价是只有毒性比例、没有严重度与目标对象。

**不建议**把 Social Chemistry 101（许可未证实 + 镜像 SA）、SNLI/MultiNLI（SA/许可混杂 + 无分布）、
dair-ai/emotion（研究用途限制）、tweet_eval（许可不明）放进本轮补源。

**量级核算**：按上限取 ~6,000 条新条目（ProsocialDialog 3,000 + Social IQa 2,000 + MHS 1,000），
全语料 27,003 → 33,003；social_moral ≥1,200 ✓；human_judgment 543 + 补量 ≥1,200 ✓；
单一来源上限升到 13,201，现有最大来源 Deepexi 7,872（23.9%）安全；
但**评测区仍只有 social_moral 能靠 Social IQa 补上（且需把它切成四区），human_judgment 保持 train-only**（§5.1）。

## 8. 未查到 / 需上游确认（不要当已核实）

1. **ETHICS 各子集 label 的语义**（0/1 各代表什么）：卡面未写，本轮未查到权威表述 → 采用前查 ICLR 2021 论文或上游代码。
2. **Scruples `label` / `binarized_label` 的 0/1 语义**：上游 readme 未给逐字段说明 → 采用前核对。
3. **`google/jigsaw_toxicity_pred` 的行数与字段**：datasets-server 返回 501（arbitrary Python）。
4. **Social Chemistry 101 的上游许可**：`allenai/social-chem-101` GitHub 仓库已 404；两个 HF 镜像一个无卡面、一个声明 cc-by-sa-4.0。
5. **许可干净、原生 (question, options, target) 且带多人分布的人类判断来源**：本轮**未查到**（§5.1 的负结果）。
6. **Moral Stories 基础故事语料的原始条数**：本轮只核到 30 个派生配置各 24,000 行。
7. **ProsocialDialog 的 `safety_label` 5 值与 3 值原始标注之间的官方映射规则**：卡面只说"final verdict according to safety_annotations"，
   未给逐条规则 → 若要用 5 值必须 documented 映射并保留原值。

## 9. 边界与验收

- 本报告只新增本文件，**未改任何数据、划分、脚本或 sources.json**，未做任何 git 写操作。
- 报告内所有语料条数均由 [coverage.py](coverage.py) 复算（§1 命令），与四分区文件逐格一致；
  外部来源数字来自 HF API / datasets-server 快照 / 卡面 / 实际下载，逐条标注证据等级（§5 的"证据"列）。
- 验收：`uv run --no-project --offline python tools/check.py` **已在本文件加入后重跑并通过**，输出 `{"status": "pass", "local_links": 322, "models_run": false}`（本文件新增 40 个仓内链接，全部可解析）。
