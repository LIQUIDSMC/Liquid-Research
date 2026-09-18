# Liquid Research — Platform Roadmap

**Status:** Canonical Portfolio Roadmap
**Last Updated:** 2026-09-18

---

## Mission

Liquid Research is an independent software and quantitative-research project
for building reproducible market-data systems and testing market hypotheses
through disciplined, evidence-first research.

The platform exists to improve the quality, reliability, and scope of market
research. It does not assume that any hypothesis will produce a profitable
strategy.

This roadmap governs portfolio-level priorities and promotion decisions.
Detailed methodology, experiment state, and operational checkpoints belong to
the relevant Domain, Research Engine, or shared service.

---

## Research Integrity Principles

Research quality is more important than development speed.

Rules:

- Never trust a single API field without verification.
- Validate assumptions against authoritative or directly observed evidence.
- Prefer verification over convenience.
- Treat dramatic improvements as potential bugs until proven otherwise.
- Investigate unexpected outputs before calling them signal.
- Spot-check results against real examples where possible.
- Avoid silent failures.
- Fail loudly when required data is invalid or ambiguous.
- Preserve frozen methodology during active evidence collection.
- Separate observations from validated findings.
- Do not promote a hypothesis because it is interesting, technically complex,
  or economically attractive.
- Require reproducible evidence before increasing research scope.

A recurring lesson from Liquid Research is that plausible-looking output can
still be wrong. Identifier errors, stale publications, data-path divergence,
duplicate observations, and timing assumptions have all demonstrated why
verification must precede interpretation.

---

## Operating Constraints

Liquid Research is research software, not a live execution system.

Current platform-level constraints:

- No live-trading capability is implied by research results.
- No private keys or wallet credentials belong in research workflows.
- Public or otherwise authorized data access does not imply authorization to
  trade a product or use an execution interface.
- Regulatory status, venue availability, and platform terms can change and
  must be verified before any future live-execution capability is considered.
- Paper or historical research must not be represented as live profitability.

Any future execution capability requires a separate architectural, legal,
operational, and risk review before implementation authorization.

---

## Architecture

Canonical architecture is defined by `L0_PLATFORM/zARCHITECTURE.md`.

- `L0_PLATFORM` — governance and canonical project authority.
- `L1_CORE` — shared engineering infrastructure and orchestration.
- `L2_DOMAINS` — market-domain acquisition, selection, publication, and
  domain-specific context.
- `L3_RESEARCH_ENGINES` — independent research systems.
- `L4_KNOWLEDGE` — shared findings, hypotheses, open questions, archived
  research state, and future concepts.

Architecture and roadmap are separate authorities:

- Architecture answers **where a responsibility belongs**.
- Roadmap answers **what portfolio-level work is active, parked, or next**.
- Engine-specific documents answer **how a research question is being tested
  and what its current evidence says**.

---

## Current Portfolio

### Market Selection

**Location:** `L3_RESEARCH_ENGINES/market_selection/`
**Portfolio status:** Active research

Studies whether market-level characteristics provide useful evidence for
market selection and tradeability research.

Prediction-market acquisition and canonical publication are owned upstream by
`L2_DOMAINS/prediction_markets/`.

Current research state and operations are owned by the Market Selection control
documents. This roadmap does not duplicate their changing counts or
checkpoints.

### Market Microstructure

**Location:** `L3_RESEARCH_ENGINES/market_microstructure/`
**Portfolio status:** Active research

Studies order-book and microstructure behavior, including independently tested
indicators and their stability.

Current methodology, checkpoints, backlog, and evidence are owned by the
engine's control documents.

### Market Data Platform / Crypto Trade-Flow Research

**Shared infrastructure:** `L1_CORE/market_data_platform/`
**Domain context:** `L2_DOMAINS/crypto/`
**Portfolio status:** Active engineering and research

The Market Data Platform provides shared, venue-aware data infrastructure.
Crypto-specific research uses that infrastructure without owning the shared
platform itself.

Current research has progressed beyond initial collector construction into
controlled trade-flow experimentation. Detailed experiment status remains with
the relevant L1/L2 research authorities and artifacts.

### Market Regime Intelligence

**Location:** `L3_RESEARCH_ENGINES/market_regime_intelligence/`
**Portfolio status:** Active research — methodology controlled

Studies market-regime classification and regime-conditioned research under
explicit pre-inference methodology controls.

The presence of implemented primitives or tests does not by itself authorize
later methodology-dependent stages. Current implementation authorization must
come from the engine's methodology authority.

### Wallet Intelligence

**Location:** `L3_RESEARCH_ENGINES/wallet_intelligence/`
**Portfolio status:** Retained / dormant

Existing read-only wallet discovery and analysis infrastructure is preserved.
No current evidence supports treating Wallet Intelligence as an active
research program.

Do not expand or remove it solely because the implementation exists. Revival
requires a current research question, evidence need, and explicit promotion.

---

## Portfolio Priorities

### Priority 1 — Authority and Repository Coherence

Complete the L0-L4 migration at the documentation and navigation level.

Current portfolio work includes:

- Remove stale current-state Program A/B terminology where it incorrectly
  represents present architecture.
- Repair broken post-restructure paths and authority references.
- Preserve historical terminology where it documents actual project history.
- Make current control documents easy to discover from the public repository.
- Keep architecture, roadmap, engine ownership, and implementation aligned.

