# cmk-orbvis-frontend (skeleton)

Vue 3 + TypeScript bundle for the built-in OrbVis GUI, modelled after
`~/git/checkmk/packages/cmk-frontend-vue/`. Populated in Stage 6.

## Planned layout (mirrors cmk-frontend-vue)

- `package.json` — Node 22+, Vite 7, Vitest 4, identical devDependencies
  to cmk-frontend-vue so both packages share lockable versions.
- `BUILD.bazel` — `npm_link_all_packages`, `vue_library`, `pkg_tar` for the
  wheel; copied from cmk-frontend-vue and adjusted for OrbVis sources.
- `vite.config.ts`, `eslint.config.mjs`, `prettier.config.cjs`,
  `tsconfig.*.json` — shapes identical to cmk-frontend-vue.
- `src/` — ported from the external `frontend/src/` tree with:
  - Tailwind either kept (pending legal/design clarification) or replaced
    with CMK SCSS tokens.
  - Backend URL configurable via the OMD site or a CMK-side settings form.
- `tests/` — Vitest suites covering utils, stores, key components.
