"""
Liquid Research — Find Resolved Market (Diagnostic, Phase 3 Validation)

ONE-OFF VALIDATION SCRIPT. Not a permanent feature, not a new
architecture module. This exists to answer one question: among all
markets discovered by wallet_discovery.py, is there at least one
that has actually resolved, and which candidate wallets touched it?

Strategy: search MARKETS first (cheap, ~20 unique conditionIds),
not wallets (684 of them). The first resolved market found tells
us directly which wallets to test next.

Reuses market_resolution.py's existing, already-verified functions.
No new resolution logic is written here.

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
GAMMA_API_MARKETS = "https://gamma-api.polymarket.com/markets"


def load_candidate_wallets() -> pd.DataFrame:
    """Load candidate_wallets.csv, same path used by wallet_analyzer.py."""
    if not os.path.exists(CANDIDATE_WALLETS_PATH):
        console.print(f"[red]No file found at {CANDIDATE_WALLETS_PATH}[/red]")
        return pd.DataFrame()
    return pd.read_csv(CANDIDATE_WALLETS_PATH)


def extract_unique_condition_ids(candidates_df: pd.DataFrame) -> set:
    """Pull every unique conditionId across all wallets' discovered_condition_ids."""
    all_ids = set()
    for raw_ids in candidates_df["discovered_condition_ids"].dropna():
        all_ids.update(raw_ids.split("|"))
    return all_ids


def build_condition_id_to_slug_map(closed_only: bool = False, limit: int = 100) -> dict:
    """
    Pull a batch of markets from the Gamma API and build a
    conditionId -> slug lookup. Reuses the same simple GET pattern
    already proven in market_collector.py and earlier diagnostics.

    Receives:
        closed_only (bool): if True, only request closed markets
        limit (int): how many markets to pull per call

    Returns:
        dict: {conditionId: slug}
    """
    params = {"limit": limit}
    if closed_only:
        params["closed"] = "true"

    try:
        response = requests.get(GAMMA_API_MARKETS, params=params, timeout=15)
        response.raise_for_status()
        markets = response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error fetching markets: {e}[/red]")
        return {}

    return {m.get("conditionId"): m.get("slug") for m in markets if m.get("conditionId")}


def check_market_resolution_status(condition_id: str, slug_map: dict) -> dict:
    """
    Check one conditionId's resolution status, using the already
    -verified fetch_market_by_slug() + determine_winning_outcome()
    pipeline from market_resolution.py.

    Receives:
        condition_id (str)
        slug_map (dict): conditionId -> slug lookup

    Returns:
        dict: {
            "condition_id": ...,
            "slug_found": bool,
            "resolution_confidence": str or None,
            "winning_outcome": str or None,
        }
    """
    slug = slug_map.get(condition_id)

    if not slug:
        return {
            "condition_id": condition_id,
            "slug_found": False,
            "resolution_confidence": None,
            "winning_outcome": None,
        }

    market = fetch_market_by_slug(slug)
    if not market:
        return {
            "condition_id": condition_id,
            "slug_found": True,
            "resolution_confidence": None,
            "winning_outcome": None,
        }

    resolution = determine_winning_outcome(market)
    return {
        "condition_id": condition_id,
        "slug_found": True,
        "resolution_confidence": resolution["resolution_confidence"],
        "winning_outcome": resolution["winning_outcome"],
        "question": market.get("question", "Unknown"),
    }


def find_wallets_for_market(candidates_df: pd.DataFrame, condition_id: str) -> list:
    """
    Find every candidate wallet whose discovered_condition_ids
    contains the given conditionId.

    Receives:
        candidates_df (pd.DataFrame)
        condition_id (str)

    Returns:
        list[dict]: matching wallet rows as dicts
    """
    matches = candidates_df[
        candidates_df["discovered_condition_ids"].str.contains(condition_id, na=False)
    ]
    return matches.to_dict("records")


def main():
    console.print("\n[bold cyan]Liquid Research — Find Resolved Market (Validation Diagnostic)[/bold cyan]")
    console.print("[dim]Searching discovered markets for resolution status...[/dim]\n")

    candidates_df = load_candidate_wallets()
    if candidates_df.empty:
        return

    unique_ids = extract_unique_condition_ids(candidates_df)
    console.print(f"Unique discovered conditionIds: {len(unique_ids)}\n")

    console.print("Building conditionId -> slug map from live Gamma API...")
    console.print("  Pass 1: closed markets...")
    slug_map = build_condition_id_to_slug_map(closed_only=True, limit=100)
    console.print("  Pass 2: all markets (catch any not yet marked closed)...")
    slug_map.update(build_condition_id_to_slug_map(closed_only=False, limit=100))
    console.print(f"  Slug map built: {len(slug_map)} markets total\n")

    console.print("Checking resolution status for each discovered market...\n")

    table = Table(show_lines=True)
    table.add_column("ConditionId", max_width=14)
    table.add_column("Question", max_width=40)
    table.add_column("Confidence", style="yellow")
    table.add_column("Winner", style="magenta")

    resolved_markets = []

    for condition_id in unique_ids:
        result = check_market_resolution_status(condition_id, slug_map)

        confidence_display = result["resolution_confidence"] or "[dim]Not in batch[/dim]"
        winner_display = result.get("winning_outcome") or "[dim]None[/dim]"
        question_display = result.get("question", "")[:38]

        table.add_row(
            condition_id[:12] + "...",
            question_display,
            confidence_display,
            winner_display,
        )

        if result["resolution_confidence"] == "Confirmed":
            resolved_markets.append(result)

    console.print(table)

    console.print(f"\n[bold]═══ Summary ═══[/bold]")
    console.print(f"Total unique discovered markets checked: {len(unique_ids)}")
    console.print(f"Resolved (Confirmed) markets found:      [green]{len(resolved_markets)}[/green]")

    if not resolved_markets:
        console.print(
            "\n[yellow]No resolved markets found among discovered conditionIds "
            "in this batch. This may mean: (a) none have resolved yet, or "
            "(b) they exist but weren't in the 100-market sample pulled "
            "this run. Consider re-running with a larger limit or a fresh "
            "snapshot.[/yellow]\n"
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
                f"{best['wallet_address']}[/bold cyan]"
            )
            console.print(
                "[dim]Chosen because it's the first match — any wallet in "
                "this list is valid, since this market is confirmed "
                "resolved regardless of which wallet we pick.[/dim]\n"
            )


if __name__ == "__main__":
    main()
