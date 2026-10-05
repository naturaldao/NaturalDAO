#!/usr/bin/env python3
"""fetch.py 的离线测试：用假 transport 复现 datasets-server 的响应形状，不联网。

覆盖：分页计划、429/5xx 退避、非重试错误、manifest 字段、断点续跑、
产物与 manifest 不一致时拒绝续跑、revision 漂移、未固定 revision 的来源跳过、
含 + 的 config 名必须转义（+ 在 query 里会被解成空格，是实测踩过的坑）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fetch = load_module("decision_base_fetch", HERE / "fetch.py")

REVISION = "a" * 40
DATASET = "Example/typed-decisions"
CONFIG = "default+control"          # 故意带 +，验证转义
FEATURES = [{"feature_idx": 0, "name": "state", "type": {"dtype": "string", "_type": "Value"}},
            {"feature_idx": 1, "name": "kind", "type": {"dtype": "string", "_type": "Value"}}]


class FakeServer:
    """按 URL 前缀回答的假 datasets-server。

    failures 是“前 N 次非 HF-API 请求返回的状态码”列表，逐次弹出，便于构造退避与中断。
    """

    def __init__(self, total=250, sha=REVISION, failures=None, page_size=100, fail_rows_offset=None):
        self.total = total
        self.sha = sha
        self.failures = list(failures or [])
        self.page_size = page_size
        self.fail_rows_offset = fail_rows_offset      # 该 offset 起的行请求一律 500（模拟中断）
        self.calls = []
        self.row_requests = []

    def __call__(self, url):
        self.calls.append(url)
        if url.startswith("https://huggingface.co/api/datasets/"):
            return 200, json.dumps({"sha": self.sha, "cardData": {"license": "apache-2.0"}}).encode()
        if self.failures:
            return self.failures.pop(0), json.dumps({"error": "busy"}).encode()
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        endpoint = parsed.path.strip("/")
        if endpoint == "splits":
            return 200, json.dumps({"splits": [
                {"dataset": DATASET, "config": CONFIG, "split": "train"},
                {"dataset": DATASET, "config": CONFIG, "split": "test"}]}).encode()
        if endpoint == "first-rows":
            return 200, json.dumps({"features": FEATURES, "rows": []}).encode()
        if endpoint == "rows":
            offset = int(query["offset"])
            length = int(query["length"])
            if self.fail_rows_offset is not None and offset >= self.fail_rows_offset and length > 1:
                return 500, json.dumps({"error": "interrupted"}).encode()
            self.row_requests.append((offset, length, query.get("config")))
            count = max(0, min(length, self.total - offset))
            rows = [{"row_idx": offset + index,
                     "row": {"state": f"state {offset + index}", "kind": "noul"}}
                    for index in range(count)]
            return 200, json.dumps({"features": FEATURES, "rows": rows,
                                    "num_rows_total": self.total,
                                    "num_rows_per_page": 100, "partial": False}).encode()
        raise AssertionError(f"未预期的 URL {url}")


def make_source(**overrides):
    source = {"slug": "example", "dataset": DATASET, "revision": REVISION,
              "config": CONFIG, "split": "train", "license": "apache-2.0",
              "converter": "jev_typed", "domain": "decision_mechanics", "lang": "en",
              "row_limit": 250, "sampling": {"strategy": "head"}}
    source.update(overrides)
    return source


def quiet(*_args, **_kwargs):
    return None


class PlanTests(unittest.TestCase):
    def test_head_plan_respects_limit_and_page_size(self):
        self.assertEqual(fetch.build_plan("head", 250, 250, page_size=100),
                         [(0, 100), (100, 100), (200, 50)])
        self.assertEqual(fetch.build_plan("head", 250, 30, page_size=100), [(0, 30)])
        self.assertEqual(fetch.build_plan("head", 30, 250, page_size=100), [(0, 30)])

    def test_windows_plan_is_spread_and_bounded(self):
        plan = fetch.build_plan("windows", 10_000, 300, page_size=100, window_size=100,
                                n_windows=3, seed=7)
        self.assertEqual(len(plan), 3)
        self.assertTrue(all(length <= 100 for _, length in plan))
        self.assertLess(plan[0][0], 1_000)
        self.assertGreater(plan[-1][0], 8_000)

    def test_windows_span_bounds_deep_offsets(self):
        plan = fetch.build_plan("windows", 11_269_408, 400, page_size=100, window_size=100,
                                n_windows=4, seed=0, window_span=200_000)
        self.assertEqual(len(plan), 4)
        self.assertTrue(all(offset < 200_000 for offset, _ in plan), plan)
        unbounded = fetch.build_plan("windows", 11_269_408, 400, page_size=100, window_size=100,
                                     n_windows=4, seed=0)
        self.assertGreater(unbounded[-1][0], 10_000_000)

    def test_stride_plan_single_rows(self):
        plan = fetch.build_plan("stride", 1_000, 10, page_size=100)
        self.assertEqual(len(plan), 10)
        self.assertTrue(all(length == 1 for _, length in plan))

    def test_unknown_strategy_and_bad_inputs(self):
        with self.assertRaises(fetch.FetchError):
            fetch.build_plan("nope", 10, 1)
        with self.assertRaises(fetch.FetchError):
            fetch.build_plan("head", 0, 1)
        with self.assertRaises(fetch.FetchError):
            fetch.build_plan("head", 10, 0)


class ClientTests(unittest.TestCase):
    def test_retries_with_exponential_backoff_then_succeeds(self):
        server = FakeServer(failures=[429, 503])
        sleeps = []
        client = fetch.Client(server, retries=5, base_delay=1.0, max_delay=10.0,
                              sleeper=sleeps.append, log=quiet)
        payload = client.endpoint("rows", dataset=DATASET, config=CONFIG, split="train",
                                  offset=0, length=1)
        self.assertEqual(payload["num_rows_total"], 250)
        self.assertEqual(sleeps, [1.0, 2.0])
        self.assertEqual(client.retries_used, 2)

    def test_backoff_is_capped(self):
        server = FakeServer(failures=[500] * 7)      # 第 8 次尝试成功
        sleeps = []
        client = fetch.Client(server, retries=8, base_delay=1.0, max_delay=4.0,
                              sleeper=sleeps.append, log=quiet)
        client.endpoint("splits", dataset=DATASET)
        self.assertEqual(sleeps, [1.0, 2.0, 4.0, 4.0, 4.0, 4.0, 4.0])

    def test_giving_up_after_retries(self):
        server = FakeServer(failures=[500] * 4)
        client = fetch.Client(server, retries=3, base_delay=1.0,
                              sleeper=lambda _s: None, log=quiet)
        with self.assertRaises(fetch.FetchError) as caught:
            client.endpoint("splits", dataset=DATASET)
        self.assertIn("重试 3 次仍失败", str(caught.exception))

    def test_non_retryable_error_fails_immediately(self):
        server = FakeServer(failures=[404])
        client = fetch.Client(server, retries=4, sleeper=lambda _s: None, log=quiet)
        with self.assertRaises(fetch.FetchError) as caught:
            client.endpoint("rows", dataset=DATASET, config=CONFIG, split="train",
                            offset=0, length=1)
        self.assertIn("404", str(caught.exception))
        self.assertEqual(len(server.calls), 1)

    def test_config_with_plus_is_percent_encoded(self):
        server = FakeServer()
        client = fetch.Client(server, sleeper=lambda _s: None, log=quiet)
        client.endpoint("rows", dataset=DATASET, config=CONFIG, split="train", offset=0, length=1)
        self.assertIn("config=default%2Bcontrol", server.calls[-1])
        self.assertEqual(server.row_requests[-1][2], CONFIG)

    def test_network_exception_is_retried(self):
        calls = {"n": 0}

        def flaky(url):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("connection reset")
            return 200, b'{"ok": true}'

        client = fetch.Client(flaky, retries=3, sleeper=lambda _s: None, log=quiet)
        self.assertEqual(client.json("https://example.invalid/x"), {"ok": True})


class FetchSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw_root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, server):
        return fetch.Client(server, sleeper=lambda _s: None, log=quiet)

    def fetch(self, source=None, server=None, **kwargs):
        server = server or FakeServer()
        manifest = fetch.fetch_source(self.client(server), source or make_source(),
                                      self.raw_root, log=quiet, **kwargs)
        return manifest, server

    def partial(self, source=None):
        """跑一次会在第 2 页被中断的抓取，留下 cursor=1 的半成品。"""
        source = source or make_source()
        server = FakeServer(fail_rows_offset=100)
        with self.assertRaises(fetch.FetchError):
            fetch.fetch_source(self.client(server), source, self.raw_root, log=quiet)
        manifest = json.loads((self.raw_root / "example" / "manifest.json").read_text("utf-8"))
        self.assertFalse(manifest["complete"])
        self.assertEqual((manifest["cursor"], manifest["rows"]), (1, 100))
        return source, manifest

    def test_manifest_fields_and_artifact_hash(self):
        manifest, _ = self.fetch()
        self.assertEqual(manifest["dataset"], DATASET)
        self.assertEqual(manifest["revision"], REVISION)
        self.assertEqual(manifest["config"], CONFIG)
        self.assertEqual(manifest["split"], "train")
        self.assertEqual(manifest["rows"], 250)
        self.assertTrue(manifest["complete"])
        self.assertTrue(manifest["revision_stable"])
        self.assertFalse(manifest["revision_enforced"])
        rows_path = self.raw_root / "example" / "rows.jsonl"
        self.assertEqual(manifest["bytes"], rows_path.stat().st_size)
        self.assertEqual(manifest["sha256"], hashlib.sha256(rows_path.read_bytes()).hexdigest())
        lines = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([line["row_idx"] for line in lines], list(range(250)))
        self.assertEqual(lines[7]["row"]["state"], "state 7")

    def test_limit_pages_and_first_rows_snapshot(self):
        manifest, server = self.fetch(source=make_source(row_limit=150))
        self.assertEqual(manifest["rows"], 150)
        pages = [request[:2] for request in server.row_requests if request[1] > 1]
        self.assertEqual(pages, [(0, 100), (100, 50)])
        snapshot = json.loads((self.raw_root / "example" / "first-rows.json").read_text("utf-8"))
        self.assertEqual([feature["name"] for feature in snapshot["features"]],
                         ["state", "kind"])

    def test_unpinned_revision_is_skipped(self):
        for bad in ("", "abc", "z" * 40):
            with self.assertRaises(fetch.SourceSkipped):
                self.fetch(source=make_source(revision=bad))

    def test_revision_drift_stops_the_fetch(self):
        server = FakeServer(sha="b" * 40)
        with self.assertRaises(fetch.FetchError) as caught:
            self.fetch(server=server)
        self.assertIn("不一致", str(caught.exception))
        self.assertEqual(server.row_requests, [])

    def test_revision_moving_during_fetch_is_reported(self):
        server = FakeServer()

        def moving(url):
            if url.startswith("https://huggingface.co/api/") and server.row_requests:
                server.sha = "c" * 40
            return server(url)

        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch_source(fetch.Client(moving, sleeper=lambda _s: None, log=quiet),
                               make_source(), self.raw_root, log=quiet)
        self.assertIn("sha", str(caught.exception))
        manifest = json.loads((self.raw_root / "example" / "manifest.json").read_text("utf-8"))
        self.assertFalse(manifest["revision_stable"])

    def test_missing_config_split_is_skipped(self):
        with self.assertRaises(fetch.SourceSkipped):
            self.fetch(source=make_source(config="nope"))

    def test_partial_fetch_refuses_plain_rerun_then_resumes(self):
        source, _ = self.partial()
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch_source(self.client(FakeServer()), source, self.raw_root, log=quiet)
        self.assertIn("--resume", str(caught.exception))
        resumed = fetch.fetch_source(self.client(FakeServer()), source, self.raw_root,
                                     resume=True, log=quiet)
        self.assertEqual(resumed["rows"], 250)
        self.assertTrue(resumed["complete"])

    def test_resume_is_idempotent_once_complete(self):
        source, _ = self.partial()
        fetch.fetch_source(self.client(FakeServer()), source, self.raw_root, resume=True, log=quiet)
        again = fetch.fetch_source(self.client(FakeServer()), source, self.raw_root, log=quiet)
        self.assertTrue(again["complete"])
        self.assertEqual(again["rows"], 250)

    def test_tampered_rows_file_refuses_resume(self):
        source, _ = self.partial()
        rows_path = self.raw_root / "example" / "rows.jsonl"
        rows_path.write_text(rows_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch_source(self.client(FakeServer()), source, self.raw_root, resume=True, log=quiet)
        self.assertIn("manifest 不一致", str(caught.exception))

    def test_rows_without_manifest_is_refused(self):
        directory = self.raw_root / "example"
        directory.mkdir()
        (directory / "rows.jsonl").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(fetch.FetchError) as caught:
            self.fetch()
        self.assertIn("没有 manifest", str(caught.exception))

    def test_changed_total_rows_changes_plan_and_refuses_resume(self):
        source, _ = self.partial()
        grown = FakeServer(total=400)
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch_source(self.client(grown), source, self.raw_root, resume=True, log=quiet)
        self.assertIn("num_rows_total", str(caught.exception))

    def test_resume_with_other_revision_refuses(self):
        source, _ = self.partial()
        other = dict(source, revision="d" * 40)
        server = FakeServer(sha="d" * 40)
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch_source(self.client(server), other, self.raw_root, resume=True, log=quiet)
        self.assertIn("另一个 revision", str(caught.exception))

    def test_empty_page_is_an_error(self):
        class Empty(FakeServer):
            def __call__(self, url):
                parsed = urllib.parse.urlparse(url)
                if parsed.path.strip("/") == "rows" and "length=100" in url:
                    return 200, json.dumps({"features": FEATURES, "rows": [],
                                            "num_rows_total": 250}).encode()
                return super().__call__(url)

        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch_source(self.client(Empty()), make_source(), self.raw_root, log=quiet)
        self.assertIn("空页", str(caught.exception))


class SourcesFileTests(unittest.TestCase):
    def test_shipped_sources_file_is_valid_and_pinned(self):
        payload = fetch.load_sources(HERE / "sources.json")
        slugs = [source["slug"] for source in payload["sources"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        for source in payload["sources"]:
            self.assertRegex(source["revision"], r"^[0-9a-f]{40}$", source["slug"])
            self.assertTrue(source["license"], source["slug"])
            self.assertTrue(source["converter"], source["slug"])
        self.assertIn("quotas", payload)

    def test_jev_bench_is_excluded_and_not_fetchable(self):
        payload = fetch.load_sources(HERE / "sources.json")
        excluded = {item["dataset"] for item in payload["excluded"]}
        self.assertIn("Praveenrajus/jev-bench", excluded)
        self.assertNotIn("Praveenrajus/jev-bench",
                         {source["dataset"] for source in payload["sources"]})

    def test_select_sources_rejects_unknown_slug(self):
        payload = fetch.load_sources(HERE / "sources.json")
        with self.assertRaises(fetch.FetchError):
            fetch.select_sources(payload, ["not-a-slug"])


if __name__ == "__main__":
    unittest.main()
