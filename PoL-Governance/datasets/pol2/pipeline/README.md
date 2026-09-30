# PoL2 生成与真值流水线（DATA-02 流水线）

本目录实现 [数据集契约](../README.md) 第 3 节的四类记录：case → question → answer → label。
字段名以契约第 3 节为准，扩展只走 extra 对象；本文件只记录实现口径与外部接口。

    datasets/pol2/pipeline/
      common.py      契约校验、JSONL 读写、断点续跑索引、密钥装载（不联网）
      prompts.py     提示模板与模板版本、问题派生、答案解析、最小对立对质检
      clients.py     统一模型客户端：重试/退避/429/5xx、并发、成本日志、两种协议
      fixtures.py    确定性离线合成数据（--fixture 与单元测试用，永远不是真值）
      generate.py    场景族清单 → 最小对立对 case → question
      teacher.py     question → answer（每个来源一份文件）
      jev.py         官方 Jev 适配器骨架（prepare/run 两段式，未接入即报错）
      adjudicate.py  多源比对与裁决 → label / pending
      tests/         98 条离线 unittest，不联网、不花钱

## 1. 默认离线与三种模式

所有会联网的脚本都遵守同一开关：

- 默认（不加开关）：只写请求计划 JSONL，**不联网**；generate 还会写 plan.json。
- --live：真实调用。必须显式给出；密钥只从环境变量或 --key-file 读取。
- --fixture：离线确定性合成数据，跑通全链路用；来源名固定为 fixture，血缘 fixture。

真实付费调用只在任务明确批准时进行；本目录不提供任何自动放量入口。

## 2. 契约实现口径（字段名未改）

- **pair 元数据位置**（DATA-02 lead 追加，待同步进 datasets/pol2/README.md 第 3 节）：
  pair_id / variant / diff 放 case 顶层；quality_flag 与 generator_lineage 放 provenance。
  旧记录没有这些字段仍然合法（校验器把它们视为可选）。
- **answer 失败态**：execution_status != ok 时写 answer=null、不写 probs，保留
  latency_ms / created_at / execution_status；与 benchmark/PROTOCOL.md「非 ok 时 status=null、
  不提供概率」一致。**失败永远不写 ok**；失败记录会在下次重跑时重试。
- **概率**：answer.probs 与 label.probs 必须归一（容差 1e-3，覆盖 4 位小数舍入）。
  模型原始输出里的权重/计数按比例归一到 1（契约要求「归一到 1 的概率」），键不匹配则丢弃并
  在 answer.extra.notes 记录 probs_dropped，不伪造概率。
- **label.review_level** 只有 model_cross_checked / human_reviewed；model_cross_checked
  **不是金标准**，一致性来自多血缘教师，不是人工。

## 3. 外部接口（核实日期 2026-09-30）

生成（出题）：

| 角色 | provider | 协议 | 地址 | 密钥 | 模型 | 血缘 |
|---|---|---|---|---|---|---|
| 主 | sub | chat completions | https://sub.461561.xyz/v1/chat/completions | SUB_API_KEY | gpt-6-luna | openai-luna |
| 备 | opencode-go | chat completions | https://opencode.ai/zen/go/v1/chat/completions | OPENCODE_GO_API_KEY | deepseek-v4.1-flash | deepseek |

真值教师（三方交叉，血缘互不相同）：

| 角色 | provider | 协议 | 地址 | 密钥 | 模型 | 血缘 |
|---|---|---|---|---|---|---|
| A | sub | openai-responses | https://sub.461561.xyz/v1/responses | SUB_API_KEY | gpt-6.1-sol | openai-sol |
| B | sub-grok | openai-responses | https://sub.461561.xyz/v1/responses | SUB_GROK_API_KEY | grok-4.7 | xai-grok |
| C | opencode-go | chat completions | https://opencode.ai/zen/go/v1/chat/completions | OPENCODE_GO_API_KEY | mimo-v2.6-pro | xiaomi-mimo |
| D | 官方 Jev | 未核实 | 待用户提供 | JEV_API_KEY | jev-<version> | typesafe-jev |

请求形状：

- chat completions：{"model": ..., "messages": [...], "max_tokens": N}；回复取
  choices[0].message.content，content 为空时退回 reasoning_content。
- openai-responses：{"model": ..., "input": <string>, "max_output_tokens": N}；回复取
  output[].content[].text。
- opencode-go 路由必须带请求头 x-opencode-session: <UUID>（每进程一个），否则 400
  MissingSessionID。clients.py 已内置；GLM 旧路由 https://opencode.ai/zen/go/v1 仍保留在
  SOURCES 里（glm-5.3 / glm-5.3-flash），可用 --base-url 覆盖。
