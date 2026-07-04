"""
Program B — Order Book Imbalance / Micro-Price Diagnostic
programs/program_b/obi_diagnostic.py

PURPOSE:
Feasibility check only. Answers one question:
"Can OBI and micro-price be computed correctly from data we already collect?"

This script:
- Uses existing scanner/clob_client.py with no modifications
- Computes OBI and micro-price from raw bid/ask lists
- Prints results in a readable table
- Appends each run to programs/program_b/data/obi_log.csv
- Creates programs/program_b/data/ if it does not exist
- Places no trades
- Introduces no new dependencies

THREE-QUESTION CHECK (must pass before any further Program B work):
1. Is it mathematically correct?   <- what this script tests
2. Is it stable across many markets? <- requires more runs over time
3. Does it improve a trading decision? <- do NOT assume yes yet

FORMULAS:
OBI  = (V_bid - V_ask) / (V_bid + V_ask)
       Range: -1 to +1. Positive = more bid pressure. Negative = more ask pressure.
       Uses total volume across all book levels (standard definition).

Micro-price = (best_bid * V_ask + best_ask * V_bid) / (V_bid + V_ask)
              Volume-weighted blend of best bid and ask.
              Accounts for order book pressure unlike simple midpoint.

ASSUMPTIONS AND LIMITATIONS:
- OBI uses total volume across ALL book levels, not just the inside market.
- Micro-price assumes best bid/ask sizes are meaningful — may not hold in thin books.
- A single snapshot reveals nothing about predictive value. That is Phase 2.
- This is a feasibility check only.
"""

import sys
import os
import csv
from datetime import datetime, UTC
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from scanner.clob_client import get_market_clob_data, fetch_order_book, parse_clob_token_ids, fetch_market_by_slug
from rich.console import Console
from rich.table import Table

console = Console()


def load_slugs_from_latest_snapshot(n: int = 5) -> tuple:
    """
    Read the most recent Program A market snapshot and return the
    first n slugs. This keeps Program B automatically aligned with
    Program A's current market universe without hard-coded identifiers.

    Receives:
        n (int): number of slugs to return (default 5)

    Returns:
        list[str]: slug values, or [] if no snapshot found
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



def compute_obi_and_microprice(bids: list, asks: list, best_bid: float, best_ask: float) -> dict:
    """
    Compute Order Book Imbalance and Micro-Price from raw book levels.

    OBI = (V_bid - V_ask) / (V_bid + V_ask)
    Micro-price = (best_bid * V_ask + best_ask * V_bid) / (V_bid + V_ask)

    Returns dict with obi, micro_price, v_bid, v_ask, and any error.
    """
    try:
        v_bid = sum(float(b["size"]) for b in bids if "size" in b)
        v_ask = sum(float(a["size"]) for a in asks if "size" in a)
    except (ValueError, TypeError) as e:
        return {"obi": None, "micro_price": None, "v_bid": None, "v_ask": None, "error": str(e)}

    total = v_bid + v_ask
    if total == 0:
        return {"obi": None, "micro_price": None, "v_bid": v_bid, "v_ask": v_ask, "error": "Zero total volume"}

    obi = round((v_bid - v_ask) / total, 4)

    if best_bid is None or best_ask is None:
        return {"obi": obi, "micro_price": None, "v_bid": v_bid, "v_ask": v_ask, "error": "Missing best bid/ask for micro-price"}

    micro_price = round((best_bid * v_ask + best_ask * v_bid) / total, 6)

    return {"obi": obi, "micro_price": micro_price, "v_bid": round(v_bid, 2), "v_ask": round(v_ask, 2), "error": None}


LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "obi_log.csv")
LOG_COLUMNS = [
    "timestamp", "snapshot_file", "slug", "question",
    "midpoint", "micro_price", "obi", "v_bid", "v_ask",
    "bid_count", "ask_count", "status",
]


def log_to_csv(row: dict) -> None:
    """
    Append one row to programs/program_b/data/obi_log.csv.
    Creates the data/ directory and CSV header if they do not exist.

    Receives:
        row (dict): must contain all keys in LOG_COLUMNS
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(LOG_PATH)

    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    console.print("\n[bold cyan]Program B — OBI Diagnostic[/bold cyan]")
    console.print("[dim]Feasibility check: computing OBI and micro-price from existing CLOB data[/dim]\n")

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

        # Fetch raw book again to get full bid/ask lists for volume calculation
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
