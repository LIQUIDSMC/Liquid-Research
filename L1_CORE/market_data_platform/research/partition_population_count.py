"""Bounded two-column capacity counting; no research outcomes or transfers.

One complete source partition per attempt. Callers must enforce the approved
256 MiB process address-space cap and external termination grace on Pi3.
Successful records describe sequential observations, not an atomic snapshot.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import time
import uuid

VERSION = "LRS3_PARTITION_COUNT_V1"
MAX_RECORD_BYTES = 65536
LIMITS = {
    "max_files": 12000,
    "max_logical_bytes": 80 * 1024**2,
    "max_read_bytes": 80 * 1024**2,
    "max_rows": 2_000_000,
    "max_runtime_seconds": 300.0,
}
SOURCE_DATES = tuple(
    [(dt.date(2026, 7, 21) + dt.timedelta(days=i)).isoformat() for i in range(21)]
    + [(dt.date(2026, 8, 25) + dt.timedelta(days=i)).isoformat() for i in range(7)]
)
RESEARCH_DATES = tuple(
    [(dt.date(2026, 7, 22) + dt.timedelta(days=i)).isoformat() for i in range(19)]
    + [(dt.date(2026, 8, 26) + dt.timedelta(days=i)).isoformat() for i in range(5)]
)


class CountError(RuntimeError):
    def __init__(self, message, *, attempt=None, reporting_error=None, published=False):
        super().__init__(message)
        self.attempt = attempt
        self.reporting_error = reporting_error
        self.published = published


def require(condition, message):
    if not condition:
        raise CountError(message)


def signature(info):
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns, info.st_nlink,
    )


def encode(value):
    raw = (json.dumps(
        value, sort_keys=True, indent=2, allow_nan=False
    ) + "\n").encode("utf-8")
    require(len(raw) <= MAX_RECORD_BYTES, "Record size limit exceeded")
    return raw


def open_directory(path):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "Unsafe directory path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def valid_health(value):
    require(type(value) is dict and set(value) == {
        "ActiveState", "SubState", "MainPID", "NRestarts"
    }, "Invalid collector observation")
    require(
        value["ActiveState"] == "active"
        and value["SubState"] == "running"
        and type(value["MainPID"]) is str
        and value["MainPID"].isdigit()
        and int(value["MainPID"]) > 0
        and type(value["NRestarts"]) is str
        and value["NRestarts"].isdigit(),
        "Collector is not active/running or observation is invalid",
    )
    return dict(value)


class Budget:
    def __init__(self, limits, clock):
        self.limits = dict(LIMITS if limits is None else limits)
        require(set(self.limits) == set(LIMITS), "Invalid limits")
        for key, maximum in LIMITS.items():
            value = self.limits[key]
            if key == "max_runtime_seconds":
                import math
                require(
                    type(value) in (int, float) and math.isfinite(value)
                    and 0 < value <= maximum, "Invalid runtime limit",
                )
            else:
                require(
                    type(value) is int and 0 < value <= maximum,
                    f"Invalid limit: {key}",
                )
        self.clock = clock
        self.started = clock()
        self.deadline = self.started + self.limits["max_runtime_seconds"]
        self.read_bytes = 0
        self.rows = 0

    def tick(self, reserve=0):
        require(self.clock() < self.deadline - reserve, "Runtime limit exceeded")

    def fetch(self, descriptor, offset, length):
        self.tick(6)
        require(
            type(offset) is int and type(length) is int
            and offset >= 0 and length >= 0,
            "Invalid read range",
        )
        require(
            self.read_bytes + length <= self.limits["max_read_bytes"],
            "Requested-read limit exceeded",
        )
        self.read_bytes += length
        raw = os.pread(descriptor, length, offset)
        require(len(raw) == length, "Short source read")
        return raw


def selected_image(descriptor, size, budget):
    """Only envelope, footer and approved column chunks are fetched."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    require(12 <= size <= 1024**2, "File outside bounded reader size allowance")
    header = budget.fetch(descriptor, 0, 4)
    tail = budget.fetch(descriptor, size - 8, 8)
    require(header == b"PAR1" and tail[4:] == b"PAR1", "Invalid envelope")
    length = struct.unpack("<I", tail[:4])[0]
    require(0 < length <= size - 12, "Invalid footer length")
    footer_start = size - 8 - length
    footer = budget.fetch(descriptor, footer_start, length)
    options = {
        "thrift_string_size_limit": 1024**2,
        "thrift_container_size_limit": 100_000,
    }
    with pq.ParquetFile(pa.BufferReader(header + footer + tail), **options) as parquet:
        metadata = parquet.metadata
    schema = metadata.schema.to_arrow_schema()
    require(
        schema.names.count("instrument_id") == 1
        and schema.names.count("trade_time") == 1
        and schema.field("instrument_id").type == pa.string()
        and schema.field("trade_time").type == pa.int64(),
        "Selected-column schema mismatch",
    )
    require(
        metadata.num_rows > 0 and metadata.num_row_groups > 0
        and budget.rows + metadata.num_rows <= budget.limits["max_rows"],
        "Invalid footer rows or decoded-row limit exceeded",
    )
    ranges = []
    selected = []
    for index in range(metadata.num_row_groups):
        budget.tick()
        group = metadata.row_group(index)
        for column_index in range(group.num_columns):
            column = group.column(column_index)
            require(not column.file_path, "External column file rejected")
            offsets = [column.data_page_offset]
            if column.has_dictionary_page:
                offsets.append(column.dictionary_page_offset)
            start = min(offsets)
            end = start + column.total_compressed_size
            require(4 <= start < end <= footer_start, "Invalid column bounds")
            ranges.append((start, end))
            if column.path_in_schema in {"instrument_id", "trade_time"}:
                selected.append((start, end))
    ordered = sorted(ranges)
    require(
        all(right[0] >= left[1] for left, right in zip(ordered, ordered[1:])),
        "Overlapping column chunks rejected",
    )
    image = bytearray(size)
    image[:4], image[footer_start:-8], image[-8:] = header, footer, tail
    for start, end in selected:
        image[start:end] = budget.fetch(descriptor, start, end - start)
    return image, metadata.num_rows


