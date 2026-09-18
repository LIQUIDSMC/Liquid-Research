# Prediction Markets — Canonical Publication

**Layer:** L2 Domain
**Domain:** Prediction Markets
**Status:** Current

## Purpose

This folder implements the canonical publication boundary for the Prediction
Markets domain.

L2 Prediction Markets owns acquisition, selection, classification support, and
publication of its approved market universe. The publication layer converts the
domain's internal scanner and snapshot artifacts into a stable canonical
interface for downstream research systems.

Architecture authority:

`L0_PLATFORM/zARCHITECTURE.md`

## Canonical Output

The current canonical publication is:

`L2_DOMAINS/prediction_markets/data/canonical/prediction_markets_latest.csv`

The publisher is:

`L2_DOMAINS/prediction_markets/publication/publish_canonical_output.py`

A publication represents the approved Prediction Markets research universe for
one publication cycle.

Downstream systems should consume this canonical contract rather than depending
directly on L2's internal scanner or market-snapshot artifacts.

## Canonical Schema

The publisher currently emits these columns:

- `publication_id` — identifier for the publication cycle.
- `instrument_id` — published instrument identity, currently sourced from slug.
- `resolution_id` — resolution identity, currently sourced from `market_id`.
- `instrument_name` — market question.
- `tradeability_score` — scanner-computed Tradeability Score.
- `category` — classifier output.
- `liquidity` — scanner-provided liquidity value.
- `volume_24h` — scanner-provided 24-hour volume.
- `spread_pct` — scanner-computed spread percentage.
- `spread_label` — scanner-computed spread-quality label.
- `days_left` — days remaining until resolution.

The implementation in `publish_canonical_output.py` is the executable authority
for the current schema and validation behavior.

## Publication Flow

`publish_canonical_output.py` performs four primary responsibilities:

1. Load the latest Prediction Markets scanner results.
2. Load the latest Prediction Markets market snapshot.
3. Build the canonical schema, including category classification.
4. Validate the canonical output before publication.

The current source directories are:

`L2_DOMAINS/prediction_markets/data/scanner/`

`L2_DOMAINS/prediction_markets/data/markets/`

## Failure Behavior

Structural failures fail loudly rather than knowingly publishing an invalid
contract.

Examples include:

- missing required source files;
- missing required source columns;
- canonical column mismatch;
- duplicate `instrument_id` values;
- duplicate `resolution_id` values.

Per-row publication failures are handled separately. A row missing required
publication identity such as slug or `market_id` is excluded and counted.

Classification failure does not block publication. The row remains publishable
with category `Unknown`, and the classification failure is recorded by the
publisher.

This distinction keeps structural contract failures separate from transparent
per-row exclusions or classification fallbacks.

## Publication Identity

`publication_id` identifies the publication artifact/cycle rather than the
underlying market itself.

The identifier is generated independently of the publishing logic so its
strategy can change without redefining the rest of the canonical contract.

See ADR-006 in:

`L0_PLATFORM/zARCHITECTURE.md`

## Downstream Boundary

The canonical publication is an L2 domain interface.

Current downstream research includes Market Microstructure, whose collectors
read the canonical Prediction Markets publication rather than L2 internal
scanner or snapshot files.

This publication boundary is not itself a research engine. It does not own
downstream hypotheses, research interpretation, paper-trade methodology, or
execution logic.

Market Selection research belongs under:

`L3_RESEARCH_ENGINES/market_selection/`

Market Microstructure research belongs under:

`L3_RESEARCH_ENGINES/market_microstructure/`

## Scope and Safety

This publication layer:

- publishes research data;
- validates its canonical contract;
- exposes approved Prediction Markets instruments to downstream research;
- contains no wallet or private-key responsibility;
- performs no live trade execution.

Changes to the canonical schema or producer/consumer boundary are architectural
changes and require explicit review rather than being treated as local
documentation or refactoring changes.

## Historical Terminology

Older documentation, logs, and Git history may refer to this producer through
the former Program A architecture or through pre-L0-L4 paths such as
`data/approved_markets/`.

Those references may remain valid historical evidence of prior repository
states. They are not current operating paths or current ownership terminology.
