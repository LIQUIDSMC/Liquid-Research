#!/usr/bin/env python3

"""
LRS-1 D1-001 — Tradeability Score vs paper outcomes

Prospectively registered in commit:
cfd4127510fa74b108e8d86bd91527ec50746cdb

Discovery population:
Frozen D only, n=396.

Protected V1:
Non-D rows are not retained in the D1-001 analysis population and are not
analyzed, summarized, printed, or written. The authoritative CSV is scanned
only to recover the exact frozen D rows.

Primary predictor:
tradeability_score_at_entry

Entry price:
Prespecified robustness stratification only.
It is NOT a second independently tested predictor in D1-001.
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
    / "D1_001_score_outcomes.md"
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

SCORE_SPLIT = 93.70

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
# prospectively registered D1-001 analysis.
#
# V1 protection is enforced by loading ledger rows only after obtaining the
# exact frozen D trade_id set from the frozen detector.
LEDGER_COLS = [
    "trade_id",
    "resolution_date",
    "entry_date",
    "tradeability_score_at_entry",
    "entry_price",
    "trade_won",
    "trade_pnl",
    "category",
    "spread_label",
    "liquidity",
    "volume_24h",
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


def corr_pair(x: pd.Series, y: pd.Series) -> dict:
    pair = pd.DataFrame(
        {
            "x": pd.to_numeric(x, errors="coerce"),
            "y": pd.to_numeric(y, errors="coerce"),
        }
    ).dropna()

    if len(pair) < 2:
        return {
            "n": int(len(pair)),
            "pearson": math.nan,
            "spearman": math.nan,
        }

    xr = pair["x"].rank(method="average")
    yr = pair["y"].rank(method="average")

    return {
        "n": int(len(pair)),
        "pearson": pair["x"].corr(pair["y"], method="pearson"),
        "spearman": xr.corr(yr, method="pearson"),
    }


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


def score_group(score) -> str:
    x = pd.to_numeric(pd.Series([score]), errors="coerce").iloc[0]

    if pd.isna(x):
        return "<MISSING>"

    return "Low (<93.70)" if x < SCORE_SPLIT else "High (>=93.70)"


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
    "lrs1_latent_event_family_detector_v1_1_frozen_d1_001",
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
# frozen D trade_id set. Non-D rows are never retained in the assembled D1-001
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
    fail(f"D1-001 ledger population is {len(d_ledger)}, expected 396.")

if d_ledger["trade_id"].nunique() != EXPECTED_D_N:
    fail("D1-001 ledger population does not contain 396 unique trade IDs.")

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
    fail("Joined D1-001 population changed size.")


# ============================================================
# GATE 4 — D1-001 DERIVED FIELDS
# ============================================================

d["score_group"] = d["tradeability_score_at_entry"].map(score_group)

entry_dt = pd.to_datetime(d["entry_date"], errors="coerce")

d["entry_month"] = entry_dt.dt.strftime("%Y-%m").fillna("<MISSING>")

d["entry_price_stratum"] = d["entry_price"].map(entry_stratum)


# ============================================================
# PRIMARY SCORE RESULTS
# ============================================================

score_win_corr = corr_pair(
    d["tradeability_score_at_entry"],
    d["trade_won"],
)

score_pnl_corr = corr_pair(
    d["tradeability_score_at_entry"],
    d["trade_pnl"],
)

score_group_rows = []

for group in ["Low (<93.70)", "High (>=93.70)", "<MISSING>"]:
    g = d[d["score_group"].eq(group)]

    if g.empty:
        continue

    s = outcome_summary(g)

    score_group_rows.append(
        {
            "score_group": group,
            **s,
        }
    )

score_group_df = pd.DataFrame(score_group_rows)


# ============================================================
# OUTLIER CONCENTRATION
# ============================================================

pnl_valid = pd.to_numeric(
    d["trade_pnl"],
    errors="coerce",
).dropna()

total_pnl = float(pnl_valid.sum()) if len(pnl_valid) else math.nan

abs_ranked = pnl_valid.abs().sort_values(ascending=False)

largest_abs_3 = float(abs_ranked.head(3).sum()) if len(abs_ranked) else math.nan

total_abs_pnl = float(pnl_valid.abs().sum()) if len(pnl_valid) else math.nan

largest_abs_3_share_of_abs = (
    largest_abs_3 / total_abs_pnl
    if total_abs_pnl and not math.isnan(total_abs_pnl)
    else math.nan
)


# ============================================================
# ENTRY-PRICE ROBUSTNESS STRATIFICATION
#
# IMPORTANT:
# Entry price is NOT tested here as an independent predictor.
# These fixed D0 strata only ask whether the registered SCORE relationship
# materially changes across prespecified entry-price contexts.
# ============================================================

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

    c_win = corr_pair(
        g["tradeability_score_at_entry"],
        g["trade_won"],
    )

    c_pnl = corr_pair(
        g["tradeability_score_at_entry"],
        g["trade_pnl"],
    )

    low = outcome_summary(
        g[g["score_group"].eq("Low (<93.70)")]
    )

    high = outcome_summary(
        g[g["score_group"].eq("High (>=93.70)")]
    )

    entry_rows.append(
        {
            "entry_price_stratum": stratum,
            "n": int(len(g)),
            "score_win_pearson": c_win["pearson"],
            "score_win_spearman": c_win["spearman"],
            "score_pnl_pearson": c_pnl["pearson"],
            "score_pnl_spearman": c_pnl["spearman"],
            "low_n": low["raw_n"],
            "low_win_rate": low["win_rate"],
            "low_pnl_mean": low["pnl_mean"],
            "low_pnl_median": low["pnl_median"],
            "low_pnl_trim10": low["pnl_trimmed_mean_10"],
            "high_n": high["raw_n"],
            "high_win_rate": high["win_rate"],
            "high_pnl_mean": high["pnl_mean"],
            "high_pnl_median": high["pnl_median"],
            "high_pnl_trim10": high["pnl_trimmed_mean_10"],
        }
    )

entry_df = pd.DataFrame(entry_rows)


# ============================================================
# TEMPORAL ROBUSTNESS — FIXED D0 CALENDAR MONTHS
# ============================================================

temporal_rows = []

for month in ["2026-06", "2026-07", "2026-08", "2026-09", "<MISSING>"]:
    g = d[d["entry_month"].eq(month)]

    if g.empty:
        continue

    c_pnl = corr_pair(
        g["tradeability_score_at_entry"],
        g["trade_pnl"],
    )

    low = outcome_summary(
        g[g["score_group"].eq("Low (<93.70)")]
    )

    high = outcome_summary(
        g[g["score_group"].eq("High (>=93.70)")]
    )

    temporal_rows.append(
        {
            "entry_month": month,
            "n": int(len(g)),
            "score_pnl_pearson": c_pnl["pearson"],
            "score_pnl_spearman": c_pnl["spearman"],
            "low_n": low["raw_n"],
            "low_win_rate": low["win_rate"],
            "low_pnl_mean": low["pnl_mean"],
            "low_pnl_median": low["pnl_median"],
            "low_pnl_trim10": low["pnl_trimmed_mean_10"],
            "high_n": high["raw_n"],
            "high_win_rate": high["win_rate"],
            "high_pnl_mean": high["pnl_mean"],
            "high_pnl_median": high["pnl_median"],
            "high_pnl_trim10": high["pnl_trimmed_mean_10"],
        }
    )

temporal_df = pd.DataFrame(temporal_rows)


# ============================================================
# FAMILY / DEPENDENCE SENSITIVITY
# ============================================================

family_sizes = d.groupby("family_key")["trade_id"].size().sort_values(
    ascending=False
)

family_count = int(len(family_sizes))
largest_family_n = int(family_sizes.iloc[0])
largest_family_share = largest_family_n / len(d)

family_level = (
    d.groupby("family_key", as_index=False)
    .agg(
        family_size=("trade_id", "size"),
        mean_score=("tradeability_score_at_entry", "mean"),
        mean_trade_won=("trade_won", "mean"),
        mean_trade_pnl=("trade_pnl", "mean"),
    )
)

family_score_win_corr = corr_pair(
    family_level["mean_score"],
    family_level["mean_trade_won"],
)

family_score_pnl_corr = corr_pair(
    family_level["mean_score"],
    family_level["mean_trade_pnl"],
)


# ============================================================
# CATEGORY COMPOSITION
# ============================================================

category_df = (
    d["category"]
    .astype("string")
    .fillna("<MISSING>")
    .value_counts(dropna=False)
    .rename_axis("category")
    .reset_index(name="n")
)

category_df["percent"] = 100.0 * category_df["n"] / len(d)


# ============================================================
# CORRELATED FEATURE-FAMILY CONTEXT
#
# Context only. These are NOT independent D1 candidates.
# ============================================================

context_rows = []

for predictor in ["liquidity", "volume_24h"]:
    context_rows.append(
        {
            "context_variable": predictor,
            "vs_score_pearson": corr_pair(
                d[predictor],
                d["tradeability_score_at_entry"],
            )["pearson"],
            "vs_score_spearman": corr_pair(
                d[predictor],
                d["tradeability_score_at_entry"],
            )["spearman"],
        }
    )

context_df = pd.DataFrame(context_rows)

spread_context_df = (
    d.groupby("spread_label", dropna=False)
    .agg(
        n=("trade_id", "size"),
        mean_score=("tradeability_score_at_entry", "mean"),
        median_score=("tradeability_score_at_entry", "median"),
    )
    .reset_index()
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

report = f"""# LRS-1 D1-001 — Tradeability Score vs Paper Outcomes

