#!/usr/bin/env python3

"""
LRS-1 D1-002 — Trade Side vs paper outcomes

Prospectively registered in commit:
0a4c744e0a5425b151dd2d5390fbb0977bc64ede

Discovery population:
Frozen D only, n=396.

Protected V1:
Non-D rows are not retained in the D1-002 analysis population and are not
analyzed, summarized, printed, or written. The authoritative CSV is scanned
only to recover the exact frozen D rows.

Primary predictor:
Recorded trade side (`Yes` versus `No`).

Expected direction:
None prespecified. D1-002 is two-sided with respect to which recorded side,
if either, has better paper outcomes.

Entry price:
Prespecified robustness stratification only. It is not tested as an
independent predictor in D1-002.

Candidate classification:
The execution report records the prospectively specified evidence and
robustness views. It does not algorithmically assign RETAIN, REJECT,
INCONCLUSIVE, or DESCRIPTIVE ONLY from observed outcome magnitudes.
Final candidate status is recorded separately in the append-only registry
after execution review.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

LEDGER_PATH = (
    ROOT
    / "L3_RESEARCH_ENGINES"
    / "market_selection"
    / "data"
    / "simulator"
    / "paper_trades.csv"
)

DETECTOR_PATH = (
    ROOT
    / "L3_RESEARCH_ENGINES"
    / "market_selection"
    / "analysis"
    / "latent_event_family_detector_v1_1.py"
)

REPORT_PATH = (
    ROOT
    / "L3_RESEARCH_ENGINES"
    / "market_selection"
    / "analysis"
    / "D1_002_side_outcomes.md"
)

EXPECTED_D_N = 396

EXPECTED_D_HASH = (
    "ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e"
)

EXPECTED_DETECTOR_SHA256 = (
    "008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e"
)

EXPECTED_V11_ASSIGNMENT_HASH = (
    "a0a11cd96c8d188cdab17077f38d66932c48b2f2f44acde49815a89d1a7a07c6"
)

EXPECTED_PRIMARY_SHA256 = (
    "09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3"
)

EXPECTED_DERIVED_SHA256 = (
    "1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a"
)

ENTRY_Q1 = 0.7025
ENTRY_MEDIAN = 0.8675
ENTRY_Q3 = 0.9537

FAMILY_COLS = [
    "trade_id",
    "rule_matched",
    "family_key",
    "family_size",
]

# IMPORTANT:
# This allowlist deliberately contains only fields required by the
# prospectively registered D1-002 analysis.
#
# V1 protection is enforced by loading ledger rows only after obtaining the
# exact frozen D trade_id set from the frozen detector.
LEDGER_COLS = [
    "trade_id",
    "resolution_date",
    "entry_date",
    "side",
    "entry_price",
    "trade_won",
    "trade_pnl",
    "category",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(x, digits: int = 4) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{digits}f}"


def pct(n: int, d: int) -> str:
    if not d:
        return "NA"
    return f"{100.0 * n / d:.2f}%"


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None_"

    cols = list(df.columns)

    def cell(v):
        if pd.isna(v):
            return "NA"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]

    for _, row in df.iterrows():
        lines.append(
            "| " + " | ".join(cell(row[c]) for c in cols) + " |"
        )

    return "\n".join(lines)


def trimmed_mean_10(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna().sort_values()

    n = len(s)

    if n < 10:
        return math.nan

    k = math.floor(n * 0.10)

    if k == 0 or 2 * k >= n:
        return math.nan

    return float(s.iloc[k:n-k].mean())


def outcome_summary(frame: pd.DataFrame) -> dict:
    won = pd.to_numeric(frame["trade_won"], errors="coerce")
    pnl = pd.to_numeric(frame["trade_pnl"], errors="coerce")

    won_valid = won.dropna()
    pnl_valid = pnl.dropna()

    return {
        "raw_n": int(len(frame)),
        "win_usable_n": int(len(won_valid)),
        "pnl_usable_n": int(len(pnl_valid)),
        "win_rate": (
            float(won_valid.mean()) if len(won_valid) else math.nan
        ),
        "pnl_mean": (
            float(pnl_valid.mean()) if len(pnl_valid) else math.nan
        ),
        "pnl_median": (
            float(pnl_valid.median()) if len(pnl_valid) else math.nan
        ),
        "pnl_trimmed_mean_10": trimmed_mean_10(pnl_valid),
    }


def entry_stratum(price) -> str:
    x = pd.to_numeric(pd.Series([price]), errors="coerce").iloc[0]

    if pd.isna(x):
        return "<MISSING>"

    if x <= ENTRY_Q1:
        return "Q1 <=0.7025"

    if x <= ENTRY_MEDIAN:
        return "Q2 0.7025–0.8675"

    if x <= ENTRY_Q3:
        return "Q3 0.8675–0.9537"

    return "Q4 >0.9537"


# ============================================================
# GATE 1 — EXACT FROZEN DETECTOR
# ============================================================

if not DETECTOR_PATH.is_file():
    fail(f"Frozen detector missing: {DETECTOR_PATH}")

detector_sha = sha256_file(DETECTOR_PATH)

if detector_sha != EXPECTED_DETECTOR_SHA256:
    fail(
        "Frozen detector SHA mismatch.\n"
        f"expected={EXPECTED_DETECTOR_SHA256}\n"
        f"actual={detector_sha}"
    )


# ============================================================
# GATE 2 — EXECUTE FROZEN DETECTOR / VERIFY PROVENANCE
# ============================================================

spec = importlib.util.spec_from_file_location(
    "lrs1_latent_event_family_detector_v1_1_frozen_d1_002",
    DETECTOR_PATH,
)

if spec is None or spec.loader is None:
    fail("Could not construct detector importlib spec.")

detector = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(detector)
except Exception as exc:
    fail(
        "Frozen detector execution failed closed: "
        f"{type(exc).__name__}: {exc}"
    )

required_detector_attrs = [
    "out",
    "d_hash",
    "v11_assignment_hash",
    "freeze_sha256",
    "derived_sha256",
]

missing_attrs = [
    name
    for name in required_detector_attrs
    if not hasattr(detector, name)
]

if missing_attrs:
    fail(
        "Frozen detector missing required attributes: "
        + ", ".join(missing_attrs)
    )

if detector.d_hash != EXPECTED_D_HASH:
    fail("Frozen D fingerprint mismatch.")

if detector.v11_assignment_hash != EXPECTED_V11_ASSIGNMENT_HASH:
    fail("Frozen family assignment hash mismatch.")

if detector.freeze_sha256 != EXPECTED_PRIMARY_SHA256:
    fail("Frozen primary family checksum mismatch.")

if detector.derived_sha256 != EXPECTED_DERIVED_SHA256:
    fail("Frozen derived family checksum mismatch.")

if not isinstance(detector.out, pd.DataFrame):
    fail("detector.out is not a pandas DataFrame.")

missing_family_cols = [
    c for c in FAMILY_COLS if c not in detector.out.columns
]

if missing_family_cols:
    fail(
        "Frozen detector output missing columns: "
        + ", ".join(missing_family_cols)
    )

family = detector.out[FAMILY_COLS].copy()

if len(family) != EXPECTED_D_N:
    fail(f"Frozen family population is {len(family)}, expected 396.")

if family["trade_id"].nunique() != EXPECTED_D_N:
    fail("Frozen D does not contain 396 unique trade IDs.")

if family["trade_id"].duplicated().any():
    fail("Frozen family assignment contains duplicate trade IDs.")


# ============================================================
# GATE 3 — LOAD ONLY FROZEN D ROWS FROM AUTHORITATIVE LEDGER
# ============================================================

if not LEDGER_PATH.is_file():
    fail(f"Authoritative ledger missing: {LEDGER_PATH}")

# Read only trade_id first. No outcome field is touched while determining
# which physical ledger rows belong to frozen D.
trade_ids_only = pd.read_csv(
    LEDGER_PATH,
    usecols=["trade_id"],
)

if trade_ids_only["trade_id"].duplicated().any():
    fail("Authoritative ledger contains duplicate trade IDs.")

frozen_ids = set(family["trade_id"].tolist())

row_mask = trade_ids_only["trade_id"].isin(frozen_ids)

if int(row_mask.sum()) != EXPECTED_D_N:
    fail(
        "Authoritative ledger does not contain exactly 396 frozen D rows."
    )

# Only now process the registered outcome fields.
#
# IMPORTANT V1 ANALYTICAL ISOLATION:
# The CSV parser necessarily reads source rows while scanning the authoritative
# ledger. Each bounded chunk is immediately filtered against the already
# frozen D trade_id set. Non-D rows are never retained in the assembled D1-002
# dataframe and are never analyzed, summarized, printed, or written by this
# script. This is an analytical-isolation guarantee, not a claim that source
# bytes for non-D rows are never parsed.
d_chunks = []

for chunk in pd.read_csv(
    LEDGER_PATH,
    usecols=LEDGER_COLS,
    chunksize=128,
):
    keep = chunk["trade_id"].isin(frozen_ids)

    if keep.any():
        d_chunks.append(
            chunk.loc[keep, LEDGER_COLS].copy()
        )

if not d_chunks:
    fail("No frozen D rows were recovered from authoritative ledger.")

d_ledger = pd.concat(
    d_chunks,
    ignore_index=True,
)

del d_chunks
del trade_ids_only
del row_mask

if len(d_ledger) != EXPECTED_D_N:
    fail(f"D1-002 ledger population is {len(d_ledger)}, expected 396.")

if d_ledger["trade_id"].nunique() != EXPECTED_D_N:
    fail("D1-002 ledger population does not contain 396 unique trade IDs.")

d = family.merge(
    d_ledger,
    on="trade_id",
    how="left",
    validate="one_to_one",
    indicator=True,
)

if not d["_merge"].eq("both").all():
    fail("Frozen family assignment did not one-to-one match ledger D rows.")

d = d.drop(columns="_merge")

if len(d) != EXPECTED_D_N:
    fail("Joined D1-002 population changed size.")


# ============================================================
# GATE 4 — D1-002 DERIVED FIELDS
# ============================================================

side_values = set(
    d["side"].astype("string").dropna().unique().tolist()
)

if side_values != {"Yes", "No"}:
    fail(
        "D1-002 side domain changed; expected exactly {'Yes', 'No'}, "
        f"got {sorted(side_values)}."
    )

entry_dt = pd.to_datetime(d["entry_date"], errors="coerce")
d["entry_month"] = entry_dt.dt.strftime("%Y-%m").fillna("<MISSING>")
d["entry_price_stratum"] = d["entry_price"].map(entry_stratum)


# ============================================================
# PRIMARY SIDE RESULTS
# ============================================================

side_rows = []

for side in ["Yes", "No"]:
    g = d[d["side"].eq(side)]
    s = outcome_summary(g)

    side_rows.append(
        {
            "side": side,
            **s,
        }
    )

side_df = pd.DataFrame(side_rows).set_index("side")

yes = side_df.loc["Yes"]
no = side_df.loc["No"]

primary_contrast_df = pd.DataFrame(
    [
        {
            "contrast": "Yes - No",
            "win_rate_difference": (
                yes["win_rate"] - no["win_rate"]
            ),
            "pnl_mean_difference": (
                yes["pnl_mean"] - no["pnl_mean"]
            ),
            "pnl_median_difference": (
                yes["pnl_median"] - no["pnl_median"]
            ),
            "pnl_trim10_difference": (
                yes["pnl_trimmed_mean_10"]
                - no["pnl_trimmed_mean_10"]
            ),
        }
    ]
)

side_df = side_df.reset_index()


# ============================================================
# OUTLIER CONCENTRATION
# ============================================================

pnl_valid = pd.to_numeric(
    d["trade_pnl"],
    errors="coerce",
).dropna()

total_pnl = (
    float(pnl_valid.sum())
    if len(pnl_valid)
    else math.nan
)

abs_ranked = pnl_valid.abs().sort_values(ascending=False)

largest_abs_3 = (
    float(abs_ranked.head(3).sum())
    if len(abs_ranked)
    else math.nan
)

total_abs_pnl = (
    float(pnl_valid.abs().sum())
    if len(pnl_valid)
    else math.nan
)

largest_abs_3_share_of_abs = (
    largest_abs_3 / total_abs_pnl
    if total_abs_pnl and not math.isnan(total_abs_pnl)
    else math.nan
)


# ============================================================
# ENTRY-PRICE ROBUSTNESS — FIXED D0 STRATA
# ============================================================
#
# Entry price is NOT tested as an independent predictor.
# These fixed D0 strata only ask whether the registered side/outcome
# relationship materially changes across prespecified entry-price contexts.

entry_rows = []

entry_order = [
    "Q1 <=0.7025",
    "Q2 0.7025–0.8675",
    "Q3 0.8675–0.9537",
    "Q4 >0.9537",
    "<MISSING>",
]

for stratum in entry_order:
    g = d[d["entry_price_stratum"].eq(stratum)]

    if g.empty:
        continue

    row = {
        "entry_price_stratum": stratum,
        "n": int(len(g)),
    }

    summaries = {}

    for side in ["Yes", "No"]:
        s = outcome_summary(g[g["side"].eq(side)])
        summaries[side] = s

        prefix = side.lower()
        row[f"{prefix}_n"] = s["raw_n"]
        row[f"{prefix}_win_rate"] = s["win_rate"]
        row[f"{prefix}_pnl_mean"] = s["pnl_mean"]
        row[f"{prefix}_pnl_median"] = s["pnl_median"]
        row[f"{prefix}_pnl_trim10"] = s["pnl_trimmed_mean_10"]

    row["yes_minus_no_win_rate"] = (
        summaries["Yes"]["win_rate"]
        - summaries["No"]["win_rate"]
    )
    row["yes_minus_no_pnl_mean"] = (
        summaries["Yes"]["pnl_mean"]
        - summaries["No"]["pnl_mean"]
    )
    row["yes_minus_no_pnl_median"] = (
        summaries["Yes"]["pnl_median"]
        - summaries["No"]["pnl_median"]
    )
    row["yes_minus_no_pnl_trim10"] = (
        summaries["Yes"]["pnl_trimmed_mean_10"]
        - summaries["No"]["pnl_trimmed_mean_10"]
    )

    entry_rows.append(row)

entry_df = pd.DataFrame(entry_rows)


# ============================================================
# TEMPORAL ROBUSTNESS — FIXED D0 CALENDAR MONTHS
# ============================================================

temporal_rows = []

for month in [
    "2026-06",
    "2026-07",
    "2026-08",
    "2026-09",
    "<MISSING>",
]:
    g = d[d["entry_month"].eq(month)]

    if g.empty:
        continue

    row = {
        "entry_month": month,
        "n": int(len(g)),
    }

    summaries = {}

    for side in ["Yes", "No"]:
        s = outcome_summary(g[g["side"].eq(side)])
        summaries[side] = s

        prefix = side.lower()
        row[f"{prefix}_n"] = s["raw_n"]
        row[f"{prefix}_win_rate"] = s["win_rate"]
        row[f"{prefix}_pnl_mean"] = s["pnl_mean"]
        row[f"{prefix}_pnl_median"] = s["pnl_median"]
        row[f"{prefix}_pnl_trim10"] = s["pnl_trimmed_mean_10"]

    row["yes_minus_no_win_rate"] = (
        summaries["Yes"]["win_rate"]
        - summaries["No"]["win_rate"]
    )
    row["yes_minus_no_pnl_mean"] = (
        summaries["Yes"]["pnl_mean"]
        - summaries["No"]["pnl_mean"]
    )
    row["yes_minus_no_pnl_median"] = (
        summaries["Yes"]["pnl_median"]
        - summaries["No"]["pnl_median"]
    )
    row["yes_minus_no_pnl_trim10"] = (
        summaries["Yes"]["pnl_trimmed_mean_10"]
        - summaries["No"]["pnl_trimmed_mean_10"]
    )

    temporal_rows.append(row)

temporal_df = pd.DataFrame(temporal_rows)


# ============================================================
# FAMILY / DEPENDENCE SENSITIVITY
# ============================================================

family_sizes = (
    d.groupby("family_key")["trade_id"]
    .size()
    .sort_values(ascending=False)
)

family_count = int(len(family_sizes))
largest_family_n = int(family_sizes.iloc[0])
largest_family_share = largest_family_n / len(d)

family_side_cells = (
    d.groupby(
        ["family_key", "side"],
        as_index=False,
        dropna=False,
    )
    .agg(
        cell_n=("trade_id", "size"),
        mean_trade_won=("trade_won", "mean"),
        mean_trade_pnl=("trade_pnl", "mean"),
    )
)

family_side_rows = []

for side in ["Yes", "No"]:
    g = family_side_cells[
        family_side_cells["side"].eq(side)
    ]

    family_side_rows.append(
        {
            "side": side,
            "represented_families": int(
                g["family_key"].nunique()
            ),
            "family_cell_n": int(len(g)),
            "equal_weight_mean_trade_won": float(
                g["mean_trade_won"].mean()
            ),
            "equal_weight_mean_trade_pnl": float(
                g["mean_trade_pnl"].mean()
            ),
        }
    )

family_side_df = pd.DataFrame(family_side_rows)

family_side_presence = (
    family_side_cells.groupby("family_key")["side"]
    .nunique()
)

both_side_family_keys = set(
    family_side_presence[
        family_side_presence.eq(2)
    ].index.tolist()
)

both_side_family_count = len(both_side_family_keys)

paired = family_side_cells[
    family_side_cells["family_key"].isin(
        both_side_family_keys
    )
].pivot(
    index="family_key",
    columns="side",
    values=[
        "mean_trade_won",
        "mean_trade_pnl",
    ],
)

expected_paired_columns = {
    ("mean_trade_won", "Yes"),
    ("mean_trade_won", "No"),
    ("mean_trade_pnl", "Yes"),
    ("mean_trade_pnl", "No"),
}

if both_side_family_count:
    actual_paired_columns = set(paired.columns.tolist())

    if actual_paired_columns != expected_paired_columns:
        fail(
            "Paired-family side columns changed unexpectedly."
        )

    paired_win_diff = (
        paired[("mean_trade_won", "Yes")]
        - paired[("mean_trade_won", "No")]
    )

    paired_pnl_diff = (
        paired[("mean_trade_pnl", "Yes")]
        - paired[("mean_trade_pnl", "No")]
    )

    paired_family_df = pd.DataFrame(
        [
            {
                "outcome": "trade_won",
                "paired_family_n": both_side_family_count,
                "mean_yes_minus_no": float(
                    paired_win_diff.mean()
                ),
                "median_yes_minus_no": float(
                    paired_win_diff.median()
                ),
            },
            {
                "outcome": "trade_pnl",
                "paired_family_n": both_side_family_count,
                "mean_yes_minus_no": float(
                    paired_pnl_diff.mean()
                ),
                "median_yes_minus_no": float(
                    paired_pnl_diff.median()
                ),
            },
        ]
    )
else:
    paired_family_df = pd.DataFrame(
        [
            {
                "outcome": "trade_won",
                "paired_family_n": 0,
                "mean_yes_minus_no": math.nan,
                "median_yes_minus_no": math.nan,
            },
            {
                "outcome": "trade_pnl",
                "paired_family_n": 0,
                "mean_yes_minus_no": math.nan,
                "median_yes_minus_no": math.nan,
            },
        ]
    )


# ============================================================
# CATEGORY COMPOSITION — CONTEXT ONLY
# ============================================================

category_df = (
    d["category"]
    .astype("string")
    .fillna("<MISSING>")
    .value_counts(dropna=False)
    .rename_axis("category")
    .reset_index(name="n")
)

category_df["percent"] = (
    100.0 * category_df["n"] / len(d)
)


# ============================================================
# REPORT
# ============================================================

missing_rows = []

for col in LEDGER_COLS:
    missing_rows.append(
        {
            "field": col,
            "missing": int(d[col].isna().sum()),
            "usable": int(d[col].notna().sum()),
        }
    )

missing_df = pd.DataFrame(missing_rows)

report = f"""# LRS-1 D1-002 — Trade Side vs Paper Outcomes

