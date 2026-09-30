#!/usr/bin/env python
"""通用问题集批量作答 harness（decision-base/ask.py, ask-v0.1）。

目标：外部答案源（官方 Jev / OpenAI 兼容端点 / 离线 fixture）在上万条问题上
**一条命令跑完、断了能续、失败能重跑、产物符合契约 2.2 节**。
契约：datasets/decision-base/README.md 第 2.2 节（字段名固定，不新增、不改名）。

只依赖标准库；默认离线（不加 --live 只写请求计划，不联网）。
密钥只从环境变量或 --key-file 读取，绝不写进任何产物；日志里只有 sha256 前 8 位指纹。

子命令
    plan    离线把 items.jsonl 展平成请求清单（qid/state/question/options），可直接交给 Jev
    run     批量作答：默认只写请求计划；--live 才联网；--backend fixture 离线确定性合成
    report  读 calls.jsonl（可选 answers/items）输出用量、成本、失败分类
    verify  按契约 2.2 核对 answers 文件，并给出覆盖缺口

常用命令
    # 1) 离线：生成请求清单（不联网、不需要密钥）
    uv run --no-project --offline python datasets/decision-base/ask.py plan \
        --items datasets/decision-base/data/items.jsonl --out <仓库外>/requests.jsonl

    # 2) 离线预演：只写请求计划，核对 URL/包体形状
    uv run --no-project --offline python datasets/decision-base/ask.py run \
        --items datasets/decision-base/data/items.jsonl --out <仓库外>/answers --backend jev \
        --endpoint https://<官方地址>/... --api-version <版本>

    # 3) 真跑（需要密钥；缺 endpoint/版本/密钥/--integration-confirmed 任一项退出码 2）
    $env:JEV_API_KEY = "<密钥>"
    uv run --no-project --offline python datasets/decision-base/ask.py run \
        --items datasets/decision-base/data/items.jsonl --out <仓库外>/answers --backend jev --live \
        --endpoint https://<官方地址>/... --api-version <版本> --integration-confirmed \
        --workers 8

    # 4) 续跑：默认跳过已 ok 的 qid；失败项用 --retry-failed 重跑
    ... run --live ... --retry-failed

    # 5) 核对与统计
    uv run --no-project --offline python datasets/decision-base/ask.py report \
        --calls <仓库外>/answers/calls.jev-<版本>.jsonl --answers <仓库外>/answers/answers.jev-<版本>.jsonl
    uv run --no-project --offline python datasets/decision-base/ask.py verify \
        --items datasets/decision-base/data/items.jsonl --answers <仓库外>/answers/answers.jev-<版本>.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

# 同目录的 taxonomy.py（db-schema）是问题键、题型、选项与量程的**唯一真源**：
# 本 harness 不另立一套题型校验，避免与转换器/覆盖报告漂移（2026-09-30 真实 items.jsonl 踩过）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # pragma: no cover - 仓库完整性兜底
    import taxonomy  # noqa: E402
    TAXONOMY_ERROR = None
except ImportError as error:  # pragma: no cover
    taxonomy = None
    TAXONOMY_ERROR = error

TOOL = "decision-base-ask"
HARNESS_VERSION = "ask-v0.1"
ANSWER_CONTRACT = "datasets/decision-base/README.md 2.2"
CHAT_TEMPLATE_VERSION = "ask-chat-v0.1"

KINDS = ("noul", "choice", "score")
NOUL_KEYS = ("yes", "no")
EXECUTION_STATUSES = ("ok", "timeout", "error", "invalid")

ANSWER_REQUIRED = ("qid", "id", "key", "kind", "source", "source_version", "answer",
                   "execution_status", "latency_ms", "created_at")
ANSWER_OPTIONAL = ("probs",)
SOURCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

RETRY_STATUS = (408, 409, 425, 429, 500, 502, 503, 504)
MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_USER_AGENT = "PoL-decision-base/0.1 (+https://github.com/naturaldao/NaturalDAO)"
DEFAULT_KEY_ENV = {"jev": "JEV_API_KEY", "openai-compatible": "ASK_API_KEY"}
FIXTURE_SOURCE = "fixture"
FIXTURE_VERSION = "fixture-v0.1"
PROB_TOLERANCE = 1e-3


class ConfigError(ValueError):
    """配置/用法错误：退出码 2，绝不静默降级。"""


class CallFailure(Exception):
    """kind in timeout / error / invalid，与 execution_status 同名。"""

    def __init__(self, kind, message, status_code=None, attempts=1, retryable=None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.attempts = attempts
        self.retryable = retryable


# --------------------------------------------------------------------- helpers

def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fingerprint(secret):
    """不可逆短指纹；密钥本体永不落盘。"""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]


def csv_list(value):
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _reject_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def _unique_keys(pairs):
    row = {}
    for key, value in pairs:
        require(key not in row, f"duplicate JSON key: {key}")
        row[key] = value
    return row


def read_jsonl(path):
    path = Path(path)
    require(path.is_file(), f"missing file: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
        require(isinstance(row, dict), f"{path}:{line_number}: each line must be an object")
        rows.append(row)
    return rows


def jsonl_text(rows):
    return "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)


def write_jsonl_atomic(path, rows):
    """原子替换（本 harness 自己的产物：answers / journal / requests）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(jsonl_text(rows))
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return path


class JsonlAppender:
    """追加写 JSONL：逐行 flush，fsync 至多每 fsync_interval 秒一次（进程被杀不丢已完成行）。"""

    def __init__(self, path, fsync_interval=1.0):
        self.path = Path(path)
        self.fsync_interval = fsync_interval
        self._handle = None
        self._last_fsync = 0.0
        self.lock = threading.Lock()

    def append(self, row):
        with self.lock:
            if self._handle is None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._handle = self.path.open("a", encoding="utf-8", newline="\n")
            self._handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            self._handle.flush()
            now = time.monotonic()
            if now - self._last_fsync >= self.fsync_interval:
                os.fsync(self._handle.fileno())
                self._last_fsync = now

    def close(self):
        with self.lock:
            if self._handle is not None:
                try:
                    os.fsync(self._handle.fileno())
                finally:
                    self._handle.close()
                    self._handle = None


class CallLog:
    """每次尝试/每个 qid 一条 jsonl；密钥只留指纹。"""

    def __init__(self, path=None, run_id=None):
        self.path = Path(path) if path else None
        self.run_id = run_id or hashlib.sha256(
            f"{os.getpid()}|{time.time()}|{id(self)}".encode()).hexdigest()[:12]
        self.rows = []
        self.lock = threading.Lock()
        self._appender = JsonlAppender(self.path) if self.path else None

    def record(self, row):
        require(isinstance(row, dict), "log row must be an object")
        row = {"ts": iso_now(), "run_id": self.run_id, **row}
        with self.lock:
            self.rows.append(row)
            if self._appender is not None:
                self._appender.append(row)
        return row

    def close(self):
        if self._appender is not None:
            self._appender.close()

    def summary(self):
        return aggregate_calls(self.rows)


# --------------------------------------------------------------------- secrets

_REF_LINE_RE = re.compile(r"^[ \t]+([A-Za-z0-9_.\-]+):[ \t]*(\S.*?)[ \t]*$")


def load_secret(env_names, key_file=None, ref=None, environ=None):
    """返回 (secret, origin)；env 优先，其次 --key-file（DSH YAML refs 或单值文件）。"""
    environ = os.environ if environ is None else environ
    for name in env_names:
        value = environ.get(name, "")
        if value.strip():
            return value.strip(), f"env:{name}"
    if key_file:
        path = Path(key_file)
        require(path.is_file(), f"key file not found: {path}")
        wanted = ref or (env_names[0] if env_names else None)
        refs = {}
        in_refs = False
        plain_candidates = []
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            if re.match(r"^[A-Za-z_0-9]+:[ \t]*$", raw_line):
                in_refs = raw_line.split(":", 1)[0].strip() == "refs"
                continue
            match = _REF_LINE_RE.match(raw_line)
            if match:
                if in_refs:
                    refs[match.group(1)] = match.group(2).strip().strip('"').strip("'")
                continue
            stripped = raw_line.strip()
            if stripped and not stripped.startswith("#") and ":" not in stripped:
                plain_candidates.append(stripped)
        if wanted and wanted in refs and refs[wanted]:
            return refs[wanted], f"file:{path}:{wanted}"
        if len(plain_candidates) == 1:
            return plain_candidates[0], f"file:{path}"
        names = ", ".join(env_names) if env_names else "(none)"
        raise ConfigError(f"no secret for {wanted!r} in {path}; looked for env [{names}] "
                          f"and refs keys {sorted(refs)}")
    raise ConfigError(f"no secret found; set environment variable(s) {list(env_names)}"
                      + (" or pass --key-file" if key_file is None else ""))


def validate_endpoint(url):
    parsed = urlsplit(url)
    require(parsed.scheme in ("http", "https"), "endpoint must be http(s)")
    require(not parsed.username and not parsed.password, "endpoint must not embed credentials")
    require(not parsed.query and not parsed.fragment, "endpoint must not carry query/fragment")
    if parsed.scheme == "http":
        require(parsed.hostname in ("127.0.0.1", "::1", "localhost"),
                "plain HTTP is allowed only for loopback endpoints")
    _ = parsed.port
    return url


# --------------------------------------------------------------------- items → requests

def taxonomy_module(where):
    if taxonomy is None:  # pragma: no cover - 仓库完整性兜底
        raise ConfigError(f"{where}: 同目录缺 taxonomy.py（问题键/题型的唯一真源）：{TAXONOMY_ERROR}")
    return taxonomy


