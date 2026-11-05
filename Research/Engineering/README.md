# 软件工程

[返回研究总入口](../README.md)

| 材料 | 主题 | 说明 |
|---|---|---|
| [NaturalDAO PoL Gate 软件工程设计](NaturalDAO%20PoL%20软件工程设计.md) | PoL Gate 架构与实现 | 组件结构、请求流程和实现约束，面向首次接触系统的工程师。 |
| [Memory Tax: Dissecting the Net Value of Agent Memory (PDF)](Memory-Tax-Dissecting-the-Net-Value-of-Agent-Memory-arXiv-2610.34073v1.pdf) | 智能体记忆评估 | He et al., arXiv:2610.34073v1 (2026-10-25)。比较专用记忆系统与朴素 RAG，并从 memory benefit、memory tax、faithfulness、accessibility 与 robustness 分析记忆的净价值。 |
| [Super-agent 架构调研](Super-agent架构调研.md) | 自治智能体架构 | 面向 NaturalDAO 自治系统的九层职能分解与四种主流 Agent 范式（ReAct / Plan-Execute / Reflexion / Multi-Agent）对比。笔记型材料，引用多为二手来源、部分数字未经核对，作为讨论底稿使用，结论以原文与后续独立核对为准。 |
| [MemT-1.0 复现、诚信审查与独立实验](MemT-1.0-复现/README.md) | 记忆原生模型复现 | 对 arXiv:2610.26825 的代码/权重/论文三线对齐复现与诚信审查（真实权重 CPU Q4），附容量、干扰、持久化、场景与 FP16 状态优化实测，以及单文件离线讲解 HTML。 |

论文 PDF 按原文收录；论文结论适用于其评测基准与设置，引用或复现实验时请查阅论文原文及后续版本。

NaturalDAO PoL Gate 设计记录了 2026-10-21 的实现基线，测试数量、服务状态及架构描述均对应当时的实现。如需运行本仓库的治理服务，请从 [POL2 Steward](../../POL2-Steward/README.md) 的安装和 Agent 接入说明开始。
