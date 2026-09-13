"""
LRS-4 trade-data storage certification.

Stage 1 implementation of the per-partition portion of frozen
Experiment-v1 K1.3-A Auditable Source Coverage.

audit_partition() certifies one PRESENT canonical trade receipt-time
partition against K1.3-A items 1-6 and fail-closed item 8.

K1.3-A item 7 -- proving that ALL required receipt-time partitions
spanning a certified interval were audited -- is intentionally not
owned here. That is an orchestration-level invariant for the later
required-partition certification layer.

This module does not determine:
- S0,s
- confirmed acquisition-source breaks
- source-history maturity
- instrument-day source-history eligibility
- Window Evaluation / Instrument Path disposition
- regime states
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pyarrow.parquet as pq

from L1_CORE.market_data_platform.market_data.storage import (
    TRADE_SCHEMA,
    partition_date_utc,
)


RAW_NULL_CHECK_COLUMNS = (
    "timestamp_received",
    "instrument_id",
    "trade_time",
)


@dataclass(frozen=True)
class PartitionAuditResult:
    """Immutable result of auditing one canonical trade partition."""

    date_dir: Path
    partition_date: Optional[str]
    passed: bool
    failure_code: Optional[str] = None
    failure_detail: Optional[str] = None
    file_count: int = 0
    files_checked: Tuple[str, ...] = ()


def _failure(
    date_dir: Path,
    partition_date: Optional[str],
    code: str,
    detail: str,
    *,
    file_count: int = 0,
    files_checked: Tuple[str, ...] = (),
) -> PartitionAuditResult:
    """Construct one deterministic failed partition-audit result."""
    return PartitionAuditResult(
        date_dir=date_dir,
        partition_date=partition_date,
        passed=False,
        failure_code=code,
        failure_detail=detail,
        file_count=file_count,
        files_checked=files_checked,
    )


def _parse_partition_date(date_dir: Path) -> Optional[str]:
    """
    Parse canonical receipt partition directory name: date=YYYY-MM-DD.

    Returns None when the directory name cannot be established as a
    canonical UTC date partition.
    """
    prefix = "date="
    name = date_dir.name

    if not name.startswith(prefix):
        return None

    value = name[len(prefix):]

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None

    if parsed.strftime("%Y-%m-%d") != value:
        return None

    return value


def audit_partition(date_dir: Path) -> PartitionAuditResult:
    """
    Certify one canonical trade receipt-time partition.

    Implements the per-partition portions of frozen K1.3-A:
      1. required partition container exists;
      2. >=1 candidate Parquet artifact exists;
      3. every candidate artifact is readable as Parquet;
      4. schema/types conform exactly to canonical TRADE_SCHEMA;
      5. timestamp_received, instrument_id, trade_time are raw non-null;
      6. every timestamp_received maps to the directory's encoded UTC date;
      8. inability to establish any prerequisite fails closed.

    K1.3-A item 7 is deliberately excluded because completeness of the
    required partition SET is an orchestration-level property.
    """
    date_dir = Path(date_dir)

    # Item 1: the required partition container must exist.
    if not date_dir.is_dir():
        return _failure(
            date_dir,
            None,
            "PARTITION_CONTAINER_MISSING",
            f"Required partition directory does not exist: {date_dir}",
        )

    # Establish the authoritative partition key from the directory itself.
    partition_date = _parse_partition_date(date_dir)
    if partition_date is None:
        return _failure(
            date_dir,
            None,
            "PARTITION_DIRECTORY_NAME_INVALID",
            (
                "Partition directory must use canonical "
                f"'date=YYYY-MM-DD' naming: {date_dir.name!r}"
            ),
        )

    # Item 2: directory existence alone is insufficient.
    files = tuple(sorted(date_dir.glob("*.parquet"), key=lambda p: p.name))
    if not files:
        return _failure(
            date_dir,
            partition_date,
            "PARTITION_EMPTY_NO_CANDIDATE_ARTIFACTS",
            f"No candidate Parquet artifacts found in {date_dir}",
        )

    checked = []

    for file_path in files:
        # Item 3: every candidate artifact required by the scan must read.
        try:
            table = pq.read_table(file_path)
        except Exception as exc:
            return _failure(
                date_dir,
                partition_date,
                "ARTIFACT_UNREADABLE",
                f"{file_path.name}: {type(exc).__name__}: {exc}",
                file_count=len(files),
                files_checked=tuple(checked),
            )

        # Item 4: canonical trade storage has one authoritative schema.
        if not table.schema.equals(TRADE_SCHEMA, check_metadata=False):
            return _failure(
                date_dir,
                partition_date,
                "SCHEMA_MISMATCH",
                (
                    f"{file_path.name}: expected {TRADE_SCHEMA}; "
                    f"found {table.schema}"
                ),
                file_count=len(files),
                files_checked=tuple(checked),
            )

        # Item 5: frozen raw-null invariants.
        for column_name in RAW_NULL_CHECK_COLUMNS:
            null_count = table.column(column_name).null_count
            if null_count != 0:
                return _failure(
                    date_dir,
                    partition_date,
                    "RAW_NULL_INVARIANT_VIOLATION",
                    (
                        f"{file_path.name}: column {column_name!r} "
                        f"contains {null_count} null row(s)"
                    ),
                    file_count=len(files),
                    files_checked=tuple(checked),
                )

        # Item 6: receipt timestamp must agree with receipt-date partition.
        timestamp_received = table.column("timestamp_received")
        for row_index, value in enumerate(timestamp_received.to_pylist()):
            # Null has already been rejected above.
            try:
                observed_date = partition_date_utc(int(value))
            except Exception as exc:
                return _failure(
                    date_dir,
                    partition_date,
                    "PARTITION_KEY_UNVERIFIABLE",
                    (
                        f"{file_path.name}: row {row_index}: unable to derive "
                        "UTC partition date from timestamp_received: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    file_count=len(files),
                    files_checked=tuple(checked),
                )

            if observed_date != partition_date:
                return _failure(
                    date_dir,
                    partition_date,
                    "PARTITION_KEY_INCONSISTENCY",
                    (
                        f"{file_path.name}: row {row_index}: "
                        f"timestamp_received maps to {observed_date}, "
                        f"directory encodes {partition_date}"
                    ),
                    file_count=len(files),
                    files_checked=tuple(checked),
                )

        checked.append(file_path.name)

    return PartitionAuditResult(
        date_dir=date_dir,
        partition_date=partition_date,
        passed=True,
        file_count=len(files),
        files_checked=tuple(checked),
    )


@dataclass(frozen=True)
class PartitionResolutionResult:
    """
    Deterministic resolution of an inclusive UTC receipt-date range.

    Resolution answers only which canonical partition directories exist
    and where absent required dates fall relative to the observed corpus.
    It does NOT certify the contents of any existing partition.
    """

    trades_root: Path
    start_date: str
    end_date: str
    required_dates: Tuple[str, ...]
    resolved_partitions: Tuple[Path, ...]
    missing_leading_dates: Tuple[str, ...]
    missing_interior_dates: Tuple[str, ...]
    missing_after_corpus_dates: Tuple[str, ...]
    corpus_first_date: str
    corpus_last_date: str


def _parse_iso_utc_date(value: str):
    """Parse one strict YYYY-MM-DD date or fail closed."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"Expected strict YYYY-MM-DD date, got {value!r}"
        ) from exc

    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError(
            f"Expected strict YYYY-MM-DD date, got {value!r}"
        )

    return parsed.date()


