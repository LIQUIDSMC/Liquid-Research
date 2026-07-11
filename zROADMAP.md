# Liquid Research — Platform Roadmap

## Mission
Liquid Research is a multi-program research platform whose purpose
is to discover statistically defensible, monetizable trading edges
in prediction markets through disciplined, evidence-driven research.

This is a research platform. Not a trading bot. Not an execution engine.
Every research program must answer one question:
"Does this increase the probability of discovering a repeatable edge
that can eventually generate meaningful income?"

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
Layer 7 — Research Programs     programs/

Research Vault (platform knowledge): research/
Program A (active):               programs/program_a/
Program B (active):               programs/program_b/

---

## Long-Term Product Direction

Liquid Research should never depend on a single "magic indicator."
The long-term design philosophy is:

- Every signal must earn its place through independent validation
  before it is ever combined with others.
- Signals are researched individually first. Combination comes
  later, only after each component has demonstrated standalone value.
- Any future confidence framework should emerge from evidence,
  not be assumed upfront.
- This is a philosophy, not an implementation plan. No formulas,
  no weights, no architecture decisions are implied here.

The idea lifecycle:
Idea → Research Vault → Hypothesis → Experiment → Program → Finding
→ Platform Knowledge

Programs execute research. The vault discovers research.
Those are different responsibilities and should never be confused.

Potential signals currently under investigation or planned:
  Tradeability Score (Program A — active)
  Order Book Imbalance / Micro-Price (Program B — active)
  Calibration / Entry Price (Program C — queued)
  Cross-Venue Spread (Program D — future, requires infrastructure)
  Category-Aware Wallet Intelligence (Program E — blocked)
  Future signals not yet discovered

---

## Active Research Programs

This section is the authoritative index of all research programs.
Each program tests an independent hypothesis. Programs do not share
operational documentation — each program owns its own Mission Control,
Daily Operations, and program-specific notes inside its folder under
programs/.

Platform-wide knowledge (hypotheses, findings, vault) remains in
research/ and is shared across all programs.

---

### Program A — Tradeability Score / Scanner One
**Status:** ACTIVE — daily cycle running
**Folder:** programs/program_a/
**Hypothesis:** Higher tradeability_score (combining liquidity,
spread quality, and volume) predicts better paper-trade outcomes
than lower-score markets on Polymarket.
**Data:** data/simulator/paper_trades.csv
**Current milestone:** 33 closed trades — accumulating toward 100.
**Next checkpoint:** 100 closed trades — bucket comparisons become
meaningful.
**Does not interfere with:** All other programs. Program A runs
its daily cycle independently. No other program touches Program A's
data or methodology.
**Details:** programs/program_a/MISSION_CONTROL.md
**Build history:** programs/program_a/HISTORY.md

---

### Program B — Market Microstructure Research
**Status:** ACTIVE — Indicator 1 (OBI) Phase 1 complete, Phase 2
(stability testing) in progress.
**Folder:** programs/program_b/
**Identity:** Studies order-book and market-microstructure
indicators as a class. OBI is the first indicator studied, not the
entire scope. Governing question: which microstructure indicators
give the most useful, stable signal for market selection or entry
timing?
**Indicator 1 - OBI / Micro-Price Hypothesis:** Order book imbalance
(relative volume of bids vs. asks near the best price) predicts
short-term price movement better than midpoint alone. A
volume-weighted micro-price outperforms midpoint as a short-term
reference price on Polymarket.
**Infrastructure required:** None new. scanner/clob_client.py
already fetches and correctly parses full bid/ask book depth.
**Signal class:** Timing signal (when to enter) - fundamentally
different from Program A's selection signal (which market to trade).
**Current work:** programs/program_b/diagnostics/run_obi.py computes
OBI and micro-price correctly (verified 2026-07-03) using
programs/program_b/indicators/obi.py. Logging to
data/program_b/obi_log.csv established. Two queued indicator
candidates (near-book depth imbalance, spread-normalized OBI) noted
but not started. Collecting daily observations before any further
scope expansion.
**Blocking conditions:** None.
**Details:** programs/program_b/README.md

---

### Program C — Calibration / Entry Price Analysis
**Status:** QUEUED — not yet formally started as a Program.
**Hypothesis:** Implied probability at entry independently predicts
paper-trade outcomes. Polymarket may systematically misprice markets
in certain probability ranges, representing a directly actionable edge.
**Motivation:** Emerged from Program A's 2026-07-02 median-split
analysis — low-score trades appeared to outperform high-score trades,
consistent with entry-price and payout structure acting as a
confounding factor.
**Preliminary evidence (not yet Program C itself):** Program A's own
exploratory follow-up, programs/program_a/analysis/entry_price_analysis.py,
produced a first checkpoint at n=36 closed trades (2026-07-08):
weak correlation between tradeability_score and entry_price
(Pearson 0.078, Spearman 0.103), which does not support entry_price
as the explanation for the original median-split result. See
research/validated_findings.md. This is exploratory work performed
by Program A investigating its own result — not a formally launched
Program C, which per zARCHITECTURE.md's Domain/Program model would
require its own sustained infrastructure and roadmap, the same way
Program B was promoted from vault idea to active Program.
**Infrastructure required:** None yet. Uses existing paper_trades.csv.
**Blocking conditions:** None technical. Re-evaluation planned at
~100 closed trades (currently 39). At that point, an evidence-based
decision should be made: continue this narrow line of analysis
within Program A, or formally launch Program C with the broader
Entry/Execution Research scope zARCHITECTURE.md anticipates.
**Experiment design:** research/future_experiments.md

