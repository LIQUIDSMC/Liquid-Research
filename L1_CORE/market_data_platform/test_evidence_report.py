"""Synthetic report-publication tests; no production data."""
import copy
import json
import math
import os
import select
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from L1_CORE.market_data_platform import evidence_report as er
from L1_CORE.market_data_platform import evidence_pair as pair
from L1_CORE.market_data_platform import test_evidence_preservation as fx


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def setup(tmp_path):
    primary, kwargs = fx.fixture(tmp_path / "primary")
    secondary = tmp_path / "secondary"
    shutil.copytree(primary, secondary)
    directory = tmp_path / "reports"
    directory.mkdir()
    return primary, secondary, directory, str(uuid.uuid4()), kwargs


def run(setup, **overrides):
    primary, secondary, directory, report_id, kwargs = setup
    options = copy.deepcopy(kwargs)
    options.update(overrides)
    return er.verify_and_record_synthetic_pair(
        primary, secondary, directory, report_id, **options
    )


def final_path(setup):
    return setup[2] / f"{setup[3]}.json"


def evidence_inventory(setup):
    return tuple(
        {
            str(item.relative_to(root)): (
                "directory" if item.is_dir() else item.read_bytes()
            )
            for item in root.rglob("*")
        }
        for root in setup[:2]
    )


def unchanged(setup, operation):
    before = evidence_inventory(setup)
    try:
        return operation()
    finally:
        assert evidence_inventory(setup) == before


def failure(setup, code, **overrides):
    with pytest.raises(er.ReportError) as caught:
        unchanged(setup, lambda: run(setup, **overrides))
    assert caught.value.code == code
    return caught.value


