# LRS-1 D1-003 — CP-V2 Validation Specification

**State:** PROPOSED FREEZE / NOT YET EXECUTED

**Research target:** D1-003 — Entry-price divergence

**Purpose:** Prospectively define the CP-V2 second-replication methodology
before the CP-V2 manifest is frozen and before any CP-V2 economic outcome is
loaded, inspected, summarized, printed, or otherwise exposed.

---

## 1. Authority and validation boundary

This specification operates under the separately frozen:

`D1_003_CPV2_governance.md`

CP-V2 governance defines eligibility, readiness, deterministic manifest
selection, identity sealing, one-shot integrity, and future-checkpoint rules.

This specification defines the statistical methodology that will apply to the
future immutable CP-V2 100-trade manifest.

At specification freeze:

- CP-V2 manifest frozen: NO;
- CP-V2 outcomes accessed: NO;
- CP-V2 validation executed: NO;
- CP-V2 execution authorized: NO.

The future validation population must be exactly the immutable 100-ID CP-V2
manifest produced under frozen CP-V2 governance.

This specification must not construct that population independently.

---

## 2. Exposure status

CP-V2 inherits an already-developed hypothesis.

Therefore CP-V2 is:

**not hypothesis-naive.**

The existence, direction, and research importance of the D1-003 entry-price
divergence were known before CP-V2.

Hypothesis exposure and trade-outcome exposure are distinct.

The eventual CP-V2 execution must not describe the population as globally
outcome-naive merely because no outcome access is presently known.

Before validation execution authorization, the implementation must establish
the strongest supportable outcome-exposure description from auditable
research-access history and provenance.

That determination must occur as an explicit execution-authorization
precondition rather than being left solely as narrative interpretation.

Absence of known access is insufficient by itself to establish global
outcome-naivety.

---

## 3. Replication hypothesis

CP-V2 tests the same joint divergence structure prospectively tested in
protected V1.

The CP-V2 primary hypothesis is:

> Within the frozen CP-V2 population, higher recorded `entry_price` will
> retain both:
>
> (a) a positive rank relationship with numeric `trade_won`; and
>
> (b) a negative rank relationship with `trade_pnl`.

These two directional relationships jointly define the D1-003 CP-V2
replication target.

The hypothesis does not claim causality.

It does not claim that higher entry price produces higher mean P&L, higher
median P&L, superior risk-adjusted returns, predictive superiority, or a
live-money edge.

---

## 4. Predictor

Primary predictor:

`entry_price`

Rules:

- use the existing recorded `entry_price`;
- no alternate price field;
- no transformed price proxy;
- no outcome-derived transformation;
- no optimized threshold;
- no interaction term becomes part of the primary hypothesis;
- no recoding after CP-V2 outcomes are opened.

---

## 5. Primary outcomes

The two primary outcome relationships are:

1. `entry_price` versus numeric `trade_won`;
2. `entry_price` versus `trade_pnl`.

`trade_won` must use the same deterministic numeric representation used by
the frozen D1-003/V1 methodology.

No additional outcome may replace either primary relationship after CP-V2
outcomes are opened.

---

## 6. Primary statistics and software authority

The primary validation statistics are:

1. Spearman rank association between `entry_price` and numeric `trade_won`;
   expected direction: **positive**.

2. Spearman rank association between `entry_price` and `trade_pnl`;
   expected direction: **negative**.

For each primary association, use:

- `scipy.stats.spearmanr`;
- `scipy==1.18.1`;
- the function's default two-sided behavior;
- complete usable paired observations for the applicable relationship.

No alternative Spearman implementation, exact test, permutation test, custom
tie correction, or alternate p-value calculation may replace this convention
after CP-V2 outcomes are opened.

The observed V1 or Discovery-D numerical magnitudes are not CP-V2 pass
thresholds.

No minimum correlation magnitude derived from D or V1 is used.

A conventional two-sided significance threshold of:

`p < 0.05`

is frozen prospectively.

Both raw primary relationships must satisfy their prespecified direction and
`p < 0.05` before PASS can be considered.

Pearson associations are supporting descriptive statistics only.

They have zero authority to rescue, downgrade, or otherwise change the
classification produced by the frozen primary and family rules.

