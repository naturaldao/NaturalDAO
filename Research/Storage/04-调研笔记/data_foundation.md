# PoL2 高密度原始数据与事件事实层

核验日期：2026-10-23。以下为设计研究笔记，不是已部署能力或实测结果。已阅读 V1；当前实现与建议严格区分。来源页面已实际打开，共 10 个。文中所有容量示例和阈值均为可复算的设计假设。

## 1. 什么是高密度 PoL2 的持久事实源，格式如何分工？

### Takeaway
持久事实源应为不可变原始对象、规范化事件以及发布清单；向量、图索引、全文索引和缓存是可重建派生物。先建立一个事实源，再按访问模式增加投影，避免同时引入多个湖仓主格式。

### Cited Findings
- Parquet 是列式数据文件格式，提供压缩和编码；各实现支持的特性不完全相同，跨引擎需要兼容测试。它本身不是跨文件事务协议。— [Apache Parquet overview](https://parquet.apache.org/docs/overview/)
- Arrow 定义语言无关的内存结构、序列化和传输；优化扫描、向量化和共享内存访问，并把并发修改协调交给实现。Arrow 不应被描述为持久数据库或事务层。— [Arrow columnar specification](https://arrow.apache.org/docs/format/Columnar.html)
- Iceberg 以元数据文件、快照和 manifests 跟踪数据文件；元数据指针的原子替换构成并发提交基础。规范明确具体提交原子操作由 catalog/实现承担；对象存储不是自动提供多对象事务。— [Iceberg specification](https://iceberg.apache.org/spec/)
- Paimon 主键表保留每个键的逻辑当前行，物理版本可暂存于多个文件，在读取或 compaction 时合并；其主键文件结构使用 LSM。适合 CDC/upsert，并非天然保留每次业务事实的不可变审计日志。— [Paimon 2.1 primary-key table](https://paimon.apache.org/docs/2.1/primary-key-table/)
- Lance 官方文档同时定位 file/table/catalog 格式，提供多模态 BLOB、随机行读取以及向量与全文索引。官网“100×”是项目宣传/特定基准主张，不能作为 PoL2 预测或实测。— [Lance official overview](https://lance.org/)

### Inferences
- 推荐数据模型：`RawObject(content_id, sha256, byte_length, media_type, codec, object_version, physical_locator)`；`Event(event_id, producer_id, producer_sequence, entity_id, entity_version, event_type, event_time, ingest_time, raw_refs[], schema_version, policy_version, provenance)`；`DerivedArtifact(source_content_ids, transform_digest, model_digest, tokenizer_digest, config_digest, artifact_hash)`；`ReleaseManifest(table_snapshot_ids, raw_manifest_hash, derivation_manifest_hash, policy_hash, retention_pin, event_watermarks)`。这些字段为 PoL2 设计，不是某个产品现成 API。
- 内容 ID 标识字节身份；业务 entity/event ID 标识语义身份；两者不能合并：同一字节可有不同授权、来源、时间和治理意义。去重保留每条 provenance 边，不能只留一份“出处”。
- 模态原件按原生格式保存（文档、音视频、图像、工具结果、代码、对话）；抽取文本、OCR、chunk、token、embedding、图边分别记录变换谱系。embedding 既不能无损还原原文，也不能替代通用语言模型训练语料；它只可作为特定 embedding/检索训练任务的数据组成。
- 建议主路线：原始 BLOB 对象层 + Parquet 事件/标注表，达到多写者和快照训练需求后引入 Iceberg catalog；Arrow 作批处理接口。Paimon 仅在持续 upsert/CDC 需求实测占主导后替代或承担专门投影；Lance 仅作为多模态随机取样/特征投影候选。不要默认 Iceberg + Paimon + Lance 三套都成为主事实源。
- V1“向量文件兼作训练语料”“L1–L3 全部从 L0 重建”需要改写：可重建性前提是日志包含完整原始字节，或引用的对象版本及全部变换依赖仍保留且可访问。哈希、URI、Merkle 根、embedding 都不能重建已删除原件。
- 最小地面 MVP：本地不可变对象目录（哈希分片）+ SQLite 元数据/事件/outbox 同一事务 + 批量 Parquet 导出 + 原子发布只读清单 + 一个独立 ANN 投影。原始文件先持久化再提交引用；无引用孤儿晚些清理。无须一开始部署 Kafka、Flink、Iceberg、分布式对象集群。

### Gaps
- 当前无 PoL2 真实模态比例、压缩比、数据熵、字节去重率、访问热点和训练采样分布；任何最优格式、块大小、索引比例都未实证。
- 最新网页可能含实验性规范；生产必须固定 format version、引擎版本和跨版本读取矩阵。此研究不宣称最新 Iceberg v4 相关功能已被全部引擎支持。

## 2. 怎样在高写入、十亿至万亿条记录下保持提交与恢复语义？

### Takeaway
以“至少一次传输 + 幂等业务提交 + 可核对发布清单”为默认设计。分片、批处理、压实、背压和可重复消费比选择某个日志产品更重要。

### Cited Findings
- Kafka 的事务可协调 Kafka 输入 offset 和输出 topics；写入外部系统的 exactly-once 需要目的系统协作，默认至少一次不能直接推广为跨对象、SQL、ANN 的 exactly-once。— [Kafka 4.1 design: message delivery semantics](https://kafka.apache.org/41/design/design/)
- Amazon S3 对成功对象 PUT/DELETE 提供强读后写一致性，单 key 更新原子，但明确不支持跨 key 原子更新；这些是 AWS S3 的语义，不能自动泛化所有 S3-compatible 实现。— [S3 consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- S3 官方示例每个分区前缀至少 3,500 写类请求/s 或 5,500 GET/HEAD/s；扩展渐进且可能出现 503。该数字仅是特定服务指导，既不是 PoL2 实测，也不是私有或轨道对象存储指标。— [S3 performance design patterns](https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html)
- SQLite WAL 允许读写并发，但同一时刻只有一个 writer，依赖同机共享内存；不应把 WAL 文件放网络文件系统就当成多机数据库。— [SQLite WAL](https://www.sqlite.org/wal.html)
- Iceberg 明确小文件增加 manifest 元数据和打开文件开销，提供数据文件 compaction 与 manifest rewrite；压实是持续运维职责。— [Iceberg maintenance](https://iceberg.apache.org/docs/latest/maintenance/)

### Inferences
- 写入协议：①接收幂等键并登记 staged；②写不可变原件/分片并验证长度与校验和；③在主事务提交事件、对象引用、版本和 outbox；④消费者以 `(event_id, projection_version)` 幂等处理派生任务；⑤候选投影完成后原子切换 release 指针。只有③成功才能返回业务 committed；ANN 的 fresh watermark 单独暴露。阶段②失败不提交引用，③失败会留下待清理对象，④失败重试，不应回滚已发布历史事实。
- 增量顺序以 `(entity_id, entity_version)` 或生产者序列约束；跨分区不声称全局全序。记录 event-time、ingest-time 和迟到策略；watermark 不等于“永不再到达”。从消息日志重放时必须检测幂等窗口不足、缺序、冲突版本和 schema 不兼容。
- 禁止每个 token/chunk/event 都产生独立小对象。短事件先追加段文件，再批量形成列式文件；大 BLOB 保持独立，海量小 BLOB 可不可变打包并保存 `(pack_id, offset, length, hash)`。块大小必须平衡随机读取放大、故障域、尾延迟和删除代价。
- 起始候选而非硬指标：列式文件 128–512 MiB；按时间窗口加有限 hash bucket 分区；禁止按 event_id/agent_id 创建无限分区。对象键哈希前缀、分片目录、每分片清单/索引，避免查询时全桶 LIST；清单与元数据查询必须有物理访问路径。
- 10^12 条事件与 10^12 个对象不是同一规模：若每条原始事件 1 KiB，逻辑字节约 1.024 PB；压实成 256 MiB 文件约 3.81×10^6 个文件（未计压缩/元数据），而非 10^12 个对象。若每个对象引用元数据 256 B，10^12 条引用本身即 256 TB，未计索引、复制、版本和运行开销。此为十进制容量算例。
- 并行度取决于写入分布与热点，不只是总量；采集分区偏斜、单热点 entity、失败重试放大、compaction backlog、最老 outbox 年龄、投影 lag 和读取字节/query。扩容闸门应采用实测的持续负载与恢复时间，不用“到十亿条就必须切换”之类固定规模断言。
- 分布式路径：单机瓶颈被量化后迁移 SQL 主事务至 PostgreSQL；对象层换满足一致性/持久性要求的对象服务；只有多生产者解耦及长时间积压需求出现后增加 Kafka；训练扫描与多引擎快照需求出现后增加 Iceberg catalog。每一步保留相同事件 ID、内容哈希、manifest 和幂等契约。

### Gaps
- 未运行 benchmark，因此没有亿/万亿规模可用性、吞吐、端到端 P99、恢复时限承诺；S3 服务指导不能证明自建系统规模。
- 现有代码基线09fdf57 的 PostgreSQL halfvec(4096) 和全局 vector ORDER BY 并不意味着分布式/ANN 索引、scope 过滤或在线双模型迁移已实现；报告需由负责代码核对者引用精确行号。

## 3. 如何预算容量、写放大与版本保留，避免不可恢复的 GC？

### Takeaway
容量与寿命要按整个数据生命周期核算，不能只数向量。快照、日志、对象、训练版本和派生版本的保留共同决定可恢复性，GC 必须跨层追踪引用。

### Cited Findings
- Iceberg 快照可时间旅行，过期后对应快照不可查询；数据文件须在没有保留快照引用后才能删。孤儿清理保留窗口短于最长在途写入会误删有效文件；官方默认三天仅是配置默认值，不能代替 PoL2 灾备/离线任务窗口。— [Iceberg maintenance](https://iceberg.apache.org/docs/latest/maintenance/)
- Iceberg 快照只覆盖其表数据文件与表元数据；原子提交依赖 catalog，规范不定义 PoL2 的多表、外部 BLOB、模型权重、ANN 索引的一体事务。— [Iceberg specification](https://iceberg.apache.org/spec/)

### Inferences
- 定义类别 i 的 λ_i（逻辑记录/s）、b_i（平均未压缩 byte/条）、c_i（存储字节/原始字节）、d_i（字节去重后比例）、T_i（保留秒）。稳态唯一逻辑存储 `D_i = λ_i b_i c_i d_i T_i`，适用于平稳流且没有额外版本；事件、BLOB、标注、向量分别计算。不平稳情况应对到达率积分，且不要把去重/压缩重复乘两次。
- 物理稳定容量：`D_steady = Σ_i R_i D_i + D_versions + D_indexes + D_catalog + D_backups`，R_i 为副本系数或纠删码 `(k+m)/k`；若备份已包含在 R_i 内不再重复相加。峰值 `D_peak = D_steady + D_ingest_backlog + D_compaction_workspace + D_migration_overlap + D_repair_workspace`，再除以允许使用率 u 得规划可用容量。必须记录 raw/usable 单位和 GB/GiB、TB/TiB 差异。
- `N_vectors = N_chunks × n_models × n_versions_retained`；`D_vectors = N_vectors × dimension × bytes_per_component`，另加 ID、图边、量化码、过滤字段和版本重叠。算例：10^12 个 4096维 FP16 向量本体为 8.192 PB，非整个系统容量；FP32 为16.384 PB，且不含任何索引。
- 存储软件写放大 `WA_host = host_write_bytes / admitted_unique_logical_bytes`；介质写放大 `WA_device = NAND_program_bytes / host_write_bytes`；若统计域一致，总 NAND 量为 `logical_bytes × WA_host × WA_device`。复制网络字节、对象 PUT 数、压实读量、索引重建写量和纠删码更新另列；不能把集群总写量与单盘 SMART 比值混用。没有 telemetry 的设备不可声称测得 NAND WAF。
- 保留 horizon 独立配置：流重放窗口、原件保留、判定可重放、训练可复现、模型旧版、灾备恢复。若要求“任意历史判定完整重放”，这些依赖必须保留到该判定失效；否则明确是有限窗口或仅保留指纹验证。丢失原件后的 Merkle 根只能校验提供的候选字节，不能恢复字节。
- ReleaseManifest 固定每张表的 snapshot ID、原件 manifest、模型/规则/变换版本和各分区 offset；多表快照由 PoL2 发布协议统一绑定。每张表各有事务并不自动使 release 跨表一致；先写候选后校验引用完整，最后原子发布 release pointer。
- 全局 GC 两阶段：mark 所有 retained release、training run、decision retention、active reader lease、backup pin、in-flight transaction 引用的对象/分片；sweep 仅删除未标记且超过安全期者。先候选清单/dry-run/审计，再延时删除；不能仅依据对象年龄、ANN tombstone 或单个表 snapshot expiration 删除原始 BLOB。安全期至少涵盖最长在途写/失败重试/离线消费者/时钟误差，具体值需工作负载测定。
- pack 内一项删除不能直接释放一部分对象；执行新 pack 重写、校验、切换 locator manifest，旧 release reader 释放后再删旧 pack。原始 hash/content ID 不随物理搬迁改变。删除传播到投影、缓存、备份和训练集版本必须独立跟踪，不应宣称 tombstone 等同物理清除。

### Gaps
- 轨道设备 BER、功耗、辐照寿命和修复带宽没有本研究实测；云对象服务的保证不能用于证明轨道可用性。纠删码比例、scrub 周期、冷备份量和寿命必须留待硬件与工作负载联合测试。
- 可压缩性与可去重性依赖真实数据；高“语义密度”不推出高压缩率，也不推出必须全量常驻 ANN。

### 附：协调者指定的可复算示例（设计假设）

所有数字均为假设而非实测：每日事件 E 为10^6/10^8/10^10，对应 payload b 为2048/8192/16384 bytes；保留365日；10%事件进入索引，每个被索引事件8个向量；1024维、每分量2 bytes；图度32、邻接ID8 bytes、节点开销64 bytes、PQ码64 bytes；原件压缩比0.5、归档物理因子1.5；向量副本2、ANN副本2；元数据1024 bytes/event、副本2；空闲预留25%。重建临时量定义为一份不含副本系数的 vector+ANN（不是再复制两份）。

```text
N = E * 365                         # events
V = N * 0.1 * 8                     # indexed vectors
raw_B = N * b * 0.5 * 1.5
vectors_B = V * 1024 * 2 * 2
ann_B = V * (32 * 8 + 64 + 64) * 2
metadata_B = N * 1024 * 2
steady_B = raw_B + vectors_B + ann_B + metadata_B
rebuild_B = V * (1024 * 2 + 32 * 8 + 64 + 64)
provisioned_B = (steady_B + rebuild_B) / (1 - 0.25)
TB = bytes / 10**12
PB = bytes / 10**15
```

|每日事件/载荷 bytes|原件 TB|向量 TB|ANN TB|元数据 TB|稳态 TB|重建临时 TB|含预留规划 TB|
|---|---:|---:|---:|---:|---:|---:|---:|
|10^6 / 2048|0.560640|1.196032|0.224256|0.747520|2.728448|0.710144|4.584789|
|10^8 / 8192|224.256|119.6032|22.4256|74.752|441.0368|71.0144|682.734933|
|10^10 / 16384|44851.2|11960.32|2242.56|7475.2|66529.28|7101.44|98174.293333|

最后一档规划量约98.1743 PB。计算仅包含指定项；**没有建模视频大对象、额外模型旧版本、旧快照差异、备份、compaction与故障修复并发、积压、catalog/倒排/图证据索引、对象请求费用和带宽**。archive factor1.5为该假设，不是某种纠删码部署承诺。PQ码与原始向量同时计入是假设需要保留两者；具体ANN可能用不同邻接布局或不需要这些字段。若“重建1×”意指连副本也整体双写，应把 rebuild 改为 vectors_B+ann_B；不要在计算器中隐式决定。分档 payload 随规模变化是情景设定，不代表事件载荷随规模必然增长。
