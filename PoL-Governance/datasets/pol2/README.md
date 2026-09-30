# PoL2 中文决策数据集（DATA-02）

本目录是 PoL2 治理层的正式数据入口。它把 PoL2 理论转化成**可判断、可复算、可交叉验证**的机器决策数据：场景 + 类型化问题 + 候选答案 + 裁决真值。

上游依据：[SPEC](../../SPEC.md)、[协议](../README.md)、[数据边界](../README.md)、[AGENTS](../../AGENTS.md)。
理论依据：PoL2 第 1 章（爱2/恨2/野蛮2/文明2）、第 2 章（16 爱语）、第 5 章（伦理对齐协议 EAP）。

## 1. 设计约束（先读）

1. **不新造平行 schema。** 正式数据是 [pilot 案例格式](../../benchmark/pilot.jsonl) 的超集：`input`/`proposal` 的字段语义保持不变，新增字段独立命名，既有评测器不改。
2. **问题与答案分离。** 问题文件可公开（无参考标签）；答案文件按来源各存一份，永不覆盖；真值单独裁决。
3. **分区按场景族整体切分。** 同一情节、翻译与改写不跨区。7 成训练、2 成公开测试、5% 校验、5% 私有保留。
4. **私有保留集不进仓库。** 仓库只登记版本、规模与汇总评测；内容在仓库外保管。
5. **小样本先跑通再放量。** 任何生成/标注脚本都必须支持 `--limit` 与断点续跑。
6. **不得用情绪或措辞当行为性质。** 愤怒、批评、拒绝、异议、求救不是违规；温柔措辞不构成免责。

## 2. 四层数据模型

```
case     一条场景：谁、在什么上下文、做了什么待判定行为、引用哪条 PoL2 条款
  └ question  针对该场景的类型化问题（choice / noul / score），可一问多条
      └ answer    某个答案源对该问题给出的答案与概率
          └ label     交叉验证与裁决后的真值，绑定 case
```

数据流：

```
场景族清单 ──► Luna 批量生成 case ──► 由 case 派生 question
                                        ├─► Jev 官方接口取答案
                                        ├─► GLM-5.3 取答案（教师 A）
                                        └─► 第二教师取答案（教师 B）
                                                 └─► 分歧裁决 ──► label
```

## 3. 记录格式

四类文件都用 UTF-8 的 JSONL，一行一条。字段名固定，不额外增删；扩展只走 `extra` 对象。

### 3.1 case（`<region>.cases.jsonl`）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | `pol2-<region>-<6 位序号>`，全局唯一 |
| `family_id` | string | 是 | 场景族，点分小写，如 `consent.withdrawal.multiturn` |
| `region` | string | 是 | `train` / `public_test` / `validation` / `private_holdout` |
| `lang` | string | 是 | `zh` 为主，英译为派生 |
| `input.surface` | string | 是 | `user_input` / `assistant_output` / `tool_action` |
| `input.context` | string[] | 是 | 非空字符串数组，多轮按时间顺序 |
| `input.target` | string | 是 | 待判定的具体行为，不写结论 |
| `input.policy` | string | 是 | 引用的 PoL2 条款文本；`clause` 记条款 id |
| `input.clause` | string | 是 | 如 `PoL.2.10`、`EAP.5.3.2` |
| `provenance` | object | 是 | `generator,model,prompt_id,gen_version,seed,created_at` |

### 3.2 question（`<region>.questions.jsonl`）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qid` | string | 是 | `<case id>.<key>`，全局唯一 |
| `id` | string | 是 | 所属 case id |
| `kind` | string | 是 | `choice` / `noul` / `score` |
| `key` | string | 是 | 该问题的短键，如 `status`、`action`、`issue.consent` |
| `prompt` | string | 是 | 中文问题文本 |
| `options` | object[] | choice/noul 必填 | `{key,label}`；noul 固定 `yes`/`no` |
| `scale` | object | score 必填 | `{min,max,labels}` |

