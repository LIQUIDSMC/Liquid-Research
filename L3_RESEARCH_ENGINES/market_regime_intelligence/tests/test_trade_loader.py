"""
LRS-4 -- Partition Storage-Certification Tests

Deterministic synthetic fixtures for the per-partition K1.3-A
implementation in data/trade_loader.py.

Covers the local audit_partition() contract only:
- items 1-6
- fail-closed item 8

K1.3-A item 7 (completeness of the required partition set) is
intentionally not tested here because it belongs to the later
orchestration layer.

Run:
python3 -m L3_RESEARCH_ENGINES.market_regime_intelligence.tests.test_trade_loader
"""

import tempfile
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from L1_CORE.market_data_platform.market_data.storage import TRADE_SCHEMA
from L3_RESEARCH_ENGINES.market_regime_intelligence.data.trade_loader import (
    audit_partition,
    resolve_required_partitions,
    certify_required_partitions,
    load_trade_interval,
)


def _ms_utc(date_text: str, hour: int = 12) -> int:
    dt = datetime.strptime(date_text, "%Y-%m-%d").replace(
        hour=hour,
        tzinfo=timezone.utc,
    )
    return int(dt.timestamp() * 1000)


def _valid_rows(date_text: str):
    ts = _ms_utc(date_text)
    return [
        {
            "timestamp_received": ts,
            "event_time": ts,
            "trade_time": ts,
            "trade_id": 1,
            "price": Decimal("100.00000000"),
            "quantity": Decimal("1.00000000"),
            "is_buyer_maker": False,
            "instrument_id": "BTC-USD",
        }
    ]


def _write_table(path: Path, rows, schema=TRADE_SCHEMA):
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path)


def test_valid_partition_passes():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_text = "2026-09-10"
        date_dir = Path(tmp) / f"date={date_text}"
        date_dir.mkdir()

        _write_table(date_dir / "b.parquet", _valid_rows(date_text))
        _write_table(date_dir / "a.parquet", _valid_rows(date_text))

        result = audit_partition(date_dir)

        assert result.passed is True
        assert result.failure_code is None
        assert result.failure_detail is None
        assert result.partition_date == date_text
        assert result.file_count == 2
        assert result.files_checked == ("a.parquet", "b.parquet")

    print("PASS: valid canonical partition certifies with deterministic file order")


def test_missing_partition_container_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_dir = Path(tmp) / "date=2026-09-10"

        result = audit_partition(date_dir)

        assert result.passed is False
        assert result.failure_code == "PARTITION_CONTAINER_MISSING"

    print("PASS: missing partition container fails closed")


def test_invalid_partition_directory_name_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_dir = Path(tmp) / "2026-09-10"
        date_dir.mkdir()

        result = audit_partition(date_dir)

        assert result.passed is False
        assert result.failure_code == "PARTITION_DIRECTORY_NAME_INVALID"

    print("PASS: malformed partition directory name fails closed")


def test_empty_partition_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_dir = Path(tmp) / "date=2026-09-10"
        date_dir.mkdir()

        result = audit_partition(date_dir)

        assert result.passed is False
        assert result.failure_code == "PARTITION_EMPTY_NO_CANDIDATE_ARTIFACTS"

    print("PASS: empty partition fails closed")


def test_unreadable_parquet_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_dir = Path(tmp) / "date=2026-09-10"
        date_dir.mkdir()

        (date_dir / "broken.parquet").write_text("not parquet")

        result = audit_partition(date_dir)

        assert result.passed is False
        assert result.failure_code == "ARTIFACT_UNREADABLE"

    print("PASS: unreadable candidate Parquet artifact fails closed")


