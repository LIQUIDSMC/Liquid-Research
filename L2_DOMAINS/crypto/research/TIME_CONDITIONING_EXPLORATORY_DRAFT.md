# Time-Conditioning Exploratory Diagnostic — Proposed Predeclaration

Status: DRAFT / UNFROZEN / NO EXECUTION AUTHORIZATION
Prepared: 2026-10-25
Source review baseline: b7f2a6aaef6dd33b4609411ec4cc8dc168bf87b2

## Relationship to Existing Research

This proposes a new exploratory study. It does not replace, complete,
rerun, or reconstruct historical Candidate D D0. The original 25-date /
50-instrument-day matrix and predeclaration digest remain unchanged.
The original predeclaration and execution evidence have not been located
in the previously searched records. No historical D0 conclusion is assumed.

Existing gross-edge v1 and ETH replication v2 research remain closed.
Cost-stress/economic-feasibility work remains paused.

## Question and Interpretation

Does the trade-flow imbalance gross-return contrast differ around hour
boundaries or during New York session hours within this historical
development sample?

These are previously studied dates, not an independent holdout.
This is exploratory candidate selection, not independent confirmation,
a strategy test, or evidence of executable profitability.

## Proposed Research Population

Instruments: BTC-USD and ETH-USD.

Research dates, inclusive:
- 2026-07-22 through 2026-07-31.
- 2026-08-01 through 2026-08-09.
- 2026-08-26 through 2026-08-30.

Total: 24 dates / 48 instrument-days.

September 3 is excluded prospectively from this new proposal because
its required next-day source partition is sealed. This does not amend
the original D0 matrix.

Each research day requires previous, target, and next receipt-date
partitions. The union of required source partitions is:
- trades/date=2026-07-21 through trades/date=2026-08-10 inclusive.
- trades/date=2026-08-25 through trades/date=2026-08-31 inclusive.

Total: 28 distinct trade partitions. Depth data is not required.
Required source dates must all precede 2026-09-04. Validate the complete
required partition-date set before filesystem access.

Missing partitions or resource exhaustion abort execution. Dates are
not silently omitted, substituted, or imputed. Presence of these
partitions alone does not prove completeness of the underlying feed.

## Proposed Computation

Preserve canonical files unchanged. Select each instrument's research-day
rows using the half-open UTC trade-time interval, then sort derived arrays
by ascending (trade_time, trade_id).

Retain the existing 10-second lookback and sampling of every twentieth
trade. Compute the complete instrument-day before temporal subdivision.
For each horizon, construct the whole horizon-eligible population using
the existing common-eligibility and defined-return masks, then assign
imbalance deciles across that population before applying time groups.

Primary horizon: 60 seconds.
Secondary descriptive horizons: 5, 15, and 30 seconds.

The existing outcome calculation uses the latest available trade in
(T, T+h]; it does not require a trade exactly at the horizon or prove
continuous coverage through that horizon. Report this limitation.

The existing analytical loader converts canonical decimal price and
quantity to float64. Canonical bytes remain unchanged; derived floating
point calculations do not retain exact decimal arithmetic.

## Time Groups

Hour mechanism:
- IN: minute 45–59 or minute 0–14 of each hour.
- CONTROL: minute 15–44.
- Use the existing epoch-millisecond minute-of-hour rule.

Session mechanism:
- IN: 09:30 inclusive to 16:00 exclusive, America/New_York.
- CONTROL: all other times.
- Use timezone-aware conversion.
- Apply on every included date, including weekends. This clock grouping
  does not establish an exchange trading session.

## Measurements

For every instrument-day, horizon, and mechanism:
- Report eligible observation counts.
- Report D0 and D9 counts separately within IN and CONTROL.
- Calculate each group's edge as
  10,000 * (mean D9 return - mean D0 return).
- Calculate delta as IN edge minus CONTROL edge.

