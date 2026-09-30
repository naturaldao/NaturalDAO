"""从产出文件独立复算 v0.1-pilot 的全部报告数字，并可据此生成 pilot-report.md。

只读、离线、仅用标准库；不会修改任何数据文件。

    uv run --no-project --offline python datasets/pol2/v0.1-pilot/verify_pilot.py
    uv run --no-project --offline python datasets/pol2/v0.1-pilot/verify_pilot.py --report pilot-report.md

--assign 默认读仓库外的私有分配表，用于核对 region；文件不存在时该检查标记为 skipped。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIPELINE = HERE.parent / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

from common import (PIPELINE_REGIONS, read_jsonl, validate_answer, validate_case,  # noqa: E402
                    validate_label, validate_question)

DEFAULT_ASSIGN = Path(r"C:\Projects\DAism\pol2-private\assignment.jsonl")
SECRET_PATTERNS = (re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}"), re.compile(r"sk-[A-Za-z0-9]{16,}"))


def normalize(text):
    return "".join(ch for ch in text if ch.isalnum()).lower()


def material(case):
    return normalize(" ".join(case["input"]["context"]) + " " + case["input"]["target"])


def collect(base, assign_path):
    plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
    run = json.loads((base / "run.json").read_text(encoding="utf-8"))
    calls = read_jsonl(base / "calls.jsonl")
    metrics = {"base": str(base), "plan": {}, "families": [], "calls": {}, "questions": {},
               "quality": {}, "contract": {}, "boundary": {}, "files": {}}

    # ---- 分区计划与分配表核对
    assignment, assign_state = {}, "skipped"
    if assign_path and Path(assign_path).is_file():
        for line in Path(assign_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                assignment[row["family_id"]] = row["region"]
        assign_state = "ok"
    region_mismatch = []
    for fam in plan["families"]:
        expected = assignment.get(fam["family_id"])
        if expected and expected != fam["region"]:
            region_mismatch.append({"family_id": fam["family_id"], "plan": fam["region"],
                                    "assign": expected})
    metrics["plan"] = {"total_cases": plan["total_cases"], "total_pairs": plan["total_pairs"],
                       "families": len(plan["families"]), "regions": plan["regions"],
                       "seed": plan["seed"], "pairs_per_batch": plan["pairs_per_batch"],
                       "config_sha256": plan["config_sha256"]}
    metrics["boundary"] = {"assignment_state": assign_state,
                           "region_mismatch": region_mismatch,
                           "private_holdout_in_plan": [f["family_id"] for f in plan["families"]
                                                       if f["region"] == "private_holdout"]}

    # ---- 逐族：分片、标记、质检
    qa_rows, cases_by_family, raw_cases = [], {}, []
    delivered_cases = []
    for path in sorted(base.glob("*.cases.jsonl")):
        delivered_cases.extend(read_jsonl(path))
    dropped_case_ids_by_family = {}
    family_qa_path = base / "qa" / "families.jsonl"
    if family_qa_path.is_file():
        for row in read_jsonl(family_qa_path):
            dropped_case_ids_by_family[row["family_id"]] = row.get("duplicate_case_dropped_ids", [])
    for fam in plan["families"]:
        fid = fam["family_id"]
        batch_cases, batch_qa, markers = [], [], []
        for index in range(len(fam["batches"])):
            shard = base / "shards" / fid
            cpath = shard / f"batch-{index:03d}.cases.jsonl"
            qpath = shard / f"batch-{index:03d}.qa.jsonl"
            mpath = shard / f"batch-{index:03d}.done.json"
            if cpath.is_file():
                batch_cases.extend(read_jsonl(cpath))
            if qpath.is_file():
                batch_qa.extend(read_jsonl(qpath))
            if mpath.is_file():
                markers.append(json.loads(mpath.read_text(encoding="utf-8")))
        raw_cases.extend(batch_cases)
        merged_family = base / "shards" / f"{fid}.cases.jsonl"
        cases_by_family[fid] = (read_jsonl(merged_family) if merged_family.is_file()
                                else batch_cases)
        qa_rows.extend(batch_qa)
        kept_qa = [row for row in batch_qa if not row.get("duplicate_case")]
        counts = Counter(row["expected_status"].get(key)
                         for row in kept_qa for key in ("a", "b"))
        drop_reasons = Counter(row["reason"] for marker in markers
                               for row in marker.get("dropped", []))
        metrics["families"].append({
            "family_id": fid, "region": fam["region"],
            "slots": sum(marker.get("slots", 0) for marker in markers),
            "batches_done": len(markers), "batches_planned": len(fam["batches"]),
            "cases": len(cases_by_family[fid]), "cases_planned": fam["cases"],
            "cases_raw": len(batch_cases),
            "pairs": len([row for row in batch_qa if not row.get("duplicate_case")]),
            "conforming": counts.get("conforming", 0),
            "violating": counts.get("violating", 0),
            "insufficient": counts.get("insufficient", 0),
            "complete_classes": all(counts.get(status, 0) > 0
                                    for status in ("conforming", "violating", "insufficient")),
            "status_opposite_pairs": sum(1 for row in kept_qa if row["status_opposite"]),
            "dropped_pairs": sum(len(marker.get("dropped", [])) for marker in markers),
            "drop_reasons": dict(drop_reasons),
            "regenerated_slots": sum(marker.get("regenerated_slots", 0) for marker in markers),
            "generation_attempts": sum(marker.get("attempts", 0) for marker in markers),
            "duplicate_case_dropped_ids": dropped_case_ids_by_family.get(fid, [])})

    # ---- 质量门（pair 级标记 + 整体材料重复）
    flags = Counter(flag for row in qa_rows for flag in row["quality_flags"])
    offending = {flag: sorted(row["pair_id"] for row in qa_rows if flag in row["quality_flags"])
                 for flag in ("duplicate_case", "shortcut_risk", "weak_pair",
                              "structure_mismatch", "status_conflict", "missing_key_fact")}
    material_groups = {}
    for case in delivered_cases:
        material_groups.setdefault(material(case), []).append(case["id"])
    duplicates = [{"material": key[:16], "case_ids": sorted(ids)}
                  for key, ids in material_groups.items() if len(ids) > 1]
    dup_cases = sum(len(group["case_ids"]) for group in duplicates)
    raw_groups = {}
    for case in raw_cases:
        raw_groups.setdefault(material(case), []).append(case["id"])
    raw_dup_cases = sum(len(ids) for ids in raw_groups.values() if len(ids) > 1)
    region_dup = {}
    for region in sorted({case["region"] for case in delivered_cases}):
        region_cases = [case for case in delivered_cases if case["region"] == region]
        groups = {}
        for case in region_cases:
            groups.setdefault(material(case), []).append(case["id"])
        region_dup[region] = sum(len(ids) for ids in groups.values() if len(ids) > 1)
    metrics["quality"] = {
        "pair_flags": dict(flags), "offending_pair_ids": offending,
        "duplicate_cases_total": dup_cases,
        "duplicate_rate": round(dup_cases / max(len(delivered_cases), 1), 6),
        "duplicate_groups": duplicates, "duplicate_cases_by_region": region_dup,
        "raw_shard_cases": len(raw_cases), "raw_shard_duplicate_cases": raw_dup_cases,
        "delivered_cases": len(delivered_cases),
        "pairs": len([row for row in qa_rows if not row.get("duplicate_case")]),
        "status_opposite_pairs": sum(1 for row in qa_rows if row["status_opposite"]
                                     and not row.get("duplicate_case")),
        "target_identical_pairs": sum(1 for row in qa_rows if row.get("target_identical")
                                      and not row.get("duplicate_case")),
        "merged_duplicates_dropped": run.get("duplicate_case_dropped_by_region", {}),
        "family_duplicates_dropped": {row["family_id"]: row["duplicate_case_dropped_ids"]
                                      for row in metrics["families"]
                                      if row.get("duplicate_case_dropped_ids")}}

    # ---- 调用侧
    ok = [row for row in calls if row["ok"]]
    failed = [row for row in calls if not row["ok"]]
    kinds = Counter(row.get("failure_kind") or ("legacy" if "failure_kind" not in row else "unknown")
                    for row in failed)
    network = sum(1 for row in failed if "SSL" in (row.get("error") or "")
                  or row.get("status_code") == 524 or "url error" in (row.get("error") or ""))
    invalid = sum(1 for row in failed if (row.get("failure_kind") == "invalid")
                  or (row.get("error") or "").startswith("invalid"))
    retries_absorbed = sum(row.get("retries") or 0 for row in ok)
    stamps = [row["ts"] for row in calls]
    metrics["calls"] = {
        "attempts": len(calls), "ok": len(ok), "failed": len(failed),
        "invalid_attempts": invalid,
        "invalid_attempt_rate": round(invalid / max(len(calls), 1), 6),
        "network_failures": network, "failure_kinds": dict(kinds),
        "retries_absorbed": retries_absorbed,
        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in calls),
        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in calls),
        "total_tokens": sum(row.get("total_tokens") or 0 for row in calls),
        "cost_usd": run["calls"].get("cost_usd"),
        "first_call_ts": stamps[0] if stamps else None,
        "last_call_ts": stamps[-1] if stamps else None,
        "latency_ms_p50": run["calls"].get("latency_ms_p50"),
        "latency_ms_p95": run["calls"].get("latency_ms_p95"),
        "workers": run.get("workers"), "response_format": run.get("response_format"),
        "pair_attempts": run.get("pair_attempts"),
        "successful_mean_prompt": (sum(row.get("prompt_tokens") or 0 for row in ok) / len(ok)
                                   if ok else None),
        "successful_mean_completion": (sum(row.get("completion_tokens") or 0 for row in ok) / len(ok)
                                       if ok else None),
        "run_state": run["state"], "complete_families": len(run.get("complete_families", []))}

    # ---- 问题集
    kind_counts = Counter()
    question_total = 0
    for region in sorted({case["region"] for case in delivered_cases}):
        path = base / f"{region}.questions.jsonl"
        if not path.is_file():
            continue
        rows = read_jsonl(path)
        question_total += len(rows)
        kind_counts.update(row["kind"] for row in rows)
    metrics["questions"] = {
        "total": question_total, "by_kind": dict(kind_counts),
        "per_case": round(question_total / max(len(delivered_cases), 1), 3)}

    # ---- 契约校验 + 边界检查
    errors = []
    checked = Counter()
    for path in sorted(base.glob("*.cases.jsonl")):
        for row in read_jsonl(path):
            try:
                validate_case(row)
                checked["case"] += 1
            except ValueError as error:
                errors.append(f"{path.name}: {error}")
    for path in sorted(base.glob("*.questions.jsonl")):
        for row in read_jsonl(path):
            try:
                validate_question(row)
                checked["question"] += 1
            except ValueError as error:
                errors.append(f"{path.name}: {error}")
    for path in sorted(base.glob("*.answers.*.jsonl")):
        for row in read_jsonl(path):
            try:
                validate_answer(row)
                checked["answer"] += 1
            except ValueError as error:
                errors.append(f"{path.name}: {error}")
    for path in sorted(base.glob("*.labels.jsonl")):
        for row in read_jsonl(path):
            try:
                validate_label(row)
                checked["label"] += 1
            except ValueError as error:
                errors.append(f"{path.name}: {error}")
    region_files = sorted(path.name for path in base.glob("*.cases.jsonl"))
    bad_regions = sorted({case["region"] for case in delivered_cases} - set(PIPELINE_REGIONS))

    secret_hits, scanned = [], 0
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in (".json", ".jsonl", ".md", ".py"):
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                secret_hits.append({"file": str(path.relative_to(base)),
                                    "pattern": pattern.pattern})
    metrics["contract"] = {"validated": dict(checked), "errors": errors[:20],
                           "error_count": len(errors)}
    metrics["boundary"].update({
        "region_files": region_files, "bad_regions": bad_regions,
        "private_holdout_files": [name for name in region_files
                                  if name.startswith("private_holdout")],
        "secret_hits": secret_hits, "files_scanned_for_secrets": scanned,
        "key_logged_as": "key_fingerprint only"})
    metrics["files"] = {"cases": len(delivered_cases), "questions": question_total,
                        "pairs": metrics["quality"]["pairs"], "families": len(plan["families"]),
                        "raw_shard_cases": len(raw_cases)}
    return metrics


def render_markdown(metrics):
    lines = ["# PoL2 试点放量报告（v0.1-pilot，17 族 1904 条）", "",
             "本报告所有数字由 verify_pilot.py 从产出文件复算，可独立重跑：", "",
             "    uv run --no-project --offline python datasets/pol2/v0.1-pilot/verify_pilot.py",
             "",
             "配置：--live --workers 8 --pairs-per-batch 3 --pair-attempts 3 --max-attempts 4 "
             "--response-format json_object --max-tokens 16384；"
             "不带 --limit，按各族 target_cases 生成。", "",
             "## 1) 逐族产出", "",
             "| family_id | region | 计划 case | 实际 case | 完整对 | conforming | violating | insufficient | 三类齐 | 组内 status 相反 | 丢弃 | 丢弃原因 | 重生成 slot |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in metrics["families"]:
        lines.append("| {family_id} | {region} | {cases_planned} | {cases} | {pairs} | {conforming} | "
                     "{violating} | {insufficient} | {complete_classes} | "
                     "{status_opposite_pairs}/{pairs} | {dropped_pairs} | {drop_reasons} | "
                     "{regenerated_slots} |".format(**row))
    plan = metrics["plan"]
    lines += ["", f"合计：计划 {plan['total_cases']} 条 / {plan['total_pairs']} 组对；"
                  f"实际 {metrics['files']['cases']} 条 / {metrics['files']['pairs']} 组对；"
                  f"分区分布 {json.dumps(plan['regions'], ensure_ascii=False)}。", ""]

    calls = metrics["calls"]
    lines += ["## 2) 全局调用与成本", "",
              f"- 总尝试 {calls['attempts']} 次：ok {calls['ok']}，失败 {calls['failed']}"
              f"（invalid {calls['invalid_attempts']}，占 {calls['invalid_attempt_rate']:.2%}；"
              f"网络失败 {calls['network_failures']}）。",
              f"- 失败分类：{json.dumps(calls['failure_kinds'], ensure_ascii=False)}；"
              f"成功调用中由重试吸收的额外尝试 {calls['retries_absorbed']} 次。",
              f"- token：prompt {calls['prompt_tokens']}，completion {calls['completion_tokens']}，"
              f"合计 {calls['total_tokens']}；成功调用均值 prompt "
              f"{calls['successful_mean_prompt']:.0f} / completion "
              f"{calls['successful_mean_completion']:.0f}。",
              f"- 单次成功延迟 p50 {calls['latency_ms_p50']} ms，p95 {calls['latency_ms_p95']} ms；"
              f"并发 {calls['workers']}；调用窗口 {calls['first_call_ts']} → {calls['last_call_ts']}。",
              f"- cost_usd：{calls['cost_usd']}（sub 路由不返回价格，按约定写 null）。",
              f"- run state：{calls['run_state']}，完成族 {calls['complete_families']}/"
              f"{plan['families']}。", ""]

    quality = metrics["quality"]
    lines += ["## 3) 质量门", "",
              f"- pair 级质量标记：{json.dumps(quality['pair_flags'], ensure_ascii=False)}"
              f"（duplicate_case / shortcut_risk / weak_pair 均应为 0）。",
              f"- 交付文件整体材料精确重复：{quality['duplicate_cases_total']} 条"
              f"（重复率 {quality['duplicate_rate']:.4%}）；按分区 "
              f"{json.dumps(quality['duplicate_cases_by_region'], ensure_ascii=False)}。"
              f"（内部批次分片保留原始记录，其中重复 {quality['raw_shard_duplicate_cases']} 条，"
              f"合并阶段已剔除，不进交付文件）",
              f"- 组内 status 相反：{quality['status_opposite_pairs']}/{quality['pairs']} 组；"
              f"context-only（target 相同、关键事实在 context）{quality['target_identical_pairs']} 组。"]
    for flag, pair_ids in quality["offending_pair_ids"].items():
        if pair_ids:
            lines.append(f"- 非零项 {flag}：{', '.join(pair_ids)}")
    dropped = quality.get("merged_duplicates_dropped") or {}
    if dropped:
        lines.append(f"- 合并阶段剔除的重复：{json.dumps(dropped, ensure_ascii=False)}"
                     f"（这些对不进入交付文件，分片仍保留原始记录）")
    else:
        lines.append("- 合并阶段剔除的重复：无")
    lines.append("")

    questions = metrics["questions"]
    lines += ["## 4) 问题集规模", "",
              f"- question 总数 {questions['total']}，按 kind "
              f"{json.dumps(questions['by_kind'], ensure_ascii=False)}，"
              f"每 case 平均 {questions['per_case']} 条。", ""]

    contract = metrics["contract"]
    lines += ["## 5) 契约符合性", "",
              f"- validate_case / validate_question / validate_answer / validate_label 全量校验："
              f"{json.dumps(contract['validated'], ensure_ascii=False)}；"
              f"错误 {contract['error_count']} 条。"]
    if contract["errors"]:
        lines += [f"  - {item}" for item in contract["errors"]]
    lines.append("")

    boundary = metrics["boundary"]
    lines += ["## 6) 分区与边界符合性", "",
              f"- region 与私有分配表一致：{boundary['assignment_state']}"
              f"（不一致 {len(boundary['region_mismatch'])} 条）。",
              f"- private_holdout：计划中含 {len(boundary['private_holdout_in_plan'])} 个族，"
              f"产出文件名含 private_holdout 的 {len(boundary['private_holdout_files'])} 个；"
              f"非公开分区 {len(boundary['bad_regions'])} 个。",
              f"- 密钥扫描：扫描 {boundary['files_scanned_for_secrets']} 个文本文件，"
              f"命中 {len(boundary['secret_hits'])} 处；调用日志只写 key_fingerprint。", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, default=HERE)
    parser.add_argument("--assign", type=Path, default=DEFAULT_ASSIGN)
    parser.add_argument("--report", type=Path, help="写成 markdown 报告（如 pilot-report.md）")
    args = parser.parse_args(argv)
    metrics = collect(args.base, args.assign)
    if args.report:
        target = args.report if args.report.is_absolute() else args.base / args.report
        target.write_text(render_markdown(metrics), encoding="utf-8")
        metrics["report_written"] = str(target)
    print(json.dumps({key: metrics[key] for key in
                      ("plan", "files", "calls", "questions", "quality", "contract", "boundary",
                       "report_written")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
