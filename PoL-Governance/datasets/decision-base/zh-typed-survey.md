# 中文原生 typed decision 补搜（task-17）

- 日期：2026-10-05（UTC+8）｜执行：pol2-replay（DSH Agent Team）
- 目标：按「**数据集本身提供 (state, question, options, target)**、且是我们之外的作者发布、可独立溯源」的口径补搜中文来源。
  英文侧重建后约 15,915 条，中文 ≥30% 需要约 **6,821** 条。
- 约束重申：**不是**我们生成的、**不是**单标签分类套模板、**不是**机翻；评测集只能登记为外部评测。
- 覆盖：**208 次 HF 检索**（function-calling / tool / api / agent / dialogue-act / 机构扫描等，含 `filter=language:zh`），
  去重 **5,219 个 dataset id**；32 份元数据、20 份 datasets-server 字段快照、15 组真实行抽样。
- 方法沿用以固定 revision + 逐条许可判读 + 证据等级（A 读过卡面与实际行数据 / B 读过卡面 / C 只有元数据 / D 只有检索元数据）。

## 0. 结论先说

1. **有**。`Deepexi/function-calling-small` 是**原生中文 typed decision**：每行自带 3–6 个候选函数（含中文描述）、
   一句中文请求、以及被选中的那个函数。**24,608 行**，一次就超过 6,821 的需求（约 3.5 倍余量）。
2. 但它有三个必须写清楚的限制：**单一来源**、**只覆盖 decision_mechanics 一个域**（`knowledge_reasoning` 中文侧仍为 0）、
   **没有「不需要调工具」的负类**（每行都有一个正确函数）。
3. 除它之外，本轮**没有找到第二个合格的中文原生 typed decision 来源**。其余候选要么是英文（结构对、语言不对），
   要么是评测基准，要么是单标签分类/对话行为标注，要么是机翻。**没有降门槛收进来。**

## 1. 准入（1 个数据集 / 2 个文件 / 24,608 行）

| HF dataset | 固定 revision | 许可 | 产生方式 | 语言 | 规模 | 字段 | 原生四元组 | 评测集 | 证据 |
|---|---|---|---|---|---|---|---:|---:|---:|
| `Deepexi/function-calling-small` | `8fba7ee941523e7da69f4ff882b52e5566d24288` | cc-by-4.0 | 由 700+ 个阿里云 OpenAPI 定义构造的**中文**函数选择样本（卡面未写生成模型，无翻译痕迹） | zh | 24,608 行（CSV：`function-calling-small_aliyun_openapi_V2.csv`） | `systemPrompt` / `userPrompt` / `assistantResponse` | **是**（候选菜单在 systemPrompt、问题在 userPrompt、答案在 assistantResponse） | 否（只有一个 train 划分，无 test/leaderboard） | **A** |
| `Deepexi/openai-formate-function-calling-small` | `6d1dc02a2549104cc9cd2828c4b8647e9f994341` | apache-2.0 | 同上，函数 schema 换成 OpenAI tools 格式（`name/parameters`） | zh | 24,608 行 | 同上 | 是 | 否 | **A** |

**结论：准入，但只按一个来源计数**——两份文件抽样 30/30 行完全重合（同一 userPrompt + 同一 target），
是**同一批数据的两套函数 schema**，不是两个来源；入库只能取其一（建议 V3/OpenAI 格式那份，schema 更通行）。

### 为什么算「原生 typed decision」

- 行内自带候选集：systemPrompt 里并列给出 3–6 个函数定义（**剔除格式模板占位符 `function_name` 后**），
  每个函数有中文 `description` 与参数说明；
- 行内自带问题：`你是一个函数筛选助理，如果与问题相关的话,您可以使用下面的函数…`；
- 行内自带 target：`assistantResponse` 给出被选中的函数名与参数；
- 语言原生：560 条抽样的 userPrompt **全部是中文**（如「我想查一下指定票据值为"123456"的详情信息。」），
  函数描述来自阿里云中文文档；函数名是英文（API 命名本如此），不是机翻。

### 真实样例（实际拉取，未编辑文字；systemPrompt 截断）

**样例 A**（offset 0）：

```json
{
  "systemPrompt": "你是一个函数筛选助理，如果与问题相关的话,您可以使用下面的函数来获取更多数据以回答用户提出的问题:{\"function\": \"CreateExportMigration\", \"description\": \"使用CreateExportMigration，新建DataWorks导出任务且仅创建导出任务。\", \"arguments\": [{\"name\": \"ProjectId\", \"type\": \"integer\", …}]} …（共 5–6 个候选函数）… 请以如下格式回复：:{\"function\":\"function_name\",\"arguments\": {\"argument1\": value1,…}}",
  "userPrompt": " \"更新免登嵌入报表的票据数量为10的票据值为\"abcd1234\"。\" ",
  "assistantResponse": "{ \"function\": \"UpdateTicketNum\", \"arguments\": [ { \"Ticket\": \"abcd1234\", \"TicketNum\": 10 } ] }"
}
```

