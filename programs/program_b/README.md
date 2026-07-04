# Program B — Market Microstructure Research

## Status
ACTIVE — First indicator (OBI) verified. Stability testing in progress.

Program A (Tradeability Score / Scanner One) continues running
its daily cycle uninterrupted. Program B runs independently.

## Identity
Program B studies order-book and market-microstructure indicators
as a class, not a single metric. Order Book Imbalance (OBI) and
micro-price are the first indicator studied under this program —
not the entire scope of the program.

The governing question: which microstructure indicators, if any,
give Liquid Research the most useful, stable, low-noise signal for
future market selection or entry timing? ROI and evidence matter
more than novelty. A new indicator only earns a place here if it
answers a real gap identified in an existing one.

## Review Cadence

All active Program B indicators are reviewed together on a shared
schedule, not on separate per-indicator timelines. Clock starts
from OBI's first log entry (2026-07-03).

- 1-week review: around 2026-07-10
- 2-week review: around 2026-07-17
- 1-month review: around 2026-08-03

At each checkpoint, evaluate every active indicator against:
- Is it behaving correctly? Any errors or unexpected values?
- Is it stable? Volatile? Noisy?
- Does anything deserve refinement or retirement?
- Does anything show early signs worth investing further in?

Indicators that fail early are retired without further investment.
Indicators that look promising continue collecting toward the next
checkpoint. New indicators added between checkpoints join the same
shared review cycle rather than starting their own clock.

## Folder Structure

programs/program_b/
    README.md
    indicators/       - pure calculation logic, no I/O
    diagnostics/      - runner scripts: fetch data, call indicators, log, display
    analysis/         - reserved for future comparison/stability scripts

data/program_b/
    obi_log.csv       - OBI indicator output log

This structure exists so additional indicators do not become
messy. Each indicator gets its own file in indicators/. Each
diagnostic runner imports from indicators/ rather than
duplicating calculation logic.

## Indicator 1 - Order Book Imbalance (OBI) / Micro-Price

Hypothesis: Order book imbalance (relative volume of bids vs.
asks near the best price) predicts short-term price movement
better than midpoint alone. A volume-weighted micro-price
outperforms midpoint as a short-term reference price on Polymarket.

Full hypothesis: research/market_hypotheses.md
Experiment design: research/future_experiments.md

Why this indicator first:
- No new infrastructure required - scanner/clob_client.py already
  fetches and correctly parses full bid/ask book depth for any market.
- Tests a timing signal (when to enter) rather than a selection
  filter (which market to trade) - a fundamentally different and
  complementary class of signal to Program A.

### Phase 1 - Feasibility COMPLETE (2026-07-03)
Files: programs/program_b/indicators/obi.py (calculation)
       programs/program_b/diagnostics/run_obi.py (runner)

OBI and micro-price computed successfully on all 5 markets from
the latest Program A snapshot. Mathematical sanity confirmed -
micro-price deviation direction matches OBI sign in every case.

This confirms feasibility only. No predictive claim is made.

### Phase 2 - Stability Testing IN PROGRESS
Run diagnostics/run_obi.py on consecutive days. Observe whether
OBI values are stable, volatile, or appear correlated with
subsequent price movement. No code changes required - just
repeated runs and comparison of outputs.

Done when:
- OBI and micro-price values documented across multiple days
- Stability or volatility pattern identified per market type
- Decision made: is the signal stable enough to study further?

### Phase 3 - Predictive Value Testing NOT STARTED
Only begins after Phase 2 confirms stability.

## Three-Question Check
Every indicator must answer these before earning a place in
Liquid Research:
1. Is it mathematically correct?
2. Is it stable across many markets?
3. Does it improve a trading decision?

OBI status: (1) Confirmed. (2) Testing now. (3) Do not assume yet.

## Queued Indicator Candidates (Not Started)

Near-book / top-level depth imbalance
Compute the same imbalance ratio using only the top 3-5 price
levels closest to the midpoint, instead of total book volume.
Tests whether near-market pressure differs from total pressure.
Directly interrogates an assumption already in the OBI calculation
rather than introducing an unrelated concept.

Spread-normalized OBI
Normalize OBI by spread width so imbalance values are comparable
across markets with different liquidity profiles. Tests whether
raw OBI needs a liquidity-context adjustment to be meaningful
across markets - directly answers the "is it stable across many
markets" question from the three-question check.

Neither indicator is implemented yet. Do not begin until explicitly
approved.

## Known Technical Debt
diagnostics/run_obi.py currently fetches CLOB data twice per
market - once via get_market_clob_data() and again via
fetch_market_by_slug() + fetch_order_book(). This is a future
cleanup item, not a blocker. Refactor only after Phase 2 confirms
the signal is worth pursuing.

## Data
Raw market snapshots stay in data/markets/ as shared platform input.
Program B outputs live in data/program_b/, one file per indicator.
This follows the platform convention: programs/ holds code and
documentation only. data/ holds all generated datasets and outputs,
organized per program.
Do not duplicate snapshots into Program B.

## Dependencies
scanner/clob_client.py - existing, no modifications made.
Program A trade results are not required or used.
Diagnostics only read the latest Program A market snapshot
to select live slugs.
