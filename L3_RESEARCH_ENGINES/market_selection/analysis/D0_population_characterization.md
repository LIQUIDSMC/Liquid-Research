# LRS-1 D0 — Population Characterization

**AUDITED EXECUTION EVIDENCE — ACCEPTED FOR DESCRIPTIVE D0 FINDINGS**

D0 is descriptive and outcome-blind. It characterizes the frozen D population geometry before D1 outcome discovery.

## Provenance gates

- D n: **396**
- Detector SHA-256: `008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e`
- D trade-id SHA-256: `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`
- v1.1 assignment SHA-256: `a0a11cd96c8d188cdab17077f38d66932c48b2f2f44acde49815a89d1a7a07c6`
- Primary assignment SHA-256: `09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3`
- Derived assignment SHA-256: `1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a`
- Outcome fields loaded by D0: **NONE**
- Outcome relationships examined: **NONE**

## Authorized D0 ledger columns

- `trade_id`
- `market_id`
- `entry_date`
- `scanner_run_id`
- `tradeability_score_at_entry`
- `entry_price`
- `liquidity`
- `volume_24h`
- `spread_label`
- `side`
- `category`
- `category_tier`
- `recurrence_count`

## Missingness / usable n

| variable | missing_n | usable_n |
| --- | --- | --- |
| trade_id | 0 | 396 |
| market_id | 0 | 396 |
| entry_date | 0 | 396 |
| scanner_run_id | 0 | 396 |
| tradeability_score_at_entry | 0 | 396 |
| entry_price | 0 | 396 |
| liquidity | 0 | 396 |
| volume_24h | 0 | 396 |
| spread_label | 0 | 396 |
| side | 0 | 396 |
| category | 0 | 396 |
| category_tier | 0 | 396 |
| recurrence_count | 0 | 396 |

## Continuous-variable geometry

| variable | n | missing | mean | sd | min | q1 | median | q3 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tradeability_score_at_entry | 396 | 0 | 89.3540 | 11.8684 | 20.0000 | 82.8000 | 93.7000 | 98.6000 | 99.9000 |
| entry_price | 396 | 0 | 0.8186 | 0.1527 | 0.5050 | 0.7025 | 0.8675 | 0.9537 | 0.9895 |
| liquidity | 396 | 0 | 80986.0145 | 103461.0051 | 10.6800 | 28417.8150 | 49997.3100 | 90134.4300 | 1038552.5300 |
| volume_24h | 396 | 0 | 140175.0247 | 119799.7996 | 42671.4800 | 74072.8550 | 97749.8300 | 158426.4350 | 1020518.1600 |

## Frozen family geometry

- Frozen families represented: **207**
- Singleton families: **149**
- Multi-trade families: **58**
- Trades in multi-trade families: **247 (62.37%)**

### Family-size distribution

| family_size | family_count | trade_count | trade_percent |
| --- | --- | --- | --- |
| 1.0000 | 149.0000 | 149.0000 | 37.6263 |
| 2.0000 | 21.0000 | 42.0000 | 10.6061 |
| 3.0000 | 9.0000 | 27.0000 | 6.8182 |
| 4.0000 | 8.0000 | 32.0000 | 8.0808 |
| 5.0000 | 10.0000 | 50.0000 | 12.6263 |
| 6.0000 | 1.0000 | 6.0000 | 1.5152 |
| 7.0000 | 2.0000 | 14.0000 | 3.5354 |
| 8.0000 | 2.0000 | 16.0000 | 4.0404 |
| 10.0000 | 1.0000 | 10.0000 | 2.5253 |
| 11.0000 | 1.0000 | 11.0000 | 2.7778 |
| 12.0000 | 1.0000 | 12.0000 | 3.0303 |
| 13.0000 | 1.0000 | 13.0000 | 3.2828 |
| 14.0000 | 1.0000 | 14.0000 | 3.5354 |

### Ten largest frozen families

