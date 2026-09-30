#!/bin/bash
set -u

CONFIG="${1:-}"
if [ -z "$CONFIG" ] || [ ! -r "$CONFIG" ]; then
    echo "Usage: $0 /path/to/machine-watchdog.env" >&2
    exit 2
fi

# shellcheck disable=SC1090
. "$CONFIG"

: "${NODE_NAME:?NODE_NAME required}"
: "${STATE_DIR:?STATE_DIR required}"
: "${NTFY_TOPIC:?NTFY_TOPIC required}"
: "${HC_URL:?HC_URL required}"
: "${MIN_AVAILABLE_MIB:?MIN_AVAILABLE_MIB required}"
: "${MAX_SWAP_USED_MIB:?MAX_SWAP_USED_MIB required}"
: "${MAX_DISK_PERCENT:?MAX_DISK_PERCENT required}"
: "${MAX_TEMP_C:?MAX_TEMP_C required}"
: "${REQUIRE_LRS001:=no}"
: "${EXPECTED_LRS001_SOURCE:=}"
: "${REQUIRE_COLLECTOR:=no}"

LOG="$STATE_DIR/watchdog.log"
STATE="$STATE_DIR/state"
NOTIFIED_STATE="$STATE_DIR/notified_state"
LOCK="$STATE_DIR/lock"
OOM_BOOT="$STATE_DIR/oom_boot_id"
OOM_CURSOR="$STATE_DIR/oom_cursor"

mkdir -p "$STATE_DIR"

note() {
    printf '%s %s\n' "$(date -Is)" "$*" >> "$LOG"
}

alert() {
    local title="$1"
    local body="$2"

    if curl -fsS -m 10 --retry 2 \
        -H "Title: LRS Machine Health — ${NODE_NAME} — ${title}" \
        -d "$body" \
        "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1
    then
        note "ALERT-SENT $title $body"
        return 0
    else
        note "ALERT-FAILED $title $body"
        return 1
    fi
}

exec 9>"$LOCK"
flock -n 9 || exit 0

PROB=""

# ---- Memory -------------------------------------------------------------

MEM_AVAILABLE_KIB=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)

if [[ "$MEM_AVAILABLE_KIB" =~ ^[0-9]+$ ]]; then
    MEM_AVAILABLE_MIB=$((MEM_AVAILABLE_KIB / 1024))

    if [ "$MEM_AVAILABLE_MIB" -lt "$MIN_AVAILABLE_MIB" ]; then
        PROB="${PROB}low-memory:${MEM_AVAILABLE_MIB}MiB<${MIN_AVAILABLE_MIB}MiB;"
    fi
else
    MEM_AVAILABLE_MIB="UNKNOWN"
    PROB="${PROB}memory-check-failed;"
fi

SWAP_TOTAL_KIB=$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)
SWAP_FREE_KIB=$(awk '/^SwapFree:/ {print $2}' /proc/meminfo)

if [[ "$SWAP_TOTAL_KIB" =~ ^[0-9]+$ ]] &&
   [[ "$SWAP_FREE_KIB" =~ ^[0-9]+$ ]] &&
   [ "$SWAP_FREE_KIB" -le "$SWAP_TOTAL_KIB" ]; then
    SWAP_USED_MIB=$(((SWAP_TOTAL_KIB - SWAP_FREE_KIB) / 1024))

    if [ "$SWAP_USED_MIB" -gt "$MAX_SWAP_USED_MIB" ]; then
        PROB="${PROB}swap-pressure:${SWAP_USED_MIB}MiB>${MAX_SWAP_USED_MIB}MiB;"
    fi
else
    SWAP_USED_MIB="UNKNOWN"
    PROB="${PROB}swap-check-failed;"
fi

# ---- Root disk ----------------------------------------------------------

ROOT_USED=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')

if [ -z "$ROOT_USED" ] || ! [[ "$ROOT_USED" =~ ^[0-9]+$ ]]; then
    PROB="${PROB}root-disk-check-failed;"
