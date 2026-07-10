# Liquid Research
## Architecture Specification

Version: 1.0
Status: Canonical
Last Updated: 2026-07-09

This document is the authoritative architectural reference for
Liquid Research. Architectural decisions should be made here before
implementation whenever practical. When implementation and this
document diverge, either the implementation should be updated or
this specification should be revised through a deliberate,
versioned change.

---

## 1. Philosophy

Liquid Research exists to discover, validate, and operationalize
repeatable, monetizable trading edges — not to accumulate interesting
indicators or infrastructure for its own sake. Every architectural
decision in this document should be evaluated against whether it
increases the probability of finding a real edge, not against
whether it is elegant or exhaustive.

This project follows an evidence-first engineering philosophy:
prefer better evidence over more variables, avoid infrastructure
ahead of demonstrated need, and let real implementation experience —
not speculation — drive architectural revision. See zHANDOFF.md's
Stable Principles for the full governing philosophy; this document
applies that philosophy specifically to system architecture.

---

## Scope
This document defines the architectural responsibilities,
boundaries, and data contracts of Liquid Research.
It intentionally does not specify research methodologies, trading
strategies, statistical models, or implementation details except
where necessary to explain architectural boundaries.

## Architecture Hierarchy

The project is organized into four complementary layers:

1. Philosophy
   Defines engineering values and decision-making principles
   (`zHANDOFF.md`).

2. Architecture
   Defines responsibilities, boundaries, and contracts
   (`zARCHITECTURE.md`).

3. Roadmap
   Defines priorities, planned work, and future initiatives
   (`zROADMAP.md`).

4. Implementation
   Source code implementing the architecture.

## Non-Goal
This document does not prescribe the internal implementation
architecture of a Domain. Domains remain free to evolve internally
provided they preserve their canonical interface and documented data
contract.

---
## 2. System Architecture — Domain/Program Separation

Liquid Research is organized around two distinct roles.

**Domains** own market selection. A Domain understands one category
of financial market — its data sources, its instruments, what makes
an instrument worth researching — and is responsible for producing a
canonical list of currently-approved instruments.

**Programs** consume a Domain's canonical output to answer a specific
research question. Programs never perform their own market selection,
never re-filter a Domain's decisions, and never read a Domain's raw
internal files as a required input.

This separation exists so that market-selection logic is written
exactly once, in exactly one place, regardless of how many downstream
research programs eventually depend on it.

---

## 3. Domains

A **Domain** represents a distinct category of financial market with
its own data sources, instruments, and internal logic for determining
which instruments are worth researching.

Today, exactly one Domain exists: **Prediction Markets** (Polymarket).
Crypto, Futures, and Equities are named as future possibilities in
the project's long-term vision, but none are designed or implemented.
Nothing in this document should be read as a commitment about how
they will work — see Section 7, Architectural Questions for Future Domains.

A Domain owns:
- Its own data collection
- Its own filtering logic (what counts as "approved" or research-worthy)
- Its own scoring/evaluation logic
- Translating its internal representation into its canonical output

---

## 4. Programs

A Program answers a specific research question using one or more
Domains' canonical output.

Today:
- **Program A** is the current implementation of the Prediction
  Markets Domain's producer. There is no separate "Domain layer"
  distinct from Program A yet, because only one Domain exists — but
  the Domain role and the Program A implementation are conceptually
  separate, and the architecture does not assume they remain
  permanently identical.
- **Program B** (Market Microstructure Research) is a consumer of
  the Prediction Markets Domain's canonical output.
- **Program C** (future — Entry/Execution Research) will be the same
  kind of consumer.

Program identity is an implementation detail. The Domain/Program
architecture does not depend on any specific program's name, module
structure, or internal organization remaining fixed over time.

---

## 5. Data Contracts
The canonical output is both the public interface and the canonical
data contract of a Domain. Downstream Programs interact with a
Domain exclusively through this published contract. Everything else
produced by a Domain—including snapshots, scanner runs, logs,
intermediate calculations, and implementation-specific files—is
considered an internal implementation detail. Internal
implementation may change freely provided the canonical output
contract remains intact.

