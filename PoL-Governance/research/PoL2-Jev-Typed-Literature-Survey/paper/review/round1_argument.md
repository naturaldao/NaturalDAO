# Round 1 — argument / method / balance lens

Reviewer stance: independent senior reviewer (FAccT / AIES / ACM CSUR standard). Read: `main.tex`, all `sections/*.tex` (body + Appendix D), `review/PROTOCOL.md`, `data/evidence_coding.csv`, `data/grey_literature.csv`, text layer of `figures/fig_prisma.pdf` and `figures/fig_framework.pdf`, key list of `background.bib`. No file other than this one was edited.

Quick facts used below (computed from `data/evidence_coding.csv`, empirical rows only, which reproduce Fig. framework exactly):
- Codes: S = 3, Q = 65, N = 35 (103 empirical document-axis pairs).
- Of the 35 N codes, 14 (40%) rest on Zenodo *record-description* verification and 1 on an abstract; only 17 rest on full text. Zenodo rows are N at ~41% (14/34) versus ~28% (17/61) for full-text rows.
- Of the 3 S codes, only 1 is full-text verified (`arx34862`); one is a Zenodo record description, one a live web page.
- 16 entries in `background.bib` are never cited (naeini2015obtaining, verga2024replacing, panickssery2024llm, rebedea2023nemo, bai2022constitutional, zou2023universal, toyer2024tensor, kahneman2011thinking, bansal2021whole, green2019principles, buterin2014ethereum, santana2022blockchain, danaher2016threat, liang2023holistic, mitchell2019model, gebru2021datasheets).

---

## A. Does each conclusion follow from Section 4?

### NEW-arg-1 [major]
- Location: sections/08_conclusion.tex:26-27; sections/00_abstract.tex:4-5; sections/01_introduction.tex:29
- Problem: The "not a judge" conclusion is stated as a property of *typed* models ("The same evidence shows why **they** cannot serve as the judge"), but most of the failure modes listed are generic to every automated classifier/LLM judge in the corpus, and in several cited studies Jev is *less* bad than the comparators. Section 4 itself reports: JevOut flips 61.4% for Jev vs 64.9–73.2% for the three other systems (04_evidence.tex:79); injection selected the attacker target in only 1.8% (04_evidence.tex:70); Jev's source-attribution interaction was small (0.020) where one chat model's rating of the same argument moved from 0.359 to 0.639 by attributed source (04_evidence.tex:168); Jev's act-and-wrong rate stayed ≤0.143 where a fine-tuned open model reached 0.801 (04_evidence.tex:311); "I don't know" use was 10.5% vs 8.6% for a frontier generative model (04_evidence.tex:219); option-label sensitivity is long documented for LLMs (02_background.tex:48). The conclusion therefore supports "no automated system evaluated so far, typed or generative, meets judge-grade requirements", not "typed models specifically cannot be judges".
- Why it matters: The paper's headline claim attributes to a model class a deficiency the evidence shows is shared (or worse) in the alternatives. A FAccT/CSUR reader will see this as selective framing, and the PoL2 reader may wrongly infer that switching to a generative judge would fix the problem.
- Suggested fix: Reframe the thesis comparatively in abstract, intro and conclusion. Replacement for 08_conclusion.tex:26: "The same evidence shows why they should not serve as the *judge*, and it gives no reason to think that the generative judges in the same studies would do better: on context-addition attacks, source attribution and act-when-wrong rates \jev{} was as robust as or more robust than its comparators." Add one paragraph to §5 or §8 that separates typed-specific failure modes (probability vector aids attackers; no textual grounds; two-decimal grid / dummy-option confidence artefact; multi-question calls failing together) from inherited ones (label/option sensitivity, injection, miscalibration under shift, correlated errors).

### NEW-arg-2 [major]
- Location: sections/01_introduction.tex:22-23; sections/09_statements.tex:4; sections/08_conclusion.tex:11
- Problem: The synthesis rule "giving negative and qualifying results at least as much weight as confirmatory ones" is a direction-based weighting, justified circularly ("it is also what the evidence calls for: the clearest results so far are about how these models fail"). Weighting by *direction of result* is not a recognised synthesis method; weighting should be by study quality, independence, sample size and verification level. The Limitations section (08:11) then concedes the corpus may already over-represent failure studies, which compounds the bias rather than correcting it.
- Why it matters: This is the single most attackable methodological choice in the paper; it invites the reading that the conclusion was fixed in advance. It also clashes with the positionality statement, which presents the same rule as a debiasing device (09:4).
- Suggested fix: Replace 01:22-23 with: "We then code every study by the axes it informs and synthesise the evidence axis by axis, weighting studies by verification level, independence from the model's vendor and authors, sample size and design (preregistration, held-out evaluation), not by the direction of their result. We report positive, qualifying and negative findings side by side for each axis." Delete "This emphasis follows a working principle … how these models fail." Revise 09:4 and 08:11 accordingly.

### NEW-arg-3 [major]
- Location: sections/05_synthesis.tex:13; sections/08_conclusion.tex:30
- Problem: The conclusion that "emotion recognition under §4.3.3.3 is where typed models were least reliable" rests on one task (empathy annotation in peer-support conversations) in one study (arx24574). (i) Empathy detection in text is a property of a communicative act, not detection of a person's emotional state, which is what §4.3 forbids — a construct mismatch. (ii) No emotion-recognition benchmark is in the corpus, so "least reliable" is an unsupported superlative; the paper itself reports that frozen Jev achieved the best aggregate error on SemEval-2026 multilingual dimensional sentiment (04_evidence.tex:162), which is the nearest emotion-adjacent evidence and points the other way.
- Why it matters: Single-study generalisation used to support a normative recommendation (T1) and a conclusion-level claim; countervailing evidence (arx35293) is omitted at the point of synthesis.
- Suggested fix: 08:30 → "emotion-related annotation under \clause{4.3.3.3} produced the clearest case of confident near-chance performance in one study~\cite{arx24574}, although on dimensional sentiment regression a calibrated \jev{} was competitive~\cite{arx35293}". In T1 (05:13) add the SemEval result and say "one study".

