# Program A — Scanner One / Tradeability Score
# Build History & Phase Documentation

This file contains the complete build history for Program A (Scanner One /
Tradeability Score Research), migrated from zROADMAP.md on 2026-07-03.
The platform-level zROADMAP.md now tracks forward-looking platform direction
only. This file is the authoritative record of how Program A was built.

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
   Per zHANDOFF.md: "Can this information improve expected
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

7. **Were outputs manually validated against external reality?**
   Do not rely solely on internal consistency. Verify at least one
   result against a live API response, known market, known wallet,
   or known real-world example.

8. **Could this result be explained by a bug rather than signal?**
   Treat dramatic improvements, suspiciously clean outputs,
   unexpected jumps, or surprising discoveries as potential bugs
   until verified.

---

## Phase Build History

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

### PHASE 3 — Wallet Research ✅ COMPLETE
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
- wallet_analyzer.py Mode 2 (Discovered Market Context) — analyzes
  a wallet only within the markets that caused its discovery
- Critical bug fixed: resolve_trades_batch() now uses slug-based
  lookup as primary method instead of unreliable conditionId query
- Validation run: 20/20 real trades from a known-resolved market
  correctly scored, manually verified against real-world outcome

Done when:
- Mode 2 implemented and labeled clearly in output ✅
- At least one discovered wallet analyzed successfully ✅
- At least one confirmed market resolved correctly ✅
- Win rate and P&L generated from confirmed outcomes only ✅
- Results manually verified against raw trade history ✅

### PHASE 4 — Scanner Engine ✅ COMPLETE
Goal:
Expand kill filters. Add order book depth checks. Add real
spread from CLOB API. Score surviving markets.

Completed (five patches):
- Patch 1: scanner/clob_client.py — order book retrieval, correct
  bid/ask parsing (bids ascending, asks descending — validated
  against three structurally different markets)
- Patch 2: scanner/filters.py — empty-book kill filter, returns
  explainable pass/fail dict with specific reason
- Patch 3: scanner/filters.py — spread quality labels (excellent/
  acceptable/wide/extreme/unknown), informational only, not a
  kill filter, deliberately generous to avoid penalizing low/high-
  probability markets with structurally elevated spread_pct
- Patch 4: collectors/market_collector.py — added slug field to
  snapshot CSVs, eliminating dependency on unreliable conditionId
  lookup for scanner use
- Patch 5: scanner/scorer.py + scanner/scanner.py — full
  orchestration: reads snapshot, fetches CLOB data via slug,
  applies filters, computes tradeability_score, ranks top 10,
  saves results to data/scanner/. Live-verified against 21 real
  markets; a latent NaN-propagation bug was found in code review
  and fixed before commit.

Verification:
- 21/21 markets scanned successfully with real CLOB data
- Zero markets killed in this run — explained, not assumed: Phase
  1's existing Gamma-side filters already remove thin/illiquid
  markets before CLOB scoring reaches them, so the empty-book
  filter currently has nothing left to catch on this snapshot
- Independent CSV verification matched terminal output exactly
- No conditionId fallback logic anywhere in the scanner

Done when:
- Terminal prints scanned / killed / passed summary ✅
- Every killed market has a documented reason ✅
- Every passed market has a score ✅
- Top 10 opportunities ranked and explained ✅

Deferred to future backlog (not required for Phase 4 completion):
- Depth-near-inside-market as a ranking signal
- Order Book Imbalance / micro-price (promoted to Program B,
  2026-07-03)

### PHASE 5 — Research Improvements ✅ COMPLETE (2026-06-23)

Goal:
Remove Top-5 selection bias and capture metadata required for
category and score-bucket analysis, before the dataset scales.

Completed:
- paper_trader.py converted from Top 5 to All Passing Markets —
  verified live: 19 new trades created in one run vs. 5 previously
- Every new trade record now includes category, category_tier,
  scanner_run_id, liquidity, volume_24h, spread_label,
  recurrence_count
- Category classification reuses analyzers/market_classifier.py
  directly (no duplicated logic)
- programs/program_a/MISSION_CONTROL.md and
  programs/program_a/DAILY_OPERATIONS.md created as the operating
  procedure and single-source-of-truth scorecard for ongoing
  data collection

Done when:
- paper_trader.py creates one entry per passing market, not just Top 5 ✅
- Every new trade record includes category, category_tier,
  scanner_run_id, liquidity, volume_24h, spread_label ✅
- Recurrence of the same market_id across multiple trades is
  detectable from stored data ✅

### Domain Producer Role — Prediction Markets Canonical Output ✅ COMPLETE (2026-07-10)
Not part of the original Phase 0-9 sequence. Added following the
Domain/Program architecture defined in zARCHITECTURE.md. Program A
is the current implementation of the Prediction Markets Domain's
producer, responsible for publishing a canonical output
(data/approved_markets/prediction_markets_latest.csv) that serves
as the interface for downstream Programs — Program B is the first
consumer. Implemented in
programs/program_a/domain/publish_canonical_output.py. Verified
against real scanner/snapshot data with structural and per-row
validation (missing slug/market_id handling, duplicate detection,
classification failure logging). Program A's own internal pipeline
(paper_trader.py, scanner.py) continues reading its own internal
snapshot/scanner artifacts directly — this is internal
implementation detail per zARCHITECTURE.md Section 5, not a
downstream consumer relationship, and required no changes.

### PHASE 6 — Exit Logic Research 🔲 NOT STARTED
Goal:
Study whether top wallets exit early or hold to resolution.
Build exit rules based on data, not assumptions.

Note: This phase covers wallet exit behavior (do profitable wallets
exit before resolution?), which is distinct from Resolution Speed
Research (does market duration at entry predict outcomes?). Both
are related but independent research directions.

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
