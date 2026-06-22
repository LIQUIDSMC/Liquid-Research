# Engineering Observations

A neutral holding area for implementation ideas, patterns, and
observations extracted from external material — repos, articles,
papers — that are NOT yet hypotheses, NOT findings, and NOT
accepted conclusions.

## What This File Is NOT

- NOT evidence (see validated_findings.md for that)
- NOT a testable hypothesis (see market_hypotheses.md for that)
- NOT a reviewed-and-set-aside idea (see archived_ideas.md/dead_ends.md for that)
- NOT tied to evaluating one specific source's credibility (see
  twitter_leads.md/github_repositories.md/papers.md for that)

This file exists so a potentially useful engineering pattern is
not permanently lost just because the source it came from also
contained unverified marketing claims. The pattern and the claim
are different things and are evaluated separately.

## Template

Observation:
Source context: (what external material this was extracted from, without treating that material as evidence)
Status: Unreviewed / Reviewing / Rejected / Promoted to hypothesis or experiment

## Current Entries

Observation: Arbitrage-style opportunity windows may be short-lived, requiring frequent polling to detect before they close.
Source context: Extracted from an external marketing-oriented article discussing prediction-market arbitrage bots. The article's own profitability claims are explicitly excluded.
Status: Unreviewed

---

Observation: Stability of a detection or monitoring system should be prioritized before optimization.
Source context: Same source as above.
Status: Unreviewed

---

Observation: High-liquidity markets may be more worth prioritizing than low-liquidity ones for monitoring/detection purposes.
Source context: Same source as above. Note: directionally consistent with Liquid Research's own existing kill-filter logic in market_collector.py, which already deprioritizes low-volume markets — this is not a new idea for this project, just a confirmation from an external source.
Status: Unreviewed

---

Observation: Liquidity concentration (how liquidity is distributed across markets) may matter more than total market count when deciding where to focus monitoring effort.
Source context: Same source as above.
Status: Unreviewed

---

Observation: Asynchronous architectures (e.g. Python asyncio) may be beneficial for systems that need to monitor many markets concurrently.
Source context: Same source as above.
Status: Unreviewed

---

Observation: Semantic similarity techniques (e.g. embedding-based comparison of market descriptions) may be useful for clustering markets that describe the same underlying real-world event but are worded differently.
Source context: Same source as above. Note: this is conceptually related to the verified cross-venue spread hypothesis already in market_hypotheses.md (Gebele & Matthes, 2026), which addresses the same underlying problem (semantic non-fungibility) using a real academic approach. This entry is the implementation-pattern version of that idea, not a duplicate of the hypothesis itself.
Status: Unreviewed

---

Observation: Integer programming may be useful for checking internal consistency of related market prices (e.g. whether a set of related outcome prices reconcile correctly).
Source context: Same source as above.
Status: Unreviewed

---

Observation: Machine learning classification approaches may be useful for anomaly/opportunity detection in market price data.
Source context: Same source as above.
Status: Unreviewed

---

Observation: "Small edge, high frequency" is a commonly repeated framing in market-inefficiency-focused systems, as an alternative to seeking large edges on individual trades.
Source context: Same source as above.
Status: Unreviewed
