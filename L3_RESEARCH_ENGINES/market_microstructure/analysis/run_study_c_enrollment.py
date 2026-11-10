"""Runtime runner for prospective LRS2 Study-C enrollment.

Enrollment remains impossible unless an explicit activation timestamp is supplied.
The runner consumes only completed successful orchestrator runs and outcome-blind
ledger columns.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from L3_RESEARCH_ENGINES.market_microstructure.analysis.study_c_enrollment import (
    ENROLLMENT_COLUMNS,
    EnrollmentError,
    append_enrollment_rows,
    build_enrollment_rows,
    parse_created_trade_ids,
    parse_utc,
    read_csv_rows,
    require_completed_successful_run,
    verify_detector_authority,
)


DEFAULT_LEDGER = Path(
    "L3_RESEARCH_ENGINES/market_selection/data/simulator/paper_trades.csv"
)
DEFAULT_PROVENANCE = Path(
    "L3_RESEARCH_ENGINES/market_microstructure/data/"
    "study_c_measurement_provenance.csv"
)
DEFAULT_ENROLLMENT = Path(
    "L3_RESEARCH_ENGINES/market_microstructure/data/study_c_enrollment.csv"
)
DEFAULT_LOG_ROOT = Path("logs/daily_cycle")


def read_ledger_outcome_blind(path: Path) -> list[dict]:
    allowed = {
        "trade_id",
        "entry_date",
        "market_id",
        "slug",
        "question",
        "side",
        "scanner_run_id",
    }
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        missing = allowed - set(reader.fieldnames or [])
        if missing:
            raise EnrollmentError(f"ledger missing required columns: {sorted(missing)}")
        return [{k: row[k] for k in allowed} for row in reader]


def load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = read_csv_rows(path)
    if rows and set(rows[0]) != set(ENROLLMENT_COLUMNS):
        raise EnrollmentError("existing enrollment schema mismatch")
    return rows


def run(
    *,
    repo_root: Path,
    activation_boundary: datetime,
    log_root: Path = DEFAULT_LOG_ROOT,
    ledger_path: Path = DEFAULT_LEDGER,
    provenance_path: Path = DEFAULT_PROVENANCE,
    enrollment_path: Path = DEFAULT_ENROLLMENT,
) -> int:
    verify_detector_authority(repo_root)

    ledger_rows = read_ledger_outcome_blind(repo_root / ledger_path)
    provenance_rows = read_csv_rows(repo_root / provenance_path)
    existing = load_existing(repo_root / enrollment_path)

    if len(existing) >= 150:
        print("Study C enrollment permanently complete: 150/150")
        return 0

    run_dirs = sorted(
        p for p in (repo_root / log_root).iterdir()
        if p.is_dir() and (p / "run_summary.json").is_file()
    )

    appended = 0
    for run_dir in run_dirs:
        summary = json.loads((run_dir / "run_summary.json").read_text())

        try:
            windows = require_completed_successful_run(summary)
        except EnrollmentError:
            continue

        # Only completed runs whose paper-trader stage begins after activation
        # can contribute candidates. Admission timestamps are checked again
        # trade-by-trade by the pure enrollment logic.
        if windows["paper_trader"].started <= activation_boundary:
            continue

        stage = next(
            s for s in summary["stages"] if s.get("stage") == "paper_trader"
        )
        log_path = repo_root / stage["log_path"]
        if not log_path.is_file():
            raise EnrollmentError(f"paper-trader log missing: {log_path}")

        created_ids, scanner_run_id = parse_created_trade_ids(log_path.read_text())

        new_rows = build_enrollment_rows(
            run_id=summary["run_id"],
            ledger_rows=ledger_rows,
            created_ids=created_ids,
            scanner_run_id=scanner_run_id,
            provenance_rows=provenance_rows,
            run_obi_window=windows["run_obi"],
            activation_boundary=activation_boundary,
            existing_rows=existing,
            cap=150,
        )

        append_enrollment_rows(repo_root / enrollment_path, new_rows)
        existing.extend(new_rows)
        appended += len(new_rows)

        if len(existing) >= 150:
            break

    print(f"Study C enrollment: appended={appended} total={len(existing)}/150")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enroll prospective LRS2 Study-C trades from completed runs."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--activation-utc",
        required=True,
        help="Pinned audited enrollment activation timestamp, ISO-8601 UTC.",
    )
    args = parser.parse_args()

    activation = parse_utc(args.activation_utc)
    raise SystemExit(
        run(
            repo_root=Path(args.repo_root).resolve(),
            activation_boundary=activation,
        )
    )


if __name__ == "__main__":
    main()
