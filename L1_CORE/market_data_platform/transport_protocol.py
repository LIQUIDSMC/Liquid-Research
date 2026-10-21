"""Bounded synthetic transport protocol; no network or filesystem writes."""
import json
import math
import struct
import time

from L1_CORE.market_data_platform import evidence_preservation as ep

VERSION = "LRS-TRANSPORT-V1"
HEADER, INVENTORY, FILE_START, FILE_DATA, FILE_END, EOS, ERROR = range(1, 8)
PREFIX = struct.Struct(">II")
MAX_REQUEST = 65536
MAX_JSON = 2097152
MAX_CHUNK = 1048576
MAX_PATH_BYTES = 1024
MAX_DEPTH = 32
MAX_ERROR_BYTES = 1024
MAX_INTEGER_DIGITS = 20
MAX_DIAGNOSTICS = 4096

DEFAULT_LIMITS = {
    "max_runtime_seconds": 30.0,
    "max_logical_bytes": 104857600,
    "max_artifact_count": 10000,
    "max_metadata_bytes": 1048576,
    "min_free_bytes_after_copy": 1073741824,
}
INTEGER_LIMITS = {
    "max_logical_bytes": (1, 10**11),
    "max_artifact_count": (3, 10**6),
    "max_metadata_bytes": (1, 10**7),
    "min_free_bytes_after_copy": (0, 10**13),
}
REQUEST_FIELDS = {
    "request_schema_version", "source_path", "run_id", "attempt_id",
    "expected_manifest_sha256", "expected_predeclaration_sha256",
    "expected_artifact_list_sha256", "limits",
}
FRAME_FIELDS = {
    HEADER: {"protocol_version", "run_id", "attempt_id"},
    INVENTORY: {
        "manifest_json_bytes", "manifest_sha256",
        "artifact_list_json_bytes", "artifact_list_sha256",
        "total_logical_bytes", "total_artifacts",
    },
    FILE_START: {"relative_path", "size_bytes", "sha256"},
    FILE_END: {"relative_path", "verified_sha256"},
    EOS: {"source_scan_verified", "timestamp_utc"},
    ERROR: {"error_schema_version", "code", "message"},
}
REMOTE_CODES = frozenset({
    "TRANSPORT_INVALID_INPUT", "TRANSPORT_SOURCE_INVALID",
    "TRANSPORT_SOURCE_CHANGED", "TRANSPORT_RESOURCE_LIMIT",
    "TRANSPORT_IO_ERROR",
})


class TransportError(ValueError):
    """Classified failure; secondary recording failure never replaces it."""

    def __init__(
        self, code, message, *, reporting_error=None, published=False,
        attempt_root=None, diagnostics=b"",
    ):
        super().__init__(message)
        self.code = code
        self.reporting_error = reporting_error
        self.published = published
        self.attempt_root = attempt_root
        self.diagnostics = diagnostics[-MAX_DIAGNOSTICS:]


def require(condition, message, code="TRANSPORT_MALFORMED_FRAME"):
    if not condition:
        raise TransportError(code, message)


def schema(value, fields):
    require(type(value) is dict and set(value) == fields, "Invalid schema")


def integer(value, minimum, maximum):
    require(
        type(value) is int and minimum <= value <= maximum,
        "Integer outside permitted range",
    )


def _depth_check(raw):
    """Bound structural nesting before invoking the recursive JSON decoder."""
    level = 0
    quoted = False
    escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (123, 91):
            level += 1
            require(level <= MAX_DEPTH, "JSON nesting limit exceeded")
        elif byte in (125, 93):
            level -= 1
            require(level >= 0, "Invalid JSON nesting")
    require(not quoted and level == 0, "Incomplete JSON structure")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _integer(token):
    require(
        len(token.lstrip("-")) <= MAX_INTEGER_DIGITS,
        "Integer token exceeds limit",
    )
    return int(token)


def _float(token):
    value = float(token)
    require(math.isfinite(value), "Nonfinite JSON number")
    return value


def _constant(token):
    raise TransportError("TRANSPORT_MALFORMED_FRAME", "Nonfinite JSON constant")


def decode_json(raw, maximum=MAX_JSON):
    require(type(raw) is bytes and len(raw) <= maximum, "JSON size limit exceeded")
    _depth_check(raw)
    try:
        return json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_float,
            parse_constant=_constant,
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, TransportError):
            raise
        raise TransportError(
            "TRANSPORT_MALFORMED_FRAME", "Invalid JSON encoding"
        ) from exc


def encode_json(value, maximum=MAX_JSON):
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    require(len(raw) <= maximum, "Encoded JSON size limit exceeded")
    _depth_check(raw)
    return raw


def relative_path(value):
    require(type(value) is str, "Path must be a string")
    try:
        require(len(value.encode("utf-8")) <= MAX_PATH_BYTES, "Path too long")
        return ep._path(value)
    except (ep.VerificationError, UnicodeError) as exc:
        raise TransportError("TRANSPORT_MALFORMED_FRAME", "Unsafe path") from exc


def uuid_value(value):
    try:
        ep._uuid(value)
    except ep.VerificationError as exc:
        raise TransportError("TRANSPORT_MALFORMED_FRAME", "Invalid UUID") from exc


