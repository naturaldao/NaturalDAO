# EVAL-01：配对评测核对数据版本

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Codex / OpenAI Codex | 待集成。配对比较要求两份报告具有相同的案例和标签指纹。 |

- 更新时间：2026-11-04 13:14 Asia/Hong_Kong
- 分支：pol/EVAL-01/paired-data-version
- 起点 commit：`89d9b29`
- 证据：场景族和样本数相同、数据指纹不同的合成报告现在会被拒绝。正式评测目录的 72 项测试通过。
- 环境 / 数据边界：Windows，离线检查，使用公开 fixtures 和合成报告。
- 全量检查：叠加 DATA-03 修复运行 `uv run --no-project --offline python tools/check.py` 通过（1,053 项收集，12 项按条件跳过）。独立分支的全量检查仍受主分支已知断链阻挡。
- 下一步：在 DATA-03 干净检出修复合并后集成。需要配对的旧报告可从同一版本的案例和标签重新生成。
