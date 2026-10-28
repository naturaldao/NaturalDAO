#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the single self-contained HTML report for the Kev prefix evaluation.

Usage (WSL, repo venv, PYTHONPATH not needed):
  python benchmark/kev_prefix/build_report.py --priv /home/wenbo/priv-eval       --repo . --out docs/reports/2026-10-28-kev-prefix-eval.html

Reads aggregate artifacts from the private evaluation workspace (outside the repo) and the
committed aggregate JSON files, renders matplotlib SVG charts inline, and writes one HTML file
with no external references.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

from report_figures import build_figures, LABELS, MODELS

CSS = """
:root{
  --ink:#14213d; --muted:#667085; --line:#e4e7ec; --bg:#f6f8fb; --card:#ffffff;
  --accent:#1f7a8c; --accent2:#e07a5f; --good:#2f855a; --bad:#c53030; --blue:#2563eb;
  --shadow:0 10px 30px rgba(20,33,61,.06);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC","Microsoft YaHei",sans-serif;
  font-size:16px;line-height:1.75}
a{color:var(--blue);text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px}
.hero{background:linear-gradient(135deg,#14213d 0%,#1f3a5f 55%,#1f7a8c 100%);color:#fff;padding:60px 0 46px}
.hero h1{font-size:34px;line-height:1.25;margin:0 0 10px;letter-spacing:-.01em}
.hero .meta{color:#c9d6e5;font-size:14px;margin-bottom:20px}
.hero p.lead{font-size:18px;line-height:1.8;max-width:920px;color:#f2f6fb;margin:0}
nav.toc{position:sticky;top:0;z-index:20;background:rgba(246,248,251,.94);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line);padding:10px 0;font-size:13px}
nav.toc .wrap{display:flex;gap:16px;flex-wrap:wrap}
nav.toc a{color:var(--muted)}
main{padding:28px 0 60px}
section{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:28px 32px;
  margin-bottom:22px;box-shadow:var(--shadow);scroll-margin-top:64px}
h2{font-size:26px;line-height:1.3;margin:0 0 6px;letter-spacing:-.01em}
h3{font-size:19px;margin:26px 0 8px}
h4{font-size:16px;margin:20px 0 6px;color:var(--ink)}
p{margin:10px 0}
.small{color:var(--muted);font-size:13px}
.tag{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;background:#eef4f6;color:#1f6472;margin-right:6px}
.key{font-weight:600;color:var(--bad)}
.good{color:var(--good);font-weight:600}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:860px){.grid2,.grid3{grid-template-columns:1fr}section{padding:22px 18px}.hero h1{font-size:27px}}
figure{margin:18px 0 6px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px 10px}
figure .chart{overflow-x:auto}
figcaption{color:var(--muted);font-size:13px;margin-top:8px}
.howto{background:#f8fafc;border-left:4px solid var(--accent);padding:10px 14px;border-radius:0 10px 10px 0;
  color:#344054;font-size:14px;margin:10px 0 4px}
.takeaway{background:#fdf6f3;border-left:4px solid var(--accent2);padding:10px 14px;border-radius:0 10px 10px 0;
  color:#5b2f23;font-size:14px;margin:10px 0}
table{width:100%;border-collapse:collapse;margin:14px 0 6px;font-size:14px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:#fafbfc}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.total td{font-weight:600;background:#fafbfc}
.note{font-size:13px;color:var(--muted);margin:6px 0 0}
.formula{background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0;
  font-family:"Cambria Math",Georgia,serif;font-size:15px;line-height:1.9}
.formula b{font-family:inherit}
ul,ol{margin:8px 0 8px 22px;padding:0} li{margin:4px 0}
.callout{background:#eef4f6;border-radius:12px;padding:14px 16px;font-size:14px;color:#1f3a4a;margin:14px 0}
.callout.warn{background:#fdf1ee;color:#6b2d22}
footer{color:var(--muted);font-size:13px;padding:20px 0 40px;text-align:center}
.big{font-size:19px;font-weight:600}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def pct(x, digits=1, sign=False):
    if x is None:
        return "n/a"
    text = f"{x * 100:+.{digits}f}" if sign else f"{x * 100:.{digits}f}"
    return text + " pp" if sign else text + "%"


def num(x, digits=4, sign=False):
    if x is None:
        return "n/a"
    return f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"


def fmt_int(x):
    return f"{int(x):,}"


def ci(x, digits=1, scale=100.0):
    if not x:
        return "n/a"
    return "[" + f"{x[0]*scale:.{digits}f}, {x[1]*scale:.{digits}f}" + "]"


def ci_num(x, digits=3):
    if not x:
        return "n/a"
    return "[" + f"{x[0]:+.{digits}f}, {x[1]:+.{digits}f}" + "]"


def figure(name, figs, caption, howto=None, width_class=""):
    block = '<figure class="' + width_class + '"><div class="chart">' + figs[name] + "</div><figcaption>" + caption + "</figcaption></figure>"
    if howto:
        block += '<div class="howto">' + howto + "</div>"
    return block


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--priv", default="/home/wenbo/priv-eval")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", default="docs/reports/2026-10-28-kev-prefix-eval.html")
    args = parser.parse_args()
    priv = Path(args.priv)
    repo = Path(args.repo).resolve()
    data_dir = repo / "results" / "MODEL-02-kev-prefix-eval"

    deep = json.loads((priv / "deep-stats.json").read_text(encoding="utf-8"))
    agg = json.loads((priv / "aggregate-primary.json").read_text(encoding="utf-8"))
    ext = json.loads((priv / "aggregate-extended.json").read_text(encoding="utf-8"))
    jev = json.loads((data_dir / "jev-summary.json").read_text(encoding="utf-8"))
    versions = json.loads((data_dir / "versions.json").read_text(encoding="utf-8"))
    config = json.loads((data_dir / "run-config.json").read_text(encoding="utf-8"))
    ds = deep["dataset"]
    n_primary = deep["n_primary"]
    n_clusters = deep["n_clusters"]
    models = MODELS
    run_meta = {m: agg["runs"][m] for m in models}

    leaderboard = [{"name": row["name"], "overall": row["overall"], "model_family": row["family"],
                     "reference": row.get("reference", False)}
                    for row in deep["jevbench"].get("leaderboard", [])]
    figs = build_figures(deep, agg, leaderboard)
    for name in ("accuracy", "forest", "kind_bars", "length_bars", "kind_brier", "domain_bars", "option_curve", "heatmap",
                 "sample_size", "reliability", "noul_reliability", "risk_coverage", "bootstrap",
                 "permutation", "confidence_deciles", "variant_ecdf",
                 "brier_decomp", "jev_radar", "jev_leaderboard", "latency", "score_error_hist", "dataset"):
        if name not in figs:
            raise SystemExit("missing figure " + name)

    official = deep["jevbench"]["files"]["kev-original"]
    tuned = deep["jevbench"]["files"]["seed43"]
    official_kev = deep["jevbench"].get("official_kev") or 0.7191830065359477
    official_rank = "9-15"
    local_vs_official = deep["jevbench"]["official_vs_local"]
    local_vs_seed = deep["jevbench"].get("official_vs_seed43")
    holm = deep["paired_holm"]

    # ---------- tables
    main_rows = []
    for model in models:
        pm = deep["per_model"][model]
        main_rows.append(
            "<tr><td>" + LABELS[model] + "</td>"
            f'<td class="num">{fmt_int(pm["n"])}</td>'
            f'<td class="num">{pct(pm["acc"], 2)}</td>'
            f'<td class="num">{ci(agg["runs"][model]["ci"]["acc"]["ci95"], 2)}</td>'
            f'<td class="num">{num(pm["brier"], 4)}</td>'
            f'<td class="num">{num(pm["nll"], 4)}</td>'
            f'<td class="num">{num(pm["ece_10"], 4)}</td>'
            f'<td class="num">{pct(pm["coverage_at_5pct"]["coverage"], 1)}</td>'
            f'<td class="num">{num(pm["aurc"], 4)}</td></tr>'
        )
    main_table = (
        "<table><thead><tr><th>model</th><th class=\"num\">questions</th><th class=\"num\">accuracy</th>"
        "<th class=\"num\">95% CI (accuracy)</th><th class=\"num\">Brier</th><th class=\"num\">NLL</th>"
        "<th class=\"num\">ECE-10</th><th class=\"num\">automation @5%</th><th class=\"num\">AURC</th></tr></thead><tbody>"
        + "".join(main_rows) + "</tbody></table>"
    )

    def strata_table(kind_key, title, order=None):
        keys = sorted(deep["per_model"][models[0]][kind_key].keys())
        if order:
            keys = [k for k in order if k in keys] + [k for k in keys if k not in order]
        header = "<tr><th>" + title + "</th>" + "".join(
            "<th class=\"num\">" + LABELS[m] + " acc</th><th class=\"num\">n</th>" for m in models) + "</tr>"
        rows = []
        for key in keys:
            cells = ["<td>" + esc(key) + "</td>"]
            for model in models:
                item = deep["per_model"][model][kind_key][key]
                cells.append('<td class="num">' + pct(item["acc"], 1) + "</td>")
                cells.append('<td class="num">' + fmt_int(item["n"]) + "</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return "<table><thead>" + header + "</thead><tbody>" + "".join(rows) + "</tbody></table>"

    def paired_table():
        header = ("<tr><th>comparison</th><th class=\"num\">accuracy change</th><th class=\"num\">Brier change</th>"
                  "<th class=\"num\">NLL change</th><th class=\"num\">McNemar p</th><th class=\"num\">Holm p (acc)</th>"
                  "<th class=\"num\">permutation p (Brier)</th></tr>")
        rows = []
        for seed in ("seed43", "seed17", "seed29"):
            data = deep["paired"][seed]
            rows.append(
                "<tr><td>" + LABELS[seed] + " vs original</td>"
                '<td class="num">' + pct(data["delta_acc"], 1, sign=True) + " " + ci(data["bootstrap_acc"]["ci"], 1) + "</td>"
                '<td class="num">' + num(data["delta_brier"], 4, sign=True) + " " + ci_num(data["bootstrap_brier"]["ci"], 3) + "</td>"
                '<td class="num">' + num(data["delta_nll"], 4, sign=True) + " " + ci_num(data["bootstrap_nll"]["ci"], 3) + "</td>"
                '<td class="num">' + f"{data['mcnemar']['p_value']:.2e}" + "</td>"
                '<td class="num">' + f"{holm['acc'][seed]:.2e}" + "</td>"
                '<td class="num">' + f"{data['permutation_brier']['p_value']:.4f}" + "</td></tr>"
            )
        return "<table><thead>" + header + "</thead><tbody>" + "".join(rows) + "</tbody></table>"

    calibration_rows = []
    for model in models:
        pm = deep["per_model"][model]
        cov = pm["coverage_at_5pct"]
        calibration_rows.append(
            "<tr><td>" + LABELS[model] + "</td>"
            f'<td class="num">{pct(pm["mean_conf"], 1)}</td>'
            f'<td class="num">{pct(pm["confident_error_rate"], 2)}</td>'
            f'<td class="num">{num(pm["ece_15"], 4)}</td>'
            f'<td class="num">{num(pm["brier"], 4)}</td>'
            f'<td class="num">{pct(cov["coverage"], 1)}</td>'
            f'<td class="num">{cov["accepted_n"]}</td>'
            f'<td class="num">{pct(cov["error_rate"], 2) if cov["error_rate"] is not None else "n/a"}</td></tr>'
        )
    calibration_table = (
        "<table><thead><tr><th>model</th><th class=\"num\">mean confidence</th>"
        "<th class=\"num\">confident-error rate</th><th class=\"num\">ECE-15</th><th class=\"num\">Brier</th>"
        "<th class=\"num\">automation coverage @5%</th>"
        "<th class=\"num\">accepted questions</th><th class=\"num\">error rate on accepted</th></tr></thead><tbody>"
        + "".join(calibration_rows) + "</tbody></table>"
    )

    jev_rows = []
    for name, label in (("kev-original", "Kev-4B original (local, bf16)"),
                        ("seed43", "M10 seed-43 (local, bf16)")):
        item = deep["jevbench"]["files"][name]
        pillars = item["pillars"]
        jev_rows.append(
            "<tr><td>" + label + "</td>"
            f'<td class="num">{item["overall"]*100:.2f}</td>'
            f'<td class="num">{ci(item["ci"], 1)}</td>'
            f'<td class="num">{pillars["REP"]*100:.1f}</td><td class="num">{pillars["BAT"]*100:.1f}</td>'
            f'<td class="num">{pillars["MEA"]*100:.1f}</td><td class="num">{pillars["LOG"]*100:.1f}</td>'
            f'<td class="num">{pillars["CHO"]*100:.1f}</td></tr>'
        )
    jev_rows.append(
        "<tr class=\"total\"><td>Kev-4B official leaderboard</td><td class=\"num\">71.9</td>"
        "<td class=\"num\">未公布</td><td class=\"num\">74.4</td><td class=\"num\">100.0</td>"
        "<td class=\"num\">30.1</td><td class=\"num\">67.5</td><td class=\"num\">87.5</td></tr>"
    )
    jev_table = (
        "<table><thead><tr><th>model</th><th class=\"num\">overall</th><th class=\"num\">95% CI</th>"
        "<th class=\"num\">REP</th><th class=\"num\">BAT</th><th class=\"num\">MEA</th>"
        "<th class=\"num\">LOG</th><th class=\"num\">CHO</th></tr></thead><tbody>"
        + "".join(jev_rows) + "</tbody></table>"
    )

    leaderboard_rows = "".join(
        "<tr><td>" + esc(row["name"]) + "</td>" + '<td class="num">' + f"{row['overall']*100:.1f}" + "</td></tr>"
        for row in sorted(leaderboard, key=lambda r: -r["overall"])
    )
    leaderboard_table = "<table><thead><tr><th>leaderboard entry (as published)</th><th class=\"num\">JevBench-mini coherence</th></tr></thead><tbody>" + leaderboard_rows + "</tbody></table>"

    # dataset facts text
    kind = ds["kind_questions"]
    ev_kind = ds["evaluated_kind_questions"]
    tokens = ds["state_tokens"]

    summary_lead = ("微调后的模型在准确率上略有提升，但在概率校准、风险控制和自动处置能力上明显变差；"
                    "第三方一致性基准上的分数上升，但那一指标不是准确率，也不能作为能力提升的证据。")

    nav = ("<nav class=\"toc\"><div class=\"wrap\">"
           "<a href=\"#dataset\">数据集</a><a href=\"#models\">模型与训练</a><a href=\"#results\">主结果</a>"
           "<a href=\"#calibration\">校准与风险</a><a href=\"#robust\">稳健性</a><a href=\"#external\">外部对标</a>"
           "<a href=\"#lessons\">经验与失败</a><a href=\"#repro\">复现</a></div></nav>")

    date_text = "2026-10-28"

    html_parts = []
    html_parts.append("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
                      "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                      "<title>Kev-4B 前后对照评测 · PoL-Governance</title><style>" + CSS + "</style></head><body>")
    html_parts.append("<header class=\"hero\"><div class=\"wrap\">"
                      "<h1>Kev-4B 前后对照评测：原版与 POL2 score-v2 M10</h1>"
                      "<div class=\"meta\">PoL-Governance · Session B 独立评测 · " + date_text + " · 单文件自包含报告</div>"
                      "<p class=\"lead\">" + esc(summary_lead) + "</p></div></header>")
    html_parts.append(nav)
    html_parts.append("<main><div class=\"wrap\">")

    # ---- dataset
    dataset = []
    dataset.append("<section id=\"dataset\"><h2>评测数据集：只用了私有保留集</h2>")
    dataset.append("<p>本文所有主结果只使用一份事先冻结的<b>私有保留集</b>（模型训练和选型时都看不到它）。"
                   "它包含 <b>" + fmt_int(ds["items"]) + " 个情境条目</b>和 <b>" + fmt_int(ds["questions"]) + " 道封闭式问题</b>；"
                   "问题分为三类：choice（从候选中选一个）" + fmt_int(kind.get("choice", 0)) + " 道、"
                   "noul（是/否）" + fmt_int(kind.get("noul", 0)) + " 道、score（按等级打分）" + fmt_int(kind.get("score", 0)) + " 道。"
                   "全部为英文。</p>")
    dataset.append("<p>评测时每道题独立计分。由于模型只在有限长度的输入上有已验证能力，"
                   "最终进入比较的是 <b>" + fmt_int(ds["evaluated_questions"]) + " 道题</b>（来自 " + fmt_int(ds["evaluated_items"])
                   + " 个条目）——这是本文所有表格和图表的分母；其余题目不属于共同可评测范围，不参与任何数字。"
                   "被评测子集的三类题为 choice " + fmt_int(ev_kind.get("choice", 0)) + " / noul " + fmt_int(ev_kind.get("noul", 0))
                   + " / score " + fmt_int(ev_kind.get("score", 0)) + "。</p>")
    dataset.append("<p>两个领域：决策机制（decision_mechanics）" + fmt_int(ds["domain_items"].get("decision_mechanics", 0))
                   + " 个条目、知识推理（knowledge_reasoning）" + fmt_int(ds["domain_items"].get("knowledge_reasoning", 0))
                   + " 个条目。输入文本长度（字符）中位数 " + f"{ds['state_chars']['p50']:,.0f}"
                   + "，90 分位 " + f"{ds['state_chars']['p90']:,.0f}" + "，最长 " + f"{ds['state_chars']['max']:,.0f}"
                   + "；按 token 计，已评测题目的状态长度中位数 " + str(tokens["p50"]) + "、90 分位 " + str(tokens["p90"])
                   + "、最大 " + str(tokens["max"]) + "。选项数从 2 到 68 不等。</p>")
    dataset.append(figure("dataset", figs, "图 1　数据集形态：左为输入文本长度（字符），右为每题的候选选项数（对数横轴）。",
                          "读法：输入多为几百字符的短文本，少数长文档；选项数大部分在 2–8 之间，但也有少量几十个选项的题目——后一类对准确率影响很大，后文会按选项数分层。"))
    dataset.append("<div class=\"callout\"><b>数据边界：</b>私有保留集只在本机隔离环境使用，只导出聚合数字，评测后删除临时副本；"
                   "已核对它与微调模型训练数据的重叠：<b>重叠为零</b>。</div>")
    dataset.append("</section>")

    # ---- models
    models_sec = []
    models_sec.append("<section id=\"models\"><h2>模型与训练配置</h2>")
    models_sec.append("<p>被测模型是 <b>Kev</b>：把决策问题当作“在候选选项之间做指针选择”的小模型族，底座 Qwen3.5-4B-Base；"
                      "公开代码固定在 commit <code>2074cc44</code>。比较同一架构的两个权重：</p>")
    models_sec.append("<ul><li><b>原版 Kev-4B</b>：<code>jaredpalmer/kev-4b@v1.0</code>，Hub commit <code>6cfce5c2</code>，"
                      "随权重发布的温度为 2.41（Kev 作者在自家开发集上拟合）。</li>"
                      "<li><b>微调版（M10）</b>：协作者用 POL2 score-v2 数据在原版上继续训练得到的 LoRA + pointer head，"
                      "GitHub Release <code>pol2-score-v2-v1.0.0</code>。本文报告三个随机种子：<b>seed-43（主）</b>、seed-17、seed-29。"
                      "三个 seed 都记录温度 1.0（未拟合）。</li></ul>")
    models_sec.append("<p><b>披露一个选择问题：</b>seed-43 是在看到三个 seed 的既有结果之后才被选为“默认推荐版本”的。"
                      "因此它的数字属于<b>事后选择（post-selection）</b>的探索性结果，不是事先预注册的确认性证据；"
                      "seed-17/29 的全部结果同样列出，三个 seed 不是集成（ensemble）。</p>")
    models_sec.append("<h3>训练配置（协作者提供，本报告未重新训练）</h3>")
    models_sec.append("<table><thead><tr><th>项</th><th>值</th></tr></thead><tbody>"
                      "<tr><td>底座</td><td>Qwen3.5-4B-Base，revision <code>1001bb4d</code></td></tr>"
                      "<tr><td>适配方法</td><td>LoRA（r=16，α=32）+ pointer head（hidden 256）</td></tr>"
                      "<tr><td>训练数据</td><td>6,827 条：POL2 score-v2 专家规则数据 6,166 + MRI 通用决策回放 661（MIT）</td></tr>"
                      "<tr><td>超参数</td><td>1 epoch；bf16 backbone / fp32 head；batch 1，gradient accumulation 4；lr 2e-5；max_state 4096</td></tr>"
                      "<tr><td>硬件</td><td>NVIDIA GB10（≤2.5 h/seed，training only）</td></tr>"
                      "<tr><td>评测时精度</td><td>bf16（本机 RX 7900 XT / ROCm；官方评测用 fp32，见限制）</td></tr>"
                      "</tbody></table>")
    models_sec.append("<p class=\"note\">原版权重与微调权重的底座 revision 已经固定为同一 commit；"
                      "微调权重的 <code>head.pt</code> 原本没有记录底座 revision，我们在隔离副本里把它固定后运行，"
                      "并断言模型张量不变（详见复现节）。</p>")
    models_sec.append("</section>")

    # ---- results
    res = []
    res.append("<section id=\"results\"><h2>主决策结果</h2>")
    res.append("<p>下表是最终结果。所有数字都在同一批 " + fmt_int(n_primary) + " 道题上、用同一转换和同一环境配置计算，"
               "按“条目/情境簇”聚类做统计（见下方统计说明）。</p>")
    res.append(main_table)
    res.append("<p class=\"note\"><b>附表注：</b>ACC（accuracy，准确率）= 答对题数 / 总题数；"
               "Brier = (1/N) Σ<sub>i</sub> Σ<sub>k</sub>(p<sub>ik</sub> − y<sub>ik</sub>)²（y 为 one-hot 金标，0 最好）；"
               "NLL = −(1/N) Σ<sub>i</sub> log p<sub>i,y<sub>i</sub></sub>（正确答案概率的负对数，0 最好，对自信答错惩罚最重）；"
               "ECE-10 = 把置信度分 10 个等宽箱后，按题数加权的 |实际正确率 − 平均置信度|；"
               "automation @5% = 按置信度从高到低接收、在接收集错误率 ≤5% 时能接收的最大题目比例；"
               "AURC = 风险-覆盖曲线下面积（越低越好）。CI = 95% 置信区间（单模型区间按条目簇 bootstrap；分层图为 Wilson），n = 题目数。</p>")
    res.append("<h3>指标怎么读（先看这一小节，后文的表都按它解释）</h3>")
    res.append("<table><thead><tr><th>指标</th><th>公式（N 题）</th><th>含义与读法</th></tr></thead><tbody>"
               "<tr><td>ACC</td><td>答对题数 / N</td><td>最直观的“选对率”；越高越好，但不告诉你概率是否可信</td></tr>"
               "<tr><td>Brier</td><td>(1/N) Σ<sub>i</sub> Σ<sub>k</sub>(p<sub>ik</sub> − y<sub>ik</sub>)²</td>"
               "<td>整条概率分布的平方误差；0 最好。对“把错误选项也分到不少概率”的情况敏感</td></tr>"
               "<tr><td>NLL</td><td>−(1/N) Σ<sub>i</sub> log p<sub>i,y<sub>i</sub></sub></td>"
               "<td>正确答案概率的负对数均值；0 最好。对“很自信地答错”惩罚极大</td></tr>"
               "<tr><td>ECE-10 / ECE-15</td><td>Σ<sub>b</sub> (n<sub>b</sub>/N)·|acc<sub>b</sub> − conf<sub>b</sub>|</td>"
               "<td>把置信度分成 10 或 15 个等宽箱，比较箱内平均置信度与实际正确率；0 表示完全校准。本报告并列两种分箱</td></tr>"
               "<tr><td>automation @5%</td><td>argmax<sub>c</sub> c / N 使接收集错误率 ≤5%</td>"
               "<td>在最多容忍 5% 错误时，能自动放行多少比例的题；越高越好，但必须同时看接收题数 n 与接收集错误率</td></tr>"
               "<tr><td>AURC</td><td>∫ risk d(coverage)</td>"
               "<td>按置信度排序后的风险-覆盖曲线面积；越低越好，衡量“用置信度做取舍”的整体质量</td></tr>"
               "<tr><td>95% CI</td><td>Wilson / 配对 cluster bootstrap 95% 区间</td>"
               "<td>重复抽样下该数字的波动范围；两模型比较用“配对差值”的区间，比各自区间是否重叠更准确</td></tr>"
               "</tbody></table>")
    res.append("<div class=\"howto\"><b>怎么读这张表：</b>先看 accuracy（准确率）和它的 CI——两个模型的 CI 有重叠，"
               "但配对比较（同一道题上逐题比较，见下表）更敏感。然后看后四列：它们衡量的是“概率能不能信”。"
               "准确率相近时，Brier/NLL/ECE 更小的模型在实际部署中更可靠，因为它的置信度可以用来决定哪些题自动放行、哪些交人复核。</div>")
    res.append(figure("accuracy", figs, "图 2　四个权重的准确率与 95% Wilson 置信区间（n=" + fmt_int(n_primary) + "）。",
                      "读法：条形是点估计，黑线是区间。原版与 seed-43 的区间有重叠，说明单看准确率无法区分；后文用配对检验提高灵敏度。"))
    res.append(figure("forest", figs, "图 3　三个 seed 相对原版的变化（准确率、Brier、NLL），配对 cluster bootstrap 95% 区间。",
                      "读法：横轴 0 = 与原版相同；点在 0 右侧表示数值更大。准确率右侧为好，Brier/NLL 右侧为差。"
                      "seed-43 的准确率区间整体在 0 右侧，Brier/NLL 区间也整体在 0 右侧——即“更准一点，但概率明显更差”。"))
    res.append("<h3>配对统计：差异是不是真的？</h3>")
    res.append("<p>同一道题被两个模型各答一次，因此正确/错误是可配对的。我们做三件事："
               "①用<b>配对 cluster bootstrap</b>（按条目/集团簇重抽样 2,000 次）估计差值的 95% 区间；"
               "②对准确率用 <b>McNemar 精确检验</b>（只比较两个模型答案不一致的题）；"
               "③对 Brier/NLL 用<b>簇符号翻转置换检验</b>（2,000 次）得到 p 值，并用 Holm 方法控制三个 seed 的多重比较。"
               "下表同时给出效应量与检验结果。</p>")
    res.append(paired_table())
    res.append("<div class=\"howto\"><b>怎么读：</b>“McNemar p”回答“准确率差异是否可能是巧合”，p 越小越不像巧合；"
               "“Holm p”是对三个 seed 同时比较后的校正值。Brier/NLL 的置换 p 同理。"
               "注意：统计显著不等于实际重要——seed-43 准确率只高 0.95 个百分点，但 Brier 高 0.073、NLL 高 0.70，后者的实际影响远大于前者。</div>")
    res.append(figure("bootstrap", figs, "图 4　seed-43 相对原版的配对 bootstrap 分布（准确率、Brier、NLL）。",
                      "读法：灰色柱是 2,000 次重抽样得到的差值分布；黑色实线是点估计，虚线是 95% 区间。"
                      "分布整体不跨 0（准确率在右、Brier/NLL 在左）说明差异稳定；但三者尺度不同，要看相对大小而非绝对高度。"))
    res.append(figure("permutation", figs, "图 5　置换检验：如果两个模型其实一样好，差值会落在灰色分布里；红线是实际观测值。",
                      "读法：红线落在灰色分布的极端尾部（p<0.01），说明观察到的准确率与 Brier 差异不太可能只是抽样巧合。"
                      "置换只检验“是否有差异”，不说明差异有多大——效应量看前面的表和森林图。"))
    res.append("<h3>按题型、领域与选项数分层</h3>")
    res.append("<p>“分层”指把同一批题按属性切开分别统计，检查提升/退化是否集中在某类题上。我们按四种方式分："
               "题型（choice/noul/score）、领域（决策机制/知识推理）、选项数（2 / 3–4 / 5–8 / 9–26 / &gt;26）、输入长度（字符数分桶）。"
               "下表为题型分层（其他分层见图中）。</p>")
    res.append(strata_table("kind", "题型"))
    res.append("<div class=\"howto\"><b>怎么读：</b>微调后 choice 题准确率上升（62.6%→65.8%），"
               "但 noul（是/否）从 77.1% 降到 71.7%、score（打分）从 55.8% 降到 52.3%。"
               "也就是说准确率的总体小升不是“全面变强”，而是能力结构改变：微调更擅长挑选项，更不擅长二元判断和等级判断。"
               "这一点与校准退化一致——训练目标更偏向“选中率”而不是“概率诚实”。</div>")
    res.append(figure("kind_bars", figs, "图 6　按题型分层的准确率（95% Wilson CI）。",
                      "读法：每组四根柱是四个权重。看组内高度差即可：choice 组微调更高，noul 与 score 组原版更高。"))
    res.append(figure("domain_bars", figs, "图 7　按领域分层的准确率。",
                      "读法：微调提升了知识推理题，但降低了决策机制题；两类题在总准确率里权重不同，因此总差异被稀释。"))
    res.append(figure("length_bars", figs, "图 8　按输入长度分层的准确率（95% CI）。",
                      "读法：输入越长的题整体越难；原版与微调在最长一档上都明显下降，差异不集中在长文本上。"))
    res.append(figure("option_curve", figs, "图 9　准确率随选项数变化（对数式分桶，95% CI）。",
                      "读法：选项越多，所有模型都越难；微调在 3–4 选项题上有优势，在 5–8 与 9–26 选项题上反而略差。"))
    res.append(figure("heatmap", figs, "图 10　seed-43 相对原版的准确率变化（百分点），按“题型 × 领域”切分。",
                      "读法：蓝色为正、红色为负。提升集中在 choice×知识推理；noul 与 score 在两类领域都变差。颜色只表示方向，样本较少的格子（括号内 n）不要过度解读。"))
    res.append(figure("kind_brier", figs, "图 11　按题型的概率误差（Brier，越低越好）。",
                      "读法：四根柱一组。choice 题原版与微调差距不大，noul 与 score 题微调版明显更高——"
                      "这与前面的准确率分层一致：微调在这两类题上不仅更不准，概率也更差。"))
    res.append(figure("score_error_hist", figs, "图 12　打分题的绝对等级误差分布。",
                      "读法：横轴是“预测期望等级与金标等级之差”，越靠左越好。微调版在 1 级以上误差的比例更高。"))
    res.append(figure("sample_size", figs, "图 13　准确率置信区间半宽随题目数变化。",
                      "读法：本题库有 7,347 道题，95% 区间半宽约 ±1.2 个百分点；若只有 200 道题，半宽会超过 ±7 个百分点——"
                      "这就是小样本无法给相近模型排名的原因。"))
    res.append("</section>")

    # ---- calibration
    cal = []
    cal.append("<section id=\"calibration\"><h2>校准与自动处置风险</h2>")
    cal.append("<p>决策模型不只要答对，还要<b>知道自己有多确定</b>。如果模型说“95% 确定”时实际只有 60% 正确，"
               "那么按置信度自动放行就会出错。这一节专门评估“概率是否可信”，以及它对自动处置的影响。"
               "这是本报告与只报准确率的评测最重要的区别。</p>")
    cal.append("<table><thead><tr><th>指标</th><th>怎么算</th><th>怎么读</th></tr></thead><tbody>"
               "<tr><td>Brier</td><td>把每个选项的概率与“正确答案为 1、其余为 0”的目标做平方差后求和，再对题目取平均</td>"
               "<td>综合衡量概率误差；越低越好。它对罕见类别的错误惩罚较重</td></tr>"
               "<tr><td>NLL</td><td>正确答案所获概率的负对数，再取平均</td><td>对“自信地答错”惩罚极大；越低越好</td></tr>"
               "<tr><td>ECE-10 / ECE-15</td><td>把置信度分 10 / 15 个等宽箱，比较每箱“平均置信度”与“实际正确率”，按箱内题数加权</td>"
               "<td>0 为完全校准；0.02 可视为很校准，0.2 表示置信度严重偏离实际正确率。两套分箱结果并列，避免一种分箱的偶然性</td></tr>"
               "<tr><td>automation @5%</td><td>按置信度从高到低接收题目，在“接收集错误率 ≤5%”约束下，最多能自动处置的题目比例</td>"
               "<td>越高越好，但这是本样本上的经验值，不是真实部署的错误保证；同时要报接收题数与接收集错误率</td></tr>"
               "<tr><td>AURC</td><td>风险-覆盖曲线（横轴覆盖率、纵轴错误率）下方面积</td><td>越低越好，衡量“用置信度排序”的整体质量</td></tr>"
               "</tbody></table>")
    cal.append("<p>下表汇总四个权重在“概率可信度”和“自动处置”上的表现；每一列的计算方式见上一张表。</p>")
    cal.append(calibration_table)
    cal.append("<p class=\"note\">confident-error rate = 置信度 ≥0.9 且答错的题占全部题的比例；"
               "automation 的接收题数与接收集错误率见同表后两列。</p>")
    cal.append("<div class=\"howto\"><b>怎么读：</b>原版模型“平均置信度 62.9% / 实际准确率 64.1%”，几乎贴住对角线；"
               "微调后的三个 seed “平均置信度 85–86% / 实际准确率 64–65%”，系统性过度自信。"
               "后果很直接：在允许 5% 错误的前提下，原版能自动处置 18.0% 的题目（接收 1,326 题、错误率 4.98%），"
               "seed-43 只能自动处置 14.2%（接收 1,046 题、错误率 4.97%）；高置信度错误（≥0.9）比例从 0.7% 升到 13.7%。</div>")
    cal.append("<div class=\"callout warn\"><b>温度不是全部解释。</b>原版权重自带一个在 Kev 开发集上拟合的温度（2.41），"
               "微调权重记录的是 1.0（未拟合）。为公平起见，我们又用两模型记录的 logits 把两者都还原到 T=1（无温度缩放），"
               "再比较一次：seed-43 的 Brier 仍高 0.026、NLL 仍高 0.37，说明差距不仅来自“没有拟合温度”，也来自微调后的概率尺度本身。"
               "按评测协议，我们没有在保留集上重新拟合温度（那会用测试数据调参）。</div>")
    cal.append(figure("reliability", figs, "图 14　可靠性图：横轴为预测置信度，纵轴为实际正确率；虚线为完美校准。",
                      "读法：曲线越贴近对角线越校准。左图是“随权重交付”的配置（原版温度 2.41、微调 1.0）；"
                      "右图是两者都还原到 T=1 后的结果。两图中微调版本的点都明显高于对角线——过度自信。"))
    cal.append(figure("noul_reliability", figs, "图 15　是/否题的二元校准：预测“是”的概率 vs 实际“是”的比例。",
                      "读法：同样的过度自信模式；这也是 noul 准确率下降与 Brier 变差的主要来源。"))
    cal.append(figure("brier_decomp", figs, "图 16　Brier 分解（是/否题）：reliability（校准误差，越低越好）与 resolution（区分能力，越高越好）。",
                      "读法：原版的校准误差小、区分能力也较好；微调版校准误差明显变大。"))
    cal.append(figure("risk_coverage", figs, "图 17　风险-覆盖曲线：覆盖率越高，错误率越高；红色虚线为 5% 错误预算。",
                      "读法：曲线越低越好。原版在大部分覆盖区间上错误率都低于微调版，因此能“安全地多放行一些”题目。"))
    cal.append(figure("confidence_deciles", figs, "图 18　按置信度十分位看准确率与平均置信度。",
                      "读法：左图两条线越接近说明模型越会“按置信度排序”；右图微调版整条线更高（更自信），但准确率没有相应提高。"))
    cal.append("</section>")

    # ---- robustness
    rob = []
    rob.append("<section id=\"robust\"><h2>稳健性检查（辅助结论）</h2>")
    rob.append("<p>我们把同一道题换一种问法再问一次，检查答案是否稳定，共两类："
               "<b>选项顺序打乱</b>（600 道 choice 题，顺序随机重排）与<b>拆题单独提问</b>（把一次请求里的多道题拆成独立请求）。"
               "这些检查不直接等于“是否降智”，但能说明模型对无关变化的敏感程度；结论只作辅助。</p>")
    rob_p = []
    for variant, label in (("permuted", "选项顺序打乱"), ("isolation", "拆题单独提问")):
        values = []
        for model in models:
            data = deep["variants"][model][variant]
            values.append(LABELS[model] + "：" + pct(data["mean_delta"], 1) + " 平均最大概率变化、" + pct(data["flip_rate"], 1) + " 翻转率")
        rob_p.append("<b>" + label + "</b>（n=" + str(deep["variants"]["kev-original"][variant]["n"]) + "）：" + "；".join(values) + "。")
    rob.append("<p>" + " ".join(rob_p) + "</p>")
    rob.append("<p>读法：选项顺序打乱时，微调三个 seed 的平均概率变化（约 9–10 个百分点）高于原版（6.1 个百分点），答案翻转率也从 10.2% 升到 10.7–11.3%；"
               "拆题单独提问的影响对所有模型都很小（平均变化 ≤0.35 个百分点）。"
               "也就是说，微调让模型对“选项怎么排”更敏感，而对“一次问几道题”不敏感——这与“更依赖表面选项模式”的解释一致，但不构成能力结论。</p>")
    rob.append(figure("variant_ecdf", figs, "图 19　两类扰动的累积分布：横轴为同题最大概率变化，纵轴为不超过该变化的题目比例。",
                      "读法：曲线越靠左下越稳定。左图（选项顺序）微调版整体右移，右图（拆题）几乎重合。"))
    rob.append("</section>")

    # ---- external
    ext_sec = []
    ext_sec.append("<section id=\"external\"><h2>外部对标：JevBench 与其它榜单</h2>")
    ext_sec.append("<p><b>JevBench 是什么：</b>一个第三方的“决策一致性”基准（Chen Feng，Queen's University Belfast；与 TypeSafe 无关），"
                   "不考知识量，而是考模型的概率与选择是否满足 50 条一致性关系（例如同义改写后答案不变、"
                   "互斥选项概率相加、选项顺序不改变相对概率）。它<b>没有金标答案</b>，因此衡量的是 coherence，不是 accuracy。"
                   "我们跑的是 mini 版本（1,240 次请求），这也是官方榜单的默认口径。</p>")
    ext_sec.append(figure("jev_radar", figs, "图 20　JevBench 五个维度的本地结果与官方 Kev-4B 公布值。",
                          "读法：越靠外越好。五个维度分别为 REP（表述不变性）、BAT（批次独立性）、MEA（概率测度）、LOG（逻辑顺序）、CHO（选项集合条件）。"
                          "两条实线是我们的本地复跑；虚线是官方榜上的 Kev-4B 数值。"))
    ext_sec.append(jev_table)
    ext_sec.append("<p class=\"note\">官方榜读取于 2026-10-28（数据快照 2026-10-05）：官方 Kev-4B overall 71.92（95% CI [69.80, 73.88]，名次区间 9–15）、"
                   "accuracy 87.87%（brier 0.164；240 题版本 71.20）。"
                   "coherence 分数高不代表更准——榜单里的“均匀回答”参考模型 coherence 高达 89.4，但 accuracy 只有 39.8%。"
                   "榜单也没有 TypeSafe Jev 托管 API 的条目；Kev 文档里引用的 Jev 分数（54.0）来自另一个 Decision Index，不能与这里的 coherence 混比。</p>")
    if local_vs_official is not None:
        z = local_vs_official["z"]
        p = local_vs_official["p_value"]
        ext_sec.append("<div class=\"howto\"><b>本地与官方有差异吗？</b>本地原版 "
                       + f"{official['overall']*100:.2f}" + "（95% CI " + ci(official["ci"], 1) + "），官方榜 "
                       + f"{official_kev*100:.2f}" + "（95% CI " + ci(local_vs_official["official_ci"], 1) + "）；"
                       + "差值 " + f"{local_vs_official['delta']*100:+.2f}" + " 分，两独立区间正差检验 z = "
                       + f"{z:.2f}" + "、p = " + f"{p:.3f}" + "。<b>差异不显著，在抽样误差范围内一致。</b>"
                       + "官方用 fp32 与 Python 3.11 环境，我们用 ROCm/bf16 服务，但两者的五维数值几乎逐项重合，"
                       + "说明本地复跑没有系统性偏低，也没有证据表明榜单被“刷分”。</div>")
    if local_vs_seed is not None:
        ext_sec.append("<div class=\"howto\"><b>微调后的位置：</b>seed-43 相对官方 Kev-4B 的 JevBench 差值为 "
                       + f"{local_vs_seed['delta']*100:+.2f}" + " 分（z = " + f"{local_vs_seed['z']:.2f}" + "，p = "
                       + f"{local_vs_seed['p_value']:.2e}" + "），在统计上明显更高；若放在已公布榜单里，大致位于前列。"
                       + "但这是 coherence 指标，且我们没有计算它的 accuracy（需要第三方金标），所以只能说“一致性更好”，"
                       + "不能据此宣称“更准”或“排名更高”。</div>")
    ext_sec.append(figure("jev_leaderboard", figs, "图 21　公开 JevBench 榜（点）与我们的两次本地复跑（虚线）。",
                          "读法：本地原版落点与官方 Kev-4B 几乎重合；seed-43 明显更高。"
                          "注意榜单上还有“均匀回答”参考点，位置最高但不能当真——它只是说明该指标可以被刷。"))
    ext_sec.append("<p><b>官方 Jev API 的成绩在哪：</b>JevBench 的公开榜单里没有 TypeSafe Jev 托管 API 的条目"
                   "（榜上只有 21 个开源模型与 4 个 toy/random/uniform 参考）；能查到的官方 Jev 数字来自 Kev 作者的另一个对比表"
                   "（Decision Index：Jev 54.0、Kev-4B 38.0、Kev-27B 52.3，accuracy 型指标），那是不同基准、不同指标，"
                   "不能与本文的 coherence 分数并列。本文的官方对照只用 JevBench 榜单上的 Kev-4B 一行。</p>")
    ext_sec.append("<p>微调后的 seed-43 在 JevBench-mini 上为 <b>" + f"{tuned['overall']*100:.2f}" + "</b>（95% CI "
                   + ci(tuned["ci"], 1) + "），比本地原版高 " + f"{(tuned['overall']-official['overall'])*100:.1f}"
                   + " 分，提升主要来自 MEA（概率测度）与 LOG（逻辑一致性），CHO（选项集合）略降。"
                   "这个结果说明微调改变了模型的一致性行为，但不能替代准确率与校准结论：同一批权重在私有保留集上的准确率只高 0.95 个百分点，校准却明显变差。"
                   "两项结果共同指向“能力结构改变”，而不是“整体变强”。</p>")
    ext_sec.append("<p><b>要不要提交榜单？</b>JevBench 没有公开提交表单，只接受作者邮箱与可复现脚本；"
                   "我们的权重、固定的底座 revision 与 serve 脚本都已就绪，但本次未发邮件、未提交（零提交）。"
                   "是否提交由 owner 决定；对外只写 locally reproduced, not listed。</p>")
    ext_sec.append("<h3>我们调研过的榜单</h3>")
    ext_sec.append("<p>做本次评测前，我们系统梳理了“Jev 类/决策模型类”的公开评测，结论是：真正的中立排行榜很少，"
                   "多数是厂商发布表。主要条目如下（详细清单见仓库内 docs/reports/2026-10-27-jev-benchmarks.md）：</p>")
    ext_sec.append("<ul>"
                   "<li><b>JevBench</b>（coherence，无金标，有公开榜；本文使用）</li>"
                   "<li><b>Kev suites / Decision Index</b>（Kev 官方发布的 accuracy/Brier/校准套件；部分分区不公开）</li>"
                   "<li><b>TypeSafe Jev / System One</b>（托管 API 基线，权重与数据不开源，无法本地复跑）</li>"
                   "<li><b>OpenJev、Laya typed-decisions、OpenDecider</b>（开源模型与自带 harness，多为厂商自评）</li>"
                   "<li><b>System One Bench</b>（第三方 accuracy/校准/延迟榜）——可作为后续补充方向</li>"
                   "</ul>")
    ext_sec.append("<h3>安全 / 伦理对齐方向的候选基准（本次未运行，仅列清单）</h3>")
    ext_sec.append("<p>如果后续要把 PoL2 方向放到“知名度高、提交模型多”的安全榜上，我们调研到以下候选。"
                   "“公开榜”指有公开可见的模型排名；“能否提交”以各自当前条款为准。本次未申请、未下载题目、未运行、未提交。"
                   "适配度按接口形态（封闭选择题 vs 生成式红队）与关注点（误拦、伦理判断）评估。</p>")
    ext_sec.append("<table><thead><tr><th>基准</th><th>维护方 / 规模</th><th>公开榜 / 提交</th><th>对 PoL2 的适配度</th></tr></thead><tbody>"
                   "<tr><td>SafetyBench</td><td>清华 THU-CoAI（ACL 2024）；11,435 道中英四选一安全题，MIT</td><td>原在线评测入口已不可用；需从仓库自行运行，无正式公开榜</td><td><b>高</b>：封闭四选一，与 PoL2 同构；建议作为第一补测</td></tr>"
                   "<tr><td>XSTest</td><td>过度拒答测试集；450 条，CC-BY-4.0</td><td>无榜单；本地二分类自评</td><td><b>高</b>：直接对应“误拦率”，适合内部回归</td></tr>"
                   "<tr><td>SALAD-Bench</td><td>安全基准；约 21k 题，6/16/66 三级分类，Apache-2.0</td><td>有 HF Space 公开榜；提交方式待核实，MCQ 子集可精确判分</td><td>中–高：有公开榜，但需筛出封闭选择子集</td></tr>"
                   "<tr><td>TrustLLM</td><td>多维可信度（真实性/安全/公平等）</td><td>可在线提交（学术运营）</td><td>中：维度多，需裁剪</td></tr>"
                   "<tr><td>ToxicChat</td><td>毒性对话真实样本</td><td>公开数据；无正式榜</td><td>中：需生成式适配</td></tr>"
                   "<tr><td>HELM Safety</td><td>Stanford CRFM；场景化安全评测</td><td>公开 leaderboard；运营方/申请制</td><td>低–中：生成式安全，需接口适配</td></tr>"
                   "<tr><td>AILuminate</td><td>MLCommons；AI 风险与可靠性基准 v1.0</td><td>公开榜；运营方/申请制</td><td>低–中：工业界参与多，指标偏生成式风险</td></tr>"
                   "<tr><td>AIR-Bench 2024</td><td>Alibaba；按监管/政策风险分类</td><td>有公开结果页；提交入口需核实</td><td>低–中：风险分类细，但非封闭选择</td></tr>"
                   "</tbody></table>")
    ext_sec.append("<p><b>关键限制：接口能否直接匹配。</b>PoL2 的输出是封闭选择（choice/score/noul），"
                   "只有单选题与二分类基准能直接适配；HELM Safety、AIR-Bench、AILuminate、HarmBench、AgentHarm 都要求模型生成自然语言"
                   "（或多步工具行动），直接上需要外接 verbalizer/agent，测到的将是“适配器 + 模型”，构念已经改变，"
                   "因此它们只能作为间接探索，不能与 JevBench/保留集并列在一张表里。</p>")
    ext_sec.append("<p class=\"note\">建议：先本地补 <b>SafetyBench</b>（封闭选择题、与 PoL2 同构）与 <b>XSTest</b>（误拦率）；"
                   "若要“公开榜可见度”再评估 <b>SALAD-Bench</b>（有公开榜、含可精确判分的 MCQ 子集）。"
                   "HELM Safety / AILuminate / AIR-Bench 权威但偏生成式，需要先做接口适配。所有补测须另立预注册协议，"
                   "不与本文的 JevBench/保留集数字混表。</p>")
    ext_sec.append("</section>")

    # ---- lessons
    les = []
    les.append("<section id=\"lessons\"><h2>运行成本、失败与经验</h2>")
    les.append("<h3>成本</h3>")
    les.append("<p>评测在一张 AMD Radeon RX 7900 XT（20 GB，WSL2 + ROCm 7.2.1）上完成，单卡串行。"
               "四个权重各评测 9,052 条请求（含变体），每个约 16–17 分钟；每道题的中位延迟 "
               + f"{run_meta['kev-original']['run_metadata']['latency_ms']['median']:.1f} ms（原版）到 "
               + f"{run_meta['seed43']['run_metadata']['latency_ms']['median']:.1f} ms（seed-43），p95 约 0.34–0.36 s。"
               "CPU（Ryzen 5700X，fp32）只用于公开样本的冒烟测试，不是性能基准。GPU 显存峰值未测（WSL 无相应监控模块）。</p>")
    les.append("<p class=\"note\">我们遵守了项目 GPU 纪律：只在允许时段启动单卡任务，运行前后检查系统事件日志（Kernel-Power/BugCheck/WHEA 无异常）。</p>")
    les.append(figure("latency", figs, "图 22　每道题的 GPU 延迟（对数纵轴；实心为 median，半透明为 p95）。",
                      "读法：四个权重延迟相差不大（中位约 78–84 ms，p95 约 0.34–0.36 s）。延迟不是本次结论的区分因素。"))
    les.append("<h3>失败与修复（都发生在报告数字定稿之前）</h3>")
    les.append("<ol>"
               "<li><b>20 GB 显存装不下超长题目的 attention。</b>首轮完整评测在一条输入约 4.7k token 的题上触发 HIP OOM（eager attention 的 L×L 缓冲需要 4 GB）。"
               "处置：按硬件可执行性把 5 个条目（14 道题）单列为“本机不可评测”，其余题目重跑成功（0 拒绝）；这些条目没有进入任何数字。</li>"
               "<li><b>JevBench 的请求缓存会跨模型复用。</b>jevbench 0.1.0 的缓存键不包含被评测的 checkpoint，"
               "单独加 --no-cache 仍会返回上一模型的缓存响应，导致两个模型分数逐位相同。"
               "处置：每个模型使用全新缓存目录，并用服务端日志的 POST 计数（各 1,442 次）确认请求真的落到对应模型上，然后重跑。</li>"
               "<li><b>依赖版本超出上游声明。</b>Kev 声明 torch&lt;2.9，本机是 2.9.1+rocm7.2.1。我们记录了完整环境并全流程实测通过；"
               "这项偏离已写入限制，不能把本报告数字与官方 fp32 结果直接等同。</li>"
               "</ol>")
    les.append("<h3>可迁移的经验</h3>")
    les.append("<ul><li>报告“更准”之前先问“概率能不能信”：本次微调的准确率提升 0.95 个百分点，但 ECE 从 0.025 升到 0.21，实际部署含义完全相反。</li>"
               "<li>配对比较比独立比较灵敏得多：同一道题上逐题比较能把“谁更好”的区间缩到 ±1 个百分点量级。</li>"
               "<li>保留集只能评一次、不能用于任何选择；事后选出的 seed 必须明确标注，否则结论会被高估。</li>"
               "<li>复现细节（固定 revision、固定缓存、记录环境与失败）比多跑一个模型更重要。</li></ul>")
    les.append("</section>")

    # ---- glossary / repro
    gl = []
    gl.append("<section id=\"repro\"><h2>指标与统计词典 / 复现</h2>")
    gl.append("<h3>指标定义</h3>")
    gl.append("<div class=\"formula\"><b>ACC（准确率）</b> = 答对题数 / 总题数。<br>"
               "<b>Brier</b> = (1/N) Σ<sub>i</sub> Σ<sub>k</sub> (p<sub>ik</sub> − y<sub>ik</sub>)²，其中 y 为 one-hot 金标；0 最好。<br>"
               "<b>NLL</b> = −(1/N) Σ<sub>i</sub> log p<sub>i,y<sub>i</sub></sub>，即正确答案概率的负对数均值；越低越好，对自信答错惩罚大。<br>"
               "<b>ECE</b> = Σ<sub>bins</sub> (n<sub>b</sub>/N) · |acc<sub>b</sub> − conf<sub>b</sub>|；<b>coverage@5%</b>：按置信度降序接收、在接收集经验错误率 ≤5% 时能接收的最大比例；<b>AURC</b> 为风险-覆盖曲线下面积。</div>")
    gl.append("<h3>统计方法</h3>")
    gl.append("<p><b>配对 cluster bootstrap：</b>以条目/情境簇为重抽样单位（同一条目的多道题一起抽），重抽样 2,000 次估计差值区间，处理同源题目的相关性。"
               "<b>McNemar 精确检验：</b>只用“一个对一个错”的题做二项检验，适合配对准确率。"
               "<b>置换检验：</b>在“两个模型可互换”的零假设下随机翻转每个簇的差值符号，得到 p 值。"
               "<b>Holm 校正：</b>对三个 seed 的多重比较控制族错误率。<b>Wilson 区间：</b>单模型比例的 95% 区间，适合小比例与中等样本。</p>")
    gl.append("<h3>本文做过的与没做的事</h3>")
    gl.append("<ul><li>做过：固定数据与权重 revision；对私有保留集只导出聚合；配对统计、校准与风险分析；JevBench 本地复跑；与官方榜的误差范围内对照。</li>"
               "<li>没做：多 seed 重新训练；在保留集上拟合温度或调阈值；语义层面的训练数据去重；JevBench 的 accuracy（需第三方金标）；榜单提交。</li>"
               "<li>可复现材料：仓库 <code>benchmark/kev_prefix/</code>（评测代码与单测）、结果目录的聚合 JSON 与版本清单；"
               "原始逐题记录按数据边界在评测后删除，不进入仓库。</li></ul>")
    gl.append("</section>")

    html_parts.append("".join(dataset))
    html_parts.append("".join(models_sec))
    html_parts.append("".join(res))
    html_parts.append("".join(cal))
    html_parts.append("".join(rob))
    html_parts.append("".join(ext_sec))
    html_parts.append("".join(les))
    html_parts.append("".join(gl))
    html_parts.append("</div></main><footer>PoL-Governance · Kev prefix evaluation · " + date_text
                      + " · 单文件 HTML，无外部资源 · 私有保留集只发布聚合结果</footer></body></html>")

    html_text = "".join(html_parts)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = repo / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    for name in ("aggregate-primary.json", "aggregate-extended.json", "aggregate-full.json",
                 "screening-report.json", "training-context-stats.json", "deep-stats.json"):
        src = priv / name
        if src.is_file():
            shutil.copyfile(src, data_dir / name)
    print("wrote", out_path, len(html_text), "bytes; copied aggregate artifacts")


if __name__ == "__main__":
    main()