**样例 B**（同一批数据里候选菜单最短的一条，3 个真实候选 + 1 个占位符）：

```json
{
  "systemPrompt": "你是一个函数筛选助理，如果与问题相关的话,您可以使用下面的函数来获取更多数据以回答用户提出的问题:{\"function\": \"QueryTicketInfo\", \"description\": \"获取免登嵌入报表的指定ticket的详情信息。\", \"arguments\": [{\"name\": \"Ticket\", \"type\": \"string\", \"description\": \"票据值。\"}]} …（另有 GetQuotaPlan 等）…",
  "userPrompt": " \"我想查一下指定票据值为\"123456\"的详情信息。\" ",
  "assistantResponse": "{ \"function\": \"QueryTicketInfo\", \"arguments\": [ { \"Ticket\": \"123456\" } ] }"
}
```

### 质量与可用量（560 行抽检，跨 offset 0/5,000/10,000/15,000/20,000/24,000）

| 指标 | 实测 |
|---|---|
| 抽样行数 | 560（每行 (systemPrompt,userPrompt) 唯一，560/560） |
| 真实候选数（剔除 `function_name` 占位符） | 3–6 个，平均 4.49 → 落在本契约 choice 的 2–16 选项区间内 |
| target 命中候选集 | 544/560 = **97.1%** |
| target 不在候选集 | 4/560 = 0.7%（例如菜单里没有 `ListInstances` 却答了它）→ 入库时剔除 |
| assistantResponse 不是合法 JSON | 12/560 = 2.1%（CSV 里的换行把 JSON 拆断）→ 入库时剔除 |
| systemPrompt 含格式模板占位符 `function_name` | 560/560（**必须剥掉**，否则会被当成候选） |
| 抽样覆盖到的不同函数名 | 666 个（卡面称 700+ 个阿里云 OpenAPI） |
| userPrompt 为中文 | 560/560 |

**扣掉 2.9% 的坏行后可用量 ≈ 23,900 条**（24,608 × 97.1%），仍然远超 6,821。

### 映射到本契约

- 域：`decision_mechanics`；问题键用 **`next_step_candidate`**（taxonomy 里为「条目自带候选」专门定义的 choice 键，
  `options_from_state=True`），`options` 直接取该行的候选函数名 + 中文描述，`target.answer` 取被选中的函数；
- 函数参数（`arguments`）本契约没有对应的键，按「不硬塞」口径原样进 `meta.source_record`；
- 许可链说明：数据集声明 cc-by-4.0 / apache-2.0（Deepexi），但内容取材自**阿里云公开 OpenAPI 文档的中文接口说明**——
  这部分不是数据集许可，入库需保留 Deepexi 署名并注明来源，必要时再与阿里云条款核对（与 CValues 的处置同一口径）。

## 2. 观察（形态接近但不够格，不进准入）

