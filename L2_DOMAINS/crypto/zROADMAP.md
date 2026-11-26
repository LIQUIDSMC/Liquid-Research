# Crypto Domain — Roadmap

> This document records the current roadmap state for L2 Crypto.
> See `zMISSION_CONTROL.md` for detailed operational and research status,
> `zREADME.md` for Crypto orientation and boundaries, and
> `L1_CORE/market_data_platform/market_data/zROADMAP.md` for shared
> Market Data Platform authority.

Last updated: 2026-09-18
Research state anchored to closure baseline: `a622e42`

## Roadmap Status

### Completed

- Shared L1 Coinbase BTC-USD and ETH-USD collection and canonical storage are
  operational.
- The causal trade-flow research sequence is closed through fixed-horizon
  gross-edge v1 and ETH replication v2 at baseline `a622e42`. The specific
  ETH LONG Post-Entry Continuation H1 was rejected under the frozen v2 design;
  `zMISSION_CONTROL.md` records the scope of that result.

### Paused

- Cost-stress/economic-feasibility research is NOT STARTED / PAUSED.

### Open

- No next research experiment is selected or authorized by this document.

This roadmap does not commit to a timeline or to specific future deliverables.

Detailed current limitations and evidence boundaries are maintained in
`zMISSION_CONTROL.md`.

## Proposed Development Roadmap — NOT YET APPROVED

Status: PLANNING DRAFT / NO RESEARCH EXECUTION AUTHORIZATION.
This section defines proposed development checkpoints, not approved
experiments, scientific findings, or permission to access production data.

Historical gross-edge v1 and ETH replication v2 remain closed.
The specific ETH LONG H1 rejection remains limited to frozen v2.
Cost-stress remains paused. Original Candidate D D0 remains blocked.
The H2 reserve remains sealed.

### R01 — Research Governance and Roadmap

- [x] MC01 — Define three-level planning hierarchy in the development thread.
- [x] MC02 — Verify repository-wide operating-rule adoption (GM-owned).
- [ ] MC03 — Verify Gemini audit-protocol reconciliation (GM-owned).
- [x] MC04 — Define complete LRS3 roadmap.
- [x] MC05 — Establish measurable acceptance criteria.
- [x] MC06 — Establish evidence and replacement-thread continuity.
- [x] MC07 — Reconcile Crypto control-document status.
- [x] MC08 — Obtain independent Gemini roadmap audit.
- [x] MC09 — Resolve blocking findings and obtain PASS.
- [x] MC10 — Commit, push, and verify the reviewed roadmap.

Acceptance: all required checkpoints complete, repository evidence
verified, independent audit PASS, and authorized Git completion.

### R02 — Exploratory Design Readiness

- [x] MC01 — Verify research question and historical boundaries.
- [x] MC02 — Verify population, partitions, and sealed-date exclusions.
- [x] MC03 — Verify sampling, eligibility, deciles, and return semantics.
- [x] MC04 — Verify hour-boundary and New York clock groups.
- [x] MC05 — Verify invalid-cell and paired-date reporting.
- [x] MC06 — Document statistical and interpretive limitations.
- [x] MC07 — Resolve design questions without outcome inspection.
- [x] MC08 — Obtain independent Gemini design review.
- [x] MC09 — Resolve findings and obtain PASS.
- [x] MC10 — Record reviewed design and separate approval status.

Acceptance: reproducible, reviewed descriptive design. No freeze,
production-data access, or execution authorization is implied.

### R03 — Capacity and Acquisition Readiness

- [x] MC01 — Reconcile observed inventory and synthetic profiling evidence.
- [x] MC02 — Define bounded inventory and acquisition operations.
- [ ] MC03 — Define file, byte, runtime, and repeated-I/O ceilings.
- [x] MC04 — Define process memory and termination safeguards.
- [x] MC05 — Define storage, incomplete-artifact, and reserve budgets.
- [x] MC06 — Define input integrity and historical-fidelity checks.
- [ ] MC07 — Test fail-closed resource controls without outcome analysis.
- [x] MC08 — Obtain independent Gemini capacity review.
- [ ] MC09 — Resolve findings and obtain PASS.
- [ ] MC10 — Record separately authorized capacity/acquisition scope.

Acceptance: approved numerical safeguards supported by evidence.
Proposed limits in the exploratory draft are not approved by this roadmap.


