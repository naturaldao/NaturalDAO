"""把 general v5 条目 JSONL 转成 Kev 标记请求 JSONL（kev benchmark suite/data 的输入）。

用途：原版 Kev-4B 与 POL2 score-v2 M10（seed-43/17/29）在同一份评测集上的规范对照。
本模块只做确定性映射，不读答案之外的任何信息，不联网，不导入第三方库。

映射（每个 item 的每个 question 一条 Kev question）：
- state      = item["state"]（原文，不改写）
- instructions = question["prompt"]（原文）
- choice     = {"type":"choice","criteria":{"opt_1": <选项1文字>, ...},"label":"opt_<answer_idx+1>"}
               选项 key 统一换成中性 "opt_<i>"（原生 key 多为截断文字，渲染成 "key: label" 会重复/失真）；
               选项顺序与条目一致，不 shuffle。
- noul       = {"type":"noul","criteria":{"false":<否侧文字>,"true":<是侧文字>},"label":<bool>}
               是/否侧按以下顺序唯一判定：keys 为 false/true 或 no/yes；否则 key 以 yes_/no_ 开头；
               否则 label 以 yes/no 开头；仍不唯一 -> 跳过并计数（不臆造）。
- score      = {"type":"score","criteria":[<scale.labels 或 "0".."max">],"label":<answer - scale.min>}
- 无法映射（无 target / 答案不在选项内 / score 越界 / noul 歧义）一律跳过并计数，绝不猜标签；
  跳过的是整个 item（保证同一 item 的问题不跨记录拆分）。
- 超长标记：len(state)+len(instructions)+Σlen(选项渲染) > --max-chars（默认 4000，沿用 general v5 view 规则）
  不丢记录，只在 sidecar 标 "overlong": true；主表分母默认排除并在 manifest 计数（两个模型同口径）。

输出（都只允许写到仓库外；sidecar/join 含 item id，仅评测端临时使用，禁止导出/提交）：
- --out-records : 一行一个 Kev labelled request（state + questions，无 id/meta）
- --sidecar     : 一行一个记录 {"record": n, "item_id":..., "domain","lang","group_id","questions":[...]}
                  questions 里放 qid/rid/kind/num_options/overlong 供分层聚合与 view 子集对齐
- --manifest    : 聚合计数（无 item id/正文），含输入/输出 sha256 与跳过分布，可入结果卡。

    python benchmark/kev_prefix/convert.py \\
        --items <仓库外>/items.jsonl --out-records <仓库外>/records.jsonl \\
        --sidecar <仓库外>/sidecar.jsonl --manifest <仓库外>/convert-manifest.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_OPTIONS = 255          # kev.api.MAX_OPTIONS
DEFAULT_MAX_CHARS = 4000   # general v5 view 规则：超长 prompt 标记排除
MAPPING_VERSION = "kev-general-v5-map-v1"


def _load_view_module():
    """按文件路径加载 datasets/general/build_training_view.py，复用其 option_space/resolve_answer。

    不按包名 import，避免与 PyPI 的 datasets 混淆；返回模块对象。
    """
    path = ROOT / "datasets" / "general" / "build_training_view.py"
    spec = importlib.util.spec_from_file_location("_pol_general_build_training_view", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VIEW = _load_view_module()


class SkipQuestion(ValueError):
    """该问题无法无损映射；reason 是稳定短标签，只进聚合计数。"""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _option_text(name, desc):
    """与 kev.api.option_text 同形的渲染长度近似（只用于超长判断）。"""
    if desc is None or desc == "":
        return str(name)
    return f"{name}: {desc}"


def _noul_true_index(option_keys, option_labels):
    """返回「是/true」一侧的下标；无法唯一判定时返回 None。"""
    keys = [str(k).strip().lower() for k in option_keys]
    if len(keys) != 2:
        return None
    if set(keys) == {"false", "true"}:
        return keys.index("true")
    if set(keys) == {"no", "yes"}:
        return keys.index("yes")
    yes_idx = [i for i, k in enumerate(keys) if k.startswith("yes")]
    no_idx = [i for i, k in enumerate(keys) if k.startswith("no")]
    if len(yes_idx) == 1 and len(no_idx) == 1:
        return yes_idx[0]
    labels = [str(x).strip().lower() for x in option_labels]
    yes_idx = [i for i, x in enumerate(labels) if x.startswith("yes")]
    no_idx = [i for i, x in enumerate(labels) if x.startswith("no")]
    if len(yes_idx) == 1 and len(no_idx) == 1:
        return yes_idx[0]
    return None


def map_question(question, item, *, max_chars=DEFAULT_MAX_CHARS, stats=None):
    """-> (kev_question, sidecar_row) 或抛 SkipQuestion。"""
    stats = stats if stats is not None else {}
    kind = question.get("kind")
    if kind not in ("choice", "noul", "score"):
        raise SkipQuestion("unsupported_kind")
    prompt = question.get("prompt")
    instructions = "" if prompt is None else str(prompt)
    state_text = "" if item.get("state") is None else str(item.get("state"))
    target = (item.get("targets") or {}).get(question.get("key"))
    answer = target.get("answer") if isinstance(target, dict) else None
    if answer is None:
        raise SkipQuestion("no_target")
    if kind == "score":
        scale = question.get("scale") or {}
        try:
            minimum, maximum = int(scale.get("min")), int(scale.get("max"))
        except (TypeError, ValueError):
            raise SkipQuestion("invalid_scale")
        if maximum < minimum:
            raise SkipQuestion("invalid_scale")
        try:
            number = int(answer)
        except (TypeError, ValueError):
            raise SkipQuestion("answer_not_integer")
        index = number - minimum
        labels = scale.get("labels")
        if not isinstance(labels, list) or len(labels) != maximum - minimum + 1:
            labels = [str(minimum + i) for i in range(maximum - minimum + 1)]
            stats["score_labels_fallback"] = stats.get("score_labels_fallback", 0) + 1
        if not 0 <= index < len(labels):
            raise SkipQuestion("answer_out_of_range")
        criteria = [str(x) for x in labels]
        rendered = len(state_text) + len(instructions) + sum(len(x) + 3 for x in criteria)
        kev_q = {"type": "score", "instructions": instructions, "criteria": criteria, "label": index,
                 "src": "score"}
        return kev_q, {"kind": "score", "num_options": len(criteria), "overlong": rendered > max_chars}
    try:
        option_keys, option_labels, _scale = VIEW.option_space(question)
    except Exception:
        raise SkipQuestion("invalid_options")
    if len(option_keys) < 2:
        raise SkipQuestion("invalid_options")
    if len(option_keys) > MAX_OPTIONS:
        raise SkipQuestion("options_gt_255")
    answer_idx = VIEW.resolve_answer(answer, option_keys, option_labels, None)
    if answer_idx is None:
        raise SkipQuestion("answer_not_in_options")
    if kind == "noul":
        true_idx = _noul_true_index(option_keys, option_labels)
        if true_idx is None:
            raise SkipQuestion("noul_ambiguous")
        no_label = option_labels[1 - true_idx]
        yes_label = option_labels[true_idx]
        rendered = (len(state_text) + len(instructions)
                    + len(_option_text("false", no_label)) + len(_option_text("true", yes_label)))
        kev_q = {"type": "noul", "instructions": instructions,
                 "criteria": {"false": no_label, "true": yes_label},
                 "label": bool(answer_idx == true_idx), "src": "noul"}
        return kev_q, {"kind": "noul", "num_options": 2, "overlong": rendered > max_chars}
    keys, labels = [], []
    for i, label in enumerate(option_labels, start=1):
        keys.append(f"opt_{i}")
        labels.append(str(label))
    criteria = dict(zip(keys, labels))
    rendered = (len(state_text) + len(instructions)
                + sum(len(_option_text(k, v)) for k, v in criteria.items()))
    kev_q = {"type": "choice", "instructions": instructions, "criteria": criteria,
             "label": keys[answer_idx], "src": "choice"}
    return kev_q, {"kind": "choice", "num_options": len(keys), "overlong": rendered > max_chars}


def convert_items(items, *, max_chars=DEFAULT_MAX_CHARS, limit=0):
    """-> (records, sidecar, stats)。records/sidecar 只含可映射记录，顺序与输入 item 顺序一致。"""
    records, sidecar = [], []
    stats = {
        "items_in": 0, "records_out": 0, "questions_in": 0, "questions_out": 0,
        "questions_primary": 0, "questions_overlong_flagged": 0,
        "skipped": {}, "skipped_by_kind": {}, "score_labels_fallback": 0,
        "max_chars": max_chars, "mapping_version": MAPPING_VERSION,
    }

    def bump(bucket, key):
        bucket[key] = bucket.get(key, 0) + 1

    for item in items:
        stats["items_in"] += 1
        item_id = item.get("id")
        questions = item.get("questions") or []
        stats["questions_in"] += len(questions)
        out_questions, out_meta = {}, []
        for index, question in enumerate(questions):
            qid = f"q{index}"
            kind = question.get("kind")
            try:
                kev_q, side = map_question(question, item, max_chars=max_chars, stats=stats)
            except SkipQuestion as error:
                bump(stats["skipped"], error.reason)
                bump(stats["skipped_by_kind"], f"{kind}:{error.reason}")
                continue
            out_questions[qid] = kev_q
            # rid 只用于评测端 join/子集过滤，绝不出仓库；必须是单行安全串（部分原生 question key 含换行符）
            rid = f"{item_id}#{qid}"
            if any(ch in rid for ch in ("\n", "\r", "\t", " ")):
                raise SkipQuestion("unsafe_rid")
            out_meta.append({"qid": qid, "rid": rid, **side})
            stats["questions_out"] += 1
            if side["overlong"]:
                stats["questions_overlong_flagged"] += 1
            else:
                stats["questions_primary"] += 1
        if not out_questions:
            bump(stats["skipped"], "record_no_questions")
            bump(stats["skipped_by_kind"], "record:no_questions")
            continue
        record_index = len(records)
        records.append({"state": item.get("state"), "questions": out_questions})
        meta = item.get("meta") or {}
        sidecar.append({
            "record": record_index,
            "item_id": item_id,
            "domain": item.get("domain"),
            "lang": item.get("lang"),
            "group_id": meta.get("group_id"),
            "questions": out_meta,
        })
        stats["records_out"] += 1
        if limit and stats["records_out"] >= limit:
            break
    return records, sidecar, stats


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_items(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            yield json.loads(line)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("wb") as handle:
        for row in rows:
            data = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
            handle.write(data)
            digest.update(data)
    return digest.hexdigest()


def assert_outside_repo(path, allow_inside, flag):
    resolved = Path(path).resolve()
    if allow_inside:
        return
    if resolved == ROOT or ROOT in resolved.parents:
        raise SystemExit(f"refusing to write {flag} inside the repository: {resolved}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=Path, required=True, help="general v5 items JSONL(.gz)")
    parser.add_argument("--out-records", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--limit", type=int, default=0, help="debug: stop after N records")
    parser.add_argument("--allow-inside-repo", action="store_true",
                        help="only for synthetic fixtures/tests; private item sidecars must stay outside the repo")
    args = parser.parse_args(argv)
    if args.max_chars < 1:
        parser.error("--max-chars must be >= 1")
    for path, flag in ((args.out_records, "--out-records"), (args.sidecar, "--sidecar")):
        assert_outside_repo(path, args.allow_inside_repo, flag)
    if args.manifest:
        assert_outside_repo(args.manifest, args.allow_inside_repo, "--manifest")
    if not args.items.is_file():
        parser.error(f"missing items file: {args.items}")
    records, sidecar, stats = convert_items(read_items(args.items), max_chars=args.max_chars, limit=args.limit)
    if not records:
        parser.error("no records converted (all filtered)")
    records_sha = write_jsonl(args.out_records, records)
    sidecar_sha = write_jsonl(args.sidecar, sidecar)
    manifest = {
        "schema": "kev-prefix-convert/1",
        **stats,
        "items_file": str(args.items),
        "items_sha256": _sha256_file(args.items),
        "out_records_sha256": records_sha,
        "sidecar_sha256": sidecar_sha,
        "rules": {
            "choice": "neutral option keys opt_<i>; labels as description; order preserved",
            "noul": "label bool; true side by false/true or no/yes keys, else yes_/no_ keys, else yes/no labels",
            "score": "criteria = scale.labels (fallback numeric strings); label = answer - scale.min",
            "overlong": f"flagged in sidecar when len(state)+len(instructions)+rendered options > {args.max_chars}; "
                        "excluded from the primary denominator, counted here",
            "private": "sidecar carries item ids/rids and must never be exported/committed",
        },
    }
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("items_in", "records_out", "questions_in", "questions_out",
                                              "questions_primary", "questions_overlong_flagged", "skipped")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())