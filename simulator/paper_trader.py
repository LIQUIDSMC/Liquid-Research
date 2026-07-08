"""
Liquid Research — Paper Trader (Phase 5, Research Improvements)

Creates hypothetical paper trade entries from ALL markets that
passed the scanner's filters — not just the top-ranked ones. This
is a deliberate research design decision: studying only the
highest tradeability_score markets would eliminate score diversity
and make it impossible to ever answer the project's primary
research question ("does higher tradeability_score produce better
outcomes?"). Widening the sample now, narrowing later once
evidence justifies a threshold.

Read-only, no wallet, no private key, no execution, no real money.
Mechanical side selection only — NOT a prediction signal. Fixed
$100 position size, no risk sizing.

Joins two existing, already-validated data sources:
  - data/scanner/scanner_run_*.csv (Phase 4 output: tradeability_score,
    spread_label, liquidity, volume_24h)
  - data/markets/snapshot_*.csv (Phase 1 output: yes_price/no_price,
    days_left)
since the scanner run alone does not carry pricing or timing data
needed for side selection and category classification.

Side selection rule (v1): paper-buy whichever side (Yes/No) has
the higher implied probability per the market snapshot's own
price. This is a mechanical bookkeeping rule, not a prediction.

Category classification reuses analyzers/market_classifier.py
directly — no new classification logic is invented here.

Every new trade records the metadata needed for future category
and score-bucket analysis: category, category_tier, the exact
scanner_run_id it came from, spread_label, liquidity, volume_24h,
and a recurrence_count showing how many times this exact market_id
has appeared in prior paper trades (to detect oversampling of a
small set of persistently liquid markets).

Avoids creating duplicate OPEN paper trades for the same slug on
rerun. A market whose prior trade has already closed is eligible
to be traded again (recurrence_count will reflect this).

No mark-to-market. No early exit. No fake P&L. Trades start
status=open and stay that way until paper_resolver.py confirms
real resolution.

Usage:
    python3 simulator/paper_trader.py
"""

import sys
import os
import glob
import pandas as pd
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzers"))
from market_classifier import classify_market

console = Console()

SCANNER_DIR = "data/scanner"
MARKETS_DIR = "data/markets"
SIMULATOR_DIR = "data/simulator"
PAPER_TRADES_PATH = os.path.join(SIMULATOR_DIR, "paper_trades.csv")

FIXED_POSITION_SIZE = 100.0

OUTPUT_COLUMNS = [
    "trade_id", "entry_date", "market_id", "slug", "question", "side",
    "entry_price", "position_size", "tradeability_score_at_entry",
    "category", "category_tier", "scanner_run_id", "spread_label",
    "liquidity", "volume_24h", "recurrence_count",
    "entry_reason", "status", "resolution_date", "winning_outcome",
    "trade_won", "trade_pnl", "exit_reason",
]


# ── File Loading ──────────────────────────────────────────────────────────────

def find_latest_file(directory: str, pattern: str) -> Optional[str]:
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
    if os.path.exists(PAPER_TRADES_PATH):
        try:
            return pd.read_csv(PAPER_TRADES_PATH)
        except Exception as e:
            console.print(f"[red]Error reading existing paper trades: {e}[/red]")
            return pd.DataFrame(columns=OUTPUT_COLUMNS)

    return pd.DataFrame(columns=OUTPUT_COLUMNS)


# ── Side Selection ────────────────────────────────────────────────────────────

def determine_side(yes_price: Optional[float], no_price: Optional[float]) -> tuple[Optional[str], Optional[float]]:
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


# ── Category Classification ──────────────────────────────────────────────────

def classify_trade_category(question: str, slug: str, days_left: Optional[float]) -> dict:
    """
    Reuses analyzers/market_classifier.py directly. No new
    classification logic is invented in this file.

    Receives:
        question (str)
        slug (str)
        days_left (float or None)

    Returns:
        dict: {"category": str, "category_tier": str or bool}
    """
    market_input = {
        "title": question if question else "Unknown",
        "slug": slug if slug else "",
        "days_left": days_left,
    }
    classification = classify_market(market_input)
    return {
        "category": classification.get("category", "Unknown"),
        "category_tier": classification.get("category_tier", "Unknown"),
    }


# ── Recurrence Tracking ───────────────────────────────────────────────────────