def validate_question(question, where):
    """题型校验的唯一真源是 taxonomy.validate_question（契约 2.1 的实现方，不另立一套）。"""
    errors = taxonomy_module(where).validate_question(question)
    require(not errors, f"{where}: " + "；".join(errors))
    return question


def validate_item(item, where, strict_schema=True):
    """strict_schema=True 时走 taxonomy.item_errors（README 2.1 全字段）。

    这是 plan/run 的默认：在花钱调用之前就拦住形状不对的条目。
    非严格模式只校验本 harness 真正消费的字段（id/state/questions），供 report/verify 分析既有产物。
    """
    require(isinstance(item, dict), f"{where}: item must be an object")
    if strict_schema:
        errors = taxonomy_module(where).item_errors(item)
        if errors:
            shown = "；".join(errors[:8]) + ("…" if len(errors) > 8 else "")
            raise ValueError(f"{where}: 条目不符合 README 2.1（{len(errors)} 处）：{shown}"
                             "（确需跳过用 --skip-item-schema，但请先修数据）")
        return item
    require(text(item.get("id")), f"{where}: item.id must be a non-empty string")
    require(text(item.get("state")), f"{where}: item.state must be a non-empty string")
    questions = item.get("questions")
    require(isinstance(questions, list) and questions, f"{where}: item.questions must be non-empty")
    return item


def request_from_question(item, question):
    """按 taxonomy 已校验过的形状展平成一条请求（scale.labels 是 min..max 的字符串数组）。"""
    request = {"qid": f"{item['id']}.{question['key']}", "id": item["id"], "key": question["key"],
               "kind": question["kind"], "domain": item.get("domain") or "",
               "lang": item.get("lang") or "", "state": item["state"],
               "question": question["prompt"]}
    if question["kind"] == "score":
        scale = question["scale"]
        request["scale"] = {"min": int(scale["min"]), "max": int(scale["max"]),
                            "labels": [str(label) for label in scale["labels"]]}
    else:
        request["options"] = [{"key": str(option["key"]), "label": str(option["label"])}
                              for option in question["options"]]
    return request


def load_requests(items_path, keys=None, domains=None, limit=None, strict_items=True):
    """读 items.jsonl，展平成请求列表；qid = <item id>.<question key>（契约 2.1/2.2）。"""
    rows = read_jsonl(items_path)
    require(bool(rows), f"{items_path}: no items")
    requests = []
    seen = set()
    for position, item in enumerate(rows, 1):
        where = f"{items_path}[{position}]"
        validate_item(item, where, strict_schema=strict_items)
        questions = item.get("questions")
        require(isinstance(questions, list) and questions, f"{where}: item.questions must be non-empty")
        for question_position, question in enumerate(questions, 1):
            qwhere = f"{where}.questions[{question_position}]"
            validate_question(question, qwhere)
            request = request_from_question(item, question)
            require(request["qid"] not in seen, f"{where}: duplicate qid {request['qid']}")
            seen.add(request["qid"])
            requests.append(request)
    selected = requests
    if keys:
        wanted = set(keys)
        selected = [row for row in selected if row["key"] in wanted]
        require(bool(selected), f"no question matches --keys {sorted(wanted)}")
    if domains:
        wanted = set(domains)
        selected = [row for row in selected if row["domain"] in wanted]
        require(bool(selected), f"no question matches --domains {sorted(wanted)}")
    if limit is not None:
        require(integer(limit) and limit > 0, "--limit must be a positive integer")
        selected = selected[:limit]
    return requests, selected


def plan_row(request):
    row = {"qid": request["qid"], "id": request["id"], "key": request["key"], "kind": request["kind"],
           "domain": request["domain"], "lang": request["lang"], "state": request["state"],
           "question": request["question"]}
    if request["kind"] == "score":
        row["scale"] = request["scale"]
    else:
        row["options"] = request["options"]
    return row


# --------------------------------------------------------------------- answer contract 2.2

def expected_prob_keys(question):
    """问题的完整取值域：score 是 min..max 的整数分级（字符串键，与 taxonomy 一致），其余是选项 key。"""
    if question["kind"] == "score":
        scale = question["scale"]
        return [str(level) for level in range(int(scale["min"]), int(scale["max"]) + 1)]
    return [option["key"] for option in question["options"]]


def normalize_probs(raw, keys=None):
    """归一到 1；键必须落在问题的取值域内（允许只给部分取值，与 taxonomy._prob_errors 同口径）。"""
    require(isinstance(raw, dict) and raw, "probs must be a non-empty object")
    require(all(text(key) for key in raw), "probs keys must be non-empty strings")
    if keys is not None:
        unknown = sorted(set(raw) - set(keys))
        require(not unknown, f"probs keys {unknown} not in {sorted(keys)}")
    values = {}
    for key, value in raw.items():
        require(number(value) and value >= 0, f"probs[{key}] must be a finite number >= 0")
        values[key] = float(value)
    total = sum(values.values())
    require(total > 0, "probs must have a positive sum")
    return {key: value / total for key, value in values.items()}


def validate_answer_row(row, where="answer", question=None, allow_unknown_fields=True):
    require(isinstance(row, dict), f"{where}: must be an object")
    missing = [key for key in ANSWER_REQUIRED if key not in row]
    require(not missing, f"{where}: missing field(s) {missing}")
    if not allow_unknown_fields:
        unknown = sorted(set(row) - set(ANSWER_REQUIRED) - set(ANSWER_OPTIONAL))
        require(not unknown, f"{where}: unknown field(s) {unknown}")
    require(text(row["qid"]), f"{where}: qid must be a non-empty string")
    require(text(row["id"]), f"{where}: id must be a non-empty string")
    require(text(row["key"]), f"{where}: key must be a non-empty string")
    require(row["kind"] in KINDS, f"{where}: kind must be one of {list(KINDS)}")
    require(text(row["source"]) and SOURCE_RE.match(row["source"]),
            f"{where}: source must match {SOURCE_RE.pattern}")
    require(text(row["source_version"]), f"{where}: source_version must be a non-empty string")
    require(row["execution_status"] in EXECUTION_STATUSES,
            f"{where}: execution_status must be one of {list(EXECUTION_STATUSES)}")
    require(number(row["latency_ms"]) and row["latency_ms"] >= 0,
            f"{where}: latency_ms must be a finite number >= 0")
    require(text(row["created_at"]), f"{where}: created_at must be a non-empty string")
    if row["execution_status"] == "ok":
        answer = row["answer"]
        require(number(answer) or (isinstance(answer, str) and answer.strip()),
                f"{where}: answer must be a non-empty string or number when execution_status=ok")
    else:
        require(row["answer"] is None,
                f"{where}: answer must be null when execution_status={row['execution_status']}")
        require("probs" not in row,
                f"{where}: probs must be omitted when execution_status={row['execution_status']}")
    if question is not None:
        require(row["qid"] == question["qid"], f"{where}: qid != {question['qid']}")
        require(row["id"] == question["id"], f"{where}: id != {question['id']}")
        require(row["key"] == question["key"], f"{where}: key != {question['key']}")
        require(row["kind"] == question["kind"], f"{where}: kind != {question['kind']}")
    if "probs" in row:
        keys = expected_prob_keys(question) if question is not None else None
        probs = normalize_probs(row["probs"], keys=keys)
        if abs(sum(probs.values()) - 1) > PROB_TOLERANCE:
            raise ValueError(f"{where}: probs must be normalized")
    if question is not None and row["execution_status"] == "ok":
        answer = row["answer"]
        if question["kind"] == "score":
            require(number(answer) and question["scale"]["min"] <= answer <= question["scale"]["max"],
                    f"{where}: score answer must be a number in "
                    f"[{question['scale']['min']}, {question['scale']['max']}]")
        else:
            require(answer in [option["key"] for option in question["options"]],
                    f"{where}: answer {answer!r} is not one of "
                    f"{[option['key'] for option in question['options']]}")
    return row


def coerce_answer(value, question):
    """把答案源的原始取值收敛到问题取值域；不能收敛就返回 (None, 原因)。"""
    if question["kind"] == "score":
        scale = question["scale"]
        candidate = None
        if number(value):
            candidate = float(value)
        elif isinstance(value, str) and value.strip():
            try:
                candidate = float(value.strip())
            except ValueError:
                candidate = None
        if candidate is None:
            return None, f"score answer {value!r} is not numeric"
        if not (scale["min"] <= candidate <= scale["max"]):
            return None, f"score answer {candidate} outside [{scale['min']}, {scale['max']}]"
        if abs(candidate - round(candidate)) > 1e-9:
            return None, f"score answer {candidate} is not an integer level"
        return int(round(candidate)), None
    if not isinstance(value, str) or not value.strip():
        return None, f"answer {value!r} must be a non-empty string for kind={question['kind']}"
    cleaned = value.strip()
    keys = [option["key"] for option in question["options"]]
    if cleaned in keys:
        return cleaned, None
    labels = {}
    collisions = set()
    for option in question["options"]:
        label = option["label"].strip()
        if label in labels:
            collisions.add(label)
        labels[label] = option["key"]
    if cleaned in labels and cleaned not in collisions:
        return labels[cleaned], f"answer_from_label: {cleaned!r}"
    folded = {}
    for key in keys:
        folded.setdefault(key.lower(), []).append(key)
    match = folded.get(cleaned.lower(), [])
    if len(match) == 1:
        return match[0], f"answer_case_folded: {cleaned!r}"
    return None, f"answer {cleaned!r} outside options {keys}"


def argmax_key(probs, question):
    if question["kind"] == "score":
        return str(min(probs, key=lambda key: (-probs[key], float(key))))
    order = [option["key"] for option in question["options"]]
    return min(order, key=lambda key: (-probs[key], order.index(key)))


