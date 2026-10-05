"""两个教师“一致”时，参考标签有多大概率仍是错的？（label_noise_ceiling）

背景：datasets/pol2/pipeline/adjudicate.py 把“至少 2 个不同谱系的来源一致”记为 agreed，
review_level 写 model_cross_checked（不称金标准，这一点做得对）。但一致不等于独立：
各来源对同一案例的错误若相关，一致时的错标率会远高于独立情形。

模型：每个来源对每个案例错的边际概率 e；两来源的错误指示变量的相关系数 rho；
两者都错时给出同一个错误标签的概率 c（三态标签里至少约 0.5）。
P(两者一致且标签错) = c * P(都错)，P(一致) = P(都对) + c * P(都错)。
P(都错) = e^2 + rho e (1-e)；P(都对) = (1-e)^2 + rho e (1-e)。
这是闭式计算，不是对真实教师模型的证据。rho 与 e 需要用人工审计样本来估计。
"""
for c in (0.5, 1.0):
    print(f"\n两者都错时给出同一错误标签的概率 c={c}")
    print(f"{'单来源错误率e':>14}" + "".join(f"   rho={r:<4}" for r in (0.0, 0.3, 0.5, 0.7)))
    for e in (0.05, 0.10, 0.15):
        cells = []
        for rho in (0.0, 0.3, 0.5, 0.7):
            both_wrong = e * e + rho * e * (1 - e)
            both_right = (1 - e) ** 2 + rho * e * (1 - e)
            cells.append(c * both_wrong / (both_right + c * both_wrong))
        print(f"{e:>14.2f}" + "".join(f"   {x*100:5.1f}% " for x in cells))
