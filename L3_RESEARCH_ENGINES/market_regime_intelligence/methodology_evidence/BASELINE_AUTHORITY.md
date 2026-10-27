# LRS4 Experiment v2 — Proposed Evidence Baseline Authority

Status: PROPOSED / NOT ACCEPTED / NOT FROZEN.
Implementation: UNAUTHORIZED.
Research-outcome inspection: N=0.

## 1. Scope and authority

This document identifies the proposed selected test and invariant
evidence supporting `LRS4_Experiment_v2_Pre-Inference_Methodology.md`.

The v2 methodology remains authoritative for technical definitions,
evaluation order, inherited interfaces, and supersession rules.
This document does not independently define or modify methodology.

## 2. Evidence preservation checkpoint

Verified evidence-preservation commit:

`ba3e25c8aad9beced3a5103b046ad59e58c0d938`

This commit preserves the original and proposed evidence artifacts.
The commit is a provenance anchor, not a methodology-freeze marker.

## 3. Proposed selected test baseline

- Family A: `Family_A_Corrected_Proposed.md` — 145 tests.
- Family B: `Family_B_Original_Selected.md` — 51 tests.
- Total: 196 tests.

Historical Family A evidence remains preserved in
`Family_A_Original_Selected.md`.

The corrected Family A differs from the selected original only at:
- A43 / I48: D4 cannot mutate upstream D2 or D3.
- A92 / I49: SH_path follows finalized Instrument Path.
- A136 / I52: exactly one authoritative D3 producer, including
  duplicate emissions with identical values.

Supporting correction and reconciliation records:
- `POST_AUDIT_TEST_CORRECTIONS_PROPOSED.md`
- `TEST_RECONCILIATION_OVERLAY_PROPOSED.md`
- `SOURCE_LEDGER.json`

## 4. Proposed selected invariant baseline

- `INVARIANT_REGISTRY_RECONCILED_PROPOSED.md` — 53 entries.

Supporting historical and reconciliation records:
- `INVARIANT_REGISTRY_SOURCE_EXTRACT.md`
- `INVARIANT_SOURCE_LEDGER.json`
- `INVARIANT_RECONCILIATION_LEDGER.json`

The reconciled registry is the proposed selected inventory.
Its presence in Git does not constitute formal acceptance.

## 5. Historical reconciliation and supersession tracking

`OPEN_RECONCILIATION_ITEMS.md` preserves historical reconciliation
questions and corrections, including I47, I49, I14, I37,
A43, A92, A136, A57, A128–A130, and proposed B52–B60.

That historical list must not be silently interpreted as either
proof that every item remains unresolved or proof that every item
has been closed. Formal acceptance requires reconciliation against
the selected registry, correction records, and provenance ledgers.

Proposed B52–B60 are excluded from the 196-test selected inventory.

## 6. Inherited source boundary

The frozen LRS3 source and inherited Experiment-v1 rules remain
subject to their independently verified provenance and explicit
Experiment-v2 supersession boundaries. This evidence selection
does not modify LRS3, Experiment v1, or inherited interfaces.

## 7. Acceptance boundary

No methodology acceptance or freeze is declared here.
No implementation is authorized.
No research outcomes have been inspected.

Formal acceptance requires a separate explicit decision following
review of the selected evidence, provenance, and reconciliation state.
