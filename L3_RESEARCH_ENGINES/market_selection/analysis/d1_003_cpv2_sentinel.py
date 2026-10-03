#!/usr/bin/env python3

"""
LRS-1 D1-003 CP-V2 readiness sentinel.

Purpose
-------
Outcome-blind operational watchdog for the prospectively frozen CP-V2
checkpoint.

This program may determine only:

    - integrity status
    - eligible closed-trade count
    - progress toward 100
    - remaining count
    - READY / NOT_READY

It does NOT:

    - access economic outcome or predictor fields
    - construct or persist the CP-V2 100-ID manifest
    - select the first 100 eligible trades
    - perform CP-V2 validation
    - invoke validation automatically

Normal scheduled operation requires an already-initialized state file.
The one authorized bootstrap must be invoked explicitly with --initialize.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

import pandas as pd


# ---------------------------------------------------------------------------
# FROZEN AUTHORITY
# ---------------------------------------------------------------------------

THRESHOLD = 100
STATE_SCHEMA_VERSION = 1

EXPECTED_D_N = 396
EXPECTED_D_SHA256 = (
    "ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e"
)

EXPECTED_V1_N = 80
EXPECTED_V1_SHA256 = (
    "a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141"
)

EXPECTED_GOVERNANCE_SHA256 = (
    "1bdb01c294a24d36a1d5cfe5b6809e528c26e6aea6eab914a09fe04e57f11f3d"
)

EXPECTED_METHODOLOGY_SHA256 = (
    "6b71862a5918a3e1c8af8f2b3d7b8525f056cec450b4b863bf9a456eb86fea98"
)

EXPECTED_V1_TRADE_IDS = frozenset(
    {
        "105", "202", "212", "229", "233", "243", "288", "298",
        "309", "313", "324", "339", "344", "353", "360", "414",
        "456", "471", "472", "484", "487", "490", "491", "492",
        "500", "505", "525", "540", "541", "544", "556", "557",
        "564", "565", "570", "573", "584", "586", "592", "594",
        "595", "596", "598", "602", "606", "614", "615", "616",
        "617", "619", "621", "622", "625", "626", "627", "632",
        "633", "634", "638", "639", "641", "642", "643", "644",
        "647", "648", "649", "650", "651", "652", "656", "659",
        "660", "663", "664", "666", "667", "671", "69", "85",
    }
)

ALLOWED_LEDGER_COLUMNS = [
    "trade_id",
    "status",
    "resolution_date",
]


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]

LEDGER = (
    HERE.parent
    / "data"
    / "simulator"
    / "paper_trades.csv"
)

D_AUTHORITY = HERE / "D1_003_frozen_D_trade_ids.txt"

GOVERNANCE = HERE / "D1_003_CPV2_governance.md"

METHODOLOGY = HERE / "D1_003_CPV2_validation_specification.md"

LOG_DIR = REPO_ROOT / "logs"

STATE = LOG_DIR / "lrs1_cpv2_sentinel_state.json"

LOCK = LOG_DIR / "lrs1_cpv2_sentinel.lock"


# ---------------------------------------------------------------------------
# EXIT CODES
# ---------------------------------------------------------------------------

EXIT_NOT_READY = 0
EXIT_READY = 10
EXIT_INTEGRITY_FAILURE = 20
EXIT_LOCKED = 21


# ---------------------------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------------------------

class SentinelError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SentinelError(message)


def sha256_file(path: Path) -> str:
    require(path.exists(), f"Missing authority file: {path}")

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def trade_id_hash(values) -> str:
    payload = "\n".join(sorted(str(x) for x in values)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# FROZEN AUTHORITY VERIFICATION
# ---------------------------------------------------------------------------

def load_d_authority() -> frozenset[str]:
    require(
        sha256_file(D_AUTHORITY) == EXPECTED_D_SHA256,
        "Frozen D authority file SHA mismatch.",
    )

    ids = D_AUTHORITY.read_text(encoding="utf-8").splitlines()

    require(
        len(ids) == EXPECTED_D_N,
        "Frozen D authority n mismatch.",
    )

    require(
        len(set(ids)) == EXPECTED_D_N,
        "Frozen D authority contains duplicate trade_id.",
    )

    require(
        ids == sorted(ids),
        "Frozen D authority is not in canonical lexicographic order.",
    )

    require(
        trade_id_hash(ids) == EXPECTED_D_SHA256,
        "Frozen D authority trade-id SHA mismatch.",
    )

    return frozenset(ids)


def verify_v1_authority() -> frozenset[str]:
    ids = EXPECTED_V1_TRADE_IDS

    require(
        len(ids) == EXPECTED_V1_N,
        "Frozen V1 authority n mismatch.",
    )

    require(
        trade_id_hash(ids) == EXPECTED_V1_SHA256,
        "Frozen V1 authority trade-id SHA mismatch.",
    )

    return ids


def verify_research_authority() -> tuple[frozenset[str], frozenset[str]]:
    require(
        sha256_file(GOVERNANCE) == EXPECTED_GOVERNANCE_SHA256,
        "CP-V2 governance authority SHA mismatch.",
    )

    require(
        sha256_file(METHODOLOGY) == EXPECTED_METHODOLOGY_SHA256,
        "CP-V2 methodology authority SHA mismatch.",
    )

    d_ids = load_d_authority()
    v1_ids = verify_v1_authority()

    require(
        not d_ids.intersection(v1_ids),
        "Frozen D/V1 identity overlap is non-zero.",
    )

    return d_ids, v1_ids


# ---------------------------------------------------------------------------
# OUTCOME-BLIND LEDGER READ / ELIGIBILITY
# ---------------------------------------------------------------------------

def load_identity_ledger() -> pd.DataFrame:
    require(LEDGER.exists(), f"Missing paper ledger: {LEDGER}")

    try:
        ledger = pd.read_csv(
            LEDGER,
            usecols=ALLOWED_LEDGER_COLUMNS,
        )
    except Exception as exc:
        raise SentinelError(
            f"Unable to read required identity/closure columns: {exc}"
        ) from exc

    require(
        list(ledger.columns) == ALLOWED_LEDGER_COLUMNS,
        "Ledger column restriction mismatch.",
    )

    require(
        ledger["trade_id"].notna().all(),
        "Ledger contains missing trade_id.",
    )

    numeric_ids = pd.to_numeric(
        ledger["trade_id"],
        errors="coerce",
    )

    require(
        numeric_ids.notna().all(),
        "Ledger contains non-numeric trade_id.",
    )

    require(
        ((numeric_ids % 1) == 0).all(),
        "Ledger contains non-integer trade_id.",
    )

    ledger["trade_id"] = (
        numeric_ids.astype("int64").astype(str)
    )

    require(
        not ledger["trade_id"].duplicated().any(),
        "Ledger contains duplicate trade_id.",
    )

    ledger["status_normalized"] = (
        ledger["status"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return ledger


def eligible_count(
    ledger: pd.DataFrame,
    d_ids: frozenset[str],
    v1_ids: frozenset[str],
) -> int:
    ledger_ids = set(ledger["trade_id"].tolist())

    require(
        d_ids.issubset(ledger_ids),
        "Current ledger is missing one or more frozen D identities.",
    )

    require(
        v1_ids.issubset(ledger_ids),
        "Current ledger is missing one or more frozen V1 identities.",
    )

    frozen_ids = d_ids.union(v1_ids)

    frozen_rows = ledger.loc[
        ledger["trade_id"].isin(frozen_ids)
    ].copy()

    require(
        frozen_rows["status_normalized"].eq("closed").all(),
        "One or more frozen D/V1 identities are no longer closed.",
    )

    closed = ledger.loc[
        ledger["status_normalized"].eq("closed")
    ].copy()

    eligible = closed.loc[
        ~closed["trade_id"].isin(frozen_ids)
    ].copy()

    if not eligible.empty:
        require(
            eligible["resolution_date"].notna().all(),
            "Eligible closed trade contains missing resolution_date.",
        )

        parsed = pd.to_datetime(
            eligible["resolution_date"],
            errors="coerce",
            utc=True,
        )

        require(
            parsed.notna().all(),
            "Eligible closed trade contains unparseable resolution_date.",
        )

    return int(len(eligible))


# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------

def expected_authority_state() -> dict:
    return {
        "governance_sha256": EXPECTED_GOVERNANCE_SHA256,
        "methodology_sha256": EXPECTED_METHODOLOGY_SHA256,
        "d_trade_id_sha256": EXPECTED_D_SHA256,
        "v1_trade_id_sha256": EXPECTED_V1_SHA256,
    }


def validate_state_shape(state: object) -> dict:
    require(
        isinstance(state, dict),
        "Sentinel state root is not an object.",
    )

    required = {
        "schema_version",
        "threshold",
        "eligible_count",
        "ready",
        "updated_at_utc",
        "authority",
    }

    require(
        set(state.keys()) == required,
        "Sentinel state schema keys mismatch.",
    )

    require(
        state["schema_version"] == STATE_SCHEMA_VERSION,
        "Sentinel state schema version mismatch.",
    )

    require(
        state["threshold"] == THRESHOLD,
        "Sentinel state threshold mismatch.",
    )

    require(
        isinstance(state["eligible_count"], int)
        and not isinstance(state["eligible_count"], bool)
        and state["eligible_count"] >= 0,
        "Sentinel state eligible_count is invalid.",
    )

    require(
        isinstance(state["ready"], bool),
        "Sentinel state ready flag is invalid.",
    )

    require(
        isinstance(state["updated_at_utc"], str)
        and bool(state["updated_at_utc"]),
        "Sentinel state timestamp is invalid.",
    )

    require(
        state["authority"] == expected_authority_state(),
        "Sentinel state research authority mismatch.",
    )

    expected_ready = state["eligible_count"] >= THRESHOLD

    require(
        state["ready"] == expected_ready,
        "Sentinel state READY/count relationship is invalid.",
    )

    return state


def read_state() -> dict:
    require(
        STATE.exists(),
        "Sentinel state missing. Normal mode will not silently reinitialize.",
    )

    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SentinelError(
            f"Unable to parse sentinel state: {exc}"
        ) from exc

    return validate_state_shape(state)


def atomic_write_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    payload = (
        json.dumps(
            state,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    fd = None
    tmp_path = None

    try:
        fd, raw_tmp = tempfile.mkstemp(
            prefix=".lrs1_cpv2_sentinel_state.",
            suffix=".tmp",
            dir=str(LOG_DIR),
        )

        tmp_path = Path(raw_tmp)

        with os.fdopen(fd, "wb") as f:
            fd = None
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, STATE)
        tmp_path = None

        dir_fd = os.open(LOG_DIR, os.O_RDONLY)

        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    finally:
        if fd is not None:
            os.close(fd)

        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass


def build_state(count: int) -> dict:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "threshold": THRESHOLD,
        "eligible_count": count,
        "ready": count >= THRESHOLD,
        "updated_at_utc": utc_now(),
        "authority": expected_authority_state(),
    }


# ---------------------------------------------------------------------------
# LOCK
# ---------------------------------------------------------------------------

def acquire_lock():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    lock_file = LOCK.open("a+")

    try:
        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        lock_file.close()
        raise

    return lock_file


# ---------------------------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------------------------

def run(initialize: bool) -> int:
    d_ids, v1_ids = verify_research_authority()

    ledger = load_identity_ledger()

    count = eligible_count(
        ledger,
        d_ids,
        v1_ids,
    )

    if initialize:
        require(
            not STATE.exists(),
            "Initialization refused: sentinel state already exists.",
        )

        state = build_state(count)
        atomic_write_state(state)

    else:
        previous = read_state()

        previous_count = previous["eligible_count"]

        require(
            count >= previous_count,
            (
                "Eligible count decreased: "
                f"previous={previous_count}, current={count}."
            ),
        )

        # READY is mechanically equivalent to count >= frozen threshold.
        # If READY was previously reached, monotonic count guarantees it
        # remains latched. A decrease fails before this point.
        state = build_state(count)

        require(
            not previous["ready"] or state["ready"],
            "READY latch attempted to revert.",
        )

        atomic_write_state(state)

    ready = state["ready"]
    remaining = max(0, THRESHOLD - count)

    print("INTEGRITY=PASS")
    print(f"ELIGIBLE_COUNT={count}")
    print(f"PROGRESS={count}/{THRESHOLD}")
    print(f"REMAINING={remaining}")
    print(f"READY={'YES' if ready else 'NO'}")

    return EXIT_READY if ready else EXIT_NOT_READY


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LRS-1 D1-003 CP-V2 outcome-blind readiness sentinel."
    )

    parser.add_argument(
        "--initialize",
        action="store_true",
        help=(
            "Explicitly create the first monotonic baseline. "
            "Refuses if state already exists."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        lock_file = acquire_lock()
    except BlockingIOError:
        print(
            "INTEGRITY=FAIL",
            file=sys.stderr,
        )
        print(
            "ERROR=Sentinel lock is already held; state untouched.",
            file=sys.stderr,
        )
        return EXIT_LOCKED
    except Exception as exc:
        print("INTEGRITY=FAIL", file=sys.stderr)
        print(f"ERROR=Unable to acquire sentinel lock: {exc}", file=sys.stderr)
        return EXIT_INTEGRITY_FAILURE

    try:
        return run(args.initialize)

    except SentinelError as exc:
        print("INTEGRITY=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return EXIT_INTEGRITY_FAILURE

    except Exception as exc:
        print("INTEGRITY=FAIL", file=sys.stderr)
        print(
            f"ERROR=Unexpected sentinel failure: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return EXIT_INTEGRITY_FAILURE

    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()


if __name__ == "__main__":
    sys.exit(main())
