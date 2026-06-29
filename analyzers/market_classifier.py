"""
Liquid Research — Market Classifier (Phase 2 Infrastructure)

Classifies markets into categories so that wallet research and
scanner logic never mix incompatible market types (e.g. 5-minute
crypto gambling markets vs long-horizon Fed rate prediction markets).

CATEGORY TIER SYSTEM:
Categories are organized into three tiers, reflecting project
philosophy that category importance should be discovered through
data, not assumed upfront:

  - Active Research:  currently studied for wallet/scanner research
  - Research Queue:    tracked and tagged, but not yet actively
                        sampled for wallet discovery
  - Excluded:           does not align with long-horizon prediction
                        skill research (sports, ultra-short crypto,
                        entertainment, celebrity/gossip markets)

This tier list is expected to evolve. It is not a final taxonomy —
it is a starting lens. Future hypothesis testing may reveal that
other signals (hold time, price range, volume tier) matter more
than category itself.

No wallet. No auth. No private key. Pure data transformation only.
This module does not call any API — it only classifies data
that is passed into it.

Usage (standalone test):
    python3 analyzers/market_classifier.py
"""

import re
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# ── Config: Category Tiers ───────────────────────────────────────────────────

CATEGORY_TIERS = {
    # Active Research — currently studied for wallet/scanner research
    "Macro/Economic": "Active Research",
    "Political": "Active Research",
    "Geopolitical": "Active Research",
    "Crypto Long-Duration": "Active Research",

    # Research Queue — tagged and tracked, not yet actively sampled
    "Corporate Events": "Research Queue",
    "Regulatory Decisions": "Research Queue",
    "Legal/Court Cases": "Research Queue",
    "Product Launches": "Research Queue",
    "Other/Unknown": "Research Queue",

    # Excluded — does not align with long-horizon prediction skill
    "Sports": "Excluded",
    "Crypto Ultra-Short": "Excluded",
    "Entertainment": "Excluded",
    "Celebrity/Gossip": "Excluded",
}

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
    "fifa", "lakers", "coach", "wta", "atp", "fifwc",
    "cricket", "t20", "odi", "ipl",
    "gold glove", "platinum glove", "cy young", "heisman",
    "ballon d'or", "silver slugger",
]

ENTERTAINMENT_KEYWORDS = [
    "oscar", "grammy", "emmy", "box office", "album", "movie",
    "tv show", "netflix series", "billboard chart",
]

CELEBRITY_KEYWORDS = [
    "kardashian", "celebrity breakup", "celebrity divorce",
    "celebrity dating", "influencer drama",
]

CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "crypto",
    "altcoin", "stablecoin", "defi",
]

CORPORATE_KEYWORDS = [
    "earnings", "ipo", "merger", "acquisition", "ceo resigns",
    "ceo steps down", "stock split", "bankruptcy filing", "layoffs",
]

REGULATORY_KEYWORDS = [
    "fda approval", "fcc ruling", "sec ruling", "antitrust",
    "regulatory approval", "ban approved", "license revoked",
]

LEGAL_KEYWORDS = [
    "supreme court ruling", "verdict", "lawsuit", "indictment",
    "convicted", "acquitted", "trial begins", "appeal denied",
]

PRODUCT_LAUNCH_KEYWORDS = [
    "product launch", "release date", "unveils", "new model",
    "ships in", "pre-order",
]

GEOPOLITICAL_CONFLICT_KEYWORDS = [
    "invade", "invasion", "war", "sanctions", "military", "troops",
    "ceasefire", "peace deal", "withdraw", "airspace", "diplomatic",
    "strait of hormuz",
]

