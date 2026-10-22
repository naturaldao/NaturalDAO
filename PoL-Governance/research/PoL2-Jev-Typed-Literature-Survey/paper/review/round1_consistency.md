# Round 1: consistency lens (NEW-cons)

Reviewer lens: internal consistency, definitions, counts, cross-references, LaTeX log.
Sources checked: `main.tex`, `sections/*.tex`, `main.log`, `main.aux`, `main.pdf` (pdftotext), `figures/src/*.py`, `../data/*.csv`, `arxiv_metadata.txt`, `gen_catalogue.py`, `grey.bib`.
Line numbers are the line numbers in each source file.

## Table of repeated quantities

| # | Quantity | Locations | Consistent? |
|---|----------|-----------|-------------|
| 1 | 65 arXiv papers | `main.tex:46` (\nArxiv); abstract:3; intro:8, :39; method:44, :46, :79; `plot_prisma.py:70` (36 + 29); `papers.csv` (65 rows with arxiv_id); `pol2_mapping.csv` (65 rows); `B_catalogue.tex` (65 arXiv + 1 alphaXiv rows); `arxiv_metadata.txt` | Y |
| 2 | 29 other preprints = 28 Zenodo + 1 alphaXiv | `main.tex:47-48`; abstract:3; intro:8; method:47, :54 (method text); `plot_prisma.py:72,74`; `plot_corpus.py` legend (n=29); `zenodo_preprints.csv` (28 rows); `papers.csv` (1 row without arxiv_id) | Y (count). But "preprints" label is not accurate for all 28 rows, see NEW-cons-9 |
| 3 | 11 grey-literature sources | `main.tex:50`; abstract:3; intro:8, :39; `plot_prisma.py:67,74`; `grey_literature.csv` (11 rows) | Y (count). Composition inconsistent with inclusion rule, see NEW-cons-10 |
| 4 | 94 preprints / 105 documents / "more than three times" the 28 papers of arx32160 | `main.tex:49`; intro:34, :39 | Y (105/28 = 3.75) |
| 5 | 28 PoL2 clauses cited and quoted | `main.tex:51`; intro:39; `A_concordance.tex` (31 rows, 28 distinct labels) | Count Y; "cited" N, see NEW-cons-6 |
| 6 | Time window: 16 days | abstract:3 ("sixteen days"); intro:8; method:38, :69; limitations `08_conclusion.tex:4` ("16 days"); conclusion `08_conclusion.tex:25` ("first two weeks") | N (NEW-cons-14) |
| 7 | Median zero-shot AUROC 0.886 over 31 benchmarks | abstract:4; `04_evidence.tex:13`; `evidence_coding.csv`; `papers.csv` note | Y |
| 8 | 63x lower cost than LLM judges | abstract:4; `02_background.tex:36`; `04_evidence.tex:13` | Value Y; condition N (19 vs 31 benchmarks), NEW-cons-4 |
| 9 | Median F1 0.706 at 0.5 vs 0.822 fitted | abstract:5; `04_evidence.tex:22`; `plot_fragility.py:14` | Y |
| 10 | TensorTrust F1 0.158 vs 0.947 (threshold 0.35) | `04_evidence.tex:23`, :392; `plot_fragility.py:16`; `evidence_coding.csv` | Y |
| 11 | Jev AUC 0.815 -> 0.581; Laya 0.938 -> 0.232 | abstract:5; `04_evidence.tex:127,129,387`; `plot_fragility.py:33`; `C_corrections.tex:23` (v0.1 "0.94 -> 0.23") | Y |
| 12 | Name-swap flips: Laya 76.9% vs 6.5%, Open-Jev 19.5%, Jev 32.5% | `04_evidence.tex:127-129`; `C_corrections.tex:23`; `plot_fragility.py:28-30` | Y |
| 13 | Unverified opinion flips 12.1% of decisions | abstract:5; `04_evidence.tex:87,389`; `evidence_coding.csv` | Value Y; comparator N ("authority" vs "injected command"), NEW-cons-5 |
| 14 | JevOut 61.4% (312/508), 229 at p>=0.7; others 64.9-73.2% | `04_evidence.tex:78-79,388`; `plot_fragility.py:20-23` (185/285 = 64.9%, 240/328 = 73.2%) | Y |
| 15 | "I don't know" chosen for 10.5% ("one in ten") | abstract:5; `04_evidence.tex:219,397`; `05_synthesis.tex:20`; `evidence_coding.csv` | Y |
| 16 | Peer judges repeat 96.0% (242/252) vs 50.3% independent | abstract:5; `04_evidence.tex:299,402`; `plot_escalation.py:264` | Y |
| 17 | Cascade gain at most 1.5 points; below best judge on 6 of 9 panels | `04_evidence.tex:300,402`; `C_corrections.tex:30`; `plot_escalation.py:267-268`; fig caption `04_evidence.tex:333` | Y |
| 18 | 130 implicit injections missed; 130 misses at conf >= 0.95; judges catch <= 5 | `04_evidence.tex:33,310,390`; `05_synthesis.tex:33`; CSV | Y |
| 19 | JEV-as-a-Judge: +0.93 (CI 0.24-1.66) at 41.4%; JudgeBench -0.74; live 75.5% | `04_evidence.tex:291-293`; `C_corrections.tex:29` ("+0.9 at 41%"); `plot_escalation.py:257-261` | Y |
| 20 | Check Point 25/27; $0.56 -> $4.39 | `04_evidence.tex:94,96,391`; `C_corrections.tex:36`; `grey_literature.csv` | Y |
| 21 | Simmons: "White" 51%, 6 of 8 traits, mean "yes" ~3% | `04_evidence.tex:144-145,393`; `C_corrections.tex:37`; `grey_literature.csv` | Y |
| 22 | Empathy: 78% at conf >= 0.9, acc 0.383, all 0.371, base 0.333, ECE 0.538 | `04_evidence.tex:151,394`; `plot_honesty.py:162`; fig caption :241 | Y |
| 23 | Negation coherence 0.064 (CI 0.055-0.072), noise 0.013, "five times"; 0.142 vs 0.018 | `04_evidence.tex:205,207,395`; `plot_honesty.py:140-146` | Values Y; figure reference N, NEW-cons-17 |
| 24 | Sys1Cal soft accuracy 0.771 / 0.903 / 0.978 | `04_evidence.tex:216`; `C_corrections.tex:24`; `plot_honesty.py:149-151` | Y |
| 25 | Recalibration ECE 0.0231 -> 0.0069 (3.3x); 0.1235 -> 0.0077 | `04_evidence.tex:194-195`; `plot_honesty.py:156,158` | Values Y; condition (in-sample vs out-of-sample) N, NEW-cons-18 |
| 26 | ChaosNLI ECE 0.076 -> 0.339 | `04_evidence.tex:200,398`; CSV | Y |
| 27 | Interfaces disagree on 32.8% ("about a third") | `04_evidence.tex:209,265,401`; CSV | Y |
| 28 | ANLI middle option 38.8% of predictions, 51.3% of errors | `04_evidence.tex:135,400` | Y |
| 29 | Saudi personas 87% (English) / 62% (Arabic) | `04_evidence.tex:167,399` | Y |
| 30 | arx32160: 28 papers, 19-24 Sep; 14 items, 9 scored; 5/26, 1/27 | intro:33,35; `02_background.tex:38`; `04_evidence.tex:132,270-272,404`; `06_design.tex:34` | Y |
| 31 | KITE 41% effect-error reduction, secondary endpoint | `04_evidence.tex:343-344`; `C_corrections.tex:34` | Y |
| 32 | 2,170 projects in first week / by 22 Sep | `02_background.tex:15`; `04_evidence.tex:362` | Y |
| 33 | Trackers: 2,073 records / 52 papers; 213 papers / 27 graded (15 + 12) | method:34-35; `plot_prisma.py:64`; `08_conclusion.tex:5` | Y |
| 34 | arXiv PRISMA: 607 / 406 / 329 / 77 / 37 / 40 / 5 / 35 / 5 / 30 / 1 / 29 / 65 | method:43-46; `plot_prisma.py:40-70` | Arithmetic Y except the 37th "already in corpus" record, N (NEW-cons-8) |
| 35 | Zenodo PRISMA: ~330 / 62 (61 + 1) / 21 (6+5+9+1) / 41 / 13 / 28 | method:47; `plot_prisma.py:53-72` | Y (but see NEW-cons-9, NEW-cons-11) |
| 36 | 14 missed papers submitted 25-27 Sep | method:45; `gen_catalogue.py` v0.2 additions with those dates (14) | Y |
| 37 | 18 arXiv queries, 11 Zenodo queries | method:36-37; `D_codebook.tex` lists (18, 11); `plot_prisma.py:40,53` | Y |
| 38 | 36 v0.1 papers | method:44; `plot_prisma.py:43,70`; `gen_catalogue.py` v0.1 block (36 arXiv + A-RAG) | Y |
| 39 | 41 Creative-Commons PDFs redistributed | `09_statements.tex:15`; `papers.csv` pdf_in_repo = yes (41) | Y |
| 40 | Seven design elements | `06_design.tex:15-24`; `plot_architecture.py` boxes 1-7; fig caption `06_design.tex:11`; conclusion `08_conclusion.tex:31` | Text/figure Y; conclusion summary N (NEW-cons-20) |
| 41 | Five tensions T1-T5 | intro:41; `05_synthesis.tex`; `plot_framework.py:115-121`; abstract:6; conclusion `08_conclusion.tex:29-30` | Y (names and order match) |
| 42 | Evidence tallies per axis (S/Q/N) | `plot_framework.py` reading `evidence_coding.csv`: G1 2/10/1, G2 0/2/6, G3 0/10/9, G4 1/16/8, G5 0/7/3, G6 0/12/5, G7 0/8/3; rendered `fig_framework.png` | Y (figure matches CSV). Fig. 2(b) counts differ (G4 27, G5 14, G6 18) because essays are kept there; explained by caption |
| 43 | Axes most covered: G4, G3, G6 | method:69; Fig. 2(b) (27, 19, 18) | Y |
| 44 | 52 pages, 7 figures | `arxiv_metadata.txt`; `main.log:2172` (52 pages); 7 `figure` labels in `main.aux` | Y |
| 45 | Abstract 1598 characters | `arxiv_metadata.txt` (recounted: 1598) | Y |
| 46 | Vendor example 0.72 / 0.47 | `02_background.tex:31`; `04_evidence.tex:208` | Y |
| 47 | Confidence gate at 0.8 lets 24.1% of flips through | `04_evidence.tex:89`; CSV | Y |
| 48 | Commit 5791ae3 (1 Oct) / 2e094d3 (27 Sep) | `02b_pol2.tex:5-6`; `03_method.tex:13`; `A_concordance.tex:5`; `C_corrections.tex:41` | Y |

