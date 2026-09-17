# Post-Actionability Δ-Latency Sensitivity Study

## Purpose

Given the validated causal actionability frontier (F_position → E_position →
A_position → NEW entry proxy, closed in the causal-frontier generalization
investigation), this study asks a narrower question:

> Given our validated causal signal frontier, how sensitive is the observable
> entry-price proxy to an additional hypothetical 0–2,000 ms of
> post-actionability latency?

This is deliberately scoped as **entry-price observation only** — it does not
model order execution, fills, slippage, fees, position sizing, or
profitability. It answers whether precise execution-latency characterization
is currently a priority blocker before that infrastructure is built.

## Methodology

Reuses the exact audited reconstruction/dedup/K5/F-R-A machinery from the
closed causal-frontier generalization investigation
(causal_frontier_generalization.py, not modified). Extended chronology
coverage per population is computed as max(A_receipt) + Δ_max(2000ms) +
60000ms safety margin, rather than a fixed horizon, since the required
discovery window depends on the largest tested Δ.

### Δ entry rule

```
Δ=0 (locked validated NEW rule, no receipt-time condition):
    pos = A_position + 1
    first physical arrival satisfying: trade_time > A_receipt

Δ>0:
    D_delta = A_receipt + Δ
    starting strictly after A_position, first physical arrival satisfying BOTH:
        timestamp_received >= D_delta
        trade_time > D_delta
```

The asymmetry between Δ=0 and Δ>0 is intentional: Δ=0 reproduces the
already-audited rule exactly; Δ>0 additionally requires the candidate arrival
to not have physically arrived before the simulated delay elapsed
(timestamp_received >= D_delta), preventing causal leakage where a trade
that arrived early is mistaken for one observable only after a longer delay.

### Populations (4)

| Instrument | Date | Samples | N10 Eligible |
|---|---|---|---|
| BTC-USD | 2026-08-05 | 24,151 | ✅ |
| BTC-USD | 2026-08-22 | 95,477 | ✅ |
| ETH-USD | 2026-08-27 | 16,349 | ✅ |
| BTC-USD | 2026-09-03 | 32,211 | ❌ N10-ineligible |

Total: 168,188 structural entry observations across all four populations.

BTC-USD 2026-09-03 fails the frozen N10 reference-date audit (2026-08-31,
2026-09-01, 2026-09-02 did not pass reconstruction audit) — no
skipping/backfill under the frozen rule. It remains in structural/entry
diagnostics but is explicitly excluded from all direction-adjusted
adverse-move statistics and aggregates.

### Causal N10 thresholds (independently reconstructed)

| Population | P10 | P90 | Historical Obs |
|---|---|---|---|
| BTC Aug05 | -0.9124993108067109 | 0.995520576372723 | 233,713 |
| BTC Aug22 | -0.8916056119723363 | 0.9638883167380699 | 342,125 |
| ETH Aug27 | -0.8260489240979522 | 0.9047507863169619 | 211,336 |

Classification: imbalance <= P10 → SHORT, imbalance > P90 → LONG,
otherwise NONE.

### Direction-adjusted adverse entry move

```
LONG:  (P_delta / P_0 - 1) * 10,000
SHORT: (P_0 / P_delta - 1) * 10,000
```

Positive = delayed entry is worse. Computed only where both the Δ=0 and Δ>0
entry are observable for a given sample; unavailable pairs are explicitly
counted (signal_unavailable_pair_n), never assigned a synthetic value.

## Results

Across 25,357 N10-eligible LONG/SHORT signals (9,411 LONG, 15,946 SHORT;
21,284 BTC, 4,073 ETH), **every Δ entry was observable — 0 unavailable pairs
at any Δ, across all populations.**

| Δ | Median | P90 | P95 | P99 | >1bp | >2bp | >5bp |
|---|---:|---:|---:|---:|---:|---:|---:|
| 150ms | 0.000 | 0.001 | 0.240 | 1.087 | 1.11% | 0.26% | 0.06% |
| 250ms | 0.000 | 0.122 | 0.491 | 1.466 | 1.90% | 0.52% | 0.08% |
| 500ms | 0.000 | 0.367 | 0.786 | 1.974 | 3.53% | 0.90% | 0.11% |
| 1000ms | 0.000 | 0.660 | 1.158 | 2.417 | 5.99% | 1.52% | 0.18% |
| 2000ms | 0.000 | 1.052 | 1.598 | 3.277 | 10.51% | 3.15% | 0.38% |

(bp = basis points, adverse move)

**ETH shows greater tail sensitivity than BTC despite its smaller sample.**
At 250ms, ETH p99 is 2.888bp vs BTC 1.251bp; at 2000ms, ETH p99 reaches
5.558bp vs BTC 2.950bp. Instrument-specific execution assumptions should be
preserved rather than treating BTC and ETH as interchangeable in later
execution-model work.

## Conclusion

Precise post-actionability execution latency in the ~150–250ms range is not
currently the dominant historical entry-price sensitivity blocker: 90% of
signals show ≤0.122bp degradation at 250ms, with tail degradation present at
150–250ms but becoming progressively more pronounced at 500ms+. Degradation
increases progressively and predictably through 2,000ms, with no
discontinuity suggesting a hidden structural threshold in this range.

**This supports proceeding without a precise production execution-latency
constant for now**, while flagging that instrument-specific (BTC vs ETH)
and tail-risk (P99+) behavior should inform later fee/slippage/execution
model design.

## Scope and Limitations

This study establishes **historical entry-price observability**, not
executable trading outcomes. It does NOT establish:
- Order acceptance latency, authenticated API round-trip time, or fill
  confirmation latency (Coinbase Advanced Trade has no sandbox; these remain
  unmeasured — see prior Coinbase execution-infrastructure inventory)
- Slippage, spread-crossing cost, or fees
- Fill probability or partial-fill behavior
- Position sizing, exit rules, or P&L
- Profitability of any kind

The 150/250ms test points were informed by measured Pi→Coinbase public REST
RTT (median ≈135ms, p95 ≈150ms, p99 ≈253ms), but are not themselves
measurements of order/fill latency — a fundamentally different code path
requiring authenticated, order-creating requests that cannot be safely
probed without financial exposure (Coinbase provides no sandbox for the
Advanced Trade API).

## Artifacts

- Diagnostic: delta_sensitivity_v1.py
- Results: results/delta_sensitivity_v1/ (per-population + aggregate JSON,
  run log)
- Reused (unmodified): causal-frontier generalization methodology from the
  closed causal-frontier investigation