| HF dataset | revision | 许可 | 语言 / 规模 | 结构 | 为什么只观察 |
|---|---|---|---|---|---|
| `chris0809/scope-intent-routing-20k` | 见 HF | apache-2.0 | zh+en / 20,000（14k/3k/3k） | `text,label,label_id,language,domain,difficulty`；标签 2 类：`DIRECT_RESPONSE` / `REQUIRES_SCOPE_CONTRACT` | **单标签分类**（每行不自带候选），且是 Qwen3.7-Flash 按 80 个人工种子族生成的合成数据。语义上接近 `tool_use_appropriate`(noul)，但属于「套模板」范畴，按口径不进准入 |
| `JayYz/multi_agent_handoff` | `5faaa754d9dcebf3945d00f984ec2256c59147ad` | apache-2.0 | zh+en / 2,199 | `instruction`(英文域模板 + 子代理清单) / `input`(中或英) / `output`(`transfer_to_X_agent`) | 结构是 choice（选哪个子代理），但清单与模板是英文，只有约一半（抽样 18/40）输入是中文；且为 GPT-4 合成 |
| `GEM/RiSAWOZ` | `d9287b21928a811281a349655655ee4be964292a` | cc-by-4.0 | zh / 10,000 段对话 | `dialogue` 内含 `user_actions`/`system_actions`，形如 `[["Inform","旅游景点","门票价格","110 元"]]` | 有「下一步动作」标注，但动作是全库固定枚举（Inform/Request/…），不是每行候选；target 是四元组不是选项 key |
| `GEM/CrossWOZ` / `ConvLab/crosswoz` | 见 HF | apache-2.0 | zh | — | datasets-server 取不到行（404/500），**本轮未能核验**，按「未知」处理 |
| `lituokobe/LoRA-Samples-Intention-Classifier` | 见 HF | apache-2.0 | zh+en / 10,104 | 只有 `messages`，意图 JSON 内嵌在 assistant 消息里 | 意图来自固定枚举，问题写在 system prompt 里，不是行内候选集 |
| `trytax/openclaw-zh-intents-50k` | 见 HF | mit | zh / 10K–100K | 未取到字段 | datasets-server 404，未能核验 |
| `voidful/agent-sft-stitch-zh` | `9f2fddfb1e33c9462dc96229a22bc2914e63ea01` | other | zh(繁) / 10K–100K | STITCH-S 轨迹（SAY/SOPR/TOOL_CALL） | **机改**：卡面写明由英文 `voidful/agent-sft` 用 gemma-4-26B 改写成台湾繁中；且许可为 other。按「机翻不算中文原生」剔除优先级 |
| `kapibala-ai/sales-conversations-150-zh` | 见 HF | mit | zh / 150 | 销售对话 + trigger 句 | 没有候选集与 target，只是对话脚本 |

## 3. 剔除（结构对但语言不对 / 评测集 / 许可或形态不符）

**3.1 英文同类（结构完全对味，但语言是英文——不能当中文来源）**

`Team-ACE/ToolACE`（apache-2.0，抽样 han-ratio=0）、`lockon/ToolACE`、`Emulated-Inc/api-calling-training-pool`（cc-by-4.0，23,953 行，抽样 60 行全英文）、
`internlm/Agent-FLAN`（apache-2.0，WebShop/ToolBench 英文）、`openbmb/UltraData-SFT-Agent-2609`（Tool-Use 配置为 tau2-bench 英文）、
`MasterVito/swe-agent-tool-rubrics-860`（候选命令 + `executed_idx`，结构极佳但英文且许可 other）、
`r0b0tlab/deepseek-v4-pro-0813-agentic`、`zake7749/Qwen3.6-*Tool-Calling`、`pyromind/agentic-tool-call-dataset-12k`、
`Salesforce/xlam-function-calling-60k`、`NousResearch/hermes-function-calling-v1`、`glaiveai/glaive-function-calling-v2`、
`Deepexi/glaive-function-calling-vicuna`（Deepexi 自己的英文数据）。

**3.2 评测基准 / 对抗考卷（只登记为外部评测，不进训练）**

- `liminghao1630/API-Bank`（mit，**英文**；仓库结构 `training-data/` + `test-data/`，level-1/2/3）：本体是 API 调用基准，
  `test-data` 绝不可进训练；其 training-data 也是英文，故本轮不取。
- `hkust-nlp/Toolathlon`（NONE/cc-by-4.0 混杂）、`hkust-nlp/Toolathlon-Trajectories`、`Qwen/AgentWorldBench`、
  `Qwen/DeepPlanning`、`internlm/WildClawBench`(+Harbor/Trajectories)、`zai-org/AgentInstruct`、`zai-org/CC-Bench-trajectories`、
  `tencent/PlanningBench`、`THU-KEG/AgentIF`(CC-BY-NC)、`ByteDance/veAgentBench`(CC-BY-NC)、
  `uninhibited-scholar/agent-safety-bench-zh`、`DataCanvasAILab/Titan-CV-Agent-Benchmark`、
  `LLaMAX/BenchMAX_Function_Completion`、`hkust-nlp/agentboard`(GPL)。
- 按 Lead 提醒点名确认：**C-Eval、CMMLU、MMLU-zh（含 `lmlmcat/cmmlu`、`ceval/ceval-exam`、`openai/MMMLU`、
  `ikala/tmmluplus`）全部是中文评测集**，只能作外部评测；其中 `ceval/ceval-exam`、`lmlmcat/cmmlu` 还是
  CC-BY-NC-SA / CC-BY-NC 许可，双重不符合。

**3.3 许可不明 / NC / 形态不符**

