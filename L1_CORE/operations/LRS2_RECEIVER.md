# LRS2 receiver: infrastructure only

`lrs2_snapshot_receiver.py` independently verifies an already staged snapshot
created by `lrs2_snapshot_handoff.py`. The producer remains source-only.
No transport, scheduler, service, checkpoint, matrix, CP15, research-state update,
or authority transfer is implemented or invoked.

The operator supplies `--staging`, `--publication-root`,
`--expected-snapshot-id`, `--expected-source-host`, and
`--expected-source-commit`. Expectations must come from the trusted source-side
handoff record, not from the incoming manifest itself. The snapshot identity is
the producer's UTC directory name (`YYYYMMDDTHHMMSS.ffffffZ`). Source paths must
match the canonical repo-relative Pi3 CSV paths. Flags are JSON false, as emitted
by producer schema 1. Sizes are recorded in each source boundary, not in an
additional file-size field.

Staging must be a hidden direct child of the existing publication root on the
same filesystem. All path components must be free of symlinks. Exactly three
single-link regular files are accepted. Verification includes strict manifest
fields, duplicate-key rejection, source provenance, UTC identity, boundary
equality, byte sizes, last physical line, hashes, and pandas CSV row/column counts.
The parser matches the producer's pandas semantics; these are structural checks,
not research/data-quality conclusions.

A native atomic no-replace rename publishes the whole directory only after
validation. Linux requires libc `renameat2`; macOS uses `renamex_np`. Missing
support fails closed. Existing destinations, including racing empty directories,
are never replaced. Failures leave staging for infrastructure investigation.
Stdout contains one JSON PASS/FAIL event; exit status is zero only for PASS.

Operational precondition: the receiver account must exclusively own staging and
publication directories, and transfer must be finished before verification starts.
No uploader or other process may mutate these paths during verification/publication.
Identity/metadata rechecks detect ordinary concurrent changes, but this is not a
sandbox against a malicious writer with the same filesystem permissions. Hashes
validate bytes against the manifest, not the authenticity of a malicious manifest.
Authenticated transport and trusted external expectations belong to the later
bridge phase. Publication is atomic visibility, not a power-loss durability or
filesystem immutability guarantee; directory permissions remain an operational
responsibility.

## Infrastructure evidence ownership

Use `L1_CORE/operations/evidence/lrs2_bridge/` for reviewed, durable infrastructure
handoff/audit records in the canonical Mac→GitHub flow. This location is separate
from LRS2 research roadmap/backlog and research findings. This change establishes
the location convention only; no historical result is invented or promoted.

For future runtime event capture, use an infrastructure-owned persistent Pi5
location outside the checkout, proposed `/var/lib/liquid-research/operations/lrs2_bridge/events.jsonl`.
Provisioning, permissions, retention, durable append/fsync, and forwarding are
future bridge work. The receiver currently emits JSON to stdout only; successful
publication does not claim that a durable external evidence append occurred.
Capture expected identity, source commit, manifest hash, verification result,
verified file metadata, and timestamp. These records demonstrate infrastructure
checks only and do not constitute checkpoint or research conclusions.

## Local verification

Run `python -m unittest discover -s L1_CORE/operations -p 'test_lrs2_snapshot_receiver.py'`.
Fixtures use temporary directories and synthetic CSVs only.
