LIQUID RESEARCH — BEGINNER WORKFLOW RULES

USER EXPERIENCE RULE — NEVER ASSUME

The user is learning Python while building this project.

The user should never have to guess:

* Where code goes
* Whether something is a terminal command
* Whether a file should be created
* Whether a file should be replaced
* Whether commands run one at a time
* Whether commands run as a batch

Every instruction must explicitly state:

1. WHAT
2. WHERE
3. HOW
4. EXPECTED RESULT

Example:

BAD:

“Paste this code.”

GOOD:

STEP 3

TYPE: New File

LOCATION:
collectors/api_sanity_check.py

ACTION:

1. Right-click collectors folder.
2. Click New File.
3. Name it:

api_sanity_check.py

4. Copy the code below.
5. Paste it into the new file.
6. Save with Cmd+S.

EXPECTED RESULT:

You should now see:

collectors/
market_collector.py
api_sanity_check.py

in the VS Code Explorer.

⸻

TERMINAL COMMAND FORMAT

Every terminal command must be isolated.

Never send a giant block of commands without explanation.

Use this format:

STEP 1

TYPE: Terminal Command

WHERE:
VS Code Terminal

RUN:

python3 –version

EXPECTED RESULT:

Python 3.10 or higher should appear.

STOP HERE.

Wait for confirmation before continuing.

⸻

MULTI-COMMAND FORMAT

If multiple commands are required:

Label them separately.

Example:

STEP 1

TYPE: Terminal Command

RUN:

git status

STEP 2

TYPE: Terminal Command

RUN:

git add .

STEP 3

TYPE: Terminal Command

RUN:

git commit -m “message”

Do not combine unrelated commands.

⸻

FILE CREATION FORMAT

Whenever creating a file:

Always state:

NEW FILE

or

REPLACE ENTIRE FILE

or

PATCH EXISTING FILE

Never simply say:

“Create this file.”

Without specifying:

* exact folder
* exact filename
* exact action

⸻

PHASE RULE

Only one major task at a time.

Do not give:

* 15 terminal commands
* 5 files
* 4 architecture decisions
* 3 API discussions

in one response.

Break work into small checkpoints.

Checkpoint → Verify → Continue.

⸻

ARCHITECTURE RULE

Before writing code:

Always explain:

1. What we are building
2. Why we need it
3. Where it lives
4. What output it produces
5. How success is measured

Then wait for approval.

⸻

RESEARCH-FIRST RULE

Liquid Research is a research platform.

Not a trading bot.

Not an execution engine.

Not a wallet manager.

Not an AI trading system.

Every feature must answer:

“What research question does this help us answer?”

If it does not improve research capability, do not build it.

⸻

SESSION START FORMAT

At the beginning of every session:

1. Ask for current repository structure.
2. Ask for current file list.
3. Ask what phase we are currently in.
4. Explain today’s goal.
5. List files expected to change.
6. Explain whether code will be written.
7. Ask all questions up front.

Do not immediately start generating code.

⸻

SUCCESS CRITERIA

The user should always know:

* What is happening
* Why it is happening
* Where it is happening
* What success looks like

The user should never feel forced to guess.





## Research Log — Wallet Pipeline Validation (Two-Wallet Test)

### Wallet 1: poRussky
- 50 trades pulled, 100% Crypto Ultra-Short
- 0 eligible trades, 50 excluded
- PROVED: exclusion filter correctly identifies and removes
  pure ultra-short gambling wallets from research

### Wallet 2: KickstandBot
- 200 trades pulled
- 68 eligible (Geopolitical, Macro/Economic, Political)
- 131 flagged Review (mostly weather/temperature markets,
  plus assorted speculative markets — entertainment, AI
  product launches, etc.)
- 1 excluded (entertainment box office market)
- PROVED: eligible-trade pipeline works correctly end-to-end
  on a wallet with real Active Research category activity
- FINDING: this wallet is broad/general-purpose, not a focused
  Active Research specialist — Review trades outnumber eligible
  trades roughly 2-to-1

### Resolution Status
- All 68 eligible trades from KickstandBot returned Open
- 0 Confirmed/scored trades — no win rate or P&L produced
- This is NOT a code failure. Confirmed resolution logic was
  already independently verified via:
  - Standalone hardcoded tests (10/10 passing)
  - Live API test against a known-resolved market
    (Czechia World Cup match — correctly Confirmed)
  - Live API test against a known dirty/archived market
    (Biden COVID market — correctly Unconfirmed, no guess)

### Conclusion
The current bottleneck is WALLET SOURCING, not classification,
resolution, or analysis logic. Every layer of the pipeline has
been independently proven correct. What's missing is a systematic
way to find wallets that (a) trade Active Research categories AND
(b) have a meaningful number of already-resolved trades in their
history — rather than discovering this by manually guessing at
wallet addresses one curl call at a time.

### Next Step
Build analyzers/wallet_discovery.py — systematic wallet sourcing
from relevant markets, not leaderboard winners. Manual wallet
hunting has hit diminishing returns.