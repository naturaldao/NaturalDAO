# POL2 score-v2 数据集 HF 发布（2026-11-02）

## 结论

GitHub Release `pol2-score-v2-v1.0.0`（2026-10-26，未更新）已按原始字节镜像发布到 Hugging Face：
[`NaturalDAO/pol2-score-v2`](https://huggingface.co/datasets/NaturalDAO/pol2-score-v2)（public dataset），
**revision `2f28833b983f120b269793cebcc6e5bd8edae05d`**；远程校验与下载回验通过。

## 发布内容

- 形式：`release/`（Release 解压树逐字节副本，50 文件）+ 简洁 HF 数据卡 + `MANIFEST.json`（逐文件 sha256/bytes/rows + 边界口径）+ `CHECKSUMS.sha256` + `samples/` + `cross-check/`；
- 规模：57 文件 / 82.7 MiB；JSONL 47,436 行；分组 pol2-specialist 19,216 / general-replay 14,212 / mixed-training 13,654 / lineage 354；4 个 >10 MB 文件由 HF LFS 托管；
- 划分：train 6,166 / validation 1,162 / calibration 1,051 / dev 354（已用于选模型，非 blind）/ **test 160**（`UNASSIGNED` 池中与 assigned splits 不重复的行）；
  Laya/Kev 为同批行两种格式，`mixed_m10` = specialist train + 661 通用回放，M10 ⊂ M25 ⊂ M40。
- 口径：owner 确认 160 行/格式为公开 test 划分（内部评测曾称 fresh blind，已消费一次，不是未见 benchmark）；上游 Release 文档的 blind 表述早于本次公开口径，以 HF 数据卡与 `MANIFEST.json` 为准。

## 校验证据

| 项 | 结果 |
|---|---|
| 本地 `export_score_v2_hf.py verify` | pass（57 文件 / 82.7 MiB） |
| 导出根 `sha256sum -c` | 57/57 OK |
| `release/` 内上游 `sha256sum -c` / 验证器 | 49/49 OK；PASS（26 files / 47,436 rows / blind false / privacy 0） |
| 远程 `verify_hf_remote.py` | status pass；57/57 match；hard_failures=0 / unverified=0；extra_on_remote 3（根 `.gitattributes`、`MANIFEST.json`、`CHECKSUMS.sha256`，预期） |
| 下载回验 | `hf download --revision 6f8b699…` → `verify` 通过、`sha256sum -c` 57/57 OK、与本地导出目录 `diff -rq` 一致 |

## 变更文件

- 工具：`datasets/pol2/export_score_v2_hf.py`（`build/verify/stats`；确定性；默认拒绝未确认的边界签名，已确认 v1.0.0 的公开 test 口径）、`datasets/pol2/test_export_score_v2_hf.py`（28 tests）；
- 托管手册：`datasets/pol2/score-v2/HF.md`（UPLOADED，含 revision 与复现/回验命令）；
- 状态回填：`datasets/pol2/score-v2/README.md`、`datasets/registry.json`（`hf_status=uploaded`、`hf_revision`）、`tasks/DATA-02-score-v2.md`、`ROADMAP.md`。

## 后续

1. 写作者可在下次 Release 同步更正 README/AUDIT/RELEASE_REVIEW/HOLDOUT 的 blind 措辞（本数据集以现有 HF 卡为准）；
2. 无数据/许可变更时固定 revision，不再更新；新增版本按 `HF.md` 流程全量重建并回填 revision。
## 2026-11-02 更新：数据卡改版（同一数据集）

按 owner 要求，HF 数据卡改为突出**安全对齐**定位与 **PoL2 论文**链接（论文 PDF、论文仓库/研究材料、PoL2 正文），数据格式与划分仅作简要介绍；数据文件未变。

- 新 revision：`2f28833b983f120b269793cebcc6e5bd8edae05d`（仅 README 变化）；
- 远程校验 57/57 match、下载回验 57/57 且与本地导出一致（同前）。
- 2026-11-02 再次改版：开头改为面向无背景读者的通俗说明（数据卡 final revision `2f28833b983f120b269793cebcc6e5bd8edae05d`；数据文件未变）。
