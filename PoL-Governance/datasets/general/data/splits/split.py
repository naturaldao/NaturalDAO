"""最终语料切分：按请求分组、按 domain x lang 分层、6:2:1:1、内部 benchmark（task-20 / task-3）。

用法（交付件必须带仓外私盐，且显式写 --out / --report）::

    uv run --no-project --offline python datasets/general/data/splits/split.py \
        --out datasets/general/data/splits --report datasets/general/split-report.md \
        --seed 20261005 --salt-file D:/pol2-raw/pol-split-salt.txt \
        --benchmark-lang en --benchmark-exclude-lang "zh=<理由>" \
        --exclude-public-items --derived-skip datasets/general/data/target-types.jsonl.gz \
        [--benchmark-exclude-ids D:/pol2-raw/pol-rotation/excluded-benchmark-ids.txt] \
        --train-supplement datasets/general/data/zh-supplement/items.jsonl

**默认值不会误伤交付件**：--out / --report 的默认值仍指向交付目录（datasets/general/data/splits、
datasets/general/split-report.md），但只要这两个参数**没有显式给出**，而目标位置已存在交付件
（split-manifest.json / 报告文件），本次运行就直接拒绝并返回 3——想覆盖必须显式写 --out / --report
或加 --force。默认值只用于"第一次生成"，不会把已交付的四区或公开报告悄悄换掉。

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
3. **benchmark 不是随机抽样，还要按来源均衡**：先按 10% 比例预留，再对 lang x kind、domain、lang 做
   保底配额补齐（该类不足时取全部）；同时用**水位法**给每个来源算配额：任一来源占比硬上限
   max_source_share（默认 25%）、每个来源下限 min_source_share（默认 5%，"各个来源都收集一点"）。
   上限不可行时才放宽到可行界 1/来源数（例如只有一个来源的合成语料），并把实际值写进报告。
   见 benchmark_source_quota / reserve_benchmark。
4. **benchmark 的语言覆盖必须是显式声明**：语料里出现的每种语言，要么允许进 benchmark
   （--benchmark-lang），要么用 --benchmark-exclude-lang LANG=理由 显式排除；漏一种就拒绝切分
   （返回 3）。本轮交付把 zh 显式排除——中文侧的 (group_id → 正确工具) 答案索引仍在公开 git 历史里
   可达（实测覆盖 5,454/5,454 组 = 100%），换盐也挡不住，理由与证据写进报告与 manifest。
5. **隐私**：benchmark 条目只写进 --out（分区 + benchmark-dataset 包）；split-report.md 与
   dataset card/manifest 只有聚合统计，**不含任何样本内容**（test_split.py 有对应断言）。
   包内 verify.py 由 tracked 模板 verify_benchmark_package.py 复制而来，必须 exit 0
   （datasets/general/test_benchmark_package.py 每次都跑）。请勿把 benchmark.jsonl(.gz) 或
   benchmark-dataset/ 提交到公开仓库——它由用户上传 Hugging Face 并设为 private。
6. **train-only 补充集**：--train-supplement 把降级（origin != source）中文补充整批追加到 train 末尾，
   只追加 train，绝不进 test/validation/benchmark；id 与语料重叠、或补充集里混入原生条目 → 直接拒绝。
7. **事故轮换**：--benchmark-exclude-ids 读一份**仓外**永久排除名单（一行一个 id），名单里的条目
   永久不进 benchmark。用途是 benchmark 轮换：某个派生交付件曾把 benchmark 成员的 probs 带进公开面，
   这些 id 即使用同一私盐重切也必须排除（详见 split-report.md §10.5）。名单不允许进仓库，否则等于
   把"哪些条目曾是 benchmark 成员"再公开一次（与盐同级保密）。
8. **公开引用排除**：--exclude-public-items 扫被 git 跟踪的**手写**文件，把其中引用过的 id 对应条目
   排除出 benchmark（被公开引用过 = 已泄漏，不能进盲测集）；派生产物（分区、target-types、jev-probs）
   切分后会被重新生成，用 --derived-skip 跳过。

可复现：随机数全部来自 random.Random("seed|盐token|阶段|domain|lang")，分区内条目按 id 排序，
补充集按文件顺序追加在 train 末尾，gzip 用 mtime=0 写入；同一输入 + 同一私盐重跑两次逐字节一致
（test_split.py 有对应测试）。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

#: 打包模块与它同目录：直接跑脚本时 sys.path[0] 就是这里，被 test_split.py 导入时也已插入；
#: 再兜一次，保证从任意 cwd 调用都不会 ImportError。
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import package_benchmark  # noqa: E402  （同目录模块，必须在 sys.path 就绪后导入）

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
#: benchmark 内任一来源的条目占比**硬上限**（水位法配额 + 选择时再查一次）。选 25% 的理由见
#: benchmark_source_quota 与 split-report.md「来源均衡」一节：语料里 6 个英文来源，25% 意味着
#: 至少 4 个来源共同撑起 benchmark；再收紧（如 15%）会把只占池子 2.8% 的小来源放大 5 倍以上，
#: 让 benchmark 偏离真实训练分布。上限不可行（来源数太少）时自动放宽到可行界 1/来源数。
DEFAULT_BENCHMARK_MAX_SOURCE_SHARE = 0.25
#: benchmark 内每个来源的条目占比下限（"各个来源都收集一点"）；来源池不够时取全部。
DEFAULT_BENCHMARK_MIN_SOURCE_SHARE = 0.05
#: benchmark 内每个来源的**绝对**条目下限：语料规模变大后 5% 会变成 300+ 条，
#: 足以把小来源（如只有 447 条的 kaivoss）抽干 70%。交付时用 --benchmark-min-source-items 给绝对值，
#: 让"每个来源都有切片"与"不把小来源抽干"同时成立。
DEFAULT_BENCHMARK_MIN_SOURCE_ITEMS = 0
#: train-only 降级补充集（中文 3,148 条，origin=taxonomy）。只追加 train，不进其它三区。
DEFAULT_TRAIN_SUPPLEMENT = Path("datasets/general/data/zh-supplement/items.jsonl")
#: 报告与 benchmark 包的版本号（每次重切改变 benchmark 条目集合就必须递增；跨版本分数不可拼接）
REPORT_VERSION = "v5"
PACKAGE_VERSION = "0.5"
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


def item_source(item: dict) -> str:
    """条目的来源数据集名；缺 source.dataset 时归到 (unknown)（报告里如实显示）。"""
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    name = source.get("dataset")
    return str(name) if isinstance(name, str) and name.strip() else "(unknown)"


def origin_of(item: dict) -> str:
    """条目来源层级：source=来源原生四元组（A 层）；其它（taxonomy 等）=降级派生（B 层）。

    一条记录的问题可能有多种 origin；全同取该值，混合取 mixed。只用于聚合报告。
    """
    origins = {str(q.get("origin") or "taxonomy") for q in item.get("questions") or []
               if isinstance(q, dict)}
    if not origins:
        return "(unknown)"
    if len(origins) == 1:
        return next(iter(origins))
    return "mixed"


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
                "source": item_source(item),
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


def record_source(record) -> str:
    """record["source"]，缺失时兜底 (unknown)（调用方可能手工构造 records）。"""
    return str(record.get("source") or "(unknown)")


def group_source_mix(group_records) -> Counter:
    """组内每个来源的条目数。组可能跨来源（同 state 的翻译/改写），所以按来源分别计数。"""
    return Counter(record_source(record) for record in group_records)


def benchmark_source_quota(pool: dict, target: int, *, max_share: float, min_share: float,
                           min_items: int = 0) -> dict:
    """水位法：把 target 条按各来源池子大小分配，并夹在 [floor, cap] 之间。

    为什么是 25% 上限（DEFAULT_BENCHMARK_MAX_SOURCE_SHARE）：英文侧有 6 个来源，
    25% 意味着**至少 4 个来源**共同撑起 benchmark，任一来源都不能单独决定总分；
    再收紧（如 15%）会把只占池子 2.8% 的小来源放大 5 倍以上——benchmark 是用来估计
    "在这份语料上表现如何"的，过度均匀化会让它偏离真实训练分布。同时 25% ≤ 契约 40%，
    且与第二大来源的自然占比（25.1%）同量级：最大的来源不再比第二名占便宜。
    下限是 max(占比下限 min_share, 绝对下限 min_items)：语料变大后 5% 会变成几百条，
    足以把小来源抽干，交付时用 min_items 给一个绝对条数（如 100），两者取大。
    min_share/min_items 都为 0 时不设下限（只按规模分配 + 上限削顶）。

    可行性：cap 至少放宽到 1/来源数（只有一个来源时无从谈均衡），
    此时 cap_policy="feasible_bound"，报告里如实写明。
    """
    names = sorted(pool)
    quota = {name: 0 for name in names}
    info = {"target": int(target), "cap": 0, "floor": 0, "cap_policy": "no_sources",
            "policy_cap": 0, "feasible_bound": 0,
            "eligible_sources": len(names), "pool_total": int(sum(pool.values()))}
    if not names or target <= 0:
        return {"quota": quota, **info}
    target = int(min(target, sum(pool.values())))
    if target <= 0:
        return {"quota": quota, **info}
    bound = -(-target // len(names))  # ceil(target / n)：来源数决定的可行界
    # 政策上限**取下整**：占比是按实际产物条数算的，上整会让 400/1598=25.03% 这种擦边越界出现
    policy_cap = int(max_share * target) if max_share > 0 else target
    cap = min(target, max(policy_cap, bound)) if max_share > 0 else target
    floor_want = max(int(min_share * target) if min_share > 0 else 0, int(min_items))
    floor = 0 if floor_want <= 0 else min(cap, max(1, floor_want))
    if floor * len(names) > target:
        floor = target // len(names)
    info.update({"target": target, "cap": cap, "floor": floor, "min_source_items": int(min_items),
                 "cap_policy": "policy" if policy_cap >= bound else "feasible_bound",
                 "policy_cap": policy_cap, "feasible_bound": bound})

    free = {name: int(pool[name]) for name in names}
    alloc: dict = {}
    remaining = target
    while free:
        # 权重用**池子大小**：先按规模比例分，越界（>上限 / <下限）的逐个夹住再回流，
        # 这才是"按规模分配 + 上限削顶 + 下限托底"，而不是把小来源放大成平均分。
        weight = sum(free[name] for name in free)
        if weight <= 0:
            for name in free:
                alloc[name] = 0
            break
        scaled = {name: remaining * free[name] / weight for name in free}
        over = sorted((name for name in free if scaled[name] > cap + 1e-9),
                      key=lambda name: (-(scaled[name] - cap), name))
        under = sorted((name for name in free if scaled[name] < floor - 1e-9),
                       key=lambda name: (scaled[name], name))
        if over:
            name, value = over[0], min(cap, free[over[0]])
        elif under:
            name, value = under[0], min(floor, free[under[0]])
        else:
            alloc.update(scaled)
            break
        alloc[name] = value
        remaining -= value
        del free[name]

    # 量化成整数：先取整，再按小数部分从大到小补足（同分按来源名，保证确定性）
    quantized = {name: min(int(alloc.get(name, 0)), int(pool[name])) for name in names}
    rest = target - sum(quantized.values())
    if rest > 0:
        order = sorted(names, key=lambda name: (-(alloc.get(name, 0) - int(alloc.get(name, 0))), name))
        for name in order:
            if rest <= 0:
                break
            if quantized[name] < int(pool[name]):
                quantized[name] += 1
                rest -= 1
    return {"quota": quantized, **info}


_TOKEN = re.compile(r"[A-Za-z0-9]+")


def content_overlap_groups(records_by_group, reserved, *, min_state_len: int = 20,
                           rare_df_limit: int = 400) -> tuple:
    """找出**内容被公开侧包含**的保留组：它的 state 完整出现在某个未保留条目的 state 里。

    为什么需要：分组只按"state 完全相等"合并，**子串包含**是另一种重叠。实测（v4 语料）
    bigbench 的 question_selection 条目把 cosmos 的整段 context 嵌在自己的 state 里，
    而旧 Jev 语料里有条目的 state 恰好就是那段 context——两者 state 不同、分组不会合并，
    结果一个进 benchmark、一个进 test，benchmark 的 state 正文就出现在公开文件里。
    这种组不能当盲测成员（正文已公开），整组移出 benchmark。

    实现：对"公开侧"（未保留组）建 词→条目 倒排索引，保留组按最稀有词取候选再逐条做子串判断；
    全由常见词构成的 state（df > rare_df_limit）用拼接全文兜底扫描，保证不漏。
    """
    public_states: list = []
    for label, group in records_by_group.items():
        if label in reserved:
            continue
        for record in group:
            state = record.get("state_norm") or ""
            if len(state) >= min_state_len:
                public_states.append((label, state))
    df: Counter = Counter()
    index: dict = defaultdict(list)
    for position, (_label, state) in enumerate(public_states):
        for token in {tok for tok in _TOKEN.findall(state) if len(tok) >= 4}:
            df[token] += 1
            index[token].append(position)
    blob = "\n\u0000\n".join(state for _label, state in public_states)
    overlapped: set = set()
    checked = fallback = 0
    for label in sorted(reserved):
        for record in records_by_group[label]:
            state = record.get("state_norm") or ""
            if len(state) < min_state_len:
                continue
            checked += 1
            tokens = sorted((tok for tok in set(_TOKEN.findall(state)) if len(tok) >= 4 and tok in df),
                            key=lambda tok: (df[tok], tok))
            found = False
            if tokens and df[tokens[0]] <= rare_df_limit:
                for position in index[tokens[0]]:
                    if state in public_states[position][1]:
                        found = True
                        break
            else:
                fallback += 1
                if state in blob:
                    found = True
            if found:
                overlapped.add(label)
                break
    return overlapped, {"checked_items": checked, "fallback_scans": fallback}


def reserve_benchmark(records_by_group, ratios: dict, seed: int, salt=None, *,
                      benchmark_langs=None,
                      min_per_domain: int, min_per_lang: int, min_per_kind: int,
                      max_source_share: float = DEFAULT_BENCHMARK_MAX_SOURCE_SHARE,
                      min_source_share: float = DEFAULT_BENCHMARK_MIN_SOURCE_SHARE,
                      min_source_items: int = DEFAULT_BENCHMARK_MIN_SOURCE_ITEMS,
                      exclude_ids: frozenset = frozenset()):
    """第一阶段：按 10% 预留 benchmark——先按来源水位配额取，再按 lang x kind / domain / lang 保底补齐。

    benchmark_langs 限定哪些语言可以进 benchmark（其余语言不预留、不设保底，全部分到公开三区）。
    exclude_ids：**已出现在公开文件里的条目 id**（被 README/fixtures/文档引用过），这些条目
    不进 benchmark——"被公开引用过的条目永不进盲测集"，由机器保证，不靠人工维护文档。
    来源配额在**每个来源内部再按 (domain, lang) 分层**取，使每个来源的切片仍是它自己的自然分布；
    选择时逐组复核硬上限 cap，保证任一来源占比不超过上限（组粒度最多差一条组）。
    返回 (reserved 组集合, 保底明细, 来源均衡报告)。
    """
    allowed = tuple(benchmark_langs) if benchmark_langs else None
    excluded_groups = 0
    excluded_items = 0
    eligible = {}
    for label, group in records_by_group.items():
        if allowed is not None and group_stratum(group)[1] not in allowed:
            continue
        if exclude_ids and any(record["id"] in exclude_ids for record in group):
            excluded_groups += 1
            excluded_items += len(group)
            continue
        eligible[label] = group
    eligible_total = sum(len(group) for group in eligible.values())
    target = int(round(eligible_total * ratios["benchmark"]))
    pool: Counter = Counter()
    for group in eligible.values():
        for record in group:
            pool[record_source(record)] += 1
    plan = benchmark_source_quota(dict(pool), target, max_share=max_source_share,
                                  min_share=min_source_share, min_items=min_source_items)
    quotas, cap_items = plan["quota"], plan["cap"]
    # 硬上限：来源数 ≥ 2 时始终生效（cap 已经取 max(政策上限, 可行界)，一定可行）；
    # 只有一个来源时无从谈均衡，此时不设上限，否则保底配额永远补不进来。
    hard_cap = cap_items if len(plan["quota"]) > 1 else None
    reserved: set = set()
    taken_by_source: Counter = Counter()

    def can_add(label) -> bool:
        """加这个组会不会让任一来源越过硬上限（组粒度：整组进，不拆）。"""
        if hard_cap is None:
            return True
        for source, count in group_source_mix(eligible[label]).items():
            if taken_by_source[source] + count > hard_cap:
                return False
        return True

    def add(label) -> None:
        reserved.add(label)
        for source, count in group_source_mix(eligible[label]).items():
            taken_by_source[source] += count

    for source in sorted(quotas):
        want = quotas[source]
        if want <= 0:
            continue
        by_stratum: dict = defaultdict(list)
        for label, group in eligible.items():
            if any(record_source(record) == source for record in group):
                by_stratum[group_stratum(group)].append(label)
        source_items = sum(len(eligible[label]) for labels in by_stratum.values() for label in labels)
        # 每个来源内部按层取：先按该来源在各层的占比分配配额，再整组取到为止
        for stratum in sorted(by_stratum):
            labels = by_stratum[stratum]
            if labels == [] or taken_by_source[source] >= want:
                continue
            share = want * sum(len(eligible[label]) for label in labels) / max(source_items, 1)
            taken_here = 0
            for label in _shuffled(labels, seed, salt, "bench-source", source, *stratum):
                if taken_here >= share or taken_by_source[source] >= want:
                    break
                if label in reserved or not can_add(label):
                    continue
                add(label)
                taken_here += len(eligible[label])
        # 兜底：本来源还没取够（层粒度/上限挡掉了一部分），按整体洗牌补齐
        if taken_by_source[source] < want:
            rest = [label for labels in by_stratum.values() for label in labels]
            for label in _shuffled(rest, seed, salt, "bench-source-topup", source):
                if taken_by_source[source] >= want:
                    break
                if label in reserved or not can_add(label):
                    continue
                add(label)

    # 补到目标条数：只要还有未选组、且不越硬上限就继续取（组粒度允许略超目标）。
    # 这一步是"占比上限"能严格成立的前提：占比按**实际**条数算，总数不足目标时同一条数会放大占比。
    if sum(taken_by_source.values()) < plan["target"]:
        for label in _shuffled([label for label in eligible if label not in reserved],
                               seed, salt, "bench-source-fill"):
            if sum(taken_by_source.values()) >= plan["target"]:
                break
            if not can_add(label):
                continue
            add(label)

    def cell_items(predicate) -> int:
        return sum(len(records_by_group[label]) for label in reserved if predicate(label))

    domains = sorted({record["domain"] for group in eligible.values() for record in group})
    langs = sorted({record["lang"] for group in eligible.values() for record in group})
    pairs = sorted({(record["lang"], kind) for group in eligible.values()
                    for record in group for kind in record["kinds"]})
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
            floors.append({"cell": name, "required": required, "have": have, "capped": False,
                           "blocked_by_source_cap": 0})
            continue
        candidates = [label for label in eligible if label not in reserved and predicate(label)]
        available = sum(len(eligible[label]) for label in candidates)
        added = blocked = 0
        for label in _shuffled(candidates, seed, salt, "floor", name):
            if cell_items(predicate) >= required:
                break
            if not can_add(label):
                blocked += 1
                continue
            add(label)
            added += len(eligible[label])
        have = cell_items(predicate)
        floors.append({"cell": name, "required": required, "have": have, "added_items": added,
                       "available_before": available, "capped": have < required,
                       "blocked_by_source_cap": blocked})

    # 内容重叠剔除：state 正文已被公开侧完整包含的组不能当盲测成员（见 content_overlap_groups）。
    overlapped, overlap_stats = content_overlap_groups(records_by_group, reserved)
    if overlapped:
        reserved -= overlapped
        taken_by_source.clear()
        for label in reserved:
            for source, count in group_source_mix(eligible[label]).items():
                taken_by_source[source] += count
        # 保底表的"实际/该类不足"必须反映**剔除后**的最终保留集，否则表里会多算被剔掉的组
        for entry, (required, _name, predicate) in zip(floors, definitions):
            entry["have"] = cell_items(predicate)
            entry["capped"] = entry["have"] < required
    total_reserved = sum(taken_by_source.values())
    rows = []
    for source in sorted(pool):
        items = taken_by_source[source]
        rows.append({"dataset": source, "pool": int(pool[source]), "quota": int(quotas.get(source, 0)),
                     "items": int(items), "share": items / max(total_reserved, 1),
                     "pool_share": int(pool[source]) / max(eligible_total, 1),
                     "take_rate": items / max(int(pool[source]), 1)})
    rows.sort(key=lambda row: (-row["items"], row["dataset"]))
    report = {
        "policy": {"max_source_share": max_source_share, "min_source_share": min_source_share,
                   "min_source_items": int(min_source_items),
                   "target_items": plan["target"], "cap_items": cap_items, "floor_items": plan["floor"],
                   "cap_policy": plan["cap_policy"], "feasible_bound": plan["feasible_bound"],
                   "cap_enforced": hard_cap is not None,
                   "bound_share": cap_items / max(total_reserved, 1),
                   "eligible_sources": plan["eligible_sources"],
                   "eligible_items": eligible_total, "pool_total": plan["pool_total"]},
        "excluded_public_groups": excluded_groups, "excluded_public_items": excluded_items,
        "content_overlap": {"excluded_groups": len(overlapped), **overlap_stats},
        "rows": rows,
        "items": total_reserved,
        "max_items": max((row["items"] for row in rows), default=0),
        "min_items": min((row["items"] for row in rows), default=0),
        "max_share": max((row["share"] for row in rows), default=0.0),
        "max_source": max(rows, key=lambda row: (row["items"], row["dataset"]))["dataset"] if rows else None,
        # 上限是否守住：设了硬上限就必须每条都不越界；单来源（不设上限）按定义满足
        "cap_ok": (hard_cap is None) or all(row["items"] <= cap_items for row in rows),
    }
    return reserved, floors, report


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
               min_per_kind: int = DEFAULT_BENCHMARK_MIN_PER_CELL,
               max_source_share: float = DEFAULT_BENCHMARK_MAX_SOURCE_SHARE,
               min_source_share: float = DEFAULT_BENCHMARK_MIN_SOURCE_SHARE,
               min_source_items: int = DEFAULT_BENCHMARK_MIN_SOURCE_ITEMS,
               exclude_ids: frozenset = frozenset()):
    """完整切分；返回 (每条目分区, 组标签, 统计, 保底明细)。

    salt 为 None 表示 public-demo（无盐）跑法：结果确定但与带盐交付件不同。
    """
    labels, group_stats = build_groups(records, use_state=use_state)
    grouped: dict = defaultdict(list)
    for record, label in zip(records, labels):
        grouped[label].append(record)
    records_by_group = dict(grouped)

    reserved, floors, source_report = reserve_benchmark(
        records_by_group, ratios, seed, salt,
        benchmark_langs=benchmark_langs,
        min_per_domain=min_per_domain,
        min_per_lang=min_per_lang,
        min_per_kind=min_per_kind,
        max_source_share=max_source_share,
        min_source_share=min_source_share,
        min_source_items=min_source_items,
        exclude_ids=exclude_ids)
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
             "benchmark_source_policy": source_report,
             "salted": salt is not None,
             "benchmark_langs": sorted(benchmark_langs) if benchmark_langs else None}
    return split_of_item, labels, stats, floors


# ---------------------------------------------------------------- 语言政策与补充集

def lang_coverage_gaps(records, *, benchmark_langs=None, exclusions=None) -> dict:
    """语料里每种语言都必须**显式**决定进不进 benchmark，否则返回缺口（调用方拒绝切分）。

    exclusions: {lang: 理由}。理由为空视为没有排除——"忘了加白名单"和"有意排除"必须能区分开，
    否则 benchmark 会静默丢掉一整种语言（本轮 zh 就是这么被排除但必须写明理由的）。
    """
    declared = {lang: reason for lang, reason in (exclusions or {}).items() if str(reason).strip()}
    corpus_langs = sorted({record["lang"] for record in records})
    allowed = set(benchmark_langs) if benchmark_langs else set(corpus_langs)
    missing = [lang for lang in corpus_langs if lang not in allowed and lang not in declared]
    conflict = sorted(set(benchmark_langs or ()) & set(declared))
    unknown = sorted(set(declared) - set(corpus_langs))
    return {"corpus_langs": corpus_langs, "benchmark_langs": sorted(allowed),
            "missing": missing, "conflict": conflict, "unknown_exclusions": unknown,
            "exclusions": {lang: declared[lang] for lang in sorted(declared)}}


def load_supplement(path, *, seen_ids: set | None = None) -> tuple:
    """读 train-only 降级补充集；返回 (items, 统计)。

    硬约束（违反直接报错，不静默放过）：
    - 每条都要带 id/domain/lang/questions；
    - 必须**降级**：问题 origin 不能是 source（原生四元组只走正常切分，避免绕过 benchmark 门禁）；
    - id 不能与已切分语料重叠（重叠会让同一条出现在两个分区）。
    """
    source = Path(path)
    if not source.is_file():
        raise SplitError(f"补充集不存在：{source}")
    items: list[dict] = []
    stats = {"path": source.as_posix(), "items": 0, "by_lang": Counter(), "by_domain": Counter(),
             "by_kind": Counter(), "by_origin": Counter(), "sources": Counter()}
    known = seen_ids if seen_ids is not None else set()
    for lineno, item in iter_jsonl(source):
        if not isinstance(item, dict):
            raise SplitError(f"{source}:{lineno} 不是 JSON 对象")
        for field in ("id", "domain", "lang", "questions"):
            if not item.get(field):
                raise SplitError(f"{source}:{lineno} 缺必填字段 {field}")
        item_id = str(item["id"])
        if item_id in known:
            raise SplitError(f"{source}:{lineno} id 与已切分语料重叠：{item_id}"
                             "（补充集必须与切分输入不相交）")
        known.add(item_id)
        origins = {str(q.get("origin") or "taxonomy") for q in item["questions"]
                   if isinstance(q, dict)}
        if "source" in origins:
            raise SplitError(f"{source}:{lineno} 含 origin=source 的原生问题：{item_id}"
                             "（补充集只能是降级派生数据，原生条目必须走正常切分）")
        items.append(item)
        stats["items"] += 1
        stats["by_lang"][str(item["lang"])] += 1
        stats["by_domain"][str(item["domain"])] += 1
        stats["by_origin"][origin_of(item)] += 1
        for kind in sorted({str(q.get("kind")) for q in item["questions"]
                            if isinstance(q, dict) and q.get("kind")}):
            stats["by_kind"][kind] += 1
        for question in item["questions"]:
            if isinstance(question, dict) and question.get("source_key"):
                stats["sources"][str(question["source_key"])] += 1
    if not items:
        raise SplitError(f"补充集为空：{source}")
    return items, stats


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


def replace_with_retry(temporary: Path, path: Path, *, attempts: int = 50,
                       delay: float = 0.1) -> None:
    """os.replace，遇到 Windows 文件占用（PermissionError）就短暂重试。

    并发生成/读取很常见：别人正读着 train.jsonl 时，Windows 上 replace 会抛 WinError 5
    （读者的句柄没带 FILE_SHARE_DELETE）。原子替换本身没问题，需要的是"等读者松手再换"。
    """
    last: PermissionError | None = None
    for _ in range(attempts):
        try:
            os.replace(temporary, path)
            return
        except PermissionError as exc:  # Windows: 目标被其他进程打开
            last = exc
            time.sleep(delay)
    raise last if last is not None else RuntimeError("replace 失败")


def atomic_write_text(path: Path, text: str) -> None:
    """先写同目录临时文件再 os.replace 原子替换。

    并发生成/读取很常见（有人边读四区边等你重跑）：直接覆盖会让读者拿到**半截文件**
    （实测撞到过一行被截断的 JSON）。os.replace 在同一文件系统上是原子的，读者要么看到旧版、
    要么看到新版，不会看到撕裂版。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    replace_with_retry(temporary, path)


