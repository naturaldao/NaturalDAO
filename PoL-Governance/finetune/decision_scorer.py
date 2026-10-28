#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track B: 候选评分头（pointer/scorer head）核心模块 (finetune/decision_scorer.py)

设计要点（模板版本 tv-1b，详见 finetune/README.md Track B 章节）：
- 输入模板：固定说明 + 【情境】state + 【问题】question + 每选项一行 "OP: <label>"；
  由 row.prompt 按 "【选项】" 从右切一刀取情境/问题段（与 tv-1 字节一致），丢弃字母选项段，
  再拼接 Track B 自己的 marker 选项段。答案不进输入。
- marker 方案：固定 marker 文本 "OP: " 前置于每个选项；分段 tokenize（每选项一个独立
  segment，add_special_tokens=False）拼接成 input_ids；每选项的评分锚点 = 该选项行
  （"OP: <label>"）的最后一个 token。锚点取行末而不是 "OP:" marker 自身，是因为因果
  decoder 的 hidden state 只能看到该位置之前的内容——若锚点放在选项文字之前，评分时
  看不到该选项自身文字，题内 softmax 会退化为位置先验（laya 是双向编码器才能前置 marker）。
- 评分：marker 锚点 hidden -> Linear(hidden->1) 得每选项 scalar；logits[B, max_opts]；
  padding 选项位填 -1e4 后题内 softmax。
- 损失（纯函数）：masked_softmax / masked_ce（硬标签）/ masked_kl（软标签，带温度，
  target 按 p**(1/T) 重整化，等价于教师 logits=log p 的标准 KD 温度）/ masked_mixed_loss
  （(1-lambda)*CE + lambda*KL，仅 distillation 且 soft 有效行启用 KL）。
- 不依赖任何 Qwen 特有 token id；tokenizer 只需提供 encode(text, add_special_tokens=False)
  与 decode，可被 tiny Llama 随机模型 + 简易 stub tokenizer 测试。
- 左侧截断：超长时从最左侧截断，保留完整选项 marker 区间；seq_len 连第一个选项行都放不下
  时跳过该行。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    from finetune.decision_common import MAX_OPTIONS
except ImportError:
    # 允许直接在 finetune/ 目录下执行
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.decision_common import MAX_OPTIONS

# torch 为可选依赖：缺 torch 时本模块仍可导入（数据构造/护栏为纯标准库），
# 仅 DecisionScorer / masked_* / save-load head 需要 torch。
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# 模板常量（tv-1b）
# ---------------------------------------------------------------------------

TRACK_B_TEMPLATE_VERSION = "tv-1b"
OPTIONS_SECTION_HEADER = "【选项】"
OPTION_MARKER_TEXT = "OP"          # 固定 marker 文本（不得依赖任何特有 token id）
OPTION_LINE_PREFIX = "OP: "        # 每选项一行的前缀：'OP: <label>'
MASKED_LOGIT_FILL = -1e4           # padding 选项位的 logits 填充值
FORBIDDEN_INPUT_TOKENS = ("benchmark", "holdout", "private")

MARKER_SCHEME_INFO = {
    "template_version": TRACK_B_TEMPLATE_VERSION,
    "option_marker": OPTION_MARKER_TEXT,
    "option_line_prefix": OPTION_LINE_PREFIX,
    "anchor": "last token of each option line 'OP: <label>' (segmented tokenization)",
    "truncation": "left-truncate, always keep the full option marker region",
}


def check_input_view_guard(view_path: Union[str, Path]) -> Path:
    """护栏：训练/评测视图文件名不得含 benchmark / holdout / private（保留集不进训练器）。"""
    path = Path(view_path)
    lowered = path.name.lower()
    for token in FORBIDDEN_INPUT_TOKENS:
        if token in lowered:
            sys.stderr.write(
                f"[GUARD ERROR] 输入视图文件名 '{path.name}' 含保留集标记 '{token}'！\n"
                f"训练与评测只允许消费公开分区的训练视图（见 datasets/general/TRAINING-VIEW.md）。\n"
            )
            sys.exit(2)
    return path


