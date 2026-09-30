"""按场景族生成 PoL2 case（最小对立对），并由 case 派生 question。

契约：datasets/pol2/README.md 第 3 节（case/question 字段名固定，扩展只走 extra）。
配对元数据：pair_id / variant / diff 在 case 顶层，quality_flag 与 generator_lineage 在 provenance。

默认离线：不加 --live 只写请求计划，不联网；--fixture 用确定性合成数据跑通全链路。
断点续跑：按 (family, batch) 原子写分片，重跑跳过已完成批次；plan.json 记录配置摘要，
配置变化时拒绝写入同一 --out（换新目录）。

    uv run --no-project --offline python datasets/pol2/pipeline/generate.py \
        --families datasets/pol2/families.jsonl --assign <分配表> --out <新目录> --limit 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clients import (SOURCES, CallFailure, CallLog, build_client,  # noqa: E402
                     run_ordered)
from common import (EXECUTION_STATUSES, PIPELINE_REGIONS, REGIONS, SURFACES, append_jsonl,  # noqa: E402
                    csv_list, index_unique, integer, iso_now, normalized_text, read_jsonl,
                    require, sha256_text, text, validate_case, validate_question,
                    write_json_atomic, write_json_new, write_jsonl_atomic, write_jsonl_new)
import fixtures  # noqa: E402
import prompts  # noqa: E402

TOOL = "pol2-generate"
GEN_SCHEMA_VERSION = "pol2-pipeline-v0.1"


# ------------------------------------------------------------------ inputs

def load_families(path):
    rows = read_jsonl(path)
    require(bool(rows), f"{path}: no families")
    index_unique(rows, "family_id", where=str(path))
    for row in rows:
        require(isinstance(row.get("surfaces"), list) and row["surfaces"],
                f"{path}: {row['family_id']}: surfaces must be a non-empty array")
        require(all(surface in SURFACES for surface in row["surfaces"]),
                f"{path}: {row['family_id']}: surfaces must use {SURFACES}")
        require(isinstance(row.get("clauses"), list) and row["clauses"]
                and all(text(clause) for clause in row["clauses"]),
                f"{path}: {row['family_id']}: clauses must be a non-empty array of strings")
        if "target_cases" in row:
            require(integer(row["target_cases"]) and row["target_cases"] > 0,
                    f"{path}: {row['family_id']}: target_cases must be a positive integer")
    return rows


def load_assignment(path):
    rows = read_jsonl(path)
    index = index_unique(rows, "family_id", where=str(path))
    assignment = {}
    for family_id, row in index.items():
        region = row.get("region")
        require(region in REGIONS, f"{path}: {family_id}: region must be one of {REGIONS}")
        assignment[family_id] = region
    return assignment


def select_families(families, filters, assignment, region):
    """Return [{family, region}] in deterministic (sorted family_id) order."""
    by_id = {row["family_id"]: row for row in families}
    if filters:
        unknown = [item for item in filters if item not in by_id]
        require(not unknown, f"unknown family id(s): {unknown}")
        wanted = [by_id[item] for item in filters]
    else:
        wanted = list(families)
    selected = []
    for row in sorted(wanted, key=lambda item: item["family_id"]):
        if assignment is not None:
            require(row["family_id"] in assignment,
                    f"family {row['family_id']} missing from the assignment table")
            chosen = assignment[row["family_id"]]
        else:
            chosen = region
        require(chosen in PIPELINE_REGIONS,
                f"refusing region {chosen!r} for {row['family_id']}: private_holdout is generated "
                f"by an independent custodian outside the repository (only {PIPELINE_REGIONS})")
        selected.append({"family": row, "region": chosen})
    require(bool(selected), "no families selected")
    return selected


# ------------------------------------------------------------------ plan

def build_plan(selected, limit, pairs_per_batch, seed, config):
    """Assign pair/case ordinals per region; deterministic for a fixed input."""
    if limit is None:
        budgets = {item["family"]["family_id"]: None for item in selected}
    else:
        require(integer(limit) and limit > 0, "--limit must be a positive integer")
        remaining = limit
        budgets = {}
        for item in selected:
            family_id = item["family"]["family_id"]
            target = item["family"].get("target_cases")
            pairs = (target + 1) // 2 if target else None
            if remaining <= 0:
                budgets[family_id] = 0
                continue
            if pairs is None:
                pairs = (remaining + 1) // 2
            pairs = min(pairs, (remaining + 1) // 2)
            budgets[family_id] = pairs
            remaining -= pairs * 2
    counters = {region: 0 for region in PIPELINE_REGIONS}
    families = []
    for item in selected:
        family_id = item["family"]["family_id"]
        region = item["region"]
        pairs = budgets[family_id]
        if pairs is None:
            target = item["family"].get("target_cases")
            require(integer(target) and target > 0,
                    f"{family_id}: needs target_cases or --limit")
            pairs = (target + 1) // 2
        if pairs <= 0:
            continue
        first_pair = counters[region] + 1
        counters[region] += pairs
        batches = []
        left = pairs
        while left > 0:
            take = min(pairs_per_batch, left)
            batches.append(take)
            left -= take
        families.append({
            "family_id": family_id, "region": region, "pairs": pairs,
            "cases": pairs * 2, "first_pair_ordinal": first_pair,
            "pair_ids": [f"pol2-{region}-p{first_pair + offset:06d}" for offset in range(pairs)],
            "case_ids": [f"pol2-{region}-{2 * (first_pair - 1) + 2 * offset + variant:06d}"
                         for offset in range(pairs) for variant in (1, 2)],
            "batches": batches,
        })
    require(bool(families), "plan is empty; check --limit and family selection")
    counts = {}
    for item in families:
        counts[item["region"]] = counts.get(item["region"], 0) + item["cases"]
    return {"tool": TOOL, "schema": GEN_SCHEMA_VERSION, "seed": seed,
            "pairs_per_batch": pairs_per_batch, "limit": limit,
            "config_sha256": sha256_text(json.dumps(config, ensure_ascii=False, sort_keys=True)),
            "created_at": iso_now(), "regions": counts,
            "total_pairs": sum(item["pairs"] for item in families),
            "total_cases": sum(item["cases"] for item in families), "families": families}


def config_snapshot(args, families_path, assign_path, issue_labels, selected, criteria=None):
    return {
        "families_sha256": sha256_text(Path(families_path).read_text(encoding="utf-8-sig")),
        "assign_sha256": (sha256_text(Path(assign_path).read_text(encoding="utf-8-sig"))
                          if assign_path else None),
        "region": args.region, "limit": args.limit, "seed": args.seed,
        "pairs_per_batch": args.pairs_per_batch, "model": args.model, "source": args.source,
        "gen_version": prompts.GEN_VERSION, "q_template": prompts.Q_TEMPLATE_VERSION,
        "with_score": args.with_score, "issue_keys": sorted(issue_labels),
        "ontology_source": str(args.issue_keys_file or prompts.ONTOLOGY_DEFAULT),
        "criteria_sections": sorted(criteria or {}),
        "similarity_threshold": args.similarity_threshold,
        "selection": [{"family_id": item["family"]["family_id"], "region": item["region"]}
                      for item in selected],
    }


def prepare_out(out, plan):
    out = Path(out)
    if out.exists():
        plan_path = out / "plan.json"
        require(plan_path.is_file(), f"{out} exists without plan.json; use a new --out directory")
        existing = json.loads(plan_path.read_text(encoding="utf-8"))
        require(existing.get("config_sha256") == plan["config_sha256"],
                f"{out}: plan.json config differs from this run "
                f"({existing.get('config_sha256')} != {plan['config_sha256']}); "
                f"use a new --out directory")
        require(existing.get("families") == plan["families"], f"{out}: plan.json families differ")
        return out, False
    out.mkdir(parents=True)
    write_json_new(out / "plan.json", plan)
    return out, True


# ------------------------------------------------------------------ per-batch production

def _batch_paths(out, family_id, batch_index):
    shard = Path(out) / "shards" / family_id
    return (shard / f"batch-{batch_index:03d}.cases.jsonl",
            shard / f"batch-{batch_index:03d}.questions.jsonl",
            shard / f"batch-{batch_index:03d}.qa.jsonl",
            shard / f"batch-{batch_index:03d}.done.json")


def _coerce_variant(variant, family, notes, case_id):
    require(isinstance(variant, dict), f"{case_id}: variant must be an object")
    surface = variant.get("surface")
    if surface not in family["surfaces"]:
        notes.append({"case_id": case_id, "field": "input.surface",
                      "from": surface, "to": family["surfaces"][0]})
        surface = family["surfaces"][0]
    clause = variant.get("clause")
    if clause not in family["clauses"]:
        notes.append({"case_id": case_id, "field": "input.clause",
                      "from": clause, "to": family["clauses"][0]})
        clause = family["clauses"][0]
    context = variant.get("context")
    require(isinstance(context, list) and context
            and all(text(item) for item in context), f"{case_id}: context must be a non-empty array")
    require(text(variant.get("target")), f"{case_id}: target must be a non-empty string")
    require(text(variant.get("policy")), f"{case_id}: policy must be a non-empty string")
    return {"lang": variant.get("lang") if text(variant.get("lang")) else "zh",
            "surface": surface, "context": [item.strip() for item in context],
            "target": variant["target"].strip(), "policy": variant["policy"].strip(),
            "clause": clause}


def pair_qa_row(pair_id, members, expected, key_fact, threshold):
    """One QA row for a pair of stored/model case objects (single source of truth)."""
    require(set(members) == {"a", "b"}, f"{pair_id}: needs variants a and b")
    quality = prompts.pair_quality(
        {"target": members["a"]["input"]["target"], "surface": members["a"]["input"]["surface"],
         "context": members["a"]["input"]["context"], "expected_status": expected.get("a")},
        {"target": members["b"]["input"]["target"], "surface": members["b"]["input"]["surface"],
         "context": members["b"]["input"]["context"], "expected_status": expected.get("b")},
        threshold=threshold)
    if key_fact is None:
        quality["quality_flags"].append("missing_key_fact")
    return {"pair_id": pair_id, "family_id": members["a"]["family_id"],
            "region": members["a"]["region"], "duplicate_case": False,
            "case_ids": [members["a"]["id"], members["b"]["id"]], "key_fact": key_fact,
            "expected_status": {"a": expected.get("a"), "b": expected.get("b")}, **quality}


def apply_pair_flags(cases, qa_rows):
    """把 pair 级质量标记与整体重复检测写回 case.provenance.quality_flag。"""
    flags_by_pair = {row["pair_id"]: list(row["quality_flags"]) for row in qa_rows}
    flagged = _duplicate_case_ids(cases)
    for row in qa_rows:
        row["duplicate_case"] = any(case_id in flagged for case_id in row["case_ids"])
    for case in cases:
        flags = flags_by_pair.get(case["pair_id"], [])
        if case["id"] in flagged:
            flags = flags + ["duplicate_case"]
        case["provenance"]["quality_flag"] = flags
    return cases, qa_rows


def build_pair_cases(family_item, pair_payloads, pair_ids, case_ids, seed, model, generator,
                     lineage, issue_labels, with_score, criteria=None):
    """Build case/question records for one batch of pairs (no quality flags yet)."""
    family = family_item["family"]
    region = family_item["region"]
    cases, questions, notes = [], [], []
    for offset, payload in enumerate(pair_payloads):
        pair_id = pair_ids[offset]
        pair_case_ids = [case_ids[2 * offset], case_ids[2 * offset + 1]]
        variants = {key: _coerce_variant(payload["variants"][key], family, notes, case_id)
                    for key, case_id in (("a", pair_case_ids[0]), ("b", pair_case_ids[1]))}
        for variant_key, case_id in (("a", pair_case_ids[0]), ("b", pair_case_ids[1])):
            body = variants[variant_key]
            case = {
                "id": case_id, "family_id": family["family_id"], "region": region,
                "lang": body["lang"],
                "input": {"surface": body["surface"], "context": body["context"],
                          "target": body["target"], "policy": body["policy"],
                          "clause": body["clause"]},
                "provenance": {"generator": generator, "model": model,
                               "prompt_id": f"pol2.gen.{prompts.GEN_VERSION}.{family['family_id']}",
                               "gen_version": prompts.GEN_VERSION, "seed": seed,
                               "created_at": iso_now(), "generator_lineage": lineage,
                               "quality_flag": []},
                "pair_id": pair_id, "variant": variant_key,
                "diff": {"key_fact": payload.get("key_fact") or "未说明",
                         "a": payload.get("a_value") or None, "b": payload.get("b_value") or None},
            }
            case["diff"] = {key: value for key, value in case["diff"].items() if value is not None}
            cases.append(case)
            questions.extend(prompts.build_questions(case, issue_labels=issue_labels,
                                                     with_score=with_score, criteria=criteria))
    return cases, questions, notes


def case_material_text(case):
    return prompts.case_material(case["input"])


def _duplicate_case_ids(cases):
    """精确重复检测（context + target 整体一致）：返回需要标记的 case id 集合。"""
    groups = {}
    for case in cases:
        groups.setdefault(normalized_text(case_material_text(case)), []).append(case["id"])
    return {case_id for ids in groups.values() if len(ids) > 1 for case_id in ids}


def produce_batch(args, family_item, batch_index, take, client, issue_labels, diagnostics=None,
                  feedback=None):
    """Produce one batch through the model (or fixture); returns (pairs, result) or raises."""
    family = family_item["family"]
    seed = args.seed + batch_index
    if args.fixture:
        pairs = fixtures.fixture_pairs(family, take, seed=seed)
        return pairs, {"text": None, "usage": {}, "latency_ms": 0.0, "attempts": 0}
    messages = [{"role": "user",
                 "content": prompts.generation_prompt(family, take, seed, feedback=feedback)}]
    if client is None:
        raise CallFailure("error", "live generation requires a client")
    result = client.chat(messages, max_tokens=args.max_tokens)
    if diagnostics is not None:
        # 只留长度与开头摘要，便于诊断截断/非 JSON；完整原文不落盘。
        diagnostics.update({"raw_len": len(result["text"]),
                            "raw_head": result["text"][:200]})
    pairs = prompts.parse_pairs(result["text"])
    return pairs, result


def _variant_material(variant):
    if not isinstance(variant, dict):
        return ""
    context = variant.get("context")
    body = " ".join(item for item in context if isinstance(item, str)) \
        if isinstance(context, list) else ""
    target = variant.get("target")
    return body + " " + (target if isinstance(target, str) else "")


def pair_material_key(pair):
    """整体材料指纹：用于跨批次/族内精确去重。"""
    variants = pair["variants"]
    return normalized_text(_variant_material(variants["a"]) + " " + _variant_material(variants["b"]))


def evaluate_pair(pair, family, threshold):
    """Structural + pair-quality gate. Returns (ok, reason); duplicates by caller.

    不合格的对不写进数据集：先带原因回灌重生成，重生成仍不合格就丢弃并计数。
    """
    for key in ("a", "b"):
        variant = pair["variants"].get(key)
        if not isinstance(variant, dict):
            return False, "malformed"
        context = variant.get("context")
        if not (isinstance(context, list) and context and all(text(item) for item in context)):
            return False, "malformed"
        if not text(variant.get("target")) or not text(variant.get("policy")):
            return False, "malformed"
    if not text(pair.get("key_fact")):
        return False, "missing_key_fact"
    quality = prompts.pair_quality(
        {"target": pair["variants"]["a"]["target"],
         "surface": pair["variants"]["a"].get("surface"),
         "context": pair["variants"]["a"]["context"],
         "expected_status": pair["variants"]["a"].get("expected_status")},
        {"target": pair["variants"]["b"]["target"],
         "surface": pair["variants"]["b"].get("surface"),
         "context": pair["variants"]["b"]["context"],
         "expected_status": pair["variants"]["b"].get("expected_status")},
        threshold=threshold)
    for flag in ("status_conflict", "shortcut_risk", "weak_pair", "structure_mismatch"):
        if flag in quality["quality_flags"]:
            return False, flag
    return True, None


def produce_family_batch(args, family_item, batch_index, take, pair_ids, case_ids, client,
                         issue_labels, criteria, family_materials, diagnostics=None):
    """Produce one batch of accepted pairs with bounded regeneration.

    Returns (cases, questions, qa_rows, notes, stats). Raises on network/parse failure
    (the batch then stays unwritten and is retried on the next run).
    """
    pending = list(range(take))
    accepted = []
    dropped = []
    last_reasons = {}
    attempts = 0
    regenerated = 0
    feedback = None
    while pending and attempts < args.pair_attempts:
        attempts += 1
        if attempts > 1:
            regenerated += len(pending)
        pairs, _result = produce_batch(args, family_item, batch_index, len(pending), client,
                                       diagnostics, feedback=feedback)
        next_pending = []
        feedback = []
        for position, slot in enumerate(pending):
            if position >= len(pairs):
                reason = "missing_pair"
                pair = None
            else:
                pair = pairs[position]
                ok, reason = evaluate_pair(pair, family_item["family"],
                                           args.similarity_threshold)
                if ok and pair_material_key(pair) in family_materials:
                    reason = "duplicate"
            if reason is None:
                accepted.append((slot, pair))
                family_materials.add(pair_material_key(pair))
            elif reason == "duplicate":
                # 重复对直接丢弃并计数，不浪费调用去重生成（见 pipeline/README.md）。
                dropped.append({"slot": slot, "reason": reason})
            else:
                last_reasons[slot] = reason
                feedback.append((len(next_pending), reason))
                next_pending.append(slot)
        pending = next_pending
    for slot in pending:
        dropped.append({"slot": slot, "reason": last_reasons.get(slot, "unknown")})
    accepted.sort(key=lambda item: item[0])
    payloads = [pair for _slot, pair in accepted]
    accepted_pair_ids = [pair_ids[slot] for slot, _pair in accepted]
    accepted_case_ids = [case_id for slot, _pair in accepted
                         for case_id in (case_ids[2 * slot], case_ids[2 * slot + 1])]
    cases, questions, notes = build_pair_cases(
        family_item, payloads, accepted_pair_ids, accepted_case_ids, args.seed, args.model,
        args.generator, args.lineage, issue_labels, args.with_score, criteria)
    qa_rows = []
    for offset, (_slot, payload) in enumerate(accepted):
        members = {case["variant"]: case for case in cases
                   if case["pair_id"] == accepted_pair_ids[offset]}
        expected = {key: payload["variants"][key].get("expected_status") for key in ("a", "b")}
        qa_rows.append(pair_qa_row(accepted_pair_ids[offset], members, expected,
                                   payload.get("key_fact"), args.similarity_threshold))
    cases, qa_rows = apply_pair_flags(cases, qa_rows)
    reasons = sorted({row["reason"] for row in dropped})
    stats = {"slots": take, "accepted": len(accepted), "dropped": dropped,
             "attempts": attempts, "regenerated_slots": regenerated,
             "drop_reasons": {reason: sum(1 for row in dropped if row["reason"] == reason)
                              for reason in reasons}}
    return cases, questions, qa_rows, notes, stats


def process_family(args, out, family_item, client, issue_labels, plan_family, call_log,
                   criteria=None):
    family_id = family_item["family"]["family_id"]
    failed = 0
    skipped = 0
    produced_cases = 0
    accepted_pairs = 0
    dropped_pairs = 0
    regenerated_slots = 0
    generation_attempts = 0
    drop_reasons = {}
    family_materials = set()
    # 已完成批次先登记材料指纹，保证跨批次去重与断点续跑一致。
    for batch_index in range(len(plan_family["batches"])):
        cases_path, _questions_path, _qa_path, marker_path = _batch_paths(out, family_id,
                                                                          batch_index)
        if marker_path.is_file() and cases_path.is_file():
            try:
                for row in read_jsonl(cases_path):
                    validate_case(row, where=str(cases_path))
                    family_materials.add(normalized_text(case_material_text(row)))
            except (ValueError, OSError):
                family_materials = set()
                break
    pair_offset = 0
    for batch_index, take in enumerate(plan_family["batches"]):
        cases_path, questions_path, qa_path, marker_path = _batch_paths(out, family_id, batch_index)
        pair_ids = plan_family["pair_ids"][pair_offset:pair_offset + take]
        case_ids = plan_family["case_ids"][2 * pair_offset:2 * (pair_offset + take)]
        pair_offset += take
        if marker_path.is_file() and cases_path.is_file() and questions_path.is_file() \
                and qa_path.is_file():
            try:
                rows = read_jsonl(cases_path)
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
                require(marker.get("slots") == take, f"{marker_path}: slot count mismatch")
                index_unique(rows, "id", where=str(cases_path))
                for row in rows:
                    validate_case(row, where=str(cases_path))
                skipped += 1
                produced_cases += len(rows)
                accepted_pairs += marker.get("accepted", len(rows) // 2)
                dropped_pairs += len(marker.get("dropped", []))
                regenerated_slots += marker.get("regenerated_slots", 0)
                generation_attempts += marker.get("attempts", 0)
                for row in marker.get("dropped", []):
                    drop_reasons[row["reason"]] = drop_reasons.get(row["reason"], 0) + 1
                continue
            except (ValueError, OSError, KeyError, json.JSONDecodeError):
                pass
        diagnostics = {}
        try:
            cases, questions, qa_rows, notes, stats = produce_family_batch(
                args, family_item, batch_index, take, pair_ids, case_ids, client, issue_labels,
                criteria, family_materials, diagnostics)
            index = index_unique(cases, "id", where=f"{family_id} batch {batch_index}")
            for case_id, row in index.items():
                validate_case(row, where=f"{cases_path}:{case_id}")
            index_unique(questions, "qid", where=f"{family_id} batch {batch_index}")
            for row in questions:
                validate_question(row, where=f"{questions_path}:{row['qid']}")
            write_jsonl_atomic(cases_path, cases)
            write_jsonl_atomic(questions_path, questions)
            write_jsonl_atomic(qa_path, qa_rows)
            write_json_atomic(marker_path, {"family_id": family_id, "batch": batch_index,
                                            "slots": take, "accepted": len(cases) // 2,
                                            "dropped": stats["dropped"],
                                            "attempts": stats["attempts"],
                                            "regenerated_slots": stats["regenerated_slots"],
                                            "completed_at": iso_now()})
            if notes:
                write_jsonl_atomic(Path(out) / "qa" / f"{family_id}.coercions.jsonl", notes)
            produced_cases += len(cases)
            accepted_pairs += len(cases) // 2
            dropped_pairs += len(stats["dropped"])
            regenerated_slots += stats["regenerated_slots"]
            generation_attempts += stats["attempts"]
            for reason, count in stats["drop_reasons"].items():
                drop_reasons[reason] = drop_reasons.get(reason, 0) + count
        except (CallFailure, ValueError, OSError) as error:
            failed += 1
            kind = error.kind if isinstance(error, CallFailure) else "invalid"
            require(kind in EXECUTION_STATUSES, f"unexpected failure kind {kind}")
            append_jsonl(Path(out) / "errors" / f"{family_id}.errors.jsonl",
                         {"ts": iso_now(), "family_id": family_id, "batch": batch_index,
                          "kind": kind, "error": str(error)[:2000], "ok": False,
                          "raw_len": diagnostics.get("raw_len"),
                          "raw_head": diagnostics.get("raw_head")})
    all_marked = all(_batch_paths(out, family_id, index)[3].is_file()
                     for index in range(len(plan_family["batches"])))
    return {"family_id": family_id, "region": family_item["region"],
            "batches": len(plan_family["batches"]), "skipped_batches": skipped,
            "failed_batches": failed, "cases": produced_cases, "slots": plan_family["pairs"],
            "accepted_pairs": accepted_pairs, "dropped_pairs": dropped_pairs,
            "drop_reasons": drop_reasons, "regenerated_slots": regenerated_slots,
            "generation_attempts": generation_attempts,
            "complete": failed == 0 and all_marked}


# ------------------------------------------------------------------ merges

def merge_family(out, family_item, plan_family):
    family_id = family_item["family"]["family_id"]
    cases_path = Path(out) / "shards" / f"{family_id}.cases.jsonl"
    questions_path = Path(out) / "shards" / f"{family_id}.questions.jsonl"
    cases, questions, qa_rows, markers = [], [], [], []
    for batch_index in range(len(plan_family["batches"])):
        batch_cases, batch_questions, batch_qa, marker_path = _batch_paths(out, family_id,
                                                                           batch_index)
        if not (batch_cases.is_file() and batch_questions.is_file() and batch_qa.is_file()
                and marker_path.is_file()):
            return None, None, None
        cases.extend(read_jsonl(batch_cases))
        questions.extend(read_jsonl(batch_questions))
        qa_rows.extend(read_jsonl(batch_qa))
        markers.append(json.loads(marker_path.read_text(encoding="utf-8")))
    # 族/分区合并文件由分片派生，--recheck 需要重建，因此原子重写（plan.json 仍锁定配置）。
    write_jsonl_atomic(cases_path, cases)
    write_jsonl_atomic(questions_path, questions)
    coverage = prompts.family_coverage([row["expected_status"][key] for row in qa_rows
                                        for key in ("a", "b")])
    flags = [flag for row in qa_rows for flag in row["quality_flags"]]
    material_groups = {}
    for case in cases:
        material_groups.setdefault(normalized_text(case_material_text(case)),
                                   []).append(case["id"])
    duplicates = [{"material_sha256": sha256_text(key), "case_ids": sorted(ids)}
                  for key, ids in sorted(material_groups.items()) if len(ids) > 1]
    drop_reasons = {}
    for marker in markers:
        for row in marker.get("dropped", []):
            drop_reasons[row["reason"]] = drop_reasons.get(row["reason"], 0) + 1
    family_qa = {"family_id": family_id, "region": family_item["region"],
                 "slots": sum(marker.get("slots", 0) for marker in markers),
                 "pairs": len(qa_rows), "cases": len(cases),
                 "dropped_pairs": sum(len(marker.get("dropped", [])) for marker in markers),
                 "drop_reasons": drop_reasons,
                 "regenerated_slots": sum(marker.get("regenerated_slots", 0)
                                          for marker in markers),
                 "generation_attempts": sum(marker.get("attempts", 0) for marker in markers),
                 "expected_status": coverage["counts"], "missing_status": coverage["missing"],
                 "complete_classes": coverage["complete"],
                 "incomplete": not coverage["complete"],
                 "quality_flags": sorted(set(flags)),
                 "shortcut_risk_pairs": sum(1 for row in qa_rows if row["shortcut_risk"]),
                 "duplicate_case_groups": duplicates,
                 "duplicate_case_cases": sum(len(group["case_ids"]) for group in duplicates),
                 "target_identical_pairs": sum(1 for row in qa_rows if row.get("target_identical")),
                 "pairs_detail": qa_rows}
    return cases, questions, family_qa


def merge_region(out, region, cases, questions):
    # 合并文件由分片派生，续跑时可能从"部分族"变成"全部族"，因此原子重写而不是拒绝覆盖。
    write_jsonl_atomic(Path(out) / f"{region}.cases.jsonl", cases)
    write_jsonl_atomic(Path(out) / f"{region}.questions.jsonl", questions)


def merge_completed(out, plan, complete_ids):
    """Merge per-family shards into family/region contract files and QA summary."""
    complete_ids = set(complete_ids)
    complete_families, region_cases, region_questions, family_qa = [], {}, {}, []
    for plan_family in plan["families"]:
        family_id = plan_family["family_id"]
        if family_id not in complete_ids:
            continue
        item = {"family": {"family_id": family_id}, "region": plan_family["region"]}
        cases, questions, qa = merge_family(out, item, plan_family)
        if cases is None:
            continue
        complete_families.append(family_id)
        family_qa.append(qa)
        region_cases.setdefault(plan_family["region"], []).extend(cases)
        region_questions.setdefault(plan_family["region"], []).extend(questions)
    for region in sorted(region_cases):
        merge_region(out, region, region_cases[region], region_questions[region])
    if family_qa:
        write_jsonl_atomic(Path(out) / "qa" / "families.jsonl",
                           [{"family_id": row["family_id"], "region": row["region"],
                             "pairs": row["pairs"], "cases": row["cases"],
                             "expected_status": row["expected_status"],
                             "missing_status": row["missing_status"],
                             "complete_classes": row["complete_classes"],
                             "incomplete": row["incomplete"],
                             "quality_flags": row["quality_flags"],
                             "shortcut_risk_pairs": row["shortcut_risk_pairs"],
                             "target_identical_pairs": row["target_identical_pairs"],
                             "duplicate_case_cases": row["duplicate_case_cases"],
                             "slots": row["slots"], "dropped_pairs": row["dropped_pairs"],
                             "drop_reasons": row["drop_reasons"],
                             "regenerated_slots": row["regenerated_slots"],
                             "generation_attempts": row["generation_attempts"]}
                            for row in family_qa])
    return complete_families, family_qa


def recheck(out, threshold):
    """离线重算质检与质量标记（不调用模型），并重建派生文件。

    用途：QA 规则修正后复算已有分片。expected_status 只存在于原有 QA 行里，不写回 case，
    教师输入仍然看不到它。
    """
    out = Path(out)
    plan_path = out / "plan.json"
    require(plan_path.is_file(), f"{out}: plan.json not found; --recheck 只用于已生成的 --out")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for plan_family in plan["families"]:
        family_id = plan_family["family_id"]
        batches = []
        for batch_index in range(len(plan_family["batches"])):
            cases_path, _questions_path, qa_path, _marker_path = _batch_paths(out, family_id,
                                                                              batch_index)
            if not cases_path.is_file():
                continue
            cases = read_jsonl(cases_path)
            old_qa = read_jsonl(qa_path) if qa_path.is_file() else []
            expected = {row["pair_id"]: row.get("expected_status", {}) for row in old_qa}
            key_facts = {row["pair_id"]: row.get("key_fact") for row in old_qa}
            batches.append((cases_path, qa_path, cases, expected, key_facts))
        if not batches:
            continue
        everything = [case for _, _, cases, _, _ in batches for case in cases]
        flagged = _duplicate_case_ids(everything)
        for cases_path, qa_path, cases, expected, key_facts in batches:
            rows = []
            for pair_id in dict.fromkeys(case["pair_id"] for case in cases):
                members = {case["variant"]: case for case in cases if case["pair_id"] == pair_id}
                rows.append(pair_qa_row(pair_id, members, expected.get(pair_id, {}),
                                        key_facts.get(pair_id), threshold))
            cases, rows = apply_pair_flags(cases, rows)
            for row in rows:
                row["duplicate_case"] = any(case_id in flagged for case_id in row["case_ids"])
            for case in cases:
                flags = case["provenance"]["quality_flag"]
                if case["id"] in flagged and "duplicate_case" not in flags:
                    flags.append("duplicate_case")
            write_jsonl_atomic(cases_path, cases)
            write_jsonl_atomic(qa_path, rows)
    return plan


# ------------------------------------------------------------------ CLI

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--families", type=Path, help="场景族清单 JSONL（--recheck 时不需要）")
    parser.add_argument("--assign", type=Path, help="splits.py 的分配表（family_id/region）")
    parser.add_argument("--region", choices=PIPELINE_REGIONS, help="无分配表时强制单一分区")
    parser.add_argument("--out", type=Path, help="新输出目录（已有 plan.json 则续跑；--recheck 必填）")
    parser.add_argument("--limit", type=int, help="本次最多生成的 case 数（按整对向上取整）")
    parser.add_argument("--family", action="append", default=[], help="只跑指定 family_id，可重复")
    parser.add_argument("--families-filter", help="逗号分隔的 family_id 列表")
    parser.add_argument("--pairs-per-batch", type=int, default=3, help="每次调用的最小对立对数量")
    parser.add_argument("--workers", "--concurrency", dest="workers", type=int, default=4,
                        help="并发上限（按族）；--concurrency 是同一参数的别名")
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--issue-keys-file", type=Path, help="本体冻结后的问题键清单")
    parser.add_argument("--with-score", action="store_true", help="额外派生 severity 数值题")
    parser.add_argument("--similarity-threshold", type=float,
                        default=prompts.DEFAULT_SIMILARITY_THRESHOLD)
    parser.add_argument("--source", default="luna", help="生成模型来源名")
    parser.add_argument("--model", help="覆盖模型 id")
    parser.add_argument("--base-url", help="覆盖 baseURL")
    parser.add_argument("--key-env", help="覆盖密钥环境变量名")
    parser.add_argument("--key-file", type=Path, help="密钥文件（DSH credentials.yaml 或纯文本）")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--price-in", type=float, help="每百万输入 token 价格（用于成本日志）")
    parser.add_argument("--price-out", type=float, help="每百万输出 token 价格")
    parser.add_argument("--user-agent", help="覆盖 HTTP User-Agent（默认产品名，绕开 urllib 被封）")
    parser.add_argument("--retry-invalid", action=argparse.BooleanOptionalAction, default=True,
                        help="把「content 为空/JSON 不可解析」当作可重试（生成侧默认开；--no-retry-invalid 关）")
    parser.add_argument("--pair-attempts", type=int, default=3,
                        help="每组对的生成尝试上限：不合格的对带原因回灌重生成，仍不合格则丢弃并计数")
    parser.add_argument("--response-format", choices=("none", "json_object"), default="none",
                        help="chat 协议可选的结构化输出；未核实前默认不用")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="真实联网调用（默认离线）")
    mode.add_argument("--fixture", action="store_true", help="离线确定性合成数据")
    mode.add_argument("--dry-run", action="store_true", help="只写请求计划，不联网")
    parser.add_argument("--check-ontology", action="store_true",
                        help="生成侧本体校验：打印 issue 键对照与判据枚举一致性后退出")
    parser.add_argument("--recheck", action="store_true",
                        help="离线重算质检与质量标记（不调用模型），用于修正 QA 规则后复算已有分片")
    return parser


def main(argv=None, client_factory=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.check_ontology:
        try:
            report = prompts.issue_alignment_report(args.issue_keys_file)
            _payload, source = prompts.load_ontology(args.issue_keys_file)
            criteria = prompts.load_criteria(args.issue_keys_file)
            expected = {"status": list(prompts.STATUSES), "polarity": list(prompts.POLARITIES),
                        "evidence": list(prompts.EVIDENCE), "actions": list(prompts.ACTIONS)}
            enum_ok = all(sorted(criteria[section]) == sorted(keys)
                          for section, keys in expected.items())
            report.update({"criteria_sections": sorted(criteria), "enums_consistent": enum_ok,
                           "enum_diff": {section: {"ontology": sorted(criteria[section]),
                                                   "pipeline": sorted(keys)}
                                         for section, keys in expected.items()
                                         if sorted(criteria[section]) != sorted(keys)}})
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if (report["aligned"] and enum_ok) else 1
        except (OSError, ValueError, KeyError) as error:
            parser.exit(2, f"generate: {error}\n")
    if args.recheck:
        try:
            require(args.out is not None, "--recheck 需要 --out")
            require(not (args.live or args.fixture or args.dry_run),
                    "--recheck 不能与 --live/--fixture/--dry-run 同时使用")
            plan = recheck(args.out, args.similarity_threshold)
            complete, family_qa = merge_completed(
                args.out, plan, [item["family_id"] for item in plan["families"]])
            coverage = prompts.family_coverage(
                [status for row in family_qa for status in row["expected_status"]
                 for _ in range(row["expected_status"][status])])
            run_path = Path(args.out) / "run.json"
            if run_path.is_file():
                run = json.loads(run_path.read_text(encoding="utf-8"))
                run.pop("duplicate_target_cases", None)
                run.update({
                    "state": ("finished" if len(complete) == len(plan["families"])
                              else run.get("state", "partial")),
                    "rechecked_at": iso_now(), "recheck_threshold": args.similarity_threshold,
                    "complete_families": complete,
                    "duplicate_case_cases": sum(row["duplicate_case_cases"] for row in family_qa),
                    "target_identical_pairs": sum(row["target_identical_pairs"]
                                                  for row in family_qa),
                    "quality_flags": sorted({flag for row in family_qa
                                             for flag in row["quality_flags"]}),
                    "missing_status": coverage["missing"],
                    "class_coverage_complete": coverage["complete"]})
                for row in run.get("families", []):
                    if row.get("family_id") in set(complete):
                        row["complete"] = True
                        row["failed_batches"] = 0
                write_json_atomic(run_path, run)
            print(json.dumps({"out": str(args.out), "mode": "recheck",
                              "rechecked_families": len(complete),
                              "duplicate_case_cases": sum(row["duplicate_case_cases"]
                                                          for row in family_qa),
                              "quality_flags": sorted({flag for row in family_qa
                                                       for flag in row["quality_flags"]}),
                              "target_identical_pairs": sum(row["target_identical_pairs"]
                                                            for row in family_qa),
                              "missing_status": coverage["missing"]}, ensure_ascii=False))
            return 0
        except (OSError, ValueError, KeyError) as error:
            parser.exit(2, f"generate: {error}\n")
    try:
        require(args.families is not None, "--families is required (除 --check-ontology/--recheck 外)")
        require(args.out is not None, "--out is required")
        require(args.pairs_per_batch > 0, "--pairs-per-batch must be positive")
        require(args.pair_attempts >= 1, "--pair-attempts must be >= 1")
        require(args.workers > 0, "--workers must be positive")
        require(0 < args.similarity_threshold <= 1, "--similarity-threshold must be in (0, 1]")
        require(args.assign is not None or args.region is not None,
                "pass --assign (splits.py 分配表) or --region (单一分区)")
        issue_labels = prompts.load_issue_labels(args.issue_keys_file)
        criteria = prompts.load_criteria(args.issue_keys_file)
        families = load_families(args.families)
        assignment = load_assignment(args.assign) if args.assign else None
        filters = csv_list(args.families_filter) + list(args.family)
        selected = select_families(families, filters, assignment, args.region)
        plan = build_plan(selected, args.limit, args.pairs_per_batch, args.seed,
                          config_snapshot(args, args.families, args.assign, issue_labels, selected,
                                          criteria))
        out, fresh = prepare_out(args.out, plan)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"generate: {error}\n")

    if args.live:
        args.generator = args.source
        args.lineage = SOURCES.get(args.source, {}).get("lineage", args.source)
        args.model = args.model or SOURCES.get(args.source, {}).get("model", args.source)
    elif args.fixture:
        args.generator = "fixture"
        args.lineage = fixtures.FIXTURE_LINEAGE
        args.model = args.model or fixtures.FIXTURE_MODEL
    else:
        args.generator = None
        args.lineage = None
        args.model = args.model or SOURCES["luna"]["model"]

    client = None
    call_log = CallLog(out / "calls.jsonl")
    if args.live:
        try:
            factory = client_factory or (lambda parsed: build_client(
                parsed.source, base_url=parsed.base_url, model=parsed.model,
                key_env=parsed.key_env, key_file=parsed.key_file, timeout=parsed.timeout,
                max_attempts=parsed.max_attempts, log=call_log, max_tokens=parsed.max_tokens,
                price_in=parsed.price_in, price_out=parsed.price_out,
                user_agent=parsed.user_agent, retry_invalid=parsed.retry_invalid,
                response_format=(None if parsed.response_format == "none"
                                 else parsed.response_format)))
            client = factory(args)
            args.lineage = getattr(client, "lineage", args.lineage)
            args.model = getattr(client, "model", args.model)
        except (OSError, ValueError) as error:
            parser.exit(2, f"generate: {error}\n")

    plan_by_family = {item["family_id"]: item for item in plan["families"]}
    results = []
    if args.dry_run or not (args.live or args.fixture):
        for item in selected:
            plan_family = plan_by_family.get(item["family"]["family_id"])
            if plan_family is None:
                results.append({"family_id": item["family"]["family_id"],
                                "region": item["region"], "state": "not_planned"})
                continue
            for batch_index, take in enumerate(plan_family["batches"]):
                messages = [{"role": "user",
                             "content": prompts.generation_prompt(item["family"], take,
                                                                  args.seed + batch_index)}]
                body = (client.payload(messages, max_tokens=args.max_tokens) if client
                        else {"model": args.model, "messages": messages,
                              "max_tokens": args.max_tokens})
                write_jsonl_new(Path(out) / "requests"
                                / f"{item['family']['family_id']}.batch-{batch_index:03d}.request.jsonl",
                                [{"family_id": item["family"]["family_id"],
                                  "batch": batch_index, "pairs": take, "payload": body}])
            results.append({"family_id": item["family"]["family_id"], "region": item["region"],
                            "planned_pairs": plan_family["pairs"], "planned_cases":
                            plan_family["cases"], "state": "planned"})
    else:
        work = [(item, plan_by_family[item["family"]["family_id"]])
                for item in selected if item["family"]["family_id"] in plan_by_family]
        outcomes = run_ordered(
            work, lambda pair, index: process_family(args, out, pair[0], client, issue_labels,
                                                     pair[1], call_log, criteria),
            workers=args.workers)
        for (item, _), outcome in zip(work, outcomes):
            if isinstance(outcome, Exception):
                results.append({"family_id": item["family"]["family_id"],
                                "region": item["region"], "state": "error",
                                "error": str(outcome)[:500]})
            else:
                results.append(outcome)

    complete_ids = [row["family_id"] for row in results if row.get("complete")]
    complete_families, family_qa = merge_completed(out, plan, complete_ids)

    failed_families = [row for row in results
                       if row.get("failed_batches") or row.get("state") == "error"]
    coverage = prompts.family_coverage([status for row in family_qa
                                        for status in row["expected_status"]
                                        for _ in range(row["expected_status"][status])])
    run = {"tool": TOOL, "state": ("planned" if not (args.live or args.fixture)
                                   else ("finished" if not failed_families else "partial")),
           "mode": ("live" if args.live else "fixture" if args.fixture else "dry-run"),
           "out": str(out), "fresh": fresh, "seed": args.seed, "model": args.model,
           "generator": args.generator, "generator_lineage": args.lineage,
           "gen_version": prompts.GEN_VERSION, "question_template": prompts.Q_TEMPLATE_VERSION,
           "ontology": {"source": str(args.issue_keys_file or prompts.ONTOLOGY_DEFAULT),
                        "issues": len(issue_labels), "issue_keys": sorted(issue_labels),
                        "criteria_sections": sorted(criteria)},
           "planned_cases": plan["total_cases"], "planned_pairs": plan["total_pairs"],
           "complete_families": complete_families,
           "duplicate_case_cases": sum(row["duplicate_case_cases"] for row in family_qa),
           "pair_slots": sum(row["slots"] for row in family_qa),
           "accepted_pairs": sum(row["pairs"] for row in family_qa),
           "dropped_pairs": sum(row["dropped_pairs"] for row in family_qa),
           "drop_reasons": {reason: sum(row["drop_reasons"].get(reason, 0) for row in family_qa)
                            for reason in sorted({key for row in family_qa
                                                  for key in row["drop_reasons"]})},
           "regenerated_slots": sum(row["regenerated_slots"] for row in family_qa),
           "generation_attempts": sum(row["generation_attempts"] for row in family_qa),
           "response_format": args.response_format, "pair_attempts": args.pair_attempts,
           "missing_status": coverage["missing"], "class_coverage_complete": coverage["complete"],
           "families": results, "calls": call_log.summary(), "created_at": iso_now()}
    write_json_atomic(Path(out) / "run.json", run)
    print(json.dumps({"out": str(out), "state": run["state"], "mode": run["mode"],
                      "planned_cases": run["planned_cases"],
                      "complete_families": len(complete_families),
                      "planned_families": len(plan["families"]),
                      "calls": run["calls"], "missing_status": coverage["missing"],
                      "duplicate_case_cases": run["duplicate_case_cases"],
                      "accepted_pairs": run["accepted_pairs"], "dropped_pairs": run["dropped_pairs"],
                      "drop_reasons": run["drop_reasons"],
                      "regenerated_slots": run["regenerated_slots"]},
                     ensure_ascii=False))
    return 1 if failed_families else 0


if __name__ == "__main__":
    raise SystemExit(main())
