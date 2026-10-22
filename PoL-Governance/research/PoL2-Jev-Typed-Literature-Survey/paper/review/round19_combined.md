# Round 19: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-18 fix pass (AUDIT.md, last entry). In that pass:
- the G6 box and §7 were updated;
- arx00346 on finding 14 was recoded as mixed, counting neither way;
- l.224 now reads "every model but one";
- zen22935043 gets a new row-2 reason, an "approximate … bound" wording and the alternative rule's 1,776/2,000;
- zen23075657 gets its caveats;
- note a now reads "very low" throughout.

Items resolved in REVIEW.md or AUDIT.md, or closed in rounds 12–18, are not re-raised.

**Inputs**
- Paper: sections/*.tex, main.pdf and main.log (84 pp; no `!` lines; no undefined references), arxiv_metadata.txt (abstract 1,909 ≤ 1,920), arxiv-submission.zip.
- Freshness: the last section edits were 17:52:10–17:52:33. The build, zip and metadata are from 17:52:43. The zip's 04_evidence.tex and D_corrections.tex contain the new round-18 sentences.
- Data and script: data/certainty_evidence.csv and scripts/rate_certainty.py.
- Full texts:
  - zen22935043.txt: l.150–161 (procedure) and l.455–490 (§4.5, sensitivity check);
  - zen23075657.txt: abstract l.9–20, l.51, l.481–487, l.1058–1060;
  - arXiv HTML of 2610.00346, §5.1.

## Status of round-18 and carried findings

| ID | Status | Note |
|---|---|---|
| R18-1 | FIXED | |
| R18-2 | FIXED | |
| R18-3 | FIXED (one wording nit, R19-3) | |
| R18-4 | FIXED (placement nit, R19-4) | |
| R18-5 | FIXED | |
| R17-2 | NOT FIXED (nit) | Unchanged. In the CSV, these rows are still `out-of-scope`: row 2 arx33689/open ("corroborates"); row 11 arx07177/open and arx03324/open; row 6 arx03387/open. The spurious row 1/2 arx24574/open rows remain. |
| R17-3 | NOT FIXED (nit) | Unchanged. There is still no 2a/2b split, and D.1 does not say how row 2's second clause is treated. |

**R18-1: what was checked**
- The G6 box (l.205) now reads "…in most studies that set one, although in several, including a preregistered one, \jev{}'s threshold met its target".
- §7 l.14 adds "the second also by two update studies whose thresholds met their targets [zen22935043, zen23075657]".
- Both agree with the CSV: hosted row 14 has 5 supporting and 3 opposing studies, and arx00346 counts neither way.
- "Most" holds when the open-model corroboration is counted.

**R18-2: what was checked**
- In the CSV, row 14 arx00346/hosted is `out-of-scope`, with the note "mixed, counts neither way … 0.049 … 0.058".
- l.224: "exceeded a 5% target for every model but one … met the target on one dataset (0.049) and missed it on the other (0.058)".
  - This matches §5.1 of the source, where the exception is the Gemma-4-31B stated-probability configuration on typed-decisions.
- D.1 l.91, "although its bound exceeded it", is correct: the CLINC upper bound is 0.066.
- With the recode, 4 Oct recomputed for row 14 is very low and not contested. The text says the same in each place:
  - script output: `very low`;
  - §3 l.128 ("would have been very low … a third met its target on one dataset and missed it on another");
  - note a of tab:keyfindings ("very low under the current rule");
  - note a of tab:certchanges ("counts neither way");
  - D.1 l.88 and l.91.
- arx00346 is correctly dropped from the row 14 sources.

**R18-3: what was checked**
- The CSV row 2 note now leads with the primary result ("calibration and certifiability depend on question form and task").
- l.392 adds the alternative rule's 1,776 of 2,000 SST-2 splits, which matches source l.473–475.
- The direction of the code is unchanged, and that is defensible.

**R18-4: what was checked**
- l.354 now has "post hoc" and "observed before and carried mixed labels".
- D.1 l.88 has "on test items that had been observed before and carried mixed labels".

**R18-5: what was checked**
- Note a reads "very low" in tab:keyfindings, tab:certchanges, §3 l.128 and D.1 l.51 and l.91.

## Script check (task 2)

`python scripts/rate_certainty.py`:
- Now: 0 moderate / 11 low / 4 very low; contested 2, 5, 11, 14.
- Main only: 0 / 10 / 5; contested 2, 5, 14.
- Given 4 Oct: 1 / 9 / 5.
- 4 Oct recomputed: 0 / 9 / 6; differs from given on row 14, now `very low` without the contested mark.

`--check`: CHECK PASSED.

`--verbose`, row 14 now:
- support: arx24574\*, arx33401, arx02267, arx03387, zen23050542 (M);
- oppose: zen22935043, zen23075657, arx33689\*;
- result: falls one level, to low c.

All of these agree with the paper:
- the abstract ("low or very low");
- §1;
- §3 l.122–128;
- §4.8;
- §4.9 l.322;
- §7 l.14 ("Four are contested … both fall from moderate to low");
- tab:keyfindings;
- tab:certchanges;
- D.1 l.74–91.

## Findings

**R19-1 [minor] The "Sources" column of tab:keyfindings leaves out supporting studies that are counted in the rating. The caption presents the column as the list of supporting and opposing studies.**
- **Location:**
  - caption, 04_evidence.tex l.280 ("*Sources*: supporting, then opposing studies … Computed by scripts/rate_certainty.py from data/certainty_evidence.csv");
  - rows 2 and 14 (l.287, l.299).
- **What is missing:**
  - Row 2: the script and D.1 l.89 count arx39496, zen22952571 and arx27607 (main window) and arx04985 and zen23050542 (update) as supporting. The table lists none of them.
  - Row 14: the table omits zen23050542, which D.1 l.88 ("one update study of moderate design agrees") and the script count.
- **Why it matters:** a reader who checks a rating against the table sees fewer supporting studies than the rating rests on. The omission is not limited to weak designs: zen22952571 and arx39496 are stronger-design studies.
- **Fix, either of:**
  - list every counted study;
  - change the caption to "principal supporting studies; the full per-arm list is in data/certainty_evidence.csv and App. D.1".

**R19-2 [minor] The released audit file contradicts the paper and the script on row 14.**
- **Location:** review/certainty_audit_2026-10-08.md (17:25:20). That is earlier than both the round-17 and round-18 recodes.
- **What is stale:**
  - Its row 14 "now" line lists zen22935043 and zen23075657 as *support*, with opposing "arx33689" only.
  - l.19 says arx00346 "met its target (out of scope)".
  - The script now prints oppose for zen22935043 and zen23075657, and "met on CLINC, missed on typed-decisions" for arx00346.
- **Why it matters:** AUDIT.md (round 16) describes the file as "regenerated from the script output". The metadata comments and §9 point readers to the review logs.
- **Fix:** regenerate the file from `--verbose` and update the l.19 sentence.

**R19-3 [nit] l.392 says "a procedure with an approximate finite-sample bound". The source says it is *not* a finite-sample bound.**
- **Source wording:**
  - "an approximate, not an exact finite-sample, bound" (l.154–155);
  - the rates are "descriptions of one procedure on this sample and not as finite-sample guarantees" (l.489–490).
- **Also missing:** under the alternative rule, Jev also rose from 0 to 4 AG News splits, with a held-out error of 6.1% in those splits. The source calls that check "exploratory".
- **Fix:** "a procedure with an approximate (Wilson) bound … although, in an exploratory check, another threshold-selection rule certified 1{,}776 of 2{,}000 SST-2 splits (4 on AG News)".

**R19-4 [nit] In l.354, "observed before and carried mixed labels" sits on the post hoc breakdown. In the source it describes the whole 4,940-item test cohort, including the 3.24% headline result.**
- **Source:** abstract l.9–15; l.51. The human-annotated stratum on its own is not mixed-label.
- **Fix:** move the qualifier, e.g. "…gave 90.52% recall at a 3.24% false-positive rate on a previously observed, mixed-label test set, within … ; in a post hoc breakdown, the false-positive rate on the human-annotated negatives alone was 5.39%". D.1 l.88 already places it correctly.

## Fresh pass (task 3)

- **Fidelity:**
  - The new sentences were checked against all three sources, and the only problems are R19-3 and R19-4.
  - l.391 (5.93% at nominal 5%) and l.224 (0.049/0.058; 31.0%/19.5% carried) stand.
- **Balance:**
  - The G6 box, §4.9, §7 and D.1 now give the opposing threshold evidence in proportion: 3 hosted studies opposing against 5 supporting, with arx00346 neutral.
  - The "does not support them as judges … thresholds do not transfer" sentence in the abstract is still within a low, contested rating. "Certainty is low or very low" covers it. This is not re-raised.
- **Consistency:** apart from R19-1 and R19-2, no inconsistency was found between the CSV, the script, the tables, §1, §3, §4.8–4.9, §7, §8, App. D or the abstract.
- **Disclosure and data statement:**
  - The protocol deviation, AI coding and κ, and the CSV and script in §9 are unchanged and adequate.
  - The audit file is stale (R19-2).
- **PoL2 framing:** neutral and clause-level. No advocacy.
- **Moderation:**
  - No risk. The bundle is current, with 28 entries and main.bbl present.
  - The abstract is within the limit.
  - The author placeholder "[Author Name]" is known and author-only, so it is not re-raised.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 2 | R19-1, R19-2 |
| Nit | 2 new, plus 2 carried | R19-3, R19-4; R17-2, R17-3 |

New major or minor problems remain: yes