def test_schema_mismatch_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_text = "2026-09-10"
        date_dir = Path(tmp) / f"date={date_text}"
        date_dir.mkdir()

        wrong_schema = pa.schema([
            ("timestamp_received", pa.int64()),
            ("event_time", pa.int64()),
            ("trade_time", pa.int64()),
            ("trade_id", pa.int64()),
            ("price", pa.float64()),
            ("quantity", pa.decimal128(18, 8)),
            ("is_buyer_maker", pa.bool_()),
            ("instrument_id", pa.string()),
        ])

        rows = _valid_rows(date_text)
        rows[0]["price"] = 100.0

        _write_table(
            date_dir / "bad_schema.parquet",
            rows,
            schema=wrong_schema,
        )

        result = audit_partition(date_dir)

        assert result.passed is False
        assert result.failure_code == "SCHEMA_MISMATCH"

    print("PASS: noncanonical trade schema fails closed")


def test_required_raw_nulls_fail():
    for null_column in (
        "timestamp_received",
        "instrument_id",
        "trade_time",
    ):
        with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
            date_text = "2026-09-10"
            date_dir = Path(tmp) / f"date={date_text}"
            date_dir.mkdir()

            rows = _valid_rows(date_text)
            rows[0][null_column] = None

            _write_table(date_dir / "null.parquet", rows)

            result = audit_partition(date_dir)

            assert result.passed is False
            assert result.failure_code == "RAW_NULL_INVARIANT_VIOLATION"
            assert null_column in result.failure_detail

    print(
        "PASS: timestamp_received, instrument_id, and trade_time "
        "raw-null invariants all fail closed"
    )


def test_partition_key_inconsistency_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_dir = Path(tmp) / "date=2026-09-10"
        date_dir.mkdir()

        rows = _valid_rows("2026-09-11")
        _write_table(date_dir / "wrong_day.parquet", rows)

        result = audit_partition(date_dir)

        assert result.passed is False
        assert result.failure_code == "PARTITION_KEY_INCONSISTENCY"

    print("PASS: timestamp_received disagreement with receipt partition fails closed")


def test_result_is_immutable():
    with tempfile.TemporaryDirectory(prefix="lrs4_audit_") as tmp:
        date_text = "2026-09-10"
        date_dir = Path(tmp) / f"date={date_text}"
        date_dir.mkdir()

        _write_table(date_dir / "a.parquet", _valid_rows(date_text))
        result = audit_partition(date_dir)

        try:
            result.passed = False
            raise AssertionError("Expected frozen PartitionAuditResult mutation to fail")
        except FrozenInstanceError:
            pass

        assert isinstance(result.files_checked, tuple)

    print("PASS: partition audit evidence object is immutable")



def test_resolver_arbitrary_n_inclusive_range():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-01",
            "2026-09-02",
            "2026-09-03",
            "2026-09-04",
            "2026-09-05",
        ):
            (root / f"date={date_text}").mkdir()

        result = resolve_required_partitions(
            root,
            "2026-09-02",
            "2026-09-04",
        )

        assert result.required_dates == (
            "2026-09-02",
            "2026-09-03",
            "2026-09-04",
        )
        assert tuple(p.name for p in result.resolved_partitions) == (
            "date=2026-09-02",
            "date=2026-09-03",
            "date=2026-09-04",
        )
        assert result.missing_leading_dates == ()
        assert result.missing_interior_dates == ()
        assert result.missing_after_corpus_dates == ()
        assert result.corpus_first_date == "2026-09-01"
        assert result.corpus_last_date == "2026-09-05"

    print("PASS: resolver expands arbitrary-N inclusive receipt-date range")


def test_resolver_existing_empty_directory_is_resolved_not_missing():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-01").mkdir()
        empty_target = root / "date=2026-09-02"
        empty_target.mkdir()
        (root / "date=2026-09-03").mkdir()

        result = resolve_required_partitions(
            root,
            "2026-09-02",
            "2026-09-02",
        )

        assert result.resolved_partitions == (empty_target,)
        assert result.missing_leading_dates == ()
        assert result.missing_interior_dates == ()
        assert result.missing_after_corpus_dates == ()

        audit = audit_partition(empty_target)
        assert audit.passed is False
        assert (
            audit.failure_code
            == "PARTITION_EMPTY_NO_CANDIDATE_ARTIFACTS"
        )

    print(
        "PASS: resolver preserves existing-empty partition as resolved; "
        "audit layer rejects its contents separately"
    )


