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

### Phase 2 — Research Infrastructure ✅ COMPLETE (2026-07-06)
Goal: Make it possible to observe the same market over multiple
days, not just today.

TERMINOLOGY NOTE (2026-07-10): entries below reference
"snapshot_file" as it was understood at the time each item was
completed — a raw Program A market snapshot filename. Following the
Prediction Markets Domain refactor (see zARCHITECTURE.md ADR-006),
Program B now reads a canonical output identified by
publication_id, and the log schema's "snapshot_file" column has
been renamed to publication_id throughout (both code and existing
log data). The historical entries below are left as originally
written to accurately reflect what was true at the time; treat
every "snapshot_file" reference below as historically accurate but
superseded by publication_id in the current codebase.

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
- Snapshot Change Detector ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/analysis/change_detector.py. Compares the
  latest observation against the immediately previous observation,
  per source (OBI, Near-Book) — NOT calendar "today vs yesterday",
  since diagnostics can be rerun against the same snapshot and the
  correct comparison is chronological, per source. Never compares
  OBI rows to Near-Book rows. Verified against the Fed rate market:
  OBI correctly showed has_change=True with real computed deltas;
  Near-Book correctly showed has_change=False with only one
  observation logged for that market. Uses get_market_history()
  exclusively — no direct CSV access, confirming the Historical
  Market View foundation supports real downstream analysis.
- Divergence Detection ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/analysis/divergence_detector.py. Measures
  divergence between the latest OBI observation and the latest
  Near-Book observation, paired only when they share the same
  snapshot_file — no forced comparison across different days.
  Reports raw_diff, absolute_diff, and sign_flip as plain
  measurements: no thresholds, no alerts, no historical maximum
  tracking, no percentile logic. Uses get_market_history()
  exclusively — no direct CSV access. Verified against three real
  cases: the Fed rate market (positive case, matching snapshot_file,
  real diff of 1.3559 with sign_flip=true), a Hormuz market
  (independent positive case, real diff of -0.3179 with
  sign_flip=false), and the China/Taiwan market (real negative case
  — no Near-Book observation exists at all, correctly returning
  has_comparable_pair=false without forcing a stale comparison).
- Stability Tracking ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/analysis/stability_tracker.py. Measures
  count, mean, min, max, range, standard deviation, and latest
  value for four independent sections: obi, near_obi,
  midpoint_obi_source, midpoint_near_source — no pairing between
  OBI and Near-Book rows. Measure only: no thresholds, no
  stable/unstable classification. Small-n behavior: count=0 gives
  all-None; count=1 gives mean/min/max/latest populated with
  range=0.0 and stddev=None; count>=2 computes everything including
  stddev. Uses get_market_history() exclusively — no direct CSV
  access. Verified against the Fed market (real count=3 for OBI
  with computed stddev, real count=1 for Near-OBI correctly showing
  range=0.0/stddev=None) and a Hormuz market (all four sections at
  count=3, fully populated, independently confirming correctness on
  a second market).

Done when: all four capabilities work correctly against the real
logs and have been spot-checked against at least one known
recurring market (e.g. the Fed rate markets, Hormuz markets).
✅ PHASE 2 COMPLETE (2026-07-06). All four capabilities
(Historical Market View, Snapshot Change Detector, Divergence
Detection, Stability Tracking) implemented and verified against
real recurring markets (Fed rate markets, Hormuz markets,
China/Taiwan). Program B is ready to move to Phase 3 — Research
Analytics & Review, which consumes this infrastructure to begin
answering the Core Research Questions above.

### Phase 3 — Research Analytics & Review ✅ COMPLETE (2026-07-06)

Goal: Turn Phase 2's capabilities into answers to the Core
Research Questions above.

