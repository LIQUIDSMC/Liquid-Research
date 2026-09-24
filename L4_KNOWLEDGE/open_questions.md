# Open Questions

Important unanswered questions that are not yet hypotheses, experiments, or roadmap items. Things worth remembering to ask later, once enough data exists to ask them properly.

## Template

Question:
Why it matters:
What data would be needed to answer it:
Date raised:

## Current Questions

Question: Do profitable wallets exit early, or hold to resolution?
Why it matters: Directly informs whether Liquid Research should study prediction skill traders or trading skill traders differently, per the trader-type distinction in zHANDOFF.md.
What data would be needed: A meaningful sample of wallets with both resolved trades and visible exit timing across many markets.
Date raised: 2026-06-19

---

Question: Are repetitive micro-orders, bot-like, identical size and price patterns, predictive of anything, profitability, a specific strategy, or just noise?
Why it matters: Several discovered wallets show this pattern. Worth knowing whether it is a distinct, study-able behavior or irrelevant clutter to filter out.
What data would be needed: Resolved trade outcomes for several wallets exhibiting this pattern, compared against wallets with varied order behavior.
Date raised: 2026-06-19

---

Question: Does category specialization, trading mostly one Active Research category, correlate with higher win rate than generalist wallets?
Why it matters: Would directly inform whether future scanner filters should weight by wallet specialization.
What data would be needed: Per-category win rate broken down per wallet, across enough wallets to compare specialists versus generalists meaningfully.
Date raised: 2026-06-19

---

Question: Do high-volume, large position size, wallets outperform low-volume wallets, or is size unrelated to skill?
Why it matters: Would inform whether position size itself is a useful signal, separate from win rate.
What data would be needed: Resolved P&L data segmented by average position size across a meaningful wallet sample.
Date raised: 2026-06-19

---

Question: Why are most discovered wallets showing only unresolved trades?
Why it matters: Phase 3 validation requires resolved outcomes.
Current evidence: KickstandBot, poRussky, and the Mode 2 candidate
wallet (0x1abf0a579401ebf4c44f919755ad20b6ae23f38d) all primarily traded currently active markets.
Potential test: Analyze additional candidate wallets and look for
older resolved markets. Better approach identified: search markets
for resolution status first, then find which discovered wallets
touched that specific market, rather than picking a wallet first.
Status: Open
Update (2026-06-20): Re-ran find_resolved_market.py after fixing
the slug-lookup bug in market_resolution.py. With the bug fixed,
the script now correctly resolves every market's real question
and status (previously showed false "Not in batch" for all 20).
Result confirmed honestly: all 20 discovered markets are still
genuinely Open. This is real-world timing, not a tooling gap.
Status: Confirmed — answer is "not enough time has passed yet,"
not a code issue.
Date raised: 2026-06-19

---

Question: Does clob_client.py's outcome_index=0 default correctly represent the primary outcome across all market types, including genuinely multi-outcome (3+) markets?
Why it matters: All three validation tests used the default index 0, which happened to be "Yes" in each case. Behavior for index 1, 2+ is implemented but has never actually been exercised against real data.
Current evidence: get_market_clob_data() accepts outcome_index as a parameter and uses it correctly in code, but only the default value has been tested.
Potential test: Run clob_client.py against a market with 3+ outcomes (e.g. a World Cup group winner market with multiple named outcomes) using outcome_index=1 or 2.
Status: Open

---

Question: How does clob_client.py behave under CLOB API rate limiting (HTTP 429)?
Why it matters: fetch_official_endpoints() and fetch_order_book() catch generic request exceptions but do not specifically detect or handle 429 responses with backoff/retry logic. Untested under real rate-limit conditions since only ~15 total calls were made across 3 markets in testing so far.
Current evidence: No 429 response has been observed yet. Behavior under this condition is unverified.
Potential test: Run clob_client.py against a larger batch of markets (10+) in quick succession and observe whether any 429s occur and how they're currently handled.
Status: Open

---

