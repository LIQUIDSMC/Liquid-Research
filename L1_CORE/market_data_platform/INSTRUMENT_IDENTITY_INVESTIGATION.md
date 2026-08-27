# INSTRUMENT_ID INCIDENT / REMEDIATION RECORD

## 1. Executive Summary

The Market Data Platform's canonical `TradeRecord` and `DepthLevelRecord` schemas did not preserve instrument identity (which real-world product — BTC-USD or ETH-USD — a given trade or depth-level update belonged to), despite the live collector subscribing to both products simultaneously on both its Coinbase and Binance adapters. This was discovered during an unrelated crypto-data audit. A forward-looking code fix was designed, implemented, and deployed to the Pi's live collector. Post-deployment production validation across 223,828,418 real rows found zero identity defects.

## 2. Problem / Failure Mode

Real Coinbase WebSocket messages include per-trade `product_id` (confirmed via a live-captured example embedded in the adapter's own smoke test) and per-event `product_id` (confirmed via both Coinbase's official documentation example and a live probe of the real WebSocket connection). Real Binance messages include a per-message `"s"` symbol field (confirmed via the adapter's own documented smoke-test examples, sourced from Binance's official WebSocket documentation). Neither adapter's parsing functions read these fields. Neither `TradeRecord` nor `DepthLevelRecord` had a field to hold instrument identity. As a result, every historical trade and depth-level record persisted to Parquet carried no record-level indication of which product it described.

## 3. Scope and Impact

Affected: all historical data collected by the Market Data Platform's Coinbase adapter for BTC-USD and ETH-USD, from the start of collection through the fix's deployment. Binance adapter: same structural defect confirmed in code, though the Binance adapter's real-world collection history/usage was not established in this investigation and should be marked **unresolved** rather than assumed.

## 4. Root Cause

The canonical schema (`schema.py`) originated, per its own module docstring, as a Binance-specific Phase 0 design, with cross-source generalization explicitly deferred to a future phase. The schema was never given a product/instrument identifier field. When a Coinbase adapter was later built against this same schema, and when the live collector was configured to subscribe to two products (BTC-USD and ETH-USD) simultaneously, no adjustment was made to accommodate multi-instrument identity within a single collection stream. Real product identity was available in both venues' raw messages at every point in the pipeline where it was checked, but was never extracted or persisted.

## 5. Forward Remediation

Added `instrument_id: Optional[str]` (no default) to both `TradeRecord` and `DepthLevelRecord`. Added `("instrument_id", pa.string())` to both PyArrow schemas in `storage.py`. Both writer functions now include `instrument_id` in their persisted row data. Both reader functions use `.get("instrument_id")` so that reading old, pre-fix files (which lack the column) returns `None` rather than raising an error. Both the Coinbase and Binance adapters now extract the real, per-message/per-event product identity and raise `ValueError` immediately if it is missing or empty, before any record is constructed — preventing any new record from silently being written without identity again.

## 6. Files Changed

Confirmed via direct `git diff` review:

- `L1_CORE/market_data_platform/market_data/schema.py`
- `L1_CORE/market_data_platform/market_data/storage.py`
- `L1_CORE/market_data_platform/market_data/adapters/coinbase.py`
- `L1_CORE/market_data_platform/market_data/adapters/binance.py`
- `L1_CORE/market_data_platform/market_data/test_storage.py`
- `L1_CORE/market_data_platform/market_data/test_parquet_roundtrip.py`

All six diffs were individually reviewed against the actual `git diff` output and confirmed to contain only the intended `instrument_id`-related changes. `git diff --check` on all six files returned exit code 0 (no whitespace/patch-format issues).

## 7. Restart Boundary

The collector was stopped, patched, and restarted on the Pi. Confirmed real restart timestamp: **2026-08-20 01:09:15 PDT** (epoch `1787213355`, confirmed via direct `date` conversion on the Pi). All post-fix validation uses this epoch as the file-modification-time (`mtime`) cutoff.

## 8. Production Validation Method

All existing automated tests for the affected module were run and passed, including `schema.py`'s and both adapters' own built-in smoke tests, `test_storage.py`, `test_parquet_roundtrip.py`, and `test_collector_integration.py` (which exercises the real production `_stream_messages()` function end-to-end). This full test suite was re-run fresh, live, a second time on 2026-08-24 to confirm currency rather than relying on memory of the original run, and passed identically. Separately, a direct scan of real, live production Parquet files was performed, selecting files by `mtime >= 1787213355`, and reading each file's actual `instrument_id` column to check for null values, empty strings, and any value outside `{"BTC-USD", "ETH-USD"}`.

**Caveat, stated precisely per the required standard:** this validates every file whose filesystem modification time is on or after the restart boundary. It does not independently verify an immutable, embedded per-record creation timestamp, since no such field exists in the schema.

## 9. Validation Results

