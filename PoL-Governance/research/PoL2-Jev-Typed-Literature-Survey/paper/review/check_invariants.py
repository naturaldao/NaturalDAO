"""Check that a style edit of a section file changed wording only.

Compares a file with its snapshot and fails if any of these differ (as multisets):
numbers, citation keys, cross-reference and label keys, \\clause{}/\\art{} arguments, count macros (\\nXxx{}),
inline math, quoted passages (``...''), environment begin/end markers and table/figure blocks.
Usage: python check_invariants.py <snapshot_dir> <sections_dir> file1.tex [file2.tex ...]
"""
import re
import sys
from collections import Counter
from pathlib import Path

FLOAT = re.compile(r"\\begin\{(table|figure|longtable|tabularx)\*?\}.*?\\end\{\1\*?\}", re.S)


def features(s):
    s_nofloat = FLOAT.sub("", s)
    f = {}
    f["floats"] = Counter(m.group(0) for m in FLOAT.finditer(s))
    f["numbers"] = Counter(re.findall(r"(?<![A-Za-z\\])\d+(?:[.,]\d+)*", s_nofloat))
    f["cites"] = Counter(k.strip() for m in re.finditer(r"\\cite[pt]?\{([^}]*)\}", s) for k in m.group(1).split(","))
    f["refs"] = Counter(k.strip() for m in re.finditer(r"\\(?:[cC]ref|ref|hyperref\[|label)\{?([^}\]]*)[}\]]", s)
                        for k in m.group(1).split(","))
    f["clauses"] = Counter(re.findall(r"\\(?:[cC]lause|[aA]rt)\{[^}]*\}", s))
    f["macros"] = Counter(re.findall(r"\\n[A-Z]\w*\{\}", s))
    f["math"] = Counter(re.findall(r"(?<!\\)\$(?:[^$\\]|\\.)+?(?<!\\)\$", s_nofloat.replace("\\$", "")))
    f["dollars"] = Counter(re.findall(r"\\\$[\d.,]+", s))
    f["quotes"] = Counter(re.findall(r"``[^']*?''", s_nofloat))
    f["envs"] = Counter(re.findall(r"\\(?:begin|end)\{[^}]*\}", s_nofloat))
    f["marks"] = Counter(re.findall(r"\\[gz]mark\{\}", s))
    return f


def main():
    snap, cur = Path(sys.argv[1]), Path(sys.argv[2])
    bad = 0
    for name in sys.argv[3:]:
        a = (snap / name).read_text(encoding="utf-8")
        b = (cur / name).read_text(encoding="utf-8")
        fa, fb = features(a), features(b)
        probs = []
        for k in fa:
            if fa[k] != fb[k]:
                lost = fa[k] - fb[k]
                added = fb[k] - fa[k]
                probs.append(f"  {k}: lost {dict(lost) if k != 'floats' else len(lost)} added {dict(added) if k != 'floats' else len(added)}")
        wa, wb = len(a.split()), len(b.split())
        status = "OK" if not probs else "FAIL"
        print(f"{name}: {status}  words {wa} -> {wb}")
        for p in probs:
            print(p[:600])
        bad += bool(probs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