def publish(attempt_fd, record, *, before_link=None):
    """Publish a new status name without overwrite; retain failed temp files."""
    raw = encode(record)
    temporary = ".record-" + uuid.uuid4().hex + ".tmp"
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600, dir_fd=attempt_fd,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    final = "complete.json" if record["state"] == "COMPLETE" else "incomplete.json"
    if before_link is not None:
        before_link()
    os.link(
        temporary, final,
        src_dir_fd=attempt_fd, dst_dir_fd=attempt_fd,
        follow_symlinks=False,
    )
    # The linked record is now published. A later durability failure cannot undo it.
    try:
        os.unlink(temporary, dir_fd=attempt_fd)
        os.fsync(attempt_fd)
    except Exception as error:
        raise CountError(
            "Record published; cleanup or directory durability uncertain",
            reporting_error=repr(error),
            published=record["state"] == "COMPLETE",
        ) from error


def count_partition(source_root, output_root, partition_date, *, health,
                    limits=None, clock=time.monotonic):
    """Count one approved partition; source/output roots must be disjoint.

    health(remaining_seconds) must return a bounded collector observation.
    No record is a cryptographically authenticated service attestation.
    """
    # Validate the entire permitted date policy before directory access.
    require(
        len(SOURCE_DATES) == 28 and len(set(SOURCE_DATES)) == 28
        and all(day < "2026-09-04" for day in SOURCE_DATES),
        "Invalid source-date policy",
    )
    require(type(partition_date) is str and partition_date in SOURCE_DATES,
            "Partition outside approved scope")
    source_root, output_root = Path(source_root), Path(output_root)
    require(
        source_root.is_absolute() and output_root.is_absolute()
        and ".." not in source_root.parts and ".." not in output_root.parts,
        "Unsafe roots",
    )
    require(
        source_root != output_root
        and source_root not in output_root.parents
        and output_root not in source_root.parents,
        "Overlapping roots",
    )
    budget = Budget(limits, clock)
    source_fd = output_fd = attempt_fd = partition_fd = None
    attempt = None
    published = False
    before = after = None
    try:
        output_fd = open_directory(output_root)
        info = os.fstat(output_fd)
        require(
            info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
            "Output root must be operator-owned mode 0700",
        )
        attempt_name = f"date={partition_date}--{uuid.uuid4()}"
        os.mkdir(attempt_name, 0o700, dir_fd=output_fd)
        os.fsync(output_fd)
        attempt = str(output_root / attempt_name)
        attempt_fd = os.open(
            attempt_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=output_fd,
        )
        initial_record = {
            "schema_version": 1, "state": "INCOMPLETE",
            "reader_version": VERSION, "partition_date": partition_date,
            "attempt": attempt,
        }
        publish(attempt_fd, initial_record)
        budget.tick()
        before = valid_health(health(max(0.0, budget.deadline - clock())))
        budget.tick()

        budget.tick(6)
        source_fd = open_directory(source_root)
        partition_name = "date=" + partition_date
        partition_fd = os.open(
            partition_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=source_fd,
        )
        directory_before = os.fstat(partition_fd)
        counts = {
            day: {"BTC-USD": 0, "ETH-USD": 0}
            for day in RESEARCH_DATES
            if abs((dt.date.fromisoformat(day)
                    - dt.date.fromisoformat(partition_date)).days) <= 1
        }
        epoch = dt.date(1970, 1, 1)
        day_keys = {(dt.date.fromisoformat(day) - epoch).days: day for day in counts}
        files = logical = linked = excluded = 0
        metadata_digest = hashlib.sha256()
        import pyarrow as pa
        import pyarrow.parquet as pq

        with os.scandir(partition_fd) as children:
            for child in children:
                budget.tick(6)
                files += 1
                require(files <= budget.limits["max_files"], "File-count limit exceeded")
                name = child.name
                require(
                    len(name) == 44 and name.endswith(".parquet")
                    and str(uuid.UUID(name[:-8])) + ".parquet" == name,
                    "Unexpected partition entry name",
                )
                info = child.stat(follow_symlinks=False)
                require(
                    stat.S_ISREG(info.st_mode) and info.st_nlink >= 1,
                    "Nonregular source entry",
                )
                logical += info.st_size
                require(logical <= budget.limits["max_logical_bytes"],
                        "Logical-byte limit exceeded")
                descriptor = os.open(
                    name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=partition_fd,
                )
                try:
                    require(signature(os.fstat(descriptor)) == signature(info),
                            "Descriptor identity mismatch")
                    image, expected_rows = selected_image(descriptor, info.st_size, budget)
                    decoded = 0
                    with pq.ParquetFile(
                        pa.BufferReader(image),
                        thrift_string_size_limit=1024**2,
                        thrift_container_size_limit=100_000,
                    ) as parquet:
                        for batch in parquet.iter_batches(
                            batch_size=8192,
                            columns=["instrument_id", "trade_time"],
                            use_threads=False,
                        ):
                            budget.tick(6)
                            budget.rows += batch.num_rows
                            decoded += batch.num_rows
                            require(budget.rows <= budget.limits["max_rows"],
                                    "Decoded-row limit exceeded")
                            values = batch.to_pydict()
                            for instrument, timestamp in zip(
                                values["instrument_id"], values["trade_time"]
                            ):
                                require(
                                    instrument in {"BTC-USD", "ETH-USD"}
                                    and type(timestamp) is int,
                                    "Null or invalid selected-column value",
                                )
                                day = day_keys.get(timestamp // 86_400_000)
                                if day is None:
                                    excluded += 1
                                else:
                                    counts[day][instrument] += 1
                    require(decoded == expected_rows, "Decoded/footer count mismatch")
                    require(signature(os.fstat(descriptor)) == signature(info),
                            "Source changed during read")
                    require(signature(os.stat(
                        name, dir_fd=partition_fd, follow_symlinks=False
                    )) == signature(info), "Source pathname changed")
                    metadata_digest.update(
                        json.dumps([name, signature(info)], separators=(",", ":")).encode()
                        + b"\n"
                    )
                finally:
                    os.close(descriptor)
                linked += int(info.st_nlink > 1)

        require(files > 0, "Required partition is empty")
        require(
            signature(directory_before) == signature(os.fstat(partition_fd))
            == signature(os.stat(
                partition_name, dir_fd=source_fd, follow_symlinks=False
            )), "Partition directory changed",
        )
        budget.tick()
        after = valid_health(health(max(0.0, budget.deadline - clock())))
        require(before == after, "Collector properties changed")
        budget.tick()
        record = {
            "schema_version": 1, "state": "COMPLETE",
            "reader_version": VERSION,
            "reader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_root": str(source_root), "partition_date": partition_date,
            "attempt": attempt, "limits": budget.limits,
            "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "files": files, "logical_bytes": logical,
            "requested_source_bytes": budget.read_bytes,
            "decoded_rows": budget.rows,
            "multiply_linked_paths": linked,
            "instrument_day_counts": counts, "excluded_rows": excluded,
            "observed_metadata_stream_sha256": metadata_digest.hexdigest(),
            "collector_before": before, "collector_after": after,
            "elapsed_seconds": clock() - budget.started,
            "limitations": [
                "Sequential observations, not an atomic snapshot.",
                "Metadata-stream digest is not a full payload digest.",
                "Collector observations do not prove zero dropped events.",
                "No price/outcome chunks requested; no analytical kernels.",
                "Hard-link provenance and transfer eligibility remain unresolved.",
                "Per-process memory limits must be enforced by the launcher.",
            ],
        }
        publish(attempt_fd, record, before_link=budget.tick)
        published = True
        return record
    except Exception as error:
        reporting_error = None
        published = published or getattr(error, "published", False)
        if attempt_fd is not None and not published:
            postcheck_error = None
            if before is not None and after is None:
                try:
                    remaining = budget.deadline - clock()
                    require(remaining > 0, "No remaining postcheck budget")
                    after = valid_health(health(min(5.0, remaining)))
                except Exception as secondary:
                    postcheck_error = type(secondary).__name__
            try:
                failure = {
                    "schema_version": 1, "state": "FAILED",
                    "reader_version": VERSION, "partition_date": partition_date,
                    "attempt": attempt, "error": str(error)[:512],
                    "requested_source_bytes": budget.read_bytes,
                    "collector_before": before,
                    "collector_after": after,
                    "collector_properties_match": (
                        before == after if before is not None and after is not None
                        else None
                    ),
                    "collector_postcheck_error": postcheck_error,
                }
                # Separate exclusive error record; initial incomplete record stays intact.
                raw = encode(failure)
                descriptor = os.open(
                    "failure.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600, dir_fd=attempt_fd,
                )
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.fsync(attempt_fd)
            except Exception as secondary:
                reporting_error = repr(secondary)
        raise CountError(
            str(error), attempt=attempt,
            reporting_error=reporting_error or getattr(error, "reporting_error", None),
            published=published,
        ) from error
    finally:
        for descriptor in (partition_fd, source_fd, attempt_fd, output_fd):
            if descriptor is not None:
                os.close(descriptor)


PRODUCTION_SOURCE = Path(
    "/mnt/lrs001/data/market_data_platform/canonical/trades"
)
PRODUCTION_RECORDS = Path("/home/kristo/lrs3-capacity-counts-v1")


def collector_health(remaining_seconds):
    """Bounded observation; no service mutations."""
    import subprocess

    require(remaining_seconds > 0, "No collector-observation budget")
    names = ("ActiveState", "SubState", "MainPID", "NRestarts")
    raw = subprocess.check_output(
        ["systemctl", "show", "liquid-research-collector.service", "--no-pager",
         *[item for name in names for item in ("-p", name)]],
        timeout=min(5.0, remaining_seconds),
    )
    require(len(raw) <= 4096, "Collector output limit exceeded")
    return valid_health(dict(
        line.split("=", 1) for line in raw.decode("utf-8").splitlines()
    ))


def configure_worker():
    """Set limits before any PyArrow import in this separate worker."""
    import resource
    import socket

    require(socket.gethostname() == "liquid-pi", "Expected Pi3 host liquid-pi")
    for name in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "ARROW_NUM_THREADS",
    ):
        os.environ[name] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    cap = 256 * 1024**2
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def launch_partition(partition_date):
    """One worker, hard wall-clock cap, two-second TERM grace, then KILL/reap."""
    import signal
    import socket
    import subprocess
    import sys

    require(socket.gethostname() == "liquid-pi", "Expected Pi3 host liquid-pi")
    require(partition_date in SOURCE_DATES, "Partition outside approved scope")
    environment = dict(os.environ)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "ARROW_NUM_THREADS",
    ):
        environment[name] = "1"
    child = subprocess.Popen(
        [sys.executable, "-B", "-m",
         "L1_CORE.market_data_platform.research.partition_population_count",
         "_worker", partition_date],
        env=environment, start_new_session=True,
    )
    try:
        return child.wait(timeout=LIMITS["max_runtime_seconds"])
    except subprocess.TimeoutExpired:
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
        print(encode({
            "classification": "INCOMPLETE",
            "partition_date": partition_date,
            "error": "Worker runtime limit; retained attempts require inspection.",
            "limitations": (
                "A completion record may have committed before termination. "
                "Inspect and validate records; no automatic retry or downgrade."
            ),
        }).decode(), end="")
        return 1



