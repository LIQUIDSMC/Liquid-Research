# Program B — Research Roadmap

This is a research roadmap, not an engineering roadmap. Every
phase below exists to answer a specific research question. If an
engineering task doesn't trace back to a question in this
document, it doesn't belong in Program B.

---

## Research Goal

Determine which order-book and market-microstructure indicators,
if any, provide Liquid Research with useful, stable signal for
market selection or entry timing — and understand how those
indicators actually behave before assuming any of them are useful.

---

## Core Research Questions

These are the reasons Program B exists. Everything below this
section is in service of answering these.

- Does OBI predict future midpoint movement?
- Does Near-Book OBI add information beyond Total-Book OBI, or is
  it redundant?
- Are large OBI/Near-OBI divergence events meaningful, or noise?
- Does indicator behavior differ across market categories
  (Geopolitical, Political, Macro/Economic, Crypto, Sports)?
- Does indicator stability vary with liquidity or spread quality?
- Does spread width affect indicator reliability?

None of these questions can be answered from a single day's
snapshot. All of them require historical data — which is why
Research Infrastructure (below) exists.

---

## Required Infrastructure

Per the platform principle "when choosing between collecting
better evidence and collecting more variables, prefer better
evidence first" (see zHANDOFF.md), Program B's infrastructure
priority is building the ability to observe existing indicators
over time, not adding new indicators.

### Phase 1 — Core Indicators ✅ COMPLETE, FROZEN

- Indicator 1: OBI / Micro-Price (indicators/obi.py)
- Indicator 2: Near-Book Depth Imbalance (indicators/near_book_depth.py)

Both indicators are frozen per the Frozen Experiments, Active
Platform principle. Methodology does not change until the review
cadence in README.md reaches a checkpoint.

### Phase 2 — Research Infrastructure 🔲 NOT STARTED

Goal: Make it possible to observe the same market over multiple
days, not just today.

- Historical Market View ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/analysis/history.py. Returns all logged
  observations for a market in LONG FORMAT (one row per real
  observation, tagged by source: obi or near_book), not the
  originally-envisioned wide/paired format. This changed during
  implementation: snapshot_file + slug is not a unique key (same-day
  diagnostic reruns produce genuine duplicate observations), so a
  wide merge risked cartesian products. Pairing OBI and Near-Book
  observations by nearest timestamp was considered and rejected as
  an unvalidated heuristic. Any future OBI-vs-Near-OBI comparison
  (e.g. a diff calculation) requires its own explicit pairing rule
  and belongs in a downstream consumer, not in this retrieval layer.
  See research/validated_findings.md or git history for the full
  reasoning if needed.
- Snapshot Change Detector — compare today's observation to
  yesterday's for the same market (simplest possible consumer of
  Historical Market View; build this next to validate the
  retrieval logic before anything more complex).
- Divergence Detection — flag when Near-OBI and Total-OBI diverge
  by more than any previously observed amount for that market.
- Stability Tracking — compute variance/stddev of an indicator's
  value for a given market across its observed history.

Done when: all four capabilities work correctly against the real
logs and have been spot-checked against at least one known
recurring market (e.g. the Fed rate markets, Hormuz markets).

### Phase 3 — Research Analytics & Review 🔲 NOT STARTED

Goal: Turn Phase 2's capabilities into answers to the Core
Research Questions above.

- Market History Report — per-market summary (days observed,
  average/median/min/max OBI and Near-OBI, largest divergence,
  average midpoint, largest midpoint move).
- Recurring Market Tracker — identify markets observed across many
  days and treat them as ongoing research subjects, tracking their
  full indicator + price history together.
- Agreement Matrix — for each day, does OBI sign match Near-OBI
  sign? Track agreement/disagreement frequency over time.
- Weekly Review Packaging — assemble the above into the existing
  review cadence (README.md) so review checkpoints require running
  a report, not manually inspecting CSVs.

Done when: at least one Core Research Question has a first-pass,
evidence-based answer (even if the answer is "inconclusive,
needs more data").

### Phase 4 — Presentation 🔲 NOT STARTED, NOT SCHEDULED

Goal: Make Phase 2/3 outputs easier to read.

- CLI dashboard summarizing Program B's current state.
- Cross-day visualization (text-based trend view, not graphics).

Do not begin until Phase 3 has produced real content worth
presenting. Revisit this phase only after that condition is met.

---

## Future Indicator Candidates

Per "prefer better evidence over more variables," these are
recorded but explicitly NOT next in line. Do not build until
Phase 2 and at least part of Phase 3 exist and have been used to
evaluate Indicators 1 and 2.

- Spread-normalized OBI — normalizes OBI by spread width so values
  are comparable across markets with different liquidity profiles.

---

## Cross-Reference: Potential Platform Generalization

The historical-retrieval pattern built in Phase 2 may generalize
to Program A's own "Price History Tracking" backlog item (see
zROADMAP.md, Platform Engineering Backlog) if that is ever built.
Not generalizing now — no second consumer exists yet — but worth
revisiting if/when Program A needs the same kind of time-series
retrieval.

---

## Three-Question Check Still Applies

Every indicator and every piece of infrastructure in this roadmap
is still governed by the platform's three-question check:
1. Is it mathematically correct?
2. Is it stable across many markets?
3. Does it improve a trading decision?

Infrastructure work (Phases 2-4) exists to help answer these
questions for Indicators 1 and 2 — it does not bypass them.