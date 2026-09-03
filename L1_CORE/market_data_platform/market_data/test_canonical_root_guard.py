"""
Market Data Platform — Canonical Root Guard Regression Tests
market_data_platform/market_data/test_canonical_root_guard.py

Regression protection for verify_canonical_root_or_raise() and the
LRS_CANONICAL_ROOT / LRS_PRODUCTION environment mechanism, added
after the storage-path divergence incident (see
STORAGE_PATH_DIVERGENCE_INCIDENT.md). The incident cost six days of
misdirected live data; these tests exist so a future refactor cannot
silently remove this protection.

Run: python3 -m L1_CORE.market_data_platform.market_data.test_canonical_root_guard
"""
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _run_subprocess_check(env_extra, expect_ok, expect_message_substring=None):
    """
    Runs a fresh Python subprocess that imports storage.py with the
    given extra environment variables set BEFORE import, so this
    actually proves the env-var mechanism works at import time --
    not just that the guard function behaves correctly once called
    with manually-set module attributes.
    """
    env = os.environ.copy()
    env.update(env_extra)

    code = (
        "import sys; sys.path.insert(0, '.'); "
        "import L1_CORE.market_data_platform.market_data.storage as storage; "
        "storage.verify_canonical_root_or_raise(); "
        "print('SUBPROCESS_OK')"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    if expect_ok:
        assert result.returncode == 0, (
            f"Expected success, got exit {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "SUBPROCESS_OK" in result.stdout
    else:
        assert result.returncode != 0, (
            f"Expected failure, subprocess succeeded unexpectedly\n"
            f"stdout: {result.stdout}"
        )
        if expect_message_substring:
            assert expect_message_substring in result.stderr, (
                f"Expected {expect_message_substring!r} in stderr, got:\n{result.stderr}"
            )


def test_absolute_valid_directory():
    with tempfile.TemporaryDirectory() as target:
        _run_subprocess_check(
            {"LRS_CANONICAL_ROOT": target},
            expect_ok=True,
        )
    print("PASS: absolute valid directory accepted")


def test_absolute_path_missing():
    _run_subprocess_check(
        {"LRS_CANONICAL_ROOT": "/tmp/lrs_test_this_does_not_exist_12345"},
        expect_ok=False,
        expect_message_substring="does not exist",
    )
    print("PASS: absolute missing path correctly rejected")


def test_relative_symlink_valid():
    """
    Calls the pure _validate_canonical_path() helper directly against
    an isolated temp directory -- no subprocess, no environment
    variables, no production configuration involved, and the real
    repo's data/canonical path is never touched.
    """
    import L1_CORE.market_data_platform.market_data.storage as storage

    with tempfile.TemporaryDirectory() as isolated_root:
        target = os.path.join(isolated_root, "target")
        link_path = os.path.join(isolated_root, "canonical")
        os.makedirs(target)
        os.symlink(target, link_path)

        storage._validate_canonical_path(link_path, is_absolute_mode=False)
    print("PASS: relative symlink (valid) accepted")


def test_relative_plain_directory_rejected():
    """
    This is the exact failure mode from the actual incident: the
    canonical path exists but is a plain directory, not a symlink.
    Calls the pure helper directly against an isolated temp
    directory -- never touches the real repo's data/canonical path.
    """
    import L1_CORE.market_data_platform.market_data.storage as storage

    with tempfile.TemporaryDirectory() as isolated_root:
        link_path = os.path.join(isolated_root, "canonical")
        os.makedirs(link_path)

        try:
            storage._validate_canonical_path(link_path, is_absolute_mode=False)
            raise AssertionError("Expected RuntimeError but none was raised")
        except RuntimeError as e:
            assert "exists but is not a symlink" in str(e), str(e)
    print("PASS: relative plain-directory (incident failure mode) correctly rejected")


def test_production_requires_env_var():
    _run_subprocess_check(
        {"LRS_PRODUCTION": "1"},
        expect_ok=False,
        expect_message_substring="LRS_CANONICAL_ROOT is not set",
    )
    print("PASS: production mode without LRS_CANONICAL_ROOT correctly rejected")


if __name__ == "__main__":
    test_absolute_valid_directory()
    test_absolute_path_missing()
    test_relative_symlink_valid()
    test_relative_plain_directory_rejected()
    test_production_requires_env_var()
    print("\nALL TESTS PASSED")
