"""
Liquid Research — Wallet Analyzer (Phase 3, Stage 2)

Pipeline:
wallet address -> pull trades -> classify each trade's market ->
exclude Crypto Ultra-Short and Sports -> flag Other/Unknown as Review
-> resolve ELIGIBLE trades only -> calculate real win rate and P&L

IMPORTANT — NO-PERFORMANCE-FILTERING PHILOSOPHY:
This module never filters out a wallet for being unprofitable.
Winning and losing wallets are both kept in the dataset. Future
hypothesis testing requires comparing winners against losers, so
no wallet is ever dropped based on its win rate or P&L.

SCOPE NOTE ON EXCLUDED/REVIEW TRADES:
Crypto Ultra-Short and Sports trades (excluded), and Other/Unknown
trades (review), are counted and displayed, but are NOT resolved
for win/loss in this version — resolving them would spend API calls
on data not currently used for research performance stats. This is
a SCOPE DECISION FOR NOW, not a permanent judgment that excluded/
review trades are worthless. A future version may resolve them
separately for wallet BEHAVIOR analysis (e.g. "does this wallet's
ultra-short activity correlate with their long-duration skill?").
That is out of scope here, but the door is intentionally left open.

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

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from market_classifier import classify_market
from market_resolution import resolve_trades_batch

console = Console()

# ── Config ────────────────────────────────────────────────────────────────────

DATA_API_TRADES = "https://data-api.polymarket.com/trades"

# Manually seeded wallet for Stage 1/2 testing.
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
    market_classifier.py.

    Receives:
        trade (dict): one raw trade record from the Data API

    Returns:
        dict: original trade fields plus category, duration_type,
              include_in_wallet_research, classification_reason
    """
    market_input = {
        "title": trade.get("title", "Unknown"),
        "slug": trade.get("slug", ""),
        "days_left": None,
    }

    classification = classify_market(market_input)

    enriched_trade = dict(trade)
    enriched_trade.update(classification)
    return enriched_trade


# ── Function 3 ─────────────────────────────────────────────────────────────

