"""Helpers for the scam-losses analysis: FTC tables, population, tail bounds, funnel limits, friction break-even."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
CFPB = ROOT.parent / "complaints" / "data" / "processed" / "complaints_all.parquet"


def load_ftc():
    return {n: pd.read_csv(PROC / f"ftc_{n}.csv") for n in ["totals", "loss_buckets", "payment_method", "contact_method"]}


def population():
    """US resident population, July 1 estimates (Census Bureau; Vintage 2019 for 2019, Vintage 2024 for 2020 to 2024)."""
    a = pd.read_excel(RAW / "census_2010_2019.xlsx", header=None)
    b = pd.read_excel(RAW / "census_2020_2024.xlsx", header=None)
    old = dict(zip(a.iloc[3, 3:].astype(float).astype(int), a.iloc[4, 3:].astype(float)))
    new = dict(zip(b.iloc[3, 2:].astype(float).astype(int), b.iloc[4, 2:].astype(float)))
    pop = {2019: old[2019], **new}
    return pd.Series(pop, name="population").astype(int)


def tail_share_lower_bound(buckets, total_loss):
    """Lower bound on the share of dollars from reports above $10,000.

    The reports in the lower bands cannot have lost more than their band's upper limit, so the top band holds at least
    total - sum(count x upper limit of the other bands).
    """
    out = {}
    for year, g in buckets.groupby("year"):
        low = g[g.high.notna()]
        upper = float((low.reports * low.high).sum())
        out[year] = max(0.0, 1 - upper / total_loss.loc[year])
    return pd.Series(out, name="top_band_dollar_share_lower_bound")


def wilson(k, n, z=1.96):
    """Wilson score interval for a proportion."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return c - h, c + h


def funnel_limits(p0, n, z):
    """Control limits for a rate p0 observed over n cases (normal approximation)."""
    se = np.sqrt(p0 * (1 - p0) / n)
    return np.clip(p0 - z * se, 0, 1), np.clip(p0 + z * se, 0, 1)


def breakeven_probability(loss, effectiveness, cost, bank_share):
    """Scam probability among flagged payments above which friction pays for itself.

    benefit per flagged payment = p x loss x bank_share x effectiveness; cost = `cost`. Solve benefit = cost.
    """
    return cost / (loss * bank_share * effectiveness)
