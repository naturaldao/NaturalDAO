"""官方 Jev 适配器：只定义接口与 HTTP 客户端骨架，未接入前明确报错，绝不静默降级。

两段式：
    prepare  由本地问题清单生成请求包（离线，随时可跑）：
        uv run --no-project --offline python datasets/pol2/pipeline/jev.py prepare \
            --questions <region>.questions.jsonl --out <目录>
    run      只有在用户提供 endpoint、官方 api_version 与密钥，并显式确认已核对协议后才执行；
             缺任何一项直接退出 2，绝不回落到其他答案源：
        uv run --no-project --offline python datasets/pol2/pipeline/jev.py run \
            --out <目录> --endpoint https://<官方地址> --api-version <版本> \
            --integration-confirmed

截至 2026-09-30，官方 Jev 服务的请求/响应形状未核实（见 pipeline/README.md「外部接口」），
因此 run 默认拒绝执行。任何缺字段、未知 qid、形状不符都记为 execution_status=invalid，不写 ok。
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clients import CallFailure, NoRedirect, validate_endpoint  # noqa: E402
from common import (PIPELINE_REGIONS, index_unique, iso_now, load_secret, read_questions,  # noqa: E402
                    require, sha256_text, validate_answer, write_json_new, write_jsonl_atomic,
                    write_jsonl_new)

TOOL = "pol2-jev-adapter"
ADAPTER_VERSION = "pol2-jev-v0.1"
DEFAULT_KEY_ENV = "JEV_API_KEY"
MAX_RESPONSE_BYTES = 2_000_000


class JevNotIntegrated(RuntimeError):
    """Raised instead of silently degrading to another answer source."""


def prepare(questions, out):
    out = Path(out)
    require(not (out / "run.json").exists() and not (out / "jev-requests.jsonl").exists(),
            f"{out} already holds a prepared pack; use a new --out directory")
    write_jsonl_new(out / "jev-requests.jsonl", questions)
    manifest = {"tool": TOOL, "adapter": ADAPTER_VERSION, "state": "prepared",
                "protocol": "unverified", "api_version": None, "endpoint": None,
                "requests": len(questions),
                "questions_sha256": sha256_text(json.dumps(questions, ensure_ascii=False,
                                                           sort_keys=True)),
                "note": "官方形状未核实；run 需 --endpoint --api-version --integration-confirmed",
                "created_at": iso_now()}
    write_json_new(out / "run.json", manifest)
    return manifest


def request_envelope(api_version, questions):
    return {"api_version": api_version,
            "requests": [{"qid": question["qid"], "kind": question["kind"],
                          "prompt": question["prompt"]} for question in questions]}


def parse_response(payload, questions):
    """Map an official response to per-question outcomes; unknown/missing qids are invalid."""
    require(isinstance(payload, dict) and isinstance(payload.get("answers"), dict),
            "Jev response must be an object with an answers object")
    answers = payload["answers"]
    outcomes = {}
    for question in questions:
        qid = question["qid"]
        item = answers.get(qid)
        if not isinstance(item, dict) or "answer" not in item:
            outcomes[qid] = {"answer": None, "execution_status": "invalid", "probs": None,
                             "notes": ["missing or malformed answer for qid"]}
            continue
        value = item["answer"]
        if question["kind"] == "score":
            valid = (isinstance(value, (int, float)) and not isinstance(value, bool)
                     and question["scale"]["min"] <= value <= question["scale"]["max"])
        else:
            valid = isinstance(value, str) and value in [o["key"] for o in question["options"]]
        if not valid:
            outcomes[qid] = {"answer": None, "execution_status": "invalid", "probs": None,
                             "notes": [f"answer {value!r} outside the question domain"]}
            continue
        probs, notes = None, []
        if isinstance(item.get("probs"), dict):
            from common import rescale_probs
            try:
                probs = rescale_probs(item["probs"],
                                        keys=None if question["kind"] == "score"
                                        else [o["key"] for o in question["options"]])
            except ValueError as error:
                notes.append(f"probs_dropped:{error}")
        outcomes[qid] = {"answer": value, "execution_status": "ok", "probs": probs, "notes": notes}
    return outcomes


def transport(endpoint, payload, timeout, key=None, request_path="/answers"):
    validate_endpoint(endpoint)
    url = endpoint.rstrip("/") + request_path
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            require(len(body) <= MAX_RESPONSE_BYTES, "response too large")
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise CallFailure("error", f"HTTP {error.code}: {error.read(200)!r}") from error
    except (TimeoutError, socket.timeout) as error:
        raise CallFailure("timeout", f"timeout: {error}") from error
    except urllib.error.URLError as error:
        kind = "timeout" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "error"
        raise CallFailure(kind, f"url error: {error.reason}") from error
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CallFailure("invalid", f"bad response: {error}") from error


def run(args, questions, key, sender=transport):
    payload = request_envelope(args.api_version or "unverified", questions)
    if args.dry_run:
        write_jsonl_new(Path(args.out) / "jev-run-requests.jsonl",
                        [{"api_version": args.api_version, "endpoint": args.endpoint,
                          "request_path": args.request_path, "payload": payload}])
        return {}, {"mode": "dry-run", "requests": len(questions), "sent": 0}
    started = time.perf_counter()
    response = sender(args.endpoint, payload, args.timeout, key, args.request_path)
    latency_ms = (time.perf_counter() - started) * 1000
    outcomes = parse_response(response, questions)
    for outcome in outcomes.values():
        outcome["latency_ms"] = latency_ms
    return outcomes, {"mode": "live", "requests": len(questions), "sent": 1,
                      "latency_ms": round(latency_ms, 2)}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare", help="离线生成请求包")
    p_prepare.add_argument("--questions", type=Path, required=True)
    p_prepare.add_argument("--out", type=Path, required=True)
    p_run = sub.add_parser("run", help="在已核实的官方接口上取答案")
    p_run.add_argument("--out", type=Path, required=True)
    p_run.add_argument("--questions", type=Path, help="缺省读 <out>/jev-requests.jsonl")
    p_run.add_argument("--endpoint")
    p_run.add_argument("--api-version")
    p_run.add_argument("--key-env", default=DEFAULT_KEY_ENV)
    p_run.add_argument("--key-file", type=Path)
    p_run.add_argument("--request-path", default="/answers")
    p_run.add_argument("--region", choices=PIPELINE_REGIONS, default="train")
    p_run.add_argument("--timeout", type=float, default=120.0)
    p_run.add_argument("--integration-confirmed", action="store_true",
                       help="确认已按官方文档核对请求/响应形状（否则拒绝执行）")
    p_run.add_argument("--dry-run", action="store_true", help="只写请求，不发送")
    return parser


def main(argv=None, sender=transport):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            questions = read_questions(args.questions)
            manifest = prepare(questions, args.out)
            print(json.dumps({"command": "prepare", "out": str(args.out),
                              "requests": manifest["requests"], "protocol": "unverified"},
                             ensure_ascii=False))
            return 0
        source = args.questions or (Path(args.out) / "jev-requests.jsonl")
        require(Path(source).is_file(), f"missing question pack: {source}（先跑 prepare）")
        questions = read_questions(source)
        index_unique(questions, "qid", where=str(source))
        key = None
        if not args.dry_run:
            require(bool(args.endpoint), "Jev endpoint 未提供：拒绝运行（--endpoint）")
            require(bool(args.api_version), "官方 api_version 未提供：拒绝运行（--api-version）")
            require(bool(args.integration_confirmed),
                    "Jev 协议未核实：先按官方文档核对请求/响应形状，再传 --integration-confirmed")
            validate_endpoint(args.endpoint)
            key, _ = load_secret([args.key_env], key_file=args.key_file, ref=args.key_env)
        version = args.api_version or "unverified"
        source_name = f"jev-{version}"
        outcomes, report = run(args, questions, key, sender=sender)
        if report["mode"] == "dry-run":
            print(json.dumps({"command": "run", "mode": "dry-run",
                              "requests": report["requests"], "out": str(args.out)},
                             ensure_ascii=False))
            return 0
        rows = []
        for question in questions:
            outcome = outcomes[question["qid"]]
            row = {"qid": question["qid"], "source": source_name, "source_version": version,
                   "answer": outcome["answer"], "execution_status": outcome["execution_status"],
                   "latency_ms": round(outcome.get("latency_ms", 0.0), 2), "created_at": iso_now()}
            if outcome.get("probs") is not None:
                row["probs"] = outcome["probs"]
            row["extra"] = {"notes": outcome["notes"], "adapter": ADAPTER_VERSION}
            validate_answer(row, where=f"jev answer {question['qid']}", question=question)
            rows.append(row)
        path = Path(args.out) / f"{args.region}.answers.{source_name}.jsonl"
        write_jsonl_atomic(path, rows)
        ok = sum(1 for row in rows if row["execution_status"] == "ok")
        print(json.dumps({"command": "run", "answers": str(path), "requests": len(rows),
                          "ok": ok, "invalid": len(rows) - ok, "report": report},
                         ensure_ascii=False))
        return 1 if ok != len(rows) else 0
    except (OSError, ValueError, KeyError, JevNotIntegrated, CallFailure) as error:
        parser.exit(2, f"jev: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
