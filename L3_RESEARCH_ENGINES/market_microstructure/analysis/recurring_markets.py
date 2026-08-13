"""
Program B — Market Microstructure Research
Market Observation Index
programs/program_b/analysis/recurring_markets.py

PURPOSE:
Build a cross-market index of observation facts: how many times
each known market has been observed, over what date range, and by
which sources. This is Phase 3's second item.

This module deliberately reports FACTS ONLY. It does not classify
any market as "recurring," does not apply a threshold, does not
assign a priority score, and does not label anything a "research
subject." Whether a given observation count or date range qualifies
as meaningful is a decision to be made later, once enough history
exists to justify a cutoff (see zHANDOFF.md: "prefer better
evidence over more variables").

This is a deliberate, justified exception to the "one slug at a
time" pattern used by every other Phase 2/3 module — this module's
entire purpose is comparison ACROSS markets, which inherently
requires operating on all known slugs at once.

This module reads no CSVs directly. It uses list_known_slugs() and
get_market_history() from analysis/history.py exclusively.
"""

import sys
import os
import pandas as pd

# sys.path.insert is required here because this module imports
# other Program B modules directly. Modules that only import
# third-party/stdlib packages do not need this.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from L3_RESEARCH_ENGINES.market_microstructure.analysis.history import get_market_history, list_known_slugs


def _build_row_for_slug(slug: str) -> dict:
    """
    Build one observation-index row for a single slug.

    Receives:
        slug (str): the market slug to index.

    Returns:
        dict: slug, question, first_seen, last_seen,
        observation_count, snapshot_count, days_observed,
        sources_present.
    """
    history = get_market_history(slug)

    if history.empty:
        return {
            "slug": slug,
            "question": None,
            "first_seen": None,
            "last_seen": None,
            "observation_count": 0,
            "snapshot_count": 0,
            "days_observed": 0,
            "sources_present": "",
        }

    question = None
    non_null_questions = history["question"].dropna()
    if len(non_null_questions) > 0:
        question = non_null_questions.iloc[0]

    timestamps = history["timestamp"].dropna()
    first_seen = timestamps.min() if len(timestamps) > 0 else None
    last_seen = timestamps.max() if len(timestamps) > 0 else None

    observation_count = len(history)

    snapshot_count = history["publication_id"].dropna().nunique()

    # days_observed uses timestamp calendar dates, not publication_id,
    # per the module's design: timestamp is the ground-truth
    # observation moment.
    calendar_dates = timestamps.str.slice(0, 10).unique() if len(timestamps) > 0 else []
    days_observed = len(calendar_dates)

    sources = sorted(history["source"].dropna().unique().tolist())
    sources_present = ", ".join(sources)

    return {
        "slug": slug,
        "question": question,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "observation_count": observation_count,
        "snapshot_count": snapshot_count,
        "days_observed": days_observed,
        "sources_present": sources_present,
    }


def build_market_observation_index() -> pd.DataFrame:
    """
    Build the full observation index across every known market.

    Returns:
        pd.DataFrame: one row per known slug, columns: slug,
        question, first_seen, last_seen, observation_count,
        snapshot_count, days_observed, sources_present. Sorted by
        last_seen descending (most recently observed first).
    """
    slugs = list_known_slugs()
    rows = [_build_row_for_slug(slug) for slug in slugs]

    df = pd.DataFrame(rows)

    if not df.empty and "last_seen" in df.columns:
        df = df.sort_values(by="last_seen", ascending=False, na_position="last").reset_index(drop=True)

    return df


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    index = build_market_observation_index()
    print(index.to_string())