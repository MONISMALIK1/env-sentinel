"""Format validators — check that env var values match expected types."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationError:
    key: str
    value: str
    expected: str
    message: str


# ── Individual validators ────────────────────────────────────────────────────

def _is_url(value: str) -> bool:
    """Accept any scheme://... URL — https, http, redis, amqp, ftp, etc."""
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://\S+", value))


def _is_integer(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_boolean(value: str) -> bool:
    return value.lower() in {"true", "false", "1", "0", "yes", "no", "on", "off"}


def _is_port(value: str) -> bool:
    try:
        p = int(value)
        return 1 <= p <= 65535
    except ValueError:
        return False


def _is_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))


def _is_uuid(value: str) -> bool:
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        value, re.IGNORECASE
    ))


def _is_hex(value: str) -> bool:
    return bool(re.match(r"^[0-9a-fA-F]+$", value))


def _is_base64(value: str) -> bool:
    import base64 as b64
    try:
        b64.b64decode(value, validate=True)
        return True
    except Exception:
        return False


def _is_json(value: str) -> bool:
    import json
    try:
        json.loads(value)
        return True
    except Exception:
        return False


def _is_nonempty(value: str) -> bool:
    return bool(value.strip())


def _is_semver(value: str) -> bool:
    return bool(re.match(r"^\d+\.\d+(\.\d+)?$", value))


def _is_duration(value: str) -> bool:
    """Matches values like 30s, 5m, 2h, 1d."""
    return bool(re.match(r"^\d+(ms|s|m|h|d)$", value, re.IGNORECASE))


def _is_db_url(value: str) -> bool:
    return bool(re.match(
        r"^(postgres(?:ql)?|mysql|sqlite|mongodb|redis)://",
        value, re.IGNORECASE
    ))


# ── Type registry ────────────────────────────────────────────────────────────

VALIDATORS = {
    "url":      (_is_url,      "a valid URL (https://...)"),
    "integer":  (_is_integer,  "an integer"),
    "boolean":  (_is_boolean,  "a boolean (true/false/1/0/yes/no)"),
    "port":     (_is_port,     "a valid port number (1-65535)"),
    "email":    (_is_email,    "a valid email address"),
    "uuid":     (_is_uuid,     "a valid UUID"),
    "hex":      (_is_hex,      "a hex string"),
    "base64":   (_is_base64,   "a base64-encoded string"),
    "json":     (_is_json,     "valid JSON"),
    "nonempty": (_is_nonempty, "a non-empty value"),
    "semver":   (_is_semver,   "a semver string (x.y.z)"),
    "duration": (_is_duration, "a duration (30s, 5m, 2h)"),
    "db_url":   (_is_db_url,   "a database URL"),
}

# ── Auto-detection heuristics ─────────────────────────────────────────────────

_AUTO_RULES = [
    # key pattern → expected type
    # DB URL must come before generic _URL rule so DATABASE_URL → db_url, not url
    (re.compile(r"(^|_)(DATABASE|DB)_(URL|DSN|URI)$", re.I), "db_url"),
    # _URL/_DSN/_URI/_ENDPOINT → url  (HOST excluded: hostnames are not full URLs)
    (re.compile(r"_(URL|DSN|URI|ENDPOINT)$",         re.I), "url"),
    (re.compile(r"_(PORT)$",                          re.I), "port"),
    (re.compile(r"_(EMAIL|MAIL)$",                    re.I), "email"),
    (re.compile(r"_(ENABLED|DISABLED|FLAG|DEBUG|VERBOSE)$", re.I), "boolean"),
    (re.compile(r"_(TIMEOUT|TTL|EXPIRY|EXPIRATION|INTERVAL|RETRY_DELAY)$", re.I), "integer"),
    (re.compile(r"_(UUID|GUID)$",                     re.I), "uuid"),
    # SECRET_KEY / SIGNING_KEY removed — secret values use many non-hex formats
]


def _auto_detect_type(key: str) -> Optional[str]:
    for pattern, typ in _AUTO_RULES:
        if pattern.search(key):
            return typ
    return None


# ── Public API ───────────────────────────────────────────────────────────────

def validate_value(key: str, value: str, expected_type: str) -> Optional[ValidationError]:
    """Validate a single key=value pair against an expected type."""
    if not value:
        return None  # empty values handled separately
    fn, description = VALIDATORS.get(expected_type, (None, expected_type))
    if fn is None:
        return None
    if not fn(value):
        return ValidationError(
            key=key,
            value=value,
            expected=expected_type,
            message=f"Expected {description}, got: {repr(value[:60])}",
        )
    return None


def validate_env(mapping: dict[str, str], schema: dict[str, str]) -> list[ValidationError]:
    """
    Validate a dict of env vars against a schema.

    schema: { KEY: "type" }  e.g. {"PORT": "port", "DATABASE_URL": "db_url"}
    """
    errors = []
    for key, expected_type in schema.items():
        value = mapping.get(key, "")
        err = validate_value(key, value, expected_type)
        if err:
            errors.append(err)
    return errors


def auto_validate(mapping: dict[str, str]) -> list[ValidationError]:
    """
    Run automatic type inference on all keys and validate.
    No schema required — infers types from key names.
    """
    errors = []
    for key, value in mapping.items():
        if not value:
            continue
        detected_type = _auto_detect_type(key)
        if detected_type:
            err = validate_value(key, value, detected_type)
            if err:
                errors.append(err)
    return errors
