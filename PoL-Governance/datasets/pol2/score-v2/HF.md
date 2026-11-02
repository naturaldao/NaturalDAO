# Hugging Face 托管手册（POL2 score-v2）

**状态：HOLD（2026-11-02）——未上传任何文件。** HF 数据集仓库 `NaturalDAO/pol2-score-v2` 已创建（public，仅默认 `.gitattributes`），
但 2026-11-02 复核对上游 Release 的边界检查发现：`UNASSIGNED` 新增单元池与其 `HOLDOUT` / `RELEASE_REVIEW` 的 blind 排除声明不一致，
因此**暂停上传**，等待上游修正版 Release（如 `v1.0.1`）后再发布；详见 §1 与维护者内部审计记录（不进入公开仓库）。

本文件是托管方案 + 操作手册（对齐 [datasets/general/HF.md](../../general/HF.md) 的托管规范）。数据实体不入库：仓库只保留本手册、
数据卡、清单（`manifests/full-release.json`）、样例与导出/校验脚本 [export_score_v2_hf.py](../export_score_v2_hf.py)。

- 数据集版本：`pol2-score-v2` / `v1.0.0-rc1`（GitHub Release `pol2-score-v2-v1.0.0`）
- 目标 HF 仓库：`NaturalDAO/pol2-score-v2`（dataset，public；当前为空仓）
- 生成器：`datasets/pol2/export_score_v2_hf.py`（纯标准库、离线、确定性；`build` / `verify` / `stats`）
- 数据卡：导出目录根 `README.md`（由生成器产出，**不要手改**）

## 0. 快速流程（解除 HOLD 后执行）

~~~bash
# 0) 前置：上游 Release 已修正（无 unassigned pool / 盲测边界一致），并已下载解压到仓库外
# 1) 严格构建（不排除任何文件；构建内部会做边界审计，检测到边界不一致会拒绝）
python datasets/pol2/export_score_v2_hf.py build \
    --release-dir <仓库外>/POL2_GitHub_Release_v1 \
    --out datasets/pol2/score-v2/hf-export --org NaturalDAO
# 2) 本地校验（离线）
python datasets/pol2/export_score_v2_hf.py verify --dir datasets/pol2/score-v2/hf-export
# 3) 上传（需 write token；token 只留本机 HF 缓存，不进仓库/日志）
hf upload NaturalDAO/pol2-score-v2 datasets/pol2/score-v2/hf-export . --repo-type dataset
# 4) 固定 revision
python -c "from huggingface_hub import HfApi; print(HfApi().repo_info('NaturalDAO/pol2-score-v2', repo_type='dataset').sha)"
# 5) 远程校验（公开仓库可匿名）
python datasets/general/verify_hf_remote.py --repo-id NaturalDAO/pol2-score-v2 \
    --manifest datasets/pol2/score-v2/hf-export/MANIFEST.json --revision <sha> --json
# 6) 下载回验（固定 revision；再跑 verify 与 sha256sum -c）
hf download NaturalDAO/pol2-score-v2 --repo-type dataset --revision <sha> --local-dir <tmp>
python datasets/pol2/export_score_v2_hf.py verify --dir <tmp>
~~~

回填清单（上传成功后）：

1. `datasets/registry.json` 的 `pol2-score-v2`：`hf_status=uploaded`、`hf_revision`、`hf_repo`；
2. 本文件 §6 更新记录（日期 / revision / 执行人）；
3. `datasets/pol2/score-v2/README.md` 增加 HF 状态与固定 revision；
4. 阶段报告 `docs/reports/`（≤每 10 轮一份）；引用数据时使用 commit sha，不用 `main`。

## 1. 为什么 HOLD：上游 Release 的边界问题（2026-11-02 复核）

- 复核对象：Release `pol2-score-v2-v1.0.0`（published 2026-10-26；资产 sha256 与本地留档一致，无更新版本）。
- Release 完整性检查全部通过：`sha256sum -c CHECKSUMS.sha256` 49/49、`scripts/validate_public_release.py` PASS、
  仓库 `manifests/full-release.json` 23/23 对齐；但**文件名/结构检查无法发现族的归属问题**。
- 边界审计（仅用 Release 内公开 manifest + 内容哈希，不读取/不导出逐例内容）发现：
  `unassigned` 新增单元池（`data/pol2-specialist/score-v2-new-units/{kev,laya}.jsonl`，各 875 行）不是单纯的待分配池，
  其中包含未分配的 blind 单元，且池行内带 label/target；`manifests/score-v2-new-units.json` 的索引进一步登记了 family/label。
  这与 Release 自身 `README` / `AUDIT` / `RELEASE_REVIEW` / `HOLDOUT` 的 blind 排除声明矛盾。
