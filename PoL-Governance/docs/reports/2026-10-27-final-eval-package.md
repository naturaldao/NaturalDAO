# 阶段报告：最终评测包与结果卡（Session B，2026-10-27）

> 范围：阶段三「校准盲测」的**执行准备**。本报告不含私有保留集的任何内容、逐例结果或可反推 id；保留集评测本轮**未执行**。
> 数据边界与协议见 [datasets/README](../../datasets/README.md)、[finetune/EVAL-PROTOCOL](../../finetune/EVAL-PROTOCOL.md)；执行方式见内部任务书 Task Book §5（`.agent/prompts/SESSION-B-final-eval.md`，不进公开仓库）。

## 1 目标与判断

**任务**（Session B）：在私有保留集（6,541 条）上按预注册协议完成 base vs 微调后的最终评测，只发布聚合结果。

**本轮判断**：目标仍然成立，但**主结论的前置条件不在本 session 手上**——①owner 未定执行方式（独立评测者 / 授权隔离执行）；②GPU 暂停（adapter lm-eval、温度拟合、延迟实测做不了）；③逐行预测未留档（配对 CI 需重跑）。

因此本轮把目标压缩成**可交付的最大闭环**：让第三方能在自己的隔离环境里、用一条条可复制的命令跑完评测，并且只带回一个被审计过的聚合 JSON；同时把现有可诚实报告的数字规范化进结果卡。这样 owner 一授权即可开跑，不需要再写代码。

## 2 交付物

| 交付 | 路径 | 状态 |
|---|---|---|
| 评测结果卡 | [results/MODEL-02-final-eval/CARD.md](../../results/MODEL-02-final-eval/CARD.md) | 完成（含未测项与门禁） |
| 版本清单（base rev / adapter sha / 视图 sha / holdout rev） | [results/MODEL-02-final-eval/versions.json](../../results/MODEL-02-final-eval/versions.json) | 完成（视图 sha 已复算一致） |
| 评测包（可交独立评测者） | [results/MODEL-02-final-eval/eval-package/](../../results/MODEL-02-final-eval/eval-package/README.md) | 完成（MANIFEST + CHECKSUMS + 手册） |
| 聚合脚本（隔离环境内） | [finetune/final_eval_aggregate.py](../../finetune/final_eval_aggregate.py) | 完成（配对 item + group-cluster bootstrap、校准分箱、覆盖率口径） |
| 导出前检查器（唯一出口） | [finetune/check_aggregate_export.py](../../finetune/check_aggregate_export.py) | 完成（结构白名单 / 禁键 / 数值自洽 / 文本扫描） |
| 延迟基准（成本） | [finetune/bench_latency.py](../../finetune/bench_latency.py) | 完成（CPU 可跑；GPU 实测待启用） |
| 打包器（可复现包 + 漂移检查） | [finetune/prepare_eval_package.py](../../finetune/prepare_eval_package.py) | 完成（`--check` 作为集成门禁） |
| 公开 test 回归汇总（脚本生成） | [results/MODEL-02-final-eval/public-test-regression.md](../../results/MODEL-02-final-eval/public-test-regression.md) | 完成（0.5047→0.7785 逐位一致） |

### 2.1 独立审计与修复（本轮实际发生的最有价值的一步）

交付后由独立审计子任务（对抗性审阅）做了 6 项检查，发现 **1 个必须修 + 5 个建议修**，全部已处理：

