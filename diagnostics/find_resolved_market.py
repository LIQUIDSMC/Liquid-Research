"""
Liquid Research — Find Resolved Market (Diagnostic, Phase 3 Validation)

ONE-OFF VALIDATION SCRIPT. Not a permanent feature.

CORRECTED VERSION: the original approach pulled a generic 100-200
market batch from Gamma and hoped our discovered conditionIds
happened to be in it — they never were, since that batch is sorted
by Polymarket's own default ordering, unrelated to our discovery
set. This version instead pulls one real trade per discovered
market directly from the Data API (which reliably includes 'slug'
on every trade record), then resolves via fetch_market_by_slug() —
the same confirmed-reliable method fixed in market_resolution.py.

No wallet connection. No private key. No execution. No scoring.
No rankings. No leaderboard. Read-only.

Usage:
    python3 diagnostics/find_resolved_market.py
"""

import requests
import pandas as pd
from rich.console import Console
from rich.table import Table
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzers"))
from market_resolution import fetch_market_by_slug, determine_winning_outcome

console = Console()

CANDIDATE_WALLETS_PATH = "data/wallets/candidate_wallets.csv"
DATA_API_TRADES = "https://data-api.polymarket.com/trades"


def load_candidate_wallets() -> pd.DataFrame:
    if not os.path.exists(CANDIDATE_WALLETS_PATH):
        console.print(f"[red]No file found at {CANDIDATE_WALLETS_PATH}[/red]")
        return pd.DataFrame()
    return pd.read_csv(CANDIDATE_WALLETS_PATH)


def extract_unique_condition_ids(candidates_df: pd.DataFrame) -> set:
    all_ids = set()
    for raw_ids in candidates_df["discovered_condition_ids"].dropna():
        all_ids.update(raw_ids.split("|"))
    return all_ids


def get_slug_for_condition_id(condition_id: str) -> str:
    """
    Get a market's slug by pulling just one real trade for it
    from the Data API, then reading the slug off that trade.
    Reuses the confirmed-working market= filter.
    """
    params = {"market": condition_id, "limit": 1}
    try:
        response = requests.get(DATA_API_TRADES, params=params, timeout=15)
        response.raise_for_status()
        trades = response.json()
        if trades:
            return trades[0].get("slug")
    except requests.RequestException as e:
        console.print(f"[red]API error fetching trade for {condition_id}: {e}[/red]")
    return None


def find_wallets_for_market(candidates_df: pd.DataFrame, condition_id: str) -> list:
    matches = candidates_df[
        candidates_df["discovered_condition_ids"].str.contains(condition_id, na=False)
    ]
    return matches.to_dict("records")


def main():
    console.print("\n[bold cyan]Liquid Research — Find Resolved Market (Validation Diagnostic)[/bold cyan]")
    console.print("[dim]Searching discovered markets for resolution status (corrected slug lookup)...[/dim]\n")

    candidates_df = load_candidate_wallets()
    if candidates_df.empty:
        return

    unique_ids = extract_unique_condition_ids(candidates_df)
    console.print(f"Unique discovered conditionIds: {len(unique_ids)}\n")
    console.print("Resolving each market via real trade slug + fetch_market_by_slug()...\n")

    table = Table(show_lines=True)
    table.add_column("ConditionId", max_width=14)
    table.add_column("Question", max_width=40)
    table.add_column("Confidence", style="yellow")
    table.add_column("Winner", style="magenta")

    resolved_markets = []

    for condition_id in unique_ids:
        slug = get_slug_for_condition_id(condition_id)

        if not slug:
            table.add_row(condition_id[:12] + "...", "[dim]No trades found[/dim]", "Unknown", "None")
            continue

        market = fetch_market_by_slug(slug)
        if not market:
            table.add_row(condition_id[:12] + "...", "[dim]Slug lookup failed[/dim]", "Unknown", "None")
            continue

        resolution = determine_winning_outcome(market)
        question = market.get("question", "Unknown")[:38]
        confidence = resolution["resolution_confidence"]
        winner = resolution["winning_outcome"] or "[dim]None[/dim]"

        table.add_row(condition_id[:12] + "...", question, confidence, winner)

        if confidence == "Confirmed":
            resolved_markets.append({**resolution, "question": question})

    console.print(table)

    console.print(f"\n[bold]═══ Summary ═══[/bold]")
    console.print(f"Total unique discovered markets checked: {len(unique_ids)}")
    console.print(f"Resolved (Confirmed) markets found:      [green]{len(resolved_markets)}[/green]")

    if not resolved_markets:
        console.print(
            "\n[yellow]No resolved markets found among discovered conditionIds. "
            "All sampled Active Research markets remain genuinely open at "
            "this time.[/yellow]\n"
        )
        return

    console.print(f"\n[bold green]Found {len(resolved_markets)} resolved market(s).[/bold green]\n")

    for market in resolved_markets:
        console.print(f"[bold]Market:[/bold] {market['question']}")
        console.print(f"[bold]Winner:[/bold] {market['winning_outcome']}")
        console.print(f"[bold]ConditionId:[/bold] {market['condition_id']}\n")

        matching_wallets = find_wallets_for_market(candidates_df, market["condition_id"])
        console.print(f"Candidate wallets that touched this market: {len(matching_wallets)}")

        for w in matching_wallets[:5]:
            console.print(
                f"  {w['wallet_address']}  "
                f"(touched {w['markets_touched']} markets, "
                f"{w['sample_trade_count']} sample trades)"
            )

        if matching_wallets:
            best = matching_wallets[0]
            console.print(
                f"\n[bold cyan]Recommended validation candidate: "
                f"{best['wallet_address']}[/bold cyan]\n"
            )


if __name__ == "__main__":
    main()
