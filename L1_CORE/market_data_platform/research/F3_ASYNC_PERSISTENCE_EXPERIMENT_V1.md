# LRS-3 F3 — Asynchronous Persistence Experiment v1

**Status:** PRE-IMPLEMENTATION METHODOLOGY FREEZE
**System:** L1_CORE / Market Data Platform
**Experiment:** F3
**Predecessor:** F2 collector timing/provenance experiment

---

## 1. Purpose

F3 tests whether canonical persistence can be removed from the synchronous WebSocket ingestion path such that large-message receive-loop occupancy is materially reduced while preserving the collector's existing correctness, persistence, reconnect, failure, and shutdown guarantees.

F3 is an engineering experiment. It does not test trading edge, profitability, execution quality, fill behavior, or second-exchange behavior.

---

## 2. Evidence Basis

F3 is motivated by the validated F2 production finding.

In the frozen F2 sample of 20 qualifying Coinbase L2 messages (10 BTC-USD and 10 ETH-USD), measured local collector stages fully reconstructed the observed multi-second loop gaps with effectively zero closure error.

Synchronous flush was the largest measured component of median loop-gap duration, at approximately 67%, followed by decode-to-parse at approximately 29%.

Across the same frozen 20-event sample:

- rows versus decode duration: r = 0.984961
- rows versus parse duration: r = 0.983334
- rows versus synchronous flush duration: r = 0.998312
- rows versus total loop-gap duration: r = 0.998250

F2 established an engineering constraint in the current synchronous architecture. It did not isolate physical disk I/O as the root cause and did not establish that a writer thread or any other specific architecture would solve the observed behavior.

---

## 3. Current Baseline Architecture

The current production path is synchronous:

WebSocket receive
→ JSON decode
→ canonical parse
→ add records to RecordBuffer
→ flush if due
→ canonical persistence
→ return to next WebSocket receive

For a qualifying large message, persistence therefore occupies the same execution path that must return before the collector can begin its next receive.

RecordBuffer currently preserves complete-message batching semantics: a single exchange message may push the buffer beyond the nominal count threshold because the threshold is evaluated after the complete message has entered the buffer.

Buffers are process-lifetime objects and survive reconnects. Sequence tracking is connection-session scoped and resets on reconnect.

Canonical persistence currently uses UTC-date grouping and immutable uniquely named Parquet files. Persistence failures are structural rather than silently ignored.

---

## 4. Research Question

Can canonical persistence be removed from the synchronous WebSocket ingestion path such that large-message receive-loop occupancy is materially reduced while preserving existing collector correctness and persistence guarantees?

---

## 5. Hypothesis

Transferring completed persistence batches from the ingestion path to a separately owned, bounded single-writer persistence path will reduce the portion of receive-loop occupancy attributable to persistence while preserving canonical record integrity, failure visibility, reconnect behavior, and shutdown durability.

---

## 6. Candidate Intervention

The candidate F3 architecture is:

WebSocket
→ decode
→ parse
→ ingestion-owned active buffer
→ detach completed persistence batch
→ bounded persistence queue
→ single persistence worker
→ existing canonical storage layer

The intervention is based on ownership transfer.

The persistence worker and ingestion path must not concurrently mutate the same active record list.

The existing canonical schema and storage format are not redesigned by F3.

A single persistence worker is the initial experimental design. Multiple concurrent persistence workers are outside F3 v1 scope.

---

## 7. Required Correctness Invariants

F3 must preserve all of the following:

1. Count-triggered persistence remains functional.
2. Time-triggered persistence remains functional during feed silence.
3. A complete exchange message is not split merely to satisfy the nominal count threshold.
4. UTC-date grouping remains correct.
5. Existing immutable uniquely named Parquet-file semantics remain unchanged.
6. Successfully persisted groups are not duplicated following a later persistence failure.
7. Failed or unwritten accepted work is not silently discarded.
8. Persistence failures remain structural and cannot remain hidden as background-worker failures.
9. Pending accepted persistence work survives network reconnect.
10. Sequence tracking remains connection-session scoped.
11. Successful shutdown drains all accepted pending persistence work before reporting success.
12. Persistence failure during shutdown prevents a false successful shutdown.
13. Persistence-queue capacity is finite.
14. Queue saturation produces explicit backpressure rather than silent record dropping or unbounded memory growth.
15. Offline tests do not touch production canonical storage.
16. Existing applicable pre-F3 regression suites continue to pass.