def resolve_outcome(raw, question):
    """原始答案对象 → outcome（answer/probs/execution_status/notes/flags）。"""
    flags = {}
    notes = []
    if not isinstance(raw, dict):
        return {"answer": None, "probs": None, "execution_status": "invalid",
                "notes": ["response has no answer object for this qid"], "flags": flags,
                "latency_ms": 0.0}
    value = raw.get("answer")
    probs = None
    raw_probs = raw.get("probs")
    if raw_probs is not None:
        if isinstance(raw_probs, dict) and raw_probs:
            expected = expected_prob_keys(question)
            try:
                probs = normalize_probs(raw_probs, keys=expected)
                if set(raw_probs) != set(expected):
                    flags["probs_partial"] = True
                    notes.append("probs_partial: 源只给了部分取值的概率（其余取值按 0 计）")
            except ValueError as error:
                notes.append(f"probs_dropped: {error}")
                flags["probs_dropped"] = True
        else:
            notes.append("probs_dropped: not a non-empty object")
            flags["probs_dropped"] = True
    if value is None and probs is not None:
        value = argmax_key(probs, question)
        flags["answer_from_probs"] = True
        notes.append("answer derived from probs argmax (source gave no discrete answer)")
    answer, why = coerce_answer(value, question)
    if why:
        flags["coerced"] = True
        notes.append(why)
    if answer is None:
        return {"answer": None, "probs": None, "execution_status": "invalid",
                "notes": notes, "flags": flags, "latency_ms": 0.0}
    return {"answer": answer, "probs": probs, "execution_status": "ok", "notes": notes,
            "flags": flags, "latency_ms": 0.0}


def build_answer_row(request, source, source_version, outcome):
    row = {"qid": request["qid"], "id": request["id"], "key": request["key"], "kind": request["kind"],
           "source": source, "source_version": source_version, "answer": outcome["answer"],
           "execution_status": outcome["execution_status"],
           "latency_ms": round(float(outcome.get("latency_ms") or 0.0), 2),
           "created_at": iso_now()}
    if outcome["execution_status"] == "ok" and outcome.get("probs") is not None:
        row["probs"] = {key: round(value, 6) for key, value in outcome["probs"].items()}
    return row


def failure_outcome(kind, reason, latency_ms=0.0):
    return {"answer": None, "probs": None, "execution_status": kind,
            "notes": [reason], "flags": {}, "latency_ms": latency_ms}


# --------------------------------------------------------------------- transport

class RateLimiter:
    """全局最小请求间隔（--rps）；0 表示不限速。"""

    def __init__(self, rps=0.0, clock=time.monotonic, sleeper=time.sleep):
        self.interval = 1.0 / rps if rps and rps > 0 else 0.0
        self.clock = clock
        self.sleeper = sleeper
        self.next_at = 0.0
        self.lock = threading.Lock()

    def wait(self):
        if not self.interval:
            return 0.0
        with self.lock:
            now = self.clock()
            delay = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + self.interval
        if delay > 0:
            self.sleeper(delay)
        return delay


def extract_usage(body, price_in=None, price_out=None):
    usage = body.get("usage") if isinstance(body, dict) and isinstance(body.get("usage"), dict) else {}
    prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    prompt = prompt if number(prompt) else None
    completion = completion if number(completion) else None
    total = total if number(total) else ((prompt or 0) + (completion or 0) or None)
    cost = None
    if price_in is not None and price_out is not None and (prompt or completion):
        cost = ((prompt or 0) * price_in + (completion or 0) * price_out) / 1_000_000
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total,
            "cost_usd": cost}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802 - urllib API
        return None


