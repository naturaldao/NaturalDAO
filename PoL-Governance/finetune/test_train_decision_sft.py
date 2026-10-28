"""Track A 纯 CPU 单元测试 (finetune/test_train_decision_sft.py)

测试覆盖：
1. 字母映射与跳过 >26 选项；
2. completion-only 标签构造与截断；
3. 输出目录安全护栏（仓库内路径拒绝，exit 2）；
4. 评测准确率分层计算（按 kind, lang, option_bucket, route）；
5. dry-run 小样本路径（使用合成数据 + --dry-run，不加载模型，0 权重）；
6. SimpleStubTokenizer 纯 CPU 编码解码验证。

不依赖真实 GPU、不下载任何大模型权重、不读外部大文件，纯离线快速运行 (<30s)。
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# 确保在任何工作目录下均能导入 finetune 包
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 公开仓库的 check.py 在未安装模型依赖的环境里也要能通过：缺依赖时跳过整组测试。
import importlib.util

_MISSING = [name for name in ("torch", "transformers", "peft")
            if importlib.util.find_spec(name) is None]
if _MISSING:
    raise unittest.SkipTest("Track A tests need training deps: missing " + ", ".join(_MISSING))

from finetune.decision_common import (
    INDEX_TO_LETTER,
    LETTER_TO_INDEX,
    LETTERS,
    MAX_OPTIONS,
    SimpleStubTokenizer,
    build_completion_only_sample,
    check_output_dir_guard,
    compute_stratified_metrics,
    format_prompt_and_answer,
    get_option_count_bucket,
    get_repo_root,
    is_path_inside_repo,
)
import finetune.train_decision_sft as train_decision_sft


class TestTrackADecisionSFT(unittest.TestCase):
    """Track A SFT 训练与评测逻辑纯 CPU 单元测试集。"""

    def setUp(self):
        self.repo_root = get_repo_root()

    def test_letter_mapping_and_skip_options_gt_26(self):
        """测试 A..Z 字母映射以及选项超过 26 个时的跳过机制。"""
        # 1. 验证字母表基本常数
        self.assertEqual(len(LETTERS), 26)
        self.assertEqual(INDEX_TO_LETTER[0], "A")
        self.assertEqual(INDEX_TO_LETTER[25], "Z")
        self.assertEqual(LETTER_TO_INDEX["A"], 0)
        self.assertEqual(LETTER_TO_INDEX["Z"], 25)

        # 2. 正常 choice 4 选项
        row_normal = {
            "rid": "item_1#q1",
            "prompt": "【情境】\n测试情境\n\n【问题】\n选择正确动作\n\n【选项】\nA. 动作1\nB. 动作2\nC. 动作3\nD. 动作4",
            "options": ["opt1", "opt2", "opt3", "opt4"],
            "answer_idx": 2,  # 应该对应 'C'
        }
        prompt_prefix, letter, skip_reason = format_prompt_and_answer(row_normal)
        self.assertIsNone(skip_reason)
        self.assertEqual(letter, "C")
        self.assertTrue(prompt_prefix.endswith("【答案】\n"))

        # 3. 边界条件：刚好 26 个选项 (A..Z)
        row_26 = {
            "rid": "item_26#q1",
            "prompt": "26选项题",
            "options": [f"opt_{i}" for i in range(26)],
            "answer_idx": 25,  # 应该对应 'Z'
        }
        prompt_prefix, letter, skip_reason = format_prompt_and_answer(row_26)
        self.assertIsNone(skip_reason)
        self.assertEqual(letter, "Z")

        # 4. 超标条件：27 个选项 (>26)，必须被跳过并标记
        row_27 = {
            "rid": "item_27#q1",
            "prompt": "27选项题",
            "options": [f"opt_{i}" for i in range(27)],
            "answer_idx": 0,
        }
        prompt_prefix, letter, skip_reason = format_prompt_and_answer(row_27)
        self.assertEqual(skip_reason, "options_gt_26")
        self.assertEqual(letter, "")

        # 5. 非法答案下标检查 (answer_idx 越界或为负数)
        row_invalid_idx = {
            "rid": "item_err#q1",
            "prompt": "越界题",
            "options": ["opt1", "opt2"],
            "answer_idx": 5,  # 越界
        }
        _, _, skip_reason_neg = format_prompt_and_answer(row_invalid_idx)
        self.assertEqual(skip_reason_neg, "invalid_answer_idx")

        row_negative_idx = {
            "rid": "item_err#q2",
            "prompt": "负当下标题",
            "options": ["opt1", "opt2"],
            "answer_idx": -1,
        }
        _, _, skip_reason_neg2 = format_prompt_and_answer(row_negative_idx)
        self.assertEqual(skip_reason_neg2, "invalid_answer_idx")

    def test_completion_only_labels_construction(self):
        """测试 completion-only 标签构造：prompt 全部 -100，答案保留 token_id，支持右侧截断。"""
        # 1. 正常无截断场景
        prompt_tokens = [10, 20, 30, 40]
        answer_tokens = [100]  # 单 token 答案
        seq_len = 16

        input_ids, labels, err = build_completion_only_sample(
            prompt_tokens, answer_tokens, seq_len
        )
        self.assertIsNone(err)
        self.assertEqual(input_ids, [10, 20, 30, 40, 100])
        self.assertEqual(labels, [-100, -100, -100, -100, 100])
        self.assertEqual(len(input_ids), len(labels))

        # 2. 截断场景：prompt 过长，保留末尾答案 token，截断 prompt 右侧
        long_prompt_tokens = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # 9 个 token
        answer_tokens = [200]
        seq_len = 5  # 限制最大长为 5

        input_ids, labels, err = build_completion_only_sample(
            long_prompt_tokens, answer_tokens, seq_len
        )
        self.assertIsNone(err)
        # 答案占 1 位，保留 prompt 前 4 位 (1, 2, 3, 4)
        self.assertEqual(input_ids, [1, 2, 3, 4, 200])
        self.assertEqual(labels, [-100, -100, -100, -100, 200])
        self.assertEqual(len(input_ids), 5)

        # 3. 异常场景：答案不是单 token
        multi_token_answer = [200, 201]
        _, _, err_multi = build_completion_only_sample(
            prompt_tokens, multi_token_answer, seq_len
        )
        self.assertEqual(err_multi, "non_single_token_answer")

    def test_output_dir_guard(self):
        """测试输出目录护栏：仓库内路径必须拒绝（exit 2），仓库外路径通过。"""
        # 1. 仓库内部路径
        inside_path_1 = self.repo_root / "finetune" / "runs"
        inside_path_2 = self.repo_root / "runs_temp"

        self.assertTrue(is_path_inside_repo(inside_path_1, self.repo_root))
        self.assertTrue(is_path_inside_repo(inside_path_2, self.repo_root))

        # 验证 check_output_dir_guard 触发 exit 2
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                check_output_dir_guard(inside_path_1, self.repo_root)
            self.assertEqual(cm.exception.code, 2)

        # 2. 仓库外部路径（例如 Windows D:/pol2-train 或系统的 tempfile）
        temp_dir = Path(tempfile.gettempdir())
        if not is_path_inside_repo(temp_dir, self.repo_root):
            self.assertFalse(is_path_inside_repo(temp_dir, self.repo_root))
            valid_path = check_output_dir_guard(temp_dir, self.repo_root)
            self.assertEqual(valid_path, temp_dir)

    def test_eval_accuracy_calculation(self):
        """测试评测指标计算与分层准确率（kind/lang/option_bucket/route）。"""
        records = [
            # 2 选项 choice, zh, classification, 正确
            {"correct": True, "kind": "choice", "lang": "zh", "num_options": 2, "route": "classification"},
            # 4 选项 choice, zh, classification, 错误
            {"correct": False, "kind": "choice", "lang": "zh", "num_options": 4, "route": "classification"},
            # 2 选项 noul, en, classification, 正确
            {"correct": True, "kind": "noul", "lang": "en", "num_options": 2, "route": "classification"},
            # 5 选项 score, en, distillation, 正确
            {"correct": True, "kind": "score", "lang": "en", "num_options": 5, "route": "distillation"},
        ]

        metrics = compute_stratified_metrics(records)

        # 整体指标
        self.assertEqual(metrics["total"], 4)
        self.assertEqual(metrics["correct"], 3)
        self.assertEqual(metrics["accuracy"], 0.75)

        # 按题型 (by_kind)
        self.assertEqual(metrics["by_kind"]["choice"]["total"], 2)
        self.assertEqual(metrics["by_kind"]["choice"]["correct"], 1)
        self.assertEqual(metrics["by_kind"]["choice"]["accuracy"], 0.5)

        self.assertEqual(metrics["by_kind"]["noul"]["total"], 1)
        self.assertEqual(metrics["by_kind"]["noul"]["correct"], 1)
        self.assertEqual(metrics["by_kind"]["noul"]["accuracy"], 1.0)

        self.assertEqual(metrics["by_kind"]["score"]["total"], 1)
        self.assertEqual(metrics["by_kind"]["score"]["correct"], 1)
        self.assertEqual(metrics["by_kind"]["score"]["accuracy"], 1.0)

        # 按语言 (by_lang)
        self.assertEqual(metrics["by_lang"]["zh"]["total"], 2)
        self.assertEqual(metrics["by_lang"]["zh"]["accuracy"], 0.5)
        self.assertEqual(metrics["by_lang"]["en"]["total"], 2)
        self.assertEqual(metrics["by_lang"]["en"]["accuracy"], 1.0)

        # 按选项数分桶 (by_option_bucket)
        # 选项数 2 -> 桶 "2" (共 2 条，全对)
        self.assertEqual(metrics["by_option_bucket"]["2"]["total"], 2)
        self.assertEqual(metrics["by_option_bucket"]["2"]["accuracy"], 1.0)
        # 选项数 4 -> 桶 "3-4" (共 1 条，错)
        self.assertEqual(metrics["by_option_bucket"]["3-4"]["total"], 1)
        self.assertEqual(metrics["by_option_bucket"]["3-4"]["accuracy"], 0.0)
        # 选项数 5 -> 桶 "5-8" (共 1 条，对)
        self.assertEqual(metrics["by_option_bucket"]["5-8"]["total"], 1)
        self.assertEqual(metrics["by_option_bucket"]["5-8"]["accuracy"], 1.0)

        # 按路由 (by_route)
        self.assertEqual(metrics["by_route"]["classification"]["total"], 3)
        self.assertEqual(metrics["by_route"]["classification"]["correct"], 2)
        self.assertEqual(metrics["by_route"]["distillation"]["total"], 1)
        self.assertEqual(metrics["by_route"]["distillation"]["correct"], 1)

    def test_simple_stub_tokenizer(self):
        """测试离线/单测备用的 SimpleStubTokenizer 行为。"""
        tok = SimpleStubTokenizer()
        # 确保 A..Z 都是单 token
        for letter in LETTERS:
            encoded = tok.encode(letter)
            self.assertEqual(len(encoded), 1, f"字母 {letter} 未能编码为单 token")
            self.assertEqual(tok.decode(encoded), letter)

        # 测试较长文本
        sample_text = "你是决策模型：选择 A 或 B"
        encoded = tok.encode(sample_text)
        self.assertTrue(len(encoded) > 0)
        self.assertEqual(tok.decode(encoded), sample_text)

    def test_dry_run_small_sample(self):
        """测试 train_decision_sft 的 --dry-run 完整小样本执行路径。"""
        # 在系统临时目录生成 3 行合成训练视图数据，加 1 行 >26 选项用于检验跳过
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            synthetic_file = temp_path / "synthetic_train_view.jsonl"
            out_run_dir = temp_path / "runs_dry_run"

            synthetic_rows = [
                # 样本 1: choice 4 选项
                {
                    "rid": "syn_item#01",
                    "src": "general-v5",
                    "split": "train",
                    "lang": "zh",
                    "domain": "decision_mechanics",
                    "kind": "choice",
                    "prompt": "【情境】\n测试情境A\n\n【问题】\n请选择最佳行动\n\n【选项】\nA. 行动一\nB. 行动二\nC. 行动三\nD. 行动四",
                    "options": ["a1", "a2", "a3", "a4"],
                    "option_labels": ["行动一", "行动二", "行动三", "行动四"],
                    "answer_idx": 1,  # 对应 'B'
                    "route": "classification",
                },
                # 样本 2: noul 2 选项
                {
                    "rid": "syn_item#02",
                    "src": "general-v5",
                    "split": "train",
                    "lang": "en",
                    "domain": "ethics",
                    "kind": "noul",
                    "prompt": "【情境】\nContext B\n\n【问题】\nIs this action allowed?\n\n【选项】\nA. Yes\nB. No",
                    "options": ["yes", "no"],
                    "option_labels": ["Yes", "No"],
                    "answer_idx": 0,  # 对应 'A'
                    "route": "classification",
                },
                # 样本 3: score 5 档位
                {
                    "rid": "syn_item#03",
                    "src": "general-v5",
                    "split": "train",
                    "lang": "zh",
                    "domain": "risk",
                    "kind": "score",
                    "prompt": "【情境】\nContext C\n\n【问题】\n风险等级评定\n\n【选项】\nA. 0\nB. 1\nC. 2\nD. 3\nE. 4",
                    "options": ["0", "1", "2", "3", "4"],
                    "option_labels": ["0", "1", "2", "3", "4"],
                    "answer_idx": 3,  # 对应 'D'
                    "route": "distillation",
                },
                # 样本 4: 超标 28 选项 -> 应当在 dry-run 中被统计并跳过
                {
                    "rid": "syn_item#04_exceed",
                    "src": "general-v5",
                    "split": "train",
                    "lang": "en",
                    "domain": "huge_options",
                    "kind": "choice",
                    "prompt": "28 options test",
                    "options": [f"opt_{i}" for i in range(28)],
                    "answer_idx": 0,
                    "route": "classification",
                },
            ]

            with open(synthetic_file, "w", encoding="utf-8") as f:
                for r in synthetic_rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

            # 运行 dry-run
            cli_args = [
                "--train-view", str(synthetic_file),
                "--output-dir", str(out_run_dir),
                "--dry-run",
                "--limit", "10",
                "--seq-len", "512",
            ]

            stdout_buf = io.StringIO()
            with redirect_stdout(stdout_buf):
                exit_code = train_decision_sft.main(cli_args)

            output_text = stdout_buf.getvalue()

            # 断言 dry-run 顺利完成，返回码 0
            self.assertEqual(exit_code, 0)
            self.assertIn("[DRY-RUN] 开启 Track A 数据校验与样本形状检查", output_text)
            self.assertIn("校验通过！未加载模型权重，未进行任何 GPU 训练计算。", output_text)
            # 断言前 3 条样本打印了答案字母 B, A, D
            self.assertIn("答案字母: B", output_text)
            self.assertIn("答案字母: A", output_text)
            self.assertIn("答案字母: D", output_text)
            # 断言 1 条超标样本被计数
            self.assertIn("skipped_options_gt_26: 1", output_text)


if __name__ == "__main__":
    unittest.main()