R03-MC01 evidence reconciliation: the existing Pi3 capacity checkpoint records 28 source partitions, 227,731 canonical paths, 1,009,697,774 logical source bytes, 19,196,490 stored rows, 15,772,386 rows selected into 48 instrument-day windows, and 678,382 rows in the largest selected instrument-day. The Pi5 combined synthetic stress case processed 1,356,764 selected rows in 194.433410 seconds with peak process RSS of 229,343,232 bytes. The combined profile reused one fabricated BTC fixture with shifted dates and instrument labels; it was not 48 independent historical corpora. These observations support preliminary capacity planning only. They do not establish current source identity, historical input fidelity, physical or repeated-I/O requirements, virtual address-space consumption, end-to-end runtime, historical execution safety, scientific readiness, or profitability. The proposed 250,000-file, 1,100,000,000-byte, 1,800-second inventory, 48-worker, 14,400-second aggregate worker-runtime, 2 GiB worker address-space, 300-second worker-runtime, 1 GiB cooperative free-space reserve, and 1 MiB report limits remain NOT APPROVED. MC01, MC02, and MC04-MC06 are recorded as design checkpoints; MC03 and MC07-MC10 remain open. No inventory, acquisition, historical execution, study freeze, deployment, or sealed-H2 access is authorized by MC01.


R03-MC02 bounded-operations design: proposed inventory, verification, and acquisition are separate authorization stages, with no automatic progression between them. Inventory is restricted to metadata-only discovery across exactly 28 required receipt-date trade partitions, counting each partition once and excluding sealed H2 and substitutions. It must have independently approved file-count, logical-byte, and wall-clock ceilings; a partial or interrupted inventory is INCOMPLETE, not a valid complete manifest. Verification involving Parquet footers, instrument_id/trade_time column reads, or cryptographic hashing requires a separately bounded read allowance and must not inspect outcomes or invoke analytical kernels. Acquisition requires its own explicit authorization identifying exact source partitions, destination, transfer scope, byte and runtime ceilings, integrity requirements, retention, and incomplete-artifact handling. Successful inventory or verification does not authorize acquisition or historical execution. Storage, termination, and input-integrity designs are recorded under MC04-MC06; numerical approval and operational validation remain outstanding under MC03 and MC07-MC10. This checkpoint defines a proposed operating design only; no inventory, verification reads, transfer, acquisition, historical analysis, study freeze, deployment, or sealed-H2 access is authorized.


R03-MC03 preliminary resource-budget assessment (OPEN, NOT APPROVED): observed Pi3 source inventory covered 227,731 paths and 1,009,697,774 logical bytes across exactly 28 partitions. The proposed corpus-wide inventory ceilings remain 250,000 paths, 1,100,000,000 logical bytes, and 1,800 seconds, with no established complete end-to-end inventory runtime. Proposed analytical execution remains at most 48 sequential instrument-day workers, 300 seconds per worker, and 14,400 seconds aggregate worker-runtime, excluding acquisition, verification, orchestration, and other I/O. The existing Pi3 partition counter independently limits each partition to 12,000 files, 80 MiB logical bytes, 80 MiB requested source reads, 2,000,000 decoded rows, and 300 seconds. Its Budget.fetch accounting checks requested os.pread byte lengths before reads; it does not measure physical disk I/O. Recorded requested-byte totals were 424,859,579 for the footer scan, 517,019,953 for the incomplete monolithic count, and 539,887,459 for completed partition counts. These are distinct operations, not a reusable cumulative read budget. MC03 remains OPEN because approved ceilings for cumulative verification reads, repeated physical I/O, acquisition bytes and runtime, and full-operation elapsed time are absent. No proposed numerical value is operationally approved, and no inventory, verification, acquisition, historical execution, study freeze, or sealed-H2 access is authorized.

R03-MC03 numerical decision framework (OPEN, NO OPERATIONAL APPROVAL): distinguish observed measurements, exploratory proposals, and independently approved enforceable limits. The existing 227,731-path and 1,009,697,774-byte inventory supports preliminary sizing but does not validate the proposed 250,000-path, 1,100,000,000-byte, or 1,800-second corpus-wide ceilings. The observed 539,887,459 requested bytes for completed partition counts is not a cumulative verification-read budget and does not measure physical disk I/O. Before MC03 closure, define and independently review separate enforceable ceilings for: (1) inventory file count, logical bytes, and elapsed time; (2) verification requested bytes, repeated reads, and full-stage elapsed time; (3) acquisition source bytes, destination allocation, transfer runtime, and interrupted artifacts; (4) analytical worker address space, per-worker runtime, aggregate runtime, and orchestration overhead; (5) temporary files, reports, retained failed attempts, and minimum remaining free space. Each ceiling requires an identified enforcement point, measurement method, failure state, and supporting evidence. Where evidence is unavailable, the corresponding operation must remain blocked rather than receive an invented limit. The existing synthetic profiling and 106 passing regression tests do not establish historical execution safety. MC03 remains OPEN pending numerical justification, independent review, and explicit authorization. No inventory, verification reads, acquisition, historical execution, study freeze, deployment, or sealed-H2 access is authorized.

