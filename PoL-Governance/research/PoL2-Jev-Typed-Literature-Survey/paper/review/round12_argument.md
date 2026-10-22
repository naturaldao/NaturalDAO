# Round 12: argument, method and consistency lens (also acting as arXiv moderator)

Date: 2026-10-08. Scope: the update search of 8 October (UPDATE_SEARCH_2026-10-08.md) and how it is integrated into v0.3. Items resolved in rounds 1 to 11 (REVIEW.md) are not re-raised.
Inputs read: main.tex, sections/00, 01, 03, 04 (§4.8, §4.9, tab:update, tab:keyfindings), 05 (T2), 06 (tab:checklist), 07, 08, B, C, E; counts_update.tex; arxiv_metadata.txt; main.log/main.aux; data/evidence_coding*.csv, quality_appraisal*.csv, coder_agreement_update_2026-10-08.csv; review/CODEBOOK_v3.md, coding/update_coder_brief.md, coding/adjudication_update.md, agent_instructions.md, update_screening_arxiv.md; scripts/rerun_arxiv_search*.py.

## Verified (no finding)

- counts_update.tex matches the CSVs. 118 tallied update pairs: S 12, Q 92, N 14. Stronger-design pairs: 5/45/9 of 59. Sets: 30 post-window, 5 late-indexed and 13 re-screened sources (48), plus arx08089, which is non-empirical and untallied.
- Every row and column sum in tab:update checks out. In-window set: 36 pairs from 18 sources, S 5 / Q 28 / N 3. Main + in-window: 21/127/49. The comparator column sums to 15/10/27/7 plus 59 with no comparator, which is 118.
- Other §4.9 numbers check out: 12% vs 29% negative (14/118, 46/161); "9 had a generative comparator, worse in 6, four open only" (arx06744, arx07177, arx02586 and arx07327 are open); 37 of 60 negative codes lack a comparator (32 + 5).
- The App. E update arithmetic is consistent. arXiv: 46 - 10 - 5 = 31 read in full. Zenodo: 44 - 9 - 7 - 3 = 25, +1 = 26. Overall: 57 = 48 + 6 + 2 + 1.
- arxiv_metadata.txt: the abstract is 1,918 characters; the PDF has 80 pages per main.log; there are 7 \includegraphics; the zip is newer than main.pdf and contains counts_update.tex.
- The ° marks in tab:checklist (items 5–8, 10–13 and 16) agree with the sentence "Items 1–4, 9, 14 and 15 draw on …".
- The sub-type certainty rise (very low → low) is correct under §3. Four independent stronger-design studies agree (arx33401, arx07953, arx03324, arx08675). It cannot reach moderate because none of them is preregistered or replicated. arx10321 reuses the arx24052 data, but this does not matter here because arx24052 is not cited in this row, and §4.9 discloses the reuse.
- Disclosures that are adequately made: the arXiv API fallback (§3, App. E), the Zenodo counts-only problem (§3, §7), and κ 0.55 (§3, §7).

## Findings

**R12A-1 [major] The certainty rules only move upward. Rises are applied; falls are never tested.**
Location: 04_evidence.tex §4.9 ("No rating falls, and no other changes …"); tab:keyfindings caption ("no other rating changes"); 01_introduction.tex l.35 and 07_discussion.tex ("raised the certainty of two findings").
Problem: The §3 rules ask only whether ≥2 or ≥3 studies "agree in direction". They never ask what happens when an equal or stronger study points the other way, which is GRADE's inconsistency domain. As a result, adding update studies can raise a rating but can never lower one, so "no rating falls" is true by construction. The update evidence contests four rows:
- **Escalation saves cost without loss of accuracy (low).** arx09188 (stronger, hosted) found gated labels lost 0.047 NDCG@10. arx07177 (preregistered, stronger) escalated 92–100% of items. arx02267 (stronger) cut cost by only 4.3%. §4.9 itself says the evidence is "less consistent".
- **Injection rarely selects the target (very low, S).** arx04985 reports 97–100% attack success with a Jev-specific injection. The text calls the row "now contested", but the table does not mark it.
- **"I don't know"/"none" (low).** arx03387 (stronger, independent, hosted) found an explicit NONE option rejected 63.7% and 82.4% of missing answers.
- **Ranking row, clause "often less accurate than the best LLMs".** arx03324 found LLMs significantly ahead on only 1 of 4 datasets; arx03935 was level with the best LLM.

Fix: Add an explicit symmetric rule. For example: when the update adds a study of equal or stronger design pointing the opposite way, the rating drops one level or is marked "contested$^u$". Apply that rule to these rows in the table. Then replace "No rating falls" and the one-sided "raised the certainty of two findings" in §1 and §7 with the result of applying it. If the author prefers not to change ratings, mark these rows "contested$^u$" and say that the rules cannot lower a rating.

