# F3 Gate-2 Tuesday Closeout Runbook v1

**Status:** Pre-result operational procedure  
**Scope:** F3 Gate-2 primary production evidence closeout  
**Primary host:** Pi3 (`liquid-pi`, `192.168.1.155`)  
**Analysis host:** Mac  
**Primary start batch:** `7037`  
**Frozen endpoint:** `2026-09-28 00:22:28 PDT` / `2026-09-28 07:22:28 UTC`

This runbook operationalizes Sections 17 and 18 of
`F3_ASYNC_PERSISTENCE_EXPERIMENT_V1.md`.

It does not change the frozen methodology, Gate-2 structural criterion,
queue capacity, F2, the frozen analyzer, or the primary population.

No production performance distribution may be inspected until the
continuity, endpoint, evidence-freeze, integrity, and structural-validation
steps below have passed.

---

## 1. Operating rules

1. Pi3 remains the authoritative F3 collector host for this evidence window.
2. Do not migrate, redeploy, restart, stop, or edit the collector as part of
   evidence closeout.
3. Do not run the heavy Gate-2 analyzer on Pi3.
4. Do not modify source telemetry.
5. Do not choose `N` from any performance measurement.
6. Do not crop telemetry to `[7037, N]` before frozen structural validation.
7. Preserve finite intact worker-epoch evidence sufficient for structural
   validation through candidate `N`, including any structurally necessary
   boundary-crossing observations.
8. Only after the intact frozen validation evidence passes complete-epoch
   structural validation may the primary population `[7037, N]` be selected.
9. Batches `1..7036` remain pre-protocol observational evidence.
10. Evidence after `N` remains outside the primary population and must not be
    deleted or rewritten.
11. Any interruption or disqualifying boundary fails closed under Sections 17
    and 18. Do not concatenate epochs or repair the primary window.
12. Gate-2 interpretation uses
    `F3_GATE2_ADJUDICATION_TEMPLATE_V1.md`.

---

## 2. Phase A — Pi3 live continuity and authority check

**Host:** PI 3  
**Mode:** read-only

Before touching evidence:

- record current local and UTC time;
- inspect `liquid-research-collector.service`;
- confirm it is active;
- record `MainPID`;
- record `NRestarts`;
- record service start timestamp;
- inspect the actual systemd unit and environment;
- confirm the expected working directory and executable;
- confirm telemetry is enabled and determine the effective telemetry
  directory;
- record deployed repository commit;
- inspect repository status;
- check collector logs for restart, fatal persistence, telemetry-cap,
  telemetry-disabled, or other relevant boundary evidence.

The repository service example is reference provenance only. The live Pi3
unit is authoritative for this phase.

**Fail closed:** if the primary candidate window crossed a collector restart,
worker epoch restart, incompatible deployment, instrumentation/schema change,
queue-capacity change, telemetry compromise, or another Section-18
disqualifying boundary.

Do not inspect Gate-2 performance distributions in this phase.

---

## 3. Phase B — identify source telemetry without modifying it

**Host:** PI 3  
**Mode:** read-only

Effective default telemetry directory:

`/mnt/lrs001/data/market_data_platform/telemetry`

Telemetry files use UTC-day names:

`telemetry_YYYY-MM-DD.jsonl`

The effective directory must still be verified from the live service
environment before relying on this default.

Identify every source JSONL needed to reconstruct the uninterrupted F3 worker
epoch from its first F3 observation through the endpoint.

Record for every source file:

- absolute path;
- byte size;
- modification timestamp;
- SHA-256.

Do not edit, truncate, rotate, rename, or otherwise mutate source telemetry.

Because the collector may still be appending to a current source file,
source-file identity alone is not the frozen evidence artifact. The closeout
must create a separate finite, immutable snapshot containing sufficient intact
worker-epoch evidence through candidate `N` and any structurally necessary
boundary-crossing observations.

---

## 4. Phase C — freeze finite immutable source snapshot

**Host:** PI 3  
**Mode:** evidence preservation