R03-MC03 cumulative verification-budget controller design (OPEN, DESIGN ONLY, NOT APPROVED): source inspection confirms that the existing Pi3 partition counter enforces requested os.pread bytes within each independent partition attempt, while its 28-record combiner sums requested bytes only after completion. No pre-launch cumulative verification-read controller was identified in the inspected LRS3 and market-data research modules. A future controller must reserve each attempt's full independently approved requested-read allowance before launch, atomically account for that reservation against the approved cumulative allowance, and refuse launch when the remaining allowance cannot cover it. Successful, failed, interrupted, killed, or otherwise uncertain attempts must retain their full reservation without automatic refunds. Retried attempts require separate authorization and additional budget; missing, ambiguous, or inconsistent prior-attempt accounting must fail closed. Durable reservation records, recovery behavior, concurrent-launch exclusion, and synthetic failure tests remain to be designed and independently reviewed before implementation can be considered validated. The existing 80 MiB per-attempt requested-read ceiling corresponds mathematically to 2,348,810,240 bytes for 28 fully reserved attempts, but neither that calculation nor the observed 539,887,459 completed-count requested bytes establishes an approved cumulative verification budget. Requested bytes do not measure physical disk I/O, and verification hashing, repeated reads, acquisition, and full-stage elapsed time require separate evidence and approved safeguards. MC03 and MC07 remain OPEN. No numerical ceiling, controller implementation, inventory, verification reads, acquisition, historical execution, study freeze, deployment, or sealed-H2 access is authorized.

R03-MC04 proposed process-safeguard design (DESIGN ONLY, NOT APPROVED): each future historical analytical instrument-day must execute in a separate worker process, with no concurrent analytical workers. Before importing numerical or Parquet libraries, each worker must apply an independently approved virtual address-space ceiling using RLIMIT_AS and restrict numerical-library thread counts to one. The existing Pi5 synthetic profiler used a proposed 2 GiB address-space ceiling and 300-second worker timeout; these are not validated historical-execution limits. Peak RSS does not measure virtual address-space consumption. The launcher must enforce an external monotonic deadline, capture bounded stdout and stderr, and terminate the worker process group on timeout or resource failure using SIGTERM, a bounded grace period, then SIGKILL and reaping. The synthetic reference implementation uses a two-second grace period. Nonzero exit, timeout, resource exhaustion, invalid output, or uncertain termination must fail closed without automatic retry or progression. Each attempt must begin INCOMPLETE, preserve failure evidence, and publish COMPLETE only after required validation and durable recording. A completion record possibly published near termination requires independent inspection rather than automatic acceptance or downgrade. Existing synthetic tests cover selected timeout and failure-record paths, but do not establish historical-runner enforcement or general memory safety. Historical implementation, synthetic fail-closed tests, independent review, numerical approval, and explicit execution authorization remain outstanding. MC03 and MC07-MC10 remain open; MC05-MC06 are design checkpoints only. No historical execution, acquisition, study freeze, deployment, or sealed-H2 access is authorized by MC04.

R03-MC05 proposed storage-budget design (DESIGN ONLY, NOT APPROVED): source logical bytes, unique-inode allocation, acquisition destination bytes, temporary working space, incomplete and failed artifacts, durable outputs, and retained prior attempts must be budgeted separately. The observed Pi3 inventory contained 1,009,697,774 logical source bytes across 227,731 paths, including 3,092 multiply linked paths accounting for 19,507,008 logical bytes. These path-based figures do not establish unique-inode disk allocation or transfer volume. The Pi5 combined synthetic profiling attempts generated 176,363,077 fixture bytes in total; this does not measure physical allocated space or historical acquisition requirements. The existing synthetic loader enforces a 256 MiB fixture-byte ceiling and checks that at least 1 GiB of filesystem free space would remain before each file write. That reserve is cooperative, not reserved capacity, and its numerical value is not approved for historical operations. The synthetic worker reference also bounds JSON output to 65,536 bytes; the exploratory draft separately proposes a 1 MiB serialized historical report ceiling, not yet approved. Before any acquisition or execution, require independently approved numerical ceilings for transferred source bytes, destination allocation, temporary files, output artifacts, aggregate retained attempts, and minimum remaining free space. Checks must account for existing filesystem use, concurrent writers, allocation overhead, interrupted writes, and post-failure retention. An interrupted or over-budget attempt must remain INCOMPLETE or FAILED, preserve evidence, and never be silently treated as COMPLETE. Cleanup, retention periods, and deletion authority require explicit approval; no automatic deletion of evidence or unrelated files is permitted. Synthetic tests demonstrate selected reserve and publication behaviors only. Numerical storage approval, historical implementation, independent review, and explicit operation authorization remain outstanding. MC03 and MC07-MC10 remain open; MC06 is a design checkpoint only. No inventory, verification, acquisition, historical execution, study freeze, deployment, or sealed-H2 access is authorized by MC05.

