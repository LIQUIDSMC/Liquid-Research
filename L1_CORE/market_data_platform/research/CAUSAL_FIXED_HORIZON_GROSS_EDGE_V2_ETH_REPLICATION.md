# Causal Fixed-Horizon Gross-Edge Replication v2 — ETH Post-Entry Continuation Test

## Status / Purpose

This is a completed confirmatory replication experiment, not strategy
optimization or parameter search. Its sole purpose was to test whether a
specific, previously observed effect reproduces on independent data. No
new hypothesis was generated from this run's own results, and no
horizon/threshold/direction was retroactively selected after seeing
outcomes.

## Provenance

- Implementation checkpoint: 756a98e14378ae8a24a49c1704f48d3425082afe
- Script SHA-256 at execution: 3cb0b89667fa3596f6fe18718ab3cd3c9e4fd0f911a2ee2b75c95f0439c0bcd6
- Script: causal_fixed_horizon_gross_edge_v2_eth_replication.py
- Canonical result path:
  L1_CORE/market_data_platform/research/results/causal_fixed_horizon_gross_edge_v2_eth_replication/
- Result preservation verified: 25/25 files, 4,017,438 bytes, SHA-256
  content-identical between Pi source and Mac canonical copy
  (order-independent manifest diff, empty).

## Frozen Design

- Instrument: ETH-USD only.
- Replication dates (9, frozen before execution):
  - EARLY threshold environment (5): 2026-08-01, 08-03, 08-05, 08-07, 08-09
  - LATE threshold environment (4): 2026-08-26, 08-28, 08-29, 08-30
- Discovery date 2026-08-27 explicitly excluded from this replication
  set -- it is the population that generated the hypothesis under test and
  was already inspected in Experiment v1; including it would bias
  replication.
- N: 10, unchanged from the causal threshold-stability methodology.
- Entry: exact Delta=0 NEW entry rule (unchanged from
  causal_fixed_horizon_gross_edge_v1.py), with 100% entry availability
  enforced as a hard structural gate per date.
- Horizons: 5s / 15s / 30s / 60s. 15s and 30s are primary
  confirmatory horizons (frozen prior to this run, matching the
  horizons flagged by the v1 discovery result). 5s and 60s are
  secondary/reference.
- Direction: ALL actionable signals evaluated; LONG and SHORT
  reported separately throughout -- no long-only filter.
- Explicitly excluded: fees, spread, slippage, stops, targets,
  sizing, threshold optimization, horizon optimization, any parameter
  tuning.

## Structural Verification

9/9 structural PASS. 0 FAIL.

frozen_dates:            9
structural_pass_dates:   9
structural_fail_dates:   0
early_frozen:             5    early_pass: 5
late_frozen:              4    late_pass:  4

Every date independently satisfied: physical chronology reconstruction,
K5 emission frontier reproduction, frozen-kernel sample alignment,
combined_tr[F_position]==R invariant, A-position dominance, Gate 7
Stage A/B exchange-time coverage (fully empirical, no arbitrary
iteration cap), and 100% Delta=0 entry availability. No date was skipped,
substituted, or backfilled.

## Primary Results -- Cross-Day Replication (15s / 30s)

Each instrument-day is treated as one independent replication unit.
This is the primary evidence -- not the pooled signal-level statistics
below, since intraday signals are correlated, not independent
observations.

30s horizon:

| Direction | Mean-of-day-means | Median-of-day-means | Positive days |
|---|---:|---:|---:|
| ALL | +0.0901 bp | +0.1126 bp | 6/9 |
| LONG | +0.0605 bp | -0.0113 bp | 4/9 |
| SHORT | +0.1395 bp | +0.0509 bp | 5/9 |

15s horizon:

| Direction | Mean-of-day-means | Median-of-day-means | Positive days |
|---|---:|---:|---:|
| ALL | +0.0986 bp | +0.0851 bp | 6/9 |
| LONG | +0.1060 bp | +0.0102 bp | 6/9 |
| SHORT | +0.0986 bp | +0.1025 bp | 7/9 |

## Discovery Comparison

The Aug 27 discovery population (excluded from this replication set)
showed:

ETH LONG @ 30s: mean = +0.8283 bp, N = 2,026, 54.79% positive

The replication population's LONG @ 30s result:

mean-of-day-means:    +0.0605 bp
median-of-day-means:  -0.0113 bp
positive daily means:  4/9

