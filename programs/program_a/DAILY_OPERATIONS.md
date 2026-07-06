# Program A — Tradeability Score / Scanner One
# Daily Operations

> This is the operating procedure for Program A's daily cycle only.
> Other programs maintain their own operating procedures in their
> respective program folders under programs/.

Run in order, in the activated venv. ~15-30 minutes including review.


## Step 0 — Activate Environment
    source venv/bin/activate

## Step 1 — Collect Fresh Markets
    python3 collectors/market_collector.py
Expected: fetched/killed/passed counts. New file in
data/markets/snapshot_<timestamp>.csv.

## Step 2 — Scan and Score
    python3 scanner/scanner.py
Expected: scanned/killed/passed counts, top-10 table. New file in
data/scanner/scanner_run_<timestamp>.csv.

## Step 3 — Create Paper Trades (All Passing Markets)
    python3 simulator/paper_trader.py
Expected: new trades created vs. skipped counts. Every passing
market gets a trade unless already open or missing data — NOT
limited to top scores.

## Step 4 — Resolve Open Trades
    python3 simulator/paper_resolver.py
Expected: open checked / newly closed / still open counts.

## Step 5 — Review
    python3 -c "
import pandas as pd
from datetime import datetime

pd.set_option('display.max_colwidth', 60)

df = pd.read_csv('data/simulator/paper_trades.csv')
closed = df[df['status']=='closed']

first_trade_date = pd.to_datetime(df['entry_date']).min()
days_running = (datetime.now() - first_trade_date).days

print('=== SUMMARY ===')
print()
print('Program A running since:', first_trade_date.strftime('%Y-%m-%d'), f'({days_running} days, {round(days_running/30.44, 1)} months)')
print()
print('Total trades:', len(df), '| Open:', (df['status']=='open').sum(), '| Closed:', len(closed))
print('Wins:', (closed['trade_won']==True).sum(), '| Losses:', (closed['trade_won']==False).sum())
print()
print('Total P&L: \$' + str(round(closed['trade_pnl'].sum(), 2)))
print('Expectancy: \$' + str(round(closed['trade_pnl'].mean(), 2)), 'per trade')
print('Win rate:', round((closed['trade_won']==True).sum() / len(closed) * 100, 1), '%')
print()
print('Category breakdown (all trades):')
print(df['category'].value_counts())
"
Expected: counts reconcile (open+closed=total, wins+losses=closed).
Category breakdown is for AWARENESS ONLY — Other/Unknown is a known,
accepted gap for proper-noun markets. See MISSION_CONTROL.md for
current Other/Unknown count and standing decision.


---

## Weekly Review (~30 min)
1. Re-run Step 5's query, update MISSION_CONTROL.md's Dataset
   Status and Performance sections with current numbers
2. Check whether any milestone (30/100/250/500 resolved trades)
   has been newly reached — if so, run the corresponding analysis
   from MISSION_CONTROL.md's Research Milestones section
3. Check market_id recurrence — has any single market dominated?
   python3 -c "
import pandas as pd
df = pd.read_csv('data/simulator/paper_trades.csv')
print(df['market_id'].value_counts().head(10))
"
4. Note anything surprising in research/open_questions.md
5. Check zROADMAP.md program registry — are any blocked programs
   now unblocked? Any new candidates for promotion?


## Monthly Review (~45-60 min)
1. Full MISSION_CONTROL.md refresh against actual data
2. Reassess whether All-Passing sampling is still appropriate
   given actual passing-market volume per run
3. Revisit classifier accuracy — has "Other/Unknown" percentage
   changed? Is it time to prioritize the classifier redesign?
4. Review zROADMAP.md and zHANDOFF.md for drift against
   actual project state