---

## Findings

### NEW-cons-1 [major]
- Location: `sections/00_abstract.tex:3`; `sections/01_introduction.tex:40`. Other locations: `sections/03_method.tex:85`, `sections/08_conclusion.tex:8`, `sections/B_catalogue.tex:83`.
- Problem: The abstract says the corpus was "checked against full texts", and Contribution 2 says "Every quantitative claim about a study was checked against its full text or live source". Section 3.3 and the Limitations say the opposite for 29 of the 94 preprints: the 28 Zenodo items were checked only against record descriptions and the alphaXiv paper only against its abstract.
- Evidence: `evidence_coding.csv` has 39 rows verified at "record description" and 1 at "abstract", against 61 at "full text" and 9 at "live source". The method text says the Zenodo preprints were "verified against their record descriptions but not their full texts".
- Suggested fix: Abstract: "...checked against full texts (arXiv) or record descriptions (Zenodo, marked)...". Contribution 2: "Every quantitative claim about an arXiv study or grey-literature source was checked against its full text or live source; Zenodo and alphaXiv items were checked at record or abstract level and are marked ‡."

### NEW-cons-2 [major]
- Location: `sections/04_evidence.tex:378` (tab:negative); `sections/06_design.tex:36` (tab:checklist). Evidence in `main.aux`.
- Problem: Both `[t]` tables float past the bibliography. Table 2 is placed on p. 42 and Table 3 on p. 43, after the references (pp. 29-41), although they are introduced on pp. 22 and 25. The Conclusion also comes before the checklist it summarises.
- Evidence: `main.aux` has `tab:negative` -> page 42 and `tab:checklist` -> page 43. `sec:negative` is on page 22 and `sec:design` on page 25.
- Suggested fix: Use `[!htbp]` or `[p]`, and/or put `\FloatBarrier` (placeins) before `\section{Open problems}` and before the bibliography. You could also make Table 2 a `longtable` or `tabularx` inside a `\begin{table}[p]`. Recompile and confirm that both tables come before page 29.

