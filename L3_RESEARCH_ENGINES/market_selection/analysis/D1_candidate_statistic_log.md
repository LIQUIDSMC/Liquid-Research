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
| D1-002 | EXECUTED | Trade-side family — YES/NO outcome relationship | Does trade side exhibit a stable relationship with paper-trade outcomes inside frozen D? | trade_won; trade_pnl | `analysis/D1_002_side_outcomes.md` | INCONCLUSIVE |
| D1-003¹ | REGISTERED / NOT YET EXECUTED | Entry-price family — entry-price/outcome relationship | Does entry price exhibit a stable relationship with paper-trade outcomes inside frozen D? | trade_won; trade_pnl | Not yet created | PENDING EXECUTION |

¹ **D1-003 status correction — 2026-10-03:** This summary row preserves the
historical pre-execution state shown when D1-003 was registered. D1-003 was
subsequently executed in Discovery D; see its canonical POST-EXECUTION RECORD
and the 2026-10-03 D1 Discovery Candidate Ranking below. Current governance
state: D1-003 is executed, ranked #1, and selected as the Discovery-D primary
for prospective V1 specification. V1 remains unopened.

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


---

## D1-002 — Trade Side vs paper outcomes

### PRE-EXECUTION REGISTRATION

- **State:** REGISTERED / NOT YET EXECUTED
- **Candidate family:** Trade-side family — YES/NO outcome relationship.
  `side` is not part of the Tradeability Score / spread / liquidity /
  volume_24h correlated feature family tested in D1-001.
- **Exact question:** Within frozen D, does recorded trade side (`Yes` versus
  `No`) exhibit a stable relationship with paper-trade outcomes, and does any
  observed side difference survive the frozen entry-price, temporal,
  family/dependence, and P&L-outlier sensitivity checks?
- **Prior exposure / novelty limitation:** D0 characterized side composition
  without outcomes: No n=264 (66.67%) and Yes n=132 (33.33%). D1-001 did not
  test side against outcomes. No directional YES-versus-NO profitability
  hypothesis is claimed from D0. D1-002 is exploratory discovery on frozen D,
  not independent validation.
- **Predictor(s):** Primary predictor = `side`, using the existing recorded
  binary values `Yes` and `No`. No recoding, optimized subgroup, or
  outcome-derived side definition is permitted.
- **Expected direction:** None prespecified. D1-002 is two-sided with respect
  to which recorded side, if either, has better paper outcomes. Direction may
  be described after execution but may not be retroactively represented as
  prospectively predicted.
- **Transformation / comparison rule:** Compare the two existing side groups
  directly: `Yes` versus `No`. No threshold search, alternate grouping, or
  post-hoc side interaction becomes part of the primary comparison.
- **Outcome metric(s):** `trade_won` and `trade_pnl`. For each side report win
  rate and P&L ordinary mean, median, and frozen 10% symmetric trimmed mean
  when eligible. Report the raw between-side difference in win rate, ordinary
  mean P&L, median P&L, and trimmed-mean P&L as descriptive economic contrasts.
  No p-value or nominal significance result alone constitutes validation.
- **Population:** Frozen D only: n=396,
  `resolution_date <= 2026-09-23`, trade-id SHA-256
  `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`.
- **Exclusions:** No discretionary exclusions. A row is excluded from a
  statistic only if a field required for that statistic is missing or invalid;
  every exclusion must be counted and disclosed. No exclusion based on
  outcome magnitude, family, category, month, entry price, or whether the
  result supports a side difference.
- **Required fields:** `trade_id`, `resolution_date`, `side`, `entry_price`,
  `trade_won`, `trade_pnl`, `entry_date`, `category`, plus the frozen v1.1
  event-family assignment.
- **Missing-data rule:** No silent deletion. Report missing count and usable n
  for every required statistic. Frozen family derivation uses explicit
  `unclassified` where applicable rather than dropping difficult markets.
- **Raw n before exclusions:** 396.
- **Family/dependence treatment:** Report raw-trade results and frozen
  event-family structure. Report represented-family count and largest-family
  concentration. For the primary family-equal-weight sensitivity, aggregate
  each `family_key × side` combination to one row containing that cell's
  arithmetic-mean `trade_won` and arithmetic-mean `trade_pnl`. Then, for each
  side separately, report the unweighted arithmetic mean across its represented
  family cells for each outcome, so every family represented on that side
  receives one equal contribution regardless of its trade count. A family
  represented on both sides contributes one family cell to each side; a family
  represented on only one side contributes only to that side. Report the
  number of frozen families represented by each side and the number containing
  both sides. As an additional paired-family sensitivity, restrict to frozen
  families containing both sides, compute within each family the difference
  `Yes family-cell mean - No family-cell mean` separately for `trade_won` and
  `trade_pnl`, then report the unweighted arithmetic mean and median of those
  family-level differences. Do not outcome-filter or otherwise select paired
  families beyond the structural requirement that both sides are represented.
  Family-aware and paired-family results are sensitivity analyses only, are
  not separate candidates, and are not proof of independent observations.
