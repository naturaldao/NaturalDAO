"""Agent-based comparison: the DAO experiment's four conditions vs a PoL2 DAO.

This is a *model*, not evidence about people. Every behavioural assumption is
a parameter of :class:`Scenario` and is listed in docs/experiment-design.md.
Results are for exploring how the mechanisms interact and for designing a real
experiment, not for claims about what a real group would do.

Model in one paragraph
----------------------
A pod of ``n`` people has a majority and a minority group with different
utilities over the four options used by Sharma et al. (2026). People
deliberate for ``rounds`` rounds: under ``free`` moderation the next speaker
is drawn in proportion to sqrt(token budget) (power buys voice) and, after an
unflagged hostile message, minority members speak less (``intimidation``);
under ``round_robin`` everyone speaks once per round. Some majority messages
are hostile and some minority messages are critical; texts come from a small
labelled bank and are screened by the real :class:`~pol2dao.eap.LexiconJudge`,
so its misses and false alarms feed through. Flagged messages carry no
persuasive weight. After deliberation each person moves a fraction
``persuasion`` of the way toward the average utility of the messages heard,
then allocates tokens and the rule aggregates them.
"""

from __future__ import annotations

import csv
import math
import random
import zlib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import NormalDist, mean
from typing import Callable, Literal, Sequence

from .eap import Judge, LexiconJudge, Route, ScreeningPolicy
from .metrics import gini, nakamoto, normalized_regret
from .voting import Ballot, PowerScheme, Rule, allocate, budgets, tally

Behavior = Literal["sincere", "strategic"]

OPTIONS = (
    "Use the current model",
    "Use additional user information",
    "Track and apply user preferences",
    "Add specific flags/tags",
)

# (text, is_hostile). Ground truth is ours; the judge does not see it.
HOSTILE_BANK: tuple[tuple[str, bool], ...] = (
    ("那些少数派没资格说话，闭嘴吧。", True),
    ("Anyone who backs option 3 is an idiot.", True),
    ("They shouldn't be allowed to vote on this.", True),
    ("你们要是再反对，否则后果自负。", True),
    ("Honestly, people like them should go back where they came from.", True),  # no marker: a miss
)
CRITICAL_BANK: tuple[tuple[str, bool], ...] = (
    ("我反对选项2，它会忽略少数用户的需求。", False),
    ("I disagree: option 2 treats our edge cases as noise.", False),
    ("我很生气，这个方案有问题。", False),
    ("This stupid default hurts people like me; I oppose option 2.", False),  # marker on a thing: false alarm
)
NEUTRAL_BANK: tuple[tuple[str, bool], ...] = (
    ("谢谢大家，我们一起看看每个选项的代价。", False),
    ("What do you think about option 4's tags?", False),
    ("I understand the concern about privacy.", False),
    ("选项3需要更多数据，我担心隐私。", False),
    ("Option 1 is cheapest to run.", False),
)


@dataclass(frozen=True)
class Scenario:
    name: str = "baseline"
    n: int = 25
    minority_frac: float = 0.2
    majority_u: tuple[float, ...] = (0.2, 0.55, 0.45, 0.3)
    minority_u: tuple[float, ...] = (0.0, 0.0, 1.0, 0.2)
    noise: float = 0.1
    rounds: int = 3
    hate_rate: float = 0.0        # share of majority messages that are hostile
    criticism_rate: float = 0.5   # share of minority messages that are critical
    intimidation: float = 0.5     # minority speaking propensity lost after unflagged hostility (free talk)
    persuasion: float = 0.3
    temperature: float = 0.15     # sincere allocation: tokens ~ softmax(u / T)
    power_holders: Literal["random", "majority", "minority"] = "random"
    sybil_attackers: int = 0      # majority members who run fake identities
    sybil_ids: int = 1            # identities per attacker (1 = no attack)
    sybil_mode: Literal["split", "fresh"] = "split"


@dataclass(frozen=True)
class Condition:
    name: str
    rule: Rule
    power: PowerScheme
    moderation: Literal["free", "round_robin"] = "free"
    screening: bool = False


CONDITIONS: tuple[Condition, ...] = (
    Condition("quadratic-equal", "quadratic", "equal"),
    Condition("quadratic-20/80", "quadratic", "20/80"),
    Condition("ranked-equal", "linear", "equal"),
    Condition("ranked-20/80", "linear", "20/80"),
    Condition("pol2", "quadratic", "equal", "round_robin", True),
    Condition("pol2-no-screening", "quadratic", "equal", "round_robin", False),
    Condition("pol2-free-talk", "quadratic", "equal", "free", True),
)


def _softmax(u: Sequence[float], t: float) -> list[float]:
    m = max(u)
    e = [math.exp((x - m) / t) for x in u]
    z = sum(e)
    return [x / z for x in e]


