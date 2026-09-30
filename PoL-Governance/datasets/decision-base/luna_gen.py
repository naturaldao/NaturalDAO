"""luna_gen.py —— 按 decision-base 覆盖域与问题键，让 Luna 生成 decision 条目（默认 dry-run）。

设计
----
* 键名权威是 datasets/decision-base/taxonomy.py（db-schema）：域、问题键、选项、量程、判据全部读它；
  它不可用时才退回本文件里的 README 级兜底表，并在 summary 里标 taxonomy_source。
* 默认 dry-run：只打印/写出**提示计划**（plan JSONL），绝不联网、绝不读密钥。
* --live 才真调，且 --limit 必填；超过 BULK_LIMIT 需要 LUNA_BULK_APPROVED=1（放量由 Lead 批准）。
* 密钥只从环境变量或 --key-file 读，日志里只写 sha256 指纹，绝不写密钥本体。
* token 用量、耗时、finish_reason、request_sha256 逐条落盘，供 luna_clean.py 与成本复盘使用。

实测路由（不要重新猜）
----------------------
* luna：POST https://sub.461561.xyz/v1/chat/completions，Bearer $SUB_API_KEY，
  model gpt-6-luna，支持 response_format={"type":"json_object"}。
* opencode-go（备用）：POST https://opencode.ai/zen/go/v1/chat/completions，
  Bearer $OPENCODE_GO_API_KEY + header x-opencode-session: <UUID>，model deepseek-v4.1-flash。

典型用法
--------
    # 1) 看提示（离线）
    uv run --no-project --offline python datasets/decision-base/luna_gen.py --dry-run --out-plan plan.jsonl
    # 2) 小样本真实生成（需 --limit；冒烟授权为 5 条）
    ... --live --limit 5 --raw-out raw.jsonl --calls-log calls.jsonl
    # 3) 清洗成契约条目
    uv run --no-project --offline python datasets/decision-base/luna_clean.py \
        --input raw.jsonl --items items.jsonl --rejects rejects.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0"
GENERATOR = "luna_gen.py"

DEFAULT_MAX_TOKENS = 4096
MIN_MAX_TOKENS_LIVE = 4096
BULK_LIMIT = 25
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
QUESTIONS_PER_ITEM = (3, 6)
USER_AGENT = "PoL-decision-base/0.1 (luna_gen.py; +https://github.com/naturaldao)"

ROUTES = {
    "luna": {
        "provider": "sub",
        "base_url": "https://sub.461561.xyz/v1",
        "model": "gpt-6-luna",
        "key_env": "SUB_API_KEY",
        "lineage": "openai-luna",
        "session_header": None,
    },
    "opencode-go": {
        "provider": "opencode-go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "model": "deepseek-v4.1-flash",
        "key_env": "OPENCODE_GO_API_KEY",
        "lineage": "deepseek",
        "session_header": "x-opencode-session",
    },
}
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

# README 第 3 节的六个覆盖域（taxonomy.py 不可用时的兜底）
FALLBACK_DOMAINS = (
    "decision_mechanics",
    "human_judgment",
    "social_moral",
    "risk_harm",
    "knowledge_reasoning",
    "pol2_axis",
)

NOUL_OPTIONS = ({"key": "yes", "label": "是"}, {"key": "no", "label": "否"})

# 兜底问题键：键名、原语、选项、量程与 taxonomy.py 对齐（只列已核对的键）。
FALLBACK_SPECS = {
    "action_selection": {"kind": "choice", "options": ["direct_answer", "use_tool",
                                                       "ask_clarification", "refuse", "defer"],
                         "criteria": "给定状态下的下一步动作类型：直接作答、调用工具、先澄清、拒绝或延后。"},
    "information_sufficient": {"kind": "noul", "criteria": "现有信息是否足以做出决定，而不必先澄清。"},
    "risk_of_action": {"kind": "score", "scale": {"min": 0, "max": 4,
                                                  "labels": ["无风险", "轻微", "中等", "高", "极高"]},
                       "criteria": "该动作产生未同意副作用的风险等级。"},
    "sentiment_polarity": {"kind": "choice", "options": ["positive", "negative", "mixed", "neutral"],
                           "criteria": "文本整体情感倾向，不构成行为性质判断。"},
    "toxicity_present": {"kind": "noul", "criteria": "文本是否含针对人或群体的敌意、侮辱或威胁。"},
    "judgment_basis": {"kind": "choice", "options": ["behavior", "wording", "context", "identity",
                                                     "unclear"],
                       "criteria": "判断主要依据行为事实、措辞语气、上下文还是身份标签。"},
    "prosocial_response_warranted": {"kind": "noul", "criteria": "是否应当给出亲社会回应而不是直接阻断。"},
    "norm_violation": {"kind": "noul", "criteria": "行为是否违反公认的社会规范。"},
    "power_asymmetry": {"kind": "noul", "criteria": "双方是否存在显著权力不对称。"},
    "contains_harm": {"kind": "noul", "criteria": "情境中是否包含对任何主体的伤害，无论是否蓄意。"},
    "harm_severity": {"kind": "score", "scale": {"min": 0, "max": 4,
                                                 "labels": ["无伤害", "轻微", "中等", "严重", "灾难性"]},
                      "criteria": "伤害严重程度 0-4，分级依据后果而非措辞强度。"},
    "harm_category": {"kind": "choice", "options": ["physical", "psychological", "sexual", "financial",
                                                    "privacy", "illegal", "self_harm", "cyber",
                                                    "ecological", "none", "other"],
                      "criteria": "伤害的主要类别；多项时取最严重的一项。"},
    "claim_supported": {"kind": "noul", "criteria": "陈述是否被给定上下文或既有事实支持。"},
    "evidence_sufficiency": {"kind": "choice", "options": ["sufficient", "insufficient", "contradictory"],
                             "criteria": "证据三值：充分 / 不足 / 冲突。"},
    "answer_uncertainty": {"kind": "score", "scale": {"min": 0, "max": 4,
                                                      "labels": ["确定", "较确定", "中等", "较不确定",
                                                                 "完全不确定"]},
                           "criteria": "答案的不确定程度 0-4（0 为确定）。"},
    "interaction_polarity": {"kind": "choice", "options": ["love", "hate", "neither", "unclear"],
                             "criteria": "本体 polarity 四值：爱 / 恨 / 非爱非恨（不在场）/ 无法定性。"},
    "policy_status": {"kind": "choice", "options": ["conforming", "violating", "insufficient"],
                      "criteria": "本体 status 三值：符合 / 违背 / 信息不足；信息不足不得当作恨。"},
}

FALLBACK_DOMAIN_KEYS = {
    "decision_mechanics": ("action_selection", "information_sufficient", "risk_of_action"),
    "human_judgment": ("sentiment_polarity", "toxicity_present", "judgment_basis"),
    "social_moral": ("prosocial_response_warranted", "norm_violation", "power_asymmetry"),
    "risk_harm": ("contains_harm", "harm_severity", "harm_category"),
    "knowledge_reasoning": ("claim_supported", "evidence_sufficiency", "answer_uncertainty"),
    "pol2_axis": ("interaction_polarity", "policy_status", "contains_harm",
                  "evidence_sufficiency"),
}

KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class Failure(Exception):
    """带退出码的命令行错误。"""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


class CallFailure(Exception):
    """一次模型调用的失败分类。"""

    def __init__(self, kind, message, status_code=None, attempts=None, retryable=None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.attempts = attempts
        self.retryable = retryable


# --------------------------------------------------------------------------- 工具

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(secret):
    if not secret:
        return None
    return sha256_text(str(secret))[:12]


def iso_now(created_at=None):
    return created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return re.sub(r"_{2,}", "_", slug)


# --------------------------------------------------------------------------- 分类法

@dataclass
class Taxonomy:
    """domain -> [spec]；spec = {key, kind, criteria, question?, options?|scale?, options_from_state?}"""

    domains: dict = field(default_factory=dict)
    source: str = "readme-fallback"

    def keys(self, domain):
        return [spec["key"] for spec in self.domains.get(domain, [])]


def _fallback_specs():
    domains = {}
    for domain, keys in FALLBACK_DOMAIN_KEYS.items():
        specs = []
        for key in keys:
            base = dict(FALLBACK_SPECS[key])
            base["key"] = key
            if base["kind"] == "choice":
                base["options"] = [{"key": option,
                                    "label": {"direct_answer": "直接作答", "use_tool": "调用工具",
                                              "ask_clarification": "先澄清", "refuse": "拒绝",
                                              "defer": "延后或转交"}.get(option, option)}
                                   for option in base["options"]]
            specs.append(base)
        domains[domain] = specs
    return domains


def fallback_taxonomy(reason="readme-fallback"):
    return Taxonomy(_fallback_specs(), source=reason)


def _spec_from_real_taxonomy(module, domain, keys, lang="zh"):
    specs = []
    for key in keys:
        try:
            spec = module.key_spec(key)
        except Exception:
            continue
        item = {"key": spec.key, "kind": spec.kind, "criteria": spec.criterion,
                "question": spec.prompt(lang),
                "options_from_state": bool(getattr(spec, "options_from_state", False))}
        if spec.kind == "choice" and not item["options_from_state"]:
            item["options"] = spec.option_pairs(lang)
        elif spec.kind == "score":
            item["scale"] = spec.score_scale(lang)
        specs.append(item)
    return specs


def _spec_from_generic(entry):
    """把第三方形状（str / dict）的问题键定义归一成内部 spec。"""
    if isinstance(entry, str):
        key = entry.strip()
        if not KEY_RE.match(key):
            return None
        base = dict(FALLBACK_SPECS.get(key, {"kind": "noul", "criteria": ""}))
        base["key"] = key
        if base["kind"] == "choice" and base.get("options"):
            base["options"] = [{"key": option, "label": option} for option in base["options"]]
        return base
    if not isinstance(entry, dict):
        return None
    key = entry.get("key") or entry.get("name") or entry.get("id")
    if not isinstance(key, str) or not KEY_RE.match(key.strip()):
        return None
    key = key.strip()
    base = dict(FALLBACK_SPECS.get(key, {}))
    kind = entry.get("kind") or entry.get("primitive") or entry.get("type") or base.get("kind")
    if kind not in ("noul", "choice", "score"):
        kind = base.get("kind", "noul")
    spec = {"key": key, "kind": kind,
            "criteria": str(entry.get("criteria") or entry.get("description")
                            or base.get("criteria") or "").strip(),
            "question": str(entry.get("prompt") or entry.get("question") or "").strip()}
    if kind == "noul":
        spec["options"] = [dict(option) for option in NOUL_OPTIONS]
    elif kind == "choice":
        raw = entry.get("options") if isinstance(entry.get("options"), list) else base.get("options")
        if not raw:
            return None
        options = []
        for option in raw:
            if isinstance(option, dict):
                okey = option.get("key") or option.get("id") or option.get("value")
                label = option.get("label") or option.get("text") or okey
            else:
                okey = label = option
            if not isinstance(okey, str) or not okey.strip():
                return None
            okey = okey.strip() if KEY_RE.match(okey.strip()) else slugify(okey)
            if not okey:
                return None
            options.append({"key": okey, "label": str(label).strip() or okey})
        spec["options"] = options
    else:
        raw = entry.get("scale") if isinstance(entry.get("scale"), dict) else entry
        if isinstance(raw, dict) and isinstance(raw.get("min"), int) and isinstance(raw.get("max"), int) \
                and raw["min"] < raw["max"]:
            labels = raw.get("labels") or raw.get("levels")
            if not isinstance(labels, list) or len(labels) != raw["max"] - raw["min"] + 1:
                labels = [str(value) for value in range(raw["min"], raw["max"] + 1)]
            spec["scale"] = {"min": raw["min"], "max": raw["max"],
                             "labels": [str(item) for item in labels]}
        elif base.get("scale"):
            spec["scale"] = dict(base["scale"])
        else:
            return None
    return spec


def _taxonomy_from_module(module, lang="zh"):
    domains = {}
    if hasattr(module, "DOMAINS") and hasattr(module, "key_spec"):
        core = getattr(module, "CORE_KEYS", {}) or {}
        allkeys = getattr(module, "DOMAIN_KEYS", {}) or {}
        for domain in module.DOMAINS:
            keys = list(core.get(domain) or allkeys.get(domain) or ())
            specs = _spec_from_real_taxonomy(module, domain, keys, lang)
            if specs:
                domains[str(domain)] = specs
        if domains:
            return domains, getattr(module, "CORE_KEYS", {}) or {}
    raw = None
    for name in ("TAXONOMY", "DOMAINS", "DOMAIN_SPECS", "COVERAGE_DOMAINS"):
        value = getattr(module, name, None)
        if isinstance(value, dict) and value:
            raw = value
            break
    if raw:
        for domain, entry in raw.items():
            if isinstance(entry, dict):
                entries = (entry.get("questions") or entry.get("keys") or entry.get("question_keys")
                           or entry.get("specs"))
            else:
                entries = entry
            if isinstance(entries, dict):
                entries = list(entries.values())
            if isinstance(entries, (list, tuple)):
                specs = [spec for spec in (_spec_from_generic(item) for item in entries) if spec]
                if specs:
                    domains[str(domain)] = specs
    if not domains:
        questions = None
        for name in ("QUESTIONS", "QUESTION_KEYS", "QUESTION_SPECS"):
            value = getattr(module, name, None)
            if isinstance(value, dict) and value:
                questions = value
                break
        if questions and all(isinstance(value, (list, tuple)) for value in questions.values()):
            for domain, entries in questions.items():
                specs = [spec for spec in (_spec_from_generic(item) for item in entries) if spec]
                if specs:
                    domains[str(domain)] = specs
    return domains, {}


def load_taxonomy(path=None, lang="zh"):
    """读 taxonomy.py；不可用（缺失/半写/形状不可识别）时退回兜底表并说明原因。"""
    path = Path(path) if path else Path(__file__).with_name("taxonomy.py")
    if not path.is_file():
        return fallback_taxonomy("readme-fallback(taxonomy.py missing)")
    try:
        module = load_module(path)
        domains, _core = _taxonomy_from_module(module, lang)
    except Exception as error:
        return fallback_taxonomy(f"readme-fallback(taxonomy.py unreadable: {error})")
    if not domains:
        return fallback_taxonomy("readme-fallback(taxonomy.py has no recognizable domains)")
    return Taxonomy(domains, source="taxonomy.py")


def load_module(path, name="decision_base_taxonomy"):
    """按路径加载模块；必须先进 sys.modules（taxonomy.py 用了 @dataclass）。"""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Failure(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


# --------------------------------------------------------------------------- 提示

PROMPT_HEADER = """你是治理决策数据生成器（decision-base v0.1）。请针对覆盖域「{domain}」生成 {items} 个待判断情境与类型化问题，并给出你自己的判断。

