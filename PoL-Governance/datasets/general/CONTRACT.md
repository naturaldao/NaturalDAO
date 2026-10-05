# 数据集契约（general v0.1）

> 本文件原为 datasets/general/README.md 的正文，2026-10-05 拆分：**README.md 改为面向协作者的总览**
> （这是什么、从哪来、怎么切），字段与格式契约留在本文件。契约内容与拆分前逐条一致。

本目录制备**通用决策数据**：不追求"更大"，追求**覆盖全面、可直接改问、可被外部答案源批量作答**。
它服务三件事：给治理模型打通用决策基本功（防偏科）、给 Jev 交叉优化提供问题集、给后续训练提供可复算底料。

依据：[SPEC](../../SPEC.md)、[数据集契约](../pol2/README.md)、协作方调研 [data.md](../../research/Wenbo/data.md)、
来源审计 [replay](../pol2/replay/survey.md)。

## 1. 三条设计原则

1. **状态与问题分离。** `state` 是待判断的情境；`questions` 是在同一 state 上**相互正交**的类型化问题；`targets` 才放答案。
   同一句话要能同时问出"有没有伤害倾向""是不是边界主张""要不要介入"，而不是压成一个"爱分"。
2. **兼容 Jev 的三种原语。** `noul`（是/否）、`choice`（多选一）、`score`（分级）。不发明第四种。
3. **概率优先于硬标签。** 有分布就存分布（多人标注的 vote distribution 尤其宝贵），没有才存单标签。
   但**不允许**把单标签伪装成概率。

## 2. 记录格式（JSONL，UTF-8）

### 2.1 条目 `items.jsonl`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | `db-<source-slug>-<8hex>`，全局唯一，由 (source, revision, row) 确定性派生 |
| `domain` | string | 是 | 覆盖域，见第 3 节 |
| `lang` | string | 是 | `en` / `zh` / 其他，保留源语言，不做静默翻译 |
| `state` | string | 是 | 待判断的情境文本；不写结论、不写"这是违规"之类提示 |
| `questions` | object[] | 是 | 非空；每条 `{key, kind, prompt, options?, scale?, origin?, source_key?}` |
| `targets` | object | 否 | `{<key>: {answer?, probs?}}`；源数据自带答案时填，否则留空等外部答案源 |
| `source` | object | 是 | `{dataset, revision, config, split, row, license, url}`，全部必填，无法固定 revision 的一律不收 |
| `meta` | object | 是 | `{converter, converter_version, created_at, quality_flags}` |

`questions[].origin` 取值（**决定这道题是谁出的**，是本源最重要的区分）：

- `source`：题目来自数据集本身。此时 `key` 直接用来源的原生问题名（如 `category`、`bug_severity`），
  `source_key` 记录该原生名以便溯源，`state` 与 `options`／`scale`／`target` 全部用来源原文，**不做改写、翻译或档位压缩**。
  这是首选形态：我们的目标模型只做"选一个"，题目应当来自真实决策场景，而不是我们替数据出题。
- `taxonomy`：来源本身没有原生问题，由本地 taxonomy 生成题面。**这是次选**，只在来源确实不含问题时使用。
  此时 `key` 取自 taxonomy 的问题键表。

> **`origin=source` 的准确含义**：它表示**候选集与答案来自来源**，**不表示题面文字也来自来源**。
> 英文侧（6 个 System-1 来源）的 prompt 就是来源自己的问题原文，键名也是来源的原生问题名；
> **中文侧（Deepexi 7,872 条）来源没有 question 字段**：prompt 只有一种措辞（"以下候选中，哪一个是正确的下一步？"）、
> key 一律是 `next_step_candidate`，**题面措辞是我们编写的**，来源提供的是请求文本、候选菜单与正确答案。
> 想区分"题面是否原生"，看 `lang` 与 `source.slug`，或看 `meta.key_source`（`native-name` / `native-text`）。