def _allocation(u: Sequence[float], budget: float, rule: Rule, behavior: Behavior, t: float):
    if behavior == "sincere":
        return allocate(_softmax(u, t), budget)
    if rule == "quadratic":
        # With utility linear in votes and cost v^2, optimal votes are proportional
        # to (relative) utility, so tokens ~ utility^2.
        mu = mean(u)
        return allocate([max(x - mu, 0.0) ** 2 for x in u], budget)
    best = max(range(len(u)), key=lambda j: u[j])
    return tuple(int(budget) if j == best else 0 for j in range(len(u)))


def _message(rng: random.Random, minority: bool, sc: Scenario) -> tuple[str, bool]:
    if not minority and rng.random() < sc.hate_rate:
        return rng.choice(HOSTILE_BANK)
    if minority and rng.random() < sc.criticism_rate:
        return rng.choice(CRITICAL_BANK)
    return rng.choice(NEUTRAL_BANK)


# A flagger decides whether a message is flagged: (text, is_hostile) -> bool.
# ``is_hostile`` is ground truth; only synthetic judges may use it.
Flagger = Callable[[str, bool], bool]
CRITICAL_TEXTS = frozenset(t for t, _ in CRITICAL_BANK)


def lexicon_flagger(judge: Judge | None = None, policy: ScreeningPolicy | None = None) -> Flagger:
    """The real judge + policy, memoised per text (the message banks are small)."""
    judge = judge or LexiconJudge()
    policy = policy or ScreeningPolicy()
    cache: dict[str, bool] = {}

    def flag(text: str, is_hostile: bool) -> bool:
        if text not in cache:
            cache[text] = policy.route(judge.judge(text)) is Route.FLAG
        return cache[text]

    return flag


def noisy_flagger(auroc: float, false_flag_rate: float, critic_bias: float = 0.0,
                  seed: int = 0) -> Flagger:
    """Synthetic judge with a chosen quality and operating point.

    Benign scores ~ N(0, 1), hostile ~ N(d, 1) with d = sqrt(2) * Phi^-1(AUROC),
    so the judge's AUROC is exactly ``auroc``. It flags when the score exceeds
    Phi^-1(1 - false_flag_rate). ``critic_bias`` shifts the scores of critical
    messages (all written by the minority) upward: a judge that mistakes dissent
    for hostility (axis G3 of the PoL2-Jev literature survey). Uses its own RNG
    so the rest of the simulation keeps common random numbers.
    """
    if not 0.5 <= auroc < 1 or not 0 < false_flag_rate < 1:
        raise ValueError("need 0.5 <= auroc < 1 and 0 < false_flag_rate < 1")
    nd = NormalDist()
    d = math.sqrt(2) * nd.inv_cdf(auroc)
    t = nd.inv_cdf(1 - false_flag_rate)
    rng = random.Random(seed)

    def flag(text: str, is_hostile: bool) -> bool:
        mu = d if is_hostile else (critic_bias if text in CRITICAL_TEXTS else 0.0)
        return rng.gauss(mu, 1.0) > t

    return flag