elif [ "$ROOT_USED" -ge "$MAX_DISK_PERCENT" ]; then
    PROB="${PROB}root-disk:${ROOT_USED}%>=${MAX_DISK_PERCENT}%;"
fi

# ---- Pi3 canonical storage ---------------------------------------------

if [ "$REQUIRE_LRS001" = "yes" ]; then
    if ! mountpoint -q /mnt/lrs001; then
        PROB="${PROB}lrs001-not-mounted;"
    else
        LRS001_SOURCE=$(findmnt -n -o SOURCE -T /mnt/lrs001 2>/dev/null)

        if [ -n "$EXPECTED_LRS001_SOURCE" ] &&
           [ "$LRS001_SOURCE" != "$EXPECTED_LRS001_SOURCE" ]; then
            PROB="${PROB}lrs001-wrong-source:${LRS001_SOURCE};"
        fi

        LRS001_USED=$(df -P /mnt/lrs001 | awk 'NR==2 {gsub("%","",$5); print $5}')

        if [ -z "$LRS001_USED" ] || ! [[ "$LRS001_USED" =~ ^[0-9]+$ ]]; then
            PROB="${PROB}lrs001-disk-check-failed;"
        elif [ "$LRS001_USED" -ge "$MAX_DISK_PERCENT" ]; then
            PROB="${PROB}lrs001-disk:${LRS001_USED}%>=${MAX_DISK_PERCENT}%;"
        fi
    fi
fi

# ---- Temperature / throttling ------------------------------------------

TEMP_RAW=$(vcgencmd measure_temp 2>/dev/null || true)
TEMP_C=$(printf '%s\n' "$TEMP_RAW" | sed -n "s/^temp=\([0-9.]*\)'C$/\1/p")

if [ -z "$TEMP_C" ]; then
    PROB="${PROB}temperature-check-failed;"
elif awk -v actual="$TEMP_C" -v maximum="$MAX_TEMP_C" \
         'BEGIN {exit !(actual >= maximum)}'
then
    PROB="${PROB}temperature:${TEMP_C}C>=${MAX_TEMP_C}C;"
fi

THROTTLED=$(vcgencmd get_throttled 2>/dev/null | sed -n 's/^throttled=//p')

if [[ "$THROTTLED" =~ ^0x[0-9A-Fa-f]+$ ]]; then
    THROTTLED_VALUE=$((THROTTLED))
    CURRENT_THROTTLE=$((THROTTLED_VALUE & 0xF))
    HISTORICAL_THROTTLE=$((THROTTLED_VALUE & 0xF0000))

    if [ "$CURRENT_THROTTLE" -ne 0 ]; then
        PROB="${PROB}current-throttled:${THROTTLED};"
    fi

    if [ "$HISTORICAL_THROTTLE" -ne 0 ]; then
        note "THROTTLE-HISTORY raw=$THROTTLED historical_mask=$(printf '0x%x' "$HISTORICAL_THROTTLE")"
    fi
else
    PROB="${PROB}throttle-check-failed;"
fi

# ---- Authoritative collector -------------------------------------------

if [ "$REQUIRE_COLLECTOR" = "yes" ]; then
    COLLECTOR_ENABLED=$(systemctl is-enabled liquid-research-collector.service 2>/dev/null || true)
    COLLECTOR_ACTIVE=$(systemctl is-active liquid-research-collector.service 2>/dev/null || true)

    if [ "$COLLECTOR_ENABLED" != "enabled" ]; then
        PROB="${PROB}collector-not-enabled:${COLLECTOR_ENABLED};"
    fi

    if [ "$COLLECTOR_ACTIVE" != "active" ]; then
        PROB="${PROB}collector-not-active:${COLLECTOR_ACTIVE};"
    fi
fi

# ---- New kernel OOM events ---------------------------------------------
#
# First run establishes a baseline at the current end of the kernel journal
# so historical OOM events do not generate deployment-time alerts.
#
# Subsequent runs inspect only journal entries after the persisted cursor.
# A boot-ID change establishes a new baseline for the new kernel epoch.

