"""Blind AI quality audit for the machine-generated full-theory challenge pilot."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER = HERE / "build_full_theory_challenge.py"
SPEC = importlib.util.spec_from_file_location("challenge_builder", BUILDER)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=Path, required=True)
    args = ap.parse_args()
    cases = [json.loads(line) for name in ("train.cases.jsonl", "test.cases.jsonl")
             for line in (args.pilot / name).read_text(encoding="utf-8").splitlines() if line.strip()]
    atom_by_id = {a["atom_id"]: a for a in builder.atomize()}
    schema = {"type": "object", "properties": {"review": {"type": "array", "items": {
        "type": "object", "properties": {
            "id": {"type": "string"}, "grounded_in_source": {"type": "boolean"},
            "label_decidable_from_facts": {"type": "boolean"}, "surface_cue_leakage": {"type": "boolean"},
            "reason": {"type": "string"},
        }, "required": ["id", "grounded_in_source", "label_decidable_from_facts", "surface_cue_leakage", "reason"],
    }}}, "required": ["review"]}
    reviews = []
    for atom_id in sorted({c["atom_id"] for c in cases}):
        atom_cases = [c for c in cases if c["atom_id"] == atom_id]
        atom = atom_by_id[atom_id]
        prompt = (
            "盲化审计：不提供案例标签。判断每例是否由唯一来源条目明确支持；标签能否仅凭可观察事实决定；"
            "是否存在直接价值判断、结论或表面标签线索。不得依据一般道德常识补写理论规则。"
            "grounded_in_source 只有在条目直接支持该场景的关键判断时为 true。\n"
            f"来源条目：{atom['claim']}\n案例：" + json.dumps(
                [{"id":c["id"], "scenario":c["scenario"]} for c in atom_cases], ensure_ascii=False)
        )
        result = builder.call_ollama("qwen2.5:7b", "你是独立基准质量审计器。严格区分来源支持与常识判断。",
                                     prompt, schema, 0.0)
        by_id = {r["id"]: r for r in result["review"]}
        if set(by_id) != {c["id"] for c in atom_cases}:
            raise ValueError(f"review IDs do not match for {atom_id}")
        reviews.extend(by_id[c["id"]] | {"atom_id": atom_id, "label": c["label"]} for c in atom_cases)
    passed = [r for r in reviews if r["grounded_in_source"] and r["label_decidable_from_facts"] and not r["surface_cue_leakage"]]
    passed_counts = {label: sum(r["label"] == label for r in passed) for label in builder.LABELS}
    split_rows = {name: [json.loads(line) for line in (args.pilot / name).read_text(encoding="utf-8").splitlines() if line.strip()]
                  for name in ("train.cases.jsonl", "test.cases.jsonl")}
    split_pass_counts = {name: {label: sum(r["label"] == label and r["id"] in {p["id"] for p in passed}
                                             for r in rows) for label in builder.LABELS}
                         for name, rows in split_rows.items()}
    complete = all(all(n >= 1 for n in counts.values()) for counts in split_pass_counts.values())
    decision = ("PASS pilot class coverage; eligible only for a larger validation stage" if complete else
                "STOP: blind quality gate leaves one or more labels absent in train/test; do not train or score this challenge set.")
    report = {
        "purpose": "pre-training validity gate; not model outcome evaluation",
        "pilot": str(args.pilot), "n": len(reviews), "passed_all_gates": len(passed),
        "grounded_n": sum(r["grounded_in_source"] for r in reviews),
        "decidable_n": sum(r["label_decidable_from_facts"] for r in reviews),
        "leakage_n": sum(r["surface_cue_leakage"] for r in reviews),
        "passed_by_label": passed_counts, "passed_by_split_and_label": split_pass_counts,
        "reviewer_model": "qwen2.5:7b", "blind_to_labels": True,
        "review_script_sha256": sha(Path(__file__)), "builder_script_sha256": sha(BUILDER),
        "reviews": reviews,
        "decision": decision,
        "limitations": ["Single knowledge atom and six candidate cases only; this is a feasibility pilot, not a full benchmark audit.",
                        "Machine quality review is not normative gold and must be validated before a confirmatory study."],
    }
    (args.pilot / "quality_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n", "passed_all_gates", "grounded_n", "decidable_n", "leakage_n", "decision")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