**DISCOVERY ANALYSIS — FROZEN D ONLY**

This report is hypothesis-generating discovery evidence, not independent
validation and not a live-money edge claim.

Protected V1 was not retained in the D1-002 analysis population and was not
analyzed, summarized, printed, or written.

## Provenance

- Prospective registration commit:
  `0a4c744e0a5425b151dd2d5390fbb0977bc64ede`
- Frozen D n: **{len(d)}**
- Frozen D trade-id SHA-256: `{EXPECTED_D_HASH}`
- Frozen detector SHA-256: `{EXPECTED_DETECTOR_SHA256}`
- Frozen family primary SHA-256: `{detector.freeze_sha256}`
- Frozen family derived SHA-256: `{detector.derived_sha256}`
- Expected direction: **none prespecified**
- Primary comparison: **Yes versus No**
- Entry-price role: **robustness stratification only**

## Missingness / usable n

{markdown_table(missing_df)}

## Primary side outcomes

{markdown_table(side_df)}

Primary descriptive contrast:

{markdown_table(primary_contrast_df)}

The contrast is always defined as **Yes minus No**. Positive values therefore
favor Yes on the reported metric; negative values favor No. Because D1-002
registered no directional hypothesis, the observed sign must not be described
as prospectively predicted.

## Frozen P&L outlier sensitivity

