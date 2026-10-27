# Time-Conditioning Capacity Checkpoint

Recorded: 2026-10-26.
Documentation baseline: 356a19acdfa685f1900a76156c164e98908ce37c.
Classification: retrospective engineering measurements, not prospective anchors.
Study status: DRAFT / UNFROZEN; no historical analytical execution authorized.

## Scope and Evidence Provenance

Chris authorized bounded metadata discovery, footer inspection, two-column
population counting, checkpoint writes, and synthetic Pi5 profiling.
These were capacity measurements, not execution of the proposed study.

This document summarizes operator-pasted execution transcripts. Detailed
counting records remain on Pi3 and profiling records remain on Pi5 at
the paths below; they are not embedded in this repository document.
The records are ordinary operator-controlled files, not immutable storage
or independently authenticated service attestations.

## Pi3 Source Scope

Canonical trade root:
`/mnt/lrs001/data/market_data_platform/canonical/trades`.

Exactly 28 source partitions were selected:
- 2026-07-21 through 2026-08-10 inclusive.
- 2026-08-25 through 2026-08-31 inclusive.

All selected dates precede the September 4 sealed-reserve boundary.
No depth data or H2 partitions were included.

Metadata discovery observed 227,731 canonical file paths and 1,009,697,774
logical bytes. Of these, 3,092 paths on August 25 had link count two,
accounting for 19,507,008 logical bytes. Other hard-link locations and
file-specific backup provenance remain unverified. These are path-based
logical totals, not unique-inode disk usage or transfer approval.

The footer scan completed in 478.164 seconds, reporting 19,196,490 stored
rows, 227,731 row groups, and a largest file row count of 298.
Requested envelope/footer reads totaled 424,859,579 bytes.
Footer metadata alone did not verify data-page contents or instrument-day
population counts.

## Checkpointed Two-Column Counts

The first monolithic two-column count stopped INCOMPLETE at its runtime
boundary after 1,194.045 seconds and 517,019,953 requested source bytes.
It established no complete population totals. It was not automatically
retried or treated as a successful inventory.

The replacement counter was committed at
`c8a4f1c5787523eb8a8613ccf62d0b7f7c6d1c8d`, with 37 synthetic tests
passing on Mac and independent review before the Pi3 trial.

One source partition was processed per worker under these limits:
- 12,000 files.
- 80 MiB logical source bytes.
- 80 MiB requested source reads.
- 2,000,000 decoded rows.
- 256 MiB process address space.
- 300-second worker wall-clock limit, with termination grace.
- Single-thread numerical-library settings.

The reader requested envelope/footer bytes and only the instrument_id
and trade_time column chunks. It did not request price/outcome chunks
or decode analytical features. Source data was not modified.
Requested read accounting excludes kernel/filesystem read amplification.

All 28 partition completion records were produced and validated before
aggregation. Final totals:
- Files: 227,731.
- Logical source bytes: 1,009,697,774.
- Requested source bytes for completed partition counts: 539,887,459.
- Decoded rows: 19,196,490.
- Rows selected into the 48 defined instrument-day windows: 15,772,386.
- Rows excluded by that selection: 3,424,104.
- Multiply linked canonical paths: 3,092.

The largest selected instrument-day was BTC-USD on 2026-08-28:
678,382 rows. These counts follow the specified previous/target/next
partition selection; they do not establish complete exchange-feed coverage.

Pi3 checkpoint root:
`/home/kristo/lrs3-capacity-counts-v1/`.

Final batch records:
`/home/kristo/lrs3-capacity-tmux-78851f6e1686/`.

The saved combined.json matched the SHA-256 recorded in finished.json:
`08ca48fab946b4ca27389d4ed8cc9417f06d7358d9a8b7d56cbe96e52c0552c9`.

The completion record reports 2026-10-25T23:15:49.633894+00:00.
Matching local hashes bind record bytes, not independent authenticity
or unchanged source content between sequential partition observations.

