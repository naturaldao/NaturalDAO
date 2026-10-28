"""上传后远程校验：HF 仓库文件 vs 本地导出 MANIFEST（纯标准库 + 只读网络）。

用途：owner/维护者把 hf-export/public 或 private-holdout 上传到 Hugging Face 之后，
在本地校验远端仓库内容与本地产物逐文件一致（sha256 / bytes / 缺失 / 多余）。

示例：
    python datasets/general/verify_hf_remote.py \
        --repo-id <org>/pol-decision-general-v5 \
        --manifest datasets/general/data/hf-export/public/MANIFEST.json

    # 私有仓库：token 从仓库外文件读取（绝不写进仓库/日志）
    python datasets/general/verify_hf_remote.py \
        --repo-id <org>/pol-decision-general-v5-holdout \
        --manifest datasets/general/data/hf-export/private-holdout/HF-MANIFEST.json \
        --token-file ~/.hf_token

安全与网络：
- 只发 GET 请求；不写远端；token 只放 Authorization 头，不打印；
- 未公开/不存在的仓库通常返回 401（HF 不区分私有与不存在），需要 --token-file；
- 默认只读清单（tree API）；对非 LFS 小文件（<= --max-download-bytes）额外下载原始字节复算 sha256。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

HF_API = "https://huggingface.co"
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024

# 远端 tree 条目中可能有这些字段：
#   path, size, oid, lfs: {oid, size, pointerSize}, type: file|directory
STATUS_MATCH = "match"
STATUS_SHA_MISMATCH = "sha256_mismatch"
STATUS_SIZE_MISMATCH = "size_mismatch"
STATUS_MISSING = "missing"
STATUS_SIZE_ONLY = "size_only_verified"
STATUS_SKIPPED = "skipped_large_unverified"
STATUS_EXTRA = "extra_on_remote"


class RemoteVerifyError(RuntimeError):
    """网络或输入错误（exit 2）。"""


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError(f"{path}: 缺少非空 files 列表")
    result: List[Dict[str, Any]] = []
    for item in files:
        name = item.get("path")
        size = item.get("bytes", item.get("size"))
        sha = item.get("sha256")
        if not isinstance(name, str) or not isinstance(size, int):
            raise ValueError(f"{path}: 文件项缺少 path/bytes: {item!r}")
        result.append({"path": name, "bytes": size, "sha256": sha})
    return result


def parse_next_link(link_header: Optional[str]) -> Optional[str]:
    if not link_header:
        return None
    match = re.search(r'<([^>]+)>\s*;\s*rel="next"', link_header)
    return match.group(1) if match else None


def _request(url: str, token: Optional[str], timeout: int = 30) -> Tuple[int, bytes, str]:
    headers = {"User-Agent": "polgov-hf-verify/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get("Link", "") or ""
    except urllib.error.HTTPError as error:
        return error.code, b"", ""
    except urllib.error.URLError as error:
        raise RemoteVerifyError(f"无法连接 {HF_API}: {error.reason}") from error


def fetch_tree(repo_id: str, revision: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """递归列出 dataset 仓库文件（处理分页）。"""
    url = f"{HF_API}/api/datasets/{repo_id}/tree/{revision}?recursive=true"
    entries: List[Dict[str, Any]] = []
    while url:
        status, body, link = _request(url, token)
        if status in (401, 403):
            raise RemoteVerifyError(
                f"{repo_id} 返回 {status}：仓库不存在或私有（HF 不区分）；私有仓库请提供 --token-file"
            )
        if status == 404:
            raise RemoteVerifyError(f"{repo_id} 不存在（404）")
        if status != 200:
            raise RemoteVerifyError(f"{repo_id} tree API 返回 {status}")
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, list):
            raise RemoteVerifyError(f"{repo_id}: tree API 返回非列表")
        entries.extend(payload)
        url = parse_next_link(link)
    return [entry for entry in entries if entry.get("type", "file") == "file"]


def fetch_raw(repo_id: str, revision: str, path: str, token: Optional[str] = None) -> bytes:
    url = f"{HF_API}/datasets/{repo_id}/resolve/{revision}/{path}"
    status, body, _ = _request(url, token)
    if status != 200:
        raise RemoteVerifyError(f"{repo_id}/{path} 下载失败: HTTP {status}")
    return body


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compare(
    manifest_files: List[Dict[str, Any]],
    tree_entries: List[Dict[str, Any]],
    raw_fetcher: Optional[Callable[[str], bytes]] = None,
    max_download_bytes: int = MAX_DOWNLOAD_BYTES,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """逐文件比较。raw_fetcher(path)->bytes 可选（用于非 LFS 小文件 sha 复算）。"""
    remote: Dict[str, Dict[str, Any]] = {}
    for entry in tree_entries:
        path = entry.get("path")
        if isinstance(path, str):
            remote[path] = entry
    results: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {STATUS_MATCH: 0, STATUS_SHA_MISMATCH: 0, STATUS_SIZE_MISMATCH: 0,
                              STATUS_MISSING: 0, STATUS_SIZE_ONLY: 0, STATUS_SKIPPED: 0}
    expected_paths = {item["path"] for item in manifest_files}
    for item in manifest_files:
        path = item["path"]
        expected_size = item["bytes"]
        expected_sha = item.get("sha256")
        entry = remote.get(path)
        if entry is None:
            counts[STATUS_MISSING] += 1
            results.append({"path": path, "status": STATUS_MISSING,
                            "expected_bytes": expected_size})
            continue
        remote_size = entry.get("size")
        if isinstance(remote_size, int) and remote_size != expected_size:
            counts[STATUS_SIZE_MISMATCH] += 1
            results.append({"path": path, "status": STATUS_SIZE_MISMATCH,
                            "expected_bytes": expected_size, "remote_bytes": remote_size})
            continue
        lfs = entry.get("lfs") if isinstance(entry.get("lfs"), dict) else None
        remote_sha = lfs.get("oid") if lfs else entry.get("sha256")
        if isinstance(remote_sha, str) and expected_sha:
            if remote_sha.lower() == expected_sha.lower():
                counts[STATUS_MATCH] += 1
                results.append({"path": path, "status": STATUS_MATCH, "bytes": expected_size,
                                "sha256": expected_sha, "via": "lfs" if lfs else "tree"})
            else:
                counts[STATUS_SHA_MISMATCH] += 1
                results.append({"path": path, "status": STATUS_SHA_MISMATCH,
                                "expected_sha256": expected_sha, "remote_sha256": remote_sha})
            continue
        # 非 LFS 且无法从 tree 得到 sha：下载小文件复算
        if raw_fetcher is not None and expected_size <= max_download_bytes:
            data = raw_fetcher(path)
            actual = sha256_bytes(data)
            if len(data) != expected_size:
                counts[STATUS_SIZE_MISMATCH] += 1
                results.append({"path": path, "status": STATUS_SIZE_MISMATCH,
                                "expected_bytes": expected_size, "remote_bytes": len(data)})
            elif expected_sha and actual.lower() != expected_sha.lower():
                counts[STATUS_SHA_MISMATCH] += 1
                results.append({"path": path, "status": STATUS_SHA_MISMATCH,
                                "expected_sha256": expected_sha, "remote_sha256": actual})
            else:
                counts[STATUS_MATCH] += 1
                results.append({"path": path, "status": STATUS_MATCH,
                                "bytes": expected_size, "sha256": actual, "via": "download"})
        elif raw_fetcher is not None:
            counts[STATUS_SKIPPED] += 1
            results.append({"path": path, "status": STATUS_SKIPPED,
                            "bytes": expected_size,
                            "reason": f"非 LFS 且大于 {max_download_bytes} bytes，未下载复算"})
        else:
            counts[STATUS_SIZE_ONLY] += 1
            results.append({"path": path, "status": STATUS_SIZE_ONLY,
                            "bytes": expected_size, "reason": "tree 无 sha 且未提供下载器"})
    extras = [entry["path"] for entry in tree_entries
              if entry.get("type", "file") == "file"
              and isinstance(entry.get("path"), str) and entry["path"] not in expected_paths]
    counts[STATUS_EXTRA] = len(extras)
    return results, counts


def summarize(counts: Dict[str, int]) -> Dict[str, Any]:
    hard_failures = (counts.get(STATUS_SHA_MISMATCH, 0) + counts.get(STATUS_SIZE_MISMATCH, 0)
                     + counts.get(STATUS_MISSING, 0))
    unverified = counts.get(STATUS_SKIPPED, 0) + counts.get(STATUS_SIZE_ONLY, 0)
    status = "pass" if hard_failures == 0 else "fail"
    return {"status": status, "hard_failures": hard_failures, "unverified": unverified,
            "counts": counts}


def load_token(path: Path, repo_root: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise ValueError(f"token 文件不得位于仓库内: {resolved}")
    token = resolved.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"token 文件为空: {resolved}")
    return token


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run(args: argparse.Namespace) -> int:
    manifest_files = load_manifest(Path(args.manifest))
    token = None
    if args.token_file:
        token = load_token(Path(args.token_file), repo_root())
    elif args.token_env:
        import os
        token = os.environ.get(args.token_env) or None
        if not token:
            raise RemoteVerifyError(f"环境变量 {args.token_env} 为空")
    elif args.token_cache:
        try:
            from huggingface_hub import get_token  # 可选依赖，仅 --token-cache 时导入
        except ImportError as error:
            raise RemoteVerifyError(
                "--token-cache 需要 huggingface_hub；可用 uv run --with huggingface_hub python ..."
            ) from error
        token = get_token()
        if not token:
            raise RemoteVerifyError("HF 缓存中没有 token；先运行 hf auth login 或改用 --token-file")
    tree = fetch_tree(args.repo_id, args.revision, token)
    raw_fetcher = None
    if not args.skip_raw:
        def raw_fetcher(path: str) -> bytes:  # type: ignore[misc]
            return fetch_raw(args.repo_id, args.revision, path, token)
    results, counts = compare(manifest_files, tree, raw_fetcher=raw_fetcher,
                              max_download_bytes=args.max_download_bytes)
    summary = summarize(counts)
    report = {"repo_id": args.repo_id, "revision": args.revision,
              "manifest": args.manifest, "files": results, **summary}
    print(json.dumps(report, ensure_ascii=False) if args.json else
          "repo {repo_id}@{revision}: {status} | {counts}".format(**report))
    return 0 if summary["status"] == "pass" else 2


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="上传后校验 HF 仓库与本地 MANIFEST 是否一致")
    parser.add_argument("--repo-id", required=True, help="例如 <org>/pol-decision-general-v5")
    parser.add_argument("--manifest", required=True, help="本地 MANIFEST.json 或 HF-MANIFEST.json")
    parser.add_argument("--revision", default="main", help="分支/commit（建议上传后固定到 commit sha）")
    parser.add_argument("--token-file", help="HF token 文件（必须在仓库外）")
    parser.add_argument("--token-env", default=None,
                        help="从该环境变量读取 token（默认不读取，匿名请求公开仓库）")
    parser.add_argument("--token-cache", action="store_true",
                        help="从本机 HF 缓存读取 token（需 huggingface_hub；可用 uv run --with huggingface_hub）")
    parser.add_argument("--skip-raw", action="store_true",
                        help="只读 tree 清单，不下载小文件复算 sha256")
    parser.add_argument("--max-download-bytes", type=int, default=MAX_DOWNLOAD_BYTES,
                        help="非 LFS 文件复算 sha256 的最大下载字节数（默认 10 MiB）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except (RemoteVerifyError, ValueError, OSError) as error:
        print(f"verify_hf_remote failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