---

### Program D — Cross-Venue Spread Research
**Status:** FUTURE — requires new infrastructure
**Hypothesis:** Semantically equivalent markets on different
prediction market venues (e.g. Polymarket vs. Kalshi) exhibit
persistent, measurable price deviations that may be exploitable.
**Evidence:** Gebele & Matthes (2026), arXiv:2601.01706 — roughly
6% of events listed across platforms, with 2-4% persistent price
deviations even in liquid markets. Strongest external evidence for
any hypothesis in the research vault.
**Infrastructure required:** Kalshi data collection (does not exist).
**Blocking conditions:** Requires building an entirely new data
pipeline for a second venue before any testing can occur.
**Hypothesis:** research/market_hypotheses.md

---

### Program E — Category-Aware Wallet Research
**Status:** BLOCKED — pending Phase 3 resolved trade data
**Hypothesis:** Wallets that concentrate trading in a single
category (specialists) outperform wallets that spread trades across
categories (generalists). Category-aware wallet analysis can
identify reliably profitable participants.
**Infrastructure required:** None new. wallet_discovery.py and
wallet_analyzer.py already exist from Phase 3.
**Blocking conditions:** Requires wallets with meaningful resolved
trade history. All wallets discovered during Phase 3 had only
open/unresolved trades at time of analysis. This resolves naturally
as Polymarket markets mature — no active work needed to unblock.
**Hypothesis:** research/market_hypotheses.md

---

## Platform Research Backlog

### Queued Research Programs
(Defined hypotheses, no infrastructure blocker, ready to begin)

See Active Research Programs section above for Programs B and C.
Additional queued directions:

**Resolution Speed Research**
Investigate whether market duration at entry (days_left) affects
tradeability score correlation with outcomes, expectancy, or win
rate. Entirely self-contained — days_left already captured in
paper_trades.csv. Testable once sufficient closed trades exist
across varied duration buckets.

---

### Deferred / Blocked Research Programs

**Sports Research Framework**
Sports markets pass scanner and paper trading but are excluded
from wallet research. Decision needed: dedicated framework, or
reclassify consistently across all systems.
Blocking condition: None technical — this is a strategic decision.

**Crypto Ultra-Short Research Framework**
Crypto Ultra-Short markets excluded entirely. Revisit whether a
dedicated framework would be worth building or exclusion should
remain permanent.
Blocking condition: None technical — this is a strategic decision.

---

### Platform Engineering Backlog
(Infrastructure work not tied to a specific research program)

**Auto-generated Mission Control Status**
Generate operational statistics directly from paper_trades.csv
(trade counts, category counts, open/closed totals, performance
metrics) rather than manually updating MISSION_CONTROL.md. Keep
architecture/history documents human-authored while operational
status is generated automatically to eliminate transcription drift.
Small engineering task, permanent payoff.

**Price History Tracking**
Currently the scanner captures market state at a single daily
snapshot. No memory of how a market was priced on prior days
exists. Building even a simple price history tracker (appending
daily yes_price per active market to a running file) would unlock
an entirely new class of research questions including momentum,
late-stage repricing, and timing signals. Medium infrastructure
effort, high long-term research value.

**Automated Reclassification on Classifier Patch**
Dataset-wide reclassification has been run manually three times
after classifier patches. A script that automatically re-checks
all open trades against the current classifier after any patch
would eliminate this recurring maintenance burden.

**Resolution Cache**
Avoid repeatedly resolving the same market across large wallet
batches. Market resolutions should be cached locally.

**ConditionId Validation Layer**
Prevent malformed identifiers from contaminating discovery or
analysis. Invalid IDs should fail loudly, not silently.

**Combined Filter Stress Testing**
Validate user and market filtering under larger workloads —
multiple wallets, multiple markets, higher trade counts,
pagination behavior, truncation and duplication checks.

**Proper-Noun Classification Limitation — Standing Decision**
Remaining Other/Unknown trades (Starmer, Mojtaba Khamenei,
aliens-type questions) are not solvable by any text-based method
available to this project. Decision made 2026-06-25: accept as
Other/Unknown for now. Revisit only if a maintained lookup table
becomes worth the ongoing effort, Other/Unknown volume grows large
enough to justify the investment, or a fundamentally different
data source becomes available.
See research/validated_findings.md for the full investigation record.
