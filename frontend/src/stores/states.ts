import { defineStore } from 'pinia'
import { markRaw, ref, shallowRef, triggerRef } from 'vue'

import { boardsApi, connectionsApi } from '@/api/client'
import type {
  FolderTreeDelta,
  FolderTreeNode,
  FolderTreeOverride,
  MetricGraphGroup,
  ObjectState,
  TopologyDelta,
  TopologyNode,
  TopologyTiming,
  WebSocketStateUpdate,
  WebSocketTopologyUpdate
} from '@/types/api'
import { parsePerfData, utilPercent } from '@/utils/perf'

export interface MetricSnapshot {
  ts: number
  pct: number
}
export interface MetricPoint {
  ts: number
  value: number
  unit: string
}
const HISTORY_MAX = 10080 // up to 7d at 1min resolution

// Base path without trailing slash, e.g. '/heute/orbvis' or ''.
// When built with --base=./ (relative), fall back to window.location.pathname.
const _base = import.meta.env.BASE_URL.startsWith('.')
  ? window.location.pathname.replace(/\/+$/, '')
  : import.meta.env.BASE_URL.replace(/\/$/, '')

const _BAD_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN'])
const _SEVERITY: Record<string, number> = {
  OK: 0,
  UP: 0,
  PENDING: 0,
  WARNING: 1,
  UNKNOWN: 1,
  CRITICAL: 2,
  UNREACHABLE: 2,
  DOWN: 3
}

// Fire a browser notification when `name` worsens into a bad state. Shared by
// the flat-states path and the foldertree snapshot diff so the policy lives once.
function _maybeNotify(name: string, state: string, prevState: string | undefined) {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
  const prevSev = _SEVERITY[prevState ?? 'OK'] ?? 0
  const newSev = _SEVERITY[state] ?? 0
  if (newSev <= prevSev || !_BAD_STATES.has(state)) return
  new Notification(`OrbVis: ${state}`, { body: name, tag: name })
}

function _notifyStateChange(obj: ObjectState, prev: ObjectState | undefined) {
  _maybeNotify(obj.object_id, obj.state, prev?.state)
}

function _collectFolderHostStates(node: FolderTreeNode, out: Map<string, string>) {
  if (node.kind === 'host') {
    out.set(node.title, node.state)
    return
  }
  for (const c of node.children) _collectFolderHostStates(c, out)
}

// Index every node by its (unique) path so folder-tree deltas can patch in place.
function _indexFolderTree(node: FolderTreeNode, out: Map<string, FolderTreeNode>) {
  out.set(node.path, node)
  for (const c of node.children) _indexFolderTree(c, out)
}

// Foldertree boards ship no flat states list, so host-state notifications are
// derived by diffing successive tree snapshots. Returns the new snapshot to
// store; a null `prev` only primes (else every bad host would alert on load).
function _diffNotifyFolderTree(
  tree: FolderTreeNode | null,
  prev: Map<string, string> | null
): Map<string, string> | null {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted' || !tree) {
    return null
  }
  const current = new Map<string, string>()
  _collectFolderHostStates(tree, current)
  if (prev !== null) {
    for (const [host, state] of current) _maybeNotify(host, state, prev.get(host))
  }
  return current
}