def write_jsonl(path: Path, items) -> str:
    text = "".join(_json_line(item) + "\n" for item in items)
    atomic_write_text(path, text)
    return text


def count_bare_line_separators(path: Path) -> int:
    """数产物里裸 U+2028 / U+2029 / U+0085 的字节数（应为 0；测试与报告都用这个口径）。"""
    data = Path(path).read_bytes()
    return sum(data.count(char.encode("utf-8")) for char in _LINE_SEPARATORS)


def write_gz(path: Path, text: str) -> None:
    """mtime=0 写 gzip：同一内容两次压缩逐字节一致；同样走"临时文件 + 原子替换"。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            handle.write(text.encode("utf-8"))
    replace_with_retry(temporary, path)


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


def export_benchmark_dataset(directory: Path, items, sources, *, seed: int, ratios: dict,
                             policy: dict, generation: dict, known_limitations,
                             version: str = "0.3") -> dict:
    """导出可直接上传私有托管的目录：数据 + dataset card + USAGE.md + manifest + verify.py。

    只写聚合信息，不写任何样本内容；卡片/manifest 的文本全部由入参决定，不含时间戳。
    """
    directory.mkdir(parents=True, exist_ok=True)
    text = write_jsonl(directory / "benchmark.jsonl", items)
    write_gz(directory / "benchmark.jsonl.gz", text)
    return package_benchmark.write_package(
        directory, items, version=version, seed=seed, ratios=ratios, policy=policy,
        generation=generation, sources=sources, known_limitations=known_limitations)


# ---------------------------------------------------------------- 报告

#: 逐字节比对范围：4 个分区 + benchmark-dataset 的确定性产物
PRODUCT_FILES = (
    "train.jsonl", "train.jsonl.gz", "test.jsonl", "test.jsonl.gz",
    "validation.jsonl", "validation.jsonl.gz", "benchmark.jsonl", "benchmark.jsonl.gz",
    "benchmark-dataset/README.md", "benchmark-dataset/USAGE.md",
    "benchmark-dataset/benchmark.jsonl", "benchmark-dataset/benchmark.jsonl.gz",
    "benchmark-dataset/manifest.json", "benchmark-dataset/verify.py",
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


def public_needles(items) -> dict:
    """从 benchmark 条目派生公开面必须零命中的两种指纹：条目 id 与正文。

    正文口径取**条目级唯一**的 state 原文（>= 20 字符）。两种口径的理由：
    - 完整条目行一定含它自己的 id，所以"整行 JSON 泄漏"必然先被 id 口径抓到，不必再加一遍
      （而且 1,598 行的交替式正则有 1.6 MB，编译一次要几分钟，属于自找麻烦）；
    - 不取问题 prompt：同一条 taxonomy 模板被成千上万条条目共用（README 也引用模板），
      按模板判命中会把公开文档全部误报，而它指认不出"哪一条在 benchmark 里"。
    """
    ids, texts = [], []
    for item in items:
        ids.append(str(item.get("id") or ""))
        state = str(item.get("state") or "")
        if len(state) >= 20:
            texts.append(state)
    return {"ids": sorted({value for value in ids if value}),
            "texts": sorted({value for value in texts if value})}


def tracked_files(repo_root: Path) -> list[Path]:
    """被 git 跟踪的文件（绝对路径）；不在仓库或缺 git 时返回空表。

    必须用 -z 分隔 + core.quotePath=false：默认的 ls-files 会把非 ASCII 路径转成带引号的
    八进制转义（"\346\233..."），Path 拼出来是**不存在的路径**——审计会把它算进"已扫描"
    但实际一个字节都不读。这个坑是 v5 事故核查时发现的：15 个中文文件名被静默跳过。
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "-c", "core.quotePath=false", "ls-files", "-z"],
            capture_output=True)
    except (OSError, FileNotFoundError):
        return []
    if completed.returncode != 0:
        return []
    return [Path(repo_root) / name.decode("utf-8", "surrogateescape")
            for name in completed.stdout.split(b"\0") if name]


