# LRS4 — Formal Evidence Baseline Acceptance Record

**Status:** FORMALLY ACCEPTED EVIDENCE BASELINE
**Scope:** Experiment-v2 proposed test and invariant evidence
**Authority:** User-authorized evidence-governance decision
**Methodology status:** DRAFT / NOT FROZEN
**Implementation:** UNAUTHORIZED
**Outcome inspection:** N=0

## 1. Acceptance Decision

The selected LRS4 Experiment-v2 evidence baseline is formally
accepted for methodology-governance and future conformance review.

This acceptance does not independently establish that every test
has been executed or that any implementation has passed.

## 2. Accepted Inventory

- Family A: 145 corrected selected tests.
- Family B: 51 original selected tests.
- Total: 196 selected tests.
- Reconciled invariant registry: 53 invariants.

The selected baseline consists of:

- `Family_A_Corrected_Proposed.md`
- `Family_B_Original_Selected.md`
- `INVARIANT_REGISTRY_RECONCILED_PROPOSED.md`

The filenames retain their historical PROPOSED labels.
This acceptance record governs their current evidence-acceptance
status without rewriting the preserved source artifacts.

## 3. Provenance

- Evidence preservation commit:
  `ba3e25c8aad9beced3a5103b046ad59e58c0d938`
- Baseline authority integration commit:
  `706db43a4dc23f0e4ff33911c13901dfb927c495`

Original selected evidence, source ledgers, reconciliation ledgers,
and correction overlays remain preserved for auditability.

## 4. Reconciliation Acceptance

The following dispositions are accepted:

- I14: D3 endpoint totality remains distinct from I52 producer uniqueness.
- I37: ADJUDICATED_CORRECTION; original provenance preserved.
- I47: RECONSTRUCTED_PROPOSED_NOT_ORIGINAL; not represented as original wording.
- I49: ADJUDICATED_REPLACEMENT; not represented as original wording.
- A43: corrected to cover I48 D4 upstream immutability.
- A92: corrected to cover I49 finalized-path timing.
- A136: corrected to exercise I52 D3 producer uniqueness.
- A57: episode-count identity remains derived, not independently normative.
- A128–A130: I50 naming discipline is static interface/schema
  compliance, not automatically a runtime integrity result.
- B52–B60: proposed additions excluded from the 196-test inventory.
- Fresh independent cross-check: excluded from the accepted inventory.

The historical reconciliation list remains preserved.
The accompanying disposition appendix records the current status.

## 5. Authority and Governance Boundaries

Acceptance establishes a reviewed evidence baseline; it does not
supersede the technical methodology in Experiment-v2 or inherited
Experiment-v1 provisions.

This decision does not:

- Freeze Experiment-v2 methodology.
- Authorize implementation or code changes.
- Authorize outcome inspection or inference.
- Alter frozen Experiment-v1 or LRS3 source artifacts.
- Add B52–B60 to the selected test corpus.
- Convert historical source provenance into original wording.
- Declare runtime conformance or test execution success.

Any later methodology freeze, implementation authorization, or
outcome-inspection authorization requires a separate explicit decision.

## 6. Review and Commit Status

User authorization: RECEIVED.
Gemini second opinion: ACCEPTANCE READY; zero blockers.
Documentation commit: PENDING.
