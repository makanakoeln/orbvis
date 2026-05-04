# Contributing to OrbVis

Thanks for your interest in OrbVis. This is a community-driven project that
aims to be a modern successor to NagVis. Contributions of all sizes are
welcome — bug reports, doc fixes, refactors, new features.

## Ground rules

- Be respectful. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Open an issue **before** starting non-trivial work, so we can align on
  scope and avoid duplicate effort.
- One logical change per pull request. Don't bundle unrelated fixes.
- All contributions are licensed under the project's GPL-2.0-only license.

## Development setup

See the [README](README.md#development) for a full backend + frontend
quickstart. Short version:

```bash
# Backend
cd backend
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

The frontend talks to the backend via a Vite proxy on `:5173 → :8000`.

## Code style

OrbVis follows the Checkmk code-style stack 1:1, since the long-term plan
is to ship as a built-in Checkmk package:

- **Python**: `ruff` + `mypy --strict`. Run `make fmt lint type` before
  committing. No `# type: ignore` without a verified reason; no `Any`.
- **TypeScript / Vue**: `eslint` + `prettier` + `stylelint`. Run
  `npm run lint` and `npm run typecheck`. No `any`, no `eslint-disable`
  unless unavoidable and justified in a comment.
- **Imports**: at the top of the file, never inside functions.

Pre-commit hooks enforce all of the above:

```bash
make install-hooks   # one-time
```

After that, `git commit` automatically runs the relevant checks.

## Tests

- **Backend**: `pytest` from `backend/`. New code should ship with tests;
  the CI gate is currently 45% line coverage but the bar is rising.
- **Frontend**: `npm test` from `frontend/` (Vitest). Coverage gate is
  intentionally low at this stage but will be raised over time.
- **Security-sensitive code**: add a test under
  `backend/tests/test_security_hardening.py` (or an analogous file)
  that documents the threat being defended against.

## Commit conventions

Subject line only, no body, no description, no `Co-Authored-By` lines.

```
<scope>: <what changed>
```

- English, imperative mood, lowercase after the colon
- Keep the subject ≤ 72 characters

Examples:

```
board: fix clone modal input sanitization
home: replace permissions button with settings gear
states: use #ffd000 for WARNING color
docs: add migration guide for NagVis users
```

## Pull requests

1. Fork the repo and branch from `main`. Branch names should be short
   and descriptive: `fix-clone-input-sanitization`, `add-radar-board-edit`.
2. Make your change. Keep the diff focused.
3. Run the full local checks:
   ```bash
   make precommit   # ruff + mypy + bandit + pip-audit + tests
   cd frontend && npm run lint && npm run typecheck && npm test
   ```
4. Open a PR using the template. Include:
   - What the change does and why
   - Manual test steps if UI is touched
   - Screenshots or short video for visual changes
5. CI must be green before review.

## Reporting bugs

Please use the bug-report issue template. Include OrbVis version, Checkmk
version (if applicable), browser, and exact steps to reproduce. Logs from
`journalctl -u orbvis` or the Docker container are very helpful.

## Reporting security issues

**Do not open a public issue for security problems.** See
[`SECURITY.md`](SECURITY.md) for the private reporting process.

## License & contribution agreement

OrbVis is GPL-2.0-only. By submitting a pull request you agree that your
contribution is licensed under GPL-2.0-only.

## Questions

If you're not sure where to start, open a *Question* issue or comment on
an existing one — happy to help you find a first task.