硬性要求（违反任何一条该条目作废）：
1. 只输出一个 JSON 对象，不要 markdown 围栏，不要解释文字。顶层结构必须是 {{"items": [ ... ]}}。
2. 每个 item 的结构：
   {{"state": "情境文本", "lang": "{lang}", "questions": [ ... ], "targets": {{ ... }}}}
3. state 只描述情境与关系，60–200 字；不写结论，不写「这是违规/这很善良」之类提示，不出现答案。
4. questions 从下面列出的问题键里选 {low}–{high} 个相互正交的键，不得发明新键，每个键最多出现一次；
   同一个问题键在不同 item 之间尽量错开，覆盖正常、违规、信息不足三类情境。
5. noul 的 options 固定为 [{{"key":"yes","label":"是"}},{{"key":"no","label":"否"}}]（英文语境用 Yes/No）。
6. choice 的 options 必须与下面该键列出的取值完全一致（key 与 label 都要给全，顺序不限）。
7. score 的 scale 是 {{"min":<整数>,"max":<整数>,"labels":[<逐级标签>]}}，labels 个数必须等于 max-min+1，
   量程与下面列出的完全一致。
8. targets 里每个问题给 {{"answer": <合法取值>, "probs": {{<选项key>: <概率>}}}}：
   probs 之和必须等于 1；不确定就给真实分布，禁止把单标签伪装成概率；没有依据时不要编造极端概率。
