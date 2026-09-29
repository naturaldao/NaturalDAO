"""Read task ownership from fetched pol/* branches; never fetch or mutate Git."""
import argparse
import json
import re
import subprocess
from pathlib import Path


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


def fields(text):
    def get(label):
        match = re.search(r'^- ' + re.escape(label) + r'：[ \t]*(.*)$', text, re.MULTILINE)
        return match.group(1).strip() if match else ''
    owner, agent, status = get('领取人'), get('Agent'), get('状态')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == '| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |' and i + 2 < len(lines):
            cells = [cell.strip() for cell in lines[i + 2].strip().strip('|').split('|')]
            if len(cells) == 2:
                identity, status = cells
                owner, separator, agent = identity.partition(' / ')
                if not separator:
                    agent = ''
            break
    return {'owner': owner.strip(), 'agent': agent.strip(), 'status': status,
            'updated_at': get('更新时间'), 'next': get('下一步'),
            'blocker': get('阻塞 / 需要谁帮助')}


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
                          encoding='utf-8', errors='replace', check=True).stdout.strip()


def main():
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
        refs = git(repo, 'for-each-ref', '--format=%(refname:short)',
                   f'refs/remotes/{args.remote}/pol/').splitlines()
        rows = []
        for ref in refs:
            location = task_location(ref, args.remote, module)
            if not location:
                rows.append({'branch': ref, 'status': 'unrecognized_branch_name'})
                continue
            task, path = location
            row = {'task': task, 'branch': ref, 'task_file': path}
            try:
                row.update(fields(git(repo, 'show', f'{ref}:{path}')))
            except subprocess.CalledProcessError:
                row.update(owner='', status='task_file_missing')
            rows.append(row)
        print(json.dumps({'source': 'locally_fetched_remote_refs',
                          'refresh': f'git fetch {args.remote}', 'tasks': rows},
                         ensure_ascii=False, indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'Cannot read task branches: {type(error).__name__}. Run inside a Git repository and fetch the remote first.\n')


if __name__ == '__main__':
    main()
