"""
Program B — Market Microstructure Research
Weekly Review Packaging
programs/program_b/presentation/weekly_review.py

PURPOSE:
Assemble existing evidence from every known market into one
readable review artifact. This is Phase 3's third item.

This module contains NO new analysis logic beyond trivial
dataset-level counts and min/max of existing timestamps. It does
NOT compute new statistics, does NOT classify markets, does NOT
rank, recommend, or interpret. It packages evidence that already
exists — every value in this document is pulled directly from
build_market_observation_index(), build_market_report(), or
build_agreement_matrix(), never recomputed. Presentation formatting
belongs here rather than in analysis modules so computation and
presentation remain separate responsibilities.

This module reads no CSVs and creates no new logs. It calls
build_market_observation_index(), build_market_report(),
build_agreement_matrix(), format_stability_table(), and
format_agreement_matrix_table() exclusively.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from programs.program_b.analysis.recurring_markets import build_market_observation_index
from programs.program_b.analysis.market_report import build_market_report
from programs.program_b.analysis.agreement_matrix import build_agreement_matrix
from programs.program_b.presentation.report_printer import format_stability_table, format_agreement_matrix_table


def _render_dataset_summary(index_df: pd.DataFrame) -> str:
    """
    Render the dataset summary section: trivial counts and
    min/max of timestamps already present in the observation index.

    Receives:
        index_df (pd.DataFrame): output of
        build_market_observation_index().

    Returns:
        str: formatted section text.
    """
    total_markets = len(index_df)
    total_observations = int(index_df["observation_count"].sum()) if total_markets > 0 else 0

    earliest = index_df["first_seen"].dropna().min() if total_markets > 0 else None
    latest = index_df["last_seen"].dropna().max() if total_markets > 0 else None

    lines = [
        "--- 1. DATASET SUMMARY ---",
        f"Total known markets: {total_markets}",
        f"Total observations (all sources): {total_observations}",
        f"Earliest observation: {earliest if earliest is not None else '—'}",
        f"Latest observation: {latest if latest is not None else '—'}",
    ]
    return "\n".join(lines)


def _render_observation_index(index_df: pd.DataFrame) -> str:
    """
    Render the full observation index as a plain text table.

    Receives:
        index_df (pd.DataFrame): output of
        build_market_observation_index(), already sorted.

    Returns:
        str: formatted section text.
    """
    lines = ["--- 2. OBSERVATION INDEX ---"]
    if index_df.empty:
        lines.append("No markets observed yet.")
        return "\n".join(lines)

    display_cols = [
        "slug", "observation_count", "snapshot_count",
        "days_observed", "sources_present", "last_seen",
    ]
    lines.append(index_df[display_cols].to_string(index=False))
    return "\n".join(lines)


def _render_missing_source_section(index_df: pd.DataFrame) -> str:
    """
    Render markets whose sources_present does not include both
    "obi" and "near_book" — a filtered view of the observation
    index, no new computation.

    Receives:
        index_df (pd.DataFrame): output of
        build_market_observation_index().

    Returns:
        str: formatted section text.
    """
    lines = ["--- 3. MARKETS MISSING ONE SOURCE ---"]

    if index_df.empty:
        lines.append("No markets observed yet.")
        return "\n".join(lines)

    missing = index_df[~index_df["sources_present"].str.contains("obi") |
                        ~index_df["sources_present"].str.contains("near_book")]

    if missing.empty:
        lines.append("All known markets have both OBI and Near-Book observations.")
        return "\n".join(lines)

    for _, row in missing.iterrows():
        missing_source = "near_book" if "obi" in row["sources_present"] else "obi"
        lines.append(f"{row['slug']} — missing: {missing_source}")

    return "\n".join(lines)


def _render_divergence_summary(index_df: pd.DataFrame, reports: dict) -> str:
    """
    Render a compact, one-row-per-market divergence summary:
    slug | has_comparable_pair | raw_diff | absolute_diff | sign_flip.

    Full divergence detail already appears in the per-market
    section below — this section is deliberately compact. This
    section reflects the LATEST observation per market only. See
    Section 6 (Agreement Matrix) for the historical view across
    every matched snapshot_file.

    Receives:
        index_df (pd.DataFrame): output of
        build_market_observation_index(), used only for slug order.
        reports (dict): slug -> build_market_report(slug) output,
        built once by the caller and reused here to avoid
        recomputing each report.

    Returns:
        str: formatted section text.
    """
    lines = [
        "--- 4. CURRENT DIVERGENCE SUMMARY ---",
        f"{'slug':<45}{'pair?':>7}{'raw_diff':>11}{'abs_diff':>11}{'sign_flip':>11}",
    ]

    for slug in index_df["slug"]:
        div = reports[slug]["current_divergence"]

        has_pair = div["has_comparable_pair"]
        raw_diff = div["raw_diff"] if div["raw_diff"] is not None else "—"
        abs_diff = div["absolute_diff"] if div["absolute_diff"] is not None else "—"
        sign_flip = div["sign_flip"] if div["sign_flip"] is not None else "—"

        lines.append(f"{slug:<45}{str(has_pair):>7}{str(raw_diff):>11}{str(abs_diff):>11}{str(sign_flip):>11}")

    return "\n".join(lines)


def _render_per_market_section(index_df: pd.DataFrame, reports: dict) -> str:
    """
    Render full per-market detail: question, stability table,
    latest change per source, and current divergence detail.

    Receives:
        index_df (pd.DataFrame): output of
        build_market_observation_index(), used for slug order.
        reports (dict): slug -> build_market_report(slug) output,
        built once by the caller and reused here to avoid
        recomputing each report.

    Returns:
        str: formatted section text.
    """
    lines = ["--- 5. PER-MARKET DETAIL ---"]

    for slug in index_df["slug"]:
        report = reports[slug]

        lines.append("")
        lines.append(f"---- {slug} ----")
        lines.append(f"Question: {report['question'] if report['question'] else '—'}")

        if report["observation_summary"]["missing_source_warning"]:
            lines.append(f"Warning: {report['observation_summary']['missing_source_warning']}")

        lines.append("")
        lines.append(format_stability_table(report["stability"]))

        lines.append("")
        obi_change = report["latest_change"]["obi"]
        near_change = report["latest_change"]["near_book"]
        lines.append(f"Latest change (OBI): has_change={obi_change['has_change']}, "
                      f"midpoint_delta={obi_change['midpoint_delta']}, obi_delta={obi_change.get('obi_delta')}")
        lines.append(f"Latest change (Near-Book): has_change={near_change['has_change']}, "
                      f"midpoint_delta={near_change['midpoint_delta']}, near_obi_delta={near_change.get('near_obi_delta')}")

        div = report["current_divergence"]
        lines.append(f"Current divergence: has_comparable_pair={div['has_comparable_pair']}, "
                      f"raw_diff={div['raw_diff']}, absolute_diff={div['absolute_diff']}, sign_flip={div['sign_flip']}")

    return "\n".join(lines)


def build_weekly_review() -> str:
    """
    Assemble the full Weekly Review Packaging document across every
    known market. See module docstring for full scope and
    constraints.

    Builds each market's report exactly once and reuses it across
    all sections that need it, avoiding duplicated computation.
    Builds the agreement matrix exactly once as well.

    Returns:
        str: the complete, human-readable weekly review document.
    """
    index_df = build_market_observation_index()

    reports = {
        slug: build_market_report(slug)
        for slug in index_df["slug"]
    }

    agreement_matrix_df = build_agreement_matrix()

    sections = [
        "=" * 64,
        "PROGRAM B — WEEKLY REVIEW",
        "=" * 64,
        "",
        _render_dataset_summary(index_df),
        "",
        _render_observation_index(index_df),
        "",
        _render_missing_source_section(index_df),
        "",
        _render_divergence_summary(index_df, reports),
        "",
        _render_per_market_section(index_df, reports),
        "",
        "--- 6. AGREEMENT MATRIX (HISTORICAL, ALL MATCHED SNAPSHOTS) ---",
        format_agreement_matrix_table(agreement_matrix_df),
        "",
        "=" * 64,
        "END OF REVIEW",
        "=" * 64,
    ]

    return "\n".join(sections)


if __name__ == "__main__":
    print(build_weekly_review())