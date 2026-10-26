# Bank app reviews: research plan (written before data collection)

## Decision and reader
**Decision:** Which problems should a bank fix first in its mobile app to reduce low-rated reviews, and how do customer complaints about banks differ from those about fintech and payment apps?
**Reader:** Head of digital product or customer experience at a bank. They need a ranked list of problem themes, how much each costs in star rating, and where their app sits against peers.

## Data and access check
- **Source:** Apple's public App Store customer-review feed (`itunes.apple.com/us/rss/customerreviews`), US storefront, iOS only. Each app returns at most the 500 most recent reviews (10 pages of 50). App identity and lifetime rating counts come from Apple's public lookup API.
- **Why not the CFPB complaint narratives:** I checked the bulk file and the API; neither returns narrative text for any year, so that source is unusable here.
- **Apps (17):** banks and credit unions (Chase, Bank of America, Wells Fargo, Citi, Capital One, U.S. Bank, PNC, Truist, Navy Federal); card issuers (American Express, Discover); fintech and digital banks (Chime, Cash App, PayPal, Venmo, SoFi, Ally). Zelle has no standalone app in the store.
- **Politeness and privacy:** 1 to 2 seconds between requests, an identifying User-Agent, retries with backoff. Reviewer names, IDs and profile links are dropped at ingestion and never stored. Raw review text stays local and is not committed; the repo contains aggregated results only.
- **Known selection bias:** apps prompt happy users to rate (lifetime averages are 4.6 to 4.9 stars for every app), while written reviews skew toward people with a problem or strong feelings. Findings describe **people who write reviews**, not all customers.
- **Sampling window:** the 500 most recent reviews cover very different time spans per app (days for the biggest apps, weeks or months for smaller ones). The analysis compares themes within this snapshot, and checks results on a common recent window.
- Before writing this plan I saw a handful of sample reviews (Chase, Cash App) and the lifetime ratings; no theme or rating analysis was run.

## Method
1. **Collect and clean:** the 500 most recent reviews per app; drop duplicates; keep rating, title, text, app version and date. Flag very short reviews and non-English text.
2. **Theme tagging:** transparent keyword and phrase rules for nine themes, a review can have several: login and authentication; crashes, bugs and slowness; fraud, scams and security; frozen, closed or restricted accounts and held funds; customer service and support; fees and charges; payments, transfers and deposits; features, design and updates; praise and ease of use.
3. **Validation:** hand-label a random sample of about 150 reviews for the same themes (labeled by me, an AI, reading each review; not a human second opinion), and report precision and recall per theme against those labels. Rules are refined once on a development half and scored on a held-out half.
4. **What lowers ratings:** share of 1 and 2 star reviews mentioning each theme; logistic regression of a low rating (1 or 2 stars) on themes with app fixed effects, reported as odds ratios with confidence intervals.
5. **Banks versus fintech and payment apps:** theme prevalence by group, with Wilson intervals.
6. **Link to the scam analysis:** share of reviews mentioning fraud, scams or frozen accounts by app group.
7. **App view:** each app's theme profile and star distribution against its group, with small-sample caution.

## Predictions (logged before analysis)
1. Login and authentication problems plus crashes and bugs together appear in at least 30% of 1 and 2 star reviews for banks.
2. Fintech and payment apps have at least twice the share of reviews about frozen or restricted accounts, and about fraud or scams, compared with banks.
3. Mentions of customer service have the largest association with a low rating (largest odds ratio) among the themes, after adjusting for app.
4. The keyword tagger has precision of at least 0.8 for most themes and lower recall (around 0.6), since it misses paraphrases.
5. The average star rating of recent written reviews differs by more than 1 star between the best and worst app.

## Limits
iOS only; recent-review sample, not a random sample of customers; reviews skew negative or extreme; very different time windows per app; keyword rules miss sarcasm and paraphrase; validation labels were made by an AI; app reviews describe the app, not the bank's overall service; the number of reviews per app is small for per-app conclusions.

## Amendment (after data collection, before any theme analysis)
The collected sample showed that the time window covered by an app's 500 most recent reviews ranges from 2 days (U.S. Bank) to 281 days (Navy Federal), and that mean rating of recent reviews ranges from 1.6 to 4.8 stars. Apps that prompt satisfied users heavily fill their window with short five-star reviews, so **mean rating and overall theme prevalence are not comparable across apps** (they measure prompting as much as quality). Changes to the plan:
- **Primary denominator is 1 and 2 star reviews.** People who leave low ratings write spontaneously, so "what do unhappy reviewers write about" is comparable across apps. Prevalence among all reviews is reported only as a secondary view.
- Predictions 2 and 5 are evaluated on this basis; prediction 5 is replaced by a check of how strongly an app's mean rating relates to the time window its reviews cover.
- New check: whether an app's low ratings are driven by a single burst (one day or app version), since a short window can capture one incident.
- Exact-duplicate review text is flagged; duplicates of 8 or more words are removed as likely reposts.
