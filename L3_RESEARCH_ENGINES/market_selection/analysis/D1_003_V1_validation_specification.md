# LRS-1 D1-003 — V1 Validation Specification

**Specification date:** 2026-10-03

**State:** PROPOSED FREEZE / NOT YET EXECUTED

**Discovery primary:** D1-003 — Entry-price family

**Purpose:** Prospectively define the independent V1 validation of the
entry-price/outcome structure selected from Discovery D before any V1 outcome
value is loaded, inspected, summarized, printed, or otherwise exposed.

---

## 1. Validation boundary

Discovery D and protected validation population V1 remain distinct.

- Discovery D: n=396.
- D trade-id SHA-256:
  `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`
- Protected V1: n=80.
- V1 trade-id SHA-256:
  `a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141`
- D/V1 trade-id overlap: 0.
- Future ledger growth does not alter D or V1 membership.
- V1 outcomes have not been opened for this validation round at the time this
  specification is written.

V1 membership must come from the already-frozen D/V1 identity boundary used
by the existing LRS-1 discovery tooling. It must not be reconstructed using a
new date-only shortcut or any outcome-dependent rule.

---

## 2. Hypothesis being independently tested

Discovery D selected an entry-price **divergence structure**, not a claim that
higher entry price monotonically improves economic outcomes.

The V1 primary hypothesis is:

> Within protected V1, higher recorded `entry_price` will retain both
> (a) a positive rank relationship with `trade_won`, and
> (b) a negative rank relationship with `trade_pnl`.

These two directional relationships jointly define the primary D1-003
replication target.

The hypothesis does not claim causality.

The hypothesis does not claim that higher entry price produces higher mean
P&L, higher median P&L, superior risk-adjusted returns, predictive superiority,
or a live-money edge.

---

## 3. Predictor

Primary predictor:

`entry_price`

Rules:

- use the existing recorded `entry_price`;
- no alternate price field;
- no transformed price proxy;
- no outcome-derived transformation;
- no optimized threshold;
- no interaction term becomes part of the primary hypothesis;
- no recoding after V1 is opened.

---

## 4. Primary outcomes

The two primary outcome relationships are:

1. `entry_price` versus numeric `trade_won`;
2. `entry_price` versus `trade_pnl`.

`trade_won` is represented numerically using the same deterministic
representation used by the frozen D1-003 Discovery-D methodology.

No additional outcome may replace either relationship after V1 is opened.

---

## 5. Primary statistics and expected directions

The primary validation statistics are:

1. Spearman rank association between `entry_price` and numeric `trade_won`;
   expected direction: **positive**.
2. Spearman rank association between `entry_price` and `trade_pnl`;
   expected direction: **negative**.

Both directions were selected because they constitute the Discovery-D
structure chosen prospectively for independent V1 validation.

The observed numerical magnitudes from D are not V1 pass thresholds.

No minimum correlation magnitude or Discovery-D-derived threshold is used.

For each primary Spearman association, report the two-sided p-value produced
by `scipy.stats.spearmanr` under `scipy==1.18.1`, using the function's default
two-sided behavior on the complete usable paired observations. This exact
library/version/function convention is frozen for V1 classification. No
alternative Spearman implementation, exact test, permutation test, custom
tie correction, or alternate p-value calculation may replace it after V1 is
opened.

A conventional two-sided significance threshold of `p < 0.05` is frozen
prospectively as a non-D-derived evidentiary bar. Both primary relationships
must satisfy their prespecified direction and `p < 0.05` to satisfy the
primary V1 replication criterion.

Pearson associations are supporting descriptive statistics and are not
permitted to rescue failure or non-confirmation of either primary Spearman
relationship.

---

## 6. Primary success criterion

D1-003 satisfies the primary V1 replication criterion only if, using the
complete usable protected V1 population:

- Spearman(`entry_price`, `trade_won`) is strictly greater than 0 with a
  two-sided `p < 0.05`; **and**
- Spearman(`entry_price`, `trade_pnl`) is strictly less than 0 with a
  two-sided `p < 0.05`.

Both conditions are required.

Primary classification is deterministic:

- if either primary Spearman association has the opposite prespecified sign,
  the V1 result is FAIL;
