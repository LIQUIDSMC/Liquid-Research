import pandas as pd
import pytest

from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_a import (
    StudyAError,
)
from L3_RESEARCH_ENGINES.market_microstructure.analysis.forward_midpoint_study_b import (
    STUDY_A_OBI_EVIDENCE_BOUNDARY,
    run_study_b_from_frames,
)


def _obi_row(slug, publication_id, timestamp, midpoint, obi, status="ok"):
    return {
        "timestamp": timestamp,
        "publication_id": publication_id,
        "slug": slug,
        "midpoint": midpoint,
        "obi": obi,
        "status": status,
    }


def _near_row(slug, publication_id, timestamp, midpoint, near_obi, status="ok"):
    return {
        "timestamp": timestamp,
        "publication_id": publication_id,
        "slug": slug,
        "midpoint": midpoint,
        "near_obi": near_obi,
        "status": status,
    }


def _two_cluster_replication_frames():
    obi = pd.DataFrame(
        [
            _obi_row("a", "a1", "2026-10-07T00:00:00Z", 0.40, 0.50),
            _obi_row("a", "a2", "2026-10-08T00:00:00Z", 0.45, 0.25),
            _obi_row("b", "b1", "2026-10-07T01:00:00Z", 0.60, -0.50),
            _obi_row("b", "b2", "2026-10-08T01:00:00Z", 0.52, -0.25),
            _obi_row("c", "c1", "2026-10-07T02:00:00Z", 0.50, 0.20),
            _obi_row("c", "c2", "2026-10-08T02:00:00Z", 0.53, 0.10),
        ]
    )
    near = pd.DataFrame(
        [
            _near_row("a", "a1", "2026-10-07T00:00:30Z", 0.40, 0.40),
            _near_row("b", "b1", "2026-10-07T01:00:30Z", 0.60, -0.40),
            _near_row("c", "c1", "2026-10-07T02:00:30Z", 0.50, 0.15),
        ]
    )
    return obi, near


def test_study_b_boundary_constant_is_frozen():
    assert STUDY_A_OBI_EVIDENCE_BOUNDARY == pd.Timestamp(
        "2026-10-06T12:03:13Z"
    )


def test_anchor_exactly_on_boundary_is_excluded():
    obi, near = _two_cluster_replication_frames()

    obi = pd.concat(
        [
            pd.DataFrame(
                [
                    _obi_row(
                        "boundary",
                        "p1",
                        "2026-10-06T12:03:13Z",
                        0.40,
                        0.30,
                    ),
                    _obi_row(
                        "boundary",
                        "p2",
                        "2026-10-07T12:03:13Z",
                        0.45,
                        0.20,
                    ),
                ]
            ),
            obi,
        ],
        ignore_index=True,
    )
    near = pd.concat(
        [
            pd.DataFrame(
                [
                    _near_row(
                        "boundary",
                        "p1",
                        "2026-10-06T12:03:43Z",
                        0.40,
                        0.20,
                    )
                ]
            ),
            near,
        ],
        ignore_index=True,
    )

    eligible, _ = run_study_b_from_frames(obi, near)

    assert "boundary" not in set(eligible["slug"])


def test_strictly_post_boundary_anchor_and_next_are_retained():
    obi, near = _two_cluster_replication_frames()

    eligible, result = run_study_b_from_frames(obi, near)

    assert len(eligible) == 3
    assert result.eligible_n == 3
    assert result.slug_clusters == 3
    assert (eligible["obi_timestamp"] > STUDY_A_OBI_EVIDENCE_BOUNDARY).all()
    assert (eligible["next_obi_timestamp"] > STUDY_A_OBI_EVIDENCE_BOUNDARY).all()


def test_full_sequence_is_preserved_for_immediate_next_rule():
    obi, near = _two_cluster_replication_frames()

    extra_obi = pd.DataFrame(
        [
            _obi_row(
                "sequence",
                "p0",
                "2026-10-06T12:00:00Z",
                0.40,
                0.10,
            ),
            _obi_row(
                "sequence",
                "p1",
                "2026-10-06T12:04:00Z",
                0.41,
                0.20,
            ),
            _obi_row(
                "sequence",
                "p2",
                "2026-10-06T22:04:00Z",
                0.42,
                0.30,
            ),
            _obi_row(
                "sequence",
                "p3",
                "2026-10-07T12:04:00Z",
                0.50,
                0.40,
            ),
        ]
    )
    extra_near = pd.DataFrame(
        [
            _near_row(
                "sequence",
                "p1",
                "2026-10-06T12:04:30Z",
                0.41,
                0.25,
            )
        ]
    )

    obi = pd.concat([extra_obi, obi], ignore_index=True)
    near = pd.concat([extra_near, near], ignore_index=True)

    eligible, _ = run_study_b_from_frames(obi, near)

    # p1's true immediate next observation is p2 at +10 hours. It must not be
    # skipped in favor of p3 at +24 hours.
    sequence_rows = eligible.loc[eligible["slug"] == "sequence"]
    assert sequence_rows.empty


def test_boundary_filter_does_not_create_synthetic_next_observation():
    obi, near = _two_cluster_replication_frames()

    extra_obi = pd.DataFrame(
        [
            _obi_row(
                "cross",
                "pre",
                "2026-10-06T11:00:00Z",
                0.40,
                0.10,
            ),
            _obi_row(
                "cross",
                "post",
                "2026-10-07T11:00:00Z",
                0.50,
                0.20,
            ),
        ]
    )
    extra_near = pd.DataFrame(
        [
            _near_row(
                "cross",
                "pre",
                "2026-10-06T11:00:30Z",
                0.40,
                0.10,
            )
        ]
    )

    obi = pd.concat([extra_obi, obi], ignore_index=True)
    near = pd.concat([extra_near, near], ignore_index=True)

    eligible, _ = run_study_b_from_frames(obi, near)

    # The pre-boundary anchor cannot enter Study B even though its next
    # observation is post-boundary.
    assert "cross" not in set(eligible["slug"])


def test_study_b_retains_study_a_fail_closed_cluster_inference():
    obi = pd.DataFrame(
        [
            _obi_row("a", "p1", "2026-10-07T00:00:00Z", 0.40, 0.10),
            _obi_row("a", "p2", "2026-10-08T00:00:00Z", 0.45, 0.20),
        ]
    )
    near = pd.DataFrame(
        [
            _near_row("a", "p1", "2026-10-07T00:00:30Z", 0.40, 0.10),
        ]
    )

    with pytest.raises(StudyAError, match="G > 1"):
        run_study_b_from_frames(obi, near)