- 仓库 `datasets/pol2/score-v2/samples/specialist-*.jsonl` 亦有少量行来自这些未分配单元（已在 `main` 公开）。
- 结论：在**任何**公开托管（HF 或其它镜像）之前必须由上游修正 Release 与样例；本 session 只做审计与工具准备，**不传播**。

## 2. 导出布局（两种模式）

~~~text
<out>/README.md                 HF 数据卡（生成器产出，含边界审计说明；不可手改）
<out>/MANIFEST.json             逐文件 sha256/bytes/rows + 分组统计 + 边界审计 + 排除清单
<out>/CHECKSUMS.sha256          sha256sum 格式（覆盖除 MANIFEST/CHECKSUMS 外全部文件）
<out>/release/                  Release 解压树的逐字节副本（严格模式=完整；安全子集模式=排除项见 MANIFEST）
<out>/samples/                  仓库 datasets/pol2/score-v2/samples/ 的副本（命中盲测的样例文件会被排除）
<out>/cross-check/full-release.json   仓库侧交叉核对登记
~~~

### 2.1 严格模式（上游修正后使用）

- 不加排除参数；构建时做边界审计，**检测到 blind/边界不一致即拒绝导出**；
- 上传后的 `release/` 与 GitHub Release 资产解压结果逐字节一致；`release/CHECKSUMS.sha256` 与
  `release/scripts/validate_public_release.py` 可直接在 `release/` 内使用。

### 2.2 安全子集模式（仅在上游修正前、且 owner 书面同意时使用）

~~~bash
python datasets/pol2/export_score_v2_hf.py build \
    --release-dir <仓库外>/POL2_GitHub_Release_v1 \
    --exclude-unassigned-pool --exclude-blind-samples \
    --out datasets/pol2/score-v2/hf-export --org NaturalDAO
~~~

- 排除上游 `data/pol2-specialist/score-v2-new-units/{kev,laya}.jsonl` 与 `manifests/score-v2-new-units.json`；
- 排除命中盲测行的样例文件（`samples/specialist-*.jsonl`），保留无盲样例与通用回放样例；
- 实测：**52 个文件 / 76.3 MiB / 45,686 数据行**（严格模式为 57 文件 / 82.7 MiB / 47,436 行）；两次构建树哈希一致，导出 JSONL 对未分配池行内容命中 0；
- `MANIFEST.json` 记录 `excluded_upstream_files` / `excluded_samples` / `boundary_audit`；数据卡 §10 会说明这是安全子集，
  **不是完整 Release 镜像**；`release/` 内上游 `CHECKSUMS`/验证器会对被排除文件报缺失（预期，不是损坏）。

## 3. 边界与红线

1. **不得**把 blind / sealed / fresh blind / 私有保留集的内容（含逐例 state、问题、label、id、预测）写入仓库、日志、截图、HF 或任何公开渠道；
2. 上传前必须跑 `build`（含边界审计）与 `verify`；不要手工往导出目录塞文件；
3. 若发现新的边界问题：立即停止上传/传播，按项目内部泄漏处置流程（维护者侧）记录并通知维护者（公开文档不粘贴逐例内容）；
4. token 只在 `hf auth login` 缓存；私有/受限材料使用仓库外 token 文件，不进入命令历史、仓库或日志；
5. HF 数据卡与 `MANIFEST.json` 的数字必须由生成器现算，不手工改；
6. 本数据集是研究预发布：`training_approved=false`、`expert_gold=false`，不是生产安全批准。

## 4. 常见失败处理

| 现象 | 处理 |
|---|---|
| `build` 报『unassigned 池含 fresh-blind 单元』 | 上游 Release 未修正：不要绕过；联系维护者修正 Release，或按 §2.2 在 owner 同意下走安全子集模式 |
| `verify` 报 sha/bytes 不匹配 | 生成物过期或混入手工文件：删除导出目录后重跑 `build`，不要手改 |
| 远程校验 sha 不匹配 | 上传不完整：重跑同一条 `hf upload`（幂等增量）；仍失败先查 revision |
| 上传被拒 401/403 | token 无 write 权限或仓库名不对；重新 `hf auth login` |
| HF viewer 报列类型错误 | 不要在一个 config 里混合 Laya/Kev 或不同列集合；按数据集卡配置使用 Laya 文件 |

## 5. 历史留档

- 2026-10-27：Release 资产本地留档与校验（`.agent/notes/2026-10-27-pol2-release-archive.md`，仓库外）；当时约定『不复制进仓库、不上传 HF』。
- 2026-11-02：owner 要求把 PoL2 专项数据集规范托管到 HF；本 session 完成导出/校验工具与边界审计，因 §1 问题暂停上传（本 HOLD）。

## 6. 更新记录

| 日期 | 事件 | revision / 备注 |
|---|---|---|
| 2026-11-02 | 创建 HF 仓库（public，空）；导出/校验工具与边界守卫就绪；**上传 HOLD** | 未上传；详见内部审计 |