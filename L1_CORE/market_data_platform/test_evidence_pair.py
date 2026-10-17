"""Synthetic read-only pair tests; no production evidence or connections."""
import copy
import math
import shutil
from pathlib import Path

import pytest

from L1_CORE.market_data_platform import evidence_pair as pair
from L1_CORE.market_data_platform import evidence_preservation as ep
from L1_CORE.market_data_platform import test_evidence_preservation as fx


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def bundles(tmp_path):
    primary, kwargs = fx.fixture(tmp_path / "primary")
    secondary = tmp_path / "secondary"
    shutil.copytree(primary, secondary)
    return primary, secondary, kwargs


def run(bundles, **overrides):
    primary, secondary, kwargs = bundles
    options = copy.deepcopy(kwargs)
    options.update(overrides)
    return pair.verify_synthetic_pair(primary, secondary, **options)


def inventory(root):
    return {
        str(item.relative_to(root)): (
            "directory" if item.is_dir() else "file",
            None if item.is_dir() else item.read_bytes(),
        )
        for item in root.rglob("*")
    }


def unchanged(bundles, operation):
    primary, secondary, _ = bundles
    before = inventory(primary), inventory(secondary)
    try:
        return operation()
    finally:
        assert (inventory(primary), inventory(secondary)) == before


def corrupt(root):
    (root / fx.SOURCE).write_bytes(b"synthetic corruption")


def assert_not_attempted(result):
    assert result == {
        "status": "NOT_ATTEMPTED",
        "error_code": "NOT_ATTEMPTED",
        "verification": None,
    }


@pytest.mark.parametrize("outcome", ["SUCCEEDED", "FAILED"])
def test_valid_exact_report(tmp_path, outcome):
    primary, kwargs = fx.fixture(tmp_path / "primary", outcome=outcome)
    secondary = tmp_path / "secondary"
    shutil.copytree(primary, secondary)
    bundles = primary, secondary, kwargs
    report = unchanged(bundles, lambda: run(bundles))
    expected_verification = ep.verify_bundle(primary, **kwargs)
    assert report == {
        "report_schema_version": 1,
        "classification": "PAIR_VERIFIED",
        "run_id": kwargs["expected_run_id"],
        "attempt_id": kwargs["expected_attempt_id"],
        "manifest_sha256": kwargs["expected_manifest_sha256"],
        "budget_exhausted": False,
        "primary": {
            "status": "VERIFIED", "error_code": None,
            "verification": expected_verification,
        },
        "secondary": {
            "status": "VERIFIED", "error_code": None,
            "verification": expected_verification,
        },
        "storage_independence": "NOT_ATTESTED",
    }


@pytest.mark.parametrize("bad", ["primary", "secondary", "both"])
def test_corrupt_copies_are_independently_reported(bundles, bad):
    if bad in {"primary", "both"}:
        corrupt(bundles[0])
    if bad in {"secondary", "both"}:
        corrupt(bundles[1])
    report = unchanged(bundles, lambda: run(bundles))
    assert report["classification"] == "PAIR_NOT_VERIFIED"
    assert report["budget_exhausted"] is False
    for name in ("primary", "secondary"):
        failed = bad in {name, "both"}
        assert report[name]["status"] == ("FAILED" if failed else "VERIFIED")
        assert report[name]["error_code"] == (
            "VERIFICATION_FAILED" if failed else None
        )


@pytest.mark.parametrize("field", [
    "expected_manifest_sha256",
    "expected_predeclaration_sha256",
    "expected_artifact_list_sha256",
    "expected_run_id",
    "expected_attempt_id",
])
def test_well_formed_wrong_anchors_fail_both(bundles, field):
    value = (
        "00000000-0000-4000-8000-000000000000"
        if field.endswith("_id") else "0" * 64
    )
    report = unchanged(bundles, lambda: run(bundles, **{field: value}))
    for name in ("primary", "secondary"):
        assert report[name]["error_code"] == "VERIFICATION_FAILED"
    assert report["classification"] == "PAIR_NOT_VERIFIED"


@pytest.mark.parametrize("field,value", [
    ("max_runtime_seconds", True),
    ("max_runtime_seconds", False),
    ("max_runtime_seconds", 0),
    ("max_runtime_seconds", -1),
    ("max_runtime_seconds", math.inf),
    ("max_runtime_seconds", math.nan),
    ("max_runtime_seconds", "5"),
    ("max_runtime_seconds", None),
    ("max_artifacts", True),
    ("max_metadata_bytes", 0),
    ("max_logical_bytes", -1),
])
def test_invalid_limits_before_clock_or_filesystem(
    bundles, monkeypatch, field, value
):
    limits = dict(bundles[2]["limits"])
    limits[field] = value

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid inputs must reject before clock or roots")

    monkeypatch.setattr(pair, "_roots", forbidden)
    with pytest.raises(pair.PairInputError) as caught:
        unchanged(
            bundles,
            lambda: run(bundles, limits=limits, clock=forbidden),
        )
    assert caught.value.code == "INVALID_INPUT"
    assert not isinstance(caught.value, ep.RuntimeLimitExceeded)


