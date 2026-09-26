#!/usr/bin/env python3
"""Create, transfer, verify, and publish one bounded LRS2 infrastructure snapshot."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone

from lrs2_snapshot_handoff import create_snapshot, DEFAULT_OBI, DEFAULT_NEAR


FILES = ("MANIFEST.json", "obi_log.csv", "near_book_depth_log.csv")
SNAPSHOT_PATTERN = re.compile(r"\d{8}T\d{6}\.\d{6}Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run_checked(command):
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def load_source_expectations(snapshot: Path, outgoing_root: Path) -> dict[str, str]:
    snapshot = snapshot.resolve(strict=True)
    outgoing_root = outgoing_root.resolve(strict=True)

    require(snapshot.parent == outgoing_root, "snapshot must be a direct child of outgoing root")
    require(SNAPSHOT_PATTERN.fullmatch(snapshot.name) is not None, "invalid snapshot ID")
    require(
        {p.name for p in snapshot.iterdir()} == set(FILES),
        "source snapshot must contain exactly the three expected files",
    )

    manifest_path = snapshot / "MANIFEST.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    require(manifest.get("schema_version") == 1, "unsupported manifest schema")
    require(manifest.get("purpose") == "LRS2 bounded analytical snapshot", "invalid purpose")
    require(manifest.get("research_checkpoint") is False, "research checkpoint must be false")
    require(manifest.get("cp15") is False, "CP15 must be false")

    source_host = manifest.get("source_host")
    source_commit = manifest.get("source_commit")
    snapshot_utc = manifest.get("snapshot_utc")

    require(type(source_host) is str and source_host == socket.gethostname(), "source host mismatch")
    require(
        type(source_commit) is str and re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None,
        "invalid source commit",
    )
    require(type(snapshot_utc) is str, "invalid snapshot time")

    timestamp = datetime.fromisoformat(snapshot_utc)
    require(
        timestamp.tzinfo is not None and timestamp.utcoffset().total_seconds() == 0,
        "snapshot time must be UTC",
    )
    require(
        timestamp.strftime("%Y%m%dT%H%M%S.%fZ") == snapshot.name,
        "snapshot identity mismatch",
    )

    return {
        "snapshot_id": snapshot.name,
        "source_host": source_host,
        "source_commit": source_commit,
    }


def ssh_base(key: Path, remote_user: str, remote_host: str) -> list[str]:
    return [
        "ssh",
        "-i",
        str(key),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=5",
        f"{remote_user}@{remote_host}",
    ]


def scp_base(key: Path) -> list[str]:
    return [
        "scp",
        "-i",
        str(key),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=5",
    ]


def bridge_snapshot(
    outgoing_root: Path,
    obi_source: Path,
    near_source: Path,
    key: Path,
    remote_user: str,
    remote_host: str,
    remote_repo: Path,
    remote_publication_root: Path,
) -> dict:
    key = key.expanduser().resolve(strict=True)
    require(key.is_file(), "SSH key must be a regular file")

    snapshot = create_snapshot(
        output_root=outgoing_root.resolve(),
        obi_source=obi_source.resolve(),
        near_source=near_source.resolve(),
    )
    expected = load_source_expectations(snapshot, outgoing_root)
    snapshot_id = expected["snapshot_id"]

    staging_name = f".{snapshot_id}.transfer"
    remote_staging = remote_publication_root / staging_name
    remote_final = remote_publication_root / snapshot_id

    ssh = ssh_base(key, remote_user, remote_host)

    # Refuse resume, overwrite, or implicit success. Both paths must be absent.
    preflight = run_checked(
        ssh
        + [
            "python3",
            "-c",
            (
                "import os,sys;"
                "s=sys.argv[1];f=sys.argv[2];"
                "sys.exit(0 if not os.path.lexists(s) and not os.path.lexists(f) else 23)"
            ),
            str(remote_staging),
            str(remote_final),
        ]
    )
    require(preflight.returncode == 0, "remote destination preflight failed")

    run_checked(ssh + ["mkdir", "--", str(remote_staging)])

    remote_target = f"{remote_user}@{remote_host}:{remote_staging}/"
    run_checked(
        scp_base(key)
        + [
            str(snapshot / "MANIFEST.json"),
            str(snapshot / "obi_log.csv"),
            str(snapshot / "near_book_depth_log.csv"),
            remote_target,
        ]
    )

    receiver = remote_repo / "L1_CORE/operations/lrs2_snapshot_receiver.py"
    python = remote_repo / "venv/bin/python3"

    result = run_checked(
        ssh
        + [
            str(python),
            str(receiver),
            "--staging",
            str(remote_staging),
            "--publication-root",
            str(remote_publication_root),
            "--expected-snapshot-id",
            snapshot_id,
            "--expected-source-host",
            expected["source_host"],
            "--expected-source-commit",
            expected["source_commit"],
        ]
    )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    require(len(lines) == 1, "receiver must emit exactly one evidence line")
    evidence = json.loads(lines[0])
    require(evidence.get("status") == "PASS", "receiver did not report PASS")
    require(evidence.get("published") is True, "receiver did not publish")
    require(evidence.get("snapshot_id") == snapshot_id, "receiver snapshot mismatch")
    require(evidence.get("source_host") == expected["source_host"], "receiver host mismatch")
    require(evidence.get("source_commit") == expected["source_commit"], "receiver commit mismatch")
    require(evidence.get("research_checkpoint") is False, "receiver checkpoint flag mismatch")
    require(evidence.get("cp15") is False, "receiver CP15 flag mismatch")
    require(evidence.get("authority_transferred") is False, "receiver authority flag mismatch")

    return {
        "status": "PASS",
        "event": "lrs2_snapshot_bridge",
        "snapshot_id": snapshot_id,
        "source_snapshot": str(snapshot),
        "published_destination": evidence.get("destination"),
        "source_host": expected["source_host"],
        "source_commit": expected["source_commit"],
        "manifest_sha256": evidence.get("manifest_sha256"),
        "research_checkpoint": False,
        "cp15": False,
        "authority_transferred": False,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outgoing-root", type=Path, required=True)
    parser.add_argument("--obi-source", type=Path, default=DEFAULT_OBI)
    parser.add_argument("--near-source", type=Path, default=DEFAULT_NEAR)
    parser.add_argument("--ssh-key", type=Path, required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-repo", type=Path, required=True)
    parser.add_argument("--remote-publication-root", type=Path, required=True)
    args = parser.parse_args(argv)

    evidence = {
        "status": "FAIL",
        "event": "lrs2_snapshot_bridge",
        "research_checkpoint": False,
        "cp15": False,
        "authority_transferred": False,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }

    try:
        evidence = bridge_snapshot(
            outgoing_root=args.outgoing_root,
            obi_source=args.obi_source,
            near_source=args.near_source,
            key=args.ssh_key,
            remote_user=args.remote_user,
            remote_host=args.remote_host,
            remote_repo=args.remote_repo,
            remote_publication_root=args.remote_publication_root,
        )
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
