# Round 6: combined review (fidelity, consistency, argument, arXiv moderation)

Scope: main.pdf (65 pp., built 4 Oct 23:55, same time as the newest section files), sections/*.tex, grey.bib, arxiv_metadata.txt, data/*.csv, the PoL2 local copies and the full texts. The only file I edited is this one.

## Status of round-5 findings

| ID | Status | Note |
|---|---|---|
| R5-1 | PARTLY | "The only Chinese benchmark" is gone, and the CJ-Bench result is now reported (11.45% against 3.78%; 92%). The counter-finding the round-5 fix asked for is still missing: after domain fine-tuning, the open specialists were worse calibrated than Jev. See R6-1. |
| R5-2 | FIXED | Table 2 now says "lost no macro-F1, but fewer disguised attacks were flagged". Element 3 says "without loss of macro-F1, although fewer disguised attacks were flagged as non-benign". §4.6 says "on simulated network data … without loss of macro-F1". |
| R5-3 | FIXED | Now "0.93 and 0.96 at nominal 80% and 90%, above nominal and possibly conservative". |
| R5-4 | FIXED | Now "No protocol was written or registered in advance", which is consistent with App. E 24a–c. |
| R5-5 | FIXED | §2.2 now paraphrases \clause{4.3.3.2} ("for people it offers real-time hate-language identification and correction suggestions"). This matches zh_4.md l.123 and en_4.md l.123, under human–human collaborative alignment (PAI-assisted). |
| R5-6 | FIXED | Now "they were also vulnerable". |
| R5-7 | FIXED | §2.1 now cites [7] for the price and [4] for 70–500 ms. |

## Consistency checks (all pass)

- **Abstract.** The arxiv_metadata abstract matches the PDF word for word. The only difference is that pdftotext drops the κ glyph. Length is 1,917 characters.
- **Figure count.** The PDF has 7 figures, as the Comments line states.
- **Tallies.** These are unchanged from round 5 and agree across the answer boxes, Fig. 1b, Fig. 2, Table 5 and §4.8.
- **Table 2 certainty.** 1 moderate / 9 low / 5 very low, which matches §7.
- **App. D and §4.3 on the Chinese repository.** They agree with each other: v0.1 did not test Jev, and v0.2 withdrew the over-confidence reading. grey.bib does not agree with either (R6-2).

## Source claims spot-checked this round (not in the round-4 or round-5 lists)

| # | Source | Claim | Result |
|---|---|---|---|
| 1 | arx36965 | Jev ECE 11.45 vs 3.78 (Table 1); +1.24% relative general accuracy; medicine +3.36 pp (specialist); 92.0% of Jev's average across domains; initialised from Laya Multilingual; Jev version not reported | Correct, apart from the omission and conflation in R6-1 |
| 2 | qin2026zhdecisionbench (README at commit 7cd0164) | n = 323; Jev 1.9% order flips (voice) and 1.7% zh-TW flips; Laya 10.8% (voice) and 20.6% (CS); "Jev needs no refit at all" | Numbers correct; see R6-2 for version labelling and task mixing |
| 3 | arx38827 | 38.8% of predictions and 51.3% of errors on Neutral; balanced candidate positions | Correct |
| 4 | Simmons blog | 6,336 claims; about 3% typical "true"; White 51% of first picks across eight traits; author says order not yet counterbalanced | Correct |
| 5 | arx36399 | Without a persona, answers lie next to its American personas | Correct |
| 6 | Check Point blog | Strongest attacker 25/27, on average at the fourth turn; "untrusted" marking made no meaningful difference; "focused, directional study" | Correct |
| 7 | zen23038928 (Kev-0.8B) | One planted note breaks several answers in a four-question call (risk wrong 48% vs 8% when allow/block flipped) | Correct |
| 8 | zen22959854 | Coverage-based threshold sent every attacked wrong answer to review; fixed 0.8 did not hold | Correct |
| 9 | zen22849329 | Showing Luna Jev's judgment adds 2.0 pt vs 3.5 for a plain second look (no reasoning), nothing extra at high effort, so "no better" | Correct |
| 10 | zen22901853 (Link) | Laya explicit_support 0.9909; no_support 0.3091; LLM 1.0000 on the same items | Correct |
| 11 | bernoulli.app | 738,164 Choice answers; formula (Nx−1)/(N−1), so padding N inflates confidence | Correct |
| 12 | zen23023694 (Blum) | Stable across runs, sensitive to wording | Correct |
| 13 | zen23064668 | Hop-level calibration audits have zero power under regime shift | Correct; matches "per-step calibration audits can miss chain-level error when conditions shift" |
| 14 | zen22848952 | Noul conflict 0.50–0.57 vs ignorance 0.46–0.48; Choice separates "in all four completed cases" | Correct |
| 15 | arx32160 | 14 items (B1–B3, T1–T4, R1–R3, C1–C4); 9 adopted plus 5 not adopted, as listed in §6 | Correct |
| 16 | arx26758 | Question counts: Laya 1,200, Open-Jev 1,800, Jev 1,200 (its Table 6); Jev 32.5%; 24× floor; AUC 81.5 → 58.1 | Fig. 3 caption correct |
| 17 | arx23959 | Non-inferior to an LLM judge (App. E example) | Correct |
| 18 | arx22664 | Assurance obligations are properties of the harness | Correct |
| 19 | Awesome System One Models | "27 graded studies … risk of bias low 0" | Correct. The live README now says 214 papers against the paper's 213 at the 24 Sep cutoff; this is a later update, not a finding |

### Appendix A and arXiv

- **Appendix A.** I re-checked the 4.3.3.1 and 4.3.3.2 rows and the 4.3.3.x headings against zh_4.md and en_4.md, and they are verbatim.
- **arXiv.**
  - Tone is neutral.
  - cs.CY primary with a cs.AI cross-list remains appropriate.
  - The Comments line ("Policy analysis with a documented evidence assessment") describes the original-analysis character accurately. The residual risk under the CS review/position-paper policy is unchanged from earlier rounds (low).

---

### R6-1 [minor] The CJ-Bench sentence reports only Jev's unfavourable calibration and attributes the medicine result to the wrong model

**Location:** 04_evidence.tex l.119 (§4.3 Language), and the parallel clause in §5 T3.

**Problem:**
- **Calibration.** The sentence gives hosted Jev's general-task ECE of 11.45% against 3.78%. It omits that in the specialised domains Jev was the better calibrated model. Its average ECE was 5.57%, against 12.08% for the open specialists. In medicine it was 5.70% against 7.25%. The authors themselves stress this ("the specialists' average ECE remains higher than Jev's", §4.2 of arx36965).
  - As written, the only CJ-Bench calibration evidence for hosted Jev in Chinese, the language of the PoL2 construct, is the unfavourable half.
  - This is selective reporting that a reviewer of a "symmetric" assessment would ask to fix. Round 5's suggested fix already contained the clause.
- **Medicine.** "that model, which slightly exceeded Jev in accuracy on general tasks and in medicine" refers back to the general model initialised from Laya. The medicine gain (+3.36 pp, 87.65 vs 84.29) belongs to the separately fine-tuned medical specialist; the general model scored 39.77% in medicine. T3 repeats the conflation ("a Chinese model initialised from Laya slightly exceeded Jev … and in medicine").

**Fix:** "…hosted \jev{} (version not reported) had a calibration error of 11.45\% on general tasks against 3.78\% for the authors' general model, which slightly exceeded \jev{} in accuracy; their domain-fine-tuned specialists beat \jev{} in medicine but reached 92\% of its average accuracy across specialised domains and were worse calibrated (ECE 12.08\% against 5.57\%)~\cite{arx36965}." In T3, write "models initialised from Laya".

### R6-2 [minor] The Chinese repository citation names the wrong version as the source of the figures, and the Laya range mixes tasks

**Location:**
- grey.bib `qin2026zhdecisionbench`, note field, which reaches the reference list: "v0.1 2026-09-26 (cited figures); v0.2.0 released 2026-09-28, commit 7cd0164".
- 04_evidence.tex l.118.

**Problem:**
- **Version.** Every figure cited in §4.3 comes from v0.2: n = 323, Jev 1.9% and 1.7%, Laya 10.8–20.6%, and "no recalibration".
  - The v0.2 commit (28 Sep, "语音集扩至323条") expanded the voice set to 323 and reran five models.
  - v0.1 did not test Jev at all. App. D and data/grey_literature.csv both say so, so the bibliography contradicts the paper's own appendix.
  - A reader checking v0.1 would find none of the numbers.
- **Task mixing.** The sentence compares Jev's voice-routing order-flip rate (1.9%) with a Laya range of 10.8–20.6%. The upper end, 20.6%, is the customer-service subset, where Jev flipped 2.9%. The comparison is therefore not like for like (the README table: "Option-order flip rate (CS / voice) 2.9% / 1.9% … 20.6% / 10.8%").

**Fix:**
- In grey.bib, write: `note = {v0.2.0, released 2026-09-28, commit 7cd0164 (cited figures); v0.1 (2026-09-26) did not test Jev}`.
- In §4.3, write "changed 1.9–2.9\% of decisions under option-order swaps … against 10.8–20.6\% for the open Laya multilingual model", or restrict both sides to voice routing (1.9% against 10.8%).

---

## Counts

0 major, 2 minor (R6-1, R6-2), 0 nits.

New major or minor problems: **yes**, two minor fidelity problems:
- R6-1 is the incomplete part of R5-1 together with a new conflation.
- R6-2 is new.

No major problem remains. All seven round-5 findings are fixed except R5-1 (partly).