# ---------------------------------------------------------------------------
# 样本构造（纯数据逻辑，无 torch 依赖）
# ---------------------------------------------------------------------------

def extract_prompt_head(prompt: Any) -> Tuple[Optional[str], Optional[str]]:
    """从 tv-1 渲染 prompt 中切出情境/问题段（【选项】之前的部分，含固定说明）。

    用 rpartition 取最后一个 "【选项】"：情境/问题正文理论上可能包含该字样，
    而真正的选项段永远在末尾。
    返回: (head_text, skip_reason)；skip_reason ∈ {missing_prompt, prompt_without_option_marker}
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return None, "missing_prompt"
    if OPTIONS_SECTION_HEADER not in prompt:
        return None, "prompt_without_option_marker"
    head, _sep, _tail = prompt.rpartition(OPTIONS_SECTION_HEADER)
    return head, None


def normalize_soft(soft: Any, num_options: int) -> Optional[List[float]]:
    """校验并归一化软分布（与 options 对齐）。无效返回 None（调用方回退硬标签）。"""
    if not isinstance(soft, (list, tuple)) or len(soft) != num_options:
        return None
    values: List[float] = []
    for v in soft:
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        if x != x or x in (float("inf"), float("-inf")) or x < 0.0:
            return None
        values.append(x)
    total = sum(values)
    if not (total > 0.0):
        return None
    return [x / total for x in values]


def _encode_segment(tokenizer: Any, text: str) -> List[int]:
    ids = tokenizer.encode(text, add_special_tokens=False)
    if not isinstance(ids, list):
        ids = list(ids)
    return ids


def build_scorer_sample(
    row: Dict[str, Any],
    tokenizer: Any,
    seq_len: int = 1536,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """把一行训练视图构造成 Track B 评分头样本。

    返回 (sample, None) 或 (None, skip_reason)。sample 关键字段：
      input_ids / attention_mask / marker_positions / option_count / answer_idx /
      soft / route / rid（另附 kind/lang/src/template_version 供分层评测与清单）。

    skip_reason ∈ {missing_options, options_gt_26, invalid_answer_idx,
                   missing_prompt, prompt_without_option_marker,
                   seq_len_too_short_for_options, empty_option_segment}
    """
    options = row.get("options")
    if not options or not isinstance(options, list):
        return None, "missing_options"
    num_options = len(options)
    if num_options > MAX_OPTIONS:
        return None, "options_gt_26"

    answer_idx = row.get("answer_idx")
    if not isinstance(answer_idx, int) or isinstance(answer_idx, bool):
        return None, "invalid_answer_idx"
    if not (0 <= answer_idx < num_options):
        return None, "invalid_answer_idx"

    head, skip = extract_prompt_head(row.get("prompt"))
    if skip:
        return None, skip
    assert head is not None

    # 选项展示文字：优先 option_labels，缺失时回退 options 键
    labels_raw = row.get("option_labels")
    if not isinstance(labels_raw, list) or len(labels_raw) != num_options:
        labels = [str(o) for o in options]
    else:
        labels = [str(x) for x in labels_raw]

    route = row.get("route") or "classification"
    soft_used: Optional[List[float]] = None
    if route == "distillation":
        # 仅 distillation 路由消费 soft；无效 soft 由数据集层回退硬标签并计数
        soft_used = normalize_soft(row.get("soft"), num_options)

    # 分段 tokenize：head + 每选项一个 segment（首个选项行不带前导换行）
    head_segment = head + OPTIONS_SECTION_HEADER + "\n"
    ids: List[int] = _encode_segment(tokenizer, head_segment)
    if not ids:
        return None, "missing_prompt"

    marker_positions: List[int] = []
    option_starts: List[int] = []
    for k, label in enumerate(labels):
        line = OPTION_LINE_PREFIX + label
        segment = line if k == 0 else "\n" + line
        seg_ids = _encode_segment(tokenizer, segment)
        if not seg_ids:
            return None, "empty_option_segment"
        option_starts.append(len(ids))
        ids.extend(seg_ids)
        marker_positions.append(len(ids) - 1)

    # 左侧截断：保留完整选项 marker 区间（第一个选项行的全部 token 必须在序列内）
    if len(ids) > seq_len:
        drop = len(ids) - seq_len
        if drop > option_starts[0]:
            return None, "seq_len_too_short_for_options"
        ids = ids[drop:]
        marker_positions = [p - drop for p in marker_positions]

    sample = {
        "rid": row.get("rid") or "unknown_rid",
        "kind": row.get("kind", "choice"),
        "lang": row.get("lang", "zh"),
        "route": route,
        "src": row.get("src"),
        "input_ids": ids,
        "attention_mask": [1] * len(ids),
        "marker_positions": marker_positions,
        "option_count": num_options,
        "answer_idx": answer_idx,
        "soft": soft_used,
        "template_version": TRACK_B_TEMPLATE_VERSION,
    }
    return sample, None


def collate_scorer_batch(
    samples: List[Dict[str, Any]],
    pad_token_id: int = 0,
) -> Dict[str, Any]:
    """批量对齐：右侧 padding input_ids；marker_positions 补 -1；option_mask 标记真实选项。"""
    if not samples:
        raise ValueError("collate_scorer_batch: 空批量")

    max_len = max(len(s["input_ids"]) for s in samples)
    max_opts = max(s["option_count"] for s in samples)

    batch_input_ids: List[List[int]] = []
    batch_attention: List[List[int]] = []
    batch_markers: List[List[int]] = []
    batch_option_mask: List[List[int]] = []
    batch_soft: List[List[float]] = []
    batch_has_soft: List[bool] = []
    batch_answer: List[int] = []

    for s in samples:
        n = s["option_count"]
        inp = list(s["input_ids"])
        pad_len = max_len - len(inp)
        batch_input_ids.append(inp + [pad_token_id] * pad_len)
        batch_attention.append([1] * len(inp) + [0] * pad_len)

        markers = list(s["marker_positions"])
        soft = s.get("soft")
        if soft is None:
            batch_has_soft.append(False)
            soft_row = [0.0] * n
        else:
            batch_has_soft.append(True)
            soft_row = [float(x) for x in soft]
        batch_markers.append(markers + [-1] * (max_opts - n))
        batch_option_mask.append([1] * n + [0] * (max_opts - n))
        batch_soft.append(soft_row + [0.0] * (max_opts - n))
        batch_answer.append(int(s["answer_idx"]))

    rids = [s.get("rid", "unknown_rid") for s in samples]
    option_counts = [s["option_count"] for s in samples]
    kinds = [str(s.get("kind", "choice")) for s in samples]
    langs = [str(s.get("lang", "zh")) for s in samples]
    routes = [str(s.get("route", "classification")) for s in samples]

    if TORCH_AVAILABLE:
        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention, dtype=torch.long),
            "marker_positions": torch.tensor(batch_markers, dtype=torch.long),
            "option_mask": torch.tensor(batch_option_mask, dtype=torch.bool),
            "answer_idx": torch.tensor(batch_answer, dtype=torch.long),
            "soft": torch.tensor(batch_soft, dtype=torch.float32),
            "has_soft": torch.tensor(batch_has_soft, dtype=torch.bool),
            "rids": rids,
            "option_counts": option_counts,
            "kinds": kinds,
            "langs": langs,
            "routes": routes,
        }
    return {
        "input_ids": batch_input_ids,
        "attention_mask": batch_attention,
        "marker_positions": batch_markers,
        "option_mask": batch_option_mask,
        "answer_idx": batch_answer,
        "soft": batch_soft,
        "has_soft": batch_has_soft,
        "rids": rids,
        "option_counts": option_counts,
        "kinds": kinds,
        "langs": langs,
        "routes": routes,
    }


# ---------------------------------------------------------------------------
# 纯函数损失（需要 torch；padding 选项位填 -1e4 后题内归一）
# ---------------------------------------------------------------------------

def _require_torch() -> None:
    if not TORCH_AVAILABLE:
        raise RuntimeError("masked_* 损失函数需要 torch（当前环境未安装）")


def _as_bool_mask(option_mask: Any, ref: Any) -> Any:
    if torch.is_tensor(option_mask):
        return option_mask.to(device=ref.device, dtype=torch.bool)
    return torch.as_tensor(option_mask, dtype=torch.bool, device=ref.device)


def masked_softmax(logits: Any, option_mask: Any, dim: int = -1) -> Any:
    """题内 softmax：无效选项位先填 -1e4 再归一。返回与 logits 同形状的概率张量。"""
    _require_torch()
    logits = logits.float()
    mask = _as_bool_mask(option_mask, logits)
    masked = logits.masked_fill(~mask, MASKED_LOGIT_FILL)
    return torch.softmax(masked, dim=dim)


def masked_ce(logits: Any, answer_idx: Any, option_mask: Any) -> Any:
    """题内 masked 交叉熵：返回每行损失 [B]（无有效选项或答案落在无效位的行置 0）。"""
    _require_torch()
    logits = logits.float()
    mask = _as_bool_mask(option_mask, logits)
    logp = torch.log_softmax(logits.masked_fill(~mask, MASKED_LOGIT_FILL), dim=-1)

    idx = torch.as_tensor(answer_idx, dtype=torch.long, device=logits.device)
    if idx.dim() == 0:
        idx = idx.unsqueeze(0)
    picked = logp.gather(1, idx.clamp(min=0).unsqueeze(1)).squeeze(1)
    answer_ok = mask.gather(1, idx.clamp(min=0).unsqueeze(1)).squeeze(1)
    row_valid = mask.any(dim=-1) & answer_ok
    ce = -picked
    return torch.where(row_valid, ce, torch.zeros_like(ce))


def masked_kl(logits: Any, soft_targets: Any, option_mask: Any, temperature: float = 1.0) -> Any:
    """题内 masked KL(soft_target_T || softmax(z/T))，返回每行 [B]。

    温度处理与标准 KD 一致：教师分布 p 视为 softmax(教师 logits)，其 logits≈log p，
    故 T 温度下 target = p**(1/T) 重整化；学生 logits 除以 T。
    """
    _require_torch()
    if not (isinstance(temperature, (int, float)) and float(temperature) > 0):
        raise ValueError(f"temperature 必须为正数，收到 {temperature!r}")
    temperature = float(temperature)

    logits = logits.float()
    mask = _as_bool_mask(option_mask, logits)
    soft = torch.as_tensor(soft_targets, dtype=torch.float32, device=logits.device)
    if soft.shape != logits.shape:
        raise ValueError(f"soft_targets 形状 {tuple(soft.shape)} 与 logits {tuple(logits.shape)} 不一致")

    logq = torch.log_softmax(logits.masked_fill(~mask, MASKED_LOGIT_FILL) / temperature, dim=-1)

    p = torch.where(mask, soft, torch.zeros_like(soft))
    p_t = p.pow(1.0 / temperature)
    denom = p_t.sum(dim=-1, keepdim=True).clamp_min(1e-12)
    p_t = p_t / denom
    logp_t = torch.log(p_t.clamp_min(1e-12))

    terms = torch.where(p_t > 0, p_t * (logp_t - logq), torch.zeros_like(p_t))
    kl = terms.sum(dim=-1)
    row_valid = mask.any(dim=-1) & (p.sum(dim=-1) > 0)
    return torch.where(row_valid, kl, torch.zeros_like(kl))


def masked_mixed_loss(
    logits: Any,
    answer_idx: Any,
    soft_targets: Any,
    option_mask: Any,
    has_soft: Any,
    lambda_soft: float = 0.3,
    temperature: float = 1.0,
) -> Any:
    """每行混合损失：soft 行 (1-λ)·CE + λ·KL(T)，非 soft 行纯 CE。返回 [B]。"""
    _require_torch()
    ce = masked_ce(logits, answer_idx, option_mask)
    kl = masked_kl(logits, soft_targets, option_mask, temperature=temperature)
    lam = min(max(float(lambda_soft), 0.0), 1.0)
    if torch.is_tensor(has_soft):
        soft_flag = has_soft.to(device=ce.device, dtype=torch.bool)
    else:
        soft_flag = torch.as_tensor(has_soft, dtype=torch.bool, device=ce.device)
    if soft_flag.shape != ce.shape:
        raise ValueError("has_soft 形状与批量不一致")
    return torch.where(soft_flag, (1.0 - lam) * ce + lam * kl, ce)


# ---------------------------------------------------------------------------
# DecisionScorer：base + pointer head
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:
    _ScorerBase = nn.Module
else:  # 允许无 torch 环境导入本模块（py_compile / 静态检查）；实例化时再报错
    _ScorerBase = object


class DecisionScorer(_ScorerBase):  # type: ignore[misc, valid-type]
    """候选评分头：transformer base + Linear(hidden->1) pointer head。

    forward(input_ids, attention_mask, marker_positions) -> logits [B, max_opts]；
    marker_positions 中 -1 为批量 padding 选项位，其 logits 已填 MASKED_LOGIT_FILL。
    """

    def __init__(self, base: Any, hidden_size: Optional[int] = None):
        if not TORCH_AVAILABLE:
            raise RuntimeError("DecisionScorer 需要 torch（当前环境未安装）")
        super().__init__()
        self.base = base
        if hidden_size is None:
            config = getattr(base, "config", None)
            hidden_size = getattr(config, "hidden_size", None)
        if hidden_size is None:
            raise ValueError("无法从 base.config 推断 hidden_size，请显式传入 hidden_size")
        self.hidden_size = int(hidden_size)
        self.pointer_head = nn.Linear(self.hidden_size, 1)

    def forward(self, input_ids: Any, attention_mask: Any = None, marker_positions: Any = None):
        if marker_positions is None:
            raise ValueError("DecisionScorer.forward 需要 marker_positions [B, max_opts]")
        outputs = self.base(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
            use_cache=False,
        )
        hidden = getattr(outputs, "hidden_states", None)
        if hidden is not None:
            hidden = hidden[-1]
        else:
            hidden = outputs.last_hidden_state

        # gather 每个选项锚点的 hidden state（padding 位先 clamp 到 0 再覆盖掩码）
        idx = marker_positions.clamp(min=0)
        gather_idx = idx.unsqueeze(-1).expand(-1, -1, hidden.shape[-1])
        h_marker = hidden.gather(dim=1, index=gather_idx)          # [B, max_opts, H]
        scores = self.pointer_head(h_marker).squeeze(-1)           # [B, max_opts]
        scores = scores.masked_fill(marker_positions < 0, MASKED_LOGIT_FILL)
        return scores


# ---------------------------------------------------------------------------
# head 保存 / 加载辅助
# ---------------------------------------------------------------------------

def save_scorer_head(pointer_head: Any, path: Union[str, Path], config: Optional[Dict[str, Any]] = None) -> Path:
    """保存 pointer head 的 state_dict 与配置到单个 .pt 文件。"""
    _require_torch()
    out_path = Path(path)
    if out_path.parent and str(out_path.parent):
        out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state_dict": pointer_head.state_dict(),
        "config": dict(config or {}),
    }
    torch.save(payload, str(out_path))
    return out_path


def load_scorer_head(pointer_head: Any, path: Union[str, Path], map_location: str = "cpu") -> Dict[str, Any]:
    """把 scorer_head.pt 中的 state_dict 载入给定 head，返回其中保存的配置 dict。"""
    _require_torch()
    payload = torch.load(str(path), map_location=map_location)
    if isinstance(payload, dict) and "state_dict" in payload:
        state = payload["state_dict"]
        config = payload.get("config") or {}
    else:
        state = payload
        config = {}
    pointer_head.load_state_dict(state)
    return config
