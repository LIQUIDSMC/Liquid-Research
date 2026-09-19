"""
Liquid Research — Live Resolution Integration Test (Diagnostic)

TEMPORARY/DIAGNOSTIC SCRIPT. Not part of the permanent module
architecture. This verifies that market_resolution.py's functions
work correctly against REAL live Polymarket API data, not just
hardcoded test examples.

Uses fetch_market_by_slug() — the CONFIRMED WORKING lookup method
per official Polymarket documentation (slug is part of the URL
path: /markets/slug/{slug}, not a query parameter).

Does NOT modify wallet_analyzer.py. Does NOT change any permanent
architecture. Pulls a small number of real trades, resolves them
once each, and prints honest results — including the possibility
that all pulled trades turn out to be open/unresolved.

No wallet. No auth. No private key. No execution. Read-only.

Usage:
    python3 L2_DOMAINS/prediction_markets/validation_history/test_live_resolution.py
"""

import requests
import sys
import os
from rich.console import Console
from rich.table import Table

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resolution"))
from market_resolution import (
    determine_winning_outcome,
    evaluate_trade_outcome,
    fetch_market_by_slug,
)

console = Console()

DATA_API_TRADES = "https://data-api.polymarket.com/trades"

# Same seeded wallet used in wallet_analyzer.py's Stage 1 test.
SEEDED_WALLET_ADDRESS = "0xd28a3f0e8d6c3d5c6f0c75b73451fe266d35fc48"
TRADE_LIMIT = 10  # small, deliberate — this is a diagnostic, not a full run


