"""
Liquid Research — Market Classifier (Phase 2 Infrastructure)

Classifies markets into categories and duration types so that
wallet research and scanner logic never mix incompatible market
types (e.g. 5-minute crypto gambling markets vs long-horizon
Fed rate prediction markets).

No wallet. No auth. No private key. Pure data transformation only.
This module does not call any API — it only classifies data
that is passed into it.

Usage (standalone test):
    python3 analyzers/market_classifier.py
"""

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# ── Config: Keyword Lists ──────────────────────────────────────────────────
# Order matters. Categories are checked top to bottom. The first match wins.

ULTRA_SHORT_SLUG_PATTERNS = [
    "-5m-", "-10m-", "-15m-", "-30m-",
    "-1h-", "-hourly-", "-updown-",
]

SPORTS_KEYWORDS = [
    "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
    "baseball", "hockey", "tennis", "golf", "ufc", "mma", "boxing",
    "world cup", "super bowl", "championship", "playoffs", "game",
    "match", "tournament", "season", "team", "player", "score",
    "fifa", "lakers", "coach",
]

CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "crypto",
    "altcoin", "stablecoin", "defi",
]

GEOPOLITICAL_KEYWORDS = [
    "invade", "invasion", "war", "sanctions", "military", "troops",
    "ceasefire", "peace deal", "nato", "china", "taiwan", "russia",
    "ukraine", "iran", "israel", "middle east", "strait of hormuz",
    "withdraw", "airspace", "diplomatic",
]

POLITICAL_KEYWORDS = [
    "president", "election", "congress", "senate", "house",
    "supreme court", "prime minister", "governor", "legislation",
    "impeachment", "vote", "ballot", "candidate",
]

MACRO_KEYWORDS = [
    "fed", "federal reserve", "interest rate", "inflation", "gdp",
    "recession", "unemployment", "jobs report", "treasury", "bond",
    "yield", "deficit", "debt ceiling", "tariff", "trade deal",
]

# ── Config: Duration Thresholds (in days) ────────────────────────────────────

SHORT_DURATION_MAX_DAYS = 7
MEDIUM_DURATION_MAX_DAYS = 60

# ── Config: Wallet Research Inclusion Policy ─────────────────────────────────

INCLUSION_POLICY = {
    "Crypto Ultra-Short": False,
    "Sports": False,
    "Other/Unknown": "Review",
    "Macro/Economic": True,
    "Political": True,
    "Geopolitical": True,
    "Crypto Long-Duration": True,
}


# ── Function 1 ─────────────────────────────────────────────────────────────

def detect_ultra_short(slug: str) -> bool:
    """
    Check if a market slug matches an ultra-short time-window pattern.

    Receives:
        slug (str): the market's URL slug, e.g. 'btc-updown-5m-1781826300'

    Returns:
        bool: True if the slug matches a known ultra-short pattern
    """
    if not slug:
        return False
    slug_lower = slug.lower()
    return any(pattern in slug_lower for pattern in ULTRA_SHORT_SLUG_PATTERNS)


# ── Function 2 ─────────────────────────────────────────────────────────────

import re


def _contains_keyword(text: str, keyword: str) -> bool:
    """
    Check if a keyword appears in text as a whole word (or phrase),
    not as a substring inside another word.

    Example: "nfl" should match "NFL Draft" but NOT match inside
    "inflation".
    """
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text) is not None


# Country/region names that need an accompanying conflict-style
# keyword before they count as Geopolitical. On their own, country
# names are too broad — they appear in ordinary political questions
# too (e.g. "next Prime Minister of Israel").
GEOPOLITICAL_CONFLICT_KEYWORDS = [
    "invade", "invasion", "war", "sanctions", "military", "troops",
    "ceasefire", "peace deal", "withdraw", "airspace", "diplomatic",
    "strait of hormuz",
]

GEOPOLITICAL_REGION_KEYWORDS = [
    "nato", "china", "taiwan", "russia", "ukraine", "iran", "israel",
    "middle east",
]


