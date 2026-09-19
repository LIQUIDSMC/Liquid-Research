# EXPERIMENT v2 -- PRE-INFERENCE METHODOLOGY REVISION

**Status:** DRAFT / OUTCOME-BLIND / NOT FROZEN / IMPLEMENTATION NOT AUTHORIZED

## Section 1 -- Scope and Reason for Experiment v2

Experiment v2 exists to resolve the implementation-blocking Gate-2 evaluation-domain specification omission documented above. Frozen Experiment v1 requires a current Gate-2 evaluation domain for episode censoring, `K_total`, `T_classified`, turnover, persistence, and related Gate-2 resolution, but does not deterministically define that domain's temporal boundaries. Because those quantities can alter Window Evaluation and Instrument Path disposition, resolving the omission requires an Experiment-v2 methodology revision rather than an implementation-level interpretation.

Experiment v2 is being specified under outcome-blind change control. No conditioned LRS-4 HIGH-versus-LOW comparison, `Delta_regime`, conditioned forward-return result, bootstrap interval, K7 conditioned result, leave-one-instrument-day-out conditioned effect, or reconstructible equivalent has been inspected or used to select the Experiment-v2 methodology.

Experiment v1 remains frozen as the historical predecessor specification. Experiment v2 does not retroactively repair, reinterpret, or reopen Experiment v1. Where Experiment v2 explicitly identifies a frozen Experiment-v1 rule as `SUPERSEDED ONLY WHERE SPECIFIED` or otherwise supplies an explicit v2 resolution, that v2 rule governs Experiment-v2 execution only. Frozen Experiment-v1 methodology not explicitly superseded remains inherited unchanged where applicable.

Previously completed Stage-1 primitives remain reusable only to the extent that their frozen behavior is unaffected by the Experiment-v2 revision and their interfaces satisfy the final Experiment-v2 dependency and authority model. Reuse does not itself establish authorization for Gate-2 implementation or conditioned-outcome access.

Experiment v2 is not frozen by the presence of this section or by completion of any individual subsection. Gate-2-dependent implementation remains unauthorized until the complete Experiment-v2 methodology, inheritance/interface audit, implementation invariants, and required-test specification have undergone the final whole-document consistency audit and Experiment v2 has been explicitly declared `FROZEN`.

Until that declaration, any newly identified methodological ambiguity that could alter population membership, temporal-domain construction, regime admissibility, episode topology, Gate-2 diagnostics, Instrument Path routing, final observation disposition, or downstream inferential authorization must be resolved in the methodology before implementation proceeds.

## Section 2 -- Gate-2 Evaluation-Domain Object Model

Experiment v2 resolves the missing Gate-2 evaluation-domain specification through an ordered set of authoritative objects. These objects define current-Window target-observation membership, temporal-domain geometry, environmental admissibility, structural episode topology, and the later final-path observation projection without allowing a downstream result to redefine an upstream population.

### D0 -- Window Constructibility

For instrument `s` and an entered regime window `W`, construct `D1_W(s)` according to D1 below. Window constructibility is then determined solely by whether that current-Window target-observation population is nonempty.

If

`|D1_W(s)| = 0`,

then

`WINDOW_CONSTRUCTIBILITY = FAIL`

with reason

`NO_TARGET_OBSERVATION_POPULATION`.

D0 is evaluated before Gate 2. It is not a Gate-2 diagnostic, is distinct from excessive regime ineligibility, and introduces no additional numeric minimum-observation threshold. Any nonempty `D1_W(s)` passes D0 constructibility and proceeds to D2 and the remaining current-Window evaluation machinery, subject to their own independent requirements.

A D0 failure is terminal for the currently entered Window Evaluation and for the Instrument Path. It does not invoke the F1 directional fallback mechanism and does not synthesize a Gate-2 disposition, directional trigger, or fallback authorization.

The terminal reason remains `NO_TARGET_OBSERVATION_POPULATION` under either of two distinct provenance cases: (C1) candidate observations existed for one or more relevant instrument-days but every such day was excluded from `D1_W(s)` by the W-specific aggregate source-history requirement; or (C2) no candidate observations existed for the entered window. These provenance cases must remain distinguishable in diagnostics even though they share the same D0 terminal reason.

No downstream regime-validity result, D3 admissibility result, Gate-2 diagnostic, Instrument Path result, or final observation disposition may alter whether D0 passed or failed.

### D1 -- Current-Window Target-Observation Population

For instrument `s`, research day `d`, and a regime window `W` that has been legitimately entered by the Instrument Path, define `O_candidate(s,d,W)` as the inherited frozen LRS-3 observations on day `d` that enter the current Window Evaluation solely because `W` was entered. Candidate membership is upstream of source-history authorization, regime classification, and Gate-2 resolution.

Accordingly, membership in `O_candidate(s,d,W)` must not depend on endpoint source-history authorization, aggregate `SH(s,d,W)`, `REGIME_STATE_VALID`, `D3_ADMISSIBLE`, any Gate-2 diagnostic or disposition, `SH_path`, or any final-path observation result.

For every `T in O_candidate(s,d,W)`, obtain `G(T)` using the inherited C10 mapping: the latest completed 5-minute grid endpoint satisfying strict `G < T`. Define

`G_candidate(s,d,W) = {G(T) : T in O_candidate(s,d,W)}`,

with duplicate grid endpoints represented once for aggregate source-history authorization. Failure to obtain the required strict-C10 predecessor for a candidate observation is an integrity failure; it must not be converted into ordinary source-history or regime ineligibility.

`SH(s,d,W)` is a partial instrument-day-window function. It is defined only when `|O_candidate(s,d,W)| > 0`. For a nonempty candidate set,

`SH(s,d,W) = ELIGIBLE`

if and only if every unique endpoint in `G_candidate(s,d,W)` satisfies the inherited W-specific endpoint source-history authorization requirements. Otherwise,

`SH(s,d,W) = INELIGIBLE`.

When `|O_candidate(s,d,W)| = 0`, `SH(s,d,W)` is undefined. Undefined `SH(s,d,W)` must not be coerced to `ELIGIBLE` or `INELIGIBLE`.

The authoritative current-Window target-observation population is

`D1_W(s) = union over d such that |O_candidate(s,d,W)| > 0 and SH(s,d,W) = ELIGIBLE of O_candidate(s,d,W)`.

Thus an instrument-day contributes either all of its current-W candidate observations to `D1_W(s)` or none of them according to the aggregate W-specific source-history requirement. `D1_W(s)` contains observations, not grid endpoints or instrument-days.

