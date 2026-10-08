"""Isolated synthetic tests for Candidate C legacy export validation."""

import hashlib
from decimal import Decimal
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from L1_CORE.market_data_platform.market_data import legacy_snapshot_export as exp


TEST_DATE = "2026-08-21"
TEST_TS = int(
    datetime(2026, 8, 21, 12, tzinfo=timezone.utc).timestamp() * 1000
)


def make_file(root, dataset, instrument="BTC-USD", timestamp=None):
    timestamp = TEST_TS if timestamp is None else timestamp

    if dataset == "trades":
        schema = exp.DATASETS["trades"]
        row = {
            "timestamp_received": timestamp,
            "event_time": timestamp,
            "trade_time": timestamp,
            "trade_id": 1,
            "price": Decimal("50000.00000000"),
            "quantity": Decimal("0.01000000"),
            "is_buyer_maker": True,
            "instrument_id": instrument,
        }
    else:
        schema = exp.DATASETS["depth_levels"]
        row = {
            "timestamp_received": timestamp,
            "event_time": timestamp,
            "transaction_time": timestamp,
            "first_update_id": None,
            "final_update_id": None,
            "previous_final_update_id": None,
            "side": "bid",
            "price": Decimal("50000.00000000"),
            "quantity": Decimal("0.01000000"),
            "instrument_id": instrument,
        }

    relative = Path(dataset) / f"date={TEST_DATE}" / "00000000-0000-4000-8000-000000000001.parquet"
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pylist([row], schema=schema)
    pq.write_table(table, path)

    return relative


def test_valid_files():
    with tempfile.TemporaryDirectory() as tmp:
        for dataset in exp.DATASETS:
            relative = make_file(tmp, dataset)
            result = exp.validate_source_file(tmp, relative)

            assert result["dataset"] == dataset
            assert result["row_count"] == 1
            assert result["instruments"] == ["BTC-USD"]

            raw = (Path(tmp) / relative).read_bytes()
            assert result["sha256"] == hashlib.sha256(raw).hexdigest()

    print("PASS: valid trade/depth files and SHA-256")


def test_invalid_instrument():
    with tempfile.TemporaryDirectory() as tmp:
        relative = make_file(tmp, "trades", instrument="SOL-USD")

        try:
            exp.validate_source_file(tmp, relative)
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected instrument was accepted")

    print("PASS: invalid instrument rejected")


def test_wrong_partition():
    with tempfile.TemporaryDirectory() as tmp:
        wrong_ts = TEST_TS + 86400000
        relative = make_file(tmp, "trades", timestamp=wrong_ts)

        try:
            exp.validate_source_file(tmp, relative)
        except ValueError:
            pass
        else:
            raise AssertionError("Wrong partition timestamp was accepted")

    print("PASS: incorrect UTC partition rejected")


def test_zero_byte():
    with tempfile.TemporaryDirectory() as tmp:
        relative = Path("trades/date=2026-08-21/00000000-0000-4000-8000-000000000002.parquet")
        path = Path(tmp) / relative
        path.parent.mkdir(parents=True)
        path.touch()

        try:
            exp.validate_source_file(tmp, relative)
        except ValueError:
            pass
        else:
            raise AssertionError("Zero-byte file was accepted")

    print("PASS: zero-byte file rejected")


def test_corrupt_parquet():
    with tempfile.TemporaryDirectory() as tmp:
        relative = Path("trades/date=2026-08-21/00000000-0000-4000-8000-000000000003.parquet")
        path = Path(tmp) / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a parquet file")

        try:
            exp.validate_source_file(tmp, relative)
        except (ValueError, OSError, pa.ArrowException):
            pass
        else:
            raise AssertionError("Corrupt Parquet was accepted")

    print("PASS: corrupted Parquet rejected")


def test_path_traversal():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            exp.validate_source_file(
                tmp,
                "../trades/date=2026-08-21/00000000-0000-4000-8000-000000000001.parquet",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Path traversal was accepted")

    print("PASS: path traversal rejected")


if __name__ == "__main__":
    test_valid_files()
    test_invalid_instrument()
    test_wrong_partition()
    test_zero_byte()
    test_corrupt_parquet()
    test_path_traversal()

    print("\nAll synthetic validation tests passed.")


def test_noncanonical_filename():
    with tempfile.TemporaryDirectory() as tmp:
        relative = make_file(tmp, "trades")
        renamed = relative.with_name("not-a-uuid.parquet")
        (Path(tmp) / relative).rename(Path(tmp) / renamed)

        try:
            exp.validate_source_file(tmp, renamed)
        except ValueError as exc:
            assert "UUID" in str(exc)
        else:
            raise AssertionError("Noncanonical filename accepted")

    print("PASS: noncanonical UUID filename rejected")


def test_symlink_partition():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        real_partition = root / "real_partition"
        real_partition.mkdir()

        relative = make_file(tmp, "trades")
        original = root / relative
        target = real_partition / original.name
        original.rename(target)
        original.parent.rmdir()
        original.parent.symlink_to(real_partition, target_is_directory=True)

        try:
            exp.validate_source_file(tmp, relative)
        except ValueError as exc:
            assert "Symlink" in str(exc)
        else:
            raise AssertionError("Symlink partition accepted")

    print("PASS: symlink partition rejected")


def test_concurrent_mutation_detected():
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmp:
        relative = make_file(tmp, "trades")
        original_hash = exp.sha256_file

        def mutate_during_hash(path):
            digest = original_hash(path)
            with open(path, "ab") as handle:
                handle.write(b"mutation")
            return digest

        with patch.object(exp, "sha256_file", mutate_during_hash):
            try:
                exp.validate_source_file(tmp, relative)
            except ValueError as exc:
                assert "changed" in str(exc)
            else:
                raise AssertionError("Concurrent mutation accepted")

    print("PASS: concurrent file mutation detected")
