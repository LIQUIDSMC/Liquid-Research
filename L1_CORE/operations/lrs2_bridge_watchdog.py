#!/usr/bin/env python3
"""Monitor bridge publication evidence independently of the bridge scheduler."""
import argparse
import fcntl
import json
import os
import stat
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc


def evaluate(path, now, grace_minutes, daily_time="05:00", schedule_timezone="America/Los_Angeles"):
    try:
        with path.open("rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - 1048576))
            payload = stream.read()
        if not payload.endswith(b"\n"):
            raise ValueError("incomplete evidence record")
        lines = payload.splitlines()
        if not lines:
            raise ValueError("empty evidence")
        event = json.loads(lines[-1])
        if event.get("event") != "lrs2_snapshot_bridge":
            raise ValueError("unexpected evidence event")
        stamp = datetime.fromisoformat(event["recorded_utc"])
        if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
            raise ValueError("evidence timestamp must be UTC")
        if stamp > now:
            raise ValueError("future evidence timestamp")
        local = now.astimezone(ZoneInfo(schedule_timezone))
        hour, minute = map(int, daily_time.split(":"))
        due = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local < due + timedelta(minutes=grace_minutes):
            due -= timedelta(days=1)
        overdue = stamp < due.astimezone(UTC)
        if event.get("status") == "FAIL":
            if overdue:
                return "STALE_FAILURE", "Last attempt failed and no current-cycle evidence exists; inspect scheduler and bridge."
            return "FAILED", "Latest bridge attempt failed; inspect bridge journal."
        if event.get("status") != "PASS":
            raise ValueError("unknown evidence status")
        for flag in ("research_checkpoint", "cp15", "authority_transferred"):
            if event.get(flag) is not False:
                raise ValueError("invalid authority flags")
        if not event.get("published_destination") or not event.get("snapshot_id"):
            raise ValueError("missing publication identity")

        if overdue:
            return "OVERDUE", "No successful publication for the latest due daily cycle."
        return "HEALTHY", "Bridge publication evidence is current."
    except Exception:
        return "EVIDENCE_ERROR", "Bridge evidence missing, unreadable, or invalid."


def request(url, message=None, title=None):
    headers = {}
    if title:
        headers["Title"] = title
    body = message.encode("utf-8") if message is not None else b""
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def save(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".state-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config_stat = args.config.stat()
    if (not stat.S_ISREG(config_stat.st_mode)
            or config_stat.st_uid != os.getuid()
            or stat.S_IMODE(config_stat.st_mode) != 0o600):
        raise SystemExit("Config must be an owner-only mode-600 regular file.")
    config = json.loads(args.config.read_text())
    grace = config["grace_minutes"]
    if type(grace) is not int or not 10 <= grace <= 180:
        raise SystemExit("Invalid grace_minutes.")
    daily_time = config["expected_daily_time"]
    schedule_timezone = config["schedule_timezone"]
    try:
        if (not isinstance(daily_time, str) or len(daily_time) != 5
                or daily_time[2] != ":"
                or not daily_time[:2].isdigit()
                or not daily_time[3:].isdigit()):
            raise ValueError()
        hour, minute = map(int, daily_time.split(":"))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError()
        ZoneInfo(schedule_timezone)
    except Exception:
        raise SystemExit("Invalid expected schedule configuration.")
    topic = config["ntfy_topic"]
    heartbeat = config["healthchecks_url"]
    if (not topic or topic == "REPLACE_LOCALLY"
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in topic)
            or not heartbeat.startswith("https://hc-ping.com/")
            or "REPLACE_LOCALLY" in heartbeat):
        raise SystemExit("Provision valid local notification configuration.")
    state_dir = Path(config["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state_dir / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        condition, message = evaluate(
            Path(config["evidence_file"]), datetime.now(UTC), grace,
            daily_time, schedule_timezone
        )
        save(state_dir / "state", condition)
        notified_path = state_dir / "notified_state"
        previous = notified_path.read_text().strip() if notified_path.exists() else ""
        delivery_ok = True
        if not previous and condition == "HEALTHY":
            save(notified_path, condition)
        elif previous != condition:
            title = "LRS2 bridge " + ("RECOVERED" if condition == "HEALTHY" and previous else condition)
            delivery_ok = request("https://ntfy.sh/" + topic, message, title)
            if delivery_ok:
                save(notified_path, condition)
        heartbeat_ok = False
        if condition == "HEALTHY" and delivery_ok:
            heartbeat_ok = request(heartbeat)
        print(json.dumps({
            "condition": condition,
            "notification_ok": delivery_ok,
            "heartbeat_sent": heartbeat_ok,
        }, sort_keys=True))
        return 0 if condition == "HEALTHY" and delivery_ok and heartbeat_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
