"""最终评测聚合脚本的纯 CPU 单元测试（标准库，不依赖 torch）。"""
from __future__ import annotations

import io
import json
import math
import os
import random
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from finetune import final_eval_aggregate as fea


# ---------- 合成数据构造 ----------

def _make_pred_row(
    rid: str,
    kind: str = "choice",
    lang: str = "en",
    route: str = "classification",
    num_options: int = 4,
    correct: bool = True,
    gold_letter: str = "A",
    pred_letter: str | None = None,
    candidate_probs: dict | None = None,
) -> dict:
    """构造一行预测 JSONL。"""
    if pred_letter is None:
        pred_letter = gold_letter if correct else "B"
    row = {
        "rid": rid,
        "kind": kind,
        "lang": lang,
        "route": route,
        "num_options": num_options,
        "gold_letter": gold_letter,
        "pred_letter": pred_letter,
        "correct": correct,
    }
    if candidate_probs is not None:
        row["candidate_probs"] = candidate_probs
    return row


def _make_synthetic_rows(count: int = 100, seed: int = 42) -> list[dict]:
    """生成固定随机的合成预测行集合。"""
    rng = random.Random(seed)
    kinds = ["choice", "noul", "score"]
    langs = ["en", "zh"]
    routes = ["classification", "distillation"]
    bucket_opts = [2, 3, 5, 10]  # maps to "2", "3-4", "5-8", "9-26"
    letters = "ABCD"
    rows = []
    for i in range(count):
        gold = rng.choice(letters)
        correct = rng.random() > 0.4
        pred = gold if correct else rng.choice([l for l in letters if l != gold])
        num_options = rng.choice(bucket_opts)
        # candidate_probs: 模拟概率
        probs = {}
        for j in range(num_options):
            letter = chr(ord("A") + j)
            probs[letter] = rng.random()
        total = sum(probs.values())
        probs = {k: round(v / total, 6) for k, v in probs.items()}
        rows.append(_make_pred_row(
            rid=f"synth-{i:06d}#q",
            kind=rng.choice(kinds),
            lang=rng.choice(langs),
            route=rng.choice(routes),
            num_options=num_options,
            correct=correct,
            gold_letter=gold,
            pred_letter=pred,
            candidate_probs=probs,
        ))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------- 测试类 ----------

class TestWilsonCI(unittest.TestCase):
    def test_all_correct(self):
        """100% 正确率：CI 上界为 1.0。"""
        ci = fea.wilson_ci(100, 100)
        self.assertAlmostEqual(ci[1], 1.0, places=4)
        self.assertGreater(ci[0], 0.9)

    def test_none_correct(self):
        """0% 正确率：CI 下界为 0.0。"""
        ci = fea.wilson_ci(0, 100)
        self.assertAlmostEqual(ci[0], 0.0, places=4)
        self.assertLess(ci[1], 0.1)

    def test_ci_contains_point(self):
        """CI 包含点估计。"""
        for correct, total in [(50, 100), (1, 10), (99, 100)]:
            ci = fea.wilson_ci(correct, total)
            p = correct / total
            self.assertLessEqual(ci[0], p + 1e-6)
            self.assertGreaterEqual(ci[1], p - 1e-6)

    def test_zero_total(self):
        ci = fea.wilson_ci(0, 0)
        self.assertEqual(ci, [0.0, 0.0])