- **GLM baseURL 结论**：opencode-go 路由为 https://opencode.ai/zen/go/v1（Lead 实测 200，
  必带 session 头）。DSH 已装目录里没有 glm-5.3 条目，它由 profile 配置层追加，所以模型 id
  与地址都做成可配置常量（--model / --base-url），不把推断写死。
- **reasoning 坑**：mimo-v2.6-pro / glm-5.3 等会输出 reasoning_content，max_tokens 过小时
  content 会是 null。真值调用统一 max_tokens >= 1024（clients.py 自动抬到下限），并且
  content 与 reasoning_content 皆空记 execution_status=invalid，绝不当 ok。
- **User-Agent**：sub 网关（Cloudflare）会以 1010 Access denied 拒绝 urllib 默认 UA
  （Python-urllib/3.x）。clients.py 默认发产品 UA
  "PoL2-pipeline/0.1 (+https://github.com/naturaldao/NaturalDAO)"，可用 --user-agent 覆盖；
  这是客户端标识，不是绕过鉴权：403/401 一律照实记 error，不重试成 ok。
- **Jev**：官方请求/响应形状截至 2026-09-30 未核实。jev.py prepare 可离线生成请求包；
  run 必须同时给出 --endpoint、--api-version、密钥与 --integration-confirmed，缺任何一项
  直接退出码 2，并明确说明缺什么，绝不回落到其他答案源。任何缺字段/未知 qid/形状不符记
  execution_status=invalid。

## 4. 生成：最小对立对

generate.py 逐族生成**最小对立对**：同一情节骨架，只改一处关键事实，两条 case 共享 pair_id，
variant 为 a/b，diff 记录被改动的那一处（key_fact/a/b）。

    uv run --no-project --offline python datasets/pol2/pipeline/generate.py \
        --families datasets/pol2/families.pilot.jsonl --assign <仓库外分配表> \
        --out <新目录> --limit 6            # 默认离线：只写请求计划
    ... --live --concurrency 8              # 真实生成；并发上限按族
    ... --fixture                           # 离线合成数据跑通链路

- **判据来源**：issue 选项与 status/polarity/evidence/action 判据默认取自冻结本体
  datasets/pol2/ontology/pol2-labels.v0.1.json（15 个 issue slug）；--issue-keys-file 可指向
  新版本本体。运行 generate.py --check-ontology 可打印 issue 键对照与枚举一致性（退出码非 0
  表示与本体不一致）。本体是唯一判据来源，代码不另立清单。
- --limit N 是 case 数目标，按整对向上取整（N=5 → 3 对 6 条）。--family 可重复，
  --families-filter 支持逗号列表。--assign 用 splits.py 的分配表（family_id/region/…）；
  没有分配表时用 --region 指定单一分区。
- **private_holdout 一律拒绝**：该分区由独立保管者生成，写入仓库外目录；管线只处理
  train / public_test / validation（契约第 5 节）。
- 输出布局（--out 是新目录，或已有同配置 plan.json 的续跑目录）：

      plan.json                        固定计划与配置摘要（config 变了就拒绝写入）
      <region>.cases.jsonl             case（契约 3.1）
      <region>.questions.jsonl         question（契约 3.2）
      shards/<family>/batch-<k>.*.jsonl 按族分片、按批原子写（断点续跑的最小单位）
      shards/<family>.cases.jsonl      族合并
      qa/families.jsonl                族级质检汇总
      qa/<family>.coercions.jsonl      被强制的 surface/clause 取值（不静默）
      errors/<family>.errors.jsonl     失败批次（kind/error，不写 ok）
      requests/<family>.batch-<k>.request.jsonl   离线模式的请求计划
      calls.jsonl                      每次 HTTP 尝试：延迟、token、成本
      run.json                         运行汇总（可重复运行，原子重写）

- **不合格对的处理（不放宽判定）**：结构不完整、expected_status 不相反、只靠情绪/礼貌词区分
  （shortcut_risk）、骨架差太远（weak_pair）、context 结构不一致的对，会带失败原因回灌到下一次
  提示里重生成（--pair-attempts，默认 3 次）；仍不合格就**丢弃并计数**（qa/families.jsonl 的
  dropped_pairs / drop_reasons），绝不带着质量标记留在数据集里。整体材料完全重复的对直接丢弃并
  计数，不再花调用重生成。
- **结构化输出**：sub 路由实测支持 response_format={"type":"json_object"}（2026-09-30），
  generate.py --response-format json_object 可显著降低解析失败；--max-tokens 建议 16384，
  因为 reasoning 会吃掉 8192 预算并导致截断/空 content。解析仍然坚持"必须取出结构"，不做
  宽松兜底。
- **断点续跑**：批次有 batch-<k>.done.json 标记且三件产物齐全即跳过；失败批次不写文件、不留
  标记，重跑只补失败部分（丢弃与重生成计数写在标记里）。
  配置（族清单哈希、limit、seed、模板版本…）变化时拒绝复用同一 --out，请换新目录。
