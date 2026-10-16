"""Synthetic-only tests for the read-only Increment 1 verifier."""
import copy
import hashlib
import json
import math
import uuid

import pytest

from L1_CORE.market_data_platform import evidence_preservation as ep

LIMITS = {
    "max_artifacts": 64,
    "max_metadata_bytes": 262144,
    "max_logical_bytes": 2097152,
    "max_runtime_seconds": 5,
}
SOURCE = "evidence/source/analyzer.py"
RESULT = "evidence/results/result.json"


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def put(root, name, raw):
    destination = root / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)


def reseal(root, kwargs):
    """Test-only resealing: intentionally supply new independent anchors."""
    manifest = json.loads((root / "manifest.json").read_bytes())
    for record in manifest["artifacts"]:
        raw = (root / record["relative_path"]).read_bytes()
        record["size_bytes"] = len(raw)
        record["sha256"] = digest(raw)
    manifest["artifact_list_sha256"] = digest(
        (root / "artifact_list.json").read_bytes()
    )
    manifest["predeclaration_sha256"] = digest(
        (root / ep.SINGLETONS["PREDECLARATION"]).read_bytes()
    )
    put(root, "manifest.json", encoded(manifest))
    kwargs["expected_manifest_sha256"] = digest(encoded(manifest))
    kwargs["expected_artifact_list_sha256"] = manifest["artifact_list_sha256"]
    kwargs["expected_predeclaration_sha256"] = manifest["predeclaration_sha256"]


def fixture(root, outcome="SUCCEEDED"):
    root.mkdir()
    run_id, attempt_id = str(uuid.uuid4()), str(uuid.uuid4())
    records = []
    for role, name in ep.SINGLETONS.items():
        records.append({
            "relative_path": name, "role": role,
            "required_on_success": True, "required_on_failure": True,
        })
    records += [
        {"relative_path": SOURCE, "role": "SOURCE",
         "required_on_success": True, "required_on_failure": True},
        {"relative_path": RESULT, "role": "RESULT",
         "required_on_success": True, "required_on_failure": False},
    ]
    artifact_list = {"schema_version": 1, "run_id": run_id, "artifacts": records}
    provenance = {
        "schema_version": 1, "run_id": run_id, "attempt_id": attempt_id,
        "run_outcome": outcome, "host_id": "synthetic-host",
        "source_revision": "a" * 40,
        "source_files": [{
            "source_path": "analyzer.py", "artifact_path": SOURCE,
            "sha256": digest(b"# synthetic source\n"),
        }],
        "dependencies": [{"name": "python", "version": "synthetic-version"}],
        "parameters": {"synthetic": True}, "input_identity": {"fixture": "001"},
        "started_utc": "2026-10-15T00:00:00Z",
        "ended_utc": "2026-10-15T00:00:01.123456Z",
    }
    evidence = {
        ep.SINGLETONS["PREDECLARATION"]: b"synthetic predeclaration",
        ep.SINGLETONS["AUTHORIZATION"]: b"synthetic authorization only",
        ep.SINGLETONS["PROVENANCE"]: encoded(provenance),
        ep.SINGLETONS["EXECUTION_LOG"]: b"",
        SOURCE: b"# synthetic source\n",
    }
    if outcome == "SUCCEEDED":
        evidence[RESULT] = b'{"synthetic_result":true}'
    for name, raw in evidence.items():
        put(root, name, raw)
    put(root, "artifact_list.json", encoded(artifact_list))
    manifest = {
        "schema_version": 1, "run_id": run_id, "attempt_id": attempt_id,
        "run_outcome": outcome,
        "predeclaration_sha256": digest(evidence[ep.SINGLETONS["PREDECLARATION"]]),
        "artifact_list_sha256": digest(encoded(artifact_list)),
        "artifacts": [
            {"relative_path": name,
             "role": next(r["role"] for r in records if r["relative_path"] == name),
             "size_bytes": len(raw), "sha256": digest(raw)}
            for name, raw in evidence.items()
        ],
    }
    put(root, "manifest.json", encoded(manifest))
    kwargs = {
        "expected_manifest_sha256": digest(encoded(manifest)),
        "expected_predeclaration_sha256": manifest["predeclaration_sha256"],
        "expected_artifact_list_sha256": manifest["artifact_list_sha256"],
        "expected_run_id": run_id, "expected_attempt_id": attempt_id,
        "limits": dict(LIMITS),
    }
    return root, kwargs


