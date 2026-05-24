/**
 * Typed API client for the Orbvis backend.
 */

import type {
    AggregationInfo,
    AggregationNode,
    BoardConfig,
    BoardObject,
    BoardPermissions,
    BoardRead,
    ConnectionConfig,
    ConnectionContext,
    DowntimeEntry,
    GlobalSettings,
    GroupMember,
    ImageEntry,
    ImageUsageEntry,
    MapStates,
    MetricGraphGroup,
    MetricHistoryResponse,
    ObjectDetails,
    PerfometerResult,
    PermissionRead,
    RoleRead,
    SystemSettings,
    TokenResponse,
    UserRead,
} from '@/types/api';

// import.meta.env.BASE_URL is '/' in dev and '/heute/orbvis/' when built with --base
const BASE_URL = `${import.meta.env.BASE_URL}api/v1`;

export class ApiError extends Error {
    constructor(
        public status: number,
        message: string,
        public detail?: unknown,
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

function formatApiErrorBody(body: unknown, status: number): string {
    if (body && typeof body === 'object') {
        const d = (body as { detail?: unknown; message?: unknown }).detail;
        if (typeof d === 'string') return d;
        if (typeof (body as { message?: unknown }).message === 'string') {
            return (body as { message: string }).message;
        }
        if (Array.isArray(d)) {
            const parts = d
                .filter(
                    (it): it is { loc?: unknown[]; msg?: string } => !!it && typeof it === 'object',
                )
                .map((it) => {
                    const loc = Array.isArray(it.loc)
                        ? it.loc
                              .filter((p) => p !== 'body' && p !== 'query' && p !== 'path')
                              .map((p) => String(p))
                              .join('.')
                        : '';
                    const rawMsg = (it.msg ?? '').replace(/^Value error,\s*/, '');
                    return loc ? `${loc}: ${rawMsg}` : rawMsg;
                })
                .filter(Boolean);
            if (parts.length) return parts.join('; ');
        }
    }
    return `HTTP ${status}`;
}

const METHOD_OVERRIDE = new Set(['PATCH', 'PUT', 'DELETE']);

async function uploadFile<T>(path: string, file: File, token: string): Promise<T> {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${BASE_URL}${path}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
    });
    if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new ApiError(response.status, formatApiErrorBody(detail, response.status), detail);
    }
    return response.json();
}

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
        throw new ApiError(response.status, formatApiErrorBody(detail, response.status), detail);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
}

// ---- Capabilities ----

export interface Capabilities {
    form_specs: boolean;
}

export const capabilitiesApi = {
    // Unauthenticated — feature flags are public.
    get: (): Promise<Capabilities> => request('/capabilities'),
};

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

    get: (name: string, token: string): Promise<BoardConfig> =>
        request(`/boards/${name}`, {}, token),

    autoObjects: (name: string, token: string): Promise<BoardObject[]> =>
        request(`/boards/${name}/auto-objects`, {}, token),

    create: (
        data: {
            name: string;
            alias?: string;
            connection_id?: string;
            icon_size?: number | null;
            view?: Record<string, unknown>;
        },
        token: string,
    ): Promise<BoardConfig> =>
        request('/boards', { method: 'POST', body: JSON.stringify(data) }, token),

    update: (
        name: string,
        data: Record<string, unknown>,
        token: string,
        ifMatch?: number | null,
    ): Promise<BoardConfig> =>
        request(
            `/boards/${name}`,
            {
                method: 'PUT',
                body: JSON.stringify(data),
                headers:
                    ifMatch != null
                        ? ({ 'If-Match': String(ifMatch) } as Record<string, string>)
                        : {},
            },
            token,
        ),

    reorder: (order: { name: string; sort_order: number }[], token: string): Promise<void> =>
        request('/boards/reorder', { method: 'POST', body: JSON.stringify(order) }, token),

    delete: (name: string, token: string): Promise<void> =>
        request(`/boards/${name}`, { method: 'DELETE' }, token),

    getStates: (
        name: string,
        token: string,
        radarOverride?: { filter: string; filterValue: string } | null,
    ): Promise<MapStates> => {
        let path = `/boards/${name}/states`;
        if (radarOverride) {
            const qs = new URLSearchParams({
                radar_filter: radarOverride.filter,
                radar_filter_value: radarOverride.filterValue,
            });
            path += `?${qs.toString()}`;
        }
        return request(path, {}, token);
    },

    addObject: (boardName: string, obj: BoardObject, token: string): Promise<BoardConfig> =>
        request(
            `/boards/${boardName}/objects`,
            { method: 'POST', body: JSON.stringify(obj) },
            token,
        ),

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

    uploadBackground: (
        boardName: string,
        file: File,
        token: string,
    ): Promise<{ filename: string; version: number | null }> =>
        uploadFile(`/boards/${boardName}/background`, file, token),

    deleteBackground: (boardName: string, token: string): Promise<{ version: number | null }> =>
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

    importCfg: (file: File, token: string, overwrite = false): Promise<BoardConfig> =>
        uploadFile(`/boards/import/cfg?overwrite=${overwrite}`, file, token),

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
        data: {
            name: string;
            password: string;
            is_admin?: boolean;
            must_change_password?: boolean;
        },
        token: string,
    ): Promise<UserRead> =>
        request('/users', { method: 'POST', body: JSON.stringify(data) }, token),

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