Collector service observations matched around the reported scans:
active/running, MainPID 1190, NRestarts 0. These observations do not
prove uninterrupted collection, zero dropped events, or absence of
transient performance effects.

## Synthetic Pi5 Profiling

The independently reviewed profiler was committed at
`356a19acdfa685f1900a76156c164e98908ce37c`.
Its Mac synthetic suite passed 16 tests before execution on Pi5.

Profiling ran from a clean isolated checkout:
`/home/kristo/lrs3-pi5-profiler-356a19a/`.

Records were published under:
`/home/kristo/lrs3-pi5-profiling-v1/`.

Environment: Linux aarch64, Python 3.13.5, NumPy 2.4.6.
Each case used a fresh worker, a 2 GiB address-space limit,
single-thread settings, and a 300-second wall-clock limit.
All four workers exited successfully with empty stderr tails.

| Synthetic rows | Stage | Peak process RSS, bytes | Worker wall time, seconds |
|---:|---|---:|---:|
| 678,382 | Array sorting | 71,729,152 | 0.330678 |
| 678,382 | Actual calculation kernel, including preparation | 77,709,312 | 1.220595 |
| 1,356,764 | Array sorting | 105,627,648 | 0.527491 |
| 1,356,764 | Actual calculation kernel, including preparation | 117,374,976 | 2.340970 |

The stress case doubles the largest measured instrument-day row count.
Inputs were deterministic fabricated arrays. The calculation stage called
the existing compute_screen kernel, rather than a proxy VWAP/spread routine.
No historical payloads were opened or transferred for these benchmarks.

Profiler source SHA-256:
`76227e12e07b6e63e987044e0ac37bc8dfb64c08491cfbfa876f4d0ad5907558`.

Kernel source SHA-256:
`35ee2a19ea9c87ece6bc5533b9462d1035c1e83e7a53a43ff5ce809f70b3ae67`.

RSS values are process-lifetime high-water marks. Kernel-process peaks
include synthetic input generation and sorting; they are not isolated
incremental kernel allocations. Address-space limits and resident-memory
measurements are different quantities.

## Synthetic Pi5 Parquet Loader Checkpoint — 2026-10-26

The separately authorized synthetic-file extension was independently
reviewed and committed at
`9e2b0f4e76279df01c5bcad9ff93b9be919df3e2`.
The loader-profiler and shared regression suites passed 38 tests on Mac.

Both full-size cases subsequently completed successfully on Pi5, using
Python 3.13.5, NumPy 2.4.6, and PyArrow 25.0.0. Each fresh worker used
a 2 GiB address-space cap, single-thread settings, and a 300-second
wall-clock limit.

The generator created three synthetic partitions dated August 21–23,
with 8,955 files per partition. Controls included ETH rows, BTC rows
before the target day, and BTC rows exactly at its exclusive end.
The actual shared resolver, two-pass loader, decimal-to-float conversion,
integrity checks, lexsort, and sorted-array validation were exercised.
Exact selected synthetic trade-ID membership was also verified.

| Selected rows | Synthetic files | Generated rows including controls | Fixture file bytes | Peak process RSS, bytes | Total elapsed seconds |
|---:|---:|---:|---:|---:|---:|
| 678,382 | 26,865 | 758,977 | 81,831,442 | 169,328,640 | 70.973315 |
| 1,356,764 | 26,865 | 1,437,359 | 94,531,635 | 204,832,768 | 74.220515 |

Both workers exited with status zero and published COMPLETE records.
Captured stderr contained expected shared-loader progress messages.
The isolated checkout finished clean at the pinned revision.

Checkout: `/home/kristo/lrs3-pi5-loader-profiler-9e2b0f4/`.
Retained fixture/report root: `/home/kristo/lrs3-pi5-loader-profiling-v1/`.

Attempt directories beneath that root:
- `parquet-loader-678382--556dd903-5e81-40e9-96c4-d1cc1e701a98`
- `parquet-loader-1356764--03d98d06-1dfd-4e00-926d-891e8aa52382`

