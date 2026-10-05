#!/usr/bin/env python3
r"""把通用数据集条目精简成「数据集级 manifest + 逐条紧凑引用」，并保证可逐字段复原。

为什么要精简（用户原话）
------------------------
「很多没必要的重复字段。比如授权方式，没必要写在每一条数据里；至于数据来源，完全可以记录在
JSON 里（比如注明第几行到第几行是什么来源）。」

做法：逐条恒定、或能整批复述的东西抽到 manifest
------------------------------------------------
- source 对象（dataset / revision / config / split / license / url / slug）→ 记录只留 **src 下标 + row**
- meta 字段按**实测**分三档处理，不靠硬编码猜测：
    * 全库每条都有且值恒定 → manifest.defaults
    * 某个来源里每条都有且值恒定 → manifest.sources[].meta
    * 其余（逐条变化）→ 记录里的紧凑 m 对象
- 能从原始行复原的 meta 键（native_id / native_source / group_id / state_id / domain_rule …）
  → 整批删掉，manifest.dropped_meta_keys 写明"怎么拿回来"
- 某个来源所有条目的 quality_flags 完全一致（顺序也一致）→ 提升到 sources[].flags
- questions[].origin（恒为 source）与 questions[].source_key（契约规定恒等于 key）→ manifest.defaults
- questions[].prompt 与 key 相同时（原生问题文本即键名）→ 删掉，manifest 注明默认等于 key
- lang（全库一致时）→ manifest.defaults

为什么不算丢溯源能力
--------------------
记录的 (src, row) 配上 manifest.sources[src] 的 dataset / revision / config / split / license / url
以及 trace.raw_file + raw_sha256，能唯一定位到原始数据集的那一行；被删掉的字段都能从那一行读回来。
expand 子命令把 slim 还原成完整契约条目，用来校验"契约字段一个都没丢"。

用法
----
    uv run --no-project --offline python datasets/general/slim.py build \
        --items datasets/general/data/items.native.jsonl \
        --out datasets/general/data/items.native.slim.jsonl \
        --manifest datasets/general/data/items.native.manifest.json \
        --report datasets/general/data/slim-report.json --raw-root D:\pol2-raw --gzip

    uv run --no-project --offline python datasets/general/slim.py expand \
        --manifest ... --slim ... --out <仓库外>\expanded.jsonl --expect <原文件>

    uv run --no-project --offline python datasets/general/slim.py fields --items <任意 items.jsonl>

测试：python -m unittest discover -s datasets/general -p "test_slim.py" -q
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import shutil
import sys
from pathlib import Path

SCHEMA = "general-items-manifest/0.1"
DEFAULT_RAW_ROOT = Path(r"D:\pol2-raw")

#: 每条重复、且能从原始行复原 → 整批删掉（manifest.dropped_meta_keys 写明复原方式）
RECOVERABLE_META_KEYS = (
    "domain_rule", "native_source", "native_id", "native_domain", "native_kind", "native_family",
    "native_task", "native_level", "state_id", "group_id", "native_line_number",
    "native_label_alias", "native_label_key", "native_criteria_keys", "native_option_count",
    "native_config_shape",
)
#: 空列表也算"值"，但 quality_flags 为空时省略（展开时同样省略，比对时两边都归一）
OPTIONAL_EMPTY_KEYS = ("quality_flags",)


def json_size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, records) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    count, digest = 0, hashlib.sha256()
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            line = json.dumps(record, ensure_ascii=False) + "\n"
            handle.write(line)
            digest.update(line.encode("utf-8"))
            count += 1
    return {"path": str(path), "records": count, "bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def write_gzip(source: Path, target: Path) -> dict:
    with source.open("rb") as fin, gzip.GzipFile(target, "wb", compresslevel=9, mtime=0) as fout:
        shutil.copyfileobj(fin, fout)
    return {"path": str(target), "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def field_profile(items) -> dict:
    """顶层字段与 questions/meta/source 子字段的字节占比（精简前后各跑一次）。"""
    top, meta_keys, question_keys = collections.Counter(), collections.Counter(), collections.Counter()
    total, count = 0, 0
    for item in items:
        count += 1
        total += json_size(item) + 1
        for key, value in item.items():
            top[key] += json_size(value)
        for key, value in (item.get("meta") or {}).items():
            meta_keys[key] += json_size(value)
        for key, value in (item.get("source") or {}).items():
            top[f"source.{key}"] += json_size(value)
        for question in item.get("questions") or []:
            for key, value in question.items():
                question_keys[key] += json_size(value)

    def table(counter):
        return [{"field": key, "bytes": value, "share": round(value / total, 4) if total else 0.0}
                for key, value in counter.most_common()]

    return {"records": count, "bytes": total,
            "bytes_per_record": round(total / count, 1) if count else 0.0,
            "top_level": table(top), "meta": table(meta_keys), "questions": table(question_keys)}


def fetch_facts(raw_root: Path, slug: str) -> dict:
    """读 fetch.py 的 manifest：原始文件、行数、sha256 —— 溯源链的后半段。"""
    path = raw_root / slug / "manifest.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    facts = {"raw_file": str(raw_root / slug / "rows.jsonl"), "raw_rows": payload.get("rows"),
             "raw_bytes": payload.get("bytes"), "raw_sha256": payload.get("sha256"),
             "raw_num_rows_total": payload.get("num_rows_total"),
             "revision_stable": payload.get("revision_stable")}
    sampling = payload.get("sampling")
    if sampling and sampling.get("strategy") not in (None, "head"):
        facts["raw_sampling"] = sampling
    return facts


def build_slim(items, raw_root: Path):
    """产出 (slim 记录, manifest, 统计)。"""
    sources: dict = {}
    order: list = []
    source_items = collections.Counter()
    lang_values = collections.Counter()
    key_stats: dict = {}                      # meta 键 → 出现次数/取值集合/逐来源统计
    flag_lists = collections.defaultdict(collections.Counter)
    pending = []

    for item in items:
        source = item["source"]
        slug = source.get("slug") or source.get("dataset")
        if slug not in sources:
            sources[slug] = {"src": len(order), "slug": slug, "dataset": source["dataset"],
                             "revision": source["revision"], "config": source["config"],
                             "split": source["split"], "license": source["license"],
                             "url": source["url"]}
            order.append(slug)
        entry = sources[slug]
        row = source.get("row")
        if isinstance(row, int):
            entry["row_range"] = [row, row] if entry.get("row_range") is None else \
                [min(entry["row_range"][0], row), max(entry["row_range"][1], row)]
        source_items[slug] += 1
        lang_values[item.get("lang")] += 1
        meta = item.get("meta") or {}
        for key, value in meta.items():
            stats = key_stats.setdefault(key, {"present": 0, "values": set(), "per_source": {}})
            stats["present"] += 1
            stats["values"].add(stable(value))
            per = stats["per_source"].setdefault(slug, {"present": 0, "values": set()})
            per["present"] += 1
            per["values"].add(stable(value))
        flags = list(meta.get("quality_flags") or [])
        # 空列表也要计进去：否则"部分记录带 flag、部分不带"的来源会被误判为一致并错误提升
        flag_lists[slug][stable(flags)] += 1
        pending.append((slug, item, meta))

    total_items = len(pending)
    global_meta, per_source_meta = {}, collections.defaultdict(dict)
    for key, stats in key_stats.items():
        if key in RECOVERABLE_META_KEYS:
            continue
        if stats["present"] == total_items and len(stats["values"]) == 1:
            global_meta[key] = json.loads(next(iter(stats["values"])))
            continue
        for slug, per in stats["per_source"].items():
            if per["present"] == source_items[slug] and len(per["values"]) == 1:
                per_source_meta[slug][key] = json.loads(next(iter(per["values"])))
    hoisted_flags = {slug: (json.loads(next(iter(counts))) if len(counts) == 1 else [])
                     for slug, counts in flag_lists.items()}
    dropped = collections.Counter()

    records = []
    for slug, item, meta in pending:
        entry = sources[slug]
        questions = []
        for question in item.get("questions") or []:
            slim_question = {"key": question["key"], "kind": question["kind"]}
            if question.get("kind") == "score":
                slim_question["scale"] = question.get("scale")
            else:
                slim_question["options"] = question.get("options")
            prompt = question.get("prompt")
            if prompt is not None and prompt != question["key"]:
                slim_question["prompt"] = prompt
            questions.append(slim_question)
        record = {"id": item["id"], "src": entry["src"], "row": item["source"].get("row"),
                  "domain": item["domain"], "state": item["state"], "questions": questions,
                  "targets": item.get("targets") or {}}
        kept = [flag for flag in (meta.get("quality_flags") or [])
                if flag not in hoisted_flags.get(slug, ())]
        if kept:
            record["flags"] = kept
        leftover = {}
        for key, value in meta.items():
            if key in RECOVERABLE_META_KEYS:
                dropped[key] += 1
                continue
            if key in global_meta or key in per_source_meta.get(slug, {}):
                continue
            if key in OPTIONAL_EMPTY_KEYS and not value:
                continue
            leftover[key] = value
        if leftover:
            record["m"] = leftover
        if len(lang_values) > 1:
            record["lang"] = item.get("lang")
        records.append(record)

    manifest_sources = []
    for slug in order:
        entry = dict(sources[slug])
        entry["items"] = source_items[slug]
        entry.setdefault("row_range", None)
        if per_source_meta.get(slug):
            entry["meta"] = per_source_meta[slug]
        if hoisted_flags.get(slug):
            entry["flags"] = hoisted_flags[slug]
        facts = fetch_facts(raw_root, slug)
        if facts:
            entry["trace"] = facts
        manifest_sources.append(entry)

    defaults = dict(global_meta)
    if len(lang_values) == 1:
        defaults["lang"] = next(iter(lang_values))
    defaults["question_origin"] = "source"
    defaults["prompt"] = "缺省等于 key（origin=source 时问题文本就是原生问题名）"
    defaults["source_key"] = "缺省等于 key（契约规定 origin=source 时两者相同）"
    defaults["omitted_when_empty"] = list(OPTIONAL_EMPTY_KEYS)
    manifest = {
        "schema": SCHEMA,
        "generated_at": global_meta.get("created_at"),
        "converter": global_meta.get("converter"),
        "converter_version": global_meta.get("converter_version"),
        "defaults": defaults,
        "dropped_meta_keys": {
            key: {"records": count,
                  "how_to_recover": "按 (src,row) 读 sources[src].trace.raw_file 的那一行，字段同名"}
            for key, count in sorted(dropped.items())
        },
        "record_fields": ["id", "src", "row", "domain", "state", "questions", "targets",
                          "flags?(非空时)", "m?(逐条变化的 meta)"],
        "notes": [
            "溯源：(src,row) + sources[src].dataset/revision/config/split/license/url "
            "+ trace.raw_file/raw_sha256 唯一定位原始行；被删字段可从那一行读回",
            "meta 三档：defaults（全库恒定）/ sources[].meta（该来源恒定）/ 记录 m（逐条变化）",
            "questions[].origin 与 source_key 见 defaults；prompt 仅在不同于 key 时出现",
            "quality_flags 为空时省略，展开时同样不补空数组",
        ],
        "sources": manifest_sources,
    }
    return records, manifest, {"dropped_meta_keys": dict(dropped), "hoisted_flags": hoisted_flags,
                               "global_meta_keys": sorted(global_meta),
                               "per_source_meta_keys": {s: sorted(v) for s, v in per_source_meta.items()}}


def expand_records(manifest: dict, slim_records):
    """slim 记录 + manifest → 完整契约条目（被删的可复原 meta 键按文档不还原）。"""
    defaults = manifest.get("defaults") or {}
    sources = {entry["src"]: entry for entry in manifest.get("sources") or []}
    for record in slim_records:
        entry = sources[record["src"]]
        questions = []
        for question in record["questions"]:
            expanded = {"key": question["key"], "kind": question["kind"],
                        "origin": defaults.get("question_origin", "source"),
                        "source_key": question["key"],
                        "prompt": question.get("prompt", question["key"])}
            if question["kind"] == "score":
                expanded["scale"] = question.get("scale")
            else:
                expanded["options"] = question.get("options")
            questions.append(expanded)
        meta = {}
        for key, value in defaults.items():
            # 这几个是「记录级/问题级」的默认值，不是 meta 内容
            if key in ("prompt", "source_key", "omitted_when_empty", "lang"):
                continue
            meta[key] = value
        meta.update(entry.get("meta") or {})
        meta.update(record.get("m") or {})
        flags = list(entry.get("flags") or []) + list(record.get("flags") or [])
        if flags:
            meta["quality_flags"] = flags
        yield {
            "id": record["id"], "domain": record["domain"],
            "lang": record.get("lang", defaults.get("lang")),
            "state": record["state"], "questions": questions,
            "targets": record.get("targets") or {},
            "source": {"dataset": entry["dataset"], "revision": entry["revision"],
                       "config": entry["config"], "split": entry["split"], "row": record["row"],
                       "license": entry["license"], "url": entry["url"], "slug": entry["slug"]},
            "meta": meta,
        }


def compare(original, expanded, dropped_keys) -> dict:
    """契约字段必须完全一致；可复原 meta 键单独说明；quality_flags 空值两边归一。"""
    mismatches = collections.Counter()
    examples = {}
    count = 0
    for left, right in zip(original, expanded):
        count += 1
        for field in ("id", "domain", "lang", "state", "questions", "targets", "source"):
            if stable(left.get(field)) != stable(right.get(field)):
                mismatches[field] += 1
                examples.setdefault(field, left.get("id"))
        def normalized(meta):
            return {k: v for k, v in (meta or {}).items()
                    if not (k in OPTIONAL_EMPTY_KEYS and not v)}

        left_meta = normalized({k: v for k, v in (left.get("meta") or {}).items()
                                if k not in dropped_keys})
        right_meta = normalized(right.get("meta"))
        if stable(left_meta) != stable(right_meta):
            mismatches["meta(可复原键之外)"] += 1
            examples.setdefault("meta(可复原键之外)", left.get("id"))
    return {"compared": count, "mismatches": dict(mismatches), "examples": examples}


def markdown_report(report: dict, manifest: dict, verification: dict) -> str:
    """把字节对比与字段占比写成可直接放进仓库的 markdown（数字全部来自实测报告）。"""
    before, after = report["before"], report["after"]
    lines = [
        "# 字段精简报告（items.native → items.native.slim）",
        "",
        f"- 源文件：{before['records']:,} 条，{before['bytes']:,} 字节（{before['bytes_per_record']} B/条）",
        f"- 精简后：{after['records']:,} 条，{after['bytes']:,} 字节（{after['bytes_per_record']} B/条）",
        f"- **省下 {report['saved_bytes']:,} 字节（{report['saved_share'] * 100:.1f}%）**；"
        f"manifest 另占 {report['manifest']['bytes']:,} 字节",
        "",
        "## 每字段字节占比（精简前 → 精简后）",
        "",
        "| 字段 | 精简前字节 | 占比 | 精简后字节 | 占比 | 处理方式 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    after_top = {row["field"]: row for row in after["top_level"]}
    notes = {
        "source": "拆成 src 下标 + row；dataset/revision/config/split/license/url 移入 manifest",
        "meta": "按实测分三档：全库恒定→defaults、来源内恒定→sources[].meta、逐条变化→m",
        "lang": "全库一致，移入 manifest.defaults",
        "id": "保留（记录身份；可由 src+row 复算）",
        "state": "保留（原始情境文本，不加工）",
        "questions": "保留题目；origin/source_key 移入 defaults，prompt==key 时省略 prompt",
        "targets": "保留（原生真值）",
        "domain": "保留（来源自身字段映射）",
    }
    for row in before["top_level"]:
        now = after_top.get(row["field"], {"bytes": 0, "share": 0.0})
        lines.append(f"| {row['field']} | {row['bytes']:,} | {row['share'] * 100:.1f}% | "
                     f"{now['bytes']:,} | {now['share'] * 100:.1f}% | {notes.get(row['field'], '')} |")
    lines += [
        "",
        "## questions 内部（精简前 → 精简后）",
        "",
        "| 子字段 | 精简前字节 | 占比 | 精简后字节 | 占比 |",
        "|---|---:|---:|---:|---:|",
    ]
    after_q = {row["field"]: row for row in after["questions"]}
    for row in before["questions"]:
        now = after_q.get(row["field"], {"bytes": 0, "share": 0.0})
        lines.append(f"| {row['field']} | {row['bytes']:,} | {row['share'] * 100:.1f}% | "
                     f"{now['bytes']:,} | {now['share'] * 100:.1f}% |")
    lines += [
        "",
        "## meta 内部（精简前）",
        "",
        "| meta 键 | 字节 | 占比 | 去向 |",
        "|---|---:|---:|---|",
    ]
    dropped = set(manifest.get("dropped_meta_keys") or {})
    defaults = manifest.get("defaults") or {}
    per_source = {k for entry in manifest.get("sources") or [] for k in (entry.get("meta") or {})}
    for row in before["meta"][:16]:
        key = row["field"]
        if key in dropped:
            where = "整批删掉（可按 src+row 从原始行复原）"
        elif key in defaults:
            where = "manifest.defaults（全库恒定）"
        elif key in per_source:
            where = "manifest.sources[].meta（来源内恒定）"
        else:
            where = "记录内 m（逐条变化）"
        lines.append(f"| meta.{key} | {row['bytes']:,} | {row['share'] * 100:.1f}% | {where} |")
    lines += [
        "",
        "## 溯源怎么保证",
        "",
        "每条记录的 (src, row) 配上 manifest 里该来源的 dataset / revision / config / split / license / url",
        "以及原始文件 D:\\pol2-raw\\<slug>\\rows.jsonl 的 sha256，能唯一定位到原始数据集的那一行。",
        "被整批删掉的 meta 键，manifest.dropped_meta_keys 逐键写明「按 (src,row) 读原始行，字段同名」。",
        "",
        "## 可复算校验",
        "",
        "slim 文件能还原成完整契约条目，与原件逐字段比对：",
        "",
        "    uv run --no-project --offline python datasets/general/slim.py expand " + "\\",
        "        --manifest data/items.native.manifest.json --slim data/items.native.slim.jsonl " + "\\",
        "        --out <仓库外>\\expanded.jsonl --expect data/items.native.jsonl",
        "",
        f"结果：**{verification['compared']:,} 条逐字段比对，{len(verification['mismatches'])} 处不一致**"
        f"（id / domain / lang / state / questions / targets / source 与可复原键之外的 meta 全部相等）",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="通用数据集字段精简（manifest + 紧凑引用）")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="生成 slim 文件与 manifest")
    build.add_argument("--items", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--report", type=Path)
    build.add_argument("--report-md", type=Path, help="同时写人读的 markdown 报告")
    build.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    build.add_argument("--gzip", action="store_true", help="同时写确定性 .gz")
    expand = sub.add_parser("expand", help="把 slim 还原成完整条目，可用 --expect 与原件比对")
    expand.add_argument("--manifest", type=Path, required=True)
    expand.add_argument("--slim", type=Path, required=True)
    expand.add_argument("--out", type=Path, required=True)
    expand.add_argument("--expect", type=Path)
    fields = sub.add_parser("fields", help="打印字段字节占比")
    fields.add_argument("--items", type=Path, required=True)
    fields.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    if args.command == "fields":
        profile = field_profile(read_jsonl(args.items))
        if args.out:
            args.out.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        print(json.dumps({"records": profile["records"], "bytes": profile["bytes"],
                          "bytes_per_record": profile["bytes_per_record"]}, ensure_ascii=False))
        return 0

    if args.command == "build":
        original_items = list(read_jsonl(args.items))
        before = field_profile(original_items)
        records, manifest, stats = build_slim(original_items, args.raw_root)
        written = write_jsonl(args.out, records)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        after = field_profile(records)
        # 自校验：把刚生成的 slim 记录原地展开，与原件逐字段比对，结果写进报告
        verification = compare(original_items, list(expand_records(manifest, records)),
                               set(manifest.get("dropped_meta_keys") or {}))
        report = {"schema": SCHEMA, "source_file": str(args.items),
                  "verification": verification,
                  "before": before, "after": after,
                  "saved_bytes": before["bytes"] - after["bytes"],
                  "saved_share": round((before["bytes"] - after["bytes"]) / before["bytes"], 4),
                  "slim": written,
                  "manifest": {"path": str(args.manifest), "bytes": args.manifest.stat().st_size},
                  "stats": stats}
        if args.gzip:
            report["gzip"] = write_gzip(args.out, args.out.with_suffix(args.out.suffix + ".gz"))
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
        if args.report_md:
            args.report_md.write_text(markdown_report(report, manifest, verification),
                                      encoding="utf-8")
        print(json.dumps({"records": written["records"], "bytes_before": before["bytes"],
                          "bytes_after": after["bytes"], "saved": report["saved_bytes"],
                          "saved_share": report["saved_share"], "manifest": str(args.manifest)},
                         ensure_ascii=False))
        return 0

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expanded = list(expand_records(manifest, read_jsonl(args.slim)))
    write_jsonl(args.out, expanded)
    if not args.expect:
        print(json.dumps({"expanded": len(expanded), "out": str(args.out)}, ensure_ascii=False))
        return 0
    original = list(read_jsonl(args.expect))
    result = compare(original, expanded, set(manifest.get("dropped_meta_keys") or {}))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
