# AI 时代 PoL2 高密度存储与可审计检索

核验日期：2026-10-23。资料为本次实际打开的项目官方文档与论文原始摘要；没有重用 V1 的 2026 年预印本性能数字。以下“推论”均是设计建议，尚未构成 PoL2 实测。

## 1. 当前技术选择与 4096 维兼容性

### Takeaway
以已有 PostgreSQL/pgvector 集成为最小实现基础，先补真实索引、过滤与回放，不应因数据量预期就改用 Hannoy 或预定 DiskANN 为最终内核。必须区分字段可存维度与 ANN 可索引维度。

### Cited Findings
- pgvector 官方文档：vector 与 halfvec 类型均可存 16000 维；HNSW、IVFFlat 的 vector 索引上限 2000 维，halfvec 上限 4000 维，bit 上限 64000 维。现有 halfvec(4096) 可存但无法直接使用这两种 halfvec ANN 索引。官方给出 binary_quantize 与原向量重排、支持模型的子向量索引等办法。近似索引过滤发生在扫描后，0.8.0 起迭代扫描可扩大搜索，但达到预算仍可能少于 k。— [pgvector README](https://github.com/pgvector/pgvector)
- DiskANN 主仓库是 DiskANN3 可组合 Rust 索引库，要求宿主实现 DataProvider；官方列出的内存、磁盘、Garnet、Bf-tree provider 是说明性实现。提供更新、量化、谓词钩子；旧 C++ 保存在 cpp_main，官方明确不再积极维护。README 的吞吐优势属于项目方宣称，本文不采作 PoL2 数据。— [DiskANN README](https://github.com/microsoft/DiskANN)
- 当前打开 main/Cargo.toml 的 workspace 版本为 0.60.0；V1 的 0.55.0 是旧快照，不应作为当前版本。这个版本号不意味着稳定生产 API 或数据库事务能力。— [Cargo.toml](https://raw.githubusercontent.com/microsoft/DiskANN/main/Cargo.toml)
- pgvectorscale 提供 StreamingDiskANN/SBQ，smallint[] labels 的 && 过滤进入索引，但任意 WHERE 仍为后过滤；README 明确称项目仍处早期，且给出未支持 UNLOGGED table 等限制。它不是对当前 halfvec(4096) 零修改即兼容的保证，应另验证数据类型、运算符类、升级恢复。— [pgvectorscale README](https://github.com/timescale/pgvectorscale)
- LanceDB 官方提供向量与全文检索混合及重排；它是分析/多模态检索候选，不代表已经具有 PoL2 事务事实源的一切语义。— [Hybrid search](https://docs.lancedb.com/search/hybrid-search)

### Inferences
- 4096 维迁移路径 A：保留原始向量，binary_quantize 后 bit HNSW 召回，原 4096 维精排；路径 B：选经验证的新低维 embedding 或投影，独立存检索向量与投影版本，保留旧原向量。不可任意截掉 96 维再声称质量不变，也不可把 Matryoshka 子向量能力泛化到任意模型。
- 厂商成熟度比较应列：锁定版本、恢复演练、过滤语义、备份/升级、SDK 与部署、量化质量、运维负担；Star 数不进入决策。
- pgvector 是当前基线；pgvectorscale 是同栈挑战者；Qdrant 是独立混合检索服务挑战者；LanceDB 是多模态/湖上训练数据检索挑战者；DiskANN3 是高定制适配候选。全部应经过同一 workload/golden set，不能按厂商公开 benchmark 排序。

### Gaps
- 本次没有部署并验证任何引擎的 4096 维方案、并发持久化或真实性能，也未核查所有 Python binding 源代码。不得把 README 的能力当成该项目已实现能力。

## 2. 高密度 AI 检索、记忆与迁移

### Takeaway
高密度不应等同于“所有字节都做一个大向量”。按权威状态、时间、来源与访问范围先约束候选，再进行稀疏/稠密融合和有限预算精排；多向量只给质量增益已验证的数据层。

### Cited Findings
- Qdrant Query API 支持多路 prefetch、融合和多阶段查询，官方展示 dense 与 sparse 的 RRF 融合。RRF 是排名融合，不是不同模型相似度校准后的概率。— [Hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- Qdrant 官方混合重排示例以稠密与全文召回，用 MAX_SIM 多向量精排，并为精排向量设 m=0 关闭 HNSW；因此 token 级多向量不必再各建 ANN 图。— [Hybrid search with reranking](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/)
- ColBERT 原论文明确分别编码 query/document，通过 late interaction 比较细粒度表示，document 可离线预计算；论文具体数据集性能不直接外推 PoL2。— [ColBERT, SIGIR 2020](https://arxiv.org/abs/2004.12832)
- LanceDB 默认预过滤；后过滤可能少于 limit 乃至为空；混合查询同一过滤应用于全文与向量分支。较旧 SDK 多次 where 会覆盖而非 AND，当前文档给出了需检查的版本差异。— [Metadata filtering](https://docs.lancedb.com/search/filtering)
- Qdrant 官方模型迁移流程包括重嵌入、新集合质量比较、原子切换 alias、切换 query embedding 模型，以及观察期保持旧新双写以便回滚。— [Embedding migration](https://qdrant.tech/documentation/tutorials-operations/embedding-model-migration/)
- LangGraph 将长期记忆定义为跨 session、按 namespace 存储的应用数据，并区分语义、情节、程序性记忆。— [Memory overview](https://docs.langchain.com/oss/python/concepts/memory)
- vLLM prefix caching 根据父块、精确 token 与额外上下文 hash 复用计算 KV，支持 cache salt 隔离；其 hash 序列化选择会影响跨版本可复现性。它服务推理加速，不是可引用知识记录。— [Prefix caching](https://docs.vllm.ai/en/latest/design/prefix_caching/)

### Inferences
- 建议 retrieval pipeline：身份/作用域和策略解析 → 结构化有效集合过滤 → 稀疏与稠密并路召回 → RRF/去重 → 有效性再次核验 → cross-encoder 或小候选 late interaction → 原文证据包 → 规则与治理。若尚无多租户，先实施 source/status/version/valid_at/snapshot，ACL 为未来契约；不得在外部 reranker 已看到内容后才做访问控制。
- 过滤低选择率时可对有效小集合精确扫描；扩大 ANN 预算不是普适解。语言分词、条款编号、否定、例外、引用链、过期撤销与互相矛盾证据须进入专门 golden set。
- 设 N 个 chunk、每 chunk 平均 t 个 token 向量、d_t 维、b 字节，则多向量原始负载为 N*t*d_t*b；与单向量 N*d*b 相比倍率为 t*d_t/d。该倍率不含图、offset、版本、复制。用实测 t 分布和 P95/P99，避免只算平均。
- 将 memory episode（执行轨迹）、semantic facts（来源事实）、procedure（已批准规则）分别管理。Agent 输出先作为候选，不能自动升级为规范；“记住”不等于“可信”。KV cache 可丢弃重算，知识与判定记录必须持久。
- cache key 至少绑定 namespace/scope、词库快照、策略、embedding/reranker/model、有效时间语义与查询规范化版本；撤销与策略切换要主动失效，不能仅靠 TTL。
- 模型/分块/量化/索引升级按 generation 进行：冻结旧 schema/manifest → 新代回填 + outbox 追增量 → 分层质量/删除可见性验证 → shadow read → 原子切换配置与 query encoder → 双写观察 → 可回退后按保留政策回收。迁移容量必须计旧新双索引与训练临时文件。

### Gaps
- 未证明 late interaction 在 PoL2 规则判断上的净收益，暂不宜全库铺设。向量检索高 recall 不等于治理证据完备。

## 3. target_recall、重放与安全的可验证边界

### Takeaway
target_recall 是离线校准目标，不能成为逐查询保证；记录回放、重新检索和模型重新生成应分级验收。Merkle 证明字节未变，不能证明内容真实或当时检索无遗漏。

### Cited Findings
- pgvector 明确默认精确 nearest-neighbor，加入近似索引会牺牲部分召回；建议比较 exact search 监控 recall，并给出事务内关闭 indexscan 的方法。— [pgvector README](https://github.com/pgvector/pgvector)
- FreshDiskANN 原文关注流式更新下 ANN 性能与召回，其论文摘要并没有提供 PoL2 单查询证明、规范性证据完备性或历史确定回放能力。— [FreshDiskANN 2021](https://arxiv.org/abs/2105.09613)
- OWASP 明确 RAG/微调不能充分消除 prompt injection，并以被篡改的 RAG 仓库为间接注入案例；建议隔离外部内容、约束权限、确定性格式校验与对抗测试。— [LLM01 Prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

### Inferences
- V1 target_recall=0.95 应改为 recall_target + calibration_id + estimated_recall（允许 null）+ budget_exhausted + effective_filter + eligible_count + incomplete；不允许把 estimate 当置信保证。离线分母是同一过滤后有效集合的 exact top-k，k_eff=min(k,有效数)，固定并声明 ties 规则。
- 分开报告 ANN Recall@k、人工/规则标注证据召回、冲突/例外覆盖、citation-support、治理误放/误拒、无证据弃权、越权返回数。若没有可信 ground truth 或有效证据不足，应 incomplete/abstain，不能虚报达到目标。
- 回放 R0：取回当时保存的证据字节和判定记录并验证 hash；R1：固定证据、规则与确定性判定代码重算；R2：固定 index snapshot、query vector、过滤、预算、数值库、排序与 tie-break 重新检索；R3：固定模型权重/tokenizer/prompt/runtime/随机状态重生成。ANN 重建不保证逐位同图；GPU/外部 API/model version label 不保证逐 token 一致。对 R0/R1 可有硬验收，R2/R3须声明环境和容差，原输出始终独立保存。
- DecisionRecord 额外记录原始与规范化 query hash、query embedding 字节引用、encoder/chunker/normalizer/quantizer/reranker 版本、所有过滤表达式、candidate IDs 与排序分数、融合配置、已选原文 byte range 与 hash、工具调用和返回、prompt、model artifact hash/外部服务版本标识、sampling 参数、实际输出、index generation/commit watermark。只存 request_hash 不能重算 request；仅存证据 ID 不能恢复被清理正文。
- 安全应在用户既有不要求多租户/密码学的边界内实施：读入原文一律数据而非控制指令；Agent 不能绕 stage/commit 自动提权为 policy；外部证据、候选记忆、批准规则分权限；自动高风险操作经确定性能力网关与独立机器审查，不引入运行时人工批准作为默认依赖。注入测试必须覆盖索引、reranker、摘要、工具和记忆写回环路。
- 最小 MVP：沿用 PostgreSQL，增加原文对象引用/内容 hash 与 immutable versions、transactional outbox、可用维度索引 + exact baseline、全文检索与简单 RRF、明确 snapshot watermark、证据包记录、R0/R1 replay。用 10K/100K/1M 作规模测试档而非上线容量承诺。只有当目标硬件上 P99、有效过滤召回、更新滞后、磁盘/内存、水位恢复、故障/重放和成本门槛失败，才启用挑战引擎；阈值由业务治理风险与负载测量制定，不从论文摘要复制。

### Gaps
- V1 的 VADER 等近期预印本没有在本研究中核验，不引用其数值，也不把其 target recall 术语升格为数学保证。未进行新的 PoL2 实验、索引建造或模型回放，本节为验收规格。
