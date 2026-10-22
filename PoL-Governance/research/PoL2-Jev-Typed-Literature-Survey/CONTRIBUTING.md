# 参与贡献

欢迎补充论文、修正归类或指出错误。

## 新增一篇论文

1. 在 [`data/pol2_mapping.csv`](data/pol2_mapping.csv) 加一行：`arxiv_id, tier, pol_axes, note_zh`。
   - `tier`：`核心` / `相关` / `背景`；
   - `pol_axes`：G1–G7 中的一个或多个，用空格分隔，定义见 [`data/pol2_axes.json`](data/pol2_axes.json)；
   - `note_zh`：一句话要点，尽量带上论文中的具体数字。
2. 运行 `scripts/fetch_papers.ps1` 抓取元数据、许可与 PDF。
3. 运行 `python scripts/build_catalog.py` 与 `python scripts/check.py`，确认检查通过。
4. 如果这篇论文改变了综述中的某个结论，同时修改 [`docs/survey.zh.md`](docs/survey.zh.md) 的对应小节。

非 arXiv 的灰色文献（博客、技术报告、开源仓库）加到 [`data/grey_literature.csv`](data/grey_literature.csv)，并在综述第 6 节的表格中补一行。

## 纳入标准

以 Jev 或 Jev 类 System One 决策模型为研究对象、实验组件或直接对照的研究。Jev 发布之前的背景文献（校准、拒答选项、LLM 评判器等经典工作）不收入本目录，可参考 [Awesome System One Models](https://github.com/pozapas/awesome-system-one-models) 的完整谱系。

## 写作约定

- **术语**遵循 PoL2 正文：写"恨语"而不写"仇恨言论 / hate speech"，写"被遮蔽的智慧"而不写"被污染的智慧"；不使用"恨人 / 爱人"之类的身份名词。
- **负面结果优先。** 与 PoL2 的设计原则一致，负面或限定性的发现比确认性的发现更值得写清楚。
- **不夸大。** 预印本就写预印本，样本小就写样本小；没有读过全文的，只引用摘要中的数字。
- **需要团队确认的判断**用 ★ 标出。

## 许可

**只收入允许再分发的论文全文**（Creative Commons 各版本）。arXiv 默认许可（arXiv.org perpetual non-exclusive license）只授权 arXiv 分发，这类论文只提供链接；`fetch_papers.ps1` 会把它们下载到被 git 忽略的 `papers/_local/`，请勿手动加入仓库。`scripts/check.py` 会拦截这类文件。

## 分支与 PR

在主仓库新建分支，例如 `lit/pol2-jev/<短名>`，提交后开 PR 到 `main`。如果 [PR #15](https://github.com/naturaldao/NaturalDAO/pull/15) 的 `PoL-Governance/` 协作约定已合并，也可以按其 `pol/<任务ID>/<短名>` 规则开任务分支。
