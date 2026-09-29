# 模型与训练共享

从 [清单](CATALOG.md) 选模型，也可带来新模型。当前推荐是实验起点，不是参与限制。

- 调研：更新清单，附一手来源、核查日期和未确定项；较长报告放 `models/research/<名称>.md`。
- 适配：在 `models/<名称>/` 放 [模型卡](CARD.template.md)、配置和复现脚本。
- 索引：在 [registry.json](registry.json) 登记；外部权重链接固定 revision，不提交大权重。
- 结果：按 [results](../results/README.md) 提交；不同框架、SFT/LoRA/RL/RLCD 等都可参加。

公开权重不自动意味着许可允许训练/分发，需分别注明底座、权重、代码和数据许可。原模型与适配模型的成绩分开记录。
