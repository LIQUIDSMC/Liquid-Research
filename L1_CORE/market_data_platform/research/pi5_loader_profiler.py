"""Synthetic Parquet generation and actual-loader profiling only.

Fixtures are retained. No canonical source access, transfers, or research
outcomes. Production calls use fresh, bounded Pi5 worker processes.
"""
import contextlib
import datetime as dt
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid

from L1_CORE.market_data_platform.research import pi5_memory_profiler as base

VERSION = "LRS3_PI5_LOADER_PROFILER_V1"
ROOT = Path("/home/kristo/lrs3-pi5-loader-profiling-v1")
MODULE_NAME = "L1_CORE.market_data_platform.research.pi5_loader_profiler"
FILES_PER_PARTITION = 8955
MAX_FIXTURE_BYTES = 256 * 1024**2
MAX_FILE_BYTES = 1024**2
MAX_GENERATED_ROWS = 2_000_000
FREE_RESERVE = 1024**3
DATES = ("2026-08-21", "2026-08-22", "2026-08-23")
TARGET_DATE = "2026-08-22"
LOADER_PATH = Path(__file__).with_name("run_trade_flow_vs_momentum_screen.py")


def hashes():
    return {
        "loader_profiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "loader_sha256": hashlib.sha256(LOADER_PATH.read_bytes()).hexdigest(),
        **base.code_hashes(),
    }


def tick(deadline):
    base.require(time.monotonic() < deadline, "Loader-profile runtime limit exceeded")


