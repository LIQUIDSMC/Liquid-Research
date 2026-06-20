# Validated Findings

Discoveries verified against real-world data, checked directly, reproduced, and measured. This is the only file in the vault where entries are treated as reliably true going forward.

## Template

Finding:
How it was verified: (exact test performed)
Date verified:
Evidence: (link to commit, terminal output, or session log)
Affects: (which module(s)/file(s))

## Confirmed Entries

Finding: Combined user and market filtering works on the Data API /trades endpoint.
How it was verified: curl tested with a known wallet and known conditionId together; all returned trades matched both filters exactly.
Date verified: 2026-06-19
Evidence: Session log, Patch B pre-work.
Affects: wallet_analyzer.py Mode 2

Finding: The Data API's /trades endpoint requires the market parameter to be a conditionId hash, not Polymarket's internal numeric id field. Numeric IDs are silently ignored and the API falls back to unfiltered default results rather than raising an error.
How it was verified: Identical-looking trade results were returned for two different numeric market_id values, proving no real filtering occurred. Switching to the conditionId hash format produced correctly scoped, varied results.
Date verified: 2026-06-19
Evidence: market_collector.py fix, wallet_discovery.py rerun, 79 wallets to 684 wallets after fix, commit 7c4d975.
Affects: market_collector.py, wallet_discovery.py

Finding: The correct way to fetch a single market by slug from the Gamma API is a path parameter, not a query parameter. The query parameter form silently returns an empty result.
How it was verified: curl tested both forms against the same known slug; only the path form returned data.
Date verified: 2026-06-18
Evidence: market_resolution.py fetch_market_by_slug(), session log.
Affects: market_resolution.py

Finding: Market resolution outcome is determined by comparing outcomes against outcomePrices. The outcome whose price is exactly 1, within tolerance, is the winner. A market can be closed true but still have unclear or dirty pricing, such as both prices showing 0, which must resolve as Unconfirmed, never guessed.
How it was verified: Tested against a known-resolved market with a clean winner, a known archived/dirty market, and a 50/50 partial-resolution case. All three states behaved correctly.
Date verified: 2026-06-18
Evidence: market_resolution.py standalone test suite, 10 of 10 passing, live API verification.
Affects: market_resolution.py, wallet_analyzer.py

Finding: Plain substring keyword matching produces false positives, such as nfl matching inside inflation. Word-boundary regex matching is required for reliable category classification.
How it was verified: Direct test case caught the bug before it reached production data; fix verified against the same test case afterward.
Date verified: 2026-06-18
Evidence: market_classifier.py, commit ef1f272.
Affects: market_classifier.py



Finding: Gamma API ?condition_ids= lookup works correctly when given a real, correct conditionId.
How it was verified: Looked up 0x8bf1c1536ecb1c08fe13c6b71e8ab1f58bf3461c4cb79f5f1679f869a06aef86 directly; the API returned the correct Fed July 2026 market with matching conditionId, slug, and question.
Date verified: 2026-06-19
Evidence: diagnostics/find_resolved_market.py investigation, direct curl confirmation.
Affects: Corrects an earlier finding — previous failures using this parameter were caused by bad/stale numeric IDs as input, not by the parameter itself being invalid.




Finding: fetch_market_by_condition_id() in market_resolution.py is unreliable, even when given a correct, verified conditionId. It returns an empty result intermittently, while fetch_market_by_slug() on the exact same market returns correctly every time.
How it was verified: Direct isolated testing on 2026-06-19 — the same conditionId for a known-resolved market (Czechia World Cup match) returned a full market record via slug lookup but zero results via the condition_ids query parameter, repeatedly, across three separate attempts at different times.
Date verified: 2026-06-19
Evidence: diagnostics/validate_resolved_trade.py — after switching resolve_trades_batch() to slug-first lookup, 20/20 real trades from this market correctly scored as Confirmed, with manually verified correct win/loss and P&L.
Affects: market_resolution.py (resolve_trades_batch), and retroactively wallet_analyzer.py Mode 1 and Mode 2, which likely produced false "Open" results for some trades prior to this fix.

Finding: Phase 3 end-to-end validation achieved. The full pipeline (fetch real trades → classify → resolve against a known-closed market → score win/loss → calculate P&L) produces correct, verifiable results.
How it was verified: 20 real trades pulled from a known-resolved market (Czechia vs South Africa World Cup match, winning outcome "No"). All 18 "No" trades scored as wins, both "Yes" trades scored as losses, P&L signs matched expected direction, and one trade was manually walked through in plain English and matched the code's output exactly.
Date verified: 2026-06-19
Evidence: diagnostics/validate_resolved_trade.py output, this session.
Affects: Confirms market_resolution.py, wallet_analyzer.py Mode 1/Mode 2, market_classifier.py all work correctly together as one verified pipeline.