Create a finite, immutable snapshot of the relevant source telemetry before
endpoint selection or structural analysis. Do not analyze a live file that
continues to append while the closeout decision is being made.

The frozen validation artifact must:

- begin at the actual worker-epoch start and preserve the original persisted
  F3 observation order and previous-observer provenance chain;
- preserve sufficient raw F3 telemetry to reconstruct every batch through the
  frozen endpoint boundary;
- preserve boundary-crossing F3 observations beyond the eventual candidate
  `N` when required to keep the serialized provenance chain intact and the
  supplied worker epoch structurally complete under frozen
  `validate_and_pair()`;
- preserve selected source bytes without parsing and reserializing telemetry;
- not modify source telemetry.

Because handoff and completion observations originate from different threads,
a handoff for `N+1` may be serialized before completion `N`. The snapshot must
therefore remain intact through a structurally closed validation boundary
rather than being cropped to the eventual candidate `N`.

Record before transfer:

- source host;
- collector PID / epoch evidence;
- deployed code commit;
- ordered source telemetry file list;
- source-file byte sizes and SHA-256 values;
- frozen snapshot file list;
- frozen snapshot byte sizes and SHA-256 values;
- frozen endpoint;
- primary start `7037`.

Do not delete, truncate, rewrite, or otherwise modify pre-protocol,
post-endpoint, or source telemetry.

---

## 5. Phase D — determine endpoint candidate N from frozen snapshot

**Host:** MAC  
**Mode:** structural/boundary inspection only

Frozen endpoint:

`2026-09-28T07:22:28Z`

Endpoint nanoseconds:

`1790580148000000000`

Determine candidate `N` only from the finite frozen snapshot after transfer
integrity has been verified.

`wall_ns` on an F3 telemetry record is the wall-clock observation timestamp
added by `Telemetry.f3_persistence()` before the record enters telemetry
serialization.

For endpoint selection, inspect only structural/boundary fields needed to
identify F3 completion observations:

- `type`;
- `batch_id`;
- `wall_ns`;
- observer-provenance identity fields where needed for continuity.

Do not print or inspect:

- `submit_block_ms`;
- `queue_wait_after_accept_ms`;
- `worker_persist_ms`;
- queue-depth distributions;
- observer callback duration distributions;
- other Gate-2 performance outcomes.

The endpoint candidate is:

> the highest batch ID represented by an `f3_persistence_complete` observation
> in the frozen snapshot whose
> `wall_ns <= 1790580148000000000`.

This produces a **candidate N only**. The candidate is not structurally
accepted until the complete frozen snapshot passes frozen
`validate_and_pair()` and Phase G confirms the endpoint against the validated
pairs.

This is an observation-time boundary. It must not be described as an exact UTC
timestamp for physical persistence completion. `worker_end_ns` is monotonic
process time and is not retrospectively converted to UTC.

Record the first completion observation after the endpoint as boundary
evidence when available, but do not include it in the primary population.

Do not crop the frozen snapshot to candidate `N`. Any retained batch above
candidate `N` remains boundary/provenance evidence only and must not influence
the candidate.

---

## 6. Phase E — transfer frozen evidence to Mac

Transfer the frozen evidence artifact and its provenance record from Pi3 to a
dedicated Mac closeout directory.

Transfer must not alter the Pi3 source telemetry or frozen evidence artifact.

After transfer:

1. calculate SHA-256 on Mac;
2. compare it to the Pi3 frozen-artifact SHA-256;
3. require an exact match before analysis.

**Fail closed:** any integrity mismatch.

---

## 7. Phase F — frozen structural validation on Mac

**Host:** MAC  
**Mode:** offline analysis

Use the canonical frozen analyzer:

`L1_CORE/market_data_platform/research/analyze_f3_gate2.py`

Load the complete finite frozen validation evidence.

Before primary selection, require `validate_and_pair()` to establish:

- valid F3 record structure;
- observer-provenance continuity;
- exactly one intended uninterrupted worker epoch;
- epoch begins at batch 1;
- matching handoff/completion sets;
- contiguous batch IDs;
- matching pair identity fields;
- valid accounting;
- frozen queue capacity.

If complete-epoch validation fails, stop.

Do not crop around the error, concatenate another epoch, infer missing records,
or redefine `N`.

---

## 8. Phase G — confirm N after structural validation

After the complete epoch passes frozen validation:

- require the validated pair set to contain every batch `1..N`;
- require `N >= 7037`;
- confirm the completion observation associated with `N` is the last
  structurally completed batch at or before the frozen endpoint;
- confirm no structurally completed batch with a higher ID belongs at or
  before the endpoint.

Only now is `N` accepted as the Section-17 primary endpoint.

---

## 9. Phase H — select and summarize primary `[7037, N]`

Use:

`L1_CORE/market_data_platform/research/prepare_f3_gate2_primary.py`

Inputs:

- complete validated finite snapshot containing structural evidence through
  candidate `N`;
- `--start-batch 7037`;
- `--end-batch N`.

The helper must validate the complete supplied epoch before selecting the
primary population.

The resulting summary is descriptive evidence only.

Preserve the deterministic JSON output as a separate result artifact and
record its SHA-256.

---

## 10. Phase I — Gate-2 adjudication

Use:

`F3_GATE2_ADJUDICATION_TEMPLATE_V1.md`

Populate only from the frozen primary evidence and established provenance.

Allowed result:

- `PASS`
- `FAIL`
- `INCONCLUSIVE`

Do not introduce:

- a new numerical success threshold;
- a new population;
- a different endpoint rule;
- queue-capacity optimization;
- post-hoc causal assumptions;
- F2 reinterpretation;
- physical-disk claims;
- Coinbase/network claims;
- trading-edge claims;
- execution claims;
- profitability/economic claims.

Preserve negative or inconclusive evidence as such.

---

## 11. Tuesday execution order

Execute in this exact order:

1. Pi3 continuity / live authority verification.
2. Pi3 source telemetry identification.
3. Pi3 finite immutable source snapshot.
4. Pi3 provenance + SHA-256.
5. Transfer frozen snapshot to Mac.
6. Mac SHA-256 integrity verification.
7. Mac outcome-blind endpoint candidate `N` from frozen snapshot.
8. Mac frozen complete-epoch structural validation.
9. Mac confirmation of deterministic `N`.
10. Mac primary selection `[7037, N]`.
11. Mac descriptive Gate-2 summary.
12. Gate-2 adjudication using the frozen template.
13. Preserve final evidence, provenance, result, and hashes.
14. Only after evidence closeout is complete may collector migration be
    considered separately.

---

## 11A. Exact Tuesday operator commands

Execute these commands in numerical order. Stop on any failed prerequisite.
Do not execute a later command to work around an earlier failure.

### Command 1 — PI 3 continuity and authority

Run from Mac. This command is read-only on PI 3.

