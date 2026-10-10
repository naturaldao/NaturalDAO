# Rounds 44–46: condensing the paper into a submittable main text (v0.5, 2026-10-10)

## Goal and reference papers

The author asked for a version that meets submission norms and is submitted to arXiv only. Two reference papers were read in full on arXiv and used as structural models:

- **COMPL-AI** (Guldimann et al., arXiv 2410.07959). Translates regulatory clauses into technical requirements, evaluates against them, and moves implementation detail to appendices.
- **Policy-as-Prompt** (Palla et al., arXiv 2502.18695; FAccT 2025; primary category cs.CY). Studies large models enforcing written governance rules directly. Its main text is about 5–6k words, its abstract about 210 words, and it has about 70 references.

### Diagnosis (v0.4.1)

- The main text was about 28.6k words: 67 pages including 209 references.
- The abstract was about 300 words.
- Method (3.1k words) and evidence (8.1k words) were written in the style of a systematic-review report, which an arXiv moderator could treat as an unreviewed survey.

## Restructuring

### Main text (about 11.8k words; 20 pages of body text plus references)

| § | Section |
|---|---|
| 1 | Introduction (problem, gap, detector/judge, this work, takeaways, contributions) |
| 2 | Background and related work (including paradigms, condensed) |
| 3 | PoL2 clauses → G1–G7 |
| 4 | Method (key points) |
| 5 | Results by requirement (one subsection per requirement; update search) |
| 6 | Implications for PoL2: tensions T1–T5, reference design, verdict summary table |
| 7 | Discussion (certainty, limitations, what would change the conclusion) |
| 8 | Conclusion |

The key-findings table (tab:keyfindings) is kept unchanged. The full verdict table moves to Supplement S6, and a summary table (tab:verdict-summary) stays in the main text.

### Supplement

- **S1–S6:** the full body text of the long version, kept verbatim. Only section titles were changed, floats kept in the main text were removed, and colliding labels were given a `-full` suffix (script make_full.py, run once from the backup).
- **S7–S11:** the former S1–S5.

### Unchanged

Conclusions, certainty ratings and data are unchanged. `rate_certainty.py --check` passes; its path was changed to 05_results.tex.

## Reviews (independent agents comparing sentence by sentence against the long-version backup)

### Round 44

All numbers and citations were consistent. Findings: 8 major and about 25 minor, all fixed.

**Major:**
1. In the discussion, "each opposed by a study of comparable design" did not hold. Fixed to say that only the opposing study for the two threshold findings ranks as high as the strongest supporting study.
2. The abstract had dropped the comparative finding that typed models were "not generally worse".
3. The comparator distribution for the 14 negative codes was omitted.
4. The update search's G1 result listed only favourable evidence.
5. T4 had dropped the "contested" qualifier.
6. T4 option (b) had widened the scope of Art. 11 and dropped "untested on this task".
7. The paraphrase of AI Act Art. 5(1)(c) had become broader than the provision.
8. The comparator for "I don't know" (8.6% and 73.9%) was omitted.

**Minor:** hedges ("version not reported", "can", "on rubric grading", "on current evidence", and others); legal scope (Annex III 5(a), the medical/safety exception, DSA addressees); the stronger-design conjunction; the rule on conditions that constitute a requirement's test; and others.

### Round 45

All newly inserted sentences checked accurate. Findings: 1 borderline major and 10 minor, all fixed.

- **Borderline major:** the main text kept only the favourable Chinese evidence; added arx36965 and the vendor's CJK statement.
- **Minor:**
  - separate citations for the cost figures;
  - "on 19 benchmarks";
  - several studies opposing the threshold findings;
  - 51.6% and AUROC 0.98;
  - the local generative baseline;
  - "medical benchmark";
  - 34.2%;
  - the reason for the precautionary extension;
  - grey literature not searched systematically;
  - social-scoring wording.

### Round 46

Full independent pass. **No major findings.** 8 minor findings, all fixed:

- calibration in specialised domains for arx36965, and Laya order changes;
- "extreme case";
- "one study, multi-hop";
- cultural default limited to hosted Jev and one study;
- Hatevolution scope (English, 20 models, no typed model tested);
- the lure condition;
- scope date aligned to 8 October;
- the abstract now says per-person assessment is "permits" rather than "prescribes" (clause 5.6 says "can").

## Build

| Output | Pages | Errors | Undefined references |
|---|---|---|---|
| main | 32 | 0 | 0 |
| supplement | 87 | 0 | 0 |
| arXiv clean-room compile | 32 | 0 | 0 |

Abstract: 1812 / 1920 characters.