class TestNormalAggregate(unittest.TestCase):
    """正常聚合：分层 / CI / 配对。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_rows = _make_synthetic_rows(100, seed=42)
        self.tuned_rows = _make_synthetic_rows(100, seed=43)
        self.base_path = Path(self.tmpdir) / "base.jsonl"
        self.tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        self.out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(self.base_path, self.base_rows)
        _write_jsonl(self.tuned_path, self.tuned_rows)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, extra_args: list[str] | None = None) -> tuple[int, dict | None]:
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--out", str(self.out_path),
        ]
        if extra_args:
            args.extend(extra_args)
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        if code == 0 and self.out_path.exists():
            return code, json.loads(self.out_path.read_text(encoding="utf-8"))
        return code, None

    def test_basic_aggregate(self):
        code, output = self._run()
        self.assertEqual(code, 0)
        self.assertIsNotNone(output)
        self.assertEqual(output["schema"], "pol-final-eval-aggregate-v1")
        self.assertEqual(output["protocol"], "finetune/EVAL-PROTOCOL.md#v1")

        # coverage
        cov = output["coverage"]
        self.assertEqual(cov["view_rows"], 100)
        self.assertEqual(cov["expected_evaluated"], 100)

        # models
        for label in ("base", "tuned"):
            m = output["models"][label]
            self.assertEqual(m["total"], 100)
            self.assertIn("accuracy", m)
            self.assertIn("accuracy_ci95_wilson", m)
            self.assertEqual(len(m["accuracy_ci95_wilson"]), 2)
            # 分层键全在
            for kind in ("choice", "noul", "score"):
                self.assertIn(kind, m["by_kind"])
            for lang in ("en", "zh"):
                self.assertIn(lang, m["by_lang"])
            for bucket in ("2", "3-4", "5-8", "9-26"):
                self.assertIn(bucket, m["by_option_bucket"])
            for route in ("classification", "distillation"):
                self.assertIn(route, m["by_route"])

            # 分层 total 之和 == total
            kind_total = sum(v["total"] for v in m["by_kind"].values())
            self.assertEqual(kind_total, m["total"])

        # paired
        paired = output["paired"]
        self.assertEqual(paired["method"], "paired_item_bootstrap")
        self.assertIn("ci95", paired)
        self.assertEqual(len(paired["ci95"]), 2)

        # calibration = pending_temperature (未指定)
        cal = output["calibration"]
        self.assertEqual(cal["status"], "pending_temperature")

    def test_deterministic_output(self):
        """两次输出逐字节相同。"""
        code1, _ = self._run()
        text1 = self.out_path.read_bytes()
        code2, _ = self._run()
        text2 = self.out_path.read_bytes()
        self.assertEqual(code1, 0)
        self.assertEqual(code2, 0)
        self.assertEqual(text1, text2)

    def test_no_rid_in_output(self):
        """输出不含 rid 或逐例字段。"""
        code, output = self._run()
        self.assertEqual(code, 0)
        text = self.out_path.read_text(encoding="utf-8")
        # 不应包含 rid
        self.assertNotIn('"rid"', text)
        # 不应包含 pred_letter / gold_letter
        self.assertNotIn('"pred_letter"', text)
        self.assertNotIn('"gold_letter"', text)
        # 不应包含 candidate_probs
        self.assertNotIn('"candidate_probs"', text)
        # 不应包含 synth- (合成 rid 前缀)
        self.assertNotIn("synth-", text)


class TestTemperatureAndFitPreds(unittest.TestCase):
    """--temperature 与 --fit-preds 互斥。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rows = _make_synthetic_rows(100, seed=42)
        self.base_path = Path(self.tmpdir) / "base.jsonl"
        self.tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        self.fit_path = Path(self.tmpdir) / "fit.jsonl"
        self.out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(self.base_path, rows)
        _write_jsonl(self.tuned_path, rows)
        _write_jsonl(self.fit_path, rows)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_mutual_exclusive(self):
        """同时给 --temperature 和 --fit-preds → exit 2。"""
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--temperature", "1.5",
            "--fit-preds", str(self.fit_path),
            "--out", str(self.out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 2)

    def test_temperature_applied(self):
        """--temperature 只 apply，status=applied。"""
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--temperature", "1.5",
            "--out", str(self.out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 0)
        output = json.loads(self.out_path.read_text(encoding="utf-8"))
        self.assertEqual(output["calibration"]["status"], "applied")
        self.assertAlmostEqual(output["calibration"]["temperature"], 1.5)

    def test_fit_preds(self):
        """--fit-preds 拟合温度，status=fitted。"""
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--fit-preds", str(self.fit_path),
            "--out", str(self.out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 0)
        output = json.loads(self.out_path.read_text(encoding="utf-8"))
        self.assertEqual(output["calibration"]["status"], "fitted")
        self.assertGreater(output["calibration"]["temperature"], 0)
        self.assertEqual(output["calibration"]["fit_half"], "calibration")
        self.assertIn("raw", output["calibration"])
        self.assertIn("calibrated", output["calibration"])
        self.assertIsInstance(output["calibration"]["accuracy_unchanged"], bool)


