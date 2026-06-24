# Liquid Research — Mission Control

Last updated: 2026-06-23
(Updated during weekly review — see DAILY_OPERATIONS.md)

## Phase Status
Phase 0-4: Complete
Phase 5: v1 complete (paper_trader.py + paper_resolver.py),
         Research Improvements in progress (All-Passing migration
         done; classifier redesign pending)

## Dataset Status
Total paper trades: 34
Open: 25
Closed: 9

## Category Breakdown (all trades, 2026-06-23)
Other/Unknown: 13 (38%)
Geopolitical: 10
Sports: 4
Crypto Long-Duration: 1
Macro/Economic: 1
Political: 0

## Category Breakdown (closed trades ONLY, 2026-06-23)
⚠️ CRITICAL FINDING: 9/9 closed trades (100%) are Other/Unknown.
This is NOT a partial gap — it currently blocks ALL category-
performance analysis entirely, since there is not yet a single
classified, resolved trade to compare. Likely explanation: short-
duration markets (political tenure questions, single sports
matches with named players/teams) resolve fastest and happen to
be exactly the proper-noun-heavy questions the classifier
misses. Longer-duration Active Research markets (Fed decisions,
multi-year conflict questions) are still open. This pattern
should be re-checked as more trades close — if it persists, it
suggests resolution speed and classification failure may be
correlated, which would be a second real finding beyond the
classifier gap itself. See Technical Debt below.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only — calculated from paper_trades.csv, 2026-06-23)
⚠️ Not statistically reliable at n=9. Treat as directional
awareness only, not evidence.
Win rate: 88.9% (8W / 1L)
Total realized P&L: $89.57
Average win: $23.70
Average loss: -$100.00 (n=1 — single data point, not a real average yet)
Expectancy: $9.95/trade
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

## Future Category Analysis Section (placeholder, populate once unblocked)
Political:        win rate __  expectancy __
Macro/Economic:    win rate __  expectancy __
Geopolitical:      win rate __  expectancy __
Crypto Long-Dur:   win rate __  expectancy __
Sports:            win rate __  expectancy __