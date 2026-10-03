# LRS-1 D1-002 — Trade Side vs Paper Outcomes

**DISCOVERY ANALYSIS — FROZEN D ONLY**

This report is hypothesis-generating discovery evidence, not independent
validation and not a live-money edge claim.

Protected V1 was not retained in the D1-002 analysis population and was not
analyzed, summarized, printed, or written.

## Provenance

- Prospective registration commit:
  `0a4c744e0a5425b151dd2d5390fbb0977bc64ede`
- Frozen D n: **396**
- Frozen D trade-id SHA-256: `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`
- Frozen detector SHA-256: `008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e`
- Frozen family primary SHA-256: `09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3`
- Frozen family derived SHA-256: `1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a`
- Expected direction: **none prespecified**
- Primary comparison: **Yes versus No**
- Entry-price role: **robustness stratification only**

## Missingness / usable n

| field | missing | usable |
| --- | --- | --- |
| trade_id | 0 | 396 |
| resolution_date | 0 | 396 |
| entry_date | 0 | 396 |
| side | 0 | 396 |
| entry_price | 0 | 396 |
| trade_won | 0 | 396 |
| trade_pnl | 0 | 396 |
| category | 0 | 396 |

## Primary side outcomes

| side | raw_n | win_usable_n | pnl_usable_n | win_rate | pnl_mean | pnl_median | pnl_trimmed_mean_10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Yes | 132 | 132 | 132 | 0.8258 | 10.2473 | 11.9250 | 14.4619 |
| No | 264 | 264 | 264 | 0.8258 | -3.3302 | 5.8200 | 0.3023 |

Primary descriptive contrast:

| contrast | win_rate_difference | pnl_mean_difference | pnl_median_difference | pnl_trim10_difference |
| --- | --- | --- | --- | --- |
| Yes - No | 0.0000 | 13.5774 | 6.1050 | 14.1596 |

The contrast is always defined as **Yes minus No**. Positive values therefore
favor Yes on the reported metric; negative values favor No. Because D1-002
registered no directional hypothesis, the observed sign must not be described
as prospectively predicted.

## Frozen P&L outlier sensitivity

- Total realized P&L: **473.48**
- Sum of three largest absolute P&L magnitudes:
  **300.00**
- Total absolute P&L: **14273.48**
- Three-largest-absolute share of total absolute P&L:
  **2.10%**

The primary side table reports the frozen 10% symmetric trimmed mean wherever
the side-specific n is eligible. The top-three concentration denominator is
total absolute P&L, matching the prospectively registered D1-002 convention.

## Entry-price robustness

Entry price is not tested as a standalone predictor. These fixed D0 strata
evaluate whether the registered Yes/No outcome contrast is stable across
prespecified entry-price contexts.

| entry_price_stratum | n | yes_n | yes_win_rate | yes_pnl_mean | yes_pnl_median | yes_pnl_trim10 | no_n | no_win_rate | no_pnl_mean | no_pnl_median | no_pnl_trim10 | yes_minus_no_win_rate | yes_minus_no_pnl_mean | yes_minus_no_pnl_median | yes_minus_no_pnl_trim10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 <=0.7025 | 99 | 56 | 0.7143 | 21.1084 | 60.1900 | 26.5033 | 43 | 0.5349 | -10.8784 | 43.8800 | -12.4429 | 0.1794 | 31.9868 | 16.3100 | 38.9461 |
| Q2 0.7025–0.8675 | 99 | 26 | 0.8077 | 3.6846 | 26.5900 | 9.7768 | 73 | 0.7397 | -6.1585 | 22.7000 | -0.4169 | 0.0680 | 9.8431 | 3.8900 | 10.1938 |
| Q3 0.8675–0.9537 | 99 | 27 | 0.9259 | 0.6404 | 6.9500 | 8.1765 | 72 | 0.9167 | -0.5744 | 7.2950 | 7.8948 | 0.0093 | 1.2148 | -0.3450 | 0.2817 |
| Q4 >0.9537 | 99 | 23 | 1.0000 | 2.4991 | 2.2000 | 2.4468 | 76 | 0.9868 | 1.0466 | 1.8800 | 2.2840 | 0.0132 | 1.4526 | 0.3200 | 0.1628 |

