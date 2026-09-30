"""Equal Connection counterfactual on the DAO experiment's real ballots.

Question: in the 20/80 conditions of Sharma et al. (2026), would the outcome
change if every participant had the same token budget but split it the same
way? (PoLEn 4.3.1: persons are equal; 4.3.3 "equal access to resources".)

Two entry points:

* :func:`from_published` -- uses only numbers published with the article
  (Table 1 mean budget shares and the per-option token totals). For *ranked*
  (linear) conditions the equal-budget totals are exactly ``n * mean share``,
  so the counterfactual is exact. For quadratic conditions it is not
  computable from means and is reported as such.
* :func:`replay_osf` -- per-ballot replay on the OSF vote files
  (<https://osf.io/q6snh/>, not redistributed here), with a bootstrap over
  ballots for how stable each winner is.

Caveat for both: people might have split their tokens differently had the
budgets been equal. The counterfactual keeps their split fixed.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .voting import Ballot, Rule, equalize, tally

REPO_ROOT = Path(__file__).resolve().parents[2]
OSF_FILES = {1: "anonymous_round1_vote.csv", 2: "anonymous_round3_vote.csv"}  # "round3" = article's round 2


def rule_for(cond: str) -> Rule:
    return "quadratic" if cond.startswith("quadratic") else "linear"


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# Published aggregates
# --------------------------------------------------------------------------

def from_published(data_dir: str | Path | None = None) -> list[dict]:
    d = Path(data_dir) if data_dir else REPO_ROOT / "data"
    means = {(r["round"], r["cond"]): r for r in _read(d / "sharma2026_table1_means.csv")}
    rows = []
    for r in _read(d / "sharma2026_token_totals.csv"):
        key = (r["round"], r["cond"])
        tokens = [float(r[f"tokens_{i}"]) for i in range(1, 5)]
        shares = [float(means[key][f"mean_r{i}"]) for i in range(1, 5)]
        out = {"round": int(r["round"]), "cond": r["cond"], "n": int(r["n"]),
               "rule": rule_for(r["cond"])}
        if out["rule"] == "linear":
            actual = max(range(4), key=lambda j: tokens[j]) + 1
            equal = max(range(4), key=lambda j: shares[j]) + 1
            s = sorted(shares, reverse=True)
            out.update(actual_winner=actual, equal_budget_winner=equal, flipped=actual != equal,
                       equal_budget_margin=round(s[0] - s[1], 4), note="exact from Table 1 means")
        else:
            out.update(actual_winner="", equal_budget_winner="", flipped="",
                       equal_budget_margin="", note="needs per-ballot data (quadratic)")
        rows.append(out)
    return rows


# --------------------------------------------------------------------------
# Per-ballot replay
# --------------------------------------------------------------------------

def read_osf_votes(data_dir: str | Path) -> list[dict]:
    """Rows with round, cond, phase, budget and tokens from the two OSF vote files."""
    out = []
    for rnd, name in OSF_FILES.items():
        path = Path(data_dir) / name
        if not path.exists():
            raise FileNotFoundError(f"{path} not found; download the OSF files (https://osf.io/q6snh/)")
        for i, r in enumerate(_read(path)):
            cond = r.get("pod-categorical") or r.get("pod")
            out.append({
                "round": rnd, "cond": cond, "phase": r.get("phase", "main"),
                "voter": f"R{rnd}_{r.get('user') or i}",
                "budget": float(r["votes_given"]),
                "tokens": tuple(float(r[f"choice_{j}"]) for j in range(1, 5)),
            })
    return out


def _winner(ballots: list[Ballot], rule: Rule) -> int:
    return tally(ballots, rule).winner + 1


def replay_osf(rows: Iterable[dict], boot: int = 2000, seed: int = 20260929,
               include_pilots: bool = True) -> list[dict]:
    groups: dict[tuple[int, str], list[Ballot]] = defaultdict(list)
    for r in rows:
        if not include_pilots and r["phase"] == "pilots":
            continue
        groups[(r["round"], r["cond"])].append(Ballot(r["voter"], r["tokens"], r["budget"]))
    rng = random.Random(seed)
    out = []
    for (rnd, cond), ballots in sorted(groups.items()):
        rule = rule_for(cond)
        eq = [equalize(b) for b in ballots]
        actual, equal = _winner(ballots, rule), _winner(eq, rule)
        flips = same_actual = same_equal = 0
        for _ in range(boot):
            idx = [rng.randrange(len(ballots)) for _ in ballots]
            a = _winner([ballots[i] for i in idx], rule)
            e = _winner([eq[i] for i in idx], rule)
            flips += a != e
            same_actual += a == actual
            same_equal += e == equal
        t_a, t_e = tally(ballots, rule), tally(eq, rule)
        out.append({
            "round": rnd, "cond": cond, "n": len(ballots), "rule": rule,
            "unequal_budgets": len({b.budget for b in ballots}) > 1,
            "actual_winner": actual, "actual_shares": [round(s, 4) for s in t_a.shares],
            "equal_budget_winner": equal, "equal_budget_shares": [round(s, 4) for s in t_e.shares],
            "flipped": actual != equal,
            "boot_p_flip": round(flips / boot, 4),
            "boot_p_actual_winner_stable": round(same_actual / boot, 4),
            "boot_p_equal_winner_stable": round(same_equal / boot, 4),
        })
    return out


def write_rows(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path
