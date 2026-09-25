"""
Market Data Platform - F2 collector telemetry (observational only).

Records timing/provenance for diagnosing the receive loop. It never
touches market-data buffers, the sequence tracker, or canonical storage,
and no telemetry call may raise into the collector. Disable with
LRS_TELEMETRY=0. Not part of the canonical schema.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from threading import RLock

DEFAULT_DIR = "/mnt/lrs001/data/market_data_platform/telemetry"
MAX_RECORDS = 200
MAX_BYTES = 64 * 1024
MAX_AGE_S = 10.0
FILE_CAP_BYTES = 200 * 1024 * 1024
DISABLE_AFTER = 20
WARN_EVERY = 100


def resolve_code_commit() -> str:
    env = os.environ.get("LRS_CODE_COMMIT")
    if env:
        return env
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=2)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


class Telemetry:
    def __init__(self, directory=None, enabled=True, code_commit="unknown"):
        self.enabled = bool(enabled)
        self.directory = directory or DEFAULT_DIR
        self.code_commit = code_commit
        self.compromised = False
        self.dropped = 0
        self._batch = []
        self._batch_bytes = 0
        self._batch_started = None
        self._consec_fail = 0
        self._total_fail = 0
        self._emit_ms = None
        self._file_bytes = {}
        self._flush_id = 0
        self._lock = RLock()

    @classmethod
    def disabled(cls):
        return cls(enabled=False)

    @classmethod
    def from_env(cls):
        if os.environ.get("LRS_TELEMETRY", "1") == "0":
            return cls.disabled()
        return cls(directory=os.environ.get("LRS_TELEMETRY_DIR") or DEFAULT_DIR,
                   enabled=True, code_commit=resolve_code_commit())

    def session_start(self, session_id):
        self.emit({"type": "session_start", "session_id": session_id,
                   "wall_ns": time.time_ns(), "mono_ns": time.monotonic_ns(),
                   "pid": os.getpid(), "code_commit": self.code_commit})

    def session_end(self, session_id, reason):
        self.emit({"type": "session_end", "session_id": session_id,
                   "wall_ns": time.time_ns(), "reason": reason})

    def loop_gap(self, session_id, seq, prev_seq, gap_ms, prev_end, t0):
        self.emit({"type": "loop_gap", "session_id": session_id, "seq": seq,
                   "prev_seq": prev_seq, "gap_ms": gap_ms, "prev_end": prev_end, "t0": t0})

    def big_msg(self, **fields):
        rec = {"type": "big_msg"}
        rec.update(fields)
        self.emit(rec)

    def f3_persistence(self, record):
        """Emit one F3 persistence observation without mutating the caller's record."""
        rec = dict(record)
        event_type = rec.get("type")
        if event_type not in ("persistence_handoff", "persistence_complete"):
            return
        rec["type"] = "f3_" + event_type
        rec["wall_ns"] = time.time_ns()
        self.emit(rec)

    def flush_record(self, session_id, buffer, rows_pending, trigger_seq, t4, t5,
                     ok, n_files, exc):
        if not self.enabled:
            return
        self._flush_id += 1
        self.emit({"type": "flush", "trigger_session_id": session_id,
                   "flush_id": self._flush_id, "buffer": buffer,
                   "rows_pending": rows_pending, "trigger_seq": trigger_seq,
                   "t4": t4, "t5": t5, "dur_ms": (t5 - t4) / 1e6, "ok": ok,
                   "n_files": n_files, "exc": exc,
                   "prev_emit_ms": self.take_emit_ms(), "dropped": self.dropped})

    def take_emit_ms(self):
        with self._lock:
            v, self._emit_ms = self._emit_ms, None
            return v

    def emit(self, rec):
        with self._lock:
            if not self.enabled or self.compromised:
                return
            try:
                line = json.dumps(rec, separators=(",", ":")) + "\n"
                if not self._batch:
                    self._batch_started = time.monotonic()
                self._batch.append(line)
                self._batch_bytes += len(line.encode())
                if (len(self._batch) >= MAX_RECORDS or self._batch_bytes >= MAX_BYTES
                        or time.monotonic() - self._batch_started >= MAX_AGE_S):
                    self._write()
                while self._batch and (len(self._batch) > MAX_RECORDS
                                       or self._batch_bytes > MAX_BYTES):
                    old = self._batch.pop(0)
                    self._batch_bytes -= len(old.encode())
                    self.dropped += 1
            except Exception as exc:
                self._on_failure(exc)

    def close(self):
        with self._lock:
            try:
                self._write()
            except Exception as exc:
                self._on_failure(exc)

    def _write(self):
        if not self._batch or not self.enabled or self.compromised:
            return
        t_start = time.monotonic_ns()
        try:
            os.makedirs(self.directory, exist_ok=True)
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            path = os.path.join(self.directory, "telemetry_%s.jsonl" % day)
            data = "".join(self._batch)
            n = len(data.encode())
            size = self._file_bytes.get(path)
            if size is None:
                size = os.path.getsize(path) if os.path.exists(path) else 0
            if size + n > FILE_CAP_BYTES:
                self.compromised = True
                self._batch.clear()
                self._batch_bytes = 0
                print("TELEMETRY-CAP-REACHED: %s - run is COMPROMISED, telemetry stopped" % path,
                      flush=True)
                return
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(data)
            self._file_bytes[path] = size + n
            self._batch.clear()
            self._batch_bytes = 0
            self._consec_fail = 0
        except Exception as exc:
            self._on_failure(exc)
        finally:
            self._emit_ms = (time.monotonic_ns() - t_start) / 1e6

    def _on_failure(self, exc):
        self._consec_fail += 1
        self._total_fail += 1
        if self._total_fail == 1 or self._total_fail % WARN_EVERY == 0:
            print("TELEMETRY-WARNING: %s: %s (failures=%d)" % (
                type(exc).__name__, str(exc)[:120], self._total_fail), flush=True)
        if self._consec_fail >= DISABLE_AFTER:
            self.enabled = False
            self._batch.clear()
            self._batch_bytes = 0
            print("TELEMETRY-DISABLED after %d consecutive failures" % self._consec_fail,
                  flush=True)