Question: Are the 0.05/0.95 thresholds in filters.py's _is_near_extreme_price() the right cutoffs for flagging "near 0 or 1" pricing in spread quality labels?
Why it matters: These thresholds were chosen by inspection, not derived from data. Only one real data point (Ivory Coast, midpoint 0.0055) has confirmed the logic fires correctly. No data point yet confirms where it should NOT fire (e.g. is a market at midpoint 0.10 "near extreme" or not?).
Current evidence: Single confirmed case at midpoint 0.0055. Function exists and runs without error, but the specific cutoff values are a judgment call, not a validated finding.
Potential test: Run label_spread_quality() against more markets across a range of midpoints (0.05, 0.10, 0.15, 0.20...) to see whether 0.05/0.95 actually separates "structurally elevated spread_pct" cases from normal ones, or whether the boundary should move.
Status: Open

---

## Future Research Domain — Execution Quality

These questions emerged from reviewing external research on
Polymarket execution dynamics (2026-07-05). Not yet a coherent
research program — just a set of related open questions. Per the
research vault's own promotion rules, this domain earns its own
document only once enough related questions and experiments
accumulate. Until then, it lives here.

Question: How frequently does displayed liquidity disappear before it can be acted on?
Why it matters: If quotes vanish quickly, displayed book depth may overstate what's actually available, which would affect how any future signal (OBI, near-book depth, etc.) should be interpreted.
What data would be needed: Repeated observation of the same market's order book over short time windows — a different data collection pattern than the current point-in-time snapshots used by Program A and Program B.
Date raised: 2026-07-05

---

Question: How stable is order-book depth over short time horizons?
Why it matters: Directly relevant to whether Program B's indicators (OBI, near-book depth) are measuring something persistent or something that changes faster than the diagnostic's snapshot cadence.
What data would be needed: Same as above — continuous or repeated book snapshots for the same market.
Date raised: 2026-07-05

---

Question: How often do best bid/ask levels change within a short window?
Why it matters: Establishes a baseline for how "fresh" a single snapshot actually is, which matters for interpreting any point-in-time indicator.
What data would be needed: Same as above.
Date raised: 2026-07-05

---

Question: How quickly do pricing opportunities decay once they appear?
Why it matters: Relevant background context if any future indicator identifies a market as unusually mispriced — decay speed would inform whether that's a durable finding or a fleeting artifact.
What data would be needed: Same as above.
Date raised: 2026-07-05

---

