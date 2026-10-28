#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track B: 决策评分头独立评测脚本 (finetune/eval_decision_scorer.py)

用途
----
为 Track B（候选评分头：LoRA adapter + Linear(hidden->1) pointer head）提供**独立评测入口**：
在任意训练视图 JSONL（validation / test / 自定义）上复算题内 argmax 准确率与分层指标，
并可选导出逐行候选概率，供 finetune/calibrate.py 做温度校准（sha256(rid) 奇偶切半）。

与 Track A 评测口径（finetune/eval_decision.py）对齐
----------------------------------------------------
- 聚合指标键名与语义一致：total / correct / accuracy / by_kind / by_lang /
  by_option_bucket / by_route / skipped_stats / duration_seconds /
  samples_per_second / eval_view / model / adapter；
- accuracy = correct / total，**total 是实际评测行数**（与 Track A 相同：跳过行不计入
  分母，但计数写入 skipped_stats）；
- 跳过口径一致：选项数 > 26、超长 prompt（默认 > 4000 字符，--max-prompt-chars 可调）
  在训练/评测中跳过并计数；> 26 选项与超长 prompt 的优先级也按 Track A 的
  format_prompt_and_answer 顺序处理（先结构校验，再字符数）；
- 额外键（head / template_version / device / dtype / data_build_seconds）只是溯源信息，
  不改变上述键的语义；duration_seconds 只统计**前向评测循环**（数据 tokenize 耗时单列
  data_build_seconds），samples_per_second = total / duration_seconds。

视图构造（与训练完全一致）
--------------------------
直接复用 finetune/train_decision_scorer.py 的 ScorerDataset（分段 tokenize、marker 锚点 =
每选项行 "OP: <label>" 末 token、左侧截断保留选项区等规则全部不变），
本脚本只在其外层增加 Track A 口径的 prompt 字符数过滤（EvalScorerDataset），不重写 tokenize。

评测协议（见 finetune/EVAL-PROTOCOL.md 第 2/3 节）
---------------------------------------------
- validation 用于选模型与温度校准（calibrate.py 按 sha256(rid) 奇偶切 calibration /
  selection 两半）；test 只做回归，不用于梯度、教师生成或阈值选择——脚本按调用方给定
  的视图路径执行，不自动区分分区，分区纪律由流程保证；
- accuracy 是题内 argmax 与 answer_idx 的一致率；>26 选项、超长 prompt 等跳过行
  **不计入分母**但计数写入 skipped_stats（与 Track A 评测协议一致）；
- --seq-len 默认 1536，必须与训练时的 --seq-len 一致（否则样本截断/构造口径会变）。

性能：只算需要位置的分数（省显存）
----------------------------------
不构造 [B, L, vocab] 全量 lm_head logits，也不调用 DecisionScorer.forward 的
output_hidden_states=True（会保留每层 hidden）。实际做法是：
  1) 从 PeftModel/AutoModelForCausalLM 中定位底层 transformer 主干（resolve_transformer）；
  2) 只取 last_hidden_state；
  3) 仅 gather 每行 marker_positions 处的 [B, max_opts, H] hidden，再过 pointer_head
     得到 [B, max_opts] 标量分数；
  4) 题内 masked softmax（无效位填 -1e4）后 argmax。
无法定位主干时回退到 DecisionScorer.forward（更慢更占显存，与训练/周期评测同口径）。
注意：直接调用底层 transformer 时 LoRA 层仍按注入方式生效（单测用小模型 + 随机 LoRA
权重与 DecisionScorer.forward 数值对照，误差 < 1e-5）。

--predictions 输出（供 calibrate.py）
-------------------------------------
JSONL，每行一个 dict（UTF-8，字段顺序固定）：
  rid, kind, lang, num_options, gold_letter, candidate_probs, correct, route,
  answer_idx, pred_letter
其中 candidate_probs 是 {字母: 概率}（仅该题真实选项，A..Z），保留 6 位小数，
归一化误差 < 1e-5；calibrate.py 读取 candidate_probs / gold_letter / rid，
按 sha256(rid) 奇偶切 calibration / selection 两半拟合与复核温度。

