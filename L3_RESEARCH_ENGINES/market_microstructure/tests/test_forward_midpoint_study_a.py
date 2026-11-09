import numpy as np
import pandas as pd
import pytest
from scipy import stats

from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_a import (
    StudyAError,
    attach_frozen_forward_outcomes,
    build_eligible_anchors,
    canonicalize_near,
    canonicalize_obi,
    fit_frozen_clustered_ols,
    secondary_same_direction,
)


def _obi_row(
    slug,
    publication_id,
    timestamp,
    midpoint,
    obi,
    status="ok",
):
    return {
        "timestamp": timestamp,
        "publication_id": publication_id,
        "slug": slug,
        "midpoint": midpoint,
        "obi": obi,
        "status": status,
    }


def _near_row(
    slug,
    publication_id,
    timestamp,
    midpoint,
    near_obi,
    status="ok",
):
    return {
        "timestamp": timestamp,
        "publication_id": publication_id,
        "slug": slug,
        "midpoint": midpoint,
        "near_obi": near_obi,
        "status": status,
    }



def test_canonicalization_uses_repository_ok_status_contract():
    obi = pd.DataFrame(
        [
            _obi_row("a", "p1", "2026-01-01T00:00:00Z", 0.40, 0.10, status="ok"),
            _obi_row("b", "p2", "2026-01-01T00:00:00Z", 0.50, 0.20, status="valid"),
        ]
    )

    result = canonicalize_obi(obi)

    assert len(result) == 1
    assert result.iloc[0]["slug"] == "a"
    assert result.iloc[0]["status"] == "ok"


def test_canonicalization_keeps_latest_valid_row_per_key():
    obi = pd.DataFrame(
        [
            _obi_row("a", "p1", "2026-01-01T00:00:00Z", 0.40, 0.10),
            _obi_row("a", "p1", "2026-01-01T00:01:00Z", 0.41, 0.20),
            _obi_row(
                "a",
                "p1",
                "2026-01-01T00:02:00Z",
                0.99,
                0.99,
                status="invalid",
            ),
        ]
    )

    result = canonicalize_obi(obi)

    assert len(result) == 1
    assert result.iloc[0]["midpoint"] == pytest.approx(0.41)
    assert result.iloc[0]["obi"] == pytest.approx(0.20)


def test_pairing_120_seconds_is_inclusive_and_over_120_is_rejected():
    obi = canonicalize_obi(
        pd.DataFrame(
            [
                _obi_row("a", "p1", "2026-01-01T00:00:00Z", 0.4, 0.1),
                _obi_row("b", "p1", "2026-01-01T00:00:00Z", 0.5, -0.2),
            ]
        )
    )
    near = canonicalize_near(
        pd.DataFrame(
            [
                _near_row("a", "p1", "2026-01-01T00:02:00Z", 0.4, 0.2),
                _near_row("b", "p1", "2026-01-01T00:02:01Z", 0.5, -0.3),
            ]
        )
    )

    anchors = build_eligible_anchors(obi, near)

    assert anchors["slug"].tolist() == ["a"]
    assert anchors.iloc[0]["pair_offset_seconds"] == pytest.approx(120.0)


def test_forward_window_18_and_30_hours_are_inclusive():
    obi = canonicalize_obi(
        pd.DataFrame(
            [
                _obi_row("a", "p1", "2026-01-01T00:00:00Z", 0.40, 0.1),
                _obi_row("a", "p2", "2026-01-01T18:00:00Z", 0.45, 0.2),
                _obi_row("b", "p1", "2026-01-01T00:00:00Z", 0.50, -0.1),
                _obi_row("b", "p2", "2026-01-02T06:00:00Z", 0.40, -0.2),
            ]
        )
    )
    near = canonicalize_near(
        pd.DataFrame(
            [
                _near_row("a", "p1", "2026-01-01T00:00:30Z", 0.40, 0.1),
                _near_row("b", "p1", "2026-01-01T00:00:30Z", 0.50, -0.1),
            ]
        )
    )

    anchors = build_eligible_anchors(obi, near)
    eligible = attach_frozen_forward_outcomes(anchors, obi)

    assert eligible["slug"].tolist() == ["a", "b"]
    assert eligible["forward_hours"].tolist() == pytest.approx([18.0, 30.0])


