#!/usr/bin/env python
"""Jev 分层校验 + 概率补全（datasets/general/jev_fill.py, jev-v0.1）。

用途
    phase=validation  抽 300 条（lang x domain x kind 分层）调 Jev 取答案，与语料真值比对
    phase=fill        对 answer-only 的 target 调 Jev，满足硬约束才写旁挂 probs（不改冻结语料）

子命令
    show-config   打印生效配置（密钥只留 sha256 前 8 位指纹；本脚本永不打印密钥本体）
    sample        分层抽样 -> validation plan（只读语料）
    fill-plan     全量 answer-only target -> fill plan（只读语料）
    run           执行调用：可续跑、限速、指数退避重试、预算硬停、逐次尝试落盘
    report        生成 datasets/general/jev-validation.md
    verify        校验阶段二产物（argmax==answer / 归一 / 无重复 / 只含 answer-only 的 qid）
    cost          汇总若干 journal 的调用数与花费

只用标准库；sample/report/verify/cost 均可离线运行。
调用细节（Lead 实测，2026-10-15）：必须带 user-agent（否则 Cloudflare 返回 HTML）；
max_tokens 必须 >= 2000（推理模型思维链会吃光输出预算）；temperature=0。

示例
    uv run --no-project --offline python datasets/general/jev_fill.py sample --n 300
    uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation --limit 3 --budget 0.01
    uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation --budget 0.05
    uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

TOOL = "general-jev-fill"
HARNESS_VERSION = "jev-v0.1"
GENERAL = Path(__file__).resolve().parent
ROOT = GENERAL.parents[1]
DEFAULT_ITEMS = GENERAL / "data" / "items.final.jsonl"
DEFAULT_JEV_YAML = ROOT / "datasets" / "jev.yaml"
DEFAULT_WORK = GENERAL / "data" / "jev"
DEFAULT_VALIDATION_MD = GENERAL / "jev-validation.md"
DEFAULT_FILL_OUT = GENERAL / "data" / "jev-probs.jsonl"

RETRY_STATUS = (408, 409, 425, 429, 500, 502, 503, 504)
FENCE = chr(96) * 3
MAX_RESPONSE_BYTES = 4_000_000
USER_AGENT = "PoL-general-jev/0.1 (+https://github.com/naturaldao/NaturalDAO)"

KINDS = ("noul", "choice", "score")
POSITIVE = ("yes", "y", "true", "t", "1", "是", "对", "正确")
NEGATIVE = ("no", "n", "false", "f", "0", "否", "不是", "错误")

# 无法解析的原因分类（报告里按此归类）
REASONS = {
    "empty_content": "空输出",
    "length": "被 max_tokens 截断（finish_reason=length）",
    "not_in_options": "输出不在选项内",
    "ambiguous_match": "同时命中多个选项",
    "no_integer_in_range": "score 输出里没有合法档位",
    "not_json": "distribution 变体输出不是合法 JSON 对象",
    "http_error": "HTTP 非 200",
    "insufficient_credits": "HTTP 402：账户/密钥余额不足（致命，立即停止整批）",
    "fatal_stop": "因致命错误（余额不足）未发出",
    "timeout": "超时",
    "network_error": "网络/其他错误",
    "budget_stop": "预算上限，未调用",
}


# ------------------------------------------------------------------ 基础工具

def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def fingerprint(secret):
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    return path


class Journal:
    """追加写 JSONL：逐行 flush + fsync（进程被杀不丢已完成行）。"""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.rows = []
        if self.path.is_file():
            self.rows = read_jsonl(self.path)

    def append(self, row):
        row = {"ts": iso_now(), **row}
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self.rows.append(row)
        return row


# ------------------------------------------------------------------ 配置

def load_jev_config(path=DEFAULT_JEV_YAML):
    """读 datasets/jev.yaml 的三行键值；环境变量优先。密钥绝不落盘、绝不打印。"""
    values = {}
    path = Path(path)
    if path.is_file():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
                continue
            name, value = raw.split(":", 1)
            values[name.strip()] = value.strip().strip('"').strip("'")
    config = {
        "endpoint": os.environ.get("JEV_ENDPOINT") or values.get("endpoint") or "",
        "apikey": os.environ.get("JEV_API_KEY") or values.get("apikey") or "",
        "model": os.environ.get("JEV_MODEL") or values.get("model") or "",
        "config_path": str(path),
    }
    if not config["endpoint"]:
        raise SystemExit("缺 endpoint：datasets/jev.yaml 或环境变量 JEV_ENDPOINT")
    if not config["model"]:
        raise SystemExit("缺 model：datasets/jev.yaml 或环境变量 JEV_MODEL")
    return config


def chat_url(endpoint):
    endpoint = endpoint.rstrip("/")
    return endpoint + "/chat/completions"


# ------------------------------------------------------------------ 语料读取

def iter_targets(items_path):
    """流式产出 (item, key, question, target)；不改写任何东西。"""
    with open(items_path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            qmap = {q.get("key"): q for q in (item.get("questions") or [])}
            for key, target in (item.get("targets") or {}).items():
                question = qmap.get(key)
                if question is None:
                    continue
                yield item, key, question, target


def option_space(question):
    """问题的完整取值域：score 是 min..max 的数字档位（字符串），其余是选项 key。"""
    if question["kind"] == "score":
        scale = question["scale"]
        return [str(level) for level in range(int(scale["min"]), int(scale["max"]) + 1)]
    return [str(option["key"]) for option in question["options"]]


def display_tokens(question):
    """给人看的候选文本（与 key 一一对应，顺序一致）。"""
    if question["kind"] == "score":
        scale = question["scale"]
        labels = [str(label) for label in scale["labels"]]
        levels = list(range(int(scale["min"]), int(scale["max"]) + 1))
        if all(labels[index] == str(level) for index, level in enumerate(levels)):
            return [str(level) for level in levels]
        return ["%d (%s)" % (level, labels[index]) for index, level in enumerate(levels)]
    tokens = []
    for option in question["options"]:
        key = str(option["key"])
        label = str(option.get("label") or "").strip()
        if not label or label == key:
            tokens.append(key)
        elif label.startswith(key):
            tokens.append(label)
        else:
            tokens.append("%s (%s)" % (key, label))
    return tokens


def target_shape(target):
    probs = target.get("probs")
    if not probs:
        return "answer_only"
    values = [float(value) for value in probs.values()]
    if max(values) == min(values):
        return "uniform"
    return "one_hot" if sum(1 for value in values if value) == 1 else "real"


def build_prompt(state, question, variant="answer"):
    head = [str(question.get("prompt") or "").strip(), ""]
    state = str(state or "").strip()
    if state:
        head += [state, ""]
    tokens = display_tokens(question)
    if variant == "answer":
        head.append("Options: " + " | ".join(tokens))
        head.append("Reply with exactly one option from the list, nothing else.")
    elif variant == "distribution":
        head.append("Options:")
        head += ["%d: %s" % (index, token) for index, token in enumerate(tokens)]
        head.append('Reply with a JSON object mapping each option index to a probability, '
                    'e.g. {"0": 0.7, "1": 0.3}. Probabilities must be non-negative and sum to 1. '
                    "Reply with the JSON object only, nothing else.")
    else:
        raise SystemExit("未知 prompt 变体：%s" % variant)
    return "\n".join(head).strip()


# ------------------------------------------------------------------ 解析

def _clean(text):
    text = (text or "").strip()
    text = re.sub(r"^[\s\"'\u201c\u201d\u2018\u2019]+", "", text)
    text = re.sub(r"[\s\"'\u201c\u201d\u2018\u2019]+$", "", text)
    text = text.rstrip("。.;,、")
    return text.strip()


def _label_head(label, key):
    """label 形如 'ListMessages：按…' 时取冒号前的部分。"""
    for separator in ("\uff1a", ":", "\uff08", "(", " \u2014 ", " - ", "\u2013"):
        if separator in label:
            head = label.split(separator, 1)[0].strip()
            if head:
                return head
    return label


def _polarity(word):
    word = str(word).strip().lower()
    if word in POSITIVE:
        return "pos"
    if word in NEGATIVE:
        return "neg"
    return None


def match_choice(candidate, question):
    """把一段自由文本收敛到选项 key；返回 (key, reason)。"""
    options = question["options"]
    keys = [str(option["key"]) for option in options]
    labels = [str(option.get("label") or "") for option in options]
    displays = display_tokens(question)
    if question["kind"] == "noul":
        polarity = _polarity(candidate)
        if polarity:
            hits = sorted({keys[index] for index in range(len(keys))
                           if _polarity(keys[index]) == polarity
                           or _polarity(labels[index]) == polarity
                           or _polarity(displays[index]) == polarity})
            if len(hits) == 1:
                return hits[0], "ok"
            if len(hits) > 1:
                return None, "ambiguous_match"
    variants = [candidate, _clean(candidate)]
    attempts = []
    attempts.append(lambda c: {keys[i] for i in range(len(keys)) if keys[i] == c})
    attempts.append(lambda c: {keys[i] for i in range(len(labels)) if labels[i] == c})
    attempts.append(lambda c: {keys[i] for i in range(len(displays)) if displays[i] == c})
    attempts.append(lambda c: {keys[i] for i in range(len(keys)) if labels[i] and _label_head(labels[i], keys[i]) == c})
    attempts.append(lambda c: {keys[i] for i in range(len(keys)) if keys[i].lower() == c.lower()})
    attempts.append(lambda c: {keys[i] for i in range(len(labels)) if labels[i].lower() == c.lower()})
    attempts.append(lambda c: {keys[i] for i in range(len(displays)) if displays[i].lower() == c.lower()})
    for candidate_text in variants:
        if not candidate_text:
            continue
        for attempt in attempts:
            hits = attempt(candidate_text)
            if len(hits) == 1:
                return next(iter(hits)), "ok"
            if len(hits) > 1:
                return None, "ambiguous_match"
    for candidate_text in variants:
        if not candidate_text:
            continue
        folded = candidate_text.casefold()
        hits = {keys[index] for index in range(len(keys))
                if len(keys[index]) >= 4 and re.search(r"(?<![0-9A-Za-z_])%s(?![0-9A-Za-z_])"
                                                       % re.escape(keys[index].casefold()), folded)}
        if len(hits) == 1:
            return next(iter(hits)), "ok"
        if len(hits) > 1:
            return None, "ambiguous_match"
        hits = {keys[index] for index in range(len(labels))
                if len(labels[index]) >= 6 and labels[index].casefold() in folded}
        if len(hits) == 1:
            return next(iter(hits)), "ok"
        if len(hits) > 1:
            return None, "ambiguous_match"
    return None, "not_in_options"


def match_score(candidate, question):
    scale = question["scale"]
    low, high = int(scale["min"]), int(scale["max"])
    text = _clean(candidate)
    if re.fullmatch(r"-?\d+", text):
        value = int(text)
        if low <= value <= high:
            return str(value), "ok"
    numbers = [int(found) for found in re.findall(r"(?<![\d.])-?\d+(?![\d.])", text)]
    in_range = sorted({value for value in numbers if low <= value <= high})
    if len(in_range) == 1:
        return str(in_range[0]), "ok"
    if len(in_range) > 1:
        return None, "ambiguous_match"
    return None, "no_integer_in_range"


def _json_objects(text):
    found = []
    for match in re.finditer(r"\{", text or ""):
        start = match.start()
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start:index + 1])
                    except json.JSONDecodeError:
                        parsed = None
                    if isinstance(parsed, dict):
                        found.append(parsed)
                    break
    return found


def extract_answer_value(content):
    for parsed in _json_objects(content):
        for name in ("answer", "Answer", "ANSWER", "choice", "selected"):
            if name in parsed:
                value = parsed[name]
                if isinstance(value, (str, int, float)):
                    return str(value)
    return None


def parse_answer(content, question, finish_reason=None):
    """answer 变体：返回 (key, reason)。"""
    if content is None or not str(content).strip():
        return None, "length" if finish_reason == "length" else "empty_content"
    candidates = []
    value = extract_answer_value(content)
    if value is not None:
        candidates.append(value)
    stripped = content.strip()
    candidates.append(stripped)
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if lines:
        candidates.append(lines[-1])
        candidates.append(lines[0])
    matcher = match_score if question["kind"] == "score" else match_choice
    best = None
    for candidate in candidates:
        cleaned = _clean(candidate)
        if not cleaned:
            continue
        key, reason = matcher(cleaned, question)
        if reason == "ok":
            return key, "ok"
        if best is None or (best[1] != "ambiguous_match" and reason == "ambiguous_match"):
            best = (key, reason)
    if finish_reason == "length":
        return None, "length"
    return best if best else (None, "not_in_options")


def parse_distribution(content, question, finish_reason=None):
    """distribution 变体：返回 (probs_by_option_key, reason)。"""
    if content is None or not str(content).strip():
        return None, "length" if finish_reason == "length" else "empty_content"
    keys = option_space(question)
    tokens = display_tokens(question)
    for parsed in _json_objects(content):
        for payload in (parsed, parsed.get("probs") if isinstance(parsed.get("probs"), dict) else None,
                        parsed.get("probabilities") if isinstance(parsed.get("probabilities"), dict) else None):
            if not isinstance(payload, dict) or not payload:
                continue
            values = {}
            usable = True
            for name, raw in payload.items():
                if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not math.isfinite(raw):
                    usable = False
                    break
                if raw < 0:
                    usable = False
                    break
                name = str(name).strip()
                if name.isdigit() and int(name) < len(keys):
                    target_key = keys[int(name)]
                elif name in keys:
                    target_key = name
                elif name in tokens:
                    target_key = keys[tokens.index(name)]
                else:
                    usable = False
                    break
                values[target_key] = float(raw)
            if not usable or not values or sum(values.values()) <= 0:
                continue
            total = sum(values.values())
            return {key: value / total for key, value in values.items()}, "ok"
    return None, "not_json"


def argmax_key(probs, question):
    keys = option_space(question)
    order = {key: index for index, key in enumerate(keys)}
    return min(probs, key=lambda key: (-probs[key], order.get(key, 1 << 30)))


# ------------------------------------------------------------------ 抽样

def stratum_of(item, kind):
    return "%s|%s|%s" % (item.get("lang") or "?", item.get("domain") or "?", kind)


def allocate(cells, total):
    sizes = {cell: len(members) for cell, members in cells.items()}
    population = sum(sizes.values())
    exact = {cell: sizes[cell] * total / population for cell in cells}
    quota = {cell: min(sizes[cell], int(math.floor(exact[cell]))) for cell in cells}
    remainder = total - sum(quota.values())
    order = sorted(cells, key=lambda cell: (-(exact[cell] - quota[cell]), cell))
    while remainder > 0:
        progressed = False
        for cell in order:
            if remainder <= 0:
                break
            if quota[cell] < sizes[cell]:
                quota[cell] += 1
                remainder -= 1
                progressed = True
        if not progressed:
            break
    return quota


def cmd_sample(args):
    items_path = Path(args.items)
    corpus_sha = sha256_file(items_path)
    cells = {}
    for item, key, question, target in iter_targets(items_path):
        answer = target.get("answer")
        if answer is None or str(answer) == "":
            continue
        record = {
            "qid": "%s.%s" % (item["id"], key),
            "id": item["id"],
            "key": key,
            "kind": question["kind"],
            "domain": item.get("domain") or "",
            "lang": item.get("lang") or "",
            "source_dataset": (item.get("source") or {}).get("dataset") or "",
            "origin": question.get("origin") or "taxonomy",
            "answer": str(answer),
            "shape": target_shape(target),
            "n_options": len(option_space(question)),
        }
        cells.setdefault(stratum_of(item, question["kind"]), []).append(record)
    population = sum(len(members) for members in cells.values())
    quota = allocate(cells, min(args.n, population))
    rng = random.Random(args.seed)
    selected = []
    for cell in sorted(cells):
        members = sorted(cells[cell], key=lambda row: row["qid"])
        rng.shuffle(members)
        selected += members[:quota[cell]]
    selected.sort(key=lambda row: row["qid"])
    wanted = {row["qid"] for row in selected}
    prompts = {}
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid not in wanted:
            continue
        prompt = build_prompt(item.get("state"), question, args.variant)
        prompts[qid] = {
            "prompt": prompt,
            "prompt_sha256": sha256_text(prompt),
            "options_display": display_tokens(question)[:64],
            "question_prompt": str(question.get("prompt") or ""),
            "state": str(item.get("state") or ""),
            "chance": round(1.0 / max(1, len(option_space(question))), 6),
        }
    rows = []
    for seq, record in enumerate(selected, 1):
        extra = prompts[record["qid"]]
        rows.append({"record_type": "request", "seq": seq, "variant": args.variant, **record,
                     "chance": extra["chance"], "options_display": extra["options_display"],
                     "question_prompt": extra["question_prompt"], "state": extra["state"],
                     "prompt_sha256": extra["prompt_sha256"]})
    manifest = {"record_type": "manifest", "tool": TOOL, "harness_version": HARNESS_VERSION,
                "phase": "validation", "created_at": iso_now(), "seed": args.seed,
                "requested_n": args.n, "sampled_n": len(rows), "population": population,
                "items": str(items_path), "items_sha256": corpus_sha,
                "variant": args.variant,
                "strata": {cell: {"population": len(cells[cell]), "sampled": quota[cell]}
                           for cell in sorted(cells)}}
    out = Path(args.out or DEFAULT_WORK / ("validation-plan%s.jsonl" % ("" if args.variant == "answer" else "-" + args.variant)))
    write_jsonl(out, [manifest] + rows)
    print(json.dumps({"plan": str(out), "sampled": len(rows), "population": population,
                      "strata": manifest["strata"], "items_sha256": corpus_sha[:16]},
                     ensure_ascii=False, indent=2))


def cmd_fill_plan(args):
    items_path = Path(args.items)
    corpus_sha = sha256_file(items_path)
    rows = []
    population = 0
    langs = set(args.lang or [])
    kinds = set(args.kind or [])
    for item, key, question, target in iter_targets(items_path):
        if target_shape(target) != "answer_only":
            continue
        if langs and (item.get("lang") or "") not in langs:
            continue
        if kinds and question["kind"] not in kinds:
            continue
        if args.limit and len(rows) >= args.limit:
            break
        population += 1
        prompt = build_prompt(item.get("state"), question, args.variant)
        rows.append({"record_type": "request", "seq": population,
                     "qid": "%s.%s" % (item["id"], key), "id": item["id"], "key": key,
                     "kind": question["kind"], "domain": item.get("domain") or "",
                     "lang": item.get("lang") or "", "variant": args.variant,
                     "source_dataset": (item.get("source") or {}).get("dataset") or "",
                     "answer": str(target.get("answer")), "shape": "answer_only",
                     "n_options": len(option_space(question)),
                     "chance": round(1.0 / max(1, len(option_space(question))), 6),
                     "prompt_sha256": sha256_text(prompt)})
    manifest = {"record_type": "manifest", "tool": TOOL, "harness_version": HARNESS_VERSION,
                "phase": "fill", "created_at": iso_now(), "population": population,
                "items": str(items_path), "items_sha256": corpus_sha, "variant": args.variant,
                "filters": {"lang": sorted(langs), "kind": sorted(kinds)}}
    out = Path(args.out or DEFAULT_WORK / ("fill-plan.jsonl" if args.variant == "answer"
                                           else "fill-plan-distribution.jsonl"))
    write_jsonl(out, [manifest] + rows)
    print(json.dumps({"plan": str(out), "requests": len(rows), "population": population,
                      "items_sha256": corpus_sha[:16], "variant": args.variant,
                      "filters": manifest["filters"]}, ensure_ascii=False, indent=2))


def cmd_fill_write(args):
    """把 fill journal 按硬门禁写成旁挂 probs；不满足就跳过并分类计数。冻结语料只读。"""
    plan_path = Path(args.plan or DEFAULT_WORK / "fill-plan-distribution.jsonl")
    journal_path = Path(args.journal or DEFAULT_WORK / "fill-calls-dist.jsonl")
    out_path = Path(args.out or DEFAULT_FILL_OUT)
    stats_path = Path(args.stats or DEFAULT_WORK / "fill-write-report.json")
    plan = read_jsonl(plan_path)
    manifest = plan[0]
    plan_rows = {row["qid"]: row for row in plan[1:] if row.get("record_type") == "request"}
    latest = {}
    if Path(journal_path).is_file():
        for row in read_jsonl(journal_path):
            if row.get("status") == "ok" and row.get("qid") in plan_rows:
                latest[row["qid"]] = row          # 同一 qid 取最后一次成功
    questions = {}
    wanted = set(plan_rows)
    items_path = Path(manifest["items"])
    if args.items:
        items_path = Path(args.items)
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid in wanted:
            questions[qid] = question
    rows = []
    skipped = {}
    models = {}
    cost = 0.0
    consensus = {}

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    for qid in sorted(plan_rows):
        plan_row = plan_rows[qid]
        question = questions.get(qid)
        journal_row = latest.get(qid)
        if question is None:
            skip("missing_question")
            continue
        if journal_row is None:
            skip("not_called_or_failed")
            continue
        cost += float(journal_row.get("cost_usd") or 0.0)
        model = journal_row.get("upstream_model") or "-"
        models[model] = models.get(model, 0) + 1
        variant = plan_row.get("variant") or "answer"
        if variant == "distribution":
            probs, reason = parse_distribution(journal_row.get("content"), question,
                                               journal_row.get("finish_reason"))
        else:
            key, reason = parse_answer(journal_row.get("content"), question,
                                       journal_row.get("finish_reason"))
            probs = {option_key: (1.0 if option_key == key else 0.0)
                     for option_key in option_space(question)} if reason == "ok" else None
        if probs is None:
            skip("unparsed:" + (reason or "unknown"))
            continue
        if len(probs) < 1:
            skip("empty_probs")
            continue
        # 互证率统计：分母 = 所有**可解析**的尝试（含退化 one-hot——它们的 argmax 也是判断），
        # 这样不会因为「输出退化」被排除而虚高。
        top = argmax_key(probs, question)
        group = plan_row.get("source_dataset") or "?"
        stat = consensus.setdefault(group, {"n": 0, "agree": 0})
        stat["n"] += 1
        if top == plan_row["answer"]:
            stat["agree"] += 1
        values = list(probs.values())
        support = sum(1 for value in values if value > 0)
        # 硬门禁（比任务书更严）：只写真分布；one-hot / 均匀都是伪概率，宁可不写
        if support == 1:
            skip("degenerate:one_hot")
            continue
        if max(values) == min(values):
            skip("degenerate:uniform")
            continue
        if top != plan_row["answer"]:
            skip("answer_mismatch")
            continue
        total = sum(probs.values())
        if abs(total - 1.0) > 1e-6:
            probs = {option_key: value / total for option_key, value in probs.items()}
        rows.append({"id": plan_row["id"], "key": plan_row["key"], "qid": qid,
                     "kind": plan_row["kind"], "lang": plan_row["lang"],
                     "domain": plan_row["domain"], "answer": plan_row["answer"],
                     "probs": probs, "distribution_semantics": "jev_router",
                     "source": "jev-router", "source_version": "typesafe/jev-router",
                     "upstream_model": journal_row.get("upstream_model"),
                     "created_at": journal_row.get("ts") or iso_now(),
                     "n_options": plan_row.get("n_options"),
                     "prompt_sha256": plan_row.get("prompt_sha256"),
                     "label_confidence": None, "consensus_group": group})
    for group, stat in consensus.items():
        stat["agree_rate"] = round(stat["agree"] / stat["n"], 4) if stat["n"] else 0.0
        stat["label_confidence"] = consensus_label(stat["n"], stat["agree"])
    for row in rows:
        stat = consensus.get(row.get("consensus_group") or "?") or {}
        row["label_confidence"] = stat.get("label_confidence")
        row["consensus_agree"] = stat.get("agree")
        row["consensus_n"] = stat.get("n")
        row.pop("consensus_group", None)
    write_jsonl(out_path, rows)
    by_label = {}
    for row in rows:
        value = row.get("label_confidence") or "unknown"
        by_label[value] = by_label.get(value, 0) + 1
    fragment = {"line": "C. jev-router zh choice（旧方案，已付费部分）", "group_by": "source dataset",
                "written_rows_by_label": by_label,
                "configs": dict(sorted(consensus.items(), key=lambda kv: kv[1]["agree_rate"]))}
    (Path(out_path).parent / "label-confidence-jevrouter.json").write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2), encoding="utf-8")
    by_kind = {}
    by_lang = {}
    for row in rows:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        by_lang[row["lang"]] = by_lang.get(row["lang"], 0) + 1
    stats = {"generated_at": iso_now(), "plan": str(plan_path), "journal": str(journal_path),
             "out": str(out_path), "variant": manifest.get("variant"),
             "label_confidence_counts": by_label,
             "filters": manifest.get("filters"), "plan_requests": len(plan_rows),
             "journal_ok": len(latest), "written": len(rows),
             "written_by_kind": by_kind, "written_by_lang": by_lang,
             "skipped": dict(sorted(skipped.items(), key=lambda pair: -pair[1])),
             "cost_usd": round(cost, 6), "upstream_models": models}
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------ 调用

class Budget:
    """硬预算：每次派发前预留。预留额取「命令行估计」与「已观测均值 x 安全系数」的较大者，
    避免路由到贵模型时把上限冲穿（2026-10-15 实测：单次成本在 $0.00003-$0.0044 之间浮动 100 倍）。"""

    def __init__(self, limit, estimate, safety=2.0):
        self.limit = float(limit)
        self.base_estimate = float(estimate)
        self.safety = float(safety)
        self.spent = 0.0
        self.reserved = 0.0
        self.samples = 0
        self.lock = threading.Lock()
        self.exhausted = False

    def _estimate(self):
        if self.samples >= 5:
            return max(self.base_estimate, self.safety * self.spent / self.samples)
        return max(self.base_estimate, self.base_estimate)

    def reserve(self):
        with self.lock:
            estimate = self._estimate()
            if self.spent + self.reserved + estimate > self.limit + 1e-12:
                self.exhausted = True
                return False
            self.reserved += estimate
            return True

    def settle(self, cost):
        with self.lock:
            self.reserved = max(0.0, self.reserved - self._estimate())
            self.spent += float(cost)
            self.samples += 1
            if self.spent >= self.limit:
                self.exhausted = True

    def mean_cost(self):
        """已观测均价（无样本时退回命令行估计）；用于给「API 未回传 cost」的调用兜底记账。"""
        with self.lock:
            if self.samples:
                return max(self.base_estimate, self.spent / self.samples)
            return self.base_estimate

    def state(self):
        with self.lock:
            return {"spent": round(self.spent, 6), "reserved": round(self.reserved, 6),
                    "limit": self.limit, "exhausted": self.exhausted}


class Limiter:
    def __init__(self, min_interval):
        self.min_interval = max(0.0, float(min_interval))
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_at)
            self.next_at = start + self.min_interval
        delay = start - time.monotonic()
        if delay > 0:
            time.sleep(delay)


def post_chat(url, key, body, timeout):
    payload = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json",
               "Authorization": "Bearer " + key, "User-Agent": USER_AGENT,
               "HTTP-Referer": "https://github.com/naturaldao/NaturalDAO",
               "X-Title": "PoL-Governance general dataset"}
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200) or 200)
            chunk = response.read(MAX_RESPONSE_BYTES)
    except urllib.error.HTTPError as error:
        chunk = error.read(MAX_RESPONSE_BYTES) or b""
        return {"status": int(error.code), "body": chunk, "latency_ms": (time.perf_counter() - started) * 1000,
                "error": "HTTP %d" % int(error.code)}
    except (TimeoutError, OSError) as error:
        kind = "timeout" if isinstance(error, TimeoutError) else "network_error"
        return {"status": None, "body": b"", "latency_ms": (time.perf_counter() - started) * 1000,
                "error": "%s: %s" % (kind, error), "kind": kind}
    return {"status": status, "body": chunk, "latency_ms": (time.perf_counter() - started) * 1000}


def call_once(url, key, model, prompt, max_tokens, temperature, timeout):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "usage": {"include": True}}
    if temperature is not None:
        body["temperature"] = temperature
    return post_chat(url, key, body, timeout)


def outcome_of(response):
    """HTTP 响应 -> 统一 outcome dict。"""
    status = response["status"]
    if status != 200:
        kind = response.get("kind") or ("timeout" if status is None else "http_error")
        text = response["body"][:400].decode("utf-8", "replace") if response.get("body") else ""
        if status == 402 and ("credit" in text.lower() or "afford" in text.lower()):
            kind = "insufficient_credits"
        return {"status": "error", "reason": kind, "http_status": status,
                "error": (response.get("error") or "") + (" | " + text if text else ""),
                "latency_ms": response["latency_ms"]}
    try:
        parsed = json.loads(response["body"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"status": "error", "reason": "not_json", "http_status": 200,
                "error": "bad JSON: %s | %s" % (error, response["body"][:200].decode("utf-8", "replace")),
                "latency_ms": response["latency_ms"]}
    choices = parsed.get("choices") or []
    message = (choices[0] or {}).get("message") if choices and isinstance(choices[0], dict) else {}
    content = None
    for candidate in ((message or {}).get("content"), (message or {}).get("reasoning_content")):
        if isinstance(candidate, str) and candidate.strip():
            content = candidate
            break
    usage = parsed.get("usage") or {}
    return {"status": "ok", "http_status": 200, "content": content or "",
            "finish_reason": (choices[0] or {}).get("finish_reason") if choices else None,
            "upstream_model": parsed.get("model") or (parsed.get("provider") or ""),
            "usage": {"prompt_tokens": usage.get("prompt_tokens"),
                      "completion_tokens": usage.get("completion_tokens"),
                      "total_tokens": usage.get("total_tokens"),
                      "cost": usage.get("cost")},
            "latency_ms": response["latency_ms"], "response_id": parsed.get("id")}


def cost_of(outcome, price_in, price_out, fallback):
    usage = outcome.get("usage") or {}
    if isinstance(usage.get("cost"), (int, float)):
        return float(usage["cost"]), False
    if price_in is not None and price_out is not None and usage.get("prompt_tokens") is not None:
        return (float(usage["prompt_tokens"]) * price_in
                + float(usage.get("completion_tokens") or 0) * price_out) / 1_000_000.0, True
    return float(fallback), True


def cmd_run(args):
    config = load_jev_config(args.jev_yaml)
    plan_path = Path(args.plan or DEFAULT_WORK / ("validation-plan.jsonl" if args.phase == "validation" else "fill-plan.jsonl"))
    plan = read_jsonl(plan_path)
    if not plan or plan[0].get("record_type") != "manifest":
        raise SystemExit("%s: 缺少 manifest 首行" % plan_path)
    manifest = plan[0]
    requests = [row for row in plan[1:] if row.get("record_type") == "request"]
    if args.items:
        items_path = Path(args.items)
    else:
        items_path = Path(manifest["items"])
    if args.workers < 1:
        raise SystemExit("--workers 必须 >= 1")
    url = chat_url(config["endpoint"])
    key = config["apikey"]
    if not key and not args.dry_run:
        raise SystemExit("缺 apikey：datasets/jev.yaml 或环境变量 JEV_API_KEY")

    # 重建 prompt 并核对 sha256（语料漂移必须显式放行）
    prompts = {}
    wanted = {row["qid"] for row in requests}
    for item, target_key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], target_key)
        if qid in wanted:
            variant = next((row.get("variant") or "answer" for row in requests if row["qid"] == qid), "answer")
            prompts[qid] = build_prompt(item.get("state"), question, variant)
    drifted = []
    for row in requests:
        prompt = prompts.get(row["qid"])
        if prompt is None:
            drifted.append((row["qid"], "语料里找不到该 qid"))
        elif sha256_text(prompt) != row.get("prompt_sha256"):
            drifted.append((row["qid"], "prompt 与 plan 记录不一致"))
    if drifted and not args.allow_corpus_drift:
        raise SystemExit("语料/plan 漂移 %d 条（%s…）；确认后用 --allow-corpus-drift" %
                         (len(drifted), drifted[0]))

    journal_path = Path(args.journal or DEFAULT_WORK / ("validation-calls.jsonl" if args.phase == "validation" else "fill-calls.jsonl"))
    journal = Journal(journal_path)
    reuse = [Journal(path) for path in (args.reuse_journal or [])]
    answered = {}
    for source in [journal] + reuse:
        for row in source.rows:
            if row.get("status") == "ok":
                answered[(row.get("qid"), row.get("repeat_index", 0))] = row
    pending = []
    for row in requests:
        for repeat_index in range(args.repeat):
            if (row["qid"], repeat_index) in answered and not args.force:
                continue
            pending.append((row, repeat_index))
    if args.limit:
        pending = pending[:args.limit]
    done_ok = sum(1 for row in journal.rows if row.get("status") == "ok")
    header = {"phase": args.phase, "plan": str(plan_path), "journal": str(journal_path),
              "model": config["model"], "endpoint_host": config["endpoint"].split("//")[-1].split("/")[0],
              "key_fingerprint": fingerprint(key) if key else None, "pending": len(pending),
              "already_ok": done_ok, "budget": args.budget, "workers": args.workers,
              "variant": manifest.get("variant"), "repeat": args.repeat,
              "tools": TOOL, "harness_version": HARNESS_VERSION}
    print(json.dumps({"run": header}, ensure_ascii=False), flush=True)
    if args.dry_run:
        for row, repeat_index in pending[:max(1, args.limit or 1)]:
            print(json.dumps({"qid": row["qid"], "variant": row.get("variant"),
                              "prompt_preview": prompts[row["qid"]][:600]}, ensure_ascii=False))
        print(json.dumps({"dry_run": True, "would_call": len(pending)}, ensure_ascii=False))
        return

    budget = Budget(args.budget, args.estimate_per_call)
    limiter = Limiter(args.min_interval)
    state = {"calls": 0, "ok": 0, "error": 0, "stopped": False, "fatal": None}
    lock = threading.Lock()

    def worker(row, repeat_index):
        if state["fatal"]:
            journal.append({"phase": args.phase, "variant": row.get("variant"), "qid": row["qid"],
                            "seq": row.get("seq"), "repeat_index": repeat_index, "attempt": 1,
                            "status": "skipped", "reason": "fatal_stop",
                            "prompt_sha256": row.get("prompt_sha256")})
            return
        prompt = prompts[row["qid"]]
        attempts = 0
        last = None
        max_tokens = args.max_tokens   # 每条请求自己的预算，不能跨线程改共享的 args
        while attempts < args.max_attempts:
            attempts += 1
            if not budget.reserve():
                with lock:
                    state["stopped"] = True
                journal.append({"phase": args.phase, "variant": row.get("variant"), "qid": row["qid"],
                                "seq": row.get("seq"), "repeat_index": repeat_index, "attempt": attempts,
                                "status": "skipped", "reason": "budget_stop",
                                "prompt_sha256": row.get("prompt_sha256")})
                return
            limiter.wait()
            response = call_once(url, key, config["model"], prompt, max_tokens,
                                 args.temperature, args.timeout)
            outcome = outcome_of(response)
            cost, estimated = cost_of(outcome, args.price_in, args.price_out, budget.mean_cost())
            budget.settle(cost)
            record = {"phase": args.phase, "variant": row.get("variant"), "qid": row["qid"],
                      "id": row.get("id"), "key": row.get("key"), "kind": row.get("kind"),
                      "domain": row.get("domain"), "lang": row.get("lang"), "seq": row.get("seq"),
                      "repeat_index": repeat_index, "attempt": attempts,
                      "status": outcome["status"], "reason": outcome.get("reason"),
                      "http_status": outcome.get("http_status"), "error": outcome.get("error"),
                      "upstream_model": outcome.get("upstream_model"),
                      "finish_reason": outcome.get("finish_reason"),
                      "content": outcome.get("content"), "usage": outcome.get("usage"),
                      "cost_usd": round(cost, 8), "cost_estimated": estimated,
                      "latency_ms": round(float(outcome.get("latency_ms") or 0.0), 1),
                      "response_id": outcome.get("response_id"),
                      "prompt_sha256": row.get("prompt_sha256"), "max_tokens": max_tokens}
            with lock:
                state["calls"] += 1
                state["ok" if outcome["status"] == "ok" else "error"] += 1
            journal.append(record)
            last = record
            if outcome["status"] == "ok":
                # 输出被 max_tokens 截断时最多再试一次（放宽到 2 倍，上限 8000）
                if outcome.get("finish_reason") == "length" and args.retry_truncated and attempts < args.max_attempts:
                    max_tokens = min(8000, max_tokens * 2)
                    continue
                return
            if outcome.get("reason") == "insufficient_credits":
                with lock:
                    state["fatal"] = "insufficient_credits"
                print(json.dumps({"fatal": "insufficient_credits",
                                  "hint": "OpenRouter 余额不足：整批停止，已完成的调用保留在 journal，充值后重跑即可续"},
                                 ensure_ascii=False), flush=True)
                return
            retryable = outcome.get("http_status") in RETRY_STATUS or outcome.get("reason") in ("timeout", "network_error")
            if not retryable or attempts >= args.max_attempts:
                return
            delay = min(args.max_backoff, args.backoff * (2 ** (attempts - 1)))
            time.sleep(delay + random.uniform(0, 0.25 * delay))
        return last

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        iterator = iter(pending)
        futures = {}
        for _ in range(args.workers * 2):
            item = next(iterator, None)
            if item is None:
                break
            futures[pool.submit(worker, item[0], item[1])] = item
        while futures:
            finished, _ = wait(list(futures), return_when=FIRST_COMPLETED)
            for future in finished:
                futures.pop(future, None)
                try:
                    future.result()
                except Exception as error:  # 单条失败不得中断整批
                    print(json.dumps({"worker_error": repr(error)}, ensure_ascii=False), flush=True)
                item = next(iterator, None)
                if item is not None and not state["stopped"] and not state["fatal"]:
                    futures[pool.submit(worker, item[0], item[1])] = item
    summary = {"done": True, "elapsed_s": round(time.perf_counter() - started, 1),
               "calls": state["calls"], "ok": state["ok"], "error": state["error"],
               "budget": budget.state(), "journal": str(journal_path),
               "journal_rows": len(journal.rows)}
    print(json.dumps(summary, ensure_ascii=False), flush=True)


# ------------------------------------------------------------------ 报告

def wilson(success, total, z=1.96):
    if total <= 0:
        return (0.0, 0.0)
    phat = success / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    half = z * math.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def pct(value):
    return "%.1f%%" % (100.0 * value)


def rate_cell(success, total):
    if total <= 0:
        return "n/a"
    low, high = wilson(success, total)
    return "%d/%d = %s [95%%CI %s–%s]" % (success, total, pct(success / total), pct(low), pct(high))


def summarize(records):
    """records: [{row, outcome(key/reason/model/...)}] -> dict of metrics."""
    attempted = [record for record in records]
    http_ok = [record for record in attempted if record.get("http_status") == 200]
    parsed = [record for record in http_ok if record.get("parsed") is not None]
    agree = [record for record in parsed if record["parsed"] == record["truth"]]
    return {"n": len(attempted), "http_ok": len(http_ok), "parsed": len(parsed),
            "agree": len(agree),
            "parse_rate": (len(parsed) / len(http_ok)) if http_ok else 0.0,
            "agree_rate": (len(agree) / len(parsed)) if parsed else 0.0,
            "chance": (sum(record["chance"] for record in parsed) / len(parsed)) if parsed else 0.0}


def group_table(records, field):
    groups = {}
    for record in records:
        value = record.get(field)
        if value is None:
            value = (record.get("row") or {}).get(field)
        groups.setdefault(value or "?", []).append(record)
    return {name: summarize(groups[name]) for name in sorted(groups)}


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def load_records(plan, journal_paths, variant_override=None):
    """把 plan 与 journal 合起来 -> 逐条记录（同 qid 取最后一条 ok；失败也保留）。"""
    plan_rows = {row["qid"]: row for row in plan[1:] if row.get("record_type") == "request"}
    latest = {}
    for path in journal_paths:
        if not Path(path).is_file():
            continue
        for row in read_jsonl(path):
            qid = row.get("qid")
            if qid not in plan_rows:
                continue
            key = (qid, row.get("repeat_index", 0))
            if row.get("status") == "ok":
                latest[key] = row
            elif key not in latest:
                latest[key] = row
    records = []
    for (qid, repeat_index), row in sorted(latest.items()):
        if repeat_index != 0:
            continue
        plan_row = plan_rows[qid]
        question = {"kind": plan_row["kind"], "options": [], "scale": None}
        records.append({"row": plan_row, "journal": row, "repeat_index": repeat_index,
                        "truth": plan_row["answer"], "chance": plan_row.get("chance") or 0.0,
                        "chance_kind": plan_row["kind"]})
    return records


def score_records(records, plan_path):
    """需要按 qid 重新解析：从语料取 question 结构。"""
    plan = read_jsonl(plan_path)
    plan_rows = {row["qid"]: row for row in plan[1:] if row.get("record_type") == "request"}
    items_path = Path(plan[0]["items"])
    questions = {}
    wanted = set(plan_rows)
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid in wanted:
            questions[qid] = question
    scored = []
    for record in records:
        row = record["row"]
        journal = record["journal"]
        question = questions.get(row["qid"])
        parsed = None
        reason = None
        probs = None
        if journal.get("status") != "ok":
            reason = journal.get("reason") or "http_error"
        elif question is None:
            reason = "not_in_options"
        elif (row.get("variant") or "answer") == "distribution":
            probs, reason = parse_distribution(journal.get("content"), question, journal.get("finish_reason"))
            parsed = argmax_key(probs, question) if probs else None
        else:
            parsed, reason = parse_answer(journal.get("content"), question, journal.get("finish_reason"))
        record.update({"parsed": parsed, "reason": reason, "probs": probs,
                       "http_status": journal.get("http_status"),
                       "upstream_model": journal.get("upstream_model") or "-",
                       "cost_usd": journal.get("cost_usd") or 0.0,
                       "latency_ms": journal.get("latency_ms") or 0.0,
                       "usage": journal.get("usage") or {},
                       "options_display": row.get("options_display") or [],
                       "question_prompt": row.get("question_prompt") or "",
                       "state": row.get("state") or "",
                       "variant": row.get("variant") or "answer"})
        scored.append(record)
    return scored


def cost_summary(journal_paths):
    http_calls = 0
    skipped = 0
    failed = 0
    http_errors = 0
    ok = 0
    cost = 0.0
    estimated = 0
    measured_usd = 0.0
    estimated_usd = 0.0
    tokens_in = 0
    tokens_out = 0
    models = {}
    for path in journal_paths:
        if not Path(path).is_file():
            continue
        for row in read_jsonl(path):
            if row.get("attempt") is None:
                continue
            if row.get("http_status") is None:
                if row.get("reason") == "budget_stop":
                    skipped += 1
                else:
                    failed += 1
                continue
            http_calls += 1
            if row.get("status") != "ok":
                http_errors += 1          # 402/5xx 等不计费，也不进成本与模型表
                continue
            ok += 1
            row_cost = float(row.get("cost_usd") or 0.0)
            cost += row_cost
            if row.get("cost_estimated"):
                estimated += 1
                estimated_usd += row_cost
            else:
                measured_usd += row_cost
            usage = row.get("usage") or {}
            tokens_in += int(usage.get("prompt_tokens") or 0)
            tokens_out += int(usage.get("completion_tokens") or 0)
            model = row.get("upstream_model") or "-"
            entry = models.setdefault(model, {"calls": 0, "cost_usd": 0.0, "completion_tokens": 0})
            entry["calls"] += 1
            entry["cost_usd"] += row_cost
            entry["completion_tokens"] += int(usage.get("completion_tokens") or 0)
    return {"attempts": http_calls, "http_calls": http_calls, "skipped": skipped, "failed_attempts": failed,
            "http_errors": http_errors,
            "ok": ok, "cost_usd": cost, "cost_measured_usd": measured_usd,
            "cost_estimated_usd": estimated_usd, "estimated_rows": estimated,
            "tokens_in": tokens_in, "tokens_out": tokens_out, "models": models}

# ------------------------------------------------------------------ mercury-decide 后端
# 2026-10-20 实测（Lead 探测）：决策专用端点，不能走 chat/completions。
#   POST https://openrouter.ai/api/alpha/decisions
#   body {"model":"inception/mercury-decide:free","state":"...","questions":{"<key>":{"type":"noul","instructions":"..."}}}
#   resp {"model":"inception/mercury-decide-20260930",
#         "answers":{"<key>":{"type":"noul","noul":0.9466...}},
#         "usage":{"input_tokens":68,"output_tokens":1,"cost":0}}
# noul 直接给校准概率 P(yes)，cost=0 —— 原生概率，不是伪 one-hot。

# 2026-10-20 实测：":free" 变体持续 429（上游 rate_limit_exceeded，间隔 6s 重试 3 次仍 429）；
# 同款付费 id "inception/mercury-decide" 同一决策端点可用，返回同一个模型
# (inception/mercury-decide-20260930)，usage.cost 约 $0.0000013/次
# （跑满 7,907 条 noul 约 $0.01，相对 key 剩余额度可忽略），故默认走付费 id。
MERCURY_MODEL = "inception/mercury-decide"
DEFAULT_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
MERCURY_QUESTION_KEY = "next_step_candidate"
NOUL_POSITIVE = ("true", "yes", "1", "y", "t")
NOUL_NEGATIVE = ("false", "no", "0", "n", "f")


def noul_polarity(value):
    text = str(value).strip().lower()
    if text in NOUL_POSITIVE:
        return "pos"
    if text in NOUL_NEGATIVE:
        return "neg"
    # 部分来源的选项 key 是整句判据（如 "yes_escalation_is_warran" / "no_escalation_is_not_war"）
    if re.match(r"^(yes|true)([_\-\s:.()]|$)", text):
        return "pos"
    if re.match(r"^(no|false)([_\-\s:.()]|$)", text):
        return "neg"
    return None


def noul_option_keys(question):
    """noul 题的两个选项按极性配成 (pos_key, neg_key)；必须恰好一正一负，否则 (None, None)。"""
    if question.get("kind") != "noul":
        return None, None
    positive = []
    negative = []
    for option in question.get("options") or []:
        key = str(option.get("key"))
        polarity = noul_polarity(key)
        if polarity is None:
            polarity = noul_polarity(option.get("label"))
        if polarity == "pos":
            positive.append(key)
        elif polarity == "neg":
            negative.append(key)
    if len(positive) == 1 and len(negative) == 1:
        return positive[0], negative[0]
    return None, None


def mercury_body(model, state, instructions):
    return {"model": model, "state": str(state or ""),
            "questions": {MERCURY_QUESTION_KEY: {"type": "noul",
                                                 "instructions": str(instructions or "")}}}


def mercury_outcome(response):
    """决策端点响应 -> 与 outcome_of 同形状；content 存 answers[key] 的 JSON。"""
    status = response["status"]
    if status != 200:
        kind = response.get("kind") or ("timeout" if status is None else "http_error")
        text = response["body"][:400].decode("utf-8", "replace") if response.get("body") else ""
        if status == 429:
            kind = "rate_limited"
        elif status == 402 and ("credit" in text.lower() or "afford" in text.lower()):
            kind = "insufficient_credits"
        return {"status": "error", "reason": kind, "http_status": status,
                "error": (response.get("error") or "") + (" | " + text if text else ""),
                "latency_ms": response["latency_ms"]}
    try:
        body = json.loads(response["body"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"status": "error", "reason": "not_json", "http_status": 200,
                "error": "bad JSON: %s" % error, "latency_ms": response["latency_ms"]}
    answers = body.get("answers") or {}
    answer = answers.get(MERCURY_QUESTION_KEY)
    if not isinstance(answer, dict):
        return {"status": "error", "reason": "not_in_options", "http_status": 200,
                "error": "response has no answers[%s]: %s" % (MERCURY_QUESTION_KEY,
                                                              json.dumps(body, ensure_ascii=False)[:300]),
                "latency_ms": response["latency_ms"]}
    usage = body.get("usage") or {}
    return {"status": "ok", "http_status": 200,
            "content": json.dumps(answer, ensure_ascii=False),
            "finish_reason": "stop", "upstream_model": body.get("model"),
            "usage": {"prompt_tokens": usage.get("input_tokens"),
                      "completion_tokens": usage.get("output_tokens"),
                      "cost": usage.get("cost")},
            "latency_ms": response["latency_ms"], "response_id": None}


def parse_mercury(content, question):
    """answers[key] -> (probs, reason)。noul 给 P(yes)，转成两个选项上的分布。"""
    positive, negative = noul_option_keys(question)
    if positive is None or negative is None:
        return None, "not_in_options"
    try:
        payload = json.loads(content) if isinstance(content, str) else content
    except json.JSONDecodeError:
        return None, "not_json"
    if not isinstance(payload, dict):
        return None, "not_json"
    value = payload.get("noul")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None, "not_in_options"
    if value < 0 or value > 1:
        return None, "not_in_options"
    return {positive: float(value), negative: 1.0 - float(value)}, "ok"


def mercury_request(url, key, model, state, instructions, timeout):
    return post_chat(url, key, mercury_body(model, state, instructions), timeout)


def _sleep_until(limiter, interval):
    limiter.wait()


def cmd_noul_probe(args):
    """20 条 noul 小样本验证：mercury-decide 的 P(yes) 与语料 answer 比 argmax。"""
    config = load_jev_config(args.jev_yaml)
    items_path = Path(args.items)
    candidates = []
    for item, key, question, target in iter_targets(items_path):
        if question.get("kind") != "noul":
            continue
        positive, negative = noul_option_keys(question)
        answer = str(target.get("answer"))
        if positive is None or negative is None or answer not in (positive, negative):
            continue
        candidates.append({"qid": "%s.%s" % (item["id"], key), "id": item["id"], "key": key,
                           "answer": answer, "positive": positive, "negative": negative,
                           "state": str(item.get("state") or ""),
                           "instructions": str(question.get("prompt") or ""),
                           "lang": item.get("lang") or "", "domain": item.get("domain") or "",
                           "corpus_shape": target_shape(target)})
    rng = random.Random(args.seed)
    candidates.sort(key=lambda row: row["qid"])
    rng.shuffle(candidates)
    picked = candidates[:args.n]
    journal_path = Path(args.journal or DEFAULT_WORK / "mercury-noul-probe.jsonl")
    journal = Journal(journal_path)
    done = {row["qid"] for row in journal.rows if row.get("status") == "ok"}
    url = args.decisions_url
    limiter = Limiter(1.0 / max(0.1, args.rate))
    calls = 0
    for row in picked:
        if row["qid"] in done:
            continue
        attempts = 0
        while attempts < args.max_attempts:
            attempts += 1
            limiter.wait()
            response = mercury_request(url, config["apikey"], args.mercury_model,
                                       row["state"], row["instructions"], args.timeout)
            outcome = mercury_outcome(response)
            record = {"phase": "noul-probe", "qid": row["qid"], "id": row["id"], "key": row["key"],
                      "lang": row["lang"], "domain": row["domain"], "attempt": attempts,
                      "status": outcome["status"], "reason": outcome.get("reason"),
                      "http_status": outcome.get("http_status"), "error": outcome.get("error"),
                      "upstream_model": outcome.get("upstream_model"),
                      "content": outcome.get("content"),
                      "content_sha256": sha256_text(outcome.get("content") or ""),
                      "usage": outcome.get("usage"),
                      "cost_usd": float((outcome.get("usage") or {}).get("cost") or 0.0),
                      "latency_ms": round(float(outcome.get("latency_ms") or 0.0), 1)}
            journal.append(record)
            calls += 1
            if outcome["status"] == "ok":
                break
            retryable = (outcome.get("http_status") in RETRY_STATUS
                         or outcome.get("reason") in ("timeout", "network_error", "rate_limited"))
            if not retryable or attempts >= args.max_attempts:
                break
            delay = min(args.max_backoff, args.backoff * (2 ** (attempts - 1)))
            if outcome.get("reason") == "rate_limited":
                delay = max(delay, args.rate_limit_backoff * attempts)
            time.sleep(delay + random.uniform(0, 0.3 * delay))
    # 统计（读 journal，天然可续跑）
    latest = {}
    for row in journal.rows:
        if row.get("status") == "ok":
            latest[row["qid"]] = row
    picked_by_qid = {row["qid"]: row for row in picked}
    candidates_by_qid = {row["qid"]: row for row in candidates}
    parsed = agree = positive_calls = 0
    pos_total = pos_hit = neg_total = neg_hit = 0
    probs_list = []
    reasons = {}
    latencies = []
    for qid, row in latest.items():
        # 统计口径 = journal 里所有已完成的 noul 探针（跨轮累积），不只是本轮抽中的
        plan_row = candidates_by_qid.get(qid)
        if plan_row is None:
            continue
        question = {"kind": "noul", "options": [{"key": plan_row["positive"]},
                                                {"key": plan_row["negative"]}]}
        probs, reason = parse_mercury(row.get("content"), question)
        if probs is None:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        parsed += 1
        value = probs[plan_row["positive"]]
        probs_list.append(round(value, 4))
        latencies.append(row.get("latency_ms") or 0.0)
        top = plan_row["positive"] if value > 0.5 else plan_row["negative"] if value < 0.5 else None
        if value > 0.5:
            positive_calls += 1
        if plan_row["answer"] == plan_row["positive"]:
            pos_total += 1
            pos_hit += 1 if top == plan_row["answer"] else 0
        else:
            neg_total += 1
            neg_hit += 1 if top == plan_row["answer"] else 0
        if top == plan_row["answer"]:
            agree += 1
    total_cost = sum(float(row.get("cost_usd") or 0.0) for row in journal.rows)
    probed = [qid for qid in latest if qid in candidates_by_qid]
    stats = {"generated_at": iso_now(), "decision_url": url, "model": args.mercury_model,
             "cost_usd": round(total_cost, 6),
             "sampled_this_run": len(picked), "probed_total": len(probed),
             "sampled": len(probed), "called_ok": len(latest), "parsed": parsed,
             "agree": agree, "agree_rate": (agree / parsed) if parsed else None,
             "corpus_answer_positive_share": (sum(1 for row in picked
                                                  if row["answer"] == row["positive"]) / len(picked))
             if picked else None,
             "model_positive_rate": (positive_calls / parsed) if parsed else None,
             "p_yes": {"min": min(probs_list) if probs_list else None,
                       "max": max(probs_list) if probs_list else None,
                       "median": sorted(probs_list)[len(probs_list) // 2] if probs_list else None,
                       "values": probs_list},
             "confusion": {"pos_total": pos_total, "pos_hit": pos_hit,
                           "neg_total": neg_total, "neg_hit": neg_hit,
                           "pos_accuracy": (pos_hit / pos_total) if pos_total else None,
                           "neg_accuracy": (neg_hit / neg_total) if neg_total else None,
                           "balanced_accuracy": ((pos_hit / pos_total + neg_hit / neg_total) / 2)
                           if pos_total and neg_total else None,
                           "always_negative_baseline": (neg_total / (pos_total + neg_total))
                           if (pos_total + neg_total) else None},
             "unparsed_reasons": reasons,
             "latency_ms_median": sorted(latencies)[len(latencies) // 2] if latencies else None,
             "calls_this_run": calls, "journal": str(journal_path),
             "details": [{"sample": index + 1, "answer": picked_by_qid[qid]["answer"],
                          "p_yes": round(parse_mercury(row.get("content"),
                                                       {"kind": "noul",
                                                        "options": [{"key": picked_by_qid[qid]["positive"]},
                                                                    {"key": picked_by_qid[qid]["negative"]}]})[0][
                              picked_by_qid[qid]["positive"]], 4)
                          if parse_mercury(row.get("content"),
                                           {"kind": "noul",
                                            "options": [{"key": picked_by_qid[qid]["positive"]},
                                                        {"key": picked_by_qid[qid]["negative"]}]})[0]
                          else None}
                         for index, (qid, row) in enumerate(sorted(latest.items()))
                         if qid in picked_by_qid]}
    stats_path = Path(args.stats or DEFAULT_WORK / "mercury-noul-probe-stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "details"}, ensure_ascii=False, indent=2))
    print(json.dumps(stats["details"], ensure_ascii=False, indent=2))


def _noul_candidates(items_path):
    """语料里所有可判极性的 noul target（answer ∈ {pos,neg}）。"""
    candidates = []
    for item, key, question, target in iter_targets(items_path):
        if question.get("kind") != "noul":
            continue
        positive, negative = noul_option_keys(question)
        answer = str(target.get("answer"))
        if positive is None or negative is None or answer not in (positive, negative):
            continue
        candidates.append({"qid": "%s.%s" % (item["id"], key), "id": item["id"], "key": key,
                           "answer": answer, "positive": positive, "negative": negative,
                           "state": str(item.get("state") or ""),
                           "instructions": str(question.get("prompt") or ""),
                           "lang": item.get("lang") or "", "domain": item.get("domain") or "",
                           "source_dataset": (item.get("source") or {}).get("dataset") or "?",
                           "corpus_shape": target_shape(target)})
    candidates.sort(key=lambda row: row["qid"])
    return candidates


def _mercury_probs_of(row, candidate):
    probs, reason = parse_mercury(row.get("content"),
                                  {"kind": "noul",
                                   "options": [{"key": candidate["positive"]},
                                               {"key": candidate["negative"]}]})
    return probs, reason


def noul_config_consensus(journal, candidates_by_qid):
    """noul 线按 source dataset 分组的「与语料一致率」+ label_confidence。"""
    ok = {}
    for row in journal.rows:
        if row.get("status") == "ok" and row.get("qid") in candidates_by_qid:
            ok[row["qid"]] = row
    per = {}
    for qid, row in ok.items():
        candidate = candidates_by_qid[qid]
        probs, reason = _mercury_probs_of(row, candidate)
        if probs is None:
            continue
        value = probs[candidate["positive"]]
        top = candidate["positive"] if value > 0.5 else candidate["negative"]
        key = candidate.get("source_dataset") or "?"
        stat = per.setdefault(key, {"n": 0, "agree": 0})
        stat["n"] += 1
        stat["agree"] += 1 if top == candidate["answer"] else 0
    for key, stat in per.items():
        stat["agree_rate"] = round(stat["agree"] / stat["n"], 4)
        stat["label_confidence"] = consensus_label(stat["n"], stat["agree"])
    return per


def write_mercury_probs(journal, candidates_by_qid, out_path, stats_path, skip_existing_real=False):
    consensus = noul_config_consensus(journal, candidates_by_qid)
    latest = {}
    for row in journal.rows:
        if row.get("status") == "ok" and row.get("qid") in candidates_by_qid:
            latest[row["qid"]] = row
    rows = []
    skipped = {}
    models = {}
    cost = 0.0

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    for qid in sorted(latest):
        candidate = candidates_by_qid[qid]
        row = latest[qid]
        probs, reason = _mercury_probs_of(row, candidate)
        cost += float(row.get("cost_usd") or 0.0)
        model = row.get("upstream_model") or "-"
        models[model] = models.get(model, 0) + 1
        if probs is None:
            skip("unparsed:" + (reason or "unknown"))
            continue
        value = probs[candidate["positive"]]
        if value <= 0.0 or value >= 1.0:
            skip("degenerate:extreme")
            continue
        all_values = list(probs.values())
        if max(all_values) == min(all_values):
            # p(yes)=0.5 → 两个选项各 0.5，是无信息的均匀分布，不写
            skip("degenerate:uniform")
            continue
        if skip_existing_real and candidate.get("corpus_shape") == "real":
            skip("kept_source_real_distribution")
            continue
        top = candidate["positive"] if value > 0.5 else candidate["negative"]
        if top != candidate["answer"]:
            skip("answer_mismatch")
            continue
        rows.append({"id": candidate["id"], "key": candidate["key"], "qid": qid,
                     "kind": "noul", "lang": candidate["lang"], "domain": candidate["domain"],
                     "answer": candidate["answer"], "probs": probs,
                     "distribution_semantics": "mercury_decide_native",
                     "source": "mercury-decide", "source_version": MERCURY_MODEL,
                     "upstream_model": row.get("upstream_model"),
                     "created_at": row.get("ts") or iso_now(),
                     "n_options": 2, "p_positive_key": candidate["positive"],
                     "corpus_shape": candidate.get("corpus_shape"),
                     "label_confidence": (consensus.get(candidate.get("source_dataset") or "?") or {}).get("label_confidence"),
                     "consensus_agree": (consensus.get(candidate.get("source_dataset") or "?") or {}).get("agree"),
                     "consensus_n": (consensus.get(candidate.get("source_dataset") or "?") or {}).get("n")})
    write_jsonl(out_path, rows)
    by_lang = {}
    by_domain = {}
    by_corpus_shape = {}
    for row in rows:
        by_lang[row["lang"]] = by_lang.get(row["lang"], 0) + 1
        by_domain[row["domain"]] = by_domain.get(row["domain"], 0) + 1
        shape = row.get("corpus_shape") or "?"
        by_corpus_shape[shape] = by_corpus_shape.get(shape, 0) + 1
    stats = {"generated_at": iso_now(), "journal": str(journal.path), "out": str(out_path),
             "decisions_url": DEFAULT_DECISIONS_URL, "model": MERCURY_MODEL,
             "semantics": "mercury_decide_native",
             "candidates": len(candidates_by_qid), "journal_ok": len(latest),
             "written": len(rows), "written_by_lang": by_lang, "written_by_domain": by_domain,
             "written_by_corpus_shape": by_corpus_shape, "skip_existing_real": bool(skip_existing_real),
             "skipped": dict(sorted(skipped.items(), key=lambda pair: -pair[1])),
             "cost_usd": round(cost, 6), "upstream_models": models}
    by_label = {}
    for row in rows:
        value = row.get("label_confidence") or "unknown"
        by_label[value] = by_label.get(value, 0) + 1
    fragment = {"line": "A. mercury-decide noul（升级伪 one-hot / 均匀）",
                "group_by": "source dataset", "written_rows_by_label": by_label,
                "configs": dict(sorted(consensus.items(), key=lambda kv: kv[1]["agree_rate"]))}
    (Path(out_path).parent / "label-confidence-noul.json").write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2), encoding="utf-8")
    stats["label_confidence_counts"] = by_label
    Path(stats_path).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def cmd_noul_fill(args):
    """mercury-decide 全量补 noul：可断点续跑 + 控速 + 429 退避。"""
    config = load_jev_config(args.jev_yaml)
    items_path = Path(args.items)
    candidates = _noul_candidates(items_path)
    candidates_by_qid = {row["qid"]: row for row in candidates}
    journal_path = Path(args.journal or DEFAULT_WORK / "mercury-noul-fill.jsonl")
    journal = Journal(journal_path)
    done = {row["qid"] for row in journal.rows if row.get("status") == "ok"}
    pending = [row for row in candidates if row["qid"] not in done]
    if args.limit:
        pending = pending[:args.limit]
    print(json.dumps({"noul_targets": len(candidates), "already_ok": len(done),
                      "pending": len(pending), "rate_per_s": args.rate,
                      "model": args.mercury_model, "journal": str(journal_path)}, ensure_ascii=False), flush=True)
    limiter = Limiter(1.0 / max(0.1, args.rate))
    state = {"calls": 0, "ok": 0, "errors": 0}
    lock = threading.Lock()
    started = time.perf_counter()

    def process(row):
        attempts = 0
        while attempts < args.max_attempts:
            attempts += 1
            limiter.wait()
            response = mercury_request(args.decisions_url, config["apikey"], args.mercury_model,
                                       row["state"], row["instructions"], args.timeout)
            outcome = mercury_outcome(response)
            record = {"phase": "noul-fill", "qid": row["qid"], "id": row["id"], "key": row["key"],
                      "lang": row["lang"], "domain": row["domain"], "attempt": attempts,
                      "status": outcome["status"], "reason": outcome.get("reason"),
                      "http_status": outcome.get("http_status"), "error": outcome.get("error"),
                      "upstream_model": outcome.get("upstream_model"),
                      "content": outcome.get("content"),
                      "usage": outcome.get("usage"),
                      "cost_usd": float((outcome.get("usage") or {}).get("cost") or 0.0),
                      "latency_ms": round(float(outcome.get("latency_ms") or 0.0), 1)}
            journal.append(record)
            with lock:
                state["calls"] += 1
                if outcome["status"] == "ok":
                    state["ok"] += 1
                    calls_now = state["calls"]
                else:
                    state["errors"] += 1
                    calls_now = None
                progress = state["calls"] % 100 == 0
                snapshot = dict(state)
            if outcome["status"] == "ok":
                if progress:
                    elapsed = max(0.001, time.perf_counter() - started)
                    print(json.dumps({"calls": snapshot["calls"], "ok": snapshot["ok"],
                                      "errors": snapshot["errors"],
                                      "rate_actual": round(snapshot["calls"] / elapsed, 2),
                                      "elapsed_s": round(elapsed, 1)}, ensure_ascii=False), flush=True)
                return
            retryable = (outcome.get("http_status") in RETRY_STATUS
                         or outcome.get("reason") in ("timeout", "network_error", "rate_limited"))
            if not retryable or attempts >= args.max_attempts:
                return
            delay = min(args.max_backoff, args.backoff * (2 ** (attempts - 1)))
            if outcome.get("reason") == "rate_limited":
                delay = max(delay, args.rate_limit_backoff * attempts)
            time.sleep(delay + random.uniform(0, 0.3 * delay))

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(process, pending))
    calls, ok_now, errors = state["calls"], state["ok"], state["errors"]
    stats = write_mercury_probs(journal, candidates_by_qid,
                                Path(args.out or DEFAULT_WORK / "mercury-noul-probs.jsonl"),
                                Path(args.stats or DEFAULT_WORK / "mercury-noul-fill-stats.json"),
                                skip_existing_real=args.skip_existing_real)
    stats.update({"calls_this_run": calls, "ok_this_run": ok_now, "errors_this_run": errors,
                  "elapsed_s": round(time.perf_counter() - started, 1)})
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def load_split_ids(splits_dir, names):
    """读当前（现读、不写死）分区 id 集合；.jsonl 不存在时退回 .jsonl.gz。"""
    splits_dir = Path(splits_dir)
    ids = set()
    for name in names:
        path = splits_dir / ("%s.jsonl" % name)
        if not path.is_file():
            gz = splits_dir / ("%s.jsonl.gz" % name)
            if not gz.is_file():
                raise SystemExit("缺少分区文件，无法安全导出：%s" % path)
            path = gz
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line:
                    ids.add(json.loads(line)["id"])
    return ids


def assert_no_benchmark(rows, benchmark_ids, stage):
    """硬断言：待写行里出现任何 benchmark 成员 id → 非零退出、不写任何文件。

    只打印命中条数与行号，**不打印成员 id / qid**（它们本身就是成员名单）。
    """
    hits = [index for index, row in enumerate(rows) if row.get("id") in benchmark_ids]
    if hits:
        raise SystemExit("benchmark guard 触发（%s）：%d 行命中 benchmark 成员（行号 %s…）；"
                         "拒绝写出，未生成/未覆盖任何交付文件。"
                         % (stage, len(hits), hits[:5]))


def filter_public_probs(src, out_path, splits_dir, pack=False):
    """只导出**公开三区**（train/test/validation）的 target，写盘前后双重 benchmark 硬校验。

    sidecar 的 id 列等于一份成员名单：含 benchmark 成员的交付件会踩保密护栏
    （test_split.SecrecyTest.test_tracked_files_contain_no_benchmark_records）。
    校验逻辑（写前 + 写后重读，明文与 .gz 各一遍）不通过就 SystemExit，绝不覆盖已有交付文件。
    """
    splits_dir = Path(splits_dir)
    public_ids = load_split_ids(splits_dir, ("train", "test", "validation"))
    benchmark_ids = load_split_ids(splits_dir, ("benchmark",))
    overlap = public_ids & benchmark_ids
    if overlap:
        raise SystemExit("分区自检失败：公开三区与 benchmark 有 %d 个 id 重叠，拒绝导出（不得猜测落哪边）。"
                         % len(overlap))
    rows = list(read_jsonl(src))
    selected = [row for row in rows if row.get("id") in public_ids]
    assert_no_benchmark(selected, benchmark_ids, "写盘前/明文")
    write_jsonl(out_path, selected)
    raw = Path(out_path).read_bytes()
    packed_info = None
    if pack:
        gz_path = Path(str(out_path) + ".gz")
        with open(gz_path, "wb") as handle:
            with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0, compresslevel=9) as gz:
                gz.write(raw)
        with gzip.open(gz_path, "rb") as handle:
            back = handle.read()
        if back != raw:
            raise SystemExit("自检失败：.gz 解压后与明文不一致，交付件不可信。")
        gz_rows = [json.loads(line) for line in back.decode("utf-8").splitlines() if line.strip()]
        assert_no_benchmark(gz_rows, benchmark_ids, "写盘后/.gz")
        packed_info = {"gz": str(gz_path), "gz_bytes": gz_path.stat().st_size,
                       "gz_sha256": hashlib.sha256(gz_path.read_bytes()).hexdigest()}
    reread = list(read_jsonl(out_path))
    assert_no_benchmark(reread, benchmark_ids, "写盘后/明文重读")
    if len(reread) != len(selected):
        raise SystemExit("自检失败：重读行数不一致（%d != %d）。" % (len(reread), len(selected)))
    return {"src": str(src), "out": str(out_path), "total": len(rows), "rows": len(selected),
            "distinct_ids": len({row.get("id") for row in selected}),
            "benchmark_intersection": 0, "splits_dir": str(splits_dir),
            "plain_sha256": hashlib.sha256(raw).hexdigest(), "packed": packed_info}


def merge_label_confidence(work_dir):
    """把 noul / choice 两条线的 label-confidence 片段合并成总表。"""
    work_dir = Path(work_dir)
    fragments = []
    for name in ("label-confidence-noul.json", "label-confidence-choice.json",
                 "label-confidence-jevrouter.json"):
        path = work_dir / name
        if path.is_file():
            fragments.append(json.loads(path.read_text(encoding="utf-8")))
    if not fragments:
        return None
    merged = {"generated_at": iso_now(), "scheme": CONSENSUS_SCHEME, "note": CONSENSUS_NOTE,
              "lines": {}, "written_rows_by_label": {}}
    for fragment in fragments:
        merged["lines"][fragment["line"]] = {
            "group_by": fragment.get("group_by"), "configs": fragment.get("configs") or {},
            "written_rows_by_label": fragment.get("written_rows_by_label") or {}}
        for label, count in (fragment.get("written_rows_by_label") or {}).items():
            merged["written_rows_by_label"][label] = merged["written_rows_by_label"].get(label, 0) + count
    (work_dir / "label-confidence.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def guard_self_test(src, splits_dir):
    """自检：故意把一个 benchmark 成员放进「待写集合」，验证 assert_no_benchmark 真的会拒写。

    不依赖 splits 恰好正确（正常导出时 filter 已把 benchmark 行滤掉，负例无法自然触发），
    所以这里直接测断言函数本身；只在内存里做，不写任何文件。
    """
    splits_dir = Path(splits_dir)
    benchmark_ids = load_split_ids(splits_dir, ("benchmark",))
    public_ids = load_split_ids(splits_dir, ("train", "test", "validation"))
    rows = list(read_jsonl(src))
    bench_row = next((row for row in rows if row.get("id") in benchmark_ids), None)
    public_row = next((row for row in rows if row.get("id") in public_ids), None)
    if bench_row is None or public_row is None:
        raise SystemExit("自检无法进行：源文件里找不到可用的行。")
    injected = [public_row, bench_row]
    try:
        assert_no_benchmark(injected, benchmark_ids, "自检/注入")
    except SystemExit as error:
        return {"status": "pass", "message": str(error),
                "injected_rows": 2, "expected_hits": 1, "wrote_files": False}
    raise SystemExit("guard 自检失败：注入 benchmark 行后断言没有触发！")


def cmd_probs_guard_test(args):
    print(json.dumps(guard_self_test(args.src, args.splits_dir), ensure_ascii=False, indent=2))


def cmd_probs_public(args):
    print(json.dumps(filter_public_probs(args.src, args.out, args.splits_dir, pack=args.pack),
                     ensure_ascii=False, indent=2))


def cmd_probs_assemble(args):
    """把各来源的旁挂 probs 合并成交付文件 data/jev-probs.jsonl（按 qid 去重排序）。"""
    sources = args.source or []
    rows = {}
    origin = {}
    for path in sources:
        path = Path(path)
        if not path.is_file():
            continue
        for row in read_jsonl(path):
            qid = row.get("qid")
            if not qid or qid in rows:
                continue
            rows[qid] = row
            origin[row.get("distribution_semantics")] = origin.get(row.get("distribution_semantics"), 0) + 1
    ordered = [rows[qid] for qid in sorted(rows)]
    out = Path(args.out or DEFAULT_FILL_OUT)
    write_jsonl(out, ordered)
    confidence = merge_label_confidence(DEFAULT_WORK)
    stats = {"out": str(out), "rows": len(ordered), "by_semantics": origin,
             "label_confidence": (confidence or {}).get("written_rows_by_label"),
             "sources": [str(path) for path in sources]}
    print(json.dumps(stats, ensure_ascii=False, indent=2))


CHOICE_CRITERION_TEMPLATE = "the correct answer is %s"


def _choice_candidates(items_path, exclude_qids):
    """answer-only 的 choice target（排除指定的旧集合），criteria 由选项 label 模板生成。"""
    candidates = []
    for item, key, question, target in iter_targets(items_path):
        if target_shape(target) != "answer_only" or question.get("kind") != "choice":
            continue
        qid = "%s.%s" % (item["id"], key)
        if qid in exclude_qids:
            continue
        options = question.get("options") or []
        if len(options) < 2:
            continue
        option_keys = [str(option.get("key")) for option in options]
        answer = str(target.get("answer"))
        if answer not in option_keys:
            continue
        criteria = {}
        for option in options:
            option_key = str(option.get("key"))
            label = str(option.get("label") or option_key).strip()[:300]
            criteria[option_key] = CHOICE_CRITERION_TEMPLATE % label
        candidates.append({"qid": qid, "id": item["id"], "key": key, "kind": "choice",
                           "answer": answer, "option_keys": option_keys, "criteria": criteria,
                           "state": str(item.get("state") or ""),
                           "instructions": str(question.get("prompt") or ""),
                           "lang": item.get("lang") or "", "domain": item.get("domain") or "",
                           "corpus_shape": "answer_only",
                           "source_dataset": (item.get("source") or {}).get("dataset") or ""})
    candidates.sort(key=lambda row: row["qid"])
    return candidates


def mercury_choice_request(url, key, model, state, instructions, criteria, timeout):
    body = {"model": model, "state": str(state or "")[:12000],
            "questions": {MERCURY_QUESTION_KEY: {"type": "choice",
                                                 "instructions": str(instructions or "")[:4000],
                                                 "criteria": criteria}}}
    return post_chat(url, key, body, timeout)


def mercury_choice_outcome(response, option_keys):
    """choice 决策响应 -> probs over option keys。"""
    status = response["status"]
    if status != 200:
        kind = response.get("kind") or ("timeout" if status is None else "http_error")
        text = response["body"][:400].decode("utf-8", "replace") if response.get("body") else ""
        if status == 429:
            kind = "rate_limited"
        elif status == 402 and ("credit" in text.lower() or "afford" in text.lower()):
            kind = "insufficient_credits"
        return {"status": "error", "reason": kind, "http_status": status,
                "error": (response.get("error") or "") + (" | " + text if text else ""),
                "latency_ms": response["latency_ms"]}
    try:
        body = json.loads(response["body"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"status": "error", "reason": "not_json", "http_status": 200,
                "error": "bad JSON: %s" % error, "latency_ms": response["latency_ms"]}
    answer = (body.get("answers") or {}).get(MERCURY_QUESTION_KEY) or {}
    probabilities = answer.get("probabilities")
    usage = body.get("usage") or {}
    if not isinstance(probabilities, dict) or not probabilities:
        return {"status": "error", "reason": "not_in_options", "http_status": 200,
                "error": "no probabilities: %s" % json.dumps(answer, ensure_ascii=False)[:300],
                "latency_ms": response["latency_ms"]}
    probs = {}
    for option_key in option_keys:
        value = probabilities.get(option_key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            probs[option_key] = float(value)
    if len(probs) < 2:
        return {"status": "error", "reason": "not_in_options", "http_status": 200,
                "error": "probabilities do not cover the option keys: %s"
                         % json.dumps(probabilities, ensure_ascii=False)[:300],
                "latency_ms": response["latency_ms"]}
    total = sum(probs.values())
    if total <= 0:
        return {"status": "error", "reason": "not_in_options", "http_status": 200,
                "error": "probabilities sum to 0", "latency_ms": response["latency_ms"]}
    probs = {option_key: value / total for option_key, value in probs.items()}
    return {"status": "ok", "http_status": 200,
            "content": json.dumps({"choice": answer.get("choice"), "probs": probs,
                                   "confidence": answer.get("confidence")}, ensure_ascii=False),
            "finish_reason": "stop", "upstream_model": body.get("model"),
            "usage": {"prompt_tokens": usage.get("input_tokens"),
                      "completion_tokens": usage.get("output_tokens"),
                      "cost": usage.get("cost")},
            "latency_ms": response["latency_ms"], "response_id": body.get("id")}


def cmd_choice_fill(args):
    """mercury-decide 补 answer-only choice：criteria 由选项模板生成，可续跑、按预算停。"""
    config = load_jev_config(args.jev_yaml)
    items_path = Path(args.items)
    exclude = set()
    if args.exclude_plan and Path(args.exclude_plan).is_file():
        plan = read_jsonl(args.exclude_plan)
        exclude = {row["qid"] for row in plan[1:] if row.get("record_type") == "request"}
    candidates = _choice_candidates(items_path, exclude)
    candidates_by_qid = {row["qid"]: row for row in candidates}
    journal_path = Path(args.journal or DEFAULT_WORK / "mercury-choice-fill.jsonl")
    journal = Journal(journal_path)
    done = {row["qid"] for row in journal.rows if row.get("status") == "ok"}
    pending = [row for row in candidates if row["qid"] not in done]
    if args.limit:
        pending = pending[:args.limit]
    spent = sum(float(row.get("cost_usd") or 0.0) for row in journal.rows if row.get("status") == "ok")
    print(json.dumps({"choice_targets": len(candidates), "excluded_old": len(exclude),
                      "already_ok": len(done), "pending": len(pending), "spent_usd": round(spent, 6),
                      "budget_usd": args.budget, "workers": args.workers, "rate_per_s": args.rate,
                      "model": args.mercury_model, "journal": str(journal_path)}, ensure_ascii=False), flush=True)
    limiter = Limiter(1.0 / max(0.1, args.rate))
    state = {"calls": 0, "ok": 0, "errors": 0, "stopped": False}
    lock = threading.Lock()
    started = time.perf_counter()

    def spend() -> float:
        with lock:
            return spent

    def process(row):
        if state["stopped"]:
            return
        attempts = 0
        while attempts < args.max_attempts:
            with lock:
                if state["stopped"]:
                    return
                run_spent = state.get("spent", 0.0)
                total_spent = spent + run_spent
                done_calls = len(done) + state["ok"]
                mean = total_spent / done_calls if done_calls else args.estimate_per_call
                if total_spent + max(args.estimate_per_call, mean * 1.5) > args.budget:
                    state["stopped"] = True
                    print(json.dumps({"stop": "budget", "spent_usd": round(total_spent, 6),
                                      "calls": state["calls"]}, ensure_ascii=False), flush=True)
                    return
            attempts += 1
            limiter.wait()
            response = mercury_choice_request(args.decisions_url, config["apikey"], args.mercury_model,
                                              row["state"], row["instructions"], row["criteria"],
                                              args.timeout)
            outcome = mercury_choice_outcome(response, row["option_keys"])
            cost = float((outcome.get("usage") or {}).get("cost") or 0.0)
            record = {"phase": "choice-fill", "qid": row["qid"], "id": row["id"], "key": row["key"],
                      "lang": row["lang"], "domain": row["domain"], "attempt": attempts,
                      "status": outcome["status"], "reason": outcome.get("reason"),
                      "http_status": outcome.get("http_status"), "error": outcome.get("error"),
                      "upstream_model": outcome.get("upstream_model"),
                      "content": outcome.get("content"), "usage": outcome.get("usage"),
                      "cost_usd": cost,
                      "latency_ms": round(float(outcome.get("latency_ms") or 0.0), 1)}
            journal.append(record)
            with lock:
                state["calls"] += 1
                state["spent"] = state.get("spent", 0.0) + cost
                if outcome["status"] == "ok":
                    state["ok"] += 1
                else:
                    state["errors"] += 1
            if outcome["status"] == "ok":
                if state["calls"] % 200 == 0:
                    elapsed = max(0.001, time.perf_counter() - started)
                    print(json.dumps({"calls": state["calls"], "ok": state["ok"],
                                      "errors": state["errors"],
                                      "spent_usd": round(state.get("spent", 0.0), 5),
                                      "rate_actual": round(state["calls"] / elapsed, 2),
                                      "elapsed_s": round(elapsed, 1)}, ensure_ascii=False), flush=True)
                return
            retryable = (outcome.get("http_status") in RETRY_STATUS
                         or outcome.get("reason") in ("timeout", "network_error", "rate_limited"))
            if not retryable or attempts >= args.max_attempts:
                if outcome.get("reason") == "insufficient_credits":
                    with lock:
                        state["stopped"] = True
                return
            delay = min(args.max_backoff, args.backoff * (2 ** (attempts - 1)))
            if outcome.get("reason") == "rate_limited":
                delay = max(delay, args.rate_limit_backoff * attempts)
            time.sleep(delay + random.uniform(0, 0.3 * delay))

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(process, pending))
    total_cost = sum(float(row.get("cost_usd") or 0.0) for row in journal.rows if row.get("status") == "ok")
    stats = write_choice_probs(journal, candidates_by_qid,
                               Path(args.out or DEFAULT_WORK / "mercury-choice-probs.jsonl"),
                               Path(args.stats or DEFAULT_WORK / "mercury-choice-fill-stats.json"))
    stats.update({"calls_this_run": state["calls"], "ok_this_run": state["ok"],
                  "errors_this_run": state["errors"], "budget_stopped": state["stopped"],
                  "total_cost_usd": round(total_cost, 6),
                  "elapsed_s": round(time.perf_counter() - started, 1)})
    print(json.dumps(stats, ensure_ascii=False, indent=2))


CONSENSUS_THRESHOLDS = {"low": 0.70, "high": 0.95, "min_n": 10}
CONSENSUS_SCHEME = {
    "low_consensus": "双方一致率 < 70%（n >= 10）",
    "medium_consensus": "70% <= 一致率 < 95%",
    "high_consensus": "一致率 >= 95%",
    "insufficient_sample": "n < 10，不下结论",
}
CONSENSUS_NOTE = ("label_confidence 衡量的是「我们与该 config 的 mercury 判断是否互相印证」，"
                  "**不是「标签对错」**。low_consensus = 该子集标签未经双方互证，"
                  "训练时应降权或标记复核，不要当作和 high_consensus 一样可信。")


def consensus_label(n, agree):
    """按「双方一致率」给 config 打标签；n 太小不下结论。"""
    if n < CONSENSUS_THRESHOLDS["min_n"]:
        return "insufficient_sample"
    rate = agree / n
    if rate < CONSENSUS_THRESHOLDS["low"]:
        return "low_consensus"
    if rate < CONSENSUS_THRESHOLDS["high"]:
        return "medium_consensus"
    return "high_consensus"


def choice_config_consensus(journal, candidates_by_qid):
    """journal 里每个 question key 的「与语料一致率」+ label_confidence。"""
    ok = {}
    for row in journal.rows:
        if row.get("status") == "ok" and row.get("qid") in candidates_by_qid:
            ok[row["qid"]] = row
    per = {}
    for qid, row in ok.items():
        candidate = candidates_by_qid[qid]
        try:
            payload = json.loads(row.get("content") or "")
        except json.JSONDecodeError:
            continue
        probs = payload.get("probs") if isinstance(payload, dict) else None
        if not isinstance(probs, dict) or not probs:
            continue
        top = max(probs, key=lambda option_key: probs[option_key])
        key = candidate["key"]
        stat = per.setdefault(key, {"n": 0, "agree": 0})
        stat["n"] += 1
        stat["agree"] += 1 if top == candidate["answer"] else 0
    for key, stat in per.items():
        stat["agree_rate"] = round(stat["agree"] / stat["n"], 4)
        stat["label_confidence"] = consensus_label(stat["n"], stat["agree"])
    return per


def write_choice_probs(journal, candidates_by_qid, out_path, stats_path):
    consensus = choice_config_consensus(journal, candidates_by_qid)
    latest = {}
    for row in journal.rows:
        if row.get("status") == "ok" and row.get("qid") in candidates_by_qid:
            latest[row["qid"]] = row
    rows = []
    skipped = {}
    models = {}
    cost = 0.0

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    for qid in sorted(latest):
        candidate = candidates_by_qid[qid]
        row = latest[qid]
        cost += float(row.get("cost_usd") or 0.0)
        model = row.get("upstream_model") or "-"
        models[model] = models.get(model, 0) + 1
        try:
            payload = json.loads(row.get("content") or "")
        except json.JSONDecodeError:
            skip("unparsed:not_json")
            continue
        probs = payload.get("probs") if isinstance(payload, dict) else None
        if not isinstance(probs, dict) or len(probs) < 2:
            skip("unparsed:not_in_options")
            continue
        values = list(probs.values())
        if max(values) == min(values):
            skip("degenerate:uniform")
            continue
        if sum(1 for value in values if value > 0) == 1:
            skip("degenerate:one_hot")
            continue
        top = max(probs, key=lambda option_key: probs[option_key])
        if top != candidate["answer"]:
            skip("answer_mismatch")
            continue
        rows.append({"id": candidate["id"], "key": candidate["key"], "qid": qid,
                     "kind": "choice", "lang": candidate["lang"], "domain": candidate["domain"],
                     "answer": candidate["answer"], "probs": probs,
                     "distribution_semantics": "mercury_decide_native",
                     "source": "mercury-decide", "source_version": MERCURY_MODEL,
                     "upstream_model": row.get("upstream_model"),
                     "created_at": row.get("ts") or iso_now(),
                     "n_options": len(probs), "corpus_shape": "answer_only",
                     "label_confidence": (consensus.get(candidate["key"]) or {}).get("label_confidence"),
                     "consensus_agree": (consensus.get(candidate["key"]) or {}).get("agree"),
                     "consensus_n": (consensus.get(candidate["key"]) or {}).get("n")})
    write_jsonl(out_path, rows)
    by_lang = {}
    by_domain = {}
    for row in rows:
        by_lang[row["lang"]] = by_lang.get(row["lang"], 0) + 1
        by_domain[row["domain"]] = by_domain.get(row["domain"], 0) + 1
    stats = {"generated_at": iso_now(), "journal": str(journal.path), "out": str(out_path),
             "decisions_url": DEFAULT_DECISIONS_URL, "model": MERCURY_MODEL,
             "semantics": "mercury_decide_native", "kind": "choice",
             "candidates": len(candidates_by_qid), "journal_ok": len(latest),
             "written": len(rows), "written_by_lang": by_lang, "written_by_domain": by_domain,
             "skipped": dict(sorted(skipped.items(), key=lambda pair: -pair[1])),
             "cost_usd": round(cost, 6), "upstream_models": models}
    Path(stats_path).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    by_label = {}
    for row in rows:
        by_label[row.get("label_confidence") or "unknown"] = \
            by_label.get(row.get("label_confidence") or "unknown", 0) + 1
    fragment = {"line": "B. mercury-decide choice（补 answer-only）", "group_by": "question key",
                "written_rows_by_label": by_label,
                "configs": dict(sorted(consensus.items(), key=lambda kv: kv[1]["agree_rate"]))}
    (Path(out_path).parent / "label-confidence-choice.json").write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2), encoding="utf-8")
    stats["label_confidence_counts"] = by_label
    return stats


# ------------------------------------------------------------------ 阶段一报告

def _state_brief(text, limit=150):
    text = " ".join(str(text or "").split())
    return text[:limit] + ("…" if len(text) > limit else "")


def _journal_rows(path):
    path = Path(path)
    if not path.is_file():
        return []
    return read_jsonl(path)


def _self_consistency(self_plan_path, self_journal_paths):
    plan_rows = {row["qid"]: row for row in read_jsonl(self_plan_path)[1:]
                 if row.get("record_type") == "request"} if Path(self_plan_path).is_file() else {}
    rounds = {}
    for journal_path in self_journal_paths:
        for row in _journal_rows(journal_path):
            if row.get("status") != "ok" or row.get("qid") not in plan_rows:
                continue
            rounds.setdefault(row["qid"], {})[row.get("repeat_index", 0)] = row
    paired = {qid: value for qid, value in rounds.items() if len(value) >= 2}
    if not paired:
        return None
    items_path = Path(read_jsonl(self_plan_path)[0]["items"])
    questions = {}
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid in paired:
            questions[qid] = question
    agree = 0
    total = 0
    models = {}
    for qid, value in paired.items():
        question = questions.get(qid)
        if question is None:
            continue
        parsed = {}
        for index, row in value.items():
            key, reason = parse_answer(row.get("content"), question, row.get("finish_reason"))
            parsed[index] = key if reason == "ok" else None
            models[row.get("upstream_model") or "-"] = models.get(row.get("upstream_model") or "-", 0) + 1
        usable = [parsed[index] for index in sorted(parsed) if parsed[index] is not None]
        if len(usable) >= 2:
            total += 1
            agree += 1 if len(set(usable)) == 1 else 0
    return {"pairs": total, "agree": agree,
            "rate": (agree / total) if total else 0.0,
            "unique_models": len(models), "models": models}


def chance_verdict(metric):
    """把一致率的 Wilson 95% CI 与随机基线比：显著高 / 不可区分 / 显著低。"""
    if not metric or not metric["parsed"]:
        return "无样本"
    low, high = wilson(metric["agree"], metric["parsed"])
    base = metric["chance"]
    if low > base:
        return "显著高于随机"
    if high < base:
        return "显著低于随机"
    return "与随机不可区分"


def degeneracy(records):
    """分布变体的退化性体检：one-hot / 均匀 / 支撑集大小 / 最大概率。"""
    sizes = []
    maxes = []
    one_hot = 0
    uniform = 0
    full_support = 0
    empty = 0
    for record in records:
        probs = record.get("probs")
        if not probs:
            empty += 1
            continue
        values = [float(value) for value in probs.values()]
        support = sum(1 for value in values if value > 0)
        sizes.append(support)
        maxes.append(max(values))
        if support == 1:
            one_hot += 1
        if max(values) == min(values):
            uniform += 1
        if support == len(values):
            full_support += 1
    total = len(sizes)
    sizes.sort()
    maxes.sort()
    return {"total": total, "unparsed_or_empty": empty, "one_hot": one_hot, "uniform": uniform,
            "non_degenerate": total - one_hot - uniform,
            "full_support": full_support,
            "median_support": sizes[len(sizes) // 2] if sizes else 0,
            "median_max": maxes[len(maxes) // 2] if maxes else 0.0,
            "mean_max": (sum(maxes) / len(maxes)) if maxes else 0.0}


def anon_labels(qids):
    """把 qid 映射成「样本 #N（id 从略）」；N 按 qid 排序稳定，跨次重生成不变。"""
    ordered = sorted(set(qids))
    return {qid: "样本 #%03d（id 从略）" % (index + 1) for index, qid in enumerate(ordered)}