| family_key | family_size | rule_matched | trade_percent_of_D |
| --- | --- | --- | --- |
| us announces end of iranian blockade | 14 | deadline_series | 3.5354 |
| bitcoin\|reach\|in august | 13 | threshold_window | 3.2828 |
| israel x iran ceasefire continues | 12 | deadline_series | 3.0303 |
| tennis\|2026_mens_us_open\|winner | 11 | explicit_contest | 2.7778 |
| bitcoin\|dip to\|in august | 10 | threshold_window | 2.5253 |
| elon_musk_posts\|window=august 14 to august 21, 2026 | 8 | range_bucket | 2.0202 |
| wti\|high\|in july | 8 | threshold_window | 2.0202 |
| us x iran diplomatic meeting | 7 | deadline_series | 1.7677 |
| wti\|high\|in august | 7 | threshold_window | 1.7677 |
| lebron_james\|team\|2026-27 | 6 | destination_template | 1.5152 |

## Category composition

| value | n | percent |
| --- | --- | --- |
| Other/Unknown | 180 | 45.4545 |
| Geopolitical | 105 | 26.5152 |
| Crypto Long-Duration | 64 | 16.1616 |
| Sports | 17 | 4.2929 |
| Political | 15 | 3.7879 |
| Macro/Economic | 14 | 3.5354 |
| Entertainment | 1 | 0.2525 |

## Category-tier composition

| value | n | percent |
| --- | --- | --- |
| Active Research | 198 | 50.0000 |
| Research Queue | 180 | 45.4545 |
| Excluded | 18 | 4.5455 |

## Spread-label composition

| value | n | percent |
| --- | --- | --- |
| excellent | 173 | 43.6869 |
| acceptable | 127 | 32.0707 |
| wide | 64 | 16.1616 |
| extreme | 32 | 8.0808 |

## Side composition

| value | n | percent |
| --- | --- | --- |
| No | 264 | 66.6667 |
| Yes | 132 | 33.3333 |

## Temporal coverage

- Earliest parsed entry date: **2026-06-22 11:28:00**
- Latest parsed entry date: **2026-09-22 05:01:00**
- Unparseable/missing entry dates: **0**

| month | n |
| --- | --- |
| 2026-06 | 45 |
| 2026-07 | 108 |
| 2026-08 | 163 |
| 2026-09 | 80 |

## Scanner-run cohort composition

