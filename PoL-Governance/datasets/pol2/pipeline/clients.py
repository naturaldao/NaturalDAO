"""统一模型客户端：超时、重试与退避、并发上限、429/5xx、每次调用写 jsonl 成本日志。

外部接口（用户定稿矩阵，核实日期 2026-09-30，详见 pipeline/README.md「外部接口」）：
- 生成主：provider sub，POST https://sub.461561.xyz/v1/chat/completions，
  Bearer <SUB_API_KEY>，模型 gpt-6-luna（血缘 openai-luna）。
- 生成备：provider opencode-go，POST https://opencode.ai/zen/go/v1/chat/completions，
  Bearer <OPENCODE_GO_API_KEY> + x-opencode-session: <UUID>，模型 deepseek-v4.1-flash。
- 教师 A：provider sub，model gpt-6.1-sol，协议 openai-responses：
  POST https://sub.461561.xyz/v1/responses，body {"model","input","max_output_tokens"}，
  回复取 output[].content[].text（血缘 openai-sol）。
- 教师 B：provider sub-grok，model grok-4.7，同 responses 协议，Bearer <SUB_GROK_API_KEY>
  （血缘 xai-grok）。
- 教师 C：provider opencode-go，model mimo-v2.6-pro，chat completions + session 头
  （血缘 xiaomi-mimo）。
- 外部源 D：官方 Jev，见 jev.py（血缘 typesafe-jev）。

坑：mimo-v2.6-pro / glm-5.3 等会返回 reasoning_content，max_tokens 过小时 content 会是 null；
真值调用统一 max_tokens >= 1024，content 与 reasoning_content 皆空记 execution_status=invalid。

本模块不发起任何未经显式允许的调用：调用方负责 --live / --dry-run 的判定。
"""
from __future__ import annotations

import json
import random
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

from common import (append_jsonl, fingerprint, iso_now, load_secret, number, require,
                    sha256_text, text)

RETRY_STATUS = (408, 409, 425, 429, 500, 502, 503, 504)
# urllib 默认 UA（Python-urllib/3.x）会被 sub 网关的 Cloudflare 以 1010 拒绝，这里用产品名。
DEFAULT_USER_AGENT = "PoL2-pipeline/0.1 (+https://github.com/naturaldao/NaturalDAO)"
MAX_RESPONSE_BYTES = 2_000_000
PROCESS_SESSION_ID = str(uuid.uuid4())

SUB_BASE_URL = "https://sub.461561.xyz/v1"
OPENCODE_BASE_URL = "https://opencode.ai/zen/go/v1"
SUB_KEY_ENV = "SUB_API_KEY"
SUB_GROK_KEY_ENV = "SUB_GROK_API_KEY"
OPENCODE_KEY_ENV = "OPENCODE_GO_API_KEY"
# 真值/生成统一下限：短预算会被 reasoning 吃光，content 变空。
MIN_MAX_TOKENS = 1024
CHAT_PROTOCOL = "chat"
RESPONSES_PROTOCOL = "responses"
PROTOCOLS = (CHAT_PROTOCOL, RESPONSES_PROTOCOL)

