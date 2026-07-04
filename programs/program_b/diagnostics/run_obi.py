"""
Program B — Market Microstructure Research
Diagnostic Runner: Order Book Imbalance (OBI) and Micro-Price
programs/program_b/diagnostics/run_obi.py

PURPOSE:
Feasibility and stability check. Answers:
"Can OBI and micro-price be computed correctly from data we already
collect, and are they stable across markets and over time?"

This script:
- Uses existing scanner/clob_client.py with no modifications
- Uses programs/program_b/indicators/obi.py for calculation
- Prints results in a readable table
- Appends each run to data/program_b/obi_log.csv
- Creates data/program_b/ if it does not exist
- Places no trades
- Introduces no new dependencies

THREE-QUESTION CHECK (must pass before any further Program B work):
1. Is it mathematically correct?   <- confirmed
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
from rich.console import Console
from rich.table import Table

console = Console()

LOG_PATH = os.path.join("data", "program_b", "obi_log.csv")
LOG_COLUMNS = [
    "timestamp", "snapshot_file", "slug", "question",
    "midpoint", "micro_price", "obi", "v_bid", "v_ask",
    "bid_count", "ask_count", "status",
]


def load_slugs_from_latest_snapshot(n: int = 5) -> tuple:
    """
    Read the most recent Program A market snapshot and return the
    first n slugs.

    Returns:
        tuple: (list[str] slugs, str snapshot filename), or ([], "") if none found
    """
    import glob
    import pandas as pd

    snapshots = sorted(glob.glob("data/markets/snapshot_*.csv"))
    if not snapshots:
        return [], ""

    latest = snapshots[-1]
    console.print(f"[dim]Reading slugs from: {latest}[/dim]")

    try:
        df = pd.read_csv(latest)
        if "slug" not in df.columns:
            console.print("[red]No slug column found in snapshot.[/red]")
            return [], ""
        return df["slug"].dropna().tolist()[:n], os.path.basename(latest)
    except Exception as e:
        console.print(f"[red]Failed to read snapshot: {e}[/red]")
        return [], ""


def log_to_csv(row: dict) -> None:
    """
    Append one row to data/program_b/obi_log.csv.
    Creates data/program_b/ and the CSV header if they do not exist.
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(LOG_PATH)

    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    console.print("\n[bold cyan]Program B — Market Microstructure Research[/bold cyan]")
    console.print("[dim]Indicator: OBI / Micro-Price — stability check[/dim]\n")

    table = Table(show_lines=True)
    table.add_column("Market", max_width=28)
    table.add_column("Midpoint", justify="right")
    table.add_column("Micro-Price", justify="right")
    table.add_column("OBI", justify="right")
    table.add_column("V_Bid", justify="right")
    table.add_column("V_Ask", justify="right")
    table.add_column("Bids", justify="right")
    table.add_column("Asks", justify="right")
    table.add_column("Status")

    slugs, snapshot_file = load_slugs_from_latest_snapshot(n=5)
    if not slugs:
        console.print("[red]No slugs found. Is data/markets/ populated?[/red]")
        return

    for slug in slugs:
        clob = get_market_clob_data(slug, outcome_index=0, include_official=False)

        if clob["status"] not in ("ok", "incomplete_book"):
            table.add_row(
                slug[:26],
                "-", "-", "-", "-", "-", "-", "-",
                f"FAILED: {clob['status']}"
            )
            continue

        market = fetch_market_by_slug(slug)
        token_ids = parse_clob_token_ids(market)
        if not token_ids:
            table.add_row(slug[:26], "-", "-", "-", "-", "-", "-", "-", "No token IDs")
            continue

        book = fetch_order_book(token_ids[0])
        if not book["success"]:
            table.add_row(slug[:26], "-", "-", "-", "-", "-", "-", "-", f"Book failed: {book['error']}")
            continue

        metrics = compute_obi_and_microprice(
            book["bids"], book["asks"],
            clob["best_bid"], clob["best_ask"]
        )

        question_short = (clob["question"] or slug)[:26]
        midpoint_str = f"{clob['midpoint']:.4f}" if clob["midpoint"] else "-"
        micro_str = f"{metrics['micro_price']:.4f}" if metrics["micro_price"] is not None else "-"
        obi_str = f"{metrics['obi']:+.4f}" if metrics["obi"] is not None else "-"
        vbid_str = f"{metrics['v_bid']:.0f}" if metrics["v_bid"] is not None else "-"
        vask_str = f"{metrics['v_ask']:.0f}" if metrics["v_ask"] is not None else "-"
        status = metrics["error"] if metrics["error"] else "ok"

        log_to_csv({
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "snapshot_file": snapshot_file,
            "slug": slug,
            "question": clob.get("question") or "",
            "midpoint": clob["midpoint"] if clob["midpoint"] is not None else "",
            "micro_price": metrics["micro_price"] if metrics["micro_price"] is not None else "",
            "obi": metrics["obi"] if metrics["obi"] is not None else "",
            "v_bid": metrics["v_bid"] if metrics["v_bid"] is not None else "",
            "v_ask": metrics["v_ask"] if metrics["v_ask"] is not None else "",
            "bid_count": clob["bid_count"],
            "ask_count": clob["ask_count"],
            "status": status,
        })

        table.add_row(
            question_short,
            midpoint_str,
            micro_str,
            obi_str,
            vbid_str,
            vask_str,
            str(clob["bid_count"]),
            str(clob["ask_count"]),
            status
        )

    console.print(table)
    console.print("\n[dim]Note: OBI range is -1 to +1. Positive = more bid volume. Negative = more ask volume.[/dim]")
    console.print("[dim]Micro-price is a volume-weighted reference price. Compare to midpoint for pressure direction.[/dim]\n")


if __name__ == "__main__":
    main()
