"""确定性压缩交付件 + benchmark 硬断言（与 jev_fill.py probs-public 同思路的兜底路径）。

用法：python data/jev/_pack_deliverable.py <plain.jsonl> [<out.gz>] [--splits-dir DIR]

写盘前读当前 data/splits/benchmark.jsonl 的 id，命中任一 → 非零退出、不生成 .gz；
写盘后重读 .gz 再校验一次；只打印命中条数，不打印成员 id。
"""
import gzip, hashlib, json, pathlib, sys


def split_ids(splits_dir, name):
    path = pathlib.Path(splits_dir) / (name + '.jsonl')
    if not path.is_file():
        path = pathlib.Path(splits_dir) / (name + '.jsonl.gz')
        if not path.is_file():
            raise SystemExit('缺少分区文件，无法校验：%s' % path)
    opener = gzip.open if str(path).endswith('.gz') else open
    ids = set()
    with opener(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            line = line.strip()
            if line:
                ids.add(json.loads(line)['id'])
    return ids


def guard(rows, benchmark_ids, stage):
    hits = [index for index, row in enumerate(rows) if row.get('id') in benchmark_ids]
    if hits:
        raise SystemExit('benchmark guard 触发（%s）：%d 行命中 benchmark 成员（行号 %s…）；'
                         '拒绝写盘。' % (stage, len(hits), hits[:5]))


def main(argv):
    args = [item for item in argv[1:] if not item.startswith('--')]
    options = [item for item in argv[1:] if item.startswith('--')]
    plain = pathlib.Path(args[0] if args else 'datasets/general/data/jev-probs.jsonl')
    packed = pathlib.Path(args[1] if len(args) > 1 else str(plain) + '.gz')
    splits_dir = 'datasets/general/data/splits'
    for option in options:
        if option.startswith('--splits-dir='):
            splits_dir = option.split('=', 1)[1]
    benchmark_ids = split_ids(splits_dir, 'benchmark')
    rows = []
    with plain.open(encoding='utf-8') as stream:
        for line in stream:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    guard(rows, benchmark_ids, '写盘前')
    raw = plain.read_bytes()
    with open(packed, 'wb') as handle:
        with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0, compresslevel=9) as gz:
            gz.write(raw)
    with gzip.open(packed, 'rb') as handle:
        back = handle.read()
    if back != raw:
        raise SystemExit('自检失败：.gz 解压后与明文不一致。')
    gz_rows = [json.loads(line) for line in back.decode('utf-8').splitlines() if line.strip()]
    guard(gz_rows, benchmark_ids, '写盘后/.gz')
    print('plain  %s bytes=%d sha256=%s' % (plain.name, len(raw), hashlib.sha256(raw).hexdigest()[:16]))
    print('gzip   %s bytes=%d sha256=%s' % (packed.name, packed.stat().st_size,
                                            hashlib.sha256(packed.read_bytes()).hexdigest()[:16]))
    print('rows=%d distinct_ids=%d benchmark_intersection=0' % (len(rows), len({row['id'] for row in rows})))
    print('roundtrip identical: True')


if __name__ == '__main__':
    main(sys.argv)
