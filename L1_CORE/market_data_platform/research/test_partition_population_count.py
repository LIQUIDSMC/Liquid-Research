"""Synthetic fixtures only; never access the canonical source corpus."""
import datetime as dt
import json
import os
from pathlib import Path
import uuid

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from L1_CORE.market_data_platform.research import partition_population_count as counter

HEALTH = {
    "ActiveState": "active", "SubState": "running",
    "MainPID": "123", "NRestarts": "0",
}


@pytest.fixture
def setup(tmp_path):
    source = tmp_path / "trades"
    partition = source / "date=2026-08-30"
    partition.mkdir(parents=True)
    output = tmp_path / "records"
    output.mkdir(mode=0o700)
    timestamp = (dt.date(2026, 8, 30) - dt.date(1970, 1, 1)).days * 86_400_000
    payload = partition / f"{uuid.uuid4()}.parquet"
    pq.write_table(pa.table({
        "instrument_id": ["BTC-USD", "ETH-USD", "BTC-USD"],
        "trade_time": pa.array([timestamp, timestamp + 1, timestamp + 2],
                              type=pa.int64()),
        "price": [1.0, 2.0, 3.0],
    }), payload, row_group_size=2)
    return source, output, payload


def run(setup, **kwargs):
    source, output, _ = setup
    return counter.count_partition(
        source, output, "2026-08-30",
        health=kwargs.pop("health", lambda remaining: dict(HEALTH)), **kwargs,
    )


def test_complete_record_counts_and_preserves_source(setup):
    raw = setup[2].read_bytes()
    record = run(setup)
    assert record["state"] == "COMPLETE"
    assert record["decoded_rows"] == 3
    assert record["instrument_day_counts"]["2026-08-30"] == {
        "BTC-USD": 2, "ETH-USD": 1,
    }
    attempt = Path(record["attempt"])
    assert json.loads((attempt / "complete.json").read_text()) == record
    assert json.loads((attempt / "incomplete.json").read_text())["state"] == "INCOMPLETE"
    assert setup[2].read_bytes() == raw
    assert os.stat(attempt).st_mode & 0o777 == 0o700
    assert os.stat(attempt / "complete.json").st_mode & 0o777 == 0o600


def test_hardlinked_regular_source_is_counted_without_unlinking(setup):
    alias = setup[2].parent.parent.parent / "retained-link"
    os.link(setup[2], alias)
    record = run(setup)
    assert record["multiply_linked_paths"] == 1
    assert alias.stat().st_nlink == 2


def test_symlink_retains_incomplete_attempt(setup):
    alias = setup[2].with_name(f"{uuid.uuid4()}.parquet")
    alias.symlink_to(setup[2])
    with pytest.raises(counter.CountError) as caught:
        run(setup)
    attempt = Path(caught.value.attempt)
    assert (attempt / "incomplete.json").exists()
    assert (attempt / "failure.json").exists()
    assert not (attempt / "complete.json").exists()


@pytest.mark.parametrize("field,value", [
    ("max_logical_bytes", 1), ("max_read_bytes", 1), ("max_rows", 1),
])
def test_resource_failure_retains_attempt(setup, field, value):
    limits = dict(counter.LIMITS)
    limits[field] = value
    with pytest.raises(counter.CountError) as caught:
        run(setup, limits=limits)
    assert not (Path(caught.value.attempt) / "complete.json").exists()
    assert (Path(caught.value.attempt) / "failure.json").exists()


