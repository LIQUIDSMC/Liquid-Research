# LRS-1 D1 — Candidate / Statistic Log

**DISCOVERY EVIDENCE — D ONLY. V1 REMAINS UNOPENED.**

## Purpose

This is the append-only running log for LRS-1 D1 hypothesis-generating
outcome discovery.

Every materially distinct outcome-facing question or statistic examined on
the frozen discovery population D must be registered here before execution.
Its result must then be recorded here whether supportive, null, adverse,
ambiguous, or operationally uninteresting.

This log exists to prevent selective memory, silent candidate deletion,
post-hoc redefinition, and unrecorded repeated slicing.

## Frozen research boundary

### Discovery population D

- n: **396**
- Boundary: currently closed LRS-1 paper trades with recorded
  `resolution_date` on or before 2026-09-23.
- D trade-id SHA-256:
  `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`
- D is historically outcome-exposed and is used for discovery only.
- D is not independent validation evidence.

### Protected validation population V1

- n: **80**
- V1 trade-id SHA-256:
  `a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141`
- D/V1 trade-id overlap: **0**
- V1 outcomes remain unopened for this research round.
- No D1 analysis may load, inspect, summarize, print, or otherwise expose
  V1 outcome values.
- Future ledger growth does not alter D or V1 membership.

### Frozen family assignment

- Detector:
  `analysis/latent_event_family_detector_v1_1.py`
- Detector SHA-256:
  `008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e`
- v1.1 assignment SHA-256:
  `a0a11cd96c8d188cdab17077f38d66932c48b2f2f44acde49815a89d1a7a07c6`
- Primary assignment SHA-256:
  `09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3`
- Derived assignment SHA-256:
  `1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a`

Family-aware analyses are sensitivity analyses. They do not establish that
observations are fully independent.

## Canonical LRS-1 remains frozen

D1 does not authorize changes to:

- Tradeability Score formula or weights
- scanner filters
- admission behavior
- D1/D2 market-identity invariant
- paper-trading behavior
- category classifier or taxonomy
- production/runtime behavior

Discovery findings do not automatically modify canonical LRS-1.

## D1 logging rule

Before executing any materially distinct outcome-facing question, append a
new entry to the registry below and freeze:

1. candidate/statistic ID;
2. registration state;
3. exact question;
4. predictor(s);
5. transformation, bucket, or comparison rule;
6. outcome metric(s);
7. population and exclusions;
8. missing-data rule;
9. family/dependence treatment;
10. temporal treatment;
11. entry-price treatment where applicable;
12. outlier treatment for P&L;
13. planned descriptive/statistical outputs;
14. code or execution artifact;
15. registration timestamp / commit provenance where available.

Only after registration may the statistic be executed.

After execution, append the observed result without rewriting the
pre-execution specification.

A null, adverse, reversed, fragile, or uninteresting result remains in this
log permanently.

## Outcome metrics

Outcome-facing D1 analyses may use only explicitly registered outcome
metrics.

Possible metrics include:

- `trade_won`
- `trade_pnl`

`winning_outcome` may be used only if a prospectively registered question
actually requires the resolved contract outcome itself.

`exit_reason` is not an economic performance metric and must not be pulled
into an analysis without separate prospective justification.

## Frozen P&L robustness rule

For every P&L-based candidate:

- ordinary mean P&L;
- median P&L;
- **10% symmetric trimmed mean P&L** as the primary robust sensitivity;
- concentration of total P&L in the largest absolute observations reported
  separately.

If usable n < 10, no 10% trimmed mean is computed. Report raw mean and
median and mark the trimmed statistic unavailable.

The trim percentage must not change candidate-by-candidate.

## Predictor-family control

`tradeability_score_at_entry`, `spread_label`, `liquidity`, and
`volume_24h` belong to one conceptual tradeability feature family.

Aligned findings among these variables do not count as independent
discoveries.

`category_tier` encodes another research program's priorities and carries
no LRS-1 profitability prior.

`position_size` is excluded because it is constant in the frozen
population.

