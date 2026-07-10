# Prediction Markets Domain — Producer

This folder implements the Prediction Markets Domain's producer
responsibility, per zARCHITECTURE.md.

## What This Is

Per zARCHITECTURE.md Section 2, a **Domain** owns market selection
for one category of financial market. A **Domain producer**
publishes exactly one canonical output — the public interface and
canonical data contract that downstream Programs consume.

Today, Program A is the current implementation of the Prediction
Markets Domain's producer. This folder holds that producer's
implementation, separate from Program A's own research logic
(programs/program_a/analysis/) and presentation tooling
(programs/program_a/presentation/).

## Responsibilities

Per zARCHITECTURE.md Section 5, a Domain producer is responsible
for:
- Producing a complete canonical output.
- Ensuring every published instrument satisfies the Domain's
  approval criteria.
- Maintaining compatibility with the documented canonical schema.
- Publishing a coherent snapshot representing a single publication
  cycle.

These are architectural responsibilities, not implementation
details — the how may change freely as long as the published
contract remains intact (see zARCHITECTURE.md, Interface
Stability).

## What Gets Published

File: data/approved_markets/prediction_markets_latest.csv

Schema (per zARCHITECTURE.md Section 5):

publication_id — unique identifier for this publication cycle
instrument_id — maps to slug
resolution_id — maps to market_id / conditionId
instrument_name — maps to question
tradeability_score — Prediction Markets' scanner-computed score
category — classifier output
liquidity — scanner-computed liquidity figure
volume_24h — scanner-computed 24-hour volume
spread_pct — scanner-computed spread percentage
spread_label — scanner-computed spread quality label
days_left — days remaining until resolution

## How It Works

publish_canonical_output.py performs four responsibilities only:
1. Load the latest scanner results.
2. Load the latest snapshot.
3. Build the canonical schema (including computing category).
4. Validate the output before publishing.

Structural failures (missing source file, missing required column)
raise loudly rather than publishing an invalid contract. Per-row
failures (missing slug, missing market_id) are excluded and
counted, not silently dropped — every publication reports how many
instruments were approved by the scanner, how many were published,
and how many were skipped and why.

generate_publication_id() is isolated in its own function so the
identifier strategy can change independently of the publishing
logic. See zARCHITECTURE.md ADR-006 for why publication_id
identifies the publication artifact itself, not the underlying
scanner/snapshot data.

## Downstream Consumers

Per zARCHITECTURE.md Section 5, downstream Programs interact with
this Domain exclusively through the published canonical output —
never by reading Program A's internal snapshot or scanner files
directly.

Program B (Market Microstructure Research) is currently the only
downstream consumer, reading the canonical output directly with no
joins and no artificial sample-size limit.

## What This Folder Does NOT Do

- Does not perform research or analysis (see
  programs/program_a/analysis/).
- Does not decide Program A's own internal trading logic —
  paper_trader.py and scanner.py continue to use Program A's own
  internal snapshot/scanner artifacts directly, per
  zARCHITECTURE.md Section 5 (internal implementation details
  rather than the published Domain interface). This is correct
  architecture, not technical debt — the canonical output exists
  as the interface for downstream Programs, and Program A is the
  Domain's own producer, not a downstream consumer of itself.