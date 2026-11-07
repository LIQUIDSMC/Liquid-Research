#!/usr/bin/env python3
"""Shared checkpoint notification controller; never determines research triggers."""

import argparse
import fcntl
import json
import os
import re
import stat
import tempfile
import urllib.request
from email.header import Header
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
REMINDER = timedelta(hours=24)

DEVICES = {"pi3": "🍓", "pi5": "🚀", "mac": "🖥️"}
OWNERS = {
    "LRS1": "🎯",
    "LRS2": "🔬",
    "LRS3": "💧",
    "LRS4": "🌤️",
    "GM": "👑",
}
EVENTS = {
    "due": "⭐",
    "reminder": "✨",
    "error": "🚨",
    "warning": "⚠️",
    "recovered": "✅",
    "healthy": "💚",
}


def title(event, device, owner, condition):
    if event not in EVENTS or device not in DEVICES or owner not in OWNERS:
        raise ValueError("Unknown event, device, or owner")
    if not isinstance(condition, str) or not condition.strip():
        raise ValueError("Condition must be nonempty")
    if "\n" in condition or "\r" in condition:
        raise ValueError("Condition must be one line")
    return f"{EVENTS[event]} {DEVICES[device]} {OWNERS[owner]} {owner} — {condition}"


def send(url, body="", notification_title=None):
    try:
        headers = {}
        if notification_title:
            headers["Title"] = Header(
                notification_title, "utf-8"
            ).encode()
        request = urllib.request.Request(
            url, data=body.encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def atomic_write(path, payload):
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_state(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"version": 1, "trigger_id": None}

    if (not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError("Unsafe notification state file")

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) != 0o600
                or (opened.st_dev, opened.st_ino)
                != (info.st_dev, info.st_ino)):
            raise ValueError("Notification state changed during read")
        with os.fdopen(fd, "r") as stream:
            fd = -1
            state = json.load(stream)
    finally:
        if fd >= 0:
            os.close(fd)

    if not isinstance(state, dict) or state.get("version") != 1:
        raise ValueError("Invalid notification state")
    return state


def parse_timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    return result.astimezone(UTC)


