"""decision-base 覆盖报告与配额校验。

用法：

    uv run --no-project --offline python datasets/general/coverage.py --items datasets/general/data/items.jsonl

输出：按 domain / source.dataset / 原语(kind) / lang / 问题键 的分布，PoL2 15 条判定轴的逐轴覆盖，
以及配额校验（总量 / 每域 / 单一来源占比）。报告会写明本次配额用的是哪一套。

配额来源（优先级从高到低，逐字段解析，报告 quotas.origin 给出每个字段的来源）：

1. 命令行：--min-total / --min-per-domain / --domain-min / --max-source-share；
2. datasets/general/sources.json 的 quotas 段（db-hf 维护，字段名兼容见 resolve_quotas 的别名表）；
3. README 硬阈值（本文件常量）：总量 >= 10000、每域 >= 1200、单一来源 <= 40%。

per-domain 政策（基础下限 + 例外）整组取用：命令行给了任一每域参数就整组用命令行，
否则整组取 sources.json，再否则用 README 默认。README 默认里 pol2_axis 下限是 **400**（其余五域 1200）：
decision-base 是通用底座，PoL2 专项语料本轮由协作者在别处生产（我方已搁置），
把它卡在 1200 会逼通用底座去补一个不归它管的缺口、稀释通用覆盖；等 PoL2 语料落地后再提这一档。
命令行显式给 --min-per-domain 而未给 --domain-min 时，该默认例外不自动生效。

出题方（questions[].origin，见 README 2.1）：

- origin=source：题目来自数据集本身，key 即来源原生问题名，**不在 taxonomy 词表内属正常**。
  形状校验改用条目自带的 options/scale：noul 只要求恰好 2 个非空选项（不强制字面量 yes/no——
  实测原生 noul 用 false/true、no/yes 且顺序不一）、choice >= 2 且不设上限（实测最多 57 个）、
  score 用自带 scale 自洽（实测最高 10 档）。原生键不计入 taxonomy 覆盖率统计，另列一组计数。
- origin=taxonomy（或缺省；老 items.jsonl 根本没有该字段）：沿用 taxonomy 词表的严格校验
  （noul 必须 yes/no、choice 2–16、score 0–4）。
- **未知键永不提前中断校验**：未知键只报一条可分类告警，同一条目的形状问题照样全部报出。

产物档位（--profile）：

- full（默认）：全量产物，按 sources.json / README 阈值校验总量、每域下限、单一来源占比。
- subset：子集产物（如 System-1 原生题子集）只校验它自己该负责的维度——非空、domain 合法、
  id 唯一、每道题显式声明 origin；全量阈值只在命令行显式给出时才生效（README / sources.json 的
  环境值不套用）。否则"单一来源 48.5%、三个域为 0"的子集产物会永远红，配额检查再次失去信号。

退出码：

- 0：通过（有问题但只是 schema 警告时仍为 0，除非加 --strict）
- 1：配额或硬性违规（未知 domain、重复 id、配额不达标），缺口会逐条列出
- 2：输入不可读（文件缺失、JSON 损坏、参数非法）

硬性违规与 schema 警告的分界：domain 必须在 taxonomy 内、id 不得重复，因为它们直接破坏配额口径；
其余 README 2.1 的字段问题（缺 source/meta 字段、键名/选项/答案不合法等）先记警告，--strict 时才算失败。

本阶段明确不做（不是漏了）：

- **语义近重复与同族跨区检测**：等通用底座定版、要切 train/eval 分区时另做独立工具
  （同情节的翻译与改写必须落在同一分区，见 README 第 4 节；本脚本只看单文件分布，不做语义比对）。
- **跨文件/跨来源 id 去重**：本阶段各来源各自确定性派生 id，跨来源碰撞由报告里的重复项体现、不拦截；
  同一文件内的重复 id 仍按硬违规拦截。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import taxonomy  # noqa: E402

SCHEMA = "decision-base-coverage/0.1"
DEFAULT_ITEMS = _HERE / "data" / "items.jsonl"
SOURCES_PATH = _HERE / "sources.json"
DEFAULT_MIN_TOTAL = 10_000
DEFAULT_MIN_PER_DOMAIN = 1_200
#: README 默认每域下限的例外：pol2_axis 400（理由见模块 docstring）
DEFAULT_DOMAIN_MIN: dict[str, int] = {"pol2_axis": 400}
DEFAULT_MAX_SOURCE_SHARE = 0.40
MAX_DISTINCT_MESSAGES = 200

#: sources.json 的 quotas 段字段名兼容表（第一个命中的为准；列出的都是同义写法，只取其一）
QUOTA_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "min_total": ("min_total", "total_min", "min_items", "min_records"),
    "min_per_domain": ("min_per_domain", "per_domain_min", "min_items_per_domain"),
    "domain_min": ("domain_min", "domain_minimums", "per_domain_overrides"),
    "max_source_share": ("max_source_share", "source_share_cap", "single_source_max_share", "max_share"),
}
QUOTA_ORIGIN_LABELS = {"cli": "命令行", "sources.json": "sources.json", "readme-default": "README 默认"}

#: questions[].origin 取值（README 2.1）；缺省按 taxonomy，保证老数据行为不变
ORIGIN_SOURCE = "source"
ORIGIN_TAXONOMY = "taxonomy"
ORIGINS = (ORIGIN_SOURCE, ORIGIN_TAXONOMY)

#: 产物档位：full=全量配额，subset=子集只查自身该负责的维度（见模块 docstring）
PROFILES: dict[str, dict] = {
    "full": {
        "description": "全量产物：按 sources.json / README 阈值校验总量、每域下限、单一来源占比",
        "read_ambient": True,
        "require_origin": False,
        "enforce_total": True,
        "enforce_domains": True,
        "enforce_source_share": True,
    },
    "subset": {
        "description": "子集产物：只校验非空/域合法/id 唯一/origin 显式；全量阈值需命令行显式给出",
        "read_ambient": False,
        "require_origin": True,
        "enforce_total": False,
        "enforce_domains": False,
        "enforce_source_share": False,
    },
}
DEFAULT_PROFILE = "full"


class ItemsError(Exception):
    """items.jsonl 不可读或不是逐行 JSON 对象。"""


def read_items(path: Path | str) -> list[dict]:
    """读取 JSONL；空行跳过，任何一行不是 JSON 对象就报错（不静默跳过坏行）。"""
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ItemsError(f"无法读取 {source}: {exc}") from exc
    items: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ItemsError(f"{source}:{lineno} JSON 解析失败: {exc}") from exc
        if not isinstance(record, dict):
            raise ItemsError(f"{source}:{lineno} 不是 JSON 对象，而是 {type(record).__name__}")
        items.append(record)
    return items

def read_sources_quotas(path: Path | str = SOURCES_PATH) -> tuple[dict, list[str], bool]:
    """读 sources.json 的 quotas 段（兼容 QUOTA_FIELD_ALIASES 里的同义字段名）。

    返回 (原始字段字典, 说明列表, 是否真的用上了文件)。文件不存在 / 无法解析 / 没有 quotas 段时
    返回 ({}, 说明, False)，由 resolve_quotas 逐字段回退 README 硬阈值；
    只有第三种元素为 True 时报告才写 source_file。
    """
    source = Path(path)
    if not source.is_file():
        return {}, [f"sources.json 不存在（{source}），配额用 README 默认值"], False
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"sources.json 无法解析（{exc}），配额用 README 默认值"], False
    if not isinstance(data, dict):
        return {}, ["sources.json 顶层不是对象，配额用 README 默认值"], False
    raw = data.get("quotas", data.get("quota"))
    if not isinstance(raw, dict):
        return {}, ["sources.json 没有 quotas 段，配额用 README 默认值"], False
    return raw, [], True


def _as_nonneg_int(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _as_share(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    share = float(value)
    if 1.0 < share <= 100.0:  # 允许写 40 表示 40%
        share = share / 100.0
    return share if 0.0 <= share <= 1.0 else None


def _as_domain_map(value, notes: list[str], label: str):
    if not isinstance(value, dict):
        notes.append(f"sources.json quotas.{label} 不是对象，忽略")
        return None
    parsed: dict[str, int] = {}
    for name, raw in value.items():
        if name not in taxonomy.DOMAINS:
            notes.append(f"sources.json quotas.{label} 的 {name!r} 不是覆盖域，忽略")
            continue
        number = _as_nonneg_int(raw)
        if number is None:
            notes.append(f"sources.json quotas.{label}[{name}]={raw!r} 不是非负整数，忽略")
            continue
        parsed[name] = number
    if value and not parsed:
        notes.append(f"sources.json quotas.{label} 没有任何合法条目，整段忽略")
        return None
    return parsed


def _first_present(raw: dict, field: str):
    for key in QUOTA_FIELD_ALIASES[field]:
        if key in raw:
            return key, raw[key]
    return None, None


def resolve_quotas(*, sources_path: Path | str = SOURCES_PATH, use_sources: bool = True,
                   min_total: int | None = None, min_per_domain: int | None = None,
                   max_source_share: float | None = None, domain_min: dict | None = None,
                   profile: str = DEFAULT_PROFILE) -> dict:
    """按 命令行 > sources.json > README 默认 逐字段解析配额，并给出哪些维度要强制。

    参数传 None 表示"这一层没给"，交给下一层；传具体值表示覆盖。
    domain_min 的 None 与 {} 含义不同：None=没给，{}=显式要求没有任何例外。
    profile=subset 时不套用环境值（sources.json / README），只有命令行显式给出的维度才强制。
    """
    if profile not in PROFILES:
        raise ValueError(f"未知档位 {profile!r}；合法值：{sorted(PROFILES)}")
    settings = PROFILES[profile]
    notes: list[str] = []
    raw: dict = {}
    used_file = False
    if use_sources and settings["read_ambient"]:
        raw, file_notes, used_file = read_sources_quotas(sources_path)
        notes.extend(file_notes)
    elif use_sources:
        notes.append(f"档位 {profile}：不套用 sources.json / README 的环境配额，"
                     "只有命令行显式给出的阈值才生效")
    origin: dict[str, str] = {}

    def pick(cli_value, field: str, default, cast):
        if cli_value is not None:
            origin[field] = "cli"
            return cli_value
        key, value = _first_present(raw, field)
        if key is not None:
            parsed = cast(value)
            if parsed is None:
                notes.append(f"sources.json quotas.{key}={value!r} 不合法，回退 README 默认 {default!r}")
            else:
                origin[field] = "sources.json"
                return parsed
        origin[field] = "readme-default"
        return default

    resolved_total = pick(min_total, "min_total", DEFAULT_MIN_TOTAL, _as_nonneg_int)
    resolved_share = pick(max_source_share, "max_source_share", DEFAULT_MAX_SOURCE_SHARE, _as_share)

    # per-domain 政策（基础下限 + 例外）整组解析，避免"某来源只给一半"造成半套配额
    file_base = None
    for key in QUOTA_FIELD_ALIASES["min_per_domain"]:
        if key in raw:
            parsed = _as_nonneg_int(raw[key])
            if parsed is None:
                notes.append(f"sources.json quotas.{key}={raw[key]!r} 不合法，改用 README 每域默认")
            else:
                file_base = parsed
            break
    file_exceptions = None
    for key in QUOTA_FIELD_ALIASES["domain_min"]:
        if key in raw:
            file_exceptions = _as_domain_map(raw[key], notes, key)
            break

    if min_per_domain is not None or domain_min is not None:
        base = min_per_domain if min_per_domain is not None else DEFAULT_MIN_PER_DOMAIN
        exceptions = dict(domain_min or {})
        origin["min_per_domain"] = "cli" if min_per_domain is not None else "readme-default"
        origin["domain_min"] = "cli" if domain_min is not None else "readme-default"
        if min_per_domain is not None and domain_min is None:
            notes.append("命令行给了 --min-per-domain 而未给 --domain-min：默认的 pol2_axis 例外不自动生效"
                         f"（如需保留请加 --domain-min pol2_axis={DEFAULT_DOMAIN_MIN['pol2_axis']}）")
    elif file_base is not None or file_exceptions is not None:
        base = file_base if file_base is not None else DEFAULT_MIN_PER_DOMAIN
        exceptions = file_exceptions if file_exceptions is not None else dict(DEFAULT_DOMAIN_MIN)
        origin["min_per_domain"] = "sources.json" if file_base is not None else "readme-default"
        origin["domain_min"] = "sources.json" if file_exceptions is not None else "readme-default"
        if file_exceptions is None:
            notes.append("sources.json 只给了每域下限、没给 domain_min：沿用默认例外 pol2_axis="
                         f"{DEFAULT_DOMAIN_MIN['pol2_axis']}（通用底座不背 PoL2 专项配额）")
    else:
        base = DEFAULT_MIN_PER_DOMAIN
        exceptions = dict(DEFAULT_DOMAIN_MIN)
        origin["min_per_domain"] = "readme-default"
        origin["domain_min"] = "readme-default"
        if settings["enforce_domains"]:
            notes.append(f"pol2_axis 下限默认 {DEFAULT_DOMAIN_MIN['pol2_axis']}（其余五域 {base}）："
                         "decision-base 是通用底座，PoL2 专项语料本轮由协作者在别处生产，"
                         "等其落地后再提这一档")

    values = set(origin.values())
    if "cli" in values:
        status = "cli"
    elif values == {"sources.json"}:
        status = "sources.json"
    elif values == {"readme-default"}:
        status = "readme-defaults"
    else:
        status = "mixed"
    enforce = {
        "total": bool(settings["enforce_total"] or origin.get("min_total") == "cli"),
        "domains": bool(settings["enforce_domains"] or origin.get("min_per_domain") == "cli"
                        or origin.get("domain_min") == "cli"),
        "source_share": bool(settings["enforce_source_share"] or origin.get("max_source_share") == "cli"),
        "require_origin": bool(settings["require_origin"]),
    }
    return {
        "profile": profile,
        "profile_description": settings["description"],
        "min_total": resolved_total,
        "min_per_domain": base,
        "domain_min": exceptions,
        "max_source_share": resolved_share,
        "origin": origin,
        "status": status,
        "source_file": str(sources_path) if used_file else None,
        "notes": notes,
        "enforce": enforce,
    }


# ---------------------------------------------------------------- origin 感知的校验


def question_origin(question) -> str:
    """取问题的出题方；缺省按 taxonomy（老 items.jsonl 没有该字段，行为必须不变）。"""
    origin = question.get("origin") if isinstance(question, dict) else None
    return origin if origin in ORIGINS else ORIGIN_TAXONOMY


def _option_item_errors(label: str, options) -> list[str]:
    """选项表自身的形状：key/label 非空、key 不重复。"""
    errors: list[str] = []
    seen: list[str] = []
    for option in options:
        if not isinstance(option, dict):
            errors.append(f"{label}: 选项必须是对象")
            continue
        okey, text = option.get("key"), option.get("label")
        if not isinstance(okey, str) or not okey.strip():
            errors.append(f"{label}: 选项缺非空 key")
            continue
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{label}: 选项 {okey} 缺非空 label")
        if okey in seen:
            errors.append(f"{label}: 选项 key 重复 {okey}")
        seen.append(okey)
    return errors


def _scale_shape_errors(label: str, scale, *, strict_limits: bool) -> list[str]:
    if not isinstance(scale, dict):
        return [f"{label}: score 必须有 scale 对象"]
    errors: list[str] = []
    low, high = scale.get("min"), scale.get("max")
    if isinstance(low, bool) or isinstance(high, bool) or \
            not isinstance(low, int) or not isinstance(high, int):
        return [f"{label}: scale.min/max 必须是整数"]
    if high < low:
        errors.append(f"{label}: scale.max {high} < min {low}")
    labels = scale.get("labels")
    if not isinstance(labels, list) or len(labels) != high - low + 1:
        errors.append(f"{label}: scale.labels 必须覆盖 {low}..{high} 共 {high - low + 1} 档")
    elif any(not isinstance(x, str) or not x.strip() for x in labels):
        errors.append(f"{label}: scale.labels 必须都是非空字符串")
    if strict_limits and (low, high) != (0, 4):
        errors.append(f"{label}: taxonomy 出题的 score 量程必须是 0..4，收到 {low}..{high}")
    return errors


def question_shape_errors(question, *, strict_limits: bool) -> list[str]:
    """与 origin 无关的形状校验（kind / prompt / options / scale 的结构）。

    strict_limits=True（taxonomy 出题）套用 README 固定档位；False（source 出题或未知键）只查结构：
    noul 恰好 2 个非空选项、choice >= 2 且不设上限、score 的 min/max/labels 自洽。都不提前返回。
    """
    if not isinstance(question, dict):
        return ["问题不是 JSON 对象"]
    raw_key = question.get("key")
    label = raw_key if isinstance(raw_key, str) and raw_key.strip() else "(缺 key)"
    errors: list[str] = []
    kind = question.get("kind")
    if kind not in taxonomy.KINDS:
        errors.append(f"{label}: kind={kind!r} 不在 {list(taxonomy.KINDS)}")
    prompt = question.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append(f"{label}: prompt 必须是非空字符串")
    if kind == "noul":
        options = question.get("options")
        if not isinstance(options, list):
            errors.append(f"{label}: noul 必须有 options 数组")
            return errors
        if len(options) != 2:
            errors.append(f"{label}: noul 必须恰好 2 个选项，收到 {len(options)}")
        errors += _option_item_errors(label, options)
        if strict_limits:
            names = [o.get("key") for o in options if isinstance(o, dict)]
            if names != ["yes", "no"]:
                errors.append(f"{label}: taxonomy 出题的 noul 选项必须恰好是 ['yes', 'no']，收到 {names}")
    elif kind == "choice":
        options = question.get("options")
        if not isinstance(options, list):
            errors.append(f"{label}: choice 必须有 options 数组")
            return errors
        if len(options) < taxonomy.MIN_CHOICE_OPTIONS:
            errors.append(f"{label}: choice 至少 {taxonomy.MIN_CHOICE_OPTIONS} 个选项，收到 {len(options)}")
        if strict_limits and len(options) > taxonomy.MAX_CHOICE_OPTIONS:
            errors.append(f"{label}: taxonomy 出题的 choice 最多 {taxonomy.MAX_CHOICE_OPTIONS} 个选项，"
                          f"收到 {len(options)}")
        errors += _option_item_errors(label, options)
    elif kind == "score":
        errors += _scale_shape_errors(label, question.get("scale"), strict_limits=strict_limits)
    return errors


def question_errors(question) -> list[str]:
    """一个 questions[] 条目的完整校验（origin 感知；不因未知键提前返回）。"""
    if not isinstance(question, dict):
        return ["问题不是 JSON 对象"]
    raw_key = question.get("key")
    origin = question_origin(question)
    if origin == ORIGIN_SOURCE:
        errors: list[str] = []
        if not isinstance(raw_key, str) or not raw_key.strip():
            errors.append("origin=source 的问题缺非空 key")
        source_key = question.get("source_key")
        if not isinstance(source_key, str) or not source_key.strip():
            errors.append(f"{raw_key or '(缺 key)'}: origin=source 必须带非空 source_key")
        return errors + question_shape_errors(question, strict_limits=False)
    try:
        taxonomy.key_spec(raw_key)
    except KeyError as exc:
        return [f"{raw_key!r}: 未知问题键且未标 origin=source（{exc}）"] + \
            question_shape_errors(question, strict_limits=False)
    return list(taxonomy.validate_question(question))


def _target_against_question(key: str, value, question) -> list[str]:
    """按条目自带的 options/scale 校验 targets[key]（source 原生键走这条路）。"""
    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{key}: target 必须是对象 {{answer?, probs?}}"]
    kind = question.get("kind")
    option_keys = [o.get("key") for o in question.get("options") or [] if isinstance(o, dict)]
    scale = question.get("scale") if isinstance(question.get("scale"), dict) else {}
    low, high = scale.get("min"), scale.get("max")
    errors: list[str] = []
    answer = value.get("answer")
    if answer is not None:
        if kind == "noul":
            if not (isinstance(answer, bool) or answer in option_keys):
                errors.append(f"{key}: noul 答案必须是 {option_keys} 之一（或布尔），收到 {answer!r}")
        elif kind == "choice":
            if not isinstance(answer, str) or answer not in option_keys:
                errors.append(f"{key}: 答案 {answer!r} 不在该题的 {len(option_keys)} 个选项内")
        elif kind == "score":
            level = _as_level(answer)
            if level is None:
                errors.append(f"{key}: score 答案必须是整数或整数字符串，收到 {answer!r}")
            elif isinstance(low, int) and isinstance(high, int) and not low <= level <= high:
                errors.append(f"{key}: score 答案 {level} 越界 {low}..{high}")
    errors += _prob_against_question(key, value.get("probs"), kind, option_keys, low, high)
    return errors


def _as_level(answer):
    """把 score 答案归一成整数：接受 int，也接受原生数据里的整数字符串（如 "4"）。"""
    if isinstance(answer, bool):
        return None
    if isinstance(answer, int):
        return answer
    if isinstance(answer, str):
        text = answer.strip()
        if text.lstrip("-").isdigit():
            return int(text)
    return None


def _prob_against_question(key: str, probs, kind, option_keys, low, high) -> list[str]:
    if probs is None:
        return []
    if not isinstance(probs, dict) or not probs:
        return [f"{key}: probs 必须是非空对象"]
    errors: list[str] = []
    total = 0.0
    for raw, prob in probs.items():
        if isinstance(prob, bool) or not isinstance(prob, (int, float)):
            errors.append(f"{key}: probs[{raw!r}] 必须是数字")
            continue
        if not 0.0 <= float(prob) <= 1.0:
            errors.append(f"{key}: probs[{raw!r}]={prob} 越界 [0,1]")
            continue
        total += float(prob)
        text = str(raw)
        if kind in ("noul", "choice"):
            if text not in option_keys:
                errors.append(f"{key}: probs 键 {raw!r} 不在该题的选项内")
        elif kind == "score":
            level = _as_level(text)
            if level is None:
                errors.append(f"{key}: probs 键 {raw!r} 不是整数分级")
            elif isinstance(low, int) and isinstance(high, int) and not low <= level <= high:
                errors.append(f"{key}: probs 键 {level} 越界 {low}..{high}")
    if not errors and abs(total - 1.0) > 1e-3:
        errors.append(f"{key}: probs 之和 {total:.6f} 未归一到 1")
    return errors


def target_errors(key: str, value, question) -> list[str]:
    """校验 targets[key]；question 为该条目里同名的 questions[] 条目（可为 None）。"""
    if question is None:
        return [f"没有对应的 questions 条目"]
    if question_origin(question) == ORIGIN_TAXONOMY:
        try:
            taxonomy.key_spec(key)
        except KeyError:
            pass
        else:
            return list(taxonomy.validate_target(key, value))
    return _target_against_question(key, value, question)


def item_errors(item) -> list[str]:
    """按 README 2.1 校验一个条目（origin 感知；任何单点错误都不会中断其余校验）。"""
    if not isinstance(item, dict):
        return ["条目不是 JSON 对象"]
    errors: list[str] = []
    for field_name in ("id", "domain", "lang", "state", "questions", "source", "meta"):
        if field_name not in item:
            errors.append(f"缺字段 {field_name}")
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        errors.append("id 必须是非空字符串")
    domain = item.get("domain")
    if domain not in taxonomy.DOMAINS:
        errors.append(f"domain={domain!r} 不在 taxonomy 的 6 个覆盖域内")
    lang = item.get("lang")
    if not isinstance(lang, str) or not lang.strip():
        errors.append("lang 必须是非空字符串")
    state = item.get("state")
    if not isinstance(state, str) or not state.strip():
        errors.append("state 必须是非空字符串")

    by_key: dict[str, dict] = {}
    questions = item.get("questions")
    if not isinstance(questions, list) or not questions:
        errors.append("questions 必须是非空数组")
    else:
        for index, question in enumerate(questions):
            errors += [f"questions[{index}]: {e}" for e in question_errors(question)]
            raw = question.get("key") if isinstance(question, dict) else None
            if not isinstance(raw, str) or not raw.strip():
                continue
            canonical = raw if question_origin(question) == ORIGIN_SOURCE else taxonomy.QUESTION_KEY_ALIASES.get(raw, raw)
            if canonical in by_key:
                errors.append(f"questions[{index}]: 问题键重复 {canonical}")
            by_key[canonical] = question

    targets = item.get("targets")
    if targets is None:
        targets = {}
    if not isinstance(targets, dict):
        errors.append("targets 必须是对象")
    else:
        for raw_key, value in targets.items():
            question = by_key.get(str(raw_key))
            if question is None:
                question = by_key.get(taxonomy.QUESTION_KEY_ALIASES.get(str(raw_key), ""))
            errors += [f"targets[{raw_key}]: {e}" for e in target_errors(str(raw_key), value, question)]

    source = item.get("source")
    if not isinstance(source, dict):
        errors.append("source 必须是对象")
    else:
        for field_name in ("dataset", "revision", "config", "split", "row", "license", "url"):
            if field_name not in source:
                errors.append(f"source 缺字段 {field_name}")
    meta = item.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta 必须是对象")
    else:
        for field_name in ("converter", "converter_version", "created_at"):
            if field_name not in meta:
                errors.append(f"meta 缺字段 {field_name}")
    return errors


def _dist(counter: Counter, total: int, limit: int | None = None) -> dict:
    rows = sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))
    if limit is not None:
        rows = rows[:limit]
    return {
        str(key): {"count": count, "share": round(count / total, 6) if total else 0.0}
        for key, count in rows
    }


def _share(counter: Counter, total: int) -> dict[str, float]:
    return {str(key): (round(count / total, 6) if total else 0.0) for key, count in counter.items()}


def build_report(items, *, items_file=None, min_total: int = DEFAULT_MIN_TOTAL,
                 min_per_domain: int = DEFAULT_MIN_PER_DOMAIN,
                 max_source_share: float = DEFAULT_MAX_SOURCE_SHARE,
                 domain_min: dict | None = None, quota_meta: dict | None = None) -> dict:
    """对已读入的条目做分布统计与配额校验，返回可 JSON 序列化的报告。

    domain_min 是"每域下限的例外"（如 {"pol2_axis": 400}）；quota_meta 来自 resolve_quotas，
    用于写明本次配额是哪一套（origin/status/source_file/notes）以及哪些维度要强制（enforce）。
    """
    meta = quota_meta or {}
    enforce = dict(meta.get("enforce") or {})
    enforce_total = bool(enforce.get("total", True))
    enforce_domains = bool(enforce.get("domains", True))
    enforce_share = bool(enforce.get("source_share", True))
    require_origin = bool(enforce.get("require_origin", False))
    profile = meta.get("profile", DEFAULT_PROFILE)

    total = len(items)
    per_domain_min = {domain: int((domain_min or {}).get(domain, min_per_domain))
                      for domain in taxonomy.DOMAINS}

    domain_counts: Counter = Counter()
    kind_counts: Counter = Counter()
    lang_counts: Counter = Counter()
    source_counts: Counter = Counter()
    key_counts: Counter = Counter()
    source_key_counts: Counter = Counter()
    kind_by_origin: Counter = Counter()
    origin_counts: Counter = Counter()
    domain_kind: Counter = Counter()
    domain_lang: Counter = Counter()
    axes_asked: Counter = Counter()
    axes_answered: Counter = Counter()
    mitigation_counts: Counter = Counter()
    love_language_counts: Counter = Counter()

    question_total = 0
    taxonomy_question_total = 0
    source_question_total = 0
    origin_missing = 0
    duplicates: list[str] = []
    seen_ids: set[str] = set()
    unknown_domains: Counter = Counter()
    issue_counts: Counter = Counter()
    issue_examples: dict[str, str] = {}
    issue_total = 0

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issue_total += 1
            issue_counts["条目不是 JSON 对象"] += 1
            continue
        domain = item.get("domain")
        if domain in taxonomy.DOMAINS:
            domain_counts[domain] += 1
        else:
            unknown_domains[str(domain)] += 1
            domain_counts["(unknown)"] += 1
        lang = item.get("lang")
        lang_counts[str(lang)] += 1
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        source_counts[str(source.get("dataset", "(missing)"))] += 1
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            if item_id in seen_ids:
                duplicates.append(item_id)
            seen_ids.add(item_id)

        origin_map: dict[str, str] = {}
        for question in item.get("questions") or []:
            if not isinstance(question, dict):
                continue
            key = question.get("key")
            if not isinstance(key, str) or not key.strip():
                continue
            origin = question_origin(question)
            if question.get("origin") not in ORIGINS:
                origin_missing += 1
            question_total += 1
            origin_counts[origin] += 1
            kind = str(question.get("kind"))
            kind_counts[kind] += 1
            kind_by_origin[f"{origin}|{kind}"] += 1
            if domain in taxonomy.DOMAINS:
                domain_kind[f"{domain}|{kind}"] += 1
                domain_lang[f"{domain}|{lang}"] += 1
            if origin == ORIGIN_SOURCE:
                source_question_total += 1
                source_key_counts[key] += 1
                origin_map[key] = origin
            else:
                taxonomy_question_total += 1
                key_counts[key] += 1
                canonical = taxonomy.QUESTION_KEY_ALIASES.get(key, key)
                origin_map[canonical] = origin
                if canonical in taxonomy.POL2_AXIS_KEYS:
                    axes_asked[canonical[len("issue_"):]] += 1

        for raw_key, value in (item.get("targets") or {}).items():
            raw_text = str(raw_key)
            canonical = (raw_text if origin_map.get(raw_text) == ORIGIN_SOURCE
                         else taxonomy.QUESTION_KEY_ALIASES.get(raw_text, raw_text))
            if origin_map.get(canonical) != ORIGIN_TAXONOMY:
                continue
            if canonical in taxonomy.POL2_AXIS_KEYS and isinstance(value, dict) and value:
                axes_answered[canonical[len("issue_"):]] += 1
            if canonical == "mitigation" and isinstance(value, dict):
                mitigation_counts[str(value.get("answer"))] += 1
            if canonical == "love_language" and isinstance(value, dict):
                love_language_counts[str(value.get("answer"))] += 1

        errors = item_errors(item)
        if errors:
            issue_total += len(errors)
            for message in errors:
                issue_counts[message] += 1
                if message not in issue_examples and len(issue_examples) < MAX_DISTINCT_MESSAGES:
                    issue_examples[message] = f"item[{index}] id={item_id}"

    checks: list[dict] = []
    violations: list[str] = []
    gaps: dict = {"total_shortfall": 0, "domains": {}, "sources_over_share": {}}
    skipped = f"未启用（profile={profile}；需命令行显式给出阈值）"
    skipped_origin = f"未启用（profile={profile} 不要求）"

    if total == 0:
        violations.append("条目数为 0：任何产物都必须非空")
    checks.append({"id": "non_empty", "enforced": True, "ok": total > 0,
                   "actual": total, "required": ">= 1", "detail": "非空"})

    checks.append({"id": "total", "enforced": enforce_total,
                   "ok": (not enforce_total) or total >= min_total,
                   "actual": total,
                   "required": f">= {min_total}" if enforce_total else skipped,
                   "detail": "总量"})
    if enforce_total and total < min_total:
        gaps["total_shortfall"] = min_total - total
        violations.append(f"总量 {total} < 下限 {min_total}（缺 {min_total - total}）")

    for domain in taxonomy.DOMAINS:
        count = domain_counts.get(domain, 0)
        required = per_domain_min[domain]
        checks.append({"id": f"domain:{domain}", "enforced": enforce_domains,
                       "ok": (not enforce_domains) or count >= required,
                       "actual": count,
                       "required": f">= {required}" if enforce_domains else skipped,
                       "detail": f"覆盖域 {domain}"})
        if enforce_domains and count < required:
            gaps["domains"][domain] = required - count
            violations.append(f"覆盖域 {domain} 只有 {count} 条 < 下限 {required}（缺 {required - count}）")

    checks.append({"id": "origin_declared", "enforced": require_origin,
                   "ok": (not require_origin) or origin_missing == 0,
                   "actual": origin_missing,
                   "required": f"= 0（合法值 {list(ORIGINS)}）" if require_origin else skipped_origin,
                   "detail": "每道题显式声明 origin"})
    if require_origin and origin_missing:
        violations.append(f"档位要求每道题显式声明 origin：{origin_missing} 道题缺失或取值非法"
                          f"（合法值 {list(ORIGINS)}）")

    if unknown_domains:
        violations.append("存在未知覆盖域：" + "、".join(
            f"{name}×{count}" for name, count in unknown_domains.most_common()))

    if duplicates:
        unique = sorted(set(duplicates))
        violations.append(f"存在 {len(duplicates)} 条重复 id（{len(unique)} 个）："
                          + "、".join(unique[:5]) + ("…" if len(unique) > 5 else ""))

    if total:
        worst = source_counts.most_common(1)[0]
        top_source, top_count = worst[0], worst[1]
    else:
        top_source, top_count = "", 0
    top_share = (top_count / total) if total else 0.0
    checks.append({"id": "max_source_share", "enforced": enforce_share,
                   "ok": (not enforce_share) or top_share <= max_source_share + 1e-9,
                   "actual": round(top_share, 6),
                   "required": f"<= {max_source_share}" if enforce_share else skipped,
                   "detail": f"最大单一来源 {top_source or '(none)'}"})
    over = {name: round(count / total, 6) for name, count in source_counts.items()
            if total and count / total > max_source_share + 1e-9}
    if enforce_share and over:
        gaps["sources_over_share"] = over
        for name, share in sorted(over.items(), key=lambda kv: -kv[1]):
            violations.append(f"单一来源 {name} 占 {share:.1%}，超过上限 {max_source_share:.0%}"
                              f"（需降到 {int(total * max_source_share)} 条以下）")

    axes_missing = [axis for axis in (key[len("issue_"):] for key in taxonomy.POL2_AXIS_KEYS)
                    if not axes_asked.get(axis)]
    warnings: list[str] = []
    if taxonomy_question_total and axes_missing:
        warnings.append(f"PoL2 判定轴有 {len(axes_missing)} 条没有任何条目提问："
                        + "、".join(axes_missing)
                        + "（pol2_axis 条目应按涉及范围带上对应 issue_* 键）")
    if source_question_total:
        warnings.append(f"origin=source 的原生问题键 {len(source_key_counts)} 个 / "
                        f"{source_question_total} 次：不在 taxonomy 词表内属正常，不计入 taxonomy 覆盖率")
    if issue_total:
        warnings.append(f"schema 警告共 {issue_total} 条（{len(issue_counts)} 类），"
                        "加 --strict 可让它失败")

    report = {
        "schema": SCHEMA,
        "items_file": str(items_file) if items_file else None,
        "items": total,
        "questions": question_total,
        "taxonomy": taxonomy.summary(),
        "profile": profile,
        "origin": {
            "questions": dict(origin_counts.most_common()),
            "missing_or_invalid": origin_missing,
            "source_questions": source_question_total,
            "taxonomy_questions": taxonomy_question_total,
            "source_keys_distinct": len(source_key_counts),
        },
        "distributions": {
            "domain": _dist(domain_counts, total),
            "kind": _dist(kind_counts, question_total),
            "lang": _dist(lang_counts, total),
            "source.dataset": _dist(source_counts, total),
            "question_key": _dist(key_counts, taxonomy_question_total),
            "question_key_source": _dist(source_key_counts, source_question_total),
            "kind_by_origin": dict(sorted(kind_by_origin.items(), key=lambda kv: (-kv[1], kv[0]))),
            "domain_x_kind": dict(sorted(domain_kind.items(), key=lambda kv: (-kv[1], kv[0]))),
            "domain_x_lang": dict(sorted(domain_lang.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "pol2_axis": {
            "axes_asked": {axis: axes_asked.get(axis, 0) for axis in
                           (key[len("issue_"):] for key in taxonomy.POL2_AXIS_KEYS)},
            "axes_answered": {axis: axes_answered.get(axis, 0) for axis in
                              (key[len("issue_"):] for key in taxonomy.POL2_AXIS_KEYS)},
            "axes_missing": axes_missing,
            "mitigation_answers": dict(mitigation_counts.most_common()),
            "love_language_answers": dict(love_language_counts.most_common()),
        },
        "quotas": {
            "profile": profile,
            "min_total": min_total,
            "min_per_domain": min_per_domain,
            "per_domain": per_domain_min,
            "max_source_share": max_source_share,
            "origin": dict(meta.get("origin") or {}),
            "status": meta.get("status", "explicit"),
            "source_file": meta.get("source_file"),
            "notes": list(meta.get("notes") or []),
            "enforce": {
                "total": enforce_total,
                "domains": enforce_domains,
                "source_share": enforce_share,
                "require_origin": require_origin,
            },
            "source_shares": _share(source_counts, total),
            "checks": checks,
            "violations": violations,
        },
        "gaps": gaps,
        "unknown_domains": dict(unknown_domains.most_common()),
        "duplicate_ids": sorted(set(duplicates)),
        "schema_issues": {
            "total": issue_total,
            "distinct": len(issue_counts),
            "counts": dict(issue_counts.most_common(MAX_DISTINCT_MESSAGES)),
            "examples": issue_examples,
        },
        "warnings": warnings,
        "ok": not violations,
    }
    return report


def format_report(report: dict, *, top: int = 40) -> str:
    """人类可读的文本报告。"""
    lines: list[str] = []
    profile = report.get("profile") or report["quotas"].get("profile", DEFAULT_PROFILE)
    lines.append(f"decision-base 覆盖报告  schema={report['schema']}  profile={profile}")
    origin_info = report.get("origin") or {}
    lines.append(f"items: {report['items']}  问题数: {report['questions']}"
                 f"（source {origin_info.get('source_questions', 0)} / "
                 f"taxonomy {origin_info.get('taxonomy_questions', 0)}）"
                 f"  file: {report['items_file']}")
    summary = report["taxonomy"]
    kinds = " / ".join(f"{kind} {count}" for kind, count in summary["key_kinds"].items())
    lines.append(f"taxonomy: {summary['schema']}  {len(summary['domains'])} 域 / "
                 f"{summary['keys']} 键（{kinds}）")
    lines.append("")

    def section(title: str, dist: dict, note: str = "", limit: int | None = None) -> None:
        lines.append(f"[{title}]{('  ' + note) if note else ''}")
        if not dist:
            lines.append("  (空)")
        rows = list(dist.items())
        shown = rows if limit is None else rows[:limit]
        for name, row in shown:
            display = str(name).replace("\r", "").replace("\n", "\\n")
            if len(display) > 48:
                display = display[:45] + "…"
            lines.append(f"  {display:<34} {row['count']:>7}  {row['share']:>7.2%}")
        if limit is not None and len(rows) > limit:
            lines.append(f"  ... 其余 {len(rows) - limit} 项见 --json-out")
        lines.append("")

    distributions = report["distributions"]
    enforce = report["quotas"].get("enforce") or {}
    domain_note = (f"每域下限 {report['quotas']['min_per_domain']}"
                   if enforce.get("domains", True) else
                   f"每域下限未启用（profile={profile}）")
    share_note = (f"单一来源上限 {report['quotas']['max_source_share']:.0%}"
                  if enforce.get("source_share", True) else
                  f"单一来源上限未启用（profile={profile}）")
    section("domain", distributions["domain"], domain_note)
    origin_counts = origin_info.get("questions") or {}
    total_questions = report["questions"] or 1
    section("出题方 origin", {name: {"count": count, "share": round(count / total_questions, 6)}
                               for name, count in origin_counts.items()},
            f"缺失或非法 origin {origin_info.get('missing_or_invalid', 0)} 道")
    section("原语 kind", distributions["kind"], "占全部问题数的比例")
    section("lang", distributions["lang"])
    section("source.dataset", distributions["source.dataset"], share_note)
    section("问题键 question_key（taxonomy 出题）", distributions["question_key"], limit=top)
    source_keys = distributions.get("question_key_source") or {}
    if source_keys:
        section(f"问题键 source 原生（共 {len(source_keys)} 个）", source_keys, limit=top)

    axis = report["pol2_axis"]
    covered = sum(1 for count in axis["axes_asked"].values() if count)
    lines.append(f"[pol2_axis] 15 条判定轴被提问 {covered}/15"
                 f"（被作答 {sum(1 for c in axis['axes_answered'].values() if c)}/15）")
    for name, count in axis["axes_asked"].items():
        mark = " " if count else "!"
        lines.append(f"  {mark} issue_{name:<38} {count:>7}")
    lines.append("")

    quotas = report["quotas"]
    origin = quotas.get("origin") or {}
    origin_text = "，".join(f"{field}={QUOTA_ORIGIN_LABELS.get(source, source)}"
                            for field, source in origin.items())
    lines.append(f"[配额校验] 配额来源：{quotas.get('status', 'explicit')}"
                 + (f"  file={quotas['source_file']}" if quotas.get("source_file") else ""))
    if origin_text:
        lines.append(f"  逐字段来源：{origin_text}")
    for note in quotas.get("notes") or []:
        lines.append(f"  注：{note}")
    for check in report["quotas"]["checks"]:
        if not check.get("enforced", True):
            mark = "--"
        else:
            mark = "OK" if check["ok"] else "NG"
        lines.append(f"  [{mark}] {check['detail']}: {check['actual']} （要求 {check['required']}）")
    lines.append("")
    if report["quotas"]["violations"]:
        lines.append("[不通过] " + str(len(report["quotas"]["violations"])) + " 项：")
        for violation in report["quotas"]["violations"]:
            lines.append(f"  - {violation}")
        gaps = report["gaps"]
        if gaps["total_shortfall"]:
            lines.append(f"  总量缺口：{gaps['total_shortfall']}")
        for domain, shortfall in gaps["domains"].items():
            lines.append(f"  {domain} 缺口：{shortfall}")
    elif enforce.get("total", True) and enforce.get("domains", True) \
            and enforce.get("source_share", True):
        lines.append("[通过] 总量、每域下限、单一来源占比均达标")
    else:
        lines.append(f"[通过] profile={profile}：只判定启用的检查"
                     "（非空 / domain 合法 / id 唯一 / origin 显式），未启用的全量阈值不参与）")
    lines.append("")
    issues = report["schema_issues"]
    if issues["total"]:
        lines.append(f"[schema 警告] {issues['total']} 条 / {issues['distinct']} 类（默认不拦截，--strict 才失败）")
        for message, count in list(issues["counts"].items())[:15]:
            lines.append(f"  - ×{count} {message}   例：{issues['examples'].get(message, '')}")
        if issues["distinct"] > 15:
            lines.append(f"  ... 其余 {issues['distinct'] - 15} 类见 --json-out")
    else:
        lines.append("[schema 警告] 无")
    return "\n".join(lines)


def parse_domain_min(values) -> dict:
    """解析 --domain-min DOMAIN=N（可重复）。"""
    result: dict[str, int] = {}
    for value in values or []:
        name, sep, raw = str(value).partition("=")
        if not sep or name not in taxonomy.DOMAINS:
            raise ValueError(f"--domain-min 需要 DOMAIN=N，DOMAIN 必须是 {list(taxonomy.DOMAINS)}，收到 {value!r}")
        try:
            result[name] = int(raw)
        except ValueError as exc:
            raise ValueError(f"--domain-min {value!r} 的 N 不是整数") from exc
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="decision-base 覆盖报告与配额校验")
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS,
                        help=f"items.jsonl 路径（默认 {DEFAULT_ITEMS}）")
    parser.add_argument("--profile", choices=sorted(PROFILES), default=DEFAULT_PROFILE,
                        help="产物档位：full=全量配额（默认）；subset=子集只校验自身一致性"
                             "（非空/域合法/id 唯一/origin 显式），全量阈值需命令行显式给出")
    parser.add_argument("--sources", type=Path, default=SOURCES_PATH,
                        help=f"配额来源 sources.json（默认 {SOURCES_PATH}）")
    parser.add_argument("--no-sources", action="store_true",
                        help="忽略 sources.json，只用 README 硬阈值")
    parser.add_argument("--min-total", type=int, default=None,
                        help=f"覆盖总量下限（默认 sources.json 或 README {DEFAULT_MIN_TOTAL}）")
    parser.add_argument("--min-per-domain", type=int, default=None,
                        help=f"覆盖每域下限（默认 sources.json 或 README {DEFAULT_MIN_PER_DOMAIN}；"
                             f"显式给出时默认例外 pol2_axis={DEFAULT_DOMAIN_MIN['pol2_axis']} 不自动生效）")
    parser.add_argument("--domain-min", action="append", default=[], metavar="DOMAIN=N",
                        help="单个域的配额下限例外（可重复）")
    parser.add_argument("--max-source-share", type=float, default=None,
                        help=f"覆盖单一来源占比上限（默认 sources.json 或 README {DEFAULT_MAX_SOURCE_SHARE}）")
    parser.add_argument("--json-out", type=Path, help="把完整报告写成 JSON")
    parser.add_argument("--top", type=int, default=40, help="文本报告里问题键分布显示前 N 项")
    parser.add_argument("--strict", action="store_true", help="schema 警告也计为失败")
    parser.add_argument("--quiet", action="store_true", help="不打印文本报告（仍写 --json-out）")
    args = parser.parse_args(argv)

    if args.max_source_share is not None and not 0.0 <= args.max_source_share <= 1.0:
        print(f"参数错误：--max-source-share 必须在 [0,1]，收到 {args.max_source_share}", file=sys.stderr)
        return 2
    for flag, value in (("--min-total", args.min_total), ("--min-per-domain", args.min_per_domain)):
        if value is not None and value < 0:
            print(f"参数错误：{flag} 必须是非负整数，收到 {value}", file=sys.stderr)
            return 2
    try:
        domain_min = parse_domain_min(args.domain_min)
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2

    if not args.items.is_file():
        print(f"items 文件不存在：{args.items}（先跑 fetch.py/convert.py 产出 items.jsonl）", file=sys.stderr)
        return 2
    try:
        items = read_items(args.items)
    except ItemsError as exc:
        print(f"items 读取失败：{exc}", file=sys.stderr)
        return 2

    resolved = resolve_quotas(sources_path=args.sources, use_sources=not args.no_sources,
                              min_total=args.min_total, min_per_domain=args.min_per_domain,
                              max_source_share=args.max_source_share, profile=args.profile,
                              domain_min=(domain_min if domain_min or args.domain_min else None))
    report = build_report(items, items_file=args.items, min_total=resolved["min_total"],
                          min_per_domain=resolved["min_per_domain"],
                          domain_min=resolved["domain_min"], quota_meta=resolved,
                          max_source_share=resolved["max_source_share"])
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    if not args.quiet:
        print(format_report(report, top=args.top))

    failed = bool(report["quotas"]["violations"])
    if args.strict and report["schema_issues"]["total"]:
        failed = True
        print(f"--strict：{report['schema_issues']['total']} 条 schema 警告计为失败", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    # 管道/重定向时 Python 默认用系统 locale 编码（本机 cp936），中文报告会变成不可复现的字节；
    # 统一按 UTF-8 输出：控制台（isatty）与文件/管道都能正确解出中文。测试直接调 main()，不走这里。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
