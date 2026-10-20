"""split.py 自检：分组不泄漏、分层、比例、benchmark 保底、可复现、隐私。

放在 datasets/general/ 根目录（与其余 8 个 test_*.py 一致，db-hf 的目录规范建议），
这样 tools/check.py 的 unittest discovery 能递归收进来，同时不用给 data/ 加 __init__.py。
被测脚本在 datasets/general/data/splits/split.py。
"""

import contextlib
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPLIT_DIR = HERE / "data" / "splits"
if str(SPLIT_DIR) not in sys.path:
    sys.path.insert(0, str(SPLIT_DIR))

import split as sp  # noqa: E402
import build_corpus as bc  # noqa: E402  （同目录：合并语料脚本）


def question(kind: str) -> dict:
    if kind == "noul":
        return {"key": "q", "kind": "noul", "prompt": "q?",
                "options": [{"key": "yes", "label": "是"}, {"key": "no", "label": "否"}]}
    if kind == "score":
        return {"key": "q", "kind": "score", "prompt": "q?",
                "scale": {"min": 0, "max": 4, "labels": ["0", "1", "2", "3", "4"]}}
    return {"key": "q", "kind": "choice", "prompt": "q?",
            "options": [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}]}


def item(index: int, *, domain="decision_mechanics", lang="en", state=None,
         group=None, kind="choice", dataset="syn") -> dict:
    record = {
        "id": f"db-syn-{index:08x}",
        "domain": domain,
        "lang": lang,
        "state": state if state is not None else f"state {index}",
        "questions": [question(kind)],
        "targets": {},
        "source": {"dataset": dataset, "revision": "0" * 40, "config": "default",
                   "split": "train", "row": index, "license": "cc0-1.0",
                   "url": "https://example.invalid/x"},
        "meta": {"converter": "test", "converter_version": "0", "created_at": "2026-10-05"},
    }
    if group:
        record["group_id"] = group
    return record


def corpus(*, groups=40, variants=4, langs=("en", "zh"),
           domains=("decision_mechanics", "human_judgment", "risk_harm"),
           kind_for=None) -> list:
    """默认：每请求 groups 个、各 variants 套变体（同 state、同 group_id）。"""
    items = []
    index = 0
    for group_index in range(groups):
        domain = domains[group_index % len(domains)]
        lang = langs[group_index % len(langs)]
        for variant in range(variants):
            kind = kind_for(group_index, variant) if kind_for else "choice"
            items.append(item(index, domain=domain, lang=lang,
                              state=f"SECRET-STATE-{group_index}", group=f"req-{group_index}",
                              kind=kind))
            index += 1
    return items


def records_for(items) -> list:
    """与 split.load_records 同形的 records（含 source：来源均衡按它统计）。"""
    return [{"index": i, "id": it["id"], "input": "syn", "line": i + 1,
             "domain": it["domain"], "lang": it["lang"],
             "source": str((it.get("source") or {}).get("dataset") or "(unknown)"),
             "state_norm": sp.normalize_state(it.get("state")),
             "declared": sp.declared_group(it),
             "kinds": tuple(sorted({q["kind"] for q in it["questions"]}))}
            for i, it in enumerate(items)]


def write_input(directory: Path, items) -> Path:
    path = directory / "items.jsonl"
    path.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
                    encoding="utf-8")
    return path


def run_quiet(argv) -> int:
    """测试统一走 public-demo 跑法（无盐、输出在临时目录=仓库外）：交付件必须带仓外私盐。"""
    argv = list(argv)
    if "--public-demo" not in argv and "--salt-file" not in argv:
        argv.append("--public-demo")
    with contextlib.redirect_stdout(io.StringIO()):
        return sp.run(argv)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GroupingTest(unittest.TestCase):
    def test_variants_with_same_group_stay_together(self):
        items = corpus(groups=30, variants=4)
        records = records_for(items)
        splits, labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=7,
                                                 min_per_domain=0, min_per_lang=0, min_per_kind=0)
        by_group = {}
        for label, split in zip(labels, splits):
            by_group.setdefault(label, set()).add(split)
        self.assertEqual(stats["groups"]["groups"], 30)
        self.assertEqual(stats["groups"]["largest_group"], 4)
        self.assertTrue(all(len(value) == 1 for value in by_group.values()), by_group)

    def test_same_state_without_group_id_stays_together(self):
        items = [item(i, state="同一个请求的四个候选集", kind="choice") for i in range(4)]
        items += [item(100 + i, state=f"独立 state {i}") for i in range(20)]
        records = records_for(items)
        splits, labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=7,
                                                 min_per_domain=0, min_per_lang=0, min_per_kind=0)
        first_four = {splits[i] for i in range(4)}
        self.assertEqual(len(first_four), 1, "同 state 无 group_id 也必须同区")
        self.assertEqual(stats["groups"]["groups"], 21)

    def test_request_id_in_meta_groups_items(self):
        items = []
        for variant in range(4):
            record = item(200 + variant, state=f"候选集变体 {variant} 的 state 不同")
            record["meta"]["request_id"] = "req-meta-1"
            items.append(record)
        items += [item(300 + i, state=f"独立 {i}") for i in range(10)]
        records = records_for(items)
        splits, _labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=7,
                                                  min_per_domain=0, min_per_lang=0, min_per_kind=0)
        self.assertEqual(len({splits[i] for i in range(4)}), 1, "meta.request_id 必须把变体并成一组")
        self.assertEqual(stats["groups"]["groups"], 11)

    def test_family_id_in_source_groups_items(self):
        items = []
        for variant in range(3):
            record = item(400 + variant, state=f"family 变体 {variant}")
            record["source"]["family_id"] = "fam-9"
            items.append(record)
        records = records_for(items)
        splits, _labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=7,
                                                  min_per_domain=0, min_per_lang=0, min_per_kind=0)
        self.assertEqual(len(set(splits)), 1)
        self.assertEqual(stats["groups"]["groups"], 1)

    def test_no_state_grouping_switch_keeps_rows_separate(self):
        items = [item(i, state="同一个请求", kind="choice") for i in range(4)]
        records = records_for(items)
        _splits, _labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=7,
                                                   use_state=False,
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=0)
        self.assertEqual(stats["groups"]["groups"], 4)