- **Temporal treatment:** Use the outcome-blind D0 calendar-month cohorts
  already fixed by entry date: June, July, August, September 2026. Report
  Yes/No direction and economic magnitude within each month where usable n
  permits. No outcome-driven temporal cutoffs.
- **Entry-price treatment:** Primary side comparison is unadjusted. Robustness
  uses the fixed outcome-blind D0 entry-price boundaries:
  Q1=0.7025, median=0.8675, Q3=0.9537. Compare Yes/No outcomes within those
  four fixed strata. Boundaries may not be moved after outcome inspection.
  Changed side performance across strata is evidence about robustness, not
  evidence of entry-price causality.
- **P&L outlier treatment:** Ordinary mean + median + frozen 10% symmetric
  trimmed mean when n >= 10. Also report the sum of the three largest absolute
  `trade_pnl` magnitudes and its share of total absolute P&L for the complete
  usable D1-002 population, using the same prospectively fixed D1 concentration
  convention as D1-001. This concentration statistic is contextual and does
  not replace side-specific robust estimators.
- **Category treatment:** Category composition may be reported by side as
  context/concentration diagnostics. Category-specific outcome comparisons
  are not separate D1-002 candidates and may not be promoted from this test
  without prospective registration.
- **Planned outputs:** Raw/usable n; missingness; Yes/No group sizes; win rates;
  P&L mean/median/10%-trimmed mean; between-side descriptive contrasts;
  absolute-P&L concentration; represented-family counts and family-aware
  sensitivity; fixed calendar-month sensitivity; fixed entry-price-stratum
  sensitivity; category composition by side; adverse/null findings; economic
  magnitude; interpretation limits. No candidate ranking or V1 promotion is
  implied by execution.
- **Execution artifact/code:**
  `L3_RESEARCH_ENGINES/market_selection/analysis/d1_002_side_outcomes.py`
  and
  `L3_RESEARCH_ENGINES/market_selection/analysis/D1_002_side_outcomes.md`.
  Neither artifact exists at registration time.
- **Registered before execution:** YES
- **V1 accessed:** NO

### POST-EXECUTION RECORD

- **State:** EXECUTED
- **Execution date/time:** 2026-10-02; exact execution time was not captured in
  the execution artifact.
- **Code/artifact SHA or commit:** Frozen execution methodology commit
  `5f84a8dc642350f2e0e344ccf3d595b95863551c`; executed script SHA-256
  `d84d416bea44d9d70b412fe6d5f91a3220b2d372538ed4a8d0cfd9e55079f923`;
  report SHA-256
  `8863e3c394c99a270823c1d78fc7d3015da1de0faca46c4037dad5081194773c`.
- **Usable n:** 396/396 for all registered required fields and primary
  statistics; Yes n=132 and No n=264.
- **Families represented:** 207 frozen v1.1 families; largest family n=14
  (3.54% of D). Yes represented 99 families, No represented 132, and 24
  frozen families contained both sides.
- **Category composition:** The generated execution report emitted overall
  category composition but omitted the registered by-side context diagnostic.
  That diagnostic was subsequently completed outcome-free using the exact
  frozen detector D identity. Yes: Other/Unknown 57 (43.18%), Geopolitical
  34 (25.76%), Crypto Long-Duration 17 (12.88%), Sports 8 (6.06%),
  Political 8 (6.06%), Macro/Economic 7 (5.30%), Entertainment 1 (0.76%).
  No: Other/Unknown 123 (46.59%), Geopolitical 71 (26.89%), Crypto
  Long-Duration 47 (17.80%), Sports 9 (3.41%), Political 7 (2.65%),
  Macro/Economic 7 (2.65%), Entertainment 0 (0.00%). The completion read no
  outcome columns, performed no category/outcome comparison, introduced no
  new candidate or subgroup, wrote no artifact, and did not access V1.
- **Temporal coverage:** June 2026 n=45; July n=108; August n=163;
  September n=80.
- **Observed result:** Reported pooled win rates were Yes=0.8258 and
  No=0.8258, with reported Yes-minus-No difference=0.0000. Pooled P&L
  favored Yes: Yes mean=10.2473, median=11.9250, trimmed mean=14.4619;
  No mean=-3.3302, median=5.8200, trimmed mean=0.3023.
