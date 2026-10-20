import gzip, hashlib, os, pathlib

src = pathlib.Path('datasets/general/data/jev-probs.jsonl')
dst = pathlib.Path('datasets/general/data/jev-probs.jsonl.gz')
raw = src.read_bytes()
with open(dst, 'wb') as fh:
    with gzip.GzipFile(filename='', mode='wb', fileobj=fh, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
packed = dst.read_bytes()
print('plain  bytes=%d sha256=%s' % (len(raw), hashlib.sha256(raw).hexdigest()[:16]))
print('gzip   bytes=%d sha256=%s' % (len(packed), hashlib.sha256(packed).hexdigest()[:16]))
# 校验可逆
with gzip.open(dst, 'rb') as gz:
    back = gz.read()
print('roundtrip identical:', back == raw)
