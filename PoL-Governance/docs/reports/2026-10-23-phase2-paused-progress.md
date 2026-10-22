# 阶段报告：第二阶段暂停期进展（2026-10-23）

> 一句话：GPU 实验按 owner 要求暂停；暂停期完成**评测/校准/多 seed/评测器集成/数据适配/混合视图与一键恢复链**，
> Track A 基线结论不变；**没有新增 GPU 结果**。

## 1. 数据与托管状态

- **通用数据集 v5**：Hugging Face 导出离线复检通过——公开三区 7 个文件、私有保留集 6 个文件、包自校验结果 0；
  状态仍为 **READY / NOT UPLOADED**（本机无 token，上传由维护者执行；见 [HF.md](../../datasets/general/HF.md)）。
- **专用冻结集 POL2-accepted-8705-v1**：pv-1 视图适配器就绪（schema 层，[POL2-VIEW.md](../../datasets/pol2/POL2-VIEW.md)）：
  - 当前 training_approved=false，唯一允许 --schema-preview（只打印 schema/stats，不写文件）；
  - 写仓库外视图的 build 在授权前一律 exit 2；blind_test/private_holdout 内容不进入任何输出；
  - 真实 train preview 实测 5,900 行（choice 5,361 / score 539、skipped=0），两次输出逐字节一致。
- 仓库 main 新增同仓库项目 POL2-Steward（仓库根目录的新项目）（Agent-neutral 治理服务，developer preview）；
  我们的任务分支已合入最新 main。PR #44/#45 已由维护者关闭，**集成方式待确认**，分支保持可用。

## 2. 评测与校准（预注册）

- [EVAL-PROTOCOL](../../finetune/EVAL-PROTOCOL.md)：数据划分、指标（决策/校准/通用能力/成本）、预注册阈值、
  统计规则（2–3 seed、配对 bootstrap、CI 口径）、报告模板。
- **温度校准** finetune/calibrate.py：validation 按 sha256(rid) 固定切半（calibration 拟合 / selection 复算），
  输出 NLL / Brier / ECE / MCE；7 个 CPU 测试。
- **统一汇总** finetune/collect_results.py：分层表、base↔tuned 差值、配对 bootstrap 95% CI、
  多 seed 均值 ± CI、lm-eval 输出目录解析；12 个 CPU 测试。
- **Track B 独立评测** finetune/eval_decision_scorer.py：adapter + scorer_head 独立评测，与 Track A 同键名 JSON，
  可导出逐行概率给校准；31 个 CPU 测试 + 真实底座/adapter CPU 冒烟通过。
- **通用能力代理**：lm-eval 0.4.13，ceval/cmmlu/mmlu/agieval 四任务可用（cmmlu 需 datasets<4 + --trust_remote_code）；
  真实 Qwen3-1.7B + Track A adapter 在 CPU 上小样本冒烟通过。

## 3. 数据适配与混合视图

- **mix-1 混合视图** datasets/general/build_mixed_view.py：通用视图 × 专用视图按 9:1 / 8:2 混合；
  真实数据冒烟：general train 51,947 + validation 8,177、ratio 0.05 → 54,681 行（实际 0.049999），
  两次输出逐字节一致；输出带 manifest（输入/输出 sha、实际比例）；POL2 行需显式 --allow-pol2。
- **一键恢复链** finetune/run_plan.py：8 个阶段（env-check / base-test / lm-eval / calibrate /
  track-b-smoke / track-b-full / seeds / pol2-mix），生成脚本通过 bash -n。

## 4. 当前限制（引用时不要弱化）

- 暂停期**没有新的 GPU 结果**；Track A 数字仍为单 seed：validation 0-shot 0.5127 → adapter 0.7883，test adapter 0.7785。
- **Track B 尚未真实训练**；PoL2 未批准训练；HF 未上传；PR 集成方式未定。
- **zh 子集存在位置先验天花板**（0-shot 已 0.944），不能当中文能力证据；>26 选项题未训练；
  通用能力代理与校准的正式数字待 GPU 恢复后产出。

## 5. 恢复后的执行顺序

1. test 的 base 0-shot 对照（补 Track A test 差值）
2. lm-eval base vs adapter（ceval/cmmlu/mmlu/agieval，limit 100）
3. 校准（validation 半 B 拟合温度 → 半 A / test 复算）
4. Track B 全量训练 + 独立评测
5. 多 seed 复现（20261023/24/25）与选项顺序消融
6. PoL2 混合（pol2-mix，需 owner 授权后）

## 6. 需要 owner 决定/开启

GPU 恢复时间；PR 集成方式（#44/#45 已关闭）；HF 上传；PoL2 训练授权；底座档位（1.7B→4B）；评测阈值确认。

## 7. 补充（至 Round 10：文档与校验工具）

- **HF 上传后远程校验** `datasets/general/verify_hf_remote.py`：上传后无需全量下载即可比对远端文件树与本地 MANIFEST
  （LFS sha256/bytes、非 LFS 小文件下载复算、缺失/多余/401 处理、私有仓库 token 文件）；10 个 CPU 测试；
  HF 状态复核：`naturaldao` 公开数据集列表为空、目标仓库 401 → 仍为 **READY / NOT UPLOADED**。
- **PoL2 训练授权前置清单** `datasets/pol2/APPROVAL-CHECKLIST.md`：owner 确认项、解禁步骤、训练前验收、报告要求、回滚与批准记录；
  未执行任何解禁步骤。
- **P8 补源筛选**（内部研究）：14 个候选 + 不可用清单；Top3 = MedMCQA / SHPDRG（有条件）/ e-CARE，预算测算可把世界知识 1.74%→~5.5%、因果 0.83%→~2.3%；
  政策问题（学术基准 train 划分、SHPDRG 许可）待 owner 书面意见。
- **文档**：阶段报告索引 `docs/reports/README.md`；Track B 结果卡必填项；内部目标评估（核心交付达成，HF 执行与下一阶段 GPU 工作待 owner）。
- **周期性复检**：视图 sha256（train/val/test）、HF 导出离线 verify、POL2 freeze 17 项检查均通过。
- **端到端 CPU 冒烟（Round 11，无 GPU）**：
  - 校准链路：真实 adapter 在 validation 前 120 行（device=cpu）导出逐行候选概率 → calibration 半区拟合温度 → selection 半区复算（NLL/Brier/ECE/MCE），全链路跑通（仅管线验证，样本太小不作结论）；
  - 通用能力链路：ceval-valid / cmmlu / mmlu / agieval 四任务家族在 CPU 上以真实 Qwen3-1.7B 各 limit=1 端到端跑通（含 cmmlu 的 datasets<4 + trust_remote_code 路径）；此前 datasets 5.x 预取缓存与 3.6 编码不兼容的问题已定位并清理缓存解决。
- 本轮仍**无新增 GPU 结果**；GPU 暂停令继续生效。
