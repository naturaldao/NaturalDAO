# Language edit: style guide (v0.5, 2026-10-10)

Goal: the paper should read like an academic paper written and revised by its author. It should not read like model output. The reference style is the two papers used as models: COMPL-AI (arXiv 2410.07959) and Policy-as-Prompt (arXiv 2502.18695).

This edit changes wording only. Content stays as it is.

## Hard rules (checked by `check_invariants.py`; a file that fails is rejected)

- **Numbers, citations, references:** keep every number, `\cite` key, `\cref`/`\ref`/`\label` key, `\clause{}`/`\art{}` argument and count macro (`\nPapers{}` and the others). Keep every inline math expression, every quoted passage (` ``...'' `) and every `\gmark{}`/`\zmark{}`.
- **Floats:** do not touch `table`, `figure`, `longtable` or `tabularx` environments, including captions.
- **Hedges:** keep every hedge and scope condition. Examples:
  - hosted vs open;
  - "version not reported";
  - "in one study", "preregistered", "upper bound", "contested";
  - "by analogy", "on current evidence", "precautionary";
  - the certainty levels.
- **Claims:** do not add or strengthen any claim. Do not drop any qualification. Do not merge two findings so that one study seems to support both.
- **Text kept as is:**
  - British spelling and the paper's terms: Love Language, hate language, state of absence, detector, judge, LLM evaluators, typed decision models.
  - Run-in headings (`\paragraph{...}`) and section titles. You may reword a title that sounds like a slogan.
- **Length:** must not grow. A little shorter is welcome.

## What to change (patterns that make text read as generated)

1. **Semicolon chains and colon lists.** Sentences such as "X: A; B; and C" or three clauses joined by semicolons. Split them into separate sentences, or use ordinary subordinate clauses. Keep at most one semicolon per paragraph where it is natural.
2. **Formulaic contrasts.** "not X but Y", "not because X but because Y", "X, not Y", "the question is not ... but ...". Keep one only where the contrast is the point. Otherwise state the positive claim directly.
3. **Aphorisms and flourishes.** Lines like "turns each from a philosophical question into an engineering default", "independence must be built", "is the work that follows", "what is new is the price". Replace them with plain statements of the finding.
4. **Signposting and meta-commentary.** "It is worth noting", "Importantly", "Notably", "Crucially", "Moreover", "Furthermore", "Additionally", "In other words", "that is,", "Read together", "Put simply". Delete them, or use a plain connective ("also", "however", "so").
5. **Rule-of-three rhythm.** Lists of exactly three adjectives or clauses repeated paragraph after paragraph. Vary the rhythm; keep lists only where the items are real distinct items.
6. **Uniform sentence shape.** Every sentence the same length, opening with the subject, carrying a parenthetical. Vary the length. Move parentheticals into the sentence or a footnote-free short sentence where they hurt reading. Keep citations attached to the claim.
7. **Over-hedged double qualifiers.** "may potentially", "could possibly". Use one hedge, exactly as strong as the original.
8. **Emphatic italics and bold** used for rhetoric rather than for terms being defined. Remove the rhetorical ones. Keep italics for defined terms and paper titles.
9. **Banned vocabulary:** "landscape", "delve", "underscore", "pivotal", "robust" (except the technical sense), "nuanced", "holistic", "leverage", "tapestry", "realm", "paramount", "seamless", "foster", "multifaceted", "a testament to", "navigate" (figurative).
10. **Prose, not bullets.** Do not turn prose into bullet lists, or bullet lists into new headings.

## Process

1. Edit the assigned files in place with the Edit tool. Keep LaTeX valid.
2. Run `python paper/review/check_invariants.py <snapshot> paper/sections <files>` from the repository root. The snapshot is `C:\Users\Administrator\Downloads\PoL2-Jev-v0.5-prelang-snapshot`.
3. Fix every FAIL until all files pass.
4. Report the word count change per file, plus anything you deliberately did not change and why.