| Dataset | Files | Rows | Null instrument_id | Empty instrument_id | Unexpected values | Read failures |
|---|---:|---:|---:|---:|---:|---:|
| Trades | 35,131 | 6,186,063 | 0 | 0 | 0 | 0 |
| Depth | 934,167 | 217,642,355 | 0 | 0 | 0 | 0 |

Combined: 223,828,418 rows validated, zero defects of any kind.

An earlier attempted validation scan used an incorrect restart epoch (`1755673755`, which does not correspond to 2026-08-20) and consequently swept in a large number of genuine pre-fix files, producing a real but misleading set of `FieldRef.Name(instrument_id)` read errors on files that were not corrupted — they simply predated the schema change. That earlier scan's results are superseded by the corrected scan documented above and should not be cited.

## 10. Historical Data Recovery Investigation

### Trade recovery

A full, exhaustive scan of the historical trade dataset (as it existed at the time of that scan) found real `trade_id` values clustering into two distinct, non-overlapping numeric bands, with a confirmed gap of 224,328,314 between the observed maximum of the lower band (835,280,351) and the observed minimum of the upper band (1,059,608,665). Zero records were found with a `trade_id` inside this gap across the full scanned dataset. Independent price-based validation (real trade prices in the lower band clustered at \$1,872–\$1,905; real trade prices in the upper band clustered at \$62,722–\$63,904) confirmed the lower band corresponds to ETH-USD and the upper band to BTC-USD.

**This is evidence-based, strong support for reconstructing historical trade identity in the dataset as it existed at the time of the scan.** It is not established as a universal or permanent guarantee of Coinbase's trade_id allocation scheme, and no independent confirmation was obtained from Coinbase's own primary documentation.

**Update, 2026-08-26 -- reconstruction executed, promoted, and independently validated.** A subsequent, more exhaustive audit found the originally recorded ETH upper boundary (835,280,351) was stale: 26,133 rows initially appearing to fall in an ambiguous gap were all found to be genuinely ETH-priced ($2,237.40-$2,265.69), extending the real ETH band to 835,306,482. The corrected empirical bands are: ETH-USD trade_id <= 835,306,482; BTC-USD trade_id >= 1,059,608,665; remaining unused separation of 224,302,182 IDs.

Using these corrected bands, the complete readable pre-fix trade corpus (258,208 files, 20,616,107 rows -- the 20 zero-byte files contained no rows and were excluded, see Section 11) was reconstructed with instrument_id added: 6,281,726 ETH-USD rows, 14,334,381 BTC-USD rows, zero unclassified. A 100-file pilot ran first and passed before the full reconstruction. The reconstructed corpus was written to a separate location (/mnt/lrs001/data/market_data_platform/recovery/instrument_id_trades_full), never overwriting the original canonical files during reconstruction itself.

The reconstructed corpus was independently validated four separate times before promotion: (1) internal self-consistency (zero nulls, zero unexpected values, correct totals), (2) source-correspondence and non-instrument-column value equality against canonical for all 258,208 files, (3) full-set bidirectional path correspondence using the exact mtime < 1787213355 selection rule (exact 1:1 match, zero orphans either direction), and (4) a completely fresh, independent re-derivation of every count directly from the recovery corpus alone. All four passed with zero defects.

**Canonical promotion was then executed.** A hard-linked, filesystem-level backup of the full canonical trade corpus (317,694 files, 1.9GB) was taken immediately before promotion. The collector was stopped to freeze the tree. Each of the 258,208 pre-fix files was replaced in canonical via an atomic, fail-closed, per-file operation: content copied to a same-directory temporary file, fsync'd, then os.replace()'d over the original (POSIX-atomic). Promoted files received fresh filesystem modification times rather than the original historical mtimes, since preserving the old mtimes would have caused the promoted files to be misclassified by the restart-boundary logic used throughout this investigation, and because the on-disk content was genuinely rewritten. All 258,208 files were promoted with zero failures.

Post-promotion, an exhaustive (non-sampled) validation confirmed every non-zero-byte file in canonical trades/ now carries instrument_id: zero nulls, zero unexpected values, zero read failures, across all 317,674 readable files (see Section 11 for the 20 excluded zero-byte files). The collector was restarted and confirmed to resume cleanly, with fresh post-restart trade writes independently inspected and confirmed to carry correct instrument_id values.

**Historical trade identity recovery is COMPLETE: reconstructed, independently validated, and promoted into canonical.**

### Depth recovery

No equivalent per-record identifier exists in the depth-level schema. Investigation tested three candidate structural recovery signals directly against live WebSocket data:

- `event_time` alone: cross-product collisions confirmed in two separate live samples (41 collisions / 4,916 unique values in one 5,000-message sample; 16 collisions / 4,955 unique values in a second).
- `timestamp_received` alone: worse performance (203 collisions / 4,731 unique values).
- Composite `(timestamp_received, event_time)`: improved but not zero (7 collisions / 4,975 unique keys).

No candidate tested achieved zero collisions.