9. 语言：{lang_hint}
10. 情境要彼此不同，避免同一情节的翻译或改写。

覆盖域「{domain}」可用的问题键（共 {count} 个）：
{questions}
"""


def describe_spec(spec):
    kind = spec["kind"]
    if kind == "noul":
        values = "yes|no"
    elif kind == "choice":
        options = spec.get("options") or []
        values = ("|".join(option["key"] for option in options) if options
                  else "2–16 个候选，由该 item 的 state 自带（每个候选给 key 与 label）")
    else:
        scale = spec.get("scale") or {}
        labels = "/".join(scale.get("labels", []))
        values = f"{scale.get('min')}..{scale.get('max')}" + (f"（{labels}）" if labels else "")
    text = spec.get("question") or ""
    criteria = spec.get("criteria") or ""
    tail = f"判据：{criteria}" if criteria else ""
    return f"  - {spec['key']} ({kind})：取值 {values}。{text} {tail}".rstrip()


def build_prompt(domain, specs, lang="zh", items=2):
    lang_hint = "全部文字使用简体中文。" if lang.startswith("zh") else f"全部文字使用 {lang}。"
    low, high = QUESTIONS_PER_ITEM
    return PROMPT_HEADER.format(domain=domain, items=items, lang=lang, lang_hint=lang_hint,
                                low=low, high=high, count=len(specs),
                                questions="\n".join(describe_spec(spec) for spec in specs))


def build_plan(taxonomy, domains=None, samples=1, items_per_call=2, lang="zh", created_at=None):
    """确定性生成请求计划（同参数必得同计划）。"""
    chosen = list(domains) if domains else sorted(taxonomy.domains)
    plan = []
    for domain in chosen:
        specs = taxonomy.domains.get(domain)
        if not specs:
            raise Failure(f"覆盖域 {domain!r} 没有可用的问题键；可用：{sorted(taxonomy.domains)}")
        for index in range(samples):
            plan.append({
                "id": f"luna-{domain}-{index:04d}",
                "domain": domain,
                "lang": lang,
                "items": items_per_call,
                "keys": [spec["key"] for spec in specs],
                "prompt": build_prompt(domain, specs, lang, items_per_call),
                "generator": GENERATOR,
                "generator_version": VERSION,
                "created_at": iso_now(created_at),
            })
    return plan


# --------------------------------------------------------------------------- 客户端

def load_key(key_env=None, key_file=None):
    """只从环境变量或 --key-file 读密钥；绝不落盘、绝不打印。"""
    if key_file:
        path = Path(key_file)
        if not path.is_file():
            raise Failure(f"密钥文件不存在：{key_file}")
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        key = lines[0].strip() if lines else ""
        if not key:
            raise Failure(f"密钥文件为空：{key_file}")
        return key
    env_name = key_env or ROUTES["luna"]["key_env"]
    key = (os.environ.get(env_name) or "").strip()
    if not key:
        raise Failure(f"环境变量 {env_name} 没有密钥（也可用 --key-file）")
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """不跟随重定向：避免把 Bearer 头带到别的域名。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        return None


