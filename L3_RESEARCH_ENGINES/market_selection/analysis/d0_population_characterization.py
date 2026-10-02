"""
LRS-1 D0 — Outcome-Blind Population Characterization

PURPOSE
-------
Describe the geometry of the frozen D population before D1 outcome discovery.

HARD BOUNDARIES
---------------
- D0 does not load economic outcome fields.
- D0 does not inspect trade_won, trade_pnl, winning_outcome, exit_reason.
- D0 does not generate or rank economic hypotheses.
- D0 does not choose buckets/cutoffs from observed distributions.
- Family assignments come only from the exact frozen v1.1 detector.
- The detector is SHA-256 gated before import.
- The frozen detector executes via importlib; D0 does not reimplement its logic.
- D0 extracts only trade_id, rule_matched, family_key, family_size from detector output.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd


# ============================================================
# FROZEN PROVENANCE
# ============================================================

DETECTOR_PATH = Path("/tmp/latent_event_family_detector_v1_1.py")

EXPECTED_DETECTOR_SHA256 = (
    "008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e"
)

EXPECTED_D_N = 396
EXPECTED_D_HASH = (
    "ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e"
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

LEDGER_PATH = Path(
    "L3_RESEARCH_ENGINES/market_selection/data/simulator/paper_trades.csv"
)

REPORT_PATH = Path("/tmp/D0_population_characterization.md")


# ============================================================
# D0 LEDGER ALLOWLIST
# ============================================================

D0_COLS = [
    "trade_id",
    "market_id",
    "entry_date",
    "scanner_run_id",
    "tradeability_score_at_entry",
    "entry_price",
    "liquidity",
    "volume_24h",
    "spread_label",
    "side",
    "category",
    "category_tier",
    "recurrence_count",
]

PROHIBITED_OUTCOME_COLS = {
    "status",
    "resolution_date",
    "winning_outcome",
    "trade_won",
    "trade_pnl",
    "exit_reason",
}

FAMILY_COLS = [
    "trade_id",
    "rule_matched",
    "family_key",
    "family_size",
]


# ============================================================
# HELPERS
# ============================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def fmt_num(x, digits=4):
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{digits}f}"


def pct(n: int, d: int) -> str:
    if d == 0:
        return "NA"
    return f"{100.0 * n / d:.2f}%"


def continuous_summary(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()

    if len(valid) == 0:
        return {
            "n": 0,
            "missing": len(s),
            "mean": math.nan,
            "sd": math.nan,
            "min": math.nan,
            "q1": math.nan,
            "median": math.nan,
            "q3": math.nan,
            "max": math.nan,
        }

    return {
        "n": int(valid.size),
        "missing": int(s.isna().sum()),
        "mean": valid.mean(),
        "sd": valid.std(ddof=1),
        "min": valid.min(),
        "q1": valid.quantile(0.25),
        "median": valid.median(),
        "q3": valid.quantile(0.75),
        "max": valid.max(),
    }


def corr_pair(df: pd.DataFrame, a: str, b: str) -> dict:
    x = pd.to_numeric(df[a], errors="coerce")
    y = pd.to_numeric(df[b], errors="coerce")

    pair = pd.DataFrame({"x": x, "y": y}).dropna()

    if len(pair) < 2:
        return {
            "n": len(pair),
            "pearson": math.nan,
            "spearman": math.nan,
        }

    # Spearman correlation is Pearson correlation of ranks.
    # Compute ranks directly with pandas so D0 does not require SciPy
    # on the Pi3 runtime.
    x_rank = pair["x"].rank(method="average")
    y_rank = pair["y"].rank(method="average")

    return {
        "n": int(len(pair)),
        "pearson": pair["x"].corr(pair["y"], method="pearson"),
        "spearman": x_rank.corr(y_rank, method="pearson"),
    }


def categorical_counts(series: pd.Series) -> pd.DataFrame:
    s = series.astype("string").fillna("<MISSING>")
    counts = s.value_counts(dropna=False)
    total = int(counts.sum())

    return pd.DataFrame(
        {
            "value": counts.index.astype(str),
            "n": counts.values.astype(int),
            "percent": [
                100.0 * int(n) / total if total else math.nan
                for n in counts.values
            ],
        }
    )


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None_"

    cols = list(df.columns)

    def clean_cell(v):
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
            "| "
            + " | ".join(clean_cell(row[c]) for c in cols)
            + " |"
        )

    return "\n".join(lines)


# ============================================================
# GATE 1 — EXACT FROZEN DETECTOR ARTIFACT
# ============================================================

if not DETECTOR_PATH.is_file():
    fail(f"Frozen detector scratch file not found: {DETECTOR_PATH}")

detector_sha = sha256_file(DETECTOR_PATH)

if detector_sha != EXPECTED_DETECTOR_SHA256:
    fail(
        "Frozen detector SHA mismatch.\n"
        f"expected={EXPECTED_DETECTOR_SHA256}\n"
        f"actual={detector_sha}"
    )


# ============================================================
# GATE 2 — EXECUTE EXACT FROZEN DETECTOR VIA IMPORTLIB
# ============================================================

spec = importlib.util.spec_from_file_location(
    "lrs1_latent_event_family_detector_v1_1_frozen",
    DETECTOR_PATH,
)

if spec is None or spec.loader is None:
    fail("Could not construct importlib spec for frozen detector.")

detector = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(detector)
except Exception as exc:
    fail(
        "Frozen detector execution failed closed: "
        f"{type(exc).__name__}: {exc}"
    )


# ============================================================
# GATE 3 — DEFENSIVE STRUCTURED PROVENANCE CHECKS
# ============================================================

required_attrs = [
    "out",
    "d_hash",
    "v11_assignment_hash",
    "freeze_sha256",
    "derived_sha256",
]

missing_attrs = [
    name for name in required_attrs
    if not hasattr(detector, name)
]

if missing_attrs:
    fail(
        "Frozen detector missing required module attributes: "
        + ", ".join(missing_attrs)
    )

if detector.d_hash != EXPECTED_D_HASH:
    fail(
        "D fingerprint mismatch after detector execution.\n"
        f"expected={EXPECTED_D_HASH}\n"
        f"actual={detector.d_hash}"
    )

if detector.v11_assignment_hash != EXPECTED_V11_ASSIGNMENT_HASH:
    fail(
        "v1.1 assignment hash mismatch.\n"
        f"expected={EXPECTED_V11_ASSIGNMENT_HASH}\n"
        f"actual={detector.v11_assignment_hash}"
    )

if detector.freeze_sha256 != EXPECTED_PRIMARY_SHA256:
    fail(
        "Primary freeze hash mismatch.\n"
        f"expected={EXPECTED_PRIMARY_SHA256}\n"
        f"actual={detector.freeze_sha256}"
    )

if detector.derived_sha256 != EXPECTED_DERIVED_SHA256:
    fail(
        "Derived freeze hash mismatch.\n"
        f"expected={EXPECTED_DERIVED_SHA256}\n"
        f"actual={detector.derived_sha256}"
    )

if not isinstance(detector.out, pd.DataFrame):
    fail("detector.out is not a pandas DataFrame.")

if len(detector.out) != EXPECTED_D_N:
    fail(
        f"Detector D population size mismatch: "
        f"{len(detector.out)} != {EXPECTED_D_N}"
    )

missing_family_cols = [
    c for c in FAMILY_COLS
    if c not in detector.out.columns
]

if missing_family_cols:
    fail(
        "Detector output missing required assignment columns: "
        + ", ".join(missing_family_cols)
    )

family = detector.out[FAMILY_COLS].copy()

if family["trade_id"].isna().any():
    fail("Frozen family assignment contains null trade_id.")

if family["trade_id"].duplicated().any():
    fail("Frozen family assignment contains duplicate trade_id.")

if family["trade_id"].nunique() != EXPECTED_D_N:
    fail("Frozen family assignment does not contain 396 unique trade IDs.")


# ============================================================
# GATE 4 — OUTCOME-FREE D0 LEDGER LOAD
# ============================================================

if set(D0_COLS) & PROHIBITED_OUTCOME_COLS:
    fail("Programming error: D0 allowlist contains prohibited outcome fields.")

if not LEDGER_PATH.is_file():
    fail(f"Authoritative ledger not found: {LEDGER_PATH}")

d0_ledger = pd.read_csv(
    LEDGER_PATH,
    usecols=D0_COLS,
)

if set(d0_ledger.columns) != set(D0_COLS):
    fail("Ledger load did not return the exact D0 allowlist.")

if set(d0_ledger.columns) & PROHIBITED_OUTCOME_COLS:
    fail("Outcome field entered D0 ledger dataframe.")

if d0_ledger["trade_id"].duplicated().any():
    fail("Authoritative ledger contains duplicate trade_id values.")


# ============================================================
# GATE 5 — EXACT D JOIN
# ============================================================

d0 = family.merge(
    d0_ledger,
    on="trade_id",
    how="left",
    validate="one_to_one",
    indicator=True,
)

if not d0["_merge"].eq("both").all():
    bad = d0.loc[
        ~d0["_merge"].eq("both"),
        ["trade_id", "_merge"],
    ]
    fail(
        "Not every frozen D trade_id matched the authoritative ledger:\n"
        + bad.to_string(index=False)
    )

d0 = d0.drop(columns="_merge")

if len(d0) != EXPECTED_D_N:
    fail(f"D0 joined population is {len(d0)}, expected 396.")

if d0["trade_id"].nunique() != EXPECTED_D_N:
    fail("D0 joined population does not contain 396 unique trade IDs.")

if set(d0.columns) & PROHIBITED_OUTCOME_COLS:
    fail("Outcome field entered final D0 dataframe.")


# ============================================================
# DESCRIPTIVE POPULATION GEOMETRY
# ============================================================

CONTINUOUS = [
    "tradeability_score_at_entry",
    "entry_price",
    "liquidity",
    "volume_24h",
]

continuous_rows = []

for col in CONTINUOUS:
    s = continuous_summary(d0[col])
    continuous_rows.append(
        {
            "variable": col,
            **s,
        }
    )

continuous_df = pd.DataFrame(continuous_rows)


# Missingness is restricted to explicitly authorized D0 variables.
missingness_rows = []

for col in D0_COLS:
    missingness_rows.append(
        {
            "variable": col,
            "missing_n": int(d0[col].isna().sum()),
            "usable_n": int(d0[col].notna().sum()),
        }
    )

missingness_df = pd.DataFrame(missingness_rows)


# Family geometry derives only from frozen family_key/family_size.
family_groups = (
    d0.groupby("family_key", dropna=False)
    .agg(
        family_size=("trade_id", "size"),
        rule_matched=("rule_matched", "first"),
    )
    .reset_index()
)

family_size_distribution = (
    family_groups["family_size"]
    .value_counts()
    .sort_index()
    .rename_axis("family_size")
    .reset_index(name="family_count")
)

family_size_distribution["trade_count"] = (
    family_size_distribution["family_size"]
    * family_size_distribution["family_count"]
)

family_size_distribution["trade_percent"] = (
    100.0
    * family_size_distribution["trade_count"]
    / EXPECTED_D_N
)

largest_families = (
    family_groups
    .sort_values(
        ["family_size", "family_key"],
        ascending=[False, True],
    )
    .head(10)
    .copy()
)

largest_families["trade_percent_of_D"] = (
    100.0 * largest_families["family_size"] / EXPECTED_D_N
)


# ============================================================
# CATEGORICAL / CONTEXT GEOMETRY
# ============================================================

category_df = categorical_counts(d0["category"])
category_tier_df = categorical_counts(d0["category_tier"])
spread_df = categorical_counts(d0["spread_label"])
side_df = categorical_counts(d0["side"])

entry_dates = pd.to_datetime(
    d0["entry_date"],
    errors="coerce",
)

entry_date_missing = int(entry_dates.isna().sum())
entry_date_min = entry_dates.min()
entry_date_max = entry_dates.max()

month_counts = (
    entry_dates
    .dt.to_period("M")
    .astype("string")
    .fillna("<MISSING>")
    .value_counts()
    .sort_index()
)

temporal_df = pd.DataFrame(
    {
        "month": month_counts.index.astype(str),
        "n": month_counts.values.astype(int),
    }
)

scanner_df = (
    d0["scanner_run_id"]
    .astype("string")
    .fillna("<MISSING>")
    .value_counts()
    .rename_axis("scanner_run_id")
    .reset_index(name="n")
)

scanner_df["percent"] = (
    100.0 * scanner_df["n"] / EXPECTED_D_N
)


# ============================================================
# FROZEN P1-P5 PREDICTOR RELATIONSHIPS
# ============================================================

p1 = corr_pair(
    d0,
    "tradeability_score_at_entry",
    "entry_price",
)

p2 = corr_pair(
    d0,
    "tradeability_score_at_entry",
    "liquidity",
)

p3 = corr_pair(
    d0,
    "tradeability_score_at_entry",
    "volume_24h",
)

p5 = corr_pair(
    d0,
    "entry_price",
    "liquidity",
)

pair_df = pd.DataFrame(
    [
        {
            "pair": "P1 score vs entry_price",
            **p1,
        },
        {
            "pair": "P2 score vs liquidity",
            **p2,
        },
        {
            "pair": "P3 score vs volume_24h",
            **p3,
        },
        {
            "pair": "P5 entry_price vs liquidity",
            **p5,
        },
    ]
)


# P4: score distribution by spread label.
p4_rows = []

for label, group in d0.groupby(
    "spread_label",
    dropna=False,
    sort=True,
):
    score = pd.to_numeric(
        group["tradeability_score_at_entry"],
        errors="coerce",
    ).dropna()

    p4_rows.append(
        {
            "spread_label": (
                "<MISSING>"
                if pd.isna(label)
                else str(label)
            ),
            "n": int(len(group)),
            "score_usable_n": int(len(score)),
            "mean": score.mean() if len(score) else math.nan,
            "q1": (
                score.quantile(0.25)
                if len(score)
                else math.nan
            ),
            "median": (
                score.median()
                if len(score)
                else math.nan
            ),
            "q3": (
                score.quantile(0.75)
                if len(score)
                else math.nan
            ),
        }
    )

p4_df = pd.DataFrame(p4_rows)


# ============================================================
# HISTORICAL MARKET_ID DUPLICATION GEOMETRY
# ============================================================

market_counts = (
    d0.groupby("market_id", dropna=False)
    .size()
    .rename("trade_count")
)

duplicate_market_counts = market_counts[market_counts > 1]

duplicate_market_ids = set(
    duplicate_market_counts.index.tolist()
)

duplicate_trade_mask = d0["market_id"].isin(
    duplicate_market_ids
)

duplicate_trade_count = int(duplicate_trade_mask.sum())
duplicate_group_count = int(len(duplicate_market_counts))
duplicate_excess_rows = int(
    (duplicate_market_counts - 1).sum()
)

duplicate_family_rows = []

for market_id in sorted(
    duplicate_market_ids,
    key=lambda x: str(x),
):
    g = d0[d0["market_id"] == market_id]

    family_keys = sorted(
        g["family_key"].astype(str).unique().tolist()
    )

    duplicate_family_rows.append(
        {
            "market_id": str(market_id),
            "trade_count": int(len(g)),
            "family_key_count": int(len(family_keys)),
            "same_frozen_family": (
                len(family_keys) == 1
            ),
        }
    )

duplicate_family_df = pd.DataFrame(
    duplicate_family_rows
)

duplicate_groups_same_family = (
    int(duplicate_family_df["same_frozen_family"].sum())
    if not duplicate_family_df.empty
    else 0
)

duplicate_groups_multiple_families = (
    duplicate_group_count
    - duplicate_groups_same_family
)


# ============================================================
# recurrence_count STRUCTURAL CROSS-CHECK
# ============================================================

recurrence_numeric = pd.to_numeric(
    d0["recurrence_count"],
    errors="coerce",
)

recurrence_missing = int(recurrence_numeric.isna().sum())

# Independent within-D recurrence ordinal:
# 0 for first occurrence of a market_id, 1 for second, etc.,
# ordered deterministically by trade_id.
recurrence_check = d0[
    ["trade_id", "market_id", "recurrence_count"]
].copy()

recurrence_check = recurrence_check.sort_values(
    "trade_id"
).reset_index(drop=True)

recurrence_check["computed_within_D_recurrence"] = (
    recurrence_check.groupby(
        "market_id",
        dropna=False,
    ).cumcount()
)

recurrence_check["recorded_recurrence"] = pd.to_numeric(
    recurrence_check["recurrence_count"],
    errors="coerce",
)

recurrence_comparable = recurrence_check[
    recurrence_check["recorded_recurrence"].notna()
].copy()

recurrence_exact_matches = int(
    (
        recurrence_comparable["recorded_recurrence"]
        == recurrence_comparable[
            "computed_within_D_recurrence"
        ]
    ).sum()
)

recurrence_recorded_gt_within_D = int(
    (
        recurrence_comparable["recorded_recurrence"]
        > recurrence_comparable[
            "computed_within_D_recurrence"
        ]
    ).sum()
)

recurrence_recorded_lt_within_D = int(
    (
        recurrence_comparable["recorded_recurrence"]
        < recurrence_comparable[
            "computed_within_D_recurrence"
        ]
    ).sum()
)


# ============================================================
# REPORT
# ============================================================

lines = []

lines.append("# LRS-1 D0 — Population Characterization")
lines.append("")
lines.append(
    "**EXECUTION EVIDENCE — PENDING AUDIT, "
    "NOT A VALIDATED FINDING**"
)
lines.append("")
lines.append(
    "D0 is descriptive and outcome-blind. "
    "It characterizes the frozen D population geometry "
    "before D1 outcome discovery."
)
lines.append("")

lines.append("## Provenance gates")
lines.append("")
lines.append(f"- D n: **{len(d0)}**")
lines.append(f"- Detector SHA-256: `{detector_sha}`")
lines.append(f"- D trade-id SHA-256: `{detector.d_hash}`")
lines.append(
    "- v1.1 assignment SHA-256: "
    f"`{detector.v11_assignment_hash}`"
)
lines.append(
    "- Primary assignment SHA-256: "
    f"`{detector.freeze_sha256}`"
)
lines.append(
    "- Derived assignment SHA-256: "
    f"`{detector.derived_sha256}`"
)
lines.append("- Outcome fields loaded by D0: **NONE**")
lines.append("- Outcome relationships examined: **NONE**")
lines.append("")

lines.append("## Authorized D0 ledger columns")
lines.append("")
for col in D0_COLS:
    lines.append(f"- `{col}`")
lines.append("")

lines.append("## Missingness / usable n")
lines.append("")
lines.append(markdown_table(missingness_df))
lines.append("")

lines.append("## Continuous-variable geometry")
lines.append("")
lines.append(markdown_table(continuous_df))
lines.append("")

lines.append("## Frozen family geometry")
lines.append("")
lines.append(
    f"- Frozen families represented: "
    f"**{family_groups['family_key'].nunique()}**"
)
lines.append(
    f"- Singleton families: "
    f"**{int((family_groups['family_size'] == 1).sum())}**"
)
lines.append(
    f"- Multi-trade families: "
    f"**{int((family_groups['family_size'] > 1).sum())}**"
)
lines.append(
    f"- Trades in multi-trade families: "
    f"**{int(d0.loc[d0['family_size'] > 1, 'trade_id'].count())} "
    f"({pct(int((d0['family_size'] > 1).sum()), len(d0))})**"
)
lines.append("")
lines.append("### Family-size distribution")
lines.append("")
lines.append(markdown_table(family_size_distribution))
lines.append("")
lines.append("### Ten largest frozen families")
lines.append("")
lines.append(markdown_table(largest_families))
lines.append("")

lines.append("## Category composition")
lines.append("")
lines.append(markdown_table(category_df))
lines.append("")

lines.append("## Category-tier composition")
lines.append("")
lines.append(markdown_table(category_tier_df))
lines.append("")

lines.append("## Spread-label composition")
lines.append("")
lines.append(markdown_table(spread_df))
lines.append("")

lines.append("## Side composition")
lines.append("")
lines.append(markdown_table(side_df))
lines.append("")

lines.append("## Temporal coverage")
lines.append("")
lines.append(
    f"- Earliest parsed entry date: "
    f"**{entry_date_min if pd.notna(entry_date_min) else 'NA'}**"
)
lines.append(
    f"- Latest parsed entry date: "
    f"**{entry_date_max if pd.notna(entry_date_max) else 'NA'}**"
)
lines.append(
    f"- Unparseable/missing entry dates: "
    f"**{entry_date_missing}**"
)
lines.append("")
lines.append(markdown_table(temporal_df))
lines.append("")

lines.append("## Scanner-run cohort composition")
lines.append("")
lines.append(markdown_table(scanner_df))
lines.append("")

lines.append("## Frozen predictor relationships P1-P5")
lines.append("")
lines.append(
    "These relationships are descriptive predictor/context "
    "geometry only. No economic outcome is involved."
)
lines.append("")
lines.append("### P1 / P2 / P3 / P5")
lines.append("")
lines.append(markdown_table(pair_df))
lines.append("")
lines.append("### P4 — score distribution by spread label")
lines.append("")
lines.append(markdown_table(p4_df))
lines.append("")

lines.append("## Historical market_id duplication geometry")
lines.append("")
lines.append(
    f"- Unique market_id values in D: "
    f"**{int(d0['market_id'].nunique(dropna=False))}**"
)
lines.append(
    f"- Duplicated market_id groups: "
    f"**{duplicate_group_count}**"
)
lines.append(
    f"- Excess rows beyond one trade per market_id: "
    f"**{duplicate_excess_rows}**"
)
lines.append(
    f"- Trades belonging to duplicated market_id groups: "
    f"**{duplicate_trade_count} "
    f"({pct(duplicate_trade_count, len(d0))})**"
)
lines.append(
    f"- Duplicated market groups wholly within one "
    f"frozen family: **{duplicate_groups_same_family}**"
)
lines.append(
    f"- Duplicated market groups spanning multiple "
    f"frozen families: **{duplicate_groups_multiple_families}**"
)
lines.append("")
lines.append(markdown_table(duplicate_family_df))
lines.append("")

lines.append("## recurrence_count structural cross-check")
lines.append("")
lines.append(
    f"- recurrence_count missing in D: "
    f"**{recurrence_missing}**"
)
lines.append(
    f"- Comparable rows: "
    f"**{len(recurrence_comparable)}**"
)
lines.append(
    f"- Exact matches to independently computed "
    f"within-D recurrence ordinal: "
    f"**{recurrence_exact_matches}**"
)
lines.append(
    f"- Recorded recurrence greater than recurrence visible "
    f"within D: **{recurrence_recorded_gt_within_D}**"
)
lines.append(
    f"- Recorded recurrence less than recurrence visible "
    f"within D: **{recurrence_recorded_lt_within_D}**"
)
lines.append("")
lines.append(
    "This is a structural provenance cross-check, not an "
    "equality invariant. recurrence_count records historical "
    "recurrence state at trade creation, whereas the computed "
    "ordinal only counts occurrences visible inside frozen D. "
    "Therefore recorded recurrence may legitimately exceed "
    "within-D recurrence when earlier occurrences are outside D."
)
lines.append("")

lines.append("## D0 boundary")
lines.append("")
lines.append("- `trade_won`: **NOT LOADED**")
lines.append("- `trade_pnl`: **NOT LOADED**")
lines.append("- `winning_outcome`: **NOT LOADED**")
lines.append("- `exit_reason`: **NOT LOADED**")
lines.append("- `status`: **NOT LOADED BY D0 ANALYSIS DATAFRAME**")
lines.append(
    "- `resolution_date`: "
    "**NOT LOADED BY D0 ANALYSIS DATAFRAME**"
)
lines.append("")
lines.append(
    "The frozen detector independently uses its previously "
    "audited identity/status/date fields only to reconstruct "
    "the frozen D population and family assignments."
)
lines.append("")
lines.append(
    "**No D1 economic hypothesis has been generated, tested, "
    "ranked, promoted, or rejected by this report.**"
)
lines.append("")

REPORT_PATH.write_text(
    "\n".join(lines).rstrip() + "\n",
    encoding="utf-8",
)

print()
print("===== LRS-1 D0 BUILD / STATIC GATE =====")
print(f"SCRIPT={Path(__file__).resolve()}")
print(f"REPORT_TARGET={REPORT_PATH}")
print(f"D0_ALLOWED_LEDGER_COLUMNS={len(D0_COLS)}")
print("OUTCOME_FIELDS_IN_D0_ALLOWLIST=NONE")
print("FROZEN_PREDICTOR_RELATIONSHIPS=P1,P2,P3,P4,P5")
print("FAMILY_SOURCE=FROZEN_v1.1_DETECTOR_ONLY")
print("DETECTOR_IMPORT_ATTRIBUTE=v11_assignment_hash")
print("D0 SCRIPT BUILD: READY FOR PI3 EXECUTION")