GEOPOLITICAL_REGION_KEYWORDS = [
    "nato", "china", "chinese", "taiwan", "russia", "russian",
    "ukraine", "iran", "iranian", "israel", "israeli", "middle east",
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
    "Entertainment": False,
    "Celebrity/Gossip": False,
    "Other/Unknown": "Review",
    "Macro/Economic": True,
    "Political": True,
    "Geopolitical": True,
    "Crypto Long-Duration": True,
    "Corporate Events": True,
    "Regulatory Decisions": True,
    "Legal/Court Cases": True,
    "Product Launches": True,
}


# ── Helper: Word-Boundary Keyword Matching ───────────────────────────────────

def _contains_keyword(text: str, keyword: str) -> bool:
    """
    Check if a keyword appears in text as a whole word (or phrase),
    not as a substring inside another word.

    Example: "nfl" should match "NFL Draft" but NOT match inside
    "inflation". This is the fix for the original substring bug.
    """
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text) is not None


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

    # Priority 3 — Entertainment
    for kw in ENTERTAINMENT_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Entertainment", f"matched entertainment keyword '{kw}'")

    # Priority 4 — Celebrity/Gossip
    for kw in CELEBRITY_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Celebrity/Gossip", f"matched celebrity/gossip keyword '{kw}'")

    # Priority 5 — Crypto Long-Duration (crypto keyword, no ultra-short slug)
    for kw in CRYPTO_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Crypto Long-Duration", f"matched crypto keyword '{kw}'")

    # Priority 6 — Corporate Events
    for kw in CORPORATE_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Corporate Events", f"matched corporate keyword '{kw}'")

    # Priority 7 — Regulatory Decisions
    for kw in REGULATORY_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Regulatory Decisions", f"matched regulatory keyword '{kw}'")

    # Priority 8 — Legal/Court Cases
    for kw in LEGAL_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Legal/Court Cases", f"matched legal keyword '{kw}'")

    # Priority 9 — Product Launches
    for kw in PRODUCT_LAUNCH_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Product Launches", f"matched product launch keyword '{kw}'")

    # Priority 10 — Geopolitical (conflict keyword required — a bare
    # country/region name like "israel" is not enough on its own,
    # since that also shows up in ordinary political questions)
    for conflict_kw in GEOPOLITICAL_CONFLICT_KEYWORDS:
        if _contains_keyword(combined, conflict_kw):
            return ("Geopolitical", f"matched geopolitical conflict keyword '{conflict_kw}'")

    # Priority 11 — Political
    for kw in POLITICAL_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Political", f"matched political keyword '{kw}'")

    # Priority 12 — Macro/Economic
    for kw in MACRO_KEYWORDS:
        if _contains_keyword(combined, kw):
            return ("Macro/Economic", f"matched macro keyword '{kw}'")

    # Priority 13 — Geopolitical region name alone, with no conflict
    # keyword and no political/macro match either. Lower priority
    # than Political/Macro on purpose.
    for region_kw in GEOPOLITICAL_REGION_KEYWORDS:
        if _contains_keyword(combined, region_kw):
            return ("Geopolitical", f"matched geopolitical region keyword '{region_kw}' (no other category matched)")

    # Fallback — nothing matched
    return ("Other/Unknown", "no keyword or slug pattern matched")


# ── Function 3 ─────────────────────────────────────────────────────────────

def determine_duration_type(slug: str, days_left) -> str:
    """
    Assign a duration bucket independent of category.

    Receives:
        slug (str): the market's URL slug
        days_left (float or None): days remaining until resolution

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
        category (str): one of the defined categories

    Returns:
        bool or str: True, False, or "Review"
    """
    return INCLUSION_POLICY.get(category, "Review")


# ── Function 4b (NEW) ────────────────────────────────────────────────────────

def get_category_tier(category: str) -> str:
    """
    Look up which tier a category belongs to.

    Receives:
        category (str): one of the defined categories

    Returns:
        str: "Active Research", "Research Queue", or "Excluded"
    """
    return CATEGORY_TIERS.get(category, "Research Queue")


# ── Function 5 ─────────────────────────────────────────────────────────────

