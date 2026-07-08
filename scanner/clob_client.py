"""
Liquid Research — CLOB Client (Phase 4, Patch 1)

Reusable wrapper for fetching and correctly interpreting Polymarket
CLOB order book data. This is the lowest-risk first permanent
Phase 4 module, because the behavior has been validated by
diagnostics (diagnostics/clob_recon.py, diagnostics/clob_book_structure.py)
across three structurally different markets before any permanent
code was written.

CRITICAL, PROVEN BEHAVIOR THIS MODULE ENCODES:
Bid lists are sorted ASCENDING (worst to best). Ask lists are
sorted DESCENDING (worst to best). Index 0 in either list is the
WORST price, not the best. This module NEVER reads index 0 as the
best price — it always scans for max(bid) and min(ask) by value.
This is not an assumption; it is a directly tested, reproduced
finding (see research/api_discoveries.md).

This file contains ONLY the reusable client. No filters, no
scoring, no scanner orchestration, no permanent thresholds.

No wallet. No private key. No order placement. No execution.
Read-only.

Usage (standalone test):
    python3 scanner/clob_client.py
"""

import requests
import json
from typing import Optional
from rich.console import Console
from rich.table import Table

console = Console()

GAMMA_API_MARKET_BY_SLUG = "https://gamma-api.polymarket.com/markets/slug"
CLOB_BASE = "https://clob.polymarket.com"

# Request timeouts (seconds). Gamma market lookup and CLOB
# endpoint calls previously used separate inline literals — two
# of the three CLOB-related calls already shared the same value
# (10), now centralized. The market lookup timeout (15) is kept
# separate since it is a different endpoint with potentially
# different latency characteristics.
GAMMA_LOOKUP_TIMEOUT = 15
CLOB_REQUEST_TIMEOUT = 10


# ── Function 1 ─────────────────────────────────────────────────────────────

def fetch_market_by_slug(slug: str) -> dict:
    """
    Fetch one market's full record from Gamma using its slug.
    Same confirmed-reliable method used throughout this project
    since Phase 3 (market_resolution.py).

    Receives:
        slug (str)

    Returns:
        dict: the raw market record, or {} on failure/not found
    """
    if not slug:
        return {}

    url = f"{GAMMA_API_MARKET_BY_SLUG}/{slug}"
    try:
        response = requests.get(url, timeout=GAMMA_LOOKUP_TIMEOUT)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {}
    except requests.RequestException:
        return {}


# ── Function 2 ─────────────────────────────────────────────────────────────

