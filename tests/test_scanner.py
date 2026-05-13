"""Tests for the secret scanner."""

from env_sentinel.scanner import scan_entry, scan_env, SecretFinding

# Test-only fake keys — constructed at runtime so push-protection scanners
# don't flag this test file as containing real credentials.
_FAKE_OPENAI   = "sk-" + "abcdefghijklmnopqrstuvwxyz123456789012"
_FAKE_SK_LIVE  = "sk_live_" + "abcdefghijklmnopqrstuvwx"
_FAKE_SK_TEST  = "sk_test_" + "abcdefghijklmnopqrstuvwx"


class TestScanEntry:
    def test_openai_key_detected(self):
        finding = scan_entry("OPENAI_KEY", _FAKE_OPENAI)
        assert finding is not None
        assert finding.severity == "high"
        assert "OpenAI" in finding.reason

    def test_stripe_live_key_detected(self):
        finding = scan_entry("STRIPE_KEY", _FAKE_SK_LIVE)
        assert finding is not None
        assert finding.severity == "high"

    def test_stripe_test_key_detected(self):
        finding = scan_entry("STRIPE_KEY", _FAKE_SK_TEST)
        assert finding is not None
        assert finding.severity == "medium"

    def test_github_token_detected(self):
        finding = scan_entry("GITHUB_TOKEN", "ghp_" + "a" * 36)
        assert finding is not None
        assert finding.severity == "high"

    def test_aws_key_detected(self):
        finding = scan_entry("AWS_ACCESS_KEY", "AKIAIOSFODNN7EXAMPLE")
        assert finding is not None
        assert finding.severity == "high"

    def test_jwt_detected(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        finding = scan_entry("AUTH_TOKEN", jwt)
        assert finding is not None
        assert "JWT" in finding.reason

    def test_placeholder_ignored(self):
        assert scan_entry("API_KEY", "your_api_key_here") is None
        assert scan_entry("SECRET", "changeme") is None
        assert scan_entry("PASSWORD", "placeholder") is None

    def test_short_value_ignored(self):
        assert scan_entry("SECRET", "abc") is None

    def test_clean_value_no_finding(self):
        assert scan_entry("APP_NAME", "my-cool-app") is None
        assert scan_entry("LOG_LEVEL", "info") is None
        assert scan_entry("PORT", "3000") is None

    def test_high_entropy_password_detected(self):
        # A random-looking 32-char value for a key named PASSWORD
        finding = scan_entry("DB_PASSWORD", "xK9#mP2$vL8nQ5wR3jT7yU4iO6hF1gE0")
        assert finding is not None

    def test_value_redacted_in_finding(self):
        finding = scan_entry("OPENAI_KEY", _FAKE_OPENAI)
        assert finding is not None
        assert _FAKE_OPENAI not in finding.value
        assert "****" in finding.value

    def test_sendgrid_key_detected(self):
        key = "SG." + "a" * 22 + "." + "b" * 43
        finding = scan_entry("SENDGRID_KEY", key)
        assert finding is not None


class TestScanEnv:
    def test_clean_env_no_findings(self):
        mapping = {
            "APP_NAME": "myapp",
            "PORT": "3000",
            "DEBUG": "false",
            "LOG_LEVEL": "info",
        }
        assert scan_env(mapping) == []

    def test_finds_multiple_secrets(self):
        mapping = {
            "OPENAI_KEY": _FAKE_OPENAI,
            "STRIPE_KEY": _FAKE_SK_LIVE,
            "APP_NAME": "myapp",
        }
        findings = scan_env(mapping)
        keys = {f.key for f in findings}
        assert "OPENAI_KEY" in keys
        assert "STRIPE_KEY" in keys
        assert "APP_NAME" not in keys

    def test_returns_list(self):
        assert isinstance(scan_env({}), list)

    def test_empty_mapping(self):
        assert scan_env({}) == []
