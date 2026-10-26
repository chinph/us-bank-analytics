"""Parse the FTC Consumer Sentinel Data Book PDFs (2019 to 2024) into tidy tables.

The FTC publishes these figures only as PDF tables and an interactive dashboard (no record-level or CSV download),
so the numbers are extracted from page 11 (amount lost), page 12 (payment method) and page 13 (contact method).
"""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
NUM = r"[\d,]+"


def _page(year, n):
    with pdfplumber.open(RAW / f"csn_{year}.pdf") as pdf:
        return pdf.pages[n - 1].extract_text() or ""


def fraud_totals(year):
    """Total fraud reports, reports with a loss, total dollars lost, median loss."""
    t = _page(year, 11)
    reports, with_loss = re.search(rf"^({NUM}) ({NUM}) \((\d+)%\)", t, re.M).group(1, 2)
    total, median = re.search(r"^\$([\d,]+) \$([\d,]+)", t, re.M).group(1, 2)
    return {"year": year, "fraud_reports": int(reports.replace(",", "")), "reports_with_loss": int(with_loss.replace(",", "")),
            "total_loss": int(total.replace(",", "")), "median_loss": int(median.replace(",", ""))}


def loss_buckets(year):
    """Number of loss reports in each dollar band ($1-$1,000, ..., more than $10,000)."""
    t = _page(year, 11).split("Reported Fraud Losses in $1 - $1,000 Range")[0]
    rows = []
    for lo, hi, n in re.findall(rf"\$({NUM}) - \$({NUM}) ({NUM})$", t, re.M):
        rows.append({"year": year, "low": int(lo.replace(",", "")), "high": int(hi.replace(",", "")), "reports": int(n.replace(",", ""))})
    m = re.search(rf"More than \$10,000 ({NUM})", t)
    rows.append({"year": year, "low": 10_000, "high": None, "reports": int(m.group(1).replace(",", ""))})
    return rows


def payment_methods(year):
    """Reports and total dollars lost by payment method (table on page 12)."""
    t = _page(year, 12).replace("Bank Transfer or\n", "Bank Transfer or Payment ").replace("\nPayment\n", "\n")
    rows = []
    for name, n, loss in re.findall(rf"^([A-Za-z\\ /]+?)\s?({NUM}) \$({NUM})M$", t, re.M):
        rows.append({"year": year, "method": name.strip(), "reports": int(n.replace(",", "")), "total_loss_musd": int(loss.replace(",", ""))})
    return rows


def contact_methods(year):
    """Reports, total dollars lost and median loss by contact method (table on page 13)."""
    t = _page(year, 13)
    rows = []
    for name, n, loss, med in re.findall(rf"^([A-Za-z\\ /-]+?)\s?({NUM}) \$({NUM})M\s?\$({NUM})$", t, re.M):
        rows.append({"year": year, "method": name.strip(), "reports": int(n.replace(",", "")), "total_loss_musd": int(loss.replace(",", "")),
                     "median_loss": int(med.replace(",", ""))})
    return rows


def build_all():
    totals = pd.DataFrame([fraud_totals(y) for y in YEARS])
    buckets = pd.DataFrame([r for y in YEARS for r in loss_buckets(y)])
    pay = pd.DataFrame([r for y in YEARS for r in payment_methods(y)])
    contact = pd.DataFrame([r for y in YEARS for r in contact_methods(y)])
    return totals, buckets, pay, contact


if __name__ == "__main__":
    out = ROOT / "data" / "processed"
    out.mkdir(parents=True, exist_ok=True)
    for name, df in zip(["ftc_totals", "ftc_loss_buckets", "ftc_payment_method", "ftc_contact_method"], build_all()):
        df.to_csv(out / f"{name}.csv", index=False)
        print(name, df.shape)
