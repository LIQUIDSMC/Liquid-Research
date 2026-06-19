"""
Liquid Research — Wallet Analyzer (Phase 3, Stage 1)

Proves the wallet research pipeline works end-to-end using ONE
manually seeded wallet address. No leaderboard. No scoring system.
No win rate or P&L calculation yet (requires market resolution
lookup, which is not built in this version).

Pipeline:
wallet address -> pull trades -> classify each trade's market ->
exclude Crypto Ultra-Short and Sports -> flag Other/Unknown as Review
-> summarize wallet stats

No wallet connection. No private key. No execution. Read-only.

Usage:
    python3 analyzers/wallet_analyzer.py
"""

import requests
import pandas as pd
from rich.console import Console
from rich.table import Table
import os
import sys

# Allow importing market_classifier.py from the analyzers folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from market_classifier import classify_market

console = Console()

# ── Config ────────────────────────────────────────────────────────────────────

DATA_API_TRADES = "https://data-api.polymarket.com/trades"

# Manually seeded wallet for Stage 1 testing.
# This is the wallet ('poRussky') seen in our earlier API sanity check.
SEEDED_WALLET_ADDRESS = "0xd28a3f0e8d6c3d5c6f0c75b73451fe266d35fc48"
SEEDED_WALLET_NAME = "poRussky"

TRADE_LIMIT = 50

OUTPUT_PATH = "data/wallets/wallet_test_run.csv"


# ── Function 1 ─────────────────────────────────────────────────────────────