Candidate membership does not imply membership in `D1_W(s)`, and membership in `D1_W(s)` does not imply valid regime classification or D3 admissibility. Those are downstream questions. `SH_path` is also downstream of final Instrument Path resolution and has no authority over construction of `O_candidate`, `G_candidate`, `SH(s,d,W)`, or `D1_W(s)`.

For the current Window Evaluation, `D1_W(s)` is the observation population from which the G-NUMERIC.1-.3 observation counts and exposures are derived. No regime-assignment result may be used to construct or filter `D1_W(s)`.

### D2 -- Fixed Gate-2 Temporal Domain

D2 is defined only after D0 has established that `D1_W(s)` is nonempty. Let

`T_first = min D1_W(s)`

and

`T_last = max D1_W(s)`.

Using the inherited strict-C10 mapping, define

`G_first = G(T_first)`

and

`G_last = G(T_last)`.

With the frozen grid interval `Delta = 5 minutes`, the authoritative discrete Gate-2 temporal domain is

`D2_W(s) = {G_first, G_first + Delta, ..., G_last}`,

including both endpoints. The corresponding continuous temporal domain is

`(G_first, G_last + Delta]`.

D2 is constructed exactly once from the D1 extrema using the inherited C10/C11 temporal conventions. Because C10 requires strict `G < T`, an observation occurring exactly on a grid timestamp maps to the preceding completed endpoint and cannot use the state calculated at its own timestamp.

The D2 grid is temporally continuous from `G_first` through `G_last`. Interior observations, instrument-days, or endpoints excluded from D1 by aggregate source-history qualification do not create holes in D2 once its boundaries have been established. Conversely, candidate observations excluded from D1 cannot establish or extend the leading or trailing D2 boundary.

D2 is immutable for the remainder of the current Window Evaluation. D3 admissibility, regime invalidity, episode construction, Gate-2 diagnostics, and downstream observation eligibility may classify or partition time within D2 but may not shrink, expand, re-anchor, or otherwise reconstruct its temporal boundaries.

A nonempty D1 may legitimately produce the minimum D2 geometry of a single grid cell when `G_first = G_last`. This one-cell domain remains subject to the same D3, episode-boundary, censoring, and Gate-2 rules as any larger D2 domain.

### D3 -- Endpoint Environmental Admissibility

For every grid endpoint `G in D2_W(s)`, Experiment v2 defines one authoritative current-Window environmental-admissibility value:

`D3_ADMISSIBLE(G,W) = SH_AUTHORIZED(G,W) AND REGIME_STATE_VALID(G,W)`.

`SH_AUTHORIZED(G,W)` is the inherited endpoint-level, W-specific source-history authorization. It determines whether the classifier is authorized to interpret the endpoint at all. Aggregate instrument-day `SH(s,d,W)` is not a substitute for this endpoint-level object, and final-path `SH_path` has no authority in D3 construction.

Conditional on `SH_AUTHORIZED(G,W) = TRUE`, `REGIME_STATE_VALID(G,W)` indicates that the inherited measurement, RVOL, threshold-learning, and E4 classification machinery validly produces a HIGH or LOW regime state rather than INVALID. The dependency order is therefore source-history authorization first, followed by the inherited measurement/threshold/classification validity machinery, followed by the D3 conjunction.

If `SH_AUTHORIZED(G,W) = FALSE`, `D3_ADMISSIBLE(G,W) = FALSE` regardless of whether a HIGH or LOW state could be mechanically computed from available values. Such a mechanically computed state has no Experiment-v2 classification authority. If source history is authorized but the inherited regime-state machinery is invalid, `D3_ADMISSIBLE(G,W) = FALSE` for that independent reason.

D3 must be instantiated for every endpoint in the fixed D2 grid. It is not restricted to endpoints represented by observations in `D1_W(s)`. Consequently, interior time associated with observations or instrument-days excluded from D1 may still contribute to Gate-2 structural morphology when its endpoint is independently D3-admissible.

D3 does not resize or reconstruct D2. A FALSE D3 cell remains part of D2 but is environmentally inadmissible for regime classification and structural episode continuity. Its underlying failure provenance must remain auditable so that source-history unauthorized, measurement-invalid, threshold-invalid, and other inherited regime-invalid causes are not silently collapsed into an interchangeable upstream or downstream exclusion class.

Current-Window observation regime eligibility is downstream of both D1 membership and authoritative D3. For `T in D1_W(s)`, the strict-C10 endpoint `G(T)` is regime-eligible for that Window Evaluation if and only if `D3_ADMISSIBLE(G(T),W) = TRUE`. This observation-level use of D3 does not alter D1 membership or D2 geometry.

### D4 -- Structural Episode Topology and Boundary Censoring

For each instrument `s` and entered window `W` that reaches D4, construct one authoritative structural episode topology by a single chronological sweep over the complete D3 timeline on `D2_W(s)`. An episode is a maximal contiguous run of D3-admissible grid cells carrying the same authoritative HIGH or LOW regime state.

Every structural episode boundary must have one of exactly three causes:

- `STATE_CHANGE`
- `D3_INADMISSIBILITY`
- `D2_BOUNDARY`

A HIGH-to-LOW or LOW-to-HIGH `STATE_CHANGE` is an observed episode termination and does not create censoring.

A D3-inadmissible grid cell is an internal terminating discontinuity. It breaks episode continuity, is not itself an episode, and never creates a censor boundary. Episode construction must not bridge, search backward across, or otherwise join same-state runs across a D3-inadmissible cell.

Only a literal `D2_BOUNDARY` may create censoring. Left-edge censoring is resolved using the inherited F4 prehistory-trace logic without extending D2 itself. If the inherited F4 prehistory trace identifies a state transition or an inherited validity discontinuity before the left-edge episode, that episode's origin is observed rather than left-censored. If the same state persists through the earliest auditable pre-D2 boundary without an observed terminating event, the episode is left-censored.

Any episode that reaches `G_last` is right-censored at the literal right D2 boundary. No information after D2 may be used to rescue, remove, or reinterpret that right-censor flag.

Left- and right-censor status are independent attributes. A one-cell episode may therefore be left-censored, right-censored, both, or neither according to its actual boundary evidence. Its observed duration remains one grid interval, `5 minutes`; however, right censoring prevents the unobserved terminal duration from being inferred solely from that observed one-cell duration.

D4 is constructed from the full D3 timeline, not by filtering the timeline back through `D1_W(s)`. Structural episode counts, including `K_HIGH`, `K_LOW`, and `K_total`, and the classified-time quantity `T_classified` are therefore derived from the authoritative D3/D4 environmental timeline. D1 remains the separate current-Window observation population for observation-based Gate-2 diagnostics.

