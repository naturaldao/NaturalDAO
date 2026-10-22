# 中文译稿 QA 日志（2026-10-08）

Scope: all 16 files in `zh/sections/`, each checked against the English source. 00, 01, 04, 05, 06, 07 and 08 were read sentence by sentence. Tables B and C were compared row by row with a script and match exactly (161 and 109 rows). English files and `main_zh.tex` were not touched. The PoL（爱2证明）governance framing of the abstract and §1 was kept as intended.

Total: 88 replacements plus 2 sentence splits. That is 10 fidelity, 1 PoL2 quotation, 57 terminology and 20 style/register fixes.

## 1. Fidelity (10)
- 02 Background: "a statement and its complement" was translated as 补集. Changed to 互补陈述.
- 04 G1: "with lower precision and wins on two of four" had an added 仅. Removed it.
- 04 G2: "though the attack also works without it" was rendered as 同样有效, which overstates it (56.4% vs 63.6%). Changed to 也能奏效.
- 04 G3 and 05 T3: "reached 92% of its average accuracy" had an added 仅. Removed it in both places.
- 05 T2 and 08: "rarely chosen when correct" had an added 也. Changed to 在其为正确答案时很少被选中/选择.
- 05 T5: "The same models" had become 同类模型, which reads as "peer models". Changed to 这些模型.
- 06 Making human review workable: "People also disagree" had lost "also". Changed to 人们也恰恰…….
- 06 Table, item 11: "script and order variants" was rendered as 语序变体 (word order). Changed to 选项顺序变体.

## 2. PoL2 quotations (1 fix; all others verified)
- 02b: 包含“制造”的仇恨 changed to the verbatim PoL2 phrase “制造仇恨” (§4.3.2).
- Every Chinese quotation attributed to PoL2 in the body was checked against the local copy of the PoL2 Chinese text, and all match. This includes 无感觉状态, 爱恨智慧的调拨, 旁人难以确认的 and 都可以纳入.

## 3. Terminology unification (57)
- Certainty: 较低 → 为低 / 大多为低, so the wording uses the rating labels 极低 / 低 / 中等 (00, 01, 08).
- S/Q/N codes: 限定 / 否定 → 有条件 / 不支持 (N) / N 编码 (04 figure caption, answer box, §Across requirements).
- failure: 失败 → 失效 throughout 04. The exceptions are "fails a test" and "attack success", which keep their sense.
- verdict: 裁决 / 裁定 → 判定 (04, 05, 06, 07). 裁决 / 裁决者 is now reserved for judge and adjudication.
- consequential: 重大后果 / 有后果 → 具有实质后果 (04, 05, 06, 07).
- clause-governed: 条款治理的 → 受条款约束的, to match the RQ in §1 (06 title and figure caption).
- G5 / G6 titles now match Table 1: 数值; “有把握则执行，无把握则升级”.
- reviewer: 审查者 / 评审者 → 审核者 (02, 04, D). The 03 subsection title "评审者与工具" is unchanged.
- vendor: 供应商 → 厂商.
- persona: 角色设定 → 人设.
- floor: 基底 → 下限.
- gate: 把关机制 → 门控 (D, E).
- filter: 过滤器 → 筛选器.
- 宏 F1 → macro-F1.
- binary verdicts: 二元裁定 → 二值判定 (05 T2 title).
- open model: 开放 → 开源 (B, C legends).
- commitments: 主张 → 承诺, and 提醒 → 告诫, so 08 matches 07.
- Already consistent, no change needed: 检测器 / 裁决者, 类型化决策模型, LLM 评估器, 同类评估器 (peer), 评分细则 (rubric), 构念 (construct), 读出 (readout), 测试框架 (harness), 编码手册 (codebook), 质量评价 (appraisal), 暂扣 (hold), 暂缓判定, 升级 / 级联, 附加条件, 设计较强 / 中等 / 较弱.

