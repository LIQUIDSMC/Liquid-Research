"""
Liquid Research — ONE-TIME Legacy Metadata Backfill (2026-06-24)

Purpose: backfill metadata for paper trades 1-5 ONLY. These trades
were created before the Phase 5 Research Improvements metadata
patch (2026-06-23) and have NaN for category, category_tier,
scanner_run_id, spread_label, liquidity, volume_24h, and
recurrence_count.

This is NOT a general migration framework. It is a one-time,
dated script for this specific historical gap. Delete or archive
after a successful, verified run.

Source of truth: data/scanner/scanner_run_20260621_2155.csv
(confirmed to still exist and contain all 5 legacy market_ids
with complete metadata, verified 2026-06-24 before writing this
script).

Safety rules enforced:
- Matches rows by trade_id, never by row index/position
- Only touches rows where trade_id is in [1,2,3,4,5] AND category
  is currently null (so re-running this script is a no-op if
  already applied — it will not re-touch already-backfilled rows)
- NEVER writes to entry_price, position_size, status,
  resolution_date, winning_outcome, trade_won, trade_pnl, or
  exit_reason — only the 7 confirmed-recoverable metadata fields
- Forces object dtype on target columns before writing, per the
  paper_resolver.py LossySetitemError lesson
- Creates a timestamped backup of paper_trades.csv before writing
- Prints a before/after preview and runs full verification after
  writing, re-reading from disk (not from memory)

No wallet. No private key. No execution. Read-only except for the
one explicit, verified write to paper_trades.csv.

Usage:
    python3 simulator/backfill_2026_06_24_legacy_metadata.py
"""

import os
import shutil
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

PAPER_TRADES_PATH = "data/simulator/paper_trades.csv"
SOURCE_SCANNER_RUN = "data/scanner/scanner_run_20260621_2155.csv"
LEGACY_TRADE_IDS = [1, 2, 3, 4, 5]

RECOVERABLE_FIELDS = [
    "category", "category_tier", "scanner_run_id",
    "spread_label", "liquidity", "volume_24h", "recurrence_count",
]

PROTECTED_FIELDS = [
    "entry_price", "position_size", "status", "resolution_date",
    "winning_outcome", "trade_won", "trade_pnl", "exit_reason",
]


