"""
Liquid Research — Market Resolution Lookup (Phase 3 Infrastructure)

Determines whether a market has resolved, and if so, which outcome
won, by reading 'outcomes' and 'outcomePrices' from the Gamma API.

This module NEVER guesses a winner. If the data is unclear, it
returns Unconfirmed/Unknown rather than forcing an answer.

Resolution states handled explicitly:
  - Resolved, clean winner       -> winning_outcome set, confidence "Confirmed"
  - Resolved, dirty/archived data -> winning_outcome None, confidence "Unconfirmed"
  - Resolved, 50/50 partial       -> winning_outcome None, confidence "Partial"
  - Not yet resolved (open)       -> is_resolved False, trade_won None

No wallet. No auth. No private key. No execution. Read-only.

Usage (standalone test):
    python3 analyzers/market_resolution.py
"""

import json
import requests
from rich.console import Console
from rich.table import Table

console = Console()

GAMMA_API_MARKETS = "https://gamma-api.polymarket.com/markets"
GAMMA_API_MARKET_BY_SLUG = "https://gamma-api.polymarket.com/markets/slug"


# ── Function 1 ─────────────────────────────────────────────────────────────

def fetch_market_by_slug(slug: str) -> dict:
    """
    Fetch one market's full record from the Gamma API using its slug.

    This is the CONFIRMED WORKING lookup method, per official
    Polymarket documentation: the slug is part of the URL path,
    not a query parameter (e.g. /markets/slug/{slug}, NOT
    /markets?slug={slug}).

    Receives:
        slug (str): the market's URL slug

    Returns:
        dict: the raw market record, or an empty dict on failure
              or if not found
    """
    if not slug:
        return {}

    url = f"{GAMMA_API_MARKET_BY_SLUG}/{slug}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict):
            return result
        return {}
    except requests.RequestException as e:
        console.print(f"[red]API error while fetching market by slug: {e}[/red]")
        return {}


def fetch_market_by_condition_id(condition_id: str) -> dict:
    """
    Fetch one market's full record from the Gamma API using its
    conditionId.

    NOTE: The Gamma API's /markets endpoint does not reliably filter
    by condition_id as a query parameter (confirmed via live testing
    — it silently ignores unrecognized parameters and returns
    unrelated default results rather than an error). This function
    is kept for interface compatibility, but callers should prefer
    fetch_market_by_slug() when a slug is available, since that is
    the confirmed-working lookup method per official documentation.

    Receives:
        condition_id (str): the market's condition ID

    Returns:
        dict: the raw market record, or an empty dict on failure
              or if not found
    """
    params = {"condition_ids": condition_id}
    try:
        response = requests.get(GAMMA_API_MARKETS, params=params, timeout=15)
        response.raise_for_status()
        results = response.json()
        if isinstance(results, list) and len(results) > 0:
            # Defensive check: confirm the returned market actually
            # matches the condition_id we asked for, since this
            # endpoint has been observed returning unrelated markets
            # when given an unrecognized parameter.
            for market in results:
                if market.get("conditionId") == condition_id:
                    return market
        return {}
    except requests.RequestException as e:
        console.print(f"[red]API error while fetching market: {e}[/red]")
        return {}



# ── Helper: Safely Parse outcomes / outcomePrices ────────────────────────────