class ProportionTest(unittest.TestCase):
    def test_proportions_close_to_target(self):
        items = corpus(groups=50, variants=4)
        records = records_for(items)
        splits, _labels, _stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=11,
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=0)
        counts = {split: splits.count(split) for split in sp.SPLITS}
        for split, target in sp.DEFAULT_RATIOS.items():
            self.assertLess(abs(counts[split] / len(items) - target), 0.05, counts)

    def test_stratification_keeps_lang_and_domain_mix(self):
        items = corpus(groups=60, variants=3)
        records = records_for(items)
        splits, _labels, _stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=13,
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=0)
        global_lang = {}
        for record in records:
            global_lang[record["lang"]] = global_lang.get(record["lang"], 0) + 1
        total = len(records)
        for split in sp.SPLITS:
            members = [r for r, s in zip(records, splits) if s == split]
            for lang, count in global_lang.items():
                share = sum(1 for r in members if r["lang"] == lang) / len(members)
                self.assertLess(abs(share - count / total), 0.08, (split, lang))

    def test_ratio_override(self):
        items = corpus(groups=20, variants=2)
        records = records_for(items)
        ratios = {"train": 0.7, "test": 0.1, "validation": 0.1, "benchmark": 0.1}
        splits, _labels, _stats, _ = sp.assign_all(records, ratios=ratios, seed=3,
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=0)
        self.assertLess(abs(splits.count("train") / len(items) - 0.7), 0.05)


class LineSeparatorTest(unittest.TestCase):
    """U+2028 / U+2029 / U+0085 必须转义。

    它们在 JSON 里合法，但 Python 的 str.splitlines() 会把它们当换行，于是"换一种读法"就把一条记录
    从中间劈开（coverage.py 第一次读 items.jsonl 就是这么炸的）。本类同时守两件事：
    产物字节里没有裸分隔符，且用 splitlines() 读出来的行数正好等于条目数。
    """

    TRICKY = "\u2028前\u2029中\u0085后"

    def tricky_items(self):
        items = []
        for index in range(4):
            record = item(index, state=f"{self.TRICKY} state {index}", group=f"req-{index}")
            record["questions"][0]["prompt"] = f"q{self.TRICKY}?"
            items.append(record)
        return items

    def test_serializer_escapes_and_round_trips(self):
        line = sp._json_line({"state": self.TRICKY})
        for char in ("\u2028", "\u2029", "\u0085"):
            self.assertNotIn(char, line, repr(char))
        self.assertIn("\\u2028", line)
        self.assertEqual(json.loads(line)["state"], self.TRICKY)

    def test_products_have_no_bare_separators(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, self.tricky_items())
            out_dir = root / "out"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / "r.md"),
                                        "--benchmark-min-per-kind", "0",
                                        "--benchmark-min-per-domain", "0",
                                        "--benchmark-min-per-lang", "0"]), 0)
            for split in sp.SPLITS:
                self.assertEqual(sp.count_bare_line_separators(out_dir / f"{split}.jsonl"), 0, split)
                with gzip.open(out_dir / f"{split}.jsonl.gz", "rt", encoding="utf-8") as handle:
                    gz_text = handle.read()
                for char in ("\u2028", "\u2029", "\u0085"):
                    self.assertNotIn(char, gz_text, f"{split}.jsonl.gz")
            for name in ("benchmark.jsonl", "manifest.json", "README.md"):
                self.assertEqual(sp.count_bare_line_separators(out_dir / "benchmark-dataset" / name), 0, name)

    def test_splitlines_reads_back_the_same_row_count(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, self.tricky_items())
            out_dir = root / "out"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / "r.md"),
                                        "--benchmark-min-per-kind", "0",
                                        "--benchmark-min-per-domain", "0",
                                        "--benchmark-min-per-lang", "0"]), 0)
            states = []
            for split in sp.SPLITS:
                text = (out_dir / f"{split}.jsonl").read_text(encoding="utf-8")
                rows = load_lines(out_dir / f"{split}.jsonl")
                self.assertEqual(len(text.splitlines()), len(rows), f"{split} 被裸分隔符劈开了")
                states.extend(row["state"] for row in rows)
            # 无损：转义后读回来仍是原字符
            self.assertEqual(len(states), 4)
            for state in states:
                for char in ("\u2028", "\u2029", "\u0085"):
                    self.assertIn(char, state, repr(state))


