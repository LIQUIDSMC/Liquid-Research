# Research Evidence Preservation — Draft Specification

Status: DRAFT / INCREMENTS 1 AND 2 IMPLEMENTED — SYNTHETIC ONLY / FURTHER IMPLEMENTATION NOT AUTHORIZED
Initial consumer: LRS3 research workflows
Proposed owner: L1 Market Data Platform
Draft date: 2026-10-15

## Implementation Checkpoint — Increment 1

Chris explicitly authorized the bounded synthetic-only Increment 1 after
independent proposal review. The read-only verifier and tests were
independently audited, committed, and pushed at `23c2066`:
- `evidence_preservation.py`
- `test_evidence_preservation.py`

Validation at that checkpoint: 83 verifier tests and 280 existing Candidate C
snapshot regressions passed. The verifier returns only
`INCREMENT_1_INTEGRITY_VERIFIED`; it writes no evidence or status files.

Paths are limited to 128 components, including metadata-declared paths.
This bounds ancestor-prefix validation; it is not a linear-time claim.

Increment 1 does not implement copying, locking, retry orchestration,
completion publication, second-copy verification, retention, deployment,
or experiment adoption. The full acceptance criteria below remain the
target for the complete preservation workflow, not a claim that Increment 1
satisfies every criterion.

## Implementation Checkpoint — Increment 2

Chris explicitly authorized the bounded synthetic-only Increment 2 after
independent design review. Its runtime-classification prerequisite was
separately audited, committed, and pushed at `585c11c`:
`RuntimeLimitExceeded` subclasses `VerificationError` and distinguishes
cooperative verifier runtime exhaustion from malformed input.

The copy implementation and tests were independently audited, committed,
and pushed at `323089c`:
- `evidence_copy.py`
- `test_evidence_copy.py`

Validation at the Increment 2 checkpoint: 50 copy tests, 92 verifier tests,
and 280 existing Candidate C snapshot regressions passed.

Increment 2 copies an already prepared synthetic bundle into a new attempt
under a cooperative local-filesystem lock, checks source stability, and
verifies the copied payload with Increment 1 and caller-supplied anchors.
One shared cooperative deadline covers the operation. Failures after
attempt creation retain incomplete attempts and partial payloads.

The final deadline check before successful control publication gates
`COPY_VERIFIED`. Once publication succeeds, a later elapsed deadline does
not downgrade that state. `COPY_VERIFIED` is copy-integrity evidence, not
preservation-complete status, scientific readiness, or cleanup eligibility.

The public API classifies validation and operational failures with
`CopyError.code`. `INVALID_INPUT` is a pre-attempt API error and is never
written as an attempt error code.

Existing attempts are never overwritten or resumed. A retry requires a
separately prepared source bundle with a new attempt ID and the same run ID.
No automatic retry, cleanup, source deletion, or second-copy verification
is implemented.

Production storage selection, retention, recurring monitoring, deployment,
and experiment adoption remain separately gated. This synthetic checkpoint
does not establish hardware crash durability or safety against
noncooperating writers, and does not claim full-spec compliance.

## Purpose and Scope

Preserve evidence identifying what was declared, executed, and concluded
in a separately authorized research run.

Candidate D motivates this design: its analyzer remains tracked, while
the referenced predeclaration and default result artifacts were not located
in the searches documented on 2026-10-14 in
`market_data/zROADMAP.md`. This does not establish whether D0 ran or
whether evidence survives elsewhere.

This specification proposes an engineering interface, not a new research
experiment. The separately authorized Increments 1 and 2 use synthetic
fixtures only. Existing frozen analyzers remain unchanged; adoption by an
existing experiment requires separate review.

This work does not recover missing evidence, authorize research, access
sealed H2 data, or establish scientific readiness.

## Existing Authority

This design does not supersede incident-specific retention, deletion,
or tooling decisions in `STORAGE_PATH_DIVERGENCE_INCIDENT.md` or
`INSTRUMENT_IDENTITY_INVESTIGATION.md`. It does not require historical
one-shot incident tools to become permanent repository source.

Source development follows the established Mac -> GitHub -> Pi workflow.
Evidence storage is separately selected; runtime evidence does not
automatically belong in Git.

## Identifiers and Evidence Bundle

Use a canonical UUID for each research run and a separate canonical UUID
for each preservation attempt. Retries retain the run ID and receive a
new attempt ID. Identifiers establish uniqueness, not authenticity.

Each attempt has an explicitly selected persistent destination outside
temporary storage. Storage locations, retention owner, retention period,
and failure-reporting arrangements must be agreed before implementation.

The implementation proposal must define resource budgets: maximum artifact
count and logical bytes per attempt, destination capacity requirements,
and a cooperative runtime limit, including the synthetic-fixture footprint.
Logical byte limits are not total physical I/O limits, and cooperative
runtime checks are not hard deadlines. Budget exhaustion leaves the attempt
incomplete and reports the failure without deleting source evidence.

Preserve:
- Exact predeclaration bytes.
- The supplied authorization decision record and its provenance.
- The prospective required/optional artifact list.
- Host identity, source revision, relevant source-file hashes,
  dependency/version information, parameters, and execution timestamps.