def fetch_sample_trades(wallet_address: str, limit: int = TRADE_LIMIT) -> list:
    """Pull a small number of real trades for one wallet."""
    params = {"user": wallet_address, "limit": limit}
    try:
        response = requests.get(DATA_API_TRADES, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error while fetching trades: {e}[/red]")
        return []


def run_wallet_sample_test():
    """Pull real trades for the seeded wallet and resolve them."""
    console.print("\n[bold cyan]Liquid Research — Live Resolution Integration Test[/bold cyan]")
    console.print("[dim]Verifying market_resolution.py against REAL Polymarket API data...[/dim]\n")

    console.print(f"Pulling {TRADE_LIMIT} real trades for wallet {SEEDED_WALLET_ADDRESS}...")
    raw_trades = fetch_sample_trades(SEEDED_WALLET_ADDRESS, limit=TRADE_LIMIT)

    if not raw_trades:
        console.print("[red]No trades returned. Cannot proceed with this part of the test.[/red]\n")
        return

    console.print(f"[dim]Pulled {len(raw_trades)} real trades. Resolving...[/dim]\n")

    table = Table(show_lines=True)
    table.add_column("Market Title", max_width=30)
    table.add_column("Chosen Outcome", style="cyan")
    table.add_column("Winning Outcome", style="magenta")
    table.add_column("Confidence", style="yellow")
    table.add_column("Trade Won", justify="center")
    table.add_column("P&L", justify="right", style="green")

    confirmed_count = 0
    open_count = 0
    unconfirmed_count = 0
    partial_count = 0

    resolution_cache = {}  # fetch each unique market only once, keyed by slug

    for trade in raw_trades:
        slug = trade.get("slug")
        title = trade.get("title", "Unknown")
        chosen_outcome = trade.get("outcome", "Unknown")

        if slug not in resolution_cache:
            market = fetch_market_by_slug(slug)
            resolution_cache[slug] = determine_winning_outcome(market)

        resolution = resolution_cache[slug]
        confidence = resolution["resolution_confidence"]

        if confidence == "Confirmed":
            confirmed_count += 1
        elif confidence == "Open":
            open_count += 1
        elif confidence == "Unconfirmed":
            unconfirmed_count += 1
        elif confidence == "Partial":
            partial_count += 1

        resolved_trade = evaluate_trade_outcome(trade, resolution)

        title_short = title[:28] + ("..." if len(title) > 28 else "")
        winning_display = resolution["winning_outcome"] or "[dim]None[/dim]"
        won_display = (
            str(resolved_trade["trade_won"])
            if resolved_trade["trade_won"] is not None
            else "[dim]None[/dim]"
        )
        pnl_display = (
            str(resolved_trade["trade_pnl"])
            if resolved_trade["trade_pnl"] is not None
            else "[dim]None[/dim]"
        )

        table.add_row(
            title_short, chosen_outcome, winning_display, confidence,
            won_display, pnl_display,
        )

    console.print(table)

    console.print("\n[bold]── Resolution Confidence Summary (poRussky sample) ──[/bold]")
    console.print(f"  Confirmed (real win/loss known): [green]{confirmed_count}[/green]")
    console.print(f"  Open (not yet resolved):          [yellow]{open_count}[/yellow]")
    console.print(f"  Unconfirmed (unclear data):       [red]{unconfirmed_count}[/red]")
    console.print(f"  Partial (50/50 resolution):       [magenta]{partial_count}[/magenta]")

    console.print()
    if confirmed_count == 0:
        console.print(
            "[bold yellow]Honest result: none of the sampled trades had a "
            "Confirmed resolution.[/bold yellow]"
        )
        console.print(
            "[dim]This wallet trades 5-minute markets that resolve almost "
            "immediately. This may reflect how quickly the Gamma API marks "
            "ultra-short markets as closed, not a flaw in the resolution "
            "logic itself.[/dim]\n"
        )
    else:
        console.print(
            f"[bold green]{confirmed_count} trade(s) successfully resolved "
            f"with real win/loss data from live API.[/bold green]\n"
        )


def test_known_resolved_market():
    """
    Directly test fetch_market_by_slug() and determine_winning_outcome()
    against ONE market we already confirmed resolved cleanly during
    earlier investigation: a recently-closed FIFA World Cup match
    (Czechia vs South Africa), which showed closed=true and a clean
    outcomePrices winner when inspected manually.
    """
    known_slug = "fifwc-cze-rsa-2026-06-18-cze"

    console.print("\n[bold cyan]── Targeted Test: Known Resolved Market ──[/bold cyan]")
    console.print(f"[dim]Fetching slug: {known_slug}[/dim]\n")

    market = fetch_market_by_slug(known_slug)

    if not market:
        console.print("[red]No market data returned. Cannot verify.[/red]\n")
        return

    console.print(f"Market question: {market.get('question', 'Unknown')}")
    console.print(f"Closed: {market.get('closed')}")

    resolution = determine_winning_outcome(market)

    console.print(f"\nResolution result:")
    console.print(f"  is_resolved:            {resolution['is_resolved']}")
    console.print(f"  winning_outcome:        {resolution['winning_outcome']}")
    console.print(f"  resolution_confidence:  {resolution['resolution_confidence']}")

    if resolution["resolution_confidence"] == "Confirmed":
        console.print("\n[bold green]Confirmed state successfully verified against live API.[/bold green]\n")
    else:
        console.print("\n[bold yellow]Expected Confirmed, got something else. Worth investigating.[/bold yellow]\n")


def test_known_dirty_market():
    """
    Directly test fetch_market_by_slug() and determine_winning_outcome()
    against the Biden COVID market — a known archived/dirty data case
    where outcomePrices showed ["0", "0"] despite closed=true. This
    must resolve as Unconfirmed, NEVER forced into Yes or No.
    """
    known_slug = "will-joe-biden-get-coronavirus-before-the-election"

    console.print("\n[bold cyan]── Targeted Test: Known Dirty/Archived Market ──[/bold cyan]")
    console.print(f"[dim]Fetching slug: {known_slug}[/dim]\n")

    market = fetch_market_by_slug(known_slug)

    if not market:
        console.print("[red]No market data returned. Cannot verify.[/red]\n")
        return

    console.print(f"Market question: {market.get('question', 'Unknown')}")
    console.print(f"Closed: {market.get('closed')}")
    console.print(f"Raw outcomePrices: {market.get('outcomePrices')}")

    resolution = determine_winning_outcome(market)

    console.print(f"\nResolution result:")
    console.print(f"  is_resolved:            {resolution['is_resolved']}")
    console.print(f"  winning_outcome:        {resolution['winning_outcome']}")
    console.print(f"  resolution_confidence:  {resolution['resolution_confidence']}")

    if resolution["resolution_confidence"] == "Unconfirmed" and resolution["winning_outcome"] is None:
        console.print(
            "\n[bold green]Correctly refused to guess a winner from dirty "
            "data. Unconfirmed as expected.[/bold green]\n"
        )
    else:
        console.print(
            "\n[bold red]WARNING: Expected Unconfirmed with no winner. "
            "Review logic — this should never force a guess.[/bold red]\n"
        )


if __name__ == "__main__":
    run_wallet_sample_test()
    test_known_resolved_market()
    test_known_dirty_market()
