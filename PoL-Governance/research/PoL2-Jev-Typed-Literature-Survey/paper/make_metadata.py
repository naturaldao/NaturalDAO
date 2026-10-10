"""Write paper/arxiv_metadata.txt: plain-text title, authors, abstract and comments for the arXiv submission form.

arXiv metadata must contain no LaTeX; the abstract is limited to 1,920 characters.
Counts are read from counts.tex and counts_update.tex and the page count from main.log, so run after a full build.
Run: python paper/make_metadata.py
"""
import re
from pathlib import Path

P = Path(__file__).resolve().parent
LIMIT = 1920

TITLE = ("Can Typed Decision Models Serve as Automated Safeguards in PoL Governance? "
         "A Clause-Level Analysis of the Proof of Love2 Specification")
AUTHORS = "Shentao Yan"


def counts():
    c = {}
    for name in ("counts.tex", "counts_update.tex", "counts_all.tex"):
        for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", (P / name).read_text(encoding="utf-8")):
            c[m.group(1)] = m.group(2)
    return c


def plain_abstract(c):
    a = (P / "sections" / "00_abstract.tex").read_text(encoding="utf-8")
    a = a.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0]
    for k, v in c.items():
        a = a.replace("\\" + k + "{}", v)
    rep = {r"\jev{}": "Jev", r"\pol{}": "PoL2", r"$\kappa = ": "kappa = ", r"$\times$": "x", r"\%": "%",
           "``": '"', "''": '"', "~": " "}
    for k, v in rep.items():
        a = a.replace(k, v)
    a = a.replace("$", "")
    a = re.sub(r"\\texttt\{([^}]*)\}", r"\1", a)
    a = re.sub(r"\s+", " ", a).strip()
    if "\\" in a or "{" in a:
        raise SystemExit(f"LaTeX left in abstract: {a}")
    return a


def main():
    c = counts()
    a = plain_abstract(c)
    status = "OK" if len(a) <= LIMIT else f"TOO LONG by {len(a) - LIMIT}"
    log = (P / "main.log").read_text(encoding="latin-1") if (P / "main.log").exists() else ""
    pages = re.search(r"Output written on main\.pdf \((\d+) pages", log)
    n_fig = len(re.findall(r"\\begin\{figure\}", "".join(
        f.read_text(encoding="utf-8") for f in (P / "sections").glob("0*.tex"))))
    n_tab = len(re.findall(r"\\begin\{table\}", "".join(
        f.read_text(encoding="utf-8") for f in (P / "sections").glob("*.tex"))))
    text = (f"Title:\n{TITLE}\n\nAuthors:\n{AUTHORS}\n\n"
            f"Abstract ({len(a)} characters; arXiv limit {LIMIT}: {status}):\n{a}\n\n"
            f"Comments:\n{pages.group(1) if pages else '?'} pages, {n_fig} figures. Online appendix: "
            "https://github.com/naturaldao/NaturalDAO/blob/main/PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey/paper/online_appendix.pdf. "
            "Data, evidence coding, review logs and scripts: https://github.com/naturaldao/NaturalDAO "
            "(PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey)\n\n"
            "Primary category (suggested): cs.CY (Computers and Society)\n"
            "Cross-list (suggested): cs.AI\n"
            "License (suggested): CC BY 4.0\n")
    (P / "arxiv_metadata.txt").write_text(text, encoding="utf-8")
    print(len(a), status)


if __name__ == "__main__":
    main()
