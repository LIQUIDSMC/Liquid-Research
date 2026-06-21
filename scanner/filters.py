"""
Liquid Research — Scanner Filters (Phase 4, Patch 2)

First CLOB-based kill filter: Empty Book / Unusable Book.

A market fails this filter if it has no usable order book at all
(market not found, no tokens minted, book fetch failed) OR if the
book exists but is not genuinely two-sided (zero bids or zero asks
on the side(s) checked).

Rationale: a market with no bids or no asks is not realistically
tradeable, regardless of any future scoring logic. This is the
simplest, most unambiguous CLOB-based kill rule, and intentionally
does not address spread width or depth quality — those are
separate, threshold-based decisions reserved for later patches.

This file does NOT do spread thresholds, depth scoring, ranking,
or scanner orchestration. It contains the empty-book filter only.

No wallet. No private key. No execution. Read-only logic only.

Usage (standalone test):
    python3 scanner/filters.py
"""

import sys
import os
from rich.console import Console
from rich.table import Table

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from clob_client import get_market_clob_data

console = Console()

# Status values from clob_client.py that mean "no usable book exists
# at all" — distinct from "book exists but is empty on one side."
NO_BOOK_STATUSES = {
    "market_not_found",
    "no_token_ids",
    "invalid_outcome_index",
    "book_fetch_failed",
}


# ── Helper ────────────────────────────────────────────────────────────────────

def is_empty_book(clob_data: dict) -> bool:
    """
    Quick boolean check: does this market have an empty or
    nonexistent order book?

    Receives:
        clob_data (dict): output of clob_client.get_market_clob_data()

    Returns:
        bool: True if the book is empty or doesn't exist
    """
    if not clob_data:
        return True

    status = clob_data.get("status")
    if status in NO_BOOK_STATUSES:
        return True

    bid_count = clob_data.get("bid_count", 0)
    ask_count = clob_data.get("ask_count", 0)

    return bid_count == 0 or ask_count == 0


# ── Primary Scanner-Facing Function ──────────────────────────────────────────

def evaluate_empty_book_filter(clob_data: dict) -> dict:
    """
    Evaluate whether a market passes the empty-book filter, with a
    specific, explainable reason on failure — so future scanner
    output can log WHY a market was killed, not just that it was.

    Receives:
        clob_data (dict): output of clob_client.get_market_clob_data().
                           May be None/empty if CLOB data was never
                           successfully fetched at all.

    Returns:
        dict: {
            "passed": bool,
            "filter": "empty_book",
            "reason": str or None
        }
    """
    if not clob_data:
        return {"passed": False, "filter": "empty_book", "reason": "missing_clob_data"}

    status = clob_data.get("status")

    if status in NO_BOOK_STATUSES:
        return {"passed": False, "filter": "empty_book", "reason": status}

    bid_count = clob_data.get("bid_count", 0)
    ask_count = clob_data.get("ask_count", 0)

    if bid_count == 0 and ask_count == 0:
        return {"passed": False, "filter": "empty_book", "reason": "zero_bids_and_asks"}
    elif bid_count == 0:
        return {"passed": False, "filter": "empty_book", "reason": "zero_bids"}
    elif ask_count == 0:
        return {"passed": False, "filter": "empty_book", "reason": "zero_asks"}

    return {"passed": True, "filter": "empty_book", "reason": None}


# ── Standalone Test Harness ───────────────────────────────────────────────────

TEST_SLUGS = [
    "will-there-be-no-change-in-fed-interest-rates-after-the-july-2026-meeting",  # should PASS
    "will-ivory-coast-win-the-2026-fifa-world-cup",                                # should PASS
    "strait-of-hormuz-traffic-returns-to-normal-by-end-of-june",                   # should PASS
    "ethereum-above-2275-on-april-21-2026-3pm-et",                                 # should FAIL (closed, no book)
]


def main():
    console.print("\n[bold cyan]Liquid Research — Empty Book Filter Test[/bold cyan]")
    console.print("[dim]Validating against 3 known-active markets (expect PASS) and 1 known-closed market (expect FAIL)...[/dim]\n")

    table = Table(show_lines=True)
    table.add_column("Slug", max_width=30)
    table.add_column("Bid Count")
    table.add_column("Ask Count")
    table.add_column("CLOB Status")
    table.add_column("Filter Result")
    table.add_column("Reason")

    for slug in TEST_SLUGS:
        clob_data = get_market_clob_data(slug)
        result = evaluate_empty_book_filter(clob_data)

        result_display = "[green]PASS[/green]" if result["passed"] else "[red]FAIL[/red]"
        reason_display = result["reason"] or "[dim]—[/dim]"

        table.add_row(
            slug[:28],
            str(clob_data.get("bid_count")),
            str(clob_data.get("ask_count")),
            str(clob_data.get("status")),
            result_display,
            reason_display,
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    main()