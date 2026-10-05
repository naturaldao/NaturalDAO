"""PoL2 流水线共享工具：契约校验、JSONL 读写、断点续跑索引、密钥装载。

契约以 datasets/pol2/README.md 第 3 节为准，字段名固定；扩展只走 extra 对象。
本模块只做校验与本地 IO；除 load_secret 读取密钥文件外不接触仓库外数据，也不联网。

四类契约记录：case / question / answer / label。
- case 的配对元数据是 DATA-02 lead 追加的可选字段：pair_id / variant / diff 放 case 顶层，
  quality_flag 与 generator_lineage 放 provenance；契约同步见 pipeline/README.md
  「配对与质量标记」；缺这些字段的旧记录仍然合法。
- answer 在 execution_status != ok 时写 answer=null、不写 probs，与 benchmark/PROTOCOL.md
  「非 ok 时 status=null、不提供概率」的既有口径一致。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REGIONS = ("train", "public_test", "validation", "private_holdout")
PIPELINE_REGIONS = ("train", "public_test", "validation")
SURFACES = ("user_input", "assistant_output", "tool_action")
STATUSES = ("conforming", "violating", "insufficient")
POLARITIES = ("love", "hate", "neither", "unclear")
ACTIONS = ("allow", "repair", "block", "clarify", "review")
EVIDENCE = ("sufficient", "insufficient", "contradictory")
KINDS = ("choice", "noul", "score")
EXECUTION_STATUSES = ("ok", "timeout", "error", "invalid")
REVIEW_LEVELS = ("model_cross_checked", "human_reviewed")
NOUL_KEYS = ("yes", "no")
VARIANTS = ("a", "b")

CASE_ID_RE = re.compile(r"^pol2-(train|public_test|validation|private_holdout)-(\d{6})$")
PAIR_ID_RE = re.compile(r"^pol2-(train|public_test|validation|private_holdout)-p(\d{6})$")
FAMILY_ID_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

PAIR_FIELDS = ("pair_id", "variant", "diff")
PROVENANCE_OPTIONAL = ("generator_lineage", "quality_flag")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def csv_list(value):
    """Split a comma separated CLI value into non-empty stripped items."""
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


# ------------------------------------------------------------------ JSONL IO

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
    if path.suffix == ".gz":
        import gzip
        with gzip.open(path, "rt", encoding="utf-8-sig") as stream:
            return _parse_jsonl_lines(stream.read(), path)
    return _parse_jsonl_lines(path.read_text(encoding="utf-8-sig"), path)


def read_jsonl_any(path):
    """按扩展名读 .jsonl 或 .jsonl.gz；明文缺失时自动回退到同名 .gz。"""
    path = Path(path)
    if path.is_file():
        return read_jsonl(path)
    packed = Path(str(path) + ".gz")
    require(packed.is_file(), f"neither {path} nor {packed} exists")
    return read_jsonl(packed)


def resolve_jsonl(path):
    """Return the path that actually exists（明文优先，其次 .gz）。"""
    path = Path(path)
    if path.is_file():
        return path
    packed = Path(str(path) + ".gz")
    require(packed.is_file(), f"neither {path} nor {packed} exists")
    return packed


def _parse_jsonl_lines(text, path):
    rows = []
    for line_number, line in enumerate(text.splitlines(), 1):
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


def write_jsonl_new(path, rows):
    """Write a fresh JSONL file; refuse to overwrite different content."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = jsonl_text(rows)
    if path.exists():
        require(path.read_text(encoding="utf-8") == payload,
                f"refusing to overwrite {path}: exists with different content "
                f"(use a new --out directory)")
        return False
    path.write_text(payload, encoding="utf-8")
    return True


