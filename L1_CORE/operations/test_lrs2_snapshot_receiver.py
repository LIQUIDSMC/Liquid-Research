"""Isolated infrastructure fixtures only; never reads live research data."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lrs2_snapshot_receiver as receiver


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.stage = self.root / '.incoming'
        self.stage.mkdir()
        self.snapshot = '20260926T120000.000000Z'
        self.final = self.root / self.snapshot
        self.commit = 'a' * 40
        data = b'time,value\n2026-09-26,1\n'
        self.manifest = dict(schema_version=1, purpose='LRS2 bounded analytical snapshot',
                             research_checkpoint=False, cp15=False, source_host='liquid-pi',
                             source_commit=self.commit, snapshot_utc='2026-09-26T12:00:00+00:00',
                             sources=receiver.SOURCES.copy(), files={})
        for name in receiver.FILES:
            (self.stage / name).write_bytes(data)
            boundary = dict(size_bytes=len(data), mtime_ns=123, last_row='2026-09-26,1')
            self.manifest['files'][name] = dict(sha256=hashlib.sha256(data).hexdigest(), rows=1, columns=2,
                source_boundary=dict(before_copy=boundary.copy(), after_copy=boundary.copy()))
        self.save()

    def save(self):
        (self.stage / 'MANIFEST.json').write_text(json.dumps(self.manifest))

    def run_receiver(self):
        return receiver.receive(self.stage, self.root, self.snapshot, 'liquid-pi', self.commit)

    def rejected(self):
        with self.assertRaises(Exception):
            self.run_receiver()
        self.assertTrue(self.stage.is_dir())
        self.assertFalse(self.final.exists())

    def test_success(self):
        result = self.run_receiver()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(set(p.name for p in self.final.iterdir()), {'MANIFEST.json', *receiver.FILES})
        self.assertFalse(self.stage.exists())

    def test_manifest_failures(self):
        original = json.dumps(self.manifest)
        for field, bad in [('schema_version', True), ('schema_version', 2), ('purpose', 'other'),
                           ('cp15', 0), ('research_checkpoint', 'NO'), ('source_host', 'other'),
                           ('source_commit', 'b'*40), ('snapshot_utc', '2026-09-25T12:00:00+00:00'),
                           ('snapshot_utc', '2026-09-26T12:00:00'), ('sources', {})]:
            with self.subTest(field=field, bad=bad):
                self.manifest = json.loads(original)
                self.manifest[field] = bad
                self.save()
                self.rejected()

    def test_metadata_failures(self):
        original = json.dumps(self.manifest)
        for field, bad in [('rows', 2), ('columns', 3), ('sha256', '0'*64), ('rows', True)]:
            with self.subTest(field=field):
                self.manifest = json.loads(original)
                self.manifest['files'][receiver.FILES[0]][field] = bad
                self.save()
                self.rejected()

    def test_boundary_failures(self):
        original = json.dumps(self.manifest)
        for field, bad in [('size_bytes', 999), ('mtime_ns', -1), ('last_row', 'wrong')]:
            self.manifest = json.loads(original)
            for side in self.manifest['files'][receiver.FILES[0]]['source_boundary'].values():
                side[field] = bad
            self.save()
            self.rejected()
        self.manifest = json.loads(original)
        self.manifest['files'][receiver.FILES[0]]['source_boundary']['after_copy']['mtime_ns'] += 1
        self.save()
        self.rejected()

    def test_extra_and_missing(self):
        extra = self.stage / 'extra'
        extra.write_text('x')
        self.rejected()
        extra.unlink()
        (self.stage / receiver.FILES[0]).unlink()
        self.rejected()

    def test_symlink(self):
        path = self.stage / receiver.FILES[0]
        path.unlink()
        path.symlink_to(self.stage / receiver.FILES[1])
        self.rejected()

    def test_duplicate_json(self):
        p = self.stage / 'MANIFEST.json'
        p.write_text(p.read_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
        self.rejected()

    def test_tampered_bytes(self):
        (self.stage / receiver.FILES[0]).write_bytes(b'time,value\n2026-09-26,2\n')
        self.rejected()

    def test_destination_race(self):
        native = receiver.rename_exclusive
        def race(src, dst):
            dst.mkdir()
            native(src, dst)
        with patch.object(receiver, 'rename_exclusive', side_effect=race):
            with self.assertRaises(OSError):
                self.run_receiver()
        self.assertTrue(self.stage.is_dir())
        self.assertEqual(list(self.final.iterdir()), [])

    def test_existing_destination(self):
        self.final.mkdir()
        with self.assertRaises(ValueError):
            self.run_receiver()
        self.assertTrue(self.stage.exists())

    def test_mutation_during_parse(self):
        real = receiver.pd.read_csv
        def mutate(*a, **kw):
            (self.stage / receiver.FILES[0]).write_bytes(b'changed')
            return real(*a, **kw)
        with patch.object(receiver.pd, 'read_csv', side_effect=mutate):
            self.rejected()

    def test_cross_filesystem(self):
        original = Path.stat
        from types import SimpleNamespace
        def different_device(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path == self.stage:
                return SimpleNamespace(st_mode=value.st_mode, st_dev=value.st_dev + 1)
            return value
        with patch.object(Path, 'stat', different_device):
            with self.assertRaisesRegex(ValueError, 'share a filesystem'):
                self.run_receiver()
        self.assertTrue(self.stage.exists())
        self.assertFalse(self.final.exists())

    def test_invalid_csv_with_valid_hash(self):
        data = b'a,b\n"unterminated,1\n'
        name = receiver.FILES[0]
        (self.stage / name).write_bytes(data)
        entry = self.manifest['files'][name]
        entry['sha256'] = hashlib.sha256(data).hexdigest()
        for side in entry['source_boundary'].values():
            side['size_bytes'] = len(data)
            side['last_row'] = '"unterminated,1'
        self.save()
        self.rejected()

    def test_cli_failure_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = receiver.main([])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