- **幂等 id**：pol2-<region>-<6 位序号> 按族 id 排序后在分区内连续分配；
  pair_id 为 pol2-<region>-p<6 位序号>。改变 --limit/族集合会改变编号 → 换新 --out。

### 族级质检（qa/families.jsonl）

- 三类覆盖：明显合规 / 明显违规 / 证据不足，缺任一类 → incomplete=true（整族标记）。
- 对质检：expected_status 必须不同（否则 status_conflict）；**整体材料（context + target）**
  相似度低于阈值（--similarity-threshold，默认 0.4）记 weak_pair；两侧 surface 或 context
  条数不一致记 structure_mismatch；差异只落在情绪/礼貌词表内记 shortcut_risk。
  关键事实差异允许落在 context（例如"已明确撤回"vs"仍然有效"），此时两条 target 相同，
  QA 记 target_identical=true 但不是缺陷；只比较 target 会把这类合法的 context-only 对
  误判成重复或捷径（首版实现踩过，见 --recheck）。
- 去重：批内与族内**整体材料**完全一致才记 duplicate_case（context+target 的整体哈希），
  并汇总 duplicate_case_cases；重复不静默通过。
- --recheck：QA 规则修正后，离线重算已有分片的质量标记与派生文件（不调用模型、不重付费）。
  命令：generate.py --recheck --out <已有目录> [--similarity-threshold F]
- expected_status 只存在于质检文件与 answer 分析里，**不进 question.prompt**，教师看不到。

## 5. 取答案：teacher.py

    uv run --no-project --offline python datasets/pol2/pipeline/teacher.py \
        --questions <region>.questions.jsonl --out-dir <目录> --region train \
        --source gpt-6.1-sol --keys status,action,polarity,evidence --concurrency 8

- 输出 <region>.answers.<source>.jsonl（契约 3.3），一个来源一份，永不覆盖其他来源。
- --source 取 SOURCES 里的名字（luna / deepseek-v4.1-flash / gpt-6.1-sol / grok-4.7 /
  mimo-v2.6-pro / glm-5.3 / glm-5.3-flash），fixture 模式用 --source fixture。
- 已 ok 的 qid 跳过；非 ok 会在重跑时重试，最终文件按 question 顺序原子压缩为每 qid 一条，
  历史尝试保留在 calls.<source>.jsonl。观测到的 model/usage/模板版本写进 answer.extra。
- 原始响应默认不落盘；--save-raw 才写 raw，且只有许可允许公开时才能提交。

## 6. 裁决：adjudicate.py

    uv run --no-project --offline python datasets/pol2/pipeline/adjudicate.py \
        --cases <region>.cases.jsonl --questions <region>.questions.jsonl \
        --answers <region>.answers.gpt-6.1-sol.jsonl \
        --answers <region>.answers.grok-4.7.jsonl --out <目录> --region train

规则（SPEC「不把同源教师一致当真值」+ DATA-02 lead 追加约束）：

1. 至少 --min-lineages（默认 2）个**不同血缘**逐题一致才采纳；血缘按模型家族算
   （glm-5.3 与 glm-5.3-flash 同族）。同族多源一致只记 same_family_only。
2. 生成该 case 的血缘 provenance.generator_lineage 必须从教师池剔除；缺该字段直接 pending。
3. **Luna 与 fixture 默认整体排除**（--exclude-lineage，默认 openai-luna,luna,fixture），
   只作出题模型自评分析，永不参与 label。
4. 未映射来源（不在 SOURCES、也没有 --lineage source=lineage）记为 unmapped_sources，
   不能提供独立性；需要时用 --lineage 显式声明。
5. 分歧、同血缘一致、缺答案、内部矛盾（violating 却无 issue、conforming 却有 issue、
   violating+证据不足、violating+polarity=love 等）一律不产 label。
6. --allow-majority 才允许不同血缘的多数票（默认关，采纳时 review.agreement=majority 并
   在 disagreements 记录少数派）。--allow-missing-issues 才允许 issue 题缺答案不阻塞。
7. label 字段按契约 3.4；citations 取 case 条款（--families 可补全族条款）；
   acceptable_actions 用协议五动作，非空；review.sources/agreement/disagreements/
   adjudicated_by 记录全部依据。人工结果用 --human-labels 覆盖并标 human_reviewed。

输出：<region>.labels.jsonl、<region>.pending.jsonl（原因、逐题取值与血缘、分歧）、
adjudication.<region>.json（计数、未映射来源、血缘使用、review_level 分布）。pending 文件是
辅助文件，不属于契约四类记录。

## 7. 成本与日志

