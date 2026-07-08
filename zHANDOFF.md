# Liquid Research — Operating Manual

This document is the single source of truth for how Liquid Research
is built, how decisions are made, and how future Claude sessions
should collaborate on this project.

Read this before writing any code, moving any files, or making any
architectural decisions. If anything here conflicts with another
document, this document takes precedence — then update the other
document to match.

---

# PART 1 — STABLE PRINCIPLES
## (These change rarely. Treat them as the project's constitution.)

---

## What Liquid Research Is

Liquid Research is a multi-program research platform whose purpose
is to discover statistically defensible, monetizable trading edges
in prediction markets.

It is:
- A prediction market research platform
- A market scanner
- A paper trading simulator
- A pattern discovery engine
- A multi-program research incubator

It is NOT:
- A trading bot
- An execution engine
- A wallet copier
- A get-rich-quick system
- A single-experiment project

Every feature, every research program, every line of code must
connect back to one question:
"Does this increase the probability of discovering a repeatable
edge that can eventually generate meaningful income?"

If the answer is unclear, challenge the feature before building it.

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
Every file, every folder, every document has one clear owner:
- Platform (universal knowledge, shared across all programs)
- Program A (operational knowledge specific to Scanner One)
- Program B (operational knowledge specific to OBI research)
- Future programs as they are created

If ownership isn't immediately obvious from the folder structure,
the architecture is probably wrong.

**Two kinds of knowledge:**
1. Platform / Universal — lives in research/ and root-level docs.
   Shared by every program. Never duplicated.
2. Program-Specific — lives in programs/program_x/. Owned entirely
   by that program. Not shared.

**The idea lifecycle:**
Idea → Research Vault → Hypothesis → Experiment → Program →
Finding → Platform Knowledge

Programs execute research. The vault discovers research.
These are different responsibilities and should never be confused.

**Do not over-engineer.**
Do not create folders or files because they might be useful someday.
Do not write documentation that doesn't reflect current reality.
Do not build infrastructure before the data justifies it.

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
When the person says "run the daily cycle," this means: run the
normal daily operational workflow for every currently active
program, not just Program A. As of 2026-07-08 that means Program A
and Program B. Any future program added to Liquid Research
automatically becomes part of the daily cycle unless explicitly
excluded — no separate reminder needed to include it.

Running the daily cycle does NOT imply any program needs code
changes. The correct sequence is: (1) run each program's normal
daily workflow, (2) verify everything completed correctly, (3)
update operational artifacts (MISSION_CONTROL.md, research
checkpoints, program logs) only if the day's results actually
justify an update, (4) only then consider whether any program
needs maintenance — and only recommend maintenance backed by a
real observation from that day's run, not for its own sake.

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
## (As of 2026-07-03. Update this section as the project evolves.)

---

## Current Platform Status

Liquid Research has transitioned from a single-experiment project
to a multi-program research platform. Program A (Scanner One)
continues its daily data collection cycle. Program B (Market
Microstructure Research) is active, with OBI/Micro-Price and
Near-Book Depth Imbalance both collecting daily observations.

Full program registry: zROADMAP.md — Active Research Programs section.

---

## Program A — Current State

**What it is:** Testing whether tradeability_score (combining
liquidity, spread quality, and volume) predicts better paper-trade
outcomes on Polymarket.

**Daily cycle:** Runs every day. Collect → Scan → Paper Trade →
Resolve → Review. See programs/program_a/DAILY_OPERATIONS.md.

**Current dataset:** 70 total trades, 33 closed, 37 open.

**Key finding to date:** First median-split analysis (n=32, 2026-07-02)
showed low-score trades outperforming high-score trades, but ~85%
of the low-score group's P&L came from two high-payout trades
entered near 50% implied probability. The observed result is
consistent with entry-price and payout structure acting as a
confounding factor, but the relationship between tradeability score
and entry price has not yet been quantified. Hypothesis remains
unresolved. See research/validated_findings.md.

**Next milestone:** 100 closed trades — bucket comparisons become
meaningful.

**Do not modify Program A's methodology** while it is collecting
data toward the 100-trade milestone. The experiment must remain
frozen for the results to be interpretable.

---