def _inclusive_date_strings(start_date: str, end_date: str) -> Tuple[str, ...]:
    """Return every UTC calendar date in [start_date, end_date]."""
    start = _parse_iso_utc_date(start_date)
    end = _parse_iso_utc_date(end_date)

    if end < start:
        raise ValueError(
            f"end_date {end_date} precedes start_date {start_date}"
        )

    out = []
    current = start
    while current <= end:
        out.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return tuple(out)


def resolve_required_partitions(
    trades_root: Path,
    start_date: str,
    end_date: str,
) -> PartitionResolutionResult:
    """
    Resolve an arbitrary-N inclusive receipt-date range.

    The canonical corpus boundary is established from EXISTING canonical
    date=YYYY-MM-DD directories under trades_root. Directory presence is
    intentionally distinct from partition certification: an existing but
    empty/corrupt/unreadable partition is still inside the corpus and must
    later fail audit_partition(), rather than being reclassified as a
    corpus-boundary absence.

    Missing required dates are classified descriptively as:
      - leading: before the earliest observed canonical partition;
      - interior: between observed corpus boundaries;
      - after-corpus: after the latest observed canonical partition.

    This function does not apply K1.3-B source-history eligibility and does
    not create any new Experiment-v1 authorization rule.
    """
    trades_root = Path(trades_root)

    if not trades_root.is_dir():
        raise FileNotFoundError(
            f"Canonical trades root does not exist or is not a directory: "
            f"{trades_root}"
        )

    required_dates = _inclusive_date_strings(start_date, end_date)

    canonical_by_date = {}

    for entry in sorted(trades_root.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if not entry.name.startswith("date="):
            continue

        parsed_date = _parse_partition_date(entry)
        if parsed_date is None:
            raise RuntimeError(
                "Unable to establish canonical receipt-partition inventory: "
                f"malformed partition-like directory {entry}"
            )

        canonical_by_date[parsed_date] = entry

    if not canonical_by_date:
        raise RuntimeError(
            "Unable to establish corpus boundaries: no canonical "
            "date=YYYY-MM-DD trade partitions found"
        )

    corpus_dates = sorted(canonical_by_date)
    corpus_first_date = corpus_dates[0]
    corpus_last_date = corpus_dates[-1]

    resolved = []
    missing_leading = []
    missing_interior = []
    missing_after = []

    for required_date in required_dates:
        existing = canonical_by_date.get(required_date)

        if existing is not None:
            resolved.append(existing)
        elif required_date < corpus_first_date:
            missing_leading.append(required_date)
        elif required_date > corpus_last_date:
            missing_after.append(required_date)
        else:
            missing_interior.append(required_date)

    return PartitionResolutionResult(
        trades_root=trades_root,
        start_date=start_date,
        end_date=end_date,
        required_dates=required_dates,
        resolved_partitions=tuple(resolved),
        missing_leading_dates=tuple(missing_leading),
        missing_interior_dates=tuple(missing_interior),
        missing_after_corpus_dates=tuple(missing_after),
        corpus_first_date=corpus_first_date,
        corpus_last_date=corpus_last_date,
    )


@dataclass(frozen=True)
class PartitionCertificationResult:
    """
    Whole-interval K1.3-A storage certification evidence.

    This object preserves:
      - deterministic required-partition resolution;
      - the audit result for every existing required partition;
      - missing-date classifications from the resolver;
      - failed local partition audits.

    It does not interpret source-history eligibility or K1.3-B.
    """

    resolution: PartitionResolutionResult
    partition_audits: Tuple[PartitionAuditResult, ...]
    failed_partition_dates: Tuple[str, ...]
    passed: bool
    failure_code: Optional[str] = None
    failure_detail: Optional[str] = None


def certify_required_partitions(
    trades_root: Path,
    start_date: str,
    end_date: str,
) -> PartitionCertificationResult:
    """
    Certify the complete inclusive receipt-partition interval.

    K1.3-A item 7 requires every receipt-time partition spanning the
    certified interval to be accounted for and audited.

    Behavior:
      1. Resolve the complete arbitrary-N required date range.
      2. Audit every EXISTING required partition, deterministically.
      3. Preserve leading/interior/after-corpus missing classifications.
      4. Preserve every local audit failure.
      5. PASS only if no required partition is missing and every required
         partition passes audit_partition().

    Important:
      - Existing partitions are all audited even if some required dates
        are missing elsewhere in the interval.
      - This function does not translate missing classes into
        LRS4_SOURCE_HISTORY_INELIGIBLE or any other downstream
        Experiment-v1 eligibility status.
      - K1.3-B operational acquisition evidence is outside this layer.
    """
    resolution = resolve_required_partitions(
        trades_root,
        start_date,
        end_date,
    )

    audits = tuple(
        audit_partition(partition_dir)
        for partition_dir in resolution.resolved_partitions
    )

    failed_audits = tuple(
        audit
        for audit in audits
        if not audit.passed
    )

    failed_partition_dates = tuple(
        audit.partition_date
        if audit.partition_date is not None
        else audit.date_dir.name
        for audit in failed_audits
    )

    missing_count = (
        len(resolution.missing_leading_dates)
        + len(resolution.missing_interior_dates)
        + len(resolution.missing_after_corpus_dates)
    )

    complete_required_set = (
        missing_count == 0
        and len(resolution.resolved_partitions)
        == len(resolution.required_dates)
    )

    all_audits_pass = (
        len(audits) == len(resolution.required_dates)
        and not failed_audits
    )

    passed = complete_required_set and all_audits_pass

    if passed:
        return PartitionCertificationResult(
            resolution=resolution,
            partition_audits=audits,
            failed_partition_dates=(),
            passed=True,
        )

    if missing_count and failed_audits:
        failure_code = "PARTITION_SET_AND_AUDIT_FAILURE"
    elif missing_count:
        failure_code = "REQUIRED_PARTITION_SET_INCOMPLETE"
    else:
        failure_code = "PARTITION_AUDIT_FAILED"

    detail_parts = []

    if resolution.missing_leading_dates:
        detail_parts.append(
            "leading_missing="
            + ",".join(resolution.missing_leading_dates)
        )

    if resolution.missing_interior_dates:
        detail_parts.append(
            "interior_missing="
            + ",".join(resolution.missing_interior_dates)
        )

    if resolution.missing_after_corpus_dates:
        detail_parts.append(
            "after_corpus_missing="
            + ",".join(resolution.missing_after_corpus_dates)
        )

    if failed_audits:
        audit_failure_text = ",".join(
            (
                f"{audit.partition_date or audit.date_dir.name}:"
                f"{audit.failure_code}"
            )
            for audit in failed_audits
        )
        detail_parts.append(
            "audit_failures=" + audit_failure_text
        )

    return PartitionCertificationResult(
        resolution=resolution,
        partition_audits=audits,
        failed_partition_dates=failed_partition_dates,
        passed=False,
        failure_code=failure_code,
        failure_detail="; ".join(detail_parts),
    )


@dataclass(frozen=True)
class TradeIntervalResult:
    """
    Deterministically loaded trades for one instrument and one
    half-open trade-time interval [start_ms, end_ms).

    Arrays are sorted lexicographically by:
        (trade_time, trade_id)
    """

    instrument_id: str
    start_ms: int
    end_ms: int
    trade_time: np.ndarray
    trade_id: np.ndarray
    price: np.ndarray
    row_count: int


_INTERVAL_COLUMNS = (
    "instrument_id",
    "trade_time",
    "trade_id",
    "price",
)


def _iter_certified_parquet_files(
    certification: PartitionCertificationResult,
):
    """
    Yield every candidate Parquet file from a successful certification
    in deterministic receipt-date then filename order.
    """
    if not certification.passed:
        raise ValueError(
            "Trade interval loading requires passed partition certification"
        )

    for audit in certification.partition_audits:
        if not audit.passed:
            raise RuntimeError(
                "Certification invariant violated: passed whole-interval "
                "certification contains failed partition audit"
            )

        for file_name in audit.files_checked:
            yield audit.date_dir / file_name


def _validate_interval_request(
    instrument_id: str,
    start_ms: int,
    end_ms: int,
):
    if not isinstance(instrument_id, str) or not instrument_id:
        raise ValueError("instrument_id must be a non-empty string")

    if not isinstance(start_ms, (int, np.integer)):
        raise TypeError("start_ms must be an integer millisecond timestamp")

    if not isinstance(end_ms, (int, np.integer)):
        raise TypeError("end_ms must be an integer millisecond timestamp")

    start_ms = int(start_ms)
    end_ms = int(end_ms)

    if end_ms <= start_ms:
        raise ValueError(
            f"end_ms must be greater than start_ms; "
            f"got start_ms={start_ms}, end_ms={end_ms}"
        )

    return start_ms, end_ms


def _count_trade_interval_rows(
    certification: PartitionCertificationResult,
    instrument_id: str,
    start_ms: int,
    end_ms: int,
) -> int:
    """
    Pass 1: count exact qualifying rows without materializing the
    complete interval population.
    """
    count = 0

    for file_path in _iter_certified_parquet_files(certification):
        table = pq.ParquetFile(file_path).read(
            columns=["instrument_id", "trade_time"]
        )

        instrument_col = table.column("instrument_id")
        trade_time_col = table.column("trade_time")

        # These are already certified raw-null invariants, but retain an
        # execution-time fail-closed check so the loader never relies on
        # stale certification evidence if files change underneath it.
        if instrument_col.null_count:
            raise RuntimeError(
                f"{file_path}: instrument_id contains null rows during load"
            )

        if trade_time_col.null_count:
            raise RuntimeError(
                f"{file_path}: trade_time contains null rows during load"
            )

        instruments = np.asarray(
            instrument_col.to_pylist(),
            dtype=object,
        )
        trade_time = np.asarray(
            trade_time_col.to_numpy(zero_copy_only=False),
            dtype=np.int64,
        )

        mask = (
            (instruments == instrument_id)
            & (trade_time >= start_ms)
            & (trade_time < end_ms)
        )

        count += int(np.count_nonzero(mask))

    return count


def load_trade_interval(
    certification: PartitionCertificationResult,
    instrument_id: str,
    start_ms: int,
    end_ms: int,
) -> TradeIntervalResult:
    """
    Load one exact instrument/trade-time interval using a deterministic
    two-pass procedure.

    Frozen structural semantics:
      - input receipt partitions must already pass K1.3-A certification;
      - exact instrument_id match;
      - trade-time interval is [start_ms, end_ms);
      - Pass 1 counts qualifying rows;
      - Pass 2 allocates exact arrays and loads those rows;
      - Pass1/Pass2 disagreement hard-fails;
      - price must be finite and strictly positive;
      - output is sorted by (trade_time, trade_id).

    No grid, RVOL, threshold, state, episode, or outcome logic occurs here.
    """
    start_ms, end_ms = _validate_interval_request(
        instrument_id,
        start_ms,
        end_ms,
    )

    expected_rows = _count_trade_interval_rows(
        certification,
        instrument_id,
        start_ms,
        end_ms,
    )

    trade_time_out = np.empty(expected_rows, dtype=np.int64)
    trade_id_out = np.empty(expected_rows, dtype=np.int64)
    price_out = np.empty(expected_rows, dtype=np.float64)

    cursor = 0

    for file_path in _iter_certified_parquet_files(certification):
        table = pq.ParquetFile(file_path).read(
            columns=list(_INTERVAL_COLUMNS)
        )

        instrument_col = table.column("instrument_id")
        trade_time_col = table.column("trade_time")
        trade_id_col = table.column("trade_id")
        price_col = table.column("price")

        if instrument_col.null_count:
            raise RuntimeError(
                f"{file_path}: instrument_id contains null rows during load"
            )

        if trade_time_col.null_count:
            raise RuntimeError(
                f"{file_path}: trade_time contains null rows during load"
            )

        if trade_id_col.null_count:
            raise RuntimeError(
                f"{file_path}: trade_id contains null rows during load"
            )

        if price_col.null_count:
            raise RuntimeError(
                f"{file_path}: price contains null rows during load"
            )

        instruments = np.asarray(
            instrument_col.to_pylist(),
            dtype=object,
        )
        trade_time = np.asarray(
            trade_time_col.to_numpy(zero_copy_only=False),
            dtype=np.int64,
        )

        mask = (
            (instruments == instrument_id)
            & (trade_time >= start_ms)
            & (trade_time < end_ms)
        )

        selected = np.flatnonzero(mask)
        n_selected = int(selected.size)

        if n_selected == 0:
            continue

        trade_id = np.asarray(
            trade_id_col.to_numpy(zero_copy_only=False),
            dtype=np.int64,
        )

        # Canonical storage uses decimal128(18,8). Convert explicitly
        # through Python values to avoid relying on implicit Arrow/NumPy
        # decimal casting behavior.
        price = np.asarray(
            [float(value) for value in price_col.to_pylist()],
            dtype=np.float64,
        )

        next_cursor = cursor + n_selected

        if next_cursor > expected_rows:
            raise RuntimeError(
                "Pass 2 produced more qualifying rows than Pass 1 counted"
            )

        trade_time_out[cursor:next_cursor] = trade_time[selected]
        trade_id_out[cursor:next_cursor] = trade_id[selected]
        price_out[cursor:next_cursor] = price[selected]

        cursor = next_cursor

    if cursor != expected_rows:
        raise RuntimeError(
            "Pass1/Pass2 row-count mismatch: "
            f"Pass1={expected_rows}, Pass2={cursor}"
        )

    if expected_rows:
        if not np.all(np.isfinite(price_out)):
            raise ValueError(
                "Loaded interval contains non-finite price value(s)"
            )

        if np.any(price_out <= 0.0):
            raise ValueError(
                "Loaded interval contains non-positive price value(s)"
            )

        if np.any(trade_time_out < start_ms) or np.any(
            trade_time_out >= end_ms
        ):
            raise RuntimeError(
                "Loaded interval contains trade_time outside "
                "[start_ms, end_ms)"
            )

        # Lexicographic deterministic ordering:
        # primary trade_time, secondary trade_id.
        order = np.lexsort((trade_id_out, trade_time_out))

        trade_time_out = trade_time_out[order]
        trade_id_out = trade_id_out[order]
        price_out = price_out[order]

    return TradeIntervalResult(
        instrument_id=instrument_id,
        start_ms=start_ms,
        end_ms=end_ms,
        trade_time=trade_time_out,
        trade_id=trade_id_out,
        price=price_out,
        row_count=expected_rows,
    )
