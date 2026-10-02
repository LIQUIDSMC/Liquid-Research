import pandas as pd
import re
import hashlib
from collections import Counter

P = "L3_RESEARCH_ENGINES/market_selection/data/simulator/paper_trades.csv"
EXPECTED_D_HASH = "ad6efd9801c8f18fba47769ba49f42f37ee59f7b2a9454709d18e8e9c65b2f4e"

COLS = [
    "trade_id",
    "market_id",
    "question",
    "slug",
    "category",
    "status",
    "resolution_date",
]

df = pd.read_csv(P, usecols=COLS)

closed = df[
    df["status"].astype(str).str.lower().eq("closed")
].copy()

closed["_rd"] = pd.to_datetime(
    closed["resolution_date"],
    errors="coerce",
)

D = closed[
    closed["_rd"] <= pd.Timestamp("2026-09-23 23:59:59")
].copy()

# IMPORTANT:
# Preserve the ORIGINAL historical D fingerprint algorithm exactly:
# trade_id -> string -> lexicographic sort.
d_payload = "\n".join(
    D["trade_id"].astype(str).sort_values().tolist()
).encode("utf-8")

d_hash = hashlib.sha256(d_payload).hexdigest()

assert len(D) == 396
assert D["trade_id"].nunique() == 396
assert d_hash == EXPECTED_D_HASH

# Separate deterministic ordering for detector/checksum output.
D = D.sort_values("trade_id").reset_index(drop=True)


def clean(s):
    s = str(s).lower().strip()
    s = s.replace("’", "'").replace("–", "-")
    s = re.sub(r"\s+", " ", s)
    return s


MONTHS = (
    r"january|february|march|april|may|june|july|"
    r"august|september|october|november|december"
)

DEADLINE_TAIL = re.compile(
    rf"\s+(?:by|before|through)\s+"
    rf"(?:the\s+)?(?:end\s+of\s+)?"
    rf"(?:{MONTHS})"
    rf"(?:\s+\d{{1,2}})?"
    rf"(?:,\s*\d{{4}})?\??$",
    re.I,
)


# ============================================================
# SHARED NARROW MATCHERS
# ============================================================

def match_range_threshold(q0):

    m = re.fullmatch(
        r"will elon musk post "
        r"\d+\s*-\s*\d+ "
        r"tweets from (.+?)\?",
        q0,
    )
    if m:
        return (
            "range_bucket",
            f"elon_musk_posts|window={m.group(1).strip()}",
        )

    m = re.fullmatch(
        r"will (bitcoin|ethereum|xrp|solana) "
        r"(dip to|reach) \$?[\d,]+(?:\.\d+)? "
        r"(.+?)\?",
        q0,
    )
    if m:
        asset, direction, window = m.groups()
        return (
            "threshold_window",
            f"{asset}|{direction}|{window}",
        )

    m = re.fullmatch(
        r"will the price of (bitcoin|ethereum|xrp|solana) "
        r"be above \$?[\d,]+(?:\.\d+)? "
        r"(.+?)\?",
        q0,
    )
    if m:
        asset, window = m.groups()
        return (
            "threshold_window",
            f"{asset}|above|{window}",
        )

    m = re.fullmatch(
        r"will wti crude oil \(wti\) hit "
        r"\((high|low)\) \$?[\d,]+(?:\.\d+)? "
        r"(.+?)\?",
        q0,
    )
    if m:
        direction, window = m.groups()
        return (
            "threshold_window",
            f"wti|{direction}|{window}",
        )

    m = re.fullmatch(
        r"laptop fdv above \$?[\d,.]+[mb] "
        r"one day after launch\?",
        q0,
    )
    if m:
        return (
            "threshold_window",
            "laptop_fdv|above|one_day_after_launch",
        )

    return None


def match_decision_point(q0):

    m = re.fullmatch(
        r"will the fed "
        r"(?:increase|decrease) interest rates by "
        r"(?:25|50\+?) bps after the "
        r"(" + MONTHS + r") 2026 meeting\?",
        q0,
    )
    if m:
        return (
            "decision_point",
            f"fed_rate_decision|{m.group(1)}_2026_meeting",
        )

    m = re.fullmatch(
        r"will there be no change in fed interest rates "
        r"after the (" + MONTHS + r") 2026 meeting\?",
        q0,
    )
    if m:
        return (
            "decision_point",
            f"fed_rate_decision|{m.group(1)}_2026_meeting",
        )

    return None


def match_explicit_contest(q0):

    if re.fullmatch(
        r"will .+ win the 2026 men's us open\?",
        q0,
    ):
        return (
            "explicit_contest",
            "tennis|2026_mens_us_open|winner",
        )

    if re.fullmatch(
        r"will .+ win the 2026 women's us open\?",
        q0,
    ):
        return (
            "explicit_contest",
            "tennis|2026_womens_us_open|winner",
        )

    if re.fullmatch(
        r"will .+ win the clacton by-election\?",
        q0,
    ):
        return (
            "explicit_contest",
            "clacton_by_election|winner",
        )

    return None