### NEW-cons-3 [major]
- Location: `sections/D_codebook.tex:7` (S example), `data/evidence_coding.csv` row `arx34862,G1,S`. Other locations: `sections/04_evidence.tex:26-28`, `sections/C_corrections.tex:26`.
- Problem: The codebook's own worked example for S contradicts its definitions. S requires "without conditions that would change a deployment decision", and Q covers results that are "mixed across tasks". For arx34862 the text says that Jev "won on only two of the four benchmarks", had lower precision (77.1 vs 91.9), and was tested on saved traces rather than as a pre-execution gate. Correction C also downgrades it. By the stated rules this is Q.
- Evidence: Quoted text at the lines above. The S code is one of only 2 S codes on G1 in Fig. 6.
- Suggested fix: Recode `arx34862,G1` to Q (the G1 bar becomes 1/11/1) and regenerate fig_framework. Choose another S example, e.g. `grazian` G4 (ECE 0.027), or say the codebook has no unconditional S example. Alternatively, rewrite the S definition so that it admits mixed-but-favourable results, and apply the same rule to the other rows.

### NEW-cons-4 [minor]
- Location: `sections/00_abstract.tex:4`. Other location: `sections/04_evidence.tex:13`.
- Problem: The abstract attaches "at 63x lower cost than LLM judges" to "median zero-shot AUROC 0.886 across 31 alignment-failure benchmarks", so the reader assumes both are measured on the same set. In the text, the cost ratio is for "one pass over the 19 benchmarks scored by an API LLM judge" ($0.30 vs $18.96). The text also never says why AUROC covers 31 of the 44 benchmarks.
- Evidence: `04_evidence.tex:12-13`: "44 benchmarks"; "over 31 benchmarks"; "19 benchmarks scored by an API LLM judge".
- Suggested fix: Abstract: "(median zero-shot AUROC 0.886 across 31 alignment-failure benchmarks; 63x cheaper than LLM-judge scorers on the 19 benchmarks they score)". In §4.1, add a clause explaining 31 of 44 (e.g. "benchmarks with both classes present").

### NEW-cons-5 [minor]
- Location: `sections/04_evidence.tex:103` (G2 polbox). Other locations: `sections/04_evidence.tex:83,87,389`; `data/evidence_coding.csv` row `arx31142,G2`.
- Problem: The comparator for the 12.1% opinion attack is given in three different ways. The text and Table 2 say it is "statistically tied with impersonating an authority (10.1%)". The polbox says it "moved Jev as much as an injected command". The paragraph title says "An opinion is as strong as a command", and the CSV rationale says "tied with strongest injected command".
- Evidence: Quotes above.
- Suggested fix: Pick the comparator the source supports, probably authority impersonation, and use it everywhere: retitle to "An opinion is as strong as an authority claim", change the polbox to "as much as impersonating an authority", and fix the CSV rationale.

