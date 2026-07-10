"""
Program B — Market Microstructure Research
Diagnostic Runner: Near-Book Depth Imbalance vs. Total-Book OBI
programs/program_b/diagnostics/run_near_book_depth.py

PURPOSE:
Compares near-book depth imbalance (top N levels) against total-book
OBI to test whether they diverge meaningfully. Both values are
computed and logged together so comparison requires no later join.

This script:
- Uses existing scanner/clob_client.py with no modifications
- Uses indicators/obi.py and indicators/near_book_depth.py
- Prints both metrics side-by-side in a readable table
- Appends each run to data/program_b/near_book_depth_log.csv
- Does NOT modify data/program_b/obi_log.csv
- Places no trades
- Introduces no new dependencies

THREE-QUESTION CHECK (must pass before this indicator is trusted):
1. Is it mathematically correct?   <- verify against hand calculation
2. Is it stable across many markets? <- testing now, this script's purpose
3. Does it improve a trading decision? <- do NOT assume yes yet
"""

import sys
import os
import csv
from datetime import datetime, UTC

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from scanner.clob_client import get_market_clob_data, fetch_order_book, parse_clob_token_ids, fetch_market_by_slug
from programs.program_b.indicators.obi import compute_obi_and_microprice
from programs.program_b.indicators.near_book_depth import compute_near_book_obi
from rich.console import Console
from rich.table import Table

console = Console()

LOG_PATH = os.path.join("data", "program_b", "near_book_depth_log.csv")
LOG_COLUMNS = [
    "timestamp", "publication_id", "slug", "question",
    "midpoint", "total_obi", "near_obi", "n_levels",
    "v_bid_top_n", "v_ask_top_n", "bid_count", "ask_count", "status",
]

N_LEVELS = 5


def load_approved_slugs() -> tuple:
    """
    Read the Prediction Markets Domain's canonical output and
    return every approved instrument_id, per zARCHITECTURE.md
    Section 5.

    Returns:
        tuple: (list[str] instrument_ids, str publication_id for
        this publication cycle), or ([], "") if the canonical
        output does not exist or is missing required columns.
    """
    import pandas as pd
    canonical_path = "data/approved_markets/prediction_markets_latest.csv"
    if not os.path.exists(canonical_path):
        console.print(
            f"[red]No canonical output found at {canonical_path}. "
            f"Run programs/program_a/domain/publish_canonical_output.py first.[/red]"
        )
        return [], ""
    console.print(f"[dim]Reading approved instruments from: {canonical_path}[/dim]")
    try:
        df = pd.read_csv(canonical_path)
        if "instrument_id" not in df.columns or "publication_id" not in df.columns:
            console.print("[red]Canonical output missing instrument_id or publication_id column.[/red]")
            return [], ""
        slugs = df["instrument_id"].dropna().tolist()
        publication_id = df["publication_id"].iloc[0] if len(df) > 0 else ""
        return slugs, publication_id
    except Exception as e:
        console.print(f"[red]Failed to read canonical output: {e}[/red]")
        return [], ""


def log_to_csv(row: dict) -> None:
    """
    Append one row to data/program_b/near_book_depth_log.csv.

    Schema uses publication_id as the canonical identifier
    for the Program A publication cycle.

    Creates data/program_b/ and the CSV header if they do not exist.
    Does NOT touch obi_log.csv.
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(LOG_PATH)

    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    console.print("\n[bold cyan]Program B — Market Microstructure Research[/bold cyan]")
    console.print(f"[dim]Indicator: Near-Book Depth (N={N_LEVELS}) vs. Total-Book OBI[/dim]\n")
    table = Table(show_lines=True)
    table.add_column("Market", max_width=24)
    table.add_column("Midpoint", justify="right")
    table.add_column("Total OBI", justify="right")
    table.add_column("Near OBI", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("Bids", justify="right")
    table.add_column("Asks", justify="right")
    table.add_column("Status")

    slugs, publication_id = load_approved_slugs()
    if not slugs:
        console.print("[red]No slugs found. Is the canonical output populated?[/red]")
        return

    for slug in slugs:
        clob = get_market_clob_data(slug, outcome_index=0, include_official=False)

        if clob["status"] not in ("ok", "incomplete_book"):
            table.add_row(slug[:22], "-", "-", "-", "-", "-", "-", f"FAILED: {clob['status']}")
            continue

        market = fetch_market_by_slug(slug)
        token_ids = parse_clob_token_ids(market)
        if not token_ids:
            table.add_row(slug[:22], "-", "-", "-", "-", "-", "-", "No token IDs")
            continue

        book = fetch_order_book(token_ids[0])
        if not book["success"]:
            table.add_row(slug[:22], "-", "-", "-", "-", "-", "-", f"Book failed: {book['error']}")
            continue

        total_metrics = compute_obi_and_microprice(
            book["bids"], book["asks"], clob["best_bid"], clob["best_ask"]
        )
        near_metrics = compute_near_book_obi(book["bids"], book["asks"], n=N_LEVELS)

        question_short = (clob["question"] or slug)[:22]
        midpoint_str = f"{clob['midpoint']:.4f}" if clob["midpoint"] else "-"
        total_obi_str = f"{total_metrics['obi']:+.4f}" if total_metrics["obi"] is not None else "-"
        near_obi_str = f"{near_metrics['near_obi']:+.4f}" if near_metrics["near_obi"] is not None else "-"

        if total_metrics["obi"] is not None and near_metrics["near_obi"] is not None:
            diff = round(near_metrics["near_obi"] - total_metrics["obi"], 4)
            diff_str = f"{diff:+.4f}"
        else:
            diff_str = "-"

        status_parts = []
        if total_metrics["error"]:
            status_parts.append(f"total: {total_metrics['error']}")
        if near_metrics["error"]:
            status_parts.append(f"near: {near_metrics['error']}")
        status = "; ".join(status_parts) if status_parts else "ok"

        log_to_csv({
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publication_id": publication_id,
            "slug": slug,
            "question": clob.get("question") or "",
            "midpoint": clob["midpoint"] if clob["midpoint"] is not None else "",
            "total_obi": total_metrics["obi"] if total_metrics["obi"] is not None else "",
            "near_obi": near_metrics["near_obi"] if near_metrics["near_obi"] is not None else "",
            "n_levels": N_LEVELS,
            "v_bid_top_n": near_metrics["v_bid_top_n"] if near_metrics["v_bid_top_n"] is not None else "",
            "v_ask_top_n": near_metrics["v_ask_top_n"] if near_metrics["v_ask_top_n"] is not None else "",
            "bid_count": clob["bid_count"],
            "ask_count": clob["ask_count"],
            "status": status,
        })

        table.add_row(
            question_short,
            midpoint_str,
            total_obi_str,
            near_obi_str,
            diff_str,
            str(clob["bid_count"]),
            str(clob["ask_count"]),
            status
        )

    console.print(table)
    console.print(f"\n[dim]Near OBI uses only the top {N_LEVELS} price levels closest to the midpoint per side.[/dim]")
    console.print("[dim]Total OBI uses all book levels. Large Diff values suggest near-book pressure differs from total pressure.[/dim]\n")


if __name__ == "__main__":
    main()
