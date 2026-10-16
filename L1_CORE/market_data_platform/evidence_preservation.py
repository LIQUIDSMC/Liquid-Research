"""Increment 1: read-only integrity verification of synthetic evidence.

No copying, publication, cleanup, research execution, or production adoption.
Requires a quiescent fixture; filesystem checks are not an atomic snapshot.
"""
import hashlib
import json
import math
import os
import re
import stat
import time
import uuid
from datetime import datetime
from pathlib import Path

MAX_PATH_COMPONENTS = 128

CONTROLS = {"manifest.json", "artifact_list.json"}
SINGLETONS = {
    "PREDECLARATION": "evidence/predeclaration.txt",
    "AUTHORIZATION": "evidence/authorization.txt",
    "PROVENANCE": "evidence/provenance.json",
    "EXECUTION_LOG": "evidence/execution.log",
}
ROLES = set(SINGLETONS) | {"SOURCE", "RESULT"}
MANIFEST_FIELDS = {
    "schema_version", "run_id", "attempt_id", "run_outcome",
    "predeclaration_sha256", "artifact_list_sha256", "artifacts",
}
PROVENANCE_FIELDS = {
    "schema_version", "run_id", "attempt_id", "run_outcome", "host_id",
    "source_revision", "source_files", "dependencies", "parameters",
    "started_utc", "ended_utc", "input_identity",
}
LIMIT_FIELDS = {
    "max_artifacts", "max_metadata_bytes", "max_logical_bytes",
    "max_runtime_seconds",
}


class VerificationError(ValueError):
    """Evidence is invalid, changed, or exceeds a verification limit."""


class RuntimeLimitExceeded(VerificationError):
    """Verification exhausted its cooperative runtime allowance."""


def _require(condition, message):
    if not condition:
        raise VerificationError(message)


def _schema(value, fields, label):
    _require(type(value) is dict and set(value) == fields,
             f"Invalid {label} schema")


def _text(value, label):
    _require(type(value) is str and bool(value.strip()), f"Invalid {label}")


def _uuid(value):
    _text(value, "UUID")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise VerificationError("Invalid UUID") from exc
    _require(str(parsed) == value, "Noncanonical UUID")


def _digest(value):
    _require(type(value) is str and
             re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             "Invalid SHA-256 digest")


def _path(value):
    _text(value, "relative path")
    _require("\\" not in value and "\x00" not in value,
             "Unsafe relative path")
    parts = value.split("/")
    _require(len(parts) <= MAX_PATH_COMPONENTS,
             "Path depth limit exceeded")
    _require(not value.startswith("/") and
             all(part not in {"", ".", ".."} for part in parts),
             "Unsafe relative path")
    return value


def _role_path(name, role):
    _path(name)
    _require(type(role) is str and role in ROLES, "Invalid artifact role")
    if role in SINGLETONS:
        _require(name == SINGLETONS[role], "Invalid singleton artifact path")
    else:
        prefix = "evidence/source/" if role == "SOURCE" else "evidence/results/"
        _require(name.startswith(prefix), "Invalid role/path containment")


def _version(document):
    _require(type(document["schema_version"]) is int and
             document["schema_version"] == 1, "Invalid schema version")


def _identity(document, run_id, attempt_id=None, outcome=None):
    _uuid(document["run_id"])
    _require(document["run_id"] == run_id, "Run identity mismatch")
    if attempt_id is not None:
        _uuid(document["attempt_id"])
        _require(document["attempt_id"] == attempt_id, "Attempt identity mismatch")
    if outcome is not None:
        _require(document["run_outcome"] == outcome, "Run outcome mismatch")


def _outcome(value):
    _require(type(value) is str and value in {"SUCCEEDED", "FAILED"},
             "Invalid run outcome")


def _timestamp(value):
    _require(type(value) is str and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
    ) is not None, "Invalid UTC timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise VerificationError("Invalid UTC timestamp") from exc


