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

**This is evidence-based, strong support for reconstructing historical trade identity in the dataset as it existed at the time of the scan.** It is not established as a universal or permanent guarantee of Coinbase's trade_id allocation scheme, and no independent confirmation was obtained from Coinbase's own primary documentation. Historical trade reconstruction using this method has not yet been executed against the actual dataset.

### Depth recovery

No equivalent per-record identifier exists in the depth-level schema. Investigation tested three candidate structural recovery signals directly against live WebSocket data:

- `event_time` alone: cross-product collisions confirmed in two separate live samples (41 collisions / 4,916 unique values in one 5,000-message sample; 16 collisions / 4,955 unique values in a second).
- `timestamp_received` alone: worse performance (203 collisions / 4,731 unique values).
- Composite `(timestamp_received, event_time)`: improved but not zero (7 collisions / 4,975 unique keys).

No candidate tested achieved zero collisions. The composite key was never tested against the actual historical depth Parquet dataset itself (only against live-probed data), so its real, row-weighted ambiguity rate in the historical dataset is **unresolved**.

## 11. Remaining Limitations / Unresolved Questions

- Historical trade reconstruction: designed, evidence-supported, **not yet executed** against the real dataset.
- Historical depth reconstruction: **unresolved**. No deterministic method identified. Composite-key hybrid approach not yet tested against real historical data.
- 20 zero-byte trade files identified during the exhaustive historical trade scan: confirmed genuinely empty (0 bytes each), cause not investigated, disposition not yet decided.
- Binance adapter's real-world usage history: not established in this investigation.
- Coinbase's trade_id allocation scheme: not confirmed against primary documentation; current evidence is empirical/observational only.

## 12. Research Epoch Decision

**Not yet finalized.** Under consideration: treating 2026-08-20 01:09:15 PDT as the start of a clean research epoch for depth-level data specifically, given the real, demonstrated absence of a deterministic historical depth recovery method, while leaving the door open to historical trade reconstruction separately, given its meaningfully stronger evidentiary basis. This decision has not been made final and should be recorded as a deliberate choice, not a default, whenever it is.

## 13. Git Preservation / Commit

Committed on the Mac development workspace at commit `c018f04`, pushed to the canonical GitHub repository (`origin/main`), and confirmed in sync on the Pi deployment/runtime checkout via `git diff --exit-code origin/main` (exit code 0 across all six affected files). This followed, and helped establish, the project's canonical workflow: **Mac (development workspace) → GitHub `origin/main` (canonical versioned repository) → Pi (deployment/runtime)**. The fix had briefly existed only as staged, uncommitted changes directly on the Pi; that state was corrected by transferring the exact tested changes to the Mac, verifying them there, and committing/pushing from the Mac before syncing the Pi — rather than committing directly from the Pi.

## 14. Final Status

Forward fix: implemented, deployed, exhaustively validated in live production, and preserved through the canonical Mac → GitHub → Pi workflow at commit `c018f04`. Historical trade recovery: evidence-supported, not yet executed. Historical depth recovery: unresolved. 20 zero-byte trade files: identified, not yet investigated.
