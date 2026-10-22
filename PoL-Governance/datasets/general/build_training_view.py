"""把通用决策数据集 v5 的分区转换成统一训练视图（M2-2）。

一行 = 一个问题；只读公开分区文件 + 训练路由旁挂件，离线、仅标准库、确定性。

    python datasets/general/build_training_view.py --split train --out D:/pol2-train/data/general-train-view.jsonl

输出行 schema 与渲染模板见 TRAINING-VIEW.md。
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets" / "general" / "data"
DEFAULT_TARGET_TYPES = DATA_DIR / "target-types.jsonl.gz"
SPLITS = ("train", "validation", "test")
TEMPLATE_VERSION = "tv-1"
SKIP_BENCHMARK_TOKENS = ("benchmark", "holdout", "private")

TEMPLATE = (
    "你是只做封闭选择的决策模型：给定情境、问题与候选选项，只选择一个最合适的选项，不解释、不输出其他文字。\n\n"
    "【情境】\n{state}\n\n"
    "【问题】\n{question}\n\n"
    "【选项】\n{options}"
)


class BuildError(ValueError):
    """校验失败（CLI 退出码 2）。"""


def index_to_letter(idx: int) -> str:
    """将 0-based 下标转换为字母 A..Z, AA..ZZ (双射进位)。"""
    if idx < 0:
        raise BuildError(f"negative option index: {idx}")
    res = []
    while True:
        res.append(chr(ord("A") + (idx % 26)))
        idx = idx // 26 - 1
        if idx < 0:
            break
    return "".join(reversed(res))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl_gz(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise BuildError(f"{path}:{number}: invalid JSON: {error}") from error
            if not isinstance(row, dict):
                raise BuildError(f"{path}:{number}: each line must be an object")
            yield row


def load_routes(path: Path) -> dict:
    routes = {}
    for row in read_jsonl_gz(path):
        item_id = row.get("item_id")
        question_key = row.get("question_key")
        if not isinstance(item_id, str) or not isinstance(question_key, str):
            raise BuildError(f"{path}: route row missing item_id/question_key")
        key = (item_id, question_key)
        if key in routes:
            raise BuildError(f"{path}: duplicate route for {key}")
        routes[key] = row
    if not routes:
        raise BuildError(f"{path}: no routes")
    return routes


def guard_items_path(path: Path, split: str | None = None) -> None:
    lowered = path.name.lower()
    if any(token in lowered for token in SKIP_BENCHMARK_TOKENS):
        raise BuildError(f"refusing to read non-public partition file: {path.name}")
    if split and any(token in split.lower() for token in SKIP_BENCHMARK_TOKENS):
        raise BuildError(f"refusing to read non-public partition split: {split}")


def option_space(question: dict) -> tuple[list[str], list[str], dict | None]:
    """返回 (option_keys, option_labels, scale)。"""
    kind = question.get("kind")
    if kind in ("choice", "noul"):
        options = question.get("options") or []
        keys = []
        labels = []
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("key"), str):
                raise BuildError(f"question {question.get('key')}: invalid option {option!r}")
            keys.append(option["key"])
            labels.append(str(option.get("label") if option.get("label") is not None else option["key"]))
        if len(keys) < 2:
            raise BuildError(f"question {question.get('key')}: needs >=2 options")
        if len(set(keys)) != len(keys):
            raise BuildError(f"question {question.get('key')}: duplicate option keys")
        return keys, labels, None
    if kind == "score":
        scale = question.get("scale") or {}
        try:
            minimum = int(scale["min"])
            maximum = int(scale["max"])
        except (KeyError, TypeError, ValueError) as error:
            raise BuildError(f"question {question.get('key')}: invalid scale {scale!r}") from error
        if maximum < minimum:
            raise BuildError(f"question {question.get('key')}: scale max < min")
        keys = [str(value) for value in range(minimum, maximum + 1)]
        return keys, list(keys), {"min": minimum, "max": maximum}
    raise BuildError(f"question {question.get('key')}: unknown kind {kind!r}")


def resolve_answer(answer, option_keys: list[str], option_labels: list[str], scale: dict | None):
    if answer is None:
        return None
    if scale is not None:
        try:
            number = int(answer)
        except (TypeError, ValueError):
            return None
        index = number - scale["min"]
        return index if 0 <= index < len(option_keys) else None

    # 布尔或字符串统一转小写匹配
    ans_str = "true" if answer is True else ("false" if answer is False else str(answer))
    if ans_str in option_keys:
        return option_keys.index(ans_str)
    lowered_keys = [k.lower() for k in option_keys]
    if ans_str.lower() in lowered_keys:
        return lowered_keys.index(ans_str.lower())
    if ans_str in option_labels:
        return option_labels.index(ans_str)
    lowered_labels = [l.lower() for l in option_labels]
    if ans_str.lower() in lowered_labels:
        return lowered_labels.index(ans_str.lower())
    if isinstance(answer, int) and not isinstance(answer, bool):
        return answer if 0 <= answer < len(option_keys) else None
    return None


def build_soft(probs, option_keys: list[str], scale: dict | None):
    """把 probs 对齐到 options 并归一；若缺失/退化则返回 None。"""
    if not isinstance(probs, dict) or not probs:
        return None
    values = []
    for index, key in enumerate(option_keys):
        lookup = key if scale is None else str(scale["min"] + index)
        value = probs.get(lookup)
        if value is None and scale is not None:
            value = probs.get(key)
        try:
            values.append(float(value if value is not None else 0.0))
        except (TypeError, ValueError):
            return None
    values = [max(0.0, v) for v in values]
    total = sum(values)
    if total <= 0:
        return None
    values = [value / total for value in values]
    if len({round(value, 12) for value in values}) <= 1:
        return None
    return values


def render_prompt(item: dict, question: dict, labels: list[str]) -> str:
    option_lines = [
        f"{index_to_letter(index)}. {label}"
        for index, label in enumerate(labels)
    ]
    return TEMPLATE.format(
        state=str(item.get("state") or "").strip(),
        question=str(question.get("prompt") or "").strip(),
        options="\n".join(option_lines),
    )


def build_view(items, routes, split: str, limit: int = 0, warnings=None, allow_fallback: bool = True):
    warnings = warnings if warnings is not None else []
    rows = []
    skipped = collections.Counter()
    fallbacks = collections.Counter()
    seen = set()
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise BuildError("item without id")
        targets = item.get("targets") or {}
        for question in item.get("questions") or []:
            if not isinstance(question, dict) or not isinstance(question.get("key"), str):
                raise BuildError(f"{item_id}: invalid question")
            key = question["key"]
            rid = f"{item_id}#{key}"
            if rid in seen:
                raise BuildError(f"duplicate rid {rid}")
            seen.add(rid)
            try:
                option_keys, option_labels, scale = option_space(question)
            except BuildError:
                raise

            target = targets.get(key) if isinstance(targets, dict) else None
            target = target if isinstance(target, dict) else {}
            answer = target.get("answer")
            probs = target.get("probs")
            answer_idx = resolve_answer(answer, option_keys, option_labels, scale)
            route_row = routes.get((item_id, key))
            if route_row is None:
                # 中文补充等未进旁挂件的 target：按 TRAINING.md §1.1 兜底为 answer_only/classification
                if not allow_fallback or (answer_idx is None and not probs):
                    skipped["no_route"] += 1
                    continue
                route = "classification"
                fallbacks["classification_without_route"] += 1
            else:
                route = route_row.get("training_route")
                if route == "drop":
                    skipped["drop"] += 1
                    continue
                if route not in ("classification", "distillation"):
                    skipped["unknown_route"] += 1
                    continue

            soft = None
            soft_conf = None
            if route == "distillation":
                soft = build_soft(probs, option_keys, scale)
                if soft is None:
                    skipped["degenerate_soft"] += 1
                    continue
                conf = route_row.get("label_confidence") or route_row.get("semantics_confidence")
                if conf in ("high", "medium", "low"):
                    soft_conf = conf

            if answer_idx is None:
                if soft is not None:
                    answer_idx = max(range(len(soft)), key=lambda idx: soft[idx])
                elif probs and scale is None:
                    vals = [float(probs.get(k, 0.0)) for k in option_keys]
                    if max(vals) > min(vals) and sum(vals) > 0:
                        answer_idx = max(range(len(vals)), key=lambda i: vals[i])
                    else:
                        skipped["no_target"] += 1
                        continue
                else:
                    if answer is not None and scale is not None:
                        skipped["answer_out_of_range"] += 1
                    elif answer is not None:
                        skipped["answer_not_in_options"] += 1
                    else:
                        skipped["no_target"] += 1
                    continue

            row = {
                "rid": rid,
                "src": "general-v5",
                "split": split,
                "lang": item.get("lang"),
                "domain": item.get("domain"),
                "kind": question.get("kind"),
                "prompt": render_prompt(item, question, option_labels),
                "options": option_keys,
                "option_labels": option_labels,
                "answer_idx": answer_idx,
                "soft": soft,
                "soft_conf": soft_conf,
                "scale": scale,
                "route": route,
                "source_slug": ((item.get("meta") or {}).get("native_source")
                                or (item.get("source") or {}).get("slug")),
                "template_version": TEMPLATE_VERSION,
            }
            rows.append(row)
            if limit and len(rows) >= limit:
                rows.sort(key=lambda r: r["rid"])
                return rows, skipped, fallbacks
    rows.sort(key=lambda r: r["rid"])
    return rows, skipped, fallbacks


def write_view(rows, out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with out_path.open("wb") as fh:
        for row in rows:
            data = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
            fh.write(data)
            digest.update(data)
    return digest.hexdigest()


def stats_for(rows):
    by_kind = collections.Counter(row["kind"] for row in rows)
    by_lang = collections.Counter(row["lang"] for row in rows)
    by_route = collections.Counter(row["route"] for row in rows)
    by_soft = collections.Counter("soft" if row["soft"] else "hard" for row in rows)
    return {
        "rows": len(rows),
        "by_kind": dict(sorted(by_kind.items())),
        "by_lang": dict(sorted(by_lang.items())),
        "by_route": dict(sorted(by_route.items())),
        "by_target": dict(sorted(by_soft.items())),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--split", choices=SPLITS, default="train")
    parser.add_argument("--items", type=Path,
                        help="分区 JSONL(.gz)；默认 data/splits/<split>.jsonl.gz")
    parser.add_argument("--target-types", type=Path, default=DEFAULT_TARGET_TYPES)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="默认 <out>.manifest.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="只打印 JSON 摘要")
    parser.add_argument(
        "--strict-route",
        action="store_true",
        help="严格禁止无旁挂 target 兜底，未覆盖 target 全部计入 skipped.no_route",
    )
    args = parser.parse_args(argv)
    items_path = args.items or (DATA_DIR / "splits" / f"{args.split}.jsonl.gz")
    manifest_path = args.manifest or args.out.with_suffix(args.out.suffix + ".manifest.json")
    try:
        guard_items_path(items_path, args.split)
        if not items_path.is_file():
            raise BuildError(f"missing items file: {items_path}")
        if not args.target_types.is_file():
            raise BuildError(f"missing target-types file: {args.target_types}")
        if args.limit < 0:
            raise BuildError("--limit must be >= 0")
        routes = load_routes(args.target_types)
        warnings: list[str] = []
        rows, skipped, fallbacks = build_view(
            read_jsonl_gz(items_path),
            routes,
            args.split,
            limit=args.limit,
            warnings=warnings,
            allow_fallback=not args.strict_route,
        )
        if not rows:
            raise BuildError("no rows built (all filtered)")
        out_sha = write_view(rows, args.out)
        summary = stats_for(rows)
        manifest = {
            "schema": "general-training-view/1",
            "template_version": TEMPLATE_VERSION,
            "split": args.split,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "datasets/general/build_training_view.py",
            "items_file": str(items_path.relative_to(ROOT)) if items_path.is_relative_to(ROOT) else str(items_path),
            "items_sha256": sha256_file(items_path),
            "target_types_file": (str(args.target_types.relative_to(ROOT))
                                  if args.target_types.is_relative_to(ROOT) else str(args.target_types)),
            "target_types_sha256": sha256_file(args.target_types),
            "out_file": str(args.out),
            "out_sha256": out_sha,
            **summary,
            "skipped": dict(sorted(skipped.items())),
            "fallbacks": dict(sorted(fallbacks.items())),
            "warnings": len(warnings),
            "warning_examples": warnings[:5],
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        if args.json:
            print(json.dumps(manifest, ensure_ascii=False))
        else:
            print("training view built")
            print(f"  split      : {args.split}")
            print(f"  rows       : {len(rows)}")
            print(f"  by kind    : {summary['by_kind']}")
            print(f"  by route   : {summary['by_route']}")
            print(f"  by target  : {summary['by_target']}")
            print(f"  skipped    : {dict(sorted(skipped.items()))}")
            print(f"  fallbacks  : {dict(sorted(fallbacks.items()))}")
            print(f"  warnings   : {len(warnings)}")
            print(f"  out sha256 : {out_sha}")
            print(f"  out        : {args.out}")
            print(f"  manifest   : {manifest_path}")
        return 0
    except (BuildError, OSError) as error:
        print(f"build_training_view failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