// ---- Connections ----

export const boardsApiFormSpec = {
    getMetadataSchema: (token: string): Promise<Record<string, unknown>> =>
        request('/boards/-/metadata-schema', {}, token),

    getFlowViewSchema: (token: string): Promise<Record<string, unknown>> =>
        request('/boards/-/flow-view-schema', {}, token),

    getMetadata: (name: string, token: string): Promise<Record<string, unknown>> =>
        request(`/boards/${encodeURIComponent(name)}/metadata`, {}, token),

    updateMetadata: (
        name: string,
        form: Record<string, unknown>,
        token: string,
    ): Promise<unknown> =>
        request(
            `/boards/${encodeURIComponent(name)}/metadata`,
            { method: 'PUT', body: JSON.stringify(form) },
            token,
        ),
};

export const connectionsApiFormSpec = {
    getSchema: (token: string): Promise<Record<string, unknown>> =>
        request('/connections/schema', {}, token),

    getFormData: (id: string, token: string): Promise<Record<string, unknown>> =>
        request(`/connections/${encodeURIComponent(id)}/form`, {}, token),

    createFromForm: (
        id: string,
        form: Record<string, unknown>,
        token: string,
    ): Promise<ConnectionConfig> =>
        request('/connections/form', { method: 'POST', body: JSON.stringify({ id, form }) }, token),

    updateFromForm: (id: string, form: Record<string, unknown>, token: string): Promise<unknown> =>
        request(
            `/connections/${encodeURIComponent(id)}/form`,
            { method: 'PUT', body: JSON.stringify(form) },
            token,
        ),

    testFromForm: (
        id: string,
        form: Record<string, unknown>,
        token: string,
    ): Promise<{ ok: boolean; message: string }> =>
        request(
            '/connections/form/test-connection',
            { method: 'POST', body: JSON.stringify({ id, form }) },
            token,
        ),
};

