"""Track A 决策模型微调与评测公共模块 (finetune/decision_common.py)

提供纯标准库实现的：
1. 字母 A..Z 映射与选项数检查（<=26）；
2. 仓库外输出目录安全护栏（exit 2）；
3. 提示词与答案拼接、completion-only 标签构造与截断；
4. 分层评测指标计算（按 kind, lang, option_bucket, route）；
5. 离线/测试/dry-run 使用的轻量 Stub Tokenizer；
6. 辅助工具（sha256 计算、git commit 提取）。
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
MAX_OPTIONS = len(LETTERS)  # 26
INDEX_TO_LETTER = list(LETTERS)
LETTER_TO_INDEX = {c: i for i, c in enumerate(LETTERS)}


def get_repo_root() -> Path:
    """获取当前仓库根目录（根据本文件路径回溯两级）。"""
    return Path(__file__).resolve().parent.parent


def is_path_inside_repo(
    path: Union[str, Path],
    repo_root: Optional[Union[str, Path]] = None,
) -> bool:
    """检查指定路径是否落在仓库根目录内部（防止训练产物污染 git 仓库）。"""
    if repo_root is None:
        resolved_repo = get_repo_root().resolve()
    else:
        resolved_repo = Path(repo_root).resolve()

    resolved_path = Path(path).resolve()
    if resolved_path == resolved_repo:
        return True
    return resolved_repo in resolved_path.parents


def check_output_dir_guard(
    output_dir: Union[str, Path],
    repo_root: Optional[Union[str, Path]] = None,
) -> Path:
    """护栏：检查 output_dir 是否在仓库内。如果在仓库内，直接 exit 2。"""
    if repo_root is None:
        repo_root = get_repo_root()

    if is_path_inside_repo(output_dir, repo_root):
        msg = (
            f"[GUARD ERROR] output-dir '{output_dir}' 落在仓库内 ({repo_root})！\n"
            f"根据项目安全规范，训练与评测产物必须存放在仓库外部目录（例如 D:/pol2-train/runs/...）。\n"
        )
        sys.stderr.write(msg)
        sys.exit(2)

    return Path(output_dir)


def get_option_count_bucket(num_options: int) -> str:
    """将选项数量分桶，供分层评测分析。"""
    if num_options <= 2:
        return "2"
    elif 3 <= num_options <= 4:
        return "3-4"
    elif 5 <= num_options <= 8:
        return "5-8"
    elif 9 <= num_options <= 26:
        return "9-26"
    else:
        return ">26"


def format_prompt_and_answer(row: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
    """根据训练视图行格式化 prompt 题面和答案字母。

    返回: (prompt_prefix, answer_letter, skip_reason)
    若数据不合法，返回 skip_reason:
      - "options_gt_26": 选项数 > 26
      - "missing_options": 选项列表为空
      - "invalid_answer_idx": answer_idx 不在 [0, len(options)-1]
      - "missing_prompt": prompt 为空
    """
    options = row.get("options")
    if not options or not isinstance(options, list):
        return "", "", "missing_options"

    if len(options) > MAX_OPTIONS:
        return "", "", "options_gt_26"

    answer_idx = row.get("answer_idx")
    if answer_idx is None or not isinstance(answer_idx, int):
        return "", "", "invalid_answer_idx"

    if not (0 <= answer_idx < len(options)):
        return "", "", "invalid_answer_idx"

    prompt = row.get("prompt")
    if not prompt or not isinstance(prompt, str):
        return "", "", "missing_prompt"

    letter = INDEX_TO_LETTER[answer_idx]
    # Track A 规范格式：row.prompt + "\n【答案】\n"
    # 若 prompt 已经以 \n 结尾，避免出现过多空行
    prompt_clean = prompt.rstrip("\r\n")
    prompt_prefix = prompt_clean + "\n\n【答案】\n"

    return prompt_prefix, letter, None


def build_completion_only_sample(
    prompt_token_ids: List[int],
    answer_token_ids: List[int],
    seq_len: int,
) -> Tuple[List[int], List[int], Optional[str]]:
    """构造 completion-only 的 input_ids 与 labels。

    - 答案 token 必须是单 token (len(answer_token_ids) == 1)，否则返回 skip_reason="non_single_token_answer"
    - 若 prompt_tokens + answer_tokens > seq_len，从右侧截断 prompt，保留答案 token
    - labels 数组中 prompt 部分全部设为 -100，只有答案位置保留原始 token id
    """
    if len(answer_token_ids) != 1:
        return [], [], "non_single_token_answer"

    total_len = len(prompt_token_ids) + len(answer_token_ids)
    if total_len > seq_len:
        keep_len = seq_len - len(answer_token_ids)
        if keep_len <= 0:
            return [], [], "seq_len_too_short"
        truncated_prompt_ids = prompt_token_ids[:keep_len]
    else:
        truncated_prompt_ids = prompt_token_ids

    input_ids = truncated_prompt_ids + answer_token_ids
    labels = [-100] * len(truncated_prompt_ids) + answer_token_ids

    return input_ids, labels, None


def compute_stratified_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算评测准确率并按 kind、lang、option_bucket、route 分层统计。

    每个 record 必须包含：
    - correct: bool
    - kind: str (choice / noul / score)
    - lang: str (en / zh / ...)
    - num_options: int
    - route: str (classification / distillation)
    """
    if not records:
        return {
            "total": 0,
            "correct": 0,
            "accuracy": 0.0,
            "by_kind": {},
            "by_lang": {},
            "by_option_bucket": {},
            "by_route": {},
        }

    total = len(records)
    correct_count = sum(1 for r in records if r.get("correct"))
    overall_acc = correct_count / total if total > 0 else 0.0

    def init_group():
        return {"total": 0, "correct": 0, "accuracy": 0.0}

    by_kind: Dict[str, Dict[str, Any]] = {}
    by_lang: Dict[str, Dict[str, Any]] = {}
    by_option_bucket: Dict[str, Dict[str, Any]] = {}
    by_route: Dict[str, Dict[str, Any]] = {}

    for r in records:
        is_corr = bool(r.get("correct"))

        k = str(r.get("kind", "unknown"))
        if k not in by_kind:
            by_kind[k] = init_group()
        by_kind[k]["total"] += 1
        if is_corr:
            by_kind[k]["correct"] += 1

        l = str(r.get("lang", "unknown"))
        if l not in by_lang:
            by_lang[l] = init_group()
        by_lang[l]["total"] += 1
        if is_corr:
            by_lang[l]["correct"] += 1

        b = get_option_count_bucket(r.get("num_options", 0))
        if b not in by_option_bucket:
            by_option_bucket[b] = init_group()
        by_option_bucket[b]["total"] += 1
        if is_corr:
            by_option_bucket[b]["correct"] += 1

        rt = str(r.get("route", "unknown"))
        if rt not in by_route:
            by_route[rt] = init_group()
        by_route[rt]["total"] += 1
        if is_corr:
            by_route[rt]["correct"] += 1

    for d in (by_kind, by_lang, by_option_bucket, by_route):
        for v in d.values():
            v["accuracy"] = round(v["correct"] / v["total"], 4) if v["total"] > 0 else 0.0

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": round(overall_acc, 4),
        "by_kind": by_kind,
        "by_lang": by_lang,
        "by_option_bucket": by_option_bucket,
        "by_route": by_route,
    }


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """计算文件的 SHA256 校验和。"""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return "non_existent_or_not_file"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit(cwd: Optional[Union[str, Path]] = None) -> str:
    """读取当前 git commit 散列值。"""
    if cwd is None:
        cwd = get_repo_root()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


