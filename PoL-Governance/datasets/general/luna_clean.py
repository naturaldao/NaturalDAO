"""luna_clean.py —— 把 Luna（自回归教师）的自由文本/半结构化输出清洗成 decision-base 契约条目。

职责边界
--------
* 只做「提取 + 字段级校验 + 归一 + 隔离」，默认不联网；只有显式 --live 才会为重生成调用模型。
* **不得静默丢弃**：每条输入行必须落到 items 或 rejects 之一；统计里的 rows_without_output
  必须为 0，否则进程以非零码退出。
* 契约与键名的权威是 datasets/general/taxonomy.py（db-schema）；它存在时：
  - 问题键解析别名（interaction_type→interaction_polarity 等）并取规范 options/scale/prompt；
  - 答案用 taxonomy.normalize_answer 归一、taxonomy.validate_target 校验；
  - 最后整条跑 taxonomy.item_errors 兜底。
  taxonomy.py 不可读时退回 README 级结构校验（summary 里标 domain_source）。

输入（JSONL，一行一条）
----------------------
    {"id": "...", "domain": "risk_harm", "response": "<模型原文>",
     "state": "可选（提示里已固定情境时）", "lang": "可选",
     "prompt": "可选，生成用提示（--live 补生成或 --repair 回灌用）",
     "finish_reason": "可选，length 表示被截断", "model": "可选"}

也可以直接喂 luna_gen.py --dry-run 的产出（只有 prompt、没有 response）：
不带 --live 时会明确拒绝（reason_code=missing_response），不会跳过。

输出
----
* items.jsonl —— 契约 2.1 节条目；id 由 (source, revision, row) 确定性派生为 db-luna-<8hex>。
* rejects.jsonl —— 每行 {id, input_id, line, severity, stage, reason_code, reason, errors[],
  response_excerpt}。severity=reject 表示该条没进 items；severity=warning 表示条目已入库、
  但其中某个 targets 被丢弃（按 db-schema 的规矩：宁可不写 targets，也不写非法答案）。
* stdout —— 一行 JSON 统计（含 rejects_by_code / warnings_by_code / flags 直方图）。

容错策略（哪类「修」，哪类「拒」）
--------------------------------
* 表示层问题就地归一并在 meta.quality_flags 留痕：
  bool→yes/no、label→option key、别名值→规范值、数字字符串→整数、scale.labels 缺失→默认标签、
  probs 之和≤0.02 偏差→重归一、问题键别名→规范键、options/scale/prompt 与 taxonomy 不一致→用 taxonomy 的。
* 结构/语义非法整条拒收（可配 --repair 重生成）：
  kind 非法或与 taxonomy 不符、noul 选项不是 yes/no、choice 选项数越界或 key 重复、
  score 的 min>=max 或 labels 数量不匹配、state/domain/lang 缺失、未知问题键。
* targets 层默认只告警不拒收（--strict-targets 可改为拒收）：非法答案/非法 probs 丢弃该 target。

用法
----
    uv run --no-project --offline python datasets/general/luna_clean.py \
        --input raw.jsonl --items items.jsonl --rejects rejects.jsonl
    # 离线重生成路径（fixture 回放，不联网）
    ... --repair 1 --repair-fixture repairs.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0"
SOURCE_SLUG = "luna"
CONVERTER = "luna_clean.py"

DEFAULT_DATASET = "luna-synth"
DEFAULT_LICENSE = "unknown-teacher-terms"
DEFAULT_SPLIT = "train"
DEFAULT_LANG = "zh"
DEFAULT_TEACHER = "gpt-6-luna"
DEFAULT_URL = "https://sub.461561.xyz/v1/chat/completions"

KINDS = ("noul", "choice", "score")
NOUL_KEYS = ("yes", "no")
MAX_QUESTIONS = 12
MAX_ITEMS_PER_RESPONSE = 8
MAX_RESPONSE_CHARS = 1_000_000
MAX_CHOICE_OPTIONS = 16
MIN_CHOICE_OPTIONS = 2
MAX_REPAIRS = 3
MAX_WARNINGS_PER_ITEM = 6
PROBS_SUM_TOL = 0.02
LIVE_CALL_CAP = 25  # 超过需要 LUNA_BULK_APPROVED=1（放量由 Lead 批准）

KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
LANG_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")

# README 第 3 节的六个覆盖域；taxonomy.py 存在时以它为准。
FALLBACK_DOMAINS = (
    "decision_mechanics",
    "human_judgment",
    "social_moral",
    "risk_harm",
    "knowledge_reasoning",
    "pol2_axis",
)

SOURCE_KEYS = ("dataset", "revision", "config", "split", "row", "license", "url")


# --------------------------------------------------------------------------- 账本

class Failure(Exception):
    """带退出码的命令行错误。"""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


@dataclass
class Problem:
    """一条校验失败；stage 说明在哪一层失败。"""

    item_id: str
    stage: str
    code: str
    message: str
    path: str = ""

    def as_dict(self):
        row = {"code": self.code, "stage": self.stage, "message": self.message}
        if self.path:
            row["path"] = self.path
        return row


@dataclass
class Options:
    """清洗参数；测试可直接构造。"""

    default_domain: str | None = None
    default_lang: str = DEFAULT_LANG
    split: str = DEFAULT_SPLIT
    dataset: str = DEFAULT_DATASET
    revision: str = ""
    license: str = DEFAULT_LICENSE  # 契约字段名
    url: str = DEFAULT_URL
    created_at: str | None = None
    teacher_model: str = DEFAULT_TEACHER
    salvage_truncated: bool = False
    allow_targets: bool = True
    max_repairs: int = 0
    taxonomy_check: bool = True
    strict_targets: bool = False

    def timestamp(self):
        if self.created_at:
            return self.created_at
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class CleanResult:
    items: list = field(default_factory=list)
    rejects: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- 提取

def scan_json(text):
    """扫描第一个平衡的 JSON 片段（容忍前后解说与 markdown 围栏）。

    返回 dict：start / end（end=None 表示未闭合）/ mismatch / stack / in_string。
    """
    start = None
    for index, char in enumerate(text):
        if char in "{[":
            start = index
            break
    if start is None:
        return {"start": None, "end": None, "mismatch": False, "stack": [], "in_string": False}
    stack = []
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
        elif char in "{[":
            stack.append(char)
        elif char in "}]":
            expected = "{" if char == "}" else "["
            if stack and stack[-1] == expected:
                stack.pop()
                if not stack:
                    return {"start": start, "end": index + 1, "mismatch": False,
                            "stack": [], "in_string": False}
            else:
                return {"start": start, "end": None, "mismatch": True,
                        "stack": list(stack), "in_string": in_string}
    return {"start": start, "end": None, "mismatch": False,
            "stack": list(stack), "in_string": in_string}


def extract_json(text):
    """提取并解析第一个平衡的 JSON 片段；失败抛 Failure。"""
    diagnostic = scan_json(text)
    if diagnostic["start"] is None:
        raise Failure("no_json_found: 输出里找不到 '{' 或 '['", code=3)
    if diagnostic["mismatch"]:
        raise Failure("unbalanced_json: 括号不匹配", code=3)
    if diagnostic["end"] is None:
        raise Failure("unterminated_json: JSON 片段未闭合", code=3)
    fragment = text[diagnostic["start"]:diagnostic["end"]]
    try:
        return json.loads(fragment)
    except json.JSONDecodeError as error:
        raise Failure(f"bad_json: {error}", code=3) from error


def salvage_json(text):
    """保守修复被截断的输出：回退到最后一个完整元素边界，再补闭合括号。

    只用于 --salvage-truncated。成功返回 (object, cut_position)，失败返回 (None, None)。
    """
    diagnostic = scan_json(text)
    if diagnostic["start"] is None or diagnostic["mismatch"]:
        return None, None
    fragment = text[diagnostic["start"]:]
    # 优先回退到「完整元素边界」（} 或 ]），再考虑逗号，最后才是原始截断点：
    # 否则会在半个元素里补引号，产出一个看似合法、实则残缺的条目。
    boundaries = [index + 1 for index, char in enumerate(fragment) if char in "}]"]
    commas = [index + 1 for index, char in enumerate(fragment) if char == ","]
    candidates = list(dict.fromkeys(boundaries[::-1] + commas[::-1] + [len(fragment)]))[:400]
    seen = set()
    for cut in candidates:
        if cut in seen or cut <= 1:
            continue
        seen.add(cut)
        piece = fragment[:cut]
        while piece and piece[-1] in ", \t\r\n":
            piece = piece[:-1]
        if not piece or piece[0] not in "{[":
            continue
        repaired = _close_open(piece)
        if repaired is None:
            continue
        try:
            value = json.loads(repaired)
        except json.JSONDecodeError:
            continue
        if isinstance(value, (dict, list)):
            return value, cut
    return None, None


def _close_open(fragment):
    """给被截断的片段补上未闭合的字符串与括号；无法安全判断时返回 None。"""
    stack = []
    in_string = False
    escaped = False
    for char in fragment:
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
        elif char in "{[":
            stack.append(char)
        elif char in "}]":
            expected = "{" if char == "}" else "["
            if not stack or stack[-1] != expected:
                return None
            stack.pop()
    tail = '"' if in_string else ""
    for opener in reversed(stack):
        tail += "}" if opener == "{" else "]"
    return fragment + tail


# --------------------------------------------------------------------------- 小工具

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_id(revision, row, source=SOURCE_SLUG):
    """契约 2.1：id = db-<source-slug>-<8hex>，由 (source, revision, row) 确定性派生。"""
    digest = sha256_text(f"{source}|{revision}|{row}")
    return f"db-{source}-{digest[:8]}"


def excerpt(text, limit=600):
    value = "" if text is None else str(text)
    return value if len(value) <= limit else value[:limit] + "…"


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
        if number.is_integer():
            return int(number)
    return None


def _as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    slug = re.sub(r"_{2,}", "_", slug)
    if not slug or not slug[0].isalpha():
        return ""
    return slug[:64]


# --------------------------------------------------------------------------- 分类法

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


def open_taxonomy(path=None):
    """返回 (taxonomy 模块或 None, 覆盖域 tuple, 来源标签)。"""
    path = Path(path) if path else Path(__file__).with_name("taxonomy.py")
    if not path.is_file():
        return None, tuple(FALLBACK_DOMAINS), "readme-fallback(taxonomy.py missing)"
    try:
        module = load_module(path)
        domains = _domains_from_module(module)
    except Exception as error:  # 别人的文件可能正在写，不能让清洗器崩掉
        return None, tuple(FALLBACK_DOMAINS), f"readme-fallback(taxonomy.py unreadable: {error})"
    if not domains:
        return None, tuple(FALLBACK_DOMAINS), "readme-fallback(no domains in taxonomy.py)"
    return module, tuple(domains), "taxonomy.py"


def load_domains(path=None):
    """只要覆盖域；返回 (domains, source)。"""
    _module, domains, source = open_taxonomy(path)
    return domains, source


def _domains_from_module(module):
    for name in ("DOMAINS", "TAXONOMY", "DOMAIN_SPECS", "COVERAGE_DOMAINS"):
        value = getattr(module, name, None)
        if isinstance(value, (list, tuple, set)) and value and all(isinstance(x, str) for x in value):
            return sorted(value)
        if isinstance(value, dict) and value:
            return sorted(value)
    for name in ("domain_names", "domains", "all_domains"):
        function = getattr(module, name, None)
        if callable(function):
            try:
                value = function()
            except Exception:
                continue
            if isinstance(value, dict):
                return sorted(value)
            if isinstance(value, (list, tuple, set)) and all(isinstance(x, str) for x in value):
                return sorted(value)
    return []


def taxonomy_lang(lang):
    """taxonomy 的问题文案只有 zh/en 两套。"""
    return "zh" if str(lang).lower().startswith("zh") else "en"


def resolve_key(taxonomy, key):
    """按 taxonomy 解析问题键别名；返回规范键或 None。"""
    if taxonomy is None:
        return key
    try:
        return taxonomy.resolve_key(key)
    except Exception:
        return None


# --------------------------------------------------------------------------- 问题校验

def clean_noul_options(options, lang):
    """noul：options 固定 yes/no；缺失时补默认，写了别的键就拒。"""
    labels = ("是", "否") if str(lang).lower().startswith("zh") else ("Yes", "No")
    default = [{"key": "yes", "label": labels[0]}, {"key": "no", "label": labels[1]}]
    if options in (None, [], {}):
        return default, None, "noul_options_defaulted"
    if not isinstance(options, list):
        return None, "noul_options_invalid", None
    keys = []
    for option in options:
        if isinstance(option, str):
            keys.append(option.strip().lower())
        elif isinstance(option, dict) and isinstance(option.get("key"), str):
            keys.append(option["key"].strip().lower())
        else:
            return None, "noul_options_invalid", None
    if sorted(keys) != sorted(NOUL_KEYS):
        return None, "noul_options_invalid", None
    flag = None if keys == list(NOUL_KEYS) else "noul_options_reordered"
    return default, None, flag


def clean_choice_options(options):
    """choice：2–16 个 {key,label}，key 稳定唯一。"""
    if not isinstance(options, list) or not (MIN_CHOICE_OPTIONS <= len(options) <= MAX_CHOICE_OPTIONS):
        return None, "choice_options_count", None
    cleaned = []
    seen = set()
    normalized = False
    for option in options:
        if isinstance(option, str):
            key = slugify(option)
            label = option.strip()
            normalized = True
            if not key:
                return None, "choice_option_key_invalid", None
        elif isinstance(option, dict):
            key = option.get("key")
            label = option.get("label")
            if not isinstance(key, str) or not key.strip():
                key = label if isinstance(label, str) else ""
                normalized = True
            key = str(key).strip()
            if not KEY_RE.match(key):
                slug = slugify(key)
                if not slug:
                    return None, "choice_option_key_invalid", None
                key = slug
                normalized = True
            if not isinstance(label, str) or not label.strip():
                label = key
                normalized = True
        else:
            return None, "choice_option_invalid", None
        if key in seen:
            return None, "choice_option_key_duplicate", None
        seen.add(key)
        cleaned.append({"key": key, "label": label.strip()})
    return cleaned, None, ("choice_options_normalized" if normalized else None)


def clean_scale(scale):
    """score：scale {min,max,labels}，整数分级，min<max，labels 数量 = max-min+1。"""
    if isinstance(scale, list):
        numbers = [_as_int(item) for item in scale]
        if len(numbers) < 2 or any(item is None for item in numbers):
            return None, "score_scale_invalid", None
        return ({"min": numbers[0], "max": numbers[-1], "labels": [str(item) for item in numbers]},
                None, "scale_normalized")
    if not isinstance(scale, dict):
        return None, "score_scale_missing", None
    low = _as_int(scale.get("min"))
    high = _as_int(scale.get("max"))
    if low is None or high is None:
        return None, "score_scale_invalid", None
    if low >= high:
        return None, "score_bounds_invalid", None
    labels = scale.get("labels")
    flag = None
    if labels in (None, [], {}):
        labels = [str(value) for value in range(low, high + 1)]
        flag = "scale_labels_defaulted"
    if not isinstance(labels, list) or not all(isinstance(item, str) and item.strip() for item in labels):
        return None, "score_labels_invalid", None
    if len(labels) != high - low + 1:
        return None, "score_labels_mismatch", None
    return ({"min": low, "max": high, "labels": [item.strip() for item in labels]}, None, flag)


def clean_question(raw, index, lang=DEFAULT_LANG, taxonomy=None):
    """校验并归一一条 question；返回 (question, Problem, flag)。"""
    path = f"questions[{index}]"
    if not isinstance(raw, dict):
        return None, Problem("", "questions", "question_not_object", f"{path} 不是对象", path), None
    key = raw.get("key")
    if not isinstance(key, str) or not key.strip():
        return None, Problem("", "questions", "question_key_missing",
                             f"{path}.key 缺失", f"{path}.key"), None
    key = key.strip()
    if not KEY_RE.match(key):
        return None, Problem("", "questions", "question_key_invalid",
                             f"{path}.key 不合规：{key!r}", f"{path}.key"), None
    collected = []
    if taxonomy is not None:
        canonical = resolve_key(taxonomy, key)
        if canonical is None:
            return None, Problem("", "questions", "question_key_unknown",
                                 f"{path}.key={key!r} 不在 taxonomy 的问题键表里", f"{path}.key"), None
        if canonical != key:
            collected.append("question_key_alias_resolved")
            key = canonical
    kind = raw.get("kind")
    if kind is None:
        for alias in ("type", "primitive", "question_type"):
            if isinstance(raw.get(alias), str):
                kind = raw[alias]
                collected.append("kind_alias_normalized")
                break
    if kind not in KINDS:
        return None, Problem("", "questions", "kind_invalid",
                             f"{path}.kind 必须是 {KINDS}，得到 {kind!r}", f"{path}.kind"), None
    prompt = raw.get("prompt") or raw.get("question") or raw.get("text")
    if not isinstance(prompt, str) or not prompt.strip():
        return None, Problem("", "questions", "prompt_missing",
                             f"{path}.prompt 为空", f"{path}.prompt"), None
    question = {"key": key, "kind": kind, "prompt": prompt.strip()}
    spec = None
    fixed = False
    if taxonomy is not None:
        try:
            spec = taxonomy.key_spec(key)
        except Exception:
            spec = None
        if spec is not None:
            if kind != spec.kind:
                return None, Problem("", "questions", "kind_mismatch",
                                     f"{path}.kind={kind!r} 与 taxonomy 的 {spec.kind!r} 不一致",
                                     f"{path}.kind"), None
            fixed = not getattr(spec, "options_from_state", False)
    if fixed and spec is not None:
        # 选项/量程由 taxonomy 固定：模型怎么写都不采信，直接构造规范问题（不因模型的
        # 残缺 options 拒收，taxonomy 是唯一权威）。
        options = None
        try:
            rebuilt = taxonomy.build_question(key, lang=taxonomy_lang(lang),
                                              prompt=question["prompt"], options=options)
        except Exception as error:
            return None, Problem("", "questions", "taxonomy_question_invalid",
                                 f"{path}: {error}", path), None
        return rebuilt, None, collected + ["question_from_taxonomy"]
    if kind == "noul":
        options, code, flags = clean_noul_options(raw.get("options"), lang)
        if code:
            return None, Problem("", "questions", code,
                                 f"{path}.options 不是固定 yes/no", f"{path}.options"), None
        question["options"] = options
        if flags:
            collected.append(flags)
    elif kind == "choice":
        options, code, flags = clean_choice_options(raw.get("options"))
        if code:
            return None, Problem("", "questions", code,
                                 f"{path}.options 非法（{code}）", f"{path}.options"), None
        question["options"] = options
        if flags:
            collected.append(flags)
        if taxonomy is not None and spec is not None and getattr(spec, "options_from_state", False):
            try:
                rebuilt = taxonomy.build_question(key, lang=taxonomy_lang(lang),
                                                  prompt=question["prompt"],
                                                  options=question["options"])
            except Exception as error:
                return None, Problem("", "questions", "taxonomy_question_invalid",
                                     f"{path}: {error}", path), None
            return rebuilt, None, collected + ["question_from_taxonomy"]
    else:
        scale_source = raw.get("scale") if raw.get("scale") is not None else raw.get("options")
        scale, code, flags = clean_scale(scale_source)
        if code:
            return None, Problem("", "questions", code,
                                 f"{path}.scale 非法（{code}）", f"{path}.scale"), None
        question["scale"] = scale
        if flags:
            collected.append(flags)
    return question, None, collected


def clean_questions(raw_questions, lang=DEFAULT_LANG, taxonomy=None):
    """校验整组 questions；返回 (questions, problems, flags)。"""
    if not isinstance(raw_questions, list) or not raw_questions:
        return None, [Problem("", "questions", "questions_missing",
                              "questions 必须是非空数组", "questions")], []
    if len(raw_questions) > MAX_QUESTIONS:
        return None, [Problem("", "questions", "questions_too_many",
                              f"questions 超过 {MAX_QUESTIONS} 条", "questions")], []
    questions = []
    problems = []
    flags = []
    seen = set()
    for index, raw in enumerate(raw_questions):
        question, problem, flag = clean_question(raw, index, lang, taxonomy)
        if problem is not None:
            problems.append(problem)
            continue
        if question["key"] in seen:
            problems.append(Problem("", "questions", "question_key_duplicate",
                                    f"questions[{index}].key 重复：{question['key']}", "questions"))
            continue
        seen.add(question["key"])
        if flag:
            flags.extend([flag] if isinstance(flag, str) else list(flag))
        questions.append(question)
    if problems:
        return None, problems, flags
    return questions, [], flags


# --------------------------------------------------------------------------- 答案校验

def _match_answer(question, answer, flags, taxonomy=None):
    """把答案归一到该 question 的合法取值；失败返回 (None, code)。"""
    kind = question["kind"]
    if isinstance(answer, bool) and kind == "noul":
        flags.append("answer_bool_normalized")
        return ("yes" if answer else "no"), None
    if kind == "noul":
        if isinstance(answer, str):
            value = answer.strip().lower()
            if value in NOUL_KEYS:
                if value != answer.strip():
                    flags.append("answer_case_normalized")
                return value, None
            for option in question["options"]:
                if option["label"].strip() == answer.strip():
                    flags.append("answer_by_label")
                    return option["key"], None
        return None, "answer_invalid"
    if kind == "choice":
        if isinstance(answer, str):
            value = answer.strip()
            keys = [option["key"] for option in question["options"]]
            if value in keys:
                return value, None
            lowered = value.lower()
            if lowered in keys:
                flags.append("answer_case_normalized")
                return lowered, None
            matches = [option["key"] for option in question["options"]
                       if option["label"].strip() == value]
            if len(matches) == 1:
                flags.append("answer_by_label")
                return matches[0], None
            slug = slugify(value)
            if slug and slug in keys:
                flags.append("answer_by_slug")
                return slug, None
            if taxonomy is not None:
                try:
                    normalized = taxonomy.normalize_answer(question["key"], value)
                except Exception:
                    normalized = None
                if isinstance(normalized, str) and normalized in keys:
                    flags.append("answer_alias_normalized")
                    return normalized, None
        return None, "answer_invalid"
    number = _as_int(answer)
    if number is None:
        return None, "answer_invalid"
    scale = question["scale"]
    if not (scale["min"] <= number <= scale["max"]):
        return None, "answer_out_of_range"
    if not isinstance(answer, int) or isinstance(answer, bool):
        flags.append("answer_int_normalized")
    return number, None


def _valid_prob_keys(question):
    if question["kind"] == "score":
        scale = question["scale"]
        return [str(value) for value in range(scale["min"], scale["max"] + 1)]
    return [option["key"] for option in question["options"]]


def clean_probs(question, probs, flags):
    """校验并归一概率分布；非法时返回 (None, code)。"""
    if not isinstance(probs, dict) or not probs:
        return None, "probs_not_object"
    allowed = _valid_prob_keys(question)
    cleaned = {}
    for key, value in probs.items():
        text_key = str(key).strip()
        if question["kind"] == "score":
            number_key = _as_int(text_key)
            text_key = str(number_key) if number_key is not None else text_key
        if text_key not in allowed:
            return None, "probs_unknown_key"
        number = _as_number(value)
        if number is None or number < 0 or number > 1:
            return None, "probs_value_invalid"
        cleaned[text_key] = number
    total = sum(cleaned.values())
    if total <= 0 or abs(total - 1.0) > PROBS_SUM_TOL:
        return None, "probs_sum_invalid"
    if abs(total - 1.0) > 1e-9:
        cleaned = {key: value / total for key, value in cleaned.items()}
        flags.append("probs_renormalized")
    if len(cleaned) < len(allowed):
        flags.append("probs_partial")
    return cleaned, None


def clean_targets(raw_targets, questions, flags, taxonomy=None, strict=False):
    """校验 targets。

    返回 (targets, problems, warnings)。problems 会让整条进 rejects；
    warnings 只丢弃该 target（条目仍然入库），符合 db-schema 的「宁可不写 targets」。
    """
    problems = []
    warnings = []
    issues = problems if strict else warnings

    def issue(code, message, path, stage="targets"):
        issues.append(Problem("", stage, code, message, path))

    by_key = {question["key"]: question for question in questions}
    pairs = []
    if raw_targets in (None, {}, []):
        return {}, [], []
    if isinstance(raw_targets, dict):
        pairs = list(raw_targets.items())
    elif isinstance(raw_targets, list):
        for index, entry in enumerate(raw_targets):
            if not isinstance(entry, dict):
                issue("target_not_object", f"targets[{index}] 不是对象", "targets")
                continue
            key = entry.get("key")
            if not isinstance(key, str) or not key.strip():
                issue("target_key_missing", f"targets[{index}].key 缺失", "targets")
                continue
            pairs.append((key.strip(), entry))
    else:
        issue("targets_not_object", "targets 必须是对象或数组", "targets")
        return {}, problems, warnings
    targets = {}
    for key, payload in pairs:
        canonical = resolve_key(taxonomy, key) if taxonomy is not None else key
        question = by_key.get(canonical)
        if question is None:
            issue("target_unknown_key", f"targets.{key} 没有对应的问题键", f"targets.{key}")
            continue
        if payload is None:
            continue
        if not isinstance(payload, dict):
            payload = {"answer": payload}
            flags.append("target_scalar_normalized")
        answer = payload.get("answer", payload.get("label"))
        probs = payload.get("probs", payload.get("probabilities"))
        entry = {}
        answer_flag_start = len(flags)
        if answer is not None:
            value, code = _match_answer(question, answer, flags, taxonomy)
            if code:
                del flags[answer_flag_start:]
                if strict:
                    issue(code, f"targets.{key}.answer={answer!r} 不是合法答案",
                          f"targets.{key}.answer")
                else:
                    issue("target_dropped_answer_invalid",
                          f"targets.{key}.answer={answer!r} 不是合法答案（该 target 已丢弃）",
                          f"targets.{key}.answer")
                continue
            entry["answer"] = value
        if probs is not None:
            cleaned, code = clean_probs(question, probs, flags)
            if code:
                if "answer" in entry:
                    flags.append(f"probs_dropped_{code}")
                elif strict:
                    issue(code, f"targets.{key}.probs 非法（{code}）", f"targets.{key}.probs")
                    continue
                else:
                    issue("target_dropped_probs_invalid",
                          f"targets.{key}.probs 非法（{code}），且没有合法 answer（该 target 已丢弃）",
                          f"targets.{key}.probs")
                    continue
            else:
                entry["probs"] = cleaned
                if "answer" not in entry:
                    best = max(cleaned.items(), key=lambda item: item[1])[0]
                    entry["answer"] = int(best) if question["kind"] == "score" else best
                    flags.append("answer_from_probs")
        if entry:
            targets[question["key"]] = entry
    if taxonomy is not None:
        for key in list(targets):
            errors = taxonomy.validate_target(key, targets[key])
            if errors:
                if strict:
                    problems.extend(Problem("", "targets", "taxonomy_target_invalid", message,
                                            f"targets.{key}") for message in errors[:3])
                else:
                    warnings.extend(Problem("", "targets", "target_dropped_taxonomy_invalid",
                                            message, f"targets.{key}") for message in errors[:3])
                del targets[key]
    return targets, problems, warnings


# --------------------------------------------------------------------------- 条目

def _item_flags(options, record):
    flags = ["synthetic", "closed_teacher", "not_ground_truth", "license_unverified",
             f"teacher_{slugify(options.teacher_model) or 'unknown'}"]
    model = record.get("model")
    if isinstance(model, str) and model.strip() and model.strip() != options.teacher_model:
        flags.append(f"route_model_{slugify(model) or 'unknown'}")
    return flags


class Cleaner:
    """把响应 JSONL 清洗成契约条目；regenerate 为可选的有限次重生成回调。"""

    def __init__(self, options=None, regenerate=None, domains=None, taxonomy=None,
                 taxonomy_source=None):
        self.options = options or Options()
        if domains is None:
            auto_module, domains, source = open_taxonomy()
            if taxonomy is None:
                taxonomy = auto_module
            self.domain_source = taxonomy_source or source
        else:
            domains = tuple(domains)
            self.domain_source = taxonomy_source or ("taxonomy.py" if taxonomy else "explicit")
        self.taxonomy = taxonomy
        self.taxonomy_check = bool(taxonomy is not None and self.options.taxonomy_check)
        self.domains = set(domains)
        self.regenerate = regenerate
        self.seen_ids = set()
        self.counter = {"rows_read": 0, "rows_with_output": 0, "rows_without_output": 0,
                        "items": 0, "rejects": 0, "warnings": 0, "targets_kept": 0,
                        "targets_dropped": 0, "repairs_used": 0, "repaired_items": 0,
                        "salvaged_items": 0, "multi_item_rows": 0}
        self.rejects_by_code = {}
        self.warnings_by_code = {}
        self.flag_counts = {}

    # ------------------------------------------------------------------ 对外
    def clean_rows(self, rows):
        items, rejects = [], []
        for line_no, record in rows:
            row_items, row_rejects = self.clean_row(line_no, record)
            items.extend(row_items)
            rejects.extend(row_rejects)
            self.counter["rows_read"] += 1
            if len(row_items) + len(row_rejects) == 0:
                self.counter["rows_without_output"] += 1
            else:
                self.counter["rows_with_output"] += 1  # 条目、硬拒或仅 warning 都算有产出
        self.counter["items"] = len(items)
        self.counter["rejects"] = len(rejects)
        stats = dict(self.counter)
        stats["rejects_by_code"] = dict(sorted(self.rejects_by_code.items()))
        stats["warnings_by_code"] = dict(sorted(self.warnings_by_code.items()))
        stats["flags"] = dict(sorted(self.flag_counts.items()))
        stats["domain_source"] = self.domain_source
        stats["taxonomy_check"] = self.taxonomy_check
        stats["converter_version"] = VERSION
        return CleanResult(items=items, rejects=rejects, stats=stats)

    # ------------------------------------------------------------------ 单行
    def clean_row(self, line_no, record):
        parse_error = record.get("__parse_error__") if isinstance(record, dict) else "输入行不是对象"
        if parse_error:
            record_id = f"line-{line_no}"
            problem = Problem(record_id, "input", "input_json_invalid",
                              f"输入行不是合法 JSON 对象：{parse_error}")
            return [], [self._reject_record(problem, record_id, line_no, "")]
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            record_id = f"line-{line_no}"
        record_id = record_id.strip()
        response = record.get("response")
        repairs = 0
        items, problems, warnings = [], [], []
        while True:
            items, problems, warnings = self._attempt(record_id, record, response)
            if not problems or repairs >= self.options.max_repairs or self.regenerate is None:
                break
            try:
                replacement = self.regenerate(record, repairs + 1, problems)
            except Failure:
                raise
            except Exception as error:  # 重生成失败不该让整批中止
                replacement = None
                anchor = problems[0].item_id if problems else record_id
                problems.append(Problem(anchor, "repair", "repair_call_failed",
                                        f"重生成调用失败：{type(error).__name__}"))
            repairs += 1
            self.counter["repairs_used"] += 1
            if not replacement:
                break
            response = replacement
        if repairs and items:
            tag = f"repaired_{repairs}x"
            for item in items:
                item["meta"]["quality_flags"] = sorted(set(item["meta"]["quality_flags"]) | {tag})
            self.counter["repaired_items"] += len(items)
            self._count_flags([tag])
        grouped = {}
        order = []
        for problem in problems:
            if problem.item_id not in grouped:
                grouped[problem.item_id] = []
                order.append(problem.item_id)
            grouped[problem.item_id].append(problem)
        rejects = []
        for item_id in order:
            entry = grouped[item_id]
            rejects.append(self._reject_record(entry[0], record_id, line_no, response,
                                               extra=entry[1:], item_id=item_id, repairs=repairs))
        warn_grouped = {}
        for index, warning in enumerate(warnings[:MAX_WARNINGS_PER_ITEM * max(len(items), 1)]):
            warn_grouped.setdefault(warning.item_id or f"{record_id}#{index}", []).append(warning)
        for item_id, entry in warn_grouped.items():
            rejects.append(self._reject_record(entry[0], record_id, line_no, response,
                                               extra=entry[1:], item_id=item_id,
                                               severity="warning"))
        for item in items:
            self._count_flags(item["meta"]["quality_flags"])
            self.counter["targets_kept"] += len(item.get("targets") or {})
        if len(items) + len(rejects) == 0:
            problem = Problem(record_id, "internal", "empty_attempt",
                              "既没有条目也没有拒绝记录（内部错误）")
            rejects.append(self._reject_record(problem, record_id, line_no, response))
        return items, rejects

    def _reject_record(self, problem, record_id, line_no, response, extra=None,
                       item_id=None, repairs=0, severity="reject"):
        entries = [problem] + list(extra or [])
        bucket = self.rejects_by_code if severity == "reject" else self.warnings_by_code
        for entry in entries:
            bucket[entry.code] = bucket.get(entry.code, 0) + 1
        if severity == "warning":
            self.counter["warnings"] += 1
            self.counter["targets_dropped"] += 1
        return {
            "id": item_id or problem.item_id or record_id,
            "input_id": record_id,
            "line": line_no,
            "severity": severity,
            "item_kept": severity == "warning",
            "stage": problem.stage,
            "reason_code": problem.code,
            "reason": "; ".join(entry.message for entry in entries[:4]),
            "errors": [entry.as_dict() for entry in entries[:8]],
            "codes": [entry.code for entry in entries[:8]],
            "repairs_attempted": repairs,
            "response_excerpt": excerpt(response),
            "created_at": self.options.timestamp(),
        }

    # ------------------------------------------------------------------ 一次尝试
    def _attempt(self, record_id, record, response):
        if response is None or not str(response).strip():
            return [], [Problem(record_id, "input", "missing_response",
                                "输入行没有 response；只有 prompt 时需 --live 生成")], []
        text = str(response)
        if len(text) > MAX_RESPONSE_CHARS:
            return [], [Problem(record_id, "extract", "response_too_large",
                                f"response 超过 {MAX_RESPONSE_CHARS} 字符")], []
        payload = None
        salvaged = False
        try:
            payload = extract_json(text)
        except Failure as failure:
            code = str(failure).split(":", 1)[0]
            hint = "（finish_reason=length，输出被截断）" if self._truncated(record) else ""
            if self.options.salvage_truncated:
                candidate, _ = salvage_json(text)
                if candidate is not None:
                    payload = candidate
                    salvaged = True
            if payload is None:
                return [], [Problem(record_id, "extract", code, f"{failure}{hint}")], []
        raw_items, problems = self._envelope(payload)
        if not raw_items and not problems:
            problems = [Problem(record_id, "envelope", "envelope_invalid",
                                "无法从输出里取出条目数组")]
        if len(raw_items) > 1:
            self.counter["multi_item_rows"] += 1
        items = []
        warnings = []
        for index, raw in enumerate(raw_items):
            row_key = record_id if len(raw_items) == 1 else f"{record_id}#{index}"
            item_id = derive_id(self.options.revision, row_key)
            item, item_problems, item_warnings, _flags = self._clean_one(
                raw, record, item_id, record_id, salvaged)
            if item is not None:
                if item_id in self.seen_ids:
                    problems.append(Problem(item_id, "item", "duplicate_item_id",
                                            f"条目 id 重复：{item_id}"))
                    continue
                self.seen_ids.add(item_id)
                items.append(item)
            problems.extend(item_problems)
            warnings.extend(item_warnings[:MAX_WARNINGS_PER_ITEM])
        if salvaged and items:
            tag = "salvaged_truncated"
            for item in items:
                item["meta"]["quality_flags"] = sorted(set(item["meta"]["quality_flags"]) | {tag})
            self.counter["salvaged_items"] += len(items)
        return items, problems, warnings

    @staticmethod
    def _truncated(record):
        return str(record.get("finish_reason") or "").lower() in ("length", "max_tokens")

    def _envelope(self, payload):
        """把提取到的 JSON 归一成条目数组；超出上限时显式记一条 reject，不静默丢弃。"""
        problems = []
        if isinstance(payload, list):
            values = payload
        elif not isinstance(payload, dict):
            return [], [Problem("", "envelope", "envelope_invalid",
                                "顶层 JSON 既不是对象也不是数组")]
        else:
            values = None
            for key in ("items", "records", "entries", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    values = value
                    break
                if isinstance(value, dict) and "questions" in value:
                    values = [value]
                    break
            if values is None:
                if "questions" in payload or "state" in payload:
                    values = [payload]
                elif len(payload) == 1:
                    only = next(iter(payload.values()))
                    if isinstance(only, dict) and "questions" in only:
                        values = [only]
                    elif isinstance(only, list):
                        values = only
                    else:
                        return [], []
                else:
                    return [], []
        if len(values) > MAX_ITEMS_PER_RESPONSE:
            problems.append(Problem("", "envelope", "items_truncated",
                                    f"输出含 {len(values)} 个条目，只取前 {MAX_ITEMS_PER_RESPONSE} 个"))
        return values[:MAX_ITEMS_PER_RESPONSE], problems

    def _clean_one(self, raw, record, item_id, record_id, salvaged=False):
        if not isinstance(raw, dict):
            return None, [Problem(item_id, "item", "item_not_object", "条目不是 JSON 对象")], [], []
        problems = []
        flags = _item_flags(self.options, record)
        if salvaged:
            flags.append("salvaged_truncated")
        state = raw.get("state")
        record_state = record.get("state")
        if isinstance(record_state, str) and record_state.strip():
            state = record_state
            flags.append("state_from_request")
        if not isinstance(state, str) or not state.strip():
            problems.append(Problem(item_id, "item", "state_missing", "state 为空或缺失", "state"))
        domain = record.get("domain") or raw.get("domain") or self.options.default_domain
        if not isinstance(domain, str) or not domain.strip():
            problems.append(Problem(item_id, "item", "domain_missing", "domain 缺失", "domain"))
        elif domain.strip() not in self.domains:
            problems.append(Problem(item_id, "item", "domain_unknown",
                                    f"domain={domain!r} 不在覆盖域 {sorted(self.domains)}", "domain"))
        lang = record.get("lang") or raw.get("lang") or self.options.default_lang
        if not isinstance(lang, str) or not LANG_RE.match(lang.strip()):
            problems.append(Problem(item_id, "item", "lang_invalid", f"lang={lang!r} 非法", "lang"))
        lang = lang.strip() if isinstance(lang, str) else self.options.default_lang
        taxonomy = self.taxonomy if self.taxonomy_check else None
        questions, question_problems, question_flags = clean_questions(
            raw.get("questions"), lang, taxonomy)
        problems.extend(Problem(item_id, entry.stage, entry.code, entry.message, entry.path)
                        for entry in question_problems)
        flags.extend(question_flags)
        targets = {}
        warnings = []
        if questions and self.options.allow_targets:
            target_flags = []
            targets, target_problems, target_warnings = clean_targets(
                raw.get("targets"), questions, target_flags, taxonomy, self.options.strict_targets)
            problems.extend(Problem(item_id, entry.stage, entry.code, entry.message, entry.path)
                            for entry in target_problems)
            warnings.extend(Problem(item_id, entry.stage, entry.code, entry.message, entry.path)
                            for entry in target_warnings)
            flags.extend(target_flags)
        if problems:
            return None, problems, warnings, flags
        item = {
            "id": item_id,
            "domain": domain.strip(),
            "lang": lang,
            "state": state.strip(),
            "questions": questions,
            "source": {
                "dataset": self.options.dataset,
                "revision": self.options.revision,
                "config": domain.strip(),
                "split": self.options.split,
                "row": record_id,
                "license": self.options.license,
                "url": self.options.url,
            },
            "meta": {
                "converter": CONVERTER,
                "converter_version": VERSION,
                "created_at": self.options.timestamp(),
                "quality_flags": sorted(set(flags)),
            },
        }
        if targets:
            item["targets"] = targets
        if self.taxonomy_check:
            errors = self.taxonomy.item_errors(item)
            if errors:
                problems = [Problem(item_id, "taxonomy", "taxonomy_invalid", message)
                            for message in errors[:6]]
                return None, problems, warnings, flags
        return item, [], warnings, flags

    def _count_flags(self, flags):
        for flag in flags:
            self.flag_counts[flag] = self.flag_counts.get(flag, 0) + 1


# --------------------------------------------------------------------------- IO

def iter_jsonl(path):
    text = Path(path).read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            yield line_no, {"__parse_error__": str(error)}
            continue
        if not isinstance(record, dict):
            yield line_no, {"__parse_error__": "顶层不是 JSON 对象"}
            continue
        yield line_no, record


def write_jsonl(path, rows):
    target = Path(path)
    if str(target.parent):
        target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- 重生成

def load_repair_fixture(path):
    """离线修复回放：{id, attempt, response} -> (id, attempt) 映射。"""
    table = {}
    for _, record in iter_jsonl(path):
        if "__parse_error__" in record:
            raise Failure(f"repair fixture 不是合法 JSONL：{record['__parse_error__']}")
        table[(str(record.get("id")), int(record.get("attempt", 1)))] = record.get("response")
    return table


def make_fixture_regenerator(table):
    def regenerate(record, attempt, problems):
        return table.get((str(record.get("id")), int(attempt)),
                         table.get((str(record.get("id")), 1)))
    return regenerate


def build_repair_prompt(record, attempt, problems):
    lines = []
    base = record.get("prompt")
    if isinstance(base, str) and base.strip():
        lines.append(base.strip())
    else:
        lines.append("你是决策数据生成器。请输出一个 JSON 对象："
                     '{"items":[{"state":"...","lang":"zh","questions":[...],"targets":{...}}]}；'
                     "不要 markdown 围栏、不要解释文字。")
    lines.append(f"第 {attempt} 次校验失败，错误如下：")
    for problem in problems[:8]:
        lines.append(f"- [{problem.code}] {problem.message}")
    previous = record.get("response")
    if isinstance(previous, str) and previous.strip():
        lines.append("上一次输出（可能被截断）：")
        lines.append(excerpt(previous, 1200))
    lines.append("请修正后重新只输出一个合法 JSON 对象。")
    return "\n".join(lines)


def make_live_regenerator(args):
    """真实调用重生成；密钥只从环境变量或 --key-file 读，绝不落盘。"""
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import luna_gen  # 同目录模块，延迟导入

    key = luna_gen.load_key(args.key_env, args.key_file)
    route = luna_gen.ROUTES[args.route]
    client = luna_gen.LunaClient(route=args.route, model=args.model or route["model"], api_key=key,
                                 timeout=args.timeout, max_tokens=args.max_tokens,
                                 response_format=args.response_format)
    calls = {"count": 0}

    def regenerate(record, attempt, problems):
        if calls["count"] >= LIVE_CALL_CAP and os.environ.get("LUNA_BULK_APPROVED") != "1":
            raise Failure(f"重生成超过 {LIVE_CALL_CAP} 次需要 LUNA_BULK_APPROVED=1（放量需 Lead 批准）")
        calls["count"] += 1
        return client.complete(build_repair_prompt(record, attempt, problems))["text"]

    return regenerate


# --------------------------------------------------------------------------- CLI

def build_parser():
    parser = argparse.ArgumentParser(description="把 Luna 输出清洗成 decision-base 契约条目")
    parser.add_argument("--input", required=True, help="原始响应 JSONL")
    parser.add_argument("--items", required=True, help="输出 items.jsonl")
    parser.add_argument("--rejects", required=True, help="输出 rejects.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少行输入")
    parser.add_argument("--domain", default=None, help="输入行没有 domain 时的默认覆盖域")
    parser.add_argument("--lang", default=DEFAULT_LANG)
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--revision", default=f"luna-gen-v{VERSION}+{DEFAULT_TEACHER}")
    parser.add_argument("--teacher-model", default=DEFAULT_TEACHER)
    parser.add_argument("--license", default=DEFAULT_LICENSE,
                        help="source.license；Luna 是闭源教师，默认 unknown-teacher-terms（不得冒认可再分发）")
    parser.add_argument("--source-url", default=DEFAULT_URL)
    parser.add_argument("--created-at", default=None, help="固定 meta.created_at（可复算用）")
    parser.add_argument("--salvage-truncated", action="store_true",
                        help="对截断输出做保守修复（默认直接进 rejects）")
    parser.add_argument("--no-targets", action="store_true", help="丢弃 targets，只输出 state+questions")
    parser.add_argument("--no-taxonomy-check", action="store_true",
                        help="即使 taxonomy.py 存在也不做键名/选项/答案一致性校验")
    parser.add_argument("--strict-targets", action="store_true",
                        help="targets 层问题也整条拒收（默认只丢弃该 target 并记 warning）")
    parser.add_argument("--repair", type=int, default=0, help=f"有限次重生成（0–{MAX_REPAIRS}）")
    parser.add_argument("--repair-fixture", default=None, help="离线修复回放 JSONL：{id, attempt, response}")
    parser.add_argument("--live", action="store_true", help="允许真实调用（重生成/补生成），需密钥")
    parser.add_argument("--route", default="luna", choices=("luna", "opencode-go"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--key-env", default=None)
    parser.add_argument("--key-file", default=None)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--response-format", default="json_object", choices=("json_object", "none"))
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--fail-on-reject", action="store_true",
                        help="有任何 severity=reject 就非零退出（冒烟时用）")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 0 <= args.repair <= MAX_REPAIRS:
        parser.error(f"--repair 必须在 0–{MAX_REPAIRS} 之间")
    regenerate = None
    if args.repair:
        if args.repair_fixture:
            regenerate = make_fixture_regenerator(load_repair_fixture(args.repair_fixture))
        elif args.live:
            try:
                regenerate = make_live_regenerator(args)
            except Exception as error:
                parser.error(f"--live 重生成不可用：{error}")
        else:
            parser.error("--repair 需要 --repair-fixture（离线）或 --live（真实调用）")
    options = Options(default_domain=args.domain, default_lang=args.lang, split=args.split,
                      dataset=args.dataset, revision=args.revision, license=args.license,
                      url=args.source_url, created_at=args.created_at,
                      teacher_model=args.teacher_model, salvage_truncated=args.salvage_truncated,
                      allow_targets=not args.no_targets, max_repairs=args.repair,
                      taxonomy_check=not args.no_taxonomy_check,
                      strict_targets=args.strict_targets)
    cleaner = Cleaner(options=options, regenerate=regenerate)
    rows = []
    for line_no, record in iter_jsonl(args.input):
        if args.limit is not None and len(rows) >= args.limit:
            break
        rows.append((line_no, record))
    result = cleaner.clean_rows(rows)
    write_jsonl(args.items, result.items)
    write_jsonl(args.rejects, result.rejects)
    summary = dict(result.stats)
    summary.update({"input": args.input, "items_path": args.items, "rejects_path": args.rejects})
    if not args.quiet:
        print(json.dumps(summary, ensure_ascii=False))
    if summary["rows_without_output"]:
        print(f"ERROR: {summary['rows_without_output']} 行既没有条目也没有拒绝记录（违反不得静默丢弃）",
              file=sys.stderr)
        return 1
    if args.fail_on_reject and summary["rejects"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
