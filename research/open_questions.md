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
Date raised: 2026-06-19



