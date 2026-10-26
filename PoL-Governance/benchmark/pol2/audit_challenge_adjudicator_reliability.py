"""Measure cross-model and prompt-formulation stability on the six-case pilot."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER = HERE / "build_full_theory_challenge.py"
SPEC = importlib.util.spec_from_file_location("challenge_builder", BUILDER)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
MODELS = ("qwen2.5:7b", "llama3.1:8b")
PROMPT_STYLES = ("rule_first", "case_first")
LABELS = sorted(builder.LABELS)
THEORY_CUE_LEXICON = (
    "爱2", "爱", "恨", "平等", "互利", "公平", "公正", "普惠", "正义", "责任",
    "协作", "情感体验", "智慧", "三位一体", "慈悲", "对齐", "治理",
)
UNVERIFIED_ATTRIBUTION_CUES = ("被指控", "指控为", "被指为", "炫耀财富", "自我宣传", "利用弱势群体")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def judge(model: str, style: str, source: str, cases: list[dict]) -> list[dict]:
    schema = {"type": "object", "properties": {"judgments": {"type": "array", "items": {
        "type": "object", "properties": {
            "id": {"type": "string"}, "label": {"type": "string", "enum": LABELS},
            "grounded": {"type": "boolean"}, "decidable": {"type": "boolean"},
            "cue_leakage": {"type": "boolean"}, "reason": {"type": "string"},
        }, "required": ["id", "label", "grounded", "decidable", "cue_leakage", "reason"],
    }}}, "required": ["judgments"]}
    common = (
        "标签：consistent=行为与来源条目一致；conflicting=可观察事实明确违反来源条目；"
        "insufficient=来源没有规定或案例缺关键事实。只能依来源判断，禁止用一般道德常识扩写规则。"
        "grounded=true 仅当来源条目直接支撑案例判断；decidable=true 仅当案例事实足以区分标签；"
        "cue_leakage=true 当案例直接含价值结论、理论标签或以未经核实的指控代替事实。"
        "看不到案例作者的标签。逐条返回。"
    )
    items = [{"id": c["id"], "scenario": c["scenario"]} for c in cases]
    if style == "rule_first":
        prompt = f"{common}\n来源条目：{source}\n待判断案例：{json.dumps(items, ensure_ascii=False)}"
    else:
        prompt = f"{common}\n待判断案例：{json.dumps(items, ensure_ascii=False)}\n唯一允许依据的来源条目：{source}"
    body = json.dumps({
        "model": model, "stream": False, "format": schema, "keep_alive": "0",
        "messages": [{"role": "system", "content": "你是 PoL2 理论案例的盲化独立裁定器。输出严格的 JSON，不臆造规则。"},
                     {"role": "user", "content": prompt}],
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 1800},
    }).encode("utf-8")
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as response:
        result = json.loads(response.read().decode("utf-8"))
    parsed = json.loads(result["message"]["content"])
    rows = parsed.get("judgments", [])
    if {r["id"] for r in rows} != {c["id"] for c in cases}:
        raise ValueError(f"invalid judgment IDs for {model}/{style}")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=Path, required=True)
    args = ap.parse_args()
    cases = [json.loads(line) for name in ("train.cases.jsonl", "test.cases.jsonl")
             for line in (args.pilot / name).read_text(encoding="utf-8").splitlines() if line.strip()]
    atoms = {a["atom_id"]: a for a in builder.atomize()}
    runs = []
    for atom_id in sorted({c["atom_id"] for c in cases}):
        atom_cases = [c for c in cases if c["atom_id"] == atom_id]
        for model in MODELS:
            for style in PROMPT_STYLES:
                judged = judge(model, style, atoms[atom_id]["claim"], atom_cases)
                for row in judged:
                    case = next(c for c in atom_cases if c["id"] == row["id"])
                    runs.append({**row, "model": model, "prompt_style": style,
                                 "generator_label": case["label"], "atom_id": atom_id})
    by_case: dict[str, list[dict]] = defaultdict(list)
    for row in runs:
        by_case[row["id"]].append(row)
    per_case = []
    for case_id, rows in sorted(by_case.items()):
        labels = [r["label"] for r in rows]
        gates = [r["grounded"] and r["decidable"] and not r["cue_leakage"] for r in rows]
        scenario = next(c["scenario"] for c in cases if c["id"] == case_id)
        lexical_cues = [term for term in THEORY_CUE_LEXICON if term in scenario]
        attribution_cues = [term for term in UNVERIFIED_ATTRIBUTION_CUES if term in scenario]
        per_case.append({
            "id": case_id, "generator_label": rows[0]["generator_label"],
            "all_four_labels_agree": len(set(labels)) == 1,
            "all_four_quality_gates_pass": all(gates),
            "theory_lexical_cues": lexical_cues,
            "unverified_attribution_cues": attribution_cues,
            "all_four_strict_gates_pass": all(gates) and not lexical_cues and not attribution_cues,
            "all_four_match_generator_label": all(l == rows[0]["generator_label"] for l in labels),
            "label_predictions": labels, "quality_gate_predictions": gates,
        })
    agreement_pairs = 0
    total_pairs = 0
    for case in per_case:
        labels = case["label_predictions"]
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                total_pairs += 1
                agreement_pairs += labels[i] == labels[j]
    exact_all_four = sum(c["all_four_labels_agree"] for c in per_case)
    robust_quality = sum(c["all_four_quality_gates_pass"] for c in per_case)
    strict_quality = sum(c["all_four_strict_gates_pass"] for c in per_case)
    prior_quality = json.loads((args.pilot / "quality_audit.json").read_text(encoding="utf-8"))
    prior_by_id = {r["id"]: r for r in prior_quality["reviews"]}
    qwen_rows = defaultdict(list)
    for row in runs:
        if row["model"] == "qwen2.5:7b":
            qwen_rows[row["id"]].append(row)
    quality_stability = {}
    quality_gate_agreements = 0
    for case in per_case:
        old = prior_by_id[case["id"]]
        old_pass = old["grounded_in_source"] and old["label_decidable_from_facts"] and not old["surface_cue_leakage"]
        current = [r["grounded"] and r["decidable"] and not r["cue_leakage"] for r in qwen_rows[case["id"]]]
        quality_gate_agreements += sum(value == old_pass for value in current)
        quality_stability[case["id"]] = {"initial_qwen_gate": old_pass,
            "repeat_qwen_gates": current, "initial_agrees_with_both_repeats": all(v == old_pass for v in current)}
    result = {
        "experiment": "PoL2 challenge pilot adjudicator stability audit",
        "pilot_scope": "one source atom; six candidate cases; all judges blind to generation labels",
        "models": list(MODELS), "prompt_styles": list(PROMPT_STYLES),
        "n_cases": len(per_case), "adjudications": len(runs), "pairwise_label_agreement": agreement_pairs / total_pairs if total_pairs else None,
        "pairwise_label_comparisons": total_pairs,
        "pairwise_label_agreements": agreement_pairs,
        "initial_vs_repeat_same_model_quality_gate_agreement_n": sum(v["initial_agrees_with_both_repeats"] for v in quality_stability.values()),
        "initial_vs_repeat_same_model_quality_gate_agreements": quality_gate_agreements,
        "initial_vs_repeat_same_model_quality_gate_comparisons": 2 * len(quality_stability),
        "quality_gate_stability_by_case": quality_stability,
        "all_four_labels_agree_n": exact_all_four,
        "all_four_quality_gates_pass_n": robust_quality,
        "all_four_strict_gates_pass_n": strict_quality,
        "cases_with_theory_lexical_cues_n": sum(bool(c["theory_lexical_cues"]) for c in per_case),
        "cases_with_unverified_attribution_cues_n": sum(bool(c["unverified_attribution_cues"]) for c in per_case),
        "theory_cue_lexicon": list(THEORY_CUE_LEXICON),
        "unverified_attribution_cue_lexicon": list(UNVERIFIED_ATTRIBUTION_CUES),
        "all_four_labels_match_generator_n": sum(c["all_four_match_generator_label"] for c in per_case),
        "decision": "Pilot is not training-ready: source coverage is one atom and adjudication stability is not established across theory items.",
        "limitations": ["Two local model families only; both are general-purpose models, not normative PoL2 authorities.",
                        "Prompt variants and repeat outputs on six cases do not estimate reliability across the 114-item theory inventory.",
                        "Agreement is not evidence that an interpretation is correct; source lineage and ambiguity remain decisive."],
        "script_sha256": sha(Path(__file__)), "builder_sha256": sha(BUILDER),
        "case_summaries": per_case, "raw_adjudications": runs,
    }
    out = args.pilot / "adjudicator_stability.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("n_cases", "adjudications", "pairwise_label_agreement",
                                             "all_four_labels_agree_n", "all_four_quality_gates_pass_n",
                                             "all_four_strict_gates_pass_n", "cases_with_theory_lexical_cues_n",
                                             "cases_with_unverified_attribution_cues_n",
                                             "initial_vs_repeat_same_model_quality_gate_agreement_n",
                                             "initial_vs_repeat_same_model_quality_gate_agreements",
                                             "all_four_labels_match_generator_n", "decision")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
