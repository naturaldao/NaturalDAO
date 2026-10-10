"""Build the arXiv submission bundle: paper/arxiv/ and paper/arxiv-submission.zip.

Follows the arXiv submission requirements checklist (Desktop/arxiv-submission-requirements.md):
- single flat directory: main.tex, the \\input files, figure PDFs and main.bbl at top level;
- figures as PDF (pdflatex), relative paths without spaces;
- main.bbl shipped, no .bib, no compiled PDF, no auxiliary files, no hidden files;
- all TeX comments stripped; 00README.json declares pdflatex and the top-level file.
Run after a full local build (pdflatex, bibtex, pdflatex x2):  python paper/make_arxiv.py
The bundle is then recompiled in a clean temporary directory as a check.
"""
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent
OUT = P / "arxiv"
ZIP = P / "arxiv-submission.zip"

COMMENT = re.compile(r"(?<!\\)%.*$")


def strip_comments(text):
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("%"):
            continue  # whole-line comment
        # keep a trailing % so that line-end spacing is unchanged
        new = COMMENT.sub("%", line) if COMMENT.search(line) else line
        lines.append(new)
    return "\n".join(lines) + "\n"


def flatten_paths(text):
    text = re.sub(r"\\input\{sections/([\w\-]+)\}", r"\\input{\1}", text)
    text = re.sub(r"\{figures/([\w\-]+\.pdf)\}", r"{\1}", text)
    return text


def main():
    if not (P / "main.bbl").exists():
        raise SystemExit("main.bbl missing: run pdflatex + bibtex first")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    tex_files = {"main.tex": P / "main.tex", "preamble.tex": P / "preamble.tex", "counts.tex": P / "counts.tex",
                 "counts_update.tex": P / "counts_update.tex",
                 "counts_all.tex": P / "counts_all.tex"}
    # the paper only; the online appendix is a separate PDF on GitHub
    for f in (P / "sections").glob("0*.tex"):
        tex_files[f.name] = f
    used_figs = set()
    for name, src in tex_files.items():
        t = src.read_text(encoding="utf-8")
        used_figs |= set(re.findall(r"figures/([\w\-]+\.pdf)", t))
        (OUT / name).write_text(flatten_paths(strip_comments(t)), encoding="utf-8")
    for fig in sorted(used_figs):
        shutil.copy(P / "figures" / fig, OUT / fig)
    shutil.copy(P / "main.bbl", OUT / "main.bbl")
    (OUT / "00README.json").write_text(json.dumps({
        "spec_version": 1,
        "process": {"compiler": "pdflatex"},
        "sources": [{"filename": "main.tex", "usage": "toplevel"}],
    }, indent=2) + "\n", encoding="utf-8")

    bad = [f.name for f in OUT.iterdir() if " " in f.name or f.name.startswith(".") or f.is_dir()]
    if bad:
        raise SystemExit(f"non-flat or badly named entries: {bad}")

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(OUT).as_posix())

    # clean-room compile check (4 passes, as arXiv would do)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(tmp)
        for _ in range(4):
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=tmp,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log = Path(tmp, "main.log").read_text(encoding="latin-1")
        errors = log.count("\n!")
        undefined = len(re.findall(r"(Citation|Reference) .* undefined", log))
        pages = re.search(r"Output written on main\.pdf \((\d+) pages", log)
    n = sum(1 for _ in OUT.iterdir())
    print(f"{n} files (flat), figures: {sorted(used_figs)}")
    print(f"-> {ZIP} ({ZIP.stat().st_size // 1024} KB)")
    print(f"clean-room compile: errors={errors}, undefined refs/cites={undefined}, "
          f"pages={pages.group(1) if pages else '?'}")


if __name__ == "__main__":
    main()
