"""
LRS-2 — Market Microstructure Research
Forward Midpoint Study A

Frozen Study-A implementation.

This module implements the prospectively frozen Study-A methodology for testing
whether continuous full-book OBI at T is associated with the signed change in
market midpoint at the immediately next canonical publication-level OBI
observation, when that next observation occurs 18–30 hours after T.

This module does not select alternate horizons, thresholds, transformations,
market subsets, covariance estimators, or fallback inference procedures.

The primary estimator is:

    future_midpoint_change = intercept + beta * obi_t + error

with one-way cluster-robust covariance by canonical market slug, the frozen CR1
finite-sample correction, and Student-t inference with G - 1 degrees of freedom.

No production trading interpretation or LRS-1 integration is implied.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


PAIR_TOLERANCE_SECONDS = 120.0
MIN_FORWARD_HOURS = 18.0
MAX_FORWARD_HOURS = 30.0
ALPHA = 0.05
K_PARAMETERS = 2

OBI_REQUIRED_COLUMNS = {
    "timestamp",
    "publication_id",
    "slug",
    "midpoint",
    "obi",
    "status",
}

NEAR_REQUIRED_COLUMNS = {
    "timestamp",
    "publication_id",
    "slug",
    "midpoint",
    "near_obi",
    "status",
}


class StudyAError(RuntimeError):
    """Raised when the frozen Study-A analysis cannot be validly computed."""


@dataclass(frozen=True)
class ClusteredOLSResult:
    """Frozen primary Study-A regression result."""

    intercept: float
    beta: float
    clustered_se_beta: float
    beta_ci_95_low: float
    beta_ci_95_high: float
    beta_p_value_two_sided: float
    eligible_n: int
    slug_clusters: int


def _require_columns(
    df: pd.DataFrame,
    required: set[str],
    source_name: str,
) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise StudyAError(
            f"{source_name} is missing required columns: {', '.join(missing)}"
        )


def _canonicalize_source(
    df: pd.DataFrame,
    required: set[str],
    source_name: str,
) -> pd.DataFrame:
    """
    Return latest valid row per (slug, publication_id), ordered chronologically.

    A valid row must contain all frozen fields required from that source and a
    parseable timestamp. No nearest-timestamp or other pairing heuristic is
    applied here.
    """
    _require_columns(df, required, source_name)

    work = df.copy()

    work["timestamp"] = pd.to_datetime(
        work["timestamp"],
        utc=True,
        errors="coerce",
    )

    validity_columns = sorted(required - {"status"})
    valid = (
        work["status"].astype(str).str.lower().eq("ok")
        & work["timestamp"].notna()
        & work[validity_columns].notna().all(axis=1)
    )
    work = work.loc[valid].copy()

    if work.empty:
        return work.reset_index(drop=True)

    for column in ("midpoint",):
        work[column] = pd.to_numeric(work[column], errors="coerce")

    if source_name == "OBI":
        work["obi"] = pd.to_numeric(work["obi"], errors="coerce")
        numeric_columns = ["midpoint", "obi"]
    else:
        work["near_obi"] = pd.to_numeric(work["near_obi"], errors="coerce")
        numeric_columns = ["midpoint", "near_obi"]

    work = work.dropna(subset=numeric_columns).copy()

    if work.empty:
        return work.reset_index(drop=True)

    numeric = work[numeric_columns].to_numpy(dtype=float)
    finite_mask = np.isfinite(numeric).all(axis=1)
    work = work.loc[finite_mask].copy()

    # Stable ordering makes duplicate-key latest-row selection deterministic
    # when source rows are already in real observation order.
    work["_source_order"] = np.arange(len(work), dtype=np.int64)
    work = work.sort_values(
        ["timestamp", "_source_order"],
        kind="stable",
    )

    work = work.drop_duplicates(
        subset=["slug", "publication_id"],
        keep="last",
    )

    work = work.sort_values(
        ["slug", "timestamp", "publication_id"],
        kind="stable",
    ).reset_index(drop=True)

    return work.drop(columns=["_source_order"])


def canonicalize_obi(obi_df: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize OBI under the frozen latest-row-per-key rule."""
    return _canonicalize_source(
        obi_df,
        OBI_REQUIRED_COLUMNS,
        "OBI",
    )


