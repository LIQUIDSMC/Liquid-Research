"""
LRS-2 — Market Microstructure Research
Forward Midpoint Study B

Frozen Study-B temporal replication wrapper.

Study B carries forward the frozen Study-A scientific and numerical
specification unchanged except for the prospectively frozen requirement that
both the anchor OBI timestamp and its immediately next canonical same-slug OBI
outcome timestamp are strictly later than the Study-A OBI evidence boundary.

The complete canonical OBI sequence is retained while identifying the
immediately next observation. This module does not pre-filter that sequence in
a way that could skip an observation and alter the frozen forward rule.

No production trading interpretation, CP18 trigger, or LRS-1 integration is
implied.
"""

from __future__ import annotations

import pandas as pd

from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_a import (
    ClusteredOLSResult,
    StudyAError,
    attach_frozen_forward_outcomes,
    build_eligible_anchors,
    canonicalize_near,
    canonicalize_obi,
    fit_frozen_clustered_ols,
    secondary_same_direction,
)


STUDY_A_OBI_EVIDENCE_BOUNDARY = pd.Timestamp("2026-10-06T12:03:13Z")


def run_study_b_from_frames(
    obi_df: pd.DataFrame,
    near_df: pd.DataFrame,
) -> tuple[pd.DataFrame, ClusteredOLSResult]:
    """
    Run frozen Study B from already-supplied DataFrames.

    The full canonical OBI sequence is preserved for immediate-next lookup.
    Candidate anchors must be strictly post-boundary before outcomes are
    attached, and the resulting immediate-next OBI observation must also be
    strictly post-boundary.

    This function performs no file discovery or live-data access.
    """

    canonical_obi = canonicalize_obi(obi_df)
    canonical_near = canonicalize_near(near_df)

    anchors = build_eligible_anchors(
        canonical_obi,
        canonical_near,
    )

    anchors = anchors.loc[
        anchors["obi_timestamp"] > STUDY_A_OBI_EVIDENCE_BOUNDARY
    ].copy()

    eligible = attach_frozen_forward_outcomes(
        anchors,
        canonical_obi,
    )

    eligible = eligible.loc[
        eligible["next_obi_timestamp"] > STUDY_A_OBI_EVIDENCE_BOUNDARY
    ].copy()

    eligible = eligible.reset_index(drop=True)

    eligible["secondary_same_direction"] = [
        secondary_same_direction(float(obi), float(change))
        for obi, change in zip(
            eligible["obi_t"],
            eligible["future_midpoint_change"],
            strict=True,
        )
    ]

    result = fit_frozen_clustered_ols(eligible)
    return eligible, result
