"""Verify formatting changes preserve technical blocks and sources."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[3]
old = subprocess.check_output([
    'git', '-c', 'safe.directory=C:/Users/Administrator/Documents/ChatGPT/NaturalDAO',
    '-c', 'safe.directory=C:/Users/Administrator/Documents/ChatGPT/NaturalDAO-storage-v2',
    'show', '817037f:Research/PoL2存储技术方案.md'], cwd=root).decode('utf-8')
new = (root / 'Research/Storage/02-技术方案/PoL2存储技术方案.md').read_text(encoding='utf-8')
assert re.findall(r'```[\s\S]*?```', old) == re.findall(r'```[\s\S]*?```', new)
assert re.findall(r'\$\$[\s\S]*?\$\$', old) == re.findall(r'\$\$[\s\S]*?\$\$', new)
assert set(re.findall(r'https?://[^)\s]+', old)) <= set(re.findall(r'https?://[^)\s]+', new))
assert len(re.findall(r'<a id="section-', new)) == 16
body = re.sub(r'<a id="section-\d+"></a>\s*', '', new)
body = re.sub(r'<!-- readability-v2 -->[\s\S]*?(?=## 1\.)', '', body, count=1)
assert re.sub(r'\s', '', body) == re.sub(r'\s', '', old)
for target in re.findall(r'\]\((\./[^)]+)\)', new):
    assert (root / 'Research/Storage/02-技术方案' / target).exists(), target
print('PASS: original text, code, formulas, sources, local links and navigation preserved.')
