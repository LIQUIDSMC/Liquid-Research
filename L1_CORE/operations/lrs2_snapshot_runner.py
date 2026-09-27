#!/usr/bin/env python3
"""Run one LRS2 snapshot bridge attempt and durably record its evidence."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lrs2_snapshot_bridge import bridge_snapshot
from lrs2_snapshot_handoff import DEFAULT_NEAR, DEFAULT_OBI


DEFAULT_OUTGOING = Path("/mnt/lrs001/research_out/lrs2_handoff/outgoing")
DEFAULT_KEY = Path.home() / ".ssh" / "lrs2_handoff_ed25519"
DEFAULT_REMOTE_REPO = Path("/home/kristo/liquid-research-l0l4")
DEFAULT_REMOTE_PUBLICATION = Path("/home/kristo/lrs2_handoff/incoming")
DEFAULT_EVIDENCE = Path(
    "/var/lib/liquid-research/operations/lrs2_bridge/events.jsonl"
)


def git_head(repo: Path) -> str:
    head = (repo / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = repo / ".git" / head[5:]
        value = ref.read_text(encoding="utf-8").strip()
    else:
        value = head
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise RuntimeError("local repository HEAD is not a full lowercase commit SHA")
    return value


def append_evidence(path: Path, evidence: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def run(args) -> dict:
    base = {
        "status": "FAIL",
        "event": "lrs2_snapshot_bridge",
        "research_checkpoint": False,
        "cp15": False,
        "authority_transferred": False,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "runner": "lrs2_snapshot_runner",
    }

    try:
        expected_remote_commit = git_head(args.repo)
        evidence = bridge_snapshot(
            outgoing_root=args.outgoing_root,
            obi_source=args.obi_source,
            near_source=args.near_source,
            key=args.ssh_key,
            remote_user=args.remote_user,
            remote_host=args.remote_host,
            remote_repo=args.remote_repo,
            remote_publication_root=args.remote_publication_root,
            expected_remote_commit=expected_remote_commit,
        )
        evidence["runner"] = "lrs2_snapshot_runner"
        evidence["expected_remote_commit"] = expected_remote_commit
    except Exception as exc:
        evidence = dict(base)
        evidence["error"] = f"{type(exc).__name__}: {exc}"

    try:
        append_evidence(args.evidence_file, evidence)
    except Exception as exc:
        raise RuntimeError(
            "durable evidence append failed after bridge status "
            f"{evidence.get('status', 'UNKNOWN')}: "
            f"{type(exc).__name__}: {exc}; "
            f"bridge_evidence={json.dumps(evidence, sort_keys=True)}"
        ) from exc

    return evidence


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence-file", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--outgoing-root", type=Path, default=DEFAULT_OUTGOING)
    parser.add_argument("--obi-source", type=Path, default=DEFAULT_OBI)
    parser.add_argument("--near-source", type=Path, default=DEFAULT_NEAR)
    parser.add_argument("--ssh-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--remote-user", default="kristo")
    parser.add_argument("--remote-host", default="liquid-pi5")
    parser.add_argument("--remote-repo", type=Path, default=DEFAULT_REMOTE_REPO)
    parser.add_argument(
        "--remote-publication-root",
        type=Path,
        default=DEFAULT_REMOTE_PUBLICATION,
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    evidence = run(args)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
