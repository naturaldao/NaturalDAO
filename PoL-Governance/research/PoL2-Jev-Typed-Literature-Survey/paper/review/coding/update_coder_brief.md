# Brief for primary coders: update search of 8 October 2026

Root: `C:\Users\Administrator\Downloads\PoL2-Jev-Typed-Literature-Survey`

## Read first
- `paper\review\UPDATE_SEARCH_2026-10-08.md` (protocol)
- `paper\review\CODEBOOK_v3.md` (binding: S/Q/N for **detector** use, rule (iv), comparator field, design rating)
- `paper\sections\03_method.tex`, especially tab:clauses (what G1–G7 ask)
- The answer boxes in `paper\sections\04_evidence.tex`, so you know what each requirement's current reading is
- Two or three rows of `paper\review\coding\coding_group1.csv` and `quality_group1.csv`, to see the expected depth of a rationale
- The screening note for your documents: `paper\review\update_screening_arxiv.md` or `update_screening_zenodo_grey.md`

## For each assigned document
1. Read the **full text**: `C:\Users\ADMINI~1\AppData\Local\Temp\claude\C--Users-Administrator-Downloads-PoL2-Jev-Typed-Literature-Survey\5604ea6b-ea90-485c-a48d-e4d8bbecf48f\scratchpad\update\<doc>.txt`. If a passage is garbled, fetch the arXiv HTML or the Zenodo file.
2. Decide its tier:
   - **coded**: it bears on at least one of G1–G7;
   - **context**: on topic, but bears on none;
   - **non-empirical**.
3. For every requirement it bears on, write one row in `coding_update_<group>.csv` with the columns
   `doc,axis,code,empirical,system,jev_version,comparator,rationale,set`.
   - `doc` ids look like `arx02267` or `zen23179064`.
   - `system` is `hosted`, `open` or `hosted+open`.
   - `comparator` is `better`, `similar`, `worse`, `mixed` or `none`, describing the typed model against generative evaluators on that requirement.
   - `set` is `post-window` or `late-indexed`.
   - The rationale is one or two sentences with **exact numbers and a locator** (section, table or figure). Never invent or round numbers beyond the source.
4. Write one row per document in `quality_update_<group>.csv` with the columns `doc,verification,independence,design,size_uncertainty,quality,notes`.
   - Use the vocabulary of `quality_group1.csv`.
   - `independence`: is the study by the system's own authors or the vendor?
   - `design`: preregistered, held-out, single-run, case study or non-empirical.
   - `size_uncertainty`: n+CI, n only, or none.
5. Write a 2–4 line note per document in `docs_update_<group>.md`. Cover what was tested, the key numbers, the tier, and **whether it confirms, qualifies or contradicts the current answer box** for each requirement coded.
   - Flag especially:
     - anything about **hate speech, toxicity or content moderation** (PoL2's 安全阀 and 恨语);
     - **emotion recognition** (tension T1);
     - **Chinese-language** data;
     - **three-valued outputs or abstention**.

## Rules
- Code what the paper shows, not what it claims in its abstract.
- Code the typed-model results, not the authors' own non-typed system.
- Authors-built typed models count, with `independence` = author-built system.
- Do not open the other groups' files.
- Do not edit the paper.

When done, reply with up to 8 lines:
- the number of documents per tier;
- the number of rows per code (S/Q/N);
- any finding that would **change the direction** of an answer box (quote the numbers).
