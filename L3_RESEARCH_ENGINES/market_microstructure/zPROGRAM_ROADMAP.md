# LRS-2 — Market Microstructure Research Roadmap

This is a research roadmap, not an engineering roadmap. Every
phase below exists to answer a specific research question. If an
engineering task doesn't trace back to a question in this
document, it doesn't belong in LRS-2.

---

## Research Goal

Determine which order-book and market-microstructure indicators,
if any, provide Liquid Research with useful, stable signal for
market selection or entry timing — and understand how those
indicators actually behave before assuming any of them are useful.

---

## Core Research Questions

These are the reasons LRS-2 exists. Everything below this
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
evidence first" (see zHANDOFF.md), LRS-2's infrastructure
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
LRS-2 now reads a canonical output identified by
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
China/Taiwan). LRS-2 was then ready to move to Phase 3 — Research
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

- CLI dashboard summarizing LRS-2's current state.
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
to another engine or domain that needs the same kind of time-series
retrieval. No generalization is authorized here; shared extraction
should wait for a demonstrated second consumer.

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
- Tenth checkpoint (2026-08-05, n=720 pairs, 199 markets): triggered
  because total comparable pairs reached 720, exceeding the ninth
  checkpoint's 700-pair threshold. Aggregate measurements changed
  only marginally (56.2% to 56.5% same-sign) despite ~25% growth in
  comparable pairs, continuing the small back-and-forth pattern
  observed since the sixth checkpoint, still consistent with
  ordinary variation. Still five markets at n≥15, no sixth crossed
  this interval. US Invade Iran deepened and strengthened again
  (20/3 at n=23 to 24/3 at n=27), now showing genuine, progressive
  strengthening across three consecutive checkpoints (84.2% to
  87.0% to 88.9% same-sign) — the most durable single-market
  stability evidence gathered so far. Hormuz August 31 deepened
  further (17/2 at n=19 to 20/3 at n=23) and remained strongly
  agreement-dominated, though its same-sign proportion declined
  slightly (89.5% to 87.0%) rather than strengthening. Hormuz July
  31, Fed Increase, and Fed No-Change received no new observations
  this interval. Data generated by the Pi's automated daily runs
  (2026-08-03 through 2026-08-05). See research/validated_findings.md
  for the full analysis.

Next re-evaluation trigger: whether US Invade Iran's strengthening
trend continues or eventually plateaus/reverts; whether Hormuz
August 31's slight decline this interval continues, reverses, or
was noise; whether Fed Increase, Fed No-Change, and Hormuz July
31's classifications hold once new observations resume; total
comparable pairs reaching at least 900; or a sixth market reaching
n≥15.
- Eleventh checkpoint (2026-08-13, n=744 pairs, 210 markets): triggered
  because a sixth market (Clarity Act) reached n≥15, meeting the
  alternate trigger condition; total pairs at 744 had not yet reached
  the 900-pair threshold. Aggregate same-sign rate held at a rounded
  56.5% relative to checkpoint 10, with the underlying proportion
  moving only fractionally (56.53% to 56.45%). Half of the six deep
  markets received zero new observations this interval. US Invade
  Iran strengthened again (24/3 at n=27 to 25/3 at n=28), now 89.3%
  same-sign across four consecutive checkpoints — the strongest
  sustained single-market stability record observed so far in
  Program B. Hormuz August 31 received one new observation, a
  sign-flip, moving its ratio from 20/3 at n=23 to 20/4 at n=24 —
  a real but modest single-observation data point, not treated as a
  reversal. Clarity Act newly reached n≥15 at 10/5 (66.7% same-sign),
  a moderately-stable, genuinely shallow new addition to the deep-
  market roster. This checkpoint used a frozen, SHA-256-verified
  snapshot of the Pi's research data captured 2026-08-12 after the
  researcher's return from travel, analyzed independently of the
  concurrent Mac-side L0-L4 repository restructure. See
  research/validated_findings.md (now L4_KNOWLEDGE/validated_findings.md)
  for the full analysis.

Next re-evaluation trigger: whether US Invade Iran's strengthening
trend continues or eventually plateaus/reverts; whether Hormuz
August 31's single-observation decline this interval continues,
reverses, or was noise; whether Clarity Act's moderate stability
holds or shifts as it deepens; whether Fed Increase, Fed No-Change,
and Hormuz July 31's classifications hold once new observations
resume; total comparable pairs reaching at least 900; or a seventh
market reaching n≥15.
- Twelfth checkpoint (2026-08-28, n=1,463 pairs, 388 markets): triggered
  by both conditions simultaneously — total comparable pairs reached
  1,463, far exceeding the 900-pair threshold, and the deep-market
  roster grew to 18 markets at n>=15, well past the 7-market alternate
  trigger. Aggregate same-sign rate moved to 59.26% (867/1,463), up
  from checkpoint 11's 56.5% — a real, more notable shift than the
  marginal back-and-forth observed across checkpoints 9-11, though
  still modest in absolute terms.

  US Invade Iran continued its multi-checkpoint stability trend,
  strengthening further to 91.5% same-sign at n=47 (up from 89.3% at
  n=28), now spanning five consecutive checkpoints of sustained high
  agreement -- the most durable single-market record in the program's
  history.

  Two markets newly reached perfect same-sign agreement at meaningful
  sample size: "Will the Iranian regime fall by the end of 2026"
  (100.0%, n=16) and "Putin out before 2027" (100.0%, n=19).

  A distinct cluster of markets showed consistent disagreement rather
  than agreement, worth recording explicitly rather than treating as
  noise: "Will the Fed decrease interest rates by 25 bps after the
  September 2026 meeting" (25.8% same-sign, n=31), "Will Renan Santos
  win the 2026 Brazilian presidential election" (28.6%, n=21), and
  "Will the Fed increase interest rates by 25 bps after the July 2026
  meeting" (33.3%, n=21) -- all large-n samples showing sign-flip
  dominance rather than agreement, a real pattern distinct from the
  majority of deep markets.

  Twelve markets newly crossed the n>=15 threshold since checkpoint 11
  (previously six: US Invade Iran, Hormuz Aug 31, Hormuz Jul 31, Fed
  Increase Jul, Fed No-Change Jul, Clarity Act). Full deep-market
  roster (n>=15) and same-sign rates:

  | Market | n | Same-sign | % |
  |---|---:|---:|---:|
  | Will the US invade Iran before 2027? | 47 | 43 | 91.5% |
  | Strait of Hormuz traffic returns to normal by August 31 | 37 | 29 | 78.4% |
  | No change in Fed interest rates after Sept 2026 meeting | 33 | 31 | 93.9% |
  | Strait of Hormuz traffic returns to normal by December 31 | 32 | 25 | 78.1% |
  | Clarity Act signed into law in 2026 | 32 | 21 | 65.6% |
  | Strait of Hormuz traffic returns to normal by September 30 | 31 | 24 | 77.4% |
  | Fed decrease 25bps (Sept 2026 meeting) | 31 | 8 | 25.8% |
  | Fed increase 25bps (Sept 2026 meeting) | 31 | 19 | 61.3% |
  | No change in Fed interest rates after July 2026 meeting | 25 | 15 | 60.0% |
  | Will Renan Santos win 2026 Brazilian presidential election? | 21 | 6 | 28.6% |
  | Fed increase 25bps (July 2026 meeting) | 21 | 7 | 33.3% |
  | US announces end of Iranian blockade by Aug 31, 2026 | 21 | 16 | 76.2% |
  | Putin out before 2027 | 19 | 19 | 100.0% |
  | Fed rate hike in 2026 | 19 | 11 | 57.9% |
  | Israel x Iran ceasefire continues through August 31 | 17 | 9 | 52.9% |
  | Will the Iranian regime fall by end of 2026? | 16 | 16 | 100.0% |
  | Israel x Iran ceasefire continues through August 15 | 16 | 7 | 43.8% |
  | Strait of Hormuz traffic returns to normal by July 31 | 15 | 14 | 93.3% |

Next re-evaluation trigger: whether US Invade Iran's stability
continues past 91.5% or begins to plateau; whether the Fed-related
disagreement cluster persists or reverses as those markets deepen;
whether the two newly-perfect markets (Iranian regime fall, Putin out)
maintain 100% as they accumulate more observations; total comparable
pairs reaching at least 2,000; or additional markets reaching n>=15.

