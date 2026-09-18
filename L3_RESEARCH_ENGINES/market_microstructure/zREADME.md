# LRS-2 — Market Microstructure Engine

## Status

ACTIVE — Core indicators, research infrastructure, and research analytics/review are implemented.

Phase 1 — Core Indicators: COMPLETE, FROZEN
Phase 2 — Research Infrastructure: COMPLETE
Phase 3 — Research Analytics & Review: COMPLETE

Current research checkpoint: CP13 (2026-09-09).

At CP13, the research dataset contained 1,762 comparable OBI/Near-Book pairs across 468 markets, with 21 markets at n>=15. The aggregate same-sign rate was 58.97%, compared with 59.26% at CP12 despite 299 additional comparable pairs.

This describes stability of the observed aggregate rate over that interval only. It does not establish predictive value.

Collection continues until the next predefined research trigger documented in `zPROGRAM_ROADMAP.md`.

## Identity

LRS-2 studies order-book and market-microstructure indicators as a class, not a single metric.

Its governing question is:

Which microstructure indicators, if any, provide useful, stable information for future market selection or entry timing?

Evidence matters more than novelty. A new indicator only earns a place here if it addresses a real research gap identified by existing evidence.

LRS-2 currently studies two frozen core indicators:

- Order Book Imbalance (OBI)
- Near-Book Depth Imbalance, using the top N=5 price levels

Neither indicator is treated as predictive merely because it is mathematically valid or exhibits stable aggregate behavior.

Research questions, checkpoint evidence, infrastructure history, and future work are tracked in `zPROGRAM_ROADMAP.md` and `zRESEARCH_BACKLOG.md`.

## Upstream Contract

Current data flow:

L2 Prediction Markets canonical publication → LRS-2 Market Microstructure

Canonical input:

`L2_DOMAINS/prediction_markets/data/canonical/prediction_markets_latest.csv`

LRS-2 consumes the canonical publication produced by the Prediction Markets domain. The collection runners require:

- `instrument_id`
- `publication_id`

LRS-2 does not own Prediction Markets acquisition, scanning, classification, or canonical publication.

## Folder Structure

L3_RESEARCH_ENGINES/market_microstructure/
    analysis/
        agreement_matrix.py
        change_detector.py
        divergence_detector.py
        history.py
        market_report.py
        recurring_markets.py
        stability_tracker.py
    collection/
        run_near_book_depth.py
        run_obi.py
    data/
        near_book_depth_log.csv
        obi_log.csv
    indicators/
        near_book_depth.py
        obi.py
    presentation/
        report_printer.py
        weekly_review.py
    zPROGRAM_ROADMAP.md
    zREADME.md
    zRESEARCH_BACKLOG.md

Calculation logic remains separated from collection, analysis, and presentation so research behavior can be inspected and tested independently.

## Indicator 1 — Order Book Imbalance (OBI)

OBI measures the relative bid/ask depth represented in the order book.

The original research hypothesis was that order-book imbalance and its associated micro-price behavior might provide useful information beyond midpoint alone.

Phase 1 established calculation feasibility and mathematical sanity. That result did not establish predictive value.

OBI remains a frozen core indicator while evidence accumulates through the checkpoint process.

Calculation:
`L3_RESEARCH_ENGINES/market_microstructure/indicators/obi.py`

Collection:
`L3_RESEARCH_ENGINES/market_microstructure/collection/run_obi.py`

Output:
`L3_RESEARCH_ENGINES/market_microstructure/data/obi_log.csv`

## Indicator 2 — Near-Book Depth Imbalance

Near-Book Depth Imbalance tests whether pressure near the best available prices differs meaningfully from full-book imbalance.

The methodology uses the top N=5 price levels. N=5 is frozen for the current experiment and must not be changed during active evidence collection.

Calculation:
`L3_RESEARCH_ENGINES/market_microstructure/indicators/near_book_depth.py`

Collection:
`L3_RESEARCH_ENGINES/market_microstructure/collection/run_near_book_depth.py`

Output:
`L3_RESEARCH_ENGINES/market_microstructure/data/near_book_depth_log.csv`

No predictive claim is made by the calculation itself.

## Research Infrastructure

The engine includes research infrastructure for:

- loading accumulated indicator history;
- detecting changes across observations;
- measuring divergence between indicator sources;
- identifying recurring markets;
- tracking stability;
- building OBI/Near-Book agreement matrices;
- generating market-level reports;
- producing review-oriented presentation output.

The checkpoint statistics are based on real comparable OBI/Near-Book observations. Research logic and definitions remain governed by the implementation and the checkpoint record in `zPROGRAM_ROADMAP.md`.

## Current Research State

CP13 is the current frozen research checkpoint.

CP13 recorded:

- 1,762 comparable pairs;
- 468 markets;
- 21 markets with n>=15;
- 58.97% aggregate same-sign;
- CP12 aggregate same-sign: 59.26%;
- 299 additional comparable pairs between CP12 and CP13.

The small aggregate change over that interval is evidence of observed interval-level stability only.

It is not evidence that OBI, Near-Book Depth Imbalance, or their agreement predicts future market outcomes.

Behavior remains heterogeneous across individual markets.

The next checkpoint is triggered when predefined evidence conditions in `zPROGRAM_ROADMAP.md` are met, including total comparable pairs reaching at least 2,000 or additional markets reaching n>=15.

## Three-Question Check

Every indicator must answer these before earning a stronger role in Liquid Research:

1. Is it mathematically correct?
2. Is it stable across many markets?
3. Does it improve a trading decision?

Current state:

1. Mathematical implementation: established for the frozen core indicators.
2. Stability/behavior: under continued empirical observation; heterogeneous across markets.
3. Trading-decision improvement: not established.

The third question must not be inferred from the first two.

## Research Discipline

LRS-2 is an evidence-gathering research engine.

Observed stability, disagreement, persistence, reversals, or aggregate ratios are descriptive until separately validated against an outcome or decision-relevant target.

Historical checkpoints are retained because changes in interpretation, sample depth, and market behavior are part of the research record.

Frozen methodology is not changed merely because a later observation is surprising.

## Known Technical Debt

Technical debt is tracked separately from research conclusions.

Potential implementation cleanup must not silently alter:

- frozen indicator definitions;
- N=5 Near-Book methodology;
- pairing semantics;
- chronological semantics;
- log schemas;
- canonical input requirements;
- accumulated research evidence.

Any behavioral refactor requires its own verification rather than being bundled into documentation cleanup.

Known items:

- `collection/run_obi.py` currently fetches CLOB data twice per market — once via `get_market_clob_data()` and again via `fetch_market_by_slug()` + `fetch_order_book()`. This is not a blocker; refactor only with its own verification, not as part of documentation cleanup.

## Data

LRS-2's current engine-local outputs are:

`L3_RESEARCH_ENGINES/market_microstructure/data/obi_log.csv`

`L3_RESEARCH_ENGINES/market_microstructure/data/near_book_depth_log.csv`

These accumulated logs are research evidence and are not modified as part of documentation or architecture cleanup.

The upstream market universe is supplied through the L2 Prediction Markets canonical publication rather than duplicated inside LRS-2.

## Dependencies

Upstream authority:

`L2_DOMAINS/prediction_markets/data/canonical/prediction_markets_latest.csv`

Collection requires the canonical publication's `instrument_id` and `publication_id` fields.

LRS-2 does not require LRS-1 paper-trading results to collect or analyze its microstructure indicators.

Downstream integration into market selection or entry timing remains a research question, not an assumed dependency.