This is a documentation and repository-coherence priority, not authorization
to change research methodology.

### Priority 2 — Preserve Active Research Integrity

Allow active engines to continue under their existing methodology and evidence
gates.

Portfolio-level rules:

- Do not alter frozen experiments to accelerate results.
- Do not combine signals before standalone evidence justifies combination.
- Do not infer predictive value from implementation completeness.
- Do not promote paper or historical results into profitability claims.
- Do not let repository cleanup change experimental meaning.

### Priority 3 — Strengthen Shared Engineering Where Evidence Requires It

Shared infrastructure should be promoted into `L1_CORE` only when multiple
domains or engines genuinely need the capability.

Examples include:

- Market-data collection and normalization.
- Orchestration and operational safeguards.
- Deterministic validation.
- Failure detection and observability.
- Reusable data contracts.

Avoid speculative platform engineering without a demonstrated consumer or
operating requirement.

### Priority 4 — Improve Public Technical Legibility

The repository should accurately expose the engineering and research work that
already exists.

Priorities include:

- Clear root navigation.
- Accurate architecture and ownership documentation.
- Discoverable engine entry points.
- Visible tests and validation practices.
- Reproducible research artifacts where appropriate.
- Clear distinction between active research, historical evidence, and parked
  concepts.

Public presentation must not inflate Liquid Research into a company,
institutional platform, production trading system, or validated profitable
strategy.

---

## Parked and Future Research

Parked work is not scheduled implementation.

A parked concept may have supporting notes, preliminary evidence, or even
historical code. None of those automatically authorize promotion.

### Gamma Research

**Location:** `L4_KNOWLEDGE/future_engine_concepts/gamma_research/`
**Status:** Parked

Retained as a future research concept. Revival requires a current research
question, data-source review, methodology definition, and explicit promotion.

### Entry Calibration

**Status:** Parked candidate

Research into entry-price or calibration effects remains a legitimate future
direction. Historical exploratory work does not constitute an active,
independent research engine.

### Execution Intelligence

**Status:** Parked candidate

Potential future research into spread, depth, slippage, queue position,
partial fills, latency, and execution realism.

Promotion should follow demonstrated need from research that requires a more
realistic execution model.

### Cross-Market / Cross-Venue Intelligence

**Status:** Parked candidate

Potential research into semantically related markets or instruments across
venues and market structures.

This supersedes the old assumption that a future lettered "Program D" should
automatically represent cross-venue spread research. Any future implementation
must earn its own current architecture and methodology.

### Additional Concepts

Additional hypotheses and future-system ideas belong in `L4_KNOWLEDGE/` until
they pass deliberate review.

Examples may include event intelligence, opportunity-cost analysis, research
quality tooling, failure-mode monitoring, simulation, allocation research,
meta-learning, and other concepts recorded in the knowledge layer.

Their presence in L4 is not a build queue.

---

## Promotion Rules

A concept does not become an active Research Engine merely because:

- A paper or repository describes it.
- A preliminary analysis looks promising.
- Infrastructure already exists.
- The implementation would be technically interesting.
- The expected economic payoff appears large.

Promotion requires:

1. A clearly stated research question.
2. A defined owner and architecture boundary.
3. Evidence that the required data is available and sufficiently understood.
4. A methodology that can be tested without contaminating existing frozen
   experiments.
5. Explicit success, failure, and stopping criteria where applicable.
6. A decision that the expected information value justifies the engineering
   and research cost.
7. Explicit authorization to move from concept to implementation.

Where appropriate, methodology reproduction and independent evidence should
remain separate promotion gates.

---

## Platform Engineering Backlog

Engineering work should remain tied to demonstrated research or operational
needs.

Current classes of legitimate platform work include:

- Observability and failure-mode detection.
- Data-integrity validation.
- Canonical publication and provenance safeguards.
- Reproducible research tooling.
- Operational automation where manual processes create demonstrated drift.
- Portability improvements where environment coupling is an actual reusable
  software problem.
- Public repository navigation and documentation coherence.

Historical backlog items from the pre-L0-L4 architecture should not be copied
forward automatically. Re-evaluate them against current implementation and
current engine needs before scheduling work.

---

## Historical Naming

Earlier Liquid Research versions used lettered Programs:

- Program A — Tradeability / Market Selection lineage.
- Program B — Market Microstructure lineage.
- Program C — proposed Entry Calibration research.
- Program D — proposed Cross-Venue research.
- Program E — proposed Category-Aware Wallet research.

These names remain valid historical terminology when describing the project at
that time.

They are **not** the current portfolio namespace.

Current work should use L0-L4 ownership and descriptive system names. Do not
perform blind global renames inside historical research evidence, incident
records, frozen methodology, or provenance artifacts.

---

## Roadmap Maintenance

Update this document when:

- A research concept is formally promoted, parked, revived, or retired.
- A new Domain, shared platform service, or Research Engine becomes canonical.
- Portfolio priorities materially change.
- An architectural migration changes the portfolio-level ownership map.

Do not update this document merely because:

- A trade count changed.
- A new daily observation arrived.
- An engine reached an internal checkpoint.
- A paper experiment produced another sample.
- A methodology-specific diagnostic changed.

Those belong to the owning engine's authority.

The roadmap should remain a stable map of **portfolio direction**, not a
duplicate Mission Control.
