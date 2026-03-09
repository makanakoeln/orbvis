import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/client'
import type { UserRead } from '@/types/api'
import router from '@/router'
import type { RouteLocationRaw } from 'vue-router'
import { i18n } from '@/main'

const ACCESS_TOKEN_KEY = 'orbvis_access_token'
const REFRESH_TOKEN_KEY = 'orbvis_refresh_token'
const SSO_ACTIVE_KEY = 'orbvis_sso'

// Derive Checkmk logout URL from current path: /heute/orbvis/... → /heute/check_mk/logout.py
function _checkmkLogoutUrl(): string | null {
  const m = window.location.pathname.match(/^(\/[^/]+)\/orbvis/)
  return m ? `${m[1]}/check_mk/logout.py` : null
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const user = ref<UserRead | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  // true when logged in via Checkmk SSO
  const ssoActive = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)

  // Ensures initialization runs exactly once per SPA session and is awaitable
  let _initPromise: Promise<void> | null = null

  function init(): Promise<void> {
    if (!_initPromise) {
      _initPromise = _doInit()
    }
    return _initPromise
  }

  async function _doInit(): Promise<void> {
    // Try Checkmk SSO via session cookie (auth_<site>); only works when served through OMD Apache
    try {
      const tokens = await authApi.sso()
      accessToken.value = tokens.access_token
      refreshToken.value = tokens.refresh_token
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
      sessionStorage.setItem(SSO_ACTIVE_KEY, '1')
      ssoActive.value = true
      await fetchCurrentUser()
      return
    } catch {
      // Not running behind Checkmk Apache, fall through to normal auth
    }

    ssoActive.value = false
    sessionStorage.removeItem(SSO_ACTIVE_KEY)
    accessToken.value = localStorage.getItem(ACCESS_TOKEN_KEY)
    refreshToken.value = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (accessToken.value) {
      await fetchCurrentUser()
    }
  }

  async function fetchCurrentUser() {
    if (!accessToken.value) return
    try {
      user.value = await authApi.me(accessToken.value)
      i18n.global.locale.value = (user.value?.language ?? 'en') as 'en' | 'de'
    } catch {
      // Token invalid; clear state
      clearAuth()
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.login(username, password)
      accessToken.value = tokens.access_token
      refreshToken.value = tokens.refresh_token
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
      await fetchCurrentUser()
      const redirect = router.currentRoute.value.query.redirect as string | undefined
      const target: RouteLocationRaw = redirect ? { path: redirect } : { name: 'home' }
      router.push(target)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Login failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    if (accessToken.value) {
      await authApi.logout(accessToken.value).catch(() => {})
    }
    clearAuth()
    if (ssoActive.value) {
      // In Checkmk SSO mode, log out of Checkmk itself
      const url = _checkmkLogoutUrl()
      if (url) { window.location.href = url; return }
    }
    router.push('/login')
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      const tokens = await authApi.refresh(refreshToken.value)
      accessToken.value = tokens.access_token
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
      return true
    } catch {
      clearAuth()
      return false
    }
  }

  function clearAuth() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    ssoActive.value = false
    _initPromise = null  // allow re-init after logout
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    sessionStorage.removeItem(SSO_ACTIVE_KEY)
  }

  return {
    accessToken,
    refreshToken,
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    ssoActive,
    init,
    login,
    logout,
    refreshAccessToken,
    fetchCurrentUser,
  }
})
