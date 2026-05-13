"""Diff engine — compare two parsed env files."""

from dataclasses import dataclass, field
from .parser import ParsedEnv


@dataclass
class DiffResult:
    base_path: str
    target_path: str
    missing_in_target: list[str]    # keys in base but not in target
    extra_in_target: list[str]      # keys in target but not in base
    empty_in_target: list[str]      # keys present but with no value in target
    empty_in_base: list[str]        # keys present but with no value in base

    @property
    def has_issues(self) -> bool:
        return bool(
            self.missing_in_target or
            self.empty_in_target
        )

    @property
    def total_issues(self) -> int:
        return len(self.missing_in_target) + len(self.empty_in_target)


def diff(base: ParsedEnv, target: ParsedEnv) -> DiffResult:
    """
    Diff base against target.

    'base' is typically .env.example (the template / source of truth).
    'target' is the environment you want to validate (.env.production, etc.).

    Reports:
      - Keys in base missing from target (required but not set)
      - Keys in target not in base (undocumented)
      - Keys present but empty in target
    """
    base_keys = base.keys
    target_keys = target.keys
    target_map = target.mapping
    base_map = base.mapping

    missing = sorted(base_keys - target_keys)
    extra = sorted(target_keys - base_keys)

    # Keys present in target but empty
    empty_target = sorted(
        k for k in base_keys & target_keys
        if not target_map.get(k)
    )

    # Keys present in base but empty (placeholders)
    empty_base = sorted(
        k for k in base_keys
        if not base_map.get(k)
    )

    return DiffResult(
        base_path=base.path,
        target_path=target.path,
        missing_in_target=missing,
        extra_in_target=extra,
        empty_in_target=empty_target,
        empty_in_base=empty_base,
    )


@dataclass
class MultiDiffResult:
    template_path: str
    results: dict[str, DiffResult] = field(default_factory=dict)  # env_path -> DiffResult

    @property
    def has_issues(self) -> bool:
        return any(r.has_issues for r in self.results.values())

    def all_missing(self) -> dict[str, list[str]]:
        """Return {env_path: [missing_keys]} for envs that have missing keys."""
        return {p: r.missing_in_target for p, r in self.results.items() if r.missing_in_target}


def multi_diff(template: ParsedEnv, envs: list[ParsedEnv]) -> MultiDiffResult:
    """Compare a template against multiple environment files."""
    result = MultiDiffResult(template_path=template.path)
    for env in envs:
        result.results[env.path] = diff(template, env)
    return result
