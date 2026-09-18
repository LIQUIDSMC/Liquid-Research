"""
LRS-2 — Market Microstructure Research
Agreement Matrix
L3_RESEARCH_ENGINES/market_microstructure/analysis/agreement_matrix.py

PURPOSE:
Build a historical, cross-market view of whether OBI and Near-OBI
agree in sign, across every (slug, publication_id) combination
where both an OBI and a Near-Book observation exist. This is Phase
3's fourth and final item, deliberately sequenced last since it
becomes more valuable once other Phase 3 modules reveal which
markets have accumulated enough history to compare repeatedly.

This module does NOT classify agreement as good/bad, does NOT
apply any threshold, and does NOT infer predictive value from
agreement or disagreement. It reports a historical fact: for each
real (slug, publication_id) pairing where both sources exist, did
OBI and Near-OBI have the same sign?

PAIRING RULE:
For each (slug, publication_id), take the LATEST OBI row and the
LATEST Near-Book row for that combination, then compare those two.
This mirrors divergence_detector.py's existing "latest vs latest"
philosophy, extended historically across every publication_id
rather than only the current moment. This avoids the cartesian-
product risk already identified in history.py's design: a
publication_id can have multiple OBI or Near-Book rows (same-cycle
diagnostic reruns), and naively comparing every combination would
fabricate comparisons that don't represent real, distinct
observation moments.

Rows are included ONLY when both an OBI and a Near-Book observation
exist for that (slug, publication_id). Combinations missing one
side are correctly excluded entirely — the same "no forced
comparison" principle used throughout divergence_detector.py.

ZERO HANDLING:
If either obi_value or near_obi_value is exactly 0, same_sign and
sign_flip are both False. Zero is neutral, not agreement or
disagreement — consistent with divergence_detector.py's existing
_compute_sign_flip() convention.

This module reads no CSVs directly. It calls list_known_slugs()
and get_market_history() from analysis/history.py exclusively.
"""

import sys
import os
import pandas as pd

# sys.path.insert is required here because this module imports
# other LRS-2 modules directly. Modules that only import
# third-party/stdlib packages do not need this.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from L3_RESEARCH_ENGINES.market_microstructure.analysis.history import get_market_history, list_known_slugs


def _compute_same_sign(obi_value: float, near_obi_value: float) -> bool:
    """
    Determine whether obi_value and near_obi_value share the same
    sign. A value of exactly 0 is treated as neutral — same_sign is
    False in that case, not True.

    Receives:
        obi_value (float)
        near_obi_value (float)

    Returns:
        bool: True only if both values are strictly positive or
        both strictly negative. False if either is exactly 0.
    """
    if obi_value == 0 or near_obi_value == 0:
        return False
    return (obi_value > 0) == (near_obi_value > 0)


def build_agreement_matrix() -> pd.DataFrame:
    """
    Build the full historical agreement matrix across every known
    market.

    Returns:
        pd.DataFrame: one row per (slug, publication_id) combination
        where both an OBI and a Near-Book observation exist, with
        columns: slug, question, publication_id, snapshot_date,
        obi_timestamp, near_book_timestamp, obi_value,
        near_obi_value, same_sign, sign_flip.

        Combinations missing either source are excluded entirely.
        No duplicate (slug, publication_id) rows are produced — the
        latest OBI row and latest Near-Book row are taken per
        combination before comparison.

        Sorted by snapshot_date, slug, publication_id (all
        ascending) for readability. This sort does not affect any
        calculation or pairing logic.
    """
    rows = []

    for slug in list_known_slugs():
        history = get_market_history(slug)
        if history.empty:
            continue

        obi_rows = history[history["source"] == "obi"]
        near_rows = history[history["source"] == "near_book"]

        if obi_rows.empty or near_rows.empty:
            continue

        common_publications = set(obi_rows["publication_id"].dropna().unique()) & \
                              set(near_rows["publication_id"].dropna().unique())

        for publication_id in sorted(common_publications):
            obi_slice = obi_rows[obi_rows["publication_id"] == publication_id]
            near_slice = near_rows[near_rows["publication_id"] == publication_id]

            # Take the latest row per source for this publication_id
            # (history is already chronologically sorted by
            # get_market_history(), so .iloc[-1] is the latest).
            latest_obi = obi_slice.iloc[-1]
            latest_near = near_slice.iloc[-1]

            obi_value = latest_obi.get("obi")
            near_obi_value = latest_near.get("near_obi")

            if pd.isna(obi_value) or pd.isna(near_obi_value):
                continue

            obi_value = float(obi_value)
            near_obi_value = float(near_obi_value)

            same_sign = _compute_same_sign(obi_value, near_obi_value)
            sign_flip = not same_sign if (obi_value != 0 and near_obi_value != 0) else False

            snapshot_date = str(latest_obi.get("timestamp"))[:10] if pd.notna(latest_obi.get("timestamp")) else None

            rows.append({
                "slug": slug,
                "question": latest_obi.get("question"),
                "publication_id": publication_id,
                "snapshot_date": snapshot_date,
                "obi_timestamp": latest_obi.get("timestamp"),
                "near_book_timestamp": latest_near.get("timestamp"),
                "obi_value": round(obi_value, 6),
                "near_obi_value": round(near_obi_value, 6),
                "same_sign": same_sign,
                "sign_flip": sign_flip,
            })

    columns = [
        "slug", "question", "publication_id", "snapshot_date",
        "obi_timestamp", "near_book_timestamp",
        "obi_value", "near_obi_value", "same_sign", "sign_flip",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df = df[columns]
    df = df.sort_values(
        by=["snapshot_date", "slug", "publication_id"],
        ascending=[True, True, True],
        na_position="last",
    ).reset_index(drop=True)

    return df


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    matrix = build_agreement_matrix()
    print(matrix.to_string())