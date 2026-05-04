# OrbVis frontend

Vue 3 + TypeScript + Vite + Pinia + Tailwind CSS + D3 + Leaflet.

## Quickstart (development)

Requirements: Node.js 20+.

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies `/api/*` to
the backend on `http://localhost:8080` (set in `vite.config.ts`).

Run the backend separately — see [`../backend/README.md`](../backend/README.md).

## Common commands

```bash
npm run dev          # dev server with HMR
npm run build        # production build (dist/)
npm run preview      # serve the built output
npm test             # vitest in watch mode
npm run test:coverage  # coverage report (gate enforced)
npm run type-check   # vue-tsc, no emit
npm run lint         # eslint + stylelint
npm run format       # prettier write
```

## Layout

```
src/
  api/                client.ts (typed fetch wrapper, refresh-token rotation)
  components/         shared UI components
  components/map/     MapCanvas, MapObject, MapLine, HoverMenu, ContextMenu, …
  composables/        useTheme, useToast, useKeyboardShortcuts, …
  i18n/               translations
  router/             Vue Router (hash mode for reverse-proxy compat)
  stores/             Pinia: auth, maps, states (WebSocket), backends, …
  types/              shared types, API types mirror Pydantic schemas
  utils/              naming, perf, stateColors, sanitize, template
  views/              top-level routes (Login, Home, MapView, Admin/*)
  vendor/             vendored CMK components / assets (do not edit by hand)
```

## End-to-end tests

A small Playwright smoke suite lives in `e2e/`. See
[`e2e/README.md`](e2e/README.md) for one-time setup and how to run it.

## Building for an OMD install

```bash
VITE_BASE_PATH=./ npm run build -- --base='./'
```

Relative base paths let the same bundle work behind any
`/<site>/orbvis/` URL. The MKP build script (`make_mkp.sh`) does this
for you.

## CMK vendored components

`src/vendor/cmk/` contains components and styles vendored from the
Checkmk frontend, used to keep the OrbVis UI visually aligned with
Checkmk. Stubs in `src/components/cmk-stubs/` replace components that
have unbundleable dependencies (icons, multitone-icons). The Vite
plugin in `vite.config.ts` redirects imports automatically.

When updating from Checkmk, copy verbatim — do not edit the vendored
files. If a vendored file needs a tweak, leave the original alone and
override via a stub.

## See also

- [Architecture overview](../docs/architecture.md)
- [Frontend coverage plan](../docs/frontend-coverage-plan.md)
- [Contributing](../CONTRIBUTING.md)