1. **导出闸门「假拒」bug（必须修）**：`paired.delta` 与两个 `accuracy` 各自 round6 后相减会差 1e-6，而 checker 用 1e-6 容差比较，导致**合法聚合结果被唯一出口拒绝**。已改用派生量容差 3e-6，并加入真实数字（7859/12124/15573）的回归测试；
2. `paired.seed` 无上下界 → 已限制 0..2^63-1；
3. 模型标签是自由安全 token → 已强制 `[A-Za-z0-9._-]{1,24}`（与聚合脚本一致，堵住用标签藏长标识符）；
4. `coverage.skipped` 的键可藏 rid（如 `db-bigbench-00183cfc#formal_fallacies` 恰好是合法"安全标识符"）→ 已改为只允许 15 个已知跳过原因，聚合脚本与检查器同枚举、各加回归测试；
5. 交付脚本里残留本机示例路径（`D:/pol2-train/...`）→ 全部改为通用占位；
6. 主 CI 作用域（配对交集 vs 固定分母）→ 已在结果卡披露（v3 ITT 模式标为 deferred）。

审计还确认：聚合公式（Wilson/kish/reliability/ECE/gap）手算复核正确；数据边界干净；包完整性（CHECKSUMS 13/13、`--check` pass、package_sha256 重算一致）通过；协议一致性 PASS。

### 2.2 验证证据（本轮实际跑过）

- `prepare_eval_package.py --check` → `{"status":"pass","files":12}`；包内 `sha256sum -c CHECKSUMS.sha256` → 13/13 OK；
- **CPU 端到端冒烟**（公开 validation 前 48 行 + 9.8M 随机 tiny Qwen3 与其 LoRA；无 GPU、无私有数据）：base/tuned 各评测 35 行（13 行 >26 选项按协议跳过）→ 聚合（fit 温度路径、`--cluster-rounds 1000`）→ 导出检查器 pass（1012 项检查）→ 延迟基准产出 `pol-latency-bench-v1`（batch 1/4）；导出文件中不存在任何视图 rid 或 prompt 片段；
- 公开视图 sha256 全部与 manifest 复算一致；公开 test 回归表由 `finetune/collect_results.py` 从仓库外评测 JSON 重新生成，与历史结果逐位一致。

## 3 得到确认的既有数字（口径 sanity check）

- **public test（15,573 行，只做回归）**：base 0-shot **0.5047** → adapter **0.7785（+27.4 pt）**；与 Track A 结果卡逐位一致；跳过 >26 选项 656 行、超长 prompt 77 行，两侧同口径。
- **validation（7,887 行）**：0.5127 → 0.7883（+27.6 pt）。
- **lm-eval base**：ceval-valid 0.5847 / cmmlu 0.5624 / mmlu 0.5765 / agieval 0.4133，均值 **0.5342**（201 子任务 + 4 组聚合，limit 100）；adapter 侧**未测**（2026-10-23 崩溃中断）。
- **视图 sha256 复算**：train/test/validation 三个视图与各自 manifest 完全一致（`a136c2a1…` / `2235f0b7…` / `b936c618…`）。

## 4 统计口径：本轮最重要的设计决定

独立统计审查（内部笔记 `.agent/notes/2026-10-27-expert-answer-final-eval-stats.md`）给出三条结论，已写进聚合脚本与结果卡：

1. **配对 group-cluster bootstrap 为主区间**：簇 = rid 的 `#` 前缀（同族/同来源单位），10,000 次重采样，Δ 按行加权；报告簇数、簇大小分布、Kish n_eff 与 reliability（≥50 ok / 30–49 cautious / <30 low）。item-level bootstrap 只作近似——用它替代会把 CI 报窄。
2. **预注册判据不事后更改**：仍是「两独立 95% CI 不重叠」；配对 Δ CI 不含 0 但独立 CI 重叠时，只能写「配对分析显示正向差异；预注册门槛未满足」。
3. **失败/缺失口径**：主口径固定分母、失败记错误；同时披露完成率；双方完成子集只作敏感性分析。MDE 在 n=6,541 下约 **2.0–2.5 pt**（α=0.05、power=0.8，双比例保守上界）——不能把 6,541 当独立样本保证检出 +5 pt。

## 4.1 导出通道加固（本轮发现并修复）