class HttpCaller:
    """带并发限速、超时、指数退避的 POST JSON 客户端；每次尝试写 calls.jsonl。"""

    def __init__(self, *, log, backend, source, source_version, key_fingerprint=None,
                 key_source=None, timeout=120.0, max_attempts=3, backoff=2.0, max_backoff=30.0,
                 jitter=0.25, limiter=None, opener=None, sleeper=time.sleep, rng=None,
                 user_agent=DEFAULT_USER_AGENT, price_in=None, price_out=None):
        self.log = log
        self.backend = backend
        self.source = source
        self.source_version = source_version
        self.key_fingerprint = key_fingerprint
        self.key_source = key_source
        self.timeout = timeout
        self.max_attempts = max(1, int(max_attempts))
        self.backoff = max(0.0, float(backoff))
        self.max_backoff = max(0.0, float(max_backoff))
        self.jitter = max(0.0, float(jitter))
        self.limiter = limiter
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.sleeper = sleeper
        self.rng = rng or random.Random(0)
        self.user_agent = user_agent
        self.price_in = price_in
        self.price_out = price_out

    def _delay(self, attempt, retry_after=None):
        base = min(self.backoff * (2 ** (attempt - 1)), self.max_backoff)
        if retry_after:
            try:
                base = min(float(retry_after), self.max_backoff)
            except (TypeError, ValueError):
                pass
        return max(0.0, base + self.rng.uniform(0, self.jitter * base))

    def _log_attempt(self, meta, attempt, ok, status_code, latency_ms, digest, error=None,
                     failure_kind=None, usage=None):
        row = {"phase": "attempt", "backend": self.backend, "source": self.source,
               "source_version": self.source_version, "qids": list(meta.get("qids") or []),
               "batch_size": len(meta.get("qids") or []), "attempt": attempt, "retries": attempt - 1,
               "ok": bool(ok), "status_code": status_code, "latency_ms": round(latency_ms, 2),
               "error": error, "failure_kind": failure_kind, "request_sha256": digest,
               "key_fingerprint": self.key_fingerprint, "key_source": self.key_source,
               "dry_run": False}
        row.update(usage or {"prompt_tokens": None, "completion_tokens": None,
                             "total_tokens": None, "cost_usd": None})
        self.log.record(row)
        return row

    def post_json(self, url, headers, body, meta):
        payload = json.dumps(body, ensure_ascii=False, allow_nan=False)
        digest = sha256_text(payload)
        raw = payload.encode("utf-8")
        last_failure = None
        delay = 0.0
        for attempt in range(1, self.max_attempts + 1):
            if self.limiter is not None:
                self.limiter.wait()
            started = time.perf_counter()
            status = None
            error_text = None
            response_headers = {}
            chunk = b""
            try:
                request = urllib.request.Request(url, data=raw, headers=headers, method="POST")
                with self.opener.open(request, timeout=self.timeout) as response:
                    status = int(getattr(response, "status", 200) or 200)
                    chunk = response.read(MAX_RESPONSE_BYTES + 1)
                    response_headers = dict(getattr(response, "headers", {}) or {})
            except urllib.error.HTTPError as error:
                status = int(error.code)
                chunk = error.read(MAX_RESPONSE_BYTES) or b""
                response_headers = dict(error.headers or {})
                error_text = f"HTTP {status}: {chunk[:200]!r}"
            except (TimeoutError, socket.timeout) as error:
                latency_ms = (time.perf_counter() - started) * 1000
                last_failure = CallFailure("timeout", f"timeout: {error}", None, attempt)
                self._log_attempt(meta, attempt, False, None, latency_ms, digest,
                                  error=f"timeout: {error}", failure_kind="timeout")
                if attempt == self.max_attempts:
                    raise last_failure
                self.sleeper(self._delay(attempt))
                continue
            except urllib.error.URLError as error:
                kind = "timeout" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "error"
                latency_ms = (time.perf_counter() - started) * 1000
                last_failure = CallFailure(kind, f"url error: {error.reason}", None, attempt)
                self._log_attempt(meta, attempt, False, None, latency_ms, digest,
                                  error=f"url error: {error.reason}", failure_kind=kind)
                if attempt == self.max_attempts:
                    raise last_failure
                self.sleeper(self._delay(attempt))
                continue
            except OSError as error:
                latency_ms = (time.perf_counter() - started) * 1000
                last_failure = CallFailure("error", f"os error: {error}", None, attempt)
                self._log_attempt(meta, attempt, False, None, latency_ms, digest,
                                  error=f"os error: {error}", failure_kind="error")
                if attempt == self.max_attempts:
                    raise last_failure
                self.sleeper(self._delay(attempt))
                continue

            latency_ms = (time.perf_counter() - started) * 1000
            if len(chunk) > MAX_RESPONSE_BYTES:
                self._log_attempt(meta, attempt, False, status, latency_ms, digest,
                                  error="response too large", failure_kind="invalid")
                raise CallFailure("invalid", "response too large", status, attempt, retryable=False)
            if status in RETRY_STATUS:
                error_text = error_text or f"HTTP {status}"
                last_failure = CallFailure("error", error_text, status, attempt)
                self._log_attempt(meta, attempt, False, status, latency_ms, digest, error=error_text,
                                  failure_kind="error")
                delay = self._delay(attempt, response_headers.get("Retry-After"))
            elif status != 200:
                error_text = error_text or f"HTTP {status}"
                self._log_attempt(meta, attempt, False, status, latency_ms, digest, error=error_text,
                                  failure_kind="error")
                raise CallFailure("error", error_text, status, attempt, retryable=False)
            else:
                try:
                    parsed = json.loads(chunk.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    self._log_attempt(meta, attempt, False, status, latency_ms, digest,
                                      error=f"bad JSON response: {error}", failure_kind="invalid")
                    raise CallFailure("invalid", f"bad JSON response: {error}", status, attempt,
                                      retryable=False) from error
                require(isinstance(parsed, dict), "response JSON must be an object")
                usage = extract_usage(parsed, self.price_in, self.price_out)
                self._log_attempt(meta, attempt, True, status, latency_ms, digest, usage=usage)
                return {"body": parsed, "usage": usage, "latency_ms": latency_ms,
                        "attempts": attempt, "status_code": status, "request_sha256": digest}
            if attempt == self.max_attempts:
                raise last_failure
            if delay > 0:
                self.sleeper(delay)
        raise last_failure or CallFailure("error", "no attempt made")


# --------------------------------------------------------------------- backends

class BaseBackend:
    name = "base"

    def __init__(self, *, source, source_version, log, caller=None):
        self.source = source
        self.source_version = source_version
        self.log = log
        self.caller = caller

    def plan(self, requests):  # pragma: no cover - overridden
        raise NotImplementedError

    def units(self, requests):
        return [[request] for request in requests]

    def execute(self, unit):  # pragma: no cover - overridden
        raise NotImplementedError

    def _log_outcomes(self, unit, outcomes, latency_ms=0.0):
        for request in unit:
            outcome = outcomes.get(request["qid"]) or failure_outcome(
                "invalid", "backend produced no outcome for this qid", latency_ms)
            outcome.setdefault("latency_ms", latency_ms)
            self.log.record({"phase": "outcome", "backend": self.name, "source": self.source,
                             "source_version": self.source_version, "qid": request["qid"],
                             "kind": request["kind"], "execution_status": outcome["execution_status"],
                             "failure_reason": " | ".join(outcome.get("notes") or []) or None,
                             "flags": outcome.get("flags") or {},
                             "latency_ms": round(float(outcome.get("latency_ms") or 0.0), 2)})
        return outcomes

    def _finish(self, unit, outcomes, latency_ms):
        for request in unit:
            outcome = outcomes.get(request["qid"])
            if outcome is not None and outcome["execution_status"] == "ok":
                outcome["latency_ms"] = latency_ms
        return self._log_outcomes(unit, outcomes, latency_ms)

    def _fail(self, unit, kind, reason, latency_ms=0.0):
        outcomes = {request["qid"]: failure_outcome(kind, reason, latency_ms) for request in unit}
        return self._log_outcomes(unit, outcomes, latency_ms)


def parse_jev_payload(body, unit):
    """官方 Jev 响应形状（未核实，按 pipeline/jev.py 的假设实现，两种形状都接受）。"""
    require(isinstance(body, dict), "Jev response must be a JSON object")
    if "answers" in body:
        payload = body["answers"]
    elif len(unit) == 1 and ("answer" in body or "probs" in body):
        return {unit[0]["qid"]: body}, []
    else:
        raise ValueError("unrecognized Jev response shape: expected an object with an answers "
                         "object/array (see ask.md「Jev 适配层」)")
    unknown = []
    if isinstance(payload, dict):
        wanted = {request["qid"] for request in unit}
        unknown = sorted(str(key) for key in payload if key not in wanted)
        return payload, unknown
    if isinstance(payload, list):
        indexed = {}
        for position, item in enumerate(payload):
            require(isinstance(item, dict), f"answers[{position}] must be an object")
            qid = item.get("qid")
            require(text(qid), f"answers[{position}] has no qid")
            require(qid not in indexed, f"duplicate qid in response: {qid}")
            indexed[qid] = item
        wanted = {request["qid"] for request in unit}
        unknown = sorted(set(indexed) - wanted)
        return indexed, unknown
    raise ValueError("answers must be an object keyed by qid or an array of objects with qid")


def require_jev_config(*, endpoint, api_version, integration_confirmed, live):
    """缺 endpoint / 版本 / --integration-confirmed 任一项直接拒绝（退出码 2），绝不静默降级。"""
    if live:
        require(text(endpoint), "Jev endpoint 未提供：拒绝运行（--endpoint）；"
                                "官方地址与请求形状见 ask.md")
        require(text(api_version), "官方 api_version 未提供：拒绝运行（--api-version）")
        require(bool(integration_confirmed),
                "Jev 协议未核实：先按官方文档核对请求/响应形状，再传 --integration-confirmed")
    else:
        require(text(endpoint), "离线预演也要 --endpoint 才能写出可用的请求计划")
        require(text(api_version), "离线预演也要 --api-version 才能写出请求包")


def require_chat_config(*, base_url, model):
    require(text(base_url), "--base-url 未提供：openai-compatible 后端需要它")
    require(text(model), "--model 未提供：openai-compatible 后端需要它")


class JevBackend(BaseBackend):
    """官方 Jev 适配层：缺 endpoint / 版本 / 密钥 / --integration-confirmed 任一项直接拒绝执行。"""

    name = "jev"

    def __init__(self, *, endpoint, api_version, key, key_source, request_path="", auth_scheme="bearer",
                 auth_header="X-API-Key", version_in="body", version_header="X-API-Version",
                 batch_size=1, extra_headers=None, source, source_version, log, caller, live,
                 integration_confirmed=False):
        super().__init__(source=source, source_version=source_version, log=log, caller=caller)
        require_jev_config(endpoint=endpoint, api_version=api_version,
                           integration_confirmed=integration_confirmed, live=live)
        if live:
            require(bool(key), "Jev 密钥缺失：设置 --key-env 指向的环境变量或 --key-file")
        require(integer(batch_size) and batch_size >= 1, "--batch-size must be a positive integer")
        require(auth_scheme in ("bearer", "api-key", "none"),
                "--auth-scheme must be one of bearer / api-key / none")
        require(version_in in ("body", "header"), "--version-in must be body or header")
        self.endpoint = validate_endpoint(endpoint)
        self.api_version = api_version
        self.key = key
        self.key_source = key_source
        self.request_path = request_path or ""
        self.auth_scheme = auth_scheme
        self.auth_header = auth_header
        self.version_in = version_in
        self.version_header = version_header
        self.batch_size = batch_size
        self.extra_headers = dict(extra_headers or {})
        self.url = self.endpoint.rstrip("/") + (self.request_path if self.request_path.startswith("/")
                                                else ("/" + self.request_path if self.request_path else ""))

    def headers(self):
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "User-Agent": self.caller.user_agent if self.caller else DEFAULT_USER_AGENT}
        if self.auth_scheme == "bearer":
            headers["Authorization"] = "Bearer " + self.key if self.key else "<unset; 离线预演未读密钥>"
        elif self.auth_scheme == "api-key":
            headers[self.auth_header] = self.key or "<unset; 离线预演未读密钥>"
        if self.version_in == "header":
            headers[self.version_header] = self.api_version
        headers.update(self.extra_headers)
        return headers

    def redacted_headers(self):
        if not self.key:
            return self.headers()
        return {name: ("<redacted; from " + (self.key_source or "key") + ">"
                       if name in ("Authorization", self.auth_header) else value)
                for name, value in self.headers().items()}

    def envelope(self, unit):
        body = {"requests": [{"qid": request["qid"], "kind": request["kind"],
                              "state": request["state"], "question": request["question"],
                              **({"options": request["options"]} if "options" in request
                                 else {"scale": request["scale"]})}
                             for request in unit]}
        if self.version_in == "body":
            body["api_version"] = self.api_version
        return body

    def units(self, requests):
        size = self.batch_size
        return [requests[index:index + size] for index in range(0, len(requests), size)]

    def plan(self, requests):
        rows = []
        for seq, unit in enumerate(self.units(requests), 1):
            rows.append({"seq": seq, "backend": self.name, "method": "POST", "url": self.url,
                         "headers": self.redacted_headers(), "body": self.envelope(unit),
                         "qids": [request["qid"] for request in unit]})
        return rows

    def execute(self, unit):
        meta = {"qids": [request["qid"] for request in unit]}
        try:
            result = self.caller.post_json(self.url, self.headers(), self.envelope(unit), meta)
        except CallFailure as failure:
            return self._fail(unit, failure.kind, f"{failure.kind}: {failure}", 0.0)
        try:
            payload, unknown = parse_jev_payload(result["body"], unit)
        except ValueError as error:
            return self._fail(unit, "invalid", f"unrecognized Jev response: {error}",
                              result["latency_ms"])
        outcomes = {}
        for request in unit:
            item = payload.get(request["qid"]) if isinstance(payload, dict) else None
            if item is None:
                outcomes[request["qid"]] = failure_outcome(
                    "invalid", "missing qid in Jev response", result["latency_ms"])
            else:
                outcomes[request["qid"]] = resolve_outcome(item, request)
        self.log.record({"phase": "batch", "backend": self.name, "source": self.source,
                         "source_version": self.source_version, "qids": meta["qids"],
                         "batch_size": len(unit), "status_code": result["status_code"],
                         "unknown_qids": unknown,
                         "ok": sum(1 for outcome in outcomes.values()
                                   if outcome["execution_status"] == "ok"),
                         "latency_ms": round(result["latency_ms"], 2),
                         "prompt_tokens": result["usage"].get("prompt_tokens"),
                         "completion_tokens": result["usage"].get("completion_tokens")})
        return self._finish(unit, outcomes, result["latency_ms"])


def extract_json_object(value):
    start = value.find("{")
    require(start >= 0, "no JSON object in response text")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(value)):
        char = value[index]
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
                return json.loads(value[start:index + 1])
    raise ValueError("unbalanced JSON object in response text")


def chat_prompt(request):
    lines = [f"你是严格的判定器（模板 {CHAT_TEMPLATE_VERSION}）。只输出一个 JSON 对象，"
             "不要解释、不要 Markdown 代码块。", "", "情境（state）：", request["state"], "",
             f"问题（question）：{request['question']}"]
    if request["kind"] == "score":
        scale = request["scale"]
        levels = list(range(int(scale["min"]), int(scale["max"]) + 1))
        described = "；".join(f"{level}={label}" for level, label in zip(levels, scale["labels"]))
        lines.append(f"整数分级：{described}")
        lines.append('输出格式：{"answer": <整数分值>, "probs": {"<分值>": <非负权重>, ...}}')
    else:
        lines.append("可选答案（answer 必须原样返回 key）："
                     + "；".join(f"{option['key']}={option['label']}" for option in request["options"]))
        lines.append('输出格式：{"answer": "<key>", "probs": {"<key>": <非负权重>, ...}}')
    lines.append("probs 可省略；给出时权重必须非负、键必须与可选答案一致。")
    return "\n".join(lines)


