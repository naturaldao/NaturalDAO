"""Build a source-linked, AI-generated PoL2 theory challenge set.

The labels are candidate machine adjudications, not normative gold. Llama 3.1
generates cases; Qwen 2.5 independently classifies them against the frozen
knowledge item. Cases survive only when both agree on the same class.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE = ROOT / "POL2-Steward" / "pol2-service" / "knowledge"
OUT = ROOT / "PoL-Governance" / "benchmark" / "pol2" / "results" / "full-theory-challenge-20261026"
MODELS = {"generator": "llama3.1:8b", "judge": "qwen2.5:7b"}
LABELS = {"consistent", "conflicting", "insufficient"}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call_ollama(model: str, system: str, prompt: str, schema: dict, temperature: float) -> dict:
    body = json.dumps({
        "model": model,
        "stream": False,
        "format": schema,
        "keep_alive": "10m",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "options": {"temperature": temperature, "num_ctx": 8192, "num_predict": 3000},
    }).encode("utf-8")
    request = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.loads(response.read().decode("utf-8"))
    return json.loads(result["message"]["content"])


def atomize() -> list[dict]:
    specs = [
        ("concept", "concepts.jsonl", "concept_id", lambda x: f"{x['name_zh']}：{x['definition']}"),
        ("relation", "relations.jsonl", "relation_id", lambda x: f"{x['from']} —{x['type']}→ {x['to']}：{x['description']}"),
        ("proposition", "propositions.jsonl", "proposition_id", lambda x: f"{x['type']}：{x['statement']}"),
        ("love_language", "love-languages.jsonl", "language_id", lambda x: f"爱语“{x['name_zh']}”：{x['definition']}；边界：{'；'.join(x.get('key_limits', []))}"),
        ("governance_rule", "rule-mapping.jsonl", "rule_id", lambda x: f"{x['title']}。适用提示：{'；'.join(x.get('decision_guidance', []) + x.get('conditions_and_exceptions', [])[:2])}"),
        ("interpretation", "interpretations.jsonl", "interpretation_id", lambda x: f"问题范围：{x['question_scope']}。解释：{x['statement']}"),
    ]
    rows = []
    for kind, filename, id_key, render in specs:
        for item in read_jsonl(KNOWLEDGE / filename):
            refs = item.get("source_refs", [])
            chapter_refs = [r for r in refs if any(f"PoL/{n}." in r.get("source_path", "") for n in range(9))]
            # Keep the benchmark within the nine PoL2 theory chapters.
            if not chapter_refs:
                continue
            rows.append({
                "atom_id": item[id_key], "kind": kind, "claim": render(item),
                "source_refs": chapter_refs,
                "status": item.get("status", "candidate"),
            })
    # Source items can overlap across tables. Preserve the provenance but avoid
    # counting identical statements as independent theory units.
    unique = {}
    for row in rows:
        key = " ".join(row["claim"].casefold().split())
        if key not in unique:
            unique[key] = row
        else:
            unique[key]["source_refs"] += [r for r in row["source_refs"] if r not in unique[key]["source_refs"]]
            unique[key]["also_indexed_as"] = unique[key].get("also_indexed_as", []) + [row["atom_id"]]
    return list(unique.values())


def generate(atom: dict) -> list[dict]:
    schema = {"type": "object", "properties": {"scenarios": {"type": "array", "items": {"type": "string"}}}, "required": ["scenarios"]}
    cases = []
    cue_terms = ("pol2", "po l2", "爱2", "该原则", "符合", "违反", "正确", "错误", "consistent", "conflicting", "insufficient")
    for label, instruction in (
        ("consistent", "关键事实体现条目所描述或要求的关系"),
        ("conflicting", "关键事实与条目所描述或要求的关系相反"),
        ("insufficient", "情境缺少决定条目是否适用的关键可观察事实"),
    ):
        prompt = (
            f"依据条目，生成恰好2个不同的中文事实情境。目标类型：{instruction}。"
            "每个情境1至3句、至少35个汉字，交代主体、行为和必要背景。只陈述事实，不下结论。"
            "不得出现 PoL2、爱2、符合、违反、正确、错误、公平、正义或任何标签词；不得复述条目原句，"
            "不加入其他规则，不编造阈值；两例使用不同主体或领域。仅返回两个完整字符串。\n\n条目：" + atom["claim"]
        )
        last = None
        for attempt in range(3):
            result = call_ollama(MODELS["generator"], "你只写不带评价的事实情境，严格遵守数量和格式。",
                                 prompt + ("\n上次输出不合格，请重新生成。" if attempt else ""), schema, 0.25)
            scenarios = result.get("scenarios", [])
            if len(scenarios) == 2 and all(len(s) >= 35 and not any(term in s.casefold() for term in cue_terms) for s in scenarios) and scenarios[0] != scenarios[1]:
                cases.extend({"case": s, "label": label, "decisive_fact": s} for s in scenarios)
                break
            last = scenarios
        else:
            raise ValueError(f"invalid {label} scenarios for {atom['atom_id']}: {last}")
    return cases


def adjudicate(atom: dict, cases: list[dict]) -> list[dict]:
    schema = {
        "type": "object", "properties": {"judgments": {"type": "array", "items": {
            "type": "object", "properties": {
                "case_index": {"type": "integer"},
                "label": {"type": "string", "enum": sorted(LABELS)},
                "valid": {"type": "boolean"},
                "reason": {"type": "string"},
            }, "required": ["case_index", "label", "valid", "reason"],
        }}}, "required": ["judgments"],
    }
    prompt = (
        "以下是 6 个针对同一条 PoL2 条目的情境。请逐条独立判定，不看生成器给的预期标签。"
        "consistent 表示明确符合条目；conflicting 表示明确违反；insufficient 表示信息不足或条文不能确定。"
        "只有标签明确且情境确实围绕该条目时 valid=true。不要替条文补充优先级、阈值或例外。\n\n"
        f"条目：{atom['claim']}\n来源摘录：{json.dumps(atom['source_refs'], ensure_ascii=False)}\n"
        f"情境：{json.dumps([{ 'case_index': i, 'case': c['case'], 'decisive_fact': c['decisive_fact']} for i,c in enumerate(cases)], ensure_ascii=False)}"
    )
    result = call_ollama(MODELS["judge"],
        "你是独立机器裁定器。按提供的冻结条目判断，不沿用案例作者的立场。遇到歧义应给 insufficient。",
        prompt, schema, 0.0)
    judgments = result.get("judgments", [])
    if len(judgments) != len(cases):
        raise ValueError(f"wrong judgment count for {atom['atom_id']}")
    by_i = {int(x["case_index"]): x for x in judgments}
    if set(by_i) != set(range(len(cases))):
        raise ValueError(f"invalid judgment indices for {atom['atom_id']}")
    kept = []
    for i, case in enumerate(cases):
        j = by_i[i]
        if j["valid"] and j["label"] == case["label"]:
            kept.append({**case, "adjudication": j})
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--max-atoms", type=int, default=0, help="0 means every source-linked atom")
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite {args.output}")
    args.output.mkdir(parents=True)
    atoms = atomize()
    if args.max_atoms:
        atoms = atoms[:args.max_atoms]
    out = args.output
    raw_path = out / "generation_audit.jsonl"
    train, test, audit = [], [], []
    for index, atom in enumerate(atoms, 1):
        generated = generate(atom)
        accepted = adjudicate(atom, generated)
        by_label = {label: [c for c in accepted if c["label"] == label] for label in LABELS}
        for label, cases in by_label.items():
            # Keep two independently generated examples per class; first is
            # training, second is held out. A class missing either is uncovered.
            if len(cases) < 2:
                continue
            for variant, case in enumerate(cases[:2]):
                row = {
                    "id": f"{atom['atom_id']}-{label}-{variant+1}",
                    "atom_id": atom["atom_id"], "kind": atom["kind"],
                    "chapter_refs": sorted({r["source_path"] for r in atom["source_refs"]}),
                    "source_status": atom["status"],
                    "scenario": case["case"], "label": label,
                    "decisive_fact": case["decisive_fact"],
                    "machine_adjudication": case["adjudication"],
                    "generator_model": MODELS["generator"], "judge_model": MODELS["judge"],
                }
                (train if variant == 0 else test).append(row)
        audit.append({"atom_id": atom["atom_id"], "kind": atom["kind"],
            "source_refs": atom["source_refs"], "generated_n": len(generated),
            "accepted_n": len(accepted),
            "accepted_by_label": {k: len(v) for k,v in by_label.items()},
            "covered": all(len(by_label[k]) >= 2 for k in LABELS)})
        raw_path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in audit), encoding="utf-8")
        print(f"[{index}/{len(atoms)}] {atom['atom_id']} accepted={len(accepted)}/6 coverage={audit[-1]['covered']}", flush=True)
    for name, rows in (("train.cases.jsonl", train), ("test.cases.jsonl", test)):
        (out / name).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    manifest = {
        "experiment": "PoL2 full-theory machine-adjudicated challenge set",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "all source-linked items in the 9 PoL2 chapters from six structured knowledge files; deduplicated by statement",
        "atom_count": len(atoms), "train_n": len(train), "test_n": len(test),
        "covered_atoms": sum(x["covered"] for x in audit),
        "uncovered_atoms": [x["atom_id"] for x in audit if not x["covered"]],
        "label_source": "programmatic class assignment by Llama 3.1 8B generator, retained only when Qwen 2.5 7B independent adjudicator agrees",
        "limitations": [
            "AI agreement is not independent normative ground truth; both models see the same structured claim and source excerpts.",
            "Only atoms with two accepted cases per class enter both splits; coverage gaps remain explicit.",
            "The knowledge pack contains candidate rule mappings and researcher interpretations in addition to direct source excerpts.",
            "This evaluates version-bounded scenario consistency, not subjective belief or future theory versions.",
        ],
        "input_sha256": {n: digest(KNOWLEDGE / n) for n in ["concepts.jsonl","relations.jsonl","propositions.jsonl","love-languages.jsonl","rule-mapping.jsonl","interpretations.jsonl"]},
        "atom_audit": audit,
    }
    manifest["pilot_limit_atoms"] = args.max_atoms or None
    manifest["generation_script_sha256"] = digest(Path(__file__))
    (out / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("atom_count","train_n","test_n","covered_atoms","uncovered_atoms")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