导出检查器第一版允许 `coverage.skipped` 的键是任意"安全标识符"——而一条 rid（如 `db-bigbench-00183cfc#formal_fallacies`）恰好符合该正则，可以被伪装成"跳过原因"键随聚合文件带出隔离环境。已修：**skipped 的键只允许 15 个已知原因**（聚合脚本与检查器两侧同一枚举，未知键 fail-closed），并各自加回归测试。这类"聚合文件里能藏一整个标识符"的问题，是只导出汇总时最容易被忽略的泄漏面。

## 5 数据边界执行情况

- 未读取、未复制、未运行私有保留集（`items`/`benchmark`）任何内容；评测包内不含私有数据，只含脚本、MANIFEST/CHECKSUMS 与手工手册；
- 结果卡与报告只出现公开三区的数字与本轮交付物；保留集仅登记「版本 + 规模 + revision」；
- 评测者的唯一出口是 `check_aggregate_export.py`（结构白名单、禁键、数值自洽、体积/文本扫描）；未通过不得带出隔离环境。

## 6 未测与门禁（不填 0）

| # | 项 | 门禁 |
|---|---|---|
| 1 | 私有保留集 base vs adapter | owner 定执行方式 + 独立评测者按包执行 |
| 2 | 温度拟合（validation B 半）与保留集 apply | adapter 逐行预测（GPU，~5–10 分钟） |
| 3 | adapter lm-eval 四任务 | GPU 恢复 + 硬件确认 |
| 4 | 成对 CI / 多 seed | 逐行预测 + 预注册 seed 重训 |
| 5 | 正式延迟（p50/p95、batch=1/16、峰值显存） | GPU + `bench_latency.py` |
| 6 | 保留集分层指标 | 随 #1 产出 |

## 7 失败与教训

- **评测不能只写「怎么跑」**：没有聚合脚本 + 导出闸门时，第三方评测只能回传逐例预测或不可审计的口头结论；本轮把「隔离环境内聚合」做成代码，是让最终评测真正可执行的关键。
- **统计口径要在跑之前定**：item-level CI 会低估、独立 CI 与配对检验不等价——这两条如果等结果出来再讨论，就等于事后挑判据。已在跑之前写进协议与脚本。
- **文档要写「还没发生的事」**：评测手册里温度值、延迟数字、adapter lm-eval 都必须写成「待冻结/待测」，不能先填一个占位数字。
- **并行实现的接口必须先冻结**：本轮先写接口契约（`.agent/notes/2026-10-27-final-eval-package-spec.md`）再并行实现，5 个子任务的文件边界与 CLI 未冲突；唯一冲突（invalid 行口径）在联调时由 Lead 裁决为「一律 fail-closed」。
- **GPU 暂停期间仍能推进阶段三**：评测执行链、统计口径、版本清单、结果卡、公开回归复算全部可在 CPU 侧完成；只有「跑数」必须等 GPU/授权。

## 8 下一步（授权后的最短路径）

1. owner 选执行方式；若方式 2，则按包内手册在隔离环境执行（预计 GPU 上 30–60 分钟：视图构建 + 两次推理 + 聚合 + 检查）；
2. GPU 恢复后先补 adapter lm-eval（~30–60 分钟）与 validation 逐行预测（拟合温度，冻结进包）；
3. 跑保留集 → 带回 `aggregate.json` → 填 CARD §1/§2/§6 与 ROADMAP E3-3/4/5/6；
4. 多 seed（20261024/25）与 Track B 仍待 GPU 排期。

## 9 复算入口

```bash
python -m unittest finetune.test_final_eval_aggregate finetune.test_check_aggregate_export \
  finetune.test_bench_latency finetune.test_prepare_eval_package -q   # 纯 CPU 单测
python finetune/prepare_eval_package.py --versions results/MODEL-02-final-eval/versions.json \
  --out results/MODEL-02-final-eval/eval-package --check                 # 评测包漂移检查
cd results/MODEL-02-final-eval/eval-package && sha256sum -c CHECKSUMS.sha256
```