class OpenAICompatibleBackend(BaseBackend):
    """OpenAI 兼容 chat completions 后端（每问一次请求）；Jev 若走该形状可直接使用。"""

    name = "openai-compatible"

    def __init__(self, *, base_url, model, key, key_source, chat_path="/chat/completions",
                 max_tokens=2048, temperature=None, response_format=None, extra_headers=None,
                 source, source_version, log, caller, live):
        super().__init__(source=source, source_version=source_version, log=log, caller=caller)
        require_chat_config(base_url=base_url, model=model)
        if live:
            require(bool(key), "密钥缺失：设置 --key-env 指向的环境变量或 --key-file")
        require(response_format in (None, "json_object"),
                "--response-format 只支持 json_object（不猜其他形状）")
        require(integer(max_tokens) and max_tokens > 0, "--max-tokens must be a positive integer")
        self.base_url = validate_endpoint(base_url.rstrip("/"))
        self.model = model
        self.key = key
        self.key_source = key_source
        self.chat_path = chat_path if chat_path.startswith("/") else "/" + chat_path
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.response_format = response_format
        self.extra_headers = dict(extra_headers or {})
        self.url = self.base_url + self.chat_path

    def headers(self):
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "User-Agent": self.caller.user_agent if self.caller else DEFAULT_USER_AGENT,
                   "Authorization": "Bearer " + self.key if self.key else "<unset; 离线预演未读密钥>"}
        headers.update(self.extra_headers)
        return headers

    def redacted_headers(self):
        if not self.key:
            return self.headers()
        return {name: ("<redacted; from " + (self.key_source or "key") + ">"
                       if name == "Authorization" else value)
                for name, value in self.headers().items()}

    def body(self, request):
        body = {"model": self.model, "messages": [{"role": "user", "content": chat_prompt(request)}],
                "max_tokens": self.max_tokens}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.response_format:
            body["response_format"] = {"type": self.response_format}
        return body

    def units(self, requests):
        return [[request] for request in requests]

    def plan(self, requests):
        return [{"seq": seq, "backend": self.name, "method": "POST", "url": self.url,
                 "headers": self.redacted_headers(), "body": self.body(request),
                 "qids": [request["qid"]]}
                for seq, request in enumerate(requests, 1)]

    def execute(self, unit):
        request = unit[0]
        meta = {"qids": [request["qid"]]}
        try:
            result = self.caller.post_json(self.url, self.headers(), self.body(request), meta)
        except CallFailure as failure:
            return self._fail(unit, failure.kind, f"{failure.kind}: {failure}", 0.0)
        text_value = None
        choices = result["body"].get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                for candidate in (message.get("content"), message.get("reasoning_content")):
                    if isinstance(candidate, str) and candidate.strip():
                        text_value = candidate
                        break
        if text_value is None:
            return self._fail(unit, "invalid", "empty content and reasoning_content "
                                               "(max_tokens 可能被 reasoning 吃光)",
                              result["latency_ms"])
        try:
            item = extract_json_object(text_value)
            require(isinstance(item, dict), "answer JSON must be an object")
        except (ValueError, json.JSONDecodeError) as error:
            return self._fail(unit, "invalid", f"no parseable answer JSON: {error}",
                              result["latency_ms"])
        outcomes = {request["qid"]: resolve_outcome(item, request)}
        self.log.record({"phase": "batch", "backend": self.name, "source": self.source,
                         "source_version": self.source_version, "qids": meta["qids"],
                         "batch_size": 1, "status_code": result["status_code"], "unknown_qids": [],
                         "ok": sum(1 for outcome in outcomes.values()
                                   if outcome["execution_status"] == "ok"),
                         "latency_ms": round(result["latency_ms"], 2),
                         "prompt_tokens": result["usage"].get("prompt_tokens"),
                         "completion_tokens": result["usage"].get("completion_tokens")})
        return self._finish(unit, outcomes, result["latency_ms"])


