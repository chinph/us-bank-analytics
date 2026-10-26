"""Complaint monitor: weekly stream counts, alert detectors, surge-injection back-test, alert triage."""
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parents[1]
ALL = ROOT / "data" / "processed" / "complaints_all.parquet"
LAST_COMPLETE_WEEK = pd.Timestamp("2026-10-05")   # week starting Monday; weeks after this are incomplete (publication lag)
WINDOW = 26                                       # baseline length in weeks
GROUPS = {
    "Checking or savings account": "Checking & savings", "Bank account or service": "Checking & savings",
    "Credit card": "Credit & prepaid cards", "Credit card or prepaid card": "Credit & prepaid cards", "Prepaid card": "Credit & prepaid cards",
    "Mortgage": "Mortgage",
    "Money transfer, virtual currency, or money service": "Money transfer & wallets", "Money transfers": "Money transfer & wallets",
    "Vehicle loan or lease": "Vehicle loans",
    "Payday loan, title loan, personal loan, or advance loan": "Personal loans",
    "Payday loan, title loan, or personal loan": "Personal loans", "Consumer Loan": "Personal loans",
}
BUREAUS = ("EQUIFAX", "TRANSUNION", "EXPERIAN")
MIN_STREAM_TOTAL = 500


def load_scoped(path=ALL):
    """Complaints in scope: bank-product groups, 2018 onward, complete weeks, no credit bureaus."""
    d = pd.read_parquet(path)
    d["pg"] = d["product"].map(GROUPS)
    d = d[d.pg.notna() & (d.date_received >= "2018-01-01")].copy()
    d["company"] = d.company.astype(str)
    d = d[~d.company.str.upper().str.startswith(BUREAUS)]
    d["week"] = d.date_received.dt.to_period("W-SUN").dt.start_time
    return d[d.week <= LAST_COMPLETE_WEEK].reset_index(drop=True)


def weekly_streams(d, min_total=MIN_STREAM_TOTAL):
    """Matrix of weekly counts: rows = company x product group streams, columns = weeks."""
    c = d.groupby(["company", "pg", "week"]).size().unstack("week", fill_value=0)
    c = c.loc[c.sum(axis=1) >= min_total]
    weeks = pd.date_range(d.week.min(), LAST_COMPLETE_WEEK, freq="W-MON")
    return c.reindex(columns=weeks, fill_value=0)


# ---------- detectors ----------
def detect_clean(X, k, min_excess=5.0, window=WINDOW):
    """Robust rule with an alert-aware baseline.

    Weeks that alert enter the history capped at the alert threshold, so one huge spike cannot
    inflate the baseline for the next `window` weeks. A persistent real level shift still
    raises the baseline slowly (capped weeks sit just above it), so it is not alerted on forever.
    Returns (alert matrix, threshold matrix).
    """
    X = X.astype(float)
    S, T = X.shape
    H = X.copy()
    alert = np.zeros((S, T), bool)
    thr = np.full((S, T), np.nan)
    for t in range(window, T):
        w = H[:, t - window: t]
        med = np.median(w, axis=1)
        mad = np.median(np.abs(w - med[:, None]), axis=1)
        sigma = np.maximum(1.4826 * mad, np.sqrt(np.maximum(med, 1.0)))
        thr[:, t] = med + k * sigma
        a = (X[:, t] > thr[:, t]) & (X[:, t] - med >= min_excess)
        alert[:, t] = a
        H[:, t] = np.where(a, np.minimum(X[:, t], thr[:, t]), X[:, t])
    return alert, thr



def baselines(X, window=WINDOW):
    """Per stream-week baseline from the previous `window` weeks (current week excluded).

    Returns arrays aligned to X's columns (NaN for the first `window` weeks).
    """
    S, T = X.shape
    out = {k: np.full((S, T), np.nan) for k in ["median", "mean", "std", "sigma"]}
    win = sliding_window_view(X.astype(float), window, axis=1)[:, :-1]          # windows ending the week before t
    med = np.median(win, axis=2)
    mad = np.median(np.abs(win - med[:, :, None]), axis=2)
    out["median"][:, window:] = med
    out["mean"][:, window:] = win.mean(axis=2)
    out["std"][:, window:] = win.std(axis=2, ddof=1)
    # robust spread, never below the Poisson floor sqrt(median) (so a MAD of zero cannot make a tiny stream hair-trigger)
    out["sigma"][:, window:] = np.maximum(1.4826 * mad, np.sqrt(np.maximum(med, 1.0)))
    return out


def detect(X, method, k, min_excess=5.0, cusum_slack=0.5, base=None):
    """Boolean alert matrix and the score used. `k` is the threshold on the method's own scale."""
    b = base if base is not None else baselines(X)
    X = X.astype(float)
    if method == "static":
        score = X
        alert = X >= k
    elif method == "mean_sd":
        score = (X - b["mean"]) / np.maximum(b["std"], 1.0)
        alert = (score > k) & (X - b["mean"] >= min_excess)
    elif method == "robust":
        score = (X - b["median"]) / b["sigma"]
        alert = (score > k) & (X - b["median"] >= min_excess)
    elif method == "robust_clean":
        alert, thr = detect_clean(X, k, min_excess=min_excess)
        return alert, X - thr
    elif method == "cusum":
        r = (X - b["median"]) / b["sigma"]
        r = np.where(np.isnan(r), 0.0, r)
        s = np.zeros_like(r)
        for t in range(1, X.shape[1]):
            s[:, t] = np.maximum(0.0, s[:, t - 1] + np.clip(r[:, t], None, 10) - cusum_slack)   # clip: one huge week must not dominate
        score = s
        alert = (s > k) & (X - b["median"] >= min_excess)
    else:
        raise ValueError(method)
    alert = alert & ~np.isnan(score)
    return alert, score