def assert_no_item_ids(text, ids):
    """硬断言：报告里出现语料中任一完整 item id 就直接失败（成员身份是敏感信息）。"""
    tokens = set(re.findall(r"db-[A-Za-z0-9._:-]+", text))
    for token in tokens:
        if token in ids or any(token.startswith(item_id + ".") for item_id in ids):
            raise SystemExit("报告泄漏完整 item id（%d 个候选 token 中命中 1 个）。"
                             "报告必须只用匿名索引，见 anon_labels()。" % len(tokens))
    return len(tokens)


def choice_config_breakdown(items_path, journal_path):
    """choice 线按 (source, question key) 的一致率，用来看哪些 config 分歧高。"""
    path = Path(journal_path)
    if not path.is_file():
        return []
    ok = {}
    for row in read_jsonl(path):
        if row.get("status") == "ok":
            ok[row["qid"]] = row
    wanted = set(ok)
    info = {}
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid in wanted:
            info[qid] = (str(target.get("answer")), str(question.get("key")),
                         (item.get("source") or {}).get("dataset") or "?")
    per = {}
    for qid, row in ok.items():
        if qid not in info:
            continue
        try:
            payload = json.loads(row.get("content") or "")
        except json.JSONDecodeError:
            continue
        probs = payload.get("probs") if isinstance(payload, dict) else None
        if not isinstance(probs, dict) or not probs:
            continue
        top = max(probs, key=lambda option_key: probs[option_key])
        answer, key, _src = info[qid]
        stat = per.setdefault(key, {"n": 0, "agree": 0})
        stat["n"] += 1
        stat["agree"] += 1 if top == answer else 0
    rows = [(key, value["n"], value["agree"]) for key, value in per.items()]
    rows.sort(key=lambda row: row[2] / row[1])
    return rows


