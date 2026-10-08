"""Persistent synthetic tests for Candidate C publication and verification."""

import json
import shutil
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from L1_CORE.market_data_platform.market_data import legacy_snapshot_export as exp
from L1_CORE.market_data_platform.market_data.test_legacy_snapshot_export import make_file



@pytest.fixture(autouse=True)
def synthetic_unsealed_date_range(monkeypatch):
    """
    Restrict workflow tests to isolated, unsealed synthetic dates.

    The production Candidate C constants are restored after each test.
    """
    monkeypatch.setattr(
        exp,
        "END_DATE",
        exp.START_DATE + timedelta(days=1),
    )


@pytest.fixture
def candidate_export(tmp_path):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    day = exp.START_DATE
    while day <= exp.END_DATE:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    make_file(source, "trades")
    make_file(source, "depth_levels")

    result = exp.run_candidate_c_export_prototype(
        source_root=source,
        output_dir=output,
        max_files=10,
    )

    assert result["acceptance"]["accepted"] is True
    assert result["seal"] is not None

    with sqlite3.connect(output / "inventory.sqlite3") as connection:
        publication = exp.publish_candidate_c_prototype(
            connection, output, result["seal"], source
        )

    assert publication["state"] == "ACCEPTED"

    return source, output


def copy_destination(source, output, destination):
    destination.mkdir()

    for dataset in exp.DATASETS:
        (destination / dataset).mkdir()

    for record in exp.stream_jsonl_records(output / "files.jsonl"):
        relative = Path(record["relative_path"])
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)


def test_complete_publication(candidate_export):
    source, output = candidate_export

    result = exp.verify_published_candidate_c_prototype(output, source)

    assert result["verified"] is True
    assert result["record_count"] == 2
    assert result["point_in_time_complete"] is False
    assert result["transfer_authorized"] is False

    inspection = exp.inspect_candidate_c_publication(output, source)
    assert inspection["classification"] == "COMPLETE"


def test_missing_completion_marker(candidate_export):
    source, output = candidate_export
    (output / "COMPLETE").unlink()

    with pytest.raises(ValueError):
        exp.verify_published_candidate_c_prototype(output, source)

    inspection = exp.inspect_candidate_c_publication(output, source)
    assert inspection["classification"] == "INTERRUPTED"


def test_tampered_files_ledger(candidate_export):
    source, output = candidate_export

    with (output / "files.jsonl").open("a") as handle:
        handle.write('{"unexpected":true}\n')

    with pytest.raises(ValueError):
        exp.verify_published_candidate_c_prototype(output, source)


def test_corrupted_source_bytes(candidate_export):
    source, output = candidate_export
    record = next(exp.stream_jsonl_records(output / "files.jsonl"))

    with (source / record["relative_path"]).open("ab") as handle:
        handle.write(b"CORRUPTED")

    with pytest.raises(ValueError):
        exp.verify_published_candidate_c_prototype(output, source)


def test_sqlite_state_mismatch(candidate_export):
    source, output = candidate_export

    with sqlite3.connect(output / "inventory.sqlite3") as connection:
        connection.execute(
            "UPDATE export_state SET state = 'VALIDATED'"
        )

    with pytest.raises(ValueError):
        exp.verify_published_candidate_c_prototype(output, source)


def test_interrupted_publication_artifact(candidate_export):
    source, output = candidate_export
    (output / "COMPLETE.tmp").write_text("interrupted")

    inspection = exp.inspect_candidate_c_publication(output, source)
    assert inspection["classification"] == "INTERRUPTED"

    with pytest.raises(ValueError):
        exp.verify_published_candidate_c_prototype(output, source)


def test_valid_destination(candidate_export, tmp_path):
    source, output = candidate_export
    destination = tmp_path / "destination"
    copy_destination(source, output, destination)

    result = exp.verify_candidate_c_destination(
        output, source, destination
    )

    assert result["verified"] is True
    assert result["record_count"] == 2
    assert result["transfer_authorized"] is False


def test_corrupted_destination(candidate_export, tmp_path):
    source, output = candidate_export
    destination = tmp_path / "destination"
    copy_destination(source, output, destination)

    record = next(exp.stream_jsonl_records(output / "files.jsonl"))
    with (destination / record["relative_path"]).open("ab") as handle:
        handle.write(b"CORRUPTED")

    with pytest.raises(ValueError):
        exp.verify_candidate_c_destination(output, source, destination)


