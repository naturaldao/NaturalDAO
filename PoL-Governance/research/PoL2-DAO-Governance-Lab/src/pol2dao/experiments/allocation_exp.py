"""E14, E15: two checks on the ch. 6 and ch. 7 clauses that the voting experiments do not reach.

E14  needs reporting      "按需分配" (ch. 6 art. 6) when the need signal is a report that can be inflated
E15  reviewer correlation how much a second, third ... reviewer helps when all reviewers share one base
                          model (ch. 7 art. 6 step 3: EAP ethics check by Skills), and what an
                          independent escalation path buys instead

Both are small models of a mechanism, not evidence about real people or real models. The
computations use only the standard library; E15 is closed-form (no Monte Carlo error).
"""

from __future__ import annotations

import math
import heapq
import random
from pathlib import Path
from statistics import NormalDist, mean, pstdev

from ..plotstyle import DOWN, PALETTE, UP, finalize_figure, legend_panel, new_figure, plot_line
from ._common import fig_path, seed, write_csv, _ci

_ND = NormalDist()


# ---------------------------------------------------------------------------
# E14 needs reporting
# ---------------------------------------------------------------------------

N_AGENTS = 200
SCARCITY = 0.6          # supply = 60 % of total true need
RULES = ("R1", "R2", "R3")
RULE_LABEL = {
    "R1": "R1 proportional to report",
    "R2": "R2 capped water-filling",
    "R3": "R3 = R2 + ex-ante audit",
}
RULE_STYLE = {   # R1 is the baseline clause reading (red); R3 adds the verifiable chain (blue)
    "R1": {"color": PALETTE["red_strong"], "marker": "o"},
    "R2": {"color": PALETTE["green_3"], "marker": "D"},
    "R3": {"color": PALETTE["blue_main"], "marker": "^"},
}


def water_fill(reports: list[float], supply: float) -> list[float]:
    """x_i = min(r_i, lam) with sum x_i = supply (everyone fully served if supply suffices)."""
    if sum(reports) <= supply:
        return list(reports)
    rs = sorted(reports)
    left = supply
    n = len(rs)
    lam = rs[-1]
    for i, r in enumerate(rs):
        share = left / (n - i)
        if r >= share:
            lam = share
            break
        left -= r
    return [min(r, lam) for r in reports]


def needs_once(rng: random.Random, f: float, k: float, p_audit: float, n: int = N_AGENTS) -> dict[str, tuple[float, float]]:
    """One draw. Returns {rule: (honest fill rate, efficiency)}."""
    need = [rng.lognormvariate(0.0, 0.8) for _ in range(n)]
    supply = SCARCITY * sum(need)
    inflate = [rng.random() < f for _ in range(n)]
    rep = [k * d if s else d for d, s in zip(need, inflate)]
    caught = [s and rng.random() < p_audit for s in inflate]
    rep3 = [d if c else r for d, r, c in zip(need, rep, caught)]
    tot = sum(rep)
    alloc = {
        "R1": [supply * r / tot for r in rep],
        "R2": water_fill(rep, supply),
        "R3": water_fill(rep3, supply),
    }
    out = {}
    honest = [i for i in range(n) if not inflate[i]]
    for name, x in alloc.items():
        used = [min(xi, d) for xi, d in zip(x, need)]
        fill = mean(used[i] / need[i] for i in honest) if honest else float("nan")
        out[name] = (fill, sum(used) / supply)
    return out


def _ci(xs: list[float]) -> float:
    xs = [x for x in xs if x == x]
    return 1.96 * pstdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def needs_cell(f: float, k: float, p_audit: float, reps: int) -> dict[str, dict[str, float]]:
    rng = random.Random(seed("E14", f, k, p_audit))
    acc = {r: ([], []) for r in RULES}
    for _ in range(reps):
        o = needs_once(rng, f, k, p_audit)
        for r in RULES:
            acc[r][0].append(o[r][0])
            acc[r][1].append(o[r][1])
    res = {}
    for r in RULES:
        fill = [x for x in acc[r][0] if x == x]
        res[r] = {"honest_fill": mean(fill) if fill else float("nan"), "honest_fill_ci": _ci(fill),
                  "efficiency": mean(acc[r][1]), "efficiency_ci": _ci(acc[r][1])}
    return res


