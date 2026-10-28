"""把 aggregate.py 的 aggregate JSON 渲染成结果卡用的 Markdown 表格（纯标准库，离线）。

输入：benchmark/kev_prefix/aggregate.py --out 生成的 aggregate JSON。
输出：stdout 上的 Markdown 表格片段；--format json 输出 {table_name: rows}，
      每个 row 是 {列名: 已格式化字符串}，格式与 Markdown 单元一致（缺失为 U+2014）。

    python benchmark/kev_prefix/report_tables.py --aggregate <仓库外>/aggregate.json
    python benchmark/kev_prefix/report_tables.py --aggregate ... --section paired --format json

口径：
- 缺失/不可用字段显示 "—"（不会伪装成 0）；
- 比例 4 位小数；n 为整数；延迟 2 位小数；
- 配对差值带 +/− 号（负号用 ASCII "-" 以兼容 GBK 控制台），95% CI 单独一列；
- 只读 aggregate JSON，不接触逐例数据、不联网、不依赖第三方库。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

MISSING = "\u2014"          # em dash：缺失/不可用
SECTION_ORDER = ("main", "calibration", "strata", "paired", "variants", "latency")
SECTION_TABLES = {
    "main": ("main_served", "main_raw_t1"),
    "calibration": ("calibration",),
    "strata": ("strata_kind", "strata_lang", "strata_domain",
               "strata_option_bucket", "strata_state_chars"),
    "paired": ("paired_served", "paired_raw_t1"),
    "variants": ("variants",),
    "latency": ("latency",),
}
STRATA_FIELDS = (("kind", "by_kind"), ("lang", "by_lang"), ("domain", "by_domain"),
                 ("option_bucket", "by_option_bucket"), ("state_chars", "by_state_chars"))
PAIRED_METRICS = ("acc", "nll", "brier", "ece_10")
OPTION_BUCKET_ORDER = ("2", "3-4", "5-8", "9-26", ">26")
STATE_CHAR_ORDER = ("<=400", "401-1200", "1201-3000", ">3000")
LATENCY_DECIMALS = 2
RATIO_DECIMALS = 4


# ----------------------------------------------------------------------------- 取值与格式化

def _mapping(value):
    """只接受 dict；其余一律当成缺失（绝不把 None/列表当成指标）。"""
    return value if isinstance(value, dict) else {}


def _lookup(container, *path):
    """沿 path 取 dict；任一层缺失都返回 {}，便于统一格式化。"""
    current = container
    for key in path:
        current = _mapping(current).get(key)
    return _mapping(current)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def fmt_int(value):
    if not _is_number(value):
        return MISSING
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def fmt_ratio(value, decimals=RATIO_DECIMALS):
    if not _is_number(value):
        return MISSING
    return f"{value:.{decimals}f}"


def fmt_signed(value, decimals=RATIO_DECIMALS):
    """配对差值：正数带 +，负数带 -；零也带 +，以显示比较方向。"""
    if not _is_number(value):
        return MISSING
    if value < 0:
        return f"-{abs(value):.{decimals}f}"
    return f"+{value:.{decimals}f}"


def fmt_ci(ci):
    """ci95: [low, high] -> "[low, high]"；缺任一端都显示缺失。"""
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        return MISSING
    low, high = ci
    if not (_is_number(low) and _is_number(high)):
        return MISSING
    return f"[{fmt_signed(low)}, {fmt_signed(high)}]"


def fmt_latency(value):
    return fmt_ratio(value, LATENCY_DECIMALS)


def _compact_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if _is_number(value):
        if float(value).is_integer():
            return str(int(value))
        return f"{value:g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return str(value)


def fmt_compact(value):
    """把 coverage/dropped 等小对象压成 "k=v, ..."；缺失用 —，空 dict 用 {}。"""
    if value is None:
        return MISSING
    if isinstance(value, dict):
        if not value:
            return "{}"
        return ", ".join(f"{key}={_compact_scalar(value[key])}" for key in sorted(value, key=str))
    return _compact_scalar(value)


def md_cell(value):
    """Markdown 表格单元：转义竖线并压掉换行。"""
    text = MISSING if value is None else str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


# ----------------------------------------------------------------------------- 表格构造

def _table(name, section, title, columns, rows):
    return {"name": name, "section": section, "title": title,
            "columns": tuple(columns), "rows": tuple(rows)}


def _main_tables(aggregate):
    runs = _mapping(aggregate.get("runs"))
    served_columns = (
        ("run", "run", "left"),
        ("n", "n（样本量）", "right"),
        ("acc", "acc", "right"),
        ("brier", "brier", "right"),
        ("nll", "nll", "right"),
        ("ece_10", "ece_10", "right"),
        ("ece_15", "ece_15", "right"),
        ("coverage_at_5pct_error", "coverage@5%err", "right"),
        ("aurc", "aurc", "right"),
    )
    raw_columns = (
        ("run", "run", "left"),
        ("n", "n（样本量）", "right"),
        ("acc", "acc", "right"),
        ("brier", "brier", "right"),
        ("nll", "nll", "right"),
        ("ece_15", "ece_15", "right"),
    )
    served_rows, raw_rows = [], []
    for name, run in runs.items():
        run = _mapping(run)
        served = _lookup(run, "served", "overall")
        served_rows.append({
            "run": str(name),
            "n": fmt_int(served.get("n")),
            "acc": fmt_ratio(served.get("acc")),
            "brier": fmt_ratio(served.get("brier")),
            "nll": fmt_ratio(served.get("nll")),
            "ece_10": fmt_ratio(served.get("ece_10")),
            "ece_15": fmt_ratio(served.get("ece_15")),
            "coverage_at_5pct_error": fmt_ratio(served.get("coverage_at_5pct_error")),
            "aurc": fmt_ratio(served.get("aurc")),
        })
        raw = _lookup(run, "raw_t1", "overall")
        raw_rows.append({
            "run": str(name),
            "n": fmt_int(raw.get("n")),
            "acc": fmt_ratio(raw.get("acc")),
            "brier": fmt_ratio(raw.get("brier")),
            "nll": fmt_ratio(raw.get("nll")),
            "ece_15": fmt_ratio(raw.get("ece_15")),
        })
    return [
        _table("main_served", "main", "served 主指标", served_columns, served_rows),
        _table("main_raw_t1", "main", "raw_t1 主指标（T=1）", raw_columns, raw_rows),
    ]


def _calibration_tables(aggregate):
    runs = _mapping(aggregate.get("runs"))
    columns = (
        ("run", "run", "left"),
        ("mode", "mode", "left"),
        ("n", "n（样本量）", "right"),
        ("mean_conf", "mean_conf", "right"),
        ("confident_error_rate", "confident_error_rate", "right"),
        ("coverage_at_5pct_error", "coverage@5%err", "right"),
        ("ece_10", "ece_10", "right"),
        ("ece_15", "ece_15", "right"),
    )
    rows = []
    for name, run in runs.items():
        run = _mapping(run)
        for mode in ("served", "raw_t1"):
            metrics = _lookup(run, mode, "overall")
            rows.append({
                "run": str(name),
                "mode": mode,
                "n": fmt_int(metrics.get("n")),
                "mean_conf": fmt_ratio(metrics.get("mean_conf")),
                "confident_error_rate": fmt_ratio(metrics.get("confident_error_rate")),
                "coverage_at_5pct_error": fmt_ratio(metrics.get("coverage_at_5pct_error")),
                "ece_10": fmt_ratio(metrics.get("ece_10")),
                "ece_15": fmt_ratio(metrics.get("ece_15")),
            })
    return [_table("calibration", "calibration", "served vs raw_t1 校准", columns, rows)]


def _bucket_order(field, buckets):
    canonical = {"option_bucket": OPTION_BUCKET_ORDER, "state_chars": STATE_CHAR_ORDER}.get(field)
    if canonical is None:
        return sorted(buckets)
    known = [bucket for bucket in canonical if bucket in buckets]
    extra = sorted(bucket for bucket in buckets if bucket not in canonical)
    return known + extra


def _strata_tables(aggregate):
    runs = _mapping(aggregate.get("runs"))
    tables = []
    for field, key in STRATA_FIELDS:
        grouped = {name: _lookup(_mapping(run), "served", key) for name, run in runs.items()}
        buckets = set()
        for groups in grouped.values():
            buckets.update(str(bucket) for bucket in groups)
        columns = [("bucket", "bucket", "left")]
        for name in runs:
            columns.extend((
                (f"{name} n", f"{name} n", "right"),
                (f"{name} acc", f"{name} acc", "right"),
                (f"{name} ece_15", f"{name} ece_15", "right"),
            ))
        rows = []
        for bucket in _bucket_order(field, buckets):
            row = {"bucket": bucket}
            for name, groups in grouped.items():
                metrics = _mapping(groups.get(bucket))
                row[f"{name} n"] = fmt_int(metrics.get("n"))
                row[f"{name} acc"] = fmt_ratio(metrics.get("acc"))
                row[f"{name} ece_15"] = fmt_ratio(metrics.get("ece_15"))
            rows.append(row)
        tables.append(_table(f"strata_{field}", "strata", f"分层 · {field}（served）", columns, rows))
    return tables


def _paired_tables(aggregate):
    paired = _mapping(aggregate.get("paired"))
    tables = []
    for mode in ("served", "raw_t1"):
        columns = [
            ("comparison", "comparison", "left"),
            ("n_pairs", "n_pairs", "right"),
        ]
        for metric in PAIRED_METRICS:
            columns.append((f"{metric}_delta", f"Δ {metric}", "right"))
            columns.append((f"{metric}_ci95", f"{metric} 95% CI", "left"))
        rows = []
        for comparison_name, comparison in paired.items():
            block = _lookup(comparison, mode)
            row = {"comparison": str(comparison_name), "n_pairs": fmt_int(block.get("n_pairs"))}
            deltas = _mapping(block.get("deltas"))
            for metric in PAIRED_METRICS:
                entry = _mapping(deltas.get(metric))
                row[f"{metric}_delta"] = fmt_signed(entry.get("delta"))
                row[f"{metric}_ci95"] = fmt_ci(entry.get("ci95"))
            rows.append(row)
        title = "配对比较 · {0}（Δ = 模型 - reference）".format(mode)
        tables.append(_table(f"paired_{mode}", "paired", title, columns, rows))
    return tables


def _variant_tables(aggregate):
    runs = _mapping(aggregate.get("runs"))
    variants = _mapping(aggregate.get("variants"))
    columns = (
        ("run", "run", "left"),
        ("variant", "variant", "left"),
        ("n_pairs", "n_pairs", "right"),
        ("mean_max_delta", "mean_max_delta", "right"),
        ("max_max_delta", "max_max_delta", "right"),
        ("median_max_delta", "median_max_delta", "right"),
        ("flip_rate", "flip_rate", "right"),
        ("accuracy_unchanged_rate", "accuracy_unchanged_rate", "right"),
    )
    rows = []
    for name in runs:
        run_variants = _mapping(variants.get(name))
        for variant in ("permuted", "isolation"):
            stats = _mapping(run_variants.get(variant))
            rows.append({
                "run": str(name),
                "variant": variant,
                "n_pairs": fmt_int(stats.get("n_pairs")),
                "mean_max_delta": fmt_ratio(stats.get("mean_max_delta")),
                "max_max_delta": fmt_ratio(stats.get("max_max_delta")),
                "median_max_delta": fmt_ratio(stats.get("median_max_delta")),
                "flip_rate": fmt_ratio(stats.get("flip_rate")),
                "accuracy_unchanged_rate": fmt_ratio(stats.get("accuracy_unchanged_rate")),
            })
    return [_table("variants", "variants", "变体稳健性（permuted / isolation）", columns, rows)]


def _latency_value(latency, key):
    if not isinstance(latency, dict):
        return None
    value = latency.get(key)
    if value is None and key == "median":
        value = latency.get("p50")
    return value


def _latency_tables(aggregate):
    runs = _mapping(aggregate.get("runs"))
    columns = (
        ("run", "run", "left"),
        ("temperature", "temperature", "right"),
        ("latency_median_ms", "latency median (ms)", "right"),
        ("latency_p95_ms", "latency p95 (ms)", "right"),
        ("coverage_primary_questions", "coverage.primary_questions", "right"),
        ("coverage_dropped", "coverage.dropped", "left"),
        ("coverage_report", "report coverage", "left"),
    )
    rows = []
    for name, run in runs.items():
        run = _mapping(run)
        metadata = _mapping(run.get("run_metadata"))
        latency = metadata.get("latency_ms")
        if isinstance(latency, dict):
            median, p95 = _latency_value(latency, "median"), _latency_value(latency, "p95")
        elif _is_number(latency):
            median, p95 = latency, None
        else:
            median, p95 = None, None
        coverage = _mapping(run.get("coverage"))
        rows.append({
            "run": str(name),
            "temperature": fmt_ratio(metadata.get("temperature")),
            "latency_median_ms": fmt_latency(median),
            "latency_p95_ms": fmt_latency(p95),
            "coverage_primary_questions": fmt_int(coverage.get("primary_questions")),
            "coverage_dropped": fmt_compact(coverage.get("dropped")),
            "coverage_report": fmt_compact(metadata.get("coverage")),
        })
    return [_table("latency", "latency", "延迟与覆盖", columns, rows)]


def build_tables(aggregate):
    """返回 {table_name: table}；缺失字段保留为 —，缺失整节则表格无行。"""
    aggregate = _mapping(aggregate)
    tables = {}
    for table in (_main_tables(aggregate) + _calibration_tables(aggregate)
                  + _strata_tables(aggregate) + _paired_tables(aggregate)
                  + _variant_tables(aggregate) + _latency_tables(aggregate)):
        tables[table["name"]] = table
    return tables


def select_tables(tables, section="all"):
    """按 --section 过滤；all 保持完整顺序。"""
    if section == "all":
        return dict(tables)
    return {name: tables[name] for name in SECTION_TABLES[section] if name in tables}


# ----------------------------------------------------------------------------- 输出

def render_markdown(tables):
    if not tables:
        return ""
    lines = ["<!-- report_tables.py: — = missing; ratios 4 d.p.; Δ = model - reference; CI = 95% -->"]
    current = None
    for table in tables.values():
        if table["section"] != current:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"## {table['section']}")
            lines.append("")
            current = table["section"]
        lines.append(f"### {table['name']} · {table['title']}")
        lines.append("")
        lines.append("| " + " | ".join(md_cell(label) for _, label, _ in table["columns"]) + " |")
        lines.append("| " + " | ".join("---:" if align == "right" else "---"
                                         for _, _, align in table["columns"]) + " |")
        for row in table["rows"]:
            cells = [md_cell(row.get(key, MISSING)) for key, _, _ in table["columns"]]
            lines.append("| " + " | ".join(cells) + " |")
        if not table["rows"]:
            lines.append("")
            lines.append("_（无数据）_")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def tables_payload(tables):
    """--format json 的结构：{table_name: [row_dict, ...]}，单元为已格式化字符串。"""
    return {name: [dict(row) for row in table["rows"]] for name, table in tables.items()}


# ----------------------------------------------------------------------------- CLI

def load_aggregate(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path}: aggregate root must be a JSON object")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Render aggregate.py output as result-card Markdown tables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--aggregate", type=Path, required=True,
                        help="aggregate.py --out 生成的 aggregate JSON")
    parser.add_argument("--section", choices=("all",) + SECTION_ORDER, default="all",
                        help="只输出某一节（默认 all）")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown",
                        help="markdown 表格片段或 {table_name: rows}（默认 markdown）")
    args = parser.parse_args(argv)
    try:
        aggregate = load_aggregate(args.aggregate)
    except ValueError as error:
        print(f"report_tables.py: {error}", file=sys.stderr)
        return 2
    tables = select_tables(build_tables(aggregate), args.section)
    if args.format == "json":
        sys.stdout.write(json.dumps(tables_payload(tables), ensure_ascii=True, indent=2) + "\n")
    else:
        sys.stdout.write(render_markdown(tables))
    return 0


if __name__ == "__main__":
    sys.exit(main())
