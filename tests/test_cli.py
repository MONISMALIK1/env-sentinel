"""Tests for the CLI commands."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from env_sentinel.cli import cli

# Test-only fake keys — constructed at runtime so push-protection scanners
# don't flag this test file as containing real credentials.
_FAKE_OPENAI  = "sk-" + "abcdefghijklmnopqrstuvwxyz123456789012"
_FAKE_SK_LIVE = "sk_live_" + "abcdefghijklmnopqrstuvwx"
_FAKE_SK_TEST = "sk_test_" + "abcdefghijklmnopqrstuvwx"


def write_tmp(content: str, suffix=".env"):
    """Write content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


class TestDiffCommand:
    def test_identical_files_exits_0(self):
        runner = CliRunner()
        base = write_tmp("A=1\nB=2\nC=3")
        target = write_tmp("A=1\nB=2\nC=3")
        result = runner.invoke(cli, ["diff", base, target])
        assert result.exit_code == 0

    def test_missing_key_exits_1(self):
        runner = CliRunner()
        base = write_tmp("A=1\nB=2\nC=3")
        target = write_tmp("A=1\nB=2")
        result = runner.invoke(cli, ["diff", base, target])
        assert result.exit_code == 1
        assert "C" in result.output

    def test_empty_value_exits_1(self):
        runner = CliRunner()
        base = write_tmp("A=1\nB=placeholder")
        target = write_tmp("A=1\nB=")
        result = runner.invoke(cli, ["diff", base, target])
        assert result.exit_code == 1

    def test_json_report_written(self, tmp_path):
        runner = CliRunner()
        base = write_tmp("A=1\nB=2")
        target = write_tmp("A=1\nB=2")
        report_path = str(tmp_path / "report.json")
        result = runner.invoke(cli, ["diff", base, target, "--json-report", report_path])
        assert result.exit_code == 0
        assert os.path.exists(report_path)
        data = json.loads(open(report_path).read())
        assert "generated_at" in data

    def test_scan_secrets_flag(self):
        runner = CliRunner()
        base = write_tmp("OPENAI_KEY=placeholder")
        target = write_tmp(f"OPENAI_KEY={_FAKE_OPENAI}")
        result = runner.invoke(cli, ["diff", base, target, "--scan-secrets"])
        assert result.exit_code == 1
        assert "OPENAI_KEY" in result.output


class TestAuditCommand:
    def test_all_clean_exits_0(self):
        runner = CliRunner()
        template = write_tmp("A=1\nB=2")
        staging = write_tmp("A=x\nB=y")
        prod = write_tmp("A=p\nB=q")
        result = runner.invoke(cli, [
            "audit",
            "--template", template,
            "--check", staging,
            "--check", prod,
        ])
        assert result.exit_code == 0

    def test_missing_key_exits_1(self):
        runner = CliRunner()
        template = write_tmp("A=1\nB=2")
        staging = write_tmp("A=x")     # B missing
        result = runner.invoke(cli, ["audit", "--template", template, "--check", staging])
        assert result.exit_code == 1

    def test_no_check_targets_exits_1(self):
        runner = CliRunner()
        template = write_tmp("A=1")
        result = runner.invoke(cli, ["audit", "--template", template])
        assert result.exit_code == 1


class TestValidateCommand:
    def test_valid_env_exits_0(self):
        runner = CliRunner()
        envfile = write_tmp("APP_PORT=3000\nAPI_URL=https://api.example.com\nDEBUG_ENABLED=true")
        result = runner.invoke(cli, ["validate", envfile])
        assert result.exit_code == 0

    def test_bad_port_exits_1(self):
        runner = CliRunner()
        envfile = write_tmp("APP_PORT=not_a_port")
        result = runner.invoke(cli, ["validate", envfile])
        assert result.exit_code == 1
        assert "APP_PORT" in result.output

    def test_bad_url_exits_1(self):
        runner = CliRunner()
        envfile = write_tmp("API_URL=not-a-url")
        result = runner.invoke(cli, ["validate", envfile])
        assert result.exit_code == 1


class TestScanCommand:
    def test_clean_file_exits_0(self):
        runner = CliRunner()
        envfile = write_tmp("APP_NAME=myapp\nPORT=3000")
        result = runner.invoke(cli, ["scan", envfile])
        assert result.exit_code == 0

    def test_openai_key_exits_1(self):
        runner = CliRunner()
        envfile = write_tmp(f"OPENAI_KEY={_FAKE_OPENAI}")
        result = runner.invoke(cli, ["scan", envfile])
        assert result.exit_code == 1
        assert "OPENAI_KEY" in result.output

    def test_stripe_test_key_exits_0_without_flag(self):
        runner = CliRunner()
        envfile = write_tmp(f"STRIPE_KEY={_FAKE_SK_TEST}")
        result = runner.invoke(cli, ["scan", envfile])
        # medium severity — exits 0 unless --fail-on-medium
        assert result.exit_code == 0

    def test_stripe_test_key_exits_1_with_flag(self):
        runner = CliRunner()
        envfile = write_tmp(f"STRIPE_KEY={_FAKE_SK_TEST}")
        result = runner.invoke(cli, ["scan", envfile, "--fail-on-medium"])
        assert result.exit_code == 1

    def test_json_report_scan(self, tmp_path):
        runner = CliRunner()
        envfile = write_tmp("APP_NAME=myapp")
        report_path = str(tmp_path / "scan.json")
        result = runner.invoke(cli, ["scan", envfile, "--json-report", report_path])
        assert result.exit_code == 0
        assert os.path.exists(report_path)


class TestCheckCommand:
    def test_all_clean_exits_0(self):
        runner = CliRunner()
        template = write_tmp("APP_NAME=placeholder\nPORT=3000")
        target = write_tmp("APP_NAME=myapp\nPORT=8080")
        result = runner.invoke(cli, ["check", "--template", template, "--check", target])
        assert result.exit_code == 0

    def test_missing_key_exits_1(self):
        runner = CliRunner()
        template = write_tmp("APP_NAME=placeholder\nPORT=3000\nDEBUG=false")
        target = write_tmp("APP_NAME=myapp")    # PORT, DEBUG missing
        result = runner.invoke(cli, ["check", "--template", template, "--check", target])
        assert result.exit_code == 1

    def test_secret_in_target_exits_1(self):
        runner = CliRunner()
        template = write_tmp("OPENAI_KEY=placeholder")
        target = write_tmp(f"OPENAI_KEY={_FAKE_OPENAI}")
        result = runner.invoke(cli, ["check", "--template", template, "--check", target])
        assert result.exit_code == 1

    def test_no_targets_exits_1(self):
        runner = CliRunner()
        template = write_tmp("A=1")
        result = runner.invoke(cli, ["check", "--template", template])
        assert result.exit_code == 1
