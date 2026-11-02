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
## 2026-11-02 复核与 HF 托管（HOLD）

- Release 无更新：资产 sha256 与 2026-10-27 本地留档一致；`sha256sum -c` 49/49、`validate_public_release.py` PASS、仓库 `manifests/full-release.json` 交叉核对 23/23。
- **边界审计发现阻断问题**：`UNASSIGNED` 新增单元池与其 blind/holdout 声明不一致（聚合证据在维护者内部审计记录，不在公开仓库展开）；据此 **HF 上传暂停**（`NaturalDAO/pol2-score-v2` 为空仓，未传任何文件）。
- 已就绪：`datasets/pol2/export_score_v2_hf.py`（确定性导出/清单/校验 + 边界守卫；严格模式与安全子集模式）+ 单测；托管手册 `datasets/pol2/score-v2/HF.md`。
- 下一步（维护者/owner）：修正 Release（例如删除 unassigned 池与其索引清单、替换命中盲测的仓库样例、更正 README/AUDIT/REVIEW/HOLDOUT 声明），然后按 HF.md 严格模式上传并固定 revision。