def count_market_recurrence(existing_trades: pd.DataFrame, market_id: str) -> int:
    """
    Count how many times this exact market_id has appeared in
    prior paper trades. Used to detect whether the dataset is
    being dominated by a small set of persistently liquid markets.

    Receives:
        existing_trades (pd.DataFrame)
        market_id (str)

    Returns:
        int: count of prior occurrences (0 if this is the first)
    """
    if existing_trades.empty or "market_id" not in existing_trades.columns:
        return 0
    return int((existing_trades["market_id"] == market_id).sum())


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    console.print("\n[bold cyan]Liquid Research — Paper Trader (Phase 5)[/bold cyan]")
    console.print("[dim]Trading ALL passing scanner markets — score diversity preserved.[/dim]\n")

    scanner_path = find_latest_file(SCANNER_DIR, "scanner_run_*.csv")
    if not scanner_path:
        console.print("[red]No scanner run found in data/scanner/. Run scanner/scanner.py first.[/red]")
        return

    snapshot_path = find_latest_file(MARKETS_DIR, "snapshot_*.csv")
    if not snapshot_path:
        console.print("[red]No market snapshot found in data/markets/.[/red]")
        return

    scanner_run_id = os.path.basename(scanner_path)

    console.print(f"Scanner run: {scanner_path}")
    console.print(f"Market snapshot: {snapshot_path}\n")

    scanner_df = pd.read_csv(scanner_path)
    snapshot_df = pd.read_csv(snapshot_path)

    # ALL passing markets — no Top-N restriction. Score diversity
    # is required to ever answer the project's primary research
    # question (does tradeability_score predict outcomes?).
    passed_df = scanner_df[scanner_df["killed"] == False].copy()
    passed_df = passed_df.sort_values("tradeability_score", ascending=False)

    if passed_df.empty:
        console.print("[yellow]No passed markets available in the latest scanner run.[/yellow]")
        return

    # Join with snapshot to get pricing, slug, and days_left
    # (days_left needed for category classification, same inputs
    # used elsewhere in the project).
    merged_df = passed_df.merge(
        snapshot_df[["market_id", "slug", "yes_price", "no_price", "days_left"]],
        on="market_id", how="left", suffixes=("", "_snapshot"),
    )

    existing_trades = load_existing_paper_trades()
    existing_open_slugs = set(
        existing_trades[existing_trades["status"] == "open"]["slug"].dropna()
    ) if not existing_trades.empty else set()

    new_trades = []
    skipped = []
    next_id = len(existing_trades) + 1

    for _, row in merged_df.iterrows():
        slug = row.get("slug")
        question = row.get("question", "Unknown")

        if pd.isna(slug) or slug == "":
            skipped.append((question, "missing slug from snapshot join"))
            continue

        if slug in existing_open_slugs:
            skipped.append((question, "already has an open paper trade"))
            continue

        side, entry_price = determine_side(row.get("yes_price"), row.get("no_price"))

        if side is None:
            skipped.append((question, "missing/invalid price data"))
            continue

        market_id = row.get("market_id")
        category_info = classify_trade_category(question, slug, row.get("days_left"))
        recurrence_count = count_market_recurrence(existing_trades, market_id)

        new_trades.append({
            "trade_id": next_id,
            "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "market_id": market_id,
            "slug": slug,
            "question": question,
            "side": side,
            "entry_price": entry_price,
            "position_size": FIXED_POSITION_SIZE,
            "tradeability_score_at_entry": row.get("tradeability_score"),
            "category": category_info["category"],
            "category_tier": category_info["category_tier"],
            "scanner_run_id": scanner_run_id,
            "spread_label": row.get("spread_label"),
            "liquidity": row.get("liquidity"),
            "volume_24h": row.get("volume_24h"),
            "recurrence_count": recurrence_count,
            "entry_reason": f"All passing markets from {scanner_run_id}",
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
        table.add_column("Market", max_width=30)
        table.add_column("Side")
        table.add_column("Entry Price")
        table.add_column("Category", max_width=15)
        table.add_column("Score")
        table.add_column("Recur")

        for t in new_trades:
            title = str(t["question"])[:28] + ("..." if len(str(t["question"])) > 28 else "")
            table.add_row(
                str(t["trade_id"]), title, t["side"],
                str(t["entry_price"]), str(t["category"])[:13],
                str(t["tradeability_score_at_entry"]), str(t["recurrence_count"]),
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