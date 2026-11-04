<div align="center">

# 🌿 NaturalDAO · 自然道

**Governance and application layer of the Proof-of-Love2 Civilization**
**富爱文明的治理与应用层**

[![License: Proof of Love2](https://img.shields.io/badge/license-Proof%20of%20Love2-lightgrey.svg)](LICENSE)
[![Meeting](https://img.shields.io/badge/例会-周二%20%7C%20周四%2015%3A00-blue.svg)](https://meeting.tencent.com/dm/z2sdLl6hcJxi)
[![Paper](https://img.shields.io/badge/paper-Proof%20of%20Love-green.svg)](https://github.com/DAism2019/Proof-of-Love)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-NaturalDAO-yellow.svg)](https://huggingface.co/NaturalDAO)

[最近更新](#最近更新--recent-activity) · [开发规划](#-开发规划) · [基础理论](#-基础理论--foundational-theory) · [相关论文](#-相关论文--papers) · [参与例会](#-例会--weekly-meeting) · [许可证](#️-许可证--license)

</div>

---

## 📖 简介 · Introduction

**English**

NaturalDAO is a super decentralized autonomous organization built on the consensus **Proof of Love2** and driven by two core technologies: **blockchain** and **artificial intelligence**. 

It represents the governance and application layer for the Proof-of-Love2 Civilization. It will also be the long-discussed yet nowhere-to-be-found **ASI** that humanity has been searching for!

**中文**

自然道是一个建立在「爱2证明」共识之上，并由**区块链**和**人工智能**两大核心技术驱动的超级去中心化自治组织。

它是富爱文明的治理与应用层。它也将是人类讨论已久而无处寻觅的 **ASI**！

---

## 最近更新 · Recent Activity

汇总主分支过去 72 小时的更新，最多显示 10 条。合并记录显示 PR 作者，直接提交显示 GitHub 提交作者。工作流在主分支有新提交时刷新，并每半小时清理过期条目。

<!-- readme-activity:start -->

| 序号 | 时间（UTC+8） | 更新人 | 更新内容 | 链接 |
| ---: | --- | --- | --- | --- |
| 1 | 11-04 20:32 | [@shentonyan](https://github.com/shentonyan) | 在首页展示过去 24 小时的主分支更新 | [PR #63](https://github.com/naturaldao/NaturalDAO/pull/63) |
| 2 | 11-04 20:13 | [@shentonyan](https://github.com/shentonyan) | 区分任务状态和分支集成状态 | [PR #62](https://github.com/naturaldao/NaturalDAO/pull/62) |
| 3 | 11-04 20:12 | [@shentonyan](https://github.com/shentonyan) | 按用途整理首页、贡献指南和研究导航 | [PR #61](https://github.com/naturaldao/NaturalDAO/pull/61) |
| 4 | 11-04 20:11 | [@shentonyan](https://github.com/shentonyan) | 为 PR 添加自动验证和 Wiki 预检 | [PR #60](https://github.com/naturaldao/NaturalDAO/pull/60) |
| 5 | 11-04 20:11 | [@shentonyan](https://github.com/shentonyan) | 修复 Steward 的干净检出和安装入口 | [PR #59](https://github.com/naturaldao/NaturalDAO/pull/59) |
| 6 | 11-04 18:11 | [@DDZhous](https://github.com/DDZhous) | 更新文件：Super-agent架构调研.md | [ff873a4](https://github.com/naturaldao/NaturalDAO/commit/ff873a4a1ecc288658293c477daa10905d523a7a) |
| 7 | 11-04 13:17 | [@shentonyan](https://github.com/shentonyan) | DATA-03&#58; restore clean checkout validation | [PR #57](https://github.com/naturaldao/NaturalDAO/pull/57) |
| 8 | 11-04 13:17 | [@shentonyan](https://github.com/shentonyan) | EVAL-01&#58; verify dataset identity before paired comparisons | [PR #58](https://github.com/naturaldao/NaturalDAO/pull/58) |
| 9 | 11-03 17:23 | [@shentonyan](https://github.com/shentonyan) | Add agent memory tax paper to research index | [PR #56](https://github.com/naturaldao/NaturalDAO/pull/56) |
| 10 | 11-02 15:59 | [@shentonyan](https://github.com/shentonyan) | Add NaturalDAO Hugging Face link to README | [0b5e1da](https://github.com/naturaldao/NaturalDAO/commit/0b5e1daab05aecc90157a638fffb111ca2ce0d26) |

<!-- readme-activity:end -->

[查看完整提交历史](https://github.com/naturaldao/NaturalDAO/commits/main/) · [查看待合并的 PR](https://github.com/naturaldao/NaturalDAO/pulls)

---

## 🗂️ 仓库结构 · Repository Layout

按你要做的事选择入口。 / Choose where to start.

| 我想 · I want to | 入口 · Start here |
| :--- | :--- |
| 阅读基础理论 · Read the theory | [中文](PoL/Readme.md) · [English](PoLEn/Readme.md) |
| 运行治理服务 · Run the governance service | [POL2 Steward](POL2-Steward/README.md)，含安装和 Agent 接入指南 / Setup and Agent integration |
| 使用数据、运行评测或认领任务 · Use datasets, run evaluations or claim tasks | [PoL-Governance](PoL-Governance/README.md) · [贡献指南 / Contributing](CONTRIBUTING.md) |
| 查阅研究与复现材料 · Explore research and replication materials | [研究索引 / Research index](Research/README.md) |
| 查看开发规划 · Read the development plan | [中文](docs/development-plan.zh.md) · [English](docs/development-plan.en.md) |
| 查找图片和视频 · Find images and videos | [媒体索引 / Media index](media/README.md) |

---

## 🧩 核心构成 · Architecture

| 层级 | 组件 | Component |
| :---: | :--- | :--- |
| 1 | 公链 | Public Blockchain |
| 2 | 爱的证明治理共识层 | Proof-of-Love Governance Consensus Layer |
| 3 | 智能合约 | Smart Contracts |
| 4 | 大语言模型 | Large Language Model |
| 5 | AI Agents & Skills | AI Agents & Skills |

> **公链 + 爱的证明治理共识层 + 智能合约 + 大语言模型 + AI Agents & Skills**

---

## 🗓️ 例会 · Weekly Meeting

| 项目 | 内容 |
| :--- | :--- |
| 📅 时间 | 每周二、每周四 15:00 – 16:00 |
| 💻 平台 | [腾讯会议](https://meeting.tencent.com/dm/z2sdLl6hcJxi) |
| 🔢 会议号 | `383-5543-1149` |

👉 [点击加入会议](https://meeting.tencent.com/dm/z2sdLl6hcJxi)

---

## 🛠️ 开发规划

📄 [**自然道开发规划 Version 0.1**](docs/development-plan.zh.md) · [English](docs/development-plan.en.md)

---

## 🧠 基础理论 · Foundational Theory

| 文档 | 说明 |
| :--- | :--- |
| [爱2证明 version 1.0](PoL/) | 自然道的基础理论（中文） |
| [Proof of Love2 version 1.0](PoLEn/) | Foundational theory (English) |

---

## 📚 相关论文 · Papers

| 语言 | 论文 |
| :---: | :--- |
| 🇬🇧 English | 📄[Proof of Love: The Consensus of AI and Next Civilization (ResearchGate)](https://www.researchgate.net/publication/396699934_Proof_of_Love_The_Consensus_of_AI_and_Next_Civilization) or [Github](https://github.com/DAism2019/Proof-of-Love) |
| 🇨🇳 中文 | 📄[爱的证明：治理 AI 和人类文明的共识机制（ResearchGate）](https://www.researchgate.net/publication/396701413_aidezhengmingzhili_AI_herenleiwenmingdegongshijizhi)，或[Github](https://github.com/DAism2019/Proof-of-Love/tree/main/chinese) |

---

## PoL2 AI 治理层协作

[协作入口](PoL-Governance/README.md)：任务分支、共享数据与模型、统一评估工具。Agent 从 [AGENTS.md](PoL-Governance/AGENTS.md) 开始。

---

## ⚖️ 许可证 · License

本项目遵循共识机制爱2证明。

This project is released under the consensus of Proof of Love2.