def test_resolver_classifies_leading_missing_dates():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-03",
            "2026-09-04",
            "2026-09-05",
        ):
            (root / f"date={date_text}").mkdir()

        result = resolve_required_partitions(
            root,
            "2026-09-01",
            "2026-09-04",
        )

        assert result.missing_leading_dates == (
            "2026-09-01",
            "2026-09-02",
        )
        assert result.missing_interior_dates == ()
        assert result.missing_after_corpus_dates == ()
        assert tuple(p.name for p in result.resolved_partitions) == (
            "date=2026-09-03",
            "date=2026-09-04",
        )

    print("PASS: resolver identifies leading corpus-boundary absences")


def test_resolver_classifies_interior_missing_dates():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-01").mkdir()
        (root / "date=2026-09-03").mkdir()

        result = resolve_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )

        assert result.missing_leading_dates == ()
        assert result.missing_interior_dates == ("2026-09-02",)
        assert result.missing_after_corpus_dates == ()
        assert tuple(p.name for p in result.resolved_partitions) == (
            "date=2026-09-01",
            "date=2026-09-03",
        )

    print("PASS: resolver identifies interior missing receipt partition")


def test_resolver_classifies_after_corpus_missing_dates():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-01").mkdir()
        (root / "date=2026-09-02").mkdir()

        result = resolve_required_partitions(
            root,
            "2026-09-02",
            "2026-09-04",
        )

        assert result.missing_leading_dates == ()
        assert result.missing_interior_dates == ()
        assert result.missing_after_corpus_dates == (
            "2026-09-03",
            "2026-09-04",
        )
        assert tuple(p.name for p in result.resolved_partitions) == (
            "date=2026-09-02",
        )

    print("PASS: resolver identifies required dates after observed corpus")


def test_resolver_can_report_all_three_missing_classes():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-03").mkdir()
        (root / "date=2026-09-05").mkdir()

        result = resolve_required_partitions(
            root,
            "2026-09-01",
            "2026-09-07",
        )

        assert result.missing_leading_dates == (
            "2026-09-01",
            "2026-09-02",
        )
        assert result.missing_interior_dates == ("2026-09-04",)
        assert result.missing_after_corpus_dates == (
            "2026-09-06",
            "2026-09-07",
        )
        assert tuple(p.name for p in result.resolved_partitions) == (
            "date=2026-09-03",
            "date=2026-09-05",
        )

    print(
        "PASS: resolver simultaneously preserves leading/interior/"
        "after-corpus classifications"
    )


def test_resolver_ignores_unrelated_entries():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-01").mkdir()
        (root / "date=2026-09-02").mkdir()
        (root / "notes").mkdir()
        (root / "README.txt").write_text("not a partition")

        result = resolve_required_partitions(
            root,
            "2026-09-01",
            "2026-09-02",
        )

        assert result.corpus_first_date == "2026-09-01"
        assert result.corpus_last_date == "2026-09-02"
        assert len(result.resolved_partitions) == 2

    print("PASS: unrelated non-partition entries do not alter corpus inventory")


def test_resolver_malformed_partition_like_directory_fails_closed():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-01").mkdir()
        (root / "date=NOT-A-DATE").mkdir()

        try:
            resolve_required_partitions(
                root,
                "2026-09-01",
                "2026-09-01",
            )
            raise AssertionError(
                "Expected malformed partition-like directory to fail"
            )
        except RuntimeError as exc:
            assert "malformed partition-like directory" in str(exc)

    print("PASS: malformed partition-like directory fails corpus inventory closed")


def test_resolver_reversed_interval_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)
        (root / "date=2026-09-01").mkdir()

        try:
            resolve_required_partitions(
                root,
                "2026-09-03",
                "2026-09-01",
            )
            raise AssertionError(
                "Expected reversed required interval to fail"
            )
        except ValueError as exc:
            assert "precedes start_date" in str(exc)

    print("PASS: resolver rejects reversed required interval")


