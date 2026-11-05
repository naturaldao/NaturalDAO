<div align="center">

# 🌿 NaturalDAO · 自然道

**Governance and application layer of the Proof-of-Love2 Civilization123**
**富爱文明的治理与应用层**

[![License: Proof of Love2](https://img.shields.io/badge/license-Proof%20of%20Love2-lightgrey.svg)](LICENSE)
[![Meeting](https://img.shields.io/badge/例会-周二%20%7C%20周四%2015%3A00-blue.svg)](https://meeting.tencent.com/dm/z2sdLl6hcJxi)
[![Paper](https://img.shields.io/badge/paper-Proof%20of%20Love-green.svg)](https://github.com/DAism2019/Proof-of-Love)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-NaturalDAO-yellow.svg)](https://huggingface.co/NaturalDAO)

[简介](#-简介--introduction) · [最近更新](#-最近更新--recent-activity) · [仓库结构](#️-仓库结构--repository-layout) · [核心构成](#-核心构成--architecture) · [例会](#️-例会--weekly-meeting)<br>
[开发规划](#️-开发规划) · [基础理论](#-基础理论--foundational-theory) · [相关论文](#-相关论文--papers) · [治理层协作](#pol2-ai-治理层协作) · [许可证](#️-许可证--license)

</div>

---

## 📖 简介 · Introduction

NaturalDAO is a super decentralized autonomous organization built on the consensus **Proof of Love2** and driven by two core technologies: **blockchain** and **artificial intelligence**. 

It represents the governance and application layer for the Proof-of-Love2 Civilization. It will also be the long-discussed yet nowhere-to-be-found **ASI** that humanity has been searching for!

自然道是一个建立在「爱2证明」共识之上，并由**区块链**和**人工智能**两大核心技术驱动的超级去中心化自治组织。

它是富爱文明的治理与应用层。它也将是人类讨论已久而无处寻觅的 **ASI**！

---

## 🪾 最近更新 · Recent Activity

主分支最近 7 天的更新按人、按日汇总（UTC+8），最多 15 行。每行显示最新两项，其余见「其他更新」。点击文件名打开对应版本，点击「详情」查看完整变更。

Main branch updates from the past seven days, grouped by contributor and day (UTC+8), up to 15 rows. Each row shows the two latest updates. File names open the changed version, and “Details” opens the full change.

<!-- readme-activity:start -->

| 序号<br>No. | 时间（UTC+8）<br>Time (UTC+8) | 更新人<br>Contributor | 更新详情<br>Update details |
| ---: | --- | --- | --- |
| 1 | 11-04 13:17–22:01 | [@shentonyan](https://github.com/shentonyan) | <strong>22:01 · 精简首页文件预览并缩进文件行</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/859ab39d2b755301784d63a2ce10e597fce5da90/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/859ab39d2b755301784d63a2ce10e597fce5da90)<br><br><strong>21:55 · 首页默认显示两项更新并补充英文对照</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/4badf7a61839af49619962cb15dafe71317ca1cf/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/4badf7a61839af49619962cb15dafe71317ca1cf)<details><summary>其他更新 · Other updates (13)</summary><strong>21:49 · 折叠首页动态并配对摘要与文件</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/6ba91332ea6100b27a13b1092c5c40abcee1cf90/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/6ba91332ea6100b27a13b1092c5c40abcee1cf90)<br><br><strong>21:39 · 按更新人和日期合并首页动态并校正导航</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/06b884b3a4d7fa224881f25cb95bbfec07294712/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/06b884b3a4d7fa224881f25cb95bbfec07294712)<br><br><strong>21:02 · 分页展示过去一周的更新并链接变更文件</strong><br>　　[readme&#95;activity.py](https://github.com/naturaldao/NaturalDAO/blob/7ea6c8405216bd3236e4a291beaf33c99a7c4919/.github/scripts/readme_activity.py) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/7ea6c8405216bd3236e4a291beaf33c99a7c4919)<br><br><strong>20:53 · Update README.md</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/4c26121fe3c167a5bdadd1bb46cc7f9b19203655/README.md)<br><br><strong>20:44 · Update README.md</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/fa04b31abdf7960fcb161268d1cf548e7c0451b3/README.md)<br><br><strong>20:42 · 用表格展示主分支最近 72 小时的更新</strong><br>　　[readme&#95;activity.py](https://github.com/naturaldao/NaturalDAO/blob/2b59b258c393df100f58a17a2b5812b42a4ff779/.github/scripts/readme_activity.py) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/2b59b258c393df100f58a17a2b5812b42a4ff779)<br><br><strong>20:32 · 在首页展示过去 24 小时的主分支更新</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/f4a0cea3403d0a6e2a4a22c0e851bdba3c107b3c/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/f4a0cea3403d0a6e2a4a22c0e851bdba3c107b3c)<br><br><strong>20:13 · 区分任务状态和分支集成状态</strong><br>　　[TASKS.md](https://github.com/naturaldao/NaturalDAO/blob/d65349f9fe29f931fcd4ba0eba259fb680f89ce4/PoL-Governance/TASKS.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/d65349f9fe29f931fcd4ba0eba259fb680f89ce4)<br><br><strong>20:12 · 按用途整理首页、贡献指南和研究导航</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/f3bb0165725a5d7f4591aa7ba0eeec2073adf1dd/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/f3bb0165725a5d7f4591aa7ba0eeec2073adf1dd)<br><br><strong>20:11 · 为 PR 添加自动验证和 Wiki 预检</strong><br>　　[sync&#95;wiki.py](https://github.com/naturaldao/NaturalDAO/blob/a204ecb8dcb83b6da1fc6cca1ac7f8ed37ad1a3e/.github/scripts/sync_wiki.py) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/a204ecb8dcb83b6da1fc6cca1ac7f8ed37ad1a3e)<br><br><strong>20:11 · 修复 Steward 的干净检出和安装入口</strong><br>　　[install.sh](https://github.com/naturaldao/NaturalDAO/blob/ddbc5ff477100ae8dd48f8be00191beb7b5d8e60/POL2-Steward/pol2-service/install.sh) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/ddbc5ff477100ae8dd48f8be00191beb7b5d8e60)<br><br><strong>13:17 · DATA-03&#58; restore clean checkout validation</strong><br>　　[HF.md](https://github.com/naturaldao/NaturalDAO/blob/511c27d1136de5cee74a0d58fdcdd67f47750793/PoL-Governance/datasets/general/HF.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/511c27d1136de5cee74a0d58fdcdd67f47750793)<br><br><strong>13:17 · EVAL-01&#58; verify dataset identity before paired comparisons</strong><br>　　[uncertainty.py](https://github.com/naturaldao/NaturalDAO/blob/52d87efd15f197b72d9f7458ca2d031b4ea23486/PoL-Governance/benchmark/pol2/uncertainty.py) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/52d87efd15f197b72d9f7458ca2d031b4ea23486)</details> |
| 2 | 11-04 18:11 | [@DDZhous](https://github.com/DDZhous) | <strong>18:11 · 更新文件 / Updated files：Super-agent架构调研.md</strong><br>　　[Super-agent架构调研.md](https://github.com/naturaldao/NaturalDAO/blob/ff873a4a1ecc288658293c477daa10905d523a7a/Research/Engineering/Super-agent%E6%9E%B6%E6%9E%84%E8%B0%83%E7%A0%94.md) |
| 3 | 11-03 17:23 | [@shentonyan](https://github.com/shentonyan) | <strong>17:23 · Add agent memory tax paper to research index</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/89d9b297d74a6ed379133ec3476acf1404b56fe1/Research/Engineering/README.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/89d9b297d74a6ed379133ec3476acf1404b56fe1) |
| 4 | 11-02 15:59 | [@shentonyan](https://github.com/shentonyan) | <strong>15:59 · Add NaturalDAO Hugging Face link to README</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/0b5e1daab05aecc90157a638fffb111ca2ce0d26/README.md) |
| 5 | 11-01 20:06 | [@shentonyan](https://github.com/shentonyan) | <strong>20:06 · GOV-01&#58; add E17 priority appeal robustness study</strong><br>　　[experiment-design.md](https://github.com/naturaldao/NaturalDAO/blob/1c0905dc3fa38dc40d864019b057b43491a1cda4/PoL-Governance/research/PoL2-DAO-Governance-Lab/docs/experiment-design.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/1c0905dc3fa38dc40d864019b057b43491a1cda4) |
| 6 | 11-01 16:49 | [@Aranna-0572](https://github.com/Aranna-0572) | <strong>16:49 · Update outreach tracker with 7 contacted researchers</strong><br>　　[NaturalDAO&#95;BD&#95;Outreach&#95;Tracker.csv](https://github.com/naturaldao/NaturalDAO/blob/2eabd365002e953799d245e21f14def4682e6b64/BD/NaturalDAO_BD_Outreach_Tracker.csv) |
| 7 | 10-30 04:36–14:29 | [@shentonyan](https://github.com/shentonyan) | <strong>14:29 · Fix inline math spacing and equation number alignment</strong><br>　　[MemT-1.0-节选翻译.md](https://github.com/naturaldao/NaturalDAO/blob/630c0ec4204380a9a03bc7ab7bfe40c2fc471fcc/Research/Storage/02-%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/MemT-1.0-%E8%8A%82%E9%80%89%E7%BF%BB%E8%AF%91.md)<br><br><strong>14:27 · Fix equation rendering and right-align numbers</strong><br>　　[MemT-1.0-节选翻译.md](https://github.com/naturaldao/NaturalDAO/blob/543f80df15314915d59964a7bc88b330214e7929/Research/Storage/02-%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/MemT-1.0-%E8%8A%82%E9%80%89%E7%BF%BB%E8%AF%91.md)<details><summary>其他更新 · Other updates (2)</summary><strong>14:15 · Fix GitHub math rendering and number equations</strong><br>　　[MemT-1.0-节选翻译.md](https://github.com/naturaldao/NaturalDAO/blob/d0b7a0e08e9869ea118cf33086f07419653a4e50/Research/Storage/02-%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/MemT-1.0-%E8%8A%82%E9%80%89%E7%BF%BB%E8%AF%91.md)<br><br><strong>04:36 · GOV-01&#58; add E16 non-market public resource allocation study</strong><br>　　[experiment-design.md](https://github.com/naturaldao/NaturalDAO/blob/49dcde670691d9bb141ced5d18f94b2f4050647a/PoL-Governance/research/PoL2-DAO-Governance-Lab/docs/experiment-design.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/49dcde670691d9bb141ced5d18f94b2f4050647a)</details> |
| 8 | 10-30 10:21–11:53 | [@DDZhous](https://github.com/DDZhous) | <strong>11:53 · Update and rename MemT-1.0-arxiv.md to MemT-1.0-节选翻译.md</strong><br>　　[MemT-1.0-节选翻译.md](https://github.com/naturaldao/NaturalDAO/blob/297386d51522eadb70fa574c3e425d90d75036b0/Research/Storage/02-%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/MemT-1.0-%E8%8A%82%E9%80%89%E7%BF%BB%E8%AF%91.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/297386d51522eadb70fa574c3e425d90d75036b0)<br><br><strong>11:52 · Create MemT-1.0-arxiv.md</strong><br>　　[MemT-1.0-arxiv.md](https://github.com/naturaldao/NaturalDAO/blob/a1dee4c06428907c1461b5411e35868ee178ee77/Research/Storage/02-%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/MemT-1.0-arxiv.md)<details><summary>其他更新 · Other updates (3)</summary><strong>10:31 · Update Readme.md</strong><br>　　[Readme.md](https://github.com/naturaldao/NaturalDAO/blob/0ae5488c3bcf8f3b8df49765f7fe28dda464f0a4/PoLEn/Readme.md)<br><br><strong>10:28 · Update Readme.md</strong><br>　　[Readme.md](https://github.com/naturaldao/NaturalDAO/blob/06e0adb8d243b157967f51beeea2e325d7891ed4/PoL/Readme.md)<br><br><strong>10:21 · Update README.md</strong><br>　　[README.md](https://github.com/naturaldao/NaturalDAO/blob/da03fde9074c7eedb0f6be8ab55cbc5616f9f43e/README.md)</details> |
| 9 | 10-29 00:04 | [@Wenbobobo](https://github.com/Wenbobobo) | <strong>00:04 · Session B：Kev-4B 前后对照评测与单文件 HTML 报告（MODEL-02 累积更新）</strong><br>　　[ROADMAP.md](https://github.com/naturaldao/NaturalDAO/blob/d2e492f3ea84c8d5cc707e9a22488ea20ca376c6/PoL-Governance/ROADMAP.md) · [详情 / Details](https://github.com/naturaldao/NaturalDAO/commit/d2e492f3ea84c8d5cc707e9a22488ea20ca376c6) |

<!-- readme-activity:end -->

[查看完整提交历史 · View full commit history](https://github.com/naturaldao/NaturalDAO/commits/main/)

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



