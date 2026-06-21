# API Discoveries

Undocumented, surprising, or hard-won API behavior. Confirmed discoveries graduate to validated_findings.md once verified.

## Template

API/Endpoint:
Discovery:
How it was found:
Verified? Yes / No (link verification if yes)
Relevance: (which module(s) affected)
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted



**Discovery:** In the two markets tested, the raw /book endpoint's bid and ask lists were sorted in opposite directions. Bids were sorted ASCENDING (worst to best); asks were sorted DESCENDING (worst to best). Index 0 in each list was therefore the WORST price on that side, not the best.

**How it was observed:** Tested against two structurally different markets — a binary economic market (Fed rate decision, ~$2.8M volume, negRisk=True) and a multi-outcome sports market (Ivory Coast World Cup winner, negRisk=True, much lower individual-outcome liquidity). The same sort pattern was observed in both.

**Implication for manual parsing:** Reading book["bids"][0] and book["asks"][0] as the best bid/ask produced incorrect results in both tests. Correctly identifying the best bid required max(price) across all bid entries; correctly identifying the best ask required min(price) across all ask entries.

**Observed behavior of official endpoints, across the two tested markets:**
- /spread was observed to match the correctly parsed book data (best ask - best bid) exactly, in both tests.
- /midpoint was observed to match the correctly parsed book data ((best ask + best bid) / 2) exactly, in both tests.
- /price?side=SELL was observed to match the correctly parsed best ASK, in both tests.
- /price?side=BUY was observed to match the correctly parsed best BID, in both tests.

**Limitation:** Only two markets were tested, and both were negRisk=True. A non-negRisk market has not yet been tested. This finding should not be treated as confirmed platform-wide behavior until tested against additional market types, including a non-negRisk market and a closed/illiquid market with a populated book.

Date verified: 2026-06-20
Evidence: diagnostics/clob_book_structure.py, two-market run, this session.
Affects: Any future CLOB-based scanner logic. Manual book parsing must scan for max/min by value, never assume position.
