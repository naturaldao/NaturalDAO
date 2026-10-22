# Hugging Face 托管手册（general 决策数据集 v5）

**状态：READY / NOT UPLOADED**（2026-10-22：本地导出与自检全部通过；尚未上传，当前环境没有 HF token，上传由维护者执行）。

本文件是**托管方案 + 操作手册**。数据实体不入库：仓库只保留数据卡、清单（`data/MANIFEST.json`）、
生成/校验脚本（`export_hf.py`）与本手册。上传前后的每一步都以本文件为准。

- 数据集版本：`general-decision-v0.5`
- 机器清单：`datasets/general/data/MANIFEST.json`（逐文件 sha256 / bytes / 行数 / 可见性 / 目标 HF 路径）
- 生成器：`datasets/general/export_hf.py`（纯标准库、离线、确定性）
- 数据卡：导出目录里的 `public/README.md`（由生成器产出，**不要手改**）

---

## 1. 托管方案（两个仓库，公开与私有物理分开）

| 用途 | 仓库 ID（org 可配置，默认 `naturaldao`） | 可见性 | 内容 | 状态 |
|---|---|---|---|---|
| 公开三区 + 旁挂件 | `naturaldao/pol-decision-general-v5` | public | train / validation / test、jev-probs、target-types、中文补充、数据卡、清单 | **READY / NOT UPLOADED** |
| 内部保留集 | `naturaldao/pol-decision-general-v5-holdout` | **private** | benchmark 私有包（benchmark.jsonl / .gz、包清单、数据卡、USAGE、verify.py） | **READY / NOT UPLOADED** |

org 用环境变量 `HF_ORG` 覆盖（默认 `naturaldao`）：

```
# bash
export HF_ORG=your-org
# PowerShell
$env:HF_ORG = "your-org"
```

导出脚本会把 org 写进两份发布清单的 `hf` 字段与数据卡里的 URL；换 org 后重跑 `build` 即可。

**红线**：公开仓库只放 `public/` 的内容；保留集只能进 `private-holdout/` 对应的私有仓库。
public 与 private-holdout 在磁盘上是两个独立目录（`datasets/general/data/hf-export/public/` 与
`datasets/general/data/hf-export/private-holdout/`），不混放、不互相引用文件。

## 2. 导出布局

`datasets/general/data/hf-export/`（gitignored，本机生成）：

```
hf-export/
  public/                        → 上传到公开仓库（repo 根 = public/ 的内容）
    README.md                    HF 数据卡（YAML front matter + 中文说明）
    MANIFEST.json                公开导出清单：7 个文件的 sha256/bytes/行数 + 计数 + 断言记录
    train.jsonl.gz               48,728 条（19.3 MB）
    validation.jsonl.gz          7,597 条（3.1 MB）
    test.jsonl.gz                15,194 条（6.2 MB）
    jev-probs.jsonl.gz           概率旁挂件 44,740 行（4.6 MB）
    target-types.jsonl.gz        target 形态/训练路由 74,853 行（834 KB）
    zh-supplement-items.jsonl.gz train-only 中文补充 3,148 条（936 KB，主数据 train 已含，供复算溯源）
  private-holdout/               → 上传到私有仓库（--private；repo 根 = private-holdout/ 的内容）
    benchmark.jsonl              6,541 条明文（包自校验用；加载用 .gz）
    benchmark.jsonl.gz           6,541 条 gzip（加载件）
    manifest.json                包格式清单（schema pol-internal-benchmark-package/0.1）
    README.md                    私有包数据卡（只有聚合统计）
    USAGE.md                     使用说明：红线、预测格式、指标口径、完整性校验
    verify.py                    包完整性校验（标准库、自包含；退出码 0=通过）
    HF-MANIFEST.json             HF 发布清单（本脚本生成；不覆盖包清单 manifest.json）
```

注意：Windows / macOS 默认文件系统大小写不敏感，`MANIFEST.json` 与包格式要求的 `manifest.json`
在同一个目录里会互相覆盖，因此私有包目录内 HF 发布清单命名为 `HF-MANIFEST.json`；包完整性清单仍是
`manifest.json`（字节与仓库内 `data/splits/benchmark-dataset/manifest.json` 一致，`verify.py` 读取它）。