```bash
ssh kristo@192.168.1.155 '
set -e

echo "===== PI 3 TIME ====="
date
date -u

echo
echo "===== PI 3 COLLECTOR AUTHORITY ====="
sudo systemctl show liquid-research-collector.service \
  -p ActiveState \
  -p SubState \
  -p MainPID \
  -p NRestarts \
  -p ExecMainStartTimestamp \
  -p FragmentPath \
  -p WorkingDirectory

echo
echo "===== PI 3 PROCESS ====="
ACTIVE="$(sudo systemctl show liquid-research-collector.service -p ActiveState --value)"
SUB="$(sudo systemctl show liquid-research-collector.service -p SubState --value)"
PID="$(sudo systemctl show liquid-research-collector.service -p MainPID --value)"
RESTARTS="$(sudo systemctl show liquid-research-collector.service -p NRestarts --value)"
START="$(sudo systemctl show liquid-research-collector.service -p ExecMainStartTimestamp --value)"

test "$ACTIVE" = "active" || {
  echo "FATAL: PI 3 collector ActiveState=$ACTIVE, expected active" >&2
  exit 1
}
test "$SUB" = "running" || {
  echo "FATAL: PI 3 collector SubState=$SUB, expected running" >&2
  exit 1
}
test "$PID" = "26953" || {
  echo "FATAL: PI 3 collector PID=$PID, expected frozen PID 26953" >&2
  exit 1
}
test "$RESTARTS" = "0" || {
  echo "FATAL: PI 3 collector NRestarts=$RESTARTS, expected 0" >&2
  exit 1
}
case "$START" in
  "Sat 2026-09-26 22:43:18 PDT"*) ;;
  *)
    echo "FATAL: PI 3 collector start timestamp differs from frozen epoch: $START" >&2
    exit 1
    ;;
esac

echo "PASS: PI 3 frozen collector continuity assertions"
ps -p "$PID" -o pid,lstart,etime,args

echo
echo "===== PI 3 DEPLOYED COMMIT ====="
git -C /mnt/lrs001/liquid-research-l0l4 rev-parse HEAD

echo
echo "===== PI 3 REPOSITORY STATUS ====="
git -C /mnt/lrs001/liquid-research-l0l4 status --short

echo
echo "===== PI 3 RELEVANT COLLECTOR LOG BOUNDARIES ====="
sudo journalctl -u liquid-research-collector.service \
  --since "2026-09-26 22:40:00" \
  --no-pager | \
grep -Ei "Started|Starting|Stopped|Stopping|Main process exited|Failed|TELEMETRY-CAP-REACHED|TELEMETRY-DISABLED|persistence" || true
'
```

Expected frozen launch provenance is collector PID `26953`, with the production
epoch beginning `2026-09-26 22:43:18 PDT`. A different runtime is not silently
accepted as equivalent evidence. Apply the Section-17/18 stop conditions.

### Command 2 — PI 3 identify endpoint-epoch telemetry

Run from Mac. This command is read-only on PI 3.

```bash
ssh kristo@192.168.1.155 '
set -e
D="/mnt/lrs001/data/market_data_platform/telemetry"

test -d "$D"

echo "===== PI 3 ORDERED SOURCE FILES ====="
for f in \
  "$D/telemetry_2026-09-27.jsonl" \
  "$D/telemetry_2026-09-28.jsonl"
do
  test -f "$f"
  stat --printf="%n\t%s bytes\t%y\n" "$f"
  sha256sum "$f"
done
'
```

Both UTC-day files are required for the known worker epoch through the frozen
endpoint. Filenames do not replace persisted JSONL order as evidence.

---

### Command 3 — PI 3 freeze immutable snapshot

This writes only a new closeout evidence directory. It does not modify source
telemetry or stop/restart the collector.