- Thirteenth checkpoint (2026-09-09, n=1,762 pairs, 468 markets): triggered
  by the alternate condition -- the deep-market roster grew to 21 markets
  at n>=15, exceeding checkpoint 12's roster of 18; total comparable pairs
  reached 1,762, still short of the 2,000-pair threshold. The aggregate
  same-sign rate was therefore stable over this interval despite 299
  additional comparable pairs, moving only from 59.26% (867/1,463) to
  58.97% (1,039/1,762). This describes stability of the observed aggregate
  rate only; it does not establish predictive value.

  US Invade Iran continued strengthening, now 92.6% same-sign at n=54
  (up from 91.5% at n=47), extending its multi-checkpoint stability
  record. Both previously-perfect markets held: "Putin out before 2027"
  remained 100.0% (now n=22, up from n=19) and "Will the Iranian regime
  fall before 2027" remained 100.0% (now n=17, up from n=16).

  Checkpoint 12's disagreement cluster did not move uniformly. Two of
  the three members received no new observations this interval and are
  therefore unchanged rather than newly confirmed: "Fed decrease 25bps
  (September 2026 meeting)" remained at 25.8% (8/31, same n), and "Fed
  increase 25bps (July 2026 meeting)" remained at 33.3% (7/21, same n).
  The third member moved materially: "Will Renan Santos win the 2026
  Brazilian presidential election" rose from 28.6% (6/21) to 37.9%
  (11/29). All three remain below 40% same-sign, but their behavior
  over this interval was not uniform. They should therefore continue
  to be tracked individually rather than treated as moving uniformly.

  Exactly three markets newly crossed the n>=15 threshold since
  checkpoint 12: "Will Bitcoin dip to $45,000 by December 31, 2026?"
  (86.7%, n=15), "Will Luiz Inácio Lula da Silva win the 2026 Brazilian
  presidential election?" (41.2%, n=17), and "Will United Russia (ER)
  gain the most seats in the next Russian parliamentary election?"
  (75.0%, n=20).

  Full deep-market roster (n>=15) and same-sign rates:

  | Market | n | Same-sign | % |
  |---|---:|---:|---:|
  | Will the US invade Iran before 2027? | 54 | 50 | 92.6% |
  | No change in Fed interest rates after Sept 2026 meeting | 45 | 41 | 91.1% |
  | Fed increase 25bps (Sept 2026 meeting) | 43 | 27 | 62.8% |
  | Clarity Act signed into law in 2026 | 42 | 28 | 66.7% |
  | Strait of Hormuz traffic returns to normal by September 30 | 40 | 28 | 70.0% |
  | Strait of Hormuz traffic returns to normal by December 31 | 39 | 29 | 74.4% |
  | Strait of Hormuz traffic returns to normal by August 31 | 37 | 29 | 78.4% |
  | Fed decrease 25bps (Sept 2026 meeting) | 31 | 8 | 25.8% |
  | Will Renan Santos win 2026 Brazilian presidential election? | 29 | 11 | 37.9% |
  | No change in Fed interest rates after July 2026 meeting | 25 | 15 | 60.0% |
  | Fed rate hike in 2026 | 25 | 13 | 52.0% |
  | Putin out before 2027 | 22 | 22 | 100.0% |
  | Fed increase 25bps (July 2026 meeting) | 21 | 7 | 33.3% |
  | US announces end of Iranian blockade by Aug 31, 2026 | 21 | 16 | 76.2% |
  | Will United Russia (ER) gain the most seats in the next Russian parliamentary election? | 20 | 15 | 75.0% |
  | Will Luiz Inácio Lula da Silva win 2026 Brazilian presidential election? | 17 | 7 | 41.2% |
  | Will the Iranian regime fall before 2027? | 17 | 17 | 100.0% |
  | Israel x Iran ceasefire continues through August 31 | 17 | 9 | 52.9% |
  | Israel x Iran ceasefire continues through August 15 | 16 | 7 | 43.8% |
  | Strait of Hormuz traffic returns to normal by July 31 | 15 | 14 | 93.3% |
  | Will Bitcoin dip to $45,000 by December 31, 2026? | 15 | 13 | 86.7% |

Next re-evaluation trigger: whether US Invade Iran maintains its >90%
same-sign pattern as n increases; whether the three disagreement-
cluster markets move independently or reconverge; whether Putin-out
and Iranian-regime-fall maintain 100% as they deepen further; whether
the three newly-deep markets' rates stabilize or shift as they
accumulate more observations; total comparable pairs reaching at least
2,000; or additional markets reaching n>=15.

- Fourteenth checkpoint (2026-09-24, n=2,213 pairs, 568 markets): triggered
  by both population conditions simultaneously -- total comparable pairs
  reached 2,213, exceeding the 2,000-pair threshold, and the deep-market
  roster grew from 21 to 26 markets at n>=15. All 21 checkpoint-13 deep
  markets remained in the deep roster, and exactly five additional markets
  crossed the threshold. The aggregate same-sign rate increased from 58.97%
  (1,039/1,762) to 60.14% (1,331/2,213), a change of +1.17 percentage
  points across 451 additional comparable pairs. The 451 added pairs
  contained 292 same-sign observations (64.75%). These figures describe
  the observed interval only; no frozen statistical threshold has been
  established for classifying this movement as a trend, stability,
  instability, or predictive signal.

  US Invade Iran added 14 observations and remained above the checkpoint-13
  >90% watch level, moving from 92.6% same-sign (50/54) to 91.2% (62/68).
  The rate therefore declined by 1.4 percentage points while the underlying
  record added 12 same-sign and two sign-flip observations. Putin out before
  2027 extended its perfect record from 22/22 to 29/29, and Iranian regime
  fall extended its perfect record from 17/17 to 20/20. These remain
  descriptive persistence records and do not establish predictive value.

  Checkpoint 13's three low-agreement watch markets again did not move as
  a uniform cluster. Fed decrease 25bps (September 2026 meeting) received
  no new observations and remained 25.8% (8/31), while Fed increase 25bps
  (July 2026 meeting) also received no new observations and remained 33.3%
  (7/21). Renan Santos added five observations and moved only slightly from
  37.9% (11/29) to 38.2% (13/34). They should therefore continue to be
  tracked individually rather than treated as a uniformly moving cluster.

  All three markets that had newly reached n>=15 at checkpoint 13 gained
  additional depth. Bitcoin dip to $45,000 moved from 86.7% (13/15) to
  79.2% (19/24); Luiz Inácio Lula da Silva moved from 41.2% (7/17) to
  33.3% (9/27); and United Russia moved from 75.0% (15/20) to 77.4%
  (24/31). Their interval movements were not uniform.

  One additional holdover movement was notable descriptively: Strait of
  Hormuz traffic returns to normal by September 30 added five observations,
  all sign-flips, moving from 70.0% same-sign (28/40) to 62.2% (28/45).
  This is recorded as an observed interval change only; no mechanism or
  predictive interpretation is inferred from it.

  Exactly five markets newly crossed the n>=15 threshold since checkpoint
  13: "Will Flávio Bolsonaro win the 2026 Brazilian presidential election?"
  (65.4%, n=26), "US announces end of Iranian blockade by September 30,
  2026?" (100.0%, n=23), "Israel x Iran ceasefire continues through
  September 30?" (78.9%, n=19), "Israel closes its airspace by September
  30?" (58.8%, n=17), and "Will China invade Taiwan by end of 2026?"
  (58.8%, n=17). No checkpoint-13 deep market fell below the n>=15 roster.

  Full deep-market roster (n>=15) and same-sign rates:

  | Market | n | Same-sign | % |
  |---|---:|---:|---:|
  | Will the U.S. invade Iran before 2027? | 68 | 62 | 91.2% |
  | Clarity Act (H.R.3633) signed into law in 2026? | 56 | 36 | 64.3% |
  | Will there be no change in Fed interest rates after the September 2026 meeting? | 50 | 45 | 90.0% |
  | Strait of Hormuz traffic returns to normal by December 31? | 49 | 39 | 79.6% |
  | Will the Fed increase interest rates by 25 bps after the September 2026 meeting? | 48 | 31 | 64.6% |
  | Strait of Hormuz traffic returns to normal by September 30? | 45 | 28 | 62.2% |
  | Strait of Hormuz traffic returns to normal by August 31? | 37 | 29 | 78.4% |
  | Will Renan Santos win the 2026 Brazilian presidential election? | 34 | 13 | 38.2% |
  | Will United Russia (ER) gain the most seats in the next Russian parliamentary election? | 31 | 24 | 77.4% |
  | Will the Fed decrease interest rates by 25 bps after the September 2026 meeting? | 31 | 8 | 25.8% |
  | Fed rate hike in 2026? | 30 | 18 | 60.0% |
  | Putin out as President of Russia by December 31, 2026? | 29 | 29 | 100.0% |
  | Will Luiz Inácio Lula da Silva win the 2026 Brazilian presidential election? | 27 | 9 | 33.3% |
  | Will Flávio Bolsonaro win the 2026 Brazilian presidential election? | 26 | 17 | 65.4% |
  | Will there be no change in Fed interest rates after the July 2026 meeting? | 25 | 15 | 60.0% |
  | Will Bitcoin dip to $45,000 by December 31, 2026? | 24 | 19 | 79.2% |
  | US announces end of Iranian blockade by September 30, 2026? | 23 | 23 | 100.0% |
  | US announces end of Iranian blockade by August 31, 2026? | 21 | 16 | 76.2% |
  | Will the Fed increase interest rates by 25 bps after the July 2026 meeting? | 21 | 7 | 33.3% |
  | Will the Iranian regime fall before 2027? | 20 | 20 | 100.0% |
  | Israel x Iran ceasefire continues through September 30? | 19 | 15 | 78.9% |
  | Israel closes its airspace by September 30? | 17 | 10 | 58.8% |
  | Israel x Iran ceasefire continues through August 31? | 17 | 9 | 52.9% |
  | Will China invade Taiwan by end of 2026? | 17 | 10 | 58.8% |
  | Israel x Iran ceasefire continues through August 15? | 16 | 7 | 43.8% |
  | Strait of Hormuz traffic returns to normal by July 31? | 15 | 14 | 93.3% |

  A previously explored magnitude-only |top5_skew| diagnostic was not
  repeated at this checkpoint because its exact test mechanics were not
  retained in checkpoint repository authority. Reconstructing those
  mechanics from conversational memory would constitute a new methodology
  specification rather than an unchanged frozen replication.

Next re-evaluation trigger: whether US Invade Iran remains above 90% as its
sample deepens; whether Putin-out and Iranian-regime-fall retain their
100% records; whether the individually tracked low-agreement markets
remain low or diverge further; whether the five newly-deep markets'
observed rates persist or shift with additional observations; total
comparable pairs reaching at least 2,500; or additional markets reaching
n>=15. The 2,500-pair threshold is the next checkpoint collection trigger,
not a statistical significance threshold.

