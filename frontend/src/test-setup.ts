import '@testing-library/jest-dom/vitest'
import { config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'
import failOnConsole from 'vitest-fail-on-console'
import { createRouter, createWebHashHistory } from 'vue-router'

// Dummy translator mirroring vendor/cmk/lib/i18n: passes the message through and
// fills %{key} placeholders so component assertions see interpolated text without
// loading the real gettext catalogs.
function interpolate(msg: string, values?: Record<string, unknown>): string {
  if (!values) return msg
  return msg.replace(/%\{(\w+)\}/g, (_, k: string) => String(values[k] ?? `%{${k}}`))
}
const dummyT = (msg: string, values?: Record<string, unknown>) => interpolate(msg, values)
const dummyTn = (
  singular: string,
  plural: string,
  count: number,
  values?: Record<string, unknown>
) => interpolate(count === 1 ? singular : plural, values)
const dummyTp = (_ctx: string, msg: string, values?: Record<string, unknown>) =>
  interpolate(msg, values)
const dummyTnp = (
  _ctx: string,
  singular: string,
  plural: string,
  count: number,
  values?: Record<string, unknown>
) => interpolate(count === 1 ? singular : plural, values)

vi.mock('@/vendor/cmk/lib/i18n', () => ({
  default: () => ({ _t: dummyT, _tn: dummyTn, _tp: dummyTp, _tnp: dummyTnp }),
  untranslated: (msg: string) => msg,
  createi18n: () => ({ _t: dummyT, _tn: dummyTn, _tp: dummyTp, _tnp: dummyTnp })
}))

// jsdom has no layout engine; stub scrolling so components that call it don't throw.
window.HTMLElement.prototype.scrollIntoView = function () {}

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{ path: '/', component: {} }]
})

// Set an active pinia rather than registering it as a global plugin: stores
// resolve through getActivePinia() so tests that don't mount (or don't pass
// their own pinia) still work, while tests that DO pass `plugins: [pinia]` no
// longer double-install it (which Vue warns about — and failOnConsole fails on).
setActivePinia(createPinia())

config.global.plugins = [router]
config.global.stubs = {
  RouterLink: true,
  RouterView: true
}

// Treat stray console output as a test failure — mirrors cmk-frontend-vue's
// setup so noisy components surface in review instead of passing silently.
failOnConsole({
  shouldFailOnAssert: true,
  shouldFailOnDebug: true,
  shouldFailOnInfo: true,
  shouldFailOnLog: true,
  shouldFailOnWarn: true,
  shouldFailOnError: true
})
