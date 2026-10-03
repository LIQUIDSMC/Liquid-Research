#!/usr/bin/env python3
"""
LRS-1 D1-003 protected-V1 validation.

FAIL-CLOSED STATUS
------------------
This artifact implements the frozen D1-003 V1 validation specification.

It MUST NOT access the prediction-market ledger, V1 outcomes, or create the
validation report unless all execution gates pass.

The source artifact is created with EXECUTION_ENABLED = False.

Execution requires a separately audited authorization change plus an externally
supplied exact audited script SHA-256. The script verifies its own bytes against
that supplied SHA before loading the outcome-bearing ledger.

V1 is validation, not discovery. No predictor, threshold, population rule,
classification rule, or sensitivity may be modified after V1 is opened.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.stats import spearmanr


# ---------------------------------------------------------------------------
# EXECUTION AUTHORIZATION — MUST REMAIN FALSE DURING CREATION / AUDIT
# ---------------------------------------------------------------------------

EXECUTION_ENABLED = True


# ---------------------------------------------------------------------------
# FROZEN GOVERNANCE / PROVENANCE
# ---------------------------------------------------------------------------

EXPECTED_METHODOLOGY_COMMIT = (
    "31faa3faa341de7ccdafaf32214306883b48a6bb"
)

EXPECTED_SPEC_SHA256 = (
    "96362fa3025a11a5fcc4c4cf6d21674f1ccf86a4535b4d34e6b019ba8bfb14f7"
)

EXPECTED_SCIPY_VERSION = "1.18.1"

EXPECTED_D_N = 396
EXPECTED_V1_N = 80

EXPECTED_D_TRADE_ID_SHA256 = (
    "ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e"
)

EXPECTED_V1_TRADE_ID_SHA256 = (
    "a8295f43480699e98f27c87fb67e943bc7f26999529e61af4e1635fa3168e141"
)

# Exact protected-V1 identities recovered outcome-blind from the historical
# 476-closed-trade boundary and independently verified against the already-
# frozen EXPECTED_V1_TRADE_ID_SHA256. Runtime membership is identity-based;
# no date cutoff participates in validation execution.
EXPECTED_V1_TRADE_IDS = frozenset(
    {
        "105", "202", "212", "229", "233", "243", "288", "298",
        "309", "313", "324", "339", "344", "353", "360", "414",
        "456", "471", "472", "484", "487", "490", "491", "492",
        "500", "505", "525", "540", "541", "544", "556", "557",
        "564", "565", "570", "573", "584", "586", "592", "594",
        "595", "596", "598", "602", "606", "614", "615", "616",
        "617", "619", "621", "622", "625", "626", "627", "632",
        "633", "634", "638", "639", "641", "642", "643", "644",
        "647", "648", "649", "650", "651", "652", "656", "659",
        "660", "663", "664", "666", "667", "671", "69", "85",
    }
)

EXPECTED_V11_ASSIGNMENT_HASH = (
    "a0a11cd96c8d188cdab17077f38d66932c48b2f2f44acde49815a89d1a7a07c6"
)

EXPECTED_FREEZE_SHA256 = (
    "09ed62c74381fae6097c671b8377a0b027ae2188b858bf3e66abf34dfaca5ca3"
)

EXPECTED_DERIVED_SHA256 = (
    "1a7dff2b1ed8258995856aa30c0dced178e5393505406088b66ea680f815662a"
)

EXPECTED_FAMILY_COUNT = 207
EXPECTED_SINGLETON_FAMILY_COUNT = 149
EXPECTED_MULTI_TRADE_FAMILY_COUNT = 58
EXPECTED_TRADES_IN_MULTI_FAMILIES = 247

PRIMARY_ALPHA = 0.05

Q1_MAX = 0.7025
Q2_MAX = 0.8675
Q3_MAX = 0.9537


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
SELF = Path(__file__).resolve()

SPEC = HERE / "D1_003_V1_validation_specification.md"
DETECTOR = HERE / "latent_event_family_detector_v1_1.py"
LEDGER = HERE.parent / "data" / "simulator" / "paper_trades.csv"
REPORT = HERE / "D1_003_V1_validation.md"


# ---------------------------------------------------------------------------
# BASIC FAIL-CLOSED UTILITIES
# ---------------------------------------------------------------------------

def fail(message: str) -> None:
    raise RuntimeError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def trade_id_hash(values) -> str:
    """
    Frozen identity serialization:
    string form -> lexicographic sort -> newline join -> SHA-256.
    """
    payload = "\n".join(sorted(str(x) for x in values)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def finite_or_none(value) -> float | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def fmt_float(value: float | None, digits: int = 6) -> str:
    value = finite_or_none(value)
    return "NA" if value is None else f"{value:.{digits}f}"


def fmt_int(value) -> str:
    return "NA" if value is None else str(int(value))


# ---------------------------------------------------------------------------
# PRE-LEDGER AUTHORITY GATES
# ---------------------------------------------------------------------------

def verify_preledger_authority() -> str:
    """
    Every check in this function occurs before LEDGER is read.
    """

    require(
        EXECUTION_ENABLED,
        "Execution disabled. V1 remains sealed.",
    )

    require(
        os.environ.get("LRS1_V1_EXECUTION_AUTHORIZED") == "YES",
        "Missing explicit V1 execution authorization environment gate.",
    )

    supplied_sha = os.environ.get("LRS1_V1_EXPECTED_SCRIPT_SHA256", "").strip()

    require(
        len(supplied_sha) == 64,
        "Missing externally supplied audited validation-script SHA-256.",
    )

    actual_sha = sha256_file(SELF)

    require(
        actual_sha == supplied_sha,
        (
            "Validation-script SHA mismatch: "
            f"expected={supplied_sha} actual={actual_sha}"
        ),
    )

    require(
        SPEC.exists(),
        f"Missing frozen V1 specification: {SPEC}",
    )

    require(
        sha256_file(SPEC) == EXPECTED_SPEC_SHA256,
        "Frozen V1 specification SHA mismatch.",
    )

    require(
        scipy.__version__ == EXPECTED_SCIPY_VERSION,
        (
            "SciPy version mismatch: "
            f"expected={EXPECTED_SCIPY_VERSION} actual={scipy.__version__}"
        ),
    )

    require(
        not REPORT.exists(),
        (
            "Validation report already exists. Refusing overwrite/re-execution: "
            f"{REPORT}"
        ),
    )

    return actual_sha


# ---------------------------------------------------------------------------
# FROZEN D / FAMILY AUTHORITY
# ---------------------------------------------------------------------------

def load_detector():
    require(DETECTOR.exists(), f"Missing frozen detector: {DETECTOR}")

    spec = importlib.util.spec_from_file_location(
        "lrs1_latent_event_family_detector_v1_1",
        DETECTOR,
    )
    require(spec is not None and spec.loader is not None, "Detector import failed.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    required_attrs = {
        "out",
        "d_hash",
        "v11_assignment_hash",
        "freeze_sha256",
        "derived_sha256",
    }

    missing = sorted(x for x in required_attrs if not hasattr(module, x))
    require(not missing, f"Frozen detector missing trusted attributes: {missing}")

    require(
        module.d_hash == EXPECTED_D_TRADE_ID_SHA256,
        "Frozen detector D hash mismatch.",
    )
    require(
        module.v11_assignment_hash == EXPECTED_V11_ASSIGNMENT_HASH,
        "Frozen detector v1.1 assignment hash mismatch.",
    )
    require(
        module.freeze_sha256 == EXPECTED_FREEZE_SHA256,
        "Frozen detector primary freeze SHA mismatch.",
    )
    require(
        module.derived_sha256 == EXPECTED_DERIVED_SHA256,
        "Frozen detector derived SHA mismatch.",
    )

    return module


def load_frozen_family_assignment() -> tuple[object, pd.DataFrame]:
    detector = load_detector()
    family = detector.out.copy()

    required = {"trade_id", "rule_matched", "family_key", "family_size"}
    require(
        required.issubset(family.columns),
        f"Frozen family assignment missing columns: {sorted(required - set(family.columns))}",
    )

    family = family[
        ["trade_id", "rule_matched", "family_key", "family_size"]
    ].copy()

    require(len(family) == EXPECTED_D_N, "Frozen family assignment n mismatch.")
    require(
        not family["trade_id"].duplicated().any(),
        "Frozen family assignment contains duplicate trade_id.",
    )
    require(
        trade_id_hash(family["trade_id"]) == EXPECTED_D_TRADE_ID_SHA256,
        "Frozen family assignment trade-id SHA mismatch.",
    )

    family_count = int(family["family_key"].nunique(dropna=False))
    singleton_count = int(
        family.loc[family["family_size"] == 1, "family_key"].nunique(dropna=False)
    )
    multi_count = int(
        family.loc[family["family_size"] > 1, "family_key"].nunique(dropna=False)
    )
    trades_multi = int((family["family_size"] > 1).sum())

    require(family_count == EXPECTED_FAMILY_COUNT, "Family count mismatch.")
    require(
        singleton_count == EXPECTED_SINGLETON_FAMILY_COUNT,
        "Singleton-family count mismatch.",
    )
    require(
        multi_count == EXPECTED_MULTI_TRADE_FAMILY_COUNT,
        "Multi-trade-family count mismatch.",
    )
    require(
        trades_multi == EXPECTED_TRADES_IN_MULTI_FAMILIES,
        "Trades-in-multi-family count mismatch.",
    )

    require(
        hasattr(detector, "classify_v11"),
        "Frozen detector does not expose classify_v11.",
    )

    return detector, family


# ---------------------------------------------------------------------------
# V1 IDENTITY — OUTCOME-BLIND PARTITION
# ---------------------------------------------------------------------------

def load_v1_population(
    family: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    This function is reachable only after execution authorization.

    V1 identity is the exact immutable protected trade-id manifest whose
    fingerprint was frozen before validation execution.

    It is accepted only if:
      D n = 396
      V1 manifest n = 80
      D hash matches
      V1 manifest hash matches
      all exact D identities remain present and closed
      all exact V1 identities remain present and closed
      D/V1 overlap = 0

    Later closed trades are outside both frozen populations and are ignored.
    No date shortcut is used at runtime.
    """
    require(LEDGER.exists(), f"Missing paper ledger: {LEDGER}")

    required_columns = {
        "trade_id",
        "question",
        "entry_price",
        "trade_won",
        "trade_pnl",
        "entry_date",
        "side",
        "category",
        "status",
    }

    header = pd.read_csv(LEDGER, nrows=0)
    missing = sorted(required_columns - set(header.columns))
    require(not missing, f"Ledger missing required columns: {missing}")

    ledger = pd.read_csv(LEDGER)
    ledger["trade_id"] = ledger["trade_id"].astype(str)

    require(
        not ledger["trade_id"].duplicated().any(),
        "Ledger contains duplicate trade_id values.",
    )

    status = ledger["status"].astype(str).str.strip().str.lower()
    closed = ledger.loc[status.eq("closed")].copy()

    d_ids = set(str(x) for x in family["trade_id"].tolist())
    v1_ids = set(EXPECTED_V1_TRADE_IDS)

    require(
        len(v1_ids) == EXPECTED_V1_N,
        "Frozen V1 manifest n mismatch.",
    )
    require(
        trade_id_hash(v1_ids) == EXPECTED_V1_TRADE_ID_SHA256,
        "Frozen V1 manifest trade-id SHA mismatch.",
    )

    overlap = d_ids.intersection(v1_ids)
    require(not overlap, "Frozen D/V1 identity overlap is non-zero.")

    d = closed.loc[closed["trade_id"].isin(d_ids)].copy()
    v1 = closed.loc[closed["trade_id"].isin(v1_ids)].copy()

    require(
        len(d) == EXPECTED_D_N,
        "Current ledger no longer contains exact D n.",
    )
    require(
        set(d["trade_id"].tolist()) == d_ids,
        "Current ledger D identities do not exactly match frozen detector identities.",
    )
    require(
        trade_id_hash(d["trade_id"]) == EXPECTED_D_TRADE_ID_SHA256,
        "Current-ledger D trade-id SHA mismatch.",
    )

    require(
        len(v1) == EXPECTED_V1_N,
        "Current ledger no longer contains exact protected V1 n.",
    )
    require(
        set(v1["trade_id"].tolist()) == v1_ids,
        "Current ledger V1 identities do not exactly match frozen manifest identities.",
    )
    require(
        trade_id_hash(v1["trade_id"]) == EXPECTED_V1_TRADE_ID_SHA256,
        "Protected V1 trade-id SHA mismatch.",
    )

    return d, v1