`entry_reason` is excluded as a meaningful predictor because it records
scanner admission provenance rather than an independent market feature.

## Entry-price control

Every serious Tradeability Score/component candidate must disclose:

- unadjusted result;
- entry-price stratification or other prospectively registered adjustment;
- interaction analysis where prospectively justified;
- whether direction and economic magnitude remain stable.

A changed relationship after entry-price adjustment is not, by itself,
evidence of causality.

## Temporal robustness

Serious candidates must be examined across prospectively defined temporal
slices where applicable.

Temporal boundaries must not be optimized to observed outcome performance.

Report whether an apparent relationship is concentrated in a narrow period
or scanner cohort.

## Dependence robustness

Report:

- raw n;
- usable n;
- represented frozen families;
- concentration in the largest families;
- category composition;
- temporal coverage.

Where applicable, compare raw-trade evidence with a prospectively
registered family-aware sensitivity.

Do not convert the frozen family detector into a mathematically exact
"effective independent n."

## Multiple-testing discipline

D is exploratory and may support many registered questions.

However:

- nominal significance alone is not validation;
- repeated slicing is not validation;
- materially tested nulls remain recorded;
- correlated variants are treated as one candidate family;
- "replication" is reserved for protected V1 or later independent evidence.

## Candidate evidence profile

Candidates are characterized without a fake numeric score.

The evidence profile considers:

- economic magnitude;
- directional consistency;
- temporal robustness;
- family/dependence robustness;
- entry-price robustness;
- outlier robustness;
- sample breadth/concentration;
- simplicity/interpretability;
- operational relevance.

## Candidate ranking

If multiple candidate families survive D discovery, ranking uses this
predefined order:

1. discovery-internal consistency / robustness;
2. breadth across time and frozen families;
3. economic relevance;
4. simplicity / interpretability;
5. operational usefulness.

Correlated versions of the same underlying hypothesis remain one candidate
family.

## Promotion to V1

Exactly one primary hypothesis may be promoted from D to V1.

Before any V1 outcome is opened, freeze:

- predictor(s);
- transformation/buckets;
- expected direction;
- population/exclusions;
- family treatment;
- temporal treatment;
- entry-price treatment;
- outcome metrics;
- primary success criterion;
- sensitivity analyses;
- rejection/inconclusive criteria;
- exact analysis code/version.

After V1 is opened, none of those may be changed for that validation round.

If the primary candidate fails V1, V1 fails. Candidate #2 is not tested on
the same V1 population.

## V1 success-criterion discipline

D determines which hypothesis is selected, but the observed D effect
magnitude does not automatically define the V1 pass threshold.

A quantitative anchor is independent only if its basis genuinely originates
outside the D0/D1 observations used by this research round — for example,
external literature, a structural fact, or a rule fixed before observing D.
A statistic observed anywhere within D0/D1 does not become an independent
anchor merely because it concerns a different predictor, relationship, or
candidate within the same discovery program.

If no defensible independent quantitative anchor exists, use the frozen
structural replication framework:

1. same prespecified direction;
2. no material reversal under entry-price sensitivity where applicable;
3. no material reversal under the frozen outlier sensitivity;
4. result not solely attributable to one latent family;
5. exact prespecified analysis with no post-open modification.

Magnitude and uncertainty are then characterized without inventing a
post-hoc decimal threshold.

---

# Statistic / Candidate Registry

**Registry state at creation: no D1 outcome-facing statistic has yet been
executed under this protocol.**

| ID | State | Candidate family | Registered question | Outcome metric(s) | Execution artifact | Result state |
| --- | --- | --- | --- | --- | --- | --- |
| D1-001 | EXECUTED | Tradeability feature family — score/outcome relationship | Does Tradeability Score exhibit a stable relationship with paper-trade outcomes inside frozen D? | trade_won; trade_pnl | `analysis/D1_001_score_outcomes.md` | INCONCLUSIVE |

---


## D1-001 — Tradeability Score vs paper outcomes

### PRE-EXECUTION REGISTRATION

