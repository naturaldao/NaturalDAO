# 阶段报告：协作者更新合并（2026-10-26）

> 一句话：main 前进 45 个提交，新增 POL2 score-v2 数据/模型、具身推理（EVAL-02）、完整理论内在化先导（EVAL-03）、
> Kev-4B pointer-head 模型与评测结果；本阶段分支已合并 main（唯一冲突 datasets/registry.json 已合并解决），
> 并把 check.py 的链接策略放宽到「仓库内跨项目链接」（11 处 Research/ 链接）。**本轮没有新的 GPU 训练。**

## 1. 合并范围

- 合并提交：01ff530（Merge origin/main），分支 pol/MODEL-02/wenbo；合并后 check.py 修复提交 9fc0a4b。
- main 相对上一合并点（e79e93f）共 **45 个提交**；PoL-Governance 下 **232 个文件**变化（约 1.37M 行新增，主要是基准资产与结果 JSON）。
- 冲突：仅 datasets/registry.json（我们的 general v5 HF 字段 vs 协作者新增 pol2-score-v2 条目）——合并保留两边内容并校验 JSON。
- 校验：check.py pass（596 项目内链接 + 11 仓库内链接）；datasets suite 等测试 OK。

## 2. 新增的协作工作线

### 2.1 EVAL-02：PoL2 × 类型决策模型具身任务验证（benchmark/embodied_reasoning/）

- 文本配对先导：16 条自建合成案例 / 8 个配对族；Ollama qwen2.5:7b 与 llama3.1:8b；generic vs PoL2 两条件。
- 三条件长度匹配筛查：generic / 中性 / PoL2 输入 token 逐条相等（16/16）；三组动作正确均为 13/16；
  中性与 PoL2 在 4/16 案例动作不同（2 例由错转对、2 例由对转错），**净变化为零**。
- Kev-0.8B typed choice + 授权门 + VirtualHome 符号闭环：PoL2 提示降低非法授权状态的 P(deliver)（0.2310→0.0595），
  但也把部分合法任务从执行变成等待（未完成）；确定性门能在执行前阻断非法动作；MuJoCo 单任务 n=1 先导。
- 边界（作者自述）：探索性、非正式基准、无统计效能、无相机感知/真机/AGIBOT 复现；不能证明 PoL2 普遍改善推理。

### 2.2 EVAL-03：完整 PoL2 理论内在化验证先导（benchmark/pol2/）

- 清点 114 个来源条目（26 概念 / 21 关系 / 5 命题 / 16 爱语 / 28 治理规则 / 18 解释）；
- love2 单条目先导：6 例生成、双模型盲裁定 36/36 标签一致，但严格质量门 **0/6** 通过 → 按规则停止训练；
- 交付的是可复现的可行性先导 + 阴性质量门结果，**不是内在化验证**，没有模型训练或得分。

### 2.3 DATA-02 / MODEL-02：POL2 score-v2 数据与 Kev-4B 模型（外部 Release）

- 数据 pol2-score-v2 v1.0.0-rc1：Laya/Kev 训练导出（train-M0 各 6,166；validation 1,162；calibration 1,051；score-dev 354；新增 score 875），
  MRI 通用回放 M10/M25/M40；完整数据在 GitHub Release，不在 Git 历史；非专家金标，sealed blind 不在包内。
- 模型 kev-4b-pol2-score-v2-m10：底座 Qwen3.5-4B-Base@1001bb4d，LoRA + pointer head，1 epoch；三个 seed（17/29/43）；
  development/fresh-blind 双门：17 FAIL/PASS、29 PASS/FAIL、43 PASS/PASS（**seed43 为看到全部结果后选出的唯一双门版本**，须保留披露）；
  三 seed blind 平均准确率均 58.71%，作者明确**不能宣称平均提升**；结果为研究预发布，不是生产认证。

## 3. 与本项目主线的关系

- 我们的决策模型线（MODEL-02：Qwen3-1.7B + 字母 SFT，validation 0-shot 0.5127→0.7883）与协作者线（Kev-4B + pointer head）**是两条并行路线**，
  数据（general v5 vs pol2-score-v2）、模型规模、评测口径不同，**不能混表比较**；
- 两条线都受同一数据边界约束：POL2 冻结内容不得进公开仓库、私有保留集不外传、训练授权前零梯度；
- EVAL-02/EVAL-03 的结果可作为阶段三/四的端到端评测与集成参考，但不能替代我们的封闭选择评测协议。

## 4. 限制（引用时不要弱化）

- 协作者结果均为**探索性/研究预发布**：小样本、无统计效能、部分为单 seed 或事后选择；
- EVAL-03 停止在质量门（0/6），没有内在化结论；EVAL-02 的对照只控制长度，不控制语义与编制偏差；
- POL2 score-v2 数据为 LLM 标注、非专家金标；Kev-4B 模型权重在外部 Release，本仓库不含权重。

## 5. 本轮对工程侧的改动

- tools/check.py：允许指向「包含仓库（REPO_ROOT）」内的链接并计入 repo_links；逃出仓库仍拒绝（兼容协作者的 Research/ 跨项目引用）。
- datasets/registry.json 合并：保留 general v5 的 HF 字段与新的 pol2-score-v2 条目。
- 未修改协作者的文档内容（仅文档系统整理另行处理）。

## 6. 下一步

- 我们的 GPU 实验仍按 owner 要求暂停；恢复后仍按 finetune/run_plan.py --stages all 执行；
- PR #44/#45 仍为关闭状态，等 owner 给新的 PR 说明意见后重新提交；
- HF 上传（general v5 公开三区 + 私有保留集）仍待 token。
