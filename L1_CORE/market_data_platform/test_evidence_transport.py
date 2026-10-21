"""Mac-local synthetic protocol and subprocess tests; no SSH."""
import base64
import copy
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from L1_CORE.market_data_platform import transport_protocol as tp
from L1_CORE.market_data_platform import transport_sender as sender
from L1_CORE.market_data_platform import transport_receiver as receiver
from L1_CORE.market_data_platform import test_evidence_preservation as fx


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def setup(tmp_path):
    source, anchors = fx.fixture(tmp_path / "source")
    destination = tmp_path / "destination"
    destination.mkdir(mode=0o700)
    limits = dict(tp.DEFAULT_LIMITS)
    return source, destination, anchors, limits


def run(setup, **options):
    source, destination, anchors, limits = setup
    kwargs = dict(anchors)
    kwargs["limits"] = dict(limits)
    kwargs.update(options)
    return receiver.receive_synthetic_bundle(source, destination, **kwargs)


def request(setup):
    source, _, anchors, limits = setup
    return {
        "request_schema_version": 1,
        "source_path": str(source),
        "run_id": anchors["expected_run_id"],
        "attempt_id": anchors["expected_attempt_id"],
        "expected_manifest_sha256": anchors["expected_manifest_sha256"],
        "expected_predeclaration_sha256":
            anchors["expected_predeclaration_sha256"],
        "expected_artifact_list_sha256":
            anchors["expected_artifact_list_sha256"],
        "limits": dict(limits),
    }


def attempt(setup):
    return setup[1] / "staging_attempts" / setup[2]["expected_attempt_id"]


def record(setup):
    return json.loads((attempt(setup) / "status.json").read_bytes())


def inventory(root):
    return {
        str(item.relative_to(root)): (
            "directory" if item.is_dir() else item.read_bytes()
        )
        for item in root.rglob("*")
    }


def fails(setup, code, **options):
    before = inventory(setup[0])
    with pytest.raises(tp.TransportError) as caught:
        run(setup, **options)
    assert caught.value.code == code
    assert inventory(setup[0]) == before
    return caught.value


def wire(setup):
    output = io.BytesIO()
    code = sender.send(request(setup), output)
    assert code == 0
    return output.getvalue()


def frames(raw):
    result = []
    offset = 0
    while offset < len(raw):
        kind, size = tp.PREFIX.unpack(raw[offset:offset + 8])
        offset += 8
        payload = raw[offset:offset + size]
        assert len(payload) == size
        result.append((kind, payload))
        offset += size
    return result


def raw_frame(kind, raw):
    return tp.PREFIX.pack(kind, len(raw)) + raw


def replay(monkeypatch, raw, *, exit_code=0, stderr=b""):
    original = subprocess.Popen
    script = (
        "import base64,sys;"
        "sys.stdin.buffer.read();"
        "sys.stderr.buffer.write(base64.b64decode(sys.argv[2]));"
        "sys.stderr.buffer.flush();"
        "sys.stdout.buffer.write(base64.b64decode(sys.argv[1]));"
        "sys.stdout.buffer.flush();"
        "sys.exit(int(sys.argv[3]))"
    )

    def spawning(command, **kwargs):
        return original(
            [
                sys.executable, "-c", script,
                base64.b64encode(raw).decode(),
                base64.b64encode(stderr).decode(), str(exit_code),
            ],
            **kwargs,
        )

    monkeypatch.setattr(receiver.subprocess, "Popen", spawning)


