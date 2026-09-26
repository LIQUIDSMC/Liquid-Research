"""Isolated standing-bridge infrastructure tests; no SSH or live LRS2 data."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lrs2_snapshot_bridge as bridge


class Result:
    def __init__(self, stdout=""):
        self.returncode = 0
        self.stdout = stdout
        self.stderr = ""


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.outgoing = self.root / "outgoing"
        self.outgoing.mkdir()
        self.key = self.root / "key"
        self.key.write_text("synthetic")
        self.snapshot_id = "20260926T120000.000000Z"
        self.snapshot = self.outgoing / self.snapshot_id
        self.snapshot.mkdir()
        self.commit = "a" * 40

        for name in ("obi_log.csv", "near_book_depth_log.csv"):
            (self.snapshot / name).write_text("a,b\n1,2\n")

        self.manifest = {
            "schema_version": 1,
            "purpose": "LRS2 bounded analytical snapshot",
            "research_checkpoint": False,
            "cp15": False,
            "source_host": "liquid-pi",
            "source_commit": self.commit,
            "snapshot_utc": "2026-09-26T12:00:00+00:00",
            "sources": {},
            "files": {},
        }
        self.save_manifest()

    def save_manifest(self):
        (self.snapshot / "MANIFEST.json").write_text(json.dumps(self.manifest))

    def receiver_json(self):
        return json.dumps({
            "status": "PASS",
            "published": True,
            "destination": f"/incoming/{self.snapshot_id}",
            "snapshot_id": self.snapshot_id,
            "source_host": "liquid-pi",
            "source_commit": self.commit,
            "manifest_sha256": "f" * 64,
            "research_checkpoint": False,
            "cp15": False,
            "authority_transferred": False,
        }) + "\n"

    def invoke(self, runner):
        with patch.object(bridge, "create_snapshot", return_value=self.snapshot), \
             patch.object(bridge.socket, "gethostname", return_value="liquid-pi"), \
             patch.object(bridge, "run_checked", side_effect=runner):
            return bridge.bridge_snapshot(
                outgoing_root=self.outgoing,
                obi_source=self.snapshot / "obi_log.csv",
                near_source=self.snapshot / "near_book_depth_log.csv",
                key=self.key,
                remote_user="kristo",
                remote_host="192.0.2.5",
                remote_repo=Path("/repo"),
                remote_publication_root=Path("/incoming"),
            )

    def test_success_and_exact_sequence(self):
        calls = []

        def runner(command):
            calls.append(command)
            if len(calls) == 4:
                return Result(self.receiver_json())
            return Result()

        result = self.invoke(runner)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[0][0], "ssh")
        self.assertIn("mkdir", calls[1])
        self.assertEqual(calls[2][0], "scp")
        self.assertEqual(calls[3][0], "ssh")
        self.assertIn("--expected-snapshot-id", calls[3])
        self.assertIn("--expected-source-host", calls[3])
        self.assertIn("--expected-source-commit", calls[3])

    def test_source_expectation_rejections(self):
        cases = [
            ("research_checkpoint", True),
            ("cp15", True),
            ("source_commit", "bad"),
            ("source_host", "other"),
            ("snapshot_utc", "2026-09-25T12:00:00+00:00"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                original = self.manifest[field]
                self.manifest[field] = value
                self.save_manifest()
                with patch.object(bridge.socket, "gethostname", return_value="liquid-pi"):
                    with self.assertRaises(Exception):
                        bridge.load_source_expectations(self.snapshot, self.outgoing)
                self.manifest[field] = original
                self.save_manifest()

    def test_extra_source_file_rejected(self):
        extra = self.snapshot / "extra"
        extra.write_text("x")
        with patch.object(bridge.socket, "gethostname", return_value="liquid-pi"):
            with self.assertRaisesRegex(ValueError, "exactly"):
                bridge.load_source_expectations(self.snapshot, self.outgoing)

    def test_remote_failure_stops_sequence(self):
        calls = []

        def runner(command):
            calls.append(command)
            if len(calls) == 2:
                raise RuntimeError("mkdir failed")
            return Result()

        with self.assertRaisesRegex(RuntimeError, "mkdir failed"):
            self.invoke(runner)
        self.assertEqual(len(calls), 2)

    def test_receiver_non_pass_rejected(self):
        calls = []

        def runner(command):
            calls.append(command)
            if len(calls) == 4:
                payload = json.loads(self.receiver_json())
                payload["status"] = "FAIL"
                return Result(json.dumps(payload) + "\n")
            return Result()

        with self.assertRaisesRegex(ValueError, "did not report PASS"):
            self.invoke(runner)

    def test_receiver_multiple_lines_rejected(self):
        calls = []

        def runner(command):
            calls.append(command)
            if len(calls) == 4:
                return Result("noise\n" + self.receiver_json())
            return Result()

        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.invoke(runner)

    def test_cli_failure_is_json_and_nonzero(self):
        with patch.object(bridge, "bridge_snapshot", side_effect=RuntimeError("synthetic")):
            from contextlib import redirect_stdout
            import io

            output = io.StringIO()
            with redirect_stdout(output):
                code = bridge.main([
                    "--outgoing-root", str(self.outgoing),
                    "--ssh-key", str(self.key),
                    "--remote-user", "kristo",
                    "--remote-host", "192.0.2.5",
                    "--remote-repo", "/repo",
                    "--remote-publication-root", "/incoming",
                ])

        self.assertEqual(code, 1)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "FAIL")
        self.assertFalse(payload["authority_transferred"])


if __name__ == "__main__":
    unittest.main()