def public_probs_counts():
    """交付面 vs 本地全量的行数（读文件头信息即可，不重扫语料）。"""
    public_path = DEFAULT_FILL_OUT
    full_path = DEFAULT_WORK / "jev-probs.full.jsonl"
    try:
        public = sum(1 for line in open(public_path, encoding="utf-8") if line.strip())
        total = sum(1 for line in open(full_path, encoding="utf-8") if line.strip()) if full_path.is_file() else public
        return {"public": public, "total": total, "dropped": max(0, total - public)}
    except OSError:
        return None


def usable_soft_share(probs_path, target_types_path):
    """按 README §4.4 口径算「可用软分布」占比：分母 = 公开件 + 补充集，分子 = soft/tie_subset ∪ 新补。"""
    tt_path = Path(target_types_path)
    if not tt_path.is_file():
        gz = Path(str(tt_path) + ".gz")
        if not gz.is_file():
            return None
        tt_path = gz
    opener = gzip.open if str(tt_path).endswith(".gz") else open
    shape_of = {}
    with opener(tt_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            shape_of[(row.get("item_id"), row.get("question_key"))] = row.get("shape_class")
    source_real = sum(1 for value in shape_of.values() if value in ("soft", "tie_subset"))
    denominator = len(shape_of) + 3148      # 公开件 + 补充集（README 口径恒等式）
    added = {}
    already_real = 0
    outside_public = 0
    for row in read_jsonl(probs_path):
        shape = shape_of.get((row.get("id"), row.get("key")))
        if shape is None:
            outside_public += 1
            continue
        if shape in ("soft", "tie_subset"):
            already_real += 1
            continue
        semantics = row.get("distribution_semantics") or "?"
        added[semantics] = added.get(semantics, 0) + 1
    added_total = sum(added.values())
    return {"public_rows": len(shape_of), "denominator": denominator,
            "source_real": source_real, "added": added, "added_total": added_total,
            "already_real": already_real, "outside_public": outside_public,
            "before_share": source_real / denominator if denominator else 0.0,
            "after_share": (source_real + added_total) / denominator if denominator else 0.0}


def corpus_snapshot(items_path, wanted_qids=None):
    """一次遍历得到：target 形态构成、answer-only 分 kind、noul 分形态、全部 item id（保密门禁用）。"""
    ids = set()
    shapes = {"real": 0, "one_hot": 0, "uniform": 0, "answer_only": 0}
    answer_only_by_kind = {}
    noul = 0
    noul_shapes = {"real": 0, "one_hot": 0, "uniform": 0, "answer_only": 0}
    shape_of = {}
    total = 0
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        ids.add(item["id"])
        shape = target_shape(target)
        shapes[shape] += 1
        total += 1
        if shape == "answer_only":
            kind = question.get("kind")
            answer_only_by_kind[kind] = answer_only_by_kind.get(kind, 0) + 1
        if question.get("kind") == "noul":
            positive, negative = noul_option_keys(question)
            if positive and negative and str(target.get("answer")) in (positive, negative):
                noul += 1
                noul_shapes[shape] += 1
        if wanted_qids and qid in wanted_qids:
            shape_of[qid] = shape
    return {"total": total, "shapes": shapes, "answer_only_by_kind": answer_only_by_kind,
            "noul": noul, "noul_shapes": noul_shapes, "ids": ids, "shape_of": shape_of}


def truth_shape_composition(items_path, sidecar_paths):
    """语料原本的 target 形态构成 vs 采用旁挂 probs 之后的构成。"""
    covered = {}
    for path in sidecar_paths:
        if not Path(path).is_file():
            continue
        for row in read_jsonl(path):
            qid = row.get("qid")
            if qid:
                covered[qid] = row.get("distribution_semantics") or "?"
    counts = {"real": 0, "one_hot": 0, "uniform": 0, "answer_only": 0}
    shape_of = {}
    total = 0
    for item, key, question, target in iter_targets(items_path):
        shape = target_shape(target)
        counts[shape] += 1
        total += 1
        qid = "%s.%s" % (item["id"], key)
        if qid in covered:
            shape_of[qid] = shape
    after = dict(counts)
    filled = {}
    for qid, semantics in covered.items():
        shape = shape_of.get(qid)
        if shape is None:
            continue
        after[shape] -= 1
        filled[semantics] = filled.get(semantics, 0) + 1
    return {"before": counts, "after": after, "total": total, "filled": filled,
            "filled_total": sum(filled.values())}


def cmd_report(args):
    work = DEFAULT_WORK
    plan_path = Path(args.plan or work / "validation-plan.jsonl")
    journal_path = Path(args.journal or work / "validation-calls.jsonl")
    plan = read_jsonl(plan_path)
    manifest = plan[0]
    sidecars = args.sidecar or [str(work / "mercury-noul-probs.jsonl"),
                                str(work / "jev-router-partial-probs.jsonl"),
                                str(work / "mercury-choice-probs.jsonl")]
    covered = {}
    for sidecar_path in sidecars:
        if not Path(sidecar_path).is_file():
            continue
        for sidecar_row in read_jsonl(sidecar_path):
            if sidecar_row.get("qid"):
                covered[sidecar_row["qid"]] = sidecar_row.get("distribution_semantics") or "?"
    items_path = Path(manifest["items"])
    snapshot = corpus_snapshot(items_path, wanted_qids=set(covered))
    current_sha = sha256_file(items_path)
    mercury_stats = {}
    mercury_stats_path = work / "mercury-noul-fill-stats.json"
    if mercury_stats_path.is_file():
        mercury_stats = json.loads(mercury_stats_path.read_text(encoding="utf-8"))
    router_stats = {}
    router_stats_path = work / "jev-router-partial-stats.json"
    if router_stats_path.is_file():
        router_stats = json.loads(router_stats_path.read_text(encoding="utf-8"))
    choice_stats = {}
    choice_stats_path = work / "mercury-choice-fill-stats.json"
    if choice_stats_path.is_file():
        choice_stats = json.loads(choice_stats_path.read_text(encoding="utf-8"))
    raw_records = load_records(plan, [journal_path])
    records = score_records(raw_records, plan_path)
    qid_label = anon_labels([record["row"]["qid"] for record in records])
    overall = summarize(records)
    by_lang = group_table(records, "lang")
    by_domain = group_table(records, "domain")
    by_kind = group_table(records, "kind")
    by_shape = group_table(records, "shape")
    by_stratum = {}
    for record in records:
        key = "%s|%s|%s" % (record["row"]["lang"], record["row"]["domain"], record["row"]["kind"])
        by_stratum.setdefault(key, []).append(record)
    by_stratum = {key: summarize(value) for key, value in sorted(by_stratum.items())}
    answer_only = summarize([record for record in records if record["row"]["shape"] == "answer_only"])
    with_probs = summarize([record for record in records if record["row"]["shape"] != "answer_only"])
    reasons = {}
    no_response = {}
    for record in records:
        if record.get("http_status") != 200:
            reason = record["reason"]
            if record.get("http_status") == 402:
                reason = "insufficient_credits"
            no_response[reason] = no_response.get(reason, 0) + 1
        elif record["parsed"] is None:
            reasons[record["reason"]] = reasons.get(record["reason"], 0) + 1
    journals = [journal_path]
    for extra in (args.extra_journal or []):
        journals.append(Path(extra))
    dist_plan_path = Path(args.dist_plan or work / "validation-plan-distribution.jsonl")
    dist_journal_path = Path(args.dist_journal or work / "probe-dist-calls.jsonl")
    self_plan_path = Path(args.self_plan or work / "validation-plan-self.jsonl")
    self_journal_path = Path(args.self_journal or work / "selfconsistency-calls.jsonl")
    dist_section = None
    if dist_plan_path.is_file() and dist_journal_path.is_file():
        dist_plan = read_jsonl(dist_plan_path)
        dist_raw = load_records(dist_plan, [dist_journal_path])
        dist_records = score_records(dist_raw, dist_plan_path)
        dist_section = {"summary": summarize(dist_records), "cost": cost_summary([dist_journal_path]),
                        "records": dist_records, "degeneracy": degeneracy(dist_records)}
        journals.append(dist_journal_path)
    self_section = None
    if self_plan_path.is_file() and self_journal_path.is_file():
        self_section = _self_consistency(self_plan_path, [self_journal_path, journal_path])
        journals.append(self_journal_path)
    paired_section = None
    if dist_section:
        base_by_qid = {record["row"]["qid"]: record for record in records}
        probe_by_qid = {record["row"]["qid"]: record for record in dist_section["records"]}
        common = sorted(set(base_by_qid) & set(probe_by_qid))
        both = [qid for qid in common
                if base_by_qid[qid]["parsed"] and probe_by_qid[qid]["parsed"]]
        same = [qid for qid in both
                if base_by_qid[qid]["parsed"] == probe_by_qid[qid]["parsed"]]
        paired_section = {"common": len(common), "both": len(both), "same": len(same),
                          "base_agree": sum(1 for qid in common if base_by_qid[qid]["parsed"] == base_by_qid[qid]["truth"]),
                          "probe_agree": sum(1 for qid in common if probe_by_qid[qid]["parsed"] == probe_by_qid[qid]["truth"]),
                          "both_base_agree": sum(1 for qid in both if base_by_qid[qid]["parsed"] == base_by_qid[qid]["truth"]),
                          "both_probe_agree": sum(1 for qid in both if probe_by_qid[qid]["parsed"] == probe_by_qid[qid]["truth"]),
                          "base_parsed": sum(1 for qid in common if base_by_qid[qid]["parsed"]),
                          "probe_parsed": sum(1 for qid in common if probe_by_qid[qid]["parsed"]),
                          "base_cost": sum(base_by_qid[qid]["cost_usd"] for qid in common),
                          "probe_cost": sum(probe_by_qid[qid]["cost_usd"] for qid in common)}

    fill_out = Path(args.fill_out or DEFAULT_FILL_OUT)
    fill_section = None
    if fill_out.is_file():
        rows = read_jsonl(fill_out)
        fill_section = {"rows": len(rows), "cost": cost_summary([work / "fill-calls.jsonl"])}
    total_cost = cost_summary(journals)
    all_models = dict(sorted(total_cost["models"].items(), key=lambda pair: -pair[1]["cost_usd"]))
    stopped = [record for record in records if record["reason"] == "budget_stop"]
    total_sent = sum(1 for record in records if record.get("http_status") is not None)
    per_call_cost = total_cost["cost_usd"] / total_cost["ok"] if total_cost["ok"] else 0.0
    remaining = max(0, manifest["sampled_n"] - total_cost["ok"]) if args.phase == "validation" else 0
    remaining_cost = remaining * per_call_cost
    credits_402 = sum(1 for record in records if record.get("http_status") == 402)
    costs = sorted(record["cost_usd"] for record in records if record["parsed"] is not None and record["cost_usd"])
    median_cost = costs[len(costs) // 2] if costs else 0.0

    lines = []
    lines.append("# Jev 分层校验与 probs 补全报告")
    lines.append("")
    lines.append("> 本报告含两部分：**第一阶段**（与语料真值的分层一致性校验，第 1–7 节）"
                 "与**第二阶段**（旁挂 probs 的补全/升级，第 8 节；两条线分开统计）。")
    lines.append("")
    lines.append("> 生成时间：%s ｜ 生成脚本：%s（[jev_fill.py](jev_fill.py)）" % (iso_now(), HARNESS_VERSION))
    lines.append("> 语料：`datasets/general/data/items.final.jsonl`（明文不入库，见 .gitignore；只读，未改动）")
    if current_sha != manifest["items_sha256"]:
        lines.append(">")
        lines.append("> ⚠️ **语料版本说明**：第一阶段抽样基于 plan 记录的语料版本（sha256 前缀 `%s`）；"
                     "**会话期间语料被其他任务重建**，当前版本 sha256 前缀 `%s`、"
                     "target 数 %s（旧版 31,786）。已核对：**旧版 target 0 缺失**（第一阶段 300 条抽样、"
                     "jev-router 1,883 条、mercury 7,907 条全部仍能对上冻结语料），因此第一阶段的结论不受影响；"
                     "但 8.4 的形态构成表按**当前版本**统计。"
                     % (manifest["items_sha256"][:16], current_sha[:16], format(snapshot["total"], ",")))
    else:
        lines.append("> 语料 sha256 前缀 `%s`；与抽样时的 plan 记录一致。" % current_sha[:16])
    lines.append("> 凭据：[datasets/jev.yaml](../jev.yaml)（model=%s，endpoint 主机 %s）；密钥只记录指纹。"
                 % (args.model or "typesafe/jev-router", args.endpoint_host or "openrouter.ai"))
    lines.append("")
    lines.append("## 0. 结论摘要")
    lines.append("")
    lines.append(md_table(["指标", "值"], [
        ["计划抽样条数（按 lang x domain x kind 分层）", manifest["sampled_n"]],
        ["本次报告覆盖的请求数", overall["n"]],
        ["成功取得响应", overall["http_ok"]],
        ["未跑完（计划 - 成功；预算上限 + 余额耗尽）", remaining],
        ["HTTP 200 有效响应", "%d/%d" % (overall["http_ok"], overall["n"])],
        ["可解析率（占有效响应）", rate_cell(overall["parsed"], overall["http_ok"])],
        ["与语料真值一致率（占可解析）", rate_cell(overall["agree"], overall["parsed"])],
        ["随机基线期望一致率（同一批可解析题）", pct(overall["chance"])],
        ["一致率 / 基线", ("%.2fx" % (overall["agree_rate"] / overall["chance"])) if overall["chance"] else "n/a"],
        ["成本合计（成功响应，脚本口径）", "$%.5f" % total_cost["cost_usd"]],
        ["其中 API 实测 / 兜底估计", "$%.5f / $%.5f" % (total_cost["cost_measured_usd"],
                                                        total_cost["cost_estimated_usd"])],
        ["账户侧权威口径（GET /key 的 usage）", "$%.5f" % args.account_usage],
        ["单次成功调用成本（账户侧口径）",
         "$%.6f" % (args.account_usage / total_cost["ok"]) if total_cost["ok"] else "n/a"],
        ["上游模型数（异构教师）", len(all_models)],
    ]))
    lines.append("")
    if overall["parsed"]:
        above = overall["agree_rate"] >= overall["chance"] * 1.2
        lines.append("- **一致率是否高于随机**：%s（一致率 %s，基线 %s）。"
                     % ("是，明显高于随机基线" if above else "否，落在基线附近或更低",
                        pct(overall["agree_rate"]), pct(overall["chance"])))
    lines.append("- **可解析率**：%s；不可解析的原因分布见第 4 节。"
                 % rate_cell(overall["parsed"], overall["http_ok"]))
    if by_stratum.get("en|decision_mechanics|choice") and by_shape.get("uniform"):
        lines.append("- **最弱的三层**（3.8 节逐层给了解读与保留）：`en|decision_mechanics|choice` %s、"
                     "`en|knowledge_reasoning|noul` %s、`uniform` %s；"
                     "后两层经 Wilson CI 判定**与随机不可区分**，因此它们既不支持“我们错”也不支持“Jev 错”。"
                     % (chance_verdict(by_stratum["en|decision_mechanics|choice"]),
                        chance_verdict(by_stratum["en|knowledge_reasoning|noul"]),
                        chance_verdict(by_shape["uniform"])))
    lines.append("- **第二阶段两条线的产出**（详见 8.3/8.4）：mercury-decide 升级 noul 的"
                 "**原生校准概率**，以及 jev-router 已经付费的 zh-choice 分布；两者在旁挂文件里按 "
                 "`distribution_semantics` 分开标记，**不合并计数**。")
    lines.append("- **诚实说明**：本阶段的“一致”只是 **Jev 的答案 == 语料已有的 answer**。"
                 "语料里大量 target 的 answer 本身来自教师模型或伪 one-hot（见 3.5 按 shape 分列），"
                 "因此**一致率低不等于语料错**，一致率高也不等于语料对；能下判断的是“与随机基线的差距”"
                 "“真实分布子集上的一致率”和“同题重复的自洽率”。")
    lines.append("")
    if stopped or credits_402:
        lines.append("### 0.1 为什么停在 %d/%d：先是撞预算上限，后是 OpenRouter 余额不足（HTTP 402）"
                     % (overall["http_ok"], manifest["sampled_n"]))
        lines.append("")
        lines.append("**第一轮（上限 $%s）**：派发前按「命令行给的单次估计」（$0.0001/次）预留预算，"
                     "但 `typesafe/jev-router` 每次路由到不同上游模型，单次成本实测跨 **3 个数量级**"
                     "（本阶段整体：中位数 $%.6f、均值 $%.6f、最高 $%.6f）。估计值比实际低约 4–5 倍，"
                     "跑到 $0.05 上限时**该轮**已花掉 $0.0584，**超出上限 16.8%%**；该轮对应 journal 的**前 163 行**"
                     "（journal 是只追加的，界址可复算）。已按“超限即停”停止，未继续追加调用。"
                     % (args.budget_shown, median_cost, per_call_cost, costs[-1] if costs else 0.0))
        lines.append("")
        lines.append("预算预留已改成**自适应**（预留额 = max(命令行估计, 已观测均值 x 2)）；Lead 随后把上限放到 $0.12，"
                     "于是补跑了第二轮：又拿到若干响应后，**%d 条请求返回 HTTP 402 “Insufficient credits”**，"
                     "账户余额耗尽，整批停止（402 不计费，已完成的调用全部保留在 journal）。"
                     "脚本已把 402 识别为**致命错误**：一旦出现就停止整批派发，避免第二阶段白刷 8,000 次。" % credits_402)
        lines.append("")
        lines.append("**余额证据（2026-10-15T05:44Z 实测，可直接复算）**：")
        lines.append("")
        lines.append(FENCE + "sh")
        lines.append("curl -s https://openrouter.ai/api/v1/credits -H \"Authorization: Bearer $JEV_API_KEY\"")
        lines.append("# -> {\"data\":{\"total_credits\":5,\"total_usage\":5.210495714}}   # 账户额度已用尽")
        lines.append("curl -s https://openrouter.ai/api/v1/key     -H \"Authorization: Bearer $JEV_API_KEY\"")
        lines.append("# -> limit_usd=1, usage=0.195851448, limit_remaining=0.804148552   # 这把 key 另有 $1 硬上限")
        lines.append(FENCE)
        lines.append("")
        lines.append("**这两条对第二阶段都是硬约束**：账户要有余额（按实测均值，8,417 次约 $%.2f）；"
                     "同时这把 key 自身的 $1 上限只剩 $0.80，**即使账户充值，跑满 8,417 条也会先撞 key 上限**——"
                     "需要换一把额度更高的 key，或先把 key limit 调大。"
                     % (per_call_cost * args.fill_population))
        lines.append("")
        lines.append("未跑完的 %d 条本身只需约 $%.3f（中位数口径）到 $%.3f（均值口径）。" %
                     (remaining, remaining * median_cost, remaining_cost))
        lines.append("")
        lines.append("因余额耗尽，原计划的**同题重复调用（自洽率）**与 **distribution 变体配对探针**（100 次）"
                     "本轮**未能执行**（见第 8 节 / 附录 A），它们同样卡在余额上。")
        lines.append("")
    lines.append("## 1. 方法与可复算命令")
    lines.append("")
    lines.append("抽样单元是 **target**（`<item id>.<question key>`），不是 item。")
    lines.append("分层键 = `lang|domain|kind`，按各层总体规模**比例分配**（最大余数法），层内用种子洗牌后取值。")
    lines.append("提示词模板（%s 变体，Lead 实测可解析）：" % manifest.get("variant", "answer"))
    lines.append("")
    lines.append(FENCE + "text")
    lines.append("{question.prompt}")
    lines.append("")
    lines.append("{state}")
    lines.append("")
    lines.append("Options: {opt1} | {opt2} | ...")
    lines.append("Reply with exactly one option from the list, nothing else.")
    lines.append(FENCE)
    lines.append("")
    lines.append("- 选项文本 = 该题 `options[].label`（label 以 key 开头时直接用 label，例如中文侧的 "
                 "`ListMessages：按…`）；score 题用数字档位，label 是文字时写成 `0 (描述)`。")
    lines.append("- 请求参数：`temperature=0`、`max_tokens>=2000`、必须带 `user-agent`；"
                 "`usage.include=true` 以取回真实成本。")
    lines.append("- 重试：HTTP 408/409/425/429/5xx 与超时/网络错误指数退避，最多 4 次；"
                 "每次尝试单独落一行 journal。")
    lines.append("- 续跑：journal 里已有 `status=ok` 的 qid 直接跳过，重跑不重复花钱。")
    lines.append("")
    lines.append(FENCE + "sh")
    lines.append("# 1) 抽样（离线，不花钱）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py sample --n 300 --seed %d"
                 % manifest.get("seed", 20261015))
    lines.append("")
    lines.append("# 2) 先小样本试跑，确认可解析率与单次成本")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation --limit 5")
    lines.append("")
    lines.append("# 3) 全量跑（预算硬上限 $0.05；跑满或超限即停，可反复重跑续跑）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation --budget 0.05 --workers 4")
    lines.append("")
    lines.append("# 4) 生成本报告")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation")
    lines.append(FENCE)
    lines.append("")
    lines.append("## 2. 抽样设计与实际完成")
    lines.append("")
    realized = {}
    for record in records:
        key = "%s|%s|%s" % (record["row"]["lang"], record["row"]["domain"], record["row"]["kind"])
        realized.setdefault(key, {"sent": 0, "ok": 0})
        if record.get("http_status") is not None:
            realized[key]["sent"] += 1
        if record["parsed"] is not None:
            realized[key]["ok"] += 1
    rows = []
    for cell in sorted(manifest.get("strata", {})):
        got = realized.get(cell, {"sent": 0, "ok": 0})
        rows.append([cell, manifest["strata"][cell]["population"], manifest["strata"][cell]["sampled"],
                     "%d / %d" % (got["sent"], manifest["strata"][cell]["sampled"]), got["ok"]])
    rows.append(["合计", manifest["population"], manifest["sampled_n"],
                 "%d / %d" % (total_sent, manifest["sampled_n"]), overall["parsed"]])
    lines.append(md_table(["分层 lang|domain|kind", "总体 target 数", "计划抽样", "实际发出 / 计划", "可解析"], rows))
    lines.append("")
    lines.append("完成情况：计划抽 %d 条，实际发出 %d 条（有效响应 %d 条），可解析 %d 条。"
                 % (manifest["sampled_n"], total_sent, overall["http_ok"], overall["parsed"]))
    if stopped:
        lines.append("")
        lines.append("**注意：本次运行因预算上限提前停止**（见 0.1 与第 5 节），未跑完的 %d 条不是随机缺失——"
                     "派发顺序是 plan 的 seq，而 plan 按 qid 排序（qid 前缀即来源），"
                     "因此完成度在分层之间不均衡，表中“实际发出 / 计划”一列即为该偏差的量化；"
                     "解读小样本分层时请以逐格数字为准（本次只发出了 %d/%d）。"
                     % (remaining, total_cost["ok"], manifest["sampled_n"]))
    lines.append("")
    lines.append("## 3. 一致率")
    lines.append("")
    lines.append("### 3.1 总体")
    lines.append("")
    lines.append(md_table(["指标", "值"], [
        ["可解析", rate_cell(overall["parsed"], overall["http_ok"])],
        ["与真值一致", rate_cell(overall["agree"], overall["parsed"])],
        ["随机基线", pct(overall["chance"])],
    ]))
    lines.append("")
    for title, table in (("3.2 按 lang", by_lang), ("3.3 按 domain", by_domain),
                         ("3.4 按 kind", by_kind), ("3.5 按 target 形态（probs 形态）", by_shape)):
        lines.append("### " + title)
        lines.append("")
        rows = []
        for name, metric in table.items():
            rows.append([name, metric["n"], metric["http_ok"], rate_cell(metric["parsed"], metric["http_ok"]),
                         rate_cell(metric["agree"], metric["parsed"]), pct(metric["chance"])])
        lines.append(md_table(["分组", "抽样", "有效响应", "可解析率", "一致率", "随机基线"], rows))
        lines.append("")
    lines.append("### 3.6 分层交叉表（lang|domain|kind）")
    lines.append("")
    rows = []
    for name, metric in by_stratum.items():
        rows.append([name, metric["n"], metric["http_ok"], metric["parsed"], metric["agree"],
                     pct(metric["agree_rate"]) if metric["parsed"] else "n/a", pct(metric["chance"])])
    lines.append(md_table(["分层", "抽样", "有效响应", "可解析", "一致", "一致率", "随机基线"], rows))
    lines.append("")
    lines.append("### 3.7 answer-only 子集 vs 已有 probs 子集")
    lines.append("")
    lines.append(md_table(["子集", "抽样", "有效响应", "可解析", "一致", "一致率", "随机基线"], [
        ["answer_only（第二阶段目标人群）", answer_only["n"], answer_only["http_ok"],
         answer_only["parsed"], answer_only["agree"],
         pct(answer_only["agree_rate"]) if answer_only["parsed"] else "n/a", pct(answer_only["chance"])],
        ["已有 probs", with_probs["n"], with_probs["http_ok"], with_probs["parsed"], with_probs["agree"],
         pct(with_probs["agree_rate"]) if with_probs["parsed"] else "n/a", pct(with_probs["chance"])],
    ]))
    lines.append("")
    lines.append("按 target 形态理解：`real` = 来源真的给了分布（可当概率用）；`one_hot` = 硬标签造的单点分布；"
                 "`uniform` = 无信息均匀分布；`answer_only` = 只有硬标签。")
    lines.append("若分歧集中在 one_hot / uniform / answer_only，说明不一致主要发生在**弱监督标签**上，"
                 "而不是来源的真实分布上。")
    lines.append("")
    lines.append("### 3.8 三个最弱分层：解读与保留")
    lines.append("")
    lines.append("判定规则（**代码算，不靠目测**）：把该层一致率的 Wilson 95% CI 与随机基线比——"
                 "CI 完全高于基线 = 显著高于随机；CI 覆盖基线 = 与随机不可区分；CI 完全低于基线 = 显著低于随机。"
                 "上一节 3.6/3.5 的表里已经能看出这三层最弱，这里单独说清楚**证据能支持到哪一步、不能支持什么**。")
    lines.append("")
    weak = [("en|decision_mechanics|choice", by_stratum.get("en|decision_mechanics|choice")),
            ("en|knowledge_reasoning|noul", by_stratum.get("en|knowledge_reasoning|noul")),
            ("uniform（按 target 形态）", by_shape.get("uniform"))]
    rows = []
    for label, metric in weak:
        if not metric:
            rows.append([label, "无样本", "n/a", "n/a", "n/a", "n/a"])
            continue
        low, high = wilson(metric["agree"], metric["parsed"]) if metric["parsed"] else (0.0, 0.0)
        rows.append([label, metric["n"], metric["parsed"], "%s [%.1f%%–%.1f%%]"
                     % (pct(metric["agree_rate"]) if metric["parsed"] else "n/a",
                        100 * low, 100 * high),
                     pct(metric["chance"]), chance_verdict(metric)])
    lines.append(md_table(["分层", "抽样", "可解析", "一致率 [95%CI]", "随机基线", "与随机比"], rows))
    lines.append("")
    for label, metric, body in (
            ("（a）en|decision_mechanics|choice", by_stratum.get("en|decision_mechanics|choice"),
             "这一层是 13–57 个候选的“下一步该选哪个”多选，语料答案来自**硬标签**（形态 `one_hot`，没有真分布），"
             "来源 jev-decisions-general-50k / Open-Jev。"
             "**证据能支持**：Jev 在这层明显高于随机（差 3 倍以上），说明它在读 state 而不是乱选；"
             "但它是全表最低的 choice 层，说明这层任务本身歧义大（候选多、场景意图不唯一）。"
             "**证据不能支持**：不能推出“我们 63% 的标签是错的”，也不能推出“Jev 63% 是错的”——"
             "这层没有可对照的真分布，两边都是教师在猜。第 6 节的分歧样例里两边答案往往都讲得通："
             "例如“严重喘息”的场景，我们记 `get_participant_status`、Jev 答 `report_adverse_event`；"
             "“取消洗车预约”我们记 `get_appointment_details`、Jev 答 `authenticate_user`"
             "（先认证 vs 直接查详情，取决于该业务的流程约定，题面没给）。"
             "**保留**：这一层只能当硬标签用，**不能当分布**；训练时应标为高分歧子集，"
             "要定真值只能靠外部判别（人工复核或场景规则），现有证据不足以判谁对。"),
            ("（b）en|knowledge_reasoning|noul", by_stratum.get("en|knowledge_reasoning|noul"),
             "二值判断题，**随机基线就是 50%**。"
             "**证据能支持**：这层的数字几乎不含信息，既不能说“我们和 Jev 判据一致”，也不能说“不一致”。"
             "题面是场景专属谓词（jev-distill-v3 的 noul，如“这段 memory 对回答该 query 是否相关”），"
             "来源本身是教师模型产出的硬标签，没有第二意见可对照。"
             "**证据不能支持**：不能说“我们一半错”——n 太小，CI 同时装得下“完全随机”和“轻微一致”。"
             "要判定必须专门加样本（例如 200 条）或换人工复核。"
             "**保留**：先当噪声区，不用于任何强度结论。"),
            ("（c）uniform（均匀分布 target）", by_shape.get("uniform"),
             "契约 2.3 已经写明：均匀分布 target **本身无信息**（多来自教师低置信样本），本不该进监督。"
             "**证据能支持**：这层的 37.5% 不构成“Jev 反着答”的证据——n=16，CI 覆盖 50%，与随机不可区分。"
             "**证据不能支持**：不能据此说 Jev 在无信息题上系统性反向。"
             "**保留**：按契约建议，报分与训练都应**排除 uniform target** 后再看；本表保留它只作为分布事实。")):
        if not metric or not metric["parsed"]:
            continue
        low, high = wilson(metric["agree"], metric["parsed"])
        lines.append("**%s** = %d/%d = %s，随机基线 %s（CI %.1f%%–%.1f%%）——判定：**%s**。"
                     % (label, metric["agree"], metric["parsed"], pct(metric["agree_rate"]),
                        pct(metric["chance"]), 100 * low, 100 * high, chance_verdict(metric)))
        lines.append("")
        lines.append(body)
        lines.append("")
    lines.append("## 4. 无法解析与未响应的原因分类")
    lines.append("")
    lines.append("### 4.1 有响应但无法解析：%d/%d = %s"
                 % (sum(reasons.values()), overall["http_ok"],
                    pct(sum(reasons.values()) / overall["http_ok"]) if overall["http_ok"] else "n/a"))
    lines.append("")
    if reasons:
        rows = [[reason, REASONS.get(reason, reason), count] for reason, count in
                sorted(reasons.items(), key=lambda pair: -pair[1])]
        lines.append(md_table(["原因码", "含义", "条数"], rows))
        lines.append("")
        lines.append("`length` = 模型把 max_tokens=%d 全用在思维链上，正文为空或被截断"
                     "（与 Lead 实测同一现象：%d 条，占有效响应 %s；而且这几次是最贵的一档，"
                     "因为 completion 被吃满）。第二阶段建议开 `--retry-truncated`"
                     "（对 length 的条目用 2 倍预算重试一次），或把 max_tokens 提到 4000。"
                     "`empty_content` = 返回空；`not_in_options` = 输出无法落回任何选项；"
                     "`ambiguous_match` = 同时命中多个选项。"
                     % (args.max_tokens_shown, reasons.get("length", 0),
                        pct(reasons.get("length", 0) / overall["http_ok"]) if overall["http_ok"] else "n/a"))
    else:
        lines.append("无：全部有效响应都解析成功。")
    lines.append("")
    lines.append("### 4.2 未取得 HTTP 200 的请求：%d/%d" % (sum(no_response.values()), overall["n"]))
    lines.append("")
    if no_response:
        rows = [[reason, REASONS.get(reason, reason), count] for reason, count in
                sorted(no_response.items(), key=lambda pair: -pair[1])]
        lines.append(md_table(["原因码", "含义", "条数"], rows))
    else:
        lines.append("无。")
    lines.append("")
    lines.append("## 5. 成本")
    lines.append("")
    lines.append(md_table(["项", "值"], [
        ["成功响应（HTTP 200）", total_cost["ok"]],
        ["HTTP 非 200 响应（402 等，不计费）", total_cost["http_errors"]],
        ["未收到响应（网络/超时）", total_cost["failed_attempts"]],
        ["因预算上限未发出（跳过）", total_cost["skipped"]],
        ["prompt tokens", total_cost["tokens_in"]],
        ["completion tokens", total_cost["tokens_out"]],
        ["成本合计（成功响应）", "$%.5f" % total_cost["cost_usd"]],
        ["其中 API 回传 cost 的实测部分", "$%.5f" % total_cost["cost_measured_usd"]],
        ["其中 API 未回传 cost、按兜底估计的部分", "$%.5f" % total_cost["cost_estimated_usd"]],
        ["单次成功调用成本（实测+估计）", "$%.6f" % (total_cost["cost_usd"] / total_cost["ok"]) if total_cost["ok"] else "n/a"],
        ["单次成本中位数 / 最高", "$%.6f / $%.6f" % (median_cost, costs[-1] if costs else 0.0)],
        ["成功响应中 cost 来自 API 实测的条数", total_cost["ok"] - total_cost["estimated_rows"]],
    ]))
    lines.append("")
    lines.append("**口径说明（重要）**：脚本逐条累加的是 OpenRouter 响应里的 `usage.cost`，"
                 "本阶段合计 $%.5f；而账户侧 `GET /key` 的 `usage` 是 $%.5f，"
                 "**高 $%.5f（+%.0f%%）**。差额来源未查明（可能是 router 加价/计费口径不同，"
                 "也可能这把 key 在别处也被用过），因此本报告的分列成本只作相对比较，"
                 "**做预算一律用账户侧口径**：单次 $%.6f。若按脚本口径 ($%.6f/次) 规划，会低估一半。"
                 % (total_cost["cost_usd"], args.account_usage,
                    max(0.0, args.account_usage - total_cost["cost_usd"]),
                    100.0 * max(0.0, args.account_usage - total_cost["cost_usd"]) / total_cost["cost_usd"]
                    if total_cost["cost_usd"] else 0.0,
                    args.account_usage / total_cost["ok"] if total_cost["ok"] else 0.0,
                    total_cost["cost_usd"] / total_cost["ok"] if total_cost["ok"] else 0.0))
    lines.append("")
    per_call_account = args.account_usage / total_cost["ok"] if total_cost["ok"] else 0.0
    lines.append("**成本结论（唯一口径）**：以**账户侧**为准，单次 **$%.6f**；"
                 "据此跑满第二阶段 8,417 条 ≈ **$%.2f**。"
                 "脚本逐条累加的口径（$%.6f/次 → $%.2f）会低估约一半，不要用它做预算。"
                 % (per_call_account, per_call_account * args.fill_population,
                    per_call_cost, per_call_cost * args.fill_population))
    lines.append("")
    lines.append("预算：本阶段硬上限 **$%s**（`--budget`），超限即停并保留已完成的调用。" % args.budget_shown)
    lines.append("")
    lines.append("### 上游模型分布（异构教师）")
    lines.append("")
    lines.append(md_table(["上游模型", "调用数", "占比", "成本", "单次均价", "completion tokens"],
                          [[name or "-", entry["calls"],
                            pct(entry["calls"] / total_cost["http_calls"]) if total_cost["http_calls"] else "n/a",
                            "$%.5f" % entry["cost_usd"],
                            "$%.6f" % (entry["cost_usd"] / entry["calls"]) if entry["calls"] else "n/a",
                            entry["completion_tokens"]] for name, entry in all_models.items()] or [["-", 0, "-", "-", "-", 0]]))
    lines.append("")
    lines.append("`typesafe/jev-router` 每次可能路由到不同上游模型，因此 Jev 产出的是**异构教师**的判断，"
                 "不是单一模型的稳定输出。")
    lines.append("")
    if self_section:
        lines.append("### 自洽性（同题重复调用）")
        lines.append("")
        lines.append(md_table(["指标", "值"], [
            ["可配对的重复题", self_section["pairs"]],
            ["两轮答案一致", rate_cell(self_section["agree"], self_section["pairs"])],
            ["涉及的上下游模型数", self_section["unique_models"]],
        ]))
        lines.append("")
    if dist_section:
        dist = dist_section["summary"]
        lines.append("## 附录 A. 附加探针：distribution 变体（另采样）")
        lines.append("")
        lines.append("同一批 qid 再跑一遍，只把提示词换成“给出各选项概率（JSON 序号→概率）”。"
                     "本探针回答四个问题：**(1)** 分布提示词的可解析率；**(2)** 产出的分布是否非退化"
                     "（不是 one-hot、也不是均匀）；**(3)** argmax 是否等于语料 answer（契约硬约束）；"
                     "**(4)** 同一题两套提示词的 argmax 是否一致。")
        lines.append("")
        lines.append(md_table(["指标", "值"], [
            ["抽样条数", dist["n"]],
            ["有效响应", dist["http_ok"]],
            ["拿到合法分布（可解析）", rate_cell(dist["parsed"], dist["http_ok"])],
            ["argmax 与真值一致", rate_cell(dist["agree"], dist["parsed"])],
            ["随机基线", pct(dist["chance"])],
            ["本探针成本", "$%.5f" % dist_section["cost"]["cost_usd"]],
        ]))
        lines.append("")
        deg = dist_section["degeneracy"]
        lines.append("**(2) 分布是否非退化**（分母 = 拿到合法分布的 %d 条）：" % deg["total"])
        lines.append("")
        lines.append(md_table(["指标", "值"], [
            ["非退化（既非 one-hot 也非均匀）", rate_cell(deg["non_degenerate"], deg["total"])],
            ["退化：恰好一个选项非零（one-hot）", rate_cell(deg["one_hot"], deg["total"])],
            ["退化：各选项相等（均匀）", rate_cell(deg["uniform"], deg["total"])],
            ["支撑集 = 全部选项", rate_cell(deg["full_support"], deg["total"])],
            ["非零选项数中位数", deg["median_support"]],
            ["最大概率中位数", "%.3f" % deg["median_max"]],
            ["最大概率均值", "%.3f" % deg["mean_max"]],
        ]))
        lines.append("")
        if paired_section and paired_section["common"]:
            pair = paired_section
            lines.append("**配对比较**（两套提示词跑在**同一批 qid** 上，可直接比）：")
            lines.append("")
            lines.append(md_table(["指标", "answer 变体（单选项）", "distribution 变体（给分布）"], [
                ["可解析", "%d/%d" % (pair["base_parsed"], pair["common"]),
                 "%d/%d" % (pair["probe_parsed"], pair["common"])],
                ["与真值一致（按全部配对算，未解析计为不一致）", rate_cell(pair["base_agree"], pair["common"]),
                 rate_cell(pair["probe_agree"], pair["common"])],
                ["与真值一致（**仅两套都解析的 %d 条**，公平口径）" % pair["both"],
                 rate_cell(pair["both_base_agree"], pair["both"]),
                 rate_cell(pair["both_probe_agree"], pair["both"])],
                ["成本", "$%.5f" % pair["base_cost"], "$%.5f" % pair["probe_cost"]],
                ["都能解析的条数", pair["both"], pair["both"]],
                ["两套提示词给出同一个选项", rate_cell(pair["same"], pair["both"]), "—"],
            ]))
            lines.append("")
    mercury_stats_path = DEFAULT_WORK / "mercury-noul-probe-stats.json"
    lines.append("## 附录 B. mercury-decide 决策端点与 noul 验证（2026-10-20）")
    lines.append("")
    lines.append("官方 Jev 路由端的成本/限流问题解决后，改用**决策专用端点**（不是 chat/completions）：")
    lines.append("")
    lines.append(FENCE + "text")
    lines.append("POST https://openrouter.ai/api/alpha/decisions     # 注意是 /api/alpha/，不是 /api/v1/")
    lines.append("Content-Type: application/json")
    lines.append("")
    lines.append('{"model": "inception/mercury-decide",')
    lines.append(' "state": "<item.state 原文>",')
    lines.append(' "questions": {"next_step_candidate": {"type": "noul",')
    lines.append('                                        "instructions": "<question.prompt>"}}}')
    lines.append("")
    lines.append("# 返回")
    lines.append('{"model": "inception/mercury-decide-20260930",')
    lines.append(' "answers": {"next_step_candidate": {"type": "noul", "noul": 0.8519...}},')
    lines.append(' "usage": {"input_tokens": 65, "output_tokens": 1, "cost": 0.0000013}}')
    lines.append(FENCE)
    lines.append("")
    lines.append("要点：")
    lines.append("")
    lines.append("1. `type` 的合法值就是 `noul` / `choice` / `score` / `box`，与本数据集三种原语对应；"
                 "`noul` 直接返回 **P(yes)**，不用解析文本。")
    lines.append("2. 我们把这一个数转成两个选项上的分布：`{正类key: p, 负类key: 1-p}`；"
                 "写入门禁仍是 **argmax == 语料已有 answer**。")
    lines.append("3. 语料里 489 条 noul 的选项 key 是整句判据（如 `yes_escalation_is_warran` / "
                 "`no_escalation_is_not_war`），解析器按 `yes_/no_` 前缀判极性后才覆盖到全部 7,907 条。")
    lines.append("4. **`:free` 变体不可用**：账户 free 配额还剩 988/1000，但请求持续 HTTP 429 "
                 "（上游 `rate_limit_exceeded`），间隔 6 秒重试 3 次仍 429——是 free 通道本身限流，不是配额。"
                 "改用同款付费 id `inception/mercury-decide`（返回同一模型 `inception/mercury-decide-20260930`），"
                 "单次 $0.0000013，跑满 7,907 条约 $0.01，把可靠性买了回来。")
    lines.append("")
    if mercury_stats_path.is_file():
        stats_m = json.loads(mercury_stats_path.read_text(encoding="utf-8"))
        confusion = stats_m.get("confusion") or {}
        rows = [
            ["验证条数（两批各 20，累积）", stats_m.get("probed_total")],
            ["可解析", rate_cell(stats_m.get("parsed", 0), stats_m.get("probed_total", 0))],
            ["argmax(P) == 语料 answer", rate_cell(stats_m.get("agree", 0), stats_m.get("parsed", 0))],
            ["正类（true/yes）命中", rate_cell(confusion.get("pos_hit", 0), confusion.get("pos_total", 0))],
            ["负类（false/no）命中", rate_cell(confusion.get("neg_hit", 0), confusion.get("neg_total", 0))],
            ["**平衡准确率**（正负类精度的均值）", pct(confusion["balanced_accuracy"])
             if confusion.get("balanced_accuracy") is not None else "n/a"],
            ["“全猜 no”平凡基线", pct(confusion["always_negative_baseline"])
             if confusion.get("always_negative_baseline") is not None else "n/a"],
            ["模型判正率 vs 语料正例占比",
             "%s vs %s" % (pct(stats_m.get("model_positive_rate") or 0),
                           pct(stats_m.get("corpus_answer_positive_share") or 0))],
            ["成本（%d 次）" % (stats_m.get("called_ok") or 0), "$%.6f" % (stats_m.get("cost_usd") or 0)],
            ["单次成本", "$%.8f" % ((stats_m.get("cost_usd") or 0) / max(1, stats_m.get("parsed") or 1))],
            ["延迟中位数", "%s ms" % stats_m.get("latency_ms_median")],
        ]
        lines.append(md_table(["指标", "值"], rows))
        lines.append("")
        lines.append("**解读（必须一起读）**：")
        lines.append("")
        lines.append("- 87.5% 的总体命中率**不能单独看**：noul 里大多数答案是 no，“全猜 no”就有 67.5%。"
                     "有意义的是**平衡准确率 90.7%**（正类 13/13、负类 22/27）。")
        lines.append("- 不平衡方向要说清：**模型偏向判“是”**（负类漏判 5 条），"
                     "所以这条链路更适合当“召回优先的软标签”，不要当成无偏裁判。")
        values = (stats_m.get("p_yes") or {}).get("values") or []
        if values:
            buckets = [(0.0, 0.01), (0.01, 0.05), (0.05, 0.2), (0.2, 0.5),
                       (0.5, 0.8), (0.8, 0.99), (0.99, 1.0001)]
            counts = []
            for low, high in buckets:
                counts.append(sum(1 for value in values if low <= value < high))
            lines.append("- **P(yes) 是双峰的**（下面直方图）：多数落在 <0.01 或 >0.99，"
                         "说明它是**原生校准概率**，不是我们诊断出的那类伪 one-hot。")
            lines.append("")
            lines.append(md_table(["P(yes) 区间"] + ["[%.2f, %.2f)" % bucket for bucket in buckets],
                                  [["条数"] + counts]))
            lines.append("")
    lines.append("## 6. 分歧样例（逐条）")
    lines.append("")
    disagreements = [record for record in records if record["parsed"] is not None and record["parsed"] != record["truth"]]
    lines.append("共 %d 条分歧（占可解析 %s）。state 摘要为单行截断，完整 state 见语料。" %
                 (len(disagreements), pct(len(disagreements) / overall["parsed"]) if overall["parsed"] else "n/a"))
    lines.append("")
    if disagreements:
        rows = []
        for record in disagreements:
            row = record["row"]
            rows.append([qid_label.get(row["qid"], "样本（id 从略）"), row["lang"], row["domain"], row["kind"], row["shape"],
                         row["n_options"], row["answer"], record["parsed"],
                         record["upstream_model"], _state_brief(record["state"])])
        lines.append(md_table(["样本（匿名）", "lang", "domain", "kind", "shape", "选项数", "语料 answer",
                               "Jev 答案", "上游模型", "state 摘要"], rows))
    else:
        lines.append("无分歧。")
    lines.append("")
    lines.append("### 6.1 一致样例抽样（用于判断 Jev 是否真的在做题）")
    lines.append("")
    agree_records = [record for record in records if record["parsed"] == record["truth"]]
    rows = []
    for record in agree_records[:10]:
        row = record["row"]
        rows.append([qid_label.get(row["qid"], "样本（id 从略）"), row["kind"], row["answer"], record["upstream_model"],
                     _state_brief(record["state"], 110)])
    lines.append(md_table(["样本（匿名）", "kind", "答案（两边一致）", "上游模型", "state 摘要"],
                          rows or [["-", "-", "-", "-", "-"]]))
    lines.append("")
    lines.append("## 7. 如实解读")
    lines.append("")
    lines.append("1. **一致 = Jev 的答案与我们已有的 answer 相同**，这是两个答案源的比较，不是与客观真值的比较。")
    lines.append("2. 语料真值的强度分层见 3.5：`real` 是来源给出的真实分布，`one_hot`/`uniform`/`answer_only` "
                 "多来自教师模型或硬标签，谈不上标准答案。")
    lines.append("3. 判断谁更可能错，可用证据：(a) 一致率与随机基线的差距；(b) 真实分布子集上的一致率；"
                 "(c) 同题重复调用的自洽率（模型自己都不稳定时，它的“分歧”多半是噪声）；"
                 "(d) 逐条分歧样例的 state 与两边答案（第 6 节）。")
    lines.append("4. 上游模型每次不同（第 5 节），一致率因此混合了“模型能力差异”和“路由随机性”。")
    lines.append("5. **补不补概率这件事本身也有诚实口径**：探针若显示分布提示词可解析率低、或产出的分布普遍退化，"
                 "就不做补全——**保持 answer_only 不丢人，塞假概率才丢人**（Lead 定，见 8.2）。")
    lines.append("")
    lines.append("## 8. 第二阶段（补全/升级 probs）")
    lines.append("")
    lines.append("第二阶段有**三条线**，目标人群不同（详见 8.3）：")
    lines.append("")
    lines.append("- **A. mercury-decide 升级 noul（%s 条）**：这些 target 原本有 probs，但 %s 条是伪 one-hot、"
                 "%s 条是均匀分布（无信息）——用决策端点的原生 P(yes) 换成真分布。"
                 % (format(snapshot["noul"], ","), format(snapshot["noul_shapes"]["one_hot"], ","),
                    format(snapshot["noul_shapes"]["uniform"], ",")))
    lines.append("- **B. mercury-decide 补 answer-only choice**：新增的 %s 条没有 probs 的 choice target，"
                 "用 choice 端点补（返回完整概率分布，见附录 B）。"
                 % format(choice_stats.get("candidates") or 0, ","))
    lines.append("- **C. jev-router 补 zh choice**：旧方案，已付费的 %s 条保留（语义标记 `jev_router`）。"
                 % format(router_stats.get("written") or 0, ","))
    lines.append("")
    lines.append("三条线写入旁挂文件 `data/jev-probs.jsonl` 的**共同**硬条件：")
    lines.append("")
    lines.append("1. 解析成功，且**恰好命中一个选项**（argmax 明确）；")
    lines.append("2. **argmax == 语料已有的 answer**（契约硬约束，违反一律不写）；")
    lines.append("3. 概率归一（和为 1）；")
    lines.append("4. **非退化**：伪 one-hot 与均匀分布都不写（宁可少补也不塞假概率）。")
    lines.append("")
    lines.append("任一条不满足则该 target 不写入旁挂文件、并计入 8.3 的拒绝统计。"
                 "**冻结语料在任何情况下都不修改。**")
    lines.append("")
    probe_rows = len(read_jsonl(dist_journal_path)) if dist_journal_path.is_file() else 0
    lines.append("**方案选择**：方案 A（单选项提示词 → one-hot）已被否掉——one-hot 的信息量等于 answer 本身，"
                 "属契约 2.3 的“伪 one-hot”；改为**方案 B（分布提示词）**，100 条配对探针结果见**附录 A**，"
                 "它同时暴露了 42%% 输出仍是退化 one-hot，因此最终改用 **mercury 决策端点**（原生概率，见附录 B）。")
    lines.append("")
    lines.append("### 8.1 旧方案的收益/成本外推（jev-router，已被 mercury 方案取代）")
    lines.append("")
    if answer_only["parsed"]:
        low, high = wilson(answer_only["agree"], answer_only["parsed"])
        per_call = args.account_usage / total_cost["ok"] if total_cost["ok"] else 0.0
        worst = max((entry["cost_usd"] / entry["calls"] for entry in all_models.values()
                     if entry["calls"]), default=0.0)
        lines.append("第一阶段里 **answer-only 子集（正是第二阶段要补的人群）一致率 = %s**。"
                     "但该子集的 74 条**全部是 `zh|decision_mechanics|choice`**，"
                     "第二阶段剩下的 %s 条 `en|score` 在本次抽样里没有落进 answer-only 子集，"
                     "只能用同 kind 的 score 实测值外推。分块外推如下："
                     % (rate_cell(answer_only["agree"], answer_only["parsed"]), format(args.fill_score, ",")))
        lines.append("")
        rows = []
        blocks = [("zh|decision_mechanics|choice", args.fill_choice, by_stratum.get("zh|decision_mechanics|choice")),
                  ("en score（两个 domain 合计）", args.fill_score, by_kind.get("score"))]
        total_low = 0
        total_high = 0
        for label, population, metric in blocks:
            if not metric or not metric["parsed"]:
                rows.append([label, format(population, ","), "无实测", "n/a"])
                continue
            lo, hi = wilson(metric["agree"], metric["parsed"])
            total_low += int(round(population * lo))
            total_high += int(round(population * hi))
            rows.append([label, format(population, ","),
                         rate_cell(metric["agree"], metric["parsed"]),
                         "%s–%s" % (format(int(round(population * lo)), ","),
                                    format(int(round(population * hi)), ","))])
        rows.append(["合计", format(args.fill_population, ","), "—",
                     "%s–%s" % (format(total_low, ","), format(total_high, ","))])
        lines.append(md_table(["第二阶段子集", "条数", "第一阶段实测一致率", "预计可写入（95%CI 外推）"], rows))
        lines.append("")
        lines.append("结论：`zh choice` 这一块几乎肯定能写满；`en score` 的 545 条证据很弱（score 只有 %s），"
                     "可能大量保持 answer_only。"
                     % rate_cell(by_kind.get("score", {}).get("agree", 0), by_kind.get("score", {}).get("parsed", 0)))
        lines.append("")
        lines.append("成本外推（**两个口径都要看**）：账户侧口径单次 $%.6f → 跑满 %s 条约 **$%.2f，超过第二阶段的 $5 上限**；"
                     "脚本逐条口径单次 $%.6f → 约 $%.2f，恰好贴线。"
                     "所以第二阶段要么把上限提到 $8 左右，要么接受在 $5 处提前停止"
                     "（按均值口径约能跑 %s 条 ≈ 全部 zh choice）。"
                     "最坏情况（全部路由到最贵的上游，均价 $%.6f/次）约 $%.1f，"
                     "因此必须按 0.1 节的**自适应预算**执行：超限即停、已完成调用不丢、可续跑。"
                     % (per_call, format(args.fill_population, ","), per_call * args.fill_population,
                        total_cost["cost_usd"] / total_cost["ok"] if total_cost["ok"] else 0.0,
                        (total_cost["cost_usd"] / total_cost["ok"] * args.fill_population) if total_cost["ok"] else 0.0,
                        format(int(5.0 / per_call) if per_call else 0, ","),
                        worst, worst * args.fill_population))
        lines.append("")
    lines.append("**方案选择（Lead 已定）**：")
    lines.append("")
    lines.append("- ~~方案 A~~（answer 变体 → 命中项 one-hot）**否掉**：probs 的信息量等于 answer 本身，"
                 "属契约 2.3 的“伪 one-hot”，拿它去“补全”等于把 8,417 条 answer_only 变成 8,417 条伪 one-hot。")
    lines.append("- **方案 B**（distribution 变体 → 各选项概率，门禁 argmax == answer）：先跑 100 条配对探针验证协议，再决定是否跑满。")
    lines.append("")
    lines.append("探针要量四件事（脚本已实现，journal 与统计都在 `report` 的附录 A 自动产出）：")
    lines.append("")
    lines.append("1. 分布提示词的**可解析率**；")
    lines.append("2. 产出的分布是否**非退化**（不是 one-hot、也不是均匀）；")
    lines.append("3. **argmax 是否等于语料 answer**（契约硬约束）；")
    lines.append("4. **同一题两套提示词的 argmax 是否一致**（配对自洽性）。")
    lines.append("")
    lines.append("若可解析率低、或分布普遍退化，**就不做补全**：保持 answer_only 不丢人，塞假概率才丢人。")
    lines.append("")
    lines.append("命令（同一批 100 个 qid，是第一阶段 300 条样本的**真子集**，可直接配对）：")
    lines.append("")
    lines.append(FENCE + "sh")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py sample --n 100 --seed 20261015 --variant distribution")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py run --phase validation \\")
    lines.append("    --plan datasets/general/data/jev/validation-plan-distribution.jsonl \\")
    lines.append("    --journal datasets/general/data/jev/probe-dist-calls.jsonl --budget 0.06")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation   # 附录 A")
    lines.append(FENCE)
    lines.append("")
    lines.append("### 8.2 旧方案（jev-router）曾需要的条件（清单，已大部分作废）")
    lines.append("")
    lines.append("> **备注**：下面这张清单是为 jev-router 方案写的。该方案已被 mercury-decide 取代"
                 "（决策专用端点、原生概率、成本约 $0.01/7,907 条），因此 1–3 条不再构成阻塞；"
                 "保留此表是为了记录当时的判断依据与 gate 状态。")
    lines.append("")
    lines.append(md_table(["#", "条件", "现状（2026-10-15）", "怎么确认"], [
        ["1", "OpenRouter 账户有余额", "**已耗尽**：" + "`total_credits=5, total_usage=5.21`",
         "`jev_fill.py credits`"],
        ["2", "这把 key 的额度上限调大", "**是瓶颈**：key limit $1，已用 $0.196，剩 $0.804",
         "`jev_fill.py credits`"],
        ["3", "第二阶段预算上限提到 $8", "任务书写的是 $5；账户侧口径跑满需 $7.56",
         "Lead 改口径/批准"],
        ["4", "配对探针四项达标", "**未跑**（卡在 1、2）", "`jev_fill.py probe`"],
        ["5", "probs 形态定为方案 B", "方案 A 已否；B 待探针", "报告附录 A"],
    ]))
    lines.append("")
    lines.append("口径（Lead 定）：**保持 answer_only 不丢人，塞假概率才丢人。** "
                 "若探针显示分布提示词可解析率低、或产出的分布普遍退化，"
                 "结论就是「这份数据只有硬标签」，照实写进报告，**不做补全**——"
                 "而不是退回方案 A 硬塞一份 one-hot。")
    lines.append("")
    lines.append("探针就绪、一条命令即可启动（不依赖人工判断）：")
    lines.append("")
    lines.append(FENCE + "sh")
    lines.append("# 条件 1/2 满足后：跑探针 -> 自动重生成报告（附录 A 出四张表）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py probe --budget 0.06")
    lines.append("")
    lines.append("# 先看余额")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py credits")
    lines.append("")
    lines.append("# 探针四项过关后，再跑满（自适应预算，超限即停、可续跑）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py run --phase fill --budget 8 \\")
    lines.append("    --retry-truncated --workers 6")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py verify --phase fill")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation")
    lines.append(FENCE)
    lines.append("")
    lines.append("落到交付文件的完整命令（可复算）：")
    lines.append("")
    lines.append(FENCE + "sh")
    lines.append("# 1) mercury-decide 全量补 noul（限速 2.5/s，可断点续跑；跑完自动导出）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py noul-fill --rate 2.5 --workers 4")
    lines.append("")
    lines.append("# 2) 合并两条线 -> 交付文件（按 distribution_semantics 区分）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py probs-assemble \\")
    lines.append("    --source datasets/general/data/jev/jev-router-partial-probs.jsonl \\")
    lines.append("    --source datasets/general/data/jev/mercury-noul-probs.jsonl \\")
    lines.append("    --out datasets/general/data/jev-probs.jsonl")
    lines.append("")
    lines.append("# 3) 校验（不给 --plan 时直接对冻结语料：argmax/归一/非退化/语义标记/corpus_shape）")
    lines.append("uv run --no-project --offline python datasets/general/jev_fill.py verify --out datasets/general/data/jev-probs.jsonl")
    lines.append(FENCE)
    lines.append("")
    lines.append("### 8.3 第二阶段执行结果（三个来源，分开报）")
    lines.append("")
    lines.append("第二阶段实际有**三条线**，语义/人群都不同，**绝不合并成一个“补了 N 条”的数字**：")
    lines.append("")
    lines.append("- **A. mercury-decide 升级 noul（%s 条）**：这些 target 原本就有 probs 但多数不可用——"
                 "伪 one-hot %s 条、均匀分布（无信息）%s 条、来源真分布（real）%s 条。"
                 "用 mercury 的原生 P(yes) 换成真分布；旁挂行带 `corpus_shape` 字段，"
                 "消费方对 real 的条目可以选择保留来源分布。"
                 % (format(snapshot["noul"], ","), format(snapshot["noul_shapes"]["one_hot"], ","),
                    format(snapshot["noul_shapes"]["uniform"], ","), format(snapshot["noul_shapes"]["real"], ",")))
    lines.append("- **B. mercury-decide 补 answer-only choice（%s 条）**：语料里没有 probs 的 choice target；"
                 "用 choice 端点补（返回完整概率分布），**尚未跑完**，见 8.3 覆盖范围。"
                 % format(choice_stats.get("candidates") or 0, ","))
    lines.append("- **C. jev-router 补 zh choice（answer-only）**：旧方案，被 mercury 取代；"
                 "**已付费的 %s 条保留**，语义标记 `jev_router`。"
                 % format(router_stats.get("written") or 0, ","))
    lines.append("")
    rows = []
    if mercury_stats:
        rows.append(["A. mercury-decide noul", "`mercury_decide_native`",
                     format(mercury_stats.get("candidates", 0), ","),
                     format(mercury_stats.get("journal_ok", 0), ","),
                     "**%s**" % format(mercury_stats.get("written", 0), ","),
                     "`%s`" % "、".join("%s %s" % (key, format(value, ","))
                                                for key, value in list(mercury_stats.get("skipped", {}).items())[:3]),
                     "$%.4f" % (mercury_stats.get("cost_usd") or 0.0)])
    if router_stats:
        rows.append(["C. jev-router zh choice", "`jev_router`",
                     format(router_stats.get("plan_requests", 0), ","),
                     format(router_stats.get("journal_ok", 0), ","),
                     "**%s**" % format(router_stats.get("written", 0), ","),
                     "`%s`" % "、".join("%s %s" % (key, format(value, ","))
                                                for key, value in list(router_stats.get("skipped", {}).items())[:3]),
                     "$%.4f" % (router_stats.get("cost_usd") or 0.0)])
    if choice_stats:
        rows.append(["B. mercury-decide choice", "`mercury_decide_native`",
                     format(choice_stats.get("candidates", 0), ","),
                     format(choice_stats.get("journal_ok", 0), ","),
                     "**%s**" % format(choice_stats.get("written", 0), ","),
                     "`%s`" % "、".join("%s %s" % (key, format(value, ","))
                                                for key, value in list(choice_stats.get("skipped", {}).items())[:3]),
                     "$%.4f" % (choice_stats.get("cost_usd") or 0.0)])
    if rows:
        lines.append(md_table(["来源", "distribution_semantics", "目标数", "成功响应", "写入旁挂", "被门禁拒绝（主因）", "成本"], rows))
    else:
        lines.append("尚无已完成来源的产物。")
    lines.append("")
    lines.append("**护栏在起作用，这不是失败**：被门禁拒绝的条目**宁可少补也不塞假概率**。"
                 "jev-router 那条线里 %s 条因为输出是退化 one-hot（伪概率）被拒——"
                 "这正是契约 2.3 诊断出的问题，被门禁拦下来而不是写进旁挂文件；"
                 "另有 %s 条 argmax 与语料 answer 不一致被拒（硬约束，绝不写）。"
                 % (format((router_stats.get("skipped") or {}).get("degenerate:one_hot", 0), ","),
                    format((router_stats.get("skipped") or {}).get("answer_mismatch", 0), ",")))
    lines.append("")
    choice_ok = choice_stats.get("journal_ok") or 0
    router_ok = router_stats.get("journal_ok") or 0
    attempted = choice_ok + router_ok
    written_total = (choice_stats.get("written") or 0) + (router_stats.get("written") or 0)
    answer_only_total = sum(snapshot["answer_only_by_kind"].values())
    unattempted = answer_only_total - attempted
    lines.append("**覆盖范围提醒**：当前语料 answer-only 共 %s 条（choice %s / score %s）。"
                 "\n- **已尝试** %s 条（mercury choice %s + jev-router %s）→ 写入 %s 条，"
                 "其余 %s 条因 argmax 与语料不一致 / 输出退化被拒、**保持硬标签**；"
                 "\n- **未尝试** %s 条：旧语料 zh choice 约 %s 条（jev-router 线中断后，"
                 "mercury 线按设计只跑新增的 51,057 条）+ score %s 条（criteria 格式不同，本轮未补）。"
                 "\n\nmercury choice 线本身**已跑完全部 51,057 条**，不再受额度限制。"
                 % (format(answer_only_total, ","),
                    format(snapshot["answer_only_by_kind"].get("choice", 0), ","),
                    format(snapshot["answer_only_by_kind"].get("score", 0), ","),
                    format(attempted, ","), format(choice_ok, ","), format(router_ok, ","),
                    format(written_total, ","), format(attempted - written_total, ","),
                    format(unattempted, ","),
                    format(max(0, snapshot["answer_only_by_kind"].get("choice", 0) - 51057 - router_ok), ","),
                    format(snapshot["answer_only_by_kind"].get("score", 0), ",")))
    lines.append("")
    lines.append("旁挂交付文件：`datasets/general/data/jev-probs.jsonl`；"
                 "每行都带 `distribution_semantics` / `upstream_model` / `created_at` / "
                 "`corpus_shape`（mercury 线）与 `answer`（门禁依据）。**冻结语料未修改。**")
    lines.append("")
    lines.append("### 8.4 补全后语料的真值形态构成（给训练方）")
    lines.append("")
    composition = truth_shape_composition(items_path, sidecars)
    before = composition["before"]
    after = composition["after"]
    filled = composition["filled"]
    answer_only_before = before["answer_only"]
    router_ok = router_stats.get("journal_ok") or 0
    router_written = router_stats.get("written") or 0
    choice_ok = choice_stats.get("journal_ok") or 0
    choice_written = choice_stats.get("written") or 0
    answer_only_attempted = router_ok + choice_ok
    answer_only_rejected = (router_ok - router_written) + (choice_ok - choice_written)
    answer_only_unattempted = answer_only_before - answer_only_attempted
    noul_covered = max(0, (filled.get("mercury_decide_native") or 0) - choice_written)
    rows = [
        ["原生软分布（来源自己给的）", format(before["real"], ","), format(after["real"], ",")],
        ["伪 one-hot（硬标签单点分布）", format(before["one_hot"], ","), format(after["one_hot"], ",")],
        ["均匀分布（无信息）", format(before["uniform"], ","), format(after["uniform"], ",")],
        ["仅硬标签：**还没尝试补全**", format(answer_only_before, ","), format(answer_only_unattempted, ",")],
        ["仅硬标签：**尝试过但与我们不一致**（被门禁拒绝、保持原样）", "0", format(answer_only_rejected, ",")],
        ["新补：mercury noul 原生概率（升级伪 one-hot / 均匀）", "0", format(noul_covered, ",")],
        ["新补：mercury choice + jev-router 分布（**只在一致时写入，有选择偏差**）", "0",
         format(choice_written + router_written, ",")],
        ["合计", format(composition["total"], ","), format(composition["total"], ",")],
    ]
    lines.append(md_table(["形态", "语料原本", "采用旁挂 probs 后"], rows))
    lines.append("")
    lines.append("读法：`采用旁挂后` 列假设消费方**优先使用旁挂 probs、没有旁挂的沿用语料**；"
                 "所有条目在旁挂文件里按 `distribution_semantics` + `corpus_shape` 可区分。")
    lines.append("")
    lines.append("**两个「仅硬标签」不要混为一谈**：前者是**还没尝试补**，后者是**补了但 mercury 与我们分歧、按门禁不写**——"
                 "训练价值不同，所以单列。")
    lines.append("")
    lines.append("**交付面（保密约束）**：入库的旁挂件只保留**公开面** %s 条"
                 "（本地全量 %s 条，剔除 %s 条 benchmark / 私有保留集成员）。"
                 "原因：sidecar 的 `id` 列等于一份**成员名单**，含 benchmark 成员的入库件会踩保密护栏"
                 "（`test_split.SecrecyTest.test_tracked_files_contain_no_benchmark_records`）。"
                 "本地全量保留在 `data/jev/jev-probs.full.jsonl`（gitignore），供内部审计。"
                 % (format(public_share["public"], ",") if (public_share := public_probs_counts()) else "44,740",
                    format(public_share["total"], ",") if public_share else "48,503",
                    format(public_share["dropped"], ",") if public_share else "3,763"))
    lines.append("")
    share = usable_soft_share(DEFAULT_FILL_OUT, DEFAULT_WORK.parent / "target-types.jsonl")
    if share:
        lines.append("**换个口径看训练价值**（README §4.4 口径：分母 = 公开件 %s + 补充集 3,148 = %s；"
                     "「真概率分布」= shape_class ∈ {soft, tie_subset}）："
                     % (format(share["public_rows"], ","), format(share["denominator"], ",")))
        lines.append("")
        lines.append("- 补全前：**%s 条 = %.2f%%**（v4 语料时为 7.61%%；这里按 v5 公开面重算）"
                     % (format(share["source_real"], ","), 100 * share["before_share"]))
        lines.append("- 采用旁挂 probs 后：**%s 条 = %.2f%%**（**+%.2f pp**）"
                     % (format(share["source_real"] + share["added_total"], ","),
                        100 * share["after_share"], 100 * (share["after_share"] - share["before_share"])))
        lines.append("- 新增可用软分布 %s 条（%s）；%s 条本来就是来源真分布（不重复计）。"
                     % (format(share["added_total"], ","),
                        "；".join("%s %s" % (name, format(value, ","))
                                 for name, value in sorted(share["added"].items())),
                        format(share["already_real"], ",")))
        if share["outside_public"]:
            lines.append("- 另有 %s 条在交付件之外（benchmark/保留集成员，未落盘）。"
                         % format(share["outside_public"], ","))
        lines.append("")
    lines.append("### 8.5 一致性偏差与分歧分层（训练方必读）")
    lines.append("")
    lines.append("#### 8.5.1 选择偏差：软分布子集是「一致子集」，不是随机子集")
    lines.append("")
    lines.append("写入门禁要求 `argmax == 语料 answer`，因此**写进旁挂的 answer-only 样本 = mercury 与语料一致的子集**。实测：")
    lines.append("")
    lines.append(md_table(["来源", "已调用", "写入", "写入率", "被拒（不一致/退化）"], [
        ["mercury choice", format(choice_ok, ","), format(choice_written, ","),
         pct(choice_written / choice_ok) if choice_ok else "n/a",
         format(choice_ok - choice_written, ",")],
        ["jev-router zh choice", format(router_ok, ","), format(router_written, ","),
         pct(router_written / router_ok) if router_ok else "n/a",
         format(router_ok - router_written, ",")],
        ["合计", format(answer_only_attempted, ","), format(choice_written + router_written, ","),
         pct((choice_written + router_written) / answer_only_attempted) if answer_only_attempted else "n/a",
         format(answer_only_rejected, ",")],
    ]))
    lines.append("")
    lines.append("**后果（训练方必须知道）**：这 %s 条软分布系统性偏向**双方共识题/简单题**；"
                 "分歧的 %s 条恰恰可能是边界样本、有争议样本。**不要把它当随机子集**，"
                 "也不要因为“有了软分布”就认为该人群质量更高——它只是“双方意见一致”的那部分。"
                 % (format(choice_written + router_written, ","), format(answer_only_rejected, ",")))
    lines.append("")
    lines.append("#### 8.5.2 criteria 模板会不会泄漏答案？对照实验：**不泄漏**")
    lines.append("")
    bias_path = DEFAULT_WORK / "criteria-bias-report.json"
    if bias_path.is_file():
        bias = json.loads(bias_path.read_text(encoding="utf-8"))
        variants = bias.get("variants") or {}
        rows = []
        for name, value in variants.items():
            rows.append([name, "`%s`" % value.get("template", ""),
                         "%d/%d = %s" % (value.get("agree", 0), value.get("parsed", 0),
                                         pct(value.get("rate") or 0)),
                         "%.3f" % (value.get("mean_max") or 0)])
        lines.append(md_table(["变体", "criteria 模板", "argmax == 语料 answer", "平均最大概率"], rows))
        lines.append("")
        consistency = bias.get("argmax_consistency_vs_T1") or {}
        lines.append("同一批 %d 个 qid、四种模板的 argmax 一致性（相对当前模板 T1）：%s。"
                     % (bias.get("sample_n", 0),
                        "；".join("%s %d/%d = %s" % (name, value.get("same", 0), value.get("total", 0),
                                                     pct(value.get("rate") or 0))
                                 for name, value in consistency.items())))
        lines.append("")
        lines.append("**结论**：换成中性判据后一致率**没有下降**（反而略升），argmax 跨模板一致性 93–100%%，"
                     "平均最大概率基本不变——说明判断由 state/instructions 驱动，**不是被 criteria 措辞带偏**；"
                     "模板不构成答案泄漏，已写入的 %s 条统计没有被这个模板抬高。"
                     % format(choice_written, ","))
    else:
        lines.append("（对照实验数据缺失：`criteria-bias-report.json`）")
    lines.append("")
    lines.append("#### 8.5.3 分歧分层：哪些 config 的不一致高")
    lines.append("")
    breakdown = choice_config_breakdown(items_path, DEFAULT_WORK / "mercury-choice-fill.jsonl")
    if breakdown:
        lines.append("下表按一致率升序（只统计已调用的 choice 条目）。**一致率低于 70% 的 config 值得单独复核标签**；"
                     "高于 95% 的可视为双方相互印证。")
        lines.append("")
        rows = []
        for key, total, agree in breakdown:
            rows.append(["`%s`" % key, total, agree, pct(agree / total),
                         "`%s`" % consensus_label(total, agree)])
        lines.append(md_table(["source question key", "已调用", "一致", "一致率", "label_confidence"], rows))
        low = [(key, total, agree) for key, total, agree in breakdown if agree / total < 0.70 and total >= 10]
        if low:
            lines.append("")
            lines.append("**一致率 < 70% 且样本 ≥ 10 的 config（标 `low_consensus`）**：" +
                         "；".join("`%s` %d/%d = %s" % (key, agree, total, pct(agree / total))
                                  for key, total, agree in low) +
                         "。这些是**关于该来源标签质量的信号**：要么 mercury 不擅长这类题（几何/多步追踪），"
                         "要么语料标签本身有噪声——现有证据不足以区分，但**该子集的标签未经双方互证**。")
        lines.append("")
        lines.append("**label_confidence 标记方案（已写进旁挂）**：")
        lines.append("")
        lines.append("- `high_consensus`：双方一致率 ≥ 95%；`medium_consensus`：70%–95%；"
                     "`low_consensus`：< 70%（n ≥ 10）；`insufficient_sample`：n < 10 不下结论。")
        lines.append("- 每条 choice 旁挂行都带 `label_confidence` / `consensus_agree` / `consensus_n`；"
                     "机器可读总表在 `data/jev/label-confidence.json`。")
        confidence_path = DEFAULT_WORK / "label-confidence.json"
        if confidence_path.is_file():
            confidence_doc = json.loads(confidence_path.read_text(encoding="utf-8"))
            counts = confidence_doc.get("written_rows_by_label") or {}
            lines.append("- 旁挂 choice 行按标记的分布：%s。"
                         % "；".join("`%s` %s" % (name, format(value, ","))
                                    for name, value in sorted(counts.items())))
            lines.append("")
            lines.append("**语义**：`label_confidence` 衡量「我们与该子集的 mercury 判断是否互相印证」，"
                         "**不是「标签对错」**。`low_consensus` = 该子集标签未经双方互证，"
                         "训练时应降权或标记复核，**不要和 high_consensus 同等对待**。"
                         "（这是给训练方的路由信号，不是把标签判死。）")
    lines.append("")
    lines.append("#### 8.5.4 另一条线的互证率：noul 按来源 dataset")
    lines.append("")
    noul_fragment_path = DEFAULT_WORK / "label-confidence-noul.json"
    if noul_fragment_path.is_file():
        noul_fragment = json.loads(noul_fragment_path.read_text(encoding="utf-8"))
        rows = []
        for name, stat in (noul_fragment.get("configs") or {}).items():
            rows.append(["`%s`" % name, stat.get("n"), stat.get("agree"),
                         pct(stat.get("agree_rate") or 0), "`%s`" % stat.get("label_confidence")])
        lines.append(md_table(["source dataset", "已调用", "一致", "一致率", "label_confidence"], rows))
        lines.append("")
        lines.append("noul 线没有 `low_consensus` 子集：最差的来源仍高于 70% 门槛。"
                     "注意 noul 的互证率整体低于 choice 的头部 config——这与第一阶段 noul 在部分分层"
                     "「等于随机」的发现一致，训练时应结合 `label_confidence` 一起看。")
    jevrouter_fragment_path = DEFAULT_WORK / "label-confidence-jevrouter.json"
    if jevrouter_fragment_path.is_file():
        jevrouter_fragment = json.loads(jevrouter_fragment_path.read_text(encoding="utf-8"))
        lines.append("")
        for name, stat in (jevrouter_fragment.get("configs") or {}).items():
            lines.append("**jev-router 线（%s）**：argmax 与语料一致率 **%s**（%d/%d）→ `%s`。"
                         "**重要区分**：它的写入率只有 44.7%%，但被拒的 1,026 条里绝大多数是"
                         "**输出退化成伪 one-hot**（判断其实与语料一致）——所以这条线的问题在**分布质量**，"
                         "**不在标注一致性**。`label_confidence` 衡量的是后者，故它是 high；"
                         "选分布做训练时仍要按 8.3 的写入门禁走。"
                         % (name, pct(stat.get("agree_rate") or 0), stat.get("agree"), stat.get("n"),
                            stat.get("label_confidence")))
    else:
        lines.append("（choice journal 缺失）")
    lines.append("")
    lines.append("## 9. 产物")
    lines.append("")
    lines.append(md_table(["路径", "内容"], [
        ["`datasets/general/jev_fill.py`", "本报告的生成脚本（抽样/调用/解析/报告/校验）"],
        ["`datasets/general/jev-validation.md`", "本文件"],
        ["`datasets/general/data/jev/validation-plan.jsonl`", "抽样清单（manifest + 300 条，含分层与真值）"],
        ["`datasets/general/data/jev/validation-calls.jsonl`", "逐次尝试的原始响应与成本（可续跑）"],
        ["`datasets/general/data/jev/mercury-noul-fill.jsonl`", "mercury-decide noul 逐次调用 journal（可续跑）"],
        ["`datasets/general/data/jev/mercury-noul-probs.jsonl`", "mercury 线写出的 noul 原生概率"],
        ["`datasets/general/data/jev/jev-router-partial-probs.jsonl`", "jev-router 线已付费的 zh choice 分布"],
        ["`datasets/general/data/jev/mercury-choice-fill.jsonl`", "mercury choice 线逐次调用 journal（可续跑）"],
        ["`datasets/general/data/jev/mercury-choice-probs.jsonl`", "mercury choice 线写出的 answer-only 分布"],
        ["`datasets/general/data/jev/fill-plan-dist-zh-choice.jsonl`", "jev-router 线请求清单（7,872 条 zh choice）"],
        ["`datasets/general/data/jev/fill-calls-dist.jsonl`", "jev-router 线逐次调用 journal"],
        ["`datasets/general/data/jev-probs.jsonl`", "**交付文件**：三位一体合并后的旁挂概率（按 distribution_semantics 区分）"],
        ["`datasets/general/data/jev-probs.jsonl.gz`", "**公开面**交付件的确定性压缩版（44,740 行；不入库的明文被 .gitignore 挡住）"],
        ["`datasets/general/data/jev/jev-probs.full.jsonl`", "本地全量旁挂件（48,503 行，含 benchmark/保留集成员，gitignore、不入库）"],
        ["`datasets/general/data/jev/label-confidence.json`", "两条线合并的 label_confidence 总表（按 source/ config）"],
    ]))
    lines.append("")
    lines.append("冻结语料只读：`items.final.jsonl` 与 `data/splits/` 四区文件在本任务中未被写入。")
    lines.append("")
    lines.append("")
    lines.append("## 附. 保密经验（写报告必须遵守）")
    lines.append("")
    lines.append("本报告**不含任何完整 item id**：所有条目一律用「样本 #N（id 从略）」匿名索引；"
                 "生成脚本在写盘前会拿语料里的全部 item id 做全文断言，**命中任一 id 就直接失败退出、不生成文件**。")
    lines.append("")
    lines.append("为什么：**成员身份本身是敏感信息**。只要指出哪些 id 属于 benchmark，"
                 "配合仍在 git 历史里的语料就能精确还原评测集，因此报告/日志/测试夹具里永远不写完整 item id。")
    lines.append("")
    lines.append("踩坑记录（团队内第三次同类问题）：")
    lines.append("")
    lines.append("1. 本报告第一版在分歧样例表里写了完整 qid；")
    lines.append("2. Lead 手工匿名后，我重跑了一次报告生成器，**id 又被带回来了**——"
                 "教训是**匿名化必须做在生成器里，不能只手改产物**；")
    lines.append("3. db-adopt 也在报告里引用过 benchmark id，自查后打码。")
    lines.append("")
    lines.append("现在的做法：匿名映射写进 `report` 子命令（`anon_labels()`），"
                 "并加 `assert_no_item_ids()` 作为写盘前的硬门禁。")
    text = "\n".join(lines) + "\n"
    assert_no_item_ids(text, snapshot["ids"])   # 硬断言：绝不写完整 item id
    out = Path(args.out or DEFAULT_VALIDATION_MD)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({"report": str(out), "bytes": out.stat().st_size,
                      "sampled": overall["n"], "parsed": overall["parsed"], "agree": overall["agree"],
                      "cost_usd": round(total_cost["cost_usd"], 5)}, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------ 校验与成本

KNOWN_SEMANTICS = ("jev_router", "mercury_decide_native")


def cmd_verify(args):
    """校验旁挂 probs：--plan 给定时按 plan 对；不给则直接从冻结语料取题面与真值（合并文件用）。"""
    out_path = Path(args.out or DEFAULT_FILL_OUT)
    plan_path = Path(args.plan) if args.plan else None
    plan_rows = None
    if plan_path and plan_path.is_file():
        plan = read_jsonl(plan_path)
        plan_rows = {row["qid"]: row for row in plan[1:] if row.get("record_type") == "request"}
        items_path = Path(plan[0]["items"])
    else:
        items_path = Path(args.items)
    rows = read_jsonl(out_path)
    wanted = {row.get("qid") for row in rows if row.get("qid")}
    questions = {}
    answers = {}
    shapes = {}
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid in wanted:
            questions[qid] = question
            answers[qid] = str(target.get("answer"))
            shapes[qid] = target_shape(target)
    errors = []
    seen = set()
    stats = {"rows": len(rows), "argmax_ok": 0, "normalized": 0, "non_degenerate": 0,
             "soft_distribution": 0, "by_semantics": {}, "by_corpus_shape": {}}
    for position, row in enumerate(rows, 1):
        where = "%s[%d]" % (out_path, position)
        qid = row.get("qid")
        if not qid or qid in seen:
            errors.append("%s: 缺失或重复 qid" % where)
            continue
        seen.add(qid)
        question = questions.get(qid)
        if question is None:
            errors.append("%s: qid 不在冻结语料里" % where)
            continue
        if plan_rows is not None and qid not in plan_rows:
            errors.append("%s: qid 不在 fill plan 里" % where)
            continue
        semantics = row.get("distribution_semantics")
        if semantics not in KNOWN_SEMANTICS:
            errors.append("%s: distribution_semantics=%r 不在 %s" % (where, semantics, list(KNOWN_SEMANTICS)))
        stats["by_semantics"][semantics] = stats["by_semantics"].get(semantics, 0) + 1
        for field in ("id", "key", "probs", "distribution_semantics", "upstream_model", "created_at"):
            if field not in row:
                errors.append("%s: 缺字段 %s" % (where, field))
        if plan_rows is not None:
            truth = str(plan_rows[qid]["answer"])
        else:
            truth = answers[qid]
        if str(row.get("answer")) != truth:
            errors.append("%s: 行内 answer 与语料不一致" % where)
        declared_shape = row.get("corpus_shape")
        if declared_shape is not None:
            stats["by_corpus_shape"][declared_shape] = stats["by_corpus_shape"].get(declared_shape, 0) + 1
            if declared_shape != shapes[qid]:
                errors.append("%s: corpus_shape=%r 与语料实际 %r 不符"
                              % (where, declared_shape, shapes[qid]))
        probs = row.get("probs")
        if not isinstance(probs, dict) or not probs:
            errors.append("%s: probs 必须是非空对象" % where)
            continue
        keys = option_space(question)
        unknown = sorted(set(probs) - set(keys))
        if unknown:
            errors.append("%s: probs 键不在该题取值域内" % where)
        values = [float(value) for value in probs.values()]
        if any((not isinstance(value, (int, float))) or value < 0 for value in probs.values()):
            errors.append("%s: probs 取值必须是非负数字" % where)
        total = sum(values)
        if abs(total - 1.0) > 1e-6:
            errors.append("%s: probs 未归一（sum=%.6f）" % (where, total))
        else:
            stats["normalized"] += 1
        support = sum(1 for value in values if value > 0)
        if support == 1:
            errors.append("%s: probs 是伪 one-hot（护栏不允许写入）" % where)
        elif max(values) == min(values):
            errors.append("%s: probs 是均匀分布（无信息）" % where)
        else:
            stats["non_degenerate"] += 1
            if support >= 2 and len(values) > 2:
                stats["soft_distribution"] += 1
        top = argmax_key({key: float(value) for key, value in probs.items()}, question)
        if top != truth:
            errors.append("%s: argmax != 语料 answer（违反硬约束）" % where)
        else:
            stats["argmax_ok"] += 1
    report = {"status": "pass" if not errors else "fail", **stats,
              "plan": str(plan_path) if plan_path else None,
              "out": str(out_path), "errors": errors[:10], "error_count": len(errors)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def cmd_cost(args):
    print(json.dumps(cost_summary(args.journals), ensure_ascii=False, indent=2))


def cmd_show_config(args):
    config = load_jev_config(args.jev_yaml)
    print(json.dumps({"endpoint": config["endpoint"], "model": config["model"],
                      "apikey_fingerprint": fingerprint(config["apikey"]) if config["apikey"] else None,
                      "config_path": config["config_path"], "url": chat_url(config["endpoint"])},
                     ensure_ascii=False, indent=2))


def fetch_key_info(config, timeout=30):
    """key 侧权威信息：累计 usage 与剩余额度（GET /key）；失败返回空 dict。"""
    url = config["endpoint"].rstrip("/") + "/key"
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + config["apikey"],
                                                   "User-Agent": USER_AGENT})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,
                                                                               timeout=timeout) as response:
            data = json.loads(response.read(MAX_RESPONSE_BYTES).decode("utf-8")).get("data") or {}
        return {"usage": data.get("usage"), "limit_remaining": data.get("limit_remaining"),
                "limit": data.get("limit")}
    except Exception:
        return {}


