# Market Selection Engine
# Mission Control

**Status:** Active Research
**Last Updated:** 2026-11-07
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

Fast-changing ledger counts are intentionally not duplicated here as current
control state.

The authoritative paper-trade ledger remains:

`data/simulator/paper_trades.csv`

Population counts, win rates, P&L, and category composition should be computed
from the current ledger or from a frozen research artifact with explicit
provenance. Historical snapshots remain research evidence but must not be
mistaken for current runtime state.

Paper-research observations do not establish live profitability, predictive
validity, or expected future returns.

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

## Current Research State — D1-003 V1 Complete / Post-V1 Exploratory

The frozen n=396 discovery population and D0 descriptive work remain preserved
historical research evidence.

D1 discovery subsequently evaluated the prospectively registered candidate
questions under the frozen discovery protocol. D1-003, the entry-price
candidate, ranked first for protected validation.

The protected D1-003 V1 validation was executed against the frozen 80-trade V1
population under its precommitted specification. The joint directional
replication classification was **PASS**:

- entry price versus `trade_won`: positive Spearman relationship;
- entry price versus `trade_pnl`: negative Spearman relationship;
- the frozen family-equal sensitivity gate retained the required directions.

That PASS establishes only replication of the frozen directional hypothesis in
V1. It does not establish causality, a universal entry-price rule, live-money
profitability, or authorization to change scoring, admission, sizing, or
trading behavior.

After V1, CP-V2 governance and validation methodology were frozen for a
prospective 100-eligible-trade replication. A fail-closed readiness sentinel
was added to monitor that threshold without reading outcome or predictor
fields.

The sentinel first recorded READY on 2026-10-26 with 107 eligible closed
post-V1 trades. The notification runtime recorded a successful outbound READY
alert and created its one-shot notification latch, but the human operator did
not observe the checkpoint. No effective subsequent READY escalation occurred.

The missed checkpoint was discovered manually on 2026-11-06 with 238 eligible
closed post-V1 trades. The operator then explicitly authorized opening all 238
post-V1 outcomes for exploratory analysis.

Therefore:

- CP-V2 outcome blindness has ended.
- The original prospective 100-trade CP-V2 validation must not be represented
  as an untouched outcome-blind validation using this already-opened cohort.
- The 238-trade post-V1 work is exploratory.
- No CP-V3 or replacement confirmatory experiment is automatically authorized.
- No scoring, admission, category, entry-price, sizing, or live-trading change
  is authorized from the exploratory results.

At the raw-trade level, the 238 post-V1 observations contained 193 wins and 45
losses, an 81.09% win rate, and aggregate paper P&L of -$319.22.

Exploratory decomposition found material dependence and concentration.
Political observations accounted for 80 trades and -$896.53 raw paper P&L,
while the 158 non-Political observations accounted for +$577.31. However,
multiple Political contracts represented related election/event exposures, and
the frozen family detector v1.1 visibly under-clustered some of that economic
dependence.

A resolution-day sensitivity also materially changed the weighting of results:
the 238 observations resolved across 34 days, with 19 positive-P&L days and 15
negative-P&L days. Equal-weight daily mean P&L was -$0.75 and median daily mean
P&L was +$5.38. This sensitivity does not define an event family and is not a
confirmatory test.

The current research conclusion is therefore deliberately limited:

**post-V1 deterioration is real at the recorded-trade accounting level, but
the observations are materially dependent and do not justify a simple
Political-category exclusion, an entry-price threshold, or another methodology
change.**

Further outcome slicing should not be used to manufacture a favorable rule.
Any new confirmatory hypothesis must be defined prospectively with a new
protected population and explicit governance.

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
