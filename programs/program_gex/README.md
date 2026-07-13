# Program GEX

**Status: Placeholder. No implementation exists.**

Program GEX is a planned downstream research Program, following the
same Domain/Program relationship established elsewhere in Liquid
Research (see zARCHITECTURE.md). It does not own market selection
or raw data collection — it will consume canonical options-chain
data (open interest, exchange-reported Greeks, contract
specifications) to compute derived analytics, primarily Gamma
Exposure (GEX).

## What This Program Would Do

Compute and research gamma exposure and related options-derived
metrics from canonical options-chain facts. GEX itself, and any
Greeks computed by us rather than reported by an exchange, are
always derived, disposable analytics — never canonical data.

## What Raw Options Data Would Come From

If and when built, raw options-chain collection (open interest,
exchange-reported Greeks, contract specs) would live under
market_data_platform/, since that platform owns venue-agnostic
canonical ingestion. Program GEX would consume that canonical
output, the same way Program B consumes the Prediction Markets
Domain's canonical output today.

## Current Status

Architecture and placement only — see the design discussion that
established this placement. No code, no collectors, no adapters,
no schemas exist for this Program. Not scheduled. Will begin with
one real instrument/source when prioritized, generalizing only
after a second implementation provides real evidence.
