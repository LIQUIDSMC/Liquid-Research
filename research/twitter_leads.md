# Twitter/X Leads

Unverified by default. A tweet is not evidence, see README.md.

## Template

Date:
Source: (handle)
Link:
Summary:
Why it might matter:
Initial confidence: Low / Medium / High
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted

Date: 2026-07-31
Source: @0x_Punisher
Link: https://x.com/0x_punisher/status/2081138347376820428?s=46&t=xiJECRLtS-xWWvG6ntPs1g
Summary: Two distinct subjects from the same author — the linked thread plus related posts from the same author. (1) The linked thread is an educational piece on look-ahead bias / future-data leakage in OHLCV-style historical backtesting, with concrete before/after pseudocode covering current-candle leakage, same-day aggregate leakage, global-scaler leakage, centered rolling-window leakage, and label leakage. Proposes a walk-forward execution pattern (history/decision/outcome) to make future data structurally unreachable rather than relying on developer discipline. (2) A separate set of posts/screenshots from the same author cover Polymarket-specific live execution setup: a correctly-coded bot may place no orders because Polymarket's trading/funder address is a separate proxy from the visible wallet address, USDC must be funded to that proxy, the exchange contract requires an on-chain allowance that must confirm before orders succeed, and cached balance responses can mask this. These two subjects are unrelated failure modes (data-integrity vs. deployment-infrastructure) and should not be conflated.
Why it might matter: The look-ahead thread's examples are framed around OHLCV/ML backtesting, which LRS does not currently do, but the underlying principle (every feature has a timestamp at which it becomes known; can the system have known this value at decision time) is a plausible lens for real, unaudited questions about Program A's paper-trade decision/resolution timing and Program B's cross-source observation pairing. The funder/allowance material is not currently relevant, since LRS has no live order execution, but would become relevant if a live-execution phase is ever built.
Author's claimed experience ("hundreds of bots built," profit screenshots) is unverified — treat the technical content on its own merits, independent of the author's credibility claims.
Initial confidence: Medium
Status: Reviewing
