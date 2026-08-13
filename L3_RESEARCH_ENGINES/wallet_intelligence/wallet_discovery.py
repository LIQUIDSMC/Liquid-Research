"""
Liquid Research — Wallet Discovery (Phase 3 Infrastructure)

Systematically sources candidate wallets by working BACKWARD from
relevant markets, not forward from a leaderboard.

Pipeline:
load market snapshot -> classify markets -> keep Active Research
tier only -> sample trades per market -> extract proxyWallet
addresses -> collapse to one row per wallet

NO PERFORMANCE FILTERING. This module has no concept of winning
or losing. A wallet appears here purely because it traded a
relevant market — never because it was profitable. Performance
evaluation happens later, in wallet_analyzer.py, never here.

Confirmed API parameter (verified via live testing + official docs):
    GET https://data-api.polymarket.com/trades?market={conditionId}&limit={n}
The 'market' parameter expects the conditionId HASH, not the slug.

No wallet connection. No private key. No execution. Read-only.

Usage:
    python3 analyzers/wallet_discovery.py
"""

import requests
import pandas as pd
from rich.console import Console
from rich.table import Table
import os
import sys
import glob

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "L2_DOMAINS", "prediction_markets", "classification"))
from market_classifier import classify_market

console = Console()

DATA_API_TRADES = "https://data-api.polymarket.com/trades"
MARKETS_SNAPSHOT_DIR = "L2_DOMAINS/prediction_markets/data/markets"
OUTPUT_PATH = "L3_RESEARCH_ENGINES/wallet_intelligence/data/candidate_wallets.csv"

TRADES_PER_MARKET = 50  # sample size per market, kept small and deliberate


# ── Function 1 ─────────────────────────────────────────────────────────────

def load_latest_market_snapshot() -> pd.DataFrame:
    """
    Find and load the most recent market snapshot CSV from
    data/markets/.

    Receives:
        Nothing — reads from the filesystem directly.

    Returns:
        pandas.DataFrame: the most recent snapshot, or an empty
                            DataFrame with a console warning if
                            none exists.
    """
    pattern = os.path.join(MARKETS_SNAPSHOT_DIR, "snapshot_*.csv")
    snapshot_files = sorted(glob.glob(pattern))

    if not snapshot_files:
        console.print(
            f"[red]No market snapshots found in {MARKETS_SNAPSHOT_DIR}/. "
            f"Run collectors/market_collector.py first.[/red]"
        )
        return pd.DataFrame()

    latest_file = snapshot_files[-1]
    console.print(f"Snapshot: {latest_file}")
    return pd.read_csv(latest_file)


# ── Function 2 ─────────────────────────────────────────────────────────────

