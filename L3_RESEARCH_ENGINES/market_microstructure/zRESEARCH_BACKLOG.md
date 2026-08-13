# Program B Research Backlog

**Canonical question this document answers:**
What evidence does Program B still need before it can responsibly become a filter for Program A?

**Source:** Built directly from the "Next evidence needed" sections of Program B's completed research checkpoints (see `research/validated_findings.md` and `programs/program_b/zPROGRAM_ROADMAP.md`). No new research directions are introduced here — every item below traces to language already recorded in a checkpoint. Audited against all eight completed checkpoints as of 2026-07-30.

**How to use this during short review sessions:** Each item is self-contained. A 10-15 minute session can review one item's "Current evidence" and "Evidence still missing," check whether new checkpoint data resolves it, and update its status — without needing to re-read every prior checkpoint.

**Research philosophy:** This backlog is intentionally evidence-driven rather than feature-driven. An item remains open until sufficient evidence exists to answer it responsibly. New ideas should not be added merely because they are interesting; they should originate from unresolved findings documented in completed research checkpoints. This is a research backlog, not a feature backlog — it asks "what do we still not know?" rather than "what should we build next?"

---

## 1. Chronological ordering of observations

**Hypothesis:** Can Program B reliably determine the true time-order of observations across markets, given that `publication_id` values are lexically sorted rather than parsed as real timestamps?

**Why it matters:** Nearly every checkpoint's market-level narrative (streaks, reversals, "newest observation," oscillation patterns) implicitly depends on knowing which observation came before which. If the lexical sort doesn't reliably reflect true chronological order — especially given the mix of `YYYYMMDD_HHMMSS`-style identifiers and legacy `snapshot_*.csv` identifiers — then any claim about a market's *sequence* of behavior (not just its aggregate same-sign/flip counts) is unverified. This is a foundational data-quality question, not a cosmetic one: it affects the credibility of every "market X shifted from stable to unstable" claim Program B has made or will make.

**Current evidence:** A manual chronological-reading discipline (using dates embedded in each identifier, rather than table row order) was established at the third checkpoint for human review of results. The specific data-quality limitation in the automated pipeline itself — that `build_agreement_matrix()`'s lexical sort on `publication_id` does not reliably reflect true chronological order — was first identified at the *fifth* checkpoint, and re-confirmed at the sixth, seventh, and eighth. Checkpoint 7 explicitly downgraded language like "newest observation" to "a later observed record" specifically because this was unresolved. No parsing or validation of true chronological order has been performed in the automated pipeline at any checkpoint — every sequence-based claim to date rests on lexical sort order only.

**Evidence still missing:** A canonical `observed_at_utc` field (or equivalent) populated from real collection timestamps, plus a verification pass confirming that lexical `publication_id` order matches this canonical field across the full mixed-format history.

**Priority:** High. This is a prerequisite for trusting *any* sequence-dependent claim Program B makes, which includes most of its most interesting findings (streaks, reversals, persistence).

**Possible future work:** Add `observed_at_utc` to the OBI/near-book logging pipeline going forward (does not require reprocessing historical data, only prevents the problem from growing). Historical data would remain subject to the lexical-sort caveat unless a separate, careful reconstruction effort is undertaken.

---

## 2. Whether market-level stability/instability is explained by liquidity, spread, or category

**Hypothesis:** Do observable market characteristics (liquidity, spread, category, or similar metadata) explain why some markets are persistently stable (e.g., Hormuz-related markets, US Invade Iran) while others are persistently unstable (e.g., Fed Increase, the LeBron team markets)?

**Why it matters:** This is the single most direct prerequisite for Program A+B integration. If persistent stability/instability is explainable by metadata Program A already has access to (liquidity, spread, category), then Program B's signal could potentially be approximated or even subsumed by simpler, already-available filters — or conversely, if it is *not* explainable by existing metadata, that would be real evidence Program B is capturing something genuinely new. Either answer is valuable; the absence of an answer means integration would be speculative.

**Current evidence:** First raised as an open question at the very first checkpoint (2026-07-10) and repeated at every checkpoint since, without ever being tested. Every checkpoint from the sixth onward has explicitly named this as untested. Real, accumulating examples exist to test against: persistently stable markets (Hormuz July 31 and August 31 — though these two are correlated, sharing one underlying event; US Invade Iran; Putin Out; Iranian Regime Fall) and persistently unstable markets (Fed Increase; Fed No-Change, though its ratio has shifted across checkpoints; the LeBron team markets). No liquidity, spread, or category correlation analysis has been run against this classification.

**Evidence still missing:** A direct analysis correlating each market's same-sign/sign-flip ratio against its liquidity, spread, and category fields (already present in the canonical output schema). This does not require new data collection — it requires a new analysis script applied to data Program B already has.

**Priority:** High. This is the most direct, already-answerable question standing between "Program B has found interesting patterns" and "Program B can inform Program A's market selection."

**Possible future work:** If a real correlation is found, that becomes the first candidate rule for an A+B filter (e.g., "prefer markets with liquidity above $X" or "deprioritize markets in category Y"). If no correlation is found, that is equally important evidence — it would suggest the stability/instability pattern is genuinely idiosyncratic per-market rather than explainable by simple metadata, which changes what kind of filter (if any) would be defensible.

---

## 3. Whether the aggregate same-sign/sign-flip ratio is trending, plateauing, or noise

**Hypothesis:** Is the dataset-wide same-sign percentage (currently oscillating in the mid-50s%) moving toward a stable long-run value, or is checkpoint-to-checkpoint movement within the range of ordinary sampling variation?

