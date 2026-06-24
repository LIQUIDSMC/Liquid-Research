# Liquid Research — Project Roadmap

## Mission
Find repeatable prediction-market edges through data collection,
market analysis, trader research, and paper trading simulation.

This is a research platform. Not a trading bot. Not an execution engine.

---

## Research Integrity Principles

Research quality is more important than development speed.

Rules:
- Never trust a single API field without verification.
- Validate assumptions using live responses whenever possible.
- Prefer verification over convenience.
- Treat dramatic improvements as potential bugs until proven otherwise.
- Investigate unexpected outputs before calling them signal.
- Spot-check results against real-world examples.
- Avoid silent failures whenever possible.
- Fail loudly when data appears invalid.
- Manual verification is required before declaring a phase complete.

Recent lesson:
A discovery run appeared successful but was later found to be using
Polymarket numeric market IDs instead of conditionId hashes. The issue
produced believable output while hiding a critical bug. This project
should assume that plausible-looking results can still be wrong until
verified.

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

7. **Were outputs manually validated against external reality?**
   Do not rely solely on internal consistency. Verify at least one
   result against a live API response, known market, known wallet,
   or known real-world example.

8. **Could this result be explained by a bug rather than signal?**
   Treat dramatic improvements, suspiciously clean outputs,
   unexpected jumps, or surprising discoveries as potential bugs
   until verified.

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
- Order Book Imbalance / micro-price (logged in Research Vault,
  flagged as testable with existing clob_client.py — not yet
  promoted to roadmap status)


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
  directly (no duplicated logic) — this surfaced the classifier
  finding now tracked under "Classifier Architecture:
  Metadata-First Redesign" in the backlog
- research/DAILY_OPERATIONS.md and research/MISSION_CONTROL.md
  created as the operating procedure and single-source-of-truth
  scorecard for ongoing data collection

Done when:
- paper_trader.py creates one entry per passing market, not just Top 5 ✅
- Every new trade record includes category, category_tier,
  scanner_run_id, liquidity, volume_24h, spread_label ✅
- Recurrence of the same market_id across multiple trades is
  detectable from stored data ✅

Known follow-up (not blocking, tracked in backlog):
- Category breakdown currently shows ~42% Other/Unknown due to
  classifier proper-noun gap — category-performance analysis
  remains blocked until this is addressed (see Classifier
  Architecture backlog item)

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

---

## Backlog — Future Engineering Work (Not Yet Started)

This section is future work only. Completed patches are NOT
recorded here — git commit history is the source of truth for
what has already been built. Items are removed from this list
once implemented, not marked "done" in place.

### High Priority

**Resolution Cache**
Goal: Avoid repeatedly resolving the same market across large
wallet batches.

Done when:
- Market resolutions cached locally
- Duplicate API calls reduced
- Cache behavior documented
- Cache invalidation strategy documented

**ConditionId Validation Layer**
Goal: Prevent malformed identifiers from contaminating discovery
or analysis.

Done when:
- ConditionIds validated before query execution
- Invalid IDs fail loudly
- Legacy pre-fix snapshot data detected automatically

**Combined Filter Stress Testing**
Goal: Validate user+market filtering under larger workloads.

Done when:
- Multiple wallets tested
- Multiple markets tested
- Higher trade counts tested
- Pagination behavior verified
- Truncation and duplication checks completed

### High Priority

**Classifier Architecture: Metadata-First Redesign**
(Formerly "Discovery Classification Improvements" — expanded and
renamed following a concrete finding during Phase 5 Research
Improvements, 2026-06-23.)

Goal: Reduce category misclassification, which directly threatens
the project's category-performance research goal (comparing win
rate/expectancy across Political, Macro/Economic, Geopolitical,
Crypto Long-Duration, and Sports categories).

Finding that motivated this:
market_classifier.py currently uses keyword matching only.
Markets phrased with proper nouns instead of generic category
terms are systematically misclassified into Other/Unknown —
observed at 10/24 (42%) of paper trades in one real dataset.
Examples: "Starmer out by..." (no generic political keyword
present), "Will Germany win on [date]?" (no generic sports
keyword present — country/team names aren't in SPORTS_KEYWORDS).

Likely better source of truth, not yet verified in code:
Gamma API market responses include an `events` array, and events
often include a `series` field (e.g. a Fed rate market's event
ticker is "fed-decision-in-july-181" with series ticker "fomc").
This is platform-assigned metadata, not inferred from title text —
potentially far more reliable than keyword matching, but requires
direct verification of availability/consistency across market
types before being trusted as primary.

Proposed approach (tiered fallback, not single-method matching):
1. Primary: check events/series metadata if present and reliable
2. Secondary: keyword matching (current approach) as fallback
3. Tertiary: explicit "Unclassified — needs review" rather than
   silently defaulting to "Other/Unknown" as if it were a real,
   intentional category

Done when:
- Gamma events/series metadata reliability is empirically verified
  (not assumed) across a sample of market types
- Classification approach is redesigned per the tiered fallback
  above, OR a documented decision is made that keyword-only
  matching is sufficient with specific improvements
- Other/Unknown rate is measurably reduced on a real dataset
  (baseline: 42% as observed 2026-06-23)
- Category-performance research (in MISSION_CONTROL.md) is
  unblocked as a result

### Research Backlog (Deferred, Not Started)

**Sports Research Framework**
Goal: Sports markets currently pass through scanner and paper
trading but are excluded from wallet research. Decide whether
sports deserves its own analysis framework given this asymmetry,
or whether it should be reclassified consistently across all
three systems.

**Crypto Ultra-Short Research Framework**
Goal: Crypto Ultra-Short markets remain excluded from research
entirely. Revisit whether a dedicated framework (different
resolution speed, different metadata needs) would be worth
building, or whether exclusion should remain permanent.