**DISCOVERY ANALYSIS — FROZEN D ONLY**

This report is hypothesis-generating discovery evidence, not independent
validation and not a live-money edge claim.

Protected V1 was not retained in the D1-001 analysis population and was not
analyzed, summarized, printed, or written by this script. The authoritative
CSV is necessarily scanned to recover frozen D rows; this is an analytical
isolation guarantee, not a claim that non-D source bytes are never parsed.

## Provenance

- Registration commit:
  `cfd4127510fa74b108e8d86bd91527ec50746cdb`
- Frozen D n: **{len(d)}**
- Frozen D trade-id SHA-256: `{EXPECTED_D_HASH}`
- Frozen detector SHA-256: `{detector_sha}`
- Frozen family primary SHA-256: `{detector.freeze_sha256}`
- Frozen family derived SHA-256: `{detector.derived_sha256}`
- Primary predictor: `tradeability_score_at_entry`
- Fixed score split: **93.70**
- Entry price role: **robustness stratification only; not an independently
  tested predictor in D1-001**

## Missingness / usable population

{markdown_table(missing_df)}

## Primary continuous score associations

| Outcome | n | Pearson | Spearman |
| --- | --- | --- | --- |
| trade_won | {score_win_corr["n"]} | {fmt(score_win_corr["pearson"])} | {fmt(score_win_corr["spearman"])} |
| trade_pnl | {score_pnl_corr["n"]} | {fmt(score_pnl_corr["pearson"])} | {fmt(score_pnl_corr["spearman"])} |

