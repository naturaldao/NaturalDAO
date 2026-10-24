# PoL2 高密度存储：可靠性、安全边界与轨道约束

核验日期：2026-10-23。本文为 V2 的研究输入，未运行 PoL2 性能、断电、辐照或热真空实验；所有验收数值均为建议要求，不是测量结果。运行治理遵循全 AI 闭环，不加入人工审批、申诉或复核权威。资料范围限定为官方技术文档与 NASA/ESA 一手材料。

## 1. 高密度下如何定义持久性、纠错与自治恢复？

### Takeaway

高密度增加的不是单一“容量”风险，而是重建时间、后台写入、不可校正错误暴露和相关失效的耦合。应把提交确认、端到端校验、跨故障域冗余及可验证恢复分别设计；ECC、RAID/纠删码、日志和备份不能互相替代。

### Cited Findings

- SQLite 在 WAL 模式下，`synchronous=FULL` 每事务提交增加 WAL 同步；`NORMAL` 可在系统崩溃或断电后丢失近期已提交事务。WAL 本身不是“断电零丢失”的充分条件。— [SQLite PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous)
- SQLite 明确依赖操作系统及硬件诚实实现同步请求；同步失败或虚假完成不能由数据库自动识别。Windows 使用 `FlushFileBuffers`，Unix 使用 `fsync`。— [SQLite corruption guide, §3](https://www.sqlite.org/howtocorrupt.html)
- WAL checkpoint 需要先同步 WAL，再迁移到数据库，再同步数据库，最后复用 WAL；长读事务会阻碍 checkpoint 进度。— [SQLite WAL, §2](https://www.sqlite.org/wal.html)
- Ceph 文档给出纠删码容量放大为 $(k+m)/k$，多数部署至少需要 $k+m$ 个所选故障域；空间节约伴随恢复和小对象性能成本。本文引用的是官方 development 文档，落地必须锁定发行版。— [Ceph erasure coding](https://docs.ceph.com/en/umbrella/rados/operations/erasure-code/)
- Ceph 的 deep scrub 读取数据并验证校验和，而普通 scrub 不等价于读取全部数据。— [Ceph OSD configuration, scrubbing](https://docs.ceph.com/en/quincy/rados/configuration/osd-config-ref/)
- Micron 产品技术规格把耐久估计关联到使用条件、NAND 周期、WAF 和磨损均衡效率，而非只由 WAF 决定；本次搜索索引可读，但 PDF 直开被源站拒绝，因此不能引用其具体 TBW 数字。— [Micron 2650 technical specification](https://assets.micron.com/adobe/assets/urn%3Aaaid%3Aaem%3A25c43d17-622f-4be5-a33f-8e599da55043/renditions/original/as/2650-nvme-ssd-tech-prod-spec.pdf)

### Inferences

- **提交协议建议**：`accepted` 只代表接收；`durable_local` 必须在完整日志帧（长度、版本、序号、payload hash、校验码）写入并完成设备持久化屏障后返回；`durable_replicated` 必须在声明数量的独立故障域同步确认后返回。批量 group commit 可以摊销同步开销，但不能先回复持久成功再同步。超时可能已提交，重试使用全局 operation ID 幂等去重。
- **跨存储原子性建议**：SQLite WAL 只保护 SQLite；不能自动原子提交外部 JSONL、Parquet 和 ANN 文件。以单一权威提交日志决定事务状态：准备记录及对象先耐久化，提交记录最后耐久化；L1/L2 是带 `applied_lsn` 的可重建投影。崩溃恢复只重放完整 committed 前缀，截断撕裂尾帧，检查 referenced object 是否可用。重建索引先建立影子副本，校验后原子切换 manifest。
- **冗余分工建议**：NAND ECC 处理控制器可纠正的介质错误；端到端内容 hash 检测路径及静默损坏；RAID/EC 恢复介质/节点丢失；隔离且经过恢复验证的备份处理软件误写、污染传播和整域丢失。多个副本位于同一 SSD、控制器、供电、机柜或航天器，不应计为这些上层故障的独立副本。
- **编码布局建议**：热提交日志、元数据及小对象先用复制；冷归档以不可变大段封装后评估 EC。可测试 4+2（容量放大 1.5）或 8+3（1.375），但后者只是数学候选，不是 Ceph 默认推荐，更不能在不足 11 个对应独立故障域时宣称容忍 3 域故障。实际容错由放置规则、读取阈值及剩余分片状态决定。
- **写入账本建议**：分别测 `A_app=host_bytes/logical_ingest_bytes`、`WAF_device=NAND_bytes/host_bytes`，则相同口径下 NAND 写入约为逻辑摄入量乘两者；日志、索引合并、复制、EC、刷新、scrub 修复和备份各记账。TBW 是规定工作负载的产品耐久指标，不可再无条件除一次 WAF；若从原始 P/E 周期预算估算则需另建模型。温度、保留时间、读扰动、辐射、控制器与固件故障仍需单独评估。
- **自治状态机建议**：健康 → 可疑 → 隔离 → 从可信副本修复 → 全量校验 → 限量重新加入；反复失败则永久退役并调整容量预算。独立 verifier AI/服务只拥有验证和状态证明能力，不能悄悄改写权威日志。无可信副本时返回 `evidence_unavailable`，不得以另一个未校验版本“修复”证据。
- **恢复容量建议**：为重建预留空间、带宽、功率及写入寿命；容量阈值按 $C_{free}\ge C_{rebuild}+C_{WAL}+C_{merge}+C_{safety}$ 设定，不能仅用“磁盘未满”。按对象大小及设备区间轮转 scrub；热对象读取时验证，冷对象必须有覆盖期限；优先修复冗余不足，再做压缩和索引合并。

### Gaps

- 尚无 PoL2 SSD 型号、固件、PLP、ECC telemetry、NAND 原始写量可读性、目标寿命、温度范围和实际摄入速率，不能给出可信寿命年数或介质数量。
- 尚无故障域拓扑、恢复吞吐及故障相关性数据，不能计算“若干个 9”的持久性；零次注入丢失也不是无限可靠证明。

## 2. Merkle、不可变日志和 AI 协作的安全边界是什么？

### Takeaway

Merkle 证明回答“某字节是否属于已知根”，不回答“内容是否真实、来源是否可信、提交者是否授权”。不可变审计应针对状态迁移和承诺值设计，不能被解释为永久保存所有私密原文。

### Cited Findings

- RFC 9162 区分 Merkle inclusion proof、consistency proof 和带签名的树头；签名验证与包含验证是不同步骤。该 RFC 是 Experimental，借鉴其构件不等于 PoL2 兼容 Certificate Transparency。— [RFC 9162, §2.1 and §8](https://www.rfc-editor.org/rfc/rfc9162.html)
- NIST SP 800-88 Rev.2 于 2025 年 9 月发布，定义介质清理为在指定努力水平下使目标数据无法获取，并要求按信息敏感度建立相应程序；它不是对任何应用删除按钮的有效性认证。— [NIST SP 800-88 Rev.2](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

### Inferences

- **配置 A：受控地面单主体原型**。保留 V1 的不引入加密、多租户或 TEE 限制，但明确它只适用于受控进程、可信网络/主机与非敏感或已脱敏数据；校验、进程权限、解析边界、资源配额和软件供应链锁定仍需实现。这里没有恶意节点容错承诺。
- **配置 B：联网多 Agent 协作**。在网络、凭证泄漏、恶意/被污染 Agent、重放及证据投毒纳入威胁模型时，增加服务身份、传输认证、最小权限、写入配额、来源签名或可验证接收回执、隔离提交区和发布校验。加密及签名因新增威胁而选配，不以全局强制 TEE 代替威胁分析；多数副本一致不能证明知识正确。
- **配置 C：跨管理主体/对抗部署**。单列拜占庭模型、信任根、可作恶节点上限、共识协议及网络分区策略；未实现并验证前不得宣称 BFT。外部签名证明的是指定密钥作出的声明，密钥本身的授权与来源可靠度仍需版本化。
- **防分叉建议**：独立 verifier 持有历史 root/sequence 并比较 consistency proof；根值只在同一主机保存，攻击者可一起重写日志和根。是否使用签名、异域见证和多方 checkpoint 由配置决定。
- **隐私与保留建议**：把审计 envelope（随机 ID、事件种类、版本、删除原因码、承诺值）与可删除 payload/模型输入隔离；按数据类别设 TTL、训练许可、legal hold 状态与访问边界。删除动作追加审计事件，但实际擦除需要遍历对象、快照、备份、缓存、向量、索引和训练导出清单。持有可枚举原文的裸 hash 可能泄露关联，不能自动视为匿名化。
- **删除与重放建议**：删除后历史验证应可返回 `payload_expired` 或 `privacy_deleted`，保留承诺和处理记录，不能继续承诺原文完整重放。采用独立加密密钥的配置可评估 cryptographic erase，但需验证密钥及其备份均不可恢复；不加密配置不能声称通过删密钥删除。语料删除不自动清除已训练模型的记忆，模型撤回/重训/遗忘是另一个验证任务。
- **全 AI 发布闭环建议**：提议 Agent → 静态验证器/回放评估 → 独立 verifier → 分阶段发布 → 运行监测 → 自动回滚/隔离。角色与权限分离，所有决策留痕，流程中不加入人工审批或人工终审。

### Gaps

- 本次不评定具体司法辖区的删除义务；需依据实际部署与数据类别另行核查。上述隐私方案是工程建议，不是法律合规结论。
- 尚无 PoL2 的密钥托管、协作身份协议、拜占庭共识及机器独立性实现，不能承诺抗内部恶意或全链来源真实性。

## 3. 轨道部署需要哪些资格验证及可测门槛？

### Takeaway

轨道不是把地面服务器换一个地点；必须把器件、控制器、供电、固件、工作状态、任务辐射环境和热设计作为整体资格验证。地面软件故障注入和他人 SSD 辐照结果不能替代本型号、本配置的发射前试验。

### Cited Findings

- NASA NEPP 的 SSD 主动辐照研究在多个汽车/工业级整机 SSD 上测试 SEE/TID，强调不同工作状态会影响观察结果，完整 test-like-you-fly 不能只覆盖最常见操作；控制器等多部件封装增加解释困难。此结论支持试验方法，不支持把其剂量阈值迁移给 PoL2。— [Wilcox et al., Solid State Drive Radiation Assurance With Active Testing](https://nepp.nasa.gov/docs/tasks/075-EEE-Parts-Assurance/NEPP-2024-Paper-Wilcox-SSD-Radiation-Assurance-with-Active-Testing-20250000802.pdf)
- ESA 说明辐射下器件行为是 COTS 选型的重要依据，其案例中纠错并没有完全消除设计复位。该网页案例是 FPGA，不是 NAND/SSD 资格认证。— [ESA Radiation testing of EEE Parts](https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Shaping_the_Future/Radiation_testing_of_EEE_Parts)
- ECSS-Q-ST-60-15C Rev.1（2025-03-20）范围涵盖 TID、TNID/DD 与 SEE，并要求任务特定的 RHA 程序；本次正文站点暂时不可用，仅官方搜索缓存显示 scope，不引用条款细节。— [ECSS RHA standard](https://ecss.nl/standard/ecss-q-st-60-15c-rev-1-radiation-hardness-assurance-20-march-2025/)
- NASA 热控章节按太阳、反照、行星红外、内部生热、储热和辐射支出做能量平衡，并强调有限表面积、体积、功率和热密度约束。— [NASA Small Spacecraft Technology, Thermal Control §7.1](https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/)

### Inferences

- **热模型建议**：理想灰体面对有效冷背景的净辐射近似为 $Q_{net}=\epsilon\sigma A F(T_r^4-T_{env}^4)$；只有忽略背景、视因子为 1 时才简化为 $Q=\epsilon\sigma A T_r^4$。$T_r$ 必须用 K，$\sigma\approx5.670374419\times10^{-8}\ \mathrm{W\,m^{-2}\,K^{-4}}$。这是一阶估算，真实轨道还需多表面视因子、太阳/地球输入、遮挡、涂层寿命退化及从 NAND 到散热面的热阻。内部可以导热/热管传热，对外净散热以辐射为主，不应写成内部没有导热。
- **一阶示例，非 PoL2 实测**：$T_r=300\,K$、$\epsilon=0.9$、$F=1$、冷背景忽略时约 $413\,W/m^2$，排出 $1\,kW$ 需约 $2.42\,m^2$ 理想辐射面积；该值不能作为飞行设计值，更不能把 NAND 允许温度直接当作辐射板温度。
- **轨道配置 O（待资格验证）**：记录高度、倾角、寿命、屏蔽、太阳活动假设、通信窗口与功率曲线；在器件批次、固件版本、控制器和实际工作负载下测试静态保留、读写、GC、休眠唤醒、重启、复位、擦除与重建。区分可纠正 SEU、功能中断 SEFI、可能破坏性的 SEL，以及累计 TID/DD；屏蔽不是对全部粒子和失效模式的充分保证。
- **恢复策略建议**：硬件 watchdog 与隔离电源域处理挂死，写保护/只读模式保留可信语料，重建和 scrub 根据热/功率余量调度，保留关键审计与健康遥测。单星内多盘不能覆盖整星失效；跨星或地面副本取决于任务通信预算，离线期间不得宣称已完成异域持久化。
- **拟定验收表（不是结果）**：

| 范围 | 建议可测门槛与测法 | 边界 |
| --- | --- | --- |
| 本地提交 | 在 7 类写入阶段累计至少 1,000 次随机进程终止/断电测试；所有 `durable_local` 回执均可恢复且内容 hash 一致；重复 operation ID 只有一次逻辑提交 | 成功测试不证明未测固件/电源场景 |
| 跨域提交 | 单域强制丢失后所有 `durable_replicated` 记录可读取并验证；被隔离旧 writer 无法继续提交（fencing） | RPO=0 只适用于已确认的指定故障集合 |
| 备份恢复 | 每个发布周期在空环境从隔离快照+日志恢复；核对记录数、最后 LSN、manifest root、权限及采样证据 | 建议初始 RTO≤4 h，最终按规模和带宽设定 |
| 索引降级 | 损坏索引后不中断权威日志写入，切换健康副本或有界慢路径；重建后 Recall/过滤正确性达到发布门槛 | 恢复时间用真实索引尺寸实测，不能套 60 s |
| 静默损坏 | 定点/随机 bit flip 注入覆盖日志、对象、manifest、向量和 RAM 边界；不得静默接受损坏证据；有可信副本时自动修复 | hash 检测不等于具备修复来源 |
| scrub | 记录每字节最近成功验证时间及未覆盖容量；建议初始全量冷数据 30 天内覆盖，热点读时校验 | 按实测读预算、BER 和轨道环境调整 |
| 性能 SLO | 分别报告正常、单故障、重建、scrub、容量高水位下的 P99/P99.9、超时率和证据可用率 | 不能只测空盘平均值 |
| 寿命与功率 | 72 h 以上稳态混合负载，记录 host/NAND 写量、温度、功率、读写错误、待修复字节和可用余量 | 初始 72 h 为工程入口，非寿命认证 |
| 发射资格 | 任务环境 RHA、热真空、功率循环、故障隔离、通信失联自治、软件回滚试验均通过，并追溯器件/固件批次 | 未完成前只能称“轨道研究路线” |

- 服务可用性目标可先设月度 99.9%，但必须明确请求集合、超时、计划维护和证据缺失是否计失败；高风险请求在证据不足时 fail-closed/返回不确定，而不是为了可用率伪造成功。控制器 AI 有权降采样非关键遥测、暂停训练导出和延迟合并，不能删除未达到保留/冗余条件的权威证据。

### Gaps

- 当前没有 PoL2 的辐照、热真空、整机功率或轨道运行证据，不能声称 ECC 使 BER 降低某百分比、WAF≤1.3 可保证任务寿命，或某类 TLC/QLC 已适航。
- 发射前 SLO 必须由任务环境和负载反推；V1 的通用“BER 相对基线降低 50%”“无 checkpoint 60 秒恢复”等阈值没有本系统依据，应替换为上述可追溯试验要求。
