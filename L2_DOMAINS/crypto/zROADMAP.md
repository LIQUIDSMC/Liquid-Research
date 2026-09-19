# Crypto Domain — Roadmap

> This document records the current roadmap state for L2 Crypto.
> See `zMISSION_CONTROL.md` for detailed operational and research status,
> `zREADME.md` for Crypto orientation and boundaries, and
> `L1_CORE/market_data_platform/market_data/zROADMAP.md` for shared
> Market Data Platform authority.

Last updated: 2026-09-18
Research state anchored to closure baseline: `a622e42`

## Roadmap Status

### Completed

- Shared L1 Coinbase BTC-USD and ETH-USD collection and canonical storage are
  operational.
- The causal trade-flow research sequence is closed through fixed-horizon
  gross-edge v1 and ETH replication v2 at baseline `a622e42`. The specific
  ETH LONG Post-Entry Continuation H1 was rejected under the frozen v2 design;
  `zMISSION_CONTROL.md` records the scope of that result.

### Paused

- Cost-stress/economic-feasibility research is NOT STARTED / PAUSED.

### Open

- No next research experiment is selected or authorized by this document.

This roadmap does not commit to a timeline or to specific future deliverables.

Detailed current limitations and evidence boundaries are maintained in
`zMISSION_CONTROL.md`.

## Historical Roadmap Snapshot — SUPERSEDED

The original roadmap is preserved verbatim below as historical planning
evidence from the pre-migration layout recorded at `a930f37`.

Its phases, filenames, priorities, candidate venues, Program references,
cross-references, and implementation state are historical. Filenames such as
`README.md` and `MISSION_CONTROL.md` predate the current `z` prefixes.
Cross-references inside the snapshot resolve to the corresponding historical
state of those documents.

Nothing below this heading represents current status, sequencing, or
authorization.

# Crypto Domain — Roadmap

Status: Phase 0 in progress. No implementation exists.

This roadmap is intentionally shallow right now. It exists to give
future research a clear, sequenced path — not to commit to a
timeline or promise specific deliverables before the evidence
justifies them.

---

### Phase 0 — Documentation and Architecture (IN PROGRESS)

Goal: Give the Crypto Domain a permanent, well-documented home in
the repository before any implementation begins.

- README.md, MISSION_CONTROL.md, zROADMAP.md (this file),
  research/strategy_vision.md
- Forward pointer added to zARCHITECTURE.md's Open Design Targets
- No collectors, scanners, scoring logic, or API integrations

Done when: every item in MISSION_CONTROL.md's "Done When (Phase 0)"
checklist is complete and committed.

---

### Phase 1 — Research (NOT STARTED, NO TIMELINE)

Goal: Answer the six open questions in
research/strategy_vision.md with real evidence, before writing any
implementation code.

Candidate first steps (not commitments, not sequenced yet):
- Confirm whether real exchange data (Coinbase, Binance, Kraken, or
  similar) is accessible under terms consistent with Liquid
  Research's read-only, no-wallet, research-only constraints.
- Review what Polymarket crypto category data already exists
  passively via Program A's classifier, as a possible low-cost
  starting point for Track 1 research.
- Design the smallest possible experiment that could produce real
  evidence on any single comparison criterion (statistical
  significance, expectancy, consistency, liquidity, automatability,
  or engineering ROI) from research/strategy_vision.md.

This phase does not begin until there is genuine capacity to do it
properly — not automatically after Phase 0.

---

### Phase 2 — First Domain Producer (NOT STARTED, BLOCKED ON PHASE 1)

Goal: If and only if Phase 1 produces evidence justifying it, build
a minimal Crypto Domain producer, following the same architectural
principles as the Prediction Markets Domain (Domain owns selection,
publishes one canonical output).

Explicitly NOT assumed: that the existing canonical schema
(instrument_id, resolution_id, instrument_name, tradeability_score,
publication_id) transfers unchanged. Per zARCHITECTURE.md's Open
Design Targets, this is the first real test of whether that schema
generalizes — to be answered with evidence during this phase, not
assumed before it.

Blocked on: Phase 1 producing a real, evidence-based case for
building anything at all.

---

## What This Roadmap Deliberately Does Not Do

- Does not commit to which research track (Crypto Prediction
  Markets vs. Real Crypto Markets) gets built first.
- Does not commit to a timeline for any phase beyond Phase 0.
- Does not assume the Prediction Markets Domain's schema, folder
  structure, or Program pattern will look identical here.
- Does not compete with or take priority over Program A's or
  Program B's active research.
