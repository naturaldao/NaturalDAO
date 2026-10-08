# Update search 2026-10-08: arXiv screening

Screener: single AI screener, 2026-10-08. Rules: `paper/review/UPDATE_SEARCH_2026-10-08.md` and the eligibility rules in §3. A record is eligible when a typed decision model is its object, a component or a direct comparator. Non-empirical items are recorded but not tallied. Records are screened only, not coded.

Sources: `data/search_rerun_2026-10-08.csv` (46 rows, arXiv web search) plus 22 IDs from the arXiv "Jev" search page. All 22 page IDs were already in the CSV, so nothing was added. The 10 rows that were also in the 4 Oct re-run are marked "already screened 2026-10-04". The other 36 were screened here.

Dates: the v1 date is the first entry in "Submission history" on `https://arxiv.org/abs/<id>` (UTC), fetched 2026-10-08 with a pause of at least 5 s between requests. Four CSV dates are one day earlier than the abs page (2610.07586, 2610.08829, 2610.09286, 2610.09328), because the web listing uses a different timezone. No set assignment changes. No candidate has v1 after 2026-10-08, so none is out of scope.

Sets: **post-window** means v1 dated 2026-10-02..08. **Late-indexed** means v1 dated <= 2026-10-01 and not retrieved by the 1 or 4 Oct searches. This was checked against `data/papers.csv`, `data/excluded_records.csv`, `data/search_rerun_2026-10-04.csv`, `data/grey_literature.csv` and `data/zenodo_preprints.csv`. 2610.08829 has an October ID, but its abs page dates v1 to 27 Sep 2026, so it is late-indexed.

## 1. Screening table