def _unique_paths(records):
    names = set(records)
    for name in names:
        parts = name.split("/")
        for index in range(1, len(parts)):
            _require("/".join(parts[:index]) not in names,
                     "File/directory prefix collision")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _bad_constant(value):
    raise VerificationError(f"Nonfinite JSON number: {value}")


def _finite_json(value):
    if type(value) is float:
        _require(math.isfinite(value), "Nonfinite JSON number")
    elif type(value) is dict:
        for child in value.values():
            _finite_json(child)
    elif type(value) is list:
        for child in value:
            _finite_json(child)


def _json(raw):
    try:
        result = json.loads(raw, object_pairs_hook=_pairs,
                            parse_constant=_bad_constant)
        _finite_json(result)
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise VerificationError("Invalid JSON metadata") from exc


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


class _Reader:
    def __init__(self, root, limits, clock):
        _schema(limits, LIMIT_FIELDS, "limits")
        for name in LIMIT_FIELDS - {"max_runtime_seconds"}:
            _require(type(limits[name]) is int and limits[name] > 0,
                     f"Invalid limit: {name}")
        seconds = limits["max_runtime_seconds"]
        _require(type(seconds) in {int, float} and
                 math.isfinite(seconds) and seconds > 0,
                 "Invalid limit: max_runtime_seconds")
        self.root = Path(root)
        _require(self.root.is_absolute() and
                 str(self.root) == str(self.root.resolve()),
                 "Root must be absolute and canonical")
        self.limits = dict(limits)
        self.clock = clock
        self.started = clock()
        self.initial = self.scan()

    def tick(self):
        if not self.clock() - self.started < self.limits["max_runtime_seconds"]:
            raise RuntimeLimitExceeded("Runtime limit exceeded")

    def scan(self):
        records = {}
        pending = [(self.root, "")]
        files = 0
        logical = 0
        # Every permitted directory is a parent of an evidence file.
        # This also bounds traversal of hostile trees before metadata parsing.
        maximum_entries = 1 + (self.limits["max_artifacts"] + 2) * (MAX_PATH_COMPONENTS + 1)
        while pending:
            self.tick()
            current, relative = pending.pop()
            info = current.lstat()
            _require(not stat.S_ISLNK(info.st_mode), "Symlinked bundle component")
            records[relative] = _signature(info)
            _require(len(records) <= maximum_entries, "Tree entry limit exceeded")
            if stat.S_ISDIR(info.st_mode):
                with os.scandir(current) as children:
                    for child in children:
                        self.tick()
                        name = f"{relative}/{child.name}" if relative else child.name
                        _path(name)
                        _require(len(pending) + len(records) < maximum_entries,
                                 "Tree entry limit exceeded")
                        pending.append((Path(child.path), name))
            else:
                _require(stat.S_ISREG(info.st_mode), "Nonregular bundle entry")
                files += 1
                logical += info.st_size
                _require(files <= self.limits["max_artifacts"] + 2,
                         "Artifact count limit exceeded")
                _require(logical <= self.limits["max_logical_bytes"],
                         "Logical byte limit exceeded")
        _require(stat.S_ISDIR(records[""][2]), "Bundle root is not a directory")
        return records

    def read(self, name, *, collect=False):
        self.tick()
        _require(name in self.initial, f"Missing file: {name}")
        initial = self.initial[name]
        _require(stat.S_ISREG(initial[2]), f"Not a regular file: {name}")
        flags = os.O_RDONLY | os.O_NONBLOCK
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.root / name, flags)
        hasher = hashlib.sha256()
        chunks = [] if collect else None
        count = 0
        with os.fdopen(descriptor, "rb") as handle:
            _require(_signature(os.fstat(handle.fileno())) == initial,
                     "File changed before read")
            while True:
                self.tick()
                chunk = handle.read(65536)
                if not chunk:
                    break
                count += len(chunk)
                _require(count <= initial[3], "File changed during read")
                hasher.update(chunk)
                if collect:
                    chunks.append(chunk)
            _require(count == initial[3], "File changed during read")
            _require(_signature(os.fstat(handle.fileno())) == initial,
                     "File changed during read")
        _require(_signature((self.root / name).lstat()) == initial,
                 "File pathname changed")
        return hasher.hexdigest(), b"".join(chunks) if collect else None

    def metadata(self, name, expected_digest=None):
        digest, raw = self.read(name, collect=True)
        if expected_digest is not None:
            _require(digest == expected_digest, f"External digest mismatch: {name}")
        return _json(raw)