export const connectionsApi = {
    list: (token: string): Promise<ConnectionConfig[]> => request('/connections', {}, token),

    create: (data: ConnectionConfig, token: string): Promise<ConnectionConfig> =>
        request('/connections', { method: 'POST', body: JSON.stringify(data) }, token),

    update: (
        id: string,
        data: Omit<ConnectionConfig, 'id'>,
        token: string,
    ): Promise<ConnectionConfig> =>
        request(`/connections/${id}`, { method: 'PUT', body: JSON.stringify(data) }, token),

    delete: (id: string, token: string): Promise<void> =>
        request(`/connections/${id}`, { method: 'DELETE' }, token),

    objects: (
        connectionId: string,
        type: string,
        token: string,
        host?: string,
    ): Promise<string[]> => {
        const params = new URLSearchParams({ type });
        if (host) params.set('host', host);
        return request(`/connections/${connectionId}/objects?${params}`, {}, token);
    },

    aggregations: (connectionId: string, token: string): Promise<AggregationInfo[]> =>
        request(`/connections/${connectionId}/aggregations`, {}, token),

    aggregationTree: (
        connectionId: string,
        aggregationId: string,
        depth: number,
        token: string,
    ): Promise<{ tree: AggregationNode | null; connection_ok: boolean }> =>
        request(
            `/connections/${connectionId}/aggregations/${encodeURIComponent(aggregationId)}/tree?depth=${depth}`,
            {},
            token,
        ),

    groupMembers: (
        connectionId: string,
        groupType: 'hostgroup' | 'servicegroup',
        groupName: string,
        token: string,
    ): Promise<GroupMember[]> =>
        request(
            `/connections/${connectionId}/groups/${groupType}/${encodeURIComponent(groupName)}/members`,
            {},
            token,
        ),

    test: (connectionId: string, token: string): Promise<{ ok: boolean; message: string }> =>
        request(`/connections/${connectionId}/test`, {}, token),

    topology: (
        connectionId: string,
        token: string,
        includeServices = false,
        opts?: {
            root?: string | null;
            childLayers?: number | null;
            parentLayers?: number | null;
            topAffectedHosts?: number | null;
            servicesPerHost?: number | null;
        },
    ): Promise<import('@/types/api').TopologyNode[]> => {
        const params = new URLSearchParams();
        if (includeServices) params.set('include_services', 'true');
        if (opts?.root) params.set('root', opts.root);
        if (opts?.childLayers != null) params.set('child_layers', String(opts.childLayers));
        if (opts?.parentLayers != null) params.set('parent_layers', String(opts.parentLayers));
        if (opts?.topAffectedHosts != null) {
            params.set('top_affected_hosts', String(opts.topAffectedHosts));
        }
        if (opts?.servicesPerHost != null) {
            params.set('services_per_host', String(opts.servicesPerHost));
        }
        const qs = params.toString();
        return request(`/connections/${connectionId}/topology${qs ? `?${qs}` : ''}`, {}, token);
    },

    perfMetrics: (
        connectionId: string,
        host: string,
        token: string,
        service?: string,
    ): Promise<string[]> => {
        const params = new URLSearchParams({ host });
        if (service) params.set('service', service);
        return request(`/connections/${connectionId}/perf-metrics?${params}`, {}, token);
    },

    graphTemplates: (
        connectionId: string,
        host: string,
        service: string | null,
        token: string,
    ): Promise<MetricGraphGroup[]> => {
        const params = new URLSearchParams({ host });
        if (service) params.set('service', service);
        return request(`/connections/${connectionId}/graph-templates?${params}`, {}, token);
    },

    metricHistory: (
        connectionId: string,
        host: string,
        service: string | null,
        minutes: number,
        token: string,
    ): Promise<MetricHistoryResponse> => {
        const params = new URLSearchParams({ host, minutes: String(minutes) });
        if (service) params.set('service', service);
        return request(`/connections/${connectionId}/metric-history?${params}`, {}, token);
    },

    objectDetails: (
        connectionId: string,
        objectType: 'host' | 'service',
        host: string,
        service: string | null,
        token: string,
    ): Promise<ObjectDetails | null> => {
        const params = new URLSearchParams({ type: objectType, host });
        if (service) params.set('service', service);
        return request(`/connections/${connectionId}/object-details?${params}`, {}, token);
    },

    hostGeo: (
        connectionId: string,
        host: string,
        token: string,
    ): Promise<{ lat: number; lng: number } | null> =>
        request(
            `/connections/${connectionId}/host-geo?host=${encodeURIComponent(host)}`,
            {},
            token,
        ),

    context: (connectionId: string, token: string): Promise<ConnectionContext> =>
        request(`/connections/${connectionId}/context`, {}, token),

    testConnection: (
        data: ConnectionConfig,
        token: string,
    ): Promise<{ ok: boolean; message: string }> =>
        request(
            '/connections/test-connection',
            { method: 'POST', body: JSON.stringify(data) },
            token,
        ),
};

// ---- Images ----

export const imagesApi = {
    list: (token: string): Promise<ImageEntry[]> => request('/images', {}, token),

    upload: (file: File, token: string): Promise<ImageEntry> => uploadFile('/images', file, token),

    usage: (name: string, token: string): Promise<ImageUsageEntry[]> =>
        request(`/images/${encodeURIComponent(name)}/usage`, {}, token),

    delete: (name: string, token: string, force = false): Promise<void> =>
        request(
            `/images/${encodeURIComponent(name)}${force ? '?force=true' : ''}`,
            { method: 'DELETE' },
            token,
        ),
};

// ---- Global Settings ----

export const settingsApi = {
    get: (token: string): Promise<GlobalSettings> => request('/settings', {}, token),

    update: (data: GlobalSettings, token: string): Promise<GlobalSettings> =>
        request('/settings', { method: 'PUT', body: JSON.stringify(data) }, token),

    getSchema: (token: string): Promise<Record<string, unknown>> =>
        request('/settings/schema', {}, token),

    // FormSpec-shaped sibling of get/update. Storage stays flat (so every
    // ``useSettingsStore`` consumer keeps using ``settings.label_color`` etc.
    // unchanged); the backend pair below packs/unpacks ``labels`` into a
    // CascadingSingleChoice payload for FormEdit.
    getForm: (token: string): Promise<Record<string, unknown>> =>
        request('/settings/form', {}, token),

    updateForm: (data: Record<string, unknown>, token: string): Promise<Record<string, unknown>> =>
        request('/settings/form', { method: 'PUT', body: JSON.stringify(data) }, token),
};

