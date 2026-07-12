# Market Data Platform — Implementation Roadmap

Status: Phase 0 (foundation) in progress. No collector exists yet.

---

## PART 1 — ARCHITECTURE (Frozen Principles)

These do not change based on which exchange, storage format, or
programming pattern is used today. If today's implementation
changes, this section should not need to change.

### Canonical Asset
The validated event history, losslessly normalized into the
canonical event schema, is the canonical asset of this platform —
independent of storage format. It is the only artifact that cannot be recreated once
lost. Every reconstructed order book state, trade view, research
dataset, and future analysis layer is a downstream, always-
reproducible consumer of this one asset. Today's implementation
happens to use Parquet for this storage; the canonical asset is the
validated event history itself, not the file format it currently
lives in.

### Canonical Asset — Precise Definition

The canonical asset is the minimal, lossless representation of
every observable fact reported by the exchange that cannot be
independently re-derived once the moment has passed. This is the
information-theoretic basis for every other principle in this
section: a field, structure, or value is required in the canonical
schema exactly when its omission would make some real, transmitted
fact permanently unrecoverable — never because of exchange-specific
naming or transport convention alone. This definition governs
schema design, precision decisions, and adapter responsibilities
uniformly, regardless of which exchange is being adapted.

### Architectural Invariant

Every downstream artifact must be reproducible solely from the
canonical event history. No downstream artifact may become an
independent source of truth. If a future dataset cannot be
recreated from the canonical event history, either that dataset
shouldn't exist in that form, or the canonical event history is
missing information that should have been captured.

### Governing Design Principle

Favor irreversible data collection over irreversible data
transformation. The raw event history cannot be recollected once a
moment passes uncaptured. Everything built from it can always be
rebuilt. This single principle explains why the canonical asset is
the validated, normalized event history rather than any
reconstructed or derived representation of it.

### Derived Data Is Disposable

Because every downstream artifact is reproducible from the
canonical event history, no derived artifact — reconstructed order
books, research datasets, analysis outputs — requires the same
care, backup discipline, or reluctance to delete that the canonical
event history itself demands. A flawed reconstruction attempt can
be deleted and rebuilt freely. Only the canonical event history
requires the operational rigor of something irreplaceable.

### Scope

This platform is venue-agnostic, shared infrastructure — not part
of any single Domain. The Crypto Domain (domains/crypto/) is its
first consumer, not its owner. Future market domains, whatever they
turn out to be, are expected to plug into this same platform via
new adapters, without requiring changes to validation,
normalization, storage, or gap-detection logic.

---

## PART 2 — CURRENT IMPLEMENTATION PLAN (Today's Engineering Decisions)

Everything in this section is today's choice, not architectural
law. It should be revised freely as evidence justifies — without
needing to revisit Part 1.

### Phase 0 — Single-Exchange Foundation (CURRENT)

**Objective:** Prove the full pipeline — connect, capture, validate,
normalize, store immutably, detect gaps, survive disconnects — for
one exchange and a small number of liquid pairs.

**Current implementation choice:** Binance, BTC-USDT and ETH-USDT.
Chosen for deepest liquidity and most third-party precedent for
this kind of collector — not an architectural requirement, subject
to change if evidence says otherwise.

**Why this phase exists:** Every future exchange adapter, Domain,
and research question depends on this foundation being solid.
Getting it right once avoids rebuilding it under every future
adapter.

**Dependencies:** None. First engineering milestone.

**Success criteria — Functional:**
- Live WebSocket connection to the exchange, maintained correctly.
- Every event (add/modify/cancel/trade) is validated before
  storage; malformed events are rejected and logged separately,
  never silently dropped.
- Events are normalized into the canonical event schema (today's
  implementation: timestamp_received, exchange_timestamp,
  sequence_number, event_type, side, price, size) before storage.
- Raw events are written to immutable, partitioned storage (today's
  implementation: date-partitioned Parquet) and never modified
  after being written.
- Sequence-number gap detection correctly identifies and logs any
  missing message range.

**Success criteria — Operational:**
- The collector automatically reconnects on drop and resumes
  logging without manual intervention.
- A deliberately forced disconnect test confirms the exact gap is
  logged correctly on reconnect — not merely assumed to work.
- The collector demonstrates sustained, unattended operation over
  a sufficiently long validation period, with the session log and
  gap log accurately reflecting what actually happened during that
  window. (Today's specific acceptance threshold — e.g. 72 hours —
  belongs in an implementation checklist, not this roadmap.)

**Risks:**
- Exchange-specific WebSocket message edge cases not caught during
  initial design.
- Reconnection logic that appears correct in short tests but fails
  under a real, extended network interruption.
- Storage growth outpacing rotation/partition assumptions before
  they're proven correct at real volume.

