"""Bounded synthetic loader/kernel/reporting profiling.

One generated BTC fixture is reused with synthetic date shifts and
instrument labels for the reporting matrix. No historical inputs.
"""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
import uuid

from L1_CORE.market_data_platform.research import (
    pi5_memory_profiler as base,
    pi5_loader_profiler as fixture,
)

VERSION = "LRS3_PI5_COMBINED_PROFILER_V1"
ROOT = Path("/home/kristo/lrs3-pi5-combined-profiling-v1")
MODULE = "L1_CORE.market_data_platform.research.pi5_combined_profiler"
POLICY = "ONE_BTC_FIXTURE_REUSED_WITH_SHIFTED_DATES_AND_INSTRUMENT_LABELS"
PHASES = (
    "generation", "counting", "loading_and_validation",
    "sorting_and_membership_validation", "kernel_and_adapter_matrix",
    "reporting_and_serialization",
)
LIMITATIONS = [
    "Synthetic inputs only; no historical source access or transfer.",
    "One generated BTC fixture is reused for both instrument labels and all dates.",
    "This is not 48 independently generated or loaded instrument-day corpora.",
    "Constant synthetic prices and quantities do not reproduce historical distributions.",
    "Empty or invalid descriptive cells remain explicit in the generated report.",
    "Compression NONE differs from potentially compressed historical files.",
    "RSS and phase peaks are process-lifetime high-water marks.",
    "Peak includes generation, membership checks, kernel, adapter and serialization.",
    "Free-space reserve is cooperative, not reserved storage.",
    "Fixtures and failed attempts are retained; no automatic cleanup.",
    "The serialized synthetic report is hashed and discarded, not published.",
    "No general memory-safety, scientific-readiness or historical execution approval.",
]


def hashes():
    folder = Path(__file__).parent
    return {
        **fixture.hashes(),
        **{
            key: hashlib.sha256((folder / name).read_bytes()).hexdigest()
            for key, name in (
                ("combined_profiler_sha256", "pi5_combined_profiler.py"),
                ("integration_sha256", "time_conditioning_synthetic_integration.py"),
                ("reporting_sha256", "time_conditioning_descriptive.py"),
            )
        },
    }