skipped_stats 键（含义）
------------------------
- options_gt_26：选项数 > 26（Track A/B 均无法单字母/超长处理）而跳过；
- prompt_too_long：prompt（含 Track A 的答案段字符占位）超过 --max-prompt-chars；
- invalid_answer_idx：answer_idx 缺失、越界或类型非法；
- missing_options / missing_prompt / prompt_without_option_marker：
  ScorerDataset 的对应跳过原因；
- seq_len_too_short_for_options：seq_len 连第一个选项 marker 行都放不下；
- other：ScorerDataset 统计键之外的跳过（如 empty_option_segment）；
- unparseable：JSONL 中无法解析为 JSON object 的行（Track A 同样静默跳过，这里显式计数）；
- total_skipped：以上全部跳过数之和（含 unparseable）。
恒等式：total_read = total + total_skipped。

退出码
------
0 成功；2 参数/数据错误（含 argparse 用法错误、文件缺失、predictions 路径落在仓库内、
无可评测样本）；1 其它异常（依赖缺失、模型加载失败等，原因打印到 stderr，不静默）。

用法示例
--------
python finetune/eval_decision_scorer.py \\
    --eval-view D:/pol2-train/data/general-validation-view.jsonl \\
    --model D:/pol2-train/models/Qwen3-1.7B \\
    --adapter-dir D:/pol2-train/runs/track-b-1.7b/adapter \\
    --head-path D:/pol2-train/runs/track-b-1.7b/scorer_head.pt \\
    --predictions D:/pol2-train/runs/track-b-1.7b/val-preds.jsonl --json

CPU-only 冒烟（随机 head）见 test_eval_decision_scorer.py 与汇报文档；本脚本不依赖网络，
只读本地模型/视图/head 文件。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 项目内部模块：沿用 Track A/B 的公共口径与数据构造（不重写 tokenize / 分层指标）
try:
    from finetune.decision_common import (
        INDEX_TO_LETTER,
        MAX_OPTIONS,
        check_output_dir_guard,
        compute_stratified_metrics,
    )
    from finetune.decision_scorer import (
        MASKED_LOGIT_FILL,
        OPTIONS_SECTION_HEADER,
        TRACK_B_TEMPLATE_VERSION,
        DecisionScorer,
        collate_scorer_batch,
        load_scorer_head,
        masked_softmax,
    )
    from finetune.train_decision_scorer import ScorerDataset
except ImportError:
    # 允许直接在 finetune/ 目录下执行 python eval_decision_scorer.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.decision_common import (
        INDEX_TO_LETTER,
        MAX_OPTIONS,
        check_output_dir_guard,
        compute_stratified_metrics,
    )
    from finetune.decision_scorer import (
        MASKED_LOGIT_FILL,
        OPTIONS_SECTION_HEADER,
        TRACK_B_TEMPLATE_VERSION,
        DecisionScorer,
        collate_scorer_batch,
        load_scorer_head,
        masked_softmax,
    )
    from finetune.train_decision_scorer import ScorerDataset

# torch / transformers / peft 为可选依赖：缺依赖时本模块仍可导入（py_compile / 静态检查），
# 只有 run_evaluation 会报错并返回退出码 1。测试模块在缺依赖时整组 skip。
try:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

# Track A format_prompt_and_answer 在 prompt 后追加的固定后缀（用于对齐字符数口径）
TRACK_A_ANSWER_SUFFIX = "\n\n【答案】\n"
DEFAULT_MAX_PROMPT_CHARS = 4000
DEFAULT_SEQ_LEN = 1536