def filter_research_eligible_trades(classified_trades: list) -> dict:
    """
    Split classified trades into three explicit buckets.

    IMPORTANT: include_in_wallet_research can be True, False, or
    the string "Review". We NEVER use a bare `if value:` check here,
    because the string "Review" is truthy in Python and would be
    silently treated as True by a careless check.

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
            review.append(trade)

    return {
        "eligible": eligible,
        "excluded": excluded,
        "review": review,
    }


# ── Function 4 ─────────────────────────────────────────────────────────────

def calculate_wallet_stats(wallet_address: str, resolved_eligible_trades: list,
                            total_pulled: int, excluded_count: int,
                            review_count: int) -> dict:
    """
    Compute summary statistics for a wallet using ONLY
    research-eligible trades, with real win rate and P&L calculated
    from resolved (Confirmed) trades only.

    NO-PERFORMANCE-FILTERING RULE: this function never decides
    whether a wallet is "good enough" to keep. It only describes
    the wallet's stats. A wallet with a 10% win rate is reported
    exactly as faithfully as one with a 90% win rate.

    Receives:
        wallet_address (str)
        resolved_eligible_trades (list[dict]): eligible trades after
            being passed through resolve_trades_batch(). Each trade
            has trade_won (True/False/None) and trade_pnl.
        total_pulled (int): total trades pulled before filtering
        excluded_count (int): count of excluded trades
        review_count (int): count of review trades

    Returns:
        dict: wallet summary stats, including resolution breakdown
              and real performance numbers
    """
    categories = sorted(set(t.get("category", "Unknown") for t in resolved_eligible_trades))

    if resolved_eligible_trades:
        sizes = [float(t.get("size", 0)) for t in resolved_eligible_trades]
        avg_trade_size = sum(sizes) / len(sizes)
    else:
        avg_trade_size = 0.0

    eligible_count = len(resolved_eligible_trades)

    if eligible_count >= 250:
        confidence_tier = "High"
    elif eligible_count >= 100:
        confidence_tier = "Medium"
    elif eligible_count >= 50:
        confidence_tier = "Low-Medium"
    else:
        confidence_tier = "Low"

    # Split eligible trades by resolution outcome. trade_won is
    # True, False, or None (None = not yet scored, for any reason).
    scored_trades = [t for t in resolved_eligible_trades if t.get("trade_won") is not None]
    unscored_trades = [t for t in resolved_eligible_trades if t.get("trade_won") is None]

    # Break down WHY unscored trades are unscored, using the
    # resolution_confidence that resolve_trades_batch() attaches
    # via evaluate_trade_outcome(). Trades that were never resolved
    # (e.g. confidence wasn't "Confirmed") don't carry a confidence
    # field directly on the trade dict in this version, so we infer
    # state from trade_pnl/trade_won being None plus checking if the
    # underlying resolution info is available. For now we count them
    # as a single "unscored" bucket; finer breakdown (Open vs
    # Unconfirmed vs Partial) requires the trade to retain the
    # resolution_confidence value, which we add explicitly below.
    open_count = sum(1 for t in unscored_trades if t.get("resolution_confidence") == "Open")
    unconfirmed_count = sum(1 for t in unscored_trades if t.get("resolution_confidence") == "Unconfirmed")
    partial_count = sum(1 for t in unscored_trades if t.get("resolution_confidence") == "Partial")
    unknown_unscored_count = len(unscored_trades) - open_count - unconfirmed_count - partial_count

    scored_count = len(scored_trades)

    if scored_count > 0:
        wins = sum(1 for t in scored_trades if t.get("trade_won") is True)
        win_rate = round(wins / scored_count, 4)
        losses = scored_count - wins
        total_pnl = round(sum(t.get("trade_pnl", 0) or 0 for t in scored_trades), 4)
    else:
        wins = 0
        losses = 0
        win_rate = None  # never 0% when there's nothing to measure
        total_pnl = 0.0

    return {
        "wallet_address": wallet_address,
        "total_trades_pulled": total_pulled,
        "research_eligible_trades": eligible_count,
        "excluded_trades": excluded_count,
        "review_trades": review_count,
        "categories_traded": ", ".join(categories) if categories else "None",
        "avg_trade_size": round(avg_trade_size, 4),
        "confidence_tier": confidence_tier,
        "scored_trades": scored_count,
        "open_trades": open_count,
        "unconfirmed_trades": unconfirmed_count,
        "partial_trades": partial_count,
        "unscored_other": unknown_unscored_count,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
    }


# ── Function 5 ─────────────────────────────────────────────────────────────

def run_wallet_analysis(wallet_address: str, limit: int = TRADE_LIMIT) -> dict:
    """
    Orchestrator. Runs the full pipeline for one wallet, including
    resolution of eligible trades for real win rate and P&L.

    Receives:
        wallet_address (str)
        limit (int): max trades to pull

    Returns:
        dict with "wallet_stats" and "classified_trades"
    """
    raw_trades = fetch_wallet_trades(wallet_address, limit=limit)
    classified_trades = [classify_trade(t) for t in raw_trades]
    buckets = filter_research_eligible_trades(classified_trades)

    # Only eligible trades get resolved. Excluded and Review trades
    # are counted and shown elsewhere, but not resolved in this
    # version (see module docstring SCOPE NOTE).
    resolved_eligible_trades = resolve_trades_batch(buckets["eligible"])

    wallet_stats = calculate_wallet_stats(
        wallet_address=wallet_address,
        resolved_eligible_trades=resolved_eligible_trades,
        total_pulled=len(raw_trades),
        excluded_count=len(buckets["excluded"]),
        review_count=len(buckets["review"]),
    )

    return {
        "wallet_stats": wallet_stats,
        "classified_trades": classified_trades,
        "resolved_eligible_trades": resolved_eligible_trades,
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
    """Print the final wallet summary block, including real
    resolution breakdown and performance numbers."""
    console.print("\n[bold cyan]═══ Wallet Summary ═══[/bold cyan]")
    console.print(f"Wallet: {stats['wallet_address']} ({wallet_name})")
    console.print(f"Total trades pulled:           {stats['total_trades_pulled']}")
    console.print(f"Research-eligible trades:      [green]{stats['research_eligible_trades']}[/green]")
    console.print(f"Excluded (ultra-short/sports): [red]{stats['excluded_trades']}[/red]")
    console.print(f"Flagged for review:            [yellow]{stats['review_trades']}[/yellow]")
    console.print(f"Categories traded (eligible):  {stats['categories_traded']}")

    console.print("\n[bold]── Resolution Breakdown (eligible trades only) ──[/bold]")
    console.print(f"Confirmed/scored:               [green]{stats['scored_trades']}[/green]")
    console.print(f"Open (not yet resolved):        [yellow]{stats['open_trades']}[/yellow]")
    console.print(f"Unconfirmed (dirty data):       [red]{stats['unconfirmed_trades']}[/red]")
    console.print(f"Partial (50/50):                [magenta]{stats['partial_trades']}[/magenta]")
    if stats["unscored_other"] > 0:
        console.print(f"Unscored (other/unresolved):    [dim]{stats['unscored_other']}[/dim]")

    console.print("\n[bold]── Performance (scored trades only) ──[/bold]")
    if stats["win_rate"] is None:
        console.print("Win rate:                       [dim]None (no scored trades yet)[/dim]")
    else:
        win_pct = stats["win_rate"] * 100
        console.print(
            f"Win rate:                       {win_pct:.1f}%  "
            f"({stats['wins']}W / {stats['losses']}L)"
        )
    console.print(f"Total P&L:                      ${stats['total_pnl']}")
    console.print(f"Avg trade size (eligible):      {stats['avg_trade_size']}")
    console.print(f"Confidence tier:                 {stats['confidence_tier']}")

    pending = stats["open_trades"] + stats["unconfirmed_trades"] + stats["partial_trades"] + stats["unscored_other"]
    if pending > 0:
        console.print(
            f"\n[dim]Note: {pending} eligible trade(s) excluded from performance "
            f"calculation (not yet resolved or unclear). This is expected and "
            f"does not indicate an error.[/dim]"
        )
    console.print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print("\n[bold cyan]Liquid Research — Wallet Analyzer (Stage 2: Real Performance)[/bold cyan]")
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

