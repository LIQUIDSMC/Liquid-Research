# Liquid Research — Operating Manual

This document is the operating manual for Liquid Research. It defines
project-wide research integrity, engineering discipline, documentation
standards, and operating workflow.

Authority is scoped rather than concentrated in one document:

- `zHANDOFF.md` — operating principles and workflow.
- `zARCHITECTURE.md` — architecture, ownership, boundaries, and data contracts.
- `zROADMAP.md` — portfolio priorities and planned work.
- Engine-specific control documents — methodology, research state, and
  engine-specific operations.
- `L4_KNOWLEDGE/` — shared findings, hypotheses, open questions, and
  historical research knowledge.

Read the relevant authority before writing code, moving files, changing
architecture, or modifying research methodology. When documents conflict,
verify the implementation and evidence first, then reconcile the documents
through a deliberate change rather than assuming one stale document wins.
---

# PART 1 — STABLE PRINCIPLES
## (These change rarely. Treat them as the project's constitution.)

---

## What Liquid Research Is

Liquid Research is an independent software and quantitative-research project
for building reproducible market-data pipelines, testing market hypotheses,
and preserving the evidence required to distinguish observations from
defensible findings.

It includes:
- Market-domain acquisition and canonical publication.
- Shared market-data and orchestration infrastructure.
- Independent research engines for market selection, microstructure,
  trade-flow, regime analysis, and other evidence-backed questions.
- Paper-research and historical experimental workflows.
- A shared knowledge layer for findings, hypotheses, open questions, and
  future research concepts.

It is NOT:
- A live trading system.
- A claim of a validated profitable strategy.
- A production execution platform.
- A get-rich-quick system.
- A single-experiment project.

Every feature, research engine, and infrastructure change should connect to
a defensible research or engineering purpose. If that connection is unclear,
challenge the work before building it.
---

## Core Research Philosophy

**Evidence over assumptions. Always.**

The research standard is:
- A screenshot is not evidence.
- A tweet is not evidence.
- A GitHub repository is not evidence.
- A YouTube video is not evidence.
- An AI-generated answer is not evidence.

Evidence requires:
1. Verification — checked directly, not taken on faith.
2. Reproduction — the result shows up again under the same conditions.
3. Measurable results — a number, a comparison, or a real outcome.

A claim with none of these belongs in the research vault as an
unreviewed lead. A claim with all three earns a place in
validated_findings.md.

**Dramatic improvements are potential bugs until proven otherwise.**
Treat suspiciously clean outputs, unexpected jumps, and surprising
discoveries as bugs to investigate — not signal to celebrate.

---

## How I Think and Prioritize

The highest-level objective is discovering repeatable, monetizable
edges. Everything else is secondary. When evaluating any idea, task,
or feature, the question is always:

"What is the highest-probability path toward a profitable,
evidence-backed research platform?"

Not: "Is this interesting?"
Not: "Is this technically impressive?"
Not: "Is this a cool dashboard?"

**Prioritization order:**
1. Protect active experiments — their methodology stays frozen
   until their review milestone, regardless of what else is being
   built. Independent parallel programs are welcome and encouraged
   whenever they do not compete for data, engineering resources, or
   methodological integrity with an active experiment (see "On
   parallel programs" and "Frozen Experiments, Active Platform"
   below).
2. Evidence-driven work over speculative work.
3. Self-contained work over work requiring new infrastructure.
4. Work that produces findings over work that produces features.

**On parallel programs:**
Liquid Research should actively maintain multiple independent
research programs whenever doing so increases the probability of
discovering a repeatable edge without compromising existing
experiments. Liquid Research operates closer to a research lab
running multiple independent efforts in parallel than a single
sequential project. The governing constraints are not "how many
programs can exist at once" but:
- They test genuinely different hypotheses.
- Their data and methodology do not contaminate each other.
- Each program's methodology stays frozen once data collection
  begins, regardless of how many other programs are also running.
- Each program maintains its own documentation.
- Each program's findings feed into the shared platform knowledge.
New programs are welcome whenever they are genuinely independent —
the discipline is in methodology isolation and evidence standards,
not in limiting how many efforts run simultaneously.