---

## 7. Population and exclusions

Population:

- exactly the future frozen CP-V2 manifest;
- expected raw n = exactly 100;
- exact CP-V2 manifest SHA-256 must be supplied by the separately authorized
  governance freeze operation.

Exclusions:

- no discretionary exclusions;
- no exclusion based on outcome magnitude;
- no exclusion based on whether a row supports the hypothesis;
- no exclusion based on family, month, side, category, or entry-price level;
- no identity substitution;
- no population resizing.

A row may be unusable for a particular statistic only if a field required for
that statistic is missing or invalid.

Every missing/invalid value and every resulting usable n must be reported.

No missing row may be silently replaced with a later eligible trade.

---

## 8. Primary classification precedence

Classification must be exactly one of:

- PASS
- FAIL
- INCONCLUSIVE

Apply the following rules in order.

### Step 1 — raw primary relationships

Calculate:

- Spearman(`entry_price`, numeric `trade_won`);
- Spearman(`entry_price`, `trade_pnl`).

### Step 2 — FAIL gate

If either raw primary association has the opposite prespecified sign,
classify:

**FAIL**

Specifically:

- Spearman(`entry_price`, `trade_won`) < 0; or
- Spearman(`entry_price`, `trade_pnl`) > 0.

The FAIL gate has precedence over later missingness or sensitivity rules when
an opposite-sign raw primary statistic is mathematically available.

### Step 3 — raw INCONCLUSIVE gate

If no FAIL condition exists, classify INCONCLUSIVE if either raw primary
statistic:

- is exactly zero;
- is mathematically undefined; or
- has the correct prespecified sign but two-sided `p >= 0.05`.

Only if both raw primary relationships have the correct signs and both have
two-sided `p < 0.05` may evaluation proceed to the family gate.

### Step 4 — family robustness gate

Evaluate the frozen family-equal-weight Spearman sensitivity defined below.

If either required family-equal-weight Spearman statistic is:

- reversed;
- exactly zero; or
- mathematically undefined;

classify:

**INCONCLUSIVE**

### Step 5 — PASS

If both raw primary relationships satisfy their required directions and
two-sided `p < 0.05`, and both family-equal-weight Spearman relationships
satisfy their required directions and are mathematically defined, classify:

**PASS**

No other sensitivity has classification authority.

---

## 9. Family/dependence sensitivity

CP-V2 must use the same frozen v1.1 event-family definition and `family_key`
semantics used by the D1-003/V1 research lineage.

The validation implementation must verify the frozen family-detector
authority and provenance before execution.

No new family detector, fuzzy grouping, embedding method, manual regrouping,
or outcome-dependent family reassignment is permitted for CP-V2.

For represented CP-V2 families, report:

- represented-family count;
- largest-family size;
- largest-family raw-trade concentration.

For the family-equal-weight sensitivity, aggregate CP-V2 to one row per
frozen v1.1 `family_key` using arithmetic means of:

- `entry_price`;
- numeric `trade_won`;
- `trade_pnl`.

Each represented family receives one row regardless of family size.

Report Pearson and Spearman associations between family-mean `entry_price`
and each family-mean outcome.

Family-aware analysis remains a sensitivity analysis and is not proof that
observations are fully independent.

### Family classification authority

Family p-values have **zero classification authority**.

The required family directions are:

- family-equal-weight Spearman(`entry_price`, `trade_won`) > 0;
- family-equal-weight Spearman(`entry_price`, `trade_pnl`) < 0.

If a raw primary result otherwise permits PASS but either family direction is
reversed, exactly zero, or mathematically undefined, the overall CP-V2 result
is INCONCLUSIVE.

Family sensitivity cannot convert a raw FAIL into INCONCLUSIVE or PASS.

---

## 10. Fixed entry-price quartile sensitivity

Use the existing frozen D0 entry-price boundaries without modification:

- Q1 boundary: `0.7025`
- median boundary: `0.8675`
- Q3 boundary: `0.9537`

These define the same four fixed entry-price strata used in the D1-003
research lineage.

For each represented stratum report:

- n;
- win rate;
- P&L ordinary mean;
- P&L median;
- frozen 10% symmetric trimmed mean when usable n >= 10.