def test_resolver_invalid_input_date_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)
        (root / "date=2026-09-01").mkdir()

        try:
            resolve_required_partitions(
                root,
                "2026-9-1",
                "2026-09-01",
            )
            raise AssertionError(
                "Expected noncanonical input date to fail"
            )
        except ValueError as exc:
            assert "strict YYYY-MM-DD" in str(exc)

    print("PASS: resolver requires strict YYYY-MM-DD input dates")


def test_resolver_missing_root_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp) / "missing"

        try:
            resolve_required_partitions(
                root,
                "2026-09-01",
                "2026-09-01",
            )
            raise AssertionError(
                "Expected missing canonical trades root to fail"
            )
        except FileNotFoundError:
            pass

    print("PASS: resolver fails closed when canonical trades root is missing")


def test_resolver_no_canonical_partitions_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_resolver_") as tmp:
        root = Path(tmp)
        (root / "notes").mkdir()

        try:
            resolve_required_partitions(
                root,
                "2026-09-01",
                "2026-09-01",
            )
            raise AssertionError(
                "Expected corpus with no canonical partitions to fail"
            )
        except RuntimeError as exc:
            assert "no canonical" in str(exc)

    print("PASS: resolver cannot infer corpus boundaries from empty inventory")


def test_certification_complete_valid_interval_passes():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-01",
            "2026-09-02",
            "2026-09-03",
        ):
            date_dir = root / f"date={date_text}"
            date_dir.mkdir()
            _write_table(
                date_dir / "trade.parquet",
                _valid_rows(date_text),
            )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )

        assert result.passed is True
        assert result.failure_code is None
        assert result.failure_detail is None
        assert result.failed_partition_dates == ()
        assert len(result.partition_audits) == 3
        assert all(audit.passed for audit in result.partition_audits)

    print("PASS: complete valid required partition interval certifies")


def test_certification_missing_only_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-01",
            "2026-09-03",
        ):
            date_dir = root / f"date={date_text}"
            date_dir.mkdir()
            _write_table(
                date_dir / "trade.parquet",
                _valid_rows(date_text),
            )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )

        assert result.passed is False
        assert (
            result.failure_code
            == "REQUIRED_PARTITION_SET_INCOMPLETE"
        )
        assert result.failed_partition_dates == ()
        assert result.resolution.missing_interior_dates == (
            "2026-09-02",
        )
        assert len(result.partition_audits) == 2
        assert all(audit.passed for audit in result.partition_audits)
        assert "interior_missing=2026-09-02" in result.failure_detail

    print("PASS: incomplete required partition set fails certification")


def test_certification_audit_failure_only_fails():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-01",
            "2026-09-02",
            "2026-09-03",
        ):
            (root / f"date={date_text}").mkdir()

        _write_table(
            root / "date=2026-09-01" / "trade.parquet",
            _valid_rows("2026-09-01"),
        )

        (
            root
            / "date=2026-09-02"
            / "broken.parquet"
        ).write_text("not parquet")

        _write_table(
            root / "date=2026-09-03" / "trade.parquet",
            _valid_rows("2026-09-03"),
        )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )

        assert result.passed is False
        assert result.failure_code == "PARTITION_AUDIT_FAILED"
        assert result.failed_partition_dates == ("2026-09-02",)
        assert len(result.partition_audits) == 3

        audits_by_date = {
            audit.partition_date: audit
            for audit in result.partition_audits
        }

        assert audits_by_date["2026-09-01"].passed is True
        assert audits_by_date["2026-09-02"].passed is False
        assert (
            audits_by_date["2026-09-02"].failure_code
            == "ARTIFACT_UNREADABLE"
        )
        assert audits_by_date["2026-09-03"].passed is True
        assert (
            "2026-09-02:ARTIFACT_UNREADABLE"
            in result.failure_detail
        )

    print("PASS: local partition audit failure fails whole interval")


