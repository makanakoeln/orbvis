/**
 * Typed API client for the Orbvis backend.
 */

import type {
  BackendConfig,
  GlobalSettings,
  IconEntry,
  MapConfig,
  MapObject,
  MapPermissions,
  MapRead,
  MapStates,
  TokenResponse,
  UserRead,
  RoleRead,
  PermissionRead,
} from '@/types/api'

// import.meta.env.BASE_URL is '/' in dev and '/heute/orbvis/' when built with --base
const BASE_URL = `${import.meta.env.BASE_URL}api/v1`

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const METHOD_OVERRIDE = new Set(['PATCH', 'PUT', 'DELETE'])

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const declaredMethod = ((options.method ?? 'GET') as string).toUpperCase()
  const needsOverride = METHOD_OVERRIDE.has(declaredMethod)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  // Tunnel PATCH/PUT/DELETE through POST so restrictive proxies (e.g. OMD Apache) don't block them.
  // The backend MethodOverrideMiddleware restores the original method before routing.
  if (needsOverride) {
    headers['X-HTTP-Method-Override'] = declaredMethod
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    method: needsOverride ? 'POST' : declaredMethod,
    headers,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    const msg = detail?.detail ?? detail?.message ?? `HTTP ${response.status}`
    throw new ApiError(response.status, typeof msg === 'string' ? msg : `HTTP ${response.status}`, detail)
  }

  if (response.status === 204) return undefined as T
  return response.json()
}

// ---- Auth ----