Each attempt retains its synthetic-trades directory and completion record.
Combined generated fixture file bytes total 176,363,077, approximately
168.2 MiB; this is not a measurement of physical allocated disk space.
Files used Parquet compression NONE. No automatic cleanup occurred.

Loader-profiler source SHA-256:
`3a064a717aea7173d4aa80bc029e330afd3a9a2342407e7e71b86cc038f448bb`.

Shared loader source SHA-256:
`52b58a3b45a2a063a829541f395c454e9a1e336c1d14b39b4a1074299f0ee072`.

The previously recorded base-profiler and kernel hashes also matched
the reported worker measurements.

These are process-lifetime RSS high-water marks, including fixture
generation and membership-validation allocations. Phase checkpoints
are cumulative high-water observations, not isolated phase allocations.
The synthetic file distribution and values are not a reconstruction
of historical data. No canonical files were accessed, no historical
payloads were transferred, and no calculation kernel or new study
reporting ran in these loader workers.

## Synthetic Descriptive Reporting Checkpoint — 2026-10-26

Chris separately authorized synthetic-only descriptive reporting development.
The independently reviewed module and tests were committed at
`d2aa90a819603a3a417613ef03a4a809b7d51070`:
- `L1_CORE/market_data_platform/research/time_conditioning_descriptive.py`
- `L1_CORE/market_data_platform/research/test_time_conditioning_descriptive.py`

Validation passed 20 synthetic tests on Mac and 20 on Pi5
(0.23 seconds on Pi5). Pi5 used the existing isolated validation checkout
at `/home/kristo/lrs3-validation-198bb8f/source/`, which finished clean
at the committed revision. No tests were run on Pi3 for this component.

The pure reporting API accepts summarized synthetic group counts and
return means, validates the complete 24-date / 48-instrument-day matrix,
and reports both mechanisms across all four horizons. It preserves
invalid cells and dates explicitly, pairs valid BTC and ETH deltas with
equal weight within each date, and reports leave-one-date-out sensitivity
only when at least two valid date pairs exist.

Malformed inputs raise ReportError. Missing or nonfinite populated-decile
means produce explicitly invalid cells; empty deciles require null means.
COMPLETE_DESCRIPTIVE denotes processing completion, not scientific validity.
The module adds no significance tests, promotion thresholds, winner
selection, or automatic follow-up decision.

The synthetic input classification is a caller declaration, not an
authentication mechanism. The module does not verify upstream populations,
decile assignments, or means. Tests used fabricated summaries; they did
not execute the historical analyzer, load canonical files, or establish
end-to-end integration from the calculation kernel into the new report.

Development bounds are 100,000 eligible observations per instrument-day
horizon and a 1 MiB serialized report. These are not frozen historical
execution budgets. Reporting has not been profiled in a combined
loader/kernel/reporting process.

## Remaining Limits and Decisions

The measurements establish completed capacity observations and synthetic
headroom for the tested array/sorting and kernel cases only.

Synthetic loader checks now exercise Parquet loading, file discovery,
schema conversion/filtering, and sorting on generated corpora. They do
not measure historical-data execution or an integrated loader/kernel/reporting
run. The reporting module was tested separately on fabricated summaries.
These checks do not reproduce
every possible historical-data allocation pattern. No full-pipeline
memory-safety, feed-completeness, profitability, or scientific-readiness
claim follows.

The study still requires final resource budgets, input identity and
retention arrangements, synthetic integration and combined resource
validation of the study components, a frozen prospective predeclaration, and explicit
authorization for any acquisition or historical execution.

Original Candidate D D0 remains blocked with its matrix unchanged.
Production transfer and broader pilot remain HOLD.
H2 remains SEALED, 2026-09-04 through 2026-10-01 inclusive.
Scientific readiness remains PENDING.
The proposed exploratory study remains DRAFT / UNFROZEN.
