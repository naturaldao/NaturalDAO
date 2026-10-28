#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a forum-friendly derivative of the Kev evaluation report.

The canonical report is a self-contained HTML with inline CSS and inline SVG. Many forum
sanitizers strip <style>/<script>/<svg> (and may dump CSS as text), so this exporter rewrites
the same content into plain semantic HTML with PNG images embedded as data URIs, plus a folder
of standalone PNG files that can be uploaded to a forum/image host instead.

Usage:
  python build_forum_export.py --repo /path/to/repo --out docs/reports/2026-10-28-kev-prefix-eval-forum.html       --png-dir docs/reports/kev-forum-figures
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
from pathlib import Path

from report_figures import build_figures, get_pngs

FIG_NAMES = [
    "dataset", "accuracy", "forest", "bootstrap", "permutation", "kind_bars", "length_bars",
    "domain_bars", "option_curve", "heatmap", "kind_brier", "score_error_hist", "sample_size",
    "reliability", "noul_reliability", "brier_decomp", "risk_coverage", "confidence_deciles",
    "variant_ecdf", "jev_radar", "jev_leaderboard", "latency",
]


def load_json(path):
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--priv", default="/home/wenbo/priv-eval")
    parser.add_argument("--out", default="docs/reports/2026-10-28-kev-prefix-eval-forum.html")
    parser.add_argument("--png-dir", default="docs/reports/kev-forum-figures")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    data_dir = repo / "results" / "MODEL-02-kev-prefix-eval"
    canonical = (repo / "docs" / "reports" / "2026-10-28-kev-prefix-eval.html").read_text(encoding="utf-8")
    deep = load_json(data_dir / "deep-stats.json")
    agg = load_json(data_dir / "aggregate-primary.json")
    leaderboard = [{"name": row["name"], "overall": row["overall"], "model_family": row.get("family"),
                    "reference": row.get("reference", False)}
                   for row in deep["jevbench"].get("leaderboard", [])]
    figs = build_figures(deep, agg, leaderboard)
    pngs = get_pngs()
    names = [key for key in figs.keys()]
    if names != FIG_NAMES:
        raise SystemExit("figure order changed: " + repr(names))
    if len(pngs) != len(FIG_NAMES):
        raise SystemExit("png count mismatch: " + str(len(pngs)))

    png_dir = repo / args.png_dir
    png_dir.mkdir(parents=True, exist_ok=True)
    png_paths = []
    for index, (name, png) in enumerate(zip(FIG_NAMES, pngs), 1):
        filename = "fig-{:02d}-{}.png".format(index, name.replace("_", "-"))
        (png_dir / filename).write_bytes(png)
        png_paths.append(filename)

    body = re.search(r"<body[^>]*>(.*)</body>", canonical, flags=re.S).group(1)
    body = re.sub(r"<nav.*?</nav>", "", body, flags=re.S)
    # inline SVG -> PNG data URI
    counter = {"i": 0}
    def replace_svg(match):
        index = counter["i"]
        counter["i"] += 1
        encoded = base64.b64encode(pngs[index]).decode("ascii")
        return ('<p><img src="data:image/png;base64,' + encoded + '" alt="' + FIG_NAMES[index]
                + '" width="1000"></p>')
    body = re.sub(r"<svg.*?</svg>", replace_svg, body, flags=re.S)
    # markup that forums often strip: keep the content, drop the wrapper
    body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    body = re.sub(r"<figure[^>]*>", "<div>", body, flags=re.S)
    body = body.replace("</figure>", "</div>")
    body = re.sub(r"<figcaption[^>]*>", "<p><em>", body, flags=re.S)
    body = body.replace("</figcaption>", "</em></p>")
    body = re.sub(r"<section[^>]*>", "<div>", body, flags=re.S)
    body = body.replace("</section>", "</div>")
    body = re.sub(r"<main[^>]*>", "<div>", body, flags=re.S)
    body = body.replace("</main>", "</div>")
    # drop class/style/id attributes; keep semantic elements and images
    body = re.sub(r'\s+(?:class|style|id)="[^"]*"', "", body)
    # tables: give plain border attributes so they render without CSS
    body = body.replace("<table>", '<table border="1" cellpadding="6" cellspacing="0">')
    # no anchors left after nav removal, but strip any remaining href to plain text
    body = re.sub(r'<a[^>]*href="[^"]*"[^>]*>(.*?)</a>', r"\1", body, flags=re.S)
    # remove empty divs left by wrappers
    body = re.sub(r"<div>\s*</div>", "", body)
    forum = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
             "<title>Kev-4B 前后对照评测（论坛副本）</title></head><body>\n"
             "<p><b>论坛友好副本</b>：本页只用基础 HTML 标签与 PNG 图片，不含 CSS/JS/SVG；"
             "若论坛会过滤 data URI 图片，请上传同目录的 kev-forum-figures/*.png 后替换图片链接。</p>\n"
             + body + "\n</body></html>\n")
    out = repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(forum, encoding="utf-8")
    # manifest for uploading PNGs manually when a forum strips data URIs
    captions = [re.sub(r"<[^>]+>", "", x).strip()
                for x in re.findall(r"<figcaption>(.*?)</figcaption>", canonical, flags=re.S)]
    manifest = ["# 论坛图片清单", "",
                "将本目录下的 PNG 上传到论坛（或图床）后，把帖子中的 data URI 图片替换为对应链接。",
                "若论坛保留 data URI 图片，则无需上传。", ""]
    for index, filename in enumerate(png_paths, 1):
        caption = captions[index - 1] if index - 1 < len(captions) else ""
        manifest.append("## " + str(index) + ". " + filename)
        manifest.append("")
        manifest.append("- 文件：" + filename)
        manifest.append("- 图注：" + caption)
        manifest.append("")
    (png_dir / "MANIFEST.md").write_text("\n".join(manifest), encoding="utf-8")

    print("wrote", out, "bytes", len(forum))
    print("png dir", png_dir, "files", len(png_paths))
    print("check: svg", forum.count("<svg"), "style", forum.count("<style"), "script", forum.count("<script"),
          "data-uri imgs", forum.count("data:image/png"), "class attrs", forum.count("class="))
    print("names:", ",".join(FIG_NAMES))


if __name__ == "__main__":
    main()