class LunaClient:
    """OpenAI 兼容 chat completions 客户端：重试、退避、用量与耗时记录。"""

    def __init__(self, route="luna", model=None, api_key=None, timeout=180.0,
                 max_tokens=DEFAULT_MAX_TOKENS, response_format="json_object",
                 max_attempts=3, backoff=2.0, session_id=None, opener=None,
                 sleeper=time.sleep, user_agent=USER_AGENT):
        if route not in ROUTES:
            raise Failure(f"未知路由 {route!r}；可用：{sorted(ROUTES)}")
        self.route_name = route
        self.route = ROUTES[route]
        self.model = model or self.route["model"]
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max(max_tokens, 1)
        self.response_format = None if response_format in (None, "none") else response_format
        self.max_attempts = max(1, max_attempts)
        self.backoff = backoff
        self.session_id = session_id or str(uuid.uuid4())
        self.sleeper = sleeper
        self.url = self.route["base_url"].rstrip("/") + "/chat/completions"
        self.headers = {"Content-Type": "application/json", "Accept": "application/json",
                        "User-Agent": user_agent}
        if self.route.get("session_header"):
            self.headers[self.route["session_header"]] = self.session_id
        self._opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())

    def payload(self, messages, max_tokens=None):
        body = {"model": self.model, "messages": messages,
                "max_tokens": max_tokens or self.max_tokens}
        if self.response_format:
            body["response_format"] = {"type": self.response_format}
        return body

    def headers_for(self):
        headers = dict(self.headers)
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        return headers

    def _request(self, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.url, data=data, headers=self.headers_for(),
                                         method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                headers = dict(getattr(response, "headers", {}) or {})
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            return status, headers, raw
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers or {}), error.read(MAX_RESPONSE_BYTES + 1)
        except (TimeoutError, socket.timeout) as error:
            raise CallFailure("timeout", f"timeout: {error}") from error
        except urllib.error.URLError as error:
            kind = "timeout" if isinstance(error.reason, (TimeoutError, socket.timeout)) else "error"
            raise CallFailure(kind, f"url error: {error.reason}") from error
        except OSError as error:
            raise CallFailure("error", f"os error: {error}") from error

    @staticmethod
    def extract_text(body):
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise CallFailure("invalid", "响应里没有 choices")
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        for value in (message.get("content"), message.get("reasoning_content")):
            if isinstance(value, str) and value.strip():
                return value, choice.get("finish_reason")
        raise CallFailure("invalid", "content 与 reasoning_content 都为空（max_tokens 可能被推理吃光）")

    @staticmethod
    def extract_usage(body):
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
        completion = usage.get("completion_tokens", usage.get("output_tokens"))
        prompt = prompt if isinstance(prompt, (int, float)) else None
        completion = completion if isinstance(completion, (int, float)) else None
        total = usage.get("total_tokens")
        if not isinstance(total, (int, float)):
            total = (prompt or 0) + (completion or 0) or None
        return {"prompt_tokens": prompt, "completion_tokens": completion,
                "total_tokens": total, "cost_usd": None}

    def _delay(self, attempt, retry_after=None):
        delay = min(self.backoff ** attempt, 30.0)
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except (TypeError, ValueError):
                pass
        return delay

    def complete(self, prompt, request_id=None, max_tokens=None):
        payload = self.payload([{"role": "user", "content": prompt}], max_tokens)
        digest = sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1
            started = time.perf_counter()
            status, headers, raw = self._request(payload)
            latency_ms = (time.perf_counter() - started) * 1000
            if status in RETRY_STATUS and attempts < self.max_attempts:
                self.sleeper(self._delay(attempts, headers.get("Retry-After")))
                continue
            if status != 200:
                raise CallFailure("error", f"HTTP {status}: {raw[:200]!r}", status, attempts, False)
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise CallFailure("invalid", f"响应不是 JSON：{error}", status, attempts) from error
            text, finish_reason = self.extract_text(body)
            return {"text": text, "finish_reason": finish_reason, "usage": self.extract_usage(body),
                    "latency_ms": round(latency_ms, 2), "attempts": attempts, "status_code": status,
                    "request_sha256": digest, "model": self.model, "route": self.route_name}
        raise CallFailure("error", f"重试 {self.max_attempts} 次仍失败", None, attempts, False)