## 3. 生成与校验（离线、确定性）

在仓库根目录（`PoL-Governance/`）执行：

```
# 一次跑完：仓库清单 + 两份导出 + 全量 sha256 复核 + 私有包 verify.py
uv run --no-project --offline python datasets/general/export_hf.py all

# 或分步
uv run --no-project --offline python datasets/general/export_hf.py inventory   # → data/MANIFEST.json
uv run --no-project --offline python datasets/general/export_hf.py build       # → data/hf-export/
uv run --no-project --offline python datasets/general/export_hf.py verify --run-package-verify

# 校验任意一份下载副本（目录里要有 MANIFEST.json 或 HF-MANIFEST.json）
uv run --no-project --offline python datasets/general/export_hf.py verify --dir <下载目录>
```

确定性验收（本次已执行）：

- 连续两次 `build` 输出逐字节相同；`all` 打印的树哈希：
  - public `9b963b6c20526c20fbe3c520337d5e232b20eaef327d5248251eae4f039fb4fe`
  - private-holdout `4d6b4c4042fe7172b1f8a24903996c4bd9d4bb420d7d3a0d1ff5608121dd4d8e`
- 公开面断言：读 benchmark 全量 6,541 个成员 id，公开导出 71,519 个条目零命中（命中即非零退出）。
- 私有包 `verify.py` 在导出目录内退出码 0（sha256、条数与分布、无裸分隔符、未被 git 跟踪）。

导出脚本不联网、不调用 HF；`all` 也不会修改数据实体。

## 4. 上传（维护者执行，按顺序）

前置：有 `naturaldao` org（或 `HF_ORG` 指定的 org）的写权限；HF token 具 write scope；
本机数据目录已按 §3 生成并通过验收。

```
# 1) 安装带 hf_transfer 的客户端（一次性）
pip install -U "huggingface_hub[hf_transfer]"

# 2) 登录（把 token 存到本机 HF 缓存；不要提交、不要写进日志）
hf auth login

# 3) 建仓库（公开 + 私有；已存在可跳过或加 --exist-ok）
hf repo create <org>/pol-decision-general-v5 --repo-type dataset
hf repo create <org>/pol-decision-general-v5-holdout --repo-type dataset --private

# 4) 上传公开仓库（repo 根 = public/ 的内容；README.md 自动成为数据卡）
HF_HUB_ENABLE_HF_TRANSFER=1 hf upload <org>/pol-decision-general-v5 \
  datasets/general/data/hf-export/public . --repo-type dataset

# 5) 上传私有保留集（必须 --private；不要放进公开仓库）
HF_HUB_ENABLE_HF_TRANSFER=1 hf upload <org>/pol-decision-general-v5-holdout \
  datasets/general/data/hf-export/private-holdout . --repo-type dataset --private
```

Windows PowerShell 的等价写法（环境变量单独设置，命令单行）：

```
$env:HF_HUB_ENABLE_HF_TRANSFER = "1"
pip install -U "huggingface_hub[hf_transfer]"
hf auth login
hf repo create <org>/pol-decision-general-v5 --repo-type dataset
hf repo create <org>/pol-decision-general-v5-holdout --repo-type dataset --private
hf upload <org>/pol-decision-general-v5 datasets/general/data/hf-export/public . --repo-type dataset
hf upload <org>/pol-decision-general-v5-holdout datasets/general/data/hf-export/private-holdout . --repo-type dataset --private
```

上传后**立刻记下两个仓库的 commit sha**（下一步固定 revision 用）：

```
python -c "from huggingface_hub import HfApi; api=HfApi(); print('public', api.repo_info('<org>/pol-decision-general-v5', repo_type='dataset').sha); print('holdout', api.repo_info('<org>/pol-decision-general-v5-holdout', repo_type='dataset').sha)"
```

也可以从上传输出 / 网页 commit 历史里取 sha。**固定 revision** 的三处：