- **Economic magnitude:** Yes-minus-No P&L differences were mean=13.5774,
  median=6.1050, and frozen 10%-trimmed mean=14.1596. No directional side
  hypothesis was prospectively registered.
- **Entry-price sensitivity:** Yes-minus-No mean P&L remained positive in all
  four frozen strata: Q1=31.9868, Q2=9.8431, Q3=1.2148, Q4=1.4526.
  Trimmed-mean differences were also positive in all four: Q1=38.9461,
  Q2=10.1938, Q3=0.2817, Q4=0.1628. Median P&L mildly reversed in Q3
  (-0.3450). P&L magnitude attenuated substantially at higher entry prices.
- **Family/dependence sensitivity:** Equal-weight family-cell mean P&L was
  10.0715 for Yes and -4.3486 for No. Equal-weight mean `trade_won` was
  0.8054 for Yes and 0.8146 for No. Among 24 families containing both sides,
  mean within-family Yes-minus-No P&L=33.8805 and median=47.1262;
  `trade_won` differences had mean=0.1156 and median=0.0000. Family-aware
  results remain sensitivity analyses, not proof of independence.
- **Temporal sensitivity:** Heterogeneous. June reversed against the pooled
  P&L direction: Yes-minus-No mean=-6.5083, median=-7.4500, trimmed
  mean=-9.7631. July favored Yes (mean=13.1271; trimmed=11.6553), August
  favored Yes modestly (mean=1.8311; trimmed=0.7284), and September favored
  Yes strongly (mean=41.0597; trimmed=46.6885). Win-rate differences were
  negative in June, July, and August and positive in September.
- **Outlier sensitivity:** Total realized P&L=473.48. The three largest
  absolute P&L magnitudes sum to 300.00 and equal 2.10% of total absolute
  P&L under the frozen D1 convention. The pooled Yes-minus-No trimmed-mean
  contrast remained positive at 14.1596.
- **Null/adverse findings:** Pooled reported win rates showed no separation;
  family-equal-weight mean win rate mildly favored No; temporal direction was
  inconsistent; June materially reversed the pooled P&L direction; and the
  P&L advantage attenuated sharply in the higher entry-price strata.
- **Interpretation limits:** D is exploratory discovery evidence, not
  independent validation or a live-money edge claim. Entry-price analysis is
  robustness analysis, not evidence of causality. Family-aware results do not
  prove independence. Category remains context only. The missing registered
  category-by-side diagnostic was completed explicitly and outcome-free
  rather than silently altering the frozen execution report. No alternate
  side grouping, threshold, subgroup, temporal boundary, category-outcome
  candidate, or paired-family selection rule is introduced.
- **Candidate status:** INCONCLUSIVE — pooled P&L separation is economically
  nontrivial, survives trimming, remains positive across all four frozen
  entry-price strata, and is supported by family-aware P&L sensitivities.
  However, pooled reported win-rate separation is absent and temporal
  robustness materially reverses in June with substantial month-to-month
  heterogeneity. The registered stable side/outcome relationship is therefore
  not consistently supported across the complete prespecified evidence.
  D1-002 remains discovery evidence and is not promoted to V1.
- **V1 accessed:** NO

---

## D1-003 — Entry Price vs paper outcomes

### PRE-EXECUTION REGISTRATION

- **State:** REGISTERED / NOT YET EXECUTED.
- **Candidate family:** Entry-price family — entry-price/outcome relationship.
  `entry_price` is not part of the Tradeability Score / spread / liquidity /
  volume_24h correlated feature family represented by D1-001.
- **Exact question:** Within frozen D, does recorded `entry_price` exhibit a
  stable relationship with paper-trade outcomes, and does any observed
  relationship remain materially coherent across the prospectively fixed
  continuous, D0-quartile, temporal, frozen-family, trade-side, and P&L-outlier
  views specified below?
- **Prior exposure / novelty limitation:** D1-003 is not outcome-naive with
  respect to entry-price context. The entry-price quartile boundaries were
  frozen outcome-blind in D0, but D1-001 subsequently reported score/outcome
  behavior within those entry-price strata and D1-002 subsequently reported
  side/outcome behavior within the same strata. Those earlier analyses exposed
  outcome behavior across entry-price contexts before D1-003 registration.
  Therefore D1-003 must not be represented as an independently generated or
  outcome-naive entry-price hypothesis. This registration does not infer an
  expected direction from those previously observed D results.
- **Predictor(s):** Primary predictor = existing recorded `entry_price`.
  No alternate price field, transformed price proxy, outcome-derived price
  variable, or post-hoc interaction becomes part of the primary predictor.
