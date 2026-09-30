"""decision-base 覆盖报告与配额校验。

用法：

    uv run --no-project --offline python datasets/decision-base/coverage.py --items datasets/decision-base/data/items.jsonl

输出：按 domain / source.dataset / 原语(kind) / lang / 问题键 的分布，PoL2 15 条判定轴的逐轴覆盖，
以及配额校验（总量 >= 10000、每域 >= 1200、单一来源 <= 40%）。

退出码：

- 0：通过（有问题但只是 schema 警告时仍为 0，除非加 --strict）
- 1：配额或硬性违规（未知 domain、重复 id、配额不达标），缺口会逐条列出
- 2：输入不可读（文件缺失、JSON 损坏、参数非法）

硬性违规与 schema 警告的分界：domain 必须在 taxonomy 内、id 不得重复，因为它们直接破坏配额口径；
其余 README 2.1 的字段问题（缺 source/meta 字段、键名/选项/答案不合法等）先记警告，--strict 时才算失败。
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
DEFAULT_MIN_TOTAL = 10_000
DEFAULT_MIN_PER_DOMAIN = 1_200
DEFAULT_MAX_SOURCE_SHARE = 0.40
MAX_DISTINCT_MESSAGES = 200


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
                 domain_min: dict | None = None) -> dict:
    """对已读入的条目做分布统计与配额校验，返回可 JSON 序列化的报告。"""
    total = len(items)
    per_domain_min = {domain: int((domain_min or {}).get(domain, min_per_domain))
                      for domain in taxonomy.DOMAINS}

    domain_counts: Counter = Counter()
    kind_counts: Counter = Counter()
    lang_counts: Counter = Counter()
    source_counts: Counter = Counter()
    key_counts: Counter = Counter()
    domain_kind: Counter = Counter()
    domain_lang: Counter = Counter()
    axes_asked: Counter = Counter()
    axes_answered: Counter = Counter()
    mitigation_counts: Counter = Counter()
    love_language_counts: Counter = Counter()

    question_total = 0
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

        for question in item.get("questions") or []:
            if not isinstance(question, dict):
                continue
            key = question.get("key")
            if not isinstance(key, str) or not key:
                continue
            key_counts[key] += 1
            question_total += 1
            kind = str(question.get("kind"))
            kind_counts[kind] += 1
            if domain in taxonomy.DOMAINS:
                domain_kind[f"{domain}|{kind}"] += 1
                domain_lang[f"{domain}|{lang}"] += 1
            try:
                canonical = taxonomy.resolve_key(key)
            except KeyError:
                continue
            if canonical in taxonomy.POL2_AXIS_KEYS:
                axes_asked[canonical[len("issue_"):]] += 1

        for raw_key, value in (item.get("targets") or {}).items():
            try:
                canonical = taxonomy.resolve_key(str(raw_key))
            except KeyError:
                continue
            if canonical in taxonomy.POL2_AXIS_KEYS and isinstance(value, dict) and value:
                axes_answered[canonical[len("issue_"):]] += 1
            if canonical == "mitigation" and isinstance(value, dict):
                mitigation_counts[str(value.get("answer"))] += 1
            if canonical == "love_language" and isinstance(value, dict):
                love_language_counts[str(value.get("answer"))] += 1

        errors = taxonomy.item_errors(item)
        if errors:
            issue_total += len(errors)
            for message in errors:
                issue_counts[message] += 1
                if message not in issue_examples and len(issue_examples) < MAX_DISTINCT_MESSAGES:
                    issue_examples[message] = f"item[{index}] id={item_id}"

    checks: list[dict] = []
    violations: list[str] = []
    gaps: dict = {"total_shortfall": 0, "domains": {}, "sources_over_share": {}}

    checks.append({"id": "total", "ok": total >= min_total,
                   "actual": total, "required": f">= {min_total}",
                   "detail": "总量"})
    if total < min_total:
        gaps["total_shortfall"] = min_total - total
        violations.append(f"总量 {total} < 下限 {min_total}（缺 {min_total - total}）")

    for domain in taxonomy.DOMAINS:
        count = domain_counts.get(domain, 0)
        required = per_domain_min[domain]
        checks.append({"id": f"domain:{domain}", "ok": count >= required,
                       "actual": count, "required": f">= {required}",
                       "detail": f"覆盖域 {domain}"})
        if count < required:
            gaps["domains"][domain] = required - count
            violations.append(f"覆盖域 {domain} 只有 {count} 条 < 下限 {required}（缺 {required - count}）")

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
    checks.append({"id": "max_source_share", "ok": top_share <= max_source_share + 1e-9,
                   "actual": round(top_share, 6), "required": f"<= {max_source_share}",
                   "detail": f"最大单一来源 {top_source or '(none)'}"})
    over = {name: round(count / total, 6) for name, count in source_counts.items()
            if total and count / total > max_source_share + 1e-9}
    if over:
        gaps["sources_over_share"] = over
        for name, share in sorted(over.items(), key=lambda kv: -kv[1]):
            violations.append(f"单一来源 {name} 占 {share:.1%}，超过上限 {max_source_share:.0%}"
                              f"（需降到 {int(total * max_source_share)} 条以下）")

    axes_missing = [axis for axis in (key[len("issue_"):] for key in taxonomy.POL2_AXIS_KEYS)
                    if not axes_asked.get(axis)]
    warnings: list[str] = []
    if total and axes_missing:
        warnings.append(f"PoL2 判定轴有 {len(axes_missing)} 条没有任何条目提问："
                        + "、".join(axes_missing)
                        + "（pol2_axis 条目应按涉及范围带上对应 issue_* 键）")
    if issue_total:
        warnings.append(f"schema 警告共 {issue_total} 条（{len(issue_counts)} 类），"
                        "加 --strict 可让它失败")

    report = {
        "schema": SCHEMA,
        "items_file": str(items_file) if items_file else None,
        "items": total,
        "questions": question_total,
        "taxonomy": taxonomy.summary(),
        "distributions": {
            "domain": _dist(domain_counts, total),
            "kind": _dist(kind_counts, question_total),
            "lang": _dist(lang_counts, total),
            "source.dataset": _dist(source_counts, total),
            "question_key": _dist(key_counts, question_total),
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
            "min_total": min_total,
            "min_per_domain": min_per_domain,
            "per_domain": per_domain_min,
            "max_source_share": max_source_share,
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
    lines.append(f"decision-base 覆盖报告  schema={report['schema']}")
    lines.append(f"items: {report['items']}  问题数: {report['questions']}  "
                 f"file: {report['items_file']}")
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
            lines.append(f"  {name:<34} {row['count']:>7}  {row['share']:>7.2%}")
        if limit is not None and len(rows) > limit:
            lines.append(f"  ... 其余 {len(rows) - limit} 项见 --json-out")
        lines.append("")

    distributions = report["distributions"]
    section("domain", distributions["domain"], f"每域下限 {report['quotas']['min_per_domain']}")
    section("原语 kind", distributions["kind"], "占全部问题数的比例")
    section("lang", distributions["lang"])
    section("source.dataset", distributions["source.dataset"],
            f"单一来源上限 {report['quotas']['max_source_share']:.0%}")
    section("问题键 question_key", distributions["question_key"], limit=top)

    axis = report["pol2_axis"]
    covered = sum(1 for count in axis["axes_asked"].values() if count)
    lines.append(f"[pol2_axis] 15 条判定轴被提问 {covered}/15"
                 f"（被作答 {sum(1 for c in axis['axes_answered'].values() if c)}/15）")
    for name, count in axis["axes_asked"].items():
        mark = " " if count else "!"
        lines.append(f"  {mark} issue_{name:<38} {count:>7}")
    lines.append("")

    lines.append("[配额校验]")
    for check in report["quotas"]["checks"]:
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
    else:
        lines.append("[通过] 总量、每域下限、单一来源占比均达标")
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
    parser.add_argument("--min-total", type=int, default=DEFAULT_MIN_TOTAL)
    parser.add_argument("--min-per-domain", type=int, default=DEFAULT_MIN_PER_DOMAIN)
    parser.add_argument("--domain-min", action="append", default=[], metavar="DOMAIN=N",
                        help="单个域的配额下限覆盖（可重复）")
    parser.add_argument("--max-source-share", type=float, default=DEFAULT_MAX_SOURCE_SHARE)
    parser.add_argument("--json-out", type=Path, help="把完整报告写成 JSON")
    parser.add_argument("--top", type=int, default=40, help="文本报告里问题键分布显示前 N 项")
    parser.add_argument("--strict", action="store_true", help="schema 警告也计为失败")
    parser.add_argument("--quiet", action="store_true", help="不打印文本报告（仍写 --json-out）")
    args = parser.parse_args(argv)

    if not 0.0 <= args.max_source_share <= 1.0:
        print(f"参数错误：--max-source-share 必须在 [0,1]，收到 {args.max_source_share}", file=sys.stderr)
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

    report = build_report(items, items_file=args.items, min_total=args.min_total,
                          min_per_domain=args.min_per_domain, domain_min=domain_min,
                          max_source_share=args.max_source_share)
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
    raise SystemExit(main())