def test_unexpected_destination_file(candidate_export, tmp_path):
    source, output = candidate_export
    destination = tmp_path / "destination"
    copy_destination(source, output, destination)

    (destination / "trades" / "unexpected.parquet").write_bytes(b"extra")

    with pytest.raises(ValueError):
        exp.verify_candidate_c_destination(output, source, destination)


def test_nested_destination_directory(candidate_export, tmp_path):
    source, output = candidate_export
    destination = tmp_path / "destination"
    copy_destination(source, output, destination)

    (destination / "trades" / "date=2026-08-21" / "nested").mkdir()

    with pytest.raises(ValueError):
        exp.verify_candidate_c_destination(output, source, destination)


def test_invalid_destination_partition(candidate_export, tmp_path):
    source, output = candidate_export
    destination = tmp_path / "destination"
    copy_destination(source, output, destination)

    (destination / "trades" / "date=2026-99-99").mkdir()

    with pytest.raises(ValueError):
        exp.verify_candidate_c_destination(output, source, destination)


def test_completion_marker_matches_manifest(candidate_export):
    source, output = candidate_export

    marker = json.loads((output / "COMPLETE").read_text())

    assert marker["manifest_sha256"] == exp.sha256_file(
        output / "manifest.json"
    )


def test_source_byte_budget_blocks_acceptance(tmp_path):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    day = exp.START_DATE
    while day <= exp.END_DATE:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    make_file(source, "trades")

    result = exp.run_candidate_c_export_prototype(
        source, output, max_files=10, max_source_bytes=1
    )

    assert result["acceptance"]["accepted"] is False
    assert result["validation"]["failed_count"] == 1
    assert result["seal"] is None

    exceptions = list(exp.stream_jsonl_records(output / "exceptions.jsonl"))
    assert any("budget exceeded" in item["message"] for item in exceptions)


def test_runtime_budget_blocks_acceptance(tmp_path, monkeypatch):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    day = exp.START_DATE
    while day <= exp.END_DATE:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    make_file(source, "trades")

    calls = iter([0.0, 2.0])
    monkeypatch.setattr(exp.time, "monotonic", lambda: next(calls))

    result = exp.run_candidate_c_export_prototype(
        source, output, max_files=10, max_runtime_seconds=1
    )

    assert result["acceptance"]["accepted"] is False
    assert result["validation"]["failed_count"] == 1
    assert result["seal"] is None


@pytest.mark.parametrize("invalid", [0, -1, True, float("inf"), float("nan")])
def test_invalid_byte_budget_rejected(tmp_path, invalid):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    with pytest.raises(ValueError):
        exp.run_candidate_c_export_prototype(
            source, output, max_files=10, max_source_bytes=invalid
        )


def test_sufficient_budgets_allow_acceptance(candidate_export):
    source, output = candidate_export

    assert exp.verify_published_candidate_c_prototype(
        output, source
    )["verified"] is True


@pytest.mark.parametrize("invalid", [0, -1, True, float("inf"), float("nan")])
def test_invalid_budgets_do_not_create_output(tmp_path, invalid):
    for parameter in ("max_source_bytes", "max_runtime_seconds"):
        output = tmp_path / f"{parameter}-export"

        with pytest.raises(ValueError):
            exp.run_candidate_c_export_prototype(
                tmp_path / "canonical",
                output,
                max_files=10,
                **{parameter: invalid},
            )

        assert not output.exists()


def test_sufficient_explicit_budgets_allow_acceptance(tmp_path):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    day = exp.START_DATE
    while day <= exp.END_DATE:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    make_file(source, "trades")

    result = exp.run_candidate_c_export_prototype(
        source,
        output,
        max_files=10,
        max_source_bytes=10_000_000,
        max_runtime_seconds=60,
    )

    assert result["acceptance"]["accepted"] is True
    assert result["validation"]["failed_count"] == 0
    assert result["seal"] is not None


@pytest.mark.parametrize(
    "byte_limit,runtime_limit",
    [
        (None, None),
        (1, 1),
        (10_000_000, 60),
        (1.5, 0.5),
    ],
)
def test_shared_budget_helper_accepts_valid_limits(
    byte_limit, runtime_limit
):
    assert exp.validate_resource_budgets(
        max_source_bytes=byte_limit,
        max_runtime_seconds=runtime_limit,
    ) is None


