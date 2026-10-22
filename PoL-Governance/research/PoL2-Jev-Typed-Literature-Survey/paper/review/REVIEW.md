# Consolidated review status (v0.3)

Protocol: `PROTOCOL.md`. Raw findings: `round1_*.md`, `round2_*.md`. Coding work: `coding/`, `CODEBOOK_v3.md`. New papers: `new_papers_2026-10-04.md`.

## Round 1 (2026-10-04): 174 findings from five reviewers

| Lens | File | Major | Minor | Nit |
|------|------|------:|------:|----:|
| fidelity G1–G3 | `round1_fidelity-A.md` | 5 | 19 | 16 |
| fidelity G4–G7, §2, §5 | `round1_fidelity-B.md` | 2 | 21 | 13 |
| consistency | `round1_consistency.md` | 4 | 31 | 5 |
| argument / method | `round1_argument.md` | 15 | 15 | 3 |
| arXiv / PoL2 | `round1_arxiv-pol2.md` | 3 | 15 | 7 |

### Resolution by theme

| Theme | Representative findings | Resolution in v0.3 |
|-------|-------------------------|--------------------|
| arXiv framing (survey rule) | arx-1, arx-2, arx-3, arx-5 | User decision 2026-10-04: reframed as a cs.CY research paper (new title, abstract with societal framing, requirements analysis + evidence assessment, no project-memo voice, ★ markers removed, §6 generalised). <!-- FIXED: 2026-10-04 --> |
| Author metadata | arx-6 | "Shentao Yan" (user decision); "NaturalDAO contributors" moved to acknowledgements. <!-- FIXED --> |
| One-sided thesis | arg-1, arg-4, arg-6, arg-7, arg-30 | Comparator field added to every coded row; §4.8 separates typed-specific from shared failures; two-sided key-findings table with certainty replaces the negative-results table; 96% caveat carried everywhere; arx37647 order robustness and hosted-Jev Chinese results added. <!-- FIXED --> |
| Asymmetric codebook, direction weighting | arg-2, arg-13, cons-3 | Symmetric v3 codebook tied to detector use; direction weighting removed; all rows recoded; arx34862 → Q. <!-- FIXED --> |
| No quality appraisal / certainty | arg-12, arg-16, arg-17 | Four-item appraisal per study (`data/quality_appraisal.csv`), GRADE-style certainty (tab:certainty, tab:keyfindings), sensitivity to higher-quality studies reported, PRISMA checklist (Appendix E). <!-- FIXED --> |
| Zenodo verified only at description level | cons-1, arg-17 | All Zenodo records read in full by the coding agents; ‡ now marks the source type only. <!-- FIXED --> |
| Single coder | arg-13, arg-14 | Blind second (AI) coder on 30 pairs, κ = 0.72, disagreements resolved and logged (`data/coder_agreement.csv`); human/AI roles disclosed in §3 and statements. <!-- PARTLY: no second human coder --> |
| Eligibility and flow | arg-15, cons-8 to cons-12 | Operational definition, date window, grey-literature criterion; arXiv search re-run 4 Oct with a script; flow recomputed; arx22664, zen22953637, two commentary blogs reclassified as context; trackers no longer counted. <!-- FIXED --> |
| Detector/judge consistency | arg-18 to arg-22 | Definition tightened (time-bounded, reversible, misses count); element 5 requires a person for final blocks; public log delayed and coarsened; trade-offs paragraph; checklist with provisional pass criteria; symmetric numeric falsification conditions. <!-- FIXED --> |
| Fairness to PoL2 / positionality | arg-5, arg-23 to arg-26, arx-21, arx-22 | Scope statement corrected; T1 retitled with charitable reading; T4 option (b) "plausible but untested"; Art. 2(1) premise; polgov coincidences disclosed; non-financial interest stated. <!-- FIXED --> |
| PoL2 fidelity | arx-14 to arx-25, cons-6, cons-7, cons-26 | Appendix A rebuilt from verbatim PoLEn text; §5.5 "may accept", §5.6 "can", §5.4 "within", §5.4.1 "where necessary", cognitive calibration reinterpreted, official terms, commit credit corrected, three missing passages added. <!-- FIXED --> |
| Number fidelity | fidA-1…40, fidB-1…36 | Applied in the rewritten §2, §4, §5; v0.2→v0.3 corrections listed in tab:corrections3. <!-- FIXED; re-checked in round 2 --> |
| Missing literature | arg-27 | 21 verified references added (moderation, emotion recognition, annotator disagreement, Chinese resources, deferral, shift/multicalibration, due process, social scoring, PRISMA/GRADE); 16 previously uncited background entries now cited. <!-- FIXED --> |
| Structure / length | arg-28, arg-29 | §4 cut to ~5,300 words of source with answer boxes; recommendations moved to §6; redundancy removed. <!-- FIXED --> |
| LaTeX / bundle | cons-2, cons-39, arx-10 to arx-13 | Floats with placeins; typeout before \end{document}; pdftitle/pdfauthor and bookmarks; catalogue column widths; metadata from counts.tex and the log. <!-- FIXED --> |
| Data availability claims | arx-7, arx-8 | Not fixable locally: the public repository must be updated (push data, coding, scripts, sources; licence audit of redistributed PDFs) before submission. <!-- OPEN: user action --> |

