# OrbVis end-to-end tests

A small Playwright smoke suite that drives a real browser against a
running OrbVis stack.

## One-time setup

```bash
cd frontend
npm install                    # picks up @playwright/test
npm run e2e:install            # downloads the Chromium binary
```

## Running locally

The tests assume a running OrbVis backend (default `:8000`) and a
running frontend dev server (default `:5173`). Start them in two
terminals:

```bash
# terminal 1
cd backend && uvicorn app.main:app --reload

# terminal 2
cd frontend && npm run dev
```

Then in a third terminal:

```bash
cd frontend
npm run e2e        # headless
npm run e2e:ui     # interactive runner
```

The default credentials are `admin` / `admin`. Override with
`E2E_ADMIN_USER` / `E2E_ADMIN_PASSWORD` if your install differs.

To run against a deployed instance, set `E2E_BASE_URL`:

```bash
E2E_BASE_URL=https://orbvis.example.com npm run e2e
```

## Coverage today

The current suite is intentionally minimal: it validates that login
works, that boards exist, and that opening a board renders a canvas.
Treat it as a "did the deployment break in any obvious way" check.

Adding tests for editor flows, hover / context menus, WebSocket state
updates, and admin pages is on the roadmap — see `ROADMAP.md`.
