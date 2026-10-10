# PoL2-Jev-Typed-Literature-Survey

**类型化决策模型能否承担 PoL 治理中的自动化保障职能？——基于早期证据的爱2证明（PoL2）规范逐条分析**

Jev 是 TypeSafe AI 于 2026-09-15 发布的第一个“System One 决策模型”：它不生成文字，只对给定问题返回选择、分级评分或是非概率。PoL2 的工程策略需要一个对每次输入输出都做“动态审计与拦截”的**安全阀**，而 Jev 这类模型在形态上正适合这个位置。本目录围绕 PoL 治理，把 PoL2 中要求或约束机器判断的条款转写为七条可检验的要求（G1–G7），用 Jev 发布后的研究逐条检验，回答一个问题：**这类模型能在多大程度上、以什么前提承担 PoL2 治理层的判断工作？**

> 本目录是研究材料，不是 PoL2 正文，也不代表协作者的共同立场。整理者是 PoL2 的贡献者之一，立场声明见论文“Positionality and competing interests”一节。

## 从这里开始

| 你想要 | 去哪里 |
|---|---|
| 读论文（英文，arXiv 投稿版，v0.5） | [paper/main.pdf](paper/main.pdf)（只含正文与参考文献）；在线附录 [paper/online_appendix.pdf](paper/online_appendix.pdf)（A 条款中英对照、B 检索筛选与编码手册、C 每项确定性评级的推导表、D 治理范式对比表与验收清单与结论全表、E 对早期数据集的更正） |
| 读论文中文译稿（对应 v0.4.1 长版；英文版为正式版本） | [paper/zh/main_zh.pdf](paper/zh/main_zh.pdf)；补充材料见 [paper/zh/supplement_zh.pdf](paper/zh/supplement_zh.pdf) |
| 看结论（Jev 是否适合作为 PoL2 的治理工具） | 论文 §6.3 与表 “Verdict for PoL2”（全表见在线附录 D） |
| 看 PoL2 与其他 AI 治理范式的比较 | 论文 §2.3 |
| 看审稿与修订记录 | [paper/review/REVIEW.md](paper/review/REVIEW.md)、[paper/review/AUDIT.md](paper/review/AUDIT.md) |
| 机器可读的数据（编码、质量评价、确定性证据） | [data/](data/)，见下文 |
| 早期中文综述（v0.1，37 篇，主要依据摘要，已被论文取代） | [docs/survey.zh.md](docs/survey.zh.md) |
| 论文全文 PDF（CC 许可部分） | [papers/](papers/)（许可见 [papers/LICENSES.md](papers/LICENSES.md)） |

## 主要发现（证据截至 2026-10-08，所有结论的确定性均为“低”或“极低”）

1. **结论：按现有证据，托管 Jev 不适合承担 PoL2 中任何“做决定”的功能**（争议裁决、自动伦理验证、逐人量化、任何不经人确认的最终拦截）。对安全阀、恨语截断和文本异常检测，它只能作为**有记录、三值、经本地校准的检测器**，并放在论文 §6 的设计中、由人终结有后果的决定；即便如此，这也是从英文二值基准外推出来的，没有任何研究测过 PoL2 的中文三值构念。
2. **作为检测器有可用之处。** 在英文基准上对有害内容排序良好，成本仅为 LLM 评估器的一小部分；在一项基于模拟数据的预注册研究中，只在独立构建的规则同意时才接受其低风险判定，准确率没有损失，但伪装攻击仍能通过。
3. **不能作为裁决者。** 阈值换场景就失效；判定会跟随选项名称而非定义；被审内容中插入的观点能操纵判定；在一项研究的三个任务中，针对 Jev 的注入攻击成功率达 97–100%；“不知道”“以上皆非”这类选项的选择不稳定；同档评估器几乎重复了它最自信的错误。
4. **结论并非专门针对类型化模型。** 在做过对比之处，类型化模型总体上并不比生成式评估器差；但大多数失效从未对比，证据既不表明失效为类型化模型独有，也不表明二者共有，所以这一结论出于审慎同样适用于低成本生成式评估器。
5. **可借鉴之处**（不依赖具体模型）：三值提问并单独问“证据是否足够”；中性的选项标识；每次判定留记录；本地校准并定期做时间再验证；只在独立构建的检测器一致时自动行动；决策用不到的敏感字段不进入检测器；对事件评分而不对人评分；链条以人结束；先建 PoL2 自己的中文构念基准。
6. **为什么以 PoL2 为案例**（论文 §2.3）：在比较的治理范式中，PoL2 与网信办《生成式人工智能服务管理暂行办法》是同时规定了推理期拦截、所用标准与判定义务的两份文本；PoL2 的构念（三值、不作道德标签）和拦截点写在可引用的条款里，因此能推导出可检验的要求，其缺口（如单次拦截没有规定理由、记录或申诉）也看得见。选择它不是因为它独一无二。

