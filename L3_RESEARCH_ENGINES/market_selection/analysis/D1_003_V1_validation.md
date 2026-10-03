# LRS-1 D1-003 — V1 Validation

## Governance

- Methodology commit: `31faa3faa341de7ccdafaf32214306883b48a6bb`
- Specification SHA-256: `96362fa3025a11a5fcc4c4cf6d21674f1ccf86a4535b4d34e6b019ba8bfb14f7`
- Validation script SHA-256: `b8965e37c40308801c3d7cc3b39832c8bd311ff0cf0d94370736ae336453f99d`
- SciPy version: `1.18.1`
- Protected V1 n: **80**
- V1 trade-id SHA-256: `a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141`
- Discovery-D outcomes used in validation: **NO**
- Post-open methodology modification: **NO**

## Primary validation

| Outcome | n | Pearson | Spearman | Spearman two-sided p |
|---|---:|---:|---:|---:|
| trade_won | 80 | 0.448833 | 0.404333 | 0.000199 |
| trade_pnl | 80 | -0.061579 | -0.528386 | 0.000000 |

## Classification: **PASS**

Classification follows the frozen precedence in the V1 specification.

## Missingness

- Raw missing: `{'entry_price': 0, 'trade_won': 0, 'trade_pnl': 0, 'entry_date': 0, 'side': 0, 'category': 0}`
- Invalid numeric/date after deterministic parsing: `{'entry_price': 0, 'trade_won': 0, 'trade_pnl': 0, 'entry_date': 0}`

## Frozen family sensitivity

- `{'represented_families': 57, 'largest_family_size': 8, 'largest_family_raw_trade_concentration': 0.1, 'rule_matched_counts': {'deadline_series': 30, 'exact_or_singleton': 23, 'range_bucket': 1, 'threshold_window': 26}, 'win_spearman': 0.3906341395748341, 'win_pearson': 0.47918200379954995, 'win_n': 57, 'pnl_spearman': -0.43034909201692684, 'pnl_pearson': 0.006912562627754931, 'pnl_n': 57}`

## Fixed D0 entry-price quartiles — disclosure only

- `{'quartile': 'Q1', 'n': 18, 'win_rate': 0.6666666666666666, 'pnl_mean': 14.096666666666668, 'pnl_median': 60.475, 'pnl_trim10': 16.223125000000003}`
- `{'quartile': 'Q2', 'n': 12, 'win_rate': 0.8333333333333334, 'pnl_mean': 2.8241666666666667, 'pnl_median': 19.05, 'pnl_trim10': 9.304000000000002}`
- `{'quartile': 'Q3', 'n': 27, 'win_rate': 0.9629629629629629, 'pnl_mean': 4.60037037037037, 'pnl_median': 8.7, 'pnl_trim10': 8.325217391304346}`
- `{'quartile': 'Q4', 'n': 23, 'win_rate': 1.0, 'pnl_mean': 2.715652173913043, 'pnl_median': 2.46, 'pnl_trim10': 2.6694736842105264}`

## Temporal sensitivity — disclosure only

- `{'month': '2026-07', 'n': 4, 'win': {'n': 4, 'pearson': None, 'spearman': None, 'spearman_p_two_sided': None}, 'pnl': {'n': 4, 'pearson': -0.9971168891504177, 'spearman': -1.0, 'spearman_p_two_sided': 0.0}}`
- `{'month': '2026-08', 'n': 15, 'win': {'n': 15, 'pearson': -0.06372715321009706, 'spearman': 0.06185895741317418, 'spearman_p_two_sided': 0.8266479231312032}, 'pnl': {'n': 15, 'pearson': -0.5225294739665144, 'spearman': -0.8714285714285712, 'spearman_p_two_sided': 2.323647782163262e-05}}`
- `{'month': '2026-09', 'n': 61, 'win': {'n': 61, 'pearson': 0.5024362532491666, 'spearman': 0.45933032260781476, 'spearman_p_two_sided': 0.0001963664363079368}, 'pnl': {'n': 61, 'pearson': -0.011914814780412905, 'spearman': -0.43952999469616716, 'spearman_p_two_sided': 0.0003940588614538433}}`

## Recorded-side sensitivity — disclosure only

- `{'side': 'No', 'n': 61, 'win': {'n': 61, 'pearson': 0.28992023118648014, 'spearman': 0.2765008637003779, 'spearman_p_two_sided': 0.030996959880607133}, 'pnl': {'n': 61, 'pearson': -0.3447443920346774, 'spearman': -0.7413603893229767, 'spearman_p_two_sided': 8.312032476526978e-12}}`
- `{'side': 'Yes', 'n': 19, 'win': {'n': 19, 'pearson': 0.6039856649029933, 'spearman': 0.6110100926607787, 'spearman_p_two_sided': 0.005450039898317342}, 'pnl': {'n': 19, 'pearson': 0.2745897513984154, 'spearman': 0.0, 'spearman_p_two_sided': 1.0}}`

## P&L outlier sensitivity — disclosure only

- `{'total_realized_pnl': 474.29999999999995, 'total_absolute_pnl': 2274.3, 'top3_absolute_pnl': 300.0, 'top3_share_total_absolute_pnl': 0.1319087191663369}`

## Category composition — context only

- `{'category': 'Other/Unknown', 'n': 35, 'share': 0.4375}`
- `{'category': 'Crypto Long-Duration', 'n': 23, 'share': 0.2875}`
- `{'category': 'Geopolitical', 'n': 20, 'share': 0.25}`
- `{'category': 'Corporate Events', 'n': 1, 'share': 0.0125}`
- `{'category': 'Political', 'n': 1, 'share': 0.0125}`

## Interpretation boundary

This is protected-V1 validation of the prospectively frozen D1-003
entry-price divergence structure. PASS, if observed, means only that
the frozen directional replication criterion was satisfied under the
frozen V1 specification. It does not establish causality, universal
generalization, live-money profitability, or a production trading rule.