def test_source_date_rejected_before_directory_access(setup, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Filesystem access before date validation")
    monkeypatch.setattr(counter, "open_directory", forbidden)
    with pytest.raises(counter.CountError, match="approved scope"):
        counter.count_partition(
            setup[0], setup[1], "2026-09-04",
            health=lambda remaining: dict(HEALTH),
        )


def test_collector_change_blocks_completion(setup):
    calls = []
    def health(remaining):
        calls.append(remaining)
        return dict(HEALTH, MainPID="124" if len(calls) == 2 else "123")
    with pytest.raises(counter.CountError, match="Collector properties changed") as caught:
        run(setup, health=health)
    assert not (Path(caught.value.attempt) / "complete.json").exists()


def test_runtime_failure_retains_initial_record(setup):
    times = iter([0.0, 301.0])
    with pytest.raises(counter.CountError, match="Runtime limit") as caught:
        run(setup, clock=lambda: next(times))
    assert (Path(caught.value.attempt) / "incomplete.json").exists()
    assert not (Path(caught.value.attempt) / "complete.json").exists()


def test_fresh_attempts_do_not_overwrite_prior_records(setup):
    first = run(setup)
    original = (Path(first["attempt"]) / "complete.json").read_bytes()
    second = run(setup)
    assert first["attempt"] != second["attempt"]
    assert (Path(first["attempt"]) / "complete.json").read_bytes() == original


def test_price_chunks_are_never_requested(setup, monkeypatch):
    forbidden_ranges = []
    with pq.ParquetFile(setup[2]) as parquet:
        for index in range(parquet.metadata.num_row_groups):
            column = parquet.metadata.row_group(index).column(2)
            offsets = [column.data_page_offset]
            if column.has_dictionary_page:
                offsets.append(column.dictionary_page_offset)
            start = min(offsets)
            forbidden_ranges.append((start, start + column.total_compressed_size))
    original = counter.os.pread
    def checked(descriptor, length, offset):
        assert all(
            offset + length <= start or offset >= end
            for start, end in forbidden_ranges
        )
        return original(descriptor, length, offset)
    monkeypatch.setattr(counter.os, "pread", checked)
    assert run(setup)["decoded_rows"] == 3


def test_null_selected_field_blocks_completion(setup):
    pq.write_table(pa.table({
        "instrument_id": pa.array([None], type=pa.string()),
        "trade_time": pa.array([1], type=pa.int64()),
    }), setup[2])
    with pytest.raises(counter.CountError, match="Null or invalid"):
        run(setup)



def test_failed_scan_records_collector_postcheck(setup):
    calls = []
    def health(remaining):
        calls.append(remaining)
        return dict(HEALTH)
    limits = dict(counter.LIMITS, max_read_bytes=1)
    with pytest.raises(counter.CountError) as caught:
        run(setup, limits=limits, health=health)
    failure = json.loads(
        (Path(caught.value.attempt) / "failure.json").read_text()
    )
    assert len(calls) == 2
    assert failure["collector_properties_match"] is True
    assert failure["collector_postcheck_error"] is None


def test_postcheck_failure_does_not_mask_original_error(setup):
    calls = []
    def health(remaining):
        calls.append(remaining)
        if len(calls) > 1:
            raise TimeoutError("synthetic collector timeout")
        return dict(HEALTH)
    with pytest.raises(counter.CountError, match="Requested-read") as caught:
        run(setup, limits=dict(counter.LIMITS, max_read_bytes=1), health=health)
    failure = json.loads(
        (Path(caught.value.attempt) / "failure.json").read_text()
    )
    assert failure["collector_postcheck_error"] == "TimeoutError"
    assert failure["collector_after"] is None


def test_completion_deadline_checked_before_link(tmp_path):
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    descriptor = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY)
    try:
        def expired():
            raise counter.CountError("Runtime limit exceeded")
        with pytest.raises(counter.CountError, match="Runtime limit"):
            counter.publish(
                descriptor, {"state": "COMPLETE"}, before_link=expired
            )
        assert not (attempt / "complete.json").exists()
        assert len(list(attempt.glob(".record-*.tmp"))) == 1
    finally:
        os.close(descriptor)


def test_existing_completion_cannot_be_overwritten(tmp_path):
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    descriptor = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY)
    try:
        counter.publish(descriptor, {"state": "COMPLETE", "value": 1})
        original = (attempt / "complete.json").read_bytes()
        with pytest.raises(FileExistsError):
            counter.publish(descriptor, {"state": "COMPLETE", "value": 2})
        assert (attempt / "complete.json").read_bytes() == original
    finally:
        os.close(descriptor)


def test_post_link_durability_error_preserves_completion(tmp_path, monkeypatch):
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    descriptor = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY)
    original_fsync = counter.os.fsync
    try:
        def fail_directory(target):
            if target == descriptor:
                raise OSError("synthetic directory fsync failure")
            return original_fsync(target)
        monkeypatch.setattr(counter.os, "fsync", fail_directory)
        with pytest.raises(counter.CountError) as caught:
            counter.publish(descriptor, {"state": "COMPLETE"})
        assert caught.value.published is True
        assert (attempt / "complete.json").exists()
    finally:
        os.close(descriptor)


def test_launcher_timeout_terminates_kills_and_reaps(monkeypatch):
    import signal
    import socket
    import subprocess

    events = []
    class Child:
        pid = 424242
        def __init__(self):
            self.waits = 0
        def wait(self, timeout=None):
            self.waits += 1
            events.append(("wait", timeout))
            if self.waits <= 2:
                raise subprocess.TimeoutExpired("synthetic", timeout)
            return -9

    monkeypatch.setattr(socket, "gethostname", lambda: "liquid-pi")
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Child())
    monkeypatch.setattr(
        counter.os, "killpg", lambda pid, sig: events.append(("signal", sig))
    )
    assert counter.launch_partition("2026-08-30") == 1
    assert events == [
        ("wait", 300.0), ("signal", signal.SIGTERM),
        ("wait", 2.0), ("signal", signal.SIGKILL), ("wait", None),
    ]


