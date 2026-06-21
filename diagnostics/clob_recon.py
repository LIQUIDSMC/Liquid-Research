"""
Liquid Research — CLOB API Reconnaissance (Diagnostic, Phase 4 Pre-Work)

ONE-OFF INVESTIGATIVE SCRIPT. Not a permanent feature. Tests
whether the CLOB API provides useful, reliable scanner signals
before any scanner architecture is built.

Both test markets are defined by SLUG, not hardcoded token IDs.
Token IDs are derived live from Gamma at runtime, per the lesson
from Phase 3 (never trust a hardcoded identifier without
re-verifying it fresh).

Markets tested (verified fresh on 2026-06-20):
  High liquidity: Fed rate decision market (~$2.8M volume, active)
  Low liquidity:  Ethereum price market (~$100 lifetime volume, closed)

No wallet. No private key. No order placement. No execution.
Read-only investigation only.

Usage:
    python3 diagnostics/clob_recon.py
"""

import requests
import json
from rich.console import Console

console = Console()

GAMMA_API_MARKET_BY_SLUG = "https://gamma-api.polymarket.com/markets/slug"
CLOB_BASE = "https://clob.polymarket.com"

TEST_MARKETS = [
    {
        "label": "Fed rate decision (high liquidity, active)",
        "slug": "will-there-be-no-change-in-fed-interest-rates-after-the-july-2026-meeting",
    },
    {
        "label": "Ethereum price market (low liquidity, closed)",
        "slug": "ethereum-above-2275-on-april-21-2026-3pm-et",
    },
]


def fetch_market_by_slug(slug: str) -> dict:
    """Same confirmed-reliable lookup method from market_resolution.py."""
    url = f"{GAMMA_API_MARKET_BY_SLUG}/{slug}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]Error fetching market by slug: {e}[/red]")
        return {}


def parse_clob_token_ids(market: dict) -> list:
    """
    Safely parse clobTokenIds, which arrives as a JSON-encoded
    string (same pattern as outcomes/outcomePrices elsewhere in
    this project) or sometimes as None if no tokens were minted.
    """
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


def test_endpoint(url: str, params: dict):
    """Hit one CLOB endpoint, report status, auth behavior, and raw shape."""
    try:
        response = requests.get(url, params=params, timeout=10)
        status = response.status_code

        if status in (401, 403):
            return {"status": status, "auth_required": True, "data": None}

        try:
            data = response.json()
        except Exception:
            data = None

        return {"status": status, "auth_required": False, "data": data}
    except requests.RequestException as e:
        return {"status": None, "auth_required": None, "data": None, "error": str(e)}


def investigate_market(label: str, slug: str):
    console.print(f"\n[bold cyan]── {label} ──[/bold cyan]")
    console.print(f"[dim]Slug: {slug}[/dim]")

    market = fetch_market_by_slug(slug)
    if not market:
        console.print("[red]Could not fetch market from Gamma. Skipping.[/red]")
        return None

    console.print(f"Question: {market.get('question')}")
    console.print(f"Closed: {market.get('closed')}")
    console.print(f"Lifetime volume: {market.get('volume')}")

    token_ids = parse_clob_token_ids(market)
    outcomes_raw = market.get("outcomes")
    try:
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else (outcomes_raw or [])
    except (json.JSONDecodeError, TypeError):
        outcomes = []

    console.print(f"Token IDs found: {len(token_ids)}")

    if not token_ids:
        console.print("[yellow]No clobTokenIds available for this market — cannot test CLOB endpoints.[/yellow]")
        return {"label": label, "token_ids_found": 0, "book": None}

    token_id = token_ids[0]
    outcome_label = outcomes[0] if outcomes else "Unknown"
    console.print(f"[dim]Testing token ID for outcome '{outcome_label}': {token_id[:20]}...[/dim]\n")

    # 1. Order book
    book_result = test_endpoint(f"{CLOB_BASE}/book", {"token_id": token_id})
    console.print(f"[bold]/book[/bold] → status: {book_result['status']}, auth_required: {book_result['auth_required']}")
    if book_result["data"]:
        bids = book_result["data"].get("bids", [])
        asks = book_result["data"].get("asks", [])
        console.print(f"  Bids: {len(bids)}, Asks: {len(asks)}")
        if bids:
            console.print(f"  Top bid: {bids[0]}")
        if asks:
            console.print(f"  Top ask: {asks[0]}")
        console.print(f"  Raw keys present: {list(book_result['data'].keys())}")

    # 2. Best bid (SELL side)
    bid_result = test_endpoint(f"{CLOB_BASE}/price", {"token_id": token_id, "side": "SELL"})
    console.print(f"\n[bold]/price (side=SELL, best bid)[/bold] → status: {bid_result['status']}")
    if bid_result["data"]:
        console.print(f"  Response: {bid_result['data']}")

    # 3. Best ask (BUY side)
    ask_result = test_endpoint(f"{CLOB_BASE}/price", {"token_id": token_id, "side": "BUY"})
    console.print(f"\n[bold]/price (side=BUY, best ask)[/bold] → status: {ask_result['status']}")
    if ask_result["data"]:
        console.print(f"  Response: {ask_result['data']}")

    # 4. Midpoint
    mid_result = test_endpoint(f"{CLOB_BASE}/midpoint", {"token_id": token_id})
    console.print(f"\n[bold]/midpoint[/bold] → status: {mid_result['status']}")
    if mid_result["data"]:
        console.print(f"  Response: {mid_result['data']}")

    # 5. Spread endpoint
    spread_result = test_endpoint(f"{CLOB_BASE}/spread", {"token_id": token_id})
    console.print(f"\n[bold]/spread[/bold] → status: {spread_result['status']}")
    if spread_result["data"]:
        console.print(f"  Response: {spread_result['data']}")

    # Manual spread calc, if possible
    if book_result["data"]:
        bids = book_result["data"].get("bids", [])
        asks = book_result["data"].get("asks", [])
        if bids and asks:
            try:
                top_bid = float(bids[0]["price"])
                top_ask = float(asks[0]["price"])
                console.print(f"\n[bold]Manually calculated spread (ask - bid):[/bold] {round(top_ask - top_bid, 4)}")
            except (KeyError, ValueError, IndexError):
                console.print("\n[yellow]Could not manually calculate spread.[/yellow]")
        else:
            console.print("\n[yellow]Book has no bids/asks — cannot calculate spread.[/yellow]")

    return {
        "label": label, "token_ids_found": len(token_ids),
        "book": book_result, "bid": bid_result, "ask": ask_result,
        "midpoint": mid_result, "spread": spread_result,
    }


def main():
    console.print("\n[bold cyan]Liquid Research — CLOB API Reconnaissance[/bold cyan]")
    console.print("[dim]Token IDs derived live from Gamma — no hardcoded identifiers.[/dim]")

    results = []
    for m in TEST_MARKETS:
        result = investigate_market(m["label"], m["slug"])
        if result:
            results.append(result)

    console.print("\n[bold]═══ Reconnaissance Summary ═══[/bold]\n")
    for r in results:
        if r.get("book"):
            auth_note = "AUTH REQUIRED" if r["book"]["auth_required"] else "public"
            console.print(f"{r['label']}: /book status={r['book']['status']} ({auth_note})")
        else:
            console.print(f"{r['label']}: no token IDs available, untested")


if __name__ == "__main__":
    main()
