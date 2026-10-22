# Round 1 — lens 5 (arxiv-pol2): arXiv moderation risk and PoL2 fidelity

Reviewer: independent arxiv-pol2 reviewer, 2026-10-04. No file other than this one was edited.

## Verdict: arXiv acceptance risk HIGH (as currently framed)

1. **The paper calls itself a review.** The title, Section 3 ("Survey method") and the abstract ("We survey...") all say "survey". The 31 Oct 2025 arXiv CS practice says that review/survey articles and position papers without documented peer review "will be likely to be rejected and not appear on arXiv". The cs.CY carve-out in that post covers *scientific research papers* on the societal impact of technology ("These are scientific research papers and are not subject to this moderation practice change"). It does not cover surveys. Choosing cs.CY as primary therefore does not by itself exempt a paper that announces itself as a survey.
2. **Moderators may read it as project documentation.** It has an internal-memo voice: ★ "decision by the team" markers, "Design implications for NaturalDAO", "a reference document for the PoL2 collaboration", and an author who contributes to the framework being analysed. The subject is a niche, non-peer-reviewed, strongly normative manifesto. That invites the "not scholarly / promotional" reading. The disclosure is honest, but the framing still centres the project.
3. **Bundle and metadata are mechanically sound**, apart from the author-name syntax and the dead `\typeout`. All 158 `\cite` keys match the 158 `\bibitem`s in `main.bbl` (bbl newer than every .bib; arxiv/main.bbl identical). Every bundled .tex matches its source after comment-stripping. All fonts in main.pdf and the 7 figure PDFs are embedded (no Type 3). Zip = 25 flat files, 400 KB. Abstract = 1598 chars, no LaTeX.

**What would lower the risk to medium/low:**
- (a) Get peer review first (journal or main-track conference) and submit with the journal ref/DOI. Or:
- (b) Rewrite it as a research paper in cs.CY. The primary contribution would become the original, clause-level policy analysis: five tensions, mapping onto the EU AI Act, GDPR and DSA, and a reference design for automated speech/welfare decisions. The 94-paper evidence base would become a documented method section, not the headline. "Survey" would be dropped from title, abstract and section names, and the framing made neutral rather than project-internal (see NEW-arx-1 to -5).

Reclassification risk: if moderators decide it is mainly about LLM evaluation, they will move it to cs.CL/cs.AI. There the review rule applies with no ambiguity. Foregrounding societal-impact questions reduces that risk: automated content moderation, AI-only adjudication, per-person scoring, emotion recognition, and regulatory compliance.

Note: the checklist `C:\Users\Administrator\Desktop\arxiv-submission-requirements.md` does **not exist** (`cat: No such file or directory`; no similarly named file found under the user profile, depth 4). I therefore reviewed against arXiv's public pages, all of which were reachable on 2026-10-04:
- moderation: https://info.arxiv.org/help/moderation/index.html
- 2025-10-31 blog post on review articles and position papers
- CS category list: https://arxiv.org/archive/cs

PoL2 fidelity summary:
- All 28 cited clause numbers exist at `5791ae3`, and every Chinese excerpt in Appendix A appears in the source; deviations are trivial (see NEW-arx-24).
- The renumbering history (2e094d3 → 5791ae3) and the v0.1 heading "3.3.3" are accurate.
- On `main` there has been no content drift in any cited clause, only the EAP file rename and a one-word edit in §1.4 outside the quoted sentence.
- The problems are in the English rendering: the "official translation" column is paraphrased, and there are several modal or qualifier shifts ("can" turned into "expects", "where necessary" dropped, "cognitive calibration" read as probability calibration).

**Findings: 25 (major 3, minor 15, nit 7).**

---

## Part 1 — arXiv acceptance risk

