"""用本地 Git 历史和 GitHub 账号刷新过去一周的更新。"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote

START = b"<!-- readme-activity:start -->"
END = b"<!-- readme-activity:end -->"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
BOT_SUBJECT = "刷新首页最近更新"
DISPLAY_TZ = timezone(timedelta(hours=8))
WINDOW_DAYS = 7
ROW_LIMIT = 15
EMPTY = "过去 7 天暂无主分支更新。 / No updates to the main branch in the past 7 days."
REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
LOGIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9-]{0,38})(\[bot\])?")
MERGE_PR = re.compile(r"Merge pull request #([1-9][0-9]*) from \S+")
SQUASH_PR = re.compile(r"(.+) \(#([1-9][0-9]*)\)")
MARKDOWN_CHARS = frozenset("\\`*_{}[]()<>!&~|@#:")


@dataclass(frozen=True)
class Commit:
    oid: str
    parents: tuple[str, ...]
    timestamp: datetime
    subject: str
    body: str


@dataclass
class DailyUpdate:
    latest: datetime
    earliest: datetime
    login: str
    entries: list[str] = field(default_factory=list)


def git(root, *args):
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def recent_commits(root, now):
    cutoff = now - timedelta(days=WINDOW_DAYS)
    history = git(
        root, "log", "--first-parent", f"--since-as-filter=@{math.floor(cutoff.timestamp())}",
        "--encoding=UTF-8", "-z", "--format=%H%x00%P%x00%ct%x00%ae%x00%s%x00%b", "HEAD",
    )
    fields = history.split("\0")[:-1]
    commits = []
    for index in range(0, len(fields), 6):
        oid, parents, seconds, email, subject, body = fields[index:index + 6]
        timestamp = datetime.fromtimestamp(int(seconds), timezone.utc)
        if not cutoff <= timestamp <= now:
            continue
        if email == BOT_EMAIL and subject == BOT_SUBJECT:
            continue
        commits.append(Commit(oid, tuple(parents.split()), timestamp, subject, body))
    return sorted(commits, key=lambda commit: commit.timestamp, reverse=True)


def pull_reference(commit):
    if len(commit.parents) > 1:
        merge = MERGE_PR.fullmatch(commit.subject)
        if merge:
            number = merge[1]
            title = next((line.strip() for line in commit.body.splitlines() if line.strip()), "")
            return number, title or f"合并 PR #{number} / Merge PR #{number}"
    else:
        squash = SQUASH_PR.fullmatch(commit.subject)
        if squash:
            title, number = squash.groups()
            return number, title
    return None, commit.subject


def github_field(repo, resource, query):
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/{resource}", "--jq", query],
        capture_output=True, check=True, timeout=20,
    )
    return result.stdout.decode("utf-8").strip()


def activity_details(commit, repo):
    number, title = pull_reference(commit)
    if number:
        try:
            pull = json.loads(github_field(repo, f"pulls/{number}",
                                           "{sha: .merge_commit_sha, login: .user.login}"))
        except subprocess.CalledProcessError as error:
            if b"(HTTP 404)" not in error.stderr:
                raise
        else:
            if pull["sha"] == commit.oid:
                return title, pull["login"] or ""

    login = github_field(repo, f"commits/{commit.oid}", ".author.login // empty")
    return commit.subject, login


def changed_files(root, commit):
    revisions = [commit.parents[0], commit.oid] if commit.parents else ["--root", commit.oid]
    changes = git(root, "diff-tree", "--no-commit-id", "--name-status", "--no-renames",
                  "-r", "-z", *revisions).split("\0")[:-1]
    return list(zip(changes[::2], changes[1::2]))


def summary(title, files):
    if title != "Add files via upload":
        return title
    files = [path.rsplit("/", 1)[-1] for _, path in files]
    if not files:
        return title
    suffix = f" …（{len(files)} 个文件 / files）" if len(files) > 2 else ""
    return "更新文件 / Updated files：" + "、".join(files[:2]) + suffix


def updater_link(login):
    match = LOGIN.fullmatch(login)
    if not match:
        return "未关联账号 / Unlinked account"
    username, bot = match.groups()
    profile = f"apps/{username}" if bot else username
    return f"[@{markdown_text(login)}](https://github.com/{profile})"


def markdown_text(text):
    flat = " ".join(text.split())
    flat = "".join(char for char in flat if unicodedata.category(char) not in ("Cc", "Cf"))
    if len(flat) > 88:
        flat = flat[:87] + "…"
    return "".join(f"&#{ord(char)};" if char in MARKDOWN_CHARS else char for char in flat)


def core_file(files, title):
    title = title.casefold()

    def priority(change):
        status, path = change
        file = PurePosixPath(path.casefold())
        mentioned = (file.name in title
                     or (len(file.stem) >= 4 and file.stem in title)
                     or (path == "README.md" and "首页" in title))
        supporting = (file.name.startswith((".", "test_")) or "tests" in file.parts
                      or file.name.endswith(".test.js"))
        asset = file.suffix in {".pdf", ".png", ".jpg", ".jpeg", ".svg", ".zip", ".gz"}
        return status == "D", not mentioned, supporting, asset, file.name == "readme.md"

    return min(files, key=priority)


def file_link(repo, commit, status, path):
    revision = commit.parents[0] if status == "D" else commit.oid
    label = markdown_text(PurePosixPath(path).name) + ("（删除前 / Before deletion）" if status == "D" else "")
    return f"[{label}](https://github.com/{repo}/blob/{revision}/{quote(path)})"


def preview_items(items, limit, more_label):
    visible = "<br><br>".join(items[:limit])
    if len(items) > limit:
        remaining = "<br><br>".join(items[limit:])
        visible += f"<details><summary>{more_label} ({len(items) - limit})</summary>{remaining}</details>"
    return visible


def file_preview(repo, commit, title, files):
    if not files:
        return "　　无文件变更 / No changed files"
    primary = file_link(repo, commit, *core_file(files, title))
    if len(files) == 1:
        return f"　　{primary}"
    return f"　　{primary} · [详情 / Details](https://github.com/{repo}/commit/{commit.oid})"


def render_activity(root, repo, now):
    updates = {}
    for commit in recent_commits(root, now):
        title, login = activity_details(commit, repo)
        local_time = commit.timestamp.astimezone(DISPLAY_TZ)
        identity = login.casefold() if LOGIN.fullmatch(login) else commit.oid
        key = (local_time.date(), identity)
        group = updates.get(key)
        if group is None:
            if len(updates) >= ROW_LIMIT:
                continue
            group = updates[key] = DailyUpdate(local_time, local_time, login)
        group.earliest = local_time
        files = changed_files(root, commit)
        label = markdown_text(summary(title, files)) or "无标题提交 / Untitled commit"
        links = file_preview(repo, commit, title, files)
        group.entries.append(f"<strong>{local_time:%H:%M} · {label}</strong><br>{links}")

    rows = []
    for index, group in enumerate(updates.values(), 1):
        earliest = group.earliest.strftime("%m-%d %H:%M")
        time_label = earliest
        if group.latest.strftime("%H:%M") != group.earliest.strftime("%H:%M"):
            time_label += group.latest.strftime("–%H:%M")
        details = preview_items(group.entries, 2, "其他更新 · Other updates")
        rows.append(f"| {index} | {time_label} | {updater_link(group.login)} | {details} |")
    if not rows:
        return EMPTY
    header = ("| 序号<br>No. | 时间（UTC+8）<br>Time (UTC+8) | 更新人<br>Contributor | "
              "更新详情<br>Update details |\n| ---: | --- | --- | --- |")
    return "\n".join([header, *rows])


def replace_activity(readme, activity):
    start = re.search(rb"(?m)^" + START + rb"(\r?\n)", readme)
    end = re.search(rb"(?m)^" + END + rb"(?=\r?\n|$)", readme)
    if (readme.count(START) != 1 or readme.count(END) != 1
            or not start or not end or start.end() > end.start()):
        raise ValueError("README.md 必须包含一对独立、顺序正确的最近更新标记。")
    newline = start[1]
    block = newline + activity.encode("utf-8").replace(b"\n", newline) + newline * 2
    return readme[:start.end()] + block + readme[end.start():]


def update(root, repo, now):
    path = root / "README.md"
    original = path.read_bytes()
    updated = replace_activity(original, render_activity(root, repo, now))
    if updated == original:
        return False
    path.write_bytes(updated)
    return True


def parse_now(value):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--now 必须是带时区的 ISO 时间。") from error
    if timestamp.utcoffset() is None:
        raise argparse.ArgumentTypeError("--now 必须包含时区偏移。")
    return timestamp.astimezone(timezone.utc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub 仓库，格式为 owner/repo")
    parser.add_argument("--now", type=parse_now, help="复现用时间，格式为带时区偏移的 ISO 时间")
    args = parser.parse_args(argv)
    if not REPO_NAME.fullmatch(args.repo):
        parser.error("--repo 必须为 owner/repo。")
    try:
        changed = update(Path.cwd(), args.repo, args.now or datetime.now(timezone.utc))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"刷新首页失败：{error}\n")
    print("已刷新首页最近更新。" if changed else "首页最近更新无需刷新。")


if __name__ == "__main__":
    main()
