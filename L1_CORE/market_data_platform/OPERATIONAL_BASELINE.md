# Market Data Platform — Operational Baseline

Recorded: 2026-07-22. Measurements taken while the collector
(PID 3059) remained continuously active — the file-count snapshot,
byte-count measurement, and system-health readings were taken in
sequence, not simultaneously; approximately 50 seconds separated
the file-count snapshot from the byte-count measurement. All rates
and projections below are estimates derived from this single
measurement window, not confirmed stable long-term rates.

## Collector — Measured Facts

- Process start: 2026-07-20 21:27:45 UTC (PID 3059)
- Measurement time (file/byte count): ~2026-07-22 05:29:37 UTC
- Elapsed runtime at measurement: 32.031 hours
- Total Parquet files (internally consistent snapshot): 196,213
  - Trade files: 9,297 (4.74%)
  - Depth-level files: 186,916 (95.26%)
  - Other: 0
- Canonical directory size (measured ~50 seconds after the file
  count above): 1,055,090,278 bytes (~1.02 GiB / ~1.06 GB)
- Collector process RSS: 138,880 KB (~135.6 MiB), 14.9% of system RAM

## Collector — Estimated Rates (single measurement window)

- ~6,126 Parquet files/hour
- ~147,024 Parquet files/24 hours
- ~31.42 MiB canonical data/hour
- ~0.736 GiB (~0.791 GB decimal) canonical data/24 hours

## Storage Projections (estimates, not confirmed long-term rates)

| Period | Projected files | Projected size (GiB) | Projected size (GB) |
|---|---|---|---|
| 7 days | ~1,029,168 | ~5.15 | ~5.53 |
| 30 days | ~4,410,720 | ~22.08 | ~23.71 |
| 90 days | ~13,232,160 | ~66.24 | ~71.13 |
| 365 days | ~53,673,760 | ~268.6 | ~288.5 |

## Filesystem Capacity (measured 2026-07-22 05:29 UTC vicinity)

- Filesystem: /dev/mmcblk0p2, 58GB total, 7.7GB used (14%), 48GB available
- This filesystem contains the full Pi OS installation and other
  files, not exclusively canonical market data — the 48GB available
  figure is not entirely attributable to future collector growth.
- Remaining headroom to 80% utilization is approximately 38.7 GB.
  Using the estimated growth rate, the filesystem would reach
  approximately 80% utilization in about 50 days. This estimate is
  approximate because filesystem capacity is reported in decimal
  units while collector growth above is expressed in binary units.
- Remaining headroom to 90% utilization is approximately 44.5 GB,
  estimated at approximately 58-60 days by the same method.

## Inode Capacity (measured 2026-07-22 05:29 UTC vicinity)

- Total inodes: 3,813,760
- Used inodes: 343,951 (10%)
- Free inodes: 3,469,809
- Estimate uses ~1 inode per Parquet file; directories and other
  files also consume inodes, so this slightly overstates true
  headroom.
- Estimated time to 80% inode utilization: ~18.4 days
- Estimated time to 90% inode utilization: ~21 days

## Capacity Conclusion

Based on this single measurement window, inode exhaustion is
estimated to arrive meaningfully sooner (~18-21 days) than byte
capacity exhaustion (~50-60 days). This should be treated as an
early, single-window estimate, not a confirmed trajectory — worth
re-measuring after several more days of real operation before
treating this gap as settled. 
Based on this measurement window, inode availability appears to be the first operational constraint to monitor. 
Additional measurements should confirm whether this relationship remains stable over time. 
Future measurements should verify whether the observed growth rate
remains stable before architectural changes are made.

## Raspberry Pi System Health (measured 2026-07-22, ~1 day 21hr uptime)

- CPU: 8.0% user, 0.0% system, 90.0% idle, 2.0% I/O wait
- Load average: 0.61, 0.40, 0.25
- RAM: 905MiB total, 92MiB free, 329MiB used, 555MiB buffer/cache, 575MiB available
- Swap: 904MiB total, 51MiB used, 853MiB free
- Temperature: 66.604°C (throttling threshold typically ~80-85°C)

## Orchestrator (Mac) — One Real Run Recorded, Average Pending

Only one real orchestrated run exists as of this writing
(2026-07-21). An average cannot yet be meaningfully calculated.

- Total runtime: 145.42s
- market_collector: 0.99s
- scanner: 55.8s
- publish_canonical_output: 0.3s
- paper_trader: 0.3s
- paper_resolver: 28.07s
- run_obi: 29.97s
- run_near_book_depth: 29.97s

## Next Investigations (not decided implementations)

- External hard drive inventory (capacity, type, interface, current
  use) to evaluate whether existing family hardware can serve as a
  storage destination.
- Re-measurement of growth rate after several more days, to confirm
  or revise the single-window estimates above.
- Research into compaction and/or alternative storage layouts for
  the depth-level dataset, which dominates total file count. No
  implementation decision has been made.
