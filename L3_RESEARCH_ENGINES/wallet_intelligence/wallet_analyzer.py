"""
Liquid Research — Wallet Analyzer (Phase 3, Patch B)

Two modes:

MODE 1 — Recent Global Activity
    Pulls a wallet's most recent N trades, regardless of category
    or discovery context. Answers: "what has this wallet done
    lately, in general?"

MODE 2 — Discovered Market Context
    Pulls a wallet's trades ONLY from the specific markets that
    caused it to be discovered during wallet_discovery.py sampling.
    Answers: "how did this wallet perform specifically in the
    Active Research markets that made it a candidate?"

Both modes run the same classify -> filter -> resolve -> summarize
pipeline. Output is always clearly labeled with which mode produced
it, since the two modes answer genuinely different questions and
must never be confused with each other.

NO-PERFORMANCE-FILTERING PHILOSOPHY (unchanged from Stage 1/2):
This module never filters out a wallet for being unprofitable.
Winning and losing wallets are both kept in the dataset.

SCOPE NOTE: Crypto Ultra-Short and Sports trades (excluded), and
Other/Unknown trades (review), are counted and displayed, but are
NOT resolved for win/loss in this version. This is a scope decision
for now, not a permanent judgment.

No wallet connection. No private key. No execution. No scoring.
No rankings. No leaderboard. No dashboard. Read-only.

Usage:
    python3 analyzers/wallet_analyzer.py
"""

import requests
import pandas as pd
from typing import Optional
from rich.console import Console
from rich.table import Table
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "L2_DOMAINS", "prediction_markets", "classification"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "L2_DOMAINS", "prediction_markets", "resolution"))
from market_classifier import classify_market
from market_resolution import resolve_trades_batch

console = Console()

# ── Config ────────────────────────────────────────────────────────────────────

DATA_API_TRADES = "https://data-api.polymarket.com/trades"
CANDIDATE_WALLETS_PATH = "L3_RESEARCH_ENGINES/wallet_intelligence/data/candidate_wallets.csv"
OUTPUT_PATH = "L3_RESEARCH_ENGINES/wallet_intelligence/data/wallet_test_run.csv"

# Mode 1 config (unchanged from Stage 1/2)
SEEDED_WALLET_ADDRESS = "0xca1f9b9d67d947c8007d9814e8f9d6045cccd282"
SEEDED_WALLET_NAME = "KickstandBot"
TRADE_LIMIT = 200

# Mode 2 config — manually selected, per architecture decision to
# avoid automatic selection in this first version
MODE2_WALLET_ADDRESS = "0x1abf0a579401ebf4c44f919755ad20b6ae23f38d"
MODE2_TRADES_PER_MARKET = 50

# Which mode to run. Set to "mode1" or "mode2".
ACTIVE_MODE = "mode2"


# ── Function: Mode 1 trade fetch (unchanged) ─────────────────────────────────