def write_jsonl_atomic(path, rows):
    """Replace path atomically (used for compaction of our own resume file)."""
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
    return True


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_json_new(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if path.exists():
        require(path.read_text(encoding="utf-8") == body,
                f"refusing to overwrite {path}: exists with different content")
        return False
    path.write_text(body, encoding="utf-8")
    return True


_NORMALIZE_RE = re.compile(r"[\s\W_]+")


def normalized_text(value):
    """Case/答案文本比较用的归一形式：去掉空白与标点、统一小写（不改变语义字符）。"""
    require(isinstance(value, str), "normalized_text expects a string")
    return _NORMALIZE_RE.sub("", value).lower()


def write_json_atomic(path, payload):
    """Atomically replace a derived JSON report (plan.json 仍用 write_json_new 保稳定)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return True


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(secret):
    """Short, non-reversible fingerprint used in logs; never log the secret itself."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]


# ------------------------------------------------------------------ indexes

def index_unique(rows, key, where="rows"):
    indexed = {}
    for position, row in enumerate(rows, 1):
        require(isinstance(row, dict), f"{where}[{position}]: each row must be an object")
        value = row.get(key)
        require(text(value), f"{where}[{position}]: missing/blank {key}")
        require(value not in indexed, f"{where}: duplicate {key}: {value}")
        indexed[value] = row
    return indexed


def read_jsonl_indexed(path, key):
    return index_unique(read_jsonl(path), key, where=str(path))


# ------------------------------------------------------------------ secrets

_REF_LINE_RE = re.compile(r"^[ \t]+([A-Za-z0-9_.\-]+):[ \t]*(\S.*?)[ \t]*$")


def load_secret(env_names, key_file=None, ref=None):
    """Return (secret, origin). Env first, then an optional secrets file.

    The file may be a DSH-style YAML with a top-level refs: mapping, or a plain
    file holding a single secret. The secret value is never logged.
    """
    for name in env_names:
        value = os.environ.get(name, "")
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
            if re.match(r"^[A-Za-z_]+:[ \t]*$", raw_line):
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
        raise ValueError(
            f"no secret for {wanted!r} in {path}; looked for env [{names}] and refs keys "
            f"{sorted(refs)}")
    raise ValueError(
        f"no secret found; set environment variable(s) {list(env_names)}"
        + (f" or pass --key-file" if key_file is None else ""))


# ------------------------------------------------------------------ probability helpers

def _prob_values(raw, keys=None, required_max=None):
    require(isinstance(raw, dict) and raw, "probs must be a non-empty object")
    require(all(isinstance(k, str) and k for k in raw), "probs keys must be non-empty strings")
    if keys is not None:
        require(set(raw) == set(keys), f"probs keys {sorted(raw)} != {sorted(keys)}")
    values = {}
    for key, value in raw.items():
        require(number(value) and value >= 0, f"probs[{key}] must be a finite number >= 0")
        if required_max is not None:
            require(value <= required_max, f"probs[{key}] must be <= {required_max}")
        values[key] = float(value)
    require(sum(values.values()) > 0, "probs must have a positive sum")
    return values


def normalize_probs(raw, keys=None, tolerance=1e-3):
    """Validate probabilities that already sum to 1 (allowing rounding) and renormalize."""
    values = _prob_values(raw, keys, required_max=1)
    total = sum(values.values())
    if abs(total - 1) > tolerance:
        raise ValueError(f"probs must sum to 1 (tolerance {tolerance}), got {total}")
    return {key: value / total for key, value in values.items()}


def rescale_probs(raw, keys=None):
    """Normalize model-produced weights/counts to a proper distribution.

    仅用于模型原始输出：任何非负权重都按比例归一到 1；这不是把不一致的答案洗成一致，
    而是契约要求的「归一到 1 的概率」。
    """
    values = _prob_values(raw, keys)
    total = sum(values.values())
    return {key: value / total for key, value in values.items()}


# ------------------------------------------------------------------ field checks

def require_fields(row, where, required, optional=()):
    require(isinstance(row, dict), f"{where}: must be an object")
    keys = set(row)
    missing = [key for key in required if key not in keys]
    require(not missing, f"{where}: missing field(s) {missing}")
    unknown = sorted(keys - set(required) - set(optional))
    require(not unknown, f"{where}: unknown field(s) {unknown}; 扩展只走 extra 对象")
    if "extra" in row:
        require(isinstance(row["extra"], dict), f"{where}: extra must be an object")


def _require_text_list(value, where, allow_empty=True):
    require(isinstance(value, list), f"{where} must be an array")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{where} must contain non-empty strings only")
    require(len(value) == len(set(value)), f"{where} must not contain duplicates")
    if not allow_empty:
        require(bool(value), f"{where} must not be empty")
    return value


# ------------------------------------------------------------------ case

def validate_case(row, where="case"):
    require_fields(row, where, ("id", "family_id", "region", "lang", "input", "provenance"),
                   optional=("extra",) + PAIR_FIELDS)
    require(text(row["id"]), f"{where}: id must be a non-empty string")
    match = CASE_ID_RE.match(row["id"])
    require(bool(match), f"{where}: id must look like pol2-<region>-<6 位序号>, got {row['id']!r}")
    require(text(row["family_id"]) and FAMILY_ID_RE.match(row["family_id"]),
            f"{where}: family_id must be dotted lowercase, got {row['family_id']!r}")
    require(row["region"] in REGIONS, f"{where}: region must be one of {REGIONS}")
    require(match.group(1) == row["region"],
            f"{where}: id encodes region {match.group(1)} but region={row['region']}")
    require(text(row["lang"]), f"{where}: lang must be a non-empty string")

    inp = row["input"]
    require(isinstance(inp, dict), f"{where}.input must be an object")
    require_fields(inp, f"{where}.input", ("surface", "context", "target", "policy", "clause"))
    require(inp["surface"] in SURFACES, f"{where}.input.surface must be one of {SURFACES}")
    _require_text_list(inp["context"], f"{where}.input.context", allow_empty=False)
    require(text(inp["target"]), f"{where}.input.target must be a non-empty string")
    require(text(inp["policy"]), f"{where}.input.policy must be a non-empty string")
    require(text(inp["clause"]), f"{where}.input.clause must be a non-empty string")

    prov = row["provenance"]
    require(isinstance(prov, dict), f"{where}.provenance must be an object")
    require_fields(prov, f"{where}.provenance",
                   ("generator", "model", "prompt_id", "gen_version", "seed", "created_at"),
                   optional=PROVENANCE_OPTIONAL)
    for key in ("generator", "model", "prompt_id", "gen_version", "created_at"):
        require(text(prov[key]), f"{where}.provenance.{key} must be a non-empty string")
    require(integer(prov["seed"]), f"{where}.provenance.seed must be an integer")
    if "generator_lineage" in prov:
        require(text(prov["generator_lineage"]),
                f"{where}.provenance.generator_lineage must be a non-empty string")
    if "quality_flag" in prov:
        _require_text_list(prov["quality_flag"], f"{where}.provenance.quality_flag")

    if "pair_id" in row or "variant" in row or "diff" in row:
        require("pair_id" in row and "variant" in row and "diff" in row,
                f"{where}: pair_id/variant/diff must appear together")
        require(bool(PAIR_ID_RE.match(row["pair_id"])),
                f"{where}: pair_id must look like pol2-<region>-p<6 位序号>")
        require(PAIR_ID_RE.match(row["pair_id"]).group(1) == row["region"],
                f"{where}: pair_id region != region")
        require(row["variant"] in VARIANTS, f"{where}: variant must be one of {VARIANTS}")
        diff = row["diff"]
        require(isinstance(diff, dict), f"{where}.diff must be an object")
        require(text(diff.get("key_fact")), f"{where}.diff.key_fact must be a non-empty string")
        require(set(diff) <= {"key_fact", "a", "b"},
                f"{where}.diff allows only key_fact/a/b, got {sorted(diff)}")
        for key in ("a", "b"):
            if key in diff:
                require(text(diff[key]), f"{where}.diff.{key} must be a non-empty string")
    return row


# ------------------------------------------------------------------ question

def validate_question(row, where="question"):
    require_fields(row, where, ("qid", "id", "kind", "key", "prompt"),
                   optional=("options", "scale", "extra"))
    require(text(row["qid"]), f"{where}: qid must be a non-empty string")
    require(text(row["id"]), f"{where}: id must be a non-empty string")
    require(text(row["key"]), f"{where}: key must be a non-empty string")
    require(row["qid"] == f"{row['id']}.{row['key']}",
            f"{where}: qid must equal <case id>.<key>, got {row['qid']!r}")
    require(row["kind"] in KINDS, f"{where}: kind must be one of {KINDS}")
    require(text(row["prompt"]), f"{where}: prompt must be a non-empty string")

    if row["kind"] in ("choice", "noul"):
        require("options" in row, f"{where}: kind={row['kind']} requires options")
        require("scale" not in row, f"{where}: kind={row['kind']} must not carry scale")
        options = row["options"]
        require(isinstance(options, list) and options, f"{where}.options must be a non-empty array")
        keys = []
        for position, option in enumerate(options):
            require(isinstance(option, dict), f"{where}.options[{position}] must be an object")
            require_fields(option, f"{where}.options[{position}]", ("key", "label"))
            require(text(option["key"]) and text(option["label"]),
                    f"{where}.options[{position}] needs non-empty key and label")
            keys.append(option["key"])
        require(len(keys) == len(set(keys)), f"{where}.options keys must be unique")
        if row["kind"] == "noul":
            require(tuple(sorted(keys)) == tuple(sorted(NOUL_KEYS)),
                    f"{where}: noul options must be exactly {list(NOUL_KEYS)}, got {keys}")
    else:
        require("scale" in row, f"{where}: kind=score requires scale")
        require("options" not in row, f"{where}: kind=score must not carry options")
        scale = row["scale"]
        require(isinstance(scale, dict), f"{where}.scale must be an object")
        require_fields(scale, f"{where}.scale", ("min", "max", "labels"))
        require(number(scale["min"]) and number(scale["max"]) and scale["min"] < scale["max"],
                f"{where}.scale needs finite min < max")
        labels = scale["labels"]
        require(isinstance(labels, dict) and labels, f"{where}.scale.labels must be a non-empty object")
        for key, label in labels.items():
            require(text(label), f"{where}.scale.labels[{key}] must be a non-empty string")
            try:
                point = float(key)
            except (TypeError, ValueError):
                raise ValueError(f"{where}.scale.labels key {key!r} must be numeric")
            require(scale["min"] <= point <= scale["max"],
                    f"{where}.scale.labels key {key} outside [{scale['min']}, {scale['max']}]")
    return row


def option_keys(question):
    if question["kind"] == "score":
        return None
    return [option["key"] for option in question["options"]]


def read_questions(path):
    rows = read_jsonl(path)
    require(bool(rows), f"{path}: no questions")
    index = index_unique(rows, "qid", where=str(path))
    for qid, row in index.items():
        validate_question(row, where=f"{path}:{qid}")
    return rows


# ------------------------------------------------------------------ answer

def validate_answer(row, where="answer", question=None):
    require_fields(row, where,
                   ("qid", "source", "source_version", "answer", "execution_status",
                    "latency_ms", "created_at"),
                   optional=("probs", "raw", "extra"))
    require(text(row["qid"]), f"{where}: qid must be a non-empty string")
    require(text(row["source"]) and SOURCE_RE.match(row["source"]),
            f"{where}: source must match {SOURCE_RE.pattern}")
    require(text(row["source_version"]), f"{where}: source_version must be a non-empty string")
    require(row["execution_status"] in EXECUTION_STATUSES,
            f"{where}: execution_status must be one of {EXECUTION_STATUSES}")
    require(number(row["latency_ms"]) and row["latency_ms"] >= 0,
            f"{where}: latency_ms must be a finite number >= 0")
    require(text(row["created_at"]), f"{where}: created_at must be a non-empty string")

    if row["execution_status"] == "ok":
        answer = row["answer"]
        require(isinstance(answer, str) or number(answer),
                f"{where}: answer must be a string or number when execution_status=ok")
        require(not isinstance(answer, bool), f"{where}: answer must not be a bool")
        require(not (isinstance(answer, str) and not answer.strip()),
                f"{where}: answer must not be a blank string")
    else:
        require(row["answer"] is None,
                f"{where}: answer must be null when execution_status={row['execution_status']}")
        require("probs" not in row,
                f"{where}: probs must be omitted when execution_status={row['execution_status']}")

    if "probs" in row:
        keys = option_keys(question) if question is not None else None
        row_keys = list(row["probs"]) if isinstance(row["probs"], dict) else None
        if keys is not None and row_keys is not None and set(row_keys) != set(keys):
            raise ValueError(f"{where}: probs keys must equal question options {keys}")
        normalize_probs(row["probs"], keys=keys)

    if question is not None and row["execution_status"] == "ok":
        answer = row["answer"]
        if question["kind"] == "score":
            require(number(answer) and question["scale"]["min"] <= answer <= question["scale"]["max"],
                    f"{where}: score answer must be a number in "
                    f"[{question['scale']['min']}, {question['scale']['max']}]")
        else:
            keys = option_keys(question)
            require(answer in keys, f"{where}: answer {answer!r} is not one of {keys}")
    return row


def read_answers(path, questions=None):
    rows = read_jsonl(path)
    index = {}
    for position, row in enumerate(rows, 1):
        where = f"{path}[{position}]"
        question = questions.get(row.get("qid")) if isinstance(questions, dict) else None
        if questions is not None:
            require(row.get("qid") in questions, f"{where}: unknown qid {row.get('qid')!r}")
        validate_answer(row, where=where, question=question)
        qid = row["qid"]
        require(qid not in index, f"{path}: duplicate qid {qid}")
        index[qid] = row
    return rows


# ------------------------------------------------------------------ label

def validate_label(row, where="label"):
    require_fields(row, where,
                   ("id", "status", "polarity", "issues", "evidence", "acceptable_actions",
                    "citations", "brief_reason", "review"),
                   optional=("love_languages", "mitigations", "probs", "extra"))
    require(text(row["id"]), f"{where}: id must be a non-empty string")
    require(row["status"] in STATUSES, f"{where}: status must be one of {STATUSES}")
    require(row["polarity"] in POLARITIES, f"{where}: polarity must be one of {POLARITIES}")
    _require_text_list(row["issues"], f"{where}.issues")
    if row["status"] == "violating":
        require(bool(row["issues"]), f"{where}: violating labels need at least one issue")
    for key in ("love_languages", "mitigations"):
        if key in row:
            _require_text_list(row[key], f"{where}.{key}")
    require(row["evidence"] in EVIDENCE, f"{where}: evidence must be one of {EVIDENCE}")
    _require_text_list(row["acceptable_actions"], f"{where}.acceptable_actions", allow_empty=False)
    require(set(row["acceptable_actions"]) <= set(ACTIONS),
            f"{where}.acceptable_actions must use protocol actions {ACTIONS}")
    _require_text_list(row["citations"], f"{where}.citations", allow_empty=False)
    require(text(row["brief_reason"]), f"{where}.brief_reason must be a non-empty string")
    if "probs" in row:
        normalize_probs(row["probs"], keys=STATUSES)

    review = row["review"]
    require(isinstance(review, dict), f"{where}.review must be an object")
    require_fields(review, f"{where}.review",
                   ("sources", "agreement", "disagreements", "adjudicated_by", "review_level"))
    _require_text_list(review["sources"], f"{where}.review.sources", allow_empty=False)
    require(text(review["agreement"]), f"{where}.review.agreement must be a non-empty string")
    require(isinstance(review["disagreements"], list), f"{where}.review.disagreements must be an array")
    require(text(review["adjudicated_by"]), f"{where}.review.adjudicated_by must be a non-empty string")
    require(review["review_level"] in REVIEW_LEVELS,
            f"{where}.review.review_level must be one of {REVIEW_LEVELS}")
    return row


def read_labels(path):
    rows = read_jsonl(path)
    for position, row in enumerate(rows, 1):
        validate_label(row, where=f"{path}[{position}]")
    return rows
