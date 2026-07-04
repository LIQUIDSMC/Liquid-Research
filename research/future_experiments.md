# Future Experiments

Concrete enough to describe how they would be tested. Not yet scheduled on the roadmap.

## Template

Experiment:
Tests which hypothesis: (link to market_hypotheses.md)
Required data:
Required engineering effort: Small / Medium / Large
Expected signal if true:
Status: Unreviewed / Reviewing / Rejected / Archived / Promoted

## Current Entries
---

Experiment: Wallet archetype classification (specialist vs. generalist labeling)
Tests which hypothesis: Specialization-performance hypothesis in market_hypotheses.md
Required data: categories_touched (already produced by wallet_discovery.py) + per-wallet trade classification (already produced by wallet_analyzer.py). No new data source needed.
Required engineering effort: Small — a concentration metric computed from existing output, not a new pipeline.
Expected signal if true: Specialist wallets would show measurably higher win rate or P&L than generalist wallets, once resolved trade data exists for enough wallets to compare.
Status: Unreviewed — blocked on Phase 3's resolved-trade-data gap.

---

Experiment: Specialist leaderboards (per-category wallet rankings, e.g. Top Geopolitical Wallets, Top Macro Wallets)
Tests which hypothesis: Specialization-performance hypothesis, applied at a reporting/output level
Required data: Same as wallet archetype classification, plus enough resolved wallets per category to avoid the small-sample fragility already flagged in zROADMAP.md's Confidence Weighting backlog item.
Required engineering effort: Medium — primarily a reporting/aggregation layer once prerequisites exist.
Expected signal if true: Category-specific leaderboards would reveal whether some categories produce more skilled traders than others.
Status: Unreviewed — blocked on resolved-trade-data gap; additionally requires enough resolved wallets per category, not just enough overall.

---

Experiment: Delayed copy-trade backtest (research only, not a live system)
Tests which hypothesis: Copy-trading viability hypothesis in market_hypotheses.md
Required data: Full resolved trade history (timestamps, entry prices, outcomes) for at least one wallet — same data wallet_analyzer.py + market_resolution.py already produce once resolved trades exist.
Required engineering effort: Medium — needs realistic delay/slippage modeling, which is new logic, but no new data source.
Expected signal if true: A wallet's followed-with-delay P&L would be measurably lower than its actual P&L but still net positive, suggesting some edge survives a realistic follow delay.
Status: Unreviewed — blocked on resolved-trade-data gap.

---

Experiment: Mispricing scanner feasibility assessment (architecture-only, not buildable yet)
Tests which hypothesis: N/A — this is a feasibility note, not a testable hypothesis itself.
Required data: External, domain-specific data per market category (economic indicators, polling data, weather forecasting models) — none of which exist in Liquid Research today.
Required engineering effort: Large — effectively N separate forecasting research programs, one per category, not a single module.
Expected signal if true: N/A.
Status: Rejected for near-term consideration. Long-term direction only, contingent on acquiring external per-category data sources this project does not currently have. Trader-edge research (see market_hypotheses.md) preferred as the better-aligned direction given current codebase shape.

---