def fetch_wallet_trades(wallet_address: str, limit: int = 50) -> list[dict]:
    """
    Pull a wallet's most recent N trades, regardless of market.
    MODE 1 ONLY.

    Receives:
        wallet_address (str)
        limit (int)

    Returns:
        list[dict]: raw trade records, or empty list on failure
    """
    params = {"user": wallet_address, "limit": limit}
    try:
        response = requests.get(DATA_API_TRADES, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error while fetching trades: {e}[/red]")
        return []


# ── Function: Mode 2 candidate wallet loading ────────────────────────────────

def load_candidate_wallets() -> pd.DataFrame:
    """
    Load data/wallets/candidate_wallets.csv. MODE 2 ONLY.

    Receives:
        Nothing — reads from the filesystem directly.

    Returns:
        pd.DataFrame: the candidate wallet table, or an empty
                       DataFrame with a console warning if the
                       file doesn't exist.
    """
    if not os.path.exists(CANDIDATE_WALLETS_PATH):
        console.print(
            f"[red]No candidate wallet file found at {CANDIDATE_WALLETS_PATH}. "
            f"Run analyzers/wallet_discovery.py first.[/red]"
        )
        return pd.DataFrame()

    return pd.read_csv(CANDIDATE_WALLETS_PATH)


def get_wallet_discovery_info(wallet_address: str) -> dict:
    """
    Find one wallet's row in candidate_wallets.csv and parse its
    discovered_condition_ids back into a list. MODE 2 ONLY.

    Receives:
        wallet_address (str)

    Returns:
        dict: {
            "found": bool,
            "condition_ids": list[str],
            "categories_touched": str,
            "markets_touched": int
        }
    """
    candidates_df = load_candidate_wallets()

    if candidates_df.empty:
        return {"found": False, "condition_ids": [], "categories_touched": "", "markets_touched": 0}

    matching_rows = candidates_df[candidates_df["wallet_address"] == wallet_address]

    if matching_rows.empty:
        return {"found": False, "condition_ids": [], "categories_touched": "", "markets_touched": 0}

    row = matching_rows.iloc[0]
    raw_ids = row.get("discovered_condition_ids", "")
    condition_ids = raw_ids.split("|") if isinstance(raw_ids, str) and raw_ids else []

    return {
        "found": True,
        "condition_ids": condition_ids,
        "categories_touched": row.get("categories_touched", ""),
        "markets_touched": int(row.get("markets_touched", 0)),
    }


# ── Function: Mode 2 trade fetch ─────────────────────────────────────────────

def fetch_wallet_trades_for_markets(wallet_address: str, condition_ids: list[str],
                                     limit_per_market: int = MODE2_TRADES_PER_MARKET) -> list[dict]:
    """
    Pull a wallet's trades ONLY from the specific markets in
    condition_ids, using the CONFIRMED working combined filter:
    ?user={wallet}&market={conditionId}. MODE 2 ONLY.

    Receives:
        wallet_address (str)
        condition_ids (list[str]): markets to pull trades from
        limit_per_market (int)

    Returns:
        list[dict]: combined trades across all given markets
    """
    all_trades = []

    for i, condition_id in enumerate(condition_ids):
        params = {"user": wallet_address, "market": condition_id, "limit": limit_per_market}
        try:
            response = requests.get(DATA_API_TRADES, params=params, timeout=15)
            response.raise_for_status()
            market_trades = response.json()
        except requests.RequestException as e:
            console.print(f"[red]API error fetching market {condition_id}: {e}[/red]")
            market_trades = []

        console.print(f"  [{i+1}/{len(condition_ids)}] {condition_id[:12]}...  →  {len(market_trades)} trades")
        all_trades.extend(market_trades)

    return all_trades


# ── Shared pipeline functions (used by both modes) ───────────────────────────

def classify_trade(trade: dict) -> dict:
    """
    Enrich one raw trade with classification data from
    market_classifier.py. Used by both modes.
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


def filter_research_eligible_trades(classified_trades: list[dict]) -> dict:
    """
    Split classified trades into eligible / excluded / review.
    Used by both modes. NEVER uses a bare `if value:` check on
    include_in_wallet_research, since "Review" is truthy in Python.
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

    return {"eligible": eligible, "excluded": excluded, "review": review}


def calculate_wallet_stats(wallet_address: str, resolved_eligible_trades: list[dict],
                            total_pulled: int, excluded_count: int,
                            review_count: int) -> dict:
    """
    Compute summary statistics using ONLY research-eligible trades.
    Used by both modes. Never filters wallets by performance.
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

    scored_trades = [t for t in resolved_eligible_trades if t.get("trade_won") is not None]
    unscored_trades = [t for t in resolved_eligible_trades if t.get("trade_won") is None]

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
        win_rate = None
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


# ── Orchestrators (one per mode) ──────────────────────────────────────────────

def run_wallet_analysis_mode1(wallet_address: str, limit: int = TRADE_LIMIT) -> dict:
    """
    MODE 1 orchestrator: recent global activity.
    """
    raw_trades = fetch_wallet_trades(wallet_address, limit=limit)
    classified_trades = [classify_trade(t) for t in raw_trades]
    buckets = filter_research_eligible_trades(classified_trades)
    resolved_eligible_trades = resolve_trades_batch(buckets["eligible"])

    wallet_stats = calculate_wallet_stats(
        wallet_address=wallet_address,
        resolved_eligible_trades=resolved_eligible_trades,
        total_pulled=len(raw_trades),
        excluded_count=len(buckets["excluded"]),
        review_count=len(buckets["review"]),
    )
    wallet_stats["analysis_mode"] = "Mode 1: Recent Global Activity"

    return {
        "wallet_stats": wallet_stats,
        "classified_trades": classified_trades,
        "discovery_info": None,
    }


def run_wallet_analysis_mode2(wallet_address: str) -> dict:
    """
    MODE 2 orchestrator: discovered market context.

    Pulls trades ONLY from the markets that caused this wallet to
    be discovered, using the confirmed user+market combined filter.
    """
    discovery_info = get_wallet_discovery_info(wallet_address)

    if not discovery_info["found"]:
        console.print(
            f"[red]Wallet {wallet_address} not found in "
            f"{CANDIDATE_WALLETS_PATH}. Run wallet_discovery.py first, "
            f"or check the address.[/red]"
        )
        return {"wallet_stats": None, "classified_trades": [], "discovery_info": discovery_info}

    condition_ids = discovery_info["condition_ids"]
    console.print(f"Found wallet with {len(condition_ids)} discovered conditionIds.\n")
    console.print("Fetching trades for each discovered market...")

    raw_trades = fetch_wallet_trades_for_markets(wallet_address, condition_ids)

    classified_trades = [classify_trade(t) for t in raw_trades]
    buckets = filter_research_eligible_trades(classified_trades)
    resolved_eligible_trades = resolve_trades_batch(buckets["eligible"])

    wallet_stats = calculate_wallet_stats(
        wallet_address=wallet_address,
        resolved_eligible_trades=resolved_eligible_trades,
        total_pulled=len(raw_trades),
        excluded_count=len(buckets["excluded"]),
        review_count=len(buckets["review"]),
    )
    wallet_stats["analysis_mode"] = "Mode 2: Discovered Market Context"

    return {
        "wallet_stats": wallet_stats,
        "classified_trades": classified_trades,
        "discovery_info": discovery_info,
    }


# ── Display ───────────────────────────────────────────────────────────────────

def print_mode_header(mode: str, wallet_address: str, wallet_name: str = "",
                        discovery_info: Optional[dict] = None) -> None:
    """
    Print an unmissable header stating which mode produced this
    output. Critical for preventing the exact confusion that
    motivated Patch B in the first place.
    """
    console.print("\n[bold cyan]Liquid Research — Wallet Analyzer[/bold cyan]")

    if mode == "mode1":
        console.print("[bold]═══ Mode 1: Recent Global Activity ═══[/bold]")
        console.print(f"Wallet: {wallet_address} ({wallet_name})")
        console.print(
            "[dim]Analyzing the wallet's most recent trades, regardless "
            "of category or discovery context.[/dim]\n"
        )
    else:
        console.print("[bold]═══ Mode 2: Discovered Market Context ═══[/bold]")
        console.print(f"Wallet: {wallet_address}")
        n_markets = discovery_info["markets_touched"] if discovery_info else "?"
        console.print(
            f"[dim]Analyzing trades ONLY from the {n_markets} market(s) that "
            f"caused this wallet to be discovered during Active Research "
            f"sampling. This does NOT include the wallet's other trading "
            f"activity.[/dim]\n"
        )


def print_trade_table(classified_trades: list[dict], max_rows: int = 15) -> None:
    """Print a table of classified trades. Used by both modes."""
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


def print_wallet_summary(stats: dict) -> None:
    """Print the final wallet summary block. Used by both modes."""
    console.print("\n[bold cyan]═══ Wallet Summary ═══[/bold cyan]")
    console.print(f"Wallet: {stats['wallet_address']}")
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
    console.print(f"Analysis mode:                   {stats['analysis_mode']}")

    pending = stats["open_trades"] + stats["unconfirmed_trades"] + stats["partial_trades"] + stats["unscored_other"]
    if pending > 0:
        console.print(
            f"\n[dim]Note: {pending} eligible trade(s) excluded from performance "
            f"calculation (not yet resolved or unclear). This is expected and "
            f"does not indicate an error.[/dim]"
        )
    console.print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if ACTIVE_MODE == "mode1":
        print_mode_header("mode1", SEEDED_WALLET_ADDRESS, SEEDED_WALLET_NAME)
        result = run_wallet_analysis_mode1(SEEDED_WALLET_ADDRESS, limit=TRADE_LIMIT)
    else:
        print_mode_header("mode2", MODE2_WALLET_ADDRESS)
        result = run_wallet_analysis_mode2(MODE2_WALLET_ADDRESS)

    if result["wallet_stats"] is None:
        return

    print_trade_table(result["classified_trades"])
    print_wallet_summary(result["wallet_stats"])

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    stats_df = pd.DataFrame([result["wallet_stats"]])
    stats_df.to_csv(OUTPUT_PATH, index=False)

    console.print(f"[dim]Saved → {OUTPUT_PATH} (analysis_mode = {result['wallet_stats']['analysis_mode']})[/dim]\n")


if __name__ == "__main__":
    main()