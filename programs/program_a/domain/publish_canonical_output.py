"""
Liquid Research — Prediction Markets Domain Publisher
programs/program_a/domain/publish_canonical_output.py

Implements the Prediction Markets Domain's producer responsibility
per zARCHITECTURE.md: publish exactly one canonical output
representing the complete approved research universe for a single
publication cycle.

Four responsibilities only, per architecture review:
    1. Load the latest scanner results.
    2. Load the latest snapshot.
    3. Build the canonical schema (including computing category).
    4. Validate the output before publishing.

STRUCTURAL FAILURE vs. PER-ROW FAILURE:
If a required source file is missing, or a required column is
missing entirely from a source file, this module fails loudly
(raises an exception). If an individual row cannot be published
(missing slug, missing market_id), that row is excluded and
counted. A classification failure never blocks publication of a
row — category falls back to "Unknown" and the failure is logged.

Verified against the current repository structure during
implementation.

The publisher validates its inputs before publication and reports
structural and per-row issues separately so the canonical output
remains transparent and auditable.

No wallet. No private key. No execution. Read-only.
"""

import sys
import os
import pandas as pd
from rich.console import Console

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "analyzers"))
from market_classifier import classify_market

console = Console()

SCANNER_DIR = "data/scanner"
MARKETS_DIR = "data/markets"
OUTPUT_PATH = "data/approved_markets/prediction_markets_latest.csv"

CANONICAL_COLUMNS = [
    "instrument_id", "resolution_id", "instrument_name",
    "tradeability_score", "category", "liquidity", "volume_24h",
    "spread_pct", "spread_label", "days_left",
]

REQUIRED_SCANNER_COLUMNS = [
    "market_id", "question", "tradeability_score", "liquidity",
    "volume_24h", "spread_pct", "spread_label", "killed",
]

REQUIRED_SNAPSHOT_COLUMNS = ["market_id", "slug", "days_left"]


def _find_latest_file(directory: str, pattern: str) -> str:
    """
    Find the most recently created file matching a glob pattern.

    Receives:
        directory (str): folder to search
        pattern (str): glob pattern, e.g. "scanner_run_*.csv"

    Returns:
        str: path to the latest matching file.

    Raises:
        FileNotFoundError: structural failure — no source file to
        publish from.
    """
    import glob
    matches = glob.glob(os.path.join(directory, pattern))
    if not matches:
        raise FileNotFoundError(
            f"No files matching '{pattern}' found in {directory}/. "
            f"Cannot publish canonical output without a source file."
        )
    return max(matches, key=os.path.getmtime)


def _load_and_validate_scanner() -> pd.DataFrame:
    """
    Load the latest scanner run and validate required columns.

    Returns:
        pd.DataFrame: the latest scanner run, unfiltered.

    Raises:
        ValueError: structural failure — required column missing.
    """
    path = _find_latest_file(SCANNER_DIR, "scanner_run_*.csv")
    console.print(f"[dim]Scanner source: {path}[/dim]")
    df = pd.read_csv(path)

    missing = [col for col in REQUIRED_SCANNER_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Scanner output at {path} is missing required column(s): {missing}. "
            f"Cannot build canonical output from an incomplete scanner schema."
        )

    return df


def _load_and_validate_snapshot() -> pd.DataFrame:
    """
    Load the latest market snapshot and validate required columns.

    Returns:
        pd.DataFrame: the latest snapshot.

    Raises:
        ValueError: structural failure — required column missing.
    """
    path = _find_latest_file(MARKETS_DIR, "snapshot_*.csv")
    console.print(f"[dim]Snapshot source: {path}[/dim]")
    df = pd.read_csv(path)

    missing = [col for col in REQUIRED_SNAPSHOT_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Snapshot at {path} is missing required column(s): {missing}. "
            f"Cannot build canonical output without slug/days_left."
        )

    return df


def _compute_category(question: str, classification_failures: list) -> str:
    """
    Compute the category for one instrument using the shared
    classifier. A classification failure never blocks publication —
    it is logged and the row still publishes with category="Unknown".

    Receives:
        question (str): the market's question text.
        classification_failures (list): mutated in place — each
        failure appends (question, error message).

    Returns:
        str: the classified category, or "Unknown" if classification
        fails for any reason.
    """
    try:
        result = classify_market({"title": question or "Unknown", "slug": "", "days_left": None})
        return result.get("category", "Unknown")
    except Exception as e:
        classification_failures.append((question, str(e)))
        return "Unknown"


