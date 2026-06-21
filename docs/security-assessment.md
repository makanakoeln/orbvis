# OrbVis Security Assessment (AppSec review prep)

**Purpose.** This document prepares the security review that gates moving OrbVis
into the Checkmk repository as an in-tree package (target 3.0). It captures the
current scan baseline, the dependency surface relative to what Checkmk already
ships, and a control-by-control map of the implemented hardening with the test
that exercises it. It is a starting point for AppSec — not a substitute for an
independent assessment.

Snapshot: OrbVis `0.6.0` (`main`). Re-run the scans in
[§1](#1-scan-baseline) to refresh before each review.

---

## 1. Scan baseline

All gating scans are clean on the current tree. They run in CI
(`.github/workflows/backend.yml`, `frontend.yml`, `pre-commit.yml`).

| Scan | Scope | Command | Result |
| --- | --- | --- | --- |
| **bandit** | backend Python, medium+ | `bandit -r app/ -x tests/ -ll` | **0 issues** (16.6k LOC) |
| **pip-audit** | backend deps | `pip-audit .` | **0 known vulnerabilities** |
| **npm audit** | frontend deps, high+ | `npm audit --audit-level=high` | **0 vulnerabilities** |
| **gitleaks** | full repo history | pre-commit / CI | clean (enforced per commit) |

### Accepted low-severity bandit findings

`bandit` at its default (low+) reports 27 low-severity, mostly false-positive
items. The CI gate is `-ll` (medium+) and is clean; these are documented here
for completeness:

| Rule | Count | Where / why it's safe |
| --- | --- | --- |
| `B101` assert | 16 | Invariant asserts in non-test code paths; not security logic. |
| `B110/B112` try/except pass/continue | 9 | Best-effort cleanup and resilient parse loops (e.g. skip a malformed row). |
| `B311` non-crypto random | 1 | `connections/livestatus.py` — retry **jitter** only, never for secrets. |
| `B105` hardcoded password string | 1 | `schemas/connection.py:75` — the literal is a field **name** (`"password"`), not a secret. |

Tokens and secrets are generated with `secrets`/`uuid4` (see
`core/security.py`), never `random`.

---

## 2. Dependency surface

### 2.1 Backend (Python runtime)

OrbVis ships **seven** runtime dependencies. Checkmk's `requirements.txt`
(master) already pins **every one** of them at a version that meets or exceeds
OrbVis's floor — so the in-tree (3.0) target introduces **zero new Python
runtime dependencies**.

| Dependency | OrbVis floor | Checkmk master | In-tree status |
| --- | --- | --- | --- |
| `fastapi` | `>=0.115.0, !=0.136.3` | `0.129.0` | ✅ covered (and the malicious `0.136.3` / MAL-2026-4750 is excluded) |
| `uvicorn` | `>=0.32.0` | `0.48.0` | ✅ covered |
| `pydantic` | `>=2.10.0` | `2.12.5` | ✅ covered |
| `bcrypt` | `>=4.0.0` | `5.0.0` | ✅ covered |
| `python-multipart` | `>=0.0.28` | `0.0.30` | ✅ covered (above the CVE-2026-40347 / -42561 floor) |
| `httpx` | `>=0.28.0` | `0.28.1` | ✅ covered |
| `defusedxml` | `>=0.7.1` | `0.7.1` | ✅ covered |

**Deliberately *not* taken on** (replaced by stdlib to keep the surface small):
SQLAlchemy / Alembic / Mako / aiosqlite → `sqlite3` + `core/schema.sql`; PyJWT →
`core/_jwt.py`; pydantic-settings → `core/_env.py`; `websockets` → SSE.

**MKP wheelhouse (standalone / 2.3–2.6 only).** The MKP build bundles
`python-multipart` (and, for 2.3, `httpx`) because those OMD releases ship
versions below OrbVis's CVE floor. This wheelhouse is **not needed for the
in-tree target**, where the repo-pinned versions above apply. See
`backend/requirements-bundle*.txt`.

### 2.2 Frontend (build-time, bundled)

Frontend dependencies are bundled into a static SPA at build time — nothing is
installed on the server at runtime. All production dependencies carry permissive
OSI licenses, and `npm audit` is clean.

| Dependency | License | Role |
| --- | --- | --- |
| `vue`, `vue-router`, `pinia` | MIT | SPA framework (same stack as `cmk-frontend-vue`) |
| `d3` | ISC | flow/radar/aggregation geometry |
| `echarts`, `vue-echarts` | Apache-2.0 | metric charts |
| `leaflet`, `@vue-leaflet/vue-leaflet` | BSD-2-Clause / MIT | geo board map |
| `sanitize-html` | MIT | template/HTML XSS sanitisation (see §3) |
| `reka-ui` | MIT | headless UI primitives |
| `vue3-gettext` | MIT | i18n (Checkmk-aligned) |
| `class-variance-authority` | Apache-2.0 | style composition |

No copyleft or non-OSI licenses are present.

### 2.3 SBOMs

CycloneDX SBOMs are produced on demand (not committed) via
`scripts/generate-sboms.sh` → `sbom-backend.cdx.json`, `sbom-frontend.cdx.json`.
Generate fresh artifacts for the review.

---

## 3. Security controls

Each control names the implementing module and the test that exercises it, so a
reviewer can jump straight from a requirement to the code and its proof.

| Area | Control | Implementation | Test |
| --- | --- | --- | --- |
| **AuthN** | JWT access + refresh, in-house HS256 (alg-confusion / `alg:none` rejected) | `core/_jwt.py`, `core/security.py` | `test_jwt.py` |
| | Stream tickets — short-lived (5 min) URL auth for SSE/tiles instead of access tokens in the URL | `core/security.py` `create_stream_ticket` | `test_security.py` |
| | Logout blocklist (per-process; see §4) | `core/security.py` `blocklist_token` | `test_security.py` |
| | bcrypt hashing + htpasswd-compatible verify | `core/security.py`, `services/auth_service.py` | `test_auth_service.py` |
| | Checkmk SSO via OMD cookie HMAC, 2FA-aware (rejects pre-2FA sessions) | `services/auth_service.py` | `test_auth_service.py` |
| | Login throttle (5 / 15 min / IP) + constant-time dummy (anti-enumeration) | `core/ratelimit.py`, `api/v1/auth.py` | `test_auth.py` |
| **AuthZ** | RBAC (mod/act/obj) + Checkmk command-permission gating | `api/v1/deps.py`, `api/v1/connections.py` | `test_permission_gates.py` |
| | Livestatus queries scoped to the caller's contact groups (`AuthUser`) | `connections/livestatus.py` | `test_folder_site_trust.py` |
| | SETUP folder skeleton scoped to folder-read permission | `connections/livestatus.py`, `integrations/checkmk.py` | `test_folder_scope.py` |
| **Input / injection** | LQL newline-injection stripping on every filter value | `connections/livestatus.py` `_ls_escape` | `test_livestatus_parsers.py` |
| | Board-name path-traversal guard (read/delete/import) | `services/board_service.py` `_board_path` | `test_board_service.py` |
| | XML/SVG: `defusedxml`, no DTD/entities/`script`/`foreignObject`/`on*` | `core/image_security.py` | `test_security_hardening.py` |
| | Image upload magic-byte validation | `core/image_security.py` | `test_security_hardening.py` |
| **SSRF** | Backend/board URL allowlist (rejects `javascript:`/`file:`/`data:`, metadata IPs, traversal) | `schemas/connection.py`, `schemas/_validators.py` | `test_security_hardening.py` |
| **XSS** | Template HTML sanitised against a tag/attr allowlist (no `url()`, no event handlers) | `frontend/src/utils/sanitize.ts`; mirror `schemas/_validators.py` | `sanitize.test.ts`, `template.test.ts` |
| | Outbound URL scheme allowlist (control-char bypass closed) | `frontend/src/utils/boardNavigation.ts` | `boardNavigation.test.ts` |
| **CSRF** | Origin check on cookie-authed state-changing requests; bearer/body exempt | `core/middleware.py` `CSRFOriginMiddleware` | `test_csrf.py`, `test_middleware.py` |
| **Secrets** | Connection secrets redacted in API responses and logs (`_redact` / `REDACTED_SECRET`) | `schemas/connection.py` | `test_security_hardening.py` |
| **Transport** | Security headers (nosniff, frame-options, referrer-policy); TLS for TCP Livestatus | `core/middleware.py`, `connections/livestatus.py` | `test_security_hardening.py` |

---

## 4. Open questions for AppSec

- **JWT blocklist is per-process.** A logout on one uvicorn worker leaves the
  token usable on the others until expiry (documented in `core/security.py`).
  In-tree, decide whether to move it to a shared store or rely on short access
  TTLs + refresh rotation.
- **Auth model in-tree.** The in-tree target drops standalone operation and runs
  auth through Checkmk SSO/htpasswd + Checkmk RBAC; the native OrbVis DB-auth /
  local-admin path is slated for removal. AppSec should review the *target*
  (CMK-only) auth surface, not the standalone DB-auth path.
- **`graph` object embeds an iframe.** Imported NagVis containers and graph
  objects render a sandboxed iframe; confirm the sandbox/`allow-*` posture and
  the `graph_url` allowlist meet Checkmk's embedding policy.
- **Tile proxy.** The geo board proxies OSM tiles with a disk cache; confirm the
  cache bounds and the upstream-host allowlist.

---

## 5. How to reproduce the baseline

```bash
# Backend
cd backend
.venv/bin/bandit -r app/ -x tests/ -ll
.venv/bin/pip-audit .
.venv/bin/pytest            # incl. the security suites listed in §3

# Frontend
cd frontend
npm audit --audit-level=high
npm run test:coverage

# SBOMs
./scripts/generate-sboms.sh
```
