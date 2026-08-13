# Crypto Domain — Strategy Vision

Status: Vision / research design document. No implementation.
Captured: 2026-07-10.

## Purpose of This Document

This document exists so the crypto research direction discussed in
conversation does not remain trapped there. It captures the full
vision, the comparison framework, and the open questions future
research must answer — deliberately before any collector, scanner,
or API integration is written.

## The Core Research Question

Liquid Research's purpose has not changed: discover, validate, and
operationalize repeatable, monetizable trading edges. The Crypto
Domain exists to ask whether that purpose is better served by
Polymarket's crypto prediction markets, real crypto exchanges, or
both — studied in parallel and compared honestly, rather than
assumed in advance.

## Two Parallel Research Tracks

### Track 1 — Crypto Prediction Markets (Polymarket)

Already partially visible in the Prediction Markets Domain today,
under the existing classifier categories "Crypto Long-Duration" and
"Crypto Ultra-Short" (see L2_DOMAINS/prediction_markets/classification/market_classifier.py). A
prediction market: binary or multi-outcome, resolves once, implied
probability rather than a continuously-traded price.

Crypto Ultra-Short markets are currently excluded entirely from
research scope (see zROADMAP.md, Deferred / Blocked Research
Programs — "Crypto Ultra-Short Research Framework"). Whether that
exclusion should be revisited as part of the broader Crypto Domain
vision, or remain a separate standing decision, is itself an open
question — not resolved by creating this folder.

### Track 2 — Real Crypto Markets (Exchanges)

Actual spot/futures markets on real exchanges — Coinbase, Binance,
Kraken, or similar. Continuously traded, real order books, real
bid/ask spreads, no resolution date, no implied-probability framing.
Structurally closer to what Program B's Market Microstructure
Research already studies on Polymarket's order books — but on a
fundamentally different kind of market.

## Comparison Framework

Rather than assuming either track is superior, both should
eventually be evaluated against the same criteria, once real data
exists for both:

- **Statistical significance** — which track, if either, produces
  edges that survive the same evidence-first scrutiny already
  applied to Program A and Program B (three-question check,
  frozen-methodology checkpoints, honest sample-size caveats)?
- **Expectancy** — real, measured average return per trade or per
  signal, not assumed.
- **Consistency** — does either track produce a stable edge over
  time, or one that decays quickly?
- **Liquidity characteristics** — can positions actually be entered
  and exited at the prices the research assumes? This connects
  directly to the "execution survives signal, not the other way
  around" principle already established in zHANDOFF.md.
- **Automatability** — how much of the research-to-execution
  pipeline could realistically be automated for either track, and
  at what engineering cost?
- **Engineering complexity and long-term ROI** — which track
  produces more research value per unit of engineering effort
  invested? This is the same lens already applied throughout
  Liquid Research's "ideas earn structure" discipline.

## Why Implementation Is Intentionally Deferred

This project does not build collectors, scanners, or scoring logic
ahead of the evidence that justifies them. The Prediction Markets
Domain earned its current architecture (canonical output, Domain/
Program separation) only after Program A and Program B had already
produced real, working research — the architecture was extracted
from what worked, not designed in advance and then filled in.

The Crypto Domain should earn its implementation the same way. This
document exists so the vision survives the wait, not so the wait is
skipped.

## Open Questions Future Research Must Answer

These are deliberately left unanswered here. They define what
Phase 1 research (see zROADMAP.md in this folder) would need to
investigate before any implementation begins:

1. Is real exchange data (Coinbase, Binance, Kraken, or similar)
   accessible under terms consistent with Liquid Research's
   platform-wide legal constraints — read-only, no wallet, no
   private key, research-only?
2. What would a minimal, honest comparison between Track 1 and
   Track 2 actually require — same time window, same asset,
   comparable position sizing logic?
3. Does Polymarket's existing crypto category data (already
   collected passively via Program A's classifier) provide enough
   of a starting point for Track 1, or does it need its own
   dedicated collection?
4. What does "canonical output" even mean for a continuously-traded
   market with no resolution date? Per zARCHITECTURE.md's Open
   Design Targets, this is explicitly unresolved for any future
   Domain — Crypto's Track 2 would be the first real test of
   whether the existing schema concepts (instrument_id,
   resolution_id, publication cycle) make sense outside prediction
   markets at all.
5. Should Crypto Ultra-Short's existing exclusion (within the
   Prediction Markets Domain) be revisited once real Crypto Domain
   research exists, or does that remain a separate, standing
   decision?
6. What is the smallest, cheapest experiment that could produce
   real evidence on any one of the six comparison criteria above,
   before committing to building either track's full infrastructure?

## What Success Looks Like at Phase 0

Per this folder's zROADMAP.md: Phase 0 is complete when this
vision is captured, the folder structure exists, and
zARCHITECTURE.md has a forward pointer to this material — not when
any of the six open questions above have answers. Those answers are
Phase 1's job, in a future, separate session.