@pytest.mark.parametrize("field,value", [
    ("expected_run_id", "bad"),
    ("expected_attempt_id", "bad"),
    ("expected_manifest_sha256", "bad"),
    ("expected_predeclaration_sha256", "bad"),
    ("expected_artifact_list_sha256", "bad"),
    ("clock", None),
])
def test_invalid_anchor_or_clock_before_filesystem(
    bundles, monkeypatch, field, value
):
    def forbidden(*args, **kwargs):
        raise AssertionError("No filesystem inspection permitted")

    monkeypatch.setattr(pair, "_roots", forbidden)
    options = {field: value}
    if field != "clock":
        options["clock"] = forbidden
    with pytest.raises(pair.PairInputError) as caught:
        unchanged(bundles, lambda: run(bundles, **options))
    assert caught.value.code == "INVALID_INPUT"


@pytest.mark.parametrize("case", [
    "missing", "relative", "symlink", "parent_symlink",
    "identical", "overlap", "file",
])
def test_invalid_roots(bundles, tmp_path, monkeypatch, case):
    primary, secondary, kwargs = bundles
    if case == "missing":
        secondary = tmp_path / "absent"
    elif case == "relative":
        secondary = Path("relative")
    elif case == "symlink":
        link = tmp_path / "link"
        link.symlink_to(secondary, target_is_directory=True)
        secondary = link
    elif case == "parent_symlink":
        link = tmp_path / "parent_link"
        link.symlink_to(tmp_path, target_is_directory=True)
        secondary = link / "secondary"
    elif case == "identical":
        secondary = primary
    elif case == "overlap":
        secondary = primary / "evidence"
    elif case == "file":
        secondary = primary / "manifest.json"

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid roots must not invoke content verifier")

    monkeypatch.setattr(ep, "verify_bundle", forbidden)
    with pytest.raises(pair.PairInputError) as caught:
        unchanged(
            bundles,
            lambda: pair.verify_synthetic_pair(primary, secondary, **kwargs),
        )
    assert caught.value.code == "INVALID_ROOTS"


