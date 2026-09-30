"""用教师模型对 question 取答案，输出 answer 记录（契约 3.3 节）。

每个来源一份文件：<region>.answers.<source>.jsonl，永不覆盖其他来源。
默认离线：不加 --live 只写请求计划；--fixture 用确定性离线答案跑通链路。
断点续跑：已 execution_status=ok 的 qid 跳过；失败记录（timeout/error/invalid）会在下次
重试，最终文件按 question 顺序原子压缩为每 qid 一条；历史尝试保留在调用日志里。
失败不写成 ok：非 ok 记录 answer=null、不写 probs（与 benchmark/PROTOCOL.md 一致）。

    uv run --no-project --offline python datasets/pol2/pipeline/teacher.py \
        --questions <region>.questions.jsonl --out-dir out --region train \
        --source glm-5.3 --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clients import (SOURCES, CallFailure, CallLog, build_client, run_ordered)  # noqa: E402
from common import (PIPELINE_REGIONS, csv_list, index_unique, iso_now, read_questions,  # noqa: E402
                    require, sha256_text, validate_answer, write_jsonl_atomic, write_jsonl_new)
import fixtures  # noqa: E402
import prompts  # noqa: E402

TOOL = "pol2-teacher"
ANSWER_SCHEMA_VERSION = "pol2-pipeline-v0.1"


def answer_path(out_dir, region, source):
    require(region in PIPELINE_REGIONS, f"region must be one of {PIPELINE_REGIONS}")
    require(bool(source) and all(char not in source for char in "/\\:*?\"<>| "),
            f"source {source!r} cannot be used in a file name")
    return Path(out_dir) / f"{region}.answers.{source}.jsonl"


def select_questions(rows, keys, limit):
    index_unique(rows, "qid", where="questions")
    selected = rows
    if keys:
        wanted = set(keys)
        selected = [row for row in rows if row["key"] in wanted]
        require(bool(selected), f"no question matches --keys {sorted(wanted)}")
    if limit is not None:
        require(isinstance(limit, int) and limit > 0, "--limit must be a positive integer")
        selected = selected[:limit]
    return selected


def answer_one(args, question, client):
    if args.fixture:
        answer, probs = fixtures.fixture_answer(question, args.seed, args.source,
                                                args.fixture_disagreement_rate)
        return {"answer": answer, "probs": probs, "execution_status": "ok",
                "latency_ms": 0.0, "notes": ["fixture"], "attempts": 0, "raw": None,
                "usage": None}
    messages = [{"role": "user", "content": prompts.answer_prompt(question)}]
    started = time.perf_counter()
    try:
        result = client.chat(messages, max_tokens=args.max_tokens)
    except CallFailure as failure:
        return {"answer": None, "probs": None, "execution_status": failure.kind,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "notes": [str(failure)[:500]], "attempts": failure.attempts, "raw": None,
                "usage": None}
    try:
        answer, probs, notes = prompts.parse_answer(result["text"], question)
    except ValueError as error:
        return {"answer": None, "probs": None, "execution_status": "invalid",
                "latency_ms": result["latency_ms"], "notes": [str(error)[:500]],
                "attempts": result["attempts"], "raw": None,
                "raw_sha256": sha256_text(result["text"]), "usage": result["usage"]}
    return {"answer": answer, "probs": probs, "execution_status": "ok",
            "latency_ms": result["latency_ms"], "notes": notes, "attempts": result["attempts"],
            "raw": result["text"], "usage": result["usage"]}


def build_record(args, question, outcome):
    row = {"qid": question["qid"], "source": args.source, "source_version": args.source_version,
           "answer": outcome["answer"], "execution_status": outcome["execution_status"],
           "latency_ms": round(outcome["latency_ms"], 2), "created_at": iso_now()}
    if outcome["probs"] is not None:
        row["probs"] = outcome["probs"]
    if args.save_raw and outcome.get("raw"):
        row["raw"] = {"text": outcome["raw"]}
    extra = {"notes": outcome["notes"], "attempts": outcome["attempts"], "model": args.model,
             "template": prompts.ANSWER_TEMPLATE_VERSION}
    if outcome.get("usage"):
        extra["usage"] = outcome["usage"]
    if outcome.get("raw_sha256"):
        extra["raw_sha256"] = outcome["raw_sha256"]
    row["extra"] = extra
    validate_answer(row, where=f"answer {question['qid']}", question=question)
    return row


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="答案文件路径；缺省用 --out-dir/<region>.answers.<source>.jsonl")
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    parser.add_argument("--region", choices=PIPELINE_REGIONS, default="train")
    parser.add_argument("--source", default="glm-5.3", help="答案来源名，写进文件名与 source 字段")
    parser.add_argument("--source-version", help="固定版本或接口版本（缺省用模型 id）")
    parser.add_argument("--keys", help="逗号分隔的问题短键过滤，如 status,action")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", "--concurrency", dest="workers", type=int, default=4,
                        help="并发上限；--concurrency 是同一参数的别名")
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--key-env")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--price-in", type=float)
    parser.add_argument("--price-out", type=float)
    parser.add_argument("--user-agent", help="覆盖 HTTP User-Agent")
    parser.add_argument("--save-raw", action="store_true",
                        help="把原始响应写进 raw（仅在许可允许公开时使用）")
    parser.add_argument("--fixture-disagreement-rate", type=float, default=0.0)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="真实联网调用（默认离线）")
    mode.add_argument("--fixture", action="store_true", help="离线确定性答案")
    mode.add_argument("--dry-run", action="store_true", help="只写请求计划，不联网")
    return parser


def main(argv=None, client_factory=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        require(args.workers > 0, "--workers must be positive")
        rows = read_questions(args.questions)
        selected = select_questions(rows, csv_list(args.keys), args.limit)
        path = args.out or answer_path(args.out_dir, args.region, args.source)
        require(not args.fixture or args.source == "fixture"
                or args.source.startswith("fixture"),
                "--fixture 只能与 --source fixture（或 fixture-*）一起使用，避免把合成答案当真实答案")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"teacher: {error}\n")

    if args.fixture:
        args.model = args.model or fixtures.FIXTURE_MODEL
        args.source_version = args.source_version or fixtures.FIXTURE_VERSION
    else:
        config = SOURCES.get(args.source, {})
        args.model = args.model or config.get("model", args.source)
        args.source_version = args.source_version or args.model

    existing = []
    if path.exists():
        try:
            from common import read_answers
            existing = read_answers(path, questions={row["qid"]: row for row in rows})
        except (OSError, ValueError) as error:
            parser.exit(2, f"teacher: existing answer file is invalid: {error}\n")
    done = {row["qid"] for row in existing if row["execution_status"] == "ok"}
    todo = [row for row in selected if row["qid"] not in done]

    call_log = CallLog(Path(args.out_dir) / f"calls.{args.source}.jsonl")
    client = None
    if args.live:
        try:
            factory = client_factory or (lambda parsed: build_client(
                parsed.source, base_url=parsed.base_url, model=parsed.model,
                key_env=parsed.key_env, key_file=parsed.key_file, timeout=parsed.timeout,
                max_attempts=parsed.max_attempts, log=call_log, max_tokens=parsed.max_tokens,
                price_in=parsed.price_in, price_out=parsed.price_out,
                user_agent=parsed.user_agent))
            client = factory(args)
            args.model = getattr(client, "model", args.model)
        except (OSError, ValueError) as error:
            parser.exit(2, f"teacher: {error}\n")

    if not (args.live or args.fixture):
        payloads = []
        for question in todo:
            messages = [{"role": "user", "content": prompts.answer_prompt(question)}]
            body = (client.payload(messages, max_tokens=args.max_tokens) if client
                    else {"model": args.model, "messages": messages, "max_tokens": args.max_tokens})
            payloads.append({"qid": question["qid"], "source": args.source, "payload": body})
        plan_path = Path(args.out_dir) / "requests" / f"{args.source}.requests.jsonl"
        write_jsonl_new(plan_path, payloads)
        print(json.dumps({"mode": "dry-run", "source": args.source, "requests": len(payloads),
                          "planned": str(plan_path), "answers": str(path),
                          "already_ok": len(done)}, ensure_ascii=False))
        return 0

    outcomes = run_ordered(todo, lambda question, index: answer_one(args, question, client),
                           workers=args.workers)
    new_rows = []
    failures = {"timeout": 0, "error": 0, "invalid": 0}
    for question, outcome in zip(todo, outcomes):
        if isinstance(outcome, Exception):
            outcome = {"answer": None, "probs": None, "execution_status": "invalid",
                       "latency_ms": 0.0, "notes": [str(outcome)[:500]], "attempts": 0, "raw": None,
                       "usage": None}
        record = build_record(args, question, outcome)
        if record["execution_status"] != "ok":
            failures[record["execution_status"]] += 1
        new_rows.append(record)

    by_qid = {row["qid"]: row for row in existing}
    for row in new_rows:
        by_qid[row["qid"]] = row
    final = [by_qid[row["qid"]] for row in rows if row["qid"] in by_qid]
    write_jsonl_atomic(path, final)
    ok_total = sum(1 for row in final if row["execution_status"] == "ok")
    summary = {"mode": "fixture" if args.fixture else "live", "source": args.source,
               "source_version": args.source_version, "answers": str(path),
               "questions": len(rows), "attempted": len(todo), "skipped_ok": len(done),
               "ok_total": ok_total, "new_failures": failures, "calls": call_log.summary()}
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if any(failures.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