R03-MC06 proposed input-integrity design (DESIGN ONLY, NOT APPROVED): historical source identity, research-population correctness, and exchange-feed fidelity are distinct verification requirements. Before any authorized acquisition, an independently reviewed manifest must identify the exact 28 required receipt-date partitions, each canonical relative path, file size, expected cryptographic digest, source provenance, and approved destination mapping. The manifest must exclude sealed H2, unapproved substitutions, and unrelated source families. Verification must detect missing, extra, duplicate, changed, or unreadable files; reject unexpected symlinks and unsafe paths; and account explicitly for multiply linked canonical files without assuming their backup provenance. Source and destination digests must match the approved manifest under separately authorized read and runtime budgets. A local matching digest proves byte consistency with its reference, not independent source authenticity. Historical population verification must retain the declared previous/target/next partition rule and use trade_time research-day boundaries rather than receipt-date membership. Both loading passes must use the same inclusion predicate, reject raw null instrument_id and trade_time, validate required columns and types, reject null or invalid selected values, and reconcile selected row counts and instrument membership. Additional synthetic tests must cover missing adjacent partitions, boundary spillover, changed inputs between passes, corrupt Parquet, duplicate identities, schema incompatibility, and manifest mismatch. Historical fidelity requires a separate assessment of collector continuity, exchange-feed completeness, dropped events, timestamp semantics, duplicate trades, and source provenance; existing inventory counts and synthetic fixtures do not establish those properties. Any unresolved integrity or fidelity requirement must fail closed as INCOMPLETE without automatic substitution, retry, outcome computation, or progression. Exact digests, approved manifests, numerical verification budgets, historical implementation, independent audit, and explicit authorization remain outstanding. MC03 and MC07-MC10 remain open. No inventory, verification reads, acquisition, historical execution, study freeze, deployment, or sealed-H2 access is authorized by MC06.

R03-MC07 synthetic fail-closed test checkpoint (PARTIAL EVIDENCE, OPEN): on 2026-11-25, the operator reported 106 passing tests in 2.95 seconds using the repository's existing Python 3.14.6 virtual environment and pytest 9.1.1. The selected modules covered synthetic memory profiling, loader profiling, combined profiling, partition population counting, multi-partition loading, and time-conditioning synthetic integration. Inspected test definitions exercise worker address-space configuration, timeout termination, requested-read and row limits, synthetic fixture byte limits, cooperative free-space rejection, missing adjacent partitions, null selected fields, malformed records, incomplete and failure artifact retention, and exclusive completion publication. The partition-counter reference includes process-group SIGTERM, bounded grace, SIGKILL, and reaping. These tests provide a passing synthetic regression baseline, not historical-operation validation. No complete historical resource-control implementation or approved source-manifest verification was demonstrated in the inspected runner. Cumulative verification reads, repeated physical I/O, acquisition byte and runtime ceilings, aggregate retained storage, historical worker limits, and full-operation deadlines remain unresolved. Additional synthetic fail-closed tests must be scoped against the final approved numerical budgets and historical implementation, without computing historical outcomes or accessing sealed H2. MC03, MC07, MC09, and MC10 remain OPEN; MC08 is complete for documentation review only. Passing tests do not authorize inventory, verification reads, acquisition, historical execution, study freeze, deployment, or sealed-H2 access.

R03-MC08 independent Gemini documentation review (PASS, LIMITED SCOPE): on 2026-11-25, the operator reported VERDICT: PASS with zero blocking documentation findings after Gemini inspected all seven audit-packet files against baseline a45bce9d044b3ec7d6ad473cdf9d691276e8c33c. The reviewed packet included the complete roadmap, full proposed diff, capacity checkpoint, exploratory draft, baseline identifier, checksums, and review instructions. The review found the completed MC01, MC02, and MC04-MC06 design checkpoints consistent with their stated limitations. This documentation PASS does not approve numerical resource ceilings, historical input integrity, historical-runner enforcement, or operational readiness. Cumulative verification reads, repeated physical I/O, acquisition and storage budgets, full-stage deadlines, historical resource safeguards, and source fidelity remain unresolved. All proposed numerical limits remain NOT APPROVED. MC03, MC07, MC09, and MC10 remain OPEN. No inventory, verification reads, acquisition, historical execution, methodology freeze, deployment, production transfer, broader pilot, or sealed-H2 access is authorized. Original Candidate D D0 remains BLOCKED; scientific readiness remains PENDING; the exploratory study remains DRAFT / UNFROZEN.

### R04 — Analytical Implementation Readiness

- [ ] MC01 — Establish bounded implementation scope and code ownership.
- [ ] MC02 — Implement deterministic input and date validation.
- [ ] MC03 — Implement analytical transformations against frozen design.
- [ ] MC04 — Implement invalid-cell and paired-date reporting.
- [ ] MC05 — Implement resource enforcement and abort behavior.
- [ ] MC06 — Build synthetic and adversarial tests.
- [ ] MC07 — Verify reproducibility and output integrity.
- [ ] MC08 — Obtain independent Gemini implementation audit.
- [ ] MC09 — Resolve findings and obtain PASS.
- [ ] MC10 — Record implementation revision and readiness limitations.

