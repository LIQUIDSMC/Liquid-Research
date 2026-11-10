import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from L3_RESEARCH_ENGINES.market_microstructure.analysis.study_c_enrollment import (
    EXPECTED_DETECTOR_SHA256,
    EnrollmentError,
    StageWindow,
    build_enrollment_rows,
    classify_v11,
    parse_created_trade_ids,
    require_completed_successful_run,
    select_ledger_rows,
)


def successful_summary():
    return {
        "run_id": "20261110T130002Z",
        "status": "success",
        "dry_run": False,
        "stages": [
            {
                "stage": "paper_trader",
                "status": "success",
                "started": "2026-11-10T13:01:50Z",
                "finished": "2026-11-10T13:01:54Z",
                "exit_code": 0,
            },
            {
                "stage": "run_obi",
                "status": "success",
                "started": "2026-11-10T13:03:14Z",
                "finished": "2026-11-10T13:04:09Z",
                "exit_code": 0,
            },
        ],
    }


def trader_log(ids=(1001, 1002), reported=2):
    rows = "\n".join(f"│ {i} │ Market │ Yes │" for i in ids)
    return f"""
Scanner run:
L2_DOMAINS/prediction_markets/data/scanner/scanner_run_20261110_0501.csv
New Paper Trades Created
{rows}
Skipped 30 candidate(s):
New trades created: {reported} | Skipped: 30
"""


def ledger_row(trade_id, slug="slug-a", side="Yes", question="Question A?"):
    return {
        "trade_id": str(trade_id),
        "entry_date": "2026-11-10 05:01",
        "market_id": f"m-{trade_id}",
        "slug": slug,
        "question": question,
        "side": side,
        "scanner_run_id": "scanner_run_20261110_0501.csv",
        # Poison outcome-bearing values: implementation must ignore them.
        "trade_won": "POISON",
        "trade_pnl": "POISON",
        "winning_outcome": "POISON",
    }


def provenance(slug="slug-a", raw="0.25", ts="2026-11-10T13:03:20Z"):
    return {
        "timestamp": ts,
        "publication_id": "20261110_050149",
        "slug": slug,
        "outcomes": "['Yes', 'No']",
        "token_ids": "['YES-TOKEN', 'NO-TOKEN']",
        "outcome_tested": "Yes",
        "token_id": "YES-TOKEN",
        "raw_obi": raw,
        "status": "ok",
    }


def test_run_contract_requires_success_non_dry_and_stage_success():
    windows = require_completed_successful_run(successful_summary())
    assert windows["paper_trader"].started.isoformat() == "2026-11-10T13:01:50+00:00"

    bad = successful_summary()
    bad["dry_run"] = True
    with pytest.raises(EnrollmentError):
        require_completed_successful_run(bad)

    bad = successful_summary()
    bad["stages"][1]["status"] = "failed"
    with pytest.raises(EnrollmentError):
        require_completed_successful_run(bad)


def test_exact_created_trade_ids_scanner_and_count_contract():
    ids, scanner = parse_created_trade_ids(trader_log())
    assert ids == [1001, 1002]
    assert scanner == "scanner_run_20261110_0501.csv"

    with pytest.raises(EnrollmentError):
        parse_created_trade_ids(trader_log(ids=(1001, 1001), reported=2))

    with pytest.raises(EnrollmentError):
        parse_created_trade_ids(trader_log(ids=(1001,), reported=2))


def test_ledger_selection_is_outcome_blind_and_scanner_bound():
    a = ledger_row(1001)
    b = dict(a)
    b["trade_won"] = "DIFFERENT"
    b["trade_pnl"] = "DIFFERENT"

    out_a = select_ledger_rows(
        [a], [1001], "scanner_run_20261110_0501.csv"
    )
    out_b = select_ledger_rows(
        [b], [1001], "scanner_run_20261110_0501.csv"
    )
    assert out_a == out_b
    assert "trade_won" not in out_a[0]
    assert "trade_pnl" not in out_a[0]

    bad = ledger_row(1001)
    bad["scanner_run_id"] = "scanner_run_19990101_0000.csv"
    with pytest.raises(EnrollmentError):
        select_ledger_rows(
            [bad], [1001], "scanner_run_20261110_0501.csv"
        )


def test_yes_side_alignment_and_first_same_run_anchor():
    activation = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    window = StageWindow(
        datetime(2026, 11, 10, 13, 3, 14, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 13, 4, 9, tzinfo=timezone.utc),
    )
    rows = build_enrollment_rows(
        run_id="20261110T130002Z",
        ledger_rows=[ledger_row(1001)],
        created_ids=[1001],
        scanner_run_id="scanner_run_20261110_0501.csv",
        provenance_rows=[
            provenance(raw="0.40", ts="2026-11-10T13:03:40Z"),
            provenance(raw="0.25", ts="2026-11-10T13:03:20Z"),
        ],
        run_obi_window=window,
        activation_boundary=activation,
    )
    assert len(rows) == 1
    assert rows[0]["raw_obi"] == 0.25
    assert rows[0]["side_aligned_obi"] == -0.25
    assert rows[0]["outcome_tested"] == "Yes"
    assert rows[0]["token_id"] == "YES-TOKEN"