class SecrecyTest(unittest.TestCase):
    """保密性必须是机器可验证的性质，而不是靠人记得。

    1) 私盐改变分配（恒可跑）；2) 同盐可复现；3) 无盐跑法复现不出交付件（集成，语料存在时跑）；
    4) 公开面扫描：所有被 git 跟踪的文件对 benchmark 记录零命中；5) 拒绝性：盐在仓内/无盐非 demo/demo 写仓内。
    """

    def bench_ids(self, items, splits):
        return {it["id"] for it, split in zip(items, splits) if split == "benchmark"}

    def test_salt_changes_benchmark(self):
        items = corpus(groups=40, variants=2)
        records = records_for(items)
        kwargs = dict(ratios=sp.DEFAULT_RATIOS, seed=7, min_per_domain=0, min_per_lang=0, min_per_kind=0)
        a = self.bench_ids(items, sp.assign_all(records, salt="salt-A", **kwargs)[0])
        b = self.bench_ids(items, sp.assign_all(records, salt="salt-B", **kwargs)[0])
        c = self.bench_ids(items, sp.assign_all(records, salt=None, **kwargs)[0])
        self.assertTrue(a and b and c)
        self.assertNotEqual(a, b, "换盐必须改变 benchmark 分配")
        self.assertNotEqual(a, c, "无盐跑法必须与带盐交付件不同")

    def test_same_salt_is_reproducible(self):
        items = corpus(groups=30, variants=2)
        records = records_for(items)
        kwargs = dict(ratios=sp.DEFAULT_RATIOS, seed=11, salt="same-salt",
                      min_per_domain=0, min_per_lang=0, min_per_kind=0)
        first = self.bench_ids(items, sp.assign_all(records, **kwargs)[0])
        second = self.bench_ids(items, sp.assign_all(records, **kwargs)[0])
        self.assertEqual(first, second)

    def test_benchmark_lang_whitelist(self):
        items = corpus(groups=40, variants=2, langs=("en", "zh"))
        records = records_for(items)
        splits, _labels, _stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=3,
                                                   salt="s", benchmark_langs=("en",),
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=0)
        zh_in_bench = [r for r, s in zip(records, splits) if s == "benchmark" and r["lang"] == "zh"]
        en_in_bench = [r for r, s in zip(records, splits) if s == "benchmark" and r["lang"] == "en"]
        self.assertEqual(zh_in_bench, [], "白名单外语言不得进 benchmark")
        self.assertTrue(en_in_bench)

    def test_salt_file_inside_repo_is_refused(self):
        inside = Path(sp.__file__).resolve().parent / "split.py"
        with self.assertRaises(sp.SplitError):
            sp.read_salt(inside, repo_root=sp.git_repo_root(inside.parent))

    def test_short_salt_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            path = Path(workspace) / "salt.txt"
            path.write_bytes(b"short")
            with self.assertRaises(sp.SplitError):
                sp.read_salt(path, repo_root=sp.git_repo_root(Path.cwd()))

    def test_no_salt_without_public_demo_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=4, variants=2))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = sp.run(["--input", str(source), "--out", str(root / "out"),
                               "--report", str(root / "r.md")])
            self.assertEqual(code, 3)
            self.assertFalse((root / "out").exists())

    def test_public_demo_inside_repo_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            source = write_input(Path(workspace), corpus(groups=4, variants=2))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = sp.run(["--input", str(source), "--public-demo",
                               "--out", str(sp.DEFAULT_OUT), "--report", str(sp.DEFAULT_REPORT)])
            self.assertEqual(code, 3)

    def test_public_run_does_not_reproduce_delivered_benchmark(self):
        corpus_path = Path("datasets/general/data/items.final.jsonl")
        delivered_path = Path("datasets/general/data/splits/benchmark.jsonl")
        if not corpus_path.is_file() or not delivered_path.is_file():
            self.skipTest("私有语料或交付件不在本机（已移出版本控制）")
        delivered = {json.loads(line)["id"] for line in
                     delivered_path.read_text(encoding="utf-8").split("\n") if line.strip()}
        with tempfile.TemporaryDirectory() as workspace:
            out_dir = Path(workspace) / "public-run"
            code = run_quiet(["--input", str(corpus_path), "--out", str(out_dir),
                              "--report", str(Path(workspace) / "report.md"),
                              "--benchmark-min-per-domain", "0", "--benchmark-min-per-lang", "0",
                              "--benchmark-min-per-kind", "0"])
            self.assertEqual(code, 0)
            public = {json.loads(line)["id"] for line in
                      (out_dir / "benchmark.jsonl").read_text(encoding="utf-8").split("\n") if line.strip()}
        self.assertTrue(public)
        self.assertNotEqual(public, delivered,
                            "只用仓库公开信息就能复现交付 benchmark——保密失效")

    def delivered_rows(self):
        delivered_path = Path("datasets/general/data/splits/benchmark.jsonl")
        if not delivered_path.is_file():
            self.skipTest("交付件不在本机（已移出版本控制）")
        return [json.loads(line) for line in
                delivered_path.read_text(encoding="utf-8").split("\n") if line.strip()]

    def test_tracked_files_contain_no_benchmark_records(self):
        """护栏（内容级）：**所有被 git 跟踪的文件**对 benchmark 的 id 与正文零命中。

        两种口径都查，且 .gz 先解压——文件级检查（有没有被 git 跟踪）挡不住内容级泄漏：
        曾经有派生索引把 benchmark 的全部 id 列在 .gz 里（本身不含答案，但能精确指认成员）。
        """
        rows = self.delivered_rows()
        repo_root = sp.git_repo_root(Path.cwd())
        if repo_root is None:
            self.skipTest("不在 git 仓库内")
        audit = sp.audit_public_surface(rows, root=repo_root)
        self.assertGreater(audit["files"], 0, "git ls-files 没返回任何文件，等于没扫")
        self.assertGreater(audit["ids"], 0)
        self.assertEqual(audit["hits"], [],
                         "公开面出现了 benchmark 成员：" +
                         "; ".join(f"{hit['file']}({hit['kind']})" for hit in audit["hits"][:5]))

    def test_audit_detects_injected_id_in_plain_and_gz(self):
        """注入验证：id 写进普通文件与 .gz，同一个扫描函数都必须报命中（护栏真的会响）。"""
        injected = "db-injected-secret-0001"
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            plain = root / "leak.jsonl"
            plain.write_text(json.dumps({"id": injected}) + "\n", encoding="utf-8")
            packed = root / "leak.jsonl.gz"
            with gzip.open(packed, "wb") as handle:
                handle.write((json.dumps({"id": injected}) + "\n").encode("utf-8"))
            plain_hit = sp.scan_public_surface([plain], ids=[injected], root=root)
            self.assertEqual(len(plain_hit), 1)
            self.assertEqual(plain_hit[0]["file"], "leak.jsonl")
            gz_hit = sp.scan_public_surface([packed], ids=[injected], root=root)
            self.assertEqual(len(gz_hit), 1, ".gz 里的泄漏必须解压后才查得到")
            self.assertEqual(gz_hit[0]["kind"], "id")
            self.assertEqual(sp.scan_public_surface([plain, packed],
                                                    ids=["db-something-else"], root=root), [],
                             "没注入时不得误报")

    def test_audit_detects_injected_state_text(self):
        """正文口径同样要响：state 原文进了公开文件就必须报出来。"""
        needle = "A secret benchmark state that must never appear in the public surface"
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            doc = root / "notes.md"
            doc.write_text(f"引用：{needle}\n", encoding="utf-8")
            hits = sp.scan_public_surface([doc], texts=[needle], root=root)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["kind"], "text")
            self.assertEqual(sp.scan_public_surface([doc], texts=["another state"], root=root), [])


class BenchmarkFloorTest(unittest.TestCase):
    def test_rare_kind_gets_floor(self):
        def kind_for(group_index, variant):
            return "score" if group_index < 3 else "choice"
        items = corpus(groups=60, variants=2, kind_for=kind_for)
        records = records_for(items)
        splits, _labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=5,
                                                  min_per_domain=0, min_per_lang=0, min_per_kind=4)
        benchmark = [r for r, s in zip(records, splits) if s == "benchmark"]
        score_items = [r for r in benchmark if "score" in r["kinds"]]
        self.assertGreaterEqual(len(score_items), 4, "稀有 kind 必须拿到保底配额")
        floors = {floor["cell"]: floor for floor in stats["benchmark_floors"]}
        self.assertTrue(any(cell.endswith("kind=score") for cell in floors))

    def test_floor_capped_when_class_too_small(self):
        def kind_for(group_index, variant):
            return "score" if group_index == 0 else "choice"
        items = corpus(groups=40, variants=2, kind_for=kind_for)
        records = records_for(items)
        _splits, _labels, stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=5,
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=50)
        capped = [floor for floor in stats["benchmark_floors"] if floor.get("capped")]
        self.assertTrue(capped, "该类不足下限时应标 capped 并取全部")
        scores = [floor for floor in stats["benchmark_floors"]
                  if floor["cell"].endswith("kind=score")]
        self.assertTrue(scores)
        self.assertTrue(all(floor["capped"] for floor in scores))
        self.assertEqual(sum(floor["have"] for floor in scores), 2)

    def test_benchmark_size_is_at_least_ten_percent(self):
        items = corpus(groups=80, variants=2)
        records = records_for(items)
        splits, _labels, _stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=9,
                                                   min_per_domain=0, min_per_lang=0, min_per_kind=0)
        self.assertGreaterEqual(splits.count("benchmark") / len(items), 0.08)


