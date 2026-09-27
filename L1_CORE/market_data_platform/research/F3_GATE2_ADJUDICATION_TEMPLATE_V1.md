# F3 Gate-2 Adjudication Template v1

**Frozen before primary production performance analysis.**

## Purpose

Define the reporting and adjudication structure for F3 Gate-2 before inspecting the frozen primary production performance distributions.

This template does not change the F3 methodology, production observation protocol, evidence population, queue capacity, F2 baseline, or Gate-2 success criterion.

It introduces no numerical latency target, percentage-improvement target, performance score, profitability criterion, or economic criterion.

## Authority

Gate-2 remains governed by the frozen F3 structural performance criterion:

> Persistence of a successfully detached batch must no longer occupy the WebSocket ingestion path for the duration of that persistence operation under normal queue capacity.

The magnitude of observed behavior must be measured and reported descriptively rather than judged against a post-hoc numerical threshold.

Gate-1 correctness remains a prerequisite. Apparent performance improvement cannot override a correctness failure.

## Evidence population

Primary confirmatory evidence is the frozen Section 17 population:

`[7037, N]`

where N is established under Sections 17 and 18 without using Gate-2 performance values.

The complete epoch prefix `[1, N]` exists for structural validation and provenance only. It does not expand the primary confirmatory population.

Pre-protocol batches `1..7036` and evidence after N remain observational evidence outside the primary confirmatory population.

## Preconditions before adjudication

Do not perform primary Gate-2 performance adjudication unless all of the following are established:

1. the planned observation endpoint has passed;
2. collector continuity through the endpoint is verified;
3. no disqualifying Section 17 environmental boundary occurred;
4. N is deterministically established;
5. raw evidence is frozen and integrity-verified;
6. complete epoch evidence `[1, N]` passes frozen G2-8A structural validation;
7. the primary population `[7037, N]` is selected only after that validation.

If any prerequisite fails, stop and preserve the evidence under the applicable Section 17/18 rule.

## Required descriptive report

Report the primary population without collapsing distinct measurement families.

### Population and correctness context

- worker epoch count:
- paired batch count:
- total rows:
- batch counts by label:
- successful completion count:
- failed completion count:
- failed completion batch IDs:
- queue capacity:

### Ingestion-side handoff / backpressure

Report `submit_block_ms`:

- n:
- min:
- median:
- p95:
- max:

Also report:

- `queue_full_at_submit_start_count`:

`submit_block_ms` is the direct measured queue-submission blocking interval. It excludes the subsequent handoff-observer callback and must not be presented as total `_handoff_if_due()` occupancy.

### Canonical persistence execution

Report `worker_persist_ms`:

- n:
- min:
- median:
- p95:
- max:

This measures canonical persistence execution only. Do not merge observer-callback duration into this measurement.

### Accepted-batch queue residence

Report `queue_wait_after_accept_ms`:

- n:
- min:
- median:
- p95:
- max:

Also report:

- `queue_wait_unknown_count`:

Unknown queue residence remains unknown and must not be converted to zero.

Queue residence must not be described as pure canonical-persistence pressure because earlier observer execution may contribute to it.

### Observer overhead

Report `previous_observer_callback_ms`:

- n:
- min:
- median:
- p95:
- max:

Treat this as instrumentation overhead. Do not classify it as canonical persistence duration or persistence-queue backpressure.

### Queue / backlog state

Report:

- `queue_depth_before` distribution:
- `queue_depth_after_accept` distribution:
- `queue_depth_at_completion` distribution:
- `max_observed_queue_depth`:
- `queue_depth_before_at_capacity_count`:
- `queue_depth_after_accept_at_capacity_count`:
- `queue_depth_at_completion_at_capacity_count`:
- `queue_depth_observations_at_capacity`:

Queue/backlog observations describe the instrumented production system. They must not be attributed exclusively to canonical persistence without independent evidence.

## Structural adjudication

### PASS

Gate-2 passes only if the frozen primary evidence supports the existing structural criterion:

1. successfully detached canonical persistence executes outside the WebSocket ingestion path rather than occupying that path for the duration of persistence;
2. the bounded queue preserves the defined backpressure behavior rather than hiding sustained throughput mismatch behind unbounded backlog;
3. the production evidence does not establish a Gate-1 correctness failure or weakening of the frozen correctness guarantees.

A PASS does not require an arbitrary percentage improvement or absolute latency threshold.

### FAIL

Gate-2 fails if the primary evidence establishes any methodology-defined failure condition, including:

- canonical persistence still occupies the WebSocket ingestion path for the duration of persistence;
- persistence was moved off-path but queue backlog grows without bound;
- correctness guarantees weakened or a Gate-1 correctness failure is established;
- another frozen F3 failure condition is established by the evidence.

### INCONCLUSIVE

Use INCONCLUSIVE when the preserved evidence is insufficient to determine whether the frozen structural criterion is satisfied or failed without adding a new assumption, threshold, causal claim, or post-hoc rule.

Inconclusive evidence must remain preserved as such and must not be rewritten as PASS or FAIL.

## Interpretation boundaries

Regardless of PASS, FAIL, or INCONCLUSIVE, do not infer from Gate-2 alone:

- physical SSD or disk performance;
- Coinbase or network performance;
- trading performance;
- profitability or economic value;
- execution quality;
- an optimized persistence-queue capacity;
- that queue residence or backlog was caused exclusively by canonical persistence;
- that F2's historical evidence changed.

Correlation between backlog and persistence duration alone is not causal proof.

## Final result record

**Primary population:** `[7037, N]`

**Evidence provenance:**
- source host:
- collector epoch:
- source telemetry files:
- frozen evidence files:
- SHA-256:
- N:
- structural validation result:

**Gate-2 result:** `PASS / FAIL / INCONCLUSIVE`

**Structural basis:**
[Fill only from frozen primary evidence.]

**Descriptive measurements:**
[Insert the required report above without introducing a success threshold.]

**Limitations / confounds:**
[Record observer overhead, unknown measurements, evidence limitations, and any other supported confounds.]

**Claims explicitly not established:**
[Record applicable interpretation boundaries.]

## Freeze rule

After this template is frozen, production results may fill its evidence fields and support the existing PASS / FAIL / INCONCLUSIVE branches.

Production results must not be used to retroactively add a numerical success threshold, change the primary population, redefine N, weaken a failure condition, or rewrite the structural Gate-2 criterion.
