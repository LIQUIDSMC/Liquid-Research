"""Synthetic Increment 2 tests; no production data or remote connections."""
import copy
import json
import math
import os
import select
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from L1_CORE.market_data_platform import evidence_copy as cp
from L1_CORE.market_data_platform import evidence_preservation as ep
from L1_CORE.market_data_platform import test_evidence_preservation as fx


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def setup(tmp_path):
    source, kwargs = fx.fixture(tmp_path / "source")
    destination = tmp_path / "destination"
    destination.mkdir()
    kwargs["limits"]["min_free_bytes_after_copy"] = 1048576
    return source, destination, kwargs


def run(setup, **extra):
    source, destination, kwargs = setup
    return cp.copy_synthetic_bundle(source, destination, **kwargs, **extra)


def attempt(setup):
    _, destination, kwargs = setup
    return destination / "attempts" / kwargs["expected_attempt_id"]


def control(setup):
    return json.loads((attempt(setup) / "attempt.json").read_bytes())


def fails(setup, code, **extra):
    with pytest.raises(cp.CopyError) as caught:
        run(setup, **extra)
    assert caught.value.code == code
    return caught.value


def incomplete(setup, code):
    record = control(setup)
    assert record["state"] == "INCOMPLETE"
    assert record["error_code"] == code


def test_valid_copy_exact_bytes_control_and_no_extra_claims(setup):
    source, _, kwargs = setup
    before = fx.snapshot(source)
    result = run(setup)
    assert set(result) == {"classification", "attempt_root", "verification"}
    assert result["classification"] == "COPY_VERIFIED"
    assert result["verification"]["classification"] == "INCREMENT_1_INTEGRITY_VERIFIED"
    assert fx.snapshot(attempt(setup) / "payload") == before
    assert fx.snapshot(source) == before
    assert control(setup) == {
        "schema_version": 1,
        "run_id": kwargs["expected_run_id"],
        "attempt_id": kwargs["expected_attempt_id"],
        "expected_manifest_sha256": kwargs["expected_manifest_sha256"],
        "state": "COPY_VERIFIED",
        "error_code": None,
    }


@pytest.mark.parametrize("field", [
    "expected_manifest_sha256", "expected_artifact_list_sha256",
    "expected_predeclaration_sha256",
])
def test_invalid_anchor_creates_no_attempt(setup, field):
    source, _, kwargs = setup
    before = fx.snapshot(source)
    kwargs[field] = "0" * 64
    fails(setup, "SOURCE_INVALID")
    assert not attempt(setup).exists()
    assert fx.snapshot(source) == before


def test_existing_attempt_unchanged(setup):
    run(setup)
    before = fx.snapshot(attempt(setup))
    fails(setup, "ATTEMPT_EXISTS")
    assert fx.snapshot(attempt(setup)) == before


