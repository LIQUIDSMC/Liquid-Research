"""
Liquid Research — Paper Trader (Phase 5)

Creates hypothetical paper trade entries from the scanner's top
ranked markets. Read-only, no wallet, no private key, no
execution, no real money. Mechanical side selection only — NOT a
prediction signal. Fixed $100 position size, no risk sizing.

Joins two existing, already-validated data sources:
  - data/scanner/scanner_run_*.csv (Phase 4 output: tradeability_score)
  - data/markets/snapshot_*.csv (Phase 1 output: yes_price/no_price)
since the scanner run alone does not carry pricing data needed
for mechanical side selection.

Side selection rule (v1): paper-buy whichever side (Yes/No) has
the higher implied probability per the market snapshot's own
price. This is a mechanical bookkeeping rule, not a prediction.

Avoids creating duplicate open paper trades for the same slug on
rerun — if an open trade already exists for a market, it is
skipped, not duplicated.

No mark-to-market. No early exit. No fake P&L. Trades start
status=open and stay that way until paper_resolver.py confirms
real resolution.

Usage:
    python3 simulator/paper_trader.py
"""

import os
import glob
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

SCANNER_DIR = "data/scanner"
MARKETS_DIR = "data/markets"
SIMULATOR_DIR = "data/simulator"
PAPER_TRADES_PATH = os.path.join(SIMULATOR_DIR, "paper_trades.csv")

TOP_N = 5
FIXED_POSITION_SIZE = 100.0


# ── File Loading ──────────────────────────────────────────────────────────────

def find_latest_file(directory: str, pattern: str) -> str:
    """
    Find the most recently created file matching a glob pattern.

    Receives:
        directory (str): folder to search
        pattern (str): glob pattern, e.g. "scanner_run_*.csv"

    Returns:
        str: path to the latest matching file, or None if none exist
    """
    matches = glob.glob(os.path.join(directory, pattern))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def load_existing_paper_trades() -> pd.DataFrame:
    """
    Load existing paper trades if the file exists, otherwise
    return an empty DataFrame with the correct columns.

    Receives:
        Nothing — reads from the filesystem directly.

    Returns:
        pd.DataFrame
    """
    columns = [
        "trade_id", "entry_date", "market_id", "slug", "question", "side",
        "entry_price", "position_size", "tradeability_score_at_entry",
        "entry_reason", "status", "resolution_date", "winning_outcome",
        "trade_won", "trade_pnl", "exit_reason",
    ]

    if os.path.exists(PAPER_TRADES_PATH):
        try:
            return pd.read_csv(PAPER_TRADES_PATH)
        except Exception as e:
            console.print(f"[red]Error reading existing paper trades: {e}[/red]")
            return pd.DataFrame(columns=columns)

    return pd.DataFrame(columns=columns)


# ── Side Selection ────────────────────────────────────────────────────────────

