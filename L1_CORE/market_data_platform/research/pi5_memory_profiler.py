"""Synthetic array/sorting and actual-kernel profiling; no canonical inputs."""
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid

VERSION = "LRS3_PI5_PROFILER_V1"
STAGES = ("array_sorting", "calculation_kernel")
ROW_COUNTS = (678382, 1356764)
ADDRESS_SPACE = 2 * 1024**3
RUNTIME = 300.0
MAX_JSON = 65536
THREAD_VARIABLES = (
    "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "ARROW_NUM_THREADS",
)
ROOT = Path("/home/kristo/lrs3-pi5-profiling-v1")
REPOSITORY = Path(__file__).absolute().parents[3]
MODULE_NAME = "L1_CORE.market_data_platform.research.pi5_memory_profiler"
KERNEL_PATH = Path(__file__).with_name("trade_flow_vs_momentum_screen.py")


class ProfileError(RuntimeError):
    def __init__(self, message, *, attempt=None, reporting_error=None, published=False):
        super().__init__(message)
        self.attempt = attempt
        self.reporting_error = reporting_error
        self.published = published


def require(condition, message):
    if not condition:
        raise ProfileError(message)


def encode(value):
    raw = (json.dumps(
        value, sort_keys=True, indent=2, allow_nan=False
    ) + "\n").encode("utf-8")
    require(len(raw) <= MAX_JSON, "JSON output limit exceeded")
    return raw


def code_hashes():
    return {
        "profiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "kernel_sha256": hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest(),
    }


def peak_rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    require(sys.platform == "darwin" or sys.platform.startswith("linux"),
            "Unsupported RSS units")
    return int(value if sys.platform == "darwin" else value * 1024)


def configure_worker():
    require(socket.gethostname() == "liquid-pi5", "Expected Pi5 host liquid-pi5")
    require(sys.platform.startswith("linux"), "Production profiling requires Linux")
    for name in THREAD_VARIABLES:
        os.environ[name] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE, ADDRESS_SPACE))


def measure(stage, rows):
    """In-memory synthetic computation; each production call gets a fresh worker."""
    require(stage in STAGES and type(rows) is int and rows in ROW_COUNTS,
            "Invalid stage or row count")
    started = time.monotonic()
    import numpy as np
    from L1_CORE.market_data_platform.research.trade_flow_vs_momentum_screen import (
        compute_screen, validate_sorted_arrays,
    )

    rng = np.random.default_rng(42 + rows)
    trade_time = rng.integers(
        1_750_003_200_000, 1_750_089_600_000, size=rows, dtype=np.int64
    )
    trade_id = np.arange(rows, dtype=np.int64)
    price = rng.uniform(100.0, 101.0, size=rows)
    quantity = rng.uniform(0.001, 2.0, size=rows)
    maker = rng.integers(0, 2, size=rows, dtype=np.int8).astype(np.bool_)
    del rng
    before_sort = peak_rss()
    sort_started = time.monotonic()

    # Preserve the existing runner's allocation/replacement sequence.
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
    validate_sorted_arrays(trade_time, trade_id, price, quantity, maker)

    sorting_seconds = time.monotonic() - sort_started
    after_preparation = peak_rss()
    kernel_seconds = None
    samples = None
    if stage == "calculation_kernel":
        kernel_started = time.monotonic()
        result = compute_screen(trade_time, trade_id, price, quantity, maker)
        kernel_seconds = time.monotonic() - kernel_started
        samples = len(result["sample_trade_time"])
        require(samples == rows // 20, "Unexpected kernel sample count")
        # Outcomes remain synthetic and are not published as research evidence.
        require(all(len(value) == samples for value in result.values()),
                "Kernel output-length mismatch")

    return {
        "version": VERSION, "stage": stage, "row_count": rows,
        "elapsed_seconds": time.monotonic() - started,
        "sorting_seconds": sorting_seconds,
        "kernel_seconds": kernel_seconds,
        "peak_rss_bytes": peak_rss(),
        "before_sort_peak_rss_bytes": before_sort,
        "prepared_inputs_peak_rss_bytes": after_preparation,
        "input_array_bytes": int(sum(
            array.nbytes for array in (trade_time, trade_id, price, quantity, maker)
        )),
        "kernel_sample_count": samples,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        **code_hashes(),
    }


def open_directory(path):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "Unsafe directory path")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def publish(directory, name, record):
    """Exclusive linked publication; never overwrite an earlier record."""
    raw = encode(record)
    temporary = ".profile-" + uuid.uuid4().hex + ".tmp"
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600, dir_fd=directory,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory,
            follow_symlinks=False)
    try:
        os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)
    except Exception as error:
        raise ProfileError(
            "Record published; cleanup or directory durability uncertain",
            published=name == "complete.json", reporting_error=repr(error),
        ) from error