### NEW-cons-6 [major]
- Location: `sections/05_synthesis.tex:11`; `sections/02b_pol2.tex:6,19,20,28,33`; `sections/05_synthesis.tex:14`. Other location: `sections/A_concordance.tex`.
- Problem: Appendix A says it "quotes every PoL2 clause cited". Several claims attributed to clauses are not in the quoted excerpts, so readers cannot check them:
  - (a) T1's central quote, §4.3.3.1 "understand human emotional states and processes" (`05:11`). The §4.3.3.1 row only covers calibration, self-reflection and truncation. T1 rests on this quote.
  - (b) §4.3.2 "graded management for fiction and games and an explicit carve-out for safety warnings" (`02b:19`, also `02b:6`) and §4.3.2 "fabricated intimacy... manipulation" (`05:14`).
  - (c) §4.3.3 "support repair after conflict" (`02b:20`). The row only quotes boundary records.
  - (d) §5.4.1 "blocked at the input and suppressed at the output" (`02b:28`).
  - (e) Art. 4 "keep resource flows auditable and give comprehensible explanations when questioned" (`02b:33`). The Art. 4 row has neither, and the explanation duty is Art. 9(2) elsewhere (see NEW-cons-7).
  - (f) §4.3 "fleeting, individual, context-sensitive and touches on human dignity" (`02b:22`, `05:10`). Only the first sentence is quoted.
- Evidence: Compare the quoted rows `A_concordance.tex:27-37` with the sentences above.
- Suggested fix: Add the missing Chinese excerpts (with "……" joins) to the existing rows, especially the §4.3.3.1 emotion-understanding item and the §4.3.2 fiction/games/safety and fabricated-intimacy items. Alternatively, drop the claims that are not quoted.

### NEW-cons-7 [minor]
- Location: `sections/02b_pol2.tex:33`. Other locations: `sections/03_method.tex:23`, `sections/04_evidence.tex:249`, `sections/05_synthesis.tex:47`, `sections/07_agenda.tex:24`, `sections/A_concordance.tex:42,48`.
- Problem: The duty to give comprehensible explanations when questioned is attributed to Art. 4 in §2.2 but to Art. 9(2) everywhere else. Appendix A has it only under Art. 9(2) ("解释义务").
- Evidence: `02b:33` "...give comprehensible explanations when questioned (\art{4})" vs `04:249` "\art{9}(2) requires a comprehensible explanation on request".
- Suggested fix: In `02b:33`, cite Art. 9(2) for explanations (or quote the Art. 4 wording in Appendix A if Art. 4 really contains it).

### NEW-cons-8 [minor]
- Location: `sections/03_method.tex:44`; `figures/src/plot_prisma.py:43`.
- Problem: "37 records were already in the corpus, including all 36 papers of version 0.1", but the included total is 36 + 29 = 65 (`plot_prisma.py:70`). The 37th record is not accounted for. The figure box also says "37 already in v0.1 corpus", which contradicts "36 v0.1 papers" in the same box.
- Evidence: Arithmetic. `gen_catalogue.py` lists 36 arXiv v0.1 papers plus A-RAG (not on arXiv).
- Suggested fix: Say what the 37th record is (e.g. a second arXiv version, or a record already excluded in v0.1) and add it to the exclusion box. Change the figure wording to "37 already known (36 v0.1 papers + 1 ...)".

### NEW-cons-9 [minor]
- Location: `sections/03_method.tex:47`; `sections/B_catalogue.tex:83,87,105,107,111`; `data/zenodo_preprints.csv`. Other locations: abstract:3, `plot_prisma.py:58,72`, `04_evidence.tex:381`.
- Problem: The 28 Zenodo items are called "preprints" and "substantive studies that bear on a governance axis". The CSV and Appendix B type them as 14 preprints, 2 datasets, 3 technical notes, 2 articles, 2 publications, 1 working paper, 2 software deposits, 1 essay and 1 "other" (an AI-assisted dialogue). The PRISMA flow excluded "companion deposits 5". Yet the dataset `zen22998941` (four-model comparison by the author of `zen22952571`) looks like a companion deposit and is retained.
- Evidence: `zenodo_preprints.csv` `type` column; Z-22998941 and Z-22952571 have the same author and topic.
- Suggested fix: Either call the class "Zenodo records (preprints, notes, datasets, essays)" throughout, or exclude the dataset and essay items and recount (this changes \nZenodo, \nOther, \nPapers, abstract, Fig. 1, Fig. 2, Fig. 6). Also say why `zen22998941` is not a companion deposit.

### NEW-cons-10 [minor]
- Location: `sections/03_method.tex:62` (inclusion of grey literature "when it reports original measurements"). Other locations: `data/grey_literature.csv`, `grey.bib`, `plot_prisma.py:67`.
- Problem: The 11 counted grey sources include the two trackers (All about Jev, Awesome System One Models). These have no axes and report no original measurements. Meanwhile, five vendor documents in `grey.bib` (`typesafe_primer`, `typesafe_models`, `typesafe_jaggedness`, `typesafe_intro`, `almeida2026introducing`) are cited as evidence (e.g. the 0.72/0.47 example, the nine failure modes, the language-support statement) but are not counted. The method text names "vendor documentation" as an included grey type.
- Evidence: `grey_literature.csv` rows G-Tracker and G-ASOM have an empty `pol_axes`. `grey.bib` has 16 entries.
- Suggested fix: Count the trackers as retrieval routes rather than grey sources, and either count the vendor documents as grey evidence or state explicitly that vendor documentation is cited as context and not counted. Update \nGrey and all counts.

### NEW-cons-11 [minor]
- Location: `sections/03_method.tex:47` ("13 applications and tools are listed in the data release only"). Other location: `sections/09_statements.tex:15`.
- Problem: No file in `data/` lists these 13 items. The data statement lists only `papers.csv`, `zenodo_preprints.csv`, `grey_literature.csv` and `evidence_coding.csv`, and the 21 excluded Zenodo records are not listed either.
- Evidence: `ls data/`: no such file. A text search finds no "tool-only" or "applications" list.
- Suggested fix: Add `data/zenodo_excluded_or_tools.csv` (id, reason) and name it in the Data availability statement, or delete the claim.