- **State:** REGISTERED / NOT YET EXECUTED
- **Candidate family:** Tradeability feature family — score/outcome relationship.
  Tradeability Score, spread label, liquidity, and volume_24h remain one
  correlated conceptual feature family; aligned results among them will not be
  counted as independent discoveries.
- **Exact question:** Within frozen D, does `tradeability_score_at_entry`
  exhibit a stable relationship with paper-trade outcomes, and does any
  observed relationship survive the frozen entry-price, temporal,
  family/dependence, and P&L-outlier sensitivity checks?
- **Prior exposure / novelty limitation:** This relationship is not a fresh,
  independent hypothesis. Historical Audit E already examined Tradeability
  Score against outcomes, including a median score split and entry-price
  stratification. D1-001 is a prospectively specified discovery analysis on
  frozen D intended to characterize robustness under the now-frozen D1
  protocol, not to erase or reset that prior exposure.
- **Predictor(s):** Primary predictor =
  `tradeability_score_at_entry`. `spread_label`, `liquidity`, and
  `volume_24h` may be reported only as correlated-feature-family context or
  decomposition and may not be promoted as separate independent discoveries
  from D1-001 without their own prospective registry entries.
- **Transformation / comparison rule:** Two prespecified score views:
  (1) continuous score using Pearson and Spearman association with numeric
  outcomes where mathematically applicable; and
  (2) fixed outcome-blind D0 median split:
  Low = score < 93.70 and High = score >= 93.70.
  The 93.70 threshold is frozen from D0 predictor-only characterization and
  may not be moved after outcomes are inspected. No outcome-optimized score
  threshold, alternate bucket boundary, or post-hoc subgroup split is allowed
  under D1-001.
- **Outcome metric(s):** `trade_won` and `trade_pnl`. For the fixed Low/High
  comparison report win rate and P&L ordinary mean, median, and frozen 10%
  symmetric trimmed mean when eligible. For continuous score report Pearson
  and Spearman association with numeric `trade_won` and `trade_pnl`, with
  interpretation separating statistical association from economic magnitude.
- **Population:** Frozen D only: n=396, `resolution_date <= 2026-09-23`,
  trade-id SHA-256
  `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`.
- **Exclusions:** No discretionary exclusions. A row is excluded from a
  specific statistic only when a field required for that statistic is missing
  or invalid; every such exclusion must be counted and disclosed. No exclusion
  based on outcome magnitude, family membership, category, month, side, or
  whether the result supports the candidate.
- **Required fields:** `trade_id`, `resolution_date`,
  `tradeability_score_at_entry`, `entry_price`, `trade_won`, `trade_pnl`,
  `entry_date`, `category`, plus the frozen v1.1 event-family assignment.
  `spread_label`, `liquidity`, and `volume_24h` are required only if the
  correlated-feature context/decomposition section is executed.
- **Missing-data rule:** No silent deletion. Report missing count and usable n
  separately for every statistic. Frozen family derivation uses explicit
  `unclassified` where applicable rather than dropping difficult markets.
- **Raw n before exclusions:** 396.
- **Family/dependence treatment:** Report raw-trade results and frozen
  event-family structure. Report represented-family count, largest-family
  concentration, and whether the apparent direction is solely attributable
  to one family. For the prespecified family-equal-weight sensitivity,
  aggregate frozen D to one row per frozen v1.1 `family_key` using the
  within-family arithmetic mean of `tradeability_score_at_entry`,
  `trade_won`, and `trade_pnl`; then report Pearson and Spearman associations
  between family-mean score and each family-mean outcome. Each represented
  family receives one row regardless of family size. Family-aware results are
  sensitivity analyses, are not a separate candidate, and are not treated as
  proof of independent observations.
- **Temporal treatment:** Use the outcome-blind D0 calendar-month cohorts
  already fixed by entry date: June, July, August, September 2026. Report
  direction/magnitude by month where usable n permits; do not create
  outcome-driven date cutoffs.