- Fifteenth checkpoint (2026-09-27, n=2,313 pairs, 595 markets): triggered
  by the alternate population condition -- the deep-market roster grew from
  26 to 27 markets at n>=15. Total comparable pairs reached 2,313, still
  below the 2,500-pair trigger. All 26 checkpoint-14 deep markets remained
  in the deep roster, and exactly one additional market crossed the threshold:
  "Will the US confirm that aliens exist before 2027?" at 46.7% same-sign
  (7/15).

  The aggregate same-sign rate increased from 60.14% (1,331/2,213) to
  60.48% (1,399/2,313), a change of +0.34 percentage points across 100
  additional comparable pairs. Those 100 added pairs contained 68 same-sign
  observations (68.00%). These figures describe the observed interval only;
  no frozen statistical threshold has been established for classifying this
  movement as a trend, stability, instability, or predictive signal.

  US Invade Iran added four observations, all same-sign, moving from 91.2%
  (62/68) to 91.7% (66/72). Putin out before 2027 remained 100.0% at 29/29,
  and Iranian regime fall remained 100.0% at 20/20. These are descriptive
  persistence records only and do not establish predictive value.

  The individually tracked low-agreement markets did not provide a new
  uniform-cluster result. Fed decrease 25bps after the September 2026 meeting
  remained 25.8% (8/31), Fed increase 25bps after the July 2026 meeting
  remained 33.3% (7/21), and Renan Santos remained 38.2% (13/34).

  Several other checkpoint-14 deep markets accumulated observations.
  Strait of Hormuz normal by December 31 moved from 79.6% (39/49) to
  81.1% (43/53), adding four same-sign observations. Luiz Inácio Lula da
  Silva moved from 33.3% (9/27) to 29.0% (9/31), adding four observations
  without an additional same-sign observation. Flávio Bolsonaro moved from
  65.4% (17/26) to 62.1% (18/29). US end of Iranian blockade by September
  30 extended its perfect record from 23/23 to 27/27. Israel x Iran ceasefire
  through September 30 moved from 78.9% (15/19) to 76.2% (16/21), and China
  invade Taiwan by end of 2026 moved from 58.8% (10/17) to 63.2% (12/19).
  These interval movements were heterogeneous and are recorded descriptively.

  Full deep-market roster (n>=15) and same-sign rates:

  | Market | n | Same-sign | % |
  |---|---:|---:|---:|
  | Will the U.S. invade Iran before 2027? | 72 | 66 | 91.7% |
  | Clarity Act (H.R.3633) signed into law in 2026? | 57 | 36 | 63.2% |
  | Strait of Hormuz traffic returns to normal by December 31? | 53 | 43 | 81.1% |
  | Will there be no change in Fed interest rates after the September 2026 meeting? | 50 | 45 | 90.0% |
  | Will the Fed increase interest rates by 25 bps after the September 2026 meeting? | 48 | 31 | 64.6% |
  | Strait of Hormuz traffic returns to normal by September 30? | 45 | 28 | 62.2% |
  | Strait of Hormuz traffic returns to normal by August 31? | 37 | 29 | 78.4% |
  | Will Renan Santos win the 2026 Brazilian presidential election? | 34 | 13 | 38.2% |
  | Will Luiz Inácio Lula da Silva win the 2026 Brazilian presidential election? | 31 | 9 | 29.0% |
  | Will the Fed decrease interest rates by 25 bps after the September 2026 meeting? | 31 | 8 | 25.8% |
  | Will United Russia (ER) gain the most seats in the next Russian parliamentary election? | 31 | 24 | 77.4% |
  | Fed rate hike in 2026? | 30 | 18 | 60.0% |
  | Putin out as President of Russia by December 31, 2026? | 29 | 29 | 100.0% |
  | Will Flávio Bolsonaro win the 2026 Brazilian presidential election? | 29 | 18 | 62.1% |
  | US announces end of Iranian blockade by September 30, 2026? | 27 | 27 | 100.0% |
  | Will there be no change in Fed interest rates after the July 2026 meeting? | 25 | 15 | 60.0% |
  | Will Bitcoin dip to $45,000 by December 31, 2026? | 24 | 19 | 79.2% |
  | Israel x Iran ceasefire continues through September 30? | 21 | 16 | 76.2% |
  | US announces end of Iranian blockade by August 31, 2026? | 21 | 16 | 76.2% |
  | Will the Fed increase interest rates by 25 bps after the July 2026 meeting? | 21 | 7 | 33.3% |
  | Will the Iranian regime fall before 2027? | 20 | 20 | 100.0% |
  | Will China invade Taiwan by end of 2026? | 19 | 12 | 63.2% |
  | Israel closes its airspace by September 30? | 17 | 10 | 58.8% |
  | Israel x Iran ceasefire continues through August 31? | 17 | 9 | 52.9% |
  | Israel x Iran ceasefire continues through August 15? | 16 | 7 | 43.8% |
  | Strait of Hormuz traffic returns to normal by July 31? | 15 | 14 | 93.3% |
  | Will the US confirm that aliens exist before 2027? | 15 | 7 | 46.7% |

  The previously explored magnitude-only |top5_skew| diagnostic was not
  repeated because its exact mechanics remain absent from checkpoint
  repository authority. No new methodology was reconstructed for CP15.

Next re-evaluation trigger: whether US Invade Iran remains above 90% as its
sample deepens; whether Putin-out, Iranian-regime-fall, and the September-30
Iranian-blockade market retain their 100% records; whether the individually
tracked low-agreement markets remain low or move independently; whether the
newly-deep US-confirm-aliens market shifts materially as it gains observations;
total comparable pairs reaching at least 2,500; or additional markets reaching
n>=15. The 2,500-pair threshold remains a checkpoint collection trigger, not
a statistical significance threshold.


CP15 provenance addendum (2026-09-28; documentation only, no CP15
result changed):

  Checkpoint 15 statistics were computed from an immutable bounded
  snapshot of the LRS-2 logs, not from the live files:

  - Snapshot ID: 20260927T120247.079559Z
  - Source host: liquid-pi (Pi3)
  - Source/code commit: 601b813046c79d6ae0ec2511b56521dc23a8e29f
  - Verified SHA-256 (snapshot CSVs, matched against the manifest):
      near_book_depth_log.csv:
        930f3939f081b24518e6dac1a832521a83d953b8ad1fe9f225482f0f7cb395f6
      obi_log.csv:
        298ec5be0cdfb67854b22b05d3a532823d26c1c6886cfa36b3a5557decab86fe
  - Computation: the canonical build_agreement_matrix() was run on
    liquid-pi5 (Pi5) against this snapshot as verification compute
    only.
  - Pi3 remained the sole authoritative live collector and writer.
    No analytical or runtime authority was transferred to Pi5.
  - No methodology change. This was the first checkpoint run through
    the bounded Pi3-to-Pi5 snapshot path.
  - The CP15 figures describe this snapshot, not the later live
    sentinel readings.

  The 27th deep market was identified from the canonical matrix on
  this snapshot. A date-boundary comparison (rows on or before
  2026-09-24) gave 2,251 pairs rather than CP14's recorded 2,213, so
  it is corroborating evidence only and is not an exact
  reconstruction of the CP14 population.

  CP16 trigger, stated mechanically from the frozen CP15 baseline
  (2,313 comparable pairs, 27 markets at n>=15): total comparable
  pairs >= 2,500, OR the count of markets at n>=15 exceeds 27. The
  2,500 pair milestone was set before CP15 and is retained; it was
  not chosen from CP15 results. This supersedes the looser wording
  "additional markets reaching n>=15" above. The qualitative watch
  items recorded in CP15 are unchanged.


