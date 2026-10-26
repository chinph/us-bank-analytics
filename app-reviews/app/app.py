"""Explore what unhappy bank-app reviewers write about, which themes go with low ratings, and how an app compares with peers."""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
st.set_page_config(page_title="Bank app reviews", layout="wide")
SHORT = {"Login & authentication": "Login", "Bugs, crashes & slowness": "Bugs & slowness", "Fraud, scams & security": "Fraud & security",
         "Frozen, closed or restricted accounts": "Frozen / closed accounts", "Customer service & support": "Customer service",
         "Fees & charges": "Fees & charges", "Payments, transfers & deposits": "Payments & transfers", "Updates, design & features": "Updates & design"}


@st.cache_data
def load():
    return (pd.read_csv(PROC / "themes_by_group.csv"), pd.read_csv(PROC / "themes_by_app.csv"), pd.read_csv(PROC / "odds_ratios.csv"),
            pd.read_csv(PROC / "app_summary.csv"), pd.read_csv(PROC / "validation_scores_B.csv"))


grp, app, orr, summ, val = load()
grp["theme"] = grp.theme.map(SHORT)
app["theme"] = app.theme.map(SHORT)

st.title("What do unhappy bank-app users write about?")
st.caption("17 US bank, card and fintech apps, App Store (iOS), the 500 most recent reviews each, collected 2026-10-26. "
           "Shares are among 1 and 2 star reviews. Reviews are self-selected, and the text is not stored in this repo.")

tab1, tab2, tab3 = st.tabs(["Themes by app type", "What goes with a low rating", "Compare an app"])

with tab1:
    wide = grp.pivot(index="theme", columns="group", values="share")
    wide = wide.loc[wide.mean(axis=1).sort_values(ascending=False).index]
    st.bar_chart((100 * wide).round(1), horizontal=True, height=380)
    st.caption("% of 1 and 2 star reviews that mention each theme. Compare groups rather than reading exact percentages: the keyword tagger "
               f"has median precision {val.precision.median():.2f} and recall {val.recall.median():.2f} on 200 fresh hand-labeled reviews.")
    n = grp.groupby("group").n.first()
    st.write("Unhappy reviews analyzed: " + ", ".join(f"{g} {int(v):,}" for g, v in n.items()))

with tab2:
    o = orr.copy()
    o["theme"] = o.theme.map(SHORT)
    o = o.dropna(subset=["theme"]).sort_values("odds_ratio", ascending=False).set_index("theme")
    st.write("Odds of a 1 or 2 star rating when a review mentions the theme, adjusting for app (logistic regression, 7,804 reviews). "
             "This is association among reviewers, not the effect of fixing a theme.")
    st.dataframe(o[["odds_ratio", "lo", "hi"]].rename(columns={"odds_ratio": "odds ratio", "lo": "95% low", "hi": "95% high"}).style.format("{:.1f}"))
    st.bar_chart(o["odds_ratio"], horizontal=True, height=320)
    st.info("Common is not the same as costly: updates and design are the most frequent theme but have the weakest link to a low rating; "
            "frozen or closed accounts are rare at banks but have the strongest.")

with tab3:
    names = sorted(app.app.unique())
    pick = st.selectbox("App", names, index=names.index("Chase") if "Chase" in names else 0)
    row = app[app.app == pick]
    g = row.group.iloc[0]
    n = int(row.n.iloc[0])
    if n < 50:
        st.warning(f"Only {n} unhappy reviews for this app: too few for conclusions.")
    peers = app[(app.group == g) & (app.app != pick)].groupby("theme").share.mean()
    comp = pd.DataFrame({pick: row.set_index("theme").share, f"Other apps in group ({g})": peers})
    comp = comp.loc[comp.mean(axis=1).sort_values(ascending=False).index]
    st.bar_chart((100 * comp).round(1), horizontal=True, height=380)
    s = summ[summ.app == pick].iloc[0]
    st.write(f"Based on {int(s.reviews)} recent reviews covering {int(s.window_days)} days; {int(n)} were rated 1 or 2 stars with four or more words. "
             "Mean rating of recent reviews is not comparable across apps (it depends on how often an app prompts happy users to rate).")

st.info("Limits: iOS only; recent reviews, not a sample of customers; rule-based tagging is moderate in accuracy; app reviews describe the app, not the bank's overall service.")
