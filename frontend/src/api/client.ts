/**
 * Typed API client for the Orbvis backend.
 */

import type {
  BackendConfig,
  BackendContext,
  BoardConfig,
  BoardObject,
  BoardPermissions,
  BoardRead,
  GlobalSettings,
  ImageEntry,
  MapStates,
  PermissionRead,
  RoleRead,
  TokenResponse,
  UserRead,
} from '@/types/api';

// import.meta.env.BASE_URL is '/' in dev and '/heute/orbvis/' when built with --base
const BASE_URL = `${import.meta.env.BASE_URL}api/v1`;

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const METHOD_OVERRIDE = new Set(['PATCH', 'PUT', 'DELETE']);

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const declaredMethod = ((options.method ?? 'GET') as string).toUpperCase();
  const needsOverride = METHOD_OVERRIDE.has(declaredMethod);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Tunnel PATCH/PUT/DELETE through POST so restrictive proxies (e.g. OMD Apache) don't block them.
  // The backend MethodOverrideMiddleware restores the original method before routing.
  if (needsOverride) {
    headers['X-HTTP-Method-Override'] = declaredMethod;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    method: needsOverride ? 'POST' : declaredMethod,
    headers,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const msg = detail?.detail ?? detail?.message ?? `HTTP ${response.status}`;
    throw new ApiError(
      response.status,
      typeof msg === 'string' ? msg : `HTTP ${response.status}`,
      detail,
    );
  }

  if (response.status === 204) return undefined as T;
  return response.json();
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

  sso: (): Promise<TokenResponse> => request('/auth/sso', {}),

  me: (token: string): Promise<UserRead> => request('/auth/me', {}, token),

  logout: (token: string): Promise<void> => request('/auth/logout', { method: 'POST' }, token),
};

// ---- Boards ----