def classify_snapshot_markets(markets_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run every market in the snapshot through market_classifier.py's
    classify_market(). Reuses existing, already-tested logic —
    no new classification rules are written here.

    Receives:
        markets_df (pd.DataFrame): raw market snapshot

    Returns:
        pd.DataFrame: same markets, with classifier columns added
    """
    if markets_df.empty:
        return markets_df

    classified_rows = []
    for _, row in markets_df.iterrows():
        market_input = {
            "title": row.get("question", "Unknown"),
            "slug": "",  # snapshot CSV does not currently save slug;
                         # classification relies on title-only matching
                         # for these markets. Ultra-short detection via
                         # slug pattern will not trigger here, but
                         # keyword-based category matching still works.
            "days_left": row.get("days_left"),
        }
        classification = classify_market(market_input)
        combined = {**row.to_dict(), **classification}
        classified_rows.append(combined)

    return pd.DataFrame(classified_rows)


# ── Function 3 ─────────────────────────────────────────────────────────────

def filter_active_research_markets(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only markets tagged Active Research tier.

    Receives:
        classified_df (pd.DataFrame): output of classify_snapshot_markets()

    Returns:
        pd.DataFrame: filtered to category_tier == "Active Research"
    """
    if classified_df.empty or "category_tier" not in classified_df.columns:
        return pd.DataFrame()

    return classified_df[classified_df["category_tier"] == "Active Research"].reset_index(drop=True)


# ── Function 4 ─────────────────────────────────────────────────────────────

def fetch_trades_for_market(condition_id: str, limit: int = TRADES_PER_MARKET) -> list[dict]:
    """
    Pull a sample of trades for ONE specific market, using the
    CONFIRMED working parameter: market={conditionId}.

    Receives:
        condition_id (str): the market's condition ID (the 0x... hash)
        limit (int): max trades to pull for this market

    Returns:
        list[dict]: raw trade records, or an empty list on failure
    """
    if not condition_id:
        return []

    params = {"market": condition_id, "limit": limit}
    try:
        response = requests.get(DATA_API_TRADES, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error while fetching trades for market: {e}[/red]")
        return []


# ── Function 5 ─────────────────────────────────────────────────────────────

def extract_wallets_from_trades(trades: list[dict], market_title: str, category: str,
                                 condition_id: str) -> dict:
    """
    Pull every proxyWallet out of one market's trade batch.

    Receives:
        trades (list[dict]): trades for one market
        market_title (str): that market's title
        category (str): that market's classified category
        condition_id (str): that market's conditionId — needed so
            downstream wallet analysis can later pull THIS wallet's
            trades from THIS specific market (Mode 2, future patch)

    Returns:
        dict: keyed by wallet_address, each value containing
              market_title, category, condition_id, and trade_count
              for THIS batch
    """
    wallets = {}
    for trade in trades:
        wallet = trade.get("proxyWallet")
        if not wallet:
            continue

        if wallet not in wallets:
            wallets[wallet] = {
                "market_title": market_title,
                "category": category,
                "condition_id": condition_id,
                "trade_count": 0,
            }
        wallets[wallet]["trade_count"] += 1

    return wallets



# ── Function 6 ─────────────────────────────────────────────────────────────

def collapse_wallet_discoveries(all_discoveries: list[dict]) -> dict:
    """
    Merge per-market discovery results into ONE row per unique
    wallet, accumulating categories_touched, markets_touched,
    sample_trade_count, AND discovered_condition_ids across every
    market that wallet appeared in.

    Receives:
        all_discoveries (list[dict]): a list of per-market discovery
            dicts, each in the shape returned by
            extract_wallets_from_trades()

    Returns:
        dict: keyed by wallet_address, with combined stats
    """
    collapsed = {}

    for market_discovery in all_discoveries:
        for wallet, info in market_discovery.items():
            if wallet not in collapsed:
                collapsed[wallet] = {
                    "wallet_address": wallet,
                    "categories_touched": set(),
                    "discovered_condition_ids": set(),
                    "markets_touched": 0,
                    "sample_trade_count": 0,
                    "first_discovered_market": info["market_title"],
                    "first_discovered_category": info["category"],
                }

            collapsed[wallet]["categories_touched"].add(info["category"])
            collapsed[wallet]["discovered_condition_ids"].add(info["condition_id"])
            collapsed[wallet]["markets_touched"] += 1
            collapsed[wallet]["sample_trade_count"] += info["trade_count"]

    return collapsed



# ── Function 7 ─────────────────────────────────────────────────────────────

def run_wallet_discovery(trades_per_market: int = TRADES_PER_MARKET) -> tuple[pd.DataFrame, dict]:
    """
    Orchestrator. Runs the full discovery pipeline.

    Receives:
        trades_per_market (int): trade sample size per market

    Returns:
        tuple(pd.DataFrame, dict): the final candidate wallet table,
            plus a stats dict for the diagnostic summary
    """
    raw_markets = load_latest_market_snapshot()
    if raw_markets.empty:
        return pd.DataFrame(), {}

    classified = classify_snapshot_markets(raw_markets)
    active_research_markets = filter_active_research_markets(classified)

    if active_research_markets.empty:
        console.print("[yellow]No Active Research tier markets found in snapshot.[/yellow]")
        return pd.DataFrame(), {}

    console.print(f"Active Research tier markets found: {len(active_research_markets)}\n")
    console.print("Sampling trades from each Active Research market...")

    all_discoveries = []
    total_trades_sampled = 0

    for i, row in active_research_markets.iterrows():
        condition_id = str(row.get("market_id", ""))
        title = row.get("question", row.get("market_title", "Unknown"))
        category = row.get("category", "Unknown")

        trades = fetch_trades_for_market(condition_id, limit=trades_per_market)
        total_trades_sampled += len(trades)

        market_wallets = extract_wallets_from_trades(trades, title, category, condition_id)
        all_discoveries.append(market_wallets)

        title_short = title[:50] + ("..." if len(title) > 50 else "")
        console.print(f"  [{i+1}/{len(active_research_markets)}] {title_short}  →  {len(market_wallets)} wallets found")

    collapsed = collapse_wallet_discoveries(all_discoveries)

    final_rows = []
    for wallet, info in collapsed.items():
        final_rows.append({
            "wallet_address": info["wallet_address"],
            "categories_touched": ", ".join(sorted(info["categories_touched"])),
            "discovered_condition_ids": "|".join(sorted(info["discovered_condition_ids"])),
            "markets_touched": info["markets_touched"],
            "sample_trade_count": info["sample_trade_count"],
            "first_discovered_market": info["first_discovered_market"],
            "first_discovered_category": info["first_discovered_category"],
        })

    result_df = pd.DataFrame(final_rows)
    if not result_df.empty:
        result_df = result_df.sort_values(by="sample_trade_count", ascending=False).reset_index(drop=True)

    stats = {
        "markets_sampled": len(active_research_markets),
        "total_trades_sampled": total_trades_sampled,
        "unique_wallets": len(collapsed),
    }

    return result_df, stats


# ── Diagnostic Summary ────────────────────────────────────────────────────────

def print_discovery_summary(result_df: pd.DataFrame, stats: dict) -> None:
    """
    Print the diagnostic summary: markets sampled, total trades
    sampled, unique wallets, average wallets per market, and top 10
    wallets by sample_trade_count. NO performance data anywhere.
    """
    console.print("\n[bold cyan]═══ Discovery Summary ═══[/bold cyan]")
    console.print(f"Markets sampled:              {stats.get('markets_sampled', 0)}")
    console.print(f"Total trades sampled:          {stats.get('total_trades_sampled', 0)}")
    console.print(f"Unique wallets discovered:     {stats.get('unique_wallets', 0)}")

    markets_sampled = stats.get("markets_sampled", 0)
    if markets_sampled > 0:
        avg_wallets = stats.get("unique_wallets", 0) / markets_sampled
        console.print(f"Average wallets per market:    {avg_wallets:.1f}")

    if result_df.empty:
        console.print("\n[yellow]No candidate wallets discovered.[/yellow]\n")
        return

    console.print("\n[bold]Top 10 Wallets by Sample Trade Count[/bold]")
    table = Table(show_lines=True)
    table.add_column("Wallet Address", max_width=44)
    table.add_column("Categories Touched", max_width=30)
    table.add_column("Markets", justify="right")
    table.add_column("ConditionIds", justify="right")
    table.add_column("Trades", justify="right")

    for _, row in result_df.head(10).iterrows():
        condition_id_count = len(row["discovered_condition_ids"].split("|")) if row["discovered_condition_ids"] else 0
        table.add_row(
            row["wallet_address"],
            row["categories_touched"],
            str(row["markets_touched"]),
            str(condition_id_count),
            str(row["sample_trade_count"]),
        )

    console.print(table)

    console.print(
        "\n[dim]No performance filtering applied. Winning and losing "
        "wallets are equally represented in this list.[/dim]"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    console.print("\n[bold cyan]Liquid Research — Wallet Discovery[/bold cyan]")
    console.print("[dim]Sourcing candidate wallets from Active Research category markets...[/dim]\n")

    result_df, stats = run_wallet_discovery()

    print_discovery_summary(result_df, stats)

    if not result_df.empty:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        result_df.to_csv(OUTPUT_PATH, index=False)
        console.print(f"\n[dim]Saved → {OUTPUT_PATH}[/dim]\n")


if __name__ == "__main__":
    main()