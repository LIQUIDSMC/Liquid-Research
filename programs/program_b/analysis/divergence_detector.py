"""
Program B — Market Microstructure Research
Divergence Detection
programs/program_b/analysis/divergence_detector.py

PURPOSE:
Measure the divergence between the latest OBI observation and the
latest Near-Book Depth observation for a market. This is a MEASURE,
not a CLASSIFICATION: no threshold, no alert, no "significant"
label, no historical maximum comparison, no percentile logic. Those
would require more historical data than currently exists to justify
any specific cutoff, per the platform principle "prefer better
evidence over more variables" (see zHANDOFF.md).

PAIRING RULE:
history.py returns long format and deliberately does not pair OBI
and Near-Book rows (see history.py's module docstring for why).
Divergence Detection defines its own explicit pairing rule: compare
the latest OBI observation to the latest Near-Book observation ONLY
if they share the same snapshot_file. snapshot_file represents the
market universe analyzed in one daily cycle; requiring a match
avoids comparing observations from different days as if they were
simultaneous. If the latest observations from each source do not
share a snapshot_file (or either source has no observations at
all), no comparable pair exists — this is reported honestly via
has_comparable_pair=False rather than forcing a stale comparison.

This module reads no CSVs directly. It calls get_market_history()
from analysis/history.py exclusively.

This module implements NO thresholds, NO alerts, NO historical
maximum tracking, and NO percentile-based anomaly detection.
"""

import sys
import os
import pandas as pd

# sys.path.insert is required here because this module imports
# another Program B module directly (history.py). Modules that
# only import third-party/stdlib packages do not need this.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from programs.program_b.analysis.history import get_market_history


def _get_latest_row(source_df: pd.DataFrame) -> dict:
    """
    Return the latest (last, since source_df is chronologically
    sorted) row as a dict, or None if source_df is empty.

    Receives:
        source_df (pd.DataFrame): rows for one source only, already
        sorted chronologically ascending.

    Returns:
        dict or None
    """
    if len(source_df) == 0:
        return None
    return source_df.iloc[-1].to_dict()


def _compute_sign_flip(obi_value, near_obi_value) -> bool:
    """
    Determine whether obi_value and near_obi_value have strictly
    opposite signs. A value of exactly 0 is treated as neutral, not
    flipped relative to anything.

    Receives:
        obi_value (float or None)
        near_obi_value (float or None)

    Returns:
        bool: True only if one value is strictly positive and the
        other strictly negative. False if either value is None,
        zero, or both share the same sign.
    """
    if obi_value is None or near_obi_value is None:
        return False
    if obi_value == 0 or near_obi_value == 0:
        return False
    return (obi_value > 0) != (near_obi_value > 0)


def detect_divergence(slug: str) -> dict:
    """
    Measure divergence between the latest OBI and latest Near-Book
    observation for a market, only if they share the same
    snapshot_file. See module docstring for the full pairing rule.

    Receives:
        slug (str): the market slug to check.

    Returns:
        dict: {
            "slug": str,
            "has_comparable_pair": bool,
            "obi_snapshot_file": str or None,
            "near_book_snapshot_file": str or None,
            "obi_timestamp": str or None,
            "near_book_timestamp": str or None,
            "obi_value": float or None,
            "near_obi_value": float or None,
            "raw_diff": float or None,       # near_obi - obi
            "absolute_diff": float or None,  # abs(near_obi - obi)
            "sign_flip": bool or None,
        }

        If has_comparable_pair is False, obi_snapshot_file /
        near_book_snapshot_file / obi_timestamp / near_book_timestamp
        are still populated where available, so the reason no pair
        was found is visible. raw_diff, absolute_diff, and sign_flip
        are None whenever has_comparable_pair is False.
    """
    history = get_market_history(slug)

    result = {
        "slug": slug,
        "has_comparable_pair": False,
        "obi_snapshot_file": None,
        "near_book_snapshot_file": None,
        "obi_timestamp": None,
        "near_book_timestamp": None,
        "obi_value": None,
        "near_obi_value": None,
        "raw_diff": None,
        "absolute_diff": None,
        "sign_flip": None,
    }

    if history.empty:
        return result

    obi_rows = history[history["source"] == "obi"].reset_index(drop=True)
    near_rows = history[history["source"] == "near_book"].reset_index(drop=True)

    latest_obi = _get_latest_row(obi_rows)
    latest_near = _get_latest_row(near_rows)

    if latest_obi is not None:
        result["obi_snapshot_file"] = latest_obi.get("snapshot_file")
        result["obi_timestamp"] = latest_obi.get("timestamp")
        result["obi_value"] = latest_obi.get("obi")

    if latest_near is not None:
        result["near_book_snapshot_file"] = latest_near.get("snapshot_file")
        result["near_book_timestamp"] = latest_near.get("timestamp")
        result["near_obi_value"] = latest_near.get("near_obi")

    if latest_obi is None or latest_near is None:
        return result

    if result["obi_snapshot_file"] != result["near_book_snapshot_file"]:
        return result

    obi_value = result["obi_value"]
    near_obi_value = result["near_obi_value"]

    if obi_value is None or near_obi_value is None:
        return result

    result["has_comparable_pair"] = True
    result["raw_diff"] = round(float(near_obi_value) - float(obi_value), 6)
    result["absolute_diff"] = round(abs(float(near_obi_value) - float(obi_value)), 6)
    result["sign_flip"] = _compute_sign_flip(float(obi_value), float(near_obi_value))

    return result


if __name__ == "__main__":
    import json
    from programs.program_b.analysis.history import list_known_slugs

    slugs = list_known_slugs()
    if slugs:
        result = detect_divergence(slugs[0])
        print(json.dumps(result, indent=2, default=str))