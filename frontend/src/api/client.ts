/**
 * Typed API client for the NagVis 2 backend.
 */

import type {
  MapConfig,
  MapRead,
  MapStates,
  TokenResponse,
  UserRead,
  RoleRead,
} from '@/types/api'

const BASE_URL = '/api/v1'

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

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new ApiError(response.status, `HTTP ${response.status}`, detail)
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

  create: (data: { name: string; alias?: string; backend_id?: string }, token: string): Promise<MapConfig> =>
    request('/maps', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (name: string, data: Record<string, unknown>, token: string): Promise<MapConfig> =>
    request(`/maps/${name}`, { method: 'PUT', body: JSON.stringify(data) }, token),

  delete: (name: string, token: string): Promise<void> =>
    request(`/maps/${name}`, { method: 'DELETE' }, token),

  getStates: (name: string, token: string): Promise<MapStates> =>
    request(`/maps/${name}/states`, {}, token),
}

// ---- Users ----

export const usersApi = {
  list: (token: string): Promise<UserRead[]> =>
    request('/users', {}, token),

  get: (id: number, token: string): Promise<UserRead> =>
    request(`/users/${id}`, {}, token),

  create: (
    data: { name: string; password: string; is_admin?: boolean },
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
}

export { ApiError }
