# Crypto Domain — Liquid Research

## Status

**Vision stage.** No collectors, scanners, scoring logic, or API
integrations exist yet. This folder captures the research direction,
architecture, and open questions for what would become Liquid
Research's second Domain — nothing here is implemented.

This is a deliberate sequencing decision, consistent with
zARCHITECTURE.md's own Open Design Targets: the canonical schema
built for the Prediction Markets Domain has not been validated
against a second Domain, and this project does not build
infrastructure ahead of the evidence that justifies it. Crypto is
the first candidate second Domain — its home exists now so the
vision doesn't stay trapped in conversation, but its implementation
waits until real evidence says it's worth building.

## What This Domain Would Cover

Liquid Research today is Polymarket-only. The Crypto Domain
represents the platform's first deliberate step toward becoming a
genuine multi-domain research platform — the "battleship" every
future research area (Futures, Equities, and beyond) will eventually
sit alongside.

Crypto is not one research direction. It's explicitly framed as
**two parallel, independently testable research tracks**, compared
against each other rather than assumed in advance:

1. **Crypto Prediction Markets** — Polymarket's existing crypto
   category (already present today as "Crypto Long-Duration" and
   "Crypto Ultra-Short" within the Prediction Markets Domain's own
   classifier). A prediction market on a crypto outcome.
2. **Real Crypto Markets** — actual continuously-traded spot/futures
   markets on real exchanges (Coinbase, Binance, Kraken, etc.). A
   fundamentally different market structure: continuous trading,
   real order books, real liquidity, no resolution date.

These are genuinely different market types, and this project does
not assume one is better than the other before the evidence exists.
See research/strategy_vision.md for the full comparison framework.

## Why This Belongs at the domains/ Level, Not programs/

Per zARCHITECTURE.md Section 2, a **Domain** owns market selection
for one category of financial market. A **Program** answers a
research question using a Domain's canonical output. Crypto, if and
when it's built, would be a second Domain — a market-selection
producer, structurally distinct from Program B or Program C, which
are research consumers of the Prediction Markets Domain.

Filing this under programs/ would misrepresent its eventual role.
domains/crypto/ correctly reserves its architectural position
without implying it's ready to be built.

## What Exists in This Folder Today

- README.md — this file.
- MISSION_CONTROL.md — current status, phased plan, done-when
  criteria.
- zROADMAP.md — Crypto Domain's own roadmap, explicitly starting
  at Phase 0 (documentation only).
- research/strategy_vision.md — the full research vision:
  comparison framework, open questions, and why implementation is
  intentionally deferred.

## What Does NOT Exist Here Yet

- No collector, scanner, scorer, or classifier.
- No API integration with any exchange.
- No canonical output.
- No wallet, no private key, no execution — consistent with Liquid
  Research's platform-wide legal and safety constraints (see
  zROADMAP.md's Legal Constraints section), which apply to every
  Domain, present and future.

## Relationship to the Prediction Markets Domain

This Domain does not depend on or modify the Prediction Markets
Domain in any way. Program A and Program B continue exactly as they
are. The Crypto Domain's eventual canonical output, if built, would
follow the same architectural principles established in
zARCHITECTURE.md (Domain owns selection, publishes one canonical
output, downstream Programs consume it) — but per zARCHITECTURE.md's
own Open Design Targets, whether the *same schema* applies is an
open question to be answered with evidence once this Domain is
actually built, not assumed today.
