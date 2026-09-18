"""
Liquid Research — Daily Cycle Orchestrator (Phase 1)
orchestrator.py

Runs the existing, unmodified daily cycle documented in
L3_RESEARCH_ENGINES/market_selection/zDAILY_OPERATIONS.md as a single,
unattended, sequential process. Wraps the existing system — does not
change Prediction Markets acquisition/selection/publication, Market
Selection, Market Microstructure, paper-trading rules, or research
methodology in any way.

Sequence (fixed, no reordering, no parallelism):
    1. market_collector.py
    2. scanner.py
    3. publish_prediction_markets_canonical_output()
    4. paper_trader.py
    5. paper_resolver.py
    6. run_obi.py
    7. run_near_book_depth.py

Each stage runs as a real subprocess with a configurable timeout,
using the same Python interpreter running this script (never a
bare "python3" lookup, which could resolve to a different
interpreter under cron/launchd). If any stage fails or times out,
the pipeline stops immediately — remaining stages are recorded as
skipped, not silently omitted. A lock file prevents overlapping
executions, guaranteed to be released via try/finally regardless
of how the run ends. Every run produces a structured JSON log and
full raw console output per stage, for debugging.

Explicitly excluded from this phase: Git commits/pushes,
notifications, checkpoint writing or interpretation, semantic
per-market success validation (a Market Microstructure collection stage
can exit 0 even if every market failed — this is a known, deliberately
deferred limitation,
see semantic_validation field and the Phase 2 TODO markers below),
and any scientific conclusion of any kind. This script only
executes and records what happened — it never interprets results.

Usage:
    python3 orchestrator.py              (real run)
    python3 orchestrator.py --dry-run    (preflight + plan only, no execution)
"""

import json
import os
import platform
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

PIPELINE_VERSION = "phase_1"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_FILE = os.path.join(REPO_ROOT, "logs", "daily_cycle.lock")
LOG_DIR = os.path.join(REPO_ROOT, "logs", "daily_cycle")
CANONICAL_OUTPUT_PATH = os.path.join(REPO_ROOT, "L2_DOMAINS", "prediction_markets", "data", "canonical", "prediction_markets_latest.csv")

MIN_FREE_DISK_GB = 10

# Timeout constants (seconds). Preliminary estimates based on
# today's observed real durations — not yet empirically tuned.
# Values unchanged from the original Phase 1 implementation.
TIMEOUT_MARKET_COLLECTOR = 180
TIMEOUT_SCANNER = 600
TIMEOUT_PUBLISH_CANONICAL = 60
TIMEOUT_PAPER_TRADER = 120
TIMEOUT_PAPER_RESOLVER = 600
TIMEOUT_RUN_OBI = 600
TIMEOUT_RUN_NEAR_BOOK_DEPTH = 600