**R12A-2 [minor] The rise of the threshold row (low → moderate$^u$) partly rests on studies that bear on the neighbouring row.**
Location: tab:keyfindings, row "Fixed thresholds do not transfer", sources after "update:"; §4.9 ("one of them has been replicated").
Problem:
- zen22935043 found a 5% automatic tier certified in 0 of 2,000 splits. That is about certification on new data, which is the claim of the separate row "Thresholds set in advance miss error targets" (already moderate). §4.9 cites it under G6 for exactly that claim.
- zen23075657 shows a locally fitted threshold that worked (90.52% recall), with FPR 5.39% against a 5% tolerance. That is not a transfer test.
- The "replicated" condition rests on jkf87_2026replication. It is a weaker-design grey source, replicates only 5 of 44 legs of arx29429, and comes from the main window, so it is not a new replication.

The rise still holds on the direct transfer evidence: arx29429 and arx00346 (main window), plus arx03387 (6 of 12 transfers failed) and arx02267 (47% of splits). The table should cite only these. The two threshold rows overlap so much that the abstract's single "thresholds do not transfer" now rests on two moderate rows that share sources.
Fix:
- List only the transfer studies after "update:". arx04985 (78% → 89% with a fitted threshold, moderate design) could be added.
- Name the replication in §4.9: "arx29429, partially re-run (5 of 44 legs) by jkf87".
- Consider merging the two threshold rows.

**R12A-3 [minor] The headline "insufficient is rarely chosen" goes further than the G4 box, and the update evidence widens the gap.**
Location: 00_abstract.tex l.6 ("an explicit 'insufficient' option is rarely chosen"); 01_introduction.tex l.32; 08_conclusion.tex l.6. Compare the G4 box: "'I don't know' … rarely chosen when it is correct, and 'none' is chosen inconsistently".
Problem: The "I don't know" half rests on one weaker-design study (arx34024: 17 of 162, 10.5%). The "none" half ranges from 7% (arx39496, arithmetic) to 63.7% and 82.4% (arx03387, hosted Jev, update). §4.9 says these results "fit the box", which is true for the box but not for the abstract's merged wording.
Fix: Write "an explicit 'insufficient' or 'none' option is chosen inconsistently (7–82% of items without an answer)" or similar in the abstract, §1 and §8. The certainty question is handled under R12A-1.

**R12A-4 [minor] Main-window codes and the main κ were produced without the text of rule (iv), and a sample shows at least one inconsistent row.**
Location: data/evidence_coding.csv; 03_method.tex l.71 ("the second coders applied the same rule as stated in this section").
Problem:
- I checked all main-window G2 rows (10), G3 rows (26) and G6 rows (28) against rule (iv) as stated in App. E.
- G2 and G6 are consistent. The attack-condition G6 rows (arx31142, zen22959854, zen23038928) are defensibly Q under the rule's second clause or under tie-break (i).
- G3 has one clear inconsistency and two borderline rows:
  - **arx00831 G3 = Q.** "Reversing option order changes the answer on 32.8% … and 33.4% … rotation averaging … does not remove it". This is a failure under the requirement's own order test, and the mitigation is an added condition, so rule (iv) gives N. The update set codes the same kind of failure N: arx07327 G3, order changed the decision in 46 of 120 states.
  - **arx35865 G3 = Q (borderline N).** The base model flips 23.5% under relabelling; only the authors' added training reduces this, to 9.8%.
  - **zen22846597 G3 = Q (borderline S).** Argmax was stable in 93.3% of cases across six orders, with no added condition (n = 30).
- Effect on G3: 2/12/10 becomes 2/11/11 (or 2/10/12). The direction does not change.
- The disclosure is also incomplete. agent_instructions.md says the main blind second coder (κ 0.72) coded "from the full texts and the codebook alone", and that codebook lacked (iv). update_coder_brief.md told the update primary coders that the codebook contained rule (iv) when it did not until 8 October; per CODEBOOK_v3.md, the update second coder pointed out the gap. So "the second coders applied the same rule" is unsupported for the main sample, and the primary coders are not mentioned at all.

Fix:
- Audit every main-window G2, G3 and G6 row against (iv).
- Recode arx00831 G3 to N and log it in AUDIT.md; decide the two borderline rows.
- Reword l.71 to say which coders had the rule's text (main primary coders, main second coder, update primary coders, update second coders and the adjudicator) and that the main κ was measured without it.

**R12A-5 [minor] CODEBOOK_v3.md also differs from §3 on the design rating, and this is not disclosed.**
Location: CODEBOOK_v3.md, `quality` line ("higher … lower … moderate"); 03_method.tex §3.5.
Problem: The released file rates design `higher` without any independence condition. §3 requires that a stronger-design study "evaluated a system its authors did not build", and round 2 made that rule binding. The update coders applied independence anyway: arx07327, zen23225893 and arx06744 are rated moderate. The file also uses higher/lower where the data uses stronger/weaker. The paper discloses one gap in the codebook file (rule (iv)) but not this one.
Fix: Bring the file into line with §3 and disclose it in the same sentence as rule (iv).

