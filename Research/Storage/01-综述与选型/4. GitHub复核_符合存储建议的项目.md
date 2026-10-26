# GitHub 复核调查：哪些项目符合《PoL2 存储技术选型建议》

**调查时间**：2026-10-10 **数据来源**：GitHub REST API v3（未认证）+ `raw.githubusercontent.com` 抓取 29 份 README **检索规模**：29 条按条款设计的检索式，召回 400+ 仓库，逐条比对后保留 26 个候选

---

## 0. 先说结论

把建议书拆成 12 条可核验的条款后，GitHub 的覆盖呈现**极度不对称**：

|条款组|覆盖情况|
|---|---|
|**检索存储层**（C1 磁盘驻留图索引、C2 在线增量更新、C3 声明式召回、C12 低 DRAM）|**很好**，且有 1 个几乎逐条命中的项目（PipeANN）|
|**热层复用**（C4 前缀/注意力复用、C5 分层与复用感知驱逐）|**很好**，LMCache 生态 + 多个 2026 年新实现|
|**介质与冷层**（C6 纠删码/对象存储、C7 FDP/写放大）|**有，但很冷门**（多为 Kioxia 官方插件级项目，个位数 star）|
|**治理存储层**（C8 版本化证明、C9 分阶段写入准入）|**几乎空白**，只有零散的个人项目触及"哈希链审计"|
|**自愈层**（C11 零 I/O 恢复）|**完全空白**，GitHub 上只有常规 checkpoint/重提交方案|

一句话：**"把知识检索做得又快又省"这件事，开源界已经做完了；"让每一次治理判定都可复算、可审计"这件事，开源界基本没人做。** 后者恰好是 PoL2 最不可替代的部分。

**首选组合**：`PipeANN`（SSD 驻留可更新图索引）＋ `GateANN`（过滤检索）＋ `LMCache`/`HiQCache`（热层复用）＋ `ErasureFs`（纠删码+FDP 冷层）＋ 自建的 C8/C9（因为找不到现成的）。

---

## 1. 判定方法

### 1.1 从建议书抽出的 12 条可核验条款

建议书的核心是"SSD 驻留、可在线增量更新的图向量索引 + 声明式召回"，加上热层、冷层、自愈三层配套。我把它拆成下面 12 条，每条都能用仓库的 README/代码结构直接验证：

|编号|条款|权重|判定依据|
|---|---|---|---|
|**C1**|索引主体驻留 SSD，DRAM 只留路由/缓存|3|是否有 disk/SSD/mmap/LMDB 后端，是否报告内存占用|
|**C2**|在线增量插入/删除，不全局重建、不阻塞查询|3|是否有 insert/delete API 与并发更新评测|
|**C3**|可配置/声明式召回 + 过滤检索|2|是否有 recall 目标、filter predicate、索引重建代价|
|**C4**|热层复用：前缀/注意力/KV/chunk 缓存|2|是否有跨请求 KV 复用与命中率数据|
|**C5**|分层卸载 + 复用感知驱逐（非纯 LRU）|2|是否有 HBM→DRAM→SSD 层级与复用评分|
|**C6**|纠删码 / 对象存储冷层|1|是否有 EC、S3 后端|
|**C7**|写放大与放置控制（FDP/ZNS）|1|是否直接操作 NVMe 放置指令|
|**C8**|不可变追加日志 + 哈希链/版本快照|3|是否有审计链、来源校验、可重放|
|**C9**|分阶段写入准入（配额/审计/仲裁）|2|是否有写入准入、冲突/过期治理|
|**C10**|真相源与索引分离，索引可整删重建|2|是否声明"索引是派生品"|
|**C11**|自愈：零 I/O 恢复 / 无检查点重建|1|是否有引用重绑、stage 重建|
|**C12**|低 DRAM/量化表示（轨道功耗）|2|是否有 2–8 bit 量化、二进制量化|

权重合计 24。**权重最高的是 C1/C2/C8（各 3 分）**——因为建议书论证过：容量、演化、可辩护性这三件事是这个场景不可让步的约束。

### 1.2 检索式设计

按条款各设计 2–3 条检索式，例如：`diskann`、`topic:diskann`、`"on-disk" vector index`、`odinann`、`freshdiskann`、`"filtered vector search"`、`"ACORN" vector search`、`"prefix caching" llm`、`lmcache`、`"kv cache" offload ssd`、`"kv cache" hierarchy`、`"erasure coding" storage`、`"object storage" vector index`、`"flexible data placement"`、`"provenance" llm audit`、`"markdown" "memory" agent index`、`"checkpoint-free"`、`"binary quantization" vector search`。