每次 HTTP 尝试一条 jsonl：ts / provider / model / base_url / attempt / ok / status_code /
latency_ms / error / prompt_tokens / completion_tokens / total_tokens / cost_usd /
request_sha256 / key_fingerprint。密钥只记 sha256 前 8 位指纹，绝不落盘明文；run.json 与
stdout 汇总给出 calls / ok / failed / tokens / cost / p50 / p95。价格用 --price-in /
--price-out（每百万 token）显式给出才计成本。

## 8. 数据边界

- 不写 private_holdout；不复制仓库外的分配表进仓库（生成只需读它）。
- 不提交密钥、凭据或原始响应；--key-file 可指向 DSH credentials.yaml（只读 refs 段）。
- 教师输入只有 question.prompt（自包含），不含 pair_id、expected_status、质量标记或参考答案。

## 9. 测试

    uv run --no-project --offline python -m unittest discover -s datasets/pol2/pipeline -p "test_*.py" -q

98 条用例全部离线：契约校验、概率归一、问题派生、解析容错、重试与 429、成本日志、
断点续跑、失败不写 ok、缺 id 处理、去重与配对质检、血缘剔除与人工覆盖、Jev 拒绝降级。

## 10. 冒烟与试点状态（2026-09-30）

- **已完成的真实冒烟**（唯一一次付费调用，命令与证据在 smoke/luna-limit5/）：

      uv run --no-project --offline python datasets/pol2/pipeline/generate.py \
          --families datasets/pol2/families.pilot.jsonl \
          --assign <仓库外分配表> --family autonomy_paternalism.evidence_insufficiency \
          --limit 5 --live --workers 1 --key-file <DSH credentials.yaml> \
          --out datasets/pol2/pipeline/smoke/luna-limit5

  结果：1 次有效调用（另一次同命令被 Cloudflare 1010 拒绝、0 token 消耗），
  prompt 4820 + completion 1547 = 6367 tokens，延迟 53.4s，产出 6 条 case / 3 组最小对立对，
  三类覆盖齐全（conforming 3 / violating 2 / insufficient 1），QA 无 shortcut_risk、
  无重复、无 weak_pair（3 组为 context-only，target_identical=true）。
- **离线全链路**：smoke/fixture-e2e/ 用 --fixture 跑完 generate → teacher（两个 fixture 来源）
  → adjudicate，labels + pending 均按预期产出（合成数据不是真值）。
- **未做**：教师模型（gpt-6.1-sol / grok-4.7 / mimo-v2.6-pro）的真实调用、17 族放量、
  官方 Jev 接入、人工复核。放量前需 Lead 另行批准。
- **Jev**：官方请求/响应形状未核实，run 会明确拒绝执行（详见第 3 节）。

## 11. 试点实测指标与放量预算（2026-09-30）

配置：--live --workers 8 --pairs-per-batch 3 --pair-attempts 3 --max-attempts 4
--response-format json_object --max-tokens 16384；两族 train 共 224 条 case。
产出目录：smoke/luna-pilot-2families/（含逐条分析 analysis.md）。

| 放量门槛 | 要求 | 实测 | 结论 |
|---|---|---|---|
| 解析失败率（含重试后） | < 5% | 0%（json_object 时代 49 次尝试中 invalid=0） | 达标 |
| 尝试失败率（网络瞬断） | — | 12.2%（5 次 SSL EOF + 1 次 524） | 由 4 次尝试上限吸收，超限批次留待续跑 |
| duplicate_case 率 | < 1% | 0.00%（族内与跨族精确重复均为 0） | 达标 |
| shortcut_risk | 0 | 0（另有 4 个 slot 触发重生成后合格） | 达标 |
| 每族三类齐备 | 是 | 是：46/41/25 与 53/36/23（conforming/violating/insufficient） | 达标 |
| 组内 status 相反 | 是 | 112/112 组（64 组 conforming↔violating，35 组 conforming↔insufficient，13 组 insufficient↔violating） | 达标 |
| 丢弃 | 记录并计数 | 0 组丢弃 | — |

产出规模与成本（json_object 时代实测）：

- 成功调用均值：prompt 4,813 tokens、completion 1,286 tokens，单次延迟 p50 25.3s（max 111.5s）。
- 每千条 case：约 190 次调用，约 0.91M prompt + 0.24M completion tokens（约 1.16M tokens）。
- 全量 96 族 10,904 条：约 2,071 次调用，约 10.0M prompt + 2.7M completion tokens；
  并发 8 约 1.8 小时；按 12% 尝试失败率预计约 250 次失败尝试由重试吸收。
- cost_usd：sub 路由不返回价格，调用日志与 run.json 写 null（不编造数字）；拿到价格后用
  --price-in/--price-out 即可自动计算。
- 历史对照：换用 json_object 之前，两族 107 次尝试中 16 次失败（15%），其中 15 次是
  "no parseable JSON"；改结构化输出 + max_tokens 16384 后解析失败归零。
