#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""POL2 score-v2 Release 到 Hugging Face 数据集的导出、清单与离线校验（纯标准库、确定性）。

三个子命令：

    build   把 Release 解压目录原样搬进 HF 数据集布局，生成数据卡、机器清单与 sha256 清单
    verify  离线校验已有导出目录：逐文件 sha256/bytes、多余文件、CHECKSUMS 与 MANIFEST 一致
    stats   打印 MANIFEST 摘要（便于结果卡引用）

导出布局（--out，默认 datasets/pol2/score-v2/hf-export/，已 gitignore）：

    <out>/README.md                 HF 数据集卡（由本脚本生成，不要手改）
    <out>/MANIFEST.json             逐文件 sha256/bytes/行数 + 分组统计 + 版本/许可元数据
    <out>/CHECKSUMS.sha256          sha256sum 格式，覆盖除 MANIFEST/CHECKSUMS 外的全部文件
    <out>/release/                  Release 解压树的逐字节副本（含隐藏文件）
    <out>/samples/                  仓库 datasets/pol2/score-v2/samples/ 的副本（可选）
    <out>/cross-check/full-release.json
                                    仓库 manifests/full-release.json 的副本（若存在）

设计约定：

1. Release 只读：先按 release/CHECKSUMS.sha256 逐项复算，任何一项不一致即 exit 2；
2. 盲测守卫：release/data/** 的文件名（不区分大小写）不得含 blind/sealed/fresh/private/holdout；
3. 逐字节复制，不改 .gitignore/.gitattributes，不打印任何样本内容；
4. 确定性：无时间戳、无绝对路径、无随机数；JSON sort_keys=True / ensure_ascii=False /
   indent=2 / LF；同一输入两次 build 逐字节相同；
5. 先写临时目录再原子替换 --out，失败不留下半成品；不联网、不调用 HF。

用法（仓库根目录执行）：

    python datasets/pol2/export_score_v2_hf.py build \
        --release-dir <Release 解压根> [--out datasets/pol2/score-v2/hf-export] \
        [--samples-dir datasets/pol2/score-v2/samples] [--org NaturalDAO] \
        [--exclude-unassigned-pool] [--exclude-blind-samples] [--json]
    python datasets/pol2/export_score_v2_hf.py verify --dir <导出根> [--json]
    python datasets/pol2/export_score_v2_hf.py stats --dir <导出根>

边界审计（不读取、不打印任何逐例 state/label/ID 内容）：

* 读上游 manifests/score-v2-integrated.json 与 manifests/score-v2-new-units.json，
  按 fresh_blind_families 做族级匹配，统计 unassigned 池里的盲测条目/案例/标签计数；
* 对 samples/specialist-{kev,laya}.jsonl 做“JSON 规范化 sha256 -> 池行号（0-based）”
  映射，找出命中盲测池的样例行位置与计数；general-replay 样例不参与映射；
* 默认（无排除参数）检测到盲测即拒绝构建。传入 --exclude-unassigned-pool 时排除
  未分配池及其索引清单；再传 --exclude-blind-samples 时排除含盲测行的样例文件。

上传由 Lead 执行；本脚本不创建/上传任何 HF 仓库。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCORE_V2 = HERE / "score-v2"
DEFAULT_OUT = SCORE_V2 / "hf-export"
DEFAULT_SAMPLES_DIR = SCORE_V2 / "samples"
FULL_RELEASE_MANIFEST = SCORE_V2 / "manifests" / "full-release.json"

RELEASE_TAG = "pol2-score-v2-v1.0.0"
RELEASE_ASSET_NAME = "pol2-score-v2-data-v1.zip"
RELEASE_ASSET_SHA256 = "8226e4a377298ba52150d970415a84b121ca761bdb70200b06f79b14c1f34428"
RELEASE_ASSET_BYTES = 10105314
PUBLIC_REPO = "pol2-score-v2"
EXPORT_SCHEMA = "pol2-score-v2-hf-export-manifest/1"
CARD_FILE = "README.md"
MANIFEST_FILE = "MANIFEST.json"
CHECKSUMS_FILE = "CHECKSUMS.sha256"
RELEASE_DIRNAME = "release"

GITHUB_REPO = "naturaldao/NaturalDAO"
DEFAULT_ORG = "NaturalDAO"
NL = chr(10)
HEX_DIGITS = frozenset("0123456789abcdef")

# Release 目录必须同时具备的顶层文件与目录（缺一即拒绝构建）。
REQUIRED_RELEASE_FILES = (
    "CHECKSUMS.sha256",
    "README.md",
    "DATASET_CARD.md",
    "SCHEMA.md",
    "HOLDOUT.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "scripts/validate_public_release.py",
)
REQUIRED_RELEASE_DIRS = ("LICENSES", "data", "manifests")

# 盲测/私有数据的文件名关键字（不区分大小写，只扫 release/data/**）。
BLIND_NAME_KEYWORDS = ("blind", "sealed", "fresh", "private", "holdout")

# 发布包排除的盲测集（来自 release/HOLDOUT.md；不含任何逐例内容）。
HOLDOUT_EXCLUSIONS = (
    {"name": "score-v2 sealed blind", "count": 268, "unit": "rows"},
    {"name": "旧专项 blind_test", "count": 687, "unit": "units"},
    {"name": "MRI general blind", "count": 264, "unit": "rows"},
)

# 上游 Release 边界审计：只读清单元数据（family_id / line / label），不读逐例 state。
BOUNDARY_SCHEMA = "pol2-score-v2-release-boundary-audit/1"
INTEGRATED_MANIFEST_REL = "manifests/score-v2-integrated.json"
NEW_UNITS_MANIFEST_REL = "manifests/score-v2-new-units.json"
UNASSIGNED_POOL_RELS = (
    "data/pol2-specialist/score-v2-new-units/kev.jsonl",
    "data/pol2-specialist/score-v2-new-units/laya.jsonl",
)
UNASSIGNED_MANIFEST_RELS = (NEW_UNITS_MANIFEST_REL,)
SPECIALIST_SAMPLE_FORMATS = (("specialist-kev.jsonl", "kev"), ("specialist-laya.jsonl", "laya"))

# 已知 v1.0.0 Release 的口径：UNASSIGNED 池中的 160 行为公开 test 划分（内部评测曾称
# "fresh blind"，已消费一次；owner 2026-11-02 确认按公开 test 上传全量包）。签名不符时仍默认拒绝。
PUBLIC_TEST_SIGNATURE = {
    "unassigned_entries": 875,
    "blind_entries": 144,
    "blind_cases": 88,
    "blind_family_count": 5,
}

# 数据卡与技术文档里固定出现的分组顺序与格式显示名。
GROUP_ORDER = ("pol2-specialist", "general-replay", "mixed-training", "lineage")
FORMAT_ORDER = ("laya", "kev", "none")
FORMAT_LABELS = {"laya": "Laya", "kev": "Kev", "none": "—"}


class ExportError(Exception):
    """Release 不合规、清单不一致或自检失败（命令行 exit 2）。"""


# ---------------------------------------------------------------- 基础 I/O

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=NL) as handle:
        handle.write(text)


def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + NL)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ExportError("JSON 解析失败：" + str(path) + "：" + str(error)) from error


def count_rows(path):
    """JSONL 非空行数；其他类型的文件返回 None。"""
    if not Path(path).name.lower().endswith(".jsonl"):
        return None
    rows = 0
    with open(path, "rb") as handle:
        for raw in handle:
            if raw.strip():
                rows += 1
    return rows


def human_bytes(size):
    if size >= 1024 * 1024:
        return "%.1f MiB" % (size / (1024.0 * 1024.0))
    if size >= 1024:
        return "%.1f KiB" % (size / 1024.0)
    return str(size) + " B"


def num(value):
    return format(int(value), ",")


def tree_digest(root):
    """整棵目录的树哈希（相对路径 + 文件 sha256，包含 MANIFEST/CHECKSUMS）。"""
    root = Path(root)
    pairs = sorted((path.relative_to(root).as_posix(), path)
                   for path in root.rglob("*") if path.is_file())
    lines = [relative + ":" + sha256_file(path) for relative, path in pairs]
    return sha256_bytes(NL.join(lines).encode("utf-8"))


def release_url():
    return "https://github.com/" + GITHUB_REPO + "/releases/tag/" + RELEASE_TAG


def asset_url():
    return ("https://github.com/" + GITHUB_REPO + "/releases/download/"
            + RELEASE_TAG + "/" + RELEASE_ASSET_NAME)


def hf_url(org):
    return "https://huggingface.co/datasets/" + org + "/" + PUBLIC_REPO


def normalize_org(value):
    org = (value or "").strip()
    if not org:
        org = DEFAULT_ORG
    if any(char in org for char in "/\\") or any(char.isspace() for char in org) \
            or org in (".", ".."):
        raise ExportError("--org 参数非法：" + org)
    return org


# ---------------------------------------------------------------- checksums 解析

def parse_checksums(text):
    """解析 sha256sum 文本为 [(路径, sha256)]；路径保留原始写法（可能带 ./ 前缀）。"""
    entries = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        digest = line[:64].lower()
        if len(digest) != 64 or any(char not in HEX_DIGITS for char in digest):
            raise ExportError("CHECKSUMS.sha256 第 " + str(number) + " 行缺少 64 位 sha256")
        marker = line[64:66]
        if marker not in ("  ", " *"):
            raise ExportError("CHECKSUMS.sha256 第 " + str(number) + " 行格式不对（应为 <sha256><两空格><路径>）")
        entries.append((line[66:], digest))
    return entries


def normalize_relpath(value):
    """规范化清单里的相对路径：去掉 ./ 前缀、反斜杠转正斜杠，拒绝绝对路径与 ..。"""
    rel = value.strip().replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    if not rel or rel.startswith("/") or rel in (".", ".."):
        raise ExportError("清单里的路径非法：" + value)
    if any(part in ("", ".", "..") for part in rel.split("/")):
        raise ExportError("清单里的路径非法：" + value)
    return rel


def write_checksums(root, files):
    lines = [entry["sha256"] + "  " + entry["path"]
             for entry in sorted(files, key=lambda item: item["path"])]
    write_text(Path(root) / CHECKSUMS_FILE, NL.join(lines) + NL)


# ---------------------------------------------------------------- Release 校验与守卫

def verify_release_dir(release_dir):
    """按 release/CHECKSUMS.sha256 逐项复算；任何不一致都抛 ExportError。"""
    release_dir = Path(release_dir)
    if not release_dir.is_dir():
        raise ExportError("Release 目录不存在：" + str(release_dir))
    missing = [name for name in REQUIRED_RELEASE_FILES if not (release_dir / name).is_file()]
    missing.extend(name + "/" for name in REQUIRED_RELEASE_DIRS if not (release_dir / name).is_dir())
    if missing:
        raise ExportError("Release 目录缺少必需项：" + "、".join(missing))

    checksums = release_dir / CHECKSUMS_FILE
    try:
        entries = parse_checksums(checksums.read_text(encoding="utf-8"))
    except OSError as error:
        raise ExportError("无法读取 " + CHECKSUMS_FILE + "：" + str(error)) from error
    if not entries:
        raise ExportError(CHECKSUMS_FILE + " 为空：" + str(checksums))

    problems = []
    seen = set()
    total_bytes = 0
    for raw_path, expected in entries:
        relative = normalize_relpath(raw_path)
        if relative in seen:
            raise ExportError(CHECKSUMS_FILE + " 重复登记：" + relative)
        seen.add(relative)
        target = release_dir / relative
        if not target.is_file():
            problems.append("缺文件 " + relative)
            continue
        total_bytes += target.stat().st_size
        if sha256_file(target) != expected:
            problems.append("sha256 不一致 " + relative)
    if problems:
        detail = "；".join(problems[:5])
        if len(problems) > 5:
            detail += "（共 " + str(len(problems)) + " 项）"
        raise ExportError("Release 目录校验失败：" + detail)
    return {"entries": len(entries), "bytes": total_bytes}


def scan_blind_names(release_dir):
    """扫描 release/data/**，返回文件名（含任一路径分量）命中盲测关键字的文件。"""
    data_root = Path(release_dir) / "data"
    hits = []
    for path in sorted(data_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(Path(release_dir))
        lowered = [part.lower() for part in relative.parts]
        if any(keyword in part for part in lowered for keyword in BLIND_NAME_KEYWORDS):
            hits.append(relative.as_posix())
    return hits


# ---------------------------------------------------------------- 上游边界审计

def _sorted_label_counts(raw_counts):
    """把 {label: count} 规范化为按 label 数值升序的字符串键字典。"""
    counts = {}
    if isinstance(raw_counts, dict):
        for label, count in raw_counts.items():
            try:
                key = str(int(label))
                value = int(count)
            except (TypeError, ValueError):
                continue
            counts[key] = value
    return {key: counts[key] for key in sorted(counts, key=int)}


def _boundary_state(release_dir):
    """读取两个上游清单并按 family 匹配；返回审计值（含内部 blind_lines）。

    只读取 family_id / line / label 等清单元数据，不读取或返回逐例 state。
    """
    release_dir = Path(release_dir)
    missing = [relative for relative in (INTEGRATED_MANIFEST_REL, NEW_UNITS_MANIFEST_REL)
               if not (release_dir / relative).is_file()]
    if missing:
        return {
            "applicable": False,
            "reason": "上游边界清单不存在，无法判断 unassigned 池是否含 fresh-blind 单元",
            "missing": missing,
        }

    integrated = read_json(release_dir / INTEGRATED_MANIFEST_REL)
    new_units = read_json(release_dir / NEW_UNITS_MANIFEST_REL)
    if not isinstance(integrated, dict) or not isinstance(new_units, dict):
        raise ExportError("上游边界清单结构异常：期望 JSON 对象")
    families_raw = integrated.get("fresh_blind_families")
    index = new_units.get("index")
    if not isinstance(families_raw, list) or not isinstance(index, list):
        raise ExportError("上游边界清单结构异常：缺少 fresh_blind_families 或 index 列表")

    families = {str(item) for item in families_raw}
    blind_entries = 0
    blind_cases = set()
    blind_labels = {}
    blind_lines = set()
    for position, item in enumerate(index, 1):
        if not isinstance(item, dict):
            raise ExportError("上游边界清单结构异常：index 含非对象条目")
        if str(item.get("family_id")) not in families:
            continue
        line = item.get("line", position)
        if not isinstance(line, int) or isinstance(line, bool):
            raise ExportError("上游边界清单结构异常：盲测条目缺少整数 line")
        blind_entries += 1
        blind_lines.add(line - 1)
        blind_cases.add(str(item.get("case_id")))
        label = item.get("label")
        try:
            label_key = str(int(label))
        except (TypeError, ValueError):
            label_key = "unknown"
        blind_labels[label_key] = blind_labels.get(label_key, 0) + 1

    label_order = sorted(blind_labels, key=lambda value: (value == "unknown",
                                                          int(value) if value != "unknown" else 0))
    blind_label_counts = {key: blind_labels[key] for key in label_order}
    declared = _sorted_label_counts(
        (integrated.get("new_label_counts") or {}).get("fresh_blind") or {})

    return {
        "applicable": True,
        "schema": BOUNDARY_SCHEMA,
        "integrated_manifest": INTEGRATED_MANIFEST_REL,
        "new_units_manifest": NEW_UNITS_MANIFEST_REL,
        "blind_family_count": len(families),
        "unassigned_entries": len(index),
        "blind_entries": blind_entries,
        "blind_cases": len(blind_cases),
        "blind_label_counts": blind_label_counts,
        "blind_label_total": sum(blind_label_counts.values()),
        "declared_blind_label_counts": declared,
        "label_counts_match": declared == blind_label_counts,
        "split_counts": integrated.get("split_counts") or {},
        "blind_lines": sorted(blind_lines),
    }


def audit_release_boundaries(release_dir):
    """审计上游 Release 的 unassigned 池与 fresh-blind 族的重叠（只返回聚合值）。"""
    state = _boundary_state(release_dir)
    return {key: value for key, value in state.items() if key != "blind_lines"}


def public_test_interpretation(boundary_audit):
    """识别已确认的『unassigned 池 = 公开 test 划分』口径；签名不符返回 None。"""
    if not boundary_audit.get("applicable") or not boundary_audit.get("label_counts_match"):
        return None
    for key, expected in PUBLIC_TEST_SIGNATURE.items():
        if boundary_audit.get(key) != expected:
            return None
    split_counts = boundary_audit.get("split_counts") or {}
    assigned_new = sum(int(split_counts.get(key) or 0) for key in
                       ("new_train_rows", "new_validation_rows",
                        "new_calibration_rows", "new_score_dev_rows"))
    test_rows = int(split_counts.get("new_score_blind_rows") or 0)
    return {
        "interpretation": "public_test_split",
        "test_rows_per_format": test_rows or None,
        "assigned_new_rows_per_format": assigned_new or None,
        "note": ("owner 2026-11-02 确认：unassigned 池中的未分配单元是公开 test 划分"
                 "（内部评测曾称 fresh blind，已消费一次），按全量 Release 发布。"),
    }


def normalized_line_sha256(raw):
    """把一行 JSON 规范化（解析后按 key 排序、紧凑输出）再算 sha256。

    规范化让池行与样例行的空白/键序差异不影响匹配；不返回行内容。
    """
    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
    obj = json.loads(text)
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return sha256_bytes(canonical)


def _pool_line_digests(path):
    """JSONL 每行的规范化 sha256 -> 0-based 行号；文件不存在返回 None。"""
    path = Path(path)
    if not path.is_file():
        return None
    mapping = {}
    position = 0
    with open(path, "rb") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            try:
                digest = normalized_line_sha256(raw)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
                position += 1
                continue
            mapping.setdefault(digest, position)
            position += 1
    return mapping


def audit_samples(samples_dir, release_dir):
    """审计 specialist 样例是否来自 unassigned 池，并返回命中盲测的行位置/计数。

    general-replay 样例不参与映射，返回空列表。返回值与异常信息都不含样本内容。
    """
    samples_dir = Path(samples_dir)
    state = _boundary_state(Path(release_dir))
    result = {
        "applicable": False,
        "files": [],
        "general_replay": [],
        "rows": 0,
        "blind_rows": 0,
        "blind_files": [],
        "unmapped_rows": 0,
        "pool_entries": {},
    }
    if not state.get("applicable"):
        result["reason"] = "上游边界清单不存在，无法建立盲测行映射"
        return result
    if not samples_dir.is_dir():
        result["reason"] = "样例目录不存在"
        return result

    pool_paths = {
        "kev": Path(release_dir) / UNASSIGNED_POOL_RELS[0],
        "laya": Path(release_dir) / UNASSIGNED_POOL_RELS[1],
    }
    pools = {}
    for fmt, path in pool_paths.items():
        mapping = _pool_line_digests(path)
        pools[fmt] = mapping
        result["pool_entries"][fmt] = 0 if mapping is None else len(mapping)
    if all(mapping is None for mapping in pools.values()):
        result["reason"] = "unassigned 池文件不存在，无法建立盲测行映射"
        return result
    result["applicable"] = True
    blind_lines = set(state["blind_lines"])

    for name, fmt in SPECIALIST_SAMPLE_FORMATS:
        path = samples_dir / name
        if not path.is_file():
            continue
        mapping = pools.get(fmt) or {}
        rows = 0
        mapped_rows = 0
        unmapped_rows = 0
        blind_positions = []
        with open(path, "rb") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                position = rows
                rows += 1
                try:
                    digest = normalized_line_sha256(raw)
                except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
                    unmapped_rows += 1
                    continue
                line_number = mapping.get(digest)
                if line_number is None:
                    unmapped_rows += 1
                    continue
                mapped_rows += 1
                if line_number in blind_lines:
                    blind_positions.append(position)
        record = {
            "path": "samples/" + name,
            "rows": rows,
            "mapped_rows": mapped_rows,
            "unmapped_rows": unmapped_rows,
            "blind_rows": len(blind_positions),
            "blind_positions": blind_positions,
        }
        result["files"].append(record)
        result["rows"] += rows
        result["unmapped_rows"] += unmapped_rows
        if blind_positions:
            result["blind_files"].append("samples/" + name)
            result["blind_rows"] += len(blind_positions)
    return result


# ---------------------------------------------------------------- 文件登记与分组

def kind_of(relative):
    if relative == CARD_FILE:
        return "card"
    head = relative.split("/", 1)[0]
    if head == RELEASE_DIRNAME:
        return "release"
    if head == "samples":
        return "samples"
    if head == "cross-check":
        return "cross-check"
    raise ExportError("导出目录里出现未知来源的文件：" + relative)


def entry_for(root, relative):
    path = Path(root) / relative
    return {
        "path": relative,
        "kind": kind_of(relative),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": count_rows(path),
    }


def collect_export_files(root):
    """登记导出目录里的全部内容文件（排除根目录的 MANIFEST.json / CHECKSUMS.sha256）。"""
    root = Path(root)
    pairs = sorted((path.relative_to(root).as_posix(), path)
                   for path in root.rglob("*") if path.is_file())
    files = []
    for relative, _path in pairs:
        if relative in (MANIFEST_FILE, CHECKSUMS_FILE):
            continue
        files.append(entry_for(root, relative))
    return files


def classify_data_path(relative):
    """release/data/<组>/... 的分组与格式（laya / kev / none）。"""
    parts = relative.split("/")
    rest = parts[2:]
    dirs = rest[:-1]
    name = rest[-1]
    group = "lineage" if "lineage" in dirs else (dirs[0] if dirs else "data")
    if "laya" in dirs:
        return group, "laya"
    if "kev" in dirs:
        return group, "kev"
    stem = name.rsplit(".", 1)[0].lower()
    if stem == "laya" or stem.startswith("laya-"):
        return group, "laya"
    if stem == "kev" or stem.startswith("kev-"):
        return group, "kev"
    return group, "none"


def build_data_groups(files):
    """按目录分组统计 release/data/**：文件数、字节数、行数与 Laya/Kev 细分。"""
    groups = {}
    for entry in files:
        relative = entry["path"]
        if not relative.startswith(RELEASE_DIRNAME + "/data/"):
            continue
        group, fmt = classify_data_path(relative)
        bucket = groups.setdefault(group, {"files": 0, "jsonl_files": 0, "bytes": 0,
                                           "rows": 0, "by_format": {}})
        fmt_bucket = bucket["by_format"].setdefault(
            fmt, {"files": 0, "jsonl_files": 0, "bytes": 0, "rows": 0})
        is_jsonl = 1 if entry["rows"] is not None else 0
        rows = entry["rows"] or 0
        for target in (bucket, fmt_bucket):
            target["files"] += 1
            target["jsonl_files"] += is_jsonl
            target["bytes"] += entry["bytes"]
            target["rows"] += rows
    return {name: groups[name] for name in sorted(groups)}


# ---------------------------------------------------------------- 数据卡

BT = chr(96)
FENCE = BT * 3


def code(text):
    """行内代码（反引号包裹），避免模板里出现裸反引号。"""
    return BT + text + BT


def render_public_test_card(ctx):
    """生成简洁 HF 数据卡：安全对齐 + PoL2 论文定位（已确认公开 test 口径）。"""
    interpretation = ctx.get("interpretation") or {}
    test_rows = interpretation.get("test_rows_per_format")
    test_line = (num(test_rows) + " 行（Laya/Kev 各一份）" if test_rows
                 else "见 unassigned 池（与 assigned splits 不重复的行）")
    boundary = ctx.get("boundary") or {}
    counts = (boundary.get("audit") or {}).get("counts") or {}
    paper_base = ("https://github.com/naturaldao/NaturalDAO/tree/main/"
                  "PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey")
    paper_pdf = ("https://github.com/naturaldao/NaturalDAO/blob/main/"
                 "PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey/paper/main.pdf")
    pol2_spec = "https://github.com/naturaldao/NaturalDAO/tree/main/PoL"
    lines = []
    add = lines.append

    add("---")
    add("license: other")
    add("license_name: proof-of-love2-and-mit")
    add("license_link: " + ctx["release_url"])
    add("language: [zh]")
    add('pretty_name: "POL2 Score-v2 安全对齐决策数据（研究预发布）"')
    add("size_categories: [10K<n<100K]")
    add("task_categories: [text-classification]")
    add("tags: [safety-alignment, ai-governance, alignment, typed-decisions, jev, pol2, synthetic, research-preview, proof-of-love2]")
    add("---")
    add("")
    add("# POL2 Score-v2 安全对齐决策数据（研究预发布）")
    add("")
    add("这个数据集用来**训练和测试 AI 的“安全判断”能力**：给模型一段中文内容（例如社区发言、")
    add("治理场景），让它在几个选项里选择——该放行、该拦截，还是信息不足无法判断；也可以给风险")
    add("打 0–4 分。模型不写长篇回答，只输出“选哪个 / 打几分”，所以判断过程容易记录、容易人工复核。")
    add("")
    add("数据里的场景和判断标准来自我们的 **PoL2（Proof of Love2）** 治理框架。配套论文研究的是：")
    add("这种“只做选择题”的小模型能否在内容审核里充当第一道过滤器（安全阀），帮人挡掉明显有害内容、")
    add("同时减少误拦。它不是自动裁决器——涉及封禁、处罚等有后果的决定，仍应由人最终确认。")
    add("")
    add("第一次接触可以把它理解成一份**中文安全判断题库**：每题有场景、问题和参考答案，适合微调或评测")
    add("审核类小模型。")
    add("")
    add("## 相关论文与项目")
    add("")
    add("| 内容 | 链接 |")
    add("|---|---|")
    add("| 论文（英文，arXiv 投稿版 PDF）：*Can Typed Decision Models Serve as Automated Safeguards? "
        "A Clause-Level Assessment Against the Proof of Love2 Specification* | " + paper_pdf + " |")
    add("| 论文仓库 / 研究材料（LaTeX 源、审稿记录、证据编码） | " + paper_base + " |")
    add("| PoL2 正文（Proof of Love2 条款） | " + pol2_spec + " |")
    add("| 本数据集 Release | " + ctx["release_url"] + " |")
    add("")
    add("## 数据内容（简要）")
    add("")
    add("每条数据是一道中文场景题：一段 `state`（场景/发言），一个或多个问题（选择 `choice`、"
        "是否以上皆非 `noul`、打分 `score`），以及答案、one-hot 目标或 0–4 评分。"
        "同一批题有 Laya 与 Kev 两种模型格式，**不要当独立证据双计**。")
    add("")
    add("| 划分 | 约定 | 行数（每格式） |")
    add("|---|---|---:|")
    add("| train | `train-m0.jsonl` | " + num(ctx.get("train_m0_rows") or 0) + " |")
    add("| validation | `validation.jsonl` | " + num(ctx.get("validation_rows") or 0) + " |")
    add("| calibration | `calibration.jsonl` | " + num(ctx.get("calibration_rows") or 0) + " |")
    add("| dev | `score-dev.jsonl`（已用于选模型，不是 blind） | " + num(ctx.get("score_dev_rows") or 0) + " |")
    add("| test（公开） | `score-v2-new-units/*.jsonl` 中与上述 split 不重复的行；内部 M10 对比已使用一次 | " + test_line + " |")
    add("")
    add("## 重要说明")
    add("")
    add("1. **安全对齐用途**：数据用于研究/评测「条款级安全判断」与 guardrail 设计；标签为模型辅助标注"
        "（`expert_gold=false`、`training_approved=false`），合成内容不对应真实事件，不构成生产安全批准。")
    add("2. test 不是未见 benchmark：已在内部 M10 对比中使用过一次；旧 sealed blind（268）/ legacy blind（687）/"
        "MRI blind（264）不在本包。")
    add("3. Laya/Kev 是同一批行的两种格式；`mixed_m10` = specialist train + 661 条通用回放；M10 ⊂ M25 ⊂ M40；"
        "unassigned 池与 train/val/cal/dev 有 715 行重复，使用时按 `unit_id` 去重。")
    add("4. 许可：POL2 原创内容遵循 **Proof of Love2**；MRI 派生回放遵循 **MIT**（见 `release/LICENSE`、"
        "`release/LICENSES/`、`release/THIRD_PARTY_NOTICES.md`）。")
    add("")
    add("## 使用与校验")
    add("")
    add("```python")
    add("from huggingface_hub import hf_hub_download")
    add('p = hf_hub_download("' + ctx["hf_repo"] + '", "release/data/pol2-specialist/laya/train-m0.jsonl",')
    add('                    repo_type="dataset", revision="<commit sha>")')
    add("```")
    add("")
    add("Laya 的 `state` / `questions` / `gold` 是 JSON 字符串，读取后 `json.loads`；Kev 的 `questions` 为嵌套 dict。"
        "引用请固定 revision（不要引用 `main`）。")
    add("")
    add("```bash")
    add("sha256sum -c CHECKSUMS.sha256")
    add("cd release && sha256sum -c CHECKSUMS.sha256 && python3 scripts/validate_public_release.py")
    add("```")
    add("")
    add("本卡由 `datasets/pol2/export_score_v2_hf.py build` 按实际文件现算（无时间戳），请勿手改。")
    return "\n".join(lines) + "\n"


def render_card(ctx):
    """生成 HF 数据集卡：固定模板，只用计算值，无时间戳、无绝对路径。"""
    lines = []
    add = lines.append

    boundary = ctx.get("boundary")
    safe_subset = bool(ctx.get("safe_subset"))
    excluded_upstream = boundary["excluded_upstream_files"] if boundary else []
    excluded_samples = boundary["excluded_samples"] if boundary else []
    blind_in_boundary = bool(boundary
                             and boundary["audit"].get("counts", {}).get("blind_entries"))

    if ctx["has_samples"] and excluded_samples:
        samples_sentence = (code("samples/") + " 保留未命中盲测的公开样例（"
                            + num(ctx["samples_files"]) + " 个文件 / " + num(ctx["samples_rows"])
                            + " 行；命中盲测行的样例文件已排除，见 §10）；")
    elif ctx["has_samples"]:
        samples_sentence = (code("samples/") + " 收录仓库内公开样例（" + num(ctx["samples_files"])
                            + " 个文件 / " + num(ctx["samples_rows"]) + " 行，Laya/Kev 成对）；")
    else:
        samples_sentence = "本导出未包含 " + code("samples/") + "；"
    if ctx["has_cross_check"]:
        cross_sentence = code("cross-check/full-release.json") + " 是仓库侧与发布包的交叉核对登记。"
    else:
        cross_sentence = "本导出未包含 " + code("cross-check/") + "。"
    if ctx["score_dev_rows"] is None:
        score_dev_sentence = "（" + code("score-dev.jsonl") + " 已用于多轮开发）"
    else:
        score_dev_sentence = ("（" + code("score-dev.jsonl") + " " + num(ctx["score_dev_rows"])
                              + " 行已用于多轮开发）")
    if ctx["train_m0_rows"] is None:
        duplicate_sentence = "例如 " + code("train-m0") + " 在 Laya/Kev 各一份（同一批案例），"
    else:
        duplicate_sentence = ("例如 " + code("train-m0") + " 在 Laya/Kev 各一份（同一批 "
                              + num(ctx["train_m0_rows"]) + " 个 unit），")

    add("---")
    add("license: other")
    add("license_name: proof-of-love2-and-mit")
    add("license_link: " + ctx["release_url"])
    add("language: [zh]")
    add('pretty_name: "POL2 Score-v2 决策数据（研究预发布）"')
    add("size_categories: [10K<n<100K]")
    add("tags: [decision-making, typed-decisions, jev, pol2, synthetic, research-preview, proof-of-love2]")
    add("---")
    add("")
    add("# POL2 Score-v2 决策数据（研究预发布）")
    add("")
    if safe_subset:
        add("本仓库是 GitHub Release " + code(RELEASE_TAG) + " 的**安全子集**镜像加中文数据卡："
            + code("release/") + " 收录 assigned splits，排除清单见 " + code(MANIFEST_FILE) + "；"
            + samples_sentence + cross_sentence)
    else:
        add("本仓库是 GitHub Release " + code(RELEASE_TAG) + " 的逐字节镜像加中文数据卡："
            + code("release/") + " 原样收录发布包，" + samples_sentence + cross_sentence)
    add("数据是中文类型化决策样本：每行一个 " + code("state") + "，一个或多个问题（"
        + code("choice") + " / " + code("noul") + " / " + code("score") + "），外加已发布的答案与 "
        + "one-hot 目标；面向 Laya/Kev 结构化决策模型的微调、复现与审阅。所有场景为合成内容、标签为"
        + "模型辅助标注：" + code("expert_gold=false") + "、" + code("training_approved=false")
        + "，不是专家金标，也不构成生产安全批准。")
    add("")
    add("> 本文件由 " + code("datasets/pol2/export_score_v2_hf.py") + " 按实际文件现算（无时间戳），请勿手改。")
    add("> " + code("release/data/") + " 共 **" + num(ctx["data_files"]) + "** 个文件 / **"
        + num(ctx["data_rows"]) + "** 行；" + code("release/") + " 整包 **"
        + num(ctx["release_files"]) + "** 个文件 / **" + num(ctx["release_bytes"]) + "** 字节（"
        + ctx["release_human"] + "）。")
    add("")
    add("## 1. 来源与版本")
    add("")
    add("| 项 | 值 |")
    add("|---|---|")
    add("| Release tag | " + code(RELEASE_TAG) + " |")
    add("| 资产 | " + code(RELEASE_ASSET_NAME) + " |")
    add("| 资产字节数 | " + num(ctx["asset_bytes"]) + " |")
    add("| 资产 sha256 | " + code(ctx["asset_sha256"]) + " |")
    add("| 发布页 | " + ctx["release_url"] + " |")
    add("| HF 仓库 | " + ctx["hf_url"] + "（" + code(ctx["hf_repo"]) + "，dataset） |")
    add("| 语言 / 原语 | zh；" + code("choice") + " / " + code("noul") + " / " + code("score") + " |")
    add("| 生成方法 | POL2 场景生成、白名单过滤、双模型独立答案、分歧隔离、结构去重 |")
    add("")
    if safe_subset:
        add(code("release/") + " 中保留的文件与资产解压结果逐字节一致（" + code(".gitignore") + "、"
            + code(".gitattributes") + " 等隐藏文件也按原字节保留）；被排除的文件见 "
            + code(MANIFEST_FILE) + " 的 " + code("excluded_upstream_files") + "。"
            + code("release/CHECKSUMS.sha256") + " 的 " + num(ctx["release_entries"])
            + " 项已在源 Release 上全部复算通过，保留文件可按该清单逐项核对。")
    else:
        add(code("release/") + " 与资产解压结果逐字节一致（" + code(".gitignore") + "、"
            + code(".gitattributes") + " 等隐藏文件也原样保留），所以资产 sha256 可当作整包身份；"
            + code("release/CHECKSUMS.sha256") + " 的 " + num(ctx["release_entries"])
            + " 项在构建时全部复算通过。")
    add("")
    add("## 2. 许可")
    add("")
    add("- POL2 原创内容（专项数据、混合文件中的专项行、脚本与文档）：**Proof of Love2**，见 "
        + code("release/LICENSE") + " 与 " + code("release/LICENSES/Proof-of-Love2.txt") + "。")
    add("- MRI 派生的通用回放（" + code("release/data/general-replay/") + " 与混合文件中的回放行）："
        + "**MIT**，上游 " + code("MoriyaResearchInstitute/MRI-decision-data-100k") + "，见 "
        + code("release/LICENSES/MIT-MRI-decision-data-100k.txt") + " 与 "
        + code("release/THIRD_PARTY_NOTICES.md") + "。")
    add("- 混合 M10 训练文件同时适用两份通知；再分发时保留 NOTICE 与逐行来源字段。")
    add("")
    add("## 3. 数据布局")
    add("")
    if safe_subset:
        add(code("release/") + " 是发布包剔除排除清单后的子集；" + samples_sentence + cross_sentence)
    else:
        add(code("release/") + " 是发布包原文；" + samples_sentence + cross_sentence)
    add("")
    add("| 组 | 格式 | 文件 | 行数 | 字节 |")
    add("|---|---|---:|---:|---:|")
    for group in GROUP_ORDER:
        bucket = ctx["groups"].get(group)
        if not bucket:
            continue
        for fmt in FORMAT_ORDER:
            fmt_bucket = bucket["by_format"].get(fmt)
            if not fmt_bucket:
                continue
            rows_text = num(fmt_bucket["rows"]) if fmt_bucket["jsonl_files"] else "—"
            add("| " + code(group) + " | " + FORMAT_LABELS[fmt] + " | " + num(fmt_bucket["files"])
                + " | " + rows_text + " | " + num(fmt_bucket["bytes"]) + " |")
    add("")
    add("Laya 与 Kev 是同一批案例的两种装载格式，行数不能相加当独立样本（见 §5）；行数按 JSONL "
        + "非空行统计。数据目录下的 " + code("README.md") + " 计入所属组的文件数与字节数，不计行数。")
    add("")
    add("## 4. Schema 摘要")
    add("")
    add("字段契约见 " + code("release/SCHEMA.md") + "：")
    add("")
    add("- **Laya**（" + code("*laya*") + "）：" + code("state") + " / " + code("questions") + " / "
        + code("gold") + " 都是 JSON 字符串，需要二次 " + code("json.loads") + "；"
        + code("questions") + " 为 " + code("{qid: question}") + "，" + code("gold") + " 为 "
        + code("{qid: {label, probabilities}}") + "。")
    add("- **Kev**（" + code("*kev*") + "）：" + code("questions") + " 是嵌套对象，每题含 "
        + code("type") + " / " + code("instructions") + " / " + code("criteria") + " / "
        + code("label") + " / " + code("target") + "；" + code("target") + " 为 one-hot 键值表。")
    add("- 两种格式都带 " + code("case_id") + " / " + code("family_id") + " / " + code("unit_id")
        + "（形如 " + code("<case_id>:a") + "）；"
        + code("release/data/pol2-specialist/lineage/score-dev.jsonl")
        + " 是 unit 级血缘登记，字段与训练行不同。")
    add("- " + code("probabilities") + " / " + code("target") + " 由离散答案生成，是 one-hot，"
        + "不是多人投票或校准概率。")
    add("")
    add("**尚未**转换为 PoL2 canonical 的 " + code("case / question / answer / label")
        + " 四层文件；映射规则与禁止事项（不得为了凑格式丢弃 A/B 世界或补写原始事实）见 "
        + code("release/SCHEMA.md") + "。")
    add("")
    add("## 5. 去重警告（必读）")
    add("")
    add("**Laya 与 Kev 同案重复，混合包再与源包重叠。** " + duplicate_sentence
        + code("mixed-training/*-m10.jsonl") + " 又同时包含专项 " + code("train-m0") + " 行与 "
        + code("general-replay/*/train-m10.jsonl") + " 的回放行。直接拼接全部文件会把同一案例"
        + "重复计入 2 次甚至 3 次。")
    add("")
    add("- 统计案例数：按 " + code("case_id") + "（或 " + code("(family_id, unit_id)")
        + "）去重，且只取一种格式；")
    add("- 训练：一次实验只用一种格式加一个混合文件，不要把 mixed 与它的两个来源同时喂进去；")
    add("- 报告：写清用的是哪种格式、哪些文件、是否去重。")
    add("")
    add("## 6. 留出集（blind）不在本仓库")
    add("")
    if blind_in_boundary:
        add("发布包不含 " + code("HOLDOUT.md") + " 登记的完整盲测文件，本导出也不含；"
            + "unassigned 池中的 fresh-blind 单元另行排除（见 §10）：")
    else:
        add("发布包不含任何盲测文件，本导出也不含：")
    add("")
    add("| 排除内容 | 行/单元 |")
    add("|---|---:|")
    for item in ctx["holdout"]:
        add("| " + item["name"] + " | " + num(item["count"]) + " " + item["unit"] + " |")
    add("")
    add("计数与边界见 " + code("release/HOLDOUT.md") + "：完整盲测文件只登记大小与 SHA-256，"
        + "在仓库外独立保存。score-v2 sealed blind 已在 Kev M10 上消费一次，不能继续当作未见测试。"
        + "构建脚本会扫描 " + code("release/data/**") + " 的文件名，出现 " + code("blind") + " / "
        + code("sealed") + " / " + code("fresh") + " / " + code("private") + " / "
        + code("holdout") + " 即中止。")
    add("")
    add("## 7. 用法")
    add("")
    add(FENCE + "python")
    add("# Kev：questions 已是嵌套对象")
    add("from datasets import load_dataset")
    add('ds = load_dataset("json", data_files="release/data/pol2-specialist/kev/train-m0.jsonl")')
    add('row = ds["train"][0]')
    add('questions = row["questions"]          # dict')
    add(FENCE)
    add("")
    add(FENCE + "python")
    add("# Laya：questions / gold 是 JSON 字符串")
    add("import json")
    add("from datasets import load_dataset")
    add('row = load_dataset("json", data_files="release/data/pol2-specialist/laya/train-m0.jsonl")["train"][0]')
    add('questions = json.loads(row["questions"])   # {qid: question}')
    add('gold = json.loads(row["gold"])             # {qid: {label, probabilities}}')
    add(FENCE)
    add("")
    add(FENCE + "python")
    add("# 大文件（本导出最大的数据文件约 " + ctx["largest_human"] + "）：流式分块读，不整份载入")
    add("from datasets import load_dataset")
    add('stream = load_dataset("json", data_files="release/data/mixed-training/kev-m10.jsonl",')
    add('                      split="train", streaming=True)')
    add("for row in stream:")
    add("    ...")
    add(FENCE)
    add("")
    add(FENCE + "python")
    add("# 纯标准库分块读（跳过空行）")
    add("import json")
    add('with open("release/data/mixed-training/kev-m10.jsonl", encoding="utf-8") as handle:')
    add("    for line in handle:")
    add("        if line.strip():")
    add("            row = json.loads(line)")
    add(FENCE)
    add("")
    add("## 8. 用途与禁用")
    add("")
    add("**适合**：Laya/Kev 结构化决策实验复现；decision-head / guardrail 研究；专项 M0 与通用回放的"
        + "对比；loader 与格式校验；需要人工复核输出的安全评测输入；构造 benchmark 的材料来源。")
    add("")
    add("**不要**：当作专家金标或法律、合规认证；当作生产安全批准；把开发集当未见 blind"
        + score_dev_sentence + "；用单点 one-hot 冒充标注分布；无人工复核的高风险自动决策；"
        + "不加 MIT 通知再分发 MRI 派生行；把 Laya 与 Kev 相加当独立证据。")
    add("")
    add("## 9. 已知限制")
    add("")
    add("1. 标签是模型辅助标注，可能共享系统性错误（" + code("expert_gold=false") + "）。")
    add("2. " + code("score") + " 量程由每题 " + code("criteria") + " 定义，跨族不可池化数字。")
    add("3. one-hot 目标来自离散答案，不是校准概率或多人共识。")
    add("4. 公开包内的 score 开发集已用于开发，只能算 development，不能当未见测试。")
    add("5. 合成场景故意包含胁迫、歧视、隐私冲突、伤害等敏感内容，不代表真实事件或立场。")
    add("6. " + code("mixed-training") + " 是专项加回放的组合，不是独立证据；MRI 回放不是中文决策"
        + "的随机样本。")
    add("7. sealed blind 已消费一次且不公开，后续模型不能宣称完全未见。")
    add("8. 覆盖范围受实验设计限制，不替代真实场景验证。")
    add("")
    next_section = 10
    if boundary and boundary["audit"].get("applicable"):
        audit = boundary["audit"]
        counts = audit["counts"]
        sample_audit = boundary["samples"]
        add("## 10. 上游 Release 边界与本次导出范围")
        add("")
        add("构建前对上游发布包的整合清单与新增单元清单做了族级边界审计（只按 "
            + code("family_id") + " 匹配，不读取或输出任何逐例内容）：")
        add("")
        add("| 审计项 | 值 |")
        add("|---|---:|")
        add("| unassigned 新增单元 | " + num(counts["unassigned_entries"]) + " |")
        add("| 命中 fresh-blind 族的单元 | " + num(counts["blind_entries"]) + " |")
        add("| 覆盖案例 | " + num(counts["blind_cases"]) + " |")
        add("| fresh-blind 族 | " + num(counts["blind_family_count"]) + " |")
        add("")
        labels = counts.get("blind_label_counts") or {}
        if labels:
            add("盲测单元的标签计数：" + "、".join(key + "=" + num(value)
                for key, value in labels.items()) + "。")
            add("")
        if blind_in_boundary:
            add("上游 Release 把 " + code("data/pol2-specialist/score-v2-new-units/") + " 池登记为 "
                + code("UNASSIGNED") + "，但上述单元属于 fresh-blind 族，池行内仍带标签；其中部分行也"
                + "出现在仓库公开样例中。为避免把未分配的盲测标签当作公开数据，本次导出采用**安全子集**："
                + "只镜像 assigned splits，不包含 unassigned 池及其索引清单，并排除命中盲测行的样例文件。"
                + "上游 Release 的该边界待维护者修正；修正并重新发布前，本仓库不应被当作完整 Release "
                + "镜像，也不应据此推导盲测结论。")
            add("")
            add("排除的上游文件（" + num(len(excluded_upstream)) + " 个）：")
            for item in excluded_upstream:
                add("- " + code(item["path"]) + "：" + item["reason"] + "（覆盖 "
                    + num(item["blind_entries"]) + " 个盲测单元）")
            add("")
            if excluded_samples:
                add("排除的样例文件（" + num(len(excluded_samples)) + " 个，共 "
                    + num(sample_audit.get("blind_rows", 0)) + " 行命中盲测池）：")
                for item in excluded_samples:
                    add("- " + code(item["path"]) + "：" + num(item["blind_rows"]) + " 行")
                add("")
            add("除上述文件外，其余文件按原字节复制；" + code("samples/")
                + " 中未命中盲测池的样例（含 general-replay）保留。")
        else:
            add("本次族级审计未检测到边界问题：unassigned 池为 "
                + num(counts["unassigned_entries"]) + " 条，命中 fresh-blind 族 "
                + num(counts["blind_entries"]) + " 条，导出按完整镜像处理。"
                + ("（构建时按显式参数排除了 unassigned 池及索引清单。）" if safe_subset else ""))
        add("")
        if excluded_upstream:
            add("上游 " + code("release/CHECKSUMS.sha256") + " 与 " + code("release/manifest.json")
                + " 仍登记上述 " + num(len(excluded_upstream)) + " 个被排除文件，因此在 "
                + code("release/") + " 内运行上游 " + code("sha256sum -c") + " 或 "
                + code("validate_public_release.py") + " 会对缺失项报错；这是本导出的预期边界，"
                + "不是文件损坏。导出根的 " + code(CHECKSUMS_FILE) + " 与 " + code("verify")
                + " 只覆盖实际保留的文件。")
        else:
            add("上游 " + code("release/CHECKSUMS.sha256") + " 与 " + code("release/manifest.json")
                + " 覆盖完整上游树；本导出按完整镜像保留，可按清单逐项核对。")
        add("")
        next_section = 11
    add("## " + str(next_section) + ". 校验")
    add("")
    add(FENCE + "bash")
    add("# 导出根目录：校验本仓库全部文件（release/、samples/、cross-check/ 与数据卡）")
    add("sha256sum -c CHECKSUMS.sha256")
    add("")
    add("# 发布包自身清单（路径以 ./ 开头，必须在 release/ 内运行）")
    add("cd release")
    add("sha256sum -c CHECKSUMS.sha256")
    add("python3 scripts/validate_public_release.py")
    add(FENCE)
    add("")
    add("（上游 " + code("scripts/validate_public_release.py") + " 用字符串比较相对路径，Windows 的反斜杠"
        + "会与清单的正斜杠不一致而误报；该脚本与 " + code("sha256sum") + " 请在 WSL/Linux 或 "
        + "Git Bash 里运行。）")
    add("")
    if safe_subset and excluded_upstream:
        add(code("release/CHECKSUMS.sha256") + " 的 " + num(ctx["release_entries"])
            + " 项已在源 Release 上全部复算通过；本导出从 " + code("release/") + " 中排除了 "
            + num(len(excluded_upstream)) + " 个上游文件（见 §10），这些项对应的文件不在本导出内。"
            + code("release/manifest.json") + " 仍登记完整上游树；" + code("verify") + " 与导出根的 "
            + code(CHECKSUMS_FILE) + " 只覆盖实际保留的文件。维护者可以用仓库脚本离线校验"
            + "任意下载副本：")
    else:
        add(code("release/CHECKSUMS.sha256") + " 的 " + num(ctx["release_entries"])
            + " 项在构建时全部复算通过；" + code("release/manifest.json")
            + " 登记的行数、字节数与 sha256 也与文件一致（" + code("scripts/validate_public_release.py")
            + " 会再查一遍结构、one-hot、跨格式一致性与隐私模式）。维护者可以用仓库脚本离线校验"
            + "任意下载副本：")
    add("")
    add(FENCE + "bash")
    add("python datasets/pol2/export_score_v2_hf.py verify --dir <本目录>")
    add(FENCE)
    add("")
    add("## " + str(next_section + 1) + ". 引用与相关链接")
    add("")
    add("- 引用信息：" + code("release/CITATION.cff") + "（title " + code("POL2 Score-v2 Decisions")
        + "，version " + code("1.0.0-rc1") + "，license " + code("Proof of Love2")
        + "）。引用时请固定 HF revision（commit sha），不要引用 " + code("main") + "。")
    add("- Release：" + ctx["release_url"])
    add("- 仓库侧数据卡与边界：https://github.com/naturaldao/NaturalDAO/blob/main/datasets/pol2/score-v2/README.md")
    add("- 上游回放：https://huggingface.co/datasets/MoriyaResearchInstitute/MRI-decision-data-100k"
        + "（revision " + code("9f89047d7d222d1cc304217d3e84acdf6dbc636c") + "，MIT）")
    add("")
    add("    @misc{pol2-score-v2-v1.0.0,")
    add("      title        = {POL2 Score-v2 Decisions},")
    add("      author       = {{NaturalDAO contributors}},")
    add("      year         = {2026},")
    add("      howpublished = {Hugging Face dataset, mirrored from GitHub Release pol2-score-v2-v1.0.0},")
    add("      note         = {Version 1.0.0-rc1; Proof of Love2, with MIT for MRI-derived rows}")
    add("    }")
    add("")
    add("---")
    add("")
    add("本数据卡由 " + code("datasets/pol2/export_score_v2_hf.py build")
        + " 生成（纯标准库、离线、确定性、无时间戳），同输入两次构建逐字节一致；机器清单见 "
        + code(MANIFEST_FILE) + "，文件校验见 " + code(CHECKSUMS_FILE) + "。")
    return NL.join(lines) + NL


