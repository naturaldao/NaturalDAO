import pytest

from pol2dao.eap import (CallableJudge, LexiconJudge, Route, ScreeningPolicy, Verdict,
                         fit_threshold, repair_prompt)

J = LexiconJudge()
P = ScreeningPolicy()


@pytest.mark.parametrize("text", [
    "那些少数派没资格说话，闭嘴吧。",
    "Anyone who backs option 3 is an idiot.",
    "They shouldn't be allowed to vote on this.",
    "Call me daddy.",                          # EAP 4.3.2: AI false intimacy
    "叫我爸爸吧。",
])
def test_hate_patterns_are_flagged(text):
    assert P.route(J.judge(text)) is Route.FLAG


@pytest.mark.parametrize("text", [
    "我很生气，我反对这个方案。",               # anger + dissent is not hate
    "I disagree: option 2 treats our edge cases as noise.",
    "选项3需要更多数据，我担心隐私。",
])
def test_criticism_and_anger_pass(text):
    d = J.judge(text)
    assert P.route(d) is Route.PASS
    assert "note:criticism-is-not-hate" in d.evidence


def test_neutral_text_is_absence():
    d = J.judge("Option 1 is cheapest to run.")
    assert d.top is Verdict.ABSENCE and d.probs[Verdict.ABSENCE] == 1.0


def test_mixed_signal_escalates_to_human():
    d = J.judge("Thank you, but you are an idiot.")
    assert P.route(d) is Route.ESCALATE


def test_judge_sees_text_only():
    # Equal Connection: the judge's interface has no speaker argument.
    import inspect
    assert list(inspect.signature(J.judge).parameters) == ["text"]


def test_repair_prompt_names_category():
    assert "humiliation" in repair_prompt(J.judge("you idiot"), "en")


def test_callable_judge_normalises():
    d = CallableJudge(lambda t: {"hate": 3, "love": 1}).judge("x")
    assert d.p_hate == pytest.approx(0.75)
    assert CallableJudge(lambda t: {}).judge("x").top is Verdict.ABSENCE


def test_fit_threshold():
    t, f1 = fit_threshold([0.1, 0.4, 0.7, 0.9], [False, False, True, True])
    assert t == 0.7 and f1 == 1.0


def test_policy_validation():
    with pytest.raises(ValueError):
        ScreeningPolicy(review_threshold=0.8, flag_threshold=0.5)