@pytest.mark.parametrize(
    "invalid",
    [0, -1, True, float("inf"), float("nan"), "100"],
)
@pytest.mark.parametrize(
    "parameter",
    ["max_source_bytes", "max_runtime_seconds"],
)
def test_shared_budget_helper_rejects_invalid_limits(
    invalid, parameter
):
    with pytest.raises(ValueError):
        exp.validate_resource_budgets(**{parameter: invalid})


def test_acceptance_rejects_falsified_reconciliation(candidate_export):
    source, output = candidate_export

    connection = sqlite3.connect(output / "inventory.sqlite3")

    try:
        start_count = connection.execute(
            "SELECT COUNT(*) FROM export_inventory"
        ).fetchone()[0]

        connection.execute(
            "UPDATE export_inventory SET seen_end = 0 "
            "WHERE path = (SELECT MIN(path) FROM export_inventory)"
        )
        connection.commit()

        false_reconciliation = {
            "reconciled": True,
            "end_count": start_count,
            "added_count": 0,
            "missing_count": 0,
        }

        result = exp.evaluate_export_acceptance(
            connection,
            output / "files.jsonl",
            output / "exceptions.jsonl",
            start_count,
            false_reconciliation,
        )

        assert result["accepted"] is False
        assert any(
            "absent from ending scan" in reason
            for reason in result["reasons"]
        )
    finally:
        connection.close()



def test_distinct_paths_with_identical_content(tmp_path):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    day = exp.START_DATE
    while day <= exp.END_DATE:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    original = make_file(source, "trades")
    duplicate = original.with_name(
        "00000000-0000-4000-8000-000000000002.parquet"
    )
    shutil.copyfile(source / original, source / duplicate)

    assert original != duplicate
    assert exp.sha256_file(source / original) == exp.sha256_file(
        source / duplicate
    )

    result = exp.run_candidate_c_export_prototype(
        source_root=source,
        output_dir=output,
        max_files=10,
    )

    assert result["acceptance"]["accepted"] is True

    records = list(exp.stream_jsonl_records(output / "files.jsonl"))
    assert len(records) == 2
    assert len({r["relative_path"] for r in records}) == 2
    assert len({r["sha256"] for r in records}) == 1

    with sqlite3.connect(output / "inventory.sqlite3") as connection:
        exp.publish_candidate_c_prototype(
            connection, output, result["seal"], source
        )

    verified = exp.verify_published_candidate_c_prototype(
        output, source
    )

    assert verified["verified"] is True
    assert verified["record_count"] == 2

    destination = tmp_path / "destination"
    copy_destination(source, output, destination)

    destination_result = exp.verify_candidate_c_destination(
        output, source, destination
    )

    assert destination_result["verified"] is True
    assert destination_result["record_count"] == 2



def test_crash_after_sqlite_acceptance_before_complete_rename(
    tmp_path, monkeypatch
):
    source = tmp_path / "canonical"
    output = tmp_path / "export"

    day = exp.START_DATE
    while day <= exp.END_DATE:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    make_file(source, "trades")
    make_file(source, "depth_levels")

    result = exp.run_candidate_c_export_prototype(
        source_root=source,
        output_dir=output,
        max_files=10,
    )

    assert result["acceptance"]["accepted"] is True

    original_replace = exp.os.replace

    def fail_completion_rename(src, dst):
        if Path(src).name == "COMPLETE.tmp":
            with sqlite3.connect(
                output / "inventory.sqlite3"
            ) as check:
                assert exp.get_export_state(check) == "ACCEPTED"

            raise OSError("Simulated crash before COMPLETE rename")

        return original_replace(src, dst)

    monkeypatch.setattr(exp.os, "replace", fail_completion_rename)

    with sqlite3.connect(output / "inventory.sqlite3") as connection:
        with pytest.raises(
            OSError, match="Simulated crash before COMPLETE rename"
        ):
            exp.publish_candidate_c_prototype(
                connection, output, result["seal"], source
            )

    assert (output / "manifest.json").is_file()
    assert (output / "COMPLETE.tmp").is_file()
    assert not (output / "COMPLETE").exists()

    with sqlite3.connect(output / "inventory.sqlite3") as connection:
        assert exp.get_export_state(connection) == "ACCEPTED"

    with pytest.raises(ValueError):
        exp.verify_published_candidate_c_prototype(output, source)

    inspection = exp.inspect_candidate_c_publication(output, source)

    assert inspection["classification"] == "INTERRUPTED"
    assert inspection["verified"] is False



