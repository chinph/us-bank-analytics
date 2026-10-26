"""Load, tag and summarize the app reviews; small stats helpers."""
from pathlib import Path

import numpy as np
import pandas as pd

import themes

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "reviews.csv"
PROC = ROOT / "data" / "processed"
PROBLEM = [t for t in themes.THEME_NAMES if t != "Praise & ease of use"]
SHORT = {"Login & authentication": "Login", "Bugs, crashes & slowness": "Bugs & slowness", "Fraud, scams & security": "Fraud & security",
         "Frozen, closed or restricted accounts": "Frozen / closed accounts", "Customer service & support": "Customer service",
         "Fees & charges": "Fees & charges", "Payments, transfers & deposits": "Payments & transfers", "Updates, design & features": "Updates & design",
         "Praise & ease of use": "Praise"}


def load(min_words=4):
    """Reviews with at least `min_words` words (title + text), tagged with themes. Adds `low` (1 or 2 stars)."""
    d = pd.read_csv(RAW, parse_dates=["date"])
    d["words"] = (d.title.fillna("") + " " + d.text.fillna("")).str.split().str.len()
    d = d[d.words >= min_words].reset_index(drop=True)
    d["low"] = d.rating <= 2
    return d.join(themes.tag_frame(d))


def wilson(k, n, z=1.96):
    """Wilson score interval for a proportion."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return c - h, c + h


def prevalence(df, by, cols=PROBLEM):
    """Share of reviews with each theme, per group, with Wilson intervals. Returns a long frame."""
    rows = []
    for key, g in df.groupby(by):
        for c in cols:
            k, n = int(g[c].sum()), len(g)
            lo, hi = wilson(k, n)
            rows.append({by: key, "theme": c, "n": n, "count": k, "share": k / n, "lo": lo, "hi": hi})
    return pd.DataFrame(rows)
