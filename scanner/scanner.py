"""
Liquid Research — Scanner Engine (Phase 4, Patch 5B)

Orchestrator only. Reads the most recent slug-populated market
snapshot, runs each market through the existing CLOB-based empty-
book filter, labels spread quality for survivors, scores survivors
via scorer.py, and saves the full run (killed and passed) to CSV.

Contains NO filter logic and NO scoring logic itself — both
already exist in filters.py and scorer.py. This file only reads
data, calls already-validated functions, and reports results.

Does NOT use conditionId lookup anywhere. Slug comes directly from
the snapshot CSV (added in Patch 4). A missing/blank slug is
killed with reason "missing_slug" — no fallback lookup is
attempted, per the explicit architecture decision in this phase.

Does NOT trigger fresh market collection. Reads the existing,
already-collected snapshot only.

No wallet. No private key. No execution. Read-only.

Usage:
    python3 scanner/scanner.py
"""

import sys
import os
import glob
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from clob_client import get_market_clob_data
from filters import evaluate_empty_book_filter, label_spread_quality
from scorer import score_market

console = Console()

MARKETS_DIR = "data/markets"
SCANNER_OUTPUT_DIR = "data/scanner"


# ── Snapshot Loading ──────────────────────────────────────────────────────────

def find_latest_snapshot() -> str:
    """
    Find the most recently created snapshot CSV in data/markets/.

    Receives:
        Nothing — reads from the filesystem directly.

    Returns:
        str: path to the latest snapshot, or None if none exist
    """
    snapshots = glob.glob(os.path.join(MARKETS_DIR, "snapshot_*.csv"))
    if not snapshots:
        return None
    return max(snapshots, key=os.path.getmtime)


def load_snapshot(path: str) -> pd.DataFrame:
    """
    Load a snapshot CSV and confirm it has a slug column.

    Receives:
        path (str): path to the snapshot CSV

    Returns:
        pd.DataFrame: the loaded snapshot, or empty DataFrame on failure
    """
    try:
        df = pd.read_csv(path)
    except Exception as e:
        console.print(f"[red]Error reading snapshot: {e}[/red]")
        return pd.DataFrame()

    if "slug" not in df.columns:
        console.print(
            "[red]This snapshot has no 'slug' column. It was likely created "
            "before Patch 4. Re-run collectors/market_collector.py to produce "
            "a scanner-compatible snapshot.[/red]"
        )
        return pd.DataFrame()

    return df


# ── Per-Market Processing ─────────────────────────────────────────────────────

def process_market(row: pd.Series) -> dict:
    """
    Run one market through the full filter -> label -> score pipeline.

    Receives:
        row (pd.Series): one row from the snapshot DataFrame

    Returns:
        dict: a complete result row, ready to append to the output list.
              Always includes 'killed' and 'kill_reason' (None if passed).
              Includes 'tradeability_score' and 'explanation' only if passed.
    """
    question = row.get("question", "Unknown")
    market_id = row.get("market_id", "")
    slug = row.get("slug", "")
    liquidity = row.get("liquidity", 0)
    volume_24h = row.get("volume_24h", 0)

    base_result = {
        "market_id": market_id,
        "question": question,
        "liquidity": liquidity,
        "volume_24h": volume_24h,
    }

    # Slug check — no conditionId fallback, per architecture decision
    if not slug or (isinstance(slug, float) and pd.isna(slug)) or str(slug).strip() == "":
        return {
            **base_result,
            "killed": True,
            "kill_reason": "missing_slug",
            "clob_status": None,
            "bid_count": None,
            "ask_count": None,
            "spread_pct": None,
            "spread_label": None,
            "tradeability_score": None,
            "explanation": None,
        }

    # Fetch CLOB data via slug — confirmed reliable method
    clob_data = get_market_clob_data(slug)

    # Empty-book filter
    filter_result = evaluate_empty_book_filter(clob_data)

    if not filter_result["passed"]:
        return {
            **base_result,
            "killed": True,
            "kill_reason": filter_result["reason"],
            "clob_status": clob_data.get("status") if clob_data else None,
            "bid_count": clob_data.get("bid_count") if clob_data else None,
            "ask_count": clob_data.get("ask_count") if clob_data else None,
            "spread_pct": None,
            "spread_label": None,
            "tradeability_score": None,
            "explanation": None,
        }

    # Passed empty-book filter — label spread quality and score
    spread_label_result = label_spread_quality(clob_data)
    score_result = score_market(
        spread_pct=clob_data.get("spread_pct"),
        liquidity=liquidity,
        volume_24h=volume_24h,
        spread_label=spread_label_result["label"],
    )

    return {
        **base_result,
        "killed": False,
        "kill_reason": None,
        "clob_status": clob_data.get("status"),
        "bid_count": clob_data.get("bid_count"),
        "ask_count": clob_data.get("ask_count"),
        "spread_pct": clob_data.get("spread_pct"),
        "spread_label": spread_label_result["label"],
        "tradeability_score": score_result["tradeability_score"],
        "explanation": score_result["explanation"],
    }


