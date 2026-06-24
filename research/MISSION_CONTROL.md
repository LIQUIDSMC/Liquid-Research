# Liquid Research — Mission Control

Last updated: 2026-06-24
(Updated during weekly review — see DAILY_OPERATIONS.md)

## Phase Status
Phase 0-4: Complete
Phase 5: v1 complete (paper_trader.py + paper_resolver.py),
         Research Improvements in progress (All-Passing migration
         done; classifier redesign pending)

## Dataset Status
Total paper trades: 39
Open: 26
Closed: 13

## Category Breakdown (closed trades ONLY, 2026-06-24)
Other/Unknown: 6
Sports: 4
Missing category / legacy pre-patch rows: 3  ⚠️ trade_ids 1-5
  predate the metadata patch (2026-06-23) and have NaN category.
  Silently excluded from value_counts()-based analysis unless
  explicitly accounted for — see Technical Debt below.

Progress since 2026-06-23: previously 9/9 closed trades (100%)
were Other/Unknown. Today, 4 Sports trades resolved correctly.
Verified root cause: these markets' SLUGS contain "mlb" (e.g.
mlb-bos-col-2026-06-23), which analyzers/market_classifier.py
catches by searching title+slug combined — but
collectors/market_collector.py's Phase 1 filter only checks
question text, so these same markets bypassed intended Phase 1
sports exclusion (see zROADMAP.md "Sports Filter Desync / Slug-
Blind Collector Check"). Still 0 trades exist for Political,
Macro/Economic, Geopolitical, or Crypto Long-Duration —
cross-category comparison remains unanswerable.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only — calculated from paper_trades.csv, 2026-06-24)
⚠️ NOT statistically reliable at n=13. A 92.3% win rate this
early is expected small-sample variance, NOT evidence of edge.
Treat with extra skepticism, not extra confidence — a streak this
clean this early is exactly the kind of result the project's
Research Integrity Principles warn about.
Win rate: 92.3% (12W / 1L)
Total realized P&L: $195.82
Expectancy: $15.06/trade
Max drawdown: not yet meaningful at this volume

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

**Legacy rows missing category metadata — discovered 2026-06-24**
trade_ids 1-5 predate the category metadata patch and have NaN
category, silently excluded from category.value_counts() analysis.
See zROADMAP.md backlog item "Legacy Missing Category Metadata."

## Future Category Analysis Section (placeholder, populate once unblocked)
Political:        win rate __  expectancy __
Macro/Economic:    win rate __  expectancy __
Geopolitical:      win rate __  expectancy __
Crypto Long-Dur:   win rate __  expectancy __
Sports:            win rate __  expectancy __