"""
Liquid Research — Market Collector (Phase 1)
Pulls active Polymarket markets from the public Gamma API.
No wallet. No auth. No private key. Read-only.
"""

import requests
import pandas as pd
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
import os
import json
import sys
from typing import Optional

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "classification"))
from market_classifier import classify_market

console = Console()

GAMMA_API = "https://gamma-api.polymarket.com"
MIN_VOLUME_24H = 5000
MIN_TOTAL_VOLUME = 10000
MAX_RESULTS = 200

# Kill filter thresholds used inside process_markets(). Centralized
# here alongside the volume thresholds above for consistency —
# these values were previously inline literals in the filter logic.
MIN_DAYS_LEFT = 1
MAX_DAYS_LEFT = 365
EXTREME_PRICE_LOWER_BOUND = 0.01
EXTREME_PRICE_UPPER_BOUND = 0.99
MAX_PRICE_SUM_DEVIATION = 0.10

FOCUS_KEYWORDS = [
    "president", "election", "federal reserve", "fed", "rate", "inflation",
    "gdp", "recession", "unemployment", "bitcoin", "crypto", "ethereum",
    "btc", "eth", "solana", "stocks", "s&p", "nasdaq", "dow",
    "congress", "senate", "house", "supreme court", "geopolitical",
    "war", "sanctions", "tariff", "trade", "economy", "economic",
    "jobs", "debt", "deficit", "treasury", "bond", "yield",
    "china", "europe", "eu", "nato", "ukraine", "middle east",
    "oil", "energy", "commodities", "gold", "dollar", "currency",
]

SPORTS_KEYWORDS = [
    "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
    "baseball", "hockey", "tennis", "golf", "ufc", "mma", "boxing",
    "world cup", "super bowl", "championship", "playoffs", "game",
    "match", "tournament", "season", "team", "player", "score",
]

OUTPUT_DIR = "L2_DOMAINS/prediction_markets/data/markets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_markets(limit: int = MAX_RESULTS, offset: int = 0) -> list[dict]:
    url = f"{GAMMA_API}/markets"
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "offset": offset,
        "order": "volume24hr",
        "ascending": "false",
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[red]API error: {e}[/red]")
        return []

def is_sports_market(question: str, slug: Optional[str] = None, days_left: Optional[float] = None) -> bool:
    """
    Determines whether a market is Sports, using the shared
    classify_market() function from analyzers/market_classifier.py
    rather than a locally duplicated keyword list. This was the
    root cause of the original desync: market_classifier.py checks
    title+slug combined, while this function previously checked
    question text only, missing markets like "Texas Rangers vs.
    Miami Marlins" whose slug (e.g. "mlb-tex-mia-2026-06-24")
    contains a sports keyword but whose question text does not.

    Fails safe: if classification raises an unexpected error,
    this returns False (does not kill the market) rather than
    crashing the collector — a misclassified market reaching the
    next filter stage is a much smaller problem than the entire
    collector run failing.

    Receives:
        question (str): the market question/title
        slug (str or None): the market's URL slug
        days_left (float or None): days until resolution

    Returns:
        bool: True if classify_market() returns category "Sports"
    """
    try:
        classification = classify_market({
            "title": question,
            "slug": slug or "",
            "days_left": days_left,
        })
        return classification.get("category") == "Sports"
    except Exception as e:
        console.print(f"[yellow]Warning: classify_market() failed during sports check ({e}). Market not killed as a precaution.[/yellow]")
        return False

def is_focus_market(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in FOCUS_KEYWORDS)

def passes_volume_filter(volume_24h: float, volume_total: float) -> bool:
    return volume_24h >= MIN_VOLUME_24H and volume_total >= MIN_TOTAL_VOLUME

def parse_price(raw) -> float:
    try:
        if isinstance(raw, list):
            return float(raw[0])
        return float(raw)
    except (TypeError, ValueError, IndexError):
        return 0.0

def days_until_end(end_date_str: Optional[str] = None) -> float:
    if not end_date_str:
        return 999.0
    try:
        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0.0, (end_dt - now).total_seconds() / 86400)
    except Exception:
        return 999.0