**R12A-6 [minor] The in-window sets expose a recall gap in the main search that the paper only partly states.**
Location: 03_method.tex l.55 ("on 4 October 2026, when the last submissions in the window had been announced"); 00_abstract.tex ("107 studies … in its first 17 days"); §4.9 sensitivity sentence.
Problem:
- Eighteen coded studies dated within the window (5 arXiv, 13 Zenodo) were missed by the main analysis. That is 18 of 103 in-window coded studies, about 17%.
- Four of the five late-indexed arXiv papers are dated 1 October with 2610 identifiers, and 2610.08829 is dated 27 September. This contradicts the l.55 claim that the window was complete on 4 October.
- The late-indexed set cannot be told apart from a difference between search engines: the update used the web search, the main window used the API.
- The sensitivity check covers per-requirement direction only. It does not recompute the comparator statistics or the certainty of key findings for main + in-window, although three in-window studies (zen22935043, zen23075657, arx02267) are among those that drive the moderate$^u$ rise.
- Keeping the main tallies frozen was a protocol decision and is defensible, but readers need the recall figure.

Fix:
- Correct l.55.
- Add one sentence to §3 or §7 stating the recall: "18 of 103 in-window coded studies, 17%, were found only by the update search".
- State that the sensitivity check covers direction only.
- Rename "late-indexed" to "late-retrieved", or say why indexing delay rather than the search engine explains these five.

**R12A-7 [minor] The κ comparison is framed as a property of the update set, when it may describe the codebook.**
Location: 03_method.tex l.70; 07_discussion.tex l.19.
Problem: κ 0.55 (95% CI 0.36–0.70) is a census of all 118 pairs, while κ 0.72 (CI 0.42–0.94) comes from a 30-pair sample. The intervals overlap, so a real difference is not established. The census is the better estimate of how reproducible the codebook is. The adjudicator overturned the first coder in 10 of 118 pairs (8.5%). Main-window codes outside the 30-pair sample were never second-coded, so a similar share of them may be wrong (about 14 of 161).
Fix: State that the intervals overlap, that the census is the better reliability estimate, and what it implies for the main codes. Avoid wording that implies only the update set is less reliable.

**R12A-8 [nit] The equivalence of the web fallback is not shown.**
Location: scripts/rerun_arxiv_search_web.py, `size=200`, one page, no pagination; App. E l.73.
Problem: The fallback uses a different search backend from the API, and any query returning more than 200 hits would be truncated without notice.
Fix: Confirm and state that no query reached 200 results, and that the two backends may differ.

**R12A-9 [nit] The "re-screened" set is a post-protocol addition.**
Location: UPDATE_SEARCH_2026-10-08.md (two sets only); coding/update_coder_brief.md (`set` = post-window | late-indexed); §3 l.67.
Problem: The third set was added after coding began. It is used consistently in §3, §4.9, App. B and App. C, but the paper does not say it was added later.
Fix: Add "(a third set added after coding)" or similar.

**R12A-10 [nit] tab:keyfindings, a main-window table, floats inside §4.9.**
Location: 04_evidence.tex. In the source the table sits after the update G7 paragraph, and it is typeset on p. 27, inside §4.9.
Problem: This blurs the separation between main window and update that the protocol requires.
Fix: Move the table into §4.8 or place it with [t] before \subsection{Update search}.

**R12A-11 [nit] Checklist item 16 overlaps other items and its pass criterion is ambiguous.**
Location: 06_design.tex, tab:checklist item 16.
Problem:
- It overlaps item 2 (threshold certification) and item 11 (languages).
- Its only basis, dibonaventura2025hatevolution, is English-only and does not test a typed model, while the safeguard targets Chinese.
- The criterion "within a set margin of the certification period and of the repeat-noise floor" does not say which margin applies to recall and which to the flip rate.

Fix: Say "recall vs the certification period; neologism flip rate vs the noise floor". Add "re-certify with the procedure of item 2" and "in each language served (item 11)".

**R12A-12 [nit] Arguments for trimming at 80 pages (arXiv moderation).**
Location: §4.9 (pp. 23–27) and App. B/C update tables (pp. 67 and 73).
Problem: The update adds roughly 4 main-text pages and 2 appendix tables to an 80-page paper. That pushes it further towards a living systematic review, which raises the cs.CY moderation risk under the Oct-2025 rule on review and position papers. Framing was resolved in earlier rounds; this point concerns only the extra weight. The PoL2-governance framing in the title, abstract and Comments is otherwise unchanged and adequate.
Fix: Optionally shorten §4.9 to the counts paragraph, tab:update and one line per requirement, and move the per-requirement paragraphs to an appendix. A related minor point: arx06744 (author-built) and arx02293 come from the same HakemBench author, which the update appraisal should note.

## Counts

Major 1 (R12A-1). Minor 6 (R12A-2 to R12A-7). Nit 5 (R12A-8 to R12A-12).

New major or minor problems remain: yes