- **Expected direction:** None prespecified. D1-003 is two-sided. Direction may
  be described only after execution and may not be retroactively converted
  into a prospectively predicted direction.
- **Transformation / comparison rule:** Two frozen views:
  (1) continuous `entry_price`, using Pearson and Spearman association with
  numeric outcomes where mathematically applicable; and
  (2) the existing outcome-blind D0 quartile boundaries:
  Q1=0.7025, median=0.8675, Q3=0.9537, producing four fixed entry-price
  strata. These boundaries may not be moved, merged, split, or optimized
  after D1-003 outcomes are inspected. The quartile view is descriptive /
  robustness evidence for the same entry-price candidate family, not four
  independent candidates.
- **Outcome metric(s):** `trade_won` and `trade_pnl`. For continuous
  `entry_price`, report Pearson and Spearman association with numeric
  `trade_won` and `trade_pnl`. For each fixed D0 entry-price stratum report
  n, win rate, and P&L ordinary mean, median, and frozen 10% symmetric
  trimmed mean when eligible. Nominal significance alone is not validation.
- **Population:** Frozen D only: n=396, exact frozen trade-id SHA-256
  `ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e`.
  D membership must be obtained from the frozen D identity already used by
  the v1.1 family detector / D1 execution tooling; do not reconstruct D with
  a new date-only shortcut.
- **Exclusions:** No discretionary exclusions. A row may be excluded from a
  specific statistic only when a field required for that statistic is missing
  or invalid, and every such exclusion must be counted and disclosed. No
  exclusion based on outcome magnitude, family membership, category, month,
  side, entry-price level, or whether the result supports the candidate.
- **Required fields:** `trade_id`, `entry_price`, `trade_won`, `trade_pnl`,
  `entry_date`, `side`, `category`, plus the frozen v1.1 event-family
  assignment. `resolution_date` may be carried only as frozen-D provenance,
  not to reconstruct or alter D membership.
- **Missing-data rule:** No silent deletion. Report required-field missingness
  and usable n separately for each statistic. Frozen family derivation uses
  its existing explicit handling rather than dropping difficult markets.
- **Raw n before exclusions:** 396.
- **Family/dependence treatment:** Report raw-trade results and frozen family
  structure: represented-family count, largest-family concentration, and
  whether an apparent direction is concentrated in a small number of
  families. For the prospectively fixed family-equal-weight sensitivity,
  aggregate frozen D to one row per frozen v1.1 `family_key` using within-family
  arithmetic means of `entry_price`, `trade_won`, and `trade_pnl`; report
  Pearson and Spearman associations between family-mean entry price and each
  family-mean outcome. Each represented family receives one row regardless
  of family size. Family-aware results are sensitivity analyses and are not
  proof of independent observations.
- **Temporal treatment:** Use the already-fixed D0 entry-date calendar-month
  cohorts: June, July, August, September 2026. Within each month report
  continuous Pearson/Spearman entry-price association with `trade_won` and
  `trade_pnl` where mathematically usable. Also report month n, win rate, and
  `trade_pnl` ordinary mean, median, and frozen 10% symmetric trimmed mean
  when usable n >= 10; if usable n < 10, report mean and median and mark the
  trimmed mean unavailable. No outcome-driven temporal boundary or scanner
  cohort may be introduced after execution.
- **Trade-side robustness:** Because D1-002 has already established that side
  composition and P&L behavior can differ, report the continuous entry-price
  association with `trade_won` and `trade_pnl` separately within the existing
  recorded `Yes` and `No` groups where mathematically usable. This is a
  prespecified robustness view of D1-003, not a new side candidate or a
  post-hoc interaction search. The side labels may not be recoded or
  regrouped.
- **Entry-price treatment:** `entry_price` is the primary predictor in
  D1-003; therefore there is no separate adjustment of entry price for itself.
  The continuous view is primary and the frozen D0 quartile view is the
  prespecified nonlinear/descriptive robustness view. No new entry-price
  threshold may be introduced from observed D1-003 outcomes.
- **P&L outlier treatment:** For every reported P&L grouping with usable
  n>=10, report ordinary mean, median, and frozen 10% symmetric trimmed mean.
  If n<10, report mean and median and mark trimmed mean unavailable. For the
  complete usable D1-003 population, report the sum of the three largest
  absolute `trade_pnl` magnitudes divided by total absolute P&L, using the
  same frozen D1 concentration convention as D1-001 and D1-002. Outlier
  sensitivity does not replace raw results.
- **Category treatment:** Category composition may be reported as
  context/concentration only. D1-003 does not authorize category-specific
  outcome comparisons, category-derived thresholds, or a category/outcome
  candidate.
