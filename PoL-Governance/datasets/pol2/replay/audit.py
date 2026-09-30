"""PoL2 通用决策回放池：HuggingFace 候选数据审计（只读、可复跑）。

三个子命令：

    fetch    联网拉取 HF dataset 元数据（固定 revision），与人工审计表合并成机器可读 JSON
    build    离线：从 fixtures/audit 的 API 快照构建同一结构（测试与断网复核用）
    verify   离线：校验每条记录必填字段齐全，并强制准入规则

只使用 Python 标准库，可在 `uv run --no-project --offline` 下运行。
网络只走 https://huggingface.co/api/datasets...（本环境 web_fetch 被拦，用 urllib 直连可行）。
审计输出是**证据**，不是数据本体：本目录不下载、不提交任何第三方数据。

准入硬规则（verify 强制，见 replay_pool.md）：
1. 公开测试集或对抗 benchmark 本体一律 exclude，不得 admit；
2. 许可不明（unclear/none）一律不得 admit；
3. admit 的记录必须是固定 revision、且只取 train 分区；
4. admit 需要 A/B 级证据（A=读过卡面与原始记录，B=读过卡面字段）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOOL = "pol2-replay-audit"
AUDIT_VERSION = "pol2-replay-audit-v0.1"
HF_API = "https://huggingface.co/api"
USER_AGENT = "PoL2-replay-audit/0.1 (+https://github.com/naturaldao/NaturalDAO)"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")

REQUIRED_FIELDS = ("id", "revision", "license", "license_status", "license_training",
                   "license_derivative", "task_forms", "languages", "splits", "train_only",
                   "is_benchmark", "generation", "source_basis", "row_count", "tier",
                   "decision_reason", "evidence_level", "checked_at", "hf")

LICENSE_STATUSES = ("clear", "composite", "unclear", "none")
LICENSE_USE = ("yes", "yes_with_conditions", "no", "unknown")
TIERS = ("admit", "observe", "exclude")
EVIDENCE_LEVELS = ("A", "B", "C", "D")
TASK_FORMS = ("choice", "noul", "score", "classification", "nli", "extraction", "other")
GENERATIONS = ("synthetic", "teacher-distill", "human", "mixed", "unknown")
ADMITTING_EVIDENCE = ("A", "B")
BENCHMARK_TAGS = ("benchmark", "evaluation", "eval", "leaderboard")
BENCHMARK_ID_HINTS = ("bench", "eval", "holdout", "heldout", "test-suite")
DEFAULT_SEARCH_TERMS = ("jev", "open-jev", "typed-decision", "typed_decision", "system-one",
                        "system_one", "decision", "nli", "rlcd", "judgement", "judgment",
                        "entailment", "risk-assessment")


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hf_get(url, timeout=60.0, attempts=3, opener=None):
    """GET a HF API URL as JSON, with a product User-Agent and bounded retries."""
    last = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": USER_AGENT})
        try:
            with (opener or urllib.request.urlopen)(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
                ValueError) as error:
            last = error
            if attempt < attempts:
                time.sleep(min(2.0 * attempt, 5.0))
    raise RuntimeError(f"HF API 请求失败: {url}: {last}")


def dataset_url(dataset_id):
    return f"{HF_API}/datasets/{dataset_id}"


def search_url(term, limit=100):
    return f"{HF_API}/datasets?search={term}&limit={limit}&sort=downloads&direction=-1"


def license_of(payload):
    """Card license first, then tags; never invent one."""
    card = payload.get("cardData") or {}
    if isinstance(card.get("license"), str):
        return card["license"]
    if isinstance(card.get("license"), list):
        return "|".join(sorted(str(item) for item in card["license"]))
    tags = [tag for tag in payload.get("tags") or [] if isinstance(tag, str)]
    found = sorted(tag.split(":", 1)[1] for tag in tags if tag.startswith("license:"))
    return "|".join(found) if found else None


def benchmark_flag(dataset_id, tags=(), card_text=""):
    """Name/tag heuristic. It only *flags*; 准入/剔除 决定仍由人工审计表给出。"""
    lowered = [tag.lower() for tag in tags or []]
    if any(any(hint in tag for hint in BENCHMARK_TAGS) for tag in lowered):
        return True
    name = dataset_id.split("/", 1)[-1].lower()
    if any(hint in name for hint in BENCHMARK_ID_HINTS):
        return True
    return bool(re.search(r"\b(bench|eval|holdout|held-out)\b", card_text or "", re.I))


def snapshot(payload):
    """Reduce an API dataset payload to the fields the audit needs."""
    card = payload.get("cardData") or {}
    languages = card.get("language")
    if isinstance(languages, str):
        languages = [languages]
    return {
        "id": payload.get("id"),
        "sha": payload.get("sha"),
        "last_modified": payload.get("lastModified"),
        "downloads": payload.get("downloads"),
        "likes": payload.get("likes"),
        "gated": payload.get("gated"),
        "card_license": license_of(payload),
        "tags": sorted(tag for tag in payload.get("tags") or [] if isinstance(tag, str)),
        "languages": languages,
        "files": len(payload.get("siblings") or []),
    }


def validate_record(record, allow_unpinned=False):
    """Return a list of problems; empty means the record obeys the admission contract."""
    problems = []
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        return [f"{record.get('id', '?')}: 缺必填字段 {sorted(missing)}"]
    rid = record["id"]
    if not isinstance(rid, str) or not ID_RE.match(rid):
        problems.append(f"{rid}: id 必须是 owner/name 形式")
    if not allow_unpinned and not (isinstance(record["revision"], str)
                                   and SHA_RE.match(record["revision"])):
        problems.append(f"{rid}: revision 必须是固定 40 位 commit sha 或 'unpinned'")
    if record["license_status"] not in LICENSE_STATUSES:
        problems.append(f"{rid}: license_status 取值非法 {record['license_status']!r}")
    for flag in ("license_training", "license_derivative"):
        if record[flag] not in LICENSE_USE:
            problems.append(f"{rid}: {flag} 取值非法 {record[flag]!r}（yes/yes_with_conditions/no/unknown）")
    if record["tier"] not in TIERS:
        problems.append(f"{rid}: tier 取值非法 {record['tier']!r}")
    if record["evidence_level"] not in EVIDENCE_LEVELS:
        problems.append(f"{rid}: evidence_level 取值非法 {record['evidence_level']!r}")
    if record["generation"] not in GENERATIONS:
        problems.append(f"{rid}: generation 取值非法 {record['generation']!r}")
    if not isinstance(record["task_forms"], list) or not record["task_forms"]:
        problems.append(f"{rid}: task_forms 必须是非空列表")
    else:
        bad = [form for form in record["task_forms"] if form not in TASK_FORMS]
        if bad:
            problems.append(f"{rid}: 未知 task_forms {bad}")
    if not isinstance(record["languages"], list) or not record["languages"]:
        problems.append(f"{rid}: languages 必须是非空列表")
    if not isinstance(record["splits"], list) or not record["splits"]:
        problems.append(f"{rid}: splits 必须是非空列表")
    for flag in ("train_only", "is_benchmark"):
        if not isinstance(record[flag], bool):
            problems.append(f"{rid}: {flag} 必须是布尔值")
    if not isinstance(record["decision_reason"], str) or not record["decision_reason"].strip():
        problems.append(f"{rid}: decision_reason 不能为空")
    if record["row_count"] is not None and not isinstance(record["row_count"], int):
        problems.append(f"{rid}: row_count 必须是整数或 null（未知就写 null，不要猜）")
    if not isinstance(record["license"], str) or not record["license"].strip():
        problems.append(f"{rid}: license 不能为空（未知写 unknown）")

    # --- 准入硬规则 ---
    if record["tier"] == "admit":
        if record["is_benchmark"]:
            problems.append(f"{rid}: 评测集/benchmark 不得 admit（SPEC 硬规则）")
        if record["license_status"] not in ("clear", "composite"):
            problems.append(f"{rid}: 许可 {record['license_status']} 不得 admit，只能进观察项")
        if not record["train_only"]:
            problems.append(f"{rid}: admit 必须 train_only=True")
        if record["evidence_level"] not in ADMITTING_EVIDENCE:
            problems.append(f"{rid}: admit 需要 A/B 级证据，当前 {record['evidence_level']}")
        if record["license_training"] != "yes":
            problems.append(f"{rid}: 许可不允许/不明确允许训练（license_training="
                            f"{record['license_training']}），不得 admit")
        if record["license_derivative"] not in ("yes", "yes_with_conditions"):
            problems.append(f"{rid}: 许可不允许衍生发布（license_derivative="
                            f"{record['license_derivative']}），不得 admit")
        if not allow_unpinned and not SHA_RE.match(str(record["revision"])):
            problems.append(f"{rid}: admit 必须绑定固定 revision")
    if record["is_benchmark"] and record["tier"] != "exclude":
        problems.append(f"{rid}: is_benchmark=True 时 tier 必须是 exclude")
    hf = record.get("hf") or {}
    if hf.get("benchmark_flag") and record["tier"] == "admit":
        review = record.get("benchmark_flag_review") or {}
        if review.get("conclusion") != "not_a_benchmark" or not str(review.get("evidence", "")).strip():
            problems.append(f"{rid}: HF 元数据已标记 benchmark/eval；除非写入 "
                            f"benchmark_flag_review（conclusion=not_a_benchmark + evidence），否则不得 admit")
    if hf.get("card_license") and record["license_status"] == "clear":
        pinned = str(record["license"]).lower()
        observed = str(hf["card_license"]).lower()
        if observed not in pinned and pinned not in observed:
            problems.append(f"{rid}: 记录许可 {record['license']} 与 HF 卡面 {hf['card_license']} 不一致")
    return problems


def build_records(candidates, details, checked_at, allow_unpinned=False):
    """Merge curated judgements with API snapshots; return (records, problems)."""
    records, problems = [], []
    for candidate in candidates:
        rid = candidate.get("id")
        payload = details.get(rid)
        hf = {}
        if payload is None:
            problems.append(f"{rid}: 缺少 API 快照，无法核对 revision/许可")
        else:
            hf = snapshot(payload)
            hf["benchmark_flag"] = benchmark_flag(rid, hf["tags"])
        record = dict(candidate)
        record["checked_at"] = checked_at
        record["hf"] = hf
        if payload is not None and not record.get("revision"):
            record["revision"] = hf.get("sha") or "unpinned"
        if payload is not None and candidate.get("verify_revision", True):
            if hf.get("sha") != record.get("revision"):
                problems.append(f"{rid}: revision 漂移：审计表 {record.get('revision')} "
                                f"≠ 实时 {hf.get('sha')}")
        records.append(record)
    for record in records:
        problems.extend(validate_record(record, allow_unpinned=allow_unpinned))
    return records, problems


def summarize(records):
    summary = {"candidates": len(records), "admit": 0, "observe": 0, "exclude": 0,
               "by_evidence": {}, "by_generation": {}, "benchmarks_excluded": 0}
    for record in records:
        summary[record["tier"]] = summary.get(record["tier"], 0) + 1
        key = record["evidence_level"]
        summary["by_evidence"][key] = summary["by_evidence"].get(key, 0) + 1
        key = record["generation"]
        summary["by_generation"][key] = summary["by_generation"].get(key, 0) + 1
        if record["is_benchmark"]:
            summary["benchmarks_excluded"] += 1
    return summary


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
                    encoding="utf-8")


def load_candidates(path):
    payload = load_json(path)
    candidates = payload["candidates"] if isinstance(payload, dict) else payload
    ids = [row["id"] for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("candidates.json 里有重复 id")
    return payload, candidates


def load_fixture_details(fixtures):
    """Read API snapshots from a fixtures directory (datasets/*.json, search-*.json)."""
    root = Path(fixtures)
    if not root.is_dir():
        raise ValueError(f"fixtures 目录不存在: {fixtures}")
    details, hits = {}, {}
    for path in sorted((root / "datasets").glob("*.json")):
        payload = load_json(path)
        details[payload["id"]] = payload
    for path in sorted(root.glob("search-*.json")):
        term = path.stem.split("search-", 1)[1]
        hits[term] = len(load_json(path))
    return details, hits


def cmd_fetch(args):
    payload, candidates = load_candidates(args.candidates)
    cache = Path(args.cache_dir) if args.cache_dir else Path(tempfile.gettempdir()) / TOOL
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "datasets").mkdir(exist_ok=True)
    hits = {}
    for term in args.search or []:
        path = cache / f"search-{term}.json"
        if path.exists() and not args.refresh:
            hits[term] = len(load_json(path))
            continue
        found = hf_get(search_url(term), timeout=args.timeout)
        write_json(path, found)
        hits[term] = len(found)
    details = {}
    for candidate in candidates:
        rid = candidate["id"]
        path = cache / "datasets" / (rid.replace("/", "__") + ".json")
        if path.exists() and not args.refresh:
            details[rid] = load_json(path)
            continue
        found = hf_get(dataset_url(rid), timeout=args.timeout)
        write_json(path, found)
        details[rid] = found
    records, problems = build_records(candidates, details, iso_now(),
                                      allow_unpinned=args.allow_unpinned)
    if problems and not args.keep_going:
        for problem in problems:
            print(f"PROBLEM {problem}", file=sys.stderr)
        print(json.dumps({"status": "failed", "problems": problems}, ensure_ascii=False))
        return 1
    report = {"tool": TOOL, "version": AUDIT_VERSION, "mode": "live", "generated_at": iso_now(),
              "search_terms": list(args.search or []), "search_hits": hits,
              "cache_dir": str(cache), "summary": summarize(records), "records": records,
              "problems": problems}
    write_json(args.out, report)
    print(json.dumps({"status": "ok" if not problems else "problems", "out": str(args.out),
                      "summary": report["summary"], "problems": len(problems)},
                     ensure_ascii=False))
    return 0 if not problems else 1


def cmd_build(args):
    payload, candidates = load_candidates(args.candidates)
    details, hits = load_fixture_details(args.fixtures)
    records, problems = build_records(candidates, details, iso_now(),
                                      allow_unpinned=args.allow_unpinned)
    report = {"tool": TOOL, "version": AUDIT_VERSION, "mode": "fixtures",
              "generated_at": iso_now(), "search_terms": sorted(hits), "search_hits": hits,
              "fixtures": str(args.fixtures), "summary": summarize(records), "records": records,
              "problems": problems}
    if problems and not args.keep_going:
        for problem in problems:
            print(f"PROBLEM {problem}", file=sys.stderr)
        print(json.dumps({"status": "failed", "problems": problems}, ensure_ascii=False))
        return 1
    write_json(args.out, report)
    print(json.dumps({"status": "ok" if not problems else "problems", "out": str(args.out),
                      "summary": report["summary"], "problems": len(problems)},
                     ensure_ascii=False))
    return 0 if not problems else 1


def cmd_verify(args):
    report = load_json(args.audit)
    records = report.get("records") if isinstance(report, dict) else report
    if not isinstance(records, list) or not records:
        print(json.dumps({"status": "failed", "problems": ["审计文件没有 records"]},
                         ensure_ascii=False))
        return 1
    problems = []
    for record in records:
        problems.extend(validate_record(record, allow_unpinned=args.allow_unpinned))
    result = {"status": "ok" if not problems else "failed", "audit": str(args.audit),
              "summary": summarize(records), "problems": problems}
    print(json.dumps(result, ensure_ascii=False))
    if args.strict and isinstance(report, dict) and report.get("problems"):
        return 1
    return 0 if not problems else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="联网拉取 HF 元数据并生成审计 JSON")
    fetch.add_argument("--candidates", type=Path, default=Path(__file__).with_name("candidates.json"))
    fetch.add_argument("--out", type=Path, required=True)
    fetch.add_argument("--cache-dir", type=Path, help="原始 API 快照缓存目录（默认系统临时目录）")
    fetch.add_argument("--search", nargs="*", default=list(DEFAULT_SEARCH_TERMS),
                       help="命名法搜索词，默认覆盖 jev/typed-decision/system-one 等")
    fetch.add_argument("--refresh", action="store_true", help="忽略缓存重新拉取")
    fetch.add_argument("--timeout", type=float, default=60.0)
    fetch.add_argument("--allow-unpinned", action="store_true")
    fetch.add_argument("--keep-going", action="store_true", help="有问题也写出 JSON")
    fetch.set_defaults(func=cmd_fetch)

    build = sub.add_parser("build", help="离线：用 fixtures 快照构建审计 JSON")
    build.add_argument("--candidates", type=Path, default=Path(__file__).with_name("candidates.json"))
    build.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("fixtures") / "audit")
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--allow-unpinned", action="store_true")
    build.add_argument("--keep-going", action="store_true")
    build.set_defaults(func=cmd_build)

    verify = sub.add_parser("verify", help="离线：校验审计 JSON 的必填字段与准入规则")
    verify.add_argument("--audit", type=Path, required=True)
    verify.add_argument("--allow-unpinned", action="store_true")
    verify.add_argument("--strict", action="store_true", help="文件里记录的 problems 也算失败")
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(2, f"audit: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
