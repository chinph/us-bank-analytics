"""Complaint monitor: weekly alert list with adjustable sensitivity, and a per-stream threshold chart."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import monitor as mo  # noqa: E402

st.set_page_config(page_title="Complaint monitor", layout="wide")


@st.cache_data
def load():
    long = pd.read_csv(ROOT / "data" / "processed" / "weekly_streams.csv.gz", parse_dates=["week"])
    tri = pd.read_csv(ROOT / "data" / "processed" / "triage.csv.gz", parse_dates=["week"])
    X = long.pivot_table(index=["company", "product_group"], columns="week", values="complaints", fill_value=0)
    return X, tri


@st.cache_data
def run(k, min_excess):
    X, _ = load()
    alert, thr = mo.detect_clean(X.values, k, min_excess=min_excess)
    return alert, thr


X, tri = load()
weeks = list(X.columns)
V = X.values

st.title("Which complaint streams need escalating this week?")
st.caption("CFPB Consumer Complaint Database, bank product groups, weekly complaints by company and product group. "
           "Unverified consumer reports: an alert is a reason to look, not a finding.")

st.sidebar.header("Alert rule")
k = st.sidebar.slider("Sensitivity: robust standard deviations above normal", 1.5, 6.0, 2.5, 0.1,
                      help="Lower = more alerts. 2.5 gives about 6 new episodes a week on 2023 to 2026 history.")
min_excess = st.sidebar.slider("Minimum complaints above normal", 1, 30, 5)
capacity = st.sidebar.number_input("Review capacity (alerts per week)", 1, 50, 10)
alert, thr = run(k, float(min_excess))
base = mo.baselines(V)

new = alert & ~np.concatenate([np.zeros((alert.shape[0], 1), bool), alert[:, :-1]], axis=1)
per_week = new.sum(0)
last52 = per_week[-52:]

week = st.select_slider("Week starting", options=weeks, value=weeks[-1], format_func=lambda w: w.strftime("%Y-%m-%d"))
t = weeks.index(week)

c1, c2, c3 = st.columns(3)
c1.metric("Alerts this week", int(alert[:, t].sum()), f"{int(new[:, t].sum())} new")
c2.metric("New episodes per week, last 52 weeks", f"{last52.mean():.1f}", f"90th percentile {np.percentile(last52, 90):.0f}", delta_color="off")
c3.metric("Weeks over your capacity (last 52)", f"{int((last52 > capacity).sum())} of 52")

idx = np.where(alert[:, t])[0]
rows = []
for s in idx:
    company, pg = X.index[s]
    rows.append({"company": company, "product group": pg, "complaints": int(V[s, t]), "normal": round(float(base["median"][s, t]), 1),
                 "severity (z)": round(float((V[s, t] - base["median"][s, t]) / base["sigma"][s, t]), 1),
                 "status": "new" if new[s, t] else "continuing"})
st.subheader("Alert list")
if rows:
    out = pd.DataFrame(rows).merge(tri.assign(week=tri.week).query("week == @week").drop(columns="week")
                                   .rename(columns={"product_group": "product group"}), on=["company", "product group"], how="left")
    out = out.sort_values("severity (z)", ascending=False).rename(
        columns={"top_issue": "top issue", "top_issue_share": "top issue share", "web_share": "web share"})
    st.dataframe(out.style.format({"top issue share": "{:.0%}", "web share": "{:.0%}"}), hide_index=True)
    st.caption("A very high top-issue share with nearly all complaints via the web looks like a coordinated or event-driven wave; "
               "a diffuse mix of issues looks more like a broad service problem.")
else:
    st.info("No alerts this week at this sensitivity.")

st.subheader("Look at one stream")
names = [f"{c} | {p}" for c, p in X.index]
default = names.index("Block, Inc. | Money transfer & wallets") if "Block, Inc. | Money transfer & wallets" in names else 0
pick = st.selectbox("Stream", names, index=default)
s = names.index(pick)
df = pd.DataFrame({"Actual complaints": V[s], "Alert threshold": thr[s]}, index=weeks)
st.line_chart(df, height=300)
st.caption("The threshold is built from the previous 26 weeks, with flagged weeks capped so one spike cannot blind the rule afterwards. "
           "Log scale is not applied; drag the sensitivity to see how the threshold moves.")

st.info("Limits: unverified reports; volume reflects awareness and campaigns as well as service quality; no normalization by company size; "
        "streams under about 5 complaints a week are too small to monitor on their own.")
