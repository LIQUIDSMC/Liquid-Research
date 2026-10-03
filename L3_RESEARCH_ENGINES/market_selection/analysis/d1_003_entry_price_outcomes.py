#!/usr/bin/env python3
"""
LRS-1 D1-003 — Entry Price vs paper outcomes.

STATUS
------
FROZEN METHODOLOGY CANDIDATE / NOT YET AUTHORIZED FOR EXECUTION.

This artifact implements the prospectively registered D1-003 methodology.
It MUST NOT execute until:
1. the exact methodology bytes receive external audit approval,
2. the approved bytes are committed,
3. execution occurs from the exact committed methodology artifact.

D1-003 is exploratory Discovery-D analysis.
It is not V1 validation and does not establish causality, independence,
predictive superiority, or live-money edge.

IMPORTANT PRIOR-EXPOSURE LIMITATION
-----------------------------------
D1-003 is not outcome-naive with respect to entry-price context.
D1-001 and D1-002 previously exposed outcome behavior inside the same
outcome-blind D0 entry-price strata. No expected D1-003 direction is inferred
from those observations.

Until external methodology audit and commit are complete, EXECUTION_ENABLED
must remain False.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# EXECUTION LOCK
# ---------------------------------------------------------------------------

EXECUTION_ENABLED = False


# ---------------------------------------------------------------------------
# FROZEN PROVENANCE
# ---------------------------------------------------------------------------

EXPECTED_METHODOLOGY_PARENT = (
    "ffecf9b3db77ffc0a24135927a13a779ae2f3d24"
)

EXPECTED_REGISTRY_SHA256 = (
    "6aa04f6a23bde851125eaa656ac164abf01daecbacd85af9f6703914da7578dc"
)

EXPECTED_D_N = 396

EXPECTED_D_TRADE_ID_SHA256 = (
    "ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e"
)

EXPECTED_DETECTOR_SHA256 = (
    "008ca37d1f08767d6a1313872313a2e034bd85f5091f5d7df8de82269586e60e"
)

EXPECTED_FAMILY_COUNT = 207

EXPECTED_SINGLETON_FAMILY_COUNT = 149

EXPECTED_MULTI_TRADE_FAMILY_COUNT = 58

EXPECTED_TRADES_IN_MULTI_FAMILIES = 247

EXPECTED_V11_ASSIGNMENT_HASH = (
    "a0a11cd96c8d188cdab17077f38d66932c48b2f2f44acde49815a89d1a7a07c6"
)

EXPECTED_FREEZE_SHA256 = (
    "09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3"
)

EXPECTED_DERIVED_SHA256 = (
    "1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a"
)

D0_Q1 = 0.7025
D0_MEDIAN = 0.8675
D0_Q3 = 0.9537

FROZEN_MONTHS = (
    "2026-06",
    "2026-07",
    "2026-08",
    "2026-09",
)

FROZEN_SIDES = ("Yes", "No")

TRIM_FRACTION = 0.10


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

LEDGER = HERE.parent / "data" / "simulator" / "paper_trades.csv"
DETECTOR = HERE / "latent_event_family_detector_v1_1.py"
REGISTRY = HERE / "D1_candidate_statistic_log.md"
REPORT = HERE / "D1_003_entry_price_outcomes.md"

REQUIRED_LEDGER_COLUMNS = (
    "trade_id",
    "entry_price",
    "trade_won",
    "trade_pnl",
    "entry_date",
    "side",
    "category",
)


# ---------------------------------------------------------------------------
# GENERIC FAIL-CLOSED HELPERS
# ---------------------------------------------------------------------------

def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def fmt_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return "NA"
    try:
        if math.isnan(float(value)):
            return "NA"
    except (TypeError, ValueError):
        return "NA"
    return f"{float(value):.{digits}f}"


def fmt_int(value: int | np.integer) -> str:
    return str(int(value))


# ---------------------------------------------------------------------------
# FROZEN FAMILY DETECTOR LOADING
# ---------------------------------------------------------------------------

def load_detector():
    require(DETECTOR.exists(), f"Missing frozen detector: {DETECTOR}")

    detector_sha = sha256_file(DETECTOR)
    require(
        detector_sha == EXPECTED_DETECTOR_SHA256,
        (
            "Frozen detector SHA mismatch: "
            f"expected={EXPECTED_DETECTOR_SHA256} actual={detector_sha}"
        ),
    )

    spec = importlib.util.spec_from_file_location(
        "lrs1_latent_event_family_detector_v1_1",
        DETECTOR,
    )
    require(spec is not None and spec.loader is not None, "Detector import failed.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    required_attrs = (
        "d_hash",
        "v11_assignment_hash",
        "freeze_sha256",
        "derived_sha256",
        "out",
    )
    missing_attrs = [
        name for name in required_attrs
        if not hasattr(module, name)
    ]
    require(
        not missing_attrs,
        f"Frozen detector missing trusted attributes: {missing_attrs}",
    )

    require(
        module.d_hash == EXPECTED_D_TRADE_ID_SHA256,
        (
            "Frozen detector D hash mismatch: "
            f"expected={EXPECTED_D_TRADE_ID_SHA256} "
            f"actual={module.d_hash}"
        ),
    )
    require(
        module.v11_assignment_hash == EXPECTED_V11_ASSIGNMENT_HASH,
        (
            "Frozen detector v1.1 assignment hash mismatch: "
            f"expected={EXPECTED_V11_ASSIGNMENT_HASH} "
            f"actual={module.v11_assignment_hash}"
        ),
    )
    require(
        module.freeze_sha256 == EXPECTED_FREEZE_SHA256,
        (
            "Frozen detector primary freeze hash mismatch: "
            f"expected={EXPECTED_FREEZE_SHA256} "
            f"actual={module.freeze_sha256}"
        ),
    )
    require(
        module.derived_sha256 == EXPECTED_DERIVED_SHA256,
        (
            "Frozen detector derived hash mismatch: "
            f"expected={EXPECTED_DERIVED_SHA256} "
            f"actual={module.derived_sha256}"
        ),
    )

    return module


def load_frozen_family_assignment() -> pd.DataFrame:
    detector = load_detector()

    require(
        hasattr(detector, "out"),
        "Frozen detector does not expose expected `out` assignment.",
    )

    family = detector.out.copy()

    required = {"trade_id", "rule_matched", "family_key", "family_size"}
    missing = required - set(family.columns)
    require(
        not missing,
        f"Frozen family assignment missing columns: {sorted(missing)}",
    )

    family = family[
        ["trade_id", "rule_matched", "family_key", "family_size"]
    ].copy()

    require(
        len(family) == EXPECTED_D_N,
        f"Frozen family assignment n mismatch: {len(family)}",
    )

    require(
        not family["trade_id"].duplicated().any(),
        "Frozen family assignment contains duplicate trade_id values.",
    )

    family_count = int(family["family_key"].nunique(dropna=False))
    singleton_count = int(
        family.loc[family["family_size"] == 1, "family_key"].nunique()
    )
    multi_count = int(
        family.loc[family["family_size"] > 1, "family_key"].nunique()
    )
    trades_multi = int((family["family_size"] > 1).sum())

    require(
        family_count == EXPECTED_FAMILY_COUNT,
        f"Family count mismatch: {family_count}",
    )
    require(
        singleton_count == EXPECTED_SINGLETON_FAMILY_COUNT,
        f"Singleton family count mismatch: {singleton_count}",
    )
    require(
        multi_count == EXPECTED_MULTI_TRADE_FAMILY_COUNT,
        f"Multi-trade family count mismatch: {multi_count}",
    )
    require(
        trades_multi == EXPECTED_TRADES_IN_MULTI_FAMILIES,
        f"Trades-in-multi-family mismatch: {trades_multi}",
    )

    return family


# ---------------------------------------------------------------------------
# FROZEN D CONSTRUCTION
# ---------------------------------------------------------------------------

def load_frozen_d(family: pd.DataFrame) -> pd.DataFrame:
    """
    Construct D only from the exact trade identities exposed by the frozen
    detector assignment.

    No date-only reconstruction is permitted.
    """
    require(LEDGER.exists(), f"Missing paper ledger: {LEDGER}")

    header = pd.read_csv(LEDGER, nrows=0)
    missing_columns = [
        c for c in REQUIRED_LEDGER_COLUMNS if c not in header.columns
    ]
    require(
        not missing_columns,
        f"Ledger missing required columns: {missing_columns}",
    )

    ledger = pd.read_csv(
        LEDGER,
        usecols=list(REQUIRED_LEDGER_COLUMNS),
    )

    frozen_ids = family["trade_id"].copy()

    d = ledger.loc[ledger["trade_id"].isin(set(frozen_ids.tolist()))].copy()

    require(
        len(d) == EXPECTED_D_N,
        f"Frozen D ledger match n mismatch: {len(d)}",
    )
    require(
        not d["trade_id"].duplicated().any(),
        "Frozen D contains duplicate trade_id values.",
    )
    require(
        set(d["trade_id"].tolist()) == set(frozen_ids.tolist()),
        "Frozen D ledger identities do not exactly match detector identities.",
    )
    d = d.merge(
        family,
        on="trade_id",
        how="left",
        validate="one_to_one",
    )

    require(
        d["family_key"].notna().all(),
        "Frozen D contains trades without family assignment.",
    )

    return d


# ---------------------------------------------------------------------------
# MISSINGNESS / TYPE VALIDATION
# ---------------------------------------------------------------------------

def prepare_analysis_frame(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    frame = d.copy()

    missing_raw = {
        col: int(frame[col].isna().sum())
        for col in REQUIRED_LEDGER_COLUMNS
    }

    frame["entry_price_num"] = pd.to_numeric(
        frame["entry_price"],
        errors="coerce",
    )
    frame["trade_won_num"] = pd.to_numeric(
        frame["trade_won"],
        errors="coerce",
    )
    frame["trade_pnl_num"] = pd.to_numeric(
        frame["trade_pnl"],
        errors="coerce",
    )
    frame["entry_dt"] = pd.to_datetime(
        frame["entry_date"],
        errors="coerce",
    )

    invalid_numeric = {
        "entry_price": int(frame["entry_price_num"].isna().sum()),
        "trade_won": int(frame["trade_won_num"].isna().sum()),
        "trade_pnl": int(frame["trade_pnl_num"].isna().sum()),
        "entry_date": int(frame["entry_dt"].isna().sum()),
    }

    valid_side = frame["side"].isin(FROZEN_SIDES)
    invalid_side = int((~valid_side).sum())

    frame["entry_month"] = frame["entry_dt"].dt.strftime("%Y-%m")

    metadata = {
        "raw_n": int(len(frame)),
        "missing_raw": missing_raw,
        "invalid_numeric_or_date": invalid_numeric,
        "invalid_side": invalid_side,
    }

    return frame, metadata


# ---------------------------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------------------------

def pairwise_numeric(
    frame: pd.DataFrame,
    x: str,
    y: str,
) -> pd.DataFrame:
    return frame[[x, y]].dropna().copy()


def pearson_spearman(
    frame: pd.DataFrame,
    x: str,
    y: str,
) -> dict:
    pair = pairwise_numeric(frame, x, y)
    n = int(len(pair))

    if n < 2:
        return {
            "n": n,
            "pearson": None,
            "spearman": None,
        }

    if pair[x].nunique(dropna=True) < 2 or pair[y].nunique(dropna=True) < 2:
        return {
            "n": n,
            "pearson": None,
            "spearman": None,
        }

    return {
        "n": n,
        "pearson": float(pair[x].corr(pair[y], method="pearson")),
        "spearman": float(pair[x].corr(pair[y], method="spearman")),
    }


def trimmed_mean_10(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(
        dtype=float
    )
    n = len(values)

    if n < 10:
        return None

    values = np.sort(values)
    k = int(math.floor(n * TRIM_FRACTION))

    if k == 0:
        return float(values.mean())

    trimmed = values[k:n-k]

    if len(trimmed) == 0:
        return None

    return float(trimmed.mean())


def pnl_summary(frame: pd.DataFrame) -> dict:
    pnl = pd.to_numeric(frame["trade_pnl_num"], errors="coerce").dropna()
    won = pd.to_numeric(frame["trade_won_num"], errors="coerce").dropna()

    return {
        "n": int(len(frame)),
        "pnl_usable_n": int(len(pnl)),
        "win_usable_n": int(len(won)),
        "win_rate": float(won.mean()) if len(won) else None,
        "pnl_mean": float(pnl.mean()) if len(pnl) else None,
        "pnl_median": float(pnl.median()) if len(pnl) else None,
        "pnl_trim10": trimmed_mean_10(pnl),
    }


# ---------------------------------------------------------------------------
# FIXED D0 ENTRY-PRICE QUARTILES
# ---------------------------------------------------------------------------

def assign_frozen_entry_price_quartile(value: float) -> str | None:
    if pd.isna(value):
        return None
    if value <= D0_Q1:
        return "Q1"
    if value <= D0_MEDIAN:
        return "Q2"
    if value <= D0_Q3:
        return "Q3"
    return "Q4"


def quartile_analysis(frame: pd.DataFrame) -> list[dict]:
    q = frame.copy()
    q["entry_price_quartile"] = q["entry_price_num"].map(
        assign_frozen_entry_price_quartile
    )

    results = []
    for label in ("Q1", "Q2", "Q3", "Q4"):
        sub = q.loc[q["entry_price_quartile"] == label].copy()
        row = {"quartile": label}
        row.update(pnl_summary(sub))
        results.append(row)

    return results


# ---------------------------------------------------------------------------
# TEMPORAL SENSITIVITY
# ---------------------------------------------------------------------------

def temporal_analysis(frame: pd.DataFrame) -> list[dict]:
    results = []

    for month in FROZEN_MONTHS:
        sub = frame.loc[frame["entry_month"] == month].copy()

        row = {
            "month": month,
            "n": int(len(sub)),
            "entry_price_vs_trade_won": pearson_spearman(
                sub,
                "entry_price_num",
                "trade_won_num",
            ),
            "entry_price_vs_trade_pnl": pearson_spearman(
                sub,
                "entry_price_num",
                "trade_pnl_num",
            ),
        }
        row.update(pnl_summary(sub))
        results.append(row)

    return results


# ---------------------------------------------------------------------------
# TRADE-SIDE SENSITIVITY
# ---------------------------------------------------------------------------

def side_analysis(frame: pd.DataFrame) -> list[dict]:
    results = []

    for side in FROZEN_SIDES:
        sub = frame.loc[frame["side"] == side].copy()

        results.append(
            {
                "side": side,
                "n": int(len(sub)),
                "entry_price_vs_trade_won": pearson_spearman(
                    sub,
                    "entry_price_num",
                    "trade_won_num",
                ),
                "entry_price_vs_trade_pnl": pearson_spearman(
                    sub,
                    "entry_price_num",
                    "trade_pnl_num",
                ),
            }
        )

    return results


# ---------------------------------------------------------------------------
# FAMILY / DEPENDENCE SENSITIVITY
# ---------------------------------------------------------------------------

def family_analysis(frame: pd.DataFrame) -> dict:
    family_sizes = (
        frame.groupby("family_key", dropna=False)
        .size()
        .sort_values(ascending=False)
    )

    represented_families = int(len(family_sizes))
    largest_family_n = int(family_sizes.iloc[0]) if len(family_sizes) else 0

    family_means = (
        frame.groupby("family_key", as_index=False, dropna=False)
        .agg(
            entry_price_num=("entry_price_num", "mean"),
            trade_won_num=("trade_won_num", "mean"),
            trade_pnl_num=("trade_pnl_num", "mean"),
            raw_trade_n=("trade_id", "size"),
        )
    )

    return {
        "represented_families": represented_families,
        "largest_family_n": largest_family_n,
        "largest_family_share": (
            largest_family_n / len(frame) if len(frame) else None
        ),
        "family_mean_entry_price_vs_trade_won": pearson_spearman(
            family_means,
            "entry_price_num",
            "trade_won_num",
        ),
        "family_mean_entry_price_vs_trade_pnl": pearson_spearman(
            family_means,
            "entry_price_num",
            "trade_pnl_num",
        ),
        "family_means": family_means,
    }


# ---------------------------------------------------------------------------
# CATEGORY CONTEXT ONLY — NO CATEGORY OUTCOME ANALYSIS
# ---------------------------------------------------------------------------

def category_context(frame: pd.DataFrame) -> pd.DataFrame:
    counts = (
        frame["category"]
        .fillna("<MISSING>")
        .value_counts(dropna=False)
        .rename_axis("category")
        .reset_index(name="n")
    )

    counts["share"] = counts["n"] / len(frame)
    return counts


# ---------------------------------------------------------------------------
# P&L OUTLIER CONCENTRATION
# ---------------------------------------------------------------------------

def outlier_concentration(frame: pd.DataFrame) -> dict:
    pnl = pd.to_numeric(
        frame["trade_pnl_num"],
        errors="coerce",
    ).dropna()

    abs_pnl = pnl.abs().sort_values(ascending=False)

    total_realized = float(pnl.sum()) if len(pnl) else 0.0
    total_absolute = float(abs_pnl.sum()) if len(abs_pnl) else 0.0
    top3_absolute = float(abs_pnl.head(3).sum()) if len(abs_pnl) else 0.0

    concentration = (
        top3_absolute / total_absolute
        if total_absolute > 0
        else None
    )

    return {
        "usable_n": int(len(pnl)),
        "total_realized_pnl": total_realized,
        "total_absolute_pnl": total_absolute,
        "top3_absolute_pnl_sum": top3_absolute,
        "top3_over_total_absolute_pnl": concentration,
    }


# ---------------------------------------------------------------------------
# REPORT HELPERS
# ---------------------------------------------------------------------------

def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return out


def correlation_rows(label: str, result: dict) -> list[str]:
    return [
        label,
        fmt_int(result["n"]),
        fmt_float(result["pearson"]),
        fmt_float(result["spearman"]),
    ]


# ---------------------------------------------------------------------------
# REPORT GENERATION
# ---------------------------------------------------------------------------

def build_report(
    frame: pd.DataFrame,
    metadata: dict,
    overall_win: dict,
    overall_pnl: dict,
    quartiles: list[dict],
    temporal: list[dict],
    sides: list[dict],
    family: dict,
    categories: pd.DataFrame,
    outliers: dict,
) -> str:
    lines: list[str] = []

    lines.extend(
        [
            "# LRS-1 D1-003 — Entry Price vs paper outcomes",
            "",
            "## Status",
            "",
            "- Discovery population: frozen D only.",
            f"- Raw D n: {len(frame)}.",
            "- Expected direction: none; two-sided exploratory analysis.",
            "- V1 validation accessed: NO.",
            "- D1-003 is not outcome-naive with respect to entry-price context.",
            "- This report does not establish causality, independence, "
            "predictive superiority, or live-money edge.",
            "",
            "## Frozen provenance",
            "",
            f"- D trade-id SHA-256: `{EXPECTED_D_TRADE_ID_SHA256}`.",
            f"- Family detector SHA-256: `{EXPECTED_DETECTOR_SHA256}`.",
            f"- Registry SHA-256: `{EXPECTED_REGISTRY_SHA256}`.",
            "",
            "## Missingness / usability",
            "",
            f"- Raw n: {metadata['raw_n']}.",
        ]
    )

    for key, value in metadata["missing_raw"].items():
        lines.append(f"- Raw missing `{key}`: {value}.")

    for key, value in metadata["invalid_numeric_or_date"].items():
        lines.append(f"- Invalid/missing parsed `{key}`: {value}.")

    lines.append(f"- Invalid recorded side: {metadata['invalid_side']}.")
    lines.append("")

    lines.extend(
        [
            "## Primary continuous associations",
            "",
        ]
    )

    lines.extend(
        markdown_table(
            ["Outcome", "usable n", "Pearson", "Spearman"],
            [
                correlation_rows("trade_won", overall_win),
                correlation_rows("trade_pnl", overall_pnl),
            ],
        )
    )
    lines.append("")

    lines.extend(
        [
            "## Fixed D0 entry-price quartiles",
            "",
            (
                "Frozen boundaries: "
                f"Q1={D0_Q1}, median={D0_MEDIAN}, Q3={D0_Q3}."
            ),
            "",
        ]
    )

    q_rows = []
    for row in quartiles:
        q_rows.append(
            [
                row["quartile"],
                fmt_int(row["n"]),
                fmt_int(row["win_usable_n"]),
                fmt_float(row["win_rate"]),
                fmt_int(row["pnl_usable_n"]),
                fmt_float(row["pnl_mean"]),
                fmt_float(row["pnl_median"]),
                fmt_float(row["pnl_trim10"]),
            ]
        )

    lines.extend(
        markdown_table(
            [
                "Quartile",
                "n",
                "win usable n",
                "win rate",
                "P&L usable n",
                "P&L mean",
                "P&L median",
                "P&L trim10",
            ],
            q_rows,
        )
    )
    lines.append("")

    lines.extend(["## Temporal sensitivity", ""])

    temporal_rows = []
    for row in temporal:
        win_corr = row["entry_price_vs_trade_won"]
        pnl_corr = row["entry_price_vs_trade_pnl"]

        temporal_rows.append(
            [
                row["month"],
                fmt_int(row["n"]),
                fmt_float(row["win_rate"]),
                fmt_float(row["pnl_mean"]),
                fmt_float(row["pnl_median"]),
                fmt_float(row["pnl_trim10"]),
                fmt_float(win_corr["pearson"]),
                fmt_float(win_corr["spearman"]),
                fmt_float(pnl_corr["pearson"]),
                fmt_float(pnl_corr["spearman"]),
            ]
        )

    lines.extend(
        markdown_table(
            [
                "Month",
                "n",
                "win rate",
                "P&L mean",
                "P&L median",
                "P&L trim10",
                "price-win Pearson",
                "price-win Spearman",
                "price-P&L Pearson",
                "price-P&L Spearman",
            ],
            temporal_rows,
        )
    )
    lines.append("")

    lines.extend(["## Recorded-side sensitivity", ""])

    side_rows = []
    for row in sides:
        win_corr = row["entry_price_vs_trade_won"]
        pnl_corr = row["entry_price_vs_trade_pnl"]

        side_rows.append(
            [
                row["side"],
                fmt_int(row["n"]),
                fmt_int(win_corr["n"]),
                fmt_float(win_corr["pearson"]),
                fmt_float(win_corr["spearman"]),
                fmt_int(pnl_corr["n"]),
                fmt_float(pnl_corr["pearson"]),
                fmt_float(pnl_corr["spearman"]),
            ]
        )

    lines.extend(
        markdown_table(
            [
                "Side",
                "n",
                "win usable n",
                "price-win Pearson",
                "price-win Spearman",
                "P&L usable n",
                "price-P&L Pearson",
                "price-P&L Spearman",
            ],
            side_rows,
        )
    )
    lines.append("")

    lines.extend(
        [
            "## Frozen-family sensitivity",
            "",
            f"- Represented families: {family['represented_families']}.",
            f"- Largest family n: {family['largest_family_n']}.",
            (
                "- Largest-family raw-trade concentration: "
                f"{fmt_float(family['largest_family_share'])}."
            ),
            (
                "- Family-aware results are sensitivity analyses and are not "
                "proof that observations are fully independent."
            ),
            "",
        ]
    )

    lines.extend(
        markdown_table(
            ["Family-mean outcome", "families n", "Pearson", "Spearman"],
            [
                correlation_rows(
                    "trade_won",
                    family["family_mean_entry_price_vs_trade_won"],
                ),
                correlation_rows(
                    "trade_pnl",
                    family["family_mean_entry_price_vs_trade_pnl"],
                ),
            ],
        )
    )
    lines.append("")

    lines.extend(["## P&L outlier concentration", ""])
    lines.extend(
        [
            f"- P&L usable n: {outliers['usable_n']}.",
            (
                "- Total realized P&L: "
                f"{fmt_float(outliers['total_realized_pnl'])}."
            ),
            (
                "- Total absolute P&L: "
                f"{fmt_float(outliers['total_absolute_pnl'])}."
            ),
            (
                "- Sum of three largest absolute P&L magnitudes: "
                f"{fmt_float(outliers['top3_absolute_pnl_sum'])}."
            ),
            (
                "- Top-3 absolute P&L / total absolute P&L: "
                f"{fmt_float(outliers['top3_over_total_absolute_pnl'])}."
            ),
            "",
        ]
    )

    lines.extend(
        [
            "## Category composition context",
            "",
            (
                "Category is reported for population context only. "
                "No category-specific outcome analysis is authorized."
            ),
            "",
        ]
    )

    category_rows = []
    for _, row in categories.iterrows():
        category_rows.append(
            [
                str(row["category"]),
                fmt_int(row["n"]),
                fmt_float(row["share"]),
            ]
        )

    lines.extend(
        markdown_table(
            ["Category", "n", "share"],
            category_rows,
        )
    )
    lines.append("")

    lines.extend(
        [
            "## Interpretation constraints",
            "",
            "- D1-003 is exploratory Discovery-D evidence.",
            (
                "- Earlier D1 analyses already exposed outcome behavior across "
                "entry-price contexts; D1-003 is therefore not outcome-naive."
            ),
            (
                "- No observed D1-003 effect may be represented as independent "
                "validation merely because it is statistically or economically "
                "large."
            ),
            (
                "- Continuous and fixed-quartile views are one candidate family, "
                "not independent candidate discoveries."
            ),
            (
                "- Temporal, side, family, and outlier views are robustness "
                "sensitivities, not separate candidate searches."
            ),
            "- No V1 promotion is implied by execution of this report.",
            "",
        ]
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------------------------

def main() -> int:
    if not EXECUTION_ENABLED:
        print(
            "EXECUTION_BLOCKED=YES\n"
            "REASON=D1-003 methodology requires external audit and committed "
            "authorization before outcome-facing execution.\n"
            "OUTCOMES_ACCESSED=NO\n"
            "V1_ACCESSED=NO"
        )
        return 3

    require(
        sha256_file(REGISTRY) == EXPECTED_REGISTRY_SHA256,
        "Frozen D1 registry SHA mismatch.",
    )

    family = load_frozen_family_assignment()
    d = load_frozen_d(family)
    frame, metadata = prepare_analysis_frame(d)

    overall_win = pearson_spearman(
        frame,
        "entry_price_num",
        "trade_won_num",
    )
    overall_pnl = pearson_spearman(
        frame,
        "entry_price_num",
        "trade_pnl_num",
    )

    quartiles = quartile_analysis(frame)
    temporal = temporal_analysis(frame)
    sides = side_analysis(frame)
    family_result = family_analysis(frame)
    categories = category_context(frame)
    outliers = outlier_concentration(frame)

    report = build_report(
        frame=frame,
        metadata=metadata,
        overall_win=overall_win,
        overall_pnl=overall_pnl,
        quartiles=quartiles,
        temporal=temporal,
        sides=sides,
        family=family_result,
        categories=categories,
        outliers=outliers,
    )

    require(
        not REPORT.exists(),
        f"Refusing to overwrite existing D1-003 report: {REPORT}",
    )

    REPORT.write_text(report + "\n", encoding="utf-8")

    print(f"D1_003_EXECUTED=YES")
    print(f"D_N={len(frame)}")
    print(f"FAMILY_COUNT={family_result['represented_families']}")
    print(f"REPORT={REPORT}")
    print(f"REPORT_SHA256={sha256_file(REPORT)}")
    print("V1_ACCESSED=NO")

    return 0


if __name__ == "__main__":
    sys.exit(main())
