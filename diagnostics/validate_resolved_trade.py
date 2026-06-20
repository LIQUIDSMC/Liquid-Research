"""
Liquid Research — Validate Resolved Trade (Diagnostic, Phase 3 Validation)

ONE-OFF VALIDATION SCRIPT. Not a permanent feature, not a new
architecture module. This proves the full classify -> resolve ->
score pipeline produces a correct result on a market we have
already manually confirmed resolved cleanly.

Known-resolved market used:
  Question: Will Czechia win on 2026-06-18?
  ConditionId: 0x825bc4151fd9c139c4f0400c1a6f5d60cf67b2d04f12d69fd9fb5de67b13e4bc
  outcomes: ["Yes", "No"]
  outcomePrices: ["0", "1"]
  Winning outcome: No

Reuses existing, already-verified functions only:
  - classify_trade() pattern from wallet_analyzer.py
  - resolve_trades_batch() from market_resolution.py
No new resolution or classification logic is written here.

No wallet connection. No private key. No execution. No scoring.
No rankings. No leaderboard. Read-only.

Usage:
    python3 diagnostics/validate_resolved_trade.py
"""

import requests
import sys
import os
from rich.console import Console
from rich.table import Table

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzers"))
from market_classifier import classify_market
from market_resolution import resolve_trades_batch

console = Console()

DATA_API_TRADES = "https://data-api.polymarket.com/trades"

KNOWN_RESOLVED_CONDITION_ID = "0x825bc4151fd9c139c4f0400c1a6f5d60cf67b2d04f12d69fd9fb5de67b13e4bc"
KNOWN_RESOLVED_QUESTION = "Will Czechia win on 2026-06-18?"
KNOWN_WINNING_OUTCOME = "No"  # manually confirmed earlier tonight
TRADE_LIMIT = 20


def fetch_trades_for_market(condition_id: str, limit: int = TRADE_LIMIT) -> list:
    """
    Pull real trades for one specific market. Same confirmed
    pattern as wallet_discovery.py's fetch_trades_for_market().

    Receives:
        condition_id (str)
        limit (int)

    Returns:
        list[dict]: raw trade records, or empty list on failure
    """
    params = {"market": condition_id, "limit": limit}
    try:
        response = requests.get(DATA_API_TRADES, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error: {e}[/red]")
        return []


def classify_trade(trade: dict) -> dict:
    """Same classification pattern used throughout wallet_analyzer.py."""
    market_input = {
        "title": trade.get("title", "Unknown"),
        "slug": trade.get("slug", ""),
        "days_left": None,
    }
    classification = classify_market(market_input)
    enriched_trade = dict(trade)
    enriched_trade.update(classification)
    return enriched_trade


def main():
    console.print("\n[bold cyan]Liquid Research — Validate Resolved Trade (Phase 3 Validation)[/bold cyan]")
    console.print(f"[dim]Known-resolved market: {KNOWN_RESOLVED_QUESTION}[/dim]")
    console.print(f"[dim]Confirmed winning outcome: {KNOWN_WINNING_OUTCOME}[/dim]\n")

    console.print(f"Pulling {TRADE_LIMIT} real trades from this market...")
    raw_trades = fetch_trades_for_market(KNOWN_RESOLVED_CONDITION_ID, limit=TRADE_LIMIT)

    if not raw_trades:
        console.print("[red]No trades returned. Cannot validate.[/red]\n")
        return

    console.print(f"[dim]Pulled {len(raw_trades)} real trades. Classifying and resolving...[/dim]\n")

    classified_trades = [classify_trade(t) for t in raw_trades]
    resolved_trades = resolve_trades_batch(classified_trades)

    table = Table(show_lines=True)
    table.add_column("Wallet", max_width=14)
    table.add_column("Side", style="cyan")
    table.add_column("Outcome Chosen", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Confidence", style="yellow")
    table.add_column("Trade Won", justify="center")
    table.add_column("P&L", justify="right", style="green")

    confirmed_count = 0

    for trade in resolved_trades:
        wallet = trade.get("proxyWallet", "Unknown")[:12] + "..."
        side = trade.get("side", "Unknown")
        outcome = trade.get("outcome", "Unknown")
        price = trade.get("price", 0)
        confidence = trade.get("resolution_confidence", "Unknown")
        won = trade.get("trade_won")
        pnl = trade.get("trade_pnl")

        if confidence == "Confirmed":
            confirmed_count += 1

        won_display = str(won) if won is not None else "[dim]None[/dim]"
        pnl_display = str(pnl) if pnl is not None else "[dim]None[/dim]"

        table.add_row(
            wallet, side, outcome, f"{float(price):.3f}",
            confidence, won_display, pnl_display,
        )

    console.print(table)

    console.print(f"\n[bold]═══ Validation Summary ═══[/bold]")
    console.print(f"Total trades checked:    {len(resolved_trades)}")
    console.print(f"Confirmed/scored trades: [green]{confirmed_count}[/green]")

    if confirmed_count == 0:
        console.print("\n[red]VALIDATION FAILED: No trades scored as Confirmed.[/red]\n")
        return

    console.print(f"\n[bold green]VALIDATION SUCCESS: {confirmed_count} trade(s) scored.[/bold green]\n")

    # Manual plain-English verification of the first scored trade
    first_scored = next(t for t in resolved_trades if t.get("resolution_confidence") == "Confirmed")

    wallet = first_scored.get("proxyWallet")
    chosen_outcome = first_scored.get("outcome")
    price = float(first_scored.get("price", 0))
    size = float(first_scored.get("size", 0))
    trade_won = first_scored.get("trade_won")
    trade_pnl = first_scored.get("trade_pnl")

    console.print("[bold]── Manual Verification (Plain English) ──[/bold]\n")
    console.print(
        f"Wallet {wallet} chose \"{chosen_outcome}\" at price {price:.3f} "
        f"for size {size}."
    )
    console.print(f"The market resolved to \"{KNOWN_WINNING_OUTCOME}\".")

    expected_won = (chosen_outcome == KNOWN_WINNING_OUTCOME)
    console.print(
        f"\nExpected result: since the wallet chose \"{chosen_outcome}\" and "
        f"the market resolved \"{KNOWN_WINNING_OUTCOME}\", this trade should "
        f"have {'WON' if expected_won else 'LOST'}."
    )
    console.print(f"Code's actual result: trade_won = {trade_won}, trade_pnl = {trade_pnl}")

    if trade_won == expected_won:
        console.print(
            "\n[bold green]MATCH CONFIRMED: the code's result agrees with "
            "manual plain-English verification.[/bold green]\n"
        )
    else:
        console.print(
            "\n[bold red]MISMATCH: the code's result does NOT match manual "
            "verification. This needs investigation before trusting the "
            "pipeline further.[/bold red]\n"
        )


if __name__ == "__main__":
    main()
