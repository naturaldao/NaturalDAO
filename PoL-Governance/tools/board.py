"""Read task ownership from fetched pol/* branches; never fetch or mutate Git."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def configure_stdio():
    """Write UTF-8 whatever the host console code page is.

    Task pages are free-form text: they may carry characters the console
    code page cannot represent (a Windows console defaults to cp936 here), and
    a status line echoed from someone else's page can therefore abort the whole
    report. Encoding the output ourselves keeps the report readable when
    redirected and prevents that abort.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(encoding='utf-8', errors='replace')


def task_location(ref, remote, module):
    prefix = f'{remote}/pol/'
    if not ref.startswith(prefix):
        return None
    parts = ref[len(prefix):].split('/')
    if len(parts) != 2 or not all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', x) for x in parts):
        return None
    task, name = parts
    path = f'tasks/{task}-{name}.md'
    return task, f'{module}/{path}' if module else path


def field(text, label):
    match = re.search(r'^- ' + re.escape(label) + r'：[ \t]*(.*)$', text, re.MULTILINE)
    return match.group(1).strip() if match else ''


def fields(text):
    owner, agent, status = (field(text, label) for label in ('领取人', 'Agent', '状态'))
    lines = text.splitlines()
    for i, line in enumerate(lines):
        header = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if header == ['领取人 / Agent', '状态 / 最近进展（Agent 更新）'] and i + 2 < len(lines):
            cells = [cell.strip() for cell in lines[i + 2].strip().strip('|').split('|')]
            if len(cells) == 2:
                identity, status = cells
                owner, separator, agent = identity.partition(' / ')
                if not separator:
                    agent = ''
            break
    return {'owner': owner.strip(), 'agent': agent.strip(), 'status': status,
            'updated_at': field(text, '更新时间'), 'next': field(text, '下一步'),
            'blocker': field(text, '阻塞 / 需要谁帮助')}


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
                          encoding='utf-8', errors='replace', check=True).stdout.strip()


def baseline_ref(repo, remote):
    for name in ('HEAD', 'main'):
        try:
            return git(repo, 'rev-parse', '--symbolic-full-name', '--verify',
                       f'refs/remotes/{remote}/{name}')
        except subprocess.CalledProcessError:
            continue
    return None


def task_page(repo, ref, branch, task, path):
    try:
        return path, git(repo, 'show', f'{ref}:{path}')
    except subprocess.CalledProcessError:
        # 兼容旧任务页的文件名，只接受明确声明当前分支的唯一匹配。
        directory = path.rsplit('/', 1)[0]
        candidates = git(repo, '-c', 'core.quotepath=false', 'ls-tree', '-r', '--name-only',
                         ref, '--', f'{directory}/').splitlines()
        matches = []
        for candidate in candidates:
            if candidate.startswith(f'{directory}/{task}-') and candidate.endswith('.md'):
                page = git(repo, 'show', f'{ref}:{candidate}')
                if field(page, '分支').strip('`') == branch:
                    matches.append((candidate, page))
        return matches[0] if len(matches) == 1 else (path, None)


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote', default='origin')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.remote):
        parser.error('Invalid remote name')
    root = Path(__file__).resolve().parents[1]
    try:
        repo = Path(git(root, 'rev-parse', '--show-toplevel')).resolve()
        module = root.relative_to(repo).as_posix()
        module = '' if module == '.' else module
        prefix = f'refs/remotes/{args.remote}/pol/'
        refs = git(repo, 'for-each-ref', '--format=%(refname:short)', prefix).splitlines()
        baseline = baseline_ref(repo, args.remote)
        integrated = (set(git(repo, 'for-each-ref', '--format=%(refname:short)',
                              f'--merged={baseline}', prefix).splitlines()) if baseline else None)
        rows = []
        for ref in refs:
            location = task_location(ref, args.remote, module)
            if not location:
                rows.append({'branch': ref, 'status': 'unrecognized_branch_name'})
                continue
            task, path = location
            branch = ref.removeprefix(f'{args.remote}/')
            task_file, page = task_page(repo, ref, branch, task, path)
            row = {'task': task, 'branch': ref, 'task_file': task_file,
                   'tip_in_baseline': ref in integrated if integrated is not None else None}
            if page is None:
                row.update(owner='', status='task_file_missing')
            else:
                row.update(fields(page))
            rows.append(row)
        print(json.dumps({'source': 'locally_fetched_remote_refs', 'baseline': baseline,
                          'refresh': f'git fetch {args.remote}', 'tasks': rows},
                         ensure_ascii=False, indent=2))
    except UnicodeEncodeError as error:
        # UnicodeEncodeError is a ValueError, so it must be reported before that
        # clause or it is misattributed to a Git problem.
        parser.exit(2, f'Cannot encode the report for this output stream: {error.encoding}. '
                       f'Redirect to a file or set PYTHONIOENCODING=utf-8.\n')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'Cannot read task branches: {type(error).__name__}. Run inside a Git repository and fetch the remote first.\n')


if __name__ == '__main__':
    main()
