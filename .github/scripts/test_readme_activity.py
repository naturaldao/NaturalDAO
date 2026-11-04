"""验证首页更新窗口、Git 历史口径及 README 的字节边界。"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import readme_activity as activity

REPO = "naturaldao/NaturalDAO"
NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


class ReadmeActivityTest(unittest.TestCase):
    def test_replacement_preserves_outside_bytes_and_newlines(self):
        prefix = b"\xef\xbb\xbf# Test\r\n\r\n" + activity.START + b"\r\n"
        suffix = activity.END + b"\r\n\r\nOriginal text  \n"
        original = prefix + b"\r\nOld\r\n" + suffix
        updated = activity.replace_activity(original, "一\n二")
        self.assertEqual(updated, prefix + "\r\n一\r\n二\r\n\r\n".encode("utf-8") + suffix)
        self.assertEqual(activity.replace_activity(updated, "一\n二"), updated)

    def test_rejects_missing_ambiguous_or_inline_markers(self):
        for original in (
            b"no markers\n",
            activity.START + b"\n" + activity.START + b"\n" + activity.END + b"\n",
            activity.START + b"\n" + activity.END + b"\n" + activity.END,
            activity.END + b"\n" + activity.START + b"\n",
            b"inline " + activity.START + b"\n" + activity.END + b"\n",
        ):
            with self.subTest(original=original), self.assertRaisesRegex(ValueError, "标记"):
                activity.replace_activity(original, "新内容")

    def test_commits_are_sorted_without_truncating_the_week(self):
        fields = []
        for minute in [4, 1, 6, 7, 3, 9, 2, 10, 5, 8, 11, 12]:
            timestamp = int((NOW - timedelta(minutes=minute)).timestamp())
            fields.extend([str(minute), "", str(timestamp), "user@example.test", str(minute), ""])
        with patch.object(activity, "git", return_value="\0".join(fields) + "\0") as git:
            rows = activity.recent_commits(Path("."), NOW)
        self.assertEqual([row.subject for row in rows], [str(i) for i in range(1, 13)])
        args = git.call_args.args
        self.assertIn("--first-parent", args)
        self.assertEqual(args[-1], "HEAD")

    def test_cli_time_requires_offset(self):
        self.assertEqual(activity.parse_now("2026-11-04T20:00:00+08:00"), NOW)
        self.assertEqual(activity.parse_now("2026-11-04T12:00:00Z"), NOW)
        with self.assertRaisesRegex(argparse.ArgumentTypeError, "时区"):
            activity.parse_now("2026-11-04T12:00:00")

    def test_escaping_treats_subjects_and_paths_as_plain_text(self):
        escaped = activity.markdown_text("[link](https://example.test)\n<img src=x> @someone `hi` | *bold*")
        self.assertEqual(
            escaped,
            "&#91;link&#93;&#40;https&#58;//example.test&#41; &#60;img src=x&#62; "
            "&#64;someone &#96;hi&#96; &#124; &#42;bold&#42;",
        )
        self.assertEqual(activity.markdown_text("\u202e" + "a" * 200), "a" * 87 + "…")

    def test_github_profile_links_and_unknown_accounts(self):
        self.assertEqual(activity.updater_link("a-user"), "[@a-user](https://github.com/a-user)")
        self.assertEqual(activity.updater_link(""), "未关联账号 / Unlinked account")

    def test_generic_upload_title_describes_the_changed_file(self):
        self.assertEqual(activity.summary("Add files via upload", [("A", "Research/实验说明.md")]),
                         "更新文件 / Updated files：实验说明.md")

    def test_file_links_pin_added_modified_and_deleted_versions(self):
        commit = activity.Commit("after", ("before",), NOW, "", "")
        files = [("M", "说明 A.md"), ("A", "new.md"), ("D", "old.md"), ("M", "fourth.md")]
        links = activity.preview_items(
            [activity.file_link(REPO, commit, status, path) for status, path in files],
            3, "其他文件 · More files", separator="<br>")
        self.assertIn(f"/blob/after/%E8%AF%B4%E6%98%8E%20A.md", links)
        self.assertIn(f"[old.md（删除前 / Before deletion）](https://github.com/{REPO}/blob/before/old.md)", links)
        self.assertIn(f"<details><summary>其他文件 · More files (1)</summary>[fourth.md](https://github.com/{REPO}/blob/after/fourth.md)", links)

    def test_group_by_account_and_utc8_calendar_day(self):
        midnight = datetime(2026, 11, 3, 16, tzinfo=timezone.utc)
        commits = [activity.Commit(oid, ("parent",), when, title, "")
                   for oid, when, title in (
                       ("latest", midnight + timedelta(hours=2), "更新说明"),
                       ("other", midnight + timedelta(hours=1), "其他人的更新"),
                       ("same", midnight, "新增说明"),
                       ("previous", midnight - timedelta(minutes=1), "前一天"),
                       ("unknown1", midnight - timedelta(minutes=2), "未知一"),
                       ("unknown2", midnight - timedelta(minutes=3), "未知二"))]
        accounts = dict(latest="Alice", other="bob", same="alice", previous="Alice",
                        unknown1="", unknown2="")
        with (patch.object(activity, "recent_commits", return_value=commits),
              patch.object(activity, "activity_details",
                           side_effect=lambda commit, repo: (commit.subject, accounts[commit.oid])),
              patch.object(activity, "changed_files", return_value=[("M", "note.md")])):
            page = activity.render_activity(Path("."), REPO, NOW)
        self.assertIn("| 1 | 11-04 00:00–02:00 | [@Alice]", page)
        self.assertNotIn("Other updates", page)
        self.assertIn("02:00 · 更新说明</strong><br>文件 / Files: "
                      f"[note.md](https://github.com/{REPO}/blob/latest/note.md)", page)
        self.assertIn("00:00 · 新增说明</strong><br>文件 / Files: "
                      f"[note.md](https://github.com/{REPO}/blob/same/note.md)", page)
        self.assertIn("| 3 | 11-03 23:59 | [@Alice]", page)
        self.assertEqual(page.count("| 未关联账号 / Unlinked account |"), 2)
        self.assertEqual(sum(line.startswith("| ") for line in page.splitlines()), 7)

    def test_readme_limits_rows_without_folding_single_updates(self):
        commits = [activity.Commit(str(i), (), NOW, "更新", "") for i in range(31)]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            readme = root / "README.md"
            readme.write_bytes(activity.START + b"\n" + activity.END + b"\n")
            with (patch.object(activity, "recent_commits", return_value=commits) as history,
                  patch.object(activity, "activity_details",
                               side_effect=lambda commit, repo: ("更新", f"user-{commit.oid}")),
                  patch.object(activity, "changed_files", return_value=[("M", "note.md")])):
                self.assertTrue(activity.update(root, REPO, NOW))
                text = readme.read_text(encoding="utf-8")
                self.assertEqual(sum(line.startswith("| ") for line in text.splitlines()), 17)
                self.assertEqual(text.count("<strong>"), 15)
                self.assertNotIn("<details", text)
                self.assertFalse(activity.update(root, REPO, NOW))
                history.return_value = commits[:1]
                self.assertTrue(activity.update(root, REPO, NOW))
            self.assertEqual(list(root.iterdir()), [readme])

    def test_other_updates_contains_only_entries_after_the_first_two(self):
        entries = ["最新", "第二项", "第三项", "第四项"]
        self.assertEqual(activity.preview_items(entries[:2], 2, "其他更新 · Other updates"),
                         "最新<br><br>第二项")
        self.assertEqual(activity.preview_items(entries, 2, "其他更新 · Other updates"),
                         "最新<br><br>第二项<details><summary>其他更新 · Other updates (2)"
                         "</summary>第三项<br><br>第四项</details>")

    def test_pr_number_in_title_requires_matching_merge_commit(self):
        commit = activity.Commit("a" * 40, ("parent",), NOW, "直接提交 (#12)", "")
        with patch.object(activity, "github_field", side_effect=[
            '{"sha": "different", "login": "unrelated"}', "actual-author",
        ]) as lookup:
            self.assertEqual(activity.activity_details(commit, REPO),
                             (commit.subject, "actual-author"))
        self.assertEqual([call.args[1] for call in lookup.call_args_list],
                         ["pulls/12", f"commits/{commit.oid}"])


class GitActivityTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.run_git("init", "-q", "--initial-branch=main")
        self.run_git("config", "user.name", "Activity test")
        self.run_git("config", "user.email", "author@example.test")
        self.run_git("config", "commit.gpgsign", "false")
        self.run_git("config", "core.autocrlf", "false")

    def run_git(self, *args, when=None, author_when=None, email=None):
        env = os.environ.copy()
        if when is not None:
            env["GIT_COMMITTER_DATE"] = when.isoformat()
            env["GIT_AUTHOR_DATE"] = (author_when or when).isoformat()
        if email is not None:
            env["GIT_AUTHOR_EMAIL"] = email
        return subprocess.run(
            ["git", *args], cwd=self.root, env=env, capture_output=True, check=True,
        ).stdout.decode("utf-8").strip()

    def commit(self, path, subject, when, *, author_when=None, email=None):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(subject, encoding="utf-8")
        self.run_git("add", "--", path)
        self.run_git("commit", "-qm", subject, when=when, author_when=author_when, email=email)
        return self.run_git("rev-parse", "HEAD")

    def test_window_first_parent_pr_titles_and_idempotence(self):
        cutoff = NOW - timedelta(days=7)
        self.commit("root.txt", "旧根提交", cutoff - timedelta(days=1))
        edge = self.commit("edge.txt", "恰好 7 天", cutoff, author_when=cutoff - timedelta(days=1))
        self.run_git("switch", "-qc", "feature")
        self.commit("Research/side.txt", "只在功能分支的提交", NOW - timedelta(minutes=25))
        self.run_git("switch", "-q", "main")
        self.commit("old.txt", "超出窗口", cutoff - timedelta(seconds=1))
        self.run_git(
            "merge", "-q", "--no-ff", "feature", "-m", "Merge pull request #12 from test/feature",
            "-m", "合并标题 [示例]", "-m", "正文第二段", when=NOW - timedelta(minutes=20),
        )
        merge = self.run_git("rev-parse", "HEAD")
        squash = self.commit("[目录]/update.txt", "压缩合并 (#13)", NOW - timedelta(minutes=15))
        self.commit("generated.txt", activity.BOT_SUBJECT, NOW - timedelta(minutes=10),
                    email=activity.BOT_EMAIL)
        human = self.commit("user.txt", activity.BOT_SUBJECT, NOW - timedelta(minutes=5))
        bot = self.commit("other-bot.txt", "正常的机器人提交", NOW, email=activity.BOT_EMAIL)
        self.commit("future.txt", "未来的时间", NOW + timedelta(seconds=1))

        accounts = {
            "pulls/12": json.dumps({"sha": merge, "login": "pr-author"}),
            "pulls/13": json.dumps({"sha": squash, "login": "squash-author"}),
            f"commits/{human}": "human",
            f"commits/{bot}": "app[bot]",
            f"commits/{edge}": "",
        }
        lookup = patch.object(activity, "github_field", side_effect=lambda repo, resource, query: accounts[resource])
        self.addCleanup(lookup.stop)
        lookup.start()
        path = self.root / "README.md"
        before = b"# Repo\n\n" + activity.START + b"\n"
        after = activity.END + b"\n\nKeep this.\n"
        path.write_bytes(before + b"Initial\n" + after)
        self.assertTrue(activity.update(self.root, REPO, NOW))
        data = path.read_bytes()
        self.assertTrue(data.startswith(before))
        self.assertTrue(data.endswith(after))
        text = data.decode("utf-8")
        self.assertIn("更新详情<br>Update details |", text)
        self.assertIn("| 1 | 11-04 20:00 | [@app&#91;bot&#93;](https://github.com/apps/app)", text)
        self.assertIn(f"正常的机器人提交</strong><br>文件 / Files: [other-bot.txt](https://github.com/{REPO}/blob/{bot}/other-bot.txt)", text)
        self.assertIn(f"{activity.BOT_SUBJECT}</strong><br>文件 / Files: [user.txt]", text)
        self.assertIn(f"压缩合并</strong><br>文件 / Files: [&#91;目录&#93;/update.txt](https://github.com/{REPO}/blob/{squash}/", text)
        self.assertIn(f"合并标题 &#91;示例&#93;</strong><br>文件 / Files: [Research/side.txt](https://github.com/{REPO}/blob/{merge}/Research/side.txt)", text)
        self.assertIn("| 10-28 20:00 | 未关联账号 / Unlinked account | <strong>", text)
        for excluded in ("generated.txt", "只在功能分支", "正文第二段", "超出窗口", "未来的时间"):
            self.assertNotIn(excluded, text)
        with patch.object(Path, "write_bytes", side_effect=AssertionError("unchanged README rewritten")):
            self.assertFalse(activity.update(self.root, REPO, NOW))

        self.assertTrue(activity.update(self.root, REPO, NOW + timedelta(days=8)))
        self.assertEqual(path.read_bytes(), before + b"\n" + activity.EMPTY.encode("utf-8") + b"\n\n" + after)


if __name__ == "__main__":
    unittest.main()
