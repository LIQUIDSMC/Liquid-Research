# LRS-4 -- Market Regime Intelligence Engine
## Experiment v1 Research Design -- FROZEN

Status: Experiment v1 methodology FROZEN. Stage 1 implementation authorized.
Methodology-integrity audit: PASS. No open Experiment-v1 methodology items remain.

---

# PART A -- OBJECTIVE, SCOPE, ARCHITECTURE, INHERITED LRS-3 SEMANTICS

## A1. Governing Question
Do objectively defined, causally observable market regimes explain material variation in the behavior of existing LRS research candidates?

Experiment v1 applies this to the frozen LRS-3 trade-flow imbalance candidate. LRS-4 is supplemental decision intelligence, not a standalone strategy.

ROI mandate: Highest research ROI (decision value for existing LRS candidates) is the primary project-selection objective. ROI never overrides causal validity, frozen-before-outcomes methodology, contamination controls, or evidence standards.

## A2. Architecture -- Experiment B (observation-level conditioning)
At every inherited frozen LRS-3 sampled observation time T:
causal trailing volatility state at T -> frozen LRS-3 imbalance observation at T -> frozen forward return.
Regime label must exist causally before the observation it conditions. No future information enters regime construction, threshold learning, eligibility, or assignment.

## A3. Target Instruments
BTC-USD, ETH-USD, evaluated independently. Combined statistics are descriptive only; pooling/averaging/joint-pass criteria may never rescue a failing instrument or suppress an asymmetric result.

## A4. Inherited LRS-3 Candidate (frozen, not modified)
- Lookback: 10s trailing trade-flow imbalance, sampled every 20th trade.
- Imbalance window (T-10s, T], exact T-10s excluded.
- I_T = (V_buy - V_sell)/(V_buy+V_sell), 0 when total volume is zero.
- Forward horizons: 5s/15s/30s/60s, strict (T, T+h].
- Momentum reference uses latest trade <= T-10s (asymmetric vs. imbalance window boundary -- frozen LRS-3 behavior, not altered).
- Deterministic rank deciles; D9-D0 = mean forward return in top decile minus bottom decile.
- Research day defined by trade_time; multi-partition loading; sort order (trade_time, trade_id).
- LRS-3 expanded validation: 50 instrument-days (25 dates x 2 instruments), 9/9 gates PASS. Combined median D9-D0 (bp): 5s +0.6622, 15s +0.6730, 30s +0.7343, 60s +0.7428. These are research effect statistics -- not executable, cost-adjusted, or proof of causation/execution viability.

## A5. Inherited LRS-3 canonical reference (supersedes any implicit restatement)
The authoritative source for inherited observation construction, eligibility, decile ranking, and D9-D0 is the frozen canonical LRS-3 implementation (trade_flow_vs_momentum_screen.py, compute_screen(), rank_deciles()). Exact commit reference must be recorded before Stage 2. LRS-4 restatements are explanatory only; any discrepancy between restatement and canonical code is a methodology-integrity failure requiring resolution before Stage 2. No Stage-2 implementation may substitute a reconstructed version of eligibility, deciling, D9-D0, or timing semantics.

## A6. Primary Estimand
Per instrument x horizon: Delta_regime = (D9-D0)_HIGH - (D9-D0)_LOW.
Primary research unit = individual frozen LRS-3 sampled observation. Estimand is observation-weighted. Episode clustering != equal episode weighting.

---

# PART B -- CONTAMINATION CONTROLS, EVIDENCE FIREWALL, SOURCE-HISTORY POPULATION

## B1. Principal Contamination Risk
LRS-3 samples every 20th trade -> activity/volume/sampling-density regime definitions are prohibited (mechanical coupling). Regime variable is price-based (volatility).

## B2-B4. Parameter-Selection / Numeric-Threshold Firewall
Allowed evidence pre-freeze: general/methodological literature, estimator behavior, inherited LRS-3 timescales as guardrails only, outcome-blind data-quality diagnostics (only after thresholds are frozen).
Forbidden: HIGH/LOW D9-D0, forward returns by candidate parameter, conditioned decile curves, outcome-maximizing parameter choice, threshold selection/rounding/relaxation after seeing corresponding canonical diagnostics.
No false precision: a threshold is acceptable only if independently justifiable in ~1-2 sentences without referencing the dataset.
External-anchoring guard: literature may support methodological reasoning; BTC/ETH/Coinbase-specific empirical values from literature may never calibrate a threshold, even incidentally encountered.

## B5-B8. Source History
Regime construction is continuous across research-day/storage-partition/calendar boundaries; these never reset the estimator. LRS-4 may read deeper prehistory read-only, not limited to LRS-3's 3-partition loader.

B6 (final, revised). Experiment v1 requires sufficient causal source history for the complete pipeline: raw price history -> 5m returns -> RVOL_W -> rolling-median threshold -> HIGH/LOW. Threshold-learning duration L = 5W (see E4). Because the earliest RVOL_W observation entering the learning history itself needs a complete W-length return history, nominal raw-history reachback is:
H_raw = L + W = 6W.

Active W=1h: L=5h, H_raw=6h
Active W=4h: L=20h, H_raw=24h
Active W=24h: L=120h, H_raw=144h (6 days)

Maximum Experiment-v1 nominal classifier prehistory: 144h. This is a causal lookback duration requirement, not a validity guarantee; exact endpoint-, instrument-day-, and source-boundary bookkeeping is governed by Part K Item 1.

B7 (final). Source-history eligibility is determined at the instrument-day level. LRS4_SOURCE_HISTORY_ELIGIBLE / LRS4_SOURCE_HISTORY_INELIGIBLE. Requirement is path-conditioned, not universal-144h: primary 4h evaluation requires nominal 24h prehistory; the 24h fallback (if legitimately invoked) requires nominal 144h; the 1h fallback requires nominal 6h (dominated by 24h already needed for the preceding 4h primary). 144h is the maximum possible Experiment-v1 requirement, not a prerequisite for every primary 4h Window Evaluation. Leading-boundary instrument-days whose required prehistory precedes the verifiable corpus boundary -> LRS4_SOURCE_HISTORY_INELIGIBLE, excluded before aggregate regime-ineligibility and D_available calculations. Ordinary interior measurement/data gaps that are not affirmatively established as acquisition-source breaks remain governed by source-completeness/state-validity rules and are not converted into source-history exclusions. An affirmatively established instrument-attributed acquisition-source break is the explicit exception: it is governed by K1.3-B source-history-break machinery and may produce LRS4_SOURCE_HISTORY_INELIGIBLE before aggregate regime-ineligibility and D_available calculations.

B8. Prehistory is initialization only, never part of the conditioned target population. Verified prehistory may make 1h/4h/24h volatility estimators mature at the first retained observation; this does not by itself guarantee the complete HIGH/LOW classifier is mature (classifier maturity is governed by the L=5W threshold-learning requirement in B6/E4). No partial warm-up permitted anywhere.

---

# PART C -- REGIME CONSTRUCTION, PRICE SERIES, GRID, GATE 1

## C1-C2. Grid (frozen ex ante, no in-v1 fallback)
Grid = 5 minutes. No 15m rescue inside v1. Deferred v2 candidates: 15m (if v1 shows excessive local sparsity/staleness), 1m (if v1 shows insufficient resolution) -- reason-specific, not automatic fallbacks; neither may rescue v1.

## C3. Gate 1 Interpretation
Gate 1 certifies constructibility and auditability only. It does not certify regime adequacy. Adequacy is Gate 2's job exclusively.

## C4-C9. Price Construction & Gate 1 Rules
- P(G) = last eligible trade price with trade_time <= G (previous-tick).
- G1-A (staleness): endpoint valid only if most recent eligible trade age <= 1x grid interval (<=5m for v1). Trade exactly 5m old passes.
- G1-B (return integrity): return requires both immediately consecutive endpoints valid; never bridge missing intervals.
- G1-C (source-boundary completeness): required source partitions/files must be available/auditable; unverifiable -> fail closed.
- G1-D (missingness accounting): every endpoint/return resolves to VALID or an explicit INVALID reason; no silent drops. BTC/ETH reconciled independently.
- Gate 1 excludes: global coverage %, corpus-level tolerance, trailing-window coverage, HIGH/LOW balance, episode requirements, adequacy judgments, grid fallback logic.

## C10. Observation-State Assignment & Invalid-State Continuity
Assignment rule: for observation at T, use the latest completed grid endpoint G with G < T (strict). If that state is VALID, T inherits it. If INVALID, T is LRS4_REGIME_INELIGIBLE. The algorithm must never search backward past an invalid state to recover an older valid state. A later valid endpoint restores eligibility prospectively.
Exact-grid observations: an observation exactly at a grid endpoint cannot consume that endpoint's own newly-calculated state (even if valid) -- it uses the immediately preceding completed endpoint.
Invalid-gap episode corollary: INVALID breaks episode continuity. A valid state reappearing after INVALID begins a new episode even if identical in value to the pre-gap state. HIGH->INVALID->HIGH = two distinct HIGH episodes.

## C11. Regime-State Temporal-Cell Rule (Convention C -- frozen)
A state established at G governs the forward interval C_G = (G, G+Delta], Delta=5m -- matching what the G<T assignment rule actually consumes. (The backward-looking return-construction interval used to build the estimate at G is a different interval and must not be confused with this forward operational cell.)

---

# PART D -- LOCAL COVERAGE, ELIGIBILITY, MISSINGNESS

## D1-D3. Coverage Rules
Full causal window required, no partial warm-up, no imputation/interpolation/bridging.
Aggregate local coverage: >=75% of expected consecutive 5m returns valid within the complete trailing window. N_valid >= ceil(0.75 * N_expected).
Contiguous-gap limit: no contiguous invalid run may exceed 25% of expected-return count. Equality passes both.

1h window: Expected 12, Min valid 9, Max aggregate invalid 3, Max contiguous run fails at 4
4h window: Expected 48, Min valid 36, Max aggregate invalid 12, Max contiguous run fails at 13
24h window: Expected 288, Min valid 216, Max aggregate invalid 72, Max contiguous run fails at 73

## D4-D5. Failure Codes & Epistemic Status
INSUFFICIENT_TRAILING_RETURN_COVERAGE (aggregate), EXCESSIVE_CONTIGUOUS_RETURN_GAP (contiguous); both retained if both trigger -> LRS4_REGIME_INELIGIBLE.
75% and 25%: precommitted conventions, not literature-derived. Same 25% reused for both aggregate-invalid ceiling and contiguous-gap ceiling as a deliberate simplicity choice, not a claim of equivalence between the two risks (concentrated missingness is plausibly worse than scattered missingness of the same magnitude; no independently defensible basis exists yet for a separately calibrated stricter contiguous threshold -- a v2 direction). 1h fallback is intentionally coarse (each return approximately 8.33 percentage points of coverage) -- accepted lumpiness, not patched.

## D6. Eligibility Bookkeeping (hierarchical/staged, no silent substitution)
LRS3_INELIGIBLE, LRS4_SOURCE_HISTORY_ELIGIBLE, LRS4_SOURCE_HISTORY_INELIGIBLE, LRS4_REGIME_INELIGIBLE, and LRS4_ELIGIBLE are hierarchical/staged bookkeeping statuses, not five mutually exclusive alternatives at one classification layer. Source-history bookkeeping is resolved before aggregate regime-ineligibility accounting; downstream eligibility statuses must preserve that ordering. All applicable counts/percentages must reconcile without silent substitution between stages.

---

# PART E -- ESTIMATOR, THRESHOLD LEARNING, NORMALIZATION

## E1. Volatility Estimator (CLOSED)
r_g = log(P_g/P_{g-Delta}), Delta=5m. Trailing realized variance:
RV_W(G) = Sum r_g^2 over valid g in the complete causal trailing window.
RVOL_W(G) = sqrt(RV_W(G)). No local-mean subtraction (standard high-frequency RV construction, not sample-standard-deviation).