## Round 2 (2026-10-04): about 80 findings from four reviewers and three verification sub-passes

| Lens | File | Major | Minor | Nit |
|------|------|------:|------:|----:|
| fidelity G1–G3, §2 | `round2_fidelity-A.md` | 0 | 3 | 6 |
| fidelity G4–end, §5–§7, PoL2 | `round2_fidelity-B.md` + sub-pass reports | 4 | 22 | 12 |
| consistency | `round2_consistency.md` | 2 | 19 | 5 |
| argument / arXiv | `round2_argument.md` | 6 | 11 | 4 |

Verdicts: minor revision (FAccT/AIES standard); arXiv risk medium, low after framing fixes.

| Theme | Resolution <!-- FIXED: 2026-10-04 unless noted --> |
|-------|------------|
| Overstated positive headline ("accepted safely") | Abstract, thesis, element 3, key-findings row now say "non-inferior on benign data; disguised attacks passed"; certainty very low. |
| "Automated judges generally" overreach; failures "shared" | Recomputed: of 14 negative codes with a comparator the typed model was worse in 6; text now says typed models are not generally worse but most failures were never compared. |
| T4 option (a) vs thesis; "repair"; conclusion wording | Option (a) flagged as outside the detector role; repair limited to the AI's own output; conclusion names person-confirmed blocks and random audit. |
| AI coders disclosed only in body | Abstract and contributions say AI agents and a second AI coder; κ 95% CI (0.43–0.94), marginals, same model family, no human re-check stated. |
| Review apparatus prominence | PRISMA flow and selection details moved to Appendix E; framing sentence; PRISMA item 1 marked "not followed by design"; checklist expanded to sub-items; cs.CL cross-list dropped; version history removed from the paper (v0.2→v0.3 table moved to `corrections_v0.2_to_v0.3.tex`). |
| Appraisal ignored independence; certainty rules | Rating now requires an independent system for "stronger"; GRADE starting point justified; one merged key-findings table with explicit rules; two findings rise to moderate. |
| Zenodo sensitivity; codebook rule (iv); SWiM | Added (13/77/27 of 117 without Zenodo); rule (iv); SWiM cited. |
| Data/coding inconsistencies | arx34862 recoded Q (override logged); catalogue requirements generated from the coding; tier rule text; excluded-records file; tension links in Fig. 6 re-derived; all-nine-panel Fig. 5c; figure labels ("evaluator", Open-Jev). |
| Source fidelity (TensorTrust CV threshold, versions not reported, masking, Kev scope, KITE retrospective, arx35286 no ranking, arx00213 removed from sub-type row, zen22847531/zen22866847 split, arx33971 statistic, GDPR 22(3) scope, AI Act medical/safety exception, §5.5 hate-attack sentence, concordance items) | Applied. |
| Open: data not public; author affiliation/email | User action required. <!-- OPEN --> |

## Round 3 (2026-10-04)

| Lens | File | Major | Minor | Nit |
|------|------|------:|------:|----:|
| fidelity + consistency | `round3_fidelity-consistency.md` | 1 | 7 | 7 |
| argument / arXiv | `round3_argument.md` | 3 | 7 | 3 |

Resolved: steering finding downgraded to low (rule violation); bridging paragraph on what "supports detectors" means and "under added conditions" in abstract and thesis; automatic allow defined as an audited exception; broken arXiv URLs in 15 references (generator bug) fixed; appraisal wording aligned with the script; checklist mapping (9 of 14); comparator cells; κ CI with 10,000 resamples (0.42–0.94); T1 empathy figure; GDPR wording in the conclusion; "clear role" → "plausible role"; review passes described as AI passes; section renamed "Changes from the earlier release". <!-- FIXED -->
Author-only: human check of codes (R3-arg-3), push and pin data (R3-arg-8), repository path in Comments (R3-arg-9). <!-- OPEN -->

## Round 4 (2026-10-04)

| Lens | File | Major | Minor | Nit |
|------|------|------:|------:|----:|
| fidelity + consistency | `round4_fidelity-consistency.md` | 0 | 3 | 5 |
| argument / arXiv | `round4_argument.md` | 0 | 2 | 5 |

Verdict: accept with minor revisions; arXiv risk low once the author-only items are done.
Resolved: "neutral" option wording (regression); Appendix E rating wording; Figure 6 caption; element-5 title and conclusion wording for automatic allow; "indicates why"; six-point sensitivity wording; † removed from a context source; GRADE adaptation stated; arx00213 identifier figures; arx00376 sentence; peer-evaluator comparator cell; clause count wording. <!-- FIXED -->

## Rounds 5-11 (2026-10-04 to 2026-10-05)

