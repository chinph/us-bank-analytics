"""Credit-risk helpers: cohort prep, WoE scorecard, metrics, profit-based cut-off."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "prosper_loans.csv"
DATA_END = pd.Timestamp("2014-03-10")          # last date in the file
RELAUNCH = pd.Timestamp("2009-07-01")          # Prosper's post-shutdown rating regime starts
SPLITS = {"train": ("2009-07-01", "2011-12-31"),
          "valid": ("2012-01-01", "2012-06-30"),
          "test": ("2012-07-01", "2013-03-10")}

NUMERIC = [
    "Term", "LoanOriginalAmount", "CreditScoreRangeLower", "DebtToIncomeRatio", "StatedMonthlyIncome",
    "EmploymentStatusDuration", "CurrentCreditLines", "OpenCreditLines", "TotalCreditLinespast7years",
    "OpenRevolvingAccounts", "OpenRevolvingMonthlyPayment", "InquiriesLast6Months", "TotalInquiries",
    "CurrentDelinquencies", "AmountDelinquent", "DelinquenciesLast7Years", "PublicRecordsLast10Years",
    "PublicRecordsLast12Months", "RevolvingCreditBalance", "BankcardUtilization", "AvailableBankcardCredit",
    "TotalTrades", "TradesNeverDelinquent (percentage)", "TradesOpenedLast6Months", "ScorexChangeAtTimeOfListing",
    "TotalProsperLoans", "OnTimeProsperPayments", "ProsperPaymentsLessThanOneMonthLate",
    "ProsperPaymentsOneMonthPlusLate", "ProsperPrincipalBorrowed", "ProsperPrincipalOutstanding",
    "credit_history_years", "loan_to_annual_income",
]
CATEGORICAL = ["IncomeRange", "EmploymentStatus", "IsBorrowerHomeowner", "IncomeVerifiable",
               "ListingCategory (numeric)", "CurrentlyInGroup"]
PRIOR_PROSPER = ["TotalProsperLoans", "OnTimeProsperPayments", "ProsperPaymentsLessThanOneMonthLate",
                 "ProsperPaymentsOneMonthPlusLate", "ProsperPrincipalBorrowed", "ProsperPrincipalOutstanding"]
BENCHMARK = "ProsperScore"


def load_cohort(horizon_months=12, path=RAW):
    """Post-relaunch loans with a complete outcome window, one row per listing, with a `bad` target.

    bad = charged off or defaulted within `horizon_months` of origination. Loans originated
    too recently to have had the full window are dropped (right-censoring).
    """
    d = pd.read_csv(path, low_memory=False).drop_duplicates("ListingKey")
    for c in ["LoanOriginationDate", "ClosedDate", "FirstRecordedCreditLine"]:
        d[c] = pd.to_datetime(d[c], format="ISO8601")
    d = d[d.LoanStatus != "Cancelled"]
    last_orig = DATA_END - pd.DateOffset(months=horizon_months)
    d = d[(d.LoanOriginationDate >= RELAUNCH) & (d.LoanOriginationDate <= last_orig)].copy()
    went_bad = d.LoanStatus.isin(["Chargedoff", "Defaulted"])
    within = d.ClosedDate <= d.LoanOriginationDate + pd.DateOffset(months=horizon_months)
    d["bad"] = (went_bad & within).astype(int)
    d["credit_history_years"] = (d.LoanOriginationDate - d.FirstRecordedCreditLine).dt.days / 365.25
    d["loan_to_annual_income"] = d.LoanOriginalAmount / (12 * d.StatedMonthlyIncome.replace(0, np.nan))
    d[PRIOR_PROSPER] = d[PRIOR_PROSPER].fillna(0)
    d["has_prior_prosper"] = (d.TotalProsperLoans > 0).astype(int)
    d["StatedMonthlyIncome"] = d.StatedMonthlyIncome.clip(upper=d.StatedMonthlyIncome.quantile(0.99))
    for c in ["IsBorrowerHomeowner", "IncomeVerifiable", "CurrentlyInGroup"]:
        d[c] = d[c].astype(str)
    d["ListingCategory (numeric)"] = d["ListingCategory (numeric)"].astype(str)
    d["split"] = pd.NA
    for name, (lo, hi) in SPLITS.items():
        d.loc[(d.LoanOriginationDate >= lo) & (d.LoanOriginationDate <= hi), "split"] = name
    return d.dropna(subset=["split"]).reset_index(drop=True)


# ---------- weight of evidence scorecard ----------
class WoEBinner:
    """Quantile-bin numeric features, group categoricals, and map each bin to its weight of evidence."""

    def __init__(self, numeric, categorical, n_bins=8, smooth=0.5):
        self.numeric, self.categorical, self.n_bins, self.smooth = numeric, categorical, n_bins, smooth

    def _bin(self, s, col):
        if col in self.edges:
            b = pd.cut(s, self.edges[col], labels=False, include_lowest=True)
            return b.astype("float").fillna(-1).astype(int).astype(str).replace("-1", "missing")
        return s.fillna("missing").astype(str)

    def bin_label(self, col, b):
        """Readable label for a bin index, e.g. '(660, 700]'."""
        if col not in self.edges or b == "missing":
            return b
        i, e = int(b), self.edges[col]
        lo = "min" if np.isinf(e[i]) else f"{e[i]:,.4g}"
        hi = "max" if np.isinf(e[i + 1]) else f"{e[i + 1]:,.4g}"
        return f"({lo}, {hi}]"

    def fit(self, X, y):
        self.edges, self.woe, self.iv = {}, {}, {}
        for c in self.numeric:
            q = np.unique(X[c].quantile(np.linspace(0, 1, self.n_bins + 1)).dropna().values)
            if len(q) > 2:
                q[0], q[-1] = -np.inf, np.inf
                self.edges[c] = q
        good, bad = (y == 0).sum(), (y == 1).sum()
        for c in self.numeric + self.categorical:
            b = self._bin(X[c], c)
            t = pd.crosstab(b, y).reindex(columns=[0, 1], fill_value=0)
            g, bd = t[0] + self.smooth, t[1] + self.smooth
            woe = np.log((g / good) / (bd / bad))
            self.woe[c] = woe.to_dict()
            self.iv[c] = float(((g / good - bd / bad) * woe).sum())
        return self

    def transform(self, X, cols=None):
        cols = cols or self.numeric + self.categorical
        out = pd.DataFrame(index=X.index)
        for c in cols:
            out[c] = self._bin(X[c], c).map(self.woe[c]).fillna(0.0)
        return out


class Scorecard:
    """WoE logistic regression exposed as points (higher = safer)."""

    def __init__(self, numeric, categorical, min_iv=0.02, C=0.05, base_score=600, base_odds=20, pdo=40):
        self.binner = WoEBinner(numeric, categorical)
        self.min_iv, self.C = min_iv, C
        self.factor, self.offset = pdo / np.log(2), base_score - pdo / np.log(2) * np.log(base_odds)

    def fit(self, X, y):
        self.binner.fit(X, y)
        self.cols = [c for c, v in self.binner.iv.items() if v >= self.min_iv]
        self.lr = LogisticRegression(C=self.C, max_iter=2000)
        self.lr.fit(self.binner.transform(X, self.cols), y)
        return self

    def predict_proba_bad(self, X):
        return self.lr.predict_proba(self.binner.transform(X, self.cols))[:, 1]

    def score(self, X):
        """Points: log(good/bad odds) scaled so +pdo points doubles the odds."""
        p = np.clip(self.predict_proba_bad(X), 1e-6, 1 - 1e-6)
        return self.offset + self.factor * np.log((1 - p) / p)

    def reason_codes(self, X, top=3):
        """For each row, the features that pull the score down most (per-feature contribution)."""
        W = self.binner.transform(X, self.cols)
        contrib = W * (-self.lr.coef_[0])          # positive = pushes toward bad
        return contrib.apply(lambda r: r.nlargest(top).index.tolist(), axis=1)


# ---------- boosted model ----------
def gbm_matrix(d, levels):
    """Numeric features plus integer-coded categoricals (levels fixed from the full cohort)."""
    z = d[NUMERIC].copy()
    for c in CATEGORICAL:
        z[c] = pd.Categorical(d[c], categories=levels[c]).codes
    return z


def fit_gbm(d, y, seed=0, **kw):
    from sklearn.ensemble import HistGradientBoostingClassifier
    levels = {c: sorted(d[c].unique()) for c in CATEGORICAL}
    params = dict(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0,
                  early_stopping=False, random_state=seed,
                  categorical_features=list(range(len(NUMERIC), len(NUMERIC) + len(CATEGORICAL))))
    params.update(kw)
    return HistGradientBoostingClassifier(**params).fit(gbm_matrix(d, levels), y), levels


# ---------- metrics ----------
def ks(y, p):
    d = pd.DataFrame({"y": y, "p": p}).sort_values("p", ascending=False)
    cb, cg = (d.y == 1).cumsum() / (d.y == 1).sum(), (d.y == 0).cumsum() / (d.y == 0).sum()
    return float((cb - cg).abs().max())


def evaluate(y, p):
    return {"auc": roc_auc_score(y, p), "ks": ks(y, p), "brier": brier_score_loss(y, p),
            "mean_pred": float(np.mean(p)), "actual": float(np.mean(y))}


def calibration_table(y, p, bins=10):
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["bin"] = pd.qcut(d.p, bins, duplicates="drop")
    return d.groupby("bin", observed=True).agg(predicted=("p", "mean"), actual=("y", "mean"), n=("y", "size")).reset_index(drop=True)


def psi(expected, actual, bins=10):
    """Population stability index of a score between two samples (< 0.1 stable, > 0.25 shifted)."""
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, 1e-4, None), np.clip(a, 1e-4, None)
    return float(((a - e) * np.log(a / e)).sum())


# ---------- cost-based cut-off ----------
def profit_curve(p_bad, y, amount, gain, loss, n_points=101):
    """Realized profit per $ lent when approving the safest `share` of loans (ranked by predicted risk)."""
    order = np.argsort(p_bad)
    y, amount = np.asarray(y)[order], np.asarray(amount)[order]
    pnl = amount * np.where(y == 1, -loss, gain)
    shares = np.linspace(0.0, 1.0, n_points)
    rows = []
    for s in shares:
        k = int(round(s * len(y)))
        lent = amount[:k].sum()
        rows.append({"approve_share": s, "profit": pnl[:k].sum(),
                     "profit_per_dollar": pnl[:k].sum() / lent if lent else np.nan,
                     "bad_rate": y[:k].mean() if k else np.nan})
    return pd.DataFrame(rows)


def loss_given_default(d):
    """Mean net principal loss per $ among bad loans (measured, not assumed)."""
    b = d[d.bad == 1]
    return float((b["LP_NetPrincipalLoss"] / b["LoanOriginalAmount"]).mean())