class SimpleStubTokenizer:
    """纯 CPU / 离线单测与 dry-run 备用的简易 Tokenizer。

    保证：
    - 每个大写字母 'A'..'Z' 映射为独立的单个 token id
    - 支持 encode, decode, pad_token_id, eos_token_id
    """

    def __init__(self):
        self.pad_token_id = 0
        self.eos_token_id = 1
        self.unk_token_id = 2
        self.pad_token = "<pad>"
        self.eos_token = "<eos>"
        self.padding_side = "right"
        # 为 A..Z 分配固定的 token id (100..125)
        self._vocab: Dict[str, int] = {
            self.pad_token: 0,
            self.eos_token: 1,
            "<unk>": 2,
        }
        for i, c in enumerate(LETTERS):
            self._vocab[c] = 100 + i
        self._id2token = {v: k for k, v in self._vocab.items()}
        self._next_id = 200

    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        ids: List[int] = []
        for ch in text:
            if ch in self._vocab:
                ids.append(self._vocab[ch])
            else:
                self._vocab[ch] = self._next_id
                self._id2token[self._next_id] = ch
                ids.append(self._next_id)
                self._next_id += 1
        return ids

    def decode(self, token_ids: List[int], skip_special_tokens: bool = False) -> str:
        tokens = []
        for tid in token_ids:
            if tid in self._id2token:
                tok = self._id2token[tid]
                if skip_special_tokens and tok in (self.pad_token, self.eos_token, "<unk>"):
                    continue
                tokens.append(tok)
            else:
                tokens.append("<unk>")
        return "".join(tokens)
