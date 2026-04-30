# Frontend test coverage — incremental plan

This is the working plan for raising frontend test coverage from the
current baseline (~7 % lines) to a more confident level. Each row is a
separate, mergeable PR.

## Baseline (today)

- Existing Vitest suites:
  - `src/utils/naming.test.ts`
  - `src/utils/perf.test.ts`
  - `src/utils/stateColors.test.ts`
  - `src/locales/locales.test.ts`
  - `src/stores/connections.test.ts`
  - `src/stores/settings.test.ts`
  - `src/stores/auth.test.ts`
  - `src/stores/boards.test.ts`
  - `src/api/client.test.ts`
  - `src/router/router.test.ts`
- Coverage gate (vite.config.ts → `test.coverage.thresholds`):
  - lines 7, functions 4, branches 3, statements 7

## Step 1 — bump the floor

Verify current coverage and lift the gate to where we already are.

```bash
cd frontend
npm run test:coverage
# inspect coverage/index.html — adjust thresholds in vite.config.ts to
# the actual numbers minus 1 percentage point so a green CI doesn't break
# from minor variance.
```

Goal: gate matches reality ±1 pp. No new tests needed for this PR.

## Step 2 — composables and utils

Targets (all pure-ish, easy to test):

- `src/composables/useTheme.ts`
- `src/composables/useToast.ts`
- `src/composables/useKeyboardShortcuts.ts`
- `src/utils/colors.ts`
- `src/utils/sanitize.ts`
- `src/utils/template.ts`
- Anything in `src/utils/` not yet covered

Expected coverage delta: +5 to +10 pp lines.

## Step 3 — the remaining stores

- `src/stores/states.ts` — WebSocket connection logic, reconnect
  behaviour, state merge. **Highest priority**: this is where bugs hide.
  Mock `WebSocket` as in `connections.test.ts`.
- `src/stores/permissions.ts`
- `src/stores/users.ts`
- `src/stores/roles.ts`

Expected coverage delta: +5 pp lines.

## Step 4 — leaf components

Components without children, easy to mount in jsdom:

- `src/components/StateBadge.vue`
- `src/components/AckBadge.vue`
- `src/components/DowntimeBadge.vue`
- `src/components/HoverMenu.vue` — verify template rendering with
  fixture state objects
- `src/components/ContextMenu.vue`

Use `@vue/test-utils` (already a dev dep). Snapshot tests are fine for
purely-presentational components; unit tests for any prop-conditional
logic.

Expected coverage delta: +5 pp lines.

## Step 5 — board renderers (the hard ones)

These touch SVG and D3 and are the riskiest:

- `src/components/map/MapCanvas.vue`
- `src/components/map/MapObject.vue`
- `src/components/map/MapLine.vue`
- `src/components/map/WorldMapCanvas.vue`

Approach:

1. Start with a fixture-based render test (mount with a known board JSON
   and assert the resulting SVG element count).
2. Add interaction tests once the render baseline is stable.

Skip force-simulation timing — that's better covered by the Playwright
E2E suite.

Expected coverage delta: +10 pp lines.

## Targets by milestone

| After step | Lines | Functions | Branches | Statements |
|------------|-------|-----------|----------|------------|
| 1          | 7     | 4         | 3        | 7          |
| 2          | 15    | 12        | 8        | 15         |
| 3          | 20    | 16        | 12       | 20         |
| 4          | 25    | 20        | 15       | 25         |
| 5          | 30    | 25        | 20       | 30         |

Any PR that bumps thresholds **must** also raise `vite.config.ts` so the
gate moves with reality. Partial coverage that depends on later PRs
not happening is worthless.

## Coverage-resistant code

Some code is intentionally excluded from coverage (vite.config.ts):

- `src/main.ts` — bootstrap, not testable in isolation
- `src/vendor/**` — third-party CMK stubs
- `src/cmk-stubs/**`
- `src/test-setup.ts`

Do not add to this list lightly. If a file is genuinely impossible to
test, document why in a comment alongside the entry.