- if either primary Spearman association is exactly zero or mathematically
  undefined, the V1 result is INCONCLUSIVE;
- if both primary associations have the correct prespecified signs but either
  has a two-sided `p >= 0.05`, the V1 result is INCONCLUSIVE;
- only if both primary associations have the correct signs and both have
  two-sided `p < 0.05` does the primary criterion permit PASS, subject only to
  the deterministic frozen family rule in Section 9.

No D-derived effect-size threshold is used.

---

## 7. Population and exclusions

Population:

- exactly the protected V1 identity set;
- expected raw n=80;
- exact V1 trade-id SHA-256:
  `a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141`.

Exclusions:

- no discretionary exclusions;
- no exclusion based on outcome magnitude;
- no exclusion based on whether a row supports the hypothesis;
- no exclusion based on family, month, side, category, or entry-price level.

A row may be unusable for a particular statistic only if a field required for
that statistic is missing or invalid.

Every missing/invalid value and every resulting usable n must be reported.

If missingness makes either primary statistic mathematically undefined, the
overall V1 result is INCONCLUSIVE rather than PASS.

---

## 8. Fixed entry-price quartile sensitivity

Use the existing outcome-blind D0 entry-price boundaries without modification:

- Q1 boundary: 0.7025
- median boundary: 0.8675
- Q3 boundary: 0.9537

These create the same four fixed entry-price strata used in D1-003 Discovery D.

For each represented stratum report:

- n;
- win rate;
- P&L ordinary mean;
- P&L median;
- frozen 10% symmetric trimmed mean when usable n >= 10.

If usable n < 10, report mean and median and mark the trimmed mean unavailable.

The quartile view is a prespecified nonlinear/descriptive sensitivity of the
same candidate family. It is not four independent validation tests and does
not replace the primary continuous Spearman criterion.

Every represented quartile result, including any non-monotonic, adverse,
zero-information, or otherwise non-confirmatory pattern, must be reported.

The fixed-quartile sensitivity is mandatory disclosure only and has **zero
classification authority** for PASS, FAIL, or INCONCLUSIVE. It may not rescue
or downgrade the result determined by the primary and family rules.

Because V1 is smaller than D, absence of observations from a fixed stratum is
reported and does not authorize moving, merging, splitting, or optimizing the
boundaries.

---

## 9. Family/dependence sensitivity

Use the existing frozen v1.1 event-family assignment.

Report:

- represented-family count;
- largest-family size;
- largest-family raw-trade concentration.

For the family-equal-weight sensitivity, aggregate V1 to one row per frozen
v1.1 `family_key` using arithmetic means of:

- `entry_price`;
- numeric `trade_won`;
- `trade_pnl`.

Report Pearson and Spearman associations between family-mean `entry_price`
and each family-mean outcome.

Each represented family receives one row regardless of family size.

Family-aware analysis remains a sensitivity analysis and is not proof that
observations are independent.

### Family robustness rule

The frozen family-equal-weight Spearman sensitivity has deterministic
classification authority.

If the raw-trade primary criterion otherwise permits PASS, the final result is
INCONCLUSIVE if either:

- family-equal-weight Spearman(`entry_price`, `trade_won`) is less than or
  equal to 0; or
- fa### Temporal robustness rule

Temporal sensitivity is mandatory disclosure only.

Every represented calendar-month result must be reported, including any
opposite-sign, zero, undefined, or otherwise adverse result.

Temporal results have **zero classification authority** for PASS, FAIL, or
INCONCLUSIVE. They may not rescue a failed or inconclusive primary result and
may not downgrade a result that otherwise satisfies the deterministic primary
and family rules.

No month may be excluded from the aggregate primary analysis.
ian;
- frozen 10% symmetric trimmed mean when n >= 10;
- Pearson and Spearman association between `entry_price` and `trade_won`;
- Pearson and Spearman association between `entry_price` and `trade_pnl`.

Because protected V1 contains only 80 trades and its month composition has not
been outcome-opened, individual months are sensitivity evidence rather than
independent primary tests.

### Temporal robustness rule

No requirement is imposed that every represented V1 month reproduce both
primary directions; doing so would create an unanchored small-subgroup pass
threshold.