# ── Display ───────────────────────────────────────────────────────────────────

def print_killed_table(killed_rows: list, max_rows: int = 15):
    if not killed_rows:
        console.print("[dim]No markets killed.[/dim]")
        return

    table = Table(title="Killed Markets", show_lines=True)
    table.add_column("Market", max_width=45)
    table.add_column("Reason", style="red")

    for row in killed_rows[:max_rows]:
        title = str(row["question"])[:43] + ("..." if len(str(row["question"])) > 43 else "")
        table.add_row(title, str(row["kill_reason"]))

    console.print(table)
    if len(killed_rows) > max_rows:
        console.print(f"[dim]...and {len(killed_rows) - max_rows} more killed markets not shown[/dim]")


def print_top_10(passed_rows: list):
    if not passed_rows:
        console.print("[yellow]No markets passed. Nothing to rank.[/yellow]")
        return

    sorted_rows = sorted(passed_rows, key=lambda r: r["tradeability_score"], reverse=True)
    top_10 = sorted_rows[:10]

    table = Table(title="Top 10 by Tradeability Score", show_lines=True)
    table.add_column("#", justify="right")
    table.add_column("Market", max_width=40)
    table.add_column("Score", justify="right")
    table.add_column("Spread Label")
    table.add_column("Explanation", max_width=50)

    for i, row in enumerate(top_10, 1):
        title = str(row["question"])[:38] + ("..." if len(str(row["question"])) > 38 else "")
        table.add_row(
            str(i), title, str(row["tradeability_score"]),
            str(row["spread_label"]), str(row["explanation"]),
        )

    console.print(table)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    console.print("\n[bold cyan]Liquid Research — Scanner Engine[/bold cyan]")

    snapshot_path = find_latest_snapshot()
    if not snapshot_path:
        console.print("[red]No snapshot found in data/markets/. Run market_collector.py first.[/red]")
        return

    console.print(f"Loaded snapshot: {snapshot_path}")

    df = load_snapshot(snapshot_path)
    if df.empty:
        return

    total_count = len(df)
    console.print(f"[dim]Scanning {total_count} markets...[/dim]\n")

    results = []
    for _, row in df.iterrows():
        result = process_market(row)
        results.append(result)

    killed_rows = [r for r in results if r["killed"]]
    passed_rows = [r for r in results if not r["killed"]]

    print_killed_table(killed_rows)
    console.print()
    print_top_10(passed_rows)

    # Save full run to CSV
    os.makedirs(SCANNER_OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(SCANNER_OUTPUT_DIR, f"scanner_run_{timestamp}.csv")

    output_columns = [
        "market_id", "question", "clob_status", "bid_count", "ask_count",
        "spread_pct", "spread_label", "liquidity", "volume_24h",
        "tradeability_score", "explanation", "killed", "kill_reason",
    ]
    results_df = pd.DataFrame(results)[output_columns]
    results_df.to_csv(output_path, index=False)

    console.print(f"\n[bold]Scanned: {total_count} | Killed: {len(killed_rows)} | Passed: {len(passed_rows)}[/bold]")
    console.print(f"[dim]Saved → {output_path}[/dim]\n")


if __name__ == "__main__":
    main()
