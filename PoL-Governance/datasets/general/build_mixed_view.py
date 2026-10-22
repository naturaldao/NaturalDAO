"""把两个训练视图按比例混合成一个新视图（mix-1，确定性，纯标准库）。

用途：通用决策视图（general v5 train view）与专用视图（如 PoL2 pv-1 视图）按
「通用:PoL = 9:1 或 8:2」混合；输出与 manifest 只写仓库外，供训练脚本直接使用。

示例：
    python datasets/general/build_mixed_view.py \
        --base D:/pol2-train/data/general-train-view.jsonl \
        --extra D:/pol2-train/data/pol2-train-view.jsonl \
        --ratio 0.1 --allow-pol2 \
        --out D:/pol2-train/data/mixed-train-view-10pct.jsonl

安全门：
- --out 必须在仓库目录之外；拒绝覆盖输入文件；
- 若 extra 含 src=="pol2-freeze-8705-v1" 行，必须显式 --allow-pol2（且该视图只有在
  POL2 训练授权后才会存在；pv-1 builder 自带 training_approved 门禁）；
- 输入行必须含 rid/prompt/options/answer_idx/kind，缺字段立即报错（不静默跳过）。

口径（mix-1）：
- ratio = 混合后 extra 行占比；extra_count = round(base_count * ratio / (1 - ratio))，
  不足时循环重复（按输入顺序），多余输入只取前 extra_count 行；
- 输出顺序 = 按等距插入（确定性），每行加 "mix_group": "base"|"extra" 便于审计；
- 输出文件逐字节确定性；manifest JSON 记录输入 sha256、行数、实际比例与输出 sha256。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TEMPLATE_VERSION = "mix-1"
REQUIRED_KEYS = ("rid", "prompt", "options", "answer_idx", "kind")
POL2_SRC = "pol2-freeze-8705-v1"


class MixError(ValueError):
    """输入/输出不合法。"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_view(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise MixError(f"输入视图不存在: {path}")
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as error:
                raise MixError(f"{path}:{number}: JSON 解析失败: {error}") from error
            if not isinstance(row, dict):
                raise MixError(f"{path}:{number}: 每行必须是 JSON object")
            missing = [key for key in REQUIRED_KEYS if key not in row]
            if missing:
                raise MixError(f"{path}:{number}: 缺少字段 {missing}")
            rows.append(row)
    if not rows:
        raise MixError(f"{path}: 视图为空")
    return rows


def extra_count_for(base_count: int, ratio: float) -> int:
    """按目标占比计算 extra 行数（四舍五入，至少 1 行）。"""
    if not 0.0 < ratio < 1.0:
        raise MixError(f"ratio 必须在 (0,1) 内，收到 {ratio}")
    if base_count <= 0:
        raise MixError("base 视图为空")
    count = int(round(base_count * ratio / (1.0 - ratio)))
    if count < 1:
        raise MixError("ratio 太小，计算得到 0 行 extra；请提高 ratio 或减少 base")
    return count


def interleave_positions(base_count: int, extra_count: int) -> List[bool]:
    """返回长度 base+extra 的布尔序列，True 表示该位置放 extra（等距插入，确定性）。"""
    total = base_count + extra_count
    result: List[bool] = []
    extras_placed = 0
    for index in range(total):
        # 目标：在第 index 步后，已放置 extra ≈ extra_count * (index+1) / total
        target = int(round(extra_count * (index + 1) / total))
        if extras_placed < extra_count and extras_placed < target:
            result.append(True)
            extras_placed += 1
        else:
            result.append(False)
    # 理论上 extras_placed == extra_count；保底修正
    while extras_placed < extra_count:
        # 把剩余的放到末尾之前（找到最后一个 base 位置）
        for position in range(len(result) - 1, -1, -1):
            if not result[position]:
                result[position] = True
                extras_placed += 1
                break
        else:  # pragma: no cover - 不应发生
            raise MixError("无法放置 extra 行（内部错误）")
    return result