D4 may partition and summarize the fixed D2 domain but may not resize D2, alter any D3 value, or rebuild either upstream object. Gate-2 morphology diagnostics must consume this authoritative D4 topology rather than independently reconstructing episodes from observations or regime labels.

### Final-Path Observation Projection

Final observation projection occurs only after the Instrument Path has completed. `InstrumentPathResult` is a discriminated path-level result whose detailed routing and terminal-state interface is specified later in Experiment v2. For the purposes of final observation projection, only `InstrumentPathResult = VIABLE` establishes a realized regime window.

Define `W*` exclusively as the unique realized regime window of a `VIABLE` Instrument Path. A D0-terminal or Gate-2-terminal path has no `W*`. The last window evaluated on a non-VIABLE path is not `W*`, and no non-VIABLE path receives final observation projection.

For a VIABLE path, final day-level `SH_path(s,d)` is evaluated as the source-history stage gate before projecting observations on research day `d`. `SH_path(s,d)` is defined according to the Experiment-v2 evidentiary-window aggregation rule specified by the K1.2-A v2 supersession (Section 4.5 below). Undefined `SH_path(s,d)` is permitted only for a day containing zero inherited LRS-3-eligible observations requiring final disposition; it is day-level bookkeeping and must never be coerced into an observation status.

For an inherited LRS-3-eligible observation `T` on a VIABLE path:

1. If `SH_path(s,d) = INELIGIBLE`, then

   `FinalObservationDisposition(T) = LRS4_SOURCE_HISTORY_INELIGIBLE`.

2. If `SH_path(s,d) = ELIGIBLE`, map `T` to `G(T)` using the inherited strict-C10 rule and read the authoritative realized-window D3 value at `(G(T), W*)`.

   If `D3_ADMISSIBLE(G(T),W*) = FALSE`, then

   `FinalObservationDisposition(T) = LRS4_REGIME_INELIGIBLE`.

   If `D3_ADMISSIBLE(G(T),W*) = TRUE`, then

   `FinalObservationDisposition(T) = LRS4_ELIGIBLE`.

`LRS3_INELIGIBLE` remains an upstream inherited status and is not reclassified by the LRS-4 final projection.

The realized-window D3 value used here must be the same authoritative D3 artifact produced during the Window Evaluation of `W*`. Final projection may invoke the same low-level strict-C10 observation-to-grid mapping primitive, but it must not recompute, regenerate, or independently reinterpret endpoint source-history authorization, RVOL, threshold history, regime state, or D3 admissibility. A missing realized-window D3 artifact, a missing required `(G,W*)` entry, or disagreement between final projection and the authoritative current-Window artifact is a methodology-integrity failure and must fail closed.

Only the authoritative D3 artifact from `W*` governs the regime component of final observation projection. Every D3 artifact from an entered window other than `W*` -- including the primary window when a fallback window becomes `W*` -- is historical Window-Evaluation evidence only; it may neither rescue nor veto the final disposition under `W*`.

Final `SH_path(s,d) = ELIGIBLE` does not replace or erase the endpoint-level source-history conjunct already embedded in `D3_ADMISSIBLE(G,W*)`. The final source-history stage gate and realized-window D3 authority remain methodologically distinct even when their expected Boolean implications are predictable.

`FinalObservationDisposition(T)` is categorical, not Boolean. Define the convenience predicate

`FinalEligible(T) := [FinalObservationDisposition(T) = LRS4_ELIGIBLE]`.

`FinalEligible(T)` is derived evidence only and does not replace the categorical final disposition as the authoritative observation-level result.

### Authority and Vocabulary

Experiment v2 applies three standing authority principles throughout the methodology.

**P1 -- Membership-language discipline.** A downstream result, diagnostic, disposition, or derived status must not define, reconstruct, or retroactively alter membership in an upstream population. When multiple eligibility layers are in scope, the bare term `eligibility` is insufficient; the applicable layer must be identified explicitly, such as inherited LRS-3 eligibility, source-history eligibility, current-Window regime eligibility, or final observation eligibility.

**P2 -- R-AUTHORITY.** Predictable equivalence or implication between two methodological objects does not make those objects interchangeable. Each object retains the authority assigned by its definition, index domain, dependency stage, and producer. A downstream consumer must use the authoritative object required by its interface rather than substitute another object merely because their values are expected to agree in a particular state.

**P3 -- Failure-layer preservation.** Window constructibility failure, source-history exclusion, endpoint environmental inadmissibility, Gate-2 failure, Instrument Path termination, and final observation exclusion are distinct methodological layers. They must retain their own provenance and must not be silently collapsed, promoted, or translated into one another.

`W*` is reserved exclusively for the unique realized window of a `VIABLE` `InstrumentPathResult`. A D0-terminal or Gate-2-terminal path has no `W*`; the last evaluated window on such a path is not a realized window.

The canonical Experiment-v2 authority vocabulary is:

- `SH_AUTHORIZED(G,W)` -- endpoint/window source-history authorization; authoritative permission for the W-specific classifier to interpret endpoint `G`.
- `SH(s,d,W)` -- partial instrument/day/window aggregate source-history result over the nonempty current-W candidate endpoint set; authoritative for D1 day inclusion only.
- `D1_W(s)` -- authoritative current-W target-observation population after W-specific aggregate source-history qualification.
- `D2_W(s)` -- authoritative fixed current-W Gate-2 temporal geometry constructed from D1 extrema.
- `REGIME_STATE_VALID(G,W)` -- conditional result of the inherited measurement, RVOL, threshold-learning, and regime-classification validity machinery after endpoint source-history authorization.
- `D3_ADMISSIBLE(G,W)` -- authoritative endpoint environmental-admissibility conjunction on D2.
- `D4_W(s)` -- authoritative current-W structural episode topology constructed from the complete D3 timeline.
- `Eligibility(T,W)` -- current-W observation regime-eligibility result for `T in D1_W(s)`, obtained from authoritative `D3_ADMISSIBLE(G(T),W)` after strict-C10 mapping; it is a Window-Evaluation object, not a final-path disposition.
- `E_W = (R_W, A_W, H_W)` -- completed Gate-2 result for the current Window Evaluation; `R_W` retains the complete Gate-2 reason set, `A_W` is the sole Instrument Path routing authority, and `H_W` is retained diagnostic evidence rather than an independent routing authority.
- `WindowEvaluationResult` -- discriminated current-W result: either D0 termination or completed Gate-2 result `E_W`; the two variants are non-coercible.
- `InstrumentPathResult` -- discriminated final path-level result. Its final interface distinguishes `VIABLE`, `GATE2_TERMINAL`, and `D0_TERMINAL`; only `VIABLE` establishes `W*`.
- `SH_path(s,d)` -- final day-level path-conditioned source-history stage gate, constructed only after the Instrument Path is finalized from the evidentiary-window aggregation rule.
- `W*` -- unique realized regime window on a VIABLE path only.
- `FinalObservationDisposition(T)` -- authoritative categorical final LRS-4 observation-level result after the finalized path, `SH_path` stage gate, strict-C10 mapping, and reuse of the authoritative realized-window D3 artifact.
- `FinalEligible(T)` -- derived Boolean convenience predicate equal to TRUE if and only if `FinalObservationDisposition(T) = LRS4_ELIGIBLE`; it has no independent decision authority.