def match_destination(q0):

    if re.fullmatch(
        r"will lebron james play for the .+ in 2026-27\?",
        q0,
    ):
        return (
            "destination_template",
            "lebron_james|team|2026-27",
        )

    if re.fullmatch(
        r"will james harden play for the .+ in 2026-27\?",
        q0,
    ):
        return (
            "destination_template",
            "james_harden|team|2026-27",
        )

    return None


def match_deadline(q0):

    base = DEADLINE_TAIL.sub("", q0)

    if base != q0:
        base = base.rstrip(" ?")
        if base:
            return (
                "deadline_series",
                base,
            )

    return None


# ============================================================
# V1 — PREVIOUS EXECUTABLE ORDER
# Comparison target only.
# ============================================================

def classify_v1(q):

    q0 = clean(q)

    hit = match_range_threshold(q0)
    if hit:
        return hit

    hit = match_deadline(q0)
    if hit:
        return hit

    hit = match_decision_point(q0)
    if hit:
        return hit

    hit = match_explicit_contest(q0)
    if hit:
        return hit

    hit = match_destination(q0)
    if hit:
        return hit

    return (
        "exact_or_singleton",
        q0.rstrip(" ?"),
    )


# ============================================================
# V1.1 — CORRECTED DOCUMENTED PRECEDENCE
#
# Narrow structural rules execute before deadline ladder.
# No fuzzy matching.
# ============================================================

def classify_v11(q):

    q0 = clean(q)

    hit = match_range_threshold(q0)
    if hit:
        return hit

    hit = match_decision_point(q0)
    if hit:
        return hit

    hit = match_explicit_contest(q0)
    if hit:
        return hit

    hit = match_destination(q0)
    if hit:
        return hit

    hit = match_deadline(q0)
    if hit:
        return hit

    return (
        "exact_or_singleton",
        q0.rstrip(" ?"),
    )


# ============================================================
# ASSIGN BOTH VERSIONS
# ============================================================

records = []

for _, r in D.iterrows():

    v1_rule, v1_key = classify_v1(r["question"])
    v11_rule, v11_key = classify_v11(r["question"])

    records.append({
        "trade_id": int(r["trade_id"]),
        "question": str(r["question"]),
        "v1_rule": v1_rule,
        "v1_key": v1_key,
        "rule_matched": v11_rule,
        "family_key": v11_key,
    })

out = pd.DataFrame(records).sort_values(
    "trade_id"
).reset_index(drop=True)


# ============================================================
# BYTE-IDENTICAL V1 -> V1.1 FAMILY ASSIGNMENT
# ============================================================

v1_assignment_bytes = "\n".join(
    f"{r.trade_id}|{r.v1_key}"
    for r in out.itertuples()
).encode("utf-8")

v11_assignment_bytes = "\n".join(
    f"{r.trade_id}|{r.family_key}"
    for r in out.itertuples()
).encode("utf-8")

assert v1_assignment_bytes == v11_assignment_bytes

v1_assignment_hash = hashlib.sha256(
    v1_assignment_bytes
).hexdigest()

v11_assignment_hash = hashlib.sha256(
    v11_assignment_bytes
).hexdigest()

assert v1_assignment_hash == v11_assignment_hash


# ============================================================
# RULE-MATCHED VS ACTUAL FAMILY FORMATION
# ============================================================

family_counts = Counter(out["family_key"])

out["family_size"] = out["family_key"].map(
    family_counts
)

out["is_merged_family"] = (
    out["family_size"] > 1
)


# ============================================================
# REGRESSION HELPERS
# ============================================================

def row_for_trade(tid):
    x = out[out["trade_id"].eq(tid)]
    assert len(x) == 1
    return x.iloc[0]


def key_for_trade(tid):
    return row_for_trade(tid)["family_key"]


# ============================================================
# NEGATIVE REGRESSIONS
# ============================================================

assert key_for_trade(240) != key_for_trade(287)

assert key_for_trade(340) != key_for_trade(454)
assert key_for_trade(340) != key_for_trade(150)

assert key_for_trade(449) != key_for_trade(515)
assert key_for_trade(426) != key_for_trade(548)
assert key_for_trade(415) != key_for_trade(461)

high_aug = set(
    out[
        out["question"].str.contains(
            r"WTI.*\(HIGH\).*August",
            case=False,
            regex=True,
            na=False,
        )
    ]["family_key"]
)

low_aug = set(
    out[
        out["question"].str.contains(
            r"WTI.*\(LOW\).*August",
            case=False,
            regex=True,
            na=False,
        )
    ]["family_key"]
)

assert high_aug.isdisjoint(low_aug)


# ============================================================
# POSITIVE REGRESSIONS
# ============================================================

assert len({
    key_for_trade(1),
    key_for_trade(2),
    key_for_trade(6),
    key_for_trade(7),
    key_for_trade(13),
}) == 1

assert key_for_trade(128) == key_for_trade(280)

assert key_for_trade(433) == key_for_trade(549)

