# LRS-1 D1-003 — CP-V2 Governance

## Status

- Governance stage: PRE-IMPLEMENTATION
- CP-V2 population frozen: NO
- CP-V2 outcomes accessed: NO
- CP-V2 statistical methodology frozen: NO
- CP-V2 sentinel implemented: NO
- CP-V2 execution authorized: NO

This document governs the prospective post-V1 checkpoint for the D1-003
entry-price divergence.

It defines checkpoint identity, eligibility, readiness, manifest-freeze
behavior, sentinel boundaries, integrity requirements, and the permitted
research lifecycle after CP-V2.

It does not define or modify LRS-1 production scoring, scanner behavior,
market admission, position sizing, or live-trading rules.

---

## 1. Purpose

CP-V2 is a prospective post-V1 replication checkpoint for the independently
validated D1-003 entry-price divergence.

Protected V1 passed its prospectively frozen directional replication
criterion. That result remains bounded evidence of replication under the
frozen V1 specification.

Creating CP-V2 does not upgrade the V1 result to evidence of causality,
universal generalization, live-money profitability, or a production trading
rule.

---

## 2. Frozen upstream identity authorities

CP-V2 must reuse the already-frozen Discovery-D and V1 identity authorities.

Discovery-D and protected V1 are immutable exclusion sets for CP-V2.

CP-V2 membership must not be defined by reconstructing a future date cutoff,
by taking a growing complement and assuming its size, or by relying on the
current total number of closed trades.

The exact D and V1 identity authorities and their existing integrity checks
remain upstream dependencies of CP-V2.

If either frozen upstream identity authority cannot be verified, CP-V2
processing must fail closed.

---

## 3. CP-V2 eligibility

A ledger trade is CP-V2-eligible only when all of the following are true:

1. its normalized `status` is exactly `closed`;
2. its `trade_id` is not a member of frozen Discovery-D;
3. its `trade_id` is not a member of frozen V1.

Eligibility is identity-based.

No future calendar date or date cutoff defines CP-V2 membership.

Later ledger growth may increase the eligible population but may not alter
the identities belonging to frozen D or frozen V1.

---

## 4. Readiness trigger

The CP-V2 readiness threshold is exactly:

**100 eligible closed trades.**

CP-V2 becomes READY when the deterministic eligibility procedure observes at
least 100 eligible closed identities.

The number 100 is a prospective governance boundary. It is not claimed to be
a uniquely optimal statistical sample size.

Once the eligible count has reached 100 under this frozen governance, the
CP-V2 threshold may not be increased, decreased, postponed, or otherwise
changed in response to the available population or a desire to wait for more
data.

Any prospective amendment to the readiness threshold would require a new
governance amendment made and audited before the then-current eligible count
reaches the existing threshold. No retrospective threshold movement is
permitted after readiness.

---

## 5. Pre-readiness sentinel behavior

Before READY, the sentinel may determine only:

- whether required identity/integrity authorities verify;
- the current number of CP-V2-eligible closed identities;
- progress toward the frozen 100-trade readiness threshold;
- whether CP-V2 is READY.

Permitted progress output may include forms such as:

`CP-V2 progress: 37/100`

or:

`CP-V2 READY`

Before READY, the sentinel must not create or persist the final CP-V2
100-trade manifest.

Readiness does not authorize outcome analysis.

---

## 6. Mandatory column-restricted ledger access

Sentinel ledger reads must be physically column-restricted at read time.

The implementation must use a `usecols`-equivalent mechanism and may load
only the minimum ledger fields required for eligibility and ordering:

- `trade_id`
- `status`
- `resolution_date`

The sentinel must not load the full ledger row and discard prohibited fields
afterward.

In particular, the sentinel must not read:

- `trade_won`
- `trade_pnl`

The sentinel must also not incidentally read `entry_price`, `side`,
`category`, `market_id`, `entry_date`, tradeability features, or other
non-required ledger fields merely for implementation convenience.

