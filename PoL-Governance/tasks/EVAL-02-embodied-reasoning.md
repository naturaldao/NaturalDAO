# EVAL-02：PoL2 × 类型决策模型具身任务执行验证

| 字段 | 内容 |
|---|---|
| 领取人 / Agent | Codex |
| 状态 / 最近进展 | 进行中；长度匹配筛查已由 PR #46 合并到 `main`；正在设计 MuJoCo 物理闭环下一阶段 |
| 范围 | 主问题：固定类型决策模型和执行接口，比较 generic 与 PoL2 条件下机器人是否更遵守约束，同时保留合法任务成功率；文本配对试验仅作先导筛查 |
| 当前数据 | `benchmark/embodied_reasoning/cases.jsonl`，16 条自建合成案例，8 个配对场景族 |
| 已运行 | Ollama 文本层配对筛查；另以 Kev-0.8B `choice` 接口在本机 CPU 决策，接入 VirtualHome Evolving Graph 执行 3 个符号动作并校验目标状态。具体 provenance 和结果见 Research 报告及 `benchmark/embodied_reasoning/results/typed-simulator-pilot-20261023b.json` |
| 边界 | 当前闭环只有 1 个场景族、2 个配对状态；授权门手工编码；仅符号状态转移，不含连续物理/传感器，不是统计效能估计，也不声称读取隐式 CoT、AGIBOT 复现或实机验证 |

## 进展记录

- 2026-10-23：核对现有 PoL2 评测器只评价规范分类与动作，不覆盖具身决策过程。完成 `qwen2.5:7b` 两轮配对试验。修订标签和计划测量后，第二轮 generic/PoL2 状态准确率分别为 8/8、7/8，计划准确率 7/8、8/8，动作准确率均为 8/8；仅 4 个配对族，不能推断 PoL2 稳定改善推理。
- 2026-10-23：扩展为 16 条案例、8 个配对族，增加计划—动作兼容性与状态—计划—动作联合指标；使用 Qwen2.5 7B 与 Llama 3.1 8B 各运行两条件。Qwen 的 PoL2 条件计划、动作与联合正确率较高；Llama 的计划/动作指标较高但状态准确率下降。结果支持部分任务中运行时规则会改变外显选择，不支持普遍提升推理能力。完整数字和数据可用性核验见 `Research/PoL2具身推理过程初步验证.md`。
- 2026-10-23：核验第四期 Physical Reasoning 的媒体发布公告；当前 Hugging Face 文件树未见该主题独立目录，故本轮仍用自建合成案例，不称 AGIBOT 复现。
- 2026-10-23：完成 Kev-0.8B typed `choice` → 授权门 → VirtualHome Evolving Graph → 目标终态核验的单任务闭环。PoL2 提示降低拒绝授权状态的 `P(deliver)`（0.2310→0.0595），但也使授权状态从执行转为等待，合法任务由完成变为未完成。强制非法 deliver 时，确定性门成功在执行前阻断；无门控时符号模拟器完成了转移。同日把 Kev 接入既有 16 个合成案例：generic / PoL2 各 13/16 动作匹配预设标签，各有 1 次禁行动；动作只在 2/16 个案例变化，1 个转对、1 个转错，净准确数不变。结果支持“规则文本会改变局部类型化决策分布”，不支持 PoL2 净效益结论。详见 Research 报告和 `benchmark/embodied_reasoning/results/` 下两个 JSON 结果。
- 2026-10-23：对上述 16 案例新增 generic / 长度匹配中性 / PoL2 三条件筛查。中性与 PoL2 的输入 token 在 16/16 案例逐条相等；三组均为 13/16 动作正确、1 次禁行动。中性与 PoL2 在 4/16 案例选择不同动作，2 例由错转对、2 例由对转错，净变化为零。此对照降低了提示长度混杂，但不控制语义/措辞、oracle 编制偏差或跨任务/模型泛化。逐条结果在 `benchmark/embodied_reasoning/results/typed-case-screen-3arm-matched-20261023.json`；首轮差 1 token 的校准数据单独保留，不进入主比较。
- 2026-10-23：脚本语法、逐条结果 JSON 解析及 `git diff --check` 均通过。仓库规定的 `uv run --no-project --offline python tools/check.py` 已运行，但被既有 `datasets/general/coverage-gaps.md` 对仓外/未公开 `data/items.final.jsonl` 的断链检查拦截；本轮不上传该数据，也未修改相关数据报告。当前批次待集成，后续需扩展新的可执行场景并引入独立 oracle。
- 2026-10-23：本轮代码、合成案例、逐条输出和报告已推送至 GitHub 分支 `pol/EVAL-02/codex`，基线提交 `880b03f`；尚未合并，后续需扩展新的可执行场景并引入独立 oracle。
- 2026-10-23：PR #46 已 squash 合并；新一轮工程调研建议先以 MuJoCo CPU 跑单物体桌面抓放闭环，将 Kev 限制为有限宏动作选择，并把任务授权门与物理安全监视器分开。报告见 `Research/PoL2具身系统闭环落地.md`；该报告是工程方案，不代表 MuJoCo 已在本机验证。

## 下一步

1. 将对象授权与任务契约编译为显式状态字段和 fail-closed 约束；覆盖授权来源、范围、有效期、撤销和未知值，不允许模型直接自授权限。
2. 扩展到数十个可执行场景族与多种状态扰动，加入遮挡/计数/占用/进度、动作失败和感知不确定性；每组任务同时含合法可完成和应拒绝的反事实状态。
3. 扩大长度匹配三条件试验到新任务族与独立标注 oracle；比较 `TDM-generic`、中性提示、`TDM-PoL2`、`TDM-generic + gate`、`TDM-PoL2 + gate`，另设 deterministic baseline 和 always-deny；单独测提示作用和门控作用。
4. 预注册主指标：未授权动作执行率、合法任务成功率、错误拒绝率；附报动作数、延迟、失败恢复和任务族级配对不确定区间。扩样后再作总体结论。
5. AGIBOT 第四期数据文件、schema 和许可可核验后，另建数据适配流程，不把合成试验当作数据集复现；后续再转至具物理建模的仿真器与目标机器人。
