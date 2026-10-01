"""一次性条款锚点迁移：旧编号 → 新编号（EAP 5→4、PoL 3→5、ENG 6.1→ENG.1）。

真源：datasets/pol2/ontology/pol2-labels.v0.1.json 的 anchor_audit.renumbering 与
retired_clause_prefixes；逐条复验见 datasets/pol2/ontology/clause-remap.md。

原则：
- 只替换 **clause 标识符**（EAP.5.x / PoL.3.x / ENG.6.1），不做自然语言替换
  （"第 5 章""3.4 节"这类叙述不匹配，因此不动）。
- 默认 --dry-run；--apply 才落盘。幂等：再跑一次命中数为 0、文件内容不变。
- **不重跑任何模型生成**：这是纯元数据字符串重映射，原地替换。
- 防复发常量（ontology 的 retired_clause_prefixes / check_ontology.py / test_ontology.py /
  clause-remap.md / 本脚本自身与测试）必须保留旧前缀，列入 allowlist，不改写也不计入"未清除"。
- generated case 的 input.policy 是条款文本的转述；新版第 1 章与 4.3.2 正文有改动，
  这些条目只进报告交 Lead 裁定，脚本不改写 policy 文本。

    uv run --no-project --offline python datasets/pol2/pipeline/migrate_anchors.py            # 预演
    uv run --no-project --offline python datasets/pol2/pipeline/migrate_anchors.py --apply \
        --report datasets/pol2/pipeline/smoke/anchor-migration-report.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT_DEFAULT = Path(__file__).resolve().parents[3]
SKIP_DIRS = {".git", "__pycache__", ".venv", ".cache", "node_modules", ".mypy_cache"}
BINARY_SUFFIXES = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".zip",
                   ".gz", ".woff", ".woff2", ".ico", ".pt", ".bin", ".safetensors", ".gguf",
                   ".so", ".dll", ".exe", ".xlsx", ".docx", ".pptx"}

# 有序规则：先长后短；lookbehind 保证不嵌在更长 token 里。
RULES = (
    (re.compile(r"(?<![A-Za-z0-9_.])ENG\.6\.1(?![0-9])"), "ENG.1"),
    (re.compile(r"(?<![A-Za-z0-9_.])ENG\.6(?![0-9.])"), "ENG.1"),
    (re.compile(r"(?<![A-Za-z0-9_.])EAP\.5\.(?=[0-9])"), "EAP.4."),
    (re.compile(r"(?<![A-Za-z0-9_.])EAP\.5(?![0-9.])"), "EAP.4"),
    (re.compile(r"(?<![A-Za-z0-9_.])PoL\.3\.(?=[0-9])"), "PoL.5."),
    (re.compile(r"(?<![A-Za-z0-9_.])PoL\.3(?![0-9.])"), "PoL.5"),
)

# 迁移后不应再出现的退役前缀（与本体 retired_clause_prefixes 一致）。
RETIRED = (re.compile(r"EAP\.5\."), re.compile(r"PoL\.3\.4"), re.compile(r"PoL\.3\.6"),
           re.compile(r"ENG\.6\."))

# 内容有实际改动的条款（新版编号）：第 1 章 + 4.3.2 新增三条例外。
DEFAULT_CHANGED_CLAUSES = ("PoL.1.1", "PoL.1.2", "PoL.1.3", "PoL.1.4", "PoL.1.5", "EAP.4.3.2")

# 允许保留旧前缀的文件（防复发常量与历史记录）：不改写，也不计入未清除。
ALLOWLIST = (
    "datasets/pol2/ontology/clause-remap.md",
    "datasets/pol2/ontology/pol2-labels.v0.1.json",
    "datasets/pol2/ontology/check_ontology.py",
    "datasets/pol2/ontology/test_ontology.py",
    "datasets/pol2/ontology/README.md",
    "datasets/pol2/pipeline/migrate_anchors.py",
    "datasets/pol2/pipeline/tests/test_migrate_anchors.py",
)


def count_hits(text):
    return sum(len(pattern.findall(text)) for pattern in RETIRED)


def migrate_text(text):
    """Apply the ordered rules; returns (new_text, hits)."""
    hits = 0
    for pattern, replacement in RULES:
        text, count = pattern.subn(replacement, text)
        hits += count
    return text, hits


def is_allowlisted(relative):
    return any(relative == item or relative.startswith(item.rstrip("/") + "/")
               for item in ALLOWLIST)


def iter_files(root, includes=(), skip=()):
    root = Path(root)
    skip = {Path(item).resolve() for item in skip}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() in skip:
            continue  # 报告/清单自身会记录旧前缀，不参与扫描
        relative = path.relative_to(root).as_posix()
        if set(path.relative_to(root).parts) & SKIP_DIRS:
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        if includes and not any(relative.startswith(prefix) for prefix in includes):
            continue
        yield path, relative


def decode(path):
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan(root, includes=(), skip=()):
    """Return (files_report, total_hits, policy_entries)."""
    files_report, total, policy_entries = [], 0, []
    for path, relative in iter_files(root, includes, skip):
        text = decode(path)
        if text is None:
            continue
        hits = count_hits(text)
        if path.name.endswith(".cases.jsonl"):
            policy_entries.extend(collect_policy_entries(text, relative))
        if hits:
            files_report.append({"path": relative, "hits": hits,
                                 "allowed": is_allowlisted(relative)})
            total += hits
    return files_report, total, policy_entries


def collect_policy_entries(text, relative, changed=DEFAULT_CHANGED_CLAUSES):
    """Cases whose clause is content-changed → 交 Lead 裁定（不改写 policy 文本）。"""
    changed = set(changed)
    entries = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        inp = row.get("input")
        if not isinstance(inp, dict):
            continue
        clause = inp.get("clause")
        if not isinstance(clause, str):
            continue
        new_clause, _hits = migrate_text(clause)
        if new_clause not in changed:
            continue
        policy = inp.get("policy") if isinstance(inp.get("policy"), str) else ""
        anchors = sorted({match.group(0) for pattern, _r in RULES
                          for match in pattern.finditer(policy)})
        entries.append({"file": relative, "line": number, "id": row.get("id"),
                        "family_id": row.get("family_id"), "region": row.get("region"),
                        "clause_old": clause, "clause_new": new_clause,
                        "policy_mentions_anchor": bool(anchors), "policy_anchors": anchors,
                        "policy": policy})
    return entries


def rewrite_gz_siblings(root, changed_paths):
    """明文改完后，用同一内容重建同名 .gz（mtime=0，保证可复现）。"""
    done = []
    for relative in changed_paths:
        packed = root / (relative + ".gz")
        plain = root / relative
        if not packed.is_file() or not plain.is_file():
            continue
        data = plain.read_bytes()
        with open(packed, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                stream.write(data)
        done.append(packed.relative_to(root).as_posix())
    return done


def run(root, apply=False, includes=(), changed=DEFAULT_CHANGED_CLAUSES, skip=()):
    root = Path(root)
    before_files, hits_before, policy_entries = scan(root, includes, skip)
    changed_paths = []
    for entry in before_files:
        if entry["allowed"]:
            continue
        path = root / entry["path"]
        text = decode(path)
        if text is None:
            continue
        new_text, hits = migrate_text(text)
        if hits and new_text != text:
            if apply:
                path.write_text(new_text, encoding="utf-8", newline="")
            changed_paths.append({"path": entry["path"], "hits": hits})
    regzipped = rewrite_gz_siblings(root, [row["path"] for row in changed_paths]) if apply else []
    after_files, hits_after, _ = scan(root, includes, skip)
    unexpected = [row for row in after_files if not row["allowed"]]
    allowed_residual = [row for row in after_files if row["allowed"]]
    return {
        "mode": "apply" if apply else "dry-run",
        "root": str(root),
        "rules": [{"pattern": pattern.pattern, "replacement": replacement}
                  for pattern, replacement in RULES],
        "retired_prefixes": ["EAP.5.", "PoL.3.4", "PoL.3.6", "ENG.6."],
        "files_with_hits_before": len(before_files),
        "hits_before": hits_before,
        "allowed_files_with_hits": [row for row in before_files if row["allowed"]],
        "changed_files": changed_paths,
        "changed_file_count": len(changed_paths),
        "changed_hits": sum(row["hits"] for row in changed_paths),
        "regzipped": regzipped,
        "hits_after": hits_after,
        "hits_after_outside_allowlist": sum(row["hits"] for row in unexpected),
        "unexpected_files_after": unexpected,
        "allowlisted_residual": allowed_residual,
        "policy_review": {
            "changed_clauses": list(changed),
            "count": len(policy_entries),
            "cases": len({entry["id"] for entry in policy_entries}),
            "by_clause": {clause: sum(1 for entry in policy_entries
                                      if entry["clause_new"] == clause)
                          for clause in sorted({entry["clause_new"]
                                                for entry in policy_entries})},
            "policy_mentions_anchor": sum(1 for entry in policy_entries
                                          if entry["policy_mentions_anchor"]),
            "entries": policy_entries},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--apply", action="store_true", help="真正落盘（默认只预演）")
    parser.add_argument("--include", action="append", default=[],
                        help="只处理这些相对路径前缀，可重复")
    parser.add_argument("--report", type=Path, help="完整 JSON 报告写到哪里")
    parser.add_argument("--policy-out", type=Path,
                        help="policy 待裁定清单 JSONL（默认写到报告同目录 policy-review.jsonl）")
    parser.add_argument("--changed-clauses", default=",".join(DEFAULT_CHANGED_CLAUSES),
                        help="内容有改动的条款（新编号），逗号分隔")
    args = parser.parse_args(argv)
    changed = tuple(item.strip() for item in args.changed_clauses.split(",") if item.strip())
    policy_target = args.policy_out or ((args.report.parent / "policy-review.jsonl")
                                        if args.report else None)
    # 报告与清单自身会记录旧前缀，构建时就排除，避免下一次运行时把它们当成待迁移文件。
    skip = [path for path in (args.report, policy_target) if path is not None]
    report = run(args.root, apply=args.apply, includes=args.include, changed=changed, skip=skip)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    entries = report["policy_review"]["entries"]
    if entries and policy_target:
        policy_target.parent.mkdir(parents=True, exist_ok=True)
        policy_target.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n"
                                         for entry in entries), encoding="utf-8")
        report["policy_review"]["written_to"] = str(policy_target)
    print(json.dumps({key: report[key] for key in
                      ("mode", "root", "files_with_hits_before", "hits_before",
                       "changed_file_count", "changed_hits", "regzipped", "hits_after",
                       "hits_after_outside_allowlist", "unexpected_files_after",
                       "allowlisted_residual")}, ensure_ascii=False, indent=1))
    print(json.dumps({"policy_review": {key: value for key, value in
                                        report["policy_review"].items() if key != "entries"}},
                     ensure_ascii=False, indent=1))
    return 1 if report["hits_after_outside_allowlist"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
