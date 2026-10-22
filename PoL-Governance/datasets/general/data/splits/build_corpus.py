"""把增量语料并入主语料 items.final，产出可复现的合并语料与合并台账（task-8 用）。

用法::

    uv run --no-project --offline python datasets/general/data/splits/build_corpus.py \
        --base datasets/general/data/items.final.jsonl \
        --add D:/pol2-raw/capability-final/items.capability.jsonl \
        --out datasets/general/data/items.final.jsonl \
        --gz-out D:/pol2-raw/general-private/data/items.final.jsonl.gz \
        --ledger D:/pol2-raw/general-private/data/items.final.merge.json \
        --expect-total 74912

三条规则（违反直接报错，绝不静默放过）：

1. **基座条目原样保留**：基座的每一行按**原始字节**写回（只解一次 JSON 做校验，不重新序列化），
   因此既有条目的 id、字段顺序、转义形式都不变。新条目用本仓库统一的序列化口径
   （ensure_ascii=False + U+2028/U+2029/U+0085 转义），与 split.py 的产物口径一致。
2. **id 全局唯一**：基座内部、增量内部、跨集合都不许重复；新增条目的 **id 前缀**（按 "-" 前两段，
   如 db-bigbench-）不得与基座或其它增量的前缀重叠——撞前缀说明两批数据可能互相覆盖，直接拒绝。
3. **确定性**：输出顺序 = 基座原序 + 各增量原序；gzip 用 mtime=0；台账只含计数与哈希，不含样本内容；
   同一输入重跑逐字节一致。写入走"临时文件 + os.replace"（并发读者不会读到半截文件）。

台账是**聚合统计**：条数、语言/来源/域/原语/origin 构成、输入输出 sha256、id 前缀表。
它不记录任何条目 id 或正文。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import split as sp  # noqa: E402  （同目录：复用它的 JSONL 读取/序列化/原子写口径）

MERGE_SCHEMA = "pol-corpus-merge/0.1"
#: id 形状是 db-<slug>-<8hex>（slug 自带连字符，如 cosmos-qa / jev-decisions-general-50k），
#: 所以前缀必须按**贪婪匹配 + 锚定末尾 8 位 hex**取，不能按 split("-") 前几段切。
_ID_PREFIX = re.compile(r"^db-(.+)-[0-9a-f]{8}$")
REQUIRED_FIELDS = ("id", "domain", "lang", "questions")


class MergeError(Exception):
    """输入或配置不可用。"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def id_prefix(item_id: str) -> str:
    """id 前缀：db-bigbench-ece1cb33 -> db-bigbench-；db-cosmos-qa-<8hex> -> db-cosmos-qa-。

    slug 里可能带连字符，所以按"末尾 8 位 hex"锚定取 slug，而不是按 "-" 切前两段。
    """
    matched = _ID_PREFIX.match(item_id)
    return f"db-{matched.group(1)}-" if matched else (item_id.split("-")[0] + "-")


def validate_item(row: dict, *, origin: str, lineno: int) -> str:
    """校验一条记录并返回 id。"""
    if not isinstance(row, dict):
        raise MergeError(f"{origin}:{lineno} 不是 JSON 对象")
    for field in REQUIRED_FIELDS:
        if not row.get(field):
            raise MergeError(f"{origin}:{lineno} 缺必填字段 {field}")
    return str(row["id"])


def read_jsonl(path: Path):
    """逐行读（支持 .gz）；产出 (行号, 原始行文本, 解析结果)。"""
    source = Path(path)
    if not source.is_file():
        raise MergeError(f"输入不存在：{source}")
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MergeError(f"{source}:{lineno} JSON 解析失败: {exc}") from exc
            yield lineno, line.rstrip("\n"), row


