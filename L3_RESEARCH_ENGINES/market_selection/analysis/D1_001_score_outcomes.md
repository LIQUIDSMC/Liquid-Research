# LRS-1 D1-001 — Tradeability Score vs Paper Outcomes

**DISCOVERY ANALYSIS — FROZEN D ONLY**

This report is hypothesis-generating discovery evidence, not independent
validation and not a live-money edge claim.

Protected V1 was not retained in the D1-001 analysis population and was not
analyzed, summarized, printed, or written by this script. The authoritative
CSV is necessarily scanned to recover frozen D rows; this is an analytical
isolation guarantee, not a claim that non-D source bytes are never parsed.

## Provenance

- Registration commit:
  `cfd4127510fa74b108e8d86bd91527ec50746cdb`
- Frozen D n: **396**
- Frozen D trade-id SHA-256: `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`
- Frozen detector SHA-256: `008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e`
- Frozen family primary SHA-256: `09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3`
- Frozen family derived SHA-256: `1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a`
- Primary predictor: `tradeability_score_at_entry`
- Fixed score split: **93.70**
- Entry price role: **robustness stratification only; not an independently
  tested predictor in D1-001**

## Missingness / usable population

| field | missing | usable |
| --- | --- | --- |
| trade_id | 0 | 396 |
| resolution_date | 0 | 396 |
| entry_date | 0 | 396 |
| tradeability_score_at_entry | 0 | 396 |
| entry_price | 0 | 396 |
| trade_won | 0 | 396 |
| trade_pnl | 0 | 396 |
| category | 0 | 396 |
| spread_label | 0 | 396 |
| liquidity | 0 | 396 |
| volume_24h | 0 | 396 |

## Primary continuous score associations

| Outcome | n | Pearson | Spearman |
| --- | --- | --- | --- |
| trade_won | 396 | -0.0627 | -0.0298 |
| trade_pnl | 396 | 0.0326 | 0.1129 |

## Fixed D0 score split

| score_group | raw_n | win_usable_n | pnl_usable_n | win_rate | pnl_mean | pnl_median | pnl_trimmed_mean_10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Low (<93.70) | 196 | 196 | 196 | 0.8265 | -3.8311 | 6.3550 | -0.4607 |
| High (>=93.70) | 200 | 200 | 200 | 0.8250 | 6.1219 | 8.1100 | 9.7947 |

## P&L outlier sensitivity

- Total realized P&L in usable D rows: **473.48**
- Sum of three largest absolute P&L magnitudes: **300.00**
- Three-largest-absolute share of total absolute P&L:
  **2.10%**
- Frozen robust estimator: 10% symmetric trimmed mean, reported in the
  score-group and sensitivity tables whenever group n >= 10.

## Entry-price robustness stratification

Entry price is not tested here as a standalone predictor. The following fixed
D0 strata only evaluate whether the registered score/outcome relationship is
stable across prespecified entry-price contexts.

| entry_price_stratum | n | score_win_pearson | score_win_spearman | score_pnl_pearson | score_pnl_spearman | low_n | low_win_rate | low_pnl_mean | low_pnl_median | low_pnl_trim10 | high_n | high_win_rate | high_pnl_mean | high_pnl_median | high_pnl_trim10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 <=0.7025 | 99 | 0.2176 | 0.2094 | 0.2056 | 0.1185 | 34 | 0.4412 | -24.5215 | -100.0000 | -29.0643 | 65 | 0.7385 | 23.8158 | 60.0000 | 30.1745 |
| Q2 0.7025–0.8675 | 99 | -0.2213 | -0.1658 | -0.2033 | -0.0047 | 47 | 0.8085 | 1.4736 | 20.4800 | 8.0418 | 52 | 0.7115 | -8.1352 | 25.0050 | -2.9386 |
| Q3 0.8675–0.9537 | 99 | 0.0798 | 0.1414 | 0.0618 | -0.1481 | 62 | 0.9032 | -1.6998 | 6.9500 | 8.2024 | 37 | 0.9459 | 2.1978 | 6.9500 | 7.6381 |
| Q4 >0.9537 | 99 | -0.0724 | -0.0760 | -0.0510 | 0.2384 | 53 | 1.0000 | 2.2447 | 1.6800 | 2.1300 | 46 | 0.9783 | 0.3924 | 2.5350 | 2.5511 |

## Temporal robustness

Calendar-month boundaries were fixed outcome-blind in D0.

| entry_month | n | score_pnl_pearson | score_pnl_spearman | low_n | low_win_rate | low_pnl_mean | low_pnl_median | low_pnl_trim10 | high_n | high_win_rate | high_pnl_mean | high_pnl_median | high_pnl_trim10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06 | 45 | -0.1067 | 0.0904 | 10 | 0.9000 | 8.9180 | 8.7750 | 11.3950 | 35 | 0.8286 | 6.5449 | 4.2800 | 10.4576 |
| 2026-07 | 108 | -0.0452 | -0.0426 | 44 | 0.9318 | 8.9548 | 7.7350 | 12.0028 | 64 | 0.8438 | 2.3981 | 6.6350 | 5.6421 |
| 2026-08 | 163 | 0.0523 | 0.1517 | 110 | 0.8091 | -7.2257 | 6.0750 | -3.6213 | 53 | 0.7925 | 4.9796 | 15.6100 | 7.7816 |
| 2026-09 | 80 | 0.0800 | 0.1779 | 32 | 0.7188 | -13.7266 | 5.4350 | -13.9288 | 48 | 0.8333 | 12.0396 | 13.6700 | 15.6160 |

## Frozen event-family / dependence sensitivity

- Families represented: **207**
- Largest family n: **14**
- Largest-family share of D: **3.54%**

Family-level equal-weight sensitivity:

| Outcome | family n | Pearson | Spearman |
| --- | --- | --- | --- |
| mean trade_won | 207 | -0.0627 | 0.0158 |
| mean trade_pnl | 207 | 0.0484 | 0.1257 |

Family-aware results are sensitivity analyses, not proof that observations are
fully independent.

## Category composition

| category | n | percent |
| --- | --- | --- |
| Other/Unknown | 180 | 45.4545 |
| Geopolitical | 105 | 26.5152 |
| Crypto Long-Duration | 64 | 16.1616 |
| Sports | 17 | 4.2929 |
| Political | 15 | 3.7879 |
| Macro/Economic | 14 | 3.5354 |
| Entertainment | 1 | 0.2525 |

## Correlated tradeability-feature context

These variables are contextual decomposition of the same conceptual
tradeability feature family. They are not independent discoveries under
D1-001.

| context_variable | vs_score_pearson | vs_score_spearman |
| --- | --- | --- |
| liquidity | 0.3604 | 0.7855 |
| volume_24h | 0.0477 | 0.2408 |

Spread-label score context:

| spread_label | n | mean_score | median_score |
| --- | --- | --- | --- |
| acceptable | 127 | 90.3276 | 95.2000 |
| excellent | 173 | 94.5139 | 98.8000 |
| extreme | 32 | 66.1000 | 68.9500 |
| wide | 64 | 85.1016 | 87.7500 |

## Interpretation constraints

- D is discovery evidence and has historical outcome exposure.
- D1-001 does not reset or erase Audit E.
- Statistical association and economic usefulness are separate questions.
- Entry-price stratification does not establish entry-price causality.
- Liquidity, volume, and spread-label context do not constitute separate
  validated predictors.
- Family-level sensitivity does not prove independence.
- No threshold may be changed after seeing these results under D1-001.
- No D1-001 result automatically promotes a hypothesis to V1.
- Protected V1 remains unopened.
