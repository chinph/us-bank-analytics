"""Collect the most recent App Store reviews (US storefront) for a set of bank and payment apps.

Source: Apple's public customer-review feed (up to 10 pages of 50 reviews per app). Reviewer names, ids and profile
links are dropped at ingestion and never written to disk. Requests are spaced and retried with backoff.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "reviews.csv"
UA = "research-script (portfolio analysis)"

APPS = {  # App Store id: (name, group)
    298867247: ("Chase", "Banks & credit unions"), 284847138: ("Bank of America", "Banks & credit unions"),
    311548709: ("Wells Fargo", "Banks & credit unions"), 301724680: ("Citi", "Banks & credit unions"),
    407558537: ("Capital One", "Banks & credit unions"), 458734623: ("U.S. Bank", "Banks & credit unions"),
    303113127: ("PNC", "Banks & credit unions"), 1555389200: ("Truist", "Banks & credit unions"),
    370811491: ("Navy Federal", "Banks & credit unions"),
    362348516: ("American Express", "Card issuers"), 338010821: ("Discover", "Card issuers"),
    836215269: ("Chime", "Fintech & digital banks"), 711923939: ("Cash App", "Fintech & digital banks"),
    283646709: ("PayPal", "Fintech & digital banks"), 351727428: ("Venmo", "Fintech & digital banks"),
    1191985736: ("SoFi", "Fintech & digital banks"), 514374715: ("Ally", "Fintech & digital banks"),
}


def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):          # past the last available page
                return None
            time.sleep(2 ** i)
        except Exception:
            time.sleep(2 ** i)
    return None


def collect(pages=10, delay=1.5):
    rows, seen = [], set()
    for app_id, (name, group) in APPS.items():
        n_app = 0
        for page in range(1, pages + 1):
            d = fetch(f"https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json")
            time.sleep(delay)
            entries = (d or {}).get("feed", {}).get("entry", []) if d else []
            if isinstance(entries, dict):
                entries = [entries]
            reviews = [e for e in entries if "im:rating" in e]
            if not reviews:
                break
            for e in reviews:
                key = (app_id, e["id"]["label"])                  # review id used only to drop duplicates, never stored
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"app_id": app_id, "app": name, "group": group, "rating": int(e["im:rating"]["label"]),
                             "title": e["title"]["label"], "text": e["content"]["label"],
                             "version": e.get("im:version", {}).get("label"), "date": e["updated"]["label"][:10]})
                n_app += 1
        print(f"{name}: {n_app} reviews")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = collect()
    df.to_csv(OUT, index=False)
    print(f"{len(df):,} reviews -> {OUT}")