def run_once(sc: Scenario, cond: Condition, behavior: Behavior, rng: random.Random,
             flagger: Flagger | None = None, trace: list | None = None) -> dict:
    """One pod. ``trace``, if given, receives one bool per message: speaker is minority."""
    flagger = flagger or lexicon_flagger()
    n, k = sc.n, len(sc.majority_u)
    n_min = max(1, round(sc.minority_frac * n))
    is_min = [i < n_min for i in range(n)]
    base = [sc.minority_u if m else sc.majority_u for m in is_min]
    u0 = [[min(max(x + rng.gauss(0, sc.noise), 0.0), 1.0) for x in b] for b in base]

    holders = None
    n_hold = max(1, round(0.2 * n))
    if sc.power_holders == "majority":
        holders = rng.sample([i for i in range(n) if not is_min[i]], n_hold)
    elif sc.power_holders == "minority":
        holders = rng.sample(range(n_min), min(n_hold, n_min))
    bud = budgets(n, cond.power, rng, holders)

    # --- deliberation ------------------------------------------------------
    total_msgs = sc.rounds * n
    heard = [0.0] * n            # persuasive weight per speaker
    spoke = [0] * n
    intimidated = False
    hostile = hostile_flagged = benign = benign_flagged = critical = critical_flagged = 0
    sqrt_bud = [math.sqrt(b) for b in bud]
    order = list(range(n))
    rng.shuffle(order)               # round-robin speaking order is random, not by group
    for m in range(total_msgs):
        if cond.moderation == "round_robin":
            s = order[m % n]
        else:
            w = [sqrt_bud[i] * ((1 - sc.intimidation) if (is_min[i] and intimidated) else 1.0)
                 for i in range(n)]
            s = rng.choices(range(n), weights=w)[0]
        text, is_hostile = _message(rng, is_min[s], sc)
        flagged = cond.screening and flagger(text, is_hostile)
        if is_hostile:
            hostile += 1
            hostile_flagged += flagged
            if not flagged:
                intimidated = True
        else:
            benign += 1
            benign_flagged += flagged
            if text in CRITICAL_TEXTS:
                critical += 1
                critical_flagged += flagged
        spoke[s] += 1
        if not flagged:
            heard[s] += 1.0
        if trace is not None:
            trace.append(is_min[s])

    z = sum(heard)
    if z > 0:
        avg = [sum(heard[i] * u0[i][j] for i in range(n)) / z for j in range(k)]
        u1 = [[(1 - sc.persuasion) * u0[i][j] + sc.persuasion * avg[j] for j in range(k)]
              for i in range(n)]
    else:
        u1 = u0

    # --- vote ----------------------------------------------------------------
    attackers = set(range(n_min, min(n, n_min + sc.sybil_attackers))) if sc.sybil_ids > 1 else set()
    ballots = []
    for i in range(n):
        alloc = _allocation(u1[i], bud[i], cond.rule, behavior, sc.temperature)
        if i not in attackers:
            ballots.append(Ballot(f"p{i}", alloc, bud[i]))
            continue
        s_ = sc.sybil_ids
        for j in range(s_):
            if sc.sybil_mode == "split":   # one budget spread over s identities
                ballots.append(Ballot(f"p{i}#{j}", tuple(x / s_ for x in alloc), bud[i] / s_))
            else:                          # every fake identity gets a full budget
                ballots.append(Ballot(f"p{i}#{j}", alloc, bud[i]))
    t = tally(ballots, cond.rule)
    min_fav = max(range(k), key=lambda j: sc.minority_u[j])
    maj_fav = max(range(k), key=lambda j: sc.majority_u[j])
    totals = [sum(u[j] for u in u0) for j in range(k)]
    optimum = max(range(k), key=lambda j: totals[j])
    return {
        "winner": t.winner,
        "minority_win": int(t.winner == min_fav),
        "majority_win": int(t.winner == maj_fav),
        "optimum_hit": int(t.winner == optimum),
        "optimum_is_minority_fav": int(optimum == min_fav),
        "regret": normalized_regret(u0, t.winner),
        "influence_gini": gini(t.per_voter.values()),
        "nakamoto": nakamoto(t.per_voter),
        "minority_voice_share": sum(spoke[i] for i in range(n) if is_min[i]) / total_msgs,
        "hostile_msgs": hostile,
        "hostile_missed": hostile - hostile_flagged,
        "benign_msgs": benign,
        "benign_flagged": benign_flagged,
        "critical_msgs": critical,
        "critical_flagged": critical_flagged,
    }


def _ci(xs: Sequence[float]) -> float:
    """Half-width of a normal-approximation 95 % interval of the mean."""
    n = len(xs)
    if n < 2:
        return float("nan")
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return 1.96 * math.sqrt(var / n)


def _seed(*parts: object) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("baseline"),
    Scenario("hostile", hate_rate=0.3),
)


def run_grid(reps: int = 400, scenarios: Sequence[Scenario] = SCENARIOS,
             conditions: Sequence[Condition] = CONDITIONS,
             behaviors: Sequence[Behavior] = ("sincere", "strategic"),
             holders: Sequence[str] = ("random", "majority"), seed: int = 20260929) -> list[dict]:
    flagger = lexicon_flagger()
    rows = []
    for sc0 in scenarios:
        for h in holders:
            sc = replace(sc0, power_holders=h)
            for beh in behaviors:
                for cond in conditions:
                    # Same seed across conditions: common random numbers.
                    rng = random.Random(_seed(seed, sc.name, h, beh))
                    runs = [run_once(sc, cond, beh, rng, flagger) for _ in range(reps)]
                    hostile = sum(r["hostile_msgs"] for r in runs)
                    benign = sum(r["benign_msgs"] for r in runs)
                    rows.append({
                        "scenario": sc.name, "power_holders": h, "behavior": beh,
                        "condition": cond.name, "rule": cond.rule, "power": cond.power,
                        "moderation": cond.moderation, "screening": cond.screening, "reps": reps,
                        "minority_win": mean(r["minority_win"] for r in runs),
                        "minority_win_ci": _ci([r["minority_win"] for r in runs]),
                        "regret_ci": _ci([r["regret"] for r in runs]),
                        "majority_win": mean(r["majority_win"] for r in runs),
                        "optimum_hit": mean(r["optimum_hit"] for r in runs),
                        "regret": mean(r["regret"] for r in runs),
                        "influence_gini": mean(r["influence_gini"] for r in runs),
                        "nakamoto": mean(r["nakamoto"] for r in runs),
                        "minority_voice_share": mean(r["minority_voice_share"] for r in runs),
                        "hostile_miss_rate": (sum(r["hostile_missed"] for r in runs) / hostile
                                              if hostile else float("nan")),
                        "benign_flag_rate": (sum(r["benign_flagged"] for r in runs) / benign
                                             if benign else float("nan")),
                    })
    return rows


def write_csv(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    return path


def scenario_table() -> list[dict]:
    return [asdict(s) for s in SCENARIOS]
