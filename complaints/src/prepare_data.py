"""Convert the CFPB bulk download into a compact parquet file used by the notebook and app.

Download first: https://files.consumerfinance.gov/ccdb/complaints.csv.zip -> data/raw/complaints.csv.zip
"""
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data" / "raw" / "complaints.csv.zip"
OUT = ROOT / "data" / "processed" / "complaints_all.parquet"

COLS = ["Date received", "Product", "Sub-product", "Issue", "Sub-issue", "Company", "State", "Submitted via",
        "Date sent to company", "Company response to consumer", "Timely response?", "Complaint ID", "Tags"]
CATEGORICAL = ["Product", "Sub-product", "Issue", "Sub-issue", "Company", "State", "Submitted via",
               "Company response to consumer", "Timely response?", "Tags"]

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z, z.open("complaints.csv") as f:
        d = pd.read_csv(f, usecols=COLS, parse_dates=["Date received", "Date sent to company"],
                        dtype={c: "category" for c in CATEGORICAL})
    d.columns = [c.lower().replace(" ", "_").replace("?", "") for c in d.columns]
    d.to_parquet(OUT)
    print(f"{len(d):,} complaints, {d.date_received.min().date()} to {d.date_received.max().date()} -> {OUT}")