class TestMissingRows(unittest.TestCase):
    """缺行时 exit 2 与 --allow-missing。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rows = _make_synthetic_rows(80, seed=42)  # 80 rows but view_rows=100
        self.base_path = Path(self.tmpdir) / "base.jsonl"
        self.tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        self.out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(self.base_path, self.rows)
        _write_jsonl(self.tuned_path, self.rows)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_exit2(self):
        """缺行时默认 exit 2。"""
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--out", str(self.out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 2)

    def test_allow_missing(self):
        """--allow-missing 时继续，accuracy_with_missing 把缺失按错误计入。"""
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--allow-missing",
            "--out", str(self.out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 0)
        output = json.loads(self.out_path.read_text(encoding="utf-8"))
        m = output["models"]["base"]
        # accuracy_with_missing = correct / 100 (expected_evaluated)
        expected_awm = round(m["correct"] / 100, 6)
        self.assertAlmostEqual(m["accuracy_with_missing"], expected_awm, places=6)
        self.assertGreater(m["missing_rows"], 0)


class TestUnknownStratumKey(unittest.TestCase):
    """未知分层键 → exit 2。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_unknown_kind(self):
        rows = [_make_pred_row(f"r-{i}#q", kind="unknown_kind") for i in range(30)]
        base_path = Path(self.tmpdir) / "base.jsonl"
        tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(base_path, rows)
        _write_jsonl(tuned_path, rows)
        args = [
            "--preds", f"base={base_path}",
            "--preds", f"tuned={tuned_path}",
            "--view-rows", "30",
            "--out", str(out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 2)

    def test_unknown_lang(self):
        rows = [_make_pred_row(f"r-{i}#q", lang="fr") for i in range(30)]
        base_path = Path(self.tmpdir) / "base.jsonl"
        tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(base_path, rows)
        _write_jsonl(tuned_path, rows)
        args = [
            "--preds", f"base={base_path}",
            "--preds", f"tuned={tuned_path}",
            "--view-rows", "30",
            "--out", str(out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 2)


class TestInvalidRows(unittest.TestCase):
    """无效行（无法确定 correct）。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_invalid_row_exit2_without_allow_missing(self):
        """无效概率行（无 correct / pred / gold）默认 exit 2。"""
        rows = _make_synthetic_rows(25, seed=42)
        # 加一行无法判定 correct 的
        rows.append({"rid": "bad-1", "kind": "choice", "lang": "en",
                      "route": "classification", "num_options": 4})
        base_path = Path(self.tmpdir) / "base.jsonl"
        tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(base_path, rows)
        _write_jsonl(tuned_path, rows)
        args = [
            "--preds", f"base={base_path}",
            "--preds", f"tuned={tuned_path}",
            "--view-rows", "26",
            "--out", str(out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 2)


class TestPairedBootstrapTooFew(unittest.TestCase):
    """配对行 < 20 → exit 2。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_too_few_paired(self):
        # 只有 10 行，但 rid 全不同
        base_rows = [_make_pred_row(f"base-{i}#q") for i in range(10)]
        tuned_rows = [_make_pred_row(f"tuned-{i}#q") for i in range(10)]
        base_path = Path(self.tmpdir) / "base.jsonl"
        tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(base_path, base_rows)
        _write_jsonl(tuned_path, tuned_rows)
        args = [
            "--preds", f"base={base_path}",
            "--preds", f"tuned={tuned_path}",
            "--view-rows", "10",
            "--allow-missing",
            "--out", str(out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 2)


class TestSkippedJSON(unittest.TestCase):
    """--skipped 参数。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rows = _make_synthetic_rows(90, seed=42)
        self.base_path = Path(self.tmpdir) / "base.jsonl"
        self.tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        self.out_path = Path(self.tmpdir) / "aggregate.json"
        _write_jsonl(self.base_path, self.rows)
        _write_jsonl(self.tuned_path, self.rows)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_skipped_reduces_expected(self):
        """skipped 减少 expected_evaluated。"""
        skipped_path = Path(self.tmpdir) / "skipped.json"
        skipped_path.write_text(json.dumps({"options_gt_26": 10}), encoding="utf-8")
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--skipped", str(skipped_path),
            "--out", str(self.out_path),
        ]
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = fea.main(args)
        self.assertEqual(code, 0)
        output = json.loads(self.out_path.read_text(encoding="utf-8"))
        cov = output["coverage"]
        self.assertEqual(cov["skipped_total"], 10)
        self.assertEqual(cov["expected_evaluated"], 90)

    def test_unknown_skip_reason_rejected(self):
        """未知跳过原因（例如一条 rid 伪装成原因）→ exit 2，不许带出。"""
        skipped_path = Path(self.tmpdir) / "skipped.json"
        skipped_path.write_text(
            json.dumps({"options_gt_26": 1, "db-bigbench-00183cfc#formal_fallacies": 1}),
            encoding="utf-8",
        )
        args = [
            "--preds", f"base={self.base_path}",
            "--preds", f"tuned={self.tuned_path}",
            "--view-rows", "100",
            "--skipped", str(skipped_path),
            "--out", str(self.out_path),
        ]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = fea.main(args)
        self.assertEqual(code, 2)
        self.assertFalse(self.out_path.exists())


# ---------- 增补 v2：簇 bootstrap / completed_only / 分母口径 / 分箱 ----------

def _cluster_sizes(groups: int = 45) -> list[int]:
    """簇大小不均：1..30，且含 >20 行的簇。"""
    return [1 + (g * 7) % 30 for g in range(groups)]


def _make_clustered_rows(sizes: list[int], seed: int, *, tuned: bool) -> list[dict]:
    """簇内强相关的合成预测（rid = g<簇号>#<行号>）。"""
    rng = random.Random(seed)
    rows = []
    for g, size in enumerate(sizes):
        cluster_rng = random.Random(1000 + g)  # base/tuned 共享簇级效应
        base_p = cluster_rng.random()
        lift = cluster_rng.choice([-0.4, 0.0, 0.5])
        p = min(1.0, max(0.0, base_p + (lift if tuned else 0.0)))
        cluster_correct = cluster_rng.random() < p
        for i in range(size):
            # 90% 跟随簇级结果 → 强簇内相关
            correct = cluster_correct if rng.random() < 0.9 else not cluster_correct
            gold = "A"
            conf = 0.35 + 0.6 * rng.random()
            other = (1.0 - conf) / 3
            if correct:
                probs = {"A": conf, "B": other, "C": other, "D": other}
            else:
                probs = {"A": other, "B": conf, "C": other, "D": other}
            rows.append(_make_pred_row(
                rid=f"g{g:03d}#{i:03d}", kind=["choice", "noul", "score"][g % 3],
                lang=["en", "zh"][i % 2], route=["classification", "distillation"][g % 2],
                num_options=4, correct=correct, gold_letter=gold,
                pred_letter="A" if correct else "B",
                candidate_probs={k: round(v, 6) for k, v in probs.items()},
            ))
    return rows


class _V2Base(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_path = Path(self.tmpdir) / "base.jsonl"
        self.tuned_path = Path(self.tmpdir) / "tuned.jsonl"
        self.out_path = Path(self.tmpdir) / "aggregate.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, view_rows: int, extra: list[str] | None = None) -> tuple[int, dict | None]:
        args = ["--preds", f"base={self.base_path}", "--preds", f"tuned={self.tuned_path}",
                "--view-rows", str(view_rows), "--out", str(self.out_path)] + (extra or [])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = fea.main(args)
        if code == 0:
            return code, json.loads(self.out_path.read_text(encoding="utf-8"))
        return code, None


class TestClusterBootstrapV2(_V2Base):
    def setUp(self):
        super().setUp()
        self.sizes = _cluster_sizes(45)
        self.n = sum(self.sizes)
        _write_jsonl(self.base_path, _make_clustered_rows(self.sizes, 1, tuned=False))
        _write_jsonl(self.tuned_path, _make_clustered_rows(self.sizes, 2, tuned=True))

    def test_fixture_shape(self):
        self.assertGreaterEqual(self.n, 200)
        self.assertGreaterEqual(len(self.sizes), 40)
        self.assertGreater(max(self.sizes), 20)
        self.assertGreater(len(set(self.sizes)), 10)

    def test_cluster_block(self):
        import statistics
        code, out = self._run(self.n)
        self.assertEqual(code, 0)
        paired = out["paired"]
        self.assertEqual(paired["scope"], "both_completed")
        cl = paired["cluster"]
        self.assertEqual(cl["method"], "paired_group_cluster_bootstrap")
        self.assertEqual(cl["cluster_key"], "rid_prefix_before_hash")
        self.assertEqual(cl["rounds"], 10000)  # 默认值
        self.assertEqual(cl["clusters"], 45)
        self.assertEqual(cl["reliability"], "cautious")
        self.assertEqual(cl["cluster_size_max"], max(self.sizes))
        q1, med, q3 = statistics.quantiles(self.sizes, n=4, method="inclusive")
        self.assertAlmostEqual(cl["cluster_size_median"], round(med, 6), places=6)
        self.assertEqual(cl["cluster_size_iqr"], [round(q1, 6), round(q3, 6)])
        kish = sum(self.sizes) ** 2 / sum(s * s for s in self.sizes)
        self.assertAlmostEqual(cl["kish_neff"], round(kish, 6), places=6)
        # Δ 按行加权，与 item 级点估计相同
        self.assertAlmostEqual(cl["delta"], paired["delta"], places=6)
        lo, hi = cl["ci95"]
        self.assertLessEqual(lo, cl["delta"] + 1e-9)
        self.assertGreaterEqual(hi, cl["delta"] - 1e-9)
        # 簇内强相关 → 簇 CI 与 item CI 不同，且更宽
        self.assertNotEqual(cl["ci95"], paired["ci95"])
        self.assertGreater(hi - lo, paired["ci95"][1] - paired["ci95"][0])

    def test_cluster_rounds_override_and_determinism(self):
        extra = ["--cluster-rounds", "2000", "--temperature", "1.3", "--ece-cluster-rounds", "200"]
        code1, out = self._run(self.n, extra)
        b1 = self.out_path.read_bytes()
        code2, _ = self._run(self.n, extra)
        b2 = self.out_path.read_bytes()
        self.assertEqual((code1, code2), (0, 0))
        self.assertEqual(b1, b2)
        self.assertEqual(out["paired"]["cluster"]["rounds"], 2000)
        text = b1.decode("utf-8")
        self.assertNotIn("g000", text)
        self.assertNotIn('"rid"', text)

    def test_calibration_bins(self):
        code, out = self._run(self.n, ["--temperature", "1.5", "--cluster-rounds", "1000"])
        self.assertEqual(code, 0)
        for key in ("raw", "calibrated"):
            block = out["calibration"][key]
            bins = block["bins"]
            self.assertEqual(len(bins), 15)
            self.assertEqual([b["bin"] for b in bins], list(range(15)))
            for b in bins:
                self.assertEqual(set(b), {"bin", "count", "avg_confidence", "accuracy", "gap"})
            self.assertEqual(sum(b["count"] for b in bins), block["rows"])
            low = sum(1 for b in bins if b["count"] < 20)
            self.assertEqual(block["low_sample_bins"], low)
            self.assertEqual(block["low_sample_flag"], low > 0)
            self.assertTrue(block["low_sample_flag"])  # 低置信区间箱为空
            self.assertEqual(block["ece_rounds"], 500)
            lo, hi = block["ece_ci95_group"]
            self.assertLessEqual(lo, hi)
            self.assertGreaterEqual(lo, 0.0)
            self.assertLessEqual(hi, 1.0)


class TestReliabilityV2(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(fea.reliability_label(50), "ok")
        self.assertEqual(fea.reliability_label(49), "cautious")
        self.assertEqual(fea.reliability_label(30), "cautious")
        self.assertEqual(fea.reliability_label(29), "low")

    def test_three_levels_from_bootstrap(self):
        for groups, expected in ((60, "ok"), (35, "cautious"), (25, "low")):
            base, tuned = {}, {}
            for g in range(groups):
                for i in range(2):
                    rid = f"c{g}#{i}"
                    base[rid] = (g + i) % 2 == 0
                    tuned[rid] = g % 3 != 0
            res = fea.paired_group_cluster_bootstrap(base, tuned, rounds=1000, seed=7)
            self.assertEqual(res["clusters"], groups)
            self.assertEqual(res["reliability"], expected)

    def test_rid_without_hash_is_own_cluster(self):
        base = {f"solo-{i}": i % 2 == 0 for i in range(30)}
        tuned = {f"solo-{i}": True for i in range(30)}
        res = fea.paired_group_cluster_bootstrap(base, tuned, rounds=1000, seed=1)
        self.assertEqual(res["clusters"], 30)
        self.assertEqual(res["kish_neff"], 30.0)

    def test_cluster_key_rejects_non_string(self):
        with self.assertRaises(ValueError):
            fea.cluster_key(None)
        with self.assertRaises(ValueError):
            fea.cluster_key(123)


class TestCompletedOnlyAndDenominatorV2(_V2Base):
    def setUp(self):
        super().setUp()
        sizes = _cluster_sizes(45)
        self.base_rows = _make_clustered_rows(sizes, 1, tuned=False)
        self.tuned_rows = _make_clustered_rows(sizes, 2, tuned=True)
        self.n = len(self.base_rows)
        # base 缺前 10 行，tuned 缺最后 15 行 → missing 集合不同
        _write_jsonl(self.base_path, self.base_rows[10:])
        _write_jsonl(self.tuned_path, self.tuned_rows[:-15])

    def test_missing_exit2_by_default(self):
        code, _ = self._run(self.n)
        self.assertEqual(code, 2)

    def test_completed_only_intersection(self):
        code, out = self._run(self.n, ["--allow-missing", "--cluster-rounds", "1000"])
        self.assertEqual(code, 0)
        inter = self.n - 10 - 15
        co = out["paired"]["completed_only"]
        self.assertEqual(co["scope"], "both_completed")
        self.assertEqual(co["rows"], inter)
        self.assertEqual(out["paired"]["rows"], inter)
        self.assertEqual(len(co["ci95_item"]), 2)
        self.assertEqual(co["ci95_group"], out["paired"]["cluster"]["ci95"])
        self.assertEqual(co["ci95_item"], out["paired"]["ci95"])
        base_map = {r["rid"]: r["correct"] for r in self.base_rows[10:]}
        tuned_map = {r["rid"]: r["correct"] for r in self.tuned_rows[:-15]}
        common = sorted(set(base_map) & set(tuned_map))
        self.assertAlmostEqual(co["base_accuracy"],
                               round(sum(base_map[r] for r in common) / len(common), 6))
        self.assertAlmostEqual(co["tuned_accuracy"],
                               round(sum(tuned_map[r] for r in common) / len(common), 6))

    def test_denominator_views(self):
        code, out = self._run(self.n, ["--allow-missing", "--cluster-rounds", "1000"])
        self.assertEqual(code, 0)
        for label, evaluated in (("base", self.n - 10), ("tuned", self.n - 15)):
            m = out["models"][label]
            cov = out["coverage"]["models"][label]
            self.assertEqual(m["total"], evaluated)
            self.assertEqual(cov["evaluated"], evaluated)
            self.assertEqual(cov["completion_rate"], round(evaluated / self.n, 6))
            self.assertEqual(m["evaluated_accuracy"], m["accuracy"])
            self.assertEqual(m["accuracy"], round(m["correct"] / evaluated, 6))
            self.assertEqual(m["accuracy_with_missing"], round(m["correct"] / self.n, 6))
            self.assertNotEqual(m["accuracy_with_missing"], m["evaluated_accuracy"])
            self.assertLessEqual(m["accuracy_with_missing"], m["evaluated_accuracy"] + 1e-6)

    def test_complete_run_completion_rate_one(self):
        _write_jsonl(self.base_path, self.base_rows)
        _write_jsonl(self.tuned_path, self.tuned_rows)
        code, out = self._run(self.n, ["--cluster-rounds", "1000"])
        self.assertEqual(code, 0)
        for label in ("base", "tuned"):
            self.assertEqual(out["coverage"]["models"][label]["completion_rate"], 1.0)
            m = out["models"][label]
            self.assertEqual(m["accuracy_with_missing"], m["evaluated_accuracy"])


class TestInvalidAndRidV2(_V2Base):
    def _rows_with(self, extra_row: dict) -> list[dict]:
        rows = _make_synthetic_rows(30, seed=5)
        rows.append(extra_row)
        return rows

    def test_invalid_row_exit2_even_with_allow_missing(self):
        rows = self._rows_with({"rid": "bad-1#q", "kind": "choice", "lang": "en",
                                "route": "classification", "num_options": 4})
        _write_jsonl(self.base_path, rows)
        _write_jsonl(self.tuned_path, rows)
        code, _ = self._run(40, ["--allow-missing", "--cluster-rounds", "1000"])
        self.assertEqual(code, 2)
        self.assertFalse(self.out_path.exists())

    def test_missing_rid_exit2(self):
        bad = _make_pred_row("x")
        del bad["rid"]
        rows = self._rows_with(bad)
        _write_jsonl(self.base_path, rows)
        _write_jsonl(self.tuned_path, rows)
        code, _ = self._run(31)
        self.assertEqual(code, 2)

    def test_non_string_rid_exit2(self):
        bad = _make_pred_row("x")
        bad["rid"] = 12345
        rows = self._rows_with(bad)
        _write_jsonl(self.base_path, rows)
        _write_jsonl(self.tuned_path, rows)
        code, _ = self._run(31)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