# ---------------------------------------------------------------- build

def _check_directories(release_dir, out):
    release = Path(release_dir).resolve()
    target = Path(out).resolve()
    if target == release or target.is_relative_to(release):
        raise ExportError("导出目录不能位于 Release 目录内：" + str(out))
    if release.is_relative_to(target):
        raise ExportError("导出目录不能是 Release 目录的祖先：" + str(out))


def _staging_dir(out):
    out = Path(out)
    parent = out.parent
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=".pol2-hf-export-", dir=str(parent)))


def _replace_out(staging, out):
    out = Path(out)
    if out.exists():
        if not out.is_dir():
            raise ExportError("导出路径已存在且不是目录：" + str(out))
        shutil.rmtree(out)
    try:
        os.replace(staging, out)
    except OSError:
        shutil.move(str(staging), str(out))


def _exclusion_ignore(root, excluded):
    """copytree 的 ignore 回调：excluded 为相对 root（POSIX 写法）的路径集合。"""
    root = Path(root).resolve()

    def ignore(directory, names):
        base = Path(directory).resolve()
        relative_dir = "" if base == root else base.relative_to(root).as_posix()
        ignored = []
        for name in names:
            relative = name if not relative_dir else relative_dir + "/" + name
            if relative in excluded:
                ignored.append(name)
        return ignored

    return ignore


