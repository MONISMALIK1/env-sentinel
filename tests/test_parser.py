"""Tests for the .env parser."""

from env_sentinel.parser import parse_string


def p(content): return parse_string(content)


class TestBasicParsing:
    def test_simple_key_value(self):
        env = p("FOO=bar")
        assert env.get("FOO") == "bar"

    def test_multiple_keys(self):
        env = p("A=1\nB=2\nC=3")
        assert env.get("A") == "1"
        assert env.get("B") == "2"
        assert env.get("C") == "3"

    def test_ignores_comments(self):
        env = p("# this is a comment\nFOO=bar")
        assert "FOO" in env.keys
        assert len(env.keys) == 1

    def test_ignores_blank_lines(self):
        env = p("\n\nFOO=bar\n\n")
        assert env.get("FOO") == "bar"

    def test_empty_value(self):
        env = p("FOO=")
        assert env.get("FOO") == ""
        entry = next(e for e in env.entries if e.key == "FOO")
        assert not entry.has_value

    def test_value_with_spaces(self):
        env = p('FOO="hello world"')
        assert env.get("FOO") == "hello world"

    def test_single_quoted_value(self):
        env = p("FOO='hello world'")
        assert env.get("FOO") == "hello world"

    def test_unquoted_value(self):
        env = p("FOO=hello")
        assert env.get("FOO") == "hello"

    def test_inline_comment_stripped(self):
        env = p("FOO=bar # this is a comment")
        assert env.get("FOO") == "bar"

    def test_export_prefix(self):
        env = p("export FOO=bar")
        assert env.get("FOO") == "bar"

    def test_keys_property(self):
        env = p("A=1\nB=2")
        assert env.keys == {"A", "B"}

    def test_mapping_property(self):
        env = p("A=1\nB=2")
        assert env.mapping == {"A": "1", "B": "2"}

    def test_value_with_equals(self):
        env = p('DATABASE_URL=postgres://user:pass@host/db')
        assert "postgres://" in env.get("DATABASE_URL")

    def test_key_with_numbers(self):
        env = p("AWS_S3_BUCKET=my-bucket")
        assert env.get("AWS_S3_BUCKET") == "my-bucket"

    def test_empty_file(self):
        env = p("")
        assert env.keys == set()
