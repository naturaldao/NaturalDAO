#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""general 决策数据集 v5 的确定性 HF 导出、仓库清单与校验（纯标准库，不联网）。

三个子命令：

    inventory   只读扫描 datasets/general/data/**，写 data/MANIFEST.json（tracked）
    build       生成 data/hf-export/public/ 与 data/hf-export/private-holdout/
    verify      校验已有导出目录（默认 data/hf-export）里每个文件的 sha256
    all         inventory + build + verify + 跑私有包 verify.py（默认）

设计约定（与任务简报一致）：

1. 输入只读：只读 datasets/general/data/** 下已有的产物，不修改数据实体。
2. 确定性：输出不含时间戳/随机数；JSON 一律 sort_keys=True、ensure_ascii=False、
   indent=2、行尾 LF；.gz 优先逐字节复制源文件（源缺失时才用 mtime=0 的固定压缩级别
   重新压缩）。同一输入两次运行，输出逐字节相同（最后打印整棵树的树哈希供比对）。
3. 公开面硬断言：发布前读 benchmark 全量成员 id，公开导出的每个条目都要过一遍，
   命中即非零退出（只报"命中"不打印成员 id）。
4. public 与 private_holdout 物理分开；私有包目录整包复制，包内 verify.py 可独立运行。
5. 不打印任何 benchmark 样本内容；私有包清单只含计数与 sha256。

用法（仓库根目录执行）：

    uv run --no-project --offline python datasets/general/export_hf.py all

发布与上传见 datasets/general/HF.md。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = HERE / "data"
SPLITS = DATA / "splits"
BENCH_PKG = SPLITS / "benchmark-dataset"
EXPORT = DATA / "hf-export"
PUBLIC_DIR = EXPORT / "public"
HOLDOUT_DIR = EXPORT / "private-holdout"
MANIFEST_PATH = DATA / "MANIFEST.json"

DATASET_ID = "general-decision-v0.5"
DATASET_TITLE = "PoL 通用决策数据集 v5"
INVENTORY_SCHEMA = "pol-general-data-manifest/1"
EXPORT_SCHEMA = "pol-hf-export-manifest/1"
BENCH_PKG_SCHEMA = "pol-internal-benchmark-package/0.1"
DEFAULT_ORG = "naturaldao"
PUBLIC_REPO = "pol-decision-general-v5"
HOLDOUT_REPO = "pol-decision-general-v5-holdout"
STATUS = "ready_not_uploaded"
NL = chr(10)
TAB = chr(9)


class ExportError(Exception):
    """输入缺失、口径不一致或自检失败。"""


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
    return json.loads(Path(path).read_text(encoding="utf-8"))


def open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "rt", encoding="utf-8")


def iter_jsonl(path):
    with open_text(path) as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def jsonl_lines(path):
    count = 0
    with open_text(path) as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def gzip_bytes(data):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, compresslevel=9) as handle:
        handle.write(data)
    return buffer.getvalue()


def copy_artifact(source_gz, source_plain, target):
    """复制压缩件（逐字节）；只有压缩件缺失时才从明文确定性重压。"""
    source_gz = Path(source_gz)
    source_plain = Path(source_plain)
    if source_gz.is_file():
        data = source_gz.read_bytes()
        mode = "verbatim-gz"
    elif source_plain.is_file():
        data = gzip_bytes(source_plain.read_bytes())
        mode = "deterministic-recompress"
    else:
        raise ExportError("缺少输入文件：" + source_gz.as_posix())
    write_bytes(target, data)
    return {"mode": mode, "bytes": len(data), "sha256": sha256_bytes(data)}


def tree_digest(root):
    root = Path(root)
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        lines.append(path.relative_to(root).as_posix() + ":" + sha256_file(path))
    return sha256_bytes(NL.join(lines).encode("utf-8"))


def org_slug():
    return (os.environ.get("HF_ORG") or DEFAULT_ORG).strip() or DEFAULT_ORG


# ---------------------------------------------------------------- git 证据（可选，不联网）

GITIGNORE_PROBES = [
    "data/MANIFEST.json",
    "data/splits/train.jsonl.gz",
    "data/splits/validation.jsonl.gz",
    "data/splits/test.jsonl.gz",
    "data/jev-probs.jsonl.gz",
    "data/target-types.jsonl.gz",
    "data/zh-supplement/items.jsonl",
    "data/zh-supplement/items.jsonl.gz",
    "data/splits/benchmark.jsonl",
    "data/splits/benchmark.jsonl.gz",
    "data/splits/benchmark-dataset/manifest.json",
    "data/hf-export/public/README.md",
    "data/hf-export/public/MANIFEST.json",
    "data/hf-export/public/train.jsonl.gz",
    "data/hf-export/private-holdout/verify.py",
    "data/hf-export/private-holdout/manifest.json",
]


def git_tracked(scope="data"):
    """git 跟踪集合（相对 datasets/general 的路径）；git 不可用返回 None。"""
    try:
        completed = subprocess.run(
            ["git", "-C", str(HERE), "-c", "core.quotePath=false", "ls-files", "-z", "--", scope],
            capture_output=True)
    except (OSError, FileNotFoundError):
        return None
    if completed.returncode != 0:
        return None
    names = completed.stdout.split(chr(0).encode("utf-8"))
    return {name.decode("utf-8", "surrogateescape") for name in names if name}


def gitignore_evidence():
    """对固定探针路径报告命中的 .gitignore 规则；git 不可用返回 None。

    这是给 Lead 做"大文件离仓 + .gitignore 是否足够"的机器可读旁证。
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(HERE), "check-ignore", "--no-index", "-v", "--"] + GITIGNORE_PROBES,
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    except (OSError, FileNotFoundError):
        return None
    if completed.returncode not in (0, 1):
        return None
    matched = {}
    for line in completed.stdout.splitlines():
        if TAB not in line:
            continue
        rule, pathname = line.split(TAB, 1)
        matched[pathname.strip()] = rule
    evidence = []
    for probe in GITIGNORE_PROBES:
        rule = matched.get(probe)
        evidence.append({"path": probe, "ignored": bool(rule), "rule": rule})
    return evidence


# ---------------------------------------------------------------- 分类与用途

PUBLIC_ITEMS = [
    ("train.jsonl.gz", "train", "datasets/general/data/splits/train.jsonl.gz"),
    ("validation.jsonl.gz", "validation", "datasets/general/data/splits/validation.jsonl.gz"),
    ("test.jsonl.gz", "test", "datasets/general/data/splits/test.jsonl.gz"),
]
SIDECARS = [
    ("jev-probs.jsonl.gz", "jev-probs", "datasets/general/data/jev-probs.jsonl.gz",
     "jev-probs/1", "datasets/general/jev_fill.py probs-public"),
    ("target-types.jsonl.gz", "target-types", "datasets/general/data/target-types.jsonl.gz",
     "target-types/1", "datasets/general/target_types.py"),
]
SUPPLEMENT = ("zh-supplement-items.jsonl.gz", "datasets/general/data/zh-supplement/items.jsonl.gz",
              "general-decision-items/0.5",
              "build_supp.py（来源与参数见 data/zh-supplement/manifest.json）")
HOLDOUT_FILES = ["benchmark.jsonl", "benchmark.jsonl.gz", "manifest.json", "README.md",
                 "USAGE.md", "verify.py"]

HOSTED = {
    "splits/train.jsonl.gz": ("public", "train.jsonl.gz"),
    "splits/validation.jsonl.gz": ("public", "validation.jsonl.gz"),
    "splits/test.jsonl.gz": ("public", "test.jsonl.gz"),
    "jev-probs.jsonl.gz": ("public", "jev-probs.jsonl.gz"),
    "target-types.jsonl.gz": ("public", "target-types.jsonl.gz"),
    "zh-supplement/items.jsonl.gz": ("public", "zh-supplement-items.jsonl.gz"),
    "splits/benchmark.jsonl": ("holdout", "benchmark.jsonl"),
    "splits/benchmark.jsonl.gz": ("holdout", "benchmark.jsonl.gz"),
    "splits/benchmark-dataset/benchmark.jsonl": ("holdout", "benchmark.jsonl"),
    "splits/benchmark-dataset/benchmark.jsonl.gz": ("holdout", "benchmark.jsonl.gz"),
    "splits/benchmark-dataset/manifest.json": ("holdout", "manifest.json"),
    "splits/benchmark-dataset/README.md": ("holdout", "README.md"),
    "splits/benchmark-dataset/USAGE.md": ("holdout", "USAGE.md"),
    "splits/benchmark-dataset/verify.py": ("holdout", "verify.py"),
}

PUBLIC_SPLIT_PATHS = {
    "splits/train.jsonl": "train 分区主数据（items JSONL）",
    "splits/train.jsonl.gz": "train 分区主数据（gzip 压缩版，HF 发布件）",
    "splits/validation.jsonl": "validation 分区主数据（选模型/调参）",
    "splits/validation.jsonl.gz": "validation 分区主数据（gzip 压缩版，HF 发布件）",
    "splits/test.jsonl": "test 分区主数据（回归测试）",
    "splits/test.jsonl.gz": "test 分区主数据（gzip 压缩版，HF 发布件）",
}


def role_of(rel):
    if rel in PUBLIC_SPLIT_PATHS:
        return PUBLIC_SPLIT_PATHS[rel]
    if rel == "jev-probs.jsonl":
        return "概率旁挂件明文（本地，不入库）"
    if rel == "jev-probs.jsonl.gz":
        return "概率旁挂件（公开面 44,740 行；HF 发布件）"
    if rel == "target-types.jsonl":
        return "target 形态与训练路由旁挂件明文（本地，不入库）"
    if rel == "target-types.jsonl.gz":
        return "target 形态与训练路由旁挂件（公开面 74,853 行；HF 发布件）"
    if rel == "zh-supplement/items.jsonl":
        return "train-only 中文安全补充 3,148 条（明文，本地，不入库）"
    if rel == "zh-supplement/items.jsonl.gz":
        return "train-only 中文安全补充 3,148 条（gzip；HF 发布件，仓库留小体积副本）"
    if rel == "zh-supplement/manifest.json":
        return "中文补充集来源与参数清单（tracked）"
    if rel == "zh-supplement/stats.json":
        return "中文补充集选择统计（tracked）"
    if rel == "splits/split-manifest.json":
        return "切分清单：盐指纹、分区哈希、保留集轮换记录（tracked）"
    if rel in ("splits/benchmark.jsonl", "splits/benchmark.jsonl.gz"):
        return "内部保留集（private_holdout，不得公开；上传件取 benchmark-dataset 内副本）"
    if rel == "splits/benchmark-dataset/benchmark.jsonl":
        return "内部保留集明文（私有包，仓库内 gitignored）"
    if rel == "splits/benchmark-dataset/benchmark.jsonl.gz":
        return "内部保留集 gzip（私有包 HF 发布件）"
    if rel == "splits/benchmark-dataset/manifest.json":
        return "私有 benchmark 包清单（schema pol-internal-benchmark-package/0.1）"
    if rel == "splits/benchmark-dataset/README.md":
        return "私有 benchmark 包数据卡"
    if rel == "splits/benchmark-dataset/USAGE.md":
        return "私有 benchmark 使用说明"
    if rel == "splits/benchmark-dataset/verify.py":
        return "私有 benchmark 包完整性校验（模板副本）"
    if rel.startswith("splits/"):
        return "切分/打包/校验脚本（tracked 代码）"
    if rel.startswith("jev/"):
        return "概率补全流水线中间产物（本地，不入库）"
    if rel == "items.final.jsonl":
        return "冻结语料 v4（74,912 条 / 82,843 target；大文件，本地保留，不入库）"
    if rel == "items.final.report.json":
        return "冻结语料构成报告（tracked）"
    if rel == "items.native.manifest.json":
        return "原生四元组构建清单（tracked）"
    if rel in ("items.jsonl", "items.bilingual.jsonl", "items.native.jsonl", "items.native.slim.jsonl"):
        return "语料构建中间产物（本地，不入库）"
    if rel.endswith(".report.json"):
        return "构建报告（tracked）"
    if rel in ("convert-report.json", "slim-report.json"):
        return "构建报告（tracked）"
    return "数据/构建产物"


def schema_of(rel):
    if rel in ("splits/train.jsonl", "splits/train.jsonl.gz", "splits/validation.jsonl",
               "splits/validation.jsonl.gz", "splits/test.jsonl", "splits/test.jsonl.gz",
               "zh-supplement/items.jsonl", "zh-supplement/items.jsonl.gz",
               "splits/benchmark.jsonl", "splits/benchmark.jsonl.gz",
               "splits/benchmark-dataset/benchmark.jsonl", "splits/benchmark-dataset/benchmark.jsonl.gz"):
        return "general-decision-items/0.5"
    if rel in ("jev-probs.jsonl", "jev-probs.jsonl.gz"):
        return "jev-probs/1"
    if rel in ("target-types.jsonl", "target-types.jsonl.gz"):
        return "target-types/1"
    if rel == "splits/split-manifest.json":
        return "split-manifest/0.5"
    if rel.startswith("splits/benchmark-dataset/"):
        return BENCH_PKG_SCHEMA
    return None


def generator_of(rel):
    if rel in ("splits/train.jsonl", "splits/train.jsonl.gz", "splits/validation.jsonl",
               "splits/validation.jsonl.gz", "splits/test.jsonl", "splits/test.jsonl.gz"):
        return "datasets/general/data/splits/split.py"
    if rel in ("jev-probs.jsonl", "jev-probs.jsonl.gz"):
        return "datasets/general/jev_fill.py probs-public"
    if rel in ("target-types.jsonl", "target-types.jsonl.gz"):
        return "datasets/general/target_types.py"
    if rel.startswith("zh-supplement/items"):
        return "build_supp.py（记录见 data/zh-supplement/manifest.json）"
    if rel.startswith("splits/benchmark"):
        return "datasets/general/data/splits/split.py + package_benchmark.py"
    if rel == "splits/split-manifest.json":
        return "datasets/general/data/splits/split.py"
    if rel == "items.final.jsonl":
        return "datasets/general/data/splits/build_corpus.py"
    if rel == "items.final.report.json":
        return "datasets/general/report_corpus.py"
    if rel == "items.native.jsonl":
        return "datasets/general/convert.py --native"
    if rel == "items.native.slim.jsonl":
        return "datasets/general/slim.py build"
    if rel == "items.native.manifest.json" or rel == "items.native.report.json":
        return "datasets/general/convert.py --native"
    if rel == "items.jsonl":
        return "datasets/general/convert.py（模板题线，已退役对照）"
    if rel == "items.bilingual.jsonl" or rel == "items.bilingual.report.json":
        return "datasets/general/merge.py（早期双语版本）"
    if rel == "convert-report.json":
        return "datasets/general/convert.py"
    if rel == "slim-report.json":
        return "datasets/general/slim.py"
    if rel.startswith("jev/"):
        return "jev 概率补全流水线（jev_fill.py / ask.py 等）"
    return None


def visibility_of(rel):
    if rel.startswith("splits/benchmark-dataset/"):
        return "private_holdout"
    if rel in ("splits/benchmark.jsonl", "splits/benchmark.jsonl.gz"):
        return "private_holdout"
    if rel.startswith("splits/train") or rel.startswith("splits/validation") or rel.startswith("splits/test"):
        return "public"
    return "sidecar"


def repo_policy_of(rel, tracked):
    hosted = HOSTED.get(rel)
    if hosted:
        return "hf_public" if hosted[0] == "public" else "hf_holdout"
    if tracked:
        return "keep_in_repo"
    return "local_only"


def count_lines_for(path):
    name = path.name
    if name.endswith(".jsonl") or name.endswith(".jsonl.gz"):
        return jsonl_lines(path)
    if name.endswith(".json"):
        text = path.read_text(encoding="utf-8")
        return len(text.split(NL)) - (1 if text.endswith(NL) else 0)
    if path.suffix in (".py", ".md"):
        text = path.read_text(encoding="utf-8")
        return len(text.split(NL)) - (1 if text.endswith(NL) else 0)
    return None


# ---------------------------------------------------------------- inventory

def build_inventory():
    tracked = git_tracked("data")
    entries = []
    for path in sorted(p for p in DATA.rglob("*") if p.is_file()):
        rel_data = path.relative_to(DATA).as_posix()
        if rel_data == "MANIFEST.json":
            continue
        if rel_data.startswith("hf-export/"):
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix in (".pyc", ".pyo"):
            continue
        rel = path.relative_to(REPO).as_posix()
        is_tracked = None if tracked is None else (("data/" + rel_data) in tracked)
        host = HOSTED.get(rel_data)
        entry = {
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "lines": count_lines_for(path),
            "tracked": is_tracked,
            "visibility": visibility_of(rel_data),
            "repo_policy": repo_policy_of(rel_data, is_tracked),
            "schema_version": schema_of(rel_data),
            "target_hf_repo": host[0] if host else None,
            "target_hf_path": host[1] if host else None,
            "role": role_of(rel_data),
            "generated_by": generator_of(rel_data),
        }
        entries.append(entry)

    by_visibility = Counter(entry["visibility"] for entry in entries)
    by_policy = Counter(entry["repo_policy"] for entry in entries)
    bytes_by_visibility = Counter()
    for entry in entries:
        bytes_by_visibility[entry["visibility"]] += entry["bytes"]
    by_path = {entry["path"].split("data/", 1)[1]: entry for entry in entries}

    def lines_of(rel_data):
        return by_path[rel_data]["lines"]

    public_items = sum(lines_of(name) for name in
                       ("splits/train.jsonl.gz", "splits/validation.jsonl.gz", "splits/test.jsonl.gz"))
    sidecar_lines = {"jev-probs": lines_of("jev-probs.jsonl.gz"),
                     "target-types": lines_of("target-types.jsonl.gz")}
    facts = {
        "public_items": public_items,
        "public_targets": sidecar_lines["target-types"] + lines_of("zh-supplement/items.jsonl.gz"),
        "public_targets_note": "口径同 README §4.4：target-types 行数 + 中文补充 target 数",
        "partition_items": {
            "train": lines_of("splits/train.jsonl.gz"),
            "validation": lines_of("splits/validation.jsonl.gz"),
            "test": lines_of("splits/test.jsonl.gz"),
            "benchmark": lines_of("splits/benchmark.jsonl.gz"),
        },
        "supplement_items": lines_of("zh-supplement/items.jsonl.gz"),
        "sidecar_lines": sidecar_lines,
    }
    try:
        split_manifest = read_json(SPLITS / "split-manifest.json")
        facts["split_manifest_counts"] = split_manifest.get("counts")
    except (OSError, json.JSONDecodeError):
        pass
    try:
        final_report = read_json(DATA / "items.final.report.json")
        final = final_report.get("final") or {}
        facts["corpus_items"] = final.get("items")
        facts["corpus_targets"] = final.get("targets")
        facts["corpus_sha256"] = (final_report.get("files") or {}).get("plain", {}).get("sha256")
    except (OSError, json.JSONDecodeError):
        pass

    org = org_slug()
    manifest = {
        "schema": INVENTORY_SCHEMA,
        "dataset_id": DATASET_ID,
        "title": DATASET_TITLE,
        "data_root": "datasets/general/data",
        "scope": "datasets/general/data/**（含 data/splits/**；排除 data/hf-export/**、__pycache__、*.pyc 与本清单自身）",
        "generated_by": "datasets/general/export_hf.py inventory",
        "inventory_command": "uv run --no-project --offline python datasets/general/export_hf.py inventory",
        "export_command": "uv run --no-project --offline python datasets/general/export_hf.py build",
        "verify_command": "uv run --no-project --offline python datasets/general/export_hf.py verify",
        "network": "不联网：只读本地文件，不做任何 HF 调用",
        "determinism": "JSON sort_keys=True / ensure_ascii=False / indent=2 / LF；同一输入两次运行输出逐字节相同",
        "tracked_note": "tracked 是生成时 git index 状态；Lead 执行 HF.md 的 git rm --cached 清单后重跑 inventory 即可刷新（脚本幂等）",
        "visibility_legend": {
            "public": "公开分区主数据（train/test/validation），可公开托管；三区只用于训练/回归，不隐藏任何评测答案",
            "sidecar": "公开面派生的旁挂件、清单与统计（可公开托管；不宣布成为隔离评测集）",
            "private_holdout": "内部保留集及其打包件：只在私有仓库，绝不进入公开仓库/公开 HF/日志",
        },
        "repo_policy_legend": {
            "keep_in_repo": "小体积、可手写/可复算的清单与脚本，继续 tracked",
            "hf_public": "大文件移出 git，托管到 HF 公开数据集仓库",
            "hf_holdout": "内部保留集，移出 git，托管到 HF 私有数据集仓库",
            "local_only": "本机保留的可复算中间产物，既不入库也不上传",
        },
        "hf": {
            "org": org + "（HF_ORG 环境变量可覆盖）",
            "public": {"repo": org + "/" + PUBLIC_REPO,
                       "url": "https://huggingface.co/datasets/" + org + "/" + PUBLIC_REPO,
                       "status": STATUS},
            "holdout": {"repo": org + "/" + HOLDOUT_REPO,
                        "url": "https://huggingface.co/datasets/" + org + "/" + HOLDOUT_REPO,
                        "private": True, "status": STATUS},
        },
        "counts": {
            "files": len(entries),
            "tracked": None if tracked is None else sum(1 for e in entries if e["tracked"]),
            "by_visibility": dict(sorted(by_visibility.items())),
            "by_repo_policy": dict(sorted(by_policy.items())),
            "bytes_total": sum(entry["bytes"] for entry in entries),
            "bytes_by_visibility": dict(sorted(bytes_by_visibility.items())),
        },
        "facts": facts,
        "benchmark_boundary": {
            "items": lines_of("splits/benchmark.jsonl.gz"),
            "source": "datasets/general/data/splits/benchmark.jsonl(.gz)",
            "package": "datasets/general/data/splits/benchmark-dataset/（生产用的私有包）",
            "rule": "公开导出必须对 benchmark 全量成员 id 零命中；导出脚本内置断言（命中即非零退出）",
            "public_export": "datasets/general/data/hf-export/private-holdout/（单独目录，不与 public 混放）",
        },
        "gitignore_evidence": gitignore_evidence(),
        "entries": entries,
    }
    return manifest


def cmd_inventory(args):
    manifest = build_inventory()
    write_json(Path(args.out), manifest)
    summary = {
        "command": "inventory",
        "manifest": Path(args.out).relative_to(REPO).as_posix(),
        "manifest_sha256": sha256_file(Path(args.out)),
        "files": manifest["counts"]["files"],
        "counts_by_visibility": manifest["counts"]["by_visibility"],
        "counts_by_repo_policy": manifest["counts"]["by_repo_policy"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- 公开导出：统计与数据卡

SOFT_SHAPES = ("soft", "tie_subset")


def load_classifier():
    """复用 readme_stats.py 的能力维度规则链，保证数据卡与 README 口径一致。"""
    import importlib.util
    path = HERE / "readme_stats.py"
    if not path.is_file():
        raise ExportError("缺少 datasets/general/readme_stats.py，无法复算能力维度")
    spec = importlib.util.spec_from_file_location("general_readme_stats", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify_capability, module.CAPABILITIES


def load_benchmark_ids():
    plain = SPLITS / "benchmark.jsonl"
    compressed = SPLITS / "benchmark.jsonl.gz"
    if plain.is_file():
        source = plain
    elif compressed.is_file():
        source = compressed
    else:
        raise ExportError("缺少内部保留集 benchmark.jsonl(.gz)；无法做公开面零命中断言")
    ids = set()
    for row in iter_jsonl(source):
        ids.add(str(row.get("id")))
    if not ids:
        raise ExportError("内部保留集 id 集合为空")
    return ids


def scan_public(public_dir, benchmark_ids, classify):
    stats = {
        "items": 0, "questions": 0, "targets": 0,
        "by_lang": Counter(), "question_kinds": Counter(), "primitive_items": Counter(),
        "capability": Counter(), "sources": set(),
    }
    per_split = {}
    for name, split, _source in PUBLIC_ITEMS:
        split_stats = {"items": 0, "questions": 0, "targets": 0}
        with open_text(Path(public_dir) / name) as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if str(row.get("id")) in benchmark_ids:
                    raise ExportError("公开导出命中内部保留集成员 id（已中止；按保密约定不打印 id）")
                kinds = set()
                for question in row.get("questions") or []:
                    stats["questions"] += 1
                    split_stats["questions"] += 1
                    kind = str(question.get("kind"))
                    stats["question_kinds"][kind] += 1
                    kinds.add(kind)
                for kind in kinds:
                    stats["primitive_items"][kind] += 1
                targets = row.get("targets") or {}
                stats["targets"] += len(targets)
                split_stats["targets"] += len(targets)
                stats["by_lang"][str(row.get("lang"))] += 1
                source = row.get("source") or {}
                stats["sources"].add(str(source.get("dataset")))
                capability, _rule = classify(row)
                stats["capability"][capability] += 1
                stats["items"] += 1
                split_stats["items"] += 1
        per_split[split] = split_stats
    return stats, per_split


def scan_sidecars(public_dir):
    types = {"lines": 0, "shape": Counter(), "route": Counter(), "map": {}}
    for row in iter_jsonl(Path(public_dir) / "target-types.jsonl.gz"):
        types["lines"] += 1
        types["shape"][str(row.get("shape_class"))] += 1
        types["route"][str(row.get("training_route"))] += 1
        types["map"][(str(row.get("item_id")), str(row.get("question_key")))] = str(row.get("shape_class"))
    probs = {"lines": 0, "confidence": Counter(), "new_soft": 0}
    for row in iter_jsonl(Path(public_dir) / "jev-probs.jsonl.gz"):
        probs["lines"] += 1
        probs["confidence"][str(row.get("label_confidence") or "unknown")] += 1
        key = (str(row.get("id")), str(row.get("key")))
        if types["map"].get(key) not in SOFT_SHAPES:
            probs["new_soft"] += 1
    supplement = {"lines": 0, "targets": 0, "sources": set()}
    for row in iter_jsonl(Path(public_dir) / "zh-supplement-items.jsonl.gz"):
        supplement["lines"] += 1
        supplement["targets"] += len(row.get("targets") or {})
        supplement["sources"].add(str((row.get("source") or {}).get("dataset")))
    return types, probs, supplement


def pct(part, whole):
    if not whole:
        return "—"
    return "%.2f%%" % (100.0 * part / whole)


def human_bytes(size):
    if size >= 1000000:
        return "%.1f MB" % (size / 1000000.0)
    if size >= 1000:
        return "%.1f KB" % (size / 1000.0)
    return str(size) + " B"


def render_public_card(ctx):
    """public/README.md 数据卡（HF dataset card）。不含保留集成员 id 或正文。"""
    lines = []
    add = lines.append
    add("---")
    add("license: other")
    add("license_name: proof-of-love-2")
    add("language:")
    add("- en")
    add("- zh")
    add("pretty_name: " + DATASET_TITLE)
    add("size_categories:")
    add("- 10K<n<100K")
    add("tags:")
    add("- decision-making")
    add("- tool-use")
    add("- multiple-choice")
    add("- calibration")
    add("- chinese")
    add("- english")
    add("task_categories:")
    add("- text-classification")
    add("- multiple-choice")
    add("---")
    add("")
    add("# " + DATASET_TITLE + "（general decision）")
    add("")
    add("给**只做“选一个”的小决策模型**用的中英双语数据集：**" + num(ctx["items"]) + " 条 / "
        + num(ctx["questions"]) + " 个问题**。每条是「情境 → 一个或多个类型化问题 → 候选项或量程 → "
        "答案（可带概率分布）」的四元组。三种封闭决策原语：**noul**（是/否）、**choice**（多选一）、"
        "**score**（序数打分）。模型只选择、不生成自由文本，便于低成本、可校准的运行时治理判定。")
    add("")
    add("*English*: a bilingual (en/zh) typed-decision dataset for small closed-choice decision models. "
        "Each item is (state → typed questions → options/scale → answer/probabilities) with three "
        "primitives (noul / choice / score). " + num(ctx["items"]) + " items / " + num(ctx["questions"])
        + " questions across train, validation and test.")
    add("")
    add("本仓库是 Hugging Face 发布副本。数据卡、来源登记、训练侧过滤与字段契约在 GitHub 工程 "
        "PoL-Governance 的 datasets/general/ 下（README / CONTRACT / TRAINING / SOURCES / HF.md）。")
    add("")
    add("## 1. 速览")
    add("")
    add("| 指标 | 数值 |")
    add("|---|---|")
    add("| 条目 / 问题 | " + num(ctx["items"]) + " / " + num(ctx["questions"]) + " |")
    add("| 分区（条目） | train " + num(ctx["per_split"]["train"]["items"])
        + " · validation " + num(ctx["per_split"]["validation"]["items"])
        + " · test " + num(ctx["per_split"]["test"]["items"]) + " |")
    add("| 语言（条目） | en " + num(ctx["by_lang"].get("en", 0)) + " · zh "
        + num(ctx["by_lang"].get("zh", 0)) + " |")
    add("| 原语（问题占比） | choice " + pct(ctx["question_kinds"].get("choice", 0), ctx["questions"])
        + " · noul " + pct(ctx["question_kinds"].get("noul", 0), ctx["questions"])
        + " · score " + pct(ctx["question_kinds"].get("score", 0), ctx["questions"]) + " |")
    capability_bits = []
    for key, name, _desc in ctx["capabilities"]:
        capability_bits.append(name + " " + pct(ctx["capability"].get(key, 0), ctx["items"]))
    add("| 能力维度（条目占比） | " + " · ".join(capability_bits) + " |")
    add("| 采用旁挂 probs 后的可用软分布 | " + pct(ctx["soft_after"], ctx["total_targets"])
        + "（" + num(ctx["soft_after"]) + " / " + num(ctx["total_targets"]) + "） |")
    add("| 来源 | " + str(ctx["source_count"]) + " 个（" + str(ctx["dataset_source_count"])
        + " 个公开数据集 + " + str(ctx["supplement_source_count"]) + " 个中文补充来源） |")
    add("| 格式 | JSONL（UTF-8，一行一条；gzip 发布） |")
    add("")
    add("数字由 datasets/general/export_hf.py 从本仓库发布文件现算；能力维度规则链与软分布口径"
        "同 GitHub README §2 / §4.4（readme_stats.py）。")
    add("")
    add("## 2. 文件")
    add("")
    add("| 文件 | 大小 | 行数 | sha256（前 16 位） | 说明 |")
    add("|---|---:|---:|---|---|")
    for entry in ctx["file_entries"]:
        line_count = "—" if entry["lines"] is None else num(entry["lines"])
        add("| " + entry["path"] + " | " + human_bytes(entry["bytes"]) + " | " + line_count + " | "
            + entry["sha256"][:16] + " | " + ctx["file_notes"][entry["path"]] + " |")
    add("| MANIFEST.json | — | — | 本文件 | 机器可读清单：逐文件 sha256/bytes/行数/可见性/来源；不列出自身 |")
    add("")
    add("完整 sha256、字节数与行数以 MANIFEST.json 为准。")
    add("")
    add("## 3. 记录字段")
    add("")
    add("| 字段 | 说明 |")
    add("|---|---|")
    add("| id | 全局唯一，由（来源, 版本, 行号）确定性派生 |")
    add("| lang | en / zh，保留源语言 |")
    add("| state | 待判断的情境文本 |")
    add("| questions[] | 非空；每项 {key, kind, prompt, options?, scale?, origin?, source_key?} |")
    add("| targets | {<问题 key>: {answer, probs?}}；本数据集 100% 自带 answer |")
    add("| source | 溯源信息：{dataset, revision, config, split, row, license, url} |")
    add("| meta | 转换器信息与质量标记 |")
    add("")
    add("score 题的 probs 键是数字下标 \"0\"..\"max\"（不是 scale.labels 的文字），建输出词表请用 range(min, max+1)。")
    add("")
    add("## 4. 旁挂件字段")
    add("")
    add("- target-types.jsonl.gz（" + num(ctx["types"]["lines"]) + " 行）：item_id / question_key / "
        "shape_class / target_type / training_route / calibration_role / rule_id / provenance_ref 等。"
        "join 键 (item_id, question_key)。")
    add("- jev-probs.jsonl.gz（" + num(ctx["probs"]["lines"]) + " 行）：id / key / qid / kind / answer / "
        "probs / label_confidence / consensus_agree / consensus_n / distribution_semantics / upstream_model。"
        "join 键 (id, key)。")
    add("- zh-supplement-items.jsonl.gz（" + num(ctx["supplement"]["lines"]) + " 行）：只追加进 train 的"
        "中文安全补充条目（字段与主数据相同，另含顶层 origin / group_id）。")
    add("")
    add("## 5. 划分与数据边界")
    add("")
    add("- train 只用于训练；validation 用于选模型/调参；test 只做回归，不用于梯度、教师生成、蒸馏或选阈值。")
    add("- 内部保留集（benchmark）：" + num(ctx["holdout_items"]) + " 条 / " + num(ctx["holdout_questions"])
        + " 问，**不在本仓库**，由维护者放在独立的私有 HF 仓库（en-only），只用于模型定版后的版本对比。")
    add("- 本仓库不含任何保留集成员 id 或正文；发布脚本生成公开面时对 benchmark 全量成员 id 做零命中断言，"
        "命中即中止。")
    add("- 反复依据 test 改方案要在结果卡披露，不要继续称它为未见测试。")
    add("- 硬边界：public 与 private_holdout 物理分开；保留集不进入任何公开分支/fork/PR/日志/截图/训练上下文。")
    add("")
    add("## 6. 已知限制（必读）")
    add("")
    add("1. **软分布 " + pct(ctx["soft_after"], ctx["total_targets"]) + " 是一致子集偏差，不是无偏概率。** "
        "旁挂 probs 来自专用决策模型（mercury-decide 系列）的判定，且只保留“模型判定与语料答案一致”的目标；"
        "与语料答案不一致的目标被系统性排除。不要拿它做校准参照；做蒸馏时按 label_confidence 分层加权"
        "（本发布件：high " + num(ctx["probs"]["confidence"].get("high_consensus", 0))
        + " / medium " + num(ctx["probs"]["confidence"].get("medium_consensus", 0))
        + " / low " + num(ctx["probs"]["confidence"].get("low_consensus", 0)) + "）。")
    add("2. **保留集只防随手复现，不是安全边界。** 切分使用了仓外私盐，防止“公开脚本 + 公开种子”"
        "重建保留集；它不提供密码学保证。评测者不得主动把保留集内容交给训练 Agent。")
    add("3. **能力偏斜。** 阅读 + 数学合计约 71.34%；世界知识 "
        + pct(ctx["capability"].get("world_knowledge", 0), ctx["items"]) + " / 因果·反事实 "
        + pct(ctx["capability"].get("causal_uncertainty", 0), ctx["items"])
        + " 很薄，别指望这份数据单独补这两维。")
    add("4. **保留集 en-only。** 中文答案索引曾在公开 git 历史可达（v5 已永久轮换该批 id），"
        "因此中文不进 benchmark，zh 分项分数不具盲测意义。")
    add("5. **保留集来源均衡导致总分不是自然分布的无偏估计：** benchmark 内单一来源上限 25%，"
        "最大的两个来源在包内合计 50%（语料里占 77.3%），请按来源分层报分。")
    add("6. **来源是教师蒸馏 / 混合行为先验。** 部分 probs 是教师或模型判定，不是人工标注的世界概率；"
        "逐来源许可与署名见 GitHub SOURCES.md 与每条的 source.license。")
    add("7. **test / validation 的分布偏斜：** 社会与人类判断在 test / validation 只有 263 / 115 条"
        "（中文补充按设计只进 train），不要用它们评这一维。")
    add("")
    add("## 7. 来源与许可")
    add("")
    add("- 来源登记（固定 revision、抓取单元、逐来源许可）：GitHub 工程 datasets/general/SOURCES.md 与 sources.json。")
    add("- 发布许可：项目数据许可 Proof of Love2；逐来源许可（apache-2.0 / cc-by-4.0 / mit / cc0-1.0 / "
        "openrail++ 等）保留在每条记录的 source.license 字段，再分发时请保留该字段与来源署名。")
    add("- 概率旁挂件由 inception/mercury-decide 系列模型判定（见 jev-probs 的 upstream_model 字段），"
        "不是人工标注。")
    add("")
    add("## 8. 引用 / Citation")
    add("")
    add("    @misc{pol-general-decision-v5,")
    add("      title        = {PoL General Decision Dataset v5},")
    add("      author       = {{NaturalDAO PoL-Governance contributors}},")
    add("      year         = {2026},")
    add("      howpublished = {Hugging Face dataset},")
    add("      note         = {Version 0.5; " + ctx["repo_url"] + "}")
    add("    }")
    add("")
    add("引用时请固定 revision：用 Hugging Face 页面上的 commit sha（或下载时用 --revision 固定）；数据集版本为 v0.5。")
    add("")
    add("## 9. 复现与校验")
    add("")
    add("- 本仓库所有文件由 GitHub 工程 datasets/general/export_hf.py 生成：离线、确定性、"
        "不含时间戳；同一输入两次构建逐字节一致。")
    add("- 在 GitHub 工程内校验下载副本：")
    add("")
    add("      uv run --no-project --offline python datasets/general/export_hf.py verify --dir <下载目录>")
    add("")
    add("- 不依赖仓库的独立校验（标准库，在本目录运行）：")
    add("")
    add("      import hashlib, json, os")
    add("      manifest = json.load(open(\"MANIFEST.json\", encoding=\"utf-8\"))")
    add("      for entry in manifest[\"files\"]:")
    add("          digest = hashlib.sha256(open(os.path.join(\"\", entry[\"path\"]), \"rb\").read()).hexdigest()")
    add("          assert digest == entry[\"sha256\"], entry[\"path\"]")
    add("      print(\"ok:\", len(manifest[\"files\"]), \"files\")")
    add("")
    add("- 生成命令：")
    add("")
    add("      uv run --no-project --offline python datasets/general/export_hf.py build")
    add("")
    add("本数据卡由 export_hf.py 生成；请勿手改（改生成器或数据后重跑）。")
    return NL.join(lines) + NL


def num(value):
    return format(int(value), ",")


def build_public(export_dir, org, benchmark_ids, classify, capabilities):
    public_dir = Path(export_dir) / "public"
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for name, partition, source_rel in PUBLIC_ITEMS:
        source_gz = REPO / source_rel
        copied = copy_artifact(source_gz, source_gz.with_suffix(""), public_dir / name)
        entries.append({
            "path": name, "bytes": copied["bytes"], "sha256": copied["sha256"],
            "lines": None, "kind": "items", "partition": partition,
            "source": source_rel, "source_mode": copied["mode"],
            "schema_version": "general-decision-items/0.5",
            "generated_by": "datasets/general/data/splits/split.py",
        })
    for name, kind, source_rel, schema_version, generated_by in SIDECARS:
        source_gz = REPO / source_rel
        copied = copy_artifact(source_gz, source_gz.with_suffix(""), public_dir / name)
        entries.append({
            "path": name, "bytes": copied["bytes"], "sha256": copied["sha256"],
            "lines": None, "kind": kind,
            "source": source_rel, "source_mode": copied["mode"],
            "schema_version": schema_version, "generated_by": generated_by,
        })
    supplement_name, supplement_rel, supplement_schema, supplement_by = SUPPLEMENT
    supplement_gz = REPO / supplement_rel
    copied = copy_artifact(supplement_gz, supplement_gz.with_suffix(""), public_dir / supplement_name)
    entries.append({
        "path": supplement_name, "bytes": copied["bytes"], "sha256": copied["sha256"],
        "lines": None, "kind": "supplement",
        "source": supplement_rel, "source_mode": copied["mode"],
        "schema_version": supplement_schema, "generated_by": supplement_by,
    })

    stats, per_split = scan_public(public_dir, benchmark_ids, classify)
    types, probs, supplement = scan_sidecars(public_dir)
    for entry in entries:
        entry["lines"] = jsonl_lines(public_dir / entry["path"])

    soft_before = sum(types["shape"].get(key, 0) for key in SOFT_SHAPES)
    total_targets = types["lines"] + supplement["targets"]
    soft_after = soft_before + probs["new_soft"]

    file_notes = {
        "train.jsonl.gz": "train 分区主数据（训练；含 3,148 条只进 train 的中文安全补充）",
        "validation.jsonl.gz": "validation 分区主数据（选模型、调超参）",
        "test.jsonl.gz": "test 分区主数据（回归测试，不用于调参）",
        "jev-probs.jsonl.gz": "概率旁挂件（按 (id, key) join；一致子集偏差，见 §6）",
        "target-types.jsonl.gz": "target 形态与训练路由旁挂件（按 (item_id, question_key) join）",
        "zh-supplement-items.jsonl.gz": "train-only 中文安全补充 3,148 条（主数据 train 已含；此文件供 README 复算与溯源）",
    }
    ctx = {
        "items": stats["items"],
        "questions": stats["questions"],
        "per_split": per_split,
        "by_lang": stats["by_lang"],
        "question_kinds": stats["question_kinds"],
        "primitive_items": stats["primitive_items"],
        "capability": stats["capability"],
        "capabilities": capabilities,
        "soft_after": soft_after,
        "total_targets": total_targets,
        "types": types,
        "probs": probs,
        "supplement": supplement,
        "source_count": len(stats["sources"]),
        "dataset_source_count": len(stats["sources"] - supplement["sources"]),
        "supplement_source_count": len(supplement["sources"]),
        "holdout_items": jsonl_lines(SPLITS / "benchmark.jsonl.gz"),
        "holdout_questions": 7990,
        "revision_note": "HF commit sha（上传后固定）",
        "repo_url": "https://huggingface.co/datasets/" + org + "/" + PUBLIC_REPO,
        "file_entries": entries,
        "file_notes": file_notes,
    }
    try:
        package_manifest = read_json(BENCH_PKG / "manifest.json")
        counts = package_manifest.get("verifiable_counts") or {}
        if counts.get("questions"):
            ctx["holdout_questions"] = int(counts["questions"])
    except (OSError, json.JSONDecodeError):
        pass

    write_text(public_dir / "README.md", render_public_card(ctx))
    card_sha = sha256_file(public_dir / "README.md")
    entries.append({
        "path": "README.md", "bytes": (public_dir / "README.md").stat().st_size,
        "sha256": card_sha, "lines": None, "kind": "card",
        "source": None, "source_mode": "generated",
        "schema_version": "hf-dataset-card/1",
        "generated_by": "datasets/general/export_hf.py build（render_public_card）",
    })
    entries.sort(key=lambda item: item["path"])

    manifest = {
        "schema": EXPORT_SCHEMA,
        "dataset_id": DATASET_ID,
        "title": DATASET_TITLE,
        "visibility": "public",
        "status": STATUS,
        "hf": {
            "org": org,
            "repo": org + "/" + PUBLIC_REPO,
            "url": "https://huggingface.co/datasets/" + org + "/" + PUBLIC_REPO,
            "revision": None,
            "revision_note": "上传后取 HF commit sha 固定；见 GitHub datasets/general/HF.md 更新记录",
        },
        "generated_by": "datasets/general/export_hf.py build",
        "generate_command": "uv run --no-project --offline python datasets/general/export_hf.py build",
        "verify_command": "uv run --no-project --offline python datasets/general/export_hf.py verify --dir <本目录>",
        "network": "不联网：导出脚本不做任何 HF 调用",
        "determinism": "同一输入两次构建输出逐字节相同；gzip 逐字节复制源文件，不含时间戳",
        "source_manifest": "datasets/general/data/MANIFEST.json",
        "source_repository": "GitHub PoL-Governance datasets/general",
        "license": {
            "project": "Proof of Love2",
            "per_source": "逐来源许可（apache-2.0 / cc-by-4.0 / mit / cc0-1.0 / openrail++ 等）见 SOURCES.md 与每条的 source.license",
        },
        "counts": {
            "items": stats["items"],
            "questions": stats["questions"],
            "targets": stats["targets"],
            "by_split": per_split,
            "by_lang": dict(sorted(stats["by_lang"].items())),
            "by_question_kind": dict(sorted(stats["question_kinds"].items())),
            "by_primitive_items": dict(sorted(stats["primitive_items"].items())),
            "sources": len(stats["sources"]),
            "supplement_sources": len(supplement["sources"]),
            "sidecar_lines": {"jev-probs": probs["lines"], "target-types": types["lines"]},
            "supplement_items": supplement["lines"],
        },
        "soft_distribution": {
            "soft_before_sidecar": soft_before,
            "new_soft_from_sidecar": probs["new_soft"],
            "soft_after": soft_after,
            "total_targets": total_targets,
            "share_after": round(soft_after / total_targets, 6) if total_targets else None,
            "caveat": "一致子集偏差：旁挂只保留模型判定与语料答案一致的目标；不能当无偏概率或校准参照",
        },
        "target_types_routes": dict(sorted(types["route"].items())),
        "target_types_shapes": dict(sorted(types["shape"].items())),
        "probs_label_confidence": dict(sorted(probs["confidence"].items())),
        "files": entries,
        "manifest_note": "本清单不列出自身（避免自引用）；其余每个发布文件的 sha256/bytes/行数都已登记",
        "benchmark_assertion": {
            "status": "pass",
            "benchmark_items": len(benchmark_ids),
            "checked_public_items": stats["items"],
            "intersection": 0,
            "rule": "发布前读 benchmark.jsonl(.gz) 全量 id；公开导出每个条目 id 零命中，命中即非零退出",
        },
    }
    write_json(public_dir / "MANIFEST.json", manifest)
    return {
        "dir": public_dir,
        "manifest": manifest,
        "tree_sha256": tree_digest(public_dir),
        "benchmark_assertion": "pass",
    }


# ---------------------------------------------------------------- 私有保留集导出

HOLDOUT_ROLES = {
    "benchmark.jsonl": "内部保留集明文（自校验用；加载请用 .gz）",
    "benchmark.jsonl.gz": "内部保留集 gzip（加载件）",
    "manifest.json": "包清单（schema pol-internal-benchmark-package/0.1）",
    "README.md": "包数据卡（只含聚合统计）",
    "USAGE.md": "使用说明（红线、预测格式、指标口径、校验）",
    "verify.py": "包完整性校验（标准库、自包含）",
}


def build_holdout(export_dir, org):
    holdout_dir = Path(export_dir) / "private-holdout"
    if holdout_dir.exists():
        shutil.rmtree(holdout_dir)
    holdout_dir.mkdir(parents=True, exist_ok=True)
    package_manifest = read_json(BENCH_PKG / "manifest.json")
    if package_manifest.get("schema") != BENCH_PKG_SCHEMA:
        raise ExportError("私有包 manifest schema 不符：" + str(package_manifest.get("schema")))
    declared = {entry["path"]: entry for entry in package_manifest.get("files", [])}
    entries = []
    for name in HOLDOUT_FILES:
        source = BENCH_PKG / name
        if not source.is_file():
            raise ExportError("缺少私有包文件：" + source.as_posix())
        data = source.read_bytes()
        digest = sha256_bytes(data)
        declared_entry = declared.get(name)
        if declared_entry is not None:
            if digest != declared_entry.get("sha256"):
                raise ExportError("私有包文件 sha256 与包清单不符：" + name)
            if len(data) != declared_entry.get("bytes"):
                raise ExportError("私有包文件字节数与包清单不符：" + name)
        write_bytes(holdout_dir / name, data)
        lines = None
        if name in ("benchmark.jsonl", "benchmark.jsonl.gz"):
            lines = jsonl_lines(holdout_dir / name)
        entries.append({
            "path": name, "bytes": len(data), "sha256": digest, "lines": lines,
            "role": HOLDOUT_ROLES.get(name, ""),
        })
    manifest_path = BENCH_PKG / "manifest.json"
    manifest_sha = sha256_file(manifest_path)
    counts = package_manifest.get("verifiable_counts") or {}
    holdout_manifest = {
        "schema": EXPORT_SCHEMA,
        "dataset_id": DATASET_ID,
        "title": DATASET_TITLE + " · 内部保留集（private holdout）",
        "visibility": "private_holdout",
        "private": True,
        "status": STATUS,
        "warning": "内部盲测保留集：不得公开、不得进入训练/蒸馏/教师造数、不得据其调参；"
                   "只用于模型定版后的版本对比与回归。本目录含保留集样本，禁止提交到任何公开仓库、"
                   "公开日志、截图或训练 Agent 上下文。",
        "hf": {
            "org": org,
            "repo": org + "/" + HOLDOUT_REPO,
            "url": "https://huggingface.co/datasets/" + org + "/" + HOLDOUT_REPO,
            "private": True,
            "revision": None,
            "revision_note": "上传后取 HF commit sha 固定；见 GitHub datasets/general/HF.md 更新记录",
        },
        "generated_by": "datasets/general/export_hf.py build",
        "generate_command": "uv run --no-project --offline python datasets/general/export_hf.py build",
        "verify_command": "python verify.py（在本目录运行；退出码 0=全部通过）",
        "source": "datasets/general/data/splits/benchmark-dataset/（仓库内 gitignored；生产件由 split.py + package_benchmark.py 生成）",
        "package_manifest": {
            "path": "manifest.json",
            "sha256": manifest_sha,
            "schema": BENCH_PKG_SCHEMA,
            "note": "包格式要求的机器清单（verify.py 读取它）；本 HF-MANIFEST.json 额外记录发布布局与校验入口",
        },
        "counts": {
            "items": counts.get("items"),
            "questions": counts.get("questions"),
            "by_lang": counts.get("by_lang"),
            "by_domain": counts.get("by_domain"),
            "by_kind": counts.get("by_kind"),
            "questions_by_kind": counts.get("questions_by_kind"),
            "declared_groups": counts.get("declared_groups"),
        },
        "files": entries,
        "leakage_note": "本清单与包内 README/USAGE/manifest 只含聚合计数与 sha256，不含任何成员 id 或 state 正文。",
        "upload": {
            "repo": org + "/" + HOLDOUT_REPO,
            "private": True,
            "command_hint": "hf upload " + org + "/" + HOLDOUT_REPO + " datasets/general/data/hf-export/private-holdout . "
                            "--repo-type dataset --private",
        },
    }
    write_json(holdout_dir / "HF-MANIFEST.json", holdout_manifest)
    return {
        "dir": holdout_dir,
        "manifest": holdout_manifest,
        "tree_sha256": tree_digest(holdout_dir),
    }


# ---------------------------------------------------------------- 校验

def verify_public_dir(directory):
    directory = Path(directory)
    manifest_path = directory / "MANIFEST.json"
    if not manifest_path.is_file():
        raise ExportError("缺少 " + manifest_path.as_posix())
    manifest = read_json(manifest_path)
    if manifest.get("schema") != EXPORT_SCHEMA or manifest.get("visibility") != "public":
        raise ExportError("不是公开导出清单：" + manifest_path.as_posix())
    problems = []
    checked_lines = 0
    for entry in manifest.get("files", []):
        path = directory / entry["path"]
        if not path.is_file():
            problems.append("缺文件：" + entry["path"])
            continue
        size = path.stat().st_size
        if size != entry.get("bytes"):
            problems.append("字节数不一致：" + entry["path"])
        if sha256_file(path) != entry.get("sha256"):
            problems.append("sha256 不一致：" + entry["path"])
        if entry.get("lines") is not None:
            counted = jsonl_lines(path)
            if counted != entry["lines"]:
                problems.append("行数不一致：" + entry["path"])
            checked_lines += 1
    return {"files": len(manifest.get("files", [])), "lines_checked": checked_lines, "problems": problems}


def verify_holdout_dir(directory):
    directory = Path(directory)
    manifest_path = directory / "HF-MANIFEST.json"
    if not manifest_path.is_file():
        raise ExportError("缺少 " + manifest_path.as_posix())
    manifest = read_json(manifest_path)
    if manifest.get("schema") != EXPORT_SCHEMA or manifest.get("visibility") != "private_holdout":
        raise ExportError("不是私有保留集清单：" + manifest_path.as_posix())
    problems = []
    for entry in manifest.get("files", []):
        path = directory / entry["path"]
        if not path.is_file():
            problems.append("缺文件：" + entry["path"])
            continue
        if path.stat().st_size != entry.get("bytes"):
            problems.append("字节数不一致：" + entry["path"])
        if sha256_file(path) != entry.get("sha256"):
            problems.append("sha256 不一致：" + entry["path"])
        if entry.get("lines") is not None and jsonl_lines(path) != entry["lines"]:
            problems.append("行数不一致：" + entry["path"])
    package_manifest = directory / "manifest.json"
    if not package_manifest.is_file():
        problems.append("缺文件：manifest.json")
    else:
        if sha256_file(package_manifest) != (manifest.get("package_manifest") or {}).get("sha256"):
            problems.append("包清单 sha256 与 HF-MANIFEST 记录不一致：manifest.json")
        declared = read_json(package_manifest)
        for entry in declared.get("files", []):
            path = directory / entry["path"]
            if not path.is_file():
                problems.append("缺包内文件：" + entry["path"])
                continue
            if sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
                problems.append("包内文件与包清单不一致：" + entry["path"])
    return {"files": len(manifest.get("files", [])), "problems": problems}


def run_package_verify(holdout_dir):
    script = Path(holdout_dir) / "verify.py"
    if not script.is_file():
        raise ExportError("缺 verify.py：" + script.as_posix())
    completed = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    return {"exit": completed.returncode,
            "summary": (completed.stdout or "").strip().splitlines()[-1][:200]
                       if (completed.stdout or "").strip() else "",
            "stderr_tail": (completed.stderr or "").strip().splitlines()[-1][:200]
                           if (completed.stderr or "").strip() else ""}


# ---------------------------------------------------------------- 命令

def run_build(export_dir):
    org = org_slug()
    classify, capabilities = load_classifier()
    benchmark_ids = load_benchmark_ids()
    public = build_public(export_dir, org, benchmark_ids, classify, capabilities)
    holdout = build_holdout(export_dir, org)
    return {
        "export_dir": Path(export_dir),
        "org": org,
        "public": {k: v for k, v in public.items() if k != "manifest"},
        "holdout": {k: v for k, v in holdout.items() if k != "manifest"},
        "public_manifest": public["manifest"],
        "holdout_manifest": holdout["manifest"],
    }


def cmd_build(args):
    result = run_build(Path(args.out))
    summary = {
        "command": "build",
        "export_dir": str(Path(args.out).resolve().relative_to(REPO).as_posix()),
        "public_tree_sha256": result["public"]["tree_sha256"],
        "holdout_tree_sha256": result["holdout"]["tree_sha256"],
        "benchmark_assertion": result["public"]["benchmark_assertion"],
        "public_files": [entry["path"] for entry in result["public_manifest"]["files"]],
        "holdout_files": [entry["path"] for entry in result["holdout_manifest"]["files"]],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args):
    target = Path(args.dir) if args.dir is not None else EXPORT
    if not target.exists():
        raise ExportError("目录不存在：" + target.as_posix())
    result = {"command": "verify", "dir": target.as_posix()}
    # 大小写不敏感的文件系统（Windows/macOS）上 MANIFEST.json 与 manifest.json 会互相命中，
    # 因此用目录里的真实文件名做分派，不能直接 is_file() 探测。
    names = {path.name for path in target.iterdir() if path.is_file()}
    if "MANIFEST.json" in names:
        result["public"] = verify_public_dir(target)
    elif "HF-MANIFEST.json" in names:
        result["holdout"] = verify_holdout_dir(target)
    elif (target / "public").is_dir() or (target / "private-holdout").is_dir():
        if (target / "public").is_dir():
            result["public"] = verify_public_dir(target / "public")
        if (target / "private-holdout").is_dir():
            result["holdout"] = verify_holdout_dir(target / "private-holdout")
    else:
        raise ExportError("目录里既没有 MANIFEST.json / HF-MANIFEST.json，也没有 public/ 与 private-holdout/：" + str(target))
    if args.run_package_verify:
        if (target / "private-holdout" / "verify.py").is_file():
            result["package_verify"] = run_package_verify(target / "private-holdout")
        elif (target / "verify.py").is_file():
            result["package_verify"] = run_package_verify(target)
    problems = []
    for key in ("public", "holdout"):
        section = result.get(key)
        if section and section.get("problems"):
            problems.extend(key + "：" + item for item in section["problems"])
    if result.get("package_verify") and result["package_verify"].get("exit") != 0:
        problems.append("package_verify 退出码非零")
    result["status"] = "pass" if not problems else "fail"
    result["problems"] = problems
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


def cmd_all(args):
    manifest_path = Path(args.manifest)
    inventory_manifest = build_inventory()
    write_json(manifest_path, inventory_manifest)
    build_result = run_build(Path(args.out))
    verify_public = verify_public_dir(Path(args.out) / "public")
    verify_holdout = verify_holdout_dir(Path(args.out) / "private-holdout")
    package_verify = run_package_verify(Path(args.out) / "private-holdout")
    problems = []
    problems.extend("public：" + item for item in verify_public["problems"])
    problems.extend("holdout：" + item for item in verify_holdout["problems"])
    if package_verify["exit"] != 0:
        problems.append("私有包 verify.py 退出码 " + str(package_verify["exit"]))
    summary = {
        "command": "all",
        "inventory": {
            "manifest": manifest_path.resolve().relative_to(REPO).as_posix(),
            "manifest_sha256": sha256_file(manifest_path),
            "files": inventory_manifest["counts"]["files"],
            "counts_by_visibility": inventory_manifest["counts"]["by_visibility"],
            "counts_by_repo_policy": inventory_manifest["counts"]["by_repo_policy"],
        },
        "build": {
            "public_tree_sha256": build_result["public"]["tree_sha256"],
            "holdout_tree_sha256": build_result["holdout"]["tree_sha256"],
            "benchmark_assertion": build_result["public"]["benchmark_assertion"],
            "public_files": [entry["path"] for entry in build_result["public_manifest"]["files"]],
            "holdout_files": [entry["path"] for entry in build_result["holdout_manifest"]["files"]],
        },
        "verify": {
            "public": verify_public,
            "holdout": verify_holdout,
            "package_verify": package_verify,
        },
        "status": "pass" if not problems else "fail",
        "problems": problems,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="general 决策数据集 v5：HF 导出、仓库清单与校验（离线、确定性）")
    sub = parser.add_subparsers(dest="command", required=True)

    inventory_parser = sub.add_parser("inventory", help="只读扫描 data/**，写 data/MANIFEST.json")
    inventory_parser.add_argument("--out", type=Path, default=MANIFEST_PATH)
    inventory_parser.set_defaults(func=cmd_inventory)

    build_parser = sub.add_parser("build", help="生成 HF 公开/私有导出")
    build_parser.add_argument("--out", type=Path, default=EXPORT)
    build_parser.set_defaults(func=cmd_build)

    verify_parser = sub.add_parser("verify", help="校验已有导出目录的 sha256/行数")
    verify_parser.add_argument("--dir", type=Path, default=None)
    verify_parser.add_argument("--run-package-verify", action="store_true",
                               help="额外运行私有包内的 verify.py")
    verify_parser.set_defaults(func=cmd_verify)

    all_parser = sub.add_parser("all", help="inventory + build + verify + 私有包自校验")
    all_parser.add_argument("--out", type=Path, default=EXPORT)
    all_parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    all_parser.set_defaults(func=cmd_all)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ExportError as error:
        print("导出失败：" + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
