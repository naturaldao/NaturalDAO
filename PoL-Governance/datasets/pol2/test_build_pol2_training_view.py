"""build_pol2_training_view.py 的离线不变量测试（合成 fixture，不读真实冻结数据）。

覆盖：
1. choice 三种选项键集的选项顺序与 answer_idx（按 criteria 插入顺序，不按词表顺序）；
2. score 0-4 映射（options/option_labels 为数字字符串，scale/soft 为 null）；
3. 未知 label 被跳过并计数（skipped_label_not_in_options）；
4. blind_test / private_holdout 输入与 region 一律拒绝（exit 2）；
5. training_approved=false 时 build 被拒、--schema-preview 允许且不写文件；
6. --out 位于仓库内（绝对或相对路径）被拒绝；
7. 确定性：两次 build 逐字节一致、两次 schema-preview stdout 一致；
8. 区域过滤：全量输入只输出指定项目区，blind_test unit 不进入输出；
9. unit_id 升序排序与重复 unit_id 检测；
10. 防注入前言与选项/档位渲染。

运行（仓库根为 cwd）：

    python -m unittest datasets.pol2.test_build_pol2_training_view -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from datasets.pol2 import build_pol2_training_view as view

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "datasets" / "pol2" / "build_pol2_training_view.py"

FACT = {
    "content": "固定事实。",
    "event_kind": "observed_condition",
    "occurred_at": "2026-07-01T00:00:00+08:00",
    "received_at": "2026-07-01T00:00:00+08:00",
}
VAR_FACT = {
    "content": "变量事实。",
    "event_kind": "published_future_plan",
    "occurred_at": "2026-08-01T00:00:00+08:00",
    "received_at": "2026-08-01T00:00:00+08:00",
}
CHOICE_4_KEYS = {"yes": "符合", "no": "不符合", "unknown": "事实不足", "not_applicable": "不适用"}
NECESSARY_KEYS = {"necessary": "必要", "unnecessary": "不必要", "unknown": "事实不足", "not_applicable": "不适用"}
RELATION_5_KEYS = {"hate2": "破坏联结", "love2": "建立联结", "mixed": "两者并存", "neither": "无关", "unknown": "事实不足"}
SCORE_LEVELS = ["档位0定义", "档位1定义", "档位2定义", "档位3定义", "档位4定义"]


def make_unit(unit_id, *, split_proposal="train", kind="choice", criteria=None, label="yes",
              world="a", case_id=None, mapping_id="fixture:选项", instructions="请判断。"):
    """合成 17 键冻结 unit（字段形状与 FREEZE-8705-V1.md §3 一致，内容为 fixture）。"""
    if kind == "choice":
        criteria = dict(CHOICE_4_KEYS if criteria is None else criteria)
        question = {"type": "choice", "instructions": instructions, "criteria": criteria}
    else:
        criteria = list(SCORE_LEVELS if criteria is None else criteria)
        question = {"type": "score", "instructions": instructions, "criteria": criteria}
    return {
        "unit_id": unit_id,
        "case_id": case_id or unit_id.split(":")[0],
        "world": world,
        "family_id": "POL2F_T_FIXTURE",
        "mapping_id": mapping_id,
        "source_run": "FULL200-0001",
        "source_batch": "FULL200-0001",
        "status": "ACCEPTED",
        "split_proposal": split_proposal,
        "label": label,
        "answer_a": {"unit_id": unit_id, "status": "ok", "label": label},
        "answer_b": {"unit_id": unit_id, "status": "ok", "label": label},
        "audit_status": "not_sampled",
        "state": {
            "fixed_facts": [dict(FACT)],
            "judgment_actor": "判定对象甲",
            "observer_cutoff": "2026-10-01T00:00:00+08:00",
            "action_stage": "observed",
            "world": {"variable_facts": [dict(VAR_FACT)], "candidate_action": "候选行动丙。"},
        },
        "question": question,
        "question_sha": "0" * 64,
        "source_sha": "1" * 64,
    }


def write_freeze(directory, units, *, approved=False, name="accepted-units.jsonl"):
    """写临时 JSONL 与同目录 manifest.json。"""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            handle.write(json.dumps(unit, ensure_ascii=False) + "\n")
    manifest = {"freeze_id": "POL2-accepted-8705-v1", "training_approved": approved}
    (directory / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    return path


class Pol2ViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.out = self.dir / "out" / "view.jsonl"

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )

    def read_rows(self, path):
        text = Path(path).read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_choice_option_order_and_answer_idx(self):
        # criteria 插入顺序各不相同；answer_idx 必须按插入顺序而非词表顺序。
        units = [
            make_unit("case01:a", label="no"),
            make_unit("case02:a", label="unknown",
                      criteria={"no": "不符合", "yes": "符合", "not_applicable": "不适用", "unknown": "事实不足"}),
            make_unit("case03:a", label="unnecessary", criteria=NECESSARY_KEYS),
            make_unit("case04:a", label="neither", criteria=RELATION_5_KEYS),
        ]
        path = write_freeze(self.dir / "choice", units, approved=True)
        res = self.run_cli("--freeze", path, "--region", "train", "--out", self.out)
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = {row["unit_id"]: row for row in self.read_rows(self.out)}
        self.assertEqual(sorted(rows), ["case01:a", "case02:a", "case03:a", "case04:a"])

        expectations = [
            ("case01:a", list(CHOICE_4_KEYS.keys()), 1, "no"),
            ("case02:a", ["no", "yes", "not_applicable", "unknown"], 3, "unknown"),
            ("case03:a", list(NECESSARY_KEYS.keys()), 1, "unnecessary"),
            ("case04:a", list(RELATION_5_KEYS.keys()), 3, "neither"),
        ]
        for unit_id, expected_options, expected_idx, expected_label in expectations:
            row = rows[unit_id]
            self.assertEqual(row["kind"], "choice")
            self.assertEqual(row["options"], expected_options)
            self.assertEqual(row["option_labels"], expected_options)
            self.assertEqual(row["answer_idx"], expected_idx)
            self.assertEqual(row["label_raw"], expected_label)
            self.assertIsNone(row["soft"])
            self.assertIsNone(row["soft_conf"])
            self.assertIsNone(row["scale"])
            self.assertEqual(row["route"], "classification")
            self.assertEqual(row["src"], view.SRC)
            self.assertEqual(row["split"], "train")
            self.assertEqual(row["lang"], "zh")
            self.assertEqual(row["template_version"], view.TEMPLATE_VERSION)
            self.assertEqual(row["rid"], unit_id + "#pol2")

        # 防注入前言 + 数据卡 §3.1 材料 + 选项渲染
        prompt = rows["case01:a"]["prompt"]
        self.assertTrue(prompt.startswith(view.PREAMBLE))
        for marker in ("【判定对象】", "判定对象甲", "【已知事实】", "固定事实。",
                       "【变量事实】", "变量事实。", "【候选行动】", "候选行动丙。",
                       "【观察截止时点】", "【行动阶段】", "【题目】", "请判断。", "【选项】"):
            self.assertIn(marker, prompt)
        self.assertIn("A. yes：符合", prompt)
        self.assertIn("B. no：不符合", prompt)

    def test_score_mapping_and_rendering(self):
        units = [
            make_unit("score0:a", kind="score", label=0),
            make_unit("score2:a", kind="score", label=2),
            make_unit("score4:a", kind="score", label=4),
        ]
        path = write_freeze(self.dir / "score", units, approved=True)
        res = self.run_cli("--freeze", path, "--region", "train", "--out", self.out)
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = {row["unit_id"]: row for row in self.read_rows(self.out)}
        for unit_id, expected_idx in (("score0:a", 0), ("score2:a", 2), ("score4:a", 4)):
            row = rows[unit_id]
            self.assertEqual(row["kind"], "score")
            self.assertEqual(row["options"], ["0", "1", "2", "3", "4"])
            self.assertEqual(row["option_labels"], ["0", "1", "2", "3", "4"])
            self.assertEqual(row["answer_idx"], expected_idx)
            self.assertEqual(row["label_raw"], expected_idx)
            self.assertIsNone(row["scale"])
            self.assertIsNone(row["soft"])
            self.assertIn("【档位】", row["prompt"])
            self.assertIn("0. 档位0定义", row["prompt"])
            self.assertIn("4. 档位4定义", row["prompt"])

    def test_unknown_label_skipped_and_counted(self):
        units = [
            make_unit("good:a", label="yes"),
            make_unit("bad-choice:a", label="maybe"),
            make_unit("bad-range:a", kind="score", label=5),
            make_unit("bad-str:a", kind="score", label="3"),
            make_unit("bad-null:a", label=None),
        ]
        path = write_freeze(self.dir / "skip", units, approved=True)
        res = self.run_cli("--freeze", path, "--region", "train", "--out", self.out, "--stats")
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = self.read_rows(self.out)
        self.assertEqual([row["unit_id"] for row in rows], ["good:a"])
        self.assertIn('"skipped_label_not_in_options": 4', res.stdout)
        self.assertIn("skipped reason", res.stdout)
        self.assertEqual(res.stderr, "")

    def test_private_region_and_blind_input_rejected(self):
        path = write_freeze(self.dir / "guard", [make_unit("g1:a")], approved=True)
        for region in ("private_holdout", "blind_test"):
            preview = self.run_cli("--freeze", path, "--region", region, "--schema-preview")
            self.assertEqual(preview.returncode, 2, region)
            self.assertIn("refusing", preview.stderr)
            build = self.run_cli("--freeze", path, "--region", region, "--out", self.out)
            self.assertEqual(build.returncode, 2, region)
            self.assertFalse(self.out.exists())

        # 输入文件按名字被识别为盲测/私有，即使 --region 看起来合法也拒绝。
        blind_path = write_freeze(self.dir / "blindsrc", [make_unit("b1:a", split_proposal="blind_test")],
                                  approved=True, name="blind_test.units.jsonl")
        res = self.run_cli("--freeze", blind_path, "--region", "train", "--schema-preview")
        self.assertEqual(res.returncode, 2)
        self.assertIn("refusing", res.stderr)

        private_path = write_freeze(self.dir / "privsrc", [make_unit("p1:a")],
                                    approved=True, name="private_holdout.units.jsonl")
        res = self.run_cli("--freeze", private_path, "--region", "train", "--schema-preview")
        self.assertEqual(res.returncode, 2)
        self.assertIn("refusing", res.stderr)

    def test_training_gate(self):
        path = write_freeze(self.dir / "gate", [make_unit("g1:a")], approved=False)
        refused = self.run_cli("--freeze", path, "--region", "train", "--out", self.out)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("NOT TRAINING APPROVED", refused.stderr)
        self.assertIn("schema preview only", refused.stderr)
        self.assertFalse(self.out.exists())

        preview = self.run_cli("--freeze", path, "--region", "train",
                               "--schema-preview", "--stats", "--out", self.out)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("pv-1", preview.stdout)
        self.assertIn("NOT TRAINING APPROVED", preview.stdout)
        self.assertIn("would-be sha256", preview.stdout)
        self.assertFalse(self.out.exists())

        # 未批准时 build 缺少 --out 也必须先被 training gate 拒绝
        no_out = self.run_cli("--freeze", path, "--region", "train")
        self.assertEqual(no_out.returncode, 2)
        self.assertIn("NOT TRAINING APPROVED", no_out.stderr)

        # 明确批准（fixture）后 build 放行；缺 --out 仍报错
        approved_path = write_freeze(self.dir / "gate-ok", [make_unit("g2:a")], approved=True)
        missing_out = self.run_cli("--freeze", approved_path, "--region", "train")
        self.assertEqual(missing_out.returncode, 2)
        self.assertIn("--out is required", missing_out.stderr)
        built = self.run_cli("--freeze", approved_path, "--region", "train", "--out", self.out)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertTrue(self.out.exists())

    def test_out_inside_repository_rejected(self):
        path = write_freeze(self.dir / "repo", [make_unit("r1:a")], approved=True)
        inside = ROOT / "datasets" / "pol2" / "_tmp_pol2_view_should_not_exist.jsonl"
        self.addCleanup(inside.unlink, missing_ok=True)

        absolute = self.run_cli("--freeze", path, "--region", "train", "--out", inside)
        self.assertEqual(absolute.returncode, 2)
        self.assertIn("inside repository", absolute.stderr)
        self.assertFalse(inside.exists())

        relative = self.run_cli("--freeze", path, "--region", "train",
                                "--out", "datasets/pol2/_tmp_pol2_view_should_not_exist.jsonl")
        self.assertEqual(relative.returncode, 2)
        self.assertIn("inside repository", relative.stderr)
        self.assertFalse(inside.exists())

    def test_deterministic(self):
        units = [
            make_unit("z9:a", label="yes"),
            make_unit("a1:a", label="no"),
            make_unit("m5:a", label="yes"),
        ]
        path = write_freeze(self.dir / "det", units, approved=True)
        out1, out2 = self.dir / "o1.jsonl", self.dir / "o2.jsonl"
        first = self.run_cli("--freeze", path, "--region", "train", "--out", out1)
        second = self.run_cli("--freeze", path, "--region", "train", "--out", out2)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(out1.read_bytes(), out2.read_bytes())

        preview1 = self.run_cli("--freeze", path, "--region", "train", "--schema-preview", "--stats")
        preview2 = self.run_cli("--freeze", path, "--region", "train", "--schema-preview", "--stats")
        self.assertEqual(preview1.returncode, 0, preview1.stderr)
        self.assertEqual(preview2.returncode, 0, preview2.stderr)
        self.assertEqual(preview1.stdout, preview2.stdout)
        self.assertEqual(preview1.stderr, preview2.stderr)
        self.assertIn("would-be sha256", preview1.stdout)

    def test_region_filter_full_input(self):
        units = [
            make_unit("t2:a", label="yes"),
            make_unit("t1:a", label="no"),
            make_unit("v1:a", split_proposal="validation", label="yes"),
            make_unit("c1:a", split_proposal="calibration", label="yes"),
            make_unit("b1:a", split_proposal="blind_test", label="yes"),
        ]
        path = write_freeze(self.dir / "regions", units, approved=True)
        expectations = {
            "train": ["t1:a", "t2:a"],
            "public_test": ["v1:a"],
            "validation": ["c1:a"],
        }
        for region, expected in expectations.items():
            out = self.dir / f"{region}.jsonl"
            res = self.run_cli("--freeze", path, "--region", region, "--out", out)
            self.assertEqual(res.returncode, 0, res.stderr)
            rows = self.read_rows(out)
            self.assertEqual([row["unit_id"] for row in rows], expected)
            self.assertTrue(all(row["split"] == region for row in rows))
            self.assertNotIn("b1:a", [row["unit_id"] for row in rows])

        # 全量输入里的 private_holdout unit 只贡献计数，不进入输出（预览也不打印其内容）。
        preview = self.run_cli("--freeze", path, "--region", "train", "--schema-preview", "--stats")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('"private_holdout": 1', preview.stdout)
        self.assertNotIn("b1:a", preview.stdout)
        self.assertNotIn("POL2F_T_FIXTURE", preview.stdout)

    def test_sorting_and_duplicate_unit_id(self):
        units = [
            make_unit("z9:a", label="yes"),
            make_unit("a1:a", label="no"),
            make_unit("m5:a", label="yes"),
        ]
        path = write_freeze(self.dir / "sort", units, approved=True)
        res = self.run_cli("--freeze", path, "--region", "train", "--out", self.out)
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = self.read_rows(self.out)
        self.assertEqual([row["unit_id"] for row in rows], ["a1:a", "m5:a", "z9:a"])
        self.assertEqual([row["rid"] for row in rows], ["a1:a#pol2", "m5:a#pol2", "z9:a#pol2"])

        dup_path = write_freeze(self.dir / "dup",
                                [make_unit("dup:a", label="yes"), make_unit("dup:a", label="no")],
                                approved=True)
        dup_out = self.dir / "dup.jsonl"
        res = self.run_cli("--freeze", dup_path, "--region", "train", "--out", dup_out)
        self.assertEqual(res.returncode, 2)
        self.assertIn("duplicate unit_id", res.stderr)
        self.assertFalse(dup_out.exists())

        # 未知 split_proposal 也是硬错误（不静默丢弃）
        bad_path = write_freeze(self.dir / "bad-split", [make_unit("x1:a", split_proposal="unknown_zone")],
                                approved=True)
        res = self.run_cli("--freeze", bad_path, "--region", "train", "--out", self.out)
        self.assertEqual(res.returncode, 2)
        self.assertIn("unknown split_proposal", res.stderr)


if __name__ == "__main__":
    unittest.main()