def validate_config(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError("Config must be owner-only mode-600 regular file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) != 0o600
                or (opened.st_dev, opened.st_ino)
                != (info.st_dev, info.st_ino)):
            raise ValueError("Configuration changed during read")
        with os.fdopen(fd, "r") as stream:
            fd = -1
            config = json.load(stream)
    finally:
        if fd >= 0:
            os.close(fd)

    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")

    required = (
        "monitor_id", "device", "owner", "state_dir",
        "ntfy_topic", "healthchecks_url",
    )
    if any(not isinstance(config.get(key), str) or not config[key]
           for key in required):
        raise ValueError("Missing monitor configuration")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", config["monitor_id"]):
        raise ValueError("Invalid monitor ID")
    if config["device"] not in DEVICES or config["owner"] not in OWNERS:
        raise ValueError("Unknown device or owner")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", config["ntfy_topic"]):
        raise ValueError("Invalid ntfy topic")
    if config["ntfy_topic"] == "REPLACE_LOCALLY":
        raise ValueError("Notification topic not provisioned")
    if (not config["healthchecks_url"].startswith("https://hc-ping.com/")
            or "REPLACE_LOCALLY" in config["healthchecks_url"]):
        raise ValueError("Healthchecks URL not provisioned")
    return config


def checkpoint(state, trigger_id, condition, body, now, config, sender=send):
    """Process an externally authorized checkpoint state.

    condition: NO_ACTIVE_TRIGGER, NOT_DUE, DUE, or ERROR.
    """
    if condition not in {"NO_ACTIVE_TRIGGER", "NOT_DUE", "DUE", "ERROR"}:
        raise ValueError("Unknown checkpoint condition")
    if condition in {"DUE", "NOT_DUE"}:
        authorization = config.get("authorized_trigger")
        if not isinstance(authorization, dict):
            raise ValueError("Active checkpoint lacks specialist authorization")

        required = ("trigger_id", "owner", "authority_ref")
        if any(
            not isinstance(authorization.get(key), str)
            or not authorization[key].strip()
            for key in required
        ):
            raise ValueError("Incomplete specialist trigger authorization")

        if (
            authorization["trigger_id"] != trigger_id
            or authorization["owner"] != config["owner"]
        ):
            raise ValueError("Checkpoint authorization identity mismatch")

    if condition in {"DUE", "ERROR"}:
        if not isinstance(body, str) or not body.strip():
            raise ValueError(
                "DUE and ERROR notifications require a nonempty message"
            )
    if not isinstance(trigger_id, str) or not trigger_id.strip():
        if condition not in {"NO_ACTIVE_TRIGGER", "ERROR"}:
            raise ValueError("Active checkpoint requires trigger identity")
    if condition == "NO_ACTIVE_TRIGGER":
        if state.get("condition") == "DUE":
            raise ValueError("Outstanding DUE trigger requires authorized closure")
        return {
            "version": 1,
            "trigger_id": None,
            "condition": "NO_ACTIVE_TRIGGER",
        }, True, "inactive"

    previous_condition = state.get("condition")
    previous_trigger = state.get("trigger_id")

    if condition == "ERROR":
        # Operational errors must not overwrite research checkpoint state.
        # Preserve the existing DUE identity, acknowledgement and reminders.
        if previous_trigger not in (None, trigger_id) and trigger_id:
            raise ValueError("Error trigger identity mismatch")
        state = dict(state)
        event = "error"
        should_send = state.get("error_notified") is not True
    else:
        if previous_condition == "DUE" and condition != "DUE":
            raise ValueError("Outstanding DUE trigger requires authorized closure")

        if previous_trigger not in (None, trigger_id):
            if previous_condition == "DUE":
                raise ValueError("Cannot replace outstanding DUE trigger")
            state = {"version": 1, "trigger_id": trigger_id}

        if condition == "DUE" and previous_condition != "DUE":
            state = {"version": 1, "trigger_id": trigger_id}

        state = {**state, "trigger_id": trigger_id, "condition": condition}
        state.pop("error_notified", None)

        if condition == "NOT_DUE":
            return state, True, "not_due"
        if state.get("acknowledged_at"):
            return state, True, "acknowledged"
        last = state.get("last_sent_at")
        event = "due" if not last else "reminder"
        should_send = not last or now - parse_timestamp(last) >= REMINDER

    if not should_send:
        return state, True, "suppressed"

    subject = title(
        event, config["device"], config["owner"],
        f"{trigger_id or config['monitor_id']} "
        + ("ERROR" if event == "error" else
           "READY" if event == "due" else "CHECKPOINT REMINDER"),
    )
    delivered = sender(
        "https://ntfy.sh/" + config["ntfy_topic"],
        body,
        subject,
    )
    if delivered:
        if event == "error":
            state["error_notified"] = True
        else:
            state["last_sent_at"] = now.isoformat()
    return state, delivered, "sent" if delivered else "delivery_failed"


def acknowledge(state, trigger_id, now):
    if state.get("trigger_id") != trigger_id:
        raise ValueError("Trigger identity mismatch")
    if state.get("condition") != "DUE":
        raise ValueError("Only DUE checkpoints can be acknowledged")
    if not state.get("last_sent_at"):
        raise ValueError("Checkpoint notification has not succeeded")
    if state.get("acknowledged_at"):
        return state
    return {**state, "acknowledged_at": now.isoformat()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    subcommands = parser.add_subparsers(dest="command", required=True)
    check = subcommands.add_parser("check")
    check.add_argument("--trigger-id", default="")
    check.add_argument(
        "--condition",
        choices=["NO_ACTIVE_TRIGGER", "NOT_DUE", "DUE", "ERROR"],
        required=True,
    )
    check.add_argument("--message", default="")
    ack = subcommands.add_parser("ack")
    ack.add_argument("--trigger-id", required=True)
    args = parser.parse_args(argv)

    config = validate_config(args.config)
    state_dir = Path(config["state_dir"])
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory_info = state_dir.lstat()
    if (not stat.S_ISDIR(directory_info.st_mode)
            or directory_info.st_uid != os.getuid()
            or stat.S_IMODE(directory_info.st_mode) != 0o700):
        raise ValueError("Unsafe state directory")

    lock_path = state_dir / "lock"
    lock_fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(lock_fd, "a+") as lock:
        lock_info = os.fstat(lock.fileno())
        if (not stat.S_ISREG(lock_info.st_mode)
                or lock_info.st_uid != os.getuid()
                or stat.S_IMODE(lock_info.st_mode) != 0o600):
            raise ValueError("Unsafe lock file")
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = state_dir / "state.json"
        state = load_state(state_path)
        now = datetime.now(UTC)

        if args.command == "ack":
            state = acknowledge(state, args.trigger_id, now)
            atomic_write(state_path, state)
            print(json.dumps({"status": "acknowledged",
                              "trigger_id": args.trigger_id}))
            return 0

        state, delivered, result = checkpoint(
            state, args.trigger_id, args.condition,
            args.message, now, config,
        )
        atomic_write(state_path, state)

        # An operational ERROR must never produce a healthy heartbeat.
        heartbeat = (
            send(config["healthchecks_url"])
            if delivered and args.condition != "ERROR"
            else False
        )
        print(json.dumps({
            "monitor_id": config["monitor_id"],
            "condition": args.condition,
            "result": result,
            "notification_ok": delivered,
            "heartbeat_sent": heartbeat,
        }, sort_keys=True))
        return 0 if delivered and heartbeat else 1


if __name__ == "__main__":
    raise SystemExit(main())
