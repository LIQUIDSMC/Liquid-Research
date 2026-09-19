# Trade-Flow Imbalance Exploration (BTC/ETH)

Historical checkpoint: this is the original exploratory screen, first committed
in `c38ffbc`. At this checkpoint, the work was exploratory, hypothesis-generating
only, and not part of the official Crypto Domain roadmap. No conclusion had been
reached. It predates the later causal trade-flow research sequence.

For current LRS-3 research status and evidence boundaries, see
`L2_DOMAINS/crypto/zMISSION_CONTROL.md`.

## Question
Does aggressive trade-flow imbalance (10s trailing window, signed by
is_buyer_maker) predict short-horizon forward price movement?

## Method
- 10-second trailing lookback window per trade event
- Forward horizons: 5s, 15s, 30s, 60s
- Sampled every 20th trade per instrument-day
- Decile bucketing (D0 = most sell-heavy, D9 = most buy-heavy)
- Primary metric: D9-D0 spread at 60s

## Dates tested
BTC-USD and ETH-USD, each on: 2026-08-10, 08-18, 08-22, 08-25

## Results (D9-D0 spread at 60s)
| Instrument | Date | Realized Range | Abs Net Move | Trade Count | D9-D0 (60s) |
|---|---|---:|---:|---:|---:|
| BTC | Aug 10 | 0.02481 | 0.01454 | 388,085 | +0.000108 |
| BTC | Aug 18 | 0.01614 | 0.00317 | 753,146 | +0.000048 |
| BTC | Aug 22 | 0.03009 | 0.01623 | 1,910,150 | -0.000019 |
| BTC | Aug 25 | 0.03237 | 0.01930 | 451,271 | +0.000431 |
| ETH | Aug 10 | 0.03354 | 0.01987 | 222,687 | +0.000128 |
| ETH | Aug 18 | 0.01994 | 0.00251 | 191,173 | +0.000063 |
| ETH | Aug 22 | 0.05775 | 0.03725 | 420,935 | +0.000352 |
| ETH | Aug 25 | 0.02468 | 0.00785 | 127,659 | +0.000044 |

D9-D0 positive in 7 of 8 instrument-days (BTC Aug 22 slightly negative).

## Regime test (within-instrument median split, n=2 per bucket)
Higher realized-range/abs-net-move days show a larger D9-D0 spread for
both BTC and ETH. Trade-count split disagrees between instruments (BTC:
high volume -> weaker spread, driven entirely by Aug 22; ETH: high
volume -> stronger spread). For ETH, range/move/trade-count bucket
assignments were identical across all three splits (collinear on this
sample), so these are not three independent confirmations.

## Honest limitations
- n=8 total instrument-days. No statistical inference is valid.
- Multiple findings are single-date-dependent (esp. BTC trade-count
  split, driven entirely by Aug 22).
- No transaction costs, spread, or slippage modeled.
- No out-of-sample validation.
- Not yet tested for leakage/overfitting.

## Historical Next Steps at This Checkpoint
At the time of this exploration:
- More instrument-days were needed before any real conclusion.
- Formal Crypto Domain Phase 1 (per the Crypto roadmap as then recorded,
  preserved in the superseded snapshot in `L2_DOMAINS/crypto/zROADMAP.md`) had
  not begun; this work existed outside that official sequence.
- No production or methodology changes were made based on this exploration.