Frozen D/V1 identity authority may be loaded from its canonical authority
mechanism as required for exclusion and integrity verification.

---

## 7. Sentinel outcome-blind safe zone

The sentinel must not calculate, derive, display, persist, or inspect:

- win rates;
- realized P&L statistics;
- Pearson correlations;
- Spearman correlations;
- significance tests;
- entry-price outcome relationships;
- quartile outcomes;
- family-adjusted outcomes;
- temporal outcomes;
- recorded-side outcomes;
- category outcomes;
- outlier P&L statistics;
- or any other economic-outcome statistic.

The sentinel exists only to establish identity integrity and checkpoint
readiness.

A future refactor that expands sentinel access beyond this safe zone requires
prospective review before deployment.

---

## 8. Eligible-count monotonicity

The system does not assume without evidence that eligible-count decreases are
structurally impossible.

Once the sentinel has persisted a previously verified eligible count, every
subsequent successful sentinel observation must satisfy:

**current eligible count >= previously verified eligible count**

A decrease is an integrity failure.

Examples include, but are not limited to:

- a previously closed trade reverting to open;
- deletion of a previously eligible ledger row;
- identity mutation;
- upstream data corruption;
- unexpected ledger reconstruction.

On a detected decrease, the sentinel must fail closed and must not silently
replace the prior progress state.

The failure requires investigation before CP-V2 readiness or manifest freeze
may proceed.

---

## 9. Deterministic manifest freeze

The final CP-V2 population is not defined as "whatever eligible rows exist
when someone happens to run the freeze."

At the first authorized manifest-freeze operation after READY, all currently
eligible identities are deterministically ordered by:

1. parsed `resolution_date` ascending;
2. numeric `trade_id` ascending as the deterministic tie-break.

The first exactly 100 identities in that ordering become the immutable CP-V2
manifest.

`trade_id` is used as a numeric tie-break, not a lexicographic string-order
tie-break.

The observed ledger structure establishes that `trade_id` is unique, so
identical `resolution_date` values remain deterministically orderable.

---

## 10. Delayed freeze is permitted

The manifest-freeze operation does not need to occur atomically at the instant
the 100th eligible trade closes.

If CP-V2 becomes READY and additional eligible trades close before an
authorized freeze is performed, that delay does not change the frozen
100-trade checkpoint definition.

For example, if 140 eligible trades exist when freeze is authorized, the
manifest remains the first exactly 100 trades under the frozen ordering rule.

Trades ranked 101 and later are outside the CP-V2 manifest.

Therefore a delayed freeze is expected and valid behavior, not a reason to
move the threshold or redefine the population.

---

## 11. Manifest identity seal

At authorized freeze, the exact 100 CP-V2 `trade_id` values must be persisted
as an immutable manifest.

The freeze implementation must define and use one canonical serialization
rule for those identities and record its SHA-256.

The frozen manifest must verify:

- exactly 100 identities;
- no duplicate `trade_id`;
- zero overlap with frozen Discovery-D;
- zero overlap with frozen V1;
- valid closed status for every selected identity;
- valid parseable `resolution_date` for every selected identity;
- deterministic ordering under the frozen ordering rule;
- exact manifest SHA-256.

Subsequent ledger growth must not alter CP-V2 membership.

---

## 12. Fail-closed conditions

CP-V2 eligibility, readiness, or manifest freeze must fail closed on at least:

- missing required ledger columns;
- duplicate ledger `trade_id`;
- missing required identity values;
- missing or unparseable `resolution_date` for an otherwise eligible closed
  trade;
- inability to verify frozen D identity authority;
- inability to verify frozen V1 identity authority;
- D/V1 identity overlap;
- CP-V2 overlap with D or V1;
- frozen identity-hash mismatch;
- eligible-count decrease relative to persisted prior verified state;
- inability to reproduce deterministic ordering;
- frozen CP-V2 manifest count other than exactly 100;
- frozen CP-V2 manifest SHA mismatch.

No affected row may be silently deleted, substituted, or reordered to make a
check pass.

---