// ---- Object option catalogues (line styles etc.) ----

export interface ObjectOption {
    name: string;
    title: string;
}
export interface ObjectOptions {
    line_styles: ObjectOption[];
}

export const objectOptionsApi = {
    get: (token: string): Promise<ObjectOptions> => request('/settings/object-options', {}, token),
};

// ---- System Settings (logging + Checkmk integration) ----

export const systemSettingsApi = {
    get: (token: string): Promise<SystemSettings> => request('/settings/system', {}, token),

    update: (data: SystemSettings, token: string): Promise<SystemSettings> =>
        request('/settings/system', { method: 'PUT', body: JSON.stringify(data) }, token),

    getSchema: (token: string): Promise<Record<string, unknown>> =>
        request('/settings/system/schema', {}, token),

    // FormSpec-shaped pair. ``log_level`` is mapped to/from the
    // "env_default" sentinel branch server-side so the FormEdit can
    // render it as a plain SingleChoice instead of an optional toggle.
    getForm: (token: string): Promise<Record<string, unknown>> =>
        request('/settings/system/form', {}, token),

    updateForm: (data: Record<string, unknown>, token: string): Promise<Record<string, unknown>> =>
        request('/settings/system/form', { method: 'PUT', body: JSON.stringify(data) }, token),
};

// ---- Checkmk REST API (direct browser → CMK, same-origin session) ----

async function cmkRequest(baseUrl: string, path: string, body?: unknown): Promise<void> {
    // baseUrl e.g. "http://host/site" → API at "http://host/site/check_mk/api/1.0"
    const base = baseUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const url = `${base}/check_mk/api/1.0${path}`;
    const response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            'If-Match': '*',
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
        const detail = await response.json().catch(() => null);
        const msg = detail?.detail ?? detail?.title ?? `HTTP ${response.status}`;
        throw new Error(typeof msg === 'string' ? msg : `HTTP ${response.status}`);
    }
}

interface CmkDowntimeItem {
    id: string;
    extensions: {
        site_id: string;
        host_name: string;
        service_description?: string;
        author: string;
        comment: string;
        start_time: string;
        end_time: string;
        is_service: boolean;
    };
}

async function cmkGetDowntimes(
    baseUrl: string,
    params: Record<string, string>,
): Promise<DowntimeEntry[]> {
    const base = baseUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const query = new URLSearchParams(params).toString();
    const url = `${base}/check_mk/api/1.0/domain-types/downtime/collections/all?${query}`;
    const response = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
        const detail = await response.json().catch(() => null);
        const msg = detail?.detail ?? detail?.title ?? `HTTP ${response.status}`;
        throw new Error(typeof msg === 'string' ? msg : `HTTP ${response.status}`);
    }
    const data: { value: CmkDowntimeItem[] } = await response.json();
    return data.value.map((item) => ({
        id: item.id,
        site_id: item.extensions.site_id,
        host_name: item.extensions.host_name,
        service_description: item.extensions.service_description,
        author: item.extensions.author,
        comment: item.extensions.comment,
        start_time: item.extensions.start_time,
        end_time: item.extensions.end_time,
        type: item.extensions.is_service ? 'service' : 'host',
    }));
}

/**
 * Action verbs the orbvis backend's livestatus-command relay accepts.
 * Mirrors `_HOST_COMMANDS` / `_SERVICE_COMMANDS` in
 * backend/app/api/v1/connections.py — keep the lists in sync.
 */
type CmkAction =
    | 'force_check'
    | 'enable_notifications'
    | 'disable_notifications'
    | 'enable_checks'
    | 'disable_checks'
    | 'remove_acknowledgement'
    | 'acknowledge'
    | 'add_comment'
    | 'schedule_downtime';

/**
 * Resolve the OrbVis API base from the CMK baseUrl the DetailDrawer
 * passes us. `<host>/<site>/check_mk/` → `<host>/<site>/orbvis/api/v1`.
 *
 * The cmkApi entries take a CMK URL because they used to talk to the
 * Checkmk REST API directly. Force-check / enable-notifications /
 * disable-active-checks etc. don't exist as REST verbs in any version of
 * Checkmk (2.3–2.6), so the calls now route through OrbVis's own backend
 * which writes to the livestatus command pipe instead.
 */
