"""最终评测包的可复现打包器（finetune/prepare_eval_package.py）。

把最终评测所需的脚本按原目录结构复制到 `results/MODEL-02-final-eval/eval-package/`，
生成 MANIFEST.json 与 CHECKSUMS.sha256，供第三方审计；`--check` 只读校验包与仓库是否一致。

用法::

    python finetune/prepare_eval_package.py \
        --versions results/MODEL-02-final-eval/versions.json \
        [--repo-root .] --out results/MODEL-02-final-eval/eval-package [--check] [--force]

接口契约见 .agent/notes/2026-10-27-final-eval-package-spec.md §4。设计取舍：

1. 白名单（`WHITELIST`）固定，dest 保持原目录结构；**白名单外的文件绝不复制**。
   package 目录里出现白名单外的文件按错误处理（fail-closed）：CHECKSUMS.sha256 必须覆盖
   “除自身外全部文件”，来源不明的文件会破坏可审计性。请先删掉它再生成。
2. README.md 是人工撰写的说明文件：优先使用 `<out>/README.md`（直接写在 package 里，
   生成时绝不覆盖、也不与源文件做“漂移”比较）；不存在时按白名单从
   `<repo-root>/README.md` 复制一份。两处都不存在 → 生成阶段 exit 2，`--check` 报违规。
3. MANIFEST.json 的 `files` 只列 package 内的内容文件（白名单文件 + README.md），
   不含 MANIFEST.json 与 CHECKSUMS.sha256 自身（互相哈希会成环）。
   CHECKSUMS.sha256 覆盖除自身外的全部文件（含 README.md 与 MANIFEST.json）。
4. `package_sha256` = sha256(去掉该字段后的规范 JSON)，规范 JSON 为
   `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)` 的 UTF-8 字节。
5. 输出确定性：无时间戳、无随机源；JSON 为 indent=2 + UTF-8 + 末行换行；
   CHECKSUMS.sha256 每行 `<sha256>  <relpath>`（两个空格）按 path 排序；文件按字节复制，
   不做换行转换，因此连续两次生成的字节一致。
6. `--check` 只读：核对（a）package 文件与仓库源文件一致（漂移）、（b）MANIFEST 与
   CHECKSUMS 自洽（篡改）、（c）文件缺失/多余；通过打印 `{"status":"pass","files":N}`，
   失败逐条打印 `VIOLATION: ...` 并 exit 2。
7. `git_commit` 由 `--git-commit` 给出，否则 `git rev-parse HEAD`（只读，禁止 fetch）；
   取不到时记为 `"unknown"`，此时 `--check` 不把它当漂移（该字段仍受
   `package_sha256` 的篡改检测覆盖）。
8. CLI 错误统一 exit 2（与 finetune/calibrate.py 一致）；只用标准库，不 import torch，
   不联网，不读写任何私有保留集。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "pol-final-eval-package-v1"
MANIFEST_NAME = "MANIFEST.json"
CHECKSUMS_NAME = "CHECKSUMS.sha256"
README_NAME = "README.md"

# 允许复制进评测包的文件（src 相对路径 == dest 相对路径）。README.md 单独处理，见模块 docstring。
WHITELIST: Tuple[str, ...] = (
    "finetune/__init__.py",
    "finetune/decision_common.py",
    "finetune/eval_decision.py",
    "finetune/calibrate.py",
    "finetune/collect_results.py",
    "finetune/final_eval_aggregate.py",
    "finetune/check_aggregate_export.py",
    "finetune/bench_latency.py",
    "datasets/__init__.py",
    "datasets/general/__init__.py",
    "datasets/general/build_training_view.py",
)

CHECKSUM_LINE = re.compile(r"([0-9a-f]{64})  (.+)")


# ---------------------------------------------------------------------------
# 哈希与序列化
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    """返回字节串的 SHA256 十六进制摘要。"""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """流式计算文件的 SHA256（不整文件读入内存）。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_signature(path: Path) -> Tuple[str, int]:
    """返回 (sha256, 字节数)，供 MANIFEST / 比较使用。"""
    return sha256_file(path), path.stat().st_size


