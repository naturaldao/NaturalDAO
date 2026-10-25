# NaturalDAO PoL Gate — 软件工程设计

> 本文档面向**初次接触本系统的工程师**，目标是让你在阅读后能回答三个问题：
> 1. 这个系统由哪些部分组成，各自为什么存在
> 2. 一次请求从进入到返回，数据经过了什么
> 3. 哪些约束是不可违反的红线，改代码时容易踩哪些坑
>
> 编写基线：2026-10-21，对应代码状态 `apps/gate-service` 402 项测试通过、`apps/pol-proxy` 13 项通过、6 容器全部 healthy。
> 本文档描述**代码实际行为**，不以需求文档为准；当两者冲突时以本文档标注的「实现现状」为准。

---

## 1. 系统定位

### 1.1 它解决什么问题

大模型会给出违反特定伦理理论的内容。本项目把 NaturalDAO 的 **PoL2（爱2证明）** 伦理框架变成一道可执行的**双向门禁**：

```
用户请求 ──▶ [请求审核] ──allow──▶ [目标模型生成] ──▶ [回答审核] ──allow──▶ 展示给用户
                 │deny                                      │deny
                 ▼                                          ▼
              直接拒绝（目标模型从未被调用）              拒绝（原文永不外泄）
```

两条不可违反的顺序约束：

- **请求审核在生成之前** —— 被拒的请求**永远触达不到**目标模型
- **回答审核在返回之前** —— 未通过审核的模型输出**永远不出当前进程**

这不是"内容过滤"，而是**理论一致性审核**：判断必须依据从 PoL2 理论原文中检索到的证据，模型被禁止凭空引用。

### 1.2 它不是

- 不是通用内容审核 / 敏感词过滤（判据是可引用的理论条文）
- 不是模型微调或对齐训练（是推理期门禁）
- 不是缓存代理（缓存命中仍返回**曾经通过双审**的答案）

---

## 2. 组件拓扑

### 2.1 六个容器

```
                       ┌─────────────────────────────────────────┐
   浏览器 :3100 ──────▶ │  web  (Next.js 16)                      │
                       │  唯一对外端口 · 无审核逻辑 · 纯 UI + 代理  │
                       └───────────────┬─────────────────────────┘
                                       │ http://gate-service:8080
   Hermes / OpenAI 客户端              │
   （可选，需显式开端口）              │
        ┌──────────────────┐          │
        │ pol-proxy :8081  │──────────┤
        │ OpenAI 协议翻译层 │          │
        └──────────────────┘          │
                                       ▼
                       ┌─────────────────────────────────────────┐
                       │  gate-service :8080                     │
                       │  唯一的审核者 · 唯一持有模型凭据          │
                       │  唯一有外网出口                          │
                       └──┬──────────┬───────────┬───────────────┘
                          │          │           │
              ┌───────────▼──┐  ┌────▼──────┐  ┌─▼──────────────┐
              │ openviking   │  │ vector-db │  │ embedding-svc  │
              │ :1933        │  │ :5432     │  │ :18080         │
              │ 理论库(只读)  │  │ pgvector  │  │ bge-small-zh   │
              └──────────────┘  └───────────┘  └────────────────┘
```

| 容器 | 镜像 | 职责 | 对外端口 |
|---|---|---|---|
| `web` | Next.js 16 | 聊天 UI + `/api/chat` 服务端代理 | **3100**（唯一） |
| `gate-service` | Node 22 + tsx | 审核编排、理论检索、记忆管理 | 无（仅内网） |
| `openviking` | ghcr.io/volcengine/openviking | 理论原文分片存储 + 语义检索 | 无 |
| `vector-db` | pgvector/pgvector:pg17 | 问答记忆 + 会话轮次（同一 PG 实例，两张表） | 无 |
| `embedding-service` | 自建 Python | bge-small-zh-v1.5 中文嵌入（512 维） | 无 |
| `pol-proxy` | Node 22 + tsx | OpenAI 协议 ⇄ gate 协议翻译 | 无（需显式 `POL_PROXY_PORT`） |

### 2.2 为什么是六个容器

**D1 — embedding-service 必须自建**：OpenViking v0.5.0 的官方镜像缺少 `llama-cpp-python`，内置本地嵌入不可用。向量空间改由独立容器提供，这也让嵌入模型可以独立升级。

