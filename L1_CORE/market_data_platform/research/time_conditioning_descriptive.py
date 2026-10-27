"""Synthetic-development descriptive reporting; no I/O or analyzer execution.

This module accepts summarized synthetic group counts and return means.
It cannot establish authenticity, population coverage, or correct upstream
decile assignment. Malformed inputs raise ReportError; structurally invalid
cells remain explicit within a completed descriptive report.
"""
import datetime as dt
import json
import math

VERSION = "TIME_CONDITIONING_DESCRIPTIVE_V1"
INSTRUMENTS = ("BTC-USD", "ETH-USD")
HORIZONS = ("5", "15", "30", "60")
MECHANISMS = ("hour", "session")
DATES = tuple(
    [(dt.date(2026, 7, 22) + dt.timedelta(days=i)).isoformat() for i in range(19)]
    + [(dt.date(2026, 8, 26) + dt.timedelta(days=i)).isoformat() for i in range(5)]
)
MAX_ELIGIBLE = 100_000
MAX_REPORT_BYTES = 1024**2
GROUP_FIELDS = {"n_d0", "n_d9", "d0_mean_return", "d9_mean_return"}


class ReportError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReportError(message)


def count(value, maximum, label):
    require(type(value) is int and 0 <= value <= maximum,
            "Invalid count: " + label)
    return value


def mean_value(value):
    if value is None:
        return None
    require(type(value) in (int, float), "Return mean must be numeric or null")
    try:
        converted = float(value)
    except OverflowError:
        return None
    return converted if math.isfinite(converted) else None


def summarize_group(group, eligible):
    require(type(group) is dict and set(group) == GROUP_FIELDS,
            "Group fields mismatch")
    low = count(group["n_d0"], eligible, "n_d0")
    high = count(group["n_d9"], eligible, "n_d9")
    require(low + high <= eligible, "Group decile counts exceed eligible population")
    for number, key in ((low, "d0_mean_return"), (high, "d9_mean_return")):
        require(number != 0 or group[key] is None,
                "Empty decile must have a null mean")
    low_mean = mean_value(group["d0_mean_return"])
    high_mean = mean_value(group["d9_mean_return"])
    reasons = []
    if low == 0:
        reasons.append("EMPTY_D0")
    if high == 0:
        reasons.append("EMPTY_D9")
    if low > 0 and low_mean is None:
        reasons.append("MISSING_OR_NONFINITE_D0_MEAN")
    if high > 0 and high_mean is None:
        reasons.append("MISSING_OR_NONFINITE_D9_MEAN")
    edge = None
    if not reasons:
        edge = (high_mean - low_mean) * 10000.0
        if not math.isfinite(edge):
            edge = None
            reasons.append("NONFINITE_EDGE")
    return {
        "valid": not reasons, "n_d0": low, "n_d9": high,
        "d0_mean_return": low_mean, "d9_mean_return": high_mean,
        "edge_bp": edge, "invalid_reasons": reasons,
    }


def summarize_cell(cell, eligible):
    require(type(cell) is dict and set(cell) == {"in_window", "control"},
            "Mechanism cell fields mismatch")
    inside = summarize_group(cell["in_window"], eligible)
    control = summarize_group(cell["control"], eligible)
    require(
        sum(group["n_d0"] + group["n_d9"] for group in (inside, control)) <= eligible,
        "Temporal-group decile counts exceed eligible population",
    )
    reasons = []
    if not inside["valid"]:
        reasons.append("INVALID_IN_WINDOW")
    if not control["valid"]:
        reasons.append("INVALID_CONTROL")
    delta = None
    if not reasons:
        delta = inside["edge_bp"] - control["edge_bp"]
        if not math.isfinite(delta):
            delta = None
            reasons.append("NONFINITE_DELTA")
    return {
        "valid": not reasons, "eligible_n": eligible,
        "in_window": inside, "control": control,
        "delta_bp": delta, "invalid_reasons": reasons,
    }


def finite_mean(values):
    require(bool(values) and all(math.isfinite(value) for value in values),
            "Invalid descriptive-mean inputs")
    try:
        result = math.fsum(value / len(values) for value in values)
    except OverflowError as error:
        raise ReportError("Descriptive mean overflow") from error
    require(math.isfinite(result), "Nonfinite descriptive mean")
    return result


def stats(values):
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = (
        ordered[middle] if len(ordered) % 2
        else ordered[middle - 1] / 2.0 + ordered[middle] / 2.0
    )
    require(math.isfinite(median), "Nonfinite descriptive median")
    return {
        "n": len(values), "mean": finite_mean(values),
        "median": median, "min": ordered[0], "max": ordered[-1],
    }


