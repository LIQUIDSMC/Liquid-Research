"""
Program B — Market Microstructure Research
Stability Tracking
programs/program_b/analysis/stability_tracker.py

PURPOSE:
Measure the stability of individual values (OBI, Near-OBI,
midpoint) for a single market across its observed history. This is
a MEASURE, not a CLASSIFICATION: no threshold, no "stable" or
"unstable" label. Per the platform principle "prefer better
evidence over more variables" (see zHANDOFF.md), classification
requires enough historical data to justify a cutoff — that data
does not exist yet at Program B's current volume.

SCOPE:
Four independent sections, each computed from a single filtered
slice of history — no pairing between OBI and Near-Book rows:
    - obi: stability of the obi value from source="obi" rows
    - near_obi: stability of the near_obi value from
      source="near_book" rows
    - midpoint_obi_source: stability of midpoint as recorded by
      the OBI diagnostic (source="obi" rows)
    - midpoint_near_source: stability of midpoint as recorded by
      the Near-Book diagnostic (source="near_book" rows)

Tracking midpoint separately per source (rather than combined) is
intentional: since both diagnostics fetch the same underlying
market moments apart, comparing midpoint_obi_source against
midpoint_near_source over time is an incidental sanity check that
both diagnostics are reading consistent market state.

This module reads no CSVs directly. It calls get_market_history()
from analysis/history.py exclusively.

This module implements NO classification, NO thresholds, and NO
stable/unstable labeling.
"""

import sys
import os
import statistics
import pandas as pd

# sys.path.insert is required here because this module imports
# another Program B module directly (history.py). Modules that
# only import third-party/stdlib packages do not need this.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from programs.program_b.analysis.history import get_market_history


def _compute_stability_section(values: list) -> dict:
    """
    Compute stability metrics for a list of numeric values.

    Receives:
        values (list[float]): observed values in chronological
        order, already filtered to non-null entries.

    Returns:
        dict: count, mean, min, max, range, stddev, latest.

        Small-n behavior:
            count == 0: all numeric fields None
            count == 1: mean/min/max/latest populated, range = 0.0,
                        stddev = None
            count >= 2: all fields populated, stddev computed
    """
    count = len(values)

    if count == 0:
        return {
            "count": 0,
            "mean": None,
            "min": None,
            "max": None,
            "range": None,
            "stddev": None,
            "latest": None,
        }

    mean_val = round(statistics.mean(values), 6)
    min_val = round(min(values), 6)
    max_val = round(max(values), 6)
    latest_val = round(values[-1], 6)

    if count == 1:
        return {
            "count": count,
            "mean": mean_val,
            "min": min_val,
            "max": max_val,
            "range": 0.0,
            "stddev": None,
            "latest": latest_val,
        }

    return {
        "count": count,
        "mean": mean_val,
        "min": min_val,
        "max": max_val,
        "range": round(max_val - min_val, 6),
        "stddev": round(statistics.stdev(values), 6),
        "latest": latest_val,
    }


def _extract_values(df: pd.DataFrame, column: str) -> list:
    """
    Extract non-null values from a column, in the DataFrame's
    current row order (already chronologically sorted by the
    caller, since get_market_history() sorts by timestamp).

    Receives:
        df (pd.DataFrame): rows to extract from.
        column (str): column name to extract.

    Returns:
        list[float]: non-null values as floats, in order.
    """
    if df.empty or column not in df.columns:
        return []
    return [float(v) for v in df[column].dropna().tolist()]


def track_stability(slug: str) -> dict:
    """
    Measure stability of OBI, Near-OBI, and midpoint (tracked
    separately per source) for a single market.

    Receives:
        slug (str): the market slug to check.

    Returns:
        dict: {
            "slug": str,
            "obi": {count, mean, min, max, range, stddev, latest},
            "near_obi": {...same shape...},
            "midpoint_obi_source": {...same shape...},
            "midpoint_near_source": {...same shape...},
        }
    """
    history = get_market_history(slug)

    if history.empty:
        empty_section = _compute_stability_section([])
        return {
            "slug": slug,
            "obi": empty_section,
            "near_obi": dict(empty_section),
            "midpoint_obi_source": dict(empty_section),
            "midpoint_near_source": dict(empty_section),
        }

    obi_rows = history[history["source"] == "obi"].reset_index(drop=True)
    near_rows = history[history["source"] == "near_book"].reset_index(drop=True)

    obi_values = _extract_values(obi_rows, "obi")
    near_obi_values = _extract_values(near_rows, "near_obi")
    midpoint_obi_values = _extract_values(obi_rows, "midpoint")
    midpoint_near_values = _extract_values(near_rows, "midpoint")

    return {
        "slug": slug,
        "obi": _compute_stability_section(obi_values),
        "near_obi": _compute_stability_section(near_obi_values),
        "midpoint_obi_source": _compute_stability_section(midpoint_obi_values),
        "midpoint_near_source": _compute_stability_section(midpoint_near_values),
    }


if __name__ == "__main__":
    import json
    from programs.program_b.analysis.history import list_known_slugs

    slugs = list_known_slugs()
    if slugs:
        result = track_stability(slugs[0])
        print(json.dumps(result, indent=2, default=str))