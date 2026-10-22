"""run_plan.py 的纯 CPU 单元测试（只验证命令生成，不执行 GPU）。"""
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from finetune import run_plan


class RunPlanTest(unittest.TestCase):
    def test_header_contains_env_and_repo(self):
        script = run_plan.build_script(["env-check"], "$HOME/src/polgov",
                                       "/mnt/c/repo", "$HOME/src/polgov/models/Qwen3-1.7B",
                                       "$HOME/src/polgov/runs/track-a/adapter")
        self.assertTrue(script.startswith("#!/bin/bash"))
        self.assertIn("set -euo pipefail", script)
        self.assertIn("source \"$POLGOV_HOME/.venv/bin/activate\"", script)
        self.assertIn("cd \"/mnt/c/repo\"", script)
        self.assertIn("ALL_STAGES_DONE", script)
        self.assertNotIn("C:\\", script)

    def test_single_stage_only(self):
        script = run_plan.build_script(["base-test"], "$HOME/src/polgov", "/mnt/c/repo",
                                       "model-x", "adapter-x")
        self.assertIn("eval_decision.py --eval-view", script)
        self.assertIn("general-test-view.jsonl", script)
        self.assertNotIn("lm_eval", script)
        self.assertNotIn("train_decision_sft.py", script)

    def test_all_stages_present_in_order(self):
        script = run_plan.build_script(list(run_plan.STAGES), "$HOME/src/polgov", "/mnt/c/repo",
                                       "model-x", "adapter-x")
        markers = [f"=== [$(date +%H:%M:%S)] {stage} ===" for stage in run_plan.STAGES]
        positions = [script.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("train_decision_scorer.py", script)
        self.assertIn("calibrate.py fit", script)
        self.assertIn("--seed 20261024", script)
        self.assertIn("--seed 20261025", script)
        self.assertIn("track-a-val-seed20261024.json", script)
        self.assertIn("collect_results.py", script)
        self.assertIn("eval_decision_scorer.py", script)
        self.assertIn("multiseed-track-a.md", script)

    def test_custom_paths_appear(self):
        script = run_plan.build_script(["lm-eval"], "/custom/home", "/custom/repo",
                                       "/custom/model", "/custom/adapter")
        self.assertIn('pretrained="/custom/model"', script)
        self.assertIn('peft="/custom/adapter"', script)
        self.assertIn('--output_path "/custom/home/evals/lm-eval-base"', script)
        self.assertIn("--trust_remote_code", script)

    def test_unknown_stage_exits_2(self):
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = run_plan.main(["--stages", "nope"])
        self.assertEqual(code, 2)
        self.assertIn("unknown stages", buffer.getvalue())

    def test_out_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "resume.sh"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = run_plan.main(["--stages", "env-check", "--out", str(out)])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("env-check", text)
            self.assertTrue(text.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