- Sixteenth checkpoint (2026-10-01, n=2,431 pairs, 630 markets): triggered
  naturally by the alternate population condition. At the scheduled 06:05 PDT
  Sentinel run, the canonical live calculation reported 2,431 comparable pairs
  and 29 markets at n>=15. The 2,500-pair condition had not fired; the
  deep-market condition fired because 29 exceeded the frozen CP15 baseline of
  27.

  Checkpoint analysis used an immutable bounded snapshot captured later that
  day. The canonical build_agreement_matrix() calculation on that frozen
  population produced 2,431 comparable pairs across 630 markets, with 29
  markets at n>=15, 1,469 same-sign pairs, and a 60.43% aggregate same-sign
  rate (1,469/2,431). The maximum per-market sample was n=75.

  Relative to CP15, the checkpoint population increased by 118 comparable
  pairs, 35 markets, two deep markets, and 70 same-sign observations. The
  aggregate same-sign rate moved from 60.48% (1,399/2,313) to 60.43%
  (1,469/2,431), a change of -0.06 percentage points using the underlying
  checkpoint fractions. The 118 additional comparable pairs contained 70
  same-sign observations (59.32%). These figures are descriptive only. No
  frozen statistical threshold has been established for classifying this
  movement as a trend, stability, instability, or predictive signal.

  The CP15-to-CP16 deep-market identity audit used canonical slug identity.
  All 27 CP15 deep markets remained in the roster, exactly two additional
  markets crossed n>=15, and no CP15 deep market was lost. The two newly-deep
  markets were:

  - Will the Fed increase interest rates by 25 bps after the October 2026
    meeting? -- 46.7% same-sign (7/15).
  - Will there be no change in Fed interest rates after the October 2026
    meeting? -- 86.7% same-sign (13/15).

  Several previously tracked records changed as their samples deepened. US
  Invade Iran moved from 91.7% (66/72) to 92.0% (69/75). Putin out before
  2027 moved from 100.0% (29/29) to 96.9% (31/32). Iranian regime fall
  remained 100.0%, moving from 20/20 to 21/21. US end of Iranian blockade by
  September 30 moved from 100.0% (27/27) to 96.6% (28/29). Flávio Bolsonaro
  moved from 62.1% (18/29) to 54.5% (18/33), while Luiz Inácio Lula da Silva
  moved from 29.0% (9/31) to 32.4% (11/34). These movements are heterogeneous
  descriptive observations and do not establish predictive value.

  Full deep-market roster (n>=15) and same-sign rates:

  | Market | n | Same-sign | % |
  |---|---:|---:|---:|
  | Will the U.S. invade Iran before 2027? | 75 | 69 | 92.0% |
  | Clarity Act (H.R.3633) signed into law in 2026? | 59 | 38 | 64.4% |
  | Strait of Hormuz traffic returns to normal by December 31? | 55 | 45 | 81.8% |
  | Will there be no change in Fed interest rates after the September 2026 meeting? | 50 | 45 | 90.0% |
  | Will the Fed increase interest rates by 25 bps after the September 2026 meeting? | 48 | 31 | 64.6% |
  | Strait of Hormuz traffic returns to normal by September 30? | 45 | 28 | 62.2% |
  | Strait of Hormuz traffic returns to normal by August 31? | 37 | 29 | 78.4% |
  | Will Luiz Inácio Lula da Silva win the 2026 Brazilian presidential election? | 34 | 11 | 32.4% |
  | Will Renan Santos win the 2026 Brazilian presidential election? | 34 | 13 | 38.2% |
  | Will Flávio Bolsonaro win the 2026 Brazilian presidential election? | 33 | 18 | 54.5% |
  | Putin out as President of Russia by December 31, 2026? | 32 | 31 | 96.9% |
  | Will the Fed decrease interest rates by 25 bps after the September 2026 meeting? | 31 | 8 | 25.8% |
  | Will United Russia (ER) gain the most seats in the next Russian parliamentary election? | 31 | 24 | 77.4% |
  | Fed rate hike in 2026? | 30 | 18 | 60.0% |
  | US announces end of Iranian blockade by September 30, 2026? | 29 | 28 | 96.6% |
  | Will there be no change in Fed interest rates after the July 2026 meeting? | 25 | 15 | 60.0% |
  | Will Bitcoin dip to $45,000 by December 31, 2026? | 24 | 19 | 79.2% |
  | Israel x Iran ceasefire continues through September 30? | 22 | 16 | 72.7% |
  | US announces end of Iranian blockade by August 31, 2026? | 21 | 16 | 76.2% |
  | Will China invade Taiwan by end of 2026? | 21 | 14 | 66.7% |
  | Will the Fed increase interest rates by 25 bps after the July 2026 meeting? | 21 | 7 | 33.3% |
  | Will the Iranian regime fall before 2027? | 21 | 21 | 100.0% |
  | Israel closes its airspace by September 30? | 17 | 10 | 58.8% |
  | Israel x Iran ceasefire continues through August 31? | 17 | 9 | 52.9% |
  | Israel x Iran ceasefire continues through August 15? | 16 | 7 | 43.8% |
  | Strait of Hormuz traffic returns to normal by July 31? | 15 | 14 | 93.3% |
  | Will the Fed increase interest rates by 25 bps after the October 2026 meeting? | 15 | 7 | 46.7% |
  | Will the US confirm that aliens exist before 2027? | 15 | 7 | 46.7% |
  | Will there be no change in Fed interest rates after the October 2026 meeting? | 15 | 13 | 86.7% |

  The previously explored magnitude-only |top5_skew| diagnostic was not
  repeated because its exact mechanics remain absent from checkpoint
  repository authority. No new methodology was reconstructed for CP16.

  CP16 provenance:

  - Natural trigger: 2026-10-01 06:05 PDT, with 2,431 comparable pairs and
    29 markets at n>=15.
  - Snapshot ID: 20261002T030715.305900771Z.
  - Snapshot capture: 2026-10-01 approximately 20:07 PDT
    (2026-10-02 03:07 UTC), later than the natural Sentinel trigger.
  - Source host: liquid-pi (Pi3).
  - Source HEAD:
    b44e433d90619d0442f03cb951f40f15960bc5c3.
  - Observed origin/main at capture:
    90f606b45b240404a0ab03743bc4fd571e685976.
  - Pi3 was zero commits ahead and one commit behind that observed
    origin/main. The missing commit was 90f606b, "Add repo-wide machine health
    watchdog."
  - The tracked LRS-2 analytical files agreement_matrix.py, history.py,
    indicators/obi.py, and indicators/near_book_depth.py were verified
    identical between Pi3 HEAD and that observed origin/main, and none had a
    worktree modification.
  - Verified SHA-256:
      obi_log.csv:
        ec15e609317e804e0e0ca3d7e69d0be920c8bf083a6af9f074fd4fdf18f4880f
      near_book_depth_log.csv:
        2c3b583da5d1d11a88c332af445111338de599acc5083365ac2ef5daa1f4c216
  - Snapshot rows and timestamp boundaries:
      obi_log.csv: 2,451 rows, 12 columns,
        2026-07-04T05:56:32Z through 2026-10-01T12:03:41Z.
      near_book_depth_log.csv: 2,441 rows, 13 columns,
        2026-07-04T17:46:14Z through 2026-10-01T12:04:19Z.
  - Pre-copy source hashes, snapshot hashes, and post-copy source hashes
    matched for both CSVs.
  - Canonical agreement-matrix SHA-256:
    1e0bc7d2c43046b9aab0643bd8e7aad22c069a06cd951bf696ea982d8869945d.
  - The later frozen snapshot produced the same 2,431 comparable-pair and
    29-deep-market counts observed by the 06:05 Sentinel trigger despite the
    later raw-log capture. The checkpoint analysis describes the frozen
    snapshot; the trigger record establishes when the checkpoint condition
    first fired.
  - Pi3 remained the sole authoritative live collector/writer. No methodology,
    indicator definition, pairing rule, N=5 setting, or research authority
    changed.

  CP17 trigger, stated mechanically from the frozen CP16 baseline
  (2,431 comparable pairs, 29 markets at n>=15): total comparable pairs
  >= 2,500, OR the count of markets at n>=15 exceeds 29. The 2,500-pair
  milestone predates CP15 and remains unchanged because it has not fired.
  This is a collection trigger, not a statistical-significance threshold.


- Seventeenth checkpoint (triggered 2026-10-04; nearest retained immutable
  analytical population through 2026-10-06, n=2,575 pairs, 671 markets):
  the scheduled 06:05 PDT Sentinel run on October 4 reported 2,515 comparable
  pairs and 29 markets at n>=15. The pair-count condition fired because
  2,515 >= the frozen 2,500-pair threshold; the deep-market condition had not
  fired because the roster remained at the frozen CP16 baseline of 29.

  No immutable October 4 trigger-time snapshot was retained. The nearest
  retained immutable post-trigger analytical snapshot is
  20261007T002008.645365Z, published to the Pi5 LRS-2 handoff directory on
  October 6 at approximately 17:20 PDT (2026-10-07 00:20 UTC). Its source
  observations extend through 2026-10-06 12:03:48 UTC. This snapshot is used
  for CP17 analysis without representing it as an exact reconstruction of the
  October 4 trigger population.

  Applying the frozen latest-row-per-(slug, publication_id) pairing semantics,
  exact-zero neutrality, and canonical slug identity to that immutable
  population produced 2,575 comparable pairs across 671 markets, with 32
  markets at n>=15, 1,558 same-sign pairs, and a 60.50% aggregate same-sign
  rate (1,558/2,575). The maximum per-market sample was n=80.

  Relative to CP16, this retained analytical population increased by 144
  comparable pairs, 41 markets, three deep markets, and 89 same-sign
  observations. The aggregate same-sign rate moved from 60.43%
  (1,469/2,431) to 60.50% (1,558/2,575), a change of +0.08 percentage points
  using the underlying checkpoint fractions. The 144 additional comparable
  pairs contained 89 same-sign observations (61.81%). These figures are
  descriptive only. No frozen statistical threshold has been established for
  classifying this movement as a trend, stability, instability, or predictive
  signal.

  The CP16-to-CP17 deep-market identity audit used canonical slug identity.
  All 29 CP16 deep markets remained in the retained CP17 analytical roster,
  exactly three additional markets crossed n>=15, and no CP16 deep market was
  lost. The newly-deep markets were:

  - 2026 Balance of Power -- Republican Senate / Republican House:
    68.8% same-sign (11/16).
  - Will Benjamin Netanyahu be the next Prime Minister of Israel?:
    60.0% same-sign (9/15).
  - US announces end of Iranian blockade by October 31, 2026?:
    100.0% same-sign (15/15).

  Several previously tracked records changed as their samples deepened. US
  Invade Iran moved from 92.0% (69/75) to 92.5% (74/80). Putin out before
  2027 moved from 96.9% (31/32) to 94.3% (33/35). Iranian regime fall
  remained 100.0%, moving from 21/21 to 22/22. US end of Iranian blockade by
  September 30 remained 96.6% (28/29). Flávio Bolsonaro moved from 54.5%
  (18/33) to 51.4% (18/35), while Luiz Inácio Lula da Silva moved from 32.4%
  (11/34) to 33.3% (12/36). These movements remain heterogeneous descriptive
  observations and do not establish predictive value.

  CP17 provenance:

  - Natural trigger: 2026-10-04 06:05 PDT, with 2,515 comparable pairs and
    29 markets at n>=15.
  - Trigger condition: pairs=2515>=2500; deep-market condition remained
    29/29.
  - The host-local Sentinel log records the transition from NOT_DUE before
    the threshold crossing to DUE at the October 4 scheduled run and records
    an ALERT-SENT event for the LRS-2 research checkpoint.
  - No immutable October 4 trigger-time snapshot was found in the retained
    Pi3 checkpoint snapshots or Pi5 bridge handoff inventory.
  - Nearest retained immutable post-trigger snapshot:
    20261007T002008.645365Z.
  - Snapshot timestamp: 2026-10-07T00:20:08.645365+00:00.
  - Source host: liquid-pi (Pi3).
  - Source commit:
    f691225fa7fc7aada1a1f9bc41d03fd2e1a06582.
  - Verified snapshot SHA-256:
      obi_log.csv:
        d30ee244a59ddf86ad74184030414436118bb986345a11e98aaba24e6a78c4e8
      near_book_depth_log.csv:
        ecfaa0dfb6d2bddbf8e9cf7f757b72c37f0ceda57c986bf017844179b1404af0
  - Snapshot rows and timestamp boundaries:
      obi_log.csv: 2,595 data rows, 12 columns,
        2026-07-04T05:56:32Z through 2026-10-06T12:03:13Z.
      near_book_depth_log.csv: 2,585 data rows, 13 columns,
        2026-07-04T17:46:14Z through 2026-10-06T12:03:48Z.
  - Manifest before-copy and after-copy source boundaries matched, and the
    retained snapshot file hashes matched the manifest.
  - Agreement-matrix CSV SHA-256 under the frozen single-pass equivalent
    semantics:
    e17af9fcbc315e156a5c87a509f2817d3dd5654fd8d2e4e26820cbb893259f6d.
  - The retained analytical population is 60 comparable pairs beyond the
    natural trigger count. It is the nearest retained immutable post-trigger
    evidence, not an exact trigger-time reconstruction.
  - Pi3 remained the authoritative live collector/writer. No indicator
    definition, N=5 setting, pairing rule, deep-market threshold, or research
    interpretation was changed for CP17.

  No CP18 collection trigger is defined by the pre-CP17 frozen authority.
  A subsequent trigger must be stated explicitly from the CP17 baseline
  rather than inferred retroactively from observations accumulated while the
  CP17 Sentinel remained DUE.