Acceptance: tested and audited implementation. No historical execution
or scientific readiness is established by implementation alone.

### R05 — Study Freeze and Execution Authorization

- [ ] MC01 — Confirm design and capacity prerequisites.
- [ ] MC02 — Identify exact input scope and expected digests.
- [ ] MC03 — Identify code revision and dependencies.
- [ ] MC04 — Specify output, retention, and recovery arrangements.
- [ ] MC05 — Preserve predeclaration and digest outside temporary storage.
- [ ] MC06 — Verify sealed-data and historical-boundary protections.
- [ ] MC07 — Independently review the exact frozen packet.
- [ ] MC08 — Resolve audit findings and obtain PASS.
- [ ] MC09 — Request explicit user authorization for exact execution scope.
- [ ] MC10 — Record freeze and authorization evidence.

Acceptance: complete frozen packet and explicit user authorization.
A Gemini PASS alone does not authorize execution.

### R06 — Historical Exploratory Execution

- [ ] MC01 — Verify authorization and exact frozen inputs.
- [ ] MC02 — Verify environment and resource preflight.
- [ ] MC03 — Execute only the authorized historical scope.
- [ ] MC04 — Preserve immutable input and output evidence.
- [ ] MC05 — Verify all required instrument-days were addressed.
- [ ] MC06 — Disclose every invalid cell and date pair.
- [ ] MC07 — Reconcile runtime, memory, and I/O observations.
- [ ] MC08 — Verify output reproducibility and provenance.
- [ ] MC09 — Obtain independent execution-evidence review.
- [ ] MC10 — Record COMPLETE_DESCRIPTIVE or INCOMPLETE.

Acceptance: authorized execution classified under frozen completion
rules. COMPLETE_DESCRIPTIVE does not establish predictive value.

### R07 — Descriptive Findings and Adjudication

- [ ] MC01 — Verify primary 60-second reporting completeness.
- [ ] MC02 — Report secondary horizons without rescue selection.
- [ ] MC03 — Report both time mechanisms side by side.
- [ ] MC04 — Report instrument-day and valid date-paired summaries.
- [ ] MC05 — Report invalid cells, exclusions, and sensitivity.
- [ ] MC06 — Document dependence and outcome-semantic limitations.
- [ ] MC07 — Separate observed contrasts from causal or economic claims.
- [ ] MC08 — Obtain independent Gemini reporting audit.
- [ ] MC09 — Resolve findings and obtain PASS.
- [ ] MC10 — Record explicit stop, defer, or new-study proposal decision.

Acceptance: reproducible descriptive findings and documented decision.
No automatic hypothesis promotion or profitability conclusion.

### R08 — Conditional Confirmation and Economic Feasibility

- [ ] MC01 — Determine whether exploratory evidence justifies continuation.
- [ ] MC02 — Define a new prospective confirmation question if warranted.
- [ ] MC03 — Establish independent data and sealed holdout boundaries.
- [ ] MC04 — Predeclare success, failure, and stopping criteria.
- [ ] MC05 — Obtain separate design audit and user authorization.
- [ ] MC06 — Execute only an independently authorized confirmation study.
- [ ] MC07 — Adjudicate confirmation without post-hoc rule changes.
- [ ] MC08 — Separately design transaction-cost and execution feasibility.
- [ ] MC09 — Independently audit any economic analysis.
- [ ] MC10 — Record continuation, rejection, or justified deferral.

Acceptance: conditional evidence and decisions, not presumed positive
results. This stage may remain parked if continuation is unjustified.

### R09 — Research Operations and Bounded AI Readiness

- [ ] MC01 — Define reproducibility and artifact-retention contracts.
- [ ] MC02 — Define monitoring, alerts, and recovery behavior.
- [ ] MC03 — Establish permission and authorization boundaries.
- [ ] MC04 — Define read-only and write-capable agent operations.
- [ ] MC05 — Define daily reporting and evidence provenance.
- [ ] MC06 — Test failure and interruption handling.
- [ ] MC07 — Conduct supervised agent dry runs if authorized.
- [ ] MC08 — Obtain independent Gemini operational audit.
- [ ] MC09 — Resolve findings and obtain PASS.
- [ ] MC10 — Record authorized operating scope or remain manual.

Acceptance: reproducible, audited operations and explicitly approved
permissions. This roadmap does not deploy or activate an agent.

### Development Control and Continuity

The persistent roadmap records major checkpoints, acceptance criteria,
verified status, and evidence references. Development responses display
the active roadmap item, its complete Major Checklist, the actionable
Minor Checklist for the active major checkpoint, and one next action.

Minor tasks are chat-level working detail. Their outstanding requirements
must remain reconstructible from repository evidence when threads change.

