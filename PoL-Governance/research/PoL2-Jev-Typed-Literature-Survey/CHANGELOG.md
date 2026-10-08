# 更新记录

## 0.4.0 — 2026-10-09

- **标题统一围绕 PoL 治理**：“Can Typed Decision Models Serve as Automated Safeguards in PoL Governance? A Clause-Level Analysis of the Proof of Love2 (PoL2) Specification Against Early Evidence”；中文“类型化决策模型能否承担 PoL 治理中的自动化保障职能？——基于早期证据的爱2证明（PoL2）规范逐条分析”。作者信息暂为占位。
- **正文与补充材料分开**：原附录 A–E 改为补充材料 S1–S5（`paper/supplement.pdf`），正文交叉引用自动显示为 Supplement S1–S5；arXiv 包中作为 `anc/` 附属文件。新增 `paper/build.py`。
- **补充检索（截至 2026-10-08）**：全文阅读 62 项，其中 5 项在全文阶段排除，保留 57 项（arXiv 31、Zenodo 26）；48 项编码，共 118 个“研究 × 要求”配对；全部配对由 AI 编码者盲法第二编码（κ = 0.55），分歧由第三轮 AI 裁定；结果单列于论文 §4.9，主窗口结论未反转。arXiv API 限流时改用网页检索（`scripts/rerun_arxiv_search_web.py`），新增 Zenodo 检索脚本。
- **新增 §2.3 PoL2 与其他 AI 治理范式的比较**（监管、平台治理、训练期宪法、推理期护栏、DAO 治理）：给出可核查的属性及其代价；网信办《暂行办法》为最接近的对照；不主张唯一性。
- **新增 §7.1 明确结论**：按现有证据，托管 Jev 不适合承担 PoL2 任何“做决定”的功能，只能作为 §6 设计中的有记录检测器；附“可借鉴之处”九条。
- **确定性评级改为脚本计算**（`data/certainty_evidence.csv` + `scripts/rate_certainty.py --check`），规则对称化（支持/相反研究、按系统组计数、“有争议”标记）；与 10 月 4 日评级并列给出，评级规则修订作为方案偏离披露。终值：0 中等、11 低、4 极低。
- 背景文献新增 Hatevolution（时间漂移）与 8 篇治理范式文献；验收清单新增第 16 项“时间再验证”，第 7 项扩展到仅凭标签的查询接口攻击。
- 法条适用收紧：欧盟《人工智能法》第 5 条第 1 款（f）项限于生物特征数据；第 14、86 条限于附件三高风险系统（争议裁决可能落入附件三第 8（a）点）。
- 审稿第 12–43 轮，记录见 `paper/review/`；中文译稿同步并审校。

## 0.3.0 — 2026-10-04

- 论文重新定位：从“综述”改为 cs.CY 研究论文（PoL2 条款级政策与工程分析 + 结构化证据评估），以符合 arXiv 2025 年 10 月对 CS 类综述的新规；新标题“Can Typed Decision Models Serve as Automated Safeguards in AI Governance?”；作者署名 Shentao Yan。
- 引入独立审稿迭代流程（`paper/review/`，借鉴 HuangPuStar/MetaInfer 的 /fix-paper）：第一轮 5 个独立审稿共 174 条意见，处理情况见 `paper/review/REVIEW.md`。
- 重新检索 arXiv（2026-10-04，脚本 `scripts/rerun_arxiv_search.py`）：新增 15 篇论文；1 篇（2609.22664）因未测试类型化模型改为背景引用。arXiv 79 篇、Zenodo 27 条、alphaXiv 1 篇、灰色文献 7 条。
- 全部文献（含 Zenodo）全文阅读；对称编码规则 v3（针对“探测器”用途）重新编码；每条记录增加“与生成式模型相比”字段；盲法第二编码者抽样 30 对，κ = 0.72；新增质量评估（`data/quality_appraisal.csv`）与 GRADE 式确定性评级。
- 附录 A 改为 PoL2 官方英文译本逐字摘录；修正 §5.5、§5.6、§5.4、§5.4.1、§4.3.3.1 等转述偏差。
- 新增 21 条经 Crossref/arXiv 核验的背景文献（内容审核、情绪识别批评、标注分歧、中文有害语言数据集、延后决策、分布偏移、正当程序、社会评分、PRISMA/GRADE）。
- 检索截止：arXiv 2026-10-04（首版日期 ≤ 2026-10-01）；Zenodo 2026-10-01。

## 0.2.0 — 2026-10-01

- 新增英文论文 `paper/`（arXiv 格式 LaTeX）：七条轴线的证据综合、PoL2 正文中的五处张力、参考架构与验收清单；图表按 figures4papers 规范绘制。
- 语料扩充：arXiv 论文 36 → 65 篇（新增 29 篇，其中 14 篇在旧截止日前提交但当时漏检；另 1 篇因 PDF 内容与标题不符而排除），新增 28 条 Zenodo 预印本（`data/zenodo_preprints.csv`）。
- 全部 arXiv 论文对照全文逐条核查，修正 v0.1 中的多处说法（见论文附录 C）；灰色文献按原网页核对并更新标题与日期。
- PoL2 条款编号更新到 NaturalDAO commit `5791ae3`（2026-10-01）：旧 §3.4.1 → §5.4.1，旧 §5.3.x → §4.3.x，旧 §3.6 → §5.6。
- 检索截止：2026-10-01。

## 0.1.0 — 2026-09-29

- 首个版本：36 篇 arXiv 论文 + 1 篇 alphaXiv 论文，按 PoL2 治理条款归入 G1–G7 七条轴线。
- 收入 23 篇 Creative Commons 许可论文的 PDF；13 篇 arXiv 默认许可论文只提供链接与本地下载脚本。
- 11 条灰色文献（博客、技术报告、开源仓库）。
- 检索截止：2026-09-29（香港时间）。PoL2 正文依据：NaturalDAO `PoL/` 目录，commit `2e094d3`。
