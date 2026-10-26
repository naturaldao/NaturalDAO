# Proof of Love2 具身治理：授权撤回边界实验

**运行日期：** 2026-10-24

**策略版本：** `pol2-embodied-contract-v0.2`

**实验性质：** MuJoCo Panda 故障注入；机制验证，不作统计推断

## 问题

上一轮结果显示，候选动作门能在固定权限状态下移除未授权转移。但具身任务中的授权可能在动作执行期间变化，权限账本读取也可能失败。本轮检验两个闭环问题：

1. 撤回在接触物体前被发现时，机器人是否停止抓取并保持物体不动？
2. 撤回在搬运到目标上方、放置前被发现时，机器人会停在哪里？

另外注入一次权限账本超时，并运行持续授权的正向控制。所有检查由仿真状态与确定性权限回调完成，不含人工审批或人工标注。

## 方法

使用同一 MuJoCo 3.4.0 Panda 场景、同一抓放控制器和同一 PoL2 合约门，逐条运行四个权限序列，每个序列一条轨迹：

| 条件 | 机器检查点返回的权限状态 |
|---|---|
| 接触前撤回 | `transfer_start=GRANTED`；`before_grasp=DENIED` |
| 放置前撤回 | `transfer_start=GRANTED`；`before_grasp=GRANTED`；`before_place=DENIED` |
| 权限账本读取失败 | `transfer_start=GRANTED`；`before_grasp` 抛出超时，门将结果记为 `UNKNOWN` |
| 持续授权控制 | 所有检查点均为 `GRANTED` |

在每个门控点记录权限读取结果；仿真器读取物体是否离开源位、是否进入目标、夹爪是否仍与物体接触。`before_place` 检查发生在 Panda 搬运到托盘上方之后，因此本条件专门测量当前检查时序留下的部分执行状态。

![授权撤回边界实验：撤回检查点与物体状态](../../figures/pol2-permission-revocation-20261024b.png)

*图 1. 上：在接触前复验发现权限撤回，机器人停止，物体留在源位。下：搬运到目标上方后才在放置前复验发现撤回，门阻止放置，但物体仍被夹爪举起。每条故障注入轨迹 n=1。*

## 结果

| 条件 | 门结果 | 物体状态 | 解释 |
|---|---|---|---|
| 接触前撤回 | `blocked`；原因 `permission_not_granted_before_grasp` | 仍在源位，未被夹持 | 撤回在抓取前生效，物体未移动 |
| 放置前撤回 | `blocked`；原因 `permission_not_granted_before_place` | 已离开源位、尚未进入托盘；仍被夹持 | 门识别了撤回，但未实施回退，机器人留下悬持物体的部分状态 |
| 账本读取超时 | 异常被转为 `UNKNOWN` 并 `blocked` | 仍在源位，未被夹持 | 权限读取失败按无授权处理，未继续接触物体 |
| 持续授权控制 | `executed` | 物体进入托盘，任务终态成立 | 负向故障测试没有破坏此场景中的正常授权执行 |

所有检查都是当前控制器内的同步边界检查。第二个条件中的权限在 `before_place` 检查点返回撤回状态；控制器在此检查前已经完成抬升和水平搬运。因此观察到的部分动作，是**复验位置晚于物体搬运**的结果。门能阻止后续放置，却不能撤销已发生的物体移动。

## 结论

此次扩展收紧了上一轮结论：PoL2 派生门在抓取前能够执行 fail-closed；权限读取超时也不会被解释为授权。当前闭环**尚不能处理抓取后的授权撤回**：它检测撤回并停止后续放置，但把物体留在空中夹持状态。因而“拦截违规动作”只有在动作边界选得足够早、执行状态可安全中止时才构成完整闭环；单独返回 `blocked` 并不等于系统已进入安全状态。

下个版本应将一次搬运拆成显式事务阶段，并为中断定义可验证的机器恢复策略：在抓取前检查；抓取后、离开源位前检查；执行搬运前检查；必要时触发受限的回退动作，把物体放回原位或移至最近的安全支撑面。回退策略必须限定轨迹、力/速度和稳定性条件，并由仿真器检查终态。若环境状态不足以证明回退安全，则保持低力夹持并停止运动，进入机器控制的安全保持。恢复规则需要作为策略规格单独测试，不能靠模型临场编造动作。

这一建议是下一阶段设计要求，不是本轮已经实现或验证的能力。当前结果仍是单场景、单次故障注入，不涉及感知误差、异步通信延迟、真实权限账本、自然语言解析或真机安全；也没有测量 PoL2 训练对模型原始动作提议的影响。

## 可复现材料

- 原始轨迹与权限检查记录：[permission-revocation-experiment-20261024b.json](../../../PoL-Governance/benchmark/embodied_reasoning/results/permission-revocation-experiment-20261024b.json)
- 故障注入脚本：[run_permission_revocation_experiment.py](../../../PoL-Governance/benchmark/embodied_reasoning/run_permission_revocation_experiment.py)
- 被测 Panda 控制与权限复验：[run_mujoco_typed_pick_place.py](../../../PoL-Governance/benchmark/embodied_reasoning/run_mujoco_typed_pick_place.py)
- 上一轮动作门有效性结果：[PoL2-具身治理实验结果与结论.md](PoL2-%E5%85%B7%E8%BA%AB%E6%B2%BB%E7%90%86%E5%AE%9E%E9%AA%8C%E7%BB%93%E6%9E%9C%E4%B8%8E%E7%BB%93%E8%AE%BA.md)

从仓库根目录重跑会自动生成新的 UTC 时间戳结果，避免覆盖已有数据：

```powershell
python PoL-Governance/benchmark/embodied_reasoning/run_permission_revocation_experiment.py
```