- Input identity references required by the experiment's existing contract.
- Result artifacts and execution logs, including failed-run evidence.
- A versioned manifest of artifact roles, relative paths, sizes, and hashes.
- A separate verification report bound to the manifest digest.

Missing required provenance prevents preservation-complete status.
A Git revision alone is insufficient when executable source has local
changes: preserve the relevant exact source bytes or another reviewed
representation sufficient to identify them.

Credentials, private keys, and notification secrets are excluded.
Large or restricted evidence requires an explicitly approved destination;
no automatic Git inclusion or publication is permitted.

## Pre-Run Requirements

Before an authorized run begins, preserve its predeclaration and
prospective artifact list. Retain their expected SHA-256 digests
independently of the bundle.

Freeze the required/optional distinction before execution. Missing required
artifacts cannot be relabeled optional after observing a failed run.

The prospective list must define required failure evidence as well as
success outputs. Results that were never produced remain explicitly absent;
do not fabricate placeholder results to make a failed run appear complete.

## Preservation and Concurrency

Copy evidence without modifying source files. Verify destination bytes
against recorded sizes and SHA-256 hashes.

Reject unsafe relative paths, symlinked roots and path components,
duplicate artifact paths, and overlapping source/destination locations.
Source evidence must be stable during preservation; detected changes abort
the attempt without publishing completion. The implementation proposal
must define how source stability is checked and its limitations.

Use one cooperative lock per preservation destination, held throughout
attempt creation, copying, verification, and publication. A competing
writer fails without modifying the existing attempt. Writers using the
same destination must use the same lock identity.

No distributed or noncooperating-writer guarantee is claimed.

Refuse to overwrite an existing attempt. Interrupted attempts remain
explicitly incomplete and available for inspection.

A retry creates a new attempt ID linked to the same run ID. Initial
implementation provides no automatic cleanup, overwrite, or resume.

## Verification and Completion

Verify manifest schema/version, required-artifact coverage, artifact
sizes and hashes, unexpected files, and independently supplied
predeclaration and artifact-list digests.

Preservation status and research-run outcome are separate fields.
Preservation-complete means all evidence required for the recorded outcome
is present and verified; it does not mean the research run succeeded.
A failed run may have complete preservation of its available failure
evidence under the prospective requirements.

The manifest declares the frozen evidence inventory. Verification reports
and completion records are separately identified control artifacts, bound
to that manifest's digest; they must not require self-referential hashes.
The implementation proposal must define their schemas and permitted paths.

A completion marker alone is insufficient. Missing required evidence or
failed verification prevents completion.

Verification establishes consistency with supplied records. It does not
authenticate authorization, prove execution timing, establish input-data
completeness, or certify scientific validity.

## Second Copy and Retention

Require a persistent primary location and an independently verified second
copy before any temporary evidence is eligible for deletion. This is a
necessary condition, not deletion authorization. No automatic source
deletion is provided.

The independently retained expected manifest digest is the comparison
anchor; neither copy's own assertions make it authoritative.

A verification failure or disagreement blocks the two-copies-verified
status and cleanup eligibility. Preserve both copies and report the
discrepancy to the designated owner. Do not automatically choose,
repair, or overwrite a winner.

The implementation proposal must specify storage failure domains and the
verification/reporting procedure. Two directories on one device must not
be described as protection against that device's failure.

Persistent storage and hashes alone do not guarantee backup availability.
Process-level fault injection does not establish hardware crash durability.

## Synthetic Acceptance Criteria

Tests must demonstrate:
1. Valid evidence verifies against independently supplied digests.
2. Missing required evidence prevents completion.
3. Changed bytes, malformed records, unsafe paths, symlinked roots/components,
   duplicate paths, and unexpected files are rejected.
4. Existing attempts cannot be overwritten.
5. Competing cooperating writers cannot mutate the same attempt.
6. Interrupted preservation cannot appear complete.
7. Retry creates a distinct attempt without modifying its predecessor.
8. Failed-run evidence remains distinct from successful-run evidence.
9. Source evidence remains unchanged; detected source changes abort.
10. Second-copy disagreement blocks verified-copy status and cleanup
    eligibility, preserves both copies, and produces an explicit report.
11. Budget exhaustion leaves the attempt explicitly incomplete, reports
    the failure, and does not delete source evidence.

## Release and Adoption Gates

This file is a draft design, not implementation or deployment authority.

Document changes follow WRITE -> VERIFY -> DIFF -> AI TEAM AUDIT ->
FIX IF NEEDED -> RE-AUDIT -> PASS -> STAGE -> INSPECT STAGED DIFF ->
COMMIT -> PUSH. Chris executes every command.

Further implementation requires separate explicit approval, a bounded proposal
resolving the schemas, storage/retention choices, source-stability checks,
lock scope, resource budgets, and reporting arrangements above, synthetic
validation, and independent audit.

Production deployment, recurring verification, experiment adoption,
and restricted-evidence access require their applicable authorization.