### 3.3 answer（`<region>.answers.<source>.jsonl`）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qid` | string | 是 | 指向 question |
| `source` | string | 是 | `luna` / `glm-5.3` / `jev-<version>` / 其他，写进文件名 |
| `source_version` | string | 是 | 固定版本或接口版本，便于复算 |
| `answer` | string 或 number | 是 | choice 用 option key；noul 用 `yes`/`no`；score 用数值 |
| `probs` | object | 否 | 归一到 1 的概率；缺省表示该源不给概率 |
| `execution_status` | string | 是 | `ok` / `timeout` / `error` / `invalid` |
| `latency_ms` | number | 是 | 客户端全程耗时 |
| `raw` | object | 否 | 原始响应；仅在许可允许公开时提交 |
| `created_at` | string | 是 | ISO 8601 带时区 |

### 3.4 label（`<region>.labels.jsonl`）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 指向 case |
| `status` | string | 是 | `conforming` / `violating` / `insufficient`，沿用既有三态 |
| `polarity` | string | 是 | PoL2 原生：`love` / `hate` / `neither` / `unclear` |
| `issues` | string[] | 是 | PoL2 分类，见本体；`conforming` 时可为空 |
| `love_languages` | string[] | 否 | 16 爱语之一或多，文明行为时用 |
| `mitigations` | string[] | 否 | 例外与辩护标志，防误拦 |
| `evidence` | string | 是 | `sufficient` / `insufficient` / `contradictory` |
| `acceptable_actions` | string[] | 是 | 非空，取值同协议五动作 |
| `probs` | object | 否 | 三态概率，和为 1 |
| `citations` | string[] | 是 | 条款 id，至少一条 |
| `brief_reason` | string | 是 | 一句话理由 |
| `review` | object | 是 | `sources`、`agreement`、`disagreements`、`adjudicated_by`、`review_level` |

`review_level` 取值 `model_cross_checked` / `human_reviewed`。**不得把 `model_cross_checked` 写成金标准。**

## 4. 标签体系 v0.1

本体与判据细则见 [ontology](ontology/README.md)。要点：

- **status 三态**沿用仓库协议，保证既有工具与结果可比。
- **polarity** 表达 PoL2 特有的第四种情形：非爱非恨的「不在场」（干扰、疾病、理解偏差）。它不是违规，因此 `status=conforming` 且 `polarity=neither`，模型不得道德化。
- **issues** 从恨2 的定义派生（暴力崇拜、排他性私有、敌意排斥分离、欺骗扭曲、尊严否定、胁迫操控、公共性侵蚀、生态伤害），外加两条 PAI 专属约束：虚构亲密、检测人的情感状态。
- **mitigations** 是防误拦的关键：值守安全的恨、正当批评、正当愤怒、拒绝与异议、修复行为、纯粹游戏与幽默的边界。

## 5. 分区与防泄露

`splits.py` 按**场景族**整体分配，族内不跨区。分配使用仓库外私有盐值，仓库只保存流程与汇总计数：

```powershell
uv run --no-project --offline python datasets/pol2/splits.py assign --families datasets/pol2/families.jsonl --salt-file <仓库外私有盐值> --out <仓库外分配表>
uv run --no-project --offline python datasets/pol2/splits.py verify --assign <分配表> --families datasets/pol2/families.jsonl
```

- 生成/训练 Agent 只拿 `train`、`public_test`、`validation`。
- `private_holdout` 的族由独立保管者生成，直接写入仓库外目录，本仓库不提交内容、逐例答案或生成提示。
- 公开测试一旦被用于改方案，必须在结果卡披露，不再称盲测。

## 6. 目录与文件归属

| 路径 | 内容 | 归属 |
|---|---|---|
| `datasets/pol2/README.md` | 本契约 | DATA-02 lead |
| `datasets/pol2/splits.py` | 族级分区与校验 | DATA-02 lead |
| `datasets/pol2/ontology/` | 标签本体、判据、测试项矩阵 | DATA-02 本体 |
| `datasets/pol2/pipeline/` | 生成、取答案、裁决流水线 | DATA-02 流水线 |
| `benchmark/pol2/` | 正式评测入口与指标 | EVAL-01 |

## 7. 检查

```powershell
uv run --no-project --offline python tools/check.py
uv run --no-project --offline python datasets/pol2/splits.py verify --assign <分配表> --families datasets/pol2/families.jsonl
```
