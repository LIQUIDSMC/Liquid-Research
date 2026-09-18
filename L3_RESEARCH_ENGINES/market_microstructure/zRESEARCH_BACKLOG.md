# LRS-2 — Market Microstructure Research Backlog

**Canonical question this document answers:**
What evidence does LRS-2 still need before its microstructure findings can responsibly inform market selection or entry timing?

**Source:** This backlog originated from the "Next evidence needed" sections of completed Market Microstructure checkpoints. It is now reconciled through CP13 (2026-09-09) against `zPROGRAM_ROADMAP.md`. Historical questions remain here when they explain why an investigation was opened, even when later implementation inspection or accumulated evidence changes their status.

**How to use this during short review sessions:** Each item is self-contained. Review its current evidence and remaining evidence, determine whether a new checkpoint changes its status, and update it without treating descriptive observations as predictive results.

**Research philosophy:** This backlog is intentionally evidence-driven rather than feature-driven. It asks "what do we still not know?" rather than "what should we build next?" New work should originate from unresolved evidence or a clearly documented research gap.

---

## 1. Chronological ordering of observations

**Original question:** Can LRS-2 reliably determine the true time-order of observations across markets when historical identifiers include mixed `publication_id` formats?

**Why it mattered:** Earlier checkpoints used sequence-oriented language such as streaks, reversals, and later observations. Those interpretations require trustworthy ordering.

**Historical concern:** Earlier checkpoint reviews identified lexical `publication_id` ordering as a possible chronology risk and deliberately weakened sequence-dependent language while that concern remained unresolved.

**Current evidence:** Subsequent implementation inspection established that the statistical agreement/checkpoint pairing path in `analysis/agreement_matrix.py` is timestamp-based rather than dependent on lexical `publication_id` ordering. The previously described active `build_agreement_matrix()` chronology defect is therefore not supported by the current implementation.

A separate lexical sort involving `publication_id` remains in `analysis/market_report.py`. Existing dependency inspection has not established that ordering as part of the checkpoint statistical pairing path or as a load-bearing chronological contract. It remains tracked separately rather than being generalized into a pipeline-wide chronology defect.

**Evidence still missing:** No new canonical timestamp field is required merely to repair the already-inspected agreement-matrix path. Any future chronology change should be justified against the specific consumer and its actual ordering contract rather than by the superseded pipeline-wide concern.

**Priority:** Resolved for the current checkpoint statistical pairing path; separate `market_report.py` ordering inventory remains a minor tracked implementation question.

**Status:** Superseded as an active checkpoint-pairing defect. Historical concern preserved.

---

## 2. Whether market-level stability/instability is explained by liquidity, spread, or category

**Hypothesis:** Do observable market characteristics such as liquidity, spread, category, or similar metadata explain why some markets show persistent agreement while others show persistent disagreement?

**Why it matters:** This remains a direct question about whether LRS-2 is observing information distinct from simpler market metadata. Either outcome is useful: an explanatory relationship could simplify future integration, while failure to find one would suggest that the observed heterogeneity is not captured by those basic fields alone.

**Current evidence:** The market-level dataset has deepened substantially, but the checkpoint record through CP13 still establishes heterogeneous microstructure behavior rather than a validated liquidity/spread/category explanation.

At CP13, 21 markets had reached n>=15. Examples include US Invade Iran at 92.6% same-sign (n=54), Fed decrease 25bps for September at 25.8% (n=31), Fed increase 25bps for July at 33.3% (n=21), Putin out before 2027 at 100.0% (n=22), and Iranian regime fall before 2027 at 100.0% (n=17).

This is substantially more evidence for persistent market-level heterogeneity than existed when the backlog was created. It does not, by itself, establish what metadata explains that heterogeneity.

**Evidence still missing:** A direct, controlled analysis comparing market-level agreement behavior with the relevant liquidity, spread, category, or other available metadata. Metadata availability and semantics must be verified from the current canonical schema before assuming that every originally proposed field is present and suitable for analysis.

**Priority:** High.

**Status:** Open. Better-powered by CP13 data, but the explanatory analysis has not been established by the checkpoint record.

**Possible future work:** Verify the current canonical metadata contract first. Then test only fields that are actually available and semantically appropriate. Treat any observed association as descriptive until separately validated.

---

## 3. Whether the aggregate same-sign/sign-flip ratio is trending, plateauing, or noise

**Hypothesis:** Is the dataset-wide same-sign percentage approaching a stable long-run range, showing a directional trend, or moving within ordinary sampling variation?

**Why it matters:** This determines how much descriptive weight should be placed on the aggregate relationship versus heterogeneous market-level behavior.

**Current evidence:** This question now has substantially more checkpoint evidence than when the backlog was created.

