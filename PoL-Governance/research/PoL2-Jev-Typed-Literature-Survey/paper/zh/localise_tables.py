# -*- coding: utf-8 -*-
r"""Produce the Chinese generated-table appendices from the current English ones.

    python paper/zh/localise_tables.py

Reads  paper/sections/B_evidence.tex, paper/sections/C_catalogue.tex
Writes paper/zh/sections/B_evidence.tex, paper/zh/sections/C_catalogue.tex

Prose lines (section titles, intro paragraphs, captions, column headers) are
replaced only when the English line matches the stored English text exactly;
otherwise the script stops, so a changed English paragraph cannot silently keep
a stale translation. Categorical table cells are mapped column by column; any
unknown label stops the script. Citations, S/Q/N codes, G-IDs, set letters
(P/L/R), dates and English titles pass through unchanged.
"""
import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parent.parent
EN = PAPER / "sections"
ZH = PAPER / "zh" / "sections"

# ---------------------------------------------------------------- cell labels
COMPARATOR = {"better": r"更好", "similar": r"相近", "worse": r"更差",
              "mixed": r"不一", "--": r"--"}
DESIGN = {"stronger": r"较强", "moderate": r"中等", "weaker": r"较弱"}
# "hosted+open" is emitted by gen_evidence_table.py for some update rows (an
# unmapped raw CSV value); it means the same as H+O, so it is normalised here.
SYSTEM = {"H": "H", "O": "O", "H+O": "H+O", "hosted+open": "H+O", "--": "--"}
TIER = {"Core": r"核心", "Related": r"相关", "Background": r"背景",
        "Coded": r"已编码", "Context": r"背景材料", "Non-emp.": r"非实证",
        "Excluded": r"已排除"}
ZTYPE = {"preprint": r"预印本", "dataset": r"数据集", "technical note": r"技术说明",
         "publication": r"出版物", "working paper": r"工作论文",
         "software + report": r"软件 + 报告", "software + paper": r"软件 + 论文",
         "article": r"文章", "essay": r"评论文章", "other": r"其他"}
KEEP = None  # column passed through unchanged

# table label -> (expected column count, {column index: mapping})
TABLES = {
    "tab:evidence":         (6, {3: COMPARATOR, 4: SYSTEM, 5: DESIGN}),
    "tab:evidence-update":  (7, {4: COMPARATOR, 5: SYSTEM, 6: DESIGN}),
    "tab:catalogue":        (6, {3: TIER, 5: SYSTEM}),
    "tab:zenodo":           (5, {3: ZTYPE}),
    "tab:catalogue-update": (6, {4: TIER}),
}