COMPLETE_FIELDS = {
    "schema_version", "state", "reader_version", "reader_sha256",
    "source_root", "partition_date", "attempt", "limits", "completed_utc",
    "files", "logical_bytes", "requested_source_bytes", "decoded_rows",
    "multiply_linked_paths", "instrument_day_counts", "excluded_rows",
    "observed_metadata_stream_sha256", "collector_before", "collector_after",
    "elapsed_seconds", "limitations",
}


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _json_integer(token):
    require(len(token.lstrip("-")) <= 20, "Oversized JSON integer")
    return int(token)


def _reject_constant(token):
    raise CountError("Nonfinite JSON constant rejected")


def _bounded_json(raw):
    text = raw.decode("utf-8")
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            require(depth <= 32, "JSON nesting limit exceeded")
        elif character in "]}":
            depth -= 1
    return json.loads(
        text, object_pairs_hook=_unique_pairs, parse_int=_json_integer,
        parse_constant=_reject_constant,
    )


def _read_complete(path):
    path = Path(path)
    require(
        path.is_absolute() and ".." not in path.parts
        and path.name == "complete.json" and len(str(path)) <= 4096,
        "Invalid completion-record path",
    )
    directory_fd = open_directory(path.parent)
    descriptor = None
    try:
        directory_info = os.fstat(directory_fd)
        require(
            directory_info.st_uid == os.geteuid()
            and stat.S_IMODE(directory_info.st_mode) == 0o700,
            "Unsafe attempt directory",
        )
        try:
            os.stat("failure.json", dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CountError("Attempt also contains a failure record")
        descriptor = os.open(
            "complete.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
        before = os.fstat(descriptor)
        require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and before.st_uid == os.geteuid()
            and stat.S_IMODE(before.st_mode) == 0o600
            and 0 < before.st_size <= MAX_RECORD_BYTES,
            "Unsafe or oversized completion record",
        )
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(MAX_RECORD_BYTES + 1)
        require(
            len(raw) == before.st_size
            and signature(before) == signature(os.fstat(descriptor))
            == signature(os.stat(
                "complete.json", dir_fd=directory_fd, follow_symlinks=False
            )),
            "Completion record changed during read",
        )
        return _bounded_json(raw), hashlib.sha256(raw).hexdigest()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory_fd)


