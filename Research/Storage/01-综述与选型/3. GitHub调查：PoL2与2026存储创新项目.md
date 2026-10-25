# 调查报告

**调查时间**：2026-10-10（GitHub REST API v3，未认证；star 数、创建日期均为 API 返回值） **调查人**：AI 助手 **调查目标**：

1. 找出使用《PoL2存储技术选型建议.md》的 AI 类项目；
2. 搜集并简介 2026 年新创建的、有存储技术创新的 AI 类项目。

---

# 第一部分：有没有项目在用《PoL2存储技术选型建议.md》

## 结论：没有，而且不可能有

该文档是本会话在 **2026-10-10** 生成于本地工作目录 `/root/dd/PoL2存储技术选型建议.md`，**从未推送到任何 Git 仓库、也未发布到任何网站**。在它被公开之前，任何 GitHub 项目都不可能引用它。

## 验证过程与证据

|检索|方式|结果|
|---|---|---|
|`PoL2 in:name,description,readme`|Repo 搜索|379 条，**全部无关**——绝大多数是生物学里的 `pol2`（DNA 聚合酶 II），如 `mdozmorov/HiC_tools`|
|`"Proof of Love2"`|Repo 搜索|**1 条**：`naturaldao/NaturalDAO`|
|`"爱2证明"`|Repo 搜索|**1 条**：同一个 `naturaldao/NaturalDAO`|
|`topic:proof-of-love`|Repo 搜索|**4 条**，全部属于同一生态（见下）|
|文件名 / 标题精确匹配|Repo 搜索 + Web 搜索|**无任何命中**（repo 搜索不覆盖文件名；GitHub **Code Search API 需要鉴权**，未认证返回 HTTP 401，这是本次调查的方法学缺口）|

**方法学局限（须说明）**：我无法执行 GitHub 的代码级搜索（`/search/code` 需要 token），因此"某个仓库的某个文件里引用了本文件名"这一最强验证做不了。但 Repo 搜索覆盖仓库名、描述与 README 正文，Web 搜索覆盖公开网页；两者均无命中，且文档本身从未发布，结论可靠。

## 但有意外发现：PoL2 生态确实在 GitHub 上，而且就在做治理层

搜索 `"Proof of Love2"` 与 `爱2证明` 命中的是同一个仓库，它才是你这个项目的真实对应物：

### `naturaldao/NaturalDAO`（4★，创建于 2026-03-19，Python，CC0-1.0，最近推送 2026-10-11）

> NaturalDAO is a system built on the consensus **Proof of Love2** and driven by two core technologies—Smart Contract and artificial intelligence. It represents the governance and application layer for the PoL2 Civilization. It will be an ASI! 自然道是个基于"爱2证明"共识机制，并由智能合约和人工智能两大核心技术驱动的系统。

其架构自述为五层：公链 → 爱的证明治理共识层 → 智能合约 → 大语言模型 → AI Agents & Skills。

**重点：它的 `PoL-Governance/` 目录已经是一个可运行的运行时治理层工程**（SPEC.md 明确写"对用户输入、助手输出和工具行动做低成本判定与约束"），含 774 个文件，其中与存储/数据最相关的是：

|路径|内容|与我的选型建议的关系|
|---|---|---|
|`PoL-Governance/datasets/pol2/replay/`|`audit.py`、`audit-2026-09-30.json`、`replay_pool.md`、`survey.md`、`fixtures/audit/`|✅ **已具备"重放/审计"机制**——对应我建议的第 3 条（决策可复算）|
|`PoL-Governance/datasets/pol2/ontology/`|`pol2-labels.v0.1.json`、`JUDGE.md`、`check_ontology.py`、`clause-remap.md`、`test-matrix.md`|⚠️ **词库的雏形，但只是 JSON 标签表，没有检索索引**|
|`PoL-Governance/datasets/pol2/pipeline/`|`jev.py`、`adjudicate.py`、`teacher.py`、`prompts.py`、`clients.py`，以及带 `*.evidence_insufficiency.*` 命名的 shard|⚠️ 有"证据不足"这一维度，但证据库是文件集合，不是可检索存储|
|`PoL-Governance/benchmark/`、`models/`、`results/`、`integrations/`、`tools/`|数据划分（70/20/5/5）、模型清单、评估工具|—|