def test_real_subprocess_exact_transfer(setup):
    before = inventory(setup[0])
    result = run(setup)
    assert result["classification"] == "TRANSPORT_VERIFIED"
    assert result["published"] is True
    assert inventory(attempt(setup) / "payload") == before
    assert inventory(setup[0]) == before
    status = record(setup)
    assert set(status) == {
        "schema_version", "run_id", "attempt_id",
        "expected_manifest_sha256", "state", "error_code",
        "timestamp_utc", "published",
    }
    assert status["state"] == "TRANSPORT_VERIFIED"
    assert status["published"] is True
    assert status["error_code"] is None


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo"])
def test_source_special_entries_rejected(setup, kind):
    pathname = setup[0] / "unexpected"
    if kind == "symlink":
        pathname.symlink_to(setup[0] / fx.SOURCE)
    elif kind == "hardlink":
        os.link(setup[0] / fx.SOURCE, pathname)
    else:
        os.mkfifo(pathname)
    # The source contains deliberately nonregular entries; avoid reading it
    # with the ordinary byte-inventory helper.
    with pytest.raises(tp.TransportError) as caught:
        run(setup)
    assert caught.value.code == "TRANSPORT_SOURCE_INVALID"
    assert record(setup)["state"] == "INCOMPLETE"
    assert record(setup)["error_code"] == caught.value.code


@pytest.mark.parametrize("raw", [
    b'{"a":1,"a":2}',
    b'{"x":{"a":1,"a":2}}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
    b'{"x":123456789012345678901}',
    b'[' * 33 + b'0' + b']' * 33,
    b'"\xff"',
])
def test_strict_json_rejects(raw):
    with pytest.raises(tp.TransportError):
        tp.decode_json(raw)


@pytest.mark.parametrize("name", [
    "/absolute", "../escape", "a/../b", "a//b", "a\\b",
    "a\x00b", "/".join(["a"] * 129), "a" * 1025,
])
def test_path_bounds(name):
    with pytest.raises(tp.TransportError):
        tp.relative_path(name)


def test_prefix_collision_rejected():
    from L1_CORE.market_data_platform import evidence_preservation as ep
    with pytest.raises(ep.VerificationError):
        ep._unique_paths([
            "evidence/source/a", "evidence/source/a-keep",
            "evidence/source/a/child",
        ])


@pytest.mark.parametrize("field,value", [
    ("max_artifact_count", True),
    ("max_artifact_count", 2),
    ("max_logical_bytes", 0),
    ("max_metadata_bytes", False),
    ("max_runtime_seconds", float("inf")),
    ("min_free_bytes_after_copy", -1),
])
def test_invalid_limits_before_child(setup, monkeypatch, field, value):
    limits = dict(setup[3])
    limits[field] = value

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid input must not start a child")

    monkeypatch.setattr(receiver, "_Child", forbidden)
    fails(setup, "TRANSPORT_INVALID_INPUT", limits=limits)
    assert not attempt(setup).exists()


def test_count_conversion():
    limits = dict(tp.DEFAULT_LIMITS)
    converted = tp.verifier_limits(limits, 2.5)
    assert converted["max_artifacts"] == limits["max_artifact_count"] - 2
    assert converted["max_runtime_seconds"] == 2.5


def test_existing_attempt_unchanged(setup):
    run(setup)
    before = inventory(attempt(setup))
    fails(setup, "TRANSPORT_ATTEMPT_EXISTS")
    assert inventory(attempt(setup)) == before