def determine_side(yes_price, no_price) -> tuple:
    """
    Mechanically select a side based on higher implied probability.
    NOT a prediction signal — a bookkeeping rule only.

    Receives:
        yes_price (float or None)
        no_price (float or None)

    Returns:
        tuple: (side: str or None, entry_price: float or None)
               Returns (None, None) if prices are unavailable.
    """
    try:
        yes = float(yes_price)
        no = float(no_price)
    except (TypeError, ValueError):
        return None, None

    if yes != yes or no != no:  # NaN check
        return None, None

    if yes >= no:
        return "Yes", yes
    return "No", no


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print("\n[bold cyan]Liquid Research — Paper Trader (Phase 5)[/bold cyan]")

    scanner_path = find_latest_file(SCANNER_DIR, "scanner_run_*.csv")
    if not scanner_path:
        console.print("[red]No scanner run found in data/scanner/. Run scanner/scanner.py first.[/red]")
        return

    snapshot_path = find_latest_file(MARKETS_DIR, "snapshot_*.csv")
    if not snapshot_path:
        console.print("[red]No market snapshot found in data/markets/.[/red]")
        return

    console.print(f"Scanner run: {scanner_path}")
    console.print(f"Market snapshot: {snapshot_path}\n")

    scanner_df = pd.read_csv(scanner_path)
    snapshot_df = pd.read_csv(snapshot_path)

    # Only consider markets that passed the scanner (not killed) and have a real score
    passed_df = scanner_df[scanner_df["killed"] == False].copy()
    passed_df = passed_df.sort_values("tradeability_score", ascending=False)
    top_n_df = passed_df.head(TOP_N)

    if top_n_df.empty:
        console.print("[yellow]No passed markets available in the latest scanner run.[/yellow]")
        return

    # Join with snapshot to get pricing + slug
    merged_df = top_n_df.merge(
        snapshot_df[["market_id", "slug", "yes_price", "no_price"]],
        on="market_id", how="left", suffixes=("", "_snapshot"),
    )

    existing_trades = load_existing_paper_trades()
    existing_open_slugs = set(
        existing_trades[existing_trades["status"] == "open"]["slug"].dropna()
    )

    new_trades = []
    skipped = []
    next_id = len(existing_trades) + 1

    for _, row in merged_df.iterrows():
        slug = row.get("slug")

        if pd.isna(slug) or slug == "":
            skipped.append((row.get("question", "Unknown"), "missing slug from snapshot join"))
            continue

        if slug in existing_open_slugs:
            skipped.append((row.get("question", "Unknown"), "already has an open paper trade"))
            continue

        side, entry_price = determine_side(row.get("yes_price"), row.get("no_price"))

        if side is None:
            skipped.append((row.get("question", "Unknown"), "missing/invalid price data"))
            continue

        new_trades.append({
            "trade_id": next_id,
            "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "market_id": row.get("market_id"),
            "slug": slug,
            "question": row.get("question"),
            "side": side,
            "entry_price": entry_price,
            "position_size": FIXED_POSITION_SIZE,
            "tradeability_score_at_entry": row.get("tradeability_score"),
            "entry_reason": f"Top {TOP_N} tradeability_score from {os.path.basename(scanner_path)}",
            "status": "open",
            "resolution_date": None,
            "winning_outcome": None,
            "trade_won": None,
            "trade_pnl": None,
            "exit_reason": None,
        })
        next_id += 1

    if not new_trades:
        console.print("[yellow]No new paper trades created (all candidates skipped or duplicated).[/yellow]")
    else:
        new_trades_df = pd.DataFrame(new_trades)
        updated_df = pd.concat([existing_trades, new_trades_df], ignore_index=True)

        os.makedirs(SIMULATOR_DIR, exist_ok=True)
        updated_df.to_csv(PAPER_TRADES_PATH, index=False)

        table = Table(title="New Paper Trades Created", show_lines=True)
        table.add_column("ID")
        table.add_column("Market", max_width=40)
        table.add_column("Side")
        table.add_column("Entry Price")
        table.add_column("Size")
        table.add_column("Score")

        for t in new_trades:
            title = str(t["question"])[:38] + ("..." if len(str(t["question"])) > 38 else "")
            table.add_row(
                str(t["trade_id"]), title, t["side"],
                str(t["entry_price"]), f"${t['position_size']:.0f}",
                str(t["tradeability_score_at_entry"]),
            )

        console.print(table)

    if skipped:
        console.print(f"\n[dim]Skipped {len(skipped)} candidate(s):[/dim]")
        for question, reason in skipped:
            console.print(f"  [dim]- {str(question)[:50]}: {reason}[/dim]")

    console.print(f"\n[bold]New trades created: {len(new_trades)} | Skipped: {len(skipped)}[/bold]")
    console.print(f"[dim]Saved → {PAPER_TRADES_PATH}[/dim]\n")


if __name__ == "__main__":
    main()