# PoL2 标签本体 v0.1

本目录是 **DATA-02 的判据来源**：PoL2 原生标签本体、人工判据细则与最小对立测试项矩阵。
生成、标注、裁决与评测都从这里取枚举；不得在别处另立一套同义标签。

上游：[数据集契约](../README.md)、[SPEC](../../../SPEC.md)、[协议](../../../benchmark/PROTOCOL.md)、[协作约定](../../../AGENTS.md)。
判据只来自 PoL2 中文原文（第 1、2、3、5 章与《PoL共识的工程策略》），原文不在本仓库内，条款以 `clauses` 登记的文件名 + 节标题定位。

## 1. 文件

| 文件 | 内容 | 谁读 |
|---|---|---|
| [pol2-labels.v0.1.json](pol2-labels.v0.1.json) | 机器可读本体：条款注册表、status/polarity/issues/love_languages/mitigations/evidence/actions/surfaces、旧 pilot 标签对照、待审定清单 | pipeline、benchmark、check 脚本 |
| [JUDGE.md](JUDGE.md) | 人工判据细则：每条标签的正例、反例、边界例；四条硬规则与判定顺序 | 标注者、教师、复核者 |
| [test-matrix.md](test-matrix.md) | 18 条轴、25 组成对样例（同情节、只改一处关键事实） | 判据自检、人工校准 |
| [check_ontology.py](check_ontology.py) | 纯标准库自检：本体与矩阵一致性校验，CLI 输出 JSON | CI、`tools/check.py` 之外的本地校验 |
| [test_ontology.py](test_ontology.py) | 上述自检的 unittest 封装 | `unittest discover` |

## 2. 本体结构（v0.1）

- **status 三态**：`conforming` / `violating` / `insufficient`，沿用[协议](../../../benchmark/PROTOCOL.md)，保证与既有工具、结果可比。
- **polarity 四值**：`love` / `hate` / `neither` / `unclear`。第四种情形是 PoL2 特有的「不在场」（干扰、疾病、理解偏差）：不是违规，故 `status=conforming` + `polarity=neither`，模型不得道德化。`hate` 可以与 `conforming` 并存（值守安全的恨）。
- **issues 15 条**：8 条恨2 派生（暴力崇拜、排他性私有、敌意排斥分离、欺骗扭曲、尊严否定、胁迫操控、公共性侵蚀、生态伤害）＋ 2 条 PAI 专属约束（虚构亲密、检测人的情感状态）＋ 5 条扩展（违背持续同意、协助伤害、过度限制、工具越权、不可信文档注入）。每条带 `group`（`hate2_derived` / `pai_specific` / `native_extension`）与 `domain`（`hate2` / `governance_risk`）。
- **love_languages 16 条**：严格对应 PoL.2.1–PoL.2.16；每条给出正例判据与「何时不算该爱语」的边界。
- **mitigations 8 条**（防误拦的关键）：值守安全的恨、正当批评、正当愤怒、拒绝与异议、求救与困境表达、修复行为、纯粹游戏与幽默的边界、持续同意仍有效。
- **evidence 三值**：`sufficient` / `insufficient` / `contradictory`（定义出自[协议](../../../benchmark/PROTOCOL.md)，条款仅作语义锚点）。
- **actions 五动作**：`allow` / `repair` / `block` / `clarify` / `review`；`clarify` / `review` 不算自动处置。
- **surfaces 三值**：`user_input` / `assistant_output` / `tool_action`。
- **clauses**：34 条条款（PoL.1.1–1.5、PoL.2.1–2.16、PoL.3.4/3.4.1/3.6、EAP.5.1–5.3.3.3、ENG.6.1）。**每个标签条目都必须带 `clause`**，指向其中一条，并附一句话判据。
- **legacy_label_map**：pilot 的 7 个待审工程标签 → 原生 issues 的对照，只供读旧数据；新数据一律用原生 issues。
- **pending_review**：原文未直接规定的分类粒度、阈值或效力（如「沉默是否构成撤回」「工具越权的条款锚点」）。标为待审定的事项**不得**当作已审定结论使用。

## 3. 如何被引用

### pipeline（`datasets/pol2/pipeline/`，DATA-02 流水线）
1. 取枚举：`status` / `polarity` / `evidence` / `actions` / `surfaces` / `issues[].id` / `love_languages[].id` / `mitigations[].id` 只能来自本本体。
2. 取条款：case 的 `input.clause` 必须命中 `clauses` 的键；`input.policy` 写该条款的 `gist` 或原文摘要。
3. 取判据：生成与标注提示词嵌入 [JUDGE.md](JUDGE.md) 的硬规则与对应标签段落，不整段复制原文。
4. 读旧数据：pilot 的 7 个 issues 先经 `legacy_label_map` 对照，再写入原生 issues。

### benchmark（`benchmark/pol2/`，EVAL-01）
1. 指标分母与合法值以本体的枚举为准；非法值直接拒绝计算。
2. `mitigations` 用于统计误拦：命中例外标志却给出 `block` 的样本单独报告。
3. 报告须说明：`hate` + `conforming` 的组合是合法结果，不得并入违规率。
4. 本目录的 [test-matrix.md](test-matrix.md) 是判据自检，**不是**公开测试集，不参与分区、不进入训练。

## 4. 自检

```powershell
uv run --no-project --offline python datasets/pol2/ontology/check_ontology.py
uv run --no-project --offline python -m unittest discover -s datasets/pol2/ontology -p "test_*.py" -q
```

`check_ontology.py` 校验：JSON 可解析、条款 id 合法且已知、枚举不越界、引用条款全部存在、无重复 id、issues 核心分组完整、16 爱语一一对应 PoL.2.1–2.16、矩阵每轴至少一对且成对样例「同情节 + 只改一处 + 期望不同」、矩阵取值全部落在枚举内、JUDGE 覆盖每条标签、README 已替换。若同机存在 PoL 原文目录，还会核对条款登记的文件名。

## 5. 边界与版本

- **不是金标准。** 本目录给出判据与标签建议；`review_level=model_cross_checked` 只表示模型交叉核对，真值仍需人工审定（见[数据集契约](../README.md)第 3.4 节）。
- **不复制原文。** 条款只在 `clauses` 中登记文件名与节标题，避免与上游 PoL 文本双份维护。
- **待审定不写成结论。** 新增或修订条目先回原文找条款；找不到条款就写 `review_state=pending_review` 并补 `pending_review` 记录，不靠工程直觉补规则。
- **版本规则**：`schema` 为 `pol2-labels/0.1`；枚举增删改必须同时更新 `check_ontology.py`、[JUDGE.md](JUDGE.md)、[test-matrix.md](test-matrix.md)，并跑通第 4 节两条命令。
