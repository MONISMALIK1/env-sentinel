"""Reporter — colored terminal output + JSON + GitHub Actions annotations."""

import json
import os
import sys
from datetime import datetime
from .differ import DiffResult, MultiDiffResult
from .validator import ValidationError
from .scanner import SecretFinding

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")


def _c(code, text):
    return text if _NO_COLOR else f"{code}{text}{RESET}"


def _ok(s):   return _c(GREEN, s)
def _err(s):  return _c(RED, s)
def _warn(s): return _c(YELLOW, s)
def _gray(s): return _c(GRAY, s)
def _bold(s): return _c(BOLD, s)
def _blue(s): return _c(BLUE, s)

LINE = "─" * 60


def print_diff(result: DiffResult, show_extra: bool = True) -> None:
    print()
    print(_bold("env-sentinel — Diff Report"))
    print(_gray(f"Base   : {result.base_path}"))
    print(_gray(f"Target : {result.target_path}"))
    print(_gray(LINE))
    print()

    if not result.has_issues and not result.extra_in_target:
        print(f"  {_ok('✓')}  {_bold('All keys present and set. No issues found.')}")
        print()
        return

    if result.missing_in_target:
        print(f"  {_err('✗')}  {_bold(f'{len(result.missing_in_target)} key(s) missing from target')}")
        for k in result.missing_in_target:
            print(f"      {_err(k)}")
        print()

    if result.empty_in_target:
        print(f"  {_warn('⚠')}  {_bold(f'{len(result.empty_in_target)} key(s) present but empty')}")
        for k in result.empty_in_target:
            print(f"      {_warn(k)}")
        print()

    if show_extra and result.extra_in_target:
        print(f"  {_blue('ℹ')}  {_bold(f'{len(result.extra_in_target)} undocumented key(s) in target (not in base)')}")
        for k in result.extra_in_target:
            print(f"      {_gray(k)}")
        print()

    print(_gray(LINE))
    print()
    if result.has_issues:
        print(f"  Result: {_err(_bold('FAILED'))}  — {result.total_issues} issue(s) found")
    else:
        print(f"  Result: {_ok(_bold('PASSED'))}")
    print()


def print_multi_diff(result: MultiDiffResult) -> None:
    print()
    print(_bold("env-sentinel — Multi-Environment Diff"))
    print(_gray(f"Template : {result.template_path}"))
    print(_gray(LINE))
    print()

    any_issue = False
    for env_path, diff in result.results.items():
        env_name = os.path.basename(env_path)
        if diff.has_issues:
            any_issue = True
            print(f"  {_err('✗')}  {_bold(env_name)}")
            for k in diff.missing_in_target:
                print(f"       {_err('missing')}  {k}")
            for k in diff.empty_in_target:
                print(f"       {_warn('empty')}   {k}")
        else:
            print(f"  {_ok('✓')}  {_bold(env_name)}")
        print()

    print(_gray(LINE))
    print()
    if any_issue:
        print(f"  Result: {_err(_bold('FAILED'))}")
    else:
        print(f"  Result: {_ok(_bold('PASSED — All environments in sync'))}")
    print()


def print_validation(errors: list[ValidationError], path: str) -> None:
    print()
    print(_bold("env-sentinel — Validation Report"))
    print(_gray(f"File : {path}"))
    print(_gray(LINE))
    print()

    if not errors:
        print(f"  {_ok('✓')}  {_bold('All values pass format validation.')}")
        print()
        return

    print(f"  {_warn('⚠')}  {_bold(f'{len(errors)} format issue(s) found')}")
    print()
    for e in errors:
        print(f"  {_warn('⚠')}  {_bold(e.key)}")
        print(_gray(f"     {e.message}"))
        print()

    print(_gray(LINE))
    print(f"\n  Result: {_warn(_bold('FORMAT ERRORS FOUND'))}\n")


def print_scan(findings: list[SecretFinding], path: str) -> None:
    print()
    print(_bold("env-sentinel — Secret Scan"))
    print(_gray(f"File : {path}"))
    print(_gray(LINE))
    print()

    if not findings:
        print(f"  {_ok('✓')}  {_bold('No secrets or leaked credentials detected.')}")
        print()
        return

    for f in findings:
        sev_color = _err if f.severity == "high" else _warn
        print(f"  {sev_color('✗')}  {_bold(f.key)}  [{sev_color(f.severity.upper())}]")
        print(_gray(f"     {f.reason}"))
        print(_gray(f"     Value: {f.value}"))
        print()

    print(_gray(LINE))
    high = sum(1 for f in findings if f.severity == "high")
    print(f"\n  Result: {_err(_bold(f'SECRET LEAK DETECTED — {high} high severity'))} \n")


def write_json(data: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def build_json_report(
    diff_results: list[DiffResult] = None,
    validation_errors: list[ValidationError] = None,
    secret_findings: list[SecretFinding] = None,
) -> dict:
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "diff": [
            {
                "base": r.base_path,
                "target": r.target_path,
                "missing": r.missing_in_target,
                "empty": r.empty_in_target,
                "extra": r.extra_in_target,
                "passed": not r.has_issues,
            }
            for r in (diff_results or [])
        ],
        "validation_errors": [
            {"key": e.key, "expected": e.expected, "message": e.message}
            for e in (validation_errors or [])
        ],
        "secret_findings": [
            {"key": f.key, "reason": f.reason, "severity": f.severity}
            for f in (secret_findings or [])
        ],
        "passed": not any([
            any(r.has_issues for r in (diff_results or [])),
            bool(validation_errors),
            any(f.severity == "high" for f in (secret_findings or [])),
        ]),
    }


def emit_github_annotations(
    diff_results: list[DiffResult] = None,
    secret_findings: list[SecretFinding] = None,
) -> None:
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    for r in (diff_results or []):
        for k in r.missing_in_target:
            print(f"::error file={r.target_path},title=env-sentinel::Missing required key: {k}")
        for k in r.empty_in_target:
            print(f"::warning file={r.target_path},title=env-sentinel::Key present but empty: {k}")
    for f in (secret_findings or []):
        level = "error" if f.severity == "high" else "warning"
        print(f"::{level} title=env-sentinel [SECRET]::{f.key} — {f.reason}")
