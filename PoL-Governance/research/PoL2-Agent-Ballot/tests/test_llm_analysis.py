"""The herding analysis reconstructs what each agent saw in the open
condition; a scripted conformist must show the step at a lead of two."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from analyze_llm_herding import analyse


def _synthetic(path: Path, n_props=30, n=7, p=0.7, seed=3):
    rng = random.Random(seed)
    lines = [{"meta": {"model": "synthetic", "n": n, "p": p}}]
    for i in range(n_props):
        truth = rng.choice(["advance", "hold"])
        ev = [truth if rng.random() < p else ("hold" if truth == "advance" else "advance") for _ in range(n)]
        for cond in ("sealed", "open"):
            seen = []
            for j, e in enumerate(ev):
                lead = sum(v != e for v in seen) - sum(v == e for v in seen)
                choice = e if cond == "sealed" or lead < 2 else ("hold" if e == "advance" else "advance")
                lines.append({"proposal": f"R-{i}", "truth": truth, "condition": cond, "agent": f"a{j}", "evidence_says": e, "choice": choice, "rationale": "x"})
                seen.append(choice)
    path.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")


def test_conformity_curve_recovers_the_rule(tmp_path):
    f = tmp_path / "run.jsonl"
    _synthetic(f)
    res = analyse(f)
    for k, v in res["conformity_curve"].items():
        assert v["rate"] == (1.0 if int(k) >= 2 else 0.0)
    assert res["against_evidence"]["sealed"]["k"] == 0
    assert res["accuracy"]["sealed"]["rate"] == res["evidence_ceiling"]["rate"]