**Canonical output definition:** The canonical output represents the
authoritative set of instruments approved by the Domain for research
at the time it was generated. Downstream Programs should assume every
instrument in this file is eligible for analysis and should not
perform additional market-selection filtering.

**Publication identity:** Every canonical output carries a
`publication_id` — a unique identifier for the publication cycle
that produced it. This field is part of the universal publication
contract, not a Domain-specific extension: every Domain Publisher
is expected to generate one, since publication identity is a
property of the publishing process itself, not of any particular
Domain's internal data. `publication_id` allows downstream Programs
to correctly group or pair observations that originated from the
same publication cycle, without depending on filenames or
timestamps embedded in unrelated internal artifacts. This
architecture does not prescribe how a `publication_id` is generated
— only that it uniquely identifies one publication cycle. See the
Prediction Markets implementation below for today's concrete
approach.

### Interface Stability

Consumers should depend only on documented canonical fields and
their documented meanings. Internal implementation details —
including collectors, scanners, algorithms, storage layout,
intermediate files, and logging — may change freely without
constituting a breaking architectural change, provided the canonical
contract remains intact. Consumers should never infer behavior from undocumented fields or implementation details.

### Producer Responsibilities

A Domain producer is responsible for:
- Producing a complete canonical output.
- Ensuring every published instrument satisfies the Domain's
  approval criteria.
- Maintaining compatibility with the documented canonical schema.
- Publishing a coherent snapshot representing a single publication
  cycle.

These are architectural responsibilities, not implementation
details.

### Prediction Markets Domain — Current Canonical Output Implementation
**Producer:** Prediction Markets Domain (currently implemented by
Program A)
**File (current implementation):** `data/approved_markets/prediction_markets_latest.csv`
**`publication_id` generation (current implementation):** the
Prediction Markets Publisher generates this using the existing
`YYYYMMDD_HHMMSS` convention already used throughout the repository
(matching `scanner_run_*.csv` and `snapshot_*.csv` naming). This is
an implementation choice, not an architectural requirement — a
future Domain, or a future revision of this Domain's implementation,
may generate `publication_id` differently as long as it remains
unique per publication cycle.

**Schema — fully specified, this is what ships:**
| Field | Description |
|---|---|
| `publication_id` | Unique identifier for the publication cycle that produced this canonical output. || `resolution_id` | Maps to `market_id` / conditionId. Used for resolution and historical tracking. |
| `instrument_name` | Maps to `question`. Human-readable label. |
| `tradeability_score` | Prediction Markets' scanner-computed evaluation score. Not assumed comparable across future Domains. |
| `category` | Prediction Markets' classifier output. |
| `liquidity` | Prediction Markets' scanner-computed liquidity figure. |
| `volume_24h` | Prediction Markets' scanner-computed 24-hour volume. |
| `spread_pct` | Prediction Markets' scanner-computed spread percentage. |
| `spread_label` | Prediction Markets' scanner-computed spread quality label. |
| `days_left` | Days remaining until the instrument's resolution date. |

**Consumers today:** Program B reads this file directly, with zero
joins and zero access to Prediction Markets' internal diagnostic
files as a required input.

### Diagnostic Artifacts

Diagnostic artifacts are a Domain's raw, internal collection and
scoring history. They remain fully preserved and available for
debugging, auditing, or genuinely domain-specific investigation —
they are never a required input for any Program's normal operation.

For Prediction Markets, the current diagnostic artifacts are the
collector's market snapshots and the scanner's timestamped scoring
runs. Their existence, format, and retention are implementation
details of the Prediction Markets Domain, not part of this
architecture's contract.

---

## 6. Engineering Principles

These are architecture-specific applications of the broader
engineering philosophy in `zHANDOFF.md`. See that document for the
complete set (Research Integrity Rules, Read-Before-Patch, etc.).

- Domains own market selection; Programs never duplicate it.
- One producer, many consumers, per Domain.
- Downstream research never writes back into a canonical output.
- Internal artifacts stay available but are never a required input.
- Prefer real implementation evidence over speculative multi-domain
  design — build one Domain concretely, generalize only once a
  second Domain provides real evidence.
- Stable interfaces are preferred over stable implementations.
  Internal implementation may evolve freely as long as the canonical
  output contract remains unchanged.
