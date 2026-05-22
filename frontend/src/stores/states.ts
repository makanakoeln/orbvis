import { defineStore } from 'pinia';
import { ref } from 'vue';

import { boardsApi, connectionsApi } from '@/api/client';
import type {
    MetricGraphGroup,
    ObjectState,
    TopologyDelta,
    TopologyNode,
    WebSocketStateUpdate,
    WebSocketTopologyUpdate,
} from '@/types/api';
import { parsePerfData, utilPercent } from '@/utils/perf';

export interface MetricSnapshot {
    ts: number;
    pct: number;
}
export interface MetricPoint {
    ts: number;
    value: number;
    unit: string;
}
const HISTORY_MAX = 10080; // up to 7d at 1min resolution

// Base path without trailing slash, e.g. '/heute/orbvis' or ''.
// When built with --base=./ (relative), fall back to window.location.pathname.
const _base = import.meta.env.BASE_URL.startsWith('.')
    ? window.location.pathname.replace(/\/+$/, '')
    : import.meta.env.BASE_URL.replace(/\/$/, '');

const _BAD_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);
const _SEVERITY: Record<string, number> = {
    OK: 0,
    UP: 0,
    PENDING: 0,
    WARNING: 1,
    UNKNOWN: 1,
    CRITICAL: 2,
    UNREACHABLE: 2,
    DOWN: 3,
};

function _notifyStateChange(obj: ObjectState, prev: ObjectState | undefined) {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return;
    const prevSev = _SEVERITY[prev?.state ?? 'OK'] ?? 0;
    const newSev = _SEVERITY[obj.state] ?? 0;
    if (newSev <= prevSev) return;
    if (!_BAD_STATES.has(obj.state)) return;
    const name = obj.object_id;
    new Notification(`OrbVis: ${obj.state}`, {
        body: name,
        tag: name,
    });
}

