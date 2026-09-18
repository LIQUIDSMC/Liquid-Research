"""
LRS-2 — Market Microstructure Research
Historical Market View
L3_RESEARCH_ENGINES/market_microstructure/analysis/history.py

PURPOSE:
Read-only retrieval layer. Reads already-logged observations from
both indicator logs and returns a combined, chronological RAW
OBSERVATION VIEW for a single market. This is the foundation Phase
2 infrastructure — Divergence Detection, Stability Tracking, and
Snapshot Change Detection all consume this rather than duplicating
retrieval logic.

This module creates NO new CSV, writes NO new logs, and deletes NO
historical data.

IMPORTANT — THIS IS A RAW OBSERVATION VIEW, NOT A PAIRED COMPARISON
TABLE:
publication_id + slug is NOT a unique key. Diagnostics have been
rerun against the same publication cycle during testing, producing
multiple real, independent observations for the same publication_id
+ slug. Because of this, get_market_history() returns LONG FORMAT —
one row per real logged observation, tagged with a `source` column
("obi" or "near_book") — rather than attempting to merge OBI and
Near-Book rows into one wide row per market-moment.

An earlier version of this function attempted a wide-format outer
merge on publication_id + slug (then named snapshot_file). This
produced a cartesian product whenever either log had more than one
row for the same key (e.g. 2 OBI rows x 1 Near-Book row = 2
incorrect combined rows). Pairing OBI and Near-Book observations by
nearest timestamp was considered and rejected — it would introduce
an unvalidated heuristic with no ground truth confirming which
observations were "the same moment."

Any future comparison between OBI and Near-Book values (e.g. a
diff calculation) requires an explicit, visible pairing rule and
belongs in a downstream consumer of this function (e.g. Divergence
Detection), not inside raw history retrieval.
"""

import os
import pandas as pd

OBI_LOG_PATH = os.path.join("L3_RESEARCH_ENGINES", "market_microstructure", "data", "obi_log.csv")
NEAR_BOOK_LOG_PATH = os.path.join("L3_RESEARCH_ENGINES", "market_microstructure", "data", "near_book_depth_log.csv")


def _load_logs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load both LRS-2 microstructure logs from disk.

    Returns:
        tuple: (obi_df, near_book_df), each a pandas DataFrame.
               Empty DataFrames if a log file does not exist yet.
    """
    obi_df = pd.read_csv(OBI_LOG_PATH) if os.path.exists(OBI_LOG_PATH) else pd.DataFrame()
    near_df = pd.read_csv(NEAR_BOOK_LOG_PATH) if os.path.exists(NEAR_BOOK_LOG_PATH) else pd.DataFrame()
    return obi_df, near_df


def list_known_slugs() -> list:
    """
    Return every unique slug observed in either log.

    Returns:
        list[str]: sorted, deduplicated slugs.
    """
    obi_df, near_df = _load_logs()

    slugs = set()
    if not obi_df.empty and "slug" in obi_df.columns:
        slugs.update(obi_df["slug"].dropna().unique().tolist())
    if not near_df.empty and "slug" in near_df.columns:
        slugs.update(near_df["slug"].dropna().unique().tolist())

    return sorted(slugs)


def get_market_history(slug: str) -> pd.DataFrame:
    """
    Return every real logged observation for one market, in long
    format, sorted chronologically. See module docstring for why
    this is long format rather than a wide, paired comparison table.

    Receives:
        slug (str): the market slug to retrieve history for.

    Returns:
       pd.DataFrame: one row per real logged observation from
        either log (no merging, no deduplication), with columns:
            timestamp, publication_id, slug, question, source,
            midpoint, bid_count, ask_count, status,
            obi, micro_price, v_bid, v_ask,
            near_obi, n_levels, v_bid_top_n, v_ask_top_n
        `source` is "obi" or "near_book". Columns not applicable
        to a given row's source are NaN (e.g. a "near_book" row
        has NaN for obi, micro_price, v_bid, v_ask).
        Sorted by timestamp ascending. All real rows are preserved,
        including multiple rows sharing the same publication_id if
        a diagnostic was rerun against that publication cycle.
    """
    obi_df, near_df = _load_logs()

    obi_slice = obi_df[obi_df["slug"] == slug].copy() if not obi_df.empty else pd.DataFrame()
    near_slice = near_df[near_df["slug"] == slug].copy() if not near_df.empty else pd.DataFrame()

    if obi_slice.empty and near_slice.empty:
        return pd.DataFrame()

    if not obi_slice.empty:
        obi_slice["source"] = "obi"
    if not near_slice.empty:
        near_slice["source"] = "near_book"
        # Rename to avoid ambiguity with obi_slice's "obi" column meaning
        near_slice = near_slice.rename(columns={"total_obi": "obi"})

    combined = pd.concat([obi_slice, near_slice], ignore_index=True, sort=False)

# Ensure every expected column exists even if one log was empty.
    # Convention: pd.NA/NaN is used for missing values inside
    # DataFrames (like this one). Plain None is used in plain dict
    # outputs intended for humans or JSON serialization (see
    # change_detector.py). Keep these separate — do not mix them
    # within the same return type.
    expected_columns = [
        "timestamp", "publication_id", "slug", "question", "source",
        "midpoint", "bid_count", "ask_count", "status",
        "obi", "micro_price", "v_bid", "v_ask",
        "near_obi", "n_levels", "v_bid_top_n", "v_ask_top_n",
    ]
    for col in expected_columns:
        if col not in combined.columns:
            combined[col] = pd.NA

    combined = combined[expected_columns]

    if "timestamp" in combined.columns:
        combined = combined.sort_values(by="timestamp", na_position="last").reset_index(drop=True)

    return combined


if __name__ == "__main__":
    # Quick manual check when run directly
    slugs = list_known_slugs()
    print(f"Known slugs ({len(slugs)}):")
    for s in slugs:
        print(f"  {s}")