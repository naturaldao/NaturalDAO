"""Merge the coding of the 8 October 2026 update search (paper/review/UPDATE_SEARCH_2026-10-08.md).

Inputs (paper/review/coding/): coding_update_{U1..U4,Z1,Z2}.csv, quality_update_*.csv and the blind second
coder's second_coder_update_B{1,2,3}.csv. RESOLVED holds the adjudicated code for every disagreement.
Outputs: data/evidence_coding_update_2026-10-08.csv, data/quality_appraisal_update_2026-10-08.csv,
data/coder_agreement_update_2026-10-08.csv and paper/counts_update.tex (macros prefixed \\nU...).
The main-window files and paper/counts.tex are not touched.
Run: python scripts/merge_update.py
"""
import collections
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_coding import cohen_kappa  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CODING = ROOT / "paper" / "review" / "coding"
GROUPS = ["U1", "U2", "U3", "U4", "Z1", "Z2"]
TAG = "2026-10-08"
# (doc, axis) -> (code, comparator, note): adjudicated outcome of first/second-coder disagreements
# from paper/review/coding/adjudication_update.md (third coder, 2026-10-08)
RESOLVED = {
    ("arx03073", "G4"): ("Q", "none", "Low in-domain ECE after security fine-tuning; general-transfer ECE 21.10% vs 4.19% init (App. H)"),
    ("arx03324", "G7"): ("S", "better", "$0.033/1K, 336 ms vs $0.120-1.177, 844-1426 ms; 1.6 F1 below Sol, no training"),
    ("arx03387", "G6"): ("Q", "none", "Gate thresholds fail 6/12 transfers; restored only by target recalibration (Sec. 3.1)"),
    ("arx03935", "G1"): ("S", "similar", "AgentHarm 84.54% vs 61.86-85.57% generative; level with best, no added condition"),
    ("arx05107", "G6"): ("Q", "better", "Agents beat System-2-only but zero escalation calls logged, delta unrecoverable (Table 8)"),
    ("arx06625", "G3"): ("Q", "none", "Order swap flips 8.8% of winners, bias -0.036; scale r=0.982; no comparator or criterion"),
    ("arx06744", "G1"): ("N", "worse", "Macro F1 0.705 below all generative (0.741-0.901); passes 128/201 harmless look-alikes"),
    ("arx06744", "G4"): ("Q", "mixed", "Guardrail ECE 0.158, 12.2% wrong at >=0.99; other tracks 0.025-0.084"),
    ("arx07177", "G3"): ("S", "better", "Order-flip 0.0002 vs 0.2188 generative; length shift -0.023 vs -0.217"),
    ("arx07716", "G3"): ("Q", "better", "Wording swings 26 pts, label-first -19.6 pts; shuffle <=0.6 pts, menu predictable"),
    ("arx09188", "G3"): ("S", "better", "Both-order agreement 94.8% vs 90.6% (TREC), 86.7% vs 72.0% (MS MARCO)"),
    ("arx09188", "G7"): ("Q", "mixed", "Cheap labels; reranker matches but chess +2.8 vs +16.7, Othello/Connect-4 weakened"),
    ("arx09683", "G3"): ("N", "mixed", "Shuffle cuts accuracy for most typed models; collect bias 1.6-1.8x chance either order"),
    ("arx09896", "G4"): ("Q", "better", "Chip ECE 0.0032 needs target fine-tuning; JevBench ECE 0.163/0.358"),
    ("arx09896", "G7"): ("Q", "mixed", "Faster, but JEV 678/5000 failures, 84.52% FFD; Chip needs task training"),
    ("arx09937", "G7"): ("Q", "mixed", "0.19 s, $18.69 vs local 72B 2 s, data on site; needs recalibration and operator"),
    ("zen22941164", "G4"): ("S", "none", "ECE <=0.06 in-domain, <=0.10 out of domain, no recalibration; DONE threshold works"),
    ("zen23005202", "G1"): ("S", "similar", "Mean 83.6/84.2 vs 85.6/84.8 frontier LLMs on five benchmarks, no training"),
    ("zen23050542", "G1"): ("Q", "none", "AUC 0.9827 > TITAN-SR, but untuned threshold >=99% recall in 16/22 reviews only"),
    ("zen23088660", "G4"): ("Q", "none", "Every band underconfident (0.60-0.70 band right 74.5-82.6%); conservative, not calibrated"),
    ("zen23221456", "G4"): ("N", "worse", "ECE 0.21, Brier 0.283 worse than constant; only generative Qwen beats constant"),
}


def rating(q):
    """Same design-strength rule as merge_coding.py."""
    design, size, indep = q["design"].strip(), q["size_uncertainty"].strip(), q["independence"].strip()
    if design in ("single-run", "case study", "non-empirical") or size == "none":
        return "weaker"
    if design in ("preregistered", "held-out") and size == "n+CI" and indep == "independent":
        return "stronger"
    return "moderate"


