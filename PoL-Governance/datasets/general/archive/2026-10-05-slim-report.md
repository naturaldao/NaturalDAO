# 字段精简报告（items.native → items.native.slim）

- 源文件：15,983 条，43,374,053 字节（2713.8 B/条）
- 精简后：15,983 条，28,415,061 字节（1777.8 B/条）
- **省下 14,958,992 字节（34.5%）**；manifest 另占 10,226 字节

## 每字段字节占比（精简前 → 精简后）

| 字段 | 精简前字节 | 占比 | 精简后字节 | 占比 | 处理方式 |
|---|---:|---:|---:|---:|---|
| questions | 15,647,101 | 36.1% | 11,990,603 | 42.2% | 保留题目；origin/source_key 移入 defaults，prompt==key 时省略 prompt |
| state | 7,897,022 | 18.2% | 7,897,022 | 27.8% | 保留（原始情境文本，不加工） |
| meta | 7,573,321 | 17.5% | 0 | 0.0% | 按实测分三档：全库恒定→defaults、来源内恒定→sources[].meta、逐条变化→m |
| targets | 5,394,177 | 12.4% | 5,394,177 | 19.0% | 保留（原生真值） |
| source | 4,487,899 | 10.3% | 0 | 0.0% | 拆成 src 下标 + row；dataset/revision/config/split/license/url 移入 manifest |
| source.url | 1,006,186 | 2.3% | 0 | 0.0% |  |
| source.revision | 671,286 | 1.6% | 0 | 0.0% |  |
| id | 516,115 | 1.2% | 516,115 | 1.8% | 保留（记录身份；可由 src+row 复算） |
| source.dataset | 494,730 | 1.1% | 0 | 0.0% |  |
| source.slug | 324,319 | 0.8% | 0 | 0.0% |  |
| domain | 324,050 | 0.8% | 324,050 | 1.1% | 保留（来源自身字段映射） |
| source.config | 190,915 | 0.4% | 0 | 0.0% |  |
| source.license | 175,058 | 0.4% | 0 | 0.0% |  |
| source.split | 111,881 | 0.3% | 0 | 0.0% |  |
| lang | 63,932 | 0.1% | 0 | 0.0% | 全库一致，移入 manifest.defaults |
| source.row | 59,071 | 0.1% | 0 | 0.0% |  |

## questions 内部（精简前 → 精简后）

| 子字段 | 精简前字节 | 占比 | 精简后字节 | 占比 |
|---|---:|---:|---:|---:|
| options | 6,908,979 | 15.9% | 6,908,979 | 24.3% |
| prompt | 2,991,039 | 6.9% | 1,759,773 | 6.2% |
| key | 1,405,148 | 3.2% | 1,405,148 | 5.0% |
| source_key | 1,405,148 | 3.2% | 0 | 0.0% |
| scale | 816,046 | 1.9% | 816,046 | 2.9% |
| origin | 191,312 | 0.4% | 0 | 0.0% |
| kind | 170,263 | 0.4% | 170,263 | 0.6% |

## meta 内部（精简前）

| meta 键 | 字节 | 占比 | 去向 |
|---|---:|---:|---|
| meta.native_state_note | 693,557 | 1.6% | manifest.sources[].meta（来源内恒定） |
| meta.domain_rule | 517,162 | 1.2% | 整批删掉（可按 src+row 从原始行复原） |
| meta.created_at | 431,541 | 1.0% | manifest.defaults（全库恒定） |
| meta.quality_flags | 383,780 | 0.9% | manifest.sources[].meta（来源内恒定） |
| meta.native_source | 329,271 | 0.8% | 整批删掉（可按 src+row 从原始行复原） |
| meta.native_id | 249,791 | 0.6% | 整批删掉（可按 src+row 从原始行复原） |
| meta.key_source | 207,779 | 0.5% | manifest.sources[].meta（来源内恒定） |
| meta.converter | 191,796 | 0.4% | manifest.defaults（全库恒定） |
| meta.native_domain | 158,348 | 0.4% | 整批删掉（可按 src+row 从原始行复原） |
| meta.question_origin | 127,864 | 0.3% | manifest.defaults（全库恒定） |
| meta.native_config_shape | 116,882 | 0.3% | 整批删掉（可按 src+row 从原始行复原） |
| meta.converter_version | 79,915 | 0.2% | manifest.defaults（全库恒定） |
| meta.native_family | 76,925 | 0.2% | 整批删掉（可按 src+row 从原始行复原） |
| meta.native | 63,932 | 0.1% | manifest.defaults（全库恒定） |
| meta.native_task | 59,071 | 0.1% | 整批删掉（可按 src+row 从原始行复原） |
| meta.native_kind | 52,150 | 0.1% | 整批删掉（可按 src+row 从原始行复原） |

## 溯源怎么保证

每条记录的 (src, row) 配上 manifest 里该来源的 dataset / revision / config / split / license / url
以及原始文件 D:\pol2-raw\<slug>\rows.jsonl 的 sha256，能唯一定位到原始数据集的那一行。
被整批删掉的 meta 键，manifest.dropped_meta_keys 逐键写明「按 (src,row) 读原始行，字段同名」。

## 可复算校验

slim 文件能还原成完整契约条目，与原件逐字段比对：

    uv run --no-project --offline python datasets/general/slim.py expand \
        --manifest data/items.native.manifest.json --slim data/items.native.slim.jsonl \
        --out <仓库外>\expanded.jsonl --expect data/items.native.jsonl

结果：**15,983 条逐字段比对，0 处不一致**（id / domain / lang / state / questions / targets / source 与可复原键之外的 meta 全部相等）