---

## Forward Midpoint Study A — Frozen Pre-Outcome Methodology

**Status:** EXECUTED — first canonical outcome exposure completed 2026-11-08 under the frozen pre-outcome methodology. No post-outcome respecification is authorized.

**Research question:** Does full-book OBI measured at time T contain information
about subsequent midpoint movement at the next approximately daily observation?

This study addresses the existing LRS-2 Core Research Question, "Does OBI
predict future midpoint movement?" It is a separate historical predictive
study. It is not CP18, does not define a CP18 collection trigger, and does not
alter the CP1-CP17 descriptive checkpoint methodology.

### Evidence population

The sole evidence population is the retained immutable CP17 analytical
snapshot:

`20261007T002008.645365Z`

Source observations extend through 2026-10-06. Later live observations,
including observations accumulated after CP17 while the old Sentinel remained
DUE, are excluded from Study A.

Verified snapshot source hashes:

- `obi_log.csv`:
  `d30ee244a59ddf86ad74184030414436118bb986345a11e98aaba24e6a78c4e8`
- `near_book_depth_log.csv`:
  `ecfaa0dfb6d2bddbf8e9cf7f757b72c37f0ceda57c986bf017844179b1404af0`

### Outcome-blind feasibility work completed before this freeze

Before any forward midpoint outcome was calculated or related to OBI, the
retained CP17 snapshot was inspected only for sampling geometry, source
pairing, timestamp separation, midpoint completeness, and contemporaneous
source consistency.

That inspection established:

- 2,580 canonical latest-row-per-(slug, publication_id) OBI observations;
- 2,575 canonical latest-row-per-(slug, publication_id) Near-Book
  observations;
- 2,575 shared OBI/Near pairs across 671 markets and 99 shared publication
  cycles;
- 2,483 pairs across 664 markets satisfy an absolute OBI/Near timestamp
  separation of no more than 120 seconds;
- 96.43% of all shared pairs satisfy that 120-second boundary;
- widening the boundary from 120 seconds to 300 seconds adds only 24 pairs
  and four markets;
- five observations with separation greater than 600 seconds all belong to
  the single legacy publication cycle `snapshot_20260704_1005.csv`;
- midpoint values are complete in both sources for all 2,575 shared pairs;
- longitudinal sampling is irregular but strongly concentrated around a
  roughly daily collection interval;
- among canonical OBI observations with any later same-market observation,
  1,091 of 1,909 anchors (57.15%) have a later observation in the 18-30 hour
  window;
- among canonical Near-Book observations with any later same-market
  observation, 1,091 of 1,904 anchors (57.30%) have a later observation in
  the 18-30 hour window.

These facts were used only to establish whether a forward study was
mechanically supportable and to freeze its timing rules. No forward midpoint
change, OBI/outcome relationship, predictive success rate, correlation,
return, or outcome-conditioned subgroup was inspected before this
methodology was frozen.

### Canonical observation construction

For each source independently:

1. retain valid observations;
2. order observations by their real timestamp;
3. for each `(slug, publication_id)`, retain the latest valid row.

This preserves the established CP1-CP17 latest-row-per-publication semantics
without assuming that `(slug, publication_id)` is inherently unique.

A Study A anchor requires both an OBI and Near-Book observation for the same
`(slug, publication_id)` and an absolute separation between their timestamps
of no more than 120 seconds.

The 120-second boundary is a contemporaneous-data eligibility rule, not a
predictive threshold. It was selected before outcome exposure from the
observed acquisition geometry described above.

No observation is excluded because the OBI-source and Near-Book-source
midpoints differ.

### Time T and predictor

For every eligible anchor:

- T is the OBI observation timestamp;
- the baseline price is the OBI-source midpoint at T;
- the primary predictor is the continuous full-book OBI value at T.

The existing frozen OBI calculation is not changed.

No OBI magnitude cutoff, percentile threshold, bin boundary, optimized
decision threshold, or newly constructed indicator is part of the primary
hypothesis.

Near-Book OBI remains retained as contemporaneous research evidence but is
not a primary predictor in Study A. Whether Near-Book OBI adds predictive
information beyond full-book OBI requires a separately specified comparison
and is not inferred from this study.

### Forward-observation rule

For each eligible anchor, identify the chronologically next canonical
publication-level OBI observation for the same slug.

The anchor is eligible for the primary outcome only when that immediately
next observation occurs from 18 through 30 elapsed hours after T, inclusive.

The immediately next observation may not be skipped in order to select a
later observation that happens to fall inside the 18-30 hour window.

No nearest-to-24-hours search is performed.

No 48-hour, 72-hour, or other alternative horizon is part of Study A.

### Primary outcome

The primary outcome is signed midpoint change:

`next_obi_midpoint - anchor_obi_midpoint`

The primary analysis asks whether continuous full-book OBI at T is associated
with this subsequent signed midpoint change.

The exact statistical implementation must preserve the continuous predictor
and signed outcome and must be specified and audited before execution. Study A
does not authorize post-outcome selection among multiple statistical tests.

### Secondary descriptive diagnostic

A single secondary diagnostic may report directional concordance:

- positive OBI with positive future midpoint change;
- negative OBI with negative future midpoint change.

Exact-zero OBI or exact-zero future midpoint change is neutral and is not
counted as directional concordance or discordance.

This diagnostic is secondary and descriptive. It does not replace the
continuous primary analysis.

### Prohibited post-outcome adaptation

After Study A outcomes are exposed, the following may not be introduced into
Study A in order to improve the result:

- alternate forward horizons;
- alternate contemporaneous-pair timing tolerances;
- OBI magnitude thresholds or optimized cutoffs;
- outcome-selected OBI bins;
- market-category rescue analyses;
- liquidity or spread rescue variables;
- exclusion based on contemporaneous midpoint disagreement;
- selective removal of markets because their outcomes weaken the result;
- LRS-1 trade outcomes or LRS-1 selection state;
- Near-Book combinations selected after observing the full-book OBI result;
- reconstructed historical diagnostics whose exact mechanics were not frozen
  before outcome exposure.

Any such question requires a separately defined follow-up study with its own
pre-outcome methodology and evidence boundary.

### First canonical result — 2026-11-08

The first canonical Study A execution used code authority
`0415f0af5a1b35d78000956bdab4cc2738a8d834` and the sole frozen CP17
analytical snapshot `20261007T002008.645365Z`.

The audited provenance runner validated the frozen snapshot contract before
delegating to the frozen Study A implementation. The execution reported:

- eligible observations: 1,009;
- unique slug clusters: 225;
- intercept: 0.00010752942338519746;
- full-book OBI coefficient (`beta`): -0.01586748820654767;
- slug-clustered robust standard error of `beta`: 0.0045457246668535152;
- 95% confidence interval for `beta`:
  [-0.024825343061202598, -0.0069096333518927425];
- two-sided p-value for `beta`: 0.00058022107633821918;
- secondary same-direction count: 418;
- secondary same-direction rate: 0.41427155599603566 (41.43%).

Under the prospectively frozen primary test, the estimated association is
negative: higher full-book OBI at T is associated with lower subsequent signed
midpoint change at the immediately next eligible 18-30 hour observation, and
lower OBI with higher subsequent signed midpoint change. The frozen two-sided
test rejects `H0: beta = 0` at alpha=0.05.

This is historical evidence of a negative association in the bounded CP17
Study A population. It does not establish prospective predictive value,
economic significance, profitability, a production trading signal, or an
improvement to LRS-1. The secondary 41.43% same-direction rate is descriptive
and does not replace the continuous primary analysis.

The first outcome exposure does not authorize alternate horizons, thresholds,
bins, market subsets, rescue variables, Near-Book combinations, LRS-1
conditioning, or any other post-outcome respecification prohibited by the
frozen methodology. Any follow-up question requires a separately specified
pre-outcome study and evidence boundary.

### Interpretation boundary

Study A is a historical research test on a bounded retained population.

A positive result would not by itself establish:

- live or prospective predictive value;
- statistical or economic significance beyond the test actually specified;
- profitability after execution costs;
- a production trading signal;
- authorization to alter LRS-1 market selection or entry timing;
- authorization to combine LRS-1 and LRS-2;
- readiness for deployment.

A null or negative result must likewise be retained as evidence and may not
be rescued by changing Study A's frozen rules after outcome exposure.

No CP18 collection trigger is created by this study.

### Frozen primary statistical procedure