class LeakCheckTest(unittest.TestCase):
    def test_assignment_has_no_leaks(self):
        items = corpus(groups=25, variants=4)
        records = records_for(items)
        splits, labels, _stats, _ = sp.assign_all(records, ratios=sp.DEFAULT_RATIOS, seed=17,
                                                  min_per_domain=0, min_per_lang=0, min_per_kind=0)
        leaks = sp.leak_report(records, labels, splits, items)
        self.assertEqual(leaks["problem_count"], 0)
        self.assertEqual(leaks["groups_multi_split"], 0)
        self.assertEqual(leaks["states_multi_split"], 0)
        self.assertEqual(leaks["ids_multi_split"], 0)

    def test_injected_leak_is_detected(self):
        records = [{"index": 0, "id": "a", "domain": "d", "lang": "en", "state_norm": "same",
                    "declared": None, "kinds": (), "input": "x", "line": 1},
                   {"index": 1, "id": "b", "domain": "d", "lang": "en", "state_norm": "same",
                    "declared": None, "kinds": (), "input": "x", "line": 2}]
        leaks = sp.leak_report(records, ["g1", "g1"], ["train", "test"])
        self.assertEqual(leaks["groups_multi_split"], 1)
        self.assertEqual(leaks["states_multi_split"], 1)
        self.assertEqual(leaks["problem_count"], 2)


class DeterminismTest(unittest.TestCase):
    def test_rerun_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            items = corpus(groups=30, variants=3)
            source = write_input(root, items)
            outputs = []
            for run_index in (1, 2):
                out_dir = root / f"out{run_index}"
                report = root / f"report{run_index}.md"
                code = run_quiet(["--input", str(source), "--out", str(out_dir),
                                  "--report", str(report), "--seed", "4242",
                                  "--benchmark-min-per-kind", "2",
                                  "--benchmark-min-per-domain", "2",
                                  "--benchmark-min-per-lang", "2"])
                self.assertEqual(code, 0)
                outputs.append(out_dir)
            files = sorted(p.relative_to(outputs[0]).as_posix()
                           for p in outputs[0].rglob("*") if p.is_file())
            self.assertTrue(files)
            for name in files:
                self.assertEqual(digest(outputs[0] / name), digest(outputs[1] / name),
                                 f"{name} 两次运行不一致")
            self.assertEqual(digest(root / "report1.md"), digest(root / "report2.md"))

    def test_gzip_header_has_zero_mtime(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=10, variants=2))
            out_dir = root / "out"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / "r.md"),
                                        "--benchmark-min-per-kind", "0"]), 0)
            for name in ("train.jsonl.gz", "benchmark.jsonl.gz"):
                header = (out_dir / name).read_bytes()[:10]
                self.assertEqual(header[4:8], b"\x00\x00\x00\x00", name)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=10, variants=2))
            out_dir = root / "out"
            code = run_quiet(["--input", str(source), "--out", str(out_dir),
                              "--report", str(root / "r.md"), "--dry-run"])
            self.assertEqual(code, 0)
            self.assertFalse(out_dir.exists())
            self.assertFalse((root / "r.md").exists())


class PrivacyTest(unittest.TestCase):
    def test_report_card_and_manifest_have_no_sample_content(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=20, variants=2))
            out_dir = root / "out"
            report = root / "split-report.md"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(report),
                                        "--benchmark-min-per-kind", "0",
                                        "--benchmark-min-per-domain", "0",
                                        "--benchmark-min-per-lang", "0"]), 0)
            for path in (report, out_dir / "benchmark-dataset" / "README.md",
                         out_dir / "benchmark-dataset" / "manifest.json"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("SECRET-STATE", text, f"{path} 泄漏了 benchmark 样本内容")
            benchmark_text = (out_dir / "benchmark.jsonl").read_text(encoding="utf-8")
            self.assertIn("SECRET-STATE", benchmark_text)

    def test_report_has_leak_section_and_seed(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=15, variants=2))
            report = root / "split-report.md"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(root / "out"),
                                        "--report", str(report), "--seed", "99",
                                        "--benchmark-min-per-kind", "0",
                                        "--benchmark-min-per-domain", "0",
                                        "--benchmark-min-per-lang", "0"]), 0)
            text = report.read_text(encoding="utf-8")
            for token in ("随机种子：99", "## 6. 泄漏检查", "跨分区的组：0", "结论：**空**",
                          "中文侧分组 id 门禁", "## 3. 数据成色与已知缺口",
                          "## 9. 可复现性", "逐字节一致", "侧只有单一来源"):
                self.assertIn(token, text)


class GroupIdGateTest(unittest.TestCase):
    """中文侧没有显式分组 id 时必须拒绝切分，绝不能退化成按行切。"""

    def zh_items(self, group):
        return [item(i, lang="zh", state=f"请求 {i} 的第 {i} 套候选", group=group) for i in range(4)]

    def test_zh_without_group_id_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, self.zh_items(None))
            code = run_quiet(["--input", str(source), "--out", str(root / "out"),
                              "--report", str(root / "r.md"), "--dry-run"])
            self.assertEqual(code, 3)
            self.assertFalse((root / "out").exists())

    def test_zh_with_group_id_passes(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, self.zh_items("req-1"))
            code = run_quiet(["--input", str(source), "--out", str(root / "out"),
                              "--report", str(root / "r.md"), "--dry-run"])
            self.assertEqual(code, 0)

    def test_english_without_group_id_is_fine(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=5, variants=2, langs=("en",)))
            code = run_quiet(["--input", str(source), "--out", str(root / "out"),
                              "--report", str(root / "r.md"), "--dry-run"])
            self.assertEqual(code, 0)

    def test_escape_hatch_allows_missing_group_id(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, self.zh_items(None))
            code = run_quiet(["--input", str(source), "--out", str(root / "out"),
                              "--report", str(root / "r.md"), "--dry-run",
                              "--allow-missing-group-id"])
            self.assertEqual(code, 0)

    def test_gap_report_counts_zh_items(self):
        records = records_for(self.zh_items(None))
        gaps = sp.group_id_gaps(records)
        self.assertEqual(gaps["total"], 4)
        self.assertTrue(all("lang=zh" in key for key in gaps["missing"]))

    def test_default_input_is_final_corpus(self):
        names = [path.name for path in sp.DEFAULT_INPUTS]
        self.assertEqual(names, ["items.final.jsonl"])