**D2 — 双库物理隔离**：理论原文只进 OpenViking，问答记忆只进 pgvector。**禁止双写**。理由见 §4.3。

**D3 — pol-proxy 独立进程**：协议翻译是无状态纯函数，与审核逻辑无关。独立成容器后可以按需开关，且不污染 gate 的安全边界（proxy 不持有任何凭据）。

### 2.3 网络与信任边界

```
pol-internal (bridge)  ── 所有服务都在这里
       │
       └── 只有 web 映射宿主端口；其余服务的隔离靠"省略 ports:"

信任分级：
  gate-service  = 持有 DeepSeek 凭据 + 有外网出口  ← 最高敏感
  pol-proxy     = 无凭据、无 DB、无模型调用        ← 低危，但无鉴权
  web           = 无凭据，仅转发到内网 gate
```

> ⚠️ **pol-proxy 没有鉴权**。默认不映射宿主端口；一旦用 `POL_PROXY_PORT` 开放，任何能访问该端口的人都能绕过认证消耗你的模型配额。只在受信网络内开放。

---

## 3. 分层架构

### 3.1 模块职责（`apps/gate-service/src`，约 6,500 行）

```
http/          路由、限流、参数校验、健康检查         ← 唯一接受用户输入的地方
  ├ app.ts       Fastify 应用 + zod schema
  ├ health.ts    分级健康（ready/degraded/not_ready）
  └ ratelimit.ts 滑动窗口限流

pipeline/      编排：把下面所有能力串成一次请求        ← 业务主干
  └ chat.ts      runPipeline()：12 步流程，约 890 行

gate/          审核能力本身
  ├ prompts.ts   所有 prompt 构造（审核/摘要/改写/相关性）
  ├ review.ts    reviewRequest / reviewResponse
  ├ evidence.ts  引文真实性校验（必须能对上真实分片）
  └ schemas.ts   结构化输出 zod schema

theory/        理论库接入
  ├ sync.ts      幂等导入（启动时灌 OpenViking）
  ├ loader.ts    语料加载 + manifest 哈希
  ├ chunker.ts   父-子分片
  └ evidence.ts  证据筛选（丢弃目录占位节点）

memory/        问答记忆与缓存
  ├ cache.ts          CacheOrchestrator：lookup + 后台刷新
  ├ applicability.ts  意图等价判定（防相似误命中）
  ├ policy.ts         是否入库的决策
  └ intent.ts         意图键归一化

context/       会话上下文（可选，web 用）
  ├ index.ts      loadSessionWindow()：单点组装
  ├ store.ts      pol_session_turn 读写
  ├ summarize.ts  超阈值摘要（失败降级为截断）
  └ rewrite.ts    指代消解（仅改检索查询）

clients/       外部调用
  ├ model.ts     OpenAI 兼容模型客户端（角色独立配置）
  ├ embedding.ts 嵌入客户端
  ├ http.ts      统一 HTTP + 超时 + 错误分类
  └ usage.ts     请求级 token 账本（AsyncLocalStorage）

adapters/      存储适配器
  ├ openviking.ts  OV HTTP 适配（唯一知道 OV 接口的地方）
  ├ pgvector.ts    pgvector 适配
  └ types.ts       适配器接口定义

runtime/       进程级状态（user key 持久化）
```

### 3.2 依赖方向（不可逆）

```
http → pipeline → { gate, theory, memory, context } → { clients, adapters }
```

**反向依赖是设计错误**。例如 `gate/` 不允许 import `pipeline/`，`adapters/` 不允许 import 业务模块。

### 3.3 `apps/pol-proxy/src`（约 456 行）

```
translate.ts   纯函数：OpenAI ⇄ gate 协议映射（无网络、无状态）
server.ts      Fastify 路由 + 状态码策略（只判"是否传输故障"）
index.ts       env → listen
```

proxy 中**不允许出现任何审核逻辑**。想加"拦截某词""改写答案"，那是 gate 的职责。

---

## 4. 存储设计

### 4.1 三套存储的职责

