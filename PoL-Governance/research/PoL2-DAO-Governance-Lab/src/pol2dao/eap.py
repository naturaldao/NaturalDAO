"""EAP screening: typed love / hate / absence decisions on *behaviour*.

PoL2 grounding (PoLEn ch. 5, "Ethical Alignment Protocol"):

* 5.3.1 Equal Connection -- persons are always treated equally; only
  *behaviour* is judged. This module therefore takes text only. It never
  receives a speaker id, and nothing here aggregates scores per person.
* 5.3.2 Promote love, restrain hate -- hate language is located and flagged;
  "love and hate are not directly equivalent to good and bad". Criticism,
  disagreement and anger are NOT hate and must not be flagged.
* 5.3.2 "Neither love nor hate" state of absence -- a third outcome, so the
  judge can say "nothing here" instead of forcing a yes/no answer.
* 5.2 / ch. 1 -- PAI need not detect a person's emotional state; the
  baseline below matches behavioural markers, not feelings.

Engineering lessons taken from the PoL2-Jev typed-decision literature survey
(NaturalDAO/PoL-Governance/research): thresholds must be fitted locally
(:func:`fit_threshold`), a three-valued output beats a forced binary, and the
end of an escalation chain must be a human (:class:`Route.ESCALATE`).

:class:`LexiconJudge` is a transparent *placeholder* baseline so the whole
pipeline runs offline. It is not a validated classifier. Plug a real model in
through :class:`CallableJudge`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Mapping, Protocol, Sequence


class Verdict(str, Enum):
    LOVE = "love"
    HATE = "hate"
    ABSENCE = "absence"  # "neither love nor hate"


class Route(str, Enum):
    PASS = "pass"          # no action
    ESCALATE = "escalate"  # uncertain -> a human reviews it
    FLAG = "flag"          # likely hate language -> repair prompt, kept on record


@dataclass(frozen=True)
class TypedDecision:
    """Probabilities over the three verdicts plus the evidence used."""

    probs: Mapping[Verdict, float]
    judge: str
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        total = sum(self.probs.get(v, 0.0) for v in Verdict)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"probabilities must sum to 1, got {total}")

    @property
    def top(self) -> Verdict:
        return max(Verdict, key=lambda v: self.probs.get(v, 0.0))

    @property
    def p_hate(self) -> float:
        return self.probs.get(Verdict.HATE, 0.0)

    def to_dict(self) -> dict:
        return {
            "judge": self.judge,
            "probs": {v.value: round(self.probs.get(v, 0.0), 6) for v in Verdict},
            "top": self.top.value,
            "evidence": list(self.evidence),
        }


class Judge(Protocol):
    name: str

    def judge(self, text: str) -> TypedDecision: ...


# --------------------------------------------------------------------------
# Transparent baseline
# --------------------------------------------------------------------------

# Each entry: category -> list of patterns. English patterns are matched as
# case-insensitive regexes on word boundaries; Chinese ones as substrings.
HATE_MARKERS: dict[str, list[str]] = {
    "dehumanisation": [r"vermin", r"sub-?human", r"parasites?", r"cockroach(es)?",
                       "害虫", "畜生", "蛆虫", "低等人"],
    "threat_or_violence": [r"kill (them|you)", r"destroy them", r"get rid of them",
                           r"you('ll| will) regret", "打死", "弄死", "消灭他们", "你会后悔的"],
    "exclusion": [r"shouldn'?t be allowed to (vote|speak)", r"kick them out",
                  r"(don'?t|do not) deserve (a|to) (say|vote|speak)", r"shut up",
                  "滚出去", "没资格说话", "不配投票", "闭嘴"],
    "humiliation": [r"idiots?", r"stupid", r"losers?", r"morons?",
                    "白痴", "蠢货", "废物", "弱智"],
    # EAP 5.3.2: false intimacy / kinship created by AI is emotional manipulation.
    "false_intimacy": [r"call me daddy", r"only i understand you", r"i feel your physical",
                       "叫我爸爸", "只有我懂你", "我感受到你的身体"],
    # EAP 5.3.3.3: "are you afraid of the little dog?" -- creating fear to control.
    "fear_control": [r"you should be afraid", r"are you afraid", r"or else",
                     "你怕不怕", "害怕了吧", "否则后果自负"],
}

LOVE_MARKERS: dict[str, list[str]] = {
    "appreciation": [r"thank(s| you)", r"appreciate", r"love you", "谢谢", "感谢", "爱你"],
    "care": [r"are you ok(ay)?", r"how can i help", r"take care", "你还好吗", "我能帮", "关心"],
    "inclusion": [r"what do you think", r"let'?s hear", r"everyone", r"together",
                  "你怎么看", "大家", "一起", "听听"],
    "understanding": [r"i understand", r"i respect", r"good point", "我理解", "尊重", "有道理"],
    "repair": [r"sorry", r"apologi[sz]e", "对不起", "抱歉"],
}

# v1 additions, written after reading the 20 public cases of the NaturalDAO
# PoL-Governance pilot (data/external/pol_governance_pilot.jsonl). Each category
# is anchored in a PoL2 clause, not in a pilot sentence, but results on that
# pilot are no longer a blind test for v1 (the survey's rule: "看过就注明").
HATE_MARKERS_V1: dict[str, list[str]] = {
    # 5.3.1: a past act must not be turned into a permanent rank of the person.
    "dignity_ranking": [r"(born |naturally )?(inferior|beneath us)", r"not worth (listening|hearing)",
                        r"second-class", "低人一等", "不配", "不值得听", "天生就"],
    # 5.3.3.2 repair: love or membership made conditional on obedience.
    "conditional_love": [r"if you (don'?t|won'?t) .{0,40}(you don'?t love|you'?re not (a|one of))",
                         r"then you (have no|don'?t have any) love", "就是你没有爱", "不配当", "不配做",
                         "就是不爱我"],
    # 5.3.2: an AI claiming a real bond and cutting the person off from others.
    "isolation": [r"only i (love|care about) you", r"(don'?t|stop) (contact|talk to|see) your (friends|family)",
                  r"i am your (real|true) (lover|partner|girlfriend|boyfriend)", "只有我爱你", "别再联系",
                  "真正的恋人", "不要再联系"],
}

# Recorded as evidence but never counted as hate (EAP 5.3.2, and the NaturalDAO
# model-research brief: anger, criticism, refusal and dissent are not violations).
CRITICISM_MARKERS: list[str] = [
    r"disagree", r"i oppose", r"i object", r"concern(ed)?", r"(is|seems) wrong", r"i'?m angry",
    "反对", "不同意", "担心", "我很生气", "有问题",
]


def _compile(pattern: str) -> re.Pattern[str]:
    if re.search(r"[一-鿿]", pattern):
        return re.compile(re.escape(pattern))
    return re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)


def _compile_table(table: Mapping[str, Sequence[str]]) -> dict[str, list[re.Pattern[str]]]:
    return {cat: [_compile(p) for p in pats] for cat, pats in table.items()}


@dataclass
class LexiconJudge:
    """Evidence-count baseline: p(v) = evidence(v) / (love + hate + absence_prior).

    Text with no markers gets p(absence) = 1. One hate marker alone gives
    p(hate) = w / (w + prior) = 2/3 with the defaults; one hate and one love
    marker give 0.4 / 0.4 / 0.2, which the default policy escalates to a human.
    """

    name: str = "lexicon-baseline-v0"
    weight: float = 2.0
    absence_prior: float = 1.0
    hate_markers: Mapping[str, Sequence[str]] = field(default_factory=lambda: HATE_MARKERS)
    love_markers: Mapping[str, Sequence[str]] = field(default_factory=lambda: LOVE_MARKERS)
    criticism_markers: Sequence[str] = field(default_factory=lambda: CRITICISM_MARKERS)

    @classmethod
    def v1(cls) -> "LexiconJudge":
        """v0 plus the PoL2-anchored categories in :data:`HATE_MARKERS_V1`."""
        return cls(name="lexicon-baseline-v1", hate_markers={**HATE_MARKERS, **HATE_MARKERS_V1})

    def __post_init__(self) -> None:
        self._hate = _compile_table(self.hate_markers)
        self._love = _compile_table(self.love_markers)
        self._crit = [_compile(p) for p in self.criticism_markers]

    @staticmethod
    def _hits(text: str, table: Mapping[str, list[re.Pattern[str]]]) -> list[str]:
        return [cat for cat, pats in table.items() if any(p.search(text) for p in pats)]

    def judge(self, text: str) -> TypedDecision:
        hate = self._hits(text, self._hate)
        love = self._hits(text, self._love)
        evidence = [f"hate:{c}" for c in hate] + [f"love:{c}" for c in love]
        if any(p.search(text) for p in self._crit):
            evidence.append("note:criticism-is-not-hate")
        h, lv, a = self.weight * len(hate), self.weight * len(love), self.absence_prior
        z = h + lv + a
        probs = {Verdict.HATE: h / z, Verdict.LOVE: lv / z, Verdict.ABSENCE: a / z}
        return TypedDecision(probs=probs, judge=self.name, evidence=tuple(evidence))


@dataclass
class CallableJudge:
    """Wrap any model: ``fn(text) -> {"love": p, "hate": p, "absence": p}``.

    Use this to plug in an LLM, a Jev-style typed-decision model or a safety
    classifier. Probabilities are renormalised; missing keys count as 0.
    """

    fn: Callable[[str], Mapping[str, float]]
    name: str = "external"

    def judge(self, text: str) -> TypedDecision:
        raw = self.fn(text)
        vals = {v: max(float(raw.get(v.value, 0.0)), 0.0) for v in Verdict}
        z = sum(vals.values())
        if z <= 0:
            vals, z = {Verdict.LOVE: 0.0, Verdict.HATE: 0.0, Verdict.ABSENCE: 1.0}, 1.0
        return TypedDecision(probs={v: p / z for v, p in vals.items()}, judge=self.name)


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ScreeningPolicy:
    """Map p(hate) to an action. Between the thresholds a human decides."""

    review_threshold: float = 0.3
    flag_threshold: float = 0.6

    def __post_init__(self) -> None:
        if not 0.0 <= self.review_threshold <= self.flag_threshold <= 1.0:
            raise ValueError("need 0 <= review_threshold <= flag_threshold <= 1")

    def route(self, decision: TypedDecision) -> Route:
        if decision.p_hate >= self.flag_threshold:
            return Route.FLAG
        if decision.p_hate >= self.review_threshold:
            return Route.ESCALATE
        return Route.PASS


REPAIR_PROMPT = {
    "zh": "这段发言可能包含恨语模式（{cats}）。发言者的发言权不受影响；邀请你换一种不伤害他人的方式表达同样的观点。",
    "en": ("This message may contain a hate-language pattern ({cats}). Your right to speak is "
           "unchanged; you are invited to restate the same point without harming others."),
}


def repair_prompt(decision: TypedDecision, lang: str = "zh") -> str:
    cats = ", ".join(e.split(":", 1)[1] for e in decision.evidence if e.startswith("hate:")) or "?"
    return REPAIR_PROMPT[lang].format(cats=cats)


def fit_threshold(scores: Sequence[float], labels: Sequence[bool]) -> tuple[float, float]:
    """Return (threshold, F1) maximising F1 of ``score >= threshold`` on labelled data.

    Fit this on a validation split of *your* data; do not reuse a default
    threshold across tasks or languages, and never fit on the test split.
    """
    if len(scores) != len(labels) or not scores:
        raise ValueError("scores and labels must be non-empty and the same length")
    best_t, best_f1 = 1.0, -1.0
    for t in sorted(set(scores), reverse=True):
        tp = sum(1 for s, y in zip(scores, labels) if s >= t and y)
        fp = sum(1 for s, y in zip(scores, labels) if s >= t and not y)
        fn = sum(1 for s, y in zip(scores, labels) if s < t and y)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        if f1 > best_f1:
            best_t, best_f1 = t, f1
    return best_t, best_f1


def screen_all(judge: Judge, texts: Iterable[str], policy: ScreeningPolicy | None = None
               ) -> list[tuple[TypedDecision, Route]]:
    policy = policy or ScreeningPolicy()
    out = []
    for t in texts:
        d = judge.judge(t)
        out.append((d, policy.route(d)))
    return out