@pytest.mark.parametrize(
    "partition_date",
    [
        exp.H2_START,
        exp.H2_END,
        exp.H2_START + timedelta(days=1),
    ],
)
def test_h2_date_guard_rejects_sealed_dates(partition_date):
    with pytest.raises(PermissionError, match="H2 reserve SEALED"):
        exp.require_unsealed_h2_date(partition_date)


@pytest.mark.parametrize(
    "partition_date",
    [
        exp.H2_START - timedelta(days=1),
        exp.H2_END + timedelta(days=1),
    ],
)
def test_h2_date_guard_allows_unsealed_dates(partition_date):
    exp.require_unsealed_h2_date(partition_date)



def test_direct_h2_validation_rejected_before_file_access(
    tmp_path, monkeypatch
):
    from datetime import date

    monkeypatch.setattr(exp, "END_DATE", date(2026, 10, 6))

    relative = (
        "trades/date=2026-09-04/"
        "00000000-0000-4000-8000-000000000001.parquet"
    )

    def forbidden_metadata(*args, **kwargs):
        raise AssertionError("H2 Parquet metadata was accessed")

    monkeypatch.setattr(exp, "inspect_parquet_metadata", forbidden_metadata)

    with pytest.raises(PermissionError, match="H2 reserve SEALED"):
        exp.validate_source_file(tmp_path / "canonical", relative)


def test_full_range_inventory_rejects_h2_before_enumeration(
    tmp_path, monkeypatch
):
    from datetime import date

    monkeypatch.setattr(exp, "END_DATE", date(2026, 10, 6))

    source = tmp_path / "canonical"
    day = exp.START_DATE

    while day < exp.H2_START:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    original_scandir = exp.os.scandir

    def guarded_scandir(path):
        if "date=2026-09-04" in str(path):
            raise AssertionError("Sealed H2 directory was enumerated")
        return original_scandir(path)

    monkeypatch.setattr(exp.os, "scandir", guarded_scandir)

    with pytest.raises(PermissionError, match="H2 reserve SEALED"):
        list(exp.iter_candidate_paths(source, max_files=10))



def test_h2_manifest_byte_verification_rejected(tmp_path, monkeypatch):
    from datetime import date

    monkeypatch.setattr(exp, "END_DATE", date(2026, 10, 6))

    record = {
        "relative_path": (
            "trades/date=2026-09-04/"
            "00000000-0000-4000-8000-000000000001.parquet"
        ),
        "dataset": "trades",
        "partition_date": "2026-09-04",
        "instruments": ["BTC-USD"],
        "size_bytes": 100,
        "sha256": "a" * 64,
        "row_count": 1,
        "row_groups": 1,
    }

    def forbidden_hash(*args, **kwargs):
        raise AssertionError("Sealed H2 file bytes were accessed")

    monkeypatch.setattr(exp, "sha256_file", forbidden_hash)

    with pytest.raises(PermissionError, match="H2 reserve SEALED"):
        exp.verify_manifest_file_bytes(tmp_path / "canonical", record)


def test_full_range_orchestrator_rejects_sealed_h2(
    tmp_path, monkeypatch
):
    """Full-range orchestration must fail closed at sealed H2."""
    from datetime import date

    monkeypatch.setattr(exp, "END_DATE", date(2026, 10, 6))

    source = tmp_path / "synthetic_canonical"
    output = tmp_path / "synthetic_export"

    day = exp.START_DATE
    while day < exp.H2_START:
        for dataset in exp.DATASETS:
            (source / dataset / f"date={day.isoformat()}").mkdir(
                parents=True, exist_ok=True
            )
        day += timedelta(days=1)

    original_scandir = exp.os.scandir

    def reject_h2_enumeration(path):
        if "date=2026-09-04" in str(path):
            raise AssertionError("Sealed H2 directory was enumerated")
        return original_scandir(path)

    monkeypatch.setattr(exp.os, "scandir", reject_h2_enumeration)

    with pytest.raises(PermissionError, match="H2 reserve SEALED"):
        exp.run_candidate_c_export_prototype(
            source_root=source,
            output_dir=output,
            max_files=100,
        )

    assert output.is_dir()
    assert not (output / "manifest.json").exists()
    assert not (output / "COMPLETE").exists()