| 存储 | 物理位置 | 存什么 | 谁写 |
|---|---|---|---|
| **OpenViking** | `ov-data` 卷 | PoL2 理论原文分片 + 索引 | 仅启动时 `theory/sync.ts` |
| **`pol_memory`** | `pg-data` 卷（PG 表） | 已通过双审的问答对 + 512 维向量 | `pipeline/chat.ts` 步骤 8 |
| **`pol_session_turn`** | 同一个 PG 实例，另一张表 | 会话轮次 | `pipeline/chat.ts` `finish()` |

**实测数据量**：理论 69 个 chunk；`pol_memory` 33 行。

### 4.2 `pol_memory` 结构要点

```sql
question_embedding  vector(512)        -- bge-small-zh-v1.5
intent_key          text               -- 意图归一化键
status              text               -- active / superseded
```

关键索引：

```sql
hnsw (question_embedding vector_cosine_ops) WHERE status='active'   -- 向量近邻
UNIQUE btree (intent_key) WHERE status='active'                     -- 同意图只留一条活记录
```

第二条保证新答案**取代**旧答案而非并存：旧行变 `superseded`，不删除（保留审计）。

### 4.3 为什么禁止双写（D2）

理论原文与问答记忆的**失效模式完全不同**：

- 理论库丢了 → 全量重新导入即可（语料在 git 里）
- 问答库丢了 → 只丢缓存，不影响正确性

混在一起会导致"重新导入理论时把用户问答一起清掉"，或"清理过期问答时误删理论条文"。

### 4.4 会话上下文与无状态模式的分离

`pol_session_turn` 只在**有状态模式**下使用。当调用方（如 Hermes）自带完整上下文时（`messages` 入参），gate 走**无状态路径**：

- 不读、不写 `pol_session_turn`
- 不查语义缓存、不写 `pol_memory`
- 历史来自调用方，`maxContextChars` 仍然生效

两条路径互斥（`messages` 与 `conversation_id` 不能同时传，否则 400）。

---

## 5. 一次请求的完整数据流

### 5.1 主链路（12 步）

```
入口：POST /api/v1/chat  {message, conversation_id? | messages?}

 1. 长度校验            超 maxRequestChars → 400，不触碰任何存储
 2. 取会话窗口          有状态：读 pol_session_turn；无状态：跳过
 3. （可选）指代改写    仅当历史可能影响检索时调模型
 4. 理论检索            查 OpenViking，selectEvidence 过滤占位节点
 5. 请求审核            gate 模型 + 理论证据 [+ 历史块]
 6. deny/uncertain?     → 直接拒绝，目标模型从未被调用
 7. 生成答案            target 模型
 8. 回答审核            gate 模型 + 理论证据（含引文真实性校验）
 9. 未通过?             有限次修复（带审核意见重生成），仍不过则拒绝
10. 相关性分类          独立判定 theory_relevance
11. 记忆写入            条件入库到 pol_memory
12. 写会话轮次          finish() 单点出口，一次请求恰好一条
```

### 5.2 哪些数据进入了哪次模型调用

| 调用 | 输入 | 说明 |
|---|---|---|
| 指代改写 | 历史 + 当前问题 | **只改检索查询**，审核器始终看原话 |
| 请求审核 | 原话 + 8 条理论证据 + 历史块 | 历史被标注"不得作为放行依据" |
| 生成 | 系统提示 + 历史 + 证据（有状态）/ 调用方原文 + 证据（无状态） | |
| 回答审核 | 原话 + 答案 + 8 条证据 | 有状态路径**不带**历史 |
| 相关性 | 原话 + 答案 | 独立分类，不是副产品 |

### 5.3 token 计量

采用**请求级账本**（`clients/usage.ts`，基于 `AsyncLocalStorage`）：

```
一次请求可能触发 4 次以上模型调用，分布在不同模块。
账本绑定异步上下文 → 模型客户端 chat() 自动记账 → 新增调用点无需改任何业务代码。
```

响应字段 `usage: {prompt_tokens, completion_tokens, total_tokens, calls}` 覆盖**整轮所有调用**，不只是一次生成。

> 实测：理论相关的完整链路约 11k–27k tokens；语义缓存命中约 0.8k–1.2k。

---

## 6. 关键机制

### 6.1 证据筛选（`theory/evidence.ts`）

OpenViking 会为每个目录生成 `.abstract.md` / `.overview.md` **占位节点**，内容恒为 `[Directory overview is not ready]`，且**排序分数高于真实正文**（实测占位 0.706–0.719 vs 正文 0.684–0.704）。

