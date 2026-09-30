"""Plug your own model into EAP screening.

Any function ``text -> {"love": p, "hate": p, "absence": p}`` works: an LLM
prompted to return JSON, a Jev-style typed-decision model, or a safety
classifier. Fit the thresholds on *your* labelled validation data.

Run: python examples/custom_judge.py
"""

from pol2dao import CallableJudge, GovernanceConfig, GovernanceSession, Proposal, ScreeningPolicy
from pol2dao.eap import fit_threshold


def my_model(text: str) -> dict:
    # Replace this toy rule with a call to your model. Keep the three keys.
    hostile = any(w in text.lower() for w in ("idiot", "闭嘴", "shut up"))
    return {"hate": 0.9 if hostile else 0.05, "love": 0.05, "absence": 0.9 if not hostile else 0.05}


judge = CallableJudge(my_model, name="my-model-v1")

# 1) Calibrate on a small labelled validation set (never on the test set).
val_texts = ["shut up", "我反对这个方案", "谢谢", "you idiot", "闭嘴吧", "option 2 is cheaper"]
val_labels = [True, False, False, True, True, False]
scores = [judge.judge(t).p_hate for t in val_texts]
threshold, f1 = fit_threshold(scores, val_labels)
print(f"fitted flag threshold {threshold:.3f} (validation F1 {f1:.2f})")

# 2) Use it in a session; the band below the flag threshold goes to a human.
policy = ScreeningPolicy(review_threshold=threshold / 2, flag_threshold=threshold)
s = GovernanceSession(Proposal("P-9", "demo", ("A", "B")), ["x", "y"],
                      GovernanceConfig.pol2(policy=policy), judge=judge)
print(s.say("x", "我反对 A").route, s.say("y", "shut up").route)
