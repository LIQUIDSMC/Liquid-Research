# Market Hypotheses

Testable claims about what might predict trader skill or market mispricing. Should connect to the Research to Edge Pipeline in zHANDOFF.md.

## Template

Hypothesis: (one clear, testable claim)
Reasoning:
Evidence so far:
How to test:
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted

## Current Entries
---

Hypothesis: Wallets that concentrate their trading in a single Active Research category (specialists) outperform wallets that spread trades evenly across multiple categories (generalists).
Reasoning: Narrow domain focus may allow a trader to develop deeper, more accurate judgment than someone splitting attention across unrelated subject areas (economics vs. geopolitics vs. sports, etc.).
Evidence so far: None directly. Anecdotal external claims exist (e.g. a trader specializing in weather markets) but these are unverified social-media claims, not evidence, per Research Integrity Rules in README.md.
How to test: Once wallets with resolved trade history exist in the dataset, compute each wallet's category concentration (% of trades in its single most-common category) and compare win rate/P&L between high-concentration and low-concentration wallets.
Status: Unreviewed — blocked on Phase 3's open question (no discovered wallet yet has resolved trade history).

---

Hypothesis: Following a historically strong wallet's trades (with a realistic reaction delay) would have produced positive historical P&L.
Reasoning: If a wallet shows a real, repeatable edge, a delayed follower might capture some of that edge, net of slippage/delay costs.
Evidence so far: None. This is explicitly a research question, not a basis for building a copy-trading system. Survivorship bias risk: a wallet's edge may not survive being followed by others, per zHANDOFF.md.
How to test: Backtest — for a wallet with resolved trade history, simulate entering each position one block after the original trade, using realistic price impact assumptions, and compare resulting P&L to the original wallet's actual P&L.
Status: Unreviewed — blocked on the same Phase 3 resolved-trade-data gap as the specialization hypothesis above.

---

Hypothesis: Trader-edge research (finding skilled traders) is a better-aligned long-term direction for Liquid Research than market-edge research (independently estimating "fair value" to find mispriced markets).
Reasoning: Trader-edge research extends data Liquid Research can already collect from Polymarket itself (trades, categories, resolutions). Market-edge research would require new external data sources per category (economic indicators, polling data, weather models) that don't exist in this project today.
Evidence so far: Architectural analysis only — see research/future_experiments.md entry on mispricing scanner feasibility.
How to test: Not directly testable as a single hypothesis; this is a strategic direction assessment, included here for visibility rather than as a true testable claim.
Status: Reviewed — accepted as architectural guidance. Trader-edge direction favored given existing codebase shape.

---

Hypothesis: Profitable wallets exit positions before market resolution more often than they hold to settlement, and exits correlate with observable signals (volume spikes, liquidity changes, price acceleration) rather than occurring randomly.
Reasoning: If exit timing is systematic rather than arbitrary, it may be a learnable behavior pattern distinct from entry selection — relevant to the existing trader-type distinction (hold-to-resolution vs. early-exit) already defined in zHANDOFF.md.
Evidence so far: None verified. This question was prompted by an external, unverified source making specific numeric claims about exit timing and profit capture — those specific numbers are explicitly NOT treated as evidence here, only the underlying question is retained.
How to test: For wallets with resolved trade history (once available — see open_questions.md), compare exit timestamp to resolution timestamp, and check whether exits cluster around detectable events (volume spikes in the market, liquidity changes, rapid price movement) versus being uniformly distributed across the market's lifetime.
Status: Unreviewed — blocked on the same resolved-trade-data gap as other wallet performance hypotheses.

---

Hypothesis: Equivalent or closely-related prediction markets on different venues (e.g. Polymarket vs. Kalshi pricing the same real-world event) exhibit a statistically stable spread that could be modeled and may revert when temporarily disrupted.
Reasoning: If two venues are pricing the same underlying event, persistent or mean-reverting pricing differences between them would be a structural signal independent of either venue's own internal liquidity quirks. This is a standard cross-venue arbitrage framing (cointegration spread S_t = P_P,t - βP_K,t - μ, with Ornstein-Uhlenbeck mean-reversion as the candidate model), not original to any single source.
Evidence so far: A real, peer-reviewed-style arXiv paper (Gebele & Matthes, 2026, "Semantic Non-Fungibility and Violations of the Law of One Price in Prediction Markets," arXiv:2601.01706) reports that roughly 6% of events are concurrently listed across platforms and that semantically equivalent markets show persistent execution-aware price deviations of 2-4% on average, even in liquid markets. This is genuine, citable evidence for the underlying phenomenon (cross-platform price divergence exists), though it does NOT confirm any specific trading strategy is profitable net of fees, and it was sourced via a marketing-oriented Twitter/blog post (separate from the paper itself) whose own profitability claims remain unverified and are explicitly excluded. Liquid Research has no Kalshi integration of any kind today, so this hypothesis still cannot be tested with current infrastructure regardless of this paper's findings.
How to test: Would require building Kalshi data collection (does not exist in this project), identifying genuinely equivalent markets across both venues (non-trivial — markets are rarely worded identically), and running statistical tests (e.g. Augmented Dickey-Fuller, Johansen cointegration) on the resulting paired price series.
Status: Unreviewed — no current prerequisite infrastructure exists. This is a larger undertaking than other open hypotheses, since it requires a new data source, not just new analysis of existing data.