Question: What observation cadence would be required to study any of the above?
Why it matters: Determines whether this domain is even practically researchable with the current single-daily-snapshot architecture, or whether it requires new infrastructure (e.g. Price History Tracking, already in zROADMAP.md's Platform Engineering Backlog).
What data would be needed: N/A — this is a feasibility question, not a data question.
Date raised: 2026-07-05

---

Question: Can execution quality be measured without placing any trades?
Why it matters: Directly tests whether this domain is compatible with Liquid Research's current read-only, no-execution constraint. If yes, this could become a legitimate research program even before any program produces a validated edge. If no, it must wait.
What data would be needed: N/A — this is a scoping question.
Date raised: 2026-07-05

---

## Combinatorial Arbitrage Pipeline — Open Questions

These questions emerged from reviewing arXiv:2508.03474's staged
filtering/reasoning/validation methodology (2026-07-05). See
research/papers.md for the paper entry and research/future_experiments.md
for the proposed Phase 0 reproduction experiment. These are open
questions only — no findings, no validated results, no promotion
to hypothesis status yet.

Question: Can we reproduce the candidate funnel from arXiv:2508.03474 on current Polymarket data?
Why it matters: The paper's methodology is only useful to Liquid Research if it actually reproduces on real, current market data — not just on the paper's own dataset.
What data would be needed: A snapshot of active Polymarket markets with title, description, end date, outcomes, prices, liquidity, and volume — data collectors/market_collector.py already gathers most of.
Date raised: 2026-07-05

---

Question: Are same-date and same-topic filters sufficient to reduce search without killing too many real opportunities?
Why it matters: Overly aggressive filtering could discard genuinely related market pairs; overly loose filtering defeats the purpose of search-space reduction.
What data would be needed: A test set of manually-identified related market pairs to check whether the filters correctly retain them.
Date raised: 2026-07-05

---

Question: Is "top 4 outcomes + Other" a robust compression rule across sports, politics, crypto, culture, and weather?
Why it matters: The paper's claim that top-4-by-liquidity captures 90%+ of relevant signal may not hold uniformly across every category Liquid Research already tracks.
What data would be needed: Outcome-level liquidity distributions across markets in each existing category (Sports, Geopolitical, Political, Macro/Economic, Crypto Long-Duration).
Date raised: 2026-07-05

---

Question: Which model is best for dependency mapping: Claude, GPT, DeepSeek, embeddings + rules, or a SAT/constraint solver?
Why it matters: The paper uses an LLM for one narrow logical-mapping task; whether that's the right tool (versus a pure rules/solver approach) affects both cost and reliability.
What data would be needed: A small labeled test set of market pairs with known logical relationships, to compare candidate approaches against.
Date raised: 2026-07-05

---

Question: Can LLM dependency outputs be converted into deterministic logical constraints?
Why it matters: Directly relevant to whether the deterministic-validation-of-LLM-output pattern from the Reduce -> Reason -> Validate principle (see zHANDOFF.md) actually holds up when implemented against real LLM outputs.
What data would be needed: Real LLM outputs from a small pilot run, checked against manually-verified expected logical relationships.
Date raised: 2026-07-05

---

Question: What is the false-positive rate after JSON validation, one-true-per-market validation, and manual review?
Why it matters: The paper's own funnel suggests the vast majority of candidates get rejected at each stage; confirming this holds on Liquid Research's own data is necessary before treating the pipeline as reliable.
What data would be needed: Output logs from a full pilot run of the pipeline against real data.
Date raised: 2026-07-05

---

Question: How often do theoretical gaps survive after maker/taker fees, spreads, depth, and partial-fill risk?
Why it matters: This is the execution-quality question applied specifically to arbitrage gaps — theoretical mispricing is not the same as executable profit. Directly related to the Future Research Domain — Execution Quality section above.
What data would be needed: Real fee schedules, order book depth, and historical fill data — none of which are needed for Phase 0 reproduction, only for any later execution-analysis phase.
Date raised: 2026-07-05

---

Question: Is maker-only execution practical, or does queue priority make most opportunities unfillable?
Why it matters: Determines whether any detected gap is realistically capturable at all, independent of whether the gap is correctly identified.
What data would be needed: Order book queue position data over time — not currently collected by any existing Liquid Research component.
Date raised: 2026-07-05

---

Question: Can we measure queue position and fill probability from the CLOB/order book?
Why it matters: A prerequisite for the execution-risk questions above; determines whether this line of research is even feasible with data Liquid Research can access.
What data would be needed: Repeated, time-stamped order book snapshots for the same market — the same continuous-observation capability flagged as missing in the Execution Quality section above.
Date raised: 2026-07-05

---

Question: Does the neural-network detector from arXiv:2306.16422 apply to prediction-market structures, or is it only useful as conceptual support?
Why it matters: Determines whether that paper deserves any further attention beyond background context.
What data would be needed: N/A at this stage — this is a scoping question, not yet worth a real test given the paper's low current relevance (see research/papers.md).
Date raised: 2026-07-05

---

Question: Is combinatorial arbitrage sufficiently common on modern Polymarket to justify becoming an ongoing research program?
Why it matters: Even if the methodology reproduces successfully (Phase 0), it may not deserve continued investment if genuine logically-dependent market pairs are too infrequent to materially improve expected returns. This is arguably the highest-leverage question in this section — it determines whether success at Phase 0 is worth acting on at all.
What data would be needed: Frequency counts from a real Phase 0 run — how many candidate pairs survive filtering, how many show genuine logical dependency, over a meaningful observation window (not a single snapshot).
Date raised: 2026-07-05
---

Question: When multiple markets represent one underlying real-world event, how should trade count, win rate, and P&L be interpreted?
Why it matters: Program A's reported statistics currently treat every closed trade as independent. If a cluster of correlated trades resolves together, one real-world event could disproportionately swing headline win rate and P&L, distorting confidence in Program A's own performance.
Current evidence: On 2026-07-27, six distinct "Will LeBron James play for [team]" markets resolved simultaneously on one real event (4 wins, 2 losses). No measured distortion has been quantified — this is an observed motivating example, not a confirmed finding.
Potential test: Investigate whether Polymarket exposes neg-risk/market-family grouping via API metadata (preferred) versus relying on unreliable text pattern-matching on question strings; if detectable, compute event-family-adjusted statistics alongside raw statistics for comparison.
Status: Open
Date raised: 2026-07-31

---

Question: Does each Program A paper trade preserve enough immutable decision-time data to reconstruct exactly what was known and used when the trade was created?
Why it matters: If trade creation does not persist a snapshot of the data actually used, a later audit or resolution step could inadvertently read different, newer data than what genuinely informed the original decision.
Current evidence: None gathered yet — this requires reading paper_trader.py's actual implementation, not assumption.
Potential test: Trace what paper_trader.py persists per trade versus what it reads at creation time; confirm whether any field could differ if re-read later from a "latest" file.
Status: Open
Date raised: 2026-07-31

---

Question: Can a market outcome recorded as resolved later be disputed or changed, and if so, how does the current resolver behave?
Why it matters: Prediction-market resolutions may involve dispute or finality stages; whether and how current Polymarket resolutions can change after first appearing resolved has not yet been verified for LRS. If they can, a resolver that reads "resolved" once and locks in the outcome could be capturing a value that later changes, silently corrupting historical trade records.
Current evidence: None gathered yet.
Potential test: Research Polymarket's actual resolution/finality mechanics from primary documentation, then trace whether paper_resolver.py re-checks resolved markets or treats resolution as permanent on first read.
Status: Open
Date raised: 2026-07-31

---

Question: Are paired total-book OBI and near-book observations in Program B genuinely contemporaneous enough to represent the same market state?
Why it matters: If the two measurements are captured via separate API calls at meaningfully different real moments, a comparison between them could reflect timing skew rather than a genuine relationship between the two indicators.
Current evidence: None gathered yet.
Potential test: Measure the actual real-time gap between total-book and near-book capture for a sample of comparable pairs in the agreement matrix.
Status: Open
Date raised: 2026-07-31

---

Question: Can LRS reconstruct the exact data state available at a past decision time, rather than only reading current or mutable "latest" files?
Why it matters: Point-in-time reconstruction capability is a prerequisite for confidently auditing any past decision after the fact; without it, later audits risk unknowingly substituting current data for what was actually available historically.
Current evidence: Believed no such capability currently exists, but this has not been confirmed as either a real gap or a real requirement.
Potential test: Attempt to reconstruct what canonical output existed at a specific arbitrary past timestamp using only currently-retained data/logs, and see whether this is actually possible.
Status: Open
Date raised: 2026-07-31

---

Question: Does Program B add information beyond Program A's existing liquidity, spread, category, and tradeability data, and what evidence would justify integration rather than continued independence?
Why it matters: This is the central question determining whether Program A and Program B should ever be combined. Program B has found persistent, market-specific stability/instability patterns, but has not tested whether these are explainable by metadata Program A already has access to.
Current evidence: No liquidity/spread/category correlation analysis has been run against Program B's stability classifications.
Potential test: Correlate each market's Program B same-sign/sign-flip ratio against its liquidity, spread, and category fields.
Status: Open
Date raised: 2026-07-31

---

Question: Which timestamps does LRS actually need to distinguish among event time, observation, receipt, processing, publication, decision, execution, and resolution?
Why it matters: A single "when was this known" timestamp may be too simple for an asynchronous, multi-machine system (Pi collector, Mac-side scanner/orchestrator, external APIs); collapsing distinct stages into one timestamp could hide real gaps between when data was captured, processed, published, and acted on.
Current evidence: LRS currently records several timestamps and publication identifiers, but no audit has yet established which stages are represented distinctly, which are inferred, and which are collapsed together.
Potential test: Trace one real trade or one real Program B comparison end-to-end and identify which of these stages are currently distinguishable in the data versus collapsed together.
Status: Open
Date raised: 2026-07-31
