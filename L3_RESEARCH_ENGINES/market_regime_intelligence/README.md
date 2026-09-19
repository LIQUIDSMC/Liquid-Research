# LRS-4 — Market Regime Intelligence

LRS-4 studies whether causally observable market regimes explain variation in
the behavior of an existing frozen LRS-3 research candidate. The current
research design conditions inherited LRS-3 observations on causal volatility
regime state rather than redefining the upstream candidate.

## Current Status

- Experiment v1 methodology is **FROZEN historical authority**.
- Stage-1 primitives were implemented and structurally tested under legitimate
  v1 authorization.
- During Stage-1 implementation, a Gate-2 evaluation-domain specification
  omission was discovered **post-freeze and pre-outcome**.
- Gate-2-dependent implementation stopped rather than adopting an unstated
  temporal-boundary interpretation.
- Experiment v2 is currently **DRAFT / OUTCOME-BLIND / NOT FROZEN /
  IMPLEMENTATION NOT AUTHORIZED**.
- No conditioned LRS-4 HIGH-versus-LOW outcome was used to resolve the
  specification omission or select the v2 methodology.

The Gate-2 omission does not retroactively invalidate completed Stage-1
primitives whose frozen behavior does not depend on the missing evaluation-domain
definition. Reuse under v2 remains subject to the final v2 dependency and
authority model.

## Implemented So Far

The current tree contains Stage-1 primitives for:

- trade loading;
- source-history handling;
- grid returns;
- realized volatility;
- threshold learning;
- regime-state construction;
- regime episodes;
- observation assignment.

Corresponding structural tests are present for these modules.

This does **not** mean that Stage 1 as a whole is declared complete, that Gate 2
has been implemented, or that v2 implementation is authorized.

## Why Gate 2 Stopped

Frozen v1 methodology relied on a current Gate-2 evaluation domain but did not
deterministically define that domain's temporal boundaries. Those boundaries
affect downstream censoring, classification totals, regime diagnostics, and
Gate-2 routing.

The omission was identified after the v1 freeze and before inspection of
conditioned LRS-4 outcomes. No missing-boundary interpretation was silently
adopted. Experiment v2 exists to resolve this specification gap through
outcome-blind methodology revision before Gate-2-dependent implementation
continues.

## Authority Boundaries

LRS-4 does not redefine the inherited LRS-3 research candidate.

The frozen canonical LRS-3 implementation remains authoritative for inherited
observation construction, eligibility, decile ranking, D9-D0, and relevant
timing semantics. LRS-4 conditions those inherited observations on regime state;
it does not substitute reconstructed upstream methodology.

Experiment v1 remains the frozen historical predecessor specification.
Experiment v2 is the current methodology revision, but it remains unfrozen and
does not authorize Gate-2-dependent implementation.

## Research Firewall

LRS-4 uses outcome-blind change control. Conditioned HIGH-versus-LOW results,
`Delta_regime`, conditioned forward-return results, bootstrap intervals, and
equivalent conditioned outcome evidence must not be used to select or repair
methodology before the applicable freeze.

No conditioned LRS-4 outcome was used to resolve the Gate-2 omission or select
the current v2 methodology.

## Documentation Map

`LRS4_Experiment_v1_Pre-Inference_Freeze.md` currently contains both:

1. the canonical frozen Experiment-v1 research-design record and its post-freeze
   Gate-2 omission history; and
2. the current Experiment-v2 pre-inference methodology revision.

The v2 material in that document remains **DRAFT / OUTCOME-BLIND / NOT FROZEN /
IMPLEMENTATION NOT AUTHORIZED**.

A future controlled documentation migration may separate v2 authority from the
v1 freeze record. Until that migration is explicitly completed, the existing
experiment document remains the source for both records.
