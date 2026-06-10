import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

import { ACCESS_TOKEN_KEY, ApiError, authApi } from '@/api/client'
import { setLanguage } from '@/i18n'
import router from '@/router'
import { useSettingsStore } from '@/stores/settings'
import type { UserRead } from '@/types/api'

const REFRESH_TOKEN_KEY = 'orbvis_refresh_token'
const SSO_ACTIVE_KEY = 'orbvis_sso'
// Guards against a redirect loop if we return from Checkmk still 2FA-pending.
const TWO_FACTOR_REDIRECT_KEY = 'orbvis_2fa_redirect'

// Derive Checkmk logout URL from current path: /heute/orbvis/... → /heute/check_mk/logout.py
function applyInlineHelp(enabled: boolean): void {
  document.body.classList.toggle('inline_help_as_text', enabled)
}

function _checkmkLogoutUrl(): string | null {
  const m = window.location.pathname.match(/^(\/[^/]+)\/orbvis/)
  return m ? `${m[1]}/check_mk/logout.py` : null
}

// Checkmk 2FA challenge page, returning to the current OrbVis URL once 2FA is done.
function _checkmkTwoFactorUrl(): string | null {
  const m = window.location.pathname.match(/^(\/[^/]+)\/orbvis/)
  if (!m) return null
  const origtarget = window.location.pathname + window.location.search + window.location.hash
  return `${m[1]}/check_mk/user_login_two_factor.py?_origtarget=${encodeURIComponent(origtarget)}`
}

// SSO probe failed because the Checkmk session passed the password step but still
// owes its second factor — the backend signals this with a sentinel detail.
function _isTwoFactorRequired(e: unknown): boolean {
  return (
    e instanceof ApiError &&
    e.status === 401 &&
    (e.detail as { detail?: unknown } | undefined)?.detail === 'two_factor_required'
  )
}