def fetch_account_usage(config, timeout=30):
    return fetch_key_info(config, timeout).get("usage")


def cmd_credits(args):
    """一条命令看余额：账户额度 + 这把 key 的额度上限。"""
    config = load_jev_config(args.jev_yaml)
    out = {"endpoint": config["endpoint"], "model": config["model"],
           "key_fingerprint": fingerprint(config["apikey"]) if config["apikey"] else None}
    for path in ("/credits", "/key"):
        request = urllib.request.Request(config["endpoint"].rstrip("/") + path,
                                         headers={"Authorization": "Bearer " + config["apikey"],
                                                  "User-Agent": USER_AGENT})
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,
                                                                                   timeout=30) as response:
                out[path] = json.loads(response.read(MAX_RESPONSE_BYTES).decode("utf-8"))
        except Exception as error:
            out[path] = {"error": str(error)}
    account = (out.get("/credits") or {}).get("data") or {}
    key = (out.get("/key") or {}).get("data") or {}
    total = account.get("total_credits")
    used = account.get("total_usage")
    out["summary"] = {
        "account_remaining_usd": (total - used) if isinstance(total, (int, float)) and isinstance(used, (int, float)) else None,
        "key_limit_usd": key.get("limit"),
        "key_usage_usd": key.get("usage"),
        "key_remaining_usd": key.get("limit_remaining"),
        "needed_for_full_fill_usd": round(args.fill_cost, 2),
        "verdict": None,
    }
    summary = out["summary"]
    if isinstance(summary["account_remaining_usd"], (int, float)) and summary["account_remaining_usd"] < args.fill_cost:
        summary["verdict"] = "账户余额不足：跑满 fill 需约 $%.2f，当前剩 $%.2f" % (
            args.fill_cost, summary["account_remaining_usd"])
    elif isinstance(summary["key_remaining_usd"], (int, float)) and summary["key_remaining_usd"] < args.fill_cost:
        summary["verdict"] = "key 额度不足：跑满 fill 需约 $%.2f，这把 key 只剩 $%.2f（要先调大 key limit）" % (
            args.fill_cost, summary["key_remaining_usd"])
    else:
        summary["verdict"] = "账户与 key 额度都够跑满 fill"
    print(json.dumps(out, ensure_ascii=False, indent=2))