| scanner_run_id | n | percent |
| --- | --- | --- |
| scanner_run_20260621_2155.csv | 22 | 5.5556 |
| scanner_run_20260820_0502.csv | 21 | 5.3030 |
| scanner_run_20260802_2336.csv | 12 | 3.0303 |
| scanner_run_20260714_1901.csv | 11 | 2.7778 |
| scanner_run_20260730_0739.csv | 11 | 2.7778 |
| scanner_run_20260808_0501.csv | 11 | 2.7778 |
| scanner_run_20260901_0501.csv | 11 | 2.7778 |
| scanner_run_20260810_0501.csv | 10 | 2.5253 |
| scanner_run_20260623_2002.csv | 8 | 2.0202 |
| scanner_run_20260724_1502.csv | 8 | 2.0202 |
| scanner_run_20260727_1236.csv | 8 | 2.0202 |
| scanner_run_20260822_0501.csv | 8 | 2.0202 |
| scanner_run_20260708_0600.csv | 7 | 1.7677 |
| scanner_run_20260708_1754.csv | 7 | 1.7677 |
| scanner_run_20260720_0011.csv | 7 | 1.7677 |
| scanner_run_20260802_1620.csv | 6 | 1.5152 |
| scanner_run_20260806_0501.csv | 6 | 1.5152 |
| scanner_run_20260807_0501.csv | 6 | 1.5152 |
| scanner_run_20260819_0501.csv | 6 | 1.5152 |
| scanner_run_20260821_0501.csv | 6 | 1.5152 |
| scanner_run_20260823_0501.csv | 6 | 1.5152 |
| scanner_run_20260825_0501.csv | 6 | 1.5152 |
| scanner_run_20260826_0502.csv | 6 | 1.5152 |
| scanner_run_20260903_0501.csv | 6 | 1.5152 |
| scanner_run_20260908_0501.csv | 6 | 1.5152 |
| scanner_run_20260917_0501.csv | 6 | 1.5152 |
| scanner_run_20260703_2100.csv | 5 | 1.2626 |
| scanner_run_20260712_1203.csv | 5 | 1.2626 |
| scanner_run_20260731_0907.csv | 5 | 1.2626 |
| scanner_run_20260801_1133.csv | 5 | 1.2626 |
| scanner_run_20260827_0501.csv | 5 | 1.2626 |
| scanner_run_20260910_0501.csv | 5 | 1.2626 |
| scanner_run_20260916_0501.csv | 5 | 1.2626 |
| scanner_run_20260625_0530.csv | 4 | 1.0101 |
| scanner_run_20260720_0801.csv | 4 | 1.0101 |
| scanner_run_20260723_0906.csv | 4 | 1.0101 |
| scanner_run_20260811_0501.csv | 4 | 1.0101 |
| scanner_run_20260813_0501.csv | 4 | 1.0101 |
| scanner_run_20260831_0501.csv | 4 | 1.0101 |
| scanner_run_20260902_0501.csv | 4 | 1.0101 |
| scanner_run_20260909_0501.csv | 4 | 1.0101 |
| scanner_run_20260914_0501.csv | 4 | 1.0101 |
| scanner_run_20260918_0501.csv | 4 | 1.0101 |
| scanner_run_20260922_0501.csv | 4 | 1.0101 |
| scanner_run_20260624_1125.csv | 3 | 0.7576 |
| scanner_run_20260722_0916.csv | 3 | 0.7576 |
| scanner_run_20260725_1610.csv | 3 | 0.7576 |
| scanner_run_20260804_0501.csv | 3 | 0.7576 |
| scanner_run_20260805_0501.csv | 3 | 0.7576 |
| scanner_run_20260809_0501.csv | 3 | 0.7576 |
| scanner_run_20260812_0501.csv | 3 | 0.7576 |
| scanner_run_20260815_0501.csv | 3 | 0.7576 |
| scanner_run_20260817_0501.csv | 3 | 0.7576 |
| scanner_run_20260829_0501.csv | 3 | 0.7576 |
| scanner_run_20260830_0501.csv | 3 | 0.7576 |
| scanner_run_20260906_0501.csv | 3 | 0.7576 |
| scanner_run_20260907_0501.csv | 3 | 0.7576 |
| scanner_run_20260911_0501.csv | 3 | 0.7576 |
| scanner_run_20260912_0501.csv | 3 | 0.7576 |
| scanner_run_20260628_0824.csv | 2 | 0.5051 |
| scanner_run_20260629_1142.csv | 2 | 0.5051 |
| scanner_run_20260701_0838.csv | 2 | 0.5051 |
| scanner_run_20260710_0558.csv | 2 | 0.5051 |
| scanner_run_20260721_1609.csv | 2 | 0.5051 |
| scanner_run_20260726_0754.csv | 2 | 0.5051 |
| scanner_run_20260728_1055.csv | 2 | 0.5051 |
| scanner_run_20260814_0500.csv | 2 | 0.5051 |
| scanner_run_20260816_0500.csv | 2 | 0.5051 |
| scanner_run_20260818_0501.csv | 2 | 0.5051 |
| scanner_run_20260904_0501.csv | 2 | 0.5051 |
| scanner_run_20260905_0501.csv | 2 | 0.5051 |
| scanner_run_20260915_0501.csv | 2 | 0.5051 |
| scanner_run_20260625_1757.csv | 1 | 0.2525 |
| scanner_run_20260626_0942.csv | 1 | 0.2525 |
| scanner_run_20260627_0809.csv | 1 | 0.2525 |
| scanner_run_20260630_0931.csv | 1 | 0.2525 |
| scanner_run_20260703_0748.csv | 1 | 0.2525 |
| scanner_run_20260706_0850.csv | 1 | 0.2525 |
| scanner_run_20260707_0943.csv | 1 | 0.2525 |
| scanner_run_20260709_1021.csv | 1 | 0.2525 |
| scanner_run_20260711_0857.csv | 1 | 0.2525 |
| scanner_run_20260713_0545.csv | 1 | 0.2525 |
| scanner_run_20260715_0929.csv | 1 | 0.2525 |
| scanner_run_20260716_0811.csv | 1 | 0.2525 |
| scanner_run_20260717_0851.csv | 1 | 0.2525 |
| scanner_run_20260718_0943.csv | 1 | 0.2525 |
| scanner_run_20260828_0501.csv | 1 | 0.2525 |
| scanner_run_20260913_0500.csv | 1 | 0.2525 |
| scanner_run_20260919_0501.csv | 1 | 0.2525 |
| scanner_run_20260921_0501.csv | 1 | 0.2525 |

