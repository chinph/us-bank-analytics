"""Friction calculator and scam-loss explorer (FTC Data Books + CFPB complaints)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import scam  # noqa: E402

PROC = ROOT / "data" / "processed"
st.set_page_config(page_title="Scam friction calculator", layout="wide")


@st.cache_data
def load():
    ftc = scam.load_ftc()
    loss = pd.read_csv(PROC / "loss_per_report_2024.csv").set_index("method").iloc[:, 0]
    co = pd.read_csv(PROC / "cfpb_scam_company.csv")
    params = json.loads((PROC / "cfpb_scam_params.json").read_text())
    return ftc, loss, co, params


ftc, loss, co, params = load()
observed = float(params["observed_bank_share"])

st.title("Where should a bank add friction to payments?")
st.caption("FTC Consumer Sentinel Data Books 2019 to 2024 and CFPB complaints. Unverified consumer reports that cover only a fraction of scams.")

tab1, tab2, tab3 = st.tabs(["Friction calculator", "Where losses concentrate", "How banks respond"])

with tab1:
    st.write("Friction is worth adding to a flagged payment when "
             "**P(scam) x loss if scam x share the bank bears x effectiveness > cost of the friction**. "
             "This finds the scam rate among flagged payments above which friction pays for itself.")
    c1, c2 = st.columns(2)
    method = c1.selectbox("Payment type", list(loss.sort_values(ascending=False).index))
    default_loss = float(loss[method])
    L = c1.number_input("Average loss when a scam succeeds ($)", 100.0, 200_000.0, default_loss, 100.0,
                        help="Default: FTC 2024 dollars per report, a conservative (low) estimate. Replace with your own.")
    e = c2.slider("Share of scam losses the friction stops", 0.05, 0.80, 0.25, 0.05)
    cost = c2.slider("Cost per flagged payment ($, including customers who drop off)", 0.5, 50.0, 5.0, 0.5)
    options = {f"Bank bears today's share ({observed:.1%}, CFPB monetary-relief rate)": observed,
               "Bank reimburses half": 0.5, "Bank reimburses all": 1.0, "Custom": None}
    share = options[st.radio("Who bears the loss?", list(options), horizontal=True)]
    if share is None:
        share = st.slider("Share of the loss the bank bears", 0.01, 1.0, 0.25, 0.01)

    p_star = scam.breakeven_probability(L, e, cost, share)
    m1, m2, m3 = st.columns(3)
    m1.metric("Breakeven scam probability", f"{100 * p_star:.3f}%")
    m2.metric("In other words", f"1 in {1 / p_star:,.0f} flagged payments" if p_star < 1 else "never pays off")
    m3.metric("Expected value per 1,000 flagged payments if 1% are scams", f"${1000 * (0.01 * L * share * e - cost):,.0f}")
    st.write(f"Compare **{100 * p_star:.2f}%** with the share of your own flagged {method.lower()} payments that turn out to be scams. "
             "If yours is higher, friction pays for itself on those payments; if lower, it does not.")
    grid = pd.DataFrame({f"cost ${c:g}": [100 * scam.breakeven_probability(L, ee, c, share) for ee in (0.1, 0.25, 0.4)] for c in (2, 5, 20)},
                        index=["stops 10%", "stops 25%", "stops 40%"])
    st.write("Breakeven scam probability (%) across assumptions:")
    st.dataframe(grid.style.format("{:.3f}"))
    st.info("Limits: FTC loss per report mixes everyone's payments, not your customers'; the model values only losses the bank bears (not customer harm "
            "or regulatory exposure); effectiveness and cost are assumptions; there is no data here on your volume of legitimate payments.")

with tab2:
    t = ftc["totals"].set_index("year")
    pop = scam.population()
    t["loss_per_resident"] = t.total_loss / pop.reindex(t.index)
    st.subheader("Reported fraud losses")
    c1, c2, c3 = st.columns(3)
    c1.metric("2024 reported losses", f"${t.total_loss[2024] / 1e9:.1f}B", f"x{t.total_loss[2024] / t.total_loss[2019]:.1f} since 2019", delta_color="off")
    c2.metric("Median loss, 2024", f"${t.median_loss[2024]:,}")
    c3.metric("Mean loss per loss report, 2024", f"${t.total_loss[2024] / t.reports_with_loss[2024]:,.0f}")
    st.line_chart(t[["total_loss"]].div(1e9).rename(columns={"total_loss": "Reported losses ($B)"}))
    st.subheader("By payment method")
    p = ftc["payment_method"]
    yr = st.select_slider("Year", options=sorted(p.year.unique())[1:], value=2024)
    pm = p[p.year == yr].set_index("method")
    pm["loss per report ($)"] = (pm.total_loss_musd * 1e6 / pm.reports).round(0)
    st.dataframe(pm[["reports", "total_loss_musd", "loss per report ($)"]].sort_values("total_loss_musd", ascending=False).rename(
        columns={"reports": "reports", "total_loss_musd": "losses ($M)"}))
    st.subheader("By contact method: total vs typical loss")
    cm = ftc["contact_method"]
    cm = cm[cm.year == yr].set_index("method")[["reports", "total_loss_musd", "median_loss"]]
    st.dataframe(cm.sort_values("total_loss_musd", ascending=False).rename(columns={"total_loss_musd": "losses ($M)", "median_loss": "median loss ($)"}))
    st.caption("Totals and medians rank channels differently: a few very large losses drive totals.")

with tab3:
    st.write(f"CFPB complaints tagged \"Fraud or scam\" (money transfer product), 2023 onward: {int(params['n_scam_complaints']):,} complaints; "
             f"{params['pooled_monetary_relief']:.1%} closed with monetary relief.")
    st.write("**Self-selection:** only customers unhappy with the company's response complain, so these are rates among complainers, not among scam victims.")
    show = co[["company", "n", "monetary_rate", "any_relief_rate", "unauth_monetary_rate"]].rename(columns={
        "n": "scam complaints", "monetary_rate": "monetary relief", "any_relief_rate": "any relief", "unauth_monetary_rate": "monetary relief, unauthorized"})
    st.dataframe(show.style.format({"monetary relief": "{:.1%}", "any relief": "{:.1%}", "monetary relief, unauthorized": "{:.1%}"}), hide_index=True)