def mix_rows(base_rows: List[Dict[str, Any]], extra_rows: List[Dict[str, Any]],
             ratio: float) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    extra_count = extra_count_for(len(base_rows), ratio)
    # 循环/截断 extra
    if extra_count <= len(extra_rows):
        chosen_extra = extra_rows[:extra_count]
    else:
        chosen_extra: List[Dict[str, Any]] = []
        index = 0
        while len(chosen_extra) < extra_count:
            chosen_extra.append(extra_rows[index % len(extra_rows)])
            index += 1
    positions = interleave_positions(len(base_rows), extra_count)
    output: List[Dict[str, Any]] = []
    base_index = 0
    extra_index = 0
    for is_extra in positions:
        if is_extra:
            row = dict(chosen_extra[extra_index])
            row["mix_group"] = "extra"
            extra_index += 1
        else:
            row = dict(base_rows[base_index])
            row["mix_group"] = "base"
            base_index += 1
        output.append(row)
    stats = {
        "template_version": TEMPLATE_VERSION,
        "base_rows": len(base_rows),
        "extra_rows_input": len(extra_rows),
        "extra_rows_used": extra_count,
        "total_rows": len(output),
        "ratio_requested": round(ratio, 6),
        "ratio_realized": round(extra_count / len(output), 6),
        "base_cycled": extra_count > len(extra_rows),
    }
    return output, stats


def write_output(rows: List[Dict[str, Any]], out_path: Path) -> Tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n"
            data = line.encode("utf-8")
            digest.update(data)
            size += len(data)
            handle.write(line)
    return digest.hexdigest(), size


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_outside_repo(out_path: Path) -> None:
    resolved = out_path.expanduser().resolve()
    root = repo_root()
    try:
        resolved.relative_to(root)
    except ValueError:
        return
    raise MixError(f"拒绝写入仓库目录: {resolved}（请写到仓库外，如 ~/src/polgov/data/）")


def run(args: argparse.Namespace) -> int:
    base_path = Path(args.base)
    extra_path = Path(args.extra)
    out_path = Path(args.out).expanduser()
    ensure_outside_repo(out_path)
    if out_path.exists() and not args.overwrite:
        raise MixError(f"输出已存在: {out_path}（加 --overwrite 覆盖）")
    resolved_out = out_path.resolve()
    for source in (base_path, extra_path):
        if resolved_out == source.expanduser().resolve():
            raise MixError(f"--out 不能覆盖输入文件: {source}")

    base_rows = read_view(base_path)
    extra_rows = read_view(extra_path)
    pol2_rows = sum(1 for row in extra_rows if row.get("src") == POL2_SRC)
    if pol2_rows and not args.allow_pol2:
        raise MixError(
            f"extra 含 {pol2_rows} 行 POL2 冻结数据（src={POL2_SRC}）；"
            "POL2 训练授权确认后才可混合，需显式 --allow-pol2"
        )

    mixed, stats = mix_rows(base_rows, extra_rows, args.ratio)
    stats.update({
        "base_path": str(base_path),
        "extra_path": str(extra_path),
        "base_sha256": sha256_file(base_path),
        "extra_sha256": sha256_file(extra_path),
        "pol2_rows_in_extra": pol2_rows,
        "allow_pol2": bool(args.allow_pol2),
        "seed": args.seed,
    })
    out_sha, out_size = write_output(mixed, out_path)
    stats["output_path"] = str(out_path)
    stats["output_sha256"] = out_sha
    stats["output_bytes"] = out_size
    manifest_path = out_path.with_suffix(out_path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps({**stats, "manifest_path": str(manifest_path)}, ensure_ascii=False)
          if args.json else
          "mixed view: {total_rows} rows (base {base_rows} + extra {extra_rows_used}, "
          "ratio_realized={ratio_realized}) -> {output_path}".format(**stats))
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按比例混合两个训练视图（mix-1，确定性；输出必须在仓库外）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base", required=True, help="基础视图 JSONL（如 general-train-view.jsonl）")
    parser.add_argument("--extra", required=True, help="额外视图 JSONL（如 pol2 pv-1 视图）")
    parser.add_argument("--ratio", type=float, default=0.1,
                        help="混合后 extra 行占比（0<ratio<1，默认 0.1 即 9:1）")
    parser.add_argument("--out", required=True, help="输出 JSONL（必须在仓库外）")
    parser.add_argument("--allow-pol2", action="store_true",
                        help="允许 extra 含 POL2 冻结行（仅在 owner 训练授权后使用）")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的输出")
    parser.add_argument("--seed", type=int, default=20261023, help="保留字段（当前插入确定性，不依赖随机）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出统计")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except MixError as error:
        print(f"mix failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