- Market History Report ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/analysis/market_report.py. Consolidates all
  four Phase 2 modules (history, change detection, divergence
  detection, stability tracking) into one organized dict for a
  single market. The only new logic is observation_summary (counts,
  known snapshots, missing-source warning) — every other section
  is an unmodified pass-through of an existing Phase 2 function's
  output. No synthesis across sections, no combined score, no
  duplicated "latest" values at the top level. Verified against the
  Fed rate market (imbalanced source counts, no warning needed),
  a Hormuz market (fully populated across all sections), and the
  China/Taiwan market (correctly triggers
  missing_source_warning="No Near-Book observations exist for this
  market" and propagates that absence honestly through every
  downstream section rather than forcing a fake comparison).
- Market Observation Index ✅ COMPLETE (2026-07-06) — implemented
  in programs/program_b/analysis/recurring_markets.py as
  build_market_observation_index(). Renamed from "Recurring Market
  Tracker" during design review: recurrence and observation volume
  are different concepts (a market seen 12 times isn't more
  "recurring" than one seen twice — both are simply not one-off).
  Reports facts only per known slug: first_seen, last_seen,
  observation_count, snapshot_count, days_observed,
  sources_present. No threshold, no recurring boolean, no priority
  score. Sorted by last_seen descending. Verified against all 12
  known markets: Fed market (observation_count=4, snapshot_count=2,
  sources_present="near_book, obi"), Hormuz July 15
  (observation_count=6, sources_present="near_book, obi"),
  China/Taiwan (observation_count=2, sources_present="obi" only).
  Total rows matched len(list_known_slugs()) exactly.
