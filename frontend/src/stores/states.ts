import { defineStore } from 'pinia';
import { ref } from 'vue';

import { boardsApi, connectionsApi } from '@/api/client';
import type { MetricGraphGroup, ObjectState, WebSocketStateUpdate } from '@/types/api';
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

// Base path without trailing slash, e.g. '/heute/orbvis' or ''
const _base = import.meta.env.BASE_URL.replace(/\/$/, '');

// States considered "bad" (descending severity)
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
  if (newSev <= prevSev) return; // only notify on worsening
  if (!_BAD_STATES.has(obj.state)) return;
  const name = obj.object_id;
  new Notification(`OrbVis: ${obj.state}`, {
    body: name,
    tag: name, // de-duplicate: same object → replace existing notification
  });
}

export const useStatesStore = defineStore('states', () => {
  const states = ref<Record<string, ObjectState>>({}); // keyed by object_id
  const history = ref<Record<string, MetricSnapshot[]>>({});
  const metricValues = ref<Record<string, Record<string, MetricPoint[]>>>({});
  const metricTitles = ref<Record<string, Record<string, string>>>({}); // objectId → metricId → title
  const metricGraphs = ref<Record<string, MetricGraphGroup[]>>({}); // objectId → graph groups
  const connected = ref(false);
  const lastUpdate = ref<number | null>(null);
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
    // Per-metric value history
    const mv = metricValues.value[objectId] ?? {};
    for (const m of metrics) {
      const mArr = mv[m.label] ?? [];
      mArr.push({ ts, value: m.value, unit: m.unit });
      mv[m.label] = mArr.length > HISTORY_MAX ? mArr.slice(-HISTORY_MAX) : mArr;
    }
    metricValues.value[objectId] = mv;
  }

  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let currentMap: string | null = null;
  let currentToken: string | undefined = undefined;
  // true once we determined WebSocket doesn't work and switched to polling
  let pollingMode = false;

  async function connectToMap(mapName: string, token?: string) {
    if (currentMap === mapName && (ws?.readyState === WebSocket.OPEN || pollTimer)) return;
    disconnect();
    currentMap = mapName;
    currentToken = token;
    await _fetchStates();
    if (!pollingMode) _connect();
    else _startPolling();
  }

  async function _fetchStates() {
    if (!currentMap || !currentToken) return;
    const mapAtStart = currentMap;
    try {
      const data = await boardsApi.getStates(mapAtStart, currentToken);
      if (currentMap !== mapAtStart) return; // board changed while fetching
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
      connected.value = data.backend_ok;
    } catch {
      // Backend unreachable or auth error – show as offline
      connected.value = false;
    }
  }

  function _startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(_fetchStates, 15_000);
  }

  function _connect() {
    if (!currentMap || !currentToken) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    // Token is sent as the first message after the handshake — never in the URL —
    // to prevent it from leaking into server logs and browser history.
    const url = `${protocol}://${window.location.host}${_base}/api/v1/ws/boards/${currentMap}`;
    ws = new WebSocket(url);
    let opened = false;

    ws.onopen = () => {
      opened = true;
      ws?.send(JSON.stringify({ type: 'auth', token: currentToken }));
      // Do NOT set connected=true here. The first state_update message sets
      // connected via msg.states.backend_ok, which correctly reflects whether the
      // monitoring backend is reachable – not just whether the WS handshake succeeded.
      // Setting true here would override a backend_ok=false from the pre-connect
      // _fetchStates() call and show "Live" when the monitoring backend is actually down.
    };

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketStateUpdate = JSON.parse(event.data);
        if (msg.type === 'state_update') {
          const newStates: Record<string, ObjectState> = {};
          for (const s of msg.states.states) {
            if (notificationsEnabled.value) _notifyStateChange(s, states.value[s.object_id]);
            newStates[s.object_id] = s;
            if (s.perf_data) _recordHistory(s.object_id, s.perf_data, msg.states.generated_at);
          }
          for (const id of Object.keys(states.value)) {
            if (!newStates[id]) delete states.value[id];
          }
          Object.assign(states.value, newStates);
          lastUpdate.value = msg.states.generated_at;
          connected.value = msg.states.backend_ok;
        }
      } catch {
        /* ignore parse errors */
      }
    };

    ws.onclose = () => {
      if (!opened) {
        // Never opened: WebSocket not available (e.g. reverse proxy without WS support).
        // Switch permanently to HTTP polling for this session.
        pollingMode = true;
        ws = null;
        _startPolling();
        return;
      }
      // Was open but dropped – try reconnect
      connected.value = false;
      reconnectTimer = setTimeout(_connect, 5000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
    connected.value = false;
    states.value = {};
    history.value = {};
    metricValues.value = {};
    metricTitles.value = {};
    metricGraphs.value = {};
    currentMap = null;
    currentToken = undefined;
  }

  function getState(objectId: string): ObjectState | undefined {
    return states.value[objectId];
  }

  async function prefillMetricHistory(
    objectId: string,
    backendId: string,
    host: string,
    service: string | null,
    timeWindowMinutes: number,
    accessToken: string,
  ): Promise<void> {
    try {
      const data = await connectionsApi.metricHistory(
        backendId,
        host,
        service,
        timeWindowMinutes,
        accessToken,
      );
      if (!data || !Object.keys(data.series).length) return;
      // Store titles (overwrite — server always has the authoritative title)
      if (Object.keys(data.titles).length) {
        metricTitles.value[objectId] = { ...data.titles };
      }
      if (data.graphs?.length) {
        metricGraphs.value[objectId] = data.graphs;
      }
      // Merge: historical points first, live WebSocket points on top (deduplicated by ts)
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
      // Backend doesn't support metric history (plain Nagios) — silently ignore
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
    notificationsEnabled,
    connectToMap,
    disconnect,
    getState,
    toggleNotifications,
    prefillMetricHistory,
    clearMetricValues,
  };
});
