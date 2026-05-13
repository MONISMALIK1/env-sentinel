# env-sentinel 🛡️

> Catch environment variable drift, format errors, and secret leaks before they reach production.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**env-sentinel** is a zero-infrastructure CLI that compares your `.env` files across environments, validates value formats, and detects accidentally committed secrets — all in one command.

---

## The Problem

You push to production and get paged at 2 AM because:
- A new `PAYMENT_WEBHOOK_SECRET` key was added to `.env.example` 3 weeks ago, but nobody updated `.env.production`
- `DATABASE_URL` in staging points to a local dev database
- Someone committed an actual OpenAI key to the repo

These bugs are invisible until they explode. **env-sentinel** makes them visible in your CI pipeline.

---

## Install

```bash
pip install env-sentinel
```

---

## Commands

### `diff` — Compare two env files

```bash
# Find keys missing in production that exist in your template
env-sentinel diff .env.example .env.production

# Also scan for secrets in the target file
env-sentinel diff .env.example .env.production --scan-secrets
```

Output:
```
⚠ Diff: .env.example → .env.production
  Missing in target (2):
    • PAYMENT_WEBHOOK_SECRET
    • SENTRY_DSN

  Empty in target (1):
    • REDIS_URL
```

### `audit` — Check multiple environments at once

```bash
env-sentinel audit \
  --template .env.example \
  --check .env.staging \
  --check .env.production \
  --scan-secrets
```

### `validate` — Format-check values by key name

```bash
env-sentinel validate .env.production
```

Automatically infers expected types from key names:
- `*_PORT` → integer 1-65535
- `*_URL` → valid URL
- `DATABASE_URL` → database connection string
- `*_EMAIL` → email address
- `*_ENABLED` / `*_DEBUG` → boolean
- `*_TIMEOUT` → integer

### `scan` — Detect secrets and API keys

```bash
env-sentinel scan .env.production

# Fail on medium severity too (default: only high)
env-sentinel scan .env.production --fail-on-medium
```

Detects:
| Pattern | Severity |
|---------|----------|
| OpenAI keys (`sk-...`) | 🔴 high |
| AWS access keys (`AKIA...`) | 🔴 high |
| GitHub tokens (`ghp_...`) | 🔴 high |
| Stripe live keys (`sk_live_...`) | 🔴 high |
| JWTs (`eyJ...`) | 🔴 high |
| SendGrid / Twilio / Slack / Google keys | 🔴 high |
| Stripe test keys (`sk_test_...`) | 🟡 medium |
| High-entropy strings on sensitive keys | 🟡 medium |

### `check` — Run everything at once

```bash
env-sentinel check \
  --template .env.example \
  --check .env.staging \
  --check .env.production
```

---

## GitHub Actions

Drop this into `.github/workflows/env-check.yml`:

```yaml
- name: Check env files
  run: |
    pip install env-sentinel
    env-sentinel check \
      --template .env.example \
      --check .env.staging \
      --check .env.production
```

When run inside GitHub Actions, env-sentinel automatically emits `::error::` and `::warning::` annotations that appear inline in your pull request diff.

---

## JSON Reports

Every command accepts `--json-report <file>`:

```bash
env-sentinel audit \
  --template .env.example \
  --check .env.staging \
  --json-report report.json
```

```json
{
  "generated_at": "2026-05-13T10:00:00Z",
  "summary": { "total_issues": 3, "secret_findings": 0 },
  "diffs": [...],
  "validation_errors": [...],
  "secret_findings": []
}
```

---

## How it works

1. **Parser** — handles quotes, inline comments, `export` prefix, multiline values
2. **Differ** — compares key sets: missing, extra, and empty values
3. **Validator** — infers expected type from key name, validates format
4. **Scanner** — regex patterns + Shannon entropy for high-entropy strings on sensitive keys

All pure Python. No external services. No network calls. Works offline.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | Issues found (missing keys, format errors, high-severity secrets) |

---

## License

MIT — see [LICENSE](LICENSE).
