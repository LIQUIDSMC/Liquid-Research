"""
Program B — Market Microstructure Research
Snapshot Change Detector
programs/program_b/analysis/change_detector.py

PURPOSE:
Simplest possible consumer of Historical Market View. Validates
that the retrieval layer (analysis/history.py) can support real
downstream analysis without duplicating any retrieval logic.

Compares the latest observation against the immediately previous
observation, per source (OBI, Near-Book), for a given market. This
is NOT "today vs yesterday" — Program B logs are append-only and
diagnostics can be rerun against the same publication cycle, so the
correct comparison is chronological: latest OBI vs previous OBI,
latest Near-Book vs previous Near-Book. OBI and Near-Book rows are
never compared against each other.

This module reads no CSVs directly. It calls get_market_history()
from analysis/history.py exclusively.

This module implements NO divergence detection and NO stability
tracking. Those are separate, later Phase 2 items.
"""

import sys
import os
import pandas as pd

# sys.path.insert is required here because this module imports
# another Program B module directly (history.py). Modules that
# only import third-party/stdlib packages (e.g. history.py itself)
# do not need this.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from programs.program_b.analysis.history import get_market_history


def _build_source_section(source_df: pd.DataFrame) -> dict:
    """
    Build the change-detection section for a single source's rows
    (already filtered and sorted chronologically by the caller).

    Receives:
        source_df (pd.DataFrame): rows for one source only (either
        all "obi" rows or all "near_book" rows), already sorted
        chronologically ascending.

Returns:
        dict: has_change, previous, latest, previous_timestamp,
        latest_timestamp, previous_publication_id,
        latest_publication_id, midpoint_delta, bid_count_delta,
        ask_count_delta.
    """
    n = len(source_df)

    if n == 0:
        return {
            "has_change": False,
            "previous": None,
            "latest": None,
"previous_timestamp": None,
            "latest_timestamp": None,
            "previous_publication_id": None,
            "latest_publication_id": None,
            "midpoint_delta": None,
            "bid_count_delta": None,
            "ask_count_delta": None,
        }
    
    latest_row = source_df.iloc[-1].to_dict()

    if n == 1:
        return {
            "has_change": False,
            "previous": None,
            "latest": latest_row,
            "previous_timestamp": None,
            "latest_timestamp": latest_row.get("timestamp"),
            "previous_publication_id": None,
            "latest_publication_id": latest_row.get("publication_id"),
            "midpoint_delta": None,
            "bid_count_delta": None,
            "ask_count_delta": None,
        }

    previous_row = source_df.iloc[-2].to_dict()

    def safe_delta(latest_val, previous_val):
        try:
            if latest_val is None or previous_val is None:
                return None
            return round(float(latest_val) - float(previous_val), 6)
        except (ValueError, TypeError):
            return None

    return {
        "has_change": True,
        "previous": previous_row,
        "latest": latest_row,
        "previous_timestamp": previous_row.get("timestamp"),
        "latest_timestamp": latest_row.get("timestamp"),
        "previous_publication_id": previous_row.get("publication_id"),
        "latest_publication_id": latest_row.get("publication_id"),
        "midpoint_delta": safe_delta(latest_row.get("midpoint"), previous_row.get("midpoint")),
        "bid_count_delta": safe_delta(latest_row.get("bid_count"), previous_row.get("bid_count")),
        "ask_count_delta": safe_delta(latest_row.get("ask_count"), previous_row.get("ask_count")),
    }


def detect_snapshot_change(slug: str) -> dict:
    """
    Compare the latest observation to the immediately previous
    observation, separately for OBI and Near-Book sources.

    Receives:
        slug (str): the market slug to check.

    Returns:
        dict: {
            "slug": str,
            "obi": { ...see _build_source_section... , "obi_delta": float or None },
            "near_book": { ...see _build_source_section... , "near_obi_delta": float or None },
        }
    """
    history = get_market_history(slug)

    if history.empty:
        empty_obi = _build_source_section(history)
        empty_obi["obi_delta"] = None
        empty_near = _build_source_section(history)
        empty_near["near_obi_delta"] = None
        return {"slug": slug, "obi": empty_obi, "near_book": empty_near}

    obi_rows = history[history["source"] == "obi"].reset_index(drop=True)
    near_rows = history[history["source"] == "near_book"].reset_index(drop=True)

    obi_section = _build_source_section(obi_rows)
    if obi_section["has_change"]:
        latest_obi = obi_section["latest"].get("obi")
        previous_obi = obi_section["previous"].get("obi")
        if latest_obi is not None and previous_obi is not None:
            obi_section["obi_delta"] = round(float(latest_obi) - float(previous_obi), 6)
        else:
            obi_section["obi_delta"] = None
    else:
        obi_section["obi_delta"] = None

    near_section = _build_source_section(near_rows)
    if near_section["has_change"]:
        latest_near = near_section["latest"].get("near_obi")
        previous_near = near_section["previous"].get("near_obi")
        if latest_near is not None and previous_near is not None:
            near_section["near_obi_delta"] = round(float(latest_near) - float(previous_near), 6)
        else:
            near_section["near_obi_delta"] = None
    else:
        near_section["near_obi_delta"] = None

    return {"slug": slug, "obi": obi_section, "near_book": near_section}


if __name__ == "__main__":
    import json
    from programs.program_b.analysis.history import list_known_slugs

    slugs = list_known_slugs()
    if slugs:
        result = detect_snapshot_change(slugs[0])
        print(json.dumps(result, indent=2, default=str))