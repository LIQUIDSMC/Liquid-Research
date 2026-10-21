"""Read-only synthetic sender; framed stdout, bounded stdin, no SSH."""
import hashlib
import os
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from L1_CORE.market_data_platform import evidence_preservation as ep
from L1_CORE.market_data_platform import transport_protocol as tp


def _emit(output, kind, value):
    raw = tp.pack_frame(kind, value)
    offset = 0
    while offset < len(raw):
        written = output.write(raw[offset:])
        if written is None or written <= 0:
            raise OSError("Sender output made no progress")
        offset += written
    output.flush()


def _identity(root, name, initial):
    pathname = root / name
    info = pathname.lstat()
    tp.require(
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and ep._signature(info) == initial,
        "Source identity changed", "TRANSPORT_SOURCE_CHANGED",
    )


def _check_tree(reader, *, initial=False):
    code = "TRANSPORT_SOURCE_INVALID" if initial else "TRANSPORT_SOURCE_CHANGED"
    tp.require(reader.scan() == reader.initial, "Source tree changed", code)
    for name, signature in reader.initial.items():
        if stat.S_ISREG(signature[2]):
            info = (reader.root / name).lstat()
            tp.require(
                info.st_nlink == 1 and ep._signature(info) == signature,
                "Hard-linked or changed source file", code,
            )


def _preflight_budget(root, limits, budget):
    """Enforce transport budgets before generic verifier rejection."""
    pending = [(root, "")]
    entries = 0
    files = 0
    logical = 0
    metadata_bytes = 0
    metadata_names = ep.CONTROLS | {ep.SINGLETONS["PROVENANCE"]}
    maximum_entries = 1 + limits["max_artifact_count"] * 129

    while pending:
        budget.remaining()
        current, relative = pending.pop()
        info = current.lstat()
        entries += 1
        tp.require(
            entries <= maximum_entries,
            "Source tree entry budget exceeded", "TRANSPORT_RESOURCE_LIMIT",
        )
        tp.require(
            not stat.S_ISLNK(info.st_mode),
            "Symlinked source entry", "TRANSPORT_SOURCE_INVALID",
        )
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(current) as children:
                for child in children:
                    budget.remaining()
                    name = f"{relative}/{child.name}" if relative else child.name
                    tp.relative_path(name)
                    tp.require(
                        entries + len(pending) < maximum_entries,
                        "Source tree entry budget exceeded",
                        "TRANSPORT_RESOURCE_LIMIT",
                    )
                    pending.append((Path(child.path), name))
        else:
            tp.require(
                stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                "Nonregular or hard-linked source entry",
                "TRANSPORT_SOURCE_INVALID",
            )
            files += 1
            logical += info.st_size
            if relative in metadata_names:
                metadata_bytes += info.st_size
            tp.require(
                files <= limits["max_artifact_count"]
                and logical <= limits["max_logical_bytes"]
                and metadata_bytes <= limits["max_metadata_bytes"],
                "Source transport budget exceeded",
                "TRANSPORT_RESOURCE_LIMIT",
            )


def _capture(request, budget):
    root = Path(request["source_path"])
    limits = request["limits"]
    tp.require(
        root.is_absolute() and str(root) == str(root.resolve()),
        "Source root must be canonical", "TRANSPORT_SOURCE_INVALID",
    )
    _preflight_budget(root, limits, budget)
    reader = ep._Reader(
        root, tp.verifier_limits(limits, budget.remaining()), budget.clock
    )
    _check_tree(reader, initial=True)

    files = {
        name: signature for name, signature in reader.initial.items()
        if stat.S_ISREG(signature[2])
    }
    tp.require(
        len(files) <= limits["max_artifact_count"]
        and sum(info[3] for info in files.values()) <= limits["max_logical_bytes"],
        "Source transport budget exceeded", "TRANSPORT_RESOURCE_LIMIT",
    )
    for name in files:
        tp.relative_path(name)

    metadata = ep.CONTROLS | {ep.SINGLETONS["PROVENANCE"]}
    tp.require(
        metadata <= files.keys(),
        "Required source metadata missing", "TRANSPORT_SOURCE_INVALID",
    )
    tp.require(
        sum(files[name][3] for name in metadata) <= limits["max_metadata_bytes"],
        "Source metadata budget exceeded", "TRANSPORT_RESOURCE_LIMIT",
    )

    controls = {}
    for name, expected in (
        ("manifest.json", request["expected_manifest_sha256"]),
        ("artifact_list.json", request["expected_artifact_list_sha256"]),
    ):
        budget.remaining()
        digest, raw = reader.read(name, collect=True)
        tp.require(
            digest == expected, "Source control anchor mismatch",
            "TRANSPORT_SOURCE_INVALID",
        )
        tp.decode_json(raw, limits["max_metadata_bytes"])
        controls[name] = raw

    # Apply transport parsing bounds to provenance before the legacy
    # verifier parses it. These bytes are still checked by that verifier.
    _, provenance = reader.read(ep.SINGLETONS["PROVENANCE"], collect=True)
    tp.decode_json(provenance, limits["max_metadata_bytes"])

    ep.verify_bundle(
        root, **tp.anchors(request),
        limits=tp.verifier_limits(limits, budget.remaining()),
        clock=budget.clock,
    )
    _check_tree(reader)
    manifest = tp.decode_json(controls["manifest.json"])
    expected_files = {
        "manifest.json": (
            len(controls["manifest.json"]), request["expected_manifest_sha256"]
        ),
        "artifact_list.json": (
            len(controls["artifact_list.json"]),
            request["expected_artifact_list_sha256"],
        ),
    }
    for record in manifest["artifacts"]:
        budget.remaining()
        expected_files[record["relative_path"]] = (
            record["size_bytes"], record["sha256"]
        )
    tp.require(
        set(expected_files) == set(files),
        "Source inventory mismatch", "TRANSPORT_SOURCE_INVALID",
    )
    return reader, controls, expected_files


