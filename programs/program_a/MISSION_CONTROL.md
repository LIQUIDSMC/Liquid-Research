# Program A — Tradeability Score / Scanner One
# Mission Control

> This document tracks Program A specifically. Platform-wide
> research programs and the experiment registry live in zROADMAP.md.
> Build history and phase details live in programs/program_a/HISTORY.md.

Last updated: 2026-07-14
(Updated during weekly review — see programs/program_a/DAILY_OPERATIONS.md)

## Phase Status
Phases 0-5: Complete. See programs/program_a/HISTORY.md for full
build history. Program A is now in active data collection toward
100 closed paper trades. Classifier redesign was investigated,
found not viable via the metadata approach, and reframed as a
standing decision (see research/validated_findings.md).

## Domain Producer Role (added 2026-07-10)
Program A is the current implementation of the Prediction Markets
Domain's producer, per zARCHITECTURE.md. It now also publishes the
Domain's canonical output (interface and data contract) for
downstream Programs to consume. Program B is currently the only
downstream consumer. See programs/program_a/domain/README.md for
the full contract and responsibilities.

## Dataset Status
Running since: 2026-06-22 (30 days as of 2026-07-22)
Total paper trades: 151
Open: 91
Closed: 60
Latest cycle (2026-07-14): 29 markets passed, canonical publication
20260714_190131. 14 new trades created. 4 newly closed: 2 wins, 2
losses.
  Wins: trade 102 (Elon Musk 160-179 tweets, +$2.77), trade 104
  (Bitcoin $65,000, +$57.48).
  Losses: trade 77 (US blockade on Iran, -$100.00), trade 103 (WTI
  $80, -$100.00).

## Category Breakdown (all trades, 2026-07-01)
Sports: 18
Geopolitical: 18
Other/Unknown: 11
Crypto Long-Duration: 5
Macro/Economic: 3
Political: 3

## Category Breakdown (closed trades only, 2026-07-01)
Sports: 17
Other/Unknown: 6
Geopolitical: 5
Crypto Long-Duration: 2
Macro/Economic: 0
Political: 0

Note: Two new LeBron James NBA trades (trade_ids 57, 58) landed
as Other/Unknown — pure proper-noun titles with no sports keyword
in title or slug. Accepted per the standing proper-noun decision.
Not patching team names into the classifier.

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

## Performance (closed trades only — calculated from paper_trades.csv, 2026-07-22)
⚠️ Still far from conclusive at n=60. Do not over-interpret.
Win rate: 85.0%
Total realized P&L: $234.24
Max drawdown: not yet meaningful at this volume

Entry-price confound checkpoint run at n=36 (2026-07-08) — weak
correlation (Pearson 0.078, Spearman 0.103) between score and
entry_price found. Does not support entry_price as the explanation
for the original median-split result. See
research/validated_findings.md for full checkpoint. Scheduled for
re-evaluation at 100 closed trades.

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
Status: FIRST EXPLORATORY ANALYSIS COMPLETED 2026-07-02 (n=32).

Median-split analysis results:
  Median tradeability score: 98.55
  High-score group (≥98.55, n=16): 75.0% win rate, -$1.77
    expectancy, -$28.35 total P&L
  Low-score group (<98.55, n=16): 93.8% win rate, +$13.44
    expectancy, +$215.06 total P&L

Why this result is NOT conclusive:
- ~85% of the low-score group's total P&L came from just 2 trades
  (Hormuz 40-ships +$98.02, Bitcoin dip +$83.82), both entered
  near 50% implied probability. High payouts on cheap entries,
  not score-related outperformance.
- The observed result is consistent with entry-price and payout
  structure acting as a confounding factor. High-score markets
  in this dataset cluster near 0.96+ entry prices (small wins
  when correct); low-score markets include more near-coin-flip
  entries (larger wins when correct). However, the relationship
  between tradeability score and entry price has not yet been
  quantified — this remains an observation, not a demonstrated
  causal relationship.
- Score distribution remains highly compressed — median of 98.55
  means even the "low" group contains high-quality markets.
- 32 trades is still too small to separate signal from noise.

Conclusion: The tradeability score hypothesis remains unresolved.
This analysis is a valuable exploratory checkpoint but not
sufficient evidence to validate or reject the hypothesis. Continue
accumulating trades toward the 100-trade milestone before drawing
any directional conclusion.

## Research Milestones
- [x] 30 resolved trades — first directional look ✅ 2026-07-01
- [ ] 100 resolved trades — bucket comparisons become meaningful
- [ ] ≥30 closed trades per category — category edge analysis:
      which categories produce highest expectancy? Does
      tradeability_score behave differently by category?
- [ ] 250 resolved trades — confidence building, repeat checks
- [ ] 500 resolved trades — threshold discussions become serious

## Current Hypotheses Under Active Test
Primary: "Does higher tradeability_score produce better paper-trade
outcomes than lower-score markets?" — see Primary Research Question
section below for current status.
Full hypothesis list: research/market_hypotheses.md

## Current Open Questions
See research/open_questions.md for the full platform list.
Most relevant to Program A currently:
- Do the 0.05/0.95 thresholds in filters.py represent the right
  cutoffs for flagging near-extreme pricing?
- Does clob_client.py's outcome_index=0 default correctly represent
  the primary outcome across all market types?

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
the fix works end-to-end. The separate "fifwc"-prefixed slug gap
discovered during verification was subsequently resolved via the
classifier hygiene patch (2026-06-25): "wta", "atp", "fifwc",
"cricket", "t20", "odi", "ipl" and sports awards terms added to
SPORTS_KEYWORDS. All known sports classification gaps resolved.

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