---

## 8. Gate 1 — Correctness

F3 cannot proceed to production performance evaluation until the candidate architecture passes offline correctness testing.

Testing must directly exercise the production code path rather than validate a parallel reimplementation.

At minimum, Gate 1 must test:

- count-triggered persistence;
- timeout-triggered persistence during feed silence;
- correct trade/depth routing;
- complete-message batching behavior;
- successful persistence;
- persistence failure propagation;
- partial persistence failure behavior;
- network closure and reconnect;
- pending-work survival across reconnect;
- sequence-session reset behavior;
- task cancellation;
- successful shutdown drain;
- shutdown persistence failure;
- bounded queue behavior;
- deliberate queue saturation/backpressure;
- no silent loss under slow persistence;
- no duplicate persistence after recoverable partial failure;
- isolation from production canonical storage;
- applicable existing regression suites.

Any silent data loss, silent persistence failure, duplicate persistence caused by the intervention, unbounded queue growth, undefined saturation behavior, or false successful shutdown is a Gate-1 failure.

A receive-loop speed improvement cannot override a Gate-1 correctness failure.

---

## 9. Gate 2 — Performance

Gate 2 begins only after Gate 1 passes.

The F3 candidate must be instrumented so the revised architecture can distinguish at least:

- receive/decode time;
- decode/parse time;
- parse/buffer-or-batch-transfer time;
- ingestion-path handoff time;
- persistence-queue wait time;
- persistence-worker execution time;
- persistence completion/acknowledgement;
- queue depth or equivalent backlog state;
- explicit backpressure intervals.

The primary performance criterion is structural:

Persistence of a successfully detached batch must no longer occupy the WebSocket ingestion path for the duration of that persistence operation under normal queue capacity.

The experiment must measure the magnitude of any improvement rather than assume a percentage or absolute latency target in advance.

No arbitrary target such as "50% faster" or "under one second" is frozen in F3 v1 because the existing evidence does not justify such a threshold.

---

## 10. F2 Comparison Boundary

F2 remains the immutable baseline evidence.

F3 must not modify the historical F2 sample, event definition, stop condition, measurements, or validated finding.

Relevant F2 reference measurements include:

- n = 20 qualifying events;
- BTC-USD n = 10;
- ETH-USD n = 10;
- BTC median loop gap = 6941.452 ms;
- ETH median loop gap = 3305.617 ms;
- synchronous flush approximately 67% of median observed loop-gap duration;
- rows versus synchronous flush duration r = 0.998312;
- rows versus total loop-gap duration r = 0.998250;
- maximum timing-decomposition closure error = 0.000000 ms.

F3 may compare new measurements against F2, but it may not retroactively redefine F2.

---

## 11. Backpressure Requirement

Moving persistence off the ingestion path must not merely transform synchronous blocking into uncontrolled memory accumulation.

The queue must therefore be bounded.

If persistence cannot keep pace with ingestion, the system must enter an explicit measurable backpressure state rather than:

- silently dropping accepted records;
- allowing unlimited queue growth;
- hiding persistence failure;
- falsely reporting normal operation.

The exact queue capacity is an implementation parameter to be selected and documented before production validation. Its value is not inferred by this methodology freeze.

---

## 12. Failure Semantics

F3 must fail closed.

A background persistence exception must become visible to the owning collector lifecycle and must not permit the collector to continue indefinitely as though persistence were healthy.

Shutdown must distinguish:

- all accepted work durably persisted; versus
- persistence failed or accepted work could not be drained.

Only the first state may be reported as a successful shutdown.

---

## 13. Scope Boundaries

F3 v1 does not establish or test:

- physical disk I/O as the isolated F2 bottleneck;
- Coinbase or network latency as the cause of F2 loop gaps;
- trading edge;
- profitability;
- execution quality;
- fills or slippage;
- second-exchange behavior;
- a new canonical market-data schema;
- a new storage format;
- multiple persistence workers;
- distributed persistence;
- elimination of every collector loop gap.