@pytest.fixture
def bundle(tmp_path):
    return fixture(tmp_path / "bundle")


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*") if p.is_file() and not p.is_symlink()
    }


def reject_unchanged(root, kwargs, match):
    before = snapshot(root)
    with pytest.raises(ep.VerificationError, match=match):
        ep.verify_bundle(root, **kwargs)
    assert snapshot(root) == before


@pytest.mark.parametrize("outcome,count", [("SUCCEEDED", 6), ("FAILED", 5)])
def test_valid_outcomes_exact_result_and_no_writes(tmp_path, outcome, count):
    root, kwargs = fixture(tmp_path / "bundle", outcome)
    before = snapshot(root)
    result = ep.verify_bundle(root, **kwargs)
    assert result == {
        "classification": "INCREMENT_1_INTEGRITY_VERIFIED",
        "run_id": kwargs["expected_run_id"],
        "attempt_id": kwargs["expected_attempt_id"],
        "run_outcome": outcome,
        "manifest_sha256": kwargs["expected_manifest_sha256"],
        "verified_artifact_count": count,
        "verified_logical_bytes": sum(map(len, before.values())),
    }
    assert snapshot(root) == before


@pytest.mark.parametrize("field", [
    "expected_manifest_sha256", "expected_predeclaration_sha256",
    "expected_artifact_list_sha256",
])
def test_external_digest_mismatch(bundle, field):
    root, kwargs = bundle
    kwargs[field] = "0" * 64
    reject_unchanged(root, kwargs, "digest mismatch|anchor mismatch")


@pytest.mark.parametrize("field", ["expected_run_id", "expected_attempt_id"])
def test_external_identity_mismatch(bundle, field):
    root, kwargs = bundle
    kwargs[field] = str(uuid.uuid4())
    reject_unchanged(root, kwargs, "identity mismatch")


@pytest.mark.parametrize("name", [
    SOURCE, RESULT, "evidence/authorization.txt", "evidence/provenance.json",
    "manifest.json", "artifact_list.json",
])
def test_changed_bytes_rejected(bundle, name):
    root, kwargs = bundle
    original = (root / name).read_bytes()
    (root / name).write_bytes(b"X" + original[1:])
    reject_unchanged(root, kwargs, "digest mismatch")


def test_missing_required_file(bundle):
    root, kwargs = bundle
    (root / SOURCE).unlink()
    reject_unchanged(root, kwargs, "Missing file")


def test_required_declaration_not_in_manifest(bundle):
    root, kwargs = bundle
    document = json.loads((root / "manifest.json").read_bytes())
    document["artifacts"] = [
        r for r in document["artifacts"] if r["relative_path"] != SOURCE
    ]
    put(root, "manifest.json", encoded(document))
    kwargs["expected_manifest_sha256"] = digest(encoded(document))
    reject_unchanged(root, kwargs, "Missing required evidence")


@pytest.mark.parametrize("name,field,value,error", [
    ("manifest.json", "schema_version", True, "schema version"),
    ("manifest.json", "schema_version", 999, "schema version"),
    ("manifest.json", "run_outcome", "UNKNOWN", "run outcome"),
    ("manifest.json", "extra", True, "manifest schema"),
    ("artifact_list.json", "schema_version", True, "schema version"),
    ("artifact_list.json", "extra", True, "artifact list schema"),
    ("evidence/provenance.json", "schema_version", True, "schema version"),
    ("evidence/provenance.json", "extra", True, "provenance schema"),
    ("evidence/provenance.json", "source_revision", "bad", "source revision"),
    ("evidence/provenance.json", "host_id", " ", "host ID"),
    ("evidence/provenance.json", "parameters", [], "provenance objects"),
    ("evidence/provenance.json", "input_identity", [], "provenance objects"),
    ("evidence/provenance.json", "started_utc", "invalid", "UTC timestamp"),
    ("evidence/provenance.json", "ended_utc", "2026-10-14T00:00:00Z",
     "timestamp order"),
    ("evidence/provenance.json", "attempt_id", str(uuid.uuid4()),
     "identity mismatch"),
])
def test_metadata_schema_validation(bundle, name, field, value, error):
    root, kwargs = bundle
    document = json.loads((root / name).read_bytes())
    document[field] = value
    put(root, name, encoded(document))
    reseal(root, kwargs)
    reject_unchanged(root, kwargs, error)