- Prefer documented contracts over implicit behavior.

---

## 7. Architectural Questions for Future Domains

These are explicitly unresolved. They should not be treated as
implied commitments — they are questions to answer with evidence
once a second Domain actually exists.

- Whether `instrument_id`, `resolution_id`, `instrument_name`, and
  `tradeability_score` as named, typed fields would transfer cleanly
  to a second Domain, or whether the *concepts* transfer but the
  concrete shape needs to change.
- Whether a second Domain needs a `domain` column, a separate
  namespace, or something else entirely to let a Program distinguish
  which Domain a row came from, if that's ever needed.
- Whether `tradeability_score` should ever be comparable across
  Domains, and if so, what normalization that would require.
- Whether the current canonical-output file convention fits a Domain
  with a different update cadence than Prediction Markets' daily
  cycle.
- Any architectural implications from an unreviewed backlog of
  external research (bookmarked material on crypto, market
  microstructure, quantitative trading, and system design) not yet
  incorporated into this document.

**Revision trigger:** Sections 3-5 (Domain/Program specifics, the
Prediction Markets schema) get revisited when a second Domain is
actually implemented, using real evidence from that implementation.
Sections 2 and 6 (the durable Domain/Program principles) only change
if real implementation experience shows one of them doesn't actually
hold — which would itself be a significant, deliberate finding.

---

## Architecture Decisions

### ADR-001
**Decision:** Domains own market selection.
**Reason:** Separates instrument selection from downstream research
and prevents duplicate filtering logic across every current and
future consumer.
**Status:** Accepted (v1)

---

### ADR-002
**Decision:** Programs consume canonical outputs only, never raw
internal Domain files, never their own joins.
**Reason:** Creates a one-producer-many-consumers architecture and
eliminates the exact duplication risk identified when redesigning
Program B's market-loading logic — each consumer independently
reconstructing the same join between scanner output and snapshot
data.
**Status:** Accepted (v1)

---

### ADR-003
**Decision:** The canonical schema is fully specified for Prediction
Markets only. No field names, types, or structure are assumed to
generalize to a future second Domain without validation.
**Reason:** Avoids designing for hypothetical domains ahead of real
implementation evidence, consistent with the project's broader
"prefer better evidence over more variables" principle.
**Status:** Accepted (v1)

---

### ADR-004
**Decision:** Domain and Program identity are decoupled from specific
module names. Program A is described as the current implementation
of the Prediction Markets Domain producer, not as synonymous with it.
**Reason:** Prevents this document from becoming outdated if a
Domain's producer is later refactored, renamed, or restructured.
**Status:** Accepted (v1)

---

### ADR-005
**Decision:** Each Domain exposes exactly one canonical output
representing the complete approved research universe for a single
publication cycle.
**Reason:** Establishes a stable producer/consumer boundary,
eliminates duplicate market-selection logic, and allows internal
implementation to evolve independently of downstream Programs.
**Status:** Accepted (v1)
---
### ADR-006
**Decision:** Every canonical output includes a `publication_id`, a
unique identifier for the publication cycle that produced it. This
field belongs to the universal publication contract, not to any
individual Domain's schema — publication identity is a property of
the publishing process itself.
**Reason:** A canonical output is published to a fixed location and
overwritten on each publication cycle, per the architecture's own
"single publication cycle" definition (ADR-005). This design
intentionally keeps consumers pointed at one stable location rather
than requiring them to track timestamped files — but it also means
a canonical output, on its own, carries no way to distinguish one
publication cycle from the next. Without an explicit identity, the
question "which cycle produced this data" cannot be answered from
the canonical output alone. `publication_id` closes this gap as a
first-class part of the contract, independent of any particular
consumer's needs. This gap was surfaced during Program B's
implementation, but the decision reflects a structural property of
canonical outputs generally, not a Program B-specific requirement.
**Status:** Accepted (v1)
---
## Version History

**v1.0 — 2026-07-09** — Initial architecture specification. Domain/
Program separation established. Prediction Markets canonical schema
fully specified. Crypto/Futures/Equities explicitly marked as open
architectural questions, not commitments.