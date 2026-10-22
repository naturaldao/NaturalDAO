# Update search, 8 October 2026: Zenodo and grey-literature screening

Protocol: `paper/review/UPDATE_SEARCH_2026-10-08.md`. Eligibility: §3 (`paper/sections/03_method.tex`). The model under study must be a typed decision model, as object, component or direct comparator. Non-empirical items are recorded and not tallied.

Source list: `data/search_rerun_zenodo_2026-10-08.csv` (44 rows). One AI coder screened it on 2026-10-08. For every row the screener read the Zenodo records API entry (`https://zenodo.org/api/records/<id>`: description, files, related identifiers, concept/version history). For every borderline row the screener also opened the main file or the deposit archive.

Conventions:
- **Set** follows the protocol's rule on the *first public version* of the Zenodo concept, taken from the concept's version history.
  - **post-window** means first version dated 2–8 Oct.
  - **late-indexed** means first version dated ≤ 1 Oct, with the record absent from `data/zenodo_preprints.csv`.
  - This rule differs from the record's own date in only two rows: KITE code 23107613 (record dated 10-02, concept first version 09-27) and wisp-science 23205210 (concept first version 2026-07-04).
- **Late-indexed caveat.** The 1 October Zenodo screening recorded its exclusions only as counts. So a "late-indexed" row here may be a record that was retrieved on 1 October and excluded then, not one that was missing from the index. This screening cannot tell the two cases apart. All ≤ 1 Oct rows were therefore re-screened with the §3 criteria. The 15 late-indexed inclusions below include several software or dataset deposits and short reports. The 1 October screen may have excluded these by record type. The author should decide whether to report them as "late-indexed" or as "re-screened, previously excluded".
- Duplicate and companion checks compared concept ids and titles against `data/zenodo_preprints.csv` (28 records, whose concept ids were fetched from the API), `data/papers.csv` (arXiv corpus) and `data/search_rerun_2026-10-08.csv` (today's arXiv re-run).

## 1. Screening table (44 rows)

| zenodo_id | first version | type | decision | set | reason |
|---|---|---|---|---|---|
| 22806344 | 09-17 | publication | exclude-title | late-indexed | Penrose/Lorentzian toy model (mathematical physics). "TypeSafe" description match is accidental. Probably an earlier count-only exclusion. |
| 22886178 | 09-21 (v1.1.0 09-22) | software | **include** | late-indexed | ExoNotes: preregistered study. Jev (hosted) is used as a semantic featurizer for TESS observer notes, with paraphrase-stability gates. 1,482 TOIs, plus a Kepler transfer test. Typed model as experimental component. |
| 22904595 | 09-23 | publication | **include** | late-indexed | Plan-and-execute web agent. Laya (open typed model, zero-shot) does element grounding and change checks. 2,400 runs against ReAct, plus a word-overlap ablation of Laya. |
| 22921974 | 09-17 (v0.6.0 09-23) | software | **include** | late-indexed | daf-jev toolkit, with a live-API characterisation of hosted Jev: batching latency/tokens, and confidence self-consistency over repeated calls. Engineering/background-type evidence. |
| 22933883 | 09-24 | publication | **include** | late-indexed | Audio-Laya: Whisper projector into the Laya decision model, compared with an ASR→Laya baseline. Spam/legit labels are fully confounded with corpus (stated by the author). Zero-shot transfer fails. |
| 22935043 | 09-24 | software | **include** | late-indexed | Calibration audit of jev-1.13.0 against DeBERTa zero-shot NLI and gpt-4.1-nano/gpt-5.4-nano on SST-2/AG News. The deposit contains the paper (`paper/JEV_PAPER.pdf`). No other public version was found, so this is a study record, not a companion. |
| 22939253 | 09-21 | publication | duplicate-version | late-indexed | Zenodo copy of arXiv 2609.25498 ("Universal Fractal Natural Language Decision Map"), which is already in the corpus (background tier). |
| 22941164 | 09-24 | publication | **include** | late-indexed | wev: open System-One decision models (Qwen3 1.7B/4B/8B) distilled from LLM browser agents. Unseen-website step accuracy, and live tasks against the LLM teacher. Not found in the arXiv corpus. |
| 22945279 | 09-24 | software | **include** | late-indexed | Benchmark: jev-1.13.0 and Laya against Qwen3.5-35B-A3B on 12,000 federal IT solicitations. Accuracy, ECE 0.049, and auto-accept at a Wilson-bounded 95% precision. Full report in `docs/reports/`. |
| 22952538 | 09-20 (v1.2.0 09-25) | dataset | companion | late-indexed | Evidence/reproduction package of included **Z-22952571** (Williams, "Jev at the Agent Authorization Boundary"). The paper record lists it as `isSupplementedBy`. |
| 22956802 | 2022-12-22 (v0.1.0 09-25) | software | exclude-abstract | late-indexed | tasksource framework release. Adds a "jev" recast of training data but measures no typed model. |
| 22971413 | 09-26 | publication | companion | late-indexed | Preregistration for included **Z-23032384** (Khosla, "Confident Where People Disagree"). That paper `references` it. Use it for the design rating (preregistered); it is not a separate study. |
| 22979052 | 09-26 | software | **include** (borderline) | late-indexed | Sev Arabic Preview: an open Arabic typed decision model (mmBERT + typed head). Its only result is an in-house dev-split accuracy/ECE that the author says is not a benchmark. Included because §3 admits studies that build a typed model and report measurements. It will probably code as background or uncoded. |
| 23005202 | 09-28 | software | **include** | late-indexed | Reflex-1: open 4B typed decision model (Gemma 4 E4B), compared on five public classification benchmarks with hosted Jev and frontier LLMs (README table). Full tables are said to be in an external blog post that is not in the deposit. |
| 23005211 | 09-27 (v1.1 09-28) | publication | duplicate-version | late-indexed | Zenodo version of arXiv **2609.34227** ("When Does Selection Replace Extraction?"), already in the corpus. |
| 23008156 | 09-28 | publication | duplicate-version | late-indexed | Zenodo version of arXiv **2609.34024** ("Jev in Medicine"), already in the corpus. Note: the arXiv title says "Preliminary Results". The Zenodo abstract reports full results on four benchmarks (MetaMedQA, PubMedQA, DiagnosisArena-MCQ, NEJM). The coders should check whether the corpus coding used the latest numbers. |
| 23019391 | 09-28 | publication | exclude-fulltext | late-indexed | TRS v3.3P. The three configurations tested are Sonnet 4.5, Gemini 3.1 Flash Lite and GPT-5 with structured outputs. No typed decision model is used (0 mentions of Jev/Laya). |
| 23024634 | 09-29 | publication | exclude-fulltext | late-indexed | Schema-conformance pilot on the same 41 texts with the same three generative LLMs. No typed decision model. |
| 23039006 | 09-29 | dataset | companion | late-indexed | Response databases of arXiv **2609.37647** (Deußer et al., "Evaluating and Benchmarking the System One Model Jev"), which is already in the corpus (`isDescribedBy`). |
| 23047544 | 09-29 | publication | **include** | late-indexed | jev-1.13.0 as a typed HOLD/LONG/SHORT/CLOSE trading agent on Binance L2 data. Latency and "epistemic calibration" claims. Single author, extraordinary Sharpe; expect a weak design rating. |
| 23048160 | 09-30 | publication | exclude-fulltext | late-indexed | Decision-theory framework. JEV appears only via vendor docs. Its empirical routing experiment uses logged LLM outputs and makes no call to a typed model. |
| 23050542 | 09-30 | software | **include** | late-indexed | Replication package: jev-1.13.0 (one overall Noul question) screens the 142,504-record TITAN-SR set of 22 Cochrane reviews. Recall/specificity at 0.3 and 0.5, AUC, WSS@95 per review (`report.md`). |
| 23065177 | 09-30 | dataset | exclude-abstract | late-indexed | SWAT+ hydrology run trees. The "typed decision log" is a workflow ledger, not a typed decision model. |
| 23075657 | 10-01 | publication | **include** | late-indexed | Hagino: Jev against three adapted encoders on ToxicChat at dev-selected operating points (90.5% recall at 3.2% FPR), plus a label-budget campaign. This is a different study from Hagino's included Z-22885291 (different concept and data). |
| 23077245 | 09-29 | publication | exclude-title | late-indexed | Soil eDNA dataset. "RLCD" match is accidental. |
| 23088660 | 10-01 | publication | **include** | late-indexed | Confidence-gated reranking with jev-1.13.0 on 4,000 held-out domain names. Gate at ≥0.90 gives 99.2% precision at 53.1% coverage. 13-slide report. |
| 23094450 | 10-02 | dataset | companion | post-window | Reproducibility package for Zenodo **23094322** ("Measuring Institutional AI Research in India", 2026-10-01). That paper was *not* returned by the 11 queries and was found through this record's `isSupplementTo` link (see §2). |
| 23094628 | 10-02 | publication | **include** | post-window | Yway: open Burmese typed decision model (Laya head + XLM-R). Held-out routing/answerability/topic accuracy, calibration, and an answer checker. |
| 23107613 | 09-27 (v0.6.1 10-02) | software | companion | late-indexed | Code and ledger of arXiv **2609.27535** (KITE), which is already in the corpus (`isSupplementTo`). |
| 23119392 | 10-03 | software | **include** | post-window | PMI-threshold study. jev-1.13.0 is the single automated judge of 40,725 Wikidata relations, not validated by humans. The paper (`Research_Paper.pdf` in the deposit) also reports Jev giving different verdicts on symmetric and identical inputs. Typed model as component. |
| 23123503 | 10-03 | publication | **include** | post-window | Lopez Lopez, "Paraphrastic Resistance". It crosses an IRP text-fragility index with a 2×2 Laya design (checkpoint × class semantics) and adds a Gemini comparison. **Reuses the Laya observations of included Z-23065532** (same author). Code only the new analysis to avoid double counting. The paper also cites a 2026-09-27 web version (aiscanlab.com), so its first public version may fall inside the window. |
| 23138396 | 10-04 | publication | **include** (non-empirical) | post-window | Position paper: an anti-cheat architecture built on System One decision models with cost-derived thresholds and escalation to human review. Not implemented. Record it; do not tally it. |
| 23154999 | 09-30 | publication | **include** | late-indexed | Laya (421M) fine-tuned, with and without retrieval-augmented decision-making, as a local intrusion detector with graduated response. Synthetic logs (20 reps) plus CIC-IDS2017, against rule and anomaly baselines. |
| 23167634 | 10-05 | software | exclude-fulltext | post-window | isotherm is a weather prediction-market forecaster (log pool of market price and EMOS-GFS, plus an MLP). Choice/Noul/Score are read off its own bucket distribution. It is not a model over a free-form state with caller-declared options, and nothing measured bears on G1–G7 (borderline). |
| 23178217 | 10-05 | dataset | companion | post-window | Experiment package for **arXiv 2610.08675** ("Same-Number Citation Swaps: Stress-Testing Jev as a Financial Evidence Judge", 2026-10-06), which is in today's arXiv re-run. The manuscript is not bundled. Link it to the arXiv record if the arXiv screener includes it. |
| 23179064 | 10-06 (v1 23175660, same day) | publication | **include** | post-window | Velu: exact-target calibration audit of hosted Jev (Choice against Noul) and three open decision models, plus ChaosNLI/DICES-350. Choice is overconfident, Noul is not. |
| 23186353 | 10-06 | publication | **include** | post-window | Noma: open 4B sliced-decoder typed decision model with a supervised abstain head. Sealed set, ablations. Not in the arXiv corpus. |
| 23187206 | 10-06 | publication | **include** | post-window | Lopez Lopez: an IRP gate against a typed (Laya) supervisor in a synthetic 3-node invoicing chain. The typed supervisor shows 0% failure recall. Same author line as Z-23065532 and 23123503, so not independent. |
| 23189584 | 10-06 | software | **include** (case study) | post-window | Runtime-governance PoC with jev-latest as a bounded semantic component inside a deterministic shell. J4 offline failure injection, plus 2 Human-Gated live calls (J6). Minimal measurement. The repo docs are dated from 2026-09-26, but the first Zenodo version is 10-06. |
| 23200782 | 10-07 | publication | **include** | post-window | Jev as a typed per-turn supervisor for SWE agents. Active, none and shadow conditions on 90 SWE-bench Verified tasks: +7.2 pp, CI −4.3 to +18.8, with the shadow arm showing a similar effect. |
| 23205210 | 2026-07-04 (v1.18.0 10-07) | software | exclude-abstract | post-window | wisp-science desktop-app release notes. No typed decision model measured. |
| 23221456 | 10-07 | software | **include** | post-window | System-One Control Bench: Jev, Laya and GLiClass against Qwen3.5-4B, Gemma 4 26B and DeepSeek V4.1 Flash on 100 grid puzzles and a 495-position exam. Report `paper/main.pdf` in the deposit. |
| 23224892 | 10-08 | software | companion | post-window | SignRule-Decide code; supplement of 23225893 (`isSupplementedBy`). |
| 23225893 | 10-08 | publication | **include** | post-window | SignRule-Decide: 4B typed decision model with an abstain option for company-representation rules. Austrian held-out set, plus Norwegian/Danish transfer. Abstention thresholds do not transfer. |

**Counts (44 rows):**

| Decision | Rows | Records |
|---|---|---|
| include | 25 | 14 late-indexed, 11 post-window. One of these is non-empirical (23138396). |
| exclude-title | 2 | |
| exclude-abstract | 3 | |
| exclude-fulltext | 4 | |
| companion | 7 | 22952538, 22971413, 23039006, 23107613 (linked to records already in the corpus); 23094450, 23224892 (linked to new inclusions); 23178217 (linked to arXiv 2610.08675, pending the arXiv screener) |
| duplicate-version | 3 | 22939253, 23005211, 23008156 (all of arXiv records already in the corpus) |

One more record was found through a companion link (§2), so there are **26 included records** in total.

The 9 exclusions are appended to `data/excluded_records_update_2026-10-08.csv`. Companions and duplicate versions are not exclusions and were not written there.

## 2. Record found outside the query results

| id | first version | decision | set | reason |
|---|---|---|---|---|
| 23094322 | 10-01 | **include** | late-indexed (found via companion link, not retrieved by the queries) | "Measuring Institutional AI Research in India" (Chintan Dave). Jev classifies 41,172 OpenAlex works into AI-relevant or not, with an internal agent-adjudicated 88-record calibration check. Typed model as population-scale component, analogous to arXiv 2610.00213. The author may prefer to report it as "identified by citation chasing". |

## 3. Included records

The main full text (PDF) and its text extract (pymupdf) are in
`C:\Users\ADMINI~1\AppData\Local\Temp\claude\C--Users-Administrator-Downloads-PoL2-Jev-Typed-Literature-Survey\5604ea6b-ea90-485c-a48d-e4d8bbecf48f\scratchpad\update\` (written below as `update\`).

Where a record has no PDF, `zen<ID>.txt` concatenates the deposit's report and README markdown files. The archive is copied alongside it as `zen<ID>.zip` or `.tar.gz`.

"G" gives the requirements that each record *plausibly* bears on (`tab:clauses`). It is a pointer for the coders, not a code.

| id | first version | title | authors | set | G (plausible) | full text |
|---|---|---|---|---|---|---|
| 22886178 | 2026-09-21 | ExoNotes: do ExoFOP observer notes carry disposition signal beyond the numeric TOI catalogue? | Kevin Javier Arce Alfaro | late-indexed | G3 (paraphrase stability), G7 | `update\zen22886178.txt` (+ `.zip`; no PDF) |
| 22904595 | 2026-09-23 | Plan Once, Ground Locally: Plan-and-Execute Web Agents Match ReAct Accuracy at One-Sixth of the Token Cost | Divyansh Shukla | late-indexed | G6 | `update\zen22904595.pdf` / `.txt` |
| 22921974 | 2026-09-17 | Jev in Practice: A Composable Python Toolkit for TypeSafe's System One Decision Model | Daniel Ari Friedman | late-indexed | G4, G5 | `update\zen22921974.pdf` / `.txt` |
| 22933883 | 2026-09-24 | Audio-Laya: direct speech-to-decision classification with a frozen Whisper encoder and a trainable projector | Thanabodee Nammungkun | late-indexed | G1, G3 | `update\zen22933883.pdf` / `.txt` (English report) |
| 22935043 | 2026-09-24 | How far can a commercial decision model's probabilities be trusted? A calibration audit of TypeSafe Jev against open and general-purpose classifiers (code and data) | Lingsen Meng | late-indexed | G4, G1 | `update\zen22935043.pdf` / `.txt` (paper from the archive) |
| 22941164 | 2026-09-24 | wev: Distilling LLM Browser Agents into Open, Local System-One Decision Models | Jun Huang; Xin Ren | late-indexed | G6, G3 | `update\zen22941164.pdf` / `.txt` |
| 22945279 | 2026-09-24 | jev-laya-classification-bench: Typed-decision models versus an LLM on 12,000 federal IT solicitations | Bhushan Kinge | late-indexed | G4, G6 | `update\zen22945279.txt` (+ `.zip`; no PDF) |
| 22979052 | 2026-09-26 | Sev Arabic Preview v0.1 | Ali Asiri | late-indexed | G3 (weak) | `update\zen22979052.txt` (+ `.zip`; no PDF) |
| 23005202 | 2026-09-28 | Reflex-1: frontier-LLM accuracy at Jev speed with a 4B open model | Gosuke Suzuki | late-indexed | G1, G3 | `update\zen23005202.txt` (+ `.zip`; no PDF) |
| 23047544 | 2026-09-29 | Epistemic Calibration and Latency Advantages of System One Probabilistic Agents in Limit Order Book Microstructure | Nathan Prados Tapia | late-indexed | G4, G6 | `update\zen23047544.pdf` / `.txt` |
| 23050542 | 2026-09-30 | titan-sr-jev-replication: TypeSafe Jev screening of the TITAN-SR external validation set (22 Cochrane reviews) | Yuki Kataoka | late-indexed | G1, G6 | `update\zen23050542.txt` (+ `.zip`; no PDF) |
| 23075657 | 2026-10-01 | Jev and adapted encoders on ToxicChat: operating-point comparison and incomplete budget evidence | Takahiro Hagino | late-indexed | G1, G6 | `update\zen23075657.pdf` / `.txt` |
| 23088660 | 2026-10-01 | Confidence-gated reranking with Jev raises domain-name segmentation accuracy | Wang Xiaolei; Liu Yuan | late-indexed | G6, G4 | `update\zen23088660.pdf` / `.txt` |
| 23094322 | 2026-10-01 | Measuring Institutional AI Research in India | Chintan Dave | late-indexed (via companion) | G7, G4 | `update\zen23094322.pdf` / `.txt` |
| 23154999 | 2026-09-30 | Institution-Specific Local AI for Network Defense: Intrusion Detection and Graduated Response with a Local Decision Model and RAD | Muhammed Fatih Cingil | late-indexed | G1, G6 | `update\zen23154999.pdf` / `.txt` |
| 23094628 | 2026-10-02 | Yway: A Burmese System One Decision Model | Aung Thu Hein | post-window | G3, G4 | `update\zen23094628.pdf` / `.txt` |
| 23119392 | 2026-10-03 | How well does a Pointwise Mutual Information threshold identify questionable Wikidata Biomedical Relations | Houcemeddine Turki | post-window | G7, G4 (repeatability) | `update\zen23119392.pdf` / `.txt` (paper from the archive) |
| 23123503 | 2026-10-03 | Paraphrastic Resistance: Text Fragility Is Not Decision Instability | Jose Lopez Lopez | post-window (web version 09-27?) | G3 | `update\zen23123503.pdf` / `.txt` |
| 23138396 | 2026-10-04 | Continuous Cheat Detection with Calibrated Decision Models | Heath Howren | post-window, non-empirical | G6, G1 | `update\zen23138396.pdf` / `.txt` |
| 23179064 | 2026-10-06 | Calibrated Decisions Are Not Calibrated Probabilities: An Exact-Target Audit of Jev and Three Open Decision Models | Mohit Shankar Velu | post-window | G4, G3 | `update\zen23179064.pdf` / `.txt` (v2) |
| 23186353 | 2026-10-06 | Noma: An Open System One Decision Model from a Sliced Decoder and Trained Heads | Atul Saxena; Divyanshi Sharma | post-window | G4 | `update\zen23186353.pdf` / `.txt` |
| 23187206 | 2026-10-06 | Paraphrastic Resistance Index (IRP) vs. Typed Decision System | Jose Lopez Lopez | post-window | G1, G5 | `update\zen23187206.pdf` / `.txt` |
| 23189584 | 2026-10-06 | Jev Runtime-Governance PoC | Ryoji Inoue | post-window | G5, G6 | `update\zen23189584.txt` (+ `.zip`; no PDF) |
| 23200782 | 2026-10-07 | Evaluating Typed Per-Turn Supervision for Software-Engineering Agents | Omar Ramadan; Tidjane Tall | post-window | G6 | `update\zen23200782.pdf` / `.txt` |
| 23221456 | 2026-10-07 | System-One Control Bench (report: Evaluating Non-Generative Decision Models in Sequential Gridworld Tasks) | Mateus Pereira | post-window | G6 | `update\zen23221456.pdf` / `.txt` (report from the archive) |
| 23225893 | 2026-10-08 | Who May Sign? Typed, Calibrated Decisions on Company Representation Rules in the Austrian Commercial Register | Ali Ildan | post-window | G4, G3 | `update\zen23225893.pdf` / `.txt` |

Notes for coders:
- **Same author line as a main-window record:**
  - 23123503 and 23187206 come from the same author as Z-23065532, and 23123503 reuses Z-23065532's Laya data.
  - 23075657 has the same author as Z-22885291, but it is a separate study.
- **Hosted Jev measured:** 22886178, 22921974, 22935043, 22945279, 23005202, 23047544, 23050542, 23075657, 23088660, 23094322, 23119392, 23179064, 23189584, 23200782, 23221456.
- **Open or Jev-like models only:** 22904595, 22933883, 22941164, 22979052, 23094628, 23123503, 23154999, 23186353, 23187206, 23225893. (22945279, 23005202, 23179064 and 23221456 also measure open models.)

## 4. Grey literature (items added after 1 October)

| Item | URL | Date | Description | Decision |
|---|---|---|---|---|
| All about Jev (tracker) | https://hanxiao.io/all-about-jev/ | `dateModified` 2026-09-27 | Still 2,073 entries, the same count as cited in §3. Temporal coverage ends 2026-09-27, so no entries were added after 1 October. | nothing to screen |
| Trio-Spark v1.0 (MachineFi) | https://huggingface.co/MachineFi/Trio-Spark-v1.0 (added to Awesome System One Models, commit a31a039, 2026-10-05) | released 2026-09-30 | A second hosted typed model (Choice with Noul/Score projections). The entry records vendor documentation and vendor-reported numbers only. An independent JevBench evaluation is "queued" (fstandhartinger/jevbench#166) and had not been published. | exclude (vendor docs; appended to the exclusion CSV as `grey,trio-spark-v1.0`). Worth mentioning as context: a second hosted model now exists. |
| arXiv:2610.00346 link | https://github.com/pozapas/awesome-system-one-models (commit 0d98a97, 2026-10-02) | 2026-10-02 | Links the companion benchmark paper (Rafe and Das). | not grey; already included from the 4 Oct arXiv re-run |
| Jev in the Wild (arXiv 2609.30216) | same repo, PR #1 merged 2026-10-02 (commit 9fad421) | 2026-10-02 | Registry entry for an arXiv paper (214th registry paper). | not grey; already in `data/papers.csv` |

Awesome System One Models: the commit feed shows three commits after 1 October (above). The README badge still reads "cutoff 2026-09-24". **No grey item qualifies for inclusion.**