Replacement-thread reconstruction for LRS3:
1. Confirm the current Git HEAD, branch, worktree status, and document
   revisions; do not assume Project Source snapshots are synchronized.
2. Read L0_PLATFORM/zHANDOFF.md for operating rules, then
   L2_DOMAINS/crypto/zREADME.md, zMISSION_CONTROL.md, and zROADMAP.md
   for domain navigation, research status, and development checkpoints.
3. Read research/TIME_CONDITIONING_EXPLORATORY_DRAFT.md and
   research/TIME_CONDITIONING_CAPACITY_CHECKPOINT.md for the proposed
   study, evidence references, unresolved decisions, and limitations.
4. Reconstruct the active roadmap item, complete Major Checklist,
   actionable Minor Checklist, blockers, evidence, and next action.
   Verify completion against repository evidence rather than treating
   checked boxes or prior conversation statements as sufficient proof.
5. Preserve sealed research boundaries and require separate explicit
   authorization for inventory, acquisition, execution, or deployment.

R01 evidence anchors: roadmap commit 5e23695; platform governance
commit 21cf802; exploratory draft revision 7f9fab3; capacity
checkpoint revision 4b18273. These identify documentation revisions,
not immutable external evidence or authorization. MC03 remains a
GM-owned platform protocol dependency; MC06 and MC07 are complete.

Historical continuity checkpoint recorded at commit 08f41f5: R01-MC06.
R01-MC06 documentation was audited, committed, pushed, and verified.
R01-MC07 Crypto control-document reconciliation was independently
Gemini-audited, committed, pushed, and verified at commit 7709ecc.
R01-MC03 remains the outstanding GM-owned platform dependency.
R02-MC01 research-question and historical-boundary documentation review received independent Gemini PASS with no blocking findings. Gemini reviewed documented excerpts, not the live repository. Original Candidate D D0 provenance remains unresolved, and the development sample is not an independent holdout. H2 remains sealed. This checkpoint permits continued descriptive design review only; it does not authorize study freeze, inventory, acquisition, production-data access, or execution.
R02-MC02 population, receipt-date partition, and sealed-date exclusion review received independent Gemini PASS with zero blocking or nonblocking findings. The proposed BTC-USD and ETH-USD population contains 24 research dates and 48 instrument-days. Previous, target, and next receipt-date coverage requires exactly 28 distinct trade partitions: 2026-07-21 through 2026-08-10 and 2026-08-25 through 2026-08-31 inclusive. No required partition overlaps sealed H2 (2026-09-04 through 2026-10-01). September 3 remains excluded because its next-day partition is sealed. Gemini independently verified calendar arithmetic, not live repository contents or historical feed completeness. This review does not authorize inventory, acquisition, transfer, execution, or study freeze.
R02-MC03 sampling, eligibility, decile, and forward-return semantics review received independent Gemini PASS with zero blocking findings and three nonblocking documentation observations. Source inspection confirmed every-20th-trade sampling beginning at zero-based index 19; the inherited 10-second lookback; common eligibility based on defined momentum; horizon-specific comparative eligibility using common_eligible & ~np.isnan(return_h); forward returns using the last trade in (T, T+h]; and deterministic imbalance-decile ranking by value, trade time, and trade ID across the complete eligible instrument-day before temporal grouping. The inherited zero-volume imbalance behavior and float64 numerical limitations remain relevant. Gemini's nonblocking observations recommend explicit cross-references to these inherited invariants during R04 implementation. Gemini assessed supplied source observations and draft text without direct repository inspection or independent digest verification. The operator separately verified the tracked source files. This checkpoint establishes design-semantics review only; it does not authorize historical data access, inventory, acquisition, transfer, execution, study freeze, or deployment, and does not establish scientific readiness.

R02-MC04 hour-boundary and New York clock-group design review received independent Gemini PASS with zero blocking findings and two nonblocking observations. Source inspection confirmed that UTC epoch-millisecond minute-of-hour masks assign minutes 45–59 and 0–14 to IN and minutes 15–44 to CONTROL; the America/New_York clock mask assigns 09:30 inclusive through 16:00 exclusive to IN and all other observations to CONTROL. The timezone-aware conversion reflects EST/EDT clock changes, and the same local-clock rule applies to every included date, including weekends, without asserting an exchange trading session. Both mechanisms check for overlapping or nonexhaustive masks. Gemini noted minute-granularity boundary semantics and the difference between integer epoch-millisecond arithmetic and floating-point timestamp conversion as nonblocking implementation-review considerations for R04. Gemini reviewed supplied source and draft excerpts, not the live repository or executable test results; baseline, digests, and unchanged-file checks were operator-reported. This checkpoint establishes temporal-group design consistency only; it does not authorize historical data access, inventory, acquisition, transfer, execution, methodology freeze, or deployment, and does not establish predictive value, profitability, or scientific readiness.