- Presentation Layer ✅ STARTED (2026-07-06) — new folder
  programs/program_b/presentation/report_printer.py. Pure
  formatting only: no analysis logic, no CSV access, no
  classification, no thresholds. First function implemented:
  format_stability_table() renders a stability dict (from
  track_stability() or market_report.py's stability section) into
  a fixed-width plain text table. Verified against the Fed market's
  real stability data. Planned expansion (not yet built): one
  format_*() function per Phase 3 analysis output
  (format_observation_summary, format_latest_change,
  format_divergence, format_market_report,
  format_market_observation_index), all living in this same file
  so analysis modules stay purely computational and presentation
  stays in one dedicated place.
- Agreement Matrix ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/analysis/agreement_matrix.py as
  build_agreement_matrix() -> pd.DataFrame. Historical, cross-market
  view of whether OBI and Near-OBI share the same sign, for every
  (slug, snapshot_file) combination where both sources exist. Pairs
  the latest OBI row against the latest Near-Book row per
  snapshot_file — mirroring divergence_detector.py's "latest vs
  latest" philosophy, extended historically instead of just to the
  current moment. Zero is neutral (same_sign=False), consistent
  with divergence_detector.py's existing convention. Rows missing
  either source are excluded entirely, not forced. Verified: 11 of
  12 known markets contributed rows (China/Taiwan correctly
  excluded, zero Near-Book observations), zero duplicate
  (slug, snapshot_file) rows, no cartesian products. A plain-text
  formatter (format_agreement_matrix_table()) was added to
  presentation/report_printer.py and integrated into
  weekly_review.py as a new Section 6, kept deliberately separate
  from Section 4's existing "current, latest-only" divergence view
  — the two represent genuinely different facts (historical vs.
  latest) and are not interchangeable.
- Weekly Review Packaging ✅ COMPLETE (2026-07-06) — implemented in
  programs/program_b/presentation/weekly_review.py as
  build_weekly_review() -> str. Assembles six sections (Dataset
  Summary, Observation Index, Markets Missing One Source, Current
  Divergence Summary, Per-Market Detail, Historical Agreement
  Matrix) entirely from existing modules
  (build_market_observation_index(), build_market_report(),
  build_agreement_matrix(), format_stability_table(),
  format_agreement_matrix_table()) — no new statistics, no
  thresholds, no rankings, no recommendations, no generated
  research notes. Each
  market's report is built exactly once and reused across sections
  to avoid duplicated computation. Verified against the real
  12-market dataset: dataset summary matched real totals,
  China/Taiwan correctly isolated in the missing-source section,
  Fed market's stability table matched character-for-character
  against earlier verified output, and a whole-artifact sanity
  check confirmed exactly 12 per-market sections present with none
  skipped or duplicated.

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
---

## Research Checkpoints

Program B's Core Research Questions are answered through checkpoints
- Third checkpoint (2026-07-17, n=152 pairs, 64 markets): split
  updated again to 57.9%/42.1%. Across the three checkpoints
  observed so far, agreement declined as the dataset expanded.
  The market with the deepest history — previously the strongest
  example of stability in the dataset — showed a sharp reversal
  in its four most recent observations (all sign-flips) despite
  retaining a majority-agreement cumulative record, demonstrating
  that a market's apparent relationship between the two indicators
  can change materially over time. See
  research/validated_findings.md for the full analysis, including
  every individually re-examined n≥6 market.
- Fourth checkpoint (2026-07-20, n=190 pairs, 75 markets): triggered
  because the Fed no-change market reached n≥15, per the third
  checkpoint's predefined trigger. Aggregate split changed very
  little (57.9% to 57.4% same-sign) — the first checkpoint interval
  without a material decline, though whether this represents a
  plateau or one interval within a longer trend is not yet known.
  The Fed no-change market's newest observation returned to
  same-sign after five consecutive sign-flips, directly testing the
  open question posed at the third checkpoint — an initial
  reversion, not confirmation the earlier reversal has resolved.
  See research/validated_findings.md for the full analysis.

Next re-evaluation trigger: the Fed no-change market's newest
same-sign observation persisting or reverting across further
observations, total comparable pairs reaching at least 200, or
another market reaching n≥15.
- Fifth checkpoint (2026-07-21, n=246 pairs): triggered because
  total comparable pairs reached 246, exceeding the fourth
  checkpoint's n≥200 threshold. Aggregate split continued its
  modest decline (57.4% to 56.5% same-sign) — a continuation, not
  a structural break. The Fed no-change market's reversion toward
  agreement (first observed at the fourth checkpoint) persisted for
  one further same-sign observation before flipping again on its
  newest reading — confirming ongoing oscillation between regimes,
  not resolution in either direction. A data-quality limitation was
  identified: build_agreement_matrix()'s lexicographic sort does
  not reflect true chronological order once snapshot-style and
  dated publication_id formats coexist; a canonical observed_at_utc
  field is recommended before further automation. See
  research/validated_findings.md for the full analysis.

Next re-evaluation trigger: whether the Fed no-change market's
oscillation between agreement and disagreement continues, resolves,
or reveals a pattern; total comparable pairs reaching at least 300;
or another market reaching n≥15.
- Sixth checkpoint (2026-07-22, n=295 pairs, 89 markets): triggered
  because a second market (Fed increase) reached n≥15. Aggregate
  split changed only marginally despite ~20% dataset growth (56.5%
  to 55.6% same-sign) — the most notable finding of this checkpoint.
  The additional data did not materially change the aggregate
  measurements during this interval, although further checkpoints
  are required to determine whether this represents a durable
  plateau or continued movement around a slower trend. The Fed
  no-change market (now n=19, the deepest market ever recorded)
  added two further sign-flip observations after the fifth
  checkpoint, extending its current disagreement streak from one
  observation to three consecutive observations since its most
  recent same-sign reading at publication 20260720_080126. This is
  real evidence that disagreement can persist across multiple
  consecutive observations in this market, without establishing a
  durable regime shift. Two new shallow watch-list markets were
  flagged with perfect n=6 records (LeBron-76ers: 0/6 same-sign;
  Iranian regime fall: 6/6 same-sign), explicitly unconfirmed given
  this project's own prior evidence that shallow perfect records
  don't reliably predict deeper behavior. See
  research/validated_findings.md for the full analysis.

Next re-evaluation trigger: whether the aggregate's near-flat
movement persists or reverses at the next checkpoint; whether the
Fed no-change market's three-observation disagreement streak
continues or reverts; whether either new watch-list market's perfect
record holds as it deepens; total comparable pairs reaching at least
350; or a third market reaching n≥15.
- Seventh checkpoint (2026-07-25, n=371 pairs, 105 markets): triggered
  because total comparable pairs reached 371, exceeding the sixth
  checkpoint's n≥350 threshold, and a fourth market reached n≥15.
  Both aggregate divergence measures decreased slightly relative to
  checkpoint 6, reported without directional interpretation given
  the small magnitude and substantial simultaneous dataset growth.
  The more notable development is the continued accumulation of
  persistent, market-specific behavior in deeper-sampled markets —
  some markets (Hormuz July 31, Fed Increase) show sustained,
  consistent character at real depth, distinguishing an emerging
  pattern of market-level classification from aggregate statistics
  alone. A sign-flip was recorded in a later observed US Invade
  Iran record following a run of same-sign observations, reported
  cautiously given the unresolved chronological-ordering
  limitation. The LeBron-76ers perfect-disagreement record held at
  n=7. See research/validated_findings.md for the full analysis.

Next re-evaluation trigger: whether the small aggregate divergence
decrease continues, reverses, or was noise; whether US Invade
Iran's new flip is isolated or the start of a new pattern; whether
the LeBron-76ers perfect-disagreement record continues to hold at
greater depth; total comparable pairs reaching at least 450; or a
fifth market reaching n≥15.
- Eighth checkpoint (2026-07-28, n=466 pairs, 124 markets): triggered
  because both predefined checkpoint-7 thresholds were reached
  simultaneously (450+ pairs, a fifth market at n≥15). Aggregate
  moved modestly back toward agreement (55.5% to 56.9% same-sign),
  small relative to the substantial simultaneous dataset growth and
  not yet treated as a directional trend. The more informative
  finding is that market-level regimes remain heterogeneous and
  persistent: two correlated Hormuz markets (same underlying event,
  different deadlines) both show strong stability; US Invade Iran
  shows strong stability at n=19; Fed Increase remains the clearest
  persistent-disagreement example at n=21 (66.7% flip rate); and
  Fed No-Change, now the deepest market in the matrix at n=25,
  shifted notably back toward majority-agreement since the seventh
  checkpoint's near-even split. See research/validated_findings.md
  for the full analysis.

Next re-evaluation trigger: whether the aggregate's modest reversal
toward agreement continues, reverses, or remains ordinary variation;
whether Fed No-Change's shift toward agreement persists or
oscillates further; whether the two correlated Hormuz markets'
stability holds as independent markets reach comparable depth;
total comparable pairs reaching at least 550; or a sixth market
reaching n≥15.
- Ninth checkpoint (2026-08-02, n=575 pairs, 164 markets): triggered
  because total comparable pairs reached 575, exceeding the eighth
  checkpoint's 550-pair threshold. Aggregate moved up slightly
  relative to checkpoint 8 (56.9% to 56.2% same-sign) — a small
  reversal of the prior small reversal, still consistent with
  ordinary variation rather than a directional trend. Still five
  markets at n≥15, no sixth crossed this interval. Two already-
  stable markets deepened and strengthened: US Invade Iran (16/3
  at n=19 to 20/3 at n=23) and Hormuz August 31 (13/2 at n=15 to
  17/2 at n=19) — real evidence that at least some persistent-
  stability classifications hold up under continued observation.
  Fed Increase and Fed No-Change received no new observations this
  interval; their unchanged records are not new evidence either
  way. See research/validated_findings.md for the full analysis.

Next re-evaluation trigger: whether US Invade Iran and Hormuz
August 31's strengthening continues as they deepen further;
whether Fed Increase and Fed No-Change's classifications hold once
new observations resume; total comparable pairs reaching at least
700; or a sixth market reaching n≥15.