F3 concerns the collector's local ingestion/persistence architecture.

---

## 14. Interpretation Rules

A Gate-1 correctness failure means the candidate architecture fails F3 regardless of apparent performance improvement.

A Gate-1 pass alone does not establish a performance improvement.

A Gate-2 reduction in ingestion-path occupancy does not establish physical disk performance, network performance, trading performance, or economic value.

If persistence time is moved off the ingestion path but queue backlog grows without bound or correctness guarantees weaken, F3 fails.

Negative or inconclusive results must be preserved as evidence and must not be rewritten as success.

---

## 15. Frozen Sequence

The experiment sequence is:

1. Freeze F3 v1 methodology.
2. Preserve and commit the methodology before production-code changes.
3. Design the minimum ownership-transfer implementation.
4. Add or adapt Gate-1 tests.
5. Run applicable existing regression suites.
6. Resolve correctness failures without changing the research question to fit the implementation.
7. Pass Gate 1.
8. Add/validate F3 performance telemetry.
9. Perform bounded validation before production deployment.
10. Run production Gate-2 observation under a separately frozen observation protocol.
11. Analyze the frozen evidence.
12. Record the result whether positive, negative, or inconclusive.

Changes to this methodology after implementation begins must be explicitly versioned and justified rather than silently edited in place.

---

## 15. F3 v1 Implementation Parameter — Persistence Queue Capacity

Selected before production validation:

- `F3_PERSISTENCE_QUEUE_CAPACITY = 2`
- Unit: detached persistence batches waiting in the bounded queue.
- This is an experimental implementation parameter, not an empirically optimized production value.
- One persistence batch may additionally be actively processed by the single persistence worker.
- When both queue slots are occupied, the next ingestion-thread submission blocks until capacity becomes available or worker failure becomes visible.
- The purpose of this deliberately small capacity is limited burst absorption while causing sustained persistence-throughput mismatch to become explicit backpressure rather than being hidden behind a large backlog.
- Queue capacity does not impose a fixed record-count or byte-memory ceiling because complete-message batching is preserved and one detached batch may contain substantially more than the nominal 200-record trigger.
- Production validation must measure queue wait/backlog/backpressure behavior before any later capacity change is considered.
- Any later capacity change requires explicit documentation and must not be presented as if it were part of the original frozen F3 v1 validation.

This selection fills the implementation parameter explicitly reserved by Section 11. It does not change the F3 hypothesis, correctness invariants, Gate-1 failure conditions, or performance-success criterion.

---

## 16. Gate-2 Observation Protocol Addendum v1 — Observer-Overhead Boundary

**Added:** 2026-09-25
**Timing:** After Gate-1 closure and during Gate-2 instrumentation validation, before production Gate-2 evidence collection.

### Reason for addendum

Gate-2 instrumentation review identified a measurement confound that was not explicitly defined in the pre-implementation methodology freeze.

The F3 persistence worker captures `worker_end_ns` immediately after canonical batch persistence completes and before the completion-observation callback executes.

The completion-observation callback then executes synchronously on the same persistence-worker thread before that worker can dequeue the next persistence batch.

Because the production observation callback may itself cause bounded telemetry serialization and JSONL persistence, observer execution can delay the worker's return to its next dequeue.

This addendum does not change the F3 hypothesis, Gate-1 correctness requirements, queue-capacity parameter, or Gate-2 structural success criterion. It freezes how Gate-2 measurements must be interpreted before production evidence is collected.

### Measurement boundaries

For Gate-2 analysis:

- `worker_persist_ms` measures canonical persistence execution from `worker_start_ns` through `worker_end_ns`.
- Completion-observer execution occurs after `worker_end_ns` and is therefore excluded from that batch's `worker_persist_ms`.
- `submit_block_ms` measures time spent by the ingestion-side submission path between submission start and successful bounded-queue acceptance. It is the direct measurement of ingestion-path blocking at persistence handoff.
- `submit_block_ms` ends before the handoff-observation callback executes and therefore excludes handoff-observer callback duration. However, `submit()` returns only after that synchronous observation callback completes, so total `_handoff_if_due()` occupancy and its returned post-submit timing anchor may include handoff-observer serialization or telemetry-write overhead. F2-style loop-gap measurements that use that returned anchor must not treat this observer work as canonical persistence or queue backpressure.
- Handoff and completion observations may originate from different threads and are serialized through a shared observation lock so observer ordering and attribution remain deterministic. Consequently, one thread's observation path may wait for the other thread's already-running observation callback to finish. This cross-thread observer-lock wait occurs after queue acceptance for the handoff path and is therefore excluded from `submit_block_ms`, but it may increase total `submit()` / `_handoff_if_due()` occupancy or delay worker progress after canonical persistence has completed. Such wait time is instrumentation overhead and must not be attributed to canonical persistence or persistence-queue backpressure.
- `queue_wait_after_accept_ms` measures accepted-to-worker-start residence when an accepted timestamp is available.
- `queue_wait_after_accept_ms` must not be interpreted as pure canonical-persistence pressure because it may include observer-callback execution associated with earlier completed batches.
- Queue-depth, backlog, and saturation observations describe the behavior of the instrumented production system and may likewise reflect observer overhead.
- Correlation between backlog and persistence duration alone must not be interpreted as proof that canonical persistence exclusively caused that backlog.

### Observer-overhead requirement

Gate-2 instrumentation must measure completion-observer callback duration separately so its magnitude can be distinguished from canonical persistence execution.

No arbitrary observer-overhead success threshold is frozen in advance.

Observer overhead must be reported as an observational component rather than silently merged into canonical persistence duration.

### Previous-observer provenance semantics

Gate-2 observation records may carry:

- `previous_observer_callback_ms`
- `previous_observer_event_type`
- `previous_observer_batch_id`

These fields describe the previous **completed serialized observer callback** according to the shared observation-lock order.

For the first completed observation sequence, all three previous-observer fields are `None`.

The fields do not assert that the referenced observation was the previous event generated by the system, the previous batch, a causal predecessor, or the immediately preceding persistence operation. Handoff and completion observations originate from different threads, so observer-lock acquisition determines their serialized observation order.

`previous_observer_callback_ms` measures the duration of that previous callback transaction. It must be interpreted as observer-instrumentation overhead, not canonical persistence duration or persistence-queue backpressure.

A callback that raises an exception but reaches observer measurement completion remains a completed serialized observer callback for provenance purposes. Observation exceptions remain non-structural.

The current callback's duration cannot be included truthfully in its own emitted observation because that duration is not known until the callback returns. Its measurement therefore becomes available to the next serialized observation. If no later observation occurs, the final completed callback remains recoverable through the worker's `last_observer_measurement` state.

Provenance fields are attached to a copied observation record; the source observation record is not mutated.

### Architecture constraint

F3 v1 will not add a second telemetry worker, telemetry queue, or other asynchronous observation subsystem solely to remove this measurement confound before the first Gate-2 production observation.

Adding such machinery would alter the architecture being evaluated and introduce additional queueing, ownership, shutdown, and failure semantics.

The initial Gate-2 design will instead preserve the existing single persistence worker and explicitly measure observer overhead.

Observation callbacks are required to remain bounded in execution. Exception-throwing callbacks remain non-structural, but an indefinitely blocking callback cannot be neutralized by exception handling. Because handoff and completion observations share the observation-serialization lock, such a hang could block observation progress across threads and may indirectly delay worker `task_done()` and shutdown drain completion. This is an accepted instrumentation risk for the initial Gate-2 design and must not be misclassified as canonical persistence failure.

### Interpretation rule

A Gate-2 result must distinguish:

1. canonical persistence execution;
2. ingestion-side handoff/backpressure;
3. accepted-batch queue residence;
4. observer overhead;
5. observed queue/backlog state.

Production evidence must not present accepted-batch queue residence or backlog as if it were generated exclusively by canonical persistence unless the evidence independently supports that conclusion.

This addendum was frozen before production Gate-2 evidence collection. It is a measurement-boundary clarification discovered during instrumentation validation, not a retroactive modification of collected results.
