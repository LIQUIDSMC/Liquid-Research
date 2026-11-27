# R03-MC03 — Synthetic Cumulative Verification Reservation Acceptance Criteria

Status: DESIGN ONLY / NOT IMPLEMENTED / NOT APPROVED

## Purpose and ownership

This document defines LRS3-owned, crypto-specific acceptance criteria for a
possible synthetic-only cumulative verification-read reservation prototype.
It does not authorize implementation, historical source reads, inventory,
verification, acquisition, deployment, or changes to shared L1 infrastructure.

The applicable operating design is recorded in
`L2_DOMAINS/crypto/zROADMAP.md` under R03-MC03.

A controller requiring shared L1 acquisition, validation, storage, or
orchestration changes is a concrete dependency for the shared-infrastructure
owner. A separate LRS3 research prototype must remain isolated from
production entry points and historical source paths.

## Accounting model

A future controller must accept an independently approved cumulative
requested-read allowance and independently approved per-attempt allowance.
Neither allowance is approved by this document.

Before launching an attempt, the controller must durably reserve its full
per-attempt allowance against the cumulative allowance.

The admission condition is:

    existing_reserved_bytes + new_attempt_allowance <= cumulative_allowance

The controller must reject missing, negative, nonintegral, overflowing,
inconsistent, or otherwise invalid budget inputs and ledger states.

A reservation is charged in full regardless of actual requested bytes.
There are no automatic refunds for unused allowances or failed attempts.

The existing 80 MiB per-partition requested-read ceiling and its
28-attempt mathematical product are illustrative historical design
references, not approved cumulative operating limits.

Requested `os.pread` bytes are not equivalent to physical disk I/O.
Hashing, repeated reads, acquisition, and elapsed-time budgets require
separate safeguards and approval.

## Atomic admission and concurrency

Only one controller operation may evaluate and mutate the cumulative
reservation ledger at a time.

A future implementation must demonstrate exclusive coordination across
independent processes, not merely threads within one process.

Under the exclusive coordination mechanism, it must:

1. Validate ledger integrity and all previous reservations.
2. Verify that the complete new allowance fits the remaining budget.
3. Create a unique, non-reusable attempt identity.
4. Durably publish the full reservation and updated cumulative accounting.
5. Release coordination only after the reservation is durable.

A worker must never launch before successful durable reservation.
If publication or durability cannot be established, launch is prohibited.

The design must explicitly address filesystem crash consistency,
directory synchronization, interrupted writes, and stale process locks.
An implementation must not assume that a file lock alone makes a
multi-file update atomic.

## Failure and recovery

All completed, failed, killed, timed-out, interrupted, and uncertain
attempts retain their entire reserved allowance.

On restart, the controller must reconcile all durable reservation
records before admitting additional work.

Missing records, duplicate identities, contradictory totals, corrupt
content, unrecognized schema versions, or ambiguous durability must
block admission until independently reconciled.

The controller must not infer a refund from a missing worker completion
record, a process exit code, a timeout, or an interrupted launch.

A reservation committed immediately before a crash remains charged even
if the corresponding worker never started.

The controller must preserve evidence of failed or uncertain operations.
Recovery and administrative correction procedures require separate
review and must never silently rewrite or erase historical reservations.

## Retry policy

Retries are distinct attempts with distinct identities.

A retry requires explicit authorization and a new full reservation
against the remaining cumulative allowance.

A failed or interrupted attempt does not replenish available budget.
No automatic retry or automatic budget reset is permitted.

## Synthetic acceptance matrix

All tests must use fabricated inputs and isolated temporary storage.
No test may open historical market-data source paths or call a
production acquisition or verification launcher.

| ID | Required synthetic demonstration |
| --- | --- |
| S01 | Valid first reservation is durable before launch authorization. |
| S02 | Exact remaining-budget reservation succeeds; one byte beyond fails. |
| S03 | Invalid, negative, fractional, missing, and overflow-like values fail closed. |
| S04 | Two competing processes cannot both spend the same remaining allowance. |
| S05 | Duplicate attempt identity is rejected without changing prior accounting. |
| S06 | Failure before durable reservation prohibits launch. |
| S07 | Crash after durable reservation but before launch retains the full charge. |
| S08 | Crash or timeout during work retains the full charge. |
| S09 | Interrupted ledger publication or uncertain synchronization blocks admission. |
| S10 | Missing, corrupt, contradictory, or unsupported ledger records block admission. |
| S11 | Restart reconstructs charged reservations without refunds or duplicate admission. |
| S12 | Retry without separate authorization fails; authorized retry consumes new budget. |
| S13 | Completion reports cannot increase remaining budget or overwrite reservations. |
| S14 | Exhaustion blocks subsequent attempts without invoking any worker. |
| S15 | Test fixtures and entry points remain synthetic-only and outside shared L1. |

Acceptance requires deterministic assertions for ledger state, durable
records, launch/no-launch decisions, and retained failure evidence.
Fault injection must cover critical write, synchronization, admission,
launch, and recovery boundaries.

Passing synthetic tests would establish only the behavior tested in the
synthetic environment. It would not prove power-loss durability across
all filesystems, historical-data safety, physical-I/O limits, or
production readiness.

## Unresolved approval gates

Before any operational use, independently establish and approve:

- Numerical cumulative and per-attempt verification-read allowances.
- Repeated-read and physical-I/O safeguards.
- Full-stage elapsed-time and storage/retention ceilings.
- Ledger storage location, permissions, durability guarantees, and recovery.
- Shared-infrastructure implementation ownership and integration boundaries.
- Independent review of implementation, synthetic tests, and failure evidence.
- Separate authorization for every historical operation.

R03-MC03, MC07, MC09, and MC10 remain OPEN.
The exploratory study remains DRAFT / UNFROZEN.
Candidate D D0 remains BLOCKED.
Sealed H2, historical execution, acquisition, production transfer, and
broader pilot remain outside this document's authorization.
