# STORAGE-PATH DIVERGENCE INCIDENT / RECONCILIATION RECORD

## 1. Executive Summary
On 2026-08-24 between 23:41:22-23:41:33 PDT, the symlink at
`L1_CORE/market_data_platform/data/canonical` (intended to point at
the SSD-backed canonical storage at
`/mnt/lrs001/data/market_data_platform/canonical`) was replaced by a
real, plain directory. From that moment until the collector was
manually stopped on 2026-08-30, the live collector wrote all trade
and depth records into this repo-local directory instead of the
intended SSD location. This was discovered on 2026-08-30/31 during
an unrelated historical depth-identity investigation, when the
expected canonical depth corpus was found to stop at `date=2026-08-25`
despite the collector reporting active status through Aug 30.

No data was lost. The misplaced data (47,918 trade files, 1,088,320
depth files, spanning 2026-08-25 through 2026-08-31, ~8.8GB) was
reconciled into the correct SSD canonical tree via a memory-safe,
fail-closed reconciliation script, independently verified, and the
symlink was restored on 2026-09-01/02. The collector was restarted
and confirmed writing to the correct location via two independent
verification paths.

## 2. Discovery
While investigating historical depth-level instrument identity as a
follow-on to the separate instrument-identity incident (see
`INSTRUMENT_IDENTITY_INVESTIGATION.md`), a read-only census of the
depth corpus found the last date partition was `date=2026-08-25`,
despite the collector service reporting `active` continuously since
a restart on 2026-08-27. A direct search confirmed a second, complete
depth and trade tree existed inside the Pi repository checkout at
`L1_CORE/market_data_platform/data/canonical/`, containing real,
continuously-growing data through the date of discovery.

## 3. Root Cause
`storage.py` defines `CANONICAL_ROOT` as a relative path:
`"L1_CORE/market_data_platform/data/canonical"`. The systemd service
unit (`liquid-research-collector.service`) sets
`WorkingDirectory=/mnt/lrs001/liquid-research-l0l4`, so this relative
path has always resolved to
`/mnt/lrs001/liquid-research-l0l4/L1_CORE/market_data_platform/data/canonical`.
Historically, that path was a symlink to the real SSD storage
location (established during the original Pi migration, confirmed
working as of commit `6b8194a`, 2026-08-24 23:37:52 PDT, whose
message explicitly documents the symlink). Sometime in the following
~4 minutes, that symlink was replaced by a real, plain directory.

**The exact command or process that caused this replacement is NOT
established.** Pi shell history was searched directly for operations
referencing `canonical` (rmtree, replace, move, rename, remove,
mkdir) outside of the known, unrelated historical-trade-recovery
pilot/full-reconstruction scripts. No matching evidence was found.
Two `shutil.rmtree()` calls were located in shell history near the
relevant timestamps but were confirmed, by direct inspection of their
surrounding code, to be defensive cleanup logic operating on the
separate historical-trade recovery corpus (`instrument_id_trades_pilot`
/ `instrument_id_trades_full`), not on the canonical symlink itself.
The timing overlaps the Aug 24 instrument-identity/repository work,
but this is a timing correlation, not a confirmed causal mechanism.
This should be treated as a permanently unresolved forensic question
unless new evidence emerges.

## 4. Scope and Impact
Affected: all live trade and depth collection from approximately
2026-08-24 23:41 PDT through 2026-08-30 (when the collector was
manually stopped for investigation) -- roughly six days. No data was
lost; every record was written successfully, just to the wrong
physical location. The real SSD canonical corpus (all data through
2026-07-21 -- 2026-08-24) was entirely unaffected and remained
correct throughout.

## 5. Evidence Preservation (Pre-Reconciliation)
Before any data was moved, the following was independently
established and verified via direct Pi filesystem inspection:

- Divergence boundary: last SSD write at epoch `1787640082.93`
  (2026-08-24 23:41:22 PDT); first forked-tree write at epoch
  `1787640093.02` (2026-08-24 23:41:33 PDT) -- an ~10.1 second gap.
- Fork tree contents (verified via `find`, per-date, both datasets):
  trades 47,918 files across `date=2026-08-25` through
  `date=2026-08-31`; depth_levels 1,088,320 files across the same
  date range.
- Full-corpus filename collision check (fork vs. SSD, all dates,
  both datasets): 0 collisions found.
- Schema/readability spot-check (20-file random sample per dataset):
  0 read failures, single consistent schema matching the official
  post-instrument-id-fix canonical schema (including `instrument_id`).
- Zero-byte file census across the entire fork: exactly 1 file
  (`depth_levels/date=2026-08-31/921c0484-2830-476a-85ac-ce7e402fc49c.parquet`).