The following control and provenance objects also retain distinct authority and must not be coerced into one another: `D0Termination`, `DiagnosticRecord`, `R_W`, `A_W`, `H_W`, `ApplicabilityStatus`, `BoundaryCause`, `CensoringStatus`, and `Episode`.

Objects with different index arity or semantic type are non-substitutable even when their realized values are predictably related. Each authoritative object has one authoritative producer within a Window Evaluation or final-path projection. Derived evidence may validate, reconcile, or report an authoritative result but may not acquire downstream decision authority from numerical agreement alone. Discriminated result variants must remain explicit and may not be coerced into synthetic equivalents.

These authority rules supplement the local invariants attached to individual methodology objects; they do not supersede or remove those local invariants.

## 3. Worked Boundary and Dependency Examples

Status: NON-NORMATIVE / ILLUSTRATIVE ONLY

The examples in this section illustrate already-defined Experiment-v2 rules and create no new methodology. If any example conflicts with a normative Experiment-v2 clause or an inherited clause not superseded by Experiment v2, the normative clause controls.

These examples may not create, modify, or resolve populations, thresholds, authority relationships, failure reasons, applicability states, Instrument Path transitions, censoring rules, source-history rules, observation-eligibility rules, or final observation dispositions. Their purpose is traceability and boundary verification only.

The `Illustrates:` field identifies the normative objects or clauses being exercised. It is a cross-reference, not an additional source of authority.

### Group A -- Strict-C10 Mapping and Candidate Endpoints

**Example 1 -- Observation immediately after a grid endpoint**
Illustrates: C10 strict predecessor mapping; C11 forward temporal cell; D1 candidate-endpoint construction.

Suppose completed 5-minute grid endpoints include `10:00` and `10:05`, and an inherited LRS-3 observation occurs at `T = 10:05:01`.

Strict C10 maps the observation to:

`G(T) = 10:05`.

The observation may consume the already-completed `10:05` endpoint because `10:05 < T`. Any current-Window source-history or D3 lookup for that observation therefore uses the authoritative `(10:05,W)` object.

This example does not establish whether that endpoint is source-history authorized or D3-admissible; it establishes only the strict-C10 mapping.

**Example 2 -- Observation exactly on the grid**
Illustrates: C10 exact-grid rule; C11 temporal-cell convention.

Suppose `T = 10:05:00` exactly.

The `10:05` endpoint does not satisfy `G < T` and therefore cannot be consumed by this observation. Assuming `10:00` is the immediately preceding completed endpoint:

`G(T) = 10:00`.

The newly calculated `10:05` state cannot be used for the observation occurring exactly at `10:05`.

**Example 3 -- Multiple observations map to one endpoint**
Illustrates: D1 `G_candidate(s,d,W)` construction; K1.2-A v2 candidate-evidence scope (Section 4.5 below).

Suppose three candidate observations on the same research day map under strict C10 to the same endpoint `G`.

All three observations remain members of `O_candidate(s,d,W)`, but `G_candidate(s,d,W)` contains `G` only once for aggregate source-history authorization.

Deduplicating the endpoint set does not deduplicate or otherwise modify the observation population.

**Example 4 -- Required strict predecessor is unavailable**
Illustrates: D1 integrity rule; failure-layer preservation.

Suppose a candidate observation exists but no required strict-C10 predecessor can be obtained.

This is a methodology-integrity failure.

It is not converted into:

`LRS4_SOURCE_HISTORY_INELIGIBLE`

or

`LRS4_REGIME_INELIGIBLE`.

No downstream status may be used to disguise failure to construct the required upstream mapping.

### Group B -- Candidate Population, Source History, and D0

**Example 5 -- Candidate observations exist and the day passes W-specific source history**
Illustrates: `O_candidate`; `SH(s,d,W)`; `D1_W(s)`.

Suppose day `d` contains candidate observations for entered window `W`, so `O_candidate(s,d,W)` is nonempty. Every unique endpoint in `G_candidate(s,d,W)` satisfies the required W-specific endpoint source-history authorization.

Then:

`SH(s,d,W) = ELIGIBLE`.

The day's candidate observations are admitted to `D1_W(s)`.

This does not imply that their mapped endpoints are D3-admissible.

**Example 6 -- Candidate observations exist but the day fails W-specific source history**
Illustrates: D0 provenance C1; aggregate `SH(s,d,W)`; D1 exclusion.

Suppose candidate observations exist for `W`, but at least one required unique candidate endpoint fails W-specific source-history authorization.

Then:

`SH(s,d,W) = INELIGIBLE`.

That instrument-day contributes no observations to `D1_W(s)` for that Window Evaluation.

If candidate observations existed across the relevant target population but every candidate-bearing day is excluded this way, `D1_W(s)` becomes empty and D0 terminates with:

`NO_TARGET_OBSERVATION_POPULATION`.

Its provenance records the C1 case: candidates existed, but source-history qualification excluded all of them.

**Example 7 -- No candidate observations exist**
Illustrates: D0 provenance C2; partial `SH(s,d,W)` semantics.

Suppose the entered window has no inherited LRS-3 candidate observations in the target population.

No empty candidate set is treated as positive source-history evidence. `SH(s,d,W)` is undefined wherever its candidate set is empty.

If `D1_W(s)` is consequently empty, D0 terminates with the same controlling reason:

`NO_TARGET_OBSERVATION_POPULATION`.

Its provenance records C2: no candidate observations existed.

Examples 6 and 7 therefore share a terminal D0 reason but preserve different provenance.

### Group C -- D2 Geometry and D3 Admissibility

**Example 8 -- D2 is fixed from D1 extrema**
Illustrates: D2 construction; strict-C10 extrema; D2 immutability.

