# Market Selection Engine
# Mission Control

**Status:** Active Research
**Last Updated:** 2026-09-18
**Engine:** `L3_RESEARCH_ENGINES/market_selection/`

---

## Purpose

The Market Selection Engine studies whether observable market characteristics
provide useful evidence for selecting prediction markets for further research.

It is a research engine, not the Prediction Markets Domain producer and not a
live-trading system.

Prediction-market acquisition, selection/publication infrastructure, and the
canonical downstream data product are owned by:

`L2_DOMAINS/prediction_markets/`

Platform architecture and portfolio priorities are owned by:

- `L0_PLATFORM/zARCHITECTURE.md`
- `L0_PLATFORM/zROADMAP.md`

Shared findings and open research questions are owned by:

- `L4_KNOWLEDGE/validated_findings.md`
- `L4_KNOWLEDGE/open_questions.md`

Historical Market Selection build history remains in:

`L3_RESEARCH_ENGINES/market_selection/zHISTORY.md`

---

## Current Research State

The engine is in active evidence collection and analysis.

The historical milestone of 100 resolved paper trades has already been passed.
It is not the current research blocker.

The current research sequence is:

1. Preserve the existing paper-trade methodology and admission invariant.
2. Continue accumulating and resolving observations.
3. Treat the completed n=396 Audit E review as the current diagnostic checkpoint.
4. Continue evaluating event-family dependence, effective independent sample
   size, entry-price effects, and market composition without changing methodology
   solely to improve the observed result.
5. Define any subsequent checkpoint prospectively from a research-relevant trigger.

Classifier or taxonomy redesign is **not** currently supported by the Audit E
evidence and is not the standing immediate blocker.

No classifier, scoring, sampling, or trade-admission change is authorized by
this document.

---

## Repository Ledger Snapshot

The following is a snapshot of the checked-in repository ledger, not a claim
about production activity after the ledger's latest recorded timestamp.

**Ledger:** `data/simulator/paper_trades.csv`
**Latest recorded entry:** 2026-08-12 20:29
**Latest recorded resolution:** 2026-08-12 20:30

### Population

- Total paper trades: **269**
- Closed: **138**
- Open: **131**
- Wins: **119**
- Losses: **19**
- Closed win rate: **86.23%**
- Aggregate recorded paper P&L: **+$644.86**

These are paper-research observations. They do not establish live
profitability, predictive validity, or expected future returns.

### Closed Performance by Recorded Category

| Category | Closed | Wins | Losses | Win Rate | Paper P&L |
| --- | ---: | ---: | ---: | ---: | ---: |
| Crypto Long-Duration | 12 | 12 | 0 | 100.00% | +$393.95 |
| Entertainment | 1 | 1 | 0 | 100.00% | +$48.15 |
| Geopolitical | 48 | 41 | 7 | 85.42% | +$194.66 |
| Macro/Economic | 5 | 5 | 0 | 100.00% | +$79.93 |
| Other/Unknown | 54 | 47 | 7 | 87.04% | -$24.46 |
| Political | 1 | 1 | 0 | 100.00% | +$2.09 |
| Sports | 17 | 12 | 5 | 70.59% | -$49.46 |

Small category samples must not be treated as validated category effects.

The `Other/Unknown` population is particularly important because its high
observed win rate coexists with negative aggregate recorded paper P&L. That
makes population composition and economics a research question rather than a
reason to assume classifier redesign is the solution.

---

## Paper-Trade Identity Invariant

Current admission identity is:

**one `market_id` may create at most one Market Selection paper trade, ever.**

Supporting rules:

- `market_id` is the admission identity.
- `slug` is metadata only.
- `scanner_run_id` is provenance only.
- A previously traded `market_id` is not eligible for re-entry merely because
  its prior paper trade is closed.
- Historical duplicate rows are preserved rather than rewritten.

The checked-in ledger currently contains:

- 256 unique `market_id` values across 269 rows.
- 12 historical duplicated `market_id` groups.
- 13 historical excess rows.

These historical duplicates predate the current invariant enforcement and are
retained as research provenance.

Do not retroactively delete, merge, or rewrite them merely to make the ledger
conform visually to the current rule.

---

## Research Boundaries

### Frozen / Protected Unless Separately Authorized

Repository cleanup does **not** authorize changes to:

- Tradeability scoring.
- Scanner thresholds.
- Sampling methodology.
- Market-selection criteria.
- Category taxonomy.
- Classifier behavior.
- Paper-trade admission identity.
- Existing historical paper trades.
- Prediction Markets canonical publication contract.
- Research methodology merely because a document is stale.

Documentation should describe implemented behavior; it must not silently
change that behavior.

### Historical Evidence

Historical classifier patches, corrected category records, milestone
checkpoints, prior hypotheses, and superseded blockers remain legitimate
research history.

They should be preserved in historical or knowledge-layer authorities rather
than carried indefinitely as current Mission Control state.

---

## Core Research Question

Whether Tradeability Score and related market-selection characteristics exhibit
a stable relationship with useful paper-research economics remains unresolved.

Historical checkpoints at n=32, n=36, and n=117 are preserved in
`L4_KNOWLEDGE/validated_findings.md`. Those observations do not establish that
Tradeability Score is predictive, inverted, harmful, or causally related to
paper-trade outcomes.

## Current Research State — Audit E Completed

Audit E's decomposition-first review was completed at the overdue
250-closed-trade checkpoint, performed at n=396 closed trades on 2026-09-23.

The review established that `Other/Unknown` is heterogeneous and contains
substantial latent event-family concentration. Removing `Other/Unknown` did
not restore the earlier n=117 lower-score economic pattern, and entry-price
stratification plus recorded-category diagnostics did not reveal a stable,
uniform Tradeability Score relationship.

The evidence does not currently support changing the taxonomy or classifier
solely to improve this research result.

The primary research question remains unresolved. Event-family dependence,
effective independent sample size, entry-price effects, and market composition
remain material interpretation issues. No new raw closed-trade milestone is
currently defined; any subsequent checkpoint should be prospectively defined
from a research-relevant trigger.

Detailed checkpoint measurements and limitations are preserved in
`L4_KNOWLEDGE/validated_findings.md`.
---

## Secondary Research Questions

Continue evaluating, with appropriate sample-size caution:

- Whether Tradeability Score buckets exhibit stable differences.
- Whether category-level behavior persists as samples grow.
- Whether entry-price characteristics explain differences in paper outcomes.
- Whether spread, liquidity, or other recorded market features provide useful
  explanatory information, while accounting for historical dependence created
  by pre-invariant repeated `market_id` observations.
- Whether apparent effects survive additional observations rather than
  reflecting small samples or historical composition.

These are research questions, not validated claims.

---

## Operational Authority

The normal daily workflow is automated through the shared L1 orchestrator.

Engine-specific operating instructions and manual recovery procedures are
maintained in:

`L3_RESEARCH_ENGINES/market_selection/zDAILY_OPERATIONS.md`

Manual execution is a fallback/recovery workflow, not the default description
of normal production operation.

---

## Documentation Authority

Use the following hierarchy when documents disagree:

1. Frozen experiment or methodology authority for experiment-specific rules.
2. Current implementation and validated runtime evidence for actual behavior.
3. `L0_PLATFORM/zARCHITECTURE.md` for architecture and ownership.
4. This Mission Control document for current Market Selection research state.
5. `zDAILY_OPERATIONS.md` for engine operations and recovery.
6. `L4_KNOWLEDGE/validated_findings.md` for shared validated findings.
7. `L4_KNOWLEDGE/open_questions.md` for shared unresolved research questions.
8. `zHISTORY.md` and Git history for historical state.

Historical documents may correctly describe an earlier architecture or
research state and should not be rewritten merely to make old evidence look
current.

---

## Promotion and Change Control

Before changing methodology or promoting a new conclusion:

- Identify the exact research question.
- Verify the relevant dataset and provenance.
- Separate observation from interpretation.
- Preserve frozen experiments.
- Define what evidence would support or reject the proposed change.
- Review effects on historical comparability.
- Obtain explicit authorization before implementation where methodology is
  affected.

Repository cleanup alone is never sufficient authorization.

---

## Mission Control Maintenance

Update this document when:

- The primary Market Selection research question materially changes.
- A methodology decision changes the engine's authorized direction.
- A major research phase begins or closes.
- The owning architecture or operating model changes.
- A new repository-ledger checkpoint is deliberately promoted into Mission
  Control.

Do not update it for every scanner run, new paper trade, resolution, or minor
diagnostic.

Fast-changing measurements belong in the underlying research data and analysis,
not in manually duplicated control-document counters.