---

Hypothesis: Order book imbalance (the relative volume of bids vs. asks near the best price) predicts short-term price movement better than the midpoint alone, and a volume-weighted "micro-price" outperforms midpoint as a short-term reference price.
Reasoning: Standard market-microstructure concept (I_t = (V_b - V_a)/(V_b + V_a) for imbalance; micro-price = volume-weighted blend of best bid/ask) — legitimate, widely used in traditional market-making, not specific to the source article.
Evidence so far: None tested on Polymarket data. Liquid Research's existing CLOB work (scanner/clob_client.py) already retrieves full bid/ask book depth and correctly parses best bid/ask by value — the raw data needed for this exists, but no imbalance or micro-price calculation has been built or tested.
How to test: Using scanner/clob_client.py's already-validated book data, compute imbalance and micro-price for a sample of markets, then compare against subsequent price movement over a short window to see if either signal has predictive value.
Status: Unreviewed — this is the one hypothesis in this batch that could be tested with EXISTING Liquid Research infrastructure (clob_client.py), unlike the cross-venue hypothesis above which requires new data sources entirely.

---

Hypothesis: Large orders or liquidity shocks temporarily move prediction-market prices away from a stable reference level, followed by measurable reversion back toward that level.
Reasoning: Standard liquidity-shock mean-reversion framing from traditional market microstructure. Plausible but unverified for prediction markets specifically, which may behave differently than continuous markets due to resolution-driven pricing rather than pure supply/demand.
Evidence so far: None. Prompted by the same external article; no performance claims from that source are treated as evidence.
How to test: Would require historical, time-series order book data (not just point-in-time snapshots) to observe price behavior before/during/after a detected liquidity shock — Liquid Research currently only takes point-in-time CLOB snapshots, not continuous historical book data.
Status: Unreviewed — blocked on a new data collection capability (continuous/historical book snapshots) that doesn't exist in this project yet.


---

Hypothesis: Certain Polymarket wallets exhibit repetitive micro-order patterns — identical or near-identical position sizes, prices, and timing intervals across many trades — and this bot-like behavior may be systematically correlated with either above-average or below-average outcomes, making it a detectable and potentially useful signal for wallet filtering or classification.
Reasoning: During Phase 3 wallet discovery, several discovered wallets showed highly repetitive order patterns inconsistent with human discretionary trading. The question of whether this pattern predicts anything (profitability, a specific strategy type, or just noise) was raised in open_questions.md but never formalized into a hypothesis. Bot wallets are explicitly defined as a separate research category in zHANDOFF.md, with the stated goal of understanding what markets they trade, what they avoid, and whether their behavior improves scanner filters — not copying them. This hypothesis is the formal version of that question.
Evidence so far: Observational only. Several wallets discovered via wallet_discovery.py showed this pattern during Phase 3 (2026-06-19). No outcome data exists yet for those wallets since all their eligible trades were unresolved at the time of analysis.
How to test: Once wallet resolved-trade data exists (Phase 3 extension prerequisite), identify wallets exhibiting repetitive micro-order patterns (concentration metric: % of trades within a narrow size/price band), compare their win rate and P&L against wallets with varied order behavior, and determine whether the pattern is correlated with any measurable performance difference.
Status: Unreviewed — blocked on Phase 3 resolved-trade-data gap. Promoted from open_questions.md (2026-07-03).

---

NOTE — Status update for Order Book Imbalance / Micro-Price hypothesis (above):
The OBI hypothesis has been reviewed and promoted to Program B (active research program). Status changed from "Unreviewed" to "Promoted — Program B (2026-07-03)." See programs/program_b/README.md and zROADMAP.md for current program status.
