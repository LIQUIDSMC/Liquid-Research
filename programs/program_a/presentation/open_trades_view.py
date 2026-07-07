"""
Program A — Tradeability Score / Scanner One
Open Trades View
programs/program_a/presentation/open_trades_view.py

PURPOSE:
Presentation-only terminal view of currently open Program A trades,
sorted by best-effort parsed deadline. This module does NOT modify
paper_trades.csv, does NOT add any permanent field to the trade
data, and does NOT imply a parsed deadline is verified or official.
parsed_deadline exists only inside this view, computed fresh each
time from the question text.

PARSING PRECISION:
Deadlines are labeled "exact" or "approximate":
    exact: a specific calendar date was stated in the question
           (e.g. "by July 15", "by December 31, 2026")
    approximate: only a year or month was stated, and a specific
           day was inferred (e.g. "before 2027" -> Jan 1 of that
           year; "end of 2026" -> Dec 31 of that year)

Season-style phrasing (e.g. "in 2026-27") is deliberately left
unparsed — forcing a single date out of a season range would
misrepresent what the market actually says.

If no recognizable pattern is found at all, the trade is shown
with "no parsed deadline" rather than a guess.
"""

import re
import pandas as pd
from datetime import datetime
import calendar

TRADES_PATH = "data/simulator/paper_trades.csv"

MONTH_NAMES = (
    "January|February|March|April|May|June|July|"
    "August|September|October|November|December"
)


def _last_day_of_month(year: int, month: int) -> datetime:
    """
    Return the last calendar day of the given month/year.

    Receives:
        year (int)
        month (int)

    Returns:
        datetime: the last day of that month.
    """
    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, last_day)


def _parse_deadline(question: str) -> tuple:
    """
    Best-effort parse of a deadline from a market question's text.

    Receives:
        question (str): the full question text.

    Returns:
        tuple: (datetime or None, precision str or None)
        precision is "exact", "approximate", or None if no pattern
        matched at all. Season-style phrasing (e.g. "2026-27") is
        deliberately never matched — left unparsed.
    """
    if not isinstance(question, str):
        return None, None

    # EXACT: "by Month Day, Year"
    match = re.search(rf"by ({MONTH_NAMES}) (\d{{1,2}}), (\d{{4}})", question)
    if match:
        month_name, day, year = match.group(1), int(match.group(2)), int(match.group(3))
        try:
            return datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y"), "exact"
        except ValueError:
            pass

    # EXACT: "by Month Day" (no year stated — assume current year)
    # (?!,) prevents this from matching a truncated portion of a
    # fuller "by Month Day, Year" phrase if the exact pattern above
    # ever fails to match for some reason.
    match = re.search(rf"by ({MONTH_NAMES}) (\d{{1,2}})\b(?!,)", question)
    if match:
        month_name, day = match.group(1), int(match.group(2))
        year = datetime.now().year
        try:
            return datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y"), "exact"
        except ValueError:
            pass

    # APPROXIMATE: "before Year" -> Jan 1 of that year
    match = re.search(r"before (\d{4})", question)
    if match:
        year = int(match.group(1))
        return datetime(year, 1, 1), "approximate"

    # APPROXIMATE: "by end of Year" or "end of Year" -> Dec 31 of that year
    match = re.search(r"(?:by )?end of (\d{4})", question)
    if match:
        year = int(match.group(1))
        return datetime(year, 12, 31), "approximate"

    # APPROXIMATE: "after the Month Year meeting" -> last day of that month
    match = re.search(rf"after the ({MONTH_NAMES}) (\d{{4}}) meeting", question)
    if match:
        month_name, year = match.group(1), int(match.group(2))
        month_num = list(calendar.month_name).index(month_name)
        return _last_day_of_month(year, month_num), "approximate"

    # APPROXIMATE: "in Month" (only if no stronger pattern matched above)
    # deliberately excludes season-style "2026-27" — this pattern
    # only matches a bare month name, not a year range.
    match = re.search(rf"in ({MONTH_NAMES})\b", question)
    if match:
        month_name = match.group(1)
        year = datetime.now().year
        month_num = list(calendar.month_name).index(month_name)
        return _last_day_of_month(year, month_num), "approximate"

    return None, None


def build_open_trades_view() -> str:
    """
    Build a plain text, terminal-friendly view of all currently
    open Program A trades, sorted by best-effort parsed deadline
    (ascending, missing deadlines last).

    Returns:
        str: the complete formatted view.
    """
    df = pd.read_csv(TRADES_PATH)
    open_trades = df[df["status"] == "open"].copy()

    parsed = open_trades["question"].apply(_parse_deadline)
    open_trades["parsed_deadline"] = parsed.apply(lambda x: x[0])
    open_trades["deadline_precision"] = parsed.apply(lambda x: x[1])

    open_trades = open_trades.sort_values(
        by="parsed_deadline", ascending=True, na_position="last"
    )

    lines = [f"=== OPEN TRADES ({len(open_trades)}) — sorted by parsed deadline ===", ""]

    for _, row in open_trades.iterrows():
        if pd.notna(row["parsed_deadline"]):
            date_str = row["parsed_deadline"].strftime("%Y-%m-%d")
            precision = row["deadline_precision"]
            header = f"[{date_str}, {precision}]  {row['category']}"
        else:
            header = f"[no parsed deadline]  {row['category']}"

        lines.append(header)
        lines.append(f"  {row['question']}")
        lines.append(f"  Side: {row['side']} @ {row['entry_price']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print(build_open_trades_view())