1. 回填 `datasets/registry.json` 里 `general-decision-v0.5` 的 `hf_public_revision` / `hf_holdout_revision`，
   并把 `hf_status` 改为 `uploaded`；
2. 更新本文件 §9 更新记录（日期 / revision / 谁上传）；
3. 引用数据时用 commit sha（HF 页面或 `--revision`），不要只写 `main`。

## 5. 上传后校验（下载回来逐文件比对 sha256）

```
# 公开仓库：固定 revision 下载到临时目录
hf download <org>/pol-decision-general-v5 --repo-type dataset --revision <public-sha> --local-dir /tmp/pol-public
uv run --no-project --offline python datasets/general/export_hf.py verify --dir /tmp/pol-public

# 私有保留集：同样固定 revision；包内 verify.py 自校验
hf download <org>/pol-decision-general-v5-holdout --repo-type dataset --revision <holdout-sha> --local-dir /tmp/pol-holdout
uv run --no-project --offline python datasets/general/export_hf.py verify --dir /tmp/pol-holdout
python /tmp/pol-holdout/verify.py
```

手工比对也行（与 `MANIFEST.json` / `HF-MANIFEST.json` 里的 sha256 对照）：

```
# Linux
sha256sum train.jsonl.gz
# Windows PowerShell
Get-FileHash ./train.jsonl.gz -Algorithm SHA256
```

校验通过后才算 UPLOADED；任何 sha256 不一致都按"重新下载 → 重新上传该文件"处理，不要静默接受。

## 6. 谁上传、何时上传、权限与访问控制

- **谁上传**：项目维护者（持有 HF 账号与 org 写权限的人）。本仓库的 Agent 不带 token、不做上传；
  上传是人工动作，凭据只留在上传者本机（`hf auth login` 的缓存）。
- **何时上传**：本任务验收通过、PR 合并之后；或用户明确指示时。上传前先跑 §3 的 `all` 并确认
  `status=pass`。数据或生成器有任何改动后要**重新导出、重新上传并更新 revision**。
- **私有仓库访问控制**：
  - 保留集仓库创建为 private，只邀请模型训练/独立评测的必要成员；
  - 上传 token 用最小权限（write 仅在上传时使用）；评测侧用 read token，放在隔离环境；
  - 保留集**不进入**训练环境、训练 Agent 上下文、公开日志、截图、CI 缓存或公开 fork；
  - 独立评测在禁网、只导出汇总结果的环境里跑；不根据逐例答案反复调模型（需要新一轮比较时换新场景）。
- **公开仓库**：无额外限制；但 public 里不得出现保留集的成员 id / state 正文。发布脚本已内置零命中断言，
  不要绕过脚本手工把其它文件塞进 public 目录。

## 7. 仓库瘦身：由 Lead 执行的 `git rm --cached` 清单

原则：数据实体不入库，仓库只留数据卡、清单、脚本与小体积复算锚点。`git rm --cached` 只改索引，
**不删除本机文件**；导出脚本从本机文件继续工作。

### 7.1 本次立即离仓（>1 MB，或按要求必须离仓）

| 文件（仓库路径） | bytes | sha256（前 16 位） | 离仓去向 / 替代链接 |
|---|---:|---|---|
| `datasets/general/data/splits/train.jsonl.gz` | 19,323,363 | `3ed3235133615616` | HF 公开 `train.jsonl.gz`；哈希见 `data/MANIFEST.json` |
| `datasets/general/data/splits/test.jsonl.gz` | 6,184,345 | `8eaf7e05cf8987f0` | HF 公开 `test.jsonl.gz` |
| `datasets/general/data/splits/validation.jsonl.gz` | 3,116,798 | `23ea40db848cb7f5` | HF 公开 `validation.jsonl.gz` |
| `datasets/general/data/jev-probs.jsonl.gz` | 4,583,256 | `3365cffe02a37b95` | HF 公开 `jev-probs.jsonl.gz` |
| `datasets/general/data/target-types.jsonl.gz` | 834,743 | `19f63155c60ffb9d` | HF 公开 `target-types.jsonl.gz` |
| `datasets/general/data/zh-supplement/items.jsonl` | 8,664,627 | `F2D87C3893D2E138` | 明文派生件离仓；HF 公开 `zh-supplement-items.jsonl.gz`（同内容压缩） |