def write_gz_atomic(path: Path, data: bytes) -> None:
    """mtime=0 写 gzip：同一内容两次压缩逐字节一致；同样原子替换。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            handle.write(data)
    sp.replace_with_retry(temporary, path)


def _composition_add(composition: dict, item: dict) -> None:
    """增量更新聚合构成（不保存条目本身，避免 7.5 万条 dict 常驻内存）。"""
    composition["by_lang"][str(item.get("lang"))] += 1
    composition["by_source"][sp.item_source(item)] += 1
    composition["by_domain"][str(item.get("domain"))] += 1
    composition["by_origin"][sp.origin_of(item)] += 1
    for kind in sorted({str(q.get("kind")) for q in item.get("questions") or []
                        if isinstance(q, dict) and q.get("kind")}):
        composition["by_kind"][kind] += 1


def merge(base_path: Path, add_paths, out_path: Path, *, gz_out=None, ledger_path=None,
          expect_total: int | None = None) -> dict:
    """流式合并：边校验边写临时文件，最后原子替换；内存里只留 id 集合与计数器。"""
    out_path = Path(out_path)
    seen: dict = {}
    prefixes: dict = {}
    composition = {"by_lang": Counter(), "by_source": Counter(), "by_domain": Counter(),
                   "by_kind": Counter(), "by_origin": Counter()}
    temporary = out_path.with_name(out_path.name + ".tmp")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0

    def emit(sink, line_text: str, row: dict) -> None:
        nonlocal written
        payload = line_text + "\n"
        sink.write(payload)
        digest.update(payload.encode("utf-8"))
        written += 1
        _composition_add(composition, row)

    with open(temporary, "w", encoding="utf-8", newline="\n") as sink:
        # 基座：原样保留原始行字节（只解一次做校验，不重新序列化）
        base_items = 0
        for lineno, raw, row in read_jsonl(base_path):
            item_id = validate_item(row, origin=str(base_path), lineno=lineno)
            if item_id in seen:
                raise MergeError(f"基座 id 重复：{item_id}")
            prefix = id_prefix(item_id)
            if prefixes.get(prefix) not in (None, "base"):
                raise MergeError(f"基座 id 前缀 {prefix!r} 与增量冲突")
            prefixes[prefix] = "base"
            seen[item_id] = "base"
            emit(sink, raw, row)
            base_items += 1
        add_entries = []
        for add_path in add_paths:
            add_path = Path(add_path)
            local_prefixes: Counter = Counter()
            local_count = 0
            for lineno, _raw, row in read_jsonl(add_path):
                item_id = validate_item(row, origin=str(add_path), lineno=lineno)
                if item_id in seen:
                    raise MergeError(f"{add_path}:{lineno} id 与已有条目重复：{item_id}")
                prefix = id_prefix(item_id)
                if prefix in prefixes and prefixes[prefix] != add_path.as_posix():
                    raise MergeError(
                        f"{add_path}:{lineno} id 前缀 {prefix!r} 与已有条目撞前缀"
                        f"（可能是两批数据互相覆盖）：{item_id}")
                seen[item_id] = "add"
                local_prefixes[prefix] += 1
                local_count += 1
                emit(sink, sp._json_line(row), row)
            for prefix in local_prefixes:
                prefixes[prefix] = add_path.as_posix()
            add_entries.append({"path": add_path.as_posix(), "items": local_count,
                                "sha256": sha256_file(add_path),
                                "id_prefixes": dict(sorted(local_prefixes.items()))})
    total = base_items + sum(entry["items"] for entry in add_entries)
    try:
        if not add_entries or all(entry["items"] == 0 for entry in add_entries):
            raise MergeError("没有可合并的增量条目")
        if total != written:
            raise MergeError(f"内部计数不一致：统计 {total} != 写出 {written}")
        if expect_total is not None and total != expect_total:
            raise MergeError(f"合并后总数 {total} != 期望 {expect_total}")
    except MergeError:
        temporary.unlink(missing_ok=True)
        raise
    sp.replace_with_retry(temporary, out_path)
    outputs = [{"path": out_path.as_posix(), "items": total,
                "bytes": out_path.stat().st_size, "sha256": digest.hexdigest()}]
    if gz_out is not None:
        write_gz_atomic(Path(gz_out), out_path.read_bytes())
        outputs.append({"path": Path(gz_out).as_posix(), "items": total,
                        "bytes": Path(gz_out).stat().st_size,
                        "sha256": sha256_file(Path(gz_out))})
    ledger = {
        "schema": MERGE_SCHEMA,
        "base": {"path": Path(base_path).as_posix(), "items": base_items,
                 "sha256": sha256_file(base_path)},
        "adds": add_entries,
        "total_items": total,
        "id_prefixes": dict(sorted(prefixes.items())),
        "composition": {key: dict(value.most_common()) for key, value in composition.items()},
        "outputs": outputs,
        "rules": ["基座条目按原始字节保留（不重新序列化）",
                  "id 全局唯一；增量 id 前缀不得与基座/其它增量重叠",
                  "输出顺序 = 基座原序 + 各增量原序；gzip mtime=0；台账只含聚合统计"],
        "note": "合并台账：只含计数与哈希，不含任何条目 id 或正文。",
    }
    if ledger_path is not None:
        sp.atomic_write_text(Path(ledger_path),
                             json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return ledger


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="把增量语料并入主语料（可复现合并）")
    parser.add_argument("--base", type=Path, default=Path("datasets/general/data/items.final.jsonl"),
                        help="基座语料（原样保留其条目字节）")
    parser.add_argument("--add", action="append", required=True, metavar="PATH",
                        help="增量语料（可重复；id 前缀必须与基座不重叠）")
    parser.add_argument("--out", type=Path, required=True, help="合并后 JSONL 输出路径")
    parser.add_argument("--gz-out", type=Path, default=None, help="合并后 gzip 输出路径（可选）")
    parser.add_argument("--ledger", type=Path, default=None, help="合并台账 JSON 输出路径（可选）")
    parser.add_argument("--expect-total", type=int, default=None,
                        help="断言合并后总数（防止静默少读）")
    args = parser.parse_args(argv)
    try:
        ledger = merge(args.base, args.add, args.out, gz_out=args.gz_out,
                       ledger_path=args.ledger, expect_total=args.expect_total)
    except MergeError as exc:
        print(f"合并失败：{exc}", file=sys.stderr)
        return 2
    comp = ledger["composition"]
    print(f"合并完成：{ledger['base']['items']:,}（基座）+ "
          + " + ".join(f"{entry['items']:,}" for entry in ledger["adds"])
          + f" = {ledger['total_items']:,} 条")
    print(f"  lang：{comp['by_lang']}")
    print(f"  source：{comp['by_source']}")
    print(f"  domain：{comp['by_domain']}")
    print(f"  origin：{comp['by_origin']}")
    for entry in ledger["outputs"]:
        print(f"  写出 {entry['path']}：{entry['items']:,} 条 / {entry['bytes']:,} B / "
              f"sha256 {entry['sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
