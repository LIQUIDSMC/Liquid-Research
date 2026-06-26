# Liquid Research — Mission Control

Last updated: 2026-06-26
(Updated during weekly review — see DAILY_OPERATIONS.md)

## Phase Status
Phase 0-4: Complete
Phase 5: v1 complete (paper_trader.py + paper_resolver.py),
         Research Improvements in progress (All-Passing migration
         done; classifier redesign pending)

## Dataset Status
Total paper trades: 48
Open: 30
Closed: 18

## Category Breakdown (all trades, 2026-06-26)
Other/Unknown: 21 (44%)
Geopolitical: 13
Sports: 7
Crypto Long-Duration: 4
Macro/Economic: 3
Political: 2

Note: Classifier hygiene patch (2026-06-25: added "wta", "atp",
"fifwc", adjectival geopolitical forms) reduced Other/Unknown from
21 to 8 unique markets at the time — but two trades created
EARLIER on 2026-06-25, before the patch landed that same day
("Will United States win on 2026-06-25?", "Will Japan win on
2026-06-25?", both fifwc-prefixed slugs), were stamped with the
old Other/Unknown classification before the fix took effect.
Manually corrected 2026-06-26 via direct reclassification —
verified trade_won/trade_pnl/winning_outcome unchanged, only
category/category_tier updated. This is why Other/Unknown's raw
count still shows 21 today despite the patch's real effectiveness
— it reflects a mix of genuinely-unsolvable proper-noun cases plus
ongoing natural growth from new daily snapshots, not a sign the
fix failed.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only — calculated from paper_trades.csv, 2026-06-26)
⚠️ NOT statistically reliable at n=18. Still far below the
30-trade first-look threshold.

IMPORTANT FINDING (2026-06-26): Total P&L turned NEGATIVE for the
first time, despite a still-high 77.8% win rate. Two new losses
today (-$100 each, both near-coin-flip entries at ~0.505 price)
outweighed the cumulative small wins from favored-entry trades.
This is the exact asymmetry the project anticipated early on: wins
on heavily-favored entries are small (a few dollars), while losses
are always the full $100 stake. A high win rate does NOT guarantee
positive expectancy if win sizes are small relative to loss sizes.
Treat this as a real, useful early signal to watch as volume
grows — NOT as evidence the system is broken or that
tradeability_score is bad, since 18 trades is still noise.

Win rate: 77.8% (14W / 4L)
Total realized P&L: -$76.84
Expectancy: -$4.27/trade
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
Status: Insufficient data (18 closed trades). Still far below the
30-trade first-look threshold. All-Passing migration continues
working as intended for score diversity. Negative expectancy
emerging at this small sample is itself a data point worth
tracking as volume grows, not evidence of an answer yet.

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

**Classifier proper-noun gap — PARTIALLY ADDRESSED 2026-06-25, REFRAMED AS DECISION 2026-06-25**
Keyword hygiene patch (wta/atp/fifwc + adjectival geo forms)
reduced Other/Unknown from 21 to 8 unique markets. Gamma
events/series metadata investigated as a further fix — found NOT
viable (series absent on all 6 tested remaining markets, events
helped only 1/6 cases). Decision: remaining proper-noun cases
(Starmer, Mojtaba Khamenei, etc.) accepted as Other/Unknown for
now — see zROADMAP.md "Proper-Noun Classification Limitation /
External-Knowledge Decision" and research/validated_findings.md.

**FIFWC pre-patch trades manually corrected — RESOLVED 2026-06-26**
Two trades (USA, Japan World Cup matches) were created on
2026-06-25 before that day's classifier patch landed, leaving them
stamped with stale Other/Unknown classification despite having
fifwc-prefixed slugs the patch now correctly catches. Manually
reclassified; trade_won/trade_pnl/winning_outcome verified
unchanged before and after.

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