export const useStatesStore = defineStore('states', () => {
    const states = ref<Record<string, ObjectState>>({}); // keyed by object_id
    const history = ref<Record<string, MetricSnapshot[]>>({});
    const metricValues = ref<Record<string, Record<string, MetricPoint[]>>>({});
    const metricTitles = ref<Record<string, Record<string, string>>>({});
    const metricGraphs = ref<Record<string, MetricGraphGroup[]>>({});
    const connected = ref(false);
    const lastUpdate = ref<number | null>(null);
    const initialLoad = ref(false);
    const topology = ref<TopologyNode[]>([]);
    const topologyReady = ref(false);
    // Kept under the historical name for compatibility with views; false after
    // we fall back to HTTP polling because SSE didn't work.
    const wsAvailable = ref(true);
    const _LS_NOTIF = 'orbvis_notifications';
    const notificationsEnabled = ref(
        typeof Notification !== 'undefined' &&
            Notification.permission === 'granted' &&
            localStorage.getItem(_LS_NOTIF) === '1',
    );

    async function toggleNotifications(): Promise<void> {
        if (typeof Notification === 'undefined') return;
        if (notificationsEnabled.value) {
            notificationsEnabled.value = false;
            localStorage.setItem(_LS_NOTIF, '0');
            return;
        }
        if (Notification.permission === 'denied') return;
        if (Notification.permission !== 'granted') {
            const result = await Notification.requestPermission();
            if (result !== 'granted') return;
        }
        notificationsEnabled.value = true;
        localStorage.setItem(_LS_NOTIF, '1');
    }

    function _recordHistory(objectId: string, perf_data: string, ts: number) {
        const metrics = parsePerfData(perf_data);
        if (!metrics.length) return;
        const arr = history.value[objectId] ?? [];
        arr.push({ ts, pct: utilPercent(metrics[0]) });
        history.value[objectId] = arr.length > HISTORY_MAX ? arr.slice(-HISTORY_MAX) : arr;
        const mv = metricValues.value[objectId] ?? {};
        for (const m of metrics) {
            const mArr = mv[m.label] ?? [];
            mArr.push({ ts, value: m.value, unit: m.unit });
            mv[m.label] = mArr.length > HISTORY_MAX ? mArr.slice(-HISTORY_MAX) : mArr;
        }
        metricValues.value[objectId] = mv;
    }

    let sse: EventSource | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let currentMap: string | null = null;
    let currentToken: string | undefined = undefined;
    // True after we determined SSE doesn't work and switched permanently to polling.
    let pollingMode = false;

    async function connectToMap(mapName: string, token?: string) {
        if (currentMap === mapName && (sse?.readyState === EventSource.OPEN || pollTimer)) return;
        disconnect();
        currentMap = mapName;
        currentToken = token;
        initialLoad.value = true;
        try {
            await _fetchStates();
        } finally {
            initialLoad.value = false;
        }
        if (!pollingMode) _connect();
        else _startPolling();
    }

    // Settings-preview override: when the radar filter is live-edited in the
    // Settings modal, the preview iframe sets this so the next fetch carries
    // the unsaved filter as query params instead of using the disk-cfg filter.
    const radarOverride = ref<{ filter: string; filterValue: string } | null>(null);

    async function _fetchStates() {
        if (!currentMap || !currentToken) return;
        const mapAtStart = currentMap;
        try {
            const data = await boardsApi.getStates(mapAtStart, currentToken, radarOverride.value);
            if (currentMap !== mapAtStart) return;
            const newStates: Record<string, ObjectState> = {};
            const ts = Date.now() / 1000;
            for (const s of data.states) {
                if (notificationsEnabled.value) _notifyStateChange(s, states.value[s.object_id]);
                newStates[s.object_id] = s;
                if (s.perf_data) _recordHistory(s.object_id, s.perf_data, ts);
            }
            for (const id of Object.keys(states.value)) {
                if (!newStates[id]) delete states.value[id];
            }
            Object.assign(states.value, newStates);
            lastUpdate.value = ts;
            connected.value = data.connection_ok;
        } catch {
            connected.value = false;
        }
    }

    function _startPolling() {
        if (pollTimer) return;
        pollTimer = setInterval(_fetchStates, 15_000);
    }

    function _applyTopologyDelta(delta: TopologyDelta) {
        if (delta.full) {
            topology.value = [...delta.added];
            return;
        }
        const removed = new Set(delta.removed);
        const updated = new Map<string, TopologyNode>(
            delta.changed.map((n) => [n.name, n] as const),
        );
        topology.value = topology.value
            .filter((n) => !removed.has(n.name))
            .map((n) => updated.get(n.name) ?? n)
            .concat(delta.added);
    }

    function _connect() {
        if (!currentMap || !currentToken) return;
        // SSE: GET endpoint, token in query string (EventSource cannot set
        // Authorization). Access-token TTL is short (60 min default), so the
        // exposure window is bounded.
        const url = `${_base}/api/v1/sse/boards/${encodeURIComponent(
            currentMap,
        )}?token=${encodeURIComponent(currentToken)}`;
        sse = new EventSource(url);
        let opened = false;

        sse.onopen = () => {
            opened = true;
        };

        sse.onmessage = (event) => {
            try {
                const msg: WebSocketStateUpdate | WebSocketTopologyUpdate = JSON.parse(event.data);
                if (msg.type === 'state_update') {
                    const isFull = msg.full ?? true;
                    for (const s of msg.states.states) {
                        if (notificationsEnabled.value)
                            _notifyStateChange(s, states.value[s.object_id]);
                        states.value[s.object_id] = s;
                        if (s.perf_data)
                            _recordHistory(s.object_id, s.perf_data, msg.states.generated_at);
                    }
                    if (isFull) {
                        const incomingIds = new Set(msg.states.states.map((s) => s.object_id));
                        for (const id of Object.keys(states.value)) {
                            if (!incomingIds.has(id)) delete states.value[id];
                        }
                    } else {
                        for (const id of msg.removed_ids ?? []) {
                            delete states.value[id];
                        }
                    }
                    lastUpdate.value = msg.states.generated_at;
                    connected.value = msg.states.connection_ok;
                } else if (msg.type === 'topology_update') {
                    _applyTopologyDelta(msg.delta);
                    topologyReady.value = true;
                    lastUpdate.value = msg.delta.generated_at;
                }
            } catch {
                /* ignore parse errors */
            }
        };

        sse.onerror = () => {
            // EventSource auto-reconnects on transient errors; close + fall back
            // to polling only when the very first connect failed (proxy without
            // streaming support, auth rejected etc.).
            if (!opened) {
                pollingMode = true;
                wsAvailable.value = false;
                sse?.close();
                sse = null;
                _startPolling();
                return;
            }
            connected.value = false;
        };
    }

    function disconnect() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
        if (sse) {
            sse.onerror = null;
            sse.close();
            sse = null;
        }
        connected.value = false;
        initialLoad.value = false;
        states.value = {};
        history.value = {};
        metricValues.value = {};
        metricTitles.value = {};
        metricGraphs.value = {};
        topology.value = [];
        topologyReady.value = false;
        currentMap = null;
        currentToken = undefined;
    }

    function getState(objectId: string): ObjectState | undefined {
        return states.value[objectId];
    }

    async function prefillMetricHistory(
        objectId: string,
        connectionId: string,
        host: string,
        service: string | null,
        timeWindowMinutes: number,
        accessToken: string,
    ): Promise<void> {
        try {
            const data = await connectionsApi.metricHistory(
                connectionId,
                host,
                service,
                timeWindowMinutes,
                accessToken,
            );
            if (!data || !Object.keys(data.series).length) return;
            if (Object.keys(data.titles).length) {
                metricTitles.value[objectId] = { ...data.titles };
            }
            if (data.graphs?.length) {
                metricGraphs.value[objectId] = data.graphs;
            }
            const mv: Record<string, MetricPoint[]> = { ...(metricValues.value[objectId] ?? {}) };
            for (const [label, pts] of Object.entries(data.series)) {
                const existing = mv[label] ?? [];
                const existingTs = new Set(existing.map((p) => p.ts));
                const merged = [...pts.filter((p) => !existingTs.has(p.ts)), ...existing]
                    .sort((a, b) => a.ts - b.ts)
                    .slice(-HISTORY_MAX);
                mv[label] = merged;
            }
            metricValues.value[objectId] = mv;
        } catch {
            // Backend doesn't support metric history (plain Nagios) — silently ignore.
        }
    }

    function clearMetricValues(objectId: string): void {
        metricValues.value[objectId] = {};
        delete metricGraphs.value[objectId];
    }

    return {
        states,
        history,
        metricValues,
        metricTitles,
        metricGraphs,
        connected,
        lastUpdate,
        initialLoad,
        topology,
        topologyReady,
        wsAvailable,
        notificationsEnabled,
        connectToMap,
        disconnect,
        getState,
        refreshNow: _fetchStates,
        async refreshWithIndicator(): Promise<void> {
            initialLoad.value = true;
            try {
                await _fetchStates();
            } finally {
                initialLoad.value = false;
            }
        },
        refreshAfterCommand(): void {
            void _fetchStates();
            setTimeout(() => void _fetchStates(), 1500);
        },
        toggleNotifications,
        prefillMetricHistory,
        clearMetricValues,
        setRadarOverride(filter: string | null, filterValue?: string): void {
            radarOverride.value =
                filter && typeof filterValue === 'string' ? { filter, filterValue } : null;
            void _fetchStates();
        },
    };
});