- **Entry-price treatment:** Primary result is unadjusted. Sensitivity uses the
  fixed outcome-blind D0 entry-price boundaries:
  Q1 = 0.7025, median = 0.8675, Q3 = 0.9537.
  Examine the prespecified score relationship within those four entry-price
  strata. These strata may not be moved after outcome inspection. A changed
  or weakened result is evidence about robustness, not automatic evidence of
  entry-price causality.
- **P&L outlier treatment:** Ordinary mean + median + frozen 10% symmetric
  trimmed mean when n >= 10; absolute-P&L concentration separately. For
  D1-001, the concentration statistic is fixed prospectively as the sum of
  the three largest absolute `trade_pnl` magnitudes and that amount as a
  share of total absolute P&L. The top-three count preserves the previously
  used Audit E focus on the three largest absolute observations, while the
  total-absolute-P&L denominator is explicitly the D1-001 concentration
  definition and should not be represented as Audit E's denominator. The
  number three and the trim percentage may not vary after D1-001 execution
  begins.
- **Planned outputs:** Raw/usable n; missingness; Low/High group sizes; win
  rates; P&L mean/median/10%-trimmed mean; continuous score associations;
  absolute-P&L concentration; represented-family count and concentration;
  calendar-month sensitivity; fixed entry-price-stratum sensitivity;
  category composition; correlated-feature-family context; adverse/null
  findings; economic magnitude; interpretation limits. No candidate ranking
  or V1 promotion is implied by execution.
- **Execution artifact/code:**
  `L3_RESEARCH_ENGINES/market_selection/analysis/d1_001_score_outcomes.py`
  and
  `L3_RESEARCH_ENGINES/market_selection/analysis/D1_001_score_outcomes.md`.
  Neither artifact exists at registration time.
- **Registered before execution:** YES
- **V1 accessed:** NO

### POST-EXECUTION RECORD

- **State:** EXECUTED
- **Execution date/time:** 2026-10-02; exact execution time was not captured in
  the execution artifact.
- **Code/artifact SHA or commit:** Frozen execution methodology commit
  `3d6979928279d168338bf424ea43ccc53a60a58d`; executed script SHA-256
  `ae1a0e699c4ec1149cf2b12b7e77b337ed6459d476fdb8f5c930f428eddcfa09`;
  report SHA-256
  `df42a6eeda2065d38dd91eb54418b9a8bda65002e6e16d315e4f1eb4aa15092c`.
- **Usable n:** 396/396 for all registered required fields and reported primary
  statistics; no missing values in the reported required/context fields.
- **Families represented:** 207 frozen v1.1 families; largest family n=14
  (3.54% of D).
- **Category composition:** Other/Unknown 180 (45.45%); Geopolitical 105
  (26.52%); Crypto Long-Duration 64 (16.16%); Sports 17 (4.29%);
  Political 15 (3.79%); Macro/Economic 14 (3.54%); Entertainment 1
  (0.25%).
- **Temporal coverage:** Frozen D calendar-month cohorts: June 2026 n=45;
  July n=108; August n=163; September n=80.
- **Observed result:** Continuous score associations were weak: score vs
  `trade_won` Pearson=-0.0627, Spearman=-0.0298; score vs `trade_pnl`
  Pearson=0.0326, Spearman=0.1129. At the frozen 93.70 split, Low n=196
  had win rate 82.65% and High n=200 had win rate 82.50%, providing
  essentially no Low/High win-rate separation.
- **Economic magnitude:** Low mean P&L=-3.8311, median=6.3550, frozen
  10%-trimmed mean=-0.4607. High mean P&L=6.1219, median=8.1100,
  frozen 10%-trimmed mean=9.7947. Thus pooled D contains an economically
  meaningful High-vs-Low P&L separation, but that separation is not by itself
  evidence of a stable general score/outcome relationship.
- **Entry-price sensitivity:** Materially heterogeneous across the four frozen
  D0 strata. Q1 favored High strongly; Q2 favored Low on mean and trimmed-mean
  P&L; Q3 mildly favored High; Q4 showed little economic separation and mixed
  continuous rank behavior. The pooled score/P&L relationship therefore does
  not remain directionally/magnitude-stable across entry-price contexts.