**关键缺口：整个仓库没有任何向量索引、嵌入库、KV 缓存、检索引擎。** 我对 774 个路径做了 `vector|embed|index|knowledge|rag|retriev|chroma|faiss|milvus|qdrant|sqlite|duckdb|redis|database|storage|memory|cache|corpus|lexicon|wiki` 的全量匹配，命中项全部是假阳性（如 `coverage.py` 里的 "rag"、`fig_fragility` 里的 "rag"）。**换句话说：PoL2 治理层已经建起来了，但我推荐的检索存储层完全空缺——不是"已被采用"，而是"尚未实现"。**

### 同生态的其他仓库（都很小，说明项目处于早期）

|仓库|★|创建|说明|
|---|---|---|---|
|`naturaldao/EAP`|5|2026-02-09|Ethical Alignment Protocol，自述为"LLM 的治理与执行层、PoL 文明的 operating system"。**但全仓库 24 个条目、全部是 Markdown 理论文档**（爱语治理官、操作性定义、伦理对齐协议…），**零代码、零存储实现**|
|`DAism2019/Proof-of-Love`|2|2025-08-07|爱之证明共识的理论论文仓库|
|`DAism2019/PoL-Civil`|0|2025-05-13|Proof of Love: The Consensus of Next Civilization|

---

# 第二部分：2026 年新创建、有存储技术创新的 AI 类项目

**筛选口径**：`created:>=2026-01-01`，从 20+ 条检索式中取回 356 个去重仓库，再按"是否在**存储层**（介质分层、索引结构、数据表示、持久化抽象、压缩、缓存）有实质创新"人工筛选，剔除仅"使用了某个向量库"的应用类项目。以下按创新类型分组。

## A. KV Cache 的 SSD 分层与卸载 —— 与你的场景最直接相关

这是我的选型建议的核心方向，2026 年出现了几个非常对口的独立实现：