**Frozen Experiments, Active Platform:**
Once an experiment begins collecting data, its methodology remains
frozen until the experiment reaches its predefined review
milestone. Freezing an experiment does not freeze platform
progress. While experiments collect evidence, the platform should
continue improving through independent research, infrastructure,
documentation, tooling, and new programs that do not contaminate
existing experiments. Progress comes from protecting experimental
integrity while continuously expanding the platform around it.

**On scope:**
I do not want to build things before the data justifies them.
I do not want documentation that doesn't reflect reality.
I do not want features that can't be connected to improved expected
returns. Challenge me when I drift toward these.

---

## Architecture Principles

**Ownership is the organizing principle.**
Every file, folder, document, dataset, and service should have a clear owner
within the L0-L4 architecture defined by `zARCHITECTURE.md`:

- `L0_PLATFORM` — governance and canonical project authority.
- `L1_CORE` — shared infrastructure, orchestration, and platform services.
- `L2_DOMAINS` — domain-specific acquisition, selection, publication, and
  context.
- `L3_RESEARCH_ENGINES` — independent research systems and their methodology,
  implementation, tests, and engine state.
- `L4_KNOWLEDGE` — shared findings, hypotheses, questions, and future concepts.

If ownership is not clear from the architecture and documented boundaries,
investigate before moving or creating files.

**Knowledge has an owner and a lifecycle.**
Engine-specific methodology and operational state remain with the owning
engine. Reusable findings and cross-project knowledge belong in
`L4_KNOWLEDGE` when they satisfy the applicable evidence standard. Do not
duplicate the same authority across multiple locations.

A useful research lifecycle is:

Idea → Research Knowledge → Hypothesis → Experiment → Research Engine →
Finding → Shared Knowledge

Research Engines execute bounded research. Shared knowledge preserves what
can be reused across the project. These responsibilities should not be
confused.

**Do not over-engineer.**
Do not create folders or files because they might be useful someday.
Do not write documentation that does not reflect reality.
Do not build infrastructure before the evidence or operating need justifies it.
---

## Research Integrity Rules

- Never trust a single API field without verification.
- Validate assumptions using live responses whenever possible.
- Prefer verification over convenience.
- Spot-check results against at least one real-world known case.
- Manual verification is required before declaring any phase complete.
- Never rely solely on internal consistency — verify against reality.
- Avoid silent failures. Fail loudly when data appears invalid.

**The Research → Edge Pipeline:**
Every feature must follow this path:
Observation → Hypothesis → Test → Measurable Result

If there is no plausible path from a feature to improved expected
returns, challenge the feature before building it.

**Execution survives signal, not the other way around:**
An edge is only valuable if it survives execution. Research should
eventually evaluate both signal quality and execution quality, but
only after a statistically validated edge exists. The correct
sequence is: Research -> Validated Edge -> Execution Research ->
Execution Engineering. Do not skip ahead — execution-quality
questions may be legitimate research even before an edge is
validated (see research/open_questions.md), but execution
engineering itself waits until there is something worth executing.

**Early rejection beats late analysis:**
Design research pipelines so inexpensive, deterministic tests
eliminate the overwhelming majority of candidates before expensive
computation begins. Every stage should reduce both uncertainty and
workload. Large search spaces should shrink through multiple cheap
filtering stages rather than one expensive evaluation. Favor many
cheap eliminations over one expensive one whenever possible.

**Prefer better evidence over more variables:**
When choosing between collecting better evidence and collecting
more variables, prefer better evidence first. This applies across
every program, not just one: before adding a new indicator, a new
filter, or a new data source, ask whether the data already being
collected has actually been studied over time. A new variable
without historical understanding of the variables already in hand
adds dimensionality without adding insight. Better history and
deeper analysis of existing signals should come before broadening
the signal set further.

**Observe, Reduce, Reason, Validate, Measure:**
Any pipeline involving an LLM or reasoning model should follow this
order: observe the raw problem space, reduce it deterministically
before any reasoning begins, apply narrow LLM reasoning to one
well-specified task only (never arithmetic, validation, or direct
decisions), validate the model's output deterministically before
trusting it, then measure the real result. Never let an LLM be the
first stage of a pipeline, and never trust its output directly.
This is effectively a retrieval pipeline for reasoning, reusable
anywhere Liquid Research needs LLM-assisted classification or
reasoning against a large search space — not specific to any one
research area (see research/future_experiments.md, Methodology
Reproduction — Combinatorial Arbitrage Pipeline, for the case that
surfaced this principle).