def test_certification_missing_and_audit_failure_do_not_short_circuit():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        date_1 = root / "date=2026-09-01"
        date_1.mkdir()
        _write_table(
            date_1 / "trade.parquet",
            _valid_rows("2026-09-01"),
        )

        # 2026-09-02 intentionally absent.

        date_3 = root / "date=2026-09-03"
        date_3.mkdir()
        (date_3 / "broken.parquet").write_text("not parquet")

        # Extend observed corpus beyond the missing date so Sep 2 is
        # definitively interior, not after-corpus.
        date_4 = root / "date=2026-09-04"
        date_4.mkdir()
        _write_table(
            date_4 / "trade.parquet",
            _valid_rows("2026-09-04"),
        )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )

        assert result.passed is False
        assert (
            result.failure_code
            == "PARTITION_SET_AND_AUDIT_FAILURE"
        )
        assert result.resolution.missing_interior_dates == (
            "2026-09-02",
        )
        assert result.failed_partition_dates == ("2026-09-03",)

        # Critical non-short-circuit proof:
        # both existing required partitions must have been audited even
        # though another required date was absent.
        assert tuple(
            audit.partition_date
            for audit in result.partition_audits
        ) == (
            "2026-09-01",
            "2026-09-03",
        )

        assert result.partition_audits[0].passed is True
        assert result.partition_audits[1].passed is False
        assert (
            result.partition_audits[1].failure_code
            == "ARTIFACT_UNREADABLE"
        )

        assert "interior_missing=2026-09-02" in result.failure_detail
        assert (
            "2026-09-03:ARTIFACT_UNREADABLE"
            in result.failure_detail
        )

    print(
        "PASS: missing partition and corrupt existing partition are both "
        "reported without short-circuit"
    )


def test_certification_preserves_missing_classifications():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-03",
            "2026-09-05",
        ):
            date_dir = root / f"date={date_text}"
            date_dir.mkdir()
            _write_table(
                date_dir / "trade.parquet",
                _valid_rows(date_text),
            )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-07",
        )

        assert result.passed is False
        assert (
            result.failure_code
            == "REQUIRED_PARTITION_SET_INCOMPLETE"
        )

        assert result.resolution.missing_leading_dates == (
            "2026-09-01",
            "2026-09-02",
        )
        assert result.resolution.missing_interior_dates == (
            "2026-09-04",
        )
        assert result.resolution.missing_after_corpus_dates == (
            "2026-09-06",
            "2026-09-07",
        )

        assert "leading_missing=2026-09-01,2026-09-02" in result.failure_detail
        assert "interior_missing=2026-09-04" in result.failure_detail
        assert (
            "after_corpus_missing=2026-09-06,2026-09-07"
            in result.failure_detail
        )

    print("PASS: certification preserves all resolver missing-date classes")


def test_certification_audit_order_is_deterministic():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        for date_text in (
            "2026-09-03",
            "2026-09-01",
            "2026-09-02",
        ):
            date_dir = root / f"date={date_text}"
            date_dir.mkdir()
            _write_table(
                date_dir / "trade.parquet",
                _valid_rows(date_text),
            )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )

        assert tuple(
            audit.partition_date
            for audit in result.partition_audits
        ) == (
            "2026-09-01",
            "2026-09-02",
            "2026-09-03",
        )

    print("PASS: certification audit order follows required date order")


def test_certification_result_is_immutable():
    with tempfile.TemporaryDirectory(prefix="lrs4_cert_") as tmp:
        root = Path(tmp)

        date_dir = root / "date=2026-09-01"
        date_dir.mkdir()
        _write_table(
            date_dir / "trade.parquet",
            _valid_rows("2026-09-01"),
        )

        result = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-01",
        )

        try:
            result.passed = False
            raise AssertionError(
                "Expected frozen PartitionCertificationResult mutation "
                "to fail"
            )
        except FrozenInstanceError:
            pass

        assert isinstance(result.partition_audits, tuple)
        assert isinstance(result.failed_partition_dates, tuple)

    print("PASS: partition certification evidence object is immutable")