def canonicalize_near(near_df: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize Near-Book observations under the frozen rule."""
    return _canonicalize_source(
        near_df,
        NEAR_REQUIRED_COLUMNS,
        "Near-Book",
    )


def build_eligible_anchors(
    canonical_obi: pd.DataFrame,
    canonical_near: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build contemporaneous Study-A anchors.

    Both canonical sources must exist for the same (slug, publication_id), and
    their timestamps must be separated by no more than 120 seconds inclusive.

    T and baseline midpoint are always taken from the OBI observation.
    """
    if canonical_obi.empty or canonical_near.empty:
        return pd.DataFrame(
            columns=[
                "slug",
                "publication_id",
                "obi_timestamp",
                "near_timestamp",
                "pair_offset_seconds",
                "anchor_midpoint",
                "obi_t",
                "near_obi_t",
            ]
        )

    obi = canonical_obi[
        ["slug", "publication_id", "timestamp", "midpoint", "obi"]
    ].rename(
        columns={
            "timestamp": "obi_timestamp",
            "midpoint": "anchor_midpoint",
            "obi": "obi_t",
        }
    )

    near = canonical_near[
        ["slug", "publication_id", "timestamp", "near_obi"]
    ].rename(
        columns={
            "timestamp": "near_timestamp",
            "near_obi": "near_obi_t",
        }
    )

    paired = obi.merge(
        near,
        on=["slug", "publication_id"],
        how="inner",
        validate="one_to_one",
    )

    paired["pair_offset_seconds"] = (
        paired["obi_timestamp"] - paired["near_timestamp"]
    ).abs().dt.total_seconds()

    paired = paired.loc[
        paired["pair_offset_seconds"] <= PAIR_TOLERANCE_SECONDS
    ].copy()

    return paired.sort_values(
        ["slug", "obi_timestamp", "publication_id"],
        kind="stable",
    ).reset_index(drop=True)


def attach_frozen_forward_outcomes(
    anchors: pd.DataFrame,
    canonical_obi: pd.DataFrame,
) -> pd.DataFrame:
    """
    Attach the frozen immediately-next OBI outcome.

    For each anchor, the target is the chronologically immediately next
    canonical OBI observation for the same slug. The anchor is eligible only
    when that next observation is 18–30 hours later, inclusive.

    An earlier next observation is never skipped in order to find a later row
    inside the window.
    """
    if anchors.empty:
        result = anchors.copy()
        for column in (
            "next_publication_id",
            "next_obi_timestamp",
            "next_obi_midpoint",
            "forward_hours",
            "future_midpoint_change",
        ):
            result[column] = pd.Series(dtype="object")
        return result

    obi = canonical_obi.sort_values(
        ["slug", "timestamp", "publication_id"],
        kind="stable",
    ).reset_index(drop=True)

    next_rows = obi[
        ["slug", "publication_id", "timestamp", "midpoint"]
    ].copy()
    next_rows["next_publication_id"] = next_rows.groupby(
        "slug",
        sort=False,
    )["publication_id"].shift(-1)
    next_rows["next_obi_timestamp"] = next_rows.groupby(
        "slug",
        sort=False,
    )["timestamp"].shift(-1)
    next_rows["next_obi_midpoint"] = next_rows.groupby(
        "slug",
        sort=False,
    )["midpoint"].shift(-1)

    next_rows = next_rows[
        [
            "slug",
            "publication_id",
            "next_publication_id",
            "next_obi_timestamp",
            "next_obi_midpoint",
        ]
    ]

    result = anchors.merge(
        next_rows,
        on=["slug", "publication_id"],
        how="left",
        validate="one_to_one",
    )

    result["forward_hours"] = (
        result["next_obi_timestamp"] - result["obi_timestamp"]
    ).dt.total_seconds() / 3600.0

    eligible = (
        result["next_obi_timestamp"].notna()
        & result["forward_hours"].between(
            MIN_FORWARD_HOURS,
            MAX_FORWARD_HOURS,
            inclusive="both",
        )
    )

    result = result.loc[eligible].copy()

    result["future_midpoint_change"] = (
        result["next_obi_midpoint"].astype(float)
        - result["anchor_midpoint"].astype(float)
    )

    return result.sort_values(
        ["slug", "obi_timestamp", "publication_id"],
        kind="stable",
    ).reset_index(drop=True)


def secondary_same_direction(obi_t: float, future_change: float) -> bool:
    """
    Frozen secondary descriptive direction diagnostic.

    Exact zero in either OBI or future midpoint change is neutral and therefore
    returns False.
    """
    if obi_t == 0 or future_change == 0:
        return False
    return (obi_t > 0) == (future_change > 0)


def fit_frozen_clustered_ols(eligible: pd.DataFrame) -> ClusteredOLSResult:
    """
    Fit the frozen Study-A OLS and one-way slug-clustered CR1 covariance.

    No alternative estimator or covariance fallback is permitted.
    """
    required = {"slug", "obi_t", "future_midpoint_change"}
    missing = sorted(required - set(eligible.columns))
    if missing:
        raise StudyAError(
            "eligible Study-A frame is missing required columns: "
            + ", ".join(missing)
        )

    frame = eligible[
        ["slug", "obi_t", "future_midpoint_change"]
    ].copy()

    if frame.isna().any().any():
        raise StudyAError("eligible Study-A regression frame contains null values")

    try:
        x_obi = frame["obi_t"].to_numpy(dtype=float)
        y = frame["future_midpoint_change"].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise StudyAError("Study-A regression values must be numeric") from exc

    if not np.isfinite(x_obi).all() or not np.isfinite(y).all():
        raise StudyAError("Study-A regression values must be finite")

    n = len(frame)
    k = K_PARAMETERS
    clusters = frame["slug"].astype(str).to_numpy()
    unique_clusters = pd.unique(clusters)
    g = len(unique_clusters)

    if g <= 1:
        raise StudyAError("frozen clustered inference requires G > 1")
    if n <= k:
        raise StudyAError("frozen clustered inference requires N > K")

    x = np.column_stack(
        [
            np.ones(n, dtype=float),
            x_obi,
        ]
    )

    if np.linalg.matrix_rank(x) != k:
        raise StudyAError("Study-A OLS design matrix is rank deficient")

    beta_hat, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta_hat

    xtx = x.T @ x
    try:
        bread = np.linalg.inv(xtx)
    except np.linalg.LinAlgError as exc:
        raise StudyAError("Study-A OLS cross-product matrix is singular") from exc

    meat = np.zeros((k, k), dtype=float)

    for cluster in unique_clusters:
        mask = clusters == cluster
        x_g = x[mask]
        u_g = residuals[mask]
        score_g = x_g.T @ u_g
        meat += np.outer(score_g, score_g)

    cr1 = (g / (g - 1.0)) * ((n - 1.0) / (n - k))
    covariance = cr1 * (bread @ meat @ bread)

    if not np.isfinite(covariance).all():
        raise StudyAError("clustered covariance is not finite")

    beta_variance = float(covariance[1, 1])
    if not np.isfinite(beta_variance) or beta_variance <= 0.0:
        raise StudyAError("clustered beta variance is not a finite positive value")

    se_beta = float(np.sqrt(beta_variance))
    if not np.isfinite(se_beta) or se_beta <= 0.0:
        raise StudyAError(
            "clustered beta standard error is not a finite positive value"
        )

    beta = float(beta_hat[1])
    intercept = float(beta_hat[0])
    t_stat = beta / se_beta
    df = g - 1

    p_value = float(2.0 * stats.t.sf(abs(t_stat), df=df))
    critical = float(stats.t.ppf(1.0 - ALPHA / 2.0, df=df))

    ci_low = beta - critical * se_beta
    ci_high = beta + critical * se_beta

    outputs = np.array(
        [intercept, beta, se_beta, p_value, critical, ci_low, ci_high],
        dtype=float,
    )
    if not np.isfinite(outputs).all():
        raise StudyAError("frozen Study-A regression produced non-finite output")

    return ClusteredOLSResult(
        intercept=intercept,
        beta=beta,
        clustered_se_beta=se_beta,
        beta_ci_95_low=float(ci_low),
        beta_ci_95_high=float(ci_high),
        beta_p_value_two_sided=p_value,
        eligible_n=n,
        slug_clusters=g,
    )


def run_study_a_from_frames(
    obi_df: pd.DataFrame,
    near_df: pd.DataFrame,
) -> tuple[pd.DataFrame, ClusteredOLSResult]:
    """
    Run frozen Study A from already-supplied DataFrames.

    This function intentionally performs no file discovery or live-data access.
    Callers must explicitly supply the two source frames.
    """
    canonical_obi = canonicalize_obi(obi_df)
    canonical_near = canonicalize_near(near_df)

    anchors = build_eligible_anchors(
        canonical_obi,
        canonical_near,
    )
    eligible = attach_frozen_forward_outcomes(
        anchors,
        canonical_obi,
    )

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
