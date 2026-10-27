# LRS4 — Invariant Registry Source Extract

**STAGING ONLY — NOT CANONICAL / NOT FROZEN**

## I01

Provenance: ORIGINAL | f7f7fa69-attachment.txt:15

| **I01** | `O_candidate(s,d,W)` depends only on inherited LRS3 candidacy and legitimate entry of `W`; no SH/regime/Gate2/path/final result may affect membership. | Integrity failure |

## I02

Provenance: ORIGINAL | f7f7fa69-attachment.txt:16

| **I02** | Every candidate `T` must resolve exactly one strict-C10 predecessor `G(T)` satisfying `G<T`; exact-grid observations consume the preceding endpoint. | Integrity failure |

## I03

Provenance: ORIGINAL | f7f7fa69-attachment.txt:17

| **I03** | `G_candidate` is the deduplicated set of candidate strict-C10 endpoints. | Integrity failure |

## I04

Provenance: ORIGINAL | f7f7fa69-attachment.txt:18

| **I04** | `SH(s,d,W)` exists **iff** `|O_candidate|>0`; empty candidate set ⇒ SH undefined, never ELIGIBLE/INELIGIBLE. | Integrity failure |

## I05

Provenance: ORIGINAL | f7f7fa69-attachment.txt:19

| **I05** | For nonempty candidates, aggregate SH is ELIGIBLE **iff every unique candidate endpoint** passes W-specific endpoint SH authorization. | Integrity failure |

## I06

Provenance: ORIGINAL | f7f7fa69-attachment.txt:20

| **I06** | A candidate-bearing day contributes **all or none** of its candidates to D1 according to aggregate SH. No partial day inclusion. | Integrity failure |

## I07

Provenance: ORIGINAL | f7f7fa69-attachment.txt:21

| **I07** | D1 contains observations only and cannot be filtered by D3, regime state, Gate2, `SH_path`, or final disposition. | Integrity failure |

## I08

Provenance: ORIGINAL | f7f7fa69-attachment.txt:22

| **I08** | `D1=∅` ⇒ D0 terminal `NO_TARGET_OBSERVATION_POPULATION`; C1 vs C2 provenance remains distinguishable. No fallback or synthetic Gate2 result. | `D0_TERMINAL` |

## I09

Provenance: ORIGINAL | f7f7fa69-attachment.txt:23

| **I09** | `D1≠∅` ⇒ D0 passes. No additional minimum-observation threshold may be introduced. | Integrity failure if violated |

## I10

Provenance: ORIGINAL | f7f7fa69-attachment.txt:24

| **I10** | D2 may be constructed only after D0 passes and must equal the complete 5-minute grid from `G(T_first)` through `G(T_last)`, inclusive. | Integrity failure |

## I11

Provenance: ORIGINAL | f7f7fa69-attachment.txt:25

| **I11** | D2 boundaries derive **only** from D1 extrema; excluded candidates cannot establish or extend them. | Integrity failure |

## I12

Provenance: ORIGINAL | f7f7fa69-attachment.txt:26

| **I12** | Once constructed, D2 is immutable. Interior exclusions or D3 failures never create holes, shrink, expand, or re-anchor it. | Integrity failure |

## I13

Provenance: ORIGINAL | f7f7fa69-attachment.txt:27

| **I13** | A one-cell D2 where `G_first=G_last` is valid and must not be rejected merely for its size. | Integrity failure |

## I14

Provenance: ORIGINAL | f7f7fa69-attachment.txt:28

| **I14** | Exactly one authoritative `D3_ADMISSIBLE(G,W)` exists for **every** endpoint in D2. | Integrity failure |

## I15

Provenance: ORIGINAL | f7f7fa69-attachment.txt:29

| **I15** | D3 must satisfy `SH_AUTHORIZED(G,W) AND REGIME_STATE_VALID(G,W)` with SH authorization evaluated first. | Integrity failure |

## I16

Provenance: ORIGINAL | f7f7fa69-attachment.txt:30

| **I16** | `SH_AUTHORIZED=FALSE` forces D3 FALSE regardless of mechanically available HIGH/LOW state; mechanically computed unauthorized state has no classification authority. | Integrity failure |

## I17

Provenance: ORIGINAL | f7f7fa69-attachment.txt:31

| **I17** | D3 FALSE leaves the cell in D2 but prevents environmental classification/episode continuity; failure provenance remains auditable. | Integrity failure |

## I18

Provenance: ORIGINAL | f7f7fa69-attachment.txt:32

| **I18** | For every `T∈D1`, current-W regime eligibility equals authoritative D3 at strict-C10 `G(T)` and cannot mutate D1 or D2. | Integrity failure |

## I19

Provenance: ORIGINAL | f7f7fa69-attachment.txt:33

| **I19** | D4 is produced by one chronological sweep over the **complete D3 timeline**, not observation-filtered D1 endpoints. | Integrity failure |

