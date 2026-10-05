"""最终语料切分：按请求分组、按 domain x lang 分层、6:2:1:1、内部 benchmark（task-20）。

用法::

    uv run --no-project --offline python datasets/general/data/splits/split.py \
        --out datasets/general/data/splits --report datasets/general/split-report.md --seed 20261005

最终输入只有一份：**datasets/general/data/items.final.jsonl**（db-hf 合并：英文原生四元组 +
已按 33% 目标筛过的中文侧）。默认就取它，不自动叠加 data/zh/（会把中文侧重复计入）。
其它语料只能显式 --input 传入，且只用于 dry-run 验证：items.native.jsonl（英文全量）、
D:/pol2-raw/zh-final/items.zh.jsonl（中文全量）、data/items.jsonl（替数据出题的旧版本，仅回归对照）。

中文侧硬门禁：zh 条目（或来自 data/zh/ 的条目）必须带显式分组 id
（item/source/meta 下的 group_id / request_id / family_id），否则直接拒绝切分并返回 3，
绝不退化成按行切——按行切会静默泄漏，比切不出来更糟。--allow-missing-group-id 可绕过，仅用于探索。

四条最容易做错的地方，本脚本的对策：

1. **按请求分组，绝不按行切分。** 分组键取（按优先级）item.group_id / source.group_id / meta.group_id /
   source.request_id / meta.request_id；此外把**同一个归一化 state** 的条目并进同一组（并查集），
   这样"同一请求的 4 套候选集变体"与"同 state 的翻译/改写"整组进同一分区。都取不到才退回 item id 兜底，
   兜底条数与各组构成写进报告。
2. **分层**：按 (domain, lang) 分层，层内按组用种子洗牌，再按"目标条数 - 已分配条数"最大缺口贪心分配，
   使四区的域分布与语言比例大体一致。
3. **benchmark 不是随机抽样**：先按 10% 比例预留，再对 lang x kind、domain、lang 做保底配额补齐
   （该类不足时取全部），保证覆盖 noul/choice/score、主要 domain 与中英两侧。
4. **隐私**：benchmark 条目只写进 --out 与 benchmark-dataset 目录；split-report.md 与 dataset card
   只有聚合统计，**不含任何样本内容**（test_split.py 有对应断言）。请勿把 benchmark.jsonl(.gz)
   提交到公开仓库——它由用户上传 Hugging Face 并设为 private。

可复现：随机数全部来自 random.Random("seed|阶段|domain|lang")，分区内条目按 id 排序，
gzip 用 mtime=0 写入；同一输入重跑两次逐字节一致（test_split.py 有对应测试）。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

SPLITS = ("train", "test", "validation", "benchmark")
GROUPED_SPLITS = ("train", "test", "validation")
DEFAULT_RATIOS = {"train": 0.6, "test": 0.2, "validation": 0.1, "benchmark": 0.1}
DEFAULT_SEED = 20261005
DEFAULT_OUT = Path("datasets/general/data/splits")
DEFAULT_REPORT = Path("datasets/general/split-report.md")
#: 最终语料是 db-hf 合并后的单一文件（英文原生四元组 + 已按 33% 目标筛过的中文侧）。
#: 不自动叠加 datasets/general/data/zh/（会把中文侧重复计入）；别的语料只能显式 --input 传入，
#: 且只用于 dry-run 验证：items.native.jsonl（英文全量）、D:/pol2-raw/zh-final/items.zh.jsonl（中文全量）、
#: data/items.jsonl（替数据出题的旧版本，仅回归对照）。
DEFAULT_INPUTS = (
    Path("datasets/general/data/items.final.jsonl"),
)
ZH_PATH_MARKER = "data/zh/"
#: 内部 benchmark 的保底配额（每个 lang x kind / 每个 domain / 每个 lang），可用命令行覆盖
DEFAULT_BENCHMARK_MIN_PER_CELL = 100
#: 无盐跑（--public-demo）时折进种子的固定标记：任何人用公开信息跑出来的都是这一套，
#: 因此**永远与交付件不同**（交付件用的是仓外私盐）。
PUBLIC_DEMO_SALT = "public-demo"
#: 环境变量里也可以放盐文件路径（优先级低于 --salt-file）
SALT_ENV = "POL_SPLIT_SALT_FILE"
_WS = re.compile(r"\s+")


class SplitError(Exception):
    """输入或配置不可用。"""


# ---------------------------------------------------------------- 读取

def iter_jsonl(path: Path | str):
    """逐行读 JSONL（支持 .gz）；坏行直接报错。"""
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield lineno, json.loads(line)
            except json.JSONDecodeError as exc:
                raise SplitError(f"{source}:{lineno} JSON 解析失败: {exc}") from exc


def _first_present(mapping: dict, keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_state(text) -> str:
    """state 归一：去首尾空白、压缩内部空白、大小写折叠。用于同 state 分组与泄漏检查。"""
    return _WS.sub(" ", (text or "").strip()).casefold()


def declared_group(item: dict):
    """按优先级取显式分组键；取不到返回 None。"""
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    keys = ("group_id", "request_id", "family_id")
    return (_first_present(item, keys) or _first_present(source, keys)
            or _first_present(meta, keys + ("source_group",)))


def looks_like_items(path: Path) -> bool:
    """判断一个 JSONL 是否像 items 文件（一行内有 id/domain/lang/questions）；只用于自动探测。"""
    try:
        for _lineno, row in iter_jsonl(path):
            return (isinstance(row, dict) and row.get("id") and row.get("domain")
                    and row.get("lang") and row.get("questions"))
    except SplitError:
        return False
    return False


def resolve_inputs(explicit, *, ignored: list | None = None) -> list[Path]:
    """解析输入；显式优先，否则只认最终语料 items.final.jsonl。

    目录输入会逐文件探测是否像条目文件（索引/清单类 JSONL 忽略并记入 ignored）；
    显式文件不做过滤（你指定什么就读什么）。
    """
    files: list[Path] = []
    sink = ignored if ignored is not None else []
    if explicit:
        for raw in explicit:
            path = Path(raw)
            if path.is_dir():
                found = sorted(p for p in path.rglob("*.jsonl"))
                if not found:
                    raise SplitError(f"目录里没有 .jsonl: {path}")
                for candidate in found:
                    if looks_like_items(candidate):
                        files.append(candidate)
                    else:
                        sink.append(candidate.as_posix())
            elif path.is_file():
                files.append(path)
            else:
                raise SplitError(f"输入不存在: {path}")
    else:
        for candidate in DEFAULT_INPUTS:
            if candidate.is_file():
                files.append(candidate)
                break
    unique: list[Path] = []
    seen: set[str] = set()
    for path in files:
        if "data/splits" in path.as_posix():
            continue  # 不把自己的产物当输入
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    if not unique:
        raise SplitError("没有找到输入：最终语料 " + DEFAULT_INPUTS[0].as_posix()
                         + " 还没生成（等 task-19 的合并产物）；dry-run 可用 --input 显式指定别的语料")
    return unique


def group_id_gaps(records, *, required_langs=("zh",), zh_path_marker: str = ZH_PATH_MARKER) -> dict:
    """中文侧必须带显式分组 id：返回缺失统计。

    Lead 的硬要求：中文侧变体共享同一个显式 group_id；没有就停下来报告，绝不退化成按行切
    （按行切会静默泄漏，比切不出来更糟）。英文侧不要求（open-jev 本来就大部分没有显式键）。
    """
    missing: Counter = Counter()
    examples: dict = {}
    for record in records:
        chinese_side = record["lang"] in required_langs or zh_path_marker in record["input"]
        if chinese_side and not record["declared"]:
            key = f"{record['input']} (lang={record['lang']})"
            missing[key] += 1
            examples.setdefault(key, record["id"])
    return {"missing": dict(missing), "total": sum(missing.values()), "examples": examples}


def load_records(paths, *, allow_duplicates: bool = False):
    """读入所有条目；返回 (items, records, stats)。records 与 items 一一对应。"""
    items: list[dict] = []
    records: list[dict] = []
    stats = {"files": [], "raw": 0, "duplicate_ids": 0}
    seen_ids: set[str] = set()
    for path in paths:
        count = 0
        for lineno, item in iter_jsonl(path):
            stats["raw"] += 1
            if not isinstance(item, dict):
                raise SplitError(f"{path}:{lineno} 不是 JSON 对象")
            for field in ("id", "domain", "lang", "questions"):
                if not item.get(field):
                    raise SplitError(f"{path}:{lineno} 缺必填字段 {field}")
            item_id = str(item["id"])
            if item_id in seen_ids:
                stats["duplicate_ids"] += 1
                if not allow_duplicates:
                    raise SplitError(f"{path}:{lineno} id 重复 {item_id}（--allow-duplicates 保留首条）")
                continue
            seen_ids.add(item_id)
            state = item.get("state")
            kinds = tuple(sorted({str(q.get("kind")) for q in item.get("questions") or []
                                  if isinstance(q, dict) and q.get("kind")}))
            records.append({
                "index": len(items),
                "id": item_id,
                "input": path.as_posix(),
                "line": lineno,
                "domain": str(item["domain"]),
                "lang": str(item["lang"]),
                "state_norm": normalize_state(state) if isinstance(state, str) else "",
                "declared": declared_group(item),
                "kinds": kinds,
            })
            items.append(item)
            count += 1
        stats["files"].append({"path": path.as_posix(), "items": count})
    if not items:
        raise SplitError("输入为空")
    return items, records, stats


# ---------------------------------------------------------------- 分组（并查集）

def _state_node(state_norm: str) -> tuple:
    return ("s", hashlib.sha1(state_norm.encode("utf-8")).hexdigest()[:20])


def build_groups(records, *, use_state: bool = True):
    """把条目并成请求组；返回 (每条目的组标签, 统计)。组标签由内容派生，稳定可复现。"""
    parent: dict = {}

    def find(node):
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    nodes: list[tuple] = []
    for record in records:
        node = ("i", record["index"])
        parent.setdefault(node, node)
        nodes.append(node)
        if record["declared"]:
            other = ("g", record["declared"])
            parent.setdefault(other, other)
            nodes.append(other)
            union(node, other)
        if use_state and record["state_norm"]:
            other = _state_node(record["state_norm"])
            parent.setdefault(other, other)
            nodes.append(other)
            union(node, other)

    members: dict = defaultdict(list)
    for node in nodes:
        members[find(node)].append(node)
    label_of_root = {root: "|".join(sorted(f"{kind}:{value}" for kind, value in group))
                     for root, group in members.items()}
    labels = [label_of_root[find(("i", record["index"]))] for record in records]

    by_label: dict = defaultdict(list)
    for record, label in zip(records, labels):
        by_label[label].append(record)
    stats = {
        "groups": len(by_label),
        "items_with_declared_group": sum(1 for r in records if r["declared"]),
        "items_without_declared_group": sum(1 for r in records if not r["declared"]),
        "multi_item_groups": sum(1 for group in by_label.values() if len(group) > 1),
        "largest_group": max((len(group) for group in by_label.values()), default=0),
        "groups_with_multiple_states": sum(
            1 for group in by_label.values() if len({r["state_norm"] for r in group}) > 1),
        "groups_with_multiple_declared_ids": sum(
            1 for group in by_label.values() if len({r["declared"] for r in group if r["declared"]}) > 1),
        "items_without_state": sum(1 for r in records if not r["state_norm"]),
        "state_grouping": use_state,
    }
    return labels, stats


def group_stratum(group_records):
    """组的 (domain, lang)：组内多数，平票按字典序，保证确定性。"""
    counts = Counter((record["domain"], record["lang"]) for record in group_records)
    return max(sorted(counts), key=lambda key: counts[key])


# ---------------------------------------------------------------- 切分

def _targets(items_count: int, ratios: dict, splits) -> dict:
    total_ratio = sum(ratios[s] for s in splits)
    return {s: items_count * ratios[s] / total_ratio for s in splits}


def git_repo_root(start: Path) -> Path | None:
    """返回包含 start 的 git 仓库根；不是仓库或没有 git 时返回 None。"""
    try:
        completed = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    except (OSError, FileNotFoundError):
        return None
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.strip())


def path_inside(root: Path | None, path: Path) -> bool:
    """path 是否位于 root 之内（root 为 None 时恒 False）。"""
    if root is None:
        return False
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def read_salt(salt_file, *, repo_root: Path | None) -> str:
    """读**仓库外**私盐，返回折进种子的 token（sha256 前 16 位）。

    硬要求：盐文件必须在仓库外——盐一旦进仓库，"公开脚本 + 公开种子无法复现 benchmark"就不成立。
    """
    path = Path(salt_file)
    if not path.is_file():
        raise SplitError(f"盐文件不存在：{path}")
    if path_inside(repo_root, path):
        raise SplitError(f"盐文件必须在仓库外（当前在仓库内）：{path}")
    data = path.read_bytes()
    if len(data) < 16:
        raise SplitError(f"盐文件太短（{len(data)} B）：请至少放 16 字节随机内容")
    return hashlib.sha256(data).hexdigest()[:16]


def _shuffled(labels, seed: int, salt, *parts) -> list[str]:
    """确定性洗牌：种子 = 公开 seed + 盐 token（无盐时用固定标记 public-demo）。"""
    ordered = sorted(labels)
    random.Random("|".join([str(seed), salt or PUBLIC_DEMO_SALT, *parts])).shuffle(ordered)
    return ordered


def reserve_benchmark(records_by_group, ratios: dict, seed: int, salt=None, *,
                      benchmark_langs=None,
                      min_per_domain: int, min_per_lang: int, min_per_kind: int):
    """第一阶段：按 10% 预留 benchmark，再按保底配额补齐（lang x kind / domain / lang）。

    benchmark_langs 限定哪些语言可以进 benchmark（其余语言不预留、不设保底，全部分到公开三区）。
    """
    total = sum(len(group) for group in records_by_group.values())
    target = total * ratios["benchmark"]
    allowed = tuple(benchmark_langs) if benchmark_langs else None
    by_stratum: dict = defaultdict(list)
    for label, group in records_by_group.items():
        stratum = group_stratum(group)
        if allowed is not None and stratum[1] not in allowed:
            continue
        by_stratum[stratum].append(label)

    reserved: set = set()
    reserved_total = 0
    budget = target * 1.2  # 允许一个组的粒度误差，但不让"每层至少一组"把 benchmark 撑大
    for stratum in sorted(by_stratum):
        labels = by_stratum[stratum]
        stratum_items = sum(len(records_by_group[label]) for label in labels)
        need = target * (stratum_items / total) if total else 0
        taken = 0
        for label in _shuffled(labels, seed, salt, "bench", *stratum):
            size = len(records_by_group[label])
            if taken >= need:
                break
            if reserved_total >= target and reserved_total + size > budget:
                break
            reserved.add(label)
            taken += size
            reserved_total += size

    def cell_items(predicate) -> int:
        return sum(len(records_by_group[label]) for label in reserved if predicate(label))

    domains = sorted({record["domain"] for group in records_by_group.values() for record in group})
    langs = sorted({record["lang"] for group in records_by_group.values() for record in group
                    if allowed is None or record["lang"] in allowed})
    pairs = sorted({(record["lang"], kind) for group in records_by_group.values()
                    for record in group for kind in record["kinds"]
                    if allowed is None or record["lang"] in allowed})
    definitions = []
    for domain in domains:
        definitions.append((min_per_domain, f"domain={domain}",
                            lambda label, d=domain: any(r["domain"] == d for r in records_by_group[label])))
    for lang in langs:
        definitions.append((min_per_lang, f"lang={lang}",
                            lambda label, l=lang: any(r["lang"] == l for r in records_by_group[label])))
    for lang, kind in pairs:
        definitions.append((min_per_kind, f"lang={lang},kind={kind}",
                            lambda label, l=lang, k=kind: any(
                                r["lang"] == l and k in r["kinds"] for r in records_by_group[label])))

    floors: list[dict] = []
    for required, name, predicate in definitions:
        have = cell_items(predicate)
        if have >= required:
            floors.append({"cell": name, "required": required, "have": have, "capped": False})
            continue
        candidates = [label for label in records_by_group if label not in reserved and predicate(label)]
        available = sum(len(records_by_group[label]) for label in candidates)
        added = 0
        for label in _shuffled(candidates, seed, salt, "floor", name):
            if cell_items(predicate) >= required:
                break
            reserved.add(label)
            added += len(records_by_group[label])
        have = cell_items(predicate)
        floors.append({"cell": name, "required": required, "have": have, "added_items": added,
                       "available_before": available, "capped": have < required})
    return reserved, floors


def assign_grouped(groups_by_stratum, records_by_group, ratios: dict, seed: int, salt=None) -> dict:
    """第二阶段：未预留的组按 6:2:1 分到 train/test/validation（层内最大缺口贪心）。"""
    assignment: dict = {}
    order = list(GROUPED_SPLITS)
    for stratum in sorted(groups_by_stratum):
        labels = groups_by_stratum[stratum]
        stratum_items = sum(len(records_by_group[label]) for label in labels)
        targets = _targets(stratum_items, ratios, GROUPED_SPLITS)
        assigned = {split: 0 for split in GROUPED_SPLITS}
        for label in _shuffled(labels, seed, salt, "split", *stratum):
            best = max(order, key=lambda split: (targets[split] - assigned[split], -order.index(split)))
            assignment[label] = best
            assigned[best] += len(records_by_group[label])
    return assignment


def assign_all(records, *, ratios: dict, seed: int, salt=None, benchmark_langs=None,
               use_state: bool = True,
               min_per_domain: int = DEFAULT_BENCHMARK_MIN_PER_CELL,
               min_per_lang: int = DEFAULT_BENCHMARK_MIN_PER_CELL,
               min_per_kind: int = DEFAULT_BENCHMARK_MIN_PER_CELL):
    """完整切分；返回 (每条目分区, 组标签, 统计, 保底明细)。

    salt 为 None 表示 public-demo（无盐）跑法：结果确定但与带盐交付件不同。
    """
    labels, group_stats = build_groups(records, use_state=use_state)
    grouped: dict = defaultdict(list)
    for record, label in zip(records, labels):
        grouped[label].append(record)
    records_by_group = dict(grouped)

    reserved, floors = reserve_benchmark(records_by_group, ratios, seed, salt,
                                         benchmark_langs=benchmark_langs,
                                         min_per_domain=min_per_domain,
                                         min_per_lang=min_per_lang,
                                         min_per_kind=min_per_kind)
    by_stratum: dict = defaultdict(list)
    for label, group in records_by_group.items():
        if label not in reserved:
            by_stratum[group_stratum(group)].append(label)
    assignment = assign_grouped(by_stratum, records_by_group, ratios, seed, salt)
    for label in reserved:
        assignment[label] = "benchmark"

    split_of_item = [assignment[label] for label in labels]
    stats = {"groups": group_stats, "benchmark_reserved_groups": len(reserved),
             "benchmark_floors": floors,
             "salted": salt is not None,
             "benchmark_langs": sorted(benchmark_langs) if benchmark_langs else None}
    return split_of_item, labels, stats, floors


# ---------------------------------------------------------------- 泄漏检查

def leak_report(records, labels, split_of_item, items=None) -> dict:
    """独立复核：组、归一化 state、id 都不得跨区。"""
    problems: list[str] = []
    splits_of_group: dict = defaultdict(set)
    splits_of_state: dict = defaultdict(set)
    ids: dict = defaultdict(set)
    for record, label, split in zip(records, labels, split_of_item):
        splits_of_group[label].add(split)
        if record["state_norm"]:
            splits_of_state[record["state_norm"]].add(split)
        ids[record["id"]].add(split)
    for label, splits in sorted(splits_of_group.items()):
        if len(splits) > 1:
            problems.append(f"组跨区 {sorted(splits)}：{label[:80]}")
    for state, splits in sorted(splits_of_state.items()):
        if len(splits) > 1:
            problems.append(f"同一 state 跨区 {sorted(splits)}：{state[:80]}")
    for item_id, splits in sorted(ids.items()):
        if len(splits) > 1:
            problems.append(f"id 跨区 {sorted(splits)}：{item_id}")
    unknown = [s for s in split_of_item if s not in SPLITS]
    if unknown:
        problems.append(f"有 {len(unknown)} 条落到了未知分区")
    return {
        "groups_multi_split": sum(1 for splits in splits_of_group.values() if len(splits) > 1),
        "states_multi_split": sum(1 for splits in splits_of_state.values() if len(splits) > 1),
        "ids_multi_split": sum(1 for splits in ids.values() if len(splits) > 1),
        "distinct_groups": len(splits_of_group),
        "distinct_states": len(splits_of_state),
        "problems": problems[:20],
        "problem_count": len(problems),
    }


# ---------------------------------------------------------------- 输出

#: json.dumps(ensure_ascii=False) 不转义这三个字符。它们在 JSON 里合法，但 Python 的 str.splitlines()
#: 会把 U+2028/U+2029 当换行、U+0085 当 NEL，于是"换一种读法"就把一条记录从中间劈开
#: （coverage.py 第一次读 items.jsonl 就是这么炸的）。输出统一写成 \uXXXX 转义：无损、仍是合法 JSON。
_LINE_SEPARATORS = ("\u2028", "\u2029", "\u0085")


def escape_line_separators(text: str) -> str:
    """把裸 U+2028 / U+2029 / U+0085 换成 JSON 转义形式（无损，只是换一种合法编码）。"""
    for char in _LINE_SEPARATORS:
        if char in text:
            text = text.replace(char, "\\u%04x" % ord(char))
    return text


def _json_line(item: dict) -> str:
    return escape_line_separators(json.dumps(item, ensure_ascii=False))


def write_jsonl(path: Path, items) -> str:
    text = "".join(_json_line(item) + "\n" for item in items)
    path.write_text(text, encoding="utf-8", newline="\n")
    return text


def count_bare_line_separators(path: Path) -> int:
    """数产物里裸 U+2028 / U+2029 / U+0085 的字节数（应为 0；测试与报告都用这个口径）。"""
    data = Path(path).read_bytes()
    return sum(data.count(char.encode("utf-8")) for char in _LINE_SEPARATORS)


def write_gz(path: Path, text: str) -> None:
    """mtime=0 写 gzip：同一内容两次压缩逐字节一致。"""
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            handle.write(text.encode("utf-8"))


def write_split_files(out_dir: Path, split_items: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for split in SPLITS:
        items = split_items[split]
        text = write_jsonl(out_dir / f"{split}.jsonl", items)
        write_gz(out_dir / f"{split}.jsonl.gz", text)
        written[split] = {"items": len(items), "jsonl": (out_dir / f"{split}.jsonl").as_posix(),
                          "gz": (out_dir / f"{split}.jsonl.gz").as_posix()}
    return written


def source_summary(items) -> list[dict]:
    """按 (dataset, revision, license) 汇总来源；只用于 manifest 与报告，不含样本内容。"""
    counts: dict = defaultdict(int)
    for item in items:
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        counts[(str(source.get("dataset", "(unknown)")), str(source.get("revision", ""))[:12],
                str(source.get("license", "")))] += 1
    rows = [{"dataset": key[0], "revision": key[1], "license": key[2], "items": count}
            for key, count in counts.items()]
    return sorted(rows, key=lambda row: (-row["items"], row["dataset"]))


def export_benchmark_dataset(directory: Path, items, groups: int, sources, *,
                             seed: int, ratios: dict) -> dict:
    """导出可直接上传 HF（private）的目录：dataset card + 数据 + 来源 manifest。

    只写聚合信息，不写任何样本内容。
    """
    directory.mkdir(parents=True, exist_ok=True)
    text = write_jsonl(directory / "benchmark.jsonl", items)
    write_gz(directory / "benchmark.jsonl.gz", text)
    manifest = {
        "name": "pol-general-general-internal-benchmark",
        "private": True,
        "seed": seed,
        "ratios": ratios,
        "items": len(items),
        "groups": groups,
        "sources": sources,
        "warning": "内部 benchmark：请上传 Hugging Face 并设为 private，不得进入公开仓库或公开日志。",
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    ratio_text = ", ".join(f"{key}={value:g}" for key, value in ratios.items())
    card = f"""---
