"""Merge the v0.3 evidence coding and quality appraisal, compute coder agreement, write the data files.

Inputs:  paper/review/coding/coding_group{1..4}.csv, quality_group{1..4}.csv, second_coder.csv
Outputs: data/evidence_coding.csv, data/quality_appraisal.csv, data/coder_agreement.csv,
         paper/counts.tex (corpus counts and agreement statistics used in the text)
Run: python scripts/merge_coding.py
"""
import csv
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODING = ROOT / "paper" / "review" / "coding"

# grey-literature short ids used by the coders -> bibliography keys
GREY = {"checkpoint": "checkpoint2026jev", "simmons": "simmons2026saidno", "zhbench": "qin2026zhdecisionbench",
        "replication": "jkf87_2026replication", "grazian": "grazian2026calibrated", "bernoulli": "yurin2026confident",
        "sev": "le2026sev", "molas": "molas2026calibrated", "willison": "willison2026jev"}
# documents read in full and then excluded from the counted corpus (cited as context only)
EXCLUDED = {
    "arx22664": "no typed model measured or built (harness paper)",
    "zen22953637": "deterministic rule engine; no typed model despite the name",
    "willison2026jev": "commentary without original measurements",
    "molas2026calibrated": "statistical argument without original measurements",
}
# rows removed after resolving coder disagreement (off-axis)
DROP = {("zen22885291", "G2"): "measures Jev detecting injection (a G1 task), not attacks on Jev"}
# resolution of each first/second-coder disagreement after re-reading the source
RESOLVED = {
    ("arx31142", "G6"): ("Q", "gate catches most flips but passes 12.6% and floods review: mixed, not a failure"),
    ("arx33282", "G7"): ("Q", "matches or beats frontier models on several but not all metrics: mixed"),
    ("zen22885291", "G2"): ("dropped", "off-axis: detection of injection belongs to G1"),
    ("zen22901853", "G5"): ("Q", "misleading fields come from access layers, not the typed model"),
}
# codes changed after review (round 2): (code, comparator, reason)
OVERRIDE = {
    ("arx34862", "G1"): ("Q", "mixed", "wins on 2 of 4 benchmarks with lower precision; mixed across tasks is Q under v3"),
    # round 12 (2026-10-08) rule-(iv) audit of main-window G2/G3/G6 rows; see paper/review/AUDIT.md
    ("arx00831", "G3"): ("N", "none", "order reversal flips 32.8-33.4%; rotation averaging is an added mitigation, so rule (iv) gives N"),
    ("arx35865", "G3"): ("N", "none", "base model flips 23.5% under relabelling; only the authors' added training lowers it, so rule (iv) gives N"),
}
TRACKERS = 2  # All about Jev, Awesome System One Models: retrieval routes, not evidence


def bibkey(doc):
    return GREY.get(doc, doc)


def kind(key):
    if key.startswith("arx"):
        return "arxiv"
    if key.startswith("zen"):
        return "zenodo"
    if key == "alphaRAG":
        return "alphaxiv"
    return "grey"


def cohen_kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return po, (po - pe) / (1 - pe)


