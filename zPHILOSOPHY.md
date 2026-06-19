# Liquid Research — Philosophy, Criteria & Operating Rules

## Core Mission
Find repeatable prediction-market edges through data,
not intuition. Every feature must connect back to one question:
"Can this information improve expected returns?"

---

## What This Project Is
- A prediction market research platform
- A market scanner
- A paper trading simulator
- A pattern discovery engine

## What This Project Is NOT
- A trading bot
- An execution engine
- A wallet copier
- A get-rich-quick system

---

## Legal Notice
Polymarket US appears to have a regulated U.S. pathway through
QCX LLC d/b/a Polymarket US, which is listed by the CFTC as a
Designated Contract Market. However, the international Polymarket
platform and older crypto/on-chain tooling may still be separate
and restricted for U.S. users. This project must remain read-only
and research-only until the exact legal/trading pathway is confirmed.

Hard rules until explicitly reviewed:
- No wallet
- No private key
- No VPN
- No live trades
- No execution code
- Public/read-only data only
- Paper trading only after data collector is confirmed working

---

## Build Order

Always follow this order:

Phase 1 — Data Collection
Phase 2 — Data Validation
Phase 3 — Wallet Research
Phase 4 — Scanner Improvements
Phase 5 — Paper Trading
Phase 6 — Performance Analysis
Phase 7 — Dashboard
Phase 8 — Alerts
Phase 9 — Execution (only if explicitly approved)

Rules:
- Never skip phases
- Never build dashboards before research is validated
- Never build execution before paper trading proves value
- Never optimize something that has not been validated

---

## Success Metrics

Research is only valuable if it improves expected returns.

Every feature must eventually connect back to one of these:
- Better market selection
- Better risk management
- Better expectancy
- Better scanner performance

Success is measured by:
1. Better scanner outputs
2. Better paper trade performance
3. Better expectancy than random market selection
4. Repeatable results across multiple market environments

Interesting research without measurable improvement
is documented but not prioritized.

---

## Research → Edge Pipeline

Every feature must follow this path:

Observation → Hypothesis → Test → Measurable Result

Example:
Observation: Top wallets rarely trade markets under $50k volume
Hypothesis: Volume filter improves win rate
Test: Compare scanner results before and after filter
Result: Win rate increases or it doesn't — document both outcomes

If there is no plausible path from a feature to improved
expected returns, challenge the feature before building it.

---

## Before Building Any Major Feature

Before writing any code, explain:

1. What we are building
2. Why we need it
3. Where it lives in the project
4. What output it produces
5. How success is measured
6. How it could improve expectancy
7. What risks or limitations exist

Then wait for approval before generating code.

---

## Trader Research Criteria

### Minimum Trade Thresholds
- Under 50 trades = ignore entirely
- 50-99 trades = worth reviewing with caution
- 100-249 trades = preferred sample size
- 250+ trades = high-confidence research candidate

### What Makes a Good Trader to Study
Good traders are defined by:
- Consistency over time
- Repeatability across different markets
- Longevity (still active, not a one-hit wonder)
- NOT just highest profit (one lucky trade inflates numbers)

### Two Trader Types to Track Separately

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

---

## Wallet Scoring System (Target Metrics)
1. Number of trades
2. Win rate
3. ROI per trade
4. Profit consistency (not just total profit)
5. Longevity (how long actively trading)
6. Average position size
7. Market diversity (categories traded)
8. Risk-adjusted performance

---

## Survivorship Bias Rules
- Never study only winning wallets
- Always flag sample size limitations
- Always document assumptions
- Never assume past wallet performance predicts future results
- Always note if a wallet's success came from one large market

---

## Bot Wallet Research Rules

Bot wallets are not automatically considered superior.

The goal is not to copy bot wallets.

The goal is to understand:
- What markets they trade
- What markets they avoid
- How long they hold positions
- Whether their behavior improves scanner filters

Bot wallets should be tagged and studied separately
from human traders.

Any wallet identified as a likely bot should be flagged
but not automatically excluded.

Bot wallet insights feed into scanner filter improvements,
not direct trade copying.

---

## Teaching Mode — Instruction Format

The user is learning Python while building this project.

The user has successfully completed:
- Python installation
- VS Code setup
- Virtual environment setup
- Package installation
- GitHub integration
- Git commits and pushes
- Running Python scripts from terminal

The user is not a professional Python developer.
Never assume knowledge. Always explain context.

### File Instruction Format

Every file instruction must state:

TYPE:
- New File
- Replace Entire File
- Patch Existing File

LOCATION:
- Exact folder path
- Exact filename

ACTION:
- Numbered step-by-step instructions

EXPECTED RESULT:
- What success looks like in VS Code Explorer

Example:

TYPE: New File

LOCATION:
collectors/api_sanity_check.py

ACTION:
1. Right-click collectors folder in VS Code
2. Click New File
3. Name it api_sanity_check.py
4. Paste the code below
5. Save with Cmd+S

EXPECTED RESULT:
You should see api_sanity_check.py
appear inside the collectors/ folder.

---

### Terminal Instruction Format

Every terminal command must be isolated.
Never combine unrelated commands in one block.

Format:

STEP 1
TYPE: Terminal Command
WHERE: VS Code Terminal

RUN:
[single command here]

EXPECTED RESULT:
[what you should see]

STOP HERE. Confirm before continuing.

---

The user should never have to guess:
- Where code goes
- Whether something is a terminal command
- Whether a file should be created or replaced
- Whether commands run individually or as a batch

---

## Project Status

Phase 1 — Data Collection ✅ COMPLETE
Phase 2 — Data Validation 🔄 IN PROGRESS
Phase 3 — Wallet Research 🔲 NOT STARTED
Phase 4 — Scanner Improvements 🔲 NOT STARTED
Phase 5 — Paper Trading 🔲 NOT STARTED
Phase 6 — Performance Analysis 🔲 NOT STARTED
Phase 7 — Dashboard 🔲 NOT STARTED
Phase 8 — Alerts 🔲 NOT STARTED
Phase 9 — Execution 🔒 LOCKED