def build_manifest(files, data_groups, org, release_entries, boundary=None):
    rows_by_group = {group: bucket["rows"] for group, bucket in data_groups.items()}
    manifest = {
        "schema": EXPORT_SCHEMA,
        "release": {
            "tag": RELEASE_TAG,
            "asset_name": RELEASE_ASSET_NAME,
            "asset_sha256": RELEASE_ASSET_SHA256,
            "asset_bytes": RELEASE_ASSET_BYTES,
            "source_repo_url": "https://github.com/" + GITHUB_REPO,
            "release_url": release_url(),
            "asset_url": asset_url(),
            "checksums_verified": release_entries,
        },
        "hf": {
            "org": org,
            "repo": org + "/" + PUBLIC_REPO,
            "url": hf_url(org),
            "repo_type": "dataset",
        },
        "license": {
            "project": "Proof of Love2",
            "project_license_name": "proof-of-love2",
            "upstream": "MIT（MoriyaResearchInstitute/MRI-decision-data-100k）",
            "mixed_license": "混合 M10 文件同时适用 Proof of Love2 与 MRI MIT 通知",
            "notice_paths": [
                "release/LICENSE",
                "release/LICENSES/Proof-of-Love2.txt",
                "release/LICENSES/MIT-MRI-decision-data-100k.txt",
                "release/THIRD_PARTY_NOTICES.md",
            ],
        },
        "summary": {
            "files": len(files),
            "bytes": sum(entry["bytes"] for entry in files),
            "rows_by_group": rows_by_group,
        },
        "files": files,
        "data_groups": data_groups,
        "excluded_holdout": {
            "included": False,
            "entries": [dict(item) for item in HOLDOUT_EXCLUSIONS],
            "source": "release/HOLDOUT.md",
        },
        "generated_by": "datasets/pol2/export_score_v2_hf.py build",
        "verify_command": "python datasets/pol2/export_score_v2_hf.py verify --dir <本目录>",
        "network": "不联网：只读本地文件，不做 HF 调用",
        "determinism": "同一输入两次构建输出逐字节相同；无时间戳/绝对路径/随机数",
    }
    if boundary is not None:
        manifest["excluded_upstream_files"] = [dict(item) for item in
                                               boundary["excluded_upstream_files"]]
        manifest["excluded_samples"] = [dict(item) for item in boundary["excluded_samples"]]
        manifest["boundary_audit"] = boundary["audit"]
    return manifest