@pytest.mark.parametrize("name", [
    "manifest.json", "artifact_list.json", "evidence/provenance.json",
])
def test_duplicate_json_keys(bundle, name):
    root, kwargs = bundle
    raw = (root / name).read_bytes()
    put(root, name, b'{"schema_version":1,' + raw[1:])
    if name == "manifest.json":
        kwargs["expected_manifest_sha256"] = digest((root / name).read_bytes())
    else:
        reseal(root, kwargs)
    reject_unchanged(root, kwargs, "Duplicate JSON key")


@pytest.mark.parametrize("injected", ["NaN", "Infinity", "1e999"])
def test_nonfinite_nested_json(bundle, injected):
    root, kwargs = bundle
    name = "evidence/provenance.json"
    raw = (root / name).read_bytes()
    raw = raw.replace(b'"parameters": {"synthetic": true}',
                      ('"parameters": {"number": ' + injected + '}').encode())
    put(root, name, raw)
    reseal(root, kwargs)
    reject_unchanged(root, kwargs, "Nonfinite JSON number")


@pytest.mark.parametrize("mutation,error", [
    ("duplicate_source", "Duplicate source record"),
    ("source_extra", "source record schema"),
    ("wrong_source_digest", "Source digest binding"),
    ("wrong_source_artifact", "Source artifact binding"),
    ("duplicate_dependency", "Duplicate dependency name"),
    ("dependency_extra", "dependency record schema"),
    ("empty_dependency", "dependency version"),
])
def test_nested_provenance_records(bundle, mutation, error):
    root, kwargs = bundle
    name = "evidence/provenance.json"
    document = json.loads((root / name).read_bytes())
    if mutation == "duplicate_source":
        document["source_files"] *= 2
    elif mutation == "source_extra":
        document["source_files"][0]["extra"] = True
    elif mutation == "wrong_source_digest":
        document["source_files"][0]["sha256"] = "0" * 64
    elif mutation == "wrong_source_artifact":
        document["source_files"][0]["artifact_path"] = RESULT
    elif mutation == "duplicate_dependency":
        document["dependencies"] *= 2
    elif mutation == "dependency_extra":
        document["dependencies"][0]["extra"] = True
    else:
        document["dependencies"][0]["version"] = ""
    put(root, name, encoded(document))
    reseal(root, kwargs)
    reject_unchanged(root, kwargs, error)


@pytest.mark.parametrize("bad_path", [
    "/absolute", "../escape", "evidence/../escape", "evidence//file",
    "evidence/./file", "evidence\\file", "manifest.json",
    "evidence/results/source.py",
])
def test_invalid_declaration_paths(bundle, bad_path):
    root, kwargs = bundle
    name = "artifact_list.json"
    document = json.loads((root / name).read_bytes())
    next(r for r in document["artifacts"] if r["role"] == "SOURCE")[
        "relative_path"
    ] = bad_path
    put(root, name, encoded(document))
    reseal(root, kwargs)
    reject_unchanged(root, kwargs, "Unsafe relative path|role/path containment")


@pytest.mark.parametrize("mutation,error", [
    ("duplicate", "Duplicate artifact path"),
    ("extra", "artifact declaration schema"),
    ("boolean", "Invalid requirement flag"),
    ("optional_source", "Mandatory role"),
    ("prefix", "prefix collision"),
])
def test_artifact_declaration_validation(bundle, mutation, error):
    root, kwargs = bundle
    name = "artifact_list.json"
    document = json.loads((root / name).read_bytes())
    source = next(r for r in document["artifacts"] if r["role"] == "SOURCE")
    if mutation == "duplicate":
        document["artifacts"].append(copy.deepcopy(source))
    elif mutation == "extra":
        source["extra"] = True
    elif mutation == "boolean":
        source["required_on_success"] = 1
    elif mutation == "optional_source":
        source["required_on_failure"] = False
    else:
        additional = copy.deepcopy(source)
        additional["relative_path"] = SOURCE + "/child"
        document["artifacts"].append(additional)
    put(root, name, encoded(document))
    reseal(root, kwargs)
    reject_unchanged(root, kwargs, error)