def canonical_package_digest(manifest: Dict[str, Any]) -> str:
    """package_sha256：对去掉 package_sha256 字段后的规范 JSON 取 sha256。"""
    payload = {key: value for key, value in manifest.items() if key != "package_sha256"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(canonical.encode("utf-8"))


def render_manifest(manifest: Dict[str, Any]) -> bytes:
    """MANIFEST.json 的确定性字节：indent=2、UTF-8、末行换行。"""
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def render_checksums(entries: Dict[str, str]) -> bytes:
    """CHECKSUMS.sha256 的确定性字节：path 排序，`<sha256>  <relpath>`，LF。"""
    lines = [f"{digest}  {rel_path}" for rel_path, digest in sorted(entries.items())]
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_manifest(git_commit: str, versions: Dict[str, Any],
                   signatures: Dict[str, Tuple[str, int]]) -> Dict[str, Any]:
    """按契约构造 MANIFEST 字典（files 按 path 排序，最后写入 package_sha256）。"""
    manifest: Dict[str, Any] = {
        "schema": SCHEMA,
        "git_commit": git_commit,
        "versions": versions,
        "files": [
            {"path": rel_path, "sha256": digest, "bytes": size}
            for rel_path, (digest, size) in sorted(signatures.items())
        ],
    }
    manifest["package_sha256"] = canonical_package_digest(manifest)
    return manifest


# ---------------------------------------------------------------------------
# 输入解析
# ---------------------------------------------------------------------------


def load_versions(path: Path, repo_root: Path) -> Dict[str, Any]:
    """读取 versions.json（原样嵌入 MANIFEST）；相对路径找不到时再相对 --repo-root 试一次。"""
    resolved = path
    if not resolved.is_absolute() and not resolved.is_file():
        candidate = repo_root / resolved
        if candidate.is_file():
            resolved = candidate
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{resolved}: versions 必须是 JSON 对象")
    return data


def resolve_git_commit(repo_root: Path, explicit: Optional[str]) -> str:
    """--git-commit 优先；否则 git rev-parse HEAD（只读，不 fetch），失败记为 unknown。"""
    if explicit is not None:
        value = explicit.strip()
        if not value:
            raise ValueError("--git-commit 不能为空")
        return value
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    value = completed.stdout.strip()
    return value or "unknown"


# ---------------------------------------------------------------------------
# 文件收集
# ---------------------------------------------------------------------------


def resolve_sources(repo_root: Path, out_dir: Path) -> Tuple[Dict[str, Path], List[str]]:
    """返回 (rel_path -> 源文件, 缺失的 rel_path 列表)。

    README.md 的来源优先级：`<out>/README.md`（人工撰写，已在 package 内）>
    `<repo-root>/README.md`（按白名单复制）。两处都没有则计入缺失。
    """
    sources: Dict[str, Path] = {}
    missing: List[str] = []
    for rel_path in WHITELIST:
        candidate = repo_root / rel_path
        if candidate.is_file():
            sources[rel_path] = candidate
        else:
            missing.append(rel_path)
    package_readme = out_dir / README_NAME
    repo_readme = repo_root / README_NAME
    if package_readme.is_file():
        sources[README_NAME] = package_readme
    elif repo_readme.is_file():
        sources[README_NAME] = repo_readme
    else:
        missing.append(README_NAME)
    return sources, missing


def iter_package_files(out_dir: Path) -> List[str]:
    """列出 package 目录内所有普通文件（相对路径，POSIX 分隔符）。"""
    if not out_dir.is_dir():
        return []
    return sorted(path.relative_to(out_dir).as_posix()
                  for path in out_dir.rglob("*") if path.is_file())


def require_sources(repo_root: Path, out_dir: Path) -> Dict[str, Path]:
    """resolve_sources 的 fail-closed 版本：缺任何白名单文件都抛 ValueError 并说明位置。"""
    sources, missing = resolve_sources(repo_root, out_dir)
    if missing:
        scripts = [rel_path for rel_path in missing if rel_path != README_NAME]
        parts: List[str] = []
        if scripts:
            parts.append("缺少白名单源文件: " + ", ".join(str(repo_root / rel_path)
                                                     for rel_path in scripts))
        if README_NAME in missing:
            parts.append(f"缺少 {README_NAME}: 需人工撰写在 {out_dir / README_NAME}"
                         f" 或 {repo_root / README_NAME}")
        raise ValueError("；".join(parts))
    return sources


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------


def generate_package(repo_root: Path, out_dir: Path, versions: Dict[str, Any],
                     git_commit: str, force: bool = False) -> Dict[str, Any]:
    """把白名单文件写进 package 并生成 MANIFEST/CHECKSUMS；返回摘要字典。"""
    sources = require_sources(repo_root, out_dir)
    if out_dir.exists() and not out_dir.is_dir():
        raise ValueError(f"--out 已存在但不是目录: {out_dir}")

    contents: Dict[str, bytes] = {}
    signatures: Dict[str, Tuple[str, int]] = {}
    for rel_path, source in sources.items():
        data = source.read_bytes()
        contents[rel_path] = data
        signatures[rel_path] = (sha256_bytes(data), len(data))

    manifest_bytes = render_manifest(build_manifest(git_commit, versions, signatures))
    checksum_entries = {rel_path: digest for rel_path, (digest, _size) in signatures.items()}
    checksum_entries[MANIFEST_NAME] = sha256_bytes(manifest_bytes)
    checksums_bytes = render_checksums(checksum_entries)

    targets: Dict[str, bytes] = dict(contents)
    targets[MANIFEST_NAME] = manifest_bytes
    targets[CHECKSUMS_NAME] = checksums_bytes

    if out_dir.is_dir():
        managed = set(targets)
        unexpected = [rel_path for rel_path in iter_package_files(out_dir)
                      if rel_path not in managed]
        if unexpected:
            raise ValueError("package 目录里存在白名单外文件（请先删除）: "
                             + ", ".join(unexpected))
        for rel_path in sorted(targets):
            target = out_dir / rel_path
            if target.exists() and not target.is_file():
                raise ValueError(f"package 目标路径已存在且不是普通文件: {target}")
        if not force:
            conflicts = sorted(
                rel_path for rel_path, data in targets.items()
                if (out_dir / rel_path).is_file() and (out_dir / rel_path).read_bytes() != data
            )
            if conflicts:
                raise ValueError("package 已存在且与本次生成不一致（确认后用 --force 覆盖）: "
                                 + ", ".join(conflicts))

    writes = {rel_path: data for rel_path, data in targets.items()
              if not (out_dir / rel_path).is_file()
              or (out_dir / rel_path).read_bytes() != data}

    out_dir.mkdir(parents=True, exist_ok=True)
    order = sorted(rel_path for rel_path in writes
                   if rel_path not in (MANIFEST_NAME, CHECKSUMS_NAME))
    order += [rel_path for rel_path in (MANIFEST_NAME, CHECKSUMS_NAME) if rel_path in writes]
    for rel_path in order:
        target = out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(writes[rel_path])

    return {
        "status": "written" if writes else "unchanged",
        "files": len(signatures),
        "out": str(out_dir),
    }


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------


def read_json_object(path: Path, label: str) -> Dict[str, Any]:
    """读 JSON 对象；不是对象时抛 ValueError（fail-closed）。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: {label} 必须是 JSON 对象")
    return data


def manifest_violations(manifest: Dict[str, Any], expected: Dict[str, Tuple[str, int]],
                        versions: Dict[str, Any], git_commit: str) -> List[str]:
    """MANIFEST 与预期内容/versions/git_commit 的逐项比对。"""
    violations: List[str] = []
    if manifest.get("schema") != SCHEMA:
        violations.append(f"MANIFEST schema 不符: {manifest.get('schema')!r} != {SCHEMA!r}")
    recorded_commit = manifest.get("git_commit")
    if not isinstance(recorded_commit, str) or not recorded_commit:
        violations.append("MANIFEST git_commit 必须是非空字符串")
    elif git_commit != "unknown" and recorded_commit != git_commit:
        violations.append(f"MANIFEST git_commit 漂移: {recorded_commit} != {git_commit}")
    if manifest.get("versions") != versions:
        violations.append("MANIFEST versions 与 --versions 内容不一致")

    files = manifest.get("files")
    if not isinstance(files, list):
        violations.append("MANIFEST files 必须是列表")
        files = []
    recorded: Dict[str, Tuple[str, int]] = {}
    order: List[str] = []
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            violations.append(f"MANIFEST files[{index}] 必须是对象")
            continue
        rel_path = entry.get("path")
        digest = entry.get("sha256")
        size = entry.get("bytes")
        if (not isinstance(rel_path, str) or not isinstance(digest, str)
                or not isinstance(size, int) or isinstance(size, bool)):
            violations.append(f"MANIFEST files[{index}] 需要 path(str)/sha256(str)/bytes(int)")
            continue
        if rel_path in recorded:
            violations.append(f"MANIFEST files 重复 path: {rel_path}")
        recorded[rel_path] = (digest, size)
        order.append(rel_path)
    if order != sorted(order):
        violations.append("MANIFEST files 必须按 path 排序")
    for rel_path in sorted(set(recorded) - set(expected)):
        violations.append(f"MANIFEST 列出了白名单外文件: {rel_path}")
    for rel_path in sorted(set(expected) - set(recorded)):
        violations.append(f"MANIFEST 缺少条目: {rel_path}")
    for rel_path in sorted(set(recorded) & set(expected)):
        if recorded[rel_path] != expected[rel_path]:
            violations.append(f"MANIFEST 条目与源文件不一致: {rel_path} "
                              f"{recorded[rel_path]} != {expected[rel_path]}")
    package_sha = manifest.get("package_sha256")
    if not isinstance(package_sha, str) or len(package_sha) != 64:
        violations.append("MANIFEST package_sha256 必须是 64 位十六进制字符串")
    elif package_sha != canonical_package_digest(manifest):
        violations.append("MANIFEST package_sha256 与自身内容不符（疑似篡改）")
    return violations


def checksums_violations(path: Path, out_dir: Path, package_files: List[str]) -> List[str]:
    """CHECKSUMS.sha256 的格式、覆盖范围与逐文件哈希核对。"""
    violations: List[str] = []
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return [f"{CHECKSUMS_NAME} 不是合法 UTF-8"]
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    else:
        violations.append(f"{CHECKSUMS_NAME} 必须以换行结尾")
    recorded: Dict[str, str] = {}
    order: List[str] = []
    for number, line in enumerate(lines, 1):
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            violations.append(f"{CHECKSUMS_NAME}:{number}: 格式错误（应为 '<sha256>  <relpath>'）")
            continue
        digest, rel_path = match.group(1), match.group(2)
        if rel_path in recorded:
            violations.append(f"{CHECKSUMS_NAME}:{number}: 重复 path {rel_path}")
        recorded[rel_path] = digest
        order.append(rel_path)
    if order != sorted(order):
        violations.append(f"{CHECKSUMS_NAME} 必须按 path 排序")
    covered = set(package_files) - {CHECKSUMS_NAME}
    for rel_path in sorted(covered - set(recorded)):
        violations.append(f"{CHECKSUMS_NAME} 缺少条目: {rel_path}")
    for rel_path in sorted(set(recorded) - covered):
        violations.append(f"{CHECKSUMS_NAME} 列出了不存在的文件: {rel_path}")
    for rel_path in sorted(covered & set(recorded)):
        if sha256_file(out_dir / rel_path) != recorded[rel_path]:
            violations.append(f"{CHECKSUMS_NAME} 哈希不符（疑似篡改）: {rel_path}")
    return violations


def check_package(repo_root: Path, out_dir: Path, versions: Dict[str, Any],
                  git_commit: str) -> Tuple[List[str], int]:
    """只读校验 package；返回 (违规列表, 内容文件数)。"""
    if not out_dir.is_dir():
        return [f"package 目录不存在: {out_dir}"], 0
    sources, missing = resolve_sources(repo_root, out_dir)
    violations: List[str] = []
    for rel_path in missing:
        if rel_path == README_NAME:
            violations.append(f"缺少 {README_NAME}: {out_dir / README_NAME} 与 "
                              f"{repo_root / README_NAME} 都不存在")
        else:
            violations.append(f"缺少白名单源文件: {repo_root / rel_path}")
    if missing:
        return violations, 0

    expected = {rel_path: file_signature(source) for rel_path, source in sources.items()}
    package_files = iter_package_files(out_dir)
    managed = set(expected) | {MANIFEST_NAME, CHECKSUMS_NAME}
    for rel_path in package_files:
        if rel_path not in managed:
            violations.append(f"package 目录里存在白名单外文件: {rel_path}")

    actual: Dict[str, Tuple[str, int]] = {}
    for rel_path in expected:
        target = out_dir / rel_path
        if target.is_file():
            actual[rel_path] = file_signature(target)
        else:
            violations.append(f"package 缺少文件: {rel_path}")
    for rel_path in sorted(expected):
        if rel_path in actual and actual[rel_path] != expected[rel_path]:
            violations.append(f"源文件漂移: {rel_path}（源 {expected[rel_path][0]} != "
                              f"package {actual[rel_path][0]}）")

    manifest_path = out_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        violations.append(f"缺少 {MANIFEST_NAME}")
    else:
        try:
            manifest = read_json_object(manifest_path, MANIFEST_NAME)
        except ValueError as error:
            violations.append(str(error))
        else:
            violations.extend(manifest_violations(manifest, expected, versions, git_commit))

    checksums_path = out_dir / CHECKSUMS_NAME
    if not checksums_path.is_file():
        violations.append(f"缺少 {CHECKSUMS_NAME}")
    else:
        violations.extend(checksums_violations(checksums_path, out_dir, package_files))
    return violations, len(expected)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--versions", type=Path, required=True,
                        help="versions.json 路径（相对路径先按当前目录解析，找不到再相对 --repo-root）")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="仓库根目录（默认当前目录）")
    parser.add_argument("--out", type=Path, required=True, help="评测包输出目录")
    parser.add_argument("--check", action="store_true", help="只读校验，不写任何文件")
    parser.add_argument("--force", action="store_true",
                        help="允许覆盖已存在且内容不一致的 package 文件")
    parser.add_argument("--git-commit",
                        help="写入 MANIFEST 的 commit（默认 git rev-parse HEAD）；"
                             "--check 时只有显式给出才比对 commit，否则只校验逐文件哈希")
    args = parser.parse_args(argv)
    try:
        repo_root = Path(args.repo_root).resolve()
        if not repo_root.is_dir():
            raise ValueError(f"--repo-root 不是目录: {repo_root}")
        out_dir = Path(args.out).resolve()
        if out_dir == repo_root or out_dir in repo_root.parents:
            raise ValueError(f"--out 不能是仓库根目录本身或其祖先目录: {out_dir}")
        versions = load_versions(Path(args.versions), repo_root)
        git_commit = resolve_git_commit(repo_root, args.git_commit)
        if args.check:
            # --check 默认不比对 git_commit（MANIFEST 记录的是"代码所属 commit"，之后
            # 提交 manifest 本身会让 HEAD 前移；真正的一致性由逐文件 sha256 保证）。
            # 需要钉住 commit 时显式传 --git-commit。
            check_commit = git_commit if args.git_commit is not None else "unknown"
            violations, files = check_package(repo_root, out_dir, versions, check_commit)
            if violations:
                for line in violations:
                    print(f"VIOLATION: {line}", file=sys.stderr)
                print(json.dumps({"status": "fail", "violations": len(violations)},
                                 ensure_ascii=False))
                return 2
            print(json.dumps({"status": "pass", "files": files}, ensure_ascii=False))
            return 0
        summary = generate_package(repo_root, out_dir, versions, git_commit, force=args.force)
        if git_commit == "unknown":
            print("警告: 无法读取 git commit，MANIFEST.git_commit 记为 'unknown'",
                  file=sys.stderr)
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as error:
        print(f"prepare_eval_package failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
