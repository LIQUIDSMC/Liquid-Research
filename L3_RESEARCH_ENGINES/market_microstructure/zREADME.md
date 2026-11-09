# LRS-2 — Market Microstructure Engine

## Status

ACTIVE — Core indicators, research infrastructure, and research analytics/review are implemented.

Phase 1 — Core Indicators: COMPLETE, FROZEN
Phase 2 — Research Infrastructure: COMPLETE
Phase 3 — Research Analytics & Review: COMPLETE

Current research checkpoint: CP16 (2026-10-01).

At CP16, the frozen research population contained 2,431 comparable OBI/Near-Book pairs across 630 markets, with 29 markets at n>=15. The aggregate same-sign rate was 60.43% (1,469/2,431), compared with 60.48% (1,399/2,313) at CP15 across 118 additional comparable pairs.

This describes the observed checkpoint interval only. No frozen statistical threshold has been established for classifying the movement as a trend, stability, instability, or predictive signal.

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

CP17 is the current research checkpoint.

The natural CP17 trigger fired on 2026-10-04 at the scheduled 06:05 PDT
Sentinel run, when the live calculation reported 2,515 comparable pairs and
29 markets at n>=15. The frozen 2,500-pair collection threshold fired; the
deep-market condition did not.

No immutable trigger-time snapshot was retained. CP17 analysis therefore uses
the nearest retained immutable post-trigger snapshot,
`20261007T002008.645365Z`, whose source observations extend through
2026-10-06. That bounded population recorded:

- 2,575 comparable pairs;
- 671 markets;
- 32 markets with n>=15;
- 1,558 same-sign pairs;
- 60.50% aggregate same-sign;
- CP16 aggregate same-sign: 60.43%;
- 144 additional comparable pairs relative to CP16.

The aggregate same-sign rate moved by +0.08 percentage points between the CP16
population and the retained CP17 analytical population using the underlying
fractions. The additional 144 comparable pairs contained 89 same-sign
observations (61.81%). No frozen statistical threshold has been established
for classifying this movement as a trend, stability, instability, or
predictive signal.

The CP17 analytical snapshot is 60 comparable pairs beyond the natural trigger
count and is not represented as an exact reconstruction of the October 4
trigger population.

It is not evidence that OBI, Near-Book Depth Imbalance, or their agreement
predicts future market outcomes.

Behavior remains heterogeneous across individual markets.

No CP18 collection trigger was defined by the pre-CP17 frozen authority. Any
subsequent checkpoint trigger must be explicitly established from the CP17
baseline rather than inferred retroactively from observations accumulated
while the CP17 Sentinel remained DUE.

## Forward Midpoint Study A

A separate frozen historical outcome study was first executed on 2026-11-08
against the retained immutable CP17 analytical snapshot
`20261007T002008.645365Z`.

The frozen primary regression contained 1,009 eligible observations across
225 slug clusters. Continuous full-book OBI had a coefficient of
-0.01586748820654767 with slug-clustered robust standard error
0.0045457246668535152, 95% confidence interval
[-0.024825343061202598, -0.0069096333518927425], and two-sided
p=0.00058022107633821918. The secondary descriptive same-direction rate was
418/1,009 (41.43%).

Study A therefore records a statistically nonzero negative historical
association under its prospectively frozen specification. It does not establish
prospective predictive value, profitability, production readiness, or
improvement to an LRS-1 trading decision. No post-outcome respecification or
LRS-1 integration is authorized by this result.

The complete frozen methodology, provenance boundary, numerical inference
convention, result, and interpretation limits are maintained in
`zPROGRAM_ROADMAP.md`.

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