@pytest.mark.parametrize("mutation,error", [
    ("duplicate", "Duplicate artifact path"),
    ("size_bool", "Invalid artifact size"),
    ("size_wrong", "Artifact size mismatch"),
    ("extra", "present artifact schema"),
    ("role", "role/path containment"),
])
def test_manifest_artifact_records(bundle, mutation, error):
    root, kwargs = bundle
    name = "manifest.json"
    document = json.loads((root / name).read_bytes())
    record = next(r for r in document["artifacts"] if r["relative_path"] == SOURCE)
    if mutation == "duplicate":
        document["artifacts"].append(copy.deepcopy(record))
    elif mutation == "size_bool":
        record["size_bytes"] = True
    elif mutation == "size_wrong":
        record["size_bytes"] += 1
    elif mutation == "extra":
        record["extra"] = True
    else:
        record["role"] = "RESULT"
    put(root, name, encoded(document))
    kwargs["expected_manifest_sha256"] = digest(encoded(document))
    reject_unchanged(root, kwargs, error)


@pytest.mark.parametrize("entry", ["file", "directory"])
def test_unexpected_entries(bundle, entry):
    root, kwargs = bundle
    if entry == "file":
        put(root, "unexpected.bin", b"x")
    else:
        (root / "unexpected").mkdir()
    reject_unchanged(root, kwargs, "Unexpected bundle inventory")


@pytest.mark.parametrize("location", ["root", "parent", "evidence", "source", "file"])
def test_symlinked_roots_and_components(bundle, tmp_path, location):
    root, kwargs = bundle
    if location in {"root", "parent"}:
        alias = tmp_path / "alias"
        alias.symlink_to(root if location == "root" else root.parent,
                         target_is_directory=True)
        candidate = alias if location == "root" else alias / root.name
        with pytest.raises(ep.VerificationError, match="absolute and canonical"):
            ep.verify_bundle(candidate, **kwargs)
        return
    original = root / {
        "evidence": "evidence", "source": "evidence/source", "file": SOURCE,
    }[location]
    outside = tmp_path / "moved"
    original.rename(outside)
    original.symlink_to(outside, target_is_directory=outside.is_dir())
    reject_unchanged(root, kwargs, "Symlinked bundle component")


@pytest.mark.parametrize("field,value,error", [
    ("max_artifacts", 1, "Artifact count limit"),
    ("max_metadata_bytes", 1, "Metadata byte limit"),
    ("max_logical_bytes", 1, "Logical byte limit"),
    ("max_artifacts", True, "Invalid limit"),
    ("max_metadata_bytes", 0, "Invalid limit"),
    ("max_logical_bytes", -1, "Invalid limit"),
    ("max_runtime_seconds", True, "Invalid limit"),
    ("max_runtime_seconds", math.inf, "Invalid limit"),
    ("max_runtime_seconds", math.nan, "Invalid limit"),
])
def test_resource_limits(bundle, field, value, error):
    root, kwargs = bundle
    kwargs["limits"][field] = value
    reject_unchanged(root, kwargs, error)


def test_runtime_limit_injected_clock(bundle):
    root, kwargs = bundle
    ticks = iter([0.0, 6.0])
    kwargs["clock"] = lambda: next(ticks)
    reject_unchanged(root, kwargs, "Runtime limit exceeded")


def test_observed_change_during_read(bundle, monkeypatch):
    root, kwargs = bundle
    original_read = ep._Reader.read
    changed = False

    def changing_read(reader, name, **options):
        nonlocal changed
        result = original_read(reader, name, **options)
        if name == SOURCE and not changed:
            changed = True
            original_bytes = (root / SOURCE).read_bytes()
            (root / SOURCE).write_bytes(b"X" * len(original_bytes))
        return result

    monkeypatch.setattr(ep._Reader, "read", changing_read)
    with pytest.raises(ep.VerificationError, match="Bundle changed"):
        ep.verify_bundle(root, **kwargs)
    assert changed


