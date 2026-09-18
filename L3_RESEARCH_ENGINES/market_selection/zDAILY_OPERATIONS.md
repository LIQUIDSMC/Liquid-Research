# Market Selection Engine
# Daily Operations

**Status:** Current Operating Procedure
**Last Updated:** 2026-09-18
**Engine:** `L3_RESEARCH_ENGINES/market_selection/`

---

## Purpose

This document describes normal operation, verification, and recovery for the
Market Selection portion of the shared Liquid Research daily cycle.

Normal operation is automated. Manual execution is a diagnostic or recovery
workflow, not the default daily procedure.

Research methodology and current research priorities are governed separately by:

`L3_RESEARCH_ENGINES/market_selection/zMISSION_CONTROL.md`

---

## Normal Automated Operation

The production Raspberry Pi currently schedules the shared daily orchestrator
through systemd:

- Timer: `liquid-research-orchestrator.timer`
- Service: `liquid-research-orchestrator.service`
- Schedule: daily at **05:00 Pacific**
- Orchestrator: `L1_CORE/orchestrator.py`

The timer-triggered service may normally appear inactive between runs. The
timer, rather than a continuously running orchestrator process, is responsible
for starting the daily cycle.

No user crontab is currently used for this workflow.

The independent Market Data Platform collector service is separate from this
daily cycle and must not be confused with the orchestrator:

`liquid-research-collector.service`

---

## Daily Pipeline

The shared L1 orchestrator executes these stages sequentially:

1. Prediction Markets acquisition
   `L2_DOMAINS/prediction_markets/acquisition/market_collector.py`

2. Prediction Markets selection/scanning
   `L2_DOMAINS/prediction_markets/selection/scanner.py`

3. Prediction Markets canonical publication
   `L2_DOMAINS/prediction_markets/publication/publish_canonical_output.py`

4. Market Selection paper-trade admission
   `L3_RESEARCH_ENGINES/market_selection/simulator/paper_trader.py`

5. Market Selection paper-trade resolution
   `L3_RESEARCH_ENGINES/market_selection/simulator/paper_resolver.py`

6. Market Microstructure OBI collection
   `L3_RESEARCH_ENGINES/market_microstructure/collection/run_obi.py`

7. Market Microstructure Near-Book Depth collection
   `L3_RESEARCH_ENGINES/market_microstructure/collection/run_near_book_depth.py`

This order is part of the current operating contract. Do not manually reorder
or parallelize these stages without separate engineering review.

The current Prediction Markets canonical output is:

`L2_DOMAINS/prediction_markets/data/canonical/prediction_markets_latest.csv`

---

## Orchestrator Safety Behavior

Before execution, the orchestrator performs preflight checks including:

- repository-root availability;
- expected virtual-environment interpreter;
- required stage-script existence;
- runtime log-directory availability;
- minimum free disk space.

A lock prevents overlapping daily-cycle executions.

Each stage has an explicit timeout. If a stage fails or times out:

1. The pipeline is marked failed.
2. Remaining stages are recorded as skipped.
3. Downstream execution stops.
4. Run evidence is written for diagnosis.
5. The lock is released through the orchestrator's cleanup path.

After canonical publication reports success, the orchestrator additionally
requires the canonical output file to exist before downstream stages continue.

---

## Run Evidence

Daily-cycle runtime evidence is written beneath:

`logs/daily_cycle/`

Each run receives its own timestamped directory containing:

- per-stage console logs;
- `run_summary.json`;
- `health_summary.txt`.

The structured run record includes operational metadata such as the run ID,
pipeline version, repository path, Python interpreter, host, Git commit,
pipeline status, stage statuses, and durations.

Use these artifacts before guessing why a run failed.

---

## Known Phase-1 Validation Limitation

A successful process exit does not by itself prove that every stage produced
the intended semantic data result.

The orchestrator currently records:

`semantic_validation = "not_implemented_phase_1"`

Several deeper validation checks remain explicitly deferred in
`L1_CORE/orchestrator.py`, including validation of expected output changes and
detection of systemic per-market failures in downstream Microstructure
collection.

Therefore:

**operational success is not automatically equivalent to research-data
validity.**

Do not promote a research conclusion solely because the orchestrator reports a
successful pipeline.

---

## Dry Run / Preflight

From the repository root with the repository virtual environment active:

`python3 L1_CORE/orchestrator.py --dry-run`

Dry-run mode performs preflight and displays the planned stages without
executing the research pipeline.

Use it when validating environment, paths, or deployment configuration before
a recovery run.

A dry run does not create new research observations.

---

## Manual Recovery

Manual execution is for diagnosis or controlled recovery after the failed stage
and existing run evidence have been inspected.

Do not automatically rerun the entire daily cycle after a partial failure.

Before recovery:

1. Read the failed run's `health_summary.txt`.
2. Read `run_summary.json`.
3. Inspect the failed stage's console log.
4. Determine which upstream stages already completed successfully.
5. Determine whether rerunning a completed stage could duplicate, replace, or
   otherwise alter research observations.
6. Verify the current repository/data state before executing anything.

If recovery requires direct execution of an individual stage, use the exact
current stage path from `L1_CORE/orchestrator.py`.

Do not rely on historical `Program A`, `collectors/`, `scanner/`, or
`programs/program_a/` paths as current operating instructions.

---

## Market Selection Admission Invariant

Routine operation must preserve the current admission identity:

**one `market_id` may create at most one Market Selection paper trade, ever.**

Supporting rules:

- `market_id` is the admission identity.
- `slug` is metadata only.
- `scanner_run_id` is provenance only.
- A previously traded `market_id` is not eligible for re-entry merely because
  its prior paper trade is closed.
- Historical duplicate rows are preserved rather than rewritten.

Operational recovery must not bypass this invariant.

---

## Routine Operator Review

Routine review should answer operational questions first:

- Did the scheduled cycle run?
- Did the pipeline finish successfully?
- Which stages succeeded, failed, timed out, or were skipped?
- Was the canonical output present after publication?
- Are the run logs and structured summary available?
- Is there evidence of a semantic/data problem despite process-level success?

Research interpretation belongs in the appropriate research workflow, not in
routine operational health checks.

---

## Changes Requiring Separate Authorization

Daily operation or recovery does **not** authorize changes to:

- Tradeability scoring.
- Scanner thresholds.
- Sampling methodology.
- Market-selection criteria.
- Category taxonomy.
- Classifier behavior.
- Paper-trade admission identity.
- Historical paper trades.
- Prediction Markets canonical publication contract.
- Research methodology.

If an operational problem appears to require one of these changes, stop and
route it through the appropriate research or engineering review.

---

## Authority

When this document conflicts with current implementation behavior, verify the
implementation and runtime evidence rather than forcing the implementation to
match stale documentation.

Relevant authorities:

- `L1_CORE/orchestrator.py` — shared daily-cycle implementation.
- `L3_RESEARCH_ENGINES/market_selection/zMISSION_CONTROL.md` — current Market
  Selection research state and protected boundaries.
- `L0_PLATFORM/zARCHITECTURE.md` — architecture and ownership.
- `L4_KNOWLEDGE/validated_findings.md` — preserved validated findings.
- `L4_KNOWLEDGE/open_questions.md` — shared unresolved research questions.

Historical documents and Git history remain evidence of prior operating states;
they are not automatically current instructions.
