# Round 17: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-16 fix pass. Ratings are now computed by `scripts/rate_certainty.py` from `data/certainty_evidence.csv` (961 rows: 135 support, 6 oppose, 19 corroborate, 800 out-of-scope, 1 descriptive). Other changes in the pass:
- arx33689's hosted arm opposes rows 2 and 14;
- arx24574 supports rows 2 and 14;
- the 4 Oct citations are taken from `paper/zh/sections/04_evidence.tex`.

Items resolved in REVIEW.md or closed in earlier rounds are not re-raised.

**Inputs**
- Paper: sections/*.tex, main.log (84 pages, no `!` errors, no undefined references), arxiv_metadata.txt, arxiv-submission.zip.
  - The zip, pdf, log and metadata were all written at 17:30:36, after the last section edit (04_evidence.tex, 17:30:16).
  - With CRLF ignored, the zip sources differ from sections/ only in figure paths and comment lines.
- Data:
  - certainty_evidence.csv;
  - evidence_coding*.csv and quality_appraisal*.csv (main and update);
  - zh/sections/04_evidence.tex (the 4 Oct table);
  - review/certainty_audit_2026-10-08.md.
- Full texts:
  - fulltext/2609.24574.txt;
  - 33689.txt;
  - update/zen23075657.txt, zen22935043.txt, arx2610.03387.txt, arx2610.02267.txt, zen23050542.txt.

## Status of round-16 findings

| ID | Status | Note |
|---|---|---|
| R16-1 | FIXED | In the CSV, arx33689's hosted arm opposes rows 2 and 14 (S\*), and arx24574 supports both (S\*). The 0.9 → ≥0.85 routing hypothesis failed: median 0.815 [0.691, 0.897], 6 of 14 tasks cleared it (full text l.672–675). The authors call for "a small gold-labeled validation set per construct" (l.759), which supports row 2. Both rows reproduce as low^c. §3 l.128, §7 l.14, App. D.1 l.84–91, tab:certchanges and the audit agree. New fidelity problems in row 14's update support are raised in R17-1. |
| R16-2 | FIXED | §3 l.128 and App. D l.51 now read "the ratings as given that day". The audit's Summary prints both counts. |
| R16-3 | FIXED | Note a now names the studies cited on 4 Oct: arx33843, zen23041163, arx00346 and arx33401. These match zh 04_evidence.tex l.296 and the `cited_4oct` column. arx33689 was correctly not among them. |
| R16-4 | FIXED | Row 11 now reads "update, opposing: arx02267; open, against: arx07177, arx03324". The caption defines "open:" and "against". Rows 4, 6, 12 and 14 mark their open corroboration. |
| R16-5 | FIXED | §3 l.119 now reads "cannot raise, lower or contest its rating". |
| R16-6 | FIXED | l.206 now reads "a finding a later study contests". |

## Script and data audit (task 2)

**Script output.** `python scripts/rate_certainty.py` gives Now 0 moderate / 11 low / 4 very low, with rows 2, 5, 11 and 14 contested. Main only gives 0 / 10 / 5, with 2, 5 and 14 contested. `--check` passes (exit 0).

**The script against §3:**
- **Matches §3 exactly:**
  - Thresholds: single study, or no S → very low; ≥2 agreeing with ≥1 S → low; ≥3 independent S with ≥1 S\* → moderate.
  - Same-author groups count once among supporters, including when counting independent S groups.
  - Rank is (design, preregistered or replicated).
  - Any opposing study → contested. The rating falls one level if the top opposing rank ≥ the top supporting rank, and not below very low.
  - Per-clause minimum.
  - D3′: an open arm cannot support or oppose a hosted or both finding, and this is asserted.
- **Not implemented in the script.** These are coding judgements recorded in the CSV notes, which App. D l.53 acknowledges:
  - D1: `replicated_by` is empty on every row, and the script does not check D1's conditions;
  - D5;
  - the "primary result" clause of the opposing definition.
- **Edge case not handled.** Opposing studies are not grouped by author, and are not checked against the supporting groups. No such overlap exists in the data, which was checked.

**Coverage.** Every study coded on each finding's requirement axes (as in the builder and audit) has a row for every finding, per arm. None is missing.
- Two extras (zen23050542 and zen23075657, coded on G1 only) are counted on row 14. That is allowed by "all coded studies that bear on it".
- Arms agree with the per-axis `system` column, except for six `system=none` non-empirical items, which are entered as hosted and out-of-scope.
- Design ratings in the coding CSVs equal those in the appraisal CSVs for every document.

**Sample.** 22 counted rows were checked against the coding rationale (random seed 17), plus every row-2 and row-14 row and every corroborate or oppose row. All agree except those in R17-1. Full-text checks:
- arx24574 (Sec. 4.4–4.5): the call is correct;
- arx33689 (6/1/0 Jev and 1/6/0 Laya FT, "within bound" = above the 0.05 target but inside the Prop. 2 bound): the hosted-arm call and the open-arm corroboration are both correct;
- arx03387 ("exceed 5% target false rejection in six of twelve task transfers", l.138): correct;
- arx02267 (4.3%; held-out splits 47%, p95 16.7%): correct;
- zen23050542: correct;
- zen23075657 and zen22935043: not correct (R17-1).

## Consistency (task 3)

The following agree with the script: 0 moderate, "low or very low", four contested, row 14 low^c, row 2 low^c.
- abstract l.7 and metadata ("Certainty is low or very low");
- §1 l.34–35 (the update raised row 14 from very low to low, which is correct against main only; it made row 11 contested);
- G2 box l.61 and G6 box l.206;
- §4.8 l.274 and §4.9 l.321–323;
- §5 l.39 ("a later study contests the first");
- §6 l.38, §7 l.11–15 and §8 l.7;
- App. D l.51–91, including the main-only column of tab:certchanges;
- §9 data statement (lists certainty_evidence.csv and rate_certainty.py).

The only factual mismatch is the set of update studies named for row 14 (R17-1).

## Findings

**R17-1 [major] Two of the four update studies said to support row 14 met their error targets in their primary analysis, and a main-window study that also met its target is left out rather than counted as opposing. App. D.1 misstates one of them.**
- **Location:**
  - certainty_evidence.csv: row 14, zen23075657 and zen22935043 (support), arx00346 hosted (out-of-scope);
  - §4.9 l.322 ("four studies of hosted Jev raise … arx03387, zen22935043, arx02267, zen23075657");
  - App. D.1 l.88 ("four from the update …, the last with a threshold set on development labels that exceeded its 5% false-positive tolerance on the test set (5.39%)");
  - App. D.1 l.91 and note a of tab:certchanges (arx00346);
  - audit l.18.
- **zen23075657.** The abstract and p. 9 say that at the development-selected threshold, Jev reached 3.24% FPR on the 4,940-item test cohort. Its conservative FPR upper bound was 0.0405 ≤ 0.05, and it was "the only arm to pass the absolute gate". The 5.39% is a **post hoc** human-annotated stratum (Table R1a). The authors say "the original aggregate and its gate decision remain valid", and that the stratum result "does not change the frozen thresholds or primary hypothesis". So the paper's "exceeded … on the test set" is wrong. Under §3 ("counts on the side of its primary result"), this study opposes row 14.
- **zen22935043.** The abstract says that "split conformal prediction reaches its marginal target". The 5.93% is the error of the single-label subgroup, not the target that was set. Its primary result therefore also runs against row 14, or at most is mixed. It cannot count as support.
- **arx00346.** Its held-out threshold met the 5% target on CLINC (realised risk 0.049); only the one-sided bound exceeded the target. The CSV and App. D.1 treat it as "not counted" because it "could not be certified". That reason is not in §3, and the same logic was not applied to zen23075657 (counted on a stratum) or zen22935043 (counted on a subgroup). Coded symmetrically, it is a hosted S that opposes row 14.
- **Effect on ratings: none.**
  - Row 14 Now still has arx24574 (S\*), arx33401, arx02267 and arx03387 (S), and zen23050542 (M). That is 4 independent S with an S\* → moderate, and the opposing S\* lowers it to **low^c**.
  - Main only stays **very low^c**.
  - 4 Oct recomputed becomes very low, *contested* (arx00346 opposing), which still matches note a's "very low".
  - Rows 1 and 2 are unaffected: zen22935043's support of row 2 (the tier was certified in 0/2,000 AG News splits vs 191/2,000 SST-2 splits) is a transfer result and stands.
- **Why it is major:** the main text and App. D.1 cite a source for the opposite of its primary result, and the coding breaks §3's own primary-result rule in one direction only.
- **Fix:**
  - In the CSV: recode zen23075657 and arx00346 (hosted) as `oppose`, and zen22935043 as `oppose` (or out-of-scope, with a reason).
  - §4.9 l.322: "two stronger-design studies of hosted Jev (arx03387, arx02267) and one of moderate design (zen23050542) raise …".
  - App. D.1 l.88: correct the description of zen23075657, and list the three opposing studies next to arx33689.
  - App. D.1 l.91 and note a: "a held-out threshold that met its target, which under the current rule opposes it".
  - Re-run `--check` and update the audit.
  - Optionally, give row 14's table cell the same update set as the text. At present it lists three update studies while the text names four.

**R17-2 [nit] Open-arm rows that bear on a finding are sometimes labelled `out-of-scope`, not `corroborate`.**
- **Location:** certainty_evidence.csv: row 2 arx33689/open ("corroborates, no effect"); row 11 arx07177/open and arx03324/open ("same direction as arx02267"), which the table shows as "open, against".
- **Problem:**
  - §3 l.124 and App. D l.53 promise that each row is listed as supporting, opposing, corroborating or out of scope.
  - The script treats both labels the same, so no rating changes. A reader of the CSV, however, sees an "out of scope" label where the paper reports corroboration.
  - Row 2 also has an open-arm row for arx24574, although its G6 coding is hosted only.
- **Fix:**
  - Use `corroborate`, with the direction ("same"/"against") in the note, wherever the open arm's result bears on the finding.
  - Drop the spurious arx24574 open row, or note why it is there.

**R17-3 [nit] Row 2's wording has two clauses ("fixed thresholds do not transfer; local fitting is needed"), but it is rated as one.**
- **Problem:** Rows 1, 6, 8, 9, 10 and 12 are split into clauses under §3's lowest-clause rule.
- **Effect if split:** the result is the same (low^c). arx33689's ≥19-label floor supports clause 2, and its hosted arm opposes clause 1.
- **Fix:** State in App. D.1 that the second clause is treated as following from the first, or split the row into 2a/2b in the CSV.

## Fresh pass (task 4)

- No moderation risk. The build, zip and metadata are current and consistent (84 pp, CC BY 4.0, cs.CY / cs.AI).
- The deviation from the update protocol is disclosed in §3 l.71 and l.126, §4.9 l.321 and §7.
- The author-name placeholder is already known and is not re-raised.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 1 | R17-1 |
| Minor | 0 | |
| Nit | 2 | R17-2, R17-3 |

New major or minor problems remain: yes
