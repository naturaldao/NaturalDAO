#!/usr/bin/env python3
"""把评测用 checkpoint 复制成「底座 revision 已固定」的隔离副本（仓库外），并记录全部 digest。

为什么需要：seed-43/17/29 的 head.pt 里 base_revision=null，Kev 会跟随 Qwen base 的 HF main。
评测前把 base_revision 固定为训练时使用的 revision（1001bb4d...），否则结论不可复现。
本脚本只改 head.pt 的 base_revision 字段（断言其余字段/张量不变），产出隔离副本与 versions.json。

用法（WSL，cd ~，项目 venv）：
  python benchmark/kev_prefix/pin_checkpoints.py --src-root ~/src/polgov/pol2-release/v1.0.0/weights \
      --out-root /home/wenbo/priv-eval/ckpt --base-revision 1001bb4d826a52d1f399e183466143f4da7b741b \
      --seeds 43 17 29 --kev-hub jaredpalmer/kev-4b@v1.0
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import torch
from huggingface_hub import snapshot_download

BASE_REVISION_DEFAULT = "1001bb4d826a52d1f399e183466143f4da7b741b"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pin_meta(run_dir, base_revision):
    """读 head.pt → 断言张量不变 → 写回 base_revision → 记录前后 sha 与字段。"""
    head_path = Path(run_dir) / "head.pt"
    before_sha = sha256_file(head_path)
    meta = torch.load(head_path, map_location="cpu")
    old = {key: meta.get(key) for key in ("base", "base_revision", "lora", "head_dim",
                                          "option_isolation", "special_embeddings",
                                          "weights_dtype", "temperature", "weights")}
    head_before = {name: tensor.detach().clone() for name, tensor in meta["head"].items()}
    original_base_revision = meta.get("base_revision")
    if original_base_revision is None:
        # 只有未固定的才补；已声明的 revision 优先保留（不覆盖 checkpoint 自带 provenance）
        meta["base_revision"] = base_revision
        torch.save(meta, head_path)
        patched = True
        effective = base_revision
    else:
        patched = False
        effective = original_base_revision
    after = torch.load(head_path, map_location="cpu")
    assert after.get("base_revision") == effective
    for key in ("base", "lora", "head_dim", "option_isolation", "special_embeddings",
                "weights_dtype", "temperature", "weights"):
        assert after.get(key) == old[key], f"patched head.pt changed {key}"
    assert set(after["head"]) == set(head_before), "patched head.pt changed tensor names"
    for name, tensor in head_before.items():
        assert torch.equal(after["head"][name], tensor), f"patched head.pt changed tensor {name}"
    return {"head_sha256_before": before_sha, "head_sha256_after": sha256_file(head_path),
            "base_revision_before": original_base_revision, "base_revision_after": after.get("base_revision"),
            "base_revision_effective": effective,
            "patched": patched, "meta": {key: after.get(key) for key in old},
            "head_tensors": {name: list(tensor.shape) for name, tensor in after["head"].items()}}


def copy_and_pin(src, dst, base_revision):
    dst = Path(dst)
    if dst.exists():
        raise SystemExit(f"refusing to overwrite existing {dst}")
    shutil.copytree(src, dst)
    record = pin_meta(dst, base_revision)
    record["files"] = {path.name: sha256_file(path) for path in sorted(dst.iterdir()) if path.is_file()}
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-root", type=Path, required=True, help="pol2-release weights dir (seed-43/17/29)")
    parser.add_argument("--out-root", type=Path, required=True, help="isolated pinned copies (outside repo)")
    parser.add_argument("--base-revision", default=BASE_REVISION_DEFAULT)
    parser.add_argument("--seeds", nargs="+", default=["43", "17", "29"])
    parser.add_argument("--kev-hub", default="jaredpalmer/kev-4b@v1.0")
    args = parser.parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    versions = {"schema": "kev-prefix-versions/1", "base_revision_pinned": args.base_revision,
                "base": "Qwen/Qwen3.5-4B-Base", "checkpoints": {}}
    for seed in args.seeds:
        src = args.src_root / f"seed-{seed}"
        if not src.is_dir():
            raise SystemExit(f"missing {src}")
        record = copy_and_pin(src, args.out_root / f"seed-{seed}", args.base_revision)
        record["source"] = str(src)
        versions["checkpoints"][f"seed-{seed}"] = record
    if args.kev_hub:
        # 原版：Hub 快照 → 隔离副本（若 head.pt 也未固定底座，一并固定）
        hub, _, revision = args.kev_hub.partition("@")
        snapshot = Path(snapshot_download(hub, revision=revision or None))
        record = copy_and_pin(snapshot, args.out_root / "kev-original", args.base_revision)
        record["source"] = {"hub": hub, "revision_arg": revision or "main", "snapshot": str(snapshot)}
        versions["checkpoints"]["kev-original"] = record
    (args.out_root / "versions.json").write_text(json.dumps(versions, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    print(json.dumps({name: {"patched": record["patched"],
                             "base_revision_before": record["base_revision_before"],
                             "temperature": record["meta"].get("temperature"),
                             "head_sha256_after": record["head_sha256_after"]}
                      for name, record in versions["checkpoints"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()