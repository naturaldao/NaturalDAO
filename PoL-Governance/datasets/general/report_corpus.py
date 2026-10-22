"""主语料 items.final.jsonl 的只读构成报告（写 data/items.final.report.json）。

用法::

    uv run --no-project --offline python datasets/general/report_corpus.py \
        --input datasets/general/data/items.final.jsonl \
        --out datasets/general/data/items.final.report.json \
        --gz D:/pol2-raw/general-private/data/items.final.jsonl.gz \
        --ledger D:/pol2-raw/general-private/data/items.final.merge.json

为什么要这个脚本（历史）：v3 的 items.final.report.json 由 merge.py 在「英中合并」时顺手写出。
v4 语料改由 data/splits/build_corpus.py 合并（base v3 + 能力增量），**不再经过 merge.py**，
于是那份 report 停留在 23,855 条、成了事实错误。本脚本只做一件事：从**当前**语料现算构成与指纹，
可随时重跑；不读、不写任何条目内容，也不碰划分。

口径：
- 全部计数从 --input 现算，不引用任何二手统计；
- --gz / --ledger 只用于登记仓外产物的字节数、sha256 与合并台账的 base/adds（都可省略）；
- 输出确定性：sort_keys=True + indent=2，同一输入重跑逐字节一致。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

SCHEMA = "pol-corpus-report/0.2"


class ReportError(Exception):
    """输入不可用。"""


def iter_rows(path: Path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile(rows):
    """一组条目的聚合构成（只存计数，不存样本）。"""
    domains, langs, kinds = Counter(), Counter(), Counter()
    ids = set()
    targets = with_targets = 0
    for item in rows:
        ids.add(str(item["id"]))
        domains[str(item.get("domain"))] += 1
        langs[str(item.get("lang"))] += 1
        item_kinds = {str(q.get("kind")) for q in item.get("questions") or []
                      if isinstance(q, dict) and q.get("kind")}
        for kind in sorted(item_kinds):
            kinds[kind] += 1
        item_targets = item.get("targets") or {}
        count = sum(1 for q in item.get("questions") or []
                    if item_targets.get(q.get("key")) is not None)
        targets += count
        with_targets += 1 if count else 0
    items = len(rows)
    return {
        "items": items,
        "unique_ids": len(ids),
        "targets": targets,
        "with_targets": with_targets,
        "target_rate": round(with_targets / items, 6) if items else 0.0,
        "domains": dict(domains.most_common()),
        "langs": dict(langs.most_common()),
        "kinds_by_item": dict(kinds.most_common()),
    }


def build(input_path: Path, gz_path=None, ledger_path=None) -> dict:
    """从语料现算报告。"""
    if not input_path.is_file():
        raise ReportError(f"输入不存在：{input_path}")
    rows = list(iter_rows(input_path))
    if not rows:
        raise ReportError(f"输入为空：{input_path}")
    by_lang = Counter(str(item.get("lang")) for item in rows)
    by_source = Counter(str(((item.get("source") or {}).get("dataset"))
                            or ((item.get("source") or {}).get("slug"))) for item in rows)
    result = {
        "schema": SCHEMA,
        "generated_from": input_path.as_posix(),
        "files": {"plain": {"path": input_path.as_posix(),
                            "bytes": input_path.stat().st_size,
                            "sha256": sha256_file(input_path)}},
        "final": profile(rows),
        "zh_share": round(by_lang.get("zh", 0) / len(rows), 4),
        "by_source": dict(by_source.most_common()),
        "note": "只含聚合计数与指纹，不含任何条目 id 或正文。",
        "recompute": ("uv run --no-project --offline python datasets/general/report_corpus.py "
                      "--input " + input_path.as_posix() +
                      " --out datasets/general/data/items.final.report.json"),
    }
    # en / zh 子档（与 v3 merge.py 的 en/zh/final 三档保持可比）
    for lang in ("en", "zh"):
        result[lang] = profile([item for item in rows if str(item.get("lang")) == lang])
    result["target_zh"] = result["zh"]["targets"]
    if gz_path is not None:
        gz_path = Path(gz_path)
        if gz_path.is_file():
            result["private_gz"] = {"bytes": gz_path.stat().st_size,
                                    "sha256": sha256_file(gz_path),
                                    "note": "仓外私有副本（不进版本控制），此处只登记指纹。"}
    if ledger_path is not None:
        ledger_path = Path(ledger_path)
        if ledger_path.is_file():
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            result["merge"] = {
                "schema": ledger.get("schema"),
                "total_items": ledger.get("total_items"),
                "base": ledger.get("base"),
                "adds": ledger.get("adds"),
                "outputs": ledger.get("outputs"),
                "note": "来自 build_corpus.py 的合并台账（只含计数与哈希，不含 id/正文）。",
            }
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path,
                        default=Path("datasets/general/data/items.final.jsonl"),
                        help="语料 JSONL(.gz)，只读")
    parser.add_argument("--out", type=Path,
                        default=Path("datasets/general/data/items.final.report.json"),
                        help="报告输出路径")
    parser.add_argument("--gz", type=Path, default=None, help="仓外 gzip 副本（只登记指纹）")
    parser.add_argument("--ledger", type=Path, default=None, help="build_corpus.py 的合并台账")
    args = parser.parse_args(argv)
    try:
        result = build(args.input, args.gz, args.ledger)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")
    except (ReportError, OSError, json.JSONDecodeError) as error:
        print(f"报告失败：{error}")
        return 1
    print(f"# 已写 {args.out}：{result['final']['items']:,} 条 / {result['final']['targets']:,} target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