class FixtureClient:
    """离线的假客户端：按 id 或顺序回放预先录好的响应。"""

    def __init__(self, path=None, rows=None, latency_ms=0.0):
        records = list(rows or [])
        if path:
            records.extend(json.loads(line) for line in
                           Path(path).read_text(encoding="utf-8").splitlines() if line.strip())
        self.by_id = {}
        self.queue = []
        for record in records:
            if isinstance(record, str):
                self.queue.append({"response": record})
                continue
            if "id" in record and "response" in record:
                self.by_id[str(record["id"])] = record
            else:
                self.queue.append(record)
        self.latency_ms = latency_ms
        self.calls = 0

    def complete(self, prompt, request_id=None, max_tokens=None):
        self.calls += 1
        record = self.by_id.get(str(request_id)) if request_id is not None else None
        if record is None and self.queue:
            record = self.queue.pop(0)
        if record is None:
            raise CallFailure("invalid", f"fixture 没有 id={request_id!r} 的响应")
        return {"text": record.get("response", ""),
                "finish_reason": record.get("finish_reason", "stop"),
                "usage": record.get("usage") or {"prompt_tokens": None, "completion_tokens": None,
                                                 "total_tokens": None, "cost_usd": None},
                "latency_ms": record.get("latency_ms", self.latency_ms), "attempts": 1,
                "status_code": 200, "request_sha256": sha256_text(prompt),
                "model": record.get("model", "fixture"), "route": "fixture", "fixture": True}


