# Round 18: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-17 fix pass. In that pass, zen23075657, zen22935043 and arx00346 (hosted arm) were recoded as opposing on row 14, and §4.9 l.322 and l.354, l.391, tab:keyfindings row 14, and App. D note a and D.1 were edited to match.

Items resolved in REVIEW.md or AUDIT.md, or closed in rounds 12–17, are not re-raised.

**Inputs**
- Paper: sections/*.tex, main.pdf, main.log (84 pp, no `!` errors), arxiv_metadata.txt, arxiv-submission.zip.
  - The build, zip and metadata (17:42:55–56) are newer than the last section edit (17:42:38) and the CSV (17:42:04).
  - The zip sources differ from sections/ only in figure paths and comment lines. main.bbl is present.
- Data and script: data/certainty_evidence.csv (961 rows: 133 support, 9 oppose, 19 corroborate, 799 out-of-scope, 1 descriptive) and scripts/rate_certainty.py.
- Full texts:
  - update/zen23075657.txt;
  - update/zen22935043.txt;
  - arXiv HTML of 2610.00346 (§3.3, §5.1, abstract).

## Status of round-17 findings

| ID | Status | Note |
|---|---|---|
| R17-1 | FIXED | Detail below. |
| R17-2 | NOT FIXED (nit) | Detail below. |
| R17-3 | NOT FIXED (nit) | App. D.1 still does not say how row 2's second clause is treated, and the CSV has no 2a/2b split. |

**R17-1: what was checked**
- In the CSV, row 14 now codes zen23075657, zen22935043 and arx00346/hosted as `oppose`, with primary-result notes.
- zen23075657 is checked against its full text:
  - l.12–16: 1,000 development labels, 90.52% recall at 3.24% FPR, encoders at 35.63–58.91%. "Only Jev met the specified absolute quality bounds".
  - l.487–490: 5.39% is a post hoc result on the human-annotated stratum.
- zen22935043 is checked against its full text:
  - l.21–22: "split conformal prediction reaches its marginal target, although its single-label answers are wrong 5.93%".
  - §4.2 (l.285–293).
- The text agrees with the CSV in four places:
  - §4.9 l.322 ("two others whose thresholds met their targets add to the opposing evidence");
  - l.354 and l.391;
  - tab:keyfindings row 14 ("update: arx03387, arx02267, opposing zen22935043, zen23075657"; arx00346 listed as opposing);
  - App. D.1 l.88 and l.91 and note a.
- The ratings are unchanged, as predicted in round 17: row 14 is low^c now, very low^c on the main window alone, and very low^c on the 4 Oct recomputation.
- Remaining fidelity gaps from the recoding are raised below as R18-1 to R18-4.

**R17-2: what remains**
- These open-arm rows bear on a finding but are still labelled `out-of-scope`:
  - row 2: arx33689/open ("corroborates");
  - row 11: arx07177/open and arx03324/open ("same direction as arx02267"), which tab:keyfindings shows as "open, against".
- The spurious row 2 arx24574/open row is still present.
- A further case: row 6, arx03387/open ("neutral identifiers cut Qwen detection 20–31 points").

## Script check (task 2)

`python scripts/rate_certainty.py`:
- Now: 0 moderate / 11 low / 4 very low; contested 2, 5, 11, 14.
- Main only: 0 / 10 / 5; contested 2, 5, 14.
- 4 Oct recomputed: 0 / 9 / 6; differs from given on 14.

`--check`: CHECK PASSED.

**Is the primary-result rule applied symmetrically?**
- **Row 14:** symmetric for zen23075657 and zen22935043, but not for arx00346 (R18-2).
- **Row 11:**
  - The only hosted opposer is arx02267. Its primary pre-screen result is a 4.3% cost cut, coded `oppose`, which is correct.
  - No hosted study whose primary escalation result met its goal is left out of scope.
  - arx09188 is correctly excluded as a peer comparison, and arx02048 is correctly assigned to row 12.
- **Row 2:**
  - arx33689/hosted opposes, as in round 16.
  - zen23088660 ("held in-distribution; no transfer tested") is correctly out of scope.
  - zen23075657 is not coded on G6, which is correct. Its development-fitted threshold that held is local fitting, not transfer.
  - The exception is zen22935043's row 2 *support*. It rests on a certification count, which App. D.1 l.87 says is not a failed transfer (R18-3).
- **Other rows (3, 5, 6, 8, 9, 10, 12):** sampled; there is no gate or target that held and was coded in the wrong direction.

## Findings

**R18-1 [minor] The G6 answer box and §7 still describe one study whose gate held. After R17-1, four hosted studies oppose row 14, against five that support it.**
- **Location:**
  - §4.7 G6 box l.205: "thresholds fixed in advance missed their error targets on new data in most studies that set one, although in one preregistered study \jev{}'s gate held";
  - §7 l.14: "both are opposed by a preregistered study … [arx33689]".
- **Problem:**
  - The hosted arm of row 14 now has these studies:
    - supporting: arx24574, arx33401, arx02267, arx03387 and zen23050542;
    - opposing: arx33689, arx00346, zen22935043 and zen23075657.
  - "Most studies" is true only when the open-model corroboration is counted. "In one preregistered study … held" understates the opposing hosted evidence that App. D.1 l.88 now sets out.
  - §7 names a single opposing study for both threshold findings. For row 14 there are four.
- **Fix:**
  - G6 box: "…missed their error targets on new data in about half the studies of hosted \jev{} that set one and in every open-model study; in four studies of hosted \jev{}, one preregistered, the threshold held".
  - §7 l.14: "…and both are opposed by a preregistered study … ; three more studies of hosted \jev{} whose thresholds met their targets oppose the second".

**R18-2 [minor] arx00346 is described only by its CLINC result. On its second dataset the held-out threshold missed the target, and l.224 still overstates the bound result.**
- **Location:** CSV row 14 arx00346/hosted note; App. D.1 l.88 and l.91; note a of tab:certchanges; §4.7 l.224.
- **Source (arXiv 2610.00346, §5.1):**
  - With the held-out threshold, hosted \jev{} "accepts 0.93 of the CLINC-150 decisions at a realized risk of 0.049 … and 0.17 of the typed-decisions decisions at 0.058". So the second dataset is above the 5% target.
  - The bound sentence reads "above the five percent target for every model except" (the exception is Gemma-4-31B's stated probabilities on typed-decisions).
  - The guarantee result in the abstract, Learn-then-Test, met the target: 0.528 of CLINC at realised risk 0.009.
- **Problem:**
  - On held-out thresholds alone the study is 1 of 2: one met, one missed. The CSV elsewhere tallies such results:
    - arx03387, 6/12 met, is coded support;
    - arx33689, 6/7 held, is coded oppose.
  - Read that way, arx00346 is mixed. "Met its 5% target on CLINC" reports only the favourable half.
  - §4.7 l.224 says the bound exceeded the target "for every model", which is not quite what the source says. It also gives no realised risks, so it still reads as support for the threshold-miss finding.
- **Fix:**
  - Either: base the `oppose` code on the study's primary guarantee result (LTT: 5% guaranteed at 0.528 coverage, realised 0.009), and give both held-out results in D.1 and note a.
  - Or: code arx00346 as mixed/out-of-scope. In that case, note a and §3 l.128 lose "contested" for the 4 Oct recomputation (very low, not contested). Main only stays very low^c through arx33689.
  - Either way, l.224 should read: "…the realised risk was 0.049 on CLINC and 0.058 on typed decisions, and the one-sided upper bound exceeded 5% for every model but one".

**R18-3 [minor] zen22935043's row 2 support rests on a certification count, the same kind of result D.1 says is not a failed transfer.**
- **Location:** CSV row 2 zen22935043 ("5% tier certified in 0/2,000 AG News vs 191/2,000 SST-2 splits"); App. D.1 l.89; §4.9 l.392.
- **Problem:**
  - Each certification split fits and tests within one dataset, so no threshold is carried to a new setting.
  - D.1 l.87 treats arx33689's ≥19-label floor as "a limit on certification, not a failed transfer". The same reasoning applies here.
  - The authors also qualify the count:
    - "Low success of one threshold-learning rule therefore does not establish that no certifiable operating point exists" (l.477–479);
    - under another selection rule, SST-2 rose to 1,776 of 2,000 splits;
    - the Wilson bound is "approximate, not an exact finite-sample, bound" (l.153).
  - §4.9 l.392 ("a procedure with a valid bound could certify no 5% … tier") omits these qualifications.
  - The study's primary result does support row 2's second clause: calibration "differs between tasks and question forms, so it has to be checked for each" (abstract).
- **Fix:**
  - Rewrite the CSV note around that primary result. The direction is unchanged.
  - Add to l.392: "under one threshold-selection rule; the authors note that another rule certified far more splits".
  - Ratings are unchanged.

**R18-4 [nit] Two qualifiers of zen23075657 are not reported.**
- **Location:** App. D.1 l.88 ("kept the test false-positive rate at 3.24%"); §4.9 l.354 ("in a later breakdown").
- **What is missing:** the study's test items were "previously observed" and mixed-label (abstract l.11; limitations l.1039–1060). Its "later breakdown" was explicitly post hoc and exceeded the tolerance.
- **Fix:** add "on a mixed-label, previously observed test set" in D.1, and use "post hoc" in l.354.

**R18-5 [nit] Note a is worded differently in different places.**
- **Location:** note a of tab:keyfindings (l.280: "very low under the current rule"); §3 l.128 ("would have been very low").
- **Problem:** tab:certchanges note a and the script say "very low and contested".
- **Fix:** align the wording, after deciding R18-2.

## Fresh pass (task 3)

**Consistent with the script:**
- abstract and metadata ("low or very low"; 1909 characters ≤ 1920);
- §1 l.32–35;
- §3 l.122–128;
- §4.8 l.274;
- §4.9 l.319–323 and l.397;
- §5;
- §7 l.11–15 (counts only; see R18-1);
- §8 l.6;
- App. D l.47–105, with tab:certchanges (main-only and now columns).

**Disclosed:**
- the protocol deviation (§3, §4.9 l.321, §7, App. D l.48–49);
- AI coding and the second-coder κ (abstract and metadata);
- the data and scripts (§9).

**PoL2 framing:** neutral.

**Moderation:** no risk. The bundle is current. The author placeholder is known and not re-raised.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 3 | R18-1, R18-2, R18-3 |
| Nit | 2 new, plus 2 carried | R18-4, R18-5; R17-2, R17-3 |

New major or minor problems remain: yes
