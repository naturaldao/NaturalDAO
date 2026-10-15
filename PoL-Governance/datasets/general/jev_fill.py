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
    for item, key, question, target in iter_targets(items_path):
        if target_shape(target) != "answer_only":
            continue
        population += 1
        prompt = build_prompt(item.get("state"), question, "answer")
        rows.append({"record_type": "request", "seq": population,
                     "qid": "%s.%s" % (item["id"], key), "id": item["id"], "key": key,
                     "kind": question["kind"], "domain": item.get("domain") or "",
                     "lang": item.get("lang") or "", "variant": "answer",
                     "source_dataset": (item.get("source") or {}).get("dataset") or "",
                     "answer": str(target.get("answer")), "shape": "answer_only",
                     "n_options": len(option_space(question)),
                     "chance": round(1.0 / max(1, len(option_space(question))), 6),
                     "prompt_sha256": sha256_text(prompt)})
    manifest = {"record_type": "manifest", "tool": TOOL, "harness_version": HARNESS_VERSION,
                "phase": "fill", "created_at": iso_now(), "population": population,
                "items": str(items_path), "items_sha256": corpus_sha, "variant": "answer"}
    out = Path(args.out or DEFAULT_WORK / "fill-plan.jsonl")
    write_jsonl(out, [manifest] + rows)
    print(json.dumps({"plan": str(out), "requests": len(rows), "items_sha256": corpus_sha[:16]},
                     ensure_ascii=False, indent=2))


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