def classify_category(title: str, slug: str) -> tuple[str, str]:
    """
    Determine which category a market belongs to, using a fixed
    priority order. First match wins.

    Receives:
        title (str): the market question/title
        slug (str): the market's URL slug

    Returns:
        tuple(category: str, reason: str)
    """
    title_lower = (title or "").lower()
    slug_lower = (slug or "").lower()
    combined = f"{title_lower} {slug_lower}"

    # Priority 1 — Crypto Ultra-Short (checked first, most reliable signal)
    if detect_ultra_short(slug_lower):
        return ("Crypto Ultra-Short", "slug matched ultra-short time pattern")

    # Priority 2 — Sports
    for kw in SPORTS_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Sports", f"matched sports keyword '{kw}'")

    # Priority 3 — Crypto Long-Duration (crypto keyword, no ultra-short slug)
    for kw in CRYPTO_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Crypto Long-Duration", f"matched crypto keyword '{kw}'")

    # Priority 4 — Geopolitical (conflict keyword required — a bare
    # country/region name like "israel" is not enough on its own,
    # since that also shows up in ordinary political questions)
    for conflict_kw in GEOPOLITICAL_CONFLICT_KEYWORDS:
        if _contains_keyword(combined, conflict_kw):
            return ("Geopolitical", f"matched geopolitical conflict keyword '{conflict_kw}'")

    # Priority 5 — Political
    for kw in POLITICAL_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Political", f"matched political keyword '{kw}'")

    # Priority 6 — Macro/Economic
    for kw in MACRO_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Macro/Economic", f"matched macro keyword '{kw}'")

    # Priority 7 — Geopolitical region name alone, with no conflict
    # keyword and no political/macro match either. Lower priority
    # than Political/Macro on purpose.
    for region_kw in GEOPOLITICAL_REGION_KEYWORDS:
        if _contains_keyword(combined, region_kw):
            return ("Geopolitical", f"matched geopolitical region keyword '{region_kw}' (no other category matched)")

    # Fallback — nothing matched
    return ("Other/Unknown", "no keyword or slug pattern matched")


# ── Function 3 ─────────────────────────────────────────────────────────────

def determine_duration_type(slug: str, days_left: float) -> str:
    """
    Assign a duration bucket independent of category.

    Receives:
        slug (str): the market's URL slug
        days_left (float): days remaining until resolution

    Returns:
        str: one of 'Ultra-Short', 'Short', 'Medium', 'Long'
    """
    if detect_ultra_short(slug):
        return "Ultra-Short"

    if days_left is None:
        return "Long"  # unknown resolution date treated conservatively

    if days_left <= SHORT_DURATION_MAX_DAYS:
        return "Short"
    elif days_left <= MEDIUM_DURATION_MAX_DAYS:
        return "Medium"
    else:
        return "Long"


# ── Function 4 ─────────────────────────────────────────────────────────────

def get_research_inclusion(category: str):
    """
    Look up whether a category should be included in wallet research.

    Receives:
        category (str): one of the seven defined categories

    Returns:
        bool or str: True, False, or "Review"
    """
    return INCLUSION_POLICY.get(category, "Review")


# ── Function 5 ─────────────────────────────────────────────────────────────

def classify_market(market: dict) -> dict:
    """
    Main orchestrator. Classifies a single market record.

    Receives:
        market (dict): must contain 'title' (or 'question') and 'slug'.
                        May optionally contain 'days_left'.

    Returns:
        dict: matches the standard output schema:
              market_title, market_slug, category, duration_type,
              include_in_wallet_research, classification_reason
    """
    title = market.get("title") or market.get("question") or "Unknown"
    slug = market.get("slug") or ""
    days_left = market.get("days_left")  # may be None if not provided

    category, reason = classify_category(title, slug)
    duration_type = determine_duration_type(slug, days_left)
    include = get_research_inclusion(category)

    return {
        "market_title": title,
        "market_slug": slug,
        "category": category,
        "duration_type": duration_type,
        "include_in_wallet_research": include,
        "classification_reason": reason,
    }