If usable n < 10, report mean and median and mark the trimmed mean
unavailable.

No boundary may be moved, optimized, merged, or re-derived from CP-V2.

Quartile sensitivity is mandatory disclosure only and has:

**zero classification authority.**

It may not rescue or downgrade PASS, FAIL, or INCONCLUSIVE.

---

## 11. Temporal sensitivity

For every represented calendar month in the frozen CP-V2 population, report
where mathematically usable:

- n;
- win rate;
- P&L ordinary mean;
- P&L median;
- frozen 10% symmetric trimmed mean when n >= 10;
- Pearson and Spearman association between `entry_price` and numeric
  `trade_won`;
- Pearson and Spearman association between `entry_price` and `trade_pnl`.

Every represented month must be reported, including opposite-sign, zero,
undefined, adverse, or otherwise non-confirmatory results.

No month may be excluded from the aggregate primary analysis.

Temporal sensitivity has:

**zero classification authority.**

There is no subjective "material temporal reversal" override in CP-V2.

Temporal results may characterize or limit interpretation but may not rescue,
downgrade, or otherwise alter the deterministic classification produced by
the raw primary and family rules.

---

## 12. Recorded-side sensitivity

Use the existing recorded `Yes` and `No` labels without recoding or
regrouping.

Within each represented side, where mathematically usable, report Pearson and
Spearman association between `entry_price` and:

- numeric `trade_won`;
- `trade_pnl`.

Every side-specific result, including reversal, zero, undefined, adverse, or
otherwise non-confirmatory results, must be reported.

No side may be excluded from the aggregate primary analysis.

Recorded-side sensitivity is mandatory disclosure only and has:

**zero classification authority.**

---

## 13. P&L outlier sensitivity

For the complete usable CP-V2 population report:

- P&L ordinary mean;
- P&L median;
- frozen 10% symmetric trimmed mean when n >= 10;
- sum of the three largest absolute `trade_pnl` magnitudes;
- total absolute P&L;
- top-three absolute-P&L concentration =
  sum of three largest absolute P&L magnitudes / total absolute P&L.

No observation is removed from the primary Spearman analysis because of P&L
magnitude.

Raw results remain primary.

Outlier sensitivity is mandatory disclosure only and has:

**zero classification authority.**

---

## 14. Category treatment

Category may be reported only as composition/concentration context.

No category-specific outcome analysis is authorized.

No category may be excluded or reweighted because of its CP-V2 outcome
behavior.

Category context has zero classification authority.

---

## 15. Supporting statistics

The following must be reported where applicable but are not alternate primary
success criteria:

- Pearson(`entry_price`, `trade_won`);
- Pearson(`entry_price`, `trade_pnl`);
- fixed D0 quartile summaries;
- family-equal-weight Pearson associations;
- temporal Pearson/Spearman associations;
- recorded-side Pearson/Spearman associations;
- raw/median/trimmed P&L summaries;
- top-three absolute-P&L concentration;
- category composition.

No nominally favorable supporting statistic may replace a failed or
inconclusive primary relationship.

---

## 16. Missingness and usable observations

Pairwise complete usable observations are used for each required association.

Every missing or invalid required value must be disclosed.

Every raw and family statistic must report its usable n.

Missingness may not cause:

- identity substitution;
- manifest resizing;
- replacement with later eligible trades;
- threshold movement;
- discretionary exclusion.

If no raw FAIL condition is present and missingness makes either required raw
primary or family statistic mathematically undefined, classify:

**INCONCLUSIVE**

Missingness cannot be used to rescue an opposite-sign raw primary result from
FAIL.

---

## 17. Multiple-testing discipline

CP-V2 evaluates one previously selected candidate family with one joint
structural replication target.

The two raw primary relationships are jointly required components of that
target and are not treated as independent discoveries.

No nominal p-value, favorable secondary statistic, subgroup, quartile,
category, month, side, family result, or outlier treatment may replace a
failed or inconclusive primary relationship.

No post-open candidate switching is permitted.

D1-002, D1-001, or any newly observed candidate may not replace D1-003 as the
CP-V2 primary.

---

## 18. Required CP-V2 validation report

The eventual report must disclose:

- exact CP-V2 manifest identity verification;
- manifest SHA-256;
- raw n and usable n;
- all required-field missingness;
- both primary Spearman statistics and two-sided p-values;
- supporting Pearson statistics;
- fixed D0 quartile summaries;
- family structure and family-equal-weight sensitivity;
- temporal sensitivity;
- recorded-side sensitivity;
- P&L raw/median/trimmed summaries;
- absolute-P&L concentration;
- category composition context;
- every adverse, null, zero, undefined, or reversed required result;
- final PASS / FAIL / INCONCLUSIVE classification;
- outcome-exposure characterization supported at execution authorization;
- interpretation limits;
- whether any prespecified step could not be executed.

No unfavorable result may be silently omitted.

---

## 19. Interpretation of classifications

### PASS

PASS means only that the D1-003 entry-price divergence structure replicated
again under the frozen CP-V2 methodology.

PASS does not establish:

- causality;
- universal generalization;
- live-money profitability;
- production readiness;
- or a production trading rule.

PASS does not automatically authorize CP-V3.

### FAIL

FAIL means at least one mathematically available raw primary relationship had
the opposite prespecified sign.

FAIL is permanently recorded.

CP-V2 may not be resized, redefined, rerun on a replacement population, or
modified to seek a more favorable result.

FAIL does not automatically authorize CP-V3.

### INCONCLUSIVE

INCONCLUSIVE means no raw FAIL condition occurred, but the frozen evidence
requirements for PASS were not completely satisfied.

INCONCLUSIVE is permanently recorded.

It does not authorize changing CP-V2 criteria, resizing the population,
rerunning the same manifest, or automatically creating CP-V3.

Any future checkpoint remains governed by the separately frozen CP-V2
governance.

---

## 20. Execution isolation and fail-closed authorization

Writing, reviewing, auditing, and freezing this specification must not access
CP-V2 economic outcomes.

The eventual validation code must be created and externally audited before
execution authorization.

Before economic outcome access, the validation implementation must verify at
minimum:

- expected canonical CP-V2 governance authority;
- expected canonical CP-V2 methodology authority;
- exact frozen CP-V2 n = 100;
- exact frozen CP-V2 manifest SHA-256;
- zero CP-V2 overlap with frozen D;
- zero CP-V2 overlap with frozen V1;
- frozen v1.1 family-detector authority and provenance;
- exact expected validation-script SHA-256;
- required software/version authority;
- auditable outcome-exposure characterization;
- explicit execution authorization.

The validation implementation must default fail-closed before explicit
execution authorization.

No CP-V2 economic outcome may be printed, summarized, persisted, or otherwise
exposed before all required authorities and execution gates verify.

---

## 21. One-shot integrity

Once the CP-V2 manifest is frozen, it is immutable.

Once CP-V2 outcomes are opened under authorized execution:

- the population may not be resized;
- identities may not be substituted;
- the readiness threshold may not be moved;
- the manifest ordering rule may not be changed;
- primary statistics may not be changed;
- significance rules may not be changed;
- classification precedence may not be changed;
- sensitivity authority may not be changed because of the observed result.

An execution failure must fail closed.

It must not silently create a replacement CP-V2 population or alternate
methodology.

---

## 22. Planned artifacts and current state

Governance:

`L3_RESEARCH_ENGINES/market_selection/analysis/D1_003_CPV2_governance.md`

Validation specification:

`L3_RESEARCH_ENGINES/market_selection/analysis/D1_003_CPV2_validation_specification.md`

Future manifest artifact:

To be defined by the separately audited CP-V2 manifest-freeze implementation.

Future validation code:

`L3_RESEARCH_ENGINES/market_selection/analysis/d1_003_cpv2_validation.py`

Future validation report:

`L3_RESEARCH_ENGINES/market_selection/analysis/D1_003_CPV2_validation.md`

At specification freeze:

- CP-V2 manifest frozen: NO;
- CP-V2 economic outcomes accessed: NO;
- CP-V2 validation executed: NO;
- CP-V2 execution authorized: NO;
- CP-V2 sentinel implemented: NO.

The next implementation phase is the separately audited CP-V2 sentinel and
readiness machinery required by frozen governance.

No outcome analysis is authorized by this specification alone.
