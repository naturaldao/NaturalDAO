# 研究图件

[返回研究总入口](../README.md) · [具身研究索引](../Embodied/README.md)

此目录保存具身实验报告共用的 PNG/PDF 与[撤权恢复重绘脚本](plot_revocation_recovery_experiment.py)。保留这个输出位置，让评测脚本和已有结果中的图件路径继续可用。

阅读实验请从具身研究索引进入对应报告，报告会链接所采用的确切图件和逐轨迹 JSON。文件名中的日期与字母后缀用于区分运行；存在多个后缀不表示它们都进入当前报告，也不能据此判断实验优劣。

本次整理保留已有图件和未提交的运行产物。后续新增图件请同步到对应报告；未经核对的重跑版本不直接替换正文使用的图。

| 图件 | 对应报告 | 内容 |
|---|---|---|
| [PoL2 理论行为能力广域评测](pol2-full-theory-behavioral-competence-20261026.png)（[PDF](pol2-full-theory-behavioral-competence-20261026.pdf)） | [评测报告](../Embodied/02-实验设计与审计/PoL2-理论行为能力广域评测.md) | 底座、规则摘要注入、参数微调的候选处置命中率及阶段切片 |
| [PoL2 参数微调因果消融](pol2-sft-parameter-ablation-20261028.png)（[PDF](pol2-sft-parameter-ablation-20261028.pdf)） | [消融报告](../Embodied/02-实验设计与审计/PoL2参数微调因果消融实验.md) | 比较完整 SFT 与保留训练头、恢复初始 LoRA 的条件；展示总体及阶段差异。重绘脚本位于 [评测目录](../../PoL-Governance/benchmark/pol2/plot_sft_parameter_ablation.py)。
| [PoL2 规则字段双向激活交换](pol2-field-activation-interchange-20261026.png)（[PDF](pol2-field-activation-interchange-20261026.pdf)） | [激活交换报告](../Embodied/02-实验设计与审计/PoL2内在规则表征双向激活交换实验.md) | 五个单字段反事实对的双向激活交换，以及授权因素的逐 block 干预定位。探索性机制诊断，不代表完整 PoL2 理解。
| [PoL2 未见规则组合泛化](pol2-rule-composition-generalization-20261026.png)（[PDF](pol2-rule-composition-generalization-20261026.pdf)） | [组合泛化实验](../Embodied/02-实验设计与审计/PoL2规则组合泛化实验-未见规则组合.md) | 单因素训练后，在未见的 134 个多规则状态上比较合约 SFT 与 task-only；准确率与动作可接受率分开展示。 |
| [PoL2 训练效果优化消融](pol2-training-improvement-ablation-20261026.png)（[PDF](pol2-training-improvement-ablation-20261026.pdf)） | [训练消融报告](../Embodied/02-实验设计与审计/PoL2训练效果优化消融实验.md) | 成对排序损失、状态均衡验证和训练轮数的配对种子比较；分开展示总体与动作类别准确率。复用已公开组合测试，属于探索性结果。 |
