"""多源答案比对与裁决，产出 label 记录（契约 3.4 节）。

硬规则（SPEC「不把同源教师一致当真值」+ DATA-02 lead 追加约束）：
- label 只由教师池产出：至少 --min-lineages（默认 2）个不同血缘逐题一致才采纳；
  glm-5.3 与 glm-5.3-flash 同血缘，同血缘多源一致只记为 same_family_only。
- 生成该 case 的血缘（provenance.generator_lineage）必须从教师池剔除后再判定。
- Luna 与 fixture 默认整体排除（--exclude-lineage，默认 luna,fixture），只作自评分析。
- 分歧、同血缘一致、缺答案、内部矛盾一律不产 label，写 <region>.pending.jsonl 等第三方或人工。
- 只有两类 review_level：model_cross_checked / human_reviewed，绝不写"金标准"。

    uv run --no-project --offline python datasets/pol2/pipeline/adjudicate.py \
        --cases train.cases.jsonl --questions train.questions.jsonl \
        --answers train.answers.glm-5.3.jsonl --answers train.answers.jev-<v>.jsonl \
        --out adjudication --region train
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clients import SOURCES  # noqa: E402
from common import (ACTIONS, PIPELINE_REGIONS, STATUSES, index_unique, iso_now,  # noqa: E402
                    normalize_probs, read_answers, read_jsonl, read_questions, require, text,
                    validate_case, validate_label, write_json_atomic, write_jsonl_atomic)

TOOL = "pol2-adjudicate"
ADJUDICATION_VERSION = "pol2-adjudication-v0.1"
DEFAULT_EXCLUDE_LINEAGES = ("openai-luna", "luna", "fixture")
LOAD_BEARING_KEYS = ("status", "polarity", "evidence")


def resolve_lineage(source, overrides):
    """Return (lineage, mapped). mapped=False means we cannot vouch for the family."""
    if source in overrides:
        return overrides[source], True
    if source in SOURCES:
        return SOURCES[source]["lineage"], True
    lowered = source.lower()
    for prefix, lineage in (("glm", "glm"), ("jev", "typesafe-jev"), ("fixture", "fixture")):
        if lowered.startswith(prefix):
            return lineage, True
    if "luna" in lowered:
        return "openai-luna", True
    return source, False


class Policy:
    def __init__(self, overrides=None, exclude_lineages=DEFAULT_EXCLUDE_LINEAGES, min_lineages=2,
                 allow_majority=False, allow_missing_issues=False):
        self.overrides = dict(overrides or {})
        self.exclude_lineages = tuple(exclude_lineages)
        self.min_lineages = min_lineages
        self.allow_majority = allow_majority
        self.allow_missing_issues = allow_missing_issues


def question_state(rows, policy):
    """rows: {source: (answer_row, lineage, mapped)} for one question (all ok)."""
    if not rows:
        return {"state": "no_answers", "values": {}, "lineages": [], "adopted": None}
    values = {}
    lineages = set()
    mapped_lineages = set()
    for source, (row, lineage, mapped) in rows.items():
        values[source] = row["answer"]
        lineages.add(lineage)
        if mapped:
            mapped_lineages.add(lineage)
    distinct_values = []
    for value in values.values():
        if value not in distinct_values:
            distinct_values.append(value)
    info = {"values": values, "lineages": sorted(lineages),
            "mapped_lineages": sorted(mapped_lineages)}
    if len(mapped_lineages) < policy.min_lineages:
        return {"state": "same_family_only" if len(lineages) == 1 else "insufficient_lineages",
                "adopted": None, **info}
    tally = Counter(values.values())
    top, count = tally.most_common(1)[0]
    if len(distinct_values) == 1:
        return {"state": "agreed", "adopted": distinct_values[0], **info}
    if policy.allow_majority and count > len(values) / 2:
        return {"state": "majority", "adopted": top, **info}
    return {"state": "disagreed", "adopted": None, **info}


def adjudicate_case(case, questions, by_qid, policy):
    """Return (label_or_None, pending_or_None)."""
    generator_lineage = case.get("provenance", {}).get("generator_lineage")
    report = {"id": case["id"], "region": case["region"],
              "generator_lineage": generator_lineage, "questions": [],
              "sources": [], "disagreements": []}
    if not text(generator_lineage):
        report["reason"] = "missing_generator_lineage"
        return None, report

    states = {}
    sources_used = set()
    for question in questions:
        rows = {}
        for source, row in by_qid.get(question["qid"], {}).items():
            if row["execution_status"] != "ok":
                continue
            lineage, mapped = resolve_lineage(source, policy.overrides)
            if lineage in policy.exclude_lineages or lineage == generator_lineage:
                continue
            rows[source] = (row, lineage, mapped)
        info = question_state(rows, policy)
        info.update({"qid": question["qid"], "key": question["key"], "kind": question["kind"]})
        states[question["key"]] = info
        report["questions"].append({k: info[k] for k in
                                    ("qid", "key", "state", "values", "lineages")})
        sources_used.update(rows)
        if info["state"] == "agreed":
            continue
        if info["state"] == "majority":
            report["disagreements"].append(
                {**{k: info[k] for k in ("qid", "key", "state", "values")},
                 "blocking": False, "note": "majority adopted (--allow-majority)"})
            continue
        if question["kind"] == "score":
            report["disagreements"].append({**{k: info[k] for k in ("qid", "key", "state", "values")},
                                            "blocking": False})
            continue
        if info["state"] == "no_answers" and question["key"].startswith("issue.") \
                and policy.allow_missing_issues:
            report["disagreements"].append({**{k: info[k] for k in ("qid", "key", "state", "values")},
                                            "blocking": False, "note": "issue question unanswered"})
            continue
        report["disagreements"].append({**{k: info[k] for k in ("qid", "key", "state", "values")},
                                        "blocking": True})
    report["sources"] = sorted(sources_used)
    if not sources_used:
        report["reason"] = "no_usable_sources"
        return None, report
    blocking = [row for row in report["disagreements"] if row["blocking"]]
    if blocking:
        report["reason"] = "unresolved_questions"
        return None, report
    missing_keys = [key for key in LOAD_BEARING_KEYS + ("action",) if key not in states]
    if missing_keys:
        report["reason"] = "missing_question_keys"
        report["note"] = f"questions missing {sorted(missing_keys)}"
        return None, report

    status = states["status"]["adopted"]
    polarity = states["polarity"]["adopted"]
    evidence = states["evidence"]["adopted"]
    issues = sorted(key.split(".", 1)[1] for key, info in states.items()
                    if key.startswith("issue.") and info.get("adopted") == "yes")
    if status == "violating" and not issues:
        report["reason"] = "inconsistent_answers"
        report["note"] = "violating without any yes-issue"
        return None, report
    if status == "conforming" and issues:
        report["reason"] = "inconsistent_answers"
        report["note"] = "conforming with a yes-issue"
        return None, report
    if status == "violating" and evidence == "insufficient":
        report["reason"] = "inconsistent_answers"
        report["note"] = "violating with insufficient evidence"
        return None, report
    if status == "conforming" and evidence == "insufficient":
        report["reason"] = "inconsistent_answers"
        report["note"] = "conforming with insufficient evidence"
        return None, report
    if status == "violating" and polarity == "love":
        report["reason"] = "inconsistent_answers"
        report["note"] = "violating with polarity=love"
        return None, report
    if status in ("conforming", "insufficient") and polarity == "hate":
        report["reason"] = "inconsistent_answers"
        report["note"] = f"{status} with polarity=hate"
        return None, report

    actions = []
    action_info = states.get("action", {"values": {}})
    for action in ACTIONS:
        if action in action_info.get("values", {}).values():
            actions.append(action)
    if not actions:
        report["reason"] = "inconsistent_answers"
        report["note"] = "no acceptable action recorded"
        return None, report

    citations = []
    for citation in [case["input"]["clause"]] + list(case["extra"].get("citations", [])
                                                     if isinstance(case.get("extra"), dict) else []):
        if text(citation) and citation not in citations:
            citations.append(citation)
    probs = None
    prob_rows = []
    for question_qid in [states.get("status", {}).get("qid")]:
        for row in by_qid.get(question_qid, {}).values():
            if row["execution_status"] == "ok" and isinstance(row.get("probs"), dict):
                prob_rows.append(row["probs"])
    if prob_rows:
        keys = set(STATUSES)
        if all(set(row) == keys for row in prob_rows):
            merged = {key: sum(row[key] for row in prob_rows) / len(prob_rows) for key in STATUSES}
            probs = normalize_probs(merged, keys=STATUSES)

    agreement = "majority" if any(info["state"] == "majority" for info in states.values()) \
        else "unanimous_multi_family"
    reason = (f"多源一致（{', '.join(sorted(sources_used))}）：status={status}，"
              f"polarity={polarity}")
    if issues:
        reason += f"，issues={', '.join(issues)}"
    reason += f"；依据 {'、'.join(citations)}。"
    label = {"id": case["id"], "status": status, "polarity": polarity, "issues": issues,
             "evidence": evidence, "acceptable_actions": actions, "citations": citations,
             "brief_reason": reason,
             "review": {"sources": sorted(sources_used), "agreement": agreement,
                        "disagreements": report["disagreements"],
                        "adjudicated_by": "auto_multi_lineage",
                        "review_level": "model_cross_checked"}}
    if probs is not None:
        label["probs"] = probs
    return label, None


def human_label(row, case):
    require(isinstance(row, dict), "human label must be an object")
    require(text(row.get("reviewer")), "human label needs a reviewer name")
    citations = [case["input"]["clause"]]
    for citation in row.get("citations", []):
        if text(citation) and citation not in citations:
            citations.append(citation)
    label = {"id": case["id"], "status": row.get("status"), "polarity": row.get("polarity"),
             "issues": row.get("issues", []), "evidence": row.get("evidence", "sufficient"),
             "acceptable_actions": row.get("acceptable_actions", []),
             "citations": citations, "brief_reason": row.get("brief_reason"),
             "review": {"sources": [f"human:{row['reviewer']}"], "agreement": "human_decision",
                        "disagreements": row.get("disagreements", []),
                        "adjudicated_by": row["reviewer"], "review_level": "human_reviewed"}}
    for key in ("love_languages", "mitigations"):
        if key in row:
            label[key] = row[key]
    validate_label(label, where=f"human label {case['id']}")
    return label


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--answers", type=Path, action="append", required=True,
                        help="答案文件，可重复；每个来源一份")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--region", choices=PIPELINE_REGIONS, default="train")
    parser.add_argument("--families", type=Path, help="族清单，用于补全 citations")
    parser.add_argument("--lineage", action="append", default=[],
                        help="source=lineage 覆盖，可重复")
    parser.add_argument("--exclude-lineage", default=",".join(DEFAULT_EXCLUDE_LINEAGES))
    parser.add_argument("--min-lineages", type=int, default=2)
    parser.add_argument("--allow-majority", action="store_true",
                        help="允许不同血缘的多数票（默认关：只有一致才采纳）")
    parser.add_argument("--allow-missing-issues", action="store_true",
                        help="issue 题缺答案不阻塞（默认关，会记录在 disagreements）")
    parser.add_argument("--human-labels", type=Path,
                        help="人工审核结果 JSONL：id/status/polarity/issues/acceptable_actions/"
                             "brief_reason/reviewer，覆盖机器裁决并标 human_reviewed")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        require(args.min_lineages >= 2, "--min-lineages must be >= 2")
        overrides = {}
        for item in args.lineage:
            require("=" in item, f"--lineage expects source=lineage, got {item!r}")
            source, lineage = item.split("=", 1)
            require(text(source) and text(lineage), f"--lineage expects source=lineage, got {item!r}")
            overrides[source.strip()] = lineage.strip()
        policy = Policy(overrides=overrides,
                        exclude_lineages=[item for item in args.exclude_lineage.split(",")
                                          if item.strip()],
                        min_lineages=args.min_lineages, allow_majority=args.allow_majority,
                        allow_missing_issues=args.allow_missing_issues)
        cases = read_jsonl(args.cases)
        require(bool(cases), f"{args.cases}: no cases")
        case_index = index_unique(cases, "id", where=str(args.cases))
        for case_id, case in case_index.items():
            validate_case(case, where=f"{args.cases}:{case_id}")
            require(case["region"] == args.region,
                    f"{case_id}: case region {case['region']} != --region {args.region}")
        questions = read_questions(args.questions)
        question_index = {row["qid"]: row for row in questions}
        per_case = {}
        for row in questions:
            require(row["id"] in case_index,
                    f"{row['qid']}: question references unknown case {row['id']!r}")
            per_case.setdefault(row["id"], []).append(row)
        answers = []
        for path in args.answers:
            answers.extend(read_answers(path, questions=question_index))
        by_qid = {}
        for row in answers:
            bucket = by_qid.setdefault(row["qid"], {})
            require(row["source"] not in bucket,
                    f"duplicate answer for {row['qid']} from {row['source']} "
                    f"(two files or two rows)")
            bucket[row["source"]] = row
        family_clauses = {}
        if args.families:
            for row in read_jsonl(args.families):
                family_clauses[row["family_id"]] = list(row.get("clauses", []))
        human_rows = {}
        if args.human_labels:
            for row in read_jsonl(args.human_labels):
                require(row.get("id") in case_index,
                        f"human label names unknown case {row.get('id')!r}")
                require(row["id"] not in human_rows, f"duplicate human label {row['id']}")
                human_rows[row["id"]] = row
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"adjudicate: {error}\n")

    labels, pendings = [], []
    reason_counts = Counter()
    lineage_used = Counter()
    unmapped_sources = set()
    for case in cases:
        case_id = case["id"]
        for extra_clause in family_clauses.get(case["family_id"], []):
            if extra_clause != case["input"]["clause"]:
                case.setdefault("extra", {})
                citations = case["extra"].setdefault("citations", [])
                if extra_clause not in citations:
                    citations.append(extra_clause)
        if case_id in human_rows:
            labels.append(human_label(human_rows[case_id], case))
            lineage_used["human"] += 1
            continue
        label, pending = adjudicate_case(case, per_case.get(case_id, []), by_qid, policy)
        if label is not None:
            validate_label(label, where=f"{case_id}")
            for source in label["review"]["sources"]:
                lineage, mapped = resolve_lineage(source, overrides)
                lineage_used[lineage] += 1
                if not mapped:
                    unmapped_sources.add(source)
            labels.append(label)
        else:
            reason_counts[pending["reason"]] += 1
            pendings.append({**pending, "review": {"sources": pending["sources"],
                                                   "disagreements": pending["disagreements"],
                                                   "adjudicated_by": "pending_independent_source",
                                                   "review_level": None},
                             "created_at": iso_now()})

    labels_path = Path(args.out) / f"{args.region}.labels.jsonl"
    pending_path = Path(args.out) / f"{args.region}.pending.jsonl"
    write_jsonl_atomic(labels_path, labels)
    write_jsonl_atomic(pending_path, pendings)
    policy_report = {"tool": TOOL, "version": ADJUDICATION_VERSION, "region": args.region,
                     "cases": len(cases), "labels": len(labels), "pending": len(pendings),
                     "pending_reasons": dict(reason_counts),
                     "min_lineages": policy.min_lineages,
                     "exclude_lineages": list(policy.exclude_lineages),
                     "allow_majority": policy.allow_majority,
                     "allow_missing_issues": policy.allow_missing_issues,
                     "answer_files": [str(path) for path in args.answers],
                     "sources": sorted({row["source"] for row in answers}),
                     "lineage_usage_in_labels": dict(lineage_used),
                     "unmapped_sources": sorted(unmapped_sources),
                     "human_labels": len(human_rows),
                     "review_levels": dict(Counter(row["review"]["review_level"]
                                                   for row in labels)),
                     "created_at": iso_now()}
    write_json_atomic(Path(args.out) / f"adjudication.{args.region}.json", policy_report)
    print(json.dumps({"region": args.region, "labels": len(labels), "pending": len(pendings),
                      "pending_reasons": dict(reason_counts),
                      "unmapped_sources": sorted(unmapped_sources),
                      "labels_path": str(labels_path), "pending_path": str(pending_path)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