def main():
    rows, qual = [], {}
    for g in range(1, 5):
        for r in csv.DictReader((CODING / f"coding_group{g}.csv").open(encoding="utf-8")):
            r["doc"] = bibkey(r["doc"].strip())
            if (r["doc"], r["axis"]) in OVERRIDE:
                r["code"], r["comparator"], note = OVERRIDE[(r["doc"], r["axis"])]
                r["rationale"] = r["rationale"] + " [Recoded in review: " + note + "]"
            if (r["doc"], r["axis"]) not in DROP:
                rows.append(r)
        for q in csv.DictReader((CODING / f"quality_group{g}.csv").open(encoding="utf-8")):
            q["doc"] = bibkey(q["doc"].strip())
            qual[q["doc"]] = q
    # design-strength rating (v0.3 round 2): stronger needs a preregistered or held-out design, sizes with
    # intervals or tests, AND evaluation of a system the authors did not build; weaker if single run, case
    # study, non-empirical or no uncertainty reported; moderate otherwise.
    for q in qual.values():
        design, size, indep = q["design"].strip(), q["size_uncertainty"].strip(), q["independence"].strip()
        if design in ("single-run", "case study", "non-empirical") or size == "none":
            q["quality"] = "weaker"
        elif design in ("preregistered", "held-out") and size == "n+CI" and indep == "independent":
            q["quality"] = "stronger"
        else:
            q["quality"] = "moderate"
    out = []
    for r in rows:
        excl = EXCLUDED.get(r["doc"], "")
        tally = "yes" if (r["empirical"] == "yes" and not excl and r["system"] != "none") else "no"
        out.append({"doc": r["doc"], "source": kind(r["doc"]), "axis": r["axis"], "code": r["code"],
                    "empirical": r["empirical"], "in_tally": tally, "system": r["system"],
                    "jev_version": r["jev_version"], "comparator": r["comparator"],
                    "quality": qual.get(r["doc"], {}).get("quality", ""), "excluded_reason": excl,
                    "rationale": r["rationale"]})
    out.sort(key=lambda r: (r["axis"], r["doc"]))
    fields = list(out[0])
    with (ROOT / "data" / "evidence_coding.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    qrows = []
    for k, q in sorted(qual.items()):
        q = dict(q)
        q["source"] = kind(k)
        q["excluded_reason"] = EXCLUDED.get(k, "")
        qrows.append(q)
    qf = ["doc", "source", "verification", "independence", "design", "size_uncertainty", "quality", "excluded_reason", "notes"]
    with (ROOT / "data" / "quality_appraisal.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=qf, extrasaction="ignore")
        w.writeheader()
        w.writerows(qrows)

    # agreement with the blind second coder (pairs both coded S/Q/N)
    first = {(r["doc"], r["axis"]): r["code"] for r in out}
    pairs, agree_rows = [], []
    for s in csv.DictReader((CODING / "second_coder.csv").open(encoding="utf-8")):
        key = (bibkey(s["doc"].strip()), s["axis"].strip())
        a, b = first.get(key), s["code"].strip()
        status = "compared" if a in ("S", "Q", "N") and b in ("S", "Q", "N") else "not compared"
        if status == "compared":
            pairs.append((a, b))
        if key in DROP and status == "not compared":
            status, a = "compared", "Q"  # first coder's code before the row was dropped
            pairs.append((a, b))
        res = RESOLVED.get(key, ("", ""))
        agree_rows.append({"doc": key[0], "axis": key[1], "first": a or "", "second": b, "status": status,
                           "resolved": res[0] or (a if status == "compared" else ""), "note": res[1]})
    with (ROOT / "data" / "coder_agreement.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc", "axis", "first", "second", "status", "resolved", "note"])
        w.writeheader()
        w.writerows(agree_rows)
    po, kappa = cohen_kappa(pairs)

    # corpus counts: every document read in full, minus exclusions; background arXiv papers come from papers.csv
    papers = list(csv.DictReader((ROOT / "data" / "papers.csv").open(encoding="utf-8")))
    arxiv_ids = {"arx" + p["arxiv_id"].split(".")[1] for p in papers if p["arxiv_id"]}
    arxiv_ids -= set(EXCLUDED)
    zen_ids = {q for q in qual if q.startswith("zen")} - set(EXCLUDED)
    grey_ids = {q for q in qual if kind(q) == "grey"} - set(EXCLUDED)
    coded = {r["doc"] for r in out if r["in_tally"] == "yes"}
    n_papers = len(arxiv_ids) + len(zen_ids) + 1
    tally = collections.Counter(r["code"] for r in out if r["in_tally"] == "yes")
    counts = {
        "nArxiv": len(arxiv_ids), "nZenodo": len(zen_ids), "nOther": len(zen_ids) + 1, "nPapers": n_papers,
        "nGrey": len(grey_ids), "nCoded": len(coded), "nRows": sum(tally.values()),
        "nS": tally["S"], "nQ": tally["Q"], "nN": tally["N"], "nPolClauses": 28,
        "nKappaN": len(pairs), "nKappaAgree": f"{sum(a == b for a, b in pairs)} of {len(pairs)}",
        "nKappa": f"{kappa:.2f}",
    }
    # bootstrap 95% interval for kappa (10,000 resamples of the sampled pairs, fixed seed)
    import random
    rng = random.Random(20261004)
    boots = []
    for _ in range(10000):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        try:
            boots.append(cohen_kappa(sample)[1])
        except ZeroDivisionError:
            pass
    boots.sort()
    counts["nKappaLo"] = f"{boots[int(0.025 * len(boots))]:.2f}"
    counts["nKappaHi"] = f"{boots[int(0.975 * len(boots)) - 1]:.2f}"
    first_marg = collections.Counter(a for a, _ in pairs)
    counts["nKappaMarg"] = f"S {first_marg['S']}, Q {first_marg['Q']}, N {first_marg['N']}"
    tallied = [r for r in out if r["in_tally"] == "yes"]
    strong = collections.Counter(r["code"] for r in tallied if r["quality"] == "stronger")
    counts.update({"nStrongS": strong["S"], "nStrongQ": strong["Q"], "nStrongN": strong["N"],
                   "nStrongRows": sum(strong.values())})
    noz = collections.Counter(r["code"] for r in tallied if r["source"] != "zenodo")
    counts.update({"nNoZenS": noz["S"], "nNoZenQ": noz["Q"], "nNoZenN": noz["N"], "nNoZenRows": sum(noz.values())})
    qcount = collections.Counter(q["quality"] for k, q in qual.items() if k not in EXCLUDED)
    counts.update({"nStronger": qcount["stronger"], "nModerate": qcount["moderate"], "nWeaker": qcount["weaker"],
                   "nAppraised": sum(qcount.values())})
    lines = ["% Generated by scripts/merge_coding.py; do not edit by hand."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in counts.items()]
    (ROOT / "paper" / "counts.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for k, v in counts.items():
        print(f"{k:12} {v}")
    disagreements = [(r["doc"], r["axis"], r["first"], r["second"]) for r in agree_rows
                     if r["status"] == "compared" and r["first"] != r["second"]]
    print("disagreements:", disagreements)
    print("not compared:", [(r["doc"], r["axis"], r["first"], r["second"]) for r in agree_rows if r["status"] != "compared"])
    missing_q = sorted({r["doc"] for r in out} - set(qual))
    if missing_q:
        print("WARNING no quality row for", missing_q)
    print("arXiv in papers.csv but not coded (background tier):", len(arxiv_ids - {r['doc'] for r in out}))


if __name__ == "__main__":
    main()