class InputValidationTest(unittest.TestCase):
    def test_duplicate_ids_are_fatal_unless_allowed(self):
        with tempfile.TemporaryDirectory() as workspace:
            path = Path(workspace) / "items.jsonl"
            row = json.dumps(item(1), ensure_ascii=False)
            path.write_text(row + "\n" + row + "\n", encoding="utf-8")
            with self.assertRaises(sp.SplitError):
                sp.load_records([path])
            items, _records, stats = sp.load_records([path], allow_duplicates=True)
            self.assertEqual(len(items), 1)
            self.assertEqual(stats["duplicate_ids"], 1)

    def test_missing_field_is_fatal(self):
        with tempfile.TemporaryDirectory() as workspace:
            path = Path(workspace) / "items.jsonl"
            broken = item(1)
            del broken["domain"]
            path.write_text(json.dumps(broken, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(sp.SplitError):
                sp.load_records([path])

    def test_broken_json_is_reported(self):
        with tempfile.TemporaryDirectory() as workspace:
            path = Path(workspace) / "items.jsonl"
            path.write_text("{not json}\n", encoding="utf-8")
            with self.assertRaises(sp.SplitError):
                sp.load_records([path])

    def test_resolve_inputs_skips_splits_outputs_and_indexes(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            row = json.dumps(item(1), ensure_ascii=False) + "\n"
            inside = root / "data" / "splits"
            inside.mkdir(parents=True)
            (inside / "train.jsonl").write_text(row, encoding="utf-8")
            outside = root / "data" / "zh"
            outside.mkdir(parents=True)
            (outside / "zh.jsonl").write_text(row, encoding="utf-8")
            (outside / "zh-group-index.jsonl").write_text(
                json.dumps({"group_id": "g1", "rows": [1, 2]}, ensure_ascii=False) + "\n",
                encoding="utf-8")
            ignored: list = []
            found = sp.resolve_inputs([root], ignored=ignored)
            names = [path.name for path in found]
            self.assertIn("zh.jsonl", names)
            self.assertNotIn("train.jsonl", names)
            self.assertIn("zh-group-index.jsonl", [Path(path).name for path in ignored])

    def test_missing_input_returns_two(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            code = run_quiet(["--input", str(root / "nope.jsonl"),
                              "--out", str(root / "out"), "--report", str(root / "r.md")])
            self.assertEqual(code, 2)

    def test_bad_ratios_return_two(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=5, variants=2))
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(root / "out"),
                                        "--ratios", "train=0.5,test=0.5"]), 2)
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(root / "out"),
                                        "--ratios", "nope=1,test=0,validation=0,benchmark=0"]), 2)


class OutputShapeTest(unittest.TestCase):
    def test_split_files_and_benchmark_dataset(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=20, variants=3))
            out_dir = root / "out"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / "r.md"),
                                        "--benchmark-min-per-kind", "2"]), 0)
            for split in sp.SPLITS:
                self.assertTrue((out_dir / f"{split}.jsonl").is_file(), split)
                self.assertTrue((out_dir / f"{split}.jsonl.gz").is_file(), split)
            for name in ("README.md", "manifest.json", "benchmark.jsonl", "benchmark.jsonl.gz"):
                self.assertTrue((out_dir / "benchmark-dataset" / name).is_file(), name)
            manifest = json.loads((out_dir / "benchmark-dataset" / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["private"])
            self.assertEqual(manifest["items"], len(load_lines(out_dir / "benchmark.jsonl")))
            self.assertTrue(manifest["sources"])

    def test_every_item_appears_exactly_once(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            items = corpus(groups=25, variants=2)
            source = write_input(root, items)
            out_dir = root / "out"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / "r.md"),
                                        "--benchmark-min-per-kind", "0",
                                        "--benchmark-min-per-domain", "0",
                                        "--benchmark-min-per-lang", "0"]), 0)
            ids = []
            for split in sp.SPLITS:
                ids.extend(row["id"] for row in load_lines(out_dir / f"{split}.jsonl"))
            self.assertEqual(len(ids), len(items))
            self.assertEqual(len(set(ids)), len(items))

    def test_gz_round_trips_jsonl(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = write_input(root, corpus(groups=10, variants=2))
            out_dir = root / "out"
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / "r.md"),
                                        "--benchmark-min-per-kind", "0"]), 0)
            plain = (out_dir / "train.jsonl").read_text(encoding="utf-8")
            with gzip.open(out_dir / "train.jsonl.gz", "rt", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), plain)