def calibrate(X, method, target_per_week, grid, weeks_mask, **kw):
    """Smallest threshold from `grid` whose alert rate on real history is at or below the target."""
    base = baselines(X)
    for k in sorted(grid):
        a, _ = detect(X, method, k, base=base, **kw)
        if a[:, weeks_mask].sum(axis=0).mean() <= target_per_week:
            return k, a[:, weeks_mask].sum(axis=0).mean()
    return grid[-1], np.nan


# ---------- surge injection back-test ----------
def volume_bucket(baseline_median):
    return pd.cut(baseline_median, [-1, 5, 20, 100, 1e9], labels=["<5/wk", "5-20/wk", "20-100/wk", ">100/wk"])


def injection_test(X, week_idx, methods, mult, length, n_per_bucket=300, seed=0, horizon=4, min_excess=5.0):
    """Inject a surge of `mult` x baseline for `length` weeks into quiet stream-weeks; measure detection.

    methods: {name: (method, k)}. Detection = first alert within `horizon` weeks of surge onset.
    Returns a DataFrame with one row per (bucket, method): detection rate and median delay in weeks.
    """
    rng = np.random.default_rng(seed)
    b = baselines(X)
    S, T = X.shape
    robust_z = (X - b["median"]) / b["sigma"]
    cands = []
    for s in range(S):
        for t in week_idx:
            if t + length + horizon + 6 > T or t - WINDOW < 0:
                continue
            seg = robust_z[s, t - WINDOW: t + length + horizon + 6]
            if np.nanmax(seg) < 3.0:                       # keep only quiet stretches
                cands.append((s, t))
    cands = np.array(cands)
    med = b["median"][cands[:, 0], cands[:, 1]]
    bucket = volume_bucket(med)
    rows = []
    span = WINDOW + length + horizon + 6
    for name in bucket.categories:
        pool = cands[bucket == name]
        if len(pool) == 0:
            continue
        pick = pool[rng.choice(len(pool), min(n_per_bucket, len(pool)), replace=False)]
        series = np.stack([X[s, t - WINDOW: t - WINDOW + span].astype(float) for s, t in pick])
        base_level = np.maximum(b["median"][pick[:, 0], pick[:, 1]], 1.0)
        extra = rng.poisson((mult - 1.0) * base_level[:, None] * np.ones((1, length)))
        series[:, WINDOW: WINDOW + length] += extra
        for mname, (method, k) in methods.items():
            a, _ = detect(series, method, k, min_excess=min_excess)
            # a detection is a NEW alert episode starting in the window; a stream already in alert gives no new notification
            starts = a & ~np.concatenate([np.zeros((a.shape[0], 1), bool), a[:, :-1]], axis=1)
            hit = starts[:, WINDOW: WINDOW + horizon]
            detected = hit.any(axis=1)
            delay = np.where(detected, hit.argmax(axis=1), np.nan)
            rows.append({"bucket": name, "method": mname, "n": len(pick), "detect_rate": detected.mean(),
                         "median_delay_wk": np.nanmedian(delay) if detected.any() else np.nan})
    return pd.DataFrame(rows)


# ---------- triage ----------
def classify_alerts(X, alert, base, weeks, persist_k=1.5):
    """List alerts with severity and whether they persist (sustained) or fade (burst)."""
    S, T = X.shape
    idx = np.argwhere(alert)
    rows = []
    for s, t in idx:
        later = X[s, t + 1: t + 4] if t + 4 <= T else None
        sustained = None
        if later is not None and len(later) == 3:
            thr = base["median"][s, t] + persist_k * base["sigma"][s, t]
            sustained = bool((later >= thr).sum() >= 2)
        rows.append({"stream": s, "week": weeks[t], "count": int(X[s, t]), "baseline": base["median"][s, t],
                     "z": (X[s, t] - base["median"][s, t]) / base["sigma"][s, t], "sustained": sustained})
    return pd.DataFrame(rows)


def triage_card(d, company, pg, week):
    """Who and what is behind an alert: issue concentration, channel mix, geography."""
    w = d[(d.company == company) & (d.pg == pg) & (d.week == pd.Timestamp(week))]
    if w.empty:
        return {}
    top_issue = w.issue.value_counts()
    return {"complaints": len(w), "top_issue": str(top_issue.index[0]), "top_issue_share": top_issue.iloc[0] / len(w),
            "web_share": float((w.submitted_via == "Web").mean()), "top_state": str(w.state.value_counts().index[0]),
            "top_state_share": float(w.state.value_counts().iloc[0] / len(w))}
