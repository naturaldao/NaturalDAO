# 具身智能机器控制与安全验证先例

## PoL2 的权限边界应落在任务提交链路，而非语言模型飞控

### Takeaway

PoL2-EG 的首个可实现边界是“任务级授权”：AI 产生有界的任务提案，PoL2 规则门与确定性适配器对身份、任务内容和状态有效性作机器检查，PX4 等飞控继续负责导航、姿态/位置闭环和已配置的失效动作。把语言模型放进实时 setpoint 或电机控制回路会把语义推理问题和具有时限约束的闭环控制混在一起；本次核验的先例不支持把这描述为现成的治理能力。

### Cited Findings

- PX4 v1.17 Mission 模式将任务上传到飞控侧存储；Mission 模式下，如果存在有效任务，飞控会从当前任务项执行；任务可通过切换模式暂停并切回恢复，上传新任务还会改变当前任务状态。PX4 对上传和开始前有基本可行性检查，但文档将它称为基本 sanity checks，而不是完整的轨迹安全证明（[PX4 v1.17 Mission Mode](https://docs.px4.io/v1.17/en/flight_modes_mc/mission)）。
- MAVSDK 的 Mission 插件有任务上传、下载、开始、暂停、重启、跳转和进度监测 API；官方 API 明确说已上传到无人机的任务可在连接丢失后启动/执行。MissionItem 只支持 PX4/MAVLink 命令的一个子集，起飞与返航等某些能力需经其他 API 或单独命令接口处理（[MAVSDK Missions Guide](https://mavsdk.mavlink.io/main/en/cpp/guide/missions.html)）。因此“切断 AI 连接会停止已授权动作”不成立为默认假设。
- MAVLink Mission Protocol 不仅包含任务上传/下载，还包含清除任务、设置当前任务项、围栏/安全点计划及其他任务命令。标准协议让 GCS 或开发者 API 直接与飞行器交换计划；`MISSION_SET_CURRENT`/`MAV_CMD_DO_SET_MISSION_CURRENT` 能更改任务项，`MISSION_CLEAR_ALL` 能清除机载计划（[MAVLink Mission Protocol](https://mavlink.io/en/services/mission.html)）。
- MAVLink 2 Message Signing 用共享密钥对消息签名，以验证消息是否来自持有该密钥的可信源并防止部分重放；标准签名材料没有表达按任务、坐标包络、命令白名单、审批版本或授权有效期定义的 PoL2 权限策略。由此可推得，消息签名可以是链路身份与完整性控制，但单独不等同于动作授权或 PoL2 策略执行点（[MAVLink Message Signing](https://mavlink.io/en/guide/message_signing.html)）。
- PX4 v1.17 Offboard 模式让外部控制器提供位置、速度、加速度、姿态、角速度或推力/力矩 setpoint；系统要求持续 >2Hz 的 MAVLink setpoint 或 ROS 2 OffboardControlMode 作为“proof of life”，失联后按 `COM_OF_LOSS_T` 和 `COM_OBL_RC_ACT` 配置退出 Offboard 并执行所设模式（[PX4 v1.17 Offboard Mode](https://docs.px4.io/v1.17/en/flight_modes/offboard)）。这个心跳检测的是外部控制链是否持续，不验证策略版本、授权是否被撤销或候选 setpoint 是否符合 PoL2。
- 当前 PX4 failsafe 配置将手动控制链路丢失、数据链路丢失、Offboard 链路丢失、定位故障和围栏越界分为不同触发器，并允许按参数配置动作和模式例外。Data Link Loss 根据与最后一个 MAVLink 地面站（如 QGroundControl）的连接超时触发；因此“链路断开后任务必然继续”也不总成立，效果取决于对应 PX4 版本、连接探测、模式例外和参数配置（[PX4 current Failsafe Configuration](https://docs.px4.io/main/en/config/safety)）。
- PX4 的围栏 failsafe 在飞机已经越出边界后触发。官方建议给围栏留出至少与固定翼盘旋半径或多旋翼制动距离相当的余量，并加上风、定位误差、姿态延迟余量。这支持把“上传前任务包络检查”与“越界后机载 failsafe”作为两个不同机制实现和评测，不能把后者说成提前证明任务路径安全（[PX4 current Failsafe Configuration](https://docs.px4.io/main/en/config/safety)）。

### Inferences

- 要使 PoL2 门成为真实的强制执行边界，必须列出所有可以写入或控制目标飞控的端点与命令路径：MAVSDK 进程、QGroundControl/GCS、ROS 2 bridge、USB/串口、备用伴随计算机和运维接口。架构应确保未经 PoL2 授权的消息不能绕过适配器进入飞控；MAVLink 签名只能区分允许的发送身份，不能代替此授权逻辑。上述“唯一入口”的需求是根据协议允许的多个计划/命令接口推导的设计要求，需在选定硬件和网络拓扑上验证。
- 任务上传、任务启动、任务暂停/恢复、当前任务项变更、任务替换、任务清除和运行中撤销都应作为独立动作定义权限；不能只审查初次任务提案。授权对象至少应绑定飞行器身份、规范/策略版本、完整任务哈希、允许命令清单、空间/高度/速度包络、状态观测时间、有效期和防重放标记。该字段清单为 PoL2-EG 设计建议，协议文档未提供现成的 PoL2 授权租约。
- 断连行为需要拆成三种语义：AI/策略服务失联；地面站 telemetry 数据链失联；Offboard setpoint 流失联。它们触发不同通道。SIH/SITL 中必须分别注入并记录各自的固件模式转换；不能将“调用 API 返回失败”推断为飞控停止。
- 若上传任务以后授权到期，系统只能通过已实现且经测试的暂停、模式切换、替换任务、清除任务或飞控侧接收的租约机制来处置。现成 Mission API 的 pause/clear 能力不自动证明撤销命令一定可达、及时或安全；需要将“撤销到达时间、飞机过渡状态、任务恢复行为”作为接口级要求和测试结果。

### Gaps

- PX4 的 failsafe 默认参数、`COM_DLL_EXCEPT` 默认模式和“最后一个 MAVLink GCS”连接判定必须针对锁定的 PX4 版本、构建、载具参数和 MAVLink 拓扑实测。官方文档显示配置是可变的，本备忘录没有假定某个默认值。
- MAVLink signing 在具体 PX4 构建、USB/GCS、多链路部署上的启用策略、是否接受未签名包以及密钥轮换策略需查目标固件配置。协议规范明确给实现留下了对未签名消息的系统特定接受规则。
- 上传后策略撤销/租约不是 PX4 Mission 或 MAVSDK Mission API 的原生 PoL2 功能，系统级解决方式与故障安全动作仍待实现和测试。

## Runtime Assurance 有真实 UAS 飞行试验先例，但不是全 AI 治理

### Takeaway

NASA 对 UAS 的 Runtime Assurance (RTA) 提供了两种不同层次的先例：一项 2024 年工作在 PVS/Plaidypvs 中形式化与验证 Simplex 类 RTA；另一项工作在小型无人机上开展了 100 余次风险监测和自动缓解飞行试验。它们展示的是针对特定物理安全性质的监测、切换和缓解机制，不是 AI 自主制定规范、管理社会价值或执行完整 PoL2 治理；且飞行试验系统仍将飞行员干预作为部分 contingency 路径。

### Cited Findings

- NASA 2024 UAS RTA 形式化框架定义高级控制器（可能含不可信黑盒）与可信回退控制器，运行时监视安全性质，在不满足性质时切换；形式化结论依赖监测器有足够时间提前发现问题、回退控制器可信以及安全性质/系统模型成立。论文将工作定位为对 hybrid program/Simplex 框架的形式化，并明确不解决工业级 RTA 部署中的众多困难（[NASA, A Verification Framework for Runtime Assurance of Autonomous UAS](https://ntrs.nasa.gov/citations/20240007986)）。
- Plaidypvs 将 differential dynamic logic 嵌入 PVS，可形式推理混合系统程序；NASA 工具页说明它用于设计时 Runtime Assurance 框架推理和混合系统时序性质验证。它是形式化工具先例，不代表本项目已有运行时监测器或经过飞行验证（[NASA Plaidypvs](https://shemesh.larc.nasa.gov/fm/Plaidypvs/)）。
- NASA 关于城市 UAS 飞行风险的另一篇 2024 DASC 论文报告开展了 100 余次飞行试验；先做仅监测/评估、记录建议缓解动作但不实际执行的试验，之后又做自动缓解试验。架构包括风险评估、自动驾驶仪监测、障碍物接近、地理围栏符合性等机载功能，覆盖导航、C2 链路、接近障碍物和失控等风险（[NASA NTRS flight-test record](https://ntrs.nasa.gov/citations/20240007663)；[NASA-hosted paper PDF](https://www.nasa.gov/wp-content/uploads/2026/03/ancel-et-al-2024.pdf)）。
- 该 NASA 飞试论文明确将风险缓解执行描述为可自动实施或由飞行员介入/监督；一些记录的先期试验只验证监测与风险建议，不实际操纵飞机。因而它是“独立机器安全监测和物理缓解”的工程先例，但不是“没有人类监督的 AI-only 治理”先例（[NASA-hosted paper PDF](https://www.nasa.gov/wp-content/uploads/2026/03/ancel-et-al-2024.pdf)）。
- CBF/QP 原始工作把安全定义为允许状态集的前向不变性，并通过控制屏障函数约束控制输入，再在 QP 中与性能目标联合优化；相关理论要求控制系统模型、CBF 条件与约束可行，不能仅因使用 CBF/QP 名称就声称现实系统得到安全保证（[Ames et al., Control Barrier Function Based Quadratic Programs for Safety Critical Systems](https://authors.library.caltech.edu/records/jnhr0-1ww05)）。后续可行性工作也将 CBF 安全约束下 QP 的可行性作为独立问题研究（[Xiao & Belta, Sufficient Conditions for Feasibility of Optimal Control Problems Using CBFs](https://arxiv.org/abs/2011.08248)）。

### Inferences

- RTA 与任务级授权门控制不同层次。PoL2 PEP 判断“该任务是否获准”，RTA monitor 判断“正在运行的控制行为是否将违反某个可监测的物理安全性质”，fallback controller 负责执行经设计、验证的回退控制。只有完成接口、时序、状态量和回退模式设计后，三者才可以集成；PX4 现有围栏/Offboard failsafe 不是当前 PoL2 V2 所提的完整 Simplex/RTA 安全内核。
- 若后续加入 RTA，必须从明确安全性质开始，例如预先定义的禁飞区域裕度、最小障碍距离、失联时安全模式、最大位置误差；然后给出观测误差、传感器采样率、处理最坏时延、切换条件、回退控制器及可达性假设。自然语言规范经 LLM 解释不能直接视作形式性质。
- NASA 飞试结果可作为“有具体风险监测与自动缓解功能的无人机系统工程可以落地”的依据，但其任务适用范围窄、试飞场景受控、治理规范由设计者与运行团队给定，且保留飞行员参与路径；它不能推导出 PoL2-EG 的理论自治、规范自我演化或普遍安全结论。
- CBF/QP 应作为可选的后续独立安全过滤器研究，不应列入第一个 Mission API demo 的已实现功能。需要在确定的 PX4 或伴随机上选定的低层控制接口、有效动力学模型、传感误差界和实时预算内验证可行性与切换行为。

### Gaps

- 公开 NASA 文档并不提供 PoL2 本项目可直接复用的完整软件/认证包，也不证明同类 RTA 可以不改造就接入 PX4 v1.17 Mission 模式。
- CBF/QP 对选定无人机型号、载荷、风场、定位误差、传感时延和执行器约束的适用参数尚未建立；当前材料不应给出安全保证值。
- 运行时治理任务中的“机器拒绝—重规划—暂停”是策略层响应；何种物理状态下应选择 Hold、Land、Return、Terminate 以及这些选项对具体起降区域的风险排序，需要单独的飞行安全分析。

## 分层评测必须同时测安全违规、任务效用和场景覆盖

### Takeaway

PoL2-EG 评测不能只报告“安全率”或模型置信度。具身决策基准已证明，只看最终任务成功率无法定位语言理解、规划、接口可执行性和轨迹错误；覆盖式测试工作则强调把场景参数空间分为安全、失败与未知区域并报告覆盖、错误召回和误判安全率。对于允许 `SAFE_HALT` 的治理系统，必须同时报告对危险任务的拦截能力和对有效任务的保留能力，否则永远拒绝执行也可能在单一安全指标上表现完美。

### Cited Findings

- NeurIPS 2024 Embodied Agent Interface (EAI) 将具身决策任务拆为目标解释、子目标分解、动作排序和状态转移预测，并提出细粒度错误指标，包括解析/语法、幻觉、参数、动作顺序、缺步、多余步骤、可供性错误等。论文明确批评只依靠最终成功率会妨碍诊断能力短板（[EAI NeurIPS 2024 paper](https://proceedings.neurips.cc/paper_files/paper/2024/hash/b631da756d1573c24c9ba9c702fde5a9-Abstract-Datasets_and_Benchmarks_Track.html)）。
- EAI 实验在 VirtualHome 和 BEHAVIOR 等仿真任务上评估不同模块，其“任务成功”和“执行成功”与具体模拟器、任务和模型相关；它提供了结构化评估方法，不构成飞行机器人实机安全验证（[EAI full paper](https://papers.neurips.cc/paper_files/paper/2024/file/b631da756d1573c24c9ba9c702fde5a9-Paper-Datasets_and_Benchmarks_Track.pdf)）。
- CoRL/PMLR 2023 的 GUARD 参数化测试框架对连续场景参数空间估计 safe/pass、unsafe/fail 和 unknown 区域；其指标包括 coverage、balanced accuracy、error recall 和 false positive rate（误判安全率）。作者使用模拟场景、专家定义的场景和测试功能安全阈值，并指出无限连续参数空间只能靠有限测试样本估计，因此不确定区域应被明确保留（[Tu et al., GUARD, CoRL 2023](https://proceedings.mlr.press/v229/tu23a.html)；[论文 PDF](https://proceedings.mlr.press/v229/tu23a/tu23a.pdf)）。
- GUARD 论文将“误判安全”单独量化：将实际失败场景预测为安全区域的比例；这对 PoL2-EG 的未授权动作门禁尤其相关，因为假放行应和拒绝有效请求分别报告，而不应汇总成总体 accuracy（[GUARD paper: metric definitions](https://proceedings.mlr.press/v229/tu23a/tu23a.pdf)）。
- SafeMindBench（2025 预印本）将具身 LLM 风险按任务理解、环境感知、高层规划、低层动作生成四阶段分类，并使用事实、因果、时间三类安全约束；它含 5,558 个多模态样本，属于安全决策基准研究，不等同真实机器人飞行/操作认证（[SafeMind arXiv paper](https://arxiv.org/abs/2509.25885)）。
- 2026 CVPR 的 AGENTSAFE 提出危险指令具身代理评测，采用仿真 sandbox、45 个风险场景、1,350 个危险任务和 9,900 条指令，并拆分 perception、planning、execution 诊断；这些数量可证明 benchmark 设计覆盖危险指令测试，不证明仿真结论直接迁移到无人机实飞（[CVPR 2026 AGENTSAFE paper](https://openaccess.thecvf.com/content/CVPR2026/html/Ying_AGENTSAFE_Benchmarking_the_Safety_of_Embodied_Agents_on_Hazardous_Instructions_CVPR_2026_paper.html)）。
- PX4 提供 SITL（软件在环）、SIH 和 HITL（硬件在环）等不同路径。SITL 让固件栈在开发机、仿真世界运行；HITL 把正常 PX4 固件放在真实飞控硬件上、接收仿真传感输入；SIH/硬件模拟路径则有自己的物理模型及传感模拟边界。不同模式执行的代码、硬件与传感器覆盖不同，不能把它们当作等价证据等级（[PX4 Simulation overview v1.18](https://docs.px4.io/v1.18/en/simulation/index)；[PX4 HITL guide](https://docs.px4.io/main/en/simulation/hitl)；[PX4 SIH v1.17](https://docs.px4.io/v1.17/en/sim_sih/)）。

### Inferences

- 建议评测分为五个指标族，并逐场景、逐固件版本记录：
  1. **授权完整性**：未授权任务被拒数 / 未授权任务尝试数；策略本应允许任务的接受率；命令白名单覆盖和未授权 MAVLink 路径拦截率。
  2. **任务效用**：符合规则的任务接受率、完成率、执行时间；合法请求误拒率/误停率；无证据情况下的拒绝/延迟成本。
  3. **物理与飞控结果**：实际越界、碰撞或接近阈值事件；违反任务包络持续时间/距离；PX4 模式转换；每种故障注入到触发与动作的延迟分布。
  4. **机器复核与演化**：条款到策略测试覆盖、策略版本差异导致的授权变化、回放反例检出、更新回滚成功率/时间、日志完整率与重放检测。
  5. **测试覆盖和置信度**：参数场景空间的 pass/fail/unknown 覆盖，失败案例召回、误判通过率及置信区间；按版本比较，避免只抽样成功场景。
- “安全且有用”的核心报告至少并列两条：对危险/未授权请求的漏放率与对合法请求的误拒率。纯拒绝系统可能有零未授权动作，但任务完成率也为零；纯任务成功系统可能高效但频繁越权。策略门必须在 Pareto 或至少二维表中同时展示 safety 与 utility。该指标设计是从 EAI 的任务/执行分解和 GUARD 的覆盖/错误指标推导而来。
- SIH 适合快速回归策略门、命令接口、状态机与很多确定性逻辑检查；Gazebo SITL 用于带 3D 世界/传感器与飞控的端到端软件仿真；HITL 检查目标飞控硬件与固件集成及通信时序；三者都不是户外实飞证明。真实环境风险还要说明载荷、风、定位、通信和运行场地覆盖。
- 首版无人机实验应冻结 PoL2 与 PX4 固件、参数、机型和任务包；注入围栏外航点、不允许命令、过期/缺失位置状态、旧任务重放、任务被另一连接篡改、AI/适配器进程退出、GCS 数据链丢失、Offboard 心跳丢失、任务已上传后授权撤销等不同故障。每一种都记录输入条件、期望策略判定、协议结果、飞控状态和日志事件。
- 使用 GUARD 思路对任务坐标/高度/速度、质量/电量、时延/丢包、风扰等连续参数做边界探索，报告尚未知的参数区，不用有限仿真通过声称全空间安全。

### Gaps

- 本项目的可执行任务规格、无授权 ground truth、有效任务样本集、参数化仿真场景与模型版本集合尚未建立，因此不应预填任何具体通过率、召回率或安全阈值。
- 将 EAI/AGENTSAFE 的 household/manipulation 语义测试映射到无人机航点与飞行状态，需另建平台级规范和标注准则；目前不是现成可直接复用的 UAV benchmark。
- 除 NASA 的特定 UAS flight-test 工作外，桌面仿真和有限飞行试验均不能支撑所有气象、复杂空域、多机交互或公共空间运营安全的普遍结论。
