# Crypto Domain — Mission Control

> This document tracks the Crypto Domain specifically. Platform-wide
> architecture lives in zARCHITECTURE.md. Platform-wide roadmap and
> program registry live in zROADMAP.md.

Last updated: 2026-07-10

## Phase Status

**Phase 0 — Documentation and Architecture: IN PROGRESS.**

No collectors, scanners, scoring logic, or exchange API integrations
exist. This is intentional. See README.md and
research/strategy_vision.md for the full reasoning.

## What Exists Today

- Folder structure (domains/crypto/, domains/crypto/research/)
- README.md — Domain overview, architectural placement, relationship
  to Prediction Markets Domain
- MISSION_CONTROL.md — this file
- zROADMAP.md — phased plan starting at documentation-only
- research/strategy_vision.md — full research vision: two-track
  comparison framework, six open questions, explicit deferral
  reasoning

## What Does NOT Exist Today

- No collector, scanner, scorer, or classifier
- No exchange API integration (Coinbase, Binance, Kraken, or any
  other)
- No canonical output
- No real or simulated trading of any kind
- No decision yet on which of the two research tracks (Crypto
  Prediction Markets vs. Real Crypto Markets) to investigate first

## Blocking Conditions

None technical. This is a resourcing and prioritization decision,
not an engineering blocker. Program A (toward its 100-trade
milestone) and Program B (its own ongoing microstructure research)
remain the platform's active research priorities. The Crypto Domain
proceeds to Phase 1 only when there's genuine capacity to do the
research properly, not because a placeholder exists.

## Done When (Phase 0)

- [x] domains/ top-level folder created
- [x] domains/crypto/ folder created
- [x] README.md captures Domain overview and architectural placement
- [x] MISSION_CONTROL.md captures current status (this file)
- [x] zROADMAP.md captures phased plan
- [x] research/strategy_vision.md captures the full research vision
- [x] zARCHITECTURE.md has a forward pointer to this Domain's
      existence

Phase 0 is complete once all items above are checked and committed.
Phase 1 (real research into the open questions in
research/strategy_vision.md) is future work, not started, no
committed timeline.

## Relationship to Program A and Program B

None. This Domain does not read from, write to, or depend on any
Program A or Program B file, dataset, or module. Its eventual
canonical output (if built) would be entirely independent, per
zARCHITECTURE.md's Domain/Program separation.
