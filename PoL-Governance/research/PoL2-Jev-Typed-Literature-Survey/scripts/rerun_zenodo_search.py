"""Re-run the documented Zenodo queries (paper Appendix E) and list records not yet screened.

Writes data/search_rerun_zenodo_<date>.csv with every record published on/after the Jev release
that is not in data/zenodo_preprints.csv, so that new candidates can be screened by title/description.
Run: python scripts/rerun_zenodo_search.py
"""
import csv
import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026-09-15"
QUERIES = [
    '"Jev" AND (TypeSafe OR decision OR "System One")', '"System One model"', '"typed decision"',
    '"calibrated decisions"', 'RLCD', 'title:Jev', 'title:JEV', 'description:"TypeSafe"',
    '"Jev" AND (calibration OR typed OR noul)', 'Laya AND "decision model"',
    '"System One" AND (typed OR calibrated) AND decision',
]


def fetch(q, page):
    url = "https://zenodo.org/api/records?" + urllib.parse.urlencode(
        {"q": q, "size": 25, "page": page, "sort": "mostrecent"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 5:
                raise
            time.sleep(20 * (attempt + 1))


def main():
    known = {re.sub(r"\D", "", row["id"]) for row in csv.DictReader(open(ROOT / "data" / "zenodo_preprints.csv", encoding="utf-8"))}
    known |= {re.sub(r"\D", "", row["id"]) for row in csv.DictReader(open(ROOT / "data" / "excluded_records.csv", encoding="utf-8"))
              if row["source"].lower().startswith("zen")}
    seen, total = {}, 0
    for q in QUERIES:
        page = 1
        while True:
            hits = fetch(q, page)["hits"]["hits"]
            total += len(hits)
            stop = False
            for h in hits:
                md = h["metadata"]
                pub = md.get("publication_date", "")[:10]
                if pub < RELEASE:
                    stop = True
                    continue
                rid = str(h["id"])
                if rid in seen:
                    seen[rid]["queries"] += f"; {q}"
                    continue
                desc = re.sub(r"<[^>]+>", " ", md.get("description", ""))
                seen[rid] = {"zenodo_id": rid, "published": pub, "queries": q,
                             "concept_id": str(h.get("conceptrecid", "")),
                             "type": md.get("resource_type", {}).get("type", ""),
                             "title": " ".join(md.get("title", "").split()),
                             "description": " ".join(desc.split())[:1500]}
            if stop or len(hits) < 25:
                break
            page += 1
            time.sleep(2)
        time.sleep(2)
    rows = sorted((r for rid, r in seen.items() if rid not in known and r["concept_id"] not in known),
                  key=lambda r: r["published"])
    out = ROOT / "data" / f"search_rerun_zenodo_{dt.date.today().isoformat()}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["zenodo_id", "concept_id", "published", "type", "queries", "title", "description"])
        w.writeheader()
        w.writerows(rows)
    print(f"{total} hits, {len(seen)} unique on/after {RELEASE}, {len(rows)} not yet screened -> {out.name}")


if __name__ == "__main__":
    main()