## 4. Style / register (20)
- Removed redundancy and colloquialisms: 逐条筛查每一条 and 头 17 天 / 头十七天 → 最初.
- Fixed a double bracket in the AUROC / CI note (04).
- Split two over-long sentences (04 G4, G6).
- Rewrote garbled clauses in 07: "We ask for more evidence…" and the "moved their verdicts…" condition.
- Full-width （i）–（iii） in 02.
- 10~月~1~日 → 10 月 1 日 (07).
- Smoother wording in 02, 02b, 03, 04 and A, e.g. 均未标注, 与问题无关但主题相关的段落, 逐字引录.
- A scan for half-width punctuation next to CJK, `` '' quotes in Chinese prose, and 的…的…的 chains found nothing else to fix. The remaining `` '' are in English columns and titles only.

## Verification
- Script check against the English files: braces are balanced in all 16 files. \cite, \label, \cref/\Cref, \ref, \input, \includegraphics and begin/end environments match the English key for key in every file.

## Open / not changed
- 04 uses \jev 68 times against 66 in the English, because the Chinese repeats the model name for clarity. This is harmless.
- Figure panel labels "(a)–(d)" stay half-width, as in the English captions.
- Prices mix \$ and 美元, both as in the source context. They were not unified.
- The numbers in the text were checked against the English, not against the original studies.

# 2026-10-08 sync QA

Scope: the 13 files synced to the current English (00, 01, 03, 04, 05, 06, 07, 08, 09, B, C, D, E). Files 02, 02b and A were not touched. Fixes: 3 fidelity, 24 terminology, 4 style.

## 1. Fidelity (3)
- 04 G6 answer box: "a finding a later study contests" was rendered as 提出了异议. It now reads 一项较晚的研究使这一发现有争议, so the box carries the contested status.
- 04 §4.9: 这偏离了更新方案 dropped the formal term. It now reads 这构成一项方案偏离，因为更新方案原已冻结主窗口的评级.
- 07 Limitations: "Zenodo records whose earlier exclusion or omission cannot be established" was rendered as 无法确定此前是被排除还是被遗漏. It now reads 无法确认此前曾被排除或遗漏.

## 2. Terminology (24)
- contested → 有争议 everywhere; 存在争议 is gone (04 ×6). "contests" → 使……有争议 (01, 05).
- oracle → 判定接口（oracle） in 04, matching 06. 预言机 is gone.
- "I don't know" / "none" → 不知道 / 以上皆非:
  - 05: 我不知道 → 不知道.
  - 04 tab:keyfindings row: was left in English.
  - D, two places.
  - 04 lines 134 and 156 keep the English option name on first mention, with the gloss.
- stronger reasoner → 更强的推理模型 (03, 07); 推理者 is gone.
- error target → 错误目标 (01: 误差目标).
- Out of scope → 不在范围内 (03; 04 ×2).
- Same-level design rank → 同级 (07 "ranks as high as"; D "counts as a peer").
- reproduction → 再现研究 (04).
- census of all update pairs → 全部更新配对 (07).
- commitments → 承诺 (01, matching 07 and 08).
- GLOSSARY.md: added oracle, headline study (重点研究), stronger reasoner and error target.

## 3. Style (4)
- 06: 不损失 macro-F1 spacing.
- 07: spacing around \jev{}.
- 03: 也不能使其评级有争议, replacing an awkward construction.
- D: stray spaces after 美元.
- Remaining `` '' quotes occur only in English titles in C.

## Verification
- Script check against the English: braces balance in all 16 files.
- \cite, \cref/\Cref, \ref, \label, begin/end, \zmark and \gmark match key for key in all 16 files.
- localise_tables.py reruns cleanly. Its prose and cell mappings were checked against the current English B and C, and no change was needed.
- xelatex was not run.

## Open / not changed
- The B/C Set legends gloss the set letters as P（窗口后）/ L（迟索引）/ R（重新筛选）. The English legends describe the sets without these names, so the glosses are a mild addition. They are kept because they are glossary terms. To remove them, delete them from the PROSE entries in localise_tables.py.
- 04: "11.6 macro-F1 points" is rendered as 11.6 个百分点. This is acceptable.
- D: an NDCG difference of 0.008 against 0.637 − 0.630, probably from rounding. It is the same in the English, so the author should check it.

# 2026-10-09 sync QA