def summarize_mechanism(records):
    """Keep all 48 cells; pair only valid BTC/ETH results from the same date."""
    by_key = {(item["date"], item["instrument"]): item for item in records}
    pairs = []
    for day in DATES:
        btc = by_key[(day, "BTC-USD")]
        eth = by_key[(day, "ETH-USD")]
        valid = btc["valid"] and eth["valid"]
        pairs.append({
            "date": day, "valid": valid,
            "btc_delta_bp": btc["delta_bp"],
            "eth_delta_bp": eth["delta_bp"],
            "paired_delta_bp": (
                btc["delta_bp"] / 2.0 + eth["delta_bp"] / 2.0 if valid else None
            ),
            "invalid_instruments": [
                item["instrument"] for item in (btc, eth) if not item["valid"]
            ],
        })
    valid_pairs = [item for item in pairs if item["valid"]]
    values = [item["paired_delta_bp"] for item in valid_pairs]
    sensitivity = None
    if len(valid_pairs) >= 2:
        sensitivity = [
            {
                "excluded_date": item["date"],
                "remaining_date_pairs": len(valid_pairs) - 1,
                "mean_paired_delta_bp": finite_mean([
                    other["paired_delta_bp"]
                    for other in valid_pairs if other["date"] != item["date"]
                ]),
            }
            for item in valid_pairs
        ]
    return {
        "instrument_days": records,
        "per_instrument": {
            instrument: {
                "valid_instrument_days": sum(
                    item["valid"] for item in records if item["instrument"] == instrument
                ),
                "invalid_dates": [
                    item["date"] for item in records
                    if item["instrument"] == instrument and not item["valid"]
                ],
                "delta_bp": stats([
                    item["delta_bp"] for item in records
                    if item["instrument"] == instrument and item["valid"]
                ]),
            }
            for instrument in INSTRUMENTS
        },
        "date_pairs": pairs,
        "valid_date_pairs": len(valid_pairs),
        "invalid_dates": [item["date"] for item in pairs if not item["valid"]],
        "paired_delta_bp": stats(values),
        "strictly_positive_date_pairs": sum(value > 0 for value in values),
        "zero_date_pairs": sum(value == 0 for value in values),
        "negative_date_pairs": sum(value < 0 for value in values),
        "leave_one_date_out": sensitivity,
        "sensitivity_unavailable_reason": (
            "FEWER_THAN_TWO_VALID_DATE_PAIRS" if sensitivity is None else None
        ),
    }


def encode_report(report):
    raw = (json.dumps(
        report, sort_keys=True, indent=2, allow_nan=False
    ) + "\n").encode("utf-8")
    require(len(raw) <= MAX_REPORT_BYTES, "Descriptive report exceeds 1 MiB")
    return raw


def build_report(records, *, input_classification):
    """Pure reporting API. Classification is an operator declaration, not security."""
    require(input_classification == "SYNTHETIC_DEVELOPMENT",
            "Only synthetic-development inputs are authorized")
    require(type(records) is list and len(records) == 48,
            "Exactly 48 instrument-day records required")
    require(len(DATES) == 24 and len(set(DATES)) == 24
            and all(day < "2026-09-04" for day in DATES),
            "Invalid reporting-date policy")
    expected = {(day, instrument) for day in DATES for instrument in INSTRUMENTS}
    normalized = {}
    for record in records:
        require(type(record) is dict
                and set(record) == {"date", "instrument", "horizons"},
                "Instrument-day fields mismatch")
        require(type(record["date"]) is str and type(record["instrument"]) is str,
                "Invalid matrix-key types")
        key = (record["date"], record["instrument"])
        require(key in expected and key not in normalized,
                "Duplicate or out-of-scope instrument-day")
        horizons = record["horizons"]
        require(type(horizons) is dict and set(horizons) == set(HORIZONS),
                "Horizon fields mismatch")
        result = {}
        for horizon in HORIZONS:
            value = horizons[horizon]
            require(type(value) is dict
                    and set(value) == {"eligible_n", *MECHANISMS},
                    "Horizon payload fields mismatch")
            eligible = count(value["eligible_n"], MAX_ELIGIBLE, "eligible_n")
            result[horizon] = {
                mechanism: summarize_cell(value[mechanism], eligible)
                for mechanism in MECHANISMS
            }
        normalized[key] = result
    require(set(normalized) == expected, "Incomplete reporting matrix")

    report = {
        "schema_version": 1, "version": VERSION,
        "classification": "COMPLETE_DESCRIPTIVE",
        "input_classification": input_classification,
        "study_status": "DRAFT / UNFROZEN",
        "dates": list(DATES), "instruments": list(INSTRUMENTS),
        "instrument_day_count": 48, "primary_horizon_s": 60,
        "secondary_descriptive_horizons_s": [5, 15, 30],
        "mechanisms": {
            mechanism: {
                horizon: summarize_mechanism([
                    {
                        "date": day, "instrument": instrument,
                        **normalized[(day, instrument)][horizon][mechanism],
                    }
                    for day in DATES for instrument in INSTRUMENTS
                ])
                for horizon in HORIZONS
            }
            for mechanism in MECHANISMS
        },
        "limitations": [
            "Synthetic summarized inputs; no historical outcomes computed.",
            "Upstream populations, means and decile assignments are not authenticated.",
            "Invalid cells and date pairs are disclosed, not imputed.",
            "Valid-subset summaries do not repair invalid dates.",
            "Instrument-days and calendar dates are not assumed independent.",
            "Secondary horizons cannot rescue a primary finding.",
            "No p-values, significance, automatic winner, or promotion decision.",
            "COMPLETE_DESCRIPTIVE denotes processing completion, not scientific validity.",
            "Production transfer, historical execution and H2 access remain unauthorized.",
        ],
    }
    encode_report(report)
    return report