def test_cross_process_lock_contention(setup):
    _, destination, _ = setup
    script = """
import sys
from pathlib import Path
from L1_CORE.market_data_platform import evidence_copy as cp
with cp._destination_lock(Path(sys.argv[1])):
    print("LOCKED", flush=True)
    sys.stdin.readline()
"""
    child = subprocess.Popen(
        [sys.executable, "-c", script, str(destination)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready, _, _ = select.select([child.stdout], [], [], 5)
        assert ready, "Child lock acquisition timed out"
        assert child.stdout.readline().strip() == "LOCKED"
        fails(setup, "LOCK_BUSY")
        assert not attempt(setup).exists()
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)
    run(setup)


@pytest.mark.parametrize("location", ["source", "destination", "component", "lock", "attempts"])
def test_symlink_rejection(setup, tmp_path, location):
    source, destination, kwargs = setup
    if location in {"source", "destination"}:
        alias = tmp_path / "alias"
        original = source if location == "source" else destination
        alias.symlink_to(original, target_is_directory=True)
        arguments = (alias, destination) if location == "source" else (source, alias)
        with pytest.raises(ep.VerificationError, match="absolute and canonical"):
            cp.copy_synthetic_bundle(*arguments, **kwargs)
    elif location == "component":
        original = source / "evidence/source"
        moved = tmp_path / "moved"
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        fails(setup, "SOURCE_INVALID")
    else:
        link = destination / (cp.LOCK_NAME if location == "lock" else "attempts")
        link.symlink_to(tmp_path / "absent")
        fails(setup, "LOCK_INVALID" if location == "lock" else "INVALID_ROOTS")
    assert not attempt(setup).exists()


@pytest.mark.parametrize("direction", ["same", "destination_inside", "source_inside"])
def test_overlap_rejection(setup, direction):
    source, destination, kwargs = setup
    if direction == "same":
        destination = source
    elif direction == "destination_inside":
        destination = source / "nested"
        destination.mkdir()
    else:
        destination = source.parent
    with pytest.raises(cp.CopyError) as caught:
        cp.copy_synthetic_bundle(source, destination, **kwargs)
    assert caught.value.code == "INVALID_ROOTS"


def test_traversal_declaration_rejected(setup):
    source, _, kwargs = setup
    document = json.loads((source / "artifact_list.json").read_bytes())
    document["artifacts"][-1]["relative_path"] = "../escape"
    fx.put(source, "artifact_list.json", fx.encoded(document))
    fx.reseal(source, kwargs)
    fails(setup, "SOURCE_INVALID")
    assert not attempt(setup).exists()


def test_nonregular_source_rejected(setup):
    source, _, _ = setup
    os.mkfifo(source / "unexpected_fifo")
    fails(setup, "SOURCE_INVALID")
    assert not attempt(setup).exists()


@pytest.mark.parametrize("when", ["before_file", "after_file", "after_verification"])
def test_source_changes_retain_incomplete(setup, monkeypatch, when):
    source, _, _ = setup
    original_copy = cp._copy_file
    original_verify = cp._verify
    changed = False

    def mutate():
        nonlocal changed
        original = (source / fx.SOURCE).read_bytes()
        (source / fx.SOURCE).write_bytes(b"X" * len(original))
        changed = True

    def copying(reader, name, *args, **kwargs):
        if name == fx.SOURCE and when == "before_file":
            mutate()
        result = original_copy(reader, name, *args, **kwargs)
        if name == fx.SOURCE and when == "after_file":
            mutate()
        return result

    def verifying(root, anchors, limits, budget, phase):
        result = original_verify(root, anchors, limits, budget, phase)
        if phase == "destination" and when == "after_verification":
            mutate()
        return result

    monkeypatch.setattr(cp, "_copy_file", copying)
    monkeypatch.setattr(cp, "_verify", verifying)
    fails(setup, "SOURCE_CHANGED")
    assert changed
    incomplete(setup, "SOURCE_CHANGED")


@pytest.mark.parametrize("failure", ["copy", "destination"])
def test_injected_failure_retains_evidence(setup, monkeypatch, failure):
    source, _, _ = setup
    before = fx.snapshot(source)
    if failure == "copy":
        def broken(*args, **kwargs):
            raise OSError("synthetic copy failure")
        monkeypatch.setattr(cp, "_copy_file", broken)
        code = "COPY_IO_ERROR"
    else:
        original = ep.verify_bundle
        def broken(root, **kwargs):
            if Path(root).name == "payload":
                raise ep.VerificationError("synthetic destination failure")
            return original(root, **kwargs)
        monkeypatch.setattr(ep, "verify_bundle", broken)
        code = "DESTINATION_VERIFICATION_FAILED"
    fails(setup, code)
    incomplete(setup, code)
    assert (attempt(setup) / "payload").is_dir()
    assert fx.snapshot(source) == before


@pytest.mark.parametrize("field,value", [
    ("max_artifacts", 1), ("max_metadata_bytes", 1), ("max_logical_bytes", 1),
])
def test_source_budget_rejection_no_attempt(setup, field, value):
    source, _, kwargs = setup
    before = fx.snapshot(source)
    kwargs["limits"][field] = value
    fails(setup, "SOURCE_INVALID")
    assert not attempt(setup).exists()
    assert fx.snapshot(source) == before


@pytest.mark.parametrize("during_copy", [False, True])
def test_capacity_exhaustion(setup, monkeypatch, during_copy):
    source, _, _ = setup
    before = fx.snapshot(source)
    calls = 0
    def capacity(root):
        nonlocal calls
        calls += 1
        return SimpleNamespace(free=10**9 if during_copy and calls == 1 else 0)
    monkeypatch.setattr(cp.shutil, "disk_usage", capacity)
    fails(setup, "RESOURCE_LIMIT")
    if during_copy:
        incomplete(setup, "RESOURCE_LIMIT")
    else:
        assert not attempt(setup).exists()
    assert fx.snapshot(source) == before


def test_failure_report_failure_preserves_original_cause(setup, monkeypatch):
    original = cp._publish_control
    def publish(root, record, budget=None):
        if record["error_code"] is not None:
            raise OSError("synthetic reporting failure")
        return original(root, record, budget)
    def broken(*args, **kwargs):
        raise OSError("synthetic original copy failure")
    monkeypatch.setattr(cp, "_publish_control", publish)
    monkeypatch.setattr(cp, "_copy_file", broken)
    error = fails(setup, "COPY_IO_ERROR")
    assert isinstance(error.reporting_error, OSError)
    assert str(error.__cause__) == "synthetic original copy failure"
    assert control(setup)["state"] == "INCOMPLETE"


def test_retry_new_attempt_preserves_previous(setup, monkeypatch):
    source, destination, kwargs = setup
    original = cp._copy_file
    def broken(*args, **options):
        raise OSError("synthetic interruption")
    monkeypatch.setattr(cp, "_copy_file", broken)
    fails(setup, "COPY_IO_ERROR")
    prior = attempt(setup)
    before = fx.snapshot(prior)
    monkeypatch.setattr(cp, "_copy_file", original)

    # Prepare a new synthetic attempt without changing its run identity.
    new_kwargs = copy.deepcopy(kwargs)
    new_id = str(uuid.uuid4())
    for name in ("manifest.json", "evidence/provenance.json"):
        document = json.loads((source / name).read_bytes())
        document["attempt_id"] = new_id
        fx.put(source, name, fx.encoded(document))
    new_kwargs["expected_attempt_id"] = new_id
    fx.reseal(source, new_kwargs)
    cp.copy_synthetic_bundle(source, destination, **new_kwargs)
    assert fx.snapshot(prior) == before
    assert prior.name != new_id


def test_shared_budget_reduced_and_subverifier_exhaustion(setup, monkeypatch):
    clock = Clock()
    original_copy = cp._copy_file
    original_verify = ep.verify_bundle
    seen = []
    raised = []

    def copying(*args, **kwargs):
        result = original_copy(*args, **kwargs)
        clock.now = 4.0
        return result

    def verifying(root, **kwargs):
        seen.append((Path(root).name, kwargs["limits"]["max_runtime_seconds"],
                     kwargs["clock"]))
        if Path(root).name == "payload":
            original_tick = ep._Reader.tick
            def exhausting_tick(reader):
                if reader.root == Path(root):
                    clock.now = 5.25
                return original_tick(reader)
            with monkeypatch.context() as patch:
                patch.setattr(ep._Reader, "tick", exhausting_tick)
                try:
                    return original_verify(root, **kwargs)
                except ep.RuntimeLimitExceeded as exc:
                    raised.append(exc)
                    raise
        return original_verify(root, **kwargs)

    monkeypatch.setattr(cp, "_copy_file", copying)
    monkeypatch.setattr(ep, "verify_bundle", verifying)
    before = fx.snapshot(setup[0])
    error = fails(setup, "RESOURCE_LIMIT", clock=clock)
    assert seen[-1][0] == "payload"
    assert seen[-1][1] == 1.0
    assert seen[-1][2] is clock
    assert len(raised) == 1 and type(raised[0]) is ep.RuntimeLimitExceeded
    assert isinstance(error.__cause__, ep.VerificationError)
    incomplete(setup, "RESOURCE_LIMIT")
    assert fx.snapshot(setup[0]) == before


@pytest.mark.parametrize("phase", ["source", "destination"])
def test_precall_exhaustion_never_forwards_nonpositive_limit(
    setup, monkeypatch, phase
):
    clock = Clock()
    original_verify = cp._verify
    original_sub = ep.verify_bundle
    seen = []

    def verifying(root, anchors, limits, budget, current_phase):
        if current_phase == phase:
            clock.now = 5.0
        return original_verify(root, anchors, limits, budget, current_phase)

    def sub(root, **kwargs):
        assert kwargs["limits"]["max_runtime_seconds"] > 0
        seen.append(Path(root).name)
        return original_sub(root, **kwargs)

    monkeypatch.setattr(cp, "_verify", verifying)
    monkeypatch.setattr(ep, "verify_bundle", sub)
    fails(setup, "RESOURCE_LIMIT", clock=clock)
    assert "payload" not in seen
    if phase == "source":
        assert seen == []
        assert not attempt(setup).exists()
    else:
        assert seen == ["source"]
        incomplete(setup, "RESOURCE_LIMIT")


def test_exhaustion_after_destination_verification_never_publishes_verified(
    setup, monkeypatch
):
    clock = Clock()
    original_verify = cp._verify
    original_publish = cp._publish_control
    states = []

    def verifying(root, anchors, limits, budget, phase):
        result = original_verify(root, anchors, limits, budget, phase)
        if phase == "destination":
            clock.now = 5.0
        return result

    def publishing(root, record, budget=None):
        states.append(record["state"])
        return original_publish(root, record, budget)

    monkeypatch.setattr(cp, "_verify", verifying)
    monkeypatch.setattr(cp, "_publish_control", publishing)
    fails(setup, "RESOURCE_LIMIT", clock=clock)
    assert "COPY_VERIFIED" not in states
    incomplete(setup, "RESOURCE_LIMIT")


@pytest.mark.parametrize("phase", ["source", "destination"])
def test_runtime_subtype_at_copy_verifier_call_sites(setup, monkeypatch, phase):
    clock = Clock()
    original = ep.verify_bundle
    caught_types = []

    def verifying(root, **kwargs):
        current = "destination" if Path(root).name == "payload" else "source"
        if current != phase:
            return original(root, **kwargs)
        original_tick = ep._Reader.tick
        def exhausting(reader):
            clock.now = 6.0
            return original_tick(reader)
        with monkeypatch.context() as patch:
            patch.setattr(ep._Reader, "tick", exhausting)
            try:
                return original(root, **kwargs)
            except ep.RuntimeLimitExceeded as exc:
                caught_types.append(type(exc))
                assert isinstance(exc, ep.VerificationError)
                raise

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    before = fx.snapshot(setup[0])
    fails(setup, "RESOURCE_LIMIT", clock=clock)
    assert caught_types == [ep.RuntimeLimitExceeded]
    assert fx.snapshot(setup[0]) == before
    if phase == "source":
        assert not attempt(setup).exists()
    else:
        incomplete(setup, "RESOURCE_LIMIT")


@pytest.mark.parametrize("seconds", [True, False, 0, -1, math.inf, math.nan, "5", None])
def test_invalid_runtime_boundary_is_validation_not_exhaustion(setup, seconds):
    setup[2]["limits"]["max_runtime_seconds"] = seconds
    def forbidden_clock():
        raise AssertionError("Malformed limit reached clock")
    with pytest.raises(cp.CopyError) as caught:
        run(setup, clock=forbidden_clock)
    assert type(caught.value) is cp.CopyError
    assert caught.value.code == "INVALID_INPUT"
    assert not isinstance(caught.value, ep.RuntimeLimitExceeded)
    assert not attempt(setup).exists()


@pytest.mark.parametrize("phase", ["source", "destination"])
def test_unrelated_verification_error_not_reclassified_by_elapsed_deadline(
    setup, monkeypatch, phase
):
    clock = Clock()
    original = ep.verify_bundle
    def verifying(root, **kwargs):
        current = "destination" if Path(root).name == "payload" else "source"
        if current == phase:
            clock.now = 6.0
            raise ep.VerificationError("synthetic unrelated validation failure")
        return original(root, **kwargs)
    monkeypatch.setattr(ep, "verify_bundle", verifying)
    code = "SOURCE_INVALID" if phase == "source" else "DESTINATION_VERIFICATION_FAILED"
    fails(setup, code, clock=clock)
    if phase == "source":
        assert not attempt(setup).exists()
    else:
        incomplete(setup, code)


def test_deadline_after_successful_publication_does_not_downgrade(
    setup, monkeypatch
):
    clock = Clock()
    original = cp._publish_control
    published = []

    def publishing(root, record, budget=None):
        result = original(root, record, budget)
        published.append(record["state"])
        if record["state"] == "COPY_VERIFIED":
            clock.now = 6.0
        return result

    monkeypatch.setattr(cp, "_publish_control", publishing)
    before = fx.snapshot(setup[0])
    result = run(setup, clock=clock)
    assert result["classification"] == "COPY_VERIFIED"
    assert published == ["INCOMPLETE", "COPY_VERIFIED"]
    assert control(setup)["state"] == "COPY_VERIFIED"
    assert control(setup)["error_code"] is None
    assert fx.snapshot(setup[0]) == before


def test_post_source_verification_scan_error_is_classified(setup, monkeypatch):
    original_verify = cp._verify
    original_scan = ep._Reader.scan
    fail_scan = False

    def verifying(root, anchors, limits, budget, phase):
        nonlocal fail_scan
        result = original_verify(root, anchors, limits, budget, phase)
        if phase == "source":
            fail_scan = True
        return result

    def scanning(reader):
        if fail_scan:
            raise ep.VerificationError("synthetic changed source component")
        return original_scan(reader)

    monkeypatch.setattr(cp, "_verify", verifying)
    monkeypatch.setattr(ep._Reader, "scan", scanning)
    fails(setup, "SOURCE_CHANGED")
    assert not attempt(setup).exists()


@pytest.mark.parametrize("invalid", ["uuid", "digest", "root"])
def test_early_validation_has_unified_copy_error(setup, invalid, tmp_path):
    source, destination, kwargs = setup
    if invalid == "uuid":
        kwargs["expected_run_id"] = "invalid"
    elif invalid == "digest":
        kwargs["expected_manifest_sha256"] = "invalid"
    else:
        destination = tmp_path / "missing"
    with pytest.raises(cp.CopyError) as caught:
        cp.copy_synthetic_bundle(source, destination, **kwargs)
    assert caught.value.code == "INVALID_INPUT"
    assert not attempt(setup).exists()


def test_missing_lock_path_is_classified(setup, monkeypatch):
    _, destination, _ = setup
    original = Path.lstat

    def missing(path, *args, **kwargs):
        if path == destination / cp.LOCK_NAME:
            raise FileNotFoundError("synthetic missing lock")
        return original(path, *args, **kwargs)

    with cp._destination_lock(destination):
        descriptor = os.open(destination / cp.LOCK_NAME, os.O_RDONLY)
        try:
            monkeypatch.setattr(Path, "lstat", missing)
            with pytest.raises(cp.CopyError) as caught:
                cp._lock_identity(descriptor, destination / cp.LOCK_NAME)
            assert caught.value.code == "LOCK_INVALID"
        finally:
            os.close(descriptor)
