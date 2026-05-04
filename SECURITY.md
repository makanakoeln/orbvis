# Security Policy

## Supported Versions

OrbVis is in early release. Security fixes are provided for the latest
released version on the `main` branch.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

**Please do not report security issues through public GitHub issues.**

Use GitHub's private vulnerability reporting feature:

1. Go to the [Security tab](https://github.com/makanakoeln/orbvis/security) of
   this repository.
2. Click *Report a vulnerability*.
3. Provide a clear description, reproduction steps, affected version, and
   impact.

Alternatively, send an encrypted email to the maintainer at
**ronny.bruska@gmail.com** with the subject prefix `[orbvis-security]`.

## What to Expect

| Stage                      | Target time          |
| -------------------------- | -------------------- |
| Acknowledgement of report  | within 3 business days |
| Initial assessment         | within 7 business days |
| Fix or mitigation timeline | shared within 14 days  |
| Public disclosure          | coordinated with reporter |

OrbVis is maintained on a best-effort basis; we cannot guarantee 24/7
response, but we take security reports seriously and will keep you
informed of progress.

## Disclosure Policy

We follow coordinated disclosure:

- We work with the reporter to confirm and fix the issue.
- A security advisory and patched release are published together.
- Credit is given in the advisory unless the reporter requests otherwise.

## Scope

In scope:

- The OrbVis backend (`backend/`), FastAPI endpoints, WebSocket protocol,
  authentication, RBAC, image upload, NagVis import tool.
- The OrbVis frontend (`frontend/`), Vue components, board rendering,
  state handling.
- The Checkmk MKP installer (`make_mkp.sh`, `orbvis-setup`), OMD-site
  integration, Apache proxy configuration.

Out of scope:

- Vulnerabilities in upstream dependencies (please report to the upstream
  project; we will pick up fixes via dependency updates).
- Issues that require an already-compromised admin account.
- Self-XSS or social engineering attacks against single users.

## Hardening Already in Place

For context, the following hardening is implemented and tested:

- JWT access + refresh token rotation with per-process blocklist
- bcrypt password hashing (with htpasswd-compatible verification for
  Checkmk SSO)
- Login throttling (5 attempts / 15 min / IP) with constant-time dummy
  verification to prevent username enumeration
- CSRF protection on state-changing endpoints
- SSRF prevention on backend URLs, image uploads, and board URL fields
  (rejects `javascript:`, `file:`, `data:`, metadata IPs, path traversal)
- SVG upload sanitisation via `defusedxml` (rejects DTDs, scripts,
  `foreignObject`, `on*` attributes, `javascript:` / `data:` hrefs)
- WebSocket origin checks, auth-on-connect, rate limiting
- Secret redaction in API responses and logs
- `pip-audit`, `bandit`, `gitleaks` in CI

See `backend/tests/test_security_hardening.py`, `test_csrf.py`,
`test_websocket.py` for the current test coverage.
