"""Build an auditable, knowledge-type-specific PoL2 recognition pilot.

Labels are copied from the versioned structured knowledge pack. No model
generates or adjudicates labels. The resulting public set is exploratory,
not a normative gold standard or a sealed test set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
KNOWLEDGE = ROOT / "POL2-Steward" / "pol2-service" / "knowledge"
DEFAULT_OUT = Path(__file__).resolve().parent / "data-v1.3"
SEED = 20261026


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chapter_key(path: str) -> str | None:
    name = Path(path).name
    if name == "Readme.md":
        return "readme"
    if "工程策略" in name:
        return "engineering"
    stem = name.split(".", 1)[0]
    if stem.isdigit() and 0 <= int(stem) <= 8:
        return stem
    return None


def source_key(ref: dict) -> str:
    return f"{ref['source_path']}#p{ref['paragraph']}"


def excerpt(ref: dict) -> str:
    return f"[{source_key(ref)}] {ref.get('excerpt', '').strip()}"


def options_for(target: dict, pool: list[dict], k: int, rng: random.Random) -> list[dict]:
    target_key = target["key"]
    others = [x for x in pool if x["key"] != target_key]
    picked = [target, *rng.sample(others, min(k - 1, len(others)))]
    rng.shuffle(picked)
    return picked


def build(out: Path) -> None:
    if out.exists():
        raise SystemExit(f"Refusing to overwrite {out}")
    out.mkdir(parents=True)
    rng = random.Random(SEED)
    inputs = {
        name: KNOWLEDGE / name for name in (
            "concepts.jsonl", "relations.jsonl", "propositions.jsonl",
            "love-languages.jsonl", "rule-mapping.jsonl", "interpretations.jsonl",
        )
    }
    data = {name: read_jsonl(path) for name, path in inputs.items()}
    concepts = data["concepts.jsonl"]
    concept_by_id = {x["concept_id"]: x for x in concepts}
    records: list[dict] = []
    labels: list[dict] = []

    def add(item: dict, label: dict) -> None:
        records.append(item)
        labels.append(label)

    # 1. Concepts and relations: definition-to-concept and directed graph completion.
    concept_options = [{"key": x["concept_id"], "label": x["name_zh"]} for x in concepts]
    for c in concepts:
        opts = options_for({"key": c["concept_id"], "label": c["name_zh"]}, concept_options, 4, rng)
        refs = c["source_refs"]
        add({
            "id": f"concept:{c['concept_id']}", "knowledge_type": "concepts_relations",
            "task_type": "definition_to_concept", "question": f"以下定义对应哪个概念？\n{c['definition']}",
            "options": opts, "source_context": "\n".join(r.get("excerpt", "") for r in refs),
            "source_record": {"record_id": c["concept_id"], "status": c["status"]},
        }, {"id": f"concept:{c['concept_id']}", "answer": c["concept_id"], "basis": "concepts.jsonl.concept_id + definition", "source_refs": refs, "source_status": c["status"]})

    nodes = sorted({x[k] for x in data["relations.jsonl"] for k in ("from", "to")})
    node_label = {x["concept_id"]: x["name_zh"] for x in concepts}
    node_label.update({n: node_label.get(n, n.replace("_", " ")) for n in nodes})
    node_options = [{"key": n, "label": node_label[n]} for n in nodes]
    for r in data["relations.jsonl"]:
        target = {"key": r["to"], "label": node_label[r["to"]]}
        opts = options_for(target, node_options, 4, rng)
        refs = r["source_refs"]
        add({
            "id": f"relation:{r['relation_id']}", "knowledge_type": "concepts_relations",
            "task_type": "directed_relation_completion",
            "question": f"在有向知识关系中，主体“{node_label[r['from']]}”与关系“{r['type']}”连接到哪个对象？",
            "options": opts, "source_context": "\n".join(x.get("excerpt", "") for x in refs),
            "source_record": {"record_id": r["relation_id"], "status": r["status"]},
        }, {"id": f"relation:{r['relation_id']}", "answer": r["to"], "basis": "relations.jsonl.from/type/to", "source_refs": refs, "source_status": r["status"]})

    # 2. Axioms and propositions: four axiom-component identifications plus
    # source-chapter attribution for the nine indexed propositions.
    axiom_edges = {"REL-009", "REL-010", "REL-011", "REL-012"}
    axiom_names = ["正念", "空性", "不二", "无量慈悲"]
    axiom_candidates = [{"key": n, "label": n} for n in axiom_names]
    for edge in data["relations.jsonl"]:
        if edge["relation_id"] not in axiom_edges:
            continue
        c = concept_by_id[edge["to"]]
        target = {"key": c["name_zh"], "label": c["name_zh"]}
        opts = options_for(target, axiom_candidates, 4, rng)
        refs = edge["source_refs"]
        add({
            "id": f"axiom:{edge['relation_id']}", "knowledge_type": "axioms_propositions",
            "task_type": "axiom_component_identification",
            "question": f"下列公理描述对应四公理中的哪一项？\n{c['definition']}",
            "options": opts, "source_context": "\n".join(x.get("excerpt", "") for x in refs),
            "source_record": {"record_id": edge["relation_id"], "status": edge["status"]},
        }, {"id": f"axiom:{edge['relation_id']}", "answer": c["name_zh"], "basis": "REL-009–REL-012 + concepts.jsonl definition", "source_refs": refs, "source_status": edge["status"]})

    chapter_pool = [{"key": str(n), "label": f"第{n}章"} for n in range(9)] + [
        {"key": "engineering", "label": "PoL共识工程策略"},
        {"key": "readme", "label": "PoL说明文档"},
    ]
    for p in data["propositions.jsonl"]:
        chapter_refs = [r for r in p["source_refs"] if chapter_key(r["source_path"]) is not None]
        if not chapter_refs:
            continue
        answers = sorted({chapter_key(r["source_path"]) for r in chapter_refs})
        add({
            "id": f"proposition:{p['proposition_id']}", "knowledge_type": "axioms_propositions",
            "task_type": "proposition_source_attribution",
            "question": f"这条结构化命题在知识包中引用了哪些直接来源文件？命题：{p['statement']}\n可多选。",
            "options": chapter_pool, "source_context": "\n".join(excerpt(r) for r in chapter_refs),
            "source_record": {"record_id": p["proposition_id"], "type": p["type"], "status": p["status"]},
        }, {"id": f"proposition:{p['proposition_id']}", "answer": "|".join(answers), "basis": "propositions.jsonl.source_refs; chapter keys derived from cited paths", "source_refs": chapter_refs, "source_status": p["status"]})

    # 3. Love languages: source definition -> one of the 16 named categories.
    languages = data["love-languages.jsonl"]
    language_pool = [{"key": x["language_id"], "label": x["name_zh"]} for x in languages]
    for x in languages:
        target = {"key": x["language_id"], "label": x["name_zh"]}
        opts = options_for(target, language_pool, 4, rng)
        refs = x["source_refs"]
        add({
            "id": f"love_language:{x['language_id']}", "knowledge_type": "love_languages",
            "task_type": "definition_to_love_language",
            "question": f"以下定义对应哪一种爱语？\n{x['definition']}\n边界：{'；'.join(x.get('key_limits', []))}",
            "options": opts, "source_context": "\n".join(r.get("excerpt", "") for r in refs),
            "source_record": {"record_id": x["language_id"], "status": x["status"]},
        }, {"id": f"love_language:{x['language_id']}", "answer": x["language_id"], "basis": "love-languages.jsonl.language_id + definition + key_limits", "source_refs": refs, "source_status": x["status"]})

    # 4. Explicit governance rules: map a typed review question to the indexed
    # rule. The source_status is retained because all mappings are annotations.
    rules = data["rule-mapping.jsonl"]
    rule_pool = [{"key": x["rule_id"], "label": f"{x['rule_id']} — {x['title']}"} for x in rules]
    for r in rules:
        q = (r.get("check_questions") or r.get("decision_guidance") or [r["title"]])[0]
        target = {"key": r["rule_id"], "label": f"{r['rule_id']} — {r['title']}"}
        opts = options_for(target, rule_pool, 4, rng)
        refs = r["source_refs"]
        add({
            "id": f"rule:{r['rule_id']}", "knowledge_type": "explicit_governance_rules",
            "task_type": "review_question_to_rule", "question": f"在治理审查中，下列检查问题对应哪条已索引规则？\n{q}",
            "options": opts, "source_context": "\n".join(x.get("excerpt", "") for x in refs),
            "source_record": {"record_id": r["rule_id"], "status": r["status"], "approved_decisions": r.get("approved_decisions", [])},
        }, {"id": f"rule:{r['rule_id']}", "answer": r["rule_id"], "basis": "rule-mapping.jsonl.rule_id + check_questions + source_refs", "source_refs": refs, "source_status": r["status"], "approved_decisions": r.get("approved_decisions", [])})

    # 5. Researcher interpretations: provenance retrieval, not direct theory
    # truth classification. Labels are the cited knowledge-pack anchors.
    interpretations = data["interpretations.jsonl"]
    ref_pool_by_key: dict[str, dict] = {}
    for row in interpretations:
        for ref in row["source_refs"]:
            ref_pool_by_key.setdefault(source_key(ref), ref)
    ref_pool = [{"key": key, "label": excerpt(ref)} for key, ref in sorted(ref_pool_by_key.items())]
    for interp in interpretations:
        refs = interp["source_refs"]
        correct = [source_key(r) for r in refs]
        distractors = [x for x in ref_pool if x["key"] not in correct]
        opts = [{"key": source_key(r), "label": source_key(r)} for r in refs]
        opts += rng.sample(distractors, min(max(0, 4 - len(opts)), len(distractors)))
        rng.shuffle(opts)
        opts = [{"key": x["key"], "label": x["key"]} for x in opts]
        add({
            "id": f"interpretation:{interp['interpretation_id']}", "knowledge_type": "researcher_interpretations",
            "task_type": "interpretation_provenance_retrieval",
            "question": f"请找出知识包为这条研究者综合解释登记的直接来源锚点。\n范围：{interp['question_scope']}\n解释：{interp['statement']}\n可多选，只选直接登记的出处。",
            "options": opts,
            "source_context": "\n".join(excerpt(ref_pool_by_key[x["key"]]) for x in opts),
            "source_record": {"record_id": interp["interpretation_id"], "status": interp["status"], "limitations": interp.get("limitations", [])},
        }, {"id": f"interpretation:{interp['interpretation_id']}", "answer": "|".join(sorted(correct)), "basis": "interpretations.jsonl.source_refs; labels are curated provenance, not proof of semantic entailment", "source_refs": refs, "source_status": interp["status"], "limitations": interp.get("limitations", [])})

    records.sort(key=lambda x: x["id"])
    labels.sort(key=lambda x: x["id"])
    if len({x["id"] for x in records}) != len(records) or {x["id"] for x in records} != {x["id"] for x in labels}:
        raise ValueError("duplicate item id or items/labels mismatch")
    for item, label in zip(records, labels):
        option_keys = {x["key"] for x in item["options"]}
        if not set(label["answer"].split("|")) <= option_keys:
            raise ValueError(f"reference answer is absent from options: {item['id']}")
        if not label["source_refs"]:
            raise ValueError(f"missing source provenance: {item['id']}")
    write_jsonl(out / "items.jsonl", records)
    write_jsonl(out / "labels.jsonl", labels)
    source_manifest_path = KNOWLEDGE / "source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "dataset_id": "pol2-typed-knowledge-v1.3",
        "created_utc": "2026-10-26",
        "seed": SEED,
        "source_manifest": str(source_manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "source_manifest_sha256": sha256(source_manifest_path),
        "source_commit": source_manifest["source_commit"],
        "theory_source_sha256_normalized": {x["path"]: x["sha256"] for x in source_manifest["files"] if x["role"] == "theory"},
        "input_sha256": {name: sha256(path) for name, path in inputs.items()},
        "item_sha256": sha256(out / "items.jsonl"),
        "label_sha256": sha256(out / "labels.jsonl"),
        "n_items": len(records),
        "by_knowledge_type": {},
        "label_status_by_type": {},
        "conditions": ["closed_book", "source_context"],
        "limits": [
            "Public exploratory set; items and labels are not sealed and must not be used for confirmatory claims.",
            "Knowledge-pack statuses and source anchors provide traceability, not complete normative gold labels.",
            "Rule mappings retain candidate versus approved-boundary provenance; scores must be stratified by this status.",
            "Interpretation source anchors measure curated provenance retrieval, not entailment or truth of the interpretation.",
            "Source context contains source excerpts only; the structured target record is withheld.",
            "No model is trained on this set; no aggregate score is computed across knowledge types.",
        ],
    }
    for typ in sorted({x["knowledge_type"] for x in records}):
        ids = [x["id"] for x in records if x["knowledge_type"] == typ]
        manifest["by_knowledge_type"][typ] = len(ids)
        manifest["label_status_by_type"][typ] = {}
        for label in labels:
            if label["id"] in ids:
                status = label["source_status"]
                manifest["label_status_by_type"][typ][status] = manifest["label_status_by_type"][typ].get(status, 0) + 1
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": manifest["dataset_id"], "n_items": len(records), "by_knowledge_type": manifest["by_knowledge_type"], "label_status_by_type": manifest["label_status_by_type"], "items_sha256": manifest["item_sha256"], "labels_sha256": manifest["label_sha256"]}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
