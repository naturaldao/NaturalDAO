# DATA-02 · POL2 score-v2 数据发布

- 领取人：w609641894 / Codex
- 状态：待集成
- 分支：`pol/DATA-02/score-v2`
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

1. 维护者审核数据卡、许可和公开发布包；
2. 需要时补 canonical 转换；
3. 合并后把 Release 状态从候选改为正式。