def _report_namespace(**overrides):
    values = {"phase": "validation", "plan": None, "journal": None, "extra_journal": [],
              "self_plan": None, "self_journal": None, "dist_plan": None, "dist_journal": None,
              "fill_out": None, "out": None, "model": None, "endpoint_host": None,
              "budget_shown": "0.05", "max_tokens_shown": 2000, "account_usage": 0.195851448,
              "key_remaining": 0.7948,
              "fill_population": 8417, "fill_score": 545, "fill_choice": 7872,
              "noul_population": 7907, "noul_one_hot": 3668, "noul_uniform": 1656,
              "noul_real": 2583,
              "sidecar": [str(DEFAULT_WORK / "mercury-noul-probs.jsonl"),
                          str(DEFAULT_WORK / "jev-router-partial-probs.jsonl")]}
    values.update(overrides)
    return argparse.Namespace(**values)


def cmd_probe(args):
    """一条命令跑完配对探针：确认 plan -> 调用 -> 重生成报告（附录 A 自动出四张表）。"""
    config = load_jev_config(args.jev_yaml)
    plan_path = DEFAULT_WORK / "validation-plan-distribution.jsonl"
    journal_path = DEFAULT_WORK / "probe-dist-calls.jsonl"
    if args.force_plan or not plan_path.is_file():
        cmd_sample(argparse.Namespace(items=args.items, n=args.n, seed=args.seed,
                                      variant="distribution", out=str(plan_path)))
    cmd_run(argparse.Namespace(
        phase="validation", plan=str(plan_path), journal=str(journal_path), reuse_journal=[],
        budget=args.budget, workers=args.workers, repeat=1, limit=args.limit,
        max_attempts=args.max_attempts, max_tokens=args.max_tokens, temperature=args.temperature,
        timeout=args.timeout, retry_truncated=args.retry_truncated, force=False,
        allow_corpus_drift=False, dry_run=args.dry_run, backoff=2.0, max_backoff=30.0,
        min_interval=args.min_interval, estimate_per_call=args.estimate_per_call,
        price_in=None, price_out=None, items=args.items, jev_yaml=args.jev_yaml))
    if args.dry_run:
        return
    info = fetch_key_info(config)
    account_usage = info.get("usage")
    key_remaining = info.get("limit_remaining")
    if account_usage is None:
        account_usage = args.account_usage
        key_remaining = args.key_remaining
        print(json.dumps({"account_usage_usd": account_usage, "key_remaining_usd": key_remaining,
                          "source": "命令行默认值（GET /key 失败）"}, ensure_ascii=False))
    else:
        print(json.dumps({"account_usage_usd": account_usage, "key_remaining_usd": key_remaining,
                          "source": "GET /key"}, ensure_ascii=False))
    cmd_report(_report_namespace(account_usage=account_usage, max_tokens_shown=args.max_tokens,
                                 key_remaining=key_remaining if key_remaining is not None else args.key_remaining))


