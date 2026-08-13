# Research Papers & Articles

## Template

Title:
Author/Source:
Link:
Key claim(s):
Relevance to Liquid Research:
Confidence in claim: Low / Medium / High
Status: Unreviewed / Reviewing / Rejected / Archived / Experiment / Promoted

## Current Entries

---

Title: Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets
Author/Source: arXiv:2508.03474
Link: https://arxiv.org/abs/2508.03474
Key claim(s): Combinatorial arbitrage across logically related prediction markets is detectable via a staged reduction pipeline: filter candidate market pairs by resolution date and topic, reduce via semantic/embedding similarity, compress large multi-outcome markets to top-4-by-liquidity plus an "Other" catch-all, use an LLM strictly for mapping logical dependencies between reduced outcome sets (not for arithmetic, validation, or trading decisions), deterministically validate LLM output (JSON well-formed, exactly one true outcome per market, no duplicate/impossible/exhaustive-dump combinations), then compare prices only across validated logically-equivalent outcome subsets. The paper's own example dataset illustrates that the overwhelming majority of candidate pairs are expected to be rejected across successive filtering stages — the specific counts are dataset-specific and not recorded here, but the rejection-heavy funnel shape is the durable, generalizable lesson.
Relevance to Liquid Research: The staged-reduction methodology (deterministic filtering before any LLM reasoning, deterministic validation of LLM output before trusting it) is a reusable engineering pattern independent of whether combinatorial arbitrage itself becomes a Liquid Research program. The specific pipeline is architecturally distinct from the already-rejected "Mispricing scanner" experiment in future_experiments.md, since it operates entirely on Polymarket's own existing market data (titles, outcomes, prices) rather than requiring external per-category forecasting data.
Confidence in claim: Medium. The paper is real, citable, and academically structured, but Liquid Research's own evidence standard (verify, reproduce, measure) applies regardless of a source's credibility — confidence increases only after independent reproduction inside Liquid Research (see research/future_experiments.md, Methodology Reproduction — Combinatorial Arbitrage Pipeline). Any performance or profitability numbers associated with this paper via secondary sources (Twitter/X threads) are NOT independently verified and are explicitly excluded from this entry's confidence rating.
Status: Unreviewed — see research/future_experiments.md "Methodology Reproduction — Combinatorial Arbitrage Pipeline (Phase 0)" for the proposed first test of this methodology against real Liquid Research data.

---

Title: Neural Networks Can Detect Model-Free Static Arbitrage Strategies
Author/Source: arXiv:2306.16422
Link: https://arxiv.org/abs/2306.16422
Key claim(s): Neural networks can be trained to detect static arbitrage opportunities without an explicit pricing model, by learning directly from market data patterns.
Relevance to Liquid Research: Conceptual support only. This paper's domain (financial options/derivatives markets) and method (trained neural network detector) do not directly map onto Liquid Research's current architecture or the combinatorial arbitrage pipeline above, which uses rule-based deterministic filtering plus narrow LLM reasoning, not a trained detection model. Referenced only as background context that model-free arbitrage detection is an established research area, not as a technique to implement.
Confidence in claim: Low relevance to current Liquid Research work. Not proposed for reproduction or implementation.
Status: Archived — background reference only, no planned follow-up.