def _row(
    receipt_date,
    trade_time,
    trade_id,
    price,
    instrument_id="BTC-USD",
):
    receipt_ts = _ms_utc(receipt_date)
    return {
        "timestamp_received": receipt_ts,
        "event_time": trade_time,
        "trade_time": trade_time,
        "trade_id": trade_id,
        "price": Decimal(price),
        "quantity": Decimal("1.00000000"),
        "is_buyer_maker": False,
        "instrument_id": instrument_id,
    }


def test_interval_loader_spill_in_and_boundaries():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)

        start_ms = _ms_utc("2026-09-02", hour=0)
        end_ms = _ms_utc("2026-09-03", hour=0)

        prev_dir = root / "date=2026-09-01"
        target_dir = root / "date=2026-09-02"
        next_dir = root / "date=2026-09-03"

        for d in (prev_dir, target_dir, next_dir):
            d.mkdir()

        _write_table(
            prev_dir / "prev.parquet",
            [
                _row(
                    "2026-09-01",
                    start_ms - 1,
                    1,
                    "99.00000000",
                ),
                _row(
                    "2026-09-01",
                    start_ms + 50,
                    2,
                    "100.01000000",
                ),
            ],
        )

        _write_table(
            target_dir / "target.parquet",
            [
                _row(
                    "2026-09-02",
                    start_ms,
                    3,
                    "100.02000000",
                ),
                _row(
                    "2026-09-02",
                    start_ms + 1000,
                    4,
                    "100.03000000",
                ),
                _row(
                    "2026-09-02",
                    start_ms + 1500,
                    5,
                    "2500.00000000",
                    instrument_id="ETH-USD",
                ),
            ],
        )

        _write_table(
            next_dir / "next.parquet",
            [
                _row(
                    "2026-09-03",
                    end_ms - 43,
                    6,
                    "100.04000000",
                ),
                _row(
                    "2026-09-03",
                    end_ms,
                    7,
                    "100.05000000",
                ),
                _row(
                    "2026-09-03",
                    end_ms + 1,
                    8,
                    "100.06000000",
                ),
            ],
        )

        certification = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )
        assert certification.passed is True

        result = load_trade_interval(
            certification,
            "BTC-USD",
            start_ms,
            end_ms,
        )

        assert result.row_count == 4
        assert result.trade_id.tolist() == [3, 2, 4, 6]
        assert result.trade_time.tolist() == [
            start_ms,
            start_ms + 50,
            start_ms + 1000,
            end_ms - 43,
        ]

        assert 1 not in result.trade_id
        assert 5 not in result.trade_id
        assert 7 not in result.trade_id
        assert 8 not in result.trade_id

    print(
        "PASS: interval loader preserves neighboring-partition spill-in "
        "and exact [start_ms,end_ms) boundaries"
    )


def test_interval_loader_sorts_by_time_then_trade_id():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)
        date_text = "2026-09-02"

        start_ms = _ms_utc(date_text, hour=0)
        end_ms = start_ms + 10_000

        date_dir = root / f"date={date_text}"
        date_dir.mkdir()

        same_t = start_ms + 1000

        _write_table(
            date_dir / "b.parquet",
            [
                _row(date_text, same_t + 500, 30, "103.00000000"),
                _row(date_text, same_t, 20, "102.00000000"),
            ],
        )

        _write_table(
            date_dir / "a.parquet",
            [
                _row(date_text, same_t, 10, "101.00000000"),
                _row(date_text, start_ms + 100, 40, "100.00000000"),
            ],
        )

        certification = certify_required_partitions(
            root,
            date_text,
            date_text,
        )
        assert certification.passed is True

        result = load_trade_interval(
            certification,
            "BTC-USD",
            start_ms,
            end_ms,
        )

        assert result.trade_id.tolist() == [40, 10, 20, 30]
        assert result.trade_time.tolist() == [
            start_ms + 100,
            same_t,
            same_t,
            same_t + 500,
        ]

    print("PASS: interval loader sorts deterministically by (trade_time, trade_id)")


