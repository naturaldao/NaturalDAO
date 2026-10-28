"""把 jevbench eval 的报告 JSON 聚合成结果卡用的 Markdown 表 / JSON 摘要（纯标准库，离线）。

只输出聚合分数：报告里的逐测试 result.outcomes、逐 case 的 result.bases
和 result.errors 明细不会被复制到输出，只取计数与汇总字段。

CLI
---
    python benchmark/kev_prefix/jevbench_summary.py \
        --report name=<path> [--report ...] \
        [--out <path>] [--format markdown|json] [--reference <name>]

- 默认把 Markdown 写到 stdout；--out 总是额外写一份 JSON 摘要。
- --format json 时 stdout 也输出同一份 JSON（仍然只在存在 --out 时落盘）。
- 默认差值是相邻模型（后 - 前）；给 --reference 时所有其它模型都相对它。
- 缺失字段一律显示 U+2014（—），不补 0。

实跑 schema（jevbench 0.1.0）
----------------------------
样例命令（fake backend，无网络、无 GPU）：

    ~/src/polgov/jevbench-venv/bin/jevbench eval \
        --backend fake:coherent --suite examples --out /tmp/jev-sample.json

顶层键恰好是 5 个：

    {
      "jevbench_report": 1,                # 报告格式版本（int）
      "name": "fake:coherent",             # backend 或 --name
      "settings": {
        "tolerance": 0.05, "min_n": 1,
        "bootstrap": 1000, "min_coverage": 0.95
      },
      "scores": { ... },                   # 聚合结果（下面是真实键）
      "result": { ... }                    # 原始运行记录（含逐例 outcomes）
    }

scores 的结构（examples v2 实跑，50 个 relation）：

    backend: str
    environment: {python: str, httpx: str}
    tolerance: "fixed 0.05" | "per-run"
    min_n: int
    overall: float | null                  # 五维等权；不完整时为 null
    pillars: {REP, BAT, MEA, LOG, CHO: float | null}
    groups: {"REP.invariance": float | null, ...}       # 11 个
    relations: {<50 个 relation 名>: float | null}
    graded: {relations, groups, pillars, overall}       # 同样结构，连续分
    ci: {} | {"overall": [lo, hi], "graded_overall": [lo, hi]}
                                           # 只在 n_cases > 1 且 bootstrap > 0 时存在
    n_cases: int
    bootstrap: int
    checks: {"<relation>/<check>": {n, score, graded, planned, coverage[, excluded]}}
    incomplete: [str]                      # 被拒/无效请求导致覆盖率不足的 relation
    min_coverage: float
    excluded: {low_n: [str], exploratory: [str], diagnostic: [str]}
    n_checks: int                          # 实际计分的 relation 数
    n_outcomes: int
    skipped_outcomes: int
    mean_repeat_noise: float | null

result 的结构（只列本脚本关心的与真实存在的键）：

    jevbench_version: "0.1.0"
    backend, environment, seed, repeats, trials,
    noise_multiplier, noise_floor, relations: [str], cases: [str],
    requests, cache_hits, backend_seconds, wall_seconds,
    planned_tests: {relation: int}, concurrency, truncated_by_budget,
    backend_down,
    bases: {case_id: {base: {变量: {取值: 概率}}, noise: {变量: float}}},
    outcomes: [ {relation, check, case_id, targets, deviation, tolerance,
                 flip, detail, tolerance_kind, violated, trial_id, variant}, ... ],
    errors: [ {case?, relation?, target?, error?}, ... ],
    suite: {name: str, version: str, files: {filename: sha256}, plan: str},
    case_domains: {case_id: domain}, selection: {...}

维度/关系/case 的对应关系：
- 维度：scores.pillars（五维）和 scores.groups（11 个组，键为 "DIM.group"）。
- 关系：scores.relations（50 个 relation 名）；每个 relation 的检验见
  scores.checks["<relation>/<check>"]；关系同时归到某个 group/pillar。
- case：result.outcomes[] 每条是一例检验（含 case_id），result.cases 是
  case id 列表，result.case_domains 给 case 的 domain，result.bases 给
  base 请求/噪声。本脚本不输出这些逐例内容。

0.1.0 的 scores 没有 accuracy 键（JevBench 测 coherence，不是 accuracy）；
如果上游合并报告提供 report.accuracy、scores.accuracy、
scores.metrics.accuracy 或 result.accuracy（数字，或含
value/accuracy/score/estimate/mean/overall 的 dict），本脚本会显示，否则为 —。
0.1.0 也没有时间戳：run_date 先找顶层或 result 里的
generated_at / created_at / timestamp / run_date，找不到才用文件 mtime。
错误数取 result.errors 的长度；键不存在时显示 —，空列表显示 0。

JSON 摘要结构
-------------
    {
      "schema": "jevbench-summary/1",
      "models": [{
        "name": "<CLI 标签>", "report_name": "...",
        "suite": "...", "suite_version": "...", "jevbench_version": "...",
        "run_date": "YYYY-MM-DD" | null,
        "errors": int | null,
        "overall": float | null,
        "pillars": {"REP": float | null, ...},
        "accuracy": float | null,
        "overall_ci": [lo, hi] | null,
        "min_n": int | null, "n_cases": int | null,
        "n_checks": int | null, "n_outcomes": int | null, "bootstrap": int | null
      }],
      "comparisons": [{
        "kind": "adjacent" | "reference",
        "model": "...", "reference": "...",
        "delta": {"overall": float | null, "REP": ..., ...}
      }]
    }

Markdown 的分数是 [0, 1] 区间的 4 位小数（1 = 无违反，不是 accuracy 百分比）；
差值带 +/- 号（模型 - 参照）；CI 是 overall 的 95% case bootstrap 区间。
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MISSING = "\u2014"
SCHEMA = "jevbench-summary/1"
REPORT_FORMAT = 1
PILLARS = ("REP", "BAT", "MEA", "LOG", "CHO")
RUN_DATE_KEYS = ("generated_at", "created_at", "timestamp", "run_date")
SUMMARY_COLUMNS = (
    ("model", "model", "left"),
    ("suite", "suite", "left"),
    ("version", "version", "left"),
    ("overall", "overall", "right"),
    ("REP", "REP", "right"),
    ("BAT", "BAT", "right"),
    ("MEA", "MEA", "right"),
    ("LOG", "LOG", "right"),
    ("CHO", "CHO", "right"),
    ("accuracy", "accuracy", "right"),
    ("ci", "95% CI", "left"),
    ("min_n", "min_n", "right"),
    ("cases", "cases", "right"),
)
DELTA_COLUMNS = (
    ("comparison", "comparison", "left"),
    ("overall", "overall", "right"),
    ("REP", "REP", "right"),
    ("BAT", "BAT", "right"),
    ("MEA", "MEA", "right"),
    ("LOG", "LOG", "right"),
    ("CHO", "CHO", "right"),
)
METADATA_COLUMNS = (
    ("model", "model", "left"),
    ("jevbench", "jevbench", "left"),
    ("suite", "suite", "left"),
    ("version", "version", "left"),
    ("run_date", "run date", "left"),
    ("errors", "errors", "right"),
)


class SummaryError(ValueError):
    """输入/参数错误；main() 统一转成 stderr + 退出码 2。"""


# --------------------------------------------------------------------- 取值

def _mapping(value):
    return value if isinstance(value, dict) else {}


def _number(value):
    """只接受有限的 int/float；bool、None、字符串、NaN/Inf 都当成缺失。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _integer(value):
    number = _number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _text(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _ci(value):
    """[lo, hi] / {low, high} / {ci: [lo, hi]} -> (lo, hi)；缺任一端就是缺失。"""
    if isinstance(value, dict):
        for key in ("ci", "ci95", "interval", "range"):
            if key in value:
                return _ci(value[key])
        low, high = _number(value.get("low")), _number(value.get("high"))
        if low is not None and high is not None:
            return (low, high)
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        low, high = _number(value[0]), _number(value[1])
        if low is not None and high is not None:
            return (low, high)
    return None


def _accuracy(report):
    """JevBench 0.1.0 没有 accuracy；兼容上游合并报告的可选字段。"""
    scores = _mapping(report.get("scores"))
    result = _mapping(report.get("result"))
    metrics = _mapping(scores.get("metrics"))
    candidates = (
        report.get("accuracy"),
        scores.get("accuracy"),
        metrics.get("accuracy"),
        result.get("accuracy"),
    )
    for candidate in candidates:
        if isinstance(candidate, dict):
            for key in ("value", "accuracy", "score", "estimate", "mean", "overall"):
                if key in candidate:
                    candidate = candidate[key]
                    break
            else:
                continue
        number = _number(candidate)
        if number is not None:
            return number
    return None


def _date_from_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        stamp = _number(value)
        if stamp is None or stamp <= 0:
            return None
        try:
            return datetime.fromtimestamp(stamp, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            match = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
            return match.group(1) if match else None
    return None


def _run_date(report, path):
    result = _mapping(report.get("result"))
    for container in (report, result):
        for key in RUN_DATE_KEYS:
            if key in container:
                date = _date_from_value(container[key])
                if date is not None:
                    return date
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    except OSError:
        return None


def _error_count(result):
    if "errors" not in result:
        return None
    errors = result["errors"]
    if isinstance(errors, list):
        return len(errors)
    return _integer(errors)


# --------------------------------------------------------------------- 模型

class ModelSummary:
    """一行模型汇总；所有字段都可能是 None（输出为 —）。"""

    def __init__(self, *, name, report_name, suite, suite_version, jevbench_version,
                 run_date, errors, overall, pillars, accuracy, overall_ci,
                 min_n, n_cases, n_checks, n_outcomes, bootstrap):
        self.name = name
        self.report_name = report_name
        self.suite = suite
        self.suite_version = suite_version
        self.jevbench_version = jevbench_version
        self.run_date = run_date
        self.errors = errors
        self.overall = overall
        self.pillars = pillars
        self.accuracy = accuracy
        self.overall_ci = overall_ci
        self.min_n = min_n
        self.n_cases = n_cases
        self.n_checks = n_checks
        self.n_outcomes = n_outcomes
        self.bootstrap = bootstrap

    def as_dict(self):
        return {
            "name": self.name,
            "report_name": self.report_name,
            "suite": self.suite,
            "suite_version": self.suite_version,
            "jevbench_version": self.jevbench_version,
            "run_date": self.run_date,
            "errors": self.errors,
            "overall": self.overall,
            "pillars": {pillar: self.pillars.get(pillar) for pillar in PILLARS},
            "accuracy": self.accuracy,
            "overall_ci": list(self.overall_ci) if self.overall_ci is not None else None,
            "min_n": self.min_n,
            "n_cases": self.n_cases,
            "n_checks": self.n_checks,
            "n_outcomes": self.n_outcomes,
            "bootstrap": self.bootstrap,
        }


def load_report(name, path):
    """读一份 jevbench eval 报告；只抽取汇总字段。"""
    path = Path(path)
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SummaryError(f"cannot read {path}: {error}") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SummaryError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(data, dict):
        raise SummaryError(f"{path}: report root must be a JSON object")
    if "jevbench_report" not in data:
        raise SummaryError(f"{path}: not a jevbench report (missing jevbench_report)")
    version = data.get("jevbench_report")
    if isinstance(version, bool) or version != REPORT_FORMAT:
        raise SummaryError(
            f"{path}: unsupported jevbench_report format {version!r}; expected {REPORT_FORMAT}"
        )
    scores = data.get("scores")
    result = data.get("result")
    if not isinstance(scores, dict) or not isinstance(result, dict):
        raise SummaryError(f"{path}: missing scores/result objects")

    settings = _mapping(data.get("settings"))
    pillar_values = _mapping(scores.get("pillars"))
    suite = _mapping(result.get("suite"))
    ci = _ci(_mapping(scores.get("ci")).get("overall"))
    min_n = _integer(scores.get("min_n"))
    if min_n is None:
        min_n = _integer(settings.get("min_n"))
    bootstrap = _integer(scores.get("bootstrap"))
    if bootstrap is None:
        bootstrap = _integer(settings.get("bootstrap"))

    return ModelSummary(
        name=name,
        report_name=_text(data.get("name")),
        suite=_text(suite.get("name")),
        suite_version=_text(suite.get("version")),
        jevbench_version=_text(result.get("jevbench_version")),
        run_date=_run_date(data, path),
        errors=_error_count(result),
        overall=_number(scores.get("overall")),
        pillars={pillar: _number(pillar_values.get(pillar)) for pillar in PILLARS},
        accuracy=_accuracy(data),
        overall_ci=ci,
        min_n=min_n,
        n_cases=_integer(scores.get("n_cases")),
        n_checks=_integer(scores.get("n_checks")),
        n_outcomes=_integer(scores.get("n_outcomes")),
        bootstrap=bootstrap,
    )


def parse_report_specs(specs):
    parsed = []
    seen = set()
    for spec in specs:
        if "=" not in spec:
            raise SummaryError(f"--report must be NAME=PATH, got {spec!r}")
        name, raw_path = spec.split("=", 1)
        name, raw_path = name.strip(), raw_path.strip()
        if not name:
            raise SummaryError(f"--report has an empty name: {spec!r}")
        if not raw_path:
            raise SummaryError(f"--report has an empty path: {spec!r}")
        if name in seen:
            raise SummaryError(f"duplicate report name: {name}")
        seen.add(name)
        parsed.append((name, Path(raw_path).expanduser()))
    if not parsed:
        raise SummaryError("at least one --report is required")
    return parsed


# --------------------------------------------------------------------- 差值

def _difference(model_value, reference_value):
    if model_value is None or reference_value is None:
        return None
    return model_value - reference_value


def _comparison(kind, model, reference):
    return {
        "kind": kind,
        "model": model.name,
        "reference": reference.name,
        "delta": {
            "overall": _difference(model.overall, reference.overall),
            **{
                pillar: _difference(model.pillars.get(pillar), reference.pillars.get(pillar))
                for pillar in PILLARS
            },
        },
    }


def build_comparisons(models, reference_name=None):
    if reference_name is not None:
        reference = next((model for model in models if model.name == reference_name), None)
        if reference is None:
            known = ", ".join(model.name for model in models)
            raise SummaryError(f"unknown --reference {reference_name!r}; known names: {known}")
        return [
            _comparison("reference", model, reference)
            for model in models
            if model.name != reference.name
        ]
    return [
        _comparison("adjacent", model, previous)
        for previous, model in zip(models, models[1:])
    ]


def build_payload(models, comparisons):
    return {
        "schema": SCHEMA,
        "models": [model.as_dict() for model in models],
        "comparisons": comparisons,
    }


# --------------------------------------------------------------------- 渲染

def _fmt_score(value):
    return MISSING if value is None else f"{value:.4f}"


def _fmt_int(value):
    return MISSING if value is None else str(value)


def _fmt_ci(ci):
    if ci is None:
        return MISSING
    return f"[{ci[0]:.4f}, {ci[1]:.4f}]"


def _fmt_delta(value):
    if value is None:
        return MISSING
    if abs(value) < 0.00005:
        value = 0.0
    return f"{value:+.4f}"


def _md_cell(value):
    text = MISSING if value is None else str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _render_table(columns, rows):
    lines = [
        "| " + " | ".join(_md_cell(label) for _, label, _ in columns) + " |",
        "| " + " | ".join("---:" if align == "right" else "---" for _, _, align in columns) + " |",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(_md_cell(row.get(key, MISSING)) for key, _, _ in columns) + " |"
        )
    return lines


def render_markdown(models, comparisons):
    lines = [
        "<!-- jevbench_summary.py: — = missing; scores are fractions 0..1 (1 = no violation), "
        "4 d.p.; delta = model - reference; CI = 95% bootstrap over cases -->",
        "",
        "## summary",
        "",
    ]
    summary_rows = []
    for model in models:
        summary_rows.append({
            "model": model.name,
            "suite": model.suite,
            "version": model.suite_version,
            "overall": _fmt_score(model.overall),
            "REP": _fmt_score(model.pillars.get("REP")),
            "BAT": _fmt_score(model.pillars.get("BAT")),
            "MEA": _fmt_score(model.pillars.get("MEA")),
            "LOG": _fmt_score(model.pillars.get("LOG")),
            "CHO": _fmt_score(model.pillars.get("CHO")),
            "accuracy": _fmt_score(model.accuracy),
            "ci": _fmt_ci(model.overall_ci),
            "min_n": _fmt_int(model.min_n),
            "cases": _fmt_int(model.n_cases),
        })
    lines.extend(_render_table(SUMMARY_COLUMNS, summary_rows))
    lines.extend(["", "## deltas", ""])
    if comparisons:
        delta_rows = []
        for comparison in comparisons:
            delta = comparison["delta"]
            delta_rows.append({
                "comparison": f"{comparison['model']} - {comparison['reference']}",
                "overall": _fmt_delta(delta.get("overall")),
                **{pillar: _fmt_delta(delta.get(pillar)) for pillar in PILLARS},
            })
        lines.extend(_render_table(DELTA_COLUMNS, delta_rows))
    else:
        lines.append("_（只有一个模型，无差值）_")
    lines.extend(["", "## metadata", ""])
    metadata_rows = []
    for model in models:
        metadata_rows.append({
            "model": model.name,
            "jevbench": model.jevbench_version,
            "suite": model.suite,
            "version": model.suite_version,
            "run_date": model.run_date,
            "errors": _fmt_int(model.errors),
        })
    lines.extend(_render_table(METADATA_COLUMNS, metadata_rows))
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------- 输出

def write_payload(path, payload):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        raise SummaryError(f"cannot write {path}: {error}") from error


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Aggregate jevbench eval reports into result-card Markdown/JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--report",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="one report per model; repeat for several models",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="also write the JSON summary here",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="stdout format (default: markdown)",
    )
    parser.add_argument(
        "--reference",
        metavar="NAME",
        help="compare every other model against this report name (default: adjacent pairs)",
    )
    args = parser.parse_args(argv)

    try:
        specs = parse_report_specs(args.report)
        models = [load_report(name, path) for name, path in specs]
        comparisons = build_comparisons(models, args.reference)
        payload = build_payload(models, comparisons)
        if args.out is not None:
            write_payload(args.out, payload)
    except SummaryError as error:
        print(f"jevbench_summary.py: {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        sys.stdout.write(json.dumps(payload, ensure_ascii=True, indent=2) + "\n")
    else:
        sys.stdout.write(render_markdown(models, comparisons))
    return 0


if __name__ == "__main__":
    sys.exit(main())