# ---------------------------------------------------------------- prose lines
PROSE = {
# ---- B_evidence
r"\section{Evidence table}": r"\section{证据表}",

r"\Cref{tab:evidence} lists every coded study--requirement pair that enters the tallies of \cref{fig:framework}. \emph{Code}: S supports, Q qualifies, N negative, for detector use (\cref{app:codebook}). \emph{vs.\ generative}: the typed model's result relative to a generative comparator on that requirement, where one was run. \emph{System}: H hosted \jev{}, O open typed model only, H+O both. \emph{Design}: design rating of \cref{sec:appraisal}. The one-sentence rationale with locators for each row is in \texttt{data/evidence\_coding.csv}. Read in full but not tallied, because they are non-empirical, measure no typed model or were reclassified as context: \cite{arx01231}, \cite{arx22664}, \cite{arx32160}, \cite{molas2026calibrated}, \cite{willison2026jev}, \cite{zen22847531}, \cite{zen22858286}, \cite{zen22866847}, \cite{zen22887464}, \cite{zen22953637}, \cite{zen23064668}.":
r"\Cref{tab:evidence}列出进入\cref{fig:framework}计数的全部已编码“研究—要求”对。\emph{编码}：就检测器用途而言，S 为支持，Q 为有条件或结果不一，N 为不支持（见\cref{app:codebook}）。\emph{与生成式模型相比}：在该要求上运行过生成式对照模型时，类型化模型相对于该对照的结果。\emph{系统}：H 为托管的\jev{}，O 为仅开源类型化模型，H+O 为二者兼有。\emph{设计}：\cref{sec:appraisal}的设计评级。每行附定位信息的一句话理由见 \texttt{data/evidence\_coding.csv}。以下文献已全文阅读但未计入统计，因其属于非实证研究、未测量任何类型化模型，或被重新归类为背景材料：\cite{arx01231}、\cite{arx22664}、\cite{arx32160}、\cite{molas2026calibrated}、\cite{willison2026jev}、\cite{zen22847531}、\cite{zen22858286}、\cite{zen22866847}、\cite{zen22887464}、\cite{zen22953637}、\cite{zen23064668}。",

r"\caption{Coded evidence by requirement.}\label{tab:evidence}\\":
r"\caption{按要求排列的证据编码。}\label{tab:evidence}\\",

r"\toprule Req. & Study & Code & vs.\ generative & System & Design \\ \midrule \endfirsthead":
r"\toprule 要求 & 研究 & 编码 & 与生成式模型相比 & 系统 & 设计 \\ \midrule \endfirsthead",
r"\toprule Req. & Study & Code & vs.\ generative & System & Design \\ \midrule \endhead":
r"\toprule 要求 & 研究 & 编码 & 与生成式模型相比 & 系统 & 设计 \\ \midrule \endhead",

r"\Cref{tab:evidence-update} lists the pairs coded in the update search of 8~October (\cref{sec:update}); they are not part of the tallies above. \emph{Set}: P dated 2--8~October; L dated in the main window but retrieved only by the update search; R Zenodo record dated in the main window and re-screened. Codes were double-coded blind and disagreements adjudicated; rationales are in \texttt{data/evidence\_coding\_update\_2026-10-08.csv}.":
r"\Cref{tab:evidence-update}列出 10 月 8 日更新检索（\cref{sec:update}）中编码的“研究—要求”对；这些配对不计入上文的统计。\emph{集合}：P（窗口后）为日期在 10 月 2--8 日的文献；L（迟索引）为日期位于主窗口内、但仅由更新检索获取的文献；R（重新筛选）为日期位于主窗口内并经重新筛选的 Zenodo 记录。编码采用盲法双重编码，分歧经裁定解决；理由见 \texttt{data/evidence\_coding\_update\_2026-10-08.csv}。",

r"\caption{Coded evidence from the update search, by requirement.}\label{tab:evidence-update}\\":
r"\caption{按要求排列的更新检索证据编码。}\label{tab:evidence-update}\\",

r"\toprule Req. & Study & Set & Code & vs.\ generative & System & Design \\ \midrule \endfirsthead":
r"\toprule 要求 & 研究 & 集合 & 编码 & 与生成式模型相比 & 系统 & 设计 \\ \midrule \endfirsthead",
r"\toprule Req. & Study & Set & Code & vs.\ generative & System & Design \\ \midrule \endhead":
r"\toprule 要求 & 研究 & 集合 & 编码 & 与生成式模型相比 & 系统 & 设计 \\ \midrule \endhead",

# ---- C_catalogue
r"\section{Catalogue of studies}": r"\section{研究目录}",

r"\Cref{tab:catalogue} lists the arXiv and alphaXiv studies in the corpus, and \cref{tab:zenodo} the Zenodo records; all were read in full. Entries marked * were read in full and then treated as context because they measure no typed model; they are not counted. \emph{Model}: H = hosted \jev{}; O = an open or other typed model only; H+O = both; -- = no typed model measured. \emph{Req.}: requirements for which the study is coded (\cref{app:evidence}). Machine-readable metadata, licences and abstracts are in \texttt{data/papers.csv} and \texttt{data/zenodo\_preprints.csv}.":
r"\Cref{tab:catalogue}列出语料库中的 arXiv 与 alphaXiv 研究，\cref{tab:zenodo}列出 Zenodo 记录；所有文献均经全文阅读。标有 * 的条目经全文阅读后，因未测量任何类型化模型而被视为背景材料，不计入统计。\emph{模型}：H = 托管的\jev{}；O = 仅开源或其他类型化模型；H+O = 二者兼有；-- = 未测量类型化模型。\emph{要求}：该研究被编码的要求（见\cref{app:evidence}）。机器可读的元数据、许可证与摘要见 \texttt{data/papers.csv} 与 \texttt{data/zenodo\_preprints.csv}。",

r"\caption{arXiv and alphaXiv studies, by tier and requirement.}\label{tab:catalogue}\\":
r"\caption{按层级与要求排列的 arXiv 与 alphaXiv 研究。}\label{tab:catalogue}\\",

r"\toprule Ref. & Title & First sub. & Tier & Req. & Model \\ \midrule \endfirsthead":
r"\toprule 文献 & 标题 & 首次提交 & 层级 & 要求 & 模型 \\ \midrule \endfirsthead",
r"\toprule Ref. & Title & First sub. & Tier & Req. & Model \\ \midrule \endhead":
r"\toprule 文献 & 标题 & 首次提交 & 层级 & 要求 & 模型 \\ \midrule \endhead",

r"\caption{Zenodo records (preprints, notes, datasets and essays).}\label{tab:zenodo}\\":
r"\caption{Zenodo 记录（预印本、说明、数据集与评论文章）。}\label{tab:zenodo}\\",

r"\toprule Ref. & Title & Date & Type & Req. \\ \midrule \endfirsthead":
r"\toprule 文献 & 标题 & 日期 & 类型 & 要求 \\ \midrule \endfirsthead",
r"\toprule Ref. & Title & Date & Type & Req. \\ \midrule \endhead":
r"\toprule 文献 & 标题 & 日期 & 类型 & 要求 \\ \midrule \endhead",

r"\Cref{tab:catalogue-update} lists the 57 sources retained after full-text reading in the update search of 8~October (\cref{sec:update}). \emph{Set}: P dated 2--8~October; L dated in the main window but retrieved only by this search; R Zenodo record dated in the main window and re-screened; a dash where no row was coded. Metadata are in \texttt{paper/corpus\_update.bib}.":
r"\Cref{tab:catalogue-update}列出 10 月 8 日更新检索（\cref{sec:update}）中经全文阅读后保留的 57 篇文献。\emph{集合}：P（窗口后）为日期在 10 月 2--8 日的文献；L（迟索引）为日期位于主窗口内、但仅由本次检索获取的文献；R（重新筛选）为日期位于主窗口内并经重新筛选的 Zenodo 记录；未编码任何行的条目以短横线表示。元数据见 \texttt{paper/corpus\_update.bib}。",

r"\caption{Sources retained after full-text reading in the update search.}\label{tab:catalogue-update}\\":
r"\caption{更新检索中经全文阅读后保留的文献。}\label{tab:catalogue-update}\\",

r"\toprule Ref. & Title & Date & Set & Tier & Req. \\ \midrule \endfirsthead":
r"\toprule 文献 & 标题 & 日期 & 集合 & 层级 & 要求 \\ \midrule \endfirsthead",
r"\toprule Ref. & Title & Date & Set & Tier & Req. \\ \midrule \endhead":
r"\toprule 文献 & 标题 & 日期 & 集合 & 层级 & 要求 \\ \midrule \endhead",
}

