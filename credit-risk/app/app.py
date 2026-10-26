"""Cut-off simulator: approval rate, bad rate and profit at an editable score cut-off and cost assumptions."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"

st.set_page_config(page_title="Credit cut-off simulator", layout="wide")


@st.cache_data
def load():
    scores = pd.read_csv(PROC / "test_scores.csv")
    params = json.loads((PROC / "params.json").read_text())
    return scores, params


scores, params = load()
measured_lgd = float(params["lgd"])

st.title("Where should the score cut-off be?")
st.caption("Test-set loans (originated Jul 2012 to Mar 2013) scored by the scorecard. Outcome = charged off or defaulted within 12 months. "
           "Funded loans only: approval rates are among loans that were already approved and funded.")

st.sidebar.header("Your cost assumptions")
gain = st.sidebar.slider("Profit on a good loan (% of principal)", 1.0, 25.0, 10.0, 0.5) / 100
loss = st.sidebar.slider("Loss on a bad loan (% of principal)", 20.0, 100.0, float(round(100 * measured_lgd)), 1.0) / 100
st.sidebar.caption(f"Measured loss given default in training data: {measured_lgd:.0%}. The profit on a good loan is an assumption.")

lo, hi = int(scores.points.min()), int(scores.points.max())
default_cut = int(np.quantile(scores.points, 0.24))
cut = st.slider("Approve applicants scoring at or above (points)", lo, hi, default_cut)

scores["pnl"] = scores.amount * np.where(scores.bad == 1, -loss, gain)
ok = scores.points >= cut
ap, dec = scores[ok], scores[~ok]


def money(x):
    return f"${x / 1e6:,.2f}M"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Approval rate", f"{ok.mean():.0%}", f"{(~ok).sum():,} loans declined", delta_color="off")
c2.metric("Bad rate, approved", f"{ap.bad.mean():.1%}" if len(ap) else "n/a",
          f"declined: {dec.bad.mean():.1%}" if len(dec) else None, delta_color="off")
c3.metric("Profit", money(ap.pnl.sum()), f"{money(ap.pnl.sum() - scores.pnl.sum())} vs approving everyone")
c4.metric("Profit per $ lent", f"{ap.pnl.sum() / ap.amount.sum():+.3f}" if len(ap) else "n/a",
          f"approve-all: {scores.pnl.sum() / scores.amount.sum():+.3f}", delta_color="off")

order = scores.sort_values("points", ascending=False).reset_index(drop=True)
order["cum_profit"] = order.pnl.cumsum() / 1e6
order["approval_rate"] = (order.index + 1) / len(order)
best = order.loc[order.cum_profit.idxmax()]

st.subheader("Profit by cut-off")
st.line_chart(order.set_index("points")["cum_profit"].rename("Profit, $ million"), height=300)
st.write(f"At these assumptions the profit-maximizing cut-off is about **{best.points:.0f} points** "
         f"(approving {best.approval_rate:.0%} of loans, profit {money(best.cum_profit * 1e6)}). "
         "This optimum is picked on the test loans themselves, so it is slightly optimistic; the notebook chooses the cut-off on a separate validation set.")

st.subheader("Bad rate by score band")
bands = pd.qcut(scores.points, 10, duplicates="drop")
t = scores.groupby(bands, observed=True).agg(loans=("bad", "size"), bad_rate=("bad", "mean"), predicted=("p_bad", "mean"))
t.index = [f"{int(i.left)} to {int(i.right)}" for i in t.index]
st.dataframe(t.style.format({"bad_rate": "{:.1%}", "predicted": "{:.1%}", "loans": "{:,}"}))

st.info("Limits: only funded loans are observed, so rejected applicants are missing; the profit on a good loan is an assumption; "
        "12-month horizon captures early default only.")