Instead, temporal results are inspected only for a **material reversal**:
a represented month with mathematically usable statistics showing both

- negative Spearman(`entry_price`, `trade_won`); and
- positive Spearman(`entry_price`, `trade_pnl`)

constitutes a joint reversal of the primary divergence structure.

A single such month does not automatically fail V1. Its n, family
concentration, and relation to the aggregate result must be reported and the
overall result classified INCONCLUSIVE if the aggregate PASS depends
materially on excluding or overwhelming that reversed temporal segment.

No month may be removed to restore the aggregate result.

---

## 11. Recorded-side sensitivity

Use the existing recorded `Yes` and `No` labels without recoding or regrouping.

Within each represented side, where mathematically usable, report Pearson and
Spearman association between `entry_price` and:

- numeric `trade_won`;
- `trade_pnl`.

Side analysis is a prespecified robustness sensitivity, not a separate
candidate or interaction search.

Every side-specific result, including any reversal, zero, undefined, or
otherwise adverse result, must be reported.

Recorded-side sensitivity is mandatory disclosure only and has **zero
classification authority** for PASS, FAIL, or INCONCLUSIVE. It may not rescue
or downgrade the result determined by the primary and family rules.

No side may be excluded from the aggregate primary analysis.

---

## 12. P&L outlier sensitivity

For the complete usable V1 population report:

- P&L ordinary mean;
- P&L median;
- frozen 10% symmetric trimmed mean when n >= 10;
- sum of the three largest absolute `trade_pnl` magnitudes;
- total absolute P&L;
- top-three absolute-P&L concentration =
  sum of three largest absolute P&L magnitudes / total absolute P&L.

The frozen 10% symmetric trimming rule is unchanged from D1-003 Discovery D.

No observation is removed from the primary Spearman analysis because it is an
outlier.

### Outlier robustness rule

Outlier sensitivity is mandatory disclosure only and has **zero
classification authority** for PASS, FAIL, or INCONCLUSIVE.

No observation is removed from the primary Spearman analysis because of P&L
magnitude. Raw results remain primary. Trimmed statistics and absolute-P&L
concentration characterize economic sensitivity only and may not rescue or
downgrade the result determined by the primary and family rules.

---

## 13. Entry-price treatment

`entry_price` itself is the primary predictor.

Therefore no separate covariate adjustment for entry price is applicable.

The continuous rank view is primary.

The fixed D0 quartile view is the prespecified nonlinear/descriptive
sensitivity.

No new entry-price threshold or bucket may be created after V1 outcomes are
opened.

---

## 14. Category treatment

Category may be reported only as composition/concentration context.

No category-specific outcome analysis is authorized.

No category may be excluded or reweighted because of its V1 outcome behavior.

---

## 15. Supporting statistics

The following are reported but are not alternate primary success criteria:

- Pearson(`entry_price`, `trade_won`);
- Pearson(`entry_price`, `trade_pnl`);
- fixed D0 quartile summaries;
- family-equal-weight Pearson associations;
- temporal Pearson/Spearman associations;
- recorded-side Pearson/Spearman associations;
- raw/median/trimmed P&L summaries;
- top-three absolute-P&L concentration;
- category composition.

Nominal significance does not independently determine PASS or FAIL.

Supporting statistics may not rescue failure of the joint primary Spearman
directional criterion.

---

## 16. Overall classification

The validation result must be classified as exactly one of PASS, FAIL, or
INCONCLUSIVE using the deterministic rules below.

### Classification precedence

Apply the rules in this order:

1. evaluate the two raw-trade primary Spearman relationships;
2. if either has the opposite prespecified sign, classify FAIL;
3. otherwise, if either is zero, mathematically undefined, or has the correct
   sign but two-sided `p >= 0.05`, classify INCONCLUSIVE;
4. otherwise both raw-trade primary relationships have the correct signs and
   two-sided `p < 0.05`; evaluate the frozen family-equal-weight Spearman
   sensitivity;
5. if either family-equal-weight direction is reversed, zero, or undefined as
   defined in Section 9, classify INCONCLUSIVE;
6. otherwise classify PASS.

No other sensitivity has classification authority.

### PASS

PASS requires:

- Spearman(`entry_price`, `trade_won`) > 0 with two-sided `p < 0.05`;
- Spearman(`entry_price`, `trade_pnl`) < 0 with two-sided `p < 0.05`;
- family-equal-weight Spearman(`entry_price`, `trade_won`) > 0;
- family-equal-weight Spearman(`entry_price`, `trade_pnl`) < 0;
- all four statistics mathematically defined; and
- exact prespecified analysis executed without post-open modification.

PASS means the selected D1-003 entry-price divergence structure independently
replicated under this frozen V1 specification.

PASS does not establish causality, live-money profitability, universal
generalization, or a production trading rule.

### FAIL

FAIL applies if either raw-trade primary Spearman relationship has the
opposite prespecified sign:

- Spearman(`entry_price`, `trade_won`) < 0; or
- Spearman(`entry_price`, `trade_pnl`) > 0.

If D1-003 FAILS, this V1 round fails.

D1-002 and D1-001 may not be tested as replacement primaries on the same V1
population.

### INCONCLUSIVE

INCONCLUSIVE applies if no FAIL condition is present and any of the following
holds:

- either raw-trade primary Spearman statistic is exactly zero;
- either raw-trade primary Spearman statistic is mathematically undefined;
- both raw-trade primary directions are correct but either has a two-sided
  `p >= 0.05`;
- either frozen family-equal-weight Spearman direction is reversed or zero;
- either frozen family-equal-weight Spearman statistic is mathematically
  undefined;
- missingness prevents a required primary or family statistic from being
  evaluated.

INCONCLUSIVE is not PASS.

### Sensitivities without classification authority

The following remain mandatory and must be reported completely but have
**zero authority** to alter PASS, FAIL, or INCONCLUSIVE:

- fixed D0 entry-price quartiles;
- calendar-month temporal sensitivity;
- recorded-side sensitivity;
- P&L trimming and absolute-P&L concentration;
- category composition context;
- supporting Pearson statistics.

They may characterize, qualify, or limit interpretation in the written
report, but they may not change the deterministic classification produced by
the raw-trade primary and frozen family rules.

---

## 17. Multiple-testing discipline

This is one candidate family with one joint structural replication target.

The two primary outcome relationships are jointly required components of that
target and are not treated as independent discoveries.

No nominal p-value, favorable secondary statistic, subgroup, quartile,
category, month, side, or family result may replace a failed primary
relationship.

No post-open candidate switching is permitted.

---

## 18. Required validation report

The eventual V1 report must disclose:

- exact V1 identity verification;
- raw n and usable n;
- all required-field missingness;
- both primary Spearman statistics;
- supporting Pearson statistics;
- fixed D0 quartile summaries;
- family structure and family-equal-weight sensitivity;
- temporal sensitivity;
- recorded-side sensitivity;
- P&L raw/median/trimmed summaries;
- absolute-P&L concentration;
- category composition context;
- every adverse, null, zero, undefined, or reversed result;
- final PASS / FAIL / INCONCLUSIVE classification;
- interpretation limits;
- whether any prespecified step could not be executed.

No unfavorable result may be silently omitted.

---

## 19. Execution isolation

Writing and reviewing this specification must not access V1 outcomes.

The eventual validation code must be created and externally audited before
execution authorization.

Before execution, the code must verify:

- expected canonical methodology commit;
- protected V1 n=80;
- exact V1 trade-id SHA-256;
- zero D/V1 overlap;
- frozen family-detector provenance and checksums;
- exact expected validation-script SHA-256;
- execution authorization state.

The validation script must default fail-closed before explicit execution
authorization.

No V1 outcome value may be printed, summarized, persisted, or otherwise
exposed before the specification and exact validation code are frozen and
execution is separately authorized.

---

## 20. Planned artifacts

Specification:

`L3_RESEARCH_ENGINES/market_selection/analysis/D1_003_V1_validation_specification.md`

Planned validation code:

`L3_RESEARCH_ENGINES/market_selection/analysis/d1_003_v1_validation.py`

Planned validation report:

`L3_RESEARCH_ENGINES/market_selection/analysis/D1_003_V1_validation.md`

At specification freeze:

- V1 validation opened: NO.
- V1 outcome values accessed: NO.
- V1 analysis executed: NO.
- V1 execution authorized: NO.