def test_interval_loader_empty_population_is_valid():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)
        date_text = "2026-09-02"

        date_dir = root / f"date={date_text}"
        date_dir.mkdir()

        ts = _ms_utc(date_text)

        _write_table(
            date_dir / "trade.parquet",
            [
                _row(
                    date_text,
                    ts,
                    1,
                    "2500.00000000",
                    instrument_id="ETH-USD",
                )
            ],
        )

        certification = certify_required_partitions(
            root,
            date_text,
            date_text,
        )
        assert certification.passed is True

        result = load_trade_interval(
            certification,
            "BTC-USD",
            ts - 1000,
            ts + 1000,
        )

        assert result.row_count == 0
        assert result.trade_time.size == 0
        assert result.trade_id.size == 0
        assert result.price.size == 0

    print("PASS: interval loader returns deterministic empty arrays for zero qualifying rows")


def test_interval_loader_requires_passed_certification():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)

        (root / "date=2026-09-01").mkdir()
        (root / "date=2026-09-03").mkdir()

        certification = certify_required_partitions(
            root,
            "2026-09-01",
            "2026-09-03",
        )
        assert certification.passed is False

        try:
            load_trade_interval(
                certification,
                "BTC-USD",
                1,
                2,
            )
            raise AssertionError(
                "Expected loader to reject failed partition certification"
            )
        except ValueError as exc:
            assert "requires passed partition certification" in str(exc)

    print("PASS: interval loader rejects failed storage certification")


def test_interval_loader_rejects_invalid_request():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)
        date_text = "2026-09-02"

        date_dir = root / f"date={date_text}"
        date_dir.mkdir()

        _write_table(
            date_dir / "trade.parquet",
            _valid_rows(date_text),
        )

        certification = certify_required_partitions(
            root,
            date_text,
            date_text,
        )
        assert certification.passed is True

        for instrument_id in ("", None):
            try:
                load_trade_interval(
                    certification,
                    instrument_id,
                    1,
                    2,
                )
                raise AssertionError(
                    "Expected invalid instrument_id to fail"
                )
            except ValueError:
                pass

        try:
            load_trade_interval(
                certification,
                "BTC-USD",
                2,
                2,
            )
            raise AssertionError(
                "Expected zero-width interval to fail"
            )
        except ValueError as exc:
            assert "greater than start_ms" in str(exc)

        try:
            load_trade_interval(
                certification,
                "BTC-USD",
                3,
                2,
            )
            raise AssertionError(
                "Expected reversed interval to fail"
            )
        except ValueError as exc:
            assert "greater than start_ms" in str(exc)

    print("PASS: interval loader validates instrument and interval request")


def test_interval_loader_rejects_null_trade_id():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)
        date_text = "2026-09-02"

        date_dir = root / f"date={date_text}"
        date_dir.mkdir()

        rows = _valid_rows(date_text)
        rows[0]["trade_id"] = None
        _write_table(date_dir / "trade.parquet", rows)

        certification = certify_required_partitions(
            root,
            date_text,
            date_text,
        )

        # K1.3-A raw-null certification does not currently include trade_id.
        assert certification.passed is True

        ts = _ms_utc(date_text)

        try:
            load_trade_interval(
                certification,
                "BTC-USD",
                ts - 1,
                ts + 1,
            )
            raise AssertionError(
                "Expected null trade_id to fail interval loading"
            )
        except RuntimeError as exc:
            assert "trade_id contains null" in str(exc)

    print("PASS: interval loader rejects null trade_id at execution layer")


def test_interval_loader_rejects_null_price():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)
        date_text = "2026-09-02"

        date_dir = root / f"date={date_text}"
        date_dir.mkdir()

        rows = _valid_rows(date_text)
        rows[0]["price"] = None
        _write_table(date_dir / "trade.parquet", rows)

        certification = certify_required_partitions(
            root,
            date_text,
            date_text,
        )

        assert certification.passed is True

        ts = _ms_utc(date_text)

        try:
            load_trade_interval(
                certification,
                "BTC-USD",
                ts - 1,
                ts + 1,
            )
            raise AssertionError(
                "Expected null price to fail interval loading"
            )
        except RuntimeError as exc:
            assert "price contains null" in str(exc)

    print("PASS: interval loader rejects null price at execution layer")


