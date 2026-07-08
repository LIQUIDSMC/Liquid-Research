"""
Liquid Research — Scanner Scorer (Phase 4, Patch 5A)

Pure scoring logic only. No API calls, no file I/O, no network
access. Takes already-fetched CLOB data, an already-computed
spread label, and a few already-collected market fields, and
produces a single tradeability_score (0-100) plus a plain-English
explanation.

IMPORTANT NAMING NOTE: this is a TRADEABILITY score, not an edge
score. It reflects spread, liquidity, and volume — how tradeable
a market currently is. It does NOT estimate probability edge,
fair value, wallet performance, or expected profit. Every
explanation string produced by this module says so explicitly.

Formula (v1, approved):
    tradeability_score = (spread_component * 0.5)
                        + (liquidity_component * 0.3)
                        + (volume_component * 0.2)

Where each component is normalized to 0-100 before weighting:
    spread_component:    max(0, 100 - spread_pct)
    liquidity_component: min(100, (liquidity / 50000) * 100)
    volume_component:    min(100, (volume_24h / 50000) * 100)

Tolerates missing/None fields by treating them as 0 for the
purposes of the affected component, never by crashing.

No wallet. No private key. No execution. Read-only logic only.

Usage (standalone test):
    python3 scanner/scorer.py
"""

from typing import Optional
from rich.console import Console
from rich.table import Table

console = Console()

# Scoring formula constants (v1, approved — see module docstring).
NORMALIZATION_DIVISOR = 50000.0
SPREAD_WEIGHT = 0.5
LIQUIDITY_WEIGHT = 0.3
VOLUME_WEIGHT = 0.2

# ── Component Calculations ───────────────────────────────────────────────────

def _safe_float(value, default: float = 0.0) -> float:
    """
    Safely convert a value to float, tolerating None, empty
    string, NaN, or genuinely missing data. Never raises, never
    silently produces NaN downstream.

    Receives:
        value: anything (float, int, str, None, NaN)
        default (float): value to use if conversion fails

    Returns:
        float
    """
    if value is None or value == "":
        return default
    try:
        result = float(value)
        if result != result:  # NaN check (NaN != NaN is always True)
            return default
        return result
    except (TypeError, ValueError):
        return default


def calculate_spread_component(spread_pct: Optional[float]) -> float:
    """
    Receives:
        spread_pct (float or None): spread as a percentage of midpoint

    Returns:
        float: 0-100, higher is better (tighter spread)
    """
    pct = _safe_float(spread_pct, default=100.0)  # missing spread = worst case
    return max(0.0, 100.0 - pct)


def calculate_liquidity_component(liquidity: Optional[float]) -> float:
    """
    Receives:
        liquidity (float or None): Gamma-reported liquidity in USD

    Returns:
        float: 0-100, higher is better
    """
    liq = _safe_float(liquidity, default=0.0)
    return min(100.0, (liq / NORMALIZATION_DIVISOR) * 100.0)


def calculate_volume_component(volume_24h: Optional[float]) -> float:
    """
    Receives:
        volume_24h (float or None): Gamma-reported 24h volume in USD

    Returns:
        float: 0-100, higher is better
    """
    vol = _safe_float(volume_24h, default=0.0)
    return min(100.0, (vol / NORMALIZATION_DIVISOR) * 100.0)


# ── Primary Scoring Function ──────────────────────────────────────────────────