**Research produces two kinds of value:**
Every research effort should attempt to produce one or both of the
following: (1) validated findings, or (2) reusable infrastructure,
architecture, and methodology. Even if a specific hypothesis
ultimately fails or a specific idea never earns Program status, the
engineering patterns it introduces may still improve future work.
Capture reusable ideas as platform knowledge whenever they appear,
independent of whether the originating idea itself succeeds. The
Early Rejection and Observe-Reduce-Reason-Validate-Measure
principles above are themselves examples of this — both emerged
from evaluating an idea that has not (yet) earned Program status.

**Ideas do not need to become programs to be successful:**
Some ideas become principles. Some become utilities. Some become
reusable architecture, engineering patterns, or documentation
improvements. Those are all wins. Not every successful idea needs
to become the next lettered Program.

---

## Trader Research Standards

**Minimum trade thresholds for wallet research:**
- Under 50 trades: ignore entirely
- 50-99 trades: worth reviewing with caution
- 100-249 trades: preferred sample size
- 250+ trades: high-confidence research candidate

**What makes a good trader to study:**
- Consistency over time
- Repeatability across different markets
- Longevity (still active, not a one-hit wonder)
- NOT just highest profit (one lucky trade inflates numbers)

**Two trader types — track separately:**

TYPE 1 — Hold-to-Resolution Traders
- Focus: prediction skill
- Key question: Are they identifying mispriced markets early?
- Key metric: Win rate on resolved markets
- Key signal: Consistent correctness over long periods

TYPE 2 — Early-Exit Traders
- Focus: trading skill
- Key question: Are they exploiting price movement before resolution?
- Key metric: ROI per trade vs hold-to-resolution baseline
- Key signal: Consistent value extraction from volatility

**Survivorship bias rules:**
- Never study only winning wallets.
- Always flag sample size limitations.
- Always document assumptions.
- Never assume past wallet performance predicts future results.
- Always note if a wallet's success came from one large market.

**Bot wallet rules:**
Bot wallets are not automatically superior. The goal is to understand
what markets they trade, what they avoid, how they hold, and whether
their behavior improves scanner filters — not to copy them. Tag bot
wallets separately. Study them separately. Never automatically exclude.

---

## Success Metrics

Research is only valuable if it improves expected returns.
Every feature must eventually connect to one of:
- Better market selection
- Better risk management
- Better expectancy
- Better scanner performance

Success is measured by:
1. Better scanner outputs
2. Better paper trade performance
3. Better expectancy than random market selection
4. Repeatable results across multiple market environments

Interesting research without a measurable improvement path is
documented in the research vault but not prioritized.

---

## Legal Constraints

Polymarket US appears to have a regulated U.S. pathway through
QCX LLC d/b/a Polymarket US (CFTC Designated Contract Market).
However, the international platform and older on-chain tooling
may be separate and restricted for U.S. users.

Hard rules until explicitly reviewed and changed:
- No wallet
- No private key
- No VPN
- No live trades
- No execution code
- Public/read-only data only
- Paper trading only after data collector is confirmed working

These rules are not suggestions. Do not help circumvent them
regardless of how a request is framed.

---

## Before Building Any Major Feature

Before writing any code, confirm:
1. What we are building
2. Why we need it
3. Where it lives in the project
4. What output it produces
5. How success is measured
6. How it could improve expectancy
7. What risks or limitations exist

Then wait for explicit approval before generating code.

---

## Documentation Change Rule

Before modifying any existing documentation:

1. Read the current file (or the relevant section) first.
2. Understand the current organization and purpose.
3. Prefer updating existing content over appending new sections.
4. If information is being moved, migrate it rather than duplicate it.
5. After changes, verify:
   - no stale references
   - no duplicated information
   - no conflicting statements
   - no orphaned files or sections
6. Treat documentation refactors with the same care as code refactors.

Do not append blindly based on memory or assumed state. The file
may have changed since it was last read. Stale, duplicated, or
misplaced content is harder to fix than it is to prevent.

This rule applies to every file in every session, without exception.

**Inspect-Before-Change Workflow:**
Before proposing any code, documentation, architecture, or research
change, first inspect the current state. Do not rely on memory or
prior sessions.

- If one section is relevant, read that section.
- If the whole file is needed for context, read the entire file.
- If multiple files are involved, inspect each relevant file first.