def terminate(child):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()


def capture(command, environment, timeout=RUNTIME):
    """Drain both pipes concurrently; cap stdout and retain only stderr's tail."""
    deadline = time.monotonic() + timeout
    child = subprocess.Popen(
        command, cwd=REPOSITORY, env=environment, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    failure = None
    try:
        for stream, name in ((child.stdout, "out"), (child.stderr, "err")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            require(remaining > 0, "Worker runtime limit exceeded")
            for key, _ in selector.select(min(remaining, 0.1)):
                block = os.read(key.fileobj.fileno(), 4096)
                if not block:
                    selector.unregister(key.fileobj)
                elif key.data == "out":
                    require(len(stdout) + len(block) <= MAX_JSON,
                            "Worker stdout limit exceeded")
                    stdout.extend(block)
                else:
                    stderr.extend(block)
                    del stderr[:-4096]
        remaining = deadline - time.monotonic()
        require(remaining > 0, "Worker runtime limit exceeded")
        try:
            child.wait(timeout=remaining)
        except subprocess.TimeoutExpired as error:
            raise ProfileError("Worker runtime limit exceeded") from error
    except BaseException as error:
        failure = error
        terminate(child)
    finally:
        selector.close()
        child.stdout.close()
        child.stderr.close()
    return {
        "exit_status": child.returncode,
        "stdout": bytes(stdout),
        "stderr_tail": bytes(stderr).decode("utf-8", errors="replace"),
        "error": None if failure is None else (
            type(failure).__name__ + ": " + str(failure)[:512]
        ),
    }


def worker_command(stage, rows):
    return [sys.executable, "-B", "-m", MODULE_NAME, "_worker", stage, str(rows)]


def parse_worker(raw, stage, rows):
    import math

    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate worker JSON key")
            value[key] = item
        return value

    def constant(token):
        raise ProfileError("Nonfinite worker JSON constant")

    require(len(raw) <= MAX_JSON, "Oversized worker JSON")
    record = json.loads(
        raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
    )
    require(type(record) is dict, "Worker result must be an object")
    require(
        record.get("version") == VERSION and record.get("stage") == stage
        and type(record.get("row_count")) is int and record["row_count"] == rows,
        "Worker identity mismatch",
    )
    for key, value in code_hashes().items():
        require(record.get(key) == value, "Worker source hash mismatch")
    for field in (
        "peak_rss_bytes", "before_sort_peak_rss_bytes",
        "prepared_inputs_peak_rss_bytes", "input_array_bytes",
    ):
        require(type(record.get(field)) is int and record[field] > 0,
                "Invalid memory measurement")
    require(record["input_array_bytes"] == rows * 33, "Input-array size mismatch")
    for field in ("elapsed_seconds", "sorting_seconds"):
        value = record.get(field)
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "Invalid runtime measurement")
    if stage == "calculation_kernel":
        value = record.get("kernel_seconds")
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "Invalid kernel runtime")
        require(type(record.get("kernel_sample_count")) is int
                and record["kernel_sample_count"] == rows // 20,
                "Invalid sample count")
    else:
        require(record.get("kernel_seconds") is None
                and record.get("kernel_sample_count") is None,
                "Unexpected kernel results in sorting stage")
    return record


