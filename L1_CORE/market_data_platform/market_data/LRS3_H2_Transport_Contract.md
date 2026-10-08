# LRS3 Candidate C — H2 Transport-Only Contract

## Authority
GM-CANDIDATE-C-002 authorizes development and synthetic testing only.
Production transfer: HOLD. H2 predictive research: SEALED.
Scientific readiness: PENDING.
Classification: SEALED / TRANSPORT ONLY.
Transport/storage does not authorize predictive outcome analysis.

## Scope
Dates: 2026-09-04 through 2026-10-01 inclusive.
Datasets: trades, depth_levels.
Instruments: BTC-USD, ETH-USD.
Operations: structural validation, schema validation, hashing,
byte-preserving copying, storage, destination integrity verification.

## Entry Point
legacy_snapshot_transport.run_synthetic_h2_transport(
    authorization_path, source_root, destination_root,
    max_files, max_source_bytes, max_runtime_seconds
)
Only synthetic development fixtures are permitted.

## Authorization JSON — Required Fields
authorization_id: nonempty string
purpose: SYNTHETIC_DEVELOPMENT_TRANSPORT_ONLY
permitted_operations: exact approved operation list
source_root: canonical absolute source path
destination_root: canonical absolute destination path
datasets: approved dataset list
instruments: approved instrument list
start_date: 2026-09-04
end_date: 2026-10-01
valid_from_utc: UTC timestamp
valid_until_utc: UTC timestamp
resource_budget_references: nonempty string mapping
Authorization is checked before H2 source enumeration.
The authorization ID and SHA-256 digest are recorded in evidence.
Local authorization is an operator control, not tamper-proof security.

## Evidence
Destination file: transport_evidence.json
Top-level fields: prototype, production_transfer_authorized,
predictive_analysis_authorized, classification, authorization_id,
authorization_sha256, source_root, destination_root, file_count,
source_bytes, max_files, max_source_bytes, max_runtime_seconds,
resource_budget_references, files.
Per-file fields: relative_path, size_bytes, sha256, classification.
TRANSPORT_COMPLETE contains the authorization digest.
The marker alone is not independent proof of destination integrity.

## Limitations
Failed runs may leave partial destination files.
Destination must not exist before execution.
File and byte budgets are cooperative checks.
Runtime limits are cooperative, not hard execution caps.
Filesystem identity checks do not provide atomic snapshots.
No production authorization record has been issued.


## Independent Destination Verification

Entry point:
legacy_snapshot_transport.verify_synthetic_h2_transport_destination(
    evidence_path, destination_root
)

This verifier operates on the destination only. It does not read the
original H2 source corpus or authorize production transfer.

It independently hashes destination files and compares them with
transport_evidence.json. It checks recorded file sizes, file counts,
total bytes, H2 partition scope, classification, authorization digest,
completion marker, and unexpected destination files.

The verifier rejects detected file tampering, missing files,
unexpected files, symlinks, and malformed or inconsistent evidence.

Verification confirms agreement with the local evidence record.
It is not cryptographic proof that the evidence itself is authentic,
nor does it establish scientific readiness or production authorization.

## Resource and I/O Accounting

max_source_bytes limits the cumulative logical size of selected
source files. It is not a limit on total disk I/O.

Source validation, repeated hashing, copying, destination hashing,
post-copy source hashing, and independent verification cause
multiple reads and writes of the same payload.

Total physical I/O can substantially exceed max_source_bytes.
Depending on the validation implementation and filesystem behavior,
it may exceed five times the logical source bytes.

max_files and max_source_bytes are cooperative transport budgets.
max_runtime_seconds is checked between operations, not enforced
as a hard deadline during individual file reads or copies.

A successful completion marker does not replace independent
destination verification.

## Release Gates
Synthetic tests and existing regressions must pass.
Independent AI-team audit of changed code is required.
Audit findings must be resolved or dispositioned.
Exact staged blobs require review before commit.
User approval is required before commit or push.
