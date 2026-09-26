#!/usr/bin/env python3
"""Verify and publish an already transferred LRS2 snapshot; no transport or research."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
from datetime import datetime, timezone

import pandas as pd

FILES = ('obi_log.csv', 'near_book_depth_log.csv')
SOURCES = dict(zip(('obi', 'near_book_depth'), (
    'L3_RESEARCH_ENGINES/market_microstructure/data/' + name for name in FILES
)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), f'{label}: invalid fields')


def integer(value, minimum, label):
    require(type(value) is int and value >= minimum, f'{label}: invalid integer')


def fingerprint(path):
    s = path.lstat()
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def read_regular(path):
    before = fingerprint(path)
    require(stat.S_ISREG(before[2]) and before[3] == 1, f'{path.name}: requires unlinked regular file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as handle:
        s = os.fstat(handle.fileno())
        require((s.st_dev, s.st_ino) == before[:2], 'file replaced during open')
        data = handle.read()
    require(fingerprint(path) == before, 'file changed during read')
    return data, before


def rename_exclusive(source, destination):
    """Native atomic no-replace rename; unsupported systems fail closed."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        fn = libc.renamex_np
        fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        arguments = (os.fsencode(source), os.fsencode(destination), 4)  # RENAME_EXCL
    elif sys.platform.startswith('linux'):
        fn = libc.renameat2
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        arguments = (-100, os.fsencode(source), -100, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    else:
        raise RuntimeError('atomic no-replace rename unsupported')
    fn.restype = ctypes.c_int
    if fn(*arguments) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def receive(staging, publication_root, snapshot_id, source_host, source_commit):
    require(re.fullmatch(r'\d{8}T\d{6}\.\d{6}Z', snapshot_id) is not None, 'invalid expected snapshot ID')
    require(bool(source_host.strip()), 'empty expected source host')
    require(re.fullmatch(r'[0-9a-f]{40}', source_commit) is not None, 'invalid expected source commit')
    staging = Path(os.path.abspath(staging))
    root = Path(os.path.abspath(publication_root))
    require(root.resolve(strict=True) == root and root.is_dir(), 'publication root must be a real existing directory')
    require(staging.resolve(strict=True) == staging and staging.is_dir(), 'staging must be a real directory without symlinks')
    require(staging.parent == root and staging.name.startswith('.') and staging.name not in ('.', '..'), 'staging must be a hidden direct child of publication root')
    require(staging.stat().st_dev == root.stat().st_dev, 'staging and publication root must share a filesystem')
    destination = root / snapshot_id
    require(not os.path.lexists(destination), 'destination already exists')
    directory_identity = fingerprint(staging)
    expected = {'MANIFEST.json', *FILES}
    require(set(os.listdir(staging)) == expected, 'staging must contain exactly the three expected files')
    payloads, identities = {}, {}
    for name in sorted(expected):
        payloads[name], identities[name] = read_regular(staging / name)
    manifest = json.loads(payloads['MANIFEST.json'].decode('utf-8'), object_pairs_hook=strict_object)
    keys(manifest, ('schema_version', 'purpose', 'research_checkpoint', 'cp15', 'source_host', 'source_commit', 'snapshot_utc', 'sources', 'files'), 'manifest')
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1, 'unsupported manifest schema')
    require(manifest['purpose'] == 'LRS2 bounded analytical snapshot', 'invalid purpose')
    require(manifest['research_checkpoint'] is False and manifest['cp15'] is False, 'checkpoint flags must be false')
    require(manifest['source_host'] == source_host and manifest['source_commit'] == source_commit, 'source provenance mismatch')
    require(manifest['sources'] == SOURCES, 'source paths mismatch')
    timestamp = datetime.fromisoformat(manifest['snapshot_utc'])
    require(timestamp.tzinfo is not None and timestamp.utcoffset().total_seconds() == 0, 'snapshot time must be UTC')
    require(timestamp.strftime('%Y%m%dT%H%M%S.%fZ') == snapshot_id, 'snapshot identity mismatch')
    keys(manifest['files'], FILES, 'files')
    evidence = {}
    for name in FILES:
        entry = manifest['files'][name]
        keys(entry, ('sha256', 'rows', 'columns', 'source_boundary'), name)
        integer(entry['rows'], 0, 'rows')
        integer(entry['columns'], 1, 'columns')
        boundary = entry['source_boundary']
        keys(boundary, ('before_copy', 'after_copy'), 'source boundary')
        for side in boundary.values():
            keys(side, ('size_bytes', 'mtime_ns', 'last_row'), 'boundary metadata')
            integer(side['size_bytes'], 1, 'size')
            integer(side['mtime_ns'], 0, 'mtime')
            require(type(side['last_row']) is str, 'invalid last row')
        require(boundary['before_copy'] == boundary['after_copy'], 'source changed during copy')
        data = payloads[name]
        require(len(data) == boundary['before_copy']['size_bytes'], 'size mismatch')
        last_row = data[-65536:].splitlines()[-1].decode('utf-8')
        require(last_row == boundary['before_copy']['last_row'], 'last row mismatch')
        digest = hashlib.sha256(data).hexdigest()
        require(entry['sha256'] == digest, 'SHA256 mismatch')
        frame = pd.read_csv(io.BytesIO(data))
        require(len(frame) == entry['rows'] and len(frame.columns) == entry['columns'], 'CSV metadata mismatch')
        evidence[name] = dict(sha256=digest, size_bytes=len(data), rows=len(frame), columns=len(frame.columns))
    require(fingerprint(staging) == directory_identity, 'staging directory changed')
    require(set(os.listdir(staging)) == expected, 'staging file set changed')
    for name in sorted(expected):
        require(fingerprint(staging / name) == identities[name], 'staged file changed before publication')
    rename_exclusive(staging, destination)
    return dict(status='PASS', published=True, destination=str(destination), snapshot_id=snapshot_id,
                source_host=source_host, source_commit=source_commit,
                manifest_sha256=hashlib.sha256(payloads['MANIFEST.json']).hexdigest(), files=evidence)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    evidence = dict(status='FAIL', published=False)
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--staging', type=Path, required=True)
        parser.add_argument('--publication-root', type=Path, required=True)
        parser.add_argument('--expected-snapshot-id', required=True)
        parser.add_argument('--expected-source-host', required=True)
        parser.add_argument('--expected-source-commit', required=True)
        args = parser.parse_args(argv)
        evidence = receive(args.staging, args.publication_root, args.expected_snapshot_id,
                           args.expected_source_host, args.expected_source_commit)
    except Exception as exc:
        evidence['error'] = f'{type(exc).__name__}: {exc}'
    evidence.update(event='lrs2_snapshot_receive', schema_version=1,
                    recorded_utc=datetime.now(timezone.utc).isoformat(),
                    research_checkpoint=False, cp15=False, authority_transferred=False)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