def _validate_canonical_output(df: pd.DataFrame) -> None:
    """
    Validate the canonical DataFrame before writing it to disk.

    Receives:
        df (pd.DataFrame): the fully-built canonical output.

    Raises:
        ValueError: if column order/presence is wrong, or if
        instrument_id / resolution_id are not unique.
    """
    if df.columns.tolist() != CANONICAL_COLUMNS:
        raise ValueError(
            f"Canonical output column mismatch. Expected exactly "
            f"{CANONICAL_COLUMNS}, got {df.columns.tolist()}."
        )

    if df["instrument_id"].duplicated().any():
        dupes = df[df["instrument_id"].duplicated(keep=False)]["instrument_id"].unique().tolist()
        raise ValueError(f"Duplicate instrument_id values in canonical output: {dupes}")

    if df["resolution_id"].duplicated().any():
        dupes = df[df["resolution_id"].duplicated(keep=False)]["resolution_id"].unique().tolist()
        raise ValueError(f"Duplicate resolution_id values in canonical output: {dupes}")


def publish_prediction_markets_canonical_output() -> dict:
    """
    Build and publish the Prediction Markets Domain's canonical
    output, per zARCHITECTURE.md Section 5.

    Returns:
        dict: {
            "approved_by_scanner": int,
            "matched_to_snapshot": int,
            "duplicate_market_ids": int,
            "published": int,
            "skipped": int,
            "skip_reasons": dict[str, int],
            "classification_failures": int,
            "output_path": str,
        }
    """
    scanner_df = _load_and_validate_scanner()
    snapshot_df = _load_and_validate_snapshot()

    approved = scanner_df.loc[~scanner_df["killed"]].copy()
    approved_count = len(approved)

    duplicate_market_ids = int(snapshot_df["market_id"].duplicated().sum())
    snapshot_lookup = snapshot_df[REQUIRED_SNAPSHOT_COLUMNS].drop_duplicates(subset="market_id")

    merged = approved.merge(
        snapshot_lookup, on="market_id", how="left", suffixes=("", "_snapshot"), indicator=True
    )
    matched_count = int((merged["_merge"] == "both").sum())

    skip_reasons = {}
    classification_failures = []
    published_rows = []

    for _, row in merged.iterrows():
        slug = row.get("slug")
        if pd.isna(slug) or str(slug).strip() == "":
            skip_reasons["missing_slug"] = skip_reasons.get("missing_slug", 0) + 1
            continue

        market_id = row.get("market_id")
        if pd.isna(market_id) or str(market_id).strip() == "":
            skip_reasons["missing_market_id"] = skip_reasons.get("missing_market_id", 0) + 1
            continue

        category = _compute_category(row.get("question"), classification_failures)

        published_rows.append({
            "instrument_id": slug,
            "resolution_id": market_id,
            "instrument_name": row.get("question"),
            "tradeability_score": row.get("tradeability_score"),
            "category": category,
            "liquidity": row.get("liquidity"),
            "volume_24h": row.get("volume_24h"),
            "spread_pct": row.get("spread_pct"),
            "spread_label": row.get("spread_label"),
            "days_left": row.get("days_left"),
        })

    published_df = pd.DataFrame(published_rows, columns=CANONICAL_COLUMNS)
    _validate_canonical_output(published_df)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    published_df.to_csv(OUTPUT_PATH, index=False)

    skipped_count = approved_count - len(published_rows)

    summary = {
        "approved_by_scanner": approved_count,
        "matched_to_snapshot": matched_count,
        "duplicate_market_ids": duplicate_market_ids,
        "published": len(published_rows),
        "skipped": skipped_count,
        "skip_reasons": skip_reasons,
        "classification_failures": len(classification_failures),
        "output_path": OUTPUT_PATH,
    }

    console.print(f"\n[bold cyan]Prediction Markets Domain Published[/bold cyan]\n")
    console.print(f"Approved:  {summary['approved_by_scanner']}")
    console.print(f"Published: [green]{summary['published']}[/green]")
    console.print(f"Skipped:   {summary['skipped']}")
    if skipped_count > 0:
        console.print(f"  [dim]({', '.join(f'{v} {k}' for k, v in skip_reasons.items())})[/dim]")
    if duplicate_market_ids > 0:
        console.print(f"[yellow]Duplicate market_ids in snapshot: {duplicate_market_ids}[/yellow]")
    if classification_failures:
        console.print(f"[yellow]Classification failures: {len(classification_failures)}[/yellow]")
        for question, error in classification_failures:
            console.print(f"  [dim]- {str(question)[:50]}: {error}[/dim]")
    console.print(f"\nSaved:\n{OUTPUT_PATH}\n")

    return summary


if __name__ == "__main__":
    publish_prediction_markets_canonical_output()