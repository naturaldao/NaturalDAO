"""Hypothetical PoL2 capacity arithmetic; licensed under Proof of Love2.

Standard-library-only calculator. All sizes are decimal bytes. This is not a
benchmark, hardware recommendation, price estimate, or availability guarantee.
"""
import argparse
import json
from decimal import Decimal
from pathlib import Path

KEYS = {
    'events_per_day', 'retention_days', 'payload_bytes', 'indexed_fraction',
    'vectors_per_indexed_event', 'dimensions', 'float_bytes', 'graph_degree',
    'neighbor_bytes', 'node_overhead_bytes', 'pq_code_bytes', 'compression_ratio',
    'archive_ec_factor', 'vector_replicas', 'ann_replicas', 'metadata_bytes',
    'metadata_replicas', 'hot_days', 'cache_copies', 'rebuild_temp_factor',
    'free_reserve_fraction',
}
POSITIVE = {'events_per_day', 'retention_days', 'payload_bytes', 'dimensions',
            'float_bytes', 'neighbor_bytes', 'archive_ec_factor',
            'vector_replicas', 'ann_replicas', 'metadata_replicas'}
INTEGERS = POSITIVE - {'archive_ec_factor'} | {
    'vectors_per_indexed_event', 'graph_degree', 'node_overhead_bytes',
    'pq_code_bytes', 'metadata_bytes', 'hot_days', 'cache_copies',
}


def calculate(parameters):
    """Validate a complete schema and return exact Decimal byte quantities."""
    if not isinstance(parameters, dict) or set(parameters) != KEYS:
        raise ValueError('All schema keys are required; unknown keys are forbidden')
    p = {}
    for key, value in parameters.items():
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError(f'{key}: expected a number, not boolean/string')
        number = Decimal(str(value))
        if not number.is_finite() or number < 0:
            raise ValueError(f'{key}: must be finite and nonnegative')
        if key in POSITIVE and number <= 0:
            raise ValueError(f'{key}: must be positive')
        if key in INTEGERS and number != number.to_integral_value():
            raise ValueError(f'{key}: must be an integer')
        p[key] = number
    if not 0 <= p['indexed_fraction'] <= 1:
        raise ValueError('indexed_fraction: must be in [0, 1]')
    if p['compression_ratio'] <= 0:
        raise ValueError('compression_ratio: must be positive; encoded data may expand')
    if not 0 <= p['free_reserve_fraction'] < 1:
        raise ValueError('free_reserve_fraction: must be in [0, 1)')
    if p['archive_ec_factor'] < 1 or p['hot_days'] > p['retention_days']:
        raise ValueError('EC factor must be >= 1; hot days cannot exceed retention')
    n = p['events_per_day'] * p['retention_days']
    nv = n * p['indexed_fraction'] * p['vectors_per_indexed_event']
    raw = n * p['payload_bytes']
    archive = raw * p['compression_ratio'] * p['archive_ec_factor']
    vectors = nv * p['dimensions'] * p['float_bytes'] * p['vector_replicas']
    ann = nv * (p['pq_code_bytes'] + p['graph_degree'] * p['neighbor_bytes']
                + p['node_overhead_bytes']) * p['ann_replicas']
    metadata = n * p['metadata_bytes'] * p['metadata_replicas']
    hot = (p['events_per_day'] * p['hot_days'] * p['payload_bytes']
           * p['compression_ratio'] * p['cache_copies'])
    temporary = p['rebuild_temp_factor'] * (vectors + ann)
    used = archive + vectors + ann + metadata + hot + temporary
    return {
        'events': n, 'vectors': nv, 'raw_logical_bytes': raw,
        'archive_physical_bytes': archive, 'canonical_vectors_physical_bytes': vectors,
        'ann_physical_bytes': ann, 'metadata_physical_bytes': metadata,
        'hot_cache_extra_bytes': hot, 'rebuild_temporary_bytes': temporary,
        'peak_used_bytes': used,
        'provisioned_bytes': used / (1 - p['free_reserve_fraction']),
    }


def run_scenarios(document):
    if not isinstance(document, dict) or set(document) != {'common', 'scenarios'}:
        raise ValueError('Expected exactly common and scenarios')
    if not isinstance(document['common'], dict) or not isinstance(document['scenarios'], dict):
        raise ValueError('common and scenarios must be objects')
    results = {}
    for name, scenario in document['scenarios'].items():
        if not isinstance(scenario, dict) or set(scenario) & set(document['common']):
            raise ValueError('Scenario fields must be objects and cannot override common fields')
        params = {**document['common'], **scenario}
        sizes = calculate(params)
        results[name] = {
            'hypothetical_inputs': params,
            'exact_quantities': {key: str(value) for key, value in sizes.items()},
            'provisioned_decimal_TB': str(sizes['provisioned_bytes'] / Decimal(10**12)),
            'provisioned_decimal_PB': str(sizes['provisioned_bytes'] / Decimal(10**15)),
        }
    return results