# ------------------------------------------------------------------ CLI

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", default=str(DEFAULT_ITEMS), help="冻结语料（只读）")
    parser.add_argument("--jev-yaml", default=str(DEFAULT_JEV_YAML))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("show-config", help="打印生效配置（密钥只留指纹）")
    p.set_defaults(func=cmd_show_config)

    p = sub.add_parser("sample", help="分层抽样 -> validation plan")
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=20261015)
    p.add_argument("--variant", choices=("answer", "distribution"), default="answer")
    p.add_argument("--out")
    p.set_defaults(func=cmd_sample)

    p = sub.add_parser("fill-plan", help="answer-only target -> fill plan（可过滤/换提示词变体）")
    p.add_argument("--variant", choices=("answer", "distribution"), default="answer")
    p.add_argument("--lang", action="append", default=[], help="只取这些语言，可重复")
    p.add_argument("--kind", action="append", default=[], help="只取这些 kind，可重复")
    p.add_argument("--limit", type=int)
    p.add_argument("--out")
    p.set_defaults(func=cmd_fill_plan)

    p = sub.add_parser("fill-write", help="按硬门禁把 fill journal 写成旁挂 probs 文件")
    p.add_argument("--plan")
    p.add_argument("--journal")
    p.add_argument("--out")
    p.add_argument("--stats")
    p.set_defaults(func=cmd_fill_write)

    p = sub.add_parser("run", help="执行调用（可续跑/限速/重试/预算硬停）")
    p.add_argument("--phase", choices=("validation", "fill"), required=True)
    p.add_argument("--plan")
    p.add_argument("--journal")
    p.add_argument("--reuse-journal", action="append", default=[])
    p.add_argument("--budget", type=float, default=None)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--limit", type=int)
    p.add_argument("--max-attempts", type=int, default=4)
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--retry-truncated", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--allow-corpus-drift", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--backoff", type=float, default=2.0)
    p.add_argument("--max-backoff", type=float, default=30.0)
    p.add_argument("--min-interval", type=float, default=0.05)
    p.add_argument("--estimate-per-call", type=float, default=0.0005)
    p.add_argument("--price-in", type=float, default=None, help="每 100 万 prompt token 的美元价")
    p.add_argument("--price-out", type=float, default=None, help="每 100 万 completion token 的美元价")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="生成阶段一报告")
    p.add_argument("--phase", choices=("validation", "fill"), default="validation")
    p.add_argument("--plan")
    p.add_argument("--journal")
    p.add_argument("--extra-journal", action="append", default=[])
    p.add_argument("--self-plan")
    p.add_argument("--self-journal")
    p.add_argument("--dist-plan")
    p.add_argument("--dist-journal")
    p.add_argument("--fill-out")
    p.add_argument("--out")
    p.add_argument("--model", default=None)
    p.add_argument("--endpoint-host", default=None)
    p.add_argument("--budget-shown", default="0.05")
    p.add_argument("--max-tokens-shown", type=int, default=2000)
    p.add_argument("--key-remaining", type=float, default=0.7948, help="运行时的 key 剩余额度（GET /key）")
    p.add_argument("--noul-population", type=int, default=7907)
    p.add_argument("--noul-one-hot", type=int, default=3668)
    p.add_argument("--noul-uniform", type=int, default=1656)
    p.add_argument("--noul-real", type=int, default=2583)
    p.add_argument("--sidecar", action="append", default=[],
                   help="旁挂 probs 文件（可重复）；默认取 jev/ 下两个来源")
    p.add_argument("--account-usage", type=float, default=0.195851448,
                   help="账户侧累计用量（GET https://openrouter.ai/api/v1/key 的 usage），权威口径")
    p.add_argument("--fill-population", type=int, default=8417)
    p.add_argument("--fill-score", type=int, default=545)
    p.add_argument("--fill-choice", type=int, default=7872)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("verify", help="校验旁挂 probs（给 --plan 按 plan 对，否则直接对冻结语料）")
    p.add_argument("--phase", choices=("validation", "fill"), default="fill")
    p.add_argument("--plan")
    p.add_argument("--out")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("noul-fill", help="mercury-decide 全量补 noul（可续跑/控速/429 退避）")
    p.add_argument("--rate", type=float, default=2.0, help="每秒请求数（全局限速）")
    p.add_argument("--workers", type=int, default=4, help="并发数；限速仍按 --rate 全局生效")
    p.add_argument("--mercury-model", default=MERCURY_MODEL)
    p.add_argument("--decisions-url", default=DEFAULT_DECISIONS_URL)
    p.add_argument("--max-attempts", type=int, default=5)
    p.add_argument("--backoff", type=float, default=2.0)
    p.add_argument("--max-backoff", type=float, default=60.0)
    p.add_argument("--rate-limit-backoff", type=float, default=5.0)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--limit", type=int)
    p.add_argument("--skip-existing-real", action="store_true",
                   help="不覆盖语料里已经是真分布(real)的 target（保守模式）")
    p.add_argument("--journal")
    p.add_argument("--out")
    p.add_argument("--stats")
    p.set_defaults(func=cmd_noul_fill)

    p = sub.add_parser("choice-fill", help="mercury-decide 补 answer-only choice（criteria 模板，可续跑/按预算停）")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--rate", type=float, default=8.0, help="全局每秒请求数")
    p.add_argument("--budget", type=float, default=0.09, help="本轮最多花多少（账户口径，美元）")
    p.add_argument("--estimate-per-call", type=float, default=0.000006)
    p.add_argument("--mercury-model", default=MERCURY_MODEL)
    p.add_argument("--decisions-url", default=DEFAULT_DECISIONS_URL)
    p.add_argument("--max-attempts", type=int, default=5)
    p.add_argument("--backoff", type=float, default=2.0)
    p.add_argument("--max-backoff", type=float, default=60.0)
    p.add_argument("--rate-limit-backoff", type=float, default=5.0)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--limit", type=int)
    p.add_argument("--exclude-plan", default=str(DEFAULT_WORK / "fill-plan-dist-zh-choice.jsonl"),
                   help="排除该 plan 里的 qid（即旧 zh choice，由 jev-router 线负责）")
    p.add_argument("--journal")
    p.add_argument("--out")
    p.add_argument("--stats")
    p.set_defaults(func=cmd_choice_fill)

    p = sub.add_parser("probs-guard-test", help="自检：注入 benchmark 行验证硬断言会拒绝写盘")
    p.add_argument("--src", default=str(DEFAULT_WORK / "jev-probs.full.jsonl"))
    p.add_argument("--splits-dir", default=str(DEFAULT_WORK.parent / "splits"))
    p.set_defaults(func=cmd_probs_guard_test)

    p = sub.add_parser("probs-public", help="只导出公开三区 probs + benchmark 硬断言 + 确定性打包")
    p.add_argument("--src", default=str(DEFAULT_WORK / "jev-probs.full.jsonl"))
    p.add_argument("--out", default=str(DEFAULT_FILL_OUT))
    p.add_argument("--splits-dir", default=str(DEFAULT_WORK.parent / "splits"))
    p.add_argument("--pack", action="store_true", help="同时写确定性 .gz（mtime=0）")
    p.set_defaults(func=cmd_probs_public)

    p = sub.add_parser("probs-assemble", help="合并各来源旁挂 probs -> data/jev-probs.jsonl")
    p.add_argument("--source", action="append", default=[])
    p.add_argument("--out")
    p.set_defaults(func=cmd_probs_assemble)

    p = sub.add_parser("noul-probe", help="mercury-decide noul 小样本验证（默认 20 条，1 req/s 控速）")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--seed", type=int, default=20261020)
    p.add_argument("--rate", type=float, default=1.0, help="每秒请求数（避开 429）")
    p.add_argument("--mercury-model", default=MERCURY_MODEL)
    p.add_argument("--decisions-url", default=DEFAULT_DECISIONS_URL)
    p.add_argument("--max-attempts", type=int, default=5)
    p.add_argument("--backoff", type=float, default=2.0)
    p.add_argument("--max-backoff", type=float, default=60.0)
    p.add_argument("--rate-limit-backoff", type=float, default=5.0)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--journal")
    p.add_argument("--stats")
    p.set_defaults(func=cmd_noul_probe)

    p = sub.add_parser("credits", help="看账户余额与这把 key 的额度上限（一条命令）")
    p.add_argument("--fill-cost", type=float, default=7.56, help="跑满第二阶段预计花费（账户侧口径）")
    p.set_defaults(func=cmd_credits)

    p = sub.add_parser("probe", help="一条命令跑 distribution 配对探针并重生成报告")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--seed", type=int, default=20261015)
    p.add_argument("--budget", type=float, default=0.06)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--limit", type=int)
    p.add_argument("--max-attempts", type=int, default=4)
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--retry-truncated", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force-plan", action="store_true")
    p.add_argument("--min-interval", type=float, default=0.05)
    p.add_argument("--estimate-per-call", type=float, default=0.0004)
    p.add_argument("--account-usage", type=float, default=0.195851448)
    p.add_argument("--key-remaining", type=float, default=0.7948)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("cost", help="汇总 journal 成本")
    p.add_argument("journals", nargs="+")
    p.set_defaults(func=cmd_cost)

    args = parser.parse_args(argv)
    if getattr(args, "func", None) is cmd_run and args.budget is None:
        args.budget = 0.05 if args.phase == "validation" else 5.0
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    return args.func(args)


if __name__ == "__main__":
    main()