@pytest.mark.parametrize("corrupt", [False, True])
def test_exact_record_and_source_unchanged(setup, corrupt):
    if corrupt:
        (setup[0] / fx.SOURCE).write_bytes(b"corrupt")
    result = unchanged(setup, lambda: run(setup))
    expected = {
        "record_schema_version": 1,
        "report_id": setup[3],
        "expected_predeclaration_sha256":
            setup[4]["expected_predeclaration_sha256"],
        "expected_artifact_list_sha256":
            setup[4]["expected_artifact_list_sha256"],
        "pair_report": result["pair_report"],
    }
    expected_raw = (
        json.dumps(
            expected, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ) + "\n"
    ).encode()
    assert final_path(setup).read_bytes() == expected_raw
    assert result == {
        "publication": "REPORT_RECORDED",
        "report_location": str(final_path(setup)),
        "pair_report": expected["pair_report"],
    }
    assert expected["pair_report"]["classification"] == (
        "PAIR_NOT_VERIFIED" if corrupt else "PAIR_VERIFIED"
    )
    assert list(setup[2].iterdir()) == [final_path(setup)]
    assert final_path(setup).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("field,value", [
    ("expected_run_id", "bad"),
    ("expected_attempt_id", "bad"),
    ("expected_manifest_sha256", "bad"),
    ("expected_predeclaration_sha256", "bad"),
    ("expected_artifact_list_sha256", "bad"),
    ("clock", None),
    ("limits", {}),
    ("limits", None),
])
def test_shared_invalid_inputs_before_clock_and_filesystem(
    setup, monkeypatch, field, value
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Clock/filesystem must not be accessed")

    monkeypatch.setattr(er, "_validated_roots", forbidden)
    options = {field: value}
    if field != "clock":
        options["clock"] = forbidden
    error = failure(setup, "INVALID_INPUT", **options)
    assert error.published is False
    assert error.pair_report is None


@pytest.mark.parametrize("seconds", [
    True, False, 0, -1, math.inf, math.nan, "5", None,
])
def test_invalid_runtime_before_clock(setup, seconds):
    limits = dict(setup[4]["limits"])
    limits["max_runtime_seconds"] = seconds

    def forbidden():
        raise AssertionError("Invalid limit must reject before clock")

    failure(setup, "INVALID_INPUT", limits=limits, clock=forbidden)


@pytest.mark.parametrize("index,value", [
    (0, "relative"), (1, "/tmp/../evidence"),
    (2, "/tmp/./reports"), (2, ""), (2, None),
    (0, 123), (3, "not-a-uuid"),
])
def test_reporting_and_root_syntax_before_clock(setup, index, value):
    modified = list(setup)
    modified[index] = value

    def forbidden():
        raise AssertionError("Invalid syntax must reject before clock")

    with pytest.raises(er.ReportError) as caught:
        unchanged(
            setup,
            lambda: run(tuple(modified), clock=forbidden),
        )
    assert caught.value.code == "INVALID_INPUT"
    assert caught.value.published is False
    assert caught.value.pair_report is None


@pytest.mark.parametrize("case", [
    "missing", "symlink", "inside", "ancestor", "file", "alias",
])
def test_report_directory_rejections(setup, tmp_path, monkeypatch, case):
    modified = list(setup)
    if case == "missing":
        modified[2] = tmp_path / "absent"
    elif case == "symlink":
        link = tmp_path / "link"
        link.symlink_to(setup[2], target_is_directory=True)
        modified[2] = link
    elif case == "inside":
        modified[2] = setup[0] / "evidence"
    elif case == "ancestor":
        modified[2] = tmp_path
    elif case == "file":
        modified[2] = setup[0] / "manifest.json"
    elif case == "alias":
        original = Path.stat
        identity = original(setup[0])

        def aliased(root, *args, **kwargs):
            if root == setup[2]:
                return identity
            return original(root, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", aliased)

    def forbidden(*args, **kwargs):
        raise AssertionError("Pair verifier must not run")

    monkeypatch.setattr(pair, "verify_synthetic_pair", forbidden)
    error = failure(tuple(modified), "INVALID_ROOTS")
    assert error.published is False


@pytest.mark.parametrize("kind", ["file", "directory", "symlink"])
def test_existing_final_never_overwritten(setup, kind):
    final = final_path(setup)
    if kind == "file":
        final.write_bytes(b"winner")
    elif kind == "directory":
        final.mkdir()
    else:
        final.symlink_to(setup[2] / "missing")
    error = failure(setup, "REPORT_EXISTS")
    assert error.published is False
    if kind == "file":
        assert final.read_bytes() == b"winner"
    elif kind == "directory":
        assert final.is_dir()
    else:
        assert final.is_symlink()


def test_cross_process_publication_race_preserves_winner(setup, monkeypatch):
    original_link = os.link
    winner = b"other-process-winner"

    def competing(source, destination, **kwargs):
        child = subprocess.run(
            [
                sys.executable, "-c",
                "import os,sys; "
                "fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); "
                "os.write(fd,b'other-process-winner'); os.close(fd)",
                str(destination),
            ],
            capture_output=True, timeout=10,
        )
        assert child.returncode == 0, child.stderr
        return original_link(source, destination, **kwargs)

    monkeypatch.setattr(os, "link", competing)
    error = failure(setup, "REPORT_EXISTS")
    assert error.published is False
    assert final_path(setup).read_bytes() == winner


def test_shared_runtime_and_clock(setup, monkeypatch):
    clock = Clock()
    original_roots = er._validated_roots
    original_pair = pair.verify_synthetic_pair
    seen = []

    def roots(*args):
        result = original_roots(*args)
        clock.now = 2.0
        return result

    def verifying(*args, **kwargs):
        seen.append((kwargs["limits"]["max_runtime_seconds"], kwargs["clock"]))
        return original_pair(*args, **kwargs)

    monkeypatch.setattr(er, "_validated_roots", roots)
    monkeypatch.setattr(pair, "verify_synthetic_pair", verifying)
    unchanged(setup, lambda: run(setup, clock=clock))
    assert seen == [(3.0, clock)]


def test_pre_pair_exhaustion_never_invokes_pair(setup, monkeypatch):
    clock = Clock()
    original = er._validated_roots

    def roots(*args):
        result = original(*args)
        clock.now = 5.0
        return result

    def forbidden(*args, **kwargs):
        raise AssertionError("Pair must not start")

    monkeypatch.setattr(er, "_validated_roots", roots)
    monkeypatch.setattr(pair, "verify_synthetic_pair", forbidden)
    error = failure(setup, "RESOURCE_LIMIT", clock=clock)
    assert error.pair_report is None
    assert error.published is False
    assert not final_path(setup).exists()


def test_expiry_after_pair_retains_report(setup, monkeypatch):
    clock = Clock()
    original = pair.verify_synthetic_pair
    observed = []

    def verifying(*args, **kwargs):
        report = original(*args, **kwargs)
        observed.append(report)
        clock.now = 5.0
        return report

    monkeypatch.setattr(pair, "verify_synthetic_pair", verifying)
    error = failure(setup, "RESOURCE_LIMIT", clock=clock)
    assert error.pair_report is observed[0]
    assert error.pair_report["classification"] == "PAIR_VERIFIED"
    assert error.published is False
    assert list(setup[2].iterdir()) == []


@pytest.mark.parametrize("when", ["before_link", "after_link"])
def test_publication_deadline_commit_point(setup, monkeypatch, when):
    clock = Clock()
    if when == "before_link":
        original = os.fsync

        def fsync(descriptor):
            result = original(descriptor)
            clock.now = 5.0
            return result

        monkeypatch.setattr(os, "fsync", fsync)
        error = failure(setup, "RESOURCE_LIMIT", clock=clock)
        assert error.published is False
        assert list(setup[2].iterdir()) == []
    else:
        original = os.link

        def linking(*args, **kwargs):
            result = original(*args, **kwargs)
            clock.now = 6.0
            return result

        monkeypatch.setattr(os, "link", linking)
        result = unchanged(setup, lambda: run(setup, clock=clock))
        assert result["publication"] == "REPORT_RECORDED"
        assert json.loads(final_path(setup).read_bytes())["pair_report"] == (
            result["pair_report"]
        )


def test_record_size_ceiling(setup, monkeypatch):
    original = pair.verify_synthetic_pair

    def oversized(*args, **kwargs):
        report = original(*args, **kwargs)
        report["synthetic_padding"] = "x" * er.MAX_RECORD_BYTES
        return report

    monkeypatch.setattr(pair, "verify_synthetic_pair", oversized)
    error = failure(setup, "RESOURCE_LIMIT")
    assert error.published is False
    assert list(setup[2].iterdir()) == []


@pytest.mark.parametrize("operation", ["write", "file_fsync", "link"])
def test_prepublication_io_failures(setup, monkeypatch, operation):
    def broken(*args, **kwargs):
        raise OSError("synthetic I/O failure")

    name = {"write": "write", "file_fsync": "fsync", "link": "link"}[operation]
    monkeypatch.setattr(os, name, broken)
    error = failure(setup, "REPORT_IO_ERROR")
    assert error.published is False
    assert error.cleanup_failed is False
    assert error.pair_report is not None
    assert list(setup[2].iterdir()) == []


def test_directory_fsync_uncertain_means_published(setup, monkeypatch):
    def broken(*args):
        raise OSError("synthetic directory fsync failure")

    monkeypatch.setattr(er, "_sync_directory", broken)
    error = failure(setup, "PUBLICATION_DURABILITY_UNCERTAIN")
    assert error.published is True
    assert error.cleanup_failed is False
    assert json.loads(final_path(setup).read_bytes())["pair_report"] == (
        error.pair_report
    )


@pytest.mark.parametrize("original_failure", [True, False])
def test_cleanup_failure_is_separate(setup, monkeypatch, original_failure):
    original_unlink = Path.unlink

    def unlinking(root, *args, **kwargs):
        if root.parent == setup[2] and root.name.startswith(".report-"):
            raise OSError("synthetic cleanup failure")
        return original_unlink(root, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlinking)
    if original_failure:
        def broken(*args):
            raise OSError("synthetic write failure")
        monkeypatch.setattr(os, "write", broken)
    error = failure(setup, "REPORT_IO_ERROR")
    assert error.cleanup_failed is True
    assert error.published is (not original_failure)
    if original_failure:
        assert isinstance(error.__cause__, OSError)
        assert str(error.__cause__) == "synthetic write failure"


def test_unowned_temporary_collision_is_not_deleted(setup, monkeypatch):
    fixed = SimpleNamespace(hex="fixed-collision")
    temporary = setup[2] / ".report-fixed-collision.tmp"
    temporary.write_bytes(b"pre-existing-file")
    monkeypatch.setattr(er.uuid, "uuid4", lambda: fixed)
    error = failure(setup, "REPORT_IO_ERROR")
    assert error.published is False
    assert temporary.read_bytes() == b"pre-existing-file"
    assert error.cleanup_failed is False


@pytest.mark.parametrize("kind", ["input", "programming"])
def test_inner_exceptions_propagate(setup, monkeypatch, kind):
    expected = (
        pair.PairInputError("INVALID_ROOTS", "synthetic inner error")
        if kind == "input" else RuntimeError("synthetic programming error")
    )

    def broken(*args, **kwargs):
        raise expected

    monkeypatch.setattr(pair, "verify_synthetic_pair", broken)
    with pytest.raises(type(expected)) as caught:
        unchanged(setup, lambda: run(setup))
    assert caught.value is expected
    assert list(setup[2].iterdir()) == []


@pytest.mark.parametrize("classification", ["PAIR_NOT_VERIFIED", "PAIR_VERIFIED"])
def test_exhausted_pair_report_policy(setup, monkeypatch, classification):
    clock = Clock()
    original = pair.verify_synthetic_pair
    observed = []

    def verifying(*args, **kwargs):
        report = original(*args, **kwargs)
        report["classification"] = classification
        report["budget_exhausted"] = True
        observed.append(report)
        return report

    monkeypatch.setattr(pair, "verify_synthetic_pair", verifying)
    if classification == "PAIR_NOT_VERIFIED":
        error = failure(setup, "RESOURCE_LIMIT", clock=clock)
        assert error.pair_report is observed[0]
        assert error.published is False
    else:
        with pytest.raises(RuntimeError, match="Invalid internal"):
            unchanged(setup, lambda: run(setup, clock=clock))
    assert clock.now == 0.0
    assert list(setup[2].iterdir()) == []
