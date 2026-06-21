"""
Liquid Research — CLOB Order Book Structure Investigation (Diagnostic)

ONE-OFF INVESTIGATIVE SCRIPT. Resolves a discrepancy found during
clob_recon.py: manually computing spread from the book's first
bid/ask entry (0.98) conflicted with Polymarket's own /spread
endpoint (0.01). This script does NOT assume the book is wrong —
it only proves our interpretation of the book was wrong, and
investigates the actual sort order and structure to find out why.

No wallet. No private key. No order placement. No execution.
Read-only investigation only.

Usage:
    python3 diagnostics/clob_book_structure.py
"""

import requests
import json
from rich.console import Console
from rich.table import Table

console = Console()

GAMMA_API_MARKET_BY_SLUG = "https://gamma-api.polymarket.com/markets/slug"
CLOB_BASE = "https://clob.polymarket.com"

SLUGS_TO_TEST = [
    "will-there-be-no-change-in-fed-interest-rates-after-the-july-2026-meeting",
    "will-ivory-coast-win-the-2026-fifa-world-cup",
]


def fetch_market_by_slug(slug: str) -> dict:
    url = f"{GAMMA_API_MARKET_BY_SLUG}/{slug}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]Error fetching market: {e}[/red]")
        return {}


def parse_clob_token_ids(market: dict) -> list:
    raw = market.get("clobTokenIds")
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def print_levels(label: str, levels: list, max_rows: int = 20):
    """Print up to max_rows of bid/ask levels in their RAW order,
    exactly as returned by the API — no re-sorting applied here,
    since the sort order itself is one of the things we're testing."""
    table = Table(title=label, show_lines=False)
    table.add_column("Index", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Size", justify="right")

    for i, level in enumerate(levels[:max_rows]):
        table.add_row(str(i), level.get("price", "?"), level.get("size", "?"))

    console.print(table)


def check_sort_order(levels: list, label: str) -> str:
    """Determine whether a list of price levels is sorted
    ascending, descending, or neither, based on actual values."""
    if len(levels) < 2:
        return "Not enough data"

    try:
        prices = [float(lvl["price"]) for lvl in levels]
    except (KeyError, ValueError):
        return "Could not parse prices"

    is_ascending = all(prices[i] <= prices[i + 1] for i in range(len(prices) - 1))
    is_descending = all(prices[i] >= prices[i + 1] for i in range(len(prices) - 1))

    if is_ascending:
        return "ASCENDING (low to high)"
    elif is_descending:
        return "DESCENDING (high to low)"
    else:
        return "NEITHER — not consistently sorted"


def investigate_one_market(slug: str) -> dict:
    """Run the full investigation for one slug, return a result dict
    instead of printing a standalone findings block — printing the
    cross-market comparison is handled once, at the end, in main()."""
    console.print(f"\n[bold cyan]── {slug} ──[/bold cyan]")

    market = fetch_market_by_slug(slug)
    if not market:
        console.print("[red]Could not fetch market.[/red]")
        return None

    question = market.get("question", "Unknown")
    closed = market.get("closed")
    neg_risk = market.get("negRisk")
    console.print(f"Question: {question}")
    console.print(f"Closed: {closed} | negRisk: {neg_risk}")

    token_ids = parse_clob_token_ids(market)
    if not token_ids:
        console.print("[red]No token IDs found.[/red]")
        return None

    outcomes_raw = market.get("outcomes")
    try:
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else (outcomes_raw or [])
    except (json.JSONDecodeError, TypeError):
        outcomes = []

    token_id = token_ids[0]
    outcome_label = outcomes[0] if outcomes else "Unknown"
    console.print(f"Testing token for outcome '{outcome_label}': {token_id[:20]}...\n")

    book_response = requests.get(f"{CLOB_BASE}/book", params={"token_id": token_id}, timeout=10)
    book = book_response.json()
    raw_bids = book.get("bids", [])
    raw_asks = book.get("asks", [])

    console.print(f"Total bids: {len(raw_bids)} | Total asks: {len(raw_asks)}")

    bid_sort = check_sort_order(raw_bids, "bids")
    ask_sort = check_sort_order(raw_asks, "asks")
    console.print(f"Bid sort order: {bid_sort}")
    console.print(f"Ask sort order: {ask_sort}")

    try:
        bid_prices = [float(b["price"]) for b in raw_bids]
        ask_prices = [float(a["price"]) for a in raw_asks]
        actual_best_bid = max(bid_prices) if bid_prices else None
        actual_best_ask = min(ask_prices) if ask_prices else None
    except (KeyError, ValueError):
        actual_best_bid = None
        actual_best_ask = None

    derived_spread = None
    derived_midpoint = None
    if actual_best_bid is not None and actual_best_ask is not None:
        derived_spread = round(actual_best_ask - actual_best_bid, 4)
        derived_midpoint = round((actual_best_ask + actual_best_bid) / 2, 4)

    console.print(f"Actual best bid (max of bids): {actual_best_bid}")
    console.print(f"Actual best ask (min of asks): {actual_best_ask}")
    console.print(f"Derived spread: {derived_spread} | Derived midpoint: {derived_midpoint}")

    price_sell = requests.get(f"{CLOB_BASE}/price", params={"token_id": token_id, "side": "SELL"}, timeout=10).json()
    price_buy = requests.get(f"{CLOB_BASE}/price", params={"token_id": token_id, "side": "BUY"}, timeout=10).json()
    midpoint_resp = requests.get(f"{CLOB_BASE}/midpoint", params={"token_id": token_id}, timeout=10).json()
    spread_resp = requests.get(f"{CLOB_BASE}/spread", params={"token_id": token_id}, timeout=10).json()

    console.print(f"/price side=SELL: {price_sell}")
    console.print(f"/price side=BUY:  {price_buy}")
    console.print(f"/midpoint: {midpoint_resp}")
    console.print(f"/spread: {spread_resp}")

    def matches(api_val, derived_val):
        try:
            return abs(float(api_val) - float(derived_val)) < 0.001
        except (TypeError, ValueError):
            return None

    sell_matches_ask = matches(price_sell.get("price"), actual_best_ask)
    buy_matches_bid = matches(price_buy.get("price"), actual_best_bid)
    spread_matches = matches(spread_resp.get("spread"), derived_spread)
    midpoint_matches = matches(midpoint_resp.get("mid"), derived_midpoint)

    console.print(f"\nside=SELL matches best ask: {sell_matches_ask}")
    console.print(f"side=BUY matches best bid: {buy_matches_bid}")
    console.print(f"/spread matches derived spread: {spread_matches}")
    console.print(f"/midpoint matches derived midpoint: {midpoint_matches}")

    return {
        "slug": slug, "question": question, "closed": closed, "negRisk": neg_risk,
        "outcome_tested": outcome_label, "bid_sort": bid_sort, "ask_sort": ask_sort,
        "best_bid": actual_best_bid, "best_ask": actual_best_ask,
        "derived_spread": derived_spread, "derived_midpoint": derived_midpoint,
        "sell_matches_ask": sell_matches_ask, "buy_matches_bid": buy_matches_bid,
        "spread_matches": spread_matches, "midpoint_matches": midpoint_matches,
    }



def main():
    console.print("\n[bold cyan]Liquid Research — CLOB Order Book Structure Investigation (Multi-Market)[/bold cyan]")

    results = []
    for slug in SLUGS_TO_TEST:
        result = investigate_one_market(slug)
        if result:
            results.append(result)

    console.print("\n[bold cyan]═══ Cross-Market Comparison Summary ═══[/bold cyan]\n")

    table = Table(show_lines=True)
    table.add_column("Market", max_width=25)
    table.add_column("negRisk")
    table.add_column("Bid Sort", max_width=12)
    table.add_column("Ask Sort", max_width=12)
    table.add_column("SELL=Ask?")
    table.add_column("BUY=Bid?")
    table.add_column("Spread Match?")
    table.add_column("Midpoint Match?")

    for r in results:
        table.add_row(
            r["question"][:23], str(r["negRisk"]), r["bid_sort"][:10], r["ask_sort"][:10],
            str(r["sell_matches_ask"]), str(r["buy_matches_bid"]),
            str(r["spread_matches"]), str(r["midpoint_matches"]),
        )


    console.print(table)

    all_consistent = all(
        r["bid_sort"] == results[0]["bid_sort"] and r["ask_sort"] == results[0]["ask_sort"]
        for r in results
    )
    console.print(f"\n[bold]Sort order consistent across all tested markets:[/bold] {all_consistent}")


if __name__ == "__main__":
    main()