def read_public_bytes(path: Path) -> bytes:
    """读公开文件内容；**.gz 先解压**（泄漏可能只藏在压缩流里，只看压缩字节会漏）。"""
    data = Path(path).read_bytes()
    if Path(path).suffix == ".gz":
        try:
            return gzip.decompress(data)
        except OSError:
            return data
    return data


#: 从公开文件里抓"像条目 id"的 token：id 口径用"抓候选 + 集合求交"，比逐针匹配快得多。
_ID_TOKEN = re.compile(r"db-[A-Za-z0-9][A-Za-z0-9._-]{4,80}")


def _needle_patterns(values, *, chunk: int = 50):
    """把一组针**分块**编译成 str 交替式正则。

    整表编译成一个正则会让 re 的编译器明显变慢；分块后既能保持 C 速扫描，编译又是毫秒级。
    正文（state）针比较长，所以块也开大一点（50），把"块数 × 文件字节数"的扫描总量压下来。
    """
    ordered = sorted({value for value in values if value})
    patterns = []
    for start in range(0, len(ordered), chunk):
        block = ordered[start:start + chunk]
        patterns.append(re.compile("|".join(re.escape(value) for value in block)))
    return patterns


def scan_public_surface(paths, *, ids=(), texts=(), root: Path | None = None) -> list[dict]:
    """扫描给定文件集合，返回命中列表（空表 = 干净）。

    两种口径都查：条目 id（成员指纹，用"抓候选 + 集合求交"）与正文（state 原文，用分块交替式）。
    .gz 先解压再查。
    """
    id_set = {str(value) for value in ids if value}
    text_patterns = _needle_patterns([value for value in texts if len(value) >= 20])
    hits: list[dict] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        data = read_public_bytes(path)
        label = path.as_posix()
        if root is not None:
            try:
                label = path.resolve().relative_to(Path(root).resolve()).as_posix()
            except ValueError:
                label = path.as_posix()
        blob = data.decode("utf-8", "replace")
        if id_set:
            found = id_set.intersection(_ID_TOKEN.findall(blob))
            if found:
                hits.append({"file": label, "kind": "id", "needle": sorted(found)[0][:60]})
        for pattern in text_patterns:
            matched = pattern.search(blob)
            if matched:
                hits.append({"file": label, "kind": "text", "needle": matched.group(0)[:60]})
                break
    return hits


def scan_referenced_ids(root: Path | None, *, skip_paths=(), extra_paths=()) -> dict:
    """扫描公开面（被 git 跟踪的文件），收集其中**出现过的条目 id**。

    用途：把"已经在公开文件里被引用过"的条目排除出 benchmark——公开引用过 = 已泄漏，
    不该再进盲测集。这里只做 id 口径（文档引用条目时一定会带 id；state 正文引用由公开面审计兜底）。
    skip_paths 用于排除**切分后会被整体替换/重新生成**的派生产物（分区目录、target-types 侧挂文件），
    它们的旧内容不代表最终公开面；最终状态由 --audit-public-surface 全量验收。
    """
    skip = {Path(path).resolve() for path in skip_paths}
    files = list(tracked_files(root)) if root is not None else []
    files.extend(Path(path) for path in extra_paths)
    pattern = re.compile(r"db-[A-Za-z0-9][A-Za-z0-9._-]{4,80}")
    referenced: set = set()
    scanned = 0
    for raw in files:
        path = Path(raw)
        if not path.is_file():
            continue
        resolved = path.resolve()
        if any(resolved == parent or parent in resolved.parents for parent in skip):
            continue
        referenced.update(pattern.findall(read_public_bytes(path).decode("utf-8", "replace")))
        scanned += 1
    return {"files": scanned, "referenced_ids": referenced, "skipped": len(files) - scanned}


