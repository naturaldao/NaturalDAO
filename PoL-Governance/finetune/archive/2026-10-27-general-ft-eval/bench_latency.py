r"""成本/延迟基准（CPU 可跑；GPU 待 owner 开启）。

口径（与 `finetune/bench_latency.py` 契约、`finetune/eval_decision.py` 保持一致）：

- prompt 构造**复用** `finetune.decision_common.format_prompt_and_answer`（与评测同口径，
  含 `\n\n【答案】\n` 后缀），不另写一套模板；
- 跳过规则与 eval_decision 相同：`options_gt_26` 与超长 prompt（`--max-prompt-chars`，0=不限制）
  计入输出 JSON 的 `skipped`；其他原因（missing_options / invalid_answer_idx / missing_prompt）
  只计数并写到 stderr 警告，**不**进入 JSON（避免契约外的字段）；
- 逐 batch 计时：先 warmup `--warmup` 个 batch（不计时），随后对**全部** items 计时；
  per-item 延迟 = 该 batch 墙钟 / 该 batch 实际条数；p50/p95 用 nearest-rank；
- tokens/s = 计时窗口内输入 token 总数（attention_mask 求和，不含 padding）/ 各计时 batch 墙钟之和；
- peak mem：cuda/ROCm 用 `torch.cuda.reset_peak_memory_stats` + `max_memory_allocated`（每个
  batch size 单独 reset，读数即该阶段峰值）；cpu 用 `resource.getrusage` 的 `ru_maxrss` 换算 MB，
  无 `resource` 模块（如 Windows）时为 null。注意 ru_maxrss 是**进程级高水位**，不会随阶段下降，
  因此 CPU 数字是「到目前为止的峰值」而非该阶段独立峰值；
- 输出 `--out` JSON（schema `pol-latency-bench-v1`）**只含聚合数字**，不含 rid / prompt 原文 /
  任何逐例字段；同输入同设备下可复现（无时间戳）。

依赖与边界：

- torch / transformers / peft **只在 `_load_backend` 内部 lazy import**（模块顶层不 import），
  因此无 torch 的普通 Python 也能导入本模块并跑纯逻辑单测；
- 缺依赖或请求 cuda 但不可用时 exit code 2 并给出中文提示（与 calibrate.py 一致）；
- 只做推理，不做任何训练；不读、不写私有保留集；不做联网；
- `--out` 不做「必须落在仓库外」的护栏：本文件只有聚合数字，允许按调用者选择落盘位置；
- 数据非法（空行以外的坏 JSON、非对象行）fail-closed：直接报错 exit 2，不静默跳过。

示例：

    python finetune/bench_latency.py --model /path/Qwen3-1.7B --adapter /path/adapter \
      --eval-view /path/general-validation-view.jsonl --limit 200 --batch-sizes 1,16 \
      --warmup 2 --device auto --max-prompt-chars 4000 --json --out /path/latency.json
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from finetune.decision_common import format_prompt_and_answer
except ImportError:  # 直接以脚本方式运行（python finetune/bench_latency.py）时的回退
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.decision_common import format_prompt_and_answer

SCHEMA = "pol-latency-bench-v1"
# 只输出契约规定的两个跳过原因；其余原因写 stderr，不进入 JSON
SKIPPED_KEYS = ("options_gt_26", "prompt_too_long")
DECIMALS = 3


def percentile_nearest_rank(values: Sequence[float], percentile: float) -> Optional[float]:
    """nearest-rank 百分位：返回排序后第 ceil(p/100 * n) 个值（rank 从 1 开始，越界钳到 [1, n]）。

    - 空序列返回 None；
    - percentile 必须落在 [0, 100]，否则 ValueError；
    - 含 NaN/Inf 时 ValueError（fail-closed，避免把坏计时混进统计）。
    """
    if not 0.0 <= percentile <= 100.0:
        raise ValueError(f"percentile 必须落在 [0, 100]: {percentile}")
    ordered = sorted(float(value) for value in values)
    for value in ordered:
        if not math.isfinite(value):
            raise ValueError("latency 必须有限")
    if not ordered:
        return None
    rank = math.ceil(percentile / 100.0 * len(ordered))
    index = min(max(rank, 1), len(ordered)) - 1
    return ordered[index]


def plan_batches(items: int, batch_size: int) -> List[int]:
    """把 items 条样本按 batch_size 切成若干 batch，返回每个 batch 的实际条数。"""
    if batch_size <= 0:
        raise ValueError(f"batch_size 必须 > 0: {batch_size}")
    if items < 0:
        raise ValueError(f"items 必须 >= 0: {items}")
    full, remainder = divmod(items, batch_size)
    plan = [batch_size] * full
    if remainder:
        plan.append(remainder)
    return plan


def _round_optional(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), DECIMALS)


def summarize_phase(
    latencies_ms: Sequence[float],
    *,
    batch_size: int,
    items: int,
    batches: int,
    warmup_batches: int,
    total_tokens: int,
    total_seconds: float,
    peak_mem_mb: Optional[float] = None,
) -> Dict[str, Any]:
    """把一个 batch size 的计时结果汇总成 `phases[]` 的一项（键顺序即契约顺序）。"""
    if batch_size <= 0:
        raise ValueError(f"batch_size 必须 > 0: {batch_size}")
    if items < 0 or batches < 0 or warmup_batches < 0:
        raise ValueError("items/batches/warmup_batches 必须 >= 0")
    if total_tokens < 0:
        raise ValueError(f"total_tokens 必须 >= 0: {total_tokens}")
    if not math.isfinite(total_seconds) or total_seconds < 0:
        raise ValueError(f"total_seconds 必须有限且 >= 0: {total_seconds}")
    if peak_mem_mb is not None:
        if not math.isfinite(peak_mem_mb) or peak_mem_mb < 0:
            raise ValueError(f"peak_mem_mb 必须有限且 >= 0: {peak_mem_mb}")

    p50 = percentile_nearest_rank(latencies_ms, 50.0)
    p95 = percentile_nearest_rank(latencies_ms, 95.0)
    count = len(latencies_ms)
    mean = sum(float(value) for value in latencies_ms) / count if count else None
    tokens_per_sec = total_tokens / total_seconds if total_seconds > 0 else 0.0

    return {
        "batch_size": int(batch_size),
        "items": int(items),
        "batches": int(batches),
        "warmup_batches": int(warmup_batches),
        "p50_ms": _round_optional(p50),
        "p95_ms": _round_optional(p95),
        "mean_ms": _round_optional(mean),
        "tokens_per_sec": round(float(tokens_per_sec), DECIMALS),
        "peak_mem_mb": _round_optional(peak_mem_mb),
    }


def parse_batch_sizes(text: str) -> List[int]:
    """解析 `--batch-sizes 1,16`；去重保序，非法/非正数 ValueError。"""
    if not str(text).strip():
        raise ValueError("--batch-sizes 不能为空（例如 1,16）")
    parts = [part.strip() for part in str(text).split(",")]
    if any(not part for part in parts):
        raise ValueError(f"--batch-sizes 含空项: {text!r}")
    sizes: List[int] = []
    for part in parts:
        try:
            size = int(part)
        except ValueError as error:
            raise ValueError(f"--batch-sizes 含非法整数: {part!r}") from error
        if size <= 0:
            raise ValueError(f"--batch-sizes 必须为正整数: {size}")
        if size not in sizes:
            sizes.append(size)
    return sizes


def read_eval_view_prompts(
    path: Path,
    limit: int = 0,
    max_prompt_chars: int = 4000,
) -> Tuple[List[str], Dict[str, int], Dict[str, int]]:
    """读取评测视图 JSONL，返回 (prompts, skipped, other_skips)。

    - prompt 一律经 `format_prompt_and_answer` 生成（与 eval_decision 同口径）；
    - skipped 只有 options_gt_26 / prompt_too_long 两个键（恒存在，初值 0）；
    - 其他跳过原因（missing_options / invalid_answer_idx / missing_prompt）进 other_skips；
    - limit > 0 时收满 limit 条即停（与 eval_decision 相同：limit 计的是可用样本）；
    - 坏 JSON / 非对象行 / 负的 limit 或 max_prompt_chars → ValueError（fail-closed）。
    """
    if limit < 0:
        raise ValueError(f"limit 必须 >= 0: {limit}")
    if max_prompt_chars < 0:
        raise ValueError(f"max_prompt_chars 必须 >= 0: {max_prompt_chars}")

    skipped: Dict[str, int] = {key: 0 for key in SKIPPED_KEYS}
    other_skips: Dict[str, int] = {}
    prompts: List[str] = []
    view_path = Path(path)
    with view_path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{view_path}:{number}: invalid JSON: {error}") from error
            if not isinstance(row, dict):
                raise ValueError(f"{view_path}:{number}: each line must be an object")

            prompt_prefix, _letter, skip_reason = format_prompt_and_answer(row)
            if skip_reason:
                if skip_reason in skipped:
                    skipped[skip_reason] += 1
                else:
                    other_skips[skip_reason] = other_skips.get(skip_reason, 0) + 1
                continue
            if max_prompt_chars and len(prompt_prefix) > max_prompt_chars:
                skipped["prompt_too_long"] += 1
                continue

            prompts.append(prompt_prefix)
            if limit > 0 and len(prompts) >= limit:
                break
    return prompts, skipped, other_skips


def read_maxrss_kb() -> Optional[int]:
    """当前进程峰值 RSS（kB）；无 resource 模块或调用失败时返回 None。

    Linux/macOS 的 resource 模块提供 ru_maxrss；Windows 没有该模块（返回 None）。
    macOS 的 ru_maxrss 单位是字节，这里换算成 kB。
    """
    try:
        import resource  # 平台相关；只在 CPU 峰值统计时 lazy import
    except ImportError:
        return None
    getrusage = getattr(resource, "getrusage", None)
    if getrusage is None:
        return None
    try:
        value = int(getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:  # 平台字段异常时宁可为 null，也不伪造数字
        return None
    if sys.platform == "darwin":
        value = int(value / 1024)
    return value


def _sanitize_label(text: str) -> str:
    """把硬件标签压成 `[A-Za-z0-9._-]` 的短串（去掉空白与奇怪字符，长度 <= 120）。"""
    collapsed = "-".join(str(text).split())
    cleaned = "".join(ch for ch in collapsed if ch.isalnum() or ch in "._-/")
    return cleaned.strip("-")[:120]


def describe_hardware(device_type: str, device_name: Optional[str] = None) -> str:
    """硬件标签：操作系统-内核版本-架构[-设备名]，例如 `Windows-11-AMD64`。"""
    labels = [platform.system(), platform.release(), platform.machine()]
    label = "-".join(cleaned for cleaned in (_sanitize_label(part) for part in labels) if cleaned)
    if device_name:
        cleaned = _sanitize_label(device_name)
        if cleaned:
            label = f"{label}-{cleaned}" if label else cleaned
    return label[:120] or "unknown"


def bench_phases(
    backend: Any,
    prompts: Sequence[str],
    batch_sizes: Sequence[int],
    warmup: int = 2,
    clock: Optional[Callable[[], float]] = None,
) -> List[Dict[str, Any]]:
    """对每个 batch size 跑一次 warmup + 计时，返回 `phases` 列表。

    backend 需要满足（真实实现是 `_TorchBackend`，单测用可达的假后端）：

    - `infer(prompts) -> int`：一次前向（内部含 tokenize + forward + 同步），返回该 batch 的
      输入 token 数（不含 padding）；必须阻塞到计算完成；
    - `reset_peak_memory() -> None`、`peak_memory_mb() -> float | None`；
    - `device_type: str`、`device_name: str | None`（供报告使用）。

    计时包含 tokenize 与 forward；wrapper 内部同步（CUDA 下 synchronize）后再取时间。
    warmup 使用计划里的前 `min(warmup, len(plan))` 个 batch（不计时），随后对全部 items 计时。
    """
    if warmup < 0:
        raise ValueError(f"warmup 必须 >= 0: {warmup}")
    if not prompts:
        raise ValueError("没有可用样本（prompts 为空）")
    if clock is None:
        clock = time.perf_counter

    phases: List[Dict[str, Any]] = []
    for batch_size in batch_sizes:
        plan = plan_batches(len(prompts), int(batch_size))
        if not plan:
            continue
        warmup_batches = min(warmup, len(plan))

        backend.reset_peak_memory()

        offset = 0
        for count in plan[:warmup_batches]:
            backend.infer(list(prompts[offset:offset + count]))
            offset += count

        latencies_ms: List[float] = []
        total_tokens = 0
        total_seconds = 0.0
        offset = 0
        for count in plan:
            chunk = list(prompts[offset:offset + count])
            offset += count
            started = clock()
            tokens = int(backend.infer(chunk))
            elapsed = clock() - started
            latencies_ms.append(elapsed * 1000.0 / count)
            total_tokens += max(0, tokens)
            total_seconds += elapsed

        phases.append(summarize_phase(
            latencies_ms,
            batch_size=int(batch_size),
            items=len(prompts),
            batches=len(plan),
            warmup_batches=warmup_batches,
            total_tokens=total_tokens,
            total_seconds=total_seconds,
            peak_mem_mb=backend.peak_memory_mb(),
        ))
    return phases


def build_report(
    *,
    hardware: str,
    device: str,
    model: str,
    adapter: Optional[str],
    limit: int,
    max_prompt_chars: int,
    phases: Sequence[Dict[str, Any]],
    skipped: Dict[str, int],
) -> Dict[str, Any]:
    """组装 `pol-latency-bench-v1` 报告（键顺序即契约顺序，只有聚合数字）。"""
    return {
        "schema": SCHEMA,
        "hardware": hardware,
        "device": str(device),
        "model": str(model),
        "adapter": None if adapter is None else str(adapter),
        "limit": int(limit),
        "max_prompt_chars": int(max_prompt_chars),
        "phases": list(phases),
        "skipped": {key: int(skipped.get(key, 0)) for key in SKIPPED_KEYS},
    }


def _import_torch() -> Any:
    """lazy import torch；缺失时抛 RuntimeError（由 main 统一转成 exit 2）。"""
    try:
        import torch  # noqa: PLC0415 —— 必须 lazy：模块顶层 import 会让无 torch 环境无法跑单测
    except ImportError as error:
        raise RuntimeError(
            "当前环境未安装 torch！真实延迟基准请在装有推理环境的 Python 下运行"
            "（项目仓库外的 venv）；纯逻辑单测不需要 torch。"
        ) from error
    return torch


def resolve_device(torch_module: Any, requested: str) -> Any:
    """auto / cpu / cuda → torch.device；请求 cuda 但不可用时 RuntimeError（不静默降级）。"""
    if requested == "auto":
        return torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError("--device cuda 但当前环境 CUDA/ROCm 不可用")
    return torch_module.device(requested)


class _TorchBackend:
    """真实 torch 推理后端；只在 `_load_backend` 内部构造，模块顶层不 import torch。"""

    def __init__(self, torch_module: Any, tokenizer: Any, model: Any, device: Any) -> None:
        self._torch = torch_module
        self._tokenizer = tokenizer
        self._model = model
        self._device = device

    @property
    def device_type(self) -> str:
        return str(self._device.type)

    @property
    def device_name(self) -> Optional[str]:
        if self._device.type != "cuda":
            return None
        try:
            return str(self._torch.cuda.get_device_name(self._device))
        except Exception:  # 取不到名字不影响计时
            return None

    def infer(self, prompts: List[str]) -> int:
        torch = self._torch
        encoded = self._tokenizer(prompts, padding=True, return_tensors="pt")
        tokens = int(encoded["attention_mask"].sum().item())
        inputs = {key: value.to(self._device) for key, value in encoded.items()}
        with torch.no_grad():
            with torch.amp.autocast(
                device_type=self._device.type,
                dtype=torch.float16,
                enabled=(self._device.type == "cuda"),
            ):
                self._model(**inputs)
        if self._device.type == "cuda":
            torch.cuda.synchronize(self._device)
        return tokens

    def reset_peak_memory(self) -> None:
        if self._device.type == "cuda":
            self._torch.cuda.reset_peak_memory_stats(self._device)

    def peak_memory_mb(self) -> Optional[float]:
        if self._device.type == "cuda":
            return self._torch.cuda.max_memory_allocated(self._device) / (1024.0 * 1024.0)
        kb = read_maxrss_kb()
        return None if kb is None else kb / 1024.0


def _load_backend(args: argparse.Namespace) -> _TorchBackend:
    """加载 tokenizer + 模型（可选 LoRA），返回推理后端。"""
    torch = _import_torch()
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "当前环境未安装 transformers！真实延迟基准需要 transformers（可选 peft）。"
        ) from error

    device = resolve_device(torch, args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"  # 与 eval_decision 一致

    torch_dtype = torch.float16 if device.type == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch_dtype,
        trust_remote_code=True,
    )
    if args.adapter:
        try:
            from peft import PeftModel
        except ImportError as error:
            raise RuntimeError(
                "指定了 --adapter 但当前环境未安装 peft！"
            ) from error
        model = PeftModel.from_pretrained(model, args.adapter)

    model.to(device)
    model.eval()
    return _TorchBackend(torch, tokenizer, model, device)


def run_bench(args: argparse.Namespace) -> Dict[str, Any]:
    """读视图 → 加载模型 → 逐 batch size 计时 → 组装报告。"""
    prompts, skipped, other_skips = read_eval_view_prompts(
        Path(args.eval_view), limit=args.limit, max_prompt_chars=args.max_prompt_chars,
    )
    if not prompts:
        raise ValueError("视图里没有可用样本（全部被跳过）")
    if other_skips:
        detail = ", ".join(f"{key}={value}" for key, value in sorted(other_skips.items()))
        sys.stderr.write(
            f"[bench_latency] 警告: {sum(other_skips.values())} 行因其他原因跳过（{detail}），"
            "未计入 JSON 的 skipped 字段\n"
        )

    batch_sizes = parse_batch_sizes(args.batch_sizes)
    if args.warmup < 0:
        raise ValueError(f"--warmup 必须 >= 0: {args.warmup}")

    backend = _load_backend(args)
    try:
        phases = bench_phases(backend, prompts, batch_sizes, warmup=args.warmup)
        hardware = describe_hardware(backend.device_type, backend.device_name)
        device_type = backend.device_type
    finally:
        close = getattr(backend, "close", None)
        if callable(close):
            close()

    if not phases:
        raise ValueError("没有可计时的 batch（batch-sizes 为空或 items 为 0）")

    return build_report(
        hardware=hardware,
        device=device_type,
        model=str(args.model),
        adapter=None if args.adapter is None else str(args.adapter),
        limit=int(args.limit),
        max_prompt_chars=int(args.max_prompt_chars),
        phases=phases,
        skipped=skipped,
    )


def _format_ms(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.{DECIMALS}f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", required=True, help="基座模型名称或本地路径（如 Qwen3-1.7B）")
    parser.add_argument("--adapter", default=None, help="LoRA 权重目录（可选）")
    parser.add_argument("--eval-view", required=True, type=Path, help="评测视图 JSONL 路径")
    parser.add_argument("--limit", type=int, default=200, help="计时样本上限（0=全量；默认 200）")
    parser.add_argument("--batch-sizes", default="1,16", help="逗号分隔的 batch size 列表（默认 1,16）")
    parser.add_argument("--warmup", type=int, default=2, help="每个 batch size 的预热 batch 数（默认 2）")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto", help="推理设备")
    parser.add_argument("--max-prompt-chars", type=int, default=4000,
                        help="跳过字符数超过该值的超长 prompt（0=不限制；默认 4000）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式向 stdout 输出报告")
    parser.add_argument("--out", required=True, type=Path, help="延迟报告 JSON 输出路径")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_bench(args)
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"bench_latency failed: {error}", file=sys.stderr)
        return 2

    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    out_path = Path(args.out)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    except OSError as error:
        print(f"bench_latency failed: 写入 {out_path} 失败: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"schema={report['schema']} device={report['device']} model={report['model']} "
              f"adapter={report['adapter'] or '(none)'} hardware={report['hardware']}")
        for phase in report["phases"]:
            print(f"batch={phase['batch_size']:>4} items={phase['items']:>6} "
                  f"batches={phase['batches']:>6} warmup={phase['warmup_batches']:>2} "
                  f"p50={_format_ms(phase['p50_ms'])}ms p95={_format_ms(phase['p95_ms'])}ms "
                  f"mean={_format_ms(phase['mean_ms'])}ms "
                  f"tokens/s={phase['tokens_per_sec']:.1f} peak_mem_mb={phase['peak_mem_mb']}")
        print(f"skipped={report['skipped']}")
        print(f"written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