### NEW-cons-12 [minor]
- Location: `sections/03_method.tex:60` (inclusion criterion: object, component or comparator is a typed model). Other locations: `sections/B_catalogue.tex:41,63`, `sections/C_corrections.tex:27`, `data/evidence_coding.csv` row `arx22664,G1,Q`.
- Problem: Two corpus papers measure no typed model: arx22664 is Model "--" ("does not use Jev at all") and arx25498 is "--". Both still count toward the 65, and arx22664 is coded Q on G1. This contradicts the inclusion rule. A Q code ("achievable only under stated conditions") also does not fit a paper with no typed model.
- Evidence: Quotes above.
- Suggested fix: Either broaden the inclusion rule ("...or a harness/system designed around one") or move these papers to context and recount (65 -> 63). Recode arx22664 as non-empirical for typed models (excluded from the tally).

### NEW-cons-13 [minor]
- Location: `sections/01_introduction.tex:39`; `main.tex:51`.
- Problem: "We... map 94 preprints and 11 grey-literature sources onto [seven axes]" and "28 clauses are cited". In fact:
  - 23 background-tier arXiv papers and 2 grey trackers have no axis. Only 80 documents are coded (`evidence_coding.csv`: 80 distinct docs).
  - §4.3.3.2, Art. 6(3), Art. 9(3) and Art. 11(2) appear only in Appendix A. The body cites Art. 6, Art. 9 and Art. 11 without sub-items and never cites §4.3.3.2.
- Evidence: CSV counts. Clause-reference scan of `sections/0*.tex`.
- Suggested fix: "map the 80 documents that bear on a governance axis (of 105 retrieved)". For clauses, either cite the sub-items in the body (Art. 6(3) at `02b:35`, Art. 9(3) at `02b:36`, Art. 11(2) at `05:35`, and use §4.3.3.2 or drop its row), or say "28 clauses are quoted in Appendix A".

### NEW-cons-14 [minor]
- Location: `sections/08_conclusion.tex:25` ("The first two weeks of evidence"). Other locations: abstract:3, intro:8, `08_conclusion.tex:4`, `07_agenda.tex:30` ("most studies come from a single team in a single week").
- Problem: The time window is given as sixteen days, 16 days, two weeks and a single week. The agenda sentence also contradicts intro:57 ("many of them small, single-author studies"), because "most studies come from a single team" reads as one team writing most studies.
- Suggested fix: Use "first sixteen days" in the conclusion. Rewrite the agenda sentence as "most findings come from a single study by a single team, posted within days of release".

### NEW-cons-15 [minor]
- Location: `sections/01_introduction.tex:34`.
- Problem: The claim that this survey, unlike arx32160 (papers of 19-24 Sep), includes "the first adversarial, abstention and coherence studies" conflicts with the catalogue dates. The adversarial studies arx28613 (09-23) and arx30243 (09-24) fall inside arx32160's window.
- Evidence: `B_catalogue.tex:18-19`.
- Suggested fix: "including the first studies of opinion attacks, abstention and probabilistic coherence" (arx31142, arx34024, arx33209/33971 are all on or after 25 Sep), or "including most of the adversarial...".

### NEW-cons-16 [minor]
- Location: `sections/01_introduction.tex:40` (`\cref{sec:evidence}`).
- Problem: The corrections to v0.1 are listed in Appendix C (`tab:corrections`), not in Section 4.
- Suggested fix: Replace with `\cref{app:corrections}`.

### NEW-cons-17 [minor]
- Location: `sections/04_evidence.tex:207` ("...0.142 when its score was near 0.5 versus 0.018 when it was near 0 or 1 (\cref{fig:honesty}a)").
- Problem: Panel (a) of Fig. 4 shows only the three model means (0.064, 0.122, 0.293) and the 0.013 noise floor. The by-confidence values are defined in `plot_honesty.py:146` (`by_confidence`) but never plotted. The caption (`04_evidence.tex:238`) describes only the means.
- Suggested fix: Move the cross-reference to the sentence with 0.064 (`:205`), or add the two by-confidence bars to panel (a) and mention them in the caption.

### NEW-cons-18 [minor]
- Location: `sections/04_evidence.tex:194`. Other location: `figures/src/plot_honesty.py:155,209`.
- Problem: The text says "pooled recalibration on the same labels reduced ECE from 0.0231 to 0.0069", which reads as in-sample. The figure legend calls the same number "Recalibrated (out-of-sample)", and the script comment says "out-of-fold". Line 197 of the text warns that ECE values differ in whether they are in or out of sample, so the condition matters.
- Suggested fix: "pooled out-of-fold recalibration on these labels reduced ECE...".

