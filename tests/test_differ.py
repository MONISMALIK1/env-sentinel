"""Tests for the diff engine."""

from env_sentinel.parser import parse_string
from env_sentinel.differ import diff, multi_diff


def env(content, path="test.env"):
    e = parse_string(content)
    e.path = path
    return e


class TestDiff:
    def test_identical_files_no_issues(self):
        base = env("A=1\nB=2\nC=3")
        target = env("A=1\nB=2\nC=3")
        result = diff(base, target)
        assert not result.has_issues
        assert result.missing_in_target == []
        assert result.empty_in_target == []

    def test_missing_key_detected(self):
        base = env("A=1\nB=2\nC=3")
        target = env("A=1\nB=2")
        result = diff(base, target)
        assert result.has_issues
        assert "C" in result.missing_in_target

    def test_multiple_missing_keys(self):
        base = env("A=1\nB=2\nC=3\nD=4")
        target = env("A=1")
        result = diff(base, target)
        assert sorted(result.missing_in_target) == ["B", "C", "D"]

    def test_extra_keys_detected(self):
        base = env("A=1")
        target = env("A=1\nB=2\nC=3")
        result = diff(base, target)
        assert "B" in result.extra_in_target
        assert "C" in result.extra_in_target

    def test_empty_value_in_target_flagged(self):
        base = env("A=1\nB=placeholder")
        target = env("A=1\nB=")
        result = diff(base, target)
        assert "B" in result.empty_in_target

    def test_empty_value_in_base_not_flagged_as_issue(self):
        # Placeholders in base are normal (.env.example often has KEY= with no value)
        base = env("A=\nB=")
        target = env("A=real_value\nB=another_value")
        result = diff(base, target)
        assert not result.has_issues

    def test_total_issues_count(self):
        base = env("A=1\nB=2\nC=3")
        target = env("A=1\nC=")   # B missing, C empty
        result = diff(base, target)
        assert result.total_issues == 2

    def test_has_issues_false_when_clean(self):
        base = env("A=1")
        target = env("A=1")
        assert not diff(base, target).has_issues


class TestMultiDiff:
    def test_all_envs_match(self):
        template = env("A=1\nB=2", "template")
        staging = env("A=x\nB=y", "staging")
        prod = env("A=p\nB=q", "prod")
        result = multi_diff(template, [staging, prod])
        assert not result.has_issues

    def test_one_env_missing_key(self):
        template = env("A=1\nB=2", "template")
        staging = env("A=x\nB=y", "staging")
        prod = env("A=p", "prod")         # missing B
        result = multi_diff(template, [staging, prod])
        assert result.has_issues
        assert "B" in result.results["prod"].missing_in_target

    def test_all_missing_report(self):
        template = env("A=1\nB=2\nC=3", "template")
        staging = env("A=x", "staging")   # missing B, C
        result = multi_diff(template, [staging])
        missing = result.all_missing()
        assert "staging" in missing
        assert "B" in missing["staging"]
        assert "C" in missing["staging"]