R02-MC05 invalid-cell and paired-date reporting design review received independent Gemini PASS with zero blocking findings and three nonblocking observations. The dedicated synthetic-development descriptive reporter retains eligible and IN/CONTROL D0/D9 counts, explicit invalid-cell reasons, finite edge and delta checks, and all 48 instrument-day records. It pairs BTC-USD and ETH-USD only when both same-date deltas are valid, reports valid and invalid date pairs and strictly positive paired counts, and computes leave-one-date-out mean sensitivity only with at least two valid pairs. The original Candidate D D0 33/50 promotion gate is not reused. Gemini identified extreme floating-point median arithmetic, future historical-mode reporting policy, and unexecuted unit tests as nonblocking observations. Gemini reviewed supplied source and test text, not the live repository or executable test results; source digests and Git state were operator-verified. The reporter accepts synthetic summaries only and cannot authenticate upstream historical populations, deciles, or returns. This checkpoint establishes descriptive-reporting design consistency only; it does not authorize historical data access, inventory, acquisition, transfer, execution, methodology freeze, or deployment, and does not establish predictive value, profitability, or scientific readiness.

R02-MC06 statistical and interpretive limitations design review received independent Gemini PASS with zero blocking findings and two nonblocking documentation observations. The exploratory draft now explicitly addresses potentially overlapping return-window dependence, repeated intraday sampling, same-date BTC/ETH co-movement, cross-horizon correlation, and the inability of instrument-day aggregation, date pairing, or leave-one-date-out summaries to establish independence. It also discloses possible selection effects from requiring both instruments to have valid same-date deltas and exploratory multiplicity across two mechanisms and four horizons. The primary 60-second designation and secondary-horizon restrictions remain unchanged. No new hypothesis test, threshold, selection rule, or methodological change is introduced. Gemini reviewed the supplied design summary and proposed wording, not the live repository or an executed study; Git state and source digests were operator-verified. This checkpoint establishes interpretive documentation consistency only and does not authorize inventory, acquisition, transfer, historical execution, study freeze, deployment, scientific promotion, or profitability claims.

R02-MC07 design-question disposition review received independent Gemini PASS with zero blocking findings and two nonblocking observations. No unresolved scientific-design questions were identified for the proposed descriptive exploratory specification. All decisions established in R02-MC01 through R02-MC06 remain unchanged; no historical outcomes were inspected, no retrospective rules were added, and no significance threshold, automatic winner, or promotion criterion was introduced. Feed completeness, serial and cross-instrument/cross-horizon dependence, valid-subset selection effects, and exploratory multiplicity remain explicit limitations, not resolved empirical facts. Numeric resource ceilings, inventory and storage budgets, termination safeguards, input/code pinning, freeze, and execution authorization remain subject to later checkpoints and separate approvals. Gemini's observation about duplicate Standing Governance headings was checked against the operator-verified source: exactly one such heading exists, so no draft edit was warranted. The other observation requires MC07 closure to remain distinct from the pending R02-MC08 independent full-design review. Gemini reviewed supplied design and capacity documents rather than independently executing commands or verifying live repository digests; baseline and hashes were operator-verified. Original Candidate D D0 remains BLOCKED, H2 remains SEALED, and the study remains DRAFT / UNFROZEN. This checkpoint does not authorize historical data access, inventory, acquisition, transfer, execution, study freeze, deployment, scientific promotion, or profitability claims.

R02-MC08 independent consolidated full-design review received Gemini VERDICT: PASS, SCOPE: PASS, and DESIGN REVIEW READINESS: READY, with zero blocking findings and four nonblocking observations. The operator supplied a complete eight-source, line-numbered evidence packet at repository HEAD e1ba086d5f03688c1c3900a444c59ae213d9e669; packet SHA-256 e0771f7224e2efdac30f95b795d7d73f69141dcdad2206af88d8fd9c23e6a45f. Gemini reported inspecting all eight complete sources. The four observations concern float-based epoch-millisecond conversion in timezone handling, even-count median arithmetic consistency, explicit DST-transition test coverage, and roadmap checkpoint documentation. These are nonblocking design-review observations, not evidence of completed R04 implementation work.

R02-MC09 finding disposition: no blocking corrections were required, and the MC08 PASS stands. The timestamp-precision, numerical-robustness, and DST-test observations are deferred to R04 implementation/testing review without changing R02 methodology. The roadmap-status observation is addressed by recording MC08 and MC09 here; MC10 separately records reviewed-design readiness and the absence of execution authorization. This disposition does not approve proposed capacity ceilings, authenticate historical inputs, freeze the study, or authorize historical inventory, acquisition, execution, deployment, or promotion. Original Candidate D D0 remains BLOCKED; H2 remains SEALED; the exploratory study remains DRAFT / UNFROZEN / NO EXECUTION AUTHORIZATION; scientific readiness remains PENDING; production transfer and broader pilot remain HOLD; cost-stress remains PAUSED.