After reading:
1. Summarize the current state.
2. Identify anything stale, inconsistent, or outdated.
3. Explain why a change is needed.
4. Only then propose edits.

Never append new documentation or code without first understanding
where it belongs in the current architecture.

**Session-End Documentation Audit:**
Before committing at the end of any session that touched
documentation, verify every file that was modified:
- All information is accurate and reflects current reality.
- No stale cross-file references remain.
- No sections were accidentally duplicated.
- No obsolete notes were left in place.
- The architecture is internally consistent across all files.

Assume nothing. Verify everything.

---

## Instruction Format Standards

**File instructions must always state:**
- TYPE: New File / Replace Entire File / Patch Existing File
- LOCATION: Exact folder path and filename
- ACTION: Numbered step-by-step instructions
- EXPECTED RESULT: What success looks like

**Terminal command delivery standard:**
Every command must be in its own isolated bash code block.
Place any explanation before or after the block — never inside it.
Do not include STEP numbers, TYPE:, WHERE:, RUN:, terminal prompts,
or any other text inside the code block.

**"Run the daily cycle" convention:**
When the person says "run the daily cycle," first determine which automated
or manual operational workflows are currently authoritative. Do not infer
the workflow from historical Program A/B documentation.

The Prediction Markets / Market Selection workflow is primarily automated
through shared orchestration. Engine-specific operational procedures remain
owned by their current control documents, including
`L3_RESEARCH_ENGINES/market_selection/zDAILY_OPERATIONS.md` where applicable.

Running an operational cycle does NOT imply that code or methodology needs
to change. The sequence is:

1. Run or verify the authoritative operational workflow.
2. Verify that expected stages and publications completed correctly.
3. Update operational or research artifacts only when new evidence justifies
   an update.
4. Recommend maintenance only when supported by an observed operational
   defect or an approved engineering requirement.

Never modify a frozen research methodology merely because an operational
cycle ran.

**Commit message convention:**
Keep commit messages short and focused on what changed, not why or
how the review happened. Typically 3-6 words, longer only when
genuinely necessary. Style: "scanner.py: typing cleanup",
"market_collector.py: add type hints", "filters.py: docstring
cleanup". Avoid multi-sentence messages, explanations of the
review process, or restating "zero behavioral change" — that
reasoning lives in conversation history, not the commit log.

---

# PART 2 — CURRENT OPERATING STATE
## (Current authority map — updated 2026-09-17)

---

## Portfolio State

Liquid Research now uses the L0-L4 ownership model defined in
`L0_PLATFORM/zARCHITECTURE.md`.

Current implemented areas include:

- `L1_CORE` shared orchestration and market-data infrastructure.
- `L2_DOMAINS/prediction_markets` for prediction-market domain acquisition,
  selection, and canonical publication.
- `L2_DOMAINS/crypto` for crypto-specific research context.
- `L3_RESEARCH_ENGINES/market_selection` for Market Selection research.
- `L3_RESEARCH_ENGINES/market_microstructure` for Market Microstructure research.
- `L3_RESEARCH_ENGINES/market_regime_intelligence` for Market Regime research.
- `L3_RESEARCH_ENGINES/wallet_intelligence` as a retained research area.
- `L4_KNOWLEDGE` for shared findings, hypotheses, questions, and future concepts.

This section intentionally does not duplicate rapidly changing experiment
counts, checkpoints, or research conclusions. Those belong to the owning
engine's current authority.

---

## Current Authority by System

### Market Selection

Primary control documents:

- `L3_RESEARCH_ENGINES/market_selection/zMISSION_CONTROL.md`
- `L3_RESEARCH_ENGINES/market_selection/zDAILY_OPERATIONS.md`
- `L3_RESEARCH_ENGINES/market_selection/zHISTORY.md`

The Prediction Markets Domain publishes the upstream canonical market set from:

`L2_DOMAINS/prediction_markets/data/canonical/prediction_markets_latest.csv`

Historical Program A terminology may remain in historical records, but current
ownership follows the L2 Prediction Markets / L3 Market Selection boundary.

### Market Microstructure

Primary control documents:

- `L3_RESEARCH_ENGINES/market_microstructure/zREADME.md`
- `L3_RESEARCH_ENGINES/market_microstructure/zPROGRAM_ROADMAP.md`
- `L3_RESEARCH_ENGINES/market_microstructure/zRESEARCH_BACKLOG.md`