Suppose the earliest observation in nonempty `D1_W(s)` maps to `G_first = 09:00`, and the latest maps to `G_last = 10:00`.

The authoritative discrete D2 grid is every 5-minute endpoint from `09:00` through `10:00`, inclusive.

The corresponding continuous temporal domain is:

`(09:00, 10:05]`.

Once constructed, later D3 outcomes cannot move either boundary.

**Example 9 -- Interior D3 failure does not shrink D2**
Illustrates: D2 immutability; D3 totality; D3 internal inadmissibility.

Using the D2 from Example 8, suppose the `09:30` endpoint is D3-inadmissible.

`09:30` remains part of D2.

The domain does not become two smaller evaluation domains and does not remove `09:30`. Instead:

`D3_ADMISSIBLE(09:30,W) = FALSE`.

That endpoint becomes an internal terminating discontinuity for D4 topology.

**Example 10 -- D3 validity resumes after an internal gap**
Illustrates: C10 invalid-state continuity; D3; D4 no-bridging rule.

Suppose:

`09:20 = HIGH / D3-admissible`

`09:25 = D3-inadmissible`

`09:30 = HIGH / D3-admissible`.

The two HIGH cells do not form one episode.

The inadmissible `09:25` cell terminates the earlier episode, and the HIGH state at `09:30` begins a new episode. Neither D3 nor observation assignment may search backward across `09:25` to recover the earlier HIGH run.

### Group D -- Structural Episodes and Censoring

**Example 11 -- State transition terminates an episode without censoring**
Illustrates: D4 `STATE_CHANGE`; inherited F4 as superseded for v2 boundary semantics (Section 4.3 below).

Suppose consecutive D3-admissible cells inside D2 are:

`HIGH, HIGH, HIGH, LOW, LOW`.

The transition from HIGH to LOW normally terminates the HIGH episode and begins a LOW episode.

The transition itself creates no censoring.

**Example 12 -- Internal D3 inadmissibility terminates but does not censor**
Illustrates: D4 `D3_INADMISSIBILITY`; v2 F4 supersession (Section 4.3 below).

Suppose a HIGH episode is followed by a D3-inadmissible cell and later another HIGH cell.

The first HIGH episode terminates at the internal discontinuity. The inadmissible cell is not an episode and is not a censor boundary. The later HIGH cell belongs to a new episode.

No episode may bridge the inadmissible cell.

**Example 13 -- Left D2 edge resolved by auditable prehistory**
Illustrates: D4 `D2_BOUNDARY`; inherited F4 left trace.

Suppose the first D2 cell is HIGH. The authorized pre-D2 trace encounters an earlier LOW-to-HIGH transition before reaching the earliest auditable prehistory boundary.

The origin of the HIGH episode is therefore observed. The episode is not left-censored merely because part of its observed run precedes D2.

The prehistory trace resolves censoring status but does not enlarge D2.

**Example 14 -- Left D2 edge remains censored**
Illustrates: D4 left censoring; inherited validity-discontinuity/state-transition trace.

Suppose the first D2 cell is HIGH and the authorized pre-D2 trace remains continuously valid and HIGH through the earliest auditable prehistory boundary without exposing either a state transition or inherited validity discontinuity.

The episode is:

`LEFT_CENSORED`.

No assumed earlier start time is fabricated.

**Example 15 -- Right D2 boundary is terminal for duration knowledge**
Illustrates: D4 right censoring; prohibition on post-D2 rescue.

Suppose an episode remains active through `G_last`.

That episode is:

`RIGHT_CENSORED`.

Post-D2 observations, states, or source-history information cannot be used to complete its duration for the current Window Evaluation.

**Example 16 -- One-cell episode can be censored at both literal D2 edges**
Illustrates: independent left/right censoring; one-cell D2 minimum.

Suppose D2 contains exactly one grid cell and the episode represented by that cell cannot have its origin resolved through authorized prehistory.

Because the same episode also reaches `G_last`, it may simultaneously be:

`LEFT_CENSORED = TRUE`

and

`RIGHT_CENSORED = TRUE`.

Its observed duration remains one 5-minute grid interval. Right censoring does not by itself certify the episode as SHORT.

### Group E -- Gate-2 Zero States and Reconciliation

**Example 17 -- Z1 only: zero current-Window eligible observations but structural episodes exist**
Illustrates: D1/D3 current-Window observation eligibility; G-NUMERIC v2 Z1 (Section 4.4 below); G-NUMERIC.1; G-NUMERIC.4 applicability; independent G-NUMERIC.5 structural support.

Suppose `D1_W(s)` is nonempty, but every current-Window observation maps to a D3-inadmissible endpoint:

`N_LRS4_ELIGIBLE(s,W) = 0`.

Assume the complete D2/D3 environmental timeline nevertheless contains D3-admissible cells elsewhere, so:

`K_total > 0`.

G-NUMERIC.4 resolves:

`NOT_APPLICABLE_ZERO_ELIGIBLE_OBSERVATIONS`.

`p_min` is not instantiated, and G-NUMERIC.4 contributes no reason to `R_W`.

G-NUMERIC.1 remains independently operative and controls its own result. G-NUMERIC.5 also resolves independently from the authoritative D4 structural episode topology; `K_total > 0` does not imply that either HIGH or LOW satisfies its frozen per-state episode-support requirement. Z1 therefore neither determines nor suppresses the G-NUMERIC.5 result.

Other applicable structural episode diagnostics continue from the authoritative D3/D4 topology.

**Example 18 -- Z1 + Z2: no eligible observations and no structural episodes**
Illustrates: G-NUMERIC v2 Z1/Z2 (Section 4.4 below); G5 independent state diagnostics; diagnostic totality.

Suppose every D2 endpoint is D3-inadmissible.

Then:

`K_total = 0`

and

`T_classified = 0`.

No current-Window observation can be regime-eligible, so:

`N_LRS4_ELIGIBLE(s,W) = 0`.

G-NUMERIC.4 is not applicable because the eligible-observation population is zero.

Turnover and persistence independently resolve:

`NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES`.

Neither morphology ratio nor its censoring bounds is instantiated.

Because `K_HIGH = K_LOW = 0`, the HIGH and LOW G-NUMERIC.5 support diagnostics independently fail. Their shared `INSUFFICIENT_STATE_EPISODE_SUPPORT` reason is retained once in `R_W`.

**Example 19 -- Z2 without Z1 is forbidden**
Illustrates: D3 totality over D2; D4 construction exclusively from D3-admissible cells; D1/D3 current-Window observation-eligibility rule; G-NUMERIC v2 Z2 reconciliation (Section 4.4 below); failure-layer preservation.