// Bounce to Checkmk's 2FA challenge, exactly once: if we land here again after
// returning still-pending, fall back to the login form instead of looping.
// Returns true when navigation was triggered (caller must stop init).
function _redirectToTwoFactor(): boolean {
  if (sessionStorage.getItem(TWO_FACTOR_REDIRECT_KEY) === '1') {
    sessionStorage.removeItem(TWO_FACTOR_REDIRECT_KEY)
    console.warn('[OrbVis] Still 2FA-pending after redirect — showing login form')
    return false
  }
  const url = _checkmkTwoFactorUrl()
  if (!url) return false
  sessionStorage.setItem(TWO_FACTOR_REDIRECT_KEY, '1')
  window.location.assign(url)
  return true
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const user = ref<UserRead | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  // true when logged in via Checkmk SSO
  const ssoActive = ref(false)

  // true when OrbVis is served inside a Checkmk/OMD installation (path: /{site}/orbvis/…)
  // Used to suppress the OrbVis sidebar even when SSO is temporarily unavailable.
  const isCheckmkDeployment = computed(() => /^\/[^/]+\/orbvis/.test(window.location.pathname))

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)
  // Capability flags from /me. In Checkmk deployments these honour the
  // orbvis.configure / orbvis.edit_all permissions so non-admin roles can be
  // granted access; they fall back to is_admin for older backends.
  const canConfigure = computed(() => user.value?.can_configure ?? user.value?.is_admin ?? false)
  const canCreateBoards = computed(
    () => user.value?.can_create_boards ?? user.value?.is_admin ?? false
  )

  function mayCommand(verb: string): boolean {
    return user.value?.command_permissions?.includes(verb) ?? false
  }

  // Ensures initialization runs exactly once per SPA session and is awaitable
  let _initPromise: Promise<void> | null = null

  function init(): Promise<void> {
    if (!_initPromise) {
      _initPromise = _doInit()
    }
    return _initPromise
  }

  async function _doInit(): Promise<void> {
    // Skip the SSO probe when a non-SSO login was already established — otherwise
    // every reload floods the network panel with 401s the user can't act on.
    const hadSsoBefore = sessionStorage.getItem(SSO_ACTIVE_KEY) === '1'
    const hasStoredToken = !!sessionStorage.getItem(ACCESS_TOKEN_KEY)
    const skipSsoProbe = hasStoredToken && !hadSsoBefore
    let ssoTokens = null
    if (isCheckmkDeployment.value && !skipSsoProbe) {
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          ssoTokens = await authApi.sso()
          break
        } catch (e: unknown) {
          if (e instanceof TypeError && attempt === 0) {
            // Network-level failure (server not ready yet) — wait briefly and retry
            await new Promise((r) => setTimeout(r, 600))
          } else if (_isTwoFactorRequired(e) && _redirectToTwoFactor()) {
            return // leaving the SPA for Checkmk's 2FA challenge
          } else {
            console.warn('[OrbVis] SSO failed:', e)
            break // HTTP 401 or second failure: SSO not available
          }
        }
      }
    }
    if (ssoTokens) {
      sessionStorage.removeItem(TWO_FACTOR_REDIRECT_KEY)
      accessToken.value = ssoTokens.access_token
      refreshToken.value = ssoTokens.refresh_token
      sessionStorage.setItem(ACCESS_TOKEN_KEY, ssoTokens.access_token)
      sessionStorage.setItem(REFRESH_TOKEN_KEY, ssoTokens.refresh_token)
      sessionStorage.setItem(SSO_ACTIVE_KEY, '1')
      ssoActive.value = true
      await fetchCurrentUser()
      return
    }

    ssoActive.value = false
    sessionStorage.removeItem(SSO_ACTIVE_KEY)
    accessToken.value = sessionStorage.getItem(ACCESS_TOKEN_KEY)
    refreshToken.value = sessionStorage.getItem(REFRESH_TOKEN_KEY)
    if (accessToken.value) {
      await fetchCurrentUser()
    } else if (refreshToken.value) {
      // No access token but refresh token present — silently renew
      const ok = await refreshAccessToken()
      if (ok) await fetchCurrentUser()
    }
  }

  async function _loadUser(token: string) {
    user.value = await authApi.me(token)
    const lang =
      ssoActive.value && user.value.cmk_language
        ? user.value.cmk_language
        : (user.value.language ?? 'en')
    void setLanguage(lang)
    applyInlineHelp(user.value.cmk_inline_help)
    // Load global settings so they're available for new map/object creation
    useSettingsStore()
      .load()
      .catch((e) => console.warn('[OrbVis] Failed to load settings:', e))
    // Load object-option registry (line styles, …) so dropdowns
    // in the EditPanel / Global Settings stay in sync. Lazy import
    // keeps the auth store free of a circular dep through pinia.
    import('@/stores/objectOptions').then((m) => {
      m.useObjectOptionsStore()
        .ensureLoaded()
        .catch((e) => console.warn('[OrbVis] Failed to load object options:', e))
    })
  }

  async function fetchCurrentUser() {
    if (!accessToken.value) return
    try {
      await _loadUser(accessToken.value)
    } catch {
      // Access token may be expired — try refresh before giving up
      if (refreshToken.value) {
        const ok = await refreshAccessToken()
        if (ok && accessToken.value) {
          try {
            await _loadUser(accessToken.value)
            return
          } catch {
            /* fall through to clearAuth */
          }
        }
      }
      clearAuth()
    }
  }

  async function login(username: string, password: string) {
    // Guard against a double submit (e.g. Enter firing both the input's keydown
    // handler and the form's implicit submission) re-entering mid-request.
    if (loading.value) return
    loading.value = true
    error.value = null
    try {
      const tokens = await authApi.login(username, password)
      accessToken.value = tokens.access_token
      refreshToken.value = tokens.refresh_token
      sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
      sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
      await fetchCurrentUser()
      // query params can be string[] (?redirect=a&redirect=b) — only honor a
      // plain single value, anything else lands on home.
      const redirect = router.currentRoute.value.query.redirect
      const target: RouteLocationRaw =
        typeof redirect === 'string' && redirect ? { path: redirect } : { name: 'home' }
      router.push(target)
    } catch (e: unknown) {
      // Communicated via `error` (LoginView renders it) — re-throwing would
      // only produce an unhandled rejection in the submit handler.
      error.value = e instanceof Error ? e.message : 'Login failed'
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    if (accessToken.value) {
      await authApi
        .logout(accessToken.value)
        .catch((e) => console.warn('[OrbVis] Logout failed:', e))
    }
    clearAuth()
    if (ssoActive.value) {
      // In Checkmk SSO mode, log out of Checkmk itself
      const url = _checkmkLogoutUrl()
      if (url) {
        window.location.href = url
        return
      }
    }
    router.push('/login')
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      const tokens = await authApi.refresh(refreshToken.value)
      accessToken.value = tokens.access_token
      sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
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
    _initPromise = null // allow re-init after logout
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
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
    canConfigure,
    canCreateBoards,
    mayCommand,
    ssoActive,
    isCheckmkDeployment,
    init,
    login,
    logout,
    refreshAccessToken,
    fetchCurrentUser
  }
})