def _stream_file(reader, name, expected, output, budget):
    size, expected_digest = expected
    initial = reader.initial[name]
    _identity(reader.root, name, initial)
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(reader.root / name, flags)
    with os.fdopen(descriptor, "rb") as handle:
        opened = os.fstat(handle.fileno())
        tp.require(
            stat.S_ISREG(opened.st_mode)
            and opened.st_nlink == 1
            and ep._signature(opened) == initial,
            "Source changed before streaming", "TRANSPORT_SOURCE_CHANGED",
        )
        _emit(output, tp.FILE_START, {
            "relative_path": name, "size_bytes": size,
            "sha256": expected_digest,
        })
        count = 0
        hasher = hashlib.sha256()
        while True:
            budget.remaining()
            chunk = handle.read(min(tp.MAX_CHUNK, size - count + 1))
            if not chunk:
                break
            count += len(chunk)
            tp.require(
                count <= size, "Source grew while streaming",
                "TRANSPORT_SOURCE_CHANGED",
            )
            hasher.update(chunk)
            _emit(output, tp.FILE_DATA, chunk)
        tp.require(
            count == size and hasher.hexdigest() == expected_digest,
            "Source bytes changed", "TRANSPORT_SOURCE_CHANGED",
        )
        final_info = os.fstat(handle.fileno())
        tp.require(
            final_info.st_nlink == 1
            and ep._signature(final_info) == initial,
            "Source descriptor changed", "TRANSPORT_SOURCE_CHANGED",
        )
    _identity(reader.root, name, initial)
    budget.remaining()
    _emit(output, tp.FILE_END, {
        "relative_path": name, "verified_sha256": expected_digest,
    })


def send(request, output, *, clock=time.monotonic):
    """Read and stream a quiescent synthetic bundle; never modify source."""
    request = tp.validate_request(request)
    budget = tp.Budget(request["limits"]["max_runtime_seconds"], clock)
    _emit(output, tp.HEADER, {
        "protocol_version": tp.VERSION,
        "run_id": request["run_id"], "attempt_id": request["attempt_id"],
    })
    phase = "capture"
    try:
        reader, controls, expected = _capture(request, budget)
        phase = "stream"
        budget.remaining()
        _emit(output, tp.INVENTORY, {
            "manifest_json_bytes": len(controls["manifest.json"]),
            "manifest_sha256": request["expected_manifest_sha256"],
            "artifact_list_json_bytes": len(controls["artifact_list.json"]),
            "artifact_list_sha256": request["expected_artifact_list_sha256"],
            "total_logical_bytes": sum(size for size, _ in expected.values()),
            "total_artifacts": len(expected),
        })
        order = ["manifest.json", "artifact_list.json"]
        order += sorted(set(expected) - ep.CONTROLS)
        for name in order:
            _stream_file(reader, name, expected[name], output, budget)
        _check_tree(reader)
        budget.remaining()
        _emit(output, tp.EOS, {
            "source_scan_verified": True,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
        return 0
    except ep.RuntimeLimitExceeded as exc:
        failure = tp.TransportError(
            "TRANSPORT_RESOURCE_LIMIT", "Source verifier runtime exhausted"
        )
    except tp.TransportError as exc:
        failure = exc
        if failure.code not in tp.REMOTE_CODES:
            failure = tp.TransportError(
                "TRANSPORT_SOURCE_INVALID" if phase == "capture"
                else "TRANSPORT_SOURCE_CHANGED",
                "Source violates transport constraints",
            )
    except ep.VerificationError as exc:
        failure = tp.TransportError(
            "TRANSPORT_SOURCE_INVALID" if phase == "capture"
            else "TRANSPORT_SOURCE_CHANGED",
            "Source verification failed",
        )
    except OSError as exc:
        failure = tp.TransportError(
            "TRANSPORT_IO_ERROR", "Source filesystem or stream failure"
        )

    _emit(output, tp.ERROR, {
        "error_schema_version": 1,
        "code": failure.code,
        "message": str(failure),
    })
    return 1


def main():
    raw = sys.stdin.buffer.read(tp.MAX_REQUEST + 1)
    try:
        request = tp.decode_json(raw, tp.MAX_REQUEST)
        return send(request, sys.stdout.buffer)
    except (tp.TransportError, OSError):
        # Invalid requests may not provide identities for a valid HEADER.
        # The local receiver validates its request before starting a child.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
