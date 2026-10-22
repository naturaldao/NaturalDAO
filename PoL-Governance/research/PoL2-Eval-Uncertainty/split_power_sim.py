"""PoL2 正式数据按“族”切分后，保留集/公开测试能把一个错误率测多准？小模拟。

背景（均来自仓库 main 的实际文件）：
  - datasets/pol2/families.jsonl：96 个族，每族 target_cases=112，共 10752 条
  - datasets/pol2/splits.py：按族 70/20/5/5 分配 -> train 67 族、public_test 19 族(2128 条)、
    validation 5 族(560 条)、private_holdout 5 族(560 条)（用 8 个不同盐值复核过，结果恒定）
  - benchmark/pol2/evaluate.py：只报点估计，没有置信区间

同一族内的案例共享情节与考点，模型在同一族上的错误是相关的。于是有效样本量接近“族数”，
而不是“案例数”。本脚本回答三件事：
  1. 同样 560 条，5 个大族 vs 更多更小的族，区间宽度差多少？
  2. 常见的三种区间（逐案例 Wilson、族级 t、族级自助法）在 5 个族时覆盖率如何？
  3. 比较两个模型时，最小可检出差值（MDE）是多少？

模型：族 f 的真实错误率 p_f = expit(a + sigma*u_f)，u_f~N(0,1)；族内案例独立 Bernoulli(p_f)。
a 取使总体平均错误率约 15 %。sigma 与实际模型无关，是敏感性参数，真实值需要用真实结果估计。
这是模型模拟，不是对真实模型的证据。

依赖：numpy。运行：python split_power_sim.py   （约 10 秒；固定种子）
"""
from __future__ import annotations

import math
import pathlib
import sys
from statistics import NormalDist

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "benchmark" / "pol2"))
SEED = 20261005
MEAN_ERR = 0.15
SIGMAS = (0.3, 0.7, 1.0)
DESIGNS = [  # (族数 m, 每族案例数 n, 说明)
    (5, 112, "现状：保留集/校验集 5 族 x 112"),
    (19, 112, "现状：公开测试 19 族 x 112"),
    (20, 28, "同样 560 条，20 个小族"),
    (40, 14, "同样 560 条，40 个小族"),
    (80, 7, "同样 560 条，80 个小族"),
]
R, B = 2000, 300
rng = np.random.default_rng(SEED)
ND = NormalDist()


def expit(x):
    return 1 / (1 + np.exp(-x))


U = np.random.default_rng(1).standard_normal(400_000)


def calibrate(sigma):
    lo, hi = -6.0, 6.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if expit(mid + sigma * U).mean() < MEAN_ERR:
            lo = mid
        else:
            hi = mid
    a = (lo + hi) / 2
    p = expit(a + sigma * U)
    icc = p.var() / (p.mean() * (1 - p.mean()))      # 族内相关（方差分量比）
    return a, p.mean(), p.var(), icc


def tcrit(df, q=0.975):
    # 与 uncertainty.py 相同的精确 t 分位数表（q=0.975 或 0.80），df 之间在 1/df 上插值
    import uncertainty
    return uncertainty.t95(df) if q == 0.975 else uncertainty.t80(df)


def wilson(x, n, z=1.959964):
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def run(sigma, m, n):
    a, pbar, pvar, icc = calibrate(sigma)
    pf = expit(a + sigma * rng.standard_normal((R, m)))
    x = rng.binomial(n, pf)
    prop = x / n
    est = prop.mean(axis=1)
    out = {"icc": icc}
    lo, hi = wilson(x.sum(axis=1), m * n)
    out["wilson"] = (np.mean((lo <= pbar) & (pbar <= hi)), np.mean(hi - lo) / 2)
    se = prop.std(axis=1, ddof=1) / math.sqrt(m)
    h = tcrit(m - 1) * se
    out["cluster_t"] = (np.mean((est - h <= pbar) & (pbar <= est + h)), h.mean())
    cover, width = [], []
    for s in range(0, R, 250):
        pr = prop[s:s + 250]
        idx = rng.integers(0, m, size=(pr.shape[0], B, m), dtype=np.int32)
        bs = np.take_along_axis(pr[:, None, :].repeat(B, 1), idx, axis=2).mean(axis=2)
        l, u = np.quantile(bs, [0.025, 0.975], axis=1)
        e = est[s:s + 250]
        cover.append(((l <= pbar) & (pbar <= u)))
        width.append((u - l) / 2)
    out["cluster_boot"] = (np.concatenate(cover).mean(), np.concatenate(width).mean())
    # 比较两个模型：族级差值的 t 检验，两模型的族级错误率相关系数 rho_f = 0.7（假设）
    sd_obs = math.sqrt(pvar + (pbar * (1 - pbar) - pvar) / n)       # 观察到的族比例的标准差
    sd_diff = sd_obs * math.sqrt(2 * (1 - 0.7))
    out["mde"] = (tcrit(m - 1) + tcrit(m - 1, 0.8)) * sd_diff / math.sqrt(m)
    return out


def main():
    print(f"总体平均错误率 {MEAN_ERR:.0%}；每格：覆盖率 / 区间半宽（百分点）\n")
    for sigma in SIGMAS:
        a, pbar, pvar, icc = calibrate(sigma)
        print(f"== sigma={sigma}  族间错误率标准差 {math.sqrt(pvar)*100:.1f} 个百分点  ICC≈{icc:.3f}")
        print(f"{'设计':<34}{'逐案例Wilson':>16}{'族级t':>14}{'族级自助法':>16}{'比较两模型MDE':>16}")
        for m, n, note in DESIGNS:
            o = run(sigma, m, n)
            f = lambda k: f"{o[k][0]*100:5.1f}% / {o[k][1]*100:4.1f}"
            print(f"{note:<30}{f('wilson'):>18}{f('cluster_t'):>16}{f('cluster_boot'):>18}{o['mde']*100:>12.1f} pp")
        print()


if __name__ == "__main__":
    main()