function orbvisApiBase(cmkBaseUrl: string): string {
    return cmkBaseUrl.replace(/\/check_mk\/?$/, '/orbvis/api/v1').replace(/\/$/, '');
}

async function orbvisCommand(
    cmkBaseUrl: string,
    target: 'host-action' | 'service-action',
    body: Record<string, unknown>,
): Promise<void> {
    // The cmkApi was originally session-cookie based (CMK SSO). Its
    // replacement uses OrbVis's own JWT. Read the same key the auth store
    // writes — keeping cmkApi callable from places without a vue-store
    // injection (composables, modal components).
    const token = sessionStorage.getItem('orbvis_access_token') || '';
    // OrbVis hardcodes "live_1" as the default connection_id on every
    // CMK-bundled install (set by orbvis-setup), so it's a safe default
    // for action commands. Future work: thread the active board's
    // connection_id through if multi-backend setups need it.
    const connectionId = 'live_1';
    const url = `${orbvisApiBase(cmkBaseUrl)}/connections/${connectionId}/${target}`;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        const detail = await response.json().catch(() => null);
        const msg = detail?.detail ?? detail?.title ?? `HTTP ${response.status}`;
        throw new Error(typeof msg === 'string' ? msg : `HTTP ${response.status}`);
    }
}

function cmkHostAction(baseUrl: string, hostname: string, action: CmkAction): Promise<void> {
    return orbvisCommand(baseUrl, 'host-action', {
        action,
        host_name: hostname,
    });
}

// ---- Metrics (perfometer) ----

export const metricsApi = {
    getPerfometer(
        connectionId: string,
        host: string,
        service: string,
        token: string,
    ): Promise<PerfometerResult | null> {
        const params = new URLSearchParams({ connection_id: connectionId, host, service });
        return request<PerfometerResult | null>(`/metrics/perfometer?${params}`, {}, token);
    },
};

function cmkServiceAction(
    baseUrl: string,
    hostname: string,
    serviceDescription: string,
    action: CmkAction,
): Promise<void> {
    return orbvisCommand(baseUrl, 'service-action', {
        action,
        host_name: hostname,
        service_description: serviceDescription,
    });
}