def e14_needs_report(out: Path, reps: int, log) -> list[Path]:
    fs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    rows, grid = [], {}
    for f in fs:
        grid[f] = needs_cell(f, 2.0, 0.5, reps)
        for r in RULES:
            rows.append({"rule": r, "f": f, "k": 2.0, "p_audit": 0.5, "reps": reps, **grid[f][r]})
        log(f"E14 f={f}")
    write_csv(rows, out, "e14_needs_report.csv")
    sens = []
    for k in (1.5, 2.0, 3.0):
        for p in (0.2, 0.5, 0.8):
            c = needs_cell(0.3, k, p, max(2, reps // 2))
            for r in RULES:
                sens.append({"rule": r, "f": 0.3, "k": k, "p_audit": p, **c[r]})
    write_csv(sens, out, "e14_sensitivity.csv")

    fig, axes = new_figure(1, 3, panel=(6.2, 5.0))
    xs = [100 * f for f in fs]
    for ax, key, label in ((axes[0][0], "honest_fill", "needs met, honest agents" + UP),
                           (axes[0][1], "efficiency", "supply used on real need" + UP)):
        for r in RULES:
            st = RULE_STYLE[r]
            plot_line(ax, xs, [grid[f][r][key] for f in fs], color=st["color"], marker=st["marker"],
                      err=[grid[f][r][key + "_ci"] for f in fs], label=RULE_LABEL[r])
        ax.set_xlabel("share of agents inflating reports (%)")
        ax.set_ylabel(label)
    axes[0][0].set_ylim(0.3, 0.9)
    axes[0][1].set_ylim(0.9, 1.01)
    handles, labels = axes[0][0].get_legend_handles_labels()
    legend_panel(axes[0][2], handles, labels)
    return finalize_figure(fig, fig_path(out, "e14_needs_report"))


# ---------------------------------------------------------------------------
# E15 correlated reviewers and escalation
# ---------------------------------------------------------------------------

MU = 2.0            # single-reviewer separation (AUROC ~ 0.92); assumed
MU_HUMAN = 3.5      # independent human review; assumed
FR_TARGET = 0.10    # benign Skills wrongly rejected
PRIOR = 0.05        # share of harmful Skills among submissions (weights the escalation share only)
_CS = [-8 + 16 * i / 640 for i in range(641)]
_W = [_ND.pdf(c) * 16 / 640 for c in _CS]


def fa_mean(n: int, rho: float, mu: float = MU, fr: float = FR_TARGET) -> float:
    """Mean of n scores that share a common factor: Gaussian, closed form."""
    sd = math.sqrt(rho + (1 - rho) / n)
    q = sd * _ND.inv_cdf(1 - fr)
    return _ND.cdf((q - mu) / sd)


def _cdf_max(q: float, n: int, rho: float, shift: float = 0.0) -> float:
    """P(max of n scores <= q) with scores = shift + sqrt(rho) c + sqrt(1-rho) e."""
    a, b = math.sqrt(rho), math.sqrt(1 - rho)
    return sum(w * _ND.cdf((q - shift - a * c) / b) ** n for c, w in zip(_CS, _W))


def fa_any(n: int, rho: float, mu: float = MU, fr: float = FR_TARGET) -> float:
    """Reject if any reviewer rejects: threshold on the maximum, set to the benign FR."""
    lo, hi = -6.0, 12.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _cdf_max(mid, n, rho) < 1 - fr:
            lo = mid
        else:
            hi = mid
    return _cdf_max(hi, n, rho, shift=mu)


def escalation_frontier(budgets: list[float], mu: float = MU, mu_h: float = MU_HUMAN, fr: float = FR_TARGET,
                        prior: float = PRIOR, step: float = 0.025) -> list[dict]:
    """Single model, green/yellow/red bands, yellow goes to an independent human reviewer."""
    h_thr = mu_h / 2
    h_false = 1 - _ND.cdf(h_thr)
    h_miss = 1 - _ND.cdf(mu_h - h_thr)
    grid = [-1.0 + step * i for i in range(int(5.0 / step) + 1)]
    cb = [_ND.cdf(t) for t in grid]
    ch = [_ND.cdf(t - mu) for t in grid]
    pts = []
    for i, tg in enumerate(grid):
        for j in range(i, len(grid)):
            yb, yh = cb[j] - cb[i], ch[j] - ch[i]
            rejected = 1 - cb[j] + yb * h_false
            if rejected > fr:
                continue
            pts.append((prior * yh + (1 - prior) * yb, ch[i] + yh * h_miss, tg, grid[j], rejected))
    out = []
    for b in budgets:
        ok = [p for p in pts if p[0] <= b + 1e-12]
        if ok:
            e, fa, tg, tr, rj = min(ok, key=lambda p: p[1])
            out.append({"escalation_budget": b, "escalated": e, "fa": fa, "tau_green": tg, "tau_red": tr,
                        "benign_rejected": rj})
    return out


def e15_reviewer_correlation(out: Path, reps: int, log) -> list[Path]:
    ns = [1, 2, 3, 5, 7]
    rhos = [0.0, 0.5, 0.9]
    rows = []
    for rule, fn in (("any", fa_any), ("mean", fa_mean)):
        for rho in rhos:
            for n in ns:
                rows.append({"rule": rule, "rho": rho, "n": n, "mu": MU, "benign_rejected": FR_TARGET,
                             "harmful_passed": fn(n, rho)})
    write_csv(rows, out, "e15_reviewer_correlation.csv")
    log("E15 reviewers done")
    front = escalation_frontier([i / 20 for i in range(11)])
    write_csv(front, out, "e15_escalation.csv")

    fig, axes = new_figure(1, 4, panel=(5.4, 5.0))
    rho_style = {0.0: PALETTE["blue_main"], 0.5: PALETTE["teal"], 0.9: PALETTE["red_strong"]}
    by = {(r["rule"], r["rho"], r["n"]): r["harmful_passed"] for r in rows}
    for ax, rule, title in ((axes[0][0], "any", "reject if any reviewer rejects"),
                            (axes[0][1], "mean", "mean of reviewer scores")):
        for rho in rhos:
            plot_line(ax, ns, [by[(rule, rho, n)] for n in ns], color=rho_style[rho], label=f"ρ = {rho}")
        ax.set_title(title)
        ax.set_xlabel("number of reviewers (same base model)")
        ax.set_ylabel("harmful Skills passed" + DOWN)
        ax.set_ylim(0, 0.26)
        ax.set_xticks(ns)
    ax = axes[0][2]
    plot_line(ax, [100 * r["escalated"] for r in front], [r["fa"] for r in front], color=PALETTE["violet"],
              label="one model + independent human on yellow")
    for rho, ls in ((0.5, "--"), (0.9, ":")):
        ax.axhline(by[("mean", rho, 7)], color=PALETTE["black"], alpha=0.3, lw=3, ls=ls,
                   label=f"7 same-base reviewers, ρ = {rho}")
    ax.set_title("independent escalation")
    ax.set_xlabel("Skills escalated to a human (%)")
    ax.set_ylabel("harmful Skills passed" + DOWN)
    ax.set_ylim(0, 0.26)
    h1, l1 = axes[0][0].get_legend_handles_labels()
    h2, l2 = ax.get_legend_handles_labels()
    legend_panel(axes[0][3], h1 + h2, l1 + l2)
    log("E15 done")
    return finalize_figure(fig, fig_path(out, "e15_reviewer_correlation"))


# ---------------------------------------------------------------------------
# E16 non-market allocation across repeated rounds
# ---------------------------------------------------------------------------

E16_RULES = ("equal_rotation", "needs_priority", "floor_then_priority")
E16_LABEL = {"equal_rotation": "Equal priority + rotation", "needs_priority": "Urgency tiers + rotation",
             "floor_then_priority": "Basic floor + urgency tiers"}
E16_STYLE = {"equal_rotation": PALETTE["neutral_dark"], "needs_priority": PALETTE["blue_main"],
             "floor_then_priority": PALETTE["green_3"]}
E16_ROUNDS = 24
E16_N = 120
E16_SHOCK_ROUNDS = (6, 12, 18, 24)


def _rotating_queue(people: list[int], caps: list[int], allocated: list[int], needs: list[int],
                    supply: int, pointer: int) -> tuple[int, int]:
    """Allocate indivisible units by least reported-need fulfillment, rotating exact ties."""
    if not people or supply <= 0:
        return 0, pointer
    order = people[pointer % len(people):] + people[:pointer % len(people)]
    heap = [(allocated[i] / max(1, caps[i]), pos, i) for pos, i in enumerate(order)
            if allocated[i] < caps[i]]
    heapq.heapify(heap)
    used = 0
    while used < supply and heap:
        # No money, bidding, transferable credits, or price signal: a transparent service queue.
        _, pos, i = heapq.heappop(heap)
        allocated[i] += 1
        used += 1
        if allocated[i] < caps[i]:
            heapq.heappush(heap, (allocated[i] / max(1, caps[i]), pos, i))
    next_pointer = (pointer + max(1, used)) % len(people)
    return used, next_pointer


def _allocate_e16(needs: list[int], claims: list[int], tiers: list[int], supply: int,
                  prioritized: bool, pointers: list[int], basic_floor: bool = False) -> tuple[list[int], list[int]]:
    allocation = [0] * len(needs)
    left = supply
    # Honor a universal first-unit floor only when this round has enough to cover
    # every claimant. Under deeper scarcity, urgent needs take precedence.
    if basic_floor and left >= sum(c > 0 for c in claims):
        everyone = list(range(len(needs)))
        used, pointers[0] = _rotating_queue(everyone, [min(c, 1) for c in claims],
                                             allocation, needs, left, pointers[0])
        left -= used
    groups = sorted(set(tiers)) if prioritized else [0]
    for tier in groups:
        members = [i for i, t in enumerate(tiers) if t == tier] if prioritized else list(range(len(needs)))
        used, pointers[tier if prioritized else 0] = _rotating_queue(
            members, claims, allocation, needs, left, pointers[tier if prioritized else 0])
        left -= used
        if left <= 0:
            break
    return allocation, pointers


def needs_priority_simulation(rng: random.Random, f: float, reps: int = 120,
                              n: int = E16_N, rounds: int = E16_ROUNDS) -> dict[str, dict[str, float]]:
    """Repeated synthetic rationing. Tier 0 is life-critical; tier 2 is ordinary need."""
    totals = {r: {"weighted_fill": [], "critical_fill": [], "real_use": [], "overclaim_units": [],
                  "shock_critical_fill": []} for r in E16_RULES}
    for _ in range(reps):
        tiers = [rng.choices([0, 1, 2], weights=[0.2, 0.35, 0.45])[0] for _ in range(n)]
        inflated = [rng.random() < f for _ in range(n)]
        ptrs = {r: [rng.randrange(n) for _ in range(3)] for r in E16_RULES}
        need_sums = [0] * n
        accum = {r: {"weighted_numerator": 0.0, "weighted_denominator": 0.0, "critical_num": 0,
                     "critical_den": 0, "real_use": 0, "claims": 0, "allocated": 0,
                     "shock_critical_num": 0, "shock_critical_den": 0} for r in E16_RULES}
        for rd in range(1, rounds + 1):
            needs = [rng.randint(1, 8) for _ in range(n)]
            need_sums = [a + d for a, d in zip(need_sums, needs)]
            claims = [d * (2 if bad else 1) for d, bad in zip(needs, inflated)]
            shock = rd in E16_SHOCK_ROUNDS
            supply = int(sum(needs) * (0.10 if shock else 0.65))
            for rule in E16_RULES:
                alloc, ptrs[rule] = _allocate_e16(needs, claims, tiers, supply,
                                                  rule != "equal_rotation", ptrs[rule],
                                                  basic_floor=rule == "floor_then_priority")
                s = accum[rule]
                for i, (d, x) in enumerate(zip(needs, alloc)):
                    real = min(d, x)
                    weight = 3 - tiers[i]
                    s["weighted_numerator"] += weight * real
                    s["weighted_denominator"] += weight * d
                    if tiers[i] == 0:
                        s["critical_num"] += real
                        s["critical_den"] += d
                        if shock:
                            s["shock_critical_num"] += real
                            s["shock_critical_den"] += d
                    s["real_use"] += real
                    s["claims"] += claims[i]
                    s["allocated"] += x
        for rule in E16_RULES:
            s = accum[rule]
            totals[rule]["weighted_fill"].append(s["weighted_numerator"] / s["weighted_denominator"])
            totals[rule]["critical_fill"].append(s["critical_num"] / s["critical_den"])
            totals[rule]["real_use"].append(s["real_use"] / s["allocated"] if s["allocated"] else 0.0)
            totals[rule]["overclaim_units"].append((s["allocated"] - s["real_use"]) / max(1, s["allocated"]))
            totals[rule]["shock_critical_fill"].append(
                s["shock_critical_num"] / s["shock_critical_den"] if s["shock_critical_den"] else 0.0)
    return {r: {k: mean(v) for k, v in values.items()} for r, values in totals.items()}


def e16_nonmarket_allocation(out: Path, reps: int, log) -> list[Path]:
    fs = [0.0, 0.1, 0.2, 0.3, 0.4]
    rows, grid = [], {}
    for f in fs:
        rng = random.Random(seed("E16", f))
        grid[f] = needs_priority_simulation(rng, f, reps=max(2, reps))
        for rule in E16_RULES:
            rows.append({"rule": rule, "inflation_share": f, "inflation_factor": 2,
                         "agents": E16_N, "rounds": E16_ROUNDS, "reps": reps, **grid[f][rule]})
        log(f"E16 inflation_share={f:.1f}")
    write_csv(rows, out, "e16_nonmarket_allocation.csv")
    fig, axes = new_figure(1, 4, panel=(6.0, 5.0))
    xs = [100 * f for f in fs]
    for rule in E16_RULES:
        color = E16_STYLE[rule]
        for ax, metric, label in ((axes[0][0], "critical_fill", "critical needs met ↑"),
                                  (axes[0][1], "weighted_fill", "priority-weighted needs met ↑")):
            plot_line(ax, xs, [grid[f][rule][metric] for f in fs], color=color, marker="o",
                      label=E16_LABEL[rule])
        plot_line(axes[0][2], xs, [grid[f][rule]["real_use"] for f in fs], color=color, marker="o",
                  label=E16_LABEL[rule])
        plot_line(axes[0][3], xs, [grid[f][rule]["shock_critical_fill"] for f in fs],
                  color=color, marker="o", label=E16_LABEL[rule])
    for ax, label in ((axes[0][0], "critical needs met ↑"),
                      (axes[0][1], "priority-weighted needs met ↑"),
                      (axes[0][2], "allocated units used for real need ↑"),
                      (axes[0][3], "critical needs met during shocks ↑")):
        ax.set_xlabel("share inflating need claims (%)")
        ax.set_ylabel(label)
        ax.set_ylim(0, 1.02)
    axes[0][3].legend(frameon=False, fontsize=10, loc="lower left")
    return finalize_figure(fig, fig_path(out, "e16_nonmarket_allocation"))


# ---------------------------------------------------------------------------
# E17 priority classification and an appeal process
# ---------------------------------------------------------------------------

E17_CAPACITIES = (0.0, 0.10, 0.25)
E17_LABEL = {0.0: "no appeal", 0.10: "review up to 10%", 0.25: "review up to 25%"}
E17_COLORS = {0.10: PALETTE["blue_main"], 0.25: PALETTE["green_3"]}
E17_SENSITIVITY = 0.90
E17_FALSE_ACCEPT = 0.05


def classify_priority(true_tier: int, error_rate: float, rng: random.Random) -> int:
    """Symmetric adjacent-tier classification error; tier 0 is most urgent."""
    if true_tier not in (0, 1, 2):
        raise ValueError("priority tier must be 0, 1, or 2")
    if not 0 <= error_rate <= 1:
        raise ValueError("error_rate must lie in [0, 1]")
    if rng.random() >= error_rate:
        return true_tier
    if true_tier == 0:
        return 1
    if true_tier == 2:
        return 1
    return rng.choice((0, 2))


def resolve_priority_appeals(true_tiers: list[int], assessed: list[int], false_claimants: list[bool],
                             capacity_share: float, rng: random.Random,
                             sensitivity: float = E17_SENSITIVITY,
                             false_accept: float = E17_FALSE_ACCEPT) -> tuple[list[int], dict[str, float]]:
    """Apply a capacity-limited lottery for independent review of upward appeals.

    Valid appeals request the actual tier after an under-classification. False
    claimants request tier 0. Review outcomes have assumed sensitivity and false
    acceptance probability; these are scenario parameters, not empirical rates.
    """
    if not (len(true_tiers) == len(assessed) == len(false_claimants)):
        raise ValueError("appeal inputs must have equal lengths")
    if not 0 <= capacity_share <= 1:
        raise ValueError("capacity_share must lie in [0, 1]")
    effective = list(assessed)
    if capacity_share == 0 or not true_tiers:
        return effective, {"filed": 0, "reviewed": 0, "valid_filed": 0,
                           "valid_corrected": 0, "false_accepted": 0}

    appeals: list[tuple[int, int, bool]] = []
    for i, (truth, label, false_claim) in enumerate(zip(true_tiers, assessed, false_claimants)):
        if label > truth and rng.random() < 0.80:
            appeals.append((i, truth, True))
        elif false_claim and truth > 0 and label > 0 and rng.random() < 0.80:
            appeals.append((i, 0, False))
    cap = int(len(true_tiers) * capacity_share)
    reviewed = rng.sample(appeals, min(cap, len(appeals))) if cap else []
    valid_filed = sum(valid for _, _, valid in appeals)
    corrected = false_accepted = 0
    for i, requested_tier, valid in reviewed:
        if valid:
            if rng.random() < sensitivity:
                effective[i] = requested_tier
                corrected += 1
        elif rng.random() < false_accept:
            effective[i] = requested_tier
            false_accepted += 1
    return effective, {"filed": len(appeals), "reviewed": len(reviewed), "valid_filed": valid_filed,
                       "valid_corrected": corrected, "false_accepted": false_accepted}


def priority_appeal_cell(error_rate: float, false_share: float, capacity: float,
                         reps: int, n: int = E16_N, rounds: int = E16_ROUNDS) -> dict[str, float]:
    rng = random.Random(seed("E17", error_rate, false_share, capacity))
    run_metrics = {k: [] for k in ("critical_fill", "weighted_fill", "mispriority_units",
                                   "appeal_load", "valid_correction_rate", "false_accept_rate",
                                   "shock_critical_fill")}
    for _ in range(reps):
        true_tiers = [rng.choices([0, 1, 2], weights=[0.2, 0.35, 0.45])[0] for _ in range(n)]
        false_claimants = [rng.random() < false_share for _ in range(n)]
        pointers = [rng.randrange(n) for _ in range(3)]
        critical_num = critical_den = 0
        weighted_num = weighted_den = 0.0
        mispriority = allocated = 0
        shock_num = shock_den = 0
        filed_total = reviewed_total = valid_filed_total = corrected_total = false_accepted_total = 0
        for rd in range(1, rounds + 1):
            needs = [rng.randint(1, 8) for _ in range(n)]
            assessed = [classify_priority(tier, error_rate, rng) for tier in true_tiers]
            effective, appeals = resolve_priority_appeals(
                true_tiers, assessed, false_claimants, capacity, rng)
            claims = [d * (2 if bad else 1) for d, bad in zip(needs, false_claimants)]
            shock = rd in E16_SHOCK_ROUNDS
            supply = int(sum(needs) * (0.10 if shock else 0.65))
            allocation, pointers = _allocate_e16(
                needs, claims, effective, supply, True, pointers, basic_floor=True)
            for i, (d, amount) in enumerate(zip(needs, allocation)):
                real = min(d, amount)
                tier = true_tiers[i]
                weight = 3 - tier
                weighted_num += weight * real
                weighted_den += weight * d
                if tier == 0:
                    critical_num += real
                    critical_den += d
                    if shock:
                        shock_num += real
                        shock_den += d
                if effective[i] < tier:
                    mispriority += amount
                allocated += amount
            filed_total += appeals["filed"]
            reviewed_total += appeals["reviewed"]
            valid_filed_total += appeals["valid_filed"]
            corrected_total += appeals["valid_corrected"]
            false_accepted_total += appeals["false_accepted"]
        run_metrics["critical_fill"].append(critical_num / critical_den)
        run_metrics["weighted_fill"].append(weighted_num / weighted_den)
        run_metrics["mispriority_units"].append(mispriority / allocated if allocated else 0.0)
        run_metrics["appeal_load"].append(reviewed_total / (n * rounds))
        run_metrics["valid_correction_rate"].append(
            corrected_total / valid_filed_total if valid_filed_total else 0.0)
        run_metrics["false_accept_rate"].append(
            false_accepted_total / reviewed_total if reviewed_total else 0.0)
        run_metrics["shock_critical_fill"].append(shock_num / shock_den if shock_den else 0.0)
    out = {}
    for metric, values in run_metrics.items():
        out[metric] = mean(values)
        out[f"{metric}_ci"] = _ci(values)
    return out


def e17_priority_appeals(out: Path, reps: int, log) -> list[Path]:
    errors, false_shares = (0.10, 0.25), (0.0, 0.15, 0.30)
    rows, grid = [], {}
    for error_rate in errors:
        for false_share in false_shares:
            for capacity in E17_CAPACITIES:
                result = priority_appeal_cell(error_rate, false_share, capacity, max(2, reps))
                grid[(error_rate, false_share, capacity)] = result
                rows.append({"classification_error": error_rate, "false_priority_claimants": false_share,
                             "appeal_capacity": capacity, "review_sensitivity": E17_SENSITIVITY,
                             "review_false_accept": E17_FALSE_ACCEPT, "agents": E16_N,
                             "rounds": E16_ROUNDS, "reps": reps, **result})
            log(f"E17 error={error_rate:.2f}, false_claims={false_share:.2f}")
    write_csv(rows, out, "e17_priority_appeals.csv")
    focus_false = 0.15
    fig, axes = new_figure(1, 4, panel=(5.6, 4.8))
    xs = [100 * capacity for capacity in E17_CAPACITIES]
    metrics = (("critical_fill", "critical needs met ↑"),
               ("weighted_fill", "priority-weighted needs met ↑"),
               ("mispriority_units", "units given to lower-need claimants ↓"))
    for error_rate in errors:
        color = E17_COLORS[error_rate]
        for ax, (metric, label) in zip((axes[0][0], axes[0][1], axes[0][2]), metrics):
            plot_line(ax, xs, [grid[(error_rate, focus_false, c)][metric] for c in E17_CAPACITIES],
                      err=[grid[(error_rate, focus_false, c)][f"{metric}_ci"] for c in E17_CAPACITIES],
                      color=color, marker="o", label=f"classification error {error_rate:.0%}")
            ax.set_xlabel("appeal review capacity (% of people per round)")
            ax.set_ylabel(label)
            ax.set_ylim(0, 1.02)
    h, labels = axes[0][0].get_legend_handles_labels()
    legend_panel(axes[0][3], h, labels)
    return finalize_figure(fig, fig_path(out, "e17_priority_appeals"))