export const authApi = {
  login: (username: string, password: string): Promise<TokenResponse> =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  refresh: (refreshToken: string): Promise<TokenResponse> =>
    request('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  sso: (): Promise<TokenResponse> =>
    request('/auth/sso', {}),

  me: (token: string): Promise<UserRead> =>
    request('/auth/me', {}, token),

  logout: (token: string): Promise<void> =>
    request('/auth/logout', { method: 'POST' }, token),
}

// ---- Maps ----

export const mapsApi = {
  list: (token: string): Promise<MapRead[]> =>
    request('/maps', {}, token),

  get: (name: string, token: string): Promise<MapConfig> =>
    request(`/maps/${name}`, {}, token),

  create: (data: { name: string; alias?: string; backend_id?: string; map_type?: string }, token: string): Promise<MapConfig> =>
    request('/maps', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (name: string, data: Record<string, unknown>, token: string): Promise<MapConfig> =>
    request(`/maps/${name}`, { method: 'PUT', body: JSON.stringify(data) }, token),

  delete: (name: string, token: string): Promise<void> =>
    request(`/maps/${name}`, { method: 'DELETE' }, token),

  getStates: (name: string, token: string): Promise<MapStates> =>
    request(`/maps/${name}/states`, {}, token),

  addObject: (mapName: string, obj: MapObject, token: string): Promise<MapConfig> =>
    request(`/maps/${mapName}/objects`, { method: 'POST', body: JSON.stringify(obj) }, token),

  updateObject: (
    mapName: string,
    objId: string,
    updates: Record<string, unknown>,
    token: string,
  ): Promise<MapObject> =>
    request(`/maps/${mapName}/objects/${objId}`, { method: 'PUT', body: JSON.stringify(updates) }, token),

  deleteObject: (mapName: string, objId: string, token: string): Promise<void> =>
    request(`/maps/${mapName}/objects/${objId}`, { method: 'DELETE' }, token),

  getPermissions: (name: string, token: string): Promise<MapPermissions> =>
    request(`/maps/${name}/permissions`, {}, token),

  uploadBackground: async (mapName: string, file: File, token: string): Promise<{ filename: string }> => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${BASE_URL}/maps/${mapName}/background`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(response.status, `HTTP ${response.status}`, detail)
    }
    return response.json()
  },
}

// ---- Users ----

export const usersApi = {
  list: (token: string): Promise<UserRead[]> =>
    request('/users', {}, token),

  get: (id: number, token: string): Promise<UserRead> =>
    request(`/users/${id}`, {}, token),

  create: (
    data: { name: string; password: string; is_admin?: boolean; must_change_password?: boolean },
    token: string,
  ): Promise<UserRead> =>
    request('/users', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (id: number, data: Record<string, unknown>, token: string): Promise<UserRead> =>
    request(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }, token),

  delete: (id: number, token: string): Promise<void> =>
    request(`/users/${id}`, { method: 'DELETE' }, token),
}

// ---- Roles ----

export const rolesApi = {
  list: (token: string): Promise<RoleRead[]> =>
    request('/roles', {}, token),

  create: (name: string, token: string): Promise<RoleRead> =>
    request('/roles', { method: 'POST', body: JSON.stringify({ name }) }, token),

  delete: (id: number, token: string): Promise<void> =>
    request(`/roles/${id}`, { method: 'DELETE' }, token),

  createPermission: (mod: string, act: string, obj: string, token: string): Promise<PermissionRead> =>
    request('/roles/permissions/', { method: 'POST', body: JSON.stringify({ mod, act, obj }) }, token),

  assignPermission: (roleId: number, permId: number, token: string): Promise<RoleRead> =>
    request(`/roles/${roleId}/permissions/${permId}`, { method: 'POST' }, token),

  removePermission: (roleId: number, permId: number, token: string): Promise<void> =>
    request(`/roles/${roleId}/permissions/${permId}`, { method: 'DELETE' }, token),
}

// ---- Backends ----

export const backendsApi = {
  list: (token: string): Promise<BackendConfig[]> =>
    request('/backends', {}, token),

  create: (data: BackendConfig, token: string): Promise<BackendConfig> =>
    request('/backends', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (id: string, data: Omit<BackendConfig, 'id'>, token: string): Promise<BackendConfig> =>
    request(`/backends/${id}`, { method: 'PUT', body: JSON.stringify(data) }, token),

  delete: (id: string, token: string): Promise<void> =>
    request(`/backends/${id}`, { method: 'DELETE' }, token),

  objects: (backendId: string, type: string, token: string, host?: string): Promise<string[]> => {
    const params = new URLSearchParams({ type })
    if (host) params.set('host', host)
    return request(`/backends/${backendId}/objects?${params}`, {}, token)
  },

  test: (backendId: string, token: string): Promise<{ ok: boolean; message: string }> =>
    request(`/backends/${backendId}/test`, {}, token),

  topology: (backendId: string, token: string): Promise<import('@/types/api').TopologyNode[]> =>
    request(`/backends/${backendId}/topology`, {}, token),

  perfMetrics: (backendId: string, host: string, token: string, service?: string): Promise<string[]> => {
    const params = new URLSearchParams({ host })
    if (service) params.set('service', service)
    return request(`/backends/${backendId}/perf-metrics?${params}`, {}, token)
  },

  testConnection: (
    data: BackendConfig,
    token: string,
  ): Promise<{ ok: boolean; message: string }> =>
    request('/backends/test-connection', { method: 'POST', body: JSON.stringify(data) }, token),
}

// ---- Icons ----

export const iconsApi = {
  list: (token: string): Promise<IconEntry[]> =>
    request('/icons', {}, token),

  upload: async (file: File, token: string): Promise<IconEntry> => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${BASE_URL}/icons`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(response.status, `HTTP ${response.status}`, detail)
    }
    return response.json()
  },

  delete: (name: string, token: string): Promise<void> =>
    request(`/icons/${encodeURIComponent(name)}`, { method: 'DELETE' }, token),
}

// ---- Global Settings ----

export const settingsApi = {
  get: (token: string): Promise<GlobalSettings> =>
    request('/settings', {}, token),

  update: (data: GlobalSettings, token: string): Promise<GlobalSettings> =>
    request('/settings', { method: 'PUT', body: JSON.stringify(data) }, token),
}

export { ApiError }