def digest_value(value):
    try:
        ep._digest(value)
    except ep.VerificationError as exc:
        raise TransportError("TRANSPORT_MALFORMED_FRAME", "Invalid digest") from exc


def validate_limits(limits):
    schema(limits, set(DEFAULT_LIMITS))
    for name, (minimum, maximum) in INTEGER_LIMITS.items():
        integer(limits[name], minimum, maximum)
    seconds = limits["max_runtime_seconds"]
    require(
        type(seconds) in {int, float}
        and 0.1 <= seconds <= 86400
        and math.isfinite(seconds),
        "Invalid runtime allowance",
    )
    return dict(limits)


def verifier_limits(limits, remaining):
    require(
        type(remaining) in {int, float}
        and math.isfinite(remaining) and remaining > 0,
        "Operation deadline exhausted", "TRANSPORT_RESOURCE_LIMIT",
    )
    return {
        "max_artifacts": limits["max_artifact_count"] - 2,
        "max_metadata_bytes": limits["max_metadata_bytes"],
        "max_logical_bytes": limits["max_logical_bytes"],
        "max_runtime_seconds": remaining,
    }


def validate_request(value):
    try:
        schema(value, REQUEST_FIELDS)
        integer(value["request_schema_version"], 1, 1)
        uuid_value(value["run_id"])
        uuid_value(value["attempt_id"])
        for field in (
            "expected_manifest_sha256", "expected_predeclaration_sha256",
            "expected_artifact_list_sha256",
        ):
            digest_value(value[field])
        source = value["source_path"]
        require(
            type(source) is str and source.startswith("/")
            and "\x00" not in source
            and not any(part in {".", ".."} for part in source.split("/")),
            "Invalid absolute source path",
        )
        require(len(source.encode("utf-8")) <= 4096, "Source path too long")
        validate_limits(value["limits"])
        encode_json(value, MAX_REQUEST)
    except (TransportError, UnicodeError, ValueError) as exc:
        raise TransportError(
            "TRANSPORT_INVALID_INPUT", "Invalid transport request"
        ) from exc
    return value


def anchors(request):
    return {
        "expected_run_id": request["run_id"],
        "expected_attempt_id": request["attempt_id"],
        **{
            name: request[name]
            for name in (
                "expected_manifest_sha256", "expected_predeclaration_sha256",
                "expected_artifact_list_sha256",
            )
        },
    }


def validate_frame(kind, value):
    require(kind in FRAME_FIELDS, "Unknown metadata frame type")
    schema(value, FRAME_FIELDS[kind])
    if kind == HEADER:
        require(value["protocol_version"] == VERSION, "Protocol version mismatch")
        uuid_value(value["run_id"])
        uuid_value(value["attempt_id"])
    elif kind == INVENTORY:
        for name in ("manifest_json_bytes", "artifact_list_json_bytes"):
            integer(value[name], 1, 10**7)
        integer(value["total_logical_bytes"], 1, 10**11)
        integer(value["total_artifacts"], 3, 10**6)
        digest_value(value["manifest_sha256"])
        digest_value(value["artifact_list_sha256"])
    elif kind in {FILE_START, FILE_END}:
        relative_path(value["relative_path"])
        if kind == FILE_START:
            integer(value["size_bytes"], 0, 10**11)
            digest_value(value["sha256"])
        else:
            digest_value(value["verified_sha256"])
    elif kind == EOS:
        require(value["source_scan_verified"] is True, "Source scan not verified")
        timestamp = value["timestamp_utc"]
        require(
            type(timestamp) is str and len(timestamp) <= 64,
            "Invalid EOS timestamp",
        )
        from datetime import datetime
        try:
            parsed = datetime.fromisoformat(timestamp)
            require(
                parsed.tzinfo is not None
                and parsed.utcoffset().total_seconds() == 0,
                "EOS timestamp must be UTC",
            )
        except ValueError as exc:
            raise TransportError(
                "TRANSPORT_MALFORMED_FRAME", "Invalid EOS timestamp"
            ) from exc
    elif kind == ERROR:
        integer(value["error_schema_version"], 1, 1)
        require(type(value["code"]) is str, "Invalid remote code type")
        require(
            value["code"] in REMOTE_CODES, "Unknown remote error code",
            "TRANSPORT_PROTOCOL_ERROR",
        )
        message = value["message"]
        require(type(message) is str, "Invalid remote error message")
        try:
            require(
                len(message.encode("utf-8")) <= MAX_ERROR_BYTES,
                "Remote error message too long",
            )
        except UnicodeError as exc:
            raise TransportError(
                "TRANSPORT_MALFORMED_FRAME", "Invalid error message encoding"
            ) from exc
    return value


def pack_frame(kind, value):
    if kind == FILE_DATA:
        require(
            type(value) is bytes and 0 < len(value) <= MAX_CHUNK,
            "Invalid data chunk",
        )
        payload = value
    else:
        validate_frame(kind, value)
        payload = encode_json(value)
    return PREFIX.pack(kind, len(payload)) + payload


class Budget:
    def __init__(self, seconds, clock=time.monotonic):
        self.clock = clock
        self.deadline = clock() + seconds

    def remaining(self):
        remaining = self.deadline - self.clock()
        require(
            remaining > 0, "Operation deadline exhausted",
            "TRANSPORT_RESOURCE_LIMIT",
        )
        return remaining
