# GitHub Repositories

A repository existing, or having stars, is not evidence it works. See README.md.

## Template

Repository:
URL:
What it does:
Potential value to Liquid Research:
Notes:
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted

## Current Entries
---

**Repository:** poly_data (warproxxx)
**URL:** https://github.com/warproxxx/poly_data
**What it does:** A data pipeline that fetches Polymarket market metadata, scrapes order-filled events from the Goldsky subgraph (a third-party blockchain indexing service, NOT direct Polygon RPC reading — this corrects an earlier assumption), and processes raw events into structured trade data including price, direction, and USD amount.
**Potential value to Liquid Research:** Reference architecture only, not code to copy. Useful concepts: resumable market ingestion (offset/checkpoint-based resume instead of re-fetching from scratch each run), incremental updates, and missing-market backfill (auto-discovering and fetching markets referenced by trades but absent from the local snapshot).
**Notes:**
- Licensing is ambiguous and unresolved: GitHub's repository metadata shows GPL-3.0, but the README's own License section states "Go wild with it." This is a real discrepancy, not something to assume away. Treat as GPL-3.0 (the more restrictive reading) until explicitly clarified, and treat as concept-only reference regardless.
- Rejected concept: on-chain/subgraph trade reconstruction (mapping raw maker/taker asset IDs to BUY/SELL direction, price, etc.). Liquid Research already receives this same information pre-computed and ready to use via Polymarket's own Data API (`side`, `price`, `size`, `outcome` fields) — rebuilding it from raw chain events would be a regression in abstraction, not an improvement, and would add a new dependency (Goldsky) we don't currently need.
- One factual note worth remembering if raw event data is ever needed later: per the poly_data README, Polymarket's contract-level events should be filtered by the `maker` column when looking at a specific user's trades, even though this seems counterintuitive — a quirk of how Polymarket generates events at the contract level. Not currently applicable since we use the Data API, not raw events.
**Status:** Reference only / Later

---

**Repository:** poly-maker (warproxxx)
**URL:** https://github.com/warproxxx/poly-maker
**What it does:** An automated market-making bot for Polymarket — maintains orders on both sides of the order book, with real-time order book monitoring via WebSockets, position management with risk controls, and parameters configured via a Google Sheet.
**Potential value to Liquid Research:** Reference only, for execution/market-making architecture concepts: order-book awareness patterns, risk-control framing, and configuration-via-spreadsheet as a lightweight non-technical config pattern (the last of these is mildly interesting for the broader LiquidOS ecosystem vision, but not a near-term fit given Liquid Research's current single-developer, code-first workflow).
**Notes:**
- MIT licensed — no ambiguity here, unlike poly_data.
- The repository's own README states directly: "In today's market, this bot is not profitable and will lose money. Use it as a reference implementation for building your own market making strategies, not as a ready-to-deploy solution." This is the author's own stated assessment, not Liquid Research's inference.
- This reinforces, with direct external evidence, that Liquid Research's existing read-only, research-first posture (see zHANDOFF.md hard rules) is the correct approach — live execution and market making are explicitly not being pursued.
- Rejected concepts for current roadmap: live market making, automated execution, order placement. None of these are under consideration now or planned.
**Status:** Rejected as build direction / Reference only
