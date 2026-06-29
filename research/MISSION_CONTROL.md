# Liquid Research — Mission Control

Last updated: 2026-06-29
(Updated during weekly review — see DAILY_OPERATIONS.md)

## Phase Status
Phase 0-4: Complete
Phase 5: v1 complete (paper_trader.py + paper_resolver.py),
         Research Improvements in progress (All-Passing migration
         done; classifier redesign pending)

## Dataset Status
Total paper trades: 54
Open: 32
Closed: 22

## Category Breakdown (all trades, 2026-06-29)
Sports: 18
Geopolitical: 17
Other/Unknown: 8
Crypto Long-Duration: 5
Macro/Economic: 3
Political: 3

IMPORTANT FIX (2026-06-29): Discovered that 13 of 21 Other/Unknown
trades were stale-classification leftovers — created before a
classifier hygiene patch landed, never retroactively corrected
(same root cause as the 2026-06-26 USA/Japan fix, just at larger
scale). Ran a full dataset-wide reclassification: every trade
still marked Other/Unknown was re-checked against the CURRENT
classifier; 13 changed (mostly to Sports, 2 to Geopolitical).
Verified ALL protected fields (trade_won, trade_pnl,
winning_outcome, resolution_date, exit_reason, status,
entry_price, position_size) byte-for-byte unchanged before/after.
Real, current Other/Unknown count is 8, not 21 — this number had
been silently overstated since classifier patches began. Going
forward, consider re-running this dataset-wide reclassification
check periodically, since this same staleness will recur after
any future classifier patch unless trades are corrected at the
time of the patch, not just newly-created ones.

## Score Bucket Breakdown (closed trades)
90-100: <n>
75-90: <n>
Below 75: <n>

## Performance (closed trades only — calculated from paper_trades.csv, 2026-06-29)
⚠️ NOT statistically reliable at n=22. 8 trades from the 30-trade
first-look threshold. P&L has swung negative -> positive ->
negative again over the past several days, purely from
small-sample variance — concrete, repeated evidence that no
conclusion should be drawn from any single day's swing.

Win rate: 77.3% (17W / 5L)
Total realized P&L: -$21.56
Expectancy: -$0.98/trade
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
Status: Insufficient data (22 closed trades). 8 trades from the
30-trade first-look threshold. Category data quality significantly
improved today (see Category Breakdown) — once 30 is reached, the
category-performance comparison may finally be worth attempting
given Sports (18) and Geopolitical (17) now have real volume.

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