# Complaint monitor: research plan (written before building detectors)

## Decision and reader
**Decision:** Each week, which company and product complaint streams should be escalated for review, and what alert rule balances catching real surges against alert fatigue?
**Reader:** Head of complaint management at a large US bank or payments firm. They have a small team, so the output must be a short weekly list they can act on, not a dashboard of everything.

## Data and access check
- Source: CFPB Consumer Complaint Database, bulk file `complaints.csv.zip` downloaded 2026-10-26 (18.7M complaints, Dec 2011 to Oct 2026, 15 columns, no narrative text). Published by a US federal agency as open data.
- **Terms of use not yet read on the CFPB page; confirm before publishing.** The repo does not redistribute the raw file.
- Complaints are **consumer-submitted and unverified**, and not representative of all customers. Volume reflects awareness, campaigns and policy as much as bank quality. A surge is a signal to look, not a finding of wrongdoing.
- Checked before analysis: file integrity, columns, volume by year and product, product renames, and the most recent weeks. No alert logic was designed from outcomes.

## Scope and data hygiene
- **Window:** 2018-01-01 onward. Product names were reorganized in 2017 and again in 2023 ("Credit card" split from "Credit card or prepaid card"), so products are mapped to six stable groups: Checking & savings; Credit & prepaid cards; Mortgage; Money transfer & wallets; Vehicle loans; Personal loans. Student loans and debt collection are excluded (servicers and collectors, not the banking relationship); the three credit bureaus are excluded.
- **Incomplete recent weeks.** The latest week in the file had about 36% of a normal week's complaints because publication lags receipt. Weeks ending within 14 days of the file date (after 2026-10-11) are dropped; counting them would create false "drops".
- **Stream** = company x product group, weekly counts (weeks start Monday, by date received). **Monitored streams:** those with at least 500 complaints over the window. The stream list is chosen using the whole period, a mild look-ahead, noted as a limit.
- Volume exploded from 2025 (5.4M complaints in 2025, driven by credit reporting). Bank-product volume is much steadier; baselines are therefore rolling, not global.

## Method
1. **Baseline** for each stream-week: the previous 26 weeks (excluding the current week).
2. **Detectors compared at equal alert workload:**
   a. static threshold on weekly count;
   b. mean + k standard deviations (naive);
   c. robust rule: median + k scaled MAD, with a minimum excess count;
   d. CUSUM on standardized robust residuals, aimed at sustained shifts.
3. **Back-test with injected surges** (ground truth we control): add surges of 1.5x, 2x and 3x the baseline, as a 1-week burst or a 4-week sustained shift, to random quiet stream-weeks; measure detection rate and delay by stream volume bucket (under 5, 5 to 20, 20 to 100, over 100 complaints a week).
4. **False alerts on real history:** alerts per week across all monitored streams for each detector and setting, with the caveat that real history contains true surges, so this overstates false alarms.
5. **Baseline contamination test:** how long after the January 2025 Cash App and Zelle spike does each detector stay blind or inflated for those streams?
6. **Alert triage card:** for each alert, issue concentration, share submitted via web, top state, and whether the surge is a burst (decays within 2 weeks) or sustained, to help separate a coordinated filing wave from a real deterioration.
7. **Workload target:** at most about 10 alerts a week across all streams (an assumption about team capacity, adjustable in the app).

## Predictions (logged before building)
1. The robust detector finds 2x sustained surges within 2 weeks in streams above 20 complaints a week, and does poorly below 5 a week, where Poisson noise swamps the signal.
2. At equal alert workload the static threshold performs worst, because it ignores stream size.
3. The mean and standard deviation rule is blinded after the January 2025 spike: its inflated baseline masks real surges for months; the robust rule recovers in a few weeks.
4. Most real alerts are 1 to 2 week bursts; a minority are sustained.
5. A setting giving about 10 alerts a week exists with detection of 2x sustained surges above 70% in streams over 20 complaints a week.

## Limits
Unverified consumer reports; volume reflects awareness and campaigns; no narrative text; no ground-truth labels of real incidents, so detection power is measured on injected surges; no company-side data (volumes of accounts) to normalize by size.