def score_market(spread_pct: Optional[float], liquidity: Optional[float], volume_24h: Optional[float], spread_label: str = "unknown") -> dict:
    """
    Compute a tradeability_score (0-100) and plain-English
    explanation for one market.

    Receives:
        spread_pct (float or None): spread as % of midpoint
        liquidity (float or None): Gamma liquidity in USD
        volume_24h (float or None): Gamma 24h volume in USD
        spread_label (str): label from filters.label_spread_quality()
                             (e.g. "excellent", "wide", "unknown")

    Returns:
        dict: {
            "tradeability_score": float (0-100, rounded to 1 decimal),
            "spread_component": float,
            "liquidity_component": float,
            "volume_component": float,
            "explanation": str
        }
    """
    spread_comp = calculate_spread_component(spread_pct)
    liquidity_comp = calculate_liquidity_component(liquidity)
    volume_comp = calculate_volume_component(volume_24h)

    raw_score = (spread_comp * SPREAD_WEIGHT) + (liquidity_comp * LIQUIDITY_WEIGHT) + (volume_comp * VOLUME_WEIGHT)
    score = round(max(0.0, min(100.0, raw_score)), 1)

    spread_display = f"{_safe_float(spread_pct, default=0.0):.2f}%" if spread_pct is not None else "unknown"
    liquidity_display = f"${_safe_float(liquidity, default=0.0):,.0f}"
    volume_display = f"${_safe_float(volume_24h, default=0.0):,.0f}"

    explanation = (
        f"Tradeability {score}/100. Spread {spread_display} ({spread_label}). "
        f"Liquidity {liquidity_display}, 24h volume {volume_display}. "
        f"This reflects how tradeable this market currently is, "
        f"NOT a prediction of profitability."
    )

    return {
        "tradeability_score": score,
        "spread_component": round(spread_comp, 1),
        "liquidity_component": round(liquidity_comp, 1),
        "volume_component": round(volume_comp, 1),
        "explanation": explanation,
    }


# ── Standalone Test Harness ───────────────────────────────────────────────────

TEST_CASES = [
    {
        "label": "Fed market (tight spread, high liquidity, high volume)",
        "spread_pct": 1.27, "liquidity": 273823.0, "volume_24h": 238785.0,
        "spread_label": "excellent",
        "expect_range": (90, 100),
    },
    {
        "label": "Ivory Coast market (wide spread, but high volume — near-extreme price)",
        "spread_pct": 18.18, "liquidity": 100000.0, "volume_24h": 7300000.0,
        "spread_label": "wide",
        "expect_range": (85, 95),
    },
    {
        "label": "Decent spread, very low liquidity and volume",
        "spread_pct": 5.0, "liquidity": 2000.0, "volume_24h": 1000.0,
        "spread_label": "excellent",
        "expect_range": (40, 60),
    },
    {
        "label": "All fields missing/None (e.g. failed CLOB fetch upstream)",
        "spread_pct": None, "liquidity": None, "volume_24h": None,
        "spread_label": "unknown",
        "expect_range": (0, 5),
    },
    {
        "label": "Extreme spread (effectively untradeable)",
        "spread_pct": 150.0, "liquidity": 50000.0, "volume_24h": 50000.0,
        "spread_label": "extreme",
        "expect_range": (45, 55),
    },
    {
        "label": "Perfect market (zero spread, very high liquidity/volume)",
        "spread_pct": 0.0, "liquidity": 500000.0, "volume_24h": 500000.0,
        "spread_label": "excellent",
        "expect_range": (98, 100),
    },
]


def main() -> None:
    console.print("\n[bold cyan]Liquid Research — Scorer Formula Test[/bold cyan]")
    console.print("[dim]Validating tradeability_score math against known cases, no live API calls...[/dim]\n")

    table = Table(show_lines=True)
    table.add_column("Case", max_width=40)
    table.add_column("Score", justify="right")
    table.add_column("Expected Range")
    table.add_column("Pass?", justify="center")

    all_passed = True

    for case in TEST_CASES:
        result = score_market(
            spread_pct=case["spread_pct"],
            liquidity=case["liquidity"],
            volume_24h=case["volume_24h"],
            spread_label=case["spread_label"],
        )
        score = result["tradeability_score"]
        low, high = case["expect_range"]
        passed = low <= score <= high
        all_passed = all_passed and passed

        table.add_row(
            case["label"],
            str(score),
            f"{low}-{high}",
            "[green]✓[/green]" if passed else "[red]✗[/red]",
        )

    console.print(table)

    console.print(f"\n[bold]Sample explanation text:[/bold]")
    sample = score_market(1.27, 273823.0, 238785.0, "excellent")
    console.print(f"  {sample['explanation']}\n")

    if all_passed:
        console.print("[bold green]All formula tests passed.[/bold green]\n")
    else:
        console.print("[bold red]Some formula tests FAILED — review before building scanner.py on top of this.[/bold red]\n")


if __name__ == "__main__":
    main()
