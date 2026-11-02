"""export_score_v2_hf.py 的单元测试（合成 fixture，不读真实 Release 数据、不联网）。"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datasets.pol2 import export_score_v2_hf as export

BT = chr(96)

# 最小假 Release：必须项 + 隐藏文件 + 两个数据文件（行数 2 / 1，用于验证非空行统计）
RELEASE_FILES = {
    "README.md": b"# fake release\n",
    "DATASET_CARD.md": b"# dataset card\n",
    "SCHEMA.md": b"# schema\n",
    "HOLDOUT.md": b"# holdout\n",
    "LICENSE": b"Proof of Love2\n",
    "LICENSES/x.txt": b"license text\n",
    "THIRD_PARTY_NOTICES.md": b"# notices\n",
    "manifests/a.json": b'{"ok": true}\n',
    "scripts/validate_public_release.py": b"print('validate')\n",
    ".gitattributes": b"* text=auto\n",
    "data/pol2-specialist/kev/train-m0.jsonl": b'{"case_id": "c1"}\n\n{"case_id": "c2"}\n',
    "data/general-replay/laya/train-m10.jsonl": b'{"case_id": "g1"}\n',
}

SAMPLES_FILES = {
    "index.json": b'{"purpose": "fake samples"}\n',
    "specialist-laya.jsonl": b'{"case_id": "s1"}\n{"case_id": "s2"}\n',
    "specialist-kev.jsonl": b'{"case_id": "s1"}\n{"case_id": "s2"}\n',
}

# 边界审计合成 fixture：4 个未分配单元，其中第 1、3 行属于 fresh-blind 族。
BOUNDARY_POOL_ROWS = [
    {"unit_id": "u0", "family_id": "fam-blind", "label": 0, "payload": "p0"},
    {"unit_id": "u1", "family_id": "fam-train", "label": 2, "payload": "p1"},
    {"unit_id": "u2", "family_id": "fam-blind", "label": 1, "payload": "p2"},
    {"unit_id": "u3", "family_id": "fam-train", "label": 3, "payload": "p3"},
]


def jsonl_bytes(rows, reverse_keys=False):
    lines = []
    for row in rows:
        if reverse_keys:
            row = {key: row[key] for key in reversed(list(row))}
        lines.append(json.dumps(row, ensure_ascii=False) + "\n")
    return "".join(lines).encode("utf-8")


def integrated_bytes(blind=True):
    payload = {
        "fresh_blind_families": ["fam-blind"] if blind else [],
        "new_label_counts": {"fresh_blind": {"0": 1, "1": 1} if blind else {}},
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def new_units_bytes(blind=True):
    index = []
    for position, row in enumerate(BOUNDARY_POOL_ROWS, 1):
        index.append({
            "line": position,
            "family_id": row["family_id"] if blind else "fam-train",
            "case_id": "case-" + str(position),
            "label": row["label"],
        })
    payload = {"index": index, "count": len(index), "split": "UNASSIGNED"}
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def boundary_samples_files():
    # 样例行取自池前 3 行（第 0、2 行为 blind），但键序/空白不同，用来验证规范化哈希。
    sample = jsonl_bytes(BOUNDARY_POOL_ROWS[:3], reverse_keys=True)
    return {
        "index.json": b'{"purpose": "fake boundary samples"}\n',
        "specialist-kev.jsonl": sample,
        "specialist-laya.jsonl": sample,
        "general-replay-kev.jsonl": b'{"case_id": "g1"}\n',
        "general-replay-laya.jsonl": b'{"case_id": "g2"}\n',
    }


def write_tree(root, files):
    root = Path(root)
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def write_text_lf(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_release_checksums(root):
    """按当前 release 目录内容重写带 ./ 前缀的 CHECKSUMS.sha256（自身除外）。"""
    root = Path(root)
    relative_paths = sorted(path.relative_to(root).as_posix()
                            for path in root.rglob("*")
                            if path.is_file() and path.name != "CHECKSUMS.sha256")
    lines = []
    for relative in relative_paths:
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        lines.append(digest + "  ./" + relative)
    write_text_lf(root / "CHECKSUMS.sha256", "\n".join(lines) + "\n")


class ExportScoreV2HfTest(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._temp.name)
        self.release = self.tmp / "release-source"
        write_tree(self.release, RELEASE_FILES)
        write_release_checksums(self.release)
        self.samples = self.tmp / "samples-source"
        write_tree(self.samples, SAMPLES_FILES)
        self.full_release = self.tmp / "full-release.json"
        self.full_release.write_bytes(b'{"schema": "fake-full-release"}\n')
        self.out = self.tmp / "out"

    def tearDown(self):
        self._temp.cleanup()

    # ------------------------------------------------------------- 工具

    def run_main(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = export.main([str(item) for item in argv])
        return code, stdout.getvalue(), stderr.getvalue()

    def build(self, out=None, samples_dir="default", org="NaturalDAO", release_dir=None,
              flags=()):
        out = self.out if out is None else out
        samples = self.samples if samples_dir == "default" else samples_dir
        argv = ["build", "--release-dir", release_dir or self.release, "--out", out]
        if samples is not None:
            argv += ["--samples-dir", samples]
        argv += ["--org", org]
        argv += list(flags)
        with mock.patch.object(export, "FULL_RELEASE_MANIFEST", self.full_release):
            return self.run_main(argv)

    def make_boundary_release(self, blind=True):
        write_tree(self.release, {
            "manifests/score-v2-integrated.json": integrated_bytes(blind),
            "manifests/score-v2-new-units.json": new_units_bytes(blind),
            "data/pol2-specialist/score-v2-new-units/kev.jsonl":
                jsonl_bytes(BOUNDARY_POOL_ROWS),
            "data/pol2-specialist/score-v2-new-units/laya.jsonl":
                jsonl_bytes(BOUNDARY_POOL_ROWS),
        })
        write_release_checksums(self.release)
        write_tree(self.samples, boundary_samples_files())

    def manifest(self, out=None):
        path = (out or self.out) / "MANIFEST.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def card(self, out=None):
        return ((out or self.out) / "README.md").read_text(encoding="utf-8")

    def checksums(self, out=None):
        text = ((out or self.out) / "CHECKSUMS.sha256").read_text(encoding="utf-8")
        return export.parse_checksums(text)

    def files_by_path(self, out=None):
        return {entry["path"]: entry for entry in self.manifest(out)["files"]}

    def disk_files(self, root):
        root = Path(root)
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    # ------------------------------------------------------------- build

    def test_build_layout_and_verbatim_copy(self):
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        self.assertTrue((self.out / "README.md").is_file())
        self.assertTrue((self.out / "MANIFEST.json").is_file())
        self.assertTrue((self.out / "CHECKSUMS.sha256").is_file())
        for relative, data in RELEASE_FILES.items():
            self.assertEqual((self.out / "release" / relative).read_bytes(), data, relative)
        self.assertTrue((self.out / "release" / ".gitattributes").is_file())
        self.assertEqual((self.out / "release" / "CHECKSUMS.sha256").read_bytes(),
                         (self.release / "CHECKSUMS.sha256").read_bytes())
        for relative, data in SAMPLES_FILES.items():
            self.assertEqual((self.out / "samples" / relative).read_bytes(), data, relative)
        self.assertEqual((self.out / "cross-check" / "full-release.json").read_bytes(),
                         self.full_release.read_bytes())
        listed = set(self.files_by_path())
        on_disk = set(self.disk_files(self.out)) - {"MANIFEST.json", "CHECKSUMS.sha256"}
        self.assertEqual(listed, on_disk)

    def test_manifest_files_sorted_with_stats(self):
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        manifest = self.manifest()
        paths = [entry["path"] for entry in manifest["files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertNotIn("MANIFEST.json", paths)
        self.assertNotIn("CHECKSUMS.sha256", paths)

        files = self.files_by_path()
        self.assertEqual(files["release/data/pol2-specialist/kev/train-m0.jsonl"]["rows"], 2)
        self.assertEqual(files["release/data/general-replay/laya/train-m10.jsonl"]["rows"], 1)
        self.assertEqual(files["samples/specialist-laya.jsonl"]["rows"], 2)
        self.assertIsNone(files["samples/index.json"]["rows"])
        self.assertIsNone(files["release/manifests/a.json"]["rows"])
        self.assertEqual(files["README.md"]["kind"], "card")
        self.assertEqual(files["release/LICENSE"]["kind"], "release")
        self.assertEqual(files["samples/index.json"]["kind"], "samples")
        self.assertEqual(files["cross-check/full-release.json"]["kind"], "cross-check")

        for entry in manifest["files"]:
            path = self.out / entry["path"]
            self.assertEqual(entry["bytes"], path.stat().st_size, entry["path"])
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest(),
                             entry["path"])

        self.assertEqual(manifest["schema"], export.EXPORT_SCHEMA)
        self.assertEqual(manifest["release"]["tag"], export.RELEASE_TAG)
        self.assertEqual(manifest["release"]["asset_name"], export.RELEASE_ASSET_NAME)
        self.assertEqual(manifest["release"]["asset_sha256"], export.RELEASE_ASSET_SHA256)
        self.assertEqual(manifest["release"]["asset_bytes"], export.RELEASE_ASSET_BYTES)
        self.assertEqual(manifest["hf"]["repo"], "NaturalDAO/pol2-score-v2")
        self.assertEqual(manifest["hf"]["url"],
                         "https://huggingface.co/datasets/NaturalDAO/pol2-score-v2")
        self.assertEqual(manifest["hf"]["repo_type"], "dataset")
        self.assertEqual(manifest["license"]["project"], "Proof of Love2")
        self.assertEqual(manifest["summary"]["files"], len(manifest["files"]))
        self.assertEqual(manifest["summary"]["bytes"],
                         sum(entry["bytes"] for entry in manifest["files"]))
        self.assertEqual(manifest["summary"]["rows_by_group"],
                         {"general-replay": 1, "pol2-specialist": 2})
        groups = manifest["data_groups"]
        self.assertEqual(groups["pol2-specialist"]["files"], 1)
        self.assertEqual(groups["pol2-specialist"]["by_format"]["kev"]["rows"], 2)
        self.assertEqual(groups["general-replay"]["by_format"]["laya"]["rows"], 1)
        self.assertFalse(manifest["excluded_holdout"]["included"])
        self.assertNotIn("generated_at", json.dumps(manifest, ensure_ascii=False))

    def test_card_front_matter_and_sections(self):
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        text = self.card()
        lines = text.splitlines()
        self.assertEqual(lines[0], "---")
        end = lines.index("---", 1)
        front = "\n".join(lines[1:end])
        self.assertIn("license: other", front)
        self.assertIn("license_name: proof-of-love2-and-mit", front)
        self.assertIn("license_link: " + export.release_url(), front)
        self.assertIn("language: [zh]", front)
        self.assertIn('pretty_name: "POL2 Score-v2 决策数据（研究预发布）"', front)
        self.assertIn("size_categories: [10K<n<100K]", front)
        self.assertIn("tags: [decision-making, typed-decisions, jev, pol2, synthetic, "
                      "research-preview, proof-of-love2]", front)
        # 计数来自计算值（fixture：release/data 2 个文件 3 行；release 树 13 个文件）
        self.assertIn(BT + "release/data/" + BT + " 共 **2** 个文件 / **3** 行", text)
        self.assertIn(BT + "release/" + BT + " 整包 **13** 个文件", text)
        self.assertIn("去重警告", text)
        self.assertIn("268", text)
        self.assertIn("687", text)
        self.assertIn("264", text)
        self.assertIn('load_dataset("json", data_files="release/data/pol2-specialist/'
                      'kev/train-m0.jsonl")', text)
        self.assertIn("streaming=True", text)
        self.assertIn("cd release", text)
        self.assertIn("python3 scripts/validate_public_release.py", text)
        self.assertIn("sha256sum -c CHECKSUMS.sha256", text)
        self.assertIn("https://huggingface.co/datasets/NaturalDAO/pol2-score-v2", text)
        self.assertNotIn(str(self.tmp), text)

    def test_checksums_cover_all_files_and_are_sorted(self):
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        entries = self.checksums()
        paths = [path for path, _digest in entries]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(set(paths), {entry["path"] for entry in self.manifest()["files"]})
        self.assertNotIn("MANIFEST.json", paths)
        self.assertNotIn("CHECKSUMS.sha256", paths)
        for path, digest in entries:
            self.assertFalse(path.startswith("./"))
            self.assertEqual(digest, hashlib.sha256((self.out / path).read_bytes()).hexdigest())
        raw = (self.out / "CHECKSUMS.sha256").read_text(encoding="utf-8")
        self.assertTrue(raw.endswith("\n"))

    def test_build_is_deterministic(self):
        first, second = self.tmp / "out-a", self.tmp / "out-b"
        self.assertEqual(self.build(out=first)[0], 0)
        digest = export.tree_digest(first)
        self.assertEqual(self.build(out=first)[0], 0)
        self.assertEqual(export.tree_digest(first), digest)
        self.assertEqual(self.build(out=second)[0], 0)
        self.assertEqual(export.tree_digest(second), digest)
        self.assertEqual(self.disk_files(first), self.disk_files(second))

    def test_org_only_changes_manifest_card_and_checksums(self):
        first, second = self.tmp / "org-a", self.tmp / "org-b"
        self.assertEqual(self.build(out=first, org="OrgA")[0], 0)
        self.assertEqual(self.build(out=second, org="OrgB")[0], 0)
        left, right = self.disk_files(first), self.disk_files(second)
        self.assertEqual(set(left), set(right))
        different = {path for path in left if left[path] != right[path]}
        self.assertEqual(different, {"README.md", "MANIFEST.json", "CHECKSUMS.sha256"})
        self.assertIn(b"https://huggingface.co/datasets/OrgA/pol2-score-v2", left["README.md"])
        self.assertEqual(json.loads(right["MANIFEST.json"])["hf"]["org"], "OrgB")

    def test_build_json_summary(self):
        with mock.patch.object(export, "FULL_RELEASE_MANIFEST", self.full_release):
            code, stdout, stderr = self.run_main(
                ["build", "--release-dir", self.release, "--out", self.out,
                 "--samples-dir", self.samples, "--org", "NaturalDAO", "--json"])
        payload = json.loads(stdout)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(payload["command"], "build")
        self.assertEqual(payload["files"], len(self.manifest()["files"]))
        self.assertEqual(payload["rows_by_group"],
                         {"general-replay": 1, "pol2-specialist": 2})
        self.assertEqual(payload["tree_sha256"], export.tree_digest(self.out))

    def test_build_without_samples_still_succeeds(self):
        code, _stdout, stderr = self.build(samples_dir=self.tmp / "missing-samples")
        self.assertEqual(code, 0, stderr)
        self.assertFalse((self.out / "samples").exists())
        kinds = {entry["kind"] for entry in self.manifest()["files"]}
        self.assertEqual(kinds, {"release", "cross-check", "card"})
        self.assertIn("本导出未包含 " + BT + "samples/" + BT, self.card())

    def test_build_fails_on_release_checksum_mismatch(self):
        target = self.release / "data" / "general-replay" / "laya" / "train-m10.jsonl"
        target.write_bytes(target.read_bytes() + b" ")
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("sha256 不一致", stderr)
        self.assertFalse(self.out.exists())

    def test_build_fails_on_blind_filename(self):
        blind = (self.release / "data" / "pol2-specialist" / "kev"
                 / "score-Sealed-extra.jsonl")
        blind.write_bytes(b'{"case_id": "blind"}\n')
        write_release_checksums(self.release)
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("盲测", stderr)
        self.assertFalse(self.out.exists())

    def test_scan_blind_names_is_case_insensitive(self):
        for keyword in export.BLIND_NAME_KEYWORDS:
            path = (self.release / "data" / "pol2-specialist" / "kev"
                    / ("x-" + keyword.upper() + ".jsonl"))
            path.write_bytes(b"{}\n")
        hits = export.scan_blind_names(self.release)
        self.assertEqual(len(hits), len(export.BLIND_NAME_KEYWORDS))

    def test_build_requires_release_entries(self):
        (self.release / "HOLDOUT.md").unlink()
        write_release_checksums(self.release)
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("缺少必需项", stderr)

    # ------------------------------------------------------------- 上游边界

    def test_audit_release_boundaries_and_samples(self):
        self.make_boundary_release()
        audit = export.audit_release_boundaries(self.release)
        self.assertTrue(audit["applicable"])
        self.assertEqual(audit["unassigned_entries"], 4)
        self.assertEqual(audit["blind_entries"], 2)
        self.assertEqual(audit["blind_cases"], 2)
        self.assertEqual(audit["blind_family_count"], 1)
        self.assertEqual(audit["blind_label_counts"], {"0": 1, "1": 1})
        self.assertEqual(audit["blind_label_total"], 2)
        self.assertTrue(audit["label_counts_match"])
        self.assertNotIn("blind_lines", audit)

        samples = export.audit_samples(self.samples, self.release)
        self.assertTrue(samples["applicable"])
        by_path = {record["path"]: record for record in samples["files"]}
        for name in ("specialist-kev.jsonl", "specialist-laya.jsonl"):
            record = by_path["samples/" + name]
            self.assertEqual(record["rows"], 3)
            self.assertEqual(record["mapped_rows"], 3)
            self.assertEqual(record["unmapped_rows"], 0)
            self.assertEqual(record["blind_rows"], 2)
            self.assertEqual(record["blind_positions"], [0, 2])
        self.assertEqual(samples["blind_rows"], 4)
        self.assertEqual(samples["blind_files"], ["samples/specialist-kev.jsonl",
                                                  "samples/specialist-laya.jsonl"])
        self.assertEqual(samples["general_replay"], [])
        self.assertNotIn("payload", json.dumps(samples, ensure_ascii=False))

    def test_audit_not_applicable_on_plain_release(self):
        audit = export.audit_release_boundaries(self.release)
        self.assertFalse(audit["applicable"])
        self.assertEqual(set(audit["missing"]),
                         {"manifests/score-v2-integrated.json",
                          "manifests/score-v2-new-units.json"})
        samples = export.audit_samples(self.samples, self.release)
        self.assertFalse(samples["applicable"])
        self.assertEqual(samples["files"], [])
        self.assertEqual(samples["general_replay"], [])
        self.assertEqual(samples["blind_rows"], 0)
        self.assertEqual(self.build()[0], 0)

    def test_build_rejects_blind_without_exclusions(self):
        self.make_boundary_release()
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 2)
        self.assertIn("--exclude-unassigned-pool", stderr)
        self.assertIn("fresh-blind", stderr)
        self.assertFalse(self.out.exists())

    def test_build_public_test_signature_allows_full_mirror(self):
        self.make_boundary_release()
        signature = {"unassigned_entries": 4, "blind_entries": 2,
                     "blind_cases": 2, "blind_family_count": 1}
        with mock.patch.object(export, "PUBLIC_TEST_SIGNATURE", signature):
            code, _stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        files = self.files_by_path()
        self.assertIn("release/data/pol2-specialist/score-v2-new-units/kev.jsonl", files)
        self.assertIn("release/data/pol2-specialist/score-v2-new-units/laya.jsonl", files)
        self.assertIn("release/manifests/score-v2-new-units.json", files)
        self.assertIn("samples/specialist-kev.jsonl", files)
        manifest = self.manifest()
        self.assertTrue(manifest["boundary_audit"]["public_test"])
        self.assertEqual(manifest["boundary_audit"]["interpretation"]["interpretation"],
                         "public_test_split")
        self.assertEqual(manifest["boundary_audit"]["counts"]["blind_entries"], 2)
        self.assertEqual(manifest["excluded_upstream_files"], [])
        self.assertEqual(manifest["excluded_samples"], [])
        card = self.card()
        self.assertIn("数据划分", card)
        self.assertIn("test（公开）", card)
        self.assertNotIn("安全子集", card)
        self.assertNotIn("§10", card)

    def test_build_safe_subset_excludes_pool_manifest_and_samples(self):
        self.make_boundary_release()
        flags = ("--exclude-unassigned-pool", "--exclude-blind-samples")
        code, _stdout, stderr = self.build(flags=flags)
        self.assertEqual(code, 0, stderr)
        files = self.files_by_path()
        pool_paths = [
            "release/data/pol2-specialist/score-v2-new-units/kev.jsonl",
            "release/data/pol2-specialist/score-v2-new-units/laya.jsonl",
        ]
        for path in pool_paths + ["release/manifests/score-v2-new-units.json"]:
            self.assertNotIn(path, files)
            self.assertFalse((self.out / path).exists(), path)
        self.assertIn("release/data/pol2-specialist/kev/train-m0.jsonl", files)
        self.assertIn("release/manifests/score-v2-integrated.json", files)
        for name in ("samples/general-replay-kev.jsonl", "samples/general-replay-laya.jsonl",
                     "samples/index.json"):
            self.assertIn(name, files)
        for name in ("samples/specialist-kev.jsonl", "samples/specialist-laya.jsonl"):
            self.assertNotIn(name, files)
            self.assertFalse((self.out / name).exists(), name)

        manifest = self.manifest()
        expected_upstream = sorted(pool_paths + ["release/manifests/score-v2-new-units.json"])
        self.assertEqual([item["path"] for item in manifest["excluded_upstream_files"]],
                         expected_upstream)
        self.assertTrue(all(item["blind_entries"] == 2
                            for item in manifest["excluded_upstream_files"]))
        self.assertEqual(manifest["excluded_samples"], [
            {"path": "samples/specialist-kev.jsonl", "blind_rows": 2},
            {"path": "samples/specialist-laya.jsonl", "blind_rows": 2},
        ])
        audit = manifest["boundary_audit"]
        self.assertTrue(audit["applicable"])
        self.assertTrue(audit["safe_subset"])
        self.assertEqual(audit["counts"]["unassigned_entries"], 4)
        self.assertEqual(audit["counts"]["blind_entries"], 2)
        self.assertEqual(audit["counts"]["blind_cases"], 2)
        self.assertEqual(audit["counts"]["blind_label_counts"], {"0": 1, "1": 1})
        self.assertEqual(audit["excluded_upstream_files"], expected_upstream)
        self.assertEqual(audit["samples"]["blind_rows"], 4)
        for path in expected_upstream:
            self.assertIn(path, audit["excluded"])
        self.assertNotIn(pool_paths[0], audit["included"])
        self.assertNotIn("payload", json.dumps(manifest, ensure_ascii=False))

        card = self.card()
        self.assertIn("## 10. 上游 Release 边界与本次导出范围", card)
        self.assertIn("安全子集", card)
        self.assertIn("assigned splits", card)
        self.assertIn("待维护者修正", card)
        self.assertIn("| unassigned 新增单元 | 4 |", card)
        self.assertIn("| 命中 fresh-blind 族的单元 | 2 |", card)
        self.assertIn("| 覆盖案例 | 2 |", card)
        self.assertIn("## 11. 校验", card)
        self.assertIn("## 12. 引用与相关链接", card)
        self.assertNotIn(str(self.tmp), card)

        code, stdout, _stderr = self.run_main(["verify", "--dir", self.out, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "pass")

    def test_build_without_blind_keeps_full_mirror(self):
        self.make_boundary_release(blind=False)
        code, _stdout, stderr = self.build()
        self.assertEqual(code, 0, stderr)
        files = self.files_by_path()
        for path in ("release/data/pol2-specialist/score-v2-new-units/kev.jsonl",
                     "release/data/pol2-specialist/score-v2-new-units/laya.jsonl",
                     "release/manifests/score-v2-new-units.json"):
            self.assertIn(path, files)
        manifest = self.manifest()
        self.assertNotIn("boundary_audit", manifest)
        self.assertNotIn("excluded_upstream_files", manifest)
        self.assertNotIn("excluded_samples", manifest)
        card = self.card()
        self.assertIn("## 10. 上游 Release 边界与本次导出范围", card)
        self.assertIn("未检测到边界问题", card)
        self.assertIn("unassigned 池为 4 条", card)
        self.assertIn("命中 fresh-blind 族 0 条", card)
        self.assertNotIn("安全子集", card)
        code, stdout, _stderr = self.run_main(["verify", "--dir", self.out, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "pass")

    def test_boundary_build_is_deterministic_and_verifies(self):
        self.make_boundary_release()
        flags = ("--exclude-unassigned-pool", "--exclude-blind-samples")
        first, second = self.tmp / "safe-a", self.tmp / "safe-b"
        self.assertEqual(self.build(out=first, flags=flags)[0], 0)
        digest = export.tree_digest(first)
        self.assertEqual(self.build(out=first, flags=flags)[0], 0)
        self.assertEqual(export.tree_digest(first), digest)
        self.assertEqual(self.build(out=second, flags=flags)[0], 0)
        self.assertEqual(export.tree_digest(second), digest)
        self.assertEqual(self.disk_files(first), self.disk_files(second))
        code, stdout, _stderr = self.run_main(["verify", "--dir", second, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "pass")

    def test_boundary_build_json_summary_and_stats(self):
        self.make_boundary_release()
        with mock.patch.object(export, "FULL_RELEASE_MANIFEST", self.full_release):
            code, stdout, stderr = self.run_main(
                ["build", "--release-dir", self.release, "--out", self.out,
                 "--samples-dir", self.samples, "--org", "NaturalDAO",
                 "--exclude-unassigned-pool", "--exclude-blind-samples", "--json"])
        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertTrue(payload["safe_subset"])
        self.assertEqual(len(payload["excluded_upstream_files"]), 3)
        self.assertEqual(len(payload["excluded_samples"]), 2)
        self.assertEqual(payload["boundary_audit"]["blind_entries"], 2)
        self.assertEqual(payload["sample_audit"]["blind_rows"], 4)
        code, stdout, _stderr = self.run_main(["stats", "--dir", self.out])
        self.assertEqual(code, 0)
        stats = json.loads(stdout)
        self.assertEqual(stats["boundary_audit"]["counts"]["blind_entries"], 2)

    # ------------------------------------------------------------- verify

    def test_verify_passes(self):
        self.assertEqual(self.build()[0], 0)
        code, stdout, _stderr = self.run_main(["verify", "--dir", self.out, "--json"])
        report = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["files"], len(self.manifest()["files"]))

    def test_verify_detects_tampering(self):
        self.assertEqual(self.build()[0], 0)
        target = (self.out / "release" / "data" / "pol2-specialist" / "kev"
                  / "train-m0.jsonl")
        target.write_bytes(target.read_bytes() + b'{"case_id": "c3"}\n')
        code, stdout, _stderr = self.run_main(["verify", "--dir", self.out, "--json"])
        report = json.loads(stdout)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("sha256 不一致" in item for item in report["problems"]))
        self.assertTrue(any("字节数不一致" in item for item in report["problems"]))

    def test_verify_detects_extra_file(self):
        self.assertEqual(self.build()[0], 0)
        (self.out / "notes.txt").write_bytes(b"extra\n")
        code, stdout, _stderr = self.run_main(["verify", "--dir", self.out, "--json"])
        report = json.loads(stdout)
        self.assertEqual(code, 2)
        self.assertTrue(any("多余文件：notes.txt" in item for item in report["problems"]))

    def test_verify_detects_checksums_mismatch(self):
        self.assertEqual(self.build()[0], 0)
        path = self.out / "CHECKSUMS.sha256"
        lines = path.read_text(encoding="utf-8").splitlines()
        lines = [("0" * 64 + line[64:]) if line.endswith("  README.md") else line
                 for line in lines]
        write_text_lf(path, "\n".join(lines) + "\n")
        code, stdout, _stderr = self.run_main(["verify", "--dir", self.out, "--json"])
        report = json.loads(stdout)
        self.assertEqual(code, 2)
        self.assertTrue(any("CHECKSUMS.sha256 与 MANIFEST" in item
                            for item in report["problems"]))

    def test_verify_rejects_missing_manifest(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        code, _stdout, stderr = self.run_main(["verify", "--dir", empty])
        self.assertEqual(code, 2)
        self.assertIn("MANIFEST.json", stderr)

    # ------------------------------------------------------------- stats / 解析

    def test_stats_prints_manifest_summary(self):
        self.assertEqual(self.build()[0], 0)
        code, stdout, _stderr = self.run_main(["stats", "--dir", self.out])
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(payload["hf"]["repo"], "NaturalDAO/pol2-score-v2")
        self.assertEqual(payload["summary"]["rows_by_group"],
                         {"general-replay": 1, "pol2-specialist": 2})

    def test_classify_data_path_groups(self):
        cases = {
            "release/data/pol2-specialist/kev/train-m0.jsonl": ("pol2-specialist", "kev"),
            "release/data/pol2-specialist/laya/train-m0.jsonl": ("pol2-specialist", "laya"),
            "release/data/pol2-specialist/lineage/score-dev.jsonl": ("lineage", "none"),
            "release/data/pol2-specialist/score-v2-new-units/laya.jsonl":
                ("pol2-specialist", "laya"),
            "release/data/general-replay/laya/train-m10.jsonl": ("general-replay", "laya"),
            "release/data/mixed-training/kev-m10.jsonl": ("mixed-training", "kev"),
            "release/data/pol2-specialist/README.md": ("pol2-specialist", "none"),
        }
        for relative, expected in cases.items():
            self.assertEqual(export.classify_data_path(relative), expected, relative)

    def test_parse_checksums_rejects_malformed(self):
        with self.assertRaises(export.ExportError):
            export.parse_checksums("deadbeef  file\n")