class EvalDataError(Exception):
    """参数/数据错误：主入口捕获后返回退出码 2。"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track B 决策评分头独立评测脚本 (LoRA adapter + scorer head, 题内 argmax 准确率)"
    )
    parser.add_argument(
        "--eval-view", type=str, required=True,
        help="评测视图 JSONL 路径 (validation / test / 自定义训练视图)",
    )
    parser.add_argument(
        "--model", type=str, default="Qwen/Qwen3-1.7B",
        help="底座模型名称或本地路径 (默认 Qwen/Qwen3-1.7B；推荐本地路径离线加载)",
    )
    parser.add_argument(
        "--adapter-dir", type=str, required=True,
        help="训练产物 adapter 目录 (含 adapter_config.json / adapter_model.* 与默认 scorer_head.pt)",
    )
    parser.add_argument(
        "--head-path", type=str, default=None,
        help="pointer head 路径 (默认 <adapter-dir>/scorer_head.pt)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=16,
        help="评测批次大小 (默认 16；按 token 长度升序组批以减少 padding)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="限制从视图读取的行数 (0 表示全量；与训练脚本 ScorerDataset 同语义，先读行后过滤)",
    )
    parser.add_argument(
        "--max-prompt-chars", type=int, default=DEFAULT_MAX_PROMPT_CHARS,
        help="跳过字符数超过该值的超长 prompt (0=不限制；默认 4000，与 Track A 评测一致)",
    )
    parser.add_argument(
        "--seq-len", type=int, default=DEFAULT_SEQ_LEN,
        help="最大序列长度 (默认 1536，必须与训练时的 --seq-len 一致；超长左侧截断保留选项区)",
    )
    parser.add_argument(
        "--predictions", type=str, default=None,
        help="逐行预测 JSONL 输出路径 (必须在仓库外；供 calibrate.py 温度校准)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="以 JSON 格式向 stdout 输出汇总结果 (stdout 只有 JSON)",
    )
    parser.add_argument(
        "--device", type=str, default="auto", choices=["auto", "cuda", "cpu"],
        help="推理设备 (auto/cuda/cpu，默认 auto：cuda 可用则 cuda，否则 cpu)",
    )
    parser.add_argument(
        "--dtype", type=str, default="auto", choices=["auto", "float16", "float32"],
        help="模型加载精度 (auto：cuda 用 float16、cpu 用 float32；默认 auto)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# 数据：复用 ScorerDataset + Track A 口径的 prompt 字符数过滤
# ---------------------------------------------------------------------------

def track_a_prompt_chars(prompt: Any) -> int:
    """按 Track A 口径计算 prompt 字符数。

    Track A 的 format_prompt_and_answer 先 rstrip 换行，再拼接 "\\n\\n【答案】\\n"，
    并以 len(prompt_prefix) 与 --max-prompt-chars 比较。Track B 输入没有答案段，
    这里加上同样的固定后缀长度，使"同一行是否被 Track A 跳过"与这里判定一致。
    """
    if not isinstance(prompt, str):
        return 0
    return len(prompt.rstrip("\r\n")) + len(TRACK_A_ANSWER_SUFFIX)


def should_skip_prompt_too_long(row: Dict[str, Any], max_prompt_chars: int) -> bool:
    """判断一行是否属于"结构合法但 prompt 超长"（Track A 口径）。

    先按 build_scorer_sample 的检查顺序做轻量结构预检（不 tokenize）：只有本来能进入
    Track B 构造的行才因字符数被跳过；这样 > 26 选项等行仍会记到 options_gt_26，
    与 Track A 的 format_prompt_and_answer 先结构校验、后字符数检查的行为一致。
    """
    if not max_prompt_chars or max_prompt_chars <= 0:
        return False

    options = row.get("options")
    if not options or not isinstance(options, list):
        return False
    if len(options) > MAX_OPTIONS:
        return False
    answer_idx = row.get("answer_idx")
    if not isinstance(answer_idx, int) or isinstance(answer_idx, bool):
        return False
    if not (0 <= answer_idx < len(options)):
        return False
    prompt = row.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return False
    if OPTIONS_SECTION_HEADER not in prompt:
        return False
    return track_a_prompt_chars(prompt) > int(max_prompt_chars)


class EvalScorerDataset(ScorerDataset):
    """ScorerDataset + Track A 口径的超长 prompt 跳过（只增计数，不改样本构造规则）。

    - 复用父类的 JSONL 读取、字段校验与 build_scorer_sample 构造（与训练一致）；
    - 在父类读取完行之后、构造样本之前，按 should_skip_prompt_too_long 过滤并计
      self.prompt_too_long；被过滤行不进入 ScorerDataset.stats 的各类 skipped_*；
    - limit 语义保持父类（限制读取行数），因此 --limit 小样本调试时先截断再过滤。
    """

    def __init__(
        self,
        jsonl_path: Path,
        tokenizer: Any,
        seq_len: int = DEFAULT_SEQ_LEN,
        limit: int = 0,
        max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
    ):
        self.max_prompt_chars = int(max_prompt_chars or 0)
        self.prompt_too_long = 0
        super().__init__(
            jsonl_path=jsonl_path,
            tokenizer=tokenizer,
            seq_len=seq_len,
            limit=limit,
            shuffle_options=False,
        )

    def _load_rows(self) -> None:
        super()._load_rows()
        if self.max_prompt_chars <= 0:
            self.prompt_too_long = 0
            return
        kept: List[Dict[str, Any]] = []
        too_long = 0
        for row in self._rows:
            if should_skip_prompt_too_long(row, self.max_prompt_chars):
                too_long += 1
            else:
                kept.append(row)
        self._rows = kept
        self.prompt_too_long = too_long


def build_skipped_stats(dataset: Any, prompt_too_long: Optional[int] = None) -> Dict[str, int]:
    """把 ScorerDataset.stats + prompt 超长计数汇总成 Track A 风格的 skipped_stats。

    恒等式（dataset 读取到的行）：total_read = total + total_skipped。
    其中 unparseable 计入 total_skipped，因此该恒等式无需再单独加 unparseable。
    """
    stats = dict(getattr(dataset, "stats", {}) or {})
    samples = getattr(dataset, "samples", []) or []
    rows = getattr(dataset, "_rows", []) or []          # 已剔除超长 prompt 行
    if prompt_too_long is None:
        prompt_too_long = int(getattr(dataset, "prompt_too_long", 0))
    prompt_too_long = int(prompt_too_long)

    valid = int(stats.get("valid", len(samples)))
    skipped: Dict[str, int] = {
        "options_gt_26": int(stats.get("skipped_options_gt_26", 0)),
        "prompt_too_long": prompt_too_long,
        "invalid_answer_idx": int(stats.get("skipped_invalid_answer_idx", 0)),
        "missing_options": int(stats.get("skipped_missing_options", 0)),
        "missing_prompt": int(stats.get("skipped_missing_prompt", 0)),
        "prompt_without_option_marker": int(stats.get("skipped_prompt_without_option_marker", 0)),
        "seq_len_too_short_for_options": int(stats.get("skipped_seq_len_too_short_for_options", 0)),
    }
    # rows 已不含 prompt_too_long 行，因此 other 只与 ScorerDataset 已统计的跳过原因做差额
    dataset_skips = (
        skipped["options_gt_26"]
        + skipped["invalid_answer_idx"]
        + skipped["missing_options"]
        + skipped["missing_prompt"]
        + skipped["prompt_without_option_marker"]
        + skipped["seq_len_too_short_for_options"]
    )
    # ScorerDataset 未统计的跳过原因（目前只有 empty_option_segment 等）
    skipped["other"] = max(0, len(rows) - valid - dataset_skips)
    total_read = int(stats.get("total_read", len(rows) + prompt_too_long))
    skipped["unparseable"] = max(0, total_read - len(rows) - prompt_too_long)
    skipped["total_skipped"] = sum(skipped.values())
    return skipped


# ---------------------------------------------------------------------------
# 分批复用：按 token 长度升序组批（只影响顺序，不影响指标）
# ---------------------------------------------------------------------------

def build_batches(samples: Sequence[Dict[str, Any]], batch_size: int) -> List[List[int]]:
    """按 input_ids 长度升序排序后切批，返回每批的原始样本下标列表。

    只影响评测顺序（减少 padding、提高吞吐），不改变任何指标；等长样本保持原始相对
    顺序（稳定排序），因此同一输入的结果可复现。
    """
    if batch_size <= 0:
        raise ValueError(f"batch_size 必须为正整数，收到 {batch_size!r}")
    order = sorted(
        range(len(samples)),
        key=lambda i: (len(samples[i]["input_ids"]), i),
    )
    return [order[offset:offset + batch_size] for offset in range(0, len(order), batch_size)]


# ---------------------------------------------------------------------------
# 省显存前向：只对选项锚点位置取 hidden -> pointer head 分数
# ---------------------------------------------------------------------------

def _looks_like_transformer(module: Any) -> bool:
    """轻量启发式：判断模块是否像 HuggingFace 的 transformer 主干。"""
    if module is None:
        return False
    return hasattr(module, "embed_tokens") or hasattr(module, "layers")


def resolve_transformer(model: Any) -> Optional[Any]:
    """从 PeftModel / AutoModelForCausalLM / AutoModel 中定位底层 transformer 主干。

    支持结构（均只做属性遍历，不加载/执行任何代码）：
      - PeftModel(LoraModel).model           -> AutoModelForCausalLM / AutoModel
      - AutoModelForCausalLM.model           -> transformer 主干
      - AutoModel                            -> 本身即主干
    返回 None 表示无法识别（调用方回退到 DecisionScorer.forward）。
    """
    if model is None:
        return None
    node = model
    seen = set()
    for _ in range(8):
        if id(node) in seen:
            return None
        seen.add(id(node))

        base_model = getattr(node, "base_model", None)
        if base_model is not None and hasattr(base_model, "model"):
            node = base_model.model
            continue

        child = getattr(node, "model", None)
        if hasattr(node, "lm_head") and child is not None:
            return child if _looks_like_transformer(child) else None
        if child is not None and _looks_like_transformer(child):
            return child
        if _looks_like_transformer(node):
            return node
        return None
    return None


def compute_marker_scores(
    scorer: Any,
    input_ids: Any,
    attention_mask: Any,
    marker_positions: Any,
    transformer: Optional[Any] = None,
) -> Any:
    """计算每行各选项位的标量分数 [B, max_opts]（无效位填 MASKED_LOGIT_FILL）。

    省显存写法（与 DecisionScorer.forward 数学等价）：
      transformer(input_ids) -> last_hidden_state [B, L, H]
      hidden.gather(marker_positions) -> [B, max_opts, H]
      pointer_head(...) -> [B, max_opts]
    不会构造 [B, L, vocab] 的 lm_head logits，也不保留各层 hidden。
    找不到 transformer 主干时回退到 DecisionScorer.forward（慢但同口径）。
    """
    if transformer is None:
        transformer = resolve_transformer(getattr(scorer, "base", None))

    if transformer is None:
        scores = scorer(
            input_ids=input_ids,
            attention_mask=attention_mask,
            marker_positions=marker_positions,
        )
        return scores.masked_fill(marker_positions < 0, MASKED_LOGIT_FILL)

    outputs = transformer(
        input_ids=input_ids,
        attention_mask=attention_mask,
        use_cache=False,
        return_dict=True,
    )
    hidden = getattr(outputs, "last_hidden_state", None)
    if hidden is None:
        hidden = outputs[0]

    index = marker_positions.clamp(min=0)
    gather_index = index.unsqueeze(-1).expand(-1, -1, hidden.shape[-1])
    h_marker = hidden.gather(dim=1, index=gather_index)      # [B, max_opts, H]
    scores = scorer.pointer_head(h_marker).squeeze(-1)       # [B, max_opts]
    return scores.masked_fill(marker_positions < 0, MASKED_LOGIT_FILL)


# ---------------------------------------------------------------------------
# 纯函数：评分 / 逐行预测 / 指标聚合（便于纯 CPU 单测）
# ---------------------------------------------------------------------------

def score_batch(scores: Any, option_mask: Any, option_counts: Sequence[int]) -> List[Dict[str, Any]]:
    """对一个 batch 的 [B, max_opts] 分数做题内 masked softmax + argmax。

    返回每行 dict：probs（长度 = 该题真实选项数，和为 1）、pred_idx（真实选项下标）。
    无效选项位（padding / marker=-1）已填 -1e4，softmax 后概率为 0，不会被 argmax 选中。
    """
    probs = masked_softmax(scores, option_mask)
    pred = probs.argmax(dim=-1)
    results: List[Dict[str, Any]] = []
    for row, count in enumerate(option_counts):
        n = int(count)
        results.append({
            "probs": [float(x) for x in probs[row, :n].tolist()],
            "pred_idx": int(pred[row].item()),
        })
    return results


def build_prediction_row(
    meta: Dict[str, Any],
    probs: Sequence[float],
    pred_idx: int,
) -> Dict[str, Any]:
    """构造 --predictions 的逐行记录（字段与 eval_decision.py 兼容，供 calibrate.py）。"""
    num_options = int(meta["num_options"])
    answer_idx = int(meta["answer_idx"])
    letters = [INDEX_TO_LETTER[i] for i in range(num_options)]
    candidate_probs = {letters[i]: round(float(probs[i]), 6) for i in range(num_options)}
    pred_letter = letters[int(pred_idx)]
    gold_letter = INDEX_TO_LETTER[answer_idx]
    return {
        "rid": meta.get("rid"),
        "kind": meta.get("kind", "choice"),
        "lang": meta.get("lang", "zh"),
        "num_options": num_options,
        "gold_letter": gold_letter,
        "candidate_probs": candidate_probs,
        "correct": bool(pred_letter == gold_letter),
        "route": meta.get("route", "classification"),
        "answer_idx": answer_idx,
        "pred_letter": pred_letter,
    }


def aggregate_metrics(
    records: Sequence[Dict[str, Any]],
    skipped_stats: Dict[str, int],
    duration_seconds: float,
    eval_view: str,
    model: str,
    adapter: str,
    head: str,
    data_build_seconds: float = 0.0,
    device: Optional[str] = None,
    dtype: Optional[str] = None,
) -> Dict[str, Any]:
    """聚合为与 eval_decision.py 同键名同口径的汇总指标（total/correct/accuracy/分层）。"""
    metrics = compute_stratified_metrics(list(records))
    total = int(metrics["total"])
    duration = max(0.001, float(duration_seconds))
    metrics["skipped_stats"] = dict(skipped_stats)
    metrics["duration_seconds"] = round(float(duration_seconds), 2)
    metrics["samples_per_second"] = round(total / duration, 2)
    metrics["data_build_seconds"] = round(float(data_build_seconds), 2)
    metrics["eval_view"] = str(eval_view)
    metrics["model"] = str(model)
    metrics["adapter"] = str(adapter)
    metrics["head"] = str(head)
    metrics["template_version"] = TRACK_B_TEMPLATE_VERSION
    if device is not None:
        metrics["device"] = str(device)
    if dtype is not None:
        metrics["dtype"] = str(dtype).replace("torch.", "")
    return metrics


def dump_predictions(path: Path, records: Sequence[Dict[str, Any]]) -> Path:
    """把逐行预测写成 JSONL（UTF-8，LF，每行一个 JSON object）。"""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_path


# ---------------------------------------------------------------------------
# 设备 / 模型加载
# ---------------------------------------------------------------------------

def resolve_device_and_dtype(args: argparse.Namespace) -> Tuple[Any, Any]:
    """解析 --device/--dtype：auto 时 cuda->float16、cpu->float32。"""
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise EvalDataError("--device cuda 但当前环境 torch.cuda.is_available() 为 False")

    if args.dtype == "auto":
        torch_dtype = torch.float16 if device.type == "cuda" else torch.float32
    elif args.dtype == "float16":
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.float32
    if device.type == "cpu" and torch_dtype == torch.float16:
        sys.stderr.write("[warn] CPU 上使用 float16 精度，速度会明显变慢（建议 --dtype float32）\n")
    return device, torch_dtype


def _load_causal_lm(model_path: str, torch_dtype: Any, attn_implementation: Optional[str]) -> Any:
    """加载底座（transformers 5.x 用 dtype=，旧版本回退 torch_dtype=）。"""
    kwargs: Dict[str, Any] = {"trust_remote_code": True}
    if attn_implementation:
        kwargs["attn_implementation"] = attn_implementation
    try:
        return AutoModelForCausalLM.from_pretrained(model_path, dtype=torch_dtype, **kwargs)
    except TypeError:
        return AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch_dtype, **kwargs)


# ---------------------------------------------------------------------------
# 主评测流程
# ---------------------------------------------------------------------------

def run_evaluation(args: argparse.Namespace) -> int:
    """执行评测并输出汇总 JSON/文本；返回退出码（0 成功）。抛出 EvalDataError 表示参数/数据错误。"""
    if not TORCH_AVAILABLE:
        raise RuntimeError(
            "当前环境未安装 torch / transformers / peft！请使用项目的推理虚拟环境运行 "
            "(例如 WSL 的 ~/src/polgov/.venv)。"
        )

    log = (lambda message: None) if args.json else print

    # 1) 路径护栏（先于任何重依赖加载；predictions 必须在仓库外）
    if args.predictions:
        check_output_dir_guard(Path(args.predictions).parent)

    # 2) 参数/数据校验（exit 2）
    eval_view_path = Path(args.eval_view)
    if not eval_view_path.exists():
        raise EvalDataError(f"评测数据文件不存在: {eval_view_path}")
    adapter_dir = Path(args.adapter_dir)
    if not adapter_dir.is_dir():
        raise EvalDataError(f"adapter 目录不存在: {adapter_dir}")
    if not (adapter_dir / "adapter_config.json").exists():
        raise EvalDataError(f"adapter 目录缺少 adapter_config.json: {adapter_dir}")
    head_path = Path(args.head_path) if args.head_path else adapter_dir / "scorer_head.pt"
    if not head_path.exists():
        raise EvalDataError(f"scorer head 文件不存在: {head_path}")
    if args.batch_size <= 0:
        raise EvalDataError(f"--batch-size 必须为正整数，收到 {args.batch_size}")
    if args.seq_len <= 0:
        raise EvalDataError(f"--seq-len 必须为正整数，收到 {args.seq_len}")
    if args.limit < 0:
        raise EvalDataError(f"--limit 不能为负数，收到 {args.limit}")
    if args.max_prompt_chars < 0:
        raise EvalDataError(f"--max-prompt-chars 不能为负数，收到 {args.max_prompt_chars}")

    device, torch_dtype = resolve_device_and_dtype(args)

    log("=" * 60)
    log("PoL-Governance Track B 决策评分头评测")
    log(f"  评测数据: {eval_view_path}")
    log(f"  基座模型: {args.model}")
    log(f"  Adapter: {adapter_dir}")
    log(f"  Scorer Head: {head_path}")
    log(f"  设备: {device} (dtype={str(torch_dtype).replace('torch.', '')})")
    log("=" * 60)

    # 3) Tokenizer（与训练/评测一致）
    log("正在加载 Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    pad_token_id = tokenizer.pad_token_id or 0

    # 4) 数据（复用 ScorerDataset；prompt 超长按 Track A 口径跳过并计数）
    log("正在解析与编码评测数据（分段 tokenize 构造 marker 选项段）...")
    build_start = time.time()
    dataset = EvalScorerDataset(
        jsonl_path=eval_view_path,
        tokenizer=tokenizer,
        seq_len=args.seq_len,
        limit=args.limit,
        max_prompt_chars=args.max_prompt_chars,
    )
    data_build_seconds = time.time() - build_start
    skipped_stats = build_skipped_stats(dataset)
    total_evaluated = len(dataset)
    log(f"可评测样本数: {total_evaluated}，数据构造耗时: {data_build_seconds:.2f}s")
    log(f"跳过统计: {skipped_stats}")
    if total_evaluated == 0:
        raise EvalDataError(
            "没有可评测样本（全部被跳过）；请检查视图格式或 --max-prompt-chars/--seq-len 设置"
        )

    # 5) 底座 + LoRA adapter + pointer head
    log(f"正在加载基座模型: {args.model} ...")
    attn_implementation = "sdpa" if device.type == "cuda" else None
    base_model = _load_causal_lm(args.model, torch_dtype, attn_implementation)
    base_model.to(device)
    base_model.eval()

    hidden_size = getattr(getattr(base_model, "config", None), "hidden_size", None)
    if not hidden_size:
        raise EvalDataError("无法从底座 config 推断 hidden_size（DecisionScorer 需要）")

    log(f"正在加载 LoRA adapter: {adapter_dir} ...")
    model = PeftModel.from_pretrained(base_model, str(adapter_dir))
    model.to(device)
    model.eval()

    scorer = DecisionScorer(model, hidden_size=int(hidden_size))
    head_config = load_scorer_head(scorer.pointer_head, str(head_path))
    head_hidden = head_config.get("hidden_size") if isinstance(head_config, dict) else None
    if head_hidden is not None and int(head_hidden) != int(hidden_size):
        raise EvalDataError(
            f"scorer_head.pt hidden_size={head_hidden} 与底座 hidden_size={hidden_size} 不一致"
        )
    head_template = head_config.get("template_version") if isinstance(head_config, dict) else None
    if head_template and head_template != TRACK_B_TEMPLATE_VERSION:
        sys.stderr.write(
            f"[warn] scorer_head.pt template_version={head_template!r} "
            f"与当前 Track B 模板 {TRACK_B_TEMPLATE_VERSION!r} 不一致，指标可能不可比\n"
        )
    scorer.to(device=device, dtype=torch_dtype)
    scorer.eval()

    fast_transformer = resolve_transformer(getattr(scorer, "base", None))
    if fast_transformer is None:
        sys.stderr.write(
            "[warn] 无法定位 transformer 主干，回退 DecisionScorer.forward（更慢、更占显存）\n"
        )
    else:
        log(f"省显存前向已启用: 只对选项锚点位置取 last hidden -> pointer_head "
            f"({type(fast_transformer).__name__})")
    log(f"DecisionScorer: hidden_size={scorer.hidden_size}, "
        f"head 参数量={sum(p.numel() for p in scorer.pointer_head.parameters())}")

    # 6) 评测循环：按 token 长度升序组批（只影响顺序）
    batches = build_batches(dataset.samples, args.batch_size)
    records: List[Dict[str, Any]] = []
    eval_start = time.time()
    processed = 0
    with torch.no_grad():
        for batch_indices in batches:
            samples = [dataset.samples[i] for i in batch_indices]
            batch = collate_scorer_batch(samples, pad_token_id=pad_token_id)
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            marker_positions = batch["marker_positions"].to(device)
            option_mask = batch["option_mask"].to(device)

            scores = compute_marker_scores(
                scorer,
                input_ids=input_ids,
                attention_mask=attention_mask,
                marker_positions=marker_positions,
                transformer=fast_transformer,
            )
            results = score_batch(scores.float(), option_mask, batch["option_counts"])

            for row, result in enumerate(results):
                meta = {
                    "rid": batch["rids"][row],
                    "kind": batch["kinds"][row],
                    "lang": batch["langs"][row],
                    "route": batch["routes"][row],
                    "num_options": int(batch["option_counts"][row]),
                    "answer_idx": int(batch["answer_idx"][row].item()),
                }
                records.append(build_prediction_row(meta, result["probs"], result["pred_idx"]))
            processed += len(samples)
            if not args.json and (processed % max(1, args.batch_size * 20) < len(samples)
                                  or processed == total_evaluated):
                log(f"已评测: {processed}/{total_evaluated} 条样本...")
    duration_seconds = time.time() - eval_start

    # 7) 聚合 + 导出预测
    metrics = aggregate_metrics(
        records=records,
        skipped_stats=skipped_stats,
        duration_seconds=duration_seconds,
        eval_view=str(eval_view_path),
        model=str(args.model),
        adapter=str(adapter_dir),
        head=str(head_path),
        data_build_seconds=data_build_seconds,
        device=str(device),
        dtype=str(torch_dtype),
    )
    if args.predictions:
        pred_path = dump_predictions(Path(args.predictions), records)
        log(f"逐行预测详情已保存至: {pred_path}")

    # 8) 输出
    if args.json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print("评测汇总报告")
        print("=" * 60)
        print(f"总样本数: {metrics['total']} | 正确数: {metrics['correct']} | "
              f"整体准确率: {metrics['accuracy']:.4f}")
        print(f"评测耗时: {metrics['duration_seconds']}s "
              f"({metrics['samples_per_second']} 样本/秒)，数据构造: {metrics['data_build_seconds']}s")
        print("\n[按题型分层 (by_kind)]:")
        for key, value in metrics["by_kind"].items():
            print(f"  {key:10s}: {value['correct']}/{value['total']} ({value['accuracy']:.4f})")
        print("\n[按语言分层 (by_lang)]:")
        for key, value in metrics["by_lang"].items():
            print(f"  {key:10s}: {value['correct']}/{value['total']} ({value['accuracy']:.4f})")
        print("\n[按选项数分层 (by_option_bucket)]:")
        for key, value in metrics["by_option_bucket"].items():
            print(f"  {key:10s}: {value['correct']}/{value['total']} ({value['accuracy']:.4f})")
        print("\n[按路由分层 (by_route)]:")
        for key, value in metrics["by_route"].items():
            print(f"  {key:16s}: {value['correct']}/{value['total']} ({value['accuracy']:.4f})")
        print("\n[过滤统计]:", metrics["skipped_stats"])
        print("=" * 60)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口：0 成功；2 参数/数据错误；1 其它异常（原因打印到 stderr）。"""
    args = parse_args(argv)
    try:
        return run_evaluation(args)
    except EvalDataError as error:
        sys.stderr.write(f"Error: {error}\n")
        return 2
    except Exception as error:  # noqa: BLE001 - 顶层兜底：打印原因到 stderr，不静默
        sys.stderr.write(f"Unexpected error: {type(error).__name__}: {error}\n")
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