### NEW-arg-4 [major]
- Location: sections/00_abstract.tex:5; sections/05_synthesis.tex:33; sections/08_conclusion.tex:27
- Problem: The 96% correlated-error figure is correctly qualified in §4 (04_evidence.tex:299: selected on Jev's most confident errors, "an upper bound on how correlated errors are in general"), but the qualification is dropped in the abstract, T4 and the conclusion ("the confident errors that matter most are shared, not corrected"). The result also concerns three flash-tier judges on rubric grading, not dispute adjudication; and arx26550 shows escalation to a *reasoning* model does work on derivable items.
- Why it matters: The selection-effect caveat is precisely what makes the number interpretable; omitting it from the headline places is over-claiming, and T4's recommendation to amend Art. 9(7) leans heavily on it.
- Suggested fix: Abstract: "…in one study, on the 84 items selected as \jev{}'s most confident errors, three flash-tier LLM judges repeated 96\% of them (an upper bound on error correlation), so escalation among similar systems can preserve them." T4 (05:33): add "on rubric grading, among flash-tier judges; escalation to a stronger reasoning model did help on derivable items~\cite{arx26550}".

### NEW-arg-5 [major]
- Location: sections/05_synthesis.tex:34-36; sections/08_conclusion.tex:13
- Problem: T4 concludes that option (b) — a human reviewer who can suspend automated execution — "better matches the evidence". But no study in the corpus measures human reviewers (Limitations 08:13 admits this), and the oversight literature the paper itself cites (parasuraman2010complacency, green2022flaws; uncited bansal2021whole) shows humans frequently fail to correct confident machine errors and also disagree among themselves (06_design.tex:31). The evidence shows AI-only escalation can preserve errors; it does not show a human end-point removes them.
- Why it matters: A causal/comparative claim (human end-point > AI-only adjudication) is drawn without comparative evidence; this is the central normative recommendation against the PoL2 text.
- Suggested fix: Replace 05:36 with: "Option (a) preserves the text; option (b) adds a check whose value is plausible from the oversight literature but untested on this task; neither is supported by direct evidence, and the choice should be revisited once human-vs-model comparisons on the \pol{} construct exist (\cref{sec:agenda})." Add an agenda item "Human reviewers vs typed detectors on the same governance items".

### NEW-arg-6 [major]
- Location: sections/08_conclusion.tex:27; sections/04_evidence.tex:131; sections/04_evidence.tex:200; sections/05_synthesis.tex:20
- Problem: Several conclusion-level generalisations rest on a single study, often at reduced verification level:
  - "their verdicts follow the names of options rather than the definitions behind them" — one study (arx26758); for hosted Jev the effect was partial (32.5% changed; AUC 0.815→0.581, "degraded but not inverted"). 04:131 "The model followed the option's name rather than the definition" holds for Laya, not Jev.
  - "they are most over-confident where people disagree" — one Zenodo preprint verified at record-description level only (zen23032384), yet it appears in the conclusion, G7 polbox, design §6 and checklist 11a.
  - "absent must be kept distinct from contested, which a single probability cannot do" (T2) — a "minimal case study" on Zenodo (zen22848952).
- Why it matters: The conclusion lists these in the indicative as general properties. With ~30% of the corpus verified only at record level and 40% of N codes coming from those rows, conclusions need provenance-weighted wording.
- Suggested fix: In 08:27 rewrite as "…in one study their verdicts tracked option names more than the definitions bound to them (strongly for an open model, partially for \jev{}), … one preregistered but record-level-verified study found them most over-confident where people disagree…". In 04:131 → "Laya followed the option's name rather than the definition bound to it; \jev{} did so in about a third of cases." More generally, see NEW-arg-12 (certainty column).

### NEW-arg-7 [major]
- Location: sections/04_evidence.tex:161; data/evidence_coding.csv (arx37647, G3)
- Problem: Cherry-picking at extraction level. The coding rationale for arx37647/G3 reads "Option rotation robust on tested subjects; degradation on low-resource languages", but §4 G3 reports only the degradation ("likewise found that all evaluated models … degraded"). The positive option-rotation robustness result is directly relevant to the "answer scale / order" paragraph two paragraphs earlier (04:137, where order effects are reported from other studies) and is omitted. Similarly, qin2026zhdecisionbench v2 "hosted Jev needed no recalibration on Chinese voice routing" (04:158) is the only hosted-Jev Chinese result and is not carried into §7 (07:11) or the conclusion's language framing.
- Why it matters: Countervailing positive evidence that appears in the authors' own coding file but not in the text is exactly what reviewers check for.
- Suggested fix: Add to 04:137 after the ordinal-order sentence: "By contrast, the 37-dataset benchmark found \jev{}'s Choice answers robust to option rotation on the subjects it tested~\cite{arx37647}." Change 04:161 "likewise" accordingly. In 07:11 add "and a revised benchmark release reporting that hosted \jev{} needed no recalibration on Chinese voice routing".

### NEW-arg-8 [minor]
- Location: sections/00_abstract.tex:4
- Problem: "median zero-shot AUROC 0.886 across 31 … benchmarks, at 63× lower cost than LLM judges" juxtaposes two different denominators: the AUROC median is over 31 benchmarks, the 63× cost is over the 19 benchmarks scored by an API LLM judge (04:13). Also "checked against full texts" (00:3) is untrue for 28 Zenodo preprints and the alphaXiv paper (~31% of the preprint corpus).
- Why it matters: Abstract precision; the verification claim is a selling point that the paper qualifies elsewhere.
- Suggested fix: "…(median zero-shot AUROC 0.886 over 31 alignment-failure benchmarks; 63× cheaper than an LLM judge on the 19 benchmarks where both were run)…" and "…checked against full texts for all arXiv papers and against record descriptions for Zenodo preprints…".

### NEW-arg-9 [minor]
- Location: sections/05_synthesis.tex:42; sections/04_evidence.tex:146
- Problem: T5 states that per-person aggregation means "these errors **would** fall unevenly on groups and become a durable label that others can manipulate". The group-bias evidence is a single non-counterbalanced blog post (simmons2026saidno), which §4 correctly says cannot exclude a position effect; no study measures differential error by speaker group on behavioural questions. The causal "would" is speculative.
- Why it matters: Causal language without causal evidence in a normative recommendation.
- Suggested fix: "…aggregated over a person's history, such errors **could** fall unevenly on groups and become a durable label that others can manipulate; no study yet measures differential error by speaker group on behavioural judgements (\cref{sec:agenda})."

### NEW-arg-10 [minor]
- Location: sections/04_evidence.tex:67, 83, 81
- Problem: (a) "This is the most consistent and most worrying group of results" — the G2 subsection opens with a result in which injection rarely succeeded (1.8%) and override markers *reduced* the effect; "most consistent" is not demonstrated (studies use different threat models, success metrics and models). (b) "An opinion is as strong as a command": 12.1% vs 10.1% "statistically tied" is a failure to reject a difference, not equivalence. (c) "The vulnerability is linked to a feature" rests on a 140-decision comparison (63.6% vs 56.4%) with no CI.
- Why it matters: Rhetorical intensifiers in the evidence section pre-empt the reader's judgement.
- Suggested fix: (a) "These results are the most directly relevant to a valve that audits hostile content." (b) Heading "An opinion moves the model about as much as an impersonated authority". (c) "…probability feedback succeeded somewhat more often (63.6\% vs 56.4\% on 140 decisions; no interval reported)".

### NEW-arg-11 [minor]
- Location: sections/05_synthesis.tex:27-29; sections/08_conclusion.tex:30
- Problem: T3 recommends running production on self-hostable models, while the evidence cited in the same paragraph shows open replicas are less accurate, include the most severe name inversion (Laya AUC 0.938→0.232) and were near chance on interaction risk. The recommendation therefore *trades accuracy and robustness for transparency*; that trade-off is a value choice, not something "the evidence" supports, and it is not named. Separately, "the transparency of Art. 4 cannot be met with a closed model" (08:30) is not charitable: Art. 4 concerns NaturalDAO's operating logic and resource flows; logged inputs, outputs, versions and calibration data of a closed component arguably satisfy process transparency, and open weights do not by themselves give the "reasoning steps" Art. 5 asks for.
- Why it matters: Fairness to the framework and transparency of the normative step.
- Suggested fix: Add to T3: "This option trades measured accuracy and robustness for inspectability; the collaboration should decide that trade-off explicitly, and re-evaluate it as open models improve." 08:30 → "and the transparency of \art{4} is hard to reconcile with a closed model whose weights and training cannot be inspected, although logging its inputs, outputs and versions meets part of it."

---

## B. Survey methodology (PRISMA 2020 / PRISMA-ScR / Cochrane rapid review)

### NEW-arg-12 [major]
- Location: sections/03_method.tex:82; sections/08_conclusion.tex:5; whole of §4–§5
- Problem: No risk-of-bias / quality appraisal and no certainty-of-evidence assessment. §3 says quality indicators (preregistration, replication, COI) were *recorded* (03:82) but they are never reported per study, never used in synthesis, and absent from the data release description. The only quality statement (08:5) borrows a third party's grading of a different, partially overlapping set of 27 studies. Yet the paper reaches recommendation-level conclusions (amend Art. 9(7), drop per-person scoring, checklist "acceptance" criteria), which under Cochrane rapid-review guidance require at least a GRADE-style certainty judgement per conclusion.
- Why it matters: Without it, a single 25-item blog post, a Zenodo "minimal case study" and a 7,193-instance preregistered benchmark carry indistinguishable weight in the narrative; this is the main reason the conclusions read as over-confident.
- Suggested fix: (1) Add a "Quality and certainty" subsection to §3 defining a 4-item appraisal for preprints (verification level; independence from vendor/model authors; held-out or preregistered evaluation; sample size/CI reported) and a 3-level certainty rating (low / moderate / very low) per synthesised claim, with rules (e.g. start "low" for preprint evidence; downgrade for single study, record-level verification, synthetic data; upgrade for independent replication). (2) Add a "Certainty" column to Table `tab:negative` and a short certainty table for the 6–8 claims carried into the abstract/conclusion. (3) Release the recorded quality indicators as columns in `papers.csv`.

### NEW-arg-13 [major]
- Location: sections/03_method.tex:65-67; sections/D_codebook.tex:7-12; data/evidence_coding.csv
- Problem: The S/Q/N codebook is asymmetric and therefore biased by construction. S requires the function to work "without conditions that would change a deployment decision"; N is triggered by any single failure ("an attack that succeeds"); everything in between is Q. Result: 3 S vs 35 N vs 65 Q. Since the paper's own thesis is that every use requires local calibration and human review, *no* study can ever be S under this rule; the Fig. framework bars then visually present "no support" as an empirical finding. The codebook's own S exemplar (arx34862) violates rule (ii)/"mixed across tasks": the text says Jev won on only 2 of 4 benchmarks with lower precision (04:27), which by the Q definition ("result is mixed across tasks") is Q. Rule (i) "main finding for that axis" is not operationalised (no tie-break when a study has both positive and negative findings of similar weight). Also, "the use that PoL2 specifies" is ambiguous: judge use or detector use? The coding should state which.
- Why it matters: Reproducibility (a second coder could not apply these rules consistently) and balance (Fig. framework is the paper's main summary visual).
- Suggested fix: Redefine codes symmetrically and relative to an explicit use: "Codes are assigned for *detector use* (\cref{sec:intro}). S: the study's primary result shows the typed model meets or exceeds its comparator on the axis under the study's own conditions. N: the primary result shows the typed model fails the axis's function or is worse than its comparator. Q: the primary result is mixed across tasks/sub-types, or success depends on a condition the study had to add (local thresholds, recalibration, human review)." Add tie-break: "if positive and negative findings are both primary, code Q". Recode arx34862 or justify. Dual-code a random 20% of rows (≥ 21 rows) and report Cohen's κ before v0.3; in the figure caption say explicitly that the bars are counts of studies, not a measure of effect or certainty (vote counting).

### NEW-arg-14 [major]
- Location: sections/03_method.tex:67; sections/D_codebook.tex:12; sections/09_statements.tex:9-10; sections/08_conclusion.tex:19
- Problem: Who did what is not reported at the granularity PRISMA (items 8–9) and rapid-review guidance require. The paper states coding was by "a single author", while the AI-use statement says "retrieval, full-text extraction, claim verification, drafting" were AI-assisted and that numbers were checked "by a separate verification pass" without saying whether that pass was human or AI. Title/abstract screening (35 abstracts, ~330 Zenodo records) is not attributed at all. Cochrane rapid reviews recommend dual screening of at least 20% of abstracts and verification of single-reviewer extraction by a second person.
- Why it matters: Single-reviewer status is disclosed for coding but not for screening and extraction; the AI role could be read as either a second reviewer or the only reviewer.
- Suggested fix: Add to §3 a "Reviewers and tools" paragraph: "Screening: one human reviewer (the author) screened all titles/abstracts; [AI system] produced a first-pass include/exclude suggestion for [n] records; disagreements: [n]. Extraction: the AI system extracted values with locators; the author checked [all / a sample of n] against the PDF. Coding: the author, informed by AI-drafted rationales." Report numbers honestly, including if no human second check occurred. Mirror this in 09:9-10.

### NEW-arg-15 [major]
- Location: sections/03_method.tex:41-48, 59-62; figures/fig_prisma.pdf
- Problem: Eligibility and flow are incompletely specified:
  1. Eligibility window is implicit ("on or after the release"); the end date (1 Oct, submission or announcement?), language restrictions, and the definition of "Jev-like typed decision model" (03:60) are not given — the latter is decisive for including Laya/ModernBERT/Kev/DeBERTa studies and network-control fine-tunes.
  2. Zenodo inclusion is conditional on the outcome of interest ("substantive studies that bear on a governance axis", 03:47): relevance-to-axes is applied as an eligibility criterion, then the axes are used to synthesise — a selection step that should be explicit and its excluded items (13 applications/tools) listed with reasons.
  3. Grey literature (11 items) has no search strategy, no sources searched and no screening counts; it is "carried over from v0.1" in the PRISMA figure. Criterion "reports original measurements" (03:62) is violated by Willison (an opinion review) which is included and used in G5.
  4. Routes (i) and (ii): the Awesome list holds 213 registry-verified papers and the tracker 52 papers; the figure says "already found or pre-release background; no new items" with no counts of how many were assessed and excluded.
  5. Arithmetic: 37 already-in-corpus + 30 included − 1 excluded = 66, but the corpus has 65 arXiv papers; the figure says "36 from v0.1 + 29 new", so the 37th already-in-corpus record is unexplained. The Zenodo "+1 by hand" in the figure is not mentioned in the text.
- Why it matters: PRISMA items 5–7 and 16a; reproducibility of the corpus.
- Suggested fix: Add an "Eligibility" paragraph listing: date window (first arXiv/Zenodo version dated 15 Sep–1 Oct 2026 inclusive), languages (any), operational definition ("a model that returns a probability distribution over caller-declared options without generating free text, or a direct comparison against such a model"), study types (empirical; non-empirical recorded but not tallied). State the grey-literature search (where, when, which terms) or label it explicitly as "convenience sample carried over from v0.1, not systematically searched". Reconcile the 37/36/65 arithmetic in text and figure and mention the hand-added Zenodo record. Move Willison to "commentary" or relax the criterion.

### NEW-arg-16 [minor]
- Location: sections/03_method.tex:41
- Problem: "rapid review following PRISMA 2020 where applicable; not preregistered" — no statement of which PRISMA items are not applicable, no deviations section, and the protocol changed between v0.1 and v0.2 (web search → API; abstract → full-text; addition of Zenodo). PRISMA-ScR or PRISMA-RR (rapid review extension) would be the more appropriate checklist given the 16-day scope.
- Why it matters: Reporting completeness; reviewers will ask for the checklist.
- Suggested fix: Add a supplementary PRISMA 2020 (or PRISMA-ScR) checklist with page locators and "not done" entries (RoB, certainty, dual screening, reporting-bias assessment), and a 4-line "Deviations from v0.1" paragraph. Consider the frame "rapid scoping review" in the title/abstract.

### NEW-arg-17 [minor]
- Location: sections/03_method.tex:85; data/evidence_coding.csv
- Problem: Zenodo items are verified at record-description level only, yet they contribute 40% of N codes and are N more often than full-text items (~41% vs ~28%). The synthesis marks them with ‡ but does not test whether conclusions survive without them (sensitivity analysis).
- Why it matters: A differential-verification bias in the direction of the conclusion.
- Suggested fix: Add one sentence and a supplementary figure variant: "Excluding record-level sources, the code distribution is S 1 / Q 43 / N 17 (full-text) …; no conclusion in \cref{sec:conclusion} depends solely on a ‡ source" — and then make that true by rewording claims that do (NEW-arg-6).

---

## C. Detector / judge distinction and falsifiability

### NEW-arg-18 [major]
- Location: sections/01_introduction.tex:27-29; sections/06_design.tex:21; sections/00_abstract.tex:6
- Problem: The distinction is not applied consistently.
  1. Abstract: decisions "end with human review". Design element 5: a hold becomes a final block "only after confirmation by **a rule or** a person" — so a model + rule can finalise a block without a person, contradicting the abstract and intro ("remain open to human review" only via appeal).
  2. Element 5 allows automatic *allow*, *repair* and temporary *hold* on agreement. A temporary hold of a person's speech is a consequential outcome decided by models alone; the definition's escape clause is "hard-to-reverse", but "temporary" and "reversible" are undefined (duration? who reverses?).
  3. The definition considers only outcomes *for the person judged*; a false *allow* (missed hate language, missed injection) can be consequential for third parties, yet automatic allow is permitted. A safety valve's principal risk is the miss.
  4. When two models must agree (element 3), the *ensemble* decides; the paper says this "keeps the typed model a detector", but the property that matters for accountability is whether any automated ensemble acts as judge.
- Why it matters: The thesis is defined by this distinction; inconsistent application makes it unfalsifiable in practice.
- Suggested fix: Tighten the definition at 01:27-28: "A *judge* is any automated component or ensemble whose output, without contemporaneous human confirmation, determines an outcome that (a) restricts a person's speech, resources or account for longer than [T, e.g. 24 h], or (b) cannot be fully reversed on appeal. A *detector* produces a recorded signal that ranks, prioritises, triggers review, or triggers only actions that are bounded in time and fully reversible." Then align element 5: "…becomes a final block … only after confirmation by a person" (or state explicitly that rule-confirmed blocks are an exception, and change the abstract). Add a sentence on misses: "automatic *allow* is itself consequential for the potential victim; its miss rate is a governed quantity alongside the false-block rate."

### NEW-arg-19 [major]
- Location: sections/08_conclusion.tex:15-18
- Problem: Falsification conditions are asymmetric and not operational. The "not a judge" half can only be weakened by *preregistered, independently replicated* evaluations, on the PoL2 construct, in Chinese, under adaptive attack, definition swaps and across languages, at error no worse than trained reviewers — a bar no near-term study can meet; yet the negative conclusions were reached from unreplicated, often single-author preprints. The "detector" half is weakened if ranking "does not survive outside English" — but the paper already concedes no study measures the PoL2 construct (01:30), so what result would count? No thresholds are given (what flip rate, AUROC, review load). There is also no condition under which *typed-ness* is shown to matter (vs generative models), which NEW-arg-1 shows is central.
- Why it matters: A conditional thesis is only useful if its conditions are testable; asymmetric standards of evidence are a balance problem.
- Suggested fix: Replace with quantified, symmetric criteria, e.g.: "We would revise 'not a judge' if, on a held-out three-valued \pol{} benchmark in Chinese, a typed model with risk-controlled thresholds (i) kept its false-block and miss rates within targets set by the collaboration, (ii) changed fewer than twice its repeat-noise share of answers under name swaps, (iii) flipped fewer than [x]\% under single-opinion insertion and a [k]-query adaptive attack, and (iv) matched trained reviewers' agreement with an independent panel — in one preregistered study with an independent replication *or* two independent studies. We would revise the 'detector' claim if on such a benchmark AUROC fell below [0.75], or two-detector agreement errors correlated above [ρ], or review load at the fitted thresholds exceeded the stated reviewer budget." Also add: "If generative judges evaluated under the same protocol pass where typed ones fail, the conclusion becomes typed-specific; until then it applies to automated judges generally."

### NEW-arg-20 [minor]
- Location: sections/06_design.tex:20, 23
- Problem: Internal inconsistency in the design: element 4 says raw probabilities must not be returned to untrusted callers because they help attackers; element 7 publishes "the probabilities" of every decision to a "tamper-evident **public** log". Post-hoc public probabilities are an oracle for offline optimisation (JevOut used 64 accepted evaluations).
- Why it matters: The reference design contradicts itself on its main G2 mitigation.
- Suggested fix: Element 7: "…the probabilities (published with a delay and coarsened to [one decimal], or held in an access-controlled audit log available to supervisors under \art{9})…", and add the trade-off between \art{4}/\art{5} transparency and attack surface to T3.

### NEW-arg-21 [minor]
- Location: sections/06_design.tex:19, 21
- Problem: Design trade-offs are asserted, not analysed. (a) Requiring two-detector agreement to block lowers sensitivity (AND rule) — misses rise — while §4 G6 already warns that strict miss limits are met by blocking more; the two pressures are not reconciled. (b) Distribution-free risk control (bates2021, angelopoulos2024) assumes exchangeability between calibration and deployment data, which the paper's own G2 evidence (adaptive attacks) and G4 evidence (calibration is local) say will not hold. (c) Separate calls per flag multiplies cost and latency, the main advantage claimed for typed models.
- Why it matters: The design is presented as following from the evidence; its weaknesses follow from the same evidence.
- Suggested fix: Add a short "Trade-offs and known limits of this design" paragraph covering (a)–(c), e.g. "risk-control guarantees hold only under exchangeability, which adaptive attackers break; they bound error on benign drift, not under attack."

### NEW-arg-22 [minor]
- Location: sections/06_design.tex:33-62 (tab:checklist)
- Problem: Called an "acceptance checklist" but no item has an acceptance criterion; most items say "report". Item 4 "reject questions whose verdict follows the name" has no threshold (Jev's 32.5% vs 1.33% noise — reject?).
- Why it matters: As written, every model passes by reporting; the checklist cannot accept or reject.
- Suggested fix: Rename "Evaluation and reporting checklist", or add a "Pass criterion" column with provisional values marked \team (e.g. item 4: "name-swap flip rate ≤ 2× repeat noise"; item 5: "\texttt{insufficient} recall ≥ 0.5 on items where it is correct"; item 8: "error correlation on confident errors below independence + [δ]").

---

## D. Fairness to PoL2 and positionality

### NEW-arg-23 [major]
- Location: sections/01_introduction.tex:47; sections/09_statements.tex:4; sections/05_synthesis.tex (T3–T5); sections/08_conclusion.tex:30
- Problem: The paper says it "takes the PoL2 governance clauses as a given specification … does not evaluate PoL2's normative or political commitments" (01:47, repeated as a debiasing step in 09:4), but §5 does evaluate them: it recommends amending Art. 9(7) (T4b), dropping or conditioning per-person scoring under §5.6 (T5), and restricting §4.3.3.3 (T1); the conclusion says provisions are "directly challenged". These are legitimate contributions, but the scope statement is then inaccurate.
- Why it matters: Readers judge the positionality statement by whether stated limits are respected.
- Suggested fix: 01:47 → "It takes the \pol{} governance clauses as the starting specification. Where the evidence bears on whether a clause can be implemented as written, \cref{sec:synthesis} identifies the tension and offers options, at least one of which preserves the text; it does not evaluate \pol{}'s broader normative or political commitments." Make 09:4 consistent.

### NEW-arg-24 [minor]
- Location: sections/05_synthesis.tex:9-14 (T1)
- Problem: Not the most charitable reading. §4.3 excludes detecting a *person's* emotional state; §4.3.3.1/§4.3.3.3 can be read as understanding emotional *content and processes in language* (the "like" vs "afraid of puppies" example is about semantics). On that reading there is no contradiction, and the paper's own "Option" is in fact the reconciliation. Presenting it as a tension overstates conflict in the text.
- Why it matters: Fairness to the framework; T1 is the weakest of the five tensions.
- Suggested fix: Retitle "T1. Understanding emotion in language versus detecting persons' emotional states" and open with: "Read together, the clauses admit a consistent interpretation — recognise emotional meaning in utterances, never infer a person's inner state — but the text does not state it, and cheap typed scoring makes the unstated boundary easy to cross." Then keep the Option as making that reading explicit.

### NEW-arg-25 [minor]
- Location: sections/05_synthesis.tex:22, 29; sections/06_design.tex:6; sections/04_evidence.tex:231
- Problem: The paper repeatedly cites the author's own workstream (polgov) as corroboration ("the evidence supports making this the rule"; "as the workstream's model catalogue already does"; "compatible with the pilot protocol"). The positionality statement mentions contribution to the workstream but not that the survey's recommendations ratify the workstream's existing design choices.
- Why it matters: Self-endorsement risk; an external reader cannot tell whether the design was derived from the evidence or the evidence read to fit the design.
- Suggested fix: Add to 09:3: "Several recommendations coincide with choices already made in the NaturalDAO governance workstream's pilot protocol, to which the author contributes; we flag each such coincidence (\cite{polgov}) so that readers can judge whether the evidence or the prior design drove the recommendation." Optionally report one point where the evidence argues *against* a current workstream choice, or state that none was found.

### NEW-arg-26 [nit]
- Location: sections/09_statements.tex:1-5
- Problem: Positionality omits (i) non-financial interests (reputation in the collaboration; PoL2's own "working principle" shaping the method, 01:23) and (ii) whether any PoL2/NaturalDAO members other than the author reviewed the tension analysis, or any external reader did.
- Why it matters: FAccT/AIES norms for positionality statements.
- Suggested fix: Add one sentence on non-financial interests and one on who, if anyone, outside the author reviewed §5 before release.

---

## E. Missing literatures

### NEW-arg-27 [major]
- Location: sections/02_background.tex:45-53; background.bib
- Problem: Related work is one paragraph, says the literature is used "to interpret the new evidence", but it is rarely used in §4–§6. 16 entries already in `background.bib` are never cited although several bear directly on claims made: verga2024replacing (panels of diverse LLM judges — the closest prior evidence on "two independent detectors", T4/design element 3); panickssery2024llm (self-preference among LLM evaluators — correlated judging); bansal2021whole and green2019principles (human–AI complementarity and limits of human oversight — needed for T4/NEW-arg-5); danaher2016threat (algocracy — directly on Art. 2 autonomy and Art. 9(7)); mitchell2019model and gebru2021datasheets (decision-record design, element 7); toyer2024tensor (TensorTrust is used in §4 G1 without citing its source); zou2023universal (adaptive attacks); rebedea2023nemo (programmable guardrails, the closest engineering precursor of a "safety valve"); naeini2015obtaining (ECE definition; the paper notes ECE is not comparable across studies); buterin2014ethereum, santana2022blockchain (DAO governance). Literatures absent from the bib that a FAccT/CSUR reviewer would expect:
  - Emotion-recognition critique: Barrett et al. 2019 (*Psychological Science in the Public Interest*), Stark & Hoey 2021 (FAccT) — central to T1.
  - Content moderation at scale: Gorwa, Binns & Katzenbach 2020 (*Big Data & Society*, "Algorithmic content moderation"); Gillespie 2018/2020 — central to the safety-valve framing.
  - Annotator disagreement in hate/toxicity labelling: Sap et al. 2022 ("Annotators with attitudes"), Davani et al. 2022 (TACL) — central to the "contested vs absent" argument.
  - Chinese offensive/hate-language resources: COLD (Deng et al. 2022), ToxiCN (Lu et al. 2023), SWSR (Jiang et al. 2022) — directly relevant to the agenda item "a PoL2 benchmark in Chinese".
  - Learning to defer / human–AI deferral: Madras et al. 2018; Mozannar & Sontag 2020 — the formal version of the cascade question in G6.
  - Calibration under distribution shift and group calibration: Ovadia et al. 2019; Hébert-Johnson et al. 2018 (multicalibration) — "calibration is local" and T5.
  - LLM-as-judge positional/label bias: Wang et al. 2023 ("LLMs are not fair evaluators").
  - Due process for automated adjudication: Citron 2008 ("Technological due process"); Elish 2019 ("moral crumple zones") — Art. 10 and the human-at-the-end recommendation.
  - Social scoring: literature on China's social credit system (e.g., Creemers 2018; Liang et al. 2018 *Policy & Internet*) — T5, given the Chinese-language source text.
  - DAO/algorithmic governance critiques: De Filippi & Wright 2018 (*Blockchain and the Law*), and empirical DAO-governance studies.
- Why it matters: A survey that maps new evidence onto "older problems" must show which findings are new; currently several typed-model failures are presented as discoveries though they replicate known LLM phenomena (see NEW-arg-1).
- Suggested fix: Expand §2.3 to ~600 words organised by axis (G1–G7), cite the unused bib entries where they bear, add the ~10 references above, and in each §4 subsection add one sentence "Relation to prior work: this replicates / extends / contradicts …".

---

## F. Structure and readability

### NEW-arg-28 [major]
- Location: sections/04_evidence.tex (whole, ~7,300 words, ~45% of the body)
- Problem: §4 is a study-by-study narrative with dense numbers; the reader loses the axis-level answer. The bottom line of each axis appears only in the polbox at the end, mixed with recommendations. There is no per-axis evidence table (study, system measured, n, design, key metric, verification, quality, code), so the reader cannot audit balance at a glance; such a table exists only implicitly in the CSV.
- Why it matters: CSUR-style surveys are judged on whether the synthesis is navigable; the length also hides the balance problems noted above.
- Suggested fix: (1) Open each G-subsection with a 2–3 sentence "Answer" box: what is established, with certainty, and the strongest positive and strongest negative result. (2) Move per-study details to an appendix evidence table (one row per document-axis pair, generated from `evidence_coding.csv` plus extracted metrics), keeping in the text only the 2–4 studies that drive each answer. Target ≤ 4,500 words for §4. (3) Separate "what the evidence shows" (end of each subsection) from "recommendations for PoL2" (consolidate into §6).

### NEW-arg-29 [minor]
- Location: polboxes in sections/04_evidence.tex:55-61, 100-105, 171-178, 225-232, 274-279, 317-325, 365-370; sections/05_synthesis.tex; sections/06_design.tex:15-24; tab:checklist; sections/08_conclusion.tex:31
- Problem: The same recommendation is stated four to five times: e.g. three-valued questions (04:231 → T2 05:21 → design element 3 → checklist item 5 → conclusion 08:31); two independent detectors (04:104 → T4 → element 3 → agenda 07:18-20); human review of confident decisions (04:322 → T4 → element 6 → conclusion). arx32160 is summarised three times (01:33-35, 02:38, 04:269-272, nearly verbatim between 02:38 and 04:270). arx36399 and zen23032384 are each discussed in G3/G4 and again in G7.
- Why it matters: Redundancy inflates length and blurs which section owns which argument.
- Suggested fix: Polboxes: keep only the *evidential implication* (one or two sentences, no \team recommendations). §5: tensions only. §6: all recommendations, each with back-references to axes. Delete the "An evidence checklist" paragraph in G5 (04:269-272) and refer to §2.1; in G7 replace the persona/disagreement paragraph (04:347-350) by a one-line back-reference.

### NEW-arg-30 [minor]
- Location: sections/04_evidence.tex:373-408 (tab:negative)
- Problem: A table of only negative and qualifying results, with no companion table of positive results, is itself an imbalance in the paper's most skimmable artefact; it mixes record-level and full-text sources without certainty.
- Why it matters: Readers who skim will take Table `tab:negative` as the paper's evidence summary.
- Suggested fix: Replace with a two-sided "Key findings" table (columns: finding, direction S/Q/N, comparator result, source, verification, certainty, clause), including at least arx29429 (AUROC 0.886), arx34862, arx37647 (calibration, selective answering), arx26550 (cascade), arx28613 (1.8%), arx33689 (act-and-wrong ≤0.143), arx35293 (SemEval), grazian2026calibrated.

### NEW-arg-31 [minor]
- Location: main.tex:57-59 (title)
- Problem: (a) The title question "Can a Typed Decision Model Be a Safety Valve?" is answered "as a detector, under conditions" — acceptable, but the paper's distinctive contributions (tensions, reference design) are not signalled. (b) "System-One Decision Models" adopts the vendor's marketing term (and Kahneman's System 1 metaphor, kahneman2011thinking is in the bib but not cited) as if it were a technical category. (c) "Survey" over-states the method for a 16-day, single-coder, unappraised review.
- Why it matters: Title accuracy and neutrality.
- Suggested fix: "Typed Decision Models as Safety Valves for AI Governance: A Rapid Review of Early Evidence on \jev{}, Mapped to the Proof-of-Love2 Framework". Use "typed decision models" throughout and, if "System One" is kept, quote it as the vendor's term at first use.

### NEW-arg-32 [nit]
- Location: sections/08_conclusion.tex:1-19
- Problem: "Limitations of this survey" contains the falsification conditions and the AI-assistance disclosure, which also appears in §09; the Limitations section and Conclusion share a file and the conclusion precedes no forward-looking summary of certainty.
- Why it matters: Readers looking for "what would change the conclusion" will look in Discussion/Conclusion.
- Suggested fix: Move "What would change the conclusion" into the Conclusion (as its last paragraph) and drop the duplicated AI-assistance sentence at 08:19 (keep it in §09).

### NEW-arg-33 [nit]
- Location: sections/04_evidence.tex:113-114 (fig:fragility caption)
- Problem: Panel (c)/(d) state that Open-Jev values are over 1,800 questions and Laya/Jev over 1,200, and the caption says the hosted version is unreported, yet the conclusion attributes the effect to `jev-1.13` (01:51, 08:18).
- Why it matters: Version scoping of conclusions.
- Suggested fix: In 08:18 "Our conclusions apply to \texttt{jev-1.13} (or the unreported hosted version in some studies) and …".

---

## Overall assessment

**Recommendation: major revision.**

The paper is unusually careful at the level of individual numbers — the full-text verification, the corrections appendix, the ‡ marking of Zenodo sources, the explicit single-coder disclosure and the "what would change the conclusion" paragraph are all to its credit, and the clause-anchored framing is a genuinely useful contribution for the PoL2 community. The axis-level reporting in §4 is mostly fair *study by study*, and several caveats (selection effect on the 96%, KITE's primary endpoint, the non-counterbalanced blog) are stated honestly where the study is described.

The problems are at the level of argument and method. (1) The headline "detector, not judge" is presented as a property of typed models when the evidence mostly shows failure modes shared by — and often worse in — the generative comparators; the comparative evidence that favours Jev is reported in §4 but disappears from the abstract, synthesis and conclusion. (2) The synthesis weights results by their direction rather than their quality, the S/Q/N codebook is asymmetric by construction (3 S vs 35 N), and 40% of negative codes rest on record-level Zenodo verification, so the summary figure and negative-results table tilt the reader. (3) There is no risk-of-bias appraisal or certainty grading, which a review that recommends amending a governance text needs. (4) The detector/judge distinction is defined loosely and applied inconsistently in the reference design (rule-confirmed final blocks; model-only temporary holds; automatic allows), and the falsification conditions are asymmetric and unquantified. (5) The tension analysis is largely fair and offers text-preserving options, but the scope statement claims not to evaluate PoL2's normative commitments while §5 does exactly that, and the self-citation of the author's own workstream as corroboration needs disclosure. Missing prior literature (content moderation, emotion-recognition critiques, annotator disagreement, Chinese hate-speech resources, learning to defer, due process, social scoring) weakens the claim that the findings are new and the PoL2 mapping is complete. §4 is too long and the recommendation layer is repeated four to five times.

None of these require new data; all can be fixed in one revision.

### The five changes that would most raise quality

1. **Make the thesis comparative and two-sided** (NEW-arg-1, -4, -6, -7, -30): state in abstract, §5 and §8 what typed models do as well as or better than generative judges, separate typed-specific from inherited failure modes, carry the 96% selection caveat and single-study qualifiers into headline places, and replace the negative-results table with a two-sided key-findings table.
2. **Fix the synthesis method** (NEW-arg-2, -13, -17): drop direction-based weighting; weight by verification level, independence, design and size; make the S/Q/N codebook symmetric and tied to *detector* use; dual-code ≥20% and report κ; add a sensitivity check without record-level sources.
3. **Add quality appraisal and certainty grading** (NEW-arg-12, -14, -15, -16): a short preprint appraisal tool, a per-claim certainty rating (GRADE-style) for every claim in the abstract and conclusion, complete eligibility criteria, reconciled flow counts, a grey-literature search description, a clear account of who (human vs AI) screened, extracted and verified, and a PRISMA/PRISMA-ScR checklist with deviations.
4. **Tighten the detector/judge definition and the falsification test** (NEW-arg-18, -19, -20, -21, -22): define consequential, time-bounded and reversible outcomes, count misses as consequential, align design element 5 with "ends with human review", resolve the public-log/hidden-probability conflict, and give symmetric, quantified conditions that would revise each half of the thesis.
5. **Restructure and connect to prior literature** (NEW-arg-27, -28, -29, -23, -5): cut §4 to ≤4,500 words with per-axis answer boxes and an appendix evidence table; move all recommendations to §6; expand related work by axis using the 16 uncited bib entries plus content-moderation, emotion-recognition, annotator-disagreement, Chinese-resource, deferral and due-process literatures; correct the scope statement so that §5's normative recommendations are acknowledged and the human-at-the-end option is presented as plausible but untested.
