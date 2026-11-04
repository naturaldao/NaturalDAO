# DATA-03：修复干净检出的交付检查

| 领取人 / Agent | 状态 / 最近进展（Agent 更新） |
|---|---|
| Codex / OpenAI Codex | 待集成。修复通用数据托管文档的历史断链，以及 Windows 短路径下的仓库内凭据路径判断。 |

- 更新时间：2026-11-04 13:14 Asia/Hong_Kong
- 分支：pol/DATA-03/clean-check
- 起点 commit：`89d9b29`
- 证据：干净检出原本在 `HF.md` 断链处中止。修复后，凭据路径检查的 10 项单元测试通过。
- 环境 / 数据边界：Windows，离线检查，使用合成测试数据。
- 全量检查：Windows 干净检出运行 `uv run --no-project --offline python tools/check.py` 通过（1,051 项收集，12 项按条件跳过）。
- 下一步：审阅后合并。