**Explicitly NOT built in this phase:**
- No order book reconstruction.
- No OBI, spread, or any derived metric.
- No second exchange or adapter.
- No research dataset builder.
- No Program or Domain code reads from this pipeline yet.

**Evidence required to move to Phase 1:** Sustained unattended
operation with correct gap tracking and successful reconnection,
including a deliberately forced disconnect test — not assumed
correct, demonstrated correct.

---

### Phase 1 — Reconstruction Layer (NOT STARTED, BLOCKED ON PHASE 0)

**Objective:** Build reconstruction of order book state from the
canonical event history — the first downstream consumer proving
the architectural invariant in practice, not just in principle.
This roadmap does not prescribe one reconstruction representation
(point-in-time snapshots, replay, intervals, or otherwise) — that
is an implementation decision for whoever builds this phase,
informed by what Phase 2's research question actually needs.

**Why this phase exists:** This is the first real test of the
invariant. If reconstruction cannot be built cleanly from Phase 0's
raw store alone, that's evidence the raw schema is missing
something — worth discovering here, before anything else depends
on it.

**Dependencies:** Phase 0 complete, with real accumulated history
to reconstruct against.

**Success criteria:**
- Reconstruction logic produces verifiably correct order book state,
  checked against independent ground truth where available (e.g.
  the exchange's own periodic snapshot endpoint, if one exists) —
  not validated only against its own internal consistency.
- Reconstruction is deterministic: re-running it against the same
  raw files produces identical results.
- No modification to any Phase 0 raw file occurs during this phase.

**Risks:** Reconstruction logic silently producing plausible-but-
wrong book states if only checked against itself.

**Explicitly NOT built in this phase:**
- No OBI or other research-specific metric.
- No cross-exchange comparison.
- No Program or Domain-level research questions asked yet.

**Evidence required to move to Phase 2:** Reconstruction verified
against independent ground truth.

---

### Phase 2 — First Research Question (NOT STARTED, BLOCKED ON PHASE 1)

**Objective:** Ask one real research question using reconstructed
data, testing whether this pipeline produces genuine research
value, not just correct infrastructure.

**Current implementation candidate:** OBI, given Program B's proven
methodology on Polymarket — a candidate, not a commitment. This
phase itself should confirm or challenge whether OBI is actually
the right first question for crypto order books.

**Why this phase exists:** Infrastructure that's correct but never
used to answer a real question hasn't earned its keep. This
directly mirrors Program B's own discipline: build, then genuinely
use, before building more.

**Dependencies:** Phase 1 complete, with enough accumulated history
for a first-pass finding to be meaningful (weeks, not days, per
Program B's own experience).

**Success criteria:** A real, honestly-hedged first checkpoint,
filed the same way Program B's findings have been — explicit
sample-size caveats, no overclaiming, "inconclusive" treated as a
valid, honest outcome.

**Risks:** Premature conclusions from insufficient history — the
same risk already named and actively avoided in every Program B
checkpoint this project has produced.

**Explicitly NOT built in this phase:** No second exchange, no
execution logic of any kind, no automation beyond answering this
one question.

**Evidence required to move to Phase 3:** A genuine first finding,
or an honest "inconclusive, needs more data" result — either is
valid evidence.

---

### Phase 3 — Second Adapter (NOT STARTED, BLOCKED ON PHASE 2)

**Objective:** Add a second exchange adapter to prove the
extensibility designed into Phase 0.

**Why this phase depends on Phase 2:** Cross-exchange infrastructure should be justified by demonstrated research needs rather than built speculatively. Phase 2 provides that evidence.

**Why this phase exists:** This is the real test of "adding a new
venue should feel like plugging in an adapter." If it doesn't,
Phase 0's architecture wasn't as venue-agnostic as intended — real,
valuable evidence to have before a third or fourth adapter is
attempted.

**Dependencies:** Phase 2 producing a real reason to want
cross-exchange data.

**Success criteria:** Second adapter built without modifying the
shared validation, normalization, storage, or gap-detection layers
— only a new adapter file added.

**Explicitly NOT built in this phase:** No cross-market research
yet, no third exchange until this one proves the pattern holds.

**Evidence required to move further:** Confirmed adapter-only
extension with zero shared-layer changes, or an honest account of
what shared-layer assumption broke and why.

---

## What This Roadmap Deliberately Does Not Commit To

- Which exchange comes second — decided later, with evidence.
- Which research question comes first in Phase 2 — OBI is a
  candidate, not a commitment.
- Any timeline beyond Phase 0.
- That this platform will only ever serve the Crypto Domain — it is
  intentionally venue-agnostic infrastructure.
- Any specific storage format, field name, or exchange choice as
  permanent — those live in Part 2 and may change without touching
  Part 1.
