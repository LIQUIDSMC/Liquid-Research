# API Discoveries

Undocumented, surprising, or hard-won API behavior. Confirmed discoveries graduate to validated_findings.md once verified.

## Template

API/Endpoint:
Discovery:
How it was found:
Verified? Yes / No (link verification if yes)
Relevance: (which module(s) affected)
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted

## Current Entries

---

**Discovery:** In the two markets tested, the raw /book endpoint's bid and ask lists were sorted in opposite directions. Bids were sorted ASCENDING (worst to best); asks were sorted DESCENDING (worst to best). Index 0 in each list was therefore the WORST price on that side, not the best.

**How it was observed:** Tested against two structurally different markets — a binary economic market (Fed rate decision, ~$2.8M volume, negRisk=True) and a multi-outcome sports market (Ivory Coast World Cup winner, negRisk=True, much lower individual-outcome liquidity). The same sort pattern was observed in both.

**Implication for manual parsing:** Reading book["bids"][0] and book["asks"][0] as the best bid/ask produced incorrect results in both tests. Correctly identifying the best bid required max(price) across all bid entries; correctly identifying the best ask required min(price) across all ask entries.

**Observed behavior of official endpoints, across the two tested markets:**
- /spread was observed to match the correctly parsed book data (best ask - best bid) exactly, in both tests.
- /midpoint was observed to match the correctly parsed book data ((best ask + best bid) / 2) exactly, in both tests.
- /price?side=SELL was observed to match the correctly parsed best ASK, in both tests.
- /price?side=BUY was observed to match the correctly parsed best BID, in both tests.

**Limitation:** Three markets tested total — two negRisk=True (Fed rate decision, Ivory Coast World Cup), one negRisk=False (Strait of Hormuz traffic). All three showed identical sort order and identical official-endpoint matching behavior, regardless of negRisk status. This suggests the behavior is not negRisk-dependent, but remains based on a small sample (three active, currently-open markets). Not yet tested: a closed market with a populated book (all closed markets tested so far had empty books), and markets with more than two outcomes beyond the World Cup case already covered.


Date verified: 2026-06-20
Evidence: diagnostics/clob_book_structure.py, three-market run (one negRisk=False added), this session.

Affects: Any future CLOB-based scanner logic. Manual book parsing must scan for max/min by value, never assume position.

---

## External Data Source Candidates (Not Yet Evaluated for Quality)

**Source:** Jon-Becker/prediction-market-analysis (GitHub)
**What it claims to provide:** A framework plus dataset for Polymarket and Kalshi market/trade data, with an organized indexer + analysis structure (DuckDB queries against Parquet files).
**Verification status:** Repository existence and basic structure independently confirmed via direct lookup on 2026-06-20. The specific "850M+ state updates" scale claim referenced in the article that surfaced this repo was NOT independently confirmed against the repo's own documentation and should be treated as unverified until checked directly.
**Potential relevance:** If real and well-formed, this could be a useful reference for Kalshi data structure (Liquid Research currently has zero Kalshi integration) and for cross-venue research generally — but using it would require evaluating actual data quality firsthand, not assuming it from a description.
**Status:** Reference only. Not adopted. No code from this repo has been inspected, copied, or run.