## Frozen predictor relationships P1-P5

These relationships are descriptive predictor/context geometry only. No economic outcome is involved.

### P1 / P2 / P3 / P5

| pair | n | pearson | spearman |
| --- | --- | --- | --- |
| P1 score vs entry_price | 396 | -0.2074 | -0.1866 |
| P2 score vs liquidity | 396 | 0.3604 | 0.7855 |
| P3 score vs volume_24h | 396 | 0.0477 | 0.2408 |
| P5 entry_price vs liquidity | 396 | -0.0840 | 0.0309 |

### P4 — score distribution by spread label

| spread_label | n | score_usable_n | mean | q1 | median | q3 |
| --- | --- | --- | --- | --- | --- | --- |
| acceptable | 127 | 127 | 90.3276 | 83.6500 | 95.2000 | 96.9000 |
| excellent | 173 | 173 | 94.5139 | 91.0000 | 98.8000 | 99.3000 |
| extreme | 32 | 32 | 66.1000 | 60.4250 | 68.9500 | 78.7500 |
| wide | 64 | 64 | 85.1016 | 76.9750 | 87.7500 | 92.3500 |

## Historical market_id duplication geometry

- Unique market_id values in D: **393**
- Duplicated market_id groups: **3**
- Excess rows beyond one trade per market_id: **3**
- Trades belonging to duplicated market_id groups: **6 (1.52%)**
- Duplicated market groups wholly within one frozen family: **3**
- Duplicated market groups spanning multiple frozen families: **0**

| market_id | trade_count | family_key_count | same_frozen_family |
| --- | --- | --- | --- |
| 0x0efcc493f7e7578cd5808b29e08c2535dee61c2a1fe841696e76e7892b29cca8 | 2 | 1 | True |
| 0x2bde6486e7067f48ee21344d8b5c1af458732536eb4d080932c88c3a7c2d2126 | 2 | 1 | True |
| 0xa43b6287d60caf4f330cc2f6884fd5a304c2110b9b847564ebbcaf22e7f66e3a | 2 | 1 | True |

## recurrence_count structural cross-check

- recurrence_count missing in D: **0**
- Comparable rows: **396**
- Exact matches to independently computed within-D recurrence ordinal: **387**
- Recorded recurrence greater than recurrence visible within D: **9**
- Recorded recurrence less than recurrence visible within D: **0**

This is a structural provenance cross-check, not an equality invariant. The recurrence implementation counts prior paper-trade rows with the same market_id at trade creation, whereas the D0 ordinal counts only occurrences visible inside frozen D. A follow-up read-only verification against the authoritative Pi3 ledger reproduced all 9 mismatches and confirmed that every affected row had the required number of earlier same-market_id rows in the full ledger (9/9 supported). Therefore the observed recorded-greater-than-within-D cases are explained by prior ledger occurrences outside the frozen D subset, not by a recurrence-count inconsistency.

## D0 boundary

- `trade_won`: **NOT LOADED**
- `trade_pnl`: **NOT LOADED**
- `winning_outcome`: **NOT LOADED**
- `exit_reason`: **NOT LOADED**
- `status`: **NOT LOADED BY D0 ANALYSIS DATAFRAME**
- `resolution_date`: **NOT LOADED BY D0 ANALYSIS DATAFRAME**

The frozen detector independently uses its previously audited identity/status/date fields only to reconstruct the frozen D population and family assignments.

**No D1 economic hypothesis has been generated, tested, ranked, promoted, or rejected by this report.**