def _parse_json_field(raw):
    """
    Safely parse a field that may arrive as a JSON-encoded string
    (e.g. '["Yes", "No"]') or already be a list. Returns an empty
    list if parsing fails, rather than raising an error.
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return []


# ── Function 2 ─────────────────────────────────────────────────────────────

def determine_winning_outcome(market: dict) -> dict:
    """
    Determine a market's resolution status and winning outcome,
    using 'closed', 'outcomes', and 'outcomePrices'.

    NEVER guesses. Explicitly handles four states:
      - Not resolved (still open)
      - Resolved with a clean winner
      - Resolved but data is dirty/unclear (e.g. ["0", "0"])
      - Resolved as 50/50 partial (e.g. ["0.5", "0.5"])

    Receives:
        market (dict): must contain 'closed', 'outcomes', 'outcomePrices'

    Returns:
        dict: {
            "condition_id": ...,
            "is_resolved": bool,
            "winning_outcome": str or None,
            "resolution_confidence": "Confirmed" / "Unconfirmed" / "Partial" / "Open"
        }
    """
    condition_id = market.get("conditionId") or market.get("condition_id") or "Unknown"
    is_closed = market.get("closed", False)

    if not is_closed:
        return {
            "condition_id": condition_id,
            "is_resolved": False,
            "winning_outcome": None,
            "resolution_confidence": "Open",
        }

    outcomes = _parse_json_field(market.get("outcomes"))
    outcome_prices_raw = _parse_json_field(market.get("outcomePrices"))

    if not outcomes or not outcome_prices_raw or len(outcomes) != len(outcome_prices_raw):
        return {
            "condition_id": condition_id,
            "is_resolved": True,
            "winning_outcome": None,
            "resolution_confidence": "Unconfirmed",
        }

    try:
        prices = [float(p) for p in outcome_prices_raw]
    except (ValueError, TypeError):
        return {
            "condition_id": condition_id,
            "is_resolved": True,
            "winning_outcome": None,
            "resolution_confidence": "Unconfirmed",
        }

    if all(abs(p - 0.5) < 0.01 for p in prices):
        return {
            "condition_id": condition_id,
            "is_resolved": True,
            "winning_outcome": None,
            "resolution_confidence": "Partial",
        }

    winner_indices = [i for i, p in enumerate(prices) if abs(p - 1.0) < 0.01]

    if len(winner_indices) == 1:
        winning_outcome = outcomes[winner_indices[0]]
        return {
            "condition_id": condition_id,
            "is_resolved": True,
            "winning_outcome": winning_outcome,
            "resolution_confidence": "Confirmed",
        }

    return {
        "condition_id": condition_id,
        "is_resolved": True,
        "winning_outcome": None,
        "resolution_confidence": "Unconfirmed",
    }


# ── Function 3 ─────────────────────────────────────────────────────────────

def evaluate_trade_outcome(trade: dict, market_resolution: dict) -> dict:
    """
    Determine whether a specific trade won or lost, based on the
    market's resolution data.

    NEVER guesses. If the market is open, unconfirmed, or partial,
    trade_won is explicitly None — never forced to True or False.

    Always attaches resolution_confidence and winning_outcome onto
    the returned trade dict, regardless of outcome, so downstream
    code (e.g. wallet_analyzer.py) can break unscored trades down
    by WHY they're unscored (Open vs Unconfirmed vs Partial), not
    just lump them into one unexplained bucket.

    Receives:
        trade (dict): must contain 'outcome', 'price', 'size'
        market_resolution (dict): output of determine_winning_outcome()

    Returns:
        dict: original trade fields plus trade_won, trade_pnl,
              resolution_confidence, and winning_outcome
    """
    enriched_trade = dict(trade)

    confidence = market_resolution.get("resolution_confidence")
    winning_outcome = market_resolution.get("winning_outcome")
    trader_outcome = trade.get("outcome")

    # Always attach these, regardless of which branch we take below.
    enriched_trade["resolution_confidence"] = confidence
    enriched_trade["winning_outcome"] = winning_outcome

    if confidence != "Confirmed" or winning_outcome is None:
        enriched_trade["trade_won"] = None
        enriched_trade["trade_pnl"] = None
        return enriched_trade

    trade_won = (trader_outcome == winning_outcome)
    enriched_trade["trade_won"] = trade_won

    try:
        price = float(trade.get("price", 0))
        size = float(trade.get("size", 0))
    except (ValueError, TypeError):
        enriched_trade["trade_pnl"] = None
        return enriched_trade

    if trade_won:
        enriched_trade["trade_pnl"] = round((1.0 - price) * size, 4)
    else:
        enriched_trade["trade_pnl"] = round(-1 * price * size, 4)

    return enriched_trade




# ── Function 4 ─────────────────────────────────────────────────────────────

def resolve_trades_batch(trades: list) -> list:
    """
    Resolve a batch of trades, caching market resolution lookups so
    the same market is never fetched twice.

    Uses fetch_market_by_slug() as the PRIMARY lookup method, since
    fetch_market_by_condition_id() has been observed to intermittently
    return empty results even for a correct, verified conditionId
    (confirmed via direct testing on 2026-06-19: the same conditionId
    returned a full market via slug lookup but zero results via the
    condition_ids query parameter, repeatedly, across three separate
    attempts). Falls back to conditionId lookup only if a trade has
    no slug field at all.

    Receives:
        trades (list[dict]): trade records. Each should include
                              'slug' (preferred) and/or 'conditionId'
                              (fallback only).

    Returns:
        list[dict]: trades enriched with trade_won, trade_pnl,
                     resolution_confidence, and winning_outcome
    """
    resolution_cache = {}
    resolved_trades = []

    for trade in trades:
        slug = trade.get("slug")
        condition_id = trade.get("conditionId") or trade.get("condition_id")
        cache_key = slug or condition_id

        if cache_key not in resolution_cache:
            if slug:
                market = fetch_market_by_slug(slug)
            else:
                market = fetch_market_by_condition_id(condition_id)
            resolution_cache[cache_key] = determine_winning_outcome(market)

        market_resolution = resolution_cache[cache_key]
        resolved_trade = evaluate_trade_outcome(trade, market_resolution)
        resolved_trades.append(resolved_trade)

    return resolved_trades



# ── Standalone Test Block ────────────────────────────────────────────────────

EXAMPLE_MARKETS = [
    {
        "label": "Clean Yes/No resolved market",
        "market": {
            "conditionId": "0xtest001",
            "closed": True,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["1", "0"]',
        },
        "expected_winner": "Yes",
        "expected_confidence": "Confirmed",
    },
    {
        "label": "Clean non-Yes/No resolved market",
        "market": {
            "conditionId": "0xtest002",
            "closed": True,
            "outcomes": '["Invicta", "Evo Novo"]',
            "outcomePrices": '["1", "0"]',
        },
        "expected_winner": "Invicta",
        "expected_confidence": "Confirmed",
    },
    {
        "label": "Unresolved / open market",
        "market": {
            "conditionId": "0xtest003",
            "closed": False,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.65", "0.35"]',
        },
        "expected_winner": None,
        "expected_confidence": "Open",
    },
    {
        "label": "Dirty archived market (0/0)",
        "market": {
            "conditionId": "0xtest004",
            "closed": True,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0", "0"]',
        },
        "expected_winner": None,
        "expected_confidence": "Unconfirmed",
    },
    {
        "label": "50/50 partial resolution market",
        "market": {
            "conditionId": "0xtest005",
            "closed": True,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.5", "0.5"]',
        },
        "expected_winner": None,
        "expected_confidence": "Partial",
    },
]

EXAMPLE_TRADES = [
    {
        "label": "Winning trade on confirmed market",
        "trade": {"conditionId": "0xtest001", "outcome": "Yes", "price": 0.65, "size": 100},
        "market_resolution_label": "Clean Yes/No resolved market",
        "expected_trade_won": True,
    },
    {
        "label": "Losing trade on confirmed market",
        "trade": {"conditionId": "0xtest001", "outcome": "No", "price": 0.35, "size": 100},
        "market_resolution_label": "Clean Yes/No resolved market",
        "expected_trade_won": False,
    },
    {
        "label": "Trade on open market",
        "trade": {"conditionId": "0xtest003", "outcome": "Yes", "price": 0.65, "size": 100},
        "market_resolution_label": "Unresolved / open market",
        "expected_trade_won": None,
    },
    {
        "label": "Trade on unconfirmed/dirty market",
        "trade": {"conditionId": "0xtest004", "outcome": "Yes", "price": 0.50, "size": 100},
        "market_resolution_label": "Dirty archived market (0/0)",
        "expected_trade_won": None,
    },
    {
        "label": "Trade on 50/50 partial market",
        "trade": {"conditionId": "0xtest005", "outcome": "Yes", "price": 0.50, "size": 100},
        "market_resolution_label": "50/50 partial resolution market",
        "expected_trade_won": None,
    },
]


def run_test():
    """Run the resolution logic against hardcoded example markets and trades."""
    console.print("\n[bold cyan]Liquid Research — Market Resolution Test[/bold cyan]")
    console.print("[dim]Testing resolution logic against hardcoded example markets (no live API calls)...[/dim]\n")

    console.print("[bold]── Part 1: Market Resolution Detection ──[/bold]\n")

    market_table = Table(show_lines=True)
    market_table.add_column("Scenario", max_width=32)
    market_table.add_column("Winner Found", style="cyan")
    market_table.add_column("Confidence", style="yellow")
    market_table.add_column("Pass?", justify="center")

    resolution_lookup = {}

    all_passed = True

    for case in EXAMPLE_MARKETS:
        result = determine_winning_outcome(case["market"])
        resolution_lookup[case["label"]] = result

        winner_correct = result["winning_outcome"] == case["expected_winner"]
        confidence_correct = result["resolution_confidence"] == case["expected_confidence"]
        passed = winner_correct and confidence_correct

        if not passed:
            all_passed = False

        pass_display = "[green]✓[/green]" if passed else "[red]✗ FAIL[/red]"
        winner_display = result["winning_outcome"] if result["winning_outcome"] else "[dim]None[/dim]"

        market_table.add_row(
            case["label"],
            winner_display,
            result["resolution_confidence"],
            pass_display,
        )

    console.print(market_table)

    console.print("\n[bold]── Part 2: Trade Outcome Evaluation ──[/bold]\n")

    trade_table = Table(show_lines=True)
    trade_table.add_column("Scenario", max_width=32)
    trade_table.add_column("Trade Won", style="cyan")
    trade_table.add_column("Trade P&L", style="green")
    trade_table.add_column("Pass?", justify="center")

    for case in EXAMPLE_TRADES:
        market_resolution = resolution_lookup[case["market_resolution_label"]]
        result = evaluate_trade_outcome(case["trade"], market_resolution)

        passed = result["trade_won"] == case["expected_trade_won"]
        if not passed:
            all_passed = False

        pass_display = "[green]✓[/green]" if passed else "[red]✗ FAIL[/red]"
        won_display = str(result["trade_won"]) if result["trade_won"] is not None else "[dim]None[/dim]"
        pnl_display = str(result["trade_pnl"]) if result["trade_pnl"] is not None else "[dim]None[/dim]"

        trade_table.add_row(
            case["label"],
            won_display,
            pnl_display,
            pass_display,
        )

    console.print(trade_table)

    console.print()
    if all_passed:
        console.print("[bold green]All resolution logic tests passed.[/bold green]")
        console.print("[dim]Standalone logic confirmed correct. Live API testing can follow.[/dim]\n")
    else:
        console.print("[bold red]One or more tests FAILED. Review logic before proceeding.[/bold red]\n")


if __name__ == "__main__":
    run_test()