`origin` **缺省即视为 `taxonomy`**：只有原生四元组的条目才写 `origin: "source"`。
早期按模板命题的语料因此不必回填该字段，也能被正确解读。`coverage.py` 按 `origin` 分别统计：
`source` 的原生键不在 taxonomy 词表内属正常，不应报 schema 警告。

**当前主产物是 data/items.native.jsonl.gz（已移出版本控制）**（15,983 条，全部 `origin=source`，100% 带原生真值；
明文同名去 `.gz`，体积大故不入库）。
`items.jsonl` 与 `items.bilingual.jsonl` 是按模板命题的早期版本，留作对照，不再是训练首选。

`questions[].kind` 取值：`noul`（是/否）、`choice`（多选一）、`score`（分级）。

**下面的形状约束只在 `origin=taxonomy` 时强制**；`origin=source` 一律以条目自带的 `options`／`scale` 为准——
原生数据是什么形状就用什么形状，**不得为了迁就我们的规范去改题**（砍选项就是改题目）。

| 约束 | `origin=taxonomy`（我们出题） | `origin=source`（数据自带） |
|---|---|---|
| `noul` 选项 | 固定 `[{"key":"yes"},{"key":"no"}]` | 恰好 2 个非空选项，`false/true`、`no/yes` 均可，顺序任意 |
| `choice` 选项数 | 2–16 | ≥2，**不设上限**（实测最多 57 个） |
| `score` 量程 | `{min:0,max:4,labels:…}` | 用自带 `scale` 自洽即可（实测 3 / 6 / 10 / **11 档**，最高 `max=10`） |
| 答案与概率 | 按 taxonomy 规范选项校验 | 按**该题自带**的 options/scale 校验 |

**score 的取值口径陷阱**：`scale.labels` 是**给人看的档位文字**，而 `targets[key].probs` 的键
**始终是数字下标** `"0".."max"`。实测 6,752 道 score 题里 **4,661 道**的 labels 是描述文字
（如 Open-Jev 的 `bug_severity` 三档："Cosmetic; no impact to functionality" …），只有 2,091 道是 `"0".."max"`。
照 `labels` 去建输出词表会**静默全 0 或 KeyError**；建词表要用 `range(min, max+1)`。

### 2.2 答案 `answers.<source>.jsonl`

