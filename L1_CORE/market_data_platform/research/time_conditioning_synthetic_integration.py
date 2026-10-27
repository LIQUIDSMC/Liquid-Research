"""Synthetic-only kernel-to-report adapter; no source loading or execution CLI.

The synthetic classification is a caller declaration, not authentication.
Historical execution remains unauthorized. Original D0 is not imported.
"""
import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np

from L1_CORE.market_data_platform.research import (
    time_conditioning_descriptive as reporting,
    trade_flow_vs_momentum_screen as kernel,
    run_trade_flow_vs_momentum_screen as runner,
)

VERSION = "TIME_CONDITIONING_SYNTHETIC_INTEGRATION_V1"


def require(condition, message):
    if not condition:
        raise reporting.ReportError(message)


def temporal_masks(times):
    """UTC hour boundaries and timezone-aware NY clock grouping."""
    minute = (times // 60_000) % 60
    hour = (minute >= 45) | (minute < 15)
    ny = ZoneInfo("America/New_York")
    session = np.array([
        570 <= (
            (local := dt.datetime.fromtimestamp(
                int(value) / 1000, tz=dt.timezone.utc
            ).astimezone(ny)).hour * 60 + local.minute
        ) < 960
        for value in times
    ], dtype=np.bool_)
    return {"hour": (hour, ~hour), "session": (session, ~session)}


def group_summary(deciles, returns, mask):
    result = {}
    for label, decile in (("d0", 0), ("d9", 9)):
        selected = mask & (deciles == decile)
        number = int(selected.sum())
        result["n_" + label] = number
        # Preserve a populated decile even when its counterpart is empty.
        result[label + "_mean_return"] = (
            float(np.mean(returns[selected])) if number else None
        )
    return result


def summarize_screen(screen, instrument, day, *, input_classification):
    """Summarize one complete synthetic instrument-day kernel result."""
    require(input_classification == "SYNTHETIC_DEVELOPMENT",
            "Only synthetic-development inputs are authorized")
    require(type(day) is str and day in reporting.DATES,
            "Date outside reporting matrix")
    require(type(instrument) is str and instrument in reporting.INSTRUMENTS,
            "Instrument outside reporting matrix")
    require(type(screen) is dict, "Screen must be a dictionary")
    required = {
        "sample_trade_time", "sample_trade_id", "imbalance",
        "momentum", "common_eligible",
        *(f"return_{h}s" for h in reporting.HORIZONS),
    }
    require(required <= set(screen), "Missing kernel outputs")
    arrays = {name: screen[name] for name in required}
    require(all(isinstance(value, np.ndarray) and value.ndim == 1
                for value in arrays.values()), "Expected one-dimensional arrays")
    lengths = {len(value) for value in arrays.values()}
    require(len(lengths) == 1, "Kernel output lengths differ")
    require(next(iter(lengths)) <= reporting.MAX_ELIGIBLE,
            "Synthetic sample limit exceeded")
    for name in ("sample_trade_time", "sample_trade_id"):
        require(arrays[name].dtype == np.dtype("int64"),
                "Expected int64 timestamp and ID arrays")
    require(arrays["common_eligible"].dtype == np.dtype("bool"),
            "Expected boolean eligibility")
    for name in ("imbalance", "momentum", *(
        f"return_{h}s" for h in reporting.HORIZONS
    )):
        require(arrays[name].dtype == np.dtype("float64"),
                "Expected float64 feature and return arrays")
    start, end = runner._day_bounds_ms(day)
    times = arrays["sample_trade_time"]
    require(bool(np.all((times >= start) & (times < end))),
            "Sample timestamp outside declared UTC day")
    horizons = {}
    for horizon in reporting.HORIZONS:
        pop = runner.build_comparative_population(screen, int(horizon))
        require(all(bool(np.isfinite(pop[name]).all())
                    for name in ("imbalance", "momentum", "return")),
                "Nonfinite eligible population")
        # Rank once across the entire horizon population, before either split.
        deciles = kernel.rank_deciles(
            pop["imbalance"], pop["sample_trade_time"], pop["sample_trade_id"]
        )
        require(len(deciles) == pop["n"]
                and bool(np.all((deciles >= 0) & (deciles <= 9))),
                "Invalid whole-day deciles")
        masks = temporal_masks(pop["sample_trade_time"])
        payload = {"eligible_n": pop["n"]}
        for mechanism, (inside, control) in masks.items():
            payload[mechanism] = {
                "in_window": group_summary(deciles, pop["return"], inside),
                "control": group_summary(deciles, pop["return"], control),
            }
        horizons[horizon] = payload
    return {"date": day, "instrument": instrument, "horizons": horizons}