## 13. Exposure classification

CP-V2 inherits the already-developed D1-003 hypothesis.

Therefore CP-V2 is:

**not hypothesis-naive.**

The existence, direction, and research importance of the D1-003 entry-price
divergence were known before CP-V2.

This is distinct from outcome exposure for the future CP-V2 population.

Trades whose outcomes were unavailable to the prior D/V1 analyses may form a
prospectively untouched outcome population, but the eventual CP-V2 record
must distinguish:

- hypothesis exposure; from
- trade-outcome exposure.

CP-V2 must not be described as globally outcome-naive unless independent
evidence establishes that stronger claim.

---

## 14. Statistical methodology is separately frozen

This governance document does not authorize CP-V2 economic analysis.

Before any CP-V2 economic outcome access, a separate CP-V2 validation
specification must be prospectively frozen and audited.

That specification must define at minimum:

- predictor;
- outcomes;
- statistical tests;
- expected directions;
- classification precedence;
- significance handling, if used;
- missingness handling;
- family/dependence sensitivity;
- temporal disclosure;
- side disclosure;
- quartile disclosure;
- outlier disclosure;
- software/version authority;
- execution authorization;
- interpretation boundaries.

No CP-V2 economic outcome may be inspected to choose or modify those rules.

---

## 15. One-shot integrity

Once the CP-V2 100-ID manifest is frozen, it is immutable.

Once CP-V2 economic outcomes are opened under an authorized validation
execution:

- CP-V2 may not be rerun on a resized population;
- identities may not be substituted;
- the threshold may not be moved;
- the ordering rule may not be changed;
- classification rules may not be changed because of the observed result.

Any execution failure must be handled under explicit fail-closed governance
without silently creating a replacement population.

---

## 16. PASS / INCONCLUSIVE / FAIL and future checkpoints

A CP-V2 result does not automatically authorize CP-V3.

### PASS

PASS establishes only another prospective replication under the separately
frozen CP-V2 validation criterion.

PASS does not itself create CP-V3 and does not establish a production trading
rule.

Any CP-V3 requires a separate prospective research rationale and governance
decision.

### INCONCLUSIVE

INCONCLUSIVE is permanently recorded.

It does not permit:

- changing CP-V2 criteria;
- resizing CP-V2;
- rerunning the same CP-V2 population;
- substituting identities;
- automatically creating CP-V3.

Any later checkpoint requires a separately justified and prospectively frozen
governance decision.

### FAIL

FAIL is permanently recorded.

CP-V2 may not be rerun, replaced, resized, or redefined because of the
failure.

CP-V3 is not automatically authorized.

Any further replication requires an explicit new research rationale and
prospective governance decision that acknowledges the CP-V2 failure.

There is no automatic V2 -> V3 -> V4 replication ladder.

---

## 17. Interpretation boundary

CP-V2 is research infrastructure.

Neither CP-V2 readiness, manifest freeze, nor a future CP-V2 result by itself
authorizes changes to:

- Tradeability Score;
- scanner ranking;
- market admission;
- position sizing;
- execution behavior;
- live-money trading.

Protected V1 remains a PASS under its frozen criterion.

The current evidence does not establish causality, universal generalization,
live-money profitability, or a production trading rule.

---

## 18. Implementation sequence

The required sequence is:

1. freeze and audit this CP-V2 governance;
2. commit the exact audited governance bytes;
3. separately freeze the CP-V2 validation methodology before outcome access;
4. design sentinel implementation from this governance;
5. externally audit sentinel code before deployment;
6. commit and deploy audited sentinel code;
7. test fail-closed behavior without economic outcome access;
8. schedule the sentinel on Pi3;
9. verify automatic operation and persisted monotonic progress state;
10. wait for READY without inspecting CP-V2 economic outcomes;
11. perform separately authorized deterministic manifest freeze;
12. execute CP-V2 validation only under its separately frozen methodology and
    authorization.

No implementation step may weaken the identity, outcome-blindness, or
one-shot requirements above.