class FixtureBackend(BaseBackend):
    """离线确定性合成答案：跑通链路与测试用，**永远不是真值**。"""

    name = "fixture"

    def __init__(self, *, source=FIXTURE_SOURCE, source_version=FIXTURE_VERSION, seed=20260930,
                 fail_rate=0.0, log):
        super().__init__(source=source, source_version=source_version, log=log, caller=None)
        require(0.0 <= fail_rate <= 1.0, "--fixture-fail-rate must be within [0, 1]")
        self.seed = seed
        self.fail_rate = fail_rate

    def _raw(self, request):
        digest = hashlib.sha256(f"{self.seed}|{request['qid']}".encode("utf-8")).digest()
        draw = int.from_bytes(digest[:8], "big") / float(2 ** 64)
        if draw < self.fail_rate:
            kind = "timeout" if digest[8] % 2 else "error"
            return None, kind, f"fixture injected {kind}"
        if request["kind"] == "score":
            scale = request["scale"]
            levels = list(range(int(scale["min"]), int(scale["max"]) + 1))
            require(len(scale["labels"]) == len(levels), "scale.labels 必须覆盖 min..max")
            weights = {str(level): 1 + int.from_bytes(
                hashlib.sha256(f"{self.seed}|{request['qid']}|{level}".encode()).digest()[:4],
                "big") % 5 for level in levels}
            return {"probs": weights}, "ok", ""
        keys = [option["key"] for option in request["options"]]
        weights = {key: 1 + int.from_bytes(
            hashlib.sha256(f"{self.seed}|{request['qid']}|{key}".encode()).digest()[:4], "big") % 5
            for key in keys}
        best = min(keys, key=lambda key: (-weights[key], keys.index(key)))
        return {"answer": best, "probs": weights}, "ok", ""

    def plan(self, requests):
        return [{"seq": seq, "backend": self.name, "method": None, "url": None, "headers": {},
                 "body": {"qid": request["qid"], "rule": "deterministic sha256(seed|qid)",
                          "fail_rate": self.fail_rate, "note": "离线合成答案，不是真值"},
                 "qids": [request["qid"]]} for seq, request in enumerate(requests, 1)]

    def execute(self, unit):
        request = unit[0]
        raw, status, reason = self._raw(request)
        if status != "ok":
            self.log.record({"phase": "attempt", "backend": self.name, "source": self.source,
                             "source_version": self.source_version, "qids": [request["qid"]],
                             "batch_size": 1, "attempt": 1, "retries": 0, "ok": False,
                             "status_code": None, "latency_ms": 0.0, "error": reason,
                             "failure_kind": status, "request_sha256": None,
                             "key_fingerprint": None, "key_source": None, "dry_run": False,
                             "prompt_tokens": None, "completion_tokens": None,
                             "total_tokens": None, "cost_usd": None, "fixture": True})
            return self._fail(unit, status, reason, 0.0)
        outcome = resolve_outcome(raw, request)
        self.log.record({"phase": "attempt", "backend": self.name, "source": self.source,
                         "source_version": self.source_version, "qids": [request["qid"]],
                         "batch_size": 1, "attempt": 1, "retries": 0,
                         "ok": outcome["execution_status"] == "ok", "status_code": None,
                         "latency_ms": 0.0, "error": None, "failure_kind": None,
                         "request_sha256": sha256_text(json.dumps(raw, ensure_ascii=False,
                                                                  sort_keys=True)),
                         "key_fingerprint": None, "key_source": None, "dry_run": False,
                         "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                         "cost_usd": None, "fixture": True})
        return self._finish(unit, {request["qid"]: outcome}, 0.0)


# --------------------------------------------------------------------- run

class Deps:
    """测试注入点：opener 假 HTTP、sleeper 不真睡、environ 假环境变量。"""

    def __init__(self, opener=None, sleeper=time.sleep, environ=None, clock=time.monotonic):
        self.opener = opener
        self.sleeper = sleeper
        self.environ = environ
        self.clock = clock


def resolve_mode(args):
    if args.backend == "fixture":
        if args.live:
            raise ConfigError("fixture 是离线后端，不能与 --live 同用（合成答案不是真值）")
        return "dry-run" if args.dry_run else "fixture"
    if getattr(args, "live", False):
        return "live"
    return "dry-run"


def backend_identity(args):
    """(source, source_version)：写进 answers 文件名与 source 字段。"""
    if args.backend == "fixture":
        source = args.source or FIXTURE_SOURCE
        require(source == FIXTURE_SOURCE or source.startswith(FIXTURE_SOURCE + "-")
                or source.startswith(FIXTURE_SOURCE + "_"),
                "--backend fixture 的 --source 必须是 fixture 或 fixture-*，"
                "避免把合成答案当真值（契约 2.2 的 source 字段）")
        return source, args.source_version or FIXTURE_VERSION
    if args.backend == "jev":
        version = args.api_version or args.source_version
        require(text(version), "缺少 --api-version（Jev 版本号）：无法确定 source=jev-<版本>")
        return args.source or f"jev-{version}", args.source_version or version
    require(text(args.source), "openai-compatible 后端必须给出 --source（写进 source 字段与文件名）")
    require(text(args.model), "openai-compatible 后端必须给出 --model")
    return args.source, args.source_version or args.model


def resolve_output_path(out, source):
    path = Path(out)
    if path.exists() and path.is_dir():
        return path / f"answers.{source}.jsonl"
    if path.suffix.lower() == ".jsonl":
        return path
    return path / f"answers.{source}.jsonl"


def build_backend(args, source, source_version, log, deps, live):
    if args.backend == "fixture":
        return FixtureBackend(source=source, source_version=source_version, seed=args.seed,
                              fail_rate=args.fixture_fail_rate, log=log)
    limiter = RateLimiter(args.rps, clock=deps.clock, sleeper=deps.sleeper)
    if args.backend == "jev":
        require_jev_config(endpoint=args.endpoint, api_version=args.api_version,
                           integration_confirmed=args.integration_confirmed, live=live)
        key, key_source = (None, None)
        if live:
            key, key_source = load_secret([args.key_env or DEFAULT_KEY_ENV["jev"]],
                                          key_file=args.key_file,
                                          ref=args.key_env or DEFAULT_KEY_ENV["jev"],
                                          environ=deps.environ)
        caller = HttpCaller(log=log, backend="jev", source=source, source_version=source_version,
                            key_fingerprint=fingerprint(key) if key else None,
                            key_source=key_source, timeout=args.timeout,
                            max_attempts=args.max_attempts, backoff=args.backoff,
                            max_backoff=args.max_backoff, limiter=limiter, opener=deps.opener,
                            sleeper=deps.sleeper, user_agent=args.user_agent, price_in=args.price_in,
                            price_out=args.price_out)
        return JevBackend(endpoint=args.endpoint, api_version=args.api_version, key=key,
                          key_source=key_source, request_path=args.request_path or "",
                          auth_scheme=args.auth_scheme, auth_header=args.auth_header,
                          version_in=args.version_in, version_header=args.version_header,
                          batch_size=args.batch_size, extra_headers=parse_headers(args.extra_header),
                          source=source, source_version=source_version, log=log, caller=caller,
                          live=live, integration_confirmed=args.integration_confirmed)
    if args.backend == "openai-compatible":
        require_chat_config(base_url=args.base_url, model=args.model)
        key, key_source = (None, None)
        if live:
            key, key_source = load_secret([args.key_env or DEFAULT_KEY_ENV["openai-compatible"]],
                                          key_file=args.key_file,
                                          ref=args.key_env or DEFAULT_KEY_ENV["openai-compatible"],
                                          environ=deps.environ)
        caller = HttpCaller(log=log, backend="openai-compatible", source=source,
                            source_version=source_version,
                            key_fingerprint=fingerprint(key) if key else None,
                            key_source=key_source, timeout=args.timeout,
                            max_attempts=args.max_attempts, backoff=args.backoff,
                            max_backoff=args.max_backoff, limiter=limiter, opener=deps.opener,
                            sleeper=deps.sleeper, user_agent=args.user_agent, price_in=args.price_in,
                            price_out=args.price_out)
        return OpenAICompatibleBackend(base_url=args.base_url, model=args.model, key=key,
                                       key_source=key_source, chat_path=args.chat_path,
                                       max_tokens=args.max_tokens, temperature=args.temperature,
                                       response_format=args.response_format,
                                       extra_headers=parse_headers(args.extra_header),
                                       source=source, source_version=source_version, log=log,
                                       caller=caller, live=live)
    raise ConfigError(f"unknown backend {args.backend!r}")


def parse_headers(values):
    headers = {}
    for value in values or []:
        require("=" in value, f"--extra-header must be NAME=VALUE, got {value!r}")
        name, header_value = value.split("=", 1)
        require(text(name) and text(header_value), f"--extra-header must be NAME=VALUE, got {value!r}")
        headers[name.strip()] = header_value.strip()
    return headers


def load_prior_rows(answers_path, journal_path, questions):
    """读已有 answers 与 journal；journal 后写优先（断点续跑的真实来源）。"""
    rows = []
    answers_path = Path(answers_path)
    journal_path = Path(journal_path)
    if answers_path.exists():
        existing = read_jsonl(answers_path)
        seen = set()
        for position, row in enumerate(existing, 1):
            where = f"{answers_path}[{position}]"
            qid = row.get("qid") if isinstance(row, dict) else None
            validate_answer_row(row, where=where, question=questions.get(qid))
            require(qid not in seen, f"{where}: duplicate qid {qid}")
            seen.add(qid)
            rows.append(row)
    if journal_path.exists():
        for position, row in enumerate(read_jsonl(journal_path), 1):
            where = f"{journal_path}[{position}]"
            qid = row.get("qid") if isinstance(row, dict) else None
            validate_answer_row(row, where=where, question=questions.get(qid))
            rows.append(row)
    return rows


def merge_rows(prior_rows, new_rows, current_order):
    merged = {}
    order = []
    for row in prior_rows:
        qid = row["qid"]
        if qid not in merged:
            order.append(qid)
        merged[qid] = row
    for qid, row in new_rows.items():
        if qid not in merged:
            order.append(qid)
        merged[qid] = row
    head = [qid for qid in current_order if qid in merged]
    head_set = set(head)
    tail = [qid for qid in order if qid not in head_set]
    return [merged[qid] for qid in head + tail]


def cmd_run(args, deps):
    mode = resolve_mode(args)
    all_requests, selected = load_requests(args.items, keys=csv_list(args.keys),
                                           domains=csv_list(args.domains), limit=args.limit,
                                           strict_items=not args.skip_item_schema)
    questions = {request["qid"]: request for request in all_requests}
    source, source_version = backend_identity(args)
    answers_path = resolve_output_path(args.out, source)
    calls_path = Path(args.calls) if args.calls else answers_path.parent / f"calls.{source}.jsonl"
    journal_path = Path(args.journal) if args.journal else answers_path.parent / f"journal.{source}.jsonl"
    requests_path = (Path(args.requests_out) if args.requests_out
                     else answers_path.parent / f"requests.{source}.jsonl")
    log = CallLog(calls_path)
    backend = build_backend(args, source, source_version, log, deps, live=mode == "live")
    prior_rows = load_prior_rows(answers_path, journal_path, questions)
    recorded = {}
    for row in prior_rows:
        recorded[row["qid"]] = row
    done_ok = {qid for qid, row in recorded.items() if row["execution_status"] == "ok"}
    recorded_failed = {qid for qid, row in recorded.items() if row["execution_status"] != "ok"}
    todo = [request for request in selected
            if request["qid"] not in done_ok
            and (args.retry_failed or request["qid"] not in recorded_failed)]
    skipped_ok = sum(1 for request in selected if request["qid"] in done_ok)
    skipped_failed = sum(1 for request in selected
                         if request["qid"] in recorded_failed and not args.retry_failed)

    if mode == "dry-run":
        plan = backend.plan(todo)
        write_jsonl_atomic(requests_path, plan)
        digest = sha256_text(jsonl_text(plan))
        print(json.dumps({"command": "run", "mode": "dry-run", "offline": True,
                          "backend": args.backend, "source": source,
                          "source_version": source_version, "items": str(args.items),
                          "answers": str(answers_path), "planned": len(plan),
                          "planned_qids": len(todo), "selected": len(selected),
                          "skipped_ok": skipped_ok, "skipped_failed": skipped_failed,
                          "requests": str(requests_path), "requests_sha256": digest,
                          "item_schema_checked": not args.skip_item_schema,
                          "note": "只写请求计划，未联网；加 --live 才真调"}, ensure_ascii=False))
        return 0

    units = backend.units(todo)
    new_rows = {}
    failures = {"timeout": 0, "error": 0, "invalid": 0}
    journal = JsonlAppender(journal_path)
    started = time.perf_counter()
    interrupted = False

    def work(unit):
        try:
            return backend.execute(unit)
        except Exception as error:  # noqa: BLE001 - 任何异常都不许写成 ok
            return {request["qid"]: failure_outcome("error", f"backend crashed: {error}")
                    for request in unit}

    print(json.dumps({"started": {"backend": args.backend, "source": source, "units": len(units),
                                  "requests": len(todo), "workers": args.workers,
                                  "answers": str(answers_path), "calls": str(calls_path)}},
                     ensure_ascii=False), file=sys.stderr)
    workers = max(1, min(args.workers, max(1, len(units))))
    window = max(workers * 4, workers)
    pool = ThreadPoolExecutor(max_workers=workers)
    pending = {}
    done_units = 0
    position = 0
    try:
        # 有界窗口：Ctrl+C 时只等已在飞的请求，不把整个队列跑完。
        while position < len(units) or pending:
            while position < len(units) and len(pending) < window:
                unit = units[position]
                position += 1
                pending[pool.submit(work, unit)] = unit
            if not pending:
                break
            finished = wait(list(pending), return_when=FIRST_COMPLETED).done
            for future in finished:
                unit = pending.pop(future)
                outcomes = future.result()
                for request in unit:
                    outcome = outcomes.get(request["qid"]) or failure_outcome(
                        "invalid", "backend produced no outcome for this qid")
                    row = build_answer_row(request, source, source_version, outcome)
                    try:
                        validate_answer_row(row, where=f"answer {request['qid']}", question=request)
                    except ValueError as error:
                        row = build_answer_row(request, source, source_version,
                                               failure_outcome("invalid",
                                                               f"contract self-check failed: {error}"))
                        validate_answer_row(row, where=f"answer {request['qid']}", question=request)
                    new_rows[row["qid"]] = row
                    journal.append(row)
                done_units += 1
                if not args.quiet and args.progress_every > 0 and done_units % args.progress_every == 0:
                    counts = {"ok": 0, "timeout": 0, "error": 0, "invalid": 0}
                    for row in new_rows.values():
                        counts[row["execution_status"]] += 1
                    print(json.dumps({"progress": {"units_done": done_units, "units_total": len(units),
                                                   "ok": counts["ok"], "failed": len(new_rows) - counts["ok"],
                                                   "elapsed_s": round(time.perf_counter() - started, 1)}},
                                     ensure_ascii=False), file=sys.stderr)
    except KeyboardInterrupt:
        interrupted = True
        for future in pending:
            future.cancel()
        print(json.dumps({"interrupted": True, "finished_qids": len(new_rows),
                          "note": "已完成部分已落盘到 journal，重跑同一条命令即可续跑"},
                         ensure_ascii=False), file=sys.stderr)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        journal.close()
        log.close()

    for row in new_rows.values():
        if row["execution_status"] != "ok":
            failures[row["execution_status"]] += 1
    final = merge_rows(prior_rows, new_rows, [request["qid"] for request in all_requests])
    write_jsonl_atomic(answers_path, final)
    write_jsonl_atomic(journal_path, final)
    ok_total = sum(1 for row in final if row["execution_status"] == "ok")
    summary = {"command": "run", "mode": mode, "backend": args.backend, "source": source,
               "source_version": source_version, "items": str(args.items),
               "answers": str(answers_path), "journal": str(journal_path), "calls": str(calls_path),
               "selected": len(selected), "attempted": len(todo), "skipped_ok": skipped_ok,
               "skipped_failed": skipped_failed, "new_failures": failures, "ok_total": ok_total,
               "rows_total": len(final), "elapsed_s": round(time.perf_counter() - started, 1),
               "item_schema_checked": not args.skip_item_schema,
               "interrupted": interrupted, "call_summary": log.summary()}
    if skipped_failed and not args.retry_failed:
        summary["hint"] = f"{skipped_failed} 条已记录的失败项被跳过；加 --retry-failed 重跑"
    final_index = {row["qid"]: row for row in final}
    remaining = [request["qid"] for request in selected
                 if (final_index.get(request["qid"]) or {}).get("execution_status") != "ok"]
    summary["ok_selected"] = len(selected) - len(remaining)
    summary["remaining_not_ok"] = len(remaining)
    summary["remaining_sample"] = remaining[:10]
    print(json.dumps(summary, ensure_ascii=False))
    if remaining:
        print(json.dumps({"done": False, "remaining_not_ok": len(remaining),
                          "next": "重跑同一条命令并加 --retry-failed"},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    return 1 if interrupted else 0


def cmd_plan(args, deps):
    _, selected = load_requests(args.items, keys=csv_list(args.keys), domains=csv_list(args.domains),
                                limit=args.limit, strict_items=not args.skip_item_schema)
    rows = [plan_row(request) for request in selected]
    write_jsonl_atomic(args.out, rows)
    print(json.dumps({"command": "plan", "mode": "offline", "items": str(args.items),
                      "requests": str(args.out), "requests_count": len(rows),
                      "requests_sha256": sha256_text(jsonl_text(rows)),
                      "kinds": {kind: sum(1 for row in rows if row["kind"] == kind)
                                for kind in KINDS},
                      "item_schema_checked": not args.skip_item_schema,
                      "note": "qid/state/question/options 可直接交给 Jev；本命令不联网"},
                     ensure_ascii=False))
    return 0


# --------------------------------------------------------------------- report / verify

def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def aggregate_calls(rows):
    attempts = [row for row in rows if row.get("phase", "attempt") == "attempt"]
    outcomes = [row for row in rows if row.get("phase") == "outcome"]
    batches = [row for row in rows if row.get("phase") == "batch"]
    ok_attempts = [row for row in attempts if row.get("ok")]
    failed_attempts = [row for row in attempts if not row.get("ok")]
    by_kind = {}
    for row in failed_attempts:
        kind = row.get("failure_kind") or "error"
        by_kind[kind] = by_kind.get(kind, 0) + 1
    status_codes = {}
    for row in attempts:
        code = row.get("status_code")
        if code is not None:
            status_codes[str(code)] = status_codes.get(str(code), 0) + 1
    latencies = [row["latency_ms"] for row in ok_attempts if number(row.get("latency_ms"))]
    costs = [row["cost_usd"] for row in attempts if number(row.get("cost_usd"))]
    keys = {}
    sources = {}
    for row in attempts:
        if row.get("key_fingerprint"):
            keys.setdefault(row["key_fingerprint"], set()).add(row.get("key_source") or "?")
        if row.get("source"):
            sources[row["source"]] = sources.get(row["source"], 0) + 1
    outcome_status = {}
    failure_reasons = {}
    for row in outcomes:
        status = row.get("execution_status") or "invalid"
        outcome_status[status] = outcome_status.get(status, 0) + 1
        if status != "ok":
            reason = row.get("failure_reason") or "unknown"
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    summary = {
        "attempts": len(attempts), "attempts_ok": len(ok_attempts),
        "attempts_failed": len(failed_attempts),
        "retries": sum(1 for row in attempts if (row.get("retries") or 0) > 0),
        "dry_run_rows": sum(1 for row in attempts if row.get("dry_run")),
        "failure_kind": by_kind, "status_code": status_codes, "sources": sources,
        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in attempts),
        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in attempts),
        "total_tokens": sum(row.get("total_tokens") or 0 for row in attempts),
        "cost_usd": round(sum(costs), 6) if costs else None,
        "latency_ms_p50": percentile(latencies, 0.5), "latency_ms_p95": percentile(latencies, 0.95),
        "latency_ms_max": max(latencies) if latencies else None,
        "key_fingerprints": {key: sorted(origins) for key, origins in keys.items()},
        "batches": len(batches),
        "batches_with_unknown_qids": sum(1 for row in batches if row.get("unknown_qids")),
        "outcomes": outcome_status,
        "qids_recorded": len({row.get("qid") for row in outcomes if row.get("qid")}),
        "failure_reasons": dict(sorted(failure_reasons.items(), key=lambda pair: -pair[1])),
    }
    return summary


def load_answers_file(path, questions):
    rows = read_jsonl(path)
    index = {}
    for position, row in enumerate(rows, 1):
        where = f"{path}[{position}]"
        qid = row.get("qid") if isinstance(row, dict) else None
        validate_answer_row(row, where=where, question=questions.get(qid))
        require(qid not in index, f"{where}: duplicate qid {qid}")
        index[qid] = row
    return rows, index


def cmd_report(args, deps):
    calls_path = Path(args.calls)
    require(calls_path.is_file(), f"missing call log: {calls_path}")
    rows = read_jsonl(calls_path)
    summary = aggregate_calls(rows)
    report = {"command": "report", "calls": str(calls_path), **summary}
    questions = {}
    if args.items:
        all_requests, _ = load_requests(args.items, strict_items=False)
        questions = {request["qid"]: request for request in all_requests}
        report["items"] = str(args.items)
        report["items_requests"] = len(all_requests)
    answer_rows = []
    if args.answers:
        answers_path = Path(args.answers)
        require(answers_path.is_file(), f"missing answers file: {answers_path}")
        answer_rows, _ = load_answers_file(answers_path, questions)
        by_status = {}
        by_kind = {}
        for row in answer_rows:
            by_status[row["execution_status"]] = by_status.get(row["execution_status"], 0) + 1
            by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        report["answers"] = str(answers_path)
        report["answers_rows"] = len(answer_rows)
        report["answers_status"] = by_status
        report["answers_kinds"] = by_kind
        report["answers_failures"] = [
            {"qid": row["qid"], "execution_status": row["execution_status"],
             "source": row["source"], "source_version": row["source_version"]}
            for row in answer_rows if row["execution_status"] != "ok"][:args.top]
        if questions:
            recorded = {row["qid"] for row in answer_rows}
            missing = [qid for qid in questions if qid not in recorded]
            failed = [row["qid"] for row in answer_rows
                      if row["execution_status"] != "ok" and row["qid"] in questions]
            report["coverage"] = {"expected": len(questions), "recorded": len(recorded & set(questions)),
                                  "missing": len(missing), "failed": len(failed),
                                  "missing_sample": missing[:args.top], "failed_sample": failed[:args.top]}
    reasons = [{"qid": row.get("qid"), "execution_status": row.get("execution_status"),
                "reason": row.get("failure_reason")} for row in rows
               if row.get("phase") == "outcome" and row.get("execution_status") != "ok"]
    reason_index = {}
    for item in reasons:
        reason_index.setdefault(item["qid"], item)
    report["top_failures"] = list(reason_index.values())[:args.top]
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"calls        : {report['calls']}")
    print(f"attempts     : {summary['attempts']} (ok {summary['attempts_ok']}, "
          f"failed {summary['attempts_failed']}, retries {summary['retries']}, "
          f"dry_run {summary['dry_run_rows']})")
    print(f"failure_kind : {summary['failure_kind'] or '-'}")
    print(f"status_codes : {summary['status_code'] or '-'}")
    print(f"tokens       : prompt={summary['prompt_tokens']} "
          f"completion={summary['completion_tokens']} total={summary['total_tokens']}")
    cost = summary["cost_usd"]
    print(f"cost_usd     : {cost if cost is not None else 'null（未提供 --price-in/--price-out，不编造）'}")
    print(f"latency_ms   : p50={summary['latency_ms_p50']} p95={summary['latency_ms_p95']} "
          f"max={summary['latency_ms_max']} (仅成功尝试)")
    print(f"keys         : {summary['key_fingerprints'] or '-'}")
    print(f"sources      : {summary['sources'] or '-'}")
    print(f"outcomes     : {summary['outcomes'] or '-'} (qids={summary['qids_recorded']})")
    if "answers_rows" in report:
        print(f"answers      : {report['answers']} rows={report['answers_rows']} "
              f"{report['answers_status']}")
        print(f"answers_kinds: {report['answers_kinds']}")
    if "coverage" in report:
        coverage = report["coverage"]
        print(f"coverage     : expected={coverage['expected']} recorded={coverage['recorded']} "
              f"missing={coverage['missing']} failed={coverage['failed']}")
    if report["top_failures"]:
        print("top_failures :")
        for item in report["top_failures"]:
            print(f"  {item['qid']} [{item['execution_status']}] {str(item['reason'])[:160]}")
    else:
        print("top_failures : -")
    return 0


def cmd_verify(args, deps):
    all_requests, _ = load_requests(args.items, strict_items=False)
    questions = {request["qid"]: request for request in all_requests}
    raw_rows = read_jsonl(args.answers)
    violations = []
    index = {}
    for position, row in enumerate(raw_rows, 1):
        where = f"{args.answers}[{position}]"
        qid = row.get("qid") if isinstance(row, dict) else None
        try:
            validate_answer_row(row, where=where, question=questions.get(qid))
        except ValueError as error:
            violations.append(str(error))
            continue
        if qid in index:
            violations.append(f"{where}: duplicate qid {qid}")
            continue
        index[qid] = row
    rows = list(index.values())
    expected = set(questions)
    recorded = set(index)
    missing = sorted(expected - recorded)
    extra = sorted(recorded - expected)
    failed = sorted(qid for qid, row in index.items() if row["execution_status"] != "ok")
    by_status = {}
    for row in rows:
        by_status[row["execution_status"]] = by_status.get(row["execution_status"], 0) + 1
    report = {"command": "verify", "items": str(args.items), "answers": str(args.answers),
              "rows": len(rows), "expected": len(expected), "recorded": len(recorded),
              "missing": len(missing), "extra": len(extra), "failed": len(failed),
              "by_status": by_status, "violations": violations[:args.top],
              "violations_total": len(violations), "missing_sample": missing[:args.top],
              "failed_sample": failed[:args.top], "extra_sample": extra[:args.top],
              "complete": not missing and not failed and not violations}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"items    : {report['items']} (expected qids {report['expected']})")
        print(f"answers  : {report['answers']} rows={report['rows']} by_status={by_status}")
        print(f"coverage : missing={len(missing)} failed={len(failed)} extra={len(extra)}")
        print(f"contract : violations={len(violations)}")
        for line in violations[:args.top]:
            print(f"  violation: {line}")
        for qid in missing[:args.top]:
            print(f"  missing  : {qid}")
        for qid in failed[:args.top]:
            print(f"  failed   : {qid}")
        print(f"complete : {report['complete']}")
    if violations:
        return 2
    if missing or failed:
        return 0 if args.allow_incomplete else 1
    return 0


