# Certainty audit of tab:keyfindings (2026-10-08, regenerated after review round 19)

This file is now a summary. The source of truth is:

- `data/certainty_evidence.csv`: one row per (finding, study, system arm) for every study coded on the finding's requirement(s) (G1 for rows 1-3; G1+G6 for row 2; G2 for 4-5; G3 for 6-7; G4 for 8-10; G6 for 11-14, plus G2 for 12). Each row is `support`, `oppose`, `corroborate` (open-model evidence on a hosted/both finding, no effect on the rating) or `out-of-scope`, with a note of at most 20 words giving the decisive number or the reason. Also: window (main/update), `cited_4oct` (cited for that finding in the 4 October version, taken from the 4 October table preserved in `paper/zh/sections/04_evidence.tex`), `author_group` (studies sharing any author, computed from the .bib files), `replicated_by` (empty: no study meets D1), `given_4oct` (rating as given on 4 October).
- `scripts/rate_certainty.py`: applies §3 mechanically (design rating and preregistration from `data/quality_appraisal*.csv`; per-arm counting D3'; same-author groups count once; very low / low / moderate thresholds; opposing → contested; one-level fall when the strongest opposing study ranks ≥ the strongest supporting one; multi-clause findings encoded as 1a-1c, 6a-6b, 8a-8c, 9a-9b, 10a-10b, 12a-12b take the lowest clause; row 15 descriptive, low by judgement).
  - `python scripts/rate_certainty.py` prints given 4 Oct / 4 Oct recomputed / main only / now.
  - `--verbose` prints the counted studies per clause and evidence set (reproduced below).
  - `--check` parses tab:keyfindings and tab:certchanges and fails on any disagreement, or if tab:certchanges does not list exactly the findings whose rating differs from the 4 October rating as given or that are now contested.

Ranks: S = stronger, M = moderate, W = weaker; * = preregistered (or replicated).

## Decisions behind the coding (rounds 16 to 18; details in paper/review/AUDIT.md)

- **arx33689, hosted arm.** Jev's gate was set in advance and carried to 7 changed templates: 6 safe, 1 within bound (0.143), 0 violating.
  - Counted as an opposing, preregistered, stronger-design study for findings 2 and 14.
  - Its open arm only corroborates.
- **arx24574.** A preregistered threshold of 0.9, fixed in advance, was meant to reach 0.85 accuracy. The median task reached 0.815, and 8 of 14 tasks fell short.
  - Counted as supporting findings 2 and 14.
- **Finding 14, decided on primary results (round 17).**
  - zen23075657 opposes: test FPR 3.24%, within its 5% tolerance. Its 5.39% comes from a post hoc subset.
  - zen22935043 opposes: split conformal reached its marginal target.
- **arx00346 on finding 14 (round 18).** Counts neither way. Its held-out threshold met the target on CLINC (0.049) and missed it on typed-decisions (0.058).
- **Open-model evidence (D3').** It corroborates only; it never supports, opposes or contests a hosted or general finding.
- **4 October column.** Shows the ratings as given that day.
  - Recomputed with the current rule on the studies cited that day, only finding 14 differs. It was given as moderate and recomputes to very low.

## Current script output

```
#   scope   given 4Oct 4Oct recomp.   main only      now             finding
1   hosted  low        low            low            low             Ranks harmful content well zero-shot at low cost; often below best LLM
2   both    low        low            low c          low c           Fixed thresholds do not transfer; local fitting is needed
3   hosted  very low   very low       low            low             Errors concentrate in sub-types hidden by aggregates
4   both    low        low            low            low             Inserted opinions, optimised context and lexical lures steer decisions
5   hosted  very low   very low       very low c     very low c      Instruction injection rarely selects the attacker target
6   both    low        low            low            low             Option names can override definitions; neutral identifiers remove most
7   hosted  very low   very low       very low       very low        Defaults to one culture's values
8   hosted  low        low            low            low             Calibrated on familiar closed-choice tasks; mixed vs frontier; calibra
9   hosted  low        low            low            low             'I don't know' rarely chosen when correct; 'none' inconsistently
10  hosted  very low   very low       very low       very low        Sufficiency question detects missing information but filters less well
11  both    low        low            low            low c           Escalation to a stronger reasoner saves cost without loss of accuracy
12  both    very low   very low       very low       very low        Acceptance on agreement with an independent rule lost no macro-F1; few
13  hosted  low        low            low            low             Peer evaluators repeat Jev's most confident errors
14  both    moderate   very low       very low c     low c           Thresholds set in advance miss error targets on new data
15  both    low        low j          low j          low j           Typed models not generally worse than generative evaluators (descripti

Now: 0 moderate, 11 low, 4 very low; contested: 2, 5, 11, 14
Main only: 0 moderate, 10 low, 5 very low; contested: 2, 5, 14
Given 4 Oct: 1 moderate, 9 low, 5 very low
4 Oct recomputed (current rule, studies cited that day): 0 moderate, 9 low, 6 very low; differs from given: 14
Changed vs given 4 Oct (rating differs or now contested): 2, 3, 5, 11, 14
```

## Counted studies per clause (`--verbose`)

```
1a   oct   -> low       support 2 group(s), 2 stronger, S* no: arx29429[S], zen22885291[S] | oppose: -
1b   oct   -> low       support 2 group(s), 2 stronger, S* yes: arx24574[S*], arx27678[S] | oppose: -
1c   oct   -> low       support 2 group(s), 2 stronger, S* yes: arx24574[S*], arx27678[S] | oppose: -
1a   main  -> low       support 5 group(s), 3 stronger, S* no: arx01079[M], arx29429[S], arx33401[S], jkf87_2026replication[W], zen22885291[S] | oppose: -
1b   main  -> moderate  support 5 group(s), 5 stronger, S* yes: arx24052[S], arx24574[S*], arx27678[S], arx29769[S], zen22849329[S] | oppose: -
1c   main  -> moderate  support 6 group(s), 4 stronger, S* yes: arx01079[M], arx24574[S*], arx27678[S], arx33401[S], arx34963[W], zen22849329[S] | oppose: -
1a   now   -> low       support 9 group(s), 5 stronger, S* no: arx01079[M], arx29429[S], arx33401[S], jkf87_2026replication[W], zen22885291[S], arx03324[S], arx03935[M], arx04985[M], arx07953[S], zen23075657[S] | oppose: -
1b   now   -> moderate  support 5 group(s), 5 stronger, S* yes: arx24052[S], arx24574[S*], arx27678[S], arx29769[S], zen22849329[S] | oppose: -
1c   now   -> moderate  support 12 group(s), 6 stronger, S* yes: arx01079[M], arx24574[S*], arx27678[S], arx33401[S], arx34963[W], zen22849329[S], arx02293[S], arx03324[S], arx03935[M], arx08775[M], arx08829[W], zen23005202[W] | oppose: -
2    oct   -> low       support 4 group(s), 2 stronger, S* no: arx00346[S], arx02046[W], arx29429[S], jkf87_2026replication[W] | oppose: -
2    main  -> low c     support 10 group(s), 7 stronger, S* yes: arx00346[S], arx01006[S], arx02046[W], arx24574[S*], arx26550[S], arx27607[M], arx29429[S], arx39496[S], jkf87_2026replication[W], zen22952571[S] | oppose: arx33689[S*] | falls one level
2    now   -> low c     support 15 group(s), 10 stronger, S* yes: arx00346[S], arx01006[S], arx02046[W], arx24574[S*], arx26550[S], arx27607[M], arx29429[S], arx39496[S], jkf87_2026replication[W], zen22952571[S], arx02267[S], arx03387[S], arx04985[M], zen22935043[S], zen23050542[M] | oppose: arx33689[S*] | falls one level
3    oct   -> very low  support 1 group(s), 1 stronger, S* no: arx33401[S] | oppose: -
3    main  -> low       support 5 group(s), 2 stronger, S* no: alphaRAG[W], arx00213[S], arx02046[W], arx33401[S], zen22846597[W] | oppose: -
3    now   -> low       support 9 group(s), 6 stronger, S* no: alphaRAG[W], arx00213[S], arx02046[W], arx33401[S], zen22846597[W], arx02267[S], arx03324[S], arx07953[S], arx08675[S], arx10321[S] | oppose: -
4    oct   -> low       support 5 group(s), 3 stronger, S* no: arx01006[S], arx01834[S], arx02048[M*], arx30243[W], arx31142[S] | oppose: -
4    main  -> low       support 5 group(s), 3 stronger, S* no: arx01006[S], arx01834[S], arx02048[M*], arx30243[W], arx31142[S] | oppose: -
4    now   -> low       support 6 group(s), 3 stronger, S* no: arx01006[S], arx01834[S], arx02048[M*], arx30243[W], arx31142[S], arx04985[M] | oppose: -
5    oct   -> very low  support 1 group(s), 1 stronger, S* yes: arx28613[S*] | oppose: -
5    main  -> very low c support 1 group(s), 1 stronger, S* yes: arx28613[S*] | oppose: arx31142[S], checkpoint2026jev[W]
5    now   -> very low c support 1 group(s), 1 stronger, S* yes: arx28613[S*] | oppose: arx31142[S], checkpoint2026jev[W], arx04985[M]
6a   oct   -> low       support 2 group(s), 2 stronger, S* no: arx00346[S], arx26758[S] | oppose: -
6b   oct   -> low       support 2 group(s), 2 stronger, S* no: arx00346[S], arx26758[S] | oppose: -
6a   main  -> low       support 2 group(s), 2 stronger, S* no: arx00346[S], arx26758[S] | oppose: -
6b   main  -> low       support 2 group(s), 2 stronger, S* no: arx00346[S], arx26758[S] | oppose: -
6a   now   -> low       support 3 group(s), 3 stronger, S* no: arx00346[S], arx26758[S], arx07953[S] | oppose: -
6b   now   -> low       support 3 group(s), 3 stronger, S* no: arx00346[S], arx26758[S], arx07953[S] | oppose: -
7    oct   -> very low  support 1 group(s), 1 stronger, S* no: arx36399[S] | oppose: -
7    main  -> very low  support 1 group(s), 1 stronger, S* no: arx36399[S] | oppose: -
7    now   -> very low  support 1 group(s), 1 stronger, S* no: arx36399[S] | oppose: -
8a   oct   -> low       support 4 group(s), 2 stronger, S* no: arx01006[S], arx34024[W], arx37647[W], zen22885291[S] | oppose: -
8b   oct   -> moderate  support 4 group(s), 3 stronger, S* yes: arx24052[S], arx24574[S*], arx34024[W], zen22885291[S] | oppose: -
8c   oct   -> low       support 3 group(s), 2 stronger, S* yes: arx01006[S], arx24574[S*], arx27607[M] | oppose: -
8a   main  -> low       support 6 group(s), 3 stronger, S* no: arx00346[S], arx01006[S], arx34024[W], arx37647[W], qin2026zhdecisionbench[W], zen22885291[S] | oppose: -
8b   main  -> moderate  support 5 group(s), 4 stronger, S* yes: arx24052[S], arx24574[S*], arx26550[S], arx34024[W], zen22885291[S] | oppose: -
8c   main  -> moderate  support 14 group(s), 10 stronger, S* yes: alphaRAG[W], arx00213[S], arx00346[S], arx01006[S], arx24574[S*], arx27607[M], arx29429[S], arx29769[S], arx35342[S], arx36154[S], arx37470[W], grazian2026calibrated[S], zen22846597[W], zen22980293[S*], zen23032384[S*] | oppose: -
8a   now   -> low       support 11 group(s), 5 stronger, S* no: arx00346[S], arx01006[S], arx34024[W], arx37647[W], qin2026zhdecisionbench[W], zen22885291[S], arx03935[M], arx05107[M], arx06625[S], arx09188[S], arx09896[M] | oppose: -
8b   now   -> moderate  support 7 group(s), 6 stronger, S* yes: arx24052[S], arx24574[S*], arx26550[S], arx34024[W], zen22885291[S], arx02293[S], arx06625[S] | oppose: -
8c   now   -> moderate  support 22 group(s), 17 stronger, S* yes: alphaRAG[W], arx00213[S], arx00346[S], arx01006[S], arx24574[S*], arx27607[M], arx29429[S], arx29769[S], arx35342[S], arx36154[S], arx37470[W], grazian2026calibrated[S], zen22846597[W], zen22980293[S*], zen23032384[S*], arx02267[S], arx07953[S], arx09937[S], arx10321[S], zen22935043[S], zen22945279[W], zen23088660[S], zen23179064[S*], zen23221456[S] | oppose: -
9a   oct   -> low       support 2 group(s), 1 stronger, S* no: arx01006[S], arx34024[W] | oppose: -
9b   oct   -> low       support 2 group(s), 2 stronger, S* no: arx01006[S], arx39496[S] | oppose: -
9a   main  -> low       support 2 group(s), 1 stronger, S* no: arx01006[S], arx34024[W] | oppose: -
9b   main  -> low       support 3 group(s), 2 stronger, S* no: arx01006[S], arx39496[S], zen22864020[W] | oppose: -
9a   now   -> low       support 4 group(s), 1 stronger, S* no: arx01006[S], arx34024[W], arx07730[M], zen23119392[W] | oppose: -
9b   now   -> low       support 5 group(s), 3 stronger, S* no: arx01006[S], arx39496[S], zen22864020[W], arx03387[S], arx06425[W] | oppose: -
10a  oct   -> very low  support 1 group(s), 1 stronger, S* no: arx01006[S] | oppose: -
10b  oct   -> very low  support 1 group(s), 1 stronger, S* no: arx01006[S] | oppose: -
10a  main  -> very low  support 1 group(s), 1 stronger, S* no: arx01006[S] | oppose: -
10b  main  -> very low  support 1 group(s), 1 stronger, S* no: arx01006[S] | oppose: -
10a  now   -> low       support 2 group(s), 1 stronger, S* no: arx01006[S], arx05107[M] | oppose: -
10b  now   -> very low  support 1 group(s), 1 stronger, S* no: arx01006[S] | oppose: -
11   oct   -> low       support 3 group(s), 2 stronger, S* yes: arx02046[W], arx24574[S*], arx26550[S] | oppose: -
11   main  -> low       support 4 group(s), 2 stronger, S* yes: arx02046[W], arx24574[S*], arx26532[M], arx26550[S] | oppose: -
11   now   -> low c     support 4 group(s), 2 stronger, S* yes: arx02046[W], arx24574[S*], arx26532[M], arx26550[S] | oppose: arx02267[S]
12a  oct   -> very low  support 1 group(s), 0 stronger, S* no: arx02048[M*] | oppose: -
12b  oct   -> very low  support 1 group(s), 0 stronger, S* no: arx02048[M*] | oppose: -
12a  main  -> very low  support 1 group(s), 0 stronger, S* no: arx02048[M*] | oppose: -
12b  main  -> very low  support 1 group(s), 0 stronger, S* no: arx02048[M*] | oppose: -
12a  now   -> very low  support 1 group(s), 0 stronger, S* no: arx02048[M*] | oppose: -
12b  now   -> very low  support 1 group(s), 0 stronger, S* no: arx02048[M*] | oppose: -
13   oct   -> low       support 2 group(s), 2 stronger, S* no: arx29769[S], arx33401[S] | oppose: -
13   main  -> low       support 2 group(s), 2 stronger, S* no: arx29769[S], arx33401[S] | oppose: -
13   now   -> low       support 2 group(s), 2 stronger, S* no: arx29769[S], arx33401[S] | oppose: -
14   oct   -> very low  support 1 group(s), 1 stronger, S* no: arx33401[S] | oppose: -
14   main  -> very low c support 2 group(s), 2 stronger, S* yes: arx24574[S*], arx33401[S] | oppose: arx33689[S*] | falls one level
14   now   -> low c     support 5 group(s), 4 stronger, S* yes: arx24574[S*], arx33401[S], arx02267[S], arx03387[S], zen23050542[M] | oppose: zen22935043[S], zen23075657[S], arx33689[S*] | falls one level

#   scope   given 4Oct 4Oct recomp.   main only      now             finding
1   hosted  low        low            low            low             Ranks harmful content well zero-shot at low cost; often below best LLM
2   both    low        low            low c          low c           Fixed thresholds do not transfer; local fitting is needed
3   hosted  very low   very low       low            low             Errors concentrate in sub-types hidden by aggregates
4   both    low        low            low            low             Inserted opinions, optimised context and lexical lures steer decisions
5   hosted  very low   very low       very low c     very low c      Instruction injection rarely selects the attacker target
6   both    low        low            low            low             Option names can override definitions; neutral identifiers remove most
7   hosted  very low   very low       very low       very low        Defaults to one culture's values
8   hosted  low        low            low            low             Calibrated on familiar closed-choice tasks; mixed vs frontier; calibra
9   hosted  low        low            low            low             'I don't know' rarely chosen when correct; 'none' inconsistently
10  hosted  very low   very low       very low       very low        Sufficiency question detects missing information but filters less well
11  both    low        low            low            low c           Escalation to a stronger reasoner saves cost without loss of accuracy
12  both    very low   very low       very low       very low        Acceptance on agreement with an independent rule lost no macro-F1; few
13  hosted  low        low            low            low             Peer evaluators repeat Jev's most confident errors
14  both    moderate   very low       very low c     low c           Thresholds set in advance miss error targets on new data
15  both    low        low j          low j          low j           Typed models not generally worse than generative evaluators (descripti

Now: 0 moderate, 11 low, 4 very low; contested: 2, 5, 11, 14
Main only: 0 moderate, 10 low, 5 very low; contested: 2, 5, 14
Given 4 Oct: 1 moderate, 9 low, 5 very low
4 Oct recomputed (current rule, studies cited that day): 0 moderate, 9 low, 6 very low; differs from given: 14
Changed vs given 4 Oct (rating differs or now contested): 2, 3, 5, 11, 14
```
