"""Isolated notification-title tests for the machine watchdog."""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("lrs_machine_watchdog.sh")


class MachineWatchdogNotificationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text()

    def run_alert(self, node, condition, curl_success=True):
        match = re.search(
            r'(?ms)^alert\(\) \{\n.*?^\}',
            self.source,
        )
        self.assertIsNotNone(match, "alert() function missing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()

            capture = root / "captured.txt"
            curl = bin_dir / "curl"
            curl.write_text(
                '#!/bin/bash\n'
                'printf "%s\\n" "$@" > "$CAPTURE_FILE"\n'
                f'exit {0 if curl_success else 22}\n'
            )
            curl.chmod(0o700)

            device = {
                "liquid-pi": "🍓",
                "liquid-pi5": "🚀",
            }.get(node)

            if device is None:
                raise ValueError("Unsupported test node")

            shell = (
                'set -u\n'
                f'DEVICE_EMOJI="{device}"\n'
                'NTFY_TOPIC="synthetic-topic"\n'
                'note() { :; }\n'
                + match.group(0)
                + '\n'
                + f'alert "{condition}" "synthetic body"\n'
            )

            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
            env["CAPTURE_FILE"] = str(capture)

            result = subprocess.run(
                ["bash", "-c", shell],
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
            )

            captured = capture.read_text() if capture.exists() else ""
            return result, captured

    def test_pi3_problem_title(self):
        result, captured = self.run_alert("liquid-pi", "PROBLEM")
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "Title: 🚨 🍓 👑 GM — MACHINE HEALTH PROBLEM",
            captured,
        )

    def test_pi5_problem_title(self):
        result, captured = self.run_alert("liquid-pi5", "PROBLEM")
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "Title: 🚨 🚀 👑 GM — MACHINE HEALTH PROBLEM",
            captured,
        )

    def test_pi3_recovery_title(self):
        result, captured = self.run_alert("liquid-pi", "RECOVERED")
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "Title: ✅ 🍓 👑 GM — MACHINE HEALTH RECOVERED",
            captured,
        )

    def test_pi5_recovery_title(self):
        result, captured = self.run_alert("liquid-pi5", "RECOVERED")
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "Title: ✅ 🚀 👑 GM — MACHINE HEALTH RECOVERED",
            captured,
        )

    def test_unknown_condition_rejected(self):
        result, captured = self.run_alert("liquid-pi", "UNKNOWN")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(captured, "")

    def test_failed_delivery_returns_failure(self):
        result, captured = self.run_alert(
            "liquid-pi", "PROBLEM", curl_success=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Title: 🚨 🍓 👑 GM", captured)


class MachineWatchdogStateTests(unittest.TestCase):
    """Exercise production state transitions using synthetic files."""

    @classmethod
    def setUpClass(cls):
        source = SCRIPT.read_text()
        start = source.index("# ---- Stateful alerting ")
        end = source.index(
            'if curl -fsS -m 10 --retry 2 "$HC_URL"',
            start,
        )
        cls.transition_code = source[start:end]

    def run_sequence(self, steps):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            notified = root / "notified"
            events = root / "events"
            observations = []

            for problem, delivery_success in steps:
                shell = (
                    'set -u\n'
                    f'STATE="{state}"\n'
                    f'NOTIFIED_STATE="{notified}"\n'
                    f'PROB="{problem}"\n'
                    f'EVENTS="{events}"\n'
                    'note() { :; }\n'
                    'alert() {\n'
                    '  printf "%s\\n" "$1" >> "$EVENTS"\n'
                    f'  return {0 if delivery_success else 1}\n'
                    '}\n'
                    + self.transition_code
                )

                result = subprocess.run(
                    ["bash", "-c", shell],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                expected_rc = 1 if problem else 0
                self.assertEqual(
                    result.returncode,
                    expected_rc,
                    msg=result.stderr,
                )

                observations.append(
                    (
                        state.read_text().strip()
                        if state.exists() else None,
                        notified.read_text().strip()
                        if notified.exists() else None,
                    )
                )

            recorded = (
                events.read_text().splitlines()
                if events.exists() else []
            )
            return observations, recorded

    def test_initial_healthy_sends_no_alert(self):
        observations, events = self.run_sequence([("", True)])
        self.assertEqual(events, [])
        self.assertEqual(observations[-1], ("HEALTHY", "HEALTHY"))

    def test_problem_deduplicates_and_recovers(self):
        observations, events = self.run_sequence([
            ("synthetic-failure;", True),
            ("synthetic-failure;", True),
            ("", True),
            ("", True),
        ])
        self.assertEqual(events, ["PROBLEM", "RECOVERED"])
        self.assertEqual(observations[-1], ("HEALTHY", "HEALTHY"))

    def test_failed_problem_delivery_retries(self):
        observations, events = self.run_sequence([
            ("synthetic-failure;", False),
            ("synthetic-failure;", True),
            ("synthetic-failure;", True),
        ])
        self.assertEqual(events, ["PROBLEM", "PROBLEM"])
        self.assertIsNone(observations[0][1])
        self.assertEqual(observations[-1][1], "PROBLEM")

    def test_failed_recovery_delivery_retries(self):
        observations, events = self.run_sequence([
            ("synthetic-failure;", True),
            ("", False),
            ("", True),
            ("", True),
        ])
        self.assertEqual(
            events,
            ["PROBLEM", "RECOVERED", "RECOVERED"],
        )
        self.assertEqual(observations[1], ("HEALTHY", "PROBLEM"))
        self.assertEqual(observations[-1], ("HEALTHY", "HEALTHY"))


if __name__ == "__main__":
    unittest.main()