def _declarations(document, run_id, maximum):
    _schema(document, {"schema_version", "run_id", "artifacts"}, "artifact list")
    _version(document)
    _identity(document, run_id)
    entries = document["artifacts"]
    _require(type(entries) is list and len(entries) <= maximum,
             "Invalid artifact list or artifact count limit")
    result = {}
    for record in entries:
        _schema(record, {"relative_path", "role", "required_on_success",
                         "required_on_failure"}, "artifact declaration")
        name, role = record["relative_path"], record["role"]
        _role_path(name, role)
        _require(name not in result, "Duplicate artifact path")
        for flag in ("required_on_success", "required_on_failure"):
            _require(type(record[flag]) is bool, "Invalid requirement flag")
        if role != "RESULT":
            _require(record["required_on_success"] and record["required_on_failure"],
                     "Mandatory role must be required for both outcomes")
        result[name] = record
    _unique_paths(result)
    _require(all(name in result for name in SINGLETONS.values()),
             "Missing mandatory artifact declaration")
    _require(any(r["role"] == "SOURCE" for r in result.values()),
             "Missing SOURCE declaration")
    return result


def _provenance(document, run_id, attempt_id, outcome, inventory):
    _schema(document, PROVENANCE_FIELDS, "provenance")
    _version(document)
    _identity(document, run_id, attempt_id, outcome)
    _text(document["host_id"], "host ID")
    revision = document["source_revision"]
    _require(type(revision) is str and
             re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision) is not None,
             "Invalid source revision")
    _require(type(document["parameters"]) is dict and
             type(document["input_identity"]) is dict, "Invalid provenance objects")
    _require(_timestamp(document["started_utc"]) <=
             _timestamp(document["ended_utc"]), "Invalid timestamp order")
    sources = document["source_files"]
    _require(type(sources) is list and sources, "Invalid source records")
    source_names, artifact_names = set(), set()
    for record in sources:
        _schema(record, {"source_path", "artifact_path", "sha256"}, "source record")
        source = _path(record["source_path"])
        artifact = _path(record["artifact_path"])
        _digest(record["sha256"])
        _require(source not in source_names and artifact not in artifact_names,
                 "Duplicate source record")
        _require(artifact in inventory and inventory[artifact]["role"] == "SOURCE",
                 "Source artifact binding mismatch")
        _require(record["sha256"] == inventory[artifact]["sha256"],
                 "Source digest binding mismatch")
        source_names.add(source)
        artifact_names.add(artifact)
    _unique_paths(source_names)
    _require(artifact_names == {n for n, r in inventory.items()
                               if r["role"] == "SOURCE"},
             "SOURCE coverage mismatch")
    dependencies = document["dependencies"]
    _require(type(dependencies) is list, "Invalid dependency records")
    seen = set()
    for record in dependencies:
        _schema(record, {"name", "version"}, "dependency record")
        _text(record["name"], "dependency name")
        _text(record["version"], "dependency version")
        _require(record["name"] not in seen, "Duplicate dependency name")
        seen.add(record["name"])


