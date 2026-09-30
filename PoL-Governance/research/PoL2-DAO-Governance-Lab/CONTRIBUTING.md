# 参与贡献 · Contributing

欢迎提 issue 和 PR。几条约定：

1. **每条机制都要对应 PoL2 的具体条款。** 新增或修改机制时，同步更新 [docs/concept-mapping.md](docs/concept-mapping.md)，写明条款编号和对应测试。
2. **核心代码只用标准库。** 画图等可选功能放在 `[project.optional-dependencies]`。
3. **不要把模拟结果写成关于真实人群的结论。** 新增的模拟假设要写进 [docs/experiment-design.md](docs/experiment-design.md)。
4. **修改词表（`eap.py` 的标记）请附例句**，并在 `tests/test_eap.py` 里加上应该通过和应该标记的句子——尤其是「批评、愤怒不是恨」的反例。
5. **作图遵循 [docs/figure-style.md](docs/figure-style.md)**：只用 `pol2dao.plotstyle` 里的调色板和辅助函数，只通过 `finalize_figure()` 保存（PNG + PDF），图内不放脚注，画完打开 PNG 检查。`tests/test_figure_style.py` 会自动检查其中几条。
6. 提交前运行：

   ```bash
   pytest
   pol2dao simulate --reps 1000   # 若改动影响模拟，请一并更新 results/
   ```

Contributions welcome. Tie every mechanism to a PoL2 clause, keep the core
stdlib-only, follow docs/figure-style.md for every figure, never present simulation output as evidence about people, and add
pass/flag example sentences for any lexicon change.
