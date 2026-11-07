"""Synthetic tests for the shared notification controller."""

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("lrs_notification_controller.py")
SPEC = importlib.util.spec_from_file_location("lrs_notification_controller", MODULE_PATH)
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
CONFIG = {
    "monitor_id": "lrs1_checkpoint",
    "device": "pi3",
    "owner": "LRS1",
    "ntfy_topic": "synthetic_topic",
    "authorized_trigger": {
        "trigger_id": "CP-V2",
        "owner": "LRS1",
        "authority_ref": "SYNTHETIC_TEST_AUTHORITY_ONLY",
    },
}


def initial_state():
    return {"version": 1, "trigger_id": None}


class NotificationControllerTests(unittest.TestCase):
    def test_emoji_title_contains_readable_identity(self):
        self.assertEqual(
            controller.title("due", "pi3", "LRS1", "CP-V2 READY"),
            "⭐ 🍓 🎯 LRS1 — CP-V2 READY",
        )
        self.assertEqual(
            controller.title("reminder", "pi5", "LRS3", "CHECKPOINT REMINDER"),
            "✨ 🚀 💧 LRS3 — CHECKPOINT REMINDER",
        )

    def test_initial_due_sends_once_and_suppresses_duplicate(self):
        calls = []

        def sender(*args):
            calls.append(args)
            return True

        state, ok, result = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, sender,
        )
        self.assertTrue(ok)
        self.assertEqual(result, "sent")
        self.assertEqual(len(calls), 1)

        state, ok, result = controller.checkpoint(
            state, "CP-V2", "DUE", "Review checkpoint",
            NOW + timedelta(minutes=5), CONFIG, sender,
        )
        self.assertTrue(ok)
        self.assertEqual(result, "suppressed")
        self.assertEqual(len(calls), 1)

    def test_failed_delivery_retries_without_advancing_latch(self):
        attempts = iter([False, True])
        sender = lambda *args: next(attempts)

        state, ok, result = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, sender,
        )
        self.assertFalse(ok)
        self.assertEqual(result, "delivery_failed")
        self.assertNotIn("last_sent_at", state)

        state, ok, result = controller.checkpoint(
            state, "CP-V2", "DUE", "Review checkpoint",
            NOW + timedelta(minutes=5), CONFIG, sender,
        )
        self.assertTrue(ok)
        self.assertEqual(result, "sent")
        self.assertIn("last_sent_at", state)

    def test_reminder_occurs_at_24_hours_not_before(self):
        titles = []

        def sender(url, body, title):
            titles.append(title)
            return True

        state, _, _ = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, sender,
        )
        state, _, result = controller.checkpoint(
            state, "CP-V2", "DUE", "Review checkpoint",
            NOW + timedelta(hours=23, minutes=59), CONFIG, sender,
        )
        self.assertEqual(result, "suppressed")

        state, _, result = controller.checkpoint(
            state, "CP-V2", "DUE", "Review checkpoint",
            NOW + timedelta(hours=24), CONFIG, sender,
        )
        self.assertEqual(result, "sent")
        self.assertEqual(len(titles), 2)
        self.assertTrue(titles[-1].startswith("✨ 🍓 🎯"))

    def test_acknowledgement_stops_reminders(self):
        sender = lambda *args: True
        state, _, _ = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, sender,
        )
        state = controller.acknowledge(
            state, "CP-V2", NOW + timedelta(minutes=1),
        )
        state, ok, result = controller.checkpoint(
            state, "CP-V2", "DUE", "Review checkpoint",
            NOW + timedelta(days=2), CONFIG, sender,
        )
        self.assertTrue(ok)
        self.assertEqual(result, "acknowledged")

    def test_acknowledgement_requires_exact_trigger(self):
        state, _, _ = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, lambda *args: True,
        )
        with self.assertRaises(ValueError):
            controller.acknowledge(state, "OTHER", NOW)

    def test_outstanding_due_cannot_be_cleared_implicitly(self):
        state, _, _ = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, lambda *args: True,
        )
        for condition in ("NOT_DUE", "NO_ACTIVE_TRIGGER"):
            with self.subTest(condition=condition):
                with self.assertRaises(ValueError):
                    controller.checkpoint(
                        state, "CP-V2", condition, "",
                        NOW + timedelta(minutes=5), CONFIG,
                        lambda *args: True,
                    )

    def test_error_does_not_erase_outstanding_due(self):
        state, _, _ = controller.checkpoint(
            initial_state(), "CP-V2", "DUE", "Review checkpoint",
            NOW, CONFIG, lambda *args: True,
        )
        state, ok, result = controller.checkpoint(
            state, "CP-V2", "ERROR", "Detector failed",
            NOW + timedelta(minutes=5), CONFIG,
            lambda *args: True,
        )
        self.assertTrue(ok)
        self.assertEqual(result, "sent")
        self.assertEqual(state["condition"], "DUE")
        self.assertTrue(state["error_notified"])

    def test_error_can_rearm_after_recovery(self):
        calls = []

        def sender(*args):
            calls.append(args)
            return True

        state, _, _ = controller.checkpoint(
            initial_state(), "CP-V2", "ERROR", "Detector failed",
            NOW, CONFIG, sender,
        )
        state, _, _ = controller.checkpoint(
            state, "CP-V2", "NOT_DUE", "",
            NOW + timedelta(minutes=5), CONFIG, sender,
        )
        state, _, result = controller.checkpoint(
            state, "CP-V2", "ERROR", "Detector failed again",
            NOW + timedelta(minutes=10), CONFIG, sender,
        )
        self.assertEqual(result, "sent")
        self.assertEqual(len(calls), 2)


    def test_state_symlink_is_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "actual.json"
            target.write_text('{"version": 1}')
            target.chmod(0o600)
            link = root / "state.json"
            link.symlink_to(target)

            with self.assertRaises(ValueError):
                controller.load_state(link)

    def test_state_with_unsafe_permissions_is_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text('{"version": 1}')
            path.chmod(0o644)

            with self.assertRaises(ValueError):
                controller.load_state(path)

    def test_private_state_loads_successfully(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text('{"version": 1, "trigger_id": null}')
            path.chmod(0o600)

            state = controller.load_state(path)
            self.assertEqual(state["version"], 1)

    def test_unicode_title_survives_http_header_encoding(self):
        from email.header import decode_header, make_header
        from unittest.mock import patch

        captured = []

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout):
            captured.append(request)
            return FakeResponse()

        expected = "⭐ 🍓 🎯 LRS1 — CP-V2 READY"

        with patch.object(
            controller.urllib.request,
            "urlopen",
            side_effect=fake_urlopen,
        ):
            result = controller.send(
                "https://ntfy.sh/synthetic_test_topic",
                "Synthetic checkpoint only",
                expected,
            )

        self.assertTrue(result)
        self.assertEqual(len(captured), 1)

        encoded = captured[0].get_header("Title")
        decoded = str(make_header(decode_header(encoded)))
        self.assertEqual(decoded, expected)


    def test_atomic_state_persists_across_reads(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            expected = {
                "version": 1,
                "trigger_id": "SYNTHETIC-CP",
                "condition": "DUE",
                "last_sent_at": NOW.isoformat(),
            }
            controller.atomic_write(path, expected)
            self.assertEqual(controller.load_state(path), expected)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_corrupt_state_fails_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{invalid-json")
            path.chmod(0o600)
            with self.assertRaises(ValueError):
                controller.load_state(path)

    def test_configuration_symlink_is_rejected(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "config.json"
            target.write_text(json.dumps({
                "monitor_id": "synthetic",
                "device": "pi3",
                "owner": "LRS1",
                "state_dir": str(root / "state"),
                "ntfy_topic": "synthetic_topic",
                "healthchecks_url":
                    "https://hc-ping.com/synthetic-only",
            }))
            target.chmod(0o600)
            link = root / "config-link.json"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                controller.validate_config(link)

    def test_unsafe_state_directory_is_detected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            state_dir.mkdir(mode=0o755)
            self.assertNotEqual(
                state_dir.stat().st_mode & 0o777,
                0o700,
            )


    def test_due_requires_actionable_notification_body(self):
        calls = []

        def sender(*args):
            calls.append(args)
            return True

        state = initial_state()
        snapshot = dict(state)

        with self.assertRaises(ValueError):
            controller.checkpoint(
                state,
                "SYNTHETIC-CP",
                "DUE",
                "",
                NOW,
                CONFIG,
                sender,
            )

        self.assertEqual(state, snapshot)
        self.assertEqual(calls, [])

    def test_due_notification_body_identifies_action_and_acknowledgement(self):
        calls = []

        def sender(url, body, subject):
            calls.append((url, body, subject))
            return True

        body = (
            "Trigger: SYNTHETIC-CP reached its authorized threshold. "
            "Action: Review the checkpoint with the responsible specialist. "
            "Acknowledgement: Required on Pi3."
        )

        config = dict(CONFIG)
        config["authorized_trigger"] = {
            "trigger_id": "SYNTHETIC-CP",
            "owner": "LRS1",
            "authority_ref": "SYNTHETIC_TEST_AUTHORITY_ONLY",
        }

        state, ok, result = controller.checkpoint(
            initial_state(),
            "SYNTHETIC-CP",
            "DUE",
            body,
            NOW,
            config,
            sender,
        )

        self.assertTrue(ok)
        self.assertEqual(result, "sent")
        self.assertEqual(len(calls), 1)
        self.assertIn("Action:", calls[0][1])
        self.assertIn("Acknowledgement:", calls[0][1])


    def test_error_cli_does_not_send_healthy_heartbeat(self):
        import json
        import tempfile
        from unittest.mock import patch

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            state_dir = root / "state"

            config_path.write_text(json.dumps({
                "monitor_id": "synthetic_error",
                "device": "pi3",
                "owner": "LRS1",
                "state_dir": str(state_dir),
                "ntfy_topic": "synthetic_topic",
                "healthchecks_url":
                    "https://hc-ping.com/synthetic-only",
            }))
            config_path.chmod(0o600)

            requests = []

            def fake_urlopen(request, timeout):
                requests.append(request.full_url)
                return FakeResponse()

            with patch.object(
                controller.urllib.request,
                "urlopen",
                side_effect=fake_urlopen,
            ):
                result = controller.main([
                    "--config", str(config_path),
                    "check",
                    "--trigger-id", "SYNTHETIC-ERROR",
                    "--condition", "ERROR",
                    "--message",
                    "Trigger: Synthetic operational failure. "
                    "Action: Investigate the monitor. "
                    "Acknowledgement: Operator review required.",
                ])

            state = controller.load_state(state_dir / "state.json")

            self.assertNotEqual(result, 0)
            self.assertEqual(
                requests,
                ["https://ntfy.sh/synthetic_topic"],
            )
            self.assertTrue(state.get("error_notified"))


    def test_due_without_authorized_trigger_fails_closed(self):
        calls = []

        def sender(*args):
            calls.append(args)
            return True

        config = dict(CONFIG)
        config.pop("authorized_trigger", None)

        state = initial_state()
        snapshot = dict(state)

        with self.assertRaises(ValueError):
            controller.checkpoint(
                state,
                "SYNTHETIC-UNAUTHORIZED",
                "DUE",
                "Trigger: Synthetic only. "
                "Action: No research action authorized. "
                "Acknowledgement: Not applicable.",
                NOW,
                config,
                sender,
            )

        self.assertEqual(state, snapshot)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