def test_nonadjacent_file_directory_prefix_collision(bundle):
    root, kwargs = bundle
    name = "artifact_list.json"
    document = json.loads((root / name).read_bytes())
    template = next(
        record for record in document["artifacts"]
        if record["role"] == "SOURCE"
    )
    for relative in (
        "evidence/source/a",
        "evidence/source/a-keep",
        "evidence/source/a/child",
    ):
        record = copy.deepcopy(template)
        record["relative_path"] = relative
        document["artifacts"].append(record)

    put(root, name, encoded(document))
    reseal(root, kwargs)
    reject_unchanged(
        root, kwargs, "^File/directory prefix collision$"
    )


@pytest.mark.parametrize("metadata", ["declaration", "provenance"])
def test_deep_metadata_path_rejected_before_prefix_processing(
    bundle, monkeypatch, metadata
):
    root, kwargs = bundle
    if metadata == "declaration":
        name = "artifact_list.json"
        document = json.loads((root / name).read_bytes())
        record = next(
            r for r in document["artifacts"] if r["role"] == "SOURCE"
        )
        record["relative_path"] = "evidence/source/" + "/".join(["a"] * 10000)
    else:
        name = "evidence/provenance.json"
        document = json.loads((root / name).read_bytes())
        document["source_files"][0]["source_path"] = "/".join(["a"] * 10000)

    put(root, name, encoded(document))
    reseal(root, kwargs)

    metadata_size = sum(
        (root / item).stat().st_size
        for item in (
            "manifest.json", "artifact_list.json", "evidence/provenance.json"
        )
    )
    assert metadata_size < kwargs["limits"]["max_metadata_bytes"]

    original_unique = ep._unique_paths
    reached = []

    def guarded_unique(records):
        names = set(records)
        assert all(
            len(item.split("/")) <= ep.MAX_PATH_COMPONENTS
            for item in names
        ), "Overdeep path reached prefix processing"
        reached.append(names)
        return original_unique(names)

    monkeypatch.setattr(ep, "_unique_paths", guarded_unique)
    reject_unchanged(root, kwargs, "^Path depth limit exceeded$")
    if metadata == "declaration":
        assert reached == []
    else:
        # Normal declarations were checked before provenance validation.
        assert len(reached) == 1


def test_path_depth_boundary():
    assert ep._path("/".join(["a"] * 128)) == "/".join(["a"] * 128)
    with pytest.raises(ep.VerificationError, match="^Path depth limit exceeded$"):
        ep._path("/".join(["a"] * 129))


def test_runtime_exhaustion_has_distinct_compatible_exception(bundle):
    root, kwargs = bundle
    before = snapshot(root)
    ticks = iter([0.0, 6.0])
    kwargs["clock"] = lambda: next(ticks)

    with pytest.raises(
        ep.RuntimeLimitExceeded, match="^Runtime limit exceeded$"
    ) as caught:
        ep.verify_bundle(root, **kwargs)

    assert type(caught.value) is ep.RuntimeLimitExceeded
    assert isinstance(caught.value, ep.VerificationError)
    assert snapshot(root) == before


@pytest.mark.parametrize("seconds", [
    True, False, 0, -1, math.inf, math.nan, "5", None,
])
def test_invalid_runtime_limit_is_not_exhaustion(bundle, seconds):
    root, kwargs = bundle
    before = snapshot(root)
    kwargs["limits"]["max_runtime_seconds"] = seconds

    def unexpected_clock():
        raise AssertionError("Invalid limit must reject before clock access")

    kwargs["clock"] = unexpected_clock
    with pytest.raises(
        ep.VerificationError, match="^Invalid limit: max_runtime_seconds$"
    ) as caught:
        ep.verify_bundle(root, **kwargs)

    assert type(caught.value) is ep.VerificationError
    assert not isinstance(caught.value, ep.RuntimeLimitExceeded)
    assert snapshot(root) == before