建议命令（在 git 仓库根执行——即包含 `PoL-Governance/` 的目录；下面路径前缀按实际 git 根调整）：

```
git rm --cached -- \
  PoL-Governance/datasets/general/data/splits/train.jsonl.gz \
  PoL-Governance/datasets/general/data/splits/test.jsonl.gz \
  PoL-Governance/datasets/general/data/splits/validation.jsonl.gz \
  PoL-Governance/datasets/general/data/jev-probs.jsonl.gz \
  PoL-Governance/datasets/general/data/target-types.jsonl.gz \
  PoL-Governance/datasets/general/data/zh-supplement/items.jsonl
```

### 7.2 保留 tracked（本次不动）

| 文件 | bytes | 说明 |
|---|---:|---|
| `datasets/general/data/zh-supplement/items.jsonl.gz` | 936,028 | < 1 MB；HF 公开仓库有同字节副本，仓库留作离线复算锚点（readme_stats 的补充集口径） |
| `datasets/general/data/MANIFEST.json` | 见 git | 数据清单（新增，本任务产出） |
| `datasets/general/data/splits/split-manifest.json` | 8,713 | 切分清单：盐指纹、分区哈希、轮换记录 |
| `datasets/general/data/items.*.report.json`、`items.native.manifest.json`、`convert-report.json`、`slim-report.json`、`data/jev/*.json`、`data/zh-supplement/{manifest,stats}.json` | 小 | 构建/统计报告与清单，可复算、小而重要 |
| `datasets/general/data/splits/{build_corpus,split,package_benchmark,verify_benchmark_package}.py` | 小 | 切分/打包/校验脚本 |
| `datasets/general/HF.md`、`export_hf.py`、README/INDEX/TRAINING/CONTRACT 等文档 | 小 | 托管手册、生成器与文档 |

**benchmark 相关**（`data/splits/benchmark*.jsonl*`、`data/splits/benchmark-dataset/`）目前本来就不被
git 跟踪（`.gitignore` 的 `datasets/general/data/splits/benchmark*`），**不需要 `git rm --cached`**；
只需确认它们没被误加。私有包上传源就是 `data/splits/benchmark-dataset/` 的副本。

### 7.3 `.gitignore`：现有规则确认

`datasets/general/data/**/*.gz` 对 `data/` 下的大文件**足够**：train/test/validation/jev-probs/
target-types/zh-supplement 的 `.gz` 都会命中（`data/splits/benchmark*`、`**/*.jsonl` 也已有规则）。
hf-export 是整目录生成物，需要单独的目录规则，否则其中 `README.md`、`MANIFEST.json`、
`HF-MANIFEST.json`、`USAGE.md`、`verify.py`、`manifest.json` 会漏网。Lead 已追加
（`.gitignore` 第 36 行），内容应为：

```
datasets/general/data/hf-export/
```

验证方法（当前 `data/MANIFEST.json` 的 `gitignore_evidence` 已记录：上述路径全部命中
`datasets/general/data/hf-export/` 规则，而 `data/MANIFEST.json` 自身不被忽略）：

```
git -C <仓库根> check-ignore --no-index -v -- \
  PoL-Governance/datasets/general/data/hf-export/public/README.md \
  PoL-Governance/datasets/general/data/hf-export/private-holdout/verify.py
# 或看清单里的机器可读旁证（重跑 inventory 会刷新）
uv run --no-project --offline python datasets/general/export_hf.py inventory
```

> 已完成 `git rm --cached` 与 .gitignore 追加后，请重跑一次 `inventory`（会刷新 `data/MANIFEST.json` 里
> 每个文件的 `tracked` 与 `gitignore_evidence` 字段），再提交 `MANIFEST.json` 的最新版本。

### 7.4 本轮链接改动清单（改前 → 改后）

原则：tracked 文档里不再直接链到「将离仓的大文件」；改为指向 [HF.md](HF.md)（托管/下载/上传手册）
或 [data/MANIFEST.json](data/MANIFEST.json)（逐文件 sha256 / bytes / 行数 / 可见性）。

