# Round 38: combined review (fidelity, balance/positionality, method, consistency, legal precision, arXiv moderator)

Date: 2026-10-08. Scope: an independent pass over the whole paper after round 37 came back clean. The only change since round 37 is R37-2 (05_synthesis.tex l.56). Priorities: (1) abstract, §1 and §8 read as stand-alone claims; (2) balance in §2.3; (3) §7.1 verdict cells checked against data/evidence_coding*.csv and tab:keyfindings; (4) all legal statements; (5) PoL2 quotations checked against A_concordance.tex and scratchpad/pol/{zh,en}_*.md; (6) build, bundle and metadata. Items already resolved in REVIEW.md, AUDIT.md and rounds 12–37 are not raised again. Author-only items, such as the author-name placeholder, are not findings.

**Inputs**
- sections/05_synthesis.tex, main.pdf, main.log and arxiv-submission.zip are all dated 23:52; arxiv_metadata.txt is dated 23:49. main.log reports "Output written on main.pdf (96 pages, 2039641 bytes).", with no `!` lines, no undefined or multiply defined references, and 17 overfull boxes, the same as round 37.
- arxiv-submission.zip was unpacked to the scratchpad. Every .tex file, counts.tex, counts_update.tex and main.bbl is byte-identical to the working copy, and 00README.json names pdflatex. The zip has 7 figure PDFs, matching "7 figures" in the metadata Comments field.
- `python scripts\rate_certainty.py --check` (repository root) printed CHECK PASSED: now 0 moderate, 11 low, 4 very low; contested findings 2, 5, 11 and 14. This matches §7.2, §1 and D.
- arxiv_metadata.txt: the abstract is 1914 of 1920 characters and its text is identical to 00_abstract.tex.

## R37 status

| Item | Status | Evidence |
|---|---|---|
| R37-2 Recital 61 paraphrase | FIXED | 05 l.56 "where its outcomes produce legal effects for the parties (Recital~61)" matches Recital 61 ("when the outcomes of the alternative dispute resolution proceedings produce legal effects for the parties"). The zip copy contains the new wording. |
| R37-1 Art. 14(4)(e) in T4(a) and §8 | not applied (optional nit), carried | 05 l.42 and 08 are unchanged. |

## Fresh pass

**(1) Abstract, §1, §8 as stand-alone claims.** I checked each sentence against the body.
- Detector and judge claims: they agree with §4, tab:keyfindings and tab:verdict.
- "17 days": matches §3 (15 September to 1 October).
- "update to 8 October reversed no answer": matches §1 and D.
- "low or very low": matches the script output.
- "four contested": matches the script output.
- Chinese-construct extrapolation: §8 and §7.1 state it.
- §8's practice list matches the "What transfers" list in §7.1 item by item.

One overstatement in the abstract (R38-1).

**(2) §2.3 balance.** Each property (i)–(v) is paired with its cost. Points against PoL2 are stated:
- control by its originator;
- the chapter renumbering;
- no peer review;
- self-verification of amendments (Art. 11(1), (3), with 6(3));
- the "may accept" scope;
- the conflict with privacy;
- contrary EU requirements.

The CAC Measures are described neutrally, and §2.3 states that the Measures "would be the natural second case". The positionality statement (09) and the coincidence flags in §6 are present. There is no promotional framing.

**(3) §7.1 verdict cells.** All decisive numbers were checked against the coding rationales:

| Function | Source | Number in the cell |
|---|---|---|
| Safety valve | arx29429 | AUROC 0.886 |
| Safety valve | arx03324 | HateCheck .960 vs .976 |
| Safety valve | jkf87 | F1 0.158/0.947 |
| Safety valve | arx04985 | 97.2–100% |
| Safety valve | arx31142 | 12.1% |
| Safety valve | arx26758, arx00346 | 32.5% and 50.5 |
| Output suppression | arx03324 | 3-class .532/.604/.639 |
| Output suppression | arx07953 | 29.4% |
| Output suppression | arx33401 | 130 at confidence ≥ 0.95 |
| Correction support | arx08829 | 21.06 vs 19.82–23.31 |
| Anomaly detection | arx00376 | 9.80% vs 22.79% |
| Anomaly detection | arx09937 | 57–94% |
| Anomaly detection | arx02048 | 0.34; 21 of 76 |
| Ethical verification | arx36399 | 87%/62% |
| Ethical verification | zen23023694 | rewording vs re-runs |
| Ethical verification | zen23032384 | 0.339 |
| Ethical verification | zen23179064 | 0.88 at 55/45 |
| Adjudication | arx29769 | 242/252 = 96.0% |
| Adjudication | arx33401 | at most 5 of 130 |
| Adjudication | arx34024 | 10.5%; 53.9% "None" |
| Adjudication | arx39496 | 7% |
| Adjudication | arx37470 | 32.8% |
| Adjudication | arx24574 | 6 of 14 cleared |
| Adjudication | arx33689 | contesting study |
| Per-person quantification | simmons | 51.12% |
| Per-person quantification | arx37647, arx31142 | as cited |
| Public assessment | arx27535 | 0.93/0.96 |
| Public assessment | arx00213, arx10321 | per-factor recalibration |