**Update, 2026-08-26 -- composite key tested directly against real historical depth data.** A memory-safe, per-file scan of one full pre-fix date (2026-08-10: 178,714 files, 39,588,286 rows) checked every (timestamp_received, event_time) group for rows spanning both real ETH-range prices (~$1,000-$6,000) and real BTC-range prices (~$20,000+) within the same group. 2,597 such mixed groups were found across 2,529 files -- direct, concrete evidence of ambiguity within the actual historical corpus, not merely inferred from live sampling. This closes the previously open gap: the composite key's failure is now demonstrated in the real, persisted data itself, including within individual files.

**Conclusion, stated precisely:** event_time alone, timestamp_received alone, and their composite have each been investigated and found insufficient to deterministically recover instrument identity -- the third now confirmed directly against the actual historical corpus, not only live-sampled data. This does not prove no deterministic recovery method could ever exist; it establishes that no trustworthy deterministic reconstruction method was identified from the persisted depth fields investigated. The historical depth corpus is therefore treated as instrument-ambiguous for any research requiring per-instrument depth identity (see Section 12).

## 11. Remaining Limitations / Unresolved Questions

- Historical trade reconstruction: **complete** -- reconstructed, independently validated, and promoted into canonical (see Section 10).
- Historical depth reconstruction: **no trustworthy deterministic method identified** from the persisted fields investigated (event_time, timestamp_received, their composite), the last confirmed directly against real historical data. Not proven impossible in principle; simply not solved by the signals actually available in the persisted schema.
- 20 zero-byte trade files: mechanism established directly from source code -- _write_partitioned_parquet()'s open(filepath, "xb") creates the destination file immediately, before pq.write_table() writes content; an interruption between these two steps leaves a genuinely empty file. All 20 cluster in short (~10-20 second) bursts on four dates (Aug 6, 13, 15, 18), temporally consistent with -- but not conclusively proven to be caused by -- real WebSocket disconnect/reconnect events confirmed in collector logs (30 occurrences logged). The exact trigger for these specific 20 events remains unconfirmed. Whether any underlying trade data was permanently lost (versus simply never captured during a real, brief gap) was not established. Zero zero-byte trade files have occurred since the 2026-08-20 forward fix deployed, across five-plus days of continuous collection at the time of writing. On 2026-08-26, each file's path, original mtime, and this cause summary were recorded to a permanent, retained record (canonical/zero_byte_trade_files_removed_20260826.txt), and the 20 files were then removed from canonical, since they contained no readable rows and could not be repaired.
- Binance adapter's real-world usage history: not established in this investigation.
- Coinbase's trade_id allocation scheme: not confirmed against primary documentation; current evidence is empirical/observational only.

## 12. Research Epoch Decision

**Finalized, 2026-08-26.** The epoch policy is deliberately asymmetric by data type, based on actual recoverability rather than a single platform-wide cutoff:

- **Depth:** 2026-08-20 01:09:15 PDT (epoch 1787213355) is the clean research boundary for any analysis requiring trustworthy per-instrument depth identity. Pre-epoch depth data remains preserved, unmodified, in canonical storage, but must be treated as instrument-ambiguous and excluded from per-instrument depth research.
- **Trades:** no epoch cutoff applies. The full historical trade corpus, including all pre-epoch data back to the start of collection (2026-07-21), now carries valid, reconstructed, independently-validated instrument identity following the promotion described in Section 10. Trade-level research may draw on the complete history without exclusion.

## 13. Git Preservation / Commit

Committed on the Mac development workspace at commit `c018f04`, pushed to the canonical GitHub repository (`origin/main`), and confirmed in sync on the Pi deployment/runtime checkout via `git diff --exit-code origin/main` (exit code 0 across all six affected files). This followed, and helped establish, the project's canonical workflow: **Mac (development workspace) → GitHub `origin/main` (canonical versioned repository) → Pi (deployment/runtime)**. The fix had briefly existed only as staged, uncommitted changes directly on the Pi; that state was corrected by transferring the exact tested changes to the Mac, verifying them there, and committing/pushing from the Mac before syncing the Pi — rather than committing directly from the Pi.

## 14. Final Status

Forward fix: implemented, deployed, exhaustively validated in live production, and preserved through the canonical Mac → GitHub → Pi workflow at commit `c018f04`.

Historical trade recovery: **complete**. Reconstructed, independently validated four separate times, and promoted into canonical via an atomic, fail-closed, backed-up procedure. Post-promotion validation confirmed zero defects. The 20 zero-byte trade files were recorded and removed; canonical trades now contains 317,674 readable files, zero unreadable, 100% carrying instrument_id.

Historical depth recovery: no trustworthy deterministic method identified from the persisted fields investigated, confirmed directly against real historical data as well as live sampling. 2026-08-20 01:09:15 PDT is the finalized clean research epoch for per-instrument depth analysis; pre-epoch depth data is preserved but instrument-ambiguous.

This incident is considered closed. Any future work on deterministic historical depth recovery, using signals not yet investigated here, would constitute a new, separate investigation rather than a continuation of this one.