|项目|★|创建|存储创新|
|---|---|---|---|
|[MIKAZE3/eugr-spark-vllm-mods](https://github.com/MIKAZE3/eugr-spark-vllm-mods)|2|2026-08-27|**GPU↔SSD 直连 KV 卸载**：用 cuFile（GPUDirect Storage）经 `vllm/v1/kv_offload/gds/` 绕开 CPU 主层，长上下文回放相对全量重算 **51×/118×/163×**（P128/P512/P800）。配套 cuFile pool、LRU 句柄缓存、三级注册回退|
|[focalcrest/vllm-marconi-offload](https://github.com/focalcrest/vllm-marconi-offload)|2|2026-05-24|**对 stock vLLM 的两级 KV 卸载**：L1 为 pinned/mmap CPU 池（`/dev/shm`，微秒级），L2 为 NVMe 上的 mmap 池（毫秒级、跨重启存活）；驱逐沿用 NSDI'25 Marconi 的 `reuse_count × exp(−decay×age)/(depth+1)` 评分，让热共享前缀比 LRU 冷尾活得更久|
|[smartprogrammer93/vllm-bounded-fs-kv-tier](https://github.com/smartprogrammer93/vllm-bounded-fs-kv-tier)|2|2026-09-02|给 vLLM `OffloadingConnector` 补**有界磁盘层 + LRU 淘汰**（out-of-tree，不 fork）：同一 60k token 提示，冷 prefill 64.6 s → 从盘恢复 16.5 s（**3.9×**），且 8 路并发恢复不抖|
|[Justin0504/thought-kv-hierarchy](https://github.com/Justin0504/thought-kv-hierarchy)|4|2026-04-09|**语义感知的 KV 内存层级**：推理链中 token 重要性长尾分布，低重要性 KV **从 HBM 下沉到 DDR 而非驱逐**。GSM8K：全量 68%；纯驱逐在 50%/30% HBM 预算下直接崩到 **0%**；层级方案在同样预算下保 **34%**|
|[jundot/omlx](https://github.com/jundot/omlx)|22708|2026-02-13|Apple Silicon 上的推理服务器，**KV Cache 热内存层 + 冷 SSD 层**双级持久化，上下文中途变化也不失效；连续批处理|
|[yandex-research/context-intensive-kv-offloading](https://github.com/yandex-research/context-intensive-kv-offloading)|5|2026-04-09|论文 _KV Cache Offloading for Context-Intensive Tasks_（arXiv:2604.08426）的官方代码，含 Text2JSON 数据集与 ShadowKV 变体评测|
|[lna-lab/LnaLang4U](https://github.com/lna-lab/LnaLang4U)|7|2026-05-15|用 sglang + **SSD** 在 Blackwell 上做 1M 上下文的 DeepSeek-V4-Flash 推理|
|[lycheenice/kvsim](https://github.com/lycheenice/kvsim)|1|2026-02-12|KV Cache 模拟器：显存、PD 解耦带宽、以及卸载路径的容量规划|

## B. 向量索引与向量表示压缩

|项目|★|创建|存储创新|
|---|---|---|---|
|[RyanCodrai/turbovec](https://github.com/RyanCodrai/turbovec)|17372|2026-03-26|Rust 进程内向量索引，基于 Google TurboQuant **每维 2/4 bit** 直接搜索压缩态：1000 万条 768 维从 float32 的 **31 GB → 4 GB**（4-bit 小 7.8×、2-bit 小 15.5×），4-bit 下比 FAISS FastScan **快 4.4×**；`sync(path)` 只写增量、一次 fsync、任意字节崩溃安全|
|[infino-ai/infino](https://github.com/infino-ai/infino)|118|2026-05-19|嵌入式检索库：全文、向量、混合与 SQL **共用同一张表，落成普通 Parquet** 放本地盘或对象存储——把"检索索引"变成"可被任何 Parquet 工具读取的数据文件"|
|[lux-db/lux](https://github.com/lux-db/lux)|288|2026-03-15|Redis 协议兼容的 KV 存储，标称最高 10× 快，**原生存向量支持**|
|[xerj-org/xerj](https://github.com/xerj-org/xerj)|3570|2026-06-30|Rust 本地 AI 搜索，**autoindex**：自动索引任意目录（含 `/_memory` 命名空间），让 agent 不再逐个读文件|
|[MinishLab/semble](https://github.com/MinishLab/semble)|6194|2026-04-06|基于静态嵌入的代码搜索：**平均仓库索引 ~500 ms、查询 ~1 ms、纯 CPU**，索引首次构建后缓存、文件变更自动失效；比 grep+read 省 99% token|

## C. 用「文件系统 / Git」做记忆底层（持久化抽象创新）

这一组把 **Markdown/文件系统当唯一真相源，把索引当可随时重建的派生物**——与我建议的"向量文件与边表分离、边表可重建"是同一思路。

|项目|★|创建|存储创新|
|---|---|---|---|
|[volcengine/OpenViking](https://github.com/volcengine/OpenViking)|39649|2026-01-05|**上下文数据库**：把 agent 的知识、记忆、技能统一成一个 `viking://` 下的虚拟文件系统，agent 像用文件一样 `ls`/`find`；文档明确提到"三层加载（three loading tiers）"与索引维护|
|[zilliztech/memsearch](https://github.com/zilliztech/memsearch)|2736|2026-02-09|**Markdown 是唯一真相源，Milvus 只是"影子索引"**（可弃可重建）；三层召回（search→expand→transcript）、稠密+BM25+RRF 混合、**SHA-256 内容哈希跳过未变内容**、文件监听增量同步|
|[tigerless-labs/agent-memory](https://github.com/tigerless-labs/agent-memory)|3401|2026-09-01|一个 store 里同时是"检索引擎"和"文件系统"：Markdown 为真相源，旁边的 **SQLite 索引是可随时删除的缓存**；检索返回路径而非粘贴文本|
|[shepherd-agents/shepherd](https://github.com/shepherd-agents/shepherd)|2481|2026-06-24|把 agent 执行变成**可逆的、Git 式的 trace**，落在文件系统/Git 底座上——日志即存储对象，可检视、可回滚|
|[enroute-sh/enroute](https://github.com/enroute-sh/enroute)|85|2026-08-24|把 git 平台重建在**对象存储之上**，"git hosting as an API"|
|[NodeDB-Lab/nodedb](https://github.com/NodeDB-Lab/nodedb)|225|2026-03-16|自述"面向 AI agent 的内存与存储引擎"，多模型、edge-to-cloud|

## D. 对象存储原生的数据系统

|项目|★|创建|存储创新|
|---|---|---|---|
|[namidb/namidb](https://github.com/namidb/namidb)|119|2026-05-18|**"bucket 就是数据库"**：Rust 写的属性图数据库直接住在 S3 桶里，支持 Cypher + 向量 + 混合检索，可嵌入、可做 HTTP/Bolt 服务、可挂 MCP|
|[HuskHoard/HuskHoard](https://github.com/HuskHoard/HuskHoard)|43|2026-04-16|Rust 写的 Linux **透明数据分层归档**：把冷数据自动下沉、对上层无感|
|[rootprint/rootprint](https://github.com/rootprint/rootprint)|431|2026-03-06|日志/trace 的全文检索**直接建在 S3 兼容存储上**|
|[storagesdk/storagesdk](https://github.com/storagesdk/storagesdk)|96|2026-05-12|统一 TS 存储 SDK，一等支持 snapshotting 与多后端|

## E. 上下文/数据压缩（减少存储与传输量）

|项目|★|创建|存储创新|
|---|---|---|---|
|[headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom)|75026|2026-01-07|**在数据进入 LLM 前压缩**工具输出、日志、RAG chunk、文件与对话历史：演示中 55,957 token 的 agent 提示压到 **24,340 token**，同时保留 item 67 的 FATAL 行；压缩在本机完成|
|[surya-koritala/Glyd](https://github.com/surya-koritala/Glyd)|248|2026-09-19|**无损 AI 压缩**：bit-for-bit 可逆，省 33% GPU 显存|
|[aerovato/magic-compact](https://github.com/aerovato/magic-compact)|174|2026-07-04|Claude Code / OpenCode 的**无损上下文压缩**插件|
|[lennney/mcp-slim-guard](https://github.com/lennney/mcp-slim-guard)|186|2026-07-31|MCP 上下文压缩，**上游调用不变、原始结果可精确取回**|
|[Supercompress/Supercompress](https://github.com/Supercompress/Supercompress)|136|2026-07-31|**查询感知**的上下文压缩，砍掉约 65% 输入 token|
|[ranxianglei/billion-context](https://github.com/ranxianglei/billion-context)|847|2026-08-06|面向小上下文窗口的压缩插件（100K 上下文即可）|
|[ojuschugh1/sqz](https://github.com/ojuschugh1/sqz)|646|2026-04-12|在工具输出进入上下文之前压缩|

## F. 语义缓存（检索结果复用层）

|项目|★|创建|存储创新|
|---|---|---|---|
|[GuglielmoCerri/khazad](https://github.com/GuglielmoCerri/khazad)|33|2026-06-13|**传输层**语义缓存，基于 Redis 拦截 LLM API 调用|
|[nickleodoen/ferrocache](https://github.com/nickleodoen/ferrocache)|25|2026-04-30|**分布式**语义缓存服务，多节点、MCP 兼容|
|[mpaymenremora/CacheCraft](https://github.com/mpaymenremora/CacheCraft)|31|2026-09-03|语义缓存策略**基准台**：把录制的请求 trace 回放到不同缓存策略上比较|
|[Rohit-Dnath/RAMen](https://github.com/Rohit-Dnath/RAMen)|36|2026-06-16|类 Redis 的内存数据存储，但**为 AI 而建**、drop-in 兼容 Redis 协议|

## G. 端侧与极端受限存储

|项目|★|创建|存储创新|
|---|---|---|---|
|[RightNow-AI/picolm](https://github.com/RightNow-AI/picolm)|2208|2026-02-19|纯 C：638 MB 模型**留在磁盘上 `mmap`，一次只换入一层**；含 FP16 KV cache 总运行内存仅 **~45 MB**（2048 上下文的 KV 从 88 MB 减半到 44 MB）|
|[memovai/mimiclaw](https://github.com/memovai/mimiclaw)|5789|2026-02-04|在 **$5 的 ESP32-S3（16 MB flash / 8 MB PSRAM）** 上跑个人 AI 助手与本地记忆，无 Linux、无 Node|
|[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen)|1950|2026-08-15|单张 24 GB 消费卡上跑 Qwen3.8-27B、150k 上下文；含模型准备流水线（重量化 head、校准 draft 词表）与分片加载|

## H. 记忆系统的分层与符号化

|项目|★|创建|存储创新|
|---|---|---|---|
|[TencentCloud/TencentDB-Agent-Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory)|27920|2026-04-07|明确反对"flat vector store"：**记忆分层（渐进披露 + 异构存储）＋ 符号记忆**——把冗长工具日志**上下文卸载**并压成 Mermaid 符号，既省 token 又可回钻|
|[MemPalace/mempalace](https://github.com/MemPalace/mempalace)|59508|2026-04-05|**逐字（verbatim）存储 + 可插拔检索后端**（默认 ChromaDB）；索引按"人/项目=wings、主题=…"结构化；LongMemEval 上 96.6% R@5、零 API 调用|
|[aiming-lab/SimpleMem](https://github.com/aiming-lab/SimpleMem)|3827|2026-01-01|ICML'26：面向 LLM agent 的**终身记忆**，主打"语义无损压缩"后存储与检索，支持文本/图像/音频/视频|
|[CortexReach/memory-lancedb-pro](https://github.com/CortexReach/memory-lancedb-pro)|4453|2026-02-24|LanceDB 记忆插件：**向量 + BM25 混合检索 + Cross-Encoder 重排 + 多作用域隔离**|
|[cortexkit/magic-context](https://github.com/cortexkit/magic-context)|2303|2026-03-26|**cache-aware 的延迟操作**：主动关闭宿主自带的 compaction 以免"双重压缩"，在后台持续管理上下文而非停顿重读|
|[moorcheh-ai/memanto](https://github.com/moorcheh-ai/memanto)|2311|2026-03-23|管理其他 agent 记忆的"记忆 agent"：管**保留、冲突、过期**，支持 `--as-of` **时间点回溯检索**|
|[FlowElement-xinliuyuansu/m_flow](https://github.com/FlowElement-xinliuyuansu/m_flow)|4515|2026-03-31|图 RAG 的下一层：不匹配 chunk，而是**对证据路径打分**（Episode + Facets + FacetPoints）|
|[xzf-thu/VoiceMem](https://github.com/xzf-thu/VoiceMem)|2455|2026-08-17|语音 agent 的"流式双脑"记忆服务：**中位检索延迟 12 ms**、中位召回 298 token，含本地 embedding 与情感归因|
|[Health-Yang/MineEcho](https://github.com/Health-Yang/MineEcho)|220|2026-05-28|Local-first Memory OS：**L0–L3 分层记忆 + Wiki++ 知识层**|

## I. 检索形态本身的创新

|项目|★|创建|存储创新|
|---|---|---|---|
|[StarTrail-org/PixelRAG](https://github.com/StarTrail-org/PixelRAG)|10248|2026-05-29|论文 _PIXELRAG: Web Screenshots Beat Text for RAG_（arXiv:2606.28344）官方实现：**不解析网页，直接渲染成截图建视觉索引**；提供 **828 万条 Wikipedia 页面**的托管索引，查询甚至可以是一张图|
|[VectifyAI/OpenKB](https://github.com/VectifyAI/OpenKB)|4774|2026-04-04|**"No Vector DB"**：用 PageIndex 的**树索引 + 摘要**做推理式（vectorless）检索，把原始文档编译成互链的 wiki 式知识库|
|[Ontos-AI/knowhere](https://github.com/Ontos-AI/knowhere)|3708|2026-04-30|**层级原生（hierarchy-native）记忆 schema**：视觉页轨与文本轨两条解析路径产出**同一份 chunk + metadata 契约**，使下游存储、图构建与检索与格式无关|

---

# 第三部分：与我的选型建议对照

|我建议的要点|2026 年项目的独立验证|
|---|---|
|KV Cache 下沉到 SSD|✅ A 组 8 个项目，其中 `eugr-spark-vllm-mods` 的 GPUDirect Storage 直连与 `vllm-bounded-fs-kv-tier` 的有界磁盘层最接近|
|下沉时不能简单驱逐（要有层级）|✅ `thought-kv-hierarchy` 直接量化了"纯驱逐在 50% 预算下精度归零"，与我引用的"分层而非丢弃"完全一致|
|词库元数据要单独成层|✅ `memsearch`（Markdown 真相源 + 影子索引 + SHA-256 去重）、`agent-memory`（SQLite 索引是可删缓存）|
|索引应当是**可重建的派生物**|✅ `infino`（索引即 Parquet）、`OpenViking`（虚拟文件系统）、`shepherd`（Git 式可逆 trace）|
|向量表示要能压到 2–4 bit 并直接搜索|✅ `turbovec`（TurboQuant，31 GB→4 GB，比 FAISS FastScan 快 4.4×，增量 `sync()` 崩溃安全）|
|低成本档与快速档要并存|✅ 语义缓存（F 组）＋ 上下文压缩（E 组）＋ 静态嵌入代码搜索（`semble`）构成低成本档；KV/注意力复用构成快速档|
|治理决策要可复算|⚠️ 生态里只有 `NaturalDAO/PoL-Governance/datasets/pol2/replay/` 做了重放审计，**且尚无检索层可审计**|

**一句话总结**：第一问的答案是"没有项目在用，因为文档还没发布"；但顺带发现**真正的 PoL2 项目就在 GitHub 上（`naturaldao/NaturalDAO`），其治理层已经跑起来、却完全没有检索存储层**——我上一轮推荐的"SSD 驻留可增量更新的图向量索引 + 声明式召回"在这个仓库里恰好是空白，而且 2026 年已经有一批开源实现（第二部分 A、B 组）可以作为它的现成地基。

---

## 附：本次调查的方法与局限

- **数据来源**：GitHub REST API v3（未认证）。仓库搜索配额 10 次/分钟，共执行 30 条检索式；README 经 `raw.githubusercontent.com` 获取（23 个仓库），不受搜索配额限制。
- **筛选口径**：`created:>=2026-01-01`；先按关键词召回 356 个去重仓库，再人工判断是否在**存储层**有实质创新，剔除"只是调用了向量库"的应用类项目。
- **局限**：(1) 无法执行代码级搜索（需鉴权），因此"仓库内文件是否引用某文档"这类验证缺失；(2) star 数为 API 返回值，未做真实性核验，且高 star 不等于技术价值；(3) 各项目自述的性能数字均未独立复现；(4) 检索式为人工设计，必然遗漏不使用标准术语的项目。