## 6. Reconciliation Method
A temporary, non-committed reconciliation script
(`reconcile_forked_canonical.py`) was authored on the Mac homebase
repository, syntax-verified, then transferred to the Pi via direct
`scp` (not `git push`/`git pull`, per a deliberate decision that
one-shot incident-recovery tooling with hard-coded, single-use
manifests should not become permanent repository source -- consistent
with how the original instrument-identity recovery/promotion scripts
were handled).

The script was memory-safe by design (streaming, one date-partition
at a time -- an earlier, non-streaming version was OOM-killed on the
Pi's ~905Mi RAM after attempting to materialize the full ~1.1M-file
copy plan in memory at once) and fail-closed: `--verify-manifest`
confirmed live filesystem state matched the frozen preflight manifest
exactly before any write was permitted; `--dry-run` previewed the
exact copy plan with zero collisions; `--execute` re-verified the
manifest internally immediately before writing, copied each file via
temp-file-then-rename with a source/destination size check and
Parquet-metadata readability check on both the source and the
written temp file before the atomic rename into place, and would
abort entirely on any collision.

Execution was run via `nohup` (Pi-independent of the SSH session) and
completed with exit code 0: 47,918 trades copied, 1,088,319 depth
files copied (1 zero-byte file correctly excluded), 0 failures.

## 7. Post-Merge Validation
The reconciliation script's own `--verify-post-merge` check reported
a `MISMATCH` on `depth_levels/date=2026-08-31` (expected 51,696,
actual 51,695) -- this is a known limitation of that specific check,
which compares against the raw fork manifest without accounting for
the one deliberately-excluded zero-byte file, and does not indicate
a real defect.

An independent, more rigorous forensic audit was performed directly
against `date=2026-08-31` depth data: a full filename-level set
comparison (fork vs. SSD) found exactly one missing filename, and it
was confirmed identical to the known zero-byte exclusion; an
exhaustive size comparison across all 51,695 common filenames found
zero mismatches; a targeted SHA-256 hash comparison on a 5-file
sample found 5/5 exact matches. This independently and conclusively
confirms the apparent post-merge count discrepancy is fully explained
by the intentional zero-byte exclusion, with no evidence of any lost
or corrupted non-zero-byte file.

## 8. Architecture Fix
The forked directory
(`L1_CORE/market_data_platform/data/canonical`, a real plain
directory at the time) was renamed (not deleted) to
`canonical_fork_backup_20260901`, preserving it fully intact. A new
symlink was then created at the original path, pointing to
`/mnt/lrs001/data/market_data_platform/canonical`, restoring the
architecture that was confirmed working prior to the incident.

## 9. Collector Restart and Verification
The collector was restarted via
`systemctl start liquid-research-collector.service` and confirmed
active. After a brief settling period, fresh trade and depth files
(`date=2026-09-02`) were confirmed present via two independent
verification paths: (1) reading through the newly-restored symlink,
and (2) reading the real SSD path directly, bypassing the symlink
entirely. Both paths showed matching, genuine new files, and the
symlink itself was re-confirmed intact (not silently replaced again)
immediately after these checks.

## 10. Remaining Limitations / Unresolved Items
- The exact command/process that destroyed the original symlink on
  2026-08-24 is not established and is not expected to be
  recoverable from available evidence (see Section 3).
- `storage.py`'s `CANONICAL_ROOT` remains a relative path. The
  symlink has been restored, but the underlying fragility that
  allowed this incident (silent dependence on a symlink surviving,
  with no startup verification) has not been hardened. A future fix
  should consider either making `CANONICAL_ROOT` absolute or adding
  an explicit startup check that verifies the canonical path is a
  real symlink pointing to the expected SSD location before the
  collector begins writing, failing loudly rather than silently
  writing to the wrong place if that check fails. This is not yet
  implemented.
- The retained fork backup (`canonical_fork_backup_20260901`, ~8.8GB)
  has not been deleted. There is no storage pressure requiring its
  removal (self, ~790GB free on the SSD at time of writing). Deletion
  should be a deliberate, separate decision made only after this
  document is considered a complete and accurate record.
- The reconciliation script (`reconcile_forked_canonical.py`) was
  never committed to version control, per the deliberate,
  precedent-consistent decision that one-shot incident tooling with
  hard-coded manifests does not belong in permanent source. It
  currently still exists locally on the Pi and should be deleted
  once this document is considered final.

## 11. Final Status
Fork reconciliation: complete, executed, independently and
forensically validated with zero evidence of data loss or
corruption. Architecture: symlink restored, verified resolving
correctly. Collector: restarted, confirmed writing to the correct
real SSD location via two independent verification methods. This
incident is considered operationally closed. The prevention hardening
described in Section 10 and the fork-backup retention decision remain
open, deliberate follow-up items, not blockers to this closure.
