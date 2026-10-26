# Scam losses: research plan (written before the analysis)

## Decision and reader
**Decision:** When customers are scammed, where do losses concentrate, and where should a bank add friction to payments?
**Reader:** Head of fraud strategy at a large US bank. They need to know which payment types and contact channels matter, how the bank's own complaint handling compares with peers, and where friction pays for itself.

## Data and access check
- **FTC Consumer Sentinel Data Books, 2019 to 2024** (six annual editions, public). The FTC does not publish record-level data or a CSV; the figures exist as PDF tables and an interactive dashboard. Tables were extracted from the PDFs (amount lost, payment method, contact method). The 2025 edition could not be located. Reports are **unverified consumer submissions**, not a survey, and cover only a fraction of all scams.
- **Coverage within the FTC tables:** payment method is known for only about 18% of fraud reports and contact method for about 58%, so by-method totals cover a minority of all dollars lost. Percentages below are shares of what is classified.
- **FTC payment-method tables give counts and total dollars but no median loss**, so medians are used for contact method and for the overall loss distribution; for payment method I use loss per report.
- **CFPB Consumer Complaint Database** (record level, downloaded 2026-10-26; terms of use not yet read on the CFPB page; confirm before publishing). Scam complaints are tagged with the issue "Fraud or scam" only within the money transfer product (the product that holds Zelle, Cash App, PayPal, wires and crypto exchanges). Scams that happen through a checking account are not separately tagged.
- **Population:** US Census Bureau resident population estimates (Vintage 2019 for 2019; Vintage 2024 for 2020 to 2024), downloaded from census.gov.
- **Disclosure:** before writing this plan I had seen the 2024 FTC payment and contact tables and the aggregate CFPB response rates for scam complaints. Some predictions below are therefore not fully blind.

## Method
1. **Trend:** reported losses, reports with a loss and median loss by year; per 100,000 residents.
2. **Loss distribution:** a few very large losses dominate totals, so report medians next to means. From the published loss-size bands, bound the dollar share held by reports above $10,000 (a rigorous lower bound, since the other bands cannot sum to more than their upper limits).
3. **Payment method (2020 to 2024, the consistent category set):** totals, share of classified dollars, and loss per report.
4. **Contact method (2020 to 2024):** totals against medians, since the two rank channels differently.
5. **CFPB response to scam complaints (2023 onward):** share closed with monetary relief, non-monetary relief and explanation, and timeliness, by company with at least 100 complaints; Wilson intervals; a funnel plot against the pooled rate; compared with unauthorized-transaction complaints at the same companies. Self-selection caveat: only customers who were unhappy with the bank's answer complain to the CFPB.
6. **Decision model for friction:** a flagged payment is worth adding friction to if
   `P(scam) x loss if scam x share of loss the bank bears x friction effectiveness > cost of friction per flagged payment`.
   Solve for the breakeven scam probability by payment type, using FTC loss per report (a lower bound on loss when a loss occurs), a range of effectiveness (10% to 40%) and friction cost ($2 to $20 per flagged payment), and a range for how much of the loss the bank bears (the CFPB monetary-relief share today up to 100% under a reimbursement regime).

## Predictions (logged before the analysis)
1. Bank transfer, cryptocurrency and wire transfer together hold at least 60% of classified payment-method losses in 2024.
2. Reports above $10,000 (about 13% of loss reports) hold at least 80% of dollars lost.
3. The contact channel with the highest total losses is not the one with the highest median loss; phone calls have the highest median.
4. Loss per report is highest for bank transfers and more than 10 times that of credit cards.
5. Reported losses per 100,000 residents grew at least 5 times from 2019 to 2024.
6. Fewer than 10% of CFPB scam complaints end in monetary relief, with wide differences between companies: at least 5 companies fall outside the 99.8% funnel limits.
7. At the stated assumptions, breakeven scam probability for bank transfers is under 0.5% if the bank bears the whole loss, and over 1% if it bears only today's observed relief share.

## Limits (stated up front)
FTC and CFPB data are unverified consumer reports and cover a fraction of scams; payment and contact method are known for a minority of reports; the FTC tables lack payment-method medians; CFPB scam tagging exists only for money transfer products; no data on the volume of legitimate payments, so the friction model gives breakeven thresholds, not a forecast; effectiveness and cost inputs are assumptions, not measurements.