SOURCE_LIST = (
    {"source": "luna", "provider": "sub", "lineage": "openai-luna", "protocol": CHAT_PROTOCOL,
     "base_url": SUB_BASE_URL, "model": "gpt-6-luna", "key_env": SUB_KEY_ENV, "max_tokens": 8192},
    {"source": "deepseek-v4.1-flash", "provider": "opencode-go", "lineage": "deepseek",
     "protocol": CHAT_PROTOCOL, "base_url": OPENCODE_BASE_URL, "model": "deepseek-v4.1-flash",
     "key_env": OPENCODE_KEY_ENV, "max_tokens": 4096},
    {"source": "gpt-6.1-sol", "provider": "sub", "lineage": "openai-sol",
     "protocol": RESPONSES_PROTOCOL, "base_url": SUB_BASE_URL, "model": "gpt-6.1-sol",
     "key_env": SUB_KEY_ENV, "max_tokens": 4096},
    {"source": "grok-4.7", "provider": "sub-grok", "lineage": "xai-grok",
     "protocol": RESPONSES_PROTOCOL, "base_url": SUB_BASE_URL, "model": "grok-4.7",
     "key_env": SUB_GROK_KEY_ENV, "max_tokens": 4096},
    {"source": "mimo-v2.6-pro", "provider": "opencode-go", "lineage": "xiaomi-mimo",
     "protocol": CHAT_PROTOCOL, "base_url": OPENCODE_BASE_URL, "model": "mimo-v2.6-pro",
     "key_env": OPENCODE_KEY_ENV, "max_tokens": 4096},
    {"source": "glm-5.3", "provider": "opencode-go", "lineage": "glm", "protocol": CHAT_PROTOCOL,
     "base_url": OPENCODE_BASE_URL, "model": "glm-5.3", "key_env": OPENCODE_KEY_ENV,
     "max_tokens": 4096},
    {"source": "glm-5.3-flash", "provider": "opencode-go", "lineage": "glm",
     "protocol": CHAT_PROTOCOL, "base_url": OPENCODE_BASE_URL, "model": "glm-5.3-flash",
     "key_env": OPENCODE_KEY_ENV, "max_tokens": 2048},
)
SOURCES = {item["source"]: {key: value for key, value in item.items() if key != "source"}
           for item in SOURCE_LIST}


class CallFailure(Exception):
    """kind is one of timeout / error / invalid, matching answer.execution_status."""

    def __init__(self, kind, message, status_code=None, attempts=1, retryable=None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.attempts = attempts
        self.retryable = retryable


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_endpoint(url):
    """HTTPS everywhere; plain HTTP only for literal loopback."""
    parsed = urlsplit(url)
    require(parsed.scheme in ("http", "https"), "endpoint must be http(s)")
    require(not parsed.username and not parsed.password, "endpoint must not embed credentials")
    require(not parsed.query and not parsed.fragment, "endpoint must not carry query/fragment")
    if parsed.scheme == "http":
        require(parsed.hostname in ("127.0.0.1", "::1", "localhost"),
                "plain HTTP is allowed only for loopback endpoints")
    _ = parsed.port
    return url


class CallLog:
    """Append-only jsonl cost log: one row per HTTP attempt."""

    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.rows = []
        self.lock = threading.Lock()

    def record(self, row):
        require(isinstance(row, dict), "log row must be an object")
        with self.lock:
            self.rows.append(row)
            if self.path is not None:
                append_jsonl(self.path, row)

    def summary(self):
        ok_rows = [row for row in self.rows if row.get("ok")]
        latencies = sorted(row["latency_ms"] for row in ok_rows if number(row.get("latency_ms")))
        totals = {"calls": len(self.rows), "ok": len(ok_rows), "failed": len(self.rows) - len(ok_rows),
                  "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in self.rows),
                  "completion_tokens": sum(row.get("completion_tokens") or 0 for row in self.rows),
                  "total_tokens": sum(row.get("total_tokens") or 0 for row in self.rows),
                  # 价格未知时写 null，不编造 0。
                  "cost_usd": (round(sum(row["cost_usd"] for row in self.rows
                                         if row.get("cost_usd") is not None), 6)
                               if any(row.get("cost_usd") is not None for row in self.rows)
                               else None)}
        if latencies:
            totals["latency_ms_p50"] = latencies[(len(latencies) - 1) // 2]
            totals["latency_ms_p95"] = latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))]
        kinds = {}
        for row in self.rows:
            if row.get("failure_kind"):
                kinds[row["failure_kind"]] = kinds.get(row["failure_kind"], 0) + 1
        totals["failed_by_kind"] = kinds
        totals["invalid_attempt_rate"] = (round(kinds.get("invalid", 0) / len(self.rows), 4)
                                          if self.rows else 0.0)
        return totals

    def print_summary(self, stream=None):
        import sys
        print(json.dumps({"call_log": str(self.path) if self.path else None,
                          **self.summary()}, ensure_ascii=False), file=stream or sys.stdout)