- **Family/dependence sensitivity:** Equal-weight family-level associations
  remained weak: family-mean score vs mean `trade_won` Pearson=-0.0627,
  Spearman=0.0158; family-mean score vs mean `trade_pnl` Pearson=0.0484,
  Spearman=0.1257. Family weighting did not materially strengthen the
  continuous relationship.
- **Temporal sensitivity:** Heterogeneous. June and July did not show a
  High-score P&L advantage; August and September did. Monthly score/P&L
  Pearson values ranged from -0.1067 to 0.0800 and Spearman values from
  -0.0426 to 0.1779. The pooled economic separation is therefore not
  temporally stable across the prespecified D0 month cohorts.
- **Outlier sensitivity:** Total realized P&L=473.48. The three largest
  absolute P&L magnitudes sum to 300.00 and represent 2.10% of total absolute
  P&L under the prospectively frozen D1-001 concentration definition.
  The pooled Low/High contrast remains present under the frozen 10% symmetric
  trimmed mean (Low=-0.4607; High=9.7947), so the pooled difference is not
  solely an ordinary-mean artifact.
- **Null/adverse findings:** Win-rate separation at the fixed score split was
  effectively absent; continuous score/outcome associations were weak;
  entry-price-stratum direction was inconsistent; temporal direction was
  inconsistent; and family equal-weighting did not materially strengthen the
  continuous result.
- **Interpretation limits:** D is discovery evidence with historical outcome
  exposure, and D1-001 does not erase Audit E. The pooled P&L contrast cannot
  be treated as an independently validated score edge because robustness is
  heterogeneous across prespecified contexts. Entry-price results are
  sensitivity analyses, not evidence of entry-price causality. Family-aware
  results do not prove independence. Correlated liquidity, volume, and
  spread-label context are not independent discoveries. No threshold,
  subgroup, or candidate may be changed post hoc from these results.
- **Candidate status:** INCONCLUSIVE — pooled P&L separation is economically
  nontrivial and survives the frozen trimmed-mean sensitivity, but the
  registered requirement of a stable score/outcome relationship is not
  supported consistently across continuous, entry-price, temporal, and
  family-aware views. This status does not promote D1-001 to V1.
- **V1 accessed:** NO

---

# Entry Template

## D1-XXX — [short candidate/statistic name]

### PRE-EXECUTION REGISTRATION

- **State:** REGISTERED / NOT YET EXECUTED
- **Candidate family:**
- **Exact question:**
- **Predictor(s):**
- **Transformation / comparison rule:**
- **Outcome metric(s):**
- **Population:** frozen D only, unless explicitly narrower
- **Exclusions:**
- **Required fields:**
- **Missing-data rule:**
- **Raw n before exclusions:** 396
- **Family/dependence treatment:**
- **Temporal treatment:**
- **Entry-price treatment:**
- **P&L outlier treatment:** ordinary mean + median + frozen 10% symmetric
  trimmed mean when n >= 10; absolute-P&L concentration separately
- **Planned outputs:**
- **Execution artifact/code:**
- **Registered before execution:** YES
- **V1 accessed:** NO

### POST-EXECUTION RECORD

- **State:** EXECUTED
- **Execution date/time:**
- **Code/artifact SHA or commit:**
- **Usable n:**
- **Families represented:**
- **Category composition:**
- **Temporal coverage:**
- **Observed result:**
- **Economic magnitude:**
- **Entry-price sensitivity:**
- **Family/dependence sensitivity:**
- **Temporal sensitivity:**
- **Outlier sensitivity:**
- **Null/adverse findings:**
- **Interpretation limits:**
- **Candidate status:** RETAIN / REJECT / INCONCLUSIVE / DESCRIPTIVE ONLY
- **V1 accessed:** NO

---

**Append-only rule:** once an entry has been executed, preserve both its
pre-execution specification and its observed result. Corrections must be
added explicitly; do not silently rewrite the historical test.