def test_worker_configures_memory_and_threads_without_real_limit_change(monkeypatch):
    import resource
    import socket

    observed = []
    monkeypatch.setattr(socket, "gethostname", lambda: "liquid-pi")
    monkeypatch.setattr(
        resource, "setrlimit", lambda kind, value: observed.append((kind, value))
    )
    for name in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "ARROW_NUM_THREADS", "PYTHONDONTWRITEBYTECODE",
    ):
        monkeypatch.setenv(name, "synthetic-old-value")
    counter.configure_worker()
    assert observed == [
        (resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    ]
    assert os.environ["OPENBLAS_NUM_THREADS"] == "1"
    assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"



@pytest.fixture
def completed_corpus(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "records"
    source.mkdir()
    output.mkdir(mode=0o700)
    paths = []
    for day in counter.SOURCE_DATES:
        partition = source / ("date=" + day)
        partition.mkdir()
        timestamp = (
            dt.date.fromisoformat(day) - dt.date(1970, 1, 1)
        ).days * 86_400_000
        pq.write_table(pa.table({
            "instrument_id": ["BTC-USD", "ETH-USD"],
            "trade_time": pa.array([timestamp, timestamp + 1], type=pa.int64()),
            "price": [1.0, 2.0],
        }), partition / f"{uuid.uuid4()}.parquet")
        record = counter.count_partition(
            source, output, day, health=lambda remaining: dict(HEALTH)
        )
        paths.append(Path(record["attempt"]) / "complete.json")
    return source, paths


def rewrite_record(path, change):
    record = json.loads(path.read_text())
    change(record)
    path.write_bytes(counter.encode(record))


def test_combines_all_28_records_without_source_reads(completed_corpus, monkeypatch):
    source, paths = completed_corpus
    def forbidden(*args, **kwargs):
        raise AssertionError("Source read during aggregation")
    monkeypatch.setattr(counter.os, "pread", forbidden)
    result = counter.combine_records(paths, expected_source_root=source)
    assert result["partition_count"] == 28
    assert result["instrument_day_count"] == 48
    assert result["decoded_rows"] == 56
    assert result["excluded_rows"] == 8
    assert all(
        values == {"BTC-USD": 1, "ETH-USD": 1}
        for values in result["instrument_day_counts"].values()
    )


def test_aggregate_missing_record_rejected(completed_corpus):
    source, paths = completed_corpus
    with pytest.raises(counter.CountError, match="Exactly 28"):
        counter.combine_records(paths[:-1], expected_source_root=source)


def test_aggregate_duplicate_path_rejected(completed_corpus):
    source, paths = completed_corpus
    paths[-1] = paths[0]
    with pytest.raises(counter.CountError, match="Duplicate"):
        counter.combine_records(paths, expected_source_root=source)


@pytest.mark.parametrize("field,value,message", [
    ("state", "FAILED", "incompatible"),
    ("reader_sha256", "0" * 64, "incompatible"),
    ("source_root", "/different/source", "Source-root"),
    ("decoded_rows", True, "record integer"),
    ("excluded_rows", 1, "accounting"),
    ("schema_version", True, "incompatible"),
    ("elapsed_seconds", 301.0, "runtime"),
])
def test_aggregate_invalid_records_rejected(
    completed_corpus, field, value, message
):
    source, paths = completed_corpus
    # Select a research-day partition whose synthetic rows are both included.
    path = paths[1]
    rewrite_record(path, lambda record: record.update({field: value}))
    with pytest.raises(counter.CountError, match=message):
        counter.combine_records(paths, expected_source_root=source)


def test_aggregate_mixed_limits_rejected(completed_corpus):
    source, paths = completed_corpus
    rewrite_record(
        paths[1],
        lambda record: record["limits"].update(max_files=11999),
    )
    with pytest.raises(counter.CountError, match="Mixed limit"):
        counter.combine_records(paths, expected_source_root=source)


def test_aggregate_record_with_failure_supplement_rejected(completed_corpus):
    source, paths = completed_corpus
    (paths[0].parent / "failure.json").write_text("{}")
    with pytest.raises(counter.CountError, match="failure record"):
        counter.combine_records(paths, expected_source_root=source)


def test_aggregate_symlinked_record_rejected(completed_corpus):
    source, paths = completed_corpus
    original = paths[0]
    retained = original.with_name("retained.json")
    original.rename(retained)
    original.symlink_to(retained)
    with pytest.raises((counter.CountError, OSError)):
        counter.combine_records(paths, expected_source_root=source)


def test_duplicate_json_keys_rejected():
    with pytest.raises(counter.CountError, match="Duplicate JSON"):
        counter._bounded_json(b'{"state":"COMPLETE","state":"FAILED"}')


@pytest.mark.parametrize("raw", [
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":123456789012345678901}',
    b'[' * 33 + b'0' + b']' * 33,
])
def test_bounded_json_rejects_invalid_or_overbudget_values(raw):
    with pytest.raises(counter.CountError):
        counter._bounded_json(raw)