```bash
ssh kristo@192.168.1.155 '
set -euo pipefail

SRC="/mnt/lrs001/data/market_data_platform/telemetry"
OUT="/mnt/lrs001/f3_gate2_closeout_20260928"

if [ -e "$OUT" ]; then
  echo "FATAL: closeout directory already exists: $OUT" >&2
  exit 1
fi

mkdir -p "$OUT/snapshot"

for name in \
  telemetry_2026-09-27.jsonl \
  telemetry_2026-09-28.jsonl
do
  test -f "$SRC/$name"
  cp --preserve=mode,timestamps "$SRC/$name" "$OUT/snapshot/$name"
done

printf "%s\n" \
  "telemetry_2026-09-27.jsonl" \
  "telemetry_2026-09-28.jsonl" \
  > "$OUT/ORDERED_FILES.txt"

(
  cd "$OUT/snapshot"
  sha256sum \
    telemetry_2026-09-27.jsonl \
    telemetry_2026-09-28.jsonl
) | tee "$OUT/SHA256SUMS"

for name in \
  telemetry_2026-09-27.jsonl \
  telemetry_2026-09-28.jsonl
do
  cmp --silent "$SRC/$name" "$OUT/snapshot/$name" || {
    echo "FATAL: source/snapshot mismatch: $name" >&2
    exit 1
  }
done

python3 -c "import json,sys
from pathlib import Path
for arg in sys.argv[1:]:
    p=Path(arg)
    with p.open(\"rb\") as fh:
        for line_no,raw in enumerate(fh,1):
            try:
                json.loads(raw)
            except Exception as exc:
                raise SystemExit(f\"FATAL: snapshot JSON integrity failure {p}:{line_no}: {exc}\")
print(\"PASS: snapshot JSON lines structurally parse\")" \
  "$OUT/snapshot/telemetry_2026-09-27.jsonl" \
  "$OUT/snapshot/telemetry_2026-09-28.jsonl"

{
  echo "source_host=$(hostname)"
  echo "frozen_endpoint_utc=2026-09-28T07:22:28Z"
  echo "frozen_endpoint_wall_ns=1790580148000000000"
  echo "primary_start_batch=7037"
  echo "collector_pid=$(sudo systemctl show liquid-research-collector.service -p MainPID --value)"
  echo "collector_restarts=$(sudo systemctl show liquid-research-collector.service -p NRestarts --value)"
  echo "collector_start=$(sudo systemctl show liquid-research-collector.service -p ExecMainStartTimestamp --value)"
  printf "deployed_commit="
  git -C /mnt/lrs001/liquid-research-l0l4 rev-parse HEAD
} | tee "$OUT/PROVENANCE.txt"

echo "PASS: PI 3 immutable snapshot created and verified"
'
```

If the destination already exists, any byte comparison fails, or any copied
JSONL line is malformed/incomplete, stop. Do not overwrite, retry in place,
repair, or silently re-copy the frozen snapshot. A failed snapshot attempt is
preserved as failed evidence and requires an explicitly new closeout attempt.

### Command 4 — transfer frozen PI 3 evidence to Mac

Run on Mac.

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -e && \
DEST="research_out/F3_GATE2_CLOSEOUT_20260928" && \
test ! -e "$DEST" && \
mkdir -p "$DEST" && \
scp -pr \
  kristo@192.168.1.155:/mnt/lrs001/f3_gate2_closeout_20260928/. \
  "$DEST/"
```

Do not reuse an existing Mac destination directory.

### Command 5 — Mac transfer-integrity verification

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -euo pipefail && \
D="research_out/F3_GATE2_CLOSEOUT_20260928" && \
test -d "$D/snapshot" && \
(
  cd "$D/snapshot"
  shasum -a 256 -c ../SHA256SUMS
) && \
echo "PASS: transferred snapshot matches PI 3 SHA-256 manifest"
```

No endpoint selection or Gate-2 performance inspection may occur unless this
integrity verification passes.

---

### Command 6 — Mac outcome-blind candidate N

This inspects only completion identity and `wall_ns`. It must not print or
summarize Gate-2 performance measurements.

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -euo pipefail && \
D="research_out/F3_GATE2_CLOSEOUT_20260928" && \
python3 -c 'import json,sys
from pathlib import Path
ENDPOINT=1790580148000000000
d=Path(sys.argv[1])
paths=[d/"snapshot"/"telemetry_2026-09-27.jsonl",d/"snapshot"/"telemetry_2026-09-28.jsonl"]
eligible=[]
after=[]
for path in paths:
    if not path.is_file(): raise SystemExit(f"FATAL: missing snapshot file: {path}")
    with path.open("rb") as fh:
        for line_no,raw in enumerate(fh,1):
            try: rec=json.loads(raw)
            except Exception as exc: raise SystemExit(f"FATAL: malformed JSON {path}:{line_no}: {exc}")
            if rec.get("type") != "f3_persistence_complete": continue
            bid=rec.get("batch_id")
            wall=rec.get("wall_ns")
            if isinstance(bid,bool) or not isinstance(bid,int) or bid<1: raise SystemExit(f"FATAL: invalid batch_id {path}:{line_no}")
            if isinstance(wall,bool) or not isinstance(wall,int) or wall<0: raise SystemExit(f"FATAL: invalid wall_ns {path}:{line_no}")
            item=(wall,bid,path.name,line_no)
            (eligible if wall<=ENDPOINT else after).append(item)