def fetch_wallet_trades(wallet_address: str, limit: int = 50) -> list:
    """
    Pull trade history for one wallet from the public Data API.

    Receives:
        wallet_address (str): the wallet's address
        limit (int): max number of trades to pull

    Returns:
        list[dict]: raw trade records, or an empty list on failure
    """
    params = {"user": wallet_address, "limit": limit}
    try:
        response = requests.get(DATA_API_TRADES, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error while fetching trades: {e}[/red]")
        return []


# ── Function 2 ─────────────────────────────────────────────────────────────

def classify_trade(trade: dict) -> dict:
    """
    Enrich one raw trade with classification data from
    market_classifier.py. Does not modify the classifier itself —
    just reuses it.

    Receives:
        trade (dict): one raw trade record from the Data API

    Returns:
        dict: original trade fields plus category, duration_type,
              include_in_wallet_research, classification_reason
    """
    market_input = {
        "title": trade.get("title", "Unknown"),
        "slug": trade.get("slug", ""),
        # days_left is not available from a trade record in this
        # version — duration classification will rely on the
        # slug-based ultra-short check only. This limitation is
        # documented, not hidden.
        "days_left": None,
    }

    classification = classify_market(market_input)

    enriched_trade = dict(trade)  # copy original trade fields
    enriched_trade.update(classification)
    return enriched_trade


# ── Function 3 ─────────────────────────────────────────────────────────────

def filter_research_eligible_trades(classified_trades: list) -> dict:
    """
    Split classified trades into three explicit buckets.

    IMPORTANT: include_in_wallet_research can be True, False, or
    the string "Review". We NEVER use a bare `if value:` check here,
    because the string "Review" is truthy in Python and would be
    silently treated as True by a careless check. Every comparison
    below is explicit.

    Receives:
        classified_trades (list[dict]): output of classify_trade(),
                                          run across all trades

    Returns:
        dict with three keys: "eligible", "excluded", "review"
    """
    eligible = []
    excluded = []
    review = []

    for trade in classified_trades:
        status = trade.get("include_in_wallet_research")

        if status is True:
            eligible.append(trade)
        elif status is False:
            excluded.append(trade)
        elif status == "Review":
            review.append(trade)
        else:
            # Defensive fallback — should not happen, but if an
            # unexpected value ever appears, treat it as Review
            # rather than silently dropping or including it.
            review.append(trade)

    return {
        "eligible": eligible,
        "excluded": excluded,
        "review": review,
    }


# ── Function 4 ─────────────────────────────────────────────────────────────

def calculate_wallet_stats(wallet_address: str, eligible_trades: list,
                            total_pulled: int, excluded_count: int,
                            review_count: int) -> dict:
    """
    Compute summary statistics for a wallet using ONLY
    research-eligible trades.

    Does NOT calculate win rate or P&L. That requires knowing
    whether each market resolved Yes or No, which is not available
    from a raw trade record. This is a deliberate limitation of
    this version, not an oversight.

    Receives:
        wallet_address (str)
        eligible_trades (list[dict]): only the "eligible" bucket
        total_pulled (int): total trades pulled before filtering
        excluded_count (int): count of excluded trades
        review_count (int): count of review trades

    Returns:
        dict: wallet summary stats
    """
    categories = sorted(set(t.get("category", "Unknown") for t in eligible_trades))

    if eligible_trades:
        sizes = [float(t.get("size", 0)) for t in eligible_trades]
        avg_trade_size = sum(sizes) / len(sizes)
    else:
        avg_trade_size = 0.0

    eligible_count = len(eligible_trades)

    if eligible_count >= 250:
        confidence_tier = "High"
    elif eligible_count >= 100:
        confidence_tier = "Medium"
    elif eligible_count >= 50:
        confidence_tier = "Low-Medium"
    else:
        confidence_tier = "Low"

    return {
        "wallet_address": wallet_address,
        "total_trades_pulled": total_pulled,
        "research_eligible_trades": eligible_count,
        "excluded_trades": excluded_count,
        "review_trades": review_count,
        "categories_traded": ", ".join(categories) if categories else "None",
        "avg_trade_size": round(avg_trade_size, 4),
        "confidence_tier": confidence_tier,
    }


# ── Function 5 ─────────────────────────────────────────────────────────────

def run_wallet_analysis(wallet_address: str, limit: int = TRADE_LIMIT) -> dict:
    """
    Orchestrator. Runs the full pipeline for one wallet.

    Receives:
        wallet_address (str)
        limit (int): max trades to pull

    Returns:
        dict with "wallet_stats" and "classified_trades"
    """
    raw_trades = fetch_wallet_trades(wallet_address, limit=limit)
    classified_trades = [classify_trade(t) for t in raw_trades]
    buckets = filter_research_eligible_trades(classified_trades)

    wallet_stats = calculate_wallet_stats(
        wallet_address=wallet_address,
        eligible_trades=buckets["eligible"],
        total_pulled=len(raw_trades),
        excluded_count=len(buckets["excluded"]),
        review_count=len(buckets["review"]),
    )

    return {
        "wallet_stats": wallet_stats,
        "classified_trades": classified_trades,
    }


# ── Display ───────────────────────────────────────────────────────────────────

def print_trade_table(classified_trades: list, max_rows: int = 15):
    """Print a table of classified trades to the terminal."""
    if not classified_trades:
        console.print("[yellow]No trades to display.[/yellow]")
        return

    table = Table(show_lines=True)
    table.add_column("Market Title", max_width=40)
    table.add_column("Category", style="cyan")
    table.add_column("Include", justify="center")
    table.add_column("Reason", style="dim", max_width=35)

    for trade in classified_trades[:max_rows]:
        status = trade.get("include_in_wallet_research")
        if status is True:
            include_display = "[green]True[/green]"
        elif status is False:
            include_display = "[red]False[/red]"
        else:
            include_display = "[yellow]Review[/yellow]"

        title = trade.get("market_title", "Unknown")
        title_short = title[:38] + ("..." if len(title) > 38 else "")

        table.add_row(
            title_short,
            trade.get("category", "Unknown"),
            include_display,
            trade.get("classification_reason", ""),
        )

    console.print(table)

    if len(classified_trades) > max_rows:
        console.print(f"[dim]...and {len(classified_trades) - max_rows} more trades not shown[/dim]")


def print_wallet_summary(stats: dict, wallet_name: str):
    """Print the final wallet summary block."""
    console.print("\n[bold cyan]═══ Wallet Summary ═══[/bold cyan]")
    console.print(f"Wallet: {stats['wallet_address']} ({wallet_name})")
    console.print(f"Total trades pulled:           {stats['total_trades_pulled']}")
    console.print(f"Research-eligible trades:      [green]{stats['research_eligible_trades']}[/green]")
    console.print(f"Excluded (ultra-short/sports): [red]{stats['excluded_trades']}[/red]")
    console.print(f"Flagged for review:            [yellow]{stats['review_trades']}[/yellow]")
    console.print(f"Categories traded (eligible):  {stats['categories_traded']}")
    console.print(f"Avg trade size (eligible):     {stats['avg_trade_size']}")
    console.print(f"Confidence tier:                {stats['confidence_tier']}")
    console.print(
        "\n[bold yellow]⚠ Note:[/bold yellow] Win rate and P&L not yet calculated.\n"
        "   Requires market resolution lookup — not implemented in this version.\n"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print("\n[bold cyan]Liquid Research — Wallet Analyzer Test (Single Seeded Wallet)[/bold cyan]")
    console.print("[dim]Testing pipeline against one known wallet address...[/dim]\n")
    console.print(f"Wallet: {SEEDED_WALLET_ADDRESS} ({SEEDED_WALLET_NAME})")
    console.print("Fetching trades...\n")

    result = run_wallet_analysis(SEEDED_WALLET_ADDRESS, limit=TRADE_LIMIT)

    print_trade_table(result["classified_trades"])
    print_wallet_summary(result["wallet_stats"], SEEDED_WALLET_NAME)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    stats_df = pd.DataFrame([result["wallet_stats"]])
    stats_df.to_csv(OUTPUT_PATH, index=False)

    console.print(f"[dim]Saved → {OUTPUT_PATH}[/dim]\n")


if __name__ == "__main__":
    main()