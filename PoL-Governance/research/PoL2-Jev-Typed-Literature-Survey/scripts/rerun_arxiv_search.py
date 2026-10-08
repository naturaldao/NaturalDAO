"""Re-run the documented arXiv queries (paper Appendix D) and list records not yet screened.

Writes data/search_rerun_<date>.csv with every record dated on/after the Jev release that is not in
data/papers.csv, so that new candidates can be screened by title/abstract.
Run: python scripts/rerun_arxiv_search.py
"""
import csv
import datetime as dt
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026-09-15"
QUERIES = [
    'all:Jev', 'abs:"typed decision"', 'abs:"System One"', 'abs:RLCD', 'abs:"calibrated decisions"',
    'abs:"typed answers"', 'abs:"TypeSafe"', 'abs:"decision model" AND abs:typed', 'abs:"System One model"',
    'abs:"System-One"', 'abs:"direct-decision"', 'abs:Laya AND abs:decision', 'abs:"typed probabilistic"',
    'abs:"decision model" AND abs:calibrated', 'abs:"this-that"', 'abs:"Reinforcement Learning for Calibrated"',
    'abs:"typed decisions"', 'abs:"single-pass decision"',
]
NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch(q):
    url = ("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "start": 0, "max_results": 200, "sortBy": "submittedDate", "sortOrder": "descending"}))
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PoL2-Jev-survey/0.3 (mailto:[email])"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return ET.fromstring(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 5:
                raise
            time.sleep(20 * (attempt + 1))  # arXiv API asks clients to back off


def main():
    known = {row["arxiv_id"] for row in csv.DictReader(open(ROOT / "data" / "papers.csv", encoding="utf-8"))}
    excluded = {"2609.35039"}
    seen, rows, total = {}, [], 0
    for q in QUERIES:
        feed = fetch(q)
        entries = feed.findall("a:entry", NS)
        total += len(entries)
        for e in entries:
            aid = re.sub(r"v\d+$", "", e.find("a:id", NS).text.rsplit("/", 1)[-1])
            pub = e.find("a:published", NS).text[:10]
            if aid in seen:
                seen[aid]["queries"] += f"; {q}"
                continue
            seen[aid] = {"arxiv_id": aid, "published": pub, "queries": q,
                         "title": " ".join(e.find("a:title", NS).text.split()),
                         "abstract": " ".join(e.find("a:summary", NS).text.split())}
        time.sleep(5)
    for aid, r in seen.items():
        if r["published"] >= RELEASE and aid not in known and aid not in excluded:
            rows.append(r)
    rows.sort(key=lambda r: r["published"])
    out = ROOT / "data" / f"search_rerun_{dt.date.today().isoformat()}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["arxiv_id", "published", "queries", "title", "abstract"])
        w.writeheader()
        w.writerows(rows)
    after = sum(1 for r in seen.values() if r["published"] >= RELEASE)
    print(f"records {total}, unique {len(seen)}, on/after release {after}, not yet in corpus {len(rows)} -> {out}")
    for r in rows:
        print(r["published"], r["arxiv_id"], r["title"][:110])


if __name__ == "__main__":
    main()