### NEW-cons-19 [minor]
- Location: `sections/04_evidence.tex:114` (Fig. 3 caption). Other location: `sections/04_evidence.tex:5`.
- Problem: (a) The caption explains "Von" in the sentence for panel (d), but Von appears only in panel (b). (b) The caption says "Jev (hosted)" is TypeSafe's API "whose version these studies do not report". §4 opens with "Unless stated otherwise, 'Jev' means the hosted jev-1.13 model". The reader cannot tell whether these results are jev-1.13. (c) Panel (b) labels the JevOut replica "Open-source Jev", panel (c) has "OpenJev", the text has "Open-Jev" (a DeBERTa encoder, `02_background.tex:24`), and arx23959's title says "Open-Jev" for a Qwen3-4B model the text calls "JevLite" (`04_evidence.tex:40`, `B_catalogue.tex:42`). Four different systems share near-identical names.
- Suggested fix: Move the Von note to the (b) sentence. Change §4:5 to "...means hosted Jev (jev-1.13 where the study reports a version)". Rename panel (b) to "JevOut open replica", panel (c) to "Open-Jev", and add one sentence noting that arx23959's "Open-Jev" is JevLite, not the DeBERTa model.

### NEW-cons-20 [minor]
- Location: `sections/08_conclusion.tex:31`. Other locations: `sections/06_design.tex:15-24`; `figures/src/plot_architecture.py`; abstract:6; intro:29.
- Problem: §6 lists seven elements, matching Fig. 7 boxes 1-7. The conclusion's summary of "the engineering agenda" lists six items that do not map onto them: it omits element 1 (give the detector the reference) and element 2 (enforce scope in code), and it splits element 3 into "three-valued questions" and "neutral and tested option names". The intro thesis (`01:29`) also lists "inputs are paired with their reference", but the abstract's conditions omit it.
- Suggested fix: Rewrite the conclusion sentence to follow the seven elements in order, e.g. "...pairing inputs with their reference, enforcing scope in code, independent three-valued detectors with tested neutral names, local calibration with private probabilities, reversible action only on agreement, human review of confident decisions, and a public decision record". Add "inputs paired with their reference" to the abstract's conditions or drop it from the intro thesis.

### NEW-cons-21 [minor]
- Location: `sections/06_design.tex:6` (compatibility claim). Other locations: `sections/06_design.tex:21`, `plot_architecture.py:47`.
- Problem: §6 says the design is "compatible with the pilot protocol..., which already distinguishes... the actions allow, repair, block, clarify and review". The design then adds a new action, "hold" (temporary), which is not one of the pilot actions, and makes "block" final only after confirmation.
- Suggested fix: Say that the design adds a temporary "hold" state to the pilot's action set, or map "hold" onto an existing pilot action (e.g. "review").

### NEW-cons-22 [minor]
- Location: `sections/06_design.tex:34` and `tab:checklist` (`06_design.tex:39-60`).
- Problem: "It extends the 14-item checklist of arx32160". The table has 15 rows, of which 7 are marked as added for PoL2 (5, 7a, 8, 9, 10, 11a, 12), so only 8 items are inherited. The reader cannot tell how the 14 original items were merged or dropped. The "7a"/"11a" numbering also looks like an artefact of revision. The caption says "Basis gives the evidence", but item 12's basis is two clauses (Art. 4, §5.5), not evidence.
- Suggested fix: State the mapping ("the 14 items of [arx32160] are merged into items 1-4, 6, 7, 11 and 13"), renumber 1-15, and change the caption to "Basis gives the evidence or clause".

### NEW-cons-23 [minor]
- Location: `figures/src/plot_framework.py:83-95` (clause column). Other location: `sections/03_method.tex:17-25` (tab:clauses).
- Problem: The Fig. 6 clause-to-axis links differ from Table 1:
  - (a) Fig. 6 links "Art. 9 Non-intervention" to G5, but Table 1 grounds G5 in Art. 9(2) (duty to explain), not 9(7).
  - (b) §1.5, a G3 clause in Table 1, is missing from Fig. 6.
  - (c) Chapter 7, a G7 clause, is missing.
  - (d) Fig. 6 links §4.3.3.1 "Hate-lang. truncation" to G4, which Table 1 does not.
  - (e) T3 is linked to G5 and G7, but §5's T3 evidence comes mainly from G3/G4 studies (arx26758, arx36965, arx38850, arx33401).
- Suggested fix: Split the Art. 9 box into "Art. 9(2) Duty to explain" (G5) and "Art. 9(7) Non-intervention" (G6). Add §1.5 to G3. Make the links match Table 1 exactly. Re-derive the tension links from the citations in §5.

### NEW-cons-24 [minor]
- Location: `sections/03_method.tex:23` (Table 1, G5 row). Other locations: `sections/04_evidence.tex:404`; `sections/02b_pol2.tex:36-37`.
- Problem: Clause sub-items are cited inconsistently. Table 1 groups "Art. 5(4)-(5) verifiable decision chain", but Art. 5(4) is "not a black box" (Appendix A) and only 5(5) is the decision chain. Table 2 maps "Typed readout has not yet shown an independent accuracy advantage" to Art. 5(4). §2.2 cites Art. 9 for "unimpeded access" (that is 9(3)) and Art. 11 for the questioning period and archive (11(2), 11(5)).
- Suggested fix: Table 1: "Art. 4 transparency; Art. 5(4) no black box; Art. 5(5) verifiable decision chain". Use 9(3), 11(2) and 11(5) where the specific item is meant. Table 2's last arx32160 row should probably cite Art. 5(5) or §5.4.1.