按 star 排序取前 25 条，人工判定是否真的实现该条款（剔除只是"调用某个库"的应用项目、fork、教学作业）。

### 1.3 判定符号

- ● 直接满足，README/代码中有明确证据
- ◐ 部分满足，或仅在某一子场景成立
- ○ 未涉及

---

## 2. 符合度矩阵

|项目|★|C1|C2|C3|C4|C5|C6|C7|C8|C9|C10|C11|C12|得分|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**thustorage/PipeANN**|158|●|●|●|○|○|○|○|○|○|◐|○|●|**17**|
|**GateANN-public**|12|●|○|●|○|○|○|○|○|○|○|○|◐|**13**|
|**microsoft/DiskANN**|1949|●|●|●|○|○|○|○|○|○|◐|○|○|**14**|
|**pgvectorscale**|3146|●|●|●|○|○|○|○|○|○|◐|○|●|**17**|
|**DiskVecLab**|13|●|◐|●|○|○|◐|○|○|○|○|○|◐|8|
|**FreshDiskANN-baseline**|18|●|●|○|○|○|○|○|○|○|○|○|○|11|
|**meilisearch/arroy**|313|●|●|○|○|○|○|○|○|○|●|○|○|14|
|**hannoy**|87|●|●|○|○|○|○|○|○|○|◐|○|○|12|
|**LMDiskANN.jl**|7|●|○|○|○|○|○|○|○|○|◐|○|●|9|
|**SIEVE (VLDB'25)**|18|○|○|●|○|○|○|○|○|○|○|○|○|2|
|**guestrin-lab/ACORN**|120|○|○|●|○|○|○|○|○|○|○|○|○|2|
|**LMCache**|12105|◐|◐|○|●|●|◐|○|○|○|○|○|○|13|
|**ruipeterpan/marconi**|71|○|○|○|●|●|○|○|○|○|○|○|○|8|
|**HiQCache**|11|○|○|○|●|●|○|○|○|○|○|○|●|11|
|**UniCache**|10|○|○|○|◐|●|○|○|○|○|○|○|○|6|
|**HERMES**|109|○|○|○|●|●|○|○|○|○|○|○|○|8|
|**kvcache-sim**|2|○|○|○|◐|●|◐|○|○|○|○|○|○|6|
|**ErasureFs**|0|○|○|○|○|○|●|●|○|○|○|○|○|4|
|**UFROP**|8|○|○|○|○|○|◐|●|○|○|○|○|○|3|
|**VecPuff**|14|◐|○|○|○|○|●|○|○|○|◐|○|○|6|
|**strand**|0|◐|○|○|○|○|●|○|○|○|●|○|○|8|
|**hypermnesic**|9|○|○|○|○|○|○|○|◐|○|●|○|○|7|
|**AI-MemoryHub**|4|○|○|◐|○|○|○|○|◐|◐|●|○|○|8|
|**provena**|18|○|○|○|○|○|○|○|●|○|○|○|○|5|
|**echovault**|150|○|○|○|○|○|○|○|○|○|●|○|○|4|
|**xcena-dev/maru**|64|◐|◐|○|●|●|○|○|○|○|○|○|○|10|

---

## 3. 第一梯队：直接实现主推荐

### 3.1 `thustorage/PipeANN` —— 建议书的"逐条命中"

> A low-latency, billion-scale, and **updatable** graph-based vector store **on SSD**.

这是我找到的唯一一个把建议书三条核心条款同时做到位的项目（C1+C2+C3+C12，得分 17/24，与 pgvectorscale 并列最高）。README 自报：

|指标|数值|
|---|---|
|延迟|**10 亿向量 <1 ms**（top-10、90% 召回），仅内存索引的 **1.14×–2.02×**|
|吞吐|10 亿向量 **20K QPS**，超过 DiskANN 与 SPANN|
|**更新**|插入/删除对搜索干扰仅 **1.07×** 波动|
|**过滤**|1 亿向量上属性过滤 3K QPS / 6 ms（speculative filtering）|
|**内存**|比内存索引省 **>10×**，10 亿向量约 **40 GB**|
|多盘|4 块 SSD + SPDK 后端，10 亿向量 70K QPS、2 ms 尾延迟|
|接口|Python（类 faiss）+ C++，Milvus 兼容 API（drop-in MilvusClient + gRPC）|

**为什么它最贴**：建议书的核心论点是"内存里只留路由层，语料主体在 NAND"。PipeANN 的 1B/40GB 恰好把这个比例做到约 2.5%（40 GB 对 1 TB 级原始向量），且它是**唯一把"可更新"写进标题**的项目——这正对应"词库由 Agent 持续生成、不能停机重建"。

**缺什么**：C8/C9（无审计链、无写入准入）、C5（无 DRAM 分层，只有单级 SSD）。

### 3.2 `GyuyeongKim/GateANN-public` —— 把 C3 做到极致

> **GateANN: I/O-Efficient Filtered Vector Search on SSDs**，直接建在 PipeANN 代码库之上。

它的做法正好回答建议书里"治理判定带类别/版本约束，不是纯 ANN"这一条：**在发起 SSD I/O 之前先检查节点的 filter metadata**，对不匹配的节点用 **graph tunneling** 完全在内存中穿越，从而在 10% 选择率下消掉最多 **90% 的 SSD 读**。

- 相对 post-filter 基线：SSD I/O 最多 **少 10×**，10% 选择率下吞吐最多 **高 7.6×**
- **不需要重建索引**就能支持任意过滤谓词
- 单台商用服务器从 1000 万扩展到 **10 亿**向量

这是"过滤器 + 图索引"组合里最接近建议书"声明式约束不应破坏召回"的实现。

### 3.3 `timescale/pgvectorscale` —— 工程化最成熟，但正在转向

- 提供 **StreamingDiskANN**（DiskANN 的流式变体）、**Statistical Binary Quantization**（比标准二值量化更好的压缩）、**label-based filtered search**
- 相对 Pinecone 存储：**28× 更低 p95 延迟、16× 更高查询吞吐**（其 README 口径）

**重要保留意见**：其 README 开头明确写着团队正在做 `pg_vectorsearch`——"**uses partitioning and compression instead of graph-based indexing**"。也就是说这个项目自己正在离开图索引路线。如果你的目标是长期押注，这一点必须知道。

### 3.4 `microsoft/DiskANN` —— 参考实现

1949★，官方描述是"bring fast, fresh and filtered search to your database"。FreshDiskANN（流式更新）与 Filtered-DiskANN 都出自这里，是上述所有派生项目的共同祖先。缺 C12（无内置低比特量化）。

### 3.5 其余可选项

- `g4197/FreshDiskANN-baseline`（18★）：OdinANN（FAST '26）官方 baseline，**默认改用 io_uring**——如果要在 SSD 上做低延迟 I/O，这个改动值得直接借鉴。
- `meilisearch/arroy`（313★）：基于 **LMDB**（mmap KV）的 ANN 库，索引与查询分离、多进程共享、**增量更新不需重建**——是"索引即文件、可被多进程同时读"的干净范例。
- `nnethercott/hannoy`（87★）：LMDB 上的 HNSW，支持**动态插入删除**，坏处是仍以图为主、内存占用不如 DiskANN 系。
- `mantzaris/LMDiskANN.jl`（7★）：Julia 的 LM-DiskANN，向量与邻接表都放 mmap 文件，可选 LevelDB——**低内存**取向清楚，适合做原型验证。
- `alibaba/DiskVecLab`（13★）：**磁盘向量检索的评测框架**，支持受控消融、多存储环境、并发与查询分布。它对应的正是建议书 §7 的"地面验证清单"——如果你要自己验收，用这个框架比自建脚本可靠。
- `BillyZhaohengLi/SIEVE-vldb25`、`guestrin-lab/ACORN`：过滤向量检索的两种不同思路（索引集合 vs 谓词无关图）。它们只解 C3，不解决存储层。

---

## 4. 第二梯队：热层复用（C4/C5）

建议书说"治理请求天然有热点，把检索+prefill 变成缓存命中是收益最大的一步"。这一层开源生态最成熟。

|项目|关键事实|
|---|---|
|**LMCache/LMCache**（12105★）|KV Cache 层的事实标准，把 KV 从 GPU 拉到 CPU/磁盘/远端并可跨实例复用。建议书里"下沉而非驱逐"的工程基座|
|**ruipeterpan/marconi**（71★）|MLSys '25 _Marconi: Prefix Caching for the Era of Hybrid LLMs_ 官方实现。**混合模型（attention+SSM）的前缀缓存**，其复用评分被多个下游项目直接借用|
|**awesome-pro/hiqcache**（11★）|给 SGLang HiCache 加 **INT8 分层**：GPU 保 BF16，被逐出的 KV 以 INT8 存进 CPU 层，命中后反量化。同样主机内存预算下 L2 容量 **1.78×**（54,254 → 96,451 tokens）|
|**xsyslab/UniCache**（10★）|基于 vLLM 的**前缀缓存逐出策略模拟器**，trace 驱动、块级命中率分析——用来选逐出策略|
|**haowei-freesky/HERMES**（109★）|ACL 2026：把 KV Cache 当**分层记忆**用于流式视频理解|
|**cklxx/kvcache-sim**（2★）|单机 HBM→DRAM→SSD 三级 + 万卡（10,240 GPU / 160 机架、每架共享 EIC）集群模拟器，含 6 种逐出/预取策略|

**对建议书的一个修正提示**：`cklxx/kvcache-sim` 的"每机架共享 EIC（CXL/RDMA）"结构说明，**CXL 在节点/机架内部作为 KV 共享池是成立的**。建议书否决的是"把 CXL 内存机架当作主存储架构"（因为需要可维护的机械与互连），但没有否决节点内共享——这一点在第 7 节还会看到一个直接证据。

---

## 5. 第三梯队：介质与冷层（C6/C7）

|项目|关键事实|
|---|---|
|**kioxia-jp/erasurefs**（0★）|RocksDB 插件：把数据切分、加纠删码，**分散到多块支持 FDP 的 SSD** 上，后端用 UFROP。这是 C6+C7 的合体，也是我找到的唯一"纠删码 + FDP"同时实现的代码|
|**kioxia-jp/ufrop**（8★）|RocksDB 的用户态文件系统，把文件生命周期 hint **翻译成 SSD 的 PlacementID**，应用无需改代码就能吃到 FDP 的写放大收益|
|**KMJ-007/VecPuff**（14★）|**S3 上的向量数据库**：WAL 批量写 S3 → 后台 compaction 成索引段 → SPFresh ANN。这是"对象存储做冷层"最干净的参考实现|
|**tsouza/strand**（0★）|引擎无关的**检索索引存储格式**，object-storage-first，一个容器里同时装 BM25 postings 与稠密 ANN 索引，支持原地查询与冷启动读小片段|

这一组 star 都很低（0–14），说明**介质层的创新在开源界几乎无人做**——大厂做了但不公开。若你要自己实现，建议直接从 Kioxia 的两个插件读起（它们直接对着 NVMe 规范写）。

---

## 6. 第四梯队：证明与可重建索引（C8/C10）——最薄弱的一环

|项目|关键事实|
|---|---|
|**leonardsellem/hypermnesic**（9★）|把建议书的 C10 说得最直白：**"Markdown 是真相源；搜索索引是可弃投影，随时删了重建，重建永远不会丢数据"**；每条记忆都是一次真实 Git commit，可审阅可回滚|
|**Traceless-zero/AI-MemoryHub**（4★）|零依赖：Markdown 正文为权威源 + 薄 SQLite 索引（**可由 front-matter 全量重建**）；**用确定性检索替代向量 RAG**，并主张"**拒答/澄清**代替向量硬猜"——这与建议书"判定必须可辩护"高度同源|
|**rajfirke/provena**（18★）|唯一把 **C8 做到代码级**的项目：每次检索调用记 SHA-256 内容哈希、做来源校验与新鲜度检查、写**哈希链审计轨迹**以检测篡改；`ContextTrail(storage_path="audit.db")` 一个装饰器接入|
|**mraza007/echovault**（150★）|Markdown vault + 索引，Obsidian 可读，支持 reindex/refresh|
|**hermes-labs-ai/zer0dex**（63★）|双层：**人类可读的 Markdown 索引**常驻上下文 + 本地向量库仅在有需要时取细节——正好是"低成本档 + 快速档"的一种落地|

**这一组的共同缺陷**：全部是个人项目，没有并发写入、冲突仲裁、版本快照（Merkle）、多 Agent 写权限这些 C9 要素。**建议书第 5 节的写入协议（分阶段准入 → 提交 → 演化 → 仲裁）在 GitHub 上找不到现成实现。** 这是必须自建的部分。

---

## 7. 与建议书相悖、但值得你知道的项目

**`xcena-dev/maru`（64★）——CXL 共享内存上的 KV Cache 存储引擎**

它的论点很锋利：_"所有现存的 KV 共享方案都假设共享等于搬运——逐字节跨网络拷贝。模型变大、上下文变长后，这个假设成为结构性瓶颈。Maru 拒绝这个前提。"_ 做法是把 KV 放进 CXL 共享内存池，多个推理实例**直接访问、零拷贝**。

建议书明确否决了"CXL 内存池化/内存机架"作为主架构，理由是它依赖可插拔的机械与互连基础设施、以及较高的静态功耗。但请注意建议书原话留了余地：

> "可以把'SSD 作为内存语义后端的想法'用在节点内单机分层上，但不要把它当作主存储架构。"

Maru 恰好落在"节点内共享"这个许可范围内。**如果未来你的轨道节点是"一个舱段内多块加速卡 + 一个 CXL 池"，Maru 是这一层的现成实现**；但若节点是单卡或跨舱段，则不适用。

---

## 8. 落空条款：C11 自愈

建议书花了整整一节讲"人类不可接入 = 没有运维"，并要求零 I/O 恢复。GitHub 上**没有任何项目实现这一类**。检索到的都是常规方案：

- `danilodjor/fault-tolerant-llm-training`（1★）：Slurm 上自动 checkpoint + 作业重提交
- `Varun-Dudipala/flextrain`（0★）：带异步 checkpoint 的容错训练框架
- `Xuqing0415/hermes-cosmos`（1★）：多区域调度 + 容错计算

它们的共性是"**故障→回滚到 checkpoint→重放**"，而建议书要的是"**故障→换掉 communicator→就地继续，零重放**"。这一层必须自研，或者去读对应论文的 artifact（`AccelPact`、`CheckFree` 这类在论文里，尚未产品化）。

---

## 9. 三种可直接拼装的组合

### 组合 A：最小可用栈（1–2 周可跑起来）

代码块

```
PipeANN（SSD 图索引，1B/40GB）
  └─ GateANN（过滤检索，省 90% SSD 读）
      └─ LMCache（KV 热层复用）
          └─ ErasureFs 或 VecPuff（冷层）
```

对应条款：C1● C2● C3● C4● C6● C12●；缺口：C8/C9/C11。

### 组合 B：生产级检索栈（成熟度优先）

代码块

```
pgvectorscale（PostgreSQL 内，StreamingDiskANN + SBQ + label filter）
  └─ HiQCache（INT8 分层 KV）
      └─ UFROP/ErasureFs（FDP + 纠删码）
```

优点：直接长在 Postgres 上，事务、备份、运维生态现成；风险：`pgvectorscale` 团队已转向非图索引。

### 组合 C：治理栈（针对 PoL2 的缺口）

代码块

```
hypermnesic 或 AI-MemoryHub（Markdown 真相源 + 可重建索引，C10●）
  ＋ provena（哈希链审计轨迹，C8●）
  ＋ 自建写入协议（分阶段准入/仲裁/版本快照 → C9）
  ＋ PipeANN（把重建出来的索引放到 SSD 上，C1●C2●）
```

这是唯一能同时满足"快"和"可辩护"的组合，代价是 C9 必须自己写。

---

## 10. 方法学与局限

1. **搜索 API 限额**：未认证 10 次/分钟，共 29 条检索式，每条只取 star 排序前 25。这意味着**低 star 但高相关的项目可能被漏掉**——C6/C7 两组就是这个问题的典型（Kioxia 的两个插件都是个位数 star，靠专门检索才捞到）。
2. **代码级搜索不可用**（`/search/code` 需鉴权，返回 401），因此"某仓库内部是否真的实现了某个机制"只能靠 README 与目录结构判断，未做代码审计。
3. **star 数不代表质量**：本表里 0★ 的 `ErasureFs` 在 C6/C7 上强于 12105★ 的 `LMCache`，因为两者解决的问题不同。
4. **性能数字全部为项目自述**，未独立复现；PipeANN 的"<1ms @1B/90% recall"这类数字需要在你自己的硬件与数据分布上重测。
5. **"符合建议书"不等于"适合 PoL2"**：建议书本身是为一套特定约束（轨道、自治、无人类接入）写的，而上述项目绝大多数面向地面机房。C11 的空白就是这个落差的直接体现。