## Temporal robustness

Calendar-month boundaries were fixed outcome-blind in D0.

| entry_month | n | yes_n | yes_win_rate | yes_pnl_mean | yes_pnl_median | yes_pnl_trim10 | no_n | no_win_rate | no_pnl_mean | no_pnl_median | no_pnl_trim10 | yes_minus_no_win_rate | yes_minus_no_pnl_mean | yes_minus_no_pnl_median | yes_minus_no_pnl_trim10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06 | 45 | 18 | 0.7778 | 3.1672 | 4.2800 | 3.6869 | 27 | 0.8889 | 9.6756 | 11.7300 | 13.4500 | -0.1111 | -6.5083 | -7.4500 | -9.7631 |
| 2026-07 | 108 | 35 | 0.8571 | 13.9423 | 11.1100 | 18.4055 | 73 | 0.8904 | 0.8152 | 5.8200 | 6.7502 | -0.0333 | 13.1271 | 5.2900 | 11.6553 |
| 2026-08 | 163 | 41 | 0.7561 | -1.8866 | 8.1100 | 0.3948 | 122 | 0.8197 | -3.7177 | 6.3300 | -0.3336 | -0.0636 | 1.8311 | 1.7800 | 0.7284 |
| 2026-09 | 80 | 38 | 0.8947 | 23.2895 | 22.7150 | 28.4897 | 42 | 0.6905 | -17.7702 | 4.0550 | -18.1988 | 0.2043 | 41.0597 | 18.6600 | 46.6885 |

## Frozen event-family / dependence sensitivity

- Families represented: **207**
- Largest family n: **14**
- Largest-family share of D:
  **3.54%**
- Families containing both Yes and No:
  **24**

Primary family-equal-weight sensitivity:

| side | represented_families | family_cell_n | equal_weight_mean_trade_won | equal_weight_mean_trade_pnl |
| --- | --- | --- | --- | --- |
| Yes | 99 | 99 | 0.8054 | 10.0715 |
| No | 132 | 132 | 0.8146 | -4.3486 |

Each `family_key × side` cell is first reduced to its arithmetic-mean outcome.
For each side, represented family cells then receive equal weight regardless
of the number of trades in the cell.

Paired-family sensitivity:

| outcome | paired_family_n | mean_yes_minus_no | median_yes_minus_no |
| --- | --- | --- | --- |
| trade_won | 24 | 0.1156 | 0.0000 |
| trade_pnl | 24 | 33.8805 | 47.1262 |

Paired-family differences are always **Yes family-cell mean minus No
family-cell mean** and include only frozen families structurally containing
both sides. No outcome-based paired-family selection is permitted.

Family-aware results are sensitivity analyses, not proof that observations
are fully independent.

## Category composition

Context only; no category-specific outcome candidate is tested here.

| category | n | percent |
| --- | --- | --- |
| Other/Unknown | 180 | 45.4545 |
| Geopolitical | 105 | 26.5152 |
| Crypto Long-Duration | 64 | 16.1616 |
| Sports | 17 | 4.2929 |
| Political | 15 | 3.7879 |
| Macro/Economic | 14 | 3.5354 |
| Entertainment | 1 | 0.2525 |

## Interpretation constraints

- D is discovery evidence and has historical outcome exposure.
- D1-002 registered no directional Yes-versus-No hypothesis.
- Statistical description and economic usefulness are separate questions.
- Entry-price stratification does not establish entry-price causality.
- Family-aware sensitivity does not prove independence.
- Category is context only and cannot be silently promoted from this analysis.
- No alternate side grouping, threshold, subgroup, temporal boundary, or
  paired-family selection rule may be introduced after seeing these results.
- The execution report does not algorithmically assign candidate status.
- Candidate status must be recorded separately in the append-only registry
  after review of the complete prospectively specified evidence.
- No D1-002 result automatically promotes a hypothesis to V1.
- Protected V1 remains unopened.
