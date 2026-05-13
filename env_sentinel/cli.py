"""Click CLI — diff / validate / scan / audit commands."""

import os
import sys
import click

from .parser import parse
from .differ import diff, multi_diff
from .validator import auto_validate, validate_env
from .scanner import scan_env
from .reporter import (
    print_diff, print_multi_diff, print_validation, print_scan,
    write_json, build_json_report, emit_github_annotations,
)


@click.group()
@click.version_option(package_name="env-sentinel")
def cli():
    """env-sentinel — catch environment variable drift before it takes down production."""


# ── diff ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("base",   type=click.Path(exists=True))
@click.argument("target", type=click.Path(exists=True))
@click.option("--no-extra", is_flag=True, default=False,
              help="Don't report undocumented keys in target")
@click.option("--json-report", default=None, help="Write report to JSON file")
@click.option("--scan-secrets", is_flag=True, default=False,
              help="Also scan target for leaked secrets")
def diff_cmd(base, target, no_extra, json_report, scan_secrets):
    """Diff BASE against TARGET — find missing, empty, or undocumented keys.

    BASE is typically .env.example (your template).
    TARGET is the environment to validate (.env.production, etc.).
    """
    base_env = parse(base)
    target_env = parse(target)
    result = diff(base_env, target_env)
    print_diff(result, show_extra=not no_extra)

    findings = []
    if scan_secrets:
        findings = scan_env(target_env.mapping)
        print_scan(findings, target)

    if json_report:
        report = build_json_report(diff_results=[result], secret_findings=findings)
        write_json(report, json_report)
        click.echo(f"JSON report written to {json_report}")

    emit_github_annotations(diff_results=[result], secret_findings=findings)

    if result.has_issues or any(f.severity == "high" for f in findings):
        sys.exit(1)


# ── audit ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--template", required=True, type=click.Path(exists=True),
              help="Template file (.env.example)")
@click.option("--check", "targets", multiple=True, type=click.Path(exists=True),
              help="Env file(s) to check against template (repeatable)")
@click.option("--json-report", default=None, help="Write report to JSON file")
@click.option("--scan-secrets", is_flag=True, default=False,
              help="Also scan all files for leaked secrets")
def audit(template, targets, json_report, scan_secrets):
    """Audit multiple env files against a single template.

    Example:
      env-sentinel audit --template .env.example
        --check .env.staging --check .env.production
    """
    if not targets:
        click.echo("No --check targets provided.", err=True)
        sys.exit(1)

    template_env = parse(template)
    target_envs = [parse(t) for t in targets]
    result = multi_diff(template_env, target_envs)
    print_multi_diff(result)

    all_findings = []
    if scan_secrets:
        for env in target_envs:
            findings = scan_env(env.mapping)
            if findings:
                print_scan(findings, env.path)
                all_findings.extend(findings)

    all_diffs = list(result.results.values())

    if json_report:
        report = build_json_report(diff_results=all_diffs, secret_findings=all_findings)
        write_json(report, json_report)
        click.echo(f"JSON report written to {json_report}")

    emit_github_annotations(diff_results=all_diffs, secret_findings=all_findings)

    if result.has_issues or any(f.severity == "high" for f in all_findings):
        sys.exit(1)


# ── validate ─────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("envfile", type=click.Path(exists=True))
@click.option("--json-report", default=None, help="Write report to JSON file")
def validate(envfile, json_report):
    """Auto-validate value formats in an env file.

    Infers expected types from key names (PORT=integer, DATABASE_URL=db_url, etc.)
    and reports values that don't match.
    """
    env = parse(envfile)
    errors = auto_validate(env.mapping)
    print_validation(errors, envfile)

    if json_report:
        report = build_json_report(validation_errors=errors)
        write_json(report, json_report)
        click.echo(f"JSON report written to {json_report}")

    if errors:
        sys.exit(1)


# ── scan ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("envfile", type=click.Path(exists=True))
@click.option("--fail-on-medium", is_flag=True, default=False,
              help="Exit 1 on medium severity findings too (default: only high)")
@click.option("--json-report", default=None, help="Write report to JSON file")
def scan(envfile, fail_on_medium, json_report):
    """Scan an env file for leaked secrets, tokens, and API keys."""
    env = parse(envfile)
    findings = scan_env(env.mapping)
    print_scan(findings, envfile)

    if json_report:
        report = build_json_report(secret_findings=findings)
        write_json(report, json_report)
        click.echo(f"JSON report written to {json_report}")

    emit_github_annotations(secret_findings=findings)

    high = any(f.severity == "high" for f in findings)
    medium = any(f.severity == "medium" for f in findings)
    if high or (fail_on_medium and medium):
        sys.exit(1)


# ── check (all-in-one) ────────────────────────────────────────────────────────

@cli.command()
@click.option("--template", required=True, type=click.Path(exists=True),
              help="Template file (.env.example)")
@click.option("--check", "targets", multiple=True, type=click.Path(exists=True),
              help="Env file(s) to validate")
@click.option("--json-report", default=None)
def check(template, targets, json_report):
    """Run diff + validate + secret scan in one command.

    The most comprehensive check — runs everything at once.
    """
    if not targets:
        click.echo("No --check targets provided.", err=True)
        sys.exit(1)

    template_env = parse(template)
    failed = False
    all_diffs, all_errors, all_findings = [], [], []

    for target_path in targets:
        target_env = parse(target_path)

        # Diff
        d = diff(template_env, target_env)
        all_diffs.append(d)
        print_diff(d)
        if d.has_issues:
            failed = True

        # Validate
        errors = auto_validate(target_env.mapping)
        all_errors.extend(errors)
        if errors:
            print_validation(errors, target_path)
            failed = True

        # Scan
        findings = scan_env(target_env.mapping)
        all_findings.extend(findings)
        if findings:
            print_scan(findings, target_path)
            if any(f.severity == "high" for f in findings):
                failed = True

    if json_report:
        report = build_json_report(
            diff_results=all_diffs,
            validation_errors=all_errors,
            secret_findings=all_findings,
        )
        write_json(report, json_report)
        click.echo(f"JSON report written to {json_report}")

    emit_github_annotations(diff_results=all_diffs, secret_findings=all_findings)

    if failed:
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