Suppose an implementation reports:

`K_total = 0`

but also:

`N_LRS4_ELIGIBLE(s,W) > 0`.

This state is impossible under the authoritative dependency model. `K_total = 0` means the authoritative D4 topology contains no structural episode, which under D3/D4 construction means no D3-admissible cell exists in D2. But every current-Window eligible observation in `D1_W(s)` requires its strict-C10 endpoint `G(T)` to satisfy:

`D3_ADMISSIBLE(G(T),W) = TRUE`.

The two reported conditions therefore cannot coexist under the normative D1/D3/D4 dependency chain.

The result is a methodology-integrity failure. It is not processed as ordinary Gate-2 output.

### Group F -- Instrument Path and Final Projection

**Example 20 -- Primary window is the realized window**
Illustrates: `InstrumentPathResult`; `W*`; final projection.

Suppose the Instrument Path completes with:

`InstrumentPathResult = VIABLE`

and its unique realized window is the primary 4h window.

Then:

`W* = 4h`.

Final observation projection may proceed only after the final `SH_path(s,d)` stage gate. For a projected observation whose day has `SH_path = ELIGIBLE`, strict C10 maps `T` to `G(T)`, and final disposition reads the same authoritative 4h D3 artifact produced during that Window Evaluation.

No D3 object is recomputed during final projection.

**Example 21 -- A fallback becomes the realized window**
Illustrates: `InstrumentPathResult`; exclusive `W*`; historical-only non-realized D3 artifacts.

Suppose the primary Window Evaluation requires a 24h fallback, the 24h Window Evaluation is entered, and the completed Instrument Path is:

`InstrumentPathResult = VIABLE`

with realized window:

`W* = 24h`.

The earlier 4h D3 artifact remains historical Window-Evaluation evidence only.

It cannot rescue, veto, average with, or otherwise alter final observation disposition under the authoritative 24h D3 artifact.

This example makes no claim about legacy `H_path` labels or their mapping to `InstrumentPathResult`.

**Example 22 -- Gate-2-terminal path has no realized window**
Illustrates: non-VIABLE path; `W*` exclusivity.

Suppose the primary evaluation leads to a fallback, the fallback is evaluated, and that fallback terminates on a structural Gate-2 failure.

The completed path is:

`InstrumentPathResult = GATE2_TERMINAL`.

There is no `W*`.

The fallback is merely the last evaluated window; it is not a realized window. No final observation projection occurs.

**Example 23 -- D0-terminal path has no realized window**
Illustrates: D0 path termination; `InstrumentPathResult`; no final projection.

Suppose an entered Window Evaluation reaches D0 because its authoritative `D1_W(s)` is empty.

The completed path is:

`InstrumentPathResult = D0_TERMINAL`.

There is no `W*`, no synthetic Gate-2 result for that window, and no final observation projection.

The D0 provenance remains separately recorded as C1 or C2.

**Example 24 -- Final source-history exclusion precedes realized-window D3 disposition**
Illustrates: `SH_path`; `FinalObservationDisposition`; failure-layer preservation.

Suppose the completed path is VIABLE and establishes `W*`, but for research day `d`:

`SH_path(s,d) = INELIGIBLE`.

For an inherited LRS-3-eligible observation `T` on that day:

`FinalObservationDisposition(T) = LRS4_SOURCE_HISTORY_INELIGIBLE`.

Final projection does not consult D3 to replace that final source-history exclusion with a regime-ineligibility result.

**Example 25 -- Final regime ineligibility under the realized window**
Illustrates: realized-window D3 reuse; `FinalObservationDisposition`.

Suppose:

`InstrumentPathResult = VIABLE`

`SH_path(s,d) = ELIGIBLE`

and strict C10 maps observation `T` to endpoint `G(T)` under `W*`.

If the already-authoritative realized-window artifact contains:

`D3_ADMISSIBLE(G(T),W*) = FALSE`

then:

`FinalObservationDisposition(T) = LRS4_REGIME_INELIGIBLE`.

Final projection does not search backward for an older admissible endpoint and does not consult D3 from another entered window.

**Example 26 -- Final LRS-4 eligibility**
Illustrates: final-path stage ordering; `FinalEligible` derived-only authority.

Suppose:

`InstrumentPathResult = VIABLE`

`SH_path(s,d) = ELIGIBLE`

and:

`D3_ADMISSIBLE(G(T),W*) = TRUE`.

Then:

`FinalObservationDisposition(T) = LRS4_ELIGIBLE`.

Consequently:

`FinalEligible(T) = TRUE`.

The Boolean is derived from the categorical disposition; it does not independently authorize or redefine that disposition.

**Example 27 -- Empty entered window abstains from `SH_path`; defined failure does not**
Illustrates: K1.2-A v2 `W_evidence` (Section 4.5 below); final source-history aggregation.

Suppose a VIABLE path entered both 4h and 24h.

On day `d`:

`|O_candidate(s,d,4h)| > 0`

but:

`|O_candidate(s,d,24h)| = 0`.

Then 24h supplies no `SH(s,d,24h)` value and abstains from `SH_path(s,d)` aggregation.

If instead the 24h candidate set were nonempty and:

`SH(s,d,24h) = INELIGIBLE`,

that result would participate in the AND and could make:

`SH_path(s,d) = INELIGIBLE`.

An empty contributor and a defined failure are therefore not interchangeable.

**Example 28 -- Undefined `SH_path` is day-level bookkeeping, not an observation status**
Illustrates: K1.2-A v2 empty `W_evidence` (Section 4.5 below); final-disposition population boundary.

Suppose:

`W_evidence(s,d) = empty`.

Then:

`SH_path(s,d) = UNDEFINED`.

Under the frozen path architecture, this implies the day contains zero inherited LRS-3-eligible observations requiring LRS-4 final disposition.

`UNDEFINED` is not converted into:

`LRS4_SOURCE_HISTORY_INELIGIBLE`,

`LRS4_REGIME_INELIGIBLE`,

or any new observation-level status.

---

## Section 4 -- Inheritance and Interface Audit

This section records how Experiment v2 consumes the frozen Experiment-v1 authority that remains applicable. It is an authority index and interface reconciliation, not a substitute for the underlying normative clauses. Where any summary in this section conflicts with an applicable normative clause, the normative clause governs.

### 4.1 -- Authority Classification Matrix

