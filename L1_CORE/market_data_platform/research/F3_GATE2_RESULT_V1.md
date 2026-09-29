# F3 Gate-2 Result v1

**Result:** PASS
**Primary population:** `[7037, 174556]`
**Frozen endpoint:** `2026-09-28T07:22:28Z`
**Validated N:** `174556`

## Authority

This result applies the frozen adjudication structure in:

`L1_CORE/market_data_platform/research/F3_GATE2_ADJUDICATION_TEMPLATE_V1.md`

Frozen template commit:

`b74b662c10c7c636e2621535f8bbf82f839cfa4e`

Frozen template SHA-256:

`0008590323085356eb05b647b551dc0b9bde04041dc8bc3dc8a798b84f90a42c`

The governing Gate-2 structural performance criterion is:

> Persistence of a successfully detached batch must no longer occupy the WebSocket ingestion path for the duration of that persistence operation under normal queue capacity.

No numerical latency threshold, percentage-improvement threshold, performance score, profitability criterion, or economic criterion was introduced for this adjudication.

## Evidence provenance

- source host: `liquid-pi`
- collector PID at evidence freeze: `26953`
- collector restarts through frozen endpoint: `0`
- collector start: `Sat 2026-09-26 22:43:18 PDT`
- deployed commit: `601b813046c79d6ae0ec2511b56521dc23a8e29f`
- frozen endpoint UTC: `2026-09-28T07:22:28Z`
- frozen endpoint wall_ns: `1790580148000000000`
- primary start batch: `7037`
- validated N: `174556`
- complete structural-validation boundary: `[1,174556]`
- primary confirmatory population: `[7037,174556]`

### Source telemetry

`telemetry_2026-09-27.jsonl`

- size: `113124922` bytes
- SHA-256: `9e8a78dbec31b016534220d33fc58933ea630f7fe2d63685ad958c108c76a69d`

`telemetry_2026-09-28.jsonl`

- size: `209707059` bytes
- SHA-256: `13c449a93eb88e0314d4656811f43306b7957d36c6e1feaa9608793638ec9b3b`

### Derived complete-epoch structural evidence

`research_out/F3_GATE2_VALIDATION_1_TO_174556/f3_epoch_1_to_174556.jsonl`

- size: `195192235` bytes
- SHA-256: `66c6a1a7802d377d671e9cc2e1f329fe828ef95a0c34ae130e2e2a061146d015`
- selection: F3 persistence handoff/completion records with `1 <= batch_id <= 174556`
- ordering: original serialized source order
- byte handling: selected source JSONL lines copied byte-for-byte without reserialization
- performance-based selection: none
- source modification: none
- post-N evidence: excluded from this derived validation input and preserved in the Attempt-2 source artifact

Derivation program SHA-256:

`0d9e1822987572844ef6418700b1044af1f1b5a05be6209eaa0d32d8a42f0c75`

### Primary descriptive report

`research_out/F3_GATE2_VALIDATION_1_TO_174556/primary_7037_to_174556_summary.json`

- size: `1195` bytes
- SHA-256: `a2654e838623225261b0fdad196198a411281ac1b2a0bff5c5c151a50ddd37e5`

## Structural validation result

**PASS**

The frozen G2-8A `validate_and_pair()` structural validation accepted the complete derived epoch `[1,174556]`.

The primary population `[7037,174556]` was selected only after complete-epoch structural validation succeeded.

Primary paired-batch count:

`174556 - 7037 + 1 = 167520`

## Required descriptive report

### Population and correctness context

- worker epoch count: `1`
- paired batch count: `167520`
- total rows: `36515162`
- depth batches: `159034`
- trade batches: `8486`
- successful completion count: `167520`
- failed completion count: `0`
- failed completion batch IDs: `[]`
- queue capacity: `2`

### Ingestion-side handoff / backpressure

`submit_block_ms`:

- n: `167520`
- min: `0.031354`
- median: `0.097656`
- p95: `0.12526`
- max: `2986.251255`

Additional measurement:

- `queue_full_at_submit_start_count`: `301`

`submit_block_ms` is the measured queue-submission blocking interval. It excludes the subsequent handoff-observer callback and is not interpreted as total `_handoff_if_due()` occupancy.

### Canonical persistence execution

`worker_persist_ms`:

- n: `167520`
- min: `6.112164`
- median: `36.747846499999994`
- p95: `57.86433474999999`
- max: `4060.30485`

This measurement is canonical persistence execution only. Observer-callback duration is not merged into it.

### Accepted-batch queue residence

`queue_wait_after_accept_ms`:

- n: `167520`
- min: `0.344375`
- median: `1.1343455`
- p95: `5.762232349999999`
- max: `3073.899255`

Additional measurement:

- `queue_wait_unknown_count`: `0`

Queue residence is not interpreted as pure canonical-persistence pressure because earlier observer execution may contribute to it.

### Observer overhead

`previous_observer_callback_ms`:

- n: `335040`
- min: `0.107917`
- median: `0.260474`
- p95: `0.432498`
- max: `49.58736`

This is instrumentation overhead and is not classified as canonical persistence duration or persistence-queue backpressure.

### Queue / backlog state

`queue_depth_before`:

- n: `167520`
- min: `0`
- median: `0.0`
- p95: `0.0`
- max: `2`

`queue_depth_after_accept`:

- n: `167520`
- min: `1`
- median: `1.0`
- p95: `1.0`
- max: `2`

`queue_depth_at_completion`:

- n: `167520`
- min: `0`
- median: `0.0`
- p95: `0.0`
- max: `2`

Additional queue measurements:

- max observed queue depth: `2`
- queue depth before at capacity count: `301`
- queue depth after accept at capacity count: `1396`
- queue depth at completion at capacity count: `1296`
- queue depth observations at capacity: `2993`

For descriptive context only, `2993 / 167520 = approximately 1.79%`.

This ratio compares the number of recorded at-capacity queue-depth observations with the paired-batch count. It is not a claim that 1.79% of batches experienced saturation because multiple queue-depth observations may occur for a batch.

## Gate-2 result

**PASS**

### Structural basis

1. **Off-path canonical persistence**

   The primary evidence supports separation between ingestion-side queue submission and canonical persistence execution.

   `submit_block_ms` directly measures queue-submission blocking, while `worker_persist_ms` separately measures canonical persistence execution.

   The observed primary distributions are consistent with successfully detached persistence executing on the persistence worker rather than requiring the WebSocket ingestion path to remain occupied for the duration of each persistence operation under normal queue capacity.

2. **Bounded explicit backpressure**

   The frozen queue capacity was `2`, and the maximum observed queue depth was `2`.

   Queue saturation was observable rather than hidden: `queue_full_at_submit_start_count = 301`, and queue-submission blocking was directly measured.

   The primary evidence does not establish unbounded queue growth. The observed behavior is consistent with the frozen design requirement that saturation produce explicit backpressure rather than unlimited backlog.

3. **Correctness prerequisite preserved**

   The primary population contains `167520` successful completions and `0` failed completions.

   Complete-epoch evidence `[1,174556]` passed frozen structural validation.

   The primary evidence does not establish a Gate-1 correctness failure or weakening of the frozen correctness guarantees.

No frozen FAIL condition is established by the primary evidence, and the evidence is sufficient to adjudicate the structural criterion without adding a new threshold, causal claim, or post-hoc rule.

## Limitations / confounds

The primary population contains material tail observations that are preserved without converting them into post-hoc failure thresholds:

- maximum canonical persistence execution: `4060.30485 ms`
- maximum ingestion-side submit blocking: `2986.251255 ms`
- maximum accepted-batch queue residence: `3073.899255 ms`
- maximum previous-observer callback duration: `49.58736 ms`

The frozen adjudication criterion defines no numerical maximum, percentile, percentage-improvement, or absolute-latency threshold for PASS/FAIL. These tail observations therefore remain descriptive evidence and are not independently classified as failure conditions.

The queue reached its frozen capacity during the primary population:

- `queue_full_at_submit_start_count = 301`
- `queue_depth_observations_at_capacity = 2993`

For descriptive context, the at-capacity observation count is approximately `1.79%` of the paired-batch count. Because queue-depth measurements occur at multiple points and the frozen criterion does not numerically define "normal queue capacity," this ratio is preserved as a limitation/confound rather than treated as a success or failure threshold.

Queue residence and backlog observations cannot be attributed exclusively to canonical persistence. Observer execution and other measured system behavior may contribute.

The evidence establishes the frozen structural Gate-2 criterion; it does not establish the physical cause of the observed latency tails.

## Claims explicitly not established

This Gate-2 PASS does not establish:

- physical SSD or disk performance;
- Coinbase or network performance;
- trading performance;
- profitability or economic value;
- execution quality;
- an optimized persistence-queue capacity;
- that queue residence or backlog was caused exclusively by canonical persistence;
- that the multi-second tail observations have a particular physical cause;
- that F2's historical evidence changed.

Correlation between backlog and persistence duration alone is not treated as causal proof.

## Post-N evidence boundary

Evidence after batch `174556` remains outside the primary confirmatory population and is preserved in the frozen Attempt-2 source artifact.

The later unmatched batch `288135` is therefore not used to determine the Gate-2 result for `[7037,174556]`. Its operational/liveness significance remains a separate post-closeout matter and is not erased or repaired by this adjudication.

## Outstanding post-closeout operations

This result does not release collector protection or authorize Pi3-to-Pi5 migration.

Still outstanding outside this Gate-2 scientific adjudication:

- bounded Pi3 collector liveness/progression verification;
- explicit collector-protection release decision;
- final Pi3/Pi5 runtime-placement adjudication;
- F2/F3 watchdog semantic-mismatch disposition;
- final independent Claude audit of the complete closeout and migration handoff;
- resolution of any material final-audit findings before GM handoff.