export const useStatesStore = defineStore('states', () => {
  const states = ref<Record<string, ObjectState>>({}) // keyed by object_id
  const history = ref<Record<string, MetricSnapshot[]>>({})
  const metricValues = ref<Record<string, Record<string, MetricPoint[]>>>({})
  const metricTitles = ref<Record<string, Record<string, string>>>({})
  const metricGraphs = ref<Record<string, MetricGraphGroup[]>>({})
  const connected = ref(false)
  const lastUpdate = ref<number | null>(null)
  const initialLoad = ref(false)
  const topology = ref<TopologyNode[]>([])
  const topologyReady = ref(false)
  // Bumped on every applied topology timing patch. Consumers that read a
  // node's timing off a captured reference (the Flow Board's detail drawer)
  // watch this to re-derive — the in-place field mutation alone doesn't always
  // re-trigger their computed.
  const topologyTimingVersion = ref(0)
  // Resolved + aggregated tree for foldertree boards (null for other types).
  // shallowRef + markRaw: not deep-reactive (100k+ nodes). The REST load + SSE
  // ``full`` replace it wholesale; SSE deltas patch nodes in place via the path
  // index and triggerRef() to notify consumers.
  const folderTree = shallowRef<FolderTreeNode | null>(null)
  // markRaw nodes patched in place are invisible to Vue, and ``triggerRef`` is
  // swallowed by every ``computed(() => states.folderTree)`` (stable reference).
  // Consumers read this counter to re-derive live (cf. topologyTimingVersion).
  const folderTreeVersion = ref(0)
  let folderTreeIndex = new Map<string, FolderTreeNode>()
  // Previous foldertree host→state snapshot, for deriving notifications (see
  // _diffNotifyFolderTree). null until the first snapshot primes it.
  let prevFolderHostStates: Map<string, string> | null = null

  // Replace the whole tree (REST load / SSE full) and rebuild the path index.
  function _setFolderTree(tree: FolderTreeNode | null) {
    folderTree.value = tree ? markRaw(tree) : null
    folderTreeIndex = new Map()
    if (tree) _indexFolderTree(tree, folderTreeIndex)
    folderTreeVersion.value++
  }

  // Apply an SSE folder-tree delta: full → replace; else patch each changed node
  // in place (and reorder its children when the server resorted them), then
  // triggerRef so consumers of the shallowRef re-derive.
  function _applyFolderTreeDelta(delta: FolderTreeDelta | null | undefined) {
    if (!delta) return
    if (delta.full) {
      _setFolderTree(delta.tree ?? null)
      return
    }
    for (const p of delta.changed) {
      const node = folderTreeIndex.get(p.path)
      if (!node) continue
      node.title = p.title
      node.site_id = p.site_id ?? null
      node.state = p.state
      node.is_empty = p.is_empty
      node.host_count = p.host_count
      node.problem_count = p.problem_count
      node.severity_counts = p.severity_counts
      node.output = p.output
      node.acknowledged = p.acknowledged
      node.in_downtime = p.in_downtime
      node.is_flapping = p.is_flapping
      node.last_state_change = p.last_state_change ?? null
      node.services_summary = p.services_summary ?? null
      if (p.children_order) {
        const byPath = new Map(node.children.map((c) => [c.path, c]))
        node.children = p.children_order
          .map((cp) => byPath.get(cp))
          .filter((c): c is FolderTreeNode => c !== undefined)
      }
    }
    triggerRef(folderTree)
    folderTreeVersion.value++
  }
  // Kept under the historical name for compatibility with views; false after
  // we fall back to HTTP polling because SSE didn't work.
  const wsAvailable = ref(true)
  const _LS_NOTIF = 'orbvis_notifications'
  const notificationsEnabled = ref(
    typeof Notification !== 'undefined' &&
      Notification.permission === 'granted' &&
      localStorage.getItem(_LS_NOTIF) === '1'
  )

  async function toggleNotifications(): Promise<void> {
    if (typeof Notification === 'undefined') return
    if (notificationsEnabled.value) {
      notificationsEnabled.value = false
      localStorage.setItem(_LS_NOTIF, '0')
      return
    }
    if (Notification.permission === 'denied') return
    if (Notification.permission !== 'granted') {
      const result = await Notification.requestPermission()
      if (result !== 'granted') return
    }
    notificationsEnabled.value = true
    localStorage.setItem(_LS_NOTIF, '1')
  }

  function _recordHistory(objectId: string, perf_data: string, ts: number) {
    const metrics = parsePerfData(perf_data)
    const first = metrics[0]
    if (first === undefined) return
    const arr = history.value[objectId] ?? []
    arr.push({ ts, pct: utilPercent(first) })
    history.value[objectId] = arr.length > HISTORY_MAX ? arr.slice(-HISTORY_MAX) : arr
    const mv = metricValues.value[objectId] ?? {}
    for (const m of metrics) {
      const mArr = mv[m.label] ?? []
      mArr.push({ ts, value: m.value, unit: m.unit })
      mv[m.label] = mArr.length > HISTORY_MAX ? mArr.slice(-HISTORY_MAX) : mArr
    }
    metricValues.value[objectId] = mv
  }

  let sse: EventSource | null = null
  let reprobe: EventSource | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let reprobeTimer: ReturnType<typeof setInterval> | null = null
  let currentMap: string | null = null
  let currentToken: string | undefined = undefined
  // True while we're on the HTTP polling fallback because SSE didn't connect.
  // Not permanent: a re-probe timer keeps testing SSE so a transient failure
  // (proxy hiccup) heals back to live streaming without a page reload.
  let pollingMode = false
  // Guards against overlapping re-probes when one is slow to open/fail.
  let probing = false
  const SSE_REPROBE_INTERVAL_MS = 60_000

  async function connectToMap(mapName: string, token?: string) {
    if (currentMap === mapName && (sse?.readyState === EventSource.OPEN || pollTimer)) return
    disconnect()
    currentMap = mapName
    currentToken = token
    initialLoad.value = true
    try {
      await _fetchStates()
    } finally {
      initialLoad.value = false
    }
    if (!pollingMode) _connect()
    else _startPolling()
  }

  // Settings-preview override: when the radar filter is live-edited in the
  // Settings modal, the preview iframe sets this so the next fetch carries
  // the unsaved filter as query params instead of using the disk-cfg filter.
  const radarOverride = ref<{ filter: string; filterValue: string } | null>(null)
  // Same idea for foldertree's server-side view fields. While set, SSE deltas
  // (built from disk-cfg) are ignored so this override snapshot isn't clobbered.
  const folderOverride = ref<FolderTreeOverride | null>(null)

  async function _fetchStates() {
    if (!currentMap || !currentToken) return
    const mapAtStart = currentMap
    try {
      const data = await boardsApi.getStates(
        mapAtStart,
        currentToken,
        radarOverride.value,
        folderOverride.value
      )
      if (currentMap !== mapAtStart) return
      const newStates: Record<string, ObjectState> = {}
      const ts = Date.now() / 1000
      for (const s of data.states) {
        if (notificationsEnabled.value) _notifyStateChange(s, states.value[s.object_id])
        newStates[s.object_id] = s
        if (s.perf_data) _recordHistory(s.object_id, s.perf_data, ts)
      }
      for (const id of Object.keys(states.value)) {
        if (!newStates[id]) delete states.value[id]
      }
      Object.assign(states.value, newStates)
      lastUpdate.value = ts
      connected.value = data.connection_ok
      _setFolderTree(data.folder_tree ?? null)
      if (notificationsEnabled.value)
        prevFolderHostStates = _diffNotifyFolderTree(folderTree.value, prevFolderHostStates)
    } catch {
      connected.value = false
    }
  }

  function _startPolling() {
    if (!pollTimer) pollTimer = setInterval(_fetchStates, 15_000)
    // Keep probing for SSE so a transient first-connect failure heals back
    // to live streaming instead of polling forever (until a page reload).
    if (!reprobeTimer) reprobeTimer = setInterval(_attemptSseReprobe, SSE_REPROBE_INTERVAL_MS)
  }

  // SSE: GET endpoint, token in query string (EventSource cannot set
  // Authorization). Access-token TTL is short (60 min default), so the
  // exposure window is bounded.
  function _sseUrl(): string {
    return `${_base}/api/v1/sse/boards/${encodeURIComponent(
      currentMap!
    )}?token=${encodeURIComponent(currentToken!)}`
  }

  // While polling, periodically test whether SSE is reachable again. On
  // success we discard the probe and re-establish the real stream via the
  // normal _connect() path (which wires the message/error handlers).
  function _attemptSseReprobe() {
    if (probing || !pollingMode || !currentMap || !currentToken) return
    probing = true
    const probeMap = currentMap
    const probe = new EventSource(_sseUrl())
    reprobe = probe
    let opened = false
    probe.onopen = () => {
      opened = true
      probing = false
      probe.close()
      if (reprobe === probe) reprobe = null
      // A board switch / disconnect happened while the probe was in
      // flight — drop the stale result instead of promoting a stream for
      // the wrong (or no) board.
      if (!pollingMode || currentMap !== probeMap) return
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
      if (reprobeTimer) {
        clearInterval(reprobeTimer)
        reprobeTimer = null
      }
      pollingMode = false
      wsAvailable.value = true
      _connect()
    }
    probe.onerror = () => {
      // Still unreachable — discard; the timer retries on the next tick.
      if (!opened) {
        probe.close()
        if (reprobe === probe) reprobe = null
        probing = false
      }
    }
  }

  function _applyTopologyDelta(delta: TopologyDelta) {
    if (delta.full) {
      topology.value = [...delta.added]
      _applyTopologyTiming(delta.timing)
      return
    }
    // Only rebuild the array (which makes the FlowBoard re-derive its d3
    // nodes) when the structure actually changed. A timing-only tick skips
    // this and patches in place below — no node rebuild, no force-sim
    // restart, just the open drawer/hover re-reading the new next-check.
    if (delta.removed.length || delta.changed.length || delta.added.length) {
      const removed = new Set(delta.removed)
      const updated = new Map<string, TopologyNode>(delta.changed.map((n) => [n.name, n] as const))
      topology.value = topology.value
        .filter((n) => !removed.has(n.name))
        .map((n) => updated.get(n.name) ?? n)
        .concat(delta.added)
    }
    _applyTopologyTiming(delta.timing)
  }

  // Patch check-timing onto existing topology nodes in place. Mutating the
  // reactive node/service objects keeps consumers that read `.next_check`
  // (the detail drawer) live, without replacing the array.
  function _applyTopologyTiming(timing?: TopologyTiming[]) {
    if (!timing?.length) return
    topologyTimingVersion.value++
    const byName = new Map(topology.value.map((n) => [n.name, n] as const))
    for (const tm of timing) {
      const node = byName.get(tm.name)
      if (!node) continue
      node.last_check = tm.last_check ?? null
      node.next_check = tm.next_check ?? null
      node.current_attempt = tm.current_attempt ?? 0
      if (tm.services?.length && node.services?.length) {
        const svcByName = new Map(node.services.map((s) => [s.name, s] as const))
        for (const st of tm.services) {
          const svc = svcByName.get(st.name)
          if (svc) {
            svc.last_check = st.last_check ?? null
            svc.next_check = st.next_check ?? null
          }
        }
      }
    }
  }

  function _connect() {
    if (!currentMap || !currentToken) return
    sse = new EventSource(_sseUrl())
    let opened = false

    sse.onopen = () => {
      opened = true
    }

    sse.onmessage = (event) => {
      try {
        const msg: WebSocketStateUpdate | WebSocketTopologyUpdate = JSON.parse(event.data)
        if (msg.type === 'state_update') {
          const isFull = msg.full ?? true
          for (const s of msg.states.states) {
            if (notificationsEnabled.value) _notifyStateChange(s, states.value[s.object_id])
            states.value[s.object_id] = s
            if (s.perf_data) _recordHistory(s.object_id, s.perf_data, msg.states.generated_at)
          }
          if (isFull) {
            const incomingIds = new Set(msg.states.states.map((s) => s.object_id))
            for (const id of Object.keys(states.value)) {
              if (!incomingIds.has(id)) delete states.value[id]
            }
          } else {
            for (const id of msg.removed_ids ?? []) {
              delete states.value[id]
            }
          }
          // Keep next-check / overdue live without re-sending full state every recheck.
          for (const tm of msg.timing ?? []) {
            const existing = states.value[tm.object_id]
            if (existing) {
              existing.last_check = tm.last_check ?? null
              existing.next_check = tm.next_check ?? null
              existing.current_attempt = tm.current_attempt ?? 0
            }
          }
          lastUpdate.value = msg.states.generated_at
          connected.value = msg.states.connection_ok
          // A disk-cfg delta would overwrite the preview override snapshot.
          if (!folderOverride.value) _applyFolderTreeDelta(msg.states.folder_tree_delta)
          if (notificationsEnabled.value)
            prevFolderHostStates = _diffNotifyFolderTree(folderTree.value, prevFolderHostStates)
        } else if (msg.type === 'topology_update') {
          _applyTopologyDelta(msg.delta)
          topologyReady.value = true
          lastUpdate.value = msg.delta.generated_at
        }
      } catch (e) {
        // A malformed frame must not kill the stream, but stay
        // diagnosable: a serialization/protocol regression would
        // otherwise silently freeze the board on stale state.
        console.warn('[OrbVis] Failed to parse SSE message:', e)
      }
    }

    sse.onerror = () => {
      // EventSource auto-reconnects on transient errors; close + fall back
      // to polling only when the very first connect failed (proxy without
      // streaming support, auth rejected etc.).
      if (!opened) {
        pollingMode = true
        wsAvailable.value = false
        sse?.close()
        sse = null
        _startPolling()
        return
      }
      connected.value = false
    }
  }

  function disconnect() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (reprobeTimer) {
      clearInterval(reprobeTimer)
      reprobeTimer = null
    }
    if (reprobe) {
      reprobe.onopen = null
      reprobe.onerror = null
      reprobe.close()
      reprobe = null
    }
    probing = false
    // Reset so the next board re-attempts SSE fresh instead of inheriting a
    // sticky polling fallback from a previously unreachable board.
    pollingMode = false
    if (sse) {
      sse.onerror = null
      sse.close()
      sse = null
    }
    connected.value = false
    initialLoad.value = false
    states.value = {}
    history.value = {}
    metricValues.value = {}
    metricTitles.value = {}
    metricGraphs.value = {}
    topology.value = []
    topologyReady.value = false
    folderTree.value = null
    folderTreeIndex = new Map()
    prevFolderHostStates = null
    folderOverride.value = null
    currentMap = null
    currentToken = undefined
  }

  function getState(objectId: string): ObjectState | undefined {
    return states.value[objectId]
  }

  async function prefillMetricHistory(
    objectId: string,
    connectionId: string,
    host: string,
    service: string | null,
    timeWindowMinutes: number,
    accessToken: string
  ): Promise<void> {
    try {
      const data = await connectionsApi.metricHistory(
        connectionId,
        host,
        service,
        timeWindowMinutes,
        accessToken
      )
      if (!data || !Object.keys(data.series).length) return
      if (Object.keys(data.titles).length) {
        metricTitles.value[objectId] = { ...data.titles }
      }
      if (data.graphs?.length) {
        metricGraphs.value[objectId] = data.graphs
      }
      const mv: Record<string, MetricPoint[]> = { ...(metricValues.value[objectId] ?? {}) }
      for (const [label, pts] of Object.entries(data.series)) {
        const existing = mv[label] ?? []
        const existingTs = new Set(existing.map((p) => p.ts))
        const merged = [...pts.filter((p) => !existingTs.has(p.ts)), ...existing]
          .sort((a, b) => a.ts - b.ts)
          .slice(-HISTORY_MAX)
        mv[label] = merged
      }
      metricValues.value[objectId] = mv
    } catch {
      // Backend doesn't support metric history (plain Nagios) — silently ignore.
    }
  }

  function clearMetricValues(objectId: string): void {
    metricValues.value[objectId] = {}
    delete metricGraphs.value[objectId]
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
    topologyTimingVersion,
    folderTree,
    folderTreeVersion,
    wsAvailable,
    notificationsEnabled,
    connectToMap,
    disconnect,
    getState,
    refreshNow: _fetchStates,
    async refreshWithIndicator(): Promise<void> {
      initialLoad.value = true
      try {
        await _fetchStates()
      } finally {
        initialLoad.value = false
      }
    },
    refreshAfterCommand(): void {
      void _fetchStates()
      setTimeout(() => void _fetchStates(), 1500)
    },
    toggleNotifications,
    prefillMetricHistory,
    clearMetricValues,
    setRadarOverride(filter: string | null, filterValue?: string): void {
      radarOverride.value =
        filter && typeof filterValue === 'string' ? { filter, filterValue } : null
      void _fetchStates()
    },
    // Refetch only when a server-side field actually changed: client-side
    // toggles re-post the whole patch, but must not trigger a full tree
    // rebuild (≈seconds on 100k+-host sites).
    setFolderTreeOverride(override: FolderTreeOverride | null): void {
      if (JSON.stringify(override) === JSON.stringify(folderOverride.value)) return
      folderOverride.value = override
      void _fetchStates()
    }
  }
})