def test_ineligible_first_anchor_cannot_be_replaced_by_later_valid_row():
    activation = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    window = StageWindow(
        datetime(2026, 11, 10, 13, 3, 14, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 13, 4, 9, tzinfo=timezone.utc),
    )

    first = provenance(raw="0.10", ts="2026-11-10T13:03:20Z")
    first["outcomes"] = "['No', 'Yes']"

    later = provenance(raw="0.90", ts="2026-11-10T13:03:40Z")

    with pytest.raises(EnrollmentError):
        build_enrollment_rows(
            run_id="20261110T130002Z",
            ledger_rows=[ledger_row(1001)],
            created_ids=[1001],
            scanner_run_id="scanner_run_20261110_0501.csv",
            provenance_rows=[later, first],
            run_obi_window=window,
            activation_boundary=activation,
        )


def test_no_side_alignment():
    activation = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    window = StageWindow(
        datetime(2026, 11, 10, 13, 3, 14, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 13, 4, 9, tzinfo=timezone.utc),
    )
    rows = build_enrollment_rows(
        run_id="r",
        ledger_rows=[ledger_row(1001, side="No")],
        created_ids=[1001],
        scanner_run_id="scanner_run_20261110_0501.csv",
        provenance_rows=[provenance(raw="-0.3")],
        run_obi_window=window,
        activation_boundary=activation,
    )
    assert rows[0]["side_aligned_obi"] == -0.3


@pytest.mark.parametrize(
    "change",
    [
        {"outcomes": "['No', 'Yes']"},
        {"outcomes": "['Yes']"},
        {"token_ids": "['YES-TOKEN']"},
        {"outcome_tested": "No"},
        {"token_id": "NO-TOKEN"},
        {"raw_obi": "nan"},
        {"status": "error"},
    ],
)
def test_token_and_measurement_contract_fails_closed(change):
    activation = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    window = StageWindow(
        datetime(2026, 11, 10, 13, 3, 14, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 13, 4, 9, tzinfo=timezone.utc),
    )
    p = provenance()
    p.update(change)
    with pytest.raises(EnrollmentError):
        build_enrollment_rows(
            run_id="r",
            ledger_rows=[ledger_row(1001)],
            created_ids=[1001],
            scanner_run_id="scanner_run_20261110_0501.csv",
            provenance_rows=[p],
            run_obi_window=window,
            activation_boundary=activation,
        )


def test_pre_activation_admission_is_not_enrolled():
    activation = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)
    window = StageWindow(
        datetime(2026, 11, 10, 13, 3, 14, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 13, 4, 9, tzinfo=timezone.utc),
    )
    rows = build_enrollment_rows(
        run_id="r",
        ledger_rows=[ledger_row(1001)],
        created_ids=[1001],
        scanner_run_id="scanner_run_20261110_0501.csv",
        provenance_rows=[provenance()],
        run_obi_window=window,
        activation_boundary=activation,
    )
    assert rows == []


def test_idempotence_ordering_and_cap():
    activation = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    window = StageWindow(
        datetime(2026, 11, 10, 13, 3, 14, tzinfo=timezone.utc),
        datetime(2026, 11, 10, 13, 4, 9, tzinfo=timezone.utc),
    )
    ledger = [
        ledger_row(1002, slug="slug-b"),
        ledger_row(1001, slug="slug-a"),
    ]
    prov = [
        provenance(slug="slug-a"),
        provenance(slug="slug-b"),
    ]
    existing = [{"trade_id": "999", "enrollment_sequence": "1"}]
    rows = build_enrollment_rows(
        run_id="r",
        ledger_rows=ledger,
        created_ids=[1002, 1001],
        scanner_run_id="scanner_run_20261110_0501.csv",
        provenance_rows=prov,
        run_obi_window=window,
        activation_boundary=activation,
        existing_rows=existing,
        cap=2,
    )
    assert [r["trade_id"] for r in rows] == [1001]
    assert rows[0]["enrollment_sequence"] == 2

    again = build_enrollment_rows(
        run_id="r",
        ledger_rows=ledger,
        created_ids=[1001],
        scanner_run_id="scanner_run_20261110_0501.csv",
        provenance_rows=prov,
        run_obi_window=window,
        activation_boundary=activation,
        existing_rows=existing + rows,
        cap=150,
    )
    assert again == []


def test_classifier_frozen_examples_and_normalization():
    assert classify_v11("Will Bitcoin dip to $72,500 tomorrow?") == (
        "threshold_window",
        "bitcoin|dip to|tomorrow",
    )
    assert classify_v11("Will X win the 2026 men's US Open?") == (
        "explicit_contest",
        "tennis|2026_mens_us_open|winner",
    )
    assert classify_v11("Will LeBron James play for the Lakers in 2026–27?") == (
        "destination_template",
        "lebron_james|team|2026-27",
    )
    assert classify_v11("  SOME   QUESTION?  ") == (
        "exact_or_singleton",
        "some question",
    )


def test_detector_sha_constant_matches_current_authority():
    root = Path(__file__).resolve().parents[3]
    detector = (
        root
        / "L3_RESEARCH_ENGINES"
        / "market_selection"
        / "analysis"
        / "latent_event_family_detector_v1_1.py"
    )
    actual = hashlib.sha256(detector.read_bytes()).hexdigest()
    assert actual == EXPECTED_DETECTOR_SHA256
