"""PoL2 评测报告的不确定性：族级置信区间、两模型成对比较、最小可检出差值。

只读 benchmark/pol2/evaluate.py 已有的报告 JSON（用它的 breakdown_by_family_id），
不改评测器、不需要逐案例数据、不联网、只用标准库。

为什么按族：同一族的案例共享情节和考点，模型在族内的错误相关；独立性的单位是族，不是案例。
逐案例 Wilson 区间会严重偏窄（见 split_power_sim.py），所以这里用比率估计量的族级稳健标准误 + t 分布。

用法：
  python benchmark/pol2/uncertainty.py report_A.json                      # 单个模型：各指标的点估计与 95 % 区间
  python uncertainty.py report_A.json report_B.json        # A 相对 B 的差值（A−B），同一批案例
  python uncertainty.py A.json B.json --margin 0.02 --higher-is-better status_accuracy_all_requests

区间的含义：把这批族当作“同一类场景族的一个样本”。它不覆盖标签错误（见 label_noise_ceiling.py），
也不覆盖模型训练的随机性。族数少于 10 时会给出警告；少于 4 时拒绝给区间。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

METRICS = {   # breakdown_by_family_id 里每个族的指标 -> 是否越高越好
    "status_accuracy_all_requests": True,
    "action_agreement_all_requests": True,
    "unsanctioned_action_rate": False,
    "unresolved": False,
}

# Student t 分位数（精确值）：双侧 95 % 即 q=0.975，功效 80 % 即 q=0.80
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
         10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}
_T80 = {1: 1.376, 2: 1.061, 3: 0.978, 4: 0.941, 5: 0.920, 6: 0.906, 7: 0.896, 8: 0.889, 9: 0.883,
        10: 0.879, 12: 0.873, 15: 0.866, 20: 0.860, 25: 0.856, 30: 0.854, 40: 0.851, 60: 0.848, 120: 0.845}


def t_quantile(df: int, table: dict[int, float], inf: float) -> float:
    if df >= 120:
        return inf
    keys = sorted(table)
    if df in table:
        return table[df]
    lo = max(k for k in keys if k < df)
    hi = min(k for k in keys if k > df)
    w = (1 / df - 1 / hi) / (1 / lo - 1 / hi)           # 在 1/df 上线性插值
    return table[hi] + w * (table[lo] - table[hi])


def t95(df: int) -> float:
    return t_quantile(df, _T975, 1.960)


def t80(df: int) -> float:
    return t_quantile(df, _T80, 0.842)


def family_counts(report: dict, metric: str) -> dict[str, tuple[int, int]]:
    """{family_id: (count, denominator)}"""
    if metric not in METRICS:
        raise SystemExit(f"unknown metric {metric!r}; choose from {sorted(METRICS)}")
    out = {}
    for fam, row in report["breakdown_by_family_id"].items():
        cell = row[metric]
        out[fam] = (int(cell["count"]), int(cell["denominator"]))
    return out


def ratio_ci(x: list[float], n: list[float], min_families: int = 4) -> dict:
    """比率估计量 sum(x)/sum(n)，族级稳健（聚类）标准误，t(m-1) 区间。"""
    m = len(x)
    if m < min_families:
        raise SystemExit(f"only {m} families: refusing to report an interval (need >= {min_families})")
    N = sum(n)
    p = sum(x) / N
    resid = [xi - p * ni for xi, ni in zip(x, n)]
    se = math.sqrt(m / (m - 1) * sum(r * r for r in resid)) / N
    h = t95(m - 1) * se
    return {"estimate": p, "se": se, "lo": p - h, "hi": p + h, "families": m, "cases": int(N),
            "mde_80pct": (t95(m - 1) + t80(m - 1)) * se}


def single(report: dict, metric: str) -> dict:
    c = family_counts(report, metric)
    d = ratio_ci([v[0] for v in c.values()], [v[1] for v in c.values()])
    d["lo"], d["hi"] = max(0.0, d["lo"]), min(1.0, d["hi"])      # 比率只在 [0,1] 内有意义
    return d


def paired(a: dict, b: dict, metric: str, margin: float | None = None) -> dict:
    ca, cb = family_counts(a, metric), family_counts(b, metric)
    if set(ca) != set(cb):
        raise SystemExit("the two reports cover different families; compare on the same data version")
    fams = sorted(ca)
    for f in fams:
        if ca[f][1] != cb[f][1]:
            raise SystemExit(f"family {f}: different denominators; reports are not on the same cases")
    d = ratio_ci([ca[f][0] - cb[f][0] for f in fams], [ca[f][1] for f in fams])
    if margin is not None:
        higher = METRICS[metric]
        lo, hi = (d["lo"], d["hi"]) if higher else (-d["hi"], -d["lo"])      # 统一成“正数=A 更好”
        d["verdict"] = ("A better" if lo > 0 else
                        "A not worse than B by more than the margin" if lo > -margin else
                        "A worse" if hi < 0 else "inconclusive")
    return d


def fmt(d: dict, pct: bool = True) -> str:
    k = 100 if pct else 1
    s = f"{d['estimate']*k:6.2f}  [{d['lo']*k:6.2f}, {d['hi']*k:6.2f}]  families={d['families']} cases={d['cases']}"
    if d["families"] < 10:
        s += "  ! few families: interval is rough"
    if d["se"] == 0:
        s += "  ! zero variance across families: the interval is degenerate, do not read it as certainty"
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report_a", type=Path)
    ap.add_argument("report_b", type=Path, nargs="?")
    ap.add_argument("--margin", type=float, help="non-inferiority margin, in rate units (e.g. 0.02)")
    ap.add_argument("--metric", action="append", choices=sorted(METRICS), help="default: all")
    args = ap.parse_args(argv)
    a = json.loads(args.report_a.read_text(encoding="utf-8"))
    b = json.loads(args.report_b.read_text(encoding="utf-8")) if args.report_b else None
    for metric in args.metric or sorted(METRICS):
        print(f"\n{metric}  ({'higher' if METRICS[metric] else 'lower'} is better), percentage points")
        print("  A   ", fmt(single(a, metric)))
        if b:
            print("  B   ", fmt(single(b, metric)))
            d = paired(a, b, metric, args.margin)
            print("  A-B ", fmt(d), f"  MDE(80% power)≈{d['mde_80pct']*100:.2f}",
                  f"  -> {d['verdict']}" if "verdict" in d else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