### NEW-arx-1 [major]
- Location: main.tex:58-60 (title); sections/03_method.tex:1; sections/00_abstract.tex:3; arxiv_metadata.txt:2
- Problem: The paper describes itself as a survey everywhere: title "A Survey of Early Evidence...", "\section{Survey method}", "We survey the first sixteen days...". Under arXiv's Oct-2025 CS practice, survey/review articles need documented peer review or are "likely to be rejected". The cs.CY exception covers research papers on societal impact, not surveys. A moderator who reads only the title and abstract will classify it as a review.
- Evidence: blog.arxiv.org/2025/10/31/...: "Review/survey articles or position papers submitted to arXiv without this documentation will be likely to be rejected and not appear on arXiv." And, on cs.CY / physics.soc-ph societal-impact papers: "These are scientific research papers and are not subject to this moderation practice change."
- Suggested fix: Pick one of two routes:
  - Obtain peer review first (journal, or main-track conference; workshops do not qualify) and submit with the DOI.
  - Re-frame as an original policy-analysis paper. New title, e.g. "Typed Decision Models as Automated Safeguards in a Clause-Based AI Governance Specification: Evidence, Tensions and a Reference Design". Rename §3 to "Evidence base and coding method". Lead the abstract with the governance/societal question and the five tensions, and present the corpus as the method.

  Do not merely delete the word "survey" while keeping a survey structure; moderators judge content. Making the clause analysis and regulatory comparison (§5) the core contribution is what makes the cs.CY research-paper claim honest.

### NEW-arx-2 [major]
- Location: sections/00_abstract.tex:2-6; arxiv_metadata.txt (Abstract, Primary category)
- Problem: cs.CY covers "impact of computers on society, computer ethics, information technology and public policy, legal aspects of computing". The abstract contains no societal or policy vocabulary. It is mostly benchmark numbers (AUROC, F1, AUC, %), which reads as cs.CL/cs.AI evaluation. Several societal-impact elements are already in the body but missing from the abstract:
  - AI-only dispute adjudication
  - automated blocking of speech and withholding of welfare
  - per-person behavioural scoring
  - emotion recognition
  - comparison with the EU AI Act Arts. 5, 14, 86, GDPR Art. 22, DSA Arts. 17/20 and the Santa Clara Principles (05_synthesis.tex:45-50)

  This raises the risk of reclassification to cs.CL/cs.AI, where the review rule applies without ambiguity.
- Evidence: arxiv.org/archive/cs, cs.CY description quoted above. The abstract has six sentences; none mentions regulation, rights, oversight, speech or welfare.
- Suggested fix: Rewrite the abstract so that sentences 1–2 state the societal question: can cheap automated classifiers be trusted to block speech, flag people, or adjudicate disputes in an autonomous AI-governance proposal? Keep at most two headline numbers. Add one sentence on the regulatory comparison and the specific conflicts found: non-intervention vs human oversight (EU AI Act Art. 14, GDPR Art. 22), and per-person scoring vs the social-scoring prohibition (EU AI Act Art. 5(1)(c)). Keep cs.CY primary, with cs.AI and cs.CL as cross-lists.

### NEW-arx-3 [minor]
- Location: sections/01_introduction.tex:45-49; sections/05_synthesis.tex:7; sections/06_design.tex:1; sections/04_evidence.tex (polbox "Implications for PoL2", 9 ★ markers); main.tex:52-54 (polbox title)
- Problem: The voice is that of an internal design memo for one project, which moderators can read as project documentation or advocacy rather than scholarship. Examples:
  - "This survey is a reference document for the PoL2 collaboration"
  - "Recommendations that require a decision by the team are marked ★"
  - "All five require a decision by the team★"
  - "\section{Design implications for NaturalDAO}"
  - "the collaboration to consider"

  arXiv requires a "sufficiently neutral tone" and declines material that is not "original or substantive research".
- Evidence: `grep -c team sections/*.tex` → 04_evidence 9, plus one each in 01, 05, 06, 07, 08, 09. info.arxiv.org/help/moderation: "professional communication, and sufficiently neutral tone".
- Suggested fix:
  - Remove the ★ "team" device from the arXiv version (keep it in the repo version).
  - Retitle §6 "A reference design for a clause-governed safety valve", and the polbox "Implications for clause-based governance (PoL2 case)".
  - Address recommendations to "designers of such a layer", not "the team".
  - Replace "reference document for the PoL2 collaboration" with a neutral statement of purpose.