只取 `topK=8` 条时，窗口会被占位节点占满，正文完全挤不进来 —— 表现为"审核器给出了理论判定，但 UI 显示未命中理论库"。

**修复**：请求 `candidatePool=24` 条候选，过滤 `level < 2` 的目录节点后再截取 topK。

> ⚠️ **不要试图用相似度阈值解决这个问题**。实测 OpenViking 分数跨问题不可比：无关问题「1+1等于几」在 0.3–0.7 各阈值下都稳定返回 16 条；而配置的 `minSimilarity=0.82` 会让相关提问只剩 1 条证据。

### 6.2 引文真实性校验（`gate/evidence.ts`）

回答审核要求模型引用理论证据，且：

1. `knowledge_id` 必须存在于**本次请求真实检索到**的分片中
2. `quote` 必须是该分片中的**原文连续片段**（允许省略号分段，回退到 token 重叠度检查）

引用真实 id 但编造引文，与编造 id 同等处理 —— 都是拒绝。

### 6.3 语义缓存不绕过审核

缓存命中返回的答案**曾经通过过双审**，且必须满足：

- `status='active'`
- `policy_version` 与当前理论版本兼容
- **意图等价判定通过**（`memory/applicability.ts`）

第三条是关键：向量相似 ≠ 同一个问题。「什么是爱2」和「什么是野蛮2」语义空间很近但答案相反。所以命中后还要让模型判一次"这两个问题是不是真的同一个意图"。

### 6.4 fail-closed 分级

| 依赖失效 | 行为 |
|---|---|
| 语义缓存 | 降级为无缓存路径，**不影响正确性** |
| 会话表 | 降级为"无上下文"，请求照常 |
| 摘要模型 | 降级为截断，保留最近 N 轮 |
| 指代改写 | 回退原问题 |
| **理论检索** | **硬失败** → `OPENVIKING_UNAVAILABLE`（失去证据就无法合规审核） |
| **审核模型** | **硬失败** → 拒绝 |

原则：**能降级的是优化项，不能降级的是安全判据**。

---

## 7. 对外接口

### 7.1 web（对外唯一端口）

```
POST /api/chat  {message, conversation_id?}
  → 转发到 gate-service，响应原样透传
```

### 7.2 gate-service（仅内网）

```
POST /api/v1/chat
  {message, conversation_id?}      有状态：gate 管历史
  {message, messages[]}            无状态：调用方管历史（互斥）

GET  /health                       分级健康
GET  /internal/v1/...              管理接口（需 X-Admin-Token）
```

响应关键字段：

```json
{
  "status": "completed|rejected|error",
  "answer": "...",
  "reason_code": "THEORY_CONFLICT",
  "cache": {"hit": false},
  "usage": {"total_tokens": 27128, "calls": 4},
  "theory_hit": true,
  "theory_raw": 17
}
```

`theory_hit` / `theory_raw` 的区别：

| `theory_hit` | `theory_raw` | 含义 |
|---|---|---|
| `false` | `0` | 没检索到，或根本没检索（缓存命中） |
| `false` | `>0` | **OpenViking 有响应，但全是目录占位节点** |
| `true` | `>0` | 正常命中 |

### 7.3 pol-proxy（OpenAI 兼容）

```
POST /v1/chat/completions    OpenAI 格式，stream 支持（单 SSE chunk）
GET  /v1/models
GET  /health
```

**状态码策略**（关键设计）：

| gate 结果 | proxy 返回 |
|---|---|
| 完成 | 200 + `finish_reason: stop` |
| 拒绝 | **200** + `finish_reason: content_filter` |
| gate 不可达 | 502 + OpenAI 错误格式 |

拒绝必须是 200：OpenAI 客户端（含 Hermes）遇到非 200 会当成**传输故障**并重试，用户反而看不到拒绝理由。门禁拒绝是**业务结论**，不是故障。

---

## 8. 红线（改代码前必读）