# ── Function 6 ─────────────────────────────────────────────────────────────

def classify_markets_batch(markets: list) -> pd.DataFrame:
    """
    Classify a list of markets and return a combined DataFrame.

    Receives:
        markets (list[dict]): a list of market records

    Returns:
        pandas.DataFrame: one row per market, fully classified
    """
    classified_rows = [classify_market(m) for m in markets]
    return pd.DataFrame(classified_rows)


# ── Standalone Test Block ────────────────────────────────────────────────────

EXAMPLE_MARKETS = [
    {
        "title": "Bitcoin Up or Down - June 18, 7:45PM-7:50PM ET",
        "slug": "btc-updown-5m-1781826300",
        "days_left": 0.003,
    },
    {
        "title": "Will there be no change in Fed interest rates after the July 2026 meeting?",
        "slug": "fed-no-change-july-2026",
        "days_left": 41,
    },
    {
        "title": "Will China invade Taiwan by end of 2026?",
        "slug": "china-invade-taiwan-2026",
        "days_left": 196,
    },
    {
        "title": "Will Avigdor Lieberman be the next Prime Minister of Israel?",
        "slug": "lieberman-pm-israel",
        "days_left": 220,
    },
    {
        "title": "Will Portugal win the 2026 FIFA World Cup?",
        "slug": "portugal-world-cup-2026",
        "days_left": 30,
    },
    {
        "title": "Will BTC hit $100k by December 2026?",
        "slug": "btc-100k-dec-2026",
        "days_left": 180,
    },
    {
        "title": "Strait of Hormuz traffic returns to normal by end of June?",
        "slug": "hormuz-normal-june",
        "days_left": 12,
    },
    {
        "title": "ETH Up or Down - June 18, 3:00PM-3:15PM ET",
        "slug": "eth-updown-15m-1781812800",
        "days_left": 0.01,
    },
    {
        "title": "Will the Lakers sign a new head coach by July 1?",
        "slug": "lakers-coach-july1",
        "days_left": 13,
    },
    {
        "title": "Will inflation exceed 3% in Q3 2026?",
        "slug": "inflation-q3-2026",
        "days_left": 75,
    },
]


def run_test():
    """Run the classifier against the 10 known example markets and print results."""
    console.print("\n[bold cyan]Liquid Research — Market Classifier Test[/bold cyan]")
    console.print("[dim]Testing classifier against 10 known example markets...[/dim]\n")

    results_df = classify_markets_batch(EXAMPLE_MARKETS)

    table = Table(show_lines=True)
    table.add_column("#", width=3)
    table.add_column("Market Title", max_width=40)
    table.add_column("Category", style="cyan")
    table.add_column("Duration", style="yellow")
    table.add_column("Include", justify="center")
    table.add_column("Reason", style="dim", max_width=35)

    for i, row in results_df.iterrows():
        include_val = row["include_in_wallet_research"]
        if include_val is True:
            include_display = "[green]True[/green]"
        elif include_val is False:
            include_display = "[red]False[/red]"
        else:
            include_display = "[yellow]Review[/yellow]"

        title_short = row["market_title"][:38] + ("..." if len(row["market_title"]) > 38 else "")

        table.add_row(
            str(i + 1),
            title_short,
            row["category"],
            row["duration_type"],
            include_display,
            row["classification_reason"],
        )

    console.print(table)

    total = len(results_df)
    category_counts = results_df["category"].value_counts().to_dict()
    excluded = (results_df["include_in_wallet_research"] == False).sum()
    review = (results_df["include_in_wallet_research"] == "Review").sum()

    console.print(f"\n[bold green]Test complete:[/bold green] {total}/{total} markets classified")

    category_summary = ", ".join(f"{cat} ({count})" for cat, count in category_counts.items())
    console.print(f"Categories found: {category_summary}")
    console.print(f"Excluded from wallet research: [red]{excluded}[/red]")
    console.print(f"Flagged for review: [yellow]{review}[/yellow]\n")


if __name__ == "__main__":
    run_test()