| 文件 | 改前 | 改后 |
|---|---|---|
| README.md（速览后） | 无托管说明 | 新增一段：数据实体托管 HF、链 [HF.md](HF.md) / [data/MANIFEST.json](data/MANIFEST.json) |
| README.md §4.4 | [data/jev-probs.jsonl.gz](data/jev-probs.jsonl.gz) | `data/jev-probs.jsonl.gz`（HF 托管，见 HF.md） |
| README.md §4.4 / §5.4 | [data/target-types.jsonl.gz](data/target-types.jsonl.gz)（2 处） | `data/target-types.jsonl.gz` / “target-types（HF 托管，见 HF.md）” |
| README.md §5.1 文件表 | [data/splits/train.jsonl](data/splits/train.jsonl)（[.gz](data/splits/train.jsonl.gz)）等 6 条大文件链接 | 文件名 + “HF 公开仓库”标注；另加清单/HF.md 指针与 `zh-supplement-items.jsonl.gz` 行 |
| README.md §5.3 / §6 | 按“仓库内文件”读/复算 | 先按 HF.md 下载解压再读；输入改为“本地 data/（从 HF 恢复）” |
| TRAINING.md 头部 / §1.1 | [target-types.jsonl.gz](data/target-types.jsonl.gz)（2 处） | `target-types.jsonl.gz` + HF.md |
| TRAINING.md §8 附 | [jev-probs.jsonl.gz](data/jev-probs.jsonl.gz) | `jev-probs.jsonl.gz`（HF 托管，见 HF.md） |
| TRAINING.md §1.1 / §8 | “入库的 .gz / 干净检出上读得到” | “由 HF 托管；从 HF 下载三个分区 .jsonl.gz 并解压后读得到” |
| CONTRACT.md §2 | data/items.native.jsonl.gz（已移出版本控制） | data/items.final.jsonl + data/items.native.jsonl（大文件不入库，链 data/MANIFEST.json） |
| jev-validation.md §8.4 / 附录 | “入库的旁挂件只保留公开面” / “明文被 .gitignore 挡住” | “发布的旁挂件只保留公开面” / “HF 公开仓库托管（见 HF.md）” |
| target-provenance.md §0 | data/target-types.jsonl.gz（只含公开分区） | 追加“文件由 HF 托管，见 HF.md” |
| INDEX.md | @B@readme_stats.py@{BT}--check` 可复算（实际无 --check） | 删除不存在的断言；新增 export_hf.py / 数据托管行、§5 表补 MANIFEST 与 hf-export 行 |
| archive/2026-10-06-coverage-gaps.md | `data/items.final.jsonl`（该文件从未 tracked，原链接在干净检出中失效） | 改为对 [data/MANIFEST.json](data/MANIFEST.json) 的哈希引用 |

> 说明：archive/ 是历史报告（明确标“数字已过时”），只修失效链接与明显失真的“入库”表述，不改历史数字。

## 8. 保密与访问边界（摘要）

- 保留集**只防随手复现**：切分用仓外私盐，防止"公开脚本 + 公开种子"重建；不是密码学边界。
- 保留集不进入任何公开分支、fork、PR、日志、截图、训练 Agent 上下文；成员身份（id 名单）本身就是敏感信息。
- 公开导出已内置 benchmark 成员 id 零命中断言；不要绕过导出脚本手工往 public 目录塞文件。
- 概率旁挂件是**一致子集偏差**（只保留模型判定与语料答案一致的目标），可公开，但不能当无偏概率或校准参照。
- 上传凭据（HF token）只留在上传者本机，不进仓库、不进日志、不写进任何文档。

## 9. 更新记录

| 日期 | 版本 | 状态 | 变更 |
|---|---|---|---|
| 2026-10-22 | v0.5 | READY / NOT UPLOADED | 建立 HF 导出（public 7 文件 / private-holdout 6 文件）、仓库清单 `data/MANIFEST.json` 与托管手册；两次构建树哈希一致；公开面 benchmark id 零命中；私有包 verify.py 通过；尚未上传 |