- **Multiple-testing / interpretation discipline:** D1-003 is exploratory D
  evidence with explicit prior outcome exposure to entry-price contexts.
  Nominal significance, a monotonic-looking quartile pattern, or an attractive
  economic magnitude is not independent validation. Previously observed
  D0/D1 statistics cannot be treated as external anchors for V1.
- **Planned outputs:** Raw/usable n; missingness; continuous Pearson/Spearman
  entry-price associations with `trade_won` and `trade_pnl`; four fixed D0
  entry-price-stratum summaries; P&L mean/median/10%-trimmed mean; absolute
  P&L concentration; represented-family counts and family-equal-weight
  sensitivity; fixed calendar-month sensitivity; fixed recorded-side
  sensitivity; category composition context; adverse/null findings; economic
  magnitude; prior-exposure limitation; interpretation limits. No candidate
  ranking or V1 promotion is implied by execution.
- **Planned execution artifacts:**
  `L3_RESEARCH_ENGINES/market_selection/analysis/d1_003_entry_price_outcomes.py`
  and
  `L3_RESEARCH_ENGINES/market_selection/analysis/D1_003_entry_price_outcomes.md`.
- **Registration provenance:** Prepared after D1-002 results commit
  `a8a312663d2825f6efe70af39dd8111e51f56ea6` and before any D1-003
  outcome-facing execution.
- **Outcomes accessed for D1-003 execution:** NO.
- **D1-003 execution artifact created:** NO.
- **V1 accessed:** NO.

### POST-EXECUTION RECORD

- **State:** EXECUTED — Discovery D only.
- **Execution date/time:** 2026-10-03. First authorized attempt failed on a
  missing SciPy runtime dependency after an outcome column had been loaded into
  memory; no outcome value was observed or persisted and no report was created.
  After the environment-only dependency repair, the exact authorized artifact
  was rerun successfully.
- **Code/artifact SHA or commit:** Execution artifact SHA-256
  `b1a83601e0b1e14c6fe520bff0ba7c87dc7142153409225471b438adb5b3e9db`;
  runtime/dependency commit
  `b25bb56ee6583c378e99a06bf8d893a6df3fd664`; generated report SHA-256
  `71657984766c24eaf72d6c6f98eab3572c46c2ef18494a0a010911250ff2d711`.
- **Usable n:** 396/396 for `entry_price`, `trade_won`, and `trade_pnl`;
  required-field and parsed-value missingness was zero.
- **Families represented:** 207 frozen v1.1 families; largest family n=14;
  largest-family raw-trade concentration=3.5354%.
- **Category composition:** Other/Unknown 180 (45.45%); Geopolitical 105
  (26.52%); Crypto Long-Duration 64 (16.16%); Sports 17 (4.29%);
  Political 15 (3.79%); Macro/Economic 14 (3.54%); Entertainment 1
  (0.25%). Category is context only; no category-specific outcome comparison
  was executed.
- **Temporal coverage:** Frozen June-September 2026 cohorts: June n=45,
  July n=108, August n=163, September n=80.
- **Observed result:** Higher recorded entry price was positively associated
  with `trade_won` (Pearson=+0.382227; Spearman=+0.379808) but showed a
  divergent relationship with `trade_pnl`: Pearson=-0.033681 and
  Spearman=-0.412216. The rank relationship therefore showed higher entry
  prices associated with more frequent wins but lower-ranked realized P&L.
- **Economic magnitude:** Fixed D0 quartile win rates rose from 63.64% in Q1
  to 75.76%, 91.92%, and 98.99% through Q4. Median P&L moved in the opposite
  direction from +52.67 in Q1 to +23.46, +6.95, and +2.09 in Q4. Ordinary
  mean P&L was non-monotonic (+7.2152, -3.5734, -0.2431, +1.3840), so the
  observed economic structure is not adequately summarized by mean P&L alone.
- **Entry-price / nonlinear sensitivity:** The frozen D0 quartiles preserved
  the strong monotonic rise in win rate and monotonic decline in median P&L.
  Frozen 10% trimmed P&L means were +9.6530, +2.3401, +7.9709, and +2.3248,
  which were not monotonic. No new threshold or transformed price predictor
  was introduced.
- **Trade-side sensitivity:** The positive entry-price/win rank association
  remained in both recorded sides: Yes Spearman=+0.316642 and No
  Spearman=+0.431057. The negative entry-price/P&L rank association also
  remained in both: Yes Spearman=-0.464321 and No Spearman=-0.363261.