# Lines that are pure LaTeX / comments and pass through unchanged.
PASS = re.compile(r"^(%|\\label\{|\\begin|\\end|\\begingroup|\\endgroup|"
                  r"\\renewcommand|\\bottomrule|\s*$)")
AMP = re.compile(r"(?<!\\)&")
ROW_END = re.compile(r"\s*\\\\\s*$")


def map_row(line, label, lineno):
    ncol, maps = TABLES[label]
    body = ROW_END.sub("", line)
    cells = AMP.split(body)
    if len(cells) != ncol:
        sys.exit(f"line {lineno}: {len(cells)} cells, expected {ncol} in {label}: {line}")
    for i, mapping in maps.items():
        raw = cells[i]
        val = raw.strip()
        if val not in mapping:
            sys.exit(f"line {lineno}: unknown label {val!r} in column {i} of {label}")
        lead = raw[: len(raw) - len(raw.lstrip())]
        trail = raw[len(raw.rstrip()):]
        cells[i] = lead + mapping[val] + trail
    return "&".join(cells) + " \\\\"


def localise(name):
    src = (EN / name).read_text(encoding="utf-8").splitlines()
    out, label, used = [], None, set()
    for n, line in enumerate(src, 1):
        m = re.search(r"\\label\{(tab:[^}]+)\}", line)
        if m:
            label = m.group(1)
        if line in PROSE:
            out.append(PROSE[line]); used.add(line)
        elif line.startswith(r"\end{longtable}"):
            out.append(line); label = None
        elif PASS.match(line):
            out.append(line)
        elif label and AMP.search(line) and ROW_END.search(line):
            out.append(map_row(line, label, n))
        else:
            sys.exit(f"{name} line {n}: no translation for English line:\n{line}")
    with open(ZH / name, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return used


def check_counts(name):
    en = (EN / name).read_text(encoding="utf-8")
    zh = (ZH / name).read_text(encoding="utf-8")
    for pat in [r"\cite{", r"\cref{", r"\Cref{", r"\label{", r"\begin{", r"\end{",
                r"\zmark{}", r"\gmark{}"]:
        a, b = en.count(pat), zh.count(pat)
        flag = "" if a == b else "  <-- MISMATCH"
        print(f"  {name:16s} {pat:10s} en={a:4d} zh={b:4d}{flag}")
        if a != b:
            sys.exit(1)
    if zh.count("{") != zh.count("}"):
        sys.exit(f"{name}: unbalanced braces")
    if len(en.splitlines()) != len(zh.splitlines()):
        sys.exit(f"{name}: line count differs")


if __name__ == "__main__":
    used = set()
    for f in ["B_evidence.tex", "C_catalogue.tex"]:
        used |= localise(f)
        check_counts(f)
    unused = [k for k in PROSE if k not in used]
    if unused:
        print("warning: stored translations not used (English changed?):")
        for k in unused:
            print("   ", k[:80])
    print("done")
