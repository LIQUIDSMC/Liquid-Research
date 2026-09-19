# Crypto Domain — Mission Control

> This document tracks the current operational and research status of the
> L2 Crypto Domain. Shared Market Data Platform architecture and implementation
> are documented in `L1_CORE/market_data_platform/market_data/zROADMAP.md`.
> Crypto orientation and research boundaries are summarized in `zREADME.md`.

Last updated: 2026-09-18
Research state anchored to closure baseline: `a622e42`

## Current Status

- **Shared market-data infrastructure:** OPERATIONAL
- **Gross-edge v1:** CLOSED
- **ETH replication v2:** CLOSED
- **ETH LONG Post-Entry Continuation H1:** REJECTED UNDER FROZEN V2 DESIGN
- **Cost stress / economic feasibility:** NOT STARTED / PAUSED
- **Active experiment:** NONE

The ETH LONG result is specific to the frozen v2 replication design. It does
not establish a general rejection of trade-flow hypotheses.

## Architecture Boundary

L1 Market Data Platform owns shared, venue-agnostic acquisition, validation,
normalization, canonical storage, data-integrity contracts, and production
market-data infrastructure.

L2 Crypto is the current consumer of that shared infrastructure. Crypto does
not own the Market Data Platform or its production storage root.

## Operational State

Coinbase BTC-USD and ETH-USD trade and L2 depth acquisition is operational
through the shared L1 Market Data Platform.

Canonical production storage is SSD-backed at the fail-closed root:

`/mnt/lrs001/data/market_data_platform/canonical`

## Data Evidence Boundary

Historical trade identity was deterministically reconstructed.

Historical depth identity could not be deterministically reconstructed.
The depth research epoch begins at `2026-08-20 01:09:15 PDT`.
Pre-epoch order-book state cannot be deterministically recreated.

## Research State

The completed research sequence progressed through expanded validation,
causal thresholds, duplicate-ID research deduplication,
delayed-canonicalization/actionability work, arithmetic-fork validation,
Delta-sensitivity, gross-edge v1, and ETH replication v2.

Gross-edge v1 and ETH replication v2 are closed. Under the frozen v2
replication design, the specific ETH LONG Post-Entry Continuation H1 was
rejected on independent replication. This result does not establish a general
rejection of trade-flow hypotheses.

Cost-stress/economic-feasibility research has not started and remains paused.
No active experiment is currently in flight.

## Current Boundaries

- No second exchange adapter is established.
- No live execution or fill infrastructure is established.
- No profitability or economic-viability conclusion is claimed.
- Neither the fixed-horizon gross-edge research nor the Delta-sensitivity work
  establishes actual fills, executable edge, or transaction-cost viability.
- No next research experiment is selected or authorized by this document.

## Primary Documents

- `zREADME.md` — current Crypto Domain orientation and research boundaries.
- `zMISSION_CONTROL.md` — current operational and research status.
- `zROADMAP.md` — Crypto roadmap; described neutrally pending separate
  current-state reconciliation.
- `research/strategy_vision.md` — original research vision and framing.
- `L1_CORE/market_data_platform/market_data/zROADMAP.md` — shared Market Data
  Platform architecture and implementation record.

## Historical Milestone

Crypto began as a documentation-and-architecture proposal. Its original Phase 0
established the Domain documentation and research vision while deliberately
deferring implementation until evidence and prioritization justified further
work.

The Real Crypto Markets track was subsequently pursued through Coinbase
BTC-USD and ETH-USD data.

The original Mission Control snapshot is preserved verbatim below as historical
evidence. Its paths, filenames, phase status, priorities, and implementation
claims reflect the state recorded on 2026-07-10 and are **superseded**. Nothing
inside the snapshot should be interpreted as current status.

---

## Historical Snapshot — 2026-07-10 (SUPERSEDED)

# Crypto Domain — Mission Control

> This document tracks the Crypto Domain specifically. Platform-wide
> architecture lives in zARCHITECTURE.md. Platform-wide roadmap and
> program registry live in zROADMAP.md.

Last updated: 2026-07-10

## Phase Status

**Phase 0 — Documentation and Architecture: IN PROGRESS.**

No collectors, scanners, scoring logic, or exchange API integrations
exist. This is intentional. See README.md and
research/strategy_vision.md for the full reasoning.

## What Exists Today

- Folder structure (domains/crypto/, domains/crypto/research/)
- README.md — Domain overview, architectural placement, relationship
  to Prediction Markets Domain
- MISSION_CONTROL.md — this file
- zROADMAP.md — phased plan starting at documentation-only
- research/strategy_vision.md — full research vision: two-track
  comparison framework, six open questions, explicit deferral
  reasoning

## What Does NOT Exist Today

- No collector, scanner, scorer, or classifier
- No exchange API integration (Coinbase, Binance, Kraken, or any
  other)
- No canonical output
- No real or simulated trading of any kind
- No decision yet on which of the two research tracks (Crypto
  Prediction Markets vs. Real Crypto Markets) to investigate first

## Blocking Conditions

None technical. This is a resourcing and prioritization decision,
not an engineering blocker. Program A (toward its 100-trade
milestone) and Program B (its own ongoing microstructure research)
remain the platform's active research priorities. The Crypto Domain
proceeds to Phase 1 only when there's genuine capacity to do the
research properly, not because a placeholder exists.

## Done When (Phase 0)

- [x] domains/ top-level folder created
- [x] domains/crypto/ folder created
- [x] README.md captures Domain overview and architectural placement
- [x] MISSION_CONTROL.md captures current status (this file)
- [x] zROADMAP.md captures phased plan
- [x] research/strategy_vision.md captures the full research vision
- [x] zARCHITECTURE.md has a forward pointer to this Domain's
      existence

Phase 0 is complete once all items above are checked and committed.
Phase 1 (real research into the open questions in
research/strategy_vision.md) is future work, not started, no
committed timeline.

## Relationship to Program A and Program B

None. This Domain does not read from, write to, or depend on any
Program A or Program B file, dataset, or module. Its eventual
canonical output (if built) would be entirely independent, per
zARCHITECTURE.md's Domain/Program separation.