# ---------------------------------------------------------------------------
# ANALYSIS FRAME / MISSINGNESS
# ---------------------------------------------------------------------------

def prepare_analysis_frame(v1: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    frame = v1.copy()

    raw_missing = {
        "entry_price": int(frame["entry_price"].isna().sum()),
        "trade_won": int(frame["trade_won"].isna().sum()),
        "trade_pnl": int(frame["trade_pnl"].isna().sum()),
        "entry_date": int(frame["entry_date"].isna().sum()),
        "side": int(frame["side"].isna().sum()),
        "category": int(frame["category"].isna().sum()),
    }

    frame["entry_price_num"] = pd.to_numeric(
        frame["entry_price"], errors="coerce"
    )
    frame["trade_won_num"] = pd.to_numeric(
        frame["trade_won"], errors="coerce"
    )
    frame["trade_pnl_num"] = pd.to_numeric(
        frame["trade_pnl"], errors="coerce"
    )
    frame["entry_date_dt"] = pd.to_datetime(
        frame["entry_date"], errors="coerce"
    )

    invalid = {
        "entry_price": int(frame["entry_price_num"].isna().sum()),
        "trade_won": int(frame["trade_won_num"].isna().sum()),
        "trade_pnl": int(frame["trade_pnl_num"].isna().sum()),
        "entry_date": int(frame["entry_date_dt"].isna().sum()),
    }

    metadata = {
        "raw_missing": raw_missing,
        "invalid_numeric_or_date": invalid,
    }

    return frame, metadata


def pairwise_numeric(frame: pd.DataFrame, x: str, y: str) -> pd.DataFrame:
    pair = frame[[x, y]].copy()
    pair[x] = pd.to_numeric(pair[x], errors="coerce")
    pair[y] = pd.to_numeric(pair[y], errors="coerce")
    pair = pair.dropna()
    return pair


# ---------------------------------------------------------------------------
# FROZEN CORRELATION IMPLEMENTATION
# ---------------------------------------------------------------------------

def correlation(frame: pd.DataFrame, x: str, y: str) -> dict:
    pair = pairwise_numeric(frame, x, y)

    if len(pair) < 2:
        return {
            "n": len(pair),
            "pearson": None,
            "spearman": None,
            "spearman_p_two_sided": None,
        }

    pearson = pair[x].corr(pair[y], method="pearson")

    result = spearmanr(
        pair[x].to_numpy(),
        pair[y].to_numpy(),
    )

    return {
        "n": int(len(pair)),
        "pearson": finite_or_none(pearson),
        "spearman": finite_or_none(result.statistic),
        "spearman_p_two_sided": finite_or_none(result.pvalue),
    }


# ---------------------------------------------------------------------------
# DESCRIPTIVE SENSITIVITIES — ZERO CLASSIFICATION AUTHORITY
# ---------------------------------------------------------------------------

def trimmed_mean_10(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)

    if len(values) == 0:
        return None

    if len(values) < 10:
        return float(np.mean(values))

    values = np.sort(values)
    k = int(math.floor(len(values) * 0.10))

    if k == 0:
        return float(np.mean(values))

    trimmed = values[k : len(values) - k]
    return None if len(trimmed) == 0 else float(np.mean(trimmed))


def pnl_summary(frame: pd.DataFrame) -> dict:
    pnl = pd.to_numeric(frame["trade_pnl_num"], errors="coerce").dropna()
    won = pd.to_numeric(frame["trade_won_num"], errors="coerce").dropna()

    return {
        "n": int(len(frame)),
        "win_rate": finite_or_none(won.mean()) if len(won) else None,
        "pnl_mean": finite_or_none(pnl.mean()) if len(pnl) else None,
        "pnl_median": finite_or_none(pnl.median()) if len(pnl) else None,
        "pnl_trim10": trimmed_mean_10(pnl),
    }


def assign_frozen_entry_price_quartile(value: float) -> str | None:
    value = finite_or_none(value)
    if value is None:
        return None
    if value <= Q1_MAX:
        return "Q1"
    if value <= Q2_MAX:
        return "Q2"
    if value <= Q3_MAX:
        return "Q3"
    return "Q4"


def quartile_analysis(frame: pd.DataFrame) -> list[dict]:
    q = frame.copy()
    q["entry_price_quartile"] = q["entry_price_num"].map(
        assign_frozen_entry_price_quartile
    )

    rows = []
    for label in ("Q1", "Q2", "Q3", "Q4"):
        sub = q.loc[q["entry_price_quartile"] == label].copy()
        rows.append({"quartile": label, **pnl_summary(sub)})
    return rows


def temporal_analysis(frame: pd.DataFrame) -> list[dict]:
    x = frame.loc[frame["entry_date_dt"].notna()].copy()
    x["month"] = x["entry_date_dt"].dt.to_period("M").astype(str)

    rows = []
    for month in sorted(x["month"].unique()):
        sub = x.loc[x["month"] == month].copy()
        rows.append(
            {
                "month": month,
                "n": int(len(sub)),
                "win": correlation(
                    sub, "entry_price_num", "trade_won_num"
                ),
                "pnl": correlation(
                    sub, "entry_price_num", "trade_pnl_num"
                ),
            }
        )
    return rows


def side_analysis(frame: pd.DataFrame) -> list[dict]:
    rows = []

    labels = sorted(
        frame["side"].dropna().astype(str).str.strip().unique().tolist()
    )

    normalized = frame["side"].astype(str).str.strip()

    for label in labels:
        sub = frame.loc[normalized.eq(label)].copy()
        rows.append(
            {
                "side": label,
                "n": int(len(sub)),
                "win": correlation(
                    sub, "entry_price_num", "trade_won_num"
                ),
                "pnl": correlation(
                    sub, "entry_price_num", "trade_pnl_num"
                ),
            }
        )

    return rows


def category_context(frame: pd.DataFrame) -> list[dict]:
    x = frame["category"].fillna("MISSING").astype(str)
    counts = x.value_counts(dropna=False)

    return [
        {
            "category": str(category),
            "n": int(n),
            "share": float(n / len(frame)) if len(frame) else None,
        }
        for category, n in counts.items()
    ]


def outlier_concentration(frame: pd.DataFrame) -> dict:
    pnl = pd.to_numeric(frame["trade_pnl_num"], errors="coerce").dropna()

    abs_pnl = pnl.abs().sort_values(ascending=False)

    top3 = float(abs_pnl.head(3).sum()) if len(abs_pnl) else 0.0
    total_abs = float(abs_pnl.sum()) if len(abs_pnl) else 0.0

    return {
        "total_realized_pnl": float(pnl.sum()) if len(pnl) else 0.0,
        "total_absolute_pnl": total_abs,
        "top3_absolute_pnl": top3,
        "top3_share_total_absolute_pnl": (
            top3 / total_abs if total_abs > 0 else None
        ),
    }


# ---------------------------------------------------------------------------
# FROZEN FAMILY SENSITIVITY — CLASSIFICATION AUTHORITY
# ---------------------------------------------------------------------------

def family_analysis(
    frame: pd.DataFrame,
    detector,
) -> dict:
    """
    Apply the already-frozen v1.1 family classifier prospectively to protected
    V1 market questions.

    The classifier is the exact classify_v11(q) function exposed by the
    provenance-checked frozen detector. It consumes only question text.

    No outcome field is supplied to family classification. No rule is fitted,
    modified, extended, or optimized from V1 outcomes.

    Family sizes and equal-weight family means are computed within protected
    V1 after those frozen family keys are assigned.
    """

    require(
        "question" in frame.columns,
        "Protected V1 frame missing question required for frozen family assignment.",
    )

    require(
        frame["question"].notna().all(),
        "Protected V1 contains missing question values.",
    )

    assigned = frame.copy()

    classifications = assigned["question"].map(detector.classify_v11)

    require(
        classifications.notna().all(),
        "Frozen classify_v11 returned missing classification.",
    )

    assigned["rule_matched"] = classifications.map(lambda x: x[0])
    assigned["family_key"] = classifications.map(lambda x: x[1])

    require(
        assigned["family_key"].notna().all(),
        "Frozen V1 family assignment contains missing family_key.",
    )

    require(
        assigned["rule_matched"].notna().all(),
        "Frozen V1 family assignment contains missing rule_matched.",
    )

    family_sizes = assigned.groupby(
        "family_key",
        dropna=False,
    ).size()

    assigned["family_size"] = assigned["family_key"].map(family_sizes)

    family_means = (
        assigned.groupby(
            "family_key",
            as_index=False,
            dropna=False,
        )
        .agg(
            entry_price_num=("entry_price_num", "mean"),
            trade_won_num=("trade_won_num", "mean"),
            trade_pnl_num=("trade_pnl_num", "mean"),
            raw_trade_n=("trade_id", "size"),
        )
        .copy()
    )

    win = correlation(
        family_means,
        "entry_price_num",
        "trade_won_num",
    )

    pnl = correlation(
        family_means,
        "entry_price_num",
        "trade_pnl_num",
    )

    represented_families = int(len(family_means))
    largest_family_size = (
        int(family_means["raw_trade_n"].max())
        if represented_families
        else 0
    )

    largest_family_concentration = (
        largest_family_size / len(assigned)
        if len(assigned)
        else None
    )

    rule_counts = (
        assigned["rule_matched"]
        .value_counts(dropna=False)
        .sort_index()
        .to_dict()
    )

    return {
        "represented_families": represented_families,
        "largest_family_size": largest_family_size,
        "largest_family_raw_trade_concentration": finite_or_none(
            largest_family_concentration
        ),
        "rule_matched_counts": {
            str(k): int(v)
            for k, v in rule_counts.items()
        },
        "win_spearman": win["spearman"],
        "win_pearson": win["pearson"],
        "win_n": win["n"],
        "pnl_spearman": pnl["spearman"],
        "pnl_pearson": pnl["pearson"],
        "pnl_n": pnl["n"],
    }


# ---------------------------------------------------------------------------
# DETERMINISTIC CLASSIFICATION
# ---------------------------------------------------------------------------

def classify(
    overall_win: dict,
    overall_pnl: dict,
    family_result: dict,
) -> str:
    win_rho = finite_or_none(overall_win["spearman"])
    pnl_rho = finite_or_none(overall_pnl["spearman"])
    win_p = finite_or_none(overall_win["spearman_p_two_sided"])
    pnl_p = finite_or_none(overall_pnl["spearman_p_two_sided"])

    # FAIL has precedence only for opposite raw-trade primary direction.
    if win_rho is not None and win_rho < 0:
        return "FAIL"
    if pnl_rho is not None and pnl_rho > 0:
        return "FAIL"

    # Zero / undefined / non-significant correct direction => INCONCLUSIVE.
    if win_rho is None or pnl_rho is None:
        return "INCONCLUSIVE"
    if win_p is None or pnl_p is None:
        return "INCONCLUSIVE"
    if win_rho == 0 or pnl_rho == 0:
        return "INCONCLUSIVE"
    if win_p >= PRIMARY_ALPHA or pnl_p >= PRIMARY_ALPHA:
        return "INCONCLUSIVE"

    family_win = finite_or_none(family_result["win_spearman"])
    family_pnl = finite_or_none(family_result["pnl_spearman"])

    if family_win is None or family_pnl is None:
        return "INCONCLUSIVE"
    if family_win <= 0 or family_pnl >= 0:
        return "INCONCLUSIVE"

    return "PASS"


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

def build_report(
    script_sha: str,
    v1: pd.DataFrame,
    metadata: dict,
    overall_win: dict,
    overall_pnl: dict,
    family_result: dict,
    quartiles: list[dict],
    temporal: list[dict],
    sides: list[dict],
    categories: list[dict],
    outliers: dict,
    classification: str,
) -> str:
    lines = [
        "# LRS-1 D1-003 — V1 Validation",
        "",
        "## Governance",
        "",
        f"- Methodology commit: `{EXPECTED_METHODOLOGY_COMMIT}`",
        f"- Specification SHA-256: `{EXPECTED_SPEC_SHA256}`",
        f"- Validation script SHA-256: `{script_sha}`",
        f"- SciPy version: `{scipy.__version__}`",
        f"- Protected V1 n: **{len(v1)}**",
        f"- V1 trade-id SHA-256: `{trade_id_hash(v1['trade_id'])}`",
        "- Discovery-D outcomes used in validation: **NO**",
        "- Post-open methodology modification: **NO**",
        "",
        "## Primary validation",
        "",
        "| Outcome | n | Pearson | Spearman | Spearman two-sided p |",
        "|---|---:|---:|---:|---:|",
        (
            f"| trade_won | {overall_win['n']} | "
            f"{fmt_float(overall_win['pearson'])} | "
            f"{fmt_float(overall_win['spearman'])} | "
            f"{fmt_float(overall_win['spearman_p_two_sided'])} |"
        ),
        (
            f"| trade_pnl | {overall_pnl['n']} | "
            f"{fmt_float(overall_pnl['pearson'])} | "
            f"{fmt_float(overall_pnl['spearman'])} | "
            f"{fmt_float(overall_pnl['spearman_p_two_sided'])} |"
        ),
        "",
        f"## Classification: **{classification}**",
        "",
        "Classification follows the frozen precedence in the V1 specification.",
        "",
        "## Missingness",
        "",
        f"- Raw missing: `{metadata['raw_missing']}`",
        (
            "- Invalid numeric/date after deterministic parsing: "
            f"`{metadata['invalid_numeric_or_date']}`"
        ),
        "",
        "## Frozen family sensitivity",
        "",
        f"- `{family_result}`",
        "",
        "## Fixed D0 entry-price quartiles — disclosure only",
        "",
    ]

    for row in quartiles:
        lines.append(f"- `{row}`")

    lines += [
        "",
        "## Temporal sensitivity — disclosure only",
        "",
    ]

    for row in temporal:
        lines.append(f"- `{row}`")

    lines += [
        "",
        "## Recorded-side sensitivity — disclosure only",
        "",
    ]

    for row in sides:
        lines.append(f"- `{row}`")

    lines += [
        "",
        "## P&L outlier sensitivity — disclosure only",
        "",
        f"- `{outliers}`",
        "",
        "## Category composition — context only",
        "",
    ]

    for row in categories:
        lines.append(f"- `{row}`")

    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This is protected-V1 validation of the prospectively frozen D1-003",
        "entry-price divergence structure. PASS, if observed, means only that",
        "the frozen directional replication criterion was satisfied under the",
        "frozen V1 specification. It does not establish causality, universal",
        "generalization, live-money profitability, or a production trading rule.",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    # CRITICAL: all execution/SHA/spec/runtime gates occur before ledger access.
    script_sha = verify_preledger_authority()

    # Detector is frozen D provenance. Import occurs only after authorization.
    detector, family = load_frozen_family_assignment()

    # First outcome-bearing ledger access occurs here.
    _, v1 = load_v1_population(family)

    frame, metadata = prepare_analysis_frame(v1)

    overall_win = correlation(
        frame,
        "entry_price_num",
        "trade_won_num",
    )
    overall_pnl = correlation(
        frame,
        "entry_price_num",
        "trade_pnl_num",
    )

    # Apply exact frozen question-only v1.1 family rules prospectively to V1.
    family_result = family_analysis(frame, detector)

    quartiles = quartile_analysis(frame)
    temporal = temporal_analysis(frame)
    sides = side_analysis(frame)
    categories = category_context(frame)
    outliers = outlier_concentration(frame)

    classification = classify(
        overall_win,
        overall_pnl,
        family_result,
    )

    report_text = build_report(
        script_sha=script_sha,
        v1=v1,
        metadata=metadata,
        overall_win=overall_win,
        overall_pnl=overall_pnl,
        family_result=family_result,
        quartiles=quartiles,
        temporal=temporal,
        sides=sides,
        categories=categories,
        outliers=outliers,
        classification=classification,
    )

    require(not REPORT.exists(), "Report appeared during execution; refusing overwrite.")

    REPORT.write_text(report_text.rstrip("\n") + "\n")

    print("D1_003_V1_EXECUTED=YES")
    print(f"VALIDATION_SCRIPT_SHA256={script_sha}")
    print(f"V1_N={len(v1)}")
    print(f"V1_TRADE_ID_SHA256={trade_id_hash(v1['trade_id'])}")
    print(f"CLASSIFICATION={classification}")
    print(f"REPORT_SHA256={sha256_file(REPORT)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(1)
