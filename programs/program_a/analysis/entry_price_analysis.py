"""
Program A — Tradeability Score / Scanner One
Entry Price Analysis
programs/program_a/analysis/entry_price_analysis.py

PURPOSE:
Reusable research report investigating whether entry_price may be
confounding the observed relationship between tradeability_score
and paper-trade outcomes. This question was raised during the
original median-split analysis (n=32) and never directly tested.

This is a descriptive report only. It does NOT compute regression,
does NOT report p-values, and does NOT make causal claims. At
small sample sizes, correlation coefficients and median splits are
highly sensitive to individual outlier trades — this report
explicitly discloses that risk rather than hiding it.

This script is designed to be reusable, not a one-time analysis.
It should be re-run as more trades close (e.g. at n=100, n=250) to
see whether the relationship changes.

Reads data/simulator/paper_trades.csv. Does NOT modify it.
No scanner, filter, or scorer logic is touched by this module.

DEPENDENCY NOTE: Spearman correlation is computed manually (Pearson
correlation applied to ranked values) rather than via
pandas.Series.corr(method="spearman"), since that method requires
scipy internally, which is not installed in this environment.
Pearson correlation uses pandas' native corr(), which has no scipy
dependency.
"""

import pandas as pd
from datetime import datetime

TRADES_PATH = "data/simulator/paper_trades.csv"

OUTLIER_TOP_N = 3

INTERPRETATION_THRESHOLD = 0.2


def _load_closed_trades() -> pd.DataFrame:
    """
    Load and filter to closed trades only.

    Returns:
        pd.DataFrame: closed trades.
    """
    df = pd.read_csv(TRADES_PATH)
    return df[df["status"] == "closed"].copy()


def _spearman_correlation(series_a: pd.Series, series_b: pd.Series) -> float:
    """
    Compute Spearman rank correlation manually: Pearson correlation
    applied to the ranked values of each series. Avoids requiring
    scipy, which pandas' built-in method="spearman" depends on
    internally.

    Receives:
        series_a (pd.Series)
        series_b (pd.Series)

    Returns:
        float: Spearman correlation coefficient.
    """
    ranked_a = series_a.rank()
    ranked_b = series_b.rank()
    return ranked_a.corr(ranked_b, method="pearson")


def _render_dataset_section(closed: pd.DataFrame) -> str:
    """
    Render the Dataset section: closed trade count and run date.

    Receives:
        closed (pd.DataFrame): closed trades.

    Returns:
        str: formatted section text.
    """
    lines = [
        "-" * 52,
        "Dataset",
        "-" * 52,
        f"Closed trades: {len(closed)}",
        f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]
    return "\n".join(lines)


def _compute_score_vs_price(closed: pd.DataFrame) -> tuple:
    """
    Compute Pearson and Spearman correlation between
    tradeability_score_at_entry and entry_price.

    Receives:
        closed (pd.DataFrame): closed trades.

    Returns:
        tuple: (pearson_r, spearman_r)
    """
    scores = closed["tradeability_score_at_entry"]
    prices = closed["entry_price"]

    pearson_r = scores.corr(prices, method="pearson")
    spearman_r = _spearman_correlation(scores, prices)

    return pearson_r, spearman_r


def _render_score_vs_price_section(closed: pd.DataFrame, pearson_r: float, spearman_r: float) -> str:
    """
    Render Section 1: Score vs Entry Price correlation.

    Receives:
        closed (pd.DataFrame): closed trades.
        pearson_r (float): precomputed Pearson correlation.
        spearman_r (float): precomputed Spearman correlation.

    Returns:
        str: formatted section text.
    """
    lines = [
        "",
        "-" * 52,
        "1. Score vs Entry Price",
        "-" * 52,
        f"Pearson correlation:  {pearson_r:.4f}",
        f"Spearman correlation: {spearman_r:.4f}",
        "",
        f"Warning: n={len(closed)} is small. Correlation coefficients",
        "at this sample size can shift substantially due to a single",
        "outlier trade. Treat these numbers as directional only.",
    ]
    return "\n".join(lines)


def _render_interpretation_note(pearson_r: float, spearman_r: float) -> str:
    """
    Render an Interpretation Note section based on the computed
    Score vs Entry Price correlation values. States a fact-based
    observation only — no regression, no p-values, no causal claim.

    Receives:
        pearson_r (float)
        spearman_r (float)

    Returns:
        str: formatted section text.
    """
    lines = [
        "",
        "-" * 52,
        "Interpretation Note",
        "-" * 52,
    ]

    if abs(pearson_r) < INTERPRETATION_THRESHOLD and abs(spearman_r) < INTERPRETATION_THRESHOLD:
        lines.append(
            f"Both Pearson ({pearson_r:.4f}) and Spearman ({spearman_r:.4f}) "
            f"are below {INTERPRETATION_THRESHOLD} in absolute value."
        )
        lines.append("Score and entry_price show weak correlation at this checkpoint.")
        lines.append("This run does NOT confirm entry_price as the explanation for")
        lines.append("any observed score/outcome differences.")
    else:
        lines.append(
            f"Pearson ({pearson_r:.4f}) or Spearman ({spearman_r:.4f}) is "
            f"{INTERPRETATION_THRESHOLD} or greater in absolute value."
        )
        lines.append("Score and entry_price show a non-trivial relationship at this")
        lines.append("checkpoint, consistent with entry_price potentially acting as")
        lines.append("a confound. This does not establish causation.")

    lines.append("")
    lines.append("Still descriptive only — n is small, see Dataset section.")

    return "\n".join(lines)