# --------------------------------------------------------------------- CLI

def add_item_check(parser):
    parser.add_argument("--skip-item-schema", action="store_true",
                        help="跳过 taxonomy.item_errors 全条目校验（只校验本 harness 消费的字段）；"
                             "默认在花钱调用前拦住形状不对的条目")


def add_selection(parser):
    parser.add_argument("--keys", help="逗号分隔的问题 key 过滤（先小样本）")
    parser.add_argument("--domains", help="逗号分隔的覆盖域过滤（decision-base 契约第 3 节）")
    parser.add_argument("--limit", type=int, help="最多取前 N 条问题请求")


def add_transport(parser):
    parser.add_argument("--workers", "--concurrency", dest="workers", type=int, default=4,
                        help="并发上限；--concurrency 是同一参数的别名（默认 4）")
    parser.add_argument("--rps", type=float, default=0.0, help="全局每秒请求上限，0 表示不限速")
    parser.add_argument("--timeout", type=float, default=120.0, help="单次 HTTP 超时秒数")
    parser.add_argument("--max-attempts", type=int, default=3, help="单请求最大尝试次数")
    parser.add_argument("--backoff", type=float, default=2.0, help="指数退避基数秒")
    parser.add_argument("--max-backoff", type=float, default=30.0, help="退避上限秒")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent")
    parser.add_argument("--price-in", type=float, help="每百万输入 token 价格（可选，用于成本统计）")
    parser.add_argument("--price-out", type=float, help="每百万输出 token 价格（可选）")
    parser.add_argument("--extra-header", action="append", default=[],
                        metavar="NAME=VALUE", help="附加请求头，可重复；会覆盖默认同名头")