## I20

Provenance: ORIGINAL | f7f7fa69-attachment.txt:34

| **I20** | Every episode is a maximal contiguous same-state run of D3-admissible cells. Exactly three boundary causes exist: `STATE_CHANGE`, `D3_INADMISSIBILITY`, `D2_BOUNDARY`. | Integrity failure |

## I21

Provenance: ORIGINAL | f7f7fa69-attachment.txt:35

| **I21** | D3-inadmissible cells terminate continuity, form no episode, create no censoring, and cannot be bridged. | Integrity failure |

## I22

Provenance: ORIGINAL | f7f7fa69-attachment.txt:36

| **I22** | Only literal D2 boundaries may censor. Pre-D2 left tracing uses inherited state-transition / inherited-validity-discontinuity authority without extending D2. | Integrity failure |

## I23

Provenance: ORIGINAL | f7f7fa69-attachment.txt:37

| **I23** | Every episode reaching `G_last` is right-censored; post-D2 evidence cannot remove/rescue that flag. | Integrity failure |

## I24

Provenance: ORIGINAL | f7f7fa69-attachment.txt:38

| **I24** | Left/right censoring are independent; a one-cell episode may carry either/both/neither and has observed duration exactly 5 minutes. | Integrity failure |

## I25

Provenance: ORIGINAL | f7f7fa69-attachment.txt:39

| **I25** | `K_HIGH`, `K_LOW`, `K_total`, and `T_classified` derive exclusively from authoritative D3/D4 environmental topology. | Integrity failure |

## I26

Provenance: ORIGINAL | f7f7fa69-attachment.txt:40

| **I26** | `K_total = 0 ⇔ T_classified = 0`. | Integrity failure |

## I27

Provenance: ORIGINAL | f7f7fa69-attachment.txt:41

| **I27** | `K_total=0` with positive current-W eligible-observation count is impossible as an ordinary realization. | Integrity failure |

## I28

Provenance: ORIGINAL | f7f7fa69-attachment.txt:42

| **I28** | `N_LRS4_ELIGIBLE=0` is a legitimate Z1 state; G-NUMERIC.4 becomes `NOT_APPLICABLE_ZERO_ELIGIBLE_OBSERVATIONS` and must not invent `p_min=0` or a Gate2 failure. | Ordinary diagnostic state |

## I29

Provenance: ORIGINAL | f7f7fa69-attachment.txt:43

| **I29** | `K_total=0` makes both G-NUMERIC.6 subdiagnostics independently `NOT_APPLICABLE_ZERO_STRUCTURAL_EPISODES`; neither contributes to `R_W`, while G-NUMERIC.5 remains operative. | Ordinary diagnostic state |

## I30

Provenance: ORIGINAL | f7f7fa69-attachment.txt:44

| **I30** | `R_W`, `A_W`, and `H_W` remain distinct: `R_W` complete reasons, `A_W` sole routing authority, `H_W` diagnostic only. | Integrity failure |

## I31

Provenance: ORIGINAL | f7f7fa69-attachment.txt:45

| **I31** | D0 cannot invoke F1 fallback. F1 directional fallback is reachable only after Gate2 and only through inherited Gate2 routing authority. | Integrity failure |

## I32

Provenance: ORIGINAL | f7f7fa69-attachment.txt:46

| **I32** | `WindowEvaluationResult` has exactly three non-coercible variants: D0 termination, completed `E_W`, `INTEGRITY_FAILURE`. | Integrity failure |

## I33

Provenance: ORIGINAL | f7f7fa69-attachment.txt:47

| **I33** | `InstrumentPathResult` has exactly four non-coercible variants: `VIABLE`, `GATE2_TERMINAL`, `D0_TERMINAL`, `INTEGRITY_FAILURE`. | Integrity failure |

## I34

Provenance: ORIGINAL | f7f7fa69-attachment.txt:48

| **I34** | `W*` exists **iff** the Instrument Path is `VIABLE`; no terminal/integrity path may synthesize one. | Integrity failure |

## I35

Provenance: ORIGINAL | f7f7fa69-attachment.txt:49

| **I35** | `W_evidence(s,d)` contains exactly entered windows having nonempty candidate sets / defined `SH(s,d,W)`. Zero-candidate entered windows abstain. | Integrity failure |

## I36

Provenance: ORIGINAL | f7f7fa69-attachment.txt:50

| **I36** | If `W_evidence≠∅`, `SH_path` equals AND across exactly those evidentiary contributors. A defined INELIGIBLE contributor cannot abstain. | Integrity failure |

## I37

Provenance: ORIGINAL | f7f7fa69-attachment.txt:51

| **I37** | `W_evidence=∅` ⇒ `SH_path=UNDEFINED`; this cannot become an observation status. Under the inherited primary-4h path, it implies no inherited LRS3-eligible observations require disposition that day. | Integrity failure if coerced |