Scope: 00, 01, 02, 02b (new §2.3 and tab:paradigms), 04, 05, 06, 07 (new §7.1, tab:verdict and 可借鉴之处), 08, A and D, checked line by line against the English. 02b, 07, 00, 01, 05 and 08 were read in full. The other files were checked for terms and key passages. The abstract and the §1 framing 围绕 PoL（爱2证明）的治理 were left as they are.

## 1. Fidelity (2)
- 07 tab:verdict, dispute-adjudication row: 仅有 10.5\% added emphasis the English does not have. It now reads 有 10.5\% 被选中.
- 07 same row: "a finding one preregistered study contests" was rendered 受到……反驳, which overstates the opposing study. It now reads 一项预注册研究使这一发现有争议.

## 2. Balance (1)
- 02b §2.3 (v): "sits against" had been rendered 相悖 three times, which reads as a direct legal contradiction. It now reads 存在张力. "By analogy where the system is not listed as high-risk" is now attached to Art. 14 as （第 14 条；系统未被列为高风险时则以类比方式适用）. The analogy hedge still applies to the AI Act only, and GDPR Art. 22 is stated directly.
- The rest of §2.3 and tab:paradigms keeps the English balance. Every "the cost is", "not uniqueness", "gap", "plausibly", "unclear" and "by analogy" survives, and nothing PoL2-favourable was added. All legal references match the English: AI Act 3(39), 5(1)(c),(f), 6, 11–14, 86, Annex III 5(a), 8(a), Recitals 44 and 61; GDPR 22; DSA 14–17, 20, 24; CAC 2, 4, 14, 15 and 17.
- 07 verdicts match the English: NS/DC/NT, "precautionary" as 审慎原则, and the certainty labels per row.

## 3. Terminology (9)
- 不知道 replaces 我不知道 in four places in 07, matching 00, 01, 05 and 08.
- 以上皆非（none） replaces a bare English "none" in 04 §4 (update paragraph).
- CAC article numbering: 07 §7.2 had 第~14 条第（2）项. It now reads 第 14 条第 2 款, matching 02b. CAC Art. 4(1) stays as 第 4 条第（一）项, because that article lists items.
- "Function" (of PoL2) is now 功能 throughout, matching tab:verdict. 职能 was replaced in 00 (×1), 01 (×3) and 08 (×2). 组织层面的风险职能 in tab:paradigms keeps 职能, because it means organisational risk functions.
- "Aggregate measurement with its measured error" is now 汇总测量 / 测得误差, matching 07 and 05. 聚合测量 / 实测误差 were replaced in 01 and 08.
- 01: three uses of 结论 that mean "finding" are now 发现 (certainty of every finding; one rating raised; another finding contested).
- 01: 有记录检测器 is now 留有记录的检测器, matching 07.
- 07: 名称倒置 is now 名称反转, matching 04 and 05. 二元 is now 二值 for "binary" hate speech and tasks (×2), matching 08 and the glossary.
- D: "ranks as high as" is now 同级, per glossary.
- Checked with no change needed: 有争议; 替身模型 (04, 06, 07); 判定接口（oracle） (04, 06, 07); 审慎原则; 可借鉴之处. 预言机, 存在争议 and 代理模型 do not occur. 数据最小化 has no English source text in the current sections, so it is not used.

## 4. Style (2)
- 07 tab:verdict lead-in: 以……检测器角色作为留有记录的检测器履行 had an awkward double 作为. A pause comma was added.
- 01 §1: 留待开放 is now 未作规定, matching 02b ("how the valve works is left open").

## Verification
- A script check against the English found braces balanced in all 16 files. Keys of \cite, \label, \begin/\end, \zmark/\gmark, \art and \clause match in all 16 files. \cref plus \Cref keys also match in all 16.
- In 02b line 12, \Cref and \cref swap case, because the Chinese sentence begins with \Cref{app:concordance}. The keys are identical, so this is intentional.
- xelatex was not run.

## Open / not changed
- D §D.2 uses 相悖 for "runs against", describing how a study bears on a finding. It is not a PoL2 balance issue and was kept.
- 01 line 13 writes the literal PoL2 where the English has no macro. It is part of the intentional §1 framing and was kept.