**Why it matters:** This affects how much weight to put on the *aggregate* statistic versus the *market-level* classification (see item 2) when eventually designing a filter. If the aggregate is genuinely stabilizing, that's a meaningful structural fact about the OBI/near-book relationship in general. If it's just noise around new-market accumulation, the aggregate number is not a reliable planning input and market-level classification should be weighted more heavily.

**Current evidence:** The aggregate has moved modestly at each checkpoint from the sixth onward — down slightly at checkpoint 7, back up slightly at checkpoint 8 — always characterized as small relative to simultaneous dataset growth, and explicitly not yet treated as a directional trend at any checkpoint.

**Evidence still missing:** Several more checkpoints' worth of aggregate readings, ideally with dataset growth rate slowing (so that a real trend, if present, would become more visible against a more stable denominator) rather than continuing to roughly double in size each time.

**Priority:** Medium. Useful context, but item 2 (market-level explanation) is likely to be more directly actionable for A+B integration than resolving whether the aggregate itself trends.

**Possible future work:** None beyond continued checkpoint accumulation — this is a "wait and observe" item, not one requiring new analysis code.

---

## 4. Whether individual "developing" market patterns are real regime changes or noise

**Hypothesis:** Several specific markets have shown a single new data point that could represent a genuine change in character: US Invade Iran's sign-flip after a run of same-sign observations (checkpoint 7); Fed No-Change's shift back toward majority-agreement at n=25 (checkpoint 8, a reversal from its near-even split at n=22). Are these genuine regime changes, or single-observation noise within markets that have shown oscillation before? Separately, checkpoint 5 raised a specific, still-untested angle on Fed No-Change: does its oscillation correlate with an external event or schedule (for example, FOMC meeting dates), rather than being unstructured noise?

**Why it matters:** Program B's own prior evidence (explicitly noted at the fourth and fifth checkpoints regarding Fed No-Change) already demonstrated that this specific market can revert after a same-sign or sign-flip run, rather than settle into a new stable regime. This is a real, demonstrated risk of over-interpreting single new observations. Getting this right matters directly for item 2 — a market misclassified as "newly stable" or "newly unstable" would corrupt any liquidity/spread/category correlation analysis built on top of it.

**Current evidence:** Both specific instances are recorded with explicit caution against over-interpretation in their respective checkpoints. Fed No-Change in particular has a documented history of oscillating rather than resolving (noted across the fourth, fifth, seventh, and eighth checkpoints).

**Evidence still missing:** Continued observations of these two specific markets at the next checkpoint(s) to see whether the new pattern holds or reverts again.

**Priority:** Medium. Directly feeds into item 2's reliability, but is naturally resolved by continued normal checkpoint accumulation rather than requiring separate investigation.

**Possible future work:** None beyond continued observation for the US Invade Iran and Fed No-Change regime-change question — no new code or analysis required. The FOMC-schedule correlation angle raised at checkpoint 5 would require pulling real FOMC meeting dates and checking Fed No-Change's sign-flip timing against them — a small, self-contained analysis that logically follows from checkpoint 5's own text, not an invented direction.

---

## 5. Whether shallow-sample "perfect record" markets hold at depth

**Hypothesis:** The LeBron-76ers market showed a perfect same-sign/sign-flip split at both n=6 and n=7 (checkpoints 6 and 7). Does this hold as it reaches genuine depth (n≥15), or does it revert the way other shallow perfect records have in this project's history?

**Why it matters:** This project has explicit prior evidence (cited at the sixth checkpoint) that a perfect record at n=6 has previously failed to predict behavior at greater depth (the original Fed no-change market's early history was cited as the precedent). This is a direct, self-referential caution Program B has already built into its own methodology — testing it on a live case is a natural, low-cost way to either reinforce or weaken that internal caution.

**Current evidence:** Held at n=6 and n=7 (0 same-sign, all sign-flip both times) as of the seventh checkpoint. Explicitly still classified as a shallow sample, not yet a conclusion.

**Evidence still missing:** Continued observations as this market's `n` grows toward 15, to see whether the perfect record holds, weakens, or reverses.

**Priority:** Low. Genuinely interesting as a test of the project's own shallow-sample caution, but does not block A+B integration work the way items 1 and 2 do — this is a single market, not a structural question.

**Possible future work:** None beyond continued observation.

---

## Summary Table

| # | Item | Priority | Status |
|---|---|---|---|
| 1 | Chronological ordering / `observed_at_utc` | High | Open since checkpoint 5 (manual discipline established at checkpoint 3), unresolved |
| 2 | Liquidity/spread/category explaining stability | High | Open since checkpoint 1, unresolved, directly actionable now |
| 3 | Aggregate trend vs. noise | Medium | Open since checkpoint 6, needs more checkpoints |
| 4 | Specific developing patterns (US Invade Iran, Fed No-Change, FOMC schedule) | Medium | Open since checkpoints 5, 7-8, needs 1-2 more checkpoints |
| 5 | LeBron-76ers shallow record at depth | Low | Open since checkpoint 6, needs more depth |

**For A+B integration specifically:** Items 1 and 2 are the highest-priority unresolved questions for evaluating future Program A + Program B integration. Item 1 is a data-quality prerequisite; item 2 is the direct, already-answerable question about whether Program B's findings are explainable by simpler existing data. Neither has been established as a hard blocker — exploratory, explicitly-labeled A+B prototyping could still proceed in parallel — but both will most directly determine whether integration is justified and how much confidence to place in it. Items 3-5 are useful, ongoing context that will keep refining naturally through continued daily cycles, without requiring dedicated investigation sessions.