CURRENT_BOOT=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || true)
SAVED_BOOT=$(cat "$OOM_BOOT" 2>/dev/null || true)
SAVED_CURSOR=$(cat "$OOM_CURSOR" 2>/dev/null || true)

get_end_cursor() {
    journalctl -k -b -n 1 --show-cursor --no-pager 2>/dev/null |
        sed -n 's/^-- cursor: //p' |
        tail -1
}

if [ -n "$CURRENT_BOOT" ]; then
    if [ "$CURRENT_BOOT" != "$SAVED_BOOT" ] || [ -z "$SAVED_CURSOR" ]; then
        END_CURSOR=$(get_end_cursor)

        printf '%s\n' "$CURRENT_BOOT" > "$OOM_BOOT"

        if [ -n "$END_CURSOR" ]; then
            printf '%s\n' "$END_CURSOR" > "$OOM_CURSOR"
        else
            rm -f "$OOM_CURSOR"
            PROB="${PROB}oom-cursor-baseline-failed;"
        fi

        note "OOM-CURSOR-BASELINED boot=$CURRENT_BOOT"
    else
        OOM_SCAN_FILE=$(mktemp "$STATE_DIR/oom_scan.XXXXXX")

        if journalctl -k -b \
            --after-cursor="$SAVED_CURSOR" \
            --no-pager -o cat >"$OOM_SCAN_FILE" 2>/dev/null
        then
            if grep -Eiq 'out of memory|oom-kill|killed process [0-9]+ .*total-vm' \
                "$OOM_SCAN_FILE"
            then
                PROB="${PROB}new-kernel-oom;"
            fi

            END_CURSOR=$(get_end_cursor)

            if [ -n "$END_CURSOR" ]; then
                printf '%s\n' "$END_CURSOR" > "$OOM_CURSOR"
            else
                PROB="${PROB}oom-cursor-update-failed;"
            fi
        else
            PROB="${PROB}oom-scan-failed;"
        fi

        rm -f "$OOM_SCAN_FILE"
    fi
else
    PROB="${PROB}boot-id-check-failed;"
fi

# ---- Stateful alerting --------------------------------------------------

PREV=$(cat "$STATE" 2>/dev/null || echo "UNKNOWN")
NOTIFIED=$(cat "$NOTIFIED_STATE" 2>/dev/null || echo "NONE")

if [ -n "$PROB" ]; then
    note "PROBLEM $PROB"
    printf '%s\n' "PROBLEM" > "$STATE"

    if [ "$NOTIFIED" != "PROBLEM" ]; then
        if alert "PROBLEM" "$PROB $(date -Is)"; then
            printf '%s\n' "PROBLEM" > "$NOTIFIED_STATE"
        fi
    fi

    echo "NOT HEALTHY: $PROB"
    exit 1
fi

printf '%s\n' "HEALTHY" > "$STATE"

if [ "$PREV" = "PROBLEM" ] || [ "$NOTIFIED" = "PROBLEM" ]; then
    if alert "RECOVERED" "Machine healthy again $(date -Is)"; then
        printf '%s\n' "HEALTHY" > "$NOTIFIED_STATE"
    fi
elif [ "$NOTIFIED" != "HEALTHY" ]; then
    printf '%s\n' "HEALTHY" > "$NOTIFIED_STATE"
fi

if curl -fsS -m 10 --retry 2 "$HC_URL" >/dev/null 2>&1; then
    note "OK machine-health-heartbeat-sent mem_available=${MEM_AVAILABLE_MIB}MiB swap_used=${SWAP_USED_MIB}MiB root=${ROOT_USED}% temp=${TEMP_C}C throttled=${THROTTLED}"
    echo "HEALTHY: machine verified; heartbeat sent"
    exit 0
else
    note "HEARTBEAT-FAILED"
    echo "ERROR: machine healthy but Healthchecks heartbeat failed"
    exit 2
fi
