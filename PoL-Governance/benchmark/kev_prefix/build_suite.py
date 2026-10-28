"""把 convert.py 的输出组装成 Kev 冻结 suite（benchmark --suite 可用），并输出评测端 join 文件。

为什么用 suite 而不是 --data：--data 走训练上下文（state 384 / row 1024 / packed 2048 tokens），
会把长文档条目整条拒掉；suite 的 manifest 可以显式记录 context。本 suite 用 Kev 的 serving context
（state 65536 / branch 73728 / packed 139264，truncate=false），即 Kev 模型卡声明已验证的长上下文范围，
所有可映射条目都能编码；两个模型看到完全相同的记录、manifest digest 与 suite_sha256。

产物（全部写到仓库外；join 含 item id，评测端临时使用，禁止导出/提交）：
- <out-suite>/development.jsonl : Kev labelled request + _meta（id 用中性 holdout/<n>，不含私有 id）
- <out-suite>/manifest.json     : holdout_sources=[]、eval_only=true、context、files sha256/records
- <out-join>                    : 一行一个 suite record → {"id","variant","item_id","domain","lang","group_id",
                                  "parent_id","state_chars","questions":[{"qid","rid","kind","num_options","overlong"}]}

可选变体（同一 suite 内，便于 kev.benchmark 直接给出 variants 分组指标）：
- --permuted-sample N : 按 sha256 确定性抽取 N 个 choice 题，生成 criteria 顺序打乱的 "permuted" 变体记录
                        （parent_id 指向 clean 记录；kev.benchmark 自动算 mean_max_delta / flip_rate）
- --isolation         : 对多问题 item，为每个问题生成单独成记录的 "isolation" 变体（packed vs 单独提问）

    python benchmark/kev_prefix/build_suite.py --records <仓库外>/records.jsonl \
        --sidecar <仓库外>/sidecar.jsonl --out-suite <仓库外>/suite --out-join <仓库外>/join.jsonl \
        --permuted-sample 600 --isolation
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "kev-prefix-suite/1"
SERVING_CONTEXT = {"max_state": 65536, "max_branch": 73728, "max_packed": 139264, "truncate": False}
DEFAULT_SEED = "pol-kev-prefix-v1"


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _normalised_state_sha(state):
    text = state if isinstance(state, str) else json.dumps(state, sort_keys=True, ensure_ascii=False)
    return _sha256_bytes(" ".join(text.casefold().split()).encode("utf-8"))


def _rng_for(*parts):
    digest = _sha256_bytes(":".join(str(p) for p in parts).encode("utf-8"))
    return random.Random(int(digest[:16], 16))


def _state_chars(state):
    if state is None:
        return 0
    if isinstance(state, str):
        return len(state)
    return len(json.dumps(state, ensure_ascii=False, sort_keys=True))


def assign_clean(records, sidecar):
    """给 clean records 补 _meta 与 join 行（stdlib only）。"""
    clean, join = [], []
    for index, (record, side) in enumerate(zip(records, sidecar)):
        record_id = f"holdout/{index}"
        group = side.get("group_id") or record_id
        meta = {"source": "holdout", "variant": "clean", "id": record_id, "group_id": group,
                "row": index, "split": "development",
                "text_sha256": _normalised_state_sha(record.get("state"))}
        clean.append({"state": record["state"], "questions": record["questions"], "_meta": meta})
        join.append({
            "id": record_id, "variant": "clean", "item_id": side.get("item_id"),
            "domain": side.get("domain"), "lang": side.get("lang"),
            "group_id": group, "parent_id": None,
            "state_chars": _state_chars(record.get("state")),
            "questions": [dict(q) for q in side["questions"]],
        })
    return clean, join


def _variant_record(clean_record, question_id, *, variant, record_id, parent_id, group, row, questions):
    meta = {"source": "holdout", "variant": variant, "id": record_id, "group_id": group,
            "parent_id": parent_id, "row": row, "split": "development",
            "text_sha256": _normalised_state_sha(clean_record["state"])}
    return {"state": clean_record["state"], "questions": {question_id: questions}, "_meta": meta}


def build_permuted(clean, join, sample, seed=DEFAULT_SEED):
    """确定性抽取 sample 个 choice 题，生成 permuted 变体。抽样只依赖 record id/qid 的 sha256，不依赖标签或模型。"""
    candidates = []
    for record, row in zip(clean, join):
        for question_id, question in record["questions"].items():
            if question.get("type") != "choice" or len(question.get("criteria") or {}) < 2:
                continue
            key = _sha256_bytes(f"{seed}:permuted:{row['id']}:{question_id}".encode())
            candidates.append((key, row["id"], question_id))
    candidates.sort()
    chosen = candidates[:sample]
    out = []
    for _, parent_id, question_id in chosen:
        parent = next(r for r in clean if r["_meta"]["id"] == parent_id)
        join_row = next(j for j in join if j["id"] == parent_id)
        question = json.loads(json.dumps(parent["questions"][question_id]))
        keys = list(question["criteria"])
        _rng_for(seed, "shuffle", parent_id, question_id).shuffle(keys)
        question["criteria"] = {key: question["criteria"][key] for key in keys}
        variant_id = f"{parent_id}/{question_id}/permuted"
        out.append(_variant_record(parent, question_id, variant="permuted", record_id=variant_id,
                                   parent_id=parent_id, group=join_row["group_id"], row=len(clean) + len(out),
                                   questions=question))
    return out


def build_isolation(clean, join, seed=DEFAULT_SEED):
    """多问题记录：每个问题单独成一条记录（同一 state），用于 packed vs separate 对比。"""
    out = []
    for record, row in zip(clean, join):
        if len(record["questions"]) <= 1:
            continue
        for question_id, question in record["questions"].items():
            variant_id = f"{row['id']}/{question_id}/isolation"
            out.append(_variant_record(record, question_id, variant="isolation", record_id=variant_id,
                                       parent_id=row["id"], group=row["group_id"],
                                       row=len(clean) + len(out), questions=json.loads(json.dumps(question))))
    return out


def variant_join(records, base_join, *, kind):
    """为变体记录生成 join 行：沿用 parent 的 item/group/kind 元数据。"""
    by_id = {row["id"]: row for row in base_join}
    out = []
    for record in records:
        meta = record["_meta"]
        parent = by_id[meta["parent_id"]]
        questions = []
        for question_id in record["questions"]:
            source = next(q for q in parent["questions"] if q["qid"] == question_id)
            questions.append(dict(source))
        out.append({
            "id": meta["id"], "variant": meta["variant"], "item_id": parent["item_id"],
            "domain": parent["domain"], "lang": parent["lang"], "group_id": parent["group_id"],
            "parent_id": meta["parent_id"], "state_chars": parent["state_chars"],
            "questions": questions,
        })
    return out


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
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--out-suite", type=Path, required=True)
    parser.add_argument("--out-join", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--permuted-sample", type=int, default=0)
    parser.add_argument("--isolation", action="store_true")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--allow-inside-repo", action="store_true")
    args = parser.parse_args(argv)
    if args.permuted_sample < 0:
        parser.error("--permuted-sample must be >= 0")
    for path, flag in ((args.out_suite, "--out-suite"), (args.out_join, "--out-join")):
        assert_outside_repo(path, args.allow_inside_repo, flag)
    if args.manifest:
        assert_outside_repo(args.manifest, args.allow_inside_repo, "--manifest")
    records = read_jsonl(args.records)
    sidecar = read_jsonl(args.sidecar)
    if len(records) != len(sidecar):
        parser.error(f"records ({len(records)}) and sidecar ({len(sidecar)}) lengths differ")
    clean, join = assign_clean(records, sidecar)
    variants, variant_rows = [], []
    if args.permuted_sample:
        variants = build_permuted(clean, join, args.permuted_sample, seed=args.seed)
        variant_rows += variant_join(variants, join, kind="permuted")
    if args.isolation:
        isolated = build_isolation(clean, join, seed=args.seed)
        variants += isolated
        variant_rows += variant_join(isolated, join, kind="isolation")
    all_records = clean + variants
    all_join = join + variant_rows
    suite_path = args.out_suite / "development.jsonl"
    args.out_suite.mkdir(parents=True, exist_ok=True)
    data_sha = write_jsonl(suite_path, all_records)
    join_sha = write_jsonl(args.out_join, all_join)
    manifest = {
        "schema": SCHEMA,
        "holdout_sources": [],
        "eval_only": True,
        "context": dict(SERVING_CONTEXT),
        "files": {"development.jsonl": {"sha256": data_sha, "records": len(all_records)}},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "counts": {
            "clean_records": len(clean),
            "clean_questions": sum(len(row["questions"]) for row in join),
            "permuted_records": sum(1 for r in variants if r["_meta"]["variant"] == "permuted"),
            "isolation_records": sum(1 for r in variants if r["_meta"]["variant"] == "isolation"),
        },
        "variants": {"permuted_sample": args.permuted_sample, "isolation": bool(args.isolation)},
        "join_sha256": join_sha,
        "source": {
            "records_sha256": _sha256_bytes(Path(args.records).read_bytes()),
            "sidecar_sha256": _sha256_bytes(Path(args.sidecar).read_bytes()),
        },
        "note": "private evaluation suite; development.jsonl and join contain evaluation data and must stay outside the repo",
    }
    manifest_path = args.manifest or (args.out_suite / "manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"clean_records": len(clean), "variants": len(variants), "suite_records": len(all_records),
                      "suite_sha256": _sha256_bytes(manifest_path.read_bytes()),
                      "development_sha256": data_sha}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