`zr-wang/AgenticOCR-SFT`(NONE)、`Trelis/function_calling_v3`(NONE)、`zhendongnvidia/*`(NONE)、`BitAgent/tool_calling`(NONE)、
`smolagents/toolcalling`(NONE)、`DeepNLP/Agent-Tool-Use-Dialogue-Open-Dataset`(NONE)、
`LiAuto-DriveAction/drive-action`（cc-by-4.0，16,185 行，抽样的 `choice_questions` 里 `options` 全为 null，且状态含图像）、
`thu-coai/kdconv`（知识驱动对话，无候选/答案）、`mikuhhn1239/novel-agent-sft-dataset`（中文小说续写，非决策）、
`openbmb/UltraData-SFT-Agent-2609`（英文 + 预训练/SFT 语料形态）。

## 4. 汇总：能不能支撑中文 ≥30%

| 项目 | 数值 |
|---|---:|
| 英文侧（Lead 给的数） | ≈15,915 |
| 30% 所需中文 | ≈**6,821** |
| 准入可用中文原生 typed decision | **≈23,900**（24,608 × 抽检可用率 97.1%） |
| 余量 | **≈3.5×** |

**结论：够。** 但有三个限制必须一起报给用户，不能只用总数回答：

1. **单一来源**。中文侧 100% 来自 Deepexi。合并语料按 15,915 en + 6,821 zh 计，该来源占 6,821/22,736 = **30.0%**，
   低于契约 §4 的 40% 上限；但若想把中文占比提到 **>10,600 条**（即合并语料里 Deepexi 超过 40%），
   就必须有第二个来源——本轮**没有**。
2. **单一域**。这 24,608 条全部落在 `decision_mechanics`（工具/函数选择）。上一轮报告里
   「中文侧 `decision_mechanics` 为 0」的缺口**可以补上**，但 **`knowledge_reasoning` 中文侧仍然是 0**：
   中文没有「陈述是否有据、证据是否充分、推理是否有效」的原生 typed decision 来源。
3. **没有负类**。每一行都有一个正确函数，**不含「不需要调用工具/应该先澄清」的样本**。
   只用它训练，中文侧的「该不该动手」判断没有监督；要补这一档，目前只能靠 `chris0809/scope-intent-routing-20k`
   这类单标签数据做 documented 映射（本轮按口径未计入准入）。

**另外两条施工注意事项**（来自实测）：

- 每行 systemPrompt 里的 `{"function":"function_name",...}` 是**输出格式模板**，不是候选，入库前必须剥掉，
  否则候选集会被污染成 4–7 个（真实是 3–6 个）。
- CSV 里的多行 JSON 会让 2.1% 的 assistantResponse 解析失败；转换器要按「解析失败即丢弃」处理，
  不要猜 target（本契约的既定口径：失败不写 ok）。

## 5. 复现命令（只读；HF 与 datasets-server，原始行落仓库外）

本轮全部用 pwsh `Invoke-WebRequest` 直接打 HF 官方接口（本环境 web_fetch 访问 huggingface.co 被拦）：

```powershell
# 1) 固定 revision 与许可
Invoke-WebRequest 'https://huggingface.co/api/datasets/Deepexi/function-calling-small' -UseBasicParsing |
    Select-Object -ExpandProperty Content | ConvertFrom-Json |
    Select-Object sha, @{n='license';e={$_.cardData.license}}, @{n='lang';e={$_.cardData.language}}

# 2) 字段与首行快照
Invoke-WebRequest 'https://datasets-server.huggingface.co/first-rows?dataset=Deepexi%2Ffunction-calling-small&config=default&split=train' -UseBasicParsing

# 3) 行数与抽样（length 上限 100；深 offset 慢，本轮取 0/5000/10000/15000/20000/24000 六个窗口共 560 行）
Invoke-WebRequest 'https://datasets-server.huggingface.co/rows?dataset=Deepexi%2Ffunction-calling-small&config=default&split=train&offset=0&length=100' -UseBasicParsing

# 4) 仓库检查（链接 + 测试）
uv run --no-project --offline python tools/check.py
```

本轮抽样与统计脚本均为一次性只读脚本，产物在 `%TEMP%\zht-typed\rows\`（仓库外）。

## 6. 与上一轮（task-14）的关系

- task-14 的结论是「中文侧 `decision_mechanics` / `knowledge_reasoning` 为 0，缺口真实」；
  本轮用一个**搜索框架的修正**（按 typed decision 结构而不是按主题搜）找到了 **24,608 条中文函数选择决策**，
  可以补上 `decision_mechanics`；
- `knowledge_reasoning` 的中文缺口**仍然存在**，本轮没有找到任何合格来源（中文的常识/证据/推理数据要么是评测集，
  要么是英文，要么是单标签）。
- 因此 task-14 报告第 6.4 节的建议不变：**A（先测差距）+ B（生成式补数据）仍然要做**，
  但 A/B 的优先项可以从「decision_mechanics」改成「knowledge_reasoning」。
