"""Secret scanner — detect leaked API keys, tokens, and passwords in .env files."""

import math
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SecretFinding:
    key: str
    value: str
    reason: str
    severity: str   # "high" | "medium" | "low"


# ── Known secret patterns ────────────────────────────────────────────────────

_SECRET_PATTERNS = [
    # (regex, label, severity)
    (re.compile(r"^sk-[A-Za-z0-9]{32,}$"),                "OpenAI API key",           "high"),
    (re.compile(r"^sk_live_[A-Za-z0-9]{24,}$"),           "Stripe live secret key",   "high"),
    (re.compile(r"^sk_test_[A-Za-z0-9]{24,}$"),           "Stripe test secret key",   "medium"),
    (re.compile(r"^rk_live_[A-Za-z0-9]{24,}$"),           "Stripe restricted key",    "high"),
    (re.compile(r"^ghp_[A-Za-z0-9]{36}$"),                "GitHub personal token",    "high"),
    (re.compile(r"^github_pat_[A-Za-z0-9_]{82}$"),        "GitHub fine-grained token","high"),
    (re.compile(r"^gho_[A-Za-z0-9]{36}$"),                "GitHub OAuth token",       "high"),
    (re.compile(r"^AKIA[0-9A-Z]{16}$"),                   "AWS access key ID",        "high"),
    (re.compile(r"^[A-Za-z0-9/+]{40}$"),                  "AWS secret access key",    "medium"),
    (re.compile(r"^xoxb-[0-9]+-[A-Za-z0-9]+$"),          "Slack bot token",          "high"),
    (re.compile(r"^xoxp-[0-9]+-[A-Za-z0-9-]+$"),         "Slack user token",         "high"),
    (re.compile(r"^ya29\.[A-Za-z0-9._-]+$"),              "Google OAuth token",       "high"),
    (re.compile(r"^AIza[0-9A-Za-z_-]{35}$"),              "Google API key",           "high"),
    (re.compile(r"^[0-9a-f]{32}$"),                       "Possible MD5/hex secret",  "low"),
    (re.compile(r"^[0-9a-f]{64}$"),                       "Possible SHA-256 secret",  "low"),
    (re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"), "JWT token", "high"),
    (re.compile(r"^SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}$"),          "SendGrid API key", "high"),
    (re.compile(r"^AC[0-9a-f]{32}$"),                     "Twilio account SID",       "medium"),
    (re.compile(r"^SK[0-9a-f]{32}$"),                     "Twilio auth token",        "high"),
]

# Key name patterns that suggest the value is sensitive
_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|APIKEY|PRIVATE_KEY|"
    r"ACCESS_KEY|AUTH_KEY|CLIENT_SECRET|SIGNING_KEY|ENCRYPTION_KEY|"
    r"WEBHOOK_SECRET|HMAC_SECRET|MASTER_KEY|SALT|CREDENTIALS)",
    re.IGNORECASE,
)

# Values that are obviously placeholder (not real secrets)
_PLACEHOLDER_VALUES = {
    "your_api_key_here", "your-api-key", "changeme", "todo", "fixme",
    "xxx", "yyy", "zzz", "placeholder", "replace_me", "your_secret_here",
    "api_key", "secret", "password", "token", "example", "test",
    "development", "production", "staging", "localhost", "none", "null", "",
}


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def _is_placeholder(value: str) -> bool:
    return value.lower().strip() in _PLACEHOLDER_VALUES or len(value) < 4


def _match_pattern(value: str) -> Optional[tuple[str, str]]:
    """Return (label, severity) if value matches a known secret pattern."""
    for pattern, label, severity in _SECRET_PATTERNS:
        if pattern.match(value):
            return label, severity
    return None


def scan_entry(key: str, value: str) -> Optional[SecretFinding]:
    """
    Scan a single key=value pair for secret leaks.

    Returns a SecretFinding if suspicious, None if clean.
    """
    if _is_placeholder(value):
        return None

    # 1. Check against known secret patterns
    match = _match_pattern(value)
    if match:
        label, severity = match
        return SecretFinding(key=key, value=_redact(value), reason=f"Matches {label} pattern", severity=severity)

    # 2. Sensitive key name + high entropy value
    if _SENSITIVE_KEY_PATTERNS.search(key):
        entropy = _shannon_entropy(value)
        if entropy > 4.0 and len(value) >= 16:
            return SecretFinding(
                key=key,
                value=_redact(value),
                reason=f"Sensitive key name with high-entropy value (entropy={entropy:.1f})",
                severity="medium",
            )

    return None


def scan_env(mapping: dict[str, str]) -> list[SecretFinding]:
    """Scan all entries in an env mapping for secrets."""
    findings = []
    for key, value in mapping.items():
        finding = scan_entry(key, value)
        if finding:
            findings.append(finding)
    return findings


def _redact(value: str, show: int = 4) -> str:
    """Redact a secret value, showing only the first few chars."""
    if len(value) <= show:
        return "****"
    return value[:show] + "****"