def measure(rows, attempt, *, files_per_partition=fixture.FILES_PER_PARTITION):
    """Small fixtures may be used by tests; production CLI fixes both scales."""
    base.require(type(rows) is int and 0 < rows <= max(base.ROW_COUNTS),
                 "Invalid synthetic row count")
    started = time.monotonic()
    deadline = started + base.RUNTIME
    phases, peaks = {}, {}

    def checkpoint(name, phase_started):
        fixture.tick(deadline)
        phases[name] = time.monotonic() - phase_started
        peaks[name] = base.peak_rss()

    attempt = Path(attempt)
    root = attempt / "synthetic-trades"
    phase_started = time.monotonic()
    generated = fixture.build_fixture(
        root, rows, files_per_partition=files_per_partition, deadline=deadline
    )
    checkpoint("generation", phase_started)

    import numpy as np
    import pyarrow as pa
    from L1_CORE.market_data_platform.research import (
        run_trade_flow_vs_momentum_screen as runner,
        trade_flow_vs_momentum_screen as kernel,
        time_conditioning_synthetic_integration as adapter,
        time_conditioning_descriptive as reporting,
    )

    original_root = runner.CANONICAL_TRADES_ROOT
    original_read = runner.pq.read_table
    reads = 0

    def read_synthetic(path, *args, **kwargs):
        nonlocal reads
        resolved = Path(path).resolve(strict=True)
        base.require(resolved.is_relative_to(root.resolve(strict=True)),
                     "Read outside generated fixture")
        fixture.tick(deadline)
        reads += 1
        return original_read(path, *args, **kwargs)

    try:
        runner.CANONICAL_TRADES_ROOT = root
        runner.pq.read_table = read_synthetic
        with contextlib.redirect_stdout(sys.stderr):
            partitions = runner._resolve_source_partitions(fixture.TARGET_DATE)
            base.require(
                [day for day, _ in partitions] == list(fixture.DATES)
                and all(directory.parent == root for _, directory in partitions),
                "Unexpected synthetic partitions",
            )
            start, end = runner._day_bounds_ms(fixture.TARGET_DATE)
            phase_started = time.monotonic()
            counted, _ = runner.count_target_rows(
                partitions, "BTC-USD", start, end
            )
            base.require(counted == rows, "Selected-row count mismatch")
            checkpoint("counting", phase_started)

            phase_started = time.monotonic()
            trade_time, trade_id, price, quantity, maker = runner.load_instrument_day(
                partitions, "BTC-USD", start, end, counted
            )
            runner.validate_day_integrity(
                trade_time, price, quantity, start, end
            )
            checkpoint("loading_and_validation", phase_started)
    finally:
        runner.CANONICAL_TRADES_ROOT = original_root
        runner.pq.read_table = original_read

    base.require(reads == generated["fixture_files"] * 2,
                 "Unexpected synthetic read-call count")
    phase_started = time.monotonic()
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
    kernel.validate_sorted_arrays(trade_time, trade_id, price, quantity, maker)
    base.require(
        np.array_equal(np.sort(trade_id), np.arange(rows, dtype=np.int64)),
        "Selected-ID membership mismatch",
    )
    checkpoint("sorting_and_membership_validation", phase_started)

    phase_started = time.monotonic()
    records = []
    kernel_calls = 0
    for day in reporting.DATES:
        day_start, _ = runner._day_bounds_ms(day)
        shifted = trade_time + (day_start - start)
        for instrument in reporting.INSTRUMENTS:
            fixture.tick(deadline)
            screen = kernel.compute_screen(
                shifted, trade_id, price, quantity, maker
            )
            kernel_calls += 1
            records.append(adapter.summarize_screen(
                screen, instrument, day,
                input_classification="SYNTHETIC_DEVELOPMENT",
            ))
            del screen
        del shifted
    checkpoint("kernel_and_adapter_matrix", phase_started)

    phase_started = time.monotonic()
    report = reporting.build_report(
        records, input_classification="SYNTHETIC_DEVELOPMENT"
    )
    raw = reporting.encode_report(report)
    report_bytes = len(raw)
    report_digest = hashlib.sha256(raw).hexdigest()
    valid_pairs = {
        mechanism: {
            horizon: report["mechanisms"][mechanism][horizon]["valid_date_pairs"]
            for horizon in reporting.HORIZONS
        }
        for mechanism in reporting.MECHANISMS
    }
    checkpoint("reporting_and_serialization", phase_started)
    return {
        "version": VERSION,
        "stage": "synthetic_loader_kernel_adapter_reporting",
        "row_count": rows,
        "loaded_target_rows": len(trade_time),
        "input_array_bytes": sum(
            array.nbytes for array in (trade_time, trade_id, price, quantity, maker)
        ),
        "fixture_root": str(root),
        **generated,
        "synthetic_read_calls": reads,
        "selected_ids_verified": True,
        "replication_policy": POLICY,
        "kernel_calls": kernel_calls,
        "instrument_day_count": len(records),
        "report_classification": report["classification"],
        "report_bytes": report_bytes,
        "report_sha256": report_digest,
        "valid_date_pairs": valid_pairs,
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
    def pairs(items):
        result = {}
        for key, value in items:
            base.require(key not in result, "Duplicate worker JSON key")
            result[key] = value
        return result

    def constant(token):
        raise base.ProfileError("Nonfinite worker JSON constant")

    base.require(len(raw) <= base.MAX_JSON, "Oversized worker result")
    record = json.loads(
        raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
    )
    base.require(type(record) is dict, "Worker record must be an object")
    expected = {
        "version": VERSION,
        "stage": "synthetic_loader_kernel_adapter_reporting",
        "row_count": rows, "loaded_target_rows": rows,
        "input_array_bytes": rows * 33,
        "fixture_root": str(Path(attempt) / "synthetic-trades"),
        "fixture_files": 3 * fixture.FILES_PER_PARTITION,
        "fixture_rows": rows + 9 * fixture.FILES_PER_PARTITION,
        "control_rows": 9 * fixture.FILES_PER_PARTITION,
        "expected_selected_rows": rows, "compression": "NONE",
        "synthetic_read_calls": 6 * fixture.FILES_PER_PARTITION,
        "selected_ids_verified": True, "replication_policy": POLICY,
        "kernel_calls": 48, "instrument_day_count": 48,
        "report_classification": "COMPLETE_DESCRIPTIVE",
        **hashes(),
    }
    for key, value in expected.items():
        base.require(type(record.get(key)) is type(value) and record[key] == value,
                     "Worker identity mismatch: " + key)
    for key, maximum in (
        ("fixture_logical_bytes", fixture.MAX_FIXTURE_BYTES),
        ("report_bytes", 1024**2),
    ):
        base.require(type(record.get(key)) is int
                     and 0 < record[key] <= maximum,
                     "Invalid bounded byte count: " + key)
    digest = record.get("report_sha256")
    base.require(type(digest) is str and len(digest) == 64
                 and all(char in "0123456789abcdef" for char in digest),
                 "Invalid report digest")
    peak = record.get("peak_rss_bytes")
    base.require(type(peak) is int and peak > 0, "Invalid peak RSS")
    elapsed = record.get("elapsed_seconds")
    base.require(type(elapsed) in (int, float) and math.isfinite(elapsed)
                 and 0 <= elapsed <= base.RUNTIME, "Invalid elapsed time")
    phases = record.get("phase_seconds")
    peaks = record.get("phase_peak_rss_bytes")
    base.require(type(phases) is dict and set(phases) == set(PHASES)
                 and type(peaks) is dict and set(peaks) == set(PHASES),
                 "Invalid phase fields")
    previous = 0
    for phase in PHASES:
        value = phases[phase]
        observed = peaks[phase]
        base.require(type(value) in (int, float) and math.isfinite(value)
                     and 0 <= value <= elapsed, "Invalid phase runtime")
        base.require(type(observed) is int and previous <= observed <= peak
                     and observed > 0, "Invalid cumulative phase RSS")
        previous = observed
    valid = record.get("valid_date_pairs")
    base.require(type(valid) is dict and set(valid) == {"hour", "session"},
                 "Invalid mechanism summary")
    for values in valid.values():
        base.require(type(values) is dict and set(values) == {"5", "15", "30", "60"},
                     "Invalid horizon summary")
        base.require(all(type(value) is int and 0 <= value <= 24
                         for value in values.values()), "Invalid date-pair count")
    return record


def launch(rows, output_root):
    base.require(type(rows) is int and rows in base.ROW_COUNTS,
                 "Invalid production scale")
    output_fd = attempt_fd = None
    attempt = None
    published = False
    try:
        output_fd = base.open_directory(output_root)
        info = os.fstat(output_fd)
        base.require(info.st_uid == os.geteuid()
                     and stat.S_IMODE(info.st_mode) == 0o700,
                     "Output root must be operator-owned mode 0700")
        name = f"combined-{rows}--{uuid.uuid4()}"
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
        outcome = base.capture([
            sys.executable, "-B", "-m", MODULE,
            "_worker", str(rows), "--attempt", attempt,
        ], environment)
        base.require(outcome["error"] is None and outcome["exit_status"] == 0,
                     f'{outcome["error"]}; exit={outcome["exit_status"]}; '
                     f'stderr={outcome["stderr_tail"]}')
        measured = parse_result(outcome["stdout"], rows, attempt)
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=base.REPOSITORY,
            text=True, timeout=5,
        ).strip()
        record = {
            "state": "COMPLETE", "schema_version": 1, "version": VERSION,
            "attempt": attempt, "row_count": rows, "source_revision": revision,
            "address_space_limit_bytes": base.ADDRESS_SPACE,
            "worker_runtime_limit_seconds": base.RUNTIME,
            "worker_exit_status": outcome["exit_status"],
            "thread_environment": {
                name: environment[name] for name in base.THREAD_VARIABLES
            },
            "measurement": measured, "stderr_tail": outcome["stderr_tail"],
            "limitations": LIMITATIONS,
        }
        base.publish(attempt_fd, "complete.json", record)
        published = True
        return record
    except Exception as error:
        published = published or getattr(error, "published", False)
        secondary = getattr(error, "reporting_error", None)
        if attempt_fd is not None and not published:
            try:
                base.publish(attempt_fd, "failure.json", {
                    "state": "FAILED", "version": VERSION,
                    "attempt": attempt, "row_count": rows,
                    "error": str(error)[-4096:],
                })
            except Exception as reporting_error:
                secondary = repr(reporting_error)
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

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("profile", "_worker"))
    parser.add_argument("rows", type=int, choices=base.ROW_COUNTS)
    parser.add_argument("--attempt")
    args = parser.parse_args()
    try:
        base.require(socket.gethostname() == "liquid-pi5", "Expected Pi5")
        if args.operation == "_worker":
            base.require(args.attempt is not None, "Worker attempt required")
            attempt = Path(args.attempt)
            base.require(attempt.is_absolute() and ".." not in attempt.parts
                         and attempt.parent == ROOT,
                         "Worker attempt outside profiling root")
            base.configure_worker()
            result = measure(args.rows, attempt)
        else:
            base.require(args.attempt is None, "Parent chooses attempts")
            result = launch(args.rows, ROOT)
        print(base.encode(result).decode(), end="")
        return 0
    except Exception as error:
        print(base.encode({
            "classification": "PUBLICATION_DURABILITY_UNCERTAIN"
                if getattr(error, "published", False) else "FAILED",
            "error": str(error)[-4096:],
            "attempt": getattr(error, "attempt", None),
            "reporting_error": getattr(error, "reporting_error", None),
        }).decode(), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