assert len({
    key_for_trade(517),
    key_for_trade(522),
    key_for_trade(523),
    key_for_trade(524),
    key_for_trade(533),
}) == 1

assert len({
    key_for_trade(3),
    key_for_trade(4),
    key_for_trade(20),
}) == 1

assert len({
    key_for_trade(94),
    key_for_trade(107),
    key_for_trade(109),
    key_for_trade(192),
    key_for_trade(193),
}) == 1

assert len({
    key_for_trade(57),
    key_for_trade(58),
    key_for_trade(68),
    key_for_trade(95),
    key_for_trade(127),
    key_for_trade(130),
}) == 1

assert key_for_trade(92) == key_for_trade(93)

mens = set(
    out[
        out["question"].str.contains(
            "2026 Men's US Open",
            regex=False,
            na=False,
        )
    ]["family_key"]
)

womens = set(
    out[
        out["question"].str.contains(
            "2026 Women",
            regex=False,
            na=False,
        )
        &
        out["question"].str.contains(
            "US Open",
            regex=False,
            na=False,
        )
    ]["family_key"]
)

assert len(mens) == 1
assert len(womens) == 1
assert mens.isdisjoint(womens)

assert key_for_trade(75) == key_for_trade(88)

# Count Binface second-place contract stays separate.
assert key_for_trade(225) != key_for_trade(88)


# ============================================================
# FREEZE CHECKSUMS
# ============================================================

freeze_lines = [
    f"{r.trade_id}|{r.rule_matched}|{r.family_key}"
    for r in out.itertuples()
]

freeze_sha256 = hashlib.sha256(
    "\n".join(freeze_lines).encode("utf-8")
).hexdigest()

derived_lines = [
    (
        f"{r.trade_id}|{r.rule_matched}|"
        f"{r.family_key}|{r.family_size}"
    )
    for r in out.itertuples()
]

derived_sha256 = hashlib.sha256(
    "\n".join(derived_lines).encode("utf-8")
).hexdigest()


# ============================================================
# REPORT
# ============================================================

family_sizes = out.groupby("family_key").size()

print("===== LRS-1 4A v1.1 FREEZE CANDIDATE =====")
print(f"D_n={len(out)}")
print(f"D_trade_id_sha256={d_hash}")

print()
print("===== PRECEDENCE CORRECTION =====")
print("v1_vs_v1.1_assignment_bytes_identical=True")
print(f"v1_assignment_sha256={v1_assignment_hash}")
print(f"v1.1_assignment_sha256={v11_assignment_hash}")

print()
print("===== FAMILY STRUCTURE =====")
print(f"family_count={len(family_sizes)}")
print(
    f"singleton_family_count="
    f"{(family_sizes == 1).sum()}"
)
print(
    f"merged_family_count="
    f"{(family_sizes > 1).sum()}"
)
print(
    "trades_in_merged_families="
    f"{int(family_sizes[family_sizes > 1].sum())}"
)

print()
print("===== RULE MATCHED COUNTS =====")
print(
    out["rule_matched"]
    .value_counts()
    .to_string()
)

print()
print("===== ACTUAL MERGED-FAMILY COUNTS BY RULE =====")
print(
    out[out["is_merged_family"]]["rule_matched"]
    .value_counts()
    .to_string()
)

print()
print("===== REGRESSION SUITE =====")
print("PASS | BTC same threshold / different dates remain split")
print("PASS | Elon different windows remain split")
print("PASS | same football club / different matches remain split")
print("PASS | WTI HIGH vs LOW remain split")
print("PASS | Starmer deadline ladder merged")
print("PASS | Iran leadership deadline ladder merged")
print("PASS | Iran-Oman deadline ladder merged")
print("PASS | LAPTOP FDV threshold ladder merged")
print("PASS | Fed July decision point merged")
print("PASS | Fed September decision point merged")
print("PASS | LeBron destination merged")
print("PASS | Harden destination merged")
print("PASS | Men's US Open internally merged")
print("PASS | Women's US Open internally merged")
print("PASS | Men's/Women's US Open remain separate")
print("PASS | Clacton winner contracts merged")
print("PASS | Clacton second-place contract remains separate")

print()
print("===== FREEZE CHECKSUMS =====")
print("PRIMARY_SCHEMA=trade_id|rule_matched|family_key")
print(f"PRIMARY_SHA256={freeze_sha256}")
print(
    "DERIVED_SCHEMA="
    "trade_id|rule_matched|family_key|family_size"
)
print(f"DERIVED_SHA256={derived_sha256}")

print()
print("===== KNOWN LIMITATIONS =====")
print(
    "Detector is deliberately conservative and may "
    "under-cluster semantic dependence."
)
print("Company-ranking alternatives remain split.")
print("Ambiguous semantic siblings remain split.")
print("No fuzzy similarity is used.")
print(
    "family_size is derived after assignment; "
    "rule_matched alone does not imply a merged family."
)

print()
print("OUTCOME FIELDS USED: NONE")
print("ECONOMIC OUTCOME VALUES PRINTED: NONE")
print("FILES WRITTEN: NONE")