def classify_market(market: dict) -> dict:
    """
    Main orchestrator. Classifies a single market record.

    Receives:
        market (dict): must contain 'title' (or 'question') and 'slug'.
                        May optionally contain 'days_left'.

    Returns:
        dict: matches the standard output schema:
              market_title, market_slug, category, category_tier,
              duration_type, include_in_wallet_research,
              classification_reason
    """
    title = market.get("title") or market.get("question") or "Unknown"
    slug = market.get("slug") or ""
    days_left = market.get("days_left")  # may be None if not provided

    category, reason = classify_category(title, slug)
    category_tier = get_category_tier(category)
    duration_type = determine_duration_type(slug, days_left)
    include = get_research_inclusion(category)

    return {
        "market_title": title,
        "market_slug": slug,
        "category": category,
        "category_tier": category_tier,
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
    {
        "title": "Will the FDA approve the new weight loss drug by Q3 2026?",
        "slug": "fda-approval-weightloss-q3-2026",
        "days_left": 90,
    },
    {
        "title": "Will Apple announce a new product launch event in September?",
        "slug": "apple-product-launch-sept",
        "days_left": 85,
    },
    {
        "title": "Will the Supreme Court ruling on tariffs come before August?",
        "slug": "supreme-court-ruling-tariffs",
        "days_left": 50,
    },
    {
        "title": "Will Tesla report a CEO resigns announcement this quarter?",
        "slug": "tesla-ceo-resigns-q3",
        "days_left": 60,
    },
]


def run_test():
    """Run the classifier against known example markets and print results."""
    console.print("\n[bold cyan]Liquid Research — Market Classifier Test[/bold cyan]")
    console.print(f"[dim]Testing classifier against {len(EXAMPLE_MARKETS)} known example markets...[/dim]\n")

    results_df = classify_markets_batch(EXAMPLE_MARKETS)

    table = Table(show_lines=True)
    table.add_column("#", width=3)
    table.add_column("Market Title", max_width=32)
    table.add_column("Category", style="cyan")
    table.add_column("Tier", style="magenta")
    table.add_column("Duration", style="yellow")
    table.add_column("Include", justify="center")
    table.add_column("Reason", style="dim", max_width=30)

    for i, row in results_df.iterrows():
        include_val = row["include_in_wallet_research"]
        if include_val is True:
            include_display = "[green]True[/green]"
        elif include_val is False:
            include_display = "[red]False[/red]"
        else:
            include_display = "[yellow]Review[/yellow]"

        tier = row["category_tier"]
        if tier == "Active Research":
            tier_display = "[green]Active[/green]"
        elif tier == "Research Queue":
            tier_display = "[yellow]Queue[/yellow]"
        else:
            tier_display = "[red]Excluded[/red]"

        title_short = row["market_title"][:30] + ("..." if len(row["market_title"]) > 30 else "")

        table.add_row(
            str(i + 1),
            title_short,
            row["category"],
            tier_display,
            row["duration_type"],
            include_display,
            row["classification_reason"],
        )

    console.print(table)

    total = len(results_df)
    category_counts = results_df["category"].value_counts().to_dict()
    tier_counts = results_df["category_tier"].value_counts().to_dict()
    excluded = (results_df["include_in_wallet_research"] == False).sum()
    review = (results_df["include_in_wallet_research"] == "Review").sum()

    console.print(f"\n[bold green]Test complete:[/bold green] {total}/{total} markets classified")

    category_summary = ", ".join(f"{cat} ({count})" for cat, count in category_counts.items())
    console.print(f"Categories found: {category_summary}")

    tier_summary = ", ".join(f"{tier} ({count})" for tier, count in tier_counts.items())
    console.print(f"Tiers found: {tier_summary}")

    console.print(f"Excluded from wallet research: [red]{excluded}[/red]")
    console.print(f"Flagged for review: [yellow]{review}[/yellow]\n")


if __name__ == "__main__":
    run_test()