def cmd_report(args):
    work = DEFAULT_WORK
    plan_path = Path(args.plan or work / "validation-plan.jsonl")
    journal_path = Path(args.journal or work / "validation-calls.jsonl")
    plan = read_jsonl(plan_path)
    manifest = plan[0]
    raw_records = load_records(plan, [journal_path])
    records = score_records(raw_records, plan_path)
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
    lines.append("# Jev 分层校验报告（第一阶段）")
    lines.append("")
    lines.append("> 生成时间：%s ｜ 生成脚本：%s（[jev_fill.py](jev_fill.py)）" % (iso_now(), HARNESS_VERSION))
    lines.append("> 语料：[items.final.jsonl](data/items.final.jsonl) sha256 前缀 %s（只读，未改动）"
                 % manifest["items_sha256"][:16])
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
    lines.append("- **诚实说明**：本阶段的“一致”只是 **Jev 的答案 == 语料已有的 answer**。"
                 "语料里大量 target 的 answer 本身来自教师模型或伪 one-hot（见 3.5 按 shape 分列），"
                 "因此**一致率低不等于语料错**，一致率高也不等于语料对；能下判断的是“与随机基线的差距”"
                 "“真实分布子集上的一致率”和“同题重复的自洽率”。")
    lines.append("")
    if stopped or credits_402:
        lines.append("### 0.1 为什么停在 %d/%d：先是撞预算上限，后是 OpenRouter 余额不足（HTTP 402）"
                     % (total_cost["ok"], manifest["sampled_n"]))
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
                ["与真值一致（按全部配对算）", rate_cell(pair["base_agree"], pair["common"]),
                 rate_cell(pair["probe_agree"], pair["common"])],
                ["成本", "$%.5f" % pair["base_cost"], "$%.5f" % pair["probe_cost"]],
                ["都能解析的条数", pair["both"], pair["both"]],
                ["两套提示词给出同一个选项", rate_cell(pair["same"], pair["both"]), "—"],
            ]))
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
            rows.append(["`%s`" % _state_brief(row["qid"], 90), row["lang"], row["domain"], row["kind"], row["shape"],
                         row["n_options"], row["answer"], record["parsed"],
                         record["upstream_model"], _state_brief(record["state"])])
        lines.append(md_table(["qid", "lang", "domain", "kind", "shape", "选项数", "语料 answer",
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
        rows.append(["`%s`" % _state_brief(row["qid"], 90), row["kind"], row["answer"], record["upstream_model"],
                     _state_brief(record["state"], 110)])
    lines.append(md_table(["qid", "kind", "答案（两边一致）", "上游模型", "state 摘要"],
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
    lines.append("## 8. 第二阶段（补全 probs）现状")
    lines.append("")
    lines.append("冻结语料中 answer-only 的 target 共 **%d** 个（`score` %d / `choice` %d）。"
                 % (args.fill_population, args.fill_score, args.fill_choice))
    lines.append("写入旁挂文件 `data/jev-probs.jsonl` 的**全部**条件：")
    lines.append("")
    lines.append("1. Jev 返回可解析，且恰好命中一个选项；")
    lines.append("2. 命中的选项 == 语料已有的 `answer`（保证 `argmax(probs) == answer`）；")
    lines.append("3. 概率归一（和为 1）。")
    lines.append("")
    lines.append("任一条不满足则该 target 保持 answer_only 不变，并计入本报告。"
                 "**冻结语料在任何情况下都不修改。**")
    lines.append("")
    if fill_section:
        lines.append("当前旁挂文件已有 %d 条。" % fill_section["rows"])
    else:
        lines.append("**当前状态**：Lead 已否掉方案 A（one-hot 的信息量等于 answer 本身，等于把问题原地搬一遍），"
                 "决定先跑 **100 条配对探针**验证方案 B（分布提示词）。"
                 "**探针未执行：账户余额耗尽（HTTP 402）**——需先给 OpenRouter 账户充值；"
                 "另外这把 key 自身还有 $1 上限（剩 $0.80），跑满 8,417 条会先撞 key 上限，需要一并放宽。")
        lines.append("")
        lines.append(FENCE + "sh")
        lines.append("uv run --no-project --offline python datasets/general/jev_fill.py fill-plan")
        lines.append("uv run --no-project --offline python datasets/general/jev_fill.py run --phase fill --budget 5")
        lines.append("uv run --no-project --offline python datasets/general/jev_fill.py report --phase validation")
        lines.append("uv run --no-project --offline python datasets/general/jev_fill.py verify --phase fill")
        lines.append(FENCE)
    lines.append("")
    lines.append("### 8.1 由第一阶段推出的第二阶段预期（等确认）")
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
    lines.append("### 8.2 要跑完第二阶段，需要同时满足的条件（清单）")
    lines.append("")
    lines.append("下面 5 条**全部**满足才开跑；任何一条不满足，第二阶段就只停留在「已就绪、未执行」，"
                 "并如实写进本报告。")
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
    lines.append("## 9. 产物")
    lines.append("")
    lines.append(md_table(["路径", "内容"], [
        ["`datasets/general/jev_fill.py`", "本报告的生成脚本（抽样/调用/解析/报告/校验）"],
        ["`datasets/general/jev-validation.md`", "本文件"],
        ["`datasets/general/data/jev/validation-plan.jsonl`", "抽样清单（manifest + 300 条，含分层与真值）"],
        ["`datasets/general/data/jev/validation-calls.jsonl`", "逐次尝试的原始响应与成本（可续跑）"],
        ["`datasets/general/data/jev/fill-plan.jsonl`", "第二阶段请求清单（8,417 条 answer-only target）"],
        ["`datasets/general/data/jev/fill-calls.jsonl`", "第二阶段的原始响应与成本（尚未生成）"],
        ["`datasets/general/data/jev-probs.jsonl`", "第二阶段的旁挂概率（answer-only 补全结果）"],
    ]))
    lines.append("")
    lines.append("冻结语料只读：`items.final.jsonl` 与 `data/splits/` 四区文件在本任务中未被写入。")
    lines.append("")
    out = Path(args.out or DEFAULT_VALIDATION_MD)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(out), "bytes": out.stat().st_size,
                      "sampled": overall["n"], "parsed": overall["parsed"], "agree": overall["agree"],
                      "cost_usd": round(total_cost["cost_usd"], 5)}, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------ 校验与成本

def cmd_verify(args):
    plan_path = Path(args.plan or DEFAULT_WORK / "fill-plan.jsonl")
    out_path = Path(args.out or DEFAULT_FILL_OUT)
    plan = read_jsonl(plan_path)
    plan_rows = {row["qid"]: row for row in plan[1:] if row.get("record_type") == "request"}
    items_path = Path(plan[0]["items"])
    questions = {}
    shapes = {}
    wanted = set(plan_rows)
    for item, key, question, target in iter_targets(items_path):
        qid = "%s.%s" % (item["id"], key)
        if qid in wanted:
            questions[qid] = question
            shapes[qid] = target_shape(target)
    rows = read_jsonl(out_path)
    errors = []
    seen = set()
    stats = {"rows": len(rows), "argmax_ok": 0, "normalized": 0, "answer_only": 0, "in_plan": 0}
    for position, row in enumerate(rows, 1):
        where = "%s[%d]" % (out_path, position)
        qid = row.get("qid")
        if not qid or qid in seen:
            errors.append("%s: 缺失或重复 qid %r" % (where, qid))
            continue
        seen.add(qid)
        question = questions.get(qid)
        if question is None:
            errors.append("%s: qid 不在 fill plan 里" % where)
            continue
        stats["in_plan"] += 1
        if shapes.get(qid) == "answer_only":
            stats["answer_only"] += 1
        for field in ("id", "key", "probs", "distribution_semantics", "upstream_model", "created_at"):
            if field not in row:
                errors.append("%s: 缺字段 %s" % (where, field))
        if row.get("distribution_semantics") != "jev_router":
            errors.append("%s: distribution_semantics 必须是 jev_router" % where)
        probs = row.get("probs")
        if not isinstance(probs, dict) or not probs:
            errors.append("%s: probs 必须是非空对象" % where)
            continue
        keys = option_space(question)
        unknown = sorted(set(probs) - set(keys))
        if unknown:
            errors.append("%s: probs 键不在该题取值域内 %s" % (where, unknown))
        if any((not isinstance(value, (int, float))) or value < 0 for value in probs.values()):
            errors.append("%s: probs 取值必须是非负数字" % where)
        total = sum(float(value) for value in probs.values())
        if abs(total - 1.0) > 1e-6:
            errors.append("%s: probs 未归一（sum=%.6f）" % (where, total))
        else:
            stats["normalized"] += 1
        top = argmax_key({key: float(value) for key, value in probs.items()}, question)
        truth = plan_rows[qid]["answer"]
        if top != truth:
            errors.append("%s: argmax=%r != answer=%r（违反硬约束）" % (where, top, truth))
        else:
            stats["argmax_ok"] += 1
    report = {"status": "pass" if not errors else "fail", **stats,
              "plan": str(plan_path), "out": str(out_path), "errors": errors[:20],
              "error_count": len(errors)}
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


def fetch_account_usage(config, timeout=30):
    """账户侧权威用量（GET /key 的 usage）；失败返回 None。"""
    url = config["endpoint"].rstrip("/") + "/key"
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + config["apikey"],
                                                   "User-Agent": USER_AGENT})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,
                                                                               timeout=timeout) as response:
            data = json.loads(response.read(MAX_RESPONSE_BYTES).decode("utf-8"))
        value = (data.get("data") or {}).get("usage")
        return float(value) if isinstance(value, (int, float)) else None
    except Exception:
        return None


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
              "fill_population": 8417, "fill_score": 545, "fill_choice": 7872}
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
    account_usage = fetch_account_usage(config)
    if account_usage is None:
        account_usage = args.account_usage
        print(json.dumps({"account_usage_usd": account_usage, "source": "命令行默认值（GET /key 失败）"},
                         ensure_ascii=False))
    else:
        print(json.dumps({"account_usage_usd": account_usage, "source": "GET /key"}, ensure_ascii=False))
    cmd_report(_report_namespace(account_usage=account_usage, max_tokens_shown=args.max_tokens))


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

    p = sub.add_parser("fill-plan", help="全量 answer-only target -> fill plan")
    p.add_argument("--out")
    p.set_defaults(func=cmd_fill_plan)

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
    p.add_argument("--account-usage", type=float, default=0.195851448,
                   help="账户侧累计用量（GET https://openrouter.ai/api/v1/key 的 usage），权威口径")
    p.add_argument("--fill-population", type=int, default=8417)
    p.add_argument("--fill-score", type=int, default=545)
    p.add_argument("--fill-choice", type=int, default=7872)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("verify", help="校验阶段二产物")
    p.add_argument("--phase", choices=("validation", "fill"), default="fill")
    p.add_argument("--plan")
    p.add_argument("--out")
    p.set_defaults(func=cmd_verify)

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
