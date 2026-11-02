# DATA-02 · POL2 score-v2 数据发布

- 领取人：w609641894 / Codex
- 状态：已集成到 `main`；GitHub 研究预发布
- 分支：`main`
- 数据：`datasets/pol2/score-v2/`
- 完整数据：GitHub Release `pol2-score-v2-v1.0.0`

## 已做

- 汇入 POL2 score 0–4 专项训练/validation/calibration/development 数据；
- 汇入 875 个新增 score 单元；
- 提供 MRI-derived 通用回放 M10/M25/M40 的 Laya/Kev 导出；
- 发布数据卡、schema 映射、holdout 清单和 40 条成对样例；
- 校验 Laya/Kev 格式对账、答案存在性、文件哈希和 blind 排除。

## 未做

- 未完成 repository canonical `case/questions/answers/labels` 四层转换；
- 本轮为模型实验切分，不冒充正式 70/20/5/5 benchmark；
- 无 human expert gold 声明。

## 下一步

1. 后续需要时补 canonical 转换；
2. 维持研究预发布边界，未经再次评审不得改成生产批准；
3. 若修改数据包，必须同步更新 Release 资产、SHA-256 和完整清单。
## 2026-11-02 复核与 HF 托管（已发布）

- Release 无更新：资产 sha256 与 2026-10-27 本地留档一致；`sha256sum -c` 49/49、`validate_public_release.py` PASS、仓库 `manifests/full-release.json` 交叉核对 23/23。
- 边界口径：`UNASSIGNED` 池（875 行/格式）= 715 行与 train/val/cal/dev 重复 + **160 行公开 test 划分**（owner 2026-11-02 确认；内部评测曾称 fresh blind，已消费一次）。上游 Release 文档的 blind 表述早于本次公开口径，以 HF 数据卡为准，建议写作者后续同步更新。
- **已上传 HF**：[`NaturalDAO/pol2-score-v2`](https://huggingface.co/datasets/NaturalDAO/pol2-score-v2)（public），revision `6f6447d7b87ffe382210d67d32868fcaabb12238`；GitHub Release v1.0.0 全量逐字节镜像（57 文件 / 82.7 MiB）+ 简洁数据卡 + MANIFEST/CHECKSUMS；远程校验 57/57、下载回验 57/57 且目录一致。
- 工具与手册：`datasets/pol2/export_score_v2_hf.py`（确定性导出/清单/校验 + 边界守卫；严格/安全子集两模式）+ 单测；`datasets/pol2/score-v2/HF.md`。
- 后续：写作者可在下次 Release 修订文档口径；无数据变更时 HF 固定 revision 不再更新。