| arxiv_id | v1 date | set | decision | reason |
|---|---|---|---|---|
| 2609.20587 | 2026-09-17 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.23513 | 2026-09-20 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.28182 | 2026-09-23 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.32191 | 2026-09-25 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.32893 | 2026-09-26 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.33609 | 2026-09-27 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.36093 | 2026-09-28 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.37009 | 2026-09-29 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.38334 | 2026-09-29 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2609.38861 | 2026-09-29 | n/a | already screened 2026-10-04 | Screened in the 4 Oct re-run (excluded then; listed in data/excluded_records.csv). |
| 2610.02267 | 2026-10-01 | late-indexed | include | Paired evaluation of hosted Jev and open Laya on 11 agent decision points (injection, tool choice, RAG gating) with order/robustness variants and a self-audit of thresholds. |
| 2610.02293 | 2026-10-01 | late-indexed | include | HakemBench: Turkish typed-decision benchmark (16 models incl. typed models) scoring F1, calibration and selective automation, with order/paraphrase/translation/name probes; guardrail and moderation tracks. |
| 2610.02486 | 2026-10-01 | late-indexed | include | SBERT2S1: authors build typed decision models from biomedical sentence encoders and compare training objectives incl. the open RLCD recipe; calibration after temperature scaling. |
| 2610.02516 | 2026-10-01 | late-indexed | exclude-fulltext | Builds a fixed-taxonomy ModernBERT/DeBERTa routing classifier (no caller-declared options); Jev and Laya are only cited for positioning, neither is measured or compared. |
| 2610.02586 | 2026-10-01 | late-indexed | include | Option-label bias in four open Jev-style typed decision models (laya, von, ...): labels override written definitions; mechanism located in prompt rendering. |
| 2610.03073 | 2026-10-02 | post-window | include | SecJev: authors-built Jev-like typed decision models for security (prompt injection, traffic, authentication) on the Kev scorer, with false-alarm analysis on new sources. |
| 2610.03324 | 2026-10-02 | post-window | include | HATEDECIDE: six structured decision-model configurations (hosted Jev and open models) for hate-speech moderation vs. classifiers and LLMs; effect of definitions and decomposition. |
| 2610.03387 | 2026-10-02 | post-window | include | Rejection-policy transfer and candidate-coverage benchmark comparing Laya, Jev and Qwen2.5 on omitted answers and out-of-scope queries. |
| 2610.03935 | 2026-10-02 | post-window | include | JEVal: bilingual benchmark of 25 configurations incl. Jev and other general decision models; overconfidence, long-horizon agent failures, social-simulation bias; InnerJev models. |
| 2610.04345 | 2026-10-03 | post-window | include | Hosted Jev benchmarked against LLMs and baselines on wireless control tasks (antenna selection, RAN slicing, edge orchestration); quality/latency trade-off. |
| 2610.04985 | 2026-10-04 | post-window | include | Security/privacy study of the Jev API and NanoJev: prompt injection, adversarial suffixes, backdoors, membership/attribute inference, dual use as detector. |
| 2610.05107 | 2026-10-04 | post-window | include | SearchJev: authors-built calibrated System-1 typed model (SLCD) for search agents that delegates uncertain decisions to a System-2 LLM. |
| 2610.06354 | 2026-10-05 | post-window | include | GraphDecide: benchmark of Jev and other choice-based models vs. LMs on graph tasks with matched graph/text input contrasts. |
| 2610.06425 | 2026-10-05 | post-window | include | SoK of 139 semantic-decision-engine paper families plus bounded measurements of Jev-1.13, Laya, AnyJev vs. LLMs on deadlines, queueing and coverage checks; proposes a minimum reporting record. |
| 2610.06625 | 2026-10-05 | post-window | include | Hosted JEV vs. GPT-6 Luna, Qwen and human coders on seven political-science replications: accuracy, cost and calibration. |
| 2610.06744 | 2026-10-05 | post-window | include | ufakzeka-karar: open Turkish typed decision model with order-invariant option scoring and an expected-error "not sure" signal; calibration on HakemBench. |
| 2610.07177 | 2026-10-05 | post-window | include | Open contrastive decision model CLM-v0.1-8B (and laya) as a judge on public benchmarks: accuracy, calibration repair, order flips, confidence-gated cascade (preregistered). |
| 2610.07242 | 2026-10-05 | post-window | exclude-title | Quantum ML for bank impersonation-fraud detection; "calibrated decision threshold" is an incidental phrase match. |
| 2610.07327 | 2026-10-05 | post-window | include | SharedKV-BT: Jev-style typed-decision interface (parallel candidate scoring from a shared KV cache) inside behavior trees, with external postconditions and candidate-order tests. |
| 2610.07586 | 2026-10-06 | post-window | exclude-title | Transonic shocks in nozzles (PDE analysis); "System One" phrase match is accidental. |
| 2610.07716 | 2026-10-06 | post-window | include | Readout stability in prefill-only (Jev-inspired) decision models across seven families: menu-only interventions predictable from the first pass; cascades vs. re-asking. |
| 2610.07730 | 2026-10-06 | post-window | include | SanSi: looped typed decision model trained with proper scoring rules; accuracy by loop budget; used as judge for RL. |
| 2610.07953 | 2026-10-06 | post-window | include | Hosted Jev and open Laya on five moderation benchmarks with rules/precedents/answer-space conditions; confidence for selective review and calibration. |
| 2610.08089 | 2026-10-06 | post-window | include | Formal cost-accuracy framework for semantic queries whose object is calibrated typed decision models (Jev/JEVDB escalation bands); synthetic simulations only. Non-empirical (formal); borderline. |
| 2610.08155 | 2026-10-06 | post-window | include | S1-MAS: open Laya System One model as the coordination controller in a multi-agent LLM framework (task choice, termination). |
| 2610.08675 | 2026-10-06 | post-window | include | Hosted Jev as a source-support verifier for LLM financial calculation traces, stress-tested with same-number citation swaps and label variants. |
| 2610.08743 | 2026-10-06 | post-window | exclude-abstract | RL with conformal/calibrated pruning for sequential recommendation; RLCP acronym match, no typed decision model. |
| 2610.08775 | 2026-10-06 | post-window | include | BOTTLED benchmark: hosted Jev zero-shot used as a direct cost/quality comparator to agent-built "bottled" solutions on ESCI and RAID. |
| 2610.08829 | 2026-09-27 | late-indexed | include | Emo-Jev: training-free decomposition/self-consistency over hosted Jev for affective classification, compared with direct Jev and five LLMs. |
| 2610.09188 | 2026-10-06 | post-window | include | Hosted Jev judgments inside chess search and as a distillation teacher (with Qwen3-32B) for chess and passage reranking. |
| 2610.09286 | 2026-10-07 | post-window | exclude-abstract | Bi-temporal graph system for LLM database agents; "typed answers/claims" are verifier claim types, no typed decision model. |
| 2610.09328 | 2026-10-07 | post-window | include | Visual Jev rewards: a Qwen3.5-4B verifier trained to the Jev-style interface, reading Yes probabilities as typed decisions for GRPO image-generation rewards. |
| 2610.09683 | 2026-10-07 | post-window | include | Open System One typed decision models (0.15B-9B, incl. Laya variants) as fast actor in Doom with confidence-gated deferral to a reasoning VLM; order, calibration, AUROC. |
| 2610.09896 | 2026-10-07 | post-window | include | NL2Hull: authors-built typed decision model Chip vs. native JEV and LMs on ship-design typed questions (accuracy, ECE, Brier). |
| 2610.09937 | 2026-10-07 | post-window | include | Hosted Jev vs. open LMs and a supervised model for HVAC fault diagnosis under season/configuration/building shift; accuracy and calibration under shift. |
| 2610.10321 | 2026-10-07 | post-window | include | Hosted Jev reads crash narratives in a two-tier probability-sample design with human recalibration to produce population estimates (Texas, 5.6M crashes). |

