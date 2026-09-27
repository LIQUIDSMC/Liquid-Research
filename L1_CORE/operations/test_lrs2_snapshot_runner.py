import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lrs2_snapshot_runner as runner


SHA = "a" * 40


class Args:
    def __init__(self, root):
        self.repo = root / "repo"
        self.evidence_file = root / "state" / "events.jsonl"
        self.outgoing_root = root / "outgoing"
        self.obi_source = root / "obi.csv"
        self.near_source = root / "near.csv"
        self.ssh_key = root / "key"
        self.remote_user = "kristo"
        self.remote_host = "liquid-pi5"
        self.remote_repo = Path("/home/kristo/liquid-research-l0l4")
        self.remote_publication_root = Path("/home/kristo/lrs2_handoff/incoming")


class RunnerTests(unittest.TestCase):
    def make_repo(self, root):
        repo = root / "repo"
        (repo / ".git" / "refs" / "heads").mkdir(parents=True)
        (repo / ".git" / "HEAD").write_text(
            "ref: refs/heads/main\n", encoding="utf-8"
        )
        (repo / ".git" / "refs" / "heads" / "main").write_text(
            SHA + "\n", encoding="utf-8"
        )
        return repo

    def test_git_head_reads_symbolic_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            self.assertEqual(runner.git_head(repo), SHA)

    def test_git_head_rejects_invalid_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            (repo / ".git" / "refs" / "heads" / "main").write_text(
                "bad\n", encoding="utf-8"
            )
            with self.assertRaises(RuntimeError):
                runner.git_head(repo)

    def test_append_evidence_writes_one_json_line_and_fsyncs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "events.jsonl"
            event = {"status": "PASS", "event": "test"}

            with patch.object(os, "fsync", wraps=os.fsync) as fsync:
                runner.append_evidence(path, event)
                self.assertEqual(fsync.call_count, 1)

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), event)

    def test_pass_event_is_durably_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            args = Args(root)
            bridge_event = {
                "status": "PASS",
                "event": "lrs2_snapshot_bridge",
                "research_checkpoint": False,
                "cp15": False,
                "authority_transferred": False,
                "receiver_commit": SHA,
            }

            with patch.object(
                runner, "bridge_snapshot", return_value=dict(bridge_event)
            ) as bridge:
                event = runner.run(args)

            self.assertEqual(event["status"], "PASS")
            self.assertEqual(event["expected_remote_commit"], SHA)
            self.assertEqual(event["runner"], "lrs2_snapshot_runner")
            self.assertEqual(
                bridge.call_args.kwargs["expected_remote_commit"], SHA
            )

            stored = json.loads(
                args.evidence_file.read_text(encoding="utf-8").strip()
            )
            self.assertEqual(stored, event)

    def test_git_head_failure_is_recorded_as_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            args = Args(root)

            with patch.object(
                runner, "git_head", side_effect=RuntimeError("bad git state")
            ), patch.object(runner, "bridge_snapshot") as bridge:
                event = runner.run(args)

            bridge.assert_not_called()
            self.assertEqual(event["status"], "FAIL")
            self.assertFalse(event["research_checkpoint"])
            self.assertFalse(event["cp15"])
            self.assertFalse(event["authority_transferred"])
            self.assertIn("RuntimeError: bad git state", event["error"])

            stored = json.loads(
                args.evidence_file.read_text(encoding="utf-8").strip()
            )
            self.assertEqual(stored, event)

    def test_evidence_failure_after_pass_raises_diagnostic_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            args = Args(root)
            bridge_event = {
                "status": "PASS",
                "event": "lrs2_snapshot_bridge",
                "research_checkpoint": False,
                "cp15": False,
                "authority_transferred": False,
                "receiver_commit": SHA,
            }

            with patch.object(
                runner, "bridge_snapshot", return_value=dict(bridge_event)
            ), patch.object(
                runner,
                "append_evidence",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "durable evidence append failed after bridge status PASS",
                ) as raised:
                    runner.run(args)

            message = str(raised.exception)
            self.assertIn("OSError: disk full", message)
            self.assertIn('"status": "PASS"', message)
            self.assertIn('"receiver_commit":', message)


    def test_bridge_failure_is_recorded_and_remains_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            args = Args(root)

            with patch.object(
                runner, "bridge_snapshot", side_effect=RuntimeError("boom")
            ):
                event = runner.run(args)

            self.assertEqual(event["status"], "FAIL")
            self.assertFalse(event["research_checkpoint"])
            self.assertFalse(event["cp15"])
            self.assertFalse(event["authority_transferred"])
            self.assertIn("RuntimeError: boom", event["error"])

            stored = json.loads(
                args.evidence_file.read_text(encoding="utf-8").strip()
            )
            self.assertEqual(stored, event)


if __name__ == "__main__":
    unittest.main()
