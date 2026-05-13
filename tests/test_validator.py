"""Tests for format validators."""

from env_sentinel.validator import validate_value, auto_validate, ValidationError


class TestValidateValue:
    def test_valid_url(self):
        assert validate_value("API_URL", "https://api.example.com", "url") is None

    def test_invalid_url(self):
        err = validate_value("API_URL", "not-a-url", "url")
        assert err is not None
        assert err.key == "API_URL"

    def test_valid_integer(self):
        assert validate_value("PORT", "8080", "integer") is None

    def test_invalid_integer(self):
        err = validate_value("PORT", "abc", "integer")
        assert err is not None

    def test_valid_boolean_true(self):
        assert validate_value("DEBUG", "true", "boolean") is None

    def test_valid_boolean_false(self):
        assert validate_value("DEBUG", "false", "boolean") is None

    def test_valid_boolean_yes(self):
        assert validate_value("DEBUG", "yes", "boolean") is None

    def test_invalid_boolean(self):
        err = validate_value("DEBUG", "maybe", "boolean")
        assert err is not None

    def test_valid_port(self):
        assert validate_value("APP_PORT", "3000", "port") is None

    def test_invalid_port_out_of_range(self):
        err = validate_value("APP_PORT", "99999", "port")
        assert err is not None

    def test_invalid_port_string(self):
        err = validate_value("APP_PORT", "abc", "port")
        assert err is not None

    def test_valid_email(self):
        assert validate_value("ADMIN_EMAIL", "admin@example.com", "email") is None

    def test_invalid_email(self):
        err = validate_value("ADMIN_EMAIL", "not-an-email", "email")
        assert err is not None

    def test_valid_uuid(self):
        assert validate_value("APP_UUID", "550e8400-e29b-41d4-a716-446655440000", "uuid") is None

    def test_invalid_uuid(self):
        err = validate_value("APP_UUID", "not-a-uuid", "uuid")
        assert err is not None

    def test_valid_db_url(self):
        assert validate_value("DATABASE_URL", "postgres://user:pass@localhost/db", "db_url") is None

    def test_invalid_db_url(self):
        err = validate_value("DATABASE_URL", "http://notadatabase.com", "db_url")
        assert err is not None

    def test_valid_json(self):
        assert validate_value("CONFIG", '{"key": "value"}', "json") is None

    def test_invalid_json(self):
        err = validate_value("CONFIG", "{not json}", "json")
        assert err is not None

    def test_nonempty_passes(self):
        assert validate_value("KEY", "anything", "nonempty") is None

    def test_empty_value_skipped(self):
        # Empty values are not validated (handled by differ)
        assert validate_value("KEY", "", "url") is None

    def test_unknown_type_skipped(self):
        assert validate_value("KEY", "value", "unknown_type_xyz") is None


class TestAutoValidate:
    def test_detects_bad_port(self):
        errors = auto_validate({"APP_PORT": "not_a_port"})
        assert any(e.key == "APP_PORT" for e in errors)

    def test_detects_bad_url(self):
        errors = auto_validate({"API_URL": "not-a-url"})
        assert any(e.key == "API_URL" for e in errors)

    def test_detects_bad_boolean(self):
        errors = auto_validate({"DEBUG_ENABLED": "maybe"})
        assert any(e.key == "DEBUG_ENABLED" for e in errors)

    def test_valid_values_no_errors(self):
        errors = auto_validate({
            "APP_PORT": "3000",
            "API_URL": "https://api.example.com",
            "DEBUG_ENABLED": "true",
            "DATABASE_URL": "postgres://localhost/db",
        })
        assert errors == []

    def test_unknown_key_pattern_skipped(self):
        errors = auto_validate({"SOME_RANDOM_KEY": "anything"})
        assert errors == []

    def test_returns_list(self):
        result = auto_validate({})
        assert isinstance(result, list)
