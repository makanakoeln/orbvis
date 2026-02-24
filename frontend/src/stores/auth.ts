import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/client'
import type { UserRead } from '@/types/api'
import router from '@/router'

const ACCESS_TOKEN_KEY = 'nagvis_access_token'
const REFRESH_TOKEN_KEY = 'nagvis_refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const user = ref<UserRead | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)

  function initFromStorage() {
    accessToken.value = localStorage.getItem(ACCESS_TOKEN_KEY)
    refreshToken.value = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (accessToken.value) {
      fetchCurrentUser()
    }
  }

  async function fetchCurrentUser() {
    if (!accessToken.value) return
    try {
      user.value = await authApi.me(accessToken.value)
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
      router.push('/')
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
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  return {
    accessToken,
    refreshToken,
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    initFromStorage,
    login,
    logout,
    refreshAccessToken,
  }
})
