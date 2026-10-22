# Proposed one-sentence insertions for the new §2.2 "PoL2 among AI-governance paradigms" (`sec:paradigms`, `tab:paradigms`)

Drafted 2026-10-08 for the lead author to integrate. No other section file was edited.

## §1 Introduction, Contributions list

Add after contribution 1 (requirements analysis), or as a clause inside it:

> \item \textbf{A comparative placement of the case.} We compare \pol{} as a text with risk-based regulation, platform content governance, training-time constitutions and specs, inference-time guardrails and DAO governance on seven dimensions (\cref{sec:paradigms}), and identify five checkable properties that make it a specification an inference-time safeguard can be tested against, each with its cost.

Shorter clause variant, appended to contribution 1:

> ..., and place the specification among five other governance paradigms to show why its clauses, unlike theirs, can be tested against evidence (\cref{sec:paradigms}).

## §1 Introduction, after "We study the question through one governance specification that makes it unusually concrete."

> \Cref{sec:paradigms} shows, by comparison with regulatory, platform, training-time, guardrail and DAO paradigms, which of its properties make that so and what each costs.

## §7 Discussion, "Beyond one specification"

Insert after the first sentence ("Any proposal that puts an automated filter ... likely to apply to it."):

> The comparison in \cref{sec:paradigms} makes this concrete: constitutional classifiers, the Chinese duty to stop unlawful generation and the DSA's provisions on automated means each move toward an inference-time interception layer, and each then needs an answer to G1--G7 that its own text does not yet give.

## Abstract (≤ 1 clause)

Replace "...an open governance text prescribing an AI ``safety valve''..." with:

> ...an open governance text that, alone among the regulatory, platform, training-time, guardrail and DAO paradigms we compare, prescribes in citable clauses an AI ``safety valve''...

## Notes for integration

- The table uses `tabularx` with the existing `L` column type and `\footnotesize`; paradigms are rows and seven dimensions are columns, as requested. If it overflows, the first fix is `\scriptsize` (already used for a table in §7); the second is to transpose (dimensions as rows), which needs no textual change.
- `\cref{sec:g2}`, `\cref{sec:evidence}`, `\cref{sec:design}`, `\cref{sec:synthesis}`, `\cref{tab:clauses}` and `\cref{tab:concordance}` are forward references to existing labels; check the labels still exist after any restructuring.
- The comparison between the two PoL2 snapshots (2e094d3, 27 Sep; 5791ae3, 30 Sep) is described in the prose as "three days apart"; adjust if §2.1 changes its dates.
