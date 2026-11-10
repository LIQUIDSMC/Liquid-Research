import csv
import json
from pathlib import Path

from L3_RESEARCH_ENGINES.market_microstructure.analysis.run_study_c_enrollment import (
    read_ledger_outcome_blind,
)


def test_runtime_ledger_reader_does_not_return_outcomes(tmp_path):
    path = tmp_path / "paper_trades.csv"
    fields = [
        "trade_id",
        "entry_date",
        "market_id",
        "slug",
        "question",
        "side",
        "scanner_run_id",
        "trade_won",
        "trade_pnl",
        "winning_outcome",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(
            {
                "trade_id": 1,
                "entry_date": "2026-11-10 05:01",
                "market_id": "m1",
                "slug": "s1",
                "question": "Q?",
                "side": "Yes",
                "scanner_run_id": "scanner_run_20261110_0501.csv",
                "trade_won": "POISON",
                "trade_pnl": "POISON",
                "winning_outcome": "POISON",
            }
        )

    rows = read_ledger_outcome_blind(path)
    assert len(rows) == 1
    assert "trade_won" not in rows[0]
    assert "trade_pnl" not in rows[0]
    assert "winning_outcome" not in rows[0]
