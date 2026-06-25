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
category-performance analysis.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only — calculated from paper_trades.csv, 2026-06-25)
⚠️ NOT statistically reliable at n=14. Treat with skepticism, not confidence.
Win rate: 92.9% (13W / 1L)

## Category Performance
BLOCKED — currently 0 categories have ANY closed trades to
analyze (100% of closed trades are Other/Unknown as of
2026-06-23). This is more severe than originally anticipated.
Remains blocked until: (a) ≥20-30 closed trades per category, AND
(b) classifier redesign reduces Other/Unknown rate substantially.

## Score Bucket Performance
BLOCKED until ≥20-30 closed trades per bucket. Unlike category
performance, NOT blocked by the classifier issue — can proceed
independently once volume allows.

## Primary Research Question
"Does higher tradeability_score produce better paper-trade
outcomes than lower-score markets?"
Status: Insufficient data (9 closed trades). Encouraging sign:
2026-06-23's scanner run achieved real score diversity (72.3 to
99.7) vs. the first dataset's narrow 99+ clustering — All-Passing
migration working as intended for sample diversity. Still far
below the 30-trade first-look threshold.

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

**Sports filter desync (team-vs-team gap) — discovered 2026-06-24**
market_collector.py and market_classifier.py maintain separate,
unsynchronized SPORTS_KEYWORDS lists. Neither contains "vs." MLB
markets reached paper trading despite Phase 1's intent to exclude
sports. See zROADMAP.md backlog item "Sports Filter Desync /
Team-vs-Team Gap."

**Collector spread field misnamed — discovered 2026-06-24**
collectors/market_collector.py's spread field is a price-sum
integrity check (Yes+No deviation from 1.0), NOT a bid/ask
liquidity spread, despite sharing a name with scanner.py's real
spread_pct. Risk of future misinterpretation. See zROADMAP.md
backlog item "Misleading Collector Spread Field."

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