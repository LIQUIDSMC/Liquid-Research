# Liquid Research — Project Roadmap

## Mission
Find repeatable prediction-market edges through data collection,
market analysis, trader research, and paper trading simulation.

This is a research platform. Not a trading bot. Not an execution engine.

---

## Legal Notice
Polymarket US appears to have a regulated U.S. pathway through QCX LLC
d/b/a Polymarket US, which is listed by the CFTC as a Designated Contract
Market. However, the international Polymarket platform and older crypto/
on-chain tooling may still be separate and restricted for U.S. users.
This project must remain read-only and research-only until the exact
legal/trading pathway is confirmed.

Hard rules until explicitly reviewed:
- No wallet
- No private key
- No VPN
- No live trades
- No execution code
- Public/read-only data only
- Paper trading only after data collector is confirmed working

---

## Architecture Overview

Layer 1 — Data Collection       collectors/
Layer 2 — Market Analysis       analyzers/
Layer 3 — Scanner Engine        scanner/
Layer 4 — Wallet Research       analyzers/wallet_analyzer.py
Layer 5 — Decision Engine       brain/
Layer 6 — Paper Trading         simulator/

---

## Phase Status

### PHASE 0 — Planning ✅ COMPLETE
- Reviewed all reference repos
- Defined architecture
- Confirmed legal status
- Produced build plan

### PHASE 1 — Data Collection ✅ COMPLETE
- Python environment configured
- GitHub repo created (LIQUIDSMC/Liquid-Research)
- market_collector.py working
- Pulls 100 markets from Polymarket Gamma API
- Kills 80, passes 20
- Saves snapshot CSV
- Saves kill log CSV
- api_sanity_check.py created
- Repo cleaned and organized

### PHASE 2 — Wallet Research 🔄 IN PROGRESS
Goal:
Study trader behavior using public Data API.
Not copy-trading. Research only.

Research questions:
- Who are the most consistent traders by win rate?
- What market categories do they trade?
- Do they hold to resolution or exit early?
- What is their average trade size?
- How many trades before a wallet is worth studying?

Files to build:
- analyzers/wallet_analyzer.py

Outputs:
- data/wallets/wallet_rankings.csv
- logs/wallet_analysis_log.csv

Done when:
- Top 50 wallets ranked by win rate and P&L
- Minimum trade count filter applied
- Survivorship bias warning included
- CSV output saved

### PHASE 3 — Scanner Engine 🔲 NOT STARTED
Goal:
Expand kill filters.
Add order book depth checks.
Add real spread from CLOB API.
Score surviving markets.

Files to build:
- scanner/scanner.py
- scanner/filters.py
- scanner/scorer.py

Done when:
- Terminal prints scanned / killed / passed summary
- Every killed market has a documented reason
- Every passed market has a score
- Top 10 opportunities ranked and explained

### PHASE 4 — Paper Trading Simulator 🔲 NOT STARTED
Goal:
Simulate entries and exits against real market data.
Track fake bankroll.
Never use real money.

Files to build:
- simulator/paper_trader.py
- simulator/risk_sizer.py
- simulator/exit_logic.py

Done when:
- 100 simulated trades logged
- Win rate, avg win, avg loss, max drawdown tracked
- Every trade has entry reason, exit reason, confidence score

### PHASE 5 — Exit Logic Research 🔲 NOT STARTED
Goal:
Study whether top wallets exit early or hold to resolution.
Build exit rules based on data, not assumptions.

Done when:
- Report comparing hold-to-resolution vs early exit P&L
- Recommended exit rules documented

### PHASE 6 — Dashboard MVP 🔲 NOT STARTED
Goal:
React/Vite local dashboard showing scanner results and paper trades.
Built to eventually plug into LiquidOS.

Done when:
- Local web app shows scanner results
- Paper trade history visible
- Daily P&L, win rate, drawdown visible

### PHASE 7 — Signal Alerts 🔲 NOT STARTED
Goal:
Send signal alerts to Discord or email.
No live execution. Manual approval required.

### PHASE 8 — Execution Layer 🔲 NOT STARTED
LOCKED. Do not begin until:
-