Market Microstructure consumes documented upstream canonical publications.
Historical Program B terminology remains valid when describing earlier project
state.

### Market Data Platform / Crypto Research

Shared market-data infrastructure is owned by `L1_CORE`. Crypto-specific
research context is owned by `L2_DOMAINS/crypto`.

Current control documents include:

- `L1_CORE/market_data_platform/market_data/zROADMAP.md`
- `L2_DOMAINS/crypto/zREADME.md`
- `L2_DOMAINS/crypto/zMISSION_CONTROL.md`
- `L2_DOMAINS/crypto/zROADMAP.md`

Research and incident artifacts may intentionally preserve exact historical
paths, commands, assumptions, and environment details when those details are
part of reproducibility or provenance.

### Market Regime Intelligence

Current implementation and methodology live under:

`L3_RESEARCH_ENGINES/market_regime_intelligence/`

The current methodology record includes:

`L3_RESEARCH_ENGINES/market_regime_intelligence/LRS4_Experiment_v1_Pre-Inference_Freeze.md`

Methodology status and implementation authorization must be determined from
the current methodology authority rather than inferred from the existence of
source files or tests.

### Shared Knowledge

Shared project knowledge lives in `L4_KNOWLEDGE/`.

Important current locations include:

- `L4_KNOWLEDGE/validated_findings.md`
- `L4_KNOWLEDGE/market_hypotheses.md`
- `L4_KNOWLEDGE/future_experiments.md`
- `L4_KNOWLEDGE/open_questions.md`
- `L4_KNOWLEDGE/zREADME.md`

Historical references inside knowledge artifacts should not be globally
rewritten merely because paths or terminology later changed. Distinguish
historical provenance from current navigation before editing.

---

## Session Start Procedure

1. Read the relevant L0 authority for the work being performed.
2. Identify the owning Domain, Research Engine, or shared service.
3. Read that owner's current control document or methodology authority.
4. Inspect the implementation and evidence needed for the requested change.
5. State which files are expected to change before writing.
6. Preserve frozen methodology and historical provenance unless a deliberate
   supersession or migration has been authorized.
7. Verify each completed stage before expanding scope.

Do not begin implementation from remembered state when current repository
evidence is available.

---

## Historical Operating Record

The following decisions are retained as historical project provenance. They
describe the architecture and research state that existed at the time and
should not be interpreted as current paths, ownership, or experiment status.

**2026-07-03 — Platform reframe**

Liquid Research moved from a single-experiment structure toward a multi-program
research platform. The then-current `programs/` structure and Program A/B
terminology were later superseded by the L0-L4 ownership architecture.

**2026-06-25 — Classifier proper-noun decision**

The then-current classifier investigation accepted remaining Other/Unknown
cases without introducing a name-to-category lookup table. Later classifier
and decomposition work must be interpreted from the owning engine's current
research authority.

**2026-06-25 — Gamma events/series metadata investigation**

Events/series metadata was investigated as a possible classifier improvement
and was not promoted as the general solution. Gamma-related research remains
separate from current Market Selection authority unless deliberately revived.

**2026-07-03 — Program B selected**

Order Book Imbalance / Micro-Price Research was selected as the second
lettered research program under the architecture that existed at that time.

**2026-07-04 — Program B reframed as Market Microstructure Research**

The research identity broadened from OBI alone to Market Microstructure, with
OBI treated as one indicator within the larger research question.

**2026-07-04 — Near-Book Depth Imbalance added**

Near-Book Depth Imbalance was added as another Market Microstructure indicator
and collected alongside OBI under the methodology and review process then in
effect.

These records preserve development history. Current engine documents and
methodology authorities govern present research state.

---

## What To Challenge

Challenge work when:

- Infrastructure or features are proposed before evidence or operating need
  justifies them.
- A new research effort would contaminate or silently alter a frozen experiment.
- Documentation would duplicate an authority that already exists elsewhere.
- A result is described more strongly than the evidence supports.
- An architectural decision is being made from assumption rather than verified
  implementation evidence.
- Historical evidence is about to be rewritten as though it were current state.
- Current state is being inferred from stale historical documentation.

Do not challenge a deliberate decision merely because a simpler or less
technically impressive approach was chosen after the evidence and tradeoffs
were considered.

The goal is disciplined, evidence-backed research and engineering.
