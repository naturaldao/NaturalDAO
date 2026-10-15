#!/usr/bin/env python
"""内部 benchmark 包完整性校验（标准库，自包含，不联网）。

本文件是**模板**：包内副本名为 verify.py，由 datasets/general/data/splits/split.py 在打包时
逐字节复制（改动请改这里，不要只改包内副本——包内副本每次重切都会被覆盖）。

校验四件事，全部通过才退出 0：

1. 包内每个文件 sha256 与 manifest.json 一致；
2. 从 benchmark.jsonl 复算的条数、语言/域/原语分布、问题数、真值覆盖、来源分布与 manifest 一致；
3. 明文与解压后的数据不含裸 U+2028 / U+2029 / U+0085（它们在 JSON 里合法，但会被
   str.splitlines() 当成换行，把一条记录从中间劈开）；
4. 包内文件不在 git 跟踪列表里（git ls-files 为空），并打印 .gitignore 命中规则作为旁证。

用法：

    python verify.py                 # 在本目录内运行
    python verify.py --skip-git      # 没有 git 的环境（会明确标注该检查被跳过）

退出码：0 全部通过；1 校验失败；2 环境不可用（缺文件 / manifest 字段不全 / 缺 git 且未 --skip-git）。
本脚本只读包内文件，不修改任何东西，也不打印任何样本内容（只有路径、计数与哈希）。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST_NAME = "manifest.json"
DATA_NAME = "benchmark.jsonl"
SCHEMA = "pol-internal-benchmark-package/0.1"
LINE_SEPARATORS = (0x2028, 0x2029, 0x0085)
REQUIRED_MANIFEST_KEYS = ("schema", "files", "verifiable_counts", "generation", "sources")


class CheckError(Exception):
    """包不可用或校验逻辑无法继续。"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list:
    """按换行符切分读取（不用 splitlines，避免被 U+2028 之类劈开）。"""
    text = path.read_text(encoding="utf-8")
    rows = []
    for lineno, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CheckError(f"{path.name}:{lineno} JSON 解析失败: {exc}") from exc
        if not isinstance(row, dict):
            raise CheckError(f"{path.name}:{lineno} 不是 JSON 对象")
        for field in ("id", "domain", "lang", "questions"):
            if not row.get(field):
                raise CheckError(f"{path.name}:{lineno} 缺必填字段 {field}")
        if not isinstance(row.get("targets"), dict):
            raise CheckError(f"{path.name}:{lineno} targets 必须是对象")
        rows.append(row)
    return rows


