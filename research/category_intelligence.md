# Category Intelligence

Tracks category-level (not wallet-level, not single-market-level)
metrics: liquidity patterns, profitability patterns, spread
quality, resolution speed, and participation patterns, aggregated
across all markets within a given Active Research / Research
Queue category.

This is distinct from market_hypotheses.md (single testable
claims) and wallet_observations.md (wallet-specific behavior).
Category Intelligence accumulates structural findings about how
entire categories behave, which may eventually inform category
weighting in scanner or wallet discovery logic, but does so
later, deliberately, not automatically.

## Template

Category:
Metric tracked: (liquidity / profitability / spread quality / resolution speed / participation)
Observation:
Sample size: (how many markets/trades this is based on)
Confidence: Low / Medium / High
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted

## Current Entries

Category: All Active Research categories (Macro/Economic, Political, Geopolitical, Crypto Long-Duration)
Metric tracked: Resolution speed
Observation: As of 2026-06-20, all markets sampled by wallet_discovery.py's live discovery run remain genuinely unresolved (Open). This is a single-snapshot limitation, not a platform-wide finding about category resolution speed, and not a tooling gap. Confirmed via diagnostics/find_resolved_market.py after fixing the slug-lookup bug.
Sample size: 20 unique markets, single snapshot, single point in time
Confidence: Low (single snapshot; all Active Research markets sampled happen to share a similar medium-duration window)
Status: Reviewed — logged as a known limitation only, not a generalizable finding.