def test_concurrent_attempt_creation_collision(setup, monkeypatch):
    original = Path.mkdir
    target = attempt(setup)

    def competing(pathname, *args, **kwargs):
        if pathname == target:
            child = subprocess.run(
                [
                    sys.executable, "-c",
                    "import os,sys; os.mkdir(sys.argv[1],0o700)",
                    str(target),
                ],
                capture_output=True, timeout=10,
            )
            assert child.returncode == 0, child.stderr
        return original(pathname, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", competing)
    fails(setup, "TRANSPORT_ATTEMPT_EXISTS")
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("field", [
    "expected_manifest_sha256", "expected_predeclaration_sha256",
    "expected_artifact_list_sha256",
])
def test_source_anchor_mismatch(setup, field):
    error = fails(setup, "TRANSPORT_SOURCE_INVALID", **{field: "0" * 64})
    assert error.published is False
    assert record(setup)["state"] == "INCOMPLETE"


@pytest.mark.parametrize("field,value", [
    ("max_logical_bytes", 1),
    ("max_metadata_bytes", 1),
    ("max_artifact_count", 3),
])
def test_source_limits_reject(setup, field, value):
    limits = dict(setup[3])
    limits[field] = value
    with pytest.raises(tp.TransportError) as caught:
        run(setup, limits=limits)
    assert caught.value.code == "TRANSPORT_RESOURCE_LIMIT"
    assert record(setup)["state"] == "INCOMPLETE"


def test_capacity_failure_retains_attempt(setup, monkeypatch):
    monkeypatch.setattr(
        receiver.shutil, "disk_usage",
        lambda root: type("Usage", (), {"free": 0})(),
    )
    fails(setup, "TRANSPORT_RESOURCE_LIMIT")
    assert record(setup)["error_code"] == "TRANSPORT_RESOURCE_LIMIT"
    assert (attempt(setup) / "payload").is_dir()


@pytest.mark.parametrize("mutation,code", [
    ("truncate", "TRANSPORT_IO_ERROR"),
    ("trailing", "TRANSPORT_MALFORMED_FRAME"),
    ("nonzero", "TRANSPORT_MALFORMED_FRAME"),
    ("oversize", "TRANSPORT_MALFORMED_FRAME"),
    ("unknown_error", "TRANSPORT_PROTOCOL_ERROR"),
])
def test_protocol_terminal_failures(setup, monkeypatch, mutation, code):
    raw = wire(setup)
    exit_code = 0
    if mutation == "truncate":
        raw = raw[:-10]
    elif mutation == "trailing":
        raw += b"x"
    elif mutation == "nonzero":
        exit_code = 1
    elif mutation == "oversize":
        raw = tp.PREFIX.pack(tp.HEADER, tp.MAX_JSON + 1)
    else:
        header = frames(raw)[0]
        raw = raw_frame(*header) + raw_frame(
            tp.ERROR, tp.encode_json({
                "error_schema_version": 1, "code": "UNKNOWN", "message": "bad",
            }),
        )
        exit_code = 1
    replay(monkeypatch, raw, exit_code=exit_code)
    fails(setup, code)
    assert record(setup)["state"] == "INCOMPLETE"


@pytest.mark.parametrize("remote_code", sorted(tp.REMOTE_CODES))
def test_remote_error_whitelist(setup, monkeypatch, remote_code):
    header = frames(wire(setup))[0]
    raw = raw_frame(*header) + tp.pack_frame(tp.ERROR, {
        "error_schema_version": 1, "code": remote_code, "message": "synthetic",
    })
    replay(monkeypatch, raw, exit_code=1)
    fails(setup, remote_code)


def test_diagnostics_tail_bounded(setup, monkeypatch):
    header = frames(wire(setup))[0]
    raw = raw_frame(*header) + tp.pack_frame(tp.ERROR, {
        "error_schema_version": 1,
        "code": "TRANSPORT_IO_ERROR", "message": "synthetic",
    })
    replay(monkeypatch, raw, exit_code=1, stderr=b"d" * 20000 + b"TAIL")
    error = fails(setup, "TRANSPORT_IO_ERROR")
    assert len(error.diagnostics) == tp.MAX_DIAGNOSTICS
    assert error.diagnostics.endswith(b"TAIL")


def test_receiver_anchor_mismatch(setup, monkeypatch):
    parts = frames(wire(setup))
    payload = json.loads(parts[1][1])
    payload["manifest_sha256"] = "0" * 64
    parts[1] = tp.INVENTORY, tp.encode_json(payload)
    replay(monkeypatch, b"".join(raw_frame(*part) for part in parts))
    fails(setup, "TRANSPORT_VERIFICATION_FAILED")


def test_source_mutation_during_stream(setup, monkeypatch):
    original = sender._stream_file
    changed = False

    def changing(reader, name, expected, output, budget):
        nonlocal changed
        result = original(reader, name, expected, output, budget)
        if name == fx.SOURCE and not changed:
            changed = True
            (setup[0] / fx.SOURCE).write_bytes(b"changed-after-stream")
        return result

    monkeypatch.setattr(sender, "_stream_file", changing)
    output = io.BytesIO()
    assert sender.send(request(setup), output) == 1
    terminal_kind, raw = frames(output.getvalue())[-1]
    assert terminal_kind == tp.ERROR
    assert json.loads(raw)["code"] == "TRANSPORT_SOURCE_CHANGED"


def test_reduced_budget_same_clock(setup, monkeypatch):
    clock = Clock()
    original_destination = receiver._destination
    original_child = receiver._Child
    observed = []

    def destination(value):
        result = original_destination(value)
        clock.now = 2.0
        return result

    def child(request_value, budget):
        observed.append((
            request_value["limits"]["max_runtime_seconds"], budget.clock
        ))
        return original_child(request_value, budget)

    monkeypatch.setattr(receiver, "_destination", destination)
    monkeypatch.setattr(receiver, "_Child", child)
    run(setup, clock=clock)
    assert observed == [(28.0, clock)]


def test_timeout_reaps_child_and_retains_attempt(setup, monkeypatch):
    original = subprocess.Popen
    children = []

    def hanging(command, **kwargs):
        child = original(
            [sys.executable, "-c", "import time; time.sleep(60)"], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(receiver.subprocess, "Popen", hanging)
    limits = dict(setup[3])
    limits["max_runtime_seconds"] = 0.3
    fails(setup, "TRANSPORT_RESOURCE_LIMIT", limits=limits)
    assert children[0].poll() is not None
    assert record(setup)["state"] == "INCOMPLETE"


def test_failure_record_error_preserves_original(setup, monkeypatch):
    original_status = receiver._status

    def status(attempt_root, request_value, state, code, publication, budget=None):
        if code is not None:
            raise OSError("synthetic failure recording error")
        return original_status(
            attempt_root, request_value, state, code, publication, budget
        )

    monkeypatch.setattr(receiver, "_status", status)
    error = fails(
        setup, "TRANSPORT_SOURCE_INVALID", expected_manifest_sha256="0" * 64
    )
    assert isinstance(error.reporting_error, OSError)
    assert error.published is False


def test_initial_control_failure_classified(setup, monkeypatch):
    def broken(*args, **kwargs):
        raise OSError("synthetic control write error")

    monkeypatch.setattr(receiver, "_write_status", broken)
    error = fails(setup, "TRANSPORT_CONTROL_IO_ERROR")
    assert error.reporting_error is not None
    assert error.published is False
    assert attempt(setup).is_dir()


def test_postcommit_directory_sync_failure(setup, monkeypatch):
    original = receiver._sync

    def syncing(directory):
        status_file = directory / "status.json"
        if status_file.exists():
            status = json.loads(status_file.read_bytes())
            if status["state"] == "TRANSPORT_VERIFIED":
                raise OSError("synthetic final directory fsync failure")
        return original(directory)

    monkeypatch.setattr(receiver, "_sync", syncing)
    error = fails(setup, "PUBLICATION_DURABILITY_UNCERTAIN")
    assert error.published is True
    assert record(setup)["state"] == "TRANSPORT_VERIFIED"
    assert record(setup)["published"] is True


@pytest.mark.parametrize("phase", ["before", "after"])
def test_publication_expiry_boundary(setup, monkeypatch, phase):
    clock = Clock()
    original = receiver._status

    def status(attempt_root, request_value, state, code, publication, budget=None):
        if state == "TRANSPORT_VERIFIED" and phase == "before":
            clock.now = 30.0
        result = original(
            attempt_root, request_value, state, code, publication, budget
        )
        if state == "TRANSPORT_VERIFIED" and phase == "after":
            clock.now = 31.0
        return result

    monkeypatch.setattr(receiver, "_status", status)
    if phase == "before":
        error = fails(setup, "TRANSPORT_RESOURCE_LIMIT", clock=clock)
        assert error.published is False
        assert record(setup)["state"] == "INCOMPLETE"
    else:
        result = run(setup, clock=clock)
        assert result["published"] is True
        assert record(setup)["state"] == "TRANSPORT_VERIFIED"