def _empty_sample_audit(reason):
    return {
        "applicable": False,
        "reason": reason,
        "files": [],
        "general_replay": [],
        "rows": 0,
        "blind_rows": 0,
        "blind_files": [],
        "unmapped_rows": 0,
        "pool_entries": {},
    }


def build(release_dir, out, samples_dir=None, org=DEFAULT_ORG,
          exclude_unassigned_pool=False, exclude_blind_samples=False):
    """校验 Release、审计边界、复制树、生成数据卡/清单/校验文件，原子替换 out。

    exclude_unassigned_pool：排除 unassigned 新增单元池及其索引清单；
    exclude_blind_samples：排除命中盲测池的 specialist 样例文件。
    """
    release_dir = Path(release_dir)
    out = Path(out)
    org = normalize_org(org)
    _check_directories(release_dir, out)

    release_info = verify_release_dir(release_dir)
    hits = scan_blind_names(release_dir)
    if hits:
        detail = "、".join(hits[:5])
        if len(hits) > 5:
            detail += "（共 " + str(len(hits)) + " 个）"
        raise ExportError("盲测文件名命中，拒绝导出（release/data 不得含 blind/sealed/fresh/private/"
                          "holdout）：" + detail)

    samples = Path(samples_dir) if samples_dir is not None else None
    has_samples = samples is not None and samples.is_dir()
    has_cross_check = Path(FULL_RELEASE_MANIFEST).is_file()

    boundary_audit = audit_release_boundaries(release_dir)
    boundary_applicable = bool(boundary_audit.get("applicable"))
    blind_entries = boundary_audit.get("blind_entries", 0) if boundary_applicable else 0
    interpretation = public_test_interpretation(boundary_audit) if boundary_applicable else None
    public_test_mode = bool(interpretation) and not exclude_unassigned_pool
    sample_audit = (audit_samples(samples, release_dir) if has_samples
                    else _empty_sample_audit("未提供样例目录"))

    if blind_entries and not exclude_unassigned_pool and not public_test_mode:
        raise ExportError(
            "上游 unassigned 池含 " + num(blind_entries) + " 个 fresh-blind 单元（"
            + num(boundary_audit.get("blind_cases", 0)) + " 个案例），默认拒绝导出。修复路径："
            "1) 上游 Release 把 fresh-blind 单元移出 unassigned 池后重新发布；"
            "2) 或加 --exclude-unassigned-pool 只导出 assigned splits（样例命中盲测时再加 "
            "--exclude-blind-samples）；3) 若该池已确认是公开 test 划分，需 Release 签名与 "
            "PUBLIC_TEST_SIGNATURE 一致（当前签名见脚本常量）。")

    excluded_release = set()
    excluded_upstream_files = []
    if exclude_unassigned_pool:
        pool_reason = ("unassigned 池行内含 fresh-blind 标签，不属于 assigned splits"
                       if blind_entries else
                       "按 --exclude-unassigned-pool 排除 unassigned 池（本次审计未命中 fresh-blind）")
        manifest_reason = ("登记 unassigned 池（含 fresh-blind 单元），排除以免重建该池"
                           if blind_entries else
                           "登记 unassigned 池；按 --exclude-unassigned-pool 一并排除")
        for relative in UNASSIGNED_POOL_RELS:
            if (release_dir / relative).is_file():
                excluded_release.add(relative)
                excluded_upstream_files.append({
                    "path": RELEASE_DIRNAME + "/" + relative,
                    "reason": pool_reason,
                    "blind_entries": blind_entries,
                })
        for relative in UNASSIGNED_MANIFEST_RELS:
            if (release_dir / relative).is_file():
                excluded_release.add(relative)
                excluded_upstream_files.append({
                    "path": RELEASE_DIRNAME + "/" + relative,
                    "reason": manifest_reason,
                    "blind_entries": blind_entries,
                })
        excluded_upstream_files.sort(key=lambda item: item["path"])

    excluded_sample_names = set()
    excluded_samples = []
    if exclude_blind_samples and sample_audit.get("applicable"):
        for record in sample_audit["files"]:
            if not record["blind_rows"]:
                continue
            name = record["path"].split("/", 1)[1]
            excluded_sample_names.add(name)
            excluded_samples.append({"path": record["path"], "blind_rows": record["blind_rows"]})
        excluded_samples.sort(key=lambda item: item["path"])

    staging = _staging_dir(out)
    try:
        shutil.copytree(release_dir, staging / RELEASE_DIRNAME,
                        copy_function=shutil.copyfile,
                        ignore=_exclusion_ignore(release_dir, excluded_release))
        if has_samples:
            shutil.copytree(samples, staging / "samples",
                            copy_function=shutil.copyfile,
                            ignore=_exclusion_ignore(samples, excluded_sample_names))
        pool_dir = staging / RELEASE_DIRNAME / "data" / "pol2-specialist" / "score-v2-new-units"
        if pool_dir.is_dir() and not any(pool_dir.iterdir()):
            pool_dir.rmdir()
        if has_cross_check:
            write_bytes(staging / "cross-check" / "full-release.json",
                        Path(FULL_RELEASE_MANIFEST).read_bytes())

        files = collect_export_files(staging)
        data_groups = build_data_groups(files)
        data_files = [entry for entry in files
                      if entry["path"].startswith(RELEASE_DIRNAME + "/data/")]
        data_bytes = sum(entry["bytes"] for entry in data_files)
        data_rows = sum(entry["rows"] or 0 for entry in data_files)
        release_files = [entry for entry in files if entry["kind"] == "release"]
        release_bytes = sum(entry["bytes"] for entry in release_files)
        samples_files = [entry for entry in files if entry["kind"] == "samples"]
        largest = max((entry["bytes"] for entry in data_files), default=0)

        def rows_of(relative):
            for entry in files:
                if entry["path"] == relative:
                    return entry["rows"]
            return None

        included_paths = sorted(
            entry["path"] for entry in files
            if entry["path"].startswith(RELEASE_DIRNAME + "/data/")
            or entry["path"].startswith("samples/"))
        excluded_paths = sorted([item["path"] for item in excluded_upstream_files]
                                + [item["path"] for item in excluded_samples])
        packaged_audit = {
            "schema": BOUNDARY_SCHEMA,
            "applicable": boundary_applicable,
            "counts": {
                "unassigned_entries": boundary_audit.get("unassigned_entries", 0),
                "blind_entries": blind_entries,
                "blind_cases": boundary_audit.get("blind_cases", 0),
                "blind_family_count": boundary_audit.get("blind_family_count", 0),
                "blind_label_counts": boundary_audit.get("blind_label_counts", {}),
                "blind_label_total": boundary_audit.get("blind_label_total", 0),
                "label_counts_match": boundary_audit.get("label_counts_match", False),
            },
            "safe_subset": bool(exclude_unassigned_pool),
            "public_test": bool(public_test_mode),
            "interpretation": interpretation,
            "excluded_upstream_files": [item["path"] for item in excluded_upstream_files],
            "excluded_samples": [item["path"] for item in excluded_samples],
            "included": included_paths,
            "excluded": excluded_paths,
            "samples": sample_audit,
        }
        boundary_ctx = {
            "audit": packaged_audit,
            "samples": sample_audit,
            "excluded_upstream_files": excluded_upstream_files,
            "excluded_samples": excluded_samples,
        }
        boundary_for_manifest = (boundary_ctx
                                 if (exclude_unassigned_pool or exclude_blind_samples
                                     or public_test_mode)
                                 else None)

        prefix = RELEASE_DIRNAME + "/data/"
        ctx = {
            "asset_bytes": RELEASE_ASSET_BYTES,
            "asset_sha256": RELEASE_ASSET_SHA256,
            "release_url": release_url(),
            "hf_url": hf_url(org),
            "hf_repo": org + "/" + PUBLIC_REPO,
            "release_files": len(release_files),
            "release_bytes": release_bytes,
            "release_human": human_bytes(release_bytes),
            "data_files": len(data_files),
            "data_rows": data_rows,
            "release_entries": release_info["entries"],
            "groups": data_groups,
            "has_samples": has_samples,
            "samples_files": len(samples_files),
            "samples_rows": sum(entry["rows"] or 0 for entry in samples_files),
            "has_cross_check": has_cross_check,
            "largest_human": human_bytes(largest),
            "train_m0_rows": rows_of(prefix + "pol2-specialist/laya/train-m0.jsonl"),
            "validation_rows": rows_of(prefix + "pol2-specialist/laya/validation.jsonl"),
            "calibration_rows": rows_of(prefix + "pol2-specialist/laya/calibration.jsonl"),
            "score_dev_rows": rows_of(prefix + "pol2-specialist/laya/score-dev.jsonl"),
            "holdout": HOLDOUT_EXCLUSIONS,
            "boundary": boundary_ctx,
            "safe_subset": bool(exclude_unassigned_pool),
            "public_test": bool(public_test_mode),
            "interpretation": interpretation,
        }

        card_text = render_public_test_card(ctx) if public_test_mode else render_card(ctx)
        write_text(staging / CARD_FILE, card_text)
        files.append(entry_for(staging, CARD_FILE))
        files.sort(key=lambda item: item["path"])

        manifest = build_manifest(files, data_groups, org, release_info["entries"],
                                  boundary_for_manifest)
        write_json(staging / MANIFEST_FILE, manifest)
        write_checksums(staging, files)
        tree = tree_digest(staging)
        _replace_out(staging, out)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "out": out,
        "org": org,
        "files": len(files),
        "bytes": sum(entry["bytes"] for entry in files),
        "rows": data_rows,
        "rows_by_group": {group: bucket["rows"] for group, bucket in data_groups.items()},
        "data_groups": data_groups,
        "tree_sha256": tree,
        "samples": has_samples,
        "cross_check": has_cross_check,
        "release_checksums": release_info["entries"],
        "boundary_audit": boundary_audit if boundary_applicable else None,
        "sample_audit": sample_audit if sample_audit.get("applicable") else None,
        "excluded_upstream_files": excluded_upstream_files,
        "excluded_samples": excluded_samples,
        "safe_subset": bool(exclude_unassigned_pool),
    }