def main():
    rows, qual = [], {}
    for g in GROUPS:
        for r in csv.DictReader((CODING / f"coding_update_{g}.csv").open(encoding="utf-8")):
            r = {k.strip(): (v or "").strip() for k, v in r.items()}
            r["group"] = g
            rows.append(r)
        for q in csv.DictReader((CODING / f"quality_update_{g}.csv").open(encoding="utf-8")):
            q = {k.strip(): (v or "").strip() for k, v in q.items()}
            q["quality"] = rating(q)
            qual[q["doc"]] = q

    second = {}
    for b in ("B1", "B2", "B3"):
        p = CODING / f"second_coder_update_{b}.csv"
        if p.exists():
            for s in csv.DictReader(p.open(encoding="utf-8")):
                second[(s["doc"].strip(), s["axis"].strip())] = s["code"].strip()

    out, agree = [], []
    for r in rows:
        key = (r["doc"], r["axis"])
        b = second.get(key, "")
        if r["empirical"] == "yes" and b:
            res = RESOLVED.get(key)
            agree.append({"doc": key[0], "axis": key[1], "first": r["code"], "second": b,
                          "resolved": res[0] if res else (r["code"] if r["code"] == b else ""),
                          "note": res[2] if res else ""})
            if res:
                r["code"], r["comparator"] = res[0], res[1]
                r["rationale"] += f" [Adjudicated: {res[2]}]"
        tally = "yes" if r["empirical"] == "yes" and r["system"] not in ("", "none") else "no"
        out.append({"doc": key[0], "source": "zenodo" if key[0].startswith("zen") else "arxiv", "set": r["set"],
                    "axis": key[1], "code": r["code"], "empirical": r["empirical"], "in_tally": tally,
                    "system": r["system"], "jev_version": r["jev_version"], "comparator": r["comparator"],
                    "quality": qual.get(key[0], {}).get("quality", ""), "rationale": r["rationale"]})
    out.sort(key=lambda r: (r["axis"], r["doc"]))
    with (ROOT / "data" / f"evidence_coding_update_{TAG}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    qf = ["doc", "verification", "independence", "design", "size_uncertainty", "quality", "notes"]
    with (ROOT / "data" / f"quality_appraisal_update_{TAG}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=qf, extrasaction="ignore")
        w.writeheader()
        w.writerows(q for _, q in sorted(qual.items()))
    with (ROOT / "data" / f"coder_agreement_update_{TAG}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc", "axis", "first", "second", "resolved", "note"])
        w.writeheader()
        w.writerows(agree)

    pairs = [(a["first"], a["second"]) for a in agree if a["first"] in "SQN" and a["second"] in "SQN"]
    po, kappa = cohen_kappa(pairs)
    rng = random.Random(20261008)
    boots = []
    for _ in range(10000):
        try:
            boots.append(cohen_kappa([pairs[rng.randrange(len(pairs))] for _ in pairs])[1])
        except ZeroDivisionError:
            pass
    boots.sort()
    tallied = [r for r in out if r["in_tally"] == "yes"]
    docs = {r["doc"] for r in tallied}
    c = collections.Counter(r["code"] for r in tallied)
    strong = collections.Counter(r["code"] for r in tallied if r["quality"] == "stronger")
    counts = {
        "nUDocs": len(qual), "nUCoded": len(docs),
        "nUArxiv": len({d for d in docs if d.startswith("arx")}), "nUZenodo": len({d for d in docs if d.startswith("zen")}),
        "nURows": len(tallied), "nUS": c["S"], "nUQ": c["Q"], "nUN": c["N"],
        "nUStrongRows": sum(strong.values()), "nUStrongS": strong["S"], "nUStrongQ": strong["Q"], "nUStrongN": strong["N"],
        "nUKappaN": len(pairs), "nUKappaAgree": f"{sum(a == b for a, b in pairs)} of {len(pairs)}",
        "nUKappa": f"{kappa:.2f}", "nUKappaLo": f"{boots[int(0.025 * len(boots))]:.2f}",
        "nUKappaHi": f"{boots[int(0.975 * len(boots)) - 1]:.2f}",
    }
    for s in ("post-window", "late-indexed", "re-screened"):
        counts["nUSet" + s.title().replace("-", "")] = len({r["doc"] for r in tallied if r["set"] == s})
    lines = [f"% Generated by scripts/merge_update.py ({TAG} update search); do not edit by hand."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in counts.items()]
    (ROOT / "paper" / "counts_update.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for k, v in counts.items():
        print(f"{k:22} {v}")

    print("\nper requirement, update set (S/Q/N, comparator better/similar/worse/mixed):")
    main_rows = [r for r in csv.DictReader((ROOT / "data" / "evidence_coding.csv").open(encoding="utf-8")) if r["in_tally"] == "yes"]
    for ax in sorted({r["axis"] for r in tallied} | {r["axis"] for r in main_rows}):
        u = collections.Counter(r["code"] for r in tallied if r["axis"] == ax)
        m = collections.Counter(r["code"] for r in main_rows if r["axis"] == ax)
        uc = collections.Counter(r["comparator"] for r in tallied if r["axis"] == ax)
        print(f"  {ax}: update S{u['S']} Q{u['Q']} N{u['N']} | main S{m['S']} Q{m['Q']} N{m['N']} | "
              f"update comparators b{uc['better']} s{uc['similar']} w{uc['worse']} m{uc['mixed']} n{uc['none']}")
    print("\ndisagreements (unresolved):",
          [(a["doc"], a["axis"], a["first"], a["second"]) for a in agree if a["first"] != a["second"] and not a["note"]])
    missing = sorted({r["doc"] for r in out} - set(qual))
    if missing:
        print("WARNING no quality row for", missing)
    no_second = sorted(k for k in {(r["doc"], r["axis"]) for r in out if r["empirical"] == "yes"} if k not in second)
    print("empirical pairs without a second code:", no_second)


if __name__ == "__main__":
    main()
