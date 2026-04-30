# OrbVis Roadmap

A pragmatic, dated view of where OrbVis is going. Items further out are
less certain — please don't plan deployments around them. PRs and
issues are welcome at every stage.

This roadmap is reviewed roughly every quarter. The dates indicate
intent, not contractual commitments.

## Now (Q2 2026) — public beta

**Theme:** Make OrbVis usable for community testing.

- [x] Real-time WebSocket state push, multi-board support
- [x] Static / Flow / Radar / Geo board types with edit mode
- [x] Checkmk integration (sidebar snapin, menu entry, SSO, MKP packaging)
- [x] Security hardening (CSRF, SSRF, XSS, XXE, login throttling, JWT rotation)
- [x] CI: ruff + mypy strict, pip-audit, bandit, gitleaks, npm audit, vitest gate
- [x] NagVis import tool (`tools/cfg_importer.py`)
- [x] Public-release docs (install, migration, troubleshooting, comparison)
- [ ] Public demo instance the forum post can link to
- [ ] Demo video / GIF for the forum post
- [ ] Initial Playwright smoke suite running in CI

## Next (Q3 2026) — closing NagVis-parity gaps

**Theme:** "Drop-in replacement for the common case."

- [ ] LDAP authentication for standalone deployments
- [ ] Audit log (who edited what, when) — both API and UI
- [ ] Recognise more NagVis stock gadgets in the importer (header, table)
- [ ] Frontend test coverage to ≥ 25 % (see `docs/frontend-coverage-plan.md`)
- [ ] Extend Playwright suite: editor flow, hover/context menu, WS updates
- [ ] Redis-backed token blocklist (unblocks multi-worker deployments)
- [ ] Mobile-friendly editor (current state: editor is desktop-first)

## Later (Q4 2026 and onward)

**Theme:** Ecosystem and polish.

- [ ] OrbVis as a built-in Checkmk package starting with Checkmk 2.6
      (parallel to the standalone / MKP-Exchange paths, which stay)
      — work tracked in `upstream-checkmk/`
- [ ] Plugin / extension API: custom map sources, custom actions
- [ ] GraphQL or batched-REST endpoint for high-object-count boards
- [ ] OAuth / SAML for enterprise standalone deployments
- [ ] Native dark / light mode for the editor (currently mostly aligned)

## Maybes — open to community input

These are ideas without a champion yet. Comment on a corresponding
GitHub issue (or open one) if you'd like to drive any of them.

- Multi-tenant board namespaces with per-tenant RBAC
- Graph editor (manual layout assists for Flow boards beyond force-sim)
- HA / clustered deployment story (requires the multi-worker work above
  plus state sync)
- Programmatic board templates for repetitive layouts (rack views, etc.)

## How decisions get made

OrbVis is small and pragmatic. The shortlist for any quarter is driven
by:

1. **Existing-user pain** — anything blocking real installs takes priority.
2. **NagVis-parity gaps** — closing the *Missing* list in
   [`docs/comparison.md`](docs/comparison.md) is the second priority,
   because OrbVis only succeeds as a NagVis successor if it's actually
   a successor.
3. **Maintainer interest** — a lone maintainer ships what they can stand
   to work on. Items that get help from contributors move up.

If you have a feature you want OrbVis to grow into, the most useful
thing you can do is **open an issue with a concrete use case**, not a
generic "nice to have". Concrete use cases land in roadmaps.