**Counts:** 46 candidates. 10 already screened on 2026-10-04. 36 screened here: 31 include, 2 exclude-title, 2 exclude-abstract, 1 exclude-fulltext.

Included by set: 26 post-window and 5 late-indexed (2610.08829, 2610.02586, 2610.02267, 2610.02486, 2610.02293). Of the exclusions, one is late-indexed (2610.02516) and four are post-window.

Non-empirical: 2610.08089 is a formal framework with synthetic simulations only. It is included under the non-empirical rule because its object is the escalation policy of calibrated typed decision models (Jev/JEVDB). This is a borderline call for the coders to confirm. 2610.06425 is a SoK but reports its own bounded measurements of Jev, Laya and AnyJev, so it is treated as empirical.

Several includes look like background-tier engineering papers ('mainly engineering' in the requirements column). The tier is for the coders to decide.

## 2. Included papers

"Plausible requirements" points to G1–G7 (tab:clauses) at screening level only; it is not a code. Full texts are in the session scratchpad, `C:\Users\ADMINI~1\AppData\Local\Temp\claude\C--Users-Administrator-Downloads-PoL2-Jev-Typed-Literature-Survey\5604ea6b-ea90-485c-a48d-e4d8bbecf48f\scratchpad\update\arx<ID>.txt`, under the file names given below. The first line of each file gives the version and source URL. The text comes from the arXiv HTML of the version read unless noted.

