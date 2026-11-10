"""Pure enrollment logic for LRS2 Study C.

This module intentionally does not import the LRS1 latent-event-family detector.
That module performs historical-ledger work at import time.  Study C reproduces
only the frozen question-only classify_v11 semantics and provenance-gates the
source detector by SHA-256.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


DETECTOR_RELATIVE_PATH = Path(
    "L3_RESEARCH_ENGINES/market_selection/analysis/"
    "latent_event_family_detector_v1_1.py"
)
EXPECTED_DETECTOR_SHA256 = (
    "008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e"
)

PACIFIC = ZoneInfo("America/Los_Angeles")

ENROLLMENT_COLUMNS = [
    "enrollment_sequence",
    "run_id",
    "trade_id",
    "market_id",
    "slug",
    "side",
    "admission_timestamp",
    "scanner_run_id",
    "publication_id",
    "lrs2_timestamp",
    "outcome_tested",
    "token_id",
    "raw_obi",
    "side_aligned_obi",
    "family_rule",
    "family_key",
]

LEDGER_ALLOWLIST = [
    "trade_id",
    "entry_date",
    "market_id",
    "slug",
    "question",
    "side",
    "scanner_run_id",
]

PROVENANCE_REQUIRED = [
    "timestamp",
    "publication_id",
    "slug",
    "outcomes",
    "token_ids",
    "outcome_tested",
    "token_id",
    "raw_obi",
    "status",
]

MONTHS = (
    r"january|february|march|april|may|june|july|"
    r"august|september|october|november|december"
)
DEADLINE_TAIL = re.compile(
    rf"\s+(?:by|before|through)\s+"
    rf"(?:the\s+)?(?:end\s+of\s+)?"
    rf"(?:{MONTHS})"
    rf"(?:\s+\d{{1,2}})?"
    rf"(?:,\s*\d{{4}})?\??$",
    re.I,
)


class EnrollmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageWindow:
    started: datetime
    finished: datetime


def clean(s):
    s = str(s).lower().strip()
    s = s.replace("’", "'").replace("–", "-")
    s = re.sub(r"\s+", " ", s)
    return s


def match_range_threshold(q0):
    m = re.fullmatch(
        r"will elon musk post "
        r"\d+\s*-\s*\d+ "
        r"tweets from (.+?)\?",
        q0,
    )
    if m:
        return ("range_bucket", f"elon_musk_posts|window={m.group(1).strip()}")

    m = re.fullmatch(
        r"will (bitcoin|ethereum|xrp|solana) "
        r"(dip to|reach) \$?[\d,]+(?:\.\d+)? "
        r"(.+?)\?",
        q0,
    )
    if m:
        asset, direction, window = m.groups()
        return ("threshold_window", f"{asset}|{direction}|{window}")

    m = re.fullmatch(
        r"will the price of (bitcoin|ethereum|xrp|solana) "
        r"be above \$?[\d,]+(?:\.\d+)? "
        r"(.+?)\?",
        q0,
    )
    if m:
        asset, window = m.groups()
        return ("threshold_window", f"{asset}|above|{window}")

    m = re.fullmatch(
        r"will wti crude oil \(wti\) hit "
        r"\((high|low)\) \$?[\d,]+(?:\.\d+)? "
        r"(.+?)\?",
        q0,
    )
    if m:
        direction, window = m.groups()
        return ("threshold_window", f"wti|{direction}|{window}")

    m = re.fullmatch(
        r"laptop fdv above \$?[\d,.]+[mb] "
        r"one day after launch\?",
        q0,
    )
    if m:
        return ("threshold_window", "laptop_fdv|above|one_day_after_launch")

    return None


def match_decision_point(q0):
    m = re.fullmatch(
        r"will the fed "
        r"(?:increase|decrease) interest rates by "
        r"(?:25|50\+?) bps after the "
        r"(" + MONTHS + r") 2026 meeting\?",
        q0,
    )
    if m:
        return (
            "decision_point",
            f"fed_rate_decision|{m.group(1)}_2026_meeting",
        )

    m = re.fullmatch(
        r"will there be no change in fed interest rates "
        r"after the (" + MONTHS + r") 2026 meeting\?",
        q0,
    )
    if m:
        return (
            "decision_point",
            f"fed_rate_decision|{m.group(1)}_2026_meeting",
        )

    return None


def match_explicit_contest(q0):
    if re.fullmatch(r"will .+ win the 2026 men's us open\?", q0):
        return ("explicit_contest", "tennis|2026_mens_us_open|winner")

    if re.fullmatch(r"will .+ win the 2026 women's us open\?", q0):
        return ("explicit_contest", "tennis|2026_womens_us_open|winner")

    if re.fullmatch(r"will .+ win the clacton by-election\?", q0):
        return ("explicit_contest", "clacton_by_election|winner")

    return None


def match_destination(q0):
    if re.fullmatch(r"will lebron james play for the .+ in 2026-27\?", q0):
        return ("destination_template", "lebron_james|team|2026-27")

    if re.fullmatch(r"will james harden play for the .+ in 2026-27\?", q0):
        return ("destination_template", "james_harden|team|2026-27")

    return None


def match_deadline(q0):
    base = DEADLINE_TAIL.sub("", q0)
    if base != q0:
        base = base.rstrip(" ?")
        if base:
            return ("deadline_series", base)
    return None


def classify_v11(q):
    q0 = clean(q)

    hit = match_range_threshold(q0)
    if hit:
        return hit

    hit = match_decision_point(q0)
    if hit:
        return hit

    hit = match_explicit_contest(q0)
    if hit:
        return hit

    hit = match_destination(q0)
    if hit:
        return hit

    hit = match_deadline(q0)
    if hit:
        return hit

    return ("exact_or_singleton", q0.rstrip(" ?"))


def verify_detector_authority(repo_root: Path) -> None:
    path = repo_root / DETECTOR_RELATIVE_PATH
    if not path.is_file():
        raise EnrollmentError(f"detector authority missing: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != EXPECTED_DETECTOR_SHA256:
        raise EnrollmentError(
            f"detector SHA mismatch: expected {EXPECTED_DETECTOR_SHA256}, "
            f"got {actual}"
        )


def parse_utc(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise EnrollmentError(f"invalid UTC timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        raise EnrollmentError(f"timestamp lacks timezone: {value!r}")
    return dt


def parse_admission_timestamp(value: str) -> datetime:
    try:
        naive = datetime.strptime(str(value), "%Y-%m-%d %H:%M")
    except Exception as exc:
        raise EnrollmentError(f"invalid admission timestamp: {value!r}") from exc
    return naive.replace(tzinfo=PACIFIC)


def require_completed_successful_run(summary: dict) -> dict[str, StageWindow]:
    if summary.get("status") != "success":
        raise EnrollmentError("run status is not success")
    if summary.get("dry_run") is not False:
        raise EnrollmentError("run is dry-run or dry_run is not explicitly false")
    if not summary.get("run_id"):
        raise EnrollmentError("run_id missing")

    stages = summary.get("stages")
    if not isinstance(stages, list):
        raise EnrollmentError("stages missing or invalid")

    by_name = {}
    for stage in stages:
        name = stage.get("stage")
        if name in by_name:
            raise EnrollmentError(f"duplicate stage record: {name}")
        by_name[name] = stage

    result = {}
    for name in ("paper_trader", "run_obi"):
        stage = by_name.get(name)
        if not stage or stage.get("status") != "success":
            raise EnrollmentError(f"{name} stage is not successful")
        if stage.get("exit_code") != 0:
            raise EnrollmentError(f"{name} exit_code is not zero")
        started = parse_utc(stage.get("started"))
        finished = parse_utc(stage.get("finished"))
        if finished < started:
            raise EnrollmentError(f"{name} stage window is reversed")
        result[name] = StageWindow(started, finished)

    return result


def parse_created_trade_ids(text: str) -> tuple[list[int], str]:
    if text.count("New Paper Trades Created") != 1:
        raise EnrollmentError("expected exactly one created-trades section")

    start = text.find("New Paper Trades Created")
    end = text.find("Skipped ", start)
    if end < 0:
        raise EnrollmentError("created-trades section terminator missing")

    section = text[start:end]
    ids = []
    for line in section.splitlines():
        m = re.match(r"^│\s*(\d+)\s*│", line)
        if m:
            ids.append(int(m.group(1)))

    m = re.search(
        r"New trades created:\s*(\d+)\s*\|\s*Skipped:\s*(\d+)",
        text,
    )
    if not m:
        raise EnrollmentError("reported new-trade count missing")

    reported = int(m.group(1))
    if len(ids) != reported:
        raise EnrollmentError(
            f"created trade count mismatch: parsed={len(ids)} reported={reported}"
        )
    if len(ids) != len(set(ids)):
        raise EnrollmentError("duplicate created trade IDs")

    scanner_hits = re.findall(
        r"scanner_run_[0-9]{8}_[0-9]{4}\.csv",
        text,
    )
    unique_scanners = sorted(set(scanner_hits))
    if len(unique_scanners) != 1:
        raise EnrollmentError(
            f"expected exactly one scanner run basename, got {unique_scanners}"
        )

    return ids, unique_scanners[0]


def select_ledger_rows(
    ledger_rows: Iterable[dict],
    created_ids: list[int],
    scanner_run_id: str,
) -> list[dict]:
    wanted = set(created_ids)
    found = {}

    for source in ledger_rows:
        row = {k: source.get(k) for k in LEDGER_ALLOWLIST}
        try:
            trade_id = int(row["trade_id"])
        except Exception as exc:
            raise EnrollmentError("ledger contains invalid trade_id") from exc

        if trade_id not in wanted:
            continue
        if trade_id in found:
            raise EnrollmentError(f"duplicate ledger trade_id: {trade_id}")
        if row["scanner_run_id"] != scanner_run_id:
            raise EnrollmentError(
                f"scanner_run_id mismatch for trade_id {trade_id}"
            )
        found[trade_id] = row

    missing = wanted - set(found)
    if missing:
        raise EnrollmentError(f"created trade IDs missing from ledger: {sorted(missing)}")

    return [found[i] for i in sorted(created_ids)]


def _parse_exact_list(value, field):
    try:
        parsed = ast.literal_eval(str(value))
    except Exception as exc:
        raise EnrollmentError(f"invalid {field} representation") from exc
    if not isinstance(parsed, list):
        raise EnrollmentError(f"{field} is not a list")
    return parsed


def select_anchor(
    provenance_rows: Iterable[dict],
    *,
    slug: str,
    admission_timestamp: datetime,
    run_obi_window: StageWindow,
) -> dict:
    """Select the frozen first successful same-run anchor, then validate it.

    Eligibility failures on that first anchor are terminal for the candidate.
    A later observation must never replace an ineligible first anchor.
    """
    candidates = []

    for source in provenance_rows:
        row = {k: source.get(k) for k in PROVENANCE_REQUIRED}
        if row["slug"] != slug or row["status"] != "ok":
            continue

        ts = parse_utc(row["timestamp"])
        if not (run_obi_window.started <= ts <= run_obi_window.finished):
            continue
        if not (ts > admission_timestamp.astimezone(ts.tzinfo)):
            continue

        candidates.append((ts, row))

    if not candidates:
        raise EnrollmentError(f"no successful same-run OBI anchor for slug {slug}")

    candidates.sort(key=lambda x: x[0])
    ts, row = candidates[0]

    # The frozen anchor has now been selected.  All Study-C eligibility
    # validation happens against this row only; there is no later-row fallback.
    outcomes = _parse_exact_list(row["outcomes"], "outcomes")
    token_ids = _parse_exact_list(row["token_ids"], "token_ids")

    if outcomes != ["Yes", "No"]:
        raise EnrollmentError(
            f"first anchor has ineligible outcomes for slug {slug}"
        )
    if len(token_ids) != 2:
        raise EnrollmentError(
            f"first anchor has ineligible token_ids for slug {slug}"
        )
    if row["outcome_tested"] != "Yes":
        raise EnrollmentError(
            f"first anchor outcome_tested is not Yes for slug {slug}"
        )
    if row["token_id"] != token_ids[0]:
        raise EnrollmentError(
            f"first anchor token_id does not match Yes token for slug {slug}"
        )

    try:
        raw_obi = float(row["raw_obi"])
    except Exception as exc:
        raise EnrollmentError(
            f"first anchor raw_obi is non-numeric for slug {slug}"
        ) from exc

    if not math.isfinite(raw_obi):
        raise EnrollmentError(
            f"first anchor raw_obi is non-finite for slug {slug}"
        )

    out = dict(row)
    out["_timestamp"] = ts
    out["_raw_obi"] = raw_obi
    return out


def build_enrollment_rows(
    *,
    run_id: str,
    ledger_rows: Iterable[dict],
    created_ids: list[int],
    scanner_run_id: str,
    provenance_rows: Iterable[dict],
    run_obi_window: StageWindow,
    activation_boundary: datetime,
    existing_rows: Iterable[dict] = (),
    cap: int = 150,
) -> list[dict]:
    existing = list(existing_rows)
    if len(existing) >= cap:
        return []

    existing_trade_ids = {
        int(r["trade_id"]) for r in existing if r.get("trade_id") not in (None, "")
    }

    selected = select_ledger_rows(ledger_rows, created_ids, scanner_run_id)
    new_rows = []

    for ledger in selected:
        trade_id = int(ledger["trade_id"])
        if trade_id in existing_trade_ids:
            continue

        admission = parse_admission_timestamp(ledger["entry_date"])
        if admission <= activation_boundary:
            continue

        side = ledger["side"]
        if side not in {"Yes", "No"}:
            continue

        anchor = select_anchor(
            provenance_rows,
            slug=ledger["slug"],
            admission_timestamp=admission,
            run_obi_window=run_obi_window,
        )

        raw_obi = anchor["_raw_obi"]
        side_aligned = -raw_obi if side == "Yes" else raw_obi
        family_rule, family_key = classify_v11(ledger["question"])

        sequence = len(existing) + len(new_rows) + 1
        if sequence > cap:
            break

        new_rows.append(
            {
                "enrollment_sequence": sequence,
                "run_id": run_id,
                "trade_id": trade_id,
                "market_id": ledger["market_id"],
                "slug": ledger["slug"],
                "side": side,
                "admission_timestamp": ledger["entry_date"],
                "scanner_run_id": scanner_run_id,
                "publication_id": anchor["publication_id"],
                "lrs2_timestamp": anchor["timestamp"],
                "outcome_tested": anchor["outcome_tested"],
                "token_id": anchor["token_id"],
                "raw_obi": raw_obi,
                "side_aligned_obi": side_aligned,
                "family_rule": family_rule,
                "family_key": family_key,
            }
        )

    return new_rows


def read_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def append_enrollment_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ENROLLMENT_COLUMNS)
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in ENROLLMENT_COLUMNS})