## 目录结构

```
PoL2-Jev-Typed-Literature-Survey/
├── README.md                 本文件
├── paper/                    论文（LaTeX）
│   ├── main.tex / main.pdf   正文；preamble.tex 为共享导言
│   ├── online_appendix.tex / .pdf  在线附录 A–E（单独 PDF，不进 arXiv 包）
│   ├── build.py              编译论文（python paper/build.py；中文加 --zh）
│   ├── sections/             各章节；B_evidence.tex、C_catalogue.tex 由脚本生成
│   ├── figures/              图（PDF）；src/ 为绘图脚本
│   ├── *.bib                 文献；corpus.bib、corpus_update.bib 由脚本生成
│   ├── make_arxiv.py         打包 arXiv 提交文件（只含正文）
│   ├── make_metadata.py      生成 arXiv 表单所需的标题、摘要与备注
│   ├── zh/                   中文译稿（xelatex；GLOSSARY.md 为术语表）
│   └── review/               审稿与修订记录（43 轮），编码手册与编码过程文件
├── data/
│   ├── evidence_coding.csv           主窗口证据编码（研究 × 要求，S/Q/N）
│   ├── evidence_coding_update_*.csv  2026-10-08 补充检索的编码
│   ├── quality_appraisal*.csv        设计质量评价
│   ├── certainty_evidence.csv        每条关键结论的支持与相反证据（确定性评级由脚本计算）
│   ├── coder_agreement*.csv          盲法第二编码与裁定
│   ├── papers.csv / .json            论文目录（生成文件）
│   ├── zenodo_preprints.csv、grey_literature.csv、excluded_records*.csv、search_rerun_*.csv
│   └── pol2_mapping.csv、pol2_axes.json、sources/arxiv_meta.csv
├── scripts/                  检索、编码合并、确定性评级（rate_certainty.py --check）、目录生成与检查
├── docs/survey.zh.md         早期中文综述（v0.1）
├── papers/                   Creative Commons 许可的论文全文与 LICENSES.md
├── CONTRIBUTING.md  CHANGELOG.md  CITATION.cff  LICENSE
```

本目录不依赖仓库其他部分，可整体复制到独立仓库使用。

## 复现

需要 Python 3.10+（仅标准库）与 TeX Live 或 MiKTeX（pdflatex、xelatex、bibtex）。

```powershell
python scripts/merge_coding.py          # 主窗口编码 → data/evidence_coding.csv 与 paper/counts.tex
python scripts/merge_update.py          # 补充检索编码 → data/*_update_*.csv 与 paper/counts_update.tex
python scripts/rate_certainty.py --check  # 确定性评级，并核对论文表格
python scripts/merge_all.py             # 全部检索合并后的计数 → paper/counts_all.tex
python paper/build.py                   # 英文论文与在线附录
python paper/build.py --zh              # 中文译稿
python paper/make_metadata.py; python paper/make_arxiv.py
```

`scripts/fetch_papers.ps1` 会把 arXiv 默认许可的论文下载到 `papers/_local/`，该文件夹已被 `.gitignore` 忽略，不会被提交。

## 与 NaturalDAO 其他项目的关系

- **PoL2 正文**：[`PoL/`](https://github.com/naturaldao/NaturalDAO/tree/main/PoL)。论文的条款编号依据 commit `5791ae3`（2026-09-30）；早期中文综述依据 `2e094d3`（2026-09-27）。
- **PoL 治理层协作**：本目录是 [`PoL-Governance/`](../../README.md) 的文献调研部分，任务编号 `LIT-01`，进度见任务页 [`tasks/LIT-01-shenton.md`](../../tasks/LIT-01-shenton.md)。
  - 可作为 [`MODEL-01`](../../TASKS.md) 模型调研与[模型清单](../../models/CATALOG.md)的文献依据：论文 §6 的 16 项验收清单可直接转为候选模型的淘汰检查项；
  - 可作为 `EVAL-01` 评估设计的参考：选项换名测试、时间再验证（新词替换句对）、按子类报告召回率等，都可以纳入 [benchmark](../../benchmark/README.md) 的协议；
  - `data/papers.json` 与 `data/evidence_coding*.csv` 为机器可读数据，可被其工具直接读取。

## 许可

整理者撰写的文字、数据与脚本以 [CC0-1.0](LICENSE) 发布。**`papers/` 中的论文不适用 CC0**，各自保留原作者的 Creative Commons 许可，详见 [papers/LICENSES.md](papers/LICENSES.md)。arXiv 默认许可的论文未收入，只提供链接。

## 引用

见 [CITATION.cff](CITATION.cff)。引用具体研究时，请直接引用原论文。
