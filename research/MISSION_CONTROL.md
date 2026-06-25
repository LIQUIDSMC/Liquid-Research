# Liquid Research — Mission Control

updated: 2026-06-25
(Updated during weekly review — see DAILY_OPERATIONS.md)

## Phase Status
Phase 0-4: Complete
Phase 5: v1 complete (paper_trader.py + paper_resolver.py),
         Research Improvements in progress (All-Passing migration
         done; classifier redesign pending)

## Dataset Status
Total paper trades: 45
Open: 31
Closed: 14

## Category Breakdown (all trades, 2026-06-25)
Other/Unknown: 21 (47%)
Geopolitical: 12
Sports: 5
Macro/Economic: 3
Crypto Long-Duration: 3
Political: 1

Note: Sports filter desync fix (resolved 2026-06-24) confirmed
working in production — "Texas Rangers vs. Miami Marlins" (the
exact market that exposed the original bug) resolved today as a
correctly-classified Sports trade, manually verified (side=No,
winning_outcome="Miami Marlins", trade_won=True, P&L=$15.61,
matches formula exactly). Other/Unknown's raw count continues
growing daily (15 -> 21), confirming the classifier proper-noun
gap remains the highest-leverage unresolved issue blocking full
category-performance analysis. Political, Macro/Economic, and
Crypto Long-Duration now all have at least some representation,
unlike 2026-06-23/24 when they had zero.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only — calculated from paper_trades.csv, 2026-06-25)
⚠️ NOT statistically reliable at n=14. A 92.9% win rate this
early is expected small-sample variance, NOT evidence of edge.
Win rate: 92.9% (13W / 1L)
Total realized P&L: $211.43
Expectancy: $15.10/trade
Max drawdown: not yet meaningful at this volume

## Category Performance
BLOCKED. As of 2026-06-25, several categories now have at least
one closed trade (Sports: several, others: still very few), but
none have anywhere near enough volume for meaningful comparison.
Remains blocked until: (a) ≥20-30 closed trades per category, AND
(b) classifier redesign reduces Other/Unknown rate substantially.

## Score Bucket Performance
BLOCKED until ≥20-30 closed trades per bucket. Unlike category
performance, NOT blocked by the classifier issue — can proceed
independently once volume allows.

## Primary Research Question
"Does higher tradeability_score produce better paper-trade
outcomes than lower-score markets?"
Status: Insufficient data (14 closed trades). Still far below the
30-trade first-look threshold. All-Passing migration continues
working as intended for score diversity.

## Research Milestones
- [ ] 30 resolved trades — first directional look (median split)
- [ ] 100 resolved trades — bucket comparisons become meaningful
- [ ] 250 resolved trades — confidence building, repeat checks
- [ ] 500 resolved trades — threshold discussions become serious

## Current Hypotheses Under Active Test
[pull live from research/market_hypotheses.md — list only ones
current data collection actually speaks to]

## Current Open Questions
[pull live from research/open_questions.md]

## Technical Debt (tracked here until resolved)

**Classifier proper-noun gap (HIGH PRIORITY)**
market_classifier.py uses keyword matching only. Markets using
proper nouns instead of generic terms (politician surnames,
country/team names in sports-style questions) are systematically
misclassified into Other/Unknown. Observed: 10/24 trades (42%)
in current dataset. This directly threatens the category-
performance research goal. Better source of truth likely exists:
Gamma's events/series metadata (platform-assigned, not inferred)
— needs direct verification before redesign. See zROADMAP.md
backlog item "Classifier Architecture: Metadata-First Redesign."

**Sports/Crypto Ultra-Short asymmetry**
Sports markets pass scanner + paper trading but are excluded from
wallet research. Crypto Ultra-Short excluded everywhere. Both
flagged in zROADMAP.md research backlog, not yet addressed.

**Sports filter desync — RESOLVED 2026-06-24, verified in production 2026-06-25**
Fixed via shared classify_market() reuse in collectors/market_collector.py.
"Texas Rangers vs. Miami Marlins" resolved 2026-06-25 as a
correctly-classified, correctly-scored Sports trade, confirming
the fix works end-to-end. See zROADMAP.md "Sports Filter Desync /
Slug-Blind Collector Check." Note: a separate, smaller gap was
found during verification — "fifwc"-prefixed slugs (individual
World Cup match markets) are still not recognized as Sports by
either system. Tracked separately as "FIFWC Slug Prefix Not
Recognized as Sports" in zROADMAP.md.

**Collector spread field misnamed — RESOLVED 2026-06-24**
Renamed to price_sum_deviation throughout (variable, CSV column,
table header, kill-reason message). Verified via live collector
run. See zROADMAP.md "Misleading Collector Spread Field."

**Legacy rows missing category metadata — RESOLVED 2026-06-24**
trade_ids 1-5 predated the category metadata patch and had NaN
category, silently excluded from category.value_counts() analysis.
Backfilled via simulator/backfill_2026_06_24_legacy_metadata.py
using the original scanner_run_20260621_2155.csv (confirmed still
present with complete data for all 5 markets). All protected
fields (P&L, resolution, status, etc.) independently verified
byte-for-byte unchanged after the write. Note: the backfill
script's own automated verification initially reported false
positives on NaN comparisons for unrelated open trades, due to a
NaN-vs-NaN string-comparison quirk in the script — confirmed via
direct pd.isna() checks that zero real mismatches existed. This
was a bug in the verification script's comparison logic, not in
the backfill itself.

## Future Category Analysis Section (placeholder, populate once unblocked)
Political:        win rate __  expectancy __
Macro/Economic:    win rate __  expectancy __
Geopolitical:      win rate __  expectancy __
Crypto Long-Dur:   win rate __  expectancy __
Sports:            win rate __  expectancy __