function toEpochSeconds(s: string): number {
    const n = Number(s);
    if (Number.isFinite(n) && n > 0) return Math.floor(n);
    const t = Date.parse(s);
    return Number.isFinite(t) ? Math.floor(t / 1000) : 0;
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
        return orbvisCommand(baseUrl, 'host-action', {
            action: 'acknowledge',
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
        return orbvisCommand(baseUrl, 'service-action', {
            action: 'acknowledge',
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
        return orbvisCommand(baseUrl, 'host-action', {
            action: 'schedule_downtime',
            host_name: hostname,
            start_time: toEpochSeconds(startTime),
            end_time: toEpochSeconds(endTime),
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
        return orbvisCommand(baseUrl, 'service-action', {
            action: 'schedule_downtime',
            host_name: hostname,
            service_description: serviceDescription,
            start_time: toEpochSeconds(startTime),
            end_time: toEpochSeconds(endTime),
            comment,
        });
    },

    removeDowntimeHost(baseUrl: string, hostname: string): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/downtime/actions/delete/invoke', {
            delete_type: 'params',
            host_name: hostname,
        });
    },

    removeDowntimeService(
        baseUrl: string,
        hostname: string,
        serviceDescription: string,
    ): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/downtime/actions/delete/invoke', {
            delete_type: 'params',
            host_name: hostname,
            service_descriptions: [serviceDescription],
        });
    },

    listDowntimesHost(baseUrl: string, hostname: string): Promise<DowntimeEntry[]> {
        return cmkGetDowntimes(baseUrl, { host_name: hostname, downtime_type: 'host' });
    },

    listDowntimesService(
        baseUrl: string,
        hostname: string,
        serviceDescription: string,
    ): Promise<DowntimeEntry[]> {
        return cmkGetDowntimes(baseUrl, {
            host_name: hostname,
            service_description: serviceDescription,
            downtime_type: 'service',
        });
    },

    removeDowntimeById(baseUrl: string, downtimeId: string, siteId: string): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/downtime/actions/delete/invoke', {
            delete_type: 'by_id',
            downtime_id: downtimeId,
            site_id: siteId,
        });
    },

    forceCheckHost: (baseUrl: string, hostname: string) =>
        cmkHostAction(baseUrl, hostname, 'force_check'),

    forceCheckService: (baseUrl: string, hostname: string, serviceDescription: string) =>
        cmkServiceAction(baseUrl, hostname, serviceDescription, 'force_check'),

    addCommentHost(baseUrl: string, hostname: string, comment: string): Promise<void> {
        return orbvisCommand(baseUrl, 'host-action', {
            action: 'add_comment',
            host_name: hostname,
            comment,
        });
    },

    addCommentService(
        baseUrl: string,
        hostname: string,
        serviceDescription: string,
        comment: string,
    ): Promise<void> {
        return orbvisCommand(baseUrl, 'service-action', {
            action: 'add_comment',
            host_name: hostname,
            service_description: serviceDescription,
            comment,
        });
    },

    // remove-ack via the OrbVis livestatus relay rather than CMK REST.
    // The REST endpoint /domain-types/acknowledge/actions/delete/invoke is
    // 2.4+ only — 2.3 sites would 404 on the old code path.
    removeAcknowledgementHost: (baseUrl: string, hostname: string) =>
        cmkHostAction(baseUrl, hostname, 'remove_acknowledgement'),

    removeAcknowledgementService: (baseUrl: string, hostname: string, serviceDescription: string) =>
        cmkServiceAction(baseUrl, hostname, serviceDescription, 'remove_acknowledgement'),

    // ── Group bulk-actions ─────────────────────────────────────────────────
    // CMK's REST API supports ``acknowledge_type=hostgroup|servicegroup`` and
    // ``downtime_type=hostgroup|servicegroup`` so a single call applies to
    // every member of the group. This is dramatically faster (and safer in
    // terms of partial failures) than looping per-member from the UI.

    acknowledgeHostgroup(
        baseUrl: string,
        groupName: string,
        comment: string,
        sticky: boolean,
        notify: boolean,
        persistent: boolean,
    ): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/acknowledge/collections/host', {
            acknowledge_type: 'hostgroup',
            hostgroup_name: groupName,
            comment,
            sticky,
            notify,
            persistent,
        });
    },

    acknowledgeServicegroup(
        baseUrl: string,
        groupName: string,
        comment: string,
        sticky: boolean,
        notify: boolean,
        persistent: boolean,
    ): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/acknowledge/collections/service', {
            acknowledge_type: 'servicegroup',
            servicegroup_name: groupName,
            comment,
            sticky,
            notify,
            persistent,
        });
    },

    downtimeHostgroup(
        baseUrl: string,
        groupName: string,
        startTime: string,
        endTime: string,
        comment: string,
    ): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/downtime/collections/host', {
            downtime_type: 'hostgroup',
            hostgroup_name: groupName,
            start_time: startTime,
            end_time: endTime,
            comment,
        });
    },

    downtimeServicegroup(
        baseUrl: string,
        groupName: string,
        startTime: string,
        endTime: string,
        comment: string,
    ): Promise<void> {
        return cmkRequest(baseUrl, '/domain-types/downtime/collections/service', {
            downtime_type: 'servicegroup',
            servicegroup_name: groupName,
            start_time: startTime,
            end_time: endTime,
            comment,
        });
    },

    enableNotificationsHost: (baseUrl: string, hostname: string) =>
        cmkHostAction(baseUrl, hostname, 'enable_notifications'),

    disableNotificationsHost: (baseUrl: string, hostname: string) =>
        cmkHostAction(baseUrl, hostname, 'disable_notifications'),

    enableNotificationsService: (baseUrl: string, hostname: string, serviceDescription: string) =>
        cmkServiceAction(baseUrl, hostname, serviceDescription, 'enable_notifications'),

    disableNotificationsService: (baseUrl: string, hostname: string, serviceDescription: string) =>
        cmkServiceAction(baseUrl, hostname, serviceDescription, 'disable_notifications'),

    enableChecksHost: (baseUrl: string, hostname: string) =>
        cmkHostAction(baseUrl, hostname, 'enable_checks'),

    disableChecksHost: (baseUrl: string, hostname: string) =>
        cmkHostAction(baseUrl, hostname, 'disable_checks'),

    enableChecksService: (baseUrl: string, hostname: string, serviceDescription: string) =>
        cmkServiceAction(baseUrl, hostname, serviceDescription, 'enable_checks'),

    disableChecksService: (baseUrl: string, hostname: string, serviceDescription: string) =>
        cmkServiceAction(baseUrl, hostname, serviceDescription, 'disable_checks'),
};