The Chinese translation is not yet synced; it still corresponds to the v0.4.1 long version.

## Round 47: aligning format with the reference papers, and language edit (2026-10-10)

The author pointed out that the format still differed from the two reference papers (PDFs on the Desktop) and asked for the language to show no signs of AI generation.

**Format.** Read against the PDFs:

- **Title block.** Neither paper has a date or a link in the title block; arXiv stamps the date in the left margin. The paper's `\date{}` is now empty and the supplement URL is removed.
- **Appendices.** Both papers put appendices in the same PDF after the references, lettered A, B, C. The body cites them as "App. B" or "Appendix A". The separate `supplement.pdf` is merged back into `main.pdf` as Appendices A–K. cleveref now prints "Appendix E.3"; it previously printed "Section E.3".
- **arXiv package.** The ancillary file is removed. `build.py` now builds a single PDF. In the data statement, the list of file paths became a single sentence.

**Language.**

- Rules are in `STYLE_GUIDE.md`.
- Five agents edited 18 files in parallel.
- `check_invariants.py` compares each file with its pre-edit snapshot (`Downloads/PoL2-Jev-v0.5-prelang-snapshot`). The numbers, citations, cross-references, clause numbers, count macros, inline math, quotations and floats in every file must match the snapshot exactly. All files pass.
- During the edit, the checker was found to treat `\$` as a math delimiter. Fixed.

**Independent review of the edit (main text).**

- **Borderline major (1), fixed.** "It sets ... per-person quantification" had turned a permission into an established provision. Changed to "permits".
- **Minor (13), fixed.**
  - In the abstract, "as" had become causal.
  - "Read as" had been dropped, so the authors' interpretation read as fact.
  - "However, calibration is local" had lost its contrast.
  - The contrast between the two Chinese benchmarks had been lost.
  - In "It also inverted", the referent was unclear.
  - "will settle" was stronger than the original.
  - In Annex III, "since" implied a causal link that is not there.
  - "although" set up a false concession.
  - "a second" should be "no second".
  - "What transfers" read as unconditional prescriptions.
  - "They" had an unclear referent.
  - "For persons" was vague.
- **Residual machine-like patterns (15), fixed.** These included "not X but Y", aphorisms, repeated triads, uniform rhythm, and a "Next," sentence opening.

**Build.** One PDF of 108 pages (body 20 pages, references, Appendices A–K). 0 errors, 0 undefined references, 0 multiply defined labels. The arXiv clean-room compile has 0 errors. Abstract is 1801/1920 characters. `rate_certainty --check` passes.

## Rounds 48-49: body-only PDF, online appendix, single search to 8 October (2026-10-10)

The author asked for four changes:

- Shorten the appendices and put them on GitHub. The PDF keeps only the paper body.
- Report the search as one search completed on 8 October, with no "update search".
- Align typography with the reference papers.
- Keep the appendices short and rigorous.

Done:

- **Paper (`main.pdf`):** 31 pages, of which 20 are body and the rest references. Sans-serif bold title and headings with a Latin Modern body, as in COMPL-AI.
- **Online appendix (`online_appendix.pdf`):** 27 pages, sections A to E.
  - A: clause concordance.
  - B: search, selection, codebook and second coding, plus procedural notes and "Protocol and deviations".
  - C: certainty rules and a derivation table generated by `rate_certainty.py --derivation`.
  - D: paradigms, checklist and full verdict tables.
  - E: corrections.
- **Long-form material:** the study-level evidence tables and the catalogue are kept as CSV only. The long appendix sources were removed; they remain in the v0.4.1 history and the backups.
- **Pooled counts:** `scripts/merge_all.py` pools the records of the runs of 1, 4 and 8 October and writes `counts_all.tex`.
  - Corpus: 163 studies and 7 grey sources; 133 coded; 279 study-requirement pairs, coded S 28, Q 189 and N 62.
  - Second coding: κ 0.59 over 148 pairs.
  - All per-requirement tallies, comparator counts and Fig. 1 were recomputed.
  - The certainty ratings were already computed on all studies and are unchanged.

Review round 48 found every number correct. It raised two major issues, both fixed:

1. The Method overstated which sources were searched on 8 October.
2. The written protocol of the 8 October run, and the deviations from it, were no longer disclosed. Online Appendix B now has a "Protocol and deviations" paragraph, and the Method points to it.

Round 49 (confirmation) found no major issues and six minor ones, all fixed:

- the appraisal scope;
- the cause of the 18 late additions;
- the tracker dates;
- which sets the protocol defined;
- five deviations rather than three;
- the full effect of the 8 October records when analysed separately.