# Stage definitions: (name, command_builder, timeout_seconds).
# command_builder receives the resolved python executable path and
# returns the full command list.
STAGES = [
    ("market_collector", lambda py: [py, "L2_DOMAINS/prediction_markets/acquisition/market_collector.py"], TIMEOUT_MARKET_COLLECTOR),
    # PHASE 2 TODO: after this stage succeeds, verify a fresh
    # snapshot file was produced in L2_DOMAINS/prediction_markets/data/markets/,
    # and that it is
    # nonempty and readable. Not implemented in Phase 1.
    ("scanner", lambda py: [py, "L2_DOMAINS/prediction_markets/selection/scanner.py"], TIMEOUT_SCANNER),
    # PHASE 2 TODO: after this stage succeeds, verify a fresh
    # scanner-run file was produced in L2_DOMAINS/prediction_markets/data/scanner/,
    # and that it is
    # nonempty and readable. Not implemented in Phase 1.
    ("publish_canonical_output", lambda py: [py, "-c", (
        "import sys; sys.path.insert(0, '.'); "
        "from L2_DOMAINS.prediction_markets.publication.publish_canonical_output import publish_prediction_markets_canonical_output; "
        "publish_prediction_markets_canonical_output()"
    )], TIMEOUT_PUBLISH_CANONICAL),
    # PHASE 2 TODO: after this stage succeeds, verify the canonical
    # output exists, that publication_id changed (or was validly
    # skipped with a documented reason), and that the file is
    # readable and structurally valid. Partially covered in Phase 1
    # (file-existence check only, immediately after this stage) —
    # publication_id-change and structural validation deferred.
    ("paper_trader", lambda py: [py, "L3_RESEARCH_ENGINES/market_selection/simulator/paper_trader.py"], TIMEOUT_PAPER_TRADER),
    # PHASE 2 TODO: after this stage succeeds, verify the paper-trade
    # file remains readable, and that expected append/skip behavior
    # occurred (e.g. new trades created or all candidates correctly
    # skipped under the one-market_id-one-trade-ever policy). Not
    # implemented in Phase 1.
    ("paper_resolver", lambda py: [py, "L3_RESEARCH_ENGINES/market_selection/simulator/paper_resolver.py"], TIMEOUT_PAPER_RESOLVER),
    # PHASE 2 TODO: after this stage succeeds, verify the paper-trade
    # file remains readable, and that status counts remain internally
    # consistent (open + closed == total, wins + losses == closed).
    # Not implemented in Phase 1.
    ("run_obi", lambda py: [py, "L3_RESEARCH_ENGINES/market_microstructure/collection/run_obi.py"], TIMEOUT_RUN_OBI),
    # PHASE 2 TODO: after this stage succeeds, verify expected rows
    # were appended to
    # L3_RESEARCH_ENGINES/market_microstructure/data/obi_log.csv, and detect
    # systemic per-market failures (e.g. most/all markets returning
    # FAILED status) — this stage can currently exit 0 even if every
    # market failed, per semantic_validation="not_implemented_phase_1".
    # Not implemented in Phase 1.
    ("run_near_book_depth", lambda py: [py, "L3_RESEARCH_ENGINES/market_microstructure/collection/run_near_book_depth.py"], TIMEOUT_RUN_NEAR_BOOK_DEPTH),
    # PHASE 2 TODO: same systemic-failure detection as run_obi above,
    # applied to
    # L3_RESEARCH_ENGINES/market_microstructure/data/near_book_depth_log.csv.
    # Not implemented in Phase 1.
]


def now_iso() -> str:
    """UTC timestamp in ISO 8601 format, matching this project's existing convention."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_git_commit() -> str:
    """
    Best-effort current commit hash. A failure here (e.g. git not
    on PATH, not a git repo for some reason) must never stop the
    pipeline — returns a clear placeholder instead.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return "unavailable"
    except Exception:
        return "unavailable"


def get_free_disk_gb(path: str) -> float:
    """Free disk space, in GB, for the filesystem containing path."""
    stat = os.statvfs(path)
    free_bytes = stat.f_bavail * stat.f_frsize
    return free_bytes / (1024 ** 3)


def preflight_checks() -> list:
    """
    Validate everything the pipeline needs before touching anything.
    Returns a list of (check_name, ok, detail) tuples. Does not
    raise — the caller decides whether any failed check should stop
    the run. CANONICAL_OUTPUT_PATH is deliberately not checked here,
    since publish_canonical_output creates/updates it during the
    run — it's checked separately, after that stage succeeds.
    """
    checks = []

    checks.append(("repo_root_exists", os.path.isdir(REPO_ROOT), REPO_ROOT))

    expected_venv_marker = os.path.join(REPO_ROOT, "venv")
    interpreter_in_venv = sys.executable.startswith(expected_venv_marker)
    checks.append((
        "venv_interpreter_active",
        interpreter_in_venv,
        f"sys.executable={sys.executable}, expected prefix={expected_venv_marker}",
    ))

    for name, command_builder, _ in STAGES:
        if name == "publish_canonical_output":
            continue  # inline -c command, not a script file
        script_path = os.path.join(REPO_ROOT, command_builder(sys.executable)[1])
        checks.append((f"stage_script_exists:{name}", os.path.isfile(script_path), script_path))

    for directory in (os.path.dirname(LOCK_FILE), LOG_DIR):
        os.makedirs(directory, exist_ok=True)
        checks.append((f"directory_ready:{directory}", os.path.isdir(directory), directory))

    free_gb = get_free_disk_gb(REPO_ROOT)
    checks.append((
        "sufficient_disk_space",
        free_gb >= MIN_FREE_DISK_GB,
        f"{free_gb:.1f}GB free, minimum required {MIN_FREE_DISK_GB}GB",
    ))

    return checks