if not eligible: raise SystemExit("FATAL: no F3 completion at/before endpoint")
candidate=max(bid for wall,bid,name,line_no in eligible)
if candidate<7037: raise SystemExit(f"FATAL: candidate N {candidate} precedes primary start")
(d/"CANDIDATE_N.txt").write_text(f"{candidate}\n")
print(f"CANDIDATE_N={candidate}")
if after:
    wall,bid,name,line_no=min(after)
    print(f"FIRST_COMPLETION_AFTER_ENDPOINT=batch_id={bid} wall_ns={wall} source={name}:{line_no}")
else:
    print("FIRST_COMPLETION_AFTER_ENDPOINT=UNKNOWN")' "$D"
```

`CANDIDATE_N.txt` is provisional boundary evidence only.

### Command 7 — Mac frozen complete-epoch structural validation

This invokes the frozen analyzer validation path but does not emit the
descriptive Gate-2 performance summary.

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -euo pipefail && \
D="research_out/F3_GATE2_CLOSEOUT_20260928" && \
python3 -c 'import sys
from pathlib import Path
from L1_CORE.market_data_platform.research.analyze_f3_gate2 import load_f3_observations,validate_and_pair
d=Path(sys.argv[1])
paths=[d/"snapshot"/"telemetry_2026-09-27.jsonl",d/"snapshot"/"telemetry_2026-09-28.jsonl"]
obs=load_f3_observations(paths)
pairs=validate_and_pair(obs)
ids=[p["batch_id"] for p in pairs]
if not ids: raise SystemExit("FATAL: no validated F3 pairs")
if ids != list(range(1,ids[-1]+1)): raise SystemExit("FATAL: validated IDs not contiguous from 1")
(d/"VALIDATED_BATCH_RANGE.txt").write_text(f"1..{ids[-1]}\n")
print("PASS: frozen complete-epoch structural validation")
print(f"VALIDATED_BATCH_RANGE=1..{ids[-1]}")' "$D"
```

Any failure here is a stop condition. Do not crop, repair, concatenate, or
redefine the evidence window.

### Command 8 — Mac confirm deterministic N from validated pairs

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -euo pipefail && \
D="research_out/F3_GATE2_CLOSEOUT_20260928" && \
python3 -c 'import sys
from pathlib import Path
from L1_CORE.market_data_platform.research.analyze_f3_gate2 import load_f3_observations,validate_and_pair
ENDPOINT=1790580148000000000
d=Path(sys.argv[1])
candidate=int((d/"CANDIDATE_N.txt").read_text().strip())
paths=[d/"snapshot"/"telemetry_2026-09-27.jsonl",d/"snapshot"/"telemetry_2026-09-28.jsonl"]
pairs=validate_and_pair(load_f3_observations(paths))
ids=[p["batch_id"] for p in pairs]
if candidate not in ids: raise SystemExit(f"FATAL: candidate N {candidate} absent from validated pairs")
if ids[:candidate] != list(range(1,candidate+1)): raise SystemExit("FATAL: missing/noncontiguous validated batch through N")
eligible=[p["batch_id"] for p in pairs if p["completion"]["wall_ns"]<=ENDPOINT]
if not eligible: raise SystemExit("FATAL: no validated completion at/before endpoint")
validated_n=max(eligible)
if validated_n != candidate: raise SystemExit(f"FATAL: candidate N={candidate}, validated N={validated_n}")
if validated_n<7037: raise SystemExit("FATAL: validated N precedes primary start")
(d/"VALIDATED_N.txt").write_text(f"{validated_n}\n")
print(f"PASS: VALIDATED_N={validated_n}")
print(f"PRIMARY_RANGE=7037..{validated_n}")' "$D"
```

Only after Command 8 passes is `N` accepted as the Section-17 endpoint.

---

### Command 9 — Mac produce primary `[7037, N]` descriptive report

This is the first command permitted to emit the frozen primary Gate-2
descriptive performance summary.

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -euo pipefail && \
D="research_out/F3_GATE2_CLOSEOUT_20260928" && \
N="$(cat "$D/VALIDATED_N.txt")" && \
python3 \
  L1_CORE/market_data_platform/research/prepare_f3_gate2_primary.py \
  "$D/snapshot/telemetry_2026-09-27.jsonl" \
  "$D/snapshot/telemetry_2026-09-28.jsonl" \
  --start-batch 7037 \
  --end-batch "$N" \
  > "$D/F3_GATE2_PRIMARY_7037_${N}.json" && \
test -s "$D/F3_GATE2_PRIMARY_7037_${N}.json" && \
echo "===== PRIMARY REPORT =====" && \
cat "$D/F3_GATE2_PRIMARY_7037_${N}.json" && \
echo && \
echo "===== PRIMARY REPORT SHA256 =====" && \
shasum -a 256 "$D/F3_GATE2_PRIMARY_7037_${N}.json"
```