The replication LONG 30s mean-of-day-means is approximately 13.7x
smaller than the Aug 27 discovery-day LONG 30s mean, and the
replication median-of-day-means is negative. Nine days
is too small a sample to draw a formal statistical conclusion from the
4/9 positive-day count in isolation; the magnitude comparison against
the discovery effect is the primary basis for this result's
interpretation.

## Secondary Evidence -- Pooled Signal-Level Aggregates

These are secondary evidence. Signals within a single day are
correlated, not independent replications, and pooling can let one large
day dominate the result. All four horizons are reported here (the
primary cross-day table above covers 15s/30s only, by design -- see
below).

| Horizon | Pooled N | Mean (ALL) | Median (ALL) | Positive % |
|---|---:|---:|---:|---:|
| 5s | 21,897 | +0.0969 bp | 0.0000 bp | 46.53% |
| 15s | 21,897 | +0.0816 bp | 0.0000 bp | 48.63% |
| 30s | 21,897 | +0.1007 bp | 0.0000 bp | 49.82% |
| 60s | 21,897 | +0.1564 bp | 0.0000 bp | 49.55% |

Signal-level positive fractions generally cluster near 50% across
horizons and splits, while pooled central tendencies (means) remain
small and pooled medians are flat at zero in most cases. One notable
exception: the LATE threshold-environment split at 30s shows a nonzero
pooled median of +0.0401 bp -- small in gross-return magnitude, though
its economic significance (if any) is not established by this
experiment. These secondary aggregates do not reproduce the
comparatively large Aug 27 LONG discovery effect.

## 5s / 60s Per-Day Table Clarification

per_day_replication_table.json contains entries for 15000 and 30000
(ms) only. This is not missing output -- the frozen design specifies
15s and 30s as the primary confirmatory horizons requiring per-day/
cross-day replication tables. 5s and 60s are reported only at the
pooled/secondary level (table above), consistent with their designated
secondary/reference role.

## Overshoot Disclosure

Fixed-horizon exits use the first qualifying physical trade strictly
beyond the requested exchange-time horizon; therefore realized exit
horizons overshoot the nominal 5s/15s/30s/60s targets. Overshoot was
measured and preserved prospectively for every signal and horizon. It
represents the historical proxy's discrete-trade exit construction and
should not be interpreted as exact timer-based execution.

Example (2026-08-01, all horizons, overshoot in milliseconds beyond the
nominal target):

| Horizon | N | Median | P90 | Max |
|---|---:|---:|---:|---:|
| 5s | 7,822 | 904 ms | 3,989 ms | 17,574 ms |
| 15s | 7,822 | 1,016 ms | 4,225 ms | 19,832 ms |
| 30s | 7,822 | 995 ms | 4,183 ms | 21,962 ms |
| 60s | 7,822 | 948 ms | 3,859 ms | 21,922 ms |

Full per-signal overshoot arrays (actual_horizon_ms_*) are preserved
in each date's .npz artifact for future audit.

## Interpretation / Limitations

This experiment establishes historical entry-to-exit gross price
movement only. It does NOT establish:

- Order execution, fills, or fill probability
- Slippage, spread-crossing cost, or fees
- Position sizing, stop/target rules, or portfolio-level P&L
- Live tradability or profitability of any kind
- That trade-flow imbalance contains no useful information generally
- That any other prospectively specified hypothesis on this or other
  instruments would fail

## Formal Conclusion

ETH LONG Post-Entry Continuation H1 -- REJECTED UNDER THE FROZEN
REPLICATION DESIGN. The comparatively large ETH LONG continuation
effect observed on the excluded Aug 27 discovery population did not
reproduce across nine prospectively frozen, previously unexamined
N10-eligible ETH instrument-days spanning both threshold environments.
This result rejects the specific ETH LONG fixed-horizon continuation
hypothesis that motivated Experiment v2. It does not establish that
trade-flow imbalance contains no information, that all implementations
are economically nonviable, or that other prospectively specified
hypotheses would fail.

## Research Boundary

Experiment v2 is CLOSED.

Cost-stress / economic-feasibility work is NOT STARTED and PAUSED
pending explicit direction to resume. No new experiment, horizon search,
threshold search, or hypothesis generation should proceed from this
closure without a separate, explicitly authorized research design.