## Fixed D0 score split

{markdown_table(score_group_df)}

## P&L outlier sensitivity

- Total realized P&L in usable D rows: **{fmt(total_pnl, 2)}**
- Sum of three largest absolute P&L magnitudes: **{fmt(largest_abs_3, 2)}**
- Three-largest-absolute share of total absolute P&L:
  **{fmt(largest_abs_3_share_of_abs * 100 if not pd.isna(largest_abs_3_share_of_abs) else math.nan, 2)}%**
- Frozen robust estimator: 10% symmetric trimmed mean, reported in the
  score-group and sensitivity tables whenever group n >= 10.

## Entry-price robustness stratification

Entry price is not tested here as a standalone predictor. The following fixed
D0 strata only evaluate whether the registered score/outcome relationship is
stable across prespecified entry-price contexts.

{markdown_table(entry_df)}

## Temporal robustness

Calendar-month boundaries were fixed outcome-blind in D0.

{markdown_table(temporal_df)}

## Frozen event-family / dependence sensitivity

- Families represented: **{family_count}**
- Largest family n: **{largest_family_n}**
- Largest-family share of D: **{pct(largest_family_n, len(d))}**

Family-level equal-weight sensitivity:

| Outcome | family n | Pearson | Spearman |
| --- | --- | --- | --- |
| mean trade_won | {family_score_win_corr["n"]} | {fmt(family_score_win_corr["pearson"])} | {fmt(family_score_win_corr["spearman"])} |
| mean trade_pnl | {family_score_pnl_corr["n"]} | {fmt(family_score_pnl_corr["pearson"])} | {fmt(family_score_pnl_corr["spearman"])} |

Family-aware results are sensitivity analyses, not proof that observations are
fully independent.

## Category composition

{markdown_table(category_df)}

## Correlated tradeability-feature context

These variables are contextual decomposition of the same conceptual
tradeability feature family. They are not independent discoveries under
D1-001.

{markdown_table(context_df)}

Spread-label score context:

{markdown_table(spread_context_df)}

## Interpretation constraints

- D is discovery evidence and has historical outcome exposure.
- D1-001 does not reset or erase Audit E.
- Statistical association and economic usefulness are separate questions.
- Entry-price stratification does not establish entry-price causality.
- Liquidity, volume, and spread-label context do not constitute separate
  validated predictors.
- Family-level sensitivity does not prove independence.
- No threshold may be changed after seeing these results under D1-001.
- No D1-001 result automatically promotes a hypothesis to V1.
- Protected V1 remains unopened.
"""

REPORT_PATH.write_text(report)

print("D1_001_EXECUTION=COMPLETE")
print(f"D_N={len(d)}")
print(f"D_HASH={EXPECTED_D_HASH}")
print(f"FAMILIES={family_count}")
print(f"REPORT={REPORT_PATH}")
print("ENTRY_PRICE_ROLE=ROBUSTNESS_STRATIFICATION_ONLY")
print("V1_ACCESSED=NO")