### NEW-cons-25 [minor]
- Location: `sections/02b_pol2.tex:20`, `sections/03_method.tex:22`, `sections/04_evidence.tex:184` ("behavioural introspection"). Other location: `sections/A_concordance.tex:33` ("Behavioral self-reflection").
- Problem: §2.2 says it follows the official English translation, but it uses "introspection" where Appendix A's official translation says "self-reflection" (行为自省). The same mismatch occurs for Art. 8: "rights of proposal" (`02b:36`) vs "Suggestions at any time" (A:47).
- Suggested fix: Use "behavioural self-reflection" and "suggestion" consistently, or note that these are the author's renderings.

### NEW-cons-26 [minor]
- Location: `sections/01_introduction.tex:12`, `sections/02b_pol2.tex:26` ("around existing large language models", "wraps them"). Other location: `sections/A_concordance.tex:36` (§5.4: "built **inside** existing large language models... application layer **outside** them"; 之内 / 其外).
- Problem: The body says the inner governance layer sits around the LLMs. The quoted clause says inside them. This is a substantive difference for where the safety valve sits.
- Suggested fix: Follow the source: "an inner governance layer built inside existing LLMs (controlling their inputs and outputs)". If "around" is a deliberate interpretation, say so.

### NEW-cons-27 [minor]
- Location: `sections/C_corrections.tex:32`. Other location: `sections/04_evidence.tex:191`.
- Problem: Appendix C says "Jev beat every other single-pass baseline". §4.4 hedges the same result: "numerically above the single-pass baselines, which were scored on the full 1,953-response set" (Jev on 1,718). The two descriptions give different strengths of claim.
- Suggested fix: In Appendix C: "Jev's AUROC was numerically above the single-pass baselines (scored on a larger set)".

### NEW-cons-28 [minor]
- Location: `sections/C_corrections.tex:38`. Other location: `sections/04_evidence.tex:157`.
- Problem: Appendix C says ZH-Decision-Bench v0.1 tested "two Laya models and Qwen3.5-2B". §4.3 refers only to "the open Laya multilingual model". In the same table, "v0.1/v0.2" refers to the benchmark's releases while the column header "Version 0.1 stated" refers to the survey's version, which is ambiguous.
- Suggested fix: Align the model description, and write "release 1 / release 2 (26 / 28 Sep)" for the benchmark.

### NEW-cons-29 [minor]
- Location: `sections/04_evidence.tex:381` (Table 2 caption, "Grey literature is marked †").
- Problem: The † mark is defined and used only in Table 2, for three rows. Grey-literature citations in the body (e.g. `qin2026zhdecisionbench`, `grazian2026calibrated`, `molas2026calibrated`, `yurin2026confident`, `willison2026jev`, `checkpoint2026jev`) are never marked. By contrast, ‡ is applied systematically via \zmark. Table 2 also writes `$^\ddagger$` in the caption but uses `\zmark` in the rows, so a change to the macro would put the two out of sync.
- Suggested fix: Define `\gmark` (†) next to `\zmark` in `main.tex`, explain it in §3.3, and either use it on every grey citation or drop it from Table 2. Use the macros in the caption.

### NEW-cons-30 [minor]
- Location: acronyms. `sections/00_abstract.tex:4-5`; `sections/04_evidence.tex:13,14,21,127,299,310`; `sections/02_background.tex:37`.
- Problem: Several acronyms and terms are never expanded, or switch form:
  - AUROC (abstract:4, `04:13`) and AUC (abstract:5, `04:127`, Fig. 3d) are used for the same metric without definition.
  - ECE first appears at `04:21` and is never expanded.
  - F1 is never defined.
  - NLL (`04:310`) is never expanded.
  - LLM is never expanded (the abstract has "large language models" without "(LLMs)").
  - κ (`04:14`) is not identified as Cohen's (or Fleiss') kappa.
  - "flash-tier" (`02:37`, `04:299`) is undefined jargon.
  - "Kev-0.8B" (`04:90`) is introduced with no description.
  - S/Q/N letter codes appear in App. D but Fig. 6's legend uses words. This is fine, but §3 never introduces the letters.
- Suggested fix: At first body use, write "area under the ROC curve (AUROC)", "expected calibration error (ECE)", "F1 (harmonic mean of precision and recall)", "negative log-likelihood (NLL)", "large language model (LLM)" and "Cohen's κ". Use AUROC throughout (state "AUC = AUROC" if a source uses AUC). Gloss "flash-tier" as "low-cost, low-latency tier of a generative model family" and Kev as "an open 0.8B typed model". In §3, add "(S, Q, N)" after "supporting, qualifying or negative".

### NEW-cons-31 [minor]
- Location: `sections/01_introduction.tex:28` (definition of *judge*). Other locations: abstract:4 ("LLM judges" and "not as judges"), `04_evidence.tex:189` ("AUROC as a judge"), `:289` (JEV-as-a-Judge), `:297-300`, `06_design.tex` element 5.
- Problem: "Judge" is defined as a component whose output alone determines a consequential outcome for a person. It is then used constantly in the LLM-as-a-judge sense (an evaluator of model outputs), including in the abstract next to the defined sense. "Not as judges" and "LLM judges" in the same sentence invite misreading.
- Suggested fix: Italicise *judge* in the defined sense, or rename the generic sense "LLM evaluators" / "LLM graders" outside paper titles. Add a sentence to the definition paragraph noting the other usage.