def build_fixture(root, rows, *, files_per_partition=FILES_PER_PARTITION,
                  max_bytes=MAX_FIXTURE_BYTES, deadline=None):
    """Build only fresh synthetic files, retaining partial builds on failure."""
    base.require(
        type(rows) is int and 0 < rows <= max(base.ROW_COUNTS)
        and type(files_per_partition) is int
        and 0 < files_per_partition <= FILES_PER_PARTITION
        and type(max_bytes) is int and 0 < max_bytes <= MAX_FIXTURE_BYTES,
        "Invalid fixture limits",
    )
    base.require(all(day < "2026-09-04" for day in DATES),
                 "Invalid synthetic partition dates")
    file_count = 3 * files_per_partition
    generated_rows = rows + 3 * file_count
    base.require(generated_rows <= MAX_GENERATED_ROWS,
                 "Generated-row limit exceeded")
    deadline = time.monotonic() + base.RUNTIME if deadline is None else deadline
    root = Path(root)
    parent_fd = base.open_directory(root.parent)
    try:
        info = os.fstat(parent_fd)
        base.require(info.st_uid == os.geteuid()
                     and stat.S_IMODE(info.st_mode) == 0o700,
                     "Fixture parent must be operator-owned mode 0700")
        base.require(root.name == "synthetic-trades", "Unexpected fixture name")
        tick(deadline)
        os.mkdir(root.name, 0o700, dir_fd=parent_fd)
        fixture_fd = os.open(
            root.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    finally:
        os.close(parent_fd)

    try:
        import numpy as np
        import pyarrow as pa
        import pyarrow.parquet as pq
        from L1_CORE.market_data_platform.research import (
            run_trade_flow_vs_momentum_screen as runner,
        )

        start, end = runner._day_bounds_ms(TARGET_DATE)
        schema = pa.schema([
            ("timestamp_received", pa.int64()),
            ("event_time", pa.int64()),
            ("trade_time", pa.int64()),
            ("trade_id", pa.int64()),
            ("price", pa.decimal128(18, 8)),
            ("quantity", pa.decimal128(18, 8)),
            ("is_buyer_maker", pa.bool_()),
            ("instrument_id", pa.string()),
        ])
        edge = rows // 20
        selected_per_partition = (edge, rows - 2 * edge, edge)
        cursor = total_bytes = index = 0
        for day, selected_rows in zip(DATES, selected_per_partition):
            tick(deadline)
            name = "date=" + day
            os.mkdir(name, 0o700, dir_fd=fixture_fd)
            partition_fd = os.open(
                name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=fixture_fd,
            )
            try:
                quotient, remainder = divmod(selected_rows, files_per_partition)
                receipt, _ = runner._day_bounds_ms(day)
                for number in range(files_per_partition):
                    tick(deadline)
                    selected = quotient + int(number < remainder)
                    ids = np.arange(cursor, cursor + selected, dtype=np.int64)
                    times = start + (
                        (rows - ids) * 86_399_000 // rows
                    )
                    all_ids = ids.tolist() + [
                        rows + index * 3, rows + index * 3 + 1,
                        rows + index * 3 + 2,
                    ]
                    all_times = times.tolist() + [start + 100, start - 1, end]
                    instruments = ["BTC-USD"] * selected + [
                        "ETH-USD", "BTC-USD", "BTC-USD",
                    ]
                    count = selected + 3
                    table = pa.table({
                        "timestamp_received": [receipt + 40_000] * count,
                        "event_time": [receipt + 39_999] * count,
                        "trade_time": all_times,
                        "trade_id": all_ids,
                        "price": [Decimal("100.00000000")] * count,
                        "quantity": [Decimal("1.00000000")] * count,
                        "is_buyer_maker": [bool(i % 2) for i in all_ids],
                        "instrument_id": instruments,
                    }, schema=schema)
                    sink = pa.BufferOutputStream()
                    pq.write_table(table, sink, compression="NONE")
                    raw = sink.getvalue().to_pybytes()
                    base.require(len(raw) <= MAX_FILE_BYTES,
                                 "Synthetic file-size limit exceeded")
                    base.require(total_bytes + len(raw) <= max_bytes,
                                 "Fixture-byte limit exceeded")
                    space = os.fstatvfs(fixture_fd)
                    base.require(
                        space.f_bavail * space.f_frsize - len(raw) >= FREE_RESERVE,
                        "Synthetic fixture free-space reserve reached",
                    )
                    filename = str(uuid.UUID(int=index + 1)) + ".parquet"
                    descriptor = os.open(
                        filename,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600, dir_fd=partition_fd,
                    )
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(raw)
                    total_bytes += len(raw)
                    cursor += selected
                    index += 1
            finally:
                os.close(partition_fd)
        base.require(cursor == rows and index == file_count,
                     "Synthetic generator accounting mismatch")
        return {
            "fixture_files": index,
            "fixture_logical_bytes": total_bytes,
            "fixture_rows": generated_rows,
            "expected_selected_rows": rows,
            "control_rows": 3 * file_count,
            "compression": "NONE",
        }
    finally:
        os.close(fixture_fd)


def measure_loader(rows, attempt_root, *, files_per_partition=FILES_PER_PARTITION,
                   fixture_byte_limit=MAX_FIXTURE_BYTES):
    """Actual counting/loading/casting/sorting; fixture generation is included."""
    started = time.monotonic()
    deadline = started + base.RUNTIME
    attempt_root = Path(attempt_root)
    fixture = attempt_root / "synthetic-trades"
    phases = {}
    peaks = {}

    phase_start = time.monotonic()
    fixture_record = build_fixture(
        fixture, rows, files_per_partition=files_per_partition,
        max_bytes=fixture_byte_limit, deadline=deadline,
    )
    phases["generation"] = time.monotonic() - phase_start
    peaks["after_generation"] = base.peak_rss()

    import numpy as np
    import pyarrow as pa
    from L1_CORE.market_data_platform.research import (
        run_trade_flow_vs_momentum_screen as runner,
        trade_flow_vs_momentum_screen as kernel,
    )

    original_root = runner.CANONICAL_TRADES_ROOT
    try:
        # The actual loader's global root is redirected before source resolution.
        runner.CANONICAL_TRADES_ROOT = fixture
        with contextlib.redirect_stdout(sys.stderr):
            tick(deadline)
            partitions = runner._resolve_source_partitions(TARGET_DATE)
            base.require(
                [label for label, _ in partitions] == list(DATES)
                and all(directory.parent == fixture for _, directory in partitions),
                "Loader resolved outside the synthetic fixture",
            )
            start, end = runner._day_bounds_ms(TARGET_DATE)
            phase_start = time.monotonic()
            counted, statistics = runner.count_target_rows(
                partitions, "BTC-USD", start, end
            )
            tick(deadline)
            base.require(counted == rows, "Pass 1 selected-row mismatch")
            phases["counting"] = time.monotonic() - phase_start
            peaks["after_counting"] = base.peak_rss()

            phase_start = time.monotonic()
            trade_time, trade_id, price, quantity, maker = runner.load_instrument_day(
                partitions, "BTC-USD", start, end, counted
            )
            tick(deadline)
            runner.validate_day_integrity(trade_time, price, quantity, start, end)
            phases["loading_and_validation"] = time.monotonic() - phase_start
            peaks["after_loading"] = base.peak_rss()

            phase_start = time.monotonic()
            order = np.lexsort((trade_id, trade_time))
            trade_time = trade_time[order]
            trade_id_sorted = trade_id[order]
            del trade_id
            trade_id = trade_id_sorted
            del trade_id_sorted
            price = price[order]
            quantity = quantity[order]
            maker = maker[order]
            del order
            kernel.validate_sorted_arrays(
                trade_time, trade_id, price, quantity, maker
            )
            # Exact synthetic membership check; its allocations count toward RSS.
            base.require(
                np.array_equal(np.sort(trade_id), np.arange(rows, dtype=np.int64)),
                "Synthetic selected-ID membership mismatch",
            )
            tick(deadline)
            phases["sorting_and_membership_validation"] = (
                time.monotonic() - phase_start
            )
            peaks["after_sorting_and_validation"] = base.peak_rss()
    finally:
        runner.CANONICAL_TRADES_ROOT = original_root

    return {
        "version": VERSION,
        "stage": "synthetic_parquet_loader_sorting",
        "row_count": rows,
        "loaded_target_rows": int(len(trade_time)),
        "input_array_bytes": int(sum(
            array.nbytes for array in (trade_time, trade_id, price, quantity, maker)
        )),
        "selected_ids_verified": True,
        **fixture_record,
        "fixture_root": str(fixture),
        "partition_statistics": statistics,
        "phase_seconds": phases,
        "phase_peak_rss_bytes": peaks,
        "peak_rss_bytes": base.peak_rss(),
        "elapsed_seconds": time.monotonic() - started,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "pyarrow_version": pa.__version__,
        **hashes(),
    }


def parse_result(raw, rows, attempt):
    import math

    def pairs(items):
        value = {}
        for key, item in items:
            base.require(key not in value, "Duplicate worker JSON key")
            value[key] = item
        return value

    def constant(token):
        raise base.ProfileError("Nonfinite worker JSON constant")

    base.require(len(raw) <= base.MAX_JSON, "Worker result exceeds size limit")
    record = json.loads(
        raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
    )
    base.require(type(record) is dict, "Invalid worker record")
    expected = {
        "version": VERSION, "stage": "synthetic_parquet_loader_sorting",
        "row_count": rows, "loaded_target_rows": rows,
        "input_array_bytes": rows * 33,
        "fixture_files": 3 * FILES_PER_PARTITION,
        "fixture_rows": rows + 9 * FILES_PER_PARTITION,
        "control_rows": 9 * FILES_PER_PARTITION,
        "expected_selected_rows": rows, "compression": "NONE",
        "fixture_root": str(Path(attempt) / "synthetic-trades"),
        **hashes(),
    }
    for key, value in expected.items():
        base.require(
            type(record.get(key)) is type(value) and record[key] == value,
            "Worker result mismatch: " + key,
        )
    base.require(record.get("selected_ids_verified") is True,
                 "Synthetic selected IDs not verified")
    base.require(
        type(record.get("fixture_logical_bytes")) is int
        and 0 < record["fixture_logical_bytes"] <= MAX_FIXTURE_BYTES,
        "Invalid fixture-byte measurement",
    )
    base.require(type(record.get("peak_rss_bytes")) is int
                 and record["peak_rss_bytes"] > 0, "Invalid peak RSS")
    base.require(
        type(record.get("elapsed_seconds")) in (int, float)
        and math.isfinite(record["elapsed_seconds"])
        and 0 <= record["elapsed_seconds"] <= base.RUNTIME,
        "Invalid worker elapsed time",
    )
    return record


def launch(rows, output_root):
    base.require(type(rows) is int and rows in base.ROW_COUNTS,
                 "Invalid production profile scale")
    output_fd = attempt_fd = None
    attempt = None
    published = False
    try:
        output_fd = base.open_directory(output_root)
        info = os.fstat(output_fd)
        base.require(
            info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
            "Output root must be operator-owned mode 0700",
        )
        name = f"parquet-loader-{rows}--{uuid.uuid4()}"
        os.mkdir(name, 0o700, dir_fd=output_fd)
        attempt = str(Path(output_root) / name)
        os.fsync(output_fd)
        attempt_fd = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output_fd
        )
        base.publish(attempt_fd, "incomplete.json", {
            "state": "INCOMPLETE", "version": VERSION,
            "row_count": rows, "attempt": attempt,
        })
        environment = dict(os.environ)
        environment.pop("PYTHONHOME", None)
        environment["PYTHONPATH"] = str(base.REPOSITORY)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        for variable in base.THREAD_VARIABLES:
            environment[variable] = "1"
        command = [
            sys.executable, "-B", "-m", MODULE_NAME,
            "_worker", str(rows), "--attempt", attempt,
        ]
        outcome = base.capture(command, environment)
        base.require(
            outcome["error"] is None and outcome["exit_status"] == 0,
            f'{outcome["error"]}; exit={outcome["exit_status"]}; '
            f'stderr={outcome["stderr_tail"]}',
        )
        measurement = parse_result(outcome["stdout"], rows, attempt)
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=base.REPOSITORY, text=True, timeout=5,
        ).strip()
        record = {
            "state": "COMPLETE", "schema_version": 1, "version": VERSION,
            "row_count": rows, "attempt": attempt,
            "source_revision": revision,
            "worker_exit_status": outcome["exit_status"],
            "address_space_limit_bytes": base.ADDRESS_SPACE,
            "thread_environment": {
                name: environment[name] for name in base.THREAD_VARIABLES
            },
            "measurement": measurement, "stderr_tail": outcome["stderr_tail"],
            "limitations": [
                "Synthetic files only; no canonical inputs or data transfer.",
                "Uniform synthetic file distribution is not a historical reconstruction.",
                "Peak RSS includes fixture generation, loading and validation.",
                "Compression NONE differs from potentially compressed historical files.",
                "Free-space reserve is cooperative, not reserved storage.",
                "Fixtures and partial attempts are retained; no automatic cleanup.",
                "No calculation kernel, new reporting, or full-study execution.",
                "No general full-pipeline memory-safety or scientific-readiness claim.",
            ],
        }
        base.publish(attempt_fd, "complete.json", record)
        published = True
        return record
    except Exception as error:
        secondary = getattr(error, "reporting_error", None)
        published = published or getattr(error, "published", False)
        if attempt_fd is not None and not published:
            try:
                base.publish(attempt_fd, "failure.json", {
                    "state": "FAILED", "version": VERSION,
                    "row_count": rows, "attempt": attempt,
                    "error": str(error)[-4096:],
                })
            except Exception as reporting:
                secondary = repr(reporting)
        raise base.ProfileError(
            str(error), attempt=attempt, published=published,
            reporting_error=secondary,
        ) from error
    finally:
        for descriptor in (attempt_fd, output_fd):
            if descriptor is not None:
                os.close(descriptor)


def main():
    import argparse
    import socket

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("profile", "_worker"))
    parser.add_argument("rows", type=int, choices=base.ROW_COUNTS)
    parser.add_argument("--attempt")
    args = parser.parse_args()
    base.require(socket.gethostname() == "liquid-pi5", "Expected Pi5")
    try:
        if args.operation == "_worker":
            base.require(args.attempt is not None, "Worker attempt required")
            attempt = Path(args.attempt)
            base.require(attempt.is_absolute() and attempt.parent == ROOT,
                         "Worker attempt outside profiling root")
            base.configure_worker()
            result = measure_loader(args.rows, attempt)
        else:
            base.require(args.attempt is None, "Parent chooses exclusive attempts")
            result = launch(args.rows, ROOT)
        print(base.encode(result).decode(), end="")
        return 0
    except Exception as error:
        print(base.encode({
            "classification": "FAILED" if not getattr(error, "published", False)
                              else "PUBLICATION_DURABILITY_UNCERTAIN",
            "error": str(error)[-4096:],
            "attempt": getattr(error, "attempt", None),
            "reporting_error": getattr(error, "reporting_error", None),
        }).decode(), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