def test_immediate_next_observation_is_not_skipped():
    obi = canonicalize_obi(
        pd.DataFrame(
            [
                _obi_row("a", "p1", "2026-01-01T00:00:00Z", 0.40, 0.1),
                _obi_row("a", "p2", "2026-01-01T10:00:00Z", 0.42, 0.2),
                _obi_row("a", "p3", "2026-01-02T00:00:00Z", 0.50, 0.3),
            ]
        )
    )
    near = canonicalize_near(
        pd.DataFrame(
            [
                _near_row("a", "p1", "2026-01-01T00:00:20Z", 0.40, 0.1),
            ]
        )
    )

    anchors = build_eligible_anchors(obi, near)
    eligible = attach_frozen_forward_outcomes(anchors, obi)

    assert eligible.empty


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (17.999, False),
        (18.0, True),
        (30.0, True),
        (30.001, False),
    ],
)
def test_forward_window_boundaries(hours, expected):
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    end = start + pd.Timedelta(hours=hours)

    obi = canonicalize_obi(
        pd.DataFrame(
            [
                _obi_row("a", "p1", start.isoformat(), 0.4, 0.1),
                _obi_row("a", "p2", end.isoformat(), 0.5, 0.2),
            ]
        )
    )
    near = canonicalize_near(
        pd.DataFrame(
            [
                _near_row(
                    "a",
                    "p1",
                    (start + pd.Timedelta(seconds=30)).isoformat(),
                    0.4,
                    0.1,
                )
            ]
        )
    )

    anchors = build_eligible_anchors(obi, near)
    eligible = attach_frozen_forward_outcomes(anchors, obi)

    assert (not eligible.empty) is expected


def test_secondary_direction_treats_exact_zero_as_neutral():
    assert secondary_same_direction(1.0, 0.1) is True
    assert secondary_same_direction(-1.0, -0.1) is True
    assert secondary_same_direction(1.0, -0.1) is False
    assert secondary_same_direction(-1.0, 0.1) is False
    assert secondary_same_direction(0.0, 0.1) is False
    assert secondary_same_direction(1.0, 0.0) is False


def test_clustered_ols_matches_independent_manual_reference():
    frame = pd.DataFrame(
        {
            "slug": ["a", "a", "b", "b", "c", "c"],
            "obi_t": [-1.0, 0.5, -0.5, 1.0, 0.25, 1.5],
            "future_midpoint_change": [-0.08, 0.04, -0.01, 0.09, 0.03, 0.10],
        }
    )

    result = fit_frozen_clustered_ols(frame)

    x = np.column_stack(
        [
            np.ones(len(frame)),
            frame["obi_t"].to_numpy(dtype=float),
        ]
    )
    y = frame["future_midpoint_change"].to_numpy(dtype=float)

    expected_coef = np.linalg.solve(x.T @ x, x.T @ y)
    residuals = y - x @ expected_coef
    bread = np.linalg.inv(x.T @ x)

    meat = np.zeros((2, 2))
    for slug in frame["slug"].unique():
        mask = frame["slug"].to_numpy() == slug
        score = x[mask].T @ residuals[mask]
        meat += np.outer(score, score)

    n = len(frame)
    g = frame["slug"].nunique()
    k = 2
    cr1 = (g / (g - 1)) * ((n - 1) / (n - k))
    covariance = cr1 * bread @ meat @ bread
    expected_se = np.sqrt(covariance[1, 1])

    expected_t = expected_coef[1] / expected_se
    expected_p = 2.0 * stats.t.sf(abs(expected_t), df=g - 1)
    critical = stats.t.ppf(0.975, df=g - 1)

    assert result.intercept == pytest.approx(expected_coef[0])
    assert result.beta == pytest.approx(expected_coef[1])
    assert result.clustered_se_beta == pytest.approx(expected_se)
    assert result.beta_p_value_two_sided == pytest.approx(expected_p)
    assert result.beta_ci_95_low == pytest.approx(
        expected_coef[1] - critical * expected_se
    )
    assert result.beta_ci_95_high == pytest.approx(
        expected_coef[1] + critical * expected_se
    )
    assert result.eligible_n == n
    assert result.slug_clusters == g


def test_clustered_ols_rejects_single_cluster():
    frame = pd.DataFrame(
        {
            "slug": ["a", "a", "a"],
            "obi_t": [-1.0, 0.0, 1.0],
            "future_midpoint_change": [-0.1, 0.0, 0.1],
        }
    )

    with pytest.raises(StudyAError, match="G > 1"):
        fit_frozen_clustered_ols(frame)


def test_clustered_ols_rejects_rank_deficient_design():
    frame = pd.DataFrame(
        {
            "slug": ["a", "b", "c", "d"],
            "obi_t": [1.0, 1.0, 1.0, 1.0],
            "future_midpoint_change": [0.1, 0.2, 0.3, 0.4],
        }
    )

    with pytest.raises(StudyAError, match="rank deficient"):
        fit_frozen_clustered_ols(frame)


def test_missing_required_source_schema_fails_closed():
    obi = pd.DataFrame(
        {
            "timestamp": ["2026-01-01T00:00:00Z"],
            "publication_id": ["p1"],
            "slug": ["a"],
            "midpoint": [0.5],
            "status": ["valid"],
        }
    )

    with pytest.raises(StudyAError, match="missing required columns"):
        canonicalize_obi(obi)
