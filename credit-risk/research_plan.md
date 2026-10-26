# Credit risk: research plan (written before modeling)

## Decision and reader
**Decision:** Which loan applicants should a consumer lender approve, and at what score cut-off?
**Reader:** Head of consumer credit. They need an approve/decline rule, the trade-off between approval rate and losses, and how much to trust it on next year's applicants.

## Data and access check
- Source: Prosper Marketplace peer-to-peer loan data, 113,937 loan records (81 columns), Nov 2005 to Mar 2014.
- Obtained from the public Udacity-hosted copy. The Kaggle upload ([henryokam/prosper-loan-data](https://www.kaggle.com/datasets/henryokam/prosper-loan-data)) is listed as CC0 by Google Dataset Search. **The license has not been confirmed on the Kaggle page itself; confirm before publishing anything derived from it.** The raw file is not committed to the repo either way.
- **Duplicates:** 871 repeated `ListingKey` rows. They differ only in `ProsperScore`, so one row per listing is kept.
- **Two regimes:** Prosper stopped lending from late 2008 to mid 2009 and relaunched with a different rating system. Loans before the break carry `CreditGrade`, loans after carry `ProsperRating`/`ProsperScore`, and no loan has both. **The model uses post-relaunch loans only (originated July 2009 or later).** Mixing regimes would let the model learn the policy change, not credit risk.
- Only status counts and date ranges were inspected before this plan (no default rates by feature).

## Target and right-censoring
**Bad** = loan charged off or defaulted within **12 months of origination** (`ClosedDate` is the charge-off date for those statuses). Good = everything else.
The data ends 2014-03-10. A loan originated after 2013-03-10 has not had 12 months to go bad, so counting it as "good" would understate risk. **Only loans originated on or before 2013-03-10 are used.** Later loans are right-censored and excluded. Cancelled loans are dropped.
Sensitivity: the same analysis with an 18-month window (originations to 2012-09-10).

## Split by time, not at random
| Set | Originations | Use |
|---|---|---|
| Train | Jul 2009 to Dec 2011 | fit scorecard and boosted model |
| Validation | Jan 2012 to Jun 2012 | tune, calibrate, choose the cut-off |
| Test | Jul 2012 to Mar 2013 | touched once, for final numbers |
A random split would let the model see the future of the same vintages. The time split mimics deployment: fit on the past, score the next cohort.

## Features (application-time only)
Credit score range, debt-to-income, income range and verifiability, stated income, employment status and duration, inquiries, delinquencies, revolving credit, open accounts, loan amount, term, listing category, homeownership, `ProsperScore`/`ProsperRating` (kept as a **benchmark**, also tested as a feature).
**Excluded as leakage** (known only after origination): `LoanStatus`, `ClosedDate`, `LoanCurrentDaysDelinquent`, all `LP_*`, `LoanMonthsSinceOrigination`, `LoanFirstDefaultedCycleNumber`. The borrower's *prior* Prosper loan history (`TotalProsperLoans`, `OnTimeProsperPayments`, and related fields) is described in the data dictionary as measured at listing time, so it is **kept** (missing means no prior Prosper loan; encoded as 0 with an indicator). Prosper's own model outputs (`ProsperScore`, `ProsperRating`, `EstimatedLoss`, `EstimatedReturn`) are used only as a benchmark. **Excluded as decision variables or market signals:** `BorrowerRate`/`APR` (set from risk, used in the profit step), `PercentFunded`, `InvestorCount`. **Excluded for fairness:** `BorrowerState` (geographic proxy risk). A bank would also need reason codes for declines; the scorecard supplies them.

## Models
1. **Scorecard:** weight-of-evidence binning plus logistic regression, converted to points. Fully explainable, the bank standard.
2. **Boosted model:** gradient boosting on the same features.
3. **Benchmark:** Prosper's own `ProsperScore` and rating, so the question is whether we beat the platform's existing model, not just whether we beat chance.

## Evaluation
AUC and KS for ranking; **calibration** (predicted vs actual bad rate by decile, Brier score) because the cut-off depends on probabilities, not ranks; **stability** across vintages (population stability index, bad-rate drift); performance by vintage.

## Cut-off by cost
Expected profit per $1 approved = P(good) x gain − P(bad) x loss. **Loss given default** is measured from bad loans in training (`LP_NetPrincipalLoss / LoanOriginalAmount`). **Gain on a good loan** is an assumption (10% of principal over the horizon, net of funding cost), with a sensitivity grid from 5% to 15%. The cut-off is chosen on the validation set and reported on the test set. A bad loan costs several times what a good loan earns, so the optimal cut-off is stricter than the one that maximizes accuracy.

## Selection problem (stated up front)
The data contains only loans that were **funded**. Applicants who were rejected, or listings that never filled, are missing, so the model learns risk only within the approved population. Approval rates reported here are rates among already-funded loans, not among all applicants. Without rejected-applicant data (reject inference) the result cannot be a complete underwriting policy.

## Predictions (logged before modeling)
1. The scorecard reaches AUC of about 0.65 to 0.70 on the test set.
2. The boosted model beats the scorecard by 0.02 AUC or less; the simpler model is the recommendation.
3. Prosper's own score is about as good as, or slightly better than, my scorecard.
4. Bad rates drift between vintages, so the boosted model is miscalibrated on the test set (predicted default rate off by more than 10% relative) until it is recalibrated on validation.
5. At the stated assumptions, the profit-maximizing cut-off declines a meaningful minority (10% to 40%) of funded loans.
6. A leakage-contaminated version (including post-origination fields) would show a near-perfect AUC; reported only as a warning.

## Limits
Peer-to-peer platform, 2009 to 2013; funded loans only; profit assumptions; 12-month horizon captures early default only; no macroeconomic cycle beyond the recovery period.