def test_same_directory_identity_rejected(bundles, monkeypatch):
    original = Path.stat
    identity = original(bundles[0])

    def aliased(root, *args, **kwargs):
        if root == bundles[1]:
            return identity
        return original(root, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", aliased)
    with pytest.raises(pair.PairInputError) as caught:
        run(bundles)
    assert caught.value.code == "INVALID_ROOTS"


@pytest.mark.parametrize("phase", [0, 1])
@pytest.mark.parametrize("error,code", [
    (ep.VerificationError, "VERIFICATION_FAILED"),
    (OSError, "IO_ERROR"),
])
def test_phase_failure_classification(bundles, monkeypatch, phase, error, code):
    original = ep.verify_bundle

    def verifying(root, **kwargs):
        if root == bundles[phase]:
            raise error("private detail must not enter report")
        return original(root, **kwargs)

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(bundles, lambda: run(bundles))
    name = ("primary", "secondary")[phase]
    assert report[name] == {
        "status": "FAILED", "error_code": code, "verification": None,
    }
    assert report[("secondary", "primary")[phase]]["status"] == "VERIFIED"
    assert "private detail" not in repr(report)


def test_shared_budget_reduced_and_same_clock(bundles, monkeypatch):
    clock = Clock()
    original = ep.verify_bundle
    seen = []

    def verifying(root, **kwargs):
        seen.append((kwargs["limits"]["max_runtime_seconds"], kwargs["clock"]))
        result = original(root, **kwargs)
        if root == bundles[0]:
            clock.now = 4.0
        return result

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(bundles, lambda: run(bundles, clock=clock))
    assert seen == [(5.0, clock), (1.0, clock)]
    assert report["classification"] == "PAIR_VERIFIED"


def test_exhaustion_before_primary_never_calls_verifier(bundles, monkeypatch):
    ticks = iter([0.0, 5.0, 5.0])

    def forbidden(*args, **kwargs):
        raise AssertionError("Verifier must not start")

    monkeypatch.setattr(ep, "verify_bundle", forbidden)
    report = unchanged(
        bundles, lambda: run(bundles, clock=lambda: next(ticks))
    )
    assert_not_attempted(report["primary"])
    assert_not_attempted(report["secondary"])
    assert report["budget_exhausted"] is True
    assert report["classification"] == "PAIR_NOT_VERIFIED"


def test_exhaustion_at_secondary_precall(bundles, monkeypatch):
    original = ep.verify_bundle
    seen = []
    ticks = iter([0.0, 0.0, 4.0, 5.0, 5.0])

    def verifying(root, **kwargs):
        seen.append(root)
        # Genuine verification with a fixed clock; operation checks use ticks.
        options = dict(kwargs)
        options["clock"] = lambda: 0.0
        return original(root, **options)

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(
        bundles, lambda: run(bundles, clock=lambda: next(ticks))
    )
    assert seen == [bundles[0]]
    assert report["primary"]["status"] == "VERIFIED"
    assert_not_attempted(report["secondary"])
    assert report["budget_exhausted"] is True


@pytest.mark.parametrize("phase", [0, 1])
def test_real_runtime_subtype_at_pair_call_sites(bundles, monkeypatch, phase):
    clock = Clock()
    original_verify = ep.verify_bundle
    original_tick = ep._Reader.tick
    observed = []

    def verifying(root, **kwargs):
        if root != bundles[phase]:
            return original_verify(root, **kwargs)

        def exhausting(reader):
            clock.now = 6.0
            return original_tick(reader)

        with monkeypatch.context() as patch:
            patch.setattr(ep._Reader, "tick", exhausting)
            try:
                return original_verify(root, **kwargs)
            except ep.RuntimeLimitExceeded as exc:
                observed.append(type(exc))
                assert isinstance(exc, ep.VerificationError)
                raise

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(bundles, lambda: run(bundles, clock=clock))
    assert observed == [ep.RuntimeLimitExceeded]
    assert report[("primary", "secondary")[phase]]["error_code"] == "RESOURCE_LIMIT"
    assert report["budget_exhausted"] is True
    assert report["classification"] == "PAIR_NOT_VERIFIED"
    if phase == 0:
        assert_not_attempted(report["secondary"])
    else:
        assert report["primary"]["status"] == "VERIFIED"


@pytest.mark.parametrize("phase", [0, 1])
@pytest.mark.parametrize("error,code", [
    (ep.VerificationError, "VERIFICATION_FAILED"),
    (OSError, "IO_ERROR"),
])
def test_unrelated_failure_coinciding_with_expiry_keeps_code(
    bundles, monkeypatch, phase, error, code
):
    clock = Clock()
    original = ep.verify_bundle

    def verifying(root, **kwargs):
        if root == bundles[phase]:
            clock.now = 6.0
            raise error("unrelated failure")
        return original(root, **kwargs)

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(bundles, lambda: run(bundles, clock=clock))
    assert report[("primary", "secondary")[phase]]["error_code"] == code
    assert report["budget_exhausted"] is True
    if phase == 0:
        assert_not_attempted(report["secondary"])


@pytest.mark.parametrize("phase", [0, 1])
def test_success_followed_by_expiry_is_never_downgraded(
    bundles, monkeypatch, phase
):
    clock = Clock()
    original = ep.verify_bundle

    def verifying(root, **kwargs):
        result = original(root, **kwargs)
        if root == bundles[phase]:
            clock.now = 5.0
        return result

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(bundles, lambda: run(bundles, clock=clock))
    assert report["primary"]["status"] == "VERIFIED"
    assert report["primary"]["error_code"] is None
    if phase == 0:
        assert_not_attempted(report["secondary"])
    else:
        assert report["secondary"]["status"] == "VERIFIED"
        assert report["secondary"]["error_code"] is None
    assert report["budget_exhausted"] is True
    assert report["classification"] == "PAIR_NOT_VERIFIED"


def test_final_check_retains_both_successes(bundles, monkeypatch):
    original = ep.verify_bundle
    ticks = iter([0.0, 0.0, 1.0, 1.0, 4.0, 5.0])

    def verifying(root, **kwargs):
        options = dict(kwargs)
        options["clock"] = lambda: 0.0
        return original(root, **options)

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(
        bundles, lambda: run(bundles, clock=lambda: next(ticks))
    )
    assert report["primary"]["status"] == "VERIFIED"
    assert report["secondary"]["status"] == "VERIFIED"
    assert report["budget_exhausted"] is True
    assert report["classification"] == "PAIR_NOT_VERIFIED"


def test_runtime_signal_stops_even_if_clock_has_not_advanced(
    bundles, monkeypatch
):
    seen = []

    def verifying(root, **kwargs):
        seen.append(root)
        raise ep.RuntimeLimitExceeded("Runtime limit exceeded")

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    report = unchanged(bundles, lambda: run(bundles, clock=Clock()))
    assert seen == [bundles[0]]
    assert report["primary"]["error_code"] == "RESOURCE_LIMIT"
    assert_not_attempted(report["secondary"])
    assert report["budget_exhausted"] is True


@pytest.mark.parametrize("phase", [0, 1])
def test_programming_errors_propagate(bundles, monkeypatch, phase):
    original = ep.verify_bundle

    def verifying(root, **kwargs):
        if root == bundles[phase]:
            raise RuntimeError("synthetic programming error")
        return original(root, **kwargs)

    monkeypatch.setattr(ep, "verify_bundle", verifying)
    with pytest.raises(RuntimeError, match="synthetic programming error"):
        unchanged(bundles, lambda: run(bundles))
