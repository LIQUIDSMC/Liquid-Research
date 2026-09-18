# Liquid Research
## Architecture Specification

Version: 1.1
Status: Canonical
Last Updated: 2026-09-17

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

## Governance and Implementation Hierarchy

Project authority and implementation are separated into four complementary levels:

1. **Operating principles** — `zHANDOFF.md`
   Defines research integrity, engineering discipline, documentation rules,
   and project-wide operating standards.

2. **Architecture** — `zARCHITECTURE.md`
   Defines ownership, responsibilities, boundaries, and stable contracts.

3. **Roadmap** — `zROADMAP.md`
   Defines current priorities, active systems, and planned work.

4. **Implementation**
   Source code, tests, runtime infrastructure, and research artifacts
   implementing those decisions.

This governance hierarchy is distinct from the repository's physical
**L0-L4 architecture**, described below.

## Non-Goal
This document does not prescribe the internal implementation
architecture of a Domain. Domains remain free to evolve internally
provided they preserve their canonical interface and documented data
contract.

---
## 2. System Architecture — L0-L4 Ownership Model

Liquid Research uses an ownership-based L0-L4 repository architecture:

- **L0_PLATFORM** — governance, canonical architecture, roadmap, and
  project-wide operating authority.
- **L1_CORE** — shared engineering infrastructure, orchestration, and
  venue-agnostic platform services.
- **L2_DOMAINS** — market-domain acquisition, selection, publication,
  and domain-specific context.
- **L3_RESEARCH_ENGINES** — independent research systems with isolated
  questions, methodology, implementation, and tests.
- **L4_KNOWLEDGE** — shared findings, hypotheses, open questions, and
  future research concepts.

The durable architectural principle established in v1.0 remains:
**market/domain ownership is separate from downstream research ownership.**

A Domain owns the logic required to understand and publish its market
universe. A Research Engine consumes documented upstream interfaces to
answer a specific research question. Research Engines should not silently
reconstruct or override a Domain's market-selection decisions.

The older term **Program** appears throughout historical records and ADRs.
For current architecture, **Research Engine** is the preferred term.

## 3. Domains

A **Domain** represents a market universe with its own data sources,
instruments, acquisition requirements, and domain-specific logic.

Current L2 domain ownership includes:

- **Prediction Markets** — owns prediction-market acquisition, selection,
  classification/resolution support, and canonical publication.
- **Crypto** — owns crypto-specific research context while shared
  venue-agnostic market-data infrastructure remains in `L1_CORE`.

The existence of multiple domains does not imply that every domain must
publish an identical schema or use identical internal architecture.
Generalization should follow implementation evidence rather than precede it.

## 4. Research Engines

A **Research Engine** answers a specific research question using documented
upstream data and contracts while maintaining its own methodology and
research state.

Current L3 research systems include:

- **Market Selection** — successor identity for the research role historically
  associated with Program A. Prediction Markets publication now belongs
  explicitly to `L2_DOMAINS/prediction_markets/`.
- **Market Microstructure** — successor identity for Program B; consumes the
  Prediction Markets canonical publication for order-book research.
- **Market Regime** — independent regime-research engine with explicit
  methodology freeze and supersession controls.
- **Wallet Intelligence** — retained L3 research area; expansion remains
  dependent on evidence and project priority.

Additional research concepts may remain parked in `L4_KNOWLEDGE` until they
justify implementation.

Historical references to Program A, Program B, Program C, or other lettered
program concepts should remain intact when they document the state or
decision that existed at that time.

## 5. Data Contracts
The canonical output is both the public interface and the canonical
data contract of a Domain. Downstream Research Engines interact with a
Domain exclusively through this published contract. Everything else
produced by a Domain—including snapshots, scanner runs, logs,
intermediate calculations, and implementation-specific files—is
considered an internal implementation detail. Internal
implementation may change freely provided the canonical output
contract remains intact.

**Canonical output definition:** The canonical output represents the
authoritative set of instruments approved by the Domain for research
at the time it was generated. Downstream Research Engines should assume every
instrument in this file is eligible for analysis and should not
perform additional market-selection filtering.

**Publication identity:** Every canonical output carries a
`publication_id` — a unique identifier for the publication cycle
that produced it. This field is part of the universal publication
contract, not a Domain-specific extension: every Domain Publisher
is expected to generate one, since publication identity is a
property of the publishing process itself, not of any particular
Domain's internal data. `publication_id` allows downstream Research Engines
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

**Producer:** `L2_DOMAINS/prediction_markets/`

**Publisher:** `L2_DOMAINS/prediction_markets/publication/publish_canonical_output.py`

**Canonical output:**
`L2_DOMAINS/prediction_markets/data/canonical/prediction_markets_latest.csv`

The Prediction Markets Domain owns publication. Downstream research engines
consume the canonical output rather than requiring Prediction Markets'
internal scanner or diagnostic files.

The canonical publication includes `publication_id` as required by ADR-006.
Concrete fields may evolve through deliberate contract revision; downstream
consumers should depend only on documented fields and meanings required by
their interface.

**Current consumers include:** Market Microstructure and other research
workflows whose documented contracts explicitly depend on the Prediction
Markets canonical publication.

### Diagnostic Artifacts

Diagnostic artifacts are a Domain's raw, internal collection and
scoring history. They remain fully preserved and available for
debugging, auditing, or genuinely domain-specific investigation —
they are never a required input for any Research Engine's normal operation.

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

- Domains own market selection; Research Engines never duplicate it.
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

## 7. Current Architectural Questions

The following remain deliberately unresolved and should be answered from
implementation evidence rather than speculative design:

- Whether future domains require a common cross-domain instrument schema or
  only stable domain-specific publication contracts.
- Which canonical fields, if any, should be universal beyond publication
  identity.
- Whether tradeability or comparable selection metrics can be meaningfully
  normalized across unrelated market domains.
- How domains with different publication cadences should expose stable
  producer/consumer interfaces.
- Whether runtime data should ultimately be organized centrally, per owner,
  or through a hybrid model separating canonical data, domain publications,
  engine state, diagnostics, and archives.
- Which shared market-data capabilities belong permanently in `L1_CORE`
  versus domain-specific implementations in `L2_DOMAINS`.

These questions are not commitments. Architectural changes require evidence,
explicit ownership, and deliberate revision of this specification.

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

**v1.1 — 2026-09-17** — Modernized the canonical architecture around the
implemented L0-L4 ownership model. Replaced obsolete current-state Program
A/B and single-Domain descriptions, updated the Prediction Markets canonical
publication boundary and path, and preserved the accepted v1 ADRs and
historical terminology where they document earlier project state.


**v1.0 — 2026-07-09** — Initial architecture specification. Domain/
Program separation established. Prediction Markets canonical schema
fully specified. Crypto/Futures/Equities explicitly marked as open
architectural questions, not commitments.