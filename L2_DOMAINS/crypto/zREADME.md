# Crypto Domain — Liquid Research

## Status

Crypto is the active L2 research domain and the current consumer of the
shared L1 Market Data Platform. Its real-market research uses Coinbase BTC-USD
and ETH-USD data collected through that platform.

The causal trade-flow research sequence is closed through gross-edge v1 and
ETH replication v2. Under the frozen v2 replication design, the specific
ETH LONG Post-Entry Continuation H1 was rejected on independent replication.
That result does not generalize the rejection to all trade-flow hypotheses.
Cost-stress/economic-feasibility research has not started and remains paused.

## Architecture Boundary

The L1 Market Data Platform owns shared, venue-agnostic acquisition,
validation, normalization, canonical storage, data-integrity contracts, and
production market-data infrastructure.

L2 Crypto is the current consumer of that shared infrastructure. Crypto
does not own the Market Data Platform.

Current production canonical storage uses the fail-closed root:

`/mnt/lrs001/data/market_data_platform/canonical`

See `L1_CORE/market_data_platform/market_data/zROADMAP.md` for the shared
platform's current architecture and implementation record.

## Domain and Program Roles (Original Architecture Rationale)

The original architecture, recorded under the earlier `domains/` and
`programs/` layout, distinguished a **Domain**, which owns market selection
for one category of financial market, from a **Program**, which answers a
research question using a Domain's canonical output. Crypto was filed as a
Domain rather than a Program for that reason. Whether the same canonical
schema applies across Domains was an open design question in that architecture
and is not assumed here.

## Original Research Framing (Historical)

The original Crypto vision distinguished two independently testable market
types:

1. **Crypto Prediction Markets** — prediction markets whose outcomes concern
   crypto assets.
2. **Real Crypto Markets** — continuously traded spot/futures markets with
   order books, continuous liquidity, and no resolution date.

That distinction remains useful as historical research framing. The Real
Crypto Markets track was the one pursued, through Coinbase BTC-USD and ETH-USD
data. No comparison of the two original tracks is established, and the status
of the Crypto Prediction Markets track is not documented in this README.

See `research/strategy_vision.md` for the original research vision and
comparison framework.

## Current Research State

The completed causal trade-flow sequence includes expanded validation,
causal thresholds, duplicate-ID research deduplication,
delayed-canonicalization/actionability work, arithmetic-fork validation,
Delta-sensitivity, gross-edge v1, and ETH replication v2.

Gross-edge v1 is closed. ETH replication v2 is closed. The specific ETH LONG
Post-Entry Continuation H1 was rejected under the frozen v2 replication
design. These findings do not establish profitability or economic viability,
and they do not invalidate all trade-flow hypotheses.

Cost-stress/economic-feasibility research is not started and remains paused.

## Data and Historical Evidence Boundary

Historical trade identity was deterministically reconstructed.

Historical depth identity could not be deterministically reconstructed.
Depth research therefore has an established epoch boundary at
`2026-08-20 01:09:15 PDT`. Pre-epoch order-book state cannot be
deterministically recreated, and no full historical order-book reconstruction
is claimed.

## Current Boundaries

- No second exchange adapter is established by current evidence.
- No live execution or fill infrastructure is established.
- No profitability or economic-viability conclusion is claimed.


## Repository Navigation

Primary Crypto Domain documents:

- `zREADME.md` — current domain orientation and navigation.
- `zMISSION_CONTROL.md` — current operational and research status.
- `zROADMAP.md` — current roadmap status, with the original roadmap preserved
  as a superseded historical snapshot.
- `research/strategy_vision.md` — original research vision and comparison
  framework.

## Historical Research Vision

Crypto began as a vision-stage proposal intended to test whether Liquid
Research could extend beyond its original Prediction Markets work without
assuming that one market schema or research method generalized across
different market structures.

That original evidence-first design rationale remains useful historical
context. `research/strategy_vision.md` preserves the earlier research vision;
it does not override the current status, architecture boundary, research
state, or evidence limitations documented above.