R02-MC10 reviewed-design and authorization-status record: R02-MC01 through R02-MC09 establish a reproducible descriptive exploratory design, with independent Gemini full-design review PASS and zero blocking findings. R02 design readiness is recorded as READY FOR SEPARATE NEXT-STAGE CONSIDERATION, not as scientific readiness or operational authorization. The design remains DRAFT / UNFROZEN / NO EXECUTION AUTHORIZATION. Numeric capacity ceilings, historical input fidelity, provenance, implementation safeguards, predeclaration freeze, and any execution authorization remain separate later checkpoints. Original Candidate D D0 remains BLOCKED; scientific readiness remains PENDING; production transfer and broader pilot remain HOLD; cost-stress remains PAUSED; H2 remains SEALED from 2026-09-04 through 2026-10-01 inclusive. No historical inventory, acquisition, canonical partition access, research execution, methodology freeze, deployment, predictive claim, or profitability claim is authorized by R02 closure. Repository completion remains subject to independent precommit audit PASS and separately reviewed Git actions.

Recheck these statuses against current Git evidence in a new thread;
this paragraph is a revision-specific checkpoint, not live state.

A checkpoint is not complete merely because a test, audit, commit,
transfer, or deployment succeeded. Scientific conclusions require their
own evidence and predefined decision criteria.

Gemini is the independent auditor, not General Manager. GM handles only
repository-wide work assigned by the user. Specialists own their domains.

All terminal commands are executed by the user. No experiment, source
inventory, transfer, production-data read, study freeze, or deployment
is authorized by this planning section.

---

## Historical Roadmap Snapshot — SUPERSEDED

The original roadmap is preserved verbatim below as historical planning
evidence from the pre-migration layout recorded at `a930f37`.

Its phases, filenames, priorities, candidate venues, Program references,
cross-references, and implementation state are historical. Filenames such as
`README.md` and `MISSION_CONTROL.md` predate the current `z` prefixes.
Cross-references inside the snapshot resolve to the corresponding historical
state of those documents.

Nothing below this heading represents current status, sequencing, or
authorization.

# Crypto Domain — Roadmap

Status: Phase 0 in progress. No implementation exists.

This roadmap is intentionally shallow right now. It exists to give
future research a clear, sequenced path — not to commit to a
timeline or promise specific deliverables before the evidence
justifies them.

---

### Phase 0 — Documentation and Architecture (IN PROGRESS)

Goal: Give the Crypto Domain a permanent, well-documented home in
the repository before any implementation begins.

- README.md, MISSION_CONTROL.md, zROADMAP.md (this file),
  research/strategy_vision.md
- Forward pointer added to zARCHITECTURE.md's Open Design Targets
- No collectors, scanners, scoring logic, or API integrations

Done when: every item in MISSION_CONTROL.md's "Done When (Phase 0)"
checklist is complete and committed.

---

### Phase 1 — Research (NOT STARTED, NO TIMELINE)

Goal: Answer the six open questions in
research/strategy_vision.md with real evidence, before writing any
implementation code.

Candidate first steps (not commitments, not sequenced yet):
- Confirm whether real exchange data (Coinbase, Binance, Kraken, or
  similar) is accessible under terms consistent with Liquid
  Research's read-only, no-wallet, research-only constraints.
- Review what Polymarket crypto category data already exists
  passively via Program A's classifier, as a possible low-cost
  starting point for Track 1 research.
- Design the smallest possible experiment that could produce real
  evidence on any single comparison criterion (statistical
  significance, expectancy, consistency, liquidity, automatability,
  or engineering ROI) from research/strategy_vision.md.

This phase does not begin until there is genuine capacity to do it
properly — not automatically after Phase 0.

---

### Phase 2 — First Domain Producer (NOT STARTED, BLOCKED ON PHASE 1)

Goal: If and only if Phase 1 produces evidence justifying it, build
a minimal Crypto Domain producer, following the same architectural
principles as the Prediction Markets Domain (Domain owns selection,
publishes one canonical output).

Explicitly NOT assumed: that the existing canonical schema
(instrument_id, resolution_id, instrument_name, tradeability_score,
publication_id) transfers unchanged. Per zARCHITECTURE.md's Open
Design Targets, this is the first real test of whether that schema
generalizes — to be answered with evidence during this phase, not
assumed before it.

Blocked on: Phase 1 producing a real, evidence-based case for
building anything at all.

---

## What This Roadmap Deliberately Does Not Do

- Does not commit to which research track (Crypto Prediction
  Markets vs. Real Crypto Markets) gets built first.
- Does not commit to a timeline for any phase beyond Phase 0.
- Does not assume the Prediction Markets Domain's schema, folder
  structure, or Program pattern will look identical here.
- Does not compete with or take priority over Program A's or
  Program B's active research.
