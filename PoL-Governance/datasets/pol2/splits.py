"""按场景族整体切分 PoL2 数据分区（70 / 20 / 5 / 5）。

族内不跨区：同一情节、翻译与改写永远落在同一分区。
分配使用仓库外私有盐值，因此公开仓库无法反推哪些族属于保留集；
仓库只保存流程与汇总计数。

    uv run --no-project --offline python datasets/pol2/splits.py assign \
        --families datasets/pol2/families.jsonl --salt-file <仓库外盐值> --out <仓库外分配表>
    uv run --no-project --offline python datasets/pol2/splits.py subset \
        --assign <分配表> --families datasets/pol2/families.jsonl \
        --regions train,public_test,validation --out datasets/pol2/families.public.jsonl
    uv run --no-project --offline python datasets/pol2/splits.py verify \
        --assign <分配表> --families datasets/pol2/families.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
REGIONS = ("train", "public_test", "validation", "private_holdout")
SHARES = {"train": 0.70, "public_test": 0.20, "validation": 0.05, "private_holdout": 0.05}
PUBLIC_REGIONS = ("train", "public_test", "validation")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: invalid JSON: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number}: each line must be an object")
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def load_families(path: Path) -> list[dict]:
    rows = read_jsonl(path)
    if not rows:
        raise ValueError(f"{path}: no families")
    seen = set()
    for row in rows:
        family_id = row.get("family_id")
        if not isinstance(family_id, str) or not family_id:
            raise ValueError(f"{path}: family_id must be a non-empty string")
        if family_id in seen:
            raise ValueError(f"{path}: duplicate family_id {family_id}")
        seen.add(family_id)
        target = row.get("target_cases")
        if not isinstance(target, int) or isinstance(target, bool) or target <= 0:
            raise ValueError(f"{path}: {family_id}: target_cases must be a positive integer")
    return rows


def inside_module(path: Path) -> bool:
    try:
        path.resolve().relative_to(MODULE_ROOT)
    except ValueError:
        return False
    return True


def assign(families: list[dict], salt: str) -> list[dict]:
    """Deterministic greedy assignment by case-count deficit.

    Ordering is fixed by the salted hash, so the same salt and family list always
    produce the same split, while an outside observer without the salt cannot
    reproduce which family went to the private holdout.
    """
    if not salt:
        raise ValueError("empty salt")
    total = sum(f["target_cases"] for f in families)
    order = sorted(families, key=lambda f: hashlib.sha256(
        (salt + "\x1f" + f["family_id"]).encode("utf-8")).hexdigest())
    assigned = {region: 0 for region in REGIONS}
    counts = {region: 0 for region in REGIONS}
    out = []
    for family in order:
        # Prefer regions that are still missing entirely, then the largest deficit.
        unmet = [r for r in REGIONS if counts[r] == 0]
        pool = unmet if unmet else list(REGIONS)
        region = max(pool, key=lambda r: (SHARES[r] * total - assigned[r], -REGIONS.index(r)))
        assigned[region] += family["target_cases"]
        counts[region] += 1
        out.append({"family_id": family["family_id"], "region": region,
                    "target_cases": family["target_cases"]})
    return out


def check_assignment(assign_rows: list[dict], families: list[dict]) -> dict:
    expected = {f["family_id"]: f["target_cases"] for f in families}
    seen: dict[str, str] = {}
    for row in assign_rows:
        family_id, region = row.get("family_id"), row.get("region")
        if family_id not in expected:
            raise ValueError(f"assignment names unknown family {family_id}")
        if family_id in seen:
            raise ValueError(f"family assigned twice: {family_id}")
        if region not in REGIONS:
            raise ValueError(f"{family_id}: unknown region {region}")
        seen[family_id] = region
    missing = sorted(set(expected) - set(seen))
    if missing:
        raise ValueError(f"{len(missing)} families unassigned, first: {missing[0]}")
    total = sum(expected.values())
    stats = {}
    for region in REGIONS:
        ids = [f for f, r in seen.items() if r == region]
        cases = sum(expected[f] for f in ids)
        if not ids:
            raise ValueError(f"region {region} has no family")
        stats[region] = {"families": len(ids), "cases": cases,
                         "case_share": round(cases / total, 4),
                         "target_share": SHARES[region]}
    for region, row in stats.items():
        if abs(row["case_share"] - row["target_share"]) > 0.03:
            raise ValueError(
                f"region {region} share {row['case_share']} off target {row['target_share']}")
    if sum(s["cases"] for s in stats.values()) != total:
        raise ValueError("case totals do not add up")
    return {"total_cases": total, "total_families": len(expected), "regions": stats}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_assign = sub.add_parser("assign", help="assign families to regions using a private salt")
    p_assign.add_argument("--families", type=Path, required=True)
    p_assign.add_argument("--salt-file", type=Path, required=True)
    p_assign.add_argument("--out", type=Path, required=True)
    p_assign.add_argument("--allow-inside-repo", action="store_true",
                          help="override the guard that keeps the assignment out of the repo")

    p_subset = sub.add_parser("subset", help="write the family list for public regions only")
    p_subset.add_argument("--assign", type=Path, required=True)
    p_subset.add_argument("--families", type=Path, required=True)
    p_subset.add_argument("--regions", default=",".join(PUBLIC_REGIONS))
    p_subset.add_argument("--out", type=Path, required=True)

    p_verify = sub.add_parser("verify", help="re-check an assignment against the family list")
    p_verify.add_argument("--assign", type=Path, required=True)
    p_verify.add_argument("--families", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        families = load_families(args.families)
        if args.command == "assign":
            if inside_module(args.out) and not args.allow_inside_repo:
                raise ValueError(
                    "refusing to write the assignment inside the repository: it names the "
                    "private holdout families. Write it outside, or pass --allow-inside-repo.")
            salt = args.salt_file.read_text(encoding="utf-8").strip()
            rows = assign(families, salt)
            stats = check_assignment(rows, families)
            write_jsonl(args.out, rows)
            print(json.dumps({"command": "assign", "out": str(args.out), **stats},
                             ensure_ascii=False, indent=2))
        elif args.command == "subset":
            regions = tuple(r.strip() for r in args.regions.split(",") if r.strip())
            unknown = [r for r in regions if r not in REGIONS]
            if unknown:
                raise ValueError(f"unknown regions: {unknown}")
            if "private_holdout" in regions:
                raise ValueError("private_holdout must never be written into the repository")
            keep = {row["family_id"] for row in read_jsonl(args.assign)
                    if row.get("region") in regions}
            if not keep:
                raise ValueError("no families selected")
            rows = [f for f in families if f["family_id"] in keep]
            if len(rows) != len(keep):
                raise ValueError("assignment names families missing from the family list")
            write_jsonl(args.out, rows)
            print(json.dumps({"command": "subset", "regions": list(regions),
                              "families": len(rows), "out": str(args.out)}, ensure_ascii=False))
        else:
            stats = check_assignment(read_jsonl(args.assign), families)
            print(json.dumps({"command": "verify", "status": "pass", **stats},
                             ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{args.command} failed: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
