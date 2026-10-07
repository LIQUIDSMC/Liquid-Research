import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import lrs2_bridge_watchdog as monitor


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / "events.jsonl"
        self.state = self.root / "state"
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "grace_minutes": 60,
            "expected_daily_time": "05:00",
            "schedule_timezone": "America/Los_Angeles",
            "ntfy_topic": "synthetic_test_topic",
            "healthchecks_url": "https://hc-ping.com/synthetic-test",
            "state_dir": str(self.state),
            "evidence_file": str(self.evidence),
        }))
        self.config.chmod(0o600)

    def event(self, stamp, status="PASS"):
        value = {
            "event": "lrs2_snapshot_bridge",
            "status": status,
            "recorded_utc": stamp,
            "research_checkpoint": False,
            "cp15": False,
            "authority_transferred": False,
            "published_destination": "/synthetic/snapshot",
            "snapshot_id": "synthetic",
        }
        self.evidence.write_text(json.dumps(value) + "\n")
        return value

    def evaluate(self, now):
        return monitor.evaluate(
            self.evidence, datetime.fromisoformat(now), 60
        )[0]

    def run_main(self, responses):
        with patch("sys.argv", [
            "watchdog", "--config", str(self.config)
        ]), patch.object(monitor, "request", side_effect=responses) as send:
            with contextlib.redirect_stdout(io.StringIO()):
                result = monitor.main()
        return result, send

    def test_current_daily_publication_is_healthy(self):
        self.event("2026-10-07T12:04:09+00:00")
        self.assertEqual(self.evaluate("2026-10-07T21:00:00+00:00"), "HEALTHY")

    def test_previous_day_allowed_before_deadline_but_not_at_deadline(self):
        self.event("2026-10-06T12:04:09+00:00")
        self.assertEqual(self.evaluate("2026-10-07T12:59:59+00:00"), "HEALTHY")
        self.assertEqual(self.evaluate("2026-10-07T13:00:00+00:00"), "OVERDUE")

    def test_daylight_saving_deadline_uses_pacific_time(self):
        self.event("2026-10-31T12:04:00+00:00")
        self.assertEqual(self.evaluate("2026-11-01T13:59:59+00:00"), "HEALTHY")
        self.assertEqual(self.evaluate("2026-11-01T14:00:00+00:00"), "OVERDUE")

    def test_failure_alerts_before_deadline(self):
        self.event("2026-10-07T12:03:00+00:00", "FAIL")
        self.assertEqual(self.evaluate("2026-10-07T12:04:00+00:00"), "FAILED")

    def test_missing_malformed_and_incomplete_evidence_fail_closed(self):
        now = "2026-10-07T21:00:00+00:00"
        self.assertEqual(self.evaluate(now), "EVIDENCE_ERROR")
        for payload in ("", "not-json\n", '{"status":"PASS"}'):
            self.evidence.write_text(payload)
            self.assertEqual(self.evaluate(now), "EVIDENCE_ERROR")

    def test_future_timestamp_and_invalid_authority_rejected(self):
        self.event("2099-01-01T00:00:00+00:00")
        self.assertEqual(self.evaluate("2026-10-07T21:00:00+00:00"), "EVIDENCE_ERROR")
        value = self.event("2026-10-07T12:04:00+00:00")
        value["research_checkpoint"] = True
        self.evidence.write_text(json.dumps(value) + "\n")
        self.assertEqual(self.evaluate("2026-10-07T21:00:00+00:00"), "EVIDENCE_ERROR")

    def test_failed_alert_is_retried_and_success_suppresses_duplicates(self):
        self.event("2026-10-07T12:03:00+00:00", "FAIL")
        with patch.object(monitor, "evaluate", return_value=("FAILED", "synthetic")):
            result, send = self.run_main([False])
            self.assertEqual(result, 1)
            self.assertEqual(send.call_count, 1)
            self.assertFalse((self.state / "notified_state").exists())
            result, send = self.run_main([True])
            self.assertEqual(send.call_count, 1)
            self.assertEqual((self.state / "notified_state").read_text().strip(), "FAILED")
            result, send = self.run_main([])
            self.assertEqual(send.call_count, 0)

    def test_recovery_alert_then_heartbeat_and_duplicate_suppression(self):
        self.state.mkdir()
        (self.state / "notified_state").write_text("FAILED\n")
        with patch.object(monitor, "evaluate", return_value=("HEALTHY", "synthetic")):
            result, send = self.run_main([True, True])
            self.assertEqual(result, 0)
            self.assertIn("RECOVERED", send.call_args_list[0].args[2])
            self.assertEqual(send.call_count, 2)
            result, send = self.run_main([True])
            self.assertEqual(result, 0)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[0], "https://hc-ping.com/synthetic-test")

    def test_heartbeat_failure_returns_failure(self):
        with patch.object(monitor, "evaluate", return_value=("HEALTHY", "synthetic")):
            result, send = self.run_main([False])
            self.assertEqual(result, 1)

    def test_initial_healthy_run_is_quiet_then_sends_only_heartbeat(self):
        with patch.object(monitor, "evaluate", return_value=("HEALTHY", "synthetic")):
            result, send = self.run_main([True])
            self.assertEqual(result, 0)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[0], "https://hc-ping.com/synthetic-test")
            self.assertEqual((self.state / "notified_state").read_text().strip(), "HEALTHY")

    def test_main_uses_real_evidence_and_configured_schedule(self):
        config = json.loads(self.config.read_text())
        config["expected_daily_time"] = "00:00"
        config["schedule_timezone"] = "UTC"
        self.config.write_text(json.dumps(config))
        now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        self.event((now - timedelta(minutes=1)).isoformat())
        with patch.object(monitor, "datetime") as clock:
            clock.now.return_value = now
            clock.fromisoformat.side_effect = datetime.fromisoformat
            result, send = self.run_main([True])
        self.assertEqual(result, 0)
        self.assertEqual((self.state / "state").read_text().strip(), "HEALTHY")
        self.assertEqual(send.call_count, 1)

    def test_old_failure_is_stale_failure(self):
        self.event("2026-10-06T12:03:00+00:00", "FAIL")
        self.assertEqual(self.evaluate("2026-10-07T13:00:00+00:00"), "STALE_FAILURE")

    def test_configured_daily_time_changes_deadline(self):
        self.event("2026-10-07T12:04:00+00:00")
        condition, _ = monitor.evaluate(
            self.evidence, datetime.fromisoformat("2026-10-07T15:00:00+00:00"),
            60, "07:00", "America/Los_Angeles")
        self.assertEqual(condition, "OVERDUE")

    def test_insecure_config_rejected_before_notifications(self):
        self.config.chmod(0o644)
        with self.assertRaises(SystemExit):
            self.run_main([])


if __name__ == "__main__":
    unittest.main()