def parse_clob_token_ids(market: dict) -> list[str]:
    """
    Safely parse clobTokenIds, which arrives as a JSON-encoded
    string, an already-parsed list, or None (no tokens minted).

    Receives:
        market (dict)

    Returns:
        list[str]: token IDs, or [] if none/unparseable
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


def parse_outcomes(market: dict) -> list[str]:
    """Safely parse the outcomes field, same JSON-string pattern."""
    raw = market.get("outcomes")
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# ── Function 3 ─────────────────────────────────────────────────────────────

def fetch_order_book(token_id: str) -> dict:
    """
    Fetch the raw order book for one token ID.

    Receives:
        token_id (str)

    Returns:
        dict: {
            "success": bool,
            "bids": list,
            "asks": list,
            "error": str or None
        }
    """
    if not token_id:
        return {"success": False, "bids": [], "asks": [], "error": "No token_id provided"}

    try:
        response = requests.get(f"{CLOB_BASE}/book", params={"token_id": token_id}, timeout=CLOB_REQUEST_TIMEOUT)

        if response.status_code == 404:
            return {"success": False, "bids": [], "asks": [], "error": "No orderbook exists (404)"}

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            return {"success": False, "bids": [], "asks": [], "error": "Malformed response (not a dict)"}

        return {
            "success": True,
            "bids": data.get("bids", []) or [],
            "asks": data.get("asks", []) or [],
            "error": None,
        }
    except requests.exceptions.Timeout:
        return {"success": False, "bids": [], "asks": [], "error": "Request timed out"}
    except requests.RequestException as e:
        return {"success": False, "bids": [], "asks": [], "error": f"Request error: {e}"}
    except (json.JSONDecodeError, ValueError):
        return {"success": False, "bids": [], "asks": [], "error": "Malformed JSON response"}


# ── Function 4 ─────────────────────────────────────────────────────────────

def parse_best_prices(bids: list[dict], asks: list[dict]) -> dict:
    """
    Correctly determine best bid/ask from raw book levels.

    PROVEN BEHAVIOR: bids sort ascending, asks sort descending —
    index 0 is the WORST price on both sides. This function NEVER
    reads position; it scans every entry for the actual max/min
    price by value.

    Receives:
        bids (list[dict]): each {"price": str, "size": str}
        asks (list[dict]): each {"price": str, "size": str}

    Returns:
        dict: {
            "best_bid": float or None,
            "best_ask": float or None,
            "bid_count": int,
            "ask_count": int,
        }
    """
    best_bid = None
    best_ask = None

    try:
        bid_prices = [float(b["price"]) for b in bids if "price" in b]
        best_bid = max(bid_prices) if bid_prices else None
    except (ValueError, TypeError):
        best_bid = None

    try:
        ask_prices = [float(a["price"]) for a in asks if "price" in a]
        best_ask = min(ask_prices) if ask_prices else None
    except (ValueError, TypeError):
        best_ask = None

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "bid_count": len(bids),
        "ask_count": len(asks),
    }


# ── Function 5 ─────────────────────────────────────────────────────────────

def compute_spread_and_midpoint(best_bid: Optional[float], best_ask: Optional[float]) -> dict:
    """
    Compute spread, midpoint, and spread as a percentage of
    midpoint, with safe handling for missing/zero values.

    Receives:
        best_bid (float or None)
        best_ask (float or None)

    Returns:
        dict: {"spread": float or None, "midpoint": float or None,
               "spread_pct": float or None}
    """
    if best_bid is None or best_ask is None:
        return {"spread": None, "midpoint": None, "spread_pct": None}

    spread = round(best_ask - best_bid, 6)
    midpoint = round((best_bid + best_ask) / 2, 6)

    if midpoint is None or midpoint == 0:
        spread_pct = None
    else:
        spread_pct = round((spread / midpoint) * 100, 4)

    return {"spread": spread, "midpoint": midpoint, "spread_pct": spread_pct}


# ── Function 6 ─────────────────────────────────────────────────────────────

def fetch_official_endpoints(token_id: str) -> dict:
    """
    Optionally fetch the official /spread, /midpoint, /price
    (BUY and SELL) endpoints, for cross-checking against the
    manually parsed book.

    Receives:
        token_id (str)

    Returns:
        dict: {
            "official_spread": float or None,
            "official_midpoint": float or None,
            "official_price_buy": float or None,
            "official_price_sell": float or None,
        }
    """
    result = {
        "official_spread": None,
        "official_midpoint": None,
        "official_price_buy": None,
        "official_price_sell": None,
    }

    if not token_id:
        return result

    endpoints = [
        ("official_spread", f"{CLOB_BASE}/spread", {"token_id": token_id}, "spread"),
        ("official_midpoint", f"{CLOB_BASE}/midpoint", {"token_id": token_id}, "mid"),
        ("official_price_buy", f"{CLOB_BASE}/price", {"token_id": token_id, "side": "BUY"}, "price"),
        ("official_price_sell", f"{CLOB_BASE}/price", {"token_id": token_id, "side": "SELL"}, "price"),
    ]

    for key, url, params, field in endpoints:
        try:
            response = requests.get(url, params=params, timeout=CLOB_REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                value = data.get(field)
                result[key] = float(value) if value is not None else None
        except (requests.RequestException, ValueError, TypeError):
            result[key] = None

    return result


# ── Function 7 (Orchestrator) ────────────────────────────────────────────────

def get_market_clob_data(slug: str, outcome_index: int = 0,
                          include_official: bool = True) -> dict:
    """
    Main orchestrator. Given a market slug, fetch and correctly
    parse all CLOB data for one outcome of that market.

    Receives:
        slug (str): market slug
        outcome_index (int): which outcome token to test (default
                              0, typically "Yes")
        include_official (bool): whether to also fetch the
                                  official /spread, /midpoint,
                                  /price endpoints for cross-check

    Returns:
        dict: a complete, clean result containing slug, question,
              closed, negRisk, outcome tested, token_id, bid_count,
              ask_count, best_bid, best_ask, spread, midpoint,
              spread_pct, official_* fields, and status/errors.
    """
    result = {
        "slug": slug,
        "question": None,
        "closed": None,
        "negRisk": None,
        "outcome_tested": None,
        "token_id": None,
        "bid_count": 0,
        "ask_count": 0,
        "best_bid": None,
        "best_ask": None,
        "spread": None,
        "midpoint": None,
        "spread_pct": None,
        "official_spread": None,
        "official_midpoint": None,
        "official_price_buy": None,
        "official_price_sell": None,
        "status": "unknown",
        "error": None,
    }

    market = fetch_market_by_slug(slug)
    if not market:
        result["status"] = "market_not_found"
        result["error"] = "Could not fetch market from Gamma"
        return result

    result["question"] = market.get("question", "Unknown")
    result["closed"] = market.get("closed")
    result["negRisk"] = market.get("negRisk")

    token_ids = parse_clob_token_ids(market)
    if not token_ids:
        result["status"] = "no_token_ids"
        result["error"] = "Market has no clobTokenIds"
        return result

    if outcome_index >= len(token_ids):
        result["status"] = "invalid_outcome_index"
        result["error"] = f"outcome_index {outcome_index} out of range (only {len(token_ids)} tokens)"
        return result

    token_id = token_ids[outcome_index]
    outcomes = parse_outcomes(market)
    result["outcome_tested"] = outcomes[outcome_index] if outcome_index < len(outcomes) else "Unknown"
    result["token_id"] = token_id

    book_result = fetch_order_book(token_id)
    if not book_result["success"]:
        result["status"] = "book_fetch_failed"
        result["error"] = book_result["error"]
        return result

    bids = book_result["bids"]
    asks = book_result["asks"]

    prices = parse_best_prices(bids, asks)
    result.update(prices)

    if prices["best_bid"] is None or prices["best_ask"] is None:
        result["status"] = "incomplete_book"
        result["error"] = "Book exists but missing valid bids and/or asks"
        # Continue anyway — partial data is still returned, not discarded
    else:
        result["status"] = "ok"

    spread_data = compute_spread_and_midpoint(prices["best_bid"], prices["best_ask"])
    result.update(spread_data)

    if include_official:
        official_data = fetch_official_endpoints(token_id)
        result.update(official_data)

    return result


# ── Standalone Test Harness ───────────────────────────────────────────────────

TEST_SLUGS = [
    "will-there-be-no-change-in-fed-interest-rates-after-the-july-2026-meeting",
    "will-ivory-coast-win-the-2026-fifa-world-cup",
    "strait-of-hormuz-traffic-returns-to-normal-by-end-of-june",
]


def main() -> None:
    console.print("\n[bold cyan]Liquid Research — CLOB Client Test Harness[/bold cyan]")
    console.print("[dim]Validating against the three previously confirmed slugs...[/dim]\n")

    table = Table(show_lines=True)
    table.add_column("Market", max_width=22)
    table.add_column("negRisk")
    table.add_column("Bids")
    table.add_column("Asks")
    table.add_column("Best Bid")
    table.add_column("Best Ask")
    table.add_column("Spread")
    table.add_column("Spread %")
    table.add_column("Midpoint")
    table.add_column("Official Match?")
    table.add_column("Status")

    for slug in TEST_SLUGS:
        data = get_market_clob_data(slug)

        def matches(a, b):
            if a is None or b is None:
                return None
            return abs(a - b) < 0.001

        spread_match = matches(data["official_spread"], data["spread"])
        midpoint_match = matches(data["official_midpoint"], data["midpoint"])
        official_match_display = (
            f"spread:{spread_match} mid:{midpoint_match}"
            if data["status"] == "ok" else "N/A"
        )

        question_short = (data["question"] or data["slug"])[:20]

        table.add_row(
            question_short,
            str(data["negRisk"]),
            str(data["bid_count"]),
            str(data["ask_count"]),
            str(data["best_bid"]),
            str(data["best_ask"]),
            str(data["spread"]),
            str(data["spread_pct"]),
            str(data["midpoint"]),
            official_match_display,
            data["status"] + (f" ({data['error']})" if data["error"] else ""),
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    main()