def load_lines(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def corpus_by_source(sizes, *, variants=2, lang="en", kind_for=None) -> list:
    """按 {dataset: 请求组数} 造语料；每组 variants 条变体共享 group_id 与 state。"""
    items = []
    index = 0
    for source, groups in sizes.items():
        for group_index in range(groups):
            for variant in range(variants):
                record = item(index, lang=lang, state=f"{source}-state-{group_index}",
                              group=f"{source}-req-{group_index}",
                              kind=kind_for(source, group_index, variant) if kind_for else "choice",
                              dataset=source)
                items.append(record)
                index += 1
    return items


def supplement_item(index: int, *, lang="zh", kind="noul", origin="taxonomy",
                    item_id=None, group=None) -> dict:
    """train-only 降级补充条目：origin 默认 taxonomy（非原生）。"""
    record = item(index, lang=lang, state=f"supplement state {index}",
                  group=group or f"supp-req-{index}", kind=kind, dataset="supp")
    record["id"] = item_id or f"db-supp-{index:08x}"
    record["questions"][0]["origin"] = origin
    return record


class SourceBalanceTest(unittest.TestCase):
    """benchmark 来源均衡：硬上限、来源下限、水位法、以及交付件自检。"""

    def sizes(self):
        # 仿真实语料：一个来源占近一半，另有大小不一的 5 个来源
        return {"big": 400, "second": 200, "third": 80, "fourth": 80, "fifth": 60, "sixth": 40}

    def assign(self, items, **kwargs):
        records = records_for(items)
        options = dict(ratios=sp.DEFAULT_RATIOS, seed=13, min_per_domain=0,
                       min_per_lang=0, min_per_kind=0)
        options.update(kwargs)
        return items, sp.assign_all(records, **options)

    def test_source_cap_is_enforced(self):
        items, (splits, _labels, stats, _floors) = self.assign(corpus_by_source(self.sizes()))
        bench = [it for it, split in zip(items, splits) if split == "benchmark"]
        counts = Counter(it["source"]["dataset"] for it in bench)
        report = stats["benchmark_source_policy"]
        policy = report["policy"]
        self.assertEqual(policy["cap_policy"], "policy", "6 个来源时应当由政策上限决定")
        self.assertTrue(policy["cap_enforced"])
        self.assertTrue(report["cap_ok"])
        self.assertLessEqual(max(counts.values()) / len(bench), policy["max_source_share"])
        self.assertGreaterEqual(len(counts), 4, "上限 25% 时至少要 4 个来源才撑得起来")
        self.assertTrue(all(row["items"] <= policy["cap_items"] for row in report["rows"]))

    def test_every_source_gets_a_floor(self):
        items, (splits, _labels, stats, _floors) = self.assign(corpus_by_source(self.sizes()))
        bench = [it for it, split in zip(items, splits) if split == "benchmark"]
        counts = Counter(it["source"]["dataset"] for it in bench)
        report = stats["benchmark_source_policy"]
        self.assertEqual(set(counts), set(self.sizes()), "每个来源都要被收集一点")
        self.assertTrue(all(count >= report["policy"]["floor_items"] for count in counts.values()))

    def test_single_source_relaxes_cap_to_feasible_bound(self):
        """只有一个来源时无从谈均衡：放宽到可行界并如实标注，而不是把 benchmark 压小。"""
        items, (splits, _labels, stats, _floors) = self.assign(corpus_by_source({"only": 60}))
        self.assertGreaterEqual(splits.count("benchmark") / len(items), 0.08)
        policy = stats["benchmark_source_policy"]["policy"]
        self.assertEqual(policy["cap_policy"], "feasible_bound")
        self.assertFalse(policy["cap_enforced"])

    def test_source_quota_water_filling_is_deterministic(self):
        pool = {"a": 10000, "b": 5000, "c": 1000, "d": 800, "e": 300, "f": 200}
        plan = sp.benchmark_source_quota(pool, 1600, max_share=0.25, min_share=0.05)
        quota = plan["quota"]
        self.assertEqual(sum(quota.values()), 1600)
        self.assertEqual(plan["cap_policy"], "policy")
        self.assertEqual(plan["cap"], 400)
        self.assertLessEqual(max(quota.values()), 400, "大来源必须被上限削顶")
        self.assertTrue(all(value >= plan["floor"] for value in quota.values()), "小来源必须被下限托底")
        self.assertEqual(quota["a"], 400)
        self.assertGreater(quota["b"], quota["c"], "上限之下仍按规模分配，而不是平均分")
        self.assertEqual(plan, sp.benchmark_source_quota(pool, 1600, max_share=0.25, min_share=0.05))

    def test_delivered_manifest_satisfies_its_own_cap(self):
        """交付件自检：split-manifest.json 记的实际占比不得超过它自己记的上限。"""
        path = sp.DEFAULT_OUT / "split-manifest.json"
        if not path.is_file():
            self.skipTest("交付件不在本机（未跑过切分）")
        policy = (json.loads(path.read_text(encoding="utf-8")).get("benchmark_source_policy") or {})
        if not policy.get("policy"):
            self.skipTest("manifest 里没有来源均衡记录（旧版产物）")
        self.assertTrue(policy["cap_ok"])
        self.assertLessEqual(policy["max_share"], policy["policy"]["max_source_share"] + 1e-9)
        self.assertTrue(all(row["items"] <= policy["policy"]["cap_items"] for row in policy["rows"]))
        self.assertGreaterEqual(len(policy["rows"]), 4)


class LangPolicyTest(unittest.TestCase):
    """语料里每种语言都必须显式决定进不进 benchmark——漏一种就拒绝切分。"""

    def run_with(self, root, extra):
        source = write_input(root, corpus(groups=12, variants=2, langs=("en", "zh")))
        out_dir = root / "out"
        code = run_quiet(["--input", str(source), "--out", str(out_dir),
                          "--report", str(root / "r.md")] + extra)
        return code, out_dir

    def test_missing_declaration_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            code, out_dir = self.run_with(Path(workspace), ["--benchmark-lang", "en"])
            self.assertEqual(code, 3, "zh 既没进白名单也没被显式排除时必须拒绝")
            self.assertFalse((out_dir / "benchmark.jsonl").exists())

    def test_conflicting_declaration_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            code, _ = self.run_with(Path(workspace),
                                    ["--benchmark-lang", "en", "--benchmark-exclude-lang", "en=理由"])
            self.assertEqual(code, 3)

    def test_empty_reason_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            code, _ = self.run_with(Path(workspace),
                                    ["--benchmark-lang", "en", "--benchmark-exclude-lang", "zh="])
            self.assertEqual(code, 2)

    def test_explicit_exclusion_passes_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            code, out_dir = self.run_with(root, ["--benchmark-lang", "en",
                                                 "--benchmark-exclude-lang", "zh=公开历史里有答案索引"])
            self.assertEqual(code, 0)
            bench = load_lines(out_dir / "benchmark.jsonl")
            self.assertTrue(bench)
            self.assertEqual({row["lang"] for row in bench}, {"en"})
            manifest = json.loads((out_dir / "split-manifest.json").read_text(encoding="utf-8"))
            policy = manifest["benchmark_lang_policy"]
            self.assertEqual(policy["benchmark_langs"], ["en"])
            self.assertEqual(policy["exclusions"], {"zh": "公开历史里有答案索引"})
            self.assertEqual(policy["missing"], [])
            report = (root / "r.md").read_text(encoding="utf-8")
            self.assertIn("公开历史里有答案索引", report, "排除理由必须写进报告")
            self.assertIn("显式排除", report)


class TrainSupplementTest(unittest.TestCase):
    """train-only 降级补充：只动 train，其它三区逐字节不变。"""

    def run_pair(self, root, supplement_path=None):
        source = write_input(root, corpus(groups=20, variants=2))
        outputs = {}
        for name, extra in (("plain", []), ("with_supplement", ["--train-supplement", str(supplement_path)])):
            if supplement_path is None and name == "with_supplement":
                continue
            out_dir = root / name
            self.assertEqual(run_quiet(["--input", str(source), "--out", str(out_dir),
                                        "--report", str(root / f"{name}.md")] + extra), 0)
            outputs[name] = out_dir
        return outputs

    def test_supplement_only_appends_to_train(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            supplement = root / "supp.jsonl"
            supplement.write_text("".join(
                json.dumps(supplement_item(i), ensure_ascii=False) + "\n" for i in range(6)),
                encoding="utf-8")
            outputs = self.run_pair(root, supplement)
            plain, with_supplement = outputs["plain"], outputs["with_supplement"]
            for name in ("test.jsonl", "test.jsonl.gz", "validation.jsonl", "validation.jsonl.gz",
                         "benchmark.jsonl", "benchmark.jsonl.gz"):
                self.assertEqual(digest(plain / name), digest(with_supplement / name),
                                 f"{name} 不该受补充集影响")
            plain_ids = {row["id"] for row in load_lines(plain / "train.jsonl")}
            supplement_ids = {row["id"] for row in load_lines(with_supplement / "train.jsonl")}
            added = supplement_ids - plain_ids
            self.assertEqual(len(added), 6, "补充集必须整批进 train")
            manifest = json.loads((with_supplement / "split-manifest.json").read_text(encoding="utf-8"))
            corpus_train = len(load_lines(plain / "train.jsonl"))
            self.assertEqual(manifest["corpus_counts"]["train"], corpus_train)
            self.assertEqual(manifest["counts"]["train"], corpus_train + 6)
            self.assertEqual(manifest["items"],
                             sum(len(load_lines(with_supplement / f"{split}.jsonl"))
                                 for split in sp.SPLITS))
            self.assertEqual(manifest["supplement"][0]["items"], 6)
            self.assertEqual(manifest["supplement"][0]["scope"].startswith("train only"), True)
            report = (root / "with_supplement.md").read_text(encoding="utf-8")
            self.assertIn("## 11. origin 构成", report)
            self.assertIn("taxonomy", report)
            for name in ("test.jsonl", "validation.jsonl", "benchmark.jsonl"):
                for row in load_lines(with_supplement / name):
                    self.assertNotIn(row["id"], added, "补充集不得进 train 以外的分区")

    def test_native_supplement_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            supplement = root / "native.jsonl"
            supplement.write_text(json.dumps(supplement_item(0, origin="source"),
                                             ensure_ascii=False) + "\n", encoding="utf-8")
            source = write_input(root, corpus(groups=8, variants=2))
            code = run_quiet(["--input", str(source), "--out", str(root / "out"),
                              "--report", str(root / "r.md"),
                              "--train-supplement", str(supplement)])
            self.assertEqual(code, 2, "原生条目必须走正常切分，不能从补充集塞进 train")

    def test_supplement_id_overlap_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            items = corpus(groups=8, variants=2)
            source = write_input(root, items)
            supplement = root / "dup.jsonl"
            supplement.write_text(json.dumps(supplement_item(0, item_id=items[0]["id"]),
                                             ensure_ascii=False) + "\n", encoding="utf-8")
            code = run_quiet(["--input", str(source), "--out", str(root / "out"),
                              "--report", str(root / "r.md"),
                              "--train-supplement", str(supplement)])
            self.assertEqual(code, 2)


class DefaultOutputGuardTest(unittest.TestCase):
    """默认 --out/--report 不得误伤已存在的交付件。"""

    def run_bare(self, root, extra=()):
        saved = (sp.DEFAULT_OUT, sp.DEFAULT_REPORT)
        sp.DEFAULT_OUT, sp.DEFAULT_REPORT = root / "splits", root / "report.md"
        try:
            source = write_input(root, corpus(groups=6, variants=2))
            return run_quiet(["--input", str(source)] + list(extra))
        finally:
            sp.DEFAULT_OUT, sp.DEFAULT_REPORT = saved

    def test_bare_run_refuses_to_overwrite_delivery(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "splits").mkdir()
            (root / "splits" / "split-manifest.json").write_text("{}", encoding="utf-8")
            (root / "report.md").write_text("旧报告", encoding="utf-8")
            self.assertEqual(self.run_bare(root), 3)
            self.assertEqual((root / "splits" / "split-manifest.json").read_text(encoding="utf-8"), "{}")
            self.assertEqual((root / "report.md").read_text(encoding="utf-8"), "旧报告")

    def test_force_allows_overwrite(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "splits").mkdir()
            (root / "splits" / "split-manifest.json").write_text("{}", encoding="utf-8")
            (root / "report.md").write_text("旧报告", encoding="utf-8")
            self.assertEqual(self.run_bare(root, ["--force"]), 0)
            self.assertNotEqual((root / "report.md").read_text(encoding="utf-8"), "旧报告")

    def test_fresh_default_location_is_allowed(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            self.assertEqual(self.run_bare(root), 0)
            self.assertTrue((root / "splits" / "split-manifest.json").is_file())


class SourceFloorTest(unittest.TestCase):
    """绝对来源下限（--benchmark-min-source-items）：语料变大后固定 5% 会抽干小来源。"""

    def test_absolute_floor_overrides_share_floor(self):
        # 一个只有 100 条的小来源：自然占比 0.28%（约 11 条），必须被绝对下限托到 100 条。
        # 注意不能设 min_share=0.05：那会算出 200 条的下限、按设计取 max(200, 100)=200，
        # 就测不到"绝对下限"本身了。
        pool = {"a": 9000, "b": 9000, "c": 9000, "d": 9000, "e": 100}
        plan = sp.benchmark_source_quota(pool, 4000, max_share=0.25, min_share=0.01, min_items=100)
        self.assertEqual(plan["floor"], 100)
        self.assertEqual(plan["quota"]["e"], 100, "小来源必须拿到绝对下限，而不是按占比只分到 11 条")
        self.assertTrue(all(value >= 100 for value in plan["quota"].values()))
        self.assertEqual(sum(plan["quota"].values()), 4000)
        # 占比下限更大时（5% → 200 条）按 max() 取占比下限，证明"两者取大"的方向
        share_floor = sp.benchmark_source_quota(pool, 4000, max_share=0.25,
                                                min_share=0.05, min_items=100)
        self.assertEqual(share_floor["floor"], 200)

    def test_zero_floor_keeps_pure_proportional(self):
        # 5 个来源 → 25% 上限可行（policy 生效），此时不设下限就是"按池子比例 + 上限削顶"。
        plan = sp.benchmark_source_quota({"a": 4000, "b": 3000, "c": 2000, "d": 800, "e": 200},
                                         1000, max_share=0.25, min_share=0.0, min_items=0)
        self.assertEqual(plan["floor"], 0)
        self.assertEqual(sum(plan["quota"].values()), 1000)
        self.assertEqual(plan["quota"]["e"], 50, "没有下限时小来源按比例分，不会被托底")
        self.assertLess(plan["quota"]["e"], 100)


class PublicReferenceExclusionTest(unittest.TestCase):
    """被公开文件引用过的条目永不进 benchmark（--exclude-public-items 的核心）。"""

    def test_excluded_items_never_enter_benchmark(self):
        items = corpus(groups=30, variants=2, langs=("en",))
        records = records_for(items)
        excluded = frozenset({it["id"] for it in items[:10]})
        splits, _labels, stats, _floors = sp.assign_all(
            records, ratios=sp.DEFAULT_RATIOS, seed=21, salt="s",
            min_per_domain=0, min_per_lang=0, min_per_kind=0, exclude_ids=excluded)
        bench_ids = {it["id"] for it, split in zip(items, splits) if split == "benchmark"}
        self.assertEqual(bench_ids & set(excluded), set(), "被公开引用的条目不得进 benchmark")
        self.assertGreater(stats["benchmark_source_policy"]["excluded_public_items"], 0)

    def test_scan_referenced_ids_finds_ids_in_plain_and_gz(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            plain = root / "doc.md"
            plain.write_text("示例：db-procedural-typed-decisions-7fbb2123 与 db-bigbench-00aa11bb\n",
                             encoding="utf-8")
            packed = root / "notes.jsonl.gz"
            with gzip.open(packed, "wb") as handle:
                handle.write(b'{"id": "db-cosmos-qa-1234abcd"}\n')
            found = sp.scan_referenced_ids(None, extra_paths=[plain, packed])
            self.assertEqual(found["referenced_ids"],
                             {"db-procedural-typed-decisions-7fbb2123", "db-bigbench-00aa11bb",
                              "db-cosmos-qa-1234abcd"})
            skipped = sp.scan_referenced_ids(None, extra_paths=[plain], skip_paths=[plain])
            self.assertEqual(skipped["referenced_ids"], set(), "被跳过的派生件不得产生引用")


class BuildCorpusTest(unittest.TestCase):
    """合并脚本：基座字节保留、id 前缀防冲突、确定性、可预期的拒绝。"""

    def write_items(self, path, items):
        path.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
                        encoding="utf-8")
        return path

    def base_items(self):
        return [item(i, dataset="base") for i in range(5)]

    def add_items(self):
        rows = []
        for i in range(3):
            row = item(100 + i, dataset="add")
            row["id"] = f"db-bigbench-{i:08x}"
            rows.append(row)
        return rows

    def test_merge_preserves_base_bytes_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = self.write_items(root / "base.jsonl", self.base_items())
            add = self.write_items(root / "add.jsonl", self.add_items())
            out1, out2 = root / "merged1.jsonl", root / "merged2.jsonl"
            for out in (out1, out2):
                ledger = bc.merge(base, [add], out, expect_total=8)
                self.assertEqual(ledger["total_items"], 8)
            self.assertEqual(out1.read_bytes(), out2.read_bytes(), "同输入两次合并必须逐字节一致")
            base_lines = base.read_text(encoding="utf-8").split("\n")[:5]
            self.assertTrue(out1.read_text(encoding="utf-8").startswith("\n".join(base_lines) + "\n"),
                            "基座条目必须按原始字节保留在文件开头")

    def test_prefix_or_id_collision_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = self.write_items(root / "base.jsonl", self.base_items())
            clash = item(200, dataset="clash")
            clash["id"] = self.base_items()[0]["id"]
            add = self.write_items(root / "add.jsonl", [clash])
            with self.assertRaises(bc.MergeError):
                bc.merge(base, [add], root / "out.jsonl")

    def test_unexpected_total_is_refused(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = self.write_items(root / "base.jsonl", self.base_items())
            add = self.write_items(root / "add.jsonl", self.add_items())
            with self.assertRaises(bc.MergeError):
                bc.merge(base, [add], root / "out.jsonl", expect_total=999)

    def test_gz_output_is_deterministic(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = self.write_items(root / "base.jsonl", self.base_items())
            add = self.write_items(root / "add.jsonl", self.add_items())
            bc.merge(base, [add], root / "m1.jsonl", gz_out=root / "m1.jsonl.gz")
            bc.merge(base, [add], root / "m2.jsonl", gz_out=root / "m2.jsonl.gz")
            self.assertEqual((root / "m1.jsonl.gz").read_bytes(),
                             (root / "m2.jsonl.gz").read_bytes(), "gzip mtime=0 → 逐字节一致")


class RotationExclusionTest(unittest.TestCase):
    """事故轮换：--benchmark-exclude-ids 读仓外永久名单，名单里的 id 永不进 benchmark。"""

    def write_ids(self, path, lines):
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return path

    def test_load_excluded_ids_parses_comments_and_dedupes(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            path = self.write_ids(root / "exclude.txt", [
                "# benchmark 轮换排除名单（注释行忽略）",
                "",
                "db-jev-distill-v3-0000aaaa",
                "  db-bigbench-1111bbbb  ",
                "db-jev-distill-v3-0000aaaa",
            ])
            loaded = sp.load_excluded_ids(path, repo_root=sp.git_repo_root(Path.cwd()))
            self.assertEqual(loaded["ids"],
                             {"db-jev-distill-v3-0000aaaa", "db-bigbench-1111bbbb"})
            self.assertEqual(loaded["lines"], 3)
            self.assertEqual(loaded["unique"], 2)
            self.assertEqual(len(loaded["file_sha256"]), 64)

    def test_load_excluded_ids_rejects_path_inside_repo(self):
        repo_root = sp.git_repo_root(Path.cwd())
        if repo_root is None:
            self.skipTest("不在 git 仓库内")
        inside = Path(sp.__file__).resolve()   # 仓库内的文件即可触发"必须在仓库外"
        with self.assertRaises(sp.SplitError):
            sp.load_excluded_ids(inside, repo_root=repo_root)

    def test_load_excluded_ids_rejects_non_id_lines(self):
        with tempfile.TemporaryDirectory() as workspace:
            path = self.write_ids(Path(workspace) / "bad.txt", ["db-ok-0000aaaa", "not-an-id"])
            with self.assertRaises(sp.SplitError):
                sp.load_excluded_ids(path, repo_root=sp.git_repo_root(Path.cwd()))

    def test_rotation_ids_never_enter_benchmark(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            items = corpus(groups=30, variants=2, langs=("en",))
            source = write_input(root, items)
            leaked = sorted(it["id"] for it in items)[:5]
            exclude_path = self.write_ids(root / "exclude.txt",
                                          ["# 泄漏名单"] + leaked)
            out_dir = root / "out"
            code = run_quiet(["--input", str(source), "--out", str(out_dir),
                              "--report", str(root / "r.md"),
                              "--benchmark-exclude-ids", str(exclude_path),
                              "--benchmark-min-per-kind", "0"])
            self.assertEqual(code, 0)
            bench = load_lines(out_dir / "benchmark.jsonl")
            bench_ids = {row["id"] for row in bench}
            self.assertEqual(bench_ids & set(leaked), set(),
                             "轮换排除名单里的 id 不得出现在 benchmark")
            manifest = json.loads((out_dir / "split-manifest.json").read_text(encoding="utf-8"))
            excl = manifest["benchmark_exclusions"]
            self.assertTrue(excl["rotation_enabled"])
            self.assertEqual(excl["rotation_exclude_ids"], 5)
            self.assertEqual(excl["rotation_ids_in_corpus"], 5)
            self.assertIsNotNone(excl["rotation_exclude_file_sha256"])
            report = (root / "r.md").read_text(encoding="utf-8")
            self.assertIn("永久排除名单", report)
            self.assertIn("§10.5", report)


if __name__ == "__main__":
    unittest.main()