### NEW-arx-4 [minor]
- Location: sections/02b_pol2.tex:4-5; sections/02_background.tex:42-53 (Related work)
- Problem: PoL2 is introduced as "a governance proposal published by the NaturalDAO collaboration" without telling the reader what kind of text it is:
  - a community-authored, non-peer-reviewed, explicitly normative and political manifesto
  - e.g. §5.5 calls refusal to accept PoL2 governance "对人类核心伦理的仇恨攻击"
  - §4.3.2 calls for a ban on weapon ownership
  - Ch. 5 characterises existing civilisation as "富仇文明"

  The paper says it "does not evaluate PoL2's normative or political commitments" (01:47). In a cs.CY paper, not situating the object at all reads as uncritical. There is also no related work on comparable value specifications or on DAO/algorithmic governance, so PoL2 appears sui generis. Comparable work includes constitutional/model-spec approaches, the literature on automated content moderation and algorithmic adjudication, and DAO governance studies.
- Evidence: PoL/5. AI和人类文明的治理….md §5.5 bullet 2: "否则，其行为就是对人类核心伦理的仇恨攻击。" Related work (02_background.tex:42ff) covers only classifiers and prompt injection.
- Suggested fix: Add 2–3 sentences in §2b that describe PoL2 neutrally as a case: authorship (originated by one author, ~8 contributors per PoL/Readme.md), status (non-peer-reviewed, CC0, versioned on GitHub), scope, and why it is a useful case, namely that it is unusually explicit about automated interception and AI-only adjudication. Add a related-work paragraph on value specifications (e.g. constitutions/model specs), algorithmic adjudication/moderation, and DAO governance, so the contribution generalises beyond one project.

