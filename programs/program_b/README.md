# Program B — Order Book Imbalance / Micro-Price Research

## Status
QUEUED — Not yet started.

Program A (Tradeability Score / Scanner One) continues running
its daily cycle uninterrupted. Program B will begin once the
initial architecture and operating procedure are designed.

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
- Could show initial results within days of starting, not weeks.
- Promoted from research vault 2026-07-03 after full architectural
  review confirmed it as the highest-ROI next research direction.

## Dependencies
None. Program A data and infrastructure are not required.
scanner/clob_client.py is the only prerequisite, and it already exists.

## When Operational Documents Will Be Created
MISSION_CONTROL.md, DAILY_OPERATIONS.md, and any program-specific
roadmap will be created when Program B actually begins — not before.
Documentation should emerge from real work, not assumptions about
what the work will look like.

## Current Blocking Conditions
None. Program B is queued by choice, not by technical dependency.
It begins when explicitly started.
