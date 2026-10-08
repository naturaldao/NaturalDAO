# Brief: syncing the Chinese translation (2026-10-08)

The English paper changed substantially after the Chinese translation was made at about 13:30 on 8 October. The changes were the update search, the certainty-rating revision and 10 rounds of review. Bring the Chinese files in line with the **current** English files.

- English (authoritative): `paper/sections/<file>.tex`
- Chinese (to update in place): `paper/zh/sections/<file>.tex`
- Glossary (binding, including the section added on 2026-10-08): `paper/zh/GLOSSARY.md`

## Method
1. Go through the current English file paragraph by paragraph, and table row by table row. The existing Chinese file is your starting point:
   - **Unchanged paragraph:** keep its existing translation as is, if it is still faithful to the current English.
   - **Changed paragraph:** retranslate it, or edit it precisely.
   - **New content:** translate it.
   - **Content no longer in the English:** delete it.
2. The final Chinese file must correspond to the current English file one to one. That means the same sections, paragraphs, tables, rows, `\label`, `\cite` and `\cref`. The counts of `\cite`, `\cref`, `\Cref`, `\label`, `\begin` and `\end` must equal the English counts. Check them with a Python script.
3. Rules carried over from the first translation:
   - Faithful translation: no claims, numbers, hedges or citations added or dropped.
   - Precise academic Chinese.
   - Full-width Chinese punctuation, with “ ” quotation marks (never `` '').
   - LaTeX commands and macros kept unchanged.
   - Titles of cited works, model names and dataset names left untranslated.
   - When quoting PoL2, use the verbatim Chinese original (the Chinese column of `paper/sections/A_concordance.tex`).
4. Keep the PoL-governance framing in the Chinese abstract and in the research-question paragraph of §1 ("本文围绕 PoL（爱2证明）的治理……"). That framing is intentional.
5. **Do not** compile with xelatex; another process does that. Check only that braces and environments balance. When you edit with Python, write the script to a file and use raw strings. Shell heredocs corrupt backslashes on this machine.

## When done
Reply in no more than 4 lines:
- the files updated;
- the number of paragraphs or rows changed, roughly;
- any newly coined terms;
- anything you were unsure of.