def test_interval_loader_rejects_non_positive_price():
    for bad_price in (
        "0.00000000",
        "-1.00000000",
    ):
        with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
            root = Path(tmp)
            date_text = "2026-09-02"

            date_dir = root / f"date={date_text}"
            date_dir.mkdir()

            rows = _valid_rows(date_text)
            rows[0]["price"] = Decimal(bad_price)
            _write_table(date_dir / "trade.parquet", rows)

            certification = certify_required_partitions(
                root,
                date_text,
                date_text,
            )
            assert certification.passed is True

            ts = _ms_utc(date_text)

            try:
                load_trade_interval(
                    certification,
                    "BTC-USD",
                    ts - 1,
                    ts + 1,
                )
                raise AssertionError(
                    "Expected non-positive price to fail"
                )
            except ValueError as exc:
                assert "non-positive price" in str(exc)

    print("PASS: interval loader rejects zero and negative prices")


def test_interval_result_is_immutable():
    with tempfile.TemporaryDirectory(prefix="lrs4_interval_") as tmp:
        root = Path(tmp)
        date_text = "2026-09-02"

        date_dir = root / f"date={date_text}"
        date_dir.mkdir()

        _write_table(
            date_dir / "trade.parquet",
            _valid_rows(date_text),
        )

        certification = certify_required_partitions(
            root,
            date_text,
            date_text,
        )
        assert certification.passed is True

        ts = _ms_utc(date_text)

        result = load_trade_interval(
            certification,
            "BTC-USD",
            ts - 1,
            ts + 1,
        )

        try:
            result.row_count = 999
            raise AssertionError(
                "Expected frozen TradeIntervalResult mutation to fail"
            )
        except FrozenInstanceError:
            pass

    print("PASS: trade interval result object is immutable")

if __name__ == "__main__":
    test_valid_partition_passes()
    test_missing_partition_container_fails()
    test_invalid_partition_directory_name_fails()
    test_empty_partition_fails()
    test_unreadable_parquet_fails()
    test_schema_mismatch_fails()
    test_required_raw_nulls_fail()
    test_partition_key_inconsistency_fails()
    test_result_is_immutable()

    test_resolver_arbitrary_n_inclusive_range()
    test_resolver_existing_empty_directory_is_resolved_not_missing()
    test_resolver_classifies_leading_missing_dates()
    test_resolver_classifies_interior_missing_dates()
    test_resolver_classifies_after_corpus_missing_dates()
    test_resolver_can_report_all_three_missing_classes()
    test_resolver_ignores_unrelated_entries()
    test_resolver_malformed_partition_like_directory_fails_closed()
    test_resolver_reversed_interval_fails()
    test_resolver_invalid_input_date_fails()
    test_resolver_missing_root_fails()
    test_resolver_no_canonical_partitions_fails()

    test_certification_complete_valid_interval_passes()
    test_certification_missing_only_fails()
    test_certification_audit_failure_only_fails()
    test_certification_missing_and_audit_failure_do_not_short_circuit()
    test_certification_preserves_missing_classifications()
    test_certification_audit_order_is_deterministic()
    test_certification_result_is_immutable()

    test_interval_loader_spill_in_and_boundaries()
    test_interval_loader_sorts_by_time_then_trade_id()
    test_interval_loader_empty_population_is_valid()
    test_interval_loader_requires_passed_certification()
    test_interval_loader_rejects_invalid_request()
    test_interval_loader_rejects_null_trade_id()
    test_interval_loader_rejects_null_price()
    test_interval_loader_rejects_non_positive_price()
    test_interval_result_is_immutable()

    print("\nALL LRS-4 TRADE-LOADER STRUCTURAL TESTS PASSED")
