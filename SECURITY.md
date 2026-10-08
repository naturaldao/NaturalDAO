# 安全政策 · Security Policy

## 适用范围 · Scope

适用于本仓库默认分支 `main` 的当前内容，包括理论文档、`PoL-Governance/` 下的数据、评测与训练脚本，以及 `.github/` 中的工作流。

## 请私下报告的问题 · Please report privately

- 泄露的凭据（API 密钥、令牌、私钥、账号信息）。
- 误提交的私有保留集、私有真实对话、个人信息或其他不应公开的数据。
- 脚本或工作流中的漏洞，例如会执行不可信输入、泄露密钥或向外传送样本的行为。
- 对评测完整性的破坏，例如私有保留集内容进入了训练或公开材料。

请**不要**为这些问题公开发 Issue 或 PR。

## 如何报告 · How to report

1. 优先使用 GitHub 的私密报告：本仓库 **Security** 页签 → **Report a vulnerability**（需维护者在仓库设置中开启 Private vulnerability reporting）。
2. 联系方式：**待补充**（维护者确定后在此处填写）。

报告时请尽量写明：位置（文件和提交）、影响、复现方式。请不要在报告里重复贴出敏感内容本身。

## 误提交后的处理 · If something was committed by mistake

按 [PoL-Governance/AGENTS.md](PoL-Governance/AGENTS.md) 的约定处理：

1. 立即停止传播（不要继续推送、转发、截图）。
2. 通知维护者。
3. 删除最新文件**不能**清除 Git 历史；是否需要重写历史由维护者决定。
4. 含凭据时，先撤销凭据，再做其他处理。

## 披露 · Disclosure

本项目是开放的研究与理论项目。收到报告后，维护者会先确认并处理，再讨论公开说明。目前没有固定的响应时限承诺。

---

**English summary.** This policy covers the current `main` branch. Report leaked credentials, accidentally committed private hold-out sets or private data, script or workflow vulnerabilities, and evaluation-integrity breaches privately, via GitHub's private vulnerability reporting on the Security tab (needs to be enabled by a maintainer). A direct contact address is still to be added. If something was committed by mistake: stop spreading it, tell a maintainer, remember that deleting the latest file does not remove Git history, and revoke any credential first. No response-time commitment is made at present.