export const boardsApi = {
  list: (token: string): Promise<BoardRead[]> => request('/boards', {}, token),

  get: (name: string, token: string): Promise<BoardConfig> => request(`/boards/${name}`, {}, token),

  create: (
    data: {
      name: string;
      alias?: string;
      backend_id?: string;
      icon_size?: number;
      view?: Record<string, unknown>;
    },
    token: string,
  ): Promise<BoardConfig> =>
    request('/boards', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (name: string, data: Record<string, unknown>, token: string): Promise<BoardConfig> =>
    request(`/boards/${name}`, { method: 'PUT', body: JSON.stringify(data) }, token),

  delete: (name: string, token: string): Promise<void> =>
    request(`/boards/${name}`, { method: 'DELETE' }, token),

  getStates: (name: string, token: string): Promise<MapStates> =>
    request(`/boards/${name}/states`, {}, token),

  addObject: (boardName: string, obj: BoardObject, token: string): Promise<BoardConfig> =>
    request(`/boards/${boardName}/objects`, { method: 'POST', body: JSON.stringify(obj) }, token),

  updateObject: (
    boardName: string,
    objId: string,
    updates: Record<string, unknown>,
    token: string,
  ): Promise<BoardObject> =>
    request(
      `/boards/${boardName}/objects/${objId}`,
      { method: 'PUT', body: JSON.stringify(updates) },
      token,
    ),

  deleteObject: (boardName: string, objId: string, token: string): Promise<void> =>
    request(`/boards/${boardName}/objects/${objId}`, { method: 'DELETE' }, token),

  getPermissions: (name: string, token: string): Promise<BoardPermissions> =>
    request(`/boards/${name}/permissions`, {}, token),

  uploadBackground: async (
    boardName: string,
    file: File,
    token: string,
  ): Promise<{ filename: string }> => {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${BASE_URL}/boards/${boardName}/background`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new ApiError(response.status, `HTTP ${response.status}`, detail);
    }
    return response.json();
  },

  deleteBackground: (boardName: string, token: string): Promise<void> =>
    request(`/boards/${boardName}/background`, { method: 'DELETE' }, token),

  clone: (
    name: string,
    data: { new_name: string; alias?: string },
    token: string,
  ): Promise<BoardConfig> =>
    request(`/boards/${name}/clone`, { method: 'POST', body: JSON.stringify(data) }, token),

  importBoard: (data: BoardConfig, token: string, overwrite = false): Promise<BoardConfig> =>
    request(
      `/boards/import?overwrite=${overwrite}`,
      { method: 'POST', body: JSON.stringify(data) },
      token,
    ),

  importCfg: async (file: File, token: string, overwrite = false): Promise<BoardConfig> => {
    const form = new FormData();
    form.append('file', file);
    const BASE_URL = `${import.meta.env.BASE_URL}api/v1`;
    const res = await fetch(`${BASE_URL}/boards/import/cfg?overwrite=${overwrite}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? res.statusText);
    }
    return res.json();
  },

  exportBoard: async (name: string, token: string): Promise<void> => {
    const cfg = await request<BoardConfig>(`/boards/${name}`, {}, token);
    const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

// ---- Users ----

export const usersApi = {
  list: (token: string): Promise<UserRead[]> => request('/users', {}, token),

  get: (id: number, token: string): Promise<UserRead> => request(`/users/${id}`, {}, token),

  create: (
    data: { name: string; password: string; is_admin?: boolean; must_change_password?: boolean },
    token: string,
  ): Promise<UserRead> => request('/users', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (id: number, data: Record<string, unknown>, token: string): Promise<UserRead> =>
    request(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }, token),

  delete: (id: number, token: string): Promise<void> =>
    request(`/users/${id}`, { method: 'DELETE' }, token),

  assignRole: (userId: number, roleId: number, token: string): Promise<UserRead> =>
    request(`/users/${userId}/roles/${roleId}`, { method: 'POST' }, token),

  removeRole: (userId: number, roleId: number, token: string): Promise<void> =>
    request(`/users/${userId}/roles/${roleId}`, { method: 'DELETE' }, token),
};

// ---- Roles ----

export const rolesApi = {
  list: (token: string): Promise<RoleRead[]> => request('/roles', {}, token),

  create: (name: string, token: string): Promise<RoleRead> =>
    request('/roles', { method: 'POST', body: JSON.stringify({ name }) }, token),

  delete: (id: number, token: string): Promise<void> =>
    request(`/roles/${id}`, { method: 'DELETE' }, token),

  createPermission: (
    mod: string,
    act: string,
    obj: string,
    token: string,
  ): Promise<PermissionRead> =>
    request(
      '/roles/permissions/',
      { method: 'POST', body: JSON.stringify({ mod, act, obj }) },
      token,
    ),

  assignPermission: (roleId: number, permId: number, token: string): Promise<RoleRead> =>
    request(`/roles/${roleId}/permissions/${permId}`, { method: 'POST' }, token),

  removePermission: (roleId: number, permId: number, token: string): Promise<void> =>
    request(`/roles/${roleId}/permissions/${permId}`, { method: 'DELETE' }, token),
};

// ---- Backends ----

export const connectionsApi = {
  list: (token: string): Promise<BackendConfig[]> => request('/backends', {}, token),

  create: (data: BackendConfig, token: string): Promise<BackendConfig> =>
    request('/backends', { method: 'POST', body: JSON.stringify(data) }, token),

  update: (id: string, data: Omit<BackendConfig, 'id'>, token: string): Promise<BackendConfig> =>
    request(`/backends/${id}`, { method: 'PUT', body: JSON.stringify(data) }, token),

  delete: (id: string, token: string): Promise<void> =>
    request(`/backends/${id}`, { method: 'DELETE' }, token),

  objects: (backendId: string, type: string, token: string, host?: string): Promise<string[]> => {
    const params = new URLSearchParams({ type });
    if (host) params.set('host', host);
    return request(`/backends/${backendId}/objects?${params}`, {}, token);
  },

  test: (backendId: string, token: string): Promise<{ ok: boolean; message: string }> =>
    request(`/backends/${backendId}/test`, {}, token),

  topology: (
    backendId: string,
    token: string,
    includeServices = false,
  ): Promise<import('@/types/api').TopologyNode[]> =>
    request(
      `/backends/${backendId}/topology${includeServices ? '?include_services=true' : ''}`,
      {},
      token,
    ),

  perfMetrics: (
    backendId: string,
    host: string,
    token: string,
    service?: string,
  ): Promise<string[]> => {
    const params = new URLSearchParams({ host });
    if (service) params.set('service', service);
    return request(`/backends/${backendId}/perf-metrics?${params}`, {}, token);
  },

  metricHistory: (
    backendId: string,
    host: string,
    service: string | null,
    minutes: number,
    token: string,
  ): Promise<Record<string, Array<{ ts: number; value: number; unit: string }>>> => {
    const params = new URLSearchParams({ host, minutes: String(minutes) });
    if (service) params.set('service', service);
    return request(`/backends/${backendId}/metric-history?${params}`, {}, token);
  },

  hostGeo: (
    backendId: string,
    host: string,
    token: string,
  ): Promise<{ lat: number; lng: number } | null> =>
    request(`/backends/${backendId}/host-geo?host=${encodeURIComponent(host)}`, {}, token),

  context: (backendId: string, token: string): Promise<BackendContext> =>
    request(`/backends/${backendId}/context`, {}, token),

  testConnection: (data: BackendConfig, token: string): Promise<{ ok: boolean; message: string }> =>
    request('/backends/test-connection', { method: 'POST', body: JSON.stringify(data) }, token),
};

// ---- Images ----

export const imagesApi = {
  list: (token: string): Promise<ImageEntry[]> => request('/images', {}, token),

  upload: async (file: File, token: string): Promise<ImageEntry> => {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${BASE_URL}/images`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new ApiError(response.status, `HTTP ${response.status}`, detail);
    }
    return response.json();
  },

  delete: (name: string, token: string): Promise<void> =>
    request(`/images/${encodeURIComponent(name)}`, { method: 'DELETE' }, token),
};

// ---- Global Settings ----

export const settingsApi = {
  get: (token: string): Promise<GlobalSettings> => request('/settings', {}, token),

  update: (data: GlobalSettings, token: string): Promise<GlobalSettings> =>
    request('/settings', { method: 'PUT', body: JSON.stringify(data) }, token),
};

// ---- Checkmk REST API (direct browser → CMK, same-origin session) ----

async function cmkRequest(baseUrl: string, path: string, body?: unknown): Promise<void> {
  // baseUrl e.g. "http://host/site" → API at "http://host/site/check_mk/api/1.0"
  const base = baseUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
  const url = `${base}/check_mk/api/1.0${path}`;
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const msg = detail?.detail ?? detail?.title ?? `HTTP ${response.status}`;
    throw new Error(typeof msg === 'string' ? msg : `HTTP ${response.status}`);
  }
}

export const cmkApi = {
  acknowledgeHost(
    baseUrl: string,
    hostname: string,
    comment: string,
    sticky: boolean,
    notify: boolean,
    persistent: boolean,
  ): Promise<void> {
    return cmkRequest(baseUrl, '/domain-types/acknowledge/collections/host', {
      acknowledge_type: 'host',
      host_name: hostname,
      comment,
      sticky,
      notify,
      persistent,
    });
  },

  acknowledgeService(
    baseUrl: string,
    hostname: string,
    serviceDescription: string,
    comment: string,
    sticky: boolean,
    notify: boolean,
    persistent: boolean,
  ): Promise<void> {
    return cmkRequest(baseUrl, '/domain-types/acknowledge/collections/service', {
      acknowledge_type: 'service',
      host_name: hostname,
      service_description: serviceDescription,
      comment,
      sticky,
      notify,
      persistent,
    });
  },

  downtimeHost(
    baseUrl: string,
    hostname: string,
    startTime: string,
    endTime: string,
    comment: string,
  ): Promise<void> {
    return cmkRequest(baseUrl, '/domain-types/downtime/collections/host', {
      downtime_type: 'host',
      host_name: hostname,
      start_time: startTime,
      end_time: endTime,
      comment,
    });
  },

  downtimeService(
    baseUrl: string,
    hostname: string,
    serviceDescription: string,
    startTime: string,
    endTime: string,
    comment: string,
  ): Promise<void> {
    return cmkRequest(baseUrl, '/domain-types/downtime/collections/service', {
      downtime_type: 'service',
      host_name: hostname,
      service_descriptions: [serviceDescription],
      start_time: startTime,
      end_time: endTime,
      comment,
    });
  },

  forceCheckHost(baseUrl: string, hostname: string): Promise<void> {
    return cmkRequest(
      baseUrl,
      `/objects/host/${encodeURIComponent(hostname)}/actions/reschedule-active-checks/invoke`,
      { force: true },
    );
  },

  forceCheckService(baseUrl: string, hostname: string, serviceDescription: string): Promise<void> {
    const id = `${encodeURIComponent(hostname)}~${encodeURIComponent(serviceDescription)}`;
    return cmkRequest(baseUrl, `/objects/service/${id}/actions/reschedule-active-checks/invoke`, {
      force: true,
    });
  },
};

export { ApiError };
