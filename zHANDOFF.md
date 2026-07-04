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
1. Finishing active experiments before starting new ones — unless
   a genuinely independent program with higher ROI exists and can
   run without contaminating the active experiment.
2. Evidence-driven work over speculative work.
3. Self-contained work over work requiring new infrastructure.
4. Work that produces findings over work that produces features.

**On parallel programs:**
Liquid Research operates as a multi-program platform. Independent
research programs can run simultaneously as long as:
- They test genuinely different hypotheses.
- Their data and methodology do not contaminate each other.
- Each program maintains its own documentation.
- Each program's findings feed into the shared platform knowledge.

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


---

## Instruction Format Standards

**File instructions must always state:**
- TYPE: New File / Replace Entire File / Patch Existing File
- LOCATION: Exact folder path and filename
- ACTION: Numbered step-by-step instructions
- EXPECTED RESULT: What success looks like

**Terminal command format:**
Every command must be isolated. Never combine unrelated commands.

STEP N
TYPE: Terminal Command
WHERE: VS Code Terminal
RUN: [single command]
EXPECTED RESULT: [what you should see]
STOP. Confirm before continuing.

**The user should never have to guess:**
- Where code goes
- Whether something is a terminal command
- Whether a file should be created or replaced
- Whether commands run individually or as a batch

**Checkpoint everything.** Small verified steps are better than
large unverified ones. When in doubt, stop and confirm.

---

# PART 2 — CURRENT OPERATING STATE
## (As of 2026-07-03. Update this section as the project evolves.)

---

## Current Platform Status

Liquid Research has transitioned from a single-experiment project
to a multi-program research platform. Program A (Scanner One)
continues its daily data collection cycle. Program B (Order Book
Imbalance) is queued and ready to begin.

Full program registry: zROADMAP.md — Active Research Programs section.

---

## Program A — Current State

**What it is:** Testing whether tradeability_score (combining
liquidity, spread quality, and volume) predicts better paper-trade
outcomes on Polymarket.

**Daily cycle:** Runs every day. Collect → Scan → Paper Trade →
Resolve → Review. See programs/program_a/DAILY_OPERATIONS.md.

**Current dataset:** 61 total trades, 32 closed, 29 open.

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

**What it is:** Testing whether order book imbalance predicts
short-term price movement better than midpoint alone.

**Status:** QUEUED. No work has begun. No operational documents
exist yet beyond programs/program_b/README.md.

**When it begins:** Explicitly, by decision — not automatically.
When Program B begins, its MISSION_CONTROL.md and
DAILY_OPERATIONS.md will be created based on what the work
actually requires, not based on assumptions.

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
