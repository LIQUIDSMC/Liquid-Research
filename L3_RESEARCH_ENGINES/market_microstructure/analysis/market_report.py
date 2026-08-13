"""
Program B — Market Microstructure Research
Market History Report
programs/program_b/analysis/market_report.py

PURPOSE:
Consolidate the four Phase 2 modules into one organized, readable
summary for a single market. This is Phase 3's first item: turn
Phase 2's infrastructure into something a human can actually read
in one place, without inventing any new measurement.

The ONLY new logic in this module is the observation_summary
section (counts, known snapshots, missing-source warning). Every
other section is a direct, unmodified pass-through of an existing
Phase 2 function's output.

This module does NOT:
- read any CSV directly (uses get_market_history() and the other
  three Phase 2 functions exclusively)
- create any new log
- add any threshold or classification
- synthesize a combined score across sections
- duplicate latest midpoint/OBI/Near-OBI values at the top level —
  those already exist inside latest_change and current_divergence;
  repeating them here would create two sources of truth for the
  same number

Small-n behavior (count=0, count=1, count>=2) is entirely inherited
from the underlying Phase 2 modules. This report does not add or
override any of that logic.
"""

import sys
import os

# sys.path.insert is required here because this module imports
# other Program B modules directly. Modules that only import
# third-party/stdlib packages do not need this.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from L3_RESEARCH_ENGINES.market_microstructure.analysis.history import get_market_history
from L3_RESEARCH_ENGINES.market_microstructure.analysis.change_detector import detect_snapshot_change
from L3_RESEARCH_ENGINES.market_microstructure.analysis.divergence_detector import detect_divergence
from L3_RESEARCH_ENGINES.market_microstructure.analysis.stability_tracker import track_stability


def _build_observation_summary(history, slug: str) -> dict:
    """
    Build the observation_summary section. This is the only new
    logic in this module — everything else is pass-through.

    Receives:
        history (pd.DataFrame): output of get_market_history(slug).
        slug (str): the market slug, used only for the warning text.

    Returns:
        dict: obi_count, near_book_count, known_snapshots,
        missing_source_warning.
    """
    if history.empty:
        return {
            "obi_count": 0,
            "near_book_count": 0,
            "known_snapshots": [],
            "missing_source_warning": f"No observations of any kind exist for '{slug}'.",
        }

    obi_rows = history[history["source"] == "obi"]
    near_rows = history[history["source"] == "near_book"]

    obi_count = len(obi_rows)
    near_book_count = len(near_rows)

    known_snapshots = sorted(history["publication_id"].dropna().unique().tolist())

    warning = None
    if obi_count == 0:
        warning = "No OBI observations exist for this market."
    elif near_book_count == 0:
        warning = "No Near-Book observations exist for this market."

    return {
        "obi_count": obi_count,
        "near_book_count": near_book_count,
        "known_snapshots": known_snapshots,
        "missing_source_warning": warning,
    }


def _get_question(history) -> str:
    """
    Pull the market's question text from history, if available.

    Receives:
        history (pd.DataFrame): output of get_market_history(slug).

    Returns:
        str or None: the question text, or None if no rows exist.
    """
    if history.empty or "question" not in history.columns:
        return None
    non_null = history["question"].dropna()
    return non_null.iloc[0] if len(non_null) > 0 else None


def build_market_report(slug: str) -> dict:
    """
    Build a full Market History Report for a single market,
    consolidating all four Phase 2 modules into one organized dict.

    Receives:
        slug (str): the market slug to report on.

    Returns:
        dict: {
            "slug": str,
            "question": str or None,
            "observation_summary": {...},
            "latest_change": {...full detect_snapshot_change output...},
            "current_divergence": {...full detect_divergence output...},
            "stability": {...full track_stability output...},
        }
    """
    history = get_market_history(slug)

    return {
        "slug": slug,
        "question": _get_question(history),
        "observation_summary": _build_observation_summary(history, slug),
        "latest_change": detect_snapshot_change(slug),
        "current_divergence": detect_divergence(slug),
        "stability": track_stability(slug),
    }


if __name__ == "__main__":
    import json
    from L3_RESEARCH_ENGINES.market_microstructure.analysis.history import list_known_slugs

    slugs = list_known_slugs()
    if slugs:
        result = build_market_report(slugs[0])
        print(json.dumps(result, indent=2, default=str))