# ---------------------------------------------------------------- verify

def verify_export(directory):
    """离线校验导出目录：sha256/bytes、多余文件、CHECKSUMS 与 MANIFEST 一致、数据卡存在。"""
    directory = Path(directory)
    if not directory.is_dir():
        raise ExportError("目录不存在：" + str(directory))
    manifest_path = directory / MANIFEST_FILE
    if not manifest_path.is_file():
        raise ExportError("缺少 " + MANIFEST_FILE + "：" + str(directory))
    manifest = read_json(manifest_path)

    problems = []
    if manifest.get("schema") != EXPORT_SCHEMA:
        problems.append("MANIFEST.json 的 schema 不是 " + EXPORT_SCHEMA)
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ExportError("MANIFEST.json 缺少非空 files 列表")

    declared = {}
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append("files 里存在非对象条目")
            continue
        relative = entry.get("path")
        size = entry.get("bytes")
        digest = entry.get("sha256")
        if not isinstance(relative, str):
            problems.append("文件项缺少 path")
            continue
        try:
            relative = normalize_relpath(relative)
        except ExportError as error:
            problems.append(str(error))
            continue
        if relative in (MANIFEST_FILE, CHECKSUMS_FILE):
            problems.append("MANIFEST.json 不应登记自身或校验清单：" + relative)
            continue
        if relative in declared:
            problems.append("文件重复登记：" + relative)
            continue
        if (not isinstance(size, int) or not isinstance(digest, str) or len(digest) != 64
                or any(char not in HEX_DIGITS for char in digest.lower())):
            problems.append("文件项字段不完整：" + relative)
            continue
        declared[relative] = entry
        target = directory / relative
        if not target.is_file():
            problems.append("缺文件：" + relative)
            continue
        if target.stat().st_size != size:
            problems.append("字节数不一致：" + relative)
        if sha256_file(target) != digest.lower():
            problems.append("sha256 不一致：" + relative)

    checksums_path = directory / CHECKSUMS_FILE
    if not checksums_path.is_file():
        problems.append("缺少 " + CHECKSUMS_FILE)
    else:
        try:
            checksum_entries = parse_checksums(checksums_path.read_text(encoding="utf-8"))
        except ExportError as error:
            problems.append(str(error))
            checksum_entries = []
        actual = {}
        for raw_path, digest in checksum_entries:
            try:
                relative = normalize_relpath(raw_path)
            except ExportError as error:
                problems.append(str(error))
                continue
            if relative in actual:
                problems.append(CHECKSUMS_FILE + " 重复登记：" + relative)
                continue
            actual[relative] = digest
        expected = {relative: entry["sha256"].lower() for relative, entry in declared.items()}
        for relative in sorted(set(expected) - set(actual)):
            problems.append(CHECKSUMS_FILE + " 缺登记：" + relative)
        for relative in sorted(set(actual) - set(expected)):
            problems.append(CHECKSUMS_FILE + " 多登记：" + relative)
        for relative in sorted(set(actual) & set(expected)):
            if actual[relative] != expected[relative]:
                problems.append(CHECKSUMS_FILE + " 与 MANIFEST 的 sha256 不一致：" + relative)

    actual_paths = {path.relative_to(directory).as_posix()
                    for path in directory.rglob("*") if path.is_file()}
    allowed = set(declared) | {MANIFEST_FILE, CHECKSUMS_FILE}
    for extra in sorted(actual_paths - allowed):
        problems.append("多余文件：" + extra)

    summary = manifest.get("summary") or {}
    if summary.get("files") != len(declared):
        problems.append("summary.files 与 files 数量不一致")
    if summary.get("bytes") != sum(entry["bytes"] for entry in declared.values()):
        problems.append("summary.bytes 与 files 之和不一致")

    card_entry = declared.get(CARD_FILE)
    if card_entry is None or card_entry.get("kind") != "card":
        problems.append("缺少数据卡登记：" + CARD_FILE)
    elif not (directory / CARD_FILE).is_file():
        problems.append("缺少数据卡文件：" + CARD_FILE)

    for key in ("excluded_upstream_files", "excluded_samples"):
        items = manifest.get(key)
        if items is None:
            continue
        if not isinstance(items, list):
            problems.append("MANIFEST." + key + " 不是列表")
            continue
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                problems.append("MANIFEST." + key + " 含缺少 path 的条目")
                continue
            try:
                relative = normalize_relpath(item["path"])
            except ExportError as error:
                problems.append(str(error))
                continue
            if relative in declared:
                problems.append("声明排除却仍登记：" + relative)

    return {
        "dir": str(directory),
        "schema": manifest.get("schema"),
        "files": len(declared),
        "bytes": sum(entry["bytes"] for entry in declared.values()),
        "status": "pass" if not problems else "fail",
        "problems": problems,
    }