| Round | File(s) | Major | Minor | Nit | Main resolutions |
|------:|---------|------:|------:|----:|------------------|
| 5 | `round5_combined.md` | 0 | 3 | - | wording and data fixes |
| 6 | `round6_combined.md` | 0 | 2 | - | Chinese-benchmark figures (arx36965, qin2026) |
| 7 | `round7_combined.md` | 0 | 2 | - | added arx29769 parity, arx01079, grazian WiC |
| 8 | `round8_combined.md` | 0 | 3 | - | balance: favourable and unfavourable results added (zen22885291, arx24574, arx27678, arx34024, arx00381, zen23032384, grazian); arx27607 rationale |
| 9 | `round9_combined.md` | 0 | 3 | 4 | "none" wording; frontier calibration now mixed; escalation scope (zen22885291) |
| 10 | `round10_combined.md` | 0 | 0 | 3 | six binary tasks; arx34024 scope; Table 2 citations |
| 11 | `round11_combined.md` | 0 | 0 | 1 | Table 2 Codes S/Q |

Exit condition met: rounds 10 and 11 had no new major or minor findings. All nits fixed. <!-- CLOSED -->

Still open (author-only): push and pin data/scripts/logs; affiliation and e-mail; human check of the 30-pair sample; repository path; confirm the two author statements; arXiv endorsement if needed. <!-- OPEN -->

## Update search and rounds 12-21 (2026-10-08)

Update search: see `UPDATE_SEARCH_2026-10-08.md`.
- 57 sources were retained after full-text reading; 48 were coded, giving 118 pairs (S 12, Q 92, N 14).
- Second coding was blind on all 118 pairs: κ 0.55 [0.36, 0.70]. A third coder adjudicated the 21 disagreements.
- The paper reports the update in §4.9 and in Appendices B, C, D and E.
- Hatevolution was added as background literature, together with checklist item 16.

| Round | File | Major | Minor | Main resolutions |
|------:|------|------:|------:|------------------|
| 12 | `round12_fidelity.md`, `round12_argument.md` | 1 | 12 | Certainty rule made symmetric; rule-(iv) audit recoded 2 main G3 rows to N; codebook gaps disclosed; recall of the main window disclosed |
| 13 | `round13_combined.md` | 0 | 6 | Rule applied to every row; definition of "opposing" |
| 14 | `round14_combined.md` | 2 | 3 | D1 replication, D2 arx33689, D3 scope, D4 deviation disclosed with 4 Oct and current ratings, D5 stronger reasoner |
| 15 | `round15_combined.md` | 2 | 3 | D3' per-arm counting; rating bookkeeping moved to App. D.1 |
| 16 | `round16_combined.md` | 1 | 3 | Ratings computed by `scripts/rate_certainty.py` from `data/certainty_evidence.csv`; `--check` |
| 17 | `round17_combined.md` | 1 | 0 | Finding 14 coded on primary results |
| 18 | `round18_combined.md` | 0 | 3 | arx00346 mixed; wording of the G6 box and §7 |
| 19 | `round19_combined.md` | 0 | 2 | Sources column labelled "principal"; audit file regenerated |
| 20 | `round20_combined.md` | 0 | 0 | Two nits fixed |
| 21 | `round21_combined.md` | 0 | 0 | One nit fixed (data statement) |

Exit condition met: rounds 20 and 21 had no new major or minor findings. <!-- CLOSED -->

Open nits:
- R17-2: open arms labelled out-of-scope instead of corroborate.
- R17-3: row 2 rated as one clause.
- R21-2: `\ldots` missing in the English cells for Art. 8 and Art. 10.
- R21-3: two §2.1 phrases are not in the concordance.

None of these affects a rating or a claim.

Final certainty ratings: no moderate, 11 low, 4 very low. Findings 2, 5, 11 and 14 are contested.

## Additions of 2026-10-08/09 and rounds 22-40

At the user's request the paper gained two sections:
- §2.3 "PoL2 among AI-governance paradigms" (tab:paradigms) compares PoL2 with regulation, platform governance, training-time constitutions, guardrails and DAO governance. It states checkable properties of PoL2, each paired with a cost, and does not claim that PoL2 is unique. China's 2023 Interim Measures are named as the closest comparator.
- §7.1 gives an explicit verdict (tab:verdict): hosted Jev is not a suitable tool for any PoL2 function that decides; it can serve only as a recorded detector inside the §6 design; even that is an extrapolation.

Eight new references were verified.

Rounds 22-40 fixed the following:
- a table that overflowed the page;
- overclaims in §2.3 (as the only paradigm, "most specification-like");
- the scope of Chapter 7 duties;
- the over-application of EU law: Art. 5(1)(f) is limited to biometric data, and Art. 14/86 to Annex III systems, with ADR covered under point 8(a);
- the oracle and data-minimisation lessons, made consistent with arx04985 §VI-A, with checklist item 7 extended;
- regressions in the abstract (the scope of the coded studies; "on simulated data").

Exit condition met: rounds 39 and 40 had no new major or minor findings. Eight nits are carried (see the round39 and round40 files). <!-- CLOSED -->
