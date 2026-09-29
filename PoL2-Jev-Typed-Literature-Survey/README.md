# PoL2-Jev-Typed-Literature-Survey

**爱2证明（PoL2）× Jev 类型化决策模型：文献综述与数据**

Jev 是 TypeSafe AI 于 2026-09-15 发布的第一个"System One 决策模型"：它不生成文字，只对给定问题返回选择、分级评分或是非概率。PoL2 的工程策略需要一个对每次输入输出都做"动态审计与拦截"的**安全阀**，而 Jev 这类模型在形态上正适合这个位置。本目录收集 Jev 发布后两周内的研究，逐条对照 PoL2 正文的治理条款，回答一个问题：**这类模型能在多大程度上、以什么前提承担 PoL2 治理层的判断工作？**

> 本目录是参考文献整理，不是 PoL2 正文，也不代表协作者的共同立场。标 ★ 的建议需要团队讨论确认。

## 从这里开始

| 你想要 | 去哪里 |
|---|---|
| 读综述正文（中文） | [docs/survey.zh.md](docs/survey.zh.md) |
| 按 PoL2 条款查论文 | [docs/survey.zh.md 第 1 节对照框架](docs/survey.zh.md#1-对照框架pol2-条款--工程问题--文献) |
| 最重要的负面结果 | [docs/survey.zh.md 第 3 节](docs/survey.zh.md#3-负面结果汇总) |
| 给 NaturalDAO 的工程建议 ★ | [docs/survey.zh.md 第 4 节](docs/survey.zh.md#4-对-naturaldao-工程的建议草案-) |
| 论文全文 PDF | [papers/](papers/)（许可见 [papers/LICENSES.md](papers/LICENSES.md)） |
| 机器可读的数据 | [data/](data/)，见下表 |

## 主要发现

1. **安全阀可以用，但只能做"探测器"。** 零样本检测十类对齐失效的 AUROC 中位数达 0.886，但默认阈值 0.5 下的 F1 可以低到 0.158，阈值必须按任务本地拟合。
2. **安全阀本身会被输入内容操纵。** 借助概率反馈优化出的、读来自然的语境短句，可把 61.4% 原本正确的决策翻转成错误；多轮自适应攻击 27 次攻破 25 次。
3. **"类型安全"不等于"判断正确"。** 只把选项名从 0/1 改成 no/yes，开源 Jev 类模型的 AUC 就从 0.94 翻转到 0.23，Jev 本身从 0.81 降到 0.58，而类型错误率始终是 0%——模型跟随的是选项的名字，而不是我们写给它的定义。
4. **模型不会主动说"不知道"。** 有研究提出，二元问题会把"不知道"压成"是 / 否"；按这一假设补回第三真值，软准确率从 0.771 升到 0.978。这与 PoL2"非爱非恨的不在场"状态直接相关。
5. **把疑难样本升级给另一个 AI，未必能纠错。** 升级给推理型模型时效果不错，但同档的 LLM 评判器几乎重复了 Jev 最自信的错误；升级链的末端必须有人。

## 目录结构

```
PoL2-Jev-Typed-Literature-Survey/
├── README.md                 本文件
├── docs/
│   └── survey.zh.md          综述正文（中文）
├── data/
│   ├── papers.csv / .json    论文目录（生成文件）：层级、PoL2 轴线、要点、许可、摘要
│   ├── pol2_mapping.csv      人工维护：每篇论文的层级、轴线与一句话要点 ← 改归类改这里
│   ├── pol2_axes.json        G1–G7 七条轴线的定义及对应的 PoL2 正文条款
│   ├── grey_literature.csv   灰色文献（博客、技术报告、开源仓库）
│   └── sources/
│       └── arxiv_meta.csv    arXiv 元数据原始快照（由脚本抓取）
├── papers/
│   ├── 2609.xxxxx.pdf        Creative Commons 许可的论文全文
│   └── LICENSES.md           每篇 PDF 的许可（生成文件）
├── scripts/
│   ├── fetch_papers.ps1      抓取元数据、许可与 PDF（Windows PowerShell）
│   ├── build_catalog.py      生成 papers.csv/json、LICENSES.md 与综述中的目录表
│   └── check.py              一致性检查
├── CONTRIBUTING.md  CHANGELOG.md  CITATION.cff  LICENSE
```

本目录不依赖仓库其他部分，可整体复制到独立仓库使用。

## 数据字段（`data/papers.csv`）

| 字段 | 含义 |
|---|---|
| `id` | `P-xxxxx`（arXiv 2609.xxxxx）或 `A-xxx`（仅 alphaXiv） |
| `tier` | `核心` 直接对应 PoL2 治理条款 · `相关` 提供补充证据 · `背景` 工程与其他领域 |
| `pol_axes` | 空格分隔的 G1–G7，定义见 `pol2_axes.json` |
| `license` / `license_url` | 作者在 arXiv 上选择的许可 |
| `pdf_in_repo` | `yes` 表示全文已收入 `papers/` |
| `note_zh` | 一句话要点 |
| `abstract` | arXiv 原文摘要 |

## 更新与复现

需要 Python 3.10+（仅标准库）；抓取脚本需要 Windows PowerShell 5.1 或 PowerShell 7。

```powershell
# 1. 在 data/pol2_mapping.csv 增删论文或修改归类
# 2. 抓取元数据、许可与 PDF（arXiv 需要代理时加 -Proxy "http://127.0.0.1:7890"）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\fetch_papers.ps1
# 3. 重新生成目录并检查
python scripts/build_catalog.py
python scripts/check.py
```

`fetch_papers.ps1` 会把 arXiv 默认许可的论文下载到 `papers/_local/`，该文件夹已被 `.gitignore` 忽略，不会被提交。

## 与 NaturalDAO 其他项目的关系

- **PoL2 正文**：[`PoL/`](https://github.com/naturaldao/NaturalDAO/tree/main/PoL)。本综述的条款编号依据 commit `2e094d3`（2026-09-27）。
- **PoL 治理层协作**：[PR #15](https://github.com/naturaldao/NaturalDAO/pull/15) 提议的 `PoL-Governance/` 目录（数据、模型适配、校准盲测、插件）。本综述可作为其模型调研（`MODEL-01`）与评估设计（`EVAL-01`）的文献依据；`data/papers.json` 可被其工具直接读取。

## 许可

整理者撰写的文字、数据与脚本以 [CC0-1.0](LICENSE) 发布。**`papers/` 中的论文不适用 CC0**，各自保留原作者的 Creative Commons 许可，详见 [papers/LICENSES.md](papers/LICENSES.md)。arXiv 默认许可的论文未收入，只提供链接。

## 引用

见 [CITATION.cff](CITATION.cff)。引用具体研究时，请直接引用原论文。