def launch(stage, rows, output_root):
    require(stage in STAGES and type(rows) is int and rows in ROW_COUNTS,
            "Invalid profiling configuration")
    output_fd = attempt_fd = None
    attempt = None
    published = False
    try:
        output_fd = open_directory(output_root)
        info = os.fstat(output_fd)
        require(info.st_uid == os.geteuid()
                and stat.S_IMODE(info.st_mode) == 0o700,
                "Output root must be operator-owned mode 0700")
        name = f"{stage}-{rows}--{uuid.uuid4()}"
        os.mkdir(name, 0o700, dir_fd=output_fd)
        attempt = str(Path(output_root) / name)
        os.fsync(output_fd)
        attempt_fd = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output_fd
        )
        publish(attempt_fd, "incomplete.json", {
            "state": "INCOMPLETE", "version": VERSION,
            "stage": stage, "row_count": rows, "attempt": attempt,
        })
        environment = dict(os.environ)
        environment.pop("PYTHONHOME", None)
        environment["PYTHONPATH"] = str(REPOSITORY)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        for variable in THREAD_VARIABLES:
            environment[variable] = "1"
        started = time.monotonic()
        outcome = capture(worker_command(stage, rows), environment)
        require(outcome["error"] is None,
                (outcome["error"] or "") + "; stderr: " + outcome["stderr_tail"])
        require(outcome["exit_status"] == 0,
                f'Worker exit {outcome["exit_status"]}; stderr: {outcome["stderr_tail"]}')
        measured = parse_worker(outcome["stdout"], stage, rows)
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True, timeout=5
        ).strip()
        record = {
            "state": "COMPLETE", "schema_version": 1, "version": VERSION,
            "attempt": attempt, "stage": stage, "row_count": rows,
            "worker_exit_status": outcome["exit_status"],
            "worker_wall_seconds": time.monotonic() - started,
            "address_space_limit_bytes": ADDRESS_SPACE,
            "thread_environment": {key: environment[key] for key in THREAD_VARIABLES},
            "source_revision": revision, "measurement": measured,
            "stderr_tail": outcome["stderr_tail"],
            "limitations": [
                "Synthetic inputs only; no canonical files or data transfer.",
                "RSS is the worker process lifetime high-water mark.",
                "Kernel-process RSS includes input generation and sorting.",
                "Sorting stage excludes Parquet loading and file-list allocations.",
                "These distributions do not reproduce every real-data allocation.",
                "Reporting stage is not implemented or measured.",
                "No production memory-safety or scientific-readiness conclusion.",
            ],
        }
        publish(attempt_fd, "complete.json", record)
        published = True
        return record
    except Exception as error:
        secondary = getattr(error, "reporting_error", None)
        published = published or getattr(error, "published", False)
        if attempt_fd is not None and not published:
            try:
                publish(attempt_fd, "failure.json", {
                    "state": "FAILED", "version": VERSION,
                    "stage": stage, "row_count": rows, "attempt": attempt,
                    "error": str(error)[-4096:],
                })
            except Exception as reporting:
                secondary = repr(reporting)
        raise ProfileError(
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
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("rows", type=int, choices=ROW_COUNTS)
    args = parser.parse_args()
    require(socket.gethostname() == "liquid-pi5", "Expected Pi5 host liquid-pi5")
    try:
        if args.operation == "_worker":
            configure_worker()
            result = measure(args.stage, args.rows)
        else:
            result = launch(args.stage, args.rows, ROOT)
        print(encode(result).decode(), end="")
        return 0
    except Exception as error:
        print(encode({
            "classification": "FAILED" if not getattr(error, "published", False)
                              else "PUBLICATION_DURABILITY_UNCERTAIN",
            "error": str(error)[-4096:],
            "attempt": getattr(error, "attempt", None),
            "reporting_error": getattr(error, "reporting_error", None),
        }).decode(), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