def acquire_lock() -> None:
    """
    Prevent overlapping pipeline executions. If a lock file exists,
    check whether the PID it contains is still alive. A live PID
    means a run is genuinely in progress — refuse to start a second
    one. A dead PID, or an unreadable/malformed lock file, is
    treated as stale — safely removed, and the run proceeds.

    Raises:
        SystemExit: if a genuinely active run is already in progress.
    """
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)

    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid_str = f.read().strip()
            old_pid = int(old_pid_str)
            os.kill(old_pid, 0)  # signal 0: check if process exists, doesn't actually kill it
            print(f"ERROR: Pipeline already running (PID {old_pid}). Refusing to start a second run.")
            sys.exit(1)
        except ProcessLookupError:
            print(f"Stale lock file found (PID {old_pid_str} not running). Removing and proceeding.")
            os.remove(LOCK_FILE)
        except PermissionError:
            # Process exists but we can't signal it (different user,
            # etc.) — treat this as "probably still running" and refuse
            # to start, rather than assuming it's safe to proceed.
            print(f"ERROR: Cannot confirm status of PID {old_pid_str} (permission denied). "
                  f"Treating as active. Refusing to start a second run.")
            sys.exit(1)
        except (ValueError, FileNotFoundError, OSError):
            print("Lock file unreadable or malformed. Removing and proceeding.")
            try:
                os.remove(LOCK_FILE)
            except FileNotFoundError:
                pass

    # Write atomically: write to a temp file, then rename — rename is
    # atomic on the same filesystem, avoiding a torn/partial lock file.
    tmp_path = LOCK_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(str(os.getpid()))
    os.replace(tmp_path, LOCK_FILE)


