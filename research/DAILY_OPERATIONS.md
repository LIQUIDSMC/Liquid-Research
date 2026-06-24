# Daily Operations

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
df = pd.read_csv('data/simulator/paper_trades.csv')
print('Total:', len(df), '| Open:', (df['status']=='open').sum(), '| Closed:', (df['status']=='closed').sum())
print('Wins:', (df['trade_won']==True).sum(), '| Losses:', (df['trade_won']==False).sum())
print()
print('Category breakdown:')
print(df['category'].value_counts())
"
Expected: counts reconcile (open+closed=total, wins+losses=closed).
Category breakdown is for AWARENESS ONLY right now — "Other/Unknown"
is a known, tracked gap (see MISSION_CONTROL.md Technical Debt),
not yet reliable for analysis.

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

## Monthly Review (~45-60 min)
1. Full MISSION_CONTROL.md refresh against actual data
2. Reassess whether All-Passing sampling is still appropriate
   given actual passing-market volume per run
3. Revisit classifier accuracy — has "Other/Unknown" percentage
   changed? Is it time to prioritize the classifier redesign?
4. Review zROADMAP.md and zPHILOSOPHY.md for drift against
   actual project state