def declared_group(row: dict):
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    for mapping in (row, source, meta):
        for key in ("group_id", "request_id", "family_id"):
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def compute_counts(rows) -> dict:
    """从数据复算的聚合统计（只算计数，不含任何样本内容）。

    打包脚本直接调用这个函数生成 manifest.verifiable_counts，保证"生成"与"校验"同一套口径。
    """
    by_lang: Counter = Counter()
    by_domain: Counter = Counter()
    by_kind: Counter = Counter()
    by_lang_kind: Counter = Counter()
    questions_by_kind: Counter = Counter()
    sources: dict = {}
    questions = 0
    with_answer = 0
    with_probs = 0
    with_declared = 0
    groups: set = set()
    for row in rows:
        lang = str(row.get("lang"))
        by_lang[lang] += 1
        by_domain[str(row.get("domain"))] += 1
        row_kinds = set()
        for question in row.get("questions") or []:
            if not isinstance(question, dict):
                continue
            questions += 1
            kind = str(question.get("kind"))
            questions_by_kind[kind] += 1
            row_kinds.add(kind)
        for kind in row_kinds:
            by_kind[kind] += 1
            by_lang_kind[f"{lang}/{kind}"] += 1
        for value in (row.get("targets") or {}).values():
            if isinstance(value, dict):
                if value.get("answer") is not None:
                    with_answer += 1
                if value.get("probs") is not None:
                    with_probs += 1
        group = declared_group(row)
        if group:
            with_declared += 1
            groups.add(group)
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        key = str(source.get("dataset"))
        entry = sources.setdefault(key, {"revision": str(source.get("revision")),
                                         "license": str(source.get("license")), "items": 0})
        entry["items"] += 1
    return {
        "items": len(rows),
        "by_lang": dict(sorted(by_lang.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "by_lang_kind": dict(sorted(by_lang_kind.items())),
        "questions": questions,
        "questions_by_kind": dict(sorted(questions_by_kind.items())),
        "questions_with_answer": with_answer,
        "questions_with_probs": with_probs,
        "items_with_declared_group_id": with_declared,
        "declared_groups": len(groups),
        "sources": {key: value for key, value in sorted(sources.items())},
    }


def compare_counts(expected: dict, actual: dict, problems: list) -> None:
    for key in sorted(set(expected) | set(actual)):
        if key not in expected:
            problems.append(f"verifiable_counts 多出字段 {key}")
        elif key not in actual:
            problems.append(f"verifiable_counts 缺字段 {key}")
        elif expected[key] != actual[key]:
            problems.append(f"{key}: manifest={expected[key]!r} 复算={actual[key]!r}")


def bare_separator_counts(package: Path, problems: list) -> dict:
    """逐个文件数裸分隔符；.gz 先解压再数（压缩流里查不出内容问题）。"""
    counts: dict = {}
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        if path.suffix == ".gz":
            try:
                data = gzip.open(path, "rb").read()
            except OSError as exc:
                problems.append(f"{path.name}: gzip 解压失败 {exc}")
                continue
        else:
            data = path.read_bytes()
        total = sum(data.count(chr(cp).encode("utf-8")) for cp in LINE_SEPARATORS)
        counts[path.name] = total
        if total:
            problems.append(f"{path.name}: 含 {total} 个裸 U+2028/U+2029/U+0085")
    return counts


def git_evidence(package: Path):
    """返回 git 跟踪与忽略证据；git 不可用时 available=False。"""
    try:
        top = subprocess.run(["git", "-C", str(package), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    except (OSError, FileNotFoundError):
        return {"available": False}
    if top.returncode != 0:
        return {"available": True, "inside_repo": False}
    repo = Path(top.stdout.strip())
    relative = package.resolve().relative_to(repo).as_posix()
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "--", relative + "/"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    ignored = subprocess.run(["git", "-C", str(repo), "check-ignore", "-v", "--",
                              f"{relative}/{DATA_NAME}", f"{relative}/{MANIFEST_NAME}"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"available": True, "inside_repo": True, "repo": repo.as_posix(), "relative": relative,
            "tracked": [line for line in tracked.stdout.splitlines() if line.strip()],
            "ignore_evidence": [line for line in ignored.stdout.splitlines() if line.strip()]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="内部 benchmark 包完整性校验")
    parser.add_argument("--package", type=Path, default=HERE, help="包目录（默认脚本所在目录）")
    parser.add_argument("--skip-git", action="store_true",
                        help="跳过 git 跟踪检查（没有 git 的环境；结果里会标为 SKIPPED）")
    args = parser.parse_args(argv)
    package = Path(args.package).resolve()
    problems: list = []
    notes: list = []

    manifest_path = package / MANIFEST_NAME
    data_path = package / DATA_NAME
    if not manifest_path.is_file() or not data_path.is_file():
        print(f"环境不可用：{package} 里缺 {MANIFEST_NAME} 或 {DATA_NAME}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"环境不可用：{MANIFEST_NAME} 解析失败 {exc}", file=sys.stderr)
        return 2
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing or manifest.get("schema") != SCHEMA:
        print(f"环境不可用：manifest 不是本包格式（缺 {missing}，schema={manifest.get('schema')!r}）；"
              "若刚重跑过切分脚本，请先重新生成 manifest", file=sys.stderr)
        return 2

    print("== 1. 文件 sha256 与 manifest 一致 ==")
    for entry in manifest["files"]:
        path = package / entry["path"]
        if not path.is_file():
            problems.append(f"缺文件 {entry['path']}")
            print(f"  [NG] {entry['path']} 不存在")
            continue
        digest = sha256_file(path)
        size = path.stat().st_size
        ok = digest == entry.get("sha256") and size == entry.get("bytes")
        print(f"  [{'OK' if ok else 'NG'}] {entry['path']} {size} B sha256={digest[:16]}")
        if digest != entry.get("sha256"):
            problems.append(f"{entry['path']} sha256 不一致")
        if size != entry.get("bytes"):
            problems.append(f"{entry['path']} 字节数不一致")

    print("== 2. 条数与分布可复算一致 ==")
    try:
        rows = read_rows(data_path)
    except CheckError as exc:
        print(f"  [NG] {exc}")
        problems.append(str(exc))
        rows = []
    if rows:
        actual = compute_counts(rows)
        compare_counts(manifest["verifiable_counts"], actual, problems)
        for key in ("items", "questions", "questions_with_answer", "questions_with_probs",
                    "declared_groups"):
            print(f"  {'OK' if not any(key in p for p in problems) else 'NG'} {key} = {actual[key]}")
        print(f"  {'OK' if not any('by_' in p or 'sources' in p for p in problems) else 'NG'} "
              f"分布与来源：lang={actual['by_lang']} domain={actual['by_domain']} "
              f"kind={actual['by_kind']}")

    print("== 3. 不含裸 U+2028 / U+2029 / U+0085 ==")
    separators = bare_separator_counts(package, problems)
    worst = {name: count for name, count in separators.items() if count}
    print(f"  [{'OK' if not worst else 'NG'}] 扫描 {len(separators)} 个文件（.gz 已解压后扫描），"
          f"命中 {len(worst)} 个" + (f"：{worst}" if worst else ""))

    print("== 4. 不在 git 跟踪列表里 ==")
    git = git_evidence(package)
    if args.skip_git:
        notes.append("git 跟踪检查被 --skip-git 跳过")
        print("  [SKIP] 按 --skip-git 跳过")
    elif not git.get("available"):
        print("  [NG] 找不到 git：无法证明未被跟踪（如确无 git，请显式加 --skip-git）")
        problems.append("git 不可用，无法证明未被跟踪")
    elif not git.get("inside_repo"):
        print("  [OK] 该目录不在任何 git 仓库内（比『已忽略』更强的证据）")
    else:
        tracked = git["tracked"]
        print(f"  [{'OK' if not tracked else 'NG'}] git ls-files {git['relative']}/ 返回 "
              f"{len(tracked)} 条" + (f"：{tracked[:5]}" if tracked else "（空）"))
        if tracked:
            problems.append(f"有 {len(tracked)} 个文件被 git 跟踪")
        for line in git["ignore_evidence"]:
            print(f"  忽略规则命中：{line}")
        if not git["ignore_evidence"]:
            notes.append("git check-ignore 没有命中规则（可能整个目录已被上层规则忽略）")

    print()
    for note in notes:
        print("注：" + note)
    if problems:
        print(f"结论：失败（{len(problems)} 项）")
        for problem in problems[:20]:
            print("  - " + problem)
        return 1
    print("结论：全部通过（sha256、条数与分布、无裸分隔符、未被 git 跟踪）")
    return 0


if __name__ == "__main__":
    # 管道/重定向时 Python 默认用系统 locale 编码，中文报告会变成不可复现的字节；统一按 UTF-8 输出。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