一行一个"某答案源对某问题的回答"：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qid` | string | 是 | `<item id>.<question key>` |
| `id` | string | 是 | 所属条目 |
| `key` | string | 是 | 问题 key |
| `kind` | string | 是 | `noul` / `choice` / `score` |
| `source` | string | 是 | `jev-<version>` / `luna` / `grok-4.7` …，写进文件名 |
| `source_version` | string | 是 | 固定版本 |
| `answer` | string 或 number | 否 | 失败时为 null |
| `probs` | object | 否 | 归一到 1；没给概率就不要编 |
| `execution_status` | string | 是 | `ok` / `timeout` / `error` / `invalid` |
| `latency_ms` | number | 是 | 客户端全程耗时 |
| `created_at` | string | 是 | ISO 8601 带时区 |

**失败不写 ok。** 外部答案源（含官方 Jev）没接通时必须显式报错退出，不得静默降级成"跳过"。

## 2.3 真值形态与 provenance（训练前必读）

字段层面**长得一样**，但 `targets[key].probs` 有三种来源完全不同的形态，必须先用下表判别：

| 形态 | 判别方法 | 全语料问题数 | 其中 benchmark | 能不能当概率用 |
|---|---|---:|---:|---|
| **真分布** | probs 有多个不同取值 | 7,520 | 757 | ✅ 可以 |
| **伪 one-hot** | 恰好一个 1.0、其余 0.0 | 14,119 | 1,398 | ❌ 是硬标签的单点分布 |
| **均匀分布** | 各项相等（如 0.5/0.5） | 1,730 | 180 | ❌ 无信息 |
| 只有 answer | 没有 probs 字段 | 11,565 | 854 | — 只有硬标签 |

**规则**：`probs` 只在来源**真的给了分布**时使用；由硬标签转换出来的**单点分布**必须能被识别，
**不允许**把它当作校准目标（本契约第 1 节第 3 条）。判别方法（无歧义）：

    def target_shapes(targets):
        """返回每个问题的形态：real / one_hot / uniform / answer_only"""
        def classify(t):
            probs = t.get("probs")
            if not probs:
                return "answer_only"
            values = list(probs.values())
            if max(values) == min(values):
                return "uniform"
            return "one_hot" if sum(1 for v in values if v) == 1 else "real"
        return {key: classify(value) for key, value in (targets or {}).items()}

**已知冲突（待数据侧修复，不要靠这份文档猜测）**：历史产物里 14,119 个问题是**伪 one-hot**，
它们与第 1 节"不允许把单标签伪装成概率"直接冲突。建议的修法是**加问题级 provenance**：
`targets[key].provenance ∈ {source_distribution, source_hard_label, derived_single_point}`，
在字段层面就能区分；在此之前，请按上表过滤，或只把 `answer` 当标签用。

**均匀分布没有信息量**（多来自教师模型的低置信样本），用它做监督等于教模型"别确定"：
报告指标时建议同时给"排除均匀目标"的子集分数。

## 3. 覆盖域（每个域设下限配额，宁缺毋滥）

| domain | 覆盖什么 | 主要来源 |
|---|---|---|
| `decision_mechanics` | 工具选择、下一步动作、计划、资格/权限判定 | Jev Decisions v1、Open-Jev、tasksource-jev |
| `human_judgment` | 真人情感/毒性/蕴含判断，含多人 vote 分布 | GoEmotions、Civil Comments、ChaosNLI（经 jev-bench 定位，但取其**上游 train 划分**） |
| `social_moral` | 亲社会回应、道德规范、动机→行为→后果 | ProsocialDialog、Social Chemistry、Moral Stories |
| `risk_harm` | 伤害类别、越狱与对抗、升级判断 | WildGuardMix、PKU-SafeRLHF |
| `knowledge_reasoning` | 常识与知识型判断，防止只会做治理题 | 受许可的问答类来源 |
| `pol2_axis` | 关怀与控制、同意撤回、批评与人格、公共性等判定轴 | 与 datasets/pol2 的 15 条判定轴对齐 |

**已知边界**：`Praveenrajus/jev-bench` 全部划分都是 `test`，它本身是排行榜基准，
**只能当外部评测，不得进训练**。要做真人校准监督，请取其上游数据集各自的 train 划分。

## 4. 规模与配额

- 总量下限 **10,000 条**，目标 20,000–30,000 条；每个覆盖域至少 1,200 条。
- 单一来源占比不得超过 40%，防止某一家数据定义整个表示。
- 同一 `state` 的翻译与改写视为同族，只能出现在同一分区。

## 5. 目录与文件归属

| 路径 | 内容 | 归属 |
|---|---|---|
| `datasets/general/README.md` | 面向协作者的总览 | db-hf |
| `datasets/general/CONTRACT.md` | 本契约（字段与格式） | Lead |
| `datasets/general/sources.json` | 来源清单与配额 | Lead |
| `datasets/general/taxonomy.py` | 覆盖域与问题键定义 | db-schema |
| `datasets/general/coverage.py` | 覆盖报告与配额校验 | db-schema |
| `datasets/general/fetch.py` | 下载（datasets-server 分页）与断点续跑 | db-hf |
| `datasets/general/convert.py` | 各来源 → 统一 schema（`--native` 为主路径） | db-hf |
| `datasets/general/slim.py` | 字段精简（manifest + 紧凑引用） | db-hf |
| `datasets/general/merge.py` | 合并中英最终语料 | db-hf |
| `datasets/general/ask.py` | 批量作答harness（Jev 适配、可续跑、默认离线） | db-ask |
| `datasets/general/luna_clean.py` | 自回归输出清洗成严格决策格式 | db-luna |
| `datasets/general/data/` | 构建产物 `items.jsonl` 等 | Lead 统管 |

原始下载放仓库外（`D:\pol2-raw\`），仓库只提交构建后的 items 与清单。

## 6. 已知限制（施工中发现，不要当成已解决）

1. **HF datasets-server 不遵守 revision 参数。** 实测带伪造 sha、别人的 sha、不带 revision，返回的首行完全相同。
   抓取时的做法是：先用 HF API 解析当前 sha 并与 sources.json 的固定值比对，不一致就停下；
   manifest 记录 revision、revision_enforced=false 与抓取后复核得到的 revision_stable。
   **真正逐字节可复现需要走 resolve/<sha>/<path> 下载文件**，而不是 /rows 分页接口。本阶段未做这一步。
2. **length 上限 100**，超过返回 422。
3. **config 名里的加号必须转义**（%2B），否则会被 query 解析成空格导致 404。
4. **来源问题与 taxonomy 键不是一一对应。** 已知：jev-distill-v3 的 score 是 0-5 六档（本契约的 score 键是 0-4 五档），
   其 noul 是场景专属谓词；prosocial-dialog 的三标注 vote 与 safety_label 五档在本契约里没有等义键。
   处理口径：**不硬塞档位**，原生问答与分布保留在 meta.source_record，条目按该域的 CORE 键提问、targets 留空等外部答案源。
   转换汇总必须分别报告 native_target_rate（带真值的条目占比）与待作答条目数。
5. 语义近重复与同情节跨区检测、跨文件/跨来源 id 去重，本阶段均未实现。
6. **伪 one-hot 与"不伪装概率"冲突**：14,119 个问题的 probs 是硬标签造的单点分布（benchmark 内 1,398），
   判别与修法见 §2.3。训练时若不先过滤，分布类损失（KL / 软交叉熵 / 校准）会学到退化解。
7. **均匀分布 target 无信息**：1,730 个问题（benchmark 内 180）各项概率相等，建议排除后再报分。
8. **train 与评测区的域分布不可比**：risk_harm（2,605）与 human_judgment（543）**只存在于 train**
   （全部来自中文补充集），test / validation / benchmark 在这两域为 0。任何跨区的域间对比都会被该结构差异污染。
9. **内部 benchmark 保密性当前不达标，正在整改**：复核确认"仓库内公开文件 + 公开种子"可逐字节重建 benchmark，
   且曾有 5,454 行中文答案索引与 9 条 benchmark 记录进入版本库。整改方向：私盐重切 + 完整语料移出版本控制
   + 不把完整语料与三个公开分区同时发布。**整改完成前请视为已泄漏。**
10. **split-manifest 有 2 条摘要与磁盘不符**（benchmark-dataset/README.md、benchmark-dataset/manifest.json），
    属于切分侧待修项（随整改一并重生成）。
11. **配额口径与当前语料不匹配**：六域下限是按已退役的混合语料定的；当前语料实测
    items.final 在 human_judgment / social_moral / risk_harm 三域为 0，items.native 另有单一来源占 48.5% > 40%。
    配额需随语料重定，见 §7。

## 7. 检查

    uv run --no-project --offline python tools/check.py

    # 覆盖与配额。注意：六域配额是按【已退役】的模板语料定的，对当前语料会报 NG（见 §6 第 11 条）：
    #   items.final → human_judgment / social_moral / risk_harm 三域为 0，报 3 项不通过；
    #   items.native → 另有单一来源 jev-distill 占 48.5% > 40%，报 4 项不通过。
    uv run --no-project --offline python datasets/general/coverage.py --items datasets/general/data/items.final.jsonl

    # 切分复现。两个坑：旗标是 --input；默认 --out/--report 指向交付目录，会把 train（含追加的 3,148 条
    # 中文补充）与 split-report.md 一起覆盖，必须显式指到仓库外。
    uv run --no-project --offline python datasets/general/data/splits/split.py \
        --input datasets/general/data/items.final.jsonl \
        --out <仓库外目录> --report <仓库外目录>/split-report.md --seed 20261005