Before outcome exposure, the independent pre-outcome methodology audit returned
PASS and required the exact primary statistical procedure to be frozen.

The primary estimator is an ordinary least squares linear regression:

`future_midpoint_change = intercept + beta * obi_t + error`

where:

- `future_midpoint_change` is the frozen signed primary outcome
  (`next_obi_midpoint - anchor_obi_midpoint`);
- `obi_t` is the frozen continuous full-book OBI value at T;
- an intercept is included;
- OBI remains on its original continuous scale, with no transformation,
  standardization, binning, clipping, or thresholding;
- midpoint change remains in original midpoint units, with no normalization or
  transformation;
- each eligible anchor contributes exactly one regression observation;
- the clustering variable is canonical market identity `slug`.

Inference uses a cluster-robust sandwich covariance estimator with standard
errors clustered at the `slug` level to account for repeated eligible anchors
from the same market.

The single primary inferential test is:

- null hypothesis: `beta = 0`;
- alternative hypothesis: `beta != 0`;
- two-sided significance level: alpha = 0.05;
- the primary p-value is computed from the slug-clustered robust covariance.

The primary result must report at minimum:

- beta estimate;
- intercept estimate;
- slug-clustered robust standard error for beta;
- 95% confidence interval for beta;
- two-sided p-value for beta;
- number of eligible anchor observations;
- number of unique slug clusters represented.

There is no fallback to ordinary, heteroskedasticity-only, or other
non-slug-clustered standard errors if the frozen clustered procedure cannot be
computed. Such a failure is an analysis failure to be diagnosed without
exposing or substituting an alternative primary result.

No alternate regression specification, transformation, weighting scheme,
fixed-effect specification, alternative covariance estimator, alternative
significance threshold, or alternative primary statistical test may be
selected after outcomes are observed.


#### Frozen clustered-inference numerical convention

Before any Study-A outcome was calculated or exposed, the numerical convention
for the already-frozen slug-clustered sandwich inference was prospectively
specified and independently audited.

For the one-way slug-clustered sandwich covariance:

- `G` is the number of unique canonical `slug` clusters among eligible anchors;
- `N` is the number of eligible anchor observations;
- `K = 2`, corresponding exactly to the intercept and continuous full-book OBI
  coefficient;
- the cluster-robust sandwich covariance is multiplied by the CR1 finite-sample
  correction `(G / (G - 1)) * ((N - 1) / (N - K))`;
- the beta test statistic is `beta / clustered_SE_beta`;
- the frozen primary two-sided p-value uses a Student-t reference distribution
  with exactly `G - 1` degrees of freedom;
- the frozen 95% confidence interval for beta uses the corresponding
  `t_(0.975, G - 1)` critical value.

There is no normal/z fallback, alternate CR correction, or alternate
degrees-of-freedom convention. If `G <= 1`, `N <= K`, the OLS design matrix is
rank deficient, or the clustered covariance or beta standard error cannot be
computed as a finite valid quantity, the frozen primary analysis fails rather
than substituting another estimator or inference procedure.

Statistical significance under this frozen historical test is not equivalent
to economic significance, prospective predictive validity, profitability, or
production readiness.

---

## Forward Midpoint Study B — Frozen Replication Methodology

**Status:** EXECUTED — canonical Study-B replication completed 2026-11-08
against the prospectively frozen strictly post-Study-A evidence population.
The frozen specification was not changed after outcome exposure.

**Research question:** Does the full-book OBI association tested in Study A
replicate in a strictly post-Study-A temporal evidence population under the
same primary specification and numerical inference convention?

Study B is a temporal replication study. It is not CP18, does not define a
CP18 collection trigger, does not alter the CP1-CP17 descriptive checkpoint
methodology, and does not authorize LRS-1 integration.

### Evidence population

The sole Study-B evidence population is the retained immutable analytical
snapshot:

`20261107T130339.259331Z`

Verified snapshot identity:

- snapshot UTC: `2026-11-07T13:03:39.259331+00:00`;
- purpose: `LRS2 bounded analytical snapshot`;
- source host: `liquid-pi`;
- source commit:
  `f691225fa7fc7aada1a1f9bc41d03fd2e1a06582`;
- research checkpoint: `False`;
- manifest SHA-256:
  `b2a80ba423448401ee8435f6d9c67c0485af537c9b456a03289eb103b79ba5f7`;
- `obi_log.csv` SHA-256:
  `74063d05e85ea3a26e07815020928ca301e592e10c120edbc0271852721d8001`;
- `near_book_depth_log.csv` SHA-256:
  `c0454875be0ce76ec55eaffa9c2286e3c0d9de2b564b4d042bba4b8d40da9f04`.

The frozen Study-A OBI evidence boundary is:

`2026-10-06T12:03:13Z`

A Study-B primary anchor is eligible only if both:

1. its canonical OBI timestamp is strictly later than the Study-A boundary;
2. its immediately next canonical same-slug OBI observation used for the
   primary outcome is also strictly later than the Study-A boundary.

No Study-A anchor may re-enter Study B.

### Outcome-blind feasibility work completed before this freeze

Before any Study-B OBI value, midpoint value, forward midpoint outcome,
OBI/outcome relationship, regression result, correlation, directional success
rate, or outcome-conditioned subgroup was calculated or exposed, the retained
Study-B candidate snapshot was inspected using identifiers, statuses, hashes,
and timestamps only.

That inspection established:

- 3,655 raw OBI rows and 3,646 raw Near-Book rows in the snapshot;
- 3,640 canonical valid OBI observations and 3,636 canonical valid Near-Book
  observations;
- 888 unique slugs in each canonical source;
- 1,060 canonical OBI observations occur strictly after the Study-A OBI
  evidence boundary;
- those 1,060 observations span 304 unique slugs;
- all 1,060 post-boundary OBI observations have a same-key canonical
  OBI/Near-Book pair with absolute timestamp separation no greater than
  120 seconds;
- 505 post-boundary contemporaneous anchors have an immediately next
  canonical same-slug OBI observation 18 through 30 elapsed hours later,
  inclusive;
- those 505 temporal-geometry-eligible anchors span 106 unique slugs;
- all 505 eligible anchors and all 505 immediately next outcome timestamps
  are strictly later than the Study-A evidence boundary;
- zero eligible forward observations cross backward over the Study-A evidence
  boundary;
- 304 observations are the first post-boundary observation for their slug;
- 87 of those first post-boundary observations have a pre-boundary
  predecessor, but this does not enter the primary forward outcome because
  the frozen outcome uses the anchor and its immediately next observation,
  and both are post-boundary for all 505 eligible anchors.

These facts establish sampling and temporal geometry only. They are not
Study-B outcome evidence.

### Replication specification

Study B carries forward the Study-A primary scientific specification unchanged
except for the prospectively defined post-Study-A evidence boundary above.

For each source independently:

1. retain valid observations;
2. order observations by their real timestamp;
3. for each `(slug, publication_id)`, retain the latest valid row.

A Study-B anchor requires both an OBI and Near-Book observation for the same
`(slug, publication_id)` and an absolute separation between their timestamps
of no more than 120 seconds.

No observation is excluded because the OBI-source and Near-Book-source
midpoints differ.

For every eligible anchor:

- T is the OBI observation timestamp;
- the baseline price is the OBI-source midpoint at T;
- the primary predictor is the continuous full-book OBI value at T.

The existing frozen OBI calculation is unchanged. There is no OBI magnitude
cutoff, percentile threshold, bin boundary, optimized decision threshold,
transformation, standardization, clipping, or newly constructed primary
indicator.

Near-Book OBI remains retained contemporaneous evidence but is not a primary
predictor in Study B.

### Forward-observation rule

For each eligible anchor, identify the chronologically immediately next
canonical publication-level OBI observation for the same slug.

The anchor is eligible for the primary outcome only when that immediately
next observation occurs from 18 through 30 elapsed hours after T, inclusive.

The immediately next observation may not be skipped to select a later
observation inside the 18-30 hour window. No nearest-to-24-hours search is
performed. No 48-hour, 72-hour, or alternative horizon is part of Study B.

Both the anchor and the immediately next observation must satisfy the frozen
strictly-post-Study-A temporal boundary.

### Primary outcome and estimator

The primary outcome is unchanged from Study A:

`next_obi_midpoint - anchor_obi_midpoint`

The primary estimator is:

`future_midpoint_change = intercept + beta * obi_t + error`

where:

- an intercept is included;
- `obi_t` remains on its original continuous scale;
- midpoint change remains in original midpoint units;
- each eligible anchor contributes exactly one regression observation;
- the clustering variable is canonical market identity `slug`.

The primary hypotheses remain:

- null hypothesis: `beta = 0`;
- alternative hypothesis: `beta != 0`;
- two-sided significance level: alpha = 0.05.

Study B does not redefine the formal alternative as negative merely because
Study A estimated a negative coefficient.

### Frozen clustered-inference numerical convention

Study B carries forward the Study-A numerical convention unchanged.

For one-way slug-clustered sandwich covariance:

- `G` is the number of unique canonical `slug` clusters among eligible anchors;
- `N` is the number of eligible anchor observations;
- `K = 2`, corresponding exactly to the intercept and continuous full-book OBI
  coefficient;
- apply the CR1 finite-sample correction
  `(G / (G - 1)) * ((N - 1) / (N - K))`;
- the beta test statistic is `beta / clustered_SE_beta`;
- the primary two-sided p-value uses a Student-t reference distribution with
  exactly `G - 1` degrees of freedom;
- the 95% confidence interval uses `t_(0.975, G - 1)`.

There is no normal/z fallback, alternate CR correction, alternate
degrees-of-freedom convention, alternate covariance estimator, alternate
regression specification, weighting scheme, fixed-effect specification, or
alternative primary statistical test.