# ---------------------------------------------------------------- 命令

def cmd_build(args):
    samples_dir = Path(args.samples_dir) if args.samples_dir is not None else DEFAULT_SAMPLES_DIR
    result = build(Path(args.release_dir), Path(args.out), samples_dir, args.org,
                   exclude_unassigned_pool=args.exclude_unassigned_pool,
                   exclude_blind_samples=args.exclude_blind_samples)
    report = {
        "command": "build",
        "out": str(result["out"]),
        "org": result["org"],
        "files": result["files"],
        "bytes": result["bytes"],
        "rows": result["rows"],
        "rows_by_group": result["rows_by_group"],
        "data_groups": result["data_groups"],
        "tree_sha256": result["tree_sha256"],
        "samples": result["samples"],
        "cross_check": result["cross_check"],
        "release_checksums": result["release_checksums"],
        "boundary_audit": result["boundary_audit"],
        "sample_audit": result["sample_audit"],
        "excluded_upstream_files": result["excluded_upstream_files"],
        "excluded_samples": result["excluded_samples"],
        "safe_subset": result["safe_subset"],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("导出完成：" + str(result["out"]))
        print("文件 " + num(result["files"]) + " 个 / " + human_bytes(result["bytes"])
              + " / 数据行 " + num(result["rows"]) + " 行")
        for group in sorted(result["rows_by_group"]):
            print("  " + group + "：" + num(result["rows_by_group"][group]) + " 行")
        audit = result["boundary_audit"]
        if audit:
            print("边界审计：unassigned " + num(audit["unassigned_entries"])
                  + " 条 / 命中 fresh-blind " + num(audit["blind_entries"]) + " 条（"
                  + num(audit["blind_cases"]) + " 个案例）")
        if result["excluded_upstream_files"]:
            print("排除上游文件 " + num(len(result["excluded_upstream_files"])) + " 个")
        if result["excluded_samples"]:
            print("排除样例文件 " + num(len(result["excluded_samples"])) + " 个")
        print("树哈希：" + result["tree_sha256"])
    return 0


def cmd_verify(args):
    report = verify_export(Path(args.dir))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif report["status"] == "pass":
        print("校验通过：" + report["dir"] + "（" + num(report["files"]) + " 个文件 / "
              + human_bytes(report["bytes"]) + "）")
    else:
        print("校验失败：" + report["dir"] + "（" + str(len(report["problems"])) + " 项问题）")
        for problem in report["problems"]:
            print("  - " + problem)
    return 0 if report["status"] == "pass" else 2


def cmd_stats(args):
    directory = Path(args.dir)
    manifest_path = directory / MANIFEST_FILE
    if not manifest_path.is_file():
        raise ExportError("缺少 " + MANIFEST_FILE + "：" + str(directory))
    manifest = read_json(manifest_path)
    summary = {
        "dir": str(directory),
        "schema": manifest.get("schema"),
        "release": manifest.get("release"),
        "hf": manifest.get("hf"),
        "summary": manifest.get("summary"),
        "data_groups": manifest.get("data_groups"),
        "excluded_holdout": manifest.get("excluded_holdout"),
        "boundary_audit": manifest.get("boundary_audit"),
        "excluded_upstream_files": manifest.get("excluded_upstream_files"),
        "excluded_samples": manifest.get("excluded_samples"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="export_score_v2_hf.py",
        description="POL2 score-v2 Release 到 HF 数据集的导出与离线校验（纯标准库、确定性）")
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build", help="复算 Release、复制树并生成数据卡/清单/校验")
    build_parser.add_argument("--release-dir", type=Path, required=True,
                              help="Release 解压包根目录（只读）")
    build_parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="导出根目录")
    build_parser.add_argument("--samples-dir", type=Path, default=None,
                              help="仓库公开样例目录；默认 datasets/pol2/score-v2/samples")
    build_parser.add_argument("--org", default=DEFAULT_ORG,
                              help="HF 组织/用户；只影响 MANIFEST.hf 与卡内链接")
    build_parser.add_argument("--exclude-unassigned-pool", action="store_true",
                              help="排除 unassigned 新增单元池及其索引清单（安全子集）")
    build_parser.add_argument("--exclude-blind-samples", action="store_true",
                              help="排除命中盲测池的 specialist 样例文件")
    build_parser.add_argument("--json", action="store_true", help="输出 JSON 摘要")
    build_parser.set_defaults(func=cmd_build)

    verify_parser = sub.add_parser("verify", help="离线校验导出目录")
    verify_parser.add_argument("--dir", type=Path, default=DEFAULT_OUT, help="导出根目录")
    verify_parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    verify_parser.set_defaults(func=cmd_verify)

    stats_parser = sub.add_parser("stats", help="打印 MANIFEST 摘要")
    stats_parser.add_argument("--dir", type=Path, default=DEFAULT_OUT, help="导出根目录")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ExportError as error:
        print("导出失败：" + str(error), file=sys.stderr)
        return 2
    except OSError as error:
        print("导出失败（I/O）：" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

