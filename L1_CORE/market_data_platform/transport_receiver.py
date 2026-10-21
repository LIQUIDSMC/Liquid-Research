"""Mac-local synthetic subprocess receiver. No SSH or deployment support."""
import hashlib
import os
import selectors
import shutil
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from L1_CORE.market_data_platform import evidence_preservation as ep
from L1_CORE.market_data_platform import transport_protocol as tp


def _sync(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_status(attempt, request, state, error_code, publication, budget=None):
    record = {
        "schema_version": 1,
        "run_id": request["run_id"],
        "attempt_id": request["attempt_id"],
        "expected_manifest_sha256": request["expected_manifest_sha256"],
        "state": state,
        "error_code": error_code,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "published": state == "TRANSPORT_VERIFIED",
    }
    temporary = attempt / f".status.tmp.{uuid.uuid4().hex}"
    if budget:
        budget.remaining()
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(tp.encode_json(record))
        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    if budget:
        budget.remaining()
    os.replace(temporary, attempt / "status.json")
    if state == "TRANSPORT_VERIFIED":
        publication["published"] = True
    try:
        _sync(attempt)
    except OSError as exc:
        if publication["published"]:
            raise tp.TransportError(
                "PUBLICATION_DURABILITY_UNCERTAIN",
                "Success committed but directory synchronization failed",
                published=True,
            ) from exc
        raise


def _status(attempt, request, state, error_code, publication, budget=None):
    try:
        return _write_status(
            attempt, request, state, error_code, publication, budget
        )
    except OSError as exc:
        raise tp.TransportError(
            "TRANSPORT_CONTROL_IO_ERROR", "Control publication failed",
            published=publication["published"],
        ) from exc


def _destination(value):
    root = Path(value)
    tp.require(
        root.is_absolute() and str(root) == str(root.resolve()),
        "Destination must be canonical", "TRANSPORT_INVALID_ROOTS",
    )
    uid = os.getuid()
    for component in reversed((root,) + tuple(root.parents)):
        info = component.lstat()
        tp.require(
            stat.S_ISDIR(info.st_mode)
            and not stat.S_ISLNK(info.st_mode)
            and info.st_uid in {0, uid}
            and not info.st_mode & 0o022,
            "Unsafe destination ancestor", "TRANSPORT_INVALID_ROOTS",
        )
    info = root.stat()
    tp.require(
        info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700,
        "Destination must be operator-owned mode 0700",
        "TRANSPORT_INVALID_ROOTS",
    )
    return root


def _capacity(root, required, reserve):
    tp.require(
        shutil.disk_usage(root).free >= required + reserve,
        "Insufficient staging capacity", "TRANSPORT_RESOURCE_LIMIT",
    )


class _Child:
    """Bounded bidirectional pipe I/O with concurrent stderr draining."""

    def __init__(self, request, budget):
        self.budget = budget
        self.buffer = bytearray()
        self.diagnostics = bytearray()
        self.stdout_eof = False
        self.request = tp.encode_json(request, tp.MAX_REQUEST)
        self.sent = 0
        self.selector = selectors.DefaultSelector()
        checkout = Path(__file__).resolve().parents[2]
        self.process = subprocess.Popen(
            [
                sys.executable, "-m",
                "L1_CORE.market_data_platform.transport_sender",
            ],
            cwd=checkout,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        for pipe, event, label in (
            (self.process.stdin, selectors.EVENT_WRITE, "stdin"),
            (self.process.stdout, selectors.EVENT_READ, "stdout"),
            (self.process.stderr, selectors.EVENT_READ, "stderr"),
        ):
            os.set_blocking(pipe.fileno(), False)
            self.selector.register(pipe, event, label)

    def _close_pipe(self, pipe):
        try:
            self.selector.unregister(pipe)
        except KeyError:
            pass
        pipe.close()

    def pump(self):
        remaining = self.budget.remaining()
        for key, _ in self.selector.select(min(0.05, remaining)):
            pipe = key.fileobj
            label = key.data
            if label == "stdin":
                try:
                    count = os.write(pipe.fileno(), self.request[self.sent:])
                    self.sent += count
                except BrokenPipeError:
                    self._close_pipe(pipe)
                    continue
                if self.sent == len(self.request):
                    self._close_pipe(pipe)
            else:
                chunk = os.read(pipe.fileno(), 65536)
                if not chunk:
                    if label == "stdout":
                        self.stdout_eof = True
                    self._close_pipe(pipe)
                elif label == "stderr":
                    self.diagnostics.extend(chunk)
                    del self.diagnostics[:-tp.MAX_DIAGNOSTICS]
                else:
                    self.buffer.extend(chunk)
                    tp.require(
                        len(self.buffer) <= tp.MAX_JSON + 65544,
                        "Pipe buffer exceeded bound",
                        "TRANSPORT_RESOURCE_LIMIT",
                    )

    def exact(self, size, *, first=False):
        while len(self.buffer) < size:
            if self.stdout_eof:
                code = "TRANSPORT_IO_ERROR"
                if first and not self.buffer:
                    exit_code = self.wait_exit()
                    if exit_code != 0:
                        code = "TRANSPORT_CONNECTION_ERROR"
                raise tp.TransportError(code, "Sender stream ended early")
            self.pump()
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result

    def frame(self, *, first=False):
        kind, length = tp.PREFIX.unpack(self.exact(tp.PREFIX.size, first=first))
        tp.require(kind in range(tp.HEADER, tp.ERROR + 1), "Unknown frame type")
        maximum = tp.MAX_CHUNK if kind == tp.FILE_DATA else tp.MAX_JSON
        tp.require(0 < length <= maximum, "Invalid frame length")
        raw = self.exact(length)
        if kind == tp.FILE_DATA:
            return kind, raw
        return kind, tp.validate_frame(kind, tp.decode_json(raw))

    def wait_exit(self):
        while (
            self.process.poll() is None
            or any(key.data == "stderr" for key in self.selector.get_map().values())
        ):
            self.pump()
        return self.process.returncode

    def terminal(self, *, error):
        while not self.stdout_eof:
            tp.require(not self.buffer, "Trailing bytes after terminal frame")
            self.pump()
        tp.require(not self.buffer, "Trailing bytes after terminal frame")
        code = self.wait_exit()
        tp.require(
            (code != 0) if error else (code == 0),
            "Sender exit status contradicts terminal frame",
        )

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            # Drain only the bounded diagnostic tail after child termination.
            if not self.process.stderr.closed:
                while True:
                    try:
                        chunk = os.read(self.process.stderr.fileno(), 65536)
                    except BlockingIOError:
                        break
                    if not chunk:
                        break
                    self.diagnostics.extend(chunk)
                    del self.diagnostics[:-tp.MAX_DIAGNOSTICS]
        finally:
            for pipe in (
                self.process.stdin, self.process.stdout, self.process.stderr
            ):
                if not pipe.closed:
                    pipe.close()
            self.selector.close()


def _expect(child, expected_kind):
    kind, value = child.frame()
    if kind == tp.ERROR:
        child.terminal(error=True)
        raise tp.TransportError(value["code"], value["message"])
    tp.require(kind == expected_kind, "Unexpected frame order")
    return value


def _receive_file(child, payload, name, expected, budget, limits, total_left):
    start = _expect(child, tp.FILE_START)
    size, digest = expected
    tp.require(
        start == {
            "relative_path": name, "size_bytes": size, "sha256": digest,
        },
        "File start disagrees with anchored inventory",
        "TRANSPORT_VERIFICATION_FAILED",
    )
    destination = payload / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        destination,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    count = 0
    hasher = hashlib.sha256()
    with os.fdopen(descriptor, "wb") as handle:
        while count < size:
            budget.remaining()
            _capacity(
                payload, total_left - count, limits["min_free_bytes_after_copy"]
            )
            chunk = _expect(child, tp.FILE_DATA)
            tp.require(
                count + len(chunk) <= size, "File exceeds declared length",
                "TRANSPORT_VERIFICATION_FAILED",
            )
            handle.write(chunk)
            hasher.update(chunk)
            count += len(chunk)
        end = _expect(child, tp.FILE_END)
        tp.require(
            end == {"relative_path": name, "verified_sha256": digest}
            and hasher.hexdigest() == digest,
            "Received file digest mismatch",
            "TRANSPORT_VERIFICATION_FAILED",
        )
        handle.flush()
        budget.remaining()
        os.fsync(handle.fileno())


def _inventory(payload, request, advertised):
    limits = request["limits"]
    raw_manifest = (payload / "manifest.json").read_bytes()
    raw_list = (payload / "artifact_list.json").read_bytes()
    manifest = tp.decode_json(raw_manifest, limits["max_metadata_bytes"])
    artifact_list = tp.decode_json(raw_list, limits["max_metadata_bytes"])
    try:
        ep._schema(manifest, ep.MANIFEST_FIELDS, "manifest")
        ep._version(manifest)
        ep._outcome(manifest["run_outcome"])
        ep._require(
            manifest["run_id"] == request["run_id"]
            and manifest["attempt_id"] == request["attempt_id"]
            and manifest["predeclaration_sha256"]
                == request["expected_predeclaration_sha256"]
            and manifest["artifact_list_sha256"]
                == request["expected_artifact_list_sha256"],
            "Manifest identity/anchor mismatch",
        )
        declarations = ep._declarations(
            artifact_list, request["run_id"], limits["max_artifact_count"] - 2
        )
        entries = manifest["artifacts"]
        ep._require(
            type(entries) is list
            and len(entries) <= limits["max_artifact_count"] - 2,
            "Invalid manifest artifact count",
        )
        expected = {
            "manifest.json": (
                len(raw_manifest), request["expected_manifest_sha256"]
            ),
            "artifact_list.json": (
                len(raw_list), request["expected_artifact_list_sha256"]
            ),
        }
        for entry in entries:
            ep._schema(
                entry, {"relative_path", "role", "size_bytes", "sha256"},
                "artifact record",
            )
            name = tp.relative_path(entry["relative_path"])
            ep._role_path(name, entry["role"])
            tp.integer(entry["size_bytes"], 0, limits["max_logical_bytes"])
            tp.digest_value(entry["sha256"])
            ep._require(
                name not in expected
                and name in declarations
                and declarations[name]["role"] == entry["role"],
                "Invalid artifact declaration",
            )
            expected[name] = (entry["size_bytes"], entry["sha256"])
        ep._unique_paths(expected)
        ep._require(
            len(expected) == advertised["total_artifacts"]
            and sum(size for size, _ in expected.values())
                == advertised["total_logical_bytes"],
            "Advertised totals disagree with anchored manifest",
        )
        return expected
    except ep.VerificationError as exc:
        if isinstance(exc, tp.TransportError):
            raise
        raise tp.TransportError(
            "TRANSPORT_VERIFICATION_FAILED", "Anchored inventory rejected"
        ) from exc


def receive_synthetic_bundle(
    source_root, destination_root, *,
    expected_run_id, expected_attempt_id,
    expected_manifest_sha256, expected_predeclaration_sha256,
    expected_artifact_list_sha256,
    limits, clock=time.monotonic,
):
    """Run a local synthetic sender and retain an isolated staging attempt."""
    request = {
        "request_schema_version": 1,
        "source_path": str(source_root),
        "run_id": expected_run_id,
        "attempt_id": expected_attempt_id,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_predeclaration_sha256": expected_predeclaration_sha256,
        "expected_artifact_list_sha256": expected_artifact_list_sha256,
        "limits": limits,
    }
    tp.validate_request(request)
    tp.require(callable(clock), "Invalid clock", "TRANSPORT_INVALID_INPUT")
    limits = dict(limits)
    request["limits"] = dict(limits)
    budget = tp.Budget(limits["max_runtime_seconds"], clock)
    attempt = None
    child = None
    publication = {"published": False}
    try:
        destination = _destination(destination_root)
        source = Path(source_root)
        tp.require(
            str(source) == str(source.resolve())
            and source != destination
            and source not in destination.parents
            and destination not in source.parents,
            "Source/destination overlap or noncanonical source",
            "TRANSPORT_INVALID_ROOTS",
        )
        parent = destination / "staging_attempts"
        if not parent.exists() and not parent.is_symlink():
            try:
                parent.mkdir(mode=0o700)
            except FileExistsError:
                pass
        _destination(parent)
        candidate = parent / expected_attempt_id
        budget.remaining()
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise tp.TransportError(
                "TRANSPORT_ATTEMPT_EXISTS", "Staging attempt already exists"
            ) from exc
        attempt = candidate
        _status(attempt, request, "INCOMPLETE", None, publication, budget)
        payload = attempt / "payload"
        payload.mkdir(mode=0o700)

        remaining = budget.remaining()
        tp.require(
            remaining >= 0.1, "Insufficient sender startup allowance",
            "TRANSPORT_RESOURCE_LIMIT",
        )
        request["limits"]["max_runtime_seconds"] = remaining
        child = _Child(request, budget)
        header = child.frame(first=True)
        tp.require(
            header == (tp.HEADER, {
                "protocol_version": tp.VERSION,
                "run_id": expected_run_id, "attempt_id": expected_attempt_id,
            }),
            "Sender header mismatch",
        )
        advertised = _expect(child, tp.INVENTORY)
        tp.require(
            advertised["manifest_sha256"] == expected_manifest_sha256
            and advertised["artifact_list_sha256"]
                == expected_artifact_list_sha256,
            "Advertised anchor mismatch", "TRANSPORT_VERIFICATION_FAILED",
        )
        tp.require(
            advertised["total_artifacts"] <= limits["max_artifact_count"]
            and advertised["total_logical_bytes"] <= limits["max_logical_bytes"]
            and advertised["manifest_json_bytes"]
                + advertised["artifact_list_json_bytes"]
                <= limits["max_metadata_bytes"],
            "Advertised inventory exceeds budget", "TRANSPORT_RESOURCE_LIMIT",
        )
        _capacity(
            destination, advertised["total_logical_bytes"],
            limits["min_free_bytes_after_copy"],
        )
        remaining_bytes = advertised["total_logical_bytes"]
        for name, size_key, digest in (
            ("manifest.json", "manifest_json_bytes", expected_manifest_sha256),
            (
                "artifact_list.json", "artifact_list_json_bytes",
                expected_artifact_list_sha256,
            ),
        ):
            size = advertised[size_key]
            tp.require(
                size <= remaining_bytes, "Invalid control-file totals",
                "TRANSPORT_VERIFICATION_FAILED",
            )
            _receive_file(
                child, payload, name, (size, digest), budget, limits,
                remaining_bytes,
            )
            remaining_bytes -= size
        expected = _inventory(payload, request, advertised)
        metadata_names = ep.CONTROLS | {ep.SINGLETONS["PROVENANCE"]}
        tp.require(
            metadata_names <= expected.keys(),
            "Missing provenance metadata", "TRANSPORT_VERIFICATION_FAILED",
        )
        tp.require(
            sum(expected[name][0] for name in metadata_names)
                <= limits["max_metadata_bytes"],
            "Metadata budget exceeded", "TRANSPORT_RESOURCE_LIMIT",
        )
        for name in sorted(set(expected) - ep.CONTROLS):
            _receive_file(
                child, payload, name, expected[name], budget, limits,
                remaining_bytes,
            )
            remaining_bytes -= expected[name][0]
        _expect(child, tp.EOS)
        child.terminal(error=False)
        tp.decode_json(
            (payload / ep.SINGLETONS["PROVENANCE"]).read_bytes(),
            limits["max_metadata_bytes"],
        )
        try:
            verified = ep.verify_bundle(
                payload, **tp.anchors(request),
                limits=tp.verifier_limits(limits, budget.remaining()),
                clock=clock,
            )
        except ep.RuntimeLimitExceeded as exc:
            raise tp.TransportError(
                "TRANSPORT_RESOURCE_LIMIT", "Destination verifier timed out"
            ) from exc
        except ep.VerificationError as exc:
            raise tp.TransportError(
                "TRANSPORT_VERIFICATION_FAILED", "Destination verifier rejected"
            ) from exc
        budget.remaining()
        _status(
            attempt, request, "TRANSPORT_VERIFIED", None, publication, budget
        )
        return {
            "classification": "TRANSPORT_VERIFIED",
            "attempt_root": str(attempt),
            "verification": verified,
            "published": True,
        }
    except Exception as exc:
        if isinstance(exc, tp.TransportError):
            failure = exc
        elif isinstance(exc, OSError):
            failure = tp.TransportError(
                "TRANSPORT_IO_ERROR", "Local transport filesystem/process failure"
            )
        else:
            raise
        failure.published = publication["published"]
        failure.attempt_root = str(attempt) if attempt else None
        if attempt is not None and not publication["published"]:
            try:
                _status(
                    attempt, request, "INCOMPLETE", failure.code, publication
                )
            except Exception as reporting:
                failure.reporting_error = reporting
        if child:
            failure.diagnostics = bytes(child.diagnostics)
        if failure is exc:
            raise
        raise failure from exc
    finally:
        if child:
            child.close()
