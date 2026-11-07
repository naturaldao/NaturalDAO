"""Verify local and cross-repository links in the public entrypoint documents."""

import argparse
import posixpath
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


REPOSITORIES = ("NaturalDAO", "NaturalDAO-2nd")
ENTRYPOINTS = ("README.md", "CONTRIBUTING.md", "SECURITY.md")
MARKDOWN_LINK = re.compile(r"\]\(\s*(<[^>\n]+>|[^\s)]+)")
REPOSITORY_LINK = re.compile(
    r"/naturaldao/(NaturalDAO(?:-2nd)?)/(blob|tree)/main/(.+)"
)


def repository_paths(root):
    tree = subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
        encoding="utf-8",
    )
    files = set(tree.rstrip("\0").split("\0"))
    directories = {
        str(parent) for file in files for parent in PurePosixPath(file).parents
    }
    return files, directories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", choices=REPOSITORIES)
    parser.add_argument("companion", type=Path)
    args = parser.parse_args()

    companion = next(name for name in REPOSITORIES if name != args.repository)
    paths = {
        args.repository: repository_paths(Path.cwd()),
        companion: repository_paths(args.companion),
    }

    failures = []
    checked = 0
    for entrypoint in ENTRYPOINTS:
        for line_number, line in enumerate(
            Path(entrypoint).read_text(encoding="utf-8").splitlines(), start=1
        ):
            for link in MARKDOWN_LINK.findall(line):
                target = urlsplit(link.strip("<>"))
                if not target.path:
                    continue
                path = unquote(target.path)
                if target.scheme or target.netloc:
                    match = REPOSITORY_LINK.fullmatch(path) if target.netloc == "github.com" else None
                    if not match:
                        continue
                    repository, kind, path = match.groups()
                    files, directories = paths[repository]
                    candidates = files if kind == "blob" else directories
                else:
                    files, directories = paths[args.repository]
                    candidates = files | directories
                checked += 1
                if posixpath.normpath(path) not in candidates:
                    failures.append(f"{entrypoint}:{line_number}: missing target {link}")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Checked {checked} entrypoint links.")


if __name__ == "__main__":
    main()