class ChatClient:
    """OpenAI-compatible chat completions client with retry, backoff and cost logging."""

    def __init__(self, provider, base_url, model, key, key_source, lineage,
                 protocol=CHAT_PROTOCOL, timeout=120.0, max_attempts=3, backoff=2.0,
                 max_backoff=30.0, backoff_jitter=0.25, max_tokens=2048, temperature=None,
                 headers=None, log=None, opener=None, sleeper=time.sleep, rng=None,
                 price_in=None, price_out=None, min_max_tokens=0, retry_invalid=False,
                 request_path=None, user_agent=DEFAULT_USER_AGENT, response_format=None):
        self.provider = provider
        self.base_url = validate_endpoint(base_url.rstrip("/"))
        self.model = model
        self.lineage = lineage
        self.key = key
        self.key_source = key_source
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff = backoff
        self.max_backoff = max_backoff
        self.backoff_jitter = backoff_jitter
        self.max_tokens_default = max_tokens
        self.min_max_tokens = min_max_tokens
        self.temperature = temperature
        self.headers = dict(headers or {})
        if user_agent:
            self.headers["User-Agent"] = user_agent
        self.log = log or CallLog()
        self.sleeper = sleeper
        self.rng = rng or random.Random(0)
        self.price_in = price_in
        self.price_out = price_out
        self.retry_invalid = retry_invalid
        require(protocol in PROTOCOLS, f"protocol must be one of {PROTOCOLS}")
        self.protocol = protocol
        if response_format and protocol != CHAT_PROTOCOL:
            raise ValueError("response_format 只在已核实的 chat completions 协议上启用；"
                             "responses 协议的形状未核实，不猜")
        self.response_format = response_format
        self.request_path = request_path or ("/chat/completions" if protocol == CHAT_PROTOCOL
                                             else "/responses")
        self.url = self.base_url + self.request_path
        self._opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())

    # ------------------------------------------------------------- payload
    def payload(self, messages, max_tokens=None):
        budget = max_tokens or self.max_tokens_default
        if self.min_max_tokens:
            budget = max(budget, self.min_max_tokens)
        require(isinstance(messages, list) and messages, "messages must be a non-empty list")
        if self.protocol == RESPONSES_PROTOCOL:
            body = {"model": self.model, "input": self._responses_input(messages),
                    "max_output_tokens": budget}
        else:
            body = {"model": self.model, "messages": messages, "max_tokens": budget}
            if self.response_format:
                body["response_format"] = {"type": self.response_format}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        return body

    @staticmethod
    def _responses_input(messages):
        parts = []
        for message in messages:
            content = message.get("content") if isinstance(message, dict) else None
            require(isinstance(content, str) and content.strip(), "message content must be text")
            parts.append(content)
        return parts[-1] if len(parts) == 1 else "\n\n".join(parts)

    def _headers(self):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        headers.update(self.headers)
        headers["Authorization"] = "Bearer " + self.key
        return headers

    # ------------------------------------------------------------- transport
    def _request(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.url, data=body, headers=self._headers(), method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                headers = dict(getattr(response, "headers", {}) or {})
            require(len(raw) <= MAX_RESPONSE_BYTES, "response too large")
            return status, headers, raw
        except urllib.error.HTTPError as error:
            raw = error.read(MAX_RESPONSE_BYTES + 1)
            return error.code, dict(error.headers or {}), raw
        except (TimeoutError, socket.timeout) as error:
            raise CallFailure("timeout", f"timeout: {error}") from error
        except urllib.error.URLError as error:
            kind = "timeout" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "error"
            raise CallFailure(kind, f"url error: {error.reason}") from error
        except OSError as error:
            raise CallFailure("error", f"os error: {error}") from error

    def _extract_text(self, body):
        if self.protocol == RESPONSES_PROTOCOL:
            output = body.get("output")
            require(isinstance(output, list), "responses payload has no output array")
            chunks = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                for part in item.get("content") or []:
                    is_text = isinstance(part, dict) and isinstance(part.get("text"), str)
                    if is_text and part["text"].strip():
                        chunks.append(part["text"])
            if chunks:
                return "\n".join(chunks)
            raise CallFailure("invalid", "empty responses output text "
                                         "(max_output_tokens likely too small)")
        choices = body.get("choices")
        require(isinstance(choices, list) and choices, "response has no choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        require(isinstance(message, dict), "response choice has no message")
        content = message.get("content")
        reasoning = message.get("reasoning_content")
        for value in (content, reasoning):
            if isinstance(value, str) and value.strip():
                return value
        raise CallFailure("invalid", "empty content and reasoning_content "
                                     "(max_tokens likely consumed by reasoning)")

    @staticmethod
    def _usage(body, price_in=None, price_out=None):
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
        completion = usage.get("completion_tokens", usage.get("output_tokens"))
        total = usage.get("total_tokens")
        prompt = prompt if number(prompt) else None
        completion = completion if number(completion) else None
        total = total if number(total) else ((prompt or 0) + (completion or 0) or None)
        cost = None
        if price_in is not None and price_out is not None and (prompt or completion):
            cost = ((prompt or 0) * price_in + (completion or 0) * price_out) / 1_000_000
        return {"prompt_tokens": prompt, "completion_tokens": completion,
                "total_tokens": total, "cost_usd": cost}

    def _log_attempt(self, digest, attempt, ok, status_code, latency_ms, error=None,
                     usage=None, dry_run=False, failure_kind=None):
        row = {"ts": iso_now(), "provider": self.provider, "model": self.model,
               "base_url": self.base_url, "attempt": attempt, "retries": attempt - 1, "ok": ok,
               "status_code": status_code, "latency_ms": round(latency_ms, 2),
               "error": error, "failure_kind": failure_kind,
               "request_sha256": digest, "key_fingerprint": fingerprint(self.key),
               "response_format": self.response_format, "dry_run": dry_run}
        row.update(usage or {"prompt_tokens": None, "completion_tokens": None,
                             "total_tokens": None, "cost_usd": None})
        self.log.record(row)
        return row

    # ------------------------------------------------------------- public API
    def chat(self, messages, max_tokens=None):
        payload = self.payload(messages, max_tokens)
        digest = sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        last_failure = None
        for attempt in range(1, self.max_attempts + 1):
            started = time.perf_counter()
            status_code = None
            try:
                status_code, headers, raw = self._request(payload)
                latency_ms = (time.perf_counter() - started) * 1000
                if status_code in RETRY_STATUS:
                    last_failure = CallFailure("error", f"HTTP {status_code}", status_code, attempt)
                    self._log_attempt(digest, attempt, False, status_code, latency_ms,
                                      error=f"HTTP {status_code}", failure_kind="error")
                elif status_code != 200:
                    raise CallFailure("error", f"HTTP {status_code}: {raw[:200]!r}",
                                      status_code, attempt, retryable=False)
                else:
                    try:
                        body = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as error:
                        raise CallFailure("invalid", f"bad JSON response: {error}") from error
                    text_value = self._extract_text(body)
                    usage = self._usage(body, self.price_in, self.price_out)
                    self._log_attempt(digest, attempt, True, status_code, latency_ms, usage=usage)
                    return {"text": text_value, "usage": usage, "latency_ms": latency_ms,
                            "attempts": attempt, "status_code": status_code,
                            "request_sha256": digest}
                delay = self._delay(attempt, headers.get("Retry-After"))
            except CallFailure as failure:
                latency_ms = (time.perf_counter() - started) * 1000
                last_failure = CallFailure(failure.kind, str(failure), failure.status_code, attempt,
                                           retryable=failure.retryable)
                retryable = (failure.kind in ("timeout", "error") if failure.retryable is None
                             else failure.retryable)
                self._log_attempt(digest, attempt, False, status_code, latency_ms,
                                  error=f"{failure.kind}: {failure}", failure_kind=failure.kind)
                if not (retryable or self.retry_invalid):
                    raise last_failure
                if attempt == self.max_attempts:
                    raise last_failure
                delay = self._delay(attempt, None)
            if attempt == self.max_attempts:
                raise last_failure
            if delay > 0:
                self.sleeper(delay)
        raise last_failure

    def _delay(self, attempt, retry_after=None):
        base = min(self.backoff * (2 ** (attempt - 1)), self.max_backoff)
        if retry_after:
            try:
                base = min(float(retry_after), self.max_backoff)
            except (TypeError, ValueError):
                pass
        return max(0.0, base + self.rng.uniform(0, self.backoff_jitter * base))


def source_lineage(source, overrides=None):
    """Lineage = 模型家族；同族一致不算独立交叉验证。"""
    overrides = dict(overrides or {})
    if source in overrides:
        return overrides[source]
    if source in SOURCES:
        return SOURCES[source]["lineage"]
    lowered = source.lower()
    if lowered.startswith("glm"):
        return "glm"
    if "luna" in lowered:
        return "openai-luna"
    if lowered.startswith("jev"):
        return "typesafe-jev"
    if lowered.startswith("fixture"):
        return "fixture"
    return source


def build_client(source, base_url=None, model=None, key_env=None, key_file=None, timeout=120.0,
                 max_attempts=3, log=None, max_tokens=None, workers=1, temperature=None,
                 session_id=None, price_in=None, price_out=None, retry_invalid=False,
                 min_max_tokens=None, api_key=None, user_agent=None, response_format=None):
    """Build a configured client for a known source name (luna / glm-5.3 / glm-5.3-flash)."""
    require(source in SOURCES, f"unknown source {source!r}; known: {sorted(SOURCES)}")
    config = SOURCES[source]
    env_name = key_env or config["key_env"]
    if api_key is None:
        key, key_source = load_secret([env_name], key_file=key_file if key_file else None,
                                      ref=env_name)
    else:
        key, key_source = api_key, "argument"
    require(bool(key.strip()), "empty API key")
    headers = {}
    if config["provider"] == "opencode-go":
        headers["x-opencode-session"] = session_id or PROCESS_SESSION_ID
    return ChatClient(provider=config["provider"], base_url=base_url or config["base_url"],
                      model=model or config["model"], key=key, key_source=key_source,
                      lineage=config["lineage"], protocol=config["protocol"], timeout=timeout,
                      max_attempts=max_attempts, max_tokens=max_tokens or config["max_tokens"],
                      temperature=temperature, headers=headers, log=log, price_in=price_in,
                      price_out=price_out, retry_invalid=retry_invalid,
                      user_agent=user_agent if user_agent is not None else DEFAULT_USER_AGENT,
                      response_format=response_format,
                      min_max_tokens=MIN_MAX_TOKENS if min_max_tokens is None
                      else (min_max_tokens or 0))


def run_ordered(items, worker, workers=1):
    """Run worker(item, index) with bounded concurrency; results keep input order.

    Exceptions are returned in place of results, never raised here.
    """
    items = list(items)
    require(workers >= 1, "workers must be >= 1")
    if workers == 1 or len(items) <= 1:
        results = []
        for index, item in enumerate(items):
            try:
                results.append(worker(item, index))
            except Exception as error:  # noqa: BLE001 - returned to caller as data
                results.append(error)
        return results
    results = [None] * len(items)

    def task(index_item):
        index, item = index_item
        try:
            results[index] = worker(item, index)
        except Exception as error:  # noqa: BLE001
            results[index] = error

    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        list(pool.map(task, list(enumerate(items))))
    return results
