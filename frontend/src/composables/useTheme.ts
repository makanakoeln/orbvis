import { watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

function getCmkThemeCookie(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)theme=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

export function applyTheme(theme: string, ssoActive: boolean) {
  let dark: boolean
  if (theme === 'dark') {
    dark = true
  } else if (theme === 'light') {
    dark = false
  } else {
    // 'system': in SSO mode try CMK cookie first, fall back to OS preference
    if (ssoActive) {
      const cmk = getCmkThemeCookie()
      // No cookie = user never changed from CMK default (modern-dark) → dark
      dark = cmk !== null ? cmk === 'modern-dark' : true
    } else {
      dark = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
  }

  const root = document.documentElement
  if (dark) {
    root.classList.remove('light')
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
    root.classList.add('light')
  }
}

export function useTheme() {
  const auth = useAuthStore()

  watch(
    () => auth.user?.theme,
    (theme) => {
      applyTheme(theme ?? 'system', auth.ssoActive)
    },
    { immediate: true },
  )
}