Every certainty entry equals the tab:keyfindings or script rating for the finding it names:
- ranking (1), sub-types (3), steering (4), option names (6), calibration (8), "I don't know" (9) and peer errors (13): low;
- thresholds (2): low^c;
- culture (7) and agreement gating (12): very low;
- thresholds in advance (14): low^c.

The verdict paragraph's ratings also match, including "low, by judgement" for finding 15. There are no discrepancies.

**(4) Legal statements.** Each was checked against the source text:
- **AI Act:** Art. 3(39) with Recital 44, Art. 5(1)(c), 5(1)(f), 11–14 and 86(1) (Annex III except point 2), Annex III 5(a) and 8(a), and Recital 61.
- **GDPR:** Art. 22(1) and (3), which applies to the contract and explicit-consent grounds.
- **DSA:** Art. 14, 15, 16, 17, 17(3)(c), 20, 20(6) and 24(5).
- **CAC Measures:** Art. 2, 4 (chapeau, 4(1) and the non-discrimination item), 14(1) (stop generation and transmission, rectify, report to authorities), 14(2) (warning, restriction, suspension, records, report), 15 (complaint channel, published procedure and time limits, feedback) and 17 (security assessment and filing for services with public-opinion attributes or social-mobilisation capacity).

All are accurate and hedged where application is uncertain ("may reach", "by analogy"). The §2 background sentence on Art. 5(1)(f) omits the medical and safety exception, but §5 gives it, so this is not a finding.

**(5) PoL2 quotations.**
- **Matching against the source files:** I wrote a script that splits every Chinese and English excerpt in tab:concordance at "……" or "\ldots" and searches for each piece in zh_*.md and en_*.md. Every piece was found, except where list items are joined (Art. 8, Art. 10) and where the Markdown has backslash escapes (§1.4, §5.4). I checked those by hand and they are verbatim.
- **Quotations in §2.2:** all 31 checked are verbatim in en_*.md.
- **Coverage gaps:** "feeling-nothing state" and "the wisdom of love and hate" are still missing from the concordance (carried R21-3). Three further cited items are also missing (R38-2).
- **Other phrases:** the §4.3.2 "case by case" wording, the "hate attack" wording in §5.5 and "can" in §5.6 are faithful.

**(6) Build, bundle, metadata.** All consistent (see Inputs). The title, "cs.CY" and "cs.AI" categories, CC BY 4.0 licence and repository path in Comments raise no arXiv moderation issue. The author placeholder is author-only.

## Findings

**R38-1 [minor] The abstract says that all 107 studies and 7 grey sources were "read in full, appraised and coded". Only 85 were coded and 92 appraised. This brings back the problem fixed as R2-arg-7.**
- **Location:** 00_abstract.tex l.4 and arxiv_metadata.txt: "assess them against \nPapers{} studies and \nGrey{} grey sources … in its first 17 days, read in full, appraised and coded by author-directed AI agents".
- **Evidence:**
  - 03_method.tex l.59–60: of the 114 sources, \nCoded{} = 85 "are coded"; 7 are non-empirical and "recorded and appraised but not tallied"; the remaining "22 are background-tier engineering papers that are not coded".
  - counts.tex: \nAppraised = 92.
  - §1 contribution 2 is correctly qualified: "every source that bears on a requirement is read in full, appraised, and coded".
  - Round 3 recorded R2-arg-7 as resolved with the wording "the 85 relevant sources were read in full, appraised and coded". The current abstract has lost that qualifier, so the method claim in the abstract is stronger than the body.
- **Fix:** replace ", read in full, appraised and coded by author-directed AI agents (blind second coding: $\kappa = \nKappa{}$)." with "; author-directed AI agents read in full, appraised and coded the 85 that bear on them ($\kappa = \nKappa{}$)." This adds 1 character, giving 1915 of 1920. To keep "blind second coding", shorten another sentence by about 17 characters. Make the same change in arxiv_metadata.txt.

**R38-2 [nit] Three more cited Chapter 7 items are missing from tab:concordance, which claims to quote "every \pol{} passage that this paper cites or paraphrases".**
- **Location:**
  - 02b_pol2.tex l.45: "with a public process and result", cited as \art{10}. This is Art. 10(3), but the concordance row is "\art{10} (lead-in, 1, 4)".
  - 02b l.110: "lets NaturalDAO propose amendments to the welfare protocol and verify them itself (\art{11}(1),~(3), with \art{6}(3))". The concordance has only \art{11}(2) and (5).
- **Source:** zh_7.md l.90–96 and en_7.md l.95–101: 1. "NaturalDAO may autonomously propose amendment suggestions based on operational experience" / NaturalDAO可根据运行经验自主提出修订建议; 3. "Amendments require passing EAP ethical verification" / 修订需通过EAP伦理验证. en_7.md l.92: 3. "The adjudication process and result are completely public".
- **Fix:**
  - Extend the Art. 10 row to "(lead-in, 1, 3, 4)", adding "……裁决过程与结果完全公开……" / "\ldots\ The adjudication process and result are completely public \ldots" (verify the Chinese wording against zh_7).
  - Add a row "\art{11}(1), (3)" with the two items above.
  - This belongs with carried R21-3 and can be fixed together with it.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R38-1 |
| Nit | 1 new, plus 6 carried | R38-2; R17-2, R17-3, R21-1, R21-2, R21-3, R37-1 |

R37-2: FIXED.

New major or minor problems remain: yes