### NEW-cons-32 [minor]
- Location: `data/evidence_coding.csv`; `data/papers.csv`; `data/grey_literature.csv`.
- Problem: The released data does not join cleanly with the paper, and some coded items are never discussed:
  - (a) Grey IDs differ between files: `checkpoint`, `simmons`, `replication`, `sev`, ... in evidence_coding vs `G-CheckPoint`, `G-Simmons`, `G-Replication`, `G-Sev` in grey_literature.csv. A-RAG is `alphaRAG` vs `A-RAG`.
  - (b) `papers.csv` tiers are in Chinese (核心/相关/背景), while the paper uses Core/Related/Background, and there is no data dictionary.
  - (c) Background paper arx36154 has `pol_axes = G4` but is neither coded nor counted, which contradicts the rule in §3 that background papers inform no axis.
  - (d) Twelve coded items (zen22980293, zen22954807, zen23041163, zen22953637, zen22957049, zen22783171, zen22998941, zen22849329, zen22858286, zen22887464, zen22995519, arx33282, le2026sev/`sev`) count toward Fig. 6's tallies but are never cited in §4-§5. Readers cannot see how they were weighed.
- Suggested fix: Use one ID scheme across the CSVs (or add a `bibkey` column). Add English tier labels. Clear the axis on arx36154 or code it. Either mention the uncited coded items briefly in §4 (one sentence per axis) or state in the Fig. 6 caption that the tally includes items not discussed in the text, with the count.

### NEW-cons-33 [minor]
- Location: `sections/A_concordance.tex:35` (v0.1 column for §4.3.3.3 shows ``3.3.3'' in quotes).
- Problem: All other v0.1 numbers follow the renumbering described in §2.2 (Ch. 5 -> Ch. 4), so this row should read §5.3.3.3. The quoted, prefix-less "3.3.3" is unexplained.
- Suggested fix: Put "§5.3.3.3", or add a footnote saying that v0.1 misnumbered it as "3.3.3".

### NEW-cons-34 [nit]
- Location: `sections/02b_pol2.tex:17` ("The EAP (\clause{4})"); `sections/02b_pol2.tex:32`, `03_method.tex:25` ("Chapter~7").
- Problem: Chapters are written as "§4" in one place and "Chapter 7" in others, and the `\clause` macro is meant for clauses.
- Suggested fix: "The EAP (Chapter~4)".

### NEW-cons-35 [nit]
- Location: `sections/A_concordance.tex:23-53` (English column).
- Problem: The "official translation" column mixes American spelling (behavior, behavioral, optimization) with British (behaviour at A:28, labelling at A:26). This suggests some rows are paraphrased rather than quoted, and it differs from the body's British spelling. Elsewhere, British spelling is consistent in the body (judgement, authorisation, labelling, organisation; no -ize forms found).
- Suggested fix: Reproduce the official translation verbatim in each row, or note "lightly normalised".

### NEW-cons-36 [nit]
- Location: `sections/02_background.tex:22`.
- Problem: Four decoder replicas are named (this-that-model-1.0, JevLite, SemIf, Visual Jev) with three citations. SemIf has no source.
- Suggested fix: Add SemIf's citation, or drop it.

### NEW-cons-37 [nit]
- Location: `figures/src/plot_architecture.py:38` (box 3: "≥2 sources: self-hosted typed model + another family or rule"). Other location: `sections/06_design.tex:17`.
- Problem: Element 3 in the text does not require the typed model to be self-hosted (that is T3's option and checklist item 12). The figure adds the requirement. Fig. 7's caption also says labels give "the axis or tension", but only T4 appears.
- Suggested fix: Add "self-hostable where possible (T3)" to element 3 in the text and "(T3)" to box 3, or drop "self-hosted" from the box.

### NEW-cons-38 [nit]
- Location: `data/evidence_coding.csv` row `arx34963` ("56x lower cost"). Other location: `sections/04_evidence.tex:37` (55.9x).
- Problem: The rounding differs between the CSV and the text.
- Suggested fix: Use "55.9x" in the CSV.

### NEW-cons-39 [minor]
- Location: `main.log:1911-2043` (`sections/B_catalogue.tex:57-79` and `:82-115`).
- Problem: There are 23 overfull hboxes of 5.80pt (the Tier column cannot fit "Background" at `p{0.08\linewidth}`) and 4 overfull alignments of 5.72pt in the Zenodo longtable (column widths sum above `\linewidth`). Both exceed the 5pt threshold. The log also reports 7 "ignored error: Infinite glue shrinkage found in box being split" on pp. 44-50 (longtables in Appendices A-C), plus smaller overfull boxes (1.29pt, A_concordance v0.1 column; 1.54pt, catalogue header "Model"). There are no undefined references or citations, and no font-substitution warnings.
- Evidence: `main.log` lines cited.
- Suggested fix: In `gen_catalogue.py`, widen Tier to `p{0.095\linewidth}` and shrink Title to `p{0.515\linewidth}` (or abbreviate "Bkgd."). Make the Zenodo widths sum to ≤ 0.97\linewidth less the inter-column space (e.g. Title `p{0.52\linewidth}`). The glue-shrinkage messages usually come from `\renewcommand{\arraystretch}` combined with `nosep` lists or `\small` inside `longtable`; check that `\endfoot`/`\endlastfoot` are set and remove any negative vertical skips.

### NEW-cons-40 [nit]
- Location: `sections/03_method.tex:65` (tier assignment: "Each arXiv study was assigned a tier...; Zenodo and grey-literature items were assigned axes only").
- Problem: The alphaXiv paper is given a tier ("Core") in Appendix B (`B_catalogue.tex:26`) and `papers.csv`, which the rule does not cover.
- Suggested fix: "Each arXiv or alphaXiv study...".