def _render_outcome_split_section(
    closed: pd.DataFrame, split_column: str, section_title: str, section_number: int
) -> str:
    """
    Render a median-split outcome section for a given column
    (either entry_price or tradeability_score_at_entry).

    Receives:
        closed (pd.DataFrame): closed trades.
        split_column (str): column name to split on.
        section_title (str): human-readable title for this section.
        section_number (int): section number for the header.

    Returns:
        str: formatted section text.
    """
    median_val = closed[split_column].median()

    low_group = closed[closed[split_column] < median_val]
    high_group = closed[closed[split_column] >= median_val]

    lines = [
        "",
        "-" * 52,
        f"{section_number}. {section_title}",
        "-" * 52,
        f"Median {split_column}: {median_val:.4f}",
        "Split rule: values >= median assigned to HIGH group.",
        "",
    ]

    for label, group in [("Low", low_group), ("High", high_group)]:
        n = len(group)
        if n == 0:
            lines.append(f"{label} group: n=0 (no trades)")
            lines.append("")
            continue

        win_rate = (group["trade_won"] == True).sum() / n * 100
        avg_pnl = group["trade_pnl"].mean()
        median_pnl = group["trade_pnl"].median()

        lines.append(f"{label} group:")
        lines.append(f"  n = {n}")
        lines.append(f"  Win rate: {win_rate:.1f}%")
        lines.append(f"  Average P&L: ${avg_pnl:.2f}")
        lines.append(f"  Median P&L: ${median_pnl:.2f}")
        lines.append("")

    return "\n".join(lines)


def _render_outlier_section(closed: pd.DataFrame) -> str:
    """
    Render the Outlier Review section: top N trades by absolute
    P&L magnitude, and what percent of total realized P&L they
    represent.

    Receives:
        closed (pd.DataFrame): closed trades.

    Returns:
        str: formatted section text.
    """
    total_pnl = closed["trade_pnl"].sum()

    top_n = closed.reindex(
        closed["trade_pnl"].abs().sort_values(ascending=False).index
    ).head(OUTLIER_TOP_N)

    top_n_pnl_sum = top_n["trade_pnl"].sum()
    pct_of_total = (top_n_pnl_sum / total_pnl * 100) if total_pnl != 0 else None

    lines = [
        "",
        "-" * 52,
        "5. Outlier Review",
        "-" * 52,
        f"Top {OUTLIER_TOP_N} trades by absolute P&L magnitude:",
        "",
    ]

    for _, row in top_n.iterrows():
        lines.append(f"  {row['question']}")
        lines.append(
            f"    entry_price={row['entry_price']:.4f}  "
            f"score={row['tradeability_score_at_entry']:.2f}  "
            f"P&L=${row['trade_pnl']:.2f}"
        )
        lines.append("")

    if pct_of_total is not None:
        lines.append(
            f"Top {OUTLIER_TOP_N} absolute-P&L trades have combined P&L of "
            f"${top_n_pnl_sum:.2f}, equal to {pct_of_total:.1f}% of total "
            f"realized P&L (${total_pnl:.2f})."
        )
    else:
        lines.append("Total realized P&L is $0.00 — percent-of-total is undefined.")

    return "\n".join(lines)


def _render_conclusions_section() -> str:
    """
    Render the Conclusions / Limitations section.

    Returns:
        str: formatted section text.
    """
    lines = [
        "",
        "-" * 52,
        "6. Conclusions / Limitations",
        "-" * 52,
        "This report is descriptive only. No causal inference is",
        "made or implied by any correlation, split, or outlier shown",
        "above.",
        "",
        "Limitations:",
        "  - Sample size is small (see Dataset section).",
        "  - Correlation and median-split results can shift",
        "    substantially as more trades close.",
        "  - This report should be re-run periodically (e.g. at the",
        "    next milestone: 100 closed trades) rather than treated",
        "    as a final answer.",
    ]
    return "\n".join(lines)


def build_entry_price_report() -> str:
    """
    Build the complete Entry Price Analysis report.

    Returns:
        str: the full formatted report.
    """
    closed = _load_closed_trades()

    pearson_r, spearman_r = _compute_score_vs_price(closed)

    sections = [
        "PROGRAM A",
        "Entry Price Research Report",
        "",
        _render_dataset_section(closed),
        _render_score_vs_price_section(closed, pearson_r, spearman_r),
        _render_interpretation_note(pearson_r, spearman_r),
        _render_outcome_split_section(closed, "entry_price", "Entry Price vs Outcome", 2),
        _render_outcome_split_section(closed, "tradeability_score_at_entry", "Tradeability Score vs Outcome", 3),
        _render_outlier_section(closed),
        _render_conclusions_section(),
    ]

    return "\n".join(sections)


if __name__ == "__main__":
    print(build_entry_price_report())