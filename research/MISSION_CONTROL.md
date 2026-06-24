# Liquid Research — Mission Control

Last updated: <date>
(Updated during weekly review — see DAILY_OPERATIONS.md)

## Phase Status
Phase 0-4: Complete
Phase 5: v1 complete (paper_trader.py + paper_resolver.py),
         Research Improvements in progress (All-Passing migration
         done; classifier redesign pending)

## Dataset Status
Total paper trades: <n>
Open: <n>
Closed: <n>

## Category Breakdown (closed trades)
Political: <n>
Macro/Economic: <n>
Geopolitical: <n>
Crypto Long-Duration: <n>
Sports: <n>
Other/Unknown: <n>  ⚠️ KNOWN GAP — see Technical Debt below.
  Do not draw category conclusions while this is a large share
  of the dataset.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only)
⚠️ Not statistically reliable below ~30 closed trades.
Win rate: <n>% (<wins>W / <losses>L)
Average win: $<n>
Average loss: $<n>
Expectancy: $<n>/trade
Max drawdown: <n> (not meaningful yet)

## Category Performance
BLOCKED until: (a) ≥20-30 closed trades per category, AND
(b) classifier redesign reduces Other/Unknown to a small minority.
Computing this now would produce misleading results.

## Score Bucket Performance
BLOCKED until ≥20-30 closed trades per bucket. Unlike category
performance, NOT blocked by the classifier issue — can proceed
independently once volume allows.

## Primary Research Question
"Does higher tradeability_score produce better paper-trade
outcomes than lower-score markets?"
Status: Insufficient data (current: <n> closed trades, mostly
clustered near 99 — limited score diversity even post All-Passing
migration since today's passing universe is small).

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

## Future Category Analysis Section (placeholder, populate once unblocked)
Political:        win rate __  expectancy __
Macro/Economic:    win rate __  expectancy __
Geopolitical:      win rate __  expectancy __
Crypto Long-Dur:   win rate __  expectancy __
Sports:            win rate __  expectancy __