license: other
pretty_name: PoL 通用决策底座 · 内部 benchmark
private: true
---

# PoL 通用决策底座 · 内部 benchmark（private）

**用途**：内部模型比较与回归；不作为公开测试集，不进入训练或教师造数。
**请勿公开**：本目录由用户上传 Hugging Face 并设为 private；不得进入公开仓库、公开日志或公开报告。

## 规模

- 条目数：{len(items)}
- 请求组数：{groups}
- 随机种子：{seed}（切分比例 {ratio_text}）
- 覆盖：中英两侧；主要覆盖域与 noul / choice / score 三种原语（分布见 manifest.json）

## 字段

每条记录沿用数据集契约 datasets/general/CONTRACT.md 第 2.1 节的 items 形状：
id / domain / lang / state / questions[] / targets / source / meta。
questions[] 是本条目自带的问题（origin=source 时 key 为来源原生名，origin=taxonomy 时取自 taxonomy 键表）。

## 来源与许可

逐来源的 dataset / revision / license / 条数见 manifest.json 的 sources 字段；
每条记录自身的 source.dataset 与 source.revision 是唯一权威。

## 生成

    uv run --no-project --offline python datasets/general/data/splits/split.py --seed {seed}

本卡片与 split-report.md 只包含聚合统计，不含任何 benchmark 样本内容。
"""
    (directory / "README.md").write_text(card, encoding="utf-8", newline="\n")
    return {"directory": directory.as_posix(), "items": len(items),
            "card": "README.md", "manifest": "manifest.json"}


# ---------------------------------------------------------------- 报告

#: 逐字节比对范围：4 个分区 + benchmark-dataset 的确定性产物
PRODUCT_FILES = (
    "train.jsonl", "train.jsonl.gz", "test.jsonl", "test.jsonl.gz",
    "validation.jsonl", "validation.jsonl.gz", "benchmark.jsonl", "benchmark.jsonl.gz",
    "benchmark-dataset/README.md", "benchmark-dataset/benchmark.jsonl",
    "benchmark-dataset/benchmark.jsonl.gz", "benchmark-dataset/manifest.json",
)


def composition_summary(records, items) -> dict:
    """数据成色：每种语言覆盖哪些 kind、各自来源数与最大来源占比（供报告如实写明缺口）。"""
    lang_kinds: dict = defaultdict(set)
    items_by_lang: Counter = Counter()
    for record in records:
        items_by_lang[record["lang"]] += 1
        for kind in record["kinds"]:
            lang_kinds[record["lang"]].add(kind)
    sources_by_lang: dict = defaultdict(Counter)
    for item in items:
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        sources_by_lang[str(item.get("lang"))][str(source.get("dataset", "(unknown)"))] += 1
    kinds = sorted({kind for group in lang_kinds.values() for kind in group})
    total = len(items)
    single_source_langs = []
    for lang, counter in sorted(sources_by_lang.items()):
        if len(counter) == 1:
            name, count = counter.most_common(1)[0]
            single_source_langs.append({"lang": lang, "dataset": name, "items": count,
                                        "share": count / max(total, 1)})
    return {
        "items_by_lang": dict(items_by_lang),
        "single_source_langs": single_source_langs,
        "kinds_by_lang": {lang: sorted(group) for lang, group in sorted(lang_kinds.items())},
        "langs_by_kind": {kind: sorted(lang for lang, group in lang_kinds.items() if kind in group)
                          for kind in kinds},
        "sources_by_lang": {lang: dict(counter.most_common())
                            for lang, counter in sorted(sources_by_lang.items())},
    }


def compare_dirs(left: Path, right: Path, names=PRODUCT_FILES) -> dict:
    """逐字节比对两个目录下的同名产物；返回是否一致、树哈希与逐文件 sha256。"""
    digests: dict = {}
    problems: list = []
    for name in names:
        left_path, right_path = left / name, right / name
        if not left_path.is_file() or not right_path.is_file():
            problems.append(f"{name}: 缺文件")
            continue
        first = hashlib.sha256(left_path.read_bytes()).hexdigest()
        second = hashlib.sha256(right_path.read_bytes()).hexdigest()
        digests[name] = first
        if first != second:
            problems.append(f"{name}: {first[:12]} != {second[:12]}")
    tree = hashlib.sha256("\n".join(f"{name}:{digests[name]}" for name in sorted(digests)).encode("utf-8"))
    return {"files": len(names), "identical": not problems, "problems": problems[:5],
            "tree_sha256": tree.hexdigest(), "digests": digests}


def render_report(*, inputs, items, records, split_of_item, labels, stats, leaks,
                  seed: int, ratios: dict, counts: dict, composition: dict,
                  rerun: dict | None = None) -> str:
    """split-report.md：只有聚合统计，不含任何样本内容。"""
    lines: list[str] = []
    total = len(items)
    group_counts = Counter()
    for split in split_of_item:
        group_counts[split] += 1
    lines.append("# 最终切分报告（6:2:1:1，按请求分组）")
    lines.append("")
    lines.append("本报告只含聚合统计，**不含任何样本内容**；内部 benchmark 的条目只存在于 "
                 "data/splits/benchmark.jsonl(.gz) 与 data/splits/benchmark-dataset/，"
                 "请勿提交到公开仓库，请上传 Hugging Face 并设为 private。")
    lines.append("")
    lines.append(f"- 随机种子：{seed}")
    lines.append("- 切分比例：" + ", ".join(f"{split}={ratios[split]:g}" for split in SPLITS))
    if stats["input"].get("ignored"):
        lines.append("- 自动探测时忽略的非条目 JSONL："
                     + ", ".join(stats["input"]["ignored"]))
    lines.append(f"- 输入文件：{len(inputs)} 个")
    for entry in stats["input"]["files"]:
        lines.append(f"  - {entry['path']}：{entry['items']} 条")
    lines.append(f"- 条目总数：{total}；请求组 {stats['groups']['groups']} 个")
    salt_state = "仓外私盐（盐值不记录、不派生进任何公开产物）" if stats.get("salted") \
        else "无盐 public-demo（**不是交付件**；公开脚本+公开种子跑出的就是这一套）"
    lines.append(f"- 保密：本次运行使用 {salt_state}")
    if stats.get("benchmark_langs"):
        lines.append("- benchmark 语言白名单：" + ", ".join(stats["benchmark_langs"])
                     + "（白名单外的语言只进 train/test/validation）")
    lines.append("")
    lines.append("## 1. 切分算法")
    lines.append("")
    lines.append("1. **分组**（并查集）：显式分组键（item.group_id / source.group_id / meta.group_id / "
                 "source.request_id / meta.request_id）与**归一化 state**（去空白、压缩空白、大小写折叠）"
                 "各自连边；同一分量的所有条目整组进同一分区，绝不按行切。")
    groups = stats["groups"]
    lines.append(f"   - 显式分组键 {groups['items_with_declared_group']} 条；"
                 f"无显式键（靠 state 或 id 兜底）{groups['items_without_declared_group']} 条")
    lines.append(f"   - 组数 {groups['groups']}；多条目组 {groups['multi_item_groups']} 个；"
                 f"最大组 {groups['largest_group']} 条；跨多个 state 的组 "
                 f"{groups['groups_with_multiple_states']} 个；含多个显式分组 id 的组 "
                 f"{groups['groups_with_multiple_declared_ids']} 个")
    lines.append(f"   - 无 state 的条目 {groups['items_without_state']} 条；"
                 f"state 分组：{'开启' if groups['state_grouping'] else '关闭'}")
    gate = stats.get("group_id_gate") or {}
    if gate:
        state_text = "已通过" if not gate.get("missing") else (
            "已用 --allow-missing-group-id 跳过（危险）" if gate.get("skipped") else "未通过")
        lines.append(f"   - 中文侧分组 id 门禁（{', '.join(gate.get('required_langs', []))}）：{state_text}"
                     + (f"，缺失 {gate['missing']} 条" if gate.get("missing") else ""))
    lines.append("2. **分层**：按 (domain, lang) 分层；层内组按种子洗牌，benchmark 先按 10% 预留，"
                 "其余组按 6:2:1 用「目标条数 - 已分配条数」最大缺口贪心分配。")
    lines.append("3. **benchmark 保底**：对每个 lang x kind、每个 domain、每个 lang 设下限，"
                 "不足时从其余组整组补足；该类总量不足下限时取全部并在下表标「是」。")
    lines.append("4. **确定性**：随机数来自 random.Random(\"seed|阶段|domain|lang\")；分区内条目按 id 排序；"
                 "gzip 以 mtime=0 写入 → 同一输入重跑逐字节一致。")
    lines.append("")
    lines.append("## 2. 分区规模")
    lines.append("")
    lines.append("| 分区 | 条目 | 占比 | 目标占比 | 请求组 |")
    lines.append("|---|---:|---:|---:|---:|")
    for split in SPLITS:
        item_count = counts["items"][split]
        lines.append(f"| {split} | {item_count} | {item_count / total:.1%} | {ratios[split]:.0%} "
                     f"| {group_counts[split]} |")
    lines.append("")
    lines.append("## 3. 数据成色与已知缺口（用户决策必读）")
    lines.append("")
    lines.append("| 语言 | 条目 | 覆盖的 kind | 来源数 | 最大来源占比 |")
    lines.append("|---|---:|---|---:|---:|")
    for lang, count in sorted(composition["items_by_lang"].items(), key=lambda kv: -kv[1]):
        kinds = ", ".join(composition["kinds_by_lang"].get(lang, [])) or "-"
        sources = composition["sources_by_lang"].get(lang, {})
        top = next(iter(sources.values()), 0)
        lines.append(f"| {lang} | {count} | {kinds} | {len(sources)} | {top / max(count, 1):.0%} |")
    lines.append("")
    lines.append("| kind | 出现在哪些语言 |")
    lines.append("|---|---|")
    for kind, langs in sorted(composition["langs_by_kind"].items()):
        lines.append(f"| {kind} | {', '.join(langs)} |")
    lines.append("")
    for kind, langs in sorted(composition["langs_by_kind"].items()):
        missing = [lang for lang in composition["items_by_lang"] if lang not in langs]
        if missing:
            lines.append(f"- **{kind} 只来自 {'/'.join(langs)}**，{'/'.join(missing)} 侧没有 {kind} 形态的原生数据。")
    for row in composition.get("single_source_langs", []):
        lines.append(f"- **{row['lang']} 侧只有单一来源** {row['dataset']}（{row['items']} 条，"
                     f"占全语料 {row['share']:.0%}）——低于契约 40% 上限，但**没有第二来源兜底**，"
                     "跨来源去偏能力有限，训练决策请按单一来源对待。")
    lines.append("- 可选补强路径：中文 noul/score 目前没有原生来源；task-14 的中文分类衍生池"
                 "（42,436 条，单标签 + documented 映射，**非原生四元组**）可作补强，属成色降级，"
                 "需用户确认后另行引入——**本轮未引入**。")
    lines.append("")
    lines.append("## 4. 分布（每区内部占比）")
    lines.append("")
    for index, dimension in enumerate(("lang", "domain", "kind"), start=1):
        lines.append(f"### 4.{index} {dimension}")
        lines.append("")
        lines.append("| " + dimension + " | " + " | ".join(SPLITS) + " |")
        lines.append("|---|" + "---:|" * len(SPLITS))
        for key in sorted(counts[dimension]):
            cells = []
            for split in SPLITS:
                have = counts[dimension][key].get(split, 0)
                base = counts["items"][split] or 1
                cells.append(f"{have} ({have / base:.0%})")
            lines.append(f"| {key} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.append("### 4.4 分层漂移（各区内 (domain, lang) 占比 vs 全局占比）")
    lines.append("")
    lines.append("| 分区 | 最大占比差 | 该层 |")
    lines.append("|---|---:|---|")
    global_cells = Counter((record["domain"], record["lang"]) for record in records)
    for split in SPLITS:
        base = counts["items"][split] or 1
        split_cells = Counter((record["domain"], record["lang"])
                              for record, assigned in zip(records, split_of_item) if assigned == split)
        worst, worst_cell = 0.0, "-"
        for cell, count in global_cells.items():
            gap = abs(split_cells.get(cell, 0) / base - count / total)
            if gap > worst:
                worst, worst_cell = gap, f"{cell[0]}/{cell[1]}"
        lines.append(f"| {split} | {worst:.1%} | {worst_cell} |")
    lines.append("")
    lines.append("## 5. benchmark 保底配额")
    lines.append("")
    lines.append("| 单元 | 下限 | 实际 | 该类不足（取全部） |")
    lines.append("|---|---:|---:|---|")
    for floor in stats["benchmark_floors"]:
        lines.append(f"| {floor['cell']} | {floor['required']} | {floor['have']} | "
                     f"{'是' if floor.get('capped') else '否'} |")
    lines.append("")
    lines.append("## 6. 泄漏检查（必须为空）")
    lines.append("")
    lines.append(f"- 跨分区的组：{leaks['groups_multi_split']}")
    lines.append(f"- 跨分区的同一 state：{leaks['states_multi_split']}")
    lines.append(f"- 跨分区的 id：{leaks['ids_multi_split']}")
    lines.append(f"- 复核范围：{leaks['distinct_groups']} 组 / {leaks['distinct_states']} 个不同 state")
    if leaks["problems"]:
        lines.append("")
        for problem in leaks["problems"]:
            lines.append(f"    {problem}")
    else:
        lines.append("- 结论：**空**（按组切分 + state 合并后无任何跨区）。")
    lines.append("")
    lines.append("## 7. 来源汇总（benchmark 分区，聚合）")
    lines.append("")
    lines.append("| dataset | revision | license | 条目 |")
    lines.append("|---|---|---|---:|")
    for row in stats["sources"]:
        lines.append(f"| {row['dataset']} | {row['revision']} | {row['license']} | {row['items']} |")
    lines.append("")
    lines.append("## 8. 产物")
    lines.append("")
    for split in SPLITS:
        suffix = "（**内部，勿公开**）" if split == "benchmark" else ""
        lines.append(f"- data/splits/{split}.jsonl（+.gz）：{counts['items'][split]} 条{suffix}")
    lines.append("- data/splits/benchmark-dataset/：可直接上传 HF 的 private benchmark"
                 "（dataset card + benchmark.jsonl(.gz) + manifest.json）")
    lines.append("- data/splits/split-manifest.json：各产物 sha256 与复跑校验结果（机器可读）")
    lines.append("")
    lines.append("## 9. 可复现性（两次运行逐字节一致）")
    lines.append("")
    lines.append(f"- 随机种子：{seed}；同一输入 + 同一种子 → 同一分组、同一分配、同一顺序。")
    lines.append("- 分区内条目按 id 排序；gzip 以 mtime=0 写入（gzip 头不含时间戳，否则两次压缩不会逐字节相同）。")
    lines.append("- 输出把裸 U+2028 / U+2029 / U+0085 统一写成 \\uXXXX 转义（无损）：它们在 JSON 里合法，"
                 "但用 str.splitlines() 读会被当成换行、把记录劈开。")
    if rerun:
        state = "**逐字节一致**" if rerun.get("identical") else "**不一致（见 problems）**"
        lines.append(f"- 本次运行额外完整复跑一遍并写到独立临时目录，比对 {rerun['files']} 个产物文件：{state}。")
        lines.append(f"- 产物树哈希（sha256 over 文件名+文件哈希）：{rerun.get('tree_sha256', '')}")
        lines.append("- 比对范围：" + "、".join(PRODUCT_FILES))
        if rerun.get("problems"):
            lines.append("- 差异：" + "; ".join(rerun["problems"]))
    else:
        lines.append("- 本次运行未启用复跑校验（--no-verify-rerun）。")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- 主流程

def _parse_ratios(raw: str) -> dict:
    ratios: dict = {}
    for part in raw.split(","):
        name, _, value = part.partition("=")
        name = name.strip()
        if name not in SPLITS:
            raise ValueError(f"未知分区 {name!r}")
        ratios[name] = float(value)
    missing = [split for split in SPLITS if split not in ratios]
    if missing:
        raise ValueError(f"缺少分区 {missing}")
    return ratios


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="最终语料切分 6:2:1:1（按请求分组）+ 内部 benchmark")
    parser.add_argument("--input", action="append", default=[], metavar="PATH",
                        help="输入 JSONL 或目录（可重复；默认取最终语料 items.final.jsonl）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"分区输出目录（默认 {DEFAULT_OUT}）")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="切分报告路径")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--ratios", default=None, help="覆盖比例，如 train=0.6,test=0.2,validation=0.1,benchmark=0.1")
    parser.add_argument("--benchmark-min-per-domain", type=int, default=DEFAULT_BENCHMARK_MIN_PER_CELL)
    parser.add_argument("--benchmark-min-per-lang", type=int, default=DEFAULT_BENCHMARK_MIN_PER_CELL)
    parser.add_argument("--benchmark-min-per-kind", type=int, default=DEFAULT_BENCHMARK_MIN_PER_CELL)
    parser.add_argument("--no-state-grouping", action="store_true", help="只用显式分组键（默认会合并同 state）")
    parser.add_argument("--allow-duplicates", action="store_true", help="重复 id 保留首条而不报错")
    parser.add_argument("--require-group-id-lang", action="append", default=None, metavar="LANG",
                        help="这些语言必须带显式分组 id（默认 zh；中文侧缺 id 直接拒绝切分）")
    parser.add_argument("--allow-missing-group-id", action="store_true",
                        help="危险：允许中文侧缺分组 id（会退化成按行切，只用于探索）")
    parser.add_argument("--no-verify-rerun", action="store_true",
                        help="跳过复跑逐字节校验（默认会完整跑第二遍写到临时目录并比对）")
    parser.add_argument("--salt-file", type=Path, default=None,
                        help="仓库外私盐文件（交付件必须给；盐的 sha256 前 16 位折进所有随机种子）")
    parser.add_argument("--public-demo", action="store_true",
                        help="无盐跑法：结果确定但**不是交付件**，且必须写到仓库外（保密性测试用）")
    parser.add_argument("--benchmark-lang", action="append", default=None, metavar="LANG",
                        help="只允许这些语言进 benchmark（可重复；不写=不限。本轮交付用 en）")
    parser.add_argument("--dry-run", action="store_true", help="只算不写（检查输入与比例）")
    args = parser.parse_args(argv)

    ratios = dict(DEFAULT_RATIOS)
    if args.ratios:
        try:
            ratios = _parse_ratios(args.ratios)
        except ValueError as exc:
            print(f"参数错误：--ratios {exc}", file=sys.stderr)
            return 2

    required_langs = tuple(args.require_group_id_lang) if args.require_group_id_lang else ("zh",)
    ignored_inputs: list = []
    repo_root = git_repo_root(Path(__file__).resolve().parent)

    # ---- 保密门禁：交付件必须带仓外私盐 ----
    salt = None
    if args.salt_file is not None:
        try:
            salt = read_salt(args.salt_file, repo_root=repo_root)
        except SplitError as exc:
            print(f"拒绝切分：{exc}", file=sys.stderr)
            return 3
    elif not args.dry_run and not args.public_demo:
        print("拒绝切分：交付件必须用仓外私盐（--salt-file）。", file=sys.stderr)
        print("  公开脚本 + 公开种子若能复现 benchmark，保密就不成立；"
              "只想看流程请加 --dry-run，或显式 --public-demo（输出必须写到仓库外，且不是交付件）。",
              file=sys.stderr)
        return 3
    if salt is None and not args.dry_run and args.public_demo:
        for label, path in (("--out", args.out), ("--report", args.report)):
            if path_inside(repo_root, path):
                print(f"拒绝切分：--public-demo 的 {label} 必须写在仓库外（当前 {path} 在仓库内）。",
                      file=sys.stderr)
                return 3
    if salt is None and args.dry_run:
        print("提示：dry-run 无盐，结果与交付件不同（仅用于检查输入与比例）。", file=sys.stderr)

    def pipeline():
        """一次完整流水线：读 → 分组/门禁 → 切分 → 派生分区与统计（复跑校验会再调一次）。"""
        items_, records_, load_ = load_records(paths, allow_duplicates=args.allow_duplicates)
        gaps_ = group_id_gaps(records_, required_langs=required_langs)
        splits_, labels_, stats_, _ = assign_all(
            records_, ratios=ratios, seed=args.seed, salt=salt,
            benchmark_langs=tuple(args.benchmark_lang) if args.benchmark_lang else None,
            use_state=not args.no_state_grouping,
            min_per_domain=args.benchmark_min_per_domain,
            min_per_lang=args.benchmark_min_per_lang,
            min_per_kind=args.benchmark_min_per_kind)
        stats_["group_id_gate"] = {
            "required_langs": list(required_langs),
            "missing": gaps_["total"],
            "skipped": bool(args.allow_missing_group_id and gaps_["total"]),
        }
        stats_["input"] = load_
        stats_["input"]["ignored"] = ignored_inputs
        leak_ = leak_report(records_, labels_, splits_, items_)
        split_items_ = {split: [] for split in SPLITS}
        for item, split in zip(items_, splits_):
            split_items_[split].append(item)
        for split in SPLITS:
            split_items_[split].sort(key=lambda item: str(item.get("id")))
        counts_ = {dimension: defaultdict(Counter) for dimension in ("lang", "domain", "kind")}
        counts_["items"] = Counter()
        for record, split in zip(records_, splits_):
            counts_["items"][split] += 1
            counts_["lang"][record["lang"]][split] += 1
            counts_["domain"][record["domain"]][split] += 1
            for kind in record["kinds"]:
                counts_["kind"][kind][split] += 1
        stats_["sources"] = source_summary(split_items_["benchmark"])
        benchmark_groups_ = len({label for label, split in zip(labels_, splits_) if split == "benchmark"})
        return {"items": items_, "records": records_, "splits": splits_, "labels": labels_,
                "stats": stats_, "gaps": gaps_, "leaks": leak_, "split_items": split_items_,
                "counts": counts_, "benchmark_groups": benchmark_groups_}

    try:
        paths = resolve_inputs(args.input, ignored=ignored_inputs)
        first = pipeline()
    except SplitError as exc:
        print(f"切分失败：{exc}", file=sys.stderr)
        return 2

    gaps = first["gaps"]
    if gaps["total"] and not args.allow_missing_group_id:
        print(f"拒绝切分：中文侧有 {gaps['total']} 条没有显式分组 id"
              "（按行切会静默泄漏，比切不出来更糟）。", file=sys.stderr)
        for key, count in sorted(gaps["missing"].items()):
            print(f"  - {key}: {count} 条（例 {gaps['examples'][key]}）", file=sys.stderr)
        print("请让中文侧为同一请求的变体写同一个 group_id / request_id；"
              "确认可接受才加 --allow-missing-group-id（危险）。", file=sys.stderr)
        return 3

    leaks = first["leaks"]
    stats = first["stats"]
    counts = first["counts"]
    print(f"输入 {len(paths)} 个文件 / {len(first['items'])} 条 / {stats['groups']['groups']} 组；"
          + "，".join(f"{split}={counts['items'][split]}" for split in SPLITS))
    print(f"泄漏检查：跨区组 {leaks['groups_multi_split']}，跨区 state {leaks['states_multi_split']}，"
          f"跨区 id {leaks['ids_multi_split']}")
    if args.dry_run:
        print("dry-run：未写任何文件")
        return 0 if leaks["problem_count"] == 0 else 1

    written = write_split_files(args.out, first["split_items"])
    export_benchmark_dataset(args.out / "benchmark-dataset", first["split_items"]["benchmark"],
                             first["benchmark_groups"], stats["sources"], seed=args.seed, ratios=ratios)

    rerun = None
    if not args.no_verify_rerun:
        # 复跑校验：完整再跑一遍（重新读文件、重新分组、重新分配）并写到独立临时目录，逐字节比对
        with tempfile.TemporaryDirectory(prefix="pol-split-rerun-") as workspace:
            rerun_dir = Path(workspace)
            second = pipeline()
            write_split_files(rerun_dir, second["split_items"])
            export_benchmark_dataset(rerun_dir / "benchmark-dataset", second["split_items"]["benchmark"],
                                     second["benchmark_groups"], second["stats"]["sources"],
                                     seed=args.seed, ratios=ratios)
            rerun = compare_dirs(args.out, rerun_dir)

    composition = composition_summary(first["records"], first["items"])
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(inputs=paths, items=first["items"], records=first["records"],
                      split_of_item=first["splits"], labels=first["labels"], stats=stats, leaks=leaks,
                      seed=args.seed, ratios=ratios, counts=counts, composition=composition,
                      rerun=rerun),
        encoding="utf-8", newline="\n")

    manifest = {
        "schema": "pol-split-manifest/0.1",
        "seed": args.seed,
        "ratios": ratios,
        "inputs": [path.as_posix() for path in paths],
        "items": len(first["items"]),
        "counts": {split: counts["items"][split] for split in SPLITS},
        "salt_policy": {
            "salted": salt is not None,
            "benchmark_langs": sorted(args.benchmark_lang) if args.benchmark_lang else None,
            "note": "交付件使用仓库外私盐；盐值与盐的哈希都不记录、不派生进任何公开产物。"
                    "只凭本 manifest 的公开种子无法复现交付件；无盐跑法（--public-demo）产出的是另一套。"
                    if salt is not None else
                    "本次为无盐 public-demo 运行，不是交付件。",
        },
        "rerun": None if rerun is None else {"files": rerun["files"], "identical": rerun["identical"],
                                             "tree_sha256": rerun["tree_sha256"]},
        "digests": {} if rerun is None else rerun["digests"],
    }
    (args.out / "split-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")

    print(f"已写：{args.out}（4 个分区 + benchmark-dataset + split-manifest.json）、{report_path}")
    for split in SPLITS:
        print(f"  {split}: {written[split]['items']} 条")
    if rerun is not None:
        print(f"复跑校验：{rerun['files']} 个文件逐字节"
              f"{'一致' if rerun['identical'] else '不一致'}，树哈希 {rerun['tree_sha256'][:16]}")
    return 0 if leaks["problem_count"] == 0 and (rerun is None or rerun["identical"]) else 1


if __name__ == "__main__":
    raise SystemExit(run())