- Total realized P&L: **{fmt(total_pnl, 2)}**
- Sum of three largest absolute P&L magnitudes:
  **{fmt(largest_abs_3, 2)}**
- Total absolute P&L: **{fmt(total_abs_pnl, 2)}**
- Three-largest-absolute share of total absolute P&L:
  **{fmt(100.0 * largest_abs_3_share_of_abs, 2) + "%" if not math.isnan(largest_abs_3_share_of_abs) else "NA"}**

The primary side table reports the frozen 10% symmetric trimmed mean wherever
the side-specific n is eligible. The top-three concentration denominator is
total absolute P&L, matching the prospectively registered D1-002 convention.

## Entry-price robustness

Entry price is not tested as a standalone predictor. These fixed D0 strata
evaluate whether the registered Yes/No outcome contrast is stable across
prespecified entry-price contexts.

{markdown_table(entry_df)}

## Temporal robustness

Calendar-month boundaries were fixed outcome-blind in D0.

{markdown_table(temporal_df)}

## Frozen event-family / dependence sensitivity

- Families represented: **{family_count}**
- Largest family n: **{largest_family_n}**
- Largest-family share of D:
  **{pct(largest_family_n, len(d))}**
- Families containing both Yes and No:
  **{both_side_family_count}**

Primary family-equal-weight sensitivity:

{markdown_table(family_side_df)}

Each `family_key × side` cell is first reduced to its arithmetic-mean outcome.
For each side, represented family cells then receive equal weight regardless
of the number of trades in the cell.

Paired-family sensitivity:

{markdown_table(paired_family_df)}

Paired-family differences are always **Yes family-cell mean minus No
family-cell mean** and include only frozen families structurally containing
both sides. No outcome-based paired-family selection is permitted.

Family-aware results are sensitivity analyses, not proof that observations
are fully independent.

## Category composition

Context only; no category-specific outcome candidate is tested here.

{markdown_table(category_df)}

## Interpretation constraints

- D is discovery evidence and has historical outcome exposure.
- D1-002 registered no directional Yes-versus-No hypothesis.
- Statistical description and economic usefulness are separate questions.
- Entry-price stratification does not establish entry-price causality.
- Family-aware sensitivity does not prove independence.
- Category is context only and cannot be silently promoted from this analysis.
- No alternate side grouping, threshold, subgroup, temporal boundary, or
  paired-family selection rule may be introduced after seeing these results.
- The execution report does not algorithmically assign candidate status.
- Candidate status must be recorded separately in the append-only registry
  after review of the complete prospectively specified evidence.
- No D1-002 result automatically promotes a hypothesis to V1.
- Protected V1 remains unopened.
"""

REPORT_PATH.write_text(report)

print("D1_002_EXECUTION=COMPLETE")
print(f"D_N={len(d)}")
print(f"D_HASH={EXPECTED_D_HASH}")
print(f"FAMILIES={family_count}")
print(f"BOTH_SIDE_FAMILIES={both_side_family_count}")
print(f"REPORT={REPORT_PATH}")
print("EXPECTED_DIRECTION=NONE_PRESPECIFIED")
print("ENTRY_PRICE_ROLE=ROBUSTNESS_STRATIFICATION_ONLY")
print("CANDIDATE_STATUS_ASSIGNED=NO")
print("V1_ACCESSED=NO")
