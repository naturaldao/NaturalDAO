import re
text = open('datasets/general/jev-validation.md', encoding='utf-8').read()
lines = text.splitlines()
print('id leak tokens:', sorted(set(re.findall(r'db-[A-Za-z0-9._:-]+', text))))
print('lines:', len(lines))
start = [i for i, l in enumerate(lines) if l.startswith('### 8.4')][0]
end = [i for i, l in enumerate(lines) if l.startswith('## 9.')][0]
for i, l in enumerate(lines[start:end], start + 1):
    if l.startswith('| ' + chr(96)) or l.startswith('|---'):
        continue
    print(i, l[:200])