## Program B — Current State

**What it is:** Market Microstructure Research. Studies order-book
indicators as a class. Indicator 1 (OBI/Micro-Price) and Indicator 2
(Near-Book Depth Imbalance) are both actively collecting data.

**Status:** ACTIVE. Both indicators logging daily observations
(data/program_b/obi_log.csv, data/program_b/near_book_depth_log.csv).
Review checkpoints scheduled for approximately 2026-07-10 (1-week),
2026-07-17 (2-week), and 2026-08-03 (1-month). See
programs/program_b/README.md for full detail.

**Do not modify Program B's methodology** while indicators are
collecting data toward their review checkpoints, for the same
reason Program A's methodology stays frozen.

---

## Key Architectural Decisions Made

**2026-07-03 — Platform reframe**
Liquid Research restructured from single-experiment project to
multi-program research platform. programs/ folder created.
Program A documentation moved to programs/program_a/.
zROADMAP.md restructured as platform document.
zHANDOFF.md rewritten as unified operating manual.
zPHILOSOPHY.md deleted (content migrated here).

**2026-06-25 — Classifier proper-noun decision**
Remaining Other/Unknown trades (Starmer, Mojtaba Khamenei,
aliens-type) accepted as permanently Other/Unknown. No name-to-
category lookup table. See research/validated_findings.md.

**2026-06-25 — Gamma events/series metadata investigation**
Investigated as a classifier fix. Found not viable — series
absent on all tested markets, events helped only 1/6 cases.
Full findings in research/validated_findings.md.

**2026-07-03 — Program B selected**
Order Book Imbalance / Micro-Price Research selected as Program B
after full architectural review of the research vault. Promoted
from research/future_experiments.md. No infrastructure blocker.

**2026-07-04 — Program B reframed as Market Microstructure Research**
Program B's identity broadened from "OBI Research" to "Market
Microstructure Research," with OBI established as Indicator 1
rather than the entire scope. Folder structure split into
indicators/, diagnostics/, and analysis/ to support multiple
independent indicators cleanly.

**2026-07-04 — Indicator 2 added: Near-Book Depth Imbalance**
Second Program B indicator added, testing whether volume near the
current price (top N book levels) diverges meaningfully from
total-book OBI. Logs independently to
data/program_b/near_book_depth_log.csv. Both indicators now
collecting data in parallel under the same review cadence.

---

## Files to Know

**Root level:**
- `zHANDOFF.md` — this file. The operating manual.
- `zROADMAP.md` — platform roadmap and program registry.
- `README.md` — public-facing project summary.

**Program A:**
- `programs/program_a/MISSION_CONTROL.md` — current state scorecard.
- `programs/program_a/DAILY_OPERATIONS.md` — daily cycle procedure.
- `programs/program_a/HISTORY.md` — Phase 0-9 build history.

**Program B:**
- `programs/program_b/README.md` — status and hypothesis only.

**Research Vault (universal, shared):**
- `research/validated_findings.md` — verified findings, platform-wide.
- `research/market_hypotheses.md` — all testable hypotheses.
- `research/future_experiments.md` — experiment designs not yet running.
- `research/open_questions.md` — important unanswered questions.
- `research/README.md` — vault governance and research funnel rules.

---

## What to Do at the Start of Every Session

1. Read zHANDOFF.md (this file) to understand the project and the person.
2. Read zROADMAP.md to understand where the platform is going.
3. Check programs/program_a/MISSION_CONTROL.md for Program A's current state.
4. Ask what today's goal is before writing any code.
5. List files expected to change before changing them.
6. Checkpoint every stage. Confirm before continuing.

Do not immediately start generating code. Understand first.

---

## What To Challenge

Challenge me when:
- I want to build something before the data justifies it.
- I want to start a new program before existing ones have produced findings.
- I want to add documentation that duplicates something that already exists.
- I'm using exciting language about a result that could be explained by noise.
- I'm about to make an architectural decision based on assumption rather than evidence.

Do not challenge me when:
- I make an explicit decision after hearing your honest assessment.
- I choose a simpler approach over a technically impressive one.
- I defer something that isn't ready yet.

The goal is honest collaboration, not agreement.
