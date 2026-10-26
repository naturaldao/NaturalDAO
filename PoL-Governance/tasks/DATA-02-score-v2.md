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
