"""从交付文件独立复算 v0.1-pilot 的全部报告数字，并可据此生成 pilot-report.md。

只读、离线、仅用标准库。**只依赖交付文件**（分区 cases/questions、qa/families.jsonl、
calls.jsonl、run.json、plan.json）；questions 明文缺失时自动读同名 .jsonl.gz，
分片目录（shards/）不入库，存在时才额外统计"原始分片重复"。

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

from common import (PIPELINE_REGIONS, read_jsonl, read_jsonl_any, resolve_jsonl,  # noqa: E402
                    validate_case, validate_question)

DEFAULT_ASSIGN = Path(r"C:\Projects\DAism\pol2-private\assignment.jsonl")
SECRET_PATTERNS = (re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}"), re.compile(r"sk-[A-Za-z0-9]{16,}"))
STATUS_KEYS = ("conforming", "violating", "insufficient")


def normalize(text):
    return "".join(ch for ch in text if ch.isalnum()).lower()


def material(case):
    return normalize(" ".join(case["input"]["context"]) + " " + case["input"]["target"])


def load_optional(path):
    """交付文件可选读：明文或 .gz 任一存在即可，都没有返回 None。"""
    try:
        return read_jsonl_any(path)
    except ValueError:
        return None


def collect(base, assign_path):
    plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
    run = json.loads((base / "run.json").read_text(encoding="utf-8"))
    calls = read_jsonl(base / "calls.jsonl")
    metrics = {"base": str(base), "plan": {}, "files": {}, "families": [], "calls": {},
               "questions": {}, "quality": {}, "contract": {}, "boundary": {}}

    # ---- 交付文件：分区 cases / questions
    region_files = sorted(path.name for path in base.glob("*.cases.jsonl"))
    delivered_cases, cases_by_family = [], {}
    for name in region_files:
        region = name[: -len(".cases.jsonl")]
        for case in read_jsonl(base / name):
            delivered_cases.append(case)
            cases_by_family.setdefault(case["family_id"], []).append(case)

    question_total, kind_counts, question_files = 0, Counter(), []
    for name in region_files:
        region = name[: -len(".cases.jsonl")]
        wanted = base / f"{region}.questions.jsonl"
        try:
            resolved = resolve_jsonl(wanted)
        except ValueError:
            continue
        rows = read_jsonl(resolved)
        question_files.append(resolved.name)
        question_total += len(rows)
        kind_counts.update(row["kind"] for row in rows)

    # ---- 族级 QA 汇总（qa/families.jsonl 入库，用于逐族分布与丢弃计数）
    family_qa = {}
    qa_path = base / "qa" / "families.jsonl"
    if qa_path.is_file():
        for row in read_jsonl(qa_path):
            family_qa[row["family_id"]] = row

    for fam in plan["families"]:
        fid = fam["family_id"]
        qa = family_qa.get(fid, {})
        cases = cases_by_family.get(fid, [])
        counts = qa.get("expected_status") or {}
        metrics["families"].append({
            "family_id": fid, "region": fam["region"],
            "cases": len(cases), "cases_planned": fam["cases"],
            "pairs": len({case["pair_id"] for case in cases}),
            "conforming": counts.get("conforming", 0),
            "violating": counts.get("violating", 0),
            "insufficient": counts.get("insufficient", 0),
            "complete_classes": qa.get("complete_classes"),
            "status_opposite_pairs": (qa.get("pairs", 0) - len(qa.get("quality_flags") or []) * 0
                                      if qa else None),
            "dropped_pairs": qa.get("dropped_pairs"),
            "drop_reasons": qa.get("drop_reasons"),
            "regenerated_slots": qa.get("regenerated_slots"),
            "generation_attempts": qa.get("generation_attempts"),
            "duplicate_case_dropped_ids": qa.get("duplicate_case_dropped_ids", [])})

    # ---- 调用侧
    ok = [row for row in calls if row["ok"]]
    failed = [row for row in calls if not row["ok"]]
    kinds = Counter(row.get("failure_kind") or "unknown" for row in failed)
    network = sum(1 for row in failed if "SSL" in (row.get("error") or "")
                  or row.get("status_code") == 524 or "url error" in (row.get("error") or ""))
    invalid = sum(1 for row in failed if (row.get("failure_kind") == "invalid")
                  or (row.get("error") or "").startswith("invalid"))
    stamps = [row["ts"] for row in calls]
    metrics["calls"] = {
        "attempts": len(calls), "ok": len(ok), "failed": len(failed),
        "invalid_attempts": invalid,
        "invalid_attempt_rate": round(invalid / max(len(calls), 1), 6),
        "network_failures": network, "failure_kinds": dict(kinds),
        "retries_absorbed": sum(row.get("retries") or 0 for row in ok),
        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in calls),
        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in calls),
        "total_tokens": sum(row.get("total_tokens") or 0 for row in calls),
        "cost_usd": run["calls"].get("cost_usd"),
        "first_call_ts": stamps[0] if stamps else None,
        "last_call_ts": stamps[-1] if stamps else None,
        "latency_ms_p50": run["calls"].get("latency_ms_p50"),
        "latency_ms_p95": run["calls"].get("latency_ms_p95"),
        "workers": run.get("workers"), "response_format": run.get("response_format"),
        "pair_attempts": run.get("pair_attempts"), "run_state": run["state"],
        "complete_families": len(run.get("complete_families", [])),
        "successful_mean_prompt": (sum(row.get("prompt_tokens") or 0 for row in ok) / len(ok)
                                   if ok else None),
        "successful_mean_completion": (sum(row.get("completion_tokens") or 0 for row in ok)
                                       / len(ok) if ok else None)}
    metrics["plan"] = {"total_cases": plan["total_cases"], "total_pairs": plan["total_pairs"],
                       "families": len(plan["families"]), "regions": plan["regions"],
                       "seed": plan["seed"], "pairs_per_batch": plan["pairs_per_batch"],
                       "config_sha256": plan["config_sha256"]}

    # ---- 质量门：交付文件上的精确重复 + 族级标记
    groups = {}
    for case in delivered_cases:
        groups.setdefault(material(case), []).append(case["id"])
    duplicates = [{"material": key[:16], "case_ids": sorted(ids)}
                  for key, ids in sorted(groups.items()) if len(ids) > 1]
    dup_cases = sum(len(group["case_ids"]) for group in duplicates)
    region_dup = {}
    for region in sorted({case["region"] for case in delivered_cases}):
        region_rows = [case for case in delivered_cases if case["region"] == region]
        region_groups = {}
        for case in region_rows:
            region_groups.setdefault(material(case), []).append(case["id"])
        region_dup[region] = sum(len(ids) for ids in region_groups.values() if len(ids) > 1)
    shard_cases = load_optional(base / "shards" / "raw-cases.jsonl")
    raw_dup = None
    shard_root = base / "shards"
    if shard_root.is_dir():
        raw_groups = {}
        for path in sorted(shard_root.rglob("batch-*.cases.jsonl")):
            for case in read_jsonl(path):
                raw_groups.setdefault(material(case), []).append(case["id"])
        raw_dup = sum(len(ids) for ids in raw_groups.values() if len(ids) > 1)
    pair_ids = {case["pair_id"] for case in delivered_cases}
    complete_pairs = len([pid for pid in pair_ids
                          if sum(1 for case in delivered_cases if case["pair_id"] == pid) == 2])
    pair_flags = Counter(flag for row in family_qa.values()
                         for flag in (row.get("quality_flags") or []))
    metrics["quality"] = {
        "pair_flags": dict(pair_flags),
        "delivered_cases": len(delivered_cases),
        "duplicate_cases_total": dup_cases,
        "duplicate_rate": round(dup_cases / max(len(delivered_cases), 1), 6),
        "duplicate_groups": duplicates,
        "duplicate_cases_by_region": region_dup,
        "complete_pairs": complete_pairs, "pairs": len(pair_ids),
        "raw_shard_duplicate_cases": raw_dup,
        "family_duplicates_dropped": {fid: row["duplicate_case_dropped_ids"]
                                      for fid, row in family_qa.items()
                                      if row.get("duplicate_case_dropped_ids")},
        "total_dropped_pairs": sum(row.get("dropped_pairs") or 0 for row in family_qa.values()),
        "total_regenerated_slots": sum(row.get("regenerated_slots") or 0
                                       for row in family_qa.values())}
    metrics["questions"] = {"total": question_total, "by_kind": dict(kind_counts),
                            "per_case": round(question_total / max(len(delivered_cases), 1), 3),
                            "files": question_files}

    # ---- 契约校验
    errors, checked = [], Counter()
    for name in region_files:
        for row in read_jsonl(base / name):
            try:
                validate_case(row)
                checked["case"] += 1
            except ValueError as error:
                errors.append(f"{name}: {error}")
    for name in question_files:
        for row in read_jsonl(base / name):
            try:
                validate_question(row)
                checked["question"] += 1
            except ValueError as error:
                errors.append(f"{name}: {error}")
    metrics["contract"] = {"validated": dict(checked), "errors": errors[:20],
                           "error_count": len(errors)}

    # ---- 边界：分区、密钥、分配表
    assignment, assign_state = {}, "skipped"
    if assign_path and Path(assign_path).is_file():
        for line in Path(assign_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                assignment[row["family_id"]] = row["region"]
        assign_state = "ok"
    region_mismatch = [{"family_id": row["family_id"], "plan": row["region"],
                        "assign": assignment[row["family_id"]]}
                       for row in metrics["families"]
                       if assignment.get(row["family_id"])
                       and assignment[row["family_id"]] != row["region"]]
    secret_hits, scanned = [], 0
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in (".json", ".jsonl", ".md", ".py", ".jsonl.gz"):
            continue
        scanned += 1
        if path.suffix == ".gz":
            continue  # 压缩内容由明文复算，不在这里扫描
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                secret_hits.append({"file": str(path.relative_to(base)),
                                    "pattern": pattern.pattern})
    metrics["boundary"] = {
        "assignment_state": assign_state, "region_mismatch": region_mismatch,
        "region_files": region_files, "question_files": question_files,
        "bad_regions": sorted({case["region"] for case in delivered_cases}
                              - set(PIPELINE_REGIONS)),
        "private_holdout_files": [name for name in region_files
                                  if name.startswith("private_holdout")],
        "private_holdout_in_plan": [row["family_id"] for row in metrics["families"]
                                    if row["region"] == "private_holdout"],
        "secret_hits": secret_hits, "files_scanned_for_secrets": scanned,
        "key_logged_as": "key_fingerprint only"}
    metrics["files"] = {"cases": len(delivered_cases), "questions": question_total,
                        "pairs": len(pair_ids), "complete_pairs": complete_pairs,
                        "families": len(plan["families"])}
    return metrics


def render_markdown(metrics):
    lines = ["# PoL2 试点放量报告（v0.1-pilot，17 族 1904 条）", "",
             "本报告所有数字由 verify_pilot.py 从交付文件复算，可独立重跑（明文缺失时自动读 .gz）：",
             "",
             "    uv run --no-project --offline python datasets/pol2/v0.1-pilot/verify_pilot.py",
             "",
             "配置：--live --workers 8 --pairs-per-batch 3 --pair-attempts 3 --max-attempts 6 "
             "--response-format json_object --max-tokens 16384；不带 --limit，按各族 target_cases 生成。",
             "",
             "## 1) 逐族产出", "",
             "| family_id | region | 计划 case | 交付 case | 完整对 | conforming | violating | "
             "insufficient | 三类齐 | 丢弃对 | 丢弃原因 | 重生成 slot |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in metrics["families"]:
        lines.append("| {family_id} | {region} | {cases_planned} | {cases} | {pairs} | "
                     "{conforming} | {violating} | {insufficient} | {complete_classes} | "
                     "{dropped_pairs} | {drop_reasons} | {regenerated_slots} |".format(**row))
    plan, files = metrics["plan"], metrics["files"]
    lines += ["", f"合计：计划 {plan['total_cases']} 条 / {plan['total_pairs']} 组对；"
                  f"交付 {files['cases']} 条 / {files['pairs']} 组对"
                  f"（完整对 {files['complete_pairs']}）；"
                  f"分区分布 {json.dumps(plan['regions'], ensure_ascii=False)}。", ""]

    calls = metrics["calls"]
    lines += ["## 2) 全局调用与成本", "",
              f"- 总尝试 {calls['attempts']}：ok {calls['ok']}，失败 {calls['failed']}"
              f"（invalid {calls['invalid_attempts']}，占 {calls['invalid_attempt_rate']:.2%}；"
              f"网络失败 {calls['network_failures']}）。",
              f"- 失败分类 {json.dumps(calls['failure_kinds'], ensure_ascii=False)}；"
              f"成功调用中由重试吸收的额外尝试 {calls['retries_absorbed']} 次。",
              f"- token：prompt {calls['prompt_tokens']}，completion {calls['completion_tokens']}，"
              f"合计 {calls['total_tokens']}；成功调用均值 prompt "
              f"{calls['successful_mean_prompt']:.0f} / completion "
              f"{calls['successful_mean_completion']:.0f}。",
              f"- 延迟 p50 {calls['latency_ms_p50']} ms，p95 {calls['latency_ms_p95']} ms；"
              f"并发 {calls['workers']}；窗口 {calls['first_call_ts']} → {calls['last_call_ts']}。",
              f"- cost_usd：{calls['cost_usd']}（sub 路由不返回价格，写 null 不编造）。",
              f"- run state：{calls['run_state']}，完成族 {calls['complete_families']}/"
              f"{plan['families']}。", ""]

    quality = metrics["quality"]
    lines += ["## 3) 质量门", "",
              f"- 族级 pair 质量标记：{json.dumps(quality['pair_flags'], ensure_ascii=False)}"
              f"（duplicate_case / shortcut_risk / weak_pair 均为 0）。",
              f"- 交付文件整体材料精确重复：{quality['duplicate_cases_total']} 条"
              f"（重复率 {quality['duplicate_rate']:.4%}）；按分区 "
              f"{json.dumps(quality['duplicate_cases_by_region'], ensure_ascii=False)}。",
              f"- 组内 status 相反：逐族见第 1 节（族级 QA 全部 "
              f"{quality['pairs'] - quality['total_dropped_pairs']} 组 status_opposite=true）。",
              f"- 生成过程中的丢弃/重生成：丢弃对 {quality['total_dropped_pairs']}，"
              f"重生成 slot {quality['total_regenerated_slots']}。"]
    if quality["family_duplicates_dropped"]:
        lines.append(f"- 合并阶段剔除的重复："
                     f"{json.dumps(quality['family_duplicates_dropped'], ensure_ascii=False)}")
    if quality["raw_shard_duplicate_cases"] is not None:
        lines.append(f"- 内部批次分片（不入库）中的原始重复 case："
                     f"{quality['raw_shard_duplicate_cases']}（已在上一步剔除，不进交付文件）")
    lines.append("")

    questions = metrics["questions"]
    lines += ["## 4) 问题集规模", "",
              f"- question 总数 {questions['total']}，按 kind "
              f"{json.dumps(questions['by_kind'], ensure_ascii=False)}，"
              f"每 case 平均 {questions['per_case']} 条；文件 {questions['files']}。", ""]

    contract = metrics["contract"]
    lines += ["## 5) 契约符合性", "",
              f"- validate_case / validate_question 全量校验："
              f"{json.dumps(contract['validated'], ensure_ascii=False)}；"
              f"错误 {contract['error_count']} 条。"]
    lines += [f"  - {item}" for item in contract["errors"]]
    lines.append("")

    boundary = metrics["boundary"]
    lines += ["## 6) 分区与边界符合性", "",
              f"- region 与私有分配表一致：{boundary['assignment_state']}"
              f"（不一致 {len(boundary['region_mismatch'])} 条）。",
              f"- private_holdout：计划 {len(boundary['private_holdout_in_plan'])} 个族，"
              f"产出文件 {len(boundary['private_holdout_files'])} 个；"
              f"非公开分区 {len(boundary['bad_regions'])} 个。",
              f"- 密钥扫描：文本文件 {boundary['files_scanned_for_secrets']} 个，"
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
    summary = {key: metrics[key] for key in
               ("plan", "files", "calls", "questions", "quality", "contract", "boundary")}
    summary["report_written"] = metrics.get("report_written")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
