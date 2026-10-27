"""Synthetic profiler tests; no Pi or canonical-corpus access."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from L1_CORE.market_data_platform.research import pi5_memory_profiler as profiler


@pytest.mark.parametrize("stage", profiler.STAGES)
@pytest.mark.parametrize("rows", profiler.ROW_COUNTS)
def test_actual_synthetic_measurement(stage, rows):
    record = profiler.measure(stage, rows)
    assert profiler.parse_worker(profiler.encode(record), stage, rows) == record
    assert record["input_array_bytes"] == rows * 33
    assert record["peak_rss_bytes"] > 0
    if stage == "calculation_kernel":
        assert record["kernel_sample_count"] == rows // 20


def test_configure_worker_sets_limits_without_changing_test_process(monkeypatch):
    observed = []
    monkeypatch.setattr(profiler.socket, "gethostname", lambda: "liquid-pi5")
    monkeypatch.setattr(profiler.sys, "platform", "linux")
    monkeypatch.setattr(
        profiler.resource, "setrlimit",
        lambda kind, value: observed.append((kind, value)),
    )
    for name in (*profiler.THREAD_VARIABLES, "PYTHONDONTWRITEBYTECODE"):
        monkeypatch.setenv(name, "old")
    profiler.configure_worker()
    assert observed == [(
        profiler.resource.RLIMIT_AS,
        (profiler.ADDRESS_SPACE, profiler.ADDRESS_SPACE),
    )]
    assert all(os.environ[name] == "1" for name in profiler.THREAD_VARIABLES)


def test_configuration_rejected_before_filesystem_access(tmp_path):
    with pytest.raises(profiler.ProfileError):
        profiler.launch("unknown", 678382, tmp_path / "missing")
    with pytest.raises(profiler.ProfileError):
        profiler.launch("array_sorting", True, tmp_path / "missing")
    assert list(tmp_path.iterdir()) == []


def test_capture_drains_stderr_and_keeps_tail():
    code = "import sys;sys.stderr.write('x'*100000);print('{}')"
    result = profiler.capture([sys.executable, "-c", code], dict(os.environ), timeout=5)
    assert result["exit_status"] == 0
    assert result["error"] is None
    assert result["stdout"].strip() == b"{}"
    assert result["stderr_tail"] == "x" * 4096


def test_capture_rejects_excess_stdout():
    result = profiler.capture(
        [sys.executable, "-c", "print('x'*100000)"], dict(os.environ), timeout=5
    )
    assert "stdout limit" in result["error"]
    assert len(result["stdout"]) <= profiler.MAX_JSON


def test_capture_terminates_timed_out_real_child():
    result = profiler.capture(
        [sys.executable, "-c", "import time;time.sleep(30)"],
        dict(os.environ), timeout=0.2,
    )
    assert result["error"] is not None
    assert result["exit_status"] is not None


def test_parse_worker_rejects_duplicate_keys():
    with pytest.raises(profiler.ProfileError, match="Duplicate"):
        profiler.parse_worker(
            b'{"version":1,"version":2}', "array_sorting", 678382
        )


def test_parse_worker_rejects_nonfinite_constants():
    with pytest.raises(profiler.ProfileError, match="Nonfinite"):
        profiler.parse_worker(b'{"x":NaN}', "array_sorting", 678382)


def test_publication_never_overwrites(tmp_path):
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        profiler.publish(descriptor, "complete.json", {"value": 1})
        before = (tmp_path / "complete.json").read_bytes()
        with pytest.raises(FileExistsError):
            profiler.publish(descriptor, "complete.json", {"value": 2})
        assert (tmp_path / "complete.json").read_bytes() == before
    finally:
        os.close(descriptor)


def test_post_link_durability_error_preserves_completion(tmp_path, monkeypatch):
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original = profiler.os.fsync
    try:
        def fail_directory(target):
            if target == descriptor:
                raise OSError("synthetic fsync failure")
            return original(target)
        monkeypatch.setattr(profiler.os, "fsync", fail_directory)
        with pytest.raises(profiler.ProfileError) as caught:
            profiler.publish(descriptor, "complete.json", {"value": 1})
        assert caught.value.published is True
        assert (tmp_path / "complete.json").exists()
    finally:
        os.close(descriptor)


def test_worker_failure_retains_attempt(tmp_path, monkeypatch):
    root = tmp_path / "profiles"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(profiler, "capture", lambda *a, **k: {
        "exit_status": -9, "stdout": b"", "stderr_tail": "synthetic failure",
        "error": None,
    })
    with pytest.raises(profiler.ProfileError) as caught:
        profiler.launch("array_sorting", 678382, root)
    attempt = Path(caught.value.attempt)
    assert (attempt / "incomplete.json").exists()
    assert (attempt / "failure.json").exists()
    assert not (attempt / "complete.json").exists()


def test_symlinked_output_root_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(real)
    with pytest.raises((profiler.ProfileError, OSError)):
        profiler.launch("array_sorting", 678382, alias)
    assert list(real.iterdir()) == []


def test_nonzero_worker_exit_is_not_success(tmp_path, monkeypatch):
    root = tmp_path / "profiles"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(profiler, "capture", lambda *a, **k: {
        "exit_status": 7, "stdout": b"{}", "stderr_tail": "", "error": None,
    })
    with pytest.raises(profiler.ProfileError, match="exit 7"):
        profiler.launch("array_sorting", 678382, root)