- **Family/dependence sensitivity:** Equal-weight frozen-family results retained
  the same directional rank pattern across 207 families: family-mean
  entry-price vs `trade_won` Spearman=+0.382494 and vs `trade_pnl`
  Spearman=-0.306146. These are sensitivity results and do not prove
  independent observations.
- **Temporal sensitivity:** All four frozen months retained positive
  entry-price/win Spearman associations: June +0.465321, July +0.350980,
  August +0.403768, September +0.337502. All four retained negative
  entry-price/P&L Spearman associations: June -0.369365, July -0.548783,
  August -0.344260, September -0.384534. Monthly ordinary P&L means and
  trimmed means remained heterogeneous, including a negative August mean and
  trimmed mean.
- **Outlier sensitivity:** Total realized P&L=473.48; total absolute
  P&L=14,273.48. The three largest absolute P&L magnitudes summed to 300.00,
  equal to 2.1018% of total absolute P&L under the frozen D1 convention.
- **Prior-exposure limitation:** D1-003 is not outcome-naive. D1-001 and
  D1-002 had already exposed outcome behavior across entry-price contexts
  before D1-003 registration. The observed direction therefore cannot be
  represented as independently generated validation.
- **Null/adverse findings:** Entry-price/P&L Pearson association was near zero
  (-0.033681) despite the materially negative Spearman association
  (-0.412216); ordinary quartile mean P&L was non-monotonic; trimmed quartile
  P&L was also non-monotonic; monthly P&L levels were heterogeneous. The
  positive win-rate relationship therefore does not imply monotonically
  improving realized profitability as entry price rises.
- **Interpretation limits:** D1-003 is exploratory Discovery-D evidence only.
  It does not establish causality, independence, predictive superiority, or
  live-money edge. Continuous and fixed-quartile views are one candidate
  family; temporal, side, family, and outlier views are robustness
  sensitivities rather than separate discoveries. No observed D1-003 effect
  is independent validation and no V1 promotion is implied by this execution.
- **Candidate status:** DISCOVERY SIGNAL — NOT YET RANKED / NOT PROMOTED.
  The entry-price candidate shows a temporally, side-, and family-directionally
  coherent divergence between win frequency and ranked P&L, but candidate
  ranking and any decision to freeze a V1 primary remain separate governance
  steps.
- **V1 accessed:** NO

---

**Append-only rule:** once an entry has been executed, preserve both its
pre-execution specification and its observed result. Corrections must be
added explicitly; do not silently rewrite the historical test.

---

## D1 Discovery Candidate Ranking — 2026-10-03

### Governance state

- **Discovery population:** frozen D only.
- **Candidate set ranked:** D1-001, D1-002, D1-003.
- **Additional D candidate required before ranking:** NO. The frozen protocol
  defines how to rank multiple surviving candidate families but does not
  prescribe a minimum candidate count beyond that condition.
- **Ranking method:** qualitative application of the prospectively frozen
  hierarchy, in order:
  1. discovery-internal consistency / robustness;
  2. breadth across time and frozen families;
  3. economic relevance;
  4. simplicity / interpretability;
  5. operational usefulness.
- **Numeric candidate score introduced:** NO.
- **V1 accessed:** NO.

### Rank 1 — D1-003: Entry-price family

- **Decision:** RANK 1 / SELECTED AS DISCOVERY PRIMARY FOR V1 SPECIFICATION.
- **Discovery-internal consistency / robustness:** strongest of the three
  candidate families. Entry price showed a positive rank association with
  `trade_won` and a negative rank association with `trade_pnl`. The fixed D0
  quartiles showed monotonically increasing win rate and monotonically
  decreasing median P&L as entry price increased. Ordinary and trimmed mean
  P&L were not monotonic, so the candidate is specifically a divergence
  structure rather than a claim that higher or lower entry price monotonically
  improves realized profitability.
- **Breadth across time and frozen families:** the directional rank structure
  remained coherent in all four frozen calendar months, within both recorded
  trade sides, and under the equal-weight frozen-family sensitivity across 207
  represented families. The largest frozen family contained 14 trades
  (3.5354% of D).
- **Economic relevance:** the structure is economically interpretable because
  win frequency rose sharply across the fixed entry-price quartiles while
  median realized P&L compressed sharply. This identifies a potentially
  important distinction between frequency of winning and economic payoff.
- **Simplicity / interpretability:** `entry_price` is an existing directly
  recorded scalar predictor. The primary continuous predictor requires no
  derived model, optimized threshold, or post-hoc feature construction.
- **Operational usefulness:** if independently replicated, entry-price/payoff
  structure could inform how LRS-1 interprets market tradeability and paper
  outcomes without changing the canonical Tradeability Score during this
  discovery round.