## I38

Provenance: ORIGINAL | f7f7fa69-attachment.txt:52

| **I38** | Final projection executes **only** for a VIABLE path and inherited LRS3-eligible observations requiring disposition. | Integrity failure |

## I39

Provenance: ORIGINAL | f7f7fa69-attachment.txt:53

| **I39** | Final projection order is fixed: `SH_path` first → if eligible, strict C10 → authoritative **existing W*** D3 artifact. | Integrity failure |

## I40

Provenance: ORIGINAL | f7f7fa69-attachment.txt:54

| **I40** | Final projection must reuse the exact authoritative W* D3 artifact; it may not recompute SH authorization, RVOL, thresholds, regime state, or D3. | Integrity failure |

## I41

Provenance: ORIGINAL | f7f7fa69-attachment.txt:55

| **I41** | Final ordinary disposition is exactly one of the three existing values: source-history ineligible, regime ineligible, eligible. | Integrity failure otherwise |

## I42

Provenance: ORIGINAL | f7f7fa69-attachment.txt:56

| **I42** | `FinalObservationResult(T)` is either a successfully resolved ordinary disposition **or** `INTEGRITY_FAILURE`, never both. | Integrity failure |

## I43

Provenance: ORIGINAL | f7f7fa69-attachment.txt:57

| **I43** | `FinalEligible(T)` exists only when an ordinary disposition exists and is TRUE iff that disposition is `LRS4_ELIGIBLE`. | Integrity failure |

## I44

Provenance: ORIGINAL | f7f7fa69-attachment.txt:58

| **I44** | Final-projection integrity failure for `T` must not retroactively alter `InstrumentPathResult`, `W*`, completed Window Evaluations, or another observation's result. | Fail closed for T |

## I45

Provenance: ORIGINAL | f7f7fa69-attachment.txt:59

| **I45** | Integrity failure at any layer cannot be translated into `R_W`, `A_W`, `H_W`, D0, source-history exclusion, regime ineligibility, or another ordinary methodological result. | Fail closed |

## I46

Provenance: ORIGINAL | f7f7fa69-attachment.txt:60

| **I46** | Partial ordinary results existing before integrity failure may remain as audit evidence but acquire **no downstream authorization authority**. | Fail closed |

## I47

**UNRESOLVED PROVENANCE — NOT EXTRACTED**
Requires separately reviewed reconstruction or adjudicated replacement.

## I48

Provenance: ORIGINAL | e4f4ad03-attachment.txt:7

> **I48 — D4 upstream immutability.**  
> `D4_W(s)` may partition and summarize the fixed `D2_W(s)` domain but must not resize or rebuild D2, alter any authoritative D3 value, or rebuild D3.  
> **Violation → methodology-integrity failure.**

## I49

**UNRESOLVED PROVENANCE — NOT EXTRACTED**
Requires separately reviewed reconstruction or adjudicated replacement.

## I50

Provenance: ADJUDICATED | 607ce4a3-attachment.txt:7

> **I50 — Eligibility-layer naming discipline.**  
> Whenever more than one eligibility layer is in scope, an implementation artifact, schema, diagnostic, or interface must identify the applicable eligibility layer explicitly rather than use an unqualified `eligibility` field/status whose authority is ambiguous. Inherited LRS3 eligibility, source-history eligibility, current-Window regime eligibility, and final observation eligibility must remain semantically distinguishable.  
> **Violation → interface/schema non-compliance. Verified through static interface-conformance review; it is not itself a runtime discriminated `INTEGRITY_FAILURE` result.**

## I51

Provenance: ADJUDICATED | 607ce4a3-attachment.txt:15

> **I51 — Authoritative-object non-substitutability.**  
> A methodological consumer must consume the authoritative object required by its interface. Predictable implication, numerical equality, compatible Boolean value, shared provenance, or reconstructibility does not authorize substitution by a different methodological object, including an object with different index arity, semantic type, dependency stage, or producer.  
> **Violation → methodology-integrity failure.**

## I52

Provenance: ADJUDICATED | 607ce4a3-attachment.txt:21

> **I52 — Single authoritative producer.**  
> Within its applicable Window Evaluation or final-path projection, each authoritative methodological object must have exactly one authoritative producer. Derived evidence may validate, reconcile, or report that object but must not become a competing authoritative producer.  
> **Violation → methodology-integrity failure.**

## I53

Provenance: ADJUDICATED | 607ce4a3-attachment.txt:27

> **I53 — Control/provenance type preservation.**  
> `D0Termination`, `DiagnosticRecord`, `R_W`, `A_W`, `H_W`, `ApplicabilityStatus`, `BoundaryCause`, `CensoringStatus`, and `Episode` are distinct authority-bearing control/provenance object types and must not be coerced into or substituted for one another. Their respective provenance and semantic roles must remain explicit.  
> **Violation → methodology-integrity failure.**