If `G <= 1`, `N <= K`, the OLS design matrix is rank deficient, or the
clustered covariance or beta standard error cannot be computed as a finite
valid quantity, the primary analysis fails rather than substituting another
procedure.

### Required primary reporting

The Study-B primary result must report at minimum:

- beta estimate;
- intercept estimate;
- slug-clustered robust standard error for beta;
- 95% confidence interval for beta;
- two-sided p-value for beta;
- number of eligible anchor observations;
- number of unique slug clusters represented.

The same secondary directional-concordance diagnostic defined in Study A may
be reported:

- positive OBI with positive future midpoint change;
- negative OBI with negative future midpoint change;
- exact-zero OBI or exact-zero future midpoint change is neutral.

It remains secondary and descriptive and does not replace the continuous
primary analysis.

### Prohibited post-outcome adaptation

After Study-B outcomes are exposed, Study B may not be altered or rescued
using:

- alternate forward horizons;
- alternate contemporaneous-pair timing tolerances;
- OBI thresholds, optimized cutoffs, bins, transformations, or clipping;
- market-category subsets selected from Study-B outcomes;
- liquidity or spread rescue variables;
- midpoint-disagreement exclusions;
- selective market removal;
- Near-Book combinations selected after seeing the Study-B result;
- LRS-1 trade outcomes, selection state, or conditioning;
- alternate estimators, covariance conventions, significance thresholds, or
  inferential tests.

A null result, opposite-sign result, or statistically non-significant result
must be retained as Study-B evidence without rescue.

### Interpretation boundary

Study B tests whether the Study-A association replicates in a later,
non-overlapping anchor/outcome temporal population under the same frozen
primary specification.

Whatever the result, Study B alone does not establish profitability,
production readiness, deployability, causal effect, or improvement to an
LRS-1 trading decision.

No LRS-1 integration and no CP18 collection trigger are authorized by this
study.

Any subsequent question involving thresholds, Near-Book incremental value,
market subsets, alternative horizons, or LRS-1 conditioning requires a
separately specified pre-outcome study and evidence boundary.

### Canonical Study-B result

Study B was executed on 2026-11-08 against the frozen immutable snapshot
`20261107T130339.259331Z` using the committed Study-B implementation at
`5b5e48aea74c6a7d10c4df18c0e1d4bcc3a9b516`.

The frozen primary regression contained 505 eligible observations across 106
slug clusters. The canonical result was:

- intercept: `-0.0027210385017333522`;
- beta: `-0.0090142714987921316`;
- slug-clustered robust standard error for beta:
  `0.0035299762431765368`;
- 95% confidence interval for beta:
  `[-0.016013562309896229, -0.0020149806876880328]`;
- two-sided p-value: `0.012096530327545912`;
- eligible observations: `505`;
- slug clusters: `106`;
- secondary same-direction count: `172`;
- secondary same-direction rate: `0.34059405940594062` (34.06%).

Under the prospectively frozen Study-B specification, the estimated beta is
negative and its frozen two-sided test rejects `beta = 0` at alpha = 0.05.
The 95% confidence interval is entirely below zero.

Study B therefore records a statistically nonzero negative historical
association in the later, non-overlapping temporal evidence population, in the
same direction as Study A. This constitutes a temporal replication of the
negative association under the frozen Study-A/Study-B primary specification.

The Study-B beta is smaller in magnitude than the Study-A beta. No
post-outcome analysis is authorized to explain, optimize, subdivide, or rescue
that difference. The secondary same-direction rate remains descriptive only.

The replication strengthens the historical evidence that the frozen
continuous full-book OBI measure is associated with subsequent signed midpoint
change under the specified sampling and 18-30 hour immediate-next rule. It
does not establish causality, economic significance, prospective predictive
validity, profitability, production readiness, deployability, or improvement
to an LRS-1 trading decision.

No alternate horizon, OBI threshold, market subset, Near-Book combination,
liquidity/spread rescue, alternate inference procedure, CP18 trigger, or LRS-1
integration is authorized by this result.

---

## Prospective Post-Admission Conditioning Study C — Frozen Pre-Outcome Methodology

**Status:** FROZEN PRE-OUTCOME METHODOLOGY — INDEPENDENT AUDIT PASS; NO OUTCOME EXECUTION AUTHORIZED.

**Research question:** Among trades independently admitted by the unchanged LRS-1
paper-trading methodology, does contemporaneous LRS-2 full-book OBI measured
after admission provide information about the trade's subsequent paper-trade
outcome?

Study C is a prospective cross-engine conditioning study owned by LRS-2. It
does not alter LRS-1 admission methodology, market selection, side selection,
position sizing, or resolution methodology. It does not modify the frozen
Study-A or Study-B evidence or specifications.

Because the LRS-2 observation is produced after LRS-1 admission in the current
daily pipeline, Study C tests **post-admission conditioning / incremental
information**. It does not test whether LRS-2 improves the original LRS-1
admission decision.

Study C is not CP18, does not define a CP18 collection trigger, and does not
authorize production integration, live trading, position sizing, or changes to
LRS-1.

### Pre-outcome evidence and rationale

Study A and Study B independently established a negative historical association
between continuous full-book OBI and subsequent same-token midpoint movement
under their frozen 18-30 hour immediate-next specifications.

Study-A canonical beta:

`-0.01586748820654767`

Study-B canonical beta:

`-0.0090142714987921316`

Both frozen two-sided tests rejected beta = 0 at alpha = 0.05, and Study B
replicated the negative direction in a later non-overlapping temporal evidence
population.

Those studies did not use LRS-1 trade outcomes and did not establish that OBI
improves or informs an LRS-1 trading decision. Study C opens that separate
question prospectively.

Before Study-C outcome exposure, outcome-blind pipeline inspection established
that new LRS-1 admissions are followed by same-slug LRS-2 full-book OBI
observations during the OBI stage of the same successful daily orchestrator
run. In the inspected 2026-11-09 run, all 15 new admissions had a matching
post-admission OBI observation approximately 2.35 to 3.13 minutes after
admission. These 15 admissions are feasibility evidence only and are not part
of the protected Study-C confirmatory cohort.

Outcome-blind recent family/dependence geometry was also inspected before this
freeze. Among 214 recent LRS-1 admissions from 2026-10-10 through 2026-11-09,
the frozen v1.1 event-family classifier produced 164 represented families,
including 142 singleton families and 22 multi-trade families. The largest
family contained 11 trades (5.14% of the 214-trade population).

For the first 150 trades in that outcome-blind recent sequence, 121 families
were represented, 106 were singletons, 15 were multi-trade families, and the
largest family contained 7 trades (4.67%).

No LRS-1 outcome, entry-price, side, P&L, or LRS-2 measurement value was
accessed in that family-geometry diagnostic.

Historical resolution timing was inspected separately without reading outcome
values, entry price, side, P&L, or LRS-2 measurement values. Among 733 rows
with valid nonnegative entry-to-resolution timestamps, the maximum observed
latency was 136.731944 days and all 733 resolved within 150 calendar days.
This timing evidence is used only to define the administrative outcome-opening
boundary below.

### Protected prospective population

The protected Study-C cohort consists of the **first 150 prospectively
eligible enrollments after the final Study-C methodology freeze commit and
freeze timestamp**.

The 150 count applies to eligible enrolled Study-C trades, not to raw LRS-1
admissions.

No admission occurring at or before the final methodology freeze boundary is
eligible for the protected cohort. The 2026-11-09 feasibility population is
therefore excluded.

Cohort membership is determined without reference to `trade_won`,
`trade_pnl`, resolution outcome, or any other outcome-bearing field.

Enrollment stops permanently when the 150th eligible Study-C trade is enrolled.
There is no early stopping for favorable evidence and no extension because of
weak, null, adverse, missing, or otherwise inconvenient eventual results.

For deterministic prospective sequencing, eligible candidates are processed in
chronological orchestrator-run order. Within the same orchestrator run,
candidates are ordered by ascending integer `trade_id`. `enrollment_sequence`
follows that order. This ordering rule has no eligibility, predictor, outcome,
or classification role beyond determining the frozen first-150 sequence.

### LRS-1 admission identity

Each candidate begins with an independently created LRS-1 paper-trade
admission under the unchanged LRS-1 methodology.

The LRS-1 trade identity is `trade_id`. The study enrollment record must also
preserve at minimum:

- `trade_id`;
- `market_id`;
- canonical `slug`;
- LRS-1 `side`;
- LRS-1 admission timestamp;
- `scanner_run_id`;
- corresponding orchestrator `run_id`.

Study C does not authorize any change to LRS-1's existing one-`market_id`,
maximum-one-paper-trade admission invariant.

### Post-admission LRS-2 anchor

For each candidate LRS-1 admission, the Study-C LRS-2 anchor is the first
successful full-book OBI observation for the same canonical `slug` produced
during the `run_obi` stage of the same successful orchestrator `run_id` in
which the LRS-1 admission was created.

The LRS-2 timestamp must be strictly later than the LRS-1 admission timestamp.

No later orchestrator run may be substituted when the required same-run anchor
is absent or invalid. No nearest-observation search, alternate timing window,
manual replacement, or retrospective fallback is permitted.

The enrollment record must preserve the LRS-2 `publication_id` and LRS-2
observation timestamp used as the anchor.

### Token/outcome identity eligibility

The full-book OBI producer measures the first token returned by the market
token/outcome ordering. Pre-outcome structural inspection established that
index 0 is typically, but not universally, the `Yes` outcome.

Study C therefore requires explicit token identity.

A candidate is eligible only when:

- the market exposes exactly two outcomes;
- the market exposes exactly two corresponding token IDs;
- the ordered outcomes are exactly `["Yes", "No"]`;
- the measured full-book OBI token is explicitly the token corresponding to
  `Yes`; and
- the LRS-1 recorded side is exactly `Yes` or `No`.

