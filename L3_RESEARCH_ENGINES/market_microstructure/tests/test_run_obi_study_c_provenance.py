import csv

from L3_RESEARCH_ENGINES.market_microstructure.collection import run_obi


EXPECTED_COLUMNS = [
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


def test_study_c_provenance_schema_is_frozen():
    assert run_obi.STUDY_C_PROVENANCE_COLUMNS == EXPECTED_COLUMNS


def test_study_c_provenance_writer_round_trip(tmp_path, monkeypatch):
    target = tmp_path / "study_c_measurement_provenance.csv"
    monkeypatch.setattr(run_obi, "STUDY_C_PROVENANCE_PATH", str(target))

    row = {
        "timestamp": "2026-11-10T13:03:14Z",
        "publication_id": "20261110_050149",
        "slug": "example-market",
        "outcomes": repr(["Yes", "No"]),
        "token_ids": repr(["yes-token", "no-token"]),
        "outcome_tested": "Yes",
        "token_id": "yes-token",
        "raw_obi": -0.125,
        "status": "ok",
    }

    run_obi.log_study_c_measurement_provenance(row)

    with target.open(newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert list(rows[0].keys()) == EXPECTED_COLUMNS
    assert rows[0]["timestamp"] == row["timestamp"]
    assert rows[0]["publication_id"] == row["publication_id"]
    assert rows[0]["slug"] == row["slug"]
    assert rows[0]["outcomes"] == "['Yes', 'No']"
    assert rows[0]["token_ids"] == "['yes-token', 'no-token']"
    assert rows[0]["outcome_tested"] == "Yes"
    assert rows[0]["token_id"] == "yes-token"
    assert float(rows[0]["raw_obi"]) == -0.125
    assert rows[0]["status"] == "ok"


def test_existing_obi_schema_is_unchanged():
    assert run_obi.LOG_COLUMNS == [
        "timestamp",
        "publication_id",
        "slug",
        "question",
        "midpoint",
        "micro_price",
        "obi",
        "v_bid",
        "v_ask",
        "bid_count",
        "ask_count",
        "status",
    ]


def test_main_provenance_uses_exact_second_fetch_token_identity(monkeypatch):
    obi_rows = []
    provenance_rows = []
    fetched_book_tokens = []

    monkeypatch.setattr(
        run_obi,
        "load_approved_slugs",
        lambda: (["example-market"], "pub-1"),
    )

    # First retrieval deliberately carries a different token identity.
    monkeypatch.setattr(
        run_obi,
        "get_market_clob_data",
        lambda *args, **kwargs: {
            "status": "ok",
            "question": "Example?",
            "midpoint": 0.5,
            "best_bid": 0.49,
            "best_ask": 0.51,
            "bid_count": 1,
            "ask_count": 1,
            "token_id": "FIRST-FETCH-TOKEN",
            "outcome_tested": "FIRST-FETCH-OUTCOME",
        },
    )

    # This second retrieval is the market identity used immediately before
    # the book fetch that actually produces the OBI measurement.
    monkeypatch.setattr(
        run_obi,
        "fetch_market_by_slug",
        lambda slug: {
            "outcomes": '["Yes", "No"]',
            "clobTokenIds": '["SECOND-YES-TOKEN", "SECOND-NO-TOKEN"]',
        },
    )

    def fake_fetch_order_book(token_id):
        fetched_book_tokens.append(token_id)
        return {
            "success": True,
            "bids": [{"price": "0.49", "size": "10"}],
            "asks": [{"price": "0.51", "size": "5"}],
        }

    monkeypatch.setattr(run_obi, "fetch_order_book", fake_fetch_order_book)
    monkeypatch.setattr(
        run_obi,
        "compute_obi_and_microprice",
        lambda *args, **kwargs: {
            "micro_price": 0.5,
            "obi": 0.3333,
            "v_bid": 10.0,
            "v_ask": 5.0,
            "error": None,
        },
    )
    monkeypatch.setattr(run_obi, "log_to_csv", obi_rows.append)
    monkeypatch.setattr(
        run_obi,
        "log_study_c_measurement_provenance",
        provenance_rows.append,
    )

    run_obi.main()

    assert fetched_book_tokens == ["SECOND-YES-TOKEN"]
    assert len(obi_rows) == 1
    assert len(provenance_rows) == 1

    obi_row = obi_rows[0]
    provenance = provenance_rows[0]

    assert provenance["outcomes"] == "['Yes', 'No']"
    assert provenance["token_ids"] == "['SECOND-YES-TOKEN', 'SECOND-NO-TOKEN']"
    assert provenance["outcome_tested"] == "Yes"
    assert provenance["token_id"] == "SECOND-YES-TOKEN"
    assert provenance["raw_obi"] == 0.3333
    assert provenance["status"] == "ok"

    # Both artifacts must describe the same measurement instant.
    assert provenance["timestamp"] == obi_row["timestamp"]
    assert provenance["publication_id"] == obi_row["publication_id"] == "pub-1"
    assert provenance["slug"] == obi_row["slug"] == "example-market"

    # Explicit regression guard against accidentally using first-fetch identity.
    assert provenance["token_id"] != "FIRST-FETCH-TOKEN"
    assert provenance["outcome_tested"] != "FIRST-FETCH-OUTCOME"
