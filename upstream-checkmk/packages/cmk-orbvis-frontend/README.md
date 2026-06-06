# cmk-orbvis-frontend

Vue 3 + TypeScript bundle for the built-in OrbVis GUI, modelled after
`packages/cmk-frontend-vue`. Unlike the external `frontend/` tree this
package compiles against the REAL cmk-frontend-vue sources (sibling
workspace package) — the vendor tree, the standalone component
overrides and all cmk-stubs from the external repo do not exist here.

## Layout

- `src/` — synced from the external `frontend/src/` by
  `scripts/sync-upstream-frontend.sh` (OrbVis repo). Do not edit here;
  edit `frontend/src/` and re-sync. The script rewrites
  `@/vendor/cmk/...` imports to `@cmk/...` and verifies every one of
  them resolves against the real cmk-frontend-vue tree.
- `src/cmk-additions/` — OrbVis-owned files that originated in the
  vendor tree: the custom FormSpec widgets (`FormOrbColor`,
  `FormOrbHostAutocomplete`), the dispatcher that registers them, and
  two upstream-orphans (`CmkDialog.vue`, `lib/rest-api-client/
  userConfig.ts`) that master removed after OrbVis vendored them.
  Candidates for upstreaming into cmk-frontend-vue at merge time.
- `locale/de.po` — translation source of truth; `src/assets/locale/`
  is generated from it (`npm run i18n:compile`, Bazel `:compile_i18n`).
- `BUILD` — real target shape (vite `:dist`, `pkg_files` →
  `share/check_mk/web/htdocs/cmk-orbvis-frontend`, `pkg_tar` for
  `//omd`). Only buildable inside the checkmk monorepo.

## Aliases

| Alias           | Target                      |
|-----------------|-----------------------------|
| `@`             | `./src`                     |
| `@cmk`          | `../cmk-frontend-vue/src`   |
| `~cmk-frontend` | `../cmk-frontend/dist`      |

## Deployment model (Stage 6c)

The SPA ships as static files in the version tree
(`share/check_mk/web/htdocs/cmk-orbvis-frontend/`, via `pkg_tar` like
cmk-frontend-vue — NOT as a wheel; wheels are for Python packages).
The per-site Apache reverse-proxy config written by the OrbVis backend
setup serves `index.html` at `/<site>/orbvis/` and proxies `/api` to
the site-local backend daemon, exactly like the NagVis model. The
sidebar snapin (`cmk/gui/orbvis/_orbvis_maps.py`) links to that URL.

## Merge-time wiring checklist

1. Add `packages/cmk-orbvis-frontend` to `pnpm-workspace.yaml`.
2. `pnpm install` (extends pnpm-lock.yaml with the package-local deps:
   pinia, echarts/vue-echarts, leaflet/@vue-leaflet, d3).
3. Add `//packages/cmk-orbvis-frontend` to `omd/BUILD`
   (`deps_packages_base`).
4. Decide upstreaming vs. keeping `src/cmk-additions/` (FormOrb*
   widgets could become regular cmk-frontend-vue form components).
5. Icon pipeline: the builtin board icons are copied from
   `@tabler/icons` by the OrbVis backend build; revisit once the
   backend packaging (Stage 6d) is designed.

## Verification (without Bazel)

Mirrors the Stage-6a ritual — copy this directory to
`~/git/checkmk/packages/cmk-orbvis-frontend`, register it in
`pnpm-workspace.yaml`, then:

```bash
pnpm install --filter cmk-orbvis-frontend...
cd packages/cmk-orbvis-frontend
pnpm exec vue-tsc -p tsconfig.json
pnpm run i18n:compile && pnpm exec vite build
pnpm exec vitest run
```