- **INHERITED UNCHANGED:** the strict C10 observation-to-grid mapping `G(T)` to the latest completed 5-minute endpoint satisfying `G < T`; the applicable C11 temporal convention; F2/F3/F5; F6 numeric mechanics; the applicable Gate-2 control architecture after Gate 2 is reached; and endpoint-level source-history and threshold-validity machinery except where Experiment v2 explicitly resolves an interface below.
- **INHERITED / RE-EXPRESSED THROUGH v2 AUTHORITY:** C10's invalid-discontinuity/non-bridging principle, expressed for Experiment v2 through authoritative D3/D4 environmental admissibility and episode topology.
- **SUPERSEDED OR RESOLVED ONLY WHERE SPECIFIED FOR v2 EXECUTION:** C10's direct observation-disposition semantics; the F4 boundary semantics identified in Section 4.3; the G-NUMERIC population/applicability semantics identified in Section 4.4; and the K1.2-A candidate-evidence and `SH_path` aggregation semantics identified in Section 4.5.
- **NEW EXPERIMENT-v2 AUTHORITY:** D0-D4, Final-Path Observation Projection, the Experiment-v2 authority/vocabulary rules, and the Experiment-v2 discriminated result interfaces.

This matrix classifies authority only. It does not independently create, modify, or supersede methodology.

### 4.2 -- C10 Observation-Assignment Interface Resolution

Experiment v2 inherits unchanged C10's strict observation-to-grid mapping: for observation `T`, `G(T)` is the latest completed 5-minute grid endpoint satisfying strict `G < T`. The inherited exact-grid convention therefore also remains operative: an observation exactly at a grid endpoint consumes the immediately preceding completed endpoint rather than that endpoint's newly calculated state.

C10's prohibition against bridging an invalid discontinuity also remains operative in Experiment v2 through the authoritative D3/D4 topology. A D3-inadmissible cell terminates episode continuity, cannot itself become an episode, and cannot be bridged to recover an earlier valid state.

Frozen Experiment v1's direct rule that an observation consuming an INVALID state becomes `LRS4_REGIME_INELIGIBLE` does not independently govern Experiment-v2 final projection. For Experiment v2, current-Window observation regime eligibility is the D3-based `Eligibility(T,W)` defined by Section 2. Final categorical observation disposition is governed by the Final-Path Observation Projection after Instrument Path completion: the applicable `SH_path(s,d)` stage gate is resolved first and, when source-history eligible, strict C10 maps `T` to `G(T)` so that final projection reads the already-authoritative realized-window D3 artifact for `W*`.

This subsection only reconciles authority already established by frozen C10 and Experiment-v2 D1/D3/D4/Final-Path methodology. It introduces no new eligibility rule, timing rule, threshold, population definition, source-history behavior, fallback behavior, disposition behavior, or other methodology.

### 4.3 -- F4 Experiment-v2 Supersession
Status: SUPERSEDED ONLY WHERE SPECIFIED. Experiment v2 supplies the deterministic evaluation-domain and admissibility objects that frozen v1 F4 lacked. All F4 censoring-duration, morphology-certainty, bound-construction, denominator, and indeterminacy rules remain INHERITED UNCHANGED except for the boundary semantics specified below.

For Experiment v2, censoring authority comes only from the literal D2 temporal boundary. An observed state transition is a normally resolved episode boundary and does not create censoring. D3 inadmissibility at a D2 grid cell is an internal terminating discontinuity: it breaks episode continuity, is not itself an episode, and never creates a censor boundary. Censoring may not jump across or bridge any D3-inadmissible gap.

At the left D2 edge, the inherited F4 backward trace through already-audited prehistory remains operative. If that trace encounters a terminating state transition or D3 inadmissibility, the episode origin is resolved normally and the episode is not left-censored on that basis. If the same state remains continuously admissible through the earliest auditable prehistory boundary, the episode is `LEFT_CENSORED`.

At the right D2 edge, an episode that reaches the literal `G_last` endpoint is `RIGHT_CENSORED`; no post-D2 observation, state, or source-history information may be used to rescue or complete that duration. A one-cell episode may independently be left-censored, right-censored, both, or neither according to these rules. Its observed duration remains one grid interval; right censoring does not by itself certify the episode as SHORT.

Experiment v2 F6 remains INHERITED UNCHANGED. Its statement that invalid regime time breaks episodes is governed by the authoritative v2 D3 topology: D3-inadmissible cells break episodes and contribute to neither episode count nor classified-time denominators.

### 4.4 -- G-NUMERIC Experiment-v2 Resolution
Status: v2 RESOLUTION. This subsection supersedes or completes three specific elements of G-NUMERIC.1-.6 above. All other G-NUMERIC content, including every numeric threshold, remains INHERITED UNCHANGED.

