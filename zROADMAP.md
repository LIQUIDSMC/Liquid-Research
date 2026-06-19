# Liquid Research — Project Roadmap

## Mission
Find repeatable prediction-market edges through data collection,
market analysis, trader research, and paper trading simulation.

This is a research platform. Not a trading bot. Not an execution engine.

---

## Phase Exit Checklist

Before moving from one phase to the next, answer these honestly.
If the answer is "no" or "unclear," stay in the current phase.

1. **Did this phase actually improve something measurable?**
   Better data, better classification accuracy, better win-rate
   signal, better filter quality — not just "more code written."

2. **Did we find and fix any bugs this phase exposed?**
   Document them in git commit messages. If nothing broke, ask
   whether testing was thorough enough.

3. **Is the current code safe to keep running?**
   No execution, no wallet connection, no private keys, no
   real money at risk — confirm this is still true every phase.

4. **Does this phase move us closer to a real edge?**
   Per PHILOSOPHY.md: "Can this information improve expected
   returns?" If a phase produced interesting output with no
   plausible link to better market selection, note that honestly
   rather than treating it as progress.

5. **What stood out, surprised us, or looked risky?**
   Document anything unexpected — a wallet behaving oddly, an API
   field that didn't mean what we assumed, a result that seemed
   too clean or too convenient. These are often where real bugs
   or real signal hide.

6. **Is this safe to commit and build on top of?**
   Confirm tests pass, confirm output was manually sanity-checked
   against at least one known real-world case, not just internal
   consistency.

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
- Saves snapshot CSV, kill log CSV
- api_sanity_check.py created

### PHASE 2 — Market Classification ✅ COMPLETE
- market_classifier.py built and tested
- Three-tier category system (Active Research / Research Queue / Excluded)
- Word-boundary keyword matching (fixed nfl/inflation bug)
- include_in_wallet_research logic (True/False/Review)

### PHASE 3 — Wallet Research 🔄 IN PROGRESS
Goal:
Study trader behavior using public Data API.
Not copy-trading. Research only.

Completed:
- market_resolution.py — verified against live API, handles
  Confirmed/Open/Unconfirmed/Partial states
- wallet_analyzer.py Mode 1 (Recent Global Activity) — classify,
  filter, resolve, real win rate/P&L
- wallet_discovery.py — sources candidate wallets from Active
  Research markets, not leaderboard (684 wallets discovered)

Remaining:
- Patch B: wallet_analyzer.py Mode 2 (Discovered Market Context)
- Run full pipeline against a real discovered candidate to
  produce first genuine scored win rate

Done when:
- Mode 2 implemented and labeled clearly in output
- At least one candidate wallet produces real Confirmed/scored
  trades with a real win rate and P&L

### PHASE 4 — Scanner Engine 🔲 NOT STARTED
Goal:
Expand kill filters. Add order book depth checks. Add real
spread from CLOB API. Score surviving markets.

Files to build:
- scanner/scanner.py
- scanner/filters.py
- scanner/scorer.py

Done when:
- Terminal prints scanned / killed / passed summary
- Every killed market has a documented reason
- Every passed market has a score
- Top 10 opportunities ranked and explained

### PHASE 5 — Paper Trading Simulator 🔲 NOT STARTED
Goal:
Simulate entries and exits against real market data.
Track fake bankroll. Never use real money.

Files to build:
- simulator/paper_trader.py
- simulator/risk_sizer.py
- simulator/exit_logic.py

Done when:
- 100 simulated trades logged
- Win rate, avg win, avg loss, max drawdown tracked
- Every trade has entry reason, exit reason, confidence score

### PHASE 6 — Exit Logic Research 🔲 NOT STARTED
Goal:
Study whether top wallets exit early or hold to resolution.
Build exit rules based on data, not assumptions.

Done when:
- Report comparing hold-to-resolution vs early exit P&L
- Recommended exit rules documented

### PHASE 7 — Dashboard MVP 🔲 NOT STARTED
Goal:
React/Vite local dashboard showing scanner results and paper trades.
Built to eventually plug into LiquidOS.

Done when:
- Local web app shows scanner results
- Paper trade history visible
- Daily P&L, win rate, drawdown visible

### PHASE 8 — Signal Alerts 🔲 NOT STARTED
Goal:
Send signal alerts to Discord or email.
No live execution. Manual approval required.

### PHASE 9 — Execution Layer 🔲 NOT STARTED
LOCKED. Do not begin until:
- Phase 5 (Paper Trading) shows 100+ simulated trades
- Results show positive expectancy vs random market selection
- Legal pathway for live trading is explicitly confirmed
- Explicit human approval is given — this is never automatic