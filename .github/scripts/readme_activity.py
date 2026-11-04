"""用本地 Git 历史和 GitHub 账号刷新首页的过去 72 小时更新。"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

START = b"<!-- readme-activity:start -->"
END = b"<!-- readme-activity:end -->"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
BOT_SUBJECT = "刷新首页最近更新"
DISPLAY_TZ = timezone(timedelta(hours=8))
WINDOW_HOURS = 72
LIMIT = 10
EMPTY = f"过去 {WINDOW_HOURS} 小时暂无主分支更新。"
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


def git(root, *args):
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def recent_commits(root, now):
    cutoff = now - timedelta(hours=WINDOW_HOURS)
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
    return sorted(commits, key=lambda commit: commit.timestamp, reverse=True)[:LIMIT]


def title_and_url(commit, repo):
    base = f"https://github.com/{repo}"
    if len(commit.parents) > 1:
        merge = MERGE_PR.fullmatch(commit.subject)
        if merge:
            number = merge[1]
            title = next((line.strip() for line in commit.body.splitlines() if line.strip()), "")
            return title or f"合并 PR #{number}", f"{base}/pull/{number}"
    else:
        squash = SQUASH_PR.fullmatch(commit.subject)
        if squash:
            title, number = squash.groups()
            return title, f"{base}/pull/{number}"
    return commit.subject or "无标题提交", f"{base}/commit/{commit.oid}"


def github_field(repo, resource, query):
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/{resource}", "--jq", query],
        capture_output=True, check=True, timeout=20,
    )
    return result.stdout.decode("utf-8").strip()


def activity_details(commit, repo):
    title, url = title_and_url(commit, repo)
    if url.startswith(f"https://github.com/{repo}/pull/"):
        number = url.rsplit("/", 1)[-1]
        try:
            pull = json.loads(github_field(repo, f"pulls/{number}",
                                           "{sha: .merge_commit_sha, login: .user.login}"))
        except subprocess.CalledProcessError as error:
            if b"(HTTP 404)" not in error.stderr:
                raise
        else:
            if pull["sha"] == commit.oid:
                return title, pull["login"] or "", f"PR #{number}", url

    login = github_field(repo, f"commits/{commit.oid}", ".author.login // empty")
    url = f"https://github.com/{repo}/commit/{commit.oid}"
    return commit.subject, login, commit.oid[:7], url


def summary(root, commit, title):
    if title != "Add files via upload":
        return title
    revisions = [commit.parents[0], commit.oid] if commit.parents else ["--root", commit.oid]
    paths = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", *revisions)
    files = [path.rsplit("/", 1)[-1] for path in paths.split("\0") if path]
    if not files:
        return title
    suffix = f"等 {len(files)} 个文件" if len(files) > 2 else ""
    return "更新文件：" + "、".join(files[:2]) + suffix


def updater_link(login):
    match = LOGIN.fullmatch(login)
    if not match:
        return "未关联账号"
    username, bot = match.groups()
    profile = f"apps/{username}" if bot else username
    return f"[@{markdown_text(login)}](https://github.com/{profile})"


def markdown_text(text):
    flat = " ".join(text.split())
    flat = "".join(char for char in flat if unicodedata.category(char) not in ("Cc", "Cf"))
    if len(flat) > 88:
        flat = flat[:87] + "…"
    return "".join(f"&#{ord(char)};" if char in MARKDOWN_CHARS else char for char in flat)


def render_activity(root, repo, now):
    commits = recent_commits(root, now)
    if not commits:
        return EMPTY
    lines = ["| 序号 | 时间（UTC+8） | 更新人 | 更新内容 | 链接 |",
             "| ---: | --- | --- | --- | --- |"]
    for index, commit in enumerate(commits, 1):
        title, login, link_label, url = activity_details(commit, repo)
        local_time = commit.timestamp.astimezone(DISPLAY_TZ).strftime("%m-%d %H:%M")
        updater = updater_link(login)
        label = markdown_text(summary(root, commit, title)) or "无标题提交"
        lines.append(f"| {index} | {local_time} | {updater} | {label} | [{link_label}]({url}) |")
    return "\n".join(lines)


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