def combine_records(paths, *, expected_source_root=PRODUCTION_SOURCE):
    """Combine exactly one complete record per approved partition; write nothing.

    Records are operator-controlled local evidence, not authenticated claims.
    Matching records cannot establish unchanged source content between attempts.
    """
    import math
    import re

    require(type(paths) in (list, tuple) and len(paths) == 28,
            "Exactly 28 completion records required")
    paths = [Path(path) for path in paths]
    require(len(set(paths)) == 28, "Duplicate completion-record paths")
    reader_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    expected_source_root = str(expected_source_root)
    totals = {
        day: {"BTC-USD": 0, "ETH-USD": 0} for day in RESEARCH_DATES
    }
    seen = set()
    config = record_root = None
    references = []
    files = logical = read_bytes = rows = excluded = linked = 0
    observations = []

    def integer(value, minimum, maximum, label):
        require(type(value) is int and minimum <= value <= maximum,
                f"Invalid record integer: {label}")
        return value

    for path in paths:
        record, digest = _read_complete(path)
        require(type(record) is dict and set(record) == COMPLETE_FIELDS,
                "Completion-record fields mismatch")
        require(
            type(record["schema_version"]) is int
            and record["schema_version"] == 1
            and record["state"] == "COMPLETE"
            and record["reader_version"] == VERSION
            and record["reader_sha256"] == reader_digest,
            "Incomplete or incompatible reader record",
        )
        day = record["partition_date"]
        require(type(day) is str and day in SOURCE_DATES and day not in seen,
                "Duplicate or out-of-scope partition")
        require(record["attempt"] == str(path.parent), "Attempt/path mismatch")
        prefix = "date=" + day + "--"
        require(path.parent.name.startswith(prefix), "Attempt/date mismatch")
        suffix = path.parent.name[len(prefix):]
        require(str(uuid.UUID(suffix)) == suffix, "Invalid attempt UUID")
        require(record["source_root"] == expected_source_root,
                "Source-root mismatch")
        parent = path.parent.parent
        root_fd = open_directory(parent)
        try:
            root_info = os.fstat(root_fd)
            require(
                root_info.st_uid == os.geteuid()
                and stat.S_IMODE(root_info.st_mode) == 0o700,
                "Unsafe records root",
            )
        finally:
            os.close(root_fd)
        if record_root is None:
            record_root = parent
        require(parent == record_root, "Mixed records roots")
        require(type(record["limits"]) is dict, "Invalid recorded limits")
        checked_limits = Budget(record["limits"], time.monotonic).limits
        fingerprint = json.dumps(checked_limits, sort_keys=True, allow_nan=False)
        if config is None:
            config = fingerprint
        require(fingerprint == config, "Mixed limit configurations")

        nfiles = integer(record["files"], 1, checked_limits["max_files"], "files")
        nbytes = integer(
            record["logical_bytes"], 12 * nfiles,
            checked_limits["max_logical_bytes"], "logical bytes",
        )
        nreads = integer(
            record["requested_source_bytes"], 1,
            checked_limits["max_read_bytes"], "read bytes",
        )
        nrows = integer(
            record["decoded_rows"], 1, checked_limits["max_rows"], "rows"
        )
        nlinked = integer(record["multiply_linked_paths"], 0, nfiles, "links")
        nexcluded = integer(record["excluded_rows"], 0, nrows, "excluded rows")
        elapsed = record["elapsed_seconds"]
        require(
            type(elapsed) in (int, float) and math.isfinite(elapsed)
            and 0 <= elapsed <= checked_limits["max_runtime_seconds"],
            "Invalid recorded runtime",
        )
        require(
            type(record["completed_utc"]) is str
            and len(record["completed_utc"]) <= 64,
            "Invalid completion timestamp",
        )
        stamp = dt.datetime.fromisoformat(record["completed_utc"])
        require(stamp.utcoffset() == dt.timedelta(0), "Completion time must be UTC")
        require(
            type(record["observed_metadata_stream_sha256"]) is str
            and re.fullmatch("[0-9a-f]{64}", record["observed_metadata_stream_sha256"])
            is not None, "Invalid metadata-stream digest",
        )
        require(
            valid_health(record["collector_before"])
            == valid_health(record["collector_after"]),
            "Collector observations disagree",
        )
        require(
            type(record["limitations"]) is list
            and all(type(item) is str for item in record["limitations"]),
            "Invalid limitations",
        )
        expected_days = {
            target for target in RESEARCH_DATES
            if abs((dt.date.fromisoformat(target) - dt.date.fromisoformat(day)).days) <= 1
        }
        counts = record["instrument_day_counts"]
        require(type(counts) is dict and set(counts) == expected_days,
                "Partition contribution dates mismatch")
        selected_rows = 0
        for target, instruments in counts.items():
            require(type(instruments) is dict and set(instruments) == {"BTC-USD", "ETH-USD"},
                    "Instrument-count fields mismatch")
            for instrument, count in instruments.items():
                integer(count, 0, nrows, "instrument count")
                totals[target][instrument] += count
                selected_rows += count
        require(selected_rows + nexcluded == nrows, "Row accounting mismatch")
        seen.add(day)
        files += nfiles
        logical += nbytes
        read_bytes += nreads
        rows += nrows
        excluded += nexcluded
        linked += nlinked
        references.append({
            "partition_date": day, "record_path": str(path),
            "record_sha256": digest,
        })
        observations.append(record["completed_utc"])

    require(seen == set(SOURCE_DATES), "Missing source partitions")
    require(
        all(value > 0 for instruments in totals.values() for value in instruments.values()),
        "Zero rows for a required instrument-day",
    )
    result = {
        "classification": "ALL_PARTITION_COUNTS_VALIDATED",
        "reader_version": VERSION, "reader_sha256": reader_digest,
        "source_root": expected_source_root,
        "limits": json.loads(config),
        "partition_count": 28, "instrument_day_count": 48,
        "total_files": files, "logical_source_bytes": logical,
        "requested_source_bytes": read_bytes, "decoded_rows": rows,
        "excluded_rows": excluded, "multiply_linked_paths": linked,
        "instrument_day_counts": totals,
        "completion_observations_utc": observations,
        "records": sorted(references, key=lambda item: item["partition_date"]),
        "limitations": [
            "Sequential partition measurements, not an atomic source snapshot.",
            "Record hashes bind local bytes, not independent authenticity.",
            "No source reread, source-content authentication, or transfer approval.",
            "No feed-completeness or analytical peak-memory guarantee.",
            "Collector observations do not establish uninterrupted collection.",
        ],
    }
    encode(result)
    return result

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="One-partition two-column capacity measurement; no outcomes."
    )
    parser.add_argument("operation", choices=("count", "_worker", "combine"))
    parser.add_argument("arguments", nargs="+")
    args = parser.parse_args()
    if args.operation == "combine":
        try:
            combined = combine_records(args.arguments)
        except Exception as error:
            print(encode({
                "classification": "AGGREGATION_REJECTED",
                "error": f"{type(error).__name__}: {str(error)[:512]}",
            }).decode(), end="")
            return 1
        print(encode(combined).decode(), end="")
        return 0
    if len(args.arguments) != 1 or args.arguments[0] not in SOURCE_DATES:
        parser.error("Count requires exactly one approved partition date.")
    partition_date = args.arguments[0]
    if args.operation == "count":
        return launch_partition(partition_date)
    configure_worker()
    try:
        record = count_partition(
            PRODUCTION_SOURCE, PRODUCTION_RECORDS, partition_date,
            health=collector_health,
        )
    except CountError as error:
        print(encode({
            "classification": "INCOMPLETE" if not error.published else
                              "PUBLICATION_DURABILITY_UNCERTAIN",
            "attempt": error.attempt,
            "published": error.published,
            "error": str(error)[:512],
            "reporting_error": error.reporting_error,
        }).decode(), end="")
        return 1
    print(encode(record).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
