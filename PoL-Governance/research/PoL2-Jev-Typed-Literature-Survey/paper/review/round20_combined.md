# Round 20: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-19 fix pass (AUDIT.md, last entry). In that pass:
- the Sources column of tab:keyfindings became "principal" studies, with a pointer to data/certainty_evidence.csv (R19-1);
- review/certainty_audit_2026-10-08.md was regenerated from scripts/rate_certainty.py, summary plus `--verbose` (R19-2);
- the zen22935043 bound and alternative-rule wording in §4.9, l.392, was revised (R19-3);
- the zen23075657 test-set caveat at l.354 was moved (R19-4).

Ratings are unchanged. Items resolved in REVIEW.md or AUDIT.md, or closed in rounds 12–19, are not re-raised.

**Inputs**
- Paper: sections/*.tex, main.pdf and main.log.
  - The build is from 17:56:25: 84 pages, no `!` lines, no undefined or multiply defined references.
  - arxiv_metadata.txt: abstract 1,909 ≤ 1,920.
  - arxiv-submission.zip (17:56:26): flat layout with 28 entries plus main.bbl. Once comments are stripped, every section file matches the current source except for the expected `sections/` and `figures/` path flattening. The zip contains the new "principal supporting" caption and the new l.392 sentence.
- Data and script: data/certainty_evidence.csv and scripts/rate_certainty.py.
- Full texts (scratchpad/update):
  - zen22935043.txt: l.149–162 (certification procedure) and l.455–490 (§4.5);
  - zen23075657.txt: abstract l.9–20, l.38, l.62, l.481–487, l.1118–1119.

## Status of round-19 and carried findings

| ID | Status | Note |
|---|---|---|
| R19-1 | FIXED | |
| R19-2 | FIXED | |
| R19-3 | FIXED | |
| R19-4 | FIXED (one new wording nit in the same sentence, R20-1) | |
| R17-2 | NOT FIXED (nit) | Unchanged. In the CSV these open-arm rows are still `out-of-scope`, with notes such as "corroborates": row 2 arx33689/open (l.111); row 11 arx07177/open and arx03324/open; row 6 arx03387/open. The spurious row 1 and row 2 arx24574/open rows remain (l.39, l.100). No rating effect. |
| R17-3 | NOT FIXED (nit) | Unchanged. There is still no 2a/2b split, and D.1 does not say how row 2's second clause ("local fitting is needed") is treated. No rating effect. |

**R19-1: what was checked**
- The caption (04_evidence.tex l.280) now reads "the principal supporting, then opposing studies (every study counted, with its direction, is listed in data/certainty_evidence.csv)".
- The rows for findings 2 and 14 are now accurately described as a subset. The full set is in `--verbose`:
  - row 2: 15 supporting groups;
  - row 14: 5 supporting and 3 opposing.
- D.1 l.88–89 still lists the full sets in prose.

**R19-2: what was checked**
- The two code blocks in review/certainty_audit_2026-10-08.md (17:56:16) were extracted and diffed against fresh `python scripts/rate_certainty.py` and `--verbose` output, after normalising CR line endings. Both are identical.
- The "Decisions" section now has:
  - zen23075657 and zen22935043 opposing on finding 14 (round 17);
  - arx00346 counting neither way, 0.049/0.058 (round 18).
- The stale "met its target" sentence is gone.

**R19-3: what was checked against zen22935043**
- l.392 reads "a procedure whose bound is approximate rather than an exact finite-sample bound". This matches source l.154–155 ("an approximate, not an exact finite-sample, bound").
- The counts match the source:
  - 0 of 2,000 AG News splits;
  - 191 of 2,000 SST-2 splits on the author's wording (l.456–461).
- "An exploratory alternative threshold rule certified 1,776 of 2,000 SST-2 splits but only 4 on AG News" matches l.466–473 ("exploratory sensitivity check"; 0→4 under either wording; 191→1,776).
- The source adds that the four AG News splits averaged 6.1% held-out error, above target. This is omitted, but "only 4" does not overstate the result, so it is not raised.

**R19-4: what was checked against zen23075657**
- "On a test set of previously observed items with mixed labels" now qualifies the 3.24% headline result, as in the abstract (l.9–10, l.20: "previously observed, mixed-label cohort").
- The post hoc 5.39% is now limited to the human-annotated negatives (128/2,376, l.481–487). This is correct.
- D.1 l.88 is consistent with it.

## Script check (task 2)

`python scripts/rate_certainty.py --check`: CHECK PASSED (exit 0). The output is unchanged from round 19:
- Now: 0 moderate / 11 low / 4 very low; contested 2, 5, 11, 14.
- Main only: 0 / 10 / 5; contested 2, 5, 14.
- Given 4 Oct: 1 / 9 / 5.
- 4 Oct recomputed: 0 / 9 / 6; differs on row 14.

The regenerated audit file reproduces this output and `--verbose` byte for byte, apart from line endings.

## Findings

**R20-1 [nit] In l.354, "against 35.6–58.9% recall for adapted encoders" misnames the comparators.**
- **Location:** 04_evidence.tex l.354.
- **What the source says:** the 35.63–58.91% range belongs to "three fixed encoder conditions" (abstract l.13–14; l.62, l.1118), described as "existing or task-adapted" (l.38).
- **Why it matters:** the separate adaptation campaign reached 79.50% recall (mDeBERTa, 3,105 labels; l.17–18). "Adapted encoders" can therefore be read as understating the encoders.
- **Fix:** "against 35.6–58.9% recall for three fixed encoder checkpoints".
- **Not a fix target:** the title of the study (C_catalogue l.175) does use "adapted encoders", and that is correct as a title.

**R20-2 [nit] Inconsistent label punctuation in the Sources cell of tab:keyfindings row 14.**
- **Location:** 04_evidence.tex l.299.
- **What is inconsistent:** the cell reads "update: \cite{arx03387,arx02267}, opposing \cite{zen22935043,zen23075657}", with no colon after "opposing". Row 5 and row 11 use the form "update, opposing: \cite{…}".
- **Fix:** "…; update, opposing: \cite{zen22935043,zen23075657}".

## Fresh pass (task 3)

- **Fidelity:**
  - Every mention of zen22935043 and zen23075657 was re-checked against the full texts: 04_evidence l.287, l.299, l.322, l.354, l.391–392; 07 l.14; B; C; D.1 l.88–89, l.96, l.101.
  - The only problem is R20-1.
  - l.391 ("split conformal prediction reached its marginal target … 5.93% at a nominal 5%") stands.
- **Consistency:**
  - The CSV, script, tab:keyfindings, tab:certchanges, §3, §4.8–4.9 (l.322: "change one rating … very low to low, still contested", plus row 11 now contested), §7 l.14 ("both fall from moderate to low", which matches `--verbose` for rows 2 and 14), §8, D.1 and the abstract all agree.
  - The abstract and counts macros (107/7/85, 26 of 30, κ 0.72, 48 update-coded, 17 days) agree with counts.tex and counts_update.tex.
- **Balance and framing:**
  - The judge/detector conclusion in §8 is stated within "certainty is low or very low", and the opposing threshold evidence is given in proportion (§4.9, §7, D.1).
  - Positionality, the AI-assistance statement, the protocol deviation (§7: rules revised in rounds 12–15) and the data statement are adequate.
  - The PoL2 treatment remains neutral and clause-level.
- **Moderation:**
  - No risk. cs.CY is appropriate, with a cs.AI cross-list.
  - The abstract is within the limit.
  - The bundle is current and self-contained: main.bbl, figures and 00README.json, using pdflatex.
  - The "[Author Name]" placeholder is known and author-only, so it is not re-raised.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 0 | |
| Nit | 2 new, plus 2 carried | R20-1, R20-2; R17-2, R17-3 |

New major or minor problems remain: no