- **Limitations affecting promotion:** D1-003 is not outcome-naive because
  D1-001 and D1-002 previously exposed outcomes across entry-price contexts.
  Its Discovery-D result is not independent validation. Pearson association
  with `trade_pnl` was near zero, quartile ordinary and trimmed mean P&L were
  non-monotonic, and monthly P&L levels remained heterogeneous.
- **Selection meaning:** Rank 1 selects D1-003 only as the candidate for which
  an exact V1 validation specification may now be prospectively frozen. It
  does not itself constitute V1 validation, successful replication, causal
  evidence, predictive superiority, or live-money edge.

### Rank 2 — D1-002: Trade-side family

- **Decision:** RANK 2 / NOT SELECTED FOR V1 IN THIS ROUND.
- **Discovery-internal consistency / robustness:** pooled P&L favored Yes and
  survived the frozen trimmed-mean and family-aware sensitivities, but pooled
  win-rate separation was absent and temporal robustness materially reversed
  in June.
- **Breadth across time and frozen families:** family-aware P&L evidence
  supported the pooled direction and the Yes-minus-No P&L difference remained
  positive across all four fixed entry-price strata, but calendar-month
  direction was materially heterogeneous.
- **Economic relevance:** pooled Yes-minus-No P&L differences were
  economically nontrivial, but the advantage attenuated substantially at
  higher entry prices.
- **Simplicity / interpretability:** recorded Yes/No side is simple and
  directly observable.
- **Operational usefulness:** potentially useful if independently replicated,
  but weaker temporal robustness places it below D1-003 under the frozen
  ranking hierarchy.
- **V1 consequence:** D1-002 is not tested on V1 if D1-003 is opened as the
  primary. If D1-003 later fails V1, V1 fails; D1-002 may not then be tested
  on that same V1 population.

### Rank 3 — D1-001: Tradeability feature family

- **Decision:** RANK 3 / NOT SELECTED FOR V1 IN THIS ROUND.
- **Discovery-internal consistency / robustness:** continuous score/outcome
  associations were weak and the fixed score split produced essentially no
  win-rate separation. Although pooled High-score P&L exceeded Low-score P&L,
  the relationship was materially heterogeneous across fixed entry-price and
  temporal views.
- **Breadth across time and frozen families:** family equal-weighting did not
  materially strengthen the continuous relationship, and temporal direction
  was inconsistent.
- **Economic relevance:** the pooled High-versus-Low P&L difference was
  economically nontrivial and survived trimming, but the lack of stable
  relationship across the prespecified robustness views materially weakens
  the candidate under the first two ranking criteria.
- **Simplicity / interpretability:** Tradeability Score is operationally
  interpretable but is a composite feature family rather than a single raw
  predictor.
- **Operational usefulness:** directly relevant to LRS-1's existing market
  selection architecture, but operational relevance does not override the
  higher-priority robustness and breadth criteria.
- **V1 consequence:** D1-001 is not selected for V1 in this round.

### Ranking decision

The prospectively frozen ranking hierarchy therefore yields:

1. **D1-003 — Entry-price family**
2. **D1-002 — Trade-side family**
3. **D1-001 — Tradeability feature family**

D1-003 is selected as the sole Discovery-D primary candidate to proceed to
**prospective V1 specification**.

This ranking does **not** open V1 and does **not** by itself promote any
observed D effect to validated evidence. Before any V1 outcome is accessed,
the exact D1-003 V1 specification must separately freeze the predictor,
transformation/buckets, expected direction, population/exclusions, family
treatment, temporal treatment, entry-price treatment, outcome metrics,
primary success criterion, sensitivity analyses, rejection/inconclusive
criteria, and exact analysis code/version.

Until that separate freeze is complete:

- **V1 validation opened:** NO.
- **V1 outcome values accessed:** NO.
- **V1 analysis executed:** NO.
- **D1-003 independently validated:** NO.

### Registry-summary status clarification

The summary table near the creation header still displays D1-003 as
`REGISTERED / NOT YET EXECUTED` with result state `PENDING EXECUTION`.
That row reflects its pre-execution registry state and was not silently
rewritten after execution. The canonical D1-003 POST-EXECUTION RECORD records
the executed Discovery-D result, and this ranking record uses that executed
record. This clarification preserves the append-only history rather than
retroactively rewriting the earlier summary row.

---

**Append-only continuation:** this ranking record is a governance decision
made after completion of D1-001, D1-002, and D1-003 Discovery-D analyses and
before any V1 outcome access. Future V1 results must not rewrite this ranking
decision.

---

