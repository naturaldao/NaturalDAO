# paper/ — 论文（arXiv 格式）

**Can Typed Decision Models Serve as Automated Safeguards in PoL Governance? A Clause-Level Analysis of the Proof of Love2 (PoL2) Specification Against Early Evidence**（v0.4，2026-10-09）

正文：[main.pdf](main.pdf)；补充材料 S1–S5：[supplement.pdf](supplement.pdf)；中文译稿：[zh/main_zh.pdf](zh/main_zh.pdf)、[zh/supplement_zh.pdf](zh/supplement_zh.pdf)（英文版为正式版本）。arXiv 提交包：`arxiv-submission.zip`（由 `make_arxiv.py` 生成，补充材料作为 `anc/supplement.pdf` 附属文件，已在干净目录中单独编译通过）。提交表单所需的纯文本元数据：`arxiv_metadata.txt`。

## 文件

| 路径 | 内容 |
|---|---|
| `main.tex` / `supplement.tex` / `preamble.tex` | 正文、补充材料（原附录 A–E，编号 S1–S5）与共享导言（pdflatex；中文引文用 CJKutf8） |
| `build.py` | 编译正文与补充材料，并互相导入交叉引用（生成 `main_labels.tex`、`supplement_labels.tex`）；`--zh` 编译中文译稿 |
| `counts_update.tex` | 补充检索计数，由 `../scripts/merge_update.py` 生成 |
| `zh/` | 中文译稿（xelatex）；`GLOSSARY.md` 术语表，`QA_LOG.md` 审校记录 |
| `counts.tex` | 语料计数与一致性统计，由 `../scripts/merge_coding.py` 生成，勿手改 |
| `sections/` | 各章节。`B_evidence.tex` 由 `gen_evidence_table.py`、`C_catalogue.tex` 由 `gen_catalogue.py` 生成，勿手改 |
| `figures/src/` | 绘图脚本，按 [figures4papers](https://github.com/ChenLiu-1996/figures4papers) 规范（`f4p_style.py`） |
| `figures/*.pdf, *.png` | 图（PDF 供 LaTeX，PNG 供预览） |
| `corpus.bib` | 由 `gen_corpus_bib.py` 从 `data/papers.csv` 与 `data/zenodo_preprints.csv` 生成 |
| `grey.bib` / `background.bib` / `pol2.bib` | 灰色文献、背景文献、PoL2 原文；核实来源见 `bib_verification_log.tsv` |
| `review/` | 独立审稿迭代：`PROTOCOL.md`（流程）、`round*_*.md`（各轮原始意见）、`REVIEW.md`（处理情况）、`CODEBOOK_v3.md`、`coding/`（编码原始文件） |

## 重新生成与编译

```powershell
python scripts/rerun_arxiv_search.py      # 可选：重跑 arXiv 检索
python scripts/build_catalog.py
python scripts/merge_coding.py            # 合并编码、计算 κ、写 counts.tex
python paper/gen_corpus_bib.py
python paper/gen_catalogue.py
python paper/gen_evidence_table.py
cd paper/figures/src; foreach ($f in Get-ChildItem plot_*.py) { python $f.Name }; cd ../../..
python scripts/merge_update.py; python scripts/rate_certainty.py --check
python paper/build.py; python paper/build.py --zh
cd paper
python make_metadata.py
python make_arxiv.py
```

需要 Python 3.10+（matplotlib、numpy）与 TeX Live / MiKTeX（pdflatex、bibtex、CJK 宏包）。

## 写作约定

- 定位：cs.CY 研究论文，不称“综述”；“judge”只用于文中定义的“裁决者”含义，泛指的 LLM-as-a-judge 写作 “LLM evaluators”。
- 术语跟随 PoL2 官方英译（`PoLEn/`）：Love Language、hate language、state of absence、Public AI (PAI)、right of suggestion、universal questioning period。
- 条款编号以 NaturalDAO commit `5791ae3` 为准；补充材料 S1 为中英逐字摘录与旧编号。
- 标 ‡（`\zmark`）的是 Zenodo 记录，标 †（`\gmark`）的是灰色文献；所有来源均已全文阅读。
- 证据编码（S/Q/N，针对“检测器”用途，对称规则 v3）在 `data/evidence_coding.csv`，规则见补充材料 S5；质量评估在 `data/quality_appraisal.csv`；盲法第二编码者结果在 `data/coder_agreement.csv`。
