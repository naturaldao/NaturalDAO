#!/usr/bin/env python3
r"""从 HuggingFace datasets-server 抓取 decision-base 原始行（仅标准库）。

配套契约：datasets/general/README.md；来源清单：datasets/general/sources.json。
原始数据写到仓库外的 D:\pol2-raw\<slug>\，仓库里只提交构建产物。

为什么不直接相信 revision 参数
--------------------------------
实测（2026-09-30）datasets-server 的 revision 参数**不被遵守**：伪造 sha、别的数据集的
sha、不传 revision，/rows 返回完全相同的首行。因此本模块：

1. 抓取前用 https://huggingface.co/api/datasets/<id> 解析出**当前** commit sha，
   与 sources.json 固定的 revision 逐字节比对，不一致就停下来（数据集漂移必须人工确认）；
2. manifest 里记录 revision 与 revision_enforced=false，不谎称数据被按 sha 钉住；
3. 抓取**结束后**再解析一次 sha，写入 revision_stable；两次不一致则该来源标记为不可信并报错。

要真正逐字节可复现，需按 https://huggingface.co/datasets/<id>/resolve/<sha>/<path> 取文件，
那是另一条链路（离线环境读不了 parquet），不在本模块范围。

用法
----
    uv run --no-project --offline python datasets/general/fetch.py --list
    uv run --no-project --offline python datasets/general/fetch.py --source jev-distill-v3 --limit 200
    uv run --no-project --offline python datasets/general/fetch.py --all --resume
    uv run --no-project --offline python datasets/general/fetch.py --source open-jev --dry-run

测试全离线：python -m unittest discover -s datasets/general -p "test_*.py"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HF_API = "https://huggingface.co/api/datasets"
DS_SERVER = "https://datasets-server.huggingface.co"
DEFAULT_SOURCES = Path(__file__).resolve().parent / "sources.json"
DEFAULT_RAW_ROOT = Path(r"D:\pol2-raw")
PAGE_SIZE = 100                      # datasets-server 的 length 上限
RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504, 522, 524})


class FetchError(RuntimeError):
    """抓取失败：HTTP 错误、数据漂移、manifest 与产物不一致等。"""


class SourceSkipped(RuntimeError):
    """来源被跳过（未固定 revision、缺少许可等），不算抓取失败。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def http_get(url: str, timeout: float = 45.0):
    """默认传输层：返回 (status, body_bytes)。4xx/5xx 不抛异常，交给重试策略判断。"""
    request = urllib.request.Request(url, headers={"User-Agent": "pol-decision-base/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class Client:
    """带指数退避的 JSON 客户端；transport 可注入，便于离线测试。"""

    def __init__(self, transport=http_get, *, retries: int = 6, base_delay: float = 1.5,
                 max_delay: float = 60.0, sleeper=time.sleep, log=print):
        self.transport = transport
        self.retries = retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleeper = sleeper
        self.log = log
        self.requests = 0
        self.retries_used = 0

    def json(self, url: str):
        last = "无响应"
        for attempt in range(self.retries):
            self.requests += 1
            try:
                status, body = self.transport(url)
            except Exception as error:                      # 网络层异常同样退避重试
                last = f"{type(error).__name__}: {error}"
                status, body = None, b""
            if status == 200:
                try:
                    return json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise FetchError(f"{url}: 响应不是合法 JSON（{error}）") from error
            if status is not None and status not in RETRY_STATUS:
                raise FetchError(f"{url}: HTTP {status} {body[:200]!r}")
            last = f"HTTP {status}" if status is not None else last
            if attempt == self.retries - 1:
                break
            self.retries_used += 1
            delay = min(self.max_delay, self.base_delay * (2 ** attempt))
            self.log(f"    [retry {attempt + 1}/{self.retries - 1}] {last}；{delay:.1f}s 后重试")
            self.sleeper(delay)
        raise FetchError(f"{url}: 重试 {self.retries} 次仍失败（{last}）")

    def dataset_metadata(self, dataset: str) -> dict:
        return self.json(f"{HF_API}/{dataset}")

    def endpoint(self, name: str, **params) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        return self.json(f"{DS_SERVER}/{name}?{query}")


# ------------------------------------------------------------------ 抓取计划


def build_plan(strategy: str, total_rows: int, limit: int, *, page_size: int = PAGE_SIZE,
               window_size: int = PAGE_SIZE, n_windows: int = 0, seed: int = 0,
               window_span: int = 0):
    """把抽样策略编译成 [(offset, length), ...]；纯函数，resume 时按同一参数重建。

    - head    ：从 0 开始连续取，便于 --limit 小样本与断点续跑。
    - windows ：在 [0, span) 上均匀开 n_windows 个窗口，跨文件位置取样（不做 uniform 全量，
                也不只读头部）。span 默认是整个分区；对千万行级数据集必须给 window_span：
                实测 offset=3,000,000 的一次 /rows 要 109 秒、offset=6,000,000 直接连接被断，
                深 offset 采样不适合走 datasets-server。
    - stride  ：等距单行取样，代价是每行一个请求，只在小样本核对时用。
    """
    if total_rows <= 0:
        raise FetchError("total_rows 必须为正数，先取 /size 或 /rows 确认行数")
    if limit <= 0:
        raise FetchError("limit 必须为正数")
    plan = []
    if strategy == "head":
        offset = 0
        while offset < min(limit, total_rows):
            length = min(page_size, limit - offset, total_rows - offset)
            plan.append((offset, length))
            offset += length
        return plan
    if strategy == "windows":
        windows = n_windows or max(1, (limit + window_size - 1) // window_size)
        length = max(1, min(window_size, page_size, limit))
        reach = min(total_rows, window_span) if window_span else total_rows
        span = max(1, reach - length)
        starts = sorted({int(round(index * span / max(1, windows - 1))) if windows > 1 else 0
                         for index in range(windows)})
        rng = random.Random(seed)
        starts = sorted({min(span, max(0, start + rng.randint(-length, length))) for start in starts})
        for start in starts:
            if len(plan) * length >= limit:
                break
            plan.append((start, min(length, limit - len(plan) * length)))
        return plan
    if strategy == "stride":
        stride = max(1, total_rows // limit)
        for index in range(limit):
            offset = index * stride
            if offset >= total_rows:
                break
            plan.append((offset, 1))
        return plan
    raise FetchError(f"未知抽样策略 {strategy!r}（可用：head/windows/stride）")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


# ------------------------------------------------------------------ manifest


def read_manifest(raw_dir: Path):
    path = raw_dir / "manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FetchError(f"{path}: manifest 不是合法 JSON（{error}）") from error


def check_resume_state(raw_dir: Path, manifest: dict, plan_meta: dict) -> int:
    """校验已有产物与 manifest 一致，返回可续跑的 cursor；不一致就拒绝续跑。"""
    rows_path = raw_dir / "rows.jsonl"
    if not rows_path.is_file():
        raise FetchError(f"{rows_path} 不存在，无法续跑；去掉 --resume 重新抓取")
    actual_bytes = rows_path.stat().st_size
    actual_sha = sha256_file(rows_path)
    if actual_bytes != manifest.get("bytes") or actual_sha != manifest.get("sha256"):
        raise FetchError(f"{rows_path} 与 manifest 不一致（bytes {actual_bytes} vs "
                         f"{manifest.get('bytes')}，sha256 {actual_sha[:12]} vs "
                         f"{str(manifest.get('sha256'))[:12]}）；删除该目录后重跑")
    for field, value in plan_meta.items():
        if manifest.get(field) != value:
            raise FetchError(f"manifest.{field}={manifest.get(field)!r} 与本次 {value!r} 不一致，"
                             f"数据集或参数已变化；删除 {raw_dir} 后重跑")
    return int(manifest.get("cursor", 0))


# ------------------------------------------------------------------ 抓取


def fetch_source(client: Client, source: dict, raw_root: Path, *, limit=None, resume=False,
                 page_size: int = PAGE_SIZE, log=print) -> dict:
    """抓取单个来源，返回 manifest。产物：rows.jsonl / first-rows.json / manifest.json。"""
    slug = source["slug"]
    dataset = source["dataset"]
    config = source["config"]
    split = source["split"]
    revision = str(source.get("revision") or "")
    raw_dir = raw_root / slug

    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise SourceSkipped(f"{slug}: revision 不是 40 位 commit sha（{revision!r}），按规则跳过")
    if not source.get("license"):
        raise SourceSkipped(f"{slug}: 缺 license 字段，按规则跳过")

    log(f"[{slug}] {dataset} {config}/{split} revision={revision[:12]}")
    requests_before = client.requests
    retries_before = client.retries_used

    metadata = client.dataset_metadata(dataset)
    live_sha = metadata.get("sha")
    if live_sha != revision:
        raise FetchError(f"{slug}: HF 上的 sha={live_sha} 与 sources.json 固定的 {revision} 不一致。"
                         f"数据集已移动，需人工确认后更新 sources.json 再抓。")
    live_license = (metadata.get("cardData") or {}).get("license")

    splits = client.endpoint("splits", dataset=dataset)
    available = {(row["config"], row["split"]) for row in splits.get("splits", [])}
    if (config, split) not in available:
        raise SourceSkipped(f"{slug}: datasets-server 没有 {config}/{split}（可用："
                            f"{sorted(available)[:6]}）")

    first_rows = client.endpoint("first-rows", dataset=dataset, config=config, split=split)
    feature_names = [feature["name"] for feature in first_rows.get("features", [])]

    probe = client.endpoint("rows", dataset=dataset, config=config, split=split, offset=0, length=1)
    total_rows = int(probe.get("num_rows_total") or 0)
    if total_rows <= 0:
        raise FetchError(f"{slug}: num_rows_total={total_rows}，无法规划抓取")

    requested = int(limit if limit is not None else source.get("row_limit") or total_rows)
    sampling = source.get("sampling") or {}
    plan = build_plan(str(sampling.get("strategy", "head")), total_rows, requested,
                      page_size=page_size,
                      window_size=int(sampling.get("window_size", page_size)),
                      n_windows=int(sampling.get("n_windows", 0)),
                      seed=int(sampling.get("seed", 0)),
                      window_span=int(sampling.get("window_span", 0)))
    plan_meta = {"strategy": sampling.get("strategy", "head"), "requested_rows": requested,
                 "num_rows_total": total_rows, "page_size": page_size,
                 "window_span": int(sampling.get("window_span", 0))}
    log(f"[{slug}] 行数 {total_rows}，计划 {len(plan)} 次请求，目标 {requested} 行，"
        f"策略 {plan_meta['strategy']}")

    raw_dir.mkdir(parents=True, exist_ok=True)
    rows_path = raw_dir / "rows.jsonl"
    manifest_path = raw_dir / "manifest.json"
    cursor = 0
    previous = read_manifest(raw_dir)
    if previous is not None:
        if previous.get("complete"):
            log(f"[{slug}] 已完成（{previous.get('rows')} 行），跳过；需要重抓请先删除 {raw_dir}")
            return previous
        if not resume:
            raise FetchError(f"[{slug}] 存在未完成的抓取（{previous.get('cursor')}/"
                             f"{previous.get('plan_length')} 批）；加 --resume 续跑，"
                             f"或删除 {raw_dir} 后重抓")
        if (previous.get("revision"), previous.get("config"), previous.get("split")) != \
                (revision, config, split):
            raise FetchError(f"[{slug}] 已有 manifest 对应另一个 revision/config/split，"
                             f"不能续跑；删除 {raw_dir} 后重跑")
        cursor = check_resume_state(raw_dir, previous, plan_meta)
        log(f"[{slug}] 断点续跑：已完成 {cursor}/{len(plan)} 批，{previous.get('rows')} 行")
        mode = "a"
    elif rows_path.exists():
        raise FetchError(f"[{slug}] {rows_path} 存在但没有 manifest，状态不明；删除该目录后重跑")
    else:
        write_json(raw_dir / "first-rows.json", first_rows)
        mode = "w"

    fetched = int(previous.get("rows", 0)) if previous else 0
    with rows_path.open(mode, encoding="utf-8") as handle:
        for index in range(cursor, len(plan)):
            offset, length = plan[index]
            payload = client.endpoint("rows", dataset=dataset, config=config, split=split,
                                      offset=offset, length=length)
            page = payload.get("rows", [])
            if not page:
                raise FetchError(f"[{slug}] offset={offset} 返回空页，但 num_rows_total={total_rows}")
            for record in page:
                handle.write(json.dumps({"row_idx": record["row_idx"], "row": record["row"]},
                                        ensure_ascii=False) + "\n")
                fetched += 1
            handle.flush()
            cursor = index + 1
            if cursor % 20 == 0 or cursor == len(plan):
                log(f"[{slug}] {cursor}/{len(plan)} 批，累计 {fetched} 行")
            write_json(manifest_path, {
                "slug": slug, "dataset": dataset, "revision": revision, "config": config,
                "split": split, "license": source.get("license"), "license_live": live_license,
                "converter": source.get("converter"), "domain": source.get("domain"),
                "lang": source.get("lang"), "cursor": cursor, "plan_length": len(plan),
                "rows": fetched, "bytes": rows_path.stat().st_size,
                "sha256": sha256_file(rows_path), "complete": False,
                "features": feature_names, "fetched_at": utc_now(),
                **plan_meta,          # 断点续跑要靠这些字段校验计划是否仍然一致
            })

    final_sha = client.dataset_metadata(dataset).get("sha")
    manifest = {
        "slug": slug,
        "dataset": dataset,
        "revision": revision,
        "revision_enforced": False,
        "revision_stable": final_sha == revision,
        "revision_note": "datasets-server 不遵守 revision 参数；本 revision 是抓取前后由 HF API "
                         "解析并核对一致的 sha",
        "revision_live_after": final_sha,
        "config": config,
        "split": split,
        "license": source.get("license"),
        "license_live": live_license,
        "converter": source.get("converter"),
        "domain": source.get("domain"),
        "lang": source.get("lang"),
        "sampling": sampling,
        **plan_meta,
        "rows": fetched,
        "bytes": rows_path.stat().st_size,
        "sha256": sha256_file(rows_path),
        "num_rows_total": total_rows,
        "features": feature_names,
        "cursor": cursor,
        "plan_length": len(plan),
        "complete": True,
        "requests": client.requests - requests_before,
        "retries": client.retries_used - retries_before,
        "fetched_at": utc_now(),
        "source_url": f"https://huggingface.co/datasets/{dataset}",
    }
    write_json(manifest_path, manifest)
    if not manifest["revision_stable"]:
        raise FetchError(f"[{slug}] 抓取期间 HF sha 从 {revision} 变为 {final_sha}，"
                         f"产物不可信；已写 manifest 供排查，请删除 {raw_dir} 后重抓")
    log(f"[{slug}] 完成：{fetched} 行 / {manifest['bytes']} 字节 / sha256={manifest['sha256'][:12]}… / "
        f"请求 {manifest['requests']} 次（重试 {manifest['retries']}）")
    return manifest


# ------------------------------------------------------------------ CLI


def load_sources(path: Path) -> dict:
    if not path.is_file():
        raise FetchError(f"来源清单不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FetchError(f"{path}: 不是合法 JSON（{error}）") from error
    if not isinstance(payload.get("sources"), list) or not payload["sources"]:
        raise FetchError(f"{path}: 缺 sources 数组")
    seen = set()
    for source in payload["sources"]:
        for field in ("slug", "dataset", "config", "split", "license", "converter"):
            if not source.get(field):
                raise FetchError(f"{path}: 来源 {source.get('slug') or source} 缺字段 {field}")
        if source["slug"] in seen:
            raise FetchError(f"{path}: slug 重复 {source['slug']}")
        seen.add(source["slug"])
    return payload


def select_sources(payload: dict, names) -> list:
    if not names:
        return list(payload["sources"])
    index = {source["slug"]: source for source in payload["sources"]}
    missing = [name for name in names if name not in index]
    if missing:
        raise FetchError(f"未知来源 {missing}；可用：{sorted(index)}")
    return [index[name] for name in names]


def plan_for_source(client: Client, source: dict, limit, page_size: int):
    metadata = client.dataset_metadata(source["dataset"])
    if metadata.get("sha") != source.get("revision"):
        raise FetchError(f"{source['slug']}: revision 漂移（HF={metadata.get('sha')}，"
                         f"sources.json={source.get('revision')}）")
    probe = client.endpoint("rows", dataset=source["dataset"], config=source["config"],
                            split=source["split"], offset=0, length=1)
    total = int(probe.get("num_rows_total") or 0)
    target = int(limit if limit is not None else source.get("row_limit") or total)
    sampling = source.get("sampling") or {}
    plan = build_plan(str(sampling.get("strategy", "head")), total, target, page_size=page_size,
                      window_size=int(sampling.get("window_size", page_size)),
                      n_windows=int(sampling.get("n_windows", 0)),
                      seed=int(sampling.get("seed", 0)),
                      window_span=int(sampling.get("window_span", 0)))
    return total, plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="抓取 decision-base 原始行（datasets-server 分页）")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="来源清单 JSON")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT, help="原始数据落盘根目录")
    parser.add_argument("--source", action="append", default=[], help="只抓指定 slug（可重复）")
    parser.add_argument("--all", action="store_true", help="抓 sources.json 里的全部来源")
    parser.add_argument("--limit", type=int, default=None, help="覆盖每源行数上限（小样本打通用）")
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE, help="每页行数，上限 100")
    parser.add_argument("--resume", action="store_true", help="从 manifest 断点续跑")
    parser.add_argument("--dry-run", action="store_true", help="只打印抓取计划，不落数据")
    parser.add_argument("--list", action="store_true", help="列出 sources.json 里的来源")
    parser.add_argument("--retries", type=int, default=6, help="单请求最大尝试次数")
    args = parser.parse_args(argv)

    if args.page_size > PAGE_SIZE:
        parser.error(f"--page-size 上限 {PAGE_SIZE}（datasets-server 硬限制）")

    try:
        payload = load_sources(args.sources)
    except FetchError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    if args.list:
        for source in payload["sources"]:
            print(f"{source['slug']:<28} {source['dataset']:<45} "
                  f"{source['config']}/{source['split']:<8} {source['license']:<14} "
                  f"limit={source.get('row_limit')} domain={source['domain']}")
        print(f"共 {len(payload['sources'])} 个来源；排除项 {len(payload.get('excluded', []))} 个")
        return 0

    if not args.all and not args.source:
        parser.error("请指定 --source <slug>（可重复）或 --all；--list 可查看全部来源")

    try:
        chosen = select_sources(payload, args.source or None)
    except FetchError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    client = Client(retries=args.retries)
    skipped, failed, done = [], [], []
    for source in chosen:
        if args.dry_run:
            try:
                total, plan = plan_for_source(client, source, args.limit, args.page_size)
                print(f"{source['slug']}: total={total} 计划{len(plan)}批 "
                      f"目标{sum(n for _, n in plan)}行")
            except (FetchError, SourceSkipped) as error:
                print(f"{source['slug']}: 计划失败 {error}", file=sys.stderr)
                failed.append(source["slug"])
            continue
        try:
            done.append(fetch_source(client, source, args.raw_root, limit=args.limit,
                                     resume=args.resume, page_size=args.page_size))
        except SourceSkipped as error:
            print(f"跳过：{error}", file=sys.stderr)
            skipped.append({"slug": source["slug"], "reason": str(error)})
        except FetchError as error:
            print(f"失败：{error}", file=sys.stderr)
            failed.append(source["slug"])

    if args.dry_run:
        return 1 if failed else 0

    report = {
        "raw_root": str(args.raw_root),
        "fetched_at": utc_now(),
        "ok": [{"slug": manifest["slug"], "rows": manifest["rows"], "bytes": manifest["bytes"],
                "sha256": manifest["sha256"]} for manifest in done],
        "skipped": skipped,
        "failed": failed,
    }
    try:
        write_json(args.raw_root / "fetch-report.json", report)
    except OSError as error:
        print(f"警告：无法写 {args.raw_root / 'fetch-report.json'}（{error}）", file=sys.stderr)
    print(json.dumps({"ok": len(done), "skipped": len(skipped), "failed": len(failed),
                      "rows": sum(manifest["rows"] for manifest in done)}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