def add_common_run(parser):
    parser.add_argument("--backend", choices=("jev", "openai-compatible", "fixture"), required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="真实联网调用（默认离线：只写请求计划）")
    mode.add_argument("--dry-run", action="store_true", help="显式离线：只写请求计划，不联网")
    parser.add_argument("--retry-failed", action="store_true",
                        help="重跑已记录为 timeout/error/invalid 的 qid（默认跳过）")
    parser.add_argument("--source", help="答案源名（默认 jev-<api-version> / fixture）")
    parser.add_argument("--source-version", help="固定版本（默认 api-version / 模型 id）")
    parser.add_argument("--calls", type=Path, help="调用日志（默认 <answers 目录>/calls.<source>.jsonl）")
    parser.add_argument("--journal", type=Path,
                        help="续跑日志（默认 <answers 目录>/journal.<source>.jsonl）")
    parser.add_argument("--requests-out", type=Path,
                        help="离线请求计划输出（默认 <answers 目录>/requests.<source>.jsonl）")
    parser.add_argument("--progress-every", type=int, default=20, help="每 N 个请求打一行进度到 stderr")
    parser.add_argument("--quiet", action="store_true", help="不打印进度行")
    parser.add_argument("--seed", type=int, default=20260930, help="fixture 确定性种子")
    parser.add_argument("--fixture-fail-rate", type=float, default=0.0,
                        help="fixture 注入失败的比例（仅测试用）")
    parser.add_argument("--key-env", help="密钥环境变量名（默认 jev=JEV_API_KEY / "
                                          "openai-compatible=ASK_API_KEY）")
    parser.add_argument("--key-file", type=Path, help="密钥文件（DSH credentials.yaml 的 refs 段或单值文件）")
    # jev
    parser.add_argument("--endpoint", help="[jev] 官方地址，可含完整路径")
    parser.add_argument("--api-version", help="[jev] 官方 api_version")
    parser.add_argument("--request-path", default="",
                        help="[jev] 追加到 endpoint 的路径；默认空=按 --endpoint 原样请求")
    parser.add_argument("--auth-scheme", choices=("bearer", "api-key", "none"), default="bearer",
                        help="[jev] 鉴权方式（默认 bearer）")
    parser.add_argument("--auth-header", default="X-API-Key", help="[jev] --auth-scheme api-key 的头名")
    parser.add_argument("--version-in", choices=("body", "header"), default="body",
                        help="[jev] api_version 放请求体还是请求头")
    parser.add_argument("--version-header", default="X-API-Version", help="[jev] 版本头名")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="[jev] 每次请求打包多少条问题（默认 1；官方支持数组时再调大）")
    parser.add_argument("--integration-confirmed", action="store_true",
                        help="[jev] 确认已按官方文档核对请求/响应形状（--live 必需）")
    # openai-compatible
    parser.add_argument("--base-url", help="[openai-compatible] 如 https://host/v1")
    parser.add_argument("--model", help="[openai-compatible] 模型 id")
    parser.add_argument("--chat-path", default="/chat/completions", help="[openai-compatible] 路径")
    parser.add_argument("--max-tokens", type=int, default=2048, help="[openai-compatible] 输出预算")
    parser.add_argument("--temperature", type=float, help="[openai-compatible] 采样温度")
    parser.add_argument("--response-format", choices=("json_object",),
                        help="[openai-compatible] 结构化输出（仅 json_object）")


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="离线把 items.jsonl 展平成请求清单（不联网）")
    plan.add_argument("--items", type=Path, required=True, help="items.jsonl（契约 2.1）")
    plan.add_argument("--out", type=Path, required=True, help="请求清单输出 JSONL")
    add_selection(plan)
    add_item_check(plan)

    run = sub.add_parser("run", help="批量作答（默认离线；--live 才联网）")
    run.add_argument("--items", type=Path, required=True, help="items.jsonl（契约 2.1）")
    run.add_argument("--out", type=Path, required=True,
                     help="answers.<source>.jsonl 的路径或所在目录")
    add_common_run(run)
    add_selection(run)
    add_item_check(run)
    add_transport(run)

    report = sub.add_parser("report", help="读 calls.jsonl 输出用量/成本/失败统计")
    report.add_argument("--calls", type=Path, required=True)
    report.add_argument("--answers", type=Path)
    report.add_argument("--items", type=Path)
    report.add_argument("--top", type=int, default=20)
    report.add_argument("--json", action="store_true")

    verify = sub.add_parser("verify", help="按契约 2.2 核对 answers 并给出覆盖缺口")
    verify.add_argument("--items", type=Path, required=True)
    verify.add_argument("--answers", type=Path, required=True)
    verify.add_argument("--allow-incomplete", action="store_true",
                        help="允许缺答/失败仍退出 0（默认不完整退出 1）")
    verify.add_argument("--top", type=int, default=20)
    verify.add_argument("--json", action="store_true")
    return parser


def main(argv=None, deps=None):
    deps = deps or Deps()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            return cmd_plan(args, deps)
        if args.command == "run":
            require(args.workers > 0, "--workers must be positive")
            require(args.progress_every >= 0, "--progress-every must be >= 0")
            return cmd_run(args, deps)
        if args.command == "report":
            return cmd_report(args, deps)
        if args.command == "verify":
            return cmd_verify(args, deps)
        raise ConfigError(f"unknown command {args.command!r}")
    except ConfigError as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 2
    except CallFailure as error:
        print(f"{TOOL}: {error.kind}: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