def process_markets(raw_markets: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    passed = []
    kill_log = []

    for m in raw_markets:
        question = m.get("question") or m.get("title") or "Unknown"
        volume_24h = float(m.get("volume24hr") or 0)
        volume_total = float(m.get("volume") or 0)
        end_date = m.get("endDate") or m.get("end_date_iso") or ""
        days_left = days_until_end(end_date)

        outcome_prices = m.get("outcomePrices") or []
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []

        yes_price = parse_price(outcome_prices[0]) if len(outcome_prices) > 0 else 0.0
        no_price = parse_price(outcome_prices[1]) if len(outcome_prices) > 1 else 0.0
        price_sum_deviation = round(abs(1.0 - yes_price - no_price), 4)
        liquidity = float(m.get("liquidity") or 0)

        if is_sports_market(question, slug=m.get("slug"), days_left=days_left):
            kill_log.append({"question": question[:80], "kill_reason": "SPORTS — excluded category (matched via shared classifier)"})
            continue

        if not passes_volume_filter(volume_24h, volume_total):
            kill_log.append({"question": question[:80], "kill_reason": f"LOW VOLUME — 24h=${volume_24h:,.0f} total=${volume_total:,.0f}"})
            continue

        if days_left < MIN_DAYS_LEFT:
            kill_log.append({"question": question[:80], "kill_reason": "TOO CLOSE — resolves in under 1 day"})
            continue

        if days_left > MAX_DAYS_LEFT:
            kill_log.append({"question": question[:80], "kill_reason": "TOO FAR — resolves in over 365 days"})
            continue

        if yes_price <= EXTREME_PRICE_LOWER_BOUND or yes_price >= EXTREME_PRICE_UPPER_BOUND:
            kill_log.append({"question": question[:80], "kill_reason": f"EXTREME PRICE — yes={yes_price:.2f} (no edge)"})
            continue
        
        if price_sum_deviation > MAX_PRICE_SUM_DEVIATION:
            kill_log.append({"question": question[:80], "kill_reason": f"PRICE SUM DEVIATION — {price_sum_deviation:.3f} (over 10%, Yes+No pricing looks broken/stale)"})
            continue

        passed.append({
            "question": question[:100],
            "yes_price": round(yes_price, 4),
            "no_price": round(no_price, 4),
            "price_sum_deviation": price_sum_deviation,
            "volume_24h": round(volume_24h, 2),
            "volume_total": round(volume_total, 2),
            "liquidity": round(liquidity, 2),
            "days_left": round(days_left, 1),
            "focus_match": is_focus_market(question),
            "market_id": m.get("conditionId") or "",
            "slug": m.get("slug") or "",
            "end_date": end_date[:10] if end_date else "",
        })


    kill_df = pd.DataFrame(kill_log)
    os.makedirs("logs", exist_ok=True)
    kill_df.to_csv("L2_DOMAINS/prediction_markets/data/kill_log.csv", index=False)

    passed_df = pd.DataFrame(passed)
    if not passed_df.empty:
        passed_df = passed_df.sort_values(
            by=["focus_match", "volume_24h"], ascending=[False, False]
        ).reset_index(drop=True)

    return passed_df, kill_df

def print_results(passed_df: pd.DataFrame, kill_df: pd.DataFrame, total_fetched: int) -> None:
    console.print("\n[bold cyan]═══ Liquid Research — Market Scanner ═══[/bold cyan]\n")
    console.print(f"  Fetched:  [white]{total_fetched}[/white]")
    console.print(f"  Killed:   [red]{len(kill_df)}[/red]")
    console.print(f"  Passed:   [green]{len(passed_df)}[/green]\n")

    if passed_df.empty:
        console.print("[yellow]No markets passed all filters.[/yellow]")
        return

    table = Table(title="Passing Markets (Top 15)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Market Question", style="white", max_width=52)
    table.add_column("YES", justify="right", style="green")
    table.add_column("Price Sum Dev", justify="right", style="yellow")
    table.add_column("Vol 24h", justify="right", style="cyan")
    table.add_column("Days", justify="right")
    table.add_column("Focus", justify="center")

    for i, row in passed_df.head(15).iterrows():
        table.add_row(
            str(i + 1),
            row["question"],
            f"{row['yes_price']:.3f}",
            f"{row['price_sum_deviation']:.3f}",
            f"${row['volume_24h']:,.0f}",
            f"{row['days_left']:.0f}d",
            "[green]✓[/green]" if row["focus_match"] else "·",
        )
    console.print(table)

    console.print(f"\n[bold red]Sample Killed Markets:[/bold red]")
    for _, row in kill_df.head(8).iterrows():
        console.print(f"  [red]✗[/red] {row['question'][:65]}  →  [dim]{row['kill_reason']}[/dim]")

def main() -> None:
    console.print("[bold]Liquid Research — Phase 1 starting...[/bold]")
    console.print("[dim]Source: Polymarket Gamma API (public, read-only, no auth)[/dim]\n")

    raw = fetch_markets()
    if not raw:
        console.print("[red]No data returned. Check your internet connection.[/red]")
        return

    console.print(f"[dim]Raw markets from API: {len(raw)}[/dim]")

    passed_df, kill_df = process_markets(raw)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    if not passed_df.empty:
        out_path = f"{OUTPUT_DIR}/snapshot_{timestamp}.csv"
        passed_df.to_csv(out_path, index=False)
        console.print(f"[dim]Saved → {out_path}[/dim]")

    console.print(f"[dim]Kill log → L2_DOMAINS/prediction_markets/data/kill_log.csv[/dim]\n")
    print_results(passed_df, kill_df, len(raw))
    console.print(f"\n[bold green]Done.[/bold green]\n")

if __name__ == "__main__":
    main()