| arxiv_id | v1 date | set | title | authors | plausible requirements | full text | version read |
|---|---|---|---|---|---|---|---|
| 2610.02267 | 2026-10-01 | late-indexed | Fast Models, Slow Evidence: A Paired and Self-Audited Evaluation of System-1 Decision Models for LLM Agent Harnesses | Jiawei Li | G1, G2, G3, G6 | `arx2610.02267.txt` (HTML) | v1 |
| 2610.02293 | 2026-10-01 | late-indexed | HakemBench: A Turkish Benchmark of Typed Decisions | Sait Furkan Teke (ufak AI) | G1, G3, G4, G6 | `arx2610.02293.txt` (HTML) | v1 |
| 2610.02486 | 2026-10-01 | late-indexed | From Retrieval to Typed Decisions: Calibrated System One Models from Biomedical Sentence Encoders | Pritam Deka | G4 (mainly engineering) | `arx2610.02486.txt` (HTML) | v1 |
| 2610.02586 | 2026-10-01 | late-indexed | Labels Override Definitions in Jev-Style Typed Decision Models | Seyedarmin Azizi, Erfan Baghaei Potraghloo, Massoud Pedram | G3 | `arx2610.02586.txt` (HTML) | v1 |
| 2610.08829 | 2026-09-27 | late-indexed | Emo-Jev: Probabilistic Reasoning for Emotion Classification with Jev | Yazhou Zhang, Junhao Yu | G5 (decomposition); mainly engineering | `arx2610.08829.txt` (HTML) | v1 |
| 2610.03073 | 2026-10-02 | post-window | SecJev: Bringing Security Expertise to System One Decision Models | Zheng Chen, Fei Yu, Haohao Huang, Yang Li, Anlong Chen, Lei Chen | G1, G2 | `arx2610.03073.txt` (HTML) | v1 |
| 2610.03324 | 2026-10-02 | post-window | To Jev or Not? Evaluating the Accuracy and Efficiency of Structured Decision Models for Hate-Speech Moderation | Demetris Paschalides, George Pallis, Marios D. Dikaiakos | G1, G3 | `arx2610.03324.txt` (HTML) | v1 |
| 2610.03387 | 2026-10-02 | post-window | Benchmarking candidate coverage and rejection policy transfer in typed decision models | Jiawen Lu, Tongtong Wu | G1, G4, G6 | `arx2610.03387.txt` (HTML) | v2 |
| 2610.03935 | 2026-10-02 | post-window | General Decision Models: Benchmarking and Insights Beyond Jev | Feiyu Duan, Jiayu Lin, Jia Wang, Jun Xiang, Jialiang Wu, Xinnong Zhang, Hanqi Yan, Siyuan Wang, Zhongyu Wei | G4, G6, G7 | `arx2610.03935.txt` (HTML) | v1 |
| 2610.04345 | 2026-10-03 | post-window | System One Models for Wireless Decision-Making:Applications and Performance Evaluation | Masoud Rahimi, S. M. Matin Alemohammad, Hamid Behroozi, Mahdi Nouri | G6 (latency context); mainly engineering | `arx2610.04345.txt` (HTML) | v1 |
| 2610.04985 | 2026-10-04 | post-window | Hidden Risks of Jev: An Empirical Study of Security, Privacy, and Dual Use | Shang Wang, Tianqing Zhu, Huajie Chen, Jiayang Li, Meng Yang, Bo Liu | G1, G2, G7 | `arx2610.04985.txt` (HTML) | v1 |
| 2610.05107 | 2026-10-04 | post-window | SearchJev: A Fast and Calibrated System-1 Model for Search Agents | Congfeng Cao, Lipeng Zuo, Konstantinos Papakostas, Qiwei Xu, Songwei Xu, Lun Zhou, Zhaochun Ren, Yougang Lyu, Xiaohui Yan | G4, G6 | `arx2610.05107.txt` (HTML) | v1 |
| 2610.06354 | 2026-10-05 | post-window | GraphDecide: Benchmarking System One Models on Graph Tasks | Xianliang Yang, Yapu Zhang, Li Zhao | G3 (input-form sensitivity); mainly capability | `arx2610.06354.txt` (PDF via pymupdf; no HTML) | v1 |
| 2610.06425 | 2026-10-05 | post-window | SoK: Semantic Decision Engines in Network Control Loops | Delong Li, Chen Li, Xu Wang, Haochen Gong, Rui Lang, Guangsheng Yu | G5, G6 | `arx2610.06425.txt` (HTML) | v1 |
| 2610.06625 | 2026-10-05 | post-window | JEV versus LLMs: Accuracy, Cost and Calibration on Seven Political Science Replications | Steven Denney, Matthew DiGiuseppe | G4, G7 | `arx2610.06625.txt` (HTML) | v2 |
| 2610.06744 | 2026-10-05 | post-window | ufakzeka-karar: An Open Turkish Typed-Decision Model with Order-Invariant Option Scoring | Sait Furkan Teke (ufak AI) | G3, G4 | `arx2610.06744.txt` (HTML) | v1 |
| 2610.07177 | 2026-10-05 | post-window | CLM-as-a-Judge: Evaluating an Open Contrastive Decision Model on Public Judge Benchmarks | Gowthamkumar Nandakishore | G3, G4, G6 | `arx2610.07177.txt` (HTML) | v1 |
| 2610.07327 | 2026-10-05 | post-window | SharedKV-BT: Node-Local Typed Decisions for Behavior-Tree Agents | Naoki Wake, Justin Wagle | G5, G6 | `arx2610.07327.txt` (HTML) | v1 |
| 2610.07716 | 2026-10-06 | post-window | Readout Stability in Prefill-Only Decision Models:Zero-Label Prediction and Inference-Time Compute Allocation | Ran Li, Lei Chen | G3, G4, G6 | `arx2610.07716.txt` (HTML) | v1 |
| 2610.07730 | 2026-10-06 | post-window | SanSi: A Looped Typed Decision Model for System 1.5 Thinking | Shuyu Gan, Young-Jun Lee, Dongyeop Kang | G4 (mainly engineering) | `arx2610.07730.txt` (HTML) | v1 |
| 2610.07953 | 2026-10-06 | post-window | Benchmarking System One Models in Online Moderation | Federico Mazzoni, Andrea Failla | G1, G4, G6 | `arx2610.07953.txt` (HTML) | v1 |
| 2610.08089 | 2026-10-06 | post-window | When Plans Change Answers: Formalizing Cost-Accuracy Optimization for Semantic Queries | Kyoungmin Kim | G5, G6 (non-empirical) | `arx2610.08089.txt` (HTML) | v1 |
| 2610.08155 | 2026-10-06 | post-window | Token-Efficient Multi-Agent Collaboration via System One-Guided Computational Division of Labor | Zihan Zhou, Xinzhe Hu, Hanxu Yang, Liangjian Wen, Zhao Kang | G6 (mainly engineering) | `arx2610.08155.txt` (HTML) | v1 |
| 2610.08675 | 2026-10-06 | post-window | Same-Number Citation Swaps: Stress-Testing Jev as a Financial Evidence Judge | Chuhong Xu (Sofia University), Bo Su (Indiana University), Ziyao Chen (University of California, San Diego), Ruiyang Xu (Northeastern University), Shimeng Dai (Michigan State University), Xinyu Qiu (Northeastern University) | G1, G3, G5 | `arx2610.08675.txt` (HTML) | v1 |
| 2610.08775 | 2026-10-06 | post-window | Agent in a Bottle: Can LLM Agents Turn Their Capabilities Into Cheap, Scalable Artifacts? | Ankit Sonthalia, Haritz Puerto, Alexander Rubinstein, Martin Gubri, Seong Joon Oh | G7 (cost at scale); comparator only | `arx2610.08775.txt` (HTML) | v1 |
| 2610.09188 | 2026-10-06 | post-window | From Probabilities to Decisions: Search and Multi-Teacher Distillation with Jev | Mohamad Yazan Sadoun, Sarah Sharif, Yaser Mike Banad | none clear (engineering; possibly G7 cost) | `arx2610.09188.txt` (HTML) | v1 |
| 2610.09328 | 2026-10-07 | post-window | Visual Jev Rewards: Reference-Bound Verification for Multi-Subject Image Generation | Baoteng Li, Wenzhuo Wu, Kongming Liang, Zhanyu Ma | G1 (verification); mainly engineering | `arx2610.09328.txt` (HTML) | v1 |
| 2610.09683 | 2026-10-07 | post-window | System Switch: When Should a Fast Decision Model Stop and Think? | Gian Luca Bailo | G3, G4, G6 | `arx2610.09683.txt` (HTML) | v1 |
| 2610.09896 | 2026-10-07 | post-window | NL2Hull: A Natural Language-Driven Constrained Ship Design Decision Framework | Wenhua Huo, Fenglei Han, Wangyuan Zhao, Jialin Wu, Jiayi Han | G4 (mainly engineering) | `arx2610.09896.txt` (HTML) | v1 |
| 2610.09937 | 2026-10-07 | post-window | Where Can a Decision Model Diagnose HVAC Faults? Reasoning Demand, Physical Representation, and Robustness Under Shift | Wooyoung Jung | G1, G4 | `arx2610.09937.txt` (HTML) | v1 |
| 2610.10321 | 2026-10-07 | post-window | Estimating Uncoded Crash Factors with Tabular Foundation and System One Models: Kumo Tabular and Jev | Amir Rafe, Subasish Das | G1, G4, G7 | `arx2610.10321.txt` (HTML) | v1 |

Versions: 2610.03387 and 2610.06625 each have a v2 dated 6 Oct 2026. The v2 was read for both, and v1 and v2 of each fall in the post-window. Every other included paper exists only as v1. 2610.06354 has no HTML rendering, so its text was extracted from the v1 PDF with pymupdf.

## 3. Exclusions

The 5 new exclusions were appended to `data/excluded_records_update_2026-10-08.csv` (source=arXiv). The 10 records already screened on 2026-10-04 are in `data/excluded_records.csv` and are not repeated.