1. **deny 永不触达目标模型** —— 任何重构都不能把生成提前到请求审核之前
2. **未审核文本永不返回** —— 回答审核必须在任何 return 之前
3. **只有 gate 持有模型凭据** —— proxy、web 不得引入 API key
4. **推理逻辑不进 proxy** —— proxy 只做形状转换
5. **理论库与问答库禁止双写**
6. **`maxContextChars` 是硬上限** —— 按渲染后真实长度校验，不是估算
7. **角色必须交替** —— 生成侧绝不允许连续两条相同 role（实测会导致上游断连）
8. **prompt 缓存不可破坏** —— 不要在同一会话中途改 system prompt 或工具集

---

## 9. 已知问题与技术债

### 9.1 未完成：无状态模式 + 调用方 system prompt（**当前阻塞项**）

**现象**：通过 pol-proxy 传入含 system 的上下文时，返回 `GATE_OUTPUT_INVALID`；去掉 system 则正常。

**根因**（已实测确认）：`buildContextBlock` 把调用方 system 折成 `【系统提示】…`，`buildRequestReviewPrompt` 把它放进审核器**自己的 system role**。模型把那段文字当成自身指令（如"回答要简洁"），破坏了 JSON 输出格式。

**影响**：Hermes 实际会发送大段 system（工具定义、行为约束），因此该路径**当前不可用**。

**修复方向**（需产品决策）：
- A：历史块从审核器 system 移到 user prompt（彻底隔离，但触及 AC1 逐字节一致红线）
- B：system 作为"调用方运行指令"单独送审，审核器显式评估该指令是否违规（可堵住 system 注入绕过门禁）

### 9.2 无关问题成本偏高

`theory_relevance` 由请求审核自身产出，而审核必须先拿到证据才能判"无关"。因此**无关问题也会走完整链路**：

| 请求 | 模型调用 | tokens |
|---|---|---|
| 无关问题（天气、算术） | 3–4 次 | 8k–13k |
| 理论相关完整链路 | 4 次 | 11k–27k |

缓解：`MAX_EVIDENCE_CHUNK_CHARS=1200` 对单条证据正文做渲染截断。

### 9.3 其他

- `hermes-integration.md` 仍描述旧版 conversation_id 行为，待更新
- pol-proxy 无鉴权
- 无状态路径的语义缓存被禁用（跨客户端不安全），因此 Hermes 侧没有缓存收益

---

## 10. 开发与验证

```bash
# 单元测试（不连数据库、不连模型）
cd apps/gate-service && npx vitest run      # 402 passed
cd apps/pol-proxy   && npx vitest run      # 13 passed

# 类型与风格
npx tsc --noEmit && npx eslint .

# 起服务（需要 .env）
cd /root/pol && docker compose up -d

# 端到端
curl -X POST http://127.0.0.1:3100/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"什么是野蛮2？"}'
```

**测试分层原则**：
- 单元测试用 stub 模型，断言"模型收到了什么"而非"模型说了什么"
- 集成测试允许 skip（需要真实依赖）
- 端到端必须手工跑通一次 —— 因为 stub 无法反映真实模型被 prompt 干扰的行为（§9.1 就是这么漏掉的）

---

## 11. 术语表

| 术语 | 含义 |
|---|---|
| **PoL2 / 爱2证明** | NaturalDAO 的伦理理论框架，本系统的判据来源 |
| **爱2 / 恨2** | 理论中的核心概念：扬爱抑恨 |
| **野蛮2** | 任何对生命、尊严、自由、精神、人类生态造成伤害/压迫/剥夺的行为 |
| **请求审核 / 回答审核** | 两道门禁，都依据检索到的理论证据 |
| **fail-closed** | 无法判断时拒绝，而非放行 |
| **theory_hit / theory_raw** | 是否取得可用证据 / 检索返回的原始条数 |
| **有状态 / 无状态** | 历史存在 gate 的 PG 表 / 历史由调用方随请求带来 |

---

## 附录：与既有文档的关系

| 文档 | 定位 |
|---|---|
| **本文档** | 面向新人的完整工程视图，反映**当前代码状态** |
| `architecture.md` | 需求驱动的设计决策记录（含 D1–D6 决策依据） |
| `ARCHITECTURE_TECH_STACK.md` | 技术栈视角，分层与框架机制细节 |
| `api.md` | 接口契约权威说明（字段级） |
| `hermes-integration.md` | Hermes 接入指南（**含待更新的旧行为**） |
| `PM_SPEC_*.md` | 各阶段需求规格 |
