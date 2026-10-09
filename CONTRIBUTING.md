# 贡献指南 · Contributing

感谢你愿意参与自然道（NaturalDAO）。本仓库有两类内容，流程不同，请先看你要改的是哪一类。

Thanks for contributing to NaturalDAO. The repository holds two kinds of content with different workflows.

| 你要改的内容 | 位置 | 流程 |
| :--- | :--- | :--- |
| 理论文档（爱2证明） | `PoL/`（中文）、`PoLEn/`（English） | 见下文「理论文档」 |
| AI 治理层协作（数据、评测、模型、任务） | `PoL-Governance/` | 见 [AGENTS.md](PoL-Governance/AGENTS.md) 和 [README](PoL-Governance/README.md) |
| 开发规划 | `NaturalDAO开发规划.md`、`NaturalDAO Development Plan EN.md` | 与理论文档相同 |

## 理论文档 · Theory documents

1. **从最新的 `main` 开分支**，不要直接推 `main`。可信成员直接在本仓库开分支；没有写权限的话，先 fork，再从你的 fork 提 PR。
2. **中英文对应**：`PoL/` 与 `PoLEn/` 的同编号文件互为对照。改了一边，请在 PR 里说明另一边是否需要同步，以及由谁来做。
3. **标明出处**：引用、改写或沿用他人的文字、公理、定义或数据，要在正文或参考文献中写明来源（作者、标题、链接或 DOI）。拿不准来源时，在 PR 里说明，不要略过。
4. **不要直接改 Wiki**：Wiki 由 `.github/workflows/sync-wiki.yml` 从 `PoL/`、`PoLEn/` 同步，请改仓库里的文件。
5. **小步提交**：一个 PR 讲一件事，提交信息写清改了什么、为什么。

## PoL-Governance

任务领取、分支命名（`pol/<任务ID>/<短名>`）、任务页、数据边界和交付检查都写在 [PoL-Governance/AGENTS.md](PoL-Governance/AGENTS.md)，以那里为准。两条最重要的：

- **私有保留集、凭据、私有真实对话不进入任何公开分支、fork、PR、日志或截图。** 误提交时立即停止传播并通知维护者；删除最新文件不能清除 Git 历史，含凭据时还需撤销凭据。
- 交付前在 `PoL-Governance/` 目录运行 `uv run --no-project --offline python tools/check.py`，并检查 `git diff --cached`。

## 许可与署名 · License and credit

本仓库遵循 [CC0-1.0](LICENSE)。提交内容即表示你同意以 CC0 发布，请不要提交无法以 CC0 发布的内容。CC0 不免除学术署名的义务：沿用他人成果时仍应标明出处。

## AI 辅助 · AI assistance

可以使用 AI 辅助撰写或整理，但请在 PR 中说明，并由提交者本人核对内容和引用。

## 提问与讨论 · Questions

- 概念、理论、文档问题：开 Issue，选择对应模板。
- 例会：见 [README](README.md) 中的例会信息。
- 安全与敏感内容：见 [SECURITY.md](SECURITY.md)，不要公开发 Issue。

---

**English summary.** Work from the latest `main` on a branch (trusted members push branches here; others fork). Keep `PoL/` and `PoLEn/` in step or say in the PR which side is pending. Credit the source of any text, axiom, definition or data you reuse. Edit the repository files, not the Wiki, which is synced from them. For `PoL-Governance/`, follow its `AGENTS.md`; never commit private hold-out sets, credentials or private conversations. Everything is released under CC0-1.0, which does not remove the duty to credit sources. Disclose AI assistance in the PR.