def load_excluded_ids(path, *, repo_root: Path | None = None) -> dict:
    """读 benchmark **永久排除名单**（一行一个条目 id，# 开头为注释）。

    用于事故轮换：曾经泄漏到公开面的 id 永不进 benchmark。硬要求：名单必须在**仓库外**——
    名单本身记录"哪些条目曾是 benchmark 成员"，进仓库等于把成员身份再公开一次（同盐的处理方式）。
    返回 {"ids": frozenset, "file_sha256", "file", "lines", "unique"}。
    """
    source = Path(path)
    if not source.is_file():
        raise SplitError(f"排除名单不存在：{source}")
    if path_inside(repo_root, source):
        raise SplitError(f"排除名单必须在仓库外（当前在仓库内）：{source}")
    ids: list[str] = []
    for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if not text.startswith("db-"):
            raise SplitError(f"{source}:{lineno} 不像条目 id：{text[:40]!r}")
        ids.append(text)
    unique = sorted(set(ids))
    if not unique:
        raise SplitError(f"排除名单为空：{source}")
    return {"ids": frozenset(unique), "file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "file": source.as_posix(), "lines": len(ids), "unique": len(unique)}


def audit_public_surface(items, *, root: Path | None, extra_paths=(), skip_paths=()) -> dict:
    """公开面审计：所有被跟踪的文件 + 显式附加文件，对 benchmark 的 id 与正文零命中。

    skip_paths 用于排除**本次运行自己正在重写的产物**（分区目录、报告）：审计时看到的还是上一版
    内容，上一版若曾把命中项写进去，就会自己报自己（这个坑真踩过一次）。独立的
    --audit-public-surface 不传 skip，扫的是完整公开面。
    """
    needles = public_needles(items)
    skip = {Path(path).resolve() for path in skip_paths}
    files = list(tracked_files(root)) if root is not None else []
    files.extend(Path(path) for path in extra_paths)
    scanned = []
    for path in files:
        resolved = path.resolve()
        if any(resolved == parent or parent in resolved.parents for parent in skip):
            continue
        scanned.append(path)
    hits = scan_public_surface(scanned, ids=needles["ids"], texts=needles["texts"], root=root)
    return {"files": len(scanned), "ids": len(needles["ids"]), "texts": len(needles["texts"]),
            "hits": hits, "tracked": root is not None, "skipped": len(files) - len(scanned)}


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
                  rerun: dict | None = None, supplements=None, actual_counts=None,
                  origin_counts=None, lang_origin=None, version: str = "v3",
                  command: str | None = None, benchmark_domain_source=None,
                  corpus_domain_source=None) -> str:
    """split-report.md：只有聚合统计，不含任何样本内容。"""
    lines: list[str] = []
    total = len(items)
    supplements = list(supplements or [])
    actual = Counter(actual_counts or counts["items"])
    supplement_total = sum(int(entry["items"]) for entry in supplements)
    group_counts = Counter()
    for split in split_of_item:
        group_counts[split] += 1
    lines.append(f"# 最终切分报告（{version}：6:2:1:1，按请求分组，benchmark 来源均衡）")
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
    lines.append(f"- 切分语料条目总数：{total}；请求组 {stats['groups']['groups']} 个")
    lines.append("- 语料来源：本轮输入是**合并后的主语料**；合并台账（各增量来源、id 前缀、sha256）"
                 "由 data/splits/build_corpus.py 生成并保管在仓外（本报告 §3 只有来源构成聚合）")
    if supplements:
        lines.append(f"- train-only 降级补充：{supplement_total} 条（"
                     + "、".join(f"{entry['path']} {entry['items']} 条" for entry in supplements)
                     + "）；只追加 train，不进 test/validation/benchmark")
    lines.append(f"- 产物条目总数（含补充）：{sum(actual.values())} 条")
    lines.append("- **口径注记（与立项数字的差异）**：立项时写的「25,405 + 51,057 = 76,462」把"
                 "**公开三区产物**（含 3,148 中文补充、不含 benchmark 1,598）当成了切分语料。"
                 "正确口径：切分语料 = 23,855 + 51,057 = **74,912**，产物 = 74,912 + 3,148 = **78,060**"
                 "（差 1,550 = 3,148 − 1,598）。本报告一律按**切分语料**口径统计，产物条数单列。")
    salt_state = "仓外私盐（盐值不记录、不派生进任何公开产物）" if stats.get("salted") \
        else "无盐 public-demo（**不是交付件**；公开脚本+公开种子跑出的就是这一套）"
    lines.append(f"- 保密：本次运行使用 {salt_state}")
    if stats.get("benchmark_langs"):
        lines.append("- benchmark 语言白名单：" + ", ".join(stats["benchmark_langs"])
                     + "（白名单外的语言只进 train/test/validation，且必须显式排除并写明理由）")
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
    lines.append("2. **分层**：按 (domain, lang) 分层；层内组按种子洗牌，其余组按 6:2:1 用"
                 "「目标条数 - 已分配条数」最大缺口贪心分配；benchmark 的来源配额在**每个来源内部**"
                 "再按 (domain, lang) 分层取，保证每个来源的切片仍是它自己的自然分布。")
    lines.append("3. **benchmark 来源均衡（硬约束）**：先按比例算目标条数，再用水位法给每个来源"
                 "分配配额——任一来源占比 ≤ max_source_share（硬上限，交付用 25%），每个来源 ≥ "
                 "max(min_source_share, min_source_items)（占比下限与**绝对条数下限**取大："
                 "语料变大后 5% 会变成几百条，足以把小来源抽干，所以下限用绝对条数）；"
                 "选择时逐组复核硬上限，组粒度最多差一条组。上限不可行（来源数太少）时放宽到"
                 "可行界 1/来源数并如实标注。")
    lines.append("4. **benchmark 保底**：对每个 lang x kind、每个 domain、每个 lang 设下限，"
                 "不足时从其余组整组补足；该类总量不足下限、或被来源上限挡住时在下表标「是」。")
    source_policy = (stats.get("benchmark_source_policy") or {}).get("policy") or {}
    if source_policy:
        lines.append(f"   - 本次配额：目标 {source_policy.get('target_items', '-')} 条；"
                     f"上限折算 {source_policy.get('cap_items', '-')} 条"
                     f"（{'政策上限' if source_policy.get('cap_policy') == 'policy' else '可行界放宽'}）；"
                     f"下限 {source_policy.get('floor_items', '-')} 条；"
                     f"可进 benchmark 的来源 {source_policy.get('eligible_sources', '-')} 个")
    lines.append("5. **确定性**：随机数全部来自 random.Random(\"公开种子|盐token|阶段|…\")（无盐时 token 为"
                 "固定标记 public-demo）；分区内条目按 id 排序，补充集按文件顺序追加在 train 末尾；"
                 "gzip 以 mtime=0 写入 → 同一输入 + 同一私盐重跑逐字节一致。")
    lines.append("6. **默认值防误伤**：--out/--report 没显式给出而目标位置已有交付件时直接拒绝（退出 3），"
                 "想覆盖必须显式给路径或加 --force；裸跑不会把已交付的四区或公开报告换掉。")
    exclusions_stat = stats.get("benchmark_exclusions") or {}
    if exclusions_stat.get("enabled"):
        lines.append(f"7. **公开引用排除（--exclude-public-items）**：扫描被 git 跟踪的**手写公开文件**"
                     f"（{exclusions_stat.get('scan_files', 0)} 个），把其中引用过的条目 id 对应条目"
                     f"整组排除出 benchmark 候选——本轮排除 {exclusions_stat.get('excluded_items', 0)} 条"
                     f"（{exclusions_stat.get('excluded_groups', 0)} 组）。"
                     "「被公开引用过的条目永不进盲测集」由机器保证，不靠人工维护文档。"
                     "派生产物（分区、target-types 侧挂文件）不在扫描范围内，它们切分后会被重新生成。")
    rotation_stat = stats.get("benchmark_exclusions") or {}
    if rotation_stat.get("rotation_enabled"):
        lines.append(f"8. **benchmark 永久排除名单（--benchmark-exclude-ids）**：事故轮换用的显式 id 名单"
                     f"（仓外保管，sha256 {str(rotation_stat.get('rotation_exclude_file_sha256'))[:12]}…），"
                     f"共 {rotation_stat.get('rotation_exclude_ids', 0)} 个 id；这些 id 永久不进 benchmark"
                     f"（其中 {rotation_stat.get('rotation_ids_in_corpus', 0)} 个在语料里）。见 §10.5。")
    lines.append("")
    lines.append("## 2. 分区规模")
    lines.append("")
    lines.append("| 分区 | 切分语料条目 | 占比 | 目标占比 | 请求组 | 产物条目（含补充） |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for split in SPLITS:
        item_count = counts["items"][split]
        lines.append(f"| {split} | {item_count} | {item_count / total:.1%} | {ratios[split]:.0%} "
                     f"| {group_counts[split]} | {actual[split]} |")
    lines.append("")
    lines.append("> **三处刻意的偏离，别当成 bug**：")
    lines.append("> 1. **train 高于 60%**：按裁定只向 train 追加了降级补充集"
                 f"（{supplement_total} 条，origin != source，仅 train）；"
                 f"切分语料 {total} 条 → 产物 {sum(actual.values())} 条。")
    if stats.get("benchmark_langs") and len(stats["benchmark_langs"]) < len(
            set(composition["items_by_lang"])):
        lines.append("> 2. **benchmark 低于 10%**：本轮只允许 "
                     + "/".join(stats["benchmark_langs"]) + " 进 benchmark（排除的语言见第 10 节），"
                     "目标条数是**可进 benchmark 那部分语料**的 10%。")
    else:
        lines.append("> 2. **benchmark 占比**按可进 benchmark 的语料计算（见第 10 节语言政策）。")
    lines.append("> 3. **benchmark 的语言构成与公开三区不同**，因此第 4.4 节 benchmark 一行的"
                 "分层漂移必然偏大；这是刻意的覆盖取舍，不是分层失效。")
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
    corpus_sources = Counter(item_source(item) for item in items)
    bench_rows = {row["dataset"]: row for row in
                  (stats.get("benchmark_source_policy") or {}).get("rows", [])}
    lines.append("### 3.1 语料来源构成（合并后，聚合）")
    lines.append("")
    lines.append("| 来源 dataset | 条目 | 占语料 | 进 benchmark | 占 benchmark |")
    lines.append("|---|---:|---:|---:|---:|")
    for source, count in corpus_sources.most_common():
        row = bench_rows.get(source) or {}
        lines.append(f"| {source} | {count} | {count / max(total, 1):.1%} | "
                     f"{row.get('items', 0)} | {row.get('share', 0):.1%} |")
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
    lines.append("> 本节占比按**切分语料**算：train 列不含追加的 3,148 条降级补充"
                 "（补充的语言/原语/origin 构成见第 11 节）。")
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
    lines.append("## 7. benchmark 来源均衡（硬约束）")
    lines.append("")
    source_report = stats.get("benchmark_source_policy") or {}
    policy = source_report.get("policy") or {}
    rows = source_report.get("rows") or []
    if policy:
        lines.append(f"- 上限：任一来源占 benchmark ≤ **{policy['max_source_share']:.0%}**"
                     f"（本次折算 {policy['cap_items']} 条；策略="
                     f"{'政策上限' if policy.get('cap_policy') == 'policy' else '可行界放宽 1/来源数'}，"
                     f"可行界 {policy.get('feasible_bound', '-')} 条）")
        floor_desc = f"占比下限 {policy['min_source_share']:.0%}"
        if policy.get("min_source_items"):
            floor_desc += f" 与绝对下限 {policy['min_source_items']} 条取大"
        lines.append(f"- 下限：每个来源 ≥ **{floor_desc}** = {policy['floor_items']} 条"
                     "（来源池不足时取全部）")
        lines.append(f"- 实际：{policy.get('eligible_sources', len(rows))} 个来源可进 benchmark；"
                     f"最大来源 {source_report.get('max_source') or '-'} 占 "
                     f"{source_report.get('max_share', 0):.1%}；"
                     f"最小来源 {source_report.get('min_items', 0)} 条；"
                     f"硬上限满足：{'是' if source_report.get('cap_ok') else '否'}")
        lines.append("")
        if rows:
            inverse = 1 / max(policy["max_source_share"], 1e-9)
            at_least = max(2, int(inverse) + (0 if float(inverse).is_integer() else 1))
            lines.append(f"**为什么把上限定在 {policy['max_source_share']:.0%}**：本次有 "
                         f"{len(rows)} 个来源可进 benchmark。{policy['max_source_share']:.0%} 上限意味着"
                         f"单一来源最多 {policy['cap_items']} 条、且数学上至少 {at_least} 个来源才能"
                         "凑满 100%——任一来源都无法单独决定总分，这是「不被单一来源绑架」的下限保证；"
                         "同时它还留出约 15 个百分点的余量给政策调整（契约参考线 40%）。"
                         "下限用「绝对条数」而不是固定占比：语料从 2.4 万涨到 7.5 万后，5% 会从 80 条"
                         "变成 300+ 条，足以把小来源抽干；用绝对条数（本次 100 条）才能同时满足"
                         "「每个来源都有切片」和「不把小来源抽干」。")
            lines.append("")
            pool_total = policy.get("eligible_items") or 0
            if pool_total:
                ordered = sorted(rows, key=lambda row: (-row["pool"], row["dataset"]))
                held_pool = sum(row["pool"] for row in ordered[:2]) / pool_total
                held_bench = sum(row["share"] for row in ordered[:2])
                rest_pool = 1 - held_pool
                rest_bench = 1 - held_bench
                if rest_pool > 0:
                    lines.append(f"**来源覆盖 vs 占比失真（必读）**：语料里最大的两个来源合计占可进"
                                 f"benchmark 语料的 {held_pool:.1%}，但受 {policy['max_source_share']:.0%} "
                                 f"上限约束，它们在 benchmark 里合计只占 {held_bench:.1%}；其余 "
                                 f"{len(rows) - 2} 个来源占语料 {rest_pool:.1%}，却在 benchmark 里占 "
                                 f"{rest_bench:.1%}（放大约 {rest_bench / max(rest_pool, 1e-9):.1f} 倍）。"
                                 "这是「必须覆盖原语料来源」的直接代价：若按自然比例，新涌入的能力语料会把"
                                 "benchmark 的大头占掉。因此 benchmark 的**总分不能当语料自然分布的无偏估计**，"
                                 "必须按来源分层报；要更接近自然比例就放宽 --benchmark-max-source-share。")
                    lines.append("")
    overlap = source_report.get("content_overlap") or {}
    if overlap.get("excluded_groups"):
        lines.append(f"- **内容重叠剔除**：{overlap['excluded_groups']} 个保留组的 state 正文被公开侧"
                     f"某个条目的 state 完整包含（检查 {overlap.get('checked_items', 0)} 个保留条目的 state，"
                     f"含 {overlap.get('fallback_scans', 0)} 个常见词兜底扫描），已整组移出 benchmark——"
                     "正文已公开的条目不能当盲测成员。典型来源：bigbench question_selection 把 cosmos 的"
                     "整段 context 嵌进 state，而旧 Jev 语料里有条目的 state 恰好就是那段 context。")
        lines.append("")
    lines.append("| dataset | revision | license | 条目 | 占 benchmark | 占语料 | 该来源池子 | 取用率 |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")
    balance_rows = {row["dataset"]: row for row in rows}
    for row in stats["sources"]:
        balance = balance_rows.get(row["dataset"], {})
        lines.append(f"| {row['dataset']} | {row['revision']} | {row['license']} | {row['items']} | "
                     f"{balance.get('share', 0):.1%} | {balance.get('pool_share', 0):.1%} | "
                     f"{balance.get('pool', '-')} | {balance.get('take_rate', 0):.1%} |")
    if not rows:
        lines.append("| （本次运行没有来源配额报告） | | | | | | | |")
    lines.append("")
    lines.append("> 取用率 = 该来源进 benchmark 的条数 / 它在这个语言白名单下的全部可用条数。"
                 "「占语料」= 该来源在可进 benchmark 语料里的占比。两者对比可以看出谁被放大、谁被压制。")
    lines.append("")
    bench_cells = Counter(benchmark_domain_source or {})
    pool_cells = Counter(corpus_domain_source or {})
    if bench_cells and pool_cells:
        total_bench = sum(bench_cells.values())
        for domain in sorted({cell[0] for cell in pool_cells}):
            pool_rows = {source: count for (cell_domain, source), count in pool_cells.items()
                         if cell_domain == domain}
            pool_total = sum(pool_rows.values())
            top_source, top_count = max(sorted(pool_rows.items()), key=lambda kv: kv[1]) if pool_rows else ("-", 0)
            have = sum(count for (cell_domain, _source), count in bench_cells.items()
                       if cell_domain == domain)
            if pool_total and top_count / pool_total >= 0.9:
                lines.append(f"- **结构性冲突（必须知道）**：{domain} 在语料里有 {pool_total} 条，其中 "
                             f"{top_count} 条（{top_count / pool_total:.0%}）来自 {top_source}；把该来源压到 "
                             f"上限以内之后，benchmark 的 {domain} 只拿到 {have} 条"
                             f"（{have / max(total_bench, 1):.1%}）。**该域几乎只有一个来源时，"
                             "「来源均衡」与「该域保持自然占比」在数学上不可兼得**："
                             "要来源均衡就接受该域欠采样，要该域自然占比就得放开单一来源上限。请按用途二选一。")
    lines.append("")
    lines.append("## 8. 产物")
    lines.append("")
    for split in SPLITS:
        suffix = "（**内部，勿公开**）" if split == "benchmark" else ""
        extra = f"（含补充 {supplement_total} 条）" if split == "train" and supplement_total else ""
        lines.append(f"- data/splits/{split}.jsonl（+.gz）：{actual[split]} 条{extra}{suffix}")
    lines.append("- data/splits/benchmark-dataset/：可直接上传私有托管的内部 benchmark"
                 "（README.md 数据卡 + USAGE.md + benchmark.jsonl(.gz) + manifest.json + verify.py）")
    lines.append("- data/splits/split-manifest.json：各产物 sha256 与复跑校验结果（机器可读）")
    lines.append("")
    lines.append("## 9. 可复现性（两次运行逐字节一致）")
    lines.append("")
    lines.append(f"- 随机种子：{seed}；同一输入 + 同一种子 + 同一私盐 + **同一份公开面** → "
                 "同一分组、同一分配、同一顺序。")
    if (stats.get("benchmark_exclusions") or {}).get("enabled"):
        lines.append("- 注意：启用 --exclude-public-items 时，「可进 benchmark 的条目集合」还取决于"
                     "**当前被 git 跟踪的手写公开文件**——若在切分之后有人新增/修改了引用条目 id 的文档，"
                     "重跑出来的 benchmark 会随之变化。这是「被公开引用过的条目永不进盲测集」的代价，"
                     "也是每次重切必须重跑公开面审计的原因。")
    if command:
        lines.append(f"- 本次命令（输出路径与盐路径用占位符，实际路径见第 8 节）：`{command}`")
    lines.append("- 分区内条目按 id 排序；gzip 以 mtime=0 写入（gzip 头不含时间戳，否则两次压缩不会逐字节相同）。")
    lines.append("- 输出把裸 U+2028 / U+2029 / U+0085 统一写成 \\uXXXX 转义（无损）：它们在 JSON 里合法，"
                 "但用 str.splitlines() 读会被当成换行、把记录劈开。")
    if rerun:
        state = "**逐字节一致**" if rerun.get("identical") else "**不一致（见 problems）**"
        lines.append(f"- 本次运行额外完整复跑一遍（重新读文件、重新分组、重新分配、重新打包）并写到"
                     f"独立临时目录，比对 {rerun['files']} 个产物文件：{state}。")
        lines.append(f"- 产物树哈希（sha256 over 文件名+文件哈希）：{rerun.get('tree_sha256', '')}")
        lines.append("- 比对范围：" + "、".join(PRODUCT_FILES))
        if rerun.get("problems"):
            lines.append("- 差异：" + "; ".join(rerun["problems"]))
    else:
        lines.append("- 本次运行未启用复跑校验（--no-verify-rerun）。")
    lines.append("")
    lines.append("## 10. 保密：私盐 + 语言政策 + 版本")
    lines.append("")
    lines.append("### 10.1 私盐挡什么、不挡什么（如实披露）")
    lines.append("")
    lines.append("- 交付件的所有随机种子都折进**仓外私盐**文件的 sha256 前 16 位；盐值与盐的哈希都"
                 "不写进任何产物。")
    lines.append("- **私盐挡的是**：用公开脚本 + 公开语料 + 公开种子**直接重跑切分**来复现 benchmark——"
                 "无盐（--public-demo）跑出来的是**另一套**分配。")
    lines.append("- **私盐不挡的是**：重建语料后做减法。公开三区（train/test/validation）是**全量发布**的，"
                 "而本语料 68% 来自公开 HF 数据集 + 公开转换脚本；任何人若能按公开脚本重建出同一份语料，"
                 "就可以用「语料 − 公开三区 = benchmark」直接算出成员身份，**不需要盐、也不需要重跑切分**。"
                 "这条路径在旧语料上就存在，新能力语料（公开来源占比更高、转换参数公开）让它更强。")
    lines.append("- 因此本 benchmark 的定位是「**防止随手复现**」，**不是**「对决心攻击者保密」。"
                 "若要用于真正的盲测/对抗性评测，评测方应另行持有**未公开的额外留出集**（不复用本 benchmark），"
                 "或先把公开三区改成只发抽样/校验和。")
    lines.append("- 护栏（test_split.py 的 SecrecyTest 每次运行都验）：两个不同盐 → benchmark 不同；"
                 "同盐两次 → 完全一致；无盐 public-demo 与交付件不同；盐文件在仓库内 / 无盐且非 demo / "
                 "demo 写到仓库内 → 均拒绝（非零退出）。这些护栏保证的是「没有私盐就分不出交付件」，"
                 "不保证「有语料就能守住成员身份」——见上面第 3 条。")
    lines.append("")
    lines.append("### 10.2 语言政策：每种语言都必须显式声明")
    lines.append("")
    policy_info = stats.get("benchmark_lang_policy") or {}
    if policy_info:
        lines.append("- 切分语料里出现的语言：" + ", ".join(policy_info.get("corpus_langs", [])))
        lines.append("- 允许进 benchmark：" + (", ".join(policy_info.get("benchmark_langs", [])) or "(不限)"))
        exclusions = policy_info.get("exclusions") or {}
        if exclusions:
            lines.append("- **显式排除**（--benchmark-exclude-lang）：")
            for lang, reason in exclusions.items():
                lines.append(f"  - {lang}：{reason}")
        else:
            lines.append("- 显式排除：无")
        if policy_info.get("unknown_exclusions"):
            lines.append("- 注意：排除列表里有多余语言（语料里没有）："
                         + ", ".join(policy_info["unknown_exclusions"]))
    lines.append("- 机制：run() 要求语料里每种语言要么在 --benchmark-lang 里，要么在"
                 "--benchmark-exclude-lang 里带非空理由；漏一种直接拒绝切分（退出 3）。"
                 "所以「benchmark 少了一整种语言」永远是**会报错的显式状态**，不是沉默的事实——"
                 "恢复条件一满足，去掉排除项即可翻回来。")
    lines.append("")
    lines.append("### 10.3 版本：v1/v4 作废，v2 / v3 / v5 不可拼接")
    lines.append("")
    lines.append("| 版本 | 内容 | 状态 |")
    lines.append("|---|---|---|")
    lines.append("| v1 | 公开种子、**无盐**；benchmark 2,389 条（含 zh 789） | **作废**：可用公开脚本 + "
                 "语料 + 种子逐字节重建（benchmark sha256 43937e09a6fdde62…） |")
    lines.append("| v2 | 私盐 + 只允许 en 进 benchmark；benchmark 1,600 条，单一来源占 47.1% | "
                 "已被 v3 取代（benchmark sha256 f5ae670811c33200…） |")
    lines.append("| v3 | 私盐 + en-only + 来源均衡（≤25% 上限 / 5% 下限）；语料 23,855 条；"
                 "benchmark 1,598 条 | 已被 v4 取代 |")
    lines.append("| v4 | 语料合并 51,057 条能力语料 + 私盐 + en-only + 来源均衡 + 公开引用排除；"
                 "benchmark 6,704 条 | **作废**：成员填充概率在提交 b6a4909 里公开过（见 §10.5），"
                 "已轮换（benchmark sha256 9ee0fc30405a59a4…） |")
    lines.append(f"| **v5（本次）** | 在 v4 基础上加**永久排除名单**（1,621 个泄漏 id）+ 同一私盐/种子重切；"
                 f"benchmark {actual['benchmark']} 条 | 现行交付件；哈希见第 9 节与 split-manifest.json |")
    lines.append("")
    lines.append("**v1 / v2 / v3 / v4 / v5 的 benchmark 是五套不同的条目集合，分数不可拼接、不可混用。"
                 "v4（以及更早）一律作废。**")
    lines.append("")
    lines.append("### 10.4 公开面零命中")
    lines.append("")
    lines.append("- 护栏：SecrecyTest 逐个扫描**所有被 git 跟踪的文件**（`.gz` 解压后），"
                 "对 benchmark 的**条目 id** 与**正文**（条目级唯一的 state 原文；完整条目行必然含 id，"
                 "由 id 口径覆盖）两种口径都要求零命中；"
                 "benchmark 分区与 benchmark-dataset/ 都在 .gitignore（benchmark*）。")
    audit = stats.get("public_surface_audit") or {}
    if audit:
        verdict = "零命中" if not audit.get("hits") else f"**{len(audit['hits'])} 处命中**"
        derived_note = (f"（本次运行跳过 {audit.get('skipped', 0)} 个会被本次运行重写/重生成的产物："
                         "四个分区、本报告，及 --derived-skip 指名的 target-types 侧挂件与 jev-probs 交付件）"
                         if audit.get("skipped") else "（本次运行未跳过任何文件）")
        lines.append(f"  - 本次运行内的公开面审计：对被跟踪文件（.gz 解压后）扫描，"
                     f"指纹 {audit.get('ids', 0)} 条 id / {audit.get('texts', 0)} 条正文 → {verdict}"
                     f"{derived_note}。可用 --audit-public-surface 单独复跑（命中则退出 1，并打印文件名）。"
                     "（不记录文件个数：仓库增删文件会让它变化，而重跑一致性要求产物只由输入与盐决定。）")
        lines.append("  - **交付验收口径**：派生件按本版公开三区重新生成后，必须再跑一次**全量**审计"
                     "（不跳过任何文件）并零命中——派生件不重生成就会立刻回流（例如 v4→v5 轮换后，"
                     "旧 v4 的 target-types 与新 benchmark 相交 4,205 个 id，重生成后清零）。"
                     "§10.5 第 4 条是本次交付的最终审计要求。")
        lines.append("  - 为什么要两种口径：文件级检查（有没有被 git 跟踪）挡不住**内容级**泄漏——"
                     "曾经有派生索引文件把 benchmark 的全部 id 列在里面（本身不含答案，但能精确指认成员）；"
                     "压缩流里的泄漏也只有解压后才看得见。")
    lines.append("- 语料、中文答案索引等含 benchmark 正文/答案的文件已移出版本控制（仓外留存）；"
                 "但**删除不改变 git 历史**——zh 的 (group_id → 正确工具) 索引仍在历史里可达，"
                 "这正是 zh 不进 benchmark 的原因（见 10.2 的排除理由）。")
    lines.append("- 本报告、数据卡、manifest 都只含聚合统计；test_split.py 与 test_benchmark_package.py "
                 "有对应断言，benchmark 包 verify.py 另有独立校验。")
    lines.append("")
    rotation_info = stats.get("benchmark_exclusions") or {}
    if rotation_info.get("rotation_enabled"):
        lines.append("### 10.5 事故与轮换：jev-probs 交付件误含 benchmark 成员")
        lines.append("")
        lines.append("2026-10-20 18:57（+08）的提交 b6a4909 把 `datasets/general/data/jev-probs.jsonl.gz`"
                     "（填充概率交付件）作为公开文件提交并推送到远端；20:57 用 amend + force-with-lease "
                     "修正为 c74eebb，**公开窗口约 2 小时**。泄漏版本 **15,223 行 / 14,092 个条目 id**，"
                     "其中 **1,621 个 id 属于当时的 benchmark（v4）**——这些基准条目的 id 与填充概率在"
                     "公开远端可被 fetch。发现于交付前核对（对公开面做 benchmark 交集检查），"
                     "独立复算同为 1,621。")
        lines.append("")
        lines.append("**为什么改历史不够**：该提交在远端公开过一段时间，可能已被 fetch/clone；而本语料"
                     "可从公开 HF 源 + 公开脚本重建，所以「泄漏 id 名单 + 重建语料」就足以还原 benchmark。"
                     "`commit --amend` + `--force-with-lease`（修正提交 "
                     "c74eebb，交付件只保留公开三区、44,460 行、与 v4 benchmark 交集 0）只能覆盖之后的"
                     "抓取，覆盖不了已经发生的。")
        lines.append("")
        lines.append("**处置**：")
        lines.append(f"1. 修正提交：c74eebb 的交付件过滤为只含公开三区条目，远端 HEAD 与 v4 benchmark "
                     f"交集 0（本地复算）。")
        lines.append(f"2. **轮换 benchmark**：把上述 1,621 个 id 写入**仓外**永久排除名单"
                     f"（sha256 {str(rotation_info.get('rotation_exclude_file_sha256'))[:12]}…，名单本身不进仓库，"
                     f"与盐同级保管），用 `--benchmark-exclude-ids` 在同一私盐、同一种子下"
                     f"重切四区；名单 {rotation_info.get('rotation_exclude_ids', 0)} 个 id 中 "
                     f"{rotation_info.get('rotation_ids_in_corpus', 0)} 个在语料里，全部被永久排除出 benchmark。")
        lines.append(f"3. **v4 benchmark 整体作废**：v4 与 v5 的条目集合不同，分数不可拼接、不可混用；"
                     f"v4 的 benchmark sha256 9ee0fc30405a59a4… 只作为事故记录保留。")
        lines.append(f"4. 派生交付件（target-types 侧挂文件、jev-probs）必须按 v5 公开三区重新生成后"
                     f"再做最终公开面审计；本报告 §10.4 的审计结论以**重新生成之后**的全量审计为准。")
        lines.append("")
        lines.append("**护栏为什么没拦住（核查结论）**：")
        lines.append("- SecrecyTest 的扫描口径是 `git ls-files` 列出的文件 × **工作区字节**"
                     "（.gz 解压后），**不是** HEAD 的提交内容。")
        lines.append("- 所以文件一旦 `git add`（进索引、ls-files 立即可见），下一次 check.py"
                     " 就会红。这次漏拦是**流程问题**：add 之后没跑 check.py 就 commit/amend 了，"
                     "不是护栏覆盖不到。")
        lines.append("- 但它暴露了第二个缺口：**磁盘上存在、但还没 git add 的交付件，护栏完全看不见**——"
                     "泄漏版 .gz 在 add 之前就是这个状态，人眼当时也没看。")
        lines.append("- 核查还发现第三个缺口：**tracked_files 用 git ls-files 默认 quotePath，非 ASCII 路径"
                     "被转义成不存在的路径**——15 个中文文件名一直被算进「已扫描」却一个字节都没读。"
                     "已改为 `ls-files -z` + `core.quotePath=false`；"
                     "修复后全量审计真正覆盖全部 348 个被跟踪文件。")
        lines.append("- 结构性修复（不靠人记得）：①**生成器写盘前硬断言**：jev_fill.py 在写 "
                     "jev-probs.jsonl(.gz) 前，用**当前 benchmark.jsonl 的全部 id** 扫待写行，"
                     "命中任一即 SystemExit、不落盘（名单从 data/splits/benchmark.jsonl 现读，不写死）；"
                     "②交付件必须「先按公开三区过滤再生成」，生成后跑 `--audit-public-surface`"
                     " 才允许提交；③护栏再加一条：把 `git status` 里未跟踪的交付件也纳入扫描"
                     "（按扩展名/路径白名单限定），堵掉「add 前不可见」的窗口。")
        lines.append("")
    lines.append("## 11. origin 构成（原生 vs 降级）")
    lines.append("")
    lines.append("| 分区 | origin=source（原生） | origin=taxonomy 等（降级） | 其它/未标 |")
    lines.append("|---|---:|---:|---:|")
    origin_rows = origin_counts or {}
    for split in SPLITS:
        counter = Counter(origin_rows.get(split) or {})
        native = sum(count for origin, count in counter.items() if origin == "source")
        derived = sum(count for origin, count in counter.items()
                      if origin not in ("source", "mixed", "(unknown)"))
        other = sum(counter.values()) - native - derived
        lines.append(f"| {split} | {native} | {derived} | {other} |")
    lines.append("")
    if lang_origin:
        lines.append("| 语言 | origin | 条目 | 落在哪些分区 |")
        lines.append("|---|---|---:|---|")
        for lang in sorted(lang_origin):
            for origin, splits in sorted(lang_origin[lang].items()):
                total_lang = sum(splits.values())
                lines.append(f"| {lang} | {origin} | {total_lang} | "
                             + ", ".join(f"{split} {count}" for split, count in sorted(splits.items())) + " |")
        lines.append("")
    lines.append("- origin=source 是来源原生四元组（A 层，可进 benchmark）；taxonomy 等是降级派生"
                 "（B 层，只进 train）。benchmark 只含 A 层。")
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
    parser.add_argument("--out", type=Path, default=None,
                        help=f"分区输出目录（不写={DEFAULT_OUT}；若该处已有交付件且未显式给出，直接拒绝）")
    parser.add_argument("--report", type=Path, default=None,
                        help=f"切分报告路径（不写={DEFAULT_REPORT}；同上，已有报告时不覆盖）")
    parser.add_argument("--force", action="store_true",
                        help="允许用默认 --out/--report 覆盖已存在的交付件（默认拒绝，避免裸跑误伤）")
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
    parser.add_argument("--benchmark-exclude-lang", action="append", default=None, metavar="LANG=REASON",
                        help="显式把某种语言排除出 benchmark 并写明理由（可重复）。"
                             "语料里每种语言要么可进 benchmark、要么带理由显式排除，否则拒绝切分")
    parser.add_argument("--benchmark-max-source-share", type=float,
                        default=DEFAULT_BENCHMARK_MAX_SOURCE_SHARE,
                        help=f"benchmark 内任一来源的占比硬上限（默认 {DEFAULT_BENCHMARK_MAX_SOURCE_SHARE:g}）")
    parser.add_argument("--benchmark-min-source-share", type=float,
                        default=DEFAULT_BENCHMARK_MIN_SOURCE_SHARE,
                        help=f"benchmark 内每个来源的占比下限（默认 {DEFAULT_BENCHMARK_MIN_SOURCE_SHARE:g}）")
    parser.add_argument("--benchmark-min-source-items", type=int,
                        default=DEFAULT_BENCHMARK_MIN_SOURCE_ITEMS,
                        help="benchmark 内每个来源的**绝对**条目下限（与占比下限取大；默认不限。"
                             "语料变大后用它代替 5% 占比，避免把小来源抽干）")
    parser.add_argument("--exclude-public-items", action="store_true",
                        help="把**已出现在公开文件里**的条目排除出 benchmark（被公开引用过 = 已泄漏）；"
                             "扫描被 git 跟踪的手写文件，跳过 --derived-skip 指名的派生件")
    parser.add_argument("--benchmark-exclude-ids", type=Path, default=None, metavar="PATH",
                        help="benchmark **永久排除名单**（一行一个 id，# 注释；必须在仓库外）。"
                             "用于事故轮换：泄漏过的 id 永不进 benchmark")
    parser.add_argument("--derived-skip", action="append", default=None, metavar="PATH",
                        help="切分后会整体替换/重新生成的派生产物（可重复）：公开引用扫描与公开面审计都"
                             "跳过它（交付时用它跳过 target-types 侧挂文件，切分后另行重生成）")
    parser.add_argument("--train-supplement", action="append", default=None, metavar="PATH",
                        help=f"train-only 降级补充集（可重复；**默认不追加**。交付命令显式传 "
                             f"{DEFAULT_TRAIN_SUPPLEMENT}）。只追加 train，不进 test/validation/benchmark")
    parser.add_argument("--dry-run", action="store_true", help="只算不写（检查输入与比例）")
    parser.add_argument("--audit-public-surface", action="store_true",
                        help="只做公开面审计：--out 里的 benchmark.jsonl 对**所有被 git 跟踪的文件**"
                             "（.gz 解压后）的 id 与正文必须零命中；命中则退出 1")
    parser.add_argument("--audit-extra", action="append", default=None, metavar="PATH",
                        help="审计时额外扫描的文件（可重复；用于验证护栏本身会响）")
    args = parser.parse_args(argv)

    ratios = dict(DEFAULT_RATIOS)
    if args.ratios:
        try:
            ratios = _parse_ratios(args.ratios)
        except ValueError as exc:
            print(f"参数错误：--ratios {exc}", file=sys.stderr)
            return 2

    # --benchmark-exclude-lang LANG=理由 → {lang: 理由}
    exclusions: dict = {}
    for raw in args.benchmark_exclude_lang or []:
        lang, _, reason = str(raw).partition("=")
        lang, reason = lang.strip(), reason.strip()
        if not lang or not reason:
            print(f"参数错误：--benchmark-exclude-lang 需要 LANG=理由，收到 {raw!r}", file=sys.stderr)
            return 2
        exclusions[lang] = reason
    if args.benchmark_max_source_share < 0 or args.benchmark_min_source_share < 0:
        print("参数错误：来源占比上下限不能为负", file=sys.stderr)
        return 2
    if args.benchmark_max_source_share and \
            args.benchmark_min_source_share > args.benchmark_max_source_share:
        print("参数错误：--benchmark-min-source-share 不能大于 --benchmark-max-source-share",
              file=sys.stderr)
        return 2
    if args.benchmark_min_source_items < 0:
        print("参数错误：--benchmark-min-source-items 不能为负", file=sys.stderr)
        return 2
    derived_skip_paths = [Path(path) for path in (args.derived_skip or [])]

    # ---- 公开面审计模式：不切分、不写任何文件 ----
    if args.audit_public_surface:
        repo = git_repo_root(Path(__file__).resolve().parent)
        audit_dir = Path(args.out) if args.out is not None else DEFAULT_OUT
        bench_path = audit_dir / "benchmark.jsonl"
        if not bench_path.is_file():
            print(f"环境不可用：{bench_path} 不存在（审计需要已生成的 benchmark.jsonl）", file=sys.stderr)
            return 2
        try:
            audit_items = [row for _lineno, row in iter_jsonl(bench_path)]
        except SplitError as exc:
            print(f"环境不可用：{exc}", file=sys.stderr)
            return 2
        report = audit_public_surface(audit_items, root=repo, extra_paths=args.audit_extra or [],
                                      skip_paths=derived_skip_paths)
        print(f"公开面审计：被 git 跟踪文件 {report['files']} 个（.gz 已解压后扫描）；"
              f"指纹：id {report['ids']} 条 / 正文 {report['texts']} 条")
        if report["hits"]:
            print(f"结论：失败——{len(report['hits'])} 处命中（benchmark 成员出现在公开面）",
                  file=sys.stderr)
            for hit in report["hits"][:20]:
                print(f"  [NG] {hit['file']} 命中 benchmark {hit['kind']}：{hit['needle'][:50]}",
                      file=sys.stderr)
            return 1
        print("结论：全部通过（公开面对 benchmark 的 id 与正文零命中）")
        return 0

    # ---- 默认值防误伤：没显式给 --out/--report 时，绝不覆盖已存在的交付件 ----
    out_dir = Path(args.out) if args.out is not None else DEFAULT_OUT
    report_path = Path(args.report) if args.report is not None else DEFAULT_REPORT
    delivered = []
    if args.out is None and (out_dir / "split-manifest.json").is_file():
        delivered.append(f"{out_dir}/split-manifest.json（--out 未显式给出）")
    if args.report is None and report_path.is_file():
        delivered.append(f"{report_path}（--report 未显式给出）")
    if delivered and not args.force and not args.dry_run:
        print("拒绝切分：默认输出位置上已有交付件，裸跑不覆盖。", file=sys.stderr)
        for entry in delivered:
            print(f"  - {entry}", file=sys.stderr)
        print("要重新生成请显式写 --out / --report 指向目标，或确认要覆盖时加 --force。",
              file=sys.stderr)
        return 3

    # ---- 补充集：只在显式给出时追加（默认不追加，避免合成语料/探索跑被真实补充集污染） ----
    supplement_paths = [Path(spec) for spec in (args.train_supplement or [])
                        if str(spec).strip().lower() != "none"]

    required_langs = tuple(args.require_group_id_lang) if args.require_group_id_lang else ("zh",)
    ignored_inputs: list = []
    repo_root = git_repo_root(Path(__file__).resolve().parent)

    # ---- 公开引用排除：被公开文件引用过的条目永不进 benchmark ----
    # 扫描对象是**手写公开文件**；产物（本次输出 + 交付位上的分区/报告）与派生件不参与，
    # 否则"同参数但 --out 不同"会扫到不同的产物、选出不同的 benchmark（这会让重跑不一致）。
    # 注意：本仓库的 git 根是工作目录的**上一级**（NaturalDAO/ 下才是 PoL-Governance/），
    # 所以 canonical 产物路径必须按 CWD 解析（与 --out 默认值的约定一致），不能用 repo_root 拼。
    product_skip = [Path(DEFAULT_OUT).resolve(), Path(DEFAULT_REPORT).resolve(),
                    out_dir, report_path] + derived_skip_paths
    referenced = {"files": 0, "referenced_ids": set(), "skipped": 0}
    if args.exclude_public_items:
        referenced = scan_referenced_ids(repo_root, extra_paths=args.audit_extra or [],
                                         skip_paths=product_skip)
        print(f"公开引用扫描：{referenced['files']} 个手写公开文件，"
              f"引用过 {len(referenced['referenced_ids'])} 个条目 id（这些条目排除出 benchmark；"
              f"跳过派生件 {referenced['skipped']} 个）")

    # ---- benchmark 永久排除名单（事故轮换）：泄漏过的 id 永不进 benchmark ----
    rotation = {"enabled": False, "ids": frozenset(), "file_sha256": None,
                "lines": 0, "unique": 0, "path": None}
    if args.benchmark_exclude_ids is not None:
        try:
            loaded = load_excluded_ids(args.benchmark_exclude_ids, repo_root=repo_root)
        except SplitError as exc:
            print(f"拒绝切分：{exc}", file=sys.stderr)
            return 3
        rotation = {"enabled": True, "ids": loaded["ids"],
                    "file_sha256": loaded["file_sha256"], "lines": loaded["lines"],
                    "unique": loaded["unique"], "path": loaded["file"]}
        print(f"benchmark 永久排除名单：{loaded['unique']} 个 id（名单 sha256 "
              f"{loaded['file_sha256'][:12]}…，仓库外保管）")

    # ---- 保密门禁：交付件必须带仓外私盐（--salt-file 优先，其次环境变量，盐必须在仓库外） ----
    salt_file = args.salt_file if args.salt_file is not None else os.environ.get(SALT_ENV) or None
    salt = None
    if salt_file is not None:
        try:
            salt = read_salt(salt_file, repo_root=repo_root)
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
        for label, path in (("--out", out_dir), ("--report", report_path)):
            if path_inside(repo_root, path):
                print(f"拒绝切分：--public-demo 的 {label} 必须写在仓库外（当前 {path} 在仓库内）。",
                      file=sys.stderr)
                return 3
    if salt is None and args.dry_run:
        print("提示：dry-run 无盐，结果与交付件不同（仅用于检查输入与比例）。", file=sys.stderr)

    def pipeline():
        """一次完整流水线：读 → 分组/门禁 → 切分 → 追加补充 → 派生统计（复跑校验会再调一次）。"""
        items_, records_, load_ = load_records(paths, allow_duplicates=args.allow_duplicates)
        gaps_ = group_id_gaps(records_, required_langs=required_langs)
        lang_policy_ = lang_coverage_gaps(records_, benchmark_langs=args.benchmark_lang,
                                          exclusions=exclusions)
        splits_, labels_, stats_, _ = assign_all(
            records_, ratios=ratios, seed=args.seed, salt=salt,
            benchmark_langs=tuple(args.benchmark_lang) if args.benchmark_lang else None,
            use_state=not args.no_state_grouping,
            min_per_domain=args.benchmark_min_per_domain,
            min_per_lang=args.benchmark_min_per_lang,
            min_per_kind=args.benchmark_min_per_kind,
            max_source_share=args.benchmark_max_source_share,
            min_source_share=args.benchmark_min_source_share,
            min_source_items=args.benchmark_min_source_items,
            exclude_ids=frozenset(referenced["referenced_ids"]) | rotation["ids"])
        leaked_in_corpus = sum(1 for record in records_ if record["id"] in rotation["ids"])             if rotation["enabled"] else 0
        stats_["benchmark_exclusions"] = {
            "public_referenced_ids": len(referenced["referenced_ids"]),
            "scan_files": referenced["files"], "scan_skipped": referenced["skipped"],
            "excluded_groups": (stats_.get("benchmark_source_policy") or {}).get(
                "excluded_public_groups", 0),
            "excluded_items": (stats_.get("benchmark_source_policy") or {}).get(
                "excluded_public_items", 0),
            "enabled": bool(args.exclude_public_items),
            "rotation_enabled": rotation["enabled"],
            "rotation_exclude_ids": rotation["unique"],
            "rotation_exclude_file_sha256": rotation["file_sha256"],
            "rotation_ids_in_corpus": leaked_in_corpus,
        }
        stats_["group_id_gate"] = {
            "required_langs": list(required_langs),
            "missing": gaps_["total"],
            "skipped": bool(args.allow_missing_group_id and gaps_["total"]),
        }
        stats_["benchmark_lang_policy"] = lang_policy_
        stats_["input"] = load_
        stats_["input"]["ignored"] = ignored_inputs
        leak_ = leak_report(records_, labels_, splits_, items_)
        split_items_ = {split: [] for split in SPLITS}
        for item, split in zip(items_, splits_):
            split_items_[split].append(item)
        for split in SPLITS:
            split_items_[split].sort(key=lambda item: str(item.get("id")))
        # train-only 降级补充：整批追加在 train 末尾（其它三区一个字节都不动）
        supplements_, supplement_items_ = [], []
        known_ids = {str(item["id"]) for item in items_}
        for supplement_path in supplement_paths:
            sup_items, sup_stats = load_supplement(supplement_path, seen_ids=known_ids)
            supplements_.append(sup_stats)
            supplement_items_.extend(sup_items)
        split_items_["train"].extend(supplement_items_)
        counts_ = {dimension: defaultdict(Counter) for dimension in ("lang", "domain", "kind")}
        counts_["items"] = Counter()
        for record, split in zip(records_, splits_):
            counts_["items"][split] += 1
            counts_["lang"][record["lang"]][split] += 1
            counts_["domain"][record["domain"]][split] += 1
            for kind in record["kinds"]:
                counts_["kind"][kind][split] += 1
        actual_counts_ = Counter({split: len(split_items_[split]) for split in SPLITS})
        origin_counts_ = {split: Counter() for split in SPLITS}
        lang_origin_: dict = {}
        for split in SPLITS:
            for item in split_items_[split]:
                origin = origin_of(item)
                origin_counts_[split][origin] += 1
                lang_origin_.setdefault(str(item.get("lang")), {}).setdefault(origin, Counter())[split] += 1
        stats_["supplements"] = supplements_
        stats_["sources"] = source_summary(split_items_["benchmark"])
        benchmark_groups_ = len({label for label, split in zip(labels_, splits_) if split == "benchmark"})
        return {"items": items_, "records": records_, "splits": splits_, "labels": labels_,
                "stats": stats_, "gaps": gaps_, "leaks": leak_, "split_items": split_items_,
                "counts": counts_, "actual_counts": actual_counts_, "origin_counts": origin_counts_,
                "lang_origin": lang_origin_, "supplements": supplements_,
                "benchmark_groups": benchmark_groups_}

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

    lang_policy = first["stats"].get("benchmark_lang_policy") or {}
    if lang_policy.get("missing") or lang_policy.get("conflict"):
        print("拒绝切分：benchmark 的语言覆盖必须**显式**声明（不能静默丢掉一整种语言）。",
              file=sys.stderr)
        for lang in lang_policy.get("missing", []):
            print(f"  - 语料里有 {lang}，但既不在 --benchmark-lang 里，也没有 "
                  f"--benchmark-exclude-lang {lang}=理由", file=sys.stderr)
        for lang in lang_policy.get("conflict", []):
            print(f"  - {lang} 既在 --benchmark-lang 里又被显式排除，二者只能选一个", file=sys.stderr)
        print("请二选一：允许它进 benchmark，或用 --benchmark-exclude-lang LANG=理由 说明为什么排除。",
              file=sys.stderr)
        return 3

    leaks = first["leaks"]
    stats = first["stats"]
    counts = first["counts"]
    actual = first["actual_counts"]
    # 跳过集必须与 --out 无关：否则"同参数不同输出目录"会扫到不同文件数、报告文字不一致
    # （canonical 产物位按 CWD 解析，见前面 product_skip 的注释）。
    audit = audit_public_surface(first["split_items"]["benchmark"], root=repo_root,
                                 extra_paths=args.audit_extra or [],
                                 skip_paths=product_skip)
    stats["public_surface_audit"] = audit
    print(f"公开面审计：被 git 跟踪文件 {audit['files']} 个（.gz 已解压后扫描）；"
          f"id 指纹 {audit['ids']} 条 / 正文指纹 {audit['texts']} 条；命中 {len(audit['hits'])}")
    for hit in audit["hits"][:10]:
        print(f"  [NG] {hit['file']} 命中 benchmark {hit['kind']}：{hit['needle'][:40]}", file=sys.stderr)
    # 命中只对**交付件**（带私盐那次）算失败：无盐 public-demo 是另一套分配，命中属正常现象。
    audit_ok = (not audit["hits"]) or salt is None
    if audit["hits"] and salt is None:
        print("  注：本次是无盐 public-demo，不是交付件；命中只作观察，不影响退出码。", file=sys.stderr)
    source_report = stats.get("benchmark_source_policy") or {}
    print(f"输入 {len(paths)} 个文件 / {len(first['items'])} 条 / {stats['groups']['groups']} 组；"
          + "，".join(f"{split}={counts['items'][split]}" for split in SPLITS))
    if first["supplements"]:
        print("train-only 补充：" + "，".join(f"{entry['path']}={entry['items']} 条"
                                              for entry in first["supplements"])
              + f"（产物 train={actual['train']} 条）")
    print(f"泄漏检查：跨区组 {leaks['groups_multi_split']}，跨区 state {leaks['states_multi_split']}，"
          f"跨区 id {leaks['ids_multi_split']}")
    overlap_stat = source_report.get("content_overlap") or {}
    if overlap_stat.get("excluded_groups"):
        print(f"benchmark 内容重叠剔除：{overlap_stat['excluded_groups']} 组（state 正文被公开侧包含）")
    print(f"benchmark 来源均衡：{len(source_report.get('rows') or [])} 个来源；"
          f"上限 {args.benchmark_max_source_share:.0%}"
          f"（折算 {source_report.get('policy', {}).get('cap_items', '-')} 条），"
          f"下限 max({args.benchmark_min_source_share:.0%}, {args.benchmark_min_source_items} 条) = "
          f"{source_report.get('policy', {}).get('floor_items', '-')} 条；"
          f"最大来源 {source_report.get('max_source')} 占 {source_report.get('max_share', 0):.1%}，"
          f"硬上限{'满足' if source_report.get('cap_ok') else '**不满足**'}")
    exclusions_stat = stats.get("benchmark_exclusions") or {}
    if rotation["enabled"]:
        print(f"benchmark 轮换排除：名单 {exclusions_stat.get('rotation_exclude_ids', 0)} 个 id，"
              f"其中 {exclusions_stat.get('rotation_ids_in_corpus', 0)} 个在语料里；"
              f"与公开引用排除合计 {exclusions_stat.get('excluded_items', 0)} 条"
              f"（{exclusions_stat.get('excluded_groups', 0)} 组）排除出候选")
    print("benchmark 语言政策：" + "可进=" + (",".join(lang_policy.get("benchmark_langs", [])) or "不限")
          + "；显式排除=" + (",".join(lang_policy.get("exclusions", {})) or "无"))
    if args.dry_run:
        print("dry-run：未写任何文件")
        return 0 if leaks["problem_count"] == 0 else 1

    def package_meta(result):
        """打包元数据：全部来自本次运行结果；只有聚合统计，不含样本内容。"""
        input_digests = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in paths}
        stats_ = result["stats"]
        lang_policy_ = stats_.get("benchmark_lang_policy") or {}
        supplement_entries = [{"path": entry["path"], "items": entry["items"],
                               "by_lang": dict(entry["by_lang"]), "by_origin": dict(entry["by_origin"])}
                              for entry in result["supplements"]]
        generation_ = {
            "generator": "datasets/general/data/splits/split.py（切分）+ "
                         "datasets/general/data/splits/package_benchmark.py（打包）",
            "seed_public": args.seed,
            "salt_note": ("仓外私盐（盐值与其哈希都不记录、不派生进任何产物）；"
                          "只凭公开脚本 + 公开种子得到的是另一套分配"
                          if salt is not None else
                          "无盐 public-demo 运行，**不是交付件**"),
            "benchmark_lang_policy": {"benchmark_langs": lang_policy_.get("benchmark_langs", []),
                                      "exclusions": lang_policy_.get("exclusions", {})},
            "algorithm": "并查集按请求分组（显式分组键 + 归一化 state）→ 按 (domain, lang) 分层 → "
                         "公开引用条目排除出 benchmark → benchmark 按来源水位配额取"
                         "（占比上限 / 绝对下限，逐组复核）→ lang x kind / domain / lang 保底补齐 → "
                         "分区内按 id 排序；gzip mtime=0",
            "input": {"path": "、".join(path.as_posix() for path in paths),
                      "items": len(result["items"]), "sha256": input_digests},
            "split_products": {split: int(result["counts"]["items"][split]) for split in SPLITS},
            "products_with_supplement": {split: int(result["actual_counts"][split]) for split in SPLITS},
            "leak_checks": {"groups_multi_split": result["leaks"]["groups_multi_split"],
                            "states_multi_split": result["leaks"]["states_multi_split"],
                            "ids_multi_split": result["leaks"]["ids_multi_split"]},
            "source_balance_constraint": {
                "max_source_share": args.benchmark_max_source_share,
                "min_source_share": args.benchmark_min_source_share,
                "min_source_items": args.benchmark_min_source_items,
                "floor_items": (source_report.get("policy") or {}).get("floor_items"),
                "eligible_sources": len(source_report.get("rows") or []),
                "actual_max_share": source_report.get("max_share"),
                "actual_max_source": source_report.get("max_source"),
                "actual_min_items": source_report.get("min_items")},
            "content_overlap_exclusion": {
                "excluded_groups": (source_report.get("content_overlap") or {}).get("excluded_groups", 0),
                "note": "state 正文被公开侧条目完整包含的保留组整组移出 benchmark（正文已公开）。"},
            "benchmark_rotation": {
                "enabled": bool((stats_.get("benchmark_exclusions") or {}).get("rotation_enabled")),
                "exclude_ids": (stats_.get("benchmark_exclusions") or {}).get("rotation_exclude_ids", 0),
                "exclude_file_sha256": (stats_.get("benchmark_exclusions") or {}).get(
                    "rotation_exclude_file_sha256"),
                "ids_in_corpus": (stats_.get("benchmark_exclusions") or {}).get(
                    "rotation_ids_in_corpus", 0),
                "supersedes_version": "0.4",
                "reason": "v4 benchmark 成员的填充概率曾在公开 git 远端暴露（提交 b6a4909，约 2 小时），"
                          "该批 id 已永久排除；v4 benchmark 作废，v5 与 v4 分数不可拼接。",
            },
            "public_reference_exclusion": {
                "enabled": bool(args.exclude_public_items),
                "excluded_items": (stats_.get("benchmark_exclusions") or {}).get("excluded_items", 0),
                "note": "已出现在公开文件（README/fixtures/文档）里的条目被排除出 benchmark："
                        "被公开引用过的条目永不进盲测集。"},
            "train_supplements": supplement_entries,
            "train_note": (f"train 在切分语料 {len(result['items'])} 条之外另含 "
                           f"{sum(entry['items'] for entry in result['supplements'])} 条降级补充"
                           "（origin != source，benchmark_eligible=false，仅 train）"
                           if result["supplements"] else "本次未追加补充集"),
        }
        limitations_ = []
        constraints_ = source_report.get("policy") or {}
        if constraints_:
            limitations_.append(
                f"benchmark 内最大来源 {source_report.get('max_source')} 占 "
                f"{source_report.get('max_share', 0):.1%}（上限 "
                f"{constraints_.get('max_source_share', 0):.0%} = {constraints_.get('cap_items', '-')} 条；"
                f"策略 {constraints_.get('cap_policy')}），单一来源已不占主导。")
        for lang, reason in (lang_policy_.get("exclusions") or {}).items():
            limitations_.append(f"**{lang} 不进 benchmark**：{reason}")
        rows_ = source_report.get("rows") or []
        eligible_total_ = (source_report.get("policy") or {}).get("eligible_items") or 0
        if len(rows_) >= 3 and eligible_total_:
            ordered_ = sorted(rows_, key=lambda row: (-row["pool"], row["dataset"]))
            held_pool = sum(row["pool"] for row in ordered_[:2]) / eligible_total_
            held_bench = sum(row["share"] for row in ordered_[:2])
            limitations_.append(
                f"来源覆盖率与语料占比不同：语料里最大的两个来源合计占 {held_pool:.1%}，"
                f"受 {args.benchmark_max_source_share:.0%} 上限约束在 benchmark 里合计只占 "
                f"{held_bench:.1%}；其余 {len(rows_) - 2} 个来源因此在 benchmark 里被放大约 "
                f"{(1 - held_bench) / max(1 - held_pool, 1e-9):.1f} 倍。这是「覆盖全部原来源」的代价，"
                "总分不能当语料自然分布的无偏估计。")
        if args.exclude_public_items:
            limitations_.append(
                f"已从 benchmark 排除 {(stats_.get('benchmark_exclusions') or {}).get('excluded_items', 0)} 条"
                "被公开文件引用过的条目（公开引用 = 已泄漏，不能进盲测集）。")
        overlap_groups_ = (source_report.get("content_overlap") or {}).get("excluded_groups", 0)
        if (stats_.get("benchmark_exclusions") or {}).get("rotation_enabled"):
            limitations_.append(
                "**本包为 v5（轮换版）**：v4 曾有 "
                f"{(stats_.get('benchmark_exclusions') or {}).get('rotation_exclude_ids', 0)} 个成员 id 的"
                "填充概率在公开 git 远端暴露约 2 小时，这批 id 已永久排除，v4 benchmark 作废；"
                "v5 与 v4 的分数不可拼接、不可混用。")
        if overlap_groups_:
            limitations_.append(
                f"已从 benchmark 整组剔除 {overlap_groups_} 个「内容重叠」组：它们的 state 正文被公开侧"
                "某个条目的 state 完整包含（例如 bigbench question_selection 嵌了 cosmos 的 context，"
                "而旧 Jev 语料里恰有 state 等于该 context 的条目）。")
        domains = sorted({item["domain"] for item in result["split_items"]["benchmark"]})
        limitations_.append("benchmark 覆盖的域：" + "、".join(domains)
                            + "；语料里其它域没有条目。")
        limitations_.append(f"benchmark {len(result['split_items']['benchmark'])} 条：适合版本对比，"
                            "不适合解读小差异。")
        if result["supplements"]:
            limitations_.append("train 里的降级补充（origin != source、benchmark_eligible=false）"
                                "不得进入本包。")
        limitations_.append("部分来源是教师蒸馏（行为先验非真值）；逐来源许可与署名见 manifest.json "
                            "的 sources 字段。")
        # 返回**完整**来源报告（含 policy / rows / max_share 等）：dataset card 要靠它渲染来源均衡表；
        # 只传内层 policy 会让卡片里出现"≤0%""0 个来源"和空表（这个坑刚踩过）。
        return source_report, generation_, limitations_

    def write_all(directory, result):
        """写 4 个分区 + benchmark 包（第一次与复跑校验共用，保证两边口径完全一致）。"""
        policy_, generation_, limitations_ = package_meta(result)
        written_ = write_split_files(directory, result["split_items"])
        package_ = export_benchmark_dataset(
            directory / "benchmark-dataset", result["split_items"]["benchmark"],
            result["stats"]["sources"], seed=args.seed, ratios=ratios, policy=policy_,
            generation=generation_, known_limitations=limitations_, version=PACKAGE_VERSION)
        return written_, package_

    written, package = write_all(out_dir, first)

    rerun = None
    if not args.no_verify_rerun:
        # 复跑校验：完整再跑一遍（重新读文件、重新分组、重新分配、重新打包）并写到独立临时目录，逐字节比对
        with tempfile.TemporaryDirectory(prefix="pol-split-rerun-") as workspace:
            rerun_dir = Path(workspace)
            second = pipeline()
            write_all(rerun_dir, second)
            rerun = compare_dirs(out_dir, rerun_dir)

    # 命令里**不写本次的输出路径**：报告必须与"写到哪里"无关（同一输入 + 同一盐 → 逐字节一致），
    # 路径用占位符，实际交付路径见本报告第 8 节。
    command_parts = ["uv run --no-project --offline python datasets/general/data/splits/split.py",
                     "--out <OUT_DIR>", "--report <REPORT_PATH>",
                     f"--seed {args.seed}",
                     "--salt-file <仓外私盐>" if salt is not None else "--public-demo"]
    if args.benchmark_lang:
        command_parts.append("--benchmark-lang " + " ".join(args.benchmark_lang))
    for lang, reason in exclusions.items():
        command_parts.append(f'--benchmark-exclude-lang "{lang}={reason}"')
    if abs(args.benchmark_max_source_share - DEFAULT_BENCHMARK_MAX_SOURCE_SHARE) > 1e-9:
        command_parts.append(f"--benchmark-max-source-share {args.benchmark_max_source_share:g}")
    if abs(args.benchmark_min_source_share - DEFAULT_BENCHMARK_MIN_SOURCE_SHARE) > 1e-9:
        command_parts.append(f"--benchmark-min-source-share {args.benchmark_min_source_share:g}")
    if args.benchmark_min_source_items != DEFAULT_BENCHMARK_MIN_SOURCE_ITEMS:
        command_parts.append(f"--benchmark-min-source-items {args.benchmark_min_source_items}")
    if args.exclude_public_items:
        command_parts.append("--exclude-public-items")
    if args.benchmark_exclude_ids is not None:
        command_parts.append("--benchmark-exclude-ids <轮换排除名单（仓外）>")
    for derived in derived_skip_paths:
        command_parts.append(f"--derived-skip {derived.as_posix()}")
    for supplement_path in supplement_paths:
        command_parts.append(f"--train-supplement {supplement_path.as_posix()}")
    command_text = " ".join(command_parts)

    composition = composition_summary(first["records"], first["items"])
    benchmark_domain_source = Counter((item["domain"], item_source(item))
                                      for item in first["split_items"]["benchmark"])
    corpus_domain_source = Counter((item["domain"], item_source(item)) for item in first["items"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        report_path,
        render_report(inputs=paths, items=first["items"], records=first["records"],
                      split_of_item=first["splits"], labels=first["labels"], stats=stats, leaks=leaks,
                      seed=args.seed, ratios=ratios, counts=counts, composition=composition,
                      rerun=rerun, supplements=first["supplements"], actual_counts=actual,
                      origin_counts=first["origin_counts"], lang_origin=first["lang_origin"],
                      version=REPORT_VERSION, command=command_text,
                      benchmark_domain_source=benchmark_domain_source,
                      corpus_domain_source=corpus_domain_source))

    manifest = {
        "schema": "pol-split-manifest/0.1",
        "report_version": REPORT_VERSION,
        "package_version": PACKAGE_VERSION,
        "seed": args.seed,
        "ratios": ratios,
        "inputs": [path.as_posix() for path in paths],
        "corpus_items": len(first["items"]),
        "items": sum(actual.values()),
        "counts": {split: int(actual[split]) for split in SPLITS},
        "corpus_counts": {split: counts["items"][split] for split in SPLITS},
        "benchmark_source_policy": {
            "max_source_share": args.benchmark_max_source_share,
            "min_source_share": args.benchmark_min_source_share,
            "min_source_items": args.benchmark_min_source_items,
            **{key: value for key, value in (stats.get("benchmark_source_policy") or {}).items()
               if key != "rows"},
            "rows": (stats.get("benchmark_source_policy") or {}).get("rows", []),
        },
        "benchmark_exclusions": stats.get("benchmark_exclusions") or {},
        "incident": ({
            "id": "jev-probs-benchmark-leak-2026-10-20",
            "leaked_artifact": "datasets/general/data/jev-probs.jsonl.gz",
            "leaked_commit": "b6a4909",
            "fixed_commit": "c74eebb",
            "leaked_artifact_sha256": "e9f02824741353cca13add708fc4359034aaf7ad0d92174a05540a5d6fdbeada",
            "leaked_artifact_rows": 15223,
            "leaked_artifact_ids": 14092,
            "benchmark_intersection": 1621,
            "handling": "amend + force-with-lease 修正交付件；benchmark 轮换：1,621 个 id 写入仓外永久"
                        "排除名单，同一私盐/种子重切；v4 benchmark 作废，v5 与 v4 不可拼接。",
            "exclude_file_sha256": (stats.get("benchmark_exclusions") or {}).get(
                "rotation_exclude_file_sha256"),
        } if (stats.get("benchmark_exclusions") or {}).get("rotation_enabled") else None),
        "benchmark_lang_policy": stats.get("benchmark_lang_policy") or {},
        "corpus_composition": {
            "items": len(first["items"]),
            "by_lang": dict(Counter(record["lang"] for record in first["records"]).most_common()),
            "by_source": dict(Counter(record_source(record) for record in first["records"]).most_common()),
            "by_domain": dict(Counter(record["domain"] for record in first["records"]).most_common()),
        },
        "supplement": [{"path": entry["path"], "items": entry["items"],
                        "by_lang": dict(entry["by_lang"]), "by_origin": dict(entry["by_origin"]),
                        "by_kind": dict(entry["by_kind"]),
                        "scope": "train only（test / validation / benchmark 不得包含）",
                        "benchmark_eligible": False,
                        "note": "切分完成后整批追加到 train 末尾；其余三区不受影响"}
                       for entry in first["supplements"]],
        "salt_policy": {
            "salted": salt is not None,
            "benchmark_langs": sorted(args.benchmark_lang) if args.benchmark_lang else None,
            "note": "交付件使用仓库外私盐；盐值与盐的哈希都不记录、不派生进任何公开产物。"
                    "只凭本 manifest 的公开种子无法复现交付件；无盐跑法（--public-demo）产出的是另一套。"
                    if salt is not None else
                    "本次为无盐 public-demo 运行，不是交付件。",
        },
        # 只记文件名与口径，**不记命中的指纹本身**：把泄漏的 id 写进 manifest 会让 manifest 自己也命中，
        # 下一轮扫描就多出一条假阳性（这个坑真踩过一次）。
        "public_surface_audit": {"ids": audit["ids"], "texts": audit["texts"],
                                 "hit_count": len(audit["hits"]),
                                 "hit_files": sorted({hit["file"] for hit in audit["hits"]}),
                                 "note": "被 git 跟踪的文件（.gz 解压后）对 benchmark 的 id 与正文"
                                         "零命中；--audit-public-surface 可单独复跑。"
                                         "不记录扫描文件数：它随仓库增删变化，会破坏重跑一致性。"},
        "package": {"directory": "benchmark-dataset", "version": PACKAGE_VERSION,
                    "files": ["README.md", "USAGE.md", "benchmark.jsonl", "benchmark.jsonl.gz",
                              "manifest.json", "verify.py"],
                    "verify": "python verify.py（在包目录内运行，退出码 0=通过）"},
        "rerun": None if rerun is None else {"files": rerun["files"], "identical": rerun["identical"],
                                             "tree_sha256": rerun["tree_sha256"]},
        "digests": {} if rerun is None else rerun["digests"],
    }
    atomic_write_text(out_dir / "split-manifest.json",
                      json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    print(f"已写：{out_dir}（4 个分区 + benchmark-dataset + split-manifest.json）、{report_path}")
    for split in SPLITS:
        print(f"  {split}: {written[split]['items']} 条")
    if rerun is not None:
        print(f"复跑校验：{rerun['files']} 个文件逐字节"
              f"{'一致' if rerun['identical'] else '不一致'}，树哈希 {rerun['tree_sha256'][:16]}")
    return 0 if (leaks["problem_count"] == 0 and audit_ok
                 and (rerun is None or rerun["identical"])) else 1


if __name__ == "__main__":
    raise SystemExit(run())