### NEW-arx-5 [minor]
- Location: main.tex:58-60; make_metadata.py:13-14
- Problem: The title is 30 words (~185 characters), has three layers (question, survey subtitle, mapping clause), and carries two niche proper nouns ("Jev", "Proof-of-Love2"). It is hard to parse and reads as product- and project-centred. "System-One Decision Models" is vendor terminology ("System One", TypeSafe AI) used as if it were a generic class.
- Evidence: TITLE string in make_metadata.py.
- Suggested fix: Use ≤15 words, a generic class name, and the societal question first. For example: "Can Typed Decision Models Serve as Automated Safeguards in AI Governance? Evidence and a Clause-Level Analysis of the PoL2 Specification". Use "typed decision models" (the paper's own generic term) rather than "System-One".

### NEW-arx-6 [major]
- Location: arxiv_metadata.txt:5; make_metadata.py:15; main.tex:62-66
- Problem: In the arXiv metadata author field, parentheses after a name are parsed as an **affiliation**. "Shenton (Shentao) Yan" would be indexed as author "Shenton Yan" with affiliation "Shentao" or malformed, which breaks the author listing and citation indexing (Google Scholar, INSPIRE, Semantic Scholar). Separately, the PDF author block puts "NaturalDAO contributors" under the name, which looks like a collective co-author that the metadata does not list.
- Evidence: arXiv metadata help: affiliations are given "in parentheses after the author name". AUTHORS = "Shenton (Shentao) Yan".
- Suggested fix:
  - Metadata author: "Shentao Yan" (the name used in pol2.bib `survey01` and on the PoL/Readme as 鄢申涛). Optionally "Shentao Yan (Independent researcher)" or a real affiliation.
  - PDF: "Shentao Yan" with an affiliation line and a contact email. Do not list "NaturalDAO contributors" as if it were an author or institution; mention the collaboration in Acknowledgements.
  - Use one romanisation consistently in the paper, metadata and CITATION.cff.

### NEW-arx-7 [minor]
- Location: arxiv_metadata.txt (Comments); sections/09_statements.tex:13-15 (Data and code availability)
- Problem: The Comments field and the data statement point to the public repo path for "Data, evidence coding and figure scripts" and to "Full texts of the 41 Creative-Commons-licensed papers". On `naturaldao/NaturalDAO@main` (checked 2026-10-04), that directory has:
  - `data/`: only grey_literature.csv, papers.csv, papers.json, pol2_axes.json, pol2_mapping.csv, sources
  - no `evidence_coding.csv`, no `zenodo_preprints.csv`, no `paper/` sources or figure scripts
  - `papers/`: 24 PDFs, not 41

  These are all present locally, so the published claim is currently false.
- Evidence: `gh api repos/naturaldao/NaturalDAO/contents/PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey/data?ref=main` → 6 entries without evidence_coding.csv/zenodo_preprints.csv; `.../papers?ref=main` → length 24; local `data/` contains both missing CSVs, and local `papers/` has 43 entries.
- Suggested fix: Push the v0.2 data, coding, scripts and LaTeX sources before submitting. Pin the Comments/Data statement to a tag or commit (e.g. `.../tree/<sha>/PoL-Governance/...`) or a Zenodo DOI rather than `main`. Make the "41" count match what is published.

### NEW-arx-8 [minor]
- Location: sections/09_statements.tex:15
- Problem: Redistributing full texts of arXiv papers is allowed only for CC-licensed ones. arXiv's default "non-exclusive license to distribute" does not permit third-party redistribution, and CC BY-NC/ND terms carry conditions. A link to a repository that redistributes PDFs with wrong licences could attract a rights complaint. The count mismatch (24 published, 41 claimed, 43 local files) suggests the licence audit is not finished.
- Evidence: see NEW-arx-7 counts. The 2e094d3→5791ae3 compare shows 24 `papers/*.pdf` added.
- Suggested fix: Add a `papers/LICENSES.csv` (arXiv id, licence URL, verified date). Keep only CC BY / CC BY-SA / CC0 (and NC versions, with attribution, if acceptable). State the per-licence count in the statement.

### NEW-arx-9 [nit]
- Location: arxiv_metadata.txt (no licence line); README/CITATION
- Problem: No licence choice is recorded for the arXiv form. The survey's data are CC0, the PoL2 text it quotes is CC0, and the bundled figures are the author's own.
- Evidence: arxiv_metadata.txt has Title/Authors/Abstract/Comments/Category only.
- Suggested fix: Choose CC BY 4.0 for the arXiv version (maximises reuse and keeps attribution; compatible with the CC0 inputs). Or choose CC0 1.0 for full consistency with the repository. Avoid the default arXiv non-exclusive licence if the intent is open reuse. Record the choice in arxiv_metadata.txt.

### NEW-arx-10 [minor]
- Location: main.tex:76 (last line, arxiv/main.tex likewise)
- Problem: `\typeout{get arXiv to do 4 passes: Label(s) may have changed. Rerun}` sits **after** `\end{document}`, so TeX never reads it and the trigger has no effect. With longtable, cleveref and natbib, label convergence may need the extra pass.
- Evidence: `grep -c "get arXiv" main.log` → 0.
- Suggested fix: Move the line to just before `\end{document}`, or into the preamble. Re-run make_arxiv.py and confirm the string appears in main.log.

### NEW-arx-11 [nit]
- Location: main.tex:27 (hyperref options)
- Problem: `bookmarks=false`, and no `pdftitle`/`pdfauthor`. pdfinfo reports empty Title and Author, so PDF readers and indexers show no title, and the arXiv PDF has no outline for a 52-page document.
- Evidence: `pdfinfo main.pdf` → "Title: (empty) Author: (empty)".
- Suggested fix: Add `pdftitle={...},pdfauthor={Shentao Yan}` via `\hypersetup`. Enable `bookmarks=true` and use `\texorpdfstring` for any heading that contains `\zh{}` or `\jev{}`.

### NEW-arx-12 [nit]
- Location: main.log (31 "Overfull \hbox (5.80287pt too wide)" warnings, consecutive lines 66–79 etc., inside a longtable — most likely B_catalogue.tex)
- Problem: Systematic 5.8 pt overflow in a long table (one column-width sum slightly exceeds `\linewidth`).
- Evidence: `grep -c Overfull main.log` → 31, all 5.80287pt.
- Suggested fix: Reduce one `p{}` column width by 0.01\linewidth, or use `@{}` padding as in A_concordance.tex.

### NEW-arx-13 [nit]
- Location: make_arxiv.py:84-90; make_metadata.py:43
- Problem:
  1. The "clean-room" compile uses local MiKTeX, which installs missing packages on the fly. It does not prove compatibility with arXiv's TeX Live, in particular CJKutf8 + gbsn (arphic) fonts, which TeX Live does ship.
  2. The Comments string hard-codes "52 pages, 7 figures" instead of reading the page count from the log.
- Evidence: `pdffonts` shows gbsn Type 1 fonts embedded locally; make_metadata.py literal "52 pages, 7 figures".
- Suggested fix: Run the clean-room compile once in a TeX Live 2025 container (e.g. `texlive/texlive:latest`), or check arXiv's preview carefully for the Chinese glyphs in Appendix A. Derive the page count from main.log in make_metadata.py.

---

## Part 2 — PoL2 fidelity (NaturalDAO commit 5791ae3)

What I checked:
- the files `PoL/1.…md`, `PoL/4. PoL之伦理对齐协议.md`, `PoL/5. AI和人类文明的治理….md` and `PoL/7. 人类公共福利的治理协议.md`, and the English `PoLEn/*.md`, all fetched via `gh api ... ?ref=5791ae3`
- the compare `2e094d3...5791ae3`
- the compare `5791ae3...main`

### NEW-arx-14 [minor]
- Location: sections/A_concordance.tex:4, 12, 14 (column header "English (official translation)") and rows 25–53
- Problem: The column claims to give "the wording of the official English translation", but most rows are the reviewer-author's paraphrases, not PoLEn text. Some paraphrases shift meaning:

  | Clause | Paper | PoLEn (5791ae3) |
  |---|---|---|
  | 1.4 | "Because inner emotional experience is hard for others to confirm" | "Since an individual's inner emotional experience is difficult for others to confirm" |
  | 4.3.1 | "Treating every person equally is not the same as treating every person's behaviour equally." | "treating every person equally and treating every person's behavior equally cannot be equated!" |
  | 4.3.2 | "Thoroughly remove the toxins of hate language." | "Thoroughly clear the toxins of hate language" |
  | 4.3.3 | "PAI records and publishes boundary statements." | "PAI records and publicizes **personal** boundary declarations" |
  | 4.3.3.2 | "hate-language recognition" | "hate-language identification" |
  | 5.5 | "Any large language model can be brought under PoL2 governance." | "Any large language model **may accept** governance under 'Proof of Love2.'" (voluntary) |
  | 5.6 (2nd) | "Provide PoL2 evaluation dimensions in public decision-making." | "Introduce Proof of Love2 as a dimension of assessment in public decision-making" |
  | Art. 9(2) | "Duty to explain" | "Obligation to explain" |
  | Art. 9(7) | omits second half | "...; issues raised through questioning are handled autonomously by NaturalDAO." |
  | Art. 11(2) | "public questioning" | "universal questioning period" |
- Evidence: PoLEn/4. PoL2 Ethical Alignment Protocol.md lines 32, 54, 76, 123; PoLEn/5. The Governance….md lines 150, 169; PoLEn/7. Governance Protocol….md lines 78, 83, 98; PoLEn/1.…md line 68.
- Suggested fix: Either paste the PoLEn sentences verbatim (with "…" for omissions), or relabel the column "English (condensed from the official translation)". Fix §5.5 and Art. 9(7) in either case, because the meaning differs.

### NEW-arx-15 [minor]
- Location: sections/02b_pol2.tex:29 ("governed AI is expected to"); sections/04_evidence.tex:366 ("§5.6 asks governed AI to provide"); sections/05_synthesis.tex:39 ("§5.6 expects governed AI to ``quantify...''")
- Problem: §5.6 lists things governed AI **can** do. It is not a requirement. Turning "can" into "expects/asks" overstates the obligation and sharpens tension T5 artificially.
- Evidence: PoL/5.…md:184 "具体而言，经过治理的AI可以：" followed by the quoted bullets; PoLEn line 166 "Specifically, governed AI can:".
- Suggested fix: Write "§5.6 lists, among things governed AI can do, 'quantify each person's Love Language and hate-language characteristics...'". T5 remains valid as a tension with an envisaged capability.

### NEW-arx-16 [minor]
- Location: sections/03_method.tex:22 (G4 "§4.3.3.1 cognitive calibration, introspection" → "Are reported probabilities honest"); sections/04_evidence.tex:184-185; sections/02b_pol2.tex:20 ("behavioural introspection")
- Problem:
  1. In §4.3.3.1, "认知校准" means regularly calibrating PAI's *cognitive model* so that it stays consistent with Love 2.0 principles, i.e. value alignment. It does not mean statistical calibration of probabilities. The paper uses the shared word "calibration" to anchor axis G4 (ECE, reliability) in this clause, which is an equivocation.
  2. The official English term is "Behavioral self-reflection", not "behavioural introspection".
- Evidence: PoL/4.…md:98 "认知校准：定期校准认知模型，确保与爱2.0原则一致"; PoLEn line 98–99 "Cognitive calibration: Regularly calibrate the cognitive model to ensure consistency with Love 2.0 principles"; "Behavioral self-reflection: Conduct real-time reflection and adjustment on its own output".
- Suggested fix: In 04_evidence.tex:184 write: "§4.3.3.1 asks PAI to calibrate its cognitive model against the Love 2.0 principles and to reflect on its own output in real time. For a typed model, one testable precondition of this is whether its probabilities reflect how often it is right." Replace "introspection" with "self-reflection" throughout (02b:20, 03:22, 04:184). Better still, anchor G4's "I don't know" component in §4.3.2 (absence), which the paper already does.

### NEW-arx-17 [minor]
- Location: sections/02b_pol2.tex:20; sections/A_concordance.tex:32
- Problem: "Love's alignment asks PAI to keep transparent records" generalises one bullet, "边界透明记录：PAI记录和公开**个人边界声明**" (record and publish *personal boundary declarations*), into a general record-keeping duty. This could be read as PoL2 support for the decision-record design of §6. The decision-record duty actually comes from Art. 5(5).
- Evidence: PoL/4.…md:76; PoLEn line 76 "Transparent boundary records: PAI records and publicizes personal boundary declarations".
- Suggested fix: "Love's alignment asks PAI to record and publish personal boundary declarations and to oversee equal participation in repair after conflict (§4.3.3)". Restore "personal" in the concordance English.

### NEW-arx-18 [minor]
- Location: sections/05_synthesis.tex:11, 14; sections/02b_pol2.tex:33; sections/A_concordance.tex
- Problem: Three PoL2 passages are quoted or paraphrased in the body but missing from Appendix A, which claims to quote "every PoL2 clause cited":
  1. §4.3.3.1, first bullet, quoted in T1: "understand human emotional states and processes" (情感体验的觉察：PAI需要理解人类情绪状态和过程，但不需要模拟人类的情感体验). This is the key half of tension T1.
  2. §4.3.2, the "PAI must keep to the boundaries of human ethics" bullet, cited at 05:14 as naming fabricated intimacy as manipulation (此类表达会制造虚假亲密关系或血缘关系，构成对人类用户的情感操控).
  3. Art. 4(2)–(3), paraphrased at 02b:33 ("keep resource flows auditable and give comprehensible explanations when questioned"). The concordance has Art. 4 = 4(1) only.
- Evidence: PoL/4.…md:97, 54-60; PoL/7.…md:31-32.
- Suggested fix: Add the three rows with Chinese and PoLEn text (PoLEn 4.md line 97 "Awareness of emotional experience: PAI needs to understand human emotional states and processes, but does not need to simulate human emotional experience"). Update \nPolClauses if the counting rule changes (§4.3.2 and §4.3.3.1 are already counted, Art. 4 is already counted, so 28 probably stays).

### NEW-arx-19 [minor]
- Location: sections/02b_pol2.tex:28; sections/04_evidence.tex:101
- Problem: §5.4.1 says the safety valve ensures hate language is blocked at the input and suppressed at the output "**在必要情况下**" (official: "**where necessary**"). The paper drops this proportionality qualifier both in the summary and in the G2 box ("§5.4.1 designs the safety valve to block hate language at the input"). The qualifier supports the paper's own "detector, not judge" argument, so leaving it out both misstates the text and wastes a point in the paper's favour.
- Evidence: PoL/5.…md:134 "确保野蛮的"恨语"在必要情况下，从输入端被阻断、从输出端被抑止"; PoLEn line 108 "ensure that barbaric 'hate language' is, where necessary, blocked at the input end and suppressed at the output end."
- Suggested fix: Insert "where necessary" in both places, and add to the concordance §5.4.1 row.

### NEW-arx-20 [minor]
- Location: sections/06_design.tex:23 (item 7 "serves ... the permanent archive of Art. 11(5)"); sections/06_design.tex:58 (checklist item 12 basis "Art. 4, §5.5")
- Problem:
  1. Art. 11(5) requires that all **amended versions of the protocol** be permanently archived. It says nothing about archiving individual decision records, so citing it as a basis for the decision log stretches the clause.
  2. §5.5 ("any LLM may accept PoL2 governance") does not support "prefer self-hostable weights; pin and publish versions". The nearer basis is §5.5 bullet 2 (accepting governance "意味着接受公共化之约", i.e. accepting the publicisation covenant) together with Art. 4/5(4).
- Evidence: PoL/7.…md:96 "5. 所有修订版本永久存档" under 第十一条【协议修订】; PoL/5.…md:166.
- Suggested fix: For item 7, cite Art. 4(1)–(2) and Art. 5(5) only, or say "in the spirit of Art. 11(5)". For checklist item 12, cite Art. 4, Art. 5(4), and §5.5 bullet 2 (publicisation covenant), quoted in the concordance.

### NEW-arx-21 [minor]
- Location: sections/02b_pol2.tex:33; sections/05_synthesis.tex:32
- Problem: Art. 2(1) makes NaturalDAO autonomous "在与全人类密切协作的前提下" ("on the premise of close collaboration with all humanity"), and Art. 8(2) obliges NaturalDAO to discuss every suggestion "immediately". The paper reports Art. 2 as "decides and executes without human votes" and "fully autonomous" without this premise. That makes T4 look starker than the text, which conditions autonomy on collaboration but leaves it undefined. Since T4 is the paper's strongest critique of the framework, fairness requires stating the premise and then noting that it is not operationalised.
- Evidence: PoL/7.…md:17, 67; PoLEn line 19 "...on the premise of close collaboration with all humanity. Autonomy means that no human voting or additional decision-making mechanism is required."
- Suggested fix: In 02b:33, write "NaturalDAO decides and executes autonomously, 'on the premise of close collaboration with all humanity', without human votes (Art. 2(1))". In T4, add "the text does not specify how this collaboration constrains individual decisions". Add the premise to the Art. 2 concordance row.

### NEW-arx-22 [minor]
- Location: sections/05_synthesis.tex:9-14 (T1); sections/08_conclusion.tex (sentence "emotion recognition under §4.3.3.3 is where typed models were least reliable")
- Problem: The §4.3.3.3 example ("你喜不喜欢小狗狗呀?" vs "你怕不怕小狗狗呀?") is about recognising the *communicative intent* of an utterance through semantics: the second question attempts to create fear in order to gain control. It is not about detecting the emotional state of a person. Reading it as "emotion recognition" that conflicts with §4.3 overstates T1. The genuine counterpart to §4.3 is §4.3.3.1 bullet 1 ("understand human emotional states and processes"). In addition, the conclusion links §4.3.3.3 to the empathy-annotation result (arx24574), but that study measured empathy labelling of text, which fits "semantic/emotion recognition of utterances" only loosely.
- Evidence: PoL/4.…md:130-132 "如何通过语义识别将"仇恨控制的剑锋"转化为"爱的关切"... 这就有很大可能是在亮出控制的剑锋，即他尝试制造恐惧而获得控制地位。"
- Suggested fix: Rest T1 on §4.3 vs §4.3.3.1 (bullet 1), and describe §4.3.3.3 as "recognising the emotional intent of utterances". In the conclusion, write "recognising empathy and emotional content in text is where typed models were least reliable".

### NEW-arx-23 [nit]
- Location: sections/02b_pol2.tex:14, 17, 36; sections/A_concordance.tex:52
- Problem: Several terms depart from the official PoLEn English that the paper says it follows (02b:11):

  | Location | Paper | Official (PoLEn) |
  |---|---|---|
  | 02b:14 | "the *absent* state" | "state of absence" (used correctly elsewhere) |
  | 02b:17 | "public AI (PAI)" | "Public AI" |
  | 02b:36 | "rights of proposal (Art. 8)" | "Human Right of Suggestion" |
  | A:52 | "public questioning" | "universal questioning period" |

  Checked and correct: "Love Language" (capitalised) and "hate language" (lower case), "Promoting love and restraining hate", "Love's Alignment", "Equal Connection", "safety valve", "wisdom navigator", "Hate-language truncation".
- Evidence: PoLEn/4.…md lines 19, 40, 65; PoLEn/7.…md lines 69, 98.
- Suggested fix: Use "state of absence", "Public AI (PAI)", "right of suggestion", "universal questioning period".

### NEW-arx-24 [nit]
- Location: sections/A_concordance.tex:30, 41, 42, 46, 47, 50
- Problem: Minor verbatim and reference issues:
  1. The §4.3.2 heading in the source uses ASCII straight quotes, `不在场的"非爱非恨"状态`, while the concordance uses curly “非爱非恨”. The second quotation, “不在场”, is curly in the source and correct in the paper.
  2. Sub-article numbering is inconsistent. 5(4), 9(7) and 11(2) are given, but the quotes for Art. 2, 4, 7, 8 and 10 come from sub-items 2(1), 4(1), 7(2)–(3), 8(1) and 10 (lead-in + items 1, 4).
  3. The Art. 9(7) English omits the second half (see NEW-arx-14).
- Evidence: PoL/4.…md:65; PoL/7.…md:17, 30, 57-58, 66.
- Suggested fix: Either reproduce the straight quotes or add a note that typographic quotes were normalised. Cite 2(1), 4(1), 7(2)–(3), 8(1), and 10 (items 1, 4).

### NEW-arx-25 [nit]
- Location: sections/02b_pol2.tex:6; sections/C_corrections.tex:41
- Problem:
  1. "That commit [5791ae3] renumbered three chapters" is inaccurate. 5791ae3 is "Create sync-wiki.yml" (2026-09-30T18:30Z). The renumbering and the §4.3.2 additions were made in commits 7750ceb and 526da3d by DDZhou (2026-09-30T10:22–10:25Z), which lie within the 43 commits between 2e094d3 and 5791ae3. The described changes themselves are accurate:
     - EAP 5→4, governance 3→5, axioms 4→3
     - fiction/games/safety-warning examples added to §4.3.2, along with the war/weapons ban and the "case-by-case" sentence
     - old heading "3.3.3"
  2. `PoL/Readme.md` at 5791ae3 still lists the **old** chapter order (3 = governance, 4 = axioms, 5 = EAP), which will confuse readers who follow the link.
  3. The commit date "1 October 2026" holds only in UTC+8.
- Evidence: `gh api repos/naturaldao/NaturalDAO/commits/5791ae3` → "Create sync-wiki.yml", 2026-09-30T18:30:48Z; `gh api "repos/.../commits?sha=5791ae3&path=PoL/4. PoL之伦理对齐协议.md"` → 526da3d, 7750ceb (DDZhou); PoL/Readme.md table of contents.
- Suggested fix: "Between 2e094d3 and 5791ae3 (commits 7750ceb–526da3d, 30 September 2026) the text renumbered three chapters... Clause numbers follow the chapter headings in the files; the directory Readme still lists the earlier order." Apply the same change to C_corrections.tex:41. Give the date as "30 September 2026 (UTC)" or state the time zone.

---

### Verified without findings (for the record)
- Clause existence at 5791ae3: §1.1, 1.2, 1.4, 1.5, 4, 4.3, 4.3.1, 4.3.2, 4.3.3, 4.3.3.1, 4.3.3.2, 4.3.3.3, 5.4, 5.4.1, 5.5, 5.6; Ch. 7 Arts. 2, 4, 5(4), 5(5), 6(3), 7, 8, 9(2), 9(3), 9(7), 10, 11(2), 11(5). All present with the cited content.
- Chinese quotes in Appendix A are verbatim substrings of the source, apart from the quote-mark nit in NEW-arx-24 and Markdown bold markers.
- v0.1 numbering column: 5.3.x / 3.4 / 3.4.1 / 3.5 / 3.6 / "3.3.3" all match 2e094d3.
- Body paraphrases checked and found faithful:
  - §1.1/1.2: "equal mutual benefit" (平等互利); exclusion, hostility, violence
  - §1.5
  - §4.3: fleeting, individual, context-sensitive, dignity
  - §4.3.1
  - §4.3.2: graded management for fiction/games, safety-warning carve-out, state of absence as communication noise
  - §4.3.3.1: hate-language truncation
  - §5.4: no retraining; two-layer architecture
  - Arts. 5, 6, 7, 9, 9(7), 10, 11
- No drift on `main` in any cited clause (5791ae3...main: EAP file renamed only; §1.4 changed 区块链→智能合约 outside the quoted sentence).
- Positionality: the author is listed as a PoL2 contributor in PoL/Readme.md ("鄢申涛Shenton"), and this is disclosed in 09_statements.tex. The §4.3.2 edits the paper relies on were made by the framework's originator, not by the survey author, so there is no circularity.
- AI-use disclosure is present (09_statements.tex), as arXiv's generative-AI policy requires.