def release_lock() -> None:
    """Remove the lock file. Called on both success and failure paths."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def run_stage(name: str, command: list, timeout_seconds: int, run_log_dir: str, dry_run: bool) -> dict:
    """
    Run one stage as a real subprocess, capturing full console
    output to a per-stage log file and returning structured
    metadata about what happened. Never raises — a timeout or
    non-zero exit code is captured as a failed status, not an
    exception, so the orchestrator's main loop can decide what to
    do next.

    In dry_run mode, does not execute anything — only prints the
    planned command and returns a "dry_run" status.
    """
    log_path = os.path.join(run_log_dir, f"{name}.log")

    if dry_run:
        print(f"\n[DRY RUN] Would run stage: {name}")
        print(f"[DRY RUN]   command: {' '.join(command)}")
        print(f"[DRY RUN]   timeout: {timeout_seconds}s")
        return {
            "stage": name,
            "status": "dry_run",
            "started": None,
            "finished": None,
            "duration_seconds": 0,
            "exit_code": None,
            "log_path": None,
        }

    started = now_iso()
    start_time = time.monotonic()

    print(f"\n--- Starting stage: {name} ---")

    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
            )
        exit_code = result.returncode
        status = "success" if exit_code == 0 else "failed"
    except subprocess.TimeoutExpired:
        exit_code = None
        status = "timeout"
        print(f"Stage '{name}' exceeded its {timeout_seconds}s timeout and was terminated.")

    duration_seconds = round(time.monotonic() - start_time, 2)
    finished = now_iso()

    print(f"--- Stage '{name}' finished: {status} (exit_code={exit_code}, duration={duration_seconds}s) ---")

    return {
        "stage": name,
        "status": status,
        "started": started,
        "finished": finished,
        "duration_seconds": duration_seconds,
        "exit_code": exit_code,
        "log_path": os.path.relpath(log_path, REPO_ROOT),
    }


def skipped_stage_record(name: str) -> dict:
    """Structured record for a stage that never ran due to an upstream failure."""
    return {
        "stage": name,
        "status": "skipped",
        "reason": "upstream stage failed",
        "started": None,
        "finished": None,
        "duration_seconds": 0,
        "exit_code": None,
        "log_path": None,
    }


def generate_health_summary(stage_results: list, pipeline_status: str, total_duration_seconds: float) -> str:
    """
    Produce a concise, human-readable summary of what happened —
    counts and statuses only, no scientific interpretation of any
    kind, per this project's explicit boundary between operational
    reporting and research interpretation.
    """
    lines = []
    for result in stage_results:
        label = result["stage"].replace("_", " ").title()
        status = result["status"]
        duration = result.get("duration_seconds", 0)
        exit_code = result.get("exit_code")

        if status == "success":
            lines.append(f"{label}: SUCCESS | {duration}s | exit_code={exit_code}")
        elif status == "timeout":
            lines.append(f"{label}: TIMEOUT | {duration}s | exit_code={exit_code}")
        elif status == "skipped":
            lines.append(f"{label}: SKIPPED | reason={result.get('reason', 'unknown')}")
        elif status == "dry_run":
            lines.append(f"{label}: DRY RUN (not executed)")
        else:
            lines.append(f"{label}: FAILED | {duration}s | exit_code={exit_code}")

    lines.append(f"\nPipeline {pipeline_status.upper()}")
    lines.append(f"Total duration: {total_duration_seconds}s")
    return "\n".join(lines)


def write_run_outputs(run_log_dir: str, run_record: dict) -> None:
    """Write both the structured JSON log and the human-readable health summary."""
    json_log_path = os.path.join(run_log_dir, "run_summary.json")
    with open(json_log_path, "w") as f:
        json.dump(run_record, f, indent=2)

    summary_text = generate_health_summary(
        run_record["stages"], run_record["status"], run_record["duration_seconds"]
    )
    summary_path = os.path.join(run_log_dir, "health_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary_text)

    print("\n" + "=" * 50)
    print(summary_text)
    print("=" * 50)
    print(f"\nFull run logs: {run_log_dir}")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    pipeline_start_time = time.monotonic()

    checks = preflight_checks()
    failed_checks = [c for c in checks if not c[1]]

    print("=== Preflight Checks ===")
    for name, ok, detail in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")

    if failed_checks:
        print(f"\nERROR: {len(failed_checks)} preflight check(s) failed. Pipeline will not start.")
        sys.exit(1)

    acquire_lock()

    try:
        run_id = now_iso().replace(":", "").replace("-", "")
        run_log_dir = os.path.join(LOG_DIR, run_id)
        os.makedirs(run_log_dir, exist_ok=True)

        pipeline_started = now_iso()
        stage_results = []
        pipeline_status = "success"
        exception_info = None

        metadata = {
            "run_id": run_id,
            "pipeline_version": PIPELINE_VERSION,
            "repo_path": REPO_ROOT,
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hostname": socket.gethostname(),
            "git_commit": get_git_commit(),
            "dry_run": dry_run,
            "semantic_validation": "not_implemented_phase_1",
        }

        print("\n=== Run Metadata ===")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

        try:
            remaining_stage_names = [s[0] for s in STAGES]

            for name, command_builder, timeout_seconds in STAGES:
                remaining_stage_names.remove(name)
                command = command_builder(sys.executable)

                result = run_stage(name, command, timeout_seconds, run_log_dir, dry_run)
                stage_results.append(result)

                if not dry_run and result["status"] != "success":
                    pipeline_status = "failed"
                    print(f"\nPipeline stopped: stage '{name}' did not succeed. Remaining stages skipped.")
                    for skipped_name in remaining_stage_names:
                        stage_results.append(skipped_stage_record(skipped_name))
                    break

                # Verify canonical output exists immediately after the
                # publisher stage succeeds, before Market Selection and
                # Market Microstructure continue — not checked at preflight,
                # since this stage
                # is what creates/updates the file.
                if not dry_run and name == "publish_canonical_output" and result["status"] == "success":
                    if not os.path.isfile(CANONICAL_OUTPUT_PATH):
                        pipeline_status = "failed"
                        print(f"\nPipeline stopped: {CANONICAL_OUTPUT_PATH} not found after publisher succeeded.")
                        for skipped_name in remaining_stage_names:
                            stage_results.append(skipped_stage_record(skipped_name))
                        break

            if dry_run:
                pipeline_status = "dry_run"

        except Exception as e:
            pipeline_status = "failed"
            exception_info = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
            }
            print("\n=== UNEXPECTED ORCHESTRATOR EXCEPTION ===")
            traceback.print_exc()

        pipeline_finished = now_iso()
        total_duration_seconds = round(time.monotonic() - pipeline_start_time, 2)

        run_record = {
            **metadata,
            "started": pipeline_started,
            "finished": pipeline_finished,
            "status": pipeline_status,
            "duration_seconds": total_duration_seconds,
            "stages": stage_results,
        }
        if exception_info:
            run_record["exception"] = exception_info

        write_run_outputs(run_log_dir, run_record)

        if pipeline_status not in ("success", "dry_run"):
            sys.exit(1)

    finally:
        release_lock()


if __name__ == "__main__":
    main()