Across checkpoints 9-11, the aggregate rate moved only modestly back and forth while the dataset continued growing. CP12 then moved to 59.26% same-sign (867/1,463), a larger change than the immediately preceding intervals. CP13 added 299 comparable pairs and moved only slightly to 58.97% (1,039/1,762).

CP13 therefore records stability of the observed aggregate rate over that specific interval. It does not establish predictive value, nor does one relatively stable interval establish a permanent long-run plateau.

**Evidence still missing:** Additional predefined checkpoints are needed to determine whether the recent aggregate range persists as the dataset grows beyond 2,000 comparable pairs and the deep-market roster continues expanding.

**Priority:** Medium.

**Status:** Open, with materially stronger evidence of interval-level aggregate stability than was available at backlog creation.

**Possible future work:** Continue checkpoint accumulation under the existing trigger discipline. No methodology change is justified by the current evidence.

---

## 4. Whether individual developing market patterns persist or revert

**Hypothesis:** Do apparently stable or unstable market-level patterns persist as individual markets deepen, or do they revert as additional observations accumulate?

**Why it matters:** Earlier checkpoints demonstrated that shallow or short-lived runs can be misleading. Market-level classifications therefore need continued evidence rather than interpretation from a single new observation.

**Current evidence:** Several examples that were shallow or developing when this backlog was created have now accumulated materially more evidence.

US Invade Iran continued strengthening through CP13 and reached 92.6% same-sign at n=54. Putin out before 2027 remained 100.0% at n=22, and Iranian regime fall before 2027 remained 100.0% at n=17.

The disagreement side is also heterogeneous. At CP13, Fed decrease 25bps for September remained at 25.8% same-sign (n=31) and Fed increase 25bps for July remained at 33.3% (n=21), while Renan Santos moved from 28.6% to 37.9% as n increased from 21 to 29. CP13 therefore explicitly records that these markets should be tracked individually rather than treated as a uniformly moving disagreement cluster.

The earlier Fed No-Change oscillation question remains useful historical evidence against over-interpreting short runs, but later checkpoints have produced a broader and deeper set of market-level examples.

**Evidence still missing:** Continued observations of deep markets are required to determine which apparent regimes persist, plateau, or reverse. External-event explanations such as the historically proposed FOMC-schedule relationship remain separate hypotheses and have not been established by the checkpoint evidence summarized here.

**Priority:** Medium.

**Status:** Open as a general persistence question; several originally shallow examples have materially matured.

**Possible future work:** Continue individual-market tracking at predefined checkpoints. Test an external-event hypothesis only as a separately defined analysis rather than assuming event causation from timing alone.

---

## 5. Whether shallow-sample perfect records hold at depth

**Hypothesis:** Do apparently perfect agreement or disagreement records observed at shallow sample sizes survive as markets reach meaningful depth?

**Why it matters:** The project has prior evidence that shallow perfect records can fail as observations accumulate. This remains an important guardrail against promoting small-n behavior into a conclusion.

**Current evidence:** The original backlog example, LeBron-76ers, was still only n=7 at the seventh checkpoint. The CP13 evidence now provides stronger examples of the underlying question: Putin out before 2027 remained 100.0% same-sign at n=22, and Iranian regime fall before 2027 remained 100.0% at n=17.

These deeper perfect records are materially stronger descriptive evidence than a perfect record at n=6 or n=7. They still do not establish predictive value or guarantee persistence.

**Evidence still missing:** Continued observations as currently perfect deep markets accumulate additional samples. Any future perfect shallow market should remain provisional until it reaches meaningful depth.

**Priority:** Low.

**Status:** Open as a methodological guardrail; the evidence base has materially matured since the original LeBron example.

**Possible future work:** None beyond continued checkpoint observation unless a separate hypothesis specifically requires analysis.

---

## Summary Table

| # | Item | Priority | Status |
|---|---|---|---|
| 1 | Chronological ordering / checkpoint pairing | Resolved for current statistical path | Superseded as active agreement-matrix defect; separate `market_report.py` ordering question remains tracked |
| 2 | Liquidity/spread/category explaining heterogeneity | High | Open; explanatory analysis not established |
| 3 | Aggregate trend vs. plateau/noise | Medium | Open; CP13 adds interval-level stability evidence |
| 4 | Individual market persistence/reversion | Medium | Open; several formerly developing examples now materially deeper |
| 5 | Shallow perfect records at depth | Low | Open methodological guardrail; deeper perfect examples now exist |

**For future integration:** Item 2 is the principal unresolved explanatory question in this backlog for determining whether LRS-2's market-level heterogeneity adds information beyond simpler available metadata. Item 1 is no longer treated as a current statistical-pairing blocker based on the inspected implementation. Items 3-5 remain research context that should continue to mature through predefined checkpoint collection rather than being forced into premature conclusions.

No backlog item by itself authorizes LRS-2 to become a production market-selection or entry-timing filter. Integration requires separate evidence that the relevant microstructure information improves an actual decision.