Experiment: Missing-market backfill
Tests which hypothesis: N/A — this is an infrastructure gap, not a testable research hypothesis.
Required data: None new. Uses the same Gamma slug-lookup method already proven reliable throughout this project (market_resolution.py's fetch_market_by_slug pattern).
Required engineering effort: Small-to-medium — a check-and-fetch-on-demand pattern: when a trade or wallet record references a market (by conditionId or slug) not present in the current local market snapshot, fetch that market individually and cache it locally rather than silently proceeding with incomplete context.
Expected signal if true: N/A — this isn't expected to reveal a hypothesis result, it's expected to close a data-completeness gap. Success would look like: fewer "Unknown" or missing-context cases in wallet_discovery.py / wallet_analyzer.py output.
Why it matters: wallet_discovery.py and wallet_analyzer.py may encounter trades from markets outside the most recent Gamma snapshot (e.g. a wallet trading a market that resolved or was created after the snapshot was taken). This can silently create incomplete market context without any error being raised.
Source: Concept observed via architecture review of poly_data (warproxxx) — see research/github_repositories.md. Reference only; no code copied.
Status: Unreviewed — future experiment, not a current Phase 4 patch. Later.

---

Experiment: Multi-dimensional wallet ranking framework (sample size + consistency + profitability + specialization + risk-adjusted performance, combined rather than ranked on a single axis)
Tests which hypothesis: Builds on, but does not replace, the specialization-performance hypothesis in market_hypotheses.md
Required data: Same prerequisites as other wallet performance work (resolved trade history) plus the confidence-weighting concept already on zROADMAP.md's backlog ("Confidence Weighting System" — sample-size weighting, minimum trade thresholds, statistical significance checks).
Required engineering effort: Medium — this is explicitly NOT a single sort-by-one-column leaderboard; combining multiple weighted dimensions into one ranking requires deliberate design of how dimensions trade off against each other (e.g. should a high-sample-size, moderate-win-rate wallet rank above a low-sample-size, high-win-rate one?).
Expected signal if true: A ranking that surfaces genuinely reliable wallets rather than ones that look good only on a single, possibly noisy metric.
Status: Unreviewed — blocked on resolved-trade-data gap; explicitly depends on zROADMAP.md's existing Confidence Weighting backlog item being addressed first, since ranking without sample-size awareness would repeat the exact "4/5 beats 40/50" problem already flagged there.

---

Experiment: Order book imbalance and micro-price calculation using existing clob_client.py data
Tests which hypothesis: Order book imbalance / micro-price hypothesis in market_hypotheses.md
Required data: None new — scanner/clob_client.py already fetches and correctly parses full bid/ask book depth for any market.
Required engineering effort: Small — this is primarily a new calculation added alongside the existing CLOB client output, not a new data pipeline. Distinct from the cross-venue and liquidity-shock hypotheses, which both require genuinely new infrastructure Liquid Research does not currently have.
Expected signal if true: Imbalance or micro-price would show measurable correlation with subsequent short-term price movement, beyond what midpoint alone shows.
Status: Unreviewed — the only experiment in this batch with no infrastructure blocker. Worth prioritizing over the cross-venue and liquidity-shock experiments specifically because it requires no new data source, just new analysis of data already being collected.

---

NOTE — Status update for Order Book Imbalance experiment (above):
Reviewed and promoted to Program B (2026-07-03). Status changed from "Unreviewed" to "Promoted — Program B." No longer a future experiment — now an active queued research program. See programs/program_b/README.md and zROADMAP.md.

---

Experiment: Calibration / Entry Price Analysis — does Polymarket price accurately reflect true probability, and does implied probability at entry independently predict outcomes?
Tests which hypothesis: Motivated by the median-split analysis finding (2026-07-02) documented in research/validated_findings.md. The observed result — low-score trades outperforming high-score trades — was consistent with entry-price and payout structure acting as a confounding factor. However, the relationship between tradeability score and entry price has not yet been quantified. This experiment tests whether that relationship is real and whether entry price is an independent predictor of outcomes.
Required data: Existing data/simulator/paper_trades.csv (entry_price, trade_won, trade_pnl, tradeability_score_at_entry fields). No new data source needed for the initial correlation analysis. Bucket analysis requires ~50-60 closed trades across varied entry price ranges.
Required engineering effort: Small — primarily terminal analysis scripts against existing CSV data, not a new pipeline.
Expected signal if true: (a) Entry price and tradeability score would show meaningful correlation, confirming the confounding factor observation. (b) Markets entered at lower implied probability (0.50-0.70) would show systematically higher expectancy than markets entered at higher implied probability (0.90+), independent of tradeability score. (c) Polymarket prices in certain ranges would show systematic miscalibration — resolving at rates meaningfully different from their implied probability — which would represent a directly actionable edge.
Status: Promoted — Program C candidate (2026-07-03). Reviewed and selected as the strongest queued research direction after Program B. Testable with existing data once Program B is underway. No infrastructure blocker.