## E2. Missing-Return Treatment (CLOSED -- Option A, unadjusted)
RV_W(G) uses only observed valid consecutive returns, no imputation, no exposure/coverage scaling (N_expected/N_valid reweighting explicitly rejected -- it assumes missing intervals statistically resemble observed ones, which contradicts the contiguous-gap rule's own premise that missingness can be structurally nonrandom).
Important limitation, precisely stated: the 75%/25% rules bound the fraction of expected return intervals missing -- they do not bound the fraction of true quadratic variation unobserved (a single missing interval could contain a disproportionately large move). This is an accepted, documented Experiment-v1 measurement limitation.
Coverage metrics remain available as diagnostic metadata for every regime state but must never enter the estimator or HIGH/LOW classification unless a future methodology explicitly reintroduces them.

## E3. Normalization (CLOSED -- none, collapses into threshold learning)
No separate pre-threshold normalization (no ratio/z-score/percentile-rank/vol-of-vol transform) is applied. Cross-instrument scale differences and baseline drift are handled entirely by causal, per-instrument threshold learning (E4). Any such transform would constitute a distinct regime feature requiring separate freezing before outcomes.

## E4. Causal Threshold Learning (CLOSED)
Family: rolling empirical quantile, independently per instrument and per active window.
Cutoff: q*=0.50 (causal trailing median). theta_W(G) = Q_0.50{RVOL_W(g): g < G, g in learning history}. RVOL_W(G) > theta_W(G) -> HIGH; <= theta_W(G) -> LOW. No current-value self-inclusion.
Interpretation: HIGH/LOW = above/at-or-below causal recent median -- a relative-state separator, not an extreme-vs-normal claim. 50th-percentile threshold != 50/50 occupancy requirement (occupancy is separately governed by the minority-occupancy floor in the Gate-2 numeric catalogue, Part G-NUMERIC, and is explicitly not required to be balanced).
Learning-history length: L = kW, single invariant multiplier across all windows. Lower-bound design requirement k>4 (median-contamination stress case: a 2W-duration episode must not be able to constitute >=half the learning history; 2W is the LONG-morphology boundary used only as a stress case, not a claim about maximum episode duration or an empirical calibration of L). k=5 frozen -- smallest integer satisfying k>4, a normative convention, not empirically optimized. L=5h/20h/120h for W=1h/4h/24h respectively.
LRS-3 firewall (reaffirmed): LRS-3's N=1/3/5/10 threshold-stability result is qualitative precedent only (rolling thresholds trade stability vs. responsiveness) -- not admissible, even as a candidate-value source, for calibrating L or k. Any numeric overlap (e.g., 24h->L=120h=5 days) is incidental and uncalibrated.
No robust location/scale (median+k*MAD) estimator is used -- rejected as unearned complexity requiring multiple additional unjustified parameters.

---

# PART F -- WINDOW ARCHITECTURE, EPISODES, CENSORING

## F1. Window Selection (CLOSED)
Primary W=4h. One-hop directional fallback only:
- EXCESSIVE_EPISODE_TURNOVER (alone, no terminal code) -> one-hop 24h.
- TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE (alone, no terminal code) -> one-hop 1h.
- Both directional codes simultaneously -> derived CONFLICTING_DIRECTIONAL_FAILURES -> terminate (no adaptive choice).
- Any Gate-2 failure on a fallback window -> terminate. No second fallback (4h->24h->1h and 4h->1h->24h both forbidden).
- All frozen Gate-2 numeric thresholds apply identically, unrescaled, at every window (4h/1h/24h), except the dimensionless morphology boundaries (F5), which scale with W by construction (not a threshold adjustment).

## F2. Episode Definition
A regime episode = maximal contiguous sequence on the valid regime-state timeline carrying the same HIGH/LOW state, bounded by a state change or invalidity (per C10's invalid-gap corollary).

## F3. Episode Duration (Convention C, CLOSED)
tau_e = N_e * Delta (N consecutive same-state cells = N complete intervals, not N-1). Equivalently (G_last+Delta) - G_first.

## F4. Censoring (CLOSED)

Left: trace backward through already-audited prehistory; if a terminating transition/invalidity is found, resolve normally; if continuous through the earliest auditable boundary, mark LEFT_CENSORED. Estimator/classifier maturity (B6-B8) does not guarantee episode-start observability.

Right: episode active at evaluation-domain end -> RIGHT_CENSORED; observed duration never treated as complete.

Episode existence != duration knowledge: censored episodes still count toward K_HIGH/K_LOW (F5/Gate 2).

Morphology certainty under censoring (corrected): True episode duration is at least the observed lower-bound duration. A censored episode whose observed lower bound already exceeds 2W is therefore definitely LONG. A censored episode whose observed lower bound is below 0.5W generally cannot be certified SHORT because unobserved continuation and/or prehistory may increase its true duration beyond the SHORT boundary. More generally, a morphology category may be assigned only when that category is invariant to all episode durations consistent with the available censoring information; otherwise the episode remains morphology-ambiguous for the affected bound calculation.

K_total denominator (explicit): for the P_short bound below, K_total = all distinct valid regime episodes (any state, any censoring status) represented in / intersecting the current Gate-2 evaluation domain -- this is the fixed population being partitioned; it is not limited to only the definitely-classified subset.

P_short bounds: partition K_total into definitely-SHORT / definitely-not-SHORT / SHORT-ambiguous -> compute:
P_short^LB = K_definitely-SHORT / K_total
P_short^UB = (K_definitely-SHORT + K_SHORT-ambiguous) / K_total
LB>1/3 -> definite FAIL. UB<=1/3 -> definite PASS. Straddle -> verdict suppressed, see indeterminacy rule.

P_long,time bounds: T_classified = valid classified time inside the evaluation domain only (never extends into prehistory or beyond domain boundary) = the fixed denominator population for this statistic. Partition into definitely-LONG / definitely-not-LONG / LONG-ambiguous time -> compute [LB,UB] against 1/2 analogously. A right-censored episode already >2W contributes its full observed duration (not truncated) to both numerator and T_classified.

Indeterminacy: bounds straddling the frozen threshold -> that statistic's directional verdict is suppressed (not emitted PASS/FAIL) -> INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING (epistemic terminal, distinct from the four structural terminal codes; see Part G). Suppression is local to the affected statistic only.

### F4 -- EXPERIMENT v2 SUPERSESSION (D2 boundary censoring vs D3 internal inadmissibility)

Status: SUPERSEDED ONLY WHERE SPECIFIED. Experiment v2 supplies the deterministic evaluation-domain and admissibility objects that frozen v1 F4 lacked. All F4 censoring-duration, morphology-certainty, bound-construction, denominator, and indeterminacy rules remain INHERITED UNCHANGED except for the boundary semantics specified below.

For Experiment v2, censoring authority comes only from the literal D2 temporal boundary. An observed state transition is a normally resolved episode boundary and does not create censoring. D3 inadmissibility at a D2 grid cell is an internal terminating discontinuity: it breaks episode continuity, is not itself an episode, and never creates a censor boundary. Censoring may not jump across or bridge any D3-inadmissible gap.

At the left D2 edge, the inherited F4 backward trace through already-audited prehistory remains operative. If that trace encounters a terminating state transition or D3 inadmissibility, the episode origin is resolved normally and the episode is not left-censored on that basis. If the same state remains continuously admissible through the earliest auditable prehistory boundary, the episode is `LEFT_CENSORED`.

At the right D2 edge, an episode that reaches the literal `G_last` endpoint is `RIGHT_CENSORED`; no post-D2 observation, state, or source-history information may be used to rescue or complete that duration. A one-cell episode may independently be left-censored, right-censored, both, or neither according to these rules. Its observed duration remains one grid interval; right censoring does not by itself certify the episode as SHORT.

Experiment v2 F6 remains INHERITED UNCHANGED. Its statement that invalid regime time breaks episodes is governed by the authoritative v2 D3 topology: D3-inadmissible cells break episodes and contribute to neither episode count nor classified-time denominators.

## F5. Episode-Duration Tail Boundaries (CLOSED)
q_e = tau_e/W. SHORT: q_e<0.5. MIDDLE: 0.5<=q_e<=2. LONG: q_e>2. Equality -> MIDDLE.
Derivation: symmetric multiplicative departure from q=1 (log-symmetric: log0.5=-log2), chosen absent an independent basis for asymmetry. Not derived from local-coverage/warm-up logic or from fallback-window lengths (rejected -- would create soft circularity, since 24h is itself a consequence of a turnover failure). A surprising Stage-1 distribution never authorizes changing these within v1.
For W=4h: SHORT<2h, LONG>8h.

## F6. Turnover & Persistence (CLOSED -- asymmetric weighting)
Turnover (episode-count weighted): P_short = K_SHORT/K_total > 1/3 -> EXCESSIVE_EPISODE_TURNOVER (directional, ->24h). Episode-count weighting because turnover is a cluster-fragmentation pathology.
Persistence (classified-time weighted): P_long,time = (Sum LONG episode time)/(Sum all valid episode time) > 1/2 -> TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE (directional, ->1h). Time weighting because persistence is a temporal-domination pathology.
Invalid regime time never dilutes either denominator (breaks episodes but isn't itself an episode).
1/3 and 1/2 are precommitted prevalence conventions, deliberately not equal to each other (different weighting bases, different questions -- not aesthetic symmetry).

---

# PART G -- GATE 2: CONTROL FLOW, DISPOSITIONS, PRECEDENCE

## G0. Vocabulary
Window Evaluation E_W = (R_W, A_W, H_W): triggered reason-code set, Resolution Action, Window Disposition, for one instrument under one window.
Window Disposition H_W in {VIABLE, PATHOLOGICALLY_FRAGMENTED, STRUCTURALLY_INSUFFICIENT, EPISTEMICALLY_INDETERMINATE} -- diagnoses the construction, independent of control-flow position.
Resolution Action A_W -- primary: {PROCEED_TO_STAGE_2, EVALUATE_24H_FALLBACK, EVALUATE_1H_FALLBACK, TERMINATE_INSTRUMENT_V1}; fallback: {PROCEED_TO_STAGE_2, TERMINATE_INSTRUMENT_V1}.
Instrument Path -- exactly 3 reachable shapes: [4h], [4h,24h], [4h,1h].
Instrument-Path Disposition H_path -- 6 possible final values (G-path below).
No implementation may infer path completion or Stage-2 eligibility from H_W alone -- A_W and full permitted-path state must always be consulted jointly.

## G2. Terminal Gate-2 Codes
Structural terminal (4, independently thresholded):
1. SEVERE_REGIME_IMBALANCE
2. EXCESSIVE_REGIME_INELIGIBILITY
3. EXCESSIVE_INELIGIBILITY_CONCENTRATION
4. INSUFFICIENT_STATE_EPISODE_SUPPORT

Epistemic terminal (1):
5. INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING

Any terminal code (structural or epistemic) terminates that instrument/window; no fallback.

## G3-G4. Directional Codes & Derived Resolution
EXCESSIVE_EPISODE_TURNOVER (->24h one-hop), TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE (->1h one-hop). If both trigger with no terminal code present -> derived CONFLICTING_DIRECTIONAL_FAILURES (not a 6th independently-thresholded code) -> terminate.

## G1, G6-G9. Precedence Rules
All reason codes evaluated independently and simultaneously; implementation/documentation order never determines precedence; full triggered set always retained. Terminal (any) dominates directional (any). Fallback windows: any failure (terminal, directional, or combination) is terminal -- no second fallback.

## G5-G6. Window Disposition Resolution
Precedence: structural terminal > epistemic terminal (iff no structural terminal) > directional-only combinations > viable.

Condition: No failures -> Action: PROCEED_TO_STAGE_2 -> Disposition: VIABLE
Condition: Turnover only -> Action: EVALUATE_24H_FALLBACK (primary) / TERMINATE (fallback) -> Disposition: PATHOLOGICALLY_FRAGMENTED
Condition: Persistence only -> Action: EVALUATE_1H_FALLBACK (primary) / TERMINATE (fallback) -> Disposition: STRUCTURALLY_INSUFFICIENT
Condition: Both directional -> Action: TERMINATE -> Disposition: STRUCTURALLY_INSUFFICIENT (derived CONFLICTING_DIRECTIONAL_FAILURES)
Condition: Any structural terminal (with or without anything else) -> Action: TERMINATE -> Disposition: STRUCTURALLY_INSUFFICIENT
Condition: Epistemic terminal, no structural terminal (with or without directional) -> Action: TERMINATE -> Disposition: EPISTEMICALLY_INDETERMINATE

Directional disposition (PATHOLOGICALLY_FRAGMENTED / STRUCTURALLY_INSUFFICIENT-from-persistence) is retained even on a fallback window recurrence -- diagnosis (H_W) is independent of whether further fallback exists; only the action (A_W) changes to TERMINATE.

## G-path. Instrument-Path Disposition Function (CLOSED)

H_path = VIABLE, if A_4h = PROCEED_TO_STAGE_2
H_path = H_4h, if A_4h = TERMINATE_INSTRUMENT_V1
H_path = VIABLE_AFTER_24H_FALLBACK, if A_4h=EVALUATE_24H_FALLBACK and H_24h=VIABLE
H_path = H_24h, if A_4h=EVALUATE_24H_FALLBACK and H_24h!=VIABLE
H_path = VIABLE_AFTER_1H_FALLBACK, if A_4h=EVALUATE_1H_FALLBACK and H_1h=VIABLE
H_path = H_1h, if A_4h=EVALUATE_1H_FALLBACK and H_1h!=VIABLE

Six possible H_path values: VIABLE, VIABLE_AFTER_24H_FALLBACK, VIABLE_AFTER_1H_FALLBACK, PATHOLOGICALLY_FRAGMENTED, STRUCTURALLY_INSUFFICIENT, EPISTEMICALLY_INDETERMINATE.
Stage 2 authorized only for the three VIABLE* labels.
Fallback-provenance asymmetry (deliberate): provenance is preserved distinctly at path level only for VIABLE outcomes. Failure dispositions are not multiplied into fallback-specific variants -- full Window Evaluation history is preserved in the audit record regardless. Many-to-one path->disposition mapping is intentional -- not redundancy.
Fail-closed path invariants: path invalid if a requested fallback's Window Evaluation is absent; if any fallback requests another fallback; if a fallback appears without exact corresponding primary authorization; path <=2 Window Evaluations; every instrument terminates with exactly one H_path before Stage 2 is considered.

## G-audit (K6 summary -- PASS, subject to change-control)
Five passes run and closed: (1) Reachability; (2) Exclusivity, contingent on the closed 8-code reason-space (4 structural + 2 directional + 1 epistemic + 1 derived) -- any future code change invalidates this and requires re-audit; (3) Path Determinism; (4) Non-Vacuity; (5) Fail-Closed Integrity.
K6 change-control invariant: any later modification to the Gate-2 reason-code universe or decision architecture invalidates the affected audit conclusions and requires re-audit before Stage 1/Stage 2 reliance.

---

# PART G-NUMERIC -- GATE-2 THRESHOLD CATALOGUE

## G-NUMERIC.1 -- Aggregate Regime Ineligibility
I_overall = N_LRS4_REGIME_INELIGIBLE / N_LRS3-eligible-unique-obs-within-source-history-eligible-population, per instrument (unique observations, never duplicated across the 4 horizons).
I_overall <= 20% passes. >20% -> EXCESSIVE_REGIME_INELIGIBILITY (structural terminal). Epistemic status: precommitted estimand-retention convention.

## G-NUMERIC.2 -- Concentration: Activation Requirements
Concentration gating (below) is evaluated only when both activation conditions are met:
- Day support: D_available >= 10, where D_available = source-history-eligible instrument-days for that instrument. If D_available < 10 -> NOT_EVALUATED_INSUFFICIENT_DAY_SUPPORT.
- Count support: N_ineligible >= 2 x D_available, where N_ineligible = Sum_d i_d (total regime-ineligible observations for that instrument). If unmet -> NOT_EVALUATED_INSUFFICIENT_INELIGIBILITY_COUNT.

If both activation conditions fail simultaneously, both non-evaluation reasons are retained together (not just one).

Zero-ineligibility case: if total N_ineligible = 0 for that instrument, concentration is structurally inapplicable, not merely under-activated. Record NOT_APPLICABLE_ZERO_INELIGIBILITY (distinct from, and takes precedence over, the two NOT_EVALUATED_* activation-failure codes above, since a zero-ineligibility instrument cannot fail the count-support check for a meaningful reason).

None of these three activation/inapplicability outcomes is itself a Gate-2 failure. They only determine whether the concentration statistic below receives gating authority; the independent 20% aggregate-ineligibility ceiling (G-NUMERIC.1) and all other Gate-2 rules remain fully operative regardless.

## G-NUMERIC.3 -- Concentration: Gating Statistic
For instrument-day d, with i_d = regime-ineligible observations on day d and n_d = LRS3-eligible observations on day d (within the source-history-eligible population):

I_d = i_d / Sum_d i_d (day's share of total regime ineligibility)
E_d = n_d / Sum_d n_d (day's share of eligible-observation exposure -- includes ALL source-history-eligible days, including zero-ineligibility days, in both sums)

C_total = (1/2) * Sum_d |I_d - E_d|

This is the total-variation distance between the day-level ineligibility-share distribution and the day-level exposure-share distribution.

Threshold: C_total <= 0.30 passes. >0.30 -> EXCESSIVE_INELIGIBILITY_CONCENTRATION (structural terminal). Independently motivated, not coupled to the 20% aggregate-ineligibility ceiling (G-NUMERIC.1).

Descriptive-only (no gating authority): R_d = I_d/E_d; X_d = I_d - E_d; X_max = max_d(X_d) -- provably X_max <= C_total always, so a separate X_max gate is redundant by construction; raw single-day/top-k concentration shares.

## G-NUMERIC.4 -- Minority Regime Occupancy
p_min = min(p_HIGH, p_LOW), computed over unique LRS4_ELIGIBLE observations per instrument.
p_min >= 10% passes. <10% -> SEVERE_REGIME_IMBALANCE (structural terminal). No 50/50 requirement -- an asymmetric split is not penalized.

## G-NUMERIC.5 -- Per-State Episode Count
K_s >= 5, independently HIGH/LOW (valid contiguous episodes). <5 -> INSUFFICIENT_STATE_EPISODE_SUPPORT (structural terminal). Not inferential sufficiency (see K7 Layer 2/3, which impose separate, stricter, non-substitutable requirements).

## G-NUMERIC.6 -- Episode Morphology & Prevalence
SHORT: q_e<0.5. LONG: q_e>2 (classification only, not itself a failure).
Turnover: P_short <= 1/3 passes; >1/3 -> EXCESSIVE_EPISODE_TURNOVER (directional).
Persistence: P_long,time <= 1/2 passes; >1/2 -> TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE (directional).
Under boundary censoring, straddling bounds -> INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING (epistemic terminal) -- see Part F4 for the full bound-construction and K_total/T_classified denominator definitions.

### G-NUMERIC -- EXPERIMENT v2 SUPERSESSION (current-window scope; zero-population diagnostic totality)

Status: v2 RESOLUTION. This subsection supersedes or completes three specific elements of G-NUMERIC.1-.6 above. All other G-NUMERIC content, including every numeric threshold, remains INHERITED UNCHANGED.

1. **Current-Window scope clarification (G-NUMERIC.1, G-NUMERIC.2, G-NUMERIC.3).** G-NUMERIC.1's "source-history-eligible population" and G-NUMERIC.2/.3's "source-history-eligible instrument-days"/"source-history-eligible population" denominators are scoped to the current Window Evaluation being assessed, not to the final realized-path population governed by `SH_path` (see K1.2-A's Experiment v2 supersession). `D1_W` (Experiment v2 Section 2) is the current-Window observation population from which G-NUMERIC.1-.3 observation counts/exposures are derived, and every observation in `D1_W` resolves to exactly one of `LRS4_ELIGIBLE` or `LRS4_REGIME_INELIGIBLE` for that Window Evaluation. `D_available` is the corresponding count of current-Window source-history-eligible instrument-days under the same W-specific source-history scope; it is a day-level count, not itself `D1_W`. `SH_path`, being downstream of realized-path resolution, has no authority over or input into G-NUMERIC.1-.3 for any individual Window Evaluation.

2. **G-NUMERIC.4 zero-eligible-observation applicability.** G-NUMERIC.4 does not define behavior when the current-Window eligible-observation population is empty. If `N_LRS4_ELIGIBLE(s,W) = 0` for a Window Evaluation whose constructibility prerequisites have passed, G-NUMERIC.4 resolves to `NOT_APPLICABLE_ZERO_ELIGIBLE_OBSERVATIONS`: `p_min` is not instantiated, and G-NUMERIC.4 contributes no reason code. This is not a Gate-2 failure; it is diagnostic metadata only and contributes no reason to `R_W`, and has no independent authority over `A_W` or `H_W`. All other Gate-2 diagnostics, including G-NUMERIC.1's independent evaluation of the same zero-eligible-observation state, remain fully operative. This state is reachable and legitimate (a Window Evaluation may have observations that all resolve `LRS4_REGIME_INELIGIBLE`); it must not be treated as an integrity failure, and it must not be inferred to numerically equal `p_min = 0` or to independently imply `SEVERE_REGIME_IMBALANCE`.

3. **G-NUMERIC.6 zero-structural-episode applicability.** G-NUMERIC.6 does not define behavior when the authoritative structural episode topology (Part F2-F4, as refined by Experiment v2's D2/D3/D4 object model) contains zero episodes. Under frozen episode-duration mechanics (F3), every actual structural episode has strictly positive duration; consequently `K_total = 0` if and only if `T_classified = 0`. If `K_total = 0` for a Window Evaluation whose constructibility prerequisites have passed, both G-NUMERIC.6 sub-diagnostics resolve independently to `NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES`: neither `P_short` nor `P_long,time`, nor their F4 censoring bounds, is instantiated, and neither `EXCESSIVE_EPISODE_TURNOVER` nor `TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE` may fire. Turnover and persistence remain two independently recorded diagnostic results despite sharing this triggering condition; neither may be inferred from the other, and their shared antecedent does not authorize merging their records. Neither is a Gate-2 failure, and neither contributes to `R_W`. G-NUMERIC.5 remains fully operative: `K_total = 0` implies `K_HIGH = K_LOW = 0`, so the independently recorded HIGH and LOW G-NUMERIC.5 diagnostics both fail their frozen support requirement. Their shared `INSUFFICIENT_STATE_EPISODE_SUPPORT` reason appears once in `R_W`, which is a set. F4's boundary-censoring indeterminacy mechanism does not apply to this state: that mechanism presupposes a nonzero, partitionable episode population, which does not exist here. A `K_total = 0` state combined with a positive current-Window eligible-observation count is not a legitimate realization of this state; it indicates a reconciliation failure between the authoritative D3 topology and current-Window observation assignment (see Experiment v2's observation-assignment supersession) and must fail closed as an integrity error rather than being processed as ordinary G-NUMERIC.6 output.

---

# PART H -- STATISTICAL UNITS, ESTIMAND, INFERENCE ARCHITECTURE

## H1-H4. Units
Research unit: individual frozen LRS-3 sampled observation. Primary dependence cluster: contiguous regime episode. Secondary robustness cluster: instrument-day (too coarse for primary inference; scoped to leave-one-out robustness/concentration diagnostics only).
Two distinct dependence problems (must never be collapsed into one generic "autocorrelation" adjustment): (a) within-cell serial dependence from overlapping 10s lookback / forward horizons; (b) regime-run clustering from HIGH/LOW persistence across contiguous observations.
Cluster unit != estimand weighting unit: estimand remains observation-weighted; episodes are resampling/dependence units only, never equal-weighted.

## H5. Inference Architecture (CLOSED -- structural level)
Primary inference: nonparametric episode-cluster bootstrap, separately within HIGH and LOW state, per instrument x horizon. Episodes sampled with replacement as intact clusters; all eligible observations of a selected episode retained (including multiplicity on repeat draws); frozen LRS-3 decile construction and D9-D0 recomputed fresh inside every replicate. Delta_regime recomputed as HIGH-LOW per replicate.
HIGH and LOW episode sets resampled separately within the same replicate (no artificial pairing; K_H and K_L need not match).
No nested day->episode bootstrap -- would silently promote instrument-day to an outer sampling unit, a methodological claim never frozen.
Secondary robustness: instrument-day leave-one-out, computed deterministically (not bootstrapped on top of).
"Preserves observation weighting" -- precise meaning: the estimand remains observation-weighted within each realized sample, because the statistic is computed on pooled observations, not episode-level means. Episodes (and their internal observation counts) can appear 0, 1, or multiple times per replicate -- that variability is how episode-cluster dependence is expressed.

## H6. Bootstrap Validity -- NOT rescued by replicate count
Monte Carlo precision cannot create environmental information. Larger B reduces simulation noise only; it does not compensate for insufficient contributing-cluster support (K7).

---

# PART I -- GOVERNING META-RULES (FULL)

## I1. Relative Support != Absolute Support
A population may be proportionally well represented yet absolutely under-supported, or absolutely large yet proportionally rare. These are diagnosed separately, and neither substitutes for the other.
Applications throughout this document: regime occupancy (a relative/proportional criterion -- G-NUMERIC.4) vs. absolute estimand support (K7 Layers 1-4, an absolute-count criterion); episode morphology share (F5/F6, relative) vs. per-state absolute episode recurrence (G-NUMERIC.5, K_s>=5, absolute).

## I2. Aggregate Failure != Concentration Failure
Aggregate sufficiency statistics can conceal concentrated structural failure. Wherever Experiment v1 uses an aggregate coverage or missingness criterion, it must also consider whether a natural spatial/temporal concentration diagnostic is required at that level. Aggregate and concentration diagnostics answer different questions and neither substitutes automatically for the other.
Applications: trailing-window aggregate coverage (D2, 75%) vs. contiguous blind gap (D2, 25%); instrument-wide regime ineligibility (G-NUMERIC.1, 20%) vs. instrument-day concentration (G-NUMERIC.2-3, C_total<=0.30); the conditioned-effect robustness question (K7 Layer 5) vs. dependence on one/few instrument-days (the same Layer 5 mechanism, viewed from the concentration angle).

## I3. Structural Sufficiency != Inferential Sufficiency
A construct can be measurable/structurally present without being adequate for inference. Passing a structural floor never certifies inferential adequacy unless the methodology explicitly says so.
The canonical example: K_min=5 (Gate-2 per-state episode count, G-NUMERIC.5) explicitly does not authorize episode-cluster bootstrap inference. Passing it establishes only that a regime state recurs often enough to not be dismissed as one or two isolated occurrences -- it says nothing about whether there is enough distinct-cluster diversity for a credible resampling distribution. That stronger claim is the entire purpose of K7 Layers 2-4, which impose independent, stricter, non-substitutable requirements (K^contrib>=8, K_D0/K_D9>=5, C_2<=0.50) before inference is authorized.

## I4. Diagnostic Computability != Resolution Authority
A diagnostic being mathematically computable does not imply it is authorized to control an Experiment-v1 resolution action. Where mathematically defined, diagnostics may be computed and retained for observability even when an upstream activation or support requirement has failed. However, a downstream diagnostic may affect resolution only when all of its own frozen upstream activation prerequisites have been satisfied. No diagnostic value may be fabricated merely to satisfy a reporting requirement -- if a quantity is undefined under the remaining sample, the appropriate non-computability state must be recorded rather than imputed, interpolated, substituted, or otherwise invented.
Applications: episode-censoring morphology diagnostics (F4 -- bounds computed and reported even when they straddle a threshold and cannot resolve PASS/FAIL); Gate-2 concentration activation (G-NUMERIC.2 -- C_total may be computed but has no gating authority until D_available and N_ineligible activation conditions clear); K7 estimand-support diagnostics generally (a failed Layer 1 sample may still expose Layer 2-4 values where mathematically defined, but those values cannot become competing primary diagnoses); instrument-day leave-one-out robustness (K7 Layer 5 -- computed whenever mathematically defined even while Layers 1-4 have failed, but resolution-inactive until they all pass).

---

# PART J -- K7: ABSOLUTE ESTIMAND-SUPPORT ARCHITECTURE (FULLY CLOSED)

## J0. Purpose & Chain
K7 determines whether a structurally-viable (Gate-2-passed) regime-conditioned candidate has sufficient absolute support for the conditioned D9-D0 estimand and downstream inference. K7 does not alter the frozen LRS-3 candidate definition, does not redefine Gate-2 regime viability, and does not permit one support dimension to rescue failure in another.
Authorization chain: L1->L2->L3->L4 (sequential, resolution-gating -- each layer's authorization is a precondition for the next being evaluated for resolution purposes). Layer 5 is diagnostic-always (computed whenever mathematically defined, even while L1-L4 are failing), and becomes resolution-active only after Layers 1-4 have all passed; it may never rescue, replace, override, or downgrade an upstream L1-L4 failure.
Stage-control clarification: K7 does not control entry into Stage 2 -- Gate 2 alone is the structural authority for whether an instrument may proceed to Stage-2 conditioned analysis. K7 is evaluated within the Stage-2 conditioned-analysis stage and governs conditioned-estimand / primary-inference authorization specifically -- this ordering avoids a circular dependency in which Stage 2 would need K7 results that can only be generated after Stage 2 has already started.

## J1. Layer 1 -- Decile-Construction Support
For each instrument x regime state x frozen LRS-3 horizon, preserve the complete canonical ten-decile count vector (N_D0, N_D1, ..., N_D9), using the authoritative frozen LRS-3 rank_deciles() implementation. No reconstructed or substitute decile algorithm is permitted.

L1-A -- Decile existence diagnostic. For every decile, N_d >= 1 is the minimum condition for that decile to exist. Retain D_empty = {d : N_d = 0}. L1-A is diagnostic and does not independently authorize advancement.

L1-B -- Non-singleton construction floor (controlling). Every canonical decile must contain at least two eligible observations: N_d >= 2 for all d in {D0,...,D9}. A singleton decile is numerically calculable but contains no within-cell replication and therefore does not constitute a non-degenerate empirical decile mean for Experiment v1. Retain D_singleton = {d : N_d = 1}, and the complete set of failed deciles. Also retain:
- EXTREME_DECILE_FAILURE (boolean flag, whether D0 and/or D9 specifically are among the failed deciles);
- exact D0 count;
- exact D9 count;
- complete ten-decile count vector.

Controlling failure code: INSUFFICIENT_DECILE_CONSTRUCTION_SUPPORT. Trigger: exists d such that N_d < 2. This is a constructibility threshold only. No separate total-N_{s,h} threshold is frozen because the realized canonical per-decile counts are the more direct and non-redundant support criterion.

Passing Layer 1 does not establish statistical stability, cluster sufficiency, tail environmental diversity, bootstrap validity, or day-level robustness. Those are the separate, independent jobs of Layers 2 through 5.

## J2. Layer 2 -- Horizon-Contributing Episode Support
For each instrument x state x horizon, define K^contrib_{s,h} = the number of distinct valid regime episodes containing at least one eligible observation contributing to that horizon-specific conditioned sample.

Requirement: K^contrib_{s,h} >= 8.

Derivation: the expected number of distinct clusters represented when K clusters are resampled K times with replacement is E[U_K] = K[1-(1-1/K)^K]. Experiment v1 requires E[U_K] >= 5 (reusing the independently frozen Gate-2 five-episode structural-recurrence floor as the bootstrap-replicate support target). The smallest integer satisfying this is K=8 (E[U_7]~=4.62 < 5; E[U_8]~=5.25 >= 5).

Epistemic status (precise): the arithmetic is exact. The use of the Gate-2 five-episode recurrence standard as the bootstrap-replicate support target is a normative methodological transfer -- structural recurrence credibility and inferential adequacy are conceptually related but are not identical statistical claims. Passing K^contrib_{s,h}>=8 does not establish asymptotic bootstrap validity, does not guarantee finite-sample bootstrap performance, does not establish tail-specific cluster diversity, and does not establish episode-contribution balance. The criterion is expectation-based: Experiment v1 does not additionally require P(U_K>=5)>=p* for some probability p*, because doing so would require introducing a new unsupported probability parameter. The expectation criterion does not guarantee that any given bootstrap replicate will actually contain >=5 distinct episodes -- only that this is true on average across replicates. Large B (replicate count) cannot compensate for small K^contrib -- Monte Carlo precision cannot create environmental information that does not exist in the underlying episode population.

Controlling failure code: INSUFFICIENT_CONTRIBUTING_EPISODE_SUPPORT. Retain: actual K^contrib_{s,h}; regime state; horizon; total structural K_s; count of structural episodes contributing zero observations at horizon h (this distinguishes "the regime itself barely recurred" from "the regime recurred plenty, but horizon eligibility stripped out many episodes" -- diagnostically different findings).

Non-substitution: the Gate-2 structural recurrence requirement K_s>=5 and the Layer-2 requirement K^contrib_{s,h}>=8 are independent, non-substitutable conditions. Neither may rescue failure of the other.

## J3. Layer 3 -- Extreme-Decile Episode Support
For each instrument x state x horizon, define K_{s,h,D0} and K_{s,h,D9} as the numbers of distinct valid regime episodes containing at least one observation assigned to the corresponding extreme decile, in the original canonical conditioned sample (not inside any bootstrap replicate).

Requirement, independently: K_{s,h,D0} >= 5 and K_{s,h,D9} >= 5.

Epistemic status: the value five reuses the independently frozen Experiment-v1 structural recurrence floor as the minimum environmental-replication convention at the tail-cell level. It is not an asymptotic-bootstrap threshold, not derived from Layer 2's K^contrib>=8 resampling calculation (Layer 3 evaluates the original, pre-resampling tail-episode population -- a raw-recurrence question, not a bootstrap-population question), and not a claim that five tail episodes are sufficient for precision.

D0 and D9 episode sets need not be disjoint -- a single regime episode may legitimately contain observations assigned to multiple canonical deciles; there is no requirement for 10 unique episodes across their union.

Controlling failure code: INSUFFICIENT_EXTREME_DECILE_EPISODE_SUPPORT. Retain: K_D0; K_D9; D0_PASS; D9_PASS; FAILED_EXTREMES (which extreme(s) failed); K_contrib (for cross-reference to Layer 2); contributing episode identifiers for each extreme.

Passing Layer 3 establishes repeated environmental representation of both extreme deciles only -- it does not establish balanced contribution across those episodes (Layer 4's job). Because rank deciles are recomputed inside every bootstrap replicate, Layer 3 does not guarantee that any given bootstrap replicate will contain five distinct D0 or D9 episodes -- it gates only the starting point's raw tail support.

## J4. Layer 4 -- Extreme-Decile Episode Concentration
No exposure-adjusted concentration baseline is constructed. Unlike Gate-2 instrument-day ineligibility concentration (where a day's exposure share is independent of whether ineligibility occurred), no independent, causally neutral episode-level measure exists for an episode's expected opportunity to contribute specifically to D0 or D9 -- an episode's tendency to contribute to an extreme imbalance decile is entangled with the phenomenon being measured. Therefore Experiment v1 prohibits constructing an artificial I_e-E_e, total-variation, or equivalent exposure-adjusted tail-concentration statistic here.

For each extreme decile d in {D0, D9}, define p_{e,d} = N_{e,d} / N_d (episode e's share of decile d's observations). Sort contributing-episode shares descending: p_(1),d >= p_(2),d >= .... Define top-two concentration: C_{2,d} = p_(1),d + p_(2),d.

Requirement, independently: C_{2,D0} <= 0.50 and C_{2,D9} <= 0.50. Equality passes. A value above 0.50 means two episodes collectively supply a majority of the observations in that extreme decile -- classified as excessive environmental concentration.

Epistemic status: the 0.50 threshold is an ex-ante majority convention, not an empirically optimized concentration level. Experiment v1 intentionally addresses one- or two-episode majority domination only; it does not introduce separate top-one, top-three, HHI, or effective-episode-count gates. Broader three-or-more-episode concentration remains a documented residual limitation and potential future-methodology (v2) question.

A separate p_max <= 0.50 gate was considered and rejected as redundant, because C_2 <= 0.50 implies p_max <= 0.50 mathematically. A p_max-only gate was also independently tested and found to miss real two-episode-domination cases -- e.g., shares (0.49, 0.49, 0.01, 0.005, 0.005) pass p_max<=0.5 despite 98% of the tail coming from two episodes; C_2 correctly catches this case (C_2=0.98, fails).

Retain diagnostically (no gating authority): complete episode-share vector; largest episode share p_max; top-two share C_2; HHI = Sum_e p_e^2; effective episode count K_eff = 1/HHI.

Controlling failure code: EXCESSIVE_EXTREME_DECILE_EPISODE_CONCENTRATION. D0 and D9 evaluated independently; all triggered failures retained.

Non-vacuity check (worked example): at the minimum Layer-3-passing support (K_d=5 episodes, perfectly equal shares of 0.20 each), C_2 = 0.20+0.20 = 0.40 -- comfortably passes. Layer 4 therefore does not silently require near-perfect balance at the Layer-3 floor; a genuinely uneven but non-dominated distribution such as (0.30, 0.20, 0.20, 0.15, 0.15) still passes at exactly C_2=0.50, while (0.35, 0.25, 0.15, 0.15, 0.10) fails at C_2=0.60.

## J5. Layer 5 -- Instrument-Day Robustness
Layer 5 is not part of the sequential Layers 1-4 authorization chain.

Full-sample contrast: Delta_hat_regime = (D9-D0)_HIGH - (D9-D0)_LOW. The sign of this quantity defines the directional Experiment-v1 regime conclusion.

Zero full-sample contrast: if Delta_hat_regime = 0, there is no directional proposition for Layer 5 to test. Record NOT_APPLICABLE_ZERO_FULL_SAMPLE_CONTRAST -- this is not a Layer-5 PASS, not INSTRUMENT_DAY_DIRECTIONAL_FRAGILITY, and not grounds for inventing an arbitrary sign convention. Ownership of the zero-contrast case belongs to the final conditioned-estimand interpretation logic, not to Layer 5.

Contributing-day universe D_contrib: for nonzero full-sample contrast, D_contrib = the set of distinct instrument-days contributing at least one observation to the full-sample conditioned analysis for the instrument x horizon under evaluation. Days contributing zero observations are not part of the deletion universe. Every day in D_contrib must be evaluated exactly once -- no contributing day may be removed from the robustness universe because its deletion produces an inconvenient, unstable, or non-computable result.

Leave-one-instrument-day-out recomputation: for every d in D_contrib, remove all eligible observations belonging to instrument-day d, then recompute the complete conditioned estimand using the frozen canonical methodology: Delta_hat^(-d)_regime. Canonical decile assignment must be recomputed after deletion -- original full-sample D0/D9 membership must never be frozen across the leave-one-out recomputation. No interpolation, imputation, substitution, or synthetic replacement is permitted. No leave-one-day-out bootstrap is used in Experiment v1. No nested day->episode bootstrap is permitted without explicit future methodology change.

Non-computable deletion: if removal of any d in D_contrib leaves insufficient support to construct the required conditioned contrast, record NOT_COMPUTABLE_AFTER_DAY_REMOVAL for that deletion. Once Layer 5 is resolution-active, such a deletion constitutes Layer-5 failure -- it must not be excluded from a denominator or silently omitted from the robustness assessment. Interpretation: if removing one contributing validation day destroys the estimand itself, the conditioned conclusion is materially dependent on that day -- this is evidence of day-level fragility, not grounds for exemption.

Controlling directional robustness criterion (categorical, parameter-free): for every contributing-day deletion, Delta_hat^(-d)_regime must be computable and must preserve the nonzero sign of the full-sample contrast: sign(Delta_hat^(-d)_regime) = sign(Delta_hat_regime) for all d in D_contrib. Exact zero after day removal does not preserve direction -- Delta_hat^(-d)_regime = 0 fails Layer 5. Experiment v1 does not use a fractional sign-consistency requirement; there is no 80%, 90%, 95%, or other tolerance threshold. The authorized categorical claim is narrower: no single contributing instrument-day may be necessary for the existence or sign of the directional regime conclusion.

Controlling failure code: INSTRUMENT_DAY_DIRECTIONAL_FRAGILITY. Triggered, once Layers 1-4 have passed and the full-sample contrast is nonzero, if any contributing-day deletion (1) makes the conditioned contrast non-computable, (2) produces an exact-zero contrast, or (3) reverses the sign of the full-sample contrast. Retain the complete diagnostic decomposition:
- NONCOMPUTABLE_DAY_REMOVALS
- SIGN_FLIP_DAY_REMOVALS
- ZERO_CONTRAST_DAY_REMOVALS
- full leave-one-day-out contrast vector
- full-sample contrast
- most magnitude-sensitive day-removal
- minimum leave-one-day-out contrast
- maximum leave-one-day-out contrast
- counts of positive, negative, zero, and non-computable leave-one-day-out outcomes

All triggered subdiagnostics are retained even though a single controlling failure code governs Layer-5 resolution.

Magnitude sensitivity is descriptive only. Where mathematically meaningful, retain for every contributing-day deletion Delta_hat^(-d)_regime - Delta_hat_regime and, optionally, the relative diagnostic (Delta_hat^(-d)_regime - Delta_hat_regime)/|Delta_hat_regime|. Experiment v1 freezes no maximum absolute-deviation, attenuation, or relative-change threshold -- a leave-one-day-out contrast may approach zero while retaining the original sign and still pass the controlling Layer-5 criterion. This is an explicit, documented Experiment-v1 residual limitation, not an omitted threshold.

LRS-3 precedent firewall: LRS-3's prior use of sign-consistency as a promotion concept (its own gate table) is admissible as qualitative methodological precedent only. Any LRS-3 numeric sign-consistency threshold, including the previously used 33/50 criterion, is numerically inadmissible for selecting or justifying the LRS-4 Layer-5 rule. Experiment v1's all-deletions requirement is justified by its own categorical claim (no single contributing day is necessary for the sign of the regime contrast) -- it is not calibrated from LRS-3's promotion threshold.

## J6. Compute-vs-Resolve / Non-Substitution Summary
Where mathematically defined, downstream diagnostics may be computed even if an upstream support layer fails. However: Layer-2 findings cannot rescue Layer 1. Layer-3 findings cannot rescue Layers 1-2. Layer-4 findings cannot rescue Layers 1-3. Layer-5 findings cannot rescue Layers 1-4. A downstream diagnostic whose activation prerequisites have not cleared is supplementary diagnostic evidence only and must not control resolution.

Thus a sample may simultaneously record, for example: inadequate D9 construction (Layer 1 failure); one D9-contributing episode (would-be Layer 3 failure); 100% D9 episode concentration (would-be Layer 4 failure); and severe leave-one-day-out fragility (would-be Layer 5 failure) -- while the controlling diagnosis remains the earliest applicable upstream support failure (Layer 1, here). The richer downstream findings remain available to explain the anatomy of that failure, but do not compete with it as alternative diagnoses.

## J7. K7 Final Audit Status -- FULL PASS
Ten checks closed:
1. Reachability -- each layer (L1-L4, plus L5's five branch outcomes) has a demonstrated nonempty reachable region, including independent failure examples for each layer given all prior layers pass (e.g., K_D9=5 with shares (0.35,0.25,0.15,0.15,0.10) passes Layer 3 but fails Layer 4 at C_2=0.60).
2. Sequential non-substitution -- verified that no downstream rule mathematically or semantically implies an upstream one (K_s>=5 does not imply K^contrib>=8; K^contrib>=8 does not imply K_D0/K_D9>=5; K_Dd>=5 does not imply C_2,Dd<=0.50).
3. Non-vacuity/redundancy -- Layer 1's per-decile floor is not replaced by any episode criterion; Layer 2's overall count is not inferable from Layer 3 (same tail episodes can overlap substantially without establishing total horizon-support semantics); Layer 3 is not redundant with Layer 4 (equal-share K_d=5 gives C_2=0.40, well under the 0.50 ceiling -- Layer 4 does not make the Layer-3 boundary impossible or require perfect balance).
4. Diagnostic-computability/resolution-authority separation -- verified consistent for L2-L5: a failed L1 sample may still expose downstream episode counts/concentration where mathematically defined, but those values cannot become competing primary diagnoses; no fabricated values required when a downstream diagnostic becomes undefined.
5. Layer-5 diagnostic accessibility -- Layer 5 remains computable diagnostically whenever mathematically defined even when Layers 1-4 have failed; downstream results remain supplementary only until L1-L4 clear; non-computable deletions represented explicitly, never fabricated or dropped; the full-sample zero-contrast case has an explicit resting place (NOT_APPLICABLE_ZERO_FULL_SAMPLE_CONTRAST) -- no possible full-sample sign state is left undefined.
6. Layer-5 resolution completeness -- for nonzero full-sample contrast after L1-L4 pass, every contributing day yields exactly one of: computable same-sign, computable opposite-sign, computable zero, or non-computable. These four exhaust the possible leave-one-day-out outcomes; resolution is deterministic (same-sign-and-computable-for-every-day -> PASS; any of the other three -> INSTRUMENT_DAY_DIRECTIONAL_FRAGILITY); no undefined branch remains.
7. Non-vacuity (Layer 5 specifically) -- a nonzero full-sample contrast can pass Layer 5 despite substantial magnitude variation (e.g., Delta_hat=0.70 with LOO values ranging 0.30 to 0.90, all same sign, passes) -- the rule does not quietly impose magnitude stability. A sign reversal, exact-zero deletion, or non-computable deletion provides a reachable failure region. Both PASS and FAIL regions are nonempty.
8. Independence from Layers 1-4 -- Layers 1-4 passing does not mathematically guarantee Layer-5 sign robustness (Layer 5 can fail independently after full upstream authorization); conversely, strong LOO sign stability cannot rescue failure of Layers 1-4 because Layer-5 resolution authority remains inactive until they clear.
9. Diagnostic versus resolution authority (Layer 5 specifically) -- magnitude diagnostics may reveal severe attenuation even where the controlling sign criterion passes; such diagnostics do not silently become resolution-active. Layer-5 findings generated while Layers 1-4 are failed remain explanatory only.
10. Stage-control ordering -- K7 does not control entry into Stage 2; Gate 2 remains the sole structural authority for that. K7 governs conditioned-estimand/primary-inference authorization, evaluated within the Stage-2 analysis itself. No circular dependency.

Change-control invariant: any future modification to Layer-1 decile construction support, Layer-2 contributing-episode support, Layer-3 extreme-decile episode support, Layer-4 concentration, Layer-5 day robustness, sequencing, reason-code semantics, activation requirements, or diagnostic-versus-resolution authority invalidates the affected K7 audit conclusions and requires explicit change-control re-audit before Stage 1/Stage 2 reliance.

---

# PART K-ITEM-1 -- SOURCE-HISTORY / THRESHOLD-LEARNING BOUNDARY BOOKKEEPING (CLOSED)

This section closes former Part K Item 1 in full. All sub-decisions below (K1.1, K1.2, K1.3-A, K1.3-B) are methodologically decided and canonical as of this patch.

## K1.1 -- Learning-history endpoint set (CLOSED)

Frozen convention: H_L(G) = {g : G-L <= g < G}. This is closed-below, open-above -- g=G-L IS included; g=G is excluded (preserving the causal g<G rule already frozen elsewhere).

Exact member counts (N = L/Delta):
- W=1h, L=5h: 60 grid endpoints
- W=4h, L=20h: 240 grid endpoints
- W=24h, L=120h: 1440 grid endpoints

Rejected alternative: H_L(G) = {g : G-L < g < G} (open-below) was rejected because it yields only L/Delta - 1 endpoints and would make the oldest included endpoint's own required prehistory reach only to G-6W+Delta -- one grid interval short of the frozen H_raw=6W statement (B6). The open interval (G-L, G) still spans continuous duration L; the deficiency is discrete grid-endpoint cardinality, not continuous span. Temporal span and discrete grid-observation count are treated as distinct properties throughout this document and must never be conflated.

## K1.2 -- Threshold-history validity, source-history maturity, and maturity ordering (CLOSED)

Three-layer separation, frozen and non-negotiable: source-history maturity != measurement validity != threshold validity. These are evaluated in that order; none may substitute for another.

**Source-history maturity.** For instrument-specific auditable source boundary S0,s (see K1.3-A below):

G_SH-mature = ceil(S0,s)_grid + 6W

This is a floor on endpoint-level classifier authorization, never a guarantee of passing. At G < G_SH-mature, that grid endpoint is source-history immature and the classifier is not authorized to evaluate threshold validity at G. At G >= G_SH-mature, evaluation is authorized but RVOL_W(G), theta_W(G), and State_W(G) remain independently governed by the rules below. Instrument-day-level source-history bookkeeping remains separate: legitimate leading corpus-boundary inability to verify the required prehistory is recorded as LRS4_SOURCE_HISTORY_INELIGIBLE with sub-reason SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT, and Stage 1 must report retained versus source-history-excluded instrument-day counts.

### K1.2-A -- Endpoint-to-instrument-day source-history aggregation (CLOSED)

Instrument-day source-history status is derived from the source-history qualification of the regime endpoints actually consumed by inherited LRS-3 observations assigned to that research day. For instrument s and research day d, let O_s,d be the inherited LRS-3 observations whose canonical trade_time-based research-day assignment is d. For each Window Evaluation W actually entered by the frozen Instrument Path, let G_used,s,d,W = {G(T) : T in O_s,d and W-scale regime classification is actually evaluated for T}, where G(T) is the latest completed 5-minute grid endpoint satisfying strictly G < T. Duplicate consumed endpoints are evaluated once within W; unused grid endpoints and endpoints for which W is not actually evaluated do not enter SH(s,d,W).

Source-history qualification remains path-conditioned, not universal-144h. For each Window Evaluation W actually entered by the frozen Instrument Path, define SH(s,d,W). For every G in G_used,s,d,W, apply the same G_SH-mature definition already frozen in K1.2, evaluated separately using that entered window's W. The endpoint must also satisfy K1.3-B/B's governing S(G) source-break rule. SH(s,d,W) = ELIGIBLE only if every consumed G satisfies both requirements; if any consumed G fails either requirement, SH(s,d,W) = INELIGIBLE. No percentage, duration, or contiguous-run tolerance is applied at this instrument-day aggregation layer.

Window qualification is evaluated only when that Window Evaluation is legitimately entered. The 4h primary therefore requires its own nominal 24h source prehistory; a legitimately invoked 24h fallback requires its own nominal 144h source prehistory; a legitimately invoked 1h fallback requires its own nominal 6h source prehistory. No fallback-specific source-history requirement is imposed prospectively when that fallback is never entered.

The instrument-day's governing realized-path source-history status is SH_path(s,d) = AND over W in W_entered of SH(s,d,W). If every entered Window Evaluation is source-history eligible, record LRS4_SOURCE_HISTORY_ELIGIBLE; if any entered Window Evaluation is source-history ineligible, record LRS4_SOURCE_HISTORY_INELIGIBLE with the applicable frozen K1.3-B provenance sub-reason(s). This aggregation creates no additional population-status class.

Optional per-window source-history clearance diagnostics for 1h, 4h, and 24h may be computed independently where mathematically defined, including for windows not entered by the realized path. Such diagnostics are supplementary only: they never override, substitute for, or alter SH_path(s,d), and they must remain separately reported rather than collapsed into a single most-permissive-window value.

**Threshold-learning validity gates**, applied to H_L(G)'s RVOL_W(g) members (filtered-median semantics: compute using VALID members only, no forward-fill, no imputation, no shrinking of L, no backward search past an invalid state):

Gate 1 (aggregate availability): N_valid_RVOL >= ceil(0.75 * N_nominal)
Gate 2 (contiguous concentration): N_max_contiguous_INVALID <= 0.25 * N_nominal

| W | N_nominal | Min VALID | Max total INVALID | Max contiguous INVALID (duration) | Fails at |
|---|---:|---:|---:|---|---:|
| 1h | 60 | 45 | 15 | 15 = 75m | 16 |
| 4h | 240 | 180 | 60 | 60 = 5h | 61 |
| 24h | 1440 | 1080 | 360 | 360 = 30h | 361 |

Epistemic status: both gates are precommitted conservative conventions (supermajority above the median's 50% breakdown point; simplicity-driven reuse of the same fraction for concentration), not empirically optimized and not implied by the breakdown point itself. If either gate fails at G: theta_W(G) = INVALID, therefore State_W(G) = INVALID, and existing C10/C11 invalid-state/episode-break rules apply -- no new mechanism required.

Limitation, stated explicitly: valid-RVOL member counts measure temporal availability of the threshold-input series, not independent information content. Adjacent RVOL_W(g) observations overlap heavily by construction; passing these gates never implies that many independent volatility estimates exist.

### K1.2-A -- EXPERIMENT v2 SUPERSESSION (candidate-evidence scope and SH_path aggregation domain)

Status: v2 RESOLUTION. This subsection supersedes only the two K1.2-A elements identified below. All other K1.2-A content, including endpoint-level source-history authorization mechanics, path-conditioned prehistory requirements, and threshold-learning validity gates, remains INHERITED UNCHANGED.

1. **Candidate-evidence scope (supersedes K1.2-A paragraph 1's "actually evaluated" membership language).** K1.2-A's phrase "W-scale regime classification is actually evaluated for T" is ambiguous between upstream candidacy and downstream evaluation outcome. Any interpretation in which membership depends on source-history authorization, regime validity, or another downstream result would create a circular dependency. Experiment v2 therefore defines `O_candidate(s,d,W)` as the inherited frozen LRS-3 observations on research day d that enter W's candidate set solely because W was legitimately entered by the Instrument Path. Candidate membership is independent of endpoint source-history authorization, `SH(s,d,W)`, regime validity, and downstream Gate-2 results. For v2 consumption, the governing consumed-endpoint set is `G_candidate(s,d,W) = {G(T) : T in O_candidate(s,d,W)}`, where `G(T)` is the inherited strict-C10 mapping to the latest completed 5-minute grid endpoint satisfying `G < T`. Duplicate endpoints are counted once for source-history authorization.

2. **SH_path aggregation domain (supersedes K1.2-A paragraph 4's all-entered-window AND).** Experiment v2 establishes `SH(s,d,W)` as a partial function: it is defined only when `|O_candidate(s,d,W)| > 0`. Define the realized-path evidentiary-contributor set

   `W_evidence(s,d) = {W in W_entered : |O_candidate(s,d,W)| > 0}`.

   Equivalently, this is the subset of entered windows for which `SH(s,d,W)` is defined. When `W_evidence(s,d)` is nonempty,

   `SH_path(s,d) = AND over W in W_evidence(s,d) of SH(s,d,W)`.

   An entered window for which day d contributes zero candidate observations abstains from this aggregation: it supplies neither positive nor negative source-history evidence for that day. A defined `SH(s,d,W) = INELIGIBLE` does not abstain and must participate in the AND.

   If `W_evidence(s,d)` is empty, `SH_path(s,d)` is undefined and must never be coerced to `LRS4_SOURCE_HISTORY_ELIGIBLE` or `LRS4_SOURCE_HISTORY_INELIGIBLE`. Under the frozen Instrument Path, the primary 4h Window Evaluation is entered for every instrument path; therefore `SH_path(s,d) = UNDEFINED` implies that day d contains zero inherited LRS-3-eligible observations requiring LRS-4 disposition. This undefined day-level bookkeeping state creates no additional observation-level population-status class.

   When `SH_path(s,d) = ELIGIBLE`, record the applicable positive source-history stage status under the downstream bookkeeping rules. When `SH_path(s,d) = INELIGIBLE`, record `LRS4_SOURCE_HISTORY_INELIGIBLE` with the applicable frozen K1.3-B provenance sub-reason(s). Final observation disposition is governed separately by Experiment v2's final-projection rules and is not defined by this subsection.

## K1.3-A -- Auditable Source Coverage: definition (CLOSED)

Auditable Source Coverage is a storage-integrity-level certification only. It is explicitly NOT a claim of collector completeness (no upstream event ledger exists to verify against) and explicitly NOT, by itself, instrument-specific (see K1.3-B for the instrument-specific extension).

Frozen storage-integrity prerequisites (necessary, not sufficient, for any interval to be treated as auditable):
1. Required partition container (date=... directory) exists.
2. Partition contains >= 1 candidate Parquet artifact (directory existence alone, per LRS-3's is_dir() check, was confirmed by direct inspection of storage.py and the LRS-3 loader to be insufficient -- an empty-but-existing partition is possible under the current write path).
3. Every candidate artifact required by the scan is readable as Parquet.
4. Schema/types conform to the frozen canonical schema.
5. Required raw null invariants pass (timestamp_received, instrument_id, trade_time non-null).
6. timestamp_received partition-key consistency: every inspected row's partition_date_utc(timestamp_received) equals the directory's encoded date. (Confirmed: canonical storage partitions by timestamp_received/receipt time, not trade_time or event_time -- this is why LRS-3's own documented cross-partition trade_time spill is structural and expected, not anomalous.)
7. All required receipt-time partitions spanning the certified interval are audited under these same deterministic rules.
8. Any inability to establish one of the above fails closed -- never silently treated as "no trading activity."

## K1.3-B -- Instrument-specific source-coverage qualification (CLOSED)

### Governing evidentiary standard (applies to all of A/B/C below)

Frozen standard: non-circular operational evidence with sufficient temporal and instrument attribution for the claim being made.

This explicitly REJECTS a mandatory external-source / two-independent-clocks requirement. Evidence is not inadmissible merely because it is emitted by the same process/subsystem the claim is about; a future structured record containing an auditable timestamp, instrument attribution, and meaningful acquisition-state semantics could independently establish a boundary. Conversely, an external subsystem's evidence (e.g., systemd) is not intrinsically superior by virtue of being external -- its evidentiary value is specific to what it actually proves (timestamped process/service state), which must be combined with separately-verified content (e.g., version-attributed static subscription payload) to support any given claim.

### K1.3-B/A -- Leading-boundary S0,s (CLOSED)

Stored trade presence alone can never establish S0,s. Required chain: auditable operational artifact + historical code/config attribution + instrument-specific acquisition semantics -> S0,s. If any link is absent, contradictory, or cannot be historically attributed: S0,s = UNRESOLVED.

Evidence-strength hierarchy (conceptual, not evidentiary-source-based):
- Tier 1: direct instrument-specific runtime confirmation.
- Tier 2: version-attributed static acquisition configuration (proven via historical code/commit inspection) + timestamped runtime startup evidence, jointly.
- Tier 3: venue/process-level runtime evidence without instrument-specific acquisition proof -- corroborative only.
- Tier 4: stored market-data presence/absence -- never sufficient.

Worked example (BTC-USD/ETH-USD, current production deployment): collector_systemd.log filesystem Birth timestamp (2026-08-17 18:37:21) associated with a Coinbase connection/subscription startup sequence, where the code version historically attributed to that deployment (verified via git history) contains a static, unconditional dual-instrument subscription payload with no partial-subscription code path. This qualifies at Tier 2 and is accepted as S0,BTC-USD = S0,ETH-USD, with the explicit qualification that this is the earliest auditable operational boundary supported by retained evidence -- not a claim of the exact subscription-event nanosecond, and not a claim that no earlier collection ever existed.

### K1.3-B/B -- Confirmed interior source-coverage breaks (CLOSED)

Two distinct objects, not to be conflated:

D_P(G) = {p in grid : G-6W <= p <= G} -- the discrete computational price-endpoint dependency domain. Derived bottom-up: threshold -> H_L(G) members -> each member's own trailing-W return-window -> each return's two price endpoints. Verified (after an intermediate synthesis error was caught and corrected) to bottom out at exactly G-6W, both endpoints inclusive. (Formerly notated D(G); D(G) is retired in favor of D_P(G) -- no second discrete object exists, this is a pure rename for clarity once the continuous S(G) object below was introduced.)

S(G) = [G-6W, G] -- the continuous acquisition-coverage envelope. Tests whether the entire real-time span backing G's dependency chain remained free of an affirmatively established source-coverage break, independent of grid alignment (an outage can occur entirely between two grid points and still be real).

D_P(G) and S(G) share identical numeric bounds because both inherit the same causal dependency span from the single threshold -> RVOL -> return -> price reduction (the same 6W duration). They are not the same object: D_P(G) asks which discrete price endpoints are computationally required; S(G) asks whether that entire continuous interval was free of confirmed acquisition-path unavailability. Same temporal extent, different mathematical objects, different tests -- D_P(G) is never tested against a break interval; only S(G) is.

A confirmed source-coverage break is an interval B_s = [T_stop, T_acquisition_restored) established via the governing evidentiary standard above (not via stored trade presence/absence, not via first-subsequent-valid-RVOL, not via another instrument producing data, not by assuming any handshake is instantaneous).

Rule: if S(G) intersect B_s != empty, source-history maturity fails at G for instrument s, deterministically, before ordinary RVOL/threshold-validity gates are evaluated. No duration threshold is used -- a break qualifies regardless of whether it lasts seconds or days; duration determines downstream footprint, not admissibility.

Bounded-break recovery: the earliest G at which the break no longer intersects S(G) is G >= ceil(T_acquisition_restored)_grid + 6W (identical formal pattern to G_SH-mature, reusing the same grid-alignment convention).

Unresolved-ended break (T_acquisition_restored cannot be established): B_s = [T_stop, infinity). No recovery exists -- S(G) intersect B_s != empty for every G >= T_stop. This remains open until qualifying non-circular operational evidence later establishes T_acquisition_restored; it is not bounded by assumption.

Worked case (current production deployment): retained systemd journal evidence establishes a service-level stop at 2026-08-30 22:10:04 and a subsequent service start at 2026-09-01 22:06:29. Systemd establishes timestamped service/process state, not direct instrument-specific acquisition state. Attribution of the confirmed service outage to both BTC-USD and ETH-USD is compositional: systemd service evidence plus version-attributed joint BTC/ETH acquisition semantics. The later systemd "Started" event is process-launch evidence only and does NOT by itself establish T_acquisition_restored. Until qualifying evidence establishes instrument-specific acquisition restoration, the break end remains unresolved under the rule above.

Source-history status is LRS4_SOURCE_HISTORY_INELIGIBLE. Frozen sub-reasons are SOURCE_HISTORY_LEADING_BOUNDARY_INSUFFICIENT, SOURCE_HISTORY_BREAK_CONFIRMED, and SOURCE_HISTORY_BREAK_END_UNRESOLVED. These are provenance categories, not severity levels; all feed the same source-history population-exclusion mechanism before the aggregate regime-ineligibility denominator. Break-cause metadata may separately record provenance such as SERVICE_PROCESS_OUTAGE or CONNECTION_INTERRUPTION without creating additional population-status classes.

### K1.3-B/C -- Connection-level interruption routing (CLOSED)

Routing rule (no new population-status class, no duration threshold):
- If admissible operational evidence establishes an actual acquisition-path interruption, instrument attribution, and an auditable clock-time start boundary, the interruption escalates to K1.3-B/B's source-break machinery and is tested against S(G) exactly as above. If restoration is established, the break is bounded; if restoration is unresolved, the break remains open.
- If an operational interruption is known to have occurred but its clock-time localization and/or instrument attribution is insufficient to construct an admissible instrument-specific break interval, it remains diagnostic-only operational provenance and does not independently trigger source-history exclusion.
- If canonical data independently fail endpoint/return/RVOL rules without an established source break, those failures are governed by the existing G1-A (staleness) / D2-D3 (coverage) / K1.2 (threshold-learning validity) machinery.

G1-A/D2-D3 explicitly CANNOT substitute for affirmative source-break evidence in the other direction: a localized, instrument-attributable outage can coexist with a G1-A-VALID endpoint (e.g., a brief outage followed by a previous-tick price still within the staleness bound) -- G1-A validity is not proof that no outage occurred, and never overrides an affirmatively established source break.

### SequenceGapTracker admissibility (CLOSED)

Confirmed via direct source inspection (collector.py): the tracker uses ONE sequence_num counter shared across every channel, product, and control-message stream on one WebSocket connection and is therefore NOT instrument-specific. A new tracker is created for every connection; the first integer sequence in that connection is accepted as the baseline, so no continuity is inferred across reconnect boundaries. GAP DETECTED establishes a within-session shared-stream sequence discontinuity. Its missing_count is the exact number of expected shared-stream sequence numbers absent between the two observed sequence values; it is NOT evidence that the same number of BTC-USD trades, ETH-USD trades, or market-data messages of any particular type were lost. GAP DETECTED output has no auditable event timestamp in the current append log.

Ruling for the current Experiment-v1 evidence: SequenceGapTracker output has no independent source-break resolution authority. It establishes within-session shared-stream sequence discontinuity but does not establish instrument attribution or auditable research-clock localization sufficient to construct B_s,j. Because the tracker resets at each connection and accepts the first new sequence as baseline, it also cannot certify continuity across reconnect boundaries. Current gap-tracker evidence therefore remains diagnostic-only.

Deferred, explicitly non-blocking, NOT a methodology item: future analysis may correlate GAP DETECTED line position with connection-marker line position for descriptive session-relative context. No "mid-session" versus "reconnect-adjacent" evidentiary subclasses are frozen, and line ordering must not be given causal meaning. In particular, a GAP DETECTED after a reconnect proves only a discontinuity after the new session baseline was established; it does not prove loss during the preceding disconnect. Positional analysis cannot presently alter S0,s, construct B_s,j, or change the S(G) intersection rule.

---

# PART K -- METHODOLOGY-ITEM LEDGER & FINAL INTEGRITY AUDIT

1. K1 (source-history / threshold-learning boundary bookkeeping) is fully closed -- see PART K-ITEM-1 above.
2. Bootstrap replicate count B -- CLOSED. Experiment v1 treats B exclusively as a Monte Carlo approximation-precision parameter. B does not compensate for insufficient K7 cluster support, strengthen evidentiary support, repair unstable underlying data, establish profitability or causality, or guarantee stability of interval endpoints in Delta_regime value units.

For the most extreme interval-defining tail probability p, Monte Carlo probability-space standard error is:

SE_p = sqrt[p(1-p)/B]

Experiment v1 requires, at frozen Monte Carlo assurance 1-gamma:

z_(1-gamma/2) * sqrt[p(1-p)/B] <= epsilon * p

Therefore:

B_min = ceil[z_(1-gamma/2)^2 * (1-p) / (epsilon^2 * p)]

The separately frozen two-sided 95% percentile interval in Item 3 gives alpha=0.05 and therefore controlling tail probability p=alpha/2=0.025. The frozen relative rank-space tolerance is epsilon=0.10: Monte Carlo displacement of the nominal 0.025 tail probability is permitted up to 10% of that probability, i.e. +/-0.0025 in probability space (0.0225 to 0.0275). This is a precommitted numerical precision convention, not an empirically optimized threshold and not a guarantee of value-space endpoint stability. A 20% tolerance was rejected as comparatively coarse for an interval-defining tail; a 5% tolerance was rejected for v1 because it requires approximately four times the replication count of the 10% convention without any currently specified downstream use for the additional rank-space precision.

The frozen Monte Carlo assurance level is 1-gamma=0.95 (gamma=0.05). It governs the probability that Monte Carlo error remains within the separately frozen epsilon tolerance. Its numerical equality with the substantive confidence level 1-alpha=0.95 is coincidental: alpha and gamma govern different objects, were justified independently, and neither is derived from the other. A 90% assurance level was rejected as unnecessarily permissive; 99% was rejected for v1 because it materially increases replication cost without an identified downstream requirement for the additional numerical assurance.

With p=0.025, epsilon=0.10, and the standard-normal quantile z_(0.975)=Phi^(-1)(0.975)=1.959963984540054...:

B_min = ceil[(1.959963984540054...)^2 * 0.975 / (0.10^2 * 0.025)]
      = ceil[14,981.6894...]
      = 14,982

The familiar approximation z_(0.975) ~= 1.96 is descriptive only and must not be substituted into the exact ceiling calculation: using rounded 1.96 would produce 14,982.24 and therefore an incorrect ceiling of 14,983. The frozen integer minimum is computed from the actual standard-normal quantile.

Frozen production replication count:

B_production = 15,000

B_production is solely an upward operational rounding of the derived minimum by 18 replicates. It has no independent methodological meaning, and production B may never be rounded below B_min.

Expected tail-count diagnostic at production B:

B_production * p = 15,000 * 0.025 = 375

This is an auditable Monte Carlo-resolution diagnostic only; it is not an independent gate and must not be confused with the empirical-quantile rank used by Item 3.

Value-space limitation, explicit and non-negotiable: for empirical quantile value q_p, approximate Monte Carlo endpoint uncertainty depends on the unknown local bootstrap density f(q_p), with SE(q_p) approximately sqrt[p(1-p)/B] / f(q_p). No finite distribution-free B therefore guarantees a fixed basis-point or Delta_regime-unit endpoint stability. Experiment v1 makes no such claim and uses no value-space endpoint-stability rule to select B.

Post-authorization numerical audit only: after Stage 2 inference is authorized, same-B independent-seed reruns may be used descriptively to assess realized numerical sensitivity. They may not select a favorable seed, alter alpha/epsilon/gamma, adaptively increase B until a preferred result appears, redefine the interval, or otherwise modify the frozen inferential procedure. Any realized numerical instability is reported as-is.

Methodological-literature admissibility note: the rank-space Monte Carlo precision framework above has direct methodological precedent in bootstrap guidance deriving the same z/p/relative-error structure for resolving a 0.025 percentile tail to within 10% relative probability error at 95% assurance, including application to percentile-bootstrap intervals (Hesterberg). This citation is admissible as methodology-level precedent only. It supplies no BTC/ETH/Coinbase outcome information, does not calibrate an LRS-4 effect threshold, and does not weaken the experiment's pre-outcome firewall.
3. Interval construction -- CLOSED. Experiment v1 reports a two-sided 95% percentile-bootstrap interval for each authorized prespecified instrument x horizon Delta_regime estimand.

Frozen confidence level:

alpha = 0.05

Therefore the nominal percentile endpoints are:

p_lower = alpha/2 = 0.025
p_upper = 1 - alpha/2 = 0.975

The 95% level is a precommitted reporting and interpretability convention selected for broad comparability with conventional scientific/statistical uncertainty reporting. It is not claimed to be mathematically privileged, uniquely optimal, or statistically necessary. K7 authorization and Layer-5 leave-one-instrument-day-out sign robustness are separate structural/robustness safeguards; they do not alter alpha, substitute for interval uncertainty, or constitute Type-I-error control.

Each interval is marginal to its own prespecified instrument x horizon estimand. Experiment v1 does not claim 95% simultaneous family-wise coverage across all reported estimands. An individual interval excluding zero does not, by itself, authorize a stronger cross-estimand discovery claim. Any future simultaneous/family-wise claim would require separately frozen multiplicity handling and is not implied by this procedure.

Interval family:

CI_(1-alpha) = [Q_(alpha/2)(Delta_regime*), Q_(1-alpha/2)(Delta_regime*)]

where Delta_regime* is the frozen episode-cluster bootstrap replicate statistic produced by resampling complete regime episodes within state, retaining all eligible observations from each selected episode, reconstructing the observation-weighted sample, recomputing the frozen LRS-3 rank-decile construction fresh within every replicate, and then recomputing Delta_regime.

Percentile intervals are used directly. Experiment v1 does not apply BCa correction, Gaussian standard-error approximation, observation-level jackknife correction, studentization, or bootstrap-t construction. Cluster-level BCa is acknowledged as legitimate established methodology; it is not rejected as invalid. It is not selected for v1 because K7 permits inference with as few as eight contributing episodes, making delete-one-episode acceleration estimates potentially fragile at the authorization boundary, while the statistic itself is nonlinear/nonsmooth because episode resampling can alter rank-decile boundaries. No admissible pre-outcome evidence establishes that BCa correction is required, so the simpler percentile family is frozen for v1.

Empirical quantile convention -- CLOSED. All percentile bounds use Hyndman-Fan Type 7 linear interpolation. The implementation must specify the convention explicitly and must not rely silently on a library default. In NumPy-compatible implementation this is:

numpy.quantile(replicates, p, method="linear")

For sorted bootstrap replicate values:

x_(1) <= x_(2) <= ... <= x_(B)

and requested probability p, define the 1-indexed virtual rank:

h = 1 + (B - 1)p

If h is an integer:

Q_p = x_(h)

If h is fractional, define:

j = floor(h)
g = h - j

then:

Q_p = x_(j) + g * [x_(j+1) - x_(j)]

This generic convention is frozen independently of the current production replication count and remains the operative definition even if future change-control produces a different B in a later experiment version.

For frozen Experiment-v1 B_production = 15,000:

Lower endpoint, p=0.025:

h_lower = 1 + (15,000 - 1)(0.025)
        = 1 + 14,999(0.025)
        = 375.975

Therefore:

Q_0.025 = x_(375) + 0.975 * [x_(376) - x_(375)]

Upper endpoint, p=0.975:

h_upper = 1 + (15,000 - 1)(0.975)
        = 1 + 14,999(0.975)
        = 14,625.025

Therefore:

Q_0.975 = x_(14,625) + 0.025 * [x_(14,626) - x_(14,625)]

Symmetry check:

h_lower + h_upper = 375.975 + 14,625.025 = 15,001 = B + 1

The Item-2 tail-count diagnostic and the Item-3 quantile rank are distinct objects and must never be substituted for one another:

B * p -> expected number of bootstrap replicates lying in a tail in probability-space expectation

1 + (B - 1)p -> Type-7 empirical-quantile interpolation position

At B=15,000 and p=0.025, Bp=375 is therefore a valid Item-2 Monte Carlo-resolution diagnostic, while h=375.975 is the correct Type-7 lower-tail quantile position. The equality Bp=375 does not imply selection of the 375th order statistic without interpolation.

The Type-7 convention is selected as a deterministic, mainstream, directly implementable quantile definition that minimizes avoidable implementation ambiguity. It is not claimed to possess special inferential superiority over other established sample-quantile conventions. Its purpose here is reproducibility and mechanical precision: the exact same finite bootstrap sample must resolve to the exact same reported percentile bounds under every conforming implementation.
4. Permitted inferential claim wording -- CLOSED (Branches A, B, C, D, E1, E2, E3 all wording-closed; cross-branch integrity audit and symmetry check below).

Item 4 defines a deterministic, evidence-derived template family for reporting the outcome of Experiment v1 for a given instrument x horizon. Governing principle, applied throughout every branch below: diagnostic computability != resolution authority (I4). No branch below asserts what was or was not computed upstream or downstream of its own controlling disposition -- each branch states only the authorization/resolution consequence that its own frozen mechanism establishes. Mandatory shared preamble (all branches): Instrument: [BTC-USD / ETH-USD]. Horizon: [5s / 15s / 30s / 60s]. LRS-4 Experiment-v1 methodology identity: [version/commit]. Inherited frozen LRS-3 methodology identity: [canonical commit]. Gate-2 window disposition path: [exact H_path]. Resolved regime window: [4h / 24h / 1h / NOT_APPLICABLE]. If H_path is non-viable: Stage 2 conditioned analysis was not authorized or entered; Branch A applies; no K7 authorization status is asserted. If H_path is viable: Stage 2 conditioned analysis was entered; K7 status is reported per Branches B-E below.

BRANCH A -- Gate-2 non-viable (instrument-scoped; H_path in {PATHOLOGICALLY_FRAGMENTED, STRUCTURALLY_INSUFFICIENT, EPISTEMICALLY_INDETERMINATE}):

"For [instrument], Gate 2 did not authorize entry into Stage 2 conditioned analysis. The resolved window disposition was [exact H_path value]. The Window Evaluation history was [exact primary/fallback evaluation sequence], with controlling reason code(s) [exact applicable reason code(s)]. [If H_path = PATHOLOGICALLY_FRAGMENTED or STRUCTURALLY_INSUFFICIENT:] The frozen Gate-2 procedure produced a terminal non-viable structural disposition under Experiment-v1 methodology. [If H_path = EPISTEMICALLY_INDETERMINATE:] The frozen Gate-2 procedure could not resolve a viable structural disposition from the admissible evidence under Experiment-v1 methodology."

Branch A reports only Gate-2's own instrument-scoped disposition. No Delta_regime, K7 status, HIGH/LOW comparison, LRS-3 commentary, or downstream interpretation of any kind appears in Branch A.

BRANCH B -- K7 Layer 1-4 support failure (per-state; K7 operates at instrument x state x horizon, reported independently for HIGH and for LOW, never as a single merged finding):

Applicability: Gate 2 passed (H_path viable). Reported once per state s in {HIGH, LOW} that did not pass all of Layers L1-L4. A state passing all four is reported via the same skeleton's passing case, not a separate branch.

Per-state skeleton: "State [HIGH / LOW], instrument [instrument], horizon [horizon]: [If all four layers passed:] Layers L1 through L4 all passed for this state. [If layer L(k) is the earliest controlling failure:] Layers L1 through L(k-1) passed for this state. Layer L(k) failed: [controlling reason code], with [exact evidence-contract fields for L(k)]. Layers L(k+1) through L4, if any, were not reached in the sequential authorization chain for this state. Any mathematically defined downstream diagnostic values for this state may still be computed and retained as supplementary evidence, but remain resolution-inactive and cannot compete with or replace the L(k) finding."

Evidence-contract fields per layer (exact required reported values when that layer is the controlling failure):
- L1 (INSUFFICIENT_DECILE_CONSTRUCTION_SUPPORT): complete ten-decile count vector (N_D0...N_D9); set of failed deciles (N_d<2); EXTREME_DECILE_FAILURE flag.
- L2 (INSUFFICIENT_CONTRIBUTING_EPISODE_SUPPORT): horizon h; K^contrib_{s,h}; total structural K_s; count of structural episodes contributing zero observations at this horizon.
- L3 (INSUFFICIENT_EXTREME_DECILE_EPISODE_SUPPORT): horizon h; K_{s,h,D0}; K_{s,h,D9}; which extreme(s) failed; K_contrib cross-reference.
- L4 (EXCESSIVE_EXTREME_DECILE_EPISODE_CONCENTRATION): horizon h; C_{2,D0} and/or C_{2,D9} (whichever triggered); which extreme(s) failed.

Instrument x horizon bridge (stated once, after both per-state blocks): "Both HIGH and LOW must independently pass Layers L1 through L4 before the instrument x horizon analysis is authorized to proceed to Layer 5 and primary inference. [If either or both states failed:] Because [state(s)] did not complete the L1-L4 authorization chain, the instrument x horizon analysis is not authorized to proceed to Layer 5 or primary inference. Any mathematically defined downstream diagnostic quantities may be computed and retained as supplementary evidence, but they are resolution-inactive and cannot alter or replace the controlling state-level K7 disposition(s). [If both states passed:] Both HIGH and LOW independently passed Layers L1 through L4. The instrument x horizon analysis is authorized to proceed to the full-sample Delta_hat_regime interpretation and, where applicable under the frozen zero-contrast and Layer-5 rules, subsequent primary inference."

BRANCH C -- Zero full-sample contrast (instrument x horizon-scoped; HIGH and LOW both passed L1-L4; Delta_hat_regime = 0):

"For [instrument] at the [horizon] forward-return horizon, both HIGH and LOW independently passed Layers L1 through L4. The full-sample conditioned contrast, Delta_hat_regime = (D9-D0)_HIGH - (D9-D0)_LOW, equals exactly zero. Record NOT_APPLICABLE_ZERO_FULL_SAMPLE_CONTRAST. There is no directional proposition for Layer 5 to test. Layer 5 is not applicable and receives neither a PASS nor an INSTRUMENT_DAY_DIRECTIONAL_FRAGILITY disposition. No primary bootstrap interval is authorized for inferential reporting under this disposition."

Worked example: (D9-D0)_HIGH = +0.72bp, (D9-D0)_LOW = +0.72bp -> Delta_hat_regime = 0.00bp. Note explicitly: zero contrast does not imply either state's own conditioned D9-D0 statistic is itself zero or negligible -- both may be materially nonzero while their difference is exactly zero.

BRANCH D -- Layer-5 directional fragility (instrument x horizon-scoped; HIGH and LOW both passed L1-L4; Delta_hat_regime != 0; at least one leave-one-instrument-day-out deletion is non-computable, exact-zero, or sign-reversed):

"For [instrument] at the [horizon] forward-return horizon, both HIGH and LOW independently passed Layers L1 through L4. The full-sample conditioned contrast, Delta_hat_regime = (D9-D0)_HIGH - (D9-D0)_LOW, equals [exact value] bp (sign: [positive/negative]). Leave-one-instrument-day-out evaluation was performed over the contributing-day universe D_contrib (n=[count] instrument-days). At least one deletion did not preserve the existence or sign of the full-sample contrast: [count] deletion(s) produced a non-computable contrast (NONCOMPUTABLE_DAY_REMOVALS), [count] produced an exact-zero contrast (ZERO_CONTRAST_DAY_REMOVALS), and [count] produced a sign reversal (SIGN_FLIP_DAY_REMOVALS). Record INSTRUMENT_DAY_DIRECTIONAL_FRAGILITY: the reported directional finding is not robust to the removal of at least one contributing instrument-day. No primary bootstrap interval is authorized for inferential reporting under this disposition. Magnitude sensitivity across leave-one-day-out deletions is available as supplementary descriptive information only and carries no bearing on this disposition."

Worked example: Delta_hat_regime = +0.85bp (HIGH stronger than LOW). D_contrib = 25 instrument-days. 23 deletions preserve sign(+); 1 deletion produces Delta_hat^(-d) = -0.15bp (sign reversal); 1 deletion produces a non-computable contrast (insufficient remaining D9 decile support). NONCOMPUTABLE_DAY_REMOVALS=1, SIGN_FLIP_DAY_REMOVALS=1, ZERO_CONTRAST_DAY_REMOVALS=0. Despite 23 of 25 deletions preserving the finding, the categorical (non-fractional) rule means even one qualifying deletion controls the disposition.

BRANCH E1/E2/E3 -- full K7 + Layer-5 authorization, primary bootstrap interval reported (instrument x horizon-scoped; HIGH and LOW both passed L1-L4; Delta_hat_regime != 0; Layer 5 PASS, meaning every leave-one-instrument-day-out deletion over D_contrib produced a computable, nonzero contrast preserving the sign of the full-sample contrast):

Shared opening (all three sub-branches): "For [instrument] at the [horizon] forward-return horizon, both HIGH and LOW independently passed Layers L1 through L4. The full-sample conditioned contrast, Delta_hat_regime = (D9-D0)_HIGH - (D9-D0)_LOW, equals [exact value] bp ([positive/negative]). Layer 5 passed: every leave-one-instrument-day-out deletion over the contributing-day universe D_contrib (n=[count] instrument-days) produced a computable, nonzero contrast preserving the sign of the full-sample contrast. The frozen episode-cluster bootstrap (B_production=15,000 replicates) produced a marginal 95% percentile interval for Delta_regime of [Q_0.025, Q_0.975] = [[lower] bp, [upper] bp]."

E1 -- 0 in CI_95% (interval includes zero): "This interval includes zero. No directional finding is reported for this instrument x horizon. This is an authorized but directionally unresolved Experiment-v1 result. It does not establish equality of the HIGH- and LOW-regime D9-D0 research effects, and it does not establish the absence of regime-dependent heterogeneity. It establishes only that the frozen marginal 95% interval does not resolve the direction of Delta_regime for this prespecified instrument x horizon estimand."

Worked example (E1): (D9-D0)_HIGH=+1.05bp, (D9-D0)_LOW=+0.64bp, Delta_hat_regime=+0.41bp, CI_95%=[-0.18,+0.96]bp. Delta_hat_regime != 0 (not Branch C); 0 in CI_95% means direction is not resolved by authorized primary inference.

E2 -- CI_95% entirely positive (Q_0.025 > 0): "This interval excludes zero and lies entirely above zero. Experiment v1 reports a directional finding for this prespecified instrument x horizon estimand: the marginal 95% percentile interval for Delta_regime lies entirely above zero. Under the frozen definition Delta_regime=(D9-D0)_HIGH-(D9-D0)_LOW, this supports a HIGH-larger-than-LOW directional interpretation of the conditioned D9-D0 research-effect contrast for this specific estimand. This inference is marginal to this single instrument x horizon estimand only. Experiment v1 does not claim simultaneous or family-wise coverage across instruments or horizons, and this result alone does not authorize a cross-estimand discovery claim. It does not establish causality, executable or cost-adjusted profitability, magnitude stability under instrument-day deletion, generalization beyond the frozen Experiment-v1 design, or any operational or trading-use conclusion for LRS-3."

Worked example (E2): (D9-D0)_HIGH=-0.20bp, (D9-D0)_LOW=-0.80bp, Delta_regime=+0.60bp. Both conditioned effects individually negative; HIGH-larger-than-LOW directional finding holds regardless (Delta_regime>0 != HIGH>0).

E3 -- CI_95% entirely negative (Q_0.975 < 0): "This interval excludes zero and lies entirely below zero. Experiment v1 reports a directional finding for this prespecified instrument x horizon estimand: the marginal 95% percentile interval for Delta_regime lies entirely below zero. Under the frozen definition Delta_regime=(D9-D0)_HIGH-(D9-D0)_LOW, this supports a HIGH-smaller-than-LOW directional interpretation of the conditioned D9-D0 research-effect contrast for this specific estimand. This inference is marginal to this single instrument x horizon estimand only. Experiment v1 does not claim simultaneous or family-wise coverage across instruments or horizons, and this result alone does not authorize a cross-estimand discovery claim. It does not establish causality, executable or cost-adjusted profitability, magnitude stability under instrument-day deletion, generalization beyond the frozen Experiment-v1 design, or any operational or trading-use conclusion for LRS-3."

Worked example (E3): (D9-D0)_HIGH=+0.30bp, (D9-D0)_LOW=+0.84bp, Delta_hat_regime=-0.54bp, CI_95%=[-0.91,-0.12]bp. Both conditioned effects individually positive; HIGH-smaller-than-LOW directional finding holds regardless (Delta_regime<0 != HIGH negative).

E2/E3 symmetry audit: interval sign (entirely>0 / entirely<0); frozen contrast definition identical (HIGH-LOW); interpretation (HIGH-larger-than-LOW / HIGH-smaller-than-LOW); individual HIGH sign implied (no / no); marginal-only (yes/yes); family-wise claim (no/no); causal claim (no/no); profitability claim (no/no); magnitude-stability claim (no/no); operational LRS-3 conclusion (no/no). No asymmetric claim present between E2 and E3 beyond the necessary sign/direction reversal.

5. Final methodology-integrity audit -- CLOSED / PASS. All frozen Experiment-v1 methodology items passed final integrity verification before Stage 1 implementation authorization.

Everything in Parts A-J not listed above is CLOSED. Any future change to a CLOSED item is an Experiment v2 methodology change requiring independent freeze before conditioned outcomes are inspected, per the terminal-outcomes and change-control rules established throughout.

---
## POST-FREEZE IMPLEMENTATION FINDING -- GATE-2 EVALUATION-DOMAIN SPECIFICATION OMISSION

**Status:** IMPLEMENTATION-BLOCKING SPECIFICATION OMISSION IDENTIFIED POST-FREEZE / PRE-OUTCOME

During Stage-1 implementation, after Experiment v1 methodology was formally frozen and before inspection of any conditioned outcomes, an implementation-blocking specification omission was identified in Part F.

F4 and F6 require a "current Gate-2 evaluation domain" whose temporal boundaries determine episode boundary censoring, the fixed `K_total` episode population, and the fixed `T_classified` valid-classified-time population. Experiment v1 defines the behavior of these quantities relative to the evaluation domain, but does not deterministically define the temporal start and end boundaries of that domain.

Targeted review of the canonical Experiment-v1 SRC found no separate definition under evaluation-domain, evaluation-period, retained-observation, target-domain, study/sample interval, corpus-span, date-range, or related terminology sufficient to resolve those temporal boundaries without introducing a new methodological rule.

This omission prevents faithful implementation of the F4/F6 morphology and censoring calculations required to determine, where applicable:

- `EXCESSIVE_EPISODE_TURNOVER`
- `TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE`
- `INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING`

Because these reason codes participate in Gate-2 resolution and can alter primary-window viability, directional fallback, or termination, the missing evaluation-domain boundary rule is methodological rather than a discretionary software-interface choice.

No interpretation of the missing Gate-2 evaluation-domain boundary has been adopted. No candidate boundary definition has been frozen or implemented. No conditioned LRS-4 outcome comparison, `Delta_regime`, HIGH-versus-LOW conditioned effect, or other Stage-2 conditioned outcome has been inspected as part of resolving this omission.

`gate2_diagnostics.py` has not been started. Gate-2 censoring/morphology implementation is blocked at this specification boundary.

Previously completed Stage-1 primitives whose frozen behavior does not depend on the missing Gate-2 evaluation-domain definition remain unchanged. This finding does not retroactively modify their frozen methodological contracts or their completed structural tests.

Under the existing Experiment-v1 change-control rule, Parts A-J are CLOSED and any future change to a CLOSED item requires an Experiment-v2 methodology change with an independent freeze before conditioned outcomes are inspected. Accordingly, this finding documents the Experiment-v1 implementation blockage only; it does not repair, reinterpret, amend, or otherwise modify the frozen Experiment-v1 methodology.

Resolution of the Gate-2 evaluation-domain definition is deferred to Experiment v2 under outcome-blind change control.

End of Experiment v1 methodology freeze. This document is the canonical LRS-4 Experiment-v1 research-design specification.
