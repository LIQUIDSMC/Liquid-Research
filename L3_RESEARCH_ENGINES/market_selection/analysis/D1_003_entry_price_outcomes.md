# LRS-1 D1-003 — Entry Price vs paper outcomes

## Status

- Discovery population: frozen D only.
- Raw D n: 396.
- Expected direction: none; two-sided exploratory analysis.
- V1 validation accessed: NO.
- D1-003 is not outcome-naive with respect to entry-price context.
- This report does not establish causality, independence, predictive superiority, or live-money edge.

## Frozen provenance

- D trade-id SHA-256: `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`.
- Family detector SHA-256: `008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e`.
- Registry SHA-256: `6aa04f6a23bde851125eaa656ac164abf01daecbacd85af9f6703914da7578dc`.

## Missingness / usability

- Raw n: 396.
- Raw missing `trade_id`: 0.
- Raw missing `entry_price`: 0.
- Raw missing `trade_won`: 0.
- Raw missing `trade_pnl`: 0.
- Raw missing `entry_date`: 0.
- Raw missing `side`: 0.
- Raw missing `category`: 0.
- Invalid/missing parsed `entry_price`: 0.
- Invalid/missing parsed `trade_won`: 0.
- Invalid/missing parsed `trade_pnl`: 0.
- Invalid/missing parsed `entry_date`: 0.
- Invalid recorded side: 0.

## Primary continuous associations

| Outcome | usable n | Pearson | Spearman |
| --- | --- | --- | --- |
| trade_won | 396 | 0.382227 | 0.379808 |
| trade_pnl | 396 | -0.033681 | -0.412216 |

## Fixed D0 entry-price quartiles

Frozen boundaries: Q1=0.7025, median=0.8675, Q3=0.9537.

| Quartile | n | win usable n | win rate | P&L usable n | P&L mean | P&L median | P&L trim10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | 99 | 99 | 0.636364 | 99 | 7.215152 | 52.670000 | 9.652963 |
| Q2 | 99 | 99 | 0.757576 | 99 | -3.573434 | 23.460000 | 2.340123 |
| Q3 | 99 | 99 | 0.919192 | 99 | -0.243131 | 6.950000 | 7.970864 |
| Q4 | 99 | 99 | 0.989899 | 99 | 1.384040 | 2.090000 | 2.324815 |

## Temporal sensitivity

| Month | n | win rate | P&L mean | P&L median | P&L trim10 | price-win Pearson | price-win Spearman | price-P&L Pearson | price-P&L Spearman |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06 | 45 | 0.844444 | 7.072222 | 5.820000 | 10.660270 | 0.472790 | 0.465321 | 0.014620 | -0.369365 |
| 2026-07 | 108 | 0.879630 | 5.069352 | 6.950000 | 9.318295 | 0.374857 | 0.350980 | -0.080233 | -0.548783 |
| 2026-08 | 163 | 0.803681 | -3.257117 | 6.440000 | -0.800763 | 0.405526 | 0.403768 | 0.034748 | -0.344260 |
| 2026-09 | 80 | 0.787500 | 1.733125 | 6.380000 | 3.974531 | 0.298946 | 0.337502 | -0.123388 | -0.384534 |

## Recorded-side sensitivity

| Side | n | win usable n | price-win Pearson | price-win Spearman | P&L usable n | price-P&L Pearson | price-P&L Spearman |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Yes | 132 | 132 | 0.320471 | 0.316642 | 132 | -0.139988 | -0.464321 |
| No | 264 | 264 | 0.445756 | 0.431057 | 264 | 0.100201 | -0.363261 |

## Frozen-family sensitivity

- Represented families: 207.
- Largest family n: 14.
- Largest-family raw-trade concentration: 0.035354.
- Family-aware results are sensitivity analyses and are not proof that observations are fully independent.

| Family-mean outcome | families n | Pearson | Spearman |
| --- | --- | --- | --- |
| trade_won | 207 | 0.417547 | 0.382494 |
| trade_pnl | 207 | -0.036446 | -0.306146 |

## P&L outlier concentration

- P&L usable n: 396.
- Total realized P&L: 473.480000.
- Total absolute P&L: 14273.480000.
- Sum of three largest absolute P&L magnitudes: 300.000000.
- Top-3 absolute P&L / total absolute P&L: 0.021018.

## Category composition context

Category is reported for population context only. No category-specific outcome analysis is authorized.

| Category | n | share |
| --- | --- | --- |
| Other/Unknown | 180 | 0.454545 |
| Geopolitical | 105 | 0.265152 |
| Crypto Long-Duration | 64 | 0.161616 |
| Sports | 17 | 0.042929 |
| Political | 15 | 0.037879 |
| Macro/Economic | 14 | 0.035354 |
| Entertainment | 1 | 0.002525 |

## Interpretation constraints

- D1-003 is exploratory Discovery-D evidence.
- Earlier D1 analyses already exposed outcome behavior across entry-price contexts; D1-003 is therefore not outcome-naive.
- No observed D1-003 effect may be represented as independent validation merely because it is statistically or economically large.
- Continuous and fixed-quartile views are one candidate family, not independent candidate discoveries.
- Temporal, side, family, and outlier views are robustness sensitivities, not separate candidate searches.
- No V1 promotion is implied by execution of this report.
