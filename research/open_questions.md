# Open Questions

Important unanswered questions that are not yet hypotheses, experiments, or roadmap items. Things worth remembering to ask later, once enough data exists to ask them properly.

## Template

Question:
Why it matters:
What data would be needed to answer it:
Date raised:

## Current Questions

Question: Do profitable wallets exit early, or hold to resolution?
Why it matters: Directly informs whether Liquid Research should study prediction skill traders or trading skill traders differently, per the trader-type distinction in zPHILOSOPHY.md.
What data would be needed: A meaningful sample of wallets with both resolved trades and visible exit timing across many markets.
Date raised: 2026-06-19

---
i
Question: Are repetitive micro-orders, bot-like, identical size and price patterns, predictive of anything, profitability, a specific strategy, or just noise?
Why it matters: Several discovered wallets show this pattern. Worth knowing whether it is a distinct, study-able behavior or irrelevant clutter to filter out.
What data would be needed: Resolved trade outcomes for several wallets exhibiting this pattern, compared against wallets with varied order behavior.
Date raised: 2026-06-19

---

Question: Does category specialization, trading mostly one Active Research category, correlate with higher win rate than generalist wallets?
Why it matters: Would directly inform whether future scanner filters should weight by wallet specialization.
What data would be needed: Per-category win rate broken down per wallet, across enough wallets to compare specialists versus generalists meaningfully.
Date raised: 2026-06-19

---

Question: Do high-volume, large position size, wallets outperform low-volume wallets, or is size unrelated to skill?
Why it matters: Would inform whether position size itself is a useful signal, separate from win rate.
What data would be needed: Resolved P&L data segmented by average position size across a meaningful wallet sample.
Date raised: 2026-06-19

---

Question: Why are most discovered wallets showing only unresolved trades?
Why it matters: Phase 3 validation requires resolved outcomes.
Current evidence: KickstandBot, poRussky, and the Mode 2 candidate
wallet (0x1abf0a...) all primarily traded currently active markets.
Potential test: Analyze additional candidate wallets and look for
older resolved markets. Better approach identified: search markets
for resolution status first, then find which discovered wallets
touched that specific market, rather than picking a wallet first.
Status: Open
Update (2026-06-20): Re-ran find_resolved_market.py after fixing
the slug-lookup bug in market_resolution.py. With the bug fixed,
the script now correctly resolves every market's real question
and status (previously showed false "Not in batch" for all 20).
Result confirmed honestly: all 20 discovered markets are still
genuinely Open. This is real-world timing, not a tooling gap.
Status: Confirmed — answer is "not enough time has passed yet,"
not a code issue.
Date raised: 2026-06-19



---

Question: Does clob_client.py's outcome_index=0 default correctly represent the primary outcome across all market types, including genuinely multi-outcome (3+) markets?
Why it matters: All three validation tests used the default index 0, which happened to be "Yes" in each case. Behavior for index 1, 2+ is implemented but has never actually been exercised against real data.
Current evidence: get_market_clob_data() accepts outcome_index as a parameter and uses it correctly in code, but only the default value has been tested.
Potential test: Run clob_client.py against a market with 3+ outcomes (e.g. a World Cup group winner market with multiple named outcomes) using outcome_index=1 or 2.
Status: Open

---

Question: How does clob_client.py behave under CLOB API rate limiting (HTTP 429)?
Why it matters: fetch_official_endpoints() and fetch_order_book() catch generic request exceptions but do not specifically detect or handle 429 responses with backoff/retry logic. Untested under real rate-limit conditions since only ~15 total calls were made across 3 markets in testing so far.
Current evidence: No 429 response has been observed yet. Behavior under this condition is unverified.
Potential test: Run clob_client.py against a larger batch of markets (10+) in quick succession and observe whether any 429s occur and how they're currently handled.
Status: Open


