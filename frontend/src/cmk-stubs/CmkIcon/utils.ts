/**
 * OrbVis-specific implementation of cmk-frontend-vue's
 * ``components/CmkIcon/utils.ts``.
 *
 * Returns a runtime URL pointing at the sibling Checkmk site's
 * ``/check_mk/themes/...`` tree, so the bundle stays free of binary
 * asset deps. Wired in via ``CMK_STUBS`` in ``frontend/vite.config.ts``
 * — vendored CmkIcon.vue picks this up instead of editing the file.
 */
import type { IconNames } from 'cmk-shared-typing/typescript/icon'

import copiedIconUrl from './icon_copied.svg'
import { iconSizes, themedIcons, unthemedIcons } from './icons.constants'

// Icons that older Checkmk themes don't ship (icon_copied.svg only exists
// from 2.5 on) are bundled so they render on every supported version.
const bundledIcons: Partial<Record<IconNames, string>> = {
  copied: copiedIconUrl
}

type IconSizeNames = keyof typeof iconSizes
type SimpleIcons = IconNames

export function iconSizeNametoNumber(sizeName: IconSizeNames | undefined) {
  return sizeName === undefined ? iconSizes['medium'] : iconSizes[sizeName]
}

// Builds an absolute "/<site>/check_mk/" prefix at runtime. Example:
//   page at /ZWEIFUENF/orbvis/#/boards/foo → '/ZWEIFUENF/check_mk/'
// We deliberately read window.location.pathname (not import.meta.env.BASE_URL)
// because the bundle is built with `base: './'` so it can be served from any
// OMD-site prefix without rebuilding. With a relative BASE_URL the icon path
// would otherwise resolve against the current SPA route (e.g. /<site>/orbvis/
// rather than /<site>/check_mk/) and 404.
//
// Falls back to '/check_mk/' when no '/orbvis/' segment is detected — that
// path resolves wherever OrbVis is co-deployed with a Checkmk site under the
// document root, which matches the current rollout.
function checkmkBase(): string {
  if (typeof window === 'undefined') return '/check_mk/'
  const pathname = window.location.pathname
  const orbvisIdx = pathname.indexOf('/orbvis/')
  if (orbvisIdx >= 0) return `${pathname.slice(0, orbvisIdx)}/check_mk/`
  return '/check_mk/'
}

export function getIconPath(name: SimpleIcons, theme: string): string {
  const bundled = bundledIcons[name]
  if (bundled) {
    return bundled
  }

  const internalTheme = theme === 'facelift' ? 'light' : 'dark'

  const themedPath = themedIcons[internalTheme]?.[name]
  if (themedPath) {
    return `${checkmkBase()}${themedPath}`
  }

  const unthemedPath = unthemedIcons[name]
  if (!unthemedPath) {
    return ''
  }
  return `${checkmkBase()}${unthemedPath}`
}
