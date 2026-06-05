import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'

import { authGuard } from './index'

const { mockAuthState } = vi.hoisted(() => ({
  mockAuthState: {
    init: vi.fn().mockResolvedValue(undefined),
    fetchCurrentUser: vi.fn(),
    isAuthenticated: false,
    isAdmin: false,
    canConfigure: false,
    ssoActive: false,
    isCheckmkDeployment: false,
    user: null as { must_change_password: boolean } | null
  }
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => mockAuthState
}))

function makeRoute(
  overrides: Partial<RouteLocationNormalized> & { meta?: Record<string, unknown> }
): RouteLocationNormalized {
  return {
    fullPath: '/',
    path: '/',
    query: {},
    hash: '',
    matched: [],
    params: {},
    redirectedFrom: undefined,
    name: undefined,
    meta: {},
    ...overrides
  } as RouteLocationNormalized
}

beforeEach(() => {
  vi.clearAllMocks()
  mockAuthState.isAuthenticated = false
  mockAuthState.isAdmin = false
  mockAuthState.canConfigure = false
  mockAuthState.ssoActive = false
  mockAuthState.isCheckmkDeployment = false
  mockAuthState.user = null
})

describe('router guards', () => {
  it('redirects unauthenticated users on protected routes to /login with redirect param', async () => {
    const result = await authGuard(
      makeRoute({
        fullPath: '/boards/foo',
        path: '/boards/foo',
        meta: { requiresAuth: true }
      })
    )
    expect(result).toEqual({ name: 'login', query: { redirect: '/boards/foo' } })
  })

  it('allows authenticated users through', async () => {
    mockAuthState.isAuthenticated = true
    const result = await authGuard(
      makeRoute({ fullPath: '/', path: '/', meta: { requiresAuth: true } })
    )
    expect(result).toBeUndefined()
  })

  it('redirects non-admin away from admin routes to home', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.isAdmin = false
    const result = await authGuard(
      makeRoute({
        fullPath: '/admin/users',
        path: '/admin/users',
        meta: { requiresAuth: true, requiresAdmin: true }
      })
    )
    expect(result).toEqual({ name: 'home' })
  })

  it('allows admin through admin routes', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.isAdmin = true
    const result = await authGuard(
      makeRoute({
        fullPath: '/admin/users',
        path: '/admin/users',
        meta: { requiresAuth: true, requiresAdmin: true }
      })
    )
    expect(result).toBeUndefined()
  })

  it('redirects users without configure permission away from configure routes', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.isAdmin = false
    mockAuthState.canConfigure = false
    const result = await authGuard(
      makeRoute({
        fullPath: '/admin/connections',
        path: '/admin/connections',
        meta: { requiresAuth: true, requiresConfigure: true }
      })
    )
    expect(result).toEqual({ name: 'home' })
  })

  it('allows non-admin configurers through configure routes', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.isAdmin = false
    mockAuthState.canConfigure = true
    const result = await authGuard(
      makeRoute({
        fullPath: '/admin/connections',
        path: '/admin/connections',
        meta: { requiresAuth: true, requiresConfigure: true }
      })
    )
    expect(result).toBeUndefined()
  })

  it('forces users with must_change_password to the change-password view', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { must_change_password: true }
    const result = await authGuard(
      makeRoute({ fullPath: '/', path: '/', name: 'home', meta: { requiresAuth: true } })
    )
    expect(result).toEqual({ name: 'change-password' })
  })

  it('does not force the change-password detour when already on that view', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { must_change_password: true }
    const result = await authGuard(
      makeRoute({
        fullPath: '/change-password',
        path: '/change-password',
        name: 'change-password',
        meta: { requiresAuth: true }
      })
    )
    expect(result).toBeUndefined()
  })

  it('sends authenticated users away from /login to home', async () => {
    mockAuthState.isAuthenticated = true
    const result = await authGuard(
      makeRoute({
        fullPath: '/login',
        path: '/login',
        name: 'login',
        meta: { public: true }
      })
    )
    expect(result).toEqual({ name: 'home' })
  })

  it('calls fetchCurrentUser in SSO mode (theme resync)', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.ssoActive = true
    await authGuard(makeRoute({ path: '/', fullPath: '/', meta: { requiresAuth: true } }))
    expect(mockAuthState.fetchCurrentUser).toHaveBeenCalledTimes(1)
  })

  it('does not call fetchCurrentUser outside SSO / Checkmk deployments', async () => {
    mockAuthState.isAuthenticated = true
    await authGuard(makeRoute({ path: '/', fullPath: '/', meta: { requiresAuth: true } }))
    expect(mockAuthState.fetchCurrentUser).not.toHaveBeenCalled()
  })
})