def create_backup(path: str) -> str:
    """Create a timestamped backup before any write."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.backup_{timestamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def main():
    console.print("\n[bold cyan]Liquid Research — Legacy Metadata Backfill (ONE-TIME, 2026-06-24)[/bold cyan]\n")

    if not os.path.exists(PAPER_TRADES_PATH):
        console.print(f"[red]No file found at {PAPER_TRADES_PATH}[/red]")
        return

    if not os.path.exists(SOURCE_SCANNER_RUN):
        console.print(f"[red]Source scanner run not found at {SOURCE_SCANNER_RUN}. Cannot proceed.[/red]")
        return

    backup_path = create_backup(PAPER_TRADES_PATH)
    console.print(f"[green]Backup created:[/green] {backup_path}\n")

    df = pd.read_csv(PAPER_TRADES_PATH)
    scanner_df = pd.read_csv(SOURCE_SCANNER_RUN)

    pre_state = df[["trade_id"] + PROTECTED_FIELDS].copy()
    pre_total_rows = len(df)
    pre_closed_count = (df["status"] == "closed").sum()
    pre_wins = (df["trade_won"] == True).sum()
    pre_losses = (df["trade_won"] == False).sum()
    pre_total_pnl = round(df["trade_pnl"].sum(), 2)

    target_mask = df["trade_id"].isin(LEGACY_TRADE_IDS) & df["category"].isna()
    target_rows = df[target_mask]

    if target_rows.empty:
        console.print("[yellow]No rows match the backfill criteria (already backfilled, or trade_ids 1-5 not found). No action taken.[/yellow]\n")
        return

    console.print(f"Found {len(target_rows)} row(s) to backfill (trade_ids: {sorted(target_rows['trade_id'].tolist())})\n")

    for col in RECOVERABLE_FIELDS:
        if col in df.columns:
            df[col] = df[col].astype(object)

    console.print("[bold]── Before / After Preview ──[/bold]\n")

    import sys
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzers"))
    from market_classifier import classify_market

    for idx in df[target_mask].index:
        market_id = df.at[idx, "market_id"]
        trade_id = df.at[idx, "trade_id"]

        match = scanner_df[scanner_df["market_id"] == market_id]

        if match.empty:
            console.print(f"[red]Trade {trade_id}: market_id not found in source scanner run. Skipping — left as NaN.[/red]")
            continue

        source_row = match.iloc[0]

        before = {col: df.at[idx, col] for col in RECOVERABLE_FIELDS}

        df.at[idx, "scanner_run_id"] = os.path.basename(SOURCE_SCANNER_RUN)
        df.at[idx, "spread_label"] = source_row.get("spread_label")
        df.at[idx, "liquidity"] = source_row.get("liquidity")
        df.at[idx, "volume_24h"] = source_row.get("volume_24h")
        df.at[idx, "recurrence_count"] = 0

        classification = classify_market({
            "title": df.at[idx, "question"],
            "slug": df.at[idx, "slug"],
            "days_left": None,
        })
        df.at[idx, "category"] = classification.get("category", "Unknown")
        df.at[idx, "category_tier"] = classification.get("category_tier", "Unknown")

        after = {col: df.at[idx, col] for col in RECOVERABLE_FIELDS}

        console.print(f"[bold]Trade {trade_id}:[/bold] {df.at[idx, 'question']}")
        console.print(f"  Before: {before}")
        console.print(f"  After:  {after}\n")

    df.to_csv(PAPER_TRADES_PATH, index=False)
    console.print(f"[green]Written → {PAPER_TRADES_PATH}[/green]\n")

    console.print("[bold cyan]── Post-Write Verification (re-read from disk) ──[/bold cyan]\n")

    verify_df = pd.read_csv(PAPER_TRADES_PATH)

    checks_passed = True

    if len(verify_df) == pre_total_rows:
        console.print(f"[green]✓[/green] Total rows unchanged: {len(verify_df)}")
    else:
        console.print(f"[red]✗[/red] ROW COUNT MISMATCH: was {pre_total_rows}, now {len(verify_df)}")
        checks_passed = False

    post_closed_count = (verify_df["status"] == "closed").sum()
    if post_closed_count == pre_closed_count:
        console.print(f"[green]✓[/green] Closed trade count unchanged: {post_closed_count}")
    else:
        console.print(f"[red]✗[/red] CLOSED COUNT MISMATCH: was {pre_closed_count}, now {post_closed_count}")
        checks_passed = False

    post_wins = (verify_df["trade_won"] == True).sum()
    post_losses = (verify_df["trade_won"] == False).sum()
    if post_wins == pre_wins and post_losses == pre_losses:
        console.print(f"[green]✓[/green] Wins/losses unchanged: {post_wins}W / {post_losses}L")
    else:
        console.print(f"[red]✗[/red] WIN/LOSS MISMATCH: was {pre_wins}W/{pre_losses}L, now {post_wins}W/{post_losses}L")
        checks_passed = False

    post_total_pnl = round(verify_df["trade_pnl"].sum(), 2)
    if post_total_pnl == pre_total_pnl:
        console.print(f"[green]✓[/green] Total realized P&L unchanged: ${post_total_pnl}")
    else:
        console.print(f"[red]✗[/red] P&L MISMATCH: was ${pre_total_pnl}, now ${post_total_pnl}")
        checks_passed = False

    post_state = verify_df[["trade_id"] + PROTECTED_FIELDS]
    merged_check = pre_state.merge(post_state, on="trade_id", suffixes=("_pre", "_post"))
    protected_mismatch = False
    for col in PROTECTED_FIELDS:
        diffs = merged_check[merged_check[f"{col}_pre"].astype(str) != merged_check[f"{col}_post"].astype(str)]
        if not diffs.empty:
            console.print(f"[red]✗[/red] PROTECTED FIELD '{col}' CHANGED on trade_id(s): {diffs['trade_id'].tolist()}")
            protected_mismatch = True
            checks_passed = False
    if not protected_mismatch:
        console.print(f"[green]✓[/green] All protected fields (P&L, resolution, status, etc.) byte-for-byte unchanged")

    still_missing = verify_df[verify_df["trade_id"].isin(LEGACY_TRADE_IDS) & verify_df["category"].isna()]
    if still_missing.empty:
        console.print(f"[green]✓[/green] All legacy trade_ids 1-5 now have category populated")
    else:
        console.print(f"[red]✗[/red] Still missing category on trade_id(s): {still_missing['trade_id'].tolist()}")
        checks_passed = False

    console.print()
    if checks_passed:
        console.print("[bold green]ALL VERIFICATION CHECKS PASSED.[/bold green]")
        console.print(f"[dim]Backup retained at {backup_path} — safe to delete once you've reviewed this output.[/dim]\n")
    else:
        console.print("[bold red]VERIFICATION FAILED. Review the mismatches above.[/bold red]")
        console.print(f"[bold red]Restore from backup if needed: cp {backup_path} {PAPER_TRADES_PATH}[/bold red]\n")


if __name__ == "__main__":
    main()