# LRS4 Family B — Selected Original Rows

STAGING ONLY — NOT CANONICAL OR FROZEN

| **B01** Primary window | frozen v1 F1 | Start new ordinary Instrument Path | First Window Evaluation is 4h | No 1h/24h initial window |
| **B02** Turnover-only routing | frozen v1 F1 + G3/G5 | Primary 4h has turnover directional code only, no terminal | `A_4h=EVALUATE_24H_FALLBACK` | No 1h/adaptive choice |
| **B03** Persistence-only routing | frozen v1 F1 + G3/G5 | Primary 4h has persistence directional code only, no terminal | `A_4h=EVALUATE_1H_FALLBACK` | No 24h/adaptive choice |
| **B04** Directional conflict | frozen v1 F1 + G3/G5 | Both directional codes, no terminal | Derived `CONFLICTING_DIRECTIONAL_FAILURES`; terminate | Must not choose either fallback |
| **B05** Structural terminal precedence | frozen v1 G2/G1/G5 | ≥1 structural terminal, optionally directional/epistemic codes too | terminate; structural terminal controls disposition precedence | No fallback |
| **B06** Epistemic terminal precedence | frozen v1 G2/G5 | Epistemic terminal, no structural terminal, optionally directional | terminate epistemically | Directional code cannot authorize fallback |
| **B07** No failures | frozen v1 G5 | `R_W` contains no failures | `A_W=PROCEED_TO_STAGE_2`, `H_W=VIABLE` | No fallback/termination |
| **B08** Full reason-set retention | frozen v1 G1/G6–G9 | Multiple simultaneous reason codes | Full triggered reason set retained regardless of precedence | Must not discard dominated reasons |
| **B09** Evaluation-order independence | frozen v1 G1/G6–G9 | Same triggered codes supplied/evaluated in different implementation orders | Same `R_W`,`A_W`,`H_W` | Documentation/code ordering cannot alter result |
| **B10** Fallback turnover recurrence | frozen v1 F1/G5 | 24h fallback itself triggers turnover or another failure | fallback terminates | No second fallback |
| **B11** Fallback persistence recurrence | frozen v1 F1/G5 | 1h fallback itself triggers persistence or another failure | fallback terminates | No second fallback |
| **B12** Cross-direction second hop forbidden | frozen v1 F1 | Attempt `4h→24h→1h` or `4h→1h→24h` | Path rejected fail-closed | No three-window path |
| **B13** Primary-only shape | frozen v1 G0/G-path | 4h proceeds or terminates without fallback | Path exactly `[4h]` | No phantom fallback |
| **B14** 24h shape | frozen v1 G0/G-path | Exact 24h authorization from primary | Path exactly `[4h,24h]` | No 1h evaluation |
| **B15** 1h shape | frozen v1 G0/G-path | Exact 1h authorization from primary | Path exactly `[4h,1h]` | No 24h evaluation |
| **B16** Shape exhaustiveness | frozen v1 G0/G-path | Enumerate accepted ordinary v1 paths | Only the three frozen shapes are accepted | Any other ordinary path rejected |
| **B17** Primary viable mapping | frozen v1 G-path | `A_4h=PROCEED_TO_STAGE_2` | legacy `H_path=VIABLE` | — |
| **B18** Primary terminal mapping | frozen v1 G-path | `A_4h=TERMINATE_INSTRUMENT_V1` | `H_path=H_4h` | Must not fabricate fallback provenance |
| **B19** 24h viable mapping | frozen v1 G-path | Authorized 24h fallback, fallback viable | `H_path=VIABLE_AFTER_24H_FALLBACK` | — |
| **B20** 24h failed mapping | frozen v1 G-path | Authorized 24h fallback, fallback nonviable | `H_path=H_24h` | No fallback-specific failure label invented |
| **B21** 1h viable mapping | frozen v1 G-path | Authorized 1h fallback, fallback viable | `H_path=VIABLE_AFTER_1H_FALLBACK` | — |
| **B22** 1h failed mapping | frozen v1 G-path | Authorized 1h fallback, fallback nonviable | `H_path=H_1h` | No fallback-specific failure label invented |
| **B23** Missing requested fallback | frozen v1 G-path | Primary requests fallback but corresponding Window Evaluation absent | Path invalid / fail closed | Cannot infer terminal/viable completion |
| **B24** Unauthorized fallback | frozen v1 G-path | Fallback exists without exact corresponding primary authorization | Path invalid / fail closed | Fallback cannot self-authorize |
| **B25** Fallback requests fallback | frozen v1 G-path | Any fallback emits another fallback request | Path invalid / fail closed | No recursive/adaptive fallback |
| **B26** Path length bound | frozen v1 G-path | Attempt >2 Window Evaluations | Path invalid / fail closed | No third Window Evaluation |
| **B27** Unique terminal legacy disposition | frozen v1 G-path | Any accepted ordinary v1 path | Exactly one `H_path` before Stage2 consideration | Zero/multiple `H_path` forbidden |
| **B28** `H_W` alone insufficient | frozen v1 G0 | Same/compatible `H_W` under differing control-flow positions | Path completion determined from `A_W` + full permitted-path state | `H_W` alone cannot establish completion/Stage2 eligibility |
| **B29** Frozen-universe audit validity | frozen v1 K6 | Unchanged closed reason-code universe and decision architecture | Existing reachability/exclusivity/determinism/non-vacuity/fail-closed audit remains applicable | — |
| **B30** Reason-universe mutation | frozen v1 K6 | Add/remove/change Gate2 reason-code universe | Affected K6 audit conclusions invalidated; re-audit required before reliance | Must not silently inherit old PASS |
| **B31** Decision-architecture mutation | frozen v1 K6 | Change routing/precedence/path architecture | Affected K6 conclusions invalidated; re-audit required | No Stage1/Stage2 reliance on stale audit |
| **B32** General censor-certification rule | frozen v1 F4 | Censored episode admits multiple true durations consistent with available boundary information | Morphology category may be certified only if that category is invariant across **all** durations consistent with censoring information | Must not classify from one selected/imputed duration |
| **B33** Definite LONG from lower bound | frozen v1 F4 | Censored episode whose observed/lower-bound duration already exceeds `2W` | Episode is definitively LONG | Unknown terminal duration must not erase a category already invariant under every admissible extension |
| **B34** Below SHORT threshold is insufficient | frozen v1 F4 | Censored episode has observed/lower-bound duration `<0.5W`, but censoring permits longer true duration | SHORT is **not** certified merely from the observed lower bound | Must not treat observed duration as completed duration |
| **B35** Exact-threshold semantics | frozen v1 F3/F4 | Censored lower bound exactly at applicable morphology threshold | Apply frozen F3 threshold inequality exactly; do not silently convert strict threshold into inclusive threshold | No `>`↔`≥` or `<`↔`≤` drift |
| **B36** Censor extension monotonicity | frozen v1 F4 | Increase admissible upper duration while preserving same lower-bound evidence | Any previously uncertifiable category remains uncertified unless invariance across the new full admissible set is established | More uncertainty cannot manufacture certainty |
| **B37** `P_short^LB` construction | frozen v1 F4/F6 | Mix definite SHORT, definite non-SHORT, and censor-ambiguous episodes | Lower bound counts only episode mass guaranteed to satisfy SHORT under all censor-consistent durations | Ambiguous episode cannot be promoted into guaranteed-short mass |
| **B38** `P_short^UB` construction | frozen v1 F4/F6 | Same topology | Upper bound includes all episode mass that could satisfy SHORT under censor-consistent durations | Potentially-short ambiguous mass must not be excluded |
| **B39** Short-turnover definite failure | frozen v1 F4/F6 | `P_short^LB > 1/3` | `EXCESSIVE_EPISODE_TURNOVER` definitely fires | Censoring cannot downgrade a failure true under every admissible realization |
| **B40** Short-turnover definite pass | frozen v1 F4/F6 | `P_short^UB ≤ 1/3` | Turnover diagnostic definitely passes | Must not fire turnover reason |
| **B41** Short-turnover straddle | frozen v1 F4/F6 | `P_short^LB ≤ 1/3 < P_short^UB` | Turnover statistic is censor-indeterminate | Must not force PASS or FAIL |
| **B42** `P_long,time` bound construction | frozen v1 F4/F6 | Classified-time topology contains censor-ambiguous long-duration contribution | Construct lower/upper persistence bounds according to frozen duration/time-weighting mechanics | Must not substitute episode-count prevalence for classified-time prevalence |
| **B43** Persistence definite failure | frozen v1 F4/F6 | Persistence bounds establish frozen `>1/2` failure under every admissible realization | `TOO_FEW_EPISODES_FROM_EXCESSIVE_PERSISTENCE` definitely fires | No indeterminate downgrade |
| **B44** Persistence definite pass | frozen v1 F4/F6 | Persistence bounds establish `≤1/2` under every admissible realization | Persistence diagnostic passes | Must not emit persistence reason |
| **B45** Persistence straddle | frozen v1 F4/F6 | Persistence interval straddles frozen `1/2` boundary | Persistence statistic is censor-indeterminate | Must not force PASS/FAIL |
| **B46** Turnover indeterminacy code | frozen v1 F4/Gate2 | Turnover bound interval straddles its decision threshold | Emit applicable `INDETERMINATE_EPISODE_MORPHOLOGY_FROM_BOUNDARY_CENSORING` evidence according to frozen F4/Gate2 semantics | Must not convert uncertainty into directional turnover failure |
| **B47** Persistence indeterminacy code | frozen v1 F4/Gate2 | Persistence bound interval straddles its threshold | Same censor-indeterminacy mechanism applies to persistence statistic | Must not fabricate persistence failure |
| **B48** Turnover suppression locality | frozen v1 F4 | Turnover is censor-indeterminate while persistence is determinately evaluable | Suppress/withhold only the affected turnover statistic/result as frozen F4 requires; persistence still evaluates | Turnover uncertainty must not suppress persistence |
| **B49** Persistence suppression locality | frozen v1 F4 | Persistence censor-indeterminate; turnover determinately evaluable | Persistence alone receives applicable suppression/indeterminacy handling; turnover still evaluates | Persistence uncertainty must not suppress turnover |
| **B50** Dual indeterminacy | frozen v1 F4 | Both statistics independently straddle | Each retains its own affected-statistic provenance | Must not merge two diagnostic records merely because they share censoring cause |
| **B51** Unaffected Gate2 diagnostics survive | frozen v1 F4/Gate2 | One or both morphology statistics censor-indeterminate while unrelated Gate2 diagnostics remain computable | Unaffected diagnostics continue evaluating normally | F4 indeterminacy must not globally abort Gate2 diagnostic construction unless frozen control architecture separately requires termination |