If any requirement fails, the candidate is ineligible. There is no outcome
reordering, alternate-token fallback, manual semantic interpretation, or
retrospective repair.

The enrollment artifact must preserve both `outcome_tested = Yes` and the
exact measured `token_id`.

### Primary LRS-2 predictor

The underlying full-book OBI remains the frozen continuous measurement:

`OBI = (V_bid - V_ask) / (V_bid + V_ask)`

Study A and Study B prospectively established before Study-C outcomes that
higher raw OBI for the measured token was associated with lower subsequent
same-token midpoint movement.

Study C therefore defines one continuous **side-aligned OBI score** before
prospective outcome exposure:

- if LRS-1 `side == "Yes"`: `side_aligned_obi = -raw_obi`;
- if LRS-1 `side == "No"`: `side_aligned_obi = +raw_obi`.

Higher `side_aligned_obi` therefore represents the direction historically
favorable to the already-selected LRS-1 side under the replicated Study-A/B
OBI relationship.

The continuous score is primary. There is no threshold, cutoff, percentile,
bin, clipping, standardization, nonlinear transformation, optimized boundary,
or abstention rule.

Near-Book OBI is not part of the Study-C primary predictor and may not be
introduced after outcome exposure to rescue or replace the frozen predictor.

### Joint primary outcomes

Study C has one joint structural target with two jointly required LRS-1
paper-trade outcome relationships:

1. `side_aligned_obi` versus numeric `trade_won`;
2. `side_aligned_obi` versus `trade_pnl`.

`trade_won` uses the existing deterministic LRS-1 numeric representation.
`trade_pnl` uses the existing LRS-1 paper-trading resolution and P&L
semantics. Study C does not redefine either outcome.

Because higher `side_aligned_obi` is defined as historically more favorable
for the already-selected LRS-1 side, the prespecified expected direction is
**positive for both primary relationships**.

The two outcome relationships are jointly required components of one Study-C
target and are not interchangeable discoveries. Neither may rescue failure of
the other.

### Primary statistical procedure

For the usable resolved members of the fixed protected cohort, compute:

- Spearman(`side_aligned_obi`, `trade_won`);
- Spearman(`side_aligned_obi`, `trade_pnl`).

The implementation must use `scipy.stats.spearmanr` with its two-sided
p-value convention and primary alpha = 0.05.

The exact audited Study-C execution environment, including the exact SciPy
version, must be pinned in the Study-C implementation/provenance contract
before any protected outcome execution. No outcome execution is authorized
until that implementation and environment are independently audited and
frozen.

Supporting Pearson associations may be reported but have zero classification
authority.

No regression, threshold test, subgroup test, alternate rank statistic,
one-sided p-value, or alternate significance level may replace the frozen
primary procedure after outcomes are exposed.

### Frozen family/dependence sensitivity

Study C carries forward the existing frozen LRS-1 v1.1 event-family
classification semantics prospectively.

Family assignment must use the frozen deterministic question-only
`classify_v11` semantics. No outcome-bearing value may influence family
assignment.

The implementation must provenance-check the frozen detector authority before
protected execution.

For the family-equal sensitivity, aggregate the usable resolved protected
cohort to exactly one row per frozen `family_key` using arithmetic means of:

- `side_aligned_obi`;
- numeric `trade_won`;
- `trade_pnl`.

Each represented family receives one row regardless of raw family size.

Report:

- represented-family count;
- largest-family size;
- largest-family raw-trade concentration;
- family-rule counts;
- family-equal Spearman and supporting Pearson association between family-mean
  `side_aligned_obi` and family-mean `trade_won`;
- family-equal Spearman and supporting Pearson association between family-mean
  `side_aligned_obi` and family-mean `trade_pnl`.

Family-aware analysis is a dependence sensitivity and is not proof that raw
trades are independent.

### Deterministic PASS / FAIL / INCONCLUSIVE classification

Classification is applied in this exact order.

1. Evaluate both raw-trade primary Spearman relationships.
2. If either raw-trade primary Spearman is negative, classify **FAIL**.
3. Otherwise, if either raw-trade primary Spearman is zero or mathematically
   undefined, classify **INCONCLUSIVE**.
4. Otherwise, if either raw-trade primary two-sided p-value is undefined or
   `>= 0.05`, classify **INCONCLUSIVE**.
5. Otherwise both raw-trade primary relationships are positive with two-sided
   `p < 0.05`; evaluate the frozen family-equal sensitivity.
6. If either required family-equal Spearman is undefined, zero, or negative,
   classify **INCONCLUSIVE**.
7. Otherwise classify **PASS**.

Therefore PASS requires:

- Spearman(`side_aligned_obi`, `trade_won`) > 0 with two-sided `p < 0.05`;
- Spearman(`side_aligned_obi`, `trade_pnl`) > 0 with two-sided `p < 0.05`;
- family-equal Spearman(`side_aligned_obi`, `trade_won`) > 0;
- family-equal Spearman(`side_aligned_obi`, `trade_pnl`) > 0;
- all required statistics mathematically defined; and
- exact prespecified analysis executed without post-outcome modification.

FAIL requires an opposite, negative direction in either raw-trade primary
relationship.

INCONCLUSIVE applies when no FAIL condition is present but a required raw
primary or family statistic is zero, undefined, insufficiently significant
under the frozen raw-primary rule, or otherwise cannot be evaluated.

The family sensitivity may downgrade an otherwise qualifying PASS to
INCONCLUSIVE. It may not rescue a raw FAIL or raw INCONCLUSIVE result.

### Fixed cohort, resolution, and administrative outcome-opening boundary

The protected cohort identities remain fixed after the 150th eligible
enrollment. Resolution speed may not determine cohort membership.

Protected outcome analysis may open when either:

1. all 150 protected cohort members have resolved under the unchanged LRS-1
   resolution contract; or
2. 150 calendar days have elapsed after the admission timestamp of the 150th
   eligible enrollment,

whichever occurs first.

At the administrative boundary, any unresolved protected member remains part
of the disclosed protected cohort and is not replaced.

Primary and family analyses use every protected cohort member with the
required predictor and resolved usable outcome fields. Raw protected n, usable
n for each required statistic, unresolved count, and all required-field
missingness must be reported.

Missing or unresolved members may not be replaced, and the cohort may not be
extended because of observed results.

If missingness or unresolved outcomes make any required primary or
family-equal statistic mathematically undefined, the final classification is
INCONCLUSIVE unless an earlier raw opposite-direction FAIL condition applies.

### Required prospective enrollment artifact

Study C must use a separate study-specific enrollment artifact rather than
changing the existing live OBI or Near-Book CSV schemas.

Each enrolled row must preserve at minimum:

- enrollment sequence;
- orchestrator `run_id`;
- LRS-1 `trade_id`;
- LRS-1 `market_id`;
- canonical `slug`;
- LRS-1 `side`;
- LRS-1 admission timestamp;
- `scanner_run_id`;
- LRS-2 `publication_id`;
- LRS-2 timestamp;
- `outcome_tested`;
- measured `token_id`;
- raw full-book OBI;
- `side_aligned_obi`;
- frozen family `rule_matched`;
- frozen `family_key`.

The enrollment artifact must not contain `trade_won`, `trade_pnl`, winning
outcome, or other future outcome values during prospective accrual.

### Prohibited post-outcome adaptation

After any protected Study-C outcome is exposed to the Study-C analysis, Study C
may not be altered, subdivided, optimized, or rescued using:

- alternate OBI thresholds, bins, cutoffs, transformations, or clipping;
- alternate side-alignment rules;
- alternate token/outcome interpretation;
- alternate post-admission timing windows or later OBI observations;
- Near-Book OBI combinations;
- liquidity, spread, category, or market-subset rescue variables;
- selective family removal or altered family semantics;
- selective trade removal other than frozen missing-data handling;
- replacement of unresolved or ineligible trades;
- extension beyond the first 150 eligible enrollments because of results;
- alternate outcomes;
- alternate correlation estimators;
- one-sided significance tests;
- alternate alpha thresholds;
- candidate switching;
- LRS-1 methodology changes justified from Study-C outcomes.

All adverse, null, zero, undefined, missing, opposite-direction, or otherwise
non-confirmatory results must be retained and reported.

### Interpretation boundary

Study C asks whether the frozen side-aligned LRS-2 full-book OBI score provides
prospective information about later LRS-1 paper-trade outcomes **conditional on
a trade already having been independently admitted by LRS-1**.

PASS would establish prospective evidence for post-admission conditioning under
this exact frozen population, timing, identity, predictor, outcome, and
classification contract.

PASS would not by itself establish:

- causality;
- live-money profitability;
- economic significance;
- universal generalization;
- a production trading signal;
- an OBI entry threshold;
- position sizing;
- an abstention rule;
- improvement to the original LRS-1 admission decision;
- authorization to modify LRS-1;
- authorization to deploy LRS-2 into production;
- a CP18 trigger.

FAIL or INCONCLUSIVE must be retained as Study-C evidence without rescue.

Any later attempt to use LRS-2 before LRS-1 admission, alter LRS-1 admission,
derive a trading threshold, combine Near-Book information, change timing, or
test production decision value requires a separately frozen prospective study.

### Frozen authorization state

Independent pre-outcome methodology audit verdict: **PASS**.

Blocking findings: **NONE**.

Required corrections: **NONE**.

The methodology is safe to freeze before prospective enrollment begins.

At this freeze stage:

- protected Study-C enrollment opened: **NO**;
- protected Study-C cohort identities established: **NO**;
- protected Study-C outcomes accessed: **NO**;
- Study-C analysis executed: **NO**;
- Study-C production integration authorized: **NO**;
- CP18 authorized: **NO**.

The protected Study-C population begins only after the final methodology freeze
commit and freeze timestamp. No pre-freeze admission is eligible.
