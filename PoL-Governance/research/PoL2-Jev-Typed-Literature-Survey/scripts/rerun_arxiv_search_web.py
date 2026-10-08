"""Fallback for rerun_arxiv_search.py when the arXiv API rate-limits (HTTP 429).

Runs the same 18 queries through arXiv's advanced-search web interface (arxiv.org/search/advanced),
restricted to submissions dated on/after the Jev release, and writes data/search_rerun_<date>.csv in the
same format (arxiv_id, published, queries, title, abstract). "published" is the first-submission date
(v1) shown on the listing.
Run: python scripts/rerun_arxiv_search_web.py
"""
import csv
import datetime as dt
import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rerun_arxiv_search import QUERIES, RELEASE, ROOT  # noqa: E402

FIELD = {"all": "all", "abs": "abstract"}
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}


def terms(q):
    """'abs:"typed decision" AND abs:typed' -> [("abstract", '"typed decision"'), ("abstract", "typed")]"""
    return [(FIELD[f], t) for f, t in re.findall(r'(all|abs):("[^"]+"|\S+)', q)]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PoL2-Jev-survey update search)"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 5:
                raise
            time.sleep(30 * (attempt + 1))


def search(q):
    params = {"advanced": "1", "abstracts": "show", "size": "200", "order": "-announced_date_first",
              "date-filter_by": "date_range", "date-from_date": RELEASE, "date-to_date": "",
              "date-date_type": "submitted_date_first", "classification-include_cross_list": "include"}
    for i, (field, term) in enumerate(terms(q)):
        params.update({f"terms-{i}-operator": "AND", f"terms-{i}-term": term, f"terms-{i}-field": field})
    page = get("https://arxiv.org/search/advanced?" + urllib.parse.urlencode(params))
    out = []
    for item in page.split('<li class="arxiv-result">')[1:]:
        aid = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", item).group(1)
        title = re.search(r'<p class="title is-5 mathjax">(.*?)</p>', item, re.S).group(1)
        abstract = re.search(r'<span class="abstract-full[^>]*>(.*?)<a', item, re.S)
        sub = re.search(r"originally announced|Submitted</span>\s*([0-9]{1,2}) (\w+), ([0-9]{4})", item)
        v1 = re.search(r"v1</span> submitted ([0-9]{1,2}) (\w+), ([0-9]{4})", item) or sub
        d = dt.date(int(v1.group(3)), MONTHS[v1.group(2)], int(v1.group(1))).isoformat() if v1 and v1.group(1) else ""
        clean = lambda s: " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())
        out.append({"arxiv_id": aid, "published": d, "title": clean(title),
                    "abstract": clean(abstract.group(1)) if abstract else ""})
    return out


def main():
    known = {row["arxiv_id"] for row in csv.DictReader(open(ROOT / "data" / "papers.csv", encoding="utf-8"))}
    excluded = {"2609.35039"}
    seen = {}
    for q in QUERIES:
        hits = search(q)
        print(f"{len(hits):4d}  {q}")
        for r in hits:
            if r["arxiv_id"] in seen:
                seen[r["arxiv_id"]]["queries"] += f"; {q}"
            else:
                seen[r["arxiv_id"]] = {**r, "queries": q}
        time.sleep(5)
    rows = sorted((r for a, r in seen.items() if r["published"] >= RELEASE and a not in known and a not in excluded),
                  key=lambda r: r["published"])
    out = ROOT / "data" / f"search_rerun_{dt.date.today().isoformat()}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["arxiv_id", "published", "queries", "title", "abstract"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(seen)} unique, {len(rows)} not yet screened -> {out.name}")


if __name__ == "__main__":
    main()
