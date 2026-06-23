"""
Liquid Research — Paper Resolver (Phase 5)

Checks open paper trades against real market resolution status.
Reuses analyzers/market_resolution.py's already-validated
fetch_market_by_slug() and determine_winning_outcome() — slug-
first lookup, the confirmed-reliable method. Does NOT invent any
new resolution logic and does NOT use conditionId lookup as a
primary path.

If a market's resolution_confidence is Open, Unconfirmed, or
Partial, the trade is left exactly as it was — no fabricated
P&L, no guessed win/loss. Only a Confirmed resolution causes any
field to change.

P&L formula (paper only, no real money):
  trade_won = True:  profit = position_size * ((1 / entry_price) - 1)
  trade_won = False: profit = -position_size

Read-only. No wallet. No private key. No execution.

Usage:
    python3 simulator/paper_resolver.py
"""

import sys
import os
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzers"))
from market_resolution import fetch_market_by_slug, determine_winning_outcome

console = Console()

PAPER_TRADES_PATH = "data/simulator/paper_trades.csv"


def calculate_paper_pnl(trade_won: bool, entry_price: float, position_size: float) -> float:
    """
    Calculate paper P&L using the fixed position size, only once
    a trade's outcome is genuinely known.

    Receives:
        trade_won (bool)
        entry_price (float)
        position_size (float)

    Returns:
        float: profit (positive) or loss (negative), rounded to 2 decimals
    """
    if trade_won:
        if entry_price <= 0:
            return 0.0  # defensive guard, should never occur with real prices
        profit = position_size * ((1.0 / entry_price) - 1.0)
    else:
        profit = -position_size

    return round(profit, 2)


def resolve_one_trade(row: pd.Series) -> dict:
    """
    Check one open trade's market against live resolution status.
    Returns the fields to update, or an unchanged copy if still
    not Confirmed.

    Receives:
        row (pd.Series): one row from paper_trades.csv

    Returns:
        dict: {
            "outcome": "closed" / "still_open" / "skipped",
            "updates": dict of fields to apply (empty if no change)
        }
    """
    slug = row.get("slug")

    if pd.isna(slug) or str(slug).strip() == "":
        return {"outcome": "skipped", "updates": {}}

    market = fetch_market_by_slug(slug)
    resolution = determine_winning_outcome(market)

    confidence = resolution["resolution_confidence"]

    if confidence != "Confirmed":
        # Open, Unconfirmed, or Partial — leave trade exactly as is
        return {"outcome": "still_open", "updates": {}}

    winning_outcome = resolution["winning_outcome"]
    side = row.get("side")

    # IMPORTANT: "side" is always "Yes" or "No" because that's how
    # market_collector.py labels outcomes[0]/outcomes[1] regardless
    # of what a market's real outcome names are (e.g. named-outcome
    # markets like "Naomi Osaka" vs "Magdalena Frech"). We cannot
    # compare "side" directly against winning_outcome by string —
    # we must compare by POSITION: is the winning outcome the FIRST
    # listed outcome (== "Yes" side) or the SECOND (== "No" side)?
    outcomes = market.get("outcomes")
    try:
        import json
        outcomes_list = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
    except (TypeError, ValueError):
        outcomes_list = None

    if not outcomes_list or len(outcomes_list) < 2:
        # Cannot safely determine position-based match — do not
        # guess. Leave trade open rather than fabricate a result.
        return {"outcome": "still_open", "updates": {}}

    first_outcome, second_outcome = outcomes_list[0], outcomes_list[1]

    if winning_outcome == first_outcome:
        trade_won = (side == "Yes")
    elif winning_outcome == second_outcome:
        trade_won = (side == "No")
    else:
        # Winning outcome doesn't match either known position —
        # something is wrong with this market's data. Do not guess.
        return {"outcome": "still_open", "updates": {}}

    entry_price = float(row.get("entry_price"))
    position_size = float(row.get("position_size"))
    trade_pnl = calculate_paper_pnl(trade_won, entry_price, position_size)


    updates = {
        "status": "closed",
        "resolution_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "winning_outcome": winning_outcome,
        "trade_won": trade_won,
        "trade_pnl": trade_pnl,
        "exit_reason": "market_resolved",
    }

    return {"outcome": "closed", "updates": updates}


def main():
    console.print("\n[bold cyan]Liquid Research — Paper Resolver (Phase 5)[/bold cyan]")

    if not os.path.exists(PAPER_TRADES_PATH):
        console.print(f"[red]No paper trades file found at {PAPER_TRADES_PATH}. Run paper_trader.py first.[/red]")
        return

    df = pd.read_csv(PAPER_TRADES_PATH)

    # Force these columns to a flexible (object) dtype before writing
    # into them. When paper_trader.py first creates the CSV, these
    # columns are entirely blank, so pandas infers them as float64
    # (all-NaN). Without this fix, writing a real date/string/bool
    # value into them later raises a LossySetitemError.
    for column in ["resolution_date", "winning_outcome", "trade_won", "trade_pnl", "exit_reason"]:
        if column in df.columns:
            df[column] = df[column].astype(object)

    open_mask = df["status"] == "open"

    open_count = open_mask.sum()
    non_open_count = len(df) - open_count

    console.print(f"Loaded {len(df)} total trades. Checking {open_count} open trade(s)...\n")

    closed_rows = []
    still_open_rows = []
    skipped_rows = []

    for idx in df[open_mask].index:
        row = df.loc[idx]
        result = resolve_one_trade(row)

        if result["outcome"] == "closed":
            for field, value in result["updates"].items():
                df.at[idx, field] = value
            closed_rows.append(row["question"])
        elif result["outcome"] == "still_open":
            still_open_rows.append(row["question"])
        else:
            skipped_rows.append(row["question"])

    df.to_csv(PAPER_TRADES_PATH, index=False)

    if closed_rows:
        table = Table(title="Newly Closed Trades", show_lines=True)
        table.add_column("Market", max_width=50)
        for q in closed_rows:
            table.add_row(str(q)[:48])
        console.print(table)
        console.print()

    console.print(f"[bold]Open checked: {open_count}[/bold]")
    console.print(f"[green]Newly closed: {len(closed_rows)}[/green]")
    console.print(f"[yellow]Still open: {len(still_open_rows)}[/yellow]")
    console.print(f"[dim]Skipped (no slug): {len(skipped_rows)}[/dim]")
    console.print(f"[dim]Non-open rows untouched: {non_open_count}[/dim]")
    console.print(f"\n[dim]Saved → {PAPER_TRADES_PATH}[/dim]\n")


if __name__ == "__main__":
    main()