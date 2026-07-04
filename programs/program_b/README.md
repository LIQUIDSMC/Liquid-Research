# Program B — Order Book Imbalance / Micro-Price Research

## Status
ACTIVE — First diagnostic complete. Stability testing in progress.

Program A (Tradeability Score / Scanner One) continues running
its daily cycle uninterrupted. Program B runs independently.

## Hypothesis
Order book imbalance (the relative volume of bids vs. asks near
the best price) predicts short-term price movement better than
the midpoint alone, and a volume-weighted micro-price outperforms
midpoint as a short-term reference price on Polymarket.

Full hypothesis: research/market_hypotheses.md
Experiment design: research/future_experiments.md

## Why This Program
- No new infrastructure required — scanner/clob_client.py already
  fetches and correctly parses full bid/ask book depth for any market.
- Tests a timing signal (when to enter) rather than a selection
  filter (which market to trade) — a fundamentally different and
  complementary class of signal to Program A.
- Promoted from research vault 2026-07-03 after full architectural
  review confirmed it as the highest-ROI next research direction.

## Current State

### Phase 1 — Feasibility ✅ COMPLETE (2026-07-03)
Script: programs/program_b/obi_diagnostic.py

OBI and micro-price computed successfully on all 5 markets from
the latest Program A snapshot. Mathematical sanity confirmed —
micro-price deviation direction matches OBI sign in every case.

Results from first run (2026-07-03):
- Fed no-change (0.895): OBI -0.48, micro-price below midpoint
- Putin out (0.105): OBI +0.58, micro-price above midpoint
- Fed increase (0.096): OBI -0.38, micro-price below midpoint
- China/Taiwan (0.034): OBI +0.80, micro-price above midpoint
- US-Iran July 10 (0.018): OBI +0.58, micro-price above midpoint

This confirms feasibility only. No predictive claim is made.

### Phase 2 — Stability Testing 🔲 IN PROGRESS
Run obi_diagnostic.py on consecutive days. Observe whether OBI
values are stable, volatile, or appear correlated with subsequent
price movement. No code changes required — just repeated runs and
comparison of outputs.

Done when:
- OBI and micro-price values documented across multiple days
- Stability or volatility pattern identified per market type
- Decision made: is the signal stable enough to study further?

### Phase 3 — Predictive Value Testing 🔲 NOT STARTED
Only begins after Phase 2 confirms stability.

## Three-Question Check
Every metric must answer these before earning a place in Liquid Research:
1. Is it mathematically correct? ✅ Confirmed (Phase 1)
2. Is it stable across many markets? ❓ Testing now (Phase 2)
3. Does it improve a trading decision? ❓ Do not assume yet

## Known Technical Debt
obi_diagnostic.py currently fetches CLOB data twice per market —
once via get_market_clob_data() and again via fetch_market_by_slug()
+ fetch_order_book(). This is a future cleanup item, not a blocker.
Refactor only after Phase 2 confirms the signal is worth pursuing.

## Data
Raw market snapshots stay in data/markets/ as shared platform input.
Program B outputs live in programs/program_b/data/.
Do not duplicate snapshots into Program B.

## Dependencies
scanner/clob_client.py — existing, no modifications made.
Program A trade results are not required or used.
The diagnostic only reads the latest Program A market snapshot
to select live slugs.