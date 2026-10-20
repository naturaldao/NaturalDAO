# ROADMAP — 通用决策数据集（pol/DATA-02）

目标：交付可上线的通用决策数据集，用于微调 System-One / Jev 类小决策模型时不降低通用智力。

## 阶段与状态

| 阶段 | 内容 | 状态 |
|---|---|---|
| P1 | 语料重建：原生四元组、溯源、格式标准化 | 完成 |
| P2 | 切分与 benchmark：分组切分、私盐、来源均衡 | 完成 |
| P3 | 文档：README 能力维度审计、契约、来源登记 | 完成 |
| P4 | 安全：公开面内容级审计 + 注入验证 | 完成 |
| P5 | 概率补全：Jev 校验 → mercury-decide 免费原生概率 | 进行中 |
| P6 | 能力拓宽：bigbench + cosmos_qa 合并（1/4 取样） | 进行中 |
| P7 | 上线：PR 审核、HF 私有 benchmark 交付 | 等 P5/P6 |

## P5 关键决策（2026-10-20）

放弃 jev-router（$0.0009/次，key 上限 $1 撞墙），改用 `inception/mercury-decide:free`：

- 端点 `POST /api/alpha/decisions`（**不是 chat/completions**）
- 请求：`{model, state, questions: {<key>: {type: "noul"|"choice"|"score"|"box", instructions, options/criteria}}}`
- 返回：`{answers: {<key>: {type, noul: <P(yes)>}}}`，**cost: 0**
- noul 直接给校准概率；choice 需 `criteria`（record）；score 的 `criteria` 是 **array**
- **限流严格**（429），必须控速

## P6 关键约束

- bigbench 在能力候选集里约占 88%，取 1/4 后仍可能占合并后 55%+ → 需按 config 分层抽样并报告最终占比
- 合并会触发重切 → benchmark 重做 → 审计重跑 → README 重算