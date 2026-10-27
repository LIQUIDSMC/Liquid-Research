"""Fabricated summary records only; no files or analyzers are consumed."""
import copy
import json

import pytest

from L1_CORE.market_data_platform.research import time_conditioning_descriptive as report


def fixture_records():
    records = []
    for day in report.DATES:
        for instrument in report.INSTRUMENTS:
            delta = 2.0 if instrument == "BTC-USD" else 4.0
            group = lambda high: {
                "n_d0": 2, "n_d9": 2,
                "d0_mean_return": 0.0, "d9_mean_return": high,
            }
            cell = {
                "in_window": group(delta / 10000.0),
                "control": group(0.0),
            }
            records.append({
                "date": day, "instrument": instrument,
                "horizons": {
                    horizon: {
                        "eligible_n": 100,
                        "hour": copy.deepcopy(cell),
                        "session": copy.deepcopy(cell),
                    }
                    for horizon in report.HORIZONS
                },
            })
    return records


def build(records):
    return report.build_report(
        records, input_classification="SYNTHETIC_DEVELOPMENT"
    )


def primary(result, mechanism="hour"):
    return result["mechanisms"][mechanism]["60"]


def test_exact_paired_summaries_and_no_input_mutation():
    records = fixture_records()
    original = copy.deepcopy(records)
    result = build(records)
    summary = primary(result)
    assert records == original
    assert result["classification"] == "COMPLETE_DESCRIPTIVE"
    assert result["input_classification"] == "SYNTHETIC_DEVELOPMENT"
    assert summary["valid_date_pairs"] == 24
    assert summary["paired_delta_bp"]["mean"] == pytest.approx(3.0)
    assert summary["per_instrument"]["BTC-USD"]["delta_bp"]["mean"] == pytest.approx(2)
    assert summary["per_instrument"]["ETH-USD"]["delta_bp"]["mean"] == pytest.approx(4)
    assert summary["strictly_positive_date_pairs"] == 24
    assert len(summary["leave_one_date_out"]) == 24
    assert all(
        item["mean_paired_delta_bp"] == pytest.approx(3)
        and item["remaining_date_pairs"] == 23
        for item in summary["leave_one_date_out"]
    )
    assert "decision" not in summary
    assert len(report.encode_report(result)) <= report.MAX_REPORT_BYTES


def test_record_order_does_not_change_report():
    records = fixture_records()
    assert build(records) == build(list(reversed(records)))


def test_nonfinite_cell_remains_explicit_and_json_safe():
    records = fixture_records()
    records[0]["horizons"]["60"]["hour"]["in_window"]["d9_mean_return"] = float("nan")
    result = build(records)
    summary = primary(result)
    assert result["classification"] == "COMPLETE_DESCRIPTIVE"
    assert summary["valid_date_pairs"] == 23
    assert summary["invalid_dates"] == [report.DATES[0]]
    assert summary["date_pairs"][0]["invalid_instruments"] == ["BTC-USD"]
    assert summary["date_pairs"][0]["paired_delta_bp"] is None
    raw = report.encode_report(result)
    assert b"NaN" not in raw
    assert json.loads(raw)["classification"] == "COMPLETE_DESCRIPTIVE"


def test_empty_decile_is_invalid_without_imputation():
    records = fixture_records()
    group = records[0]["horizons"]["60"]["hour"]["in_window"]
    group.update(n_d9=0, d9_mean_return=None)
    summary = primary(build(records))
    assert summary["valid_date_pairs"] == 23
    assert summary["instrument_days"][0]["in_window"]["invalid_reasons"] == ["EMPTY_D9"]


def test_all_invalid_pairs_have_no_sensitivity():
    records = fixture_records()
    for record in records:
        group = record["horizons"]["60"]["hour"]["in_window"]
        group.update(n_d9=0, d9_mean_return=None)
    summary = primary(build(records))
    assert summary["valid_date_pairs"] == 0
    assert summary["paired_delta_bp"]["mean"] is None
    assert summary["leave_one_date_out"] is None
    assert len(summary["invalid_dates"]) == 24


def test_one_valid_pair_has_no_leave_one_out_mean():
    records = fixture_records()
    for record in records[2:]:
        group = record["horizons"]["60"]["hour"]["in_window"]
        group.update(n_d9=0, d9_mean_return=None)
    summary = primary(build(records))
    assert summary["valid_date_pairs"] == 1
    assert summary["leave_one_date_out"] is None


def test_secondary_horizon_does_not_repair_primary():
    records = fixture_records()
    records[0]["horizons"]["60"]["hour"]["in_window"]["d9_mean_return"] = None
    result = build(records)
    assert primary(result)["valid_date_pairs"] == 23
    assert result["mechanisms"]["hour"]["5"]["valid_date_pairs"] == 24


def test_zero_deltas_are_not_positive():
    records = fixture_records()
    for record in records:
        for horizon in report.HORIZONS:
            for mechanism in report.MECHANISMS:
                record["horizons"][horizon][mechanism]["in_window"]["d9_mean_return"] = 0
    summary = primary(build(records))
    assert summary["strictly_positive_date_pairs"] == 0
    assert summary["zero_date_pairs"] == 24


@pytest.mark.parametrize("kind", ["missing", "duplicate", "sealed_date", "unknown_instrument"])
def test_invalid_matrix_rejected(kind):
    records = fixture_records()
    if kind == "missing":
        records.pop()
    elif kind == "duplicate":
        records[-1] = copy.deepcopy(records[0])
    elif kind == "sealed_date":
        records[0]["date"] = "2026-09-04"
    else:
        records[0]["instrument"] = "OTHER"
    with pytest.raises(report.ReportError):
        build(records)


@pytest.mark.parametrize("value", [True, -1, 100001, 1.5])
def test_invalid_eligible_count_rejected(value):
    records = fixture_records()
    records[0]["horizons"]["60"]["eligible_n"] = value
    with pytest.raises(report.ReportError):
        build(records)


def test_group_counts_cannot_exceed_population():
    records = fixture_records()
    records[0]["horizons"]["60"]["eligible_n"] = 7
    with pytest.raises(report.ReportError, match="Temporal-group"):
        build(records)


def test_empty_decile_with_nonnull_mean_is_malformed():
    records = fixture_records()
    records[0]["horizons"]["60"]["hour"]["in_window"]["n_d0"] = 0
    with pytest.raises(report.ReportError, match="null mean"):
        build(records)


def test_non_synthetic_declaration_rejected():
    with pytest.raises(report.ReportError, match="synthetic-development"):
        report.build_report(fixture_records(), input_classification="HISTORICAL")


def test_reporting_needs_no_file_or_subprocess_access(monkeypatch):
    import builtins
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected I/O")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert primary(build(fixture_records()))["valid_date_pairs"] == 24
