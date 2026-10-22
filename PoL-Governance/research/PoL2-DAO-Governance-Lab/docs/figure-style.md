# 制图规范

本仓库所有图表都遵循同一套出版级规范。规范参照 [ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers)（其作者在 *Nature Machine Intelligence*、ICML、NeurIPS、ECCV 等发表论文时所用的作图脚本）中的 `scientific-figure-making` 规范。该仓库采用 CC BY-NC 4.0 许可，因此本仓库**只重述规则、不复制其代码或文字**，实现全部位于 [`src/pol2dao/plotstyle.py`](../src/pol2dao/plotstyle.py)。

给 Claude Code 等编程助手看的精简版写在仓库根目录的 [`CLAUDE.md`](../CLAUDE.md)。

---

## 1. 为什么需要统一规范

- **一致**：同一个实验条件在所有图里颜色和线型都一样，读者不必每张图重新看图例。
- **可印刷**：用矢量 PDF 保证缩放清晰；用线型和阴影冗余编码，保证灰度打印和色弱读者也能区分。
- **诚实**：画出置信区间，并标明指标的好坏方向，读者不会把噪声当成效应。
- **可维护**：只有一个入口和一个调色板，想改风格只需改一处。

## 2. 规则与实现

| # | 规则 | 理由 | 在 `plotstyle.py` 中 |
|---|---|---|---|
| 1 | 所有图用 `new_figure()` 创建，用 `finalize_figure()` 保存 | 单一入口，风格不会走样 | `new_figure`, `finalize_figure` |
| 2 | 同时导出 PNG（300 dpi）和 PDF（矢量，TrueType 字体嵌入） | 网页用 PNG，论文和排版用 PDF；PDF 中的文字可在 Illustrator 里编辑 | `finalize_figure(formats=("png","pdf"), dpi=300)`；`pdf.fonttype=42` |
| 3 | 无衬线字体：Helvetica → Arial → Liberation Sans → DejaVu Sans，另加 CJK 回退 | 期刊的常用字体；没有安装时自动回退，中文不会显示成方块 | `FigureStyle.font_family`, `CJK_FONTS` |
| 4 | 字号层级：紧凑图 16 pt、轴线 2；大柱状图 24 pt、轴线 3 | 缩到单栏宽度后依然清晰可读 | `COMPACT`, `LARGE` |
| 5 | 去掉上、右边框；不画网格；图例无边框 | 减少非数据的墨水，突出数据 | `apply_publication_style` |
| 6 | 颜色语义：蓝 = 本研究方法，绿 = 正向变体，红 = 基线或损失，灰 = 参照，金 = 唯一高亮 | 读者靠颜色就能知道「谁是被研究的对象」 | `PALETTE`, `DEFAULT_COLORS` |
| 7 | 条件编码固定：色相 = 机制族，虚线和斜线阴影 = 20/80 权力 | 冗余编码，灰度下也能区分 | `COND_STYLE`, `cond_handles` |
| 8 | 柱状图：黑色描边、带端帽的误差棒、数值标在柱子上 | 边界清晰，不需要网格就能读出精确值 | `bar`, `annotate_bars`, `is_dark` |
| 9 | 折线图：线宽 3、标记点 8，每轴 2–4 条线，95 % 置信区间带 | 线条粗到能印刷；不确定性直接可见 | `plot_line(err=...)`, `ci95` |
| 10 | 热图：`Blues` 表示大小，`RdBu` 以 0 为中心表示差值；白色分隔线、格内数值、带标签的色条 | 单一色相便于排序；发散色图让正负一目了然 | `heatmap`, `SEQ_CMAP`, `DIV_CMAP` |
| 11 | 参考线：黑色、透明度 0.3、线宽 3 的虚线 | 看得见，但不与数据抢眼 | `REF_LINE` |
| 12 | 指标标签末尾标 ↑ 或 ↓ | 不必翻正文就知道哪个方向更好 | `UP`, `DOWN` |
| 13 | 图内不放脚注；来源、样本量、注意事项写进图注 | 图保持干净，说明可以写完整 | 约定，见 `docs/results.md` |
| 14 | 图例太多时单独放一个关闭坐标轴的面板 | 不遮挡数据 | `legend_panel` |
| 15 | 概率类指标的 y 轴固定为 0–1，其他指标按数据收紧范围 | 概率不夸大差异；其他指标让差异看得见 | 各实验模块 |

## 3. 调色板

| 名称 | 色值 | 用途 |
|---|---|---|
| `blue_main` | `#0F4D92` | pol2（本研究提出的机制） |
| `blue_secondary` | `#3775BA` | pol2 的消融：不筛查 |
| `green_3` | `#8BCF8B` | 正向变体：pol2-free-talk、收益、阈值最优点 |
| `green_1` / `green_2` | `#DDF3DE` / `#AADCA9` | 浅绿层级 |
| `red_strong` | `#B64342` | Sharma et al. 二次方投票基线，以及「违规」 |
| `red_1` / `red_2` | `#F6CFCB` / `#E9A6A1` | 损失 / 浅红层级 |
| `neutral_dark` | `#767676` | Sharma et al. 排序投票基线、参照项 |
| `neutral` | `#CFCECE` | 背景类别 |
| `highlight` | `#FFD700` | 唯一的高亮（每张图最多一处） |
| `teal` / `violet` | `#42949E` / `#9A4D8E` | 备用强调色 |

各条件的编码（`COND_STYLE`）：

| 条件 | 颜色 | 线型 | 阴影 | 标记 |
|---|---|---|---|---|
| quadratic-equal | 红 | 实线 | 无 | ● |
| quadratic-20/80 | 红 | 虚线 | `//` | ■ |
| ranked-equal | 灰 | 实线 | 无 | ● |
| ranked-20/80 | 灰 | 虚线 | `//` | ■ |
| **pol2** | **深蓝** | 实线 | 无 | ● |
| pol2-no-screening | 浅蓝 | 实线 | `..` | ▲ |
| pol2-free-talk | 绿 | 实线 | 无 | ◆ |

## 4. 写一张新图

```python
from pol2dao.plotstyle import UP, finalize_figure, new_figure, plot_line

fig, axes = new_figure(1, 2, panel=(5.6, 5.0))           # 每个面板 5.6 × 5.0 英寸
ax = axes[0][0]
plot_line(ax, xs, ys, "pol2", err=ci)                    # 条件名 -> 固定的颜色、线型和标记
plot_line(ax, xs, ys_base, "quadratic-equal", err=ci_b)
ax.set_ylabel("P(minority's option wins)" + UP)
ax.set_ylim(0, 1)
ax.legend(loc="upper left")
finalize_figure(fig, "results/figures/my_figure")         # 生成 my_figure.png 和 my_figure.pdf
```

然后**打开 PNG 看一遍**：有没有文字重叠、被截断、图例遮挡数据。

## 5. 自动检查

`tests/test_figure_style.py` 会检查：

- 除 `plotstyle.py` 外，源码中没有直接调用 `savefig`；
- 作图模块中没有写死的十六进制色值（必须取自 `PALETTE`）；
- `apply_publication_style()` 设置了规定的 rcParams；
- 每个实验都同时输出 `.png` 和 `.pdf`。