# --------------------------------------------------------------------------- 落盘

def write_jsonl(path, rows):
    target = Path(path)
    if str(target.parent):
        target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def raw_row(plan_row, result, created_at=None):
    return {
        "id": plan_row["id"],
        "domain": plan_row["domain"],
        "lang": plan_row["lang"],
        "keys": plan_row["keys"],
        "prompt": plan_row["prompt"],
        "response": result.get("text"),
        "finish_reason": result.get("finish_reason"),
        "usage": result.get("usage"),
        "latency_ms": result.get("latency_ms"),
        "attempts": result.get("attempts"),
        "model": result.get("model"),
        "route": result.get("route"),
        "route_url": ROUTES.get(result.get("route"), {}).get("base_url"),
        "request_sha256": result.get("request_sha256"),
        "created_at": iso_now(created_at),
    }


# --------------------------------------------------------------------------- CLI

def build_parser():
    parser = argparse.ArgumentParser(description="按覆盖域让 Luna 生成 decision 条目（默认 dry-run）")
    parser.add_argument("--domains", default=None, help="逗号分隔的覆盖域；默认全部")
    parser.add_argument("--list-domains", action="store_true", help="打印可用覆盖域与问题键")
    parser.add_argument("--key-set", default="core", choices=("core", "all"),
                        help="core=每域最小问题集（taxonomy.CORE_KEYS，默认）；all=每域全部键")
    parser.add_argument("--samples", type=int, default=1, help="每个覆盖域生成多少个请求")
    parser.add_argument("--items-per-call", type=int, default=2, help="每次请求要几个 item")
    parser.add_argument("--lang", default="zh")
    parser.add_argument("--dry-run", action="store_true", help="只产计划（默认行为）")
    parser.add_argument("--live", action="store_true", help="真实调用；必须同时给 --limit")
    parser.add_argument("--limit", type=int, default=None, help="真实调用的最大条数")
    parser.add_argument("--out-plan", default=None, help="计划 JSONL（dry-run；默认写 stdout）")
    parser.add_argument("--raw-out", default=None, help="原始响应 JSONL（live）")
    parser.add_argument("--calls-log", default=None, help="调用日志 JSONL（含用量/耗时/密钥指纹）")
    parser.add_argument("--fixture", default=None, help="离线回放：{id,response} JSONL（不联网）")
    parser.add_argument("--route", default="luna", choices=tuple(ROUTES))
    parser.add_argument("--model", default=None)
    parser.add_argument("--key-env", default=None)
    parser.add_argument("--key-file", default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--response-format", default="json_object", choices=("json_object", "none"))
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--created-at", default=None)
    parser.add_argument("--json", action="store_true", help="只打印机器可读汇总")
    return parser


def _select_taxonomy(args):
    taxonomy = load_taxonomy(lang=args.lang)
    if args.key_set == "all":
        path = Path(__file__).with_name("taxonomy.py")
        if taxonomy.source == "taxonomy.py" and path.is_file():
            module = load_module(path)
            allkeys = getattr(module, "DOMAIN_KEYS", {}) or {}
            domains = {}
            for domain in module.DOMAINS:
                specs = _spec_from_real_taxonomy(module, domain, list(allkeys.get(domain) or ()),
                                                 args.lang)
                if specs:
                    domains[str(domain)] = specs
            if domains:
                taxonomy = Taxonomy(domains, source="taxonomy.py(all-keys)")
    return taxonomy


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    taxonomy = _select_taxonomy(args)
    if args.list_domains:
        print(json.dumps({"source": taxonomy.source, "domains": sorted(taxonomy.domains),
                          "questions": {domain: [spec["key"] for spec in specs]
                                        for domain, specs in sorted(taxonomy.domains.items())}},
                         ensure_ascii=False))
        return 0
    domains = ([item.strip() for item in args.domains.split(",") if item.strip()]
               if args.domains else None)
    if domains:
        unknown = [domain for domain in domains if domain not in taxonomy.domains]
        if unknown:
            parser.error(f"未知覆盖域 {unknown}；可用：{sorted(taxonomy.domains)}")
    if args.samples < 1 or args.items_per_call < 1:
        parser.error("--samples 与 --items-per-call 必须 >= 1")
    plan = build_plan(taxonomy, domains=domains, samples=args.samples,
                      items_per_call=args.items_per_call, lang=args.lang,
                      created_at=args.created_at)
    if not args.live:
        if args.out_plan:
            write_jsonl(args.out_plan, plan)
        else:
            for row in plan:
                print(json.dumps(row, ensure_ascii=False))
        if args.json or args.out_plan:
            print(json.dumps({"mode": "dry-run", "plan": len(plan), "out_plan": args.out_plan,
                              "taxonomy_source": taxonomy.source, "key_set": args.key_set,
                              "domains": sorted(taxonomy.domains)}, ensure_ascii=False))
        return 0
    # ------------------------------------------------------------------ live
    if args.limit is None:
        parser.error("--live 必须同时给 --limit（真实付费调用，放量需 Lead 批准）")
    if args.limit < 1:
        parser.error("--limit 必须 >= 1")
    if args.limit > BULK_LIMIT and os.environ.get("LUNA_BULK_APPROVED") != "1":
        parser.error(f"--limit {args.limit} 超过 {BULK_LIMIT}，需要 LUNA_BULK_APPROVED=1"
                     "（放量由 Lead 批准）")
    if args.max_tokens < MIN_MAX_TOKENS_LIVE:
        parser.error(f"--live 时 --max-tokens 必须 >= {MIN_MAX_TOKENS_LIVE}（避免 JSON 被截断）")
    if not args.raw_out:
        parser.error("--live 需要 --raw-out")
    todo = plan[:args.limit]
    if args.fixture:
        client = FixtureClient(path=args.fixture)
    else:
        try:
            key = load_key(args.key_env or ROUTES[args.route]["key_env"], args.key_file)
        except Failure as error:
            parser.error(str(error))
        client = LunaClient(route=args.route, model=args.model, api_key=key, timeout=args.timeout,
                            max_tokens=args.max_tokens, response_format=args.response_format,
                            max_attempts=args.max_attempts)
    rows, calls, failures = [], [], []
    for plan_row in todo:
        started = time.perf_counter()
        try:
            result = client.complete(plan_row["prompt"], request_id=plan_row["id"])
            rows.append(raw_row(plan_row, result, args.created_at))
            calls.append({"ts": iso_now(), "id": plan_row["id"], "model": result.get("model"),
                          "route": result.get("route"), "ok": True,
                          "latency_ms": result.get("latency_ms"), "attempts": result.get("attempts"),
                          "status_code": result.get("status_code"),
                          "request_sha256": result.get("request_sha256"),
                          "key_fingerprint": fingerprint(getattr(client, "api_key", None)),
                          "usage": result.get("usage")})
        except CallFailure as error:
            failures.append({"id": plan_row["id"], "kind": error.kind, "message": str(error)})
            rows.append({"id": plan_row["id"], "domain": plan_row["domain"], "lang": plan_row["lang"],
                         "keys": plan_row["keys"], "prompt": plan_row["prompt"], "response": None,
                         "error": {"kind": error.kind, "message": str(error)[:500]},
                         "usage": None,
                         "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                         "attempts": error.attempts, "model": getattr(client, "model", None),
                         "route": args.route, "request_sha256": None,
                         "created_at": iso_now(args.created_at)})
            calls.append({"ts": iso_now(), "id": plan_row["id"], "route": args.route, "ok": False,
                          "failure_kind": error.kind, "message": str(error)[:500],
                          "key_fingerprint": fingerprint(getattr(client, "api_key", None))})
    write_jsonl(args.raw_out, rows)
    if args.calls_log:
        write_jsonl(args.calls_log, calls)
    prompt_tokens = sum(row["usage"]["prompt_tokens"] or 0 for row in rows
                        if isinstance(row.get("usage"), dict))
    completion_tokens = sum(row["usage"]["completion_tokens"] or 0 for row in rows
                            if isinstance(row.get("usage"), dict))
    latencies = [row["latency_ms"] for row in rows if isinstance(row.get("latency_ms"), (int, float))]
    summary = {"mode": "live", "plan": len(plan), "calls": len(rows), "ok": len(rows) - len(failures),
               "failed": len(failures), "prompt_tokens": prompt_tokens,
               "completion_tokens": completion_tokens,
               "total_tokens": prompt_tokens + completion_tokens,
               "latency_ms_total": round(sum(latencies), 2) if latencies else None,
               "latency_ms_max": max(latencies) if latencies else None,
               "raw_out": args.raw_out, "calls_log": args.calls_log,
               "model": getattr(client, "model", None), "route": args.route,
               "taxonomy_source": taxonomy.source, "failures": failures}
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