## D1-003 V1 VALIDATION — POST-EXECUTION RECORD — 2026-10-03

### Governance state

- **Discovery candidate:** D1-003 — Entry-price family.
- **Protected validation population:** V1.
- **Protected V1 n:** 80.
- **V1 trade-id SHA-256:** `a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141`.
- **Frozen V1 specification SHA-256:** `96362fa3025a11a5fcc4c4cf6d21674f1ccf86a4535b4d34e6b019ba8bfb14f7`.
- **Executed validation script SHA-256:** `b8965e37c40308801c3d7cc3b39832c8bd311ff0cf0d94370736ae336453f99d`.
- **Sealed validation report SHA-256:** `20a3a3b5a75f5485b1ca5904dff95ad45bf8b3e90f4482e85ff3ba9fa56b39ca`.
- **SciPy version:** `1.18.1`.
- **Discovery-D outcomes used in V1 validation:** NO.
- **Post-open methodology modification:** NO.
- **V1 rerun authorized:** NO.

### Execution history

The first authorized V1 execution attempt, before the frozen-identity repair,
failed closed during protected-population construction because the original
runtime loader defined V1 as the complement of frozen D within the current
closed ledger. Subsequent ledger growth made that complement larger than the
already-frozen V1 n=80. That attempt produced no validation classification and
no validation report.

The original protected V1 identities were then recovered outcome-blind and
verified against the V1 trade-id SHA-256 that had already been frozen before
V1 execution. The validation loader was repaired to select the exact immutable
80-trade manifest rather than a growing complement-of-D population. The repair
did not change the frozen predictor, outcomes, statistical tests, success
criterion, family sensitivity, or classification precedence.

The repaired script was independently audited, committed, deployed to Pi3,
verified byte-for-byte, separately authorized for the repaired SHA, and then
executed once against the protected V1 population.

### Primary validation result

| Outcome | n | Pearson | Spearman | Spearman two-sided p |
|---|---:|---:|---:|---:|
| `trade_won` | 80 | 0.448833 | 0.404333 | 0.000199 |
| `trade_pnl` | 80 | -0.061579 | -0.528386 | 0.000000 |

The prospectively frozen hypothesis required both:

1. a positive Spearman relationship between `entry_price` and `trade_won`; and
2. a negative Spearman relationship between `entry_price` and `trade_pnl`.

Both primary relationships replicated in the required directions and satisfied
the frozen significance criterion.

### Frozen family sensitivity

Across 57 represented V1 families:

- `entry_price` vs `trade_won` Spearman: **+0.390634**.
- `entry_price` vs `trade_pnl` Spearman: **-0.430349**.
- Largest family size: **8 trades**.
- Largest-family raw-trade concentration: **10.0%**.

Both family-equal-weight relationships retained the prespecified directions
required by the frozen PASS precedence.

### Disclosure-only robustness context

- Fixed D0 entry-price quartile win rates increased from **66.67%** in Q1 to
  **100.00%** in Q4.
- Temporal P&L rank direction was negative in July, August, and September.
  July contained only four V1 observations.
- August `trade_won` rank association was near zero; September retained the
  positive win and negative P&L rank directions.
- Recorded-side sensitivity retained a positive win-rank direction for both
  No and Yes trades. P&L rank association was strongly negative for No trades
  and zero for Yes trades.
- Total realized V1 P&L was **474.30**; total absolute P&L was **2,274.30**.
  The three largest absolute P&L observations summed to **300.00**, or
  **13.1909%** of total absolute P&L.
- These analyses were disclosure-only under the frozen specification and did
  not alter the primary classification.

### V1 classification

**PASS**

Under the prospectively frozen V1 specification, D1-003 independently
replicated the prespecified entry-price divergence structure in the protected
V1 population: higher recorded entry price retained a positive rank
relationship with winning and a negative rank relationship with realized P&L.

### Interpretation boundary

This PASS validates the prospectively frozen directional replication criterion
for D1-003 within protected V1. It does **not** establish causality, universal
generalization, live-money profitability, or a production trading rule.

No Tradeability Score, scanner, admission, sizing, or live-trading rule is
changed by this validation result.

### Final V1 state

- **V1 validation opened:** YES.
- **V1 outcome values accessed:** YES.
- **V1 analysis executed:** YES.
- **V1 classification produced:** PASS.
- **D1-003 independently validated under frozen V1 criterion:** YES.
- **V1 report created:** YES.
- **V1 rerun authorized:** NO.

---

**Append-only continuation:** preserve this V1 result and its sealed report as
the canonical result of the one-shot protected validation. Any future research
question, replication population, production interpretation, or methodology
change must be governed separately and must not rewrite this V1 result.
