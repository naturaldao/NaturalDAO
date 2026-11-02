# Hugging Face 托管手册（POL2 score-v2）

**状态：UPLOADED（2026-11-02）。** HF 数据集仓库 [`NaturalDAO/pol2-score-v2`](https://huggingface.co/datasets/NaturalDAO/pol2-score-v2) 已发布，
revision `6f6447d7b87ffe382210d67d32868fcaabb12238`；远程校验与下载回验通过。

本文件是托管方案 + 操作手册（对齐 [datasets/general/HF.md](../../general/HF.md) 的托管规范）。数据实体不入库：仓库只保留本手册、
数据卡、清单（`manifests/full-release.json`）、样例、导出/校验脚本 [export_score_v2_hf.py](../export_score_v2_hf.py)。

- 数据集版本：`pol2-score-v2` / `v1.0.0-rc1`（GitHub Release `pol2-score-v2-v1.0.0`）
- HF 仓库：`NaturalDAO/pol2-score-v2`（dataset，public）
- HF revision：`6f6447d7b87ffe382210d67d32868fcaabb12238`（引用时固定此 sha，不要引用 `main`）
- 生成器：`datasets/pol2/export_score_v2_hf.py`（纯标准库、离线、确定性；`build` / `verify` / `stats`）
- 数据卡：导出目录根 `README.md`（由生成器产出，**不要手改**）

## 1. 发布口径（重要）

本数据集是 GitHub Release `pol2-score-v2-v1.0.0` 的**逐字节镜像**（含 release 内 `.gitignore` / `.gitattributes`），
`release/` 与资产解压结果一致。数据划分：

| 划分 | 文件 | 每格式行数 |
|---|---|---:|
| train | `data/pol2-specialist/{laya,kev}/train-m0.jsonl` | 6,166 |
| validation | `data/pol2-specialist/{laya,kev}/validation.jsonl` | 1,162 |
| calibration | `data/pol2-specialist/{laya,kev}/calibration.jsonl` | 1,051 |
| dev（已用于选模型，不是 blind） | `data/pol2-specialist/{laya,kev}/score-dev.jsonl` | 354 |
| test（公开） | `data/pol2-specialist/score-v2-new-units/{laya,kev}.jsonl` 中与上述 split 不重复的行 | 160 |

> 口径说明：Release 的 `UNASSIGNED` 池（875 行/格式）中包含 160 行未分配 test 划分；其中 144 行的 family 在
> `score-v2-integrated.json` 里被标为 `fresh_blind_families`，label 分布与 `new_label_counts.fresh_blind` 一致。
> owner 2026-11-02 确认：该 160 行是**公开 test 划分**（内部评测曾称 fresh blind，已消费一次），按全量 Release 发布；
> Release 文档中“blind 排除/未重新发布”的措辞早于本次公开口径，以 HF 数据卡与 `MANIFEST.json` 为准。建议写作者后续同步更新 Release 文档。

## 2. 导出布局与规模

~~~text
<out>/README.md                 HF 数据卡（简洁版；由生成器现算，不可手改）
<out>/MANIFEST.json             逐文件 sha256/bytes/rows + 分组统计 + 边界口径（boundary_audit.public_test=true）
<out>/CHECKSUMS.sha256          sha256sum 格式（覆盖除 MANIFEST/CHECKSUMS 外全部文件）
<out>/release/                  Release 解压树逐字节副本（50 个文件，含隐藏文件）
<out>/samples/                  仓库 samples/ 副本（4 个样例文件）
<out>/cross-check/full-release.json   仓库侧交叉核对登记
~~~

- 规模：**57 个文件 / 82.7 MiB**；JSONL 数据 47,436 行（Laya/Kev 成对，含重复口径）；
- 分组：pol2-specialist 19,216 行、general-replay 14,212 行、mixed-training 13,654 行、lineage 354 行；
- `release/CHECKSUMS.sha256` 49 项在构建时全部复算通过；`release/scripts/validate_public_release.py` PASS。

## 3. 构建与发布流程（更新版本时照做）

~~~bash
# 0) 前置：Release 资产解压到仓库外（只读）
# 1) 构建（严格模式；默认拒绝未确认的边界签名）
python datasets/pol2/export_score_v2_hf.py build \
    --release-dir <仓库外>/POL2_GitHub_Release_v1 \
    --out datasets/pol2/score-v2/hf-export --org NaturalDAO
# 2) 本地校验
python datasets/pol2/export_score_v2_hf.py verify --dir datasets/pol2/score-v2/hf-export
# 3) 上传（token 只留本机 HF 缓存，不进仓库/日志）
hf upload NaturalDAO/pol2-score-v2 datasets/pol2/score-v2/hf-export . --repo-type dataset \
    --commit-message "POL2 score-v2: mirror GitHub release <tag>"
# 4) 固定 revision
python -c "from huggingface_hub import HfApi; print(HfApi().repo_info('NaturalDAO/pol2-score-v2', repo_type='dataset').sha)"
# 5) 远程校验（公开仓库可匿名）
python datasets/general/verify_hf_remote.py --repo-id NaturalDAO/pol2-score-v2 \
    --manifest datasets/pol2/score-v2/hf-export/MANIFEST.json --revision <sha> --json
# 6) 下载回验
hf download NaturalDAO/pol2-score-v2 --repo-type dataset --revision <sha> --local-dir <tmp>
python datasets/pol2/export_score_v2_hf.py verify --dir <tmp>
~~~

上传成功后回填：`datasets/registry.json` 的 `hf_revision`、`datasets/pol2/score-v2/README.md`、本文件 §5、
以及任务页 `tasks/DATA-02-score-v2.md`。

## 4. 本次发布校验记录（2026-11-02）

- 本地：`verify` 通过（57 文件 / 82.7 MiB）；导出根 `sha256sum -c` 57/57 OK；`release/` 内上游 `sha256sum -c` 49/49 OK、验证器 PASS。
- 远程：`verify_hf_remote` status `pass`，57/57 match，hard_failures=0、unverified=0；`extra_on_remote` 3 项（根 `.gitattributes`、`MANIFEST.json`、`CHECKSUMS.sha256`，预期）。
- 下载回验：`hf download` 固定 revision → 清理 HF 本地缓存/根 `.gitattributes` 后，`verify` 通过、`sha256sum -c` 57/57 OK，与本地导出目录 `diff -rq` 一致。

## 5. 更新记录

| 日期 | 事件 | revision / 备注 |
|---|---|---|
| 2026-10-27 | Release 资产本地留档与校验 | `.agent/notes/2026-10-27-pol2-release-archive.md`；当时约定“不复制进仓库、不上传 HF” |
| 2026-11-02 | 边界复核；owner 确认 160 行为公开 test 划分；导出/校验工具完成 | 全量 57 文件 / 82.7 MiB |
| 2026-11-02 | **正式上传 HF（public）** | revision `6f6447d7b87ffe382210d67d32868fcaabb12238`；远程 + 下载回验通过 |
| 2026-11-02 | 数据卡改版：突出**安全对齐**定位与 PoL2 论文链接，数据内容简化 | 同一 revision（内容仅 README 变化） |

## 6. 边界与红线

1. **不得**把私有保留集（general v5 holdout、MRI blind、legacy blind 等）写入仓库/HF/日志/截图；本数据集的 test 划分已在第 1 节说明为公开；
2. 上传前必须跑 `build`（含边界审计）与 `verify`；不要手改导出目录；
3. token 只在 `hf auth login` 缓存，不进入命令历史、仓库或日志；
4. HF 数据卡与 `MANIFEST.json` 的数字由生成器现算，不手改；引用固定 revision；
5. 本数据集为研究预发布：`training_approved=false`、`expert_gold=false`，不是生产安全批准。