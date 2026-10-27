# LRS4 — Post-Audit Test Correction Addendum

**STAGING ONLY — NOT CANONICAL — NOT FROZEN**

This addendum supplements, but does not replace,
TEST_RECONCILIATION_OVERLAY_PROPOSED.md.

## A43 — D4 Upstream Immutability

Required correction:
Explicitly cite I48 alongside the existing controlling
invariants for D4 upstream immutability.

Acceptance condition:
The corrected test must reject downstream mutation
of authoritative upstream D-stage outputs.

## A92 — SH_path Construction Timing

Required correction:
Explicitly cite I49 for the requirement that SH_path
is constructed only after Instrument Path finalization.

Acceptance condition:
Reject construction from an incomplete or unresolved
Instrument Path.

I38 remains independently responsible for
realization eligibility.

## A136 — D3 Producer Uniqueness

Required correction:
Add an explicit fixture exercising I52 single-authoritative-
producer requirements for D3.

Acceptance condition:
The fixture detects competing authoritative D3 producers
even if their emitted values happen to agree.

## Provenance Controls

I14: ORIGINAL. D3 endpoint totality.
I52: ADJUDICATED. Authoritative producer uniqueness.
I37: ADJUDICATED_CORRECTION.
I47: RECONSTRUCTED_PROPOSED_NOT_ORIGINAL.
I49: ADJUDICATED_REPLACEMENT.

## Additional Review Obligations

Retain all eight items in the original reconciliation overlay.

A57: Derived structural identity, not a new primitive rule.

## Integration Boundary

This document records accepted correction requirements.
It does not modify the 196 original test definitions.

Actual corrected test definitions require separate
source-grounded review and controlled integration.
