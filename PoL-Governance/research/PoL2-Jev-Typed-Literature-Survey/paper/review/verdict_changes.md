# Verdict changes (2026-10-08)

Instruction from the lead author: make the paper's conclusion explicit and specific to PoL2 (is hosted Jev, and typed models generally, a suitable governance tool for PoL2's safety valve, truncation, anomaly detection and adjudication?), function by function, without strengthening beyond what the certainty ratings allow.

## Verdict wording adopted

- **Decides**: "On the evidence to 8 October 2026, hosted Jev is not a suitable tool for any PoL2 function that decides" (dispute adjudication Art. 10; automatic ethical verification Art. 6(3); per-person quantification §5.6; any final block of a person's speech without a person's confirmation).
- **Detects**: for the safety valve (§5.4.1), truncation (§4.3.3.1) and anomaly detection (Art. 7), hosted Jev "is usable, but only inside the design of §6" (supported only as a recorded, three-valued, locally calibrated detector with conditions); the public-decision assessment dimension of §5.6 is usable only as an audited aggregate measurement.
- **Extrapolation**: "Even this detector verdict is an extrapolation": it rests on English binary hate-speech benchmarks; no coded study measures the three-valued construct in Chinese; Chinese emotion was weak for every system (arx08829, ~21 macro-F1); hate vs merely offensive weak for every system (arx03324, Jev 0.532).
- **Certainty**: every verdict carries its tab:keyfindings rating (0 moderate, 11 low, 4 very low; contested: thresholds do not transfer, injection rarely selects target, escalation to stronger reasoner, thresholds in advance); the text says so and says a single well-designed study on the construct could change any verdict.
- **Not typed-specific**: where compared, typed models were not generally worse (low, by judgement), so the verdict is against automated judges of this cost tier, not typed models in particular.

## Files changed

### sections/07_discussion.tex
- New `\subsection{Is hosted Jev a suitable governance tool for \pol{}?}` (`sec:verdict`) at the start of §7, with:
  - intro paragraph defining the three verdict values (NS / DC / NT) and the certainty convention;
  - `tab:verdict` (longtable, 8 rows): safety valve input blocking §5.4.1; output suppression / truncation §4.3.3.1; real-time correction support §4.3.3.2; anomaly detection and risk warning Art. 7(2)–(3); ethical verification Art. 6(3); dispute adjudication Art. 10 / Art. 9(7); per-person quantification §5.6; public-decision assessment dimension §5.6. Columns: function, requirements (G1–G7), evidence with numbers and cites, verdict, certainty (from tab:keyfindings, with ^c for contested, "not rated" for non-key single-study results), what would be needed.
  - `\paragraph{The verdict.}`: three paragraphs (functions that decide; functions that detect, with the positives and their conditions; two cross-cutting findings: attribute leakage / surrogate training from labels (arx04985) and closed-model transparency T3).
  - `\paragraph{What transfers.}`: nine model-independent lessons, each tied to a finding and a design element / checklist item / tension (three-valued questions + sufficiency; neutral identifiers + renaming test; record every decision; local calibration + temporal re-validation; agreement gating between differently built detectors; human-ended chains + blind audit; labels and probabilities kept from untrusted callers, separate calls for independent flags; score events not persons; construct benchmark in Chinese first).
- The previous §7 paragraphs (Beyond one specification; Certainty; Limitations; What would change the conclusion; Open problems) are unchanged and now sit under `\subsection{Scope, certainty, limitations and open problems}` (`sec:scope-certainty`).
- The subsection heading uses "hosted Jev" in plain text rather than `\jev{}` to avoid the bold small-caps font substitution warning.

### sections/08_conclusion.tex
- Rewritten to lead with the explicit verdict (decides: not suitable; detects: detector only, inside §6; extrapolation from English; certainty low/very low, four contested, update reversed nothing), then a paragraph on what transfers regardless of model. The PoL2-commitments paragraph ("For PoL2, several of the framework's own commitments ...") is kept verbatim.

### sections/00_abstract.tex
- Last two sentences replaced: the tensions sentence is shortened and the final sentence now states the verdict ("Our verdict for PoL2, at low or very low certainty: on current evidence Jev is not a suitable tool for any function that decides, adjudication included, and can serve the safety valve only as a recorded, three-valued, locally calibrated detector whose consequential decisions end with a person, the design we propose; even that extrapolates from English benchmarks, as no study measures the specification's construct in Chinese.").
- To stay within arXiv's 1,920 characters, trimmed elsewhere without changing claims: dropped the `\nCoded{}` and `\nKappaAgree{}` counts (kappa kept), "(\nUCoded{} more coded sources)", "Certainty is low or very low" (now in the verdict sentence), and a few words ("caller-declared" -> "declared", "data-protection" -> "data", "non-intervention in AI adjudication" -> "AI-only adjudication"). "peer evaluators repeated almost all items selected as confident errors" -> "almost all of its confident errors". Result: 1,916 characters (make_metadata.py: OK).

### sections/01_introduction.tex
- Thesis paragraph: one sentence added after the construct sentence stating the verdict for PoL2 with `\cref{sec:verdict}`.
- Contribution 4: adds "and an explicit verdict, function by function, on whether hosted Jev is a suitable tool for PoL2 on current evidence (sec:verdict)".

## Not changed
- Answer boxes, tab:keyfindings, all tables in §4, data files, appendices B/C/E. `python ../scripts/rate_certainty.py --check`: CHECK PASSED.

## Build
- `rm main.aux main.out; pdflatex -halt-on-error; bibtex; pdflatex x3`: 0 errors, 0 undefined references/citations. Pre-existing warnings only (tab:keyfindings float 29.9pt too large; small overfull hboxes in appendix longtables).
- `make_metadata.py`: 1916 OK. `make_arxiv.py`: clean-room errors=0, undefined=0.
- Pages: 92 (main.pdf and clean-room), including the new `sections/02b_pol2.tex` background section that another workstream added during this pass (it is `\input` by `02_background.tex`; not part of this change).

### background.bib (incidental, one line)
- `cac2023genai` (added by the concurrent workstream at 22:11) had a raw Chinese title, which bibtex copied into main.bbl outside any CJK environment and which stopped pdflatex with "Unicode character 生 not set up". Wrapped the Chinese title in `\zh{...}`, the convention used in `A_concordance.tex`. No other change to the bib files.