def verify_bundle(
    bundle_root, *, expected_manifest_sha256, expected_predeclaration_sha256,
    expected_artifact_list_sha256, expected_run_id, expected_attempt_id,
    limits, clock=time.monotonic,
):
    """Verify a quiescent synthetic fixture without writing any files.

    Caller supplies independent digests and identities. This does not
    authenticate authorization, execution timing, or scientific validity.
    """
    for digest in (expected_manifest_sha256, expected_predeclaration_sha256,
                   expected_artifact_list_sha256):
        _digest(digest)
    _uuid(expected_run_id)
    _uuid(expected_attempt_id)
    reader = _Reader(bundle_root, limits, clock)
    metadata_names = CONTROLS | {SINGLETONS["PROVENANCE"]}
    for name in metadata_names:
        _require(name in reader.initial and
                 stat.S_ISREG(reader.initial[name][2]), f"Missing metadata: {name}")
    _require(sum(reader.initial[n][3] for n in metadata_names) <=
             limits["max_metadata_bytes"], "Metadata byte limit exceeded")

    manifest = reader.metadata("manifest.json", expected_manifest_sha256)
    _schema(manifest, MANIFEST_FIELDS, "manifest")
    _version(manifest)
    _outcome(manifest["run_outcome"])
    outcome = manifest["run_outcome"]
    _identity(manifest, expected_run_id, expected_attempt_id, outcome)
    _require(manifest["predeclaration_sha256"] == expected_predeclaration_sha256,
             "Predeclaration anchor mismatch")
    _require(manifest["artifact_list_sha256"] == expected_artifact_list_sha256,
             "Artifact-list anchor mismatch")
    declarations = _declarations(
        reader.metadata("artifact_list.json", expected_artifact_list_sha256),
        expected_run_id, limits["max_artifacts"],
    )
    entries = manifest["artifacts"]
    _require(type(entries) is list and len(entries) <= limits["max_artifacts"],
             "Invalid manifest inventory or artifact count limit")
    inventory = {}
    for record in entries:
        reader.tick()
        _schema(record, {"relative_path", "role", "size_bytes", "sha256"},
                "present artifact")
        name, role = record["relative_path"], record["role"]
        _role_path(name, role)
        _require(name not in inventory, "Duplicate artifact path")
        _require(name in declarations and declarations[name]["role"] == role,
                 "Undeclared artifact or role mismatch")
        _require(type(record["size_bytes"]) is int and record["size_bytes"] >= 0,
                 "Invalid artifact size")
        _digest(record["sha256"])
        _require(name in reader.initial and
                 stat.S_ISREG(reader.initial[name][2]), f"Missing file: {name}")
        _require(reader.initial[name][3] == record["size_bytes"],
                 "Artifact size mismatch")
        inventory[name] = record
    requirement = "required_on_success" if outcome == "SUCCEEDED" else "required_on_failure"
    _require(all(not record[requirement] or name in inventory
                 for name, record in declarations.items()), "Missing required evidence")

    expected_files = CONTROLS | set(inventory)
    expected_directories = {""}
    for name in expected_files:
        parts = name.split("/")
        expected_directories.update("/".join(parts[:i]) for i in range(1, len(parts)))
    _require(set(reader.initial) == expected_files | expected_directories,
             "Unexpected bundle inventory")
    for name, record in inventory.items():
        digest, _ = reader.read(name)
        _require(digest == record["sha256"], f"Artifact digest mismatch: {name}")
    _require(inventory[SINGLETONS["PREDECLARATION"]]["sha256"] ==
             expected_predeclaration_sha256, "Predeclaration binding mismatch")
    provenance = reader.metadata(SINGLETONS["PROVENANCE"])
    _provenance(provenance, expected_run_id, expected_attempt_id, outcome, inventory)
    reader.tick()
    _require(reader.scan() == reader.initial, "Bundle changed during verification")
    reader.tick()
    return {
        "classification": "INCREMENT_1_INTEGRITY_VERIFIED",
        "run_id": expected_run_id,
        "attempt_id": expected_attempt_id,
        "run_outcome": outcome,
        "manifest_sha256": expected_manifest_sha256,
        "verified_artifact_count": len(inventory),
        "verified_logical_bytes": sum(
            signature[3] for signature in reader.initial.values()
            if stat.S_ISREG(signature[2])
        ),
    }