1. **Current-Window scope clarification (G-NUMERIC.1, G-NUMERIC.2, G-NUMERIC.3).** G-NUMERIC.1's "source-history-eligible population" and G-NUMERIC.2/.3's "source-history-eligible instrument-days"/"source-history-eligible population" denominators are scoped to the current Window Evaluation being assessed, not to the final realized-path population governed by `SH_path` (see K1.2-A's Experiment v2 supersession (Section 4.5 below)). `D1_W` (Experiment v2 Section 2) is the current-Window observation population from which G-NUMERIC.1-.3 observation counts/exposures are derived, and every observation in `D1_W` resolves to exactly one of `LRS4_ELIGIBLE` or `LRS4_REGIME_INELIGIBLE` for that Window Evaluation. `D_available` is the corresponding count of current-Window source-history-eligible instrument-days under the same W-specific source-history scope; it is a day-level count, not itself `D1_W`. `SH_path`, being downstream of realized-path resolution, has no authority over or input into G-NUMERIC.1-.3 for any individual Window Evaluation.

2. **G-NUMERIC.4 zero-eligible-observation applicability.** G-NUMERIC.4 does not define behavior when the current-Window eligible-observation population is empty. If `N_LRS4_ELIGIBLE(s,W) = 0` for a Window Evaluation whose constructibility prerequisites have passed, G-NUMERIC.4 resolves to `NOT_APPLICABLE_ZERO_ELIGIBLE_OBSERVATIONS`: `p_min` is not instantiated, and G-NUMERIC.4 contributes no reason code. This is not a Gate-2 failure; it is diagnostic metadata only and contributes no reason to `R_W`, and has no independent authority over `A_W` or `H_W`. All other Gate-2 diagnostics, including G-NUMERIC.1's independent evaluation of the same zero-eligible-observation state, remain fully operative. This state is reachable and legitimate (a Window Evaluation may have observations that all resolve `LRS4_REGIME_INELIGIBLE`); it must not be treated as an integrity failure, and it must not be inferred to numerically equal `p_min = 0` or to independently imply `SEVERE_REGIME_IMBALANCE`.

3. **G-NUMERIC.6 zero-structural-episode applicability.** G-NUMERIC.6 does not define behavior when the authoritative structural episode topology (Part F2-F4, as refined by Experiment v2's D2/D3/D4 object model) contains zero episodes. Under frozen episode-duration mechanics (F3), every actual structural episode has strictly positive duration; consequently `K_total = 0` if and only if `T_classified = 0`. If `K_total = 0` for a Window Evaluation whose constructibility prerequisites have passed, both G-NUMERIC.6 sub-diagnostics resolve independently to `NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES`: neither `P_short` nor `P_long,time`, nor their F4 censoring bounds, is instantiated, and neither `EXCESSIVE_EPISODE_TURNOVER` nor `TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE` may fire. Turnover and persistence remain two independently recorded diagnostic results despite sharing this triggering condition; neither may be inferred from the other, and their shared antecedent does not authorize merging their records. Neither is a Gate-2 failure, and neither contributes to `R_W`. G-NUMERIC.5 remains fully operative: `K_total = 0` implies `K_HIGH = K_LOW = 0`, so the independently recorded HIGH and LOW G-NUMERIC.5 diagnostics both fail their frozen support requirement. Their shared `INSUFFICIENT_STATE_EPISODE_SUPPORT` reason appears once in `R_W`, which is a set. F4's boundary-censoring indeterminacy mechanism does not apply to this state: that mechanism presupposes a nonzero, partitionable episode population, which does not exist here. A `K_total = 0` state combined with a positive current-Window eligible-observation count is not a legitimate realization of this state; it indicates a reconciliation failure between the authoritative D3 topology and current-Window observation assignment (see Experiment v2's observation-assignment supersession) and must fail closed as an integrity error rather than being processed as ordinary G-NUMERIC.6 output.

### 4.5 -- K1.2-A Experiment-v2 Supersession
Status: v2 RESOLUTION. This subsection supersedes only the two K1.2-A elements identified below. All other K1.2-A content, including endpoint-level source-history authorization mechanics, path-conditioned prehistory requirements, and threshold-learning validity gates, remains INHERITED UNCHANGED.

1. **Candidate-evidence scope (supersedes K1.2-A paragraph 1's "actually evaluated" membership language).** K1.2-A's phrase "W-scale regime classification is actually evaluated for T" is ambiguous between upstream candidacy and downstream evaluation outcome. Any interpretation in which membership depends on source-history authorization, regime validity, or another downstream result would create a circular dependency. Experiment v2 therefore defines `O_candidate(s,d,W)` as the inherited frozen LRS-3 observations on research day d that enter W's candidate set solely because W was legitimately entered by the Instrument Path. Candidate membership is independent of endpoint source-history authorization, `SH(s,d,W)`, regime validity, and downstream Gate-2 results. For v2 consumption, the governing consumed-endpoint set is `G_candidate(s,d,W) = {G(T) : T in O_candidate(s,d,W)}`, where `G(T)` is the inherited strict-C10 mapping to the latest completed 5-minute grid endpoint satisfying `G < T`. Duplicate endpoints are counted once for source-history authorization.

2. **SH_path aggregation domain (supersedes K1.2-A paragraph 4's all-entered-window AND).** Experiment v2 establishes `SH(s,d,W)` as a partial function: it is defined only when `|O_candidate(s,d,W)| > 0`. Define the realized-path evidentiary-contributor set

   `W_evidence(s,d) = {W in W_entered : |O_candidate(s,d,W)| > 0}`.

   Equivalently, this is the subset of entered windows for which `SH(s,d,W)` is defined. When `W_evidence(s,d)` is nonempty,

   `SH_path(s,d) = AND over W in W_evidence(s,d) of SH(s,d,W)`.

   An entered window for which day d contributes zero candidate observations abstains from this aggregation: it supplies neither positive nor negative source-history evidence for that day. A defined `SH(s,d,W) = INELIGIBLE` does not abstain and must participate in the AND.

   If `W_evidence(s,d)` is empty, `SH_path(s,d)` is undefined and must never be coerced to `LRS4_SOURCE_HISTORY_ELIGIBLE` or `LRS4_SOURCE_HISTORY_INELIGIBLE`. Under the frozen Instrument Path, the primary 4h Window Evaluation is entered for every instrument path; therefore `SH_path(s,d) = UNDEFINED` implies that day d contains zero inherited LRS-3-eligible observations requiring LRS-4 disposition. This undefined day-level bookkeeping state creates no additional observation-level population-status class.

   When `SH_path(s,d) = ELIGIBLE`, record the applicable positive source-history stage status under the downstream bookkeeping rules. When `SH_path(s,d) = INELIGIBLE`, record `LRS4_SOURCE_HISTORY_INELIGIBLE` with the applicable frozen K1.3-B provenance sub-reason(s). Final observation disposition is governed separately by Experiment v2's final-projection rules and is not defined by this subsection.

### 4.6 -- Remaining Inherited Interfaces

Experiment v2 does not globally supersede the remaining frozen Experiment-v1 machinery merely by existing as a separate canonical methodology document.

F1's directional fallback architecture remains applicable where a Window Evaluation reaches Gate 2 and the inherited Gate-2 resolution authorizes a directional fallback. Experiment-v2 D0 is upstream of Gate 2: a D0 constructibility failure is terminal for the current Instrument Path, does not invoke F1 fallback, and does not synthesize a Gate-2 disposition.

F2/F3/F5 and F6 remain inherited except where the Experiment-v2 D2/D3/D4 topology supplies the authoritative domain, admissibility, boundary, and episode objects consumed by those inherited mechanics. The numeric morphology and prevalence thresholds are not changed by Experiment v2.

The inherited Gate-2 `R_W`, `A_W`, and `H_W` architecture remains operative for a Window Evaluation that reaches Gate 2. Experiment-v2 `WindowEvaluationResult` and `InstrumentPathResult` preserve D0 termination as a distinct non-coercible result layer rather than translating it into an inherited Gate-2 failure.

Endpoint-level source-history authorization, source-history maturity, measurement validity, threshold-learning validity, and applicable C11 temporal semantics remain inherited except where an explicit Experiment-v2 resolution states otherwise.

No inherited Experiment-v1 methodology is superseded merely because it is not repeated in this document. Experiment-v1 methodology not explicitly superseded remains inherited unchanged where applicable, subject to the Experiment-v2 authority and interface model defined above.