The JSON is descriptive evidence only. It does not itself adjudicate Gate 2.

### Command 10 — Mac freeze final closeout hashes

```bash
cd "/Users/kristo/Desktop/Liquid Research" && \
set -euo pipefail && \
D="research_out/F3_GATE2_CLOSEOUT_20260928" && \
OUT="$D/FINAL_CLOSEOUT_SHA256.txt" && \
test ! -e "$OUT" && \
(
  cd "$D"
  find . -type f ! -name "FINAL_CLOSEOUT_SHA256.txt" -print0 | \
    LC_ALL=C sort -z | \
    while IFS= read -r -d "" f; do
      shasum -a 256 "$f"
    done
) > "$OUT" && \
cat "$OUT"
```

The final manifest excludes itself and must be created only once.

### Command 11 — Gate-2 adjudication with frozen template

No shell command performs the scientific adjudication automatically.

Use:

`L1_CORE/market_data_platform/research/F3_GATE2_ADJUDICATION_TEMPLATE_V1.md`

Populate it only from verified continuity/provenance, frozen snapshot
integrity, validated `N`, the primary `[7037, N]` report, and the already
frozen Gate-2 structural criterion.

Allowed adjudication is `PASS`, `FAIL`, or `INCONCLUSIVE`. Do not introduce a
new numerical success threshold, population, endpoint rule, causal claim,
queue optimization, F2 reinterpretation, disk/network claim, trading-edge
claim, execution claim, or profitability/economic claim.

### Command 12 — preserve final closeout state

After adjudication, preserve the completed adjudication artifact alongside
the frozen evidence. Record its SHA-256 separately or regenerate a new
post-adjudication manifest with an explicitly different filename. Never
rewrite the already-frozen `FINAL_CLOSEOUT_SHA256.txt` manifest.

Do not migrate or redeploy the collector as part of Gate-2 closeout. Any
collector migration is a separate post-closeout operation.

---

## 12. Stop conditions

Stop without adjudicating the original primary window if any of these are
established:

- collector/worker restart within the candidate primary window;
- worker-epoch discontinuity;
- instrumentation/schema change;
- frozen queue-capacity change;
- deployment/environment boundary that invalidates comparability;
- telemetry compromise affecting required evidence;
- inability to determine `N` deterministically;
- missing/non-contiguous required evidence;
- unmatched handoff/completion pair;
- broken observer provenance;
- evidence-integrity failure;
- frozen structural validation failure.

Preserve all evidence.

Follow Sections 17 and 18 for any required fresh prospective observation
window. Do not repair or concatenate the failed window.

---

## 13. Evidence boundary reminder

The complete finite validation snapshot is structural provenance through
candidate `N`; any retained batch above `N` is boundary/provenance evidence
only.

The confirmatory Gate-2 primary population remains only:

`[7037, N]`

No pre-protocol performance result from `1..7036` belongs in the primary
Gate-2 descriptive report.