A mechanism/horizon cell is structurally invalid if either group lacks
D0 or D9 observations, or if required calculations are nonfinite.
Report invalid cells explicitly; do not silently drop them.

At 60 seconds, report every instrument-day delta and per-instrument
summaries. A date-paired delta is the arithmetic mean of its BTC and ETH
deltas, only when both are valid. Report the number and identities of
valid and invalid date pairs, summaries of valid paired deltas, strictly
positive paired-delta counts, and leave-one-date-out mean sensitivity.
If fewer than two valid date pairs exist, sensitivity is unavailable.

These paired summaries are descriptive. Do not treat 48 instrument-days
as independent observations or assume calendar dates are independent.
No p-values, confidence levels, or significance claims are specified.

Secondary horizons cannot rescue a primary finding. The two mechanisms
must be reported side by side without selecting a winner automatically.

## Completion and Follow-Up Rules

No automatic scientific PASS or promotion threshold is assigned.
The original D0 33/50 gate is neither reused nor rescaled.

Permitted completion classifications:
- COMPLETE_DESCRIPTIVE: all 48 instrument-days were processed, with every
  invalid cell and date pair explicitly disclosed.
- INCOMPLETE: a source, integrity, resource, or execution requirement failed.

COMPLETE_DESCRIPTIVE does not mean all cells were valid, that the data is
scientifically complete, or that an edge exists. No automatic follow-up
decision is authorized. Any confirmation study, selection rule, hypothesis,
or economic-feasibility work requires a separate prospective design.

## Capacity and Acquisition Plan — Unresolved

Completed source-count and synthetic Pi5 profiling observations are recorded
in [TIME_CONDITIONING_CAPACITY_CHECKPOINT.md](TIME_CONDITIONING_CAPACITY_CHECKPOINT.md).
They do not freeze execution budgets, authorize acquisition, or establish
full-pipeline memory safety. This predeclaration remains DRAFT / UNFROZEN.


The one-file pilot cannot establish full-corpus file counts, byte volumes,
row counts, peak memory, or runtime requirements.

Any proposed inventory must cover the union of all 28 required source
partitions, counting each partition once. It requires a separately approved
file-count and runtime bound and must stop without treating a partial
inventory as complete.

Filesystem metadata can establish observed file sizes and counts.
Parquet footer inspection requires file reads and reports stored row
counts, not exact instrument/research-day populations. Exact counts
require reading instrument_id and trade_time under a separately bounded
read allowance.

Before any source inventory, transfer, or analytical execution, define
and approve numeric limits for:
- Maximum files and logical source bytes.
- Maximum inventory and execution runtime.
- Maximum Pi5 process memory and termination behavior.
- Minimum destination free-space reserve.
- Input and output storage allowances, including incomplete artifacts.

Physical I/O can exceed logical source bytes because verification,
counting, loading, and hashing may reread files. Account for repeated
partition scans and sorting/kernel memory separately. Capacity checks
must not instantiate analytical kernels or inspect outcomes.

## Prerequisites Before Freezing or Execution

1. Approve the question, population, descriptive policy, and outcome semantics.
2. Approve bounded capacity discovery and any subsequent acquisition separately.
3. Resolve and freeze numeric resource limits from capacity evidence.
4. Identify exact inputs, expected digests, code revision, dependencies,
   output locations, and retention arrangements.
5. Implement and independently audit synthetic tests for the new study,
   including sealed source-date checks and date-paired summaries.
6. Retain the final predeclaration and its digest outside temporary storage
   before new outcome computation; preserve this draft's review history.
7. Obtain explicit execution authorization for the exact frozen scope.

This draft does not change the blocked historical analyzer or authorize
development, production-data enumeration, transfer, or execution.

## Standing Governance

Production transfer: HOLD.
Broader pilot: HOLD.
H2 reserve: SEALED, 2026-09-04 through 2026-10-01 inclusive.
Scientific readiness: PENDING.
Original Candidate D D0: BLOCKED.
This proposed study: DRAFT / UNFROZEN.