def markdown(results):
    lines = ['# PoL2 V2 容量假设情景（非实测）', '',
             '所有输入均为规划假设；十进制 TB=10¹² bytes、PB=10¹⁵ bytes。', '',
             '| 情景 | 年事件数 | 向量数 | 峰值已用 TB | 预留后配置 TB | 配置 PB |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name, record in results.items():
        q = record['exact_quantities']
        lines.append(f"| {name} | {q['events']} | {q['vectors']} | "
                     f"{Decimal(q['peak_used_bytes']) / Decimal(10**12):,.6f} | "
                     f"{Decimal(record['provisioned_decimal_TB']):,.6f} | "
                     f"{Decimal(record['provisioned_decimal_PB']):,.9f} |")
    lines += ['', '## 物理组成（十进制 TB）', '',
              '| 情景 | 压缩归档含 EC | 规范向量副本 | ANN 副本 | 元数据副本 | 热原文额外副本 | 重建临时 |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    fields = ['archive_physical_bytes', 'canonical_vectors_physical_bytes',
              'ann_physical_bytes', 'metadata_physical_bytes', 'hot_cache_extra_bytes',
              'rebuild_temporary_bytes']
    for name, record in results.items():
        values = [f"{Decimal(record['exact_quantities'][f]) / Decimal(10**12):,.6f}" for f in fields]
        lines.append('| ' + name + ' | ' + ' | '.join(values) + ' |')
    lines += ['', '## 口径与复算', '',
              '`python capacity_model.py --scenarios scenarios.json --json-out capacity_results.json --markdown-out 容量情景结果.md`', '',
              '`python -m unittest -v test_capacity_model.py`', '',
              'N=日事件数×保留天数；Nvec=N×索引比例×每索引事件向量数。',
              '归档=N×payload×压缩比×EC 系数；规范向量=Nvec×维度×每维字节×副本数。',
              'ANN=Nvec×(PQ 字节+邻居数×邻居 ID 字节+节点开销)×ANN 副本数；不再次计完整向量。',
              '元数据=N×每事件元数据×元数据副本；热缓存=日事件数×热天数×payload×压缩比×额外副本数。',
              '重建临时=临时系数×(规范向量物理量+ANN 物理量)。',
              '配置容量=(归档+规范向量+ANN+元数据+热缓存+重建临时)/(1−空闲预留比例)。', '',
              '热缓存是在完整保留期归档之上的额外副本。元数据覆盖全部事件，不只覆盖索引事件。',
              '压缩比=编码后字节/原始字节；不可压缩内容与封装开销可能使该值大于 1。情景中的 0.5 仅为假设，不是压缩效果保证。',
              'f 是事件被索引的比例；m 是每个索引事件的向量数，已经包含分块/多向量的倍数，不可再次重复乘。',
              'JSON 保存 Decimal 字符串；有限小数分量精确计算，循环小数除法按 Decimal 默认 28 位有效数字舍入，表中再按显示位数舍入。', '',
              '## 不覆盖的成本', '',
              '不覆盖视频等大对象、模型权重、网络容量/WAL、EC 修复流量与暂存、功耗、数据库页/TOAST/索引膨胀、分片倾斜、备份历史及训练数据物化。',
              '重建临时系数只覆盖上述向量与 ANN 字节，不代表已证明可用的全系统恢复空间。',
              '原始归档不能视为免费的训练材料：解压、分词、去重、格式转换与训练副本须另预算。',
              '25% 空闲指配置容量中保留四分之一，故除以 0.75；不能按已用量乘 1.25。', '',
              '许可：Proof of Love2。未引入第三方代码。']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', type=Path, default=Path(__file__).with_name('scenarios.json'))
    parser.add_argument('--json-out', type=Path)
    parser.add_argument('--markdown-out', type=Path)
    args = parser.parse_args()
    results = run_scenarios(json.loads(args.scenarios.read_text(encoding='utf-8')))
    encoded = json.dumps(results, ensure_ascii=False, indent=2) + '\n'
    if args.json_out:
        args.json_out.write_text(encoded, encoding='utf-8')
    if args.markdown_out:
        args.markdown_out.write_text(markdown(results), encoding='utf-8')
    print(encoded)


if __name__ == '__main__':
    main()
