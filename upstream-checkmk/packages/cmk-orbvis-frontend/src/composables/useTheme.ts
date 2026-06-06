import { type Ref, ref, watch } from 'vue'

import { useAuthStore } from '@/stores/auth'

export function applyTheme(theme: string, _ssoActive: boolean, cmkTheme?: string | null) {
  let dark: boolean
  if (theme === 'dark') {
    dark = true
  } else if (theme === 'light') {
    dark = false
  } else {
    // 'system': follow CMK theme (from ui_theme.mk via backend) or default to dark.
    dark = cmkTheme !== 'light'
  }

  const root = document.documentElement
  if (dark) {
    root.classList.remove('light')
    root.classList.add('dark')
    document.body.dataset.theme = 'modern-dark'
  } else {
    root.classList.remove('dark')
    root.classList.add('light')
    document.body.dataset.theme = 'facelift'
  }
}

// Reactive dark-mode flag tracking the `dark` class applyTheme() toggles on
// <html> — for components that re-render canvas/chart colors on theme switch.
// Module-level singleton: boards render one BoardObject per object, so a
// per-instance observer would multiply by the object count for a global flag.
let _isDark: Ref<boolean> | null = null

export function useIsDark(): Readonly<Ref<boolean>> {
  if (_isDark === null) {
    const isDark = ref(document.documentElement.classList.contains('dark'))
    new MutationObserver(() => {
      isDark.value = document.documentElement.classList.contains('dark')
    }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    _isDark = isDark
  }
  return _isDark
}

export function useTheme() {
  const auth = useAuthStore()

  // Watch both theme and ssoActive so we re-apply whenever either changes.
  // Skip the very first fire if auth hasn't resolved yet (user still null and
  // ssoActive still false) — the index.html dark class already covers that gap.
  watch(
    () => [auth.user?.theme, auth.user?.cmk_theme, auth.ssoActive] as const,
    ([theme]) => {
      if (auth.user === null && !auth.ssoActive) return
      applyTheme(theme ?? 'system', auth.ssoActive, auth.user?.cmk_theme)
    },